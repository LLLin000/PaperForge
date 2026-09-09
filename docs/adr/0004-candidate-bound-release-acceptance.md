# Candidate-bound release acceptance, with RELEASE_READY separated from RELEASED

Status: accepted (2026-09-10)

PaperForge's release decision previously rested on component-level green suites plus an owner gate, which could not answer "does *this* artifact upgrade an existing vault safely?" We now bind acceptance to an explicit **Candidate** (source SHA + plugin bundle + wheel + config/fixture hashes), record **Acceptance Evidence** per case variant and evidence layer rather than one boolean per case, and split the outcome in two: **RELEASE_READY** (pre-release business set verified, certification complete, owner accepted the evidence) and **RELEASED** (owner authorized a specific version and hashes, the single publish chain ran, post-release smoke passed). RELEASE_READY never authorizes publishing.

## Considered Options

- **One gate ("tests pass → publish")** — simplest, but conflates development green runs with candidate certification and lets a stale SHA or rebuilt artifact inherit another build's evidence.
- **Separate acceptance tracker per component** — more granular, but loses the cross-task journeys where this project's historical defects actually occurred.
- **Candidate-bound acceptance with split outcomes** — chosen: costs an explicit evidence schema and a re-bind rule, and in exchange makes "we shipped on evidence for a different artifact" structurally impossible.

## Consequences

- A green run may only be reused when source, dependencies, configuration, model and artifact content are provably unchanged; editing a report's SHA field is not re-binding.
- Any post-certification change to code, dependencies, bundle, default config or packaging content invalidates the affected gates and requires re-freezing.
- Live-provider and human-ground-truth evidence are layers of the same matrix, not a parallel process; their absence keeps the corresponding case BLOCKED rather than PASS.
