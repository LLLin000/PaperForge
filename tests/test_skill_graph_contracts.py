from __future__ import annotations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = REPO_ROOT / "paperforge" / "skills" / "paperforge" / "SKILL.md"
CLARIFY_MD = REPO_ROOT / "paperforge" / "skills" / "paperforge" / "atoms" / "clarify-user-intent.md"
RETRIEVAL_MD = REPO_ROOT / "paperforge" / "skills" / "paperforge" / "atoms" / "retrieval-routing.md"
DISCOVER_MD = REPO_ROOT / "paperforge" / "skills" / "paperforge" / "molecules" / "discover-papers.md"
EVIDENCE_MD = REPO_ROOT / "paperforge" / "skills" / "paperforge" / "molecules" / "find-supporting-evidence.md"


# --- Group 1: SKILL.md routing contracts ---

def test_skill_md_has_mechanical_routing() -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    assert "/pf-sync" in text and "/pf-ocr" in text and "/pf-status" in text


def test_skill_md_has_research_aliases() -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    assert "/pf-deep" in text and "/pf-paper" in text


def test_skill_md_refers_to_molecules_dir() -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    assert "molecules/" in text


def test_skill_md_refers_to_atoms_dir() -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    assert "atoms/" in text


# --- Group 2: Clarify intent atom contracts ---

def test_clarify_atom_has_trigger_conditions() -> None:
    text = CLARIFY_MD.read_text(encoding="utf-8")
    assert any(kw in text for kw in ["ambiguous", "short", "multi-intent", "multi"])


def test_clarify_atom_has_two_round_limit() -> None:
    text = CLARIFY_MD.read_text(encoding="utf-8")
    assert "两轮" in text or "2 轮" in text or "two rounds" in text or "2 rounds" in text


def test_clarify_atom_has_fixed_question_pattern() -> None:
    text = CLARIFY_MD.read_text(encoding="utf-8")
    assert "找某篇文章" in text or "找一篇" in text or "找一批" in text or "找支持" in text


# --- Group 3: Retrieval routing atom contracts ---

def test_retrieval_routing_has_fallback_ladder() -> None:
    text = RETRIEVAL_MD.read_text(encoding="utf-8")
    assert "metadata candidate generation" in text or "metadata" in text.lower()
    assert "rg" in text
    assert any(kw in text for kw in ["grep", "findstr", "fallback", "degrade"])


def test_retrieval_routing_has_semantic_optional_rule() -> None:
    text = RETRIEVAL_MD.read_text(encoding="utf-8")
    assert "optional" in text.lower() or "supplementary" in text.lower() or "only for candidate expansion" in text


def test_skill_md_has_intent_level_trigger_language() -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    assert "必须调用 paperforge skill" in text
    assert "collection / domain" in text or "正文内容" in text


# --- Group 4: Molecule output shape contracts ---

def test_discover_papers_output_is_paper_list() -> None:
    text = DISCOVER_MD.read_text(encoding="utf-8")
    assert "candidate" in text.lower() or "paper list" in text.lower()


def test_find_evidence_output_is_grouped_hits() -> None:
    text = EVIDENCE_MD.read_text(encoding="utf-8")
    assert "group" in text.lower() or "evidence hit" in text.lower() or "snippet" in text.lower()


def test_molecules_reference_query_plan() -> None:
    discover_text = DISCOVER_MD.read_text(encoding="utf-8")
    evidence_text = EVIDENCE_MD.read_text(encoding="utf-8")
    assert "query-plan" in discover_text
    assert "query-plan" in evidence_text
