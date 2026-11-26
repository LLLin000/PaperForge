/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi } from "vitest";

vi.mock("obsidian", () => {
  class PluginSettingTab {
    app: unknown;
    plugin: unknown;
    containerEl = document.createElement("div");
    constructor(app: unknown, plugin: unknown) {
      this.app = app;
      this.plugin = plugin;
    }
    hide() {}
  }
  class ItemView {
    containerEl = document.createElement("div");
    app: unknown;
    leaf: unknown;
    constructor(leaf: unknown) {
      this.leaf = leaf;
      this.containerEl.appendChild(document.createElement("div"));
      this.containerEl.appendChild(document.createElement("div"));
    }
  }
  return {
    PluginSettingTab,
    ItemView,
    Plugin: class {},
    TFile: class {},
    App: class {},
    Scope: class {},
    Setting: class {
      setName() {
        return this;
      }
      setDesc() {
        return this;
      }
      addButton() {
        return this;
      }
      addToggle() {
        return this;
      }
    },
    Notice: vi.fn(),
    Modal: class {},
    Component: class {},
    MarkdownRenderer: { render: vi.fn() },
    setTooltip: vi.fn(),
    setIcon: vi.fn(),
    Platform: { isDesktopApp: true, isMobile: false },
  };
});

import * as fs from "fs";
import * as path from "path";
import { DEFAULT_SETTINGS } from "../src/constants";
import { PaperForgeSettingTab } from "../src/settings";
import { PaperForgeStatusView } from "../src/views/dashboard";
import PaperForgePlugin from "../src/main";

describe("Performance hygiene & zero-lag runtime invariants", () => {
  it("disables GPU-heavy Liquid Glass blur by default for maximum FPS", () => {
    expect(DEFAULT_SETTINGS.ui_liquid_glass).toBe(false);
  });

  it("never spawns probeAll or rebuilds Settings DOM in the background when Settings is closed", () => {
    const probeAll = vi.fn().mockResolvedValue({});
    const app = {
      vault: { adapter: { basePath: "/vault" } },
    } as never;
    const plugin = {
      settings: { ...DEFAULT_SETTINGS, _setup_complete: true },
      manifest: { version: "2.0.6" },
      saveSettings: vi.fn(),
      loadSettings: vi.fn(),
      getClient: () => ({ probeAll, invalidateCache: vi.fn() }),
    } as never;

    const tab = new PaperForgeSettingTab(app, plugin);
    const displaySpy = vi.spyOn(tab, "display");

    // Settings has never been opened (_isOpen === false)
    tab.refreshIfOpen();
    tab._refreshAllReadModels({ background: true });

    expect(displaySpy).not.toHaveBeenCalled();
    expect(probeAll).not.toHaveBeenCalled();

    // Closing Settings after opening resets _isOpen back to false
    tab.hide();
    tab.refreshIfOpen();
    tab._refreshAllReadModels({ background: true });
    expect(displaySpy).not.toHaveBeenCalled();
    expect(probeAll).not.toHaveBeenCalled();
  });

  it("properly detaches active-leaf-change and vault.modify listeners via offref() on Companion close (zero listener leak)", async () => {
    const leafRef = { id: "leaf-ref" };
    const modifyRef = { id: "mod-ref" };
    const stateRef = { id: "state-ref" };
    const wsOffref = vi.fn();
    const vaultOffref = vi.fn();

    const view = new PaperForgeStatusView({} as never);
    (view as unknown as { app: unknown }).app = {
      workspace: {
        on: (ev: string) => (ev === "active-leaf-change" ? leafRef : stateRef),
        offref: wsOffref,
        off: vi.fn(),
      },
      vault: {
        on: () => modifyRef,
        offref: vaultOffref,
        off: vi.fn(),
      },
    };
    (view as unknown as { _modeSubscribers: unknown[] })._modeSubscribers = [];
    (
      view as unknown as { _setupEventSubscriptions: () => void }
    )._setupEventSubscriptions();
    await view.onClose();

    expect(wsOffref).toHaveBeenCalledWith(leafRef);
    expect(wsOffref).toHaveBeenCalledWith(stateRef);
    expect(vaultOffref).toHaveBeenCalledWith(modifyRef);
  });

  it("clears pending timers on Settings.hide() and stores base filters in app.saveLocalStorage without dirtying data.json", () => {
    const saveSettings = vi.fn().mockResolvedValue(undefined);
    const saveLocalStorage = vi.fn();
    const loadLocalStorage = vi.fn().mockReturnValue(null);
    const app = {
      vault: { adapter: { basePath: "/vault" } },
      saveLocalStorage,
      loadLocalStorage,
    } as never;
    const plugin = {
      settings: { ...DEFAULT_SETTINGS, _setup_complete: true },
      manifest: { version: "2.0.6" },
      saveSettings,
      loadSettings: vi.fn(),
      getClient: () => ({ probeAll: vi.fn(), invalidateCache: vi.fn() }),
    } as never;

    const tab = new PaperForgeSettingTab(app, plugin);
    (tab as unknown as { _saveTimeout: unknown })._saveTimeout = setTimeout(
      () => {},
      5000
    );
    (tab as unknown as { _runtimePollTimer: unknown })._runtimePollTimer =
      setInterval(() => {}, 5000);
    tab.hide();
    expect(
      (tab as unknown as { _saveTimeout: unknown })._saveTimeout
    ).toBeNull();
    expect(
      (tab as unknown as { _runtimePollTimer: unknown })._runtimePollTimer
    ).toBeNull();

    const pf = Object.create(PaperForgePlugin.prototype) as PaperForgePlugin & {
      app: unknown;
      settings: Record<string, unknown>;
      saveSettings: () => Promise<void>;
    };
    pf.app = app;
    pf.settings = { ...DEFAULT_SETTINGS };
    pf.saveSettings = saveSettings;
    pf.setBaseFilters("Ortho::文献库", { query: "ACL" });
    expect(saveLocalStorage).toHaveBeenCalledWith(
      "paperforge:base-filters",
      expect.objectContaining({ "Ortho::文献库": { query: "ACL" } })
    );
    expect(saveSettings).not.toHaveBeenCalled();
  });

  it("keeps ocr-workspace.ts / domain-preview.ts free of innerHTML and main.ts free of detachLeavesOfType", () => {
    const srcRoot = path.resolve(__dirname, "../src");
    const ocrSrc = fs.readFileSync(
      path.join(srcRoot, "views/ocr-workspace.ts"),
      "utf-8"
    );
    const domSrc = fs.readFileSync(
      path.join(srcRoot, "views/domain-preview.ts"),
      "utf-8"
    );
    const mainSrc = fs.readFileSync(path.join(srcRoot, "main.ts"), "utf-8");

    expect(ocrSrc).not.toMatch(/\.innerHTML\s*=/);
    expect(domSrc).not.toMatch(/\.innerHTML\s*=/);
    expect(mainSrc).not.toMatch(/detachLeavesOfType/);
  });

  it("PF-RT-009 / PF-UI-006: onunload() calls _settingTab.hide() and prevents post-unload startup timers or fs.watch", async () => {
    const hideFn = vi.fn();
    const cancelOp = vi.fn();
    const shutdownTransport = vi.fn();
    const pf = Object.create(PaperForgePlugin.prototype) as PaperForgePlugin & {
      _unloaded: boolean;
      _settingTab: { hide: () => void } | null;
      _popoutWindows: Set<Window>;
      _daemonJobs: Map<string, unknown>;
      _client: {
        cancelActiveOperation: () => void;
        shutdownTransport: () => void;
      } | null;
      _pollTimer: ReturnType<typeof setInterval> | null;
      _stateSeqWatcher: { close?: () => void } | null;
      _closeStatusPopover: () => void;
      _startStateSeqWatcher: (vaultBase: string) => void;
      _startConvergenceTimer: () => void;
      app: unknown;
      settings: Record<string, unknown>;
    };
    pf._unloaded = false;
    pf._settingTab = { hide: hideFn };
    pf._popoutWindows = new Set();
    pf._daemonJobs = new Map();
    pf._client = {
      cancelActiveOperation: cancelOp,
      shutdownTransport,
    };
    pf._pollTimer = setInterval(() => {}, 5000);
    pf._stateSeqWatcher = null;
    pf._closeStatusPopover = vi.fn();
    pf.app = { vault: { adapter: { basePath: "/vault" } } };
    pf.settings = { ...DEFAULT_SETTINGS, autoSyncEnabled: true };

    pf.onunload();

    expect(pf._unloaded).toBe(true);
    expect(hideFn).toHaveBeenCalledOnce();
    expect(pf._pollTimer).toBeNull();
    expect(shutdownTransport).toHaveBeenCalledOnce();

    // Post-unload calls to _startConvergenceTimer / _startStateSeqWatcher are no-ops
    pf._startConvergenceTimer();
    pf._startStateSeqWatcher("/vault");
    expect(pf._pollTimer).toBeNull();
    expect(pf._stateSeqWatcher).toBeNull();
  });

  it("PF-ARCH-007: runStartupHydration calls _startStateSeqWatcher AFTER _hydrateConfigMirrors resolves", () => {
    const mainSrc = fs.readFileSync(
      path.join(path.resolve(__dirname, "../src"), "main.ts"),
      "utf-8"
    );
    const hydrationBlock = mainSrc.slice(
      mainSrc.indexOf("const runStartupHydration"),
      mainSrc.indexOf("const scheduleDeferredStartup")
    );
    const hydrateIdx = hydrationBlock.indexOf("this._hydrateConfigMirrors(vaultBase)");
    const watcherIdx = hydrationBlock.indexOf("this._startStateSeqWatcher(vaultBase)");
    expect(hydrateIdx).toBeGreaterThan(-1);
    expect(watcherIdx).toBeGreaterThan(hydrateIdx);
  });
});
