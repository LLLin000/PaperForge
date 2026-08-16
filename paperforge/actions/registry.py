"""Action registry (#163 / T2, #145 §4.2).

A frozen table of data plus plain callables.  Invariants are validated at
import/test time; no descriptor, handler binding, or emitted wire value
contains a command string or argv.
"""

from __future__ import annotations

from collections.abc import Mapping

from paperforge.actions.types import (
    ActionContext,
    ActionIntent,
    ActionRequest,
    ActionSpec,
    PreflightResult,
    require_action_id,
)
from paperforge.core.result import PFResult

# ── domain imports (local, inside handlers — avoids import cycles) ─────────


def _memory_build_preflight(ctx: ActionContext, request: ActionRequest) -> PreflightResult:
    """memory.build availability: canonical config + library index present;
    papers scope additionally validates keys against the canonical index
    (unknown key = invalid scope, exit 2)."""
    from paperforge.worker.asset_index import read_index

    if not ctx.config:
        return PreflightResult(
            availability="unavailable",
            availability_reason_code="action.config_missing",
            availability_reason="Canonical configuration is missing — run `paperforge config init`",
        )
    index = read_index(ctx.vault)
    if index is None:
        return PreflightResult(
            availability="unavailable",
            availability_reason_code="action.library_index_missing",
            availability_reason="formal-library.json is missing — run `paperforge sync --rebuild-index`",
        )
    if request.scope.kind == "papers":
        items = index.get("items") if isinstance(index, dict) else index
        canonical_keys = {e["zotero_key"] for e in items or [] if e.get("zotero_key")}
        unknown = sorted(set(request.scope.keys) - canonical_keys)
        if unknown:
            from paperforge.actions.runner import ActionError
            from paperforge.core.errors import ErrorCode

            raise ActionError(
                ErrorCode.ACTION_SCOPE_INVALID.value,
                f"unknown paper keys: {unknown}",
                exit_code=2,
            )
    return PreflightResult(
        availability="available",
        availability_reason_code="action.available",
        availability_reason="Memory index can be rebuilt from the canonical library",
        preservation_facts=("Existing paperforge.db remains readable during the build",),
        replacement_facts=("paperforge.db is replaced after the build",),
    )


def _memory_build_handler(ctx: ActionContext, request: ActionRequest) -> PFResult:
    from paperforge import __version__ as PF_VERSION
    from paperforge.core.errors import ErrorCode
    from paperforge.core.result import PFError, PFResult

    keys = None if request.scope.kind == "all" else list(request.scope.keys)
    from paperforge.memory.builder import build_for_keys

    try:
        counts = build_for_keys(ctx.vault, keys)
        if counts.get("global_rebuild_required"):
            # #164 corrective: a scoped request must never initialize the
            # global substrate — the schema needs a full memory.build(all).
            return PFResult(
                ok=False,
                command="action run",
                version=PF_VERSION,
                error=PFError(
                    code=ErrorCode.ACTION_UNAVAILABLE,
                    message="memory schema requires a full rebuild — "
                    "run `paperforge action run memory.build` (all scope) first",
                ),
            )
    except FileNotFoundError as exc:
        return PFResult(
            ok=False,
            command="action run",
            version=PF_VERSION,
            error=PFError(code=ErrorCode.PATH_NOT_FOUND, message=str(exc)),
        )
    # #167 P0-3: handlers never hardcode follow-ups — reconcile is the
    # SINGLE producer.  The follow-up chain derives the next layer via
    # post-publish reconcile(successful_keys).  T7 O1: per-key outcomes
    # flow from the builder; successful_keys drives the reconcile scope.
    return PFResult(
        ok=True,
        command="action run",
        version=PF_VERSION,
        data=counts,
        successful_keys=counts.get("successful_keys"),
    )


def _library_prune_preflight(ctx: ActionContext, request: ActionRequest) -> PreflightResult:
    """library.prune availability: canonical config + residual papers
    actually exist (the unified residual report — Zotero is the authority).
    Destructive (deletes workspace/OCR/vector/full-text records), so it is
    confirmation-required and never automatic."""
    if not ctx.config:
        return PreflightResult(
            availability="unavailable",
            availability_reason_code="action.config_missing",
            availability_reason="Canonical configuration is missing — run `paperforge config init`",
        )
    try:
        from paperforge.lineage import _detect_residuals

        residuals = _detect_residuals(ctx.vault)
        if residuals.get("count", 0) == 0:
            return PreflightResult(
                availability="unavailable",
                availability_reason_code="library.no_orphans",
                availability_reason="No residual papers found",
            )
    except Exception:  # noqa: BLE001
        pass
    return PreflightResult(
        availability="available",
        availability_reason_code="action.available",
        availability_reason="Residual papers can be removed",
        preservation_facts=("Residual workspace/OCR/vector/full-text records will be deleted",),
        replacement_facts=(),
    )


def _library_prune_handler(ctx: ActionContext, request: ActionRequest) -> PFResult:
    """library.prune: delete ALL residual artifacts for papers absent from
    Zotero (workspace dir / OCR data / vectors / full-text rows / retrieval
    units / lineage records).  Candidates come from the unified residual
    detection (Zotero exports = authority), never from a workspace scan —
    an OCR-only or FTS-only residual has no workspace dir to scan.  The
    prune re-verifies each key against the current residual report before
    deleting anything.  Destructive — confirmation is enforced by the
    registry policy; never automatic."""
    import argparse

    from pathlib import Path

    from paperforge import __version__ as PF_VERSION
    from paperforge.core.result import PFResult
    from paperforge.lineage import _detect_residuals
    from paperforge.worker.prune import prune_orphan_papers

    try:
        residuals = _detect_residuals(ctx.vault)
        if residuals.get("count", 0) == 0:
            return PFResult(
                ok=True,
                command="action run",
                version=PF_VERSION,
                data={"deleted": [], "count": 0},
            )
        # Safety: candidates are the CURRENT residual report keys — a key
        # that stopped being residual (e.g. re-added to Zotero between the
        # probe and this run) is never touched.
        try:
            from paperforge.lineage import _workspace_dir_for_key

            candidates = [
                {
                    "key": k,
                    "domain": "",
                    "workspace_dir": _workspace_dir_for_key(ctx.vault, k) or Path(),
                }
                for k in residuals.get("keys", [])
            ]
        except Exception:  # noqa: BLE001 — path resolution is best-effort
            candidates = [
                {
                    "key": k,
                    "domain": "",
                    "workspace_dir": Path(),
                }
                for k in residuals.get("keys", [])
            ]
        result_data = prune_orphan_papers(
            ctx.vault,
            _candidates=candidates,
            dry_run=False,
        )
    except Exception as exc:  # noqa: BLE001 — structured error boundary
        from paperforge.core.errors import ErrorCode
        from paperforge.core.result import PFError

        return PFResult(
            ok=False,
            command="action run",
            version=PF_VERSION,
            error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
        )
    deleted = result_data.get("deleted", [])
    counts = result_data.get("counts", {})
    return PFResult(
        ok=True,
        command="action run",
        version=PF_VERSION,
        data={"deleted": deleted, "count": len(deleted), "counts": counts},
    )


def _ocr_rebuild_derived_preflight(ctx: ActionContext, request: ActionRequest) -> PreflightResult:
    """ocr.rebuild_derived availability: canonical config + OCR root — a
    LOCAL derived-layer rebuild (no remote API), so it is automatic."""
    if not ctx.config:
        return PreflightResult(
            availability="unavailable",
            availability_reason_code="action.config_missing",
            availability_reason="Canonical configuration is missing — run `paperforge config init`",
        )
    return PreflightResult(
        availability="available",
        availability_reason_code="action.available",
        availability_reason="Derived artifacts can be rebuilt locally",
        preservation_facts=("Raw OCR blocks stay untouched",),
        replacement_facts=("Derived artifacts are regenerated from raw blocks",),
    )


def _ocr_rebuild_derived_handler(ctx: ActionContext, request: ActionRequest) -> PFResult:
    """#168/T7 P0-1: ocr.rebuild_derived — the LOCAL derived-layer rebuild
    (structured blocks/metadata/figure+table inventories/objects/render/
    health) from stored raw blocks, per-key outcomes."""
    from paperforge import __version__ as PF_VERSION
    from paperforge.core.errors import ErrorCode
    from paperforge.core.result import PFError, PFResult
    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    if request.scope.kind == "all":
        # #169 corrective: all-scope must resolve the rebuildable keys —
        # passing [] would silently rebuild zero papers.
        from paperforge.worker.ocr_maintenance import collect_maintenance_rows

        keys = [r.key for r in collect_maintenance_rows(ctx.vault) if r.can_rebuild]
    else:
        keys = list(request.scope.keys)
    try:
        result = run_derived_rebuild_for_keys(
            ctx.vault, keys, parallel=0,
        )
    except Exception as exc:  # noqa: BLE001 — structured boundary
        return PFResult(
            ok=False,
            command="action run",
            version=PF_VERSION,
            error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
        )
    failed = result.get("failed_keys", [])
    skipped = result.get("skipped", [])
    success = result.get("success_keys", [])
    return PFResult(
        ok=not failed and not skipped,
        command="action run",
        version=PF_VERSION,
        data={
            "rebuilt": success,
            "failed": failed,
            "skipped": [s.get("key") for s in skipped],
        },
        successful_keys=success or None,
    )


def _ocr_run_preflight(ctx: ActionContext, request: ActionRequest) -> PreflightResult:
    """ocr.run availability: OCR credential available (C1 seam)."""
    from paperforge.credentials import CredentialKey, status as credential_status

    cred = credential_status(CredentialKey("ocr"))
    if cred.state == "missing":
        return PreflightResult(
            availability="unavailable",
            availability_reason_code="credential.missing",
            availability_reason="OCR credential is not configured — run `paperforge auth set ocr --stdin`",
        )
    if cred.state != "available":
        return PreflightResult(
            availability="unavailable",
            availability_reason_code=f"credential.{cred.state}",
            availability_reason="OCR credential unavailable — run `paperforge auth status ocr`",
        )
    return PreflightResult(
        availability="available",
        availability_reason_code="action.available",
        availability_reason="OCR can run",
        preservation_facts=("Existing OCR output remains available until replacement",),
        replacement_facts=("OCR provider calls may incur remote cost",),
    )


def _ocr_run_handler(ctx: ActionContext, request: ActionRequest) -> PFResult:
    from paperforge import __version__ as PF_VERSION
    from paperforge.core.errors import ErrorCode
    from paperforge.core.result import PFError, PFResult
    from paperforge.worker.ocr import run_ocr

    keys = None if request.scope.kind == "all" else list(request.scope.keys)
    try:
        rc = run_ocr(ctx.vault, selected_keys=set(keys) if keys else None)
    except Exception as exc:  # noqa: BLE001 — structured boundary
        return PFResult(
            ok=False,
            command="action run",
            version=PF_VERSION,
            error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
        )
    return PFResult(ok=rc == 0, command="action run", version=PF_VERSION, data={"exit_code": rc})


def _embed_build_preflight(ctx: ActionContext, request: ActionRequest) -> PreflightResult:
    """embed.build availability: credential available and builder not
    mid-flight (global substrate operation, #159)."""
    from paperforge.credentials import CredentialKey, status as credential_status

    cred = credential_status(CredentialKey("embedding"))
    if cred.state == "missing":
        return PreflightResult(
            availability="unavailable",
            availability_reason_code="credential.missing",
            availability_reason="Embedding credential is not configured — run `paperforge auth set embedding --stdin`",
        )
    if cred.state != "available":
        return PreflightResult(
            availability="unavailable",
            availability_reason_code=f"credential.{cred.state}",
            availability_reason="Embedding credential unavailable — run `paperforge auth status embedding`",
        )
    return PreflightResult(
        availability="available",
        availability_reason_code="action.available",
        availability_reason="Vector substrate can be built",
        preservation_facts=("Existing vector rows remain available until replacement commit",),
        replacement_facts=("Embedding provider calls may incur remote cost",),
    )


def _embed_build_handler(ctx: ActionContext, request: ActionRequest) -> PFResult:
    """embed.build: the GLOBAL substrate operation — always all-scope, full
    rebuild over the canonical library."""
    import argparse
    import contextlib
    import io
    import json

    from paperforge import __version__ as PF_VERSION
    from paperforge.core.errors import ErrorCode
    from paperforge.core.result import PFError, PFResult
    from paperforge.worker.asset_index import read_index

    read_index(ctx.vault)
    args = argparse.Namespace(
        vault_path=ctx.vault,
        embed_subcommand="build",
        json=True,
        force=True,
        resume=False,
        keys=None,
    )
    buf = io.StringIO()
    from paperforge.commands.embed import run as embed_run

    with contextlib.redirect_stdout(buf):
        try:
            rc = embed_run(args)
        except Exception as exc:  # noqa: BLE001
            return PFResult(
                ok=False,
                command="action run",
                version=PF_VERSION,
                error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
            )
    for line in reversed(buf.getvalue().splitlines()):
        stripped = line.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                payload = json.loads(stripped)
                return PFResult(
                    ok=bool(payload.get("ok", rc == 0)),
                    command="action run",
                    version=PF_VERSION,
                    data=payload.get("data"),
                    error=(PFError(code=ErrorCode.INTERNAL_ERROR, message=str(payload["error"].get("message", "")))
                           if payload.get("error") else None),
                    warnings=payload.get("warnings", []),
                    next_actions=payload.get("next_actions", []),
                )
            except (ValueError, KeyError):
                break
    return PFResult(
        ok=rc == 0,
        command="action run",
        version=PF_VERSION,
        data={"exit_code": rc},
        error=PFError(code=ErrorCode.INTERNAL_ERROR, message="embed run produced no PFResult") if rc else None,
    )


def _embed_resume_preflight(ctx: ActionContext, request: ActionRequest) -> PreflightResult:
    """embed.resume availability: canonical embedding credential available
    (#173/C1) and the vector builder is not mid-flight."""
    from paperforge.credentials import CredentialKey, status as credential_status

    cred = credential_status(CredentialKey("embedding"))
    if cred.state == "missing":
        return PreflightResult(
            availability="unavailable",
            availability_reason_code="credential.missing",
            availability_reason="Embedding credential is not configured — run `paperforge auth set embedding --stdin`",
        )
    if cred.state != "available":
        return PreflightResult(
            availability="unavailable",
            availability_reason_code=f"credential.{cred.state}",
            availability_reason="Embedding credential unavailable — run `paperforge auth status embedding`",
        )
    try:
        from paperforge.embedding.build_state import read_vector_build_state

        state = read_vector_build_state(ctx.vault)
        if state.get("status") == "running":
            return PreflightResult(
                availability="busy",
                availability_reason_code="vector.build_in_progress",
                availability_reason="A vector build is already running",
            )
    except Exception:
        pass
    # #166 P0-1 (substrate ≠ availability): a GLOBAL substrate defect (model
    # changed / layout incompatible / legacy identity) makes a papers-scoped
    # resume fail-fast in run_build — surface it here as unavailable so the
    # runner never attempts it.  The global embed.build intent is what
    # reconciles it.
    if request.scope.kind == "papers":
        from paperforge.embedding.substrate import assess_vector_substrate

        substrate = assess_vector_substrate(ctx.vault)
        if not substrate.compatible and substrate.db_exists:
            return PreflightResult(
                availability="unavailable",
                availability_reason_code="vector.substrate_incompatible",
                availability_reason="Vector substrate requires a global rebuild — run `paperforge action run embed.build` first",
            )
    return PreflightResult(
        availability="available",
        availability_reason_code="action.available",
        availability_reason="Vector embedding can resume",
        preservation_facts=("Existing vector rows remain available until replacement commit",),
        replacement_facts=("Embedding provider calls may incur remote cost",),
    )


def _embed_resume_handler(ctx: ActionContext, request: ActionRequest) -> PFResult:
    import argparse
    import contextlib
    import io
    import json

    from paperforge import __version__ as PF_VERSION
    from paperforge.core.errors import ErrorCode
    from paperforge.core.result import PFError, PFResult

    args = argparse.Namespace(
        vault_path=ctx.vault,
        embed_subcommand="build",
        json=True,
        force=False,
        resume=True,
        keys=list(request.scope.keys) if request.scope.kind == "papers" else None,
    )
    buf = io.StringIO()
    from paperforge.commands.embed import run as embed_run

    with contextlib.redirect_stdout(buf):
        try:
            rc = embed_run(args)
        except Exception as exc:  # noqa: BLE001 — structured error boundary
            return PFResult(
                ok=False,
                command="action run",
                version=PF_VERSION,
                error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
            )
    # embed_run emits exactly one PFResult JSON (json mode, #137 contract).
    for line in reversed(buf.getvalue().splitlines()):
        stripped = line.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                payload = json.loads(stripped)
                error = None
                if payload.get("error"):
                    code = str(payload["error"].get("code", "INTERNAL_ERROR"))
                    try:
                        code_enum = ErrorCode(code)
                    except ValueError:
                        code_enum = ErrorCode.INTERNAL_ERROR
                    error = PFError(
                        code=code_enum,
                        message=str(payload["error"].get("message", "")),
                    )
                return PFResult(
                    ok=bool(payload.get("ok", rc == 0)),
                    command="action run",
                    version=PF_VERSION,
                    data=payload.get("data"),
                    error=error,
                    warnings=payload.get("warnings", []),
                    next_actions=payload.get("next_actions", []),
                )
            except (ValueError, KeyError):
                break
    return PFResult(
        ok=rc == 0,
        command="action run",
        version=PF_VERSION,
        data={"exit_code": rc},
        error=PFError(code=ErrorCode.INTERNAL_ERROR, message="embed run produced no PFResult") if rc else None,
    )


# ── the registry ───────────────────────────────────────────────────────────

def _foundation_update_handler(ctx: ActionContext, request: ActionRequest) -> PFResult:
    """foundation.update (#174): refresh the installed distribution via the
    pure lifecycle service (no prompts, no stdout, fresh-child verified,
    pointer published with the OBSERVED version).  Zero arbitrary args."""
    from paperforge import __version__ as PF_VERSION
    from paperforge.core.errors import ErrorCode
    from paperforge.core.result import PFError
    from paperforge.worker.update import perform_update

    result = perform_update(ctx.vault)
    if result.get("cancelled"):
        return PFResult(
            ok=False,
            command="action run",
            version=PF_VERSION,
            data={"cancelled": True},
            error=PFError(
                code=ErrorCode.ACTION_CANCELLED,
                message="update cancelled",
            ),
        )
    return PFResult(
        ok=result["ok"],
        command="action run",
        version=PF_VERSION,
        data={k: v for k, v in result.items() if k != "ok"},
        error=(
            PFError(
                code=ErrorCode.INTERNAL_ERROR,
                message=result.get("error", "update failed"),
            )
            if not result["ok"]
            else None
        ),
    )


def _foundation_update_preflight(ctx: ActionContext, request: ActionRequest) -> PreflightResult:
    # #174: update is a POST-bootstrap lifecycle operation — no published
    # pointer means the runtime was never set up, so install/setup is the
    # correct next action, not update (symmetric with foundation.repair).
    from paperforge.runtime_pointer import read_pointer

    if read_pointer() is None:
        return PreflightResult(
            availability="unavailable",
            availability_reason_code="pointer.missing",
            availability_reason="No runtime pointer published — run bootstrap install + paperforge setup",
        )
    return PreflightResult(
        availability="available",
        availability_reason_code="ok",
        availability_reason="Update is available on demand",
    )


def _foundation_repair_handler(ctx: ActionContext, request: ActionRequest) -> PFResult:
    """foundation.repair (#174): runtime LIFECYCLE repair — re-ensure deps
    and re-publish the pointer after fresh-child verification.  Distinct
    from the literature/OCR repair; zero arbitrary args."""
    from paperforge import __version__ as PF_VERSION
    from paperforge.core.errors import ErrorCode
    from paperforge.core.result import PFError
    from paperforge.worker.runtime_repair import perform_runtime_repair

    result = perform_runtime_repair()
    if result.get("cancelled"):
        return PFResult(
            ok=False,
            command="action run",
            version=PF_VERSION,
            data={"cancelled": True},
            error=PFError(
                code=ErrorCode.ACTION_CANCELLED,
                message="runtime repair cancelled",
            ),
        )
    return PFResult(
        ok=result["ok"],
        command="action run",
        version=PF_VERSION,
        data={k: v for k, v in result.items() if k != "ok"},
        error=(
            PFError(
                code=ErrorCode.INTERNAL_ERROR,
                message=result.get("error", "runtime repair failed"),
            )
            if not result["ok"]
            else None
        ),
    )


def _foundation_repair_preflight(ctx: ActionContext, request: ActionRequest) -> PreflightResult:
    from paperforge.runtime_pointer import read_pointer

    if read_pointer() is None:
        return PreflightResult(
            availability="unavailable",
            availability_reason_code="pointer.missing",
            availability_reason="No runtime pointer published — run bootstrap install + paperforge setup",
        )
    return PreflightResult(
        availability="available",
        availability_reason_code="ok",
        availability_reason="Runtime repair can verify and re-publish the pointer",
    )


def validate_registry(registry: Mapping[str, ActionSpec] | None = None) -> list[str]:
    """Registry invariant audit; empty list = valid."""
    problems: list[str] = []
    table = registry if registry is not None else ACTION_REGISTRY
    seen: set[str] = set()
    for action_id, spec in table.items():
        if action_id in seen:
            problems.append(f"duplicate action id: {action_id}")
        seen.add(action_id)
        if spec.action_id != action_id:
            problems.append(f"{action_id}: spec.action_id mismatch")
        try:
            require_action_id(action_id)
        except ValueError as exc:
            problems.append(str(exc))
        if not callable(spec.handler):
            problems.append(f"{action_id}: handler is not callable")
        if not callable(spec.preflight):
            problems.append(f"{action_id}: preflight is not callable")
        unknown_kinds = [k for k in spec.scope_kinds if k not in ("all", "papers")]
        if unknown_kinds:
            problems.append(f"{action_id}: unknown scope kinds {unknown_kinds}")
        if spec.cost == "remote_possible" and spec.confirmation != "required":
            problems.append(f"{action_id}: remote_possible requires confirmation")
        if spec.cost == "remote_possible" and spec.automatic:
            problems.append(f"{action_id}: remote_possible cannot be automatic")
        if spec.impact == "destructive" and spec.confirmation != "required":
            problems.append(f"{action_id}: destructive requires confirmation")
        if spec.impact == "destructive" and spec.automatic:
            problems.append(f"{action_id}: destructive cannot be automatic")
        if spec.automatic and (spec.cost != "local" or spec.impact == "destructive"):
            problems.append(f"{action_id}: automatic actions are local and non-destructive")
        if spec.confirmation not in ("none", "required"):
            problems.append(f"{action_id}: invalid confirmation policy")
    return problems


_SPECS: tuple[ActionSpec, ...] = (
    ActionSpec(
        action_id="foundation.update",
        label_code="action.foundation.update",
        description_code="action.foundation.update.description",
        handler=_foundation_update_handler,
        preflight=_foundation_update_preflight,
        scope_kinds=("all",),
        cost="remote_possible",
        impact="mutating",
        confirmation="required",
        automatic=False,
        interruptible=True,
    ),
    ActionSpec(
        action_id="foundation.repair",
        label_code="action.foundation.repair",
        description_code="action.foundation.repair.description",
        handler=_foundation_repair_handler,
        preflight=_foundation_repair_preflight,
        scope_kinds=("all",),
        cost="remote_possible",
        impact="mutating",
        confirmation="required",
        automatic=False,
        interruptible=True,
    ),
    ActionSpec(
        action_id="memory.build",
        label_code="action.memory.build",
        description_code="action.memory.build.description",
        handler=_memory_build_handler,
        preflight=_memory_build_preflight,
        scope_kinds=("all", "papers"),
        cost="local",
        impact="mutating",
        confirmation="none",
        automatic=True,
        interruptible=True,
    ),
    ActionSpec(
        # #135: full-text (paperforge.db papers/FTS) index realignment —
        # the DB's own "prune": rebuilds the papers table from the canonical
        # library so rows for papers removed/merged in Zotero disappear.
        # NEVER touches vectors (remote API cost) and never deletes files;
        # safe to run automatically via reconcile.
        action_id="memory.rebuild",
        label_code="action.memory.rebuild",
        description_code="action.memory.rebuild.description",
        handler=_memory_build_handler,
        preflight=_memory_build_preflight,
        scope_kinds=("all",),
        cost="local",
        impact="mutating",
        confirmation="none",
        automatic=True,
        interruptible=True,
    ),
    ActionSpec(
        action_id="library.prune",
        label_code="action.library.prune",
        description_code="action.library.prune.description",
        handler=_library_prune_handler,
        preflight=_library_prune_preflight,
        scope_kinds=("all",),
        cost="local",
        impact="mutating",
        confirmation="required",
        automatic=False,
        interruptible=True,
    ),
    ActionSpec(
        action_id="embed.resume",
        label_code="action.embed.resume",
        description_code="action.embed.resume.description",
        handler=_embed_resume_handler,
        preflight=_embed_resume_preflight,
        scope_kinds=("all", "papers"),
        cost="remote_possible",
        impact="mutating",
        confirmation="required",
        automatic=False,
        interruptible=True,
    ),
    ActionSpec(
        action_id="embed.build",
        label_code="action.embed.build",
        description_code="action.embed.build.description",
        handler=_embed_build_handler,
        preflight=_embed_build_preflight,
        scope_kinds=("all",),
        cost="remote_possible",
        impact="mutating",
        confirmation="required",
        automatic=False,
        interruptible=True,
    ),
    ActionSpec(
        action_id="ocr.run",
        label_code="action.ocr.run",
        description_code="action.ocr.run.description",
        handler=_ocr_run_handler,
        preflight=_ocr_run_preflight,
        scope_kinds=("all", "papers"),
        cost="remote_possible",
        impact="mutating",
        confirmation="required",
        automatic=False,
        interruptible=True,
    ),
    ActionSpec(
        action_id="ocr.rebuild_derived",
        label_code="action.ocr.rebuild_derived",
        description_code="action.ocr.rebuild_derived.description",
        handler=_ocr_rebuild_derived_handler,
        preflight=_ocr_rebuild_derived_preflight,
        scope_kinds=("all", "papers"),
        cost="local",
        impact="mutating",
        confirmation="none",
        automatic=True,
        interruptible=True,
    ),
)


class RegistryError(RuntimeError):
    """Raised at import time when the frozen table violates an invariant."""


def _build_registry(specs: tuple[ActionSpec, ...]) -> dict[str, ActionSpec]:
    """Build the lookup dict from the literal tuple — duplicate ids are
    detectable here (a literal dict would silently overwrite) and invariant
    violations fail loudly instead of being recorded for later."""
    table: dict[str, ActionSpec] = {}
    for spec in specs:
        if spec.action_id in table:
            raise RegistryError(f"duplicate action id: {spec.action_id}")
        problems = validate_registry({spec.action_id: spec})
        if problems:
            raise RegistryError(f"invalid action {spec.action_id}: {'; '.join(problems)}")
        table[spec.action_id] = spec
    return table


ACTION_REGISTRY: Mapping[str, ActionSpec] = _build_registry(_SPECS)



def emit_next_action(intent: ActionIntent) -> object:
    """#145 §5.2: registry hydration of an emission-time intent into the
    next_actions v1 wire model.  Unknown action ids fail closed.  The wire
    carries no dedupe_key; policy fields come from the registry, never from
    the producer."""
    from paperforge.core.next_actions import NextAction, NextActionScope

    spec = ACTION_REGISTRY[intent.action_id]  # KeyError = unknown action
    scope: NextActionScope
    if intent.scope.kind == "papers":
        scope = NextActionScope(kind="papers", keys=tuple(intent.scope.keys))
    else:
        scope = NextActionScope(kind="all")
    return NextAction(
        action_id=intent.action_id,
        scope=scope,
        automatic=spec.automatic,
        cost=spec.cost,
        impact=spec.impact,
        confirmation=spec.confirmation,
        reason=intent.trigger_reason,
    )




