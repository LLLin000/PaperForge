# /lp-index-refresh

根据 library-records 和 Zotero JSON 导出生成正式文献笔记。

## Command

```bash
paperforge index-refresh
```

## 说明

`paperforge index-refresh` 会自动读取 `paperforge.json` 定位各目录。
如需使用 Python 直接调用（备选方式）：

```bash
python $(paperforge paths --json | python -c "import json,sys; print(json.load(sys.stdin)['worker_script'])") --vault . index-refresh
```
