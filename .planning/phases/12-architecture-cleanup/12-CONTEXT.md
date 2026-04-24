# Phase 12: Architecture Cleanup - Context

**Gathered:** 2026-04-24  
**Status:** Ready for planning  
**Base Commit:** 4297dcd  

---

## Phase Boundary

**Goal:** 修复模块边界泄漏（pipeline/ 和 skills/ 在 paperforge/ 包外），消除测试死区。

**Scope:**
- 拆分 `pipeline/worker/scripts/literature_pipeline.py`（2900+ 行）为 `paperforge/worker/` 子模块
- 迁移 `skills/literature-qa/` → `paperforge/skills/literature-qa/`
- 提取 base_views 函数到独立模块
- 修复所有导入路径（commands/, tests/, scripts/）
- 更新文档引用

**Out of Scope:**
- Repair scan 性能优化
- CI 集成
- 功能变更（仅移动和重构，不修改行为）

---

## Canonical References

### Source Files to Migrate

| Current Path | Target Path | Contents |
|-------------|------------|----------|
| `pipeline/worker/scripts/literature_pipeline.py` | `paperforge/worker/sync.py` | selection-sync, index-refresh |
| | `paperforge/worker/ocr.py` | OCR runner, meta validation |
| | `paperforge/worker/repair.py` | run_repair, divergence detection |
| | `paperforge/worker/status.py` | System status checks |
| | `paperforge/worker/base_views.py` | build_base_views, merge_base_views, ensure_base_views |
| | `paperforge/worker/deep_reading.py` | scan_deep_reading_queue, prepare_deep_reading |
| | `paperforge/worker/__init__.py` | Package exports |
| `pipeline/worker/scripts/__init__.py` | `paperforge/worker/__init__.py` | (合并) |
| `skills/literature-qa/scripts/ld_deep.py` | `paperforge/skills/literature-qa/scripts/ld_deep.py` | Deep reading script |
| `skills/literature-qa/prompt_deep_subagent.md` | `paperforge/skills/literature-qa/prompt_deep_subagent.md` | Prompt template |
| `skills/literature-qa/chart-reading/` | `paperforge/skills/literature-qa/chart-reading/` | Chart guides |

### Import Path Changes

| Old Import | New Import |
|-----------|-----------|
| `from pipeline.worker.scripts.literature_pipeline import load_export_rows` | `from paperforge.worker.sync import load_export_rows` |
| `from pipeline.worker.scripts.literature_pipeline import run_ocr` | `from paperforge.worker.ocr import run_ocr` |
| `from pipeline.worker.scripts.literature_pipeline import run_repair` | `from paperforge.worker.repair import run_repair` |
| `from pipeline.worker.scripts.literature_pipeline import run_doctor` | `from paperforge.worker.status import run_doctor` |
| `from pipeline.worker.scripts.literature_pipeline import build_base_views` | `from paperforge.worker.base_views import build_base_views` |
| `from skills.literature_qa.scripts.ld_deep import main` | `from paperforge.skills.literature_qa.scripts.ld_deep import main` |

### Files Requiring Import Updates

- `paperforge/commands/sync.py` — uses load_export_rows, run_selection_sync
- `paperforge/commands/ocr.py` — uses run_ocr
- `paperforge/commands/repair.py` — uses run_repair
- `paperforge/commands/status.py` — uses run_doctor
- `paperforge/commands/deep.py` — uses scan_deep_reading_queue
- `paperforge/cli.py` — imports from commands/
- `tests/test_*.py` — 多个测试文件
- `scripts/setup.py` — 可能引用
- `setup_wizard.py` — 可能引用

---

## Current State

### Test Results (Pre-Phase 12)
```
203 passed, 2 skipped, 0 failed
```

### Directory Structure (Problematic)
```
paperforge/                 # Main package
├── __init__.py
├── cli.py
├── commands/               # Phase 9 重构（良好）
│   ├── __init__.py
│   ├── sync.py
│   ├── ocr.py
│   ├── repair.py
│   ├── status.py
│   └── deep.py
├── config.py
├── ocr_diagnostics.py
├── pdf_resolver.py
└── ...

pipeline/                   # 外部模块（问题）
└── worker/
    └── scripts/
        ├── __init__.py
        └── literature_pipeline.py   # 2900+ 行

skills/                     # 外部目录（问题）
└── literature-qa/
    ├── scripts/
    │   └── ld_deep.py
    ├── prompt_deep_subagent.md
    └── chart-reading/
```

---

## Decisions

| ID | Decision | Rationale |
|--|---------|-----------|
| D-01 | Pipeline 完全重构到 `paperforge/worker/` | 与 commands/ 结构对齐，消除跨目录导入 |
| D-02 | Skills 保留子目录结构迁移 | 配套资源需要子目录，与 commands/ 模式一致 |
| D-03 | Base views 提取到独立模块 | 完全模块化标准，易于独立测试 |
| D-04 | Test 失败已由 Phase 11 修复 | 无需额外操作 |
| D-05 | Phase 12 专注架构清理 | 不包含性能优化或 CI 集成 |
