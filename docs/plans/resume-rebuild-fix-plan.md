# Resume & Rebuild 修复 Plan

## 当前问题总结

### OCR rebuild resume
- 依赖 `.done.{key}` 文件系统 marker
- 跟产物实际状态无关（代码改了 marker 还在）
- `--all` 只过滤 `can_rebuild`，不检查版本不匹配
- `derived_stale` 是 meta.json 里的静态值，不是运行时比较

### Embed build resume
- 依赖 ChromaDB `col.get()` 判断"是否已嵌入"
- ChromaDB 损坏 → 直接崩，无 fallback
- `build_state["current"]` 每篇都写，但 resume 不用
- 入口不检查 stale state + ChromaDB 健康

### 共性问题
- 没有"检测产物是否匹配当前代码"的机制
- 中断后没有任何保护（native crash 连 Python exception 都抓不到）

---

## 设计方案

### 核心原则

```
1. 用每篇论文的固有属性检测是否需要重建，不用外部 checkpoint
2. 产物版本标签是硬编码期望值，不是 meta.json 的历史值
3. ChromaDB 损坏 → 报错退出，不静默重试
```

---

## Step 1: 统一版本检测

### OCR rebuild: 改 `_run_ocr_rebuild` 的 paper 选择

当前：
```python
if all_papers:
    keys = [r.key for r in rows if r.can_rebuild]    # 只看 can_rebuild
```

改为：
```python
if all_papers:
    # 选取所有不符合当前版本期望的论文
    keys = [r.key for r in rows if _needs_rebuild(r)]
```

`_needs_rebuild()` 函数：

```python
def _needs_rebuild(row) -> bool:
    """用论文自身的版本标签判断是否需要重建，不依赖外部 checkpoint。"""
    if not row.can_rebuild:
        return False
    
    meta = row._meta  # 需要 row 持有 meta 引用
    
    # 1. 版本标签必须匹配当前代码
    dv = meta.get("derived_version", {})
    expected = expected_derived_payload()
    for key, expected_value in expected.items():
        if dv.get(key) != expected_value:
            return True
    
    # 2. 所有产物必须存在
    artifacts = ["render/render-map.json", "index/structure-tree.json",
                 "index/role-index.json", "fulltext.md"]
    paper_dir = vault / "System" / "PaperForge" / "ocr" / row.key
    for rel in artifacts:
        if not (paper_dir / rel).exists():
            return True
    
    return False
```

**不需要 `.done.{key}`，不需要 `derived_stale` 字段。** 重新运行时比较的是"当前代码版本 vs 论文产物版本"，不是"meta 静态值 vs 期望值"。

### OCR rebuild: 移除 `.done.{key}` checkpoint

删除 `cp_dir` 相关的所有逻辑。resume flag 不再需要——`--all` 自动检测哪些需要重建。

但保留 `--resume` 语义：如果用户显式传 `--resume`，只处理中断时未完成的论文。实现方式：不再用 `.done.{key}`，改为 **在每篇成功完成后修改 `derived_version`，`_needs_rebuild` 自然返回 False**。中断后重跑 `--all`，已成功的自动跳过。

---

## Step 2: Embed build resume 修复

### 2a: 入口检测（防止在坏库上挂起）

```python
if resume:
    build_state = read_vector_build_state(vault)
    
    # 检测 stale running state
    if build_state.get("status") == "running":
        pid = build_state.get("pid", 0)
        if not _pid_alive(pid):     # Windows: tasklist /FI "PID eq N"
            print("Previous build crashed. Use --force to rebuild.")
            return 1
    
    # 检测 ChromaDB 健康
    try:
        status = get_embed_status(vault)
        if status.get("corrupted"):
            print("Vector DB corrupted. Use --force to rebuild.")
            return 1
    except Exception:
        print("Vector DB not accessible. Use --force to rebuild.")
        return 1
```

### 2b: Per-paper 检测用 DB hash，不依赖 ChromaDB col.get()

当前 `--resume` 的 per-paper 检测是对的（比较 `body_units_hash`），唯一问题是入口没守住导致它在坏库上跑。

**不改 per-paper 逻辑**，只加入口检测。当 ChromaDB 健康时，`col.get()` 能正常工作，hash 比较是对的。

### 2c: 移除 `build_state["current"]` skip 方案

上一轮讨论的 skip N papers 方案不采用——论文插入 canonical index 后顺序会变。hash 比较已经足够。

---

## Step 3: Embed 多线程

### 瓶颈分析

```
--force 跑 729 篇，约 30 分钟
  每篇 ~2.5 秒 = 1.5s API encode + 1.0s ChromaDB write
```

API 调用（SiliconFlow `encode`）是纯网络 I/O，**完全可以并行**。
ChromaDB `add()` 需要单线程（SQLite + HNSW 构建不是线程安全的）。

### 方案：线程池 encode + 单线程 write

```
主线程：遍历 done_papers
           │
           ↓
  线程池 (4–8 workers)：
    并行调用 provider.encode(texts)
           │
           ↓
  主线程串行：
    collection.add(ids, embeddings, metadatas)
    mark_vector_build_state(current=i, ...)
```

### 实现

在 `commands/embed.py` 的 `run()` 函数中：

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

# 每批 8 篇并行 encode
BATCH_SIZE = 8

with ThreadPoolExecutor(max_workers=4) as pool:
    futures = {}
    for i, entry in enumerate(papers_iter):
        key = entry.get("zotero_key")
        ...
        # 提交 encode 任务到线程池
        future = pool.submit(_encode_paper, vault, key, body_units, object_units)
        futures[future] = key
        
        # 每 BATCH_SIZE 篇或最后一篇：收集结果，串行写入 ChromaDB
        if len(futures) >= BATCH_SIZE or i == total - 1:
            for future in as_completed(futures):
                embeddings, ids, metadatas = future.result()
                # 串行写入
                collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
            futures.clear()
```

临界区只有 `collection.add()` 和 `mark_vector_build_state()`，其余全部并行。

预期加速：4 worker → 30 分钟降到 8-10 分钟。

---

## Step 4: 执行顺序

| Step | 内容 | 文件 | 风险 |
|------|------|------|------|
| 1 | 删 `.done.{key}` 逻辑 | `commands/ocr.py` | 低 |
| 2 | 加 `_needs_rebuild()` 版本检测 | `commands/ocr.py` + `worker/ocr_versions.py` | 低 |
| 3 | embed 入口加 stale state + ChromaDB 健康检测 | `commands/embed.py` | 低 |
| 4 | embed 多线程并行 encode | `commands/embed.py` + `embedding/builder.py` | 中（需要锁住 write） |
| 5 | 去掉 `--resume` flag（OCR rebuild 自动检测，embed 保留但加了入口保护） | `commands/ocr.py` + `commands/embed.py` | 低 |

---

## 边缘情况

| 情况 | 行为 |
|------|------|
| ChromaDB VECTOR segment 空但 METADATA 有值 | Entry 检测到 corrupted → 报错退出，提示用 --force |
| build state 显示 running 但进程已死 | Entry 检测 stale → 报错退出，提示用 --force |
| 中间插入了新论文 | `_needs_rebuild` 检查 `derived_version` → 新论文版本为空 → 需要重建 |
| 代码升级改了点东西 | `EXPECTED_RENDERER_VERSION` bump → 全部匹配不上 → 全量重建 |
| API key 无效 | `provider.encode()` 抛异常 → 线程池收集异常 → 主线程捕获 → 写 failed state 退出 |
