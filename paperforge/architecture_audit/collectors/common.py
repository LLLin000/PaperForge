"""Shared collector infrastructure (#133).

Exclusion rules, file digests, symbol/line helpers, and the versioned wrapper
registry. The registry is extractor knowledge (Tier 2) and stays separate from
ArchitectureContract policy — validation of both is independently tested.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from paperforge.architecture_audit.layers import (
    ArgumentRole,
    Confidence,
    EffectKind,
    EpistemicStatus,
    Evidence,
    IntentMode,
    SignalConsumerKind,
)

# ---------------------------------------------------------------- exclusions

# Source scope excludes generated bundles, dependencies, nested repositories,
# worktrees, caches, and temp artifacts. Tests are linked separately as
# coverage evidence, not scanned as production source.
EXCLUDED_DIR_NAMES = frozenset({
    ".git",
    ".worktrees",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".mypy_cache",
    ".hypothesis",
})

EXCLUDED_FILE_SUFFIXES = frozenset({
    ".min.js",
    ".min.css",
    ".map",
    ".pyc",
    ".pyo",
})

EXCLUDED_FILE_NAMES = frozenset({
    "main.js",  # generated plugin bundle
    "versions.json",
})

_SKIP_RE = re.compile(r"(?:^|/)(?:tests?|test_assets?)/", re.IGNORECASE)


def is_excluded(path: Path, root: Path, *, exclude_tests: bool = True) -> bool:
    """True when `path` falls outside the deterministic source scope."""
    rel = path.relative_to(root)
    parts = rel.parts
    if any(part in EXCLUDED_DIR_NAMES for part in parts):
        return True
    if path.suffix in EXCLUDED_FILE_SUFFIXES:
        return True
    if path.name in EXCLUDED_FILE_NAMES:
        return True
    return bool(exclude_tests and _SKIP_RE.search(rel.as_posix()))


def discover_sources(root: Path, suffixes: tuple[str, ...], *, exclude_tests: bool = True) -> list[Path]:
    """Deterministic source listing under `root`, exclusion-aware."""
    out: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix not in suffixes:
            continue
        if is_excluded(path, root, exclude_tests=exclude_tests):
            continue
        out.append(path)
    return out


def canonical_source_bytes(data: bytes) -> bytes:
    """Canonical source bytes for content digests: CRLF → LF.

    Windows checkout (CRLF) vs CI checkout (LF) must not produce different
    fingerprints — the digest means content, not line-ending style.  This is
    the single canonicalization the golden verifier mirrors.
    """
    return data.replace(b"\r\n", b"\n")


def sha256_file(path: Path) -> str:
    """Content digest of a source file (canonicalized, see
    :func:`canonical_source_bytes`)."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(canonical_source_bytes(chunk))
    return "sha256:" + digest.hexdigest()


def repo_rel(path: Path, root: Path) -> str:
    """POSIX repository-relative path for evidence."""
    return str(PurePosixPath(path.relative_to(root).as_posix()))


# ---------------------------------------------------------------- operation id

# module stem -> operation id for contract operation scoping. Only stems that
# appear in a Contract.operations list are mapped; anything else keeps the
# full `module.function` symbol as its operation id (still recorded, never
# matched against a rule subject).
def operation_id_of(rel_posix: str, symbol: str, known_operations: frozenset[str]) -> str:
    stem = PurePosixPath(rel_posix).stem
    if stem in known_operations:
        return stem
    return f"{stem}.{symbol}"


# ---------------------------------------------------------------- evidence

def make_evidence(
    file: Path,
    root: Path,
    symbol: str,
    line_start: int,
    line_end: int,
    extractor: str,
    *,
    epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVED_STATIC,
    confidence: Confidence = Confidence.EXACT,
) -> Evidence:
    """Build evidence with a stable id (computed by the Evidence layer)."""
    return Evidence(
        file=repo_rel(file, root),
        file_digest=sha256_file(file),
        symbol=symbol,
        line_start=line_start,
        line_end=line_end,
        extractor=extractor,
        epistemic_status=epistemic_status,
        confidence=confidence,
    )


# ---------------------------------------------------------------- wrapper registry

@dataclass(frozen=True)
class EffectSpec:
    effect_kind: EffectKind
    intent_mode: IntentMode | None = None


@dataclass(frozen=True)
class WriteSpec:
    unit_id: str
    via_publication_protocol: bool
    writer_id: str
    publication_authority: str
    actor_kind: str = "backend"


@dataclass(frozen=True)
class SignalSpec:
    signal_id: str
    producer: str
    consumer_kind: SignalConsumerKind
    has_code_consumer: bool = False
    consumer: str | None = None


@dataclass(frozen=True)
class WrapperSpec:
    wrapper_id: str
    qualified_name: str  # `module.func` tail-matched against callsites
    facts: tuple[EffectSpec | WriteSpec | SignalSpec, ...]
    confidence: Confidence = Confidence.EXACT
    version: int = 1
    argument_roles: tuple[ArgumentRole, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "wrapper_id": self.wrapper_id,
            "qualified_name": self.qualified_name,
            "version": self.version,
            "confidence": self.confidence.value,
            "argument_roles": [r.value for r in self.argument_roles],
            "facts": [_spec_dict(f) for f in self.facts],
        }


def _spec_dict(spec: EffectSpec | WriteSpec | SignalSpec) -> dict[str, Any]:
    if isinstance(spec, EffectSpec):
        out: dict[str, Any] = {"kind": "effect", "effect_kind": spec.effect_kind.value}
        if spec.intent_mode is not None:
            out["intent_mode"] = spec.intent_mode.value
        return out
    if isinstance(spec, WriteSpec):
        return {
            "kind": "write",
            "unit_id": spec.unit_id,
            "via_publication_protocol": spec.via_publication_protocol,
            "writer_id": spec.writer_id,
            "publication_authority": spec.publication_authority,
            "actor_kind": spec.actor_kind,
        }
    return {
        "kind": "signal",
        "signal_id": spec.signal_id,
        "producer": spec.producer,
        "consumer_kind": spec.consumer_kind.value,
        "has_code_consumer": spec.has_code_consumer,
        **({"consumer": spec.consumer} if spec.consumer else {}),
    }


def load_wrapper_registry(payload: list[dict[str, Any]]) -> tuple[WrapperSpec, ...]:
    """Validate an external wrapper-registry payload (separate from Contract)."""
    out: list[WrapperSpec] = []
    for row in payload:
        wrapper_id = row.get("wrapper_id")
        qualified_name = row.get("qualified_name")
        if not isinstance(wrapper_id, str) or not wrapper_id:
            raise ValueError("wrapper registry entry missing string wrapper_id")
        if not isinstance(qualified_name, str) or "." not in qualified_name:
            raise ValueError(f"wrapper {wrapper_id!r}: qualified_name must be module.func")
        facts: list[EffectSpec | WriteSpec | SignalSpec] = []
        for spec in row.get("facts", []):
            kind = spec.get("kind")
            if kind == "effect":
                facts.append(
                    EffectSpec(
                        effect_kind=EffectKind(spec["effect_kind"]),
                        intent_mode=IntentMode(spec["intent_mode"]) if spec.get("intent_mode") else None,
                    )
                )
            elif kind == "write":
                facts.append(
                    WriteSpec(
                        unit_id=spec["unit_id"],
                        via_publication_protocol=bool(spec.get("via_publication_protocol", False)),
                        writer_id=spec["writer_id"],
                        publication_authority=spec["publication_authority"],
                        actor_kind=spec.get("actor_kind", "backend"),
                    )
                )
            elif kind == "signal":
                facts.append(
                    SignalSpec(
                        signal_id=spec["signal_id"],
                        producer=spec["producer"],
                        consumer_kind=SignalConsumerKind(spec["consumer_kind"]),
                        has_code_consumer=bool(spec.get("has_code_consumer", False)),
                        consumer=spec.get("consumer"),
                    )
                )
            else:
                raise ValueError(f"wrapper {wrapper_id!r}: unknown fact kind {kind!r}")
        if not facts:
            raise ValueError(f"wrapper {wrapper_id!r}: at least one fact required")
        out.append(
            WrapperSpec(
                wrapper_id=wrapper_id,
                qualified_name=qualified_name,
                facts=tuple(facts),
                confidence=Confidence(row.get("confidence", "exact")),
                version=int(row.get("version", 1)),
                argument_roles=tuple(ArgumentRole(r) for r in row.get("argument_roles", [])),
            )
        )
    return tuple(out)


# Registry shipped with the collector: wrapper knowledge accumulated by #126/
# #127/#129/#99 verification (#132 "repeated legwork"), versioned separately
# from ArchitectureContract policy.
DEFAULT_PYTHON_REGISTRY: tuple[WrapperSpec, ...] = (
    WrapperSpec(
        wrapper_id="ocr_hash.publish_ocr_result_hash",
        qualified_name="ocr_hash.publish_ocr_result_hash",
        facts=(
            WriteSpec(
                unit_id="ocr_derived.generation",
                via_publication_protocol=True,
                writer_id="ocr.postprocess",
                publication_authority="ocr.publisher",
            ),
        ),
        confidence=Confidence.EXACT,
    ),
    WrapperSpec(
        wrapper_id="ocr_hash.create_result_hash_pending",
        qualified_name="ocr_hash.create_result_hash_pending",
        facts=(
            EffectSpec(
                effect_kind=EffectKind.BUSINESS_MUTATION,
            ),
        ),
        confidence=Confidence.EXACT,
    ),
    WrapperSpec(
        wrapper_id="sync.attach_next_actions",
        qualified_name="sync._attach_next_actions",
        facts=(
            EffectSpec(
                effect_kind=EffectKind.DISPOSABLE_SNAPSHOT,
                intent_mode=IntentMode.DIRECT_INVOCATION,
            ),
        ),
        confidence=Confidence.EXACT,
    ),
    WrapperSpec(
        wrapper_id="sync.run_terminal_followups",
        qualified_name="sync._run_terminal_followups",
        facts=(
            EffectSpec(
                effect_kind=EffectKind.MATERIALIZATION_BUILD,
                intent_mode=IntentMode.DIRECT_INVOCATION,
            ),
        ),
        confidence=Confidence.EXACT,
    ),
    WrapperSpec(
        wrapper_id="ocr.recover_redo_orphans",
        qualified_name="ocr.recover_redo_orphans",
        facts=(
            EffectSpec(
                effect_kind=EffectKind.BUSINESS_MUTATION,
            ),
        ),
        confidence=Confidence.EXACT,
    ),
)


def load_default_python_registry() -> tuple[WrapperSpec, ...]:
    return DEFAULT_PYTHON_REGISTRY


def to_wrapper_summaries(specs: tuple[WrapperSpec, ...]) -> tuple[Any, ...]:
    """Map registry specs to Survey WrapperSummary rows (same schema as #131)."""
    from paperforge.architecture_audit.layers import WrapperSummary

    summaries: list[WrapperSummary] = []
    for spec in specs:
        effect_kinds: list[EffectKind] = []
        for fact in spec.facts:
            if isinstance(fact, EffectSpec):
                effect_kinds.append(fact.effect_kind)
        summaries.append(
            WrapperSummary(
                wrapper_id=spec.wrapper_id,
                qualified_symbol=spec.qualified_name,
                effect_kinds=tuple(dict.fromkeys(effect_kinds)),
                argument_roles=spec.argument_roles,
                confidence=spec.confidence,
            )
        )
    return tuple(summaries)
