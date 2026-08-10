/**
 * Vitest tests for restore semantics (#129): display-only boundary,
 * provenance persistence, and the confirmation gate.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import * as fs from "fs";
import * as path from "path";
import os from "os";

import { restoreVersion } from "../src/services/version-history";
import { setPathConfigSource } from "../src/services/memory-state";

let root: string;

function paper(key: string): string {
  return path.join(root, "System", "PaperForge", "ocr", key);
}

function write(filePath: string, content: string) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, "utf-8");
}

beforeEach(() => {
  root = fs.mkdtempSync(path.join(os.tmpdir(), "pf-restore-"));
  // #142/C0: resolveVaultPaths consumes the injected config source (never
  // parses paperforge.json); fail-closed without it.
  setPathConfigSource({
    system_dir: "System",
    resources_dir: "Resources",
    literature_dir: "Literature",
    base_dir: "Bases",
    _warning: null,
  });
});

afterEach(() => {
  setPathConfigSource(null);
});

describe("restoreVersion (#129)", () => {
  it("copies only render/fulltext.md and never touches structure artifacts", () => {
    const p = paper("KEY1");
    write(path.join(p, "versions", "v3", "fulltext.md"), "old text");
    write(path.join(p, "structure", "blocks.structured.jsonl"), "STRUCTURE");
    write(path.join(p, "index", "structure-tree.json"), "TREE");

    const ok = restoreVersion(root, "KEY1", "v3", "2026-07-01T00:00:00Z");
    expect(ok).toBe(true);
    expect(
      fs.readFileSync(path.join(p, "render", "fulltext.md"), "utf-8")
    ).toBe("old text");
    // structure untouched
    expect(
      fs.readFileSync(
        path.join(p, "structure", "blocks.structured.jsonl"),
        "utf-8"
      )
    ).toBe("STRUCTURE");
    expect(
      fs.readFileSync(path.join(p, "index", "structure-tree.json"), "utf-8")
    ).toBe("TREE");
  });

  it("persists restore provenance into meta.json", () => {
    const p = paper("KEY1");
    write(path.join(p, "versions", "v3", "fulltext.md"), "old text");
    write(
      path.join(p, "meta.json"),
      JSON.stringify({
        zotero_key: "KEY1",
        ocr_finished_at: "2026-08-05T10:00:00Z",
      })
    );

    const ok = restoreVersion(root, "KEY1", "v3", "2026-07-01T00:00:00Z");
    expect(ok).toBe(true);
    const meta = JSON.parse(
      fs.readFileSync(path.join(p, "meta.json"), "utf-8")
    );
    expect(meta.restore_provenance.label).toBe("v3");
    expect(meta.restore_provenance.version_created_at).toBe(
      "2026-07-01T00:00:00Z"
    );
    expect(meta.restore_provenance.restored_at).toBeTruthy();
    // original fields preserved
    expect(meta.zotero_key).toBe("KEY1");
    expect(meta.ocr_finished_at).toBe("2026-08-05T10:00:00Z");
  });

  it("returns false when the version source is missing", () => {
    const p = paper("KEY1");
    write(path.join(p, "meta.json"), "{}");
    expect(restoreVersion(root, "KEY1", "v9", "2026-07-01T00:00:00Z")).toBe(
      false
    );
    // no provenance written on failure
    const meta = JSON.parse(
      fs.readFileSync(path.join(p, "meta.json"), "utf-8")
    );
    expect(meta.restore_provenance).toBeUndefined();
  });
});
