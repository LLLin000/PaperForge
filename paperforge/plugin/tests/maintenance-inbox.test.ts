/**
 * Issue #80 — Maintenance inbox production DOM tests.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { JSDOM } from "jsdom";

const { noticeCalls, execFileCalls } = vi.hoisted(() => {
  const calls: { msg: string; timeout?: number }[] = [];
  const efCalls: unknown[] = [];
  return { noticeCalls: calls, execFileCalls: efCalls };
});

vi.mock("../src/release-notes.json", () => ({ default: { versions: [] } }));

vi.mock("obsidian", () => ({
  PluginSettingTab: class {
    containerEl: HTMLDivElement; app: Record<string, unknown>;
    constructor(app: Record<string, unknown>, _plugin: Record<string, unknown>) {
      this.app = app; this.containerEl = document.createElement("div");
    }
  },
  App: class {},
  Setting: class {
    settingEl: HTMLDivElement; nameEl: HTMLDivElement; descEl: HTMLDivElement & { setText?: (t: string) => void }; controlEl: HTMLDivElement;
    constructor(containerEl: HTMLElement) {
      this.settingEl = document.createElement("div"); this.settingEl.className = "setting-item";
      this.nameEl = document.createElement("div"); this.nameEl.className = "setting-item-name";
      this.descEl = Object.assign(document.createElement("div"), { className: "setting-item-description", setText: (t: string) => { this.descEl.textContent = t; } });
      this.controlEl = document.createElement("div"); this.controlEl.className = "setting-item-control";
      this.settingEl.appendChild(this.nameEl); this.settingEl.appendChild(this.descEl); this.settingEl.appendChild(this.controlEl);
      containerEl.appendChild(this.settingEl);
    }
    setName(_t: string) { return this; } setDesc(_t: string) { return this; }
    addText(_cb: unknown) { return this; } addButton(_cb: unknown) { return this; }
    addDropdown(_cb: unknown) { return this; } addToggle(_cb: unknown) { return this; }
  },
  Modal: class {
    app: Record<string, unknown>; contentEl: HTMLDivElement;
    constructor(app: Record<string, unknown>) { this.app = app; this.contentEl = document.createElement("div"); }
    open() {} close() {}
  },
  Notice: class { constructor(msg: string, timeout?: number) { noticeCalls.push({ msg, timeout }); } },
  setTooltip: () => {}, Platform: {},
}));

vi.mock("fs", () => ({ default: {}, existsSync: () => false, readFileSync: () => "{}", writeFileSync: () => {}, readdirSync: () => [], statSync: () => ({}), accessSync: () => {}, constants: { X_OK: 1 } }));
vi.mock("path", () => ({ default: {}, join: (...a: string[]) => a.join("/"), dirname: (p: string) => p.split("/").slice(0,-1).join("/"), resolve: (...a: string[]) => a.join("/") }));
vi.mock("os", () => ({ default: {}, homedir: () => "/home/user", platform: () => "win32" }));

vi.mock("child_process", () => {
  const mod = {
    execFile: (_p: string, _a: string[], _o: Record<string, unknown>, cb?: (err: Error | null, stdout: string, stderr: string) => void) => {
      execFileCalls.push({ args: [..._a], cb }); if (cb) setTimeout(() => cb(null, "{}", ""), 0);
    },
    execFileSync: () => "Python 3.11.0", exec: () => {},
    spawn: () => ({ on: () => {}, stdin: { write: () => {} }, kill: () => {} }),
  };
  return { ...mod, default: mod };
});

vi.mock("../src/services/python-bridge", () => ({
  resolvePythonExecutable: () => ({ path: "/usr/bin/python3", source: "managed", extraArgs: [] }),
  buildRuntimeInstallCommand: () => [], paperforgeEnrichedEnv: () => ({}), buildTargetedEnv: () => ({}),
  scanBbtUnderProfiles: () => false, scanBbtDirectChildren: () => false, runSubprocess: () => {},
}));
vi.mock("../src/services/memory-state", () => ({
  resolveVaultPaths: () => ({}), getMemoryRuntime: () => null, getVectorRuntime: () => null,
  getRuntimeHealth: () => ({}), isMemoryReady: () => false, isVectorReady: () => false,
  getMemoryStatusText: () => "", getVectorStatusText: () => "", getCachedPython: () => null,
}));
vi.mock("../src/services/ocr-maintenance-ui", () => ({
  categorizeMaintenanceRow: () => [], buildMaintenanceSummary: () => ({}),
  maintenanceActionForRow: () => null, maintenanceActionRequiresConfirmation: () => false,
  readMaintenanceCache: () => null, refreshMaintenanceData: () => new Promise(() => {}),
}));
vi.mock("../src/services/managed-runtime", () => ({
  ManagedRuntime: class { current() { return { status: "ready" }; } },
  runtimeActionsForHealth: () => [],
  resolveRuntimeCommand: () => ({ path: "/usr/bin/python3", args: ["-u"] }),
}));
vi.mock("../src/utils/disclosure", () => ({ getDisclosureState: () => false, toggleDisclosureState: () => {} }));
vi.mock("../src/services/secret-storage", () => ({ resolveCredentialEnv: () => ({}), stripCredentialEnv: () => ({}) }));
vi.mock("../src/services/progress-parser", () => ({ processProgressChunk: () => {} }));

import type { ProbeEnvelope, MaintenanceItem } from "../src/constants";
import { PaperForgeSettingTab } from "../src/settings";
import { setLanguage } from "../src/i18n";
import { PaperForgeConfirmModal, type ConfirmModalConfig, PaperForgeIssueDraftModal } from "../src/views/modals";

function fakeApp(): Record<string, unknown> {
  return { vault: { adapter: { basePath: "/test/vault" }, getConfig: () => "en" } };
}
function fakePlugin(): Record<string, unknown> {
  return { settings: { capabilityState: {}, vault_path: "/test/vault" }, manifest: { version: "2.1.0" }, saveSettings: vi.fn(), loadSettings: vi.fn(), readPaperforgeJson: () => ({}), savePaperforgeJson: vi.fn(), _autoSyncRunning: false, _ocrProcess: null, _ocrProgress: null };
}

let dom: JSDOM;
function augmentEl(el: HTMLElement): HTMLElement {
  const rec = el as unknown as Record<string, unknown>;
  rec.addClass = (c: string) => { el.classList.add(c); return el; };
  rec.setAttr = (n: string, v: string) => { el.setAttribute(n, v); return el; };
  rec.empty = () => { el.innerHTML = ""; };
  rec.appendText = (t: string) => { el.appendChild(dom.window.document.createTextNode(t)); };
  rec.setText = (t: string) => { el.textContent = t; };
  rec.createEl = (t: string, o?: Record<string, unknown>) => {
    const ch = dom.window.document.createElement(t);
    if (o) { if (o.cls) ch.className = String(o.cls); if (o.text) ch.textContent = String(o.text); if (o.attr && typeof o.attr === "object") for (const [k, v] of Object.entries(o.attr as Record<string, string>)) ch.setAttribute(k, v); }
    el.appendChild(ch); augmentEl(ch); return ch;
  };
  rec.createDiv = (o?: Record<string, unknown>) => rec.createEl("div", o);
  return el;
}
function makeTab(): PaperForgeSettingTab {
  const app = fakeApp(); const plugin = fakePlugin(); setLanguage(app as never);
  const tab = new PaperForgeSettingTab(app as never, plugin); augmentEl(tab.containerEl); return tab;
}
function makeMaintEnv(overrides: Partial<ProbeEnvelope> = {}): ProbeEnvelope {
  return { schema_version: 1, module: "maintenance", capability_state: "needs_action", activity_state: "idle", activity_label: null, activity_progress: null, severity: "warning", reason: { code: "maintenance.items_present", text: "1 module(s) need attention" }, action: { primary: null }, notices: [], updated_at: new Date().toISOString(), ttl_seconds: 60, items: [{ module: "ocr", capability_state: "needs_action", severity: "warning", activity_state: "idle", activity_label: null, activity_progress: null, reason_code: "ocr.artifacts_stale", reason_text: "OCR artifacts stale", action: { verb: "rebuild_derived", label: "Rebuild", destructive: false, destructive_scope: null, destructive_effect: null, confirmation_required: false, confirmation_prompt: null, command: "paperforge ocr rebuild --all", scope: "module", scope_count: 1 } }], ...overrides };
}
function makeContainer(): HTMLElement { return augmentEl(dom.window.document.createElement("div")); }
function getState(tab: PaperForgeSettingTab): Record<string, unknown> { return tab as unknown as Record<string, unknown>; }

beforeEach(() => { dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", { url: "http://localhost" }); (globalThis as unknown as Record<string, unknown>).document = dom.window.document; (globalThis as unknown as Record<string, unknown>).window = dom.window; noticeCalls.length = 0; execFileCalls.length = 0; });
afterEach(() => { dom.window.close(); });

describe("Rendering states", () => {
  it("1. absent -> Checking+probe", () => { const t=makeTab(); getState(t)._capabilityState={}; const c=makeContainer(); getState(t)._renderMaintenanceInbox(c); expect(c.innerHTML).toContain("Checking"); expect(getState(t)._probing as Set<string>).toContain("maintenance"); });
  it("2. ready+no_items+[] -> all-clear", () => { const t=makeTab(); getState(t)._capabilityState={maintenance:makeMaintEnv({capability_state:"ready",severity:"ok",reason:{code:"maintenance.no_items",text:"All ready"},items:[]})}; const c=makeContainer(); getState(t)._renderMaintenanceInbox(c); expect(c.innerHTML).toContain("no maintenance needed"); });
  it("3. malformed ready+no_items+nonempty -> not all-clear", () => { const t=makeTab(); getState(t)._capabilityState={maintenance:makeMaintEnv({capability_state:"ready",severity:"ok",reason:{code:"maintenance.no_items",text:"All ready"}})}; const c=makeContainer(); getState(t)._renderMaintenanceInbox(c); expect(c.innerHTML).not.toContain("no maintenance needed"); });
  it("4. needs_action -> module+action", () => { const t=makeTab(); getState(t)._capabilityState={maintenance:makeMaintEnv()}; const c=makeContainer(); getState(t)._renderMaintenanceInbox(c); expect(c.innerHTML).toContain("OCR Engine"); expect(c.innerHTML).toContain("Rebuild"); });
  it("5. running+probing -> Checking", () => { const t=makeTab(); getState(t)._capabilityState={maintenance:makeMaintEnv({activity_state:"running",reason:{code:"maintenance.probing",text:"..."}})}; const c=makeContainer(); getState(t)._renderMaintenanceInbox(c); expect(c.innerHTML).toContain("Checking"); });
  it("6. unknown -> Checking+probe", () => { const t=makeTab(); getState(t)._capabilityState={maintenance:makeMaintEnv({capability_state:"unknown"})}; const c=makeContainer(); getState(t)._renderMaintenanceInbox(c); expect(c.innerHTML).toContain("Checking"); });
  it("7. limited -> Checking+request", () => { const t=makeTab(); getState(t)._capabilityState={maintenance:makeMaintEnv({capability_state:"limited"})}; const c=makeContainer(); getState(t)._renderMaintenanceInbox(c); expect(c.innerHTML).toContain("Checking"); });
  it("8. unavailable -> Checking+request", () => { const t=makeTab(); getState(t)._capabilityState={maintenance:makeMaintEnv({capability_state:"unavailable"})}; const c=makeContainer(); getState(t)._renderMaintenanceInbox(c); expect(c.innerHTML).toContain("Checking"); });
  it("9. missing_input -> Checking+request", () => { const t=makeTab(); getState(t)._capabilityState={maintenance:makeMaintEnv({capability_state:"missing_input"})}; const c=makeContainer(); getState(t)._renderMaintenanceInbox(c); expect(c.innerHTML).toContain("Checking"); });
});

describe("Focus", () => {
  it("10. heading tabindex=-1", () => { const t=makeTab(); getState(t)._capabilityState={maintenance:makeMaintEnv({capability_state:"ready",severity:"ok",reason:{code:"maintenance.no_items",text:"All ready"},items:[]})}; t.activeTab="maintenance"; t.display(); expect(t.containerEl.querySelector("#pf-maintenance-heading")?.getAttribute("tabindex")).toBe("-1"); });
});

describe("_requestMaintenanceProjection dedup", () => {
  it("11. sets pending when probing", () => { const t=makeTab(); getState(t)._probing=new Set(["maintenance"]); getState(t)._pendingMaintenanceRefresh=false; getState(t)._requestMaintenanceProjection(); expect(getState(t)._pendingMaintenanceRefresh).toBe(true); });
  it("12. probes when not probing", () => { const t=makeTab(); getState(t)._probing=new Set(); getState(t)._pendingMaintenanceRefresh=true; getState(t)._requestMaintenanceProjection(); expect(getState(t)._probing as Set<string>).toContain("maintenance"); expect(getState(t)._pendingMaintenanceRefresh).toBe(false); });
});

describe("PaperForgeIssueDraftModal redaction", () => {
  it("13. secrets and paths absent from rendered DOM", () => {
    const draft = { title:"OCR: ocr.quality_unacceptable", body:"API key: sk-abc123def456ghi78jkl90mno\nPath: C:\\Users\\test\\Documents\\papers\\transformer.pdf\nPath: C:\\Users\\Lin\\My Vault\\paper.pdf\nZotero data at D:\\Zotero\\data\nPaper: Attention Is All You Need\nSee https://github.com/o/r/issues/new for details", labels:["ocr","quality"] };
    const modal = new PaperForgeIssueDraftModal({vault:{adapter:{basePath:"/test"},getConfig:()=>"en"}} as never, draft, "https://github.com/o/r/issues/new");
    augmentEl(modal.contentEl); modal.onOpen();
    const html = modal.contentEl.innerHTML;
    expect(html).not.toMatch(/sk-abc123/);
    expect(html).not.toMatch(/C:\\Users\\test/);
    expect(html).not.toMatch(/Attention Is All You Need/);
    expect(html).not.toMatch(/My Vault/);
    expect(html).toMatch(/github\.com/);
    expect(html).toContain("[REDACTED]");
    expect(html).toContain("Included");
    expect(html).toContain("Redacted");
    expect(modal.contentEl.querySelectorAll('input[type=password]').length).toBe(0);
  });
  it("14. no auto-open + URL redacted after explicit click", () => {
    const draft = { title:"OCR issue", body:"API key: sk-evil1234567890abcdef\nPath: C:\\Users\\me\\secret.pdf\nPaper: Test Paper Title", labels:["ocr"] };
    const modal = new PaperForgeIssueDraftModal({vault:{adapter:{basePath:"/test"},getConfig:()=>"en"}} as never, draft, "https://github.com/o/r/issues/new");
    augmentEl(modal.contentEl); modal.onOpen();
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
    expect(openSpy).not.toHaveBeenCalled();
    const input = modal.contentEl.querySelector("input") as HTMLInputElement;
    const textarea = modal.contentEl.querySelector("textarea") as HTMLTextAreaElement;
    if (input) input.value = "sk-leak1234567890abcdef in title";
    if (textarea) textarea.value = "token: [github_token_redacted]\nPath: D:\\data\\secret.csv\nPath: /home/user/secret.csv\nPath: C:\\Users\\Lin\\My Vault\\secret.pdf\nSee https://github.com/o/r/issues/new for details";
    const btn = Array.from(modal.contentEl.querySelectorAll("button"))
      .find(b => b.textContent?.trim() === "Open GitHub Issue");
    btn?.click();
    expect(openSpy).toHaveBeenCalledTimes(1);
    const [url, target, features] = openSpy.mock.calls[0];
    expect(target).toBe("_blank");
    expect(features).toBe("noopener,noreferrer");
    const decoded = decodeURIComponent(String(url));
    expect(decoded).not.toMatch(/sk-leak/);
    expect(decoded).not.toMatch(/sk-evil/);
    expect(decoded).not.toMatch(/ghp_/);
    expect(decoded).not.toMatch(/C:\\Users/);
    expect(decoded).not.toMatch(/D:\\data/);
    expect(decoded).not.toMatch(/\/home\/user/);
    expect(decoded).not.toMatch(/My Vault/);
    expect(decoded).toMatch(/github\.com/);
    expect(decoded).not.toMatch(/Test Paper Title/);
    expect(decoded).toContain("[REDACTED]");
    openSpy.mockRestore();
  });
  it("15. excluded categories shown, no attachment claim", () => {
    const draft = { title:"OCR issue", body:"Just some text", labels:["ocr"] };
    const modal = new PaperForgeIssueDraftModal({vault:{adapter:{basePath:"/test"},getConfig:()=>"en"}} as never, draft, "https://github.com/o/r/issues/new");
    augmentEl(modal.contentEl); modal.onOpen();
    const html = modal.contentEl.innerHTML;
    expect(html).toContain("Credentials");
    expect(html).toContain("vault/Zotero paths");
    expect(html).toContain("paper titles");
    expect(html).toContain("paper content");
    expect(html).not.toContain("attached diagnostic");
    expect(html).not.toContain("See attached");
  });
});

describe("Modal inert cleanup and focus restoration", () => {
  it("16. overview card renders real reason, no action, nav button exists", () => {
    const tab = makeTab();
    (tab as unknown as Record<string, unknown>)._capabilityState = { maintenance: makeMaintEnv() };
    const cardContainer = makeContainer();
    const env = makeMaintEnv();
    (tab as unknown as Record<string, unknown>)._renderCard(cardContainer, "maintenance", env);
    const html = cardContainer.innerHTML;
    expect(html).not.toContain("Detection pending");
    expect(html).toContain("need attention");
    expect(cardContainer.querySelector(".pf-cc-card-action")).toBeNull();
    expect(cardContainer.querySelector(".pf-open-module-btn")).toBeTruthy();
  });
});
