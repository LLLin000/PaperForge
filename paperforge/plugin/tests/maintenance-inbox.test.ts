/**
 * Issue #80 — Maintenance inbox production DOM tests (legacy).
 * Updated after #UX: maintenance tab removed. Keeps modal redaction tests.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { JSDOM } from "jsdom";

const { noticeCalls, execFileCalls } = vi.hoisted(() => ({
  noticeCalls: [] as { msg: string; timeout?: number }[],
  execFileCalls: [] as { args: string[]; cb?: Function }[],
}));

vi.mock("../src/release-notes.json", () => ({ default: { versions: [] } }));

vi.mock("obsidian", () => ({
  PluginSettingTab: class {
    containerEl: HTMLElement;
    constructor() {
      this.containerEl = document.createElement("div");
    }
    display() {}
  },
  Setting: class {
    constructor() {}
    setName() {
      return this;
    }
    setDesc() {
      return this;
    }
    addToggle() {
      return this;
    }
    addButton() {
      return this;
    }
    addText() {
      return this;
    }
    addDropdown() {
      return this;
    }
  },
  Notice: class {
    constructor(msg: string, timeout?: number) {
      noticeCalls.push({ msg, timeout });
    }
  },
  setTooltip: () => {},
  Platform: {},
  Modal: class {
    contentEl: HTMLElement;
    constructor() {
      this.contentEl = document.createElement("div");
    }
    onOpen() {}
    onClose() {}
    open() {
      this.onOpen();
    }
    close() {
      this.onClose();
    }
  },
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
  join: (...a: string[]) => a.join("/"),
  dirname: (p: string) => p.split("/").slice(0, -1).join("/"),
  resolve: (...a: string[]) => a.join("/"),
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
      execFileCalls.push({ args: [..._a], cb });
      if (cb) setTimeout(() => cb(null, "{}", ""), 0);
    },
    execFileSync: () => "Python 3.11.0",
    exec: () => {},
    spawn: () => ({ on: () => {}, stdin: { write: () => {} }, kill: () => {} }),
  };
  return { ...mod, default: mod };
});

vi.mock("../src/services/python-bridge", () => ({
  resolvePythonExecutable: () => ({
    path: "/usr/bin/python3",
    source: "managed",
    extraArgs: [],
  }),
  buildRuntimeInstallCommand: () => [],
  paperforgeEnrichedEnv: () => ({}),
  buildTargetedEnv: () => ({}),
  scanBbtUnderProfiles: () => false,
  scanBbtDirectChildren: () => false,
  runSubprocess: () => {},
}));
vi.mock("../src/services/memory-state", () => ({
  resolveVaultPaths: () => ({}),
  getMemoryRuntime: () => null,
  getVectorRuntime: () => null,
  getRuntimeHealth: () => ({}),
  isMemoryReady: () => false,
  isVectorReady: () => false,
  getMemoryStatusText: () => "",
  getVectorStatusText: () => "",
  getCachedPython: () => null,
}));
vi.mock("../src/services/ocr-maintenance-ui", () => ({
  categorizeMaintenanceRow: () => [],
  buildMaintenanceSummary: () => ({}),
  maintenanceActionForRow: () => null,
  maintenanceActionRequiresConfirmation: () => false,
  readMaintenanceCache: () => null,
  refreshMaintenanceData: () => new Promise(() => {}),
}));
vi.mock("../src/services/managed-runtime", () => ({
  ManagedRuntime: class {
    current() {
      return { status: "ready" };
    }
  },
  runtimeActionsForHealth: () => [],
  resolveRuntimeCommand: () => ({ path: "/usr/bin/python3", args: ["-u"] }),
}));
vi.mock("../src/utils/disclosure", () => ({
  getDisclosureState: () => false,
  toggleDisclosureState: () => {},
}));
vi.mock("../src/services/secret-storage", () => ({
  resolveCredentialEnv: () => ({}),
  stripCredentialEnv: () => ({}),
}));
vi.mock("../src/services/progress-parser", () => ({
  processProgressChunk: () => {},
}));

import { PaperForgeIssueDraftModal } from "../src/views/modals";

let dom: JSDOM;
function augmentEl(el: HTMLElement): HTMLElement {
  const rec = el as unknown as Record<string, unknown>;
  rec.addClass = (c: string) => {
    el.classList.add(c);
    return el;
  };
  rec.setAttr = (n: string, v: string) => {
    el.setAttribute(n, v);
    return el;
  };
  rec.empty = () => {
    el.innerHTML = "";
  };
  rec.appendText = (t: string) => {
    el.appendChild(dom.window.document.createTextNode(t));
  };
  rec.setText = (t: string) => {
    el.textContent = t;
  };
  rec.createEl = (t: string, o?: Record<string, unknown>) => {
    const ch = dom.window.document.createElement(t);
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
  rec.createDiv = (o?: Record<string, unknown>) => rec.createEl("div", o);
  return el;
}

beforeEach(() => {
  dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", {
    url: "http://localhost",
  });
  (globalThis as unknown as Record<string, unknown>).document =
    dom.window.document;
  (globalThis as unknown as Record<string, unknown>).window = dom.window;
  noticeCalls.length = 0;
  execFileCalls.length = 0;
});
afterEach(() => {
  dom.window.close();
});

describe("PaperForgeIssueDraftModal redaction", () => {
  it("13. secrets and paths absent from rendered DOM", () => {
    const draft = {
      title: "OCR: ocr.quality_unacceptable",
      body: "API key: sk-abc123def456ghi78jkl90mno\nPath: C:\\Users\\test\\Documents\\papers\\transformer.pdf\nPath: C:\\Users\\Lin\\My Vault\\paper.pdf\nZotero data at D:\\Zotero\\data\nPaper: Attention Is All You Need\nSee https://github.com/o/r/issues/new for details",
      labels: ["ocr", "quality"],
    };
    const modal = new PaperForgeIssueDraftModal(
      {
        vault: { adapter: { basePath: "/test" }, getConfig: () => "en" },
      } as never,
      draft,
      "https://github.com/o/r/issues/new"
    );
    augmentEl(modal.contentEl);
    modal.onOpen();
    const html = modal.contentEl.innerHTML;
    expect(html).not.toMatch(/sk-abc123/);
    expect(html).not.toMatch(/C:\\Users\\test/);
    expect(html).not.toMatch(/Attention Is All You Need/);
    expect(html).not.toMatch(/My Vault/);
    expect(html).toMatch(/github\.com/);
    expect(html).toContain("[REDACTED]");
    expect(html).toContain("Included");
    expect(html).toContain("Redacted");
    expect(
      modal.contentEl.querySelectorAll("input[type=password]").length
    ).toBe(0);
  });
  it("14. no auto-open + URL redacted after explicit click", () => {
    const draft = {
      title: "OCR issue",
      body: "API key: sk-evil1234567890abcdef\nPath: C:\\Users\\me\\secret.pdf\nPaper: Test Paper Title",
      labels: ["ocr"],
    };
    const modal = new PaperForgeIssueDraftModal(
      {
        vault: { adapter: { basePath: "/test" }, getConfig: () => "en" },
      } as never,
      draft,
      "https://github.com/o/r/issues/new"
    );
    augmentEl(modal.contentEl);
    modal.onOpen();
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
    expect(openSpy).not.toHaveBeenCalled();
    const input = modal.contentEl.querySelector("input") as HTMLInputElement;
    const textarea = modal.contentEl.querySelector(
      "textarea"
    ) as HTMLTextAreaElement;
    if (input) input.value = "sk-leak1234567890abcdef in title";
    if (textarea)
      textarea.value =
        "token: [github_token_redacted]\nPath: D:\\data\\secret.csv\nPath: /home/user/secret.csv\nPath: C:\\Users\\Lin\\My Vault\\secret.pdf\nSee https://github.com/o/r/issues/new for details";
    const btn = Array.from(modal.contentEl.querySelectorAll("button")).find(
      (b) => b.textContent?.trim() === "Open GitHub Issue"
    );
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
    const draft = {
      title: "OCR issue",
      body: "Just some text",
      labels: ["ocr"],
    };
    const modal = new PaperForgeIssueDraftModal(
      {
        vault: { adapter: { basePath: "/test" }, getConfig: () => "en" },
      } as never,
      draft,
      "https://github.com/o/r/issues/new"
    );
    augmentEl(modal.contentEl);
    modal.onOpen();
    const html = modal.contentEl.innerHTML;
    expect(html).toContain("Credentials");
    expect(html).toContain("vault/Zotero paths");
    expect(html).toContain("paper titles");
    expect(html).toContain("paper content");
    expect(html).not.toContain("attached diagnostic");
    expect(html).not.toContain("See attached");
  });
});
