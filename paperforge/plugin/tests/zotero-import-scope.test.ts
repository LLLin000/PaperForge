import { describe, expect, it } from "vitest";
import {
  LARGE_LIBRARY_FOLDER_GUARD_THRESHOLD,
  collectLegacyDomainNames,
  computeVeteranZoteroPreselection,
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

  it("caps estimatedPapers at totalPapers when overlapping collections sum higher than totalPapers", () => {
    const res = evaluateZoteroImportScope({
      totalPapers: 120,
      collections: SAMPLE_COLS,
      selected: ["COL_A", "COL_B"],
    });
    expect(res.requiresFolderChoice).toBe(false);
    expect(res.selectedKeys).toEqual(["COL_A", "COL_B"]);
    expect(res.estimatedPapers).toBe(120);
  });
});

describe("Veteran Zotero BBT → SQLite Preselection Helpers", () => {
  it("collectLegacyDomainNames distinguishes manual BBT exports from sqlite-managed slices and ignores Unfiled", () => {
    const res = collectLegacyDomainNames({
      exportFiles: [
        { stem: "Rotator Cuff", managedBySqlite: false },
        { stem: "Unfiled", managedBySqlite: true },
      ],
      literatureFolders: ["Rotator Cuff", "Cartilage Repair", "ai", ".tmp"],
    });
    expect(res.hasManualBbtExports).toBe(true);
    expect(res.legacyDomainNames).toEqual(["Rotator Cuff", "Cartilage Repair"]);
  });

  it("preserves explicit wildcard or valid selected keys first", () => {
    expect(
      computeVeteranZoteroPreselection({
        collections: SAMPLE_COLS,
        existingSelected: ["*"],
        legacyDomainNames: ["Rotator Cuff"],
      })
    ).toEqual({ mode: "preserved", selectedKeys: ["*"], matchedNames: [] });

    expect(
      computeVeteranZoteroPreselection({
        collections: SAMPLE_COLS,
        existingSelected: ["COL_C", "GONE"],
        legacyDomainNames: ["Rotator Cuff"],
      })
    ).toEqual({ mode: "preserved", selectedKeys: ["COL_C"], matchedNames: [] });
  });

  it("matches legacy BBT domain names case-insensitively and leaves new Zotero folders unchecked", () => {
    const res = computeVeteranZoteroPreselection({
      collections: SAMPLE_COLS,
      existingSelected: [],
      legacyDomainNames: ["rotator cuff", "Unrelated"],
    });
    expect(res.mode).toBe("matched_legacy");
    expect(res.selectedKeys).toEqual(["COL_A"]);
    expect(res.matchedNames).toEqual(["Rotator Cuff"]);
  });

  it("falls back to unselected when no legacy topics match any collection", () => {
    const res = computeVeteranZoteroPreselection({
      collections: SAMPLE_COLS,
      existingSelected: [],
      legacyDomainNames: ["Nonexistent"],
    });
    expect(res).toEqual({
      mode: "unselected",
      selectedKeys: [],
      matchedNames: [],
    });
  });
});
