// A01/full-H overlay WDIO config: reuses the ORIGINAL production config
// module (./wdio.conf.mts) WITHOUT modifying it, then merges only the
// diagnostic deltas: pinned host binaries, pinned cacheDir, grep/bail, and
// pre-teardown evidence hooks. No product hooks/flags added.
// PF_DIAGNOSTIC_H_FULL=1 (diagnostic-only): full original suite, no grep,
// bail on first failure. Default: exact A01 grep. Base PF_E2E_GREP dropped.
//
// Installed as <staged-plugin>/wdio.a01.mts (imports ./wdio.conf.mts, so it
// must keep the .mts extension); run with cwd=<staged-plugin> via the
// original WDIO testrunner: `wdio run ./wdio.a01.mts`.
// Original spec/case assertions and A01 timeouts (600000/540000) untouched.
import { execFileSync } from "node:child_process";
import { cpSync, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { config as base } from "./wdio.conf.mts";

export const FULL_MODE = process.env.PF_DIAGNOSTIC_H_FULL === "1";
export const A01_TITLE =
  "installs and publishes the runtime through the first-use setup journey";

const ART = process.env.A01_ARTIFACTS_DIR ?? join(tmpdir(), "a01-overlay-art");
mkdirSync(ART, { recursive: true });

const pins = JSON.parse(readFileSync(process.env.A01_HOST_PINS ?? "", "utf8"));

function userDataDirFrom(browser) {
  try {
    // Contract: prefer the ACTUAL browser.capabilities.chrome.userDataDir
    // direct field (no renderer needed), then the merged launch args.
    const direct = browser?.capabilities?.chrome?.userDataDir ?? null;
    if (typeof direct === "string" && direct.length > 0) return direct;
    const pools = [
      browser?.capabilities?.["goog:chromeOptions"]?.args ?? [],
      browser?.requestedCapabilities?.["goog:chromeOptions"]?.args ?? [],
    ];
    for (const args of pools) {
      const hit = (args ?? []).find((a) => String(a).startsWith("--user-data-dir="));
      if (hit) return String(hit).slice("--user-data-dir=".length);
    }
    return null;
  } catch {
    return null;
  }
}

function werSnapshot() {
  try {
    const out = execFileSync(
      "powershell",
      [
        "-NoProfile",
        "-Command",
        "$ErrorActionPreference='Stop'; try { " +
          "$events=@(Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Application Error','Application Hang'; ID=1000,1002; StartTime=(Get-Date).AddHours(-6)} -ErrorAction Stop | Select-Object -First 20 TimeCreated,ProviderName,Id,Message); " +
          "@{queried=$true;count=$events.Count;events=$events;error=$null} | ConvertTo-Json -Depth 4 " +
          "} catch { if ($_.FullyQualifiedErrorId -like 'NoMatchingEventsFound*') { " +
          "@{queried=$true;count=0;events=@();error=$null} | ConvertTo-Json " +
          "} else { @{queried=$false;count=0;events=@();error=$_.Exception.Message} | ConvertTo-Json } }",
      ],
      { encoding: "utf8", timeout: 60000 }
    );
    return JSON.parse(out);
  } catch (err) {
    return { queried: false, count: 0, events: null, error: String(err?.message ?? err).slice(0, 300) };
  }
}

// Inner-UI command journal (metadata only: commandName, start/end, error
// presence — no args/payloads). Streams to command-journal.jsonl; the
// fail-first record distinguishes callback vs wait phases by command name.
const cmdStack = [];
function journalCommand(phase, commandName, error) {
  try {
    const line = phase === "before"
      ? { phase, command: String(commandName), start: new Date().toISOString() }
      : { phase, command: String(commandName), end: new Date().toISOString(), error: error ? String(error?.message ?? error).slice(0, 200) : null };
    if (phase === "before") cmdStack.push(line);
    else {
      const open = [...cmdStack].reverse().find((e) => e.command === String(commandName) && !e.closed);
      if (open) { open.closed = true; line.start = open.start; }
    }
    writeFileSync(join(ART, "command-journal.jsonl"), JSON.stringify(line) + "\n", { flag: "a" });
  } catch { /* journal is best-effort */ }
}

async function afterTestHook(test, context, result) {
  // Runs BEFORE service teardown. A dead renderer may HANG a screenshot
  // call and lose all crash evidence, so durable work goes FIRST:
  // filesystem copies + WER + snapshot write, screenshot AFTER, then the
  // JSON is updated with the image attempt. No renderer needed for files.
  const snap = { test: test?.title ?? null, ts: new Date().toISOString() };
  const b = globalThis.browser ?? null;
  // Actual in-runtime version assert (not the requested config): record
  // observed app/installer versions + requested browserVersion.
  try {
    snap.actualAppVersion = await b?.getObsidianVersion().catch(() => null) ?? null;
    snap.actualInstallerVersion = await b?.getObsidianInstallerVersion?.().catch(() => null) ?? null;
  } catch {
    snap.actualAppVersion = snap.actualAppVersion ?? null;
    snap.actualInstallerVersion = snap.actualInstallerVersion ?? null;
  }
  snap.expectedAppVersion = pins.appVersion;
  snap.requestedBrowserVersion = caps.browserVersion;
  if (snap.actualAppVersion && snap.actualAppVersion !== pins.appVersion) {
    snap.versionMismatch = `actual ${snap.actualAppVersion} != pinned ${pins.appVersion}`;
  }
  try {
    const cfg = userDataDirFrom(b);
    if (cfg && existsSync(cfg)) {
      for (const name of ["Crashpad", "main.log"]) {
        const src = join(cfg, name);
        try {
          if (existsSync(src)) {
            if (statSync(src).isDirectory()) cpSync(src, join(ART, `config-${name}`), { recursive: true });
            else if (statSync(src).size <= 5 * 1024 * 1024) cpSync(src, join(ART, `config-${name}`));
            else snap[name] = "unavailable: exceeds 5MB cap";
            snap[name] = snap[name] ?? `copied: config-${name}`;
          } else snap[name] = "unavailable: not found";
        } catch (err) {
          snap[name] = `copy failed: ${String(err?.message ?? err).slice(0, 160)}`;
        }
      }
    } else {
      snap.config = "unavailable: userDataDir missing (NOT no-crash)";
    }
    try {
      const openVault =
        b?.requestedCapabilities?.["wdio:obsidianOptions"]?.openVault ?? null;
      snap.openVault = openVault;
    } catch {
      snap.openVault = null;
    }
  } catch (err) {
    snap.error = String(err?.stack ?? err).slice(0, 300);
  }
  snap.wer = werSnapshot();
  snap.screenshot = "pending: crash evidence written before image attempt";
  writeFileSync(join(ART, "a01-aftertest-snapshot.json"), JSON.stringify(snap, null, 2));
  try {
    await b?.saveScreenshot(join(ART, "a01-aftertest.png"));
    snap.screenshot = "a01-aftertest.png";
  } catch (err) {
    snap.screenshot = `unavailable: ${String(err?.message ?? err).slice(0, 160)}`;
  }
  writeFileSync(join(ART, "a01-aftertest-snapshot.json"), JSON.stringify(snap, null, 2));
  // FULL-H journal: every executed test title/outcome appended; the FIRST
  // failure snapshot is preserved (later successes never overwrite it).
  if (FULL_MODE) {
    try {
      const jPath = join(ART, "fullh-journal.json");
      let journal = [];
      try { journal = JSON.parse(readFileSync(jPath, "utf8")); } catch { journal = []; }
      journal.push({ test: snap.test, ts: snap.ts, userDataDir: snap.userDataDir ?? null, openVault: snap.openVault ?? null, screenshot: snap.screenshot ?? null });
      writeFileSync(jPath, JSON.stringify(journal, null, 2));
      if ((result?.error || result?.failed) && !existsSync(join(ART, "first-failure-snapshot.json"))) {
        cpSync(join(ART, "a01-aftertest-snapshot.json"), join(ART, "first-failure-snapshot.json"));
        try { cpSync(join(ART, "a01-aftertest.png"), join(ART, "first-failure.png")); } catch { /* image may be absent: not absence proof */ }
      }
    } catch { /* journal is best-effort */ }
  }
}
// Fallback AFTER the session (service teardown deletes config tmp dirs, so
// this cannot recover files): writes the snapshot ONLY if no snapshot file
// exists, so a beforeEach failure that skipped afterTest still leaves bound
// paths + WER before teardown. Never overwrites the afterTest snapshot.
async function afterHookFallback() {
  try {
    const target = join(ART, "a01-aftertest-snapshot.json");
    if (existsSync(target)) return;
    const b = globalThis.browser ?? null;
    const snap = {
      test: null,
      ts: new Date().toISOString(),
      hook: "after-missing-afterTest",
      userDataDir: userDataDirFrom(b),
      openVault: (() => { try { return b?.requestedCapabilities?.["wdio:obsidianOptions"]?.openVault ?? null; } catch { return null; } })(),
      wer: werSnapshot(),
      screenshot: "unavailable: afterTest never ran",
    };
    writeFileSync(target, JSON.stringify(snap, null, 2));
  } catch { /* best-effort only */ }
}

// FULL-H final pre-teardown fallback: refreshes the COMMON snapshot with
// the ACTUAL final profile/openVault (teardown-time truth for cleanup),
// even when earlier cases wrote snapshots. First-failure stays separate;
// the runner's finally reads the common file for bound markers.
async function afterHookFallbackFull() {
  try {
    const b = globalThis.browser ?? null;
    const snap = {
      test: null,
      ts: new Date().toISOString(),
      hook: "after-full-final",
      userDataDir: userDataDirFrom(b),
      openVault: (() => { try { return b?.requestedCapabilities?.["wdio:obsidianOptions"]?.openVault ?? null; } catch { return null; } })(),
      wer: werSnapshot(),
      screenshot: "unavailable: final fallback takes no image",
    };
    writeFileSync(join(ART, "fullh-final-snapshot.json"), JSON.stringify(snap, null, 2));
    writeFileSync(join(ART, "a01-aftertest-snapshot.json"), JSON.stringify(snap, null, 2));
  } catch { /* best-effort only */ }
}

const caps = JSON.parse(JSON.stringify(base.capabilities[0]));
caps.browserVersion = pins.appVersion;
caps["wdio:obsidianOptions"] = {
  ...caps["wdio:obsidianOptions"],
  appVersion: pins.appVersion,
  installerVersion: pins.installerVersion,
  binaryPath: pins.binaryPath,
  appPath: pins.appPath,
};
caps["wdio:chromedriverOptions"] = {
  ...(caps["wdio:chromedriverOptions"] ?? {}),
  binary: pins.driverPath,
};

// FULL mode: grep removed (original full-H suite), bail on first failure.
// A01 mode: exact A01 grep. Neither mode inherits a fine-grained grep.
const mochaBase = { ...base.mochaOpts };
delete mochaBase.grep;
export const config = {
  ...base,
  capabilities: [caps],
  cacheDir: process.env.A01_CACHE_DIR ?? base.cacheDir,
  mochaOpts: FULL_MODE
    ? { ...mochaBase, bail: true }
    : { ...mochaBase, grep: A01_TITLE },
  beforeCommand: async function (commandName) {
    if (typeof base.beforeCommand === "function") await base.beforeCommand.call(this, commandName);
    journalCommand("before", commandName);
  },
  afterCommand: async function (commandName, args, result, error) {
    if (typeof base.afterCommand === "function") await base.afterCommand.call(this, commandName, args, result, error);
    journalCommand("after", commandName, error);
  },
  afterTest: async function (test, context, result) {
    if (typeof base.afterTest === "function") await base.afterTest.call(this, test, context, result);
    await afterTestHook.call(this, test, context, result);
  },
  after: async function (result, capabilities, specs) {
    if (typeof base.after === "function") await base.after.call(this, result, capabilities, specs);
    if (FULL_MODE) await afterHookFallbackFull.call(this);
    else await afterHookFallback.call(this);
  },
};
