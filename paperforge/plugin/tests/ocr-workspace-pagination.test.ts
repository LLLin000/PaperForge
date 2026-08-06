/**
 * Vitest tests for OCR Workspace pagination/selection semantics (#126 PR D).
 */
import { describe, expect, it } from "vitest";
import { paginate } from "../src/views/ocr-workspace";

function keys(n: number): string[] {
  return Array.from({ length: n }, (_, i) => `K${i + 1}`);
}

describe("paginate (#126 PR D)", () => {
  it("renders at most 100 rows on the first page", () => {
    const items = keys(876);
    const { pageItems, totalPages } = paginate(items, 1);
    expect(pageItems).toHaveLength(100);
    expect(pageItems[0]).toBe("K1");
    expect(totalPages).toBe(9);
  });

  it("moves to later pages", () => {
    const items = keys(876);
    const { pageItems, page } = paginate(items, 2);
    expect(page).toBe(2);
    expect(pageItems[0]).toBe("K101");
    expect(pageItems).toHaveLength(100);
  });

  it("clamps page below 1 and above the last page", () => {
    const items = keys(876);
    expect(paginate(items, 0).page).toBe(1);
    expect(paginate(items, 99).page).toBe(9);
    expect(paginate(items, 99).pageItems).toHaveLength(76);
  });

  it("empty list yields one empty page", () => {
    const { pageItems, totalPages, page } = paginate([], 1);
    expect(pageItems).toEqual([]);
    expect(totalPages).toBe(1);
    expect(page).toBe(1);
  });
});
