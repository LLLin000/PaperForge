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
