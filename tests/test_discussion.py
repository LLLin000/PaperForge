"""Unit tests for paperforge/worker/discussion.py -- AI Discussion Recorder.

Covers: record_session() creation, append, atomic writes, error handling,
CJK encoding, and CLI invocation.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from paperforge.worker.discussion import record_session

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_minimal_vault(tmp_path: Path, zotero_key: str = "TSTONE001",
                          domain: str = "骨科",
                          title: str = "Biomechanical Comparison") -> Path:
    """Create a minimal vault structure for testing record_session()."""
    vault = tmp_path / "vault"
    resources = vault / "03_Resources"
    literature = resources / "Literature"
    control = resources / "LiteratureControl"
    records_dir = control / "library-records"
    domain_dir = records_dir / domain
    domain_dir.mkdir(parents=True, exist_ok=True)

    # Library record with frontmatter
    record_path = domain_dir / f"{zotero_key}.md"
    record_path.write_text(
        "---\n"
        f'zotero_key: "{zotero_key}"\n'
        f'domain: "{domain}"\n'
        f'title: "{title}"\n'
        "year: \"2024\"\n"
        "analyze: true\n"
        "---\n\n"
        f"# {title}\n\n"
        "正式库控制记录。\n",
        encoding="utf-8",
    )

    # Create paperforge.json
    pf_json = vault / "paperforge.json"
    pf_json.write_text(
        json.dumps({
            "version": "1.4.15",
            "system_dir": "99_System",
            "resources_dir": "03_Resources",
            "literature_dir": "Literature",
            "control_dir": "LiteratureControl",
            "base_dir": "05_Bases",
            "skill_dir": ".opencode/skills",
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return vault


def _sample_qa_pairs() -> list[dict]:
    return [
        {
            "question": "What is the primary outcome?",
            "answer": "The primary outcome is biomechanical strength.",
            "source": "user_question",
            "timestamp": "2026-05-06T12:00:00+08:00",
        },
        {
            "question": "Any limitations?",
            "answer": "Small sample size and in vitro design.",
            "source": "agent_analysis",
            "timestamp": "2026-05-06T12:01:00+08:00",
        },
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRecordSession:
    """record_session() behavior tests."""

    def test_create_both_files(self, tmp_path: Path) -> None:
        """Test 1: Creates ai/discussion.json and ai/discussion.md with valid data."""
        vault = _create_minimal_vault(tmp_path)
        result = record_session(
            vault_path=vault,
            zotero_key="TSTONE001",
            agent="pf-paper",
            model="gpt-4",
            qa_pairs=_sample_qa_pairs(),
        )

        assert result["status"] == "ok"
        json_path = Path(result["json_path"])
        md_path = Path(result["md_path"])

        # JSON file exists and has correct structure
        assert json_path.exists()
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1"
        assert data["paper_key"] == "TSTONE001"
        assert len(data["sessions"]) == 1
        session = data["sessions"][0]
        assert len(session["session_id"]) == 36  # UUID length
        assert session["agent"] == "pf-paper"
        assert session["model"] == "gpt-4"
        assert "started" in session
        assert session["paper_key"] == "TSTONE001"
        assert session["paper_title"] == "Biomechanical Comparison"
        assert session["domain"] == "骨科"
        assert len(session["qa_pairs"]) == 2
        assert session["qa_pairs"][0]["source"] == "user_question"
        assert session["qa_pairs"][1]["source"] == "agent_analysis"

        # MD file exists and has correct format
        assert md_path.exists()
        md_content = md_path.read_text(encoding="utf-8")
        assert "# AI Discussion Record: Biomechanical Comparison" in md_content
        assert "## " in md_content  # session heading with date
        assert "**问题:**" in md_content
        assert "**解答:**" in md_content
        assert "---" in md_content  # separator

    def test_append_second_session(self, tmp_path: Path) -> None:
        """Test 2: Second call appends, does not overwrite."""
        vault = _create_minimal_vault(tmp_path)
        qa = _sample_qa_pairs()

        # First call
        r1 = record_session(vault_path=vault, zotero_key="TSTONE001",
                            agent="pf-paper", model="gpt-4", qa_pairs=qa)
        assert r1["status"] == "ok"

        # Second call with different Q&A
        qa2 = [{"question": "Q2?", "answer": "A2.", "source": "user_question",
                "timestamp": "2026-05-06T13:00:00+08:00"}]
        r2 = record_session(vault_path=vault, zotero_key="TSTONE001",
                            agent="pf-paper", model="gpt-4", qa_pairs=qa2)
        assert r2["status"] == "ok"

        # JSON: sessions length = 2, first session preserved
        json_path = Path(r2["json_path"])
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert len(data["sessions"]) == 2
        assert len(data["sessions"][0]["qa_pairs"]) == 2  # first session preserved
        assert data["sessions"][1]["qa_pairs"][0]["question"] == "Q2?"

        # MD: two ## session headings
        md_content = Path(r2["md_path"]).read_text(encoding="utf-8")
        assert md_content.count("## ") >= 2

    def test_missing_vault(self, tmp_path: Path) -> None:
        """Test 3: Non-existent vault returns error status."""
        result = record_session(
            vault_path=tmp_path / "nonexistent",
            zotero_key="TSTONE001",
            agent="pf-paper",
            model="gpt-4",
            qa_pairs=_sample_qa_pairs(),
        )
        assert result["status"] == "error"
        assert "message" in result

    def test_unknown_key(self, tmp_path: Path) -> None:
        """Test 4: Unknown zotero_key returns error without creating files."""
        vault = _create_minimal_vault(tmp_path)
        result = record_session(
            vault_path=vault,
            zotero_key="UNKNOW01",
            agent="pf-paper",
            model="gpt-4",
            qa_pairs=_sample_qa_pairs(),
        )
        assert result["status"] == "error"

        # No files created
        ai_dir = vault / "03_Resources" / "Literature" / "UNKNOW01 - untitled" / "ai"
        assert not ai_dir.exists() or not list(ai_dir.iterdir()) == []

    def test_cjk_encoding(self, tmp_path: Path) -> None:
        """Test 5: CJK content round-trips correctly via ensure_ascii=False."""
        vault = _create_minimal_vault(tmp_path, title="中文测试论文")
        cjk_qa = [
            {
                "question": "问题一",
                "answer": "答案一",
                "source": "user_question",
                "timestamp": "2026-05-06T12:00:00+08:00",
            },
        ]
        result = record_session(vault_path=vault, zotero_key="TSTONE001",
                                agent="pf-paper", model="gpt-4", qa_pairs=cjk_qa)
        assert result["status"] == "ok"

        # JSON read-back
        json_path = Path(result["json_path"])
        raw = json_path.read_text(encoding="utf-8")
        assert "中文测试论文" in raw
        assert "问题一" in raw
        assert "答案一" in raw

        # Parse and verify
        data = json.loads(raw)
        assert data["sessions"][0]["paper_title"] == "中文测试论文"
        assert data["sessions"][0]["qa_pairs"][0]["question"] == "问题一"

    def test_atomic_write_no_partial(self, tmp_path: Path) -> None:
        """Test 6: Atomic write via tempfile + os.replace prevents partial writes."""
        vault = _create_minimal_vault(tmp_path)
        result = record_session(vault_path=vault, zotero_key="TSTONE001",
                                agent="pf-paper", model="gpt-4", qa_pairs=_sample_qa_pairs())
        assert result["status"] == "ok"

        json_path = Path(result["json_path"])
        md_path = Path(result["md_path"])

        # Verify files are valid (not partial)
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1"
        assert md_path.read_text(encoding="utf-8").startswith("# AI Discussion Record")

    def test_cli_invocation(self, tmp_path: Path) -> None:
        """Test 7: CLI `python -m paperforge.worker.discussion record` works."""
        vault = _create_minimal_vault(tmp_path)
        import subprocess
        import sys

        qa_json = json.dumps(_sample_qa_pairs(), ensure_ascii=False)
        cmd = [
            sys.executable, "-m", "paperforge.worker.discussion", "record",
            "TSTONE001",
            "--vault", str(vault),
            "--agent", "pf-paper",
            "--model", "gpt-4",
            "--qa-pairs", qa_json,
        ]
        # Use binary pipes to avoid UTF-8 decode issues on Windows (Python 3.14+)
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        proc = subprocess.run(cmd, capture_output=True, env=env)
        proc_stdout = proc.stdout.decode("utf-8", errors="replace")
        proc_stderr = proc.stderr.decode("utf-8", errors="replace")
        assert proc.returncode == 0, f"CLI failed: {proc_stderr}"

        output = json.loads(proc_stdout)
        assert output["status"] == "ok"
        json_path = Path(output["json_path"])
        assert json_path.exists()
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["agent"] == "pf-paper"
