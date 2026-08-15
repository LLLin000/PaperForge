"""Materialization — per-paper truth across the OCR → retrieval → vector →
serving DAG (ADR-0002, contract
docs/research/2026-08-15-artifact-materialization-state-contract.md).

Each layer answers three questions — facts (what exists), integrity (is it
valid), identity (is it what we expect) — and the caller (probe lineage /
reconcile) finds the FIRST broken frontier.  These are stateless judging
functions; the probe is the truth, nothing is persisted here.
"""

from __future__ import annotations

from .ocr import (  # noqa: F401
    ocr_artifact_detail,
    raw_state,
)
