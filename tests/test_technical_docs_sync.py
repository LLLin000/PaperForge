"""Automated drift gate keeping PaperForge technical handbooks synced with code."""

from __future__ import annotations

import importlib.util
import re
import subprocess
from pathlib import Path

import pytest

import paperforge.actions.registry as action_registry
import paperforge.cli as pf_cli
import paperforge.config as pf_config
import paperforge.memory.schema as memory_schema
import paperforge.probes as pf_probes

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parent.parent
HANDBOOK_DIR = REPO_ROOT / "docs" / "handbook"
REFERENCE_PATH = REPO_ROOT / "docs" / "PAPERFORGE-TECHNICAL-REFERENCE.md"
DOCS_INDEX_PATH = REPO_ROOT / "docs" / "README.md"
ARCHIVE_INDEX_PATH = REPO_ROOT / "docs" / "archive" / "README.md"

EXPECTED_CHAPTERS = (
    "01-architecture-and-storage.md",
    "02-config-auth-and-runtime.md",
    "03-protocol-pfresult-and-stream.md",
    "04-probes-and-reconcile.md",
    "05-action-registry-and-safety.md",
    "06-zotero-sync-and-lineage.md",
    "07-ocr-provider-and-canonical.md",
    "08-ocr-v3-pipeline-and-objects.md",
    "09-render-audit-and-reconcile.md",
    "10-memory-db-and-retrieval.md",
    "11-annotations-and-living-memory.md",
    "12-agent-skills-and-workflows.md",
    "13-obsidian-plugin-and-views.md",
    "14-testing-gates-and-maintenance.md",
    "15-vault-migration-and-ownership.md",
)

REQUIRED_H2_SECTIONS = (
    "## 1. 职责与非目标边界",
    "## 2. 核心源码与单测映射表",
    "## 3. 磁盘文件、数据库表与协议 JSON 字段字典",
    "## 4. 核心执行链路、状态机与顺序不变量",
    "## 5. 配置项、环境变量、CLI 入口与错误码",
    "## 6. 边界防护与 Fail-Closed 防呆规则",
    "## 7. 维修、调试与升级 Checklist",
)

FORBIDDEN_LEGACY_PATTERNS = (
    re.compile(r"paperforge\s+selection-sync"),
    re.compile(r"paperforge\s+index-refresh"),
    re.compile(r"paperforge\s+ocr\s+run"),
    re.compile(r"paperforge\s+ocr\s+doctor"),
    re.compile(r"/LD-deep"),
    re.compile(r"/LD-paper"),
    re.compile(r"/lp-ocr(?!\w)"),
    re.compile(r"/lp-index-refresh"),
    re.compile(r"/lp-selection-sync"),
    re.compile(r"/lp-status(?!\w)"),
)

_REPO_PATH_RE = re.compile(r"(?<![.\w/-])((?:paperforge|scripts|tests|docs)/[A-Za-z0-9_./-]+)")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _load_script(rel_path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / rel_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read_chapter(filename: str) -> str:
    return (HANDBOOK_DIR / filename).read_text(encoding="utf-8").replace("\r\n", "\n")


def _all_managed_doc_paths() -> list[Path]:
    return [
        *(HANDBOOK_DIR / name for name in EXPECTED_CHAPTERS),
        DOCS_INDEX_PATH,
        ARCHIVE_INDEX_PATH,
        REFERENCE_PATH,
    ]


def test_all_14_handbook_chapters_exist_with_standard_sections() -> None:
    actual = sorted(p.name for p in HANDBOOK_DIR.glob("*.md"))
    assert actual == list(EXPECTED_CHAPTERS)

    for name in EXPECTED_CHAPTERS:
        text = _read_chapter(name)
        lines = text.splitlines()
        assert len(lines) >= 200, f"{name} unexpectedly short ({len(lines)} lines)"
        assert lines[0].startswith("# 第 "), f"{name} must start with unified H1 chapter title"

        last_pos = -1
        for section in REQUIRED_H2_SECTIONS:
            pos = text.find(f"\n{section}\n")
            assert pos != -1, f"{name} missing required H2 section: {section}"
            assert pos > last_pos, f"{name} has out-of-order H2 section: {section}"
            last_pos = pos


def test_referenced_repo_paths_and_markdown_links_resolve() -> None:
    ls_res = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    tracked_files = {line.strip() for line in ls_res.stdout.splitlines() if line.strip()}
    tracked_dirs: set[str] = set()
    for rel in tracked_files:
        parts = Path(rel).parts
        for idx in range(1, len(parts)):
            tracked_dirs.add("/".join(parts[:idx]))

    missing_paths: list[str] = []
    for doc_path in (*(HANDBOOK_DIR / n for n in EXPECTED_CHAPTERS), DOCS_INDEX_PATH):
        text = doc_path.read_text(encoding="utf-8")
        rel_doc = doc_path.relative_to(REPO_ROOT).as_posix()
        for match in _REPO_PATH_RE.finditer(text):
            candidate = match.group(1).rstrip("/")
            if candidate not in tracked_files and candidate not in tracked_dirs:
                missing_paths.append(f"{rel_doc}: {candidate}")
    assert not missing_paths, (
        "Missing or untracked repo paths referenced in handbook/index:\n  "
        + "\n  ".join(missing_paths)
    )

    broken_links: list[str] = []
    ref_text = REFERENCE_PATH.read_text(encoding="utf-8")
    ref_anchors = set(re.findall(r'<a id="(chapter-\d{2})"></a>', ref_text))

    for doc_path in _all_managed_doc_paths():
        text = doc_path.read_text(encoding="utf-8")
        rel_doc = doc_path.relative_to(REPO_ROOT).as_posix()
        for match in _MD_LINK_RE.finditer(text):
            target = match.group(2).strip()
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if target.startswith("#"):
                anchor = target[1:]
                if doc_path == REFERENCE_PATH and anchor not in ref_anchors:
                    broken_links.append(f"{rel_doc}: unknown internal anchor {target}")
                continue
            if "#" in target:
                broken_links.append(f"{rel_doc}: cross-file link must not use '#anchor': {target}")
                continue
            resolved = (doc_path.parent / target).resolve()
            if not resolved.exists():
                broken_links.append(f"{rel_doc}: dead relative link {target}")
    assert not broken_links, "Broken markdown links:\n  " + "\n  ".join(broken_links)


def test_no_forbidden_legacy_commands_or_machine_paths() -> None:
    path_checker = _load_script("scripts/check_machine_paths.py", "check_machine_paths")
    violations: list[str] = []

    for doc_path in _all_managed_doc_paths():
        text = doc_path.read_text(encoding="utf-8")
        rel_doc = doc_path.relative_to(REPO_ROOT).as_posix()
        for pattern in FORBIDDEN_LEGACY_PATTERNS:
            for hit in pattern.finditer(text):
                violations.append(f"{rel_doc}: forbidden legacy phrase {hit.group(0)!r}")
        for marker_name, marker_re in path_checker.MARKERS:
            if marker_re.search(text):
                violations.append(f"{rel_doc}: host machine path marker {marker_name!r}")

    assert not violations, "Documentation hygiene violations:\n  " + "\n  ".join(violations)


def test_live_code_symbols_match_handbook_documentation() -> None:
    ch02 = _read_chapter("02-config-auth-and-runtime.md")
    ch03 = _read_chapter("03-protocol-pfresult-and-stream.md")
    ch04 = _read_chapter("04-probes-and-reconcile.md")
    ch05 = _read_chapter("05-action-registry-and-safety.md")
    ch10 = _read_chapter("10-memory-db-and-retrieval.md")
    ch12 = _read_chapter("12-agent-skills-and-workflows.md")

    missing_cfg = [spec.key for spec in pf_config.FIELD_SPECS if spec.key not in ch02]
    assert not missing_cfg, f"Config keys missing from Chapter 02: {missing_cfg}"

    missing_platforms = [p for p in pf_config.AGENT_PLATFORM_IDS if p not in ch02 and p not in ch12]
    assert not missing_platforms, f"Agent platform IDs missing from Chapter 02/12: {missing_platforms}"

    parser = pf_cli.build_parser()
    subparsers_action = next(
        act for act in parser._actions if getattr(act, "choices", None) is not None
    )
    cli_commands = sorted(subparsers_action.choices.keys())
    missing_cli = [cmd for cmd in cli_commands if f"`{cmd}`" not in ch03 and cmd not in ch03]
    assert not missing_cli, f"CLI top-level commands missing from Chapter 03: {missing_cli}"

    missing_modules = [mod for mod in sorted(pf_probes.SUPPORTED_MODULES) if mod not in ch04]
    assert not missing_modules, f"Probe modules missing from Chapter 04: {missing_modules}"

    missing_states = [state for state in sorted(pf_probes.VALID_USER_STATES) if state not in ch04]
    assert not missing_states, f"Probe user states missing from Chapter 04: {missing_states}"

    missing_actions = [aid for aid in sorted(action_registry.ACTION_REGISTRY) if aid not in ch05]
    assert not missing_actions, f"ACTION_REGISTRY actions missing from Chapter 05: {missing_actions}"

    assert f"CURRENT_SCHEMA_VERSION = {memory_schema.CURRENT_SCHEMA_VERSION}" in ch10
    expected_tables = [*memory_schema.ALL_TABLES, *memory_schema.VEC_TABLES, "lineage"]
    missing_tables = [tbl for tbl in expected_tables if tbl not in ch10]
    assert not missing_tables, f"SQLite tables missing from Chapter 10: {missing_tables}"


def test_compiled_technical_reference_matches_handbook_sources() -> None:
    compiler = _load_script("scripts/build_technical_reference.py", "build_technical_reference")
    expected = compiler.compile_reference(HANDBOOK_DIR, REPO_ROOT / "paperforge" / "__init__.py")
    actual = REFERENCE_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert actual == expected, (
        "docs/PAPERFORGE-TECHNICAL-REFERENCE.md is out of sync with docs/handbook/*.md; "
        "run `python scripts/build_technical_reference.py`"
    )
