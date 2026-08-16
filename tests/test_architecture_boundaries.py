"""M2-F (Control Plane Closure): dependency boundaries.

The backend must never route through the CLI: actions/services/
materialization importing paperforge.commands.* re-creates the
Action→CLI→stdout→JSON-parse chain that swallowed the embed 401.
These tests freeze the boundary; the one known exemption (embed handler)
is tracked for M3 migration.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "paperforge"

FORBIDDEN_LAYERS = ("actions", "services", "materialization")

# Known pre-migration exemptions: file -> set of exact import lines.
# Each entry must carry the migration milestone in a comment.
KNOWN_EXEMPTIONS: dict[str, set[str]] = {
    # M3-A/B/C migrates the embed handler to EmbeddingService; until then
    # it calls the CLI entry.  The M2-E result-contract fix already makes
    # errors surface correctly.
    "actions/registry.py": {"from paperforge.commands.embed import run as embed_run"},
}


def test_core_layers_never_import_commands() -> None:
    for layer in FORBIDDEN_LAYERS:
        layer_dir = ROOT / layer
        if not layer_dir.exists():
            continue
        for py in sorted(layer_dir.rglob("*.py")):
            if py.name.startswith("_"):
                continue
            rel = py.relative_to(ROOT).as_posix()
            exemptions = KNOWN_EXEMPTIONS.get(rel, set())
            text = py.read_text(encoding="utf-8")
            for line in text.splitlines():
                s = line.strip()
                if not (s.startswith("import paperforge.commands") or s.startswith("from paperforge.commands")):
                    continue
                if line.strip() in exemptions:
                    continue
                raise AssertionError(
                    f"{rel}: `{line.strip()}` violates the boundary — "
                    + f"{layer} must not import paperforge.commands.* "
                    + "(Action→CLI→stdout→parse is banned; use the service layer)"
                )
