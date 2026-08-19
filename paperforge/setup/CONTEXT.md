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
`inspect → requirements → questions[] → plan → apply → verify`.
- `inspect` = read-only facts
- `requirements` = derived missing inputs
- `questions` = backend-owned question schema (Agent renders, never
  invents)
- `plan` = read-only mutation preview
- `apply` = mutation
- `verify` = fresh observation
_Avoid_: Agent deciding what to ask or inventing product state.

**Secret contract**:
Secret values NEVER enter questions response, argv, LLM context, or
paperforge.json.  Backend reports `credential.ocr = missing` with
`input_mode = secure_external`; the Agent points the user at
`paperforge auth set ocr`.  _Avoid_: keys in chat/argv/config.

**Relocation**:
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
3. Backend-owned onboarding protocol: `inspect → requirements →
   questions[] → plan → apply → verify` with strict read-only/mutation
   semantics.
4. Secret input contract (secure_external, never in questions/argv/context/
   config).
5. Path relocation lifecycle separate from first-time configuration.
6. S1–S8 certification as PRD acceptance (below).

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

## Relationships

- **Materialization** (paperforge/CONTEXT.md): Foundation verify must
  observe the same canonical states; onboarding produces the config that
  materialization consumes.
- **Plugin Control Center** (paperforge/plugin/CONTEXT.md): the control
  center becomes one client of this protocol, not its owner.
- **Weak-model protocol closure** (ledger §2.10/§2.11): the same
  "backend owns decisions, agent executes" discipline extends from
  retrieval/reading to installation.
