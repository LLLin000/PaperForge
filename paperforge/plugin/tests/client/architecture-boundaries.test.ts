/**
 * Architecture boundary gate (Ticket 07).
 *
 * After the thin-client cutover (Tickets 01–06), business UI code must
 * communicate with the Python backend exclusively through `PaperForgeClient`
 * over `Transport`. Direct child-process usage is allowed ONLY in:
 *
 *   1. `src/client/**`            — the single Transport owner
 *   2. `src/services/managed-runtime.ts` — bootstrap/runtime adapter seam
 *   3. `main.ts`                  — plugin bootstrap (legacy ratchet)
 *
 * Every other file is on a ratchet baseline: the recorded count of
 * `spawn|execFile|execFileSync` call sites must NEVER increase, and no new
 * file may appear on the list. Shrink the baseline as Ticket 07 deletes the
 * remaining legacy surfaces; a shrinking baseline is the enforcement.
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { describe, it, expect } from "vitest";

const SRC = join(__dirname, "..", "..", "src");

/** Files permanently exempt from the child-process ratchet. */
const EXEMPT = (relPosix: string): boolean => {
  if (relPosix.startsWith("client/")) return true; // Transport owner
  if (relPosix === "services/secret-storage.ts") return true; // DI: spawn injected via MigrationSpawn
  return false;
};

/** plugin bootstrap ratchet — shrink when main.ts legacy sync dies. */
const MAIN_BASELINE = 2;

/** Ratchet baseline: file (posix, relative to src/) → max call sites. */
const BASELINE: Record<string, number> = {
  "settings.ts": 7,
  "views/dashboard.ts": 3,
  "views/modals.ts": 3,
  "services/config-client.ts": 2,
  "services/embed-build-controller.ts": 2,
  "services/long-task-client.ts": 2,
  "services/ocr-process-controller.ts": 3,
  "services/python-bridge.ts": 3,
};

const PATTERN = /\b(spawn|execFile|execFileSync)\s*\(/g;

function* walk(dir: string): Generator<string> {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      yield* walk(full);
    } else if (full.endsWith(".ts")) {
      yield full;
    }
  }
}

function countCallSites(content: string): number {
  return [...content.matchAll(PATTERN)].length;
}

describe("architecture boundary gate (Ticket 07)", () => {
  it("no file exceeds its child-process ratchet baseline", () => {
    const violations: string[] = [];
    for (const file of walk(SRC)) {
      const rel = relative(SRC, file).split(sep).join("/");
      if (EXEMPT(rel)) continue;
      const count = countCallSites(readFileSync(file, "utf-8"));
      if (rel === "main.ts") {
        if (count > MAIN_BASELINE) {
          violations.push(`${rel}: ${count} > baseline ${MAIN_BASELINE}`);
        }
        continue;
      }
      const baseline = BASELINE[rel];
      if (baseline === undefined) {
        if (count > 0) {
          violations.push(
            `${rel}: NEW file with child-process usage (${count})`
          );
        }
        continue;
      }
      if (count > baseline) {
        violations.push(`${rel}: ${count} > baseline ${baseline}`);
      }
    }
    expect(violations).toEqual([]);
  });

  it("deleted legacy surfaces stay deleted", () => {
    // Files absorbed or obsoleted by the thin-client cutover must never return.
    const deleted = ["services/ocr-maintenance-ui.ts"];
    for (const rel of deleted) {
      expect(() => statSync(join(SRC, rel))).toThrow();
    }
  });
});
