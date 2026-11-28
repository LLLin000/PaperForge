#!/usr/bin/env python3
"""PaperForge Backend Audit Runner (PBAF v2.1).

Static (S1-S14) and optional Read-Only Dynamic (D1-D6) backend audit gates
covering Data Sovereignty, SQLite/WAL Safety, Migration FSM, Cross-OS
Resilience, Scale/Latency Budgets, Heavy Import Hygiene, N+1 SQL traps,
Polyglot Schema Parity, External API/Zotero Safety, Bounded Growth, and
Silent Exception Swallow Hygiene.

Usage:
    python scripts/backend_audit.py
    python scripts/backend_audit.py --json
    python scripts/backend_audit.py --vault <ISOLATED_VAULT> --strict

NEVER point --vault at a live user production vault; use an isolated clone.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass
class AuditFinding:
    gate: str
    pillar: str
    severity: str  # "P0" | "P1" | "P2" | "INFO"
    file: str
    line: int
    symbol: str
    message: str


@dataclass
class GateResult:
    gate_id: str
    title: str
    pillar: str
    status: str  # "PASS" | "WARN" | "FAIL"
    summary: str
    findings: list[AuditFinding] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


def _iter_backend_py_files() -> list[Path]:
    root = REPO_ROOT / "paperforge"
    out: list[Path] = []
    for dirpath_str, dirnames, filenames in os.walk(str(root), followlinks=False):
        dirnames[:] = [
            d for d in sorted(dirnames)
            if d not in ("__pycache__", "node_modules", ".git", "plugin", "skills")
        ]
        base = Path(dirpath_str)
        for fn in sorted(filenames):
            if fn.endswith(".py"):
                out.append(base / fn)
    return out


def _rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def _call_attr_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _full_attr_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _full_attr_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


# ---------------------------------------------------------------------------
# Static Gates (S1 - S9)
# ---------------------------------------------------------------------------

def gate_s1_quick_check_hot_path(files: list[Path]) -> GateResult:
    """S1: Detect PRAGMA quick_check / integrity_check in read-only hot paths."""
    hot_prefixes = (
        "paperforge/probes/",
        "paperforge/commands/status.py",
        "paperforge/commands/probe.py",
        "paperforge/commands/embed.py",
        "paperforge/embedding/status.py",
        "paperforge/embedding/substrate.py",
        "paperforge/lineage.py",
    )
    pattern = re.compile(r"PRAGMA\s+(?:quick_check|integrity_check)", re.IGNORECASE)
    findings: list[AuditFinding] = []
    maintenance_sites = 0

    for fp in files:
        rel = _rel(fp)
        txt = fp.read_text(encoding="utf-8", errors="ignore")
        for idx, line in enumerate(txt.splitlines(), 1):
            if not pattern.search(line):
                continue
            if rel.startswith(hot_prefixes):
                if rel == "paperforge/embedding/substrate.py" and "deep_check" in txt:
                    findings.append(
                        AuditFinding(
                            gate="S1",
                            pillar="P2/P5",
                            severity="INFO",
                            file=rel,
                            line=idx,
                            symbol="assess_vector_substrate",
                            message="quick_check guarded by deep_check / size threshold",
                        )
                    )
                else:
                    findings.append(
                        AuditFinding(
                            gate="S1",
                            pillar="P2/P5",
                            severity="P1",
                            file=rel,
                            line=idx,
                            symbol="read_hot_path",
                            message=f"Ungated full DB B-Tree scan in hot path: {line.strip()[:80]}",
                        )
                    )
            else:
                maintenance_sites += 1

    has_p1 = any(f.severity in ("P0", "P1") for f in findings)
    return GateResult(
        gate_id="S1_quick_check_hot_path",
        title="Hot-Path SQLite PRAGMA quick_check",
        pillar="P2/P5",
        status="WARN" if has_p1 else "PASS",
        summary=f"{sum(1 for f in findings if f.severity in ('P0', 'P1'))} ungated hot-path site(s), {maintenance_sites} maintenance/verify site(s)",
        findings=findings,
    )


def gate_s2_bare_rglob_md(files: list[Path]) -> GateResult:
    """S2: Flag bare .rglob('*.md') calls that may descend into assets/ or read fulltext.md."""
    findings: list[AuditFinding] = []
    for fp in files:
        rel = _rel(fp)
        if rel == "paperforge/core/fs_safe.py":
            continue
        src = fp.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(src, filename=rel)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "rglob" and node.args:
                    arg0 = node.args[0]
                    if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str) and ".md" in arg0.value:
                        findings.append(
                            AuditFinding(
                                gate="S2",
                                pillar="P4/P5",
                                severity="P1",
                                file=rel,
                                line=node.lineno,
                                symbol="rglob('*.md')",
                                message="Bare rglob('*.md') ignores reserved names and descends into assets/fulltext",
                            )
                        )
    return GateResult(
        gate_id="S2_bare_rglob_md",
        title="Bare .rglob('*.md') Traversal",
        pillar="P4/P5",
        status="WARN" if findings else "PASS",
        summary=f"{len(findings)} bare rglob('*.md') site(s) found",
        findings=findings,
    )


def gate_s3_platform_hardcoding(files: list[Path]) -> GateResult:
    """S3: Flag Windows-only CLI repair commands or unguarded windll references."""
    findings: list[AuditFinding] = []
    win_cmd_re = re.compile(r"mklink\s+/[Jj]|Run as Administrator", re.IGNORECASE)
    for fp in files:
        rel = _rel(fp)
        txt = fp.read_text(encoding="utf-8", errors="ignore")
        lines = txt.splitlines()
        has_nt_guard = (
            'os.name == "nt"' in txt
            or "os.name == 'nt'" in txt
            or 'os.name != "nt"' in txt
            or "os.name != 'nt'" in txt
            or 'sys.platform == "win32"' in txt
            or "sys.platform == 'win32'" in txt
            or 'sys.platform != "win32"' in txt
            or "sys.platform != 'win32'" in txt
        )
        for idx, line in enumerate(lines, 1):
            if rel.startswith("paperforge/tests"):
                continue
            if win_cmd_re.search(line):
                # Check nearby context (within 8 lines above) for an OS check
                ctx = "\n".join(lines[max(0, idx - 9) : idx])
                if 'os.name == "nt"' not in ctx and "win32" not in ctx and "os.name !=" not in ctx:
                    findings.append(
                        AuditFinding(
                            gate="S3",
                            pillar="P4",
                            severity="P2",
                            file=rel,
                            line=idx,
                            symbol="mklink_remediation",
                            message="Windows-only 'mklink' guidance emitted without OS branch",
                        )
                    )
            if "ctypes.windll" in line and not has_nt_guard:
                findings.append(
                    AuditFinding(
                        gate="S3",
                        pillar="P4",
                        severity="P0",
                        file=rel,
                        line=idx,
                        symbol="ctypes.windll",
                        message="ctypes.windll used without os.name/sys.platform guard",
                    )
                )
    has_p0 = any(f.severity == "P0" for f in findings)
    status = "FAIL" if has_p0 else ("WARN" if findings else "PASS")
    return GateResult(
        gate_id="S3_platform_hardcoding",
        title="Cross-OS Hardcoded Commands & Win32 Guards",
        pillar="P4",
        status=status,
        summary=f"{len(findings)} platform-portability finding(s)",
        findings=findings,
    )


def gate_s4_lock_and_wal_safety(files: list[Path]) -> GateResult:
    """S4: Check POSIX lock blindness on DB movability and ignored quiesce_sqlite_wal results."""
    findings: list[AuditFinding] = []
    for fp in files:
        rel = _rel(fp)
        if rel == "paperforge/core/fs_safe.py":
            continue
        src = fp.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(src, filename=rel)
        except SyntaxError:
            continue

        # 1) Detect open(db_path, "r+b") lock probe
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and "movable" in node.name:
                fn_src = ast.get_source_segment(src, node) or ""
                if "r+b" in fn_src and "BEGIN IMMEDIATE" not in fn_src:
                    findings.append(
                        AuditFinding(
                            gate="S4",
                            pillar="P4/P2",
                            severity="P0",
                            file=rel,
                            line=node.lineno,
                            symbol=node.name,
                            message="SQLite lock check uses open('r+b') which is a no-op advisory check on macOS/Linux",
                        )
                    )
            # 2) Detect discarded return value from quiesce_sqlite_wal(...)
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                if _call_attr_name(node.value.func) == "quiesce_sqlite_wal":
                    findings.append(
                        AuditFinding(
                            gate="S4",
                            pillar="P2/P3",
                            severity="P0",
                            file=rel,
                            line=node.lineno,
                            symbol="quiesce_sqlite_wal",
                            message="quiesce_sqlite_wal() return value discarded; migration/move continues even if WAL checkpoint fails",
                        )
                    )

    has_p0 = any(f.severity == "P0" for f in findings)
    return GateResult(
        gate_id="S4_lock_and_wal_safety",
        title="POSIX Lock Probes & WAL Quiesce Enforcement",
        pillar="P2/P4",
        status="FAIL" if has_p0 else "PASS",
        summary=f"{len(findings)} WAL/lock safety finding(s)",
        findings=findings,
    )


def gate_s5_heavy_import_hygiene(files: list[Path]) -> GateResult:
    """S5: Flag top-level heavy ML/PDF SDK imports in lightweight CLI/probe/config/service entrypoints."""
    heavy = {"openai", "pymupdf", "fitz", "PIL", "torch", "numpy", "chromadb", "lancedb"}
    light_prefixes = (
        "paperforge/cli.py",
        "paperforge/config.py",
        "paperforge/lineage.py",
        "paperforge/probes/",
        "paperforge/commands/status.py",
        "paperforge/commands/probe.py",
        "paperforge/commands/config.py",
        "paperforge/commands/upgrade.py",
        "paperforge/embedding/status.py",
        "paperforge/embedding/substrate.py",
        "paperforge/services/vault_upgrade.py",
        "paperforge/services/upgrade_reconcile.py",
    )
    findings: list[AuditFinding] = []
    for fp in files:
        rel = _rel(fp)
        if not rel.startswith(light_prefixes):
            continue
        src = fp.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(src, filename=rel)
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".", 1)[0]
                    if top in heavy:
                        findings.append(
                            AuditFinding(
                                gate="S5",
                                pillar="P5",
                                severity="P1",
                                file=rel,
                                line=node.lineno,
                                symbol=alias.name,
                                message=f"Top-level heavy import '{alias.name}' in fast-path module",
                            )
                        )
            elif isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".", 1)[0]
                if top in heavy:
                    findings.append(
                        AuditFinding(
                            gate="S5",
                            pillar="P5",
                            severity="P1",
                            file=rel,
                            line=node.lineno,
                            symbol=node.module,
                            message=f"Top-level heavy from-import '{node.module}' in fast-path module",
                        )
                    )
    return GateResult(
        gate_id="S5_heavy_import_hygiene",
        title="Fast-Path Heavy SDK Import Hygiene",
        pillar="P5",
        status="WARN" if findings else "PASS",
        summary=f"{len(findings)} top-level heavy SDK import(s) in fast-path modules",
        findings=findings,
    )


def gate_s6_file_action_contract() -> GateResult:
    """S6: Verify PER_FILE_ACTION_CONTRACT has zero rule conflicts."""
    try:
        from paperforge.services.migration_contract import (
            PER_FILE_ACTION_CONTRACT,
            audit_file_action_conflicts,
        )

        conflicts = audit_file_action_conflicts()
        findings = [
            AuditFinding(
                gate="S6",
                pillar="P3",
                severity="P0",
                file="paperforge/services/migration_contract.py",
                line=1,
                symbol="PER_FILE_ACTION_CONTRACT",
                message=str(c),
            )
            for c in conflicts
        ]
        return GateResult(
            gate_id="S6_file_action_contract",
            title="Per-File Action Contract Conflict Check",
            pillar="P3",
            status="FAIL" if findings else "PASS",
            summary=f"{len(PER_FILE_ACTION_CONTRACT)} contract rules audited, {len(conflicts)} conflict(s)",
            findings=findings,
        )
    except Exception as exc:
        return GateResult(
            gate_id="S6_file_action_contract",
            title="Per-File Action Contract Conflict Check",
            pillar="P3",
            status="FAIL",
            summary=f"Failed to audit contract: {exc}",
        )


def gate_s7_unchunked_threadpool_fanout(files: list[Path]) -> GateResult:
    """S7: Locate ThreadPoolExecutor.map calls without chunking (GIL/lock contention risk)."""
    findings: list[AuditFinding] = []
    for fp in files:
        rel = _rel(fp)
        if rel == "paperforge/core/fs_safe.py":
            continue
        src = fp.read_text(encoding="utf-8", errors="ignore")
        if "ThreadPoolExecutor" not in src:
            continue
        try:
            tree = ast.parse(src, filename=rel)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "map":
                    obj = _call_attr_name(node.func.value)
                    if obj in ("pool", "executor", "ex"):
                        findings.append(
                            AuditFinding(
                                gate="S7",
                                pillar="P5",
                                severity="P1",
                                file=rel,
                                line=node.lineno,
                                symbol=f"{obj}.map",
                                message="Per-item ThreadPoolExecutor.map without chunk batching risks GIL/Future lock overhead",
                            )
                        )
    return GateResult(
        gate_id="S7_unchunked_threadpool_fanout",
        title="ThreadPoolExecutor Per-Item Fan-Out",
        pillar="P5",
        status="WARN" if findings else "PASS",
        summary=f"{len(findings)} pool.map site(s) to review for batch chunking",
        findings=findings,
    )


def gate_s8_non_atomic_state_writes(files: list[Path]) -> GateResult:
    """S8: Check critical state/config/memory modules for non-atomic .write_text/.write_bytes calls."""
    critical_prefixes = (
        "paperforge/config.py",
        "paperforge/services/vault_upgrade.py",
        "paperforge/services/storage_migration.py",
        "paperforge/services/vault_engine.py",
        "paperforge/services/upgrade_reconcile.py",
        "paperforge/memory/schema.py",
        "paperforge/embedding/build_state.py",
    )
    findings: list[AuditFinding] = []
    for fp in files:
        rel = _rel(fp)
        if not rel.startswith(critical_prefixes):
            continue
        src = fp.read_text(encoding="utf-8", errors="ignore")
        lines = src.splitlines()
        try:
            tree = ast.parse(src, filename=rel)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("write_text", "write_bytes"):
                    line_txt = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                    target_name = _full_attr_name(node.func.value)
                    # Writing throwaway backups (bak / tmp / snap) is fine
                    if any(tok in target_name.lower() for tok in ("bak", "tmp", "snap", "backup")):
                        continue
                    findings.append(
                        AuditFinding(
                            gate="S8",
                            pillar="P1",
                            severity="P2",
                            file=rel,
                            line=node.lineno,
                            symbol=f"{target_name}.{node.func.attr}",
                            message=f"Direct non-atomic {node.func.attr} in critical module: {line_txt.strip()[:70]}",
                        )
                    )
    return GateResult(
        gate_id="S8_non_atomic_state_writes",
        title="Non-Atomic State Writes in Critical Modules",
        pillar="P1",
        status="WARN" if findings else "PASS",
        summary=f"{len(findings)} direct write_text/write_bytes call(s) on critical paths",
        findings=findings,
    )


def gate_s9_sql_in_loops(files: list[Path]) -> GateResult:
    """S9: AST scan for conn.execute inside for-loops in read/reconcile/probe paths."""
    target_prefixes = (
        "paperforge/lineage.py",
        "paperforge/probes/",
        "paperforge/embedding/status.py",
        "paperforge/embedding/substrate.py",
        "paperforge/services/upgrade_reconcile.py",
        "paperforge/worker/status.py",
    )
    findings: list[AuditFinding] = []

    class _LoopSQLVisitor(ast.NodeVisitor):
        def __init__(self, rel_path: str) -> None:
            self.rel_path = rel_path
            self.loop_depth = 0
            self.func_stack: list[str] = []

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.func_stack.append(node.name)
            self.generic_visit(node)
            self.func_stack.pop()

        def visit_For(self, node: ast.For) -> None:
            self.visit(node.iter)
            self.visit(node.target)
            self.loop_depth += 1
            for stmt in node.body:
                self.visit(stmt)
            self.loop_depth -= 1
            for stmt in node.orelse:
                self.visit(stmt)

        def visit_Call(self, node: ast.Call) -> None:
            if self.loop_depth > 0 and isinstance(node.func, ast.Attribute):
                if node.func.attr == "execute":
                    recv = _call_attr_name(node.func.value).lower()
                    if any(tok in recv for tok in ("conn", "con", "cur", "db", "cursor", "_vconn")):
                        fn = self.func_stack[-1] if self.func_stack else "<module>"
                        # Exclude tiny fixed-length tuple loops over the 2-3 vec/unit tables
                        is_pragma_or_small_tbl = False
                        if node.args and isinstance(node.args[0], (ast.JoinedStr, ast.Constant)):
                            s_txt = ast.unparse(node.args[0])
                            if any(tok in s_txt for tok in ("vec_fulltext", "_vvec", "_vmeta", "{tbl}", "{table}")):
                                is_pragma_or_small_tbl = True
                        if not is_pragma_or_small_tbl:
                            findings.append(
                                AuditFinding(
                                    gate="S9",
                                    pillar="P5",
                                    severity="P1",
                                    file=self.rel_path,
                                    line=node.lineno,
                                    symbol=fn,
                                    message=f"SQL execute() inside loop in {fn}() — check N+1 or batch with executemany()",
                                )
                            )
            self.generic_visit(node)

    for fp in files:
        rel = _rel(fp)
        if not rel.startswith(target_prefixes):
            continue
        src = fp.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(src, filename=rel)
        except SyntaxError:
            continue
        _LoopSQLVisitor(rel).visit(tree)

    return GateResult(
        gate_id="S9_sql_in_loops",
        title="SQL execute() Inside Loops (N+1 / Unbatched Writes)",
        pillar="P5",
        status="WARN" if findings else "PASS",
        summary=f"{len(findings)} SQL-in-loop site(s) in probe/reconcile/status modules",
        findings=findings,
    )


# ---------------------------------------------------------------------------
# Dynamic Read-Only Gates (D1 - D4) when --vault is supplied
# ---------------------------------------------------------------------------

def gate_d1_lineage_sql_budget(vault: Path) -> GateResult:
    """D1: Measure exact SQL query count inside probe_lineage(vault) without modifying files."""
    sql_count = 0
    orig_connect = sqlite3.connect

    class _CountingConnection(sqlite3.Connection):
        def execute(self, *args, **kwargs):
            nonlocal sql_count
            sql_count += 1
            return super().execute(*args, **kwargs)

    def _wrapped_connect(*args, **kwargs):
        kwargs.setdefault("factory", _CountingConnection)
        return orig_connect(*args, **kwargs)

    sqlite3.connect = _wrapped_connect  # type: ignore[assignment]
    t0 = time.perf_counter()
    try:
        from paperforge.lineage import probe_lineage

        res = probe_lineage(vault)
    finally:
        sqlite3.connect = orig_connect  # type: ignore[assignment]
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
    n_papers = len(res.get("papers") or {})
    budget = 50
    ok = sql_count <= budget
    findings = []
    if not ok:
        findings.append(
            AuditFinding(
                gate="D1",
                pillar="P5",
                severity="P1",
                file="paperforge/lineage.py",
                line=420,
                symbol="probe_lineage",
                message=f"Executed {sql_count} SQL queries (> {budget} budget) for {n_papers} papers",
            )
        )
    return GateResult(
        gate_id="D1_lineage_sql_budget",
        title="probe_lineage SQL Query Budget",
        pillar="P5",
        status="PASS" if ok else "WARN",
        summary=f"{sql_count} SQL queries for {n_papers} papers in {elapsed_ms} ms (budget <= {budget})",
        findings=findings,
        metrics={"sql_count": sql_count, "papers": n_papers, "elapsed_ms": elapsed_ms},
    )


def gate_d2_import_hygiene_runtime(vault: Path) -> GateResult:
    """D2: Verify status and embed status never import heavy SDKs in a clean child process."""
    banned = ("openai", "fitz", "pymupdf", "torch", "PIL")
    checks = [
        ("status", ["status", "--json"]),
        ("embed status", ["embed", "status", "--json"]),
    ]
    findings: list[AuditFinding] = []
    loaded_map: dict[str, list[str]] = {}
    for label, cli_args in checks:
        code = (
            "import json, sys; from paperforge.cli import main\n"
            f"sys.argv = ['paperforge', '--vault', {str(vault)!r}] + {cli_args!r}\n"
            "import io, contextlib\n"
            "with contextlib.redirect_stdout(io.StringIO()):\n"
            "    try:\n        main()\n    except SystemExit:\n        pass\n"
            f"hits = [m for m in {list(banned)!r} if m in sys.modules]\n"
            "print('AUDIT_IMPORTS:' + json.dumps(hits))\n"
        )
        cp = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        hits: list[str] = []
        for line in cp.stdout.splitlines():
            if line.startswith("AUDIT_IMPORTS:"):
                hits = json.loads(line.split("AUDIT_IMPORTS:", 1)[1])
        loaded_map[label] = hits
        for mod in hits:
            findings.append(
                AuditFinding(
                    gate="D2",
                    pillar="P5",
                    severity="P1",
                    file="paperforge/cli.py",
                    line=1,
                    symbol=label,
                    message=f"'{label}' imported heavy SDK '{mod}' at runtime",
                )
            )
    return GateResult(
        gate_id="D2_import_hygiene_runtime",
        title="Runtime Heavy SDK Import Isolation",
        pillar="P5",
        status="WARN" if findings else "PASS",
        summary=f"status={loaded_map.get('status')}, embed_status={loaded_map.get('embed status')}",
        findings=findings,
        metrics=loaded_map,
    )


def gate_d3_latency_budgets(vault: Path) -> GateResult:
    """D3: Measure read-only CLI command wall-clock latencies against PBAF budgets."""
    budgets_ms = {
        "config_validate": (["config", "validate", "--json"], 1000.0),
        "embed_status": (["embed", "status", "--json"], 1200.0),
        "status": (["status", "--json"], 2000.0),
        "doctor": (["doctor", "--json"], 4500.0),
        "probe_all": (["probe", "all", "--json"], 3500.0),
        "upgrade_plan": (["upgrade", "--plan", "--json"], 8000.0),
    }
    timings: dict[str, float] = {}
    findings: list[AuditFinding] = []
    for name, (argv, max_ms) in budgets_ms.items():
        t0 = time.perf_counter()
        cp = subprocess.run(
            [sys.executable, "-m", "paperforge", "--vault", str(vault), *argv],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
        )
        dt = round((time.perf_counter() - t0) * 1000.0, 1)
        timings[name] = dt
        if dt > max_ms:
            findings.append(
                AuditFinding(
                    gate="D3",
                    pillar="P5",
                    severity="P1",
                    file="paperforge/cli.py",
                    line=1,
                    symbol=name,
                    message=f"{name} took {dt} ms > {max_ms} ms budget (rc={cp.returncode})",
                )
            )
    return GateResult(
        gate_id="D3_latency_budgets",
        title="Read-Only CLI Latency Budgets",
        pillar="P5",
        status="WARN" if findings else "PASS",
        summary=", ".join(f"{k}={v}ms" for k, v in timings.items()),
        findings=findings,
        metrics=timings,
    )


def gate_d4_vault_integrity_readonly(vault: Path) -> GateResult:
    """D4: Read-only verification of manifest, schema tables, and zombie states."""
    findings: list[AuditFinding] = []
    manifest_p = vault / ".paperforge" / "vault-manifest.json"
    db_p = vault / ".paperforge" / "indexes" / "paperforge.db"
    if not db_p.is_file():
        db_p = vault / "System" / "PaperForge" / "indexes" / "paperforge.db"

    metrics: dict[str, Any] = {"manifest_present": manifest_p.is_file(), "db_present": db_p.is_file()}
    if not manifest_p.is_file():
        findings.append(
            AuditFinding(
                gate="D4",
                pillar="P3",
                severity="P1",
                file=".paperforge/vault-manifest.json",
                line=1,
                symbol="vault_manifest",
                message="vault-manifest.json missing (vault not yet upgraded to v2 layout)",
            )
        )
    if db_p.is_file():
        con = sqlite3.connect(f"file:{db_p.as_posix()}?mode=ro", uri=True)
        try:
            tbls = {str(r[0]) for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            for t in ("papers", "workspace_registry", "ocr_catalog", "reading_log", "vec_body_meta"):
                metrics[t] = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] if t in tbls else -1
            if "papers" in tbls:
                zombies = con.execute(
                    "SELECT COUNT(*) FROM papers WHERE lower(trim(coalesce(ocr_status, ''))) = 'running'"
                ).fetchone()[0]
                metrics["zombie_running"] = zombies
                if zombies > 0:
                    findings.append(
                        AuditFinding(
                            gate="D4",
                            pillar="P6",
                            severity="P1",
                            file="paperforge.db",
                            line=1,
                            symbol="papers.ocr_status",
                            message=f"{zombies} zombie ocr_status='running' rows detected",
                        )
                    )
        finally:
            con.close()
    return GateResult(
        gate_id="D4_vault_integrity_readonly",
        title="Target Vault Read-Only Integrity Check",
        pillar="P1/P2/P6",
        status="WARN" if findings else "PASS",
        summary=f"manifest={metrics['manifest_present']}, papers={metrics.get('papers')}, zombies={metrics.get('zombie_running')}",
        findings=findings,
        metrics=metrics,
    )


def gate_s10_silent_exception_swallow(files: list[Path]) -> GateResult:
    """S10: Flag bare 'except Exception: pass' outside cleanup/close paths in critical modules."""
    critical_prefixes = (
        "paperforge/services/storage_migration.py",
        "paperforge/services/vault_upgrade.py",
        "paperforge/services/upgrade_reconcile.py",
        "paperforge/memory/db.py",
        "paperforge/memory/builder.py",
        "paperforge/memory/schema.py",
    )
    findings: list[AuditFinding] = []
    for fp in files:
        rel = _rel(fp)
        if not rel.startswith(critical_prefixes):
            continue
        src = fp.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(src, filename=rel)
        except SyntaxError:
            continue
        parent_map: dict[ast.AST, ast.AST] = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parent_map[child] = parent
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                # Allow benign cleanup inside Try.finalbody (closing handles/temp files)
                try_node = parent_map.get(node)
                in_final = False
                cur = try_node
                while cur is not None:
                    p = parent_map.get(cur)
                    if isinstance(p, ast.Try) and cur in p.finalbody:
                        in_final = True
                        break
                    cur = p
                if in_final or node.type is not None and _call_attr_name(node.type) in ("OSError", "ValueError"):
                    continue
                try_txt = ast.unparse(try_node.body[0]) if isinstance(try_node, ast.Try) and try_node.body else ""
                if any(tok in try_txt for tok in (".close()", ".unlink(", ".rmdir(")):
                    continue
                findings.append(
                    AuditFinding(
                        gate="S10",
                        pillar="P12",
                        severity="P2",
                        file=rel,
                        line=node.lineno,
                        symbol="except: pass",
                        message=f"Silent exception swallow in critical state module near: {try_txt[:60]}",
                    )
                )
    return GateResult(
        gate_id="S10_silent_exception_swallow",
        title="Silent Exception Swallow in Critical Modules",
        pillar="P12",
        status="WARN" if findings else "PASS",
        summary=f"{len(findings)} silent broad-exception pass handler(s) in critical modules",
        findings=findings,
    )


def gate_s11_sqlite_connection_hygiene(files: list[Path]) -> GateResult:
    """S11: Verify every sqlite3.connect() in storage/memory/lineage has matching close() or with-block."""
    critical_prefixes = (
        "paperforge/services/",
        "paperforge/memory/",
        "paperforge/embedding/",
        "paperforge/lineage.py",
    )
    findings: list[AuditFinding] = []
    for fp in files:
        rel = _rel(fp)
        if not rel.startswith(critical_prefixes):
            continue
        src = fp.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(src, filename=rel)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            fn_src = ast.get_source_segment(src, node) or ""
            if "sqlite3.connect(" not in fn_src:
                continue
            if "return orig_connect" in fn_src or "return sqlite3.connect" in fn_src:
                continue
            has_with_or_close = (
                ".close()" in fn_src
                or "with sqlite3.connect(" in fn_src
                or "closing(" in fn_src
                or "with open_live_reader" in fn_src
                or "return conn" in fn_src
                or "return con" in fn_src
            )
            if not has_with_or_close:
                findings.append(
                    AuditFinding(
                        gate="S11",
                        pillar="P11/P2",
                        severity="P1",
                        file=rel,
                        line=node.lineno,
                        symbol=node.name,
                        message="Function opens sqlite3.connect() without visible .close() or context manager",
                    )
                )
    return GateResult(
        gate_id="S11_sqlite_connection_hygiene",
        title="SQLite Connection Close & FD Hygiene",
        pillar="P11/P2",
        status="WARN" if findings else "PASS",
        summary=f"{len(findings)} potential SQLite connection leak site(s)",
        findings=findings,
    )


def gate_s12_polyglot_schema_parity() -> GateResult:
    """S12 (P9): Dynamically verify Rust daemon SQL tables & manifest files match Python authorities."""
    rust_dir = REPO_ROOT / "crates" / "paperforge-daemon" / "src"
    py_schema = REPO_ROOT / "paperforge" / "memory" / "schema.py"
    py_engine = REPO_ROOT / "paperforge" / "services" / "vault_engine.py"
    py_asset = REPO_ROOT / "paperforge" / "worker" / "asset_index.py"
    py_cfg = REPO_ROOT / "paperforge" / "config.py"
    findings: list[AuditFinding] = []
    if not rust_dir.is_dir() or not py_schema.is_file():
        return GateResult(
            gate_id="S12_polyglot_schema_parity",
            title="Polyglot Schema & Manifest Parity",
            pillar="P9",
            status="PASS",
            summary="Rust daemon directory absent; skipped",
        )
    rust_text = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for p in rust_dir.glob("*.rs")
        if p.name != "main.rs"
    )
    py_schema_text = py_schema.read_text(encoding="utf-8", errors="ignore")
    py_tables = {
        m.lower()
        for m in re.findall(
            r"CREATE\s+(?:VIRTUAL\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-z_][a-z0-9_]*)",
            py_schema_text,
            re.IGNORECASE,
        )
        if m.lower() not in {"if", "sqlite_master", "sqlite_sequence"}
    }
    py_authority_text = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for p in (py_schema, py_engine, py_asset, py_cfg)
        if p.is_file()
    )

    # Extract SQL string literals from Rust daemon and collect PaperForge table references
    zotero_or_internal = frozenset({
        "sqlite_master",
        "sqlite_sequence",
        "items",
        "itemtypes",
        "deleteditems",
        "collections",
        "collectionitems",
        "itemdata",
        "itemdatavalues",
        "fields",
        "itemattachments",
        "itemcreators",
        "creators",
        "itemtags",
        "tags",
    })
    rust_sql_tables: set[str] = set()
    sql_tbl_rx = re.compile(
        r"\bSELECT\b.*?\bFROM\s+([a-z_][a-z0-9_]*)"
        r"|\bINSERT\s+(?:OR\s+[a-z_]+\s+)?INTO\s+([a-z_][a-z0-9_]*)"
        r"|\bDELETE\s+FROM\s+([a-z_][a-z0-9_]*)"
        r"|\bUPDATE\s+([a-z_][a-z0-9_]*)\s+SET\b"
        r"|\bJOIN\s+([a-z_][a-z0-9_]*)\s+(?:ON|USING|[a-z]{1,3}\b)",
        re.IGNORECASE | re.DOTALL,
    )
    for str_lit in re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', rust_text):
        for groups in sql_tbl_rx.findall(str_lit):
            for tbl in groups:
                if tbl:
                    tbl_low = tbl.lower()
                    if tbl_low not in zotero_or_internal:
                        rust_sql_tables.add(tbl_low)

    checked = 0
    for tbl in sorted(rust_sql_tables):
        checked += 1
        if tbl not in py_tables:
            findings.append(
                AuditFinding(
                    gate="S12",
                    pillar="P9",
                    severity="P0",
                    file="crates/paperforge-daemon/src",
                    line=1,
                    symbol=tbl,
                    message=f"Rust daemon queries SQLite table '{tbl}' missing from Python schema.py",
                )
            )

    file_contracts = ("vault-manifest.json", "formal-library.json", "paperforge.db")
    for tok in file_contracts:
        if tok in rust_text:
            checked += 1
            if tok not in py_authority_text:
                findings.append(
                    AuditFinding(
                        gate="S12",
                        pillar="P9",
                        severity="P0",
                        file="crates/paperforge-daemon/src",
                        line=1,
                        symbol=tok,
                        message=f"Rust daemon depends on '{tok}' missing from Python authorities",
                    )
                )

    return GateResult(
        gate_id="S12_polyglot_schema_parity",
        title="Rust <-> Python Schema & Manifest Parity",
        pillar="P9",
        status="FAIL" if findings else "PASS",
        summary=f"{checked - len(findings)}/{checked} dynamic Rust/Python contracts aligned",
        findings=findings,
    )


def gate_s13_external_api_and_zotero_safety(files: list[Path]) -> GateResult:
    """S13 (P10): Enforce explicit timeouts on all HTTP requests and read-only snapshot access on Zotero DBs."""
    findings: list[AuditFinding] = []
    http_methods = frozenset({"get", "post", "put", "delete", "head", "patch", "request"})

    for fp in files:
        rel = _rel(fp)
        src = fp.read_text(encoding="utf-8", errors="ignore")
        if "requests." in src:
            try:
                tree = ast.parse(src, filename=rel)
            except SyntaxError:
                tree = None
            if tree is not None:
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                        if (
                            node.func.attr in http_methods
                            and isinstance(node.func.value, ast.Name)
                            and node.func.value.id == "requests"
                        ):
                            kw_names = {kw.arg for kw in node.keywords}
                            if "timeout" not in kw_names:
                                findings.append(
                                    AuditFinding(
                                        gate="S13",
                                        pillar="P10",
                                        severity="P0",
                                        file=rel,
                                        line=node.lineno,
                                        symbol=f"requests.{node.func.attr}",
                                        message="Outbound HTTP request missing explicit timeout= bound",
                                    )
                                )
        if "zotero.sqlite" in src and "sqlite3.connect(" in src:
            for idx, line in enumerate(src.splitlines(), start=1):
                if "sqlite3.connect(" not in line:
                    continue
                if "zotero" in line.lower() and "mode=ro" not in line and "snap" not in line.lower():
                    findings.append(
                        AuditFinding(
                            gate="S13",
                            pillar="P10",
                            severity="P0",
                            file=rel,
                            line=idx,
                            symbol="sqlite3.connect",
                            message="Direct non-readonly/non-snapshot sqlite3.connect on Zotero source DB",
                        )
                    )

    return GateResult(
        gate_id="S13_external_api_and_zotero_safety",
        title="External HTTP Timeouts & Zotero Read-Only Snapshot Safety",
        pillar="P10",
        status="FAIL" if findings else "PASS",
        summary=f"{len(findings)} HTTP-timeout or Zotero-lock hazard(s) found",
        findings=findings,
    )


def gate_s14_unbounded_storage_and_retention() -> GateResult:
    """S14 (P11): Verify bounded retention primitives exist for backups, trash, and manifest history."""
    trash_p = REPO_ROOT / "paperforge" / "worker" / "trash.py"
    engine_p = REPO_ROOT / "paperforge" / "services" / "vault_engine.py"
    findings: list[AuditFinding] = []

    if trash_p.is_file():
        ttxt = trash_p.read_text(encoding="utf-8", errors="ignore")
        if "def purge_trash" not in ttxt or "older_than_days" not in ttxt:
            findings.append(
                AuditFinding(
                    gate="S14",
                    pillar="P11",
                    severity="P1",
                    file="paperforge/worker/trash.py",
                    line=1,
                    symbol="purge_trash",
                    message="trash.py missing age-bounded purge_trash(older_than_days=...)",
                )
            )
    if engine_p.is_file():
        etxt = engine_p.read_text(encoding="utf-8", errors="ignore")
        if "def prune_old_backups" not in etxt:
            findings.append(
                AuditFinding(
                    gate="S14",
                    pillar="P11",
                    severity="P1",
                    file="paperforge/services/vault_engine.py",
                    line=1,
                    symbol="prune_old_backups",
                    message="vault_engine.py missing bounded prune_old_backups() retention helper",
                )
            )
        if "[-50:]" not in etxt and "history[-" not in etxt:
            findings.append(
                AuditFinding(
                    gate="S14",
                    pillar="P11",
                    severity="P1",
                    file="paperforge/services/vault_engine.py",
                    line=1,
                    symbol="migration_history",
                    message="vault-manifest migration_history lacks bounded slice cap",
                )
            )

    return GateResult(
        gate_id="S14_unbounded_storage_and_retention",
        title="Bounded Backup, Trash & History Retention Controls",
        pillar="P11",
        status="FAIL" if any(f.severity == "P0" for f in findings) else ("WARN" if findings else "PASS"),
        summary=f"{len(findings)} unbounded storage retention gap(s)",
        findings=findings,
    )


def _dir_size_and_subdirs(root: Path) -> tuple[int, int]:
    if not root.is_dir() or root.is_symlink():
        return 0, 0
    total_bytes = 0
    top_subdirs = 0
    try:
        for entry in root.iterdir():
            if entry.is_dir() and not entry.is_symlink():
                top_subdirs += 1
        for dirpath_str, _, filenames in os.walk(str(root), followlinks=False):
            dp = Path(dirpath_str)
            if dp.is_symlink():
                continue
            for fn in filenames:
                try:
                    total_bytes += (dp / fn).stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total_bytes, top_subdirs


def gate_d6_unbounded_growth_and_wal_tail(vault: Path) -> GateResult:
    """D6 (P11/P2): Read-only check of backups/trash footprint and SQLite WAL sidecar size."""
    pf_dir = vault / ".paperforge"
    if not pf_dir.is_dir():
        pf_dir = vault / "System" / "PaperForge"
    backups_bytes, backups_dirs = _dir_size_and_subdirs(pf_dir / "backups")
    trash_bytes, trash_dirs = _dir_size_and_subdirs(pf_dir / "trash")
    db_p = pf_dir / "indexes" / "paperforge.db"
    wal_p = db_p.parent / f"{db_p.name}-wal"
    wal_bytes = wal_p.stat().st_size if wal_p.is_file() else 0

    journal_mode = "unknown"
    schema_ver = "unknown"
    if db_p.is_file():
        con = sqlite3.connect(f"file:{db_p.as_posix()}?mode=ro", uri=True)
        try:
            jm = con.execute("PRAGMA journal_mode").fetchone()
            journal_mode = str(jm[0]) if jm else "unknown"
            row = con.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
            schema_ver = str(row[0]) if row else "unknown"
        except sqlite3.Error:
            pass
        finally:
            con.close()

    findings: list[AuditFinding] = []
    two_gib = 2 * 1024**3
    if backups_bytes > two_gib or backups_dirs > 500:
        findings.append(
            AuditFinding(
                "D6",
                "P11",
                "P2",
                ".paperforge/backups",
                1,
                "backups_growth",
                f"Backups footprint large: {backups_bytes / (1024**2):.1f} MB across {backups_dirs} dir(s)",
            )
        )
    if trash_bytes > two_gib or trash_dirs > 500:
        findings.append(
            AuditFinding(
                "D6",
                "P11",
                "P2",
                ".paperforge/trash",
                1,
                "trash_growth",
                f"Trash footprint large: {trash_bytes / (1024**2):.1f} MB across {trash_dirs} dir(s)",
            )
        )
    if wal_bytes > 50 * 1024**2:
        findings.append(
            AuditFinding(
                "D6",
                "P2/P11",
                "P1",
                "paperforge.db-wal",
                1,
                "wal_tail",
                f"Large uncheckpointed WAL sidecar: {wal_bytes / (1024**2):.1f} MB",
            )
        )

    metrics = {
        "backups_mb": round(backups_bytes / (1024**2), 2),
        "backups_dirs": backups_dirs,
        "trash_mb": round(trash_bytes / (1024**2), 2),
        "trash_dirs": trash_dirs,
        "wal_mb": round(wal_bytes / (1024**2), 2),
        "journal_mode": journal_mode,
        "schema_version": schema_ver,
    }
    return GateResult(
        gate_id="D6_unbounded_growth_and_wal_tail",
        title="Backups/Trash Growth & SQLite WAL Tail Footprint",
        pillar="P11/P2",
        status="WARN" if findings else "PASS",
        summary=(
            f"backups={metrics['backups_mb']}MB({backups_dirs}), "
            f"trash={metrics['trash_mb']}MB({trash_dirs}), "
            f"wal={metrics['wal_mb']}MB, jm={journal_mode}, v={schema_ver}"
        ),
        findings=findings,
        metrics=metrics,
    )


def gate_d5_cross_carrier_coherence(vault: Path) -> GateResult:
    """D5: Read-only cross-check across formal-library.json, SQLite tables, workspaces, and FTS5."""
    findings: list[AuditFinding] = []
    idx_p = vault / ".paperforge" / "indexes" / "formal-library.json"
    db_p = vault / ".paperforge" / "indexes" / "paperforge.db"
    if not idx_p.is_file():
        idx_p = vault / "System" / "PaperForge" / "indexes" / "formal-library.json"
    if not db_p.is_file():
        db_p = vault / "System" / "PaperForge" / "indexes" / "paperforge.db"

    metrics: dict[str, Any] = {}
    if idx_p.is_file():
        try:
            raw = json.loads(idx_p.read_text(encoding="utf-8"))
            items = raw.get("items", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
            metrics["index_items"] = len(items)
        except Exception as exc:
            findings.append(
                AuditFinding("D5", "P11", "P1", str(idx_p.name), 1, "formal-library.json", f"Unreadable index: {exc}")
            )
    if db_p.is_file():
        con = sqlite3.connect(f"file:{db_p.as_posix()}?mode=ro", uri=True)
        try:
            tbls = {str(r[0]) for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            for t in ("papers", "workspace_registry", "body_units", "body_units_fts_docsize", "paper_fts_docsize"):
                if t in tbls:
                    metrics[t] = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            if "body_units" in tbls:
                metrics["body_units_indexable"] = con.execute(
                    "SELECT COUNT(*) FROM body_units WHERE indexable = 1"
                ).fetchone()[0]
                metrics["body_units_excluded"] = con.execute(
                    "SELECT COUNT(*) FROM body_units WHERE indexable = 0"
                ).fetchone()[0]
            if "papers" in metrics and "index_items" in metrics and metrics["papers"] != metrics["index_items"]:
                findings.append(
                    AuditFinding(
                        "D5",
                        "P11",
                        "P1",
                        "paperforge.db",
                        1,
                        "papers vs index",
                        f"Carrier mismatch: formal-library={metrics['index_items']} vs papers={metrics['papers']}",
                    )
                )
            if "workspace_registry" in metrics and "papers" in metrics and metrics["workspace_registry"] != metrics["papers"]:
                findings.append(
                    AuditFinding(
                        "D5",
                        "P11",
                        "P1",
                        "paperforge.db",
                        1,
                        "workspace_registry vs papers",
                        f"Carrier mismatch: papers={metrics['papers']} vs workspace_registry={metrics['workspace_registry']}",
                    )
                )
            if "paper_fts_docsize" in metrics and "papers" in metrics and metrics["paper_fts_docsize"] != metrics["papers"]:
                findings.append(
                    AuditFinding(
                        "D5",
                        "P2/P11",
                        "P0",
                        "paperforge.db",
                        1,
                        "paper_fts_docsize",
                        f"FTS5 drift: papers={metrics['papers']} vs paper_fts_docsize={metrics['paper_fts_docsize']}",
                    )
                )
            if (
                "body_units_indexable" in metrics
                and "body_units_fts_docsize" in metrics
                and metrics["body_units_indexable"] != metrics["body_units_fts_docsize"]
            ):
                findings.append(
                    AuditFinding(
                        "D5",
                        "P2/P11",
                        "P0",
                        "paperforge.db",
                        1,
                        "body_units_fts_docsize",
                        (
                            f"FTS5 drift: body_units(indexable=1)={metrics['body_units_indexable']} "
                            f"vs body_units_fts_docsize={metrics['body_units_fts_docsize']}"
                        ),
                    )
                )
            if "body_units_fts_docsize" in tbls and "body_units" in tbls:
                orphan_cnt = con.execute(
                    """SELECT COUNT(*) FROM body_units_fts_docsize d
                       LEFT JOIN body_units b ON b.rowid = d.id
                       WHERE b.rowid IS NULL OR b.indexable != 1"""
                ).fetchone()[0]
                metrics["body_units_fts_orphans"] = orphan_cnt
                if orphan_cnt > 0:
                    findings.append(
                        AuditFinding(
                            "D5",
                            "P2/P11",
                            "P0",
                            "paperforge.db",
                            1,
                            "body_units_fts_orphans",
                            f"FTS5 membership drift: {orphan_cnt} indexed docsize row(s) missing or indexable!=1",
                        )
                    )
            if metrics.get("body_units_indexable", 0) > 0 and "body_units_fts" in tbls:
                head_rows = con.execute(
                    "SELECT rowid, unit_text FROM body_units WHERE indexable = 1 ORDER BY rowid ASC LIMIT 8"
                ).fetchall()
                tail_rows = con.execute(
                    "SELECT rowid, unit_text FROM body_units WHERE indexable = 1 ORDER BY rowid DESC LIMIT 8"
                ).fetchall()
                sampled: dict[int, str] = {}
                for sr in (*head_rows, *tail_rows):
                    rid = int(sr[0])
                    if rid not in sampled:
                        sampled[rid] = str(sr[1] or "")
                content_mismatches = 0
                probed = 0
                for rid, text in sampled.items():
                    probe_tok = None
                    for m in re.finditer(r"[A-Za-z][A-Za-z0-9]{4,}", text):
                        tok = m.group(0)
                        if tok.upper() not in {"AND", "OR", "NOT", "NEAR"}:
                            probe_tok = tok
                            break
                    if not probe_tok:
                        continue
                    probed += 1
                    hit = con.execute(
                        "SELECT 1 FROM body_units_fts WHERE rowid = ? AND body_units_fts MATCH ? LIMIT 1",
                        (rid, f'"{probe_tok}"'),
                    ).fetchone()
                    if hit is None:
                        content_mismatches += 1
                metrics["body_units_fts_content_probed"] = probed
                metrics["body_units_fts_content_mismatches"] = content_mismatches
                metrics["body_units_fts_match_probe"] = 1 if (probed > 0 and content_mismatches == 0) else 0
                if content_mismatches > 0:
                    findings.append(
                        AuditFinding(
                            "D5",
                            "P2/P11",
                            "P0",
                            "paperforge.db",
                            1,
                            "body_units_fts content",
                            f"FTS5 content drift: {content_mismatches}/{probed} sampled indexable row(s) failed rowid-bound MATCH",
                        )
                    )
        finally:
            con.close()
    if not metrics and not findings:
        findings.append(
            AuditFinding(
                "D5",
                "P11",
                "P1",
                str(vault),
                1,
                "no carriers",
                "No index/DB carriers found in target vault — D5 check not applicable",
            )
        )
    has_p0 = any(f.severity == "P0" for f in findings)
    return GateResult(
        gate_id="D5_cross_carrier_coherence",
        title="5-Carrier Coherence Parity (Index/DB/Registry/FTS)",
        pillar="P11/P2",
        status="FAIL" if has_p0 else ("WARN" if findings else "PASS"),
        summary=", ".join(f"{k}={v}" for k, v in metrics.items()) or "no carriers found",
        findings=findings,
        metrics=metrics,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PaperForge Backend Audit Runner (PBAF v2.0)")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument("--vault", type=Path, default=None, help="Optional isolated clone vault for read-only D1-D5 gates")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on any WARN (P1/P2) in addition to FAIL (P0)")
    args = parser.parse_args(argv)

    py_files = _iter_backend_py_files()
    gates: list[GateResult] = [
        gate_s1_quick_check_hot_path(py_files),
        gate_s2_bare_rglob_md(py_files),
        gate_s3_platform_hardcoding(py_files),
        gate_s4_lock_and_wal_safety(py_files),
        gate_s5_heavy_import_hygiene(py_files),
        gate_s6_file_action_contract(),
        gate_s7_unchunked_threadpool_fanout(py_files),
        gate_s8_non_atomic_state_writes(py_files),
        gate_s9_sql_in_loops(py_files),
        gate_s10_silent_exception_swallow(py_files),
        gate_s11_sqlite_connection_hygiene(py_files),
        gate_s12_polyglot_schema_parity(),
        gate_s13_external_api_and_zotero_safety(py_files),
        gate_s14_unbounded_storage_and_retention(),
    ]

    if args.vault is not None:
        vault = args.vault.expanduser().resolve()
        gates.extend([
            gate_d1_lineage_sql_budget(vault),
            gate_d2_import_hygiene_runtime(vault),
            gate_d3_latency_budgets(vault),
            gate_d4_vault_integrity_readonly(vault),
            gate_d5_cross_carrier_coherence(vault),
            gate_d6_unbounded_growth_and_wal_tail(vault),
        ])

    fails = sum(1 for g in gates if g.status == "FAIL")
    warns = sum(1 for g in gates if g.status == "WARN")

    if args.json:
        print(
            json.dumps(
                {
                    "schema": "paperforge.backend-audit/2.1",
                    "files_scanned": len(py_files),
                    "summary": {"total_gates": len(gates), "fail": fails, "warn": warns},
                    "gates": [asdict(g) for g in gates],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"PaperForge Backend Audit (PBAF v2.1) — scanned {len(py_files)} Python file(s)\n")
        for g in gates:
            print(f"[{g.status:4s}] {g.gate_id:34s} ({g.pillar:5s}) — {g.summary}")
            for f in g.findings[:8]:
                if f.severity == "INFO":
                    continue
                print(f"       {f.severity} {f.file}:{f.line} [{f.symbol}] {f.message}")
            non_info = [f for f in g.findings if f.severity != "INFO"]
            if len(non_info) > 8:
                print(f"       ... and {len(non_info) - 8} more finding(s)")
        print(f"\nSummary: {len(gates)} gates -> {fails} FAIL, {warns} WARN")

    if fails > 0 or (args.strict and warns > 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
