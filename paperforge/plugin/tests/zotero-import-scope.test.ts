import { describe, expect, it } from "vitest";
import {
  LARGE_LIBRARY_FOLDER_GUARD_THRESHOLD,
  evaluateZoteroImportScope,
  type ZoteroCollectionCandidate,
} from "../src/services/zotero-import-scope";

const SAMPLE_COLS: ZoteroCollectionCandidate[] = [
  { key: "COL_A", name: "Rotator Cuff", item_count: 85, top_level: true },
  { key: "COL_B", name: "Cartilage Repair", item_count: 140, top_level: true },
  { key: "COL_C", name: "Archive", item_count: 420, top_level: true },
];

describe("evaluateZoteroImportScope (Folder-First Import Guardrail)", () => {
  it("requires explicit folder choice on small libraries (<= 200 papers) when collections exist and nothing is selected", () => {
    const res = evaluateZoteroImportScope({
      totalPapers: LARGE_LIBRARY_FOLDER_GUARD_THRESHOLD,
      collections: SAMPLE_COLS,
      selected: [],
    });
    expect(res.isLargeLibrary).toBe(false);
    expect(res.requiresFolderChoice).toBe(true);
    expect(res.explicitAll).toBe(false);
    expect(res.estimatedPapers).toBe(200);
  });

  it("allows import on small libraries when collections exist and at least one folder is picked", () => {
    const res = evaluateZoteroImportScope({
      totalPapers: 85,
      collections: SAMPLE_COLS,
      selected: ["COL_A"],
    });
    expect(res.isLargeLibrary).toBe(false);
    expect(res.requiresFolderChoice).toBe(false);
    expect(res.selectedKeys).toEqual(["COL_A"]);
    expect(res.estimatedPapers).toBe(85);
  });

  it("allows import on large libraries with 0 collections", () => {
    const res = evaluateZoteroImportScope({
      totalPapers: 1200,
      collections: [],
      selected: [],
    });
    expect(res.isLargeLibrary).toBe(true);
    expect(res.requiresFolderChoice).toBe(false);
    expect(res.estimatedPapers).toBe(1200);
  });

  it("requires explicit folder choice on large libraries (> 200 papers) when nothing is selected", () => {
    const res = evaluateZoteroImportScope({
      totalPapers: 1358,
      collections: SAMPLE_COLS,
      selected: [],
    });
    expect(res.isLargeLibrary).toBe(true);
    expect(res.requiresFolderChoice).toBe(true);
    expect(res.selectedKeys).toEqual([]);
    expect(res.explicitAll).toBe(false);
  });

  it("unlocks large-library import and estimates selected paper count when specific folders are picked", () => {
    const res = evaluateZoteroImportScope({
      totalPapers: 1358,
      collections: SAMPLE_COLS,
      selected: ["COL_A", "COL_B", "UNKNOWN_STALE"],
    });
    expect(res.requiresFolderChoice).toBe(false);
    expect(res.selectedKeys).toEqual(["COL_A", "COL_B"]);
    expect(res.estimatedPapers).toBe(225);
  });

  it("unlocks whole-library import when explicit wildcard '*' is chosen", () => {
    const res = evaluateZoteroImportScope({
      totalPapers: 1358,
      collections: SAMPLE_COLS,
      selected: ["*"],
    });
    expect(res.requiresFolderChoice).toBe(false);
    expect(res.explicitAll).toBe(true);
    expect(res.selectedKeys).toEqual([]);
    expect(res.estimatedPapers).toBe(1358);
  });
});
