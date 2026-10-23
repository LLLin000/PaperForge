// A01 old-baseline orchestrator (item 9): runs ONLY when the new-baseline
// result shows the HISTORICAL renderer disconnect — never on generic
// harness/pip failure, never automatically. Restores WAN for the old
// package-prefetch, re-applies the egress gate inside a01-run.mjs, then
// runs the old A01 attempt.
//
//   node scripts/diagnostics/a01-run-old-if-needed.mjs
//
// Reads a01-artifacts/result-new.json; exits 0 with a skip note unless
// rendererFailure===true. Generic new failures => no old run, no retry.
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const ART = join(REPO_ROOT, "a01-artifacts");

let fresh = null;
try {
  fresh = JSON.parse(readFileSync(join(ART, "result-new.json"), "utf8"));
} catch {
  mkdirSync(join(ART, "cells", "old"), { recursive: true });
  writeFileSync(join(ART, "result-old.json"), JSON.stringify({
    tag: "old", ok: false, stage: "harness-blocked",
    note: "result-new.json missing/unreadable: old baseline not attempted",
    ts: new Date().toISOString(),
  }, null, 2));
  console.log(JSON.stringify({ tag: "old", stage: "harness-blocked" }));
  process.exit(0);
}
if (!fresh.rendererFailure) {
  mkdirSync(join(ART, "cells", "old"), { recursive: true });
  writeFileSync(join(ART, "result-old.json"), JSON.stringify({
    tag: "old", ok: false, stage: "skipped",
    note: `new-baseline stage=${fresh.stage} without renderer disconnect: old baseline not attempted (no auto-retry)`,
    ts: new Date().toISOString(),
  }, null, 2));
  console.log(JSON.stringify({ tag: "old", stage: "skipped" }));
  process.exit(0);
}
// WAN restored for the old package-prefetch only (this orchestrator runs
// outside the egress gate); a01-run.mjs re-applies the gate itself.
for (const k of ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]) delete process.env[k];
delete process.env.PIP_NO_INDEX;
const pre = spawnSync(process.execPath, [join(REPO_ROOT, "scripts", "diagnostics", "a01-prefetch.mjs"), "old"], { cwd: REPO_ROOT, encoding: "utf8", timeout: 1800000, stdio: "inherit" });
if (pre.status !== 0) {
  console.log(JSON.stringify({ tag: "old", stage: "prefetch-blocked" }));
  process.exit(1);
}
const run = spawnSync(process.execPath, [join(REPO_ROOT, "scripts", "diagnostics", "a01-run.mjs"), "old"], { cwd: REPO_ROOT, encoding: "utf8", timeout: 900000, stdio: "inherit" });
process.exit(run.status ?? 1);
