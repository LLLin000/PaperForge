#!/usr/bin/env python3
"""Paperforge module dependency and call-graph gate (P0).

Static ceiling (honest limits, not bugs): every rule below reads syntax
with :mod:`ast` only. Dynamic imports (``importlib`` with a computed
string, ``__import__``), dependency injection, and monkeypatching are
invisible to this gate; ``--reach`` likewise follows only syntactic call
sites (``name()`` / ``mod.func()`` / ``self.method()``). Anything dynamic
must stay covered by runtime tests, not by this script.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = REPO_ROOT / "paperforge"
RATCHET_PATH = REPO_ROOT / "tests" / "architecture_import_ratchet.json"

#: Top-level distributions that must stay out of module scope. ``pymupdf``
#: is the canonical import name of the ``fitz`` distribution, so both are
#: listed; either one at module level counts as heavy.
HEAVY_TOP_LEVELS = ("torch", "chromadb", "fitz", "pymupdf", "pdfplumber", "PIL")

#: Subtrees a worker module must never import (R3).
FORBIDDEN_WORKER_TARGETS = ("paperforge.commands", "paperforge.plugin")

#: Plan stop condition: with this many pre-existing rings, R1 degrades to
#: "no new rings" instead of "no rings" so P0 stays a gate, not a refactor.
CYCLE_DOWNGRADE_THRESHOLD = 10


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__") and len(name) > 4


def iter_modules() -> dict[str, Path]:
    """Dotted module name -> file, sorted for determinism."""
    found: dict[str, Path] = {}
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        rel = path.relative_to(REPO_ROOT)
        dotted = ".".join(rel.with_suffix("").parts)
        if path.name == "__init__.py":
            dotted = ".".join(rel.parent.parts)
        found[dotted] = path
    return found


def _packages(modules: dict[str, Path]) -> set[str]:
    return {mod for mod, path in modules.items() if path.name == "__init__.py"}


def _package_of(mod: str, packages: set[str]) -> str:
    if mod in packages:
        return mod
    return mod.rpartition(".")[0] or mod


def resolve_import(
    importer: str, node: ast.Import | ast.ImportFrom, packages: set[str]
) -> list[tuple[str, str | None]]:
    """Return ``(target_module, imported_name)`` pairs.

    Plain ``import a.b`` yields ``("a.b", None)``; ``from m import n``
    yields ``("m", "n")``. Relative imports resolve against the importer's
    package. Targets outside ``paperforge`` are dropped by the callers.
    """
    if isinstance(node, ast.Import):
        return [(alias.name, None) for alias in node.names]
    if node.level == 0:
        base = node.module or ""
    else:
        pkg = _package_of(importer, packages)
        for _ in range(node.level - 1):
            pkg = pkg.rpartition(".")[0]
        base = f"{pkg}.{node.module}".strip(".") if node.module else pkg
    return [(base, alias.name) for alias in node.names]


def _scope_imports(nodes: list[ast.stmt], *, include_classes: bool) -> list[ast.AST]:
    """Return imports executed in this scope, skipping nested function bodies."""
    found: list[ast.AST] = []
    stack = list(reversed(nodes))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            found.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or (
            isinstance(node, ast.ClassDef) and not include_classes
        ):
            continue
        elif _is_type_checking_guard(node):
            continue
        else:
            stack.extend(reversed(list(ast.iter_child_nodes(node))))
    found.sort(key=lambda n: (n.lineno, n.col_offset))
    return found


def _module_scope_imports(tree: ast.Module) -> list[ast.AST]:
    """Imports executed at module import, including class suites."""
    return _scope_imports(tree.body, include_classes=True)


def _import_bindings(
    nodes: list[ast.AST], mod: str, packages: set[str]
) -> dict[str, tuple[str, str | None]]:
    imports: dict[str, tuple[str, str | None]] = {}
    for node in nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports[(alias.asname or alias.name).split(".")[0]] = (alias.name, None)
        elif isinstance(node, ast.ImportFrom):
            for (target, name), alias in zip(resolve_import(mod, node, packages), node.names):
                imports[alias.asname or alias.name] = (target, name)
    return imports


def _is_type_checking_guard(node: ast.AST) -> bool:
    if not isinstance(node, ast.If):
        return False
    test = node.test
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    return isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"

def _dep_targets(target: str, name: str | None, known: set[str]) -> list[str]:
    """Module dependencies denoted by one import.

    ``from P import S`` where ``P.S`` is a real module (including
    ``from . import sibling`` and ``from paperforge import commands``)
    depends on ``P.S``, not just ``P``. A reference to the importer's own
    name (``from P import M`` inside ``P/M.py``) resolves the partially
    initialized ``sys.modules`` entry for ``M`` itself: a true self edge.
    """
    if not target.startswith("paperforge"):
        return []
    if name:
        child = f"{target}.{name}"
        if child in known:
            return [child]
    return [target]


def _nearest_known(target: str, known: set[str]) -> str | None:
    if target in known:
        return target
    parts = target.split(".")
    while parts:
        candidate = ".".join(parts)
        if candidate in known:
            return candidate
        parts.pop()
    return None


def _top(mod: str) -> str:
    rest = mod[len("paperforge.") :] if mod.startswith("paperforge.") else mod
    return rest.split(".")[0]


def _parse(path: Path) -> ast.Module:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        raise SystemExit(f"error: cannot parse {path}: {exc}") from exc


def collect_graph(
    modules: dict[str, Path], trees: dict[str, ast.Module], packages: set[str]
) -> dict[str, set[str]]:
    """Module-scope import graph restricted to paperforge.

    Edges represent explicit imports only; package initialization is not
    synthesized. True self-imports are kept as self-loops for R1 to report.
    """
    known = set(modules)
    graph: dict[str, set[str]] = {mod: set() for mod in modules}
    for mod, tree in trees.items():
        for node in _module_scope_imports(tree):
            assert isinstance(node, (ast.Import, ast.ImportFrom))
            for target, name in resolve_import(mod, node, packages):
                for dep in _dep_targets(target, name, known):
                    resolved = _nearest_known(dep, known)
                    if resolved:
                        graph[mod].add(resolved)
    return graph


def find_rings(graph: dict[str, set[str]]) -> list[list[str]]:
    """Strongly connected components of size > 1, plus true self-loops."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    rings: list[list[str]] = []
    counter = 0
    for root in sorted(graph):
        if root in index:
            continue
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        work: list[tuple[str, object]] = [(root, iter(sorted(graph[root])))]
        while work:
            node, it = work[-1]
            descended = False
            for succ in it:
                if succ not in index:
                    index[succ] = low[succ] = counter
                    counter += 1
                    stack.append(succ)
                    on_stack.add(succ)
                    work.append((succ, iter(sorted(graph[succ]))))
                    descended = True
                    break
                elif succ in on_stack:
                    low[node] = min(low[node], index[succ])
            if descended:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
            if low[node] == index[node]:
                ring: list[str] = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    ring.append(member)
                    if member == node:
                        break
                if len(ring) > 1:
                    rings.append(sorted(ring))
    in_multi = {m for ring in rings for m in ring}
    for mod in sorted(graph):
        if mod in graph[mod] and mod not in in_multi:
            rings.append([mod])
    rings.sort()
    return rings


def ring_key(ring: list[str]) -> str:
    return "ring:" + ",".join(ring)


def _is_worker(mod: str) -> bool:
    return mod == "paperforge.worker" or mod.startswith("paperforge.worker.")


def _is_forbidden_worker_target(target: str) -> bool:
    return any(target == root or target.startswith(root + ".") for root in FORBIDDEN_WORKER_TARGETS)


def _aliases_from_imports(
    mod: str, nodes: list[ast.AST], packages: set[str], known: set[str]
) -> dict[str, str]:
    """Local name -> fully qualified paperforge module for module imports only."""
    aliases: dict[str, str] = {}
    for node in nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not alias.name.startswith("paperforge"):
                    continue
                if alias.asname:
                    aliases[alias.asname] = alias.name
                else:
                    aliases.setdefault(alias.name.split(".")[0], alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for (target, name), item in zip(resolve_import(mod, node, packages), node.names):
                if not target.startswith("paperforge") or name is None or name == "*":
                    continue
                if f"{target}.{name}" in known:
                    aliases[item.asname or name] = f"{target}.{name}"
                # else: function/class/object import -- not a module alias, ignore
    return aliases


def _resolve_attr_base(value: ast.AST, aliases: dict[str, str]) -> str | None:
    """Resolve an attribute base to a fully qualified dotted path via module aliases."""
    parts: list[str] = []
    node = value
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    parts.reverse()
    if parts[0] not in aliases:
        return None
    base = aliases[parts[0]]
    if len(parts) > 1:
        base = base + "." + ".".join(parts[1:])
    return base


class _LocalShadows(ast.NodeVisitor):
    """Names bound in one function scope, excluding nested functions/lambdas."""

    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.names.add(node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.names.add(node.name)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        pass

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.names.add(node.name)
        for dec in node.decorator_list:
            self.visit(dec)
        for base in node.bases:
            self.visit(base)
        for kw in node.keywords:
            self.visit(kw)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self.names.add(node.name)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            self.names.add(node.id)


def _local_shadows(
    mod: str,
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    packages: set[str],
    known: set[str],
    local_aliases: dict[str, str],
) -> set[str]:
    """Names in ``func`` that hide a module-level alias (params, stores, non-module imports)."""
    shadows: set[str] = set()
    args = func.args
    for arg in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs):
        shadows.add(arg.arg)
    if args.vararg is not None:
        shadows.add(args.vararg.arg)
    if args.kwarg is not None:
        shadows.add(args.kwarg.arg)
    visitor = _LocalShadows()
    for stmt in func.body:
        visitor.visit(stmt)
    shadows.update(visitor.names)
    for node in _scope_imports(func.body, include_classes=True):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = (alias.asname or alias.name).split(".")[0]
                if bound not in local_aliases:
                    shadows.add(bound)
        elif isinstance(node, ast.ImportFrom):
            for (target, name), item in zip(resolve_import(mod, node, packages), node.names):
                bound = item.asname or item.name
                if bound == "*":
                    continue
                if bound not in local_aliases:
                    shadows.add(bound)
    return shadows


def _scoped_attributes(
    tree: ast.Module,
) -> list[tuple[ast.FunctionDef | ast.AsyncFunctionDef | None, ast.Attribute]]:
    """Every ``Attribute`` node with its innermost enclosing function (if any).

    Decorators and default values belong to the enclosing scope; only the
    body runs in the function's own scope.
    """
    found: list = []

    def visit(node: ast.AST, owner: ast.AST | None) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                visit(dec, owner)
            defaults = list(node.args.defaults) + [d for d in node.args.kw_defaults if d is not None]
            for default in defaults:
                visit(default, owner)
            for arg in (
                list(node.args.posonlyargs)
                + list(node.args.args)
                + list(node.args.kwonlyargs)
                + ([node.args.vararg] if node.args.vararg is not None else [])
                + ([node.args.kwarg] if node.args.kwarg is not None else [])
            ):
                if arg.annotation is not None:
                    visit(arg.annotation, owner)
            if node.returns is not None:
                visit(node.returns, owner)
            for stmt in node.body:
                visit(stmt, node)
            return
        if isinstance(node, ast.Attribute):
            found.append((owner, node))
        for child in ast.iter_child_nodes(node):
            visit(child, owner)

    visit(tree, None)
    return found


def collect_private_member_accesses(
    modules: dict[str, Path], trees: dict[str, ast.Module], packages: set[str]
) -> dict[str, list[dict]]:
    """Cross-module ``module._private`` attribute uses, keyed by importing module.

    Values are ``{"line": int, "target_module": str, "member": str}`` objects
    sorted by ``(line, target_module, member)``. Only non-dunder private
    attribute names count, and only when the base resolves through a module
    import alias to a *known* module different from the importer (same-file
    use stays allowed; ``module._private._nested`` does not resolve to a
    known module, so only the inner access is reported). Module-level
    aliases are visible inside functions unless shadowed by a parameter,
    a local binding, or a non-module import; function-level imports never
    leak into other scopes. Dynamic access (``getattr``, ``__import__``)
    is invisible -- static limit.
    """
    known = set(modules)
    found: dict[str, set[tuple[int, str, str]]] = {}
    for mod, tree in trees.items():
        module_aliases = _aliases_from_imports(mod, _module_scope_imports(tree), packages, known)
        scope_cache: dict[int, dict[str, str]] = {}

        def effective(
            owner: ast.FunctionDef | ast.AsyncFunctionDef | None,
        ) -> dict[str, str]:
            if owner is None:
                return module_aliases
            key = id(owner)
            if key not in scope_cache:
                local = _aliases_from_imports(
                    mod, _scope_imports(owner.body, include_classes=True), packages, known
                )
                shadows = _local_shadows(mod, owner, packages, known, local)
                eff = {k: v for k, v in module_aliases.items() if k not in shadows}
                eff.update(local)
                scope_cache[key] = eff
            return scope_cache[key]

        for owner, node in _scoped_attributes(tree):
            member = node.attr
            if not member.startswith("_") or _is_dunder(member):
                continue
            target = _resolve_attr_base(node.value, effective(owner))
            if target is None or target not in known:
                continue
            if target == mod:
                continue
            found.setdefault(mod, set()).add((node.lineno, target, member))
    return {
        mod: [
            {"line": line, "target_module": target, "member": member}
            for (line, target, member) in sorted(keys)
        ]
        for mod, keys in sorted(found.items())
    }


def collect_violations(
    modules: dict[str, Path], trees: dict[str, ast.Module], packages: set[str]
) -> tuple[dict[str, list[str]], dict[str, list[str]], dict[str, list[str]]]:
    """Return (private, layer, heavy) violations keyed by importing module.

    R2/R3 scan every import site (including function-level ones, which would
    otherwise hide a dependency); R4 scans module scope only -- guarded
    ``try``/``if`` imports count, ``def`` bodies and ``TYPE_CHECKING``
    blocks do not -- since a lazy function-level heavy import is the
    sanctioned pattern.
    """
    known = set(modules)
    private: dict[str, set[str]] = {}
    layer: dict[str, set[str]] = {}
    heavy: dict[str, set[str]] = {}

    def add(bucket: dict[str, set[str]], mod: str, key: str) -> None:
        bucket.setdefault(mod, set()).add(key)

    for mod, tree in trees.items():
        worker = _is_worker(mod)
        scope_ids = {id(node) for node in _module_scope_imports(tree)}
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            module_level = id(node) in scope_ids
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = alias.name
                    if target.startswith("paperforge"):
                        for dep in _dep_targets(target, None, known):
                            if worker and _is_forbidden_worker_target(dep):
                                add(layer, mod, f"{node.lineno}:{dep}")
                            segments = dep.split(".")[1:]
                            if (
                                any(s.startswith("_") and not _is_dunder(s) for s in segments)
                                and _top(mod) != _top(dep)
                            ):
                                add(private, mod, f"{node.lineno}:{dep}")
                    elif module_level and target.split(".")[0] in HEAVY_TOP_LEVELS:
                        add(heavy, mod, f"{node.lineno}:{target.split('.')[0]}")
                continue
            for target, name in resolve_import(mod, node, packages):
                if target.startswith("paperforge"):
                    for dep in _dep_targets(target, name, known):
                        if worker and _is_forbidden_worker_target(dep):
                            add(layer, mod, f"{node.lineno}:{dep}:{name}")
                        segments = dep.split(".")[1:]
                        if (
                            any(s.startswith("_") and not _is_dunder(s) for s in segments)
                            and _top(mod) != _top(dep)
                        ):
                            add(private, mod, f"{node.lineno}:{dep}")
                    if (
                        name is not None
                        and name.startswith("_")
                        and not _is_dunder(name)
                        and _top(mod) != _top(target)
                    ):
                        add(private, mod, f"{node.lineno}:{target}:{name}")
                elif module_level and (node.module or "").split(".")[0] in HEAVY_TOP_LEVELS:
                    add(heavy, mod, f"{node.lineno}:{(node.module or '').split('.')[0]}")
    sort = lambda bucket: {mod: sorted(keys) for mod, keys in sorted(bucket.items())}
    return sort(private), sort(layer), sort(heavy)


def load_ratchet() -> dict | None:
    if not RATCHET_PATH.exists():
        return None
    return json.loads(RATCHET_PATH.read_text(encoding="utf-8"))


def build_snapshot() -> dict:
    modules = iter_modules()
    packages = _packages(modules)
    trees = {mod: _parse(path) for mod, path in modules.items()}
    graph = collect_graph(modules, trees, packages)
    rings = find_rings(graph)
    private, layer, heavy = collect_violations(modules, trees, packages)
    member_accesses = collect_private_member_accesses(modules, trees, packages)
    return {
        "version": 1,
        "r1_no_new_rings": len(rings) >= CYCLE_DOWNGRADE_THRESHOLD,
        "rings": [ring_key(r) for r in rings],
        "private_imports": private,
        "layer_violations": layer,
        "heavy_imports": heavy,
        "private_member_accesses": member_accesses,
    }


def _new_entries(
    current: dict[str, list[str]], allowed: dict[str, list[str]]
) -> dict[str, list[str]]:
    extra: dict[str, list[str]] = {}
    for mod in sorted(set(current) | set(allowed)):
        diff = sorted(set(current.get(mod, [])) - set(allowed.get(mod, [])))
        if diff:
            extra[mod] = diff
    return extra


def check(snapshot: dict, ratchet: dict) -> list[str]:
    """Return human-readable failures; empty means the gate passes.

    Stale ratchet entries (fixed since the snapshot) never fail: the
    ratchet may only shrink, and shrinking is reported by re-running
    ``--write-ratchet``, not by turning ``--check`` red.
    ``private_member_access_exceptions`` allowlists exact
    ``"target_module:member"`` strings per importer, ignoring line numbers.
    """
    failures: list[str] = []
    current_rings = set(snapshot["rings"])
    frozen_rings = set(ratchet.get("rings", []))
    if ratchet.get("r1_no_new_rings") or len(frozen_rings) >= CYCLE_DOWNGRADE_THRESHOLD:
        new_rings = sorted(current_rings - frozen_rings)
        if new_rings:
            failures.append(f"R1: new import rings: {new_rings} (frozen: {sorted(frozen_rings)})")
    elif current_rings:
        failures.append(f"R1: import rings (must be zero): {sorted(current_rings)}")
    for rule, key in (
        ("R2: cross-package private imports", "private_imports"),
        ("R3: worker -> commands/plugin imports", "layer_violations"),
        ("R4: new top-level heavy imports", "heavy_imports"),
    ):
        extra = _new_entries(snapshot.get(key, {}), ratchet.get(key, {}))
        if extra:
            details = "; ".join(f"{mod}: {keys}" for mod, keys in extra.items())
            failures.append(f"{rule}: {details}")
    member_exceptions: dict[str, list[str]] = ratchet.get("private_member_access_exceptions", {})
    extra_members: dict[str, list[str]] = {}
    current_members: dict[str, list[dict]] = snapshot.get("private_member_accesses", {})
    for mod in sorted(set(current_members) | set(member_exceptions)):
        allowed = set(member_exceptions.get(mod, []))
        remaining = sorted(
            f'{entry["line"]}:{entry["target_module"]}:{entry["member"]}'
            for entry in current_members.get(mod, [])
            if f'{entry["target_module"]}:{entry["member"]}' not in allowed
        )
        if remaining:
            extra_members[mod] = remaining
    if extra_members:
        details = "; ".join(f"{mod}: {keys}" for mod, keys in extra_members.items())
        failures.append(f"R2b: cross-module private member accesses: {details}")
    return failures


# ---------------------------------------------------------------------------
# --reach
# ---------------------------------------------------------------------------


def _module_defs(
    mod: str, tree: ast.Module, packages: set[str]
) -> tuple[
    dict[str, ast.FunctionDef | ast.AsyncFunctionDef],
    dict[str, tuple[str, str | None]],
]:
    """Return (qualname -> function node, module-scope import bindings)."""
    funcs: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}

    def visit(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs[f"{prefix}{child.name}"] = child
                visit(child, f"{prefix}{child.name}.")
            elif isinstance(child, ast.ClassDef):
                visit(child, f"{prefix}{child.name}.")

    visit(tree, "")
    imports = _import_bindings(
        _scope_imports(tree.body, include_classes=False), mod, packages
    )
    return funcs, imports


def _resolve_callee(
    tmod: str,
    tname: str | None,
    attr: str | None,
    known: set[str] | dict,
    has_func,
) -> str | None:
    """Follow an import binding to ``mod:qual``; None if unresolvable.

    ``tname`` is the imported name (None for plain ``import x.y`` bindings);
    ``attr`` is the called attribute (None for bare ``name()`` calls). A
    binding whose imported name is itself a submodule (``from P import S``,
    ``from . import S``) redirects into that submodule; calling the
    submodule itself is unresolvable.
    """
    if tmod not in known:
        return None
    if tname is not None and f"{tmod}.{tname}" in known:
        child = f"{tmod}.{tname}"
        if attr is not None and has_func(child, attr):
            return f"{child}:{attr}"
        return None
    if attr is None:
        if tname is not None and has_func(tmod, tname):
            return f"{tmod}:{tname}"
    elif tname is None and has_func(tmod, attr):
        return f"{tmod}:{attr}"
    return None


def _function_calls(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Call]:
    """Calls in this function body, excluding nested definitions."""
    calls: list[ast.Call] = []
    stack = list(reversed(function.body))
    while stack:
        node = stack.pop()
        if isinstance(node, ast.Call):
            calls.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        stack.extend(reversed(list(ast.iter_child_nodes(node))))
    return calls


def reach(entry: str) -> tuple[list[str], int]:
    """Breadth-first walk of the syntactic call graph from ``mod:func``.

    Modules are parsed lazily: only the entry module and the paperforge
    modules it (transitively) calls are read. Returns the sorted
    ``mod:qualname`` set plus the count of call sites left unresolved
    (external, builtin, or dynamic -- the documented static limit).
    """

    if ":" not in entry:
        raise SystemExit("error: --entry must look like paperforge.worker.ocr_figures:build_figure_inventory")
    entry_mod, _, entry_func = entry.partition(":")
    modules = iter_modules()
    if entry_mod not in modules:
        raise SystemExit(f"error: unknown module {entry_mod}")
    packages = _packages(modules)
    trees: dict[str, ast.Module] = {}
    defs_cache: dict[str, tuple[dict, dict]] = {}

    def get_defs(mod: str) -> tuple[dict, dict]:
        if mod not in defs_cache:
            if mod not in trees:
                trees[mod] = _parse(modules[mod])
            defs_cache[mod] = _module_defs(mod, trees[mod], packages)
        return defs_cache[mod]

    def has_func(mod: str, qual: str) -> bool:
        return qual in get_defs(mod)[0]

    if entry_func not in get_defs(entry_mod)[0]:
        raise SystemExit(f"error: {entry_mod} defines no {entry_func!r}")
    seen = {f"{entry_mod}:{entry_func}"}
    queue = [f"{entry_mod}:{entry_func}"]
    unresolved = 0
    while queue:
        current = queue.pop(0)
        mod, _, qual = current.partition(":")
        funcs, module_imports = get_defs(mod)
        node = funcs.get(qual)
        if node is None:
            continue
        imports = module_imports | _import_bindings(
            _scope_imports(node.body, include_classes=False), mod, packages
        )
        cls_ctx = qual.split(".")[0] if "." in qual else None
        for call in _function_calls(node):
            target: str | None = None
            func = call.func
            if isinstance(func, ast.Name):
                local_func = f"{qual}.{func.id}"
                if local_func in funcs:
                    target = f"{mod}:{local_func}"
                elif func.id in funcs:
                    target = f"{mod}:{func.id}"
                elif func.id in imports:
                    tmod, tname = imports[func.id]
                    resolved = _resolve_callee(tmod, tname, None, modules, has_func)
                    if resolved is None:
                        unresolved += 1
                    else:
                        target = resolved
                else:
                    unresolved += 1
            elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                base, attr = func.value.id, func.attr
                if base in ("self", "cls") and cls_ctx and f"{cls_ctx}.{attr}" in funcs:
                    target = f"{mod}:{cls_ctx}.{attr}"
                elif base in imports:
                    tmod, tname = imports[base]
                    resolved = _resolve_callee(tmod, tname, attr, modules, has_func)
                    if resolved is None:
                        unresolved += 1
                    else:
                        target = resolved
                else:
                    unresolved += 1
            else:
                unresolved += 1
            if target is not None and target not in seen:
                seen.add(target)
                queue.append(target)
    return sorted(seen), unresolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="P0 module dependency gate: import rings (R1), cross-package "
        "private imports (R2), worker->commands/plugin imports (R3), "
        "top-level heavy imports (R4), and cross-module private member "
        "accesses (R2b). AST-only; dynamic imports, DI, and "
        "monkeypatching are invisible (see module docstring). Pre-existing "
        "R2/R3/R4 violations are frozen in tests/architecture_import_ratchet.json "
        "and may only shrink; R1 degrades to no-new-rings once the frozen "
        f"baseline holds >={CYCLE_DOWNGRADE_THRESHOLD} rings.",
    )
    parser.add_argument("--check", action="store_true", help="Fail on any new violation vs the ratchet.")
    parser.add_argument("--write-ratchet", action="store_true", help="Regenerate the ratchet snapshot from the current tree.")
    parser.add_argument("--reach", action="store_true", help="Print functions reachable from --entry (for P2 legacy relocation).")
    parser.add_argument("--entry", default=None, help="Reachability entry, e.g. paperforge.worker.ocr_figures:build_figure_inventory.")
    args = parser.parse_args(argv)
    if args.reach:
        if not args.entry:
            print("error: --reach requires --entry MOD:func", file=sys.stderr)
            return 2
        reached, unresolved = reach(args.entry)
        for item in reached:
            print(item)
        print(
            f"# reached {len(reached)} functions; {unresolved} call sites "
            "left unresolved (external, builtin, or dynamic -- static limit, see --help)",
            file=sys.stderr,
        )
        return 0
    if args.write_ratchet:
        snapshot = build_snapshot()
        try:
            old = json.loads(RATCHET_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            old = {}
        if isinstance(old, dict) and "private_member_access_exceptions" in old:
            snapshot["private_member_access_exceptions"] = old["private_member_access_exceptions"]
        RATCHET_PATH.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {RATCHET_PATH} ({len(snapshot['rings'])} rings)")
        return 0
    if args.check:
        ratchet = load_ratchet()
        if ratchet is None:
            print(f"error: missing {RATCHET_PATH}; run --write-ratchet first", file=sys.stderr)
            return 2
        failures = check(build_snapshot(), ratchet)
        if failures:
            for failure in failures:
                print(failure, file=sys.stderr)
            return 1
        print("module graph OK")
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
