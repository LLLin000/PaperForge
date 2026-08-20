# Standalone Onboarding & Client-Neutral Setup Protocol

Domain context for the next product lifecycle: PaperForge installation and
first configuration as a backend-owned, client-neutral protocol.  Design
baseline = `462398cb` (current Core behavior we design FROM).

## Language

**Foundation**:
The installable Core: package/runtime + canonical config + resolved
layout + credential authority + pointer. `paperforge setup` = Foundation
only.  _Avoid_: setup meaning "install everything".

**Core READY**:
Foundation verified (`doctor`/`status` green) — independent of any client
integration.  Happens BEFORE Zotero/OCR/vector/Agent/Obsidian attach.
_Avoid_: "ready" claimed after client installs.

**Capability state**:
Per-integration readiness: `Foundation READY / Library READY / OCR READY /
Vector READY / Agent integrated / Obsidian integrated`.  Each is
independent; one failure must not fail Foundation.  _Avoid_: one combined
"setup success".

**Client integration**:
Optional adapter over Core: Agent skill, DSH, Obsidian plugin, etc.  A
client failure (e.g. AgentInstaller) is NOT a PaperForge installation
failure.  _Avoid_: treating client deploy as a Foundation step.

**Onboarding protocol** (backend-owned):
`inspect → plan → apply → verify` where inspect bundles facts + requirements + questions.
- `inspect` = read-only facts + derived requirements + questions (single call, no extra round-trip)
- `questions` = backend-owned schema (Agent renders, never invents)
- `plan` = read-only mutation preview
- `apply` = mutation
- `verify` = fresh observation
_Avoid_: Agent deciding what to ask or inventing product state.

**Secret contract** (external-action only):
Secret values NEVER enter questions response, argv, LLM context, or
paperforge.json.  Backend reports `id: credential.ocr, kind: external_action, state: missing, input_mode: secure_external` with
`input_mode = secure_external`; the Agent points the user at
`paperforge auth set ocr`.  _Avoid_: keys in chat/argv/config.

**Relocation** (stale-plan + verified-switch):
Fresh install: layout fields selectable directly. Installed vault with
materialization: direct `config set <path>` is rejected; only
`relocate plan → preflight → confirmation → move → verify → commit`, and
on failure the old location stays authoritative.  _Avoid_: config-only
path changes that orphan existing materialization.

**Client-neutrality**:
Core must not answer "which agent does this vault use" —
`.agents/skills`, `.omp/skills`, `.github/skills` can coexist; the same
vault can be driven by OpenCode + Claude + DSH + Obsidian simultaneously.
_Avoid_: `agent_platform`/`skill_dir`/`command_dir` as Core truth.

## Frozen questions (to resolve in the PRD)

1. Foundation / client-integration separation: AgentInstaller leaves
   SetupPlan; decide whether vector-extras blocks Foundation.
2. Retire `skill_dir` / `command_dir` / `agent_platform` from Core
   canonical config (migration-only), replaced by client deployment
   observation (`skill status --json` sees installed copies).
3. Backend-owned onboarding protocol: single `setup inspect --json`
   returns read-only facts + derived requirements + `questions[]`
   (internal `requirements` stays diagnosis-only).  Flow: `inspect (facts
   + requirements + questions) → plan+answers → apply → verify`, with
   strict read-only/mutation semantics.
4. External-action/secret contract: credential question kind is
   `external_action`/`secure_external`, never `secret`; secret values
   NEVER enter questions/answers/argv/LLM context/paperforge.json. Backend
   reports `id: credential.ocr, kind: external_action, input_mode:
   secure_external, interaction: {type: secure_cli, argv: [paperforge,
   auth, set, ocr]}`; the Agent points the user there.  _Avoid_: secret
   values in any machine-readable questions surface.
5. Path relocation lifecycle separate from first-time configuration:
   `relocate plan` must bind `observation_fingerprint` and
   `plan_hash`; `apply` fresh re-plans — hash mismatch →
   `setup.plan_stale`, zero mutation.  Fail closed, no orphaned split.
6. Config invariant: canonical config MUST NOT point to the destination
   until destination verification succeeds (same-volume rename/stage →
   verify → switch; cross-volume copy → fsync/hash verify → switch →
   old carrier to recoverable trash).
7. Unified Core READY gate (below): Foundation READY
   independently, covers Library/OCR/Vector without requiring optional
   capabilities; release does not bundle optional invariant.
8. S1–S8 certification as PRD acceptance (below).

## Principle

```text
Backend may recommend defaults.
Agent may explain choices.
Only the user chooses preferences.
Neither Agent nor frontend may invent product state or lifecycle decisions.
```

## Certification gates (PRD acceptance)

- S1 Clean Install: no Obsidian, no `.obsidian`, install → probe → doctor →
  status all green.
- S2 Existing Vault: `.obsidian` fully removed, vault still runs.
- S3 Full Library Journey: setup → sync → OCR → memory → vector →
  read/retrieve.
- S4 Maintenance: status → doctor → reconcile → preflight → repair.
- S5 Destructive Safety: Agent always stops at the confirmation boundary.
- S6 Lifecycle / Recovery: update → restart → interrupted op → repair →
  rollback.
- S7 Agent-guided onboarding: Qwen3-4B follows `questions[]` through a
  fresh setup — no path guessing, no parameter invention, no secret
  solicitation.
- S8 Multi-client neutrality: Core setup installs NO client; then attach
  Agent / DSH / Obsidian separately; Core state identical — clients are
  adapters, not the host.

- **Triage rule (PRD acceptance):** during the S1–S6 current-system
  certification that follows, only failures of currently frozen
  invariants/acceptance become RC blockers; failures that are gaps in
  the must-be-certified future state are recorded as census items for
  this same protocol's implementation.
- **Config-destination invariant:** canonical config must not point to
  a relocation destination until that destination is verified.

## Relationships

- **Materialization** (paperforge/CONTEXT.md): Foundation verify must
  observe the same canonical states; onboarding produces the config that
  materialization consumes.
- **Plugin Control Center** (paperforge/plugin/CONTEXT.md): the control
  center becomes one client of this protocol, not its owner.
- **Weak-model protocol closure** (ledger §2.10/§2.11): the same
  "backend owns decisions, agent executes" discipline extends from
  retrieval/reading to installation.
