# PR9C: Streaming Pipeline for Embed Progress

**目标**: 消除 Phase 1 的静默期，让 EMBED_PROGRESS 从第一篇论文处理完成就开始输出。

---

## 问题

当前三段式 pipeline（PR9B）：

```
Phase 1 (PREPARE):  遍历 729 篇，读 DB，collect jobs    ← 不输出进度，~30s 静默
Phase 2 (ENCODE):   线程池 encode                      
Phase 3 (WRITE):    主线程串行 write                     ← EMBED_PROGRESS 在这里
```

用户看到的进度条卡在 0/729 约 30 秒。

## 方案：Sliding Window Pipeline

维持一个 **固定大小的 in-flight window**，不先准备全部 729 篇：

```
WINDOW_SIZE = max_workers * 4    (默认 4×4=16)

主线程:
  for 每篇论文:
    resume check → if skip: 推进 processed_count, 输出 EMBED_PROGRESS
    prepare payloads
    submit encode to ThreadPool
    if in-flight >= WINDOW_SIZE:
      wait(FIRST_COMPLETED)
      → EMBED_PROGRESS:{processed_count}:{total}:{key}
      → delete_paper_vectors (仅 encode 成功后)
      → write_encoded_payload
      → mark_vector_build_state
  while in-flight:
    收尾遗留

encode 失败 → fail closed, 不跳过
```

## 收益

- 第一篇论文处理后（~2s）就开始输出 EMBED_PROGRESS
- 之后每完成一篇更新一次，间隔平均 0.5s（4 worker）
- 进度条从点击后 2 秒开始持续移动

---

## 关键语义

### 进度计数器

```python
processed_count = 0     # skip + embedded，用于 EMBED_PROGRESS
papers_embedded = 0     # 实际写入了 vectors
papers_skipped = 0
chunks_embedded = 0
```

`EMBED_PROGRESS` 始终用 `processed_count`，否则 resume skip 会导致进度条卡在 `<total`。

### resume skip 也推进进度

```python
if should_skip:
    processed_count += 1
    papers_skipped += 1
    print(f"EMBED_PROGRESS:{processed_count}:{total}:{key}", flush=True)
    mark_vector_build_state(vault, current=processed_count, ...)
    continue
```

不新增 `EMBED_SKIP` 事件，不改插件端协议。

### encode 失败必须 fail closed

```
encode 失败:
  - 不 delete old vectors
  - cancel in-flight futures (可能)
  - mark_vector_build_state(status="failed", paper_id=key, message=str(exc))
  - 写 failed runtime state
  - return 1
```

不跳过继续，否则 build 报告的 completed 状态是假的。

---

## 数据结构

保持 PR9B 的 paper-level bundle，不退回 payload-level：

```python
in_flight: dict[Future[PaperEncodedBundle], PaperEmbeddingJob]
```

一篇论文的 legacy + body + object payloads 是一起提交、一起完成的。

---

## 主循环

```python
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

max_workers = PR9B_MAX_WORKERS    # 4
window_size = max_workers * 4      # 16

with ThreadPoolExecutor(max_workers=max_workers) as pool:
    in_flight: dict[Future, PaperEmbeddingJob] = {}
    processed_count = 0

    def submit_job(job: PaperEmbeddingJob):
        fut = pool.submit(encode_paper_job, vault, job)
        in_flight[fut] = job

    def complete_one(block: bool = True):
        nonlocal processed_count, papers_embedded, chunks_embedded
        if not in_flight:
            return
        done, _ = wait(in_flight.keys(), return_when=FIRST_COMPLETED)
        for fut in done:
            job = in_flight.pop(fut)
            try:
                bundle = fut.result()
            except Exception as exc:
                # fail closed
                mark_vector_build_state(vault, status="failed",
                    paper_id=job.paper_id, message=str(exc), pid=0)
                return False

            # encode 全部成功后才 replace
            delete_paper_vectors(vault, bundle.paper_id)
            for payload in bundle.payloads:
                write_encoded_payload(vault, payload)

            processed_count += 1
            papers_embedded += 1
            chunks_embedded += bundle.chunk_count

            print(f"EMBED_PROGRESS:{processed_count}:{total}:{bundle.paper_id}", flush=True)
            mark_vector_build_state(vault, current=processed_count, ...)
        return True

    # ── Produce ──
    for entry in papers_iter:
        key = entry.get("zotero_key")
        if not key:
            continue

        has_body = _has_body_units_in_db(vault, key)
        has_object = _has_object_units_in_db(vault, key)

        # resume check / skip
        if resume and _should_skip(vault, key, has_body, has_object):
            processed_count += 1
            papers_skipped += 1
            print(f"EMBED_PROGRESS:{processed_count}:{total}:{key}", flush=True)
            mark_vector_build_state(vault, current=processed_count, ...)
            continue

        # prepare job (legacy / body / object)
        if has_body or has_object:
            body_units = get_body_units_for_embedding(vault, key) if has_body else []
            object_units = get_object_units_for_embedding(vault, key) if has_object else []
            payloads = prepare_payloads_for_entry(vault, key, has_body, has_object, body_units, object_units)
        else:
            fulltext_rel = entry.get("fulltext_path", "")
            if not fulltext_rel:
                continue
            payloads = prepare_payloads_for_entry(vault, key, False, False, [], [], fulltext_rel=fulltext_rel)

        if not payloads:
            processed_count += 1
            print(f"EMBED_PROGRESS:{processed_count}:{total}:{key}", flush=True)
            mark_vector_build_state(vault, current=processed_count, ...)
            continue

        job = PaperEmbeddingJob(paper_id=key, payloads=payloads)
        submit_job(job)

        if len(in_flight) >= window_size:
            ok = complete_one(block=True)
            if not ok:
                return 1

    # ── Drain ──
    while in_flight:
        ok = complete_one(block=True)
        if not ok:
            return 1
```

---

## WINDOW_SIZE

```python
PR9B_MAX_WORKERS = 4       # 已有常量
PR9C_WINDOW_SIZE = PR9B_MAX_WORKERS * 4   # 16
```

原因：每个 paper 的 embeddings 同时驻留，太大可能导致 API rate limit 或内存压力。
可参数化（`--window`），但当前不做。

---

## 边界

| 情况 | 行为 |
|------|------|
| resume skip | 推进 processed_count，输出 EMBED_PROGRESS |
| 无 payloads（所有 resume 跳过 + 无可 embed 论文） | 每篇走 skip 路径，processed_count 正常推进 |
| encode 失败 | fail closed，return 1 |
| write 失败 | 同现在，抛异常到主循环 |
| 最后一批 < WINDOW_SIZE | drain 阶段正常处理 |
| 同时多个 future 完成 | wait(FIRST_COMPLETED) 可返回多个，全部处理 |

---

## 文件变更

| File | Change |
|------|--------|
| `paperforge/commands/embed.py` | 替换 Phase 1 + Phase 2+3 为 sliding window loop |
| `tests/test_pr9c_streaming_embed.py` | 新增测试（见下方） |

## 不改的

- `paperforge/embedding/builder.py` — 数据结构 + prepare/encode/write 函数不动
- 插件端 — 不新增事件类型，不改解析逻辑

---

## 测试

### TC-C1：首个 progress 不等全量 prepare

```python
# 模拟 100 篇论文，window=4
# assert 第一批 4 篇 submit 后，complete_one 输出 EMBED_PROGRESS
# 此时 prepared < total
```

### TC-C2：resume skip 推进 progress

```python
# 10 papers, 8 skipped, 2 embedded
# expect 10 EMBED_PROGRESS lines
# final processed_count == 10
# papers_skipped == 8, papers_embedded == 2
```

### TC-C3：encode failure fail closed

```python
# mock encode_paper_job raises
# assert:
#   return code 1
#   mark_vector_build_state(status="failed")
#   delete_paper_vectors not called for failed key
#   EMBED_DONE not printed
```

### TC-C4：write remains serial

mock write_encoded_payload，确认所有调用在同一个主线程。

### TC-C5：bounded in-flight

```python
# assert max(len(in_flight)) <= WINDOW_SIZE
# 即使论文数远超 WINDOW_SIZE
```

---

## 风险

| 风险 | 缓解 |
|------|------|
| prepare + submit 跟不上 encode | prepare 是纯本地 I/O（读 DB），比 encode（网络 I/O）快得多 |
| 多篇 paper 同时 ChromaDB write | write 是串行的，只在主线程 complete_one 中调用 |
| API rate limit | WINDOW_SIZE=16，每篇平均 0.5s → ~32 req/s，在正常范围内 |
