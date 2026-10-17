"""Explicit source bindings for architecture authority facts (#229).

The contract declares the authority identities; this manifest declares the
source symbol that owns each identity.  Collection fails closed when a bound
symbol disappears: the corresponding rule then remains unresolved instead of
copying contract declarations into the survey without source evidence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from paperforge.architecture_audit.layers import RoleAuthorityFact, UnitAuthorityFact

from .common import make_evidence

if TYPE_CHECKING:
    from paperforge.architecture_audit import ArchitectureContract


@dataclass(frozen=True)
class RoleBinding:
    source: str
    symbol: str
    operation_id: str
    role: str
    authorities: tuple[str, ...]
    #: Calls the bound symbol's body must make for the role to be evidenced.
    #: A symbol that still exists but no longer performs the role is not
    #: evidence — the rule stays unresolved instead of satisfied (#229).
    required_calls: tuple[str, ...] = ()


@dataclass(frozen=True)
class UnitBinding:
    source: str
    symbol: str
    unit_id: str
    publication_authorities: tuple[str, ...]
    authorized_writers: tuple[str, ...]
    #: Calls the bound symbol's body must make for the publication to be
    #: evidenced (same fail-closed rule as RoleBinding).
    required_calls: tuple[str, ...] = ()


ROLE_BINDINGS: tuple[RoleBinding, ...] = (
    RoleBinding(
        "paperforge/worker/ocr.py",
        "run_ocr",
        "ocr_run",
        "execution",
        ("backend.ocr.executor",),
        ("_acquire_controller_lock(",),
    ),
    RoleBinding(
        "paperforge/plugin/src/views/ocr-workspace.ts",
        "_stopBuild",
        "ocr_rebuild",
        "stop",
        ("plugin.ocr_process_controller",),
        ("cancelActiveOperation(",),
    ),
    RoleBinding(
        "paperforge/plugin/src/settings.ts",
        "_renderMemoryDetail",
        "embed_build_resume",
        "stop",
        ("plugin.embed_build_controller",),
        ("cancelActiveOperation(",),
    ),
)

UNIT_BINDINGS: tuple[UnitBinding, ...] = (
    UnitBinding(
        "paperforge/commands/versions.py",
        "_run_restore",
        "ocr_display.fulltext",
        ("version_history.authority",),
        ("version_history.restore",),
        ("shutil.copy2(", "record_restore_provenance("),
    ),
    UnitBinding(
        "paperforge/memory/builder.py",
        "build_for_keys",
        "retrieval.units",
        ("memory.publisher",),
        ("memory.builder",),
        ("_build_from_index_locked(",),
    ),
    UnitBinding(
        "paperforge/memory/builder.py",
        "build_for_keys",
        "retrieval.fts",
        ("memory.publisher",),
        ("memory.builder",),
        ("_build_from_index_locked(",),
    ),
)


def _definition_line(path: Path, symbol: str) -> int | None:
    """Return the unique definition line for a manifest symbol."""
    lines = path.read_text(encoding="utf-8").splitlines()
    escaped = re.escape(symbol)
    if path.suffix == ".py":
        pattern = re.compile(rf"^\s*(?:async\s+)?def\s+{escaped}\s*\(")
    else:
        pattern = re.compile(
            "".join(
                (
                    r"^\s*(?:(?:export|public|private|protected|static|async|readonly|function)\s+)*",
                    rf"{escaped}\s*[<(]",
                )
            )
        )
    matches = [index + 1 for index, line in enumerate(lines) if pattern.search(line)]
    return matches[0] if len(matches) == 1 else None


def _symbol_body(path: Path, symbol: str, definition_line: int) -> str | None:
    """The symbol's body text, from its definition to its balanced end.

    Python: the signature's closing colon, then every line indented deeper.
    TypeScript: brace balance from the definition line.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    start = definition_line - 1
    if path.suffix == ".py":
        index = start
        while index < len(lines) and not lines[index].rstrip().endswith(":"):
            index += 1
        if index >= len(lines):
            return None
        indent = len(lines[start]) - len(lines[start].lstrip())
        body = lines[start : index + 1]
        for line in lines[index + 1 :]:
            if line.strip() and (len(line) - len(line.lstrip())) <= indent:
                break
            body.append(line)
        return "\n".join(body)
    depth = 0
    body = []
    for line in lines[start:]:
        depth += line.count("{") - line.count("}")
        body.append(line)
        if depth <= 0 and len(body) > 1:
            break
    return "\n".join(body) if body else None


def _evidence(
    repo: Path,
    source: str,
    symbol: str,
    required_calls: tuple[str, ...] = (),
):
    """Source evidence for a binding, or None when it cannot be evidenced.

    A definition line alone is not evidence (#229): the bound symbol must also
    make the calls its role or publication requires.  A symbol that still
    exists while the authority moved elsewhere therefore yields no fact, and
    the rule stays unresolved instead of claiming satisfied.
    """
    path = repo / source
    line = _definition_line(path, symbol) if path.is_file() else None
    if line is None:
        return None
    if required_calls:
        body = _symbol_body(path, symbol, line)
        if body is None or any(marker not in body for marker in required_calls):
            return None
    extractor = "typescript_compiler" if path.suffix == ".ts" else "python_ast"
    return make_evidence(
        path,
        repo,
        f"{path.with_suffix('').as_posix()}.{symbol}",
        line,
        line,
        extractor,
    )


def collect_authority_facts(
    repo: Path, contract: ArchitectureContract
) -> tuple[list[dict[str, object]], list[str]]:
    """Collect only bindings relevant to the supplied contract."""
    operation_ids = {operation.operation_id for operation in contract.operations}
    unit_ids = {unit.unit_id for unit in contract.publication_units}
    facts: list[dict[str, object]] = []
    diagnostics: list[str] = []

    for binding in ROLE_BINDINGS:
        if binding.operation_id not in operation_ids:
            continue
        evidence = _evidence(
            repo, binding.source, binding.symbol, binding.required_calls
        )
        if evidence is None:
            diagnostics.append(
                "authority binding has no source evidence: "
                f"{binding.source}:{binding.symbol} — the definition is absent, or "
                "the call-site evidence the role needs is missing "
                f"({', '.join(binding.required_calls) or 'no required calls'})"
            )
            continue
        facts.append(
            RoleAuthorityFact(
                operation_id=binding.operation_id,
                role=binding.role,
                authorities=binding.authorities,
                evidence=evidence,
            ).to_dict()
        )

    for binding in UNIT_BINDINGS:
        if binding.unit_id not in unit_ids:
            continue
        evidence = _evidence(
            repo, binding.source, binding.symbol, binding.required_calls
        )
        if evidence is None:
            diagnostics.append(
                "authority binding has no source evidence: "
                f"{binding.source}:{binding.symbol} — the definition is absent, or "
                "the call-site evidence the role needs is missing "
                f"({', '.join(binding.required_calls) or 'no required calls'})"
            )
            continue
        facts.append(
            UnitAuthorityFact(
                unit_id=binding.unit_id,
                publication_authorities=binding.publication_authorities,
                authorized_writers=binding.authorized_writers,
                evidence=evidence,
            ).to_dict()
        )

    return facts, diagnostics
