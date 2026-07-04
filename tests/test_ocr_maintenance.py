"""Tests for OCR maintenance display fields and manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


# ===========================================================================
# _compute_display_fields — pure function tests
# ===========================================================================


def _call(status: str, health: str = "-", version: str = "-",
          can_redo: bool = False, can_rebuild: bool = False,
          error_stage: str = "", error_summary: str = "",
          degraded_reasons: list[str] | None = None) -> dict:
    from paperforge.worker.ocr_maintenance import _compute_display_fields
    return _compute_display_fields(
        status=status, health_overall=health, version=version,
        can_redo=can_redo, can_rebuild=can_rebuild,
        error_stage=error_stage, error_summary=error_summary,
        degraded_reasons=degraded_reasons,
    )


def _assert(df: dict, *, action: str, label: str, group: str, severity: str,
            visible: bool, reason: str = "",
            label_key: str = "", reason_key: str = "") -> None:
    assert df["display_action"] == action, f"action: {df['display_action']} != {action}"
    assert df["display_label"] == label, f"label: {df['display_label']} != {label}"
    assert df["display_label_key"] == label_key
    assert df["display_group"] == group, f"group: {df['display_group']} != {group}"
    assert df["display_severity"] == severity
    assert df["visible_in_maintenance"] == visible, f"visible: {df['visible_in_maintenance']} != {visible}"
    assert df["display_reason"] == reason, f"reason: {df['display_reason']!r} != {reason!r}"
    assert df["display_reason_key"] == reason_key


# --- Rule 3: failed / error / fatal / done_incomplete / retryable_error + can_redo ---

class TestRule3FailedErrorCanRedo:
    """status in (failed, error, fatal_error, done_incomplete, retryable_error) + can_redo"""

    def test_failed_can_redo(self) -> None:
        df = _call(status="failed", can_redo=True)
        _assert(df, action="retry_ocr", label="重试 OCR", group="retry",
                severity="actionable", visible=True,
                reason="上次处理未完成，可以重新尝试",
                label_key="maintenance_action_retry_ocr",
                reason_key="maintenance_reason_retry")

    def test_error_can_redo(self) -> None:
        df = _call(status="error", can_redo=True)
        _assert(df, action="retry_ocr", label="重试 OCR", group="retry",
                severity="actionable", visible=True,
                reason="上次处理未完成，可以重新尝试",
                label_key="maintenance_action_retry_ocr",
                reason_key="maintenance_reason_retry")

    def test_fatal_error_can_redo(self) -> None:
        df = _call(status="fatal_error", can_redo=True)
        _assert(df, action="retry_ocr", label="重试 OCR", group="retry",
                severity="actionable", visible=True,
                reason="上次处理未完成，可以重新尝试",
                label_key="maintenance_action_retry_ocr",
                reason_key="maintenance_reason_retry")

    def test_done_incomplete_can_redo(self) -> None:
        df = _call(status="done_incomplete", can_redo=True)
        _assert(df, action="retry_ocr", label="重试 OCR", group="retry",
                severity="actionable", visible=True,
                reason="上次处理未完成，可以重新尝试",
                label_key="maintenance_action_retry_ocr",
                reason_key="maintenance_reason_retry")

    def test_retryable_error_can_redo(self) -> None:
        df = _call(status="retryable_error", can_redo=True)
        _assert(df, action="retry_ocr", label="重试 OCR", group="retry",
                severity="actionable", visible=True,
                reason="上次处理未完成，可以重新尝试",
                label_key="maintenance_action_retry_ocr",
                reason_key="maintenance_reason_retry")


# --- Rule 4: version=v1 + can_redo ---

class TestRule4LegacyUpgrade:
    def test_v1_can_redo(self) -> None:
        df = _call(status="done", health="-", version="v1", can_redo=True)
        _assert(df, action="upgrade_legacy", label="升级旧结果", group="legacy_optional",
                severity="optional", visible=True,
                reason="旧版本结果仍然可用，升级后可获得更好的章节、图表和问答效果",
                label_key="maintenance_action_upgrade_legacy",
                reason_key="maintenance_reason_legacy")

    def test_v1_no_redo_falls_through(self) -> None:
        # v1 but can't redo: rule 4 fails, should hit fallback (rule 12)
        df = _call(status="done", health="-", version="v1", can_redo=False)
        _assert(df, action="none", label="已完成", group="hidden",
                severity="normal", visible=False)


# --- Rule 5: done_degraded + can_rebuild ---

class TestRule5DoneDegradedCanRebuild:
    def test_done_degraded_can_rebuild(self) -> None:
        df = _call(status="done_degraded", can_rebuild=True)
        _assert(df, action="rebuild_result", label="重建结果", group="rebuild",
                severity="actionable", visible=True,
                reason="已有OCR数据，可重建获得更稳定的结果")


# --- Rule 6: done + health bad (red/yellow) + can_rebuild ---

class TestRule6DoneBadHealthCanRebuild:
    def test_done_red_can_rebuild(self) -> None:
        df = _call(status="done", health="red", can_rebuild=True)
        _assert(df, action="rebuild_result", label="重建结果", group="rebuild",
                severity="actionable", visible=True,
                reason="已有OCR数据，可重建获得更稳定的结果")

    def test_done_yellow_can_rebuild(self) -> None:
        df = _call(status="done", health="yellow", can_rebuild=True)
        _assert(df, action="rebuild_result", label="重建结果", group="rebuild",
                severity="actionable", visible=True,
                reason="已有OCR数据，可重建获得更稳定的结果")


# --- Rule 10: done + health NOT bad ---

class TestRule10DoneNotBadHealth:
    """health_overall NOT in {yellow, red} → hidden complete, unless v1 catches first."""

    def test_done_dash_health_can_rebuild(self) -> None:
        # "-" is not yellow/red, not v1 → rule 10
        df = _call(status="done", health="-", can_rebuild=True)
        _assert(df, action="none", label="已完成", group="hidden",
                severity="normal", visible=False)

    def test_done_unknown_health_can_rebuild(self) -> None:
        df = _call(status="done", health="unknown", can_rebuild=True)
        _assert(df, action="none", label="已完成", group="hidden",
                severity="normal", visible=False)

    def test_done_green_can_rebuild(self) -> None:
        df = _call(status="done", health="green", can_rebuild=True)
        _assert(df, action="none", label="已完成", group="hidden",
                severity="normal", visible=False)

    def test_done_green_no_capabilities(self) -> None:
        # done + green + no redo + no rebuild → rule 10 (not bad health) or rule 11
        # Rule 10 matches first: done and not _health_is_bad
        df = _call(status="done", health="green")
        _assert(df, action="none", label="已完成", group="hidden",
                severity="normal", visible=False)


# --- Rule 7: done_degraded + !can_rebuild + can_redo ---

class TestRule7DoneDegradedNoRebuildCanRedo:
    def test_done_degraded_no_rebuild_can_redo(self) -> None:
        df = _call(status="done_degraded", can_redo=True, can_rebuild=False)
        _assert(df, action="retry_ocr", label="重试 OCR", group="retry",
                severity="actionable", visible=True,
                reason="降级结果无法重建，可重新OCR")


# --- Rule 11: fallback when nothing actionable ---

class TestRule11NoAction:
    def test_done_degraded_no_rebuild_no_redo(self) -> None:
        df = _call(status="done_degraded", can_rebuild=False, can_redo=False)
        _assert(df, action="none", label="已完成", group="hidden",
                severity="normal", visible=False)

    def test_done_red_no_rebuild_no_redo(self) -> None:
        df = _call(status="done", health="red", can_rebuild=False, can_redo=False)
        _assert(df, action="none", label="已完成", group="hidden",
                severity="normal", visible=False)

    def test_done_red_no_rebuild_no_redo_with_error(self) -> None:
        # error_stage/error_summary should not affect fallback
        df = _call(status="done", health="red", can_rebuild=False, can_redo=False,
                   error_stage="ocr_parse", error_summary="TimeoutError: timeout")
        _assert(df, action="none", label="已完成", group="hidden",
                severity="normal", visible=False)


# --- Rule 8: nopdf ---

class TestRule8NoPdf:
    def test_nopdf(self) -> None:
        df = _call(status="nopdf")
        _assert(df, action="add_pdf", label="补充 PDF", group="external_action",
                severity="external", visible=False,
                reason="请去 Zotero 添加 PDF 文件")


# --- Rule 9: blocked ---

class TestRule9Blocked:
    def test_blocked(self) -> None:
        df = _call(status="blocked")
        _assert(df, action="configure_ocr", label="配置 OCR", group="external_action",
                severity="external", visible=False,
                reason="请配置 PaddleOCR API Token")


# --- Rule 1: pending ---

class TestRule1Pending:
    def test_pending(self) -> None:
        df = _call(status="pending")
        _assert(df, action="none", label="等待处理", group="hidden",
                severity="normal", visible=False)


# --- Rule 2: running/queued/processing ---

class TestRule2Running:
    def test_running(self) -> None:
        df = _call(status="running")
        _assert(df, action="none", label="处理中", group="hidden",
                severity="normal", visible=False)

    def test_queued(self) -> None:
        df = _call(status="queued")
        _assert(df, action="none", label="处理中", group="hidden",
                severity="normal", visible=False)

    def test_processing(self) -> None:
        df = _call(status="processing")
        _assert(df, action="none", label="处理中", group="hidden",
                severity="normal", visible=False)


# --- Rule 12: fallback for unrecognised status ---

class TestRule12Fallback:
    def test_unknown_status(self) -> None:
        df = _call(status="bogus_status")
        _assert(df, action="none", label="已完成", group="hidden",
                severity="normal", visible=False)


# ===========================================================================
# Scenario 17: display_reason does NOT contain forbidden substrings
# ===========================================================================

FORBIDDEN = ("failed", "degraded", "health", "质量降级", "fatal", "error")

class TestDisplayReasonCleanliness:
    """display_reason values must never contain leaky technical keywords."""

    def _assert_clean(self, reason: str) -> None:
        for token in FORBIDDEN:
            assert token not in reason, f"display_reason contains forbidden token {token!r}: {reason!r}"

    def test_failed_reason_clean(self) -> None:
        df = _call(status="failed", can_redo=True)
        self._assert_clean(df["display_reason"])

    def test_done_degraded_rebuild_reason_clean(self) -> None:
        df = _call(status="done_degraded", can_rebuild=True)
        self._assert_clean(df["display_reason"])

    def test_done_red_rebuild_reason_clean(self) -> None:
        df = _call(status="done", health="red", can_rebuild=True)
        self._assert_clean(df["display_reason"])

    def test_legacy_upgrade_reason_clean(self) -> None:
        df = _call(status="done", version="v1", can_redo=True)
        self._assert_clean(df["display_reason"])

    def test_degraded_no_rebuild_can_redo_clean(self) -> None:
        df = _call(status="done_degraded", can_redo=True, can_rebuild=False)
        self._assert_clean(df["display_reason"])

    def test_nopdf_reason_clean(self) -> None:
        df = _call(status="nopdf")
        self._assert_clean(df["display_reason"])

    def test_blocked_reason_clean(self) -> None:
        df = _call(status="blocked")
        self._assert_clean(df["display_reason"])


# ===========================================================================
# compute_maintenance_manifest — temp vault tests
# ===========================================================================


def _ocr_path(tmp_path: Path) -> Path:
    """Return the OCR root within a temp vault."""
    return tmp_path / "System" / "PaperForge" / "ocr"


def _create_paper(vault_root: Path, key: str, *,
                  ocr_status: str = "done",
                  health_overall: str = "green",
                  version: str | None = None,
                  error_stage: str = "",
                  error_type: str = "",
                  error_msg: str = "",
                  last_error: str = "",
                  is_backfilled: bool = False,
                  raw_version: bool = False,
                  derived_version: bool = False,
                  degraded_reasons: list[str] | None = None,
                  has_raw: bool = True,
                  has_source_meta: bool = True,
                  has_structured: bool = True,
                  ) -> None:
    """Set up one paper's OCR artifacts so compute_maintenance_manifest can read them."""
    import shutil
    ocr_root = _ocr_path(vault_root)
    paper_dir = ocr_root / key
    # Clean any previous artifacts so file removal is respected
    if paper_dir.exists():
        shutil.rmtree(paper_dir)
    paper_dir.mkdir(parents=True)

    meta: dict = {"ocr_status": ocr_status}
    if error_stage:
        meta["error_stage"] = error_stage
    if error_type:
        meta["error_type"] = error_type
    if error_msg:
        meta["error"] = error_msg
    if last_error:
        meta["last_error"] = last_error
    if is_backfilled:
        meta["is_backfilled"] = True
    if raw_version:
        meta["raw_version"] = {"ocr_model": "test-model"}
    if derived_version:
        meta["derived_version"] = {"version": "2.0"}

    (paper_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    health_dir = paper_dir / "health"
    health_dir.mkdir(parents=True, exist_ok=True)
    health: dict = {"overall": health_overall}
    if degraded_reasons:
        health["degraded_reasons"] = degraded_reasons
    (health_dir / "ocr_health.json").write_text(json.dumps(health), encoding="utf-8")

    # Create artifact files to control has_raw, has_source_meta, has_structured
    if has_raw:
        (paper_dir / "canonical").mkdir(parents=True, exist_ok=True)
        (paper_dir / "canonical" / "blocks.raw.jsonl").write_text("", encoding="utf-8")
    if has_source_meta:
        (paper_dir / "raw").mkdir(parents=True, exist_ok=True)
        (paper_dir / "raw" / "source_metadata.json").write_text("{}", encoding="utf-8")
    if has_structured:
        (paper_dir / "structure").mkdir(parents=True, exist_ok=True)
        (paper_dir / "structure" / "blocks.structured.jsonl").write_text("", encoding="utf-8")


class TestComputeMaintenanceManifest:
    """Integration tests against a temp vault."""

    def test_empty_vault_returns_empty(self, tmp_path: Path) -> None:
        from paperforge.worker.ocr_maintenance import compute_maintenance_manifest
        result = compute_maintenance_manifest(tmp_path)
        assert result == {}

    def test_single_paper(self, tmp_path: Path) -> None:
        _create_paper(tmp_path, "ABC123")
        from paperforge.worker.ocr_maintenance import compute_maintenance_manifest
        result = compute_maintenance_manifest(tmp_path)
        assert isinstance(result, dict)
        assert len(result) == 1
        assert "ABC123" in result
        assert isinstance(result["ABC123"], str)
        assert len(result["ABC123"]) == 64  # sha256 hexdigest

    def test_two_papers(self, tmp_path: Path) -> None:
        _create_paper(tmp_path, "AAA001", ocr_status="done", health_overall="green")
        _create_paper(tmp_path, "BBB002", ocr_status="failed", health_overall="red")
        from paperforge.worker.ocr_maintenance import compute_maintenance_manifest
        result = compute_maintenance_manifest(tmp_path)
        assert len(result) == 2
        assert "AAA001" in result
        assert "BBB002" in result

    def test_no_ocr_dir_returns_empty(self, tmp_path: Path) -> None:
        # Don't create the ocr directory
        from paperforge.worker.ocr_maintenance import compute_maintenance_manifest
        result = compute_maintenance_manifest(tmp_path)
        assert result == {}

    def test_paper_without_meta_json(self, tmp_path: Path) -> None:
        # Create ocr dir but no meta.json
        ocr_root = _ocr_path(tmp_path)
        paper_dir = ocr_root / "MISSING"
        paper_dir.mkdir(parents=True)
        from paperforge.worker.ocr_maintenance import compute_maintenance_manifest
        result = compute_maintenance_manifest(tmp_path)
        # Paper dir exists but no meta.json → should still appear (empty meta)
        assert "MISSING" in result
        assert len(result) == 1

    def test_manifest_hash_consistency(self, tmp_path: Path) -> None:
        """Same input → same hash."""
        _create_paper(tmp_path, "CONSISTENT", ocr_status="done", health_overall="green")
        from paperforge.worker.ocr_maintenance import compute_maintenance_manifest
        h1 = compute_maintenance_manifest(tmp_path)["CONSISTENT"]
        h2 = compute_maintenance_manifest(tmp_path)["CONSISTENT"]
        assert h1 == h2

    def test_manifest_hash_sensitivity_diff_status(self, tmp_path: Path) -> None:
        """Different status → different hash."""
        _create_paper(tmp_path, "SENSITIVE", ocr_status="done", health_overall="green")
        from paperforge.worker.ocr_maintenance import compute_maintenance_manifest
        h_done = compute_maintenance_manifest(tmp_path)["SENSITIVE"]

        # Same key but different status
        _create_paper(tmp_path, "SENSITIVE", ocr_status="failed", health_overall="green")
        h_failed = compute_maintenance_manifest(tmp_path)["SENSITIVE"]
        assert h_done != h_failed

    def test_manifest_hash_sensitivity_diff_health(self, tmp_path: Path) -> None:
        """Different health → different hash."""
        _create_paper(tmp_path, "SENSITIVE", ocr_status="done", health_overall="green")
        from paperforge.worker.ocr_maintenance import compute_maintenance_manifest
        h_green = compute_maintenance_manifest(tmp_path)["SENSITIVE"]

        _create_paper(tmp_path, "SENSITIVE", ocr_status="done", health_overall="red")
        h_red = compute_maintenance_manifest(tmp_path)["SENSITIVE"]
        assert h_green != h_red

    def test_manifest_hash_sensitivity_diff_raw_presence(self, tmp_path: Path) -> None:
        """Different has_raw → different hash (affects can_rebuild)."""
        _create_paper(tmp_path, "SENSITIVE", ocr_status="done", health_overall="green",
                      has_raw=True)
        from paperforge.worker.ocr_maintenance import compute_maintenance_manifest
        h_with_raw = compute_maintenance_manifest(tmp_path)["SENSITIVE"]

        _create_paper(tmp_path, "SENSITIVE", ocr_status="done", health_overall="green",
                      has_raw=False)
        h_no_raw = compute_maintenance_manifest(tmp_path)["SENSITIVE"]
        assert h_with_raw != h_no_raw

    def test_manifest_excludes_non_directories(self, tmp_path: Path) -> None:
        """Files in ocr root should be ignored."""
        ocr_root = _ocr_path(tmp_path)
        ocr_root.mkdir(parents=True)
        (ocr_root / "not_a_dir.json").write_text("{}", encoding="utf-8")

        _create_paper(tmp_path, "REALKEY")
        from paperforge.worker.ocr_maintenance import compute_maintenance_manifest
        result = compute_maintenance_manifest(tmp_path)
        assert "not_a_dir.json" not in result
        assert "REALKEY" in result
        assert len(result) == 1

    def test_manifest_hash_includes_degraded_reasons(self, tmp_path: Path) -> None:
        """Different degraded_reasons → different hash."""
        _create_paper(tmp_path, "SENSITIVE", ocr_status="done", health_overall="yellow",
                      degraded_reasons=["low_confidence"])
        from paperforge.worker.ocr_maintenance import compute_maintenance_manifest
        h_with_degraded = compute_maintenance_manifest(tmp_path)["SENSITIVE"]

        _create_paper(tmp_path, "SENSITIVE", ocr_status="done", health_overall="yellow",
                      degraded_reasons=[])
        h_no_reasons = compute_maintenance_manifest(tmp_path)["SENSITIVE"]
        assert h_with_degraded != h_no_reasons


class TestCollectMaintenanceRowsDisplayFields:
    """End-to-end: collect_maintenance_rows includes display fields."""

    def test_row_has_display_fields(self, tmp_path: Path) -> None:
        from paperforge.worker.ocr_maintenance import collect_maintenance_rows
        _create_paper(tmp_path, "DISPLAY01", ocr_status="failed", health_overall="-")
        rows = collect_maintenance_rows(tmp_path)
        assert len(rows) == 1
        row = rows[0]
        # Should detect failed → retry_ocr
        assert row.display_action == "retry_ocr"
        assert row.visible_in_maintenance is True
        assert row.display_group == "retry"

    def test_to_dict_includes_display_fields(self, tmp_path: Path) -> None:
        from paperforge.worker.ocr_maintenance import collect_maintenance_rows
        _create_paper(tmp_path, "DICT01", ocr_status="failed", health_overall="-")
        rows = collect_maintenance_rows(tmp_path)
        d = rows[0].to_dict()
        assert "display_action" in d
        assert "display_label" in d
        assert "display_label_key" in d
        assert "display_reason" in d
        assert "display_reason_key" in d
        assert "display_group" in d
        assert "display_severity" in d
        assert "visible_in_maintenance" in d


# ===========================================================================
# PR B: CLI — _run_ocr_list with manifest/keys, _run_ocr_redo with keys
# ===========================================================================


class TestOcrListManifest:
    """_run_ocr_list with manifest=True."""

    def test_manifest_flag_calls_compute_maintenance_manifest(
        self, monkeypatch, capsys
    ) -> None:
        import json as _json
        from paperforge.commands.ocr import _run_ocr_list

        manifest_data = {"KEY1": "abc123", "KEY2": "def456"}
        monkeypatch.setattr(
            "paperforge.worker.ocr_maintenance.compute_maintenance_manifest",
            lambda vault: manifest_data,
        )

        result = _run_ocr_list(Path("/fake"), manifest=True)
        captured = capsys.readouterr()
        assert result == 0
        assert _json.loads(captured.out) == manifest_data

    def test_manifest_does_not_call_collect_maintenance_rows(
        self, monkeypatch
    ) -> None:
        from paperforge.commands.ocr import _run_ocr_list

        def _raise(*args, **kwargs):
            raise RuntimeError("collect_maintenance_rows should not be called")

        monkeypatch.setattr(
            "paperforge.worker.ocr_maintenance.collect_maintenance_rows",
            _raise,
        )
        monkeypatch.setattr(
            "paperforge.worker.ocr_maintenance.compute_maintenance_manifest",
            lambda vault: {},
        )

        result = _run_ocr_list(Path("/fake"), manifest=True)
        assert result == 0


class TestOcrListKeys:
    """_run_ocr_list with keys filter."""

    @staticmethod
    def _make_row(key: str) -> "OCRMaintenanceRow":
        from paperforge.worker.ocr_maintenance import OCRMaintenanceRow

        return OCRMaintenanceRow(
            key=key,
            title=f"Paper {key}",
            title_full=f"Paper {key} Full",
            status="done",
            health="green",
            version="2.0",
            finished_at="-",
            rebuild_finished_at="-",
            pages=5,
            blocks=100,
            figures=2,
            tables=1,
            model="test",
            degraded_reasons=[],
            error_summary="",
            error_stage="",
            can_redo=False,
            can_rebuild=True,
            recommended_action="",
        )

    def test_keys_flag_filters_by_key(self, monkeypatch, capsys) -> None:
        import json as _json
        from paperforge.commands.ocr import _run_ocr_list

        rows = [self._make_row("KEY1"), self._make_row("KEY2"), self._make_row("KEY3")]
        monkeypatch.setattr(
            "paperforge.worker.ocr_maintenance.collect_maintenance_rows",
            lambda vault: rows,
        )

        result = _run_ocr_list(Path("/fake"), json_output=True, keys=["KEY1"])
        captured = capsys.readouterr()
        assert result == 0
        data = _json.loads(captured.out)
        assert len(data) == 1
        assert data[0]["key"] == "KEY1"

    def test_keys_none_returns_all(self, monkeypatch, capsys) -> None:
        import json as _json
        from paperforge.commands.ocr import _run_ocr_list

        rows = [self._make_row("KEY1"), self._make_row("KEY2")]
        monkeypatch.setattr(
            "paperforge.worker.ocr_maintenance.collect_maintenance_rows",
            lambda vault: rows,
        )

        result = _run_ocr_list(Path("/fake"), json_output=True, keys=None)
        captured = capsys.readouterr()
        assert result == 0
        data = _json.loads(captured.out)
        assert len(data) == 2
        assert data[0]["key"] == "KEY1"
        assert data[1]["key"] == "KEY2"

    def test_keys_unknown_key_ignored(self, monkeypatch, capsys) -> None:
        import json as _json
        from paperforge.commands.ocr import _run_ocr_list

        rows = [self._make_row("KEY1"), self._make_row("KEY2")]
        monkeypatch.setattr(
            "paperforge.worker.ocr_maintenance.collect_maintenance_rows",
            lambda vault: rows,
        )

        result = _run_ocr_list(Path("/fake"), json_output=True, keys=["UNKNOWN"])
        captured = capsys.readouterr()
        assert result == 0
        data = _json.loads(captured.out)
        assert len(data) == 0


class TestOcrRedoKeyed:
    """_run_ocr_redo with keys parameter."""

    def test_redo_single_key(self, tmp_path) -> None:
        from paperforge.commands.ocr import _run_ocr_redo

        ocr_root = _ocr_path(tmp_path)
        (ocr_root / "KEY1").mkdir(parents=True)
        meta = {"zotero_key": "KEY1", "ocr_status": "done", "ocr_job_id": "job-123"}
        (ocr_root / "KEY1" / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

        result = _run_ocr_redo(tmp_path, keys=["KEY1"])
        assert result == 0
        reloaded = json.loads(
            (ocr_root / "KEY1" / "meta.json").read_text(encoding="utf-8")
        )
        assert reloaded["ocr_status"] == "pending"
        assert reloaded["ocr_job_id"] == ""

    def test_redo_multiple_keys(self, tmp_path) -> None:
        from paperforge.commands.ocr import _run_ocr_redo

        ocr_root = _ocr_path(tmp_path)
        for key in ["KEY1", "KEY2"]:
            (ocr_root / key).mkdir(parents=True)
            meta = {"zotero_key": key, "ocr_status": "done", "ocr_job_id": f"job-{key}"}
            (ocr_root / key / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

        result = _run_ocr_redo(tmp_path, keys=["KEY1", "KEY2"])
        assert result == 0
        for key in ["KEY1", "KEY2"]:
            reloaded = json.loads(
                (ocr_root / key / "meta.json").read_text(encoding="utf-8")
            )
            assert reloaded["ocr_status"] == "pending"
            assert reloaded["ocr_job_id"] == ""

    def test_redo_dry_run(self, tmp_path) -> None:
        from paperforge.commands.ocr import _run_ocr_redo

        ocr_root = _ocr_path(tmp_path)
        (ocr_root / "KEY1").mkdir(parents=True)
        meta = {"zotero_key": "KEY1", "ocr_status": "done", "ocr_job_id": "job-123"}
        meta_path = ocr_root / "KEY1" / "meta.json"
        meta_path.write_text(json.dumps(meta), encoding="utf-8")

        _run_ocr_redo(tmp_path, keys=["KEY1"], dry_run=True)

        reloaded = json.loads(meta_path.read_text(encoding="utf-8"))
        assert reloaded["ocr_status"] == "done"
        assert reloaded["ocr_job_id"] == "job-123"

    def test_redo_no_keys_falls_back(self, monkeypatch) -> None:
        from paperforge.commands.ocr import _run_ocr_redo

        call_kwargs = {}

        def mock_redo(vault, **kwargs):
            call_kwargs.update(kwargs)
            call_kwargs["vault"] = vault
            return 0

        monkeypatch.setattr(
            "paperforge.worker.ocr.ocr_redo_papers",
            mock_redo,
        )

        result = _run_ocr_redo(Path("/fake"), keys=None, verbose=True)
        assert result == 0
        assert call_kwargs.get("vault") == Path("/fake")
        assert call_kwargs.get("dry_run") is False
        assert call_kwargs.get("verbose") is True

    def test_redo_skips_nopdf(self, tmp_path) -> None:
        from paperforge.commands.ocr import _run_ocr_redo

        ocr_root = _ocr_path(tmp_path)

        (ocr_root / "NOPDF").mkdir(parents=True)
        (ocr_root / "NOPDF" / "meta.json").write_text(
            json.dumps({"zotero_key": "NOPDF", "ocr_status": "nopdf"}),
            encoding="utf-8",
        )
        (ocr_root / "KEY1").mkdir(parents=True)
        (ocr_root / "KEY1" / "meta.json").write_text(
            json.dumps({"zotero_key": "KEY1", "ocr_status": "done", "ocr_job_id": "job-123"}),
            encoding="utf-8",
        )

        _run_ocr_redo(tmp_path, keys=["NOPDF", "KEY1"])

        nopdf_meta = json.loads(
            (ocr_root / "NOPDF" / "meta.json").read_text(encoding="utf-8")
        )
        assert nopdf_meta["ocr_status"] == "nopdf"

        key1_meta = json.loads(
            (ocr_root / "KEY1" / "meta.json").read_text(encoding="utf-8")
        )
        assert key1_meta["ocr_status"] == "pending"


class TestRunOcrListDispatch:
    """Dispatch in run() passes manifest/keys to _run_ocr_list."""

    def test_list_dispatch_manifest(self, monkeypatch) -> None:
        import argparse
        from paperforge.commands.ocr import run

        call_kwargs = {}

        def recording_fn(vault, **kwargs):
            call_kwargs.update(kwargs)
            call_kwargs["vault"] = vault
            return 0

        monkeypatch.setattr(
            "paperforge.commands.ocr._run_ocr_list",
            recording_fn,
        )

        ns = argparse.Namespace(
            vault_path=Path("/fake"),
            vault=None,
            ocr_action="list",
            json=False,
            output=None,
            manifest=True,
            keys=None,
            diagnose=False,
            key=None,
            live=False,
            dry_run=False,
            verbose=False,
            no_progress=False,
        )

        result = run(ns)
        assert result == 0
        assert call_kwargs.get("manifest") is True
        assert call_kwargs.get("vault") == Path("/fake")
