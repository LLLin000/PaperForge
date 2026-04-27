from __future__ import annotations

import sys
from typing import Any

from tqdm import tqdm


def progress_bar(iterable, desc: str = "", total: int | None = None, disable: bool = False) -> Any:
    return tqdm(
        iterable,
        desc=desc,
        total=total,
        disable=disable,
        file=sys.stderr,
        unit="item",
        mininterval=1.0,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
    )
