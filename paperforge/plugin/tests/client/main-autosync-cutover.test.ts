/**
 * Convergence tick cutover regression (Ticket 07 Stage 2, step 1).
 *
 * `main._autoSync` must route through the shared `PaperForgeClient.sync()`
 * and consume the sync PFResult through the SAME `orchestrateFromSync`
 * bridge as Settings/Dashboard. main never assembles sync argv, never
 * spawns for sync, never duplicates next_actions policy, and never creates
 * a second client. `_autoSyncRunning` dedup and failure cleanup semantics
 * are preserved.
 *
 * The bridge MODULE is mocked (not child_process): this observes the
 * handoff seam directly — `orchestrateFromSync` must receive the same
 * parsed PFResult document (semantic content; client.sync() JSON.parses the
 * backend stdout, so raw bytes are not preserved by design) plus the vault
 * context. Direct child-process usage of main.ts stays enforced by the
 * architecture gate (provenance snapshot = 1).
 */

import "obsidian-test-mocks/jest-setup";
import { describe, it, expect, beforeEach, beforeAll, vi } from "vitest";
import { MockTransport } from "./mock-transport";
import type { PaperForgeClient } from "../../src/client/paperforge-client";
import type { PaperForgePlugin as PluginClass } from "../../src/main";

const { orchestrateFromSync } = vi.hoisted(() => ({
  orchestrateFromSync: vi.fn(async () => 1),
}));

vi.mock("../../src/services/next-actions-bridge", () => ({
  orchestrateFromSync,
}));

vi.mock("obsidian", () => ({
  Plugin: class {},
  PluginSettingTab: class {},
  Notice: class {},
  Modal: class {},
  Setting: class {},
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
// the vi.mock obsidian module (client-first hits a hoisting TDZ).
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

function makePlugin(client: PaperForgeClient) {
  const plugin = Object.create(
    PaperForgePlugin.prototype
  ) as PaperForgePlugin & {
    _autoSyncRunning: boolean;
    _memoryStatusText: string | null;
    _lastSyncTime: string | null;
    _settingTab: { _refreshAllReadModels: (code?: number) => void } | null;
    getClient: () => PaperForgeClient;
    _getPythonCommand: () => { path: string; args: string[] } | null;
    app: unknown;
  };
  plugin._autoSyncRunning = false;
  plugin._memoryStatusText = "Checking...";
  plugin._lastSyncTime = null;
  plugin._settingTab = { _refreshAllReadModels: vi.fn() };
  plugin.getClient = () => client;
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
    orchestrateFromSync.mockClear();
  });

  it("fires sync through the shared client with the exact argv and hands the PFResult to the shared bridge", async () => {
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
    expect(
      transport.calls.filter((c) => c.argv[0] === "sync").map((c) => c.argv)
    ).toEqual([["sync", "--json"]]);

    // Same sync-result consumer as Settings: the SAME parsed PFResult
    // document (semantic content preserved through JSON.parse/stringify)
    // plus the vault context — not a projected subset.
    await vi.waitFor(() => {
      expect(orchestrateFromSync).toHaveBeenCalledTimes(1);
    });
    expect(orchestrateFromSync).toHaveBeenCalledWith(
      JSON.stringify(SYNC_RESULT),
      expect.objectContaining({
        // Item 3: the capability is the SAME client instance that just ran
        // the sync — asserted below by executing through it.
        runAction: expect.any(Function),
      })
    );
    // SAME-client binding regression: the injected capability routes
    // through THIS client's Transport (no second executor, no runtime
    // resolution) — the action argv appears on the same transport that
    // served the sync.
    transport.calls.length = 0;
    const bridgeCtx = (orchestrateFromSync as any).mock.calls[0][1];
    await bridgeCtx.runAction({
      action_id: "memory.build",
      scope: { kind: "all" },
    });
    const actionCall = transport.calls.find(
      (c) => c.argv[0] === "action" && c.argv[1] === "run"
    );
    expect(actionCall).toBeDefined();
    expect(actionCall!.argv).toContain("memory.build");
    expect(actionCall!.argv[actionCall!.argv.length - 1]).toBe("--json");
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

  it("transport failure resets state and skips refresh and follow-ups", async () => {
    transport.executeHandler = (argv) => {
      if (argv[0] === "sync") throw new Error("exit code 1");
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
    expect(orchestrateFromSync).not.toHaveBeenCalled();
  });

  it("structured ok:false result skips refresh and follow-ups", async () => {
    transport.executeHandler = (argv) => {
      if (argv[0] === "sync") {
        return JSON.stringify({ ok: false, error: { code: "SYNC_FAILED" } });
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
    expect(orchestrateFromSync).not.toHaveBeenCalled();
  });
});
