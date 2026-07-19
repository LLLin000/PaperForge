# PR9B: Embed Parallel Encode

**Depends on**: PR9A (resume/rebuild correctness)  
**Scope**: 并行 embedding API encode + 串行 ChromaDB write  
**不改变 resume/selection 逻辑，只加速**

---

## 瓶颈分析

### 当前时序（--force, 729 papers）

```
Total: ~30 min
  Per paper: ~2.5s
    API encode:              ~1.5s    ← 纯网络 I/O，可并行
    ChromaDB write:          ~0.8s    ← HNSW 构建，必须串行
    Metadata + state:        ~0.2s
```

### 目标

4 worker 并行 → 729 ÷ 4 × (1.5s + 0.8s) ≈ 10 min（~3× 加速）

---

## 设计原则

```
1. paper 级原子性：同一篇论文的 body/object/legacy 全部 encode 成功后才 replace
2. prepare 在主线程（读 DB、chunk fulltext），不参与并行
3. encode 在线程池（纯网络 I/O），每个 worker 创建自己的 provider
4. write 在主线程串行（ChromaDB HNSW 构建不是线程安全）
5. delete old vectors 在 encode 成功后、write 前执行
```

### 核心 contract

```
A paper is deleted and rewritten only after ALL payloads for that paper
have been successfully encoded.
```

---

## 数据结构

```python
@dataclass
class EmbeddingPayload:
    """准备阶段产出的载荷：texts 和 metadatas，未 encode。"""
    collection_name: str
    texts: list[str]
    ids: list[str]
    metadatas: list[dict]

@dataclass
class EncodedPayload:
    """encode 后的载荷：包含 embeddings。必须带 texts（不可从 metadata 反推）。"""
    collection_name: str
    texts: list[str]
    ids: list[str]
    metadatas: list[dict]
    embeddings: list[list[float]]

@dataclass
class PaperEmbeddingJob:
    """一篇论文的所有载荷，打包成一个 job。"""
    paper_id: str
    payloads: list[EmbeddingPayload]

@dataclass
class PaperEncodedBundle:
    """一篇论文 encode 完成后的结果。"""
    paper_id: str
    payloads: list[EncodedPayload]
    chunk_count: int
```

---

## 三段式 pipeline

### Phase 1: PREPARE（主线程串行）

为每篇论文准备 1–3 个 `EmbeddingPayload`（legacy / body / object），分别对应三个 collection。

```python
def prepare_payloads_for_entry(
    vault: Path, entry: dict
) -> list[EmbeddingPayload] | None:
    """为一篇论文准备所有 payload。不写 ChromaDB，不改状态，不删 vectors。"""
    key = entry.get("zotero_key")
    payloads = []

    has_body = _has_body_units_in_db(vault, key)
    has_object = _has_object_units_in_db(vault, key)

    if has_body or has_object:
        if has_body:
            body_units = get_body_units_for_embedding(vault, key)
            payloads.append(prepare_body_payload(key, body_units))
        if has_object:
            object_units = get_object_units_for_embedding(vault, key)
            payloads.append(prepare_object_payload(key, object_units))
    else:
        # Legacy path
        fulltext_rel = entry.get("fulltext_path", "")
        if not fulltext_rel:
            return None
        fulltext_path = vault / fulltext_rel
        chunks = chunk_fulltext(fulltext_path)          # chunk 在主线程做
        if chunks:
            payloads.append(prepare_legacy_payload(key, chunks))

    return payloads if payloads else None
```

#### `prepare_legacy_payload()`

```python
def prepare_legacy_payload(zotero_key: str, chunks: list[dict]) -> EmbeddingPayload:
    texts = [c["text"] for c in chunks]
    ids = [f"{zotero_key}_{c['chunk_index']}" for c in chunks]
    metadatas = [
        {
            "paper_id": zotero_key,
            "section": c.get("section", ""),
            "page_number": c.get("page_number", 0),
            "chunk_index": c.get("chunk_index", i),
            "token_estimate": c.get("token_estimate", 0),
        }
        for i, c in enumerate(chunks)
    ]
    return EmbeddingPayload(
        collection_name="paperforge_fulltext",
        texts=texts, ids=ids, metadatas=metadatas,
    )
```

#### `prepare_body_payload()`

```python
def prepare_body_payload(zotero_key: str, body_units: list[dict]) -> EmbeddingPayload:
    current_hash = compute_body_units_hash(body_units)
    texts = [u["unit_text"] for u in body_units]
    ids = [u["unit_id"] for u in body_units]
    metadatas = [
        {
            "paper_id": zotero_key,
            "section_path": u.get("section_path", ""),
            "unit_id": u["unit_id"],
            "unit_kind": "body",
            "body_units_hash": current_hash,
            "retrieval_policy_version": RETRIEVAL_POLICY_VERSION,
            "token_estimate": u.get("token_estimate", 0),
        }
        for u in body_units
    ]
    return EmbeddingPayload(collection_name="paperforge_body", texts=texts, ids=ids, metadatas=metadatas)
```

#### `prepare_object_payload()` 同理

collection_name=`"paperforge_objects"`，metadata 包含 `unit_kind="object"`, `object_kind`, `object_label`, `object_units_hash`。

#### 向下兼容

```python
def embed_body_units(vault, key, body_units):
    payload = prepare_body_payload(key, body_units)
    encoded = _encode_payload(vault, payload)
    _write_encoded_payload(vault, encoded)
    return len(body_units)

def embed_paper(vault, key, chunks):
    payload = prepare_legacy_payload(key, chunks)
    encoded = _encode_payload(vault, payload)
    _write_encoded_payload(vault, encoded)
    return len(chunks)
```

旧函数保留为兼容 wrapper，不破坏已有调用。

### Phase 2: ENCODE（线程池，并行）

```python
def _encode_payload(vault: Path, payload: EmbeddingPayload) -> EncodedPayload:
    """纯函数：encode texts → embeddings。每个 worker 内创建自己的 provider。"""
    from paperforge.embedding.providers.openai_compatible import OpenAICompatibleProvider
    provider = OpenAICompatibleProvider(vault)
    embeddings = provider.encode(payload.texts)
    return EncodedPayload(
        collection_name=payload.collection_name,
        texts=payload.texts,
        ids=payload.ids,
        metadatas=payload.metadatas,
        embeddings=embeddings,
    )

def _encode_paper_job(vault: Path, job: PaperEmbeddingJob) -> PaperEncodedBundle:
    """将一篇论文的所有 payload 顺序 encode（worker 线程内）。"""
    encoded_payloads = []
    total_chunks = 0
    for payload in job.payloads:
        encoded = _encode_payload(vault, payload)
        encoded_payloads.append(encoded)
        total_chunks += len(payload.ids)
    return PaperEncodedBundle(
        paper_id=job.paper_id,
        payloads=encoded_payloads,
        chunk_count=total_chunks,
    )
```

注意：
- `OpenAICompatibleProvider` 在线程内创建，不共享 client
- 同一篇论文的多个 payload（body + object）在同一个 worker 线程内顺序 encode
- 一篇论文的所有 payload 全部 encode 成功后才返回 → paper 级原子

### Phase 3: WRITE（主线程串行）

```python
def _write_encoded_payload(vault: Path, encoded: EncodedPayload):
    """写入 ChromaDB。主线程串行，HNSW 构建不是线程安全。"""
    col = get_collection(vault, name=encoded.collection_name)
    col.add(
        ids=encoded.ids,
        embeddings=encoded.embeddings,
        documents=encoded.texts,
        metadatas=encoded.metadatas,
    )
```

---

## 主流程

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import batched

BATCH_SIZE = 8      # 每批最多 8 篇 in-flight
MAX_WORKERS = 4     # 并行 encode 线程数

papers_embedded = 0
chunks_embedded = 0

# Phase 1: PREPARE（主线程）
# resume/hash skip 已在主线程完成
jobs: list[PaperEmbeddingJob] = []
for entry in papers_iter:
    payloads = prepare_payloads_for_entry(vault, entry)
    if payloads:
        jobs.append(PaperEmbeddingJob(
            paper_id=entry.get("zotero_key"),
            payloads=payloads,
        ))

# Phase 2+3: ENCODE（线程池）+ WRITE（主线程）
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
    for batch in batched(jobs, BATCH_SIZE):
        futures = [
            pool.submit(_encode_paper_job, vault, job)
            for job in batch
        ]

        for future in as_completed(futures):
            try:
                bundle = future.result()    # 如果抛异常，不删旧 vectors
            except Exception as e:
                # 不处理这篇，继续下一篇（旧 vectors 还在）
                logger.error(f"Encode failed for {bundle.paper_id}: {e}")
                continue

            # encode 全部成功后才 replace old vectors
            delete_paper_vectors(vault, bundle.paper_id)

            for payload in bundle.payloads:
                try:
                    _write_encoded_payload(vault, payload)
                except Exception as e:
                    # write 失败 → 已进入 replace 状态
                    # 写 failed state，下一次 resume 用 hash 修复
                    logger.error(f"Write failed for {bundle.paper_id}: {e}")
                    mark_vector_build_state(vault, status="failed", ...)
                    raise

            chunks_embedded += bundle.chunk_count
            papers_embedded += 1
            mark_vector_build_state(vault, current=papers_embedded, ...)
```

---

## 边界处理

| 情况 | 行为 |
|------|------|
| API key invalid | `provider.encode()` 抛异常 → future.result() 抛 → 不删旧 vectors，跳过这篇 |
| 某篇 body encode 成功、object encode 失败 | worker 线程抛异常 → bundle 不返回 → 旧 vectors 完整保留 |
| `_write_encoded_payload` 失败 | 已执行 delete → 写 failed state | 
| 线程池满载 | `batched(jobs, BATCH_SIZE)` 限制 in-flight 数量 |
| provider 被多个 worker 共享？ | 不会，每个 worker 内部创建自己的 provider |
| ChromaDB `add()` 异常 | 主线程 catch → 写 failed state → 当前批次的 futures 取消 |

---

## 文件清单

| File | Change |
|------|--------|
| `paperforge/embedding/builder.py` | 新增 `prepare_legacy_payload()`, `prepare_body_payload()`, `prepare_object_payload()`；`embed_body_units`/`embed_paper` 保留为兼容 wrapper |
| `paperforge/embedding/__init__.py` | 导出新函数（如需要） |
| `paperforge/commands/embed.py` | 主循环改为三段式 pipeline + ThreadPoolExecutor |

---

## 风险

| 风险 | 缓解 |
|------|------|
| `httpx.Client` 跨线程安全？ | 每个 worker 创建独立 provider，不共享 client |
| ChromaDB `add()` 线程安全？ | 只在主线程串行调用 |
| API rate limit | `MAX_WORKERS=4` 参数化，可调小 |
| `batched` 需要 Python 3.12 | 如果 3.12 以下手动实现 `batched()` |
| legacy `chunk_fulltext` 本身慢 | prepare 在主线程做，如果成为瓶颈再考虑并行 prepare |
