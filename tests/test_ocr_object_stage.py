"""The figure/table stage order is the contract: pin it."""

from __future__ import annotations

import paperforge.worker.ocr_blocks as blocks_module
import paperforge.worker.ocr_figures as figures_module
import paperforge.worker.ocr_figure_reader as reader_module
import paperforge.worker.ocr_tables as tables_module
from paperforge.worker import ocr_object_stage


def test_association_stage_runs_the_documented_order(monkeypatch) -> None:
    calls: list[str] = []
    structured: list[dict] = []

    def record(name):
        def _fn(*args, **kwargs):
            calls.append(name)
            if name == "build_figure_inventory":
                return {"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []}
            if name == "synthesize_reader_figures":
                return {"reader_figures": []}
            if name == "build_table_inventory":
                return {"tables": []}
            return None
        return _fn

    monkeypatch.setattr(figures_module, "build_figure_inventory", record("build_figure_inventory"))
    monkeypatch.setattr(figures_module, "write_back_figure_roles", record("write_back_figure_roles"))
    monkeypatch.setattr(figures_module, "resolve_media_asset_conflicts", record("resolve_media_asset_conflicts"))
    monkeypatch.setattr(figures_module, "attach_ownership_conflicts", record("attach_ownership_conflicts"))
    monkeypatch.setattr(reader_module, "synthesize_reader_figures", record("synthesize_reader_figures"))
    monkeypatch.setattr(tables_module, "build_table_inventory", record("build_table_inventory"))
    monkeypatch.setattr(ocr_object_stage, "_resolve_ref_start_page", lambda blocks: None, raising=False)

    ocr_object_stage.run_association_stage(structured)

    assert calls == [
        "build_figure_inventory",
        "write_back_figure_roles",
        "synthesize_reader_figures",
        "build_table_inventory",
        "resolve_media_asset_conflicts",
        "attach_ownership_conflicts",
    ]


def test_commit_applies_writeback_before_table_roles(monkeypatch) -> None:
    calls: list[str] = []
    import paperforge.worker.ocr_object_writeback as writeback_module

    monkeypatch.setattr(writeback_module, "apply_object_writebacks", lambda **kwargs: calls.append("writeback"))
    monkeypatch.setattr(tables_module, "write_back_table_roles", lambda inv, rows: calls.append("table_roles"))

    ocr_object_stage.commit_object_roles([], {"matched_figures": []}, {"tables": []})
    assert calls == ["writeback", "table_roles"]
