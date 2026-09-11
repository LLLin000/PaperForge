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


@dataclass(frozen=True)
class UnitBinding:
    source: str
    symbol: str
    unit_id: str
    publication_authorities: tuple[str, ...]
    authorized_writers: tuple[str, ...]


ROLE_BINDINGS: tuple[RoleBinding, ...] = (
    RoleBinding(
        "paperforge/worker/ocr.py",
        "run_ocr",
        "ocr_run",
        "execution",
        ("backend.ocr.executor",),
    ),
    RoleBinding(
        "paperforge/plugin/src/views/ocr-workspace.ts",
        "_stopBuild",
        "ocr_rebuild",
        "stop",
        ("plugin.ocr_process_controller",),
    ),
    RoleBinding(
        "paperforge/plugin/src/settings.ts",
        "_renderMemoryDetail",
        "embed_build_resume",
        "stop",
        ("plugin.embed_build_controller",),
    ),
)

UNIT_BINDINGS: tuple[UnitBinding, ...] = (
    UnitBinding(
        "paperforge/commands/versions.py",
        "_run_restore",
        "ocr_display.fulltext",
        ("version_history.authority",),
        ("version_history.restore",),
    ),
    UnitBinding(
        "paperforge/memory/builder.py",
        "build_for_keys",
        "retrieval.units",
        ("memory.publisher",),
        ("memory.builder",),
    ),
    UnitBinding(
        "paperforge/memory/builder.py",
        "build_for_keys",
        "retrieval.fts",
        ("memory.publisher",),
        ("memory.builder",),
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


def _evidence(repo: Path, source: str, symbol: str):
    path = repo / source
    line = _definition_line(path, symbol) if path.is_file() else None
    if line is None:
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
        evidence = _evidence(repo, binding.source, binding.symbol)
        if evidence is None:
            diagnostics.append(
                f"authority binding missing or ambiguous: {binding.source}:{binding.symbol}"
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
        evidence = _evidence(repo, binding.source, binding.symbol)
        if evidence is None:
            diagnostics.append(
                f"authority binding missing or ambiguous: {binding.source}:{binding.symbol}"
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
