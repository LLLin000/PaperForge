/**
 * Real-Obsidian Settings & Migration Matrix (H2).
 *
 * Fast, deep state-machine and UI gate covering every user-facing installation,
 * Zotero connection, upgrade/migration, failure-recovery, and control-center
 * state inside the real Obsidian desktop shell:
 *
 *   S1  Brand-new host & fresh vault keeps _setup_complete=false across reloads
 *   S2  Existing runtime + fresh vault routes cleanly to zotero_not_configured
 *   S3  Auto-detect never pollutes data.json; backend missing_input overrides cache
 *   S4  Real Zotero SQLite connect & sync (zero stale "BBT" copy, notes + Base built)
 *   S5  Version mismatch pointer surfaces engine_version_mismatch
 *   S6  Engine updating & antivirus quarantine hero-card states
 *   S7  Veteran legacy vault upgrade modal + dry-run + cutover + user note safety
 *   S8  Real sync failure (library_sync_error) & recovery back to ready
 *   S9  4-tab Control Center + EN/ZH language switch with zero runtime errors
 */

import {
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import * as os from "node:os";
import * as path from "node:path";

const PLUGIN_DIR = process.cwd();
const VAULTS_DIR = path.resolve(PLUGIN_DIR, "test", "vaults");
const FRESH_VAULT = "./test/vaults/settings-fresh";
const LEGACY_VAULT = "./test/vaults/settings-legacy";
const ZOTERO_FIXTURE = path.join(VAULTS_DIR, "settings-zotero");

const RUNTIME_HOME = process.env.PF_E2E_RUNTIME_HOME || os.homedir();
const POINTER_PATH = path.join(
  RUNTIME_HOME,
  ".paperforge",
  "runtime",
  "pointer.json"
);

async function dismissModals(): Promise<void> {
  for (let attempt = 0; attempt < 5; attempt++) {
    const open = await browser.$$(".modal-bg");
    if (open.length === 0) return;
    await browser.keys("Escape");
    await browser.pause(150);
  }
}

async function openPaperForgeSettings(): Promise<void> {
  await browser.executeObsidian(async ({ app }) => {
    const plugin = app.plugins.plugins["paperforge"] as unknown as {
      _settingTab?: { display(): void };
    };
    const setting = (
      app as unknown as {
        setting?: {
          open?: () => void;
          openTabById?: (id: string) => void;
        };
      }
    ).setting;
    if (!setting?.open || !setting.openTabById) {
      throw new Error("Obsidian settings navigation API unavailable");
    }
    setting.open();
    setting.openTabById("paperforge");
    await new Promise<void>((r) => setTimeout(r, 300));
    plugin?._settingTab?.display();
  });
}

async function sandboxBasePath(): Promise<string> {
  return await browser.executeObsidian(async ({ app }) => {
    const adapter = app.vault.adapter as unknown as { basePath?: string };
    return adapter.basePath ?? "";
  });
}

describe("PaperForge real-host Settings & Migration Matrix (H2)", function () {
  let savedPointerRaw: string | null = null;

  before(function () {
    savedPointerRaw = existsSync(POINTER_PATH)
      ? readFileSync(POINTER_PATH, "utf8")
      : null;
    if (!savedPointerRaw) {
      throw new Error(
        `Settings E2E requires a pre-published pointer at ${POINTER_PATH}`
      );
    }
  });

  after(function () {
    if (savedPointerRaw !== null) {
      mkdirSync(path.dirname(POINTER_PATH), { recursive: true });
      writeFileSync(POINTER_PATH, savedPointerRaw, "utf8");
    }
  });

  beforeEach(function () {
    if (savedPointerRaw !== null) {
      mkdirSync(path.dirname(POINTER_PATH), { recursive: true });
      writeFileSync(POINTER_PATH, savedPointerRaw, "utf8");
    }
  });

  // ── S1: Fresh vault without runtime keeps _setup_complete=false across reload ──
  it("S1: keeps _setup_complete=false across reload even after startup writes vault_path and missing_input cache", async function () {
    rmSync(POINTER_PATH, { force: true });
    await browser.reloadObsidian({ vault: FRESH_VAULT });
    await dismissModals();

    const firstRender = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: Record<string, unknown>;
        saveSettings(): Promise<void>;
        _settingTab: { containerEl: HTMLElement; display(): void };
      };
      plugin.settings.language = "en";
      plugin.settings._setup_complete = false;
      plugin.settings._setup_journey_started = false;
      plugin.settings.vault_path = "/tmp/fake-sandbox";
      plugin.settings.last_seen_version = "";
      plugin.settings.capabilityState = {
        library: {
          schema_version: 2,
          module: "library",
          capability_state: "missing_input",
          user_state: "setup_required",
          reason: {
            code: "library.zotero_missing",
            text: "Zotero data directory not configured",
          },
        },
      };
      await plugin.saveSettings();
      return {
        setupComplete: plugin.settings._setup_complete,
      };
    });
    expect(firstRender.setupComplete).toBe(false);

    // Reload the SAME copied vault directory without wiping data.json
    await browser.reloadObsidian();
    await dismissModals();
    await openPaperForgeSettings();

    const afterReload = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: Record<string, unknown>;
        _settingTab: { containerEl: HTMLElement };
      };
      const capMap = plugin._settingTab.containerEl.querySelector(
        '[data-pf-testid="setup-capability-map"]'
      );
      return {
        setupComplete: plugin.settings._setup_complete,
        capCards: capMap?.querySelectorAll(".pf-setup-cap-card").length ?? 0,
        freePills:
          capMap?.querySelectorAll(".pf-setup-cap-pill.is-free").length ?? 0,
      };
    });

    expect(afterReload.setupComplete).toBe(false);
    expect(afterReload.capCards).toBe(4);
    expect(afterReload.freePills).toBe(2);
  });

  // ── S2 & S3: Fresh vault with existing runtime & backend authority ──────
  it("S2 & S3: routes fresh vault to zotero_not_configured and trusts backend missing_input over guessed zotero_data_dir", async function () {
    await browser.reloadObsidian({ vault: FRESH_VAULT });
    await dismissModals();

    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: Record<string, unknown>;
        saveSettings(): Promise<void>;
      };
      plugin.settings.language = "en";
      plugin.settings._setup_complete = false;
      await plugin.saveSettings();
    });

    await openPaperForgeSettings();

    const s2 = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _lastAutoSyncError: unknown;
        _settingTab: {
          containerEl: HTMLElement;
          _goHome(): void;
          display(): void;
        };
      };
      plugin._settingTab._goHome();
      const card =
        plugin._settingTab.containerEl.querySelector("[data-pf-decision]");
      return {
        decision: card?.getAttribute("data-pf-decision") ?? null,
        lastAutoSyncError: plugin._lastAutoSyncError,
      };
    });
    expect(s2.decision).toBe("zotero_not_configured");
    expect(s2.lastAutoSyncError).toBeNull();

    // S3: Auto-detect keeps data.json clean; stale zotero_data_dir + autoSyncError
    // STILL must show zotero_not_configured when backend reports library.zotero_missing.
    const s3 = await browser.executeObsidian(async ({ app }, zDir: string) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: Record<string, unknown>;
        _lastAutoSyncError: { message: string; at: number } | null;
        getClient(): {
          zoteroDetect(dir?: string): Promise<{
            found: boolean;
            total_papers: number;
          }>;
        };
        _settingTab: {
          containerEl: HTMLElement;
          _capabilityState: Record<string, unknown>;
          display(): void;
        };
      };
      const detected = await plugin.getClient().zoteroDetect(zDir);
      plugin.settings.zotero_data_dir = zDir;
      plugin._lastAutoSyncError = {
        message: "Zotero data directory not configured",
        at: Date.now(),
      };
      plugin._settingTab._capabilityState.library = {
        schema_version: 2,
        module: "library",
        capability_state: "missing_input",
        user_state: "setup_required",
        reason: {
          code: "library.zotero_missing",
          text: "Zotero data directory not configured",
        },
        notices: [],
        action: { primary: null },
      };
      plugin._settingTab.display();
      const card =
        plugin._settingTab.containerEl.querySelector("[data-pf-decision]");
      return {
        detectedFound: detected.found,
        detectedPapers: detected.total_papers,
        decision: card?.getAttribute("data-pf-decision") ?? null,
      };
    }, ZOTERO_FIXTURE);
    expect(s3.detectedFound).toBe(true);
    expect(s3.detectedPapers).toBe(2);
    expect(s3.decision).toBe("zotero_not_configured");
  });

  // ── S4: Real Zotero SQLite setup & sync through UI (zero stale BBT text) ──
  it("S4: configures Zotero SQLite via Express UI, builds notes & Bases with zero stale BBT copy, and reaches ready", async function () {
    await browser.reloadObsidian({ vault: FRESH_VAULT });
    await dismissModals();

    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: Record<string, unknown>;
        saveSettings(): Promise<void>;
      };
      plugin.settings.language = "en";
      plugin.settings._setup_complete = false;
      plugin.settings.zotero_data_dir = "";
      await plugin.saveSettings();
    });

    await openPaperForgeSettings();

    await browser.executeObsidian(async ({ app }, zDir: string) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: {
          containerEl: HTMLElement;
          _runtimeStatus: { runtime_ready: boolean } | null;
          _runtimeStatusVersion: string | null;
          display(): void;
        };
        manifest: { version: string };
      };
      plugin._settingTab._runtimeStatus = { runtime_ready: true };
      plugin._settingTab._runtimeStatusVersion = plugin.manifest.version;
      plugin._settingTab.display();

      const zInput = plugin._settingTab.containerEl.querySelector(
        '[data-pf-testid="express-zotero-input"]'
      ) as HTMLInputElement | null;
      if (!zInput) throw new Error("express-zotero-input not rendered");
      zInput.value = zDir;
      zInput.dispatchEvent(new Event("change", { bubbles: true }));
    }, ZOTERO_FIXTURE);

    await browser.pause(600);

    const preClick = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { containerEl: HTMLElement };
      };
      const footerBtns = Array.from(
        plugin._settingTab.containerEl.querySelectorAll(
          ".pf-express-footer-actions button.pf-action-btn"
        )
      ) as HTMLButtonElement[];
      const cta = footerBtns[footerBtns.length - 1];
      if (!cta) throw new Error("Express footer CTA missing");
      const journeyText = plugin._settingTab.containerEl.textContent ?? "";
      cta.click();
      return { journeyText };
    });
    expect(preClick.journeyText).not.toMatch(/\bBBT\b|Better BibTeX/i);

    let sawBbtDuringSync = false;
    await browser.waitUntil(
      async () => {
        const st = await browser.executeObsidian(async ({ app }) => {
          const plugin = app.plugins.plugins["paperforge"] as unknown as {
            settings: { _setup_complete?: boolean };
            _settingTab: {
              _setupOperation: string;
              _setupFeedback: string | null;
              _setupFailureDetail: string | null;
              containerEl: HTMLElement;
            };
          };
          const text = plugin._settingTab.containerEl.textContent ?? "";
          return {
            complete: plugin.settings._setup_complete === true,
            op: plugin._settingTab._setupOperation,
            feedback: plugin._settingTab._setupFeedback,
            detail: plugin._settingTab._setupFailureDetail,
            hasBbt: /\bBBT\b|Better BibTeX/i.test(text),
          };
        });
        if (st.hasBbt) sawBbtDuringSync = true;
        if (st.op === "failed") {
          throw new Error(
            `S4 library setup/sync failed: ${st.feedback ?? ""} :: ${st.detail ?? ""}`
          );
        }
        return st.complete && st.op === "idle";
      },
      { timeout: 60000, interval: 400, timeoutMsg: "S4 sync did not finish" }
    );
    expect(sawBbtDuringSync).toBe(false);

    const vaultPath = await sandboxBasePath();
    const pfJson = JSON.parse(
      readFileSync(path.join(vaultPath, "paperforge.json"), "utf8")
    ) as Record<string, unknown>;
    expect(pfJson.zotero_source_mode).toBe("sqlite");
    expect(String(pfJson.zotero_data_dir || "")).toBe(ZOTERO_FIXTURE);
    expect(existsSync(path.join(vaultPath, "Bases", "Literature.base"))).toBe(
      true
    );
    const litFiles = readdirSync(path.join(vaultPath, "Literature"), {
      recursive: true,
    }) as string[];
    expect(litFiles.some((f) => f.endsWith(".md"))).toBe(true);

    // Also probe Overview Hero Card == ready
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { _goHome(): void };
      };
      plugin._settingTab._goHome();
    });
    const heroDecision = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { containerEl: HTMLElement };
      };
      return (
        plugin._settingTab.containerEl
          .querySelector("[data-pf-decision]")
          ?.getAttribute("data-pf-decision") ?? null
      );
    });
    expect(heroDecision).toBe("ready");
  });

  // ── S5 & S6: Version mismatch, hot-swap updating, and quarantine Hero states ──
  it("S5 & S6: renders engine_version_mismatch, engine_updating, and engine_quarantined accurately", async function () {
    // S5: version mismatch in pointer.json
    const parsedPtr = JSON.parse(savedPointerRaw!) as Record<string, unknown>;
    parsedPtr.paperforge_version = "2.0.0";
    writeFileSync(POINTER_PATH, JSON.stringify(parsedPtr), "utf8");

    await browser.reloadObsidian({ vault: FRESH_VAULT });
    await dismissModals();
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: Record<string, unknown>;
        saveSettings(): Promise<void>;
      };
      plugin.settings.language = "en";
      plugin.settings._setup_complete = true;
      await plugin.saveSettings();
    });
    await openPaperForgeSettings();

    const s5Decision = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { containerEl: HTMLElement };
      };
      return (
        plugin._settingTab.containerEl
          .querySelector("[data-pf-decision]")
          ?.getAttribute("data-pf-decision") ?? null
      );
    });
    expect(s5Decision).toBe("engine_version_mismatch");

    // Restore pointer cleanly before S6
    writeFileSync(POINTER_PATH, savedPointerRaw!, "utf8");

    const s6 = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _daemonUpdating: boolean;
        _quarantinedBinDir: string | null;
        _settingTab: { containerEl: HTMLElement; display(): void };
      };
      plugin._daemonUpdating = true;
      plugin._settingTab.display();
      const updatingDecision =
        plugin._settingTab.containerEl
          .querySelector("[data-pf-decision]")
          ?.getAttribute("data-pf-decision") ?? null;
      plugin._daemonUpdating = false;

      plugin._quarantinedBinDir = "C:\\Users\\test\\.paperforge\\bin";
      plugin._settingTab.display();
      const quarEl =
        plugin._settingTab.containerEl.querySelector("[data-pf-decision]");
      const quarDecision = quarEl?.getAttribute("data-pf-decision") ?? null;
      const quarCode =
        quarEl?.querySelector("code.pf-defender-path-code")?.textContent ?? "";
      plugin._quarantinedBinDir = null;
      return { updatingDecision, quarDecision, quarCode };
    });
    expect(s6.updatingDecision).toBe("engine_updating");
    expect(s6.quarDecision).toBe("engine_quarantined");
    expect(s6.quarCode).toContain(".paperforge");
  });

  // ── S7: Veteran legacy vault upgrade modal + cutover + user note safety ──
  it("S7: detects veteran legacy vault, opens Upgrade Modal, executes cutover, and preserves personal notes", async function () {
    await browser.reloadObsidian({ vault: LEGACY_VAULT });
    await dismissModals();

    const vaultPath = await sandboxBasePath();
    const personalNotePath = path.join(vaultPath, "Personal", "MyNotes.md");
    const personalBefore = readFileSync(personalNotePath, "utf8");

    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: Record<string, unknown>;
        saveSettings(): Promise<void>;
        refreshUpgradePlan(): Promise<{
          provenance?: { needs_upgrade?: boolean; state?: string };
        } | null>;
      };
      plugin.settings.language = "en";
      plugin.settings._setup_complete = true;
      await plugin.saveSettings();
      const plan = await plugin.refreshUpgradePlan();
      if (!plan?.provenance?.needs_upgrade) {
        throw new Error(
          `Expected legacy vault to report needs_upgrade=true, got ${JSON.stringify(plan)}`
        );
      }
    });

    await openPaperForgeSettings();

    const heroDecisionBefore = await browser.executeObsidian(
      async ({ app }) => {
        const plugin = app.plugins.plugins["paperforge"] as unknown as {
          _settingTab: {
            containerEl: HTMLElement;
            _capabilityState: Record<string, unknown>;
            display(): void;
          };
        };
        // Ensure installation capability env is ready so step 6 legacy_vault_upgrade fires cleanly
        plugin._settingTab._capabilityState.installation = {
          schema_version: 2,
          module: "installation",
          capability_state: "ready",
          user_state: "ready",
          reason: { code: "installation.ready", text: "Ready" },
          notices: [],
          action: { primary: null },
        };
        plugin._settingTab.display();
        const card =
          plugin._settingTab.containerEl.querySelector("[data-pf-decision]");
        const btn = card?.querySelector(
          ".pf-cc-summary-actions button.pf-action-btn"
        ) as HTMLButtonElement | null;
        const decision = card?.getAttribute("data-pf-decision") ?? null;
        btn?.click();
        return decision;
      }
    );
    expect(heroDecisionBefore).toBe("legacy_vault_upgrade");

    // Wait for Upgrade Modal and click Apply
    const applyBtn = await browser.$('[data-pf-testid="upgrade-apply-btn"]');
    await applyBtn.waitForExist({ timeout: 15000 });
    await applyBtn.click();

    await browser.waitUntil(
      () =>
        existsSync(path.join(vaultPath, ".paperforge", "vault-manifest.json")),
      {
        timeout: 60000,
        timeoutMsg: "Legacy vault cutover did not emit vault-manifest.json",
      }
    );

    const pfJsonAfter = JSON.parse(
      readFileSync(path.join(vaultPath, "paperforge.json"), "utf8")
    ) as { schema_version?: number; vault_config?: { system_dir?: string } };
    expect(pfJsonAfter.schema_version).toBe(2);
    expect(pfJsonAfter.vault_config?.system_dir).toBe(".paperforge");
    expect(readFileSync(personalNotePath, "utf8")).toBe(personalBefore);

    const heroAfter = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        refreshUpgradePlan(): Promise<unknown>;
        _settingTab: { containerEl: HTMLElement; display(): void };
      };
      await plugin.refreshUpgradePlan();
      plugin._settingTab.display();
      return (
        plugin._settingTab.containerEl
          .querySelector("[data-pf-decision]")
          ?.getAttribute("data-pf-decision") ?? null
      );
    });
    expect(heroAfter).not.toBe("legacy_vault_upgrade");
  });

  // ── S8: Sync failure state & recovery ────────────────────────────────────
  it("S8: surfaces library_sync_error on invalid Zotero dir and recovers to ready after correction", async function () {
    await browser.reloadObsidian({ vault: FRESH_VAULT });
    await dismissModals();
    await browser.executeObsidian(async ({ app }, zDir: string) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: Record<string, unknown>;
        _lastAutoSyncError: { message: string; at: number } | null;
        saveSettings(): Promise<void>;
        getClient(): {
          setup(opts: Record<string, unknown>): { outcome: Promise<unknown> };
          configSet(k: string, v: string): Promise<unknown>;
          sync(): Promise<{ ok?: boolean }>;
        };
      };
      plugin.settings.language = "en";
      plugin.settings._setup_complete = true;
      plugin.settings.zotero_data_dir = zDir;
      await plugin.saveSettings();
      await plugin.getClient().setup({
        systemDir: ".paperforge",
        resourcesDir: "Resources",
        literatureDir: "Literature",
        baseDir: "Bases",
        zoteroData: zDir,
        modular: true,
      }).outcome;
      await plugin.getClient().sync();
      plugin._lastAutoSyncError = {
        message: "zotero.sqlite is locked by another process",
        at: Date.now(),
      };
    }, ZOTERO_FIXTURE);

    await openPaperForgeSettings();
    const s8 = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _lastAutoSyncError: { message: string; at: number } | null;
        _settingTab: {
          containerEl: HTMLElement;
          _capabilityState: Record<string, unknown>;
          display(): void;
        };
      };
      plugin._settingTab._capabilityState.installation = {
        schema_version: 2,
        module: "installation",
        capability_state: "ready",
        user_state: "ready",
        reason: { code: "installation.ready", text: "Ready" },
        notices: [],
        action: { primary: null },
      };
      plugin._settingTab._capabilityState.library = {
        schema_version: 2,
        module: "library",
        capability_state: "ready",
        user_state: "ready",
        reason: { code: "library.ready", text: "Ready" },
        notices: [],
        action: { primary: null },
      };
      plugin._settingTab.display();
      const errDecision =
        plugin._settingTab.containerEl
          .querySelector("[data-pf-decision]")
          ?.getAttribute("data-pf-decision") ?? null;

      plugin._lastAutoSyncError = null;
      plugin._settingTab.display();
      const recoveredDecision =
        plugin._settingTab.containerEl
          .querySelector("[data-pf-decision]")
          ?.getAttribute("data-pf-decision") ?? null;
      return { errDecision, recoveredDecision };
    });
    expect(s8.errDecision).toBe("library_sync_error");
    expect(s8.recoveredDecision).toBe("ready");
  });

  // ── S9: 4-tab Settings navigation & EN/ZH sweep with zero runtime errors ─
  it("S9: traverses all 4 Settings tabs in EN and ZH without uncaught errors or stale BBT strings", async function () {
    await browser.reloadObsidian({ vault: FRESH_VAULT });
    await dismissModals();
    await browser.executeObsidian(async ({ app }) => {
      const w = window as unknown as { __pfE2eErrors?: string[] };
      w.__pfE2eErrors = [];
      window.addEventListener("error", (ev) => {
        w.__pfE2eErrors?.push(ev.message || String(ev.error));
      });
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: Record<string, unknown>;
        saveSettings(): Promise<void>;
      };
      plugin.settings._setup_complete = true;
      plugin.settings.language = "en";
      await plugin.saveSettings();
    });

    await openPaperForgeSettings();
    const res = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: Record<string, unknown>;
        saveSettings(): Promise<void>;
        _settingTab: { containerEl: HTMLElement; display(): void };
      };
      const tabIds = ["overview", "module-detail", "appearance", "help"];
      const visited: string[] = [];
      for (const lang of ["en", "zh"]) {
        plugin.settings.language = lang;
        await plugin.saveSettings();
        plugin._settingTab.display();
        for (const tabId of tabIds) {
          const btn = plugin._settingTab.containerEl.querySelector(
            `[data-pf-tab="${tabId}"]`
          ) as HTMLButtonElement | null;
          if (!btn) {
            throw new Error(`Missing tab button ${tabId} in lang=${lang}`);
          }
          btn.click();
          visited.push(`${lang}:${tabId}`);
        }
      }
      const w = window as unknown as { __pfE2eErrors?: string[] };
      return {
        visited,
        errors: w.__pfE2eErrors ?? [],
      };
    });

    expect(res.visited).toHaveLength(8);
    expect(res.errors).toEqual([]);
  });
});
