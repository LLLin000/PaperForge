#!/usr/bin/env python3
"""Compile PaperForge's 14 subsystem handbook chapters into one master reference.

Usage:
    python scripts/build_technical_reference.py
    python scripts/build_technical_reference.py --check
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HANDBOOK_DIR = REPO_ROOT / "docs" / "handbook"
OUTPUT_PATH = REPO_ROOT / "docs" / "PAPERFORGE-TECHNICAL-REFERENCE.md"
INIT_PATH = REPO_ROOT / "paperforge" / "__init__.py"

_CHAPTER_FILE_RE = re.compile(r"^(\d{2})-.+\.md$")
_VERSION_RE = re.compile(r'__version__\s*=\s*"([^"]+)"')
_FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
_ATX_HEADING_RE = re.compile(r"^(#{1,5})(\s+.*)$")
_INTRA_HANDBOOK_LINK_RE = re.compile(r"\[([^\]]+)\]\((\d{2}-[^)#]+\.md)(?:#[^)]*)?\)")
_UP_LINK_RE = re.compile(r"\[([^\]]+)\]\(((?:\.\./)+)([^)]+)\)")

EXPECTED_CHAPTER_COUNT = 14


def read_package_version(init_path: Path = INIT_PATH) -> str:
    """Parse ``paperforge.__version__`` without importing heavy runtime packages."""
    text = init_path.read_text(encoding="utf-8")
    match = _VERSION_RE.search(text)
    if not match:
        raise RuntimeError(f"Could not parse __version__ from {init_path}")
    return match.group(1)


def discover_chapters(handbook_dir: Path = HANDBOOK_DIR) -> list[tuple[str, Path]]:
    """Return sorted ``(chapter_num, path)`` pairs from ``docs/handbook/``."""
    chapters: list[tuple[str, Path]] = []
    for path in sorted(handbook_dir.glob("*.md")):
        match = _CHAPTER_FILE_RE.match(path.name)
        if match:
            chapters.append((match.group(1), path))
    if len(chapters) != EXPECTED_CHAPTER_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_CHAPTER_COUNT} handbook chapters in {handbook_dir}, "
            f"found {len(chapters)}: {[p.name for _, p in chapters]}"
        )
    return chapters


def compute_source_digest(chapters: list[tuple[str, Path]]) -> str:
    """Compute deterministic SHA-256 over ordered normalized chapter contents."""
    hasher = hashlib.sha256()
    for _num, path in chapters:
        normalized = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        hasher.update(path.name.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(normalized.encode("utf-8"))
        hasher.update(b"\0")
    return hasher.hexdigest()


def _rewrite_links(line: str) -> str:
    """Rewrite handbook-relative markdown links for ``docs/PAPERFORGE-TECHNICAL-REFERENCE.md``."""
    line = _INTRA_HANDBOOK_LINK_RE.sub(
        lambda m: f"[{m.group(1)}](#chapter-{m.group(2)[:2]})", line
    )
    return _UP_LINK_RE.sub(
        lambda m: f"[{m.group(1)}]({m.group(2)[3:]}{m.group(3)})", line
    )


def _transform_chapter(chapter_num: str, path: Path) -> tuple[str, str]:
    """Return ``(title, transformed_markdown)`` for one handbook chapter."""
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip("\n")
    lines = raw.split("\n")
    if not lines or not lines[0].startswith("# "):
        raise RuntimeError(f"{path} must start with a single '# ' H1 heading")

    title = lines[0][2:].strip()
    out_lines: list[str] = [
        f'<a id="chapter-{chapter_num}"></a>',
        "",
        f"## {title}",
        "",
        f"> 源文件：`docs/handbook/{path.name}`",
    ]

    fence_marker: str | None = None
    for line in lines[1:]:
        fence_match = _FENCE_RE.match(line)
        if fence_match:
            token = fence_match.group(1)
            stripped = line.strip()
            if fence_marker is None:
                fence_marker = token[0] * len(token)
            elif len(stripped) >= len(fence_marker) and set(stripped) == {fence_marker[0]}:
                fence_marker = None
            out_lines.append(line)
            continue

        if fence_marker is not None:
            out_lines.append(line)
            continue

        heading_match = _ATX_HEADING_RE.match(line)
        if heading_match:
            hashes, rest = heading_match.groups()
            line = f"{'#' * (len(hashes) + 1)}{rest}"
        else:
            line = _rewrite_links(line)

        out_lines.append(line)

    return title, "\n".join(out_lines).rstrip("\n")


def compile_reference(
    handbook_dir: Path = HANDBOOK_DIR,
    init_path: Path = INIT_PATH,
) -> str:
    """Build deterministic single-file technical reference markdown."""
    version = read_package_version(init_path)
    chapters = discover_chapters(handbook_dir)
    digest = compute_source_digest(chapters)

    transformed: list[tuple[str, str, str, str]] = []
    for num, path in chapters:
        title, body = _transform_chapter(num, path)
        transformed.append((num, path.name, title, body))

    toc_lines = [
        "| 章节 | 主题 | 分册源文件 |",
        "| :--- | :--- | :--- |",
    ]
    for num, filename, title, _body in transformed:
        toc_lines.append(
            f"| [{num}](#chapter-{num}) | [{title}](#chapter-{num}) "
            f"| [`{filename}`](handbook/{filename}) |"
        )

    parts: list[str] = [
        "<!-- prettier-ignore-start -->",
        "<!-- AUTO-GENERATED FILE — DO NOT EDIT MANUALLY. "
        "Regenerate via: python scripts/build_technical_reference.py -->",
        "",
        "# PaperForge 全量技术参考手册（Compiled Technical Reference）",
        "",
        f"> **版本**：`{version}` | **章节数**：`{len(transformed)}` | **分册指纹**：`sha256:{digest[:16]}`",
        ">",
        "> 本文档由 `scripts/build_technical_reference.py` 从 `docs/handbook/01`–`14` 自动汇编而成，"
        "供维护者与 AI Agent 作为单文件全景检索底本使用。所有结构、字段、CLI、Probe、Action "
        "与 SQLite Schema 均有自动化同步门禁 `tests/test_technical_docs_sync.py` 与源码双向锁定。",
        "",
        "## 目录（Table of Contents）",
        "",
        *toc_lines,
        "",
        "---",
        "",
    ]

    for idx, (_num, _filename, _title, body) in enumerate(transformed):
        if idx > 0:
            parts.extend(["", "---", ""])
        parts.append(body)

    parts.extend(["", "<!-- prettier-ignore-end -->", ""])
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify docs/PAPERFORGE-TECHNICAL-REFERENCE.md matches compiled output without writing.",
    )
    args = parser.parse_args(argv)

    expected = compile_reference()

    if args.check:
        if not OUTPUT_PATH.is_file():
            print(f"[FAIL] Missing compiled reference: {OUTPUT_PATH}", file=sys.stderr)
            return 1
        actual = OUTPUT_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")
        if actual != expected:
            diff = "".join(
                difflib.unified_diff(
                    actual.splitlines(keepends=True)[:120],
                    expected.splitlines(keepends=True)[:120],
                    fromfile="on-disk",
                    tofile="compiled",
                )
            )
            print(
                "[FAIL] docs/PAPERFORGE-TECHNICAL-REFERENCE.md is out of sync with docs/handbook/*.md.\n"
                "Run `python scripts/build_technical_reference.py` to regenerate.\n"
                + diff,
                file=sys.stderr,
            )
            return 1
        print(f"build_technical_reference: ok ({OUTPUT_PATH.relative_to(REPO_ROOT).as_posix()})")
        return 0

    OUTPUT_PATH.write_text(expected, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT).as_posix()} ({len(expected.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
