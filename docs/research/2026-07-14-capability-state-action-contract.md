# Capability State + Action Contract

**Issue:** [#69](https://github.com/LLLin000/PaperForge/issues/69) | **Parent:** [#65](https://github.com/LLLin000/PaperForge/issues/65)
**Inputs:** #66 audit, #67 Obsidian patterns, #68 desktop-runtime patterns, agent://CapabilityModel, agent://CapabilityStress

---

## 1. Locked Decisions

| Decision | Resolution |
|---|---|
| 维护 is a derived view | No independent probe. Aggregate of the five modules' non-ready states. |
| Updates are cross-cutting notices | Attached to the affected module envelope. Notices do not change state unless breaking. |
| Offline is per-capability evidence | Each module detects connectivity independently. No global offline flag. |
| Reason codes are module-prefixed snake_case | `ocr.missing_api_key`, `installation.config_corrupt`, `memory.db_corrupt`. |
| Activity does not hide attention | `running` never masks a warning/error badge. |
| Checkpointing only where needed | Most modules use artifact-state detection. OCR redo is a documented checkpoint exception. |
| Backend owns facts and actions | Plugin never reclassifies severity, derives actions, or decides maintenance visibility from raw data. |
| Stale is never ready | TTL-expired envelope renders as `unknown`, never as its stored state. |
| Source materials preserved on destructive ops | Destructive module-scoped ops never delete raw images, exports, or config files without explicit confirmation. |
| Diagnostics never auto-submitted | Issue drafts pass through user review before creation. |
| Dismissal is notification-local | Dismissing a maintenance notification does not change the underlying module capability_state. |

---

## 2. Orthogonal Axes

Every module is described by three **independent** axes:

```
Availability  x  Activity  x  Urgency/attention
(can it       (is it busy  (does the user need
 work?)       right now?)   to know about it?)
```

### Availability (6 states, ordinal worst-to-best)

```
unknown < unavailable < missing_input < needs_action < limited < ready
```

| State | Severity | Meaning |
|---|---|---|
| `unknown` | `unknown` | No probe data; stale or never checked |
| `unavailable` | `error` | Module cannot function (runtime missing, DB corrupt, auth failure) |
| `missing_input` | `warning` | Configuration needed (path, API key not set) |
| `needs_action` | `warning` | Recommended action pending (stale index, papers pending) |
| `limited` | `warning` | Degraded but functional (model unreachable, quality dip) |
| `ready` | `ok` | Fully functional; no attention needed |

### Activity (2 states, orthogonal)

| State | Meaning |
|---|---|
| `idle` | No active operation |
| `running` | Operation in progress |

### Attention (urgency overlay)

Urgency is derived purely from availability state. The attention-ordering rule: if a module is both `needs_action` (availability axis) and `running` (activity axis), the availability badge remains visible.

#### Combined axis examples

```
ready     + idle       Normal, no attention needed
ready     + running    Active operation, no issues
needs_action + idle    Pending work, badge visible
needs_action + running Active on one task; badge visible because another awaits
missing_input + idle   Configuration needed
unavailable + idle     Broken
unknown    + idle      No probe data yet
```

---

## 3. Envelope Specification

### Envelope fields

```json
{
  "schema_version": 1,
  "module": "ocr",
  "capability_state": "needs_action",
  "activity_state": "idle",
  "activity_label": null,
  "activity_progress": null,
  "severity": "warning",
  "reason": {
    "code": "ocr.artifacts_stale",
    "text": "Derived OCR artifacts are stale for 12 papers"
  },
  "action": {
    "primary": {
      "verb": "rebuild_derived",
      "label": "Rebuild derived artifacts",
      "destructive": false,
      "destructive_scope": null,
      "destructive_effect": null,
      "confirmation_required": false,
      "confirmation_prompt": null,
      "command": "paperforge ocr rebuild-derived",
      "scope": "all",
      "scope_count": 12
    }
  },
  "notices": [
    {
      "type": "update_available",
      "target": "ocr_model",
      "current_version": "paddleocr_v4",
      "available_version": "paddleocr_v5",
      "breaking": false
    }
  ],
  "updated_at": "2026-07-14T10:30:00Z",
  "ttl_seconds": 300
}
```

### Field rules

| Field | Rule |
|---|---|
| `schema_version` | Plugin checks compatibility before consuming. |
| `module` | One of: `installation`, `library`, `ocr`, `memory`, `maintenance`, `help`. |
| `capability_state` | Backend's factual assessment. Plugin never overrides. |
| `activity_state` | Orthogonal. When `running`, `activity_label` and `activity_progress` may be non-null. |
| `severity` | Derived from `capability_state` by backend. Plugin renders color from this field, never from state. |
| `reason.code` | Stable, never localized. Format: `<module>.<snake_case>`. |
| `reason.text` | English fallback. Plugin may override via i18n using `reason.code` as key. |
| `action.primary` | `null` when `capability_state` is `ready`. When `unknown`, action is `probe`. Singular invariant: at most one. |
| `action.primary.verb` | Stable English imperative, never localized. See verb table below. |
| `action.primary.destructive` | When `true`, `confirmation_required` must also be `true`. |
| `action.primary.destructive_scope` | `"paper"`, `"selection"`, `"module"`, `"all"`, or null. |
| `notices[]` | Cross-cutting info. Does not change `capability_state` unless `breaking: true`. |
| `updated_at` + `ttl_seconds` | If `now - updated_at > ttl_seconds`, plugin treats module as `unknown`. |

### Localization boundary

| Backend owns | Plugin owns |
|---|---|
| `reason.code` (stable key) | i18n mapping: `reason.<code>` → localized text |
| `action.primary.verb` (stable key) | i18n mapping: `action.<verb>.label` → localized button text |
| `reason.text` (English fallback) | Falls back to this if i18n key missing |
| `destructive_effect` (English fallback) | Localizable via `action.<verb>.destructive_effect` |
| `confirmation_prompt` (English fallback) | Localizable via `action.<verb>.confirmation_prompt` |

---

## 4. Reason-Code Grammar

```
<module>.<noun_or_past_participle_phrase_with_underscores>
```

Representative codes (illustrative, not exhaustive):

| Code | State | Typical verb |
|---|---|---|
| `installation.config_missing` | unavailable | `setup` |
| `installation.runtime_not_found` | unavailable | `setup` |
| `installation.runtime_version_mismatch` | limited | `update` |
| `installation.vault_path_invalid` | missing_input | `set_config` |
| `library.zotero_path_invalid` | missing_input | `set_config` |
| `library.sync_not_run` | needs_action | `sync` |
| `library.index_stale` | needs_action | `rebuild_index` |
| `ocr.api_key_missing` | missing_input | `set_config` |
| `ocr.artifacts_stale` | needs_action | `rebuild_derived` |
| `ocr.quality_unacceptable` | needs_action | `investigate` |
| `ocr.api_unreachable` | limited | `investigate` |
| `memory.db_missing` | needs_action | `run` |
| `memory.db_corrupt` | unavailable | `restore_backup` |
| `memory.index_stale` | needs_action | `rebuild_index` |
| `memory.snapshot_stale` | unknown | `probe` |

**Stability:** Once released, a reason code is not renamed in a patch version.

---

## 5. Canonical Action Verbs (<=12)

| Verb | Destructive | Scope | Modules | When |
|---|---|---|---|---|
| `setup` | no | all | installation | First-time or re-do installation |
| `set_config` | no | all | installation, library, ocr | Open a config surface (path, API key, etc.) |
| `sync` | no | all | library | Sync Zotero exports |
| `rebuild_derived` | no | selection | ocr | Recompute derived artifacts only |
| `rebuild_index` | no | all | library, memory | Rebuild search/vector index |
| `redo` | yes | selection | ocr | Delete and re-run OCR from raw (requires confirmation) |
| `restore_backup` | yes | module | memory | Restore DB from backup (requires confirmation) |
| `run` | no | all | ocr, memory | Run a pending batch operation |
| `migrate` | no | all | memory | Run DB schema migration |
| `update` | no | all | installation, ocr | Update runtime, model, or plugin |
| `investigate` | no | all | any | Run diagnostics |
| `probe` | no | module | any | Refresh capability check |

### One-primary-action invariant

At most one `action.primary` per module. Backend selects by priority: `setup` > `set_config` > `restore_backup` > `redo` > `run` > `migrate` > `update` > `rebuild_*` > `investigate` > `probe`. When `capability_state` is `ready`, `action.primary` is `null`. When `unknown`, action is `probe`.

---

## 6. Severity Rules

```
capability_state → severity (backend-derived, never reclassified by plugin)

unknown     → unknown   (grey)
unavailable → error     (red)
missing_input → warning (yellow)
needs_action → warning  (yellow)
limited     → warning   (yellow)
ready       → ok        (green)
```

Ordinality for maintenance aggregation: `unknown=0, ok=1, warning=2, error=3`.

---

## 7. Transition Rules

### Availability transitions

```
From → To        Event
─────────────────────────────────────────────────
unknown → *      probe returns evidence
ready → unknown  TTL expired
ready → missing_input  config invalidated
ready → needs_action   new pending work detected
ready → limited        dependency degrades
ready → unavailable    runtime failure
needs_action → ready   action completes successfully
needs_action → limited condition worsens to degradation
needs_action → unavailable  condition becomes fatal
missing_input → ready configure + validate succeed
missing_input → unavailable validate fails
limited → ready   degradation resolves
limited → needs_action  degradation becomes actionable
limited → unavailable   degradation becomes fatal
unavailable → ready     repair completes
unavailable → needs_action partial repair
```

### Activity transitions (orthogonal)

```
idle → running   operation starts
running → idle   operation: done | fail | cancel
```

### Cross-axis rules

1. A transition on one axis never affects the other axis directly.
2. After an activity completes (`running → idle`), a capability probe may run, which may change the availability state.
3. `running` never changes `capability_state`. A module that is `needs_action + running` stays `needs_action` until the underlying action completes.

---

## 8. Maintenance Projection

Maintenance is a derived view, not an independent module with its own probe.

### Content

```json
{
  "module": "maintenance",
  "capability_state": "needs_action",
  "severity": "warning",
  "reason": { "code": "maintenance.items_present", "text": "2 modules need attention" },
  "action": { "primary": { "verb": "probe", "label": "Refresh" } },
  "items": [
    { "module": "ocr", "capability_state": "needs_action", "reason_code": "ocr.artifacts_stale" },
    { "module": "memory", "capability_state": "needs_action", "reason_code": "memory.index_stale" }
  ]
}
```

### Rules

| Condition | Behavior |
|---|---|
| `maintenance.capability_state` | Worst ordinal among constituents (`items`), ignoring `unknown`. |
| Entry | Any module transitions from `ready` or `unknown` to `{unavailable, missing_input, needs_action, limited}`. |
| Exit | Constituent module transitions to `ready` or `unknown`. |
| Dismissal | Affects notification badge only. Underlying `capability_state` unchanged. Re-dismissal idempotent. |
| No items | `capability_state = ready`, `reason.code = "maintenance.no_items"`, `items = []`. |

---

## 9. Stale / Unknown Behavior

| Condition | Behavior |
|---|---|
| Never probed | `capability_state = unknown`. Action = `probe`. |
| `updated_at + ttl_seconds < now` | Plugin treats as `unknown` regardless of stored state. Grey indicator, not last-known color. |
| TTL expired + `ready` | → `unknown` → probe → (actual state). |
| TTL expired + `unavailable` | → `unknown` → probe → `unavailable` (if condition unchanged). |
| Stale data | Never used for action or severity derivation. Only fresh probe data is canonical. |

Default TTL values (per-module, calibrate during prototype):

| Module | TTL | Rationale |
|---|---|---|
| installation | 3600s | Config rarely changes at runtime |
| library | 300s | Filesystem/Zotero may change |
| ocr | 60s | Batch status changes rapidly |
| memory | 300s | DB/index state medium-lived |
| maintenance | 60s | Cheap projection recompute |
| help | 3600s | Files rarely change |

---

## 10. Destructive Metadata

```json
{
  "action": {
    "primary": {
      "verb": "redo",
      "destructive": true,
      "destructive_scope": "selection",
      "destructive_effect": "Deletes existing OCR derived artifacts for the selected papers and re-runs OCR from raw images. Raw images are preserved.",
      "confirmation_required": true,
      "confirmation_prompt": "This will delete existing OCR output for {count} papers and re-run OCR. This cannot be undone. Proceed?"
    }
  }
}
```

| Field | Rule |
|---|---|
| `destructive: true` | Always implies `confirmation_required: true`. |
| `destructive_scope` | `"paper"`, `"selection"`, `"module"`, `"all"`. |
| `confirmation_prompt` | Localized via `action.<verb>.confirmation_prompt`. |
| Two-step confirmation | Required for `scope: "all"`. |

---

## 11. Edge Cases (one per module)

| Module | Edge case | State | Code | Action |
|---|---|---|---|---|
| installation | Runtime not deployed due to pip skip defect (#66 P0) | unavailable | `installation.runtime_not_found` | `setup` |
| library | User moved Zotero after initial config | unavailable | `library.zotero_path_invalid` | `set_config` |
| ocr | Model update changes output format (breaking) | limited | `ocr.model_update_breaking` | `update` |
| memory | DB schema version mismatch | needs_action | `memory.migration_needed` | `migrate` |
| maintenance | All modules ready | ready | `maintenance.no_items` | null |
| help | Help files missing (deleted after install) | limited | `help.docs_missing` | `setup` |

---

## 12. Acceptance Tests

### Test 1: Orthogonal axes, running does not hide warning

1. Set OCR to `needs_action` (`ocr.papers_pending`). Verify badge is yellow.
2. Start OCR batch operation. Verify badge remains yellow, activity shows spinner.
3. Complete batch. Verify capability re-probes.

### Test 2: One primary action

1. Set memory to both `memory.migration_needed` and `memory.index_stale`.
2. Verify `action.primary.verb` is `migrate` (higher priority), not `rebuild_index`.

### Test 3: Stale → unknown

1. Envelope with `capability_state: "ready"`, `updated_at: 2026-01-01T00:00:00Z`, `ttl_seconds: 60`.
2. Plugin renders module as `unknown` (grey). Action is `probe`.

### Test 4: Maintenance entry and exit

1. OCR transitions from `ready` to `needs_action`. Verify maintenance items contains OCR.
2. User runs `rebuild_derived`, action completes, OCR returns to `ready`. Verify OCR is removed from maintenance items.

### Test 5: Destructive action with confirmation

1. Envelope contains `verb: "redo"`, `destructive: true`, `confirmation_required: true`.
2. UI shows confirmation dialog before executing command.
3. Verify `destroyed_effect` describes exactly what is affected.

### Test 6: Offline per-capability, not global

1. OCR becomes `limited` with `ocr.api_unreachable`. Library remains `ready`.
2. Verify OCR badge is yellow, library badge is green.

### Test 7: Localization boundary

1. Backend sends `reason.code: "ocr.api_key_missing"`, `reason.text: "API key not configured"`.
2. Plugin with zh-CN i18n renders translated text from `reason.ocr.api_key_missing` key.
3. Plugin without that i18n key renders the English fallback `"API key not configured"`.

### Test 8: Update notice is cross-cutting, not state change

1. OCR is `ready` with notice `type: "update_available"`, `breaking: false`.
2. Verify badge is green. Notice text appears as informational banner.
3. Same notice with `breaking: true` causes `capability_state` to become `limited`.

### Test 9: Unknown from TTL expiry

1. Set `ttl_seconds: 300`, clock advances past expiry.
2. Plugin render does not show stored state. Shows `unknown` with probe action.

### Test 10: Maintenance dismissal is notification-local

1. OCR in maintenance with `needs_action`. User dismisses notification badge.
2. Verify badge cleared, but OCR still appears in maintenance items list.
3. After action completes, OCR leaves maintenance entirely.

---

## 13. Unresolved Questions

**U1 — Default TTL calibration.** The values in Section 9 are initial estimates. Actual TTLs should be calibrated during the #71 prototype phase to balance re-probe frequency against visible staleness. No acceptance-test gate depends on exact TTL values.
