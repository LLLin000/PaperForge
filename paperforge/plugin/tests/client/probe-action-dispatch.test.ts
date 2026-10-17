/**
 * Probe → plugin dispatch conformance (#223).
 *
 * The Probe declares every action it can offer — in the Python ACTION_REGISTRY
 * or in NON_REGISTRY_ACTIONS with its dispatch owner and verb. These cases pin
 * the plugin side of that contract: an ID the Probe emits must reach its own
 * handler even when another action shares its verb, a registered action must
 * not fall through to the fail-closed "unknown pair" re-probe, and a declared
 * non-registry action must keep the flow its declaration names.
 */
import "obsidian-test-mocks/jest-setup";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { MockTransport } from "./mock-transport";
import { PaperForgeClient } from "../../src/client/paperforge-client";
import { PaperForgeSettingTab } from "../../src/settings";
import type { ActionPrimary } from "../../src/constants";

const { notices } = vi.hoisted(() => ({ notices: { list: [] as string[] } }));

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
    contentEl = document.createElement("div");
    titleEl = document.createElement("h2");
    open() {}
    close() {}
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

type DispatchTab = {
  containerEl: HTMLElement;
  display: () => void;
  _capabilityState: Record<string, unknown>;
  _probeModule: (mod: string) => void;
  _buildAndCopyDiagnostic: () => void;
  _refreshAllReadModels: (code?: number) => void;
  _refreshSnapshots: (vp: string) => void;
  _getVaultBasePath: () => string;
  _runAllowedDispatch: (
    mod: string,
    primary: ActionPrimary,
    env: unknown
  ) => void;
};

function primary(
  overrides: Partial<ActionPrimary> & { action_id: string; verb: string }
): ActionPrimary {
  return {
    label: overrides.action_id,
    availability: "available",
    safety_class: "safe",
    preservation_facts: [],
    replacement_facts: [],
    interruptible: true,
    confirmation_required: false,
    confirmation_prompt: null,
    scope: "module",
    scope_count: 1,
    ...overrides,
  } satisfies ActionPrimary;
}

function envelopeFor(code: string): unknown {
  return { reason: { code, text: "" }, action: { primary: null } };
}

describe("Probe action dispatch conformance (#223)", () => {
  let transport: MockTransport;
  let client: PaperForgeClient;

  beforeEach(() => {
    transport = new MockTransport();
    transport.executeHandler = () => JSON.stringify({ ok: true, data: {} });
    transport.streamHandler = () => ({
      events: [],
      outcome: {
        ok: true,
        exitCode: 0,
        cancelled: false,
        events: [],
      },
    });
    client = new PaperForgeClient({ transport });
    notices.list.length = 0;
  });

  function makeTab(): DispatchTab {
    const app = { vault: { adapter: { basePath: "/vault" } } };
    const plugin = {
      getClient: () => client,
      settings: {},
      manifest: { version: "0.0.0" },
      _ocrProgress: null,
    };
    const tab = new (PaperForgeSettingTab as unknown as new (
      ...args: unknown[]
    ) => DispatchTab)(app, plugin);
    tab.containerEl = document.createElement("div");
    tab.display = vi.fn();
    tab._probeModule = vi.fn();
    tab._buildAndCopyDiagnostic = vi.fn();
    tab._refreshAllReadModels = vi.fn();
    tab._refreshSnapshots = vi.fn();
    tab._getVaultBasePath = () => "/vault";
    tab._capabilityState = {};
    return tab;
  }

  it("routes ocr.rebuild_derived by its exact id even when the Probe sends the generic 'run' verb", async () => {
    const tab = makeTab();
    tab._runAllowedDispatch(
      "ocr",
      primary({
        action_id: "ocr.rebuild_derived",
        verb: "run",
        label: "Rebuild OCR derived",
      }),
      envelopeFor("ocr.derived_missing")
    );

    await vi.waitFor(() => {
      expect(transport.calls.length).toBeGreaterThan(0);
    });
    const actionIds = transport.calls.flatMap((call) =>
      call.argv.filter((arg) => arg.startsWith("ocr."))
    );
    expect(actionIds).toContain("ocr.rebuild_derived");
    expect(actionIds).not.toContain("ocr.run");
  });

  it("routes ocr.diagnose to the diagnostics flow while report_issue keeps the issue draft", () => {
    const tab = makeTab();
    const diagnostics = vi.mocked(tab._buildAndCopyDiagnostic);

    tab._runAllowedDispatch(
      "ocr",
      primary({ action_id: "ocr.diagnose", verb: "investigate" }),
      envelopeFor("ocr.diagnostics_requested")
    );
    expect(diagnostics).toHaveBeenCalledTimes(1);

    diagnostics.mockClear();
    tab._runAllowedDispatch(
      "ocr",
      primary({ action_id: "ocr.report_issue", verb: "investigate" }),
      envelopeFor("ocr.report")
    );
    expect(diagnostics).not.toHaveBeenCalled();
  });

  it("routes foundation.repair through the registered pipeline instead of the unknown-pair fallback", async () => {
    const tab = makeTab();
    tab._runAllowedDispatch(
      "foundation",
      primary({
        action_id: "foundation.repair",
        verb: "repair",
        label: "Repair Runtime",
        safety_class: "destructive",
        confirmation_required: true,
      }),
      envelopeFor("installation.runtime_repair_required")
    );

    await vi.waitFor(() => {
      expect(
        transport.calls.some(
          (call) => call.argv[1] === "run" && call.argv[2] === "foundation.repair"
        )
      ).toBe(true);
    });
    expect(notices.list.join(" | ")).not.toMatch(/Unknown action/i);
  });
});
