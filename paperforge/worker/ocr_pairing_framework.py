from __future__ import annotations

from collections.abc import Sequence


def run_pairing_passes(state, pass_classes: Sequence[type]) -> list:
    reports = []
    for pass_cls in pass_classes:
        reports.append(pass_cls().run(state))
    return reports
