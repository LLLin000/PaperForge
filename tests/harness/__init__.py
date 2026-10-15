"""CLI-host acceptance harness.

Cases here are **host-agnostic**: they drive the real ``paperforge`` CLI as a
subprocess against a disposable vault and assert observable state (files,
digests, probe envelopes, NDJSON terminals).  They exist because a case that
only needed the CLI was still being proven through real Obsidian + WebDriver —
the slowest, flakiest and least informative runner the project has.

Each case emits a structured evidence record (``runner_kind=harness_cli``), so a
capability can move off the H matrix without losing its evidence binding.  See
``evidence.py`` for the record shape and the project's real-machine verification
standard for the fields it consumes.

Boundary: a case belongs here only when its oracle can be stated from process- or
file-level facts.  Anything whose subject *is* the Obsidian host — vault adapter
and note registration, view rendering, ribbon/settings surfaces, plugin unload
and child reaping, app/installer compatibility — stays in
``paperforge/plugin/test/specs/paperforge.e2e.ts``.
"""

CASE_ID = ""
