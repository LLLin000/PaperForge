"""paperforge.__main__ — entry point for `python -m paperforge`."""

import sys
import traceback

from paperforge.cli import main

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 — transport contract: never rc 0 silently
        # CLI transport contract (#130 review P0): an unhandled exception must
        # never surface as "exit 0 with empty/non-JSON stdout" — machine
        # callers (plugin, agent, probe, automation) treat rc 0 as success.
        traceback.print_exc(file=sys.stderr)
        print(f"Error: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
