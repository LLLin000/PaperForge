"""PaperForge — logging configuration single entry point.

Call ``configure_logging(verbose)`` once at CLI startup before command dispatch.
All worker and command modules use ``logging.getLogger(__name__)`` for
diagnostic/trace/error output.

Environment:
    PAPERFORGE_LOG_LEVEL — default log level (DEBUG/INFO/WARNING/ERROR).
    Invalid values silently fall back to WARNING.
"""

import logging
import os
import sys


def configure_logging(verbose: bool = False) -> None:
    """Configure the root ``paperforge`` logger.

    Sets up a StreamHandler writing to stderr with a ``LEVEL:name:message``
    format string. Idempotent — does nothing if handlers are already
    configured (guards against double ``basicConfig()`` or ``dictConfig()``).

    Args:
        verbose: If True, forces ``DEBUG`` level regardless of env var.
    """
    logger = logging.getLogger("paperforge")

    # Idempotency guard: if handlers already exist, only adjust level.
    # This prevents duplicate log lines from multiple configure_logging calls.
    if logger.handlers:
        if verbose:
            logger.setLevel(logging.DEBUG)
        return

    # Resolve log level from environment or default
    level_name = os.environ.get("PAPERFORGE_LOG_LEVEL", "INFO").strip().upper()
    level = getattr(logging, level_name, None)
    if not isinstance(level, int) or level_name not in ("DEBUG", "INFO", "WARNING", "ERROR"):
        level = logging.WARNING

    if verbose:
        level = logging.DEBUG

    logger.setLevel(level)

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setLevel(logging.DEBUG)  # handler-level always DEBUG; logger controls filtering
    formatter = logging.Formatter(
        fmt="%(levelname)s:%(name)s:%(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def get_paperforge_logger() -> logging.Logger:
    """Convenience accessor for the ``paperforge`` logger.

    Equivalent to ``logging.getLogger("paperforge")`` but provides a single
    well-known reference point for early-boot logging before
    ``configure_logging()`` has been called.

    Callers in worker/command modules should still prefer the per-module
    ``logger = logging.getLogger(__name__)`` pattern. This function exists
    for places (like ``cli.py:main()``) that need the root logger before
    per-module loggers are established.
    """
    return logging.getLogger("paperforge")
