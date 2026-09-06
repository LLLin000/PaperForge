/**
 * Convergence tick cutover regression (Ticket 07 Stage 2, step 1).
 *
 * `main._autoSync` must route through the shared `PaperForgeClient.sync()`
 * and consume the sync PFResult through the SAME `orchestrateFromSync`
 * bridge as Settings/Dashboard. main never assembles sync argv, never
 * spawns for sync, never duplicates next_actions policy, and never creates
 * a second client. `_autoSyncRunning` dedup and failure cleanup semantics
 * are preserved.
 */

import "obsidian-test-mocks/jest-setup";
import { describe, it, expect, beforeEach, beforeAll, vi } from "vitest";
import { MockTransport } from "./mock-transport";
import type { ChildProcess } from "node:child_process";
import type { PaperForgeClient } from "../../src/client/paperforge-client";
import type { PaperForgePlugin as PluginClass } from "../../src/main";

const { mockExecFile, mockSpawn } = vi.hoisted(() => ({
  mockExecFile: vi.fn(),
  mockSpawn: vi.fn(),
}));

vi.mock("child_process", () => ({
  execFile: mockExecFile,
  exec: vi.fn(),
  execFileSync: vi.fn(),
  default: { execFile: mockExecFile, spawn: mockSpawn },
}));

vi.mock("obsidian", () => ({
  Plugin: class {
    app: unknown;
    constructor(_app?: unknown, _manifest?: unknown) {}
    addSettingTab() {}
    registerEvent() {}
    registerDomEvent() {}
    addRibbonIcon() {
      return { addEventListener: () => {} };
    }
    addCommand() {
      return {};
    }
    loadData() {
      return Promise.resolve({});
    }
    saveData() {
      return Promise.resolve();
    }
  },
  PluginSettingTab: class {},
  Notice: class {
    constructor(public message: string) {}
  },
  Modal: class {},
  Setting: class {
    setName() {
      return this;
    }
  },
  addIcon: () => {},
  ItemView: class {},
  TFile: class {},
  TFolder: class {},
  MarkdownView: class {},
  Platform: { isMobile: false, isDesktopApp: true },
  requestUrl: () => ({}),
  normalizePath: (p: string) => p,
  debounce: (fn: unknown) => fn,
  FileSystemAdapter: class {},
}));

// Import-order-sensitive: main must evaluate before paperforge-client under
// the vi.mock obsidian module (static order hits a vitest hoisting TDZ).
let PaperForgePlugin: typeof PluginClass;
let PaperForgeClientClass: new (t: { transport: unknown }) => PaperForgeClient;

beforeAll(async () => {
  // PaperForgePlugin is `export default class` — resolve via default interop.
  const main = await import("../../src/main");
  const clientMod = await import("../../src/client/paperforge-client");
  PaperForgePlugin = (main as unknown as { default: typeof PluginClass })
    .default;
  PaperForgeClientClass = clientMod.PaperForgeClient;
});

const SYNC_RESULT = {
  ok: true,
  data: { papers_synced: 3 },
  next_actions: [
    {
      schema_version: 1,
      action_id: "memory.build",
      automatic: true,
      scope: { kind: "all" },
    },
  ],
};

function makePlugin(client: PaperForgeClient | null) {
  const plugin = Object.create(
    PaperForgePlugin.prototype
  ) as PaperForgePlugin & {
    _autoSyncRunning: boolean;
    _memoryStatusText: string | null;
    _lastSyncTime: string | null;
    _settingTab: { _refreshAllReadModels: (code?: number) => void } | null;
    getClient: () => PaperForgeClient | null;
    _getPythonCommand: () => { path: string; args: string[] } | null;
    app: unknown;
  };
  plugin._autoSyncRunning = false;
  plugin._memoryStatusText = "Checking...";
  plugin._lastSyncTime = null;
  plugin._settingTab = { _refreshAllReadModels: vi.fn() };
  plugin.getClient = () => client!;
  plugin._getPythonCommand = () => ({ path: "py", args: ["-3"] });
  plugin.app = { vault: { adapter: { basePath: "/vault" } } };
  return plugin;
}

describe("convergence tick cutover (Ticket 07 Stage 2 step 1)", () => {
  let transport: MockTransport;
  let client: PaperForgeClient;

  beforeEach(() => {
    transport = new MockTransport();
    client = new PaperForgeClientClass({ transport });
    mockExecFile.mockClear();
    mockSpawn.mockClear();
  });

  it("fires sync through the shared client with the exact argv and refreshes the read model", async () => {
    transport.executeHandler = (argv) => {
      if (argv[0] === "sync") return JSON.stringify(SYNC_RESULT);
      if (argv[0] === "reconcile") return JSON.stringify({ deficits: [] });
      return "{}";
    };
    // The follow-up bridge spawns through the mocked child_process; give it
    // a stub child so runSubprocess never touches an undefined stream.
    mockSpawn.mockImplementation(
      () =>
        ({
          stdout: { on: vi.fn() },
          stderr: { on: vi.fn() },
          on: vi.fn(),
        }) as unknown as ChildProcess
    );
    const plugin = makePlugin(client);
    plugin._autoSync("/vault");

    await vi.waitFor(() => {
      expect(transport.calls.some((c) => c.argv[0] === "sync")).toBe(true);
    });
    expect(
      transport.calls.filter((c) => c.argv[0] === "sync").map((c) => c.argv)
    ).toEqual([["sync", "--json"]]);

    // next_actions consumed through the SAME bridge — automatic intent runs.
    await vi.waitFor(() => {
      expect(
        mockSpawn.mock.calls.some((c) =>
          JSON.stringify(c[1]).includes("memory.build")
        )
      ).toBe(true);
    });
    expect(plugin._settingTab?._refreshAllReadModels).toHaveBeenCalled();
    expect(plugin._lastSyncTime).not.toBeNull();
    await vi.waitFor(() => {
      expect(plugin._autoSyncRunning).toBe(false);
      expect(plugin._memoryStatusText).toBeNull();
    });
  });

  it("dedups concurrent ticks (_autoSyncRunning) and resets after settle", async () => {
    let releaseSync: (() => void) | null = null;
    transport.executeHandler = (argv) => {
      if (argv[0] === "sync") {
        return new Promise<string>((resolve) => {
          releaseSync = () => resolve(JSON.stringify(SYNC_RESULT));
        });
      }
      if (argv[0] === "reconcile") return JSON.stringify({ deficits: [] });
      return "{}";
    };
    const plugin = makePlugin(client);
    plugin._autoSync("/vault");
    plugin._autoSync("/vault");
    plugin._autoSync("/vault");

    expect(transport.calls.filter((c) => c.argv[0] === "sync")).toHaveLength(1);

    releaseSync?.();
    await vi.waitFor(() => {
      expect(plugin._autoSyncRunning).toBe(false);
    });
  });

  it("failure path resets state, skips refresh and follow-ups", async () => {
    transport.executeHandler = (argv) => {
      if (argv[0] === "sync") {
        throw new Error("exit code 1");
      }
      return "{}";
    };
    const plugin = makePlugin(client);
    plugin._autoSync("/vault");

    await vi.waitFor(() => {
      expect(plugin._autoSyncRunning).toBe(false);
    });
    expect(plugin._memoryStatusText).toBeNull();
    expect(plugin._settingTab?._refreshAllReadModels).not.toHaveBeenCalled();
    expect(plugin._lastSyncTime).toBeNull();
    expect(mockSpawn).not.toHaveBeenCalled();
  });

  it("never spawns or execFiles for sync", async () => {
    transport.executeHandler = (argv) => {
      if (argv[0] === "sync") return JSON.stringify(SYNC_RESULT);
      if (argv[0] === "reconcile") return JSON.stringify({ deficits: [] });
      return "{}";
    };
    const plugin = makePlugin(client);
    plugin._autoSync("/vault");
    await vi.waitFor(() => {
      expect(transport.calls.some((c) => c.argv[0] === "sync")).toBe(true);
    });
    await vi.waitFor(() => {
      expect(plugin._autoSyncRunning).toBe(false);
    });
    const childArgv = [...mockSpawn.mock.calls, ...mockExecFile.mock.calls].map(
      (c) => JSON.stringify(c[1] ?? [])
    );
    for (const a of childArgv) {
      expect(a).not.toContain('"sync"');
    }
  });
});
