/**
 * X03 concurrency / read-write timing TS coverage.
 */

import "obsidian-test-mocks/jest-setup";


import { describe, it, expect, beforeEach, vi } from "vitest";
import { MockTransport } from "./mock-transport";
import PaperForgePlugin from "../../src/main";
import { PaperForgeClient } from "../../src/client/paperforge-client";
import type { PaperForgeClient as ClientType } from "../../src/client/paperforge-client";

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

type PluginInstance = InstanceType<typeof PaperForgePlugin>;

function mockEnvelope(mod: string, state = "ready"): string {
  return JSON.stringify({
    schema_version: 2,
    module: mod,
    capability_state: state,
    activity_state: "idle",
    user_state: state,
    capability_kind: "operational",
    maintenance_eligible: false,
    user_visible_failure: false,
    user_impact: null,
    activity_label: null,
    activity_progress: null,
    severity: "ok",
    reason: { code: `${mod}.ready`, message: "Ready" },
    action_primary: null,
    details: {},
    ttl_seconds: 60,
    updated_at: new Date().toISOString(),
  });
}

function makePlugin(client: ClientType) {
  const plugin = Object.create(
    PaperForgePlugin.prototype
  ) as PluginInstance & {
    _autoSyncRunning: boolean;
    _memoryStatusText: string | null;
    _lastSyncTime: string | null;
    _settingTab: { _refreshAllReadModels: () => void } | null;
    getClient: () => ClientType;
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

describe("X03 - long-task OperationLock recovery on rejecting holder", () => {
  let transport: MockTransport;
  let client: ClientType;

  beforeEach(() => {
    transport = new MockTransport();
    client = new PaperForgeClient({ transport });
  });

  it("releases the lock when the holder's transport outcome rejects (failSpawn)", async () => {
    transport.streamHandler = () => ({ failSpawn: new Error("spawn ENOENT") });

    const handle = client.streamOperation("failing.task", ["test"]);
    expect(client.isOperationActive()).toBe(true);

    await expect(handle.outcome).rejects.toThrow("spawn ENOENT");

    expect(client.isOperationActive()).toBe(false);
    expect(client.activeOperationId).toBeNull();

    transport.streamHandler = () => ({
      events: [{ schema_version: 1, event: "result", operation: "ok" }],
      outcome: { ok: true, exitCode: 0 },
    });
    const h2 = client.streamOperation("ok.task", ["test"]);
    const out = await h2.outcome;
    expect(out.ok).toBe(true);
  });

  it("releases the lock on a failed (ok:false) outcome", async () => {
    transport.streamHandler = () => ({
      events: [{ schema_version: 1, event: "error", operation: "test" }],
      outcome: { ok: false, exitCode: 1 },
    });
    const h = client.streamOperation("err.task", ["test"]);
    const out = await h.outcome;
    expect(out.ok).toBe(false);
    expect(client.isOperationActive()).toBe(false);
  });
});

describe("X03 - concurrent read de-duplication", () => {
  let transport: MockTransport;
  let client: ClientType;
  let time: number;

  beforeEach(() => {
    transport = new MockTransport();
    time = 1000000;
    client = new PaperForgeClient({ transport, clock: () => time });
  });

  it("shares a single transport call for N concurrent identical reads", async () => {
    let calls = 0;
    let resolveOne!: (v: string) => void;
    const deferred = new Promise<string>((r) => {
      resolveOne = r;
    });
    transport.executeHandler = () => {
      calls++;
      return deferred;
    };

    const ps = [client.probe("library"), client.probe("library"), client.probe("library")];
    expect(calls).toBe(1);
    resolveOne(mockEnvelope("library", "ready"));
    const rs = await Promise.all(ps);
    rs.forEach((r) => expect(r.module).toBe("library"));
    expect(calls).toBe(1);
  });

  it("does not dedup reads with different keys", async () => {
    let calls = 0;
    transport.executeHandler = (argv) => {
      calls++;
      if (argv[1] === "library") return mockEnvelope("library", "ready");
      return mockEnvelope("ocr", "ready");
    };
    const [ra, rb] = await Promise.all([
      client.probe("ocr"),
      client.probe("library"),
    ]);
    expect(ra.module).toBe("ocr");
    expect(rb.module).toBe("library");
    expect(calls).toBe(2);
  });

  it("cleans up in-flight map on rejection so a retry dispatches again", async () => {
    let calls = 0;
    let fail = true;
    transport.executeHandler = () => {
      calls++;
      if (fail) throw new Error("boom");
      return mockEnvelope("ocr", "ready");
    };

    await expect(client.probe("ocr")).rejects.toThrow("boom");
    expect(calls).toBe(1);

    fail = false;
    const r = await client.probe("ocr");
    expect(r.module).toBe("ocr");
    expect(calls).toBe(2);
  });

  it("propagates a single rejection to all concurrent waiters", async () => {
    let calls = 0;
    transport.executeHandler = async () => {
      calls++;
      throw new Error("boom2");
    };

    const p1 = client.probe("ocr");
    const p2 = client.probe("ocr");
    await expect(p1).rejects.toThrow("boom2");
    await expect(p2).rejects.toThrow("boom2");
    expect(calls).toBe(1);
  });
});

describe("X03 - autosync tick de-dup interactions", () => {
  let transport: MockTransport;
  let client: ClientType;

  beforeEach(() => {
    transport = new MockTransport();
    client = new PaperForgeClient({ transport });
    orchestrateFromSync.mockClear();
  });

  it("dedups overlapping ticks and still resets after settle", async () => {
    let releaseSync!: () => void;
    transport.executeHandler = (argv) => {
      if (argv[0] === "sync") {
        return new Promise<string>((resolve) => {
          releaseSync = () => resolve(JSON.stringify({ ok: true, data: {} }));
        });
      }
      return "{}";
    };
    const plugin = makePlugin(client);
    plugin._autoSync("/vault");
    plugin._autoSync("/vault");
    plugin._autoSync("/vault");
    expect(transport.calls.filter((c) => c.argv[0] === "sync")).toHaveLength(1);

    releaseSync();
    await vi.waitFor(() => expect(plugin._autoSyncRunning).toBe(false));

    transport.executeHandler = (argv) => {
      if (argv[0] === "sync") return JSON.stringify({ ok: true, data: {} });
      return "{}";
    };
    plugin._autoSync("/vault");
    await vi.waitFor(() => {
      expect(transport.calls.filter((c) => c.argv[0] === "sync")).toHaveLength(2);
    });
    await vi.waitFor(() => expect(plugin._autoSyncRunning).toBe(false));
  });
});

describe("X03 - two-client / two-vault isolation", () => {
  it("two clients have independent OperationLocks", async () => {
    const tA = new MockTransport();
    const tB = new MockTransport();
    const cA = new PaperForgeClient({ transport: tA });
    const cB = new PaperForgeClient({ transport: tB });

    tA.streamHandler = () => ({ delayMs: 50, events: [], outcome: { ok: true, exitCode: 0 } });
    tB.streamHandler = () => ({ events: [], outcome: { ok: true, exitCode: 0 } });

    const hA = cA.streamOperation("long.task", ["x"]);
    expect(cA.isOperationActive()).toBe(true);
    const hB = cB.streamOperation("short.task", ["y"]);
    expect(cB.isOperationActive()).toBe(true);
    await Promise.all([hA.outcome, hB.outcome]);
    expect(cA.isOperationActive()).toBe(false);
    expect(cB.isOperationActive()).toBe(false);
  });

  it("mutation on client A bumps only A's epoch and cache", async () => {
    const tA = new MockTransport();
    const tB = new MockTransport();
    const cA = new PaperForgeClient({ transport: tA });
    const cB = new PaperForgeClient({ transport: tB });

    tA.executeHandler = (argv) => {
      if (argv.includes("probe")) return mockEnvelope("ocr", "ready");
      if (argv.includes("run")) return JSON.stringify({ ok: true, data: {} });
      return "{}";
    };
    tB.executeHandler = () => mockEnvelope("ocr", "ready");

    await cA.probe("ocr");
    await cB.probe("ocr");
    const epochA0 = cA.getEpoch();
    const epochB0 = cB.getEpoch();

    await cA.runAction({ action_id: "ocr.rebuild", scope: { kind: "all" } });
    expect(cA.getEpoch()).toBe(epochA0 + 1);
    expect(cB.getEpoch()).toBe(epochB0);
  });

  it("read de-dup is per-client, not shared across vaults", async () => {
    const tA = new MockTransport();
    const tB = new MockTransport();
    const cA = new PaperForgeClient({ transport: tA });
    const cB = new PaperForgeClient({ transport: tB });

    let callsA = 0;
    let callsB = 0;
    tA.executeHandler = () => {
      callsA++;
      return mockEnvelope("ocr", "ready");
    };
    tB.executeHandler = () => {
      callsB++;
      return mockEnvelope("ocr", "ready");
    };

    const [ra, rb] = await Promise.all([cA.probe("ocr"), cB.probe("ocr")]);
    expect(ra.module).toBe("ocr");
    expect(rb.module).toBe("ocr");
    expect(callsA).toBe(1);
    expect(callsB).toBe(1);
  });
});
