"""Python AST collector (#133).

Tier 1 — direct syntax sinks: filesystem writes (open/Path/os/shutil), SQL
mutation with literal DML, subprocess spawn (recorded unresolved — intent is
never statically inferred).
Tier 2 — versioned wrapper-summary registry entries matched at callsites via
import resolution.
Tier 3 — dynamic/unresolved calls recorded as UnresolvedFact with reason and
low confidence; no target asset or effect is fabricated.

Output is a list of Survey fact dicts plus per-file parse diagnostics. No
execution, import of project code, or network access happens here.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from paperforge.architecture_audit.collectors.common import (
    EffectSpec,
    WrapperSpec,
    WriteSpec,
    make_evidence,
    operation_id_of,
    repo_rel,
)
from paperforge.architecture_audit.layers import (
    CanonicalWriteFact,
    Confidence,
    EffectFact,
    EffectKind,
    EpistemicStatus,
    Evidence,
    SignalFact,
    UnresolvedFact,
)

EXTRACTOR = "python_ast"

# Tier 1 sinks: name -> (effect kind, statement-class note)
_SUBPROCESS_NAMES = frozenset({
    "run", "call", "Popen", "check_output", "check_call", "check_call_output",
})
_SUBPROCESS_MODULES = frozenset({"subprocess"})

_WRITE_METHODS = frozenset({"write_text", "write_bytes", "open", "mkdir"})
_OS_WRITE_NAMES = frozenset({"replace", "rename", "renames"})
_SHUTIL_WRITE_NAMES = frozenset({"move", "copy", "copy2", "copyfile", "copyfileobj"})
_OS_MODULES = frozenset({"os", "os.path", "pathlib", "shutil"})

_SQL_DML = frozenset({"insert", "update", "delete", "replace", "upsert"})

# Attribute call targets that are dynamic by construction.
_DYNAMIC_FUNCS = frozenset({"getattr", "eval", "exec", "globals", "locals", "vars"})

# Methods whose name signals a write/mutation. When the receiver cannot be
# resolved statically the effect cannot be enumerated — recorded unresolved,
# never guessed. Read-only chains (join/get/isoformat/rglob/...) stay silent.
_WRITE_VERBS = frozenset({
    "write", "write_text", "write_bytes", "writeFile", "writeFileSync",
    "appendFile", "appendFileSync", "replace", "rename", "renames", "move",
    "copy", "copy2", "copyfile", "copyfileobj", "unlink", "remove", "delete",
    "rm", "publish", "commit", "save", "dump", "execute", "executemany",
    "insert", "update", "set", "create", "mkdir",
})


@dataclass
class ImportIndex:
    """Per-file import resolution: alias -> fully-qualified module prefix."""

    aliases: dict[str, str] = field(default_factory=dict)
    direct: dict[str, str] = field(default_factory=dict)  # imported name -> module

    @classmethod
    def build(cls, tree: ast.Module, module_root: str) -> ImportIndex:
        index = cls()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    short = alias.asname or alias.name.split(".")[0]
                    index.aliases[short] = alias.name
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    index.direct[alias.asname or alias.name] = (
                        f"{module}.{alias.name}" if module else alias.name
                    )
        return index

    def resolve(self, func: ast.expr) -> str | None:
        """Return a fully-qualified callable name for a Name/Attribute expr."""
        if isinstance(func, ast.Name):
            return self.direct.get(func.id, self.aliases.get(func.id))
        if isinstance(func, ast.Attribute):
            base = func.value
            if isinstance(base, ast.Name):
                prefix = self.aliases.get(base.id) or (
                    self.direct.get(base.id) if base.id in self.direct else None
                )
                if prefix is not None:
                    return f"{prefix}.{func.attr}"
                return f"{base.id}.{func.attr}"
            if isinstance(base, ast.Attribute):
                inner = self.resolve(base)
                if inner is not None:
                    return f"{inner}.{func.attr}"
        return None


@dataclass
class PythonCollectResult:
    facts: list[dict[str, object]] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)
    scanned_files: list[tuple[str, str]] = field(default_factory=list)  # (rel, digest)
    wrapper_hits: list[dict[str, object]] = field(default_factory=list)


_BUILTIN_CONVERTERS = frozenset({
    "str", "int", "float", "bool", "repr", "list", "dict", "set", "tuple",
    "bytes", "bytearray", "format", "Path", "PurePath", "PosixPath",
    "PurePosixPath", "WindowsPath", "PureWindowsPath",
})


def _is_builtin_receiver(expr: ast.expr) -> bool:
    if isinstance(expr, ast.Constant):
        return True
    return (
        isinstance(expr, ast.Call)
        and isinstance(expr.func, ast.Name)
        and expr.func.id in _BUILTIN_CONVERTERS
    )


def _line_span(node: ast.AST) -> tuple[int, int]:
    end = getattr(node, "end_lineno", None) or node.lineno
    return node.lineno, end


def _sql_mutation_kind(arg: ast.expr | None) -> bool:
    """True when a literal SQL statement carries DML (not SELECT)."""
    if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
        return False
    head = arg.value.lstrip().lower()
    return any(head.startswith(word) for word in _SQL_DML)


class _SinkVisitor(ast.NodeVisitor):
    """Collector pass over one parsed module."""

    def __init__(
        self,
        file: Path,
        root: Path,
        module_root: str,
        index: ImportIndex,
        wrappers: tuple[WrapperSpec, ...],
        known_operations: frozenset[str],
        result: PythonCollectResult,
        symbol: str,
    ) -> None:
        self.file = file
        self.root = root
        self.module_root = module_root
        self.index = index
        self.wrappers = wrappers
        self.known_operations = known_operations
        self.result = result
        self.symbol = symbol

    def _evidence(self, node: ast.AST, confidence: Confidence = Confidence.EXACT) -> Evidence:
        start, end = _line_span(node)
        return make_evidence(
            self.file,
            self.root,
            self.symbol,
            start,
            end,
            EXTRACTOR,
            confidence=confidence,
        )

    def _operation(self, node: ast.AST) -> str:
        return operation_id_of(
            repo_rel(self.file, self.root), self.symbol, self.known_operations
        )

    def _tier1_write(self, node: ast.Call, kind: EffectKind) -> None:
        self.result.facts.append(
            EffectFact(
                operation_id=self._operation(node),
                effect_kind=kind,
                evidence=self._evidence(node),
            ).to_dict()
        )

    def _tier3_unresolved(
        self, node: ast.Call, reason: str, effects: tuple[EffectKind, ...]
    ) -> None:
        self.result.facts.append(
            UnresolvedFact(
                unresolved_id=f"unresolved:{repo_rel(self.file, self.root)}:{node.lineno}",
                expression=ast.unparse(node.func)[:120],
                reason=reason,
                possible_effects=effects,
                evidence=self._evidence(node, Confidence.LOW),
                epistemic_status=EpistemicStatus.UNRESOLVED,
            ).to_dict()
        )

    def _match_wrapper(self, qualified: str) -> WrapperSpec | None:
        for spec in self.wrappers:
            if qualified.endswith(spec.qualified_name) or qualified == spec.qualified_name:
                return spec
        return None

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        qualified = self.index.resolve(func)
        if qualified is not None:
            wrapper = self._match_wrapper(qualified)
            if wrapper is not None:
                self._apply_wrapper(node, wrapper)
                return
            tail = qualified.rsplit(".", 1)[-1]
            module_head = qualified.split(".")[0]
            if module_head in _SUBPROCESS_MODULES and tail in _SUBPROCESS_NAMES:
                self._tier3_unresolved(
                    node,
                    f"subprocess {qualified} — remote effect; intent not statically determinable",
                    (EffectKind.REMOTE_OPERATION,),
                )
                return
            if module_head in _OS_MODULES:
                if tail in _OS_WRITE_NAMES:
                    self._tier1_write(node, EffectKind.BUSINESS_MUTATION)
                    return
                if tail in _WRITE_METHODS:
                    self._tier1_write(node, EffectKind.BUSINESS_MUTATION)
                    return
        # raw Name sinks without import resolution
        if isinstance(func, ast.Name):
            if func.id in _SUBPROCESS_NAMES:
                self._tier3_unresolved(
                    node,
                    f"subprocess-like call {func.id} — remote effect; intent not statically determinable",
                    (EffectKind.REMOTE_OPERATION,),
                )
                return
            if func.id in _DYNAMIC_FUNCS:
                self._tier3_unresolved(
                    node,
                    f"dynamic call target {func.id}; cannot enumerate effects",
                    (EffectKind.REMOTE_OPERATION, EffectKind.BUSINESS_MUTATION),
                )
                return
            if func.id in {"execute", "executemany"}:
                self._tier1_write(node, EffectKind.BUSINESS_MUTATION)
                return
        if (
            isinstance(func, ast.Attribute)
            and func.attr in {"execute", "executemany"}
            and _sql_mutation_kind(node.args[0] if node.args else None)
        ):
            self._tier1_write(node, EffectKind.BUSINESS_MUTATION)
            return
        if isinstance(func, ast.Attribute) and func.attr in _WRITE_METHODS:
            self._tier1_write(node, EffectKind.BUSINESS_MUTATION)
            return
        if isinstance(func, ast.Attribute) and qualified is None:
            # Write-verb methods on a statically unresolvable receiver are
            # recorded unresolved (a write exists but the effect cannot be
            # enumerated). Read-only chains (join/get/isoformat/rglob/...) and
            # static attribute chains stay silent — they are not dynamic.
            if func.attr in _WRITE_VERBS:
                # A write-verb on a str/int/Path/etc conversion result is a
                # false positive (str.replace, Path(...).mkdir is real but the
                # receiver is a constructor — handled as a Tier 1 sink for
                # known stdlib; unknown receivers here stay silent).
                if _is_builtin_receiver(func.value):
                    return
                self._tier3_unresolved(
                    node,
                    f"write-like method {func.attr} on unresolvable receiver; "
                    "effect cannot be enumerated",
                    (EffectKind.BUSINESS_MUTATION,),
                )
                return
            if isinstance(func.value, ast.Constant):
                return
        self.generic_visit(node)

    def _apply_wrapper(self, node: ast.Call, wrapper: WrapperSpec) -> None:
        self.result.wrapper_hits.append(
            {
                "wrapper_id": wrapper.wrapper_id,
                "file": repo_rel(self.file, self.root),
                "line": node.lineno,
                "qualified_name": wrapper.qualified_name,
                "version": wrapper.version,
            }
        )
        evidence = self._evidence(node)
        for spec in wrapper.facts:
            if isinstance(spec, EffectSpec):
                self.result.facts.append(
                    EffectFact(
                        operation_id=self._operation(node),
                        effect_kind=spec.effect_kind,
                        intent_mode=spec.intent_mode,
                        evidence=evidence,
                    ).to_dict()
                )
            elif isinstance(spec, WriteSpec):
                self.result.facts.append(
                    CanonicalWriteFact(
                        unit_id=spec.unit_id,
                        actor_kind=spec.actor_kind,
                        via_publication_protocol=spec.via_publication_protocol,
                        writer_id=spec.writer_id,
                        publication_authority=spec.publication_authority,
                        evidence=evidence,
                    ).to_dict()
                )
            else:
                self.result.facts.append(
                    SignalFact(
                        signal_id=spec.signal_id,
                        producer=spec.producer,
                        consumer_kind=spec.consumer_kind,
                        has_code_consumer=spec.has_code_consumer,
                        consumer=spec.consumer,
                        evidence=evidence,
                    ).to_dict()
                )


def collect_python(
    root: Path,
    *,
    wrappers: tuple[WrapperSpec, ...] = (),
    known_operations: frozenset[str] = frozenset(),
    files: list[Path] | None = None,
) -> PythonCollectResult:
    """Collect deterministic facts from Python source under `root`."""
    from paperforge.architecture_audit.collectors.common import discover_sources

    result = PythonCollectResult()
    targets = files if files is not None else discover_sources(root, (".py",))
    for file in targets:
        rel = repo_rel(file, root)
        try:
            source = file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file))
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            result.parse_errors.append(f"{rel}: {exc}")
            result.scanned_files.append((rel, "unparsed"))
            continue
        result.scanned_files.append((rel, _file_digest(file)))
        index = ImportIndex.build(tree, rel)
        symbol = rel.replace("/", ".").removesuffix(".py")
        visitor = _SinkVisitor(
            file, root, rel, index, wrappers, known_operations, result, symbol
        )
        visitor.visit(tree)
    return result


def _file_digest(file: Path) -> str:
    from paperforge.architecture_audit.collectors.common import sha256_file

    return sha256_file(file)
