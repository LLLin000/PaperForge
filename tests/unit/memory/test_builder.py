from __future__ import annotations

from paperforge.memory.builder import compute_hash


def test_compute_hash_deterministic():
    items1 = [{"zotero_key": "A"}, {"zotero_key": "B"}]
    items2 = [{"zotero_key": "B"}, {"zotero_key": "A"}]
    assert compute_hash(items1) == compute_hash(items2)


def test_compute_hash_different_for_different_data():
    items1 = [{"zotero_key": "A", "title": "X"}]
    items2 = [{"zotero_key": "A", "title": "Y"}]
    assert compute_hash(items1) != compute_hash(items2)


def test_compute_hash_handles_empty():
    assert compute_hash([]) == compute_hash([])
    assert len(compute_hash([])) == 64  # SHA-256 hex
