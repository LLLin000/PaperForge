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
    App: class {},
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

import { DEFAULT_SETTINGS } from "../src/constants";
import { PaperForgeSettingTab } from "../src/settings";
import { PaperForgeStatusView } from "../src/views/dashboard";

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
});
