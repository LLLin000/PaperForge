# Phase 16: Retry + Progress Bars - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-27
**Phase:** 16-retry-progress-bars
**Areas discussed:** tenacity placement, tqdm placement, --no-progress flag scope, poll error handling

---

## tenacity 放置位置

| Option | Description | Selected |
|--------|-------------|----------|
| 新建 _retry.py (推荐) | 保持 _utils.py leaf 纯净，_retry.py 只 import tenacity + stdlib | ✓ |
| inline 在 ocr.py | 最简单，目前就一个调用点 | |
| 放 _utils.py | 最方便，但打破 leaf module 约束 | |

**User's choice:** 新建 _retry.py
**Notes:** 和 _utils.py 保持同样 leaf 模式，只 import tenacity + stdlib

---

## tqdm 放置位置

| Option | Description | Selected |
|--------|-------------|----------|
| 新建 _progress.py (推荐) | 封装 progress_bar() 函数，保持 _utils.py 纯 leaf | ✓ |
| inline 在 ocr.py | 最简单，目前就 OCR upload 循环用 | |
| 放 _utils.py | 全模块引入 tqdm 依赖 | |

**User's choice:** 新建 _progress.py
**Notes:** 统一 tqdm 配置（stderr, auto-disable），和 _retry.py 一致的模式

---

## --no-progress 全局还是 per-command？

| Option | Description | Selected |
|--------|-------------|----------|
| 全局 root flag (推荐) | 和 --verbose 一致，未来自动生效 | ✓ |
| 仅 per-command | 目前只有 ocr 用，但和 --verbose 不一致 | |

**User's choice:** 全局 root flag
**Notes:** 与 Phase 13 的 --verbose 使用体验一致

---

## Poll HTTP 5xx 错误要不要修？

| Option | Description | Selected |
|--------|-------------|----------|
| 修，batch resilience (推荐) | 把 poll 的 raise_for_status 也包进 try/except | ✓ |
| 不修，poll fail-fast | upload 可以重试，poll 失败快速失败 | |

**User's choice:** 修，batch resilience
**Notes:** 符合 REL-04 精神，单个请求失败不 crash 整个 batch

---

## Deferred Ideas

- OBS-05 (OCR error message improvement) — Phase 17
- E2E tests for retry behavior — Phase 19
