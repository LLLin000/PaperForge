# Rebuild 加速与批量改进设计

> 设计讨论：2026-07-05
> 状态：设计稿（已审核，待实现）
> 审核结论：7.6/10 — A1/P0#1 先做，P0#2 和 embed 进度已按审核意见重写

## 设计目标

本设计解决一个核心问题和三个附带问题：

**核心问题**：rebuild 全串行，单线程逐个跑，CPU 空闲、I/O 空闲。大规模批量 rebuild（50+ 篇）耗时过长。

**附带问题**：
1. `run_derived_rebuild_for_keys()` 是 300 行内联编排，不可测试、不可插桩
2. rebuild 缺少并行完成进度；embed 已有 stdout 机器进度协议（`EMBED_START/EMBED_PROGRESS/EMBED_DONE`），但缺少面向终端用户的 human-readable tqdm
3. CLI 文档覆盖不全，用户不知道有哪些命令可用
4. Maintenance 显示逻辑在数据类外散布

## 范围

### 目标内

1. **跨论文并行**（P0#1）：`ProcessPoolExecutor` 驱动，默认 4 进程
2. **资产裁剪并行**（P0#2）：`ThreadPoolExecutor` 驱动，默认 2 线程/进程
3. **Rebuild 阶段化**（A1）：把 300 行内联编排拆成 `_rebuild_one_paper()` + 5 个阶段函数
4. **Rebuild 进度**：并行模式 `print [i/N] key — t秒` 到 stderr；串行保持 tqdm
5. **Embed 进度**：`commands/embed.py` 中在 stderr 叠加 tqdm，保留 `EMBED_START/EMBED_PROGRESS/EMBED_DONE` 机器协议
6. **Maintenance 显示封装**（A4）：`compute_display_fields()` 转为静态方法，`__post_init__` 和 `compute_maintenance_manifest()` 共享
7. **CLI 文档补齐**（B1）：`docs/COMMANDS.md` 覆盖全部 30+ 命令，名称从 `build_parser()` 逐项核对

### 非目标

- Figure passes 内部并行（pass 间依赖，收益不高，scope 太大）
- JSONL 增量写入（ponytail 标记但实际不是瓶颈）
- Section-aware chunking（B3，shipping 后做）
- Gateway 连接管理器（A2，代码味而非性能问题）
- CLI 导入体操（A3，值不值得做不确定）
- LanceBackend 实现/删除（A5，你说了放放）

## 设计决策

### 1. 跨论文并行（P0#1）

#### 1.1 Worker 数

默认为 4，不随 `os.cpu_count()` 变化。用户通过 `--parallel N` 自定义。

理由：rebuild 是 CPU + I/O 混合负载，4 进程 SSD I/O 争用可控。

#### 1.2 CLI 接口

```python
group = parser.add_mutually_exclusive_group()
group.add_argument("--parallel", type=int, nargs="?", const=4, default=4)
group.add_argument("--no-parallel", action="store_true")
```

**必须 normalize**：argparse 不会自动把 `--no-parallel` 和 `--parallel` 关联。如果只看 `args.parallel`，`--no-parallel` 时它仍然是默认值 `4`。

```python
parallel_workers = 0 if args.no_parallel else max(1, int(args.parallel or 4))
run_derived_rebuild_for_keys(..., parallel=parallel_workers)
```

| CLI | `args.parallel` | `args.no_parallel` | 实际 workers |
|-----|-----------------|-------------------|-------------|
| 默认 | 4 | False | 4 |
| `--parallel` | 4 | False | 4 |
| `--parallel 2` | 2 | False | 2 |
| `--no-parallel` | 4 | True | 0 / serial |

`parallel=0` 或 `parallel=False` 走串行路径。
    except Exception as e:
        # 注意：ocr_rebuild.py 当前没有 logger，需要补
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Rebuild failed for {key}: {e}")
        return {"key": key, "ok": False, "error": str(e), "rebuild_count": 0}


def _run_parallel_rebuild(vault, keys, workers, ...) -> dict:
    from concurrent.futures import ProcessPoolExecutor, as_completed
    import sys
    import time
    import logging

    logger = logging.getLogger(__name__)
    # checkpoint：主进程先扫描 .done.* 过滤已完成 keys
    cp_dir = checkpoint_dir
    if cp_dir:
        cp_dir.mkdir(parents=True, exist_ok=True)
        keys = _filter_completed_keys(keys, cp_dir)

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_rebuild_one_paper, vault, k): k for k in keys}
        rebuilt_count = 0
        errors = []
        start = time.monotonic()
        for i, f in enumerate(as_completed(futures), 1):
            key = futures[f]
            try:
                result = f.result()  # 业务异常已被 worker 内部捕获
            except Exception as exc:
                # 来自子进程 crash / unpicklable / OOM / BrokenProcessPool / KeyboardInterrupt
                logger.error(f"Parallel rebuild worker failed for {key}: {exc}")
                errors.append({"key": key, "ok": False, "error": repr(exc), "rebuild_count": 0})
                continue

            if result["ok"]:
                rebuilt_count += 1
                if cp_dir:
                    _write_done_marker(cp_dir, key)
            else:
                errors.append(result)

            total_elapsed = time.monotonic() - start
            print(f"[{i}/{len(keys)}] {key} — total {total_elapsed:.1f}s",
                  file=sys.stderr, flush=True)

        return {"rebuild_count": rebuilt_count, "errors": errors}
```

#### 1.4 Checkpoint 适配

并行时用 **独立目录**，不重用旧 JSON checkpoint 文件路径。

```python
# 旧：vault / "System" / "PaperForge" / ".ocr_rebuild_checkpoint.json"
# 新：vault / "System" / "PaperForge" / ".ocr_rebuild_checkpoint" /  (目录)

# 主进程写标记：worker 只返回 result，主进程确认 ok 后写 .done.<key>
def _write_done_marker(checkpoint_dir: Path, key: str):
    (checkpoint_dir / f".done.{key}").write_text("", encoding="utf-8")

# 主进程侧：扫描过滤
def _filter_completed_keys(keys: list[str], checkpoint_dir: Path) -> list[str]:
    done = set()
    if checkpoint_dir.exists():
        for f in checkpoint_dir.iterdir():
            if f.name.startswith(".done."):
                done.add(f.name[len(".done."):])
    return [k for k in keys if k not in done]
```

CLI resume 逻辑同步改为读 `.done.*` 文件，不再读旧 JSON。

#### 1.5 日志

补 `logging.getLogger(__name__)`。

```python
import logging
logger = logging.getLogger(__name__)
```

并行模式下子进程 stderr 通过 ProcessPoolExecutor 管道自动合并到主进程，无需特殊处理。

#### 1.6 进度输出到 stderr

```python
print(f"[{i}/{len(keys)}] {key} — total {total_elapsed:.1f}s",
      file=sys.stderr, flush=True)
```

避免污染 `--json` 输出。

### 2. 资产裁剪并行（P0#2）

审核意见：**不能共享 fitz.Document 并宣称线程安全。** 本方案已重写。

#### 2.1 Worker 数

`min(2, os.cpu_count())`。不暴露 CLI。

#### 2.2 核心约束

1. **不能共享 fitz.Document**：避免多线程并发访问同一个 PDF 文件的竞态
2. **页面缓存写入用临时文件 + atomic replace**：避免读到半成品缓存
3. **Orphan ID 串行预分配**：在提交 futures 之前确定所有输出路径

#### 2.3 实现方式

```python
def extract_and_write_objects(
    pdf_path, figure_inventory, table_inventory,
    asset_root, render_root, ...,
):
    import os
    from concurrent.futures import ThreadPoolExecutor, as_completed

    max_workers = min(2, os.cpu_count() or 4)

    # 串行阶段：目录创建、清理旧文件 → 安全，不做线程中
    _prepare_directories(...)

    # 串行预构建 task list，确定所有稳定 ID
    tasks: list[Callable] = []

    for match in figure_inventory.get("matched_figures", []):
        fig_id = _resolve_figure_id(match)          # 稳定 ID
        asset_path = figures_asset_dir / f"{fig_id}.jpg"
        render_path = figures_render_dir / f"{fig_id}.md"
        tasks.append(
            lambda m=match: _crop_one_figure(m, pdf_path, asset_path, render_path, ...)
        )

    for table in table_inventory.get("tables", []):
        tbl_id = _resolve_table_id(table)            # 稳定 ID
        asset_path = tables_asset_dir / f"{tbl_id}.jpg"
        render_path = tables_render_dir / f"{tbl_id}.md"
        tasks.append(
            lambda t=table: _crop_one_table(t, pdf_path, asset_path, render_path, ...)
        )

    # 并行裁剪：每个 task 自己打开 fitz.Document
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(t) for t in tasks]
        for f in as_completed(futures):
            f.result()  # 让异常透出
```

#### 2.4 页面缓存 atomic write

```python
_RENDER_LOCKS: dict[int, threading.Lock] = {}

def _render_page_cached(doc_path: Path, page_num: int, cache_dir: Path) -> Path | None:
    """线程安全页面渲染：每个 page 独立锁 + 临时文件 atomic replace。"""
    lock = _RENDER_LOCKS.setdefault(page_num, threading.Lock())
    cache_path = cache_dir / f"page_{page_num:03d}.jpg"

    if cache_path.exists():
        return cache_path

    with lock:
        # double-check: 另一个线程可能已经写完
        if cache_path.exists():
            return cache_path

        import fitz
        doc = fitz.open(str(doc_path))
        try:
            page = doc[page_num - 1]
            pix = page.get_pixmap(dpi=200)
            # 写临时文件 → atomic replace
            tmp = cache_path.with_suffix(".tmp.jpg")
            pix.save(str(tmp))
            tmp.replace(cache_path)
            return cache_path
        finally:
            doc.close()
```

#### 2.5 每个 crop task 打开自己的 PDF

```python
def _crop_one_figure(match, pdf_path, asset_path, render_path, ...):
    import fitz

    doc = fitz.open(str(pdf_path))
    try:
        page = doc[page_num - 1]
        pix = page.get_pixmap(clip=bbox, dpi=200)
        tmp = asset_path.with_suffix(".tmp.jpg")
        pix.save(str(tmp))
        tmp.replace(asset_path)
    finally:
        doc.close()

    md = render_figure_object_markdown(...)
    md_tmp = render_path.with_suffix(".tmp.md")
    md_tmp.write_text(md)
    md_tmp.replace(render_path)

    return True
```

### 3. Rebuild 阶段化（A1）

#### 3.1 拆函数

`_rebuild_one_paper()` 内部拆成 5 个阶段函数：

```python
# Phase 1: Span
meta = _phase_span(raw_blocks, artifacts, meta, vault, key, source_pdf_path)
page_pdf_lines = extract_pdf_lines_normalized(source_pdf_path)

# Phase 2: Structure + Metadata
structured, doc_structure, resolved = _phase_structure(
    raw_blocks, source_meta, artifacts, vault, key
)

# Phase 3: Figures + Tables + Objects
figure_inventory, table_inventory = _phase_figures_tables(
    structured, page_pdf_lines, source_pdf_path, artifacts
)

# Phase 4: Render + Health
markdown = _phase_render(structured, resolved, figure_inventory, table_inventory,
                          doc_structure, reader_payload, meta)

# Phase 5: Index + Meta
_phase_index_and_meta(structured, resolved, markdown, meta, meta_patches,
                       artifacts, paper_root, vault, key)
```

#### 3.2 必须保护的顺序

**审核意见：不能重排 figure/table 管道顺序。** 以下顺序是代码注释明确要求的：

```text
1. build_figure_inventory()
2. write_back_figure_roles()
3. residual_author_bio_pass() + post_ref_bio_cleanup()
4. synthesize_reader_figures()
5. build_table_inventory()
6. resolve_media_asset_conflicts()
7. attach_ownership_conflicts()
8. apply_object_writebacks()         ← 必须在 write_figure_inventory 之前
9. write_figure_inventory()
10. write_back_table_roles()
11. write_table_inventory()
12. write_structured_blocks_jsonl()
13. extract_and_write_objects()
```

### 4. Rebuild 进度

- 串行模式：现有 `progress_bar`（tqdm）不变
- 并行模式：`as_completed` + `print(f"[{i}/{n}] {key} — total {elapsed:.1f}s", file=sys.stderr)`
- `--json` 时禁用人类进度

### 5. Embed 进度

**审核意见：原来 spec 写错位置。** 当前 embed build 循环不在 `embedding/builder.py`，在 `commands/embed.py`。

当前已有机器进度协议（`EMBED_START / EMBED_PROGRESS / EMBED_DONE`）到 stdout，插件端依赖它们。

正确方案：

```python
# commands/embed.py — 在现有机器协议之上叠加人类进度

from paperforge.worker._progress import progress_bar

def run_embed(vault, papers, ...):
    total = len(papers)
    print(f"EMBED_START:{total}", flush=True)       # 保留机器协议

    for i, paper in enumerate(progress_bar(papers, desc="Embedding", disable=args.json)):
        key = paper["key"]
        chunks = chunker.chunk(paper["fulltext"])
        count = embed_paper(vault, key, chunks)
        print(f"EMBED_PROGRESS:{i+1}:{total}:{key}:{count}", flush=True)  # 保留机器协议

    print("EMBED_DONE", flush=True)                  # 保留机器协议
```

改动范围：
- `commands/embed.py`：加 tqdm 到 stderr，受 `--json` 开关控制
- `embedding/builder.py`：不动
- 机器输出协议：不变

### 6. Maintenance 显示封装（A4）

**审核意见：不能直接删除 `_compute_display_fields()`，`compute_maintenance_manifest()` 也在用它。**

正确方案：

```python
@dataclass
class OCRMaintenanceRow:
    ...

    def __post_init__(self):
        df = self.compute_display_fields(...)
        self.display_action = df["display_action"]
        self.display_label = df["display_label"]
        self.display_severity = df["display_severity"]
        self.display_group = df["display_group"]
        self.visible_in_maintenance = df["visible_in_maintenance"]
        self.show_in_base = df["show_in_base"]

    @staticmethod
    def compute_display_fields(...) -> dict:
        """和 compute_maintenance_manifest() 共享的静态方法。"""
        ...  # 现有 10-clause if-elif 逻辑
```

改动：
- `compute_display_fields()` 转为 `@staticmethod`，签名不变
- `OCRMaintenanceRow.__post_init__()` 调用 `compute_display_fields()`
- `compute_maintenance_manifest()` 也调用 `OCRMaintenanceRow.compute_display_fields()`
- 外部独立函数 `_compute_display_fields()` 删除

说明：本次只封装 display fields。`fulltext_drift_state` 等字段保持构造后赋值，不在此次改动范围内。

### 7. CLI 文档补齐（B1）

**审核意见：命令名必须从实际 `build_parser()` 逐项核对。** 以下是当前实际命令名（非猜测）：

| 命令 | 实际 CLI 示例 | 文档状态 |
|------|-------------|---------|
| 运行 OCR | `paperforge ocr --key KEY` | 已有 |
| 重建 derived | `paperforge ocr rebuild [KEY...] [--all] [--status ...] [--parallel N]` | 需补 |
| 同步 | `paperforge sync` | 已有 |
| 状态 | `paperforge status` | 已有 |
| 检索 | `paperforge search <query>` | 已有 |
| 内容发现 | `paperforge content-discovery <query>` | 需补 |
| 范围获取 | `paperforge scoped-fetch <paper>` | 需补 |
| 论文导航 | `paperforge paper-navigation <query>` | 需补 |
| 论文查找 | `paperforge paper-lookup <query>` | 需补 |
| 阅读日志 | `paperforge reading-log --lookup/--write/--render/--validate/--import` | 需补 |
| 项目日志 | `paperforge project-log --write/--list/--render/--project/--payload` | 需补 |
| 论文状态 | `paperforge paper-status <query>` | 需补 |
| Agent 上下文 | `paperforge agent-context <query>` | 需补 |
| 运行时健康 | `paperforge runtime-health` | 需补 |
| 嵌入构建 | `paperforge embed build [--force] [--resume]` | 需补 |
| 嵌入状态 | `paperforge embed status` | 需补 |
| 停止嵌入 | `paperforge embed stop` | 需补 |
| 说明 | 以上 CLI 示例必须从 `build_parser()` 逐项核对，不要手写猜测命令名 | — |

文档格式：每命令一行用途 + 实际 CLI 示例（从 parser real_defaults 验证）。

## 非功能约束

| 属性 | 目标 |
|------|------|
| 向后兼容 | 串行路径行为 0 变化 |
| 并行下性能 | 40 篇 paper ≥ 2x 串行（**目标，非保证**；无 profiler 数据） |
| 内存 | 默认 4 workers 应在笔记本内存可承受范围内；后续用 40-paper benchmark 实测后考虑提高默认值 |
| 错误隔离 | 单篇失败不阻止其他论文；主进程 try/except f.result() 兜底 |
| 测试 | 每阶段函数独立测试 + 串行/并行路径 smoke test |

## 设计决策明细

| # | 决策 | 理由 |
|---|------|------|
| D1 | `max_workers=4` 固定值 | I/O 争用受限，非纯 CPU 密集 |
| D2 | 并行默认开 | 用户预期 "rebuild 就是快的" |
| D3 | CLI `--parallel`/`--no-parallel` 互斥组 | 语义最清晰 |
| D4 | `_rebuild_one_paper()` 返回 dict，业务异常已内部捕获 | 隔离异常传递 |
| D5 | **主进程仍 try/except f.result()** | 子进程 crash/unpicklable/OOM 无法内部拦截 |
| D6 | 独立 checkpoint_dir + `.done.<key>` 标记 | 零库依赖，零竞态 |
| D7 | 每个 crop task 打开自己的 fitz.Document | **审核后修正**：避免共享 PDF 的线程安全风险 |
| D8 | 页面缓存用 per-page 锁 + atomic replace | **审核后修正**：避免读到半成品缓存 |
| D9 | orphan/table ID 串行预分配后再并行 | 避免并行递增计数器 |
| D10 | rebuild 和 embed 进度各自独立策略 | rebuild 用 as_completed 打印；embed 保持机器协议 + tqdm |
| D11 | `compute_display_fields()` 转为 `@staticmethod` | 同时被 `__post_init__` 和 `compute_maintenance_manifest()` 调用 |
| D12 | CLI 文档从 `build_parser()` 逐项核对 | 避免手写错误命令名 |
| D13 | embed 进度改 `commands/embed.py`，不动 `embedding/builder.py` | **审核后修正**：真正 build loop 在 commands 层 |
| D14 | 保留 `EMBED_START/EMBED_PROGRESS/EMBED_DONE` stdout 协议 | 插件端依赖此协议 |
