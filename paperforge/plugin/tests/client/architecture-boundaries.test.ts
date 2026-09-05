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
 * Gate B — exact-snapshot ratchet via BINDING PROVENANCE: legacy files are
 *   frozen at their current count of call sites whose callee resolves to a
 *   child_process binding — named imports (including `import { spawn as
 *   launch }`), namespace imports (`import * as cp`), and every require
 *   form (`const cp = require(...)`, `const { spawn: launch } = require(...)`,
 *   `require("child_process").spawn(...)`). Calls on unrelated objects
 *   (`deps.spawn`, `someObject.exec`) are NOT counted — they carry no
 *   authority. `actual === snapshot` — deleting a call forces the snapshot
 *   down in the same commit, so debt can never silently regrow.
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
  // Test-seam default `spawnFn = this._opts.spawnFn ?? spawn` — the
  // `spawnFn(...)` call IS a real spawn site the old regex gate
  // under-counted as 0; binding provenance catches it. Import frozen.
  "services/ocr-process-controller.ts": 1,
  // Provenance-resolved: 8 real spawn sites (incl. `const execSync =
  // _execFileSync || execFileSync` fallback aliases at 99/151/361/415 that
  // the old regex gate under-counted as 5).
  "services/python-bridge.ts": 8,
};

/** Files that must never exist again. */
const TOMBSTONES = ["services/ocr-maintenance-ui.ts"];

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

/** binding name → how it may be called: "named" (bare callee) or "namespace" (member callee). */
type BindingKind = "named" | "namespace";

/** Is `node` a `require("child_process")` (or node: variant) call? */
function isChildProcessRequire(node: ts.Expression): boolean {
  return (
    ts.isCallExpression(node) &&
    ts.isIdentifier(node.expression) &&
    node.expression.text === "require" &&
    node.arguments.length === 1 &&
    ts.isStringLiteral(node.arguments[0]) &&
    CP_MODULE.test(node.arguments[0].text)
  );
}

/**
 * Binding-provenance probe: build the child_process binding table from
 * import/require forms, then count ONLY call sites whose callee resolves to
 * one of those bindings. Exported for synthetic provenance regressions.
 */
export function probe(content: string): Probe {
  const sf = ts.createSourceFile(
    "gate.ts",
    content,
    ts.ScriptTarget.Latest,
    true
  );
  let importsChildProcess = false;
  let callCount = 0;
  const bindings = new Map<string, BindingKind>();

  const registerRequireBindings = (name: ts.BindingName): void => {
    if (ts.isIdentifier(name)) {
      bindings.set(name.text, "namespace");
    } else if (ts.isObjectBindingPattern(name)) {
      for (const el of name.elements) {
        if (ts.isIdentifier(el.name)) bindings.set(el.name.text, "named");
      }
    }
  };

  const visit = (node: ts.Node): void => {
    // import ... from "child_process"
    if (
      ts.isImportDeclaration(node) &&
      CP_MODULE.test(node.moduleSpecifier.text)
    ) {
      importsChildProcess = true;
      const clause = node.importClause;
      if (clause?.name) bindings.set(clause.name.text, "namespace");
      if (clause?.namedBindings) {
        if (ts.isNamespaceImport(clause.namedBindings)) {
          bindings.set(clause.namedBindings.name.text, "namespace");
        } else {
          for (const el of clause.namedBindings.elements) {
            bindings.set(el.name.text, "named"); // `spawn` or `spawn as launch`
          }
        }
      }
    }
    // import cp = require("child_process")
    if (
      ts.isImportEqualsDeclaration(node) &&
      ts.isExternalModuleReference(node.moduleReference) &&
      CP_MODULE.test(node.moduleReference.expression.text)
    ) {
      importsChildProcess = true;
      bindings.set(node.name.text, "namespace");
    }
    // const cp = require("child_process") /
    // const { spawn: launch } = require("child_process") /
    // const X = <expr referencing a known binding> — local alias chains
    // inherit the binding's provenance (e.g. `const execSync =
    // _execFileSync || execFileSync`). Over-approximation is the safe
    // direction for a ratchet: debt is never under-counted.
    if (ts.isVariableStatement(node)) {
      for (const decl of node.declarationList.declarations) {
        if (decl.initializer && isChildProcessRequire(decl.initializer)) {
          importsChildProcess = true;
          registerRequireBindings(decl.name);
          continue;
        }
        if (decl.initializer) {
          // Pure rename / fallback chains only — NEVER call results
          // (`const child = spawn(...)` binds the PROCESS HANDLE, not the
          // spawning authority; counting its method calls would inflate
          // the snapshot).
          const propagate = (init: ts.Expression): BindingKind | undefined => {
            if (ts.isIdentifier(init)) return bindings.get(init.text);
            if (
              ts.isBinaryExpression(init) &&
              (init.operatorToken.kind === ts.SyntaxKind.BarBarToken ||
                init.operatorToken.kind ===
                  ts.SyntaxKind.QuestionQuestionToken ||
                init.operatorToken.kind ===
                  ts.SyntaxKind.AmpersandAmpersandToken)
            ) {
              return propagate(init.left) ?? propagate(init.right);
            }
            if (ts.isParenthesizedExpression(init)) {
              return propagate(init.expression);
            }
            return undefined;
          };
          const referenced = propagate(decl.initializer);
          if (referenced && ts.isIdentifier(decl.name)) {
            bindings.set(decl.name.text, referenced);
          }
        }
      }
    }
    if (ts.isCallExpression(node)) {
      // require("child_process").spawn(...) — member call straight off the require
      if (
        ts.isPropertyAccessExpression(node.expression) &&
        isChildProcessRequire(node.expression.expression)
      ) {
        importsChildProcess = true;
        callCount += 1;
      } else {
        const expr = node.expression;
        if (ts.isIdentifier(expr)) {
          if (bindings.get(expr.text) === "named") callCount += 1;
        } else if (ts.isPropertyAccessExpression(expr)) {
          const obj = expr.expression;
          if (ts.isIdentifier(obj) && bindings.get(obj.text) === "namespace") {
            callCount += 1;
          }
        }
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return { importsChildProcess, callCount };
}

interface Probe {
  importsChildProcess: boolean;
  callCount: number;
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

  it("Gate B: child_process call sites match their exact binding-provenance snapshot", () => {
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
  });

  it("Gate C: absorbed legacy surfaces stay deleted", () => {
    for (const rel of TOMBSTONES) {
      expect(() => statSync(join(SRC, rel))).toThrow();
    }
  });

  describe("probe binding provenance (synthetic regressions)", () => {
    it("counts aliased named imports", () => {
      expect(
        probe(`import { spawn as launch } from "child_process";\nlaunch("x");`)
      ).toEqual({ importsChildProcess: true, callCount: 1 });
    });

    it("counts namespace member calls", () => {
      expect(
        probe(`import * as cp from "child_process";\ncp.spawn("x");`)
      ).toEqual({ importsChildProcess: true, callCount: 1 });
    });

    it("counts require namespace and destructured-alias forms", () => {
      expect(
        probe(`const cp = require("child_process");\ncp.execFile("x");`)
      ).toEqual({ importsChildProcess: true, callCount: 1 });
      expect(
        probe(
          `const { fork: runFork } = require("child_process");\nrunFork("x");`
        )
      ).toEqual({ importsChildProcess: true, callCount: 1 });
    });

    it("counts member calls straight off require()", () => {
      expect(probe(`require("child_process").spawn("x");`)).toEqual({
        importsChildProcess: true,
        callCount: 1,
      });
    });

    it("does NOT count calls on unrelated objects", () => {
      expect(
        probe(
          `declare const deps: { spawn: unknown };\ndeclare const unrelated: { exec: unknown };\ndeps.spawn("x");\nunrelated.exec("y");`
        )
      ).toEqual({ importsChildProcess: false, callCount: 0 });
    });
  });
});
