/**
 * Architecture boundary gate (Ticket 07) — authority + exact-snapshot ratchet.
 *
 * Layering contract:
 *   PaperForgeClient → Transport → NodeProcessTransport  ← the ONLY
 *   long-term child-process authority in the plugin.
 *
 * Gate A — import authority: importing/requiring `child_process` (or
 *   `node:child_process`) is allowed ONLY in the exact files listed below.
 *   Any new importer fails the suite. DI seams (e.g. secret-storage's
 *   injected `deps.spawn`) carry no authority and need no exemption.
 *
 * Gate B — exact-snapshot ratchet: legacy files still on child_process
 *   authority are frozen at their current call-site count. `actual ===
 *   snapshot` — deleting a call forces the snapshot down in the same commit,
 *   so debt can never silently regrow.
 *
 * Gate C — tombstones: surfaces already absorbed by the thin-client cutover
 *   stay deleted.
 *
 * Shrink the snapshots as Stage 2 collapses each legacy surface from leaf
 * callers toward the transport root.
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";
import ts from "typescript";
import { describe, it, expect } from "vitest";

const SRC = join(__dirname, "..", "..", "src");
const CP_MODULE = /^(node:)?child_process$/;

/** Permanent child-process authority — the transport stack, exact files. */
const DIRECT_AUTHORITY_OWNERS: Record<string, number> = {
  // Transport root. Spawn delegation lives in long-task-client until Stage 2
  // collapses it into this file.
  "client/node-transport.ts": 0,
  // Transport stack (NodeProcessTransport's streaming engine). Snapshot
  // frozen; must be merged into client/node-transport.ts before Ticket 07
  // closes.
  "services/long-task-client.ts": 2,
};

/** Host-layer seams, listed file-by-file with their exact current shape. */
const HOST_SEAMS: Record<string, number> = {
  // Bootstrap/runtime adapter: imports cpExecFile/cpExecFileSync and injects
  // them as DI defaults (opts?.execFile ?? cpExecFile); zero direct calls.
  "services/managed-runtime.ts": 0,
};

/** Legacy debt — exact-snapshot ratchet, shrinks only. */
const LEGACY_RATCHET: Record<string, number> = {
  "main.ts": 2,
  "settings.ts": 7,
  "views/dashboard.ts": 3,
  "views/modals.ts": 3,
  "services/config-client.ts": 2,
  "services/embed-build-controller.ts": 2,
  // Test-seam spawn via this._spawn; zero direct call sites, import frozen.
  "services/ocr-process-controller.ts": 0,
  "services/python-bridge.ts": 5,
};

/** Files that must never exist again. */
const TOMBSTONES = ["services/ocr-maintenance-ui.ts"];

const CALL_NAMES = new Set([
  "spawn",
  "exec",
  "execFile",
  "execFileSync",
  "spawnSync",
  "execSync",
  "fork",
]);

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

interface Probe {
  importsChildProcess: boolean;
  callCount: number;
}

function probe(content: string): Probe {
  const sf = ts.createSourceFile(
    "gate.ts",
    content,
    ts.ScriptTarget.Latest,
    true
  );
  let importsChildProcess = false;
  let callCount = 0;
  const visit = (node: ts.Node): void => {
    if (
      ts.isImportDeclaration(node) &&
      CP_MODULE.test(node.moduleSpecifier.text)
    ) {
      importsChildProcess = true;
    }
    if (
      ts.isCallExpression(node) &&
      ts.isIdentifier(node.expression) &&
      node.expression.text === "require" &&
      node.arguments.length === 1 &&
      ts.isStringLiteral(node.arguments[0]) &&
      CP_MODULE.test(node.arguments[0].text)
    ) {
      importsChildProcess = true;
    }
    if (ts.isCallExpression(node)) {
      const expr = node.expression;
      const name = ts.isIdentifier(expr)
        ? expr.text
        : ts.isPropertyAccessExpression(expr)
          ? expr.name.text
          : undefined;
      if (name !== undefined && CALL_NAMES.has(name)) callCount += 1;
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return { importsChildProcess, callCount };
}

describe("architecture boundary gate (Ticket 07)", () => {
  it("Gate A: child_process import authority belongs only to listed files", () => {
    const violations: string[] = [];
    const known = new Set([
      ...Object.keys(DIRECT_AUTHORITY_OWNERS),
      ...Object.keys(HOST_SEAMS),
      ...Object.keys(LEGACY_RATCHET),
    ]);
    for (const file of walk(SRC)) {
      const rel = relative(SRC, file).split(sep).join("/");
      const { importsChildProcess } = probe(readFileSync(file, "utf-8"));
      if (importsChildProcess && !known.has(rel)) {
        violations.push(`${rel}: unauthorized child_process import`);
      }
    }
    expect(violations).toEqual([]);
  });

  it("Gate B: legacy/host subprocess call sites match their exact snapshot", () => {
    const violations: string[] = [];
    const snapshots: Array<[string, Record<string, number>]> = [
      ["authority", DIRECT_AUTHORITY_OWNERS],
      ["host", HOST_SEAMS],
      ["legacy", LEGACY_RATCHET],
    ];
    for (const [kind, map] of snapshots) {
      for (const [rel, frozen] of Object.entries(map)) {
        const file = join(SRC, rel);
        const actual = probe(readFileSync(file, "utf-8")).callCount;
        // exact equality: deleting a call forces the snapshot down in the
        // same commit — the debt can only move toward zero.
        expect([`${kind}:${rel}`, actual]).toEqual([`${kind}:${rel}`, frozen]);
      }
    }
    expect(violations).toEqual([]);
  });

  it("Gate C: absorbed legacy surfaces stay deleted", () => {
    for (const rel of TOMBSTONES) {
      expect(() => statSync(join(SRC, rel))).toThrow();
    }
  });
});
