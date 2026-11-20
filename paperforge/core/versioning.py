"""Four-dimensional release version normalization, compatibility & depsLockHash."""

from __future__ import annotations

import email.parser
import hashlib
import importlib.metadata
import platform
import re
import sys
from pathlib import Path

import tomllib

#: Earliest Python core version the current plugin generation can drive without
#: forcing a backend reinstall on UI-only plugin patch bumps.
MIN_ENGINE_VERSION = "2.0.0"

#: Earliest Obsidian plugin version compatible with this Python core.
MIN_COMPATIBLE_PLUGIN_VERSION = "2.0.0"

_PRERELEASE_RE = re.compile(
    r"^(\d+(?:\.\d+)*)[-.]?(alpha|beta|rc|a|b)\.?(\d+)(?:\.post(\d+))?$",
    re.IGNORECASE,
)
_FINAL_POST_RE = re.compile(r"^(\d+(?:\.\d+)*)(?:\.post(\d+))?$", re.IGNORECASE)
_STAGE_ORDER = {"a": -3, "b": -2, "rc": -1, "": 0}


def normalize_release_version(version: str) -> str:
    """Normalize SemVer pre-release spellings (e.g. ``2.0.0-rc.6``) to PEP 440 (``2.0.0rc6``)."""
    cleaned = (version or "").strip().lstrip("vV")
    m = _PRERELEASE_RE.fullmatch(cleaned)
    if m:
        raw_stage = m.group(2).lower()
        phase = {"alpha": "a", "a": "a", "beta": "b", "b": "b", "rc": "rc"}[raw_stage]
        post = f".post{int(m.group(4))}" if m.group(4) is not None else ""
        return f"{m.group(1)}{phase}{int(m.group(3))}{post}"
    m2 = _FINAL_POST_RE.fullmatch(cleaned)
    if m2 and m2.group(2) is not None:
        return f"{m2.group(1)}.post{int(m2.group(2))}"
    return cleaned


def parse_release_tuple(version: str) -> tuple[int, int, int, int, int, int]:
    """Convert SemVer or PEP 440 release string into a comparable 6-int tuple.

    Ordering guarantees ``2.0.0a1 < 2.0.0b1 < 2.0.0rc6 < 2.0.0 < 2.0.0.post1 < 2.1.0``.
    Raises ``ValueError`` if *version* cannot be parsed as a numeric release.
    """
    norm = normalize_release_version(version)
    if not norm:
        raise ValueError("Empty version string")

    m = _PRERELEASE_RE.fullmatch(norm)
    if m:
        parts = [int(p) for p in m.group(1).split(".")]
        stage = _STAGE_ORDER[m.group(2).lower()]
        stage_num = int(m.group(3))
        post_num = int(m.group(4)) if m.group(4) is not None else 0
    else:
        m2 = _FINAL_POST_RE.fullmatch(norm)
        if not m2:
            raise ValueError(f"Unrecognized version format: {version!r}")
        parts = [int(p) for p in m2.group(1).split(".")]
        stage = _STAGE_ORDER[""]
        stage_num = 0
        post_num = int(m2.group(2)) if m2.group(2) is not None else 0

    while len(parts) < 3:
        parts.append(0)
    return (parts[0], parts[1], parts[2], stage, stage_num, post_num)


def is_version_compatible(
    *,
    core_version: str,
    expected_version: str | None = None,
    min_engine_version: str | None = None,
    plugin_version: str | None = None,
    min_plugin_version: str | None = None,
) -> tuple[bool, str]:
    """Evaluate plugin/core compatibility under decoupled or strict 1:1 mode.

    - When ``min_engine_version`` is provided (decoupled v2.1 contract), checks
      ``core_version >= min_engine_version`` and (when both plugin & min_plugin
      versions are provided) ``plugin_version >= min_plugin_version``.
    - When ``min_engine_version`` is omitted (legacy callers / exact check),
      checks ``normalize_release_version(core_version) == normalize_release_version(expected_version)``.
    """
    if not (core_version or "").strip():
        return False, "empty_version"

    if min_engine_version and min_engine_version.strip():
        try:
            core_t = parse_release_tuple(core_version)
            min_eng_t = parse_release_tuple(min_engine_version)
        except ValueError:
            if normalize_release_version(core_version) != normalize_release_version(min_engine_version):
                return False, "core_below_min_engine"
        else:
            if core_t < min_eng_t:
                return False, "core_below_min_engine"

        effective_plugin = plugin_version or expected_version
        if effective_plugin and min_plugin_version:
            try:
                if parse_release_tuple(effective_plugin) < parse_release_tuple(min_plugin_version):
                    return False, "plugin_below_min_plugin"
            except ValueError:
                pass
        return True, "ok"

    if (
        expected_version
        and expected_version.strip()
        and normalize_release_version(core_version) != normalize_release_version(expected_version)
    ):
        return False, "exact_version_mismatch"
    return True, "ok"


def _normalize_req_spec(spec: str) -> str:
    """Normalize a PEP 508 dependency specifier for deterministic hashing."""
    base = spec.split(";", 1)[0].strip()
    return re.sub(r"\s+", "", base).lower()


def compute_deps_lock_hash(pyproject_path: Path | None = None) -> str:
    """Compute canonical 16-hex SHA-256 fingerprint of core + vector dependencies.

    Reads ``pyproject.toml`` in a source checkout and falls back to installed
    distribution metadata (``importlib.metadata.requires('paperforge')``) so
    both wheel-installed runtimes and source checkouts produce identical hashes.
    """
    specs: set[str] = set()
    candidate = pyproject_path or (Path(__file__).resolve().parents[2] / "pyproject.toml")
    if candidate.is_file():
        try:
            data = tomllib.loads(candidate.read_text(encoding="utf-8"))
            project = data.get("project") or {}
            for req in project.get("dependencies") or []:
                norm = _normalize_req_spec(str(req))
                if norm:
                    specs.add(norm)
            opt = project.get("optional-dependencies") or {}
            for req in opt.get("vector") or []:
                norm = _normalize_req_spec(str(req))
                if norm:
                    specs.add(norm)
        except (OSError, ValueError):
            specs.clear()

    if not specs:
        try:
            reqs = importlib.metadata.requires("paperforge") or []
        except importlib.metadata.PackageNotFoundError:
            reqs = []
        for req in reqs:
            parts = req.split(";", 1)
            marker = parts[1].strip().lower() if len(parts) > 1 else ""
            if "extra" in marker and "vector" not in marker:
                continue
            if "legacy-vector" in marker:
                continue
            norm = _normalize_req_spec(parts[0])
            if norm:
                specs.add(norm)

    if not specs:
        return ""
    joined = "\n".join(sorted(specs)).encode("utf-8")
    return hashlib.sha256(joined).hexdigest()[:16]


def runtime_abi_tag() -> str:
    """Return a concise host Python ABI + OS + arch identifier for runtime compatibility."""
    mach = (platform.machine() or "unknown").lower()
    return f"py{sys.version_info[0]}{sys.version_info[1]}-{sys.platform}-{mach}"


_REQ_CLAUSE_RE = re.compile(r"^\s*(===|==|~=|>=|<=|!=|>|<)\s*([^\s,;]+)\s*$")
_REQ_SPLIT_RE = re.compile(r"^([A-Za-z0-9._-]+)(?:\[[^\]]*\])?\s*(.*)$")


def _clause_satisfied(installed_ver: str, op: str, target_ver: str) -> bool:
    """Evaluate a single PEP 440 specifier clause without external dependencies."""
    if op == "===":
        return installed_ver.strip() == target_ver.strip()
    try:
        inst_t = parse_release_tuple(installed_ver)
        tgt_t = parse_release_tuple(target_ver)
    except ValueError:
        return True
    if op == "==":
        return inst_t == tgt_t
    if op == "!=":
        return inst_t != tgt_t
    if op == ">=":
        return inst_t >= tgt_t
    if op == "<=":
        return inst_t <= tgt_t
    if op == ">":
        return inst_t > tgt_t
    if op == "<":
        return inst_t < tgt_t
    if op == "~=":
        parts = [int(p) for p in re.split(r"[^0-9]+", target_ver.strip()) if p][:3]
        upper = (parts[0], parts[1] + 1, 0, 0, 0, 0) if len(parts) >= 2 else (parts[0] + 1, 0, 0, 0, 0, 0)
        return tgt_t <= inst_t < upper
    return True


def _req_specifiers_satisfied(installed_ver: str, spec_expr: str) -> bool:
    """Evaluate comma-separated PEP 440 specifiers cleanly using stdlib only."""
    for clause in spec_expr.split(","):
        clause = clause.strip()
        if not clause:
            continue
        m = _REQ_CLAUSE_RE.match(clause)
        if not m:
            continue
        if not _clause_satisfied(installed_ver, m.group(1), m.group(2)):
            return False
    return True


def installed_deps_satisfy_declarations(
    site_packages: Path,
    pyproject_path: Path | None = None,
) -> bool:
    """Verify real installed distributions in *site_packages* satisfy declared version ranges.

    Returns ``True`` cleanly when *site_packages* is a minimal mock without
    ``.dist-info`` metadata, and performs strict specifier checks whenever real
    distributions are present so fast-patch cannot reuse stale pinned deps.
    """
    if not site_packages.is_dir():
        return False
    dist_dirs = list(site_packages.glob("*.dist-info"))
    if not dist_dirs:
        return True
    installed_versions: dict[str, str] = {}
    parser = email.parser.HeaderParser()
    for d in dist_dirs:
        meta_file = d / "METADATA"
        if not meta_file.is_file():
            continue
        try:
            meta = parser.parsestr(meta_file.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        raw_name = (meta.get("Name") or "").strip()
        raw_ver = (meta.get("Version") or "").strip()
        if raw_name and raw_ver:
            installed_versions[re.sub(r"[-_.]+", "-", raw_name).lower()] = raw_ver
    if not installed_versions:
        return True

    candidate = pyproject_path or (Path(__file__).resolve().parents[2] / "pyproject.toml")
    if not candidate.is_file():
        return True

    data = tomllib.loads(candidate.read_text(encoding="utf-8"))
    project = data.get("project") or {}
    opt = project.get("optional-dependencies") or {}
    raw_reqs = [*(project.get("dependencies") or []), *(opt.get("vector") or [])]
    for raw in raw_reqs:
        req_str = str(raw).strip()
        if not req_str:
            continue
        parts = req_str.split(";", 1)
        marker = parts[1].strip().lower() if len(parts) > 1 else ""
        if "legacy-vector" in marker or ("extra" in marker and "vector" not in marker):
            continue
        m = _REQ_SPLIT_RE.match(parts[0].strip())
        if not m:
            continue
        norm_name = re.sub(r"[-_.]+", "-", m.group(1)).lower()
        spec_expr = m.group(2).strip()
        ver = installed_versions.get(norm_name)
        if not ver:
            return False
        if spec_expr and not _req_specifiers_satisfied(ver, spec_expr):
            return False
    return True
