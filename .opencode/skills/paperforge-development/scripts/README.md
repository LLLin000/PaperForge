# Scripts

- `ocr_truth_audit.py` stages OCR audit artifacts and writes deterministic helper summaries under `audit/<paper_key>/`.
- It requires an explicit external OCR root via `--source-root` or `PAPERFORGE_OCR_ROOT`.
- It is developer-only and separate from `scripts/dev/` so the repo-local `paperforge-development` skill can evolve without touching the PaperForge product workflow.
