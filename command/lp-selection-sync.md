# /lp-selection-sync

同步 Zotero Better BibTeX JSON 导出到 library-records。

## Command

```bash
paperforge selection-sync
```

## 说明

`paperforge selection-sync` 会自动读取 `paperforge.json` 定位 exports 目录和 control 目录。
如需使用 Python 直接调用（备选方式）：

```bash
python $(paperforge paths --json | python -c "import json,sys; print(json.load(sys.stdin)['worker_script'])") --vault . selection-sync
```
