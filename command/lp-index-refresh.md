# /lp-index-refresh

根据 library-records 和 Zotero JSON 导出生成正式文献笔记。

## Command

先读取 Vault 根目录的 `paperforge.json`，用其中的 `system_dir` 拼出 worker 路径，再运行：

```bash
python <system_dir>/PaperForge/worker/scripts/literature_pipeline.py --vault . index-refresh
```
