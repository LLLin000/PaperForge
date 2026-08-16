"""M2-D: standardized settlement — summary and successful_keys are derived
from per_key (single truth, no second counts)."""

from __future__ import annotations

from paperforge.core.settlement import settlement_payload, successful_keys


def test_successful_keys_derived_from_per_key():
    pk = {"A": "succeeded", "B": "pending", "C": "succeeded", "D": "failed"}
    assert successful_keys(pk) == ["A", "C"]


def test_summary_derived_from_per_key():
    pk = {"A": "succeeded", "B": "pending", "C": "succeeded", "D": "failed", "E": "noop", "F": "cancelled"}
    payload = settlement_payload(pk)
    assert payload["summary"] == {
        "succeeded": 2,
        "noop": 1,
        "pending": 1,
        "blocked": 0,
        "failed": 1,
        "cancelled": 1,
    }
    assert payload["successful_keys"] == ["A", "C"]


def test_reason_and_execution_ride_along():
    payload = settlement_payload(
        {"A": "pending"},
        reason_codes={"A": "provider.running"},
        execution_ids={"A": "pf-x"},
    )
    assert payload["per_key"]["A"]["reason_code"] == "provider.running"
    assert payload["per_key"]["A"]["execution_id"] == "pf-x"
