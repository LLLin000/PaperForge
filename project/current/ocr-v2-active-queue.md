# OCR-v2 Active Queue
> Status: OCR-v2 remains stable; Retrieval Experience recovery is now the active blocking workstream.
> Last updated: 2026-07-10

## Current checkpoint

- [Wayfinder: Restore PaperForge retrieval end to end](https://github.com/LLLin000/PaperForge/issues/45) is the canonical recovery map.
- [Inventory the live retrieval architecture and contract drift](https://github.com/LLLin000/PaperForge/issues/53) is resolved with a reviewed [architecture audit](https://gist.github.com/LLLin000/aaf5505a991e85ad9bb4cafa922f48bf).
- Source Corpus data remains authoritative and must be preserved. FTS indexes, embeddings, vec0 tables, and companion metadata are disposable Retrieval Artifacts.
- No retrieval implementation fix or production build-success claim was made at this checkpoint.

## Confirmed blocking findings

1. sql.js metadata search cannot prepare its query because `paper_fts.year` does not exist.
2. The plugin `@` path invokes `retrieve` without `--deep`.
3. Retrieve emits `data.chunks`; the plugin accepts only `data.matches` or `data.results`.
4. Embed build writes new vec0 rows and then deletes every row for that paper.
5. Resume and force still use the legacy Chroma vectors directory as their active-store gate/cleanup target.
6. SQLite `build_state` is live truth, but the plugin renders a nested copy from `vector-runtime-state.json`.
7. The repository and Literature-hub plugin bundles have different checksums; the exact deployed delta is not yet resolved.

## Frontier

- [ ] [Capture a non-destructive retrieval failure matrix](https://github.com/LLLin000/PaperForge/issues/49)
- [ ] [Audit source-to-vault deployment parity](https://github.com/LLLin000/PaperForge/issues/47)

These tickets are independent and may run in parallel. They must not mutate Source Corpus data or apply production fixes.

## Blocked after the frontier

- [ ] [Choose the canonical retrieval architecture and ownership boundary](https://github.com/LLLin000/PaperForge/issues/46)
- [ ] [Specify the retrieval build lifecycle and crash recovery semantics](https://github.com/LLLin000/PaperForge/issues/52)
- [ ] [Specify metadata and deep-search contracts](https://github.com/LLLin000/PaperForge/issues/54)
- [ ] [Define safe repair, rebuild, and model-change policy](https://github.com/LLLin000/PaperForge/issues/51)
- [ ] [Prototype retrieval panel states and recovery flows](https://github.com/LLLin000/PaperForge/issues/48)
- [ ] [Define the retrieval acceptance matrix and release gate](https://github.com/LLLin000/PaperForge/issues/50)

## Verification status

- Read-only Literature-hub DB probe confirmed that `paper_fts` has no `year` column and the sql.js query fails with `OperationalError: no such column: year`.
- Refreshed code-graph traces confirmed that `get_vector_backend()` is tests-only while production retrieval accesses vec0 directly.
- Evidence review confirmed the execution maps and P0 contract failures; build-control-only and explicit-CLI-deep findings were downgraded below P0.
- No test suite was run because this checkpoint is an architecture investigation, not an implementation completion claim.
