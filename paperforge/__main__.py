"""paperforge.__main__ — entry point for `python -m paperforge`."""

import sys

from paperforge.cli import main

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
