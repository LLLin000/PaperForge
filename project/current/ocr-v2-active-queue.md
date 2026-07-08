# OCR-v2 Active Queue
> Status: Embedding pipeline overhaul complete. PR9A-C all merged to `master`.
> Last updated: 2026-07-08

## Completed (this session)

### PR9A: Resume & Rebuild Correctness
- OCR rebuild `--all`: version/artifact-based selection via `_needs_derived_rebuild()`
- `--status` and explicit keys: manual override, no version filter
- `.done.{key}` checkpoint markers removed from selection
- `_apply_post_rebuild_version_flags` now writes `derived_version`
- Embed resume entry: three-gate protection (stale state / missing DB / corrupt DB)
- `_pid_alive()` cross-platform PID health check
- 14 regression tests

### PR9B: Embed Parallel Encode
- Four dataclasses: `EmbeddingPayload`, `EncodedPayload`, `PaperEmbeddingJob`, `PaperEncodedBundle`
- `prepare_legacy/body/object_payload` — prepare phase extraction
- `encode_payload` / `encode_paper_job` — worker-thread-safe encode
- `write_encoded_payload` — ChromaDB serial write
- Existing `embed_body_units`/`embed_paper` refactored as wrappers
- 23 regression tests

### Provider Fix
- Switched `OpenAICompatibleProvider` from `openai` client to `requests`
- Fixed SiliconFlow NAT connection hang (openai-python#3269)
- 0.3s vs 2.3s init, no more hanging

### PR9C: Streaming Embed Pipeline
- Sliding-window pipeline: prepare + submit bounded in-flight papers
- `wait(FIRST_COMPLETED)` in main thread for encode results
- `processed_count` = skip + embedded, monotonic EMBED_PROGRESS
- Resume skip and no-payload paths also advance processed_count
- Encode failure fails closed (return 1, no silent skip)
- `write_vector_build_state` fallback when file locked (Windows)
- 4 integration tests

### Plugin Fixes
- Status text shows total chunks across all three collections
- "chunks embedded" text below progress bar also uses total

## Test Status
| Suite | Result |
|-------|--------|
| Python unit tests (PR9A) | 14/14 pass |
| Python unit tests (PR9B) | 23/23 pass |
| Python unit tests (PR9C) | 4/4 pass |
| Plugin tests | 58/58 pass |
| Full vault embed build | 729/729 papers, 20,655 chunks |

## Immediate Next
- [ ] Full vault embed build (`--force`) on fresh ChromaDB
- [ ] Verify chunk counts in Obsidian plugin display
