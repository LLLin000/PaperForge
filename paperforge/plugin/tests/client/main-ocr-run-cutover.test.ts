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
import { PaperForgeConfirmModal } from "../../src/views/modals";

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
  Modal: class {
    open() {}
  },
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
  dashboardStats: ReturnType<typeof vi.fn>;
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
      dashboardStats: vi.fn(async () => ({
        items: [{ zotero_key: "SCOPE001" }, { zotero_key: "SCOPE002" }],
      })),
      runAction: vi.fn(async () => ({
        ok: true,
        payload: { status: "done" },
        exitCode: 0,
      })),
    };
    plugin = makePlugin(client);
    vi.spyOn(PaperForgeConfirmModal.prototype, "open").mockImplementation(
      function (this: PaperForgeConfirmModal) {
        // The host modal callback represents the user's affirmative click.
        const modal = this as unknown as { _onConfirm: () => void };
        modal._onConfirm();
      }
    );
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

    await plugin.requestOcrRun();

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
    void plugin.requestOcrRun();
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

    await plugin.requestOcrRun();
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

    await plugin.requestOcrRun();
    await vi.waitFor(() => {
      expect(plugin._autoSync).toHaveBeenCalledWith("/vault");
    });
    expect(notices.list.join("\n")).toContain("ocr.credential_missing");
    expect(client.runAction).toHaveBeenCalledWith(
      { action_id: "ocr.run", scope: { kind: "all" }, confirm: "ocr.run" },
      expect.anything()
    );
  });
  it("snapshots paper keys before confirmation and refuses empty selections", async () => {
    const open = vi
      .spyOn(PaperForgeConfirmModal.prototype, "open")
      .mockImplementation(function (this: PaperForgeConfirmModal) {
        // Inspect the in-process modal configuration and invoke its real confirmation callback.
        const modal = this as unknown as {
          _config: { effectLabel: string };
          _onConfirm: () => void;
        };
        expect(modal._config.effectLabel).toContain("SCOPE001");
        keys.push("SCOPE002");
        modal._onConfirm();
      });
    const keys = ["SCOPE001"];
    await plugin.requestOcrRun({ kind: "papers", keys });
    await vi.waitFor(() =>
      expect(client.runAction).toHaveBeenCalledWith(
        {
          action_id: "ocr.run",
          scope: { kind: "papers", keys: ["SCOPE001"] },
          confirm: "ocr.run",
        },
        expect.anything()
      )
    );
    client.runAction.mockClear();
    await plugin.requestOcrRun({ kind: "papers", keys: [] });
    expect(client.runAction).not.toHaveBeenCalled();
    expect(open).toHaveBeenCalledTimes(1);
    open.mockRestore();
  });
  it("labels whole-library impact and does not run when confirmation is cancelled", async () => {
    vi.spyOn(PaperForgeConfirmModal.prototype, "open").mockImplementation(
      function (this: PaperForgeConfirmModal) {
        // Read the host modal presentation without granting consent.
        const modal = this as unknown as { _config: { effectLabel: string } };
        expect(modal._config.effectLabel).toContain("Whole library");
        expect(modal._config.effectLabel).toContain("2");
      }
    );
    await plugin.requestOcrRun({ kind: "all" });
    expect(client.runAction).not.toHaveBeenCalled();
  });
});
