---
phase: 10
title: Documentation & Cohesion
milestone: v1.2
status: context_created
created: 2026-04-24
updated: 2026-04-24
---

# Phase 10: Documentation & Cohesion — Context

## Phase Goal

Document architecture and design decisions, create migration guide for v1.1 → v1.2, establish command documentation template, and perform consistency audit to ensure all project artifacts are coherent.

## Scope

Based on REQUIREMENTS-v1.2.md:
- **SYS-03:** Architecture documentation — two-layer design, data flow, directory structure
- **SYS-04:** User-facing docs — command reference (Agent ↔ CLI mapping)
- **SYS-05:** Consistency audit — old command names eliminated, terminology unified
- **SYS-06:** Migration guide — v1.1 → v1.2 transition path

## Decisions Made (from Discussion)

### Decision 1: Architecture Docs Scope
**Chosen:** 完整版 — 面向维护者 (Full version for maintainers)

ARCHITECTURE.md will include:
- Two-layer design (Worker + Agent)
- Data flow diagrams
- Directory structure rationale
- `commands/` package pattern explanation
- ADR-style design decision records (key decisions from Phases 1-9)

Target audience: maintainers and contributors.

### Decision 2: Migration Guide Scope
**Chosen:** 完整范围 — 全量迁移 (Complete migration)

MIGRATION-v1.2.md covers v1.1 → v1.2:
- Command name changes (selection-sync → sync, etc.)
- Package rename (paperforge_lite → paperforge)
- Import path changes
- pip reinstall instructions
- Config file changes (if any)
- Directory structure changes (if any)
- Rollback/downgrade instructions
- FAQ section

### Decision 3: Command Doc Template
**Chosen:** 分层结构 — 研究多平台但只实施 OpenCode

Structure:
- `docs/COMMANDS.md` — Master reference with Agent ↔ CLI mapping matrix
- `command/*.md` — Per-command detailed docs with unified template

Template must support multiple agent platforms (OpenCode, Codex, Claude Code).
Phase 10 will implement OpenCode support and document approach for others.

### Decision 4: Consistency Audit
**Chosen:** 混合方案 — 脚本+清单 (Mixed approach)

- **Automated scripts** for hard constraints:
  - No old command names (`selection-sync`, `index-refresh`, `ocr run`, `/LD-*`, `/lp-*`)
  - No dead links
  - No broken references to `paperforge_lite`

- **Manual checklist** for soft constraints:
  - Terminology consistency
  - Style consistency
  - Branding (PaperForge Lite vs PaperForge)

## Prior Context

### From Phase 9
- Package renamed: `paperforge_lite` → `paperforge`
- Commands unified: `paperforge sync`, `paperforge ocr`
- Agent commands: `/pf-*` namespace
- Architecture: `paperforge/commands/` package
- All tests pass (155/155)

### Existing Docs
- `docs/README.md` — Project overview
- `docs/INSTALLATION.md` — Setup guide
- `docs/setup-guide.md` — Detailed setup
- `command/pf-*.md` — 5 per-command docs
- `AGENTS.md` — Agent usage guide

## Open Questions

None. All gray areas resolved in discussion.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Migration guide misses edge case | Medium | Medium | Include FAQ + rollback instructions |
| Architecture doc becomes stale | High | Low | Mark as "last updated", reference code |
| Command template doesn't fit future platforms | Low | Low | Document extension approach |

## Success Criteria

- [ ] ARCHITECTURE.md created and complete
- [ ] MIGRATION-v1.2.md created and complete
- [ ] docs/COMMANDS.md created and complete
- [ ] command/*.md follow unified template
- [ ] Consistency audit scripts pass
- [ ] Manual checklist reviewed
- [ ] All docs committed
