# Annotation Phase 5: Plugin Annotation Data Bridge - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md; this log preserves the alternatives considered.

**Date:** 2026-06-18
**Phase:** annotation-05-plugin-annotation-data-bridge
**Areas discussed:** CLI entry point, active paper resolution, UI-ready state machine, missing/failure states, annotation row shape, refresh strategy

---

## CLI Entry Point

| Option | Description | Selected |
|--------|-------------|----------|
| `annotation export --paper KEY --json` | Use full export payload as the plugin bridge source; preserve provenance and PDF-location fields for later phases. | Yes |
| `annotation list --paper KEY --json` | Use lightweight list payload for current list display needs. | |
| Dual entry point | Use `list` by default and `export` only when positioning data is needed. | |

**User's choice:** 1
**Notes:** User accepted the recommended full-export bridge so Phase 7/8 can reuse the same data without reworking the bridge.

---

## Active Paper Resolution

| Option | Description | Selected |
|--------|-------------|----------|
| Note frontmatter only | Resolve active paper only from active Markdown note `zotero_key`. | |
| Reuse dashboard resolution | Support Markdown frontmatter, PDF path matching, and workspace path detection through existing dashboard logic. | Yes |
| Note plus PDF only | Resolve active paper from Markdown notes and PDFs, but not other workspace files. | |

**User's choice:** 2
**Notes:** User wants annotation behavior to follow the existing dashboard interpretation of the current paper.

---

## UI-Ready State Machine

| Option | Description | Selected |
|--------|-------------|----------|
| Parse JSON only | Return an annotation array and leave state interpretation to later UI. | |
| Full state machine | Return states such as `idle`, `loading`, `ready`, `empty`, `missing-paper`, `missing-db`, `cli-error`, and `invalid-json`. | Yes |
| Basic states only | Distinguish only success, error, and empty. | |

**User's choice:** 2
**Notes:** Full state is needed so Phase 6 can render cleanly without guessing why annotations are absent.

---

## Missing and Failure States

| Option | Description | Selected |
|--------|-------------|----------|
| `missing-db` | Treat missing or unreadable `annotations.db` as its own recoverable state. | Yes |
| `empty` | Treat missing `annotations.db` the same as no annotations. | |
| `cli-error` | Treat missing `annotations.db` as a command failure. | |

**User's choice:** 1
**Notes:** Missing database means the annotation system is not prepared, not that the current paper has no annotations.

---

## Annotation Row Shape

| Option | Description | Selected |
|--------|-------------|----------|
| List fields only | Keep only page, type/color, selected text, comment, source, and read-only state. | |
| Normalized sections plus raw | Keep `display`, `provenance`, `pdfLocation`, and `raw` fields. | Yes |
| Raw JSON only | Preserve the raw CLI payload without normalized semantic groups. | |

**User's choice:** 2
**Notes:** User accepted preserving full export information while still giving later UI a clean display shape.

---

## Refresh Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Manual loader only | Expose a loader function, but do not update on active-file changes. | |
| Active-paper update | Update annotation state when the active paper changes, without adding polling. | Yes |
| Background polling | Poll annotation data in the background. | |

**User's choice:** 2
**Notes:** Phase 5 should track active paper changes but leave visible refresh UI to Phase 6.

---

## the agent's Discretion

- Planner may choose exact helper names and module layout.
- Planner may choose how to detect `missing-db`, as long as it remains separate from `empty`.
- Planner may choose exact normalized object shape, as long as the `display`, `provenance`, `pdfLocation`, and `raw` semantics are preserved.

## Deferred Ideas

- Annotation sidebar/list UI is deferred to Annotation Phase 6.
- Jump-to-PDF/page is deferred to Annotation Phase 7.
- PDF overlay rendering is deferred to Annotation Phase 8.
- Verification gate and safety audit are deferred to Annotation Phase 9.
- Local editing, Zotero write-back, and concept-card evidence integration remain future requirements outside this phase.
