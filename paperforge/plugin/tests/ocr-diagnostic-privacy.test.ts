/**
 * R1 OCR diagnostic privacy — negative egress tests.
 *
 * Synthetic secrets must never reach the clipboard payload, the issue-draft
 * object, or the external GitHub URL — even when the probe reason text,
 * setup failure, or vault path carries them. Builders omit free text at the
 * type level (allowlist only); regex redaction is defense in depth.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { JSDOM } from "jsdom";

const { modalOpens, runtimePointer } = vi.hoisted(() => ({
  modalOpens: [] as Array<{ kind: string; draft: unknown }>,
  runtimePointer: { value: null as Record<string, string> | null },
}));

vi.mock("../src/release-notes.json", () => ({ default: { versions: [] } }));

vi.mock("obsidian", () => ({
  PluginSettingTab: class {
    containerEl: HTMLDivElement;
    app: Record<string, unknown>;
    constructor(app: Record<string, unknown>) {
      this.app = app;
      this.containerEl = document.createElement("div");
    }
  },
  App: class {},
  Setting: class {
    constructor() {}
  },
  Modal: class {
    app: Record<string, unknown>;
    contentEl: HTMLDivElement;
    constructor(app: Record<string, unknown>) {
      this.app = app;
      this.contentEl = document.createElement("div");
    }
    // Record only: the test drives the real modal explicitly, after augment.
    open() {
      const self = this as unknown as Record<string, unknown>;
      modalOpens.push({
        kind: this.constructor.name,
        draft: self["_draft"] ?? null,
      });
    }
    close() {}
    onOpen() {}
    onClose() {}
  },
  Notice: class {
    constructor() {}
  },
  setTooltip: () => {},
  Platform: {},
}));

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
      _p: string,
      _a: string[],
      _o: Record<string, unknown>,
      cb?: (err: Error | null, stdout: string, stderr: string) => void
    ) => {
      if (cb) cb(null, "{}", "");
    },
    execFileSync: () => "Python 3.11.0",
    exec: () => {},
    spawn: () => ({ on: () => {}, stdin: { write: () => {} }, kill: () => {} }),
  };
  return { ...mod, default: mod };
});

vi.mock("../src/services/python-bridge", () => ({
  scanBbtUnderProfiles: () => [],
  scanBbtDirectChildren: () => [],
  runSubprocess: () => {},
}));
vi.mock("../src/services/managed-runtime", () => ({
  readRuntimePointer: () => runtimePointer.value,
  resolveRuntimeCommand: () => ({ path: "/usr/bin/python3", args: [] }),
}));
vi.mock("../src/utils/disclosure", () => ({
  getDisclosureState: () => false,
  toggleDisclosureState: () => {},
}));
vi.mock("../src/services/progress-parser", () => ({
  processProgressChunk: () => ({ events: [], buffer: "" }),
}));

import { PaperForgeSettingTab } from "../src/settings";
import type { ActionPrimary, ProbeEnvelope } from "../src/client/probe-types";
import {
  buildSupportDiagnostic,
  collectDiagnosticModules,
  copySupportDiagnostic,
  type DiagnosticInput,
} from "../src/primitives";
import {
  buildRedactedDraft,
  PaperForgeIssueDraftModal,
  type PublicIssueDraft,
} from "../src/views/modals";

// ── Synthetic secrets (never real credentials/paths) ──
const TOKEN = "sk-live-SYNTHETIC-abcdef1234567890";
const USER_PATH = "C:\\Users\\synthetic-alice\\Documents\\vault";
const HOME_RELATIVE_PATH = "~/Documents/synthetic-alice/vault";
const PDF_NAME = "Chao 2000 — synthetic.pdf";
const PAPER_TITLE = "Attention Is All You Need (synthetic)";
const SECRETS = [
  TOKEN,
  "synthetic-alice",
  PDF_NAME,
  PAPER_TITLE,
  HOME_RELATIVE_PATH,
];

function hostileReasonText(): string {
  return (
    `OCR failed on ${PDF_NAME}: ${PAPER_TITLE} at ${USER_PATH} ` +
    `with key ${TOKEN} token=[github_token_redacted]`
  );
}

function hostilePrimary(actionId: string): ActionPrimary {
  return {
    action_id: actionId,
    verb: "investigate",
    label: "Report OCR issue",
    availability: "available",
    safety_class: "safe",
    preservation_facts: [],
    replacement_facts: [],
    interruptible: true,
    confirmation_required: false,
    confirmation_prompt: null,
    scope: "all",
    scope_count: 5,
  };
}

function hostileEnvelope(code: string): ProbeEnvelope {
  return {
    schema_version: 2,
    module: "ocr",
    capability_state: "needs_action",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    severity: "warning",
    reason: { code, text: hostileReasonText() },
    action: { primary: hostilePrimary("ocr.report_issue") },
    notices: [],
    user_state: "action_required",
    capability_kind: "optional",
    maintenance_eligible: true,
    user_visible_failure: true,
    user_impact: null,
    updated_at: "2026-11-17T00:00:00Z",
    ttl_seconds: 60,
  };
}

/** Test seam: the private dispatch surface this suite exercises. */
interface SettingTabSeam {
  display(): void;
  _resolveRuntimeCommand(): { path: string; args: string[] };
  _runAllowedDispatch(
    mod: string,
    primary: ActionPrimary,
    env: ProbeEnvelope
  ): void;
  _capabilityState: Record<string, ProbeEnvelope>;
  _lastKnownState: Map<string, { envelope: ProbeEnvelope; capturedAt: string }>;
  _setupStageLog: string[];
  _lastSetupFailure: { category: string; reason: string; at: string } | null;
}

function makeTab(vaultBasePath: string): SettingTabSeam {
  const app = {
    vault: { adapter: { basePath: vaultBasePath }, getConfig: () => "en" },
    workspace: {
      getLeavesOfType: () => [],
      onLayoutReady: (cb: () => void) => cb?.(),
    },
  };
  const plugin = {
    manifest: { version: "1.0.0" },
    settings: {},
    saveSettings: vi.fn(),
    loadSettings: vi.fn(),
    readPaperforgeJson: () => ({}),
    _ocrProgress: null,
    _ocrBuffer: "",
    _embedProgress: { current: 0, total: 0, key: "" },
    _embedBuffer: "",
  };
  // One unchecked cast at the seam: privates are exercised, never shipped.
  const tab = new PaperForgeSettingTab(
    app as never,
    plugin as never
  ) as unknown as SettingTabSeam;
  tab.display = () => {};
  tab._resolveRuntimeCommand = () => ({ path: "/usr/bin/python3", args: [] });
  tab._capabilityState = {};
  tab._lastKnownState = new Map();
  tab._setupStageLog = [];
  return tab;
}

function asDraft(value: unknown): PublicIssueDraft {
  if (!value || typeof value !== "object")
    throw new Error("route produced no draft");
  if (!("title" in value) || !("body" in value) || !("labels" in value)) {
    throw new Error("route draft lacks title/body/labels");
  }
  const { title, body, labels } = value;
  if (
    typeof title !== "string" ||
    typeof body !== "string" ||
    !Array.isArray(labels)
  ) {
    throw new Error("route draft fields have the wrong shape");
  }
  return {
    title,
    body,
    labels: labels as string[],
  } as unknown as PublicIssueDraft;
}

/** Obsidian element extensions the real modal expects. */
function augmentEl(el: HTMLElement): void {
  const rec = el as unknown as Record<string, unknown>;
  if (rec["createEl"]) return;
  const doc = el.ownerDocument;
  rec["addClass"] = (c: string) => {
    el.classList.add(c);
    return el;
  };
  rec["setAttr"] = (n: string, v: string) => {
    el.setAttribute(n, v);
    return el;
  };
  rec["empty"] = () => {
    el.innerHTML = "";
  };
  rec["setText"] = (t: string) => {
    el.textContent = t;
  };
  rec["createEl"] = (t: string, o?: Record<string, unknown>) => {
    const ch = doc.createElement(t);
    if (o) {
      if (o.cls) ch.className = String(o.cls);
      if (o.text) ch.textContent = String(o.text);
      if (o.attr && typeof o.attr === "object")
        for (const [k, v] of Object.entries(o.attr as Record<string, string>))
          ch.setAttribute(k, v);
    }
    el.appendChild(ch);
    augmentEl(ch);
    return ch;
  };
}

let dom: JSDOM;
let clipboardPayload: string | null;

beforeEach(() => {
  dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", {
    url: "http://localhost",
  });
  (globalThis as unknown as Record<string, unknown>).document =
    dom.window.document;
  (globalThis as unknown as Record<string, unknown>).window = dom.window;
  modalOpens.length = 0;
  clipboardPayload = null;
  runtimePointer.value = null;
  Object.defineProperty(navigator, "clipboard", {
    value: {
      writeText: (t: string) => {
        clipboardPayload = t;
        return Promise.resolve();
      },
    },
    configurable: true,
  });
});

afterEach(() => {
  dom.window.close();
  vi.restoreAllMocks();
});

describe("R1 OCR diagnostic privacy", () => {
  it("collector drops free reason text before the public report", () => {
    const modules = collectDiagnosticModules(
      { ocr: hostileEnvelope("ocr.quality_unacceptable") },
      new Map()
    );
    const dumped = JSON.stringify(modules);
    for (const s of SECRETS) expect(dumped).not.toContain(s);
    expect(dumped).toContain("ocr.quality_unacceptable");
    const first = modules[0];
    if (!first) throw new Error("expected one collected module");
    expect(Object.keys(first)).not.toContain("errorExcerpt");
  });

  it("support diagnostic builder + clipboard carry allowlisted fields only", async () => {
    const modules = collectDiagnosticModules(
      { ocr: hostileEnvelope("ocr.quality_unacceptable") },
      new Map()
    );
    const report = buildSupportDiagnostic({
      pluginVersion: "2.0.0rc6",
      modules,
      environment: {
        managedRuntime: "(outside home)",
        runtimeVersion: "2.0.0rc6",
        pythonSetting: null,
      },
      lastSetupFailure: { category: "network", at: "2026-11-17T00:00:00.000Z" },
    });
    for (const s of SECRETS) expect(report).not.toContain(s);
    expect(report).toContain("ocr.quality_unacceptable");

    copySupportDiagnostic(report);
    await vi.waitFor(() => expect(clipboardPayload).not.toBeNull());
    for (const s of SECRETS)
      expect(clipboardPayload as string).not.toContain(s);
  });

  it("builder withholds hostile values injected into every allowed field", () => {
    // Cast once at the untyped trust boundary: runtime callers can hand the
    // builder any string, so every selected VALUE must prove itself.
    const hostile = {
      pluginVersion: TOKEN,
      backendVersion: USER_PATH,
      modules: [
        {
          module: `${TOKEN}.exfil`,
          userState: PAPER_TITLE,
          reasonCode: TOKEN,
          actionId: PDF_NAME,
          lastSuccessAt: PAPER_TITLE,
        },
        {
          module: "ocr",
          userState: "action_required",
          reasonCode: `${USER_PATH}.x`,
          actionId: `${TOKEN}.y`,
          lastSuccessAt: PDF_NAME,
        },
      ],
      environment: {
        managedRuntime: HOME_RELATIVE_PATH,
        runtimeVersion: TOKEN,
        pythonSetting: USER_PATH,
      },
      lastSetupFailure: { category: TOKEN, at: PAPER_TITLE },
    } as unknown as DiagnosticInput;
    const text = buildSupportDiagnostic(hostile);
    for (const s of SECRETS) expect(text).not.toContain(s);
    // Structure survives: the known module is still reported, code withheld.
    expect(text).toContain("ocr: action_required");
    expect(text).toContain("category: (withheld)");
  });

  it("issue draft builder returns allowlisted fields with no raw text or vault path", () => {
    const draft = buildRedactedDraft("ocr.quality_unacceptable", 5);
    const dumped = JSON.stringify(draft);
    for (const s of SECRETS) expect(dumped).not.toContain(s);
    expect(dumped).not.toContain("Detail:");
    expect(dumped).not.toContain("vaultPath");
    expect(dumped).not.toContain("reasonText");
    expect(draft.title).toContain("ocr.quality_unacceptable");
    expect(draft.body).toContain("5");
    expect(draft.labels).toEqual(["ocr", "quality", "auto-generated"]);
    // Unknown dotted values could be filenames/titles; only probe reasons pass.
    expect(
      buildRedactedDraft("ocr.attention.is.all.you.need.pdf", 5).title
    ).toContain("ocr.report_requested");
    expect(buildRedactedDraft("../../etc/passwd", -1).title).toContain(
      "ocr.report_requested"
    );
  });

  it("ocr.diagnose route copies a clean diagnostic", async () => {
    runtimePointer.value = {
      environmentRoot: "/home/user/Documents/synthetic-alice/vault",
      paperforgeVersion: "2.0.0rc6",
    };
    const tab = makeTab(USER_PATH);
    tab._capabilityState = {
      ocr: hostileEnvelope("ocr.diagnostics_requested"),
    };
    tab._lastSetupFailure = {
      category: "network",
      reason: `pip failed with ${TOKEN} at ${USER_PATH}`,
      at: "2026-11-17T00:00:00.000Z",
    };
    tab._setupStageLog = [`2026-11-17T00:00:00.000Z reading ${PDF_NAME}`];

    tab._runAllowedDispatch(
      "ocr",
      hostilePrimary("ocr.diagnose"),
      hostileEnvelope("ocr.diagnostics_requested")
    );
    await vi.waitFor(() => expect(clipboardPayload).not.toBeNull());
    const payload = clipboardPayload as string;
    for (const s of SECRETS) expect(payload).not.toContain(s);
    expect(payload).toContain("ocr.diagnostics_requested");
    expect(payload).toContain("managed-runtime: (inside home)");
  });

  it("ocr.report_issue route drafts and links without secrets", () => {
    const tab = makeTab(USER_PATH);
    tab._capabilityState = { ocr: hostileEnvelope("ocr.quality_unacceptable") };
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);

    tab._runAllowedDispatch(
      "ocr",
      hostilePrimary("ocr.report_issue"),
      hostileEnvelope("ocr.quality_unacceptable")
    );
    expect(modalOpens.length).toBe(1);
    const opened = modalOpens[0];
    if (!opened) throw new Error("report_issue opened no modal");
    for (const s of SECRETS)
      expect(JSON.stringify(opened.draft)).not.toContain(s);

    // Open the captured draft through the real modal and click through.
    const draft = asDraft(opened.draft);
    const modal = new PaperForgeIssueDraftModal(
      {} as never,
      draft,
      "https://github.com/o/r/issues/new"
    );
    augmentEl(modal.contentEl);
    modal.onOpen();
    const btn = Array.from(modal.contentEl.querySelectorAll("button")).find(
      (b) => b.textContent?.trim() === "Open GitHub Issue"
    );
    btn?.click();
    expect(openSpy).toHaveBeenCalledTimes(1);
    const firstCall = openSpy.mock.calls[0];
    expect(firstCall?.[1]).toBe("_blank");
    const decoded = decodeURIComponent(String(firstCall?.[0]));
    for (const s of SECRETS) expect(decoded).not.toContain(s);
    expect(decoded).toContain("ocr.quality_unacceptable");
  });
});
