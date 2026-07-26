/**
 * Issue #78 — Library, OCR, and Memory module detail end-to-end tests.
 *
 * Uses JSDOM + Vitest mocks. Instantiates PaperForgeSettingTab, calls production
 * render functions, clicks production buttons. NO standalone DOM lookalikes.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { JSDOM } from "jsdom";

// ── Hoisted mutable state ──
const { noticeCalls, spawnedProcesses, execFileCalls, modalOpens } = vi.hoisted(
  () => {
    const modalOpens: Array<{
      kind: string;
      title: string;
      effectLabel: string;
      onConfirm?: () => void;
      draft: unknown;
    }> = [];
    const noticeCalls: string[] = [];
    const spawnedProcesses: Array<{
      args: string[];
      onData?: (data: unknown) => void;
      onStderr?: (data: unknown) => void;
      onError?: (err: Error) => void;
      onClose?: (code: number | null) => void;
    }> = [];
    const execFileCalls: Array<{
      args: string[];
      cb?: (err: Error | null, stdout: string, stderr: string) => void;
    }> = [];
    return { noticeCalls, spawnedProcesses, execFileCalls, modalOpens };
  }
);

// ── Mocks ──
vi.mock("../src/release-notes.json", () => ({ default: { versions: [] } }));

vi.mock("obsidian", () => {
  return {
    PluginSettingTab: class {
      containerEl: HTMLDivElement;
      app: Record<string, unknown>;
      constructor(
        app: Record<string, unknown>,
        _plugin: Record<string, unknown>
      ) {
        this.app = app;
        this.containerEl = document.createElement("div");
      }
    },
    App: class {},
    Setting: class {
      settingEl: HTMLDivElement;
      descEl: HTMLDivElement & { setText?: (t: string) => void };
      nameEl: HTMLDivElement;
      controlEl: HTMLDivElement;
      constructor(containerEl: HTMLElement) {
        this.settingEl = document.createElement("div");
        this.settingEl.className = "setting-item";
        this.nameEl = document.createElement("div");
        this.nameEl.className = "setting-item-name";
        this.descEl = Object.assign(document.createElement("div"), {
          className: "setting-item-description",
          setText: (t: string) => {
            this.descEl.textContent = t;
          },
        });
        this.controlEl = document.createElement("div");
        this.controlEl.className = "setting-item-control";
        this.settingEl.appendChild(this.nameEl);
        this.settingEl.appendChild(this.descEl);
        this.settingEl.appendChild(this.controlEl);
        containerEl.appendChild(this.settingEl);
      }
      setName(text: string) {
        this.nameEl.textContent = text;
        return this;
      }
      setDesc(text: string) {
        this.descEl.textContent = text;
        return this;
      }
      addText(cb: (text: Record<string, unknown>) => void) {
        return this;
      }
      addToggle(cb: (toggle: Record<string, unknown>) => void) {
        return this;
      }
      addDropdown(cb: (dropdown: Record<string, unknown>) => void) {
        const select = document.createElement("select");
        this.controlEl.appendChild(select);
        const dropdown = {
          addOption: () => {},
          setValue: function () {
            return this;
          },
          onChange: function () {
            return this;
          },
        };
        cb(dropdown);
        return this;
      }
      addButton(cb: (button: Record<string, unknown>) => void) {
        return this;
      }
      addExtraButton(cb: (btn: Record<string, unknown>) => void) {
        return this;
      }
    },
    Modal: class {
      app: Record<string, unknown>;
      contentEl: HTMLDivElement;
      constructor(app: Record<string, unknown>) {
        this.app = app;
        this.contentEl = document.createElement("div");
      }
      open() {
        const self = this as Record<string, unknown>;
        const kind = this.constructor.name;
        const cfg = self["_config"];
        const title =
          cfg && typeof cfg === "object"
            ? String(Reflect.get(cfg, "title") ?? "")
            : "";
        const effectLabel =
          cfg && typeof cfg === "object"
            ? String(Reflect.get(cfg, "effectLabel") ?? "")
            : "";
        const cfgDraft =
          cfg && typeof cfg === "object"
            ? Reflect.get(cfg, "_draft")
            : undefined;
        const draft = cfgDraft ?? self["_draft"] ?? null;
        const rawOnConfirm = self["_onConfirm"];
        const onConfirm =
          typeof rawOnConfirm === "function"
            ? (rawOnConfirm as () => void)
            : undefined;
        modalOpens.push({ kind, title, effectLabel, onConfirm, draft });
      }
      close() {}
    },
    Notice: class {
      constructor(msg: string, timeout?: number) {
        noticeCalls.push({ msg, timeout });
      }
    },
    setTooltip: () => {},
    Platform: {},
  };
});

// Mock node built-ins used by settings.ts
vi.mock("fs", () => ({
  default: {},
  existsSync: () => false,
  readFileSync: () => "{}",
  writeFileSync: () => {},
  readdirSync: () => [],
  statSync: () => ({}),
  accessSync: () => {},
  constants: { X_OK: 1 },
}));
vi.mock("path", () => ({
  default: {},
  join: (...args: string[]) => args.join("/"),
  dirname: (p: string) => p.split("/").slice(0, -1).join("/"),
  resolve: (...args: string[]) => args.join("/"),
}));
vi.mock("os", () => ({
  default: {},
  homedir: () => "/home/user",
  platform: () => "win32",
}));
vi.mock("child_process", () => {
  const mod = {
    execFile: (
      _path: string,
      args: string[],
      _opts: Record<string, unknown>,
      cb?: (err: Error | null, stdout: string, stderr: string) => void
    ) => {
      execFileCalls.push({ args: [...args], cb });
      // Defer callback so tests can inspect state before terminal cleanup
      if (cb) setTimeout(() => cb(null, "{}", ""), 0);
    },
    execFileSync: () => "Python 3.11.0",
    exec: () => {},
    spawn: (_path: string, args: string[], _opts: Record<string, unknown>) => {
      const self = {
        args: [...args],
        stdout: {
          on: (_ev: string, cb: (data: unknown) => void) => {
            self.onData = cb;
          },
        },
        stderr: {
          on: (_ev: string, cb: (data: unknown) => void) => {
            self.onStderr = cb;
          },
        },
        stdin: { write: (_s: string) => true },
        kill: (_sig: string) => {},
        onData: undefined as ((data: unknown) => void) | undefined,
        onStderr: undefined as ((data: unknown) => void) | undefined,
        onError: undefined as ((err: Error) => void) | undefined,
        onClose: undefined as ((code: number | null) => void) | undefined,
      };
      spawnedProcesses.push(self);
      return {
        args: [...args],
        stdout: {
          on: (_ev: string, cb: (data: unknown) => void) => {
            self.onData = cb;
          },
        },
        stderr: {
          on: (_ev: string, cb: (data: unknown) => void) => {
            self.onStderr = cb;
          },
        },
        stdin: { write: (_s: string) => true },
        kill: (_sig: string) => {},
        on: (ev: string, cb: (arg: unknown) => void) => {
          if (ev === "error") self.onError = cb as (err: Error) => void;
          if (ev === "close")
            self.onClose = cb as (code: number | null) => void;
        },
      };
    },
  };
  return { ...mod, default: mod };
});

vi.mock("../src/services/python-bridge", () => ({
  resolvePythonExecutable: () => ({ path: "/usr/bin/python3", extraArgs: [] }),
  buildRuntimeInstallCommand: () => "pip install",
  paperforgeEnrichedEnv: () => ({}),
  buildTargetedEnv: async () => ({}),
  scanBbtUnderProfiles: () => [],
  scanBbtDirectChildren: () => [],
  runSubprocess: () => {},
}));

vi.mock("../src/services/memory-state", () => ({
  resolveVaultPaths: () => ({}),
  getMemoryRuntime: () => ({}),
  getVectorRuntime: () => ({}),
  getRuntimeHealth: () => ({}),
  isMemoryReady: () => false,
  isVectorReady: () => false,
  getMemoryStatusText: () => "",
  getVectorStatusText: () => "",
  getCachedPython: () => ({ path: "/usr/bin/python3", extraArgs: [] }),
}));

vi.mock("../src/services/ocr-maintenance-ui", () => ({
  categorizeMaintenanceRow: () => [],
  buildMaintenanceSummary: () => ({ items: [], summary: "" }),
  maintenanceActionForRow: () => null,
  maintenanceActionRequiresConfirmation: () => false,
  readMaintenanceCache: () => ({ items: [], updated_at: "" }),
  refreshMaintenanceData: () => Promise.resolve({ data: [] }),
}));

vi.mock("../src/services/managed-runtime", () => ({
  ManagedRuntime: class {},
  runtimeActionsForHealth: () => [],
  resolveRuntimeCommand: (run: unknown) => ({
    command: "/usr/bin/python3",
    args: [],
  }),
}));

vi.mock("../src/utils/disclosure", () => ({
  getDisclosureState: () => false,
  toggleDisclosureState: () => {},
}));

vi.mock("../src/services/progress-parser", () => ({
  processProgressChunk: (chunk: string, _buffer: string) => {
    const events: Array<{
      event: string;
      current?: number;
      total?: number;
      key?: string;
    }> = [];
    for (const line of chunk.split("\n")) {
      const m = line.match(/^(\S+)\s+START\s+(\d+)/);
      if (m) {
        events.push({ event: "START", total: parseInt(m[2]) });
        continue;
      }
      const m2 = line.match(/^(\S+)\s+PROGRESS\s+(\d+)\s+(\d+)(?:\s+(\S+))?/);
      if (m2) {
        events.push({
          event: "PROGRESS",
          current: parseInt(m2[2]),
          total: parseInt(m2[3]),
          key: m2[4] || "",
        });
        continue;
      }
    }
    return { events, buffer: "" };
  },
}));

import { createUnknownEnvelope, ProbeEnvelope } from "../src/constants";
import { PaperForgeSettingTab } from "../src/settings";
import { setLanguage } from "../src/i18n";

// ── Helpers ──
function fakeApp() {
  return {
    vault: { adapter: { basePath: "/vault" }, getConfig: () => "en" },
    workspace: {
      getLeavesOfType: () => [],
      onLayoutReady: (cb: () => void) => cb?.(),
    },
  };
}

function fakePlugin(overrides: Record<string, unknown> = {}) {
  return {
    app: fakeApp(),
    manifest: { id: "paperforge", version: "2.0.0" },
    settings: {} as Record<string, unknown>,
    saveSettings: vi.fn(),
    loadSettings: vi.fn(),
    readPaperforgeJson: () => ({}),
    _ocrProcess: null as unknown,
    _ocrProgress: null as {
      current: number;
      total: number;
      key: string;
    } | null,
    _ocrBuffer: "",
    _ocrWasStopped: false,
    _embedProcess: null as unknown,
    _embedProgress: { current: 0, total: 0, key: "" },
    _embedBuffer: "",
    _autoSyncRunning: false,
    _lastSyncTime: "",
    ...overrides,
  };
}

function makeTab(data: Record<string, unknown> = {}) {
  const tab = new PaperForgeSettingTab(fakeApp() as any, fakePlugin(data));
  // wire managed runtime mock
  const rt = {
    current: () => ({
      path: "/usr/bin/python3",
      version: "3.11",
      state: "ready",
    }),
    status: () => Promise.resolve({ state: "ready" }),
  };
  (tab as any)._ensureManagedRuntime = () => rt;
  (tab as any)._resolveRuntimeCommand = () => ({
    path: "/usr/bin/python3",
    args: [],
  });
  (tab as any)._capabilityState = data.capabilityState || {};
  (tab as any)._selectedDetailModule = "";
  (tab as any)._probing = new Set<string>();
  // Override display() to avoid triggering full render chain in tests
  (tab as any).display = () => {};
  return tab;
}

let dom: JSDOM;

// ── Obsidian DOM polyfills ──
function polyfillObsidianDom(doc: Document) {
  // Polyfill JSDOM's own HTMLElement, not the global one
  const Win = doc.defaultView;
  if (!Win) return;
  const HTMLEl = (Win as any).HTMLElement;
  if (!HTMLEl) return;
  const ht = HTMLEl.prototype;
  const origCreate = doc.createElement.bind(doc);

  if (!ht.createEl) {
    ht.createEl = function (
      tag: string,
      opts?: {
        cls?: string;
        text?: string;
        attr?: Record<string, string>;
        title?: string;
      },
      cb?: (el: HTMLElement) => void
    ) {
      const el = origCreate(tag);
      if (opts?.cls) el.className = opts.cls;
      if (opts?.text) el.textContent = opts.text;
      if (opts?.attr) {
        for (const [k, v] of Object.entries(opts.attr)) {
          el.setAttribute(k, v);
        }
      }
      if (opts?.title) el.title = opts.title;
      this.appendChild(el);
      if (cb) cb(el);
      return el;
    };
    ht.createDiv = function (
      opts?: { cls?: string; text?: string; attr?: Record<string, string> },
      cb?: (el: HTMLElement) => void
    ) {
      return (this as any).createEl("div", opts, cb);
    };
    ht.createSpan = function (
      opts?: { cls?: string; text?: string; attr?: Record<string, string> },
      cb?: (el: HTMLElement) => void
    ) {
      return (this as any).createEl("span", opts, cb);
    };
    ht.empty = function () {
      while (this.firstChild) this.removeChild(this.firstChild);
    };
    ht.setText = function (text: string) {
      this.textContent = text;
    };
    ht.setAttr = function (name: string, value: string) {
      this.setAttribute(name, value);
    };
    ht.appendText = function (text: string) {
      this.appendChild(doc.createTextNode(text));
    };
  }
}

beforeEach(() => {
  dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", {
    url: "http://localhost",
    pretendToBeVisual: true,
  });
  polyfillObsidianDom(dom.window.document);
  (globalThis as any).window = dom.window;
  (globalThis as any).document = dom.window.document;
  (globalThis as any).confirm = () => true;

  noticeCalls.length = 0;
  spawnedProcesses.length = 0;
  execFileCalls.length = 0;
  setLanguage(fakeApp() as any);
});

afterEach(() => {
  dom.window.close();
});

// ════════════════════════════════ 1. Library Detail ════════════════════
describe("Library module detail (Issue #78)", () => {
  it("renders envelope shell with heading, no duplicate CTA", () => {
    const tab = makeTab();
    const el = dom.window.document.createElement("div");
    (tab as any)._renderLibraryDetail(el);
    expect(el.querySelector(".pf-module-detail-heading")).not.toBeNull();
    expect(el.querySelector(".mod-cta")).toBeNull();
  });

  it("renders reason, timestamp, TTL, notices, diagnostics", () => {
    const env = {
      ...createUnknownEnvelope("library"),
      capability_state: "needs_action",
      severity: "warning",
      reason: { code: "library.index_stale", text: "Index is stale" },
      updated_at: "2026-01-15T12:00:00Z",
      ttl_seconds: 300,
      notices: [{ level: "warning", message: "Test notice" }],
      action: {
        primary: {
          action_id: "library.sync",
          verb: "sync",
          label: "Sync",
          command: "paperforge sync",
          availability: "available",
          safety_class: "safe",
          preservation_facts: [],
          replacement_facts: [],
          interruptible: true,
          confirmation_required: false,
          confirmation_prompt: null,
          scope: "module",
          scope_count: 1,
        },
      },
    } as any;
    const tab = makeTab({ capabilityState: { library: env } });
    const el = dom.window.document.createElement("div");
    (tab as any)._renderLibraryDetail(el);
    expect(el.textContent).toContain("stale");
    expect(el.textContent).toContain("300s");
    expect(el.textContent).toContain("Test notice");
    expect(el.querySelector(".pf-module-diagnostics")).not.toBeNull();
  });

  it("primary action click overlays envelope running", () => {
    const tab = makeTab();
    (tab as any)._capabilityState = {
      library: {
        ...createUnknownEnvelope("library"),
        capability_state: "needs_action",
        severity: "warning",
        reason: { code: "library.index_stale", text: "stale" },
        action: {
          primary: {
            action_id: "library.sync",
            verb: "sync",
            label: "Sync",
            command: "paperforge sync",
            availability: "available",
            safety_class: "safe",
            preservation_facts: [],
            replacement_facts: [],
            interruptible: true,
            confirmation_required: false,
            confirmation_prompt: null,
            scope: "module",
            scope_count: 1,
          },
        },
      },
    };
    const el = dom.window.document.createElement("div");
    (tab as any)._renderLibraryDetail(el);
    (
      el.querySelector(".pf-module-summary .pf-action-btn") as HTMLButtonElement
    )?.click();
    const envelopes = (tab as any)._capabilityState as any;
    expect(envelopes?.library?.activity_state).toBe("running");
    expect(envelopes?.library?.activity_label).toContain("Syncing");
  });
});

// ════════════════════════════════ 2. OCR Detail ════════════════════════
describe("OCR module detail (Issue #78)", () => {
  it("renders stop only when _ocrProcess exists", () => {
    const tab = makeTab({
      _ocrProcess: { stdin: { write: () => true }, kill: () => {} },
      _ocrProgress: { current: 3, total: 10, key: "TEST" },
    });
    const ocrEnv = {
      ...createUnknownEnvelope("ocr"),
      capability_state: "needs_action",
      activity_state: "running",
      severity: "warning",
      reason: { code: "ocr.artifacts_stale", text: "Stale" },
      action: {
        primary: {
          action_id: "ocr.rebuild_derived",
          verb: "rebuild_derived",
          label: "Rebuild",
          command: "paperforge ocr rebuild --all",
          availability: "available",
          safety_class: "safe",
          preservation_facts: [],
          replacement_facts: [],
          interruptible: true,
          confirmation_required: false,
          confirmation_prompt: null,
          scope: "module",
          scope_count: 1,
        },
      },
    } as any;
    (tab as any)._capabilityState = { ocr: ocrEnv };
    const el = dom.window.document.createElement("div");
    (tab as any)._renderOcrDetail(el);
    expect(el.querySelector(".mod-warning")).not.toBeNull();
    expect(el.textContent).toContain("3/10");

    const tab2 = makeTab({ _ocrProcess: null });
    (tab2 as any)._capabilityState = { ocr: ocrEnv };
    const el2 = dom.window.document.createElement("div");
    (tab2 as any)._renderOcrDetail(el2);
    expect(el2.querySelector(".mod-warning")).toBeNull();
  });

  it("stop sends PAPERFORGE_STOP\n via stdin", () => {
    let written = "";
    const tab = makeTab({
      _ocrProcess: {
        stdin: {
          write: (s: string) => {
            written = s;
            return true;
          },
        },
        kill: () => {},
      },
    });
    (tab as any)._capabilityState = {
      ocr: {
        ...createUnknownEnvelope("ocr"),
        activity_state: "running",
        capability_state: "needs_action",
        severity: "warning",
        reason: { code: "x", text: "x" },
        action: {
          primary: {
            action_id: "ocr.rebuild_derived",
            verb: "rebuild_derived",
            label: "Rebuild",
            command: "paperforge ocr rebuild --all",
            availability: "available",
            safety_class: "safe",
            preservation_facts: [],
            replacement_facts: [],
            interruptible: true,
            confirmation_required: false,
            confirmation_prompt: null,
            scope: "module",
            scope_count: 1,
          },
        },
      },
    };
    const el = dom.window.document.createElement("div");
    (tab as any)._renderOcrDetail(el);
    (el.querySelector(".mod-warning") as HTMLButtonElement)?.click();
    expect(written).toBe("PAPERFORGE_STOP\n");
    expect((tab.plugin as any)._ocrWasStopped).toBe(true);
  });

  it("stop falls back to SIGINT when stdin unavailable", () => {
    let killed = "";
    const tab = makeTab({
      _ocrProcess: {
        kill: (sig: string) => {
          killed = sig;
        },
      },
    });
    (tab as any)._capabilityState = {
      ocr: {
        ...createUnknownEnvelope("ocr"),
        activity_state: "running",
        capability_state: "needs_action",
        severity: "warning",
        reason: { code: "x", text: "x" },
        action: {
          primary: {
            action_id: "ocr.rebuild_derived",
            verb: "rebuild_derived",
            label: "Rebuild",
            command: "paperforge ocr rebuild --all",
            availability: "available",
            safety_class: "safe",
            preservation_facts: [],
            replacement_facts: [],
            interruptible: true,
            confirmation_required: false,
            confirmation_prompt: null,
            scope: "module",
            scope_count: 1,
          },
        },
      },
    };
    const el = dom.window.document.createElement("div");
    (tab as any)._renderOcrDetail(el);
    (el.querySelector(".mod-warning") as HTMLButtonElement)?.click();
    expect(killed).toBe("SIGINT");
  });
});

// ════════════════════════════════ 3. Memory Detail ════════════════════
describe("Memory module detail (Issue #78)", () => {
  it("renders envelope shell without duplicate CTA", () => {
    const tab = makeTab();
    (tab as any)._capabilityState = {
      memory: {
        ...createUnknownEnvelope("memory"),
        capability_state: "needs_action",
        severity: "warning",
        reason: { code: "x", text: "x" },
        action: {
          primary: {
            action_id: "module.run",
            verb: "run",
            label: "Build",
            command: "paperforge memory build",
            availability: "available",
            safety_class: "safe",
            preservation_facts: [],
            replacement_facts: [],
            interruptible: true,
            confirmation_required: false,
            confirmation_prompt: null,
            scope: "module",
            scope_count: 1,
          },
        },
      },
    };
    const el = dom.window.document.createElement("div");
    (tab as any)._renderMemoryDetail(el);
    expect(el.querySelector(".pf-module-detail-heading")).not.toBeNull();
    expect(el.querySelector(".mod-cta")).toBeNull();
  });

  it("renders Build Index for a stale vector index and dispatches its exact action", async () => {
    const tab = makeTab();
    (tab as any)._capabilityState = {
      memory: {
        ...createUnknownEnvelope("memory"),
        capability_state: "needs_action",
        user_state: "action_required",
        reason: { code: "memory.index_stale", text: "Index stale" },
        action: {
          primary: {
            action_id: "memory.rebuild_vector",
            verb: "rebuild_index",
            label: "Build vector index",
            command: "paperforge embed build --force",
            availability: "available",
            safety_class: "safe",
            preservation_facts: [],
            replacement_facts: [],
            interruptible: true,
            confirmation_required: false,
            confirmation_prompt: null,
            scope: "module",
            scope_count: 1,
          },
        },
      },
    };
    const el = dom.window.document.createElement("div");
    (tab as any)._renderMemoryDetail(el);
    const button = [...el.querySelectorAll("button")].find(
      (node) => node.textContent === "Build Index"
    ) as HTMLButtonElement | undefined;
    expect(button).toBeDefined();
    spawnedProcesses.length = 0;
    button?.click();
    await Promise.resolve();
    expect(
      spawnedProcesses.some((process) =>
        process.args.join(" ").includes("embed build --force")
      )
    ).toBe(true);
  });

  it("hides the action-required impact box once the vector index is ready", () => {
    const tab = makeTab();
    (tab as any)._capabilityState = {
      memory: {
        ...createUnknownEnvelope("memory"),
        capability_state: "ready",
        user_state: "ready",
        severity: "ok",
        reason: { code: "memory.ready", text: "Index ready" },
        action: { primary: null },
      },
    };
    const el = dom.window.document.createElement("div");
    (tab as any)._renderMemoryDetail(el);

    expect(el.querySelector(".pf-sr-impact-box")).toBeNull();
    expect(el.querySelectorAll(".pf-sr-cfg-input")).toHaveLength(3);
  });
});

// ════════════════════════════════ 4. Dispatch allowlist ════════════════
describe("_dispatchModuleAction allowlist (Issue #78)", () => {
  it("unknown pair -> Notice + re-probe", () => {
    const tab = makeTab();
    (tab as any)._capabilityState = {
      library: createUnknownEnvelope("library"),
    };
    (tab as any)._probing = new Set<string>();
    const env = {
      ...createUnknownEnvelope("library"),
      action: {
        primary: {
          action_id: "module.bogus",
          verb: "bogus",
          label: "X",
          command: "x",
          availability: "available",
          safety_class: "safe",
          preservation_facts: [],
          replacement_facts: [],
          interruptible: true,
          confirmation_required: false,
          confirmation_prompt: null,
          scope: "module",
          scope_count: 1,
        },
      },
    } as any;
    noticeCalls.length = 0;
    (tab as any)._dispatchModuleAction("library", env);
    // Should emit a Notice with "Unknown"
    const msgs = noticeCalls.map((c: { msg: string }) => c.msg).join(" ");
    expect(msgs.length).toBeGreaterThan(0);
    expect(msgs.toLowerCase()).toMatch(/unknown|bogus/);
  });

  it("run + paperforge ocr run -> spawns ['ocr', 'run']", () => {
    const tab = makeTab();
    (tab as any)._capabilityState = { ocr: createUnknownEnvelope("ocr") };
    const env = {
      ...createUnknownEnvelope("ocr"),
      action: {
        primary: {
          action_id: "module.run",
          verb: "run",
          label: "Run",
          command: "paperforge ocr run",
          availability: "available",
          safety_class: "safe",
          preservation_facts: [],
          replacement_facts: [],
          interruptible: true,
          confirmation_required: false,
          confirmation_prompt: null,
          scope: "module",
          scope_count: 1,
        },
      },
    } as any;
    (tab as any)._dispatchModuleAction("ocr", env);
    const last = spawnedProcesses[spawnedProcesses.length - 1];
    expect(last.args).toContain("run");
    expect(last.args).not.toContain("rebuild");
  });

  it("rebuild_derived -> spawns rebuild --all", () => {
    const tab = makeTab();
    (tab as any)._capabilityState = { ocr: createUnknownEnvelope("ocr") };
    const env = {
      ...createUnknownEnvelope("ocr"),
      action: {
        primary: {
          action_id: "ocr.rebuild_derived",
          verb: "rebuild_derived",
          label: "Rebuild",
          command: "paperforge ocr rebuild --all",
          availability: "available",
          safety_class: "safe",
          preservation_facts: [],
          replacement_facts: [],
          interruptible: true,
          confirmation_required: false,
          confirmation_prompt: null,
          scope: "module",
          scope_count: 1,
        },
      },
    } as any;
    (tab as any)._dispatchModuleAction("ocr", env);
    const last = spawnedProcesses[spawnedProcesses.length - 1];
    expect(last.args).toContain("rebuild");
    expect(last.args).toContain("--all");
  });

  it("redo -> spawns redo args", () => {
    const tab = makeTab();
    (tab as any)._capabilityState = { ocr: createUnknownEnvelope("ocr") };
    const env = {
      ...createUnknownEnvelope("ocr"),
      action: {
        primary: {
          action_id: "ocr.redo",
          verb: "redo",
          label: "Redo",
          command: "paperforge ocr redo",
          availability: "available",
          safety_class: "destructive",
          preservation_facts: [],
          replacement_facts: ["OCR artifacts"],
          interruptible: true,
          confirmation_required: true,
          confirmation_prompt: "Proceed?",
          scope: "module",
          scope_count: 1,
        },
      },
    } as any;
    modalOpens.length = 0;
    spawnedProcesses.length = 0;
    (tab as any)._dispatchModuleAction("ocr", env);
    expect(modalOpens.length).toBe(1);
    expect(modalOpens[0].effectLabel).toBe("OCR artifacts");
    expect(spawnedProcesses.length).toBe(0);
    if (modalOpens[0].onConfirm) modalOpens[0].onConfirm();
    expect(spawnedProcesses[spawnedProcesses.length - 1].args).toContain(
      "redo"
    );
  });

  it("memory build -> uses execFile", () => {
    const tab = makeTab();
    (tab as any)._capabilityState = { memory: createUnknownEnvelope("memory") };
    const env = {
      ...createUnknownEnvelope("memory"),
      action: {
        primary: {
          action_id: "module.run",
          verb: "run",
          label: "Build",
          command: "paperforge memory build",
          availability: "available",
          safety_class: "safe",
          preservation_facts: [],
          replacement_facts: [],
          interruptible: true,
          confirmation_required: false,
          confirmation_prompt: null,
          scope: "module",
          scope_count: 1,
        },
      },
    } as any;
    execFileCalls.length = 0;
    (tab as any)._dispatchModuleAction("memory", env);
    expect(
      execFileCalls.some((c: { args: string[] }) => c.args.includes("build"))
    ).toBe(true);
  });

  it("embed build --force -> spawns embed", async () => {
    const tab = makeTab();
    (tab as any)._capabilityState = { memory: createUnknownEnvelope("memory") };
    const env = {
      ...createUnknownEnvelope("memory"),
      action: {
        primary: {
          action_id: "memory.rebuild_vector",
          verb: "rebuild_index",
          label: "Embed",
          command: "paperforge embed build --force",
          availability: "available",
          safety_class: "safe",
          preservation_facts: [],
          replacement_facts: [],
          interruptible: true,
          confirmation_required: false,
          confirmation_prompt: null,
          scope: "module",
          scope_count: 1,
        },
      },
    } as any;
    (tab as any)._dispatchModuleAction("memory", env);
    await Promise.resolve();
    const es = spawnedProcesses.find((p: { args: string[] }) =>
      p.args.includes("embed")
    );
    expect(es?.args).toContain("--force");
  });

  it("destructive opens modal with correct effect label", () => {
    const tab = makeTab();
    const env = {
      ...createUnknownEnvelope("ocr"),
      action: {
        primary: {
          action_id: "ocr.redo",
          verb: "redo",
          label: "Redo",
          command: "paperforge ocr redo",
          availability: "available",
          safety_class: "destructive",
          preservation_facts: [],
          replacement_facts: ["OCR artifacts"],
          interruptible: true,
          confirmation_required: true,
          confirmation_prompt: "Proceed?",
          scope: "module",
          scope_count: 1,
        },
      },
    } as any;
    modalOpens.length = 0;
    spawnedProcesses.length = 0;
    (tab as any)._dispatchModuleAction("ocr", env);
    expect(modalOpens.length).toBe(1);
    expect(modalOpens[0].title).toBe("Redo");
    expect(modalOpens[0].effectLabel).toBe("OCR artifacts");
    expect(spawnedProcesses.length).toBe(0);
  });
  it("investigate+issue-draft opens PaperForgeIssueDraftModal with scope_count", () => {
    const tab = makeTab();
    (tab as any)._capabilityState = { ocr: createUnknownEnvelope("ocr") };
    const env = {
      ...createUnknownEnvelope("ocr"),
      action: {
        primary: {
          verb: "investigate",
          label: "Report OCR issue",
          command: "paperforge ocr issue-draft",
          availability: "available",
          safety_class: "safe",
          preservation_facts: [],
          replacement_facts: [],
          interruptible: true,
          confirmation_required: false,
          confirmation_prompt: null,
          scope: "all",
          scope_count: 5,
        },
      },
      reason: {
        code: "ocr.quality_unacceptable",
        text: "OCR output unacceptable for 5 papers",
      },
    } as any;
    modalOpens.length = 0;
    (tab as any)._dispatchModuleAction("ocr", env);
    const draftOpens = modalOpens.filter(
      (o) => o.kind === "PaperForgeIssueDraftModal"
    );
    expect(draftOpens.length).toBe(1);
    const draft = draftOpens[0].draft;
    expect(draft && typeof draft === "object" && "labels" in draft).toBe(true);
    if (draft && typeof draft === "object" && "labels" in draft) {
      expect(Reflect.get(draft, "labels")).toEqual([
        "ocr",
        "quality",
        "auto-generated",
      ]);
      expect(String(Reflect.get(draft, "title") ?? "")).toContain("5");
      expect(String(Reflect.get(draft, "body") ?? "")).toContain("5");
    }
  });

  it("setup verb with wrong command falls through to Notice", () => {
    const tab = makeTab();
    noticeCalls.length = 0;
    const env = {
      ...createUnknownEnvelope("library"),
      action: {
        primary: {
          verb: "setup",
          label: "Setup",
          command: "paperforge sync",
          availability: "available",
          safety_class: "safe",
          preservation_facts: [],
          replacement_facts: [],
          interruptible: true,
          confirmation_required: false,
          confirmation_prompt: null,
          scope: "module",
          scope_count: 1,
        },
      },
    } as any;
    (tab as any)._dispatchModuleAction("library", env);
    const msgs = noticeCalls.map((c: { msg: string }) => c.msg).join(" ");
    expect(msgs.toLowerCase()).toMatch(/unknown|setup/);
  });

  it("probe verb with wrong command falls through to Notice", () => {
    const tab = makeTab();
    noticeCalls.length = 0;
    const env = {
      ...createUnknownEnvelope("ocr"),
      action: {
        primary: {
          verb: "probe",
          label: "Probe",
          command: "probe installation",
          availability: "available",
          safety_class: "safe",
          preservation_facts: [],
          replacement_facts: [],
          interruptible: true,
          confirmation_required: false,
          confirmation_prompt: null,
          scope: "module",
          scope_count: 1,
        },
      },
    } as any;
    (tab as any)._dispatchModuleAction("ocr", env);
    const msgs = noticeCalls.map((c: { msg: string }) => c.msg).join(" ");
    expect(msgs.toLowerCase()).toMatch(/unknown|probe/);
  });
});

// ════════════════════════════════ 5. _dispatchOcrAction ══════════════
describe("_dispatchOcrAction lifecycle (Issue #78)", () => {
  it("assigns _ocrProcess, sets activity overlay", () => {
    const tab = makeTab();
    (tab as any)._capabilityState = { ocr: createUnknownEnvelope("ocr") };
    spawnedProcesses.length = 0;
    (tab as any)._dispatchOcrAction("run");
    // Verify spawn was called with correct args
    expect(spawnedProcesses.length).toBeGreaterThan(0);
    expect(spawnedProcesses[0].args).toContain("run");
    // Verify _ocrProcess was assigned (mock spawn returns truthy)
    expect((tab.plugin as any)._ocrProcess).toBeTruthy();
    // Verify activity overlay
    const e = (tab as any)._capabilityState as any;
    expect(e?.ocr?.activity_state).toBe("running");
  });

  it("parses START/PROGRESS into activity_progress", () => {
    const tab = makeTab();
    (tab as any)._capabilityState = { ocr: createUnknownEnvelope("ocr") };
    (tab as any)._dispatchOcrAction("rebuild");
    const proc = spawnedProcesses[spawnedProcesses.length - 1];
    proc?.onData?.("OCR_REBUILD START 20\n");
    expect((tab.plugin as any)._ocrProgress.total).toBe(20);
    proc?.onData?.("OCR_REBUILD PROGRESS 5 20 KEY1\n");
    expect((tab.plugin as any)._ocrProgress.current).toBe(5);
  });

  it("clears activity and re-probes on close/error/stop", () => {
    const probes: string[] = [];
    const tab = makeTab();
    (tab as any)._probeModule = (mod: string) => {
      probes.push(mod);
    };
    (tab as any)._capabilityState = { ocr: createUnknownEnvelope("ocr") };
    (tab as any)._dispatchOcrAction("run");
    spawnedProcesses[spawnedProcesses.length - 1]?.onClose?.(0);
    expect((tab.plugin as any)._ocrProcess).toBeNull();
    expect(probes).toContain("ocr");
    expect(((tab as any)._capabilityState as any)?.ocr?.activity_state).toBe(
      "idle"
    );
  });

  it("exact CLI args: run/rebuild/redo", () => {
    for (const [mode, expected] of [
      ["run", "run"],
      ["rebuild", "rebuild"],
      ["redo", "redo"],
    ] as const) {
      const tab = makeTab();
      (tab as any)._capabilityState = { ocr: createUnknownEnvelope("ocr") };
      spawnedProcesses.length = 0;
      (tab as any)._dispatchOcrAction(mode);
      expect(spawnedProcesses[0].args).toContain(expected);
      if (mode === "rebuild")
        expect(spawnedProcesses[0].args).toContain("--all");
    }
  });

  it("does not change capability_state/severity during activity", () => {
    const tab = makeTab();
    (tab as any)._capabilityState = {
      ocr: {
        ...createUnknownEnvelope("ocr"),
        capability_state: "needs_action",
        severity: "warning",
      },
    };
    (tab as any)._dispatchOcrAction("run");
    const e = (tab as any)._capabilityState as any;
    expect(e?.ocr?.capability_state).toBe("needs_action");
    expect(e?.ocr?.severity).toBe("warning");
    expect(e?.ocr?.activity_state).toBe("running");
  });
});

// ════════════════════════════════ 6. _dispatchMemoryBuild ════════════
describe("_dispatchMemoryBuild (Issue #78)", () => {
  it("build mode overlays envelope, uses execFile", () => {
    const tab = makeTab();
    (tab as any)._capabilityState = { memory: createUnknownEnvelope("memory") };
    execFileCalls.length = 0;
    // _dispatchMemoryBuild("build") should set activity overlay and spawn execFile
    (tab as any)._dispatchMemoryBuild("build");
    const e = (tab as any)._capabilityState as any;
    expect(e?.memory?.activity_state).toBe("running");
    expect(e?.memory?.activity_label).toContain("Building memory");
    // execFile should have been called with args containing "build"
    const buildCalls = execFileCalls.filter((c: { args: string[] }) =>
      c.args.some((a) => a === "build")
    );
    expect(buildCalls.length).toBeGreaterThan(0);
  });

  it("embed mode overlays envelope, spawns embed --force", async () => {
    const tab = makeTab();
    (tab as any)._capabilityState = { memory: createUnknownEnvelope("memory") };
    (tab as any)._dispatchMemoryBuild("embed");
    await Promise.resolve();
    expect(
      ((tab as any)._capabilityState as any)?.memory?.activity_label
    ).toContain("vector");
    const es = spawnedProcesses.find((p: { args: string[] }) =>
      p.args.includes("embed")
    );
    expect(es?.args).toContain("--force");
  });

  it("shows the command's terminal diagnostic when an embed build fails", async () => {
    const tab = makeTab();
    noticeCalls.length = 0;
    (tab as any)._capabilityState = { memory: createUnknownEnvelope("memory") };
    (tab as any)._dispatchMemoryBuild("embed");
    await Promise.resolve();
    const process = spawnedProcesses.find((p: { args: string[] }) =>
      p.args.includes("embed")
    );
    process?.onStderr?.(
      "Traceback (most recent call last):\nUnboundLocalError: vec0 unavailable\n"
    );
    process?.onClose?.(1);

    const messages = noticeCalls.map((c: { msg: string }) => c.msg).join(" ");
    expect(messages).toContain("UnboundLocalError: vec0 unavailable");
  });

  it("injects the current secure credential profile into embed builds", () => {
    const tab = makeTab();
    (tab as any)._capabilityState = { memory: createUnknownEnvelope("memory") };
    const launch = vi
      .spyOn(tab as any, "_callPython")
      .mockReturnValue({} as never);
    (tab as any)._dispatchMemoryBuild("embed");
    expect(launch).toHaveBeenCalledWith(
      ["embed", "build", "--force"],
      expect.objectContaining({ credentialType: "embed", stream: true })
    );
  });

  it("embed parses PROGRESS into activity_progress", async () => {
    const tab = makeTab();
    (tab as any)._capabilityState = { memory: createUnknownEnvelope("memory") };
    (tab as any)._dispatchMemoryBuild("embed");
    await Promise.resolve();
    spawnedProcesses
      .find((p: { args: string[] }) => p.args.includes("embed"))
      ?.onData?.("MEMORY_EMBED PROGRESS 100 500\n");
    expect((tab.plugin as any)._embedProgress.current).toBe(100);
  });
});

// ════════════════════════════════ 7. Focus/back ══════════════════════
describe("focus and back navigation (Issue #78)", () => {
  it("heading tabindex=-1, back sets focus target", () => {
    const tab = makeTab();
    const el = dom.window.document.createElement("div");
    (tab as any)._renderLibraryDetail(el);
    expect(
      el.querySelector("#pf-library-detail-heading")?.getAttribute("tabindex")
    ).toBe("-1");
    (el.querySelector(".pf-back-btn") as HTMLButtonElement)?.click();
    expect((tab as any)._focusTargetId).toContain("library");
  });
});

// ════════════════════════════════ 8. Module selector ═════════════════
describe("module detail selector (Issue #78)", () => {
  it("shows five modules, active state, and Smart Retrieval navigation", () => {
    const tab = makeTab();
    const el = dom.window.document.createElement("div");
    (tab as any)._renderOcrDetail(el);
    expect(el.querySelectorAll(".pf-module-detail-btn").length).toBe(5);
    expect(
      el.querySelector(".pf-module-detail-btn--active")?.textContent
    ).toContain("OCR");
    const retrievalBtn = Array.from(
      el.querySelectorAll(".pf-module-detail-btn")
    ).find((button) => button.textContent?.includes("Smart Retrieval"));
    (retrievalBtn as HTMLButtonElement)?.click();
    expect((tab as any)._selectedDetailModule).toBe("memory");
  });
});

// ════════════════════════════════ 9. Destructive + disabled ══════════
describe("destructive metadata and disabled-while-running (Issue #78)", () => {
  it("opens impact confirmation for destructive actions", () => {
    const ocrEnv = {
      ...createUnknownEnvelope("ocr"),
      user_state: "action_required",
      action: {
        primary: {
          action_id: "ocr.redo",
          verb: "redo",
          label: "Redo",
          command: "paperforge ocr redo",
          safety_class: "destructive",
          availability: "available",
          preservation_facts: [],
          replacement_facts: ["Deletes derived OCR artifacts"],
          interruptible: true,
          confirmation_required: true,
          confirmation_prompt: "Proceed?",
          scope: "module",
          scope_count: 1,
        },
      },
    } as any;
    const tab = makeTab({ capabilityState: { ocr: ocrEnv } });
    const el = dom.window.document.createElement("div");
    (tab as any)._renderOcrDetail(el);
    (
      el.querySelector(".pf-module-summary .pf-action-btn") as HTMLButtonElement
    ).click();
    expect(modalOpens.at(-1)?.kind).toBe("PaperForgeConfirmModal");
    expect(modalOpens.at(-1)?.effectLabel).toContain("Deletes derived OCR");
  });

  it("action button disabled when running", () => {
    const ocrEnv = {
      ...createUnknownEnvelope("ocr"),
      activity_state: "running",
      action: {
        primary: {
          action_id: "ocr.rebuild_derived",
          verb: "rebuild_derived",
          label: "Rebuild",
          command: "paperforge ocr rebuild --all",
          availability: "available",
          safety_class: "safe",
          preservation_facts: [],
          replacement_facts: [],
          interruptible: true,
          confirmation_required: false,
          confirmation_prompt: null,
          scope: "module",
          scope_count: 1,
        },
      },
    } as any;
    const tab = makeTab({ capabilityState: { ocr: ocrEnv } });
    const el = dom.window.document.createElement("div");
    (tab as any)._renderOcrDetail(el);
    expect(
      (
        el.querySelector(
          ".pf-module-summary .pf-action-btn"
        ) as HTMLButtonElement
      )?.hasAttribute("disabled")
    ).toBe(true);
  });
});

// ════════════════════════════════ 10. Library sync failure probe ═══════
describe("Library sync failure probe (Issue #78)", () => {
  it("_probeModule library with nonzero exit code appends --last-operation-exit-code", () => {
    const tab = makeTab();
    execFileCalls.length = 0;

    (tab as any)._probeModule("library", 1);

    // Probe execFile call must include --last-operation-exit-code 1
    const probeCall = execFileCalls.find(
      (c) => c.args.includes("probe") && c.args.includes("library")
    );
    expect(probeCall).toBeDefined();
    const lastOpIdx = probeCall!.args.indexOf("--last-operation-exit-code");
    expect(lastOpIdx).toBeGreaterThan(-1);
    expect(probeCall!.args[lastOpIdx + 1]).toBe("1");
  });

  it("_probeModule library without exit code omits --last-operation-exit-code", () => {
    const tab = makeTab();
    execFileCalls.length = 0;

    (tab as any)._probeModule("library");

    const probeCall = execFileCalls.find(
      (c) => c.args.includes("probe") && c.args.includes("library")
    );
    expect(probeCall).toBeDefined();
    expect(probeCall!.args.indexOf("--last-operation-exit-code")).toBe(-1);
  });

  it("_probeModule non-library with exit code omits --last-operation-exit-code", () => {
    const tab = makeTab();
    execFileCalls.length = 0;

    (tab as any)._probeModule("ocr", 1);

    // OCR must NOT get --last-operation-exit-code
    const probeCall = execFileCalls.find(
      (c) => c.args.includes("probe") && c.args.includes("ocr")
    );
    expect(probeCall).toBeDefined();
    expect(probeCall!.args.indexOf("--last-operation-exit-code")).toBe(-1);
  });

  it("failed _runManualSync onClose passes nonzero code to probe", () => {
    const tab = makeTab();
    execFileCalls.length = 0;

    (tab as any)._runManualSync();

    // First call is sync, second (after onClose) is probe
    const syncCall = execFileCalls.find(
      (c) => c.args.includes("sync") && !c.args.includes("probe")
    );
    expect(syncCall).toBeDefined();

    // Simulate sync failure by invoking the onClose directly
    if (syncCall!.cb) syncCall!.cb(new Error("sync failed"), "", "error");

    // After sync failure, _probeModule should append --last-operation-exit-code 1
    const probeCall = execFileCalls.find(
      (c) =>
        c.args.includes("probe") &&
        c.args.includes("library") &&
        c.args.includes("--last-operation-exit-code")
    );
    expect(probeCall).toBeDefined();
    const lastOpIdx = probeCall!.args.indexOf("--last-operation-exit-code");
    expect(probeCall!.args[lastOpIdx + 1]).toBe("1");
  });

  it("successful _runManualSync onClose passes 0 to probe (no flag)", () => {
    const tab = makeTab();
    execFileCalls.length = 0;

    (tab as any)._runManualSync();

    const syncCall = execFileCalls.find(
      (c) => c.args.includes("sync") && !c.args.includes("probe")
    );
    expect(syncCall).toBeDefined();

    // Simulate sync success: code=0
    if (syncCall!.cb) syncCall!.cb(null, "success", "");

    // After success (code=0), probe should NOT have --last-operation-exit-code
    const probeCalls = execFileCalls.filter(
      (c) => c.args.includes("probe") && c.args.includes("library")
    );
    const failureProbe = probeCalls.find((c) =>
      c.args.includes("--last-operation-exit-code")
    );
    expect(failureProbe).toBeUndefined();
  });

  it("sync_failed envelope renders actionable on failure probe", () => {
    const syncFailedEnv: ProbeEnvelope = {
      schema_version: 1,
      module: "library",
      capability_state: "needs_action",
      activity_state: "idle",
      activity_label: null,
      activity_progress: null,
      severity: "error",
      reason: {
        code: "library.sync_failed",
        text: "Library sync failed (exit code 1)",
      },
      action: {
        primary: {
          action_id: "library.sync",
          verb: "sync",
          label: "Sync library",
          command: "paperforge sync",
          availability: "available",
          safety_class: "safe",
          preservation_facts: [],
          replacement_facts: [],
          interruptible: true,
          confirmation_required: false,
          confirmation_prompt: null,
          scope: "module",
          scope_count: 1,
        },
      },
      notices: [],
      updated_at: new Date().toISOString(),
      ttl_seconds: 300,
    };
    const tab = makeTab({ capabilityState: { library: syncFailedEnv } });
    const el = dom.window.document.createElement("div");
    (tab as any)._renderLibraryDetail(el);

    expect(el.textContent).toContain("Last library sync failed");
    expect(el.textContent).not.toContain("exit code 1");
    expect(
      el.querySelector(".pf-module-summary .pf-action-btn")
    ).not.toBeNull();
  });

  it("null _runManualSync onClose forwards sentinel 1 via code ?? 1", () => {
    const tab = makeTab();
    execFileCalls.length = 0;

    // Override _callPython on this tab to invoke opts.onClose(null, ...)
    // simulating a process exit with null code (timeout/kill).
    const origCallPython = (tab as any)._callPython.bind(tab);
    (tab as any)._callPython = (args: string[], opts: any) => {
      // Only intercept sync; pass other calls through
      if (args.includes("sync")) {
        // Simulate process close with null code
        if (opts.onClose) opts.onClose(null, "", "sync killed");
        return null;
      }
      return origCallPython(args, opts);
    };

    (tab as any)._runManualSync();

    // After _runManualSync triggers onClose(null), probe should have --last-operation-exit-code 1
    const probeCall = execFileCalls.find(
      (c) =>
        c.args.includes("probe") &&
        c.args.includes("library") &&
        c.args.includes("--last-operation-exit-code")
    );
    expect(probeCall).toBeDefined();
    const lastOpIdx = probeCall!.args.indexOf("--last-operation-exit-code");
    expect(probeCall!.args[lastOpIdx + 1]).toBe("1");
  });
});
