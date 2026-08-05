"""Fixture loading for Architecture Audit (#131).

Fixtures live in `paperforge/architecture_audit/fixtures/*.json` as
`{"contract": {...}, "survey": {...}}` payloads in canonical dict form.

- `synthetic_*.json` — one rule/edge condition per scenario, no repository churn.
- `golden_*.json` — manually curated observed evidence chains for #126, #127,
  #129, recording repository revision and source digests. Issue text supplies
  declared intent only; observed facts come from the source evidence recorded
  in each fixture.
"""
from __future__ import annotations

import json
from importlib import resources
from typing import Any

from paperforge.architecture_audit.layers import (
    ArchitectureContract,
    ArchitectureSurvey,
    validate_contract,
    validate_survey,
)

FIXTURE_NAMES = (
    "synthetic_query_side_effect",
    "synthetic_unmatched_signal",
    "synthetic_ui_canonical_write",
    "synthetic_implicit_remote_followup",
    "synthetic_publication_bypass",
    "synthetic_planned_gap",
    "synthetic_intentional_exception",
    "synthetic_partial_coverage",
    "golden_126_ocr_rebuild",
    "golden_127_sync_embed",
    "golden_129_display_restore",
)


def load_fixture_dict(name: str) -> dict[str, Any]:
    """Load a raw fixture payload as nested dicts."""
    if name not in FIXTURE_NAMES:
        raise KeyError(f"unknown architecture audit fixture: {name!r}")
    base = resources.files("paperforge.architecture_audit").joinpath("fixtures")
    ref = base.joinpath(f"{name}.json")
    with ref.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_fixture(name: str) -> tuple[ArchitectureContract, ArchitectureSurvey]:
    """Load a fixture as validated Contract + Survey layers."""
    payload = load_fixture_dict(name)
    contract = ArchitectureContract.from_dict(payload["contract"])
    survey = ArchitectureSurvey.from_dict(payload["survey"])
    validate_contract(contract)
    validate_survey(survey)
    return contract, survey
