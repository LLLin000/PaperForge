# Defect Research: PaperForge Lite

**Reviewed inputs:** release repo source, fuller local `LiteraturePipeline` structure, and Obsidian Base files in `D:\L\Med\Research\05_Bases`.

## High-Risk Defects

| Area | Evidence | Risk | Direction |
|------|----------|------|-----------|
| PaddleOCR auth and endpoint | `run_ocr()` posts to `PADDLEOCR_JOB_URL` with `Authorization: bearer <token>` but no preflight or credential format validation | User can enter key and URL yet receive opaque `PaddleOCR request failed` or jobs stuck in non-actionable states | Add `ocr doctor` that validates env, URL shape, auth header, and a lightweight request path before queue mutation |
| PDF path resolution | OCR uses `with open(queue_row['pdf_path'], 'rb')` directly | Better BibTeX/Zotero attachment paths may be absolute, vault-relative, linked-file, or storage-relative; direct open is brittle | Add `resolve_pdf_path(vault, cfg, raw_path)` with explicit diagnostics |
| Blocked/error recovery | `sync_ocr_queue()` skips `blocked`, and `cleanup_blocked_ocr_dirs()` removes only blocked dirs without payload | A transient missing token/path can leave records excluded until manual cleanup/reset | Add reset command and allow retry when config/path issue is fixed |
| Base generation | `write_base_file()` emits minimal generic views; real Base files contain workflow-specific views | New users get weaker control UX than the working vault | Promote production views into config-aware templates |
| Hardcoded Base filters | Production Bases filter `03_Resources/...` | Custom `resources_dir`/`control_dir` breaks generated or copied views | Render filters from `paperforge.json` values |
| Placeholder commands | command docs say read `paperforge.json`, then run `python <system_dir>/...` | User still relies on agent/manual substitution | Provide `paperforge` command or `python -m paperforge_lite` entrypoint |
| Validation depth | `validate_setup.py` checks presence of keys, not whether token/url work or folders are writable | Install can appear valid while OCR cannot run | Add runtime validation categories: config, paths, zotero, bbt export, ocr auth, ocr queue |

## PaddleOCR Failure Hypotheses

1. **Wrong token variable or token type**: setup writes `PADDLEOCR_API_TOKEN`; users may paste an API key requiring a different auth scheme or prefix.
2. **Endpoint mismatch**: default URL may not match the current PaddleOCR service endpoint or account region.
3. **Header casing/scheme mismatch**: code uses `bearer` lowercase; many services accept it, but not all integrations do.
4. **File path failure masked as OCR failure**: if `pdf_path` is not directly openable, the user may interpret the OCR run as PaddleOCR misconfiguration.
5. **Queue state inertia**: once a record is `blocked`/`error`, subsequent config corrections do not always lead to obvious retry behavior.
6. **Async polling contract mismatch**: code assumes `response.json()['data']['jobId']`, `payload['state']`, and `resultUrl['jsonUrl']`; any API schema change will fail without a targeted message.

## Path Configuration Direction

PaperForge should use a deterministic configuration hierarchy:

1. CLI flags: `--vault`, `--config`, optional `--system-dir` overrides.
2. Environment variables: `PAPERFORGE_VAULT`, `PAPERFORGE_SYSTEM_DIR`, `PAPERFORGE_RESOURCES_DIR`, `PAPERFORGE_LITERATURE_DIR`, `PAPERFORGE_CONTROL_DIR`, `PAPERFORGE_BASE_DIR`.
3. Vault `paperforge.json`.
4. Defaults.

The user-facing command should be stable:

```powershell
paperforge status
paperforge selection-sync
paperforge index-refresh
paperforge ocr doctor
paperforge ocr run
paperforge deep-reading
paperforge paths
```

The legacy worker path can remain supported, but documentation should stop requiring users to hand-fill placeholders.
