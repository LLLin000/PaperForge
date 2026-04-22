# /lp-selection-sync

同步 Zotero Better BibTeX JSON 导出到 library-records。

## Command

先读取 Vault 根目录的 `paperforge.json`，用其中的 `system_dir` 拼出 worker 路径，再运行：

```bash
python <system_dir>/PaperForge/worker/scripts/literature_pipeline.py --vault . selection-sync
```
