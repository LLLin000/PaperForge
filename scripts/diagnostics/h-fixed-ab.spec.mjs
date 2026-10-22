// Fixed-host A/B boot probe spec (4 cells: old/new x plugin-on/off).
// Run once per cell via the h-fixed-ab.mjs harness (NOT via wdio testrunner).
//
// Per-cell flow:
//   1. Called AFTER startWdioSession (copy:true on a fresh GENERATED vault);
//      the harness pre-seeded data.json autoSyncEnabled:false in the stage
//      plugin dir BEFORE the session (the service copies it into the vault)
//      and verified propagation against the actual copied path.
//   2. Assert obsidian/app versions, git ref, and bundle hashes.
//   3. Fresh-boot observation gate: renderer reachable, workspace responsive,
//      autoSync provably idle (poll timer null, no operation active).
//   4. plugin-state assertion: on-cells require app.plugins.plugins.paperforge
//      present AND enabled; off-cells require it absent. Mismatch = failed.
//   5. Emit result.json: { cell, verdict: "pass"|"failed"|"blocked", ... }.
//      A renderer crash / unreachable CDP is verdict "failed" with evidence —
//      never an exception that skips remaining cells.
//
// Exposes probe(browser, ctx) for the harness; the thin mocha wrapper is
// only for local `wdio run` debugging and is NOT used in CI.

import { strict as assert } from "node:assert";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";

function sha256File(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function writeResult(ctx, verdict, evidence) {
  const out = {
    cell: ctx.cell,
    verdict,
    errorStage: evidence.errorStage ?? (verdict === "pass" ? null : "probe"),
    ref: ctx.ref,
    refFull: ctx.refFull,
    pluginOn: ctx.pluginOn,
    appVersion: evidence.appVersion ?? null,
    installerVersion: evidence.installerVersion ?? null,
    electronVersion: evidence.electronVersion ?? null,
    chromeVersion: evidence.chromeVersion ?? null,
    pinnedElectron: evidence.pinnedElectron ?? null,
    pinnedChrome: evidence.pinnedChrome ?? null,
    mainJsSha256: evidence.mainJsSha256 ?? null,
    manifestSha256: evidence.manifestSha256 ?? null,
    bundleSource: evidence.bundleSource ?? null,
    lockfileSha256: ctx.lockfileSha256 ?? null,
    hostPins: evidence.hostPins ?? null,
    bootReachable: evidence.bootReachable ?? false,
    rendererResponsive: evidence.rendererResponsive ?? false,
    layoutReady: evidence.layoutReady ?? false,
    autosyncIdle: evidence.autosyncIdle ?? null,
    backendPointer: evidence.backendPointer ?? null,
    copiedVault: ctx.copiedVault ?? null,
    dataJsonSeeded: ctx.dataJsonSeeded ?? null,
    pointerAbsent: ctx.pointerAbsent ?? null,
    pluginState: evidence.pluginState ?? null,
    setupFailure: evidence.setupFailure ?? null,
    error: evidence.error ?? null,
    windowsAppCrashEvents: evidence.windowsAppCrashEvents ?? null,
    notes: evidence.notes ?? [],
    ts: new Date().toISOString(),
  };
  mkdirSync(ctx.artifactsDir, { recursive: true });
  writeFileSync(join(ctx.artifactsDir, "result.json"), JSON.stringify(out, null, 2));
  return out;
}

export async function probe(browser, ctx) {
  const evidence = { notes: [], hostPins: null };
  try {
    // 1. Version pins: fixed host contract.
    evidence.appVersion = await browser.getObsidianVersion();
    evidence.installerVersion = await browser.getObsidianInstallerVersion();
    assert.equal(evidence.appVersion, "1.14.4", `appVersion mismatch: ${evidence.appVersion}`);
    assert.equal(evidence.installerVersion, "1.5.8", `installerVersion mismatch: ${evidence.installerVersion}`);

    // 1b. Host/toolchain pins recorded by prefetch (launcher/service/WDIO/
    // driver + runner image), so the evidence stands alone.
    evidence.hostPins = ctx.versions ?? null;
    if (ctx.versions?.driver == null) {
      evidence.notes.push("driver version string unavailable; driver binary hash remains the pin");
    }
    if (ctx.versions?.launcher == null || ctx.versions?.service == null) {
      evidence.notes.push("launcher/service version unavailable; recorded as null, not assumed");
    }

    // 2. Identity: binary/process versions must EQUAL the prefetch pins —
    //    null is failure, never accepted. Bundle hashes of the built plugin.
    const versions = await browser.executeObsidian(() => ({
      electron: typeof process !== "undefined" ? process.versions?.electron ?? null : null,
      chrome: typeof process !== "undefined" ? process.versions?.chrome ?? null : null,
    }));
    evidence.electronVersion = versions?.electron ?? null;
    evidence.chromeVersion = versions?.chrome ?? null;
    evidence.pinnedElectron = ctx.versions?.electron ?? null;
    evidence.pinnedChrome = ctx.versions?.chrome ?? null;
    assert.ok(evidence.electronVersion, `electron version unreadable (pinned ${evidence.pinnedElectron})`);
    assert.ok(evidence.chromeVersion, `chrome version unreadable (pinned ${evidence.pinnedChrome})`);
    assert.equal(evidence.electronVersion, evidence.pinnedElectron, `electron mismatch: got ${evidence.electronVersion}, pinned ${evidence.pinnedElectron}`);
    assert.equal(evidence.chromeVersion, evidence.pinnedChrome, `chrome mismatch: got ${evidence.chromeVersion}, pinned ${evidence.pinnedChrome}`);
    assert.ok(/^120\./.test(String(evidence.chromeVersion)), `chrome is not 120.x: ${evidence.chromeVersion}`);
    evidence.mainJsSha256 = sha256File(ctx.builtMainJs);
    evidence.manifestSha256 = sha256File(ctx.builtManifest);
    evidence.bundleSource = ctx.ref;
    evidence.notes.push(`bundle built from ${ctx.refFull} (git archive, no baseline mutation)`);
    evidence.notes.push(`copied vault: ${ctx.copiedVault} (fresh=${ctx.copiedVaultIsFresh}, data.json seeded=${ctx.dataJsonSeeded}, pointer absent=${ctx.pointerAbsent})`);

    // 3. Fresh-boot observation gate: renderer reachable AND workspace
    //    layoutReady AND responsive — all asserted, none merely recorded.
    evidence.bootReachable = true;
    const responsive = await browser.executeObsidian(({ app }) => ({
      workspaceReady: app?.workspace != null,
      layoutReady: !!(app?.workspace?.layoutReady),
    }));
    evidence.rendererResponsive = !!(responsive && responsive.workspaceReady);
    evidence.layoutReady = !!(responsive && responsive.layoutReady);
    evidence.notes.push(`workspace: ${JSON.stringify(responsive)}`);
    assert.ok(evidence.rendererResponsive, `renderer not responsive: ${JSON.stringify(responsive)}`);
    assert.ok(evidence.layoutReady, `workspace layout not ready: ${JSON.stringify(responsive)}`);
    const idle = await browser.executeObsidian(({ app }) => {
      const plugin = app?.plugins?.plugins?.paperforge ?? app?.plugins?.getPlugin?.("paperforge") ?? null;
      if (!plugin) return { hasPlugin: false, pollTimerNull: null, autoSyncRunning: null, operationActive: null, pythonCommand: "n/a-off" };
      let pythonCommand = "unknown";
      try {
        pythonCommand = plugin._getPythonCommand() == null ? null : "RESOLVED";
      } catch (e) {
        pythonCommand = `threw:${String(e?.message ?? e).slice(0, 60)}`;
      }
      let operationActive = "unknown";
      try {
        const client = typeof plugin.getClient === "function" ? plugin.getClient() : null;
        operationActive = typeof client?.isOperationActive === "function" ? client.isOperationActive() === false : "unknown";
      } catch (e) {
        operationActive = `threw:${String(e?.message ?? e).slice(0, 60)}`;
      }
      return {
        hasPlugin: true,
        pollTimerNull: plugin._pollTimer === null || plugin._pollTimer === undefined ? true : false,
        autoSyncRunning: plugin._autoSyncRunning === false ? true : false,
        operationActive,
        pythonCommand,
      };
    });
    if (ctx.pluginOn) {
      evidence.autosyncIdle = !!(idle.pollTimerNull && idle.autoSyncRunning && idle.operationActive === true);
      evidence.notes.push(`autosync idle: ${JSON.stringify(idle)}`);
      assert.ok(evidence.autosyncIdle, `autoSync not idle in on-cell: ${JSON.stringify(idle)}`);
      evidence.backendPointer = idle.pythonCommand;
      assert.strictEqual(idle.pythonCommand, null, `on-cell backend pointer must be unavailable, got: ${JSON.stringify(idle.pythonCommand)}`);
    } else {
      evidence.autosyncIdle = idle.hasPlugin === false ? null : false;
      evidence.notes.push(`off-cell plugin probe: ${JSON.stringify(idle)}`);
      evidence.backendPointer = idle.pythonCommand ?? null;
      assert.ok(idle.hasPlugin === false, `off-cell must have no paperforge instance: ${JSON.stringify(idle)}`);
    }
    const pluginState = await browser.executeObsidian(({ app }) => {
      const plugins = app?.plugins;
      if (!plugins) return { present: false, enabled: "unknown" };
      const entry = plugins.plugins?.paperforge ?? null;
      return {
        present: entry != null,
        enabled: typeof plugins.enabledPlugins?.has === "function"
          ? plugins.enabledPlugins.has("paperforge")
          : (plugins.enabledPlugins?.includes?.("paperforge") ?? "unknown"),
      };
    });
    evidence.pluginState = pluginState;
    if (ctx.pluginOn) {
      assert.ok(pluginState.present, "plugin-on cell: paperforge plugin absent from app.plugins.plugins");
      assert.strictEqual(pluginState.enabled, true, "plugin-on cell: paperforge not in enabledPlugins");
    } else {
      assert.ok(!pluginState.present, "plugin-off cell: paperforge plugin unexpectedly present");
    }

    writeResult(ctx, "pass", evidence);
  } catch (err) {
    evidence.error = String(err?.stack ?? err);
    writeResult(ctx, "failed", evidence);
  }
}

// Thin mocha wrapper for local debugging only (wdio testrunner path).
export function registerMocha(ctx) {
  describe(`h-fixed-ab ${ctx.cell}`, function () {
    it("fixed boot observation", async function () {
      await probe(globalThis.browser, ctx);
      const result = JSON.parse(readFileSync(join(ctx.artifactsDir, "result.json"), "utf8"));
      assert.notEqual(result.verdict, "blocked", `setup failure: ${result.setupFailure ?? result.error}`);
      assert.equal(result.verdict, "pass", `probe failed: ${result.error}`);
    });
  });
}
