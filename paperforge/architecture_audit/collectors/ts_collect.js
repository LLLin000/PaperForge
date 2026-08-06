#!/usr/bin/env node
/**
 * TypeScript deterministic collector (#133).
 *
 * Uses the repository-installed TypeScript Compiler API to parse source and
 * emit versioned facts compatible with the ArchitectureSurvey schema:
 *  - Tier 1 direct sinks: fs writes (writeFile/appendFile/rename/copyFile),
 *    child_process spawns (recorded unresolved — intent is never inferred).
 *  - Tier 2 wrapper registry (JSON payload, same schema as the Python side;
 *    built-in default covers the progress-parser signal consumer).
 *  - Tier 3 unresolved dynamic calls.
 *
 * Output: JSON {facts, parse_errors, scanned, wrapper_hits} on stdout.
 * No type-checking, network, or project execution happens here.
 */
"use strict";

const fs = require("fs");
const path = require("path");

const EXCLUDED_DIRS = new Set([
  ".git", ".worktrees", ".venv", "__pycache__", ".pytest_cache",
  ".ruff_cache", "node_modules", "dist", "build", "coverage",
  ".mypy_cache", ".hypothesis", ".obsidian",
]);
const EXCLUDED_SUFFIXES = new Set([".min.js", ".min.css", ".map", ".d.ts"]);
const TS_SUFFIX = ".ts";

const FS_WRITE = new Set([
  "writeFileSync", "writeFile", "appendFileSync", "appendFile",
  "renameSync", "rename", "copyFileSync", "copyFile", "rmSync", "rm",
  "unlinkSync", "unlink",
]);
const FS_MODULES = new Set(["fs", "fs/promises", "node:fs", "node:fs/promises"]);
const SPAWN = new Set([
  "execSync", "exec", "spawn", "spawnSync", "fork", "execFileSync",
  "execFile",
]);
const SPAWN_MODULES = new Set(["child_process", "node:child_process"]);

function sha256(payload) {
  const crypto = require("crypto");
  return "sha256:" + crypto.createHash("sha256").update(payload, "utf8").digest("hex");
}

function discover(rootDir) {
  const out = [];
  function walk(dir) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      if (entry.isDirectory()) {
        if (EXCLUDED_DIRS.has(entry.name)) continue;
        if (/tests?$/i.test(entry.name) || /^test_assets?$/i.test(entry.name)) continue;
        walk(path.join(dir, entry.name));
      } else if (entry.isFile()) {
        if (!entry.name.endsWith(TS_SUFFIX)) continue;
        if (EXCLUDED_SUFFIXES.has(path.extname(entry.name))) continue;
        if (entry.name === "main.js") continue;
        out.push(path.join(dir, entry.name));
      }
    }
  }
  walk(rootDir);
  return out;
}

function posix(rel) {
  return rel.split(path.sep).join("/");
}

function buildIndex(source, ts) {
  const aliases = {};
  const direct = {};
  const sf = ts.createSourceFile("x.ts", source, ts.ScriptTarget.Latest, true);
  function visit(node) {
    if (ts.isImportDeclaration(node)) {
      const mod = node.moduleSpecifier.text;
      if (!mod.startsWith(".")) {
        const names = [];
        for (const clause of node.importClause ? [node.importClause] : []) {
          if (clause.name) names.push({ imported: "default", local: clause.name.text });
          if (clause.namedBindings) {
            if (ts.isNamespaceImport(clause.namedBindings)) {
              aliases[clause.namedBindings.name.text] = mod;
            } else {
              for (const el of clause.namedBindings.elements) {
                names.push({
                  imported: el.propertyName ? el.propertyName.text : el.name.text,
                  local: el.name.text,
                });
              }
            }
          }
        }
        for (const n of names) direct[n.local] = `${mod}.${n.imported}`;
      }
    }
    ts.forEachChild(node, visit);
  }
  visit(sf);
  return { aliases, direct };
}

function resolveCall(func, ts, index) {
  if (ts.isIdentifier(func)) {
    return index.direct[func.text] || index.aliases[func.text] || null;
  }
  if (ts.isPropertyAccessExpression(func)) {
    let expr = func;
    const parts = [];
    while (expr && ts.isPropertyAccessExpression(expr)) {
      parts.unshift(expr.name.text);
      expr = expr.expression;
    }
    if (expr && ts.isIdentifier(expr)) {
      const base = index.aliases[expr.text] || index.direct[expr.text] || expr.text;
      return [base, ...parts].join(".");
    }
    return null;
  }
  return null;
}

function main() {
  const args = process.argv.slice(2);
  const rootDir = args[0];
  const registryPath = args[1] || null;
  if (!rootDir) {
    console.error("usage: collect_ts.js <root> [wrapper-registry.json]");
    process.exit(2);
  }
  let ts;
  try {
    ts = require("typescript");
  } catch (err) {
    // The compiler ships inside the plugin's dependency tree; resolve it
    // relative to this script's repository location when not on the module path.
    try {
      const candidates = [
        path.resolve(__dirname, "../../plugin/node_modules/typescript"),
        path.resolve(__dirname, "../../../plugin/node_modules/typescript"),
      ];
      for (const candidate of candidates) {
        try {
          ts = require(candidate);
          break;
        } catch (_) {
          /* try next */
        }
      }
      if (!ts) throw err;
    } catch (fallbackErr) {
      console.error("typescript compiler unavailable: " + fallbackErr.message);
      process.exit(3);
    }
  }
  let registry = [];
  if (registryPath) {
    registry = JSON.parse(fs.readFileSync(registryPath, "utf8"));
  }
  const files = discover(path.resolve(rootDir));
  const facts = [];
  const parseErrors = [];
  const scanned = [];
  const wrapperHits = [];

  for (const file of files) {
    const rel = posix(path.relative(rootDir, file));
    let source;
    try {
      source = fs.readFileSync(file, "utf8");
    } catch (err) {
      parseErrors.push(`${rel}: ${err.message}`);
      continue;
    }
    scanned.push([rel, sha256(source)]);
    const sf = ts.createSourceFile(rel, source, ts.ScriptTarget.Latest, true);
    const index = buildIndex(source, ts);
    const symbol = rel.replace(/\//g, ".").replace(/\.ts$/, "");

    function evidence(node, confidence, extractor) {
      const start = node.getStart(sf, false);
      const end = node.getEnd();
      const lineStart = sf.getLineAndCharacterOfPosition(start).line + 1;
      const lineEnd = sf.getLineAndCharacterOfPosition(end).line + 1;
      return {
        file: rel,
        file_digest: sha256(source),
        symbol,
        line_start: lineStart,
        line_end: lineEnd,
        extractor: extractor || "typescript_compiler",
        epistemic_status: "observed_static",
        confidence: confidence || "exact",
      };
    }

    function addFact(fact) {
      facts.push(fact);
    }

    function visit(node) {
      if (ts.isCallExpression(node)) {
        const qualified = resolveCall(node.expression, ts, index);
        if (qualified) {
          const tail = qualified.split(".").pop();
          const head = qualified.split(".")[0];
          let matched = false;
          for (const spec of registry) {
            if (qualified.endsWith(spec.qualified_name)) {
              wrapperHits.push({
                wrapper_id: spec.wrapper_id,
                file: rel,
                line: sf.getLineAndCharacterOfPosition(node.getStart(sf, false)).line + 1,
                qualified_name: spec.qualified_name,
                version: spec.version,
              });
              const ev = evidence(node, spec.confidence || "exact");
              for (const f of spec.facts) {
                if (f.kind === "effect") {
                  addFact({
                    kind: "effect",
                    operation_id: operationId(rel, symbol),
                    effect_kind: f.effect_kind,
                    ...(f.intent_mode ? { intent_mode: f.intent_mode } : {}),
                    evidence: ev,
                  });
                } else if (f.kind === "write") {
                  addFact({
                    kind: "canonical_write",
                    unit_id: f.unit_id,
                    actor_kind: f.actor_kind || "backend",
                    via_publication_protocol: !!f.via_publication_protocol,
                    ...(f.writer_id ? { writer_id: f.writer_id } : {}),
                    ...(f.publication_authority ? { publication_authority: f.publication_authority } : {}),
                    evidence: ev,
                  });
                } else if (f.kind === "signal") {
                  addFact({
                    kind: "signal",
                    signal_id: f.signal_id,
                    producer: f.producer,
                    consumer_kind: f.consumer_kind,
                    has_code_consumer: !!f.has_code_consumer,
                    ...(f.consumer ? { consumer: f.consumer } : {}),
                    evidence: ev,
                  });
                }
              }
              matched = true;
              break;
            }
          }
          if (!matched) {
            if (SPAWN_MODULES.has(head) && SPAWN.has(tail)) {
              addFact({
                kind: "unresolved",
                unresolved_id: `unresolved:${rel}:${sf.getLineAndCharacterOfPosition(node.getStart(sf, false)).line + 1}`,
                expression: qualified,
                reason: `child_process ${qualified} — remote effect; intent not statically determinable`,
                possible_effects: ["remote_operation", "business_mutation"],
                evidence: evidence(node, "low"),
                epistemic_status: "unresolved",
              });
            } else if (FS_MODULES.has(head) && FS_WRITE.has(tail)) {
              addFact({
                kind: "effect",
                operation_id: operationId(rel, symbol),
                effect_kind: "business_mutation",
                evidence: evidence(node),
              });
            }
          }
        } else {
          // Unresolvable receiver. Only genuinely dynamic targets get
          // recorded as unresolved: indexed member access, results of calls,
          // or constructors. Plain `this.x()` / `obj.x()` are static and stay
          // silent (they match no sink without wrapper knowledge).
          const expr = node.expression;
          const dynamic =
            ts.isElementAccessExpression(expr) ||
            ts.isCallExpression(expr) ||
            ts.isNewExpression(expr);
          if (dynamic) {
            addFact({
              kind: "unresolved",
              unresolved_id: `unresolved:${rel}:${sf.getLineAndCharacterOfPosition(node.getStart(sf, false)).line + 1}`,
              expression: expr.getText(sf).slice(0, 120),
              reason: "dynamic call target; cannot enumerate effects",
              possible_effects: ["remote_operation", "business_mutation"],
              evidence: evidence(node, "low"),
              epistemic_status: "unresolved",
            });
          }
        }
      }
      ts.forEachChild(node, visit);
    }
    visit(sf);
  }

  function operationId(rel, symbol) {
    // operation scoping is orchestrated from the Python side; the script
    // emits module-stem ids and the orchestrator re-scopes when needed.
    return symbol;
  }

  process.stdout.write(JSON.stringify({ facts, parse_errors: parseErrors, scanned, wrapper_hits: wrapperHits }));
}

main();
