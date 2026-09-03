# 02 — Python Surface Audit & Machine-Mode Normalization

**What to build:** An audit and normalization of Python CLI machine contracts. Every backend action descriptor explicitly declares its execution mode (`execution_mode = "result" | "stream"`), ensuring clients know whether to consume a single JSON result or a #137 NDJSON event stream without guessing or hardcoding command names in TypeScript. Standardize action IDs across registry and probes.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Audit `paperforge action list/describe/preflight` to ensure every `ActionDescriptor` includes `execution_mode: "result" | "stream"`.
- [ ] Verify that streaming commands (`ocr run`, `setup`, `embed build`, `update`) strictly emit standard #137 NDJSON events (`start`, `phase`, `item_result`, `terminal: result|error|cancelled`).
- [ ] Verify that standard commands (`action run <id> --json` for non-streaming actions) emit valid, uniform single JSON results (`PFResult`).
- [ ] Verify that action registry IDs are canonical and match existing backend commands (`memory.build`, `memory.rebuild`, `embed.build`, `embed.resume`, etc.), eliminating non-existent IDs like `memory.rebuild_vector`.
- [ ] Add backend regression tests in `tests/` verifying descriptor execution modes and NDJSON event contract compliance.
