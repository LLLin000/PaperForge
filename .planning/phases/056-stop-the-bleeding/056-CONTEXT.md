# Phase 56: Stop the Bleeding - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — no grey-area discussion needed)

<domain>
## Phase Boundary

Quick consistency fixes that unblock all subsequent v2.1 phases:
- **Version sync**: Ensure all version declarations (__init__.py, manifest.json, versions.json, pyproject.toml, docs) return consistent values via a CI-gate script
- **PyYAML dependency**: PyYAML already declared in pyproject.toml as hard dependency — doctor's conditional yaml check must be removed or converted to hard-fail (single source of truth)
- **Install docs**: README, INSTALLATION.md, and setup-guide must present one unified primary install path with no conflicting recommendations
- **Plugin version pinning**: `pip install paperforge` invoked by plugin must pin to the version declared in plugin manifest — no version drift between plugin and Python package

This phase touches NO user-facing features. All changes are internal engineering consistency fixes.
</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — pure infrastructure phase. Refer to ROADMAP phase goal, success criteria, and existing codebase conventions.
</decisions>

<code_context>
## Existing Code Insights

### Current State
- **Version**: `1.4.17rc3` declared in `paperforge/__init__.py` and `paperforge/plugin/manifest.json`
- **versions.json**: Contains `{"1.4.3": "1.9.0", "1.4.17rc3": "1.9.0"}` — has stale entry
- **pyproject.toml**: `dynamic = ["version"]` reading from `paperforge.__version__` attr; PyYAML listed as hard dependency
- **Doctor check**: `paperforge/worker/status.py` has conditional yaml module check with version warning — should be hard-require or removed
- **Install docs**: README.md exists with Obsidian plugin install path; INSTALLATION.md not found; docs/setup-guide.md not found
- **Plugin runtime**: Plugin invokes `pip install paperforge` via subprocess — no version pinning visible in current `main.js`
- **check_version_sync.py**: Does not exist yet — must be created

### Reusable Assets
- `scripts/consistency_audit.py` — existing audit script that can serve as pattern for version sync checker
- `paperforge/__init__.py` — single source of truth for `__version__`

### Established Patterns
- Dynamic version via setuptools reading from `__init__.py`
- Plugin version declared in manifest.json
- Scripts in `scripts/` directory

### Integration Points
- CI gate: new script at `scripts/check_version_sync.py`
- Doctor: modify `paperforge/worker/status.py` PyYAML check
- Docs: align README.md, create INSTALLATION.md, ensure setup-guide consistency
- Plugin: modify `paperforge/plugin/main.js` pip install call to pin version
</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase. Refer to ROADMAP phase goal and success criteria.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.
</deferred>
