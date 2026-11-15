"""The evidence corpus gate must fail closed in both directions.

A published repo lost 1,143 research images, paper titles and machine paths to a
stray `git add docs/evidence`. `.gitignore` cannot stop `git add -f`, so the gate
in `scripts/check_no_evidence_tracking.py` is the enforcement; these cases prove
it catches a tracked corpus and still passes a clean tree.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_no_evidence_tracking.py"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=gate", "-c", "user.email=gate@example.invalid", *args],
        check=True,
        capture_output=True,
    )


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    (repo / "README.md").write_text("clean\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "--quiet", "-m", "base")
    return repo


def _run(repo: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), *extra],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_clean_repository_passes(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    result = _run(repo)
    assert result.returncode == 0, result.stderr
    assert "no evidence corpus" in result.stdout


def test_tracked_corpus_file_fails(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    corpus = repo / "docs" / "evidence" / "r3" / "page_001.jpg"
    corpus.parent.mkdir(parents=True)
    corpus.write_bytes(b"\xff\xd8\xff")
    _git(repo, "add", "-f", "docs/evidence/r3/page_001.jpg")
    _git(repo, "commit", "--quiet", "-m", "accidental corpus commit")

    result = _run(repo)
    assert result.returncode == 1, result.stdout
    assert "docs/evidence/r3/page_001.jpg" in result.stderr


def test_corpus_added_then_deleted_is_caught_with_base(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    corpus = repo / "docs" / "evidence" / "r3" / "page_002.jpg"
    corpus.parent.mkdir(parents=True)
    corpus.write_bytes(b"\xff\xd8\xff")
    _git(repo, "add", "-f", "docs/evidence/r3/page_002.jpg")
    _git(repo, "commit", "--quiet", "-m", "add then delete")
    base = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD~1"], capture_output=True, text=True, check=True
    ).stdout.strip()
    _git(repo, "rm", "--quiet", "-r", "docs/evidence")
    _git(repo, "commit", "--quiet", "-m", "remove")

    # The tree is clean, but the branch still carries the corpus in its history.
    assert _run(repo).returncode == 0
    widened = _run(repo, "--base", base)
    assert widened.returncode == 1, widened.stdout
    assert "docs/evidence/r3/page_002.jpg" in widened.stderr
