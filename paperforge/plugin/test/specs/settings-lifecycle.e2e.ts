/**
 * Real-Obsidian Settings, Migration & Post-Install Closed-Loop Matrix (H2).
 *
 * Covers ALL 10 SetupDecisionTree states, copy/notice hygiene (zero stale "BBT",
 * zero raw `{placeholder}` / key leaks, zero raw Python tracebacks), every
 * installation/migration transition, and real post-install operational loops:
 *
 *   S1       Brand-new host & fresh vault: _setup_complete=false reload persistence,
 *            engine_not_installed Hero Card contract, start_setup_step1 CTA round-trip
 *   S2 & S3  Existing runtime + fresh vault: zotero_not_configured contract, Refresh button
 *            round-trip (checking -> settled), auto-detect data.json purity, backend
 *            missing_input authority override, and connect_zotero CTA -> Stage 2
 *   S4       Real Zotero SQLite Express install + Post-Install Operational Closed Loops:
 *            Express <-> 4-step wizard toggle, zero BBT copy, Bases + notes + manifest v2,
 *            ready contract (5 module rows + explore checklist dismiss), Companion Panel
 *            live Search, Note Open + Workflow Flag toggle -> frontmatter persistence +
 *            idempotent re-sync, and Quick Switcher paper lookup
 *   S5 & S6  Engine lifecycle states: engine_version_mismatch (2.0.0 -> 2.0.7),
 *            engine_probe_failed (broken python_path NEVER lies as Step 1),
 *            engine_updating, engine_quarantined + secondary Dismiss button round-trip
 *   S7       Veteran legacy vault: legacy_vault_upgrade -> Defer CTA -> Upgrade Modal
 *            metrics & disclosure drawer -> fast cutover -> Notice capture + personal note
 *            safety + Foundation post-upgrade Rollback CTA visibility
 *   S8       Real sync failure (corrupt zotero.sqlite -> library_sync_error + error Notice +
 *            readable body + secondary button) & recovery via Hero Retry CTA -> ready
 *   S9       4-Tab Settings navigation (EN/ZH), Appearance reduce-motion toggle, and full
 *            EN/ZH copy-hygiene sweep across every visible tab & module
 *   S10      Folder-collision protection: existing Resources/ & Bases/ trigger isolation banner
 *            -> PaperForge/Resources & PaperForge/Bases -> user files byte-identical
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
const PLUGIN_MANIFEST = JSON.parse(
  readFileSync(path.join(PLUGIN_DIR, "manifest.json"), "utf8")
) as { version?: string };
const PLUGIN_VERSION = PLUGIN_MANIFEST.version ?? "2.0.8";
const PLUGIN_VERSION_RE = new RegExp(PLUGIN_VERSION.replace(/\./g, "\\."));
const VAULTS_DIR = path.resolve(PLUGIN_DIR, "test", "vaults");
const FRESH_VAULT = "./test/vaults/settings-fresh";
const LEGACY_VAULT = "./test/vaults/settings-legacy";
const COLLISION_VAULT = "./test/vaults/settings-collision";
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

async function closeSettingsModal(): Promise<void> {
  await browser.executeObsidian(async ({ app }) => {
    const setting = (app as unknown as { setting?: { close?: () => void } })
      .setting;
    setting?.close?.();
  });
  await dismissModals();
}

async function openVaultFile(
  filePath: string,
  leafMode: "tab" | "split" = "tab"
): Promise<void> {
  await browser.executeObsidian(
    async ({ app }, fp: string, mode: "tab" | "split") => {
      const file = app.vault.getAbstractFileByPath(fp);
      if (!file) throw new Error(`Vault file not found: ${fp}`);
      if (!("extension" in file)) throw new Error(`Not a file: ${fp}`);
      const leaf = app.workspace.getLeaf(mode);
      await leaf.openFile(file as Parameters<typeof leaf.openFile>[0]);
      app.workspace.setActiveLeaf(leaf, { focus: true });
    },
    filePath,
    leafMode
  );
}

async function sandboxBasePath(): Promise<string> {
  return await browser.executeObsidian(async ({ app }) => {
    const adapter = app.vault.adapter as unknown as { basePath?: string };
    return adapter.basePath ?? "";
  });
}

/** Start recording real Obsidian `.notice` toasts across candidate documents. */
async function startNoticeCapture(): Promise<void> {
  await browser.executeObsidian(async ({ app }) => {
    const plugin = app.plugins.plugins["paperforge"] as unknown as {
      _popoutWindows?: Set<Window>;
      _settingTab?: { containerEl?: HTMLElement };
    };
    const w = window as unknown as {
      __pfCapturedNotices?: string[];
      __pfNoticeObservers?: MutationObserver[];
    };
    for (const obs of w.__pfNoticeObservers ?? []) {
      obs.disconnect();
    }
    w.__pfCapturedNotices = [];
    w.__pfNoticeObservers = [];

    const docs = Array.from(
      new Set(
        [
          document,
          typeof activeDocument !== "undefined" ? activeDocument : null,
          plugin._settingTab?.containerEl?.ownerDocument ?? null,
          ...Array.from(plugin._popoutWindows ?? []).map((pw) => pw.document),
        ].filter((d): d is Document => Boolean(d))
      )
    );
    const collectFrom = (node: ParentNode) => {
      node.querySelectorAll?.(".notice").forEach((el) => {
        const txt = (el.textContent ?? "").trim();
        if (txt && !w.__pfCapturedNotices?.includes(txt)) {
          w.__pfCapturedNotices?.push(txt);
        }
      });
    };
    for (const doc of docs) {
      collectFrom(doc);
      if (!doc.body) continue;
      const obs = new MutationObserver((mutations) => {
        for (const m of mutations) {
          m.addedNodes.forEach((node) => {
            if (node instanceof HTMLElement) {
              if (node.classList?.contains("notice")) {
                const txt = (node.textContent ?? "").trim();
                if (txt && !w.__pfCapturedNotices?.includes(txt)) {
                  w.__pfCapturedNotices?.push(txt);
                }
              }
              collectFrom(node);
            }
          });
        }
      });
      obs.observe(doc.body, { childList: true, subtree: true });
      w.__pfNoticeObservers.push(obs);
    }
  });
}

async function readCapturedNotices(): Promise<string[]> {
  return await browser.executeObsidian(async () => {
    const w = window as unknown as { __pfCapturedNotices?: string[] };
    document.querySelectorAll(".notice").forEach((el) => {
      const txt = (el.textContent ?? "").trim();
      if (
        txt &&
        w.__pfCapturedNotices &&
        !w.__pfCapturedNotices.includes(txt)
      ) {
        w.__pfCapturedNotices.push(txt);
      }
    });
    return [...(w.__pfCapturedNotices ?? [])];
  });
}

/**
 * Wait until async Settings probes + runtime status + sync + startup checks
 * settle and the Control Center Hero Card renders a settled decision.
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

interface DecisionExpectation {
  id: string;
  badgeCls: "ready" | "checking" | "attention";
  titleRe?: RegExp;
  bodyRe?: RegExp;
  expectCodeBlock?: boolean;
  primaryLabelRe?: RegExp;
  secondaryLabelRe?: RegExp;
  noPrimary?: boolean;
  noSecondary?: boolean;
}

/** Assert Hero Card ID, badge class, title/body copy hygiene, and action buttons. */
async function assertDecisionCard(spec: DecisionExpectation): Promise<void> {
  const card = await browser.executeObsidian(async ({ app }) => {
    const plugin = app.plugins.plugins["paperforge"] as unknown as {
      _settingTab: { containerEl: HTMLElement };
    };
    const root =
      plugin._settingTab.containerEl.querySelector("[data-pf-decision]");
    if (!root) return null;
    const badge = root.querySelector(".pf-cc-summary-badge");
    const titleEl = root.querySelector(".pf-cc-summary-copy strong");
    const bodyEl = root.querySelector(".pf-cc-summary-copy .caption");
    const codeEl = root.querySelector("code.pf-defender-path-code");
    const btns = Array.from(
      root.querySelectorAll(".pf-cc-summary-actions button.pf-action-btn")
    ) as HTMLButtonElement[];
    return {
      id: root.getAttribute("data-pf-decision") ?? "",
      badgeCls: badge?.className ?? "",
      badgeText: (badge?.textContent ?? "").trim(),
      title: (titleEl?.textContent ?? "").trim(),
      body: (bodyEl?.textContent ?? "").trim(),
      codeBlock: (codeEl?.textContent ?? "").trim(),
      buttons: btns.map((b) => ({
        text: (b.textContent ?? "").trim(),
        disabled: b.disabled || b.hasAttribute("disabled"),
      })),
    };
  });

  expect(card).not.toBeNull();
  if (!card) return;

  expect(card.id).toBe(spec.id);
  expect(card.badgeCls).toContain(`pf-cc-summary-badge--${spec.badgeCls}`);
  expect(card.badgeText.length).toBeGreaterThan(0);
  expect(card.title.length).toBeGreaterThan(0);
  expect(card.body.length).toBeGreaterThan(0);

  if (spec.titleRe) expect(card.title).toMatch(spec.titleRe);
  if (spec.bodyRe) expect(card.body).toMatch(spec.bodyRe);
  if (spec.expectCodeBlock) expect(card.codeBlock.length).toBeGreaterThan(0);

  // Copy hygiene gate across every rendered string inside the Hero Card
  const allCopy = [
    card.badgeText,
    card.title,
    card.body,
    ...card.buttons.map((b) => b.text),
  ];
  for (const s of allCopy) {
    expect(s).not.toMatch(/\{[a-z_]+\}/);
    expect(s).not.toMatch(/\bBBT\b|Better BibTeX/i);
    expect(s).not.toMatch(/Traceback \(most recent call|File ".*\.py"/);
    expect(s).not.toMatch(/^(?:dt_|cc_|setup_|upgrade_|main_)[a-z0-9_]+$/);
  }

  if (spec.noPrimary) {
    expect(card.buttons.length).toBe(0);
  } else if (spec.primaryLabelRe) {
    expect(card.buttons.length).toBeGreaterThanOrEqual(1);
    expect(card.buttons[0].text).toMatch(spec.primaryLabelRe);
    expect(card.buttons[0].disabled).toBe(false);
  }
  if (spec.noSecondary) {
    expect(card.buttons.length).toBeLessThanOrEqual(1);
  } else if (spec.secondaryLabelRe) {
    expect(card.buttons.length).toBeGreaterThanOrEqual(2);
    expect(card.buttons[1].text).toMatch(spec.secondaryLabelRe);
    expect(card.buttons[1].disabled).toBe(false);
  }
}

describe("PaperForge real-host Settings, Migration & Operational Matrix (H2)", function () {
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

  // ── S1: Fresh vault without runtime -> _setup_complete + engine_not_installed ──
  it("S1: keeps _setup_complete=false across reload and surfaces engine_not_installed with Step 1 round-trip", async function () {
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

    // Leave journey via Later -> Hero Card must say engine_not_installed, and primary CTA re-opens Step 1
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { containerEl: HTMLElement; _goHome(): void };
      };
      const laterBtn = plugin._settingTab.containerEl.querySelector(
        ".pf-express-footer-actions button.pf-action-btn"
      ) as HTMLButtonElement | null;
      if (laterBtn) laterBtn.click();
      else plugin._settingTab._goHome();
    });

    await waitForSettledDecision("engine_not_installed");
    await assertDecisionCard({
      id: "engine_not_installed",
      badgeCls: "attention",
      primaryLabelRe: /setup|install/i,
      noSecondary: true,
    });

    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { containerEl: HTMLElement };
      };
      const btn = plugin._settingTab.containerEl.querySelector(
        '[data-pf-decision="engine_not_installed"] .pf-cc-summary-actions button.pf-action-btn'
      ) as HTMLButtonElement | null;
      btn?.click();
    });
    await browser.waitUntil(
      async () =>
        await browser.executeObsidian(async ({ app }) => {
          const plugin = app.plugins.plugins["paperforge"] as unknown as {
            _settingTab: { containerEl: HTMLElement };
          };
          return Boolean(
            plugin._settingTab.containerEl.querySelector(".pf-setup-journey")
          );
        }),
      { timeout: 10000, timeoutMsg: "start_setup_step1 did not re-open wizard" }
    );
  });

  // ── S2 & S3: Fresh vault with existing runtime & backend authority ──────
  it("S2 & S3: routes fresh vault to zotero_not_configured, honors Refresh & backend missing_input, and enters Stage 2", async function () {
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

    // S2: Click real Express footer "Later" button -> Overview Hero Card == zotero_not_configured
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { containerEl: HTMLElement; _goHome(): void };
      };
      const laterBtn = plugin._settingTab.containerEl.querySelector(
        ".pf-express-footer-actions button.pf-action-btn"
      ) as HTMLButtonElement | null;
      if (laterBtn) laterBtn.click();
      else plugin._settingTab._goHome();
    });
    await waitForSettledDecision("zotero_not_configured");
    await assertDecisionCard({
      id: "zotero_not_configured",
      badgeCls: "attention",
      primaryLabelRe: /zotero|connect/i,
      noSecondary: true,
    });

    const s2Err = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _lastAutoSyncError: unknown;
      };
      return plugin._lastAutoSyncError;
    });
    expect(s2Err).toBeNull();

    // Verify clicking Refresh status button transiently probes / settles back cleanly
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { containerEl: HTMLElement };
      };
      const refreshBtn = plugin._settingTab.containerEl.querySelector(
        ".pf-cc-summary-refresh"
      ) as HTMLButtonElement | null;
      if (!refreshBtn) throw new Error("Summary refresh button missing");
      refreshBtn.click();
    });
    await waitForSettledDecision("zotero_not_configured");

    // S3: Auto-detect returns Zotero stats without touching data.json; stale data.json path still loses to backend
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

    await waitForSettledDecision("zotero_not_configured");
    await assertDecisionCard({
      id: "zotero_not_configured",
      badgeCls: "attention",
      primaryLabelRe: /zotero|connect/i,
      noSecondary: true,
    });

    // Clicking primary Connect Zotero CTA enters 4-step wizard Stage 2
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { containerEl: HTMLElement };
      };
      const connectBtn = plugin._settingTab.containerEl.querySelector(
        '[data-pf-decision="zotero_not_configured"] .pf-cc-summary-actions button.pf-action-btn'
      ) as HTMLButtonElement | null;
      connectBtn?.click();
    });
    await browser.waitUntil(
      async () =>
        await browser.executeObsidian(async ({ app }) => {
          const plugin = app.plugins.plugins["paperforge"] as unknown as {
            _settingTab: { containerEl: HTMLElement };
          };
          const active = plugin._settingTab.containerEl.querySelector(
            ".pf-setup-step--active"
          );
          return (active?.textContent ?? "").includes("2.");
        }),
      {
        timeout: 10000,
        timeoutMsg: "connect_zotero CTA did not navigate to Step 2",
      }
    );
  });

  // ── S4: Real Zotero SQLite Express setup + Post-Install Operational Closed Loops ──
  it("S4: completes Express SQLite setup, verifies ready contract, and runs post-install Companion/Search/Flag/QuickSwitcher loops", async function () {
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

    // Wait for real runtime status probe + Express UI
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
        { timeout: 30000, interval: 200 }
      );
    } catch (err) {
      throw new Error(
        `S4 real runtime status check did not become ready: last=${JSON.stringify(lastRuntimeSnap)} (${err instanceof Error ? err.message : String(err)})`
      );
    }

    // Exercise Express <-> 4-step wizard switch round-trip before running setup
    const toggledWizard = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { containerEl: HTMLElement };
      };
      const tabEl = plugin._settingTab.containerEl;
      const toStep = tabEl.querySelector(
        '[data-pf-testid="express-to-step-btn"]'
      ) as HTMLButtonElement | null;
      if (!toStep) return { step1: false, back: false };
      toStep.click();
      const hasProgress = Boolean(tabEl.querySelector(".pf-setup-progress"));
      const backBtn = tabEl.querySelector(
        ".pf-express-header button"
      ) as HTMLButtonElement | null;
      backBtn?.click();
      const backToExpress = Boolean(
        tabEl.querySelector('[data-pf-testid="express-zotero-input"]')
      );
      return { step1: hasProgress, back: backToExpress };
    });
    expect(toggledWizard).toEqual({ step1: true, back: true });

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
    const manifestJson = JSON.parse(
      readFileSync(
        path.join(vaultPath, ".paperforge", "vault-manifest.json"),
        "utf8"
      )
    ) as { layout_version?: number };
    expect(manifestJson.layout_version).toBe(2);
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
    const zot1Rel = litFiles.find((f) => f.includes("ZOTKEY01"));
    expect(zot1Rel).toBeTruthy();
    expect(litFiles.some((f) => f.includes("ZOTKEY02"))).toBe(true);

    // Control Center Overview: ready contract + 5 module rows + dismissible checklist
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { _goHome(): void };
      };
      plugin._settingTab._goHome();
    });
    await waitForSettledDecision("ready");
    await assertDecisionCard({
      id: "ready",
      badgeCls: "ready",
      titleRe: /2/,
    });

    const overviewWidgets = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { containerEl: HTMLElement };
      };
      const tabEl = plugin._settingTab.containerEl;
      const rows = Array.from(tabEl.querySelectorAll(".pf-cc-nav-row")).map(
        (r) => ({
          mod: r.getAttribute("data-module") ?? "",
          name: (r.querySelector(".pf-cc-card-name")?.textContent ?? "").trim(),
          sentence: (
            r.querySelector(".pf-cc-card-sentence")?.textContent ?? ""
          ).trim(),
        })
      );
      const checklistBefore = Boolean(
        tabEl.querySelector('[data-pf-testid="cc-explore-checklist"]')
      );
      const dismissBtn = tabEl.querySelector(
        '[data-pf-testid="cc-explore-dismiss"]'
      ) as HTMLButtonElement | null;
      dismissBtn?.click();
      const checklistAfter = Boolean(
        tabEl.querySelector('[data-pf-testid="cc-explore-checklist"]')
      );
      return { rows, checklistBefore, checklistAfter };
    });
    expect(overviewWidgets.rows).toHaveLength(5);
    for (const row of overviewWidgets.rows) {
      expect(row.name.length).toBeGreaterThan(0);
      expect(row.sentence.length).toBeGreaterThan(0);
    }
    expect(overviewWidgets.checklistBefore).toBe(true);
    expect(overviewWidgets.checklistAfter).toBe(false);

    // ── Post-Install Closed Loops (Companion + Live Search + Note Flag + Quick Switcher) ──
    await closeSettingsModal();
    await browser.executeObsidianCommand("paperforge:paperforge-status-panel");
    await browser.waitUntil(
      async () =>
        await browser.executeObsidian(async () => {
          const doc =
            typeof activeDocument !== "undefined" ? activeDocument : document;
          return Boolean(
            doc.querySelector(".paperforge-status-panel") ||
            document.querySelector(".paperforge-status-panel")
          );
        }),
      {
        timeout: 15000,
        timeoutMsg: "Companion panel did not open post-install",
      }
    );
    const globalPanelState = await browser.executeObsidian(async () => {
      const doc =
        typeof activeDocument !== "undefined" ? activeDocument : document;
      const root =
        doc.querySelector(".paperforge-status-panel") ??
        document.querySelector(".paperforge-status-panel");
      return {
        hasSetupCta: Boolean(root?.querySelector(".paperforge-setup-cta")),
      };
    });
    expect(globalPanelState.hasSetupCta).toBe(false);

    // Opening the generated domain Base switches Companion to collection mode
    // and mounts the live search box.
    await openVaultFile("Bases/BoneRegen.base");
    await browser.waitUntil(
      async () =>
        await browser.executeObsidian(async () => {
          const doc =
            typeof activeDocument !== "undefined" ? activeDocument : document;
          return Boolean(
            doc.querySelector(".paperforge-search-input") ??
            document.querySelector(".paperforge-search-input")
          );
        }),
      {
        timeout: 20000,
        timeoutMsg:
          "Collection-mode search input never mounted for BoneRegen.base",
      }
    );
    const panelState = await browser.executeObsidian(async () => {
      const doc =
        typeof activeDocument !== "undefined" ? activeDocument : document;
      const root =
        doc.querySelector(".paperforge-status-panel") ??
        document.querySelector(".paperforge-status-panel");
      return {
        hasSetupCta: Boolean(root?.querySelector(".paperforge-setup-cta")),
        hasSearchInput: Boolean(
          root?.querySelector(".paperforge-search-input")
        ),
      };
    });
    expect(panelState.hasSetupCta).toBe(false);
    expect(panelState.hasSearchInput).toBe(true);

    // Live search before building Memory index shows the honest recovery card
    await browser.executeObsidian(async () => {
      const doc =
        typeof activeDocument !== "undefined" ? activeDocument : document;
      const input = (doc.querySelector(".paperforge-search-input") ??
        document.querySelector(
          ".paperforge-search-input"
        )) as HTMLInputElement | null;
      if (!input) throw new Error("paperforge-search-input missing");
      input.value = "Hydrogel";
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(
        new KeyboardEvent("keydown", { key: "Enter", bubbles: true })
      );
    });
    await browser.waitUntil(
      async () =>
        await browser.executeObsidian(async () => {
          const doc =
            typeof activeDocument !== "undefined" ? activeDocument : document;
          const card =
            doc.querySelector(".paperforge-search-state-card.warning-soft") ??
            document.querySelector(
              ".paperforge-search-state-card.warning-soft"
            );
          return Boolean(card && card.querySelector("button"));
        }),
      {
        timeout: 15000,
        timeoutMsg:
          "Pre-build search did not render missing-memory-index recovery card",
      }
    );

    // Build local Memory FTS index via real plugin action, then search hits real note
    const memBuildRes = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        getClient(): {
          runAction(req: {
            action_id: string;
            scope: { kind: string };
            confirm: string;
          }): Promise<{ ok?: boolean; error?: string }>;
        };
      };
      return await plugin.getClient().runAction({
        action_id: "memory.build",
        scope: { kind: "all" },
        confirm: "memory.build",
      });
    });
    expect(memBuildRes?.ok).toBe(true);

    await browser.executeObsidian(async () => {
      const doc =
        typeof activeDocument !== "undefined" ? activeDocument : document;
      const input = (doc.querySelector(".paperforge-search-input") ??
        document.querySelector(
          ".paperforge-search-input"
        )) as HTMLInputElement | null;
      if (!input) throw new Error("paperforge-search-input missing");
      input.value = "Hydrogel";
      input.dispatchEvent(
        new KeyboardEvent("keydown", { key: "Enter", bubbles: true })
      );
    });
    await browser.waitUntil(
      async () =>
        await browser.executeObsidian(async () => {
          const doc =
            typeof activeDocument !== "undefined" ? activeDocument : document;
          const sec =
            doc.querySelector(".paperforge-search-section") ??
            document.querySelector(".paperforge-search-section");
          return (sec?.textContent ?? "").includes(
            "Cartilage Hydrogel Scaffolds"
          );
        }),
      { timeout: 20000, timeoutMsg: "Post-install search returned no hit" }
    );

    // Open synced ZOTKEY01 note, toggle flag-do_ocr -> disk frontmatter -> idempotent re-sync
    const zot1ObsPath = path.posix.join(
      "Resources/Literature/BoneRegen",
      String(zot1Rel).replace(/\\/g, "/")
    );
    const zot1DiskPath = path.join(boneRegenDir, String(zot1Rel));
    // Reveal Companion tab first, then open ZOTKEY01 in a split pane so
    // _isPanelVisible() stays true while active-leaf-change switches to paper mode.
    await browser.executeObsidianCommand("paperforge:paperforge-status-panel");
    await browser.pause(200);
    await openVaultFile(zot1ObsPath, "split");

    let lastToggleDiag: Record<string, unknown> | null = null;
    try {
      await browser.waitUntil(
        async () => {
          const snap = await browser.executeObsidian(async () => {
            const doc =
              typeof activeDocument !== "undefined" ? activeDocument : document;
            const root =
              doc.querySelector(".paperforge-status-panel") ??
              document.querySelector(".paperforge-status-panel");
            return {
              hasToggle: Boolean(
                doc.querySelector(".paperforge-technical-details-toggle") ??
                document.querySelector(".paperforge-technical-details-toggle")
              ),
              panelDisplay: (
                root?.closest(".workspace-leaf") as HTMLElement | null
              )?.style?.display,
              placeholder:
                root
                  ?.querySelector(".paperforge-content-placeholder")
                  ?.textContent?.trim() ?? null,
              hasPaperView: Boolean(
                root?.querySelector(".paperforge-paper-view")
              ),
            };
          });
          lastToggleDiag = snap;
          return snap.hasToggle;
        },
        {
          timeout: 20000,
        }
      );
    } catch (err) {
      throw new Error(
        `Paper detail toggles did not mount when opening ZOTKEY01 note: last=${JSON.stringify(lastToggleDiag)} (${err instanceof Error ? err.message : String(err)})`
      );
    }
    await browser.executeObsidian(async () => {
      const doc =
        typeof activeDocument !== "undefined" ? activeDocument : document;
      const toggle = (doc.querySelector(
        ".paperforge-technical-details-toggle"
      ) ??
        document.querySelector(
          ".paperforge-technical-details-toggle"
        )) as HTMLButtonElement | null;
      toggle?.click();
      const cb = (doc.querySelector("[data-pf-testid='flag-do_ocr']") ??
        document.querySelector(
          "[data-pf-testid='flag-do_ocr']"
        )) as HTMLInputElement | null;
      if (!cb) throw new Error("flag-do_ocr checkbox missing");
      cb.checked = true;
      cb.dispatchEvent(new Event("change", { bubbles: true }));
    });
    await browser.waitUntil(
      () => /do_ocr:\s*true/i.test(readFileSync(zot1DiskPath, "utf8")),
      {
        timeout: 20000,
        timeoutMsg: "UI do_ocr flag toggle never persisted to note frontmatter",
      }
    );

    // Trigger Companion sync button cleanly (idempotent re-sync keeps notes healthy)
    const reSyncResult = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        getClient(): { sync(): Promise<{ ok?: boolean }> };
        refreshBaseSnapshot?(): Promise<unknown>;
      };
      const res = await plugin.getClient().sync();
      await plugin.refreshBaseSnapshot?.();
      return res;
    });
    expect(reSyncResult?.ok).not.toBe(false);
    expect(existsSync(zot1DiskPath)).toBe(true);

    // Quick Switcher finds synced paper immediately
    await browser.executeObsidianCommand(
      "paperforge:paperforge-quick-switcher"
    );
    await browser.waitUntil(
      async () =>
        await browser.executeObsidian(async () => {
          const doc =
            typeof activeDocument !== "undefined" ? activeDocument : document;
          const items = Array.from(
            doc.querySelectorAll(".prompt .suggestion-item").length > 0
              ? doc.querySelectorAll(".prompt .suggestion-item")
              : document.querySelectorAll(".prompt .suggestion-item")
          );
          return items.some((el) =>
            (el.textContent ?? "").includes("Cartilage Hydrogel Scaffolds")
          );
        }),
      {
        timeout: 15000,
        timeoutMsg: "Quick Switcher did not surface synced paper",
      }
    );
    await dismissModals();
  });

  // ── S5 & S6: Version mismatch, probe failure, updating & quarantine states ──
  it("S5 & S6: renders engine_version_mismatch, engine_probe_failed, engine_updating, and engine_quarantined cleanly", async function () {
    // Boot with valid pointer so startup settles cleanly before mutating pointer.
    // Keep _setup_complete = false on unconfigured FRESH_VAULT so data.json
    // does not trigger tier-1 veteran_legacy detection when pointer restores.
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
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { _goHome(): void };
      };
      plugin._settingTab._goHome();
    });
    await waitForSettledDecision("zotero_not_configured");

    // S5a: version mismatch in pointer.json -> engine_version_mismatch
    const parsedPtr = JSON.parse(savedPointerRaw!) as Record<string, unknown>;
    writeFileSync(
      POINTER_PATH,
      JSON.stringify({ ...parsedPtr, paperforge_version: "2.0.0" }),
      "utf8"
    );
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { _refreshAllModules(): void };
      };
      plugin._settingTab._refreshAllModules();
    });
    await waitForSettledDecision("engine_version_mismatch");
    await assertDecisionCard({
      id: "engine_version_mismatch",
      badgeCls: "attention",
      titleRe: PLUGIN_VERSION_RE,
      primaryLabelRe: /update/i,
      noSecondary: true,
    });

    // S5b: matching pointer version but vanished python_path -> engine_probe_failed (NEVER misreports Step 1!)
    const missingPy = path.join(
      RUNTIME_HOME,
      ".paperforge",
      "runtime",
      "missing-python-e2e.exe"
    );
    writeFileSync(
      POINTER_PATH,
      JSON.stringify({ ...parsedPtr, python_path: missingPy }),
      "utf8"
    );
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { _refreshAllModules(): void };
      };
      plugin._settingTab._refreshAllModules();
    });
    await waitForSettledDecision("engine_probe_failed");
    await assertDecisionCard({
      id: "engine_probe_failed",
      badgeCls: "attention",
      titleRe: PLUGIN_VERSION_RE,
      primaryLabelRe: /refresh|check/i,
      secondaryLabelRe: /repair/i,
    });

    // Restore valid pointer cleanly before S6 and settle probes
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
    await waitForSettledDecision("zotero_not_configured");

    // S6: updating & quarantine Hero cards + secondary Dismiss round-trip
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _daemonUpdating: boolean;
        _settingTab: { display(): void };
      };
      plugin._daemonUpdating = true;
      plugin._settingTab.display();
    });
    await assertDecisionCard({
      id: "engine_updating",
      badgeCls: "checking",
      noPrimary: true,
    });

    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _daemonUpdating: boolean;
        _quarantinedBinDir: string | null;
        _settingTab: { display(): void };
      };
      plugin._daemonUpdating = false;
      plugin._quarantinedBinDir = "C:\\Users\\test\\.paperforge\\bin";
      plugin._settingTab.display();
    });
    await assertDecisionCard({
      id: "engine_quarantined",
      badgeCls: "attention",
      expectCodeBlock: true,
      primaryLabelRe: /copy/i,
      secondaryLabelRe: /got it|dismiss/i,
    });

    const afterDismiss = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _quarantinedBinDir: string | null;
        _settingTab: { containerEl: HTMLElement };
      };
      const btns = Array.from(
        plugin._settingTab.containerEl.querySelectorAll(
          '[data-pf-decision="engine_quarantined"] .pf-cc-summary-actions button.pf-action-btn'
        )
      ) as HTMLButtonElement[];
      btns[1]?.click();
      return (
        plugin._settingTab.containerEl
          .querySelector("[data-pf-decision]")
          ?.getAttribute("data-pf-decision") ?? null
      );
    });
    expect(afterDismiss).not.toBe("engine_quarantined");
  });

  // ── S7: Veteran legacy vault: Defer -> Modal Drawer -> Cutover -> Rollback CTA ──
  it("S7: detects legacy vault, supports Defer, executes Upgrade Modal cutover with Notice, preserves notes, and surfaces Rollback", async function () {
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
    await waitForSettledDecision("legacy_vault_upgrade");
    await assertDecisionCard({
      id: "legacy_vault_upgrade",
      badgeCls: "attention",
      primaryLabelRe: /upgrade/i,
      secondaryLabelRe: /later|defer/i,
    });

    // Defer button hides banner cleanly for the session without breaking navigation
    const decisionAfterDefer = await browser.executeObsidian(
      async ({ app }) => {
        const plugin = app.plugins.plugins["paperforge"] as unknown as {
          _settingTab: { containerEl: HTMLElement };
        };
        const btns = Array.from(
          plugin._settingTab.containerEl.querySelectorAll(
            '[data-pf-decision="legacy_vault_upgrade"] .pf-cc-summary-actions button.pf-action-btn'
          )
        ) as HTMLButtonElement[];
        btns[1]?.click();
        return (
          plugin._settingTab.containerEl
            .querySelector("[data-pf-decision]")
            ?.getAttribute("data-pf-decision") ?? null
        );
      }
    );
    expect(decisionAfterDefer).not.toBe("legacy_vault_upgrade");

    // Re-open banner, launch Upgrade Modal, inspect metrics & disclosure drawer, and apply cutover
    await startNoticeCapture();
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _upgradeBannerDismissedForSession?: boolean;
        _settingTab: { containerEl: HTMLElement; display(): void };
      };
      plugin._upgradeBannerDismissedForSession = false;
      plugin._settingTab.display();
      const primary = plugin._settingTab.containerEl.querySelector(
        '[data-pf-decision="legacy_vault_upgrade"] .pf-cc-summary-actions button.pf-action-btn'
      ) as HTMLButtonElement | null;
      if (!primary) throw new Error("legacy_vault_upgrade primary CTA missing");
      primary.click();
    });

    let lastModalDiag: unknown = null;
    try {
      await browser.waitUntil(
        async () => {
          const diag = await browser.executeObsidian(async ({ app }) => {
            const plugin = app.plugins.plugins["paperforge"] as unknown as {
              _popoutWindows?: Set<Window>;
              _settingTab: { containerEl: HTMLElement };
            };
            const docs = Array.from(
              new Set(
                [
                  plugin._settingTab.containerEl.ownerDocument,
                  typeof activeDocument !== "undefined" ? activeDocument : null,
                  document,
                  ...Array.from(plugin._popoutWindows ?? []).map(
                    (w) => w.document
                  ),
                ].filter((d): d is Document => Boolean(d))
              )
            );
            for (const doc of docs) {
              const apply = doc.querySelector(
                '[data-pf-testid="upgrade-apply-btn"]'
              ) as HTMLButtonElement | null;
              if (apply) {
                const metrics = doc.querySelector(
                  '[data-pf-testid="upgrade-metrics"]'
                );
                const toggle = doc.querySelector(
                  '[data-pf-testid="upgrade-disclosure-toggle"]'
                ) as HTMLButtonElement | null;
                let expandedAfter = "";
                if (toggle) {
                  toggle.click();
                  expandedAfter = toggle.getAttribute("aria-expanded") ?? "";
                }
                apply.click();
                return {
                  clicked: true,
                  hasMetrics: Boolean(metrics),
                  expandedAfter,
                };
              }
            }
            return { clicked: false, hasMetrics: false, expandedAfter: "" };
          });
          lastModalDiag = diag;
          if (diag.clicked) {
            expect(diag.hasMetrics).toBe(true);
            expect(diag.expandedAfter).toBe("true");
            return true;
          }
          return false;
        },
        { timeout: 15000, interval: 200 }
      );
    } catch (err) {
      throw new Error(
        `Upgrade modal apply flow failed: diag=${JSON.stringify(lastModalDiag)} (${err instanceof Error ? err.message : String(err)})`
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

    // Wait for completion Notice and plan refresh, then verify Rollback button is surfaced in Foundation detail
    await browser.waitUntil(
      async () => (await readCapturedNotices()).length > 0,
      { timeout: 15000, timeoutMsg: "Upgrade completion Notice never appeared" }
    );
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        refreshUpgradePlan(): Promise<unknown>;
        _settingTab: {
          _refreshAllModules(): void;
          _handleCardNavigation(mod: string): void;
        };
      };
      await plugin.refreshUpgradePlan();
      plugin._settingTab._refreshAllModules();
    });
    const heroAfter = await waitForSettledDecision();
    expect(heroAfter).not.toBe("legacy_vault_upgrade");

    const rollbackVisible = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: {
          containerEl: HTMLElement;
          _handleCardNavigation(mod: string): void;
        };
      };
      plugin._settingTab._handleCardNavigation("installation");
      return Boolean(
        plugin._settingTab.containerEl.querySelector(
          '[data-pf-testid="vault-upgrade-rollback-btn"]'
        )
      );
    });
    expect(rollbackVisible).toBe(true);
  });

  // ── S8: Real sync failure state + error Notice + Retry CTA recovery ─────
  it("S8: surfaces library_sync_error with error Notice on failed sync and recovers to ready", async function () {
    await browser.reloadObsidian({ vault: FRESH_VAULT });
    await dismissModals();

    const vaultPath = await sandboxBasePath();
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
    await waitForSettledDecision("ready");
    await assertDecisionCard({
      id: "ready",
      badgeCls: "ready",
      titleRe: /2/,
    });

    // Break Zotero DB inside an existing dir so real sync() fails with rc!=0 -> library_sync_error + Notice
    const brokenZoteroDir = path.join(vaultPath, "broken-zotero");
    mkdirSync(brokenZoteroDir, { recursive: true });
    writeFileSync(
      path.join(brokenZoteroDir, "zotero.sqlite"),
      "corrupt-sqlite-header",
      "utf8"
    );

    await startNoticeCapture();
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

    await waitForSettledDecision("library_sync_error");
    await assertDecisionCard({
      id: "library_sync_error",
      badgeCls: "attention",
      bodyRe: /sync failed|exit code|re-run/i,
      primaryLabelRe: /retry/i,
      secondaryLabelRe: /zotero/i,
    });
    const errNotices = await readCapturedNotices();
    expect(errNotices.some((n) => /sync|failed|失败/i.test(n))).toBe(true);

    // Restore valid Zotero dir and click Hero Card's primary Retry CTA -> ready
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

    await waitForSettledDecision("ready");
    await assertDecisionCard({
      id: "ready",
      badgeCls: "ready",
      titleRe: /2/,
    });
  });

  // ── S9: 4-tab Settings navigation, Appearance toggle & EN/ZH copy sweep ─
  it("S9: traverses all 4 Settings tabs in EN and ZH with copy hygiene and Appearance toggle check", async function () {
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
      const badCopies: string[] = [];
      let reduceMotionApplied = false;

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
          const txt = plugin._settingTab.containerEl.textContent ?? "";
          if (/\bBBT\b|Better BibTeX/i.test(txt)) {
            badCopies.push(`${lang}:${tabId}:bbt`);
          }
          if (
            /\{(?:count|version|expected|current|detail|module|modules)\}/.test(
              txt
            )
          ) {
            badCopies.push(`${lang}:${tabId}:placeholder`);
          }
          if (tabId === "appearance" && lang === "en") {
            const motion = plugin._settingTab.containerEl.querySelector(
              '[data-pf-testid="settings-reduce-motion"]'
            ) as HTMLInputElement | null;
            if (motion) {
              motion.checked = true;
              motion.dispatchEvent(new Event("change", { bubbles: true }));
              reduceMotionApplied = plugin.settings.reduce_motion === true;
            }
          }
          visited.push(`${lang}:${tabId}`);
        }
      }
      const w = window as unknown as { __pfE2eErrors?: string[] };
      return {
        visited,
        badCopies,
        reduceMotionApplied,
        errors: w.__pfE2eErrors ?? [],
      };
    });

    expect(res.visited).toHaveLength(8);
    expect(res.badCopies).toEqual([]);
    expect(res.reduceMotionApplied).toBe(true);
    expect(res.errors).toEqual([]);
  });

  // ── S10: Folder-collision protection isolates PaperForge folders cleanly ─
  it("S10: isolates PaperForge output when Resources/ and Bases/ already contain user files", async function () {
    await browser.reloadObsidian({ vault: COLLISION_VAULT });
    await dismissModals();

    const vaultPath = await sandboxBasePath();
    const userNotePath = path.join(
      vaultPath,
      "Resources",
      "PersonalReading.md"
    );
    const userBasePath = path.join(vaultPath, "Bases", "MyTasks.base");
    const userNoteBefore = readFileSync(userNotePath, "utf8");
    const userBaseBefore = readFileSync(userBasePath, "utf8");

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

    // Wait for real runtime ready + verify collision guard banner & isolated target dirs
    await browser.waitUntil(
      async () =>
        await browser.executeObsidian(async ({ app }) => {
          const plugin = app.plugins.plugins["paperforge"] as unknown as {
            _settingTab: {
              containerEl: HTMLElement;
              _runtimeStatusLoading?: boolean;
              _runtimeStatus?: { runtime_ready?: boolean } | null;
            };
          };
          const tab = plugin._settingTab;
          return (
            !tab._runtimeStatusLoading &&
            tab._runtimeStatus?.runtime_ready === true &&
            Boolean(
              tab.containerEl.querySelector(
                '[data-pf-testid="express-zotero-input"]'
              )
            )
          );
        }),
      {
        timeout: 30000,
        interval: 200,
        timeoutMsg: "S10 runtime status did not become ready",
      }
    );

    const collisionCheck = await browser.executeObsidian(
      async ({ app }, zDir: string) => {
        const plugin = app.plugins.plugins["paperforge"] as unknown as {
          settings: Record<string, unknown>;
          _settingTab: { containerEl: HTMLElement };
        };
        const tabEl = plugin._settingTab.containerEl;
        const banner = tabEl.querySelector(".pf-collision-guard-banner");
        const zInput = tabEl.querySelector(
          '[data-pf-testid="express-zotero-input"]'
        ) as HTMLInputElement | null;
        if (!zInput) throw new Error("S10 express-zotero-input missing");
        zInput.value = zDir;
        zInput.dispatchEvent(new Event("change", { bubbles: true }));
        return {
          bannerText: (banner?.textContent ?? "").trim(),
          baseDir: String(plugin.settings.base_dir ?? ""),
          resourcesDir: String(plugin.settings.resources_dir ?? ""),
        };
      },
      ZOTERO_FIXTURE
    );
    expect(collisionCheck.bannerText.length).toBeGreaterThan(0);
    expect(collisionCheck.baseDir).toBe("PaperForge/Bases");
    expect(collisionCheck.resourcesDir).toBe("PaperForge/Resources");

    await browser.pause(600);
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { containerEl: HTMLElement };
      };
      const footerBtns = Array.from(
        plugin._settingTab.containerEl.querySelectorAll(
          ".pf-express-footer-actions button.pf-action-btn"
        )
      ) as HTMLButtonElement[];
      const cta = footerBtns[footerBtns.length - 1];
      if (!cta) throw new Error("S10 Express CTA missing");
      cta.click();
    });

    await browser.waitUntil(
      async () => {
        const st = await browser.executeObsidian(async ({ app }) => {
          const plugin = app.plugins.plugins["paperforge"] as unknown as {
            settings: { _setup_complete?: boolean };
            _settingTab: {
              _setupOperation: string;
              _setupFeedback: string | null;
              _setupFailureDetail: string | null;
            };
          };
          if (plugin._settingTab._setupOperation === "failed") {
            throw new Error(
              `S10 setup failed: ${plugin._settingTab._setupFeedback ?? ""} :: ${plugin._settingTab._setupFailureDetail ?? ""}`
            );
          }
          return (
            plugin.settings._setup_complete === true &&
            plugin._settingTab._setupOperation === "idle"
          );
        });
        return st;
      },
      {
        timeout: 60000,
        interval: 400,
        timeoutMsg: "S10 isolated sync timed out",
      }
    );

    // Assert isolated bases + notes under PaperForge/, while top-level Resources/ & Bases/ stay untouched
    expect(
      existsSync(
        path.join(vaultPath, "PaperForge", "Bases", "Literature Hub.base")
      )
    ).toBe(true);
    expect(
      existsSync(path.join(vaultPath, "PaperForge", "Bases", "BoneRegen.base"))
    ).toBe(true);
    expect(existsSync(path.join(vaultPath, "Bases", "BoneRegen.base"))).toBe(
      false
    );
    expect(readFileSync(userNotePath, "utf8")).toBe(userNoteBefore);
    expect(readFileSync(userBasePath, "utf8")).toBe(userBaseBefore);

    const isolatedMd = (
      readdirSync(path.join(vaultPath, "PaperForge"), {
        recursive: true,
      }) as string[]
    ).filter((f) => f.endsWith(".md"));
    expect(isolatedMd.some((f) => f.includes("ZOTKEY01"))).toBe(true);
    expect(isolatedMd.some((f) => f.includes("ZOTKEY02"))).toBe(true);

    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { _goHome(): void };
      };
      plugin._settingTab._goHome();
    });
    await waitForSettledDecision("ready");
    await assertDecisionCard({
      id: "ready",
      badgeCls: "ready",
      titleRe: /2/,
    });
  });
});
