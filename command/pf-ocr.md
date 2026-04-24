# /pf-ocr

处理 library-records 中 `do_ocr: true` 的 PDF OCR 队列。

## Command

```bash
paperforge ocr
```

## 说明

`paperforge ocr` 会自动读取 `paperforge.json` 定位 ocr 目录和 worker 脚本，运行 OCR 并自动诊断结果。

如需使用 Python 直接调用（备选方式）：

```bash
python -m paperforge ocr --vault .
```

### 常用选项

| 选项 | 说明 |
|------|------|
| `--diagnose` | 仅诊断配置，不上传 PDF |
| `--key <KEY>` | 仅处理指定 Zotero key 的文献 |
| `--vault <PATH>` | 指定 Vault 根目录（默认当前目录） |

### 诊断模式

Validate OCR configuration before queueing jobs:

```bash
paperforge ocr --diagnose
```

Run full diagnostics including live PDF test:

```bash
paperforge ocr --diagnose --live
```

### Diagnostic Levels

| Level | Check | Failure Meaning |
|-------|-------|-----------------|
| L1 | API token presence | `PADDLEOCR_API_TOKEN` missing or empty |
| L2 | URL reachability | Cannot connect to PaddleOCR service |
| L3 | API schema validation | Service reachable but response format unexpected |
| L4 | Live PDF round-trip | Full submission and result retrieval fails |

Exit code `0` = all checks passed. Exit code `1` = at least one check failed.
