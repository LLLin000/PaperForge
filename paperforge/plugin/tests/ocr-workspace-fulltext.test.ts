/**
 * Vitest tests for OCR Workspace fulltext resolution (#126 PR C P0):
 * the double-`PaperForge` path bug must never return.
 */
import { describe, expect, it } from "vitest";
import * as path from "path";
import { resolvePaperFulltextPath } from "../src/views/ocr-workspace";

const VAULT = "C:/vault";
const OCR_DIR = path.join(VAULT, "System", "PaperForge", "ocr");

describe("resolvePaperFulltextPath (#126 P0)", () => {
  it("prefers the canonical index fulltext_path when it exists", () => {
    const exists = (p: string) =>
      p === path.join(VAULT, "System/PaperForge/ocr/KEY1/fulltext.md");
    const result = resolvePaperFulltextPath(
      VAULT,
      "System/PaperForge/ocr/KEY1/fulltext.md",
      "KEY1",
      OCR_DIR,
      exists
    );
    expect(result).not.toBeNull();
    expect(String(result).replace(/\\/g, "/")).toContain(
      "ocr/KEY1/fulltext.md"
    );
  });

  it("falls back to ocrDir/<key>/fulltext.md when the index path is missing", () => {
    const exists = (p: string) =>
      p === path.join(OCR_DIR, "KEY1", "fulltext.md");
    const result = resolvePaperFulltextPath(
      VAULT,
      "System/PaperForge/ocr/KEY1/fulltext.md",
      "KEY1",
      OCR_DIR,
      exists
    );
    expect(String(result).replace(/\\/g, "/")).toContain(
      "System/PaperForge/ocr/KEY1/fulltext.md"
    );
  });

  it("never produces a double PaperForge segment", () => {
    const result = resolvePaperFulltextPath(
      VAULT,
      "System/PaperForge/ocr/KEY1/fulltext.md",
      "KEY1",
      OCR_DIR,
      () => true
    );
    expect(result).not.toContain("PaperForge/PaperForge");
  });

  it("returns null when neither the index path nor the fallback exists", () => {
    const result = resolvePaperFulltextPath(
      VAULT,
      "System/PaperForge/ocr/KEY1/fulltext.md",
      "KEY1",
      OCR_DIR,
      () => false
    );
    expect(result).toBeNull();
  });

  it("handles Windows separators in the resolved path", () => {
    const winVault = "D:\\vault";
    const winOcr = "D:\\vault\\System\\PaperForge\\ocr";
    const exists = (p: string) =>
      p === "D:\\vault\\System\\PaperForge\\ocr\\K\\fulltext.md";
    const result = resolvePaperFulltextPath(winVault, "", "K", winOcr, exists);
    expect(result).toBe("D:\\vault\\System\\PaperForge\\ocr\\K\\fulltext.md");
  });
});
