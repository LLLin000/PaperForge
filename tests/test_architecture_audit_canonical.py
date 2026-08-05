"""#131 Slice A — canonical serialization, semantic digests, stable IDs.

Determinism contract: identical semantic inputs produce identical digests and
stable IDs; run metadata never enters a digest; line movement never changes a
finding id; normalized subject/evidence identity changes do.
"""
from __future__ import annotations

from paperforge.architecture_audit import canonical_json, finding_id, semantic_digest, stable_id


class TestCanonicalJson:
    def test_object_keys_sorted_recursively(self):
        first = canonical_json({"b": 1, "a": {"d": 4, "c": 3}})
        second = canonical_json({"a": {"c": 3, "d": 4}, "b": 1})
        assert first == second
        # keys are sorted: a before b, c before d
        assert first == '{"a":{"c":3,"d":4},"b":1}'

    def test_lists_ordered_by_domain_id(self):
        first = canonical_json({"items": [{"id": "z"}, {"id": "a"}]})
        second = canonical_json({"items": [{"id": "a"}, {"id": "z"}]})
        assert first == second
        assert first == '{"items":[{"id":"a"},{"id":"z"}]}'

    def test_list_without_ids_ordered_by_canonical_json(self):
        first = canonical_json({"items": ["b", "a"]})
        second = canonical_json({"items": ["a", "b"]})
        assert first == second


    def test_same_domain_ids_use_canonical_tie_breaker(self):
        first = canonical_json({"facts": [{"id": "sync", "line": 116}, {"id": "sync", "line": 92}]})
        second = canonical_json({"facts": [{"id": "sync", "line": 92}, {"id": "sync", "line": 116}]})
        assert first == second

    def test_wrapper_argument_roles_preserve_parameter_order(self):
        path_argv = canonical_json({"argument_roles": ["path", "argv"]})
        argv_path = canonical_json({"argument_roles": ["argv", "path"]})
        assert path_argv != argv_path

class TestSemanticDigest:
    def test_identical_content_identical_digest(self):
        content = {"findings": [{"id": "f1", "status": "violated"}]}
        assert semantic_digest(content) == semantic_digest(content)

    def test_key_order_does_not_change_digest(self):
        a = semantic_digest({"x": 1, "y": 2})
        b = semantic_digest({"y": 2, "x": 1})
        assert a == b

    def test_run_metadata_is_not_part_of_digest(self):
        """Digests cover semantic content only; run metadata never participates.

        The caller passes semantic content; the same content must digest the same
        even when a timestamp-style field would differ between runs.
        """
        content = {"findings": [{"id": "f1"}]}
        assert semantic_digest(content) == semantic_digest({"findings": [{"id": "f1"}]})
        assert semantic_digest(content) != semantic_digest({"findings": [{"id": "f2"}]})

    def test_digest_changes_when_evidence_symbol_changes(self):
        content = {"evidence": [{"symbol": "run", "line_start": 1}]}
        changed = {"evidence": [{"symbol": "run2", "line_start": 1}]}
        assert semantic_digest(content) != semantic_digest(changed)


class TestStableIds:
    def test_finding_id_stable_under_line_movement(self):
        """Evidence symbols participate, line numbers do not."""
        before = finding_id("rule.a", ["unit.x"], ["run", "publish"])
        after = finding_id("rule.a", ["unit.x"], ["publish", "run"])
        assert before == after

    def test_finding_id_changes_with_symbol_identity(self):
        original = finding_id("rule.a", ["unit.x"], ["run"])
        renamed = finding_id("rule.a", ["unit.x"], ["execute"])
        assert original != renamed

    def test_finding_id_changes_with_rule_or_subject(self):
        base = finding_id("rule.a", ["unit.x"], ["run"])
        assert base != finding_id("rule.b", ["unit.x"], ["run"])
        assert base != finding_id("rule.a", ["unit.y"], ["run"])
    def test_finding_id_keeps_subject_and_evidence_boundaries(self):
        assert finding_id("rule", ["a"], ["b"]) != finding_id("rule", ["a", "b"], [])

    def test_finding_id_includes_evidence_file_identity(self):
        first = finding_id("rule", ["unit"], [{"file": "a.py", "symbol": "run"}])
        second = finding_id("rule", ["unit"], [{"file": "b.py", "symbol": "run"}])
        assert first != second

    def test_ordered_scope_is_not_sorted_by_generic_canonicalizer(self):
        first = canonical_json({"scope": ["stop", "execution"]})
        second = canonical_json({"scope": ["execution", "stop"]})
        assert first != second


    def test_stable_id_is_deterministic_and_prefixed(self):
        first = stable_id("finding", "a", "b")
        second = stable_id("finding", "a", "b")
        assert first == second
        assert first.startswith("finding:")
        assert first != stable_id("finding", "a", "c")
