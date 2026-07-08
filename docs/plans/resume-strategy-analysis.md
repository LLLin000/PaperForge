# Resume 策略完整分析

## 1. OCR Rebuild 的 Resume

### 检测的是什么
文件系统 `.done.{key}` marker 文件。

### 流程
```
--resume 传入
  ↓
cp_dir = vault/System/PaperForge/.ocr_rebuild_checkpoint/
  ↓
读 .done.* 文件名 → 提取 key
  ↓
从 keys 中剔除这些 key
  ↓
剩余 key 传入 run_derived_rebuild_for_keys()
```

### 怎么写入
`run_derived_rebuild_for_keys()` 里每成功重建一篇，在 `cp_dir` 下 touch `.done.{key}`。

### 弱点
**每次重建只能从 checkpoint list 跳过，跟实际渲染产物无关。**
如果某个 paper 重建中途 crash，`.done.{key}` 不会写入（只有成功最后才写）→ 下次 --resume 会重跑该 paper，正确。
但如果重建成功但产物不完整（比如 `render-map.json` 写了一半断电），`.done.{key}` 已被写入 → **下次 --resume 跳过，但产物损坏**。

当前 OCR 重建的产物是：`render-map.json` / `structure-tree.json` / `fulltext.md` / `role-index.json`，每个都是单独写入。如果最后一步写 `role-index.json` 时进程 kill，前面都已写好。`.done.{key}` 写入在全部完成后，所以这个场景概率低。

---

## 2. Embed Build 的 Resume

### 检测的两层检查

#### 第一层（入口）：build state + model 变化
```
if resume:
    read_vector_build_state(vault)          ← 读 JSON 文件
    if stored_model ≠ current_model:        ← 模型变了？
        resume = False                      ← 降级为全量重建（不清 DB）
```

**只检查 model 字段。不检查 pid 是否存活、status 是否 stale。**

#### 第二层（per-paper）：ChromaDB 向量存在性 + hash 比较

##### Structured path（有 body_units 或 object_units 的论文）
```
col.get(where={"paper_id": key}, limit=1)
  ↓
if existing.get("ids"):                     ← 向量在 ChromaDB 中存在？
    meta = existing["metadatas"][0]
    current_hash = compute_xxx_hash(units)
    if meta["body_units_hash"] == current_hash     ← hash 未变？
       and meta["retrieval_policy_version"] == RETRIEVAL_POLICY_VERSION:
        skip                                   ← 跳过
    else:
        re-embed                              ← hash 变了，重新嵌入
```

##### Legacy path（无 body_units 的论文）
```
collection.get(where={"paper_id": key}, limit=1)
  ↓
if existing["ids"] and len(ids) > 0:        ← 只要向量存在就跳过
    skip
```

### 弱点

#### 断层 A: 入口不检测 stale build state
```
state = {"status": "running", "pid": 34248}
```
进程已死，但 `--resume` 不检查 pid 存活。看到 `status=running` 照常继续。

#### 断层 B: per-paper 不检测 ChromaDB 健康
```
col.get(where={"paper_id": key})
```
如果 ChromaDB 的 VECTOR segment 损坏（HNSW 空但 metadata 有数据），调用 `col.get()` 直接挂起。

异常被 try/except 包住（line 250, 262），但 ChromaDB 崩溃不是 Python 异常——是 native 层 segfault，进程直接 exit code 5，try/except 接不住。

也就是 **一旦 ChromaDB 损坏，`--resume` 任何 paper 都过不了 `col.get()`**，但 `--resume` 的入口没有任何检查。

#### 断层 C: 无 per-paper checkpoint
`mark_vector_build_state` 只写入 `current=N, paper_id=key`，只记录进度条位置。重启后不读这个来跳过——它依赖 ChromaDB 的 `col.get()` 发现已有向量。

所以如果 729 篇跑到 700 篇时 crash，重启 `--resume` 后：
1. `col.get()` 对已写完的 700 篇 → hash 匹配 → skip
2. 对未写的 29 篇 → 不存在 → embed

但 ChromaDB 是 partial write（metadata 有值，HNSW 空），`col.get()` 根本跑不到——入口就挂。

#### 断层 D: 进程 exit code 5 不写 failed state
```
mark_vector_build_state(vault,
    status="failed", message=str(e), pid=0,
)
```
这个只有在 `except Exception as e:` 里才会触发。ChromaDB native crash (exit code 5) 不是 Python Exception —— Python 直接被 kill，没有任何 catch 机会。所以 **build state 永远停留在 `status=running`**。

下次 --resume 读到的 state: `{status: "running", pid: 34248, model: "Qwen/..."}`。model 没变 → 继续 → 又挂。

---

## 3. 两个 Resume 的设计差异

| 维度 | OCR rebuild | Embed build |
|------|------------|-------------|
| checkpoint 形式 | 文件系统 `.done.{key}` | ChromaDB 向量存在性 + hash |
| 失败后恢复 | 读 `.done.*` 跳过成功的 | 读 ChromaDB `col.get()` 判断 |
| 依赖是否写完全 | `.done.{key}` 在全部完成后写入 | ChromaDB `add()` 不是原子的 |
| 是否检测死进程 | 否 | 否 |
| 是否检测坏库 | 不适用 | 否 |
| checkpoint 粒度 | per-paper | per-paper |
| rebuild/embed 每篇成功后的行为 | 写 .done.{key} | 更新 build state current=N |

OCR rebuild 的 resume 比 embed build 更健壮：`.done.{key}` 是独立文件系统操作，不会因为产物损坏而写失败。Embed build 的 resume 依赖 ChromaDB 的 `col.get()` 来验证 —— 但如果 ChromaDB 本身坏了，就全完了。

---

## 4. 完整的故障链（本次事故）

```
1. embed build --force 启动
   state = {status: "running", pid: 12345, model: "Qwen/..."}

2. 跑了 698/729 篇，约 28 分钟
   每篇成功 → state.current 递增

3. 第 699 篇，ChromaDB add() 中
   HNSW index 写入一半
   30 分钟 timeout → 进程被 kill

4. ChromaDB 状态：
   SQLite metadata 已提交（698 篇的向量数据已写入 embeddings 表）
   HNSW 索引文件未写完 （VECTOR segment 为 0）

5. 用户点 Obsidian "重建" 按钮
   → --resume 模式
   → 读 build state: {status: "running", pid: 12345, model: "Qwen/..."}
   → model 没变，继续

6. 第一篇 paper 尝试 col.get(where={"paper_id": key})
   → ChromaDB PersistentClient(path)
   → 尝试加载 HNSW 索引
   → VECTOR segment 损坏（空 index 但 metadata 有值）
   → ChromaDB C++ 层挂起/崩溃
   → 进程 exit code 5

7. build state 没机会写 failed（直接崩）
   下次 --resume 重复步骤 5→6→7
   → 永久卡死
```

---

## 5. 各断层修复方向

| 断层 | 问题 | 修法（只方向，不动手） |
|------|------|----------------------|
| A | Entry 不检测 stale state | resume 入口检查 pid 是否存活 + start time 是否太旧。如果 stale → 报错退出，"请用 --force 重建"。 |
| B | ChromaDB 损坏时 col.get 直接崩 | resume 入口执行 `get_embed_status()`，检查 `healthy` 和 `corrupted`。如果 corrupted → 同 A。 |
| C | 无独立于 ChromaDB 的 checkpoint | embed build 也写 `.done.{key}` 文件（与 OCR rebuild 相同的模式）。resume 时先读 done list。 |
| D | Native crash 不写 failed state | 无法直接解决（exit code 5 是 OS 行为）。但 C 完成后，即使 native crash，`.done.{key}` 已写入前 N 篇，下次 resume 先读 done list 跳过。 |
