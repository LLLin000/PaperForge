# Annotation Phase 3: Annotation CLI JSON Contracts - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md; this log preserves the alternatives considered.

**Date:** 2026-06-18
**Phase:** annotation-03-cli-json-contracts
**Areas discussed:** Command shape, import default behavior, paper filtering, JSON structure, error output, list/export boundary

---

## Command Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Single `annotation` namespace | Put all commands under `paperforge annotation ...` for a clear and discoverable API. | Yes |
| Scatter into existing commands | Add import/list/status behavior into existing `sync`, `status`, or other commands. | |

**User's choice:** User selected all areas and asked to follow the recommended direction.
**Notes:** Recommended direction is a dedicated annotation namespace.

---

## Import Default Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Preview by default, write with `--apply` | Safer default; shows what would happen before changing `annotations.db`. | Yes |
| Write by default, preview with `--dry-run` | Faster for power users but riskier because import can mark stale rows. | |

**User's choice:** User selected all areas and asked to follow the recommended direction.
**Notes:** Phase 3 should make preview/apply state explicit in JSON.

---

## Paper Filtering

| Option | Description | Selected |
|--------|-------------|----------|
| `--paper KEY` as main selector | User-facing selector that can resolve through PaperForge identity rather than forcing Zotero internals. | Yes |
| `--zotero-key KEY` only | Direct but too Zotero-specific for a source-agnostic annotation database. | |
| `--attachment-key` for all imports | Precise but too technical as the main path. | |

**User's choice:** User selected all areas and asked to follow the recommended direction.
**Notes:** `--attachment-key` remains useful as optional disambiguation.

---

## JSON Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Existing PFResult envelope | Use `ok`, `command`, `version`, `data`, `error` like existing newer CLI contracts. | Yes |
| Annotation-specific top-level JSON | Flexible but creates another contract shape for users and tests. | |

**User's choice:** User selected all areas and asked to follow the recommended direction.
**Notes:** Command-specific payload should live in `data`.

---

## Error Output

| Option | Description | Selected |
|--------|-------------|----------|
| Stable JSON errors for `--json` | Always return valid JSON with code, message, details, suggestions. | Yes |
| Human text only | Simpler but breaks plugin/automation callers. | |

**User's choice:** User selected all areas and asked to follow the recommended direction.
**Notes:** Messages should be plain-language and actionable, with Chinese-friendly text where useful.

---

## List vs Export Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| `list` lightweight, `export` complete | `list` is for scanning; `export` is for downstream tools and future evidence workflows. | Yes |
| Same payload for both | Simpler but makes quick listing noisy and export less explicit. | |

**User's choice:** User selected all areas and asked to follow the recommended direction.
**Notes:** Both commands must work without the Obsidian plugin.

---

## the agent's Discretion

- Exact internal module layout.
- Exact count-field nesting under `data`.
- Exact error code names, as long as they are stable and tested.

## Deferred Ideas

- Obsidian PDF overlay.
- Local annotation editing.
- Zotero write-back.
- Concept-card/deep-reading evidence integration.
