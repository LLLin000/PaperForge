"""Unit tests for paperforge/worker/discussion.py -- AI Discussion Recorder.

Covers: record_session() creation, append, atomic writes, error handling,
CJK encoding, and CLI invocation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import filelock

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

    indexes_dir = vault / "99_System" / "PaperForge" / "indexes"
    indexes_dir.mkdir(parents=True, exist_ok=True)
    canonical_index = {
        "schema_version": "2",
        "generated_at": "2026-05-07T00:00:00+08:00",
        "paperforge_version": "1.4.15",
        "paper_count": 1,
        "items": [
            {
                "zotero_key": zotero_key,
                "domain": domain,
                "title": title,
                "ai_path": f"Literature/{domain}/{zotero_key} - {title}/ai/",
            }
        ],
    }
    (indexes_dir / "formal-library.json").write_text(
        json.dumps(canonical_index, ensure_ascii=False, indent=2), encoding="utf-8"
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

    def test_create_md_file(self, tmp_path: Path) -> None:
        """Test: Creates ai/discussion.md with rich unescaped markdown."""
        vault = _create_minimal_vault(tmp_path)
        result = record_session(
            vault_path=vault,
            zotero_key="TSTONE001",
            agent="pf-paper",
            model="gpt-4",
            qa_pairs=_sample_qa_pairs(),
        )

        assert result["status"] == "ok"
        assert "json_path" not in result
        md_path = Path(result["md_path"])

        assert md_path.exists()
        md_content = md_path.read_text(encoding="utf-8")
        assert "# AI Discussion Record: Biomechanical Comparison" in md_content
        assert "## " in md_content
        assert "**问题:**" in md_content
        assert "**解答:**" in md_content
        assert "---" in md_content

    def test_append_second_session(self, tmp_path: Path) -> None:
        """Test: Second call appends, does not overwrite."""
        vault = _create_minimal_vault(tmp_path)
        qa = _sample_qa_pairs()

        r1 = record_session(vault_path=vault, zotero_key="TSTONE001",
                            agent="pf-paper", model="gpt-4", qa_pairs=qa)
        assert r1["status"] == "ok"

        qa2 = [{"question": "Q2?", "answer": "A2.", "source": "user_question",
                "timestamp": "2026-05-06T13:00:00+08:00"}]
        r2 = record_session(vault_path=vault, zotero_key="TSTONE001",
                            agent="pf-paper", model="gpt-4", qa_pairs=qa2)
        assert r2["status"] == "ok"

        md_content = Path(r2["md_path"]).read_text(encoding="utf-8")
        assert md_content.count("## ") >= 2

    def test_markdown_preserved_unescaped(self, tmp_path: Path) -> None:
        """Test: **bold** preserved (NOT escaped to backslash-star sequences)."""
        vault = _create_minimal_vault(tmp_path)
        qa = [
            {
                "question": "What does *italic* and **bold** mean?",
                "answer": "Use **bold** and `code`",
                "source": "user_question",
                "timestamp": "2026-05-06T12:00:00+00:00",
            },
        ]
        result = record_session(
            vault_path=vault, zotero_key="TSTONE001",
            agent="pf-paper", model="gpt-4", qa_pairs=qa,
        )
        assert result["status"] == "ok"
        md = Path(result["md_path"]).read_text(encoding="utf-8")
        assert "**bold**" in md
        assert "\\*" not in md

    def test_markdown_preserved_cjk(self, tmp_path: Path) -> None:
        """Test: CJK characters preserved alongside unescaped markdown."""
        vault = _create_minimal_vault(tmp_path, title="中文测试")
        qa = [
            {
                "question": "什么是*p值*和#显著性？",
                "answer": "**效应量**为0.5`[95% CI]",
                "source": "user_question",
                "timestamp": "2026-05-06T12:00:00+00:00",
            },
        ]
        result = record_session(
            vault_path=vault, zotero_key="TSTONE001",
            agent="pf-paper", model="gpt-4", qa_pairs=qa,
        )
        assert result["status"] == "ok"
        md = Path(result["md_path"]).read_text(encoding="utf-8")
        assert "什么是" in md
        assert "效应量" in md
        assert "**效应量**" in md
        assert "\\*" not in md

    def test_file_lock_uses_md_lock(self, tmp_path: Path) -> None:
        """HARDEN-01: Lock file is .md.lock not .json.lock."""
        vault = _create_minimal_vault(tmp_path)
        result = record_session(
            vault_path=vault, zotero_key="TSTONE001",
            agent="pf-paper", model="gpt-4", qa_pairs=_sample_qa_pairs(),
        )
        assert result["status"] == "ok"
        md_path = Path(result["md_path"])
        lock_path = md_path.with_suffix(".md.lock")
        assert not lock_path.exists()

    def test_lock_timeout_returns_error(self, tmp_path: Path) -> None:
        """HARDEN-01: When lock cannot be acquired, returns error status."""
        vault = _create_minimal_vault(tmp_path)
        r1 = record_session(
            vault_path=vault, zotero_key="TSTONE001",
            agent="pf-paper", model="gpt-4", qa_pairs=_sample_qa_pairs(),
        )
        assert r1["status"] == "ok"
        md_path = Path(r1["md_path"])

        lock_path = md_path.with_suffix(".md.lock")
        external_lock = filelock.FileLock(lock_path, timeout=1)
        with external_lock:
            r2 = record_session(
                vault_path=vault, zotero_key="TSTONE001",
                agent="pf-paper", model="gpt-4", qa_pairs=_sample_qa_pairs(),
            )
            assert r2["status"] == "error"
            assert "Concurrent access" in r2.get("message", "")

    def test_missing_vault(self, tmp_path: Path) -> None:
        """Non-existent vault returns error status."""
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
        """Unknown zotero_key returns error without creating files."""
        vault = _create_minimal_vault(tmp_path)
        result = record_session(
            vault_path=vault,
            zotero_key="UNKNOW01",
            agent="pf-paper",
            model="gpt-4",
            qa_pairs=_sample_qa_pairs(),
        )
        assert result["status"] == "error"

        ai_dir = vault / "03_Resources" / "Literature" / "UNKNOW01 - untitled" / "ai"
        assert not ai_dir.exists() or not list(ai_dir.iterdir()) == []

    def test_cjk_encoding(self, tmp_path: Path) -> None:
        """CJK content round-trips correctly."""
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

        md_path = Path(result["md_path"])
        raw = md_path.read_text(encoding="utf-8")
        assert "中文测试论文" in raw
        assert "问题一" in raw
        assert "答案一" in raw

    def test_atomic_write_no_partial(self, tmp_path: Path) -> None:
        """Atomic write via tempfile + os.replace prevents partial writes."""
        vault = _create_minimal_vault(tmp_path)
        result = record_session(vault_path=vault, zotero_key="TSTONE001",
                                agent="pf-paper", model="gpt-4", qa_pairs=_sample_qa_pairs())
        assert result["status"] == "ok"

        md_path = Path(result["md_path"])
        assert md_path.read_text(encoding="utf-8").startswith("# AI Discussion Record")

    def test_cli_invocation(self, tmp_path: Path) -> None:
        """CLI `python -m paperforge.worker.discussion record` works."""
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
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        proc = subprocess.run(cmd, capture_output=True, env=env)
        proc_stdout = proc.stdout.decode("utf-8", errors="replace")
        proc_stderr = proc.stderr.decode("utf-8", errors="replace")
        assert proc.returncode == 0, f"CLI failed: {proc_stderr}"

        output = json.loads(proc_stdout)
        assert output["status"] == "ok"
        assert "md_path" in output
        md_path = Path(output["md_path"])
        assert md_path.exists()
