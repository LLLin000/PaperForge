"""Explicit source bindings for architecture authority facts (#229).

The contract declares the authority identities; this manifest declares the
source symbol that owns each identity.  Collection fails closed when a bound
symbol disappears: the corresponding rule then remains unresolved instead of
copying contract declarations into the survey without source evidence.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from paperforge.architecture_audit.layers import (
    CanonicalWriteFact,
    RoleAuthorityFact,
    UnitAuthorityFact,
)

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
class WriterScan:
    """Observe who writes a unit's artifact, so a foreign writer is visible.

    Function bodies are matched on literals rather than a full data-flow
    analysis: a body that names the artifact *and* its directory *and* uses a
    write primitive is a writer.  Everything outside ``authorized`` yields a
    canonical-write fact, which the reconciler turns into `violated` (#339).

    Known blind spots, measured rather than chased (recorded in #339's follow-up):
    a body that merely *mentions* ``backup`` — even in a comment — is skipped,
    and a publish through ``open(..., "w")`` plus ``os.replace`` is not one of the
    write primitives.  The scan proves the validated shape; it does not prove
    that no other writer exists.
    """

    artifact_markers: tuple[str, ...]
    context_markers: tuple[str, ...]
    authorized: tuple[tuple[str, str], ...]


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
    #: Present only on units whose writers are scanned (#339: the display unit).
    writer_scan: WriterScan | None = None


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
        ("ocr_display.materializer",),
        ("version_history.restore",),
        ("shutil.copy2(", "record_restore_provenance("),
        WriterScan(
            artifact_markers=("fulltext.md",),
            context_markers=("render",),
            authorized=(
                ("paperforge/commands/versions.py", "_run_restore"),
                ("paperforge/worker/ocr_render.py", "write_render_outputs"),
            ),
        ),
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


#: Calls that publish an artifact.  A function body that names the artifact and
#: its directory and uses one of these is treated as a writer (#339).
_WRITE_PRIMITIVES = (
    "write_text(",
    "writeFileSync(",
    "copy2(",
    "atomic_replace_text(",
    "write_string(",
)


def _foreign_writer_facts(repo: Path, binding: UnitBinding) -> list[dict[str, object]]:
    """Canonical-write facts for writers the unit does not authorize.

    Deliberately narrow: only bindings that opt in with a ``WriterScan`` are
    scanned, and only Python sources are read (the plugin reaches the CLI).
    A function outside ``authorized`` that names the artifact, names its
    directory and writes is a violation candidate; the reconciler decides the
    rule status from the fact.
    """
    scan = binding.writer_scan
    if scan is None:
        return []
    authorized = set(scan.authorized)
    facts: list[dict[str, object]] = []
    for path in sorted((repo / "paperforge").glob("**/*.py")):
        rel = path.relative_to(repo).as_posix()
        # Test fixtures and caches are not product writers: the e2e vault builder
        # writes the display artifact on purpose.  A real violation lives in the
        # product tree.
        if any(part in {"test", "tests", "fixtures", "__pycache__"} for part in rel.split("/")):
            continue
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if (rel, node.name) in authorized:
                continue
            segment = ast.get_source_segment(source, node) or ""
            if not all(marker in segment for marker in scan.artifact_markers):
                continue
            if not all(marker in segment for marker in scan.context_markers):
                continue
            if not any(primitive in segment for primitive in _WRITE_PRIMITIVES):
                continue
            # A backup copies the artifact *out* instead of publishing it: the
            # renderer and the restore are the only in-place writers.
            if "backup" in node.name.lower() or "backup" in segment.lower():
                continue
            facts.append(
                CanonicalWriteFact(
                    unit_id=binding.unit_id,
                    actor_kind="backend",
                    via_publication_protocol=False,
                    writer_id=f"{rel}:{node.name}",
                    publication_authority=None,
                    evidence=make_evidence(
                        path,
                        repo,
                        f"{path.with_suffix('').as_posix()}.{node.name}",
                        node.lineno,
                        node.lineno,
                        "python_ast",
                    ),
                ).to_dict()
            )
    return facts


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

    # Writer scans run independently of the bound-symbol evidence: a foreign
    # writer is a violation even when the authorized publisher is intact (#339).
    for binding in UNIT_BINDINGS:
        if binding.unit_id in unit_ids and binding.writer_scan is not None:
            facts.extend(_foreign_writer_facts(repo, binding))

    return facts, diagnostics
