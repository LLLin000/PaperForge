from pathlib import Path

import scripts.dev.m3_migration_harness as harness
import scripts.dev.r2_content_audit as audit


def test_format_only_requires_numbering_or_markdown_removal():
    assert audit.strip_format("3.3. The 16 Hz exposure") == audit.strip_format("The 16 Hz exposure")
    assert audit.strip_format("3.4. Modulation of Piezo 1-Mediated influx") != audit.strip_format(
        "1 Cells by Small Chemicals"
    )


def test_waiver_matches_only_exact_old_new_hashes():
    baseline = {
        "fulltext_sha256": "a" * 64,
        "structured_sha256": "b" * 64,
        "block_hashes": {"6:12": "c" * 64},
    }
    current = {
        "fulltext_sha256": "d" * 64,
        "structured_sha256": "e" * 64,
        "block_hashes": {"6:12": "f" * 64},
    }
    spec = {
        "old_fulltext_sha256": "a" * 64,
        "new_fulltext_sha256": "d" * 64,
        "old_structured_sha256": "b" * 64,
        "new_structured_sha256": "e" * 64,
        "block_changes": True,
        "blocks": [{"page": 6, "block_id": "12", "old_sha256": "c" * 64, "new_sha256": "f" * 64}],
        "verdict": "PASS",
        "evidence": "docs/evidence/r2-audit/content-r2e.json",
    }
    assert harness._waiver_matches(spec, baseline, current)
    current["fulltext_sha256"] = "0" * 64
    assert not harness._waiver_matches(spec, baseline, current)
    current["fulltext_sha256"] = "d" * 64
    current["block_hashes"]["6:12"] = "0" * 64
    assert not harness._waiver_matches(spec, baseline, current)


def test_baseline_fulltext_length_is_not_overwritten_by_block_text(tmp_path: Path):
    paper = tmp_path / "paper"
    (paper / "structure").mkdir(parents=True)
    fulltext = "alpha beta gamma delta"
    (paper / "fulltext.md").write_text(fulltext, encoding="utf-8")
    (paper / "structure" / "blocks.structured.jsonl").write_text(
        '{"page": 1, "block_id": "1", "text": "x"}\n', encoding="utf-8"
    )
    baseline = harness.historical_baseline(paper)
    assert baseline["fulltext_chars"] == len(fulltext)


def test_waiver_rejects_empty_shell_and_missing_contract_fields():
    baseline = {
        "fulltext_sha256": "a" * 64,
        "structured_sha256": "b" * 64,
        "block_hashes": {},
    }
    current = {
        "fulltext_sha256": "c" * 64,
        "structured_sha256": "d" * 64,
        "block_hashes": {},
    }
    assert not harness._waiver_matches({}, baseline, current)
    valid = {
        "old_fulltext_sha256": "a" * 64,
        "new_fulltext_sha256": "c" * 64,
        "old_structured_sha256": "b" * 64,
        "new_structured_sha256": "d" * 64,
        "block_changes": False,
        "blocks": [],
        "verdict": "PASS",
        "evidence": "docs/evidence/r2-audit/content-r2e.json",
    }
    assert harness._waiver_matches(valid, baseline, current)
    for key in ("old_fulltext_sha256", "verdict", "evidence"):
        broken = dict(valid)
        broken.pop(key)
        assert not harness._waiver_matches(broken, baseline, current)
    broken = dict(valid, block_changes=True)
    assert not harness._waiver_matches(broken, baseline, current)
