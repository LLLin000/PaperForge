"""Ticket 06 corrective B: real CLI parser regression for render wire.

The thin client must speak the parser's actual grammar. `render reconcile`
takes POSITIONAL keys — a `--keys` flag never existed and would fail argparse
on the first real user click.
"""

from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "argv, expected_keys",
    [
        (["render", "reconcile", "ABCD1234", "--json"], ["ABCD1234"]),
        (["render", "reconcile", "K1", "K2", "--json"], ["K1", "K2"]),
        (["render", "reconcile", "--json"], []),
    ],
)
def test_render_reconcile_takes_positional_keys(
    argv: list[str], expected_keys: list[str]
) -> None:
    from paperforge.cli import build_parser

    args = build_parser().parse_args(argv)
    assert args.render_subcommand == "reconcile"
    assert list(args.keys) == expected_keys
    assert args.json is True


def test_render_reconcile_rejects_keys_flag() -> None:
    """`--keys` was never a valid option — the client must not send it."""
    from paperforge.cli import build_parser
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            ["render", "reconcile", "--keys", "ABCD1234", "--json"]
        )
