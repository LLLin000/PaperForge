# Real OCR payloads (copied verbatim)

These are **real** `json/result.json` payloads from a production vault
(`D:/L/OB/Literature-hub/System/PaperForge/ocr`), copied so the test suite
exercises the shape PaddleOCR actually returns rather than one we invented.

## Why they are here

`tests/sandbox/ocr-complete/TSTONE001` is a hand-written stub whose
`result.json` is `{"pages": [{"markdown", "page_num"}]}`. Production returns a
**list of per-page PaddleOCR responses** (`dataInfo`, `layoutParsingResults`,
`preprocessedImages`). A regression built on the stub therefore verified a shape
that never occurs, and the difference produced a false defect report (#219:
"the legacy backfill downgrades a paper") that could not be reproduced against
any of the 950 real papers.

## Contents

| Directory | Source key | `result.json` entries | `meta.page_count` |
|---|---|---|---|
| `63EYTG95` | 63EYTG95 | 1 | 1 |
| `8LZUYXMH` | 8LZUYXMH | 2 | 5 |

The second one is deliberate: the entry count and `page_count` differ there, so
a test that assumes "one json entry per page" fails loudly instead of passing by
luck.

## What was changed, and why

- `meta.json` has `raw_version` / `derived_version` removed, which is exactly
  the legacy condition (`worker/ocr_versions.py:classify_legacy_ocr_state`:
  `ocr_status == "done"` with no version state) that routes a paper through
  `backfill_from_result`.
- Machine-local paths (`source_pdf`, `pdf_path`, `*_path`) are replaced with
  `<scrubbed>`: they name this machine's storage layout, not literature content.

Nothing else is altered — the OCR payloads are byte-for-byte as produced, which
is the point.

## Provenance and licensing

These are OCR text of published journal articles. They are vendored for shape
fidelity in tests only; the repository is public, so treat this as a deliberate,
reviewed redistribution decision rather than a neutral test-data choice.
