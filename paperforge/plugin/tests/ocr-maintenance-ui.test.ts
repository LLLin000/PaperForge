import { describe, expect, it } from "vitest";
import {
  categorizeMaintenanceRow,
  buildMaintenanceSummary,
} from "../src/services/ocr-maintenance-ui";

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
