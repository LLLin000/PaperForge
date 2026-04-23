# /lp-ocr

处理 library-records 中 `do_ocr: true` 的 PDF OCR 队列。

## Command

```bash
paperforge ocr run
```

## 说明

`paperforge ocr run` 会自动读取 `paperforge.json` 定位 ocr 目录和 worker 脚本。
如需使用 Python 直接调用（备选方式）：

```bash
python $(paperforge paths --json | python -c "import json,sys; print(json.load(sys.stdin)['worker_script'])") --vault . ocr
```

## OCR Doctor

Validate OCR configuration before queueing jobs:

```bash
paperforge ocr doctor
```

Run full diagnostics including live PDF test:

```bash
paperforge ocr doctor --live
```

### Diagnostic Levels

| Level | Check | Failure Meaning |
|-------|-------|-----------------|
| L1 | API token presence | `PADDLEOCR_API_TOKEN` missing or empty |
| L2 | URL reachability | Cannot connect to PaddleOCR service |
| L3 | API schema validation | Service reachable but response format unexpected |
| L4 | Live PDF round-trip | Full submission and result retrieval fails |

Exit code `0` = all checks passed. Exit code `1` = at least one check failed.
