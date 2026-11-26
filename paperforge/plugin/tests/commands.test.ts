// @vitest-environment jsdom
/**
 * Vitest tests for commands (ACTIONS + full Obsidian Command Palette registration).
 */
import { describe, it, expect, vi } from "vitest";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";

vi.mock("obsidian", () => {
  class Component {
    load() {}
    unload() {}
  }
  class ItemView extends Component {
    containerEl = document.createElement("div");
    contentEl = document.createElement("div");
    registerEvent() {}
  }
  class Modal {
    contentEl = document.createElement("div");
    open() {}
    close() {}
  }
  class SuggestModal<T> extends Modal {
    inputEl = document.createElement("input");
    limit = 40;
    setPlaceholder() {}
    setInstructions() {}
    getSuggestions(): T[] {
      return [];
    }
    renderSuggestion() {}
    onChooseSuggestion() {}
  }
  class PluginSettingTab extends Component {
    containerEl = document.createElement("div");
    display() {}
    hide() {}
  }
  class Plugin extends Component {
    app: unknown;
    manifest: unknown;
    constructor(app: unknown, manifest: unknown) {
      super();
      this.app = app;
      this.manifest = manifest;
    }
    loadData = vi.fn(async () => ({}));
    saveData = vi.fn(async () => undefined);
    registerView = vi.fn();
    registerBasesView = vi.fn(() => true);
    addRibbonIcon = vi.fn();
    addCommand = vi.fn();
    addSettingTab = vi.fn();
    addStatusBarItem = vi.fn(() => {
      const el = document.createElement("span");
      return Object.assign(el, {
        setText: (t: string) => {
          el.textContent = t;
        },
      });
    });
    registerEvent = vi.fn();
    registerDomEvent = vi.fn();
    registerInterval = vi.fn(() => 0);
    registerObsidianProtocolHandler = vi.fn();
  }
  return {
    App: class {},
    Plugin,
    ItemView,
    BasesView: class extends Component {},
    Modal,
    SuggestModal,
    PluginSettingTab,
    MarkdownView: class {},
    TFile: class {},
    Notice: vi.fn(),
    Setting: class {
      setName() {
        return this;
      }
      setDesc() {
        return this;
      }
      addToggle() {
        return this;
      }
      addText() {
        return this;
      }
      addDropdown() {
        return this;
      }
    },
    Component,
    MarkdownRenderer: { render: async () => {} },
    Scope: class {
      register() {}
    },
    Menu: class {
      addItem() {
        return this;
      }
      addSeparator() {
        return this;
      }
      showAtMouseEvent() {}
    },
    Platform: { isWin: true, isMacOS: false, isLinux: false },
    Keymap: { isModEvent: () => false },
    setIcon: () => {},
    loadPdfJs: vi.fn(),
  };
});

import { ACTIONS } from "../src/constants";
import PaperForgePlugin from "../src/main";

describe("ACTIONS", () => {
  it("has exactly 5 entries", () => {
    expect(ACTIONS).toHaveLength(5);
  });
  it("every entry has id, title, cmd, okMsg", () => {
    for (const a of ACTIONS) {
      expect(a).toHaveProperty("id");
      expect(a).toHaveProperty("title");
      expect(a).toHaveProperty("commandId");
      expect(a).toHaveProperty("okMsg");
    }
  });
  it("sync action has cmd: sync", () => {
    expect(ACTIONS.find((a) => a.id === "paperforge-sync")?.commandId).toBe(
      "sync"
    );
  });
  it("repair action is enabled (no disabled flag)", () => {
    expect(
      ACTIONS.find((a) => a.id === "paperforge-repair")?.disabled
    ).toBeUndefined();
  });
});

describe("Obsidian Command Palette Registration", () => {
  it("registers all user-facing Obsidian commands and mirrors them in commandRegistry", async () => {
    const tmpVault = fs.mkdtempSync(path.join(os.tmpdir(), "pf-cmd-"));
    try {
      const appMock = {
        vault: {
          adapter: { basePath: tmpVault },
          on: vi.fn(),
          offref: vi.fn(),
        },
        workspace: {
          on: vi.fn(() => ({})),
          offref: vi.fn(),
          onLayoutReady: vi.fn(),
          getLeavesOfType: vi.fn(() => []),
          containerEl: document.createElement("div"),
          rootSplit: {},
        },
        keymap: { pushScope: vi.fn(), popScope: vi.fn() },
      } as unknown as import("obsidian").App;

      const plugin = new PaperForgePlugin(appMock, {
        id: "paperforge",
        name: "PaperForge",
        version: "2.2.0",
        author: "PaperForge",
        minAppVersion: "1.10.0",
        description: "test",
      });

      await plugin.onload();
      const registeredIds = (
        plugin.addCommand as ReturnType<typeof vi.fn>
      ).mock.calls.map((c) => (c[0] as { id: string }).id);

      for (const expectedId of [
        "paperforge-status-panel",
        "paperforge-open-literature-base",
        "paperforge-ocr-workspace",
        "open-ui-gallery",
        "paperforge-quick-switcher",
        "paperforge-insert-citation",
        "paperforge-command-palette",
        "paperforge-open-current-pdf",
        "paperforge-ocr-current-paper",
        "paperforge-build-embeddings",
        "paperforge-open-settings",
        "paperforge-cycle-theme",
        "paperforge-cycle-density",
        "paperforge-toggle-liquid-glass",
        "paperforge-toggle-reduce-motion",
        "paperforge-check-orphans",
      ]) {
        expect(registeredIds).toContain(expectedId);
      }

      const regIds = plugin
        .getCommandRegistry()
        .all()
        .map((c) => c.id);
      expect(regIds).toContain("paperforge-open-settings");
      expect(regIds).toContain("paperforge-build-embeddings");
      expect(regIds).toContain("paperforge-cycle-theme");

      plugin.onunload();
    } finally {
      fs.rmSync(tmpVault, { recursive: true, force: true });
    }
  });

  it("keeps Status Bar visible in idle state, toggles Status Popover on click, and avoids noisy Notice on theme switch", async () => {
    const obsidianMod = await import("obsidian");
    vi.mocked(obsidianMod.Notice).mockClear();
    const sbEl = document.createElement("div");
    const appMock = {
      vault: {
        adapter: { basePath: os.tmpdir() },
        on: vi.fn(),
        offref: vi.fn(),
      },
      workspace: {
        on: vi.fn(() => ({})),
        offref: vi.fn(),
        onLayoutReady: vi.fn(),
        getLeavesOfType: vi.fn(() => []),
        containerEl: document.createElement("div"),
        rootSplit: {},
      },
      keymap: { pushScope: vi.fn(), popScope: vi.fn() },
    } as unknown as import("obsidian").App;

    const plugin = new PaperForgePlugin(appMock, {
      id: "paperforge",
      name: "PaperForge",
      version: "2.2.0",
      author: "PaperForge",
      minAppVersion: "1.10.0",
      description: "test",
    });
    plugin.settings = { ui_theme_mode: "obsidian" } as never;
    plugin.saveSettings = vi.fn().mockResolvedValue(undefined) as never;
    (
      plugin as unknown as { addStatusBarItem: () => HTMLElement }
    ).addStatusBarItem = () => sbEl;
    (
      plugin as unknown as { _setupEcosystemHooks: () => void }
    )._setupEcosystemHooks();

    // Idle Status Bar remains visible as a quiet anchor
    expect(sbEl.style.display).not.toBe("none");
    expect(sbEl.querySelector(".pf-sb-dot")).toBeTruthy();

    // Click toggles compact Status Popover
    sbEl.click();
    const pop = document.querySelector('[data-pf-testid="pf-status-popover"]');
    expect(pop).toBeTruthy();
    expect(
      pop?.querySelector('[data-pf-testid="pf-status-sync"]')
    ).toBeTruthy();

    // Theme cycle should never fire an intrusive Obsidian Notice
    plugin.cycleUiThemeMode();
    expect(vi.mocked(obsidianMod.Notice)).not.toHaveBeenCalled();

    plugin.onunload();
    expect(
      document.querySelector('[data-pf-testid="pf-status-popover"]')
    ).toBeNull();
  });

  it("PF-ARCH-002 / PF-UI-002: triggerBuildEmbeddings dispatches embed.build with scope all and surfaces error Notice when ok=false", async () => {
    const obsidianMod = await import("obsidian");
    vi.mocked(obsidianMod.Notice).mockClear();
    const runAction = vi.fn(async () => ({
      ok: false,
      exitCode: 2,
      payload: { error: { code: "action.scope_invalid", message: "bad scope" } },
    }));
    const plugin = Object.create(PaperForgePlugin.prototype) as PaperForgePlugin & {
      getClient: () => unknown;
      app: unknown;
      _embedProgress: { current: number; total: number; key: string };
    };
    plugin.app = { vault: { adapter: { basePath: "/vault" } } };
    plugin._embedProgress = { current: 0, total: 0, key: "" };
    plugin.getClient = () => ({
      isOperationActive: () => false,
      runAction,
    });

    await plugin.triggerBuildEmbeddings(true);

    expect(runAction).toHaveBeenCalledWith(
      {
        action_id: "embed.build",
        scope: { kind: "all" },
        confirm: "embed.build",
      },
      expect.any(Object)
    );
    const notices = vi
      .mocked(obsidianMod.Notice)
      .mock.calls.map((c) => String(c[0]));
    expect(notices.some((m) => m.includes("Vector build complete"))).toBe(false);
    expect(notices.some((m) => m.includes("bad scope") || m.includes("failed"))).toBe(
      true
    );
  });

  it("PF-UI-007 / PF-RT-006: forwards paperKey in openOcrDiagnostic and tracks runtime.repair in isRuntimeUpdating", async () => {
    const { OcrWorkspaceView } = await import("../src/views/ocr-workspace");
    const openSpy = vi
      .spyOn(OcrWorkspaceView, "open")
      .mockResolvedValue(undefined as never);
    try {
      const plugin = Object.create(PaperForgePlugin.prototype) as PaperForgePlugin;
      plugin.openOcrDiagnostic("KEY_DIAG_9");
      expect(openSpy).toHaveBeenCalledWith(plugin, "KEY_DIAG_9");
    } finally {
      openSpy.mockRestore();
    }

    const plugin2 = Object.create(PaperForgePlugin.prototype) as PaperForgePlugin & {
      _daemonJobs: Map<string, unknown>;
      _emitStateChanged: () => void;
      _refreshSettingTabIfOpen: () => void;
      _handleDaemonPushEvent: (ev: {
        event: string;
        data?: Record<string, unknown>;
      }) => void;
    };
    (plugin2 as unknown as { _daemonJobs: Map<string, unknown> })._daemonJobs =
      new Map();
    plugin2._emitStateChanged = vi.fn();
    plugin2._refreshSettingTabIfOpen = vi.fn();
    plugin2._settingTab = null as never;

    expect(plugin2.isRuntimeUpdating()).toBe(false);
    plugin2._handleDaemonPushEvent({
      event: "task.updated",
      data: { job_id: "job_rep_1", kind: "runtime.repair", status: "running" },
    });
    expect(plugin2.isRuntimeUpdating()).toBe(true);
    plugin2._handleDaemonPushEvent({
      event: "task.updated",
      data: { job_id: "job_rep_1", kind: "runtime.repair", status: "succeeded" },
    });
    expect(plugin2.isRuntimeUpdating()).toBe(false);
  });
});
