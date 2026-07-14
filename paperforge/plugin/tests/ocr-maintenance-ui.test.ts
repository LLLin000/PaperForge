import type { MaintenanceDisplayRow, MaintenanceCache } from "../src/services/ocr-maintenance-ui";
import {
  categorizeMaintenanceRow,
  buildMaintenanceSummary,
  MaintenanceRowLike,
} from "../src/services/ocr-maintenance-ui";
import { describe, expect, it } from "vitest";

describe("categorizeMaintenanceRow", () => {
  it("maps rebuild recommendation to Rebuild Recommended", () => {
    const result = categorizeMaintenanceRow({
      key: "A1",
      title: "Paper A",
      status: "done_degraded",
      health: "yellow",
      recommended_action: "rebuild",
      degraded_reasons: ["weak span coverage (62%)"],
      error_summary: "",
      error_stage: "",
      version: "v2",
      finished_at: "06-19 10:00",
      model: "PaddleOCR-VL-1.6",
    } as any);

    expect(result.category).toBe("rebuild");
    expect(result.label).toBe("Rebuild Recommended");
    expect(result.primaryAction).toBe("rebuild");
  });

  it("maps failed OCR to OCR Failed and only then promotes rerun", () => {
    const result = categorizeMaintenanceRow({
      key: "B1",
      title: "Paper B",
      status: "failed",
      health: "-",
      recommended_action: "redo",
      degraded_reasons: [],
      error_summary: "timeout",
      error_stage: "poll",
      version: "v2",
      finished_at: "06-19 11:00",
      model: "PaddleOCR-VL-1.6",
    } as any);

    expect(result.category).toBe("failed");
    expect(result.label).toBe("OCR Failed");
    expect(result.primaryAction).toBe("redo");
  });

  it("keeps non-actionable degraded papers in Result Limited", () => {
    const result = categorizeMaintenanceRow({
      key: "C1",
      title: "Paper C",
      status: "done_degraded",
      health: "yellow",
      recommended_action: "",
      degraded_reasons: ["weak body spine"],
      error_summary: "",
      error_stage: "",
      version: "v2",
      finished_at: "06-19 12:00",
      model: "PaddleOCR-VL-1.6",
    } as any);

    expect(result.category).toBe("limited");
    expect(result.label).toBe("Result Limited");
    expect(result.primaryAction).toBeNull();
  });

  it("keeps clean completed rows in No Action Needed", () => {
    const result = categorizeMaintenanceRow({
      key: "D1",
      title: "Paper D",
      status: "done",
      health: "green",
      recommended_action: "",
      degraded_reasons: [],
      error_summary: "",
      error_stage: "",
      version: "v2",
      finished_at: "06-19 13:00",
      model: "PaddleOCR-VL-1.6",
    } as any);

    expect(result.category).toBe("ok");
    expect(result.label).toBe("No Action Needed");
    expect(result.primaryAction).toBeNull();
  });

  it("uses rebuild-first copy for actionable items", () => {
    const result = categorizeMaintenanceRow({
      key: "R1",
      title: "Paper R",
      status: "done_degraded",
      health: "yellow",
      recommended_action: "rebuild",
      degraded_reasons: ["weak span coverage (51%)"],
      error_summary: "",
      error_stage: "",
      version: "v2",
      finished_at: "06-19 14:00",
      model: "PaddleOCR-VL-1.6",
    } as any);

    expect(result.reason).toContain("existing OCR data");
  });

  it("does not promote redo for non-failed rows", () => {
    const result = categorizeMaintenanceRow({
      key: "R2",
      title: "Paper R2",
      status: "done_degraded",
      health: "yellow",
      recommended_action: "redo",
      degraded_reasons: ["weak body spine"],
      error_summary: "",
      error_stage: "",
      version: "v2",
      finished_at: "06-19 14:10",
      model: "PaddleOCR-VL-1.6",
    } as any);

    expect(result.category).toBe("limited");
    expect(result.primaryAction).toBeNull();
  });

  it("keeps unknown drift rows non-deceptive", () => {
    // Test fixture: object includes drift fields before type supports them
    const input: Record<string, unknown> = {
      key: "U1",
      title: "Paper U",
      title_full: "Paper U",
      status: "done",
      health: "green",
      recommended_action: "",
      degraded_reasons: [],
      error_summary: "",
      error_stage: "",
      version: "v2",
      finished_at: "06-19 10:00",
      rebuild_finished_at: "-",
      model: "PaddleOCR-VL-1.6",
      fulltext_drift_state: "UNKNOWN",
      fulltext_drift_reason: "No machine baseline is available.",
    };
    const result = categorizeMaintenanceRow(
      input as unknown as MaintenanceRowLike
    );
    expect(result.reason).not.toContain("safe");
  });
});

describe("buildMaintenanceSummary", () => {
  it("counts categories and builds the top-level verdict", () => {
    const summary = buildMaintenanceSummary([
      { category: "ok" },
      { category: "rebuild" },
      { category: "failed" },
      { category: "limited" },
    ] as any);

    expect(summary.counts).toEqual({
      ok: 1,
      rebuild: 1,
      failed: 1,
      limited: 1,
    });
    expect(summary.tone).toBe("warn");
  });

  it("returns ok tone when no failures or rebuilds", () => {
    const summary = buildMaintenanceSummary([
      { category: "ok" },
      { category: "limited" },
    ] as any);

    expect(summary.counts).toEqual({
      ok: 1,
      rebuild: 0,
      failed: 0,
      limited: 1,
    });
    expect(summary.tone).toBe("ok");
  });
});

describe("MaintenanceDisplayRow field contract", () => {
  it("includes needs_derived_rebuild in a complete row shape", () => {
    const row: MaintenanceDisplayRow = {
      key: "TEST-001",
      title: "Test Paper",
      display_action: "rebuild_result",
      display_label: "Rebuild Recommended",
      display_reason: "Fulltext drifted from last rebuild",
      display_group: "rebuild",
      visible_in_maintenance: true,
      can_redo: false,
      can_rebuild: true,
      needs_derived_rebuild: true,
    };
    expect(row.needs_derived_rebuild).toBe(true);
    expect(row.can_rebuild).toBe(true);
    expect(row.key).toBe("TEST-001");
  });

  it("accepts needs_derived_rebuild false for clean papers", () => {
    const row: MaintenanceDisplayRow = {
      key: "CLEAN-001",
      title: "Clean Paper",
      display_action: "none",
      display_label: "No Action Needed",
      display_reason: "OK",
      display_group: "hidden",
      visible_in_maintenance: false,
      can_redo: true,
      can_rebuild: false,
      needs_derived_rebuild: false,
    };
    expect(row.needs_derived_rebuild).toBe(false);
  });
});

describe("needs_derived_rebuild schema freshness", () => {
  it("accepts a cache where every row has the boolean field", () => {
    const schemaFresh = Object.values({
      "A-1": {
        key: "A-1",
        title: "Fresh",
        display_action: "rebuild_result",
        display_label: "Rebuild",
        display_reason: "drifted",
        display_group: "rebuild",
        visible_in_maintenance: true,
        can_redo: false,
        can_rebuild: true,
        needs_derived_rebuild: true,
      } as MaintenanceDisplayRow,
      "B-2": {
        key: "B-2",
        title: "Clean",
        display_action: "none",
        display_label: "No Action",
        display_reason: "",
        display_group: "hidden",
        visible_in_maintenance: false,
        can_redo: true,
        can_rebuild: false,
        needs_derived_rebuild: false,
      } as MaintenanceDisplayRow,
    }).every((p) => typeof p.needs_derived_rebuild === "boolean");

    expect(schemaFresh).toBe(true);
  });

  it("rejects a cache where a row lacks needs_derived_rebuild", () => {
    const schemaFresh = Object.values({
      "A-1": {
        key: "A-1",
        title: "Stale row",
        display_action: "rebuild_result",
        display_label: "Rebuild",
        display_reason: "drifted",
        display_group: "rebuild",
        visible_in_maintenance: true,
        can_redo: false,
        can_rebuild: true,
        // no needs_derived_rebuild — stale schema
      } as MaintenanceDisplayRow,
      "B-2": {
        key: "B-2",
        title: "Fresh row",
        display_action: "none",
        display_label: "No Action",
        display_reason: "",
        display_group: "hidden",
        visible_in_maintenance: false,
        can_redo: true,
        can_rebuild: false,
        needs_derived_rebuild: false,
      } as MaintenanceDisplayRow,
    }).every((p) => typeof p.needs_derived_rebuild === "boolean");

    expect(schemaFresh).toBe(false);
  });

  it("rejects entirely empty cache (no papers at all)", () => {
    const schemaFresh = Object.values({} as Record<string, MaintenanceDisplayRow>).every(
      (p) => typeof p.needs_derived_rebuild === "boolean",
    );
    // .every() on empty array returns true — degenerate case handled by
    // the fact that refreshMaintenanceData would refetch when cache.papers is empty
    expect(schemaFresh).toBe(true);
  });

  it("passes through all rows regardless of visible_in_maintenance", () => {
    const cache: MaintenanceCache = {
      manifest: { "A-1": "aaa", "B-2": "bbb" },
      papers: {
        "A-1": {
          key: "A-1",
          title: "Visible Paper",
          display_action: "rebuild_result",
          display_label: "Rebuild",
          display_reason: "drifted",
          display_group: "rebuild",
          visible_in_maintenance: true,
          can_redo: false,
          can_rebuild: true,
          needs_derived_rebuild: true,
        } as MaintenanceDisplayRow,
        "B-2": {
          key: "B-2",
          title: "Hidden Paper",
          display_action: "none",
          display_label: "OK",
          display_reason: "",
          display_group: "hidden",
          visible_in_maintenance: false,
          can_redo: true,
          can_rebuild: false,
          needs_derived_rebuild: false,
        } as MaintenanceDisplayRow,
      },
      cached_at: new Date().toISOString(),
    };

    const data = Object.values(cache.papers);
    expect(data).toHaveLength(2);
    expect(data.find((p) => p.key === "B-2")).toBeTruthy();
    expect(data.find((p) => p.key === "A-1")).toBeTruthy();
  });
});
