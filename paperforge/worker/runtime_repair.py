"""#174 / #143 runtime lifecycle repair — DISTINCT from literature repair.

`paperforge repair --runtime` is the environment/runtime repair seam:
the pointer-backed runtime must be importable and version-coherent.  When
it is not (e.g. an update failure while the package is still runnable, or
a corrupted pointer), this re-ensures the [vector] dependencies in the
current runtime and re-publishes the pointer.

This is a DIFFERENT operation from the literature/OCR/path-divergence
repair in `paperforge/commands/repair.py` — the two never share code and
never pretend to be each other.
"""

from __future__ import annotations


def perform_runtime_repair(*, ndjson: bool = False) -> dict[str, object]:
    """Runtime lifecycle repair: pointer-backed runtime must import with
    the vector stack; missing/corrupt → re-ensure deps + re-publish pointer.

    Returns a typed dict; ndjson emits the #137 stream (start / phase /
    exactly-one result|error terminal) with cooperative cancellation.
    """
    if ndjson:
        from paperforge.core.cancellation import make_cancellation_token
        from paperforge.core.ndjson import emit_phase, emit_start

        emit_start("foundation.repair")
        _is_stopped, _restore = make_cancellation_token()
    else:
        _is_stopped, _restore = (lambda: False), (lambda: None)

    def _phase(label: str) -> bool:
        if ndjson:
            emit_phase("foundation.repair", phase=label)
        return _is_stopped()

    def _finish(result: dict) -> dict:
        if ndjson:
            from paperforge import __version__ as PF_VERSION
            from paperforge.core.errors import ErrorCode
            from paperforge.core.ndjson import emit_terminal
            from paperforge.core.result import PFError, PFResult

            event = "cancelled" if result.get("cancelled") else (
                "result" if result["ok"] else "error"
            )
            pf = PFResult(
                ok=result["ok"],
                command="repair",
                version=PF_VERSION,
                data={k: v for k, v in result.items() if k not in ("ok", "cancelled")},
                error=(
                    PFError(
                        code=ErrorCode.INTERNAL_ERROR,
                        message=result.get("error", "runtime repair failed"),
                    )
                    if event != "result"
                    else None
                ),
            )
            emit_terminal(event, "foundation.repair", pf)
        return result

    if _phase("check") or _is_stopped():
        return _finish({"ok": False, "cancelled": True})

    from paperforge.runtime_pointer import read_pointer
    from paperforge.setup.runtime import ensure_runtime_dependencies, vector_extras_present

    ptr = read_pointer()
    if ptr is None:
        # No published pointer: nothing to repair at runtime level — the
        # bootstrap must run (install + setup).  Report clearly.
        return _finish({
            "ok": False,
            "pointer": None,
            "error": "no runtime pointer published — run bootstrap install + paperforge setup",
        })

    if _phase("deps") or _is_stopped():
        return _finish({"ok": False, "cancelled": True})

    if not vector_extras_present():
        deps = ensure_runtime_dependencies()
        if not deps.ok:
            return _finish({
                "ok": False,
                "pointer": ptr["paperforge_version"],
                "error": f"dependency re-ensure failed: {deps.message}",
            })

    if _phase("verify") or _is_stopped():
        return _finish({"ok": False, "cancelled": True})

    from paperforge.runtime_pointer import publish_pointer

    publish_pointer(
        python_path=ptr["python_path"],
        environment_root=ptr["environment_root"],
        paperforge_version=ptr["paperforge_version"],
    )
    return _finish({
        "ok": True,
        "pointer": ptr["paperforge_version"],
        "repaired": True,
    })
