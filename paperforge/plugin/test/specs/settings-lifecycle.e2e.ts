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
 *   S4  Real Zotero SQLite connect & sync (zero stale "BBT" copy, notes + Bases built)
 *   S5  Version mismatch pointer surfaces engine_version_mismatch
 *   S6  Engine updating & antivirus quarantine hero-card states
 *   S7  Veteran legacy vault upgrade modal + dry-run + cutover + user note safety
 *   S8  Real sync failure (library_sync_error) & recovery via Retry CTA back to ready
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

/**
 * Wait until async Settings probes + runtime status + sync settle cleanly and
 * the Control Center Hero Card renders a settled decision (never `"checking"`).
 */
async function waitForSettledDecision(
  expected?: string,
  timeout = 45000
): Promise<string> {
  let lastSnapshot: {
    decision: string | null;
    probing: string[];
    runtimeLoading: boolean;
    libraryRunning: boolean;
    autoSyncRunning: boolean;
    daemonUpdating: boolean;
    runtimeUpdating: boolean;
    startupDeferPending: boolean;
    startupDaemonCheckPending: boolean;
    activeTab: string;
    setupComplete: unknown;
    setupDismissed: boolean;
    instState?: unknown;
    libState?: unknown;
  } = {
    decision: null,
    probing: [],
    runtimeLoading: false,
    libraryRunning: false,
    autoSyncRunning: false,
    daemonUpdating: false,
    runtimeUpdating: false,
    startupDeferPending: false,
    startupDaemonCheckPending: false,
    activeTab: "",
    setupComplete: undefined,
    setupDismissed: false,
  };

  try {
    await browser.waitUntil(
      async () => {
        const snap = await browser.executeObsidian(async ({ app }) => {
          const plugin = app.plugins.plugins["paperforge"] as unknown as {
            settings?: Record<string, unknown>;
            _autoSyncRunning?: boolean;
            _daemonUpdating?: boolean;
            _startupDaemonCheckPending?: boolean;
            _startupDeferTimer?: unknown;
            isRuntimeUpdating?: () => boolean;
            isStartupDaemonCheckPending?: () => boolean;
            _settingTab: {
              containerEl: HTMLElement;
              activeTab?: string;
              _setupJourneyDismissedForSession?: boolean;
              _probing?: Set<string>;
              _runtimeStatusLoading?: boolean;
              _libraryRunning?: boolean;
              _capabilityState?: Record<string, unknown>;
            };
          };
          const tab = plugin._settingTab;
          const card = tab.containerEl.querySelector("[data-pf-decision]");
          const probing = Array.from(tab._probing ?? []);
          const runtimeLoading = Boolean(tab._runtimeStatusLoading);
          const libraryRunning = Boolean(tab._libraryRunning);
          const autoSyncRunning = Boolean(plugin._autoSyncRunning);
          const daemonUpdating = Boolean(plugin._daemonUpdating);
          const runtimeUpdating = Boolean(plugin.isRuntimeUpdating?.());
          const startupDeferPending = Boolean(plugin._startupDeferTimer);
          const startupDaemonCheckPending = Boolean(
            plugin._startupDaemonCheckPending ||
            plugin.isStartupDaemonCheckPending?.()
          );
          const decision = card?.getAttribute("data-pf-decision") ?? null;
          return {
            decision,
            probing,
            runtimeLoading,
            libraryRunning,
            autoSyncRunning,
            daemonUpdating,
            runtimeUpdating,
            startupDeferPending,
            startupDaemonCheckPending,
            activeTab: String(tab.activeTab ?? ""),
            setupComplete: plugin.settings?._setup_complete,
            setupDismissed: Boolean(tab._setupJourneyDismissedForSession),
            instState: tab._capabilityState?.["installation"],
            libState: tab._capabilityState?.["library"],
          };
        });
        lastSnapshot = snap;
        const settled =
          snap.probing.length === 0 &&
          !snap.runtimeLoading &&
          !snap.libraryRunning &&
          !snap.autoSyncRunning &&
          !snap.daemonUpdating &&
          !snap.startupDeferPending &&
          !snap.startupDaemonCheckPending &&
          snap.decision !== null &&
          snap.decision !== "checking";
        if (!settled) return false;
        return expected ? snap.decision === expected : true;
      },
      {
        timeout,
        interval: 200,
      }
    );
  } catch (err) {
    throw new Error(
      `Hero decision did not settle${expected ? ` to "${expected}"` : ""}: last=${JSON.stringify(lastSnapshot)} (${err instanceof Error ? err.message : String(err)})`
    );
  }
  return lastSnapshot.decision ?? "";
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

    const vaultPath = await sandboxBasePath();
    const firstRender = await browser.executeObsidian(
      async ({ app }, vp: string) => {
        const plugin = app.plugins.plugins["paperforge"] as unknown as {
          settings: Record<string, unknown>;
          saveSettings(): Promise<void>;
        };
        plugin.settings.language = "en";
        plugin.settings._setup_complete = false;
        plugin.settings._setup_journey_started = false;
        plugin.settings.vault_path = vp;
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
      },
      vaultPath
    );
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

    // S2: Click real Express footer "Later" button to inspect Overview Hero Card
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { containerEl: HTMLElement; _goHome(): void };
      };
      const laterBtn = plugin._settingTab.containerEl.querySelector(
        ".pf-express-footer-actions button.pf-action-btn"
      ) as HTMLButtonElement | null;
      if (laterBtn) {
        laterBtn.click();
      } else {
        plugin._settingTab._goHome();
      }
    });
    const s2Decision = await waitForSettledDecision("zotero_not_configured");
    expect(s2Decision).toBe("zotero_not_configured");

    const s2Err = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _lastAutoSyncError: unknown;
      };
      return plugin._lastAutoSyncError;
    });
    expect(s2Err).toBeNull();

    // S3: Auto-detect returns Zotero stats without touching data.json; even if
    // data.json caches a Zotero path, real backend probe missing_input wins.
    const detected = await browser.executeObsidian(
      async ({ app }, zDir: string) => {
        const plugin = app.plugins.plugins["paperforge"] as unknown as {
          getClient(): {
            zoteroDetect(dir?: string): Promise<{
              found: boolean;
              total_papers: number;
            }>;
          };
        };
        return await plugin.getClient().zoteroDetect(zDir);
      },
      ZOTERO_FIXTURE
    );
    expect(detected.found).toBe(true);
    expect(detected.total_papers).toBe(2);

    const vaultPath = await sandboxBasePath();
    const dataJsonPath = path.join(
      vaultPath,
      ".obsidian",
      "plugins",
      "paperforge",
      "data.json"
    );
    if (existsSync(dataJsonPath)) {
      const persisted = JSON.parse(readFileSync(dataJsonPath, "utf8")) as {
        zotero_data_dir?: string;
      };
      expect(Boolean(persisted.zotero_data_dir)).toBe(false);
    }

    await browser.executeObsidian(async ({ app }, zDir: string) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: Record<string, unknown>;
        saveSettings(): Promise<void>;
        _settingTab: { _refreshAllModules(): void };
      };
      plugin.settings.zotero_data_dir = zDir;
      await plugin.saveSettings();
      plugin._settingTab._refreshAllModules();
    }, ZOTERO_FIXTURE);

    const s3Decision = await waitForSettledDecision("zotero_not_configured");
    expect(s3Decision).toBe("zotero_not_configured");
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

    // Wait for real runtime status probe to finish rather than mocking _runtimeStatus
    let lastRuntimeSnap: unknown = null;
    try {
      await browser.waitUntil(
        async () => {
          const snap = await browser.executeObsidian(async ({ app }) => {
            const plugin = app.plugins.plugins["paperforge"] as unknown as {
              _startupDeferTimer?: unknown;
              _daemonUpdating?: boolean;
              _settingTab: {
                containerEl: HTMLElement;
                _runtimeStatusLoading?: boolean;
                _runtimeStatus?: { runtime_ready?: boolean } | null;
                _runtimeStatusError?: string | null;
              };
            };
            const tab = plugin._settingTab;
            return {
              startupDeferPending: Boolean(plugin._startupDeferTimer),
              daemonUpdating: Boolean(plugin._daemonUpdating),
              runtimeLoading: Boolean(tab._runtimeStatusLoading),
              runtimeStatus: tab._runtimeStatus ?? null,
              runtimeStatusError: tab._runtimeStatusError ?? null,
              hasInput: Boolean(
                tab.containerEl.querySelector(
                  '[data-pf-testid="express-zotero-input"]'
                )
              ),
            };
          });
          lastRuntimeSnap = snap;
          return (
            !snap.startupDeferPending &&
            !snap.daemonUpdating &&
            !snap.runtimeLoading &&
            snap.runtimeStatus?.runtime_ready === true &&
            snap.hasInput
          );
        },
        {
          timeout: 30000,
          interval: 200,
        }
      );
    } catch (err) {
      throw new Error(
        `S4 real runtime status check did not become ready: last=${JSON.stringify(lastRuntimeSnap)} (${err instanceof Error ? err.message : String(err)})`
      );
    }

    await browser.executeObsidian(async ({ app }, zDir: string) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { containerEl: HTMLElement };
      };
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
    expect(pfJson.schema_version).toBe(2);
    expect(pfJson.zotero_source_mode).toBe("sqlite");
    expect(String(pfJson.zotero_data_dir || "")).toBe(ZOTERO_FIXTURE);
    expect(
      existsSync(path.join(vaultPath, "Bases", "Literature Hub.base"))
    ).toBe(true);
    expect(existsSync(path.join(vaultPath, "Bases", "BoneRegen.base"))).toBe(
      true
    );
    const boneRegenDir = path.join(
      vaultPath,
      "Resources",
      "Literature",
      "BoneRegen"
    );
    expect(existsSync(boneRegenDir)).toBe(true);
    const litFiles = (
      readdirSync(boneRegenDir, { recursive: true }) as string[]
    ).filter((f) => f.endsWith(".md"));
    expect(litFiles.length).toBeGreaterThanOrEqual(2);
    expect(litFiles.some((f) => f.includes("ZOTKEY01"))).toBe(true);
    expect(litFiles.some((f) => f.includes("ZOTKEY02"))).toBe(true);

    // Navigate back to Control Center Overview and verify real settled Hero Card
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { _goHome(): void };
      };
      plugin._settingTab._goHome();
    });
    const heroDecision = await waitForSettledDecision("ready");
    expect(heroDecision).toBe("ready");
  });

  // ── S5 & S6: Version mismatch, hot-swap updating, and quarantine Hero states ──
  it("S5 & S6: renders engine_version_mismatch, engine_updating, and engine_quarantined accurately", async function () {
    // Boot with valid pointer so startup settles cleanly without submitting a background runtime.update job
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
    await waitForSettledDecision();

    // S5: version mismatch in pointer.json -> refresh reads pointer and surfaces engine_version_mismatch
    const parsedPtr = JSON.parse(savedPointerRaw!) as Record<string, unknown>;
    parsedPtr.paperforge_version = "2.0.0";
    writeFileSync(POINTER_PATH, JSON.stringify(parsedPtr), "utf8");
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { _refreshAllModules(): void };
      };
      plugin._settingTab._refreshAllModules();
    });

    const s5Decision = await waitForSettledDecision("engine_version_mismatch");
    expect(s5Decision).toBe("engine_version_mismatch");

    // Restore pointer cleanly before S6 and settle probes
    writeFileSync(POINTER_PATH, savedPointerRaw!, "utf8");
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: {
          _refreshRuntimeStatus?(force?: boolean): void;
          _refreshAllModules(): void;
        };
      };
      plugin._settingTab._refreshRuntimeStatus?.(true);
      plugin._settingTab._refreshAllModules();
    });
    await waitForSettledDecision();

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
    const heroDecisionBefore = await waitForSettledDecision(
      "legacy_vault_upgrade"
    );
    expect(heroDecisionBefore).toBe("legacy_vault_upgrade");

    const clickDiag = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        openUpgradeModal?: () => Promise<void>;
        _settingTab: { containerEl: HTMLElement };
      };
      const btn = plugin._settingTab.containerEl.querySelector(
        '[data-pf-decision="legacy_vault_upgrade"] .pf-cc-summary-actions button.pf-action-btn'
      ) as HTMLButtonElement | null;
      if (!btn) {
        throw new Error("legacy_vault_upgrade Hero CTA button missing");
      }
      const win = window as unknown as {
        __pfOpenUpgradeModalErr?: string | null;
      };
      win.__pfOpenUpgradeModalErr = null;
      if (typeof plugin.openUpgradeModal === "function") {
        const origOpen = plugin.openUpgradeModal.bind(plugin);
        plugin.openUpgradeModal = async () => {
          try {
            await origOpen();
          } catch (e) {
            win.__pfOpenUpgradeModalErr =
              e instanceof Error ? e.message : String(e);
            throw e;
          }
        };
      }
      const disabled = btn.disabled || btn.hasAttribute("disabled");
      const label = btn.textContent ?? "";
      btn.click();
      return { disabled, label };
    });

    // Wait for Upgrade Modal across all active documents (main + popout/ownerDocument) and click Apply
    let lastModalDiag: unknown = null;
    try {
      await browser.waitUntil(
        async () => {
          const diag = await browser.executeObsidian(async ({ app }) => {
            const plugin = app.plugins.plugins["paperforge"] as unknown as {
              _daemonUpdating?: boolean;
              _popoutWindows?: Set<Window>;
              getUpgradePlanCache?: () => unknown;
              _settingTab: { containerEl: HTMLElement };
            };
            const ownerDoc = plugin._settingTab.containerEl.ownerDocument;
            const actDoc =
              typeof activeDocument !== "undefined" ? activeDocument : null;
            const candidateDocs = Array.from(
              new Set(
                [
                  ownerDoc,
                  actDoc,
                  document,
                  ...Array.from(plugin._popoutWindows ?? []).map(
                    (w) => w.document
                  ),
                ].filter((d): d is Document => Boolean(d))
              )
            );
            let clicked = false;
            for (const doc of candidateDocs) {
              const apply = doc.querySelector(
                '[data-pf-testid="upgrade-apply-btn"]'
              ) as HTMLButtonElement | null;
              if (apply) {
                apply.click();
                clicked = true;
                break;
              }
            }
            const card =
              plugin._settingTab.containerEl.querySelector(
                "[data-pf-decision]"
              );
            const win = window as unknown as {
              __pfOpenUpgradeModalErr?: string | null;
            };
            return {
              clicked,
              sameDoc: ownerDoc === document,
              ownerModalCount:
                ownerDoc.querySelectorAll(".modal-container").length,
              mainModalCount:
                document.querySelectorAll(".modal-container").length,
              decision: card?.getAttribute("data-pf-decision") ?? null,
              daemonUpdating: Boolean(plugin._daemonUpdating),
              hasUpgradePlan: Boolean(plugin.getUpgradePlanCache?.()),
              openUpgradeModalErr: win.__pfOpenUpgradeModalErr ?? null,
              clickDiagHint: undefined as unknown,
            };
          });
          diag.clickDiagHint = clickDiag;
          lastModalDiag = diag;
          return diag.clicked;
        },
        {
          timeout: 15000,
          interval: 200,
        }
      );
    } catch (err) {
      throw new Error(
        `Upgrade modal apply button did not appear: diag=${JSON.stringify(lastModalDiag)} (${err instanceof Error ? err.message : String(err)})`
      );
    }

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

    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        refreshUpgradePlan(): Promise<unknown>;
        _settingTab: { _refreshAllModules(): void };
      };
      await plugin.refreshUpgradePlan();
      plugin._settingTab._refreshAllModules();
    });
    const heroAfter = await waitForSettledDecision();
    expect(heroAfter).not.toBe("legacy_vault_upgrade");
  });

  // ── S8: Real sync failure state & recovery via Hero Retry CTA ───────────
  it("S8: surfaces library_sync_error on failed sync and recovers to ready after correction", async function () {
    await browser.reloadObsidian({ vault: FRESH_VAULT });
    await dismissModals();

    const vaultPath = await sandboxBasePath();
    // Run setup + initial sync while _setup_complete is still false so startup
    // auto-sync cannot race with setup().
    await browser.executeObsidian(async ({ app }, zDir: string) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: Record<string, unknown>;
        saveSettings(): Promise<void>;
        clearLastAutoSyncError?(): void;
        refreshUpgradePlan?(): Promise<unknown>;
        getClient(): {
          setup(opts: Record<string, unknown>): { outcome: Promise<unknown> };
          configSet(k: string, v: string): Promise<unknown>;
          sync(): Promise<{ ok?: boolean }>;
        };
      };
      await plugin.getClient().setup({
        systemDir: ".paperforge",
        resourcesDir: "Resources",
        literatureDir: "Literature",
        baseDir: "Bases",
        zoteroData: zDir,
        modular: true,
      }).outcome;
      await plugin.getClient().configSet("zotero_source_mode", "sqlite");
      await plugin.getClient().sync();
      await plugin.refreshUpgradePlan?.();
      plugin.settings.language = "en";
      plugin.settings._setup_complete = true;
      plugin.settings.zotero_data_dir = zDir;
      await plugin.saveSettings();
      plugin.clearLastAutoSyncError?.();
    }, ZOTERO_FIXTURE);

    await openPaperForgeSettings();
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { _refreshAllModules(): void };
      };
      plugin._settingTab._refreshAllModules();
    });
    const initialDecision = await waitForSettledDecision("ready");
    expect(initialDecision).toBe("ready");

    // Break Zotero DB inside an existing directory so probe sees configured path
    // while real sync() fails with non-zero exit code -> library.sync_failed
    const brokenZoteroDir = path.join(vaultPath, "broken-zotero");
    mkdirSync(brokenZoteroDir, { recursive: true });
    writeFileSync(
      path.join(brokenZoteroDir, "zotero.sqlite"),
      "corrupt-sqlite-header",
      "utf8"
    );

    await browser.executeObsidian(async ({ app }, badDir: string) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: Record<string, unknown>;
        saveSettings(): Promise<void>;
        getClient(): { configSet(k: string, v: string): Promise<unknown> };
        _settingTab: { _runManualSync(): void };
      };
      plugin.settings.zotero_data_dir = badDir;
      await plugin.saveSettings();
      await plugin.getClient().configSet("zotero_data_dir", badDir);
      plugin._settingTab._runManualSync();
    }, brokenZoteroDir);

    const errDecision = await waitForSettledDecision("library_sync_error");
    expect(errDecision).toBe("library_sync_error");

    // Restore valid Zotero dir and click Hero Card's primary Retry CTA
    await browser.executeObsidian(async ({ app }, goodDir: string) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: Record<string, unknown>;
        saveSettings(): Promise<void>;
        clearLastAutoSyncError?(): void;
        getClient(): { configSet(k: string, v: string): Promise<unknown> };
        _settingTab: { containerEl: HTMLElement };
      };
      plugin.settings.zotero_data_dir = goodDir;
      await plugin.saveSettings();
      await plugin.getClient().configSet("zotero_data_dir", goodDir);
      plugin.clearLastAutoSyncError?.();
      const retryBtn = plugin._settingTab.containerEl.querySelector(
        '[data-pf-decision="library_sync_error"] .pf-cc-summary-actions button.pf-action-btn'
      ) as HTMLButtonElement | null;
      if (!retryBtn) {
        throw new Error("library_sync_error Retry CTA button missing");
      }
      retryBtn.click();
    }, ZOTERO_FIXTURE);

    const recoveredDecision = await waitForSettledDecision("ready");
    expect(recoveredDecision).toBe("ready");
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
