# Consistency Checklist

> Manual review checklist for soft constraints that cannot be fully automated.
> Run this before each release, alongside `scripts/consistency_audit.py`.

---

## Terminology

- [ ] "PaperForge Lite" used correctly (product name, not "Paperforge" or "Paper Forge")
- [ ] "Zotero" capitalized correctly
- [ ] "Obsidian" capitalized correctly
- [ ] "PaddleOCR" capitalized correctly
- [ ] "Better BibTeX" capitalized correctly
- [ ] Chinese terms consistent (e.g., "精读" not "深度阅读" in one place and "精读" in another)

## Commands

- [ ] All CLI examples use `paperforge` (not `paperforge_lite`)
- [ ] All Agent examples use `/pf-*` (not `/LD-*` or `/lp-*`)
- [ ] Old commands only appear in migration guide (`docs/MIGRATION-v1.2.md`) and historical docs (`.planning/`)
- [ ] `python -m paperforge` fallback documented where relevant

## Cross-References

- [ ] All internal links work (verified by `scripts/consistency_audit.py` Check 3)
- [ ] All `command/*.md` files linked from `docs/COMMANDS.md`
- [ ] `docs/ARCHITECTURE.md` referenced from `README.md`
- [ ] `docs/MIGRATION-v1.2.md` referenced from `README.md` or `AGENTS.md`
- [ ] `AGENTS.md` referenced from all command docs

## Version References

- [ ] All docs reference v1.2 (not v1.1 or v1.0)
- [ ] Setup instructions reference current version
- [ ] `paperforge status` output example uses v1.2

## Style

- [ ] Headers use consistent capitalization (sentence case or title case, not mixed)
- [ ] Code blocks have language tags (```bash, ```python, ```markdown)
- [ ] Tables are properly formatted (aligned columns, consistent delimiters)
- [ ] Frontmatter in generated notes uses consistent field names
- [ ] Callouts use consistent syntax (`> [!NOTE]`, `> [!WARNING]`)

## Branding

- [ ] README.md uses correct product name "PaperForge Lite"
- [ ] `AGENTS.md` uses correct product name
- [ ] Command docs use correct product name
- [ ] No references to deprecated package name `paperforge_lite` in user-facing docs

## Platform Notes

- [ ] All `command/*.md` files have "Platform Notes" section
- [ ] OpenCode-specific instructions are present
- [ ] Codex/Claude Code future support is noted where applicable

## Review Sign-Off

| Reviewer | Date | Result |
|----------|------|--------|
|          |      | [ ] Pass / [ ] Fail |

**Notes:**

---

*PaperForge Lite | Consistency Checklist | For maintainers and release managers*
