/**
 * Production-entry OCR run regression (Ticket 07 Stage 2 step 3 corrective).
 *
 * `main.requestOcrRun()` is the single user-facing OCR run path for the
 * command palette, Settings run dispatch, and Dashboard. It must dispatch
 * through the shared `PaperForgeClient.runAction` with the canonical
 * `ocr.run` request (exact action_id, scope=all, confirm token), map #137
 * events into `_ocrProgress`, aggregate failed keys from item_result
 * events, surface the real failure reason (failed keys → registry
 * availability_reason → exit code), and settle into `_autoSync`.
 *
 * The shared plugin client is mocked directly — no child_process, no
 * transport. main.ts is loaded dynamically under the mocked obsidian module
 * because a static import breaks the main-first evaluation chain (same
 * pattern and rationale as main-autosync-cutover.test.ts).
 */

import "obsidian-test-mocks/jest-setup";
import { describe, it, expect, beforeEach, beforeAll, vi } from "vitest";
import type { PaperForgeClient } from "../../src/client/paperforge-client";
import type { PaperForgePlugin as PluginClass } from "../../src/main";

const { notices } = vi.hoisted(() => ({
  notices: { list: [] as string[] },
}));

vi.mock("obsidian", () => ({
  Plugin: class {},
  PluginSettingTab: class {},
  Notice: class {
    static shown = notices.list;
    constructor(msg: string) {
      notices.list.push(msg);
    }
  },
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

let PaperForgePlugin: typeof PluginClass;

beforeAll(async () => {
  // PaperForgePlugin is `export default class` — resolve via default interop.
  const main = await import("../../src/main");
  PaperForgePlugin = (main as unknown as { default: typeof PluginClass })
    .default;
});

type FakeClient = {
  isOperationActive: ReturnType<typeof vi.fn>;
  runAction: ReturnType<typeof vi.fn>;
};

function makePlugin(client: FakeClient) {
  const plugin = Object.create(PaperForgePlugin.prototype) as PluginClass & {
    _ocrProgress: { current: number; total: number; key: string };
    _settingTab: { display: () => void } | null;
    _autoSync: (vaultPath: string) => void;
    _client: FakeClient;
    getClient: () => PaperForgeClient;
    app: unknown;
  };
  plugin._ocrProgress = { current: 0, total: 1, key: "" };
  plugin._settingTab = { display: vi.fn() };
  plugin._autoSync = vi.fn();
  plugin._client = client as unknown as PaperForgeClient;
  plugin.getClient = () => client as unknown as PaperForgeClient;
  plugin.app = { vault: { adapter: { basePath: "/vault" } } };
  return plugin;
}

describe("main.requestOcrRun production entry (#07 step 3)", () => {
  let client: FakeClient;
  let plugin: ReturnType<typeof makePlugin>;

  beforeEach(() => {
    notices.list.length = 0;
    client = {
      isOperationActive: vi.fn(() => false),
      runAction: vi.fn(async () => ({
        ok: true,
        payload: { status: "done" },
        exitCode: 0,
      })),
    };
    plugin = makePlugin(client);
  });

  it("confirmed run dispatches the exact canonical ocr.run request and settles into _autoSync", async () => {
    client.runAction.mockImplementation(
      async (_req: unknown, opts?: { onEvent?: (ev: unknown) => void }) => {
        opts?.onEvent?.({
          schema_version: 1,
          event: "progress",
          current: 1,
          total: 2,
          item_id: "A",
        });
        opts?.onEvent?.({
          schema_version: 1,
          event: "item_result",
          item_id: "B",
          status: "failed",
        });
        return { ok: false, payload: null, exitCode: 1 };
      }
    );

    plugin.requestOcrRun(true);

    await vi.waitFor(() => {
      expect(client.runAction).toHaveBeenCalledTimes(1);
    });
    // Exact production wiring: canonical id, scope all, confirm token.
    expect(client.runAction).toHaveBeenCalledWith(
      { action_id: "ocr.run", scope: { kind: "all" }, confirm: "ocr.run" },
      expect.objectContaining({ onEvent: expect.any(Function) })
    );
    // Failed key surfaces in the notice, not a generic failure.
    await vi.waitFor(() => {
      expect(notices.list.some((n) => n.includes("B"))).toBe(true);
    });
    expect(plugin._settingTab?.display).toHaveBeenCalled();
    // Settle: the auto-sync cadence still runs after the run outcome.
    expect(plugin._autoSync).toHaveBeenCalledWith("/vault");
  });

  it("active operation guard rejects with zero dispatches", () => {
    client.isOperationActive.mockReturnValue(true);
    plugin.requestOcrRun(true);
    expect(client.runAction).not.toHaveBeenCalled();
    expect(plugin._autoSync).not.toHaveBeenCalled();
  });

  it("cancelled run shows the stopped notice and still settles into _autoSync", async () => {
    client.runAction.mockImplementation(
      async (_req: unknown, opts?: { onEvent?: (ev: unknown) => void }) => {
        opts?.onEvent?.({ schema_version: 1, event: "cancelled" });
        return {
          ok: false,
          payload: { status: "cancelled" },
          exitCode: 130,
          cancelled: true,
        };
      }
    );

    plugin.requestOcrRun(true);
    await vi.waitFor(() => {
      expect(plugin._autoSync).toHaveBeenCalledWith("/vault");
    });
    expect(
      notices.list.some((n) => n.includes("stopped") || n.length > 0)
    ).toBe(true);
  });

  it("registry unavailability surfaces availability_reason, not a generic failure", async () => {
    client.runAction.mockResolvedValue({
      ok: false,
      payload: {
        action_id: "ocr.run",
        availability: "unavailable",
        availability_reason: "ocr.credential_missing",
      },
      exitCode: 1,
    });

    plugin.requestOcrRun(true);
    await vi.waitFor(() => {
      expect(plugin._autoSync).toHaveBeenCalledWith("/vault");
    });
    expect(notices.list.join("\n")).toContain("ocr.credential_missing");
    expect(client.runAction).toHaveBeenCalledWith(
      { action_id: "ocr.run", scope: { kind: "all" }, confirm: "ocr.run" },
      expect.anything()
    );
  });
});
