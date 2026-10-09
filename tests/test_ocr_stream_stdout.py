"""#137 stream contract: in stream/action mode stdout must stay machine-only.

The ocr.run action's child stdout is parsed as NDJSON by the fail-closed
client parser.  A single human ``print`` in the worker's run path trips it
(observed in the D04 e2e: ``OCR: <key> uploading to PaddleOCR...`` killed
the stream ~15s after submit, so the Stop control had no live operation to
cancel and the paper was left ``running``).  Human diagnostics route to
stderr while ``set_stream_diagnostics(True)`` is active, and stay on stdout
for the plain CLI otherwise.
"""

from __future__ import annotations

import json
from pathlib import Path


def _mark_pending(vault: Path, key: str) -> None:
    """The synthetic vault's paper ships settled; mark it pending so the run
    picks it up.  Its PDF is absent and the keyring is hermetic, so the run
    settles through a human diagnostic without any network call."""
    meta_path = vault / "99_System" / "PaperForge" / "ocr" / key / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["ocr_status"] = "pending"
    meta["ocr_job_id"] = ""
    meta["error"] = ""
    meta_path.write_text(json.dumps(meta), encoding="utf-8")


def _assert_stdout_is_machine_only(stdout: str) -> None:
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            json.loads(line)
        except json.JSONDecodeError as exc:
            raise AssertionError(
                f"human line on stream stdout: {line!r}"
            ) from exc


def test_run_ocr_stream_mode_keeps_stdout_machine_only(test_vault, capsys) -> None:
    from paperforge.worker import ocr as ocr_mod

    _mark_pending(test_vault, "TSTONE001")

    ocr_mod.set_stream_diagnostics(True)
    try:
        ocr_mod.run_ocr(test_vault, selected_keys={"TSTONE001"})
    finally:
        ocr_mod.set_stream_diagnostics(False)

    captured = capsys.readouterr()
    _assert_stdout_is_machine_only(captured.out)
    assert "OCR:" in captured.err, (
        "stream mode must route human diagnostics to stderr"
    )


def test_run_ocr_default_mode_keeps_diagnostics_on_stdout(test_vault, capsys) -> None:
    from paperforge.worker import ocr as ocr_mod

    _mark_pending(test_vault, "TSTONE001")

    ocr_mod.run_ocr(test_vault, selected_keys={"TSTONE001"})

    captured = capsys.readouterr()
    assert "OCR:" in captured.out, (
        "the plain CLI keeps its human diagnostics on stdout"
    )
