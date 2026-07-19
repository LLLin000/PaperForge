# Rebuild 加速与批量改进 — 实现计划

> Branch: `feat/rebuild-speed`
> Base: `master`
> Spec: `docs/superpowers/specs/2026-07-05-rebuild-speed-and-batch-improvements.md`
> Review: 8.8/10 — 可以进入实现

## 总览

5 个 Wave，文件不重叠，可并行。

| Wave | 文件 | 改动 | 复杂度 |
|------|------|------|--------|
| 1 | `ocr_rebuild.py` + `commands/ocr.py` + `cli.py` | 阶段化 + 跨论文并行 + checkpoint 重构 | 高 |
| 2 | `ocr_objects.py` | 资产裁剪并行（复用现有坐标逻辑，不重写） | 中 |
| 3 | `ocr_maintenance.py` | Display 封装（用真实字段） | 低 |
| 4 | `commands/embed.py` | Embed 人类进度（保留机器协议） | 低 |
| 5 | `docs/COMMANDS.md` | CLI 文档补齐（从 parser 核对） | 低 |

---

## Wave 1: 阶段化 + 跨论文并行

### 1.1 前置

```python
import logging
logger = logging.getLogger(__name__)
```

### 1.2 改写 `run_derived_rebuild_for_keys()`

**签名：**

```python
def run_derived_rebuild_for_keys(
    vault: Path,
    keys: list[str],
    progress_bar=None,
    checkpoint_dir: Path | None = None,
    parallel: int = 4,
) -> dict:
```

**函数体：checkpoint 过滤在入口统一执行，串行/并行路径共享一处过滤逻辑。**

```python
def run_derived_rebuild_for_keys(vault, keys, progress_bar=None,
                                  checkpoint_dir=None, parallel=4):
    # 入口统一过滤 checkpoint，串行/并行路径共享
    if checkpoint_dir:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        keys = _filter_completed_keys(keys, checkpoint_dir)

    if parallel and len(keys) > 1:
        return _run_parallel_rebuild(vault, keys, parallel, checkpoint_dir)

    # 串行路径
    rebuilt_count = 0
    keys_iter = progress_bar(keys, desc="OCR rebuild") if progress_bar else keys
    for key in keys_iter:
        result = _rebuild_one_paper(vault, key)
        if result["ok"]:
            rebuilt_count += 1
            if checkpoint_dir:
                _write_done_marker(checkpoint_dir, key)
    return {"rebuild_count": rebuilt_count}
```

### 1.3 提取 `_rebuild_one_paper()`（module-level）

**约束：module-level，Windows/spawn pickle-safe。不写成内部闭包。**

**import 策略：保持重 imports 在阶段函数内部。** 只把 `logging`, `json`, `Path`, `datetime`, `concurrent.futures` 等 stdlib 提到模块顶部。fitz/figure/render/health 等不动。

```python
def _rebuild_one_paper(vault: Path, key: str) -> dict:
    try:
        ocr_root = pipeline_paths(vault)["ocr"]
        artifacts = artifact_paths_for_root(ocr_root, key)
        paper_root = artifacts.paper_root
        if not paper_root.exists():
            return {"key": key, "ok": False, "error": "paper root missing", "rebuild_count": 0}
        if not artifacts.blocks_raw.exists():
            return {"key": key, "ok": False, "error": "raw blocks missing", "rebuild_count": 0}

        raw_blocks = list(read_jsonl(artifacts.blocks_raw))
        meta = read_json(artifacts.meta_json) if artifacts.meta_json.exists() else {}

        # Phase 1–5
        ...
        return {"key": key, "ok": True, "rebuild_count": 1}
    except Exception as e:
        logger.exception(f"Rebuild failed for {key}: {e}")
        return {"key": key, "ok": False, "error": str(e), "rebuild_count": 0}
```

#### Phase 1: `_phase_read_and_span()`

读 raw blocks → backfill 去重 → span backfill（有效跳过）→ PDF 行提取 → source metadata enrich

Returns: `(raw_blocks, meta, source_pdf_path, source_meta, page_pdf_lines, span_meta_patch)`

#### Phase 2: `_phase_structure_and_metadata()`

`build_structured_blocks()` → `write_role_span_profiles()` → metadata resolve → write

Returns: `(structured, doc_structure, resolved)`

#### Phase 3: `_phase_figures_tables_objects()`

**必须保护以下顺序（`apply_object_writebacks` 必须在 `write_figure_inventory` 前）：**

```text
1. build_figure_inventory()
2. write_back_figure_roles()
3. residual_author_bio_pass() + post_ref_bio_cleanup()
4. synthesize_reader_figures()
5. build_table_inventory()
6. resolve_media_asset_conflicts()
7. attach_ownership_conflicts()
8. apply_object_writebacks()         ← 这个顺序不能动
9. write_figure_inventory()
10. write_back_table_roles()
11. write_table_inventory()
12. write_structured_blocks_jsonl()
13. extract_and_write_objects()
```

#### Phase 4: `_phase_render_and_health()`

`render_fulltext_markdown()` → health → decision log → write

#### Phase 5: `_phase_index_and_meta()`

role index → structure tree → version flags → render outputs → meta.json

### 1.4 `_run_parallel_rebuild()`

```python
def _run_parallel_rebuild(vault, keys, workers, checkpoint_dir=None):
    from concurrent.futures import ProcessPoolExecutor, as_completed
    import sys, time, logging
    logger = logging.getLogger(__name__)

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_rebuild_one_paper, vault, k): k for k in keys}
        rebuilt_count = 0
        errors = []
        start = time.monotonic()
        for i, f in enumerate(as_completed(futures), 1):
            key = futures[f]
            try:
                result = f.result()
            except Exception as exc:
                logger.error(f"Parallel worker failed for {key}: {exc}")
                errors.append({"key": key, "ok": False, "error": repr(exc), "rebuild_count": 0})
                continue
            if result["ok"]:
                rebuilt_count += 1
                if checkpoint_dir:
                    _write_done_marker(checkpoint_dir, key)
            else:
                errors.append(result)
            print(f"[{i}/{len(keys)}] {key} — total {time.monotonic()-start:.1f}s",
                  file=sys.stderr, flush=True)
    return {"rebuild_count": rebuilt_count, "errors": errors}
```

### 1.5 Checkpoint 辅助函数

```python
def _write_done_marker(checkpoint_dir: Path, key: str):
    (checkpoint_dir / f".done.{key}").write_text("", encoding="utf-8")

def _filter_completed_keys(keys: list[str], checkpoint_dir: Path) -> list[str]:
    done = set()
    if checkpoint_dir.exists():
        for f in checkpoint_dir.iterdir():
            if f.name.startswith(".done."):
                done.add(f.name[len(".done."):])
    return [k for k in keys if k not in done]
```

### 1.6 CLI 接口

**`cli.py` parser：**

```python
group = parser.add_mutually_exclusive_group()
group.add_argument("--parallel", type=int, nargs="?", const=4, default=4)
group.add_argument("--no-parallel", action="store_true")
```

**normalize：**

```python
parallel_workers = 0 if args.no_parallel else max(1, int(args.parallel or 4))
```

**`commands/ocr.py` dispatch：**

```python
result = run_derived_rebuild_for_keys(
    vault, keys,
    checkpoint_dir=checkpoint_dir,
    parallel=parallel_workers,
    progress_bar=progress_bar,
)
```

---

## Wave 2: 资产裁剪并行

### 2.1 设计约束

**不能重写坐标转换。** 当前 `_crop_asset_from_pdf()` 已经正确处理了 OCR bbox → PDF rect 缩放和 rotation。Wave 2 只负责并发调度，不重写裁剪算法。

```text
Object tasks should call existing _crop_asset_from_pdf() without shared pdf_doc_provider.
Preserve OCR bbox -> PDF rect conversion and rotation handling.
```

### 2.2 重构方案

```text
1. Serial: _build_object_tasks() — 创建目录、清理旧文件、构建 task list、预分配稳定 ID
2. Task executors:
     _write_figure_object_task(task)  → _crop_asset_from_pdf(pdf_doc=None, pdf_doc_provider=None)
     _write_table_object_task(task)   → _crop_asset_from_pdf(pdf_doc=None, pdf_doc_provider=None)
     _write_orphan_object_task(task)  → _crop_asset_from_pdf(pdf_doc=None, pdf_doc_provider=None)
3. Each task opens its own fitz.Document (not shared)
4. Parallel: ThreadPoolExecutor over tasks
```

### 2.3 调用方式

```python
was_cropped = _crop_asset_from_pdf(
    pdf_path=pdf_path,
    page_num=page,
    bbox=crop_bbox,
    dst=asset_path,
    page_width=page_width,
    page_height=page_height,
    page_cache_dir=threadsafe_page_cache_dir,
    pdf_doc=None,
    pdf_doc_provider=None,
    rotation_deg=rotation_deg,
)
```

### 2.4 Worker 数

```python
max_workers = min(2, os.cpu_count() or 4)
```

### 2.5 Thread-safe page cache

**接入点：** thread-safe helper 必须接入 `_crop_asset_from_pdf()` 内部，替换当前 page cache 分支。不能只写一个新函数但不被调用。

**Recommended：** 在 `_crop_asset_from_pdf()` 内部，将 page cache 写入替换为以下线程安全版本：

```python
_RENDER_LOCKS: dict[tuple[str, int], threading.Lock] = {}
_RENDER_LOCKS_GUARD = threading.Lock()

def _get_page_lock(cache_dir: Path, page_num: int) -> threading.Lock:
    key = (str(cache_dir.resolve()), page_num)
    with _RENDER_LOCKS_GUARD:
        if key not in _RENDER_LOCKS:
            _RENDER_LOCKS[key] = threading.Lock()
        return _RENDER_LOCKS[key]
```

**key 用 `(cache_dir, page_num)` 而不仅是 `page_num`**，防止同一进程中不同 cache 目录的 page 冲突。

**备选：** 如果接入成本高，并行 task 传 `page_cache_dir=None` 禁用共享缓存，代价是每次从头渲染。

### 2.6 Orphan 处理

串行预分配 ID，再并行裁剪：

```python
orphan_tasks = []
for i, orphan in enumerate(unmatched_assets):
    orphan_id = f"orphan_{page:03d}_{i:03d}"
    orphan_tasks.append((orphan, orphans_asset_dir / f"{orphan_id}.jpg",
                         figures_render_dir / f"{orphan_id}.md"))
```

---

## Wave 3: Maintenance 显示封装

### 3.1 当前真实字段

当前 `OCRMaintenanceRow` 字段：`status`, `health`, `version`, `can_redo`, `can_rebuild`, `error_stage`, `error_summary`, `degraded_reasons`, ...

当前 `_compute_display_fields()` 签名：

```python
def _compute_display_fields(
    status: str, health_overall: str, version: str,
    can_redo: bool, can_rebuild: bool,
    error_stage: str = "", error_summary: str = "",
    degraded_reasons: list[str] | None = None,
) -> dict:
```

### 3.2 改写 `OCRMaintenanceRow`

```python
@dataclass
class OCRMaintenanceRow:
    ...  # 现有字段不变

    def __post_init__(self):
        df = self.compute_display_fields(
            status=self.status, health_overall=self.health,
            version=self.version, can_redo=self.can_redo,
            can_rebuild=self.can_rebuild, error_stage=self.error_stage,
            error_summary=self.error_summary,
            degraded_reasons=self.degraded_reasons,
        )
        self.display_action = df["display_action"]
        self.display_label = df["display_label"]
        self.display_label_key = df.get("display_label_key", "")
        self.display_reason = df["display_reason"]
        self.display_reason_key = df.get("display_reason_key", "")
        self.display_group = df["display_group"]
        self.display_severity = df["display_severity"]
        self.visible_in_maintenance = df["visible_in_maintenance"]
        self.show_in_base = df["show_in_base"]

    @staticmethod
    def compute_display_fields(...) -> dict:
        """原 _compute_display_fields() 逻辑移入此处。"""
        ...
```

### 3.3 修改 `compute_maintenance_manifest()`

```python
df = OCRMaintenanceRow.compute_display_fields(
    status=status, health_overall=health_overall, version=version,
    can_redo=can_redo, can_rebuild=can_rebuild,
    error_stage=_error_stage(meta), error_summary=_error_summary(meta),
    degraded_reasons=health.get("degraded_reasons", []) or [],
)
```

### 3.4 删除或保留外部函数

- **推荐：** 保留兼容 wrapper `_compute_display_fields = OCRMaintenanceRow.compute_display_fields`
- 或：直接删除，同步更新 `tests/test_ocr_maintenance.py` 中所有 import 和调用

### 3.5 测试更新

```python
# tests/test_ocr_maintenance.py
# 原: from paperforge.worker.ocr_maintenance import _compute_display_fields
# 改: from paperforge.worker.ocr_maintenance import OCRMaintenanceRow
#     OCRMaintenanceRow.compute_display_fields(...)
```

---

## Wave 4: Embed 人类进度

### 4.1 当前状态

已有 stdout 机器协议：

```python
print(f"EMBED_START:{total}", flush=True)
for i, entry in enumerate(papers):
    ...
    print(f"EMBED_PROGRESS:{i}:{total}:{key}:{count}", flush=True)
print("EMBED_DONE", flush=True)
```

### 4.2 叠加 tqdm

**只包 iterable，不改变现有 `i += 1` 语义。** 当前 `i` 只在真正 embed 的 paper 递增（跳过 resume 已存在的）。

```python
from paperforge.worker._progress import progress_bar

use_tqdm = not getattr(args, "json", False)
papers_iter = progress_bar(papers, desc="Embedding", disable=not use_tqdm)

print(f"EMBED_START:{total}", flush=True)
i = 0
for entry in papers_iter:
    key = entry["key"]
    if resume and _already_embedded(...):
        continue
    chunks = chunker.chunk(entry["fulltext"])
    count = embed_paper(vault, key, chunks)
    i += 1
    print(f"EMBED_PROGRESS:{i}:{total}:{key}:{count}", flush=True)
print("EMBED_DONE", flush=True)
```

### 4.3 不变

- `embedding/builder.py` 不动
- `EMBED_*` stdout 协议完全保留
- 插件端不受影响

---

## Wave 5: CLI 文档补齐

### 5.1 从 `build_parser()` 逐项核对

运行 `python paperforge/cli.py --help` 获取完整命令树，逐项填入。

| 命令 | 用途 | 示例 |
|------|------|------|
| `ocr` | 运行 OCR | `paperforge ocr --key KEY` |
| `ocr rebuild` | 重新生成 derived 产物 | `paperforge ocr rebuild [KEY...] [--all] [--status done_degraded] [--parallel 4]` |
| `sync` | 同步 Zotero → Obsidian | `paperforge sync` |
| `content-discovery` | 全文内容检索 | `paperforge content-discovery <query>` |
| `scoped-fetch` | 按查询获取全文块 | `paperforge scoped-fetch <query> [--limit 5]` |
| `paper-navigation` | 论文结构导航 | `paperforge paper-navigation <query>` |
| `paper-lookup` | 模糊查找论文 | `paperforge paper-lookup <query>` |
| `reading-log` | 阅读日志操作 | `paperforge reading-log --lookup/--write/--render/--validate/--import` |
| `project-log` | 项目日志操作 | `paperforge project-log --write/--list/--render/--project/--payload` |
| `paper-status` | 论文状态摘要 | `paperforge paper-status <query>` |
| `agent-context` | Agent 上下文 | `paperforge agent-context <query>` |
| `runtime-health` | 运行时健康检查 | `paperforge runtime-health` |
| `embed build` | 构建向量索引 | `paperforge embed build [--force] [--resume]` |
| `embed status` | 向量索引状态 | `paperforge embed status` |
| `embed stop` | 停止向量构建 | `paperforge embed stop` |
| `status` | 全局状态 | `paperforge status` |
| `search` | 检索 | `paperforge search <query>` |

**所有示例必须从 `build_parser()` 实际参数核对，不要手写猜测。**

---

## 测试计划

| Wave | 测试 | 覆盖 |
|------|------|------|
| 1 | `_rebuild_one_paper()` | 成功、paper root 缺失、raw blocks 缺失 |
| 1 | `_run_parallel_rebuild()` | 3 papers → count=3；1/3 fail → count=2+1 error |
| 1 | `_filter_completed_keys()` | 有标记 → 过滤 |
| 1 | 已有 `test_ocr_rebuild` | 21 个全部通过（串行不退化） |
| 2 | `_write_figure_object_task()` | 坐标正确性（复用 `_crop_asset_from_pdf`） |
| 2 | `_get_page_lock()` 线程安全 | 并发同一页 → 不竞态 |
| 2 | 整体并行 | 3 figures → 全部产出 |
| 3 | 已有 `test_ocr_maintenance` | 28 个全部通过（行为不退化） |
| 3 | `OCRMaintenanceRow.compute_display_fields()` | 替换旧 `_compute_display_fields` import |
| 4 | stdout 抓取 | `EMBED_START / EMBED_PROGRESS / EMBED_DONE` 仍然存在 |
| 5 | `test_command_docs.py` | 更新（如果存在） |

Wave 1+2 并行 → review → Wave 3+4+5 并行 → review → 全量测试 → 合入 master。

重点审核：Wave 2 坐标安全、Wave 3 字段匹配、Wave 4 机器协议保留。
