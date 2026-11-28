"""Migration state machine and per-file action contract (ADR-018)."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from paperforge.core.io import write_json_atomic


class UpgradePhase(str, Enum):
    """Explicit lifecycle states for transactional vault upgrade."""

    IDLE = "IDLE"
    PREFLIGHT_AUDIT = "PREFLIGHT_AUDIT"
    SNAPSHOT_AND_QUIESCE = "SNAPSHOT_AND_QUIESCE"
    ENGINE_CUTOVER = "ENGINE_CUTOVER"
    DERIVED_VIEW_AND_INDEX_RECONCILE = "DERIVED_VIEW_AND_INDEX_RECONCILE"
    PER_WORKSPACE_PROGRESSIVE_HEAL = "PER_WORKSPACE_PROGRESSIVE_HEAL"
    COMPLETED = "COMPLETED"
    COMPLETED_FAST_CUTOVER = "COMPLETED_FAST_CUTOVER"
    ABORTED_CLEAN = "ABORTED_CLEAN"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    SOVEREIGNTY_VIOLATION = "SOVEREIGNTY_VIOLATION"


class MigrationStateError(RuntimeError):
    """Raised when an illegal upgrade state transition is attempted."""


ALLOWED_TRANSITIONS: dict[UpgradePhase, frozenset[UpgradePhase]] = {
    UpgradePhase.IDLE: frozenset(
        {
            UpgradePhase.PREFLIGHT_AUDIT,
            UpgradePhase.ABORTED_CLEAN,
        }
    ),
    UpgradePhase.PREFLIGHT_AUDIT: frozenset(
        {
            UpgradePhase.SNAPSHOT_AND_QUIESCE,
            UpgradePhase.ABORTED_CLEAN,
            UpgradePhase.SOVEREIGNTY_VIOLATION,
        }
    ),
    UpgradePhase.SNAPSHOT_AND_QUIESCE: frozenset(
        {
            UpgradePhase.ENGINE_CUTOVER,
            UpgradePhase.ABORTED_CLEAN,
            UpgradePhase.ROLLING_BACK,
            UpgradePhase.SOVEREIGNTY_VIOLATION,
        }
    ),
    UpgradePhase.ENGINE_CUTOVER: frozenset(
        {
            UpgradePhase.DERIVED_VIEW_AND_INDEX_RECONCILE,
            UpgradePhase.ROLLING_BACK,
            UpgradePhase.SOVEREIGNTY_VIOLATION,
        }
    ),
    UpgradePhase.DERIVED_VIEW_AND_INDEX_RECONCILE: frozenset(
        {
            UpgradePhase.PER_WORKSPACE_PROGRESSIVE_HEAL,
            UpgradePhase.COMPLETED_FAST_CUTOVER,
            UpgradePhase.COMPLETED,
            UpgradePhase.ROLLING_BACK,
            UpgradePhase.SOVEREIGNTY_VIOLATION,
        }
    ),
    UpgradePhase.PER_WORKSPACE_PROGRESSIVE_HEAL: frozenset(
        {
            UpgradePhase.COMPLETED,
            UpgradePhase.ROLLING_BACK,
            UpgradePhase.SOVEREIGNTY_VIOLATION,
        }
    ),
    UpgradePhase.SOVEREIGNTY_VIOLATION: frozenset(
        {
            UpgradePhase.ROLLING_BACK,
            UpgradePhase.ROLLED_BACK,
        }
    ),
    UpgradePhase.ROLLING_BACK: frozenset(
        {
            UpgradePhase.ROLLED_BACK,
            UpgradePhase.ABORTED_CLEAN,
        }
    ),
    UpgradePhase.COMPLETED: frozenset(),
    UpgradePhase.COMPLETED_FAST_CUTOVER: frozenset(),
    UpgradePhase.ABORTED_CLEAN: frozenset(),
    UpgradePhase.ROLLED_BACK: frozenset(),
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class UpgradeStateMachine:
    """Deterministic finite state machine recording gated vault upgrade transitions."""

    def __init__(self, initial: UpgradePhase = UpgradePhase.IDLE) -> None:
        self._state: UpgradePhase = initial
        self._trace: list[dict[str, Any]] = []

    @property
    def state(self) -> UpgradePhase:
        return self._state

    @property
    def trace(self) -> list[dict[str, Any]]:
        return list(self._trace)

    def transition(
        self,
        target: UpgradePhase,
        gate: str = "",
        detail: Any = None,
    ) -> UpgradePhase:
        """Advance to *target* if permitted by ``ALLOWED_TRANSITIONS``."""
        allowed = ALLOWED_TRANSITIONS.get(self._state, frozenset())
        if target not in allowed:
            raise MigrationStateError(
                f"Illegal upgrade state transition: {self._state.value} -> {target.value} (gate={gate!r})"
            )
        entry: dict[str, Any] = {
            "from": self._state.value,
            "to": target.value,
            "gate": gate,
            "timestamp": _utcnow_iso(),
        }
        if detail is not None:
            entry["detail"] = detail
        self._trace.append(entry)
        self._state = target
        return target

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "trace": list(self._trace),
        }

    def persist(self, path: Path) -> None:
        """Persist state and transition trace atomically."""
        write_json_atomic(path, self.to_dict())


VALID_TIERS: frozenset[str] = frozenset({"tier0", "tier1", "hostile_fs"})
VALID_STAGES: frozenset[str] = frozenset(
    {"PREFLIGHT", "CUTOVER", "RECONCILE", "PROGRESSIVE_HEAL", "NEVER_MUTATE"}
)
MUTATING_STAGES: frozenset[str] = frozenset({"CUTOVER", "RECONCILE", "PROGRESSIVE_HEAL"})
_DESTRUCTIVE_ACTION_TOKENS: frozenset[str] = frozenset({"DELETE", "OVERWRITE", "DROP"})
_FROZEN_ACTIONS: frozenset[str] = frozenset({"UNTOUCHED", "FROZEN_UNTOUCHED"})


@dataclass(frozen=True)
class FileActionRule:
    """Canonical policy row governing one vault file class during upgrade."""

    file_class: str
    tier: str
    stage: str
    action: str
    conflict_policy: str
    rollback_strategy: str


PER_FILE_ACTION_CONTRACT: tuple[FileActionRule, ...] = (
    FileActionRule(
        file_class="user_custom_markdown",
        tier="tier0",
        stage="NEVER_MUTATE",
        action="UNTOUCHED",
        conflict_policy="PRESERVE_IN_PLACE",
        rollback_strategy="NOOP",
    ),
    FileActionRule(
        file_class="paper_main_note",
        tier="tier0",
        stage="PROGRESSIVE_HEAL",
        action="RENAME_WITH_ALIAS_AND_EMBED_REWRITE",
        conflict_policy="SKIP_IF_TARGET_EXISTS",
        rollback_strategy="RESTORE_FROM_BACKUP_AND_REVERSE_RENAME",
    ),
    FileActionRule(
        file_class="ambiguous_or_sync_conflict_notes",
        tier="tier0",
        stage="NEVER_MUTATE",
        action="FROZEN_UNTOUCHED",
        conflict_policy="FREEZE_AND_REPORT",
        rollback_strategy="NOOP",
    ),
    FileActionRule(
        file_class="workspace_sidecars",
        tier="tier0",
        stage="RECONCILE",
        action="READ_ONLY_HYDRATE_TO_DB",
        conflict_policy="SIDECAR_IS_TRUTH",
        rollback_strategy="NOOP",
    ),
    FileActionRule(
        file_class="permanent_logs_jsonl",
        tier="tier0",
        stage="CUTOVER",
        action="MERGE_BY_ID_WITH_BACKUP",
        conflict_policy="BACKUP_BOTH_AND_UNION_BY_ID",
        rollback_strategy="RESTORE_FROM_MOVED_PAIRS_AND_BACKUP",
    ),
    FileActionRule(
        file_class="ocr_raw_result_json",
        tier="tier0",
        stage="CUTOVER",
        action="MOVE_WITH_PREFLIGHT_AND_CHECKSUM",
        conflict_policy="QUARANTINE_DUPLICATE_NEVER_OVERWRITE",
        rollback_strategy="REVERSE_MOVE_FROM_JOURNAL",
    ),
    FileActionRule(
        file_class="sqlite_memory_db",
        tier="tier0",
        stage="CUTOVER",
        action="QUIESCE_WAL_AND_MOVE_RICH_WINS",
        conflict_policy="RICH_WINS_ARCHIVE_LOSER",
        rollback_strategy="REVERSE_MOVE_AND_RESTORE_ARCHIVE",
    ),
    FileActionRule(
        file_class="formal_library_json",
        tier="tier1",
        stage="CUTOVER",
        action="MOVE_RICH_WINS_AND_RECONCILE_PATHS",
        conflict_policy="RICH_WINS_ARCHIVE_LOSER",
        rollback_strategy="RESTORE_PREFLIGHT_SNAPSHOT",
    ),
    FileActionRule(
        file_class="workspace_paper_meta",
        tier="tier1",
        stage="PROGRESSIVE_HEAL",
        action="STRIP_STALE_ENGINE_PATHS",
        conflict_policy="IN_PLACE_ATOMIC_UPDATE",
        rollback_strategy="REBUILD_OR_NOOP",
    ),
    FileActionRule(
        file_class="workspace_fulltext_md",
        tier="tier1",
        stage="PROGRESSIVE_HEAL",
        action="VERIFY_MIRROR_OR_PRESERVE_TRASH",
        conflict_policy="PRESERVE_USER_MODIFIED_IN_TRASH",
        rollback_strategy="RESTORE_FROM_BACKUP_OR_TRASH",
    ),
    FileActionRule(
        file_class="paperforge_owned_base",
        tier="tier1",
        stage="RECONCILE",
        action="BACKUP_AND_UPGRADE_VIEWS",
        conflict_policy="SNAPSHOT_BEFORE_WRITE",
        rollback_strategy="RESTORE_PREFLIGHT_SNAPSHOT",
    ),
    FileActionRule(
        file_class="user_custom_base",
        tier="tier0",
        stage="NEVER_MUTATE",
        action="UNTOUCHED",
        conflict_policy="PRESERVE_IN_PLACE",
        rollback_strategy="NOOP",
    ),
    FileActionRule(
        file_class="user_assets_zotero_secrets",
        tier="tier0",
        stage="NEVER_MUTATE",
        action="UNTOUCHED",
        conflict_policy="NEVER_MOVE_OR_COPY_SECRETS",
        rollback_strategy="NOOP",
    ),
    FileActionRule(
        file_class="verified_legacy_flat_duplicate",
        tier="tier1",
        stage="PROGRESSIVE_HEAL",
        action="QUARANTINE_TO_TRASH",
        conflict_policy="FOUR_GATE_EXACT_MATCH_ONLY",
        rollback_strategy="RESTORE_FROM_TRASH",
    ),
    FileActionRule(
        file_class="hostile_fs_entries",
        tier="hostile_fs",
        stage="NEVER_MUTATE",
        action="SKIP_FAIL_CLOSED",
        conflict_policy="NEVER_TRAVERSE_OR_MOVE",
        rollback_strategy="NOOP",
    ),
)


def audit_file_action_conflicts(
    contract: tuple[FileActionRule, ...] = PER_FILE_ACTION_CONTRACT,
) -> list[str]:
    """Audit *contract* for duplicate classes, destructive Tier-0 rules, or invalid stages."""
    conflicts: list[str] = []
    seen_classes: set[str] = set()
    for rule in contract:
        if rule.file_class in seen_classes:
            conflicts.append(f"duplicate file_class: {rule.file_class}")
        seen_classes.add(rule.file_class)

        if rule.tier not in VALID_TIERS:
            conflicts.append(f"{rule.file_class}: invalid tier {rule.tier!r}")
        if rule.stage not in VALID_STAGES:
            conflicts.append(f"{rule.file_class}: invalid stage {rule.stage!r}")

        action_tokens = {tok for tok in rule.action.upper().split("_") if tok}
        if rule.tier == "tier0" and (action_tokens & _DESTRUCTIVE_ACTION_TOKENS):
            conflicts.append(f"{rule.file_class}: destructive action {rule.action!r} forbidden on tier0")

        if rule.action in _FROZEN_ACTIONS and rule.stage in MUTATING_STAGES:
            conflicts.append(
                f"{rule.file_class}: frozen action {rule.action!r} placed in mutating stage {rule.stage!r}"
            )
    return conflicts


def export_file_contract_summary() -> list[dict[str, str]]:
    """Return a JSON-serializable summary of ``PER_FILE_ACTION_CONTRACT``."""
    return [asdict(rule) for rule in PER_FILE_ACTION_CONTRACT]
