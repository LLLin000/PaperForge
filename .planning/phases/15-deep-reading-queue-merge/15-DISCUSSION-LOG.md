# Phase 15: Deep-Reading Queue Merge - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-27
**Phase:** 15-deep-reading-queue-merge
**Areas discussed:** Function signature & return value, Status sync separation, ld_deep.py import strategy

---

## Function Signature & Return Value

| Option | Description | Selected |
|--------|-------------|----------|
| 纯数据获取，返回完整列表 (Recommended) | 不分类，不同步状态。返回所有 library records + OCR 状态的统一数据。Caller 自行过滤。 | ✓ |
| 顺便做分类 | 直接返回 ready/waiting/blocked 三组，和 deep_reading.py 当前行为一致。 | |

**User's choice:** 纯数据获取，返回完整列表
**Notes:** scan_library_records() returns a flat list of dicts with zotero_key, domain, title, analyze, do_ocr, deep_reading_status, ocr_status, note_path.

---

## Status Sync Separation

| Option | Description | Selected |
|--------|-------------|----------|
| 同意，只提取扫描 (Recommended) | scan_library_records() 纯获取数据。run_deep_reading() 用返回数据做同步+报告。 | ✓ |
| 同步也一起提取 | 但 _utils.py 应该保持纯函数，同步是副作用操作。 | |

**User's choice:** 同意，只提取扫描
**Notes:** run_deep_reading() retains status sync + report generation. Only the scanning logic is extracted.

---

## ld_deep.py Import Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| 模块级直接导入 (Recommended) | from paperforge.worker._utils import scan_library_records | ✓ |
| 函数级延迟导入 | 在 scan_deep_reading_queue() 内部 import，更保守 | |

**User's choice:** 模块级直接导入
**Notes:** Same pattern as existing paperforge.config imports.

---

## the agent's Discretion

- Exact error handling for malformed frontmatter (keep current lenient regex approach)
- Sorting of returned list (caller's concern, not shared function's)
- Whether to include `do_ocr` field in return dict

## Deferred Ideas

- Dead code removal / unused imports -- Phase 17
- Unit tests for scan_library_records() -- Phase 19
