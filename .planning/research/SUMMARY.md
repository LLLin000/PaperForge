# Research Summary

PaperForge Lite is close to a usable local release, but the full flow is not yet self-healing or self-explanatory enough for new users. The strongest existing pieces are the worker/agent separation, metadata-based queue model, and real-world Obsidian Base workflow. The weak pieces are install-to-first-run guidance, OCR diagnostics, path resolution, and config-aware generated Base files.

The main release strategy should be to add a small CLI/launcher layer and a robust configuration resolver before deeper feature work. This lets every command resolve the user’s custom vault directories without agent intervention, while keeping the existing `literature_pipeline.py` worker intact. PaddleOCR should be hardened through a preflight doctor, clearer state transitions, retry/reset commands, and better PDF path resolution.

Base generation should copy the structure of `骨科.base`, `运动医学.base`, and `Literature Hub.base`: overview, recommended analysis, pending OCR, completed OCR, pending deep reading, completed deep reading, and formal cards. These templates must render directory filters from `paperforge.json` instead of hardcoding `03_Resources`.

The first milestone should not broaden PaperForge. It should make the promised Lite path reliable: install, configure, sync, generate notes, OCR one PDF, inspect queue, and prepare `/LD-deep`.
