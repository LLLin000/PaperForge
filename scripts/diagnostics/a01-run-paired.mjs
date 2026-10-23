// Paired A01 orchestrator: SAME runner, SAME wheel/staged source, two arms
// (app 1.14.4 vs 1.14.5, installer 1.5.8 + pinned driver both). Fresh
// identical HOME/vault per arm (each run makes its own). No full-H, no old
// code, no retries. The second arm runs even if the first fails, provided
// the first arm's cleanup is confirmed; firewall rules are owned per-run.
//
//   node scripts/diagnostics/a01-run-paired.mjs [new|old]   (default: new)
import { spawnSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const ART = join(REPO_ROOT, "a01-artifacts");
const TAG = process.argv[2] ?? "new";

function armResultFile(arm) {
  return join(ART, `result-${TAG}-app${arm}.json`);
}
function armSummary(arm, status) {
  let payload = null;
  try { payload = JSON.parse(readFileSync(armResultFile(arm), "utf8")); } catch { payload = null; }
  return {
    status,
    ok: payload?.ok ?? null,
    stage: payload?.stage ?? null,
    rendererFailure: payload?.rendererFailure ?? null,
    failPhase: payload?.failPhase ?? null,
    callbackSource: payload?.callbackSource ?? null,
    note: payload?.note ?? payload?.error ?? null,
  };
}
function runArm(arm) {
  // Ordered before/after command timestamps (no credentials/payloads).
  const before = new Date().toISOString();
  const r = spawnSync(process.execPath, [join(REPO_ROOT, "scripts", "diagnostics", "a01-run.mjs"), TAG], {
    cwd: REPO_ROOT, encoding: "utf8", timeout: 900000, stdio: "inherit",
    // Force A01-only: a Full-H parent env must never leak into the pair.
    env: { ...process.env, A01_APP_ARM: arm, PF_DIAGNOSTIC_H_FULL: "0", PF_E2E_GREP: "" },
  });
  const after = new Date().toISOString();
  let payload = null;
  try { payload = JSON.parse(readFileSync(armResultFile(arm), "utf8")); } catch { payload = null; }
  if (payload) {
    payload.pairedBeforeCommand = before;
    payload.pairedAfterCommand = after;
    try { writeFileSync(armResultFile(arm), JSON.stringify(payload, null, 2)); } catch { /* best-effort */ }
  }
  return r.status ?? 1;
}

const summary = { tag: TAG, mode: "paired-a01", appArms: ["144", "145"], arms: {}, ts: "" };
const s144 = runArm("144");
let first = null;
try { first = JSON.parse(readFileSync(armResultFile("144"), "utf8")); } catch { first = null; }
summary.arms["144"] = armSummary("144", s144);
// Second arm runs even if the first failed — unless cleanup is unconfirmed.
let blocked = true;
try {
  blocked = first?.cleanup?.firewall !== "removed-own-rules-after-children-confirmed-stopped";
} catch { blocked = true; }
if (blocked) {
  summary.arms["145"] = { status: null, ok: false, stage: "harness-blocked", note: "first-arm cleanup unconfirmed: second arm not attempted" };
} else {
  const s145 = runArm("145");
  summary.arms["145"] = armSummary("145", s145);
}
summary.ts = new Date().toISOString();
// Pair verification: two independent receipts, distinct HOMEs, same wheel
// SHA, each matching its expected app version. Guard failure or null arm
// status exits nonzero — no false green; legit product fail still exits 1
// with artifacts always uploaded by the workflow.
try {
  const r144 = JSON.parse(readFileSync(armResultFile("144"), "utf8"));
  const r145 = JSON.parse(readFileSync(armResultFile("145"), "utf8"));
  summary.pairCheck = {
    distinctHomes: !!r144.isolatedHome && !!r145.isolatedHome && r144.isolatedHome !== r145.isolatedHome,
    sameWheel: !!r144.boundBaseline?.wheelSha256 && r144.boundBaseline.wheelSha256 === r145.boundBaseline?.wheelSha256,
    wheelSha256: r144.boundBaseline?.wheelSha256 ?? null,
    app144: r144.actualVersions?.app ?? null,
    app145: r145.actualVersions?.app ?? null,
    appMatch: r144.actualVersions?.app === "1.14.4" && r145.actualVersions?.app === "1.14.5",
    installerMatch: r144.actualVersions?.installer === "1.5.8" && r145.actualVersions?.installer === "1.5.8",
  };
} catch {
  summary.pairCheck = { error: "receipts unreadable" };
}
mkdirSync(join(ART, "cells"), { recursive: true });
writeFileSync(join(ART, `paired-summary-${TAG}.json`), JSON.stringify(summary, null, 2));
console.log(JSON.stringify(summary));
const bad = Object.values(summary.arms).some((a) => a.status !== 0 || a.ok !== true);
const checkBad = !summary.pairCheck || summary.pairCheck.error || !summary.pairCheck.distinctHomes || !summary.pairCheck.sameWheel || !summary.pairCheck.appMatch || !summary.pairCheck.installerMatch;
if (bad || checkBad) process.exit(1);
process.exit(0);
