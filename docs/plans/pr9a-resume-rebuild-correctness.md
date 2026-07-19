# PR9A: Resume & Rebuild Correctness

**只做 correctness，不做多线程。**

---

## 当前问题

| 子系统 | 问题 |
|--------|------|
| OCR rebuild `--all` | 只看 `can_rebuild`，不看版本是否匹配 |
| OCR rebuild `--resume` | 依赖 `.done.{key}` marker，跟产物脱钩 |
| OCR rebuild 成功收尾 | 不写 `derived_version`，下次检测重复重建 |
| Embed build `--resume` | 入口无保护，ChromaDB 坏了直接崩 |
| Embed build `--resume` | 无法区分"无 DB"和"坏 DB" |

---

## 设计原则

```
1. 用论文自身的版本标签 + 产物存在性判断是否需要重建
   （不依赖 .done marker，不依赖 derived_stale 静态值）
2. 成功 rebuild/embed 后更新版本标签，使其通过下次检测
3. Embed resume 入口做三道门：stale state → missing DB → corrupted DB
```

---

## Step 1: OCR rebuild 确定性选文

### 选文语义（grilling 确认）

```
ocr rebuild --all
  → 只选 _needs_derived_rebuild()=True 的论文
  → 版本不匹配 / 缺产物 → rebuild

ocr rebuild --status <STATUS>
  → 按用户指定状态选文，不过版本检测
  → 只要 can_rebuild 且状态匹配就执行

ocr rebuild KEY1 KEY2
  → manual override
  → 只要 can_rebuild 就执行，不过滤版本
```

### 核心函数 `_needs_derived_rebuild(vault, key)`

```python
def _needs_derived_rebuild(vault: Path, key: str) -> tuple[bool, str]:
    """检测一篇论文是否需要重建。返回 (need, reason)。"""
    from paperforge.worker.ocr_artifacts import artifact_paths_for_root
    from paperforge.config import pipeline_paths

    ocr_root = Path(pipeline_paths(vault)["ocr"])
    artifacts = artifact_paths_for_root(ocr_root, key)
    paper_dir = artifacts.paper_root

    if not artifacts.meta_json.exists():
        return False, "no_meta"

    meta = read_json(artifacts.meta_json)

    # can_rebuild 条件
    has_raw = artifacts.blocks_raw.exists()
    has_source_meta = artifacts.source_metadata.exists()
    if not _can_rebuild(meta, has_raw, has_source_meta):
        return False, "cannot_rebuild"

    # 版本检测（运行时比较，不依赖 meta.derived_stale）
    state = classify_version_state(
        meta,
        expected_raw={},               # derived-only rebuild 不检 raw
        expected_derived=expected_derived_payload(),
    )
    if state["derived_stale"]:
        return True, "version_mismatch"

    # 产物完整性检测
    required = [
        "structure/blocks.structured.jsonl",
        "render/render-map.json",
        "index/structure-tree.json",
        "index/role-index.json",
        "fulltext.md",
        "health/ocr_health.json",
    ]
    for rel in required:
        if not (paper_dir / rel).exists():
            return True, f"missing:{rel.split('/')[-1]}"

    return False, "current"
```

Note: `artifact_paths_for_root` 签名为 `(ocr_root, zotero_key)`，不是 `(paper_dir, key)`。

### 选文逻辑 `_select_rebuild_keys()`

```python
def _select_rebuild_keys(vault, rows, all_papers, status_filter, keys):
    """确定需要重建的论文列表。"""
    by_key = {r.key: r for r in rows}

    if all_papers:
        # 智能增量：只选版本不匹配或缺产物的
        selected = []
        reasons = {}
        for r in rows:
            if not r.can_rebuild:
                continue
            need, reason = _needs_derived_rebuild(vault, r.key)
            if need:
                selected.append(r.key)
                reasons[r.key] = reason
        return selected, reasons

    if status_filter:
        # 用户指定状态 → 不过滤版本
        selected = [r.key for r in rows if r.status == status_filter and r.can_rebuild]
        return selected, {}

    if keys:
        # manual override → 不过滤版本
        selected = [k for k in keys if k in by_key and by_key[k].can_rebuild]
        return selected, {}

    return [], {}
```

### dry-run 输出

```text
Would rebuild 37 paper(s):
  - ABC123: version_mismatch
  - DEF456: missing:render-map.json
```

每篇打印 reason，便于验证选文是否正确。

### 删除 `.done.{key}` checkpoint

- 从 `_run_ocr_rebuild` 移除 `cp_dir` 相关代码
- `--resume` 保留为兼容 no-op，不再使用 marker 文件：

```python
if resume:
    print("Note: OCR rebuild resume is now version/artifact based; .done markers are ignored.")
```

---

## Step 2: 成功 rebuild 后写 derived_version

**这是 P0。如果不写，每次 `--all` 都会无限重建。**

### 修复 `_apply_post_rebuild_version_flags()`

当前只写：
```python
updated["derived_stale"] = False
updated["version_state_updated_at"] = ...
```

改为写入当前版本：

```python
def _apply_post_rebuild_version_flags(meta: dict) -> dict:
    updated = dict(meta)
    updated["derived_version"] = expected_derived_payload()  # 写入当前版本
    updated["derived_stale"] = False
    updated["version_state_updated_at"] = datetime.now().isoformat()
    return updated
```

### 测试硬门槛

```
1. derived_version mismatch → rebuild
2. rebuild 后 meta.derived_version == expected_derived_payload()
3. 再跑 --all dry-run → 不再选中
```

### `derived_stale` 保留为 UI hint

`derived_stale` 字段继续写入 `False`，maintenance UI 仍然用它显示推荐操作。
但 rebuild selection 不再依赖它。

---

## Step 3: Embed resume 入口三道门

### 门一：stale running state 检测

```python
if resume:
    build_state = read_vector_build_state(vault)

    if build_state.get("status") == "running":
        stale = False
        pid = build_state.get("pid", 0)
        if not pid:
            stale = True
        elif not _pid_alive(pid):
            stale = True
        else:
            started = build_state.get("started_at", "")
            if started:
                try:
                    dt = datetime.fromisoformat(started)
                    if (datetime.now(timezone.utc) - dt).total_seconds() > 43200:
                        stale = True
                except:
                    pass
        if stale:
            print("Previous build appears stale (crashed?). Use --force to rebuild.")
            return 1
```

### 门二：missing DB → fresh build

```python
    db_path = get_vector_db_path(vault)
    if not db_path.exists():
        resume = False      # 无旧向量，从头开始（不是 error）
    else:
```

### 门三：corrupted DB 检测

```python
        ok, err = _assert_collections_healthy(vault)
        if not ok:
            print(f"Vector DB corrupted ({err}). Use --force to rebuild.")
            return 1

        # 过三道门后，正常 resume
        stored_model = build_state.get("model", "")
        if stored_model and _current_model and stored_model != _current_model:
            msg = f"Model changed: {stored_model} -> {_current_model}. Re-embedding all."
            print(msg)
            resume = False
```

### `_pid_alive()` 跨平台

```python
def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import subprocess
            r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                              capture_output=True, text=True, timeout=5)
            return str(pid) in r.stdout
        except:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
```

### `_assert_collections_healthy()` 显式 probe

```python
def _assert_collections_healthy(vault: Path) -> tuple[bool, str]:
    """显式 probe 三个 collection，不依赖 get_embed_status 的内部判断。"""
    for name in ("paperforge_fulltext", "paperforge_body", "paperforge_objects"):
        try:
            col = get_collection(vault, name=name)
            col.count()
        except Exception as exc:
            return False, f"{name}: {exc}"
    return True, ""
```

---

## Step 4: 不做的（PR9B）

- 多线程 encode
- encode/write 分段改造
- 批量 API 优化

---

## Step 5: 测试

### OCR rebuild selection

| # | 场景 | 期望 |
|---|------|------|
| 1 | 版本匹配 + 产物完整 | skip |
| 2 | `derived_version` 不匹配 | rebuild |
| 3 | 缺 render-map.json | rebuild |
| 4 | 缺 structure-tree.json | rebuild |
| 5 | 缺 blocks.structured.jsonl | rebuild |
| 6 | `can_rebuild=False` | skip |
| 7 | 重建后 `derived_version` 被更新 | 下次 skip |
| 8 | 有旧 `.done.{key}` 但版本不匹配 | 仍然 rebuild（旧 marker 不参与） |
| 9 | explicit key + 版本匹配 | rebuild（manual override） |
| 10 | `--status done_degraded` + 版本匹配 | rebuild（不过滤版本） |
| 11 | dry-run 输出每篇 reason | 打印原因 |

### Embed resume guard

| # | 场景 | 期望 |
|---|------|------|
| 1 | 无 vector DB + `--resume` | fresh build，不报错 |
| 2 | stale `status=running` + pid 死 | 报错退出，提示 --force |
| 3 | 三 collection 任一不可访问 | 报错退出，提示 --force |
| 4 | 健康 DB + hash 匹配 | skip |
| 5 | 健康 DB + hash 不匹配 | re-embed |
| 6 | model 变化 | 全量重建 |

---

## 文件清单

| File | Change |
|------|--------|
| `paperforge/commands/ocr.py` | `_run_ocr_rebuild` → `_select_rebuild_keys` + 删 .done |
| `paperforge/worker/ocr_versions.py` | 确认 `expected_derived_payload()` 可用（不改） |
| `paperforge/worker/ocr_rebuild.py` | `_apply_post_rebuild_version_flags()` 写 derived_version |
| `paperforge/commands/embed.py` | 入口三道门 + `_pid_alive` + `_assert_collections_healthy` |
| `paperforge/embedding/_chroma.py` | 导出 `_COLLECTION_NAMES`（已有） |
| `tests/` | 新增 17 个测试场景 |

---

## 风险

| 风险 | 缓解 |
|------|------|
| `classify_version_state` 可能检 raw 版本 | rebuild 中传 `expected_raw={}` 跳过 raw |
| 产物检测太严导致过度重建 | required list 经过评审，不包含可选产物 |
| `_pid_alive` timeout | 5s timeout + except → False |
| `--all` 检测到版本 mismatch 全量重建 | 正确行为：代码变了，产物应该重建 |
| explicit key 用户以为会静默跳过 | 不会，manual override 强制重建 |
