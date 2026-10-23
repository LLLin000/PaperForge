// Fixed-host reload-boundary hypothesis probe (4 cells: old/new x plugin-on/off).
// Scope (explicit): hypothesis test of the retry's proven reload boundary
// (service prepareApp -> reloadObsidian), NOT an exact A01 replay — the
// original 90s silence had no in-flight pass lines, so no exact known replay
// exists. A passing 90s observation does NOT claim root-found for A01.
// Run once per cell via the h-fixed-ab.mjs harness (NOT via wdio testrunner).
//
// Per-cell flow:
//   1. probeBoot (after startWdioSession on a fresh GENERATED vault): assert
//      obsidian/app versions, git ref, bundle hashes, renderer reachable,
//      workspace layoutReady, autosync idle, plugin present+enabled (on) or
//      absent (off). A renderer crash / unreachable CDP is "failed", never
//      an exception that skips remaining cells.
//   2. probeReloadBoundary (H-like runtime + fixture, exact copied vault):
//      browser.reloadObsidian() on the unchanged copied vault, then a 90s
//      dwell asserting the renderer stays reachable/responsive; disconnect
//      fails at stage "observation". Backend checks (installation probe +
//      backendVersion) distinguish a dead backend from a dead renderer.
//   3. Emits result.json: { cell, verdict: "pass"|"failed"|"blocked", ... }.
//
// Exposes probeBoot + probeReloadBoundary for the harness; the thin mocha
// wrapper is only for local `wdio run` debugging and is NOT used in CI.
//

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
    bootStage: evidence.bootStage ?? null,
    reloadStartedMs: evidence.reloadStartedMs ?? null,
    reloadReturnedMs: evidence.reloadReturnedMs ?? null,
    observationMs: evidence.observationMs ?? null,
    lastDwellSample: evidence.lastDwellSample ?? null,
    backendCapability: evidence.backendCapability ?? null,
    backendVersionObserved: evidence.backendVersionObserved ?? null,
    expectedRuntimeVersion: evidence.expectedRuntimeVersion ?? null,
    fixtureBuild: evidence.fixtureBuild ?? null,
    preReloadScreenshot: evidence.preReloadScreenshot ?? null,
    postReloadScreenshot: evidence.postReloadScreenshot ?? null,
    runtimeWheel: evidence.runtimeWheel ?? null,
    sourceSha: evidence.sourceSha ?? null,
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

export async function probeBoot(browser, ctx) {
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
      assert.strictEqual(idle.pythonCommand, "RESOLVED", `on-cell backend python must resolve via published pointer, got: ${JSON.stringify(idle.pythonCommand)}`);
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

    evidence.bootStage = "boot-ok";
    return evidence;
  } catch (err) {
    evidence.error = String(err?.stack ?? err);
    evidence.bootStage = "boot";
    writeResult(ctx, "failed", evidence);
    return null;
  }
}

// Stage 2 (H-like runtime + fixture, exact copied vault). Called AFTER
// probeBoot succeeded: reloadObsidian() on the unchanged copied vault, then
// a 90s dwell ({ observeMs }) asserting renderer reachability/responsiveness.
// Backend checks (installation probe + backendVersion) run inside the dwell
// window so a dead renderer is distinguishable from a dead backend.
// Returns null when the renderer died (result.json already failed at stage
// "observation"); otherwise the boot evidence object.
export async function probeReloadBoundary(browser, ctx, evidence, observeMs) {
  const tReloadStart = Date.now();
  try {
    evidence.reloadStartedMs = tReloadStart;
    evidence.errorStage = "reload";
    await browser.reloadObsidian();
    evidence.reloadReturnedMs = Date.now() - tReloadStart;
    const deadline = Date.now() + observeMs;
    let lastSample = null;
    let backend = null;
    for (;;) {
      evidence.errorStage = "observation";
      lastSample = await browser.executeObsidian(({ app }) => ({
        workspaceReady: app?.workspace != null,
        layoutReady: !!(app?.workspace?.layoutReady),
      }));
      assert.ok(lastSample?.workspaceReady, `renderer unreachable mid-dwell: ${JSON.stringify(lastSample)}`);
      assert.ok(lastSample?.layoutReady, `workspace layout not ready mid-dwell: ${JSON.stringify(lastSample)}`);
      if (ctx.pluginOn) {
        evidence.errorStage = "backend";
        backend = await browser.executeObsidian(async ({ app }) => {
          const plugin = app?.plugins?.plugins?.paperforge ?? null;
          if (!plugin) return { hasPlugin: false, capability: null, backend: null };
          const client = plugin.getClient();
          const probeEnv = await client.probe("installation");
          return {
            hasPlugin: true,
            capability: probeEnv?.capability_state ?? null,
            backend: await client.backendVersion(),
          };
        });
        evidence.backendCapability = backend?.capability ?? null;
        evidence.backendVersionObserved = backend?.backend ?? null;
        assert.ok(backend?.hasPlugin === true, `paperforge plugin missing after reload: ${JSON.stringify(backend)}`);
        assert.strictEqual(backend?.capability, "ready", `installation probe not ready after reload: ${JSON.stringify(backend)}`);
        assert.strictEqual(backend?.backend, ctx.expectedRuntimeVersion ?? evidence.expectedRuntimeVersion, `backend version mismatch after reload: got ${JSON.stringify(backend?.backend)}, want ${JSON.stringify(ctx.expectedRuntimeVersion ?? evidence.expectedRuntimeVersion)}`);
      }
      if (Date.now() >= deadline) break;
      await browser.pause(5000);
      evidence.errorStage = "observation";
    }
    evidence.observationMs = Date.now() - tReloadStart;
    evidence.lastDwellSample = lastSample;
    evidence.errorStage = null;
    writeResult(ctx, "pass", evidence);
    return evidence;
  } catch (err) {
    evidence.error = String(err?.stack ?? err);
    evidence.observationMs = Date.now() - tReloadStart;
    writeResult(ctx, "failed", evidence);
    return null;
  }
}

// Thin mocha wrapper for local debugging only (wdio testrunner path).
export function registerMocha(ctx) {
  describe(`h-fixed-ab ${ctx.cell}`, function () {
    it("fixed boot observation", async function () {
      const evidence = await probeBoot(globalThis.browser, ctx);
      assert.ok(evidence, "probeBoot failed without evidence; see result.json");
      assert.equal(evidence.bootStage, "boot-ok", `boot failed: ${evidence?.error ?? "unknown"}`);
    });
  });
}
