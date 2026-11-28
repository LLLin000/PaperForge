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
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
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
    app: unknown;
  };
  plugin._autoSyncRunning = false;
  plugin._memoryStatusText = "Checking...";
  plugin._lastSyncTime = null;
  plugin._settingTab = { _refreshAllReadModels: vi.fn() };
  plugin.getClient = () => client;
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

  it("skips auto-sync when setup is incomplete and suppresses unconfigured Zotero errors", async () => {
    const plugin = makePlugin(client) as ReturnType<typeof makePlugin> & {
      settings: {
        _setup_complete?: boolean;
        capabilityState?: Record<string, unknown>;
      };
      _lastAutoSyncError: { message: string; at: number } | null;
      _maybeAutoSync: (vaultPath: string) => void;
    };
    plugin._lastAutoSyncError = null;
    plugin.settings = {
      _setup_complete: false,
      capabilityState: {
        library: {
          user_state: "setup_required",
          capability_state: "missing_input",
          reason: { code: "library.zotero_missing", text: "missing" },
        },
      },
    };
    plugin._maybeAutoSync("/vault");
    plugin._autoSync("/vault");
    await Promise.resolve();
    expect(transport.calls.filter((c) => c.argv[0] === "sync")).toHaveLength(0);

    // Even if sync runs when _setup_complete is true, missing Zotero is not an outage
    plugin.settings._setup_complete = true;
    transport.executeHandler = (argv) => {
      if (argv[0] === "sync") {
        return JSON.stringify({
          ok: false,
          error: {
            code: "library.zotero_missing",
            message: "Zotero data directory not configured",
          },
        });
      }
      return "{}";
    };
    plugin._autoSync("/vault");
    await vi.waitFor(() => {
      expect(plugin._autoSyncRunning).toBe(false);
    });
    expect(plugin._lastAutoSyncError).toBeNull();
  });

  it("loadSettings preserves _setup_complete: false for fresh vaults with vault_path and zotero_missing", async () => {
    const plugin = Object.create(
      PaperForgePlugin.prototype
    ) as PaperForgePlugin & {
      loadData: () => Promise<Record<string, unknown>>;
      saveSettings: () => Promise<void>;
    };
    plugin.saveSettings = vi.fn(async () => {});
    plugin.loadData = async () => ({
      _setup_complete: false,
      vault_path: "/sandbox-vault",
      last_seen_version: "",
      capabilityState: {
        library: {
          capability_state: "missing_input",
          user_state: "setup_required",
          reason: { code: "library.zotero_missing", text: "missing" },
        },
      },
    });
    await plugin.loadSettings();
    expect(plugin.settings._setup_complete).toBe(false);
    expect(plugin.saveSettings).not.toHaveBeenCalled();

    // Legacy pre-wizard profiles with last_seen_version + ready library still migrate
    plugin.loadData = async () => ({
      _setup_complete: false,
      last_seen_version: "1.9.0",
      capabilityState: {
        library: {
          capability_state: "ready",
          user_state: "ready",
        },
      },
    });
    await plugin.loadSettings();
    expect(plugin.settings._setup_complete).toBe(true);
    expect(plugin.saveSettings).toHaveBeenCalledTimes(1);
  });

  it("clears zombie sync jobs on daemon.disconnected and reconcileDaemonJobs, and fails closed until veteran upgrade plan resolves", async () => {
    const plugin = makePlugin(client) as ReturnType<typeof makePlugin> & {
      _daemonJobs: Map<string, Record<string, unknown>>;
      _upgradePlanLoaded: boolean;
      _daemonUpdating: boolean;
      _emitStateChanged: () => void;
      _refreshSettingTabIfOpen: () => void;
      _handleDaemonPushEvent: (ev: {
        event: string;
        data?: Record<string, unknown>;
      }) => void;
      reconcileDaemonJobs: () => Promise<void>;
      refreshUpgradePlan: () => Promise<unknown>;
      _maybeAutoSync: (vp: string) => void;
    };
    plugin._daemonJobs = new Map();
    plugin._daemonUpdating = false;
    plugin._emitStateChanged = vi.fn();
    plugin._refreshSettingTabIfOpen = vi.fn();

    // 1) Zombie cli_sync job cleared immediately on daemon.disconnected
    plugin._handleDaemonPushEvent({
      event: "task.updated",
      data: {
        job_id: "cli_sync_1234",
        kind: "sync",
        status: "running",
        current: 3,
        total: 5,
        phase: "build_index",
      },
    });
    expect(plugin.isSyncing()).toBe(true);
    plugin._handleDaemonPushEvent({ event: "daemon.disconnected", data: {} });
    expect(plugin.isSyncing()).toBe(false);
    expect(plugin._daemonJobs.size).toBe(0);

    // 2) Stale cli_sync job also pruned by reconcileDaemonJobs when daemonHealth active_jobs=[]
    plugin._handleDaemonPushEvent({
      event: "task.updated",
      data: {
        job_id: "cli_sync_5678",
        kind: "sync",
        status: "running",
        current: 3,
        total: 5,
        phase: "build_index",
      },
    });
    plugin.getClient = () =>
      ({
        ...client,
        daemonHealth: vi.fn(async () => ({ ok: true, active_jobs: [] })),
      }) as unknown as PaperForgeClient;
    await plugin.reconcileDaemonJobs();
    expect(plugin.isSyncing()).toBe(false);
    expect(plugin._daemonJobs.size).toBe(0);

    // 2b) Bidirectional reconcileDaemonJobs restores live backend jobs after reconnect even from empty cache
    plugin.getClient = () =>
      ({
        ...client,
        daemonHealth: vi.fn(async () => ({
          ok: true,
          active_jobs: [
            {
              job_id: "job_live_heal_1",
              kind: "upgrade.heal",
              status: "running",
              current: 1,
              total: 4,
              phase: "heal",
            },
          ],
        })),
      }) as unknown as PaperForgeClient;
    await plugin.reconcileDaemonJobs();
    expect(plugin.isHealing()).toBe(true);
    expect(plugin._daemonJobs.has("job_live_heal_1")).toBe(true);

    // 2c) Auto-sync stays paused while upgrade.heal is running, and fires after heal succeeds when queued
    plugin.getClient = () => client;
    transport.executeHandler = (argv) =>
      argv[0] === "sync" ? JSON.stringify(SYNC_RESULT) : "{}";
    (
      plugin as unknown as { _syncAfterHealVault: string | null }
    )._syncAfterHealVault = "/vault";
    plugin._upgradePlanLoaded = true;
    plugin._autoSync("/vault");
    expect(transport.calls.filter((c) => c.argv[0] === "sync")).toHaveLength(0);
    plugin._handleDaemonPushEvent({
      event: "task.updated",
      data: {
        job_id: "job_live_heal_1",
        kind: "upgrade.heal",
        status: "succeeded",
      },
    });
    expect(plugin.isHealing()).toBe(false);
    await vi.waitFor(() => {
      expect(transport.calls.filter((c) => c.argv[0] === "sync")).toHaveLength(
        1
      );
    });
    transport.calls.length = 0;

    // 3) runtime.update succeeded refreshes upgrade plan
    const refreshSpy = vi.fn(async () => null);
    plugin.refreshUpgradePlan = refreshSpy;
    plugin.refreshBaseSnapshot = vi.fn(async () => null);
    plugin._handleDaemonPushEvent({
      event: "task.updated",
      data: {
        job_id: "rt_up_1",
        kind: "runtime.update",
        status: "succeeded",
      },
    });
    expect(refreshSpy).toHaveBeenCalledTimes(1);

    // 4) Fail-closed auto-sync when _upgradePlanLoaded===false or legacy System/PaperForge exists unmigrated
    plugin.getClient = () => client;
    plugin._upgradePlanLoaded = false;
    plugin._autoSync("/vault");
    expect(transport.calls.filter((c) => c.argv[0] === "sync")).toHaveLength(0);

    const legacyDir = fs.mkdtempSync(path.join(os.tmpdir(), "pf-legacy-gate-"));
    try {
      fs.mkdirSync(path.join(legacyDir, "System", "PaperForge"), {
        recursive: true,
      });
      plugin._upgradePlanLoaded = true;
      plugin._autoSync(legacyDir);
      expect(transport.calls.filter((c) => c.argv[0] === "sync")).toHaveLength(
        0
      );
    } finally {
      fs.rmSync(legacyDir, { recursive: true, force: true });
    }
  });

  it("isolates upgrade.heal completion by vault path and resumes pending heal/sync from manifest_state", async () => {
    const tmpVault = fs.mkdtempSync(path.join(os.tmpdir(), "pf-multivault-"));
    try {
      const dotPf = path.join(tmpVault, ".paperforge");
      fs.mkdirSync(dotPf, { recursive: true });
      fs.writeFileSync(
        path.join(dotPf, "vault-manifest.json"),
        JSON.stringify({ schema_version: 1, layout_version: 2 }),
        "utf-8"
      );

      const plugin = makePlugin(client) as ReturnType<typeof makePlugin> & {
        app: { vault: { adapter: { basePath: string } } };
        _syncAfterHealVault: string | null;
        _upgradePlanLoaded: boolean;
        _upgradePlanCache: Record<string, unknown> | null;
        _handleDaemonPushEvent: (ev: {
          event: string;
          data?: Record<string, unknown>;
        }) => void;
        refreshUpgradePlan: () => Promise<Record<string, unknown> | null>;
        _healResumeAttempted: boolean;
        _postUpgradeSyncAttempted: boolean;
      };
      plugin.app = { vault: { adapter: { basePath: tmpVault } } };
      plugin._upgradePlanLoaded = true;
      plugin._upgradePlanCache = {
        provenance: { state: "standard_current", needs_upgrade: false },
        manifest_state: {
          heal_pending: false,
          post_upgrade_sync_pending: false,
        },
      };
      plugin._syncAfterHealVault = tmpVault;
      transport.calls.length = 0;

      // 1) Heal finished event belonging to a DIFFERENT vault must NOT trigger or clear current vault sync
      plugin._handleDaemonPushEvent({
        event: "task.updated",
        data: {
          job_id: "other_vault_heal",
          kind: "upgrade.heal",
          vault: path.join(os.tmpdir(), "unrelated-other-vault"),
          status: "succeeded",
        },
      });
      await Promise.resolve();
      expect(plugin._syncAfterHealVault).toBe(tmpVault);
      expect(transport.calls.filter((c) => c.argv[0] === "sync")).toHaveLength(
        0
      );

      // 2) Heal finished event matching current vault clears state and triggers sync
      plugin._handleDaemonPushEvent({
        event: "task.updated",
        data: {
          job_id: "this_vault_heal",
          kind: "upgrade.heal",
          vault: tmpVault,
          status: "succeeded",
        },
      });
      await vi.waitFor(() => {
        expect(
          transport.calls.filter((c) => c.argv[0] === "sync")
        ).toHaveLength(1);
      });
      expect(plugin._syncAfterHealVault).toBeNull();
      await vi.waitFor(() => expect(plugin._autoSyncRunning).toBe(false));

      // 3) Restart recovery: refreshUpgradePlan sees manifest_state.heal_pending=true -> auto-submits upgrade.heal
      plugin._healResumeAttempted = false;
      const submitSpy = vi.fn().mockResolvedValue({ accepted: true });
      const origPlan = {
        vault: tmpVault,
        provenance: { state: "standard_current", needs_upgrade: false },
        manifest_state: { heal_pending: true, post_upgrade_sync_pending: true },
        census: {},
        manifest: {},
        rollback_available: true,
        category_a_auto: [],
        category_b_reconfig: [],
        category_c_tamper: [],
        cleanup_candidates: [],
        summary: {
          auto_count: 0,
          reconfig_critical_count: 0,
          reconfig_minor_count: 0,
          tamper_count: 0,
          cleanup_candidate_count: 0,
          ocr_atoms: {
            total: 0,
            current: 0,
            rebuild_derived_local: 0,
            backfill_from_result_json: 0,
            re_ocr_needed: 0,
          },
        },
      };
      plugin.getClient = () =>
        ({
          vaultUpgradePlan: async () => origPlan,
          daemonSubmitJob: submitSpy,
          sync: () => client.sync(),
        }) as unknown as typeof client;

      await plugin.refreshUpgradePlan();
      expect(submitSpy).toHaveBeenCalledWith("upgrade.heal", {
        backfillOcr: true,
      });
      expect(plugin._syncAfterHealVault).toBe(tmpVault);
    } finally {
      fs.rmSync(tmpVault, { recursive: true, force: true });
    }
  });
});
