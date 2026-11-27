/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";

const { noticeCalls } = vi.hoisted(() => ({
  noticeCalls: [] as string[],
}));

vi.mock("../src/release-notes.json", () => ({ default: { versions: [] } }));

vi.mock("obsidian", () => {
  class Component {
    load() {}
    unload() {}
  }
  class ItemView extends Component {
    app: unknown;
    leaf: unknown;
    containerEl = document.createElement("div");
    contentEl = document.createElement("div");
    constructor(leaf?: unknown) {
      super();
      this.leaf = leaf;
      this.containerEl.appendChild(document.createElement("div"));
      this.containerEl.appendChild(document.createElement("div"));
    }
    registerEvent() {}
  }
  class PluginSettingTab extends Component {
    app: unknown;
    plugin: unknown;
    containerEl: HTMLDivElement;
    constructor(app: unknown, plugin: unknown) {
      super();
      this.app = app;
      this.plugin = plugin;
      this.containerEl = document.createElement("div");
    }
    hide() {}
  }
  class Modal {
    app: unknown;
    contentEl = document.createElement("div");
    constructor(app: unknown) {
      this.app = app;
    }
    setTitle() {
      return this;
    }
    open() {}
    close() {}
  }
  class SuggestModal<T> extends Modal {
    inputEl = document.createElement("input");
    limit = 40;
    setPlaceholder() {}
    setInstructions() {}
    getSuggestions(): T[] {
      return [];
    }
    renderSuggestion() {}
    onChooseSuggestion() {}
  }
  class Setting {
    settingEl = document.createElement("div");
    nameEl = document.createElement("div");
    descEl = document.createElement("div");
    controlEl = document.createElement("div");
    constructor(containerEl: HTMLElement) {
      containerEl.appendChild(this.settingEl);
    }
    setName() {
      return this;
    }
    setDesc() {
      return this;
    }
    addButton() {
      return this;
    }
    addToggle() {
      return this;
    }
    addText() {
      return this;
    }
    addDropdown() {
      return this;
    }
  }
  return {
    PluginSettingTab,
    Plugin: class extends Component {
      app: unknown;
      manifest: unknown;
      constructor(app: unknown, manifest: unknown) {
        super();
        this.app = app;
        this.manifest = manifest;
      }
    },
    ItemView,
    SuggestModal,
    Scope: class {},
    Menu: class {},
    App: class {},
    Modal,
    Setting,
    TFile: class {},
    Notice: vi.fn((msg: string) => {
      noticeCalls.push(msg);
    }),
    setTooltip: vi.fn(),
    setIcon: vi.fn(),
    MarkdownRenderer: { render: vi.fn() },
    Component,
    requestUrl: vi.fn(),
    Platform: { isDesktopApp: true, isMobile: false },
  };
});

import {
  PaperForgeClient,
  type AgentPresenceSnapshotDto,
  type Transport,
} from "../src/client";
import { DEFAULT_SETTINGS, createUnknownEnvelope } from "../src/constants";
import { setLanguage } from "../src/i18n";
import PaperForgePlugin from "../src/main";
import { PaperForgeSettingTab } from "../src/settings";

function ensureObsidianDomHelpers(): void {
  const proto = HTMLElement.prototype as unknown as Record<string, unknown>;
  if (typeof proto.createEl !== "function") {
    proto.createEl = function (
      tag: string,
      opts?: {
        cls?: string;
        text?: string;
        type?: string;
        placeholder?: string;
        attr?: Record<string, string>;
      }
    ) {
      const el = document.createElement(tag);
      if (opts?.cls) el.className = opts.cls;
      if (opts?.text !== undefined) el.textContent = opts.text;
      if (opts?.type && "type" in el) {
        (el as HTMLInputElement).type = opts.type;
      }
      if (opts?.placeholder && "placeholder" in el) {
        (el as HTMLInputElement).placeholder = opts.placeholder;
      }
      if (opts?.attr) {
        for (const [k, v] of Object.entries(opts.attr)) {
          el.setAttribute(k, v);
        }
      }
      this.appendChild(el);
      return el;
    };
  }
  if (typeof proto.createDiv !== "function") {
    proto.createDiv = function (opts?: {
      cls?: string;
      text?: string;
      attr?: Record<string, string>;
    }) {
      return (this as unknown as { createEl: Function }).createEl("div", opts);
    };
  }
  if (typeof proto.empty !== "function") {
    proto.empty = function () {
      this.textContent = "";
    };
  }
  if (typeof proto.setText !== "function") {
    proto.setText = function (txt: string) {
      this.textContent = txt;
    };
  }
  if (typeof proto.setAttr !== "function") {
    proto.setAttr = function (name: string, val: string) {
      this.setAttribute(name, val);
    };
  }
  if (typeof proto.addClass !== "function") {
    proto.addClass = function (...classes: string[]) {
      for (const c of classes) {
        for (const part of String(c).split(/\s+/)) {
          if (part) this.classList.add(part);
        }
      }
    };
  }
  if (typeof proto.appendText !== "function") {
    proto.appendText = function (txt: string) {
      this.appendChild(document.createTextNode(txt));
    };
  }
}

function createMockWorkspace() {
  const listeners = new Map<string, Set<(payload?: unknown) => void>>();
  return {
    on(event: string, cb: (payload?: unknown) => void) {
      let set = listeners.get(event);
      if (!set) {
        set = new Set();
        listeners.set(event, set);
      }
      set.add(cb);
      return { event, cb };
    },
    offref(ref: { event: string; cb: (payload?: unknown) => void }) {
      listeners.get(ref.event)?.delete(ref.cb);
    },
    off(event: string, ref: { cb?: (payload?: unknown) => void } | ((p?: unknown) => void)) {
      const cb = typeof ref === "function" ? ref : ref?.cb;
      if (cb) listeners.get(event)?.delete(cb);
    },
    trigger(event: string, payload?: unknown) {
      for (const cb of listeners.get(event) ?? []) {
        cb(payload);
      }
    },
    listenerCount(event: string) {
      return listeners.get(event)?.size ?? 0;
    },
  };
}

function createHarness(opts?: {
  lang?: "zh" | "en";
  presence?: AgentPresenceSnapshotDto;
  vaultPath?: string;
}) {
  const lang = opts?.lang ?? "zh";
  const workspace = createMockWorkspace();
  const app = {
    vault: {
      adapter: { basePath: opts?.vaultPath ?? "/tmp/nonexistent-pf-vault" },
      getConfig: (k: string) => (k === "language" ? lang : undefined),
    },
    workspace,
  };
  setLanguage(app as never, lang);

  let currentPresence: AgentPresenceSnapshotDto = opts?.presence ?? {
    state: "unconnected",
    active_sessions: [],
    total_active: 0,
    configured_platforms: [],
    setup_checklist: {
      connected: false,
      instructions_injected: false,
      vault_reconciled: false,
      tools_ready: false,
    },
  };

  const client = {
    invalidateCache: vi.fn(),
    probeAll: vi.fn().mockResolvedValue({
      modules: {
        installation: {
          ...createUnknownEnvelope("installation"),
          user_state: "ready",
          capability_state: "ready",
          severity: "ok",
        },
        library: {
          ...createUnknownEnvelope("library"),
          user_state: "ready",
          capability_state: "ready",
          severity: "ok",
        },
      },
    }),
    probe: vi.fn().mockResolvedValue(createUnknownEnvelope("installation")),
    getAgentSessions: vi.fn(async () => currentPresence),
    isOperationActive: () => false,
  };

  const plugin = {
    settings: {
      ...DEFAULT_SETTINGS,
      language: lang,
      agent_platform: "opencode",
      _setup_complete: true,
    },
    manifest: { version: "2.0.11" },
    agentPlatformChoices: ["opencode", "claude", "cursor", "codex"],
    saveSettings: vi.fn().mockResolvedValue(undefined),
    loadSettings: vi.fn().mockResolvedValue(undefined),
    getClient: () => client,
    getAgentPresence: () => currentPresence,
    refreshAgentPresence: vi.fn(async () => currentPresence),
  };

  const tab = new PaperForgeSettingTab(app as never, plugin as never);
  return {
    app,
    workspace,
    plugin,
    client,
    tab,
    setPresence: (next: AgentPresenceSnapshotDto) => {
      currentPresence = next;
    },
  };
}

describe("Real-Time Poki Agent Presence & 4-State Onboarding UI", () => {
  let tmpHome = "";
  const prevPfHome = process.env.PAPERFORGE_HOME;

  beforeEach(() => {
    ensureObsidianDomHelpers();
    noticeCalls.length = 0;
    tmpHome = fs.mkdtempSync(path.join(os.tmpdir(), "pf-agent-ui-"));
    process.env.PAPERFORGE_HOME = tmpHome;
  });

  afterEach(() => {
    if (prevPfHome === undefined) {
      delete process.env.PAPERFORGE_HOME;
    } else {
      process.env.PAPERFORGE_HOME = prevPfHome;
    }
    try {
      fs.rmSync(tmpHome, { recursive: true, force: true });
    } catch {
      // ignore temp cleanup errors
    }
  });

  it("getAgentSessions() calls daemon agent-sessions --vault <vault> --json and falls back to ~/.paperforge/state/agent-sessions.json", async () => {
    const rpcClient = new PaperForgeClient({
      transport: {
        execute: vi.fn().mockResolvedValue(
          JSON.stringify({
            ok: true,
            data: {
              state: "ready",
              active_sessions: [
                {
                  session_id: "sess-1",
                  client_name: "claude-code",
                  client_version: "2.1.0",
                  status: "ready",
                  current_tool: "paperforge_annotate_batch",
                  setup_steps: {
                    connected: true,
                    instructions_injected: true,
                    vault_reconciled: true,
                    skill_ready: true,
                  },
                },
              ],
              total_active: 1,
            },
          })
        ),
        stream: vi.fn(),
        rpc: vi.fn(),
      } as unknown as Transport,
    });

    const snap = await rpcClient.getAgentSessions("/vault/a");
    expect(snap.state).toBe("ready");
    expect(snap.total_active).toBe(1);
    expect(snap.active_sessions[0].client_name).toBe("claude-code");
    expect(snap.setup_checklist?.tools_ready).toBe(true);

    // Fallback when daemon RPC isn't active: read PAPERFORGE_HOME/state/agent-sessions.json
    const stateDir = path.join(tmpHome, "state");
    fs.mkdirSync(stateDir, { recursive: true });
    const nowIso = new Date().toISOString();
    const staleIso = new Date(Date.now() - 10 * 60 * 1000).toISOString();
    const targetVault = path.join(tmpHome, "vault-main");
    fs.writeFileSync(
      path.join(stateDir, "agent-sessions.json"),
      JSON.stringify({
        sessions: [
          {
            session_id: "live-1",
            client_name: "claude-code",
            client_version: "2.1.0",
            vault: targetVault,
            last_seen_at: nowIso,
            status: "connected",
            setup_steps: {
              connected: true,
              instructions_injected: true,
              vault_reconciled: false,
              skill_ready: false,
            },
          },
          {
            session_id: "stale-1",
            client_name: "cursor",
            vault: targetVault,
            last_seen_at: staleIso,
          },
          {
            session_id: "other-vault",
            client_name: "codex",
            vault: path.join(tmpHome, "vault-other"),
            last_seen_at: nowIso,
          },
        ],
      }),
      "utf-8"
    );

    const fallbackClient = new PaperForgeClient({
      transport: {
        execute: vi.fn().mockRejectedValue(new Error("daemon unavailable")),
        stream: vi.fn(),
      } as unknown as Transport,
    });
    const fallbackSnap = await fallbackClient.getAgentSessions(targetVault);
    expect(fallbackSnap.state).toBe("connected");
    expect(fallbackSnap.total_active).toBe(1);
    expect(fallbackSnap.active_sessions[0].session_id).toBe("live-1");
    expect(fallbackSnap.setup_checklist).toEqual({
      connected: true,
      instructions_injected: true,
      vault_reconciled: false,
      tools_ready: false,
    });
  });

  it("(a) unconnected state NEVER shows green 'OpenCode' or '已配置' and renders inline onboarding prompt preview + copy button", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(globalThis.navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });

    const { tab } = createHarness({ lang: "zh" });

    // 1. Overview row
    tab.activeTab = "overview";
    tab.display();
    const agentRow = tab.containerEl.querySelector<HTMLElement>(
      '.pf-cc-module-card[data-module="agent"]'
    );
    expect(agentRow).not.toBeNull();
    const rowBadge = agentRow!.querySelector<HTMLElement>(
      '[data-pf-testid="agent-status-badge"]'
    );
    expect(rowBadge?.getAttribute("data-agent-state")).toBe("unconnected");
    expect(rowBadge?.textContent).toContain("未接入 AI 助手");
    expect(rowBadge?.textContent).not.toContain("OpenCode");
    expect(rowBadge?.textContent).not.toContain("已配置");
    expect(rowBadge?.className).not.toContain("pf-badge--ready");

    // 2. Setup Stage 3 optional row
    const stage3El = document.createElement("div");
    tab._renderSetupStageOptionals(stage3El);
    const stage3Chip = stage3El.querySelector<HTMLElement>(
      '[data-pf-testid="setup-optional-agent-state"]'
    );
    expect(stage3Chip).not.toBeNull();
    expect(stage3Chip?.getAttribute("data-agent-state")).toBe("unconnected");
    expect(stage3Chip?.textContent).toContain("未接入 AI 助手");
    expect(stage3Chip?.textContent).not.toContain("OpenCode");
    expect(stage3Chip?.textContent).not.toContain("已配置");
    expect(stage3Chip?.className).not.toContain("pf-setup-optional-state--ok");

    // 3. Agent Detail view
    const detailEl = document.createElement("div");
    tab._renderAgentDetail(detailEl);
    const detailBadge = detailEl.querySelector<HTMLElement>(
      '[data-pf-testid="agent-status-badge"]'
    );
    expect(detailBadge?.getAttribute("data-agent-state")).toBe("unconnected");
    expect(detailEl.textContent).toContain("未接入 AI 助手");
    expect(detailEl.textContent).toContain(
      "把下面这段话发给 Claude Code / Cursor / OpenCode / Codex，发完我会自动检测接入"
    );

    const preview = detailEl.querySelector<HTMLTextAreaElement>(
      '[data-pf-testid="agent-onboarding-prompt-preview"]'
    );
    expect(preview).not.toBeNull();
    expect(preview!.value.length).toBeGreaterThan(40);

    const copyBtn = detailEl.querySelector<HTMLButtonElement>(
      '[data-pf-testid="agent-copy-onboarding-btn"]'
    );
    expect(copyBtn).not.toBeNull();
    expect(copyBtn!.textContent).toContain("一键复制接入指令");

    copyBtn!.click();
    await new Promise((r) => setTimeout(r, 20));
    expect(writeText).toHaveBeenCalledWith(preview!.value);
  });

  it("(b) configured_idle shows waiting state with detected client", () => {
    const { tab } = createHarness({
      lang: "zh",
      presence: {
        state: "configured_idle",
        active_sessions: [],
        total_active: 0,
        configured_platforms: ["claude"],
        setup_checklist: {
          connected: false,
          instructions_injected: false,
          vault_reconciled: false,
          tools_ready: false,
        },
      },
    });

    const detailEl = document.createElement("div");
    tab._renderAgentDetail(detailEl);
    const badge = detailEl.querySelector<HTMLElement>(
      '[data-pf-testid="agent-status-badge"]'
    );
    expect(badge?.getAttribute("data-agent-state")).toBe("configured_idle");
    expect(badge?.textContent).toContain("已配置 · 等待首次握手");
    expect(detailEl.textContent).toContain("Claude Code");
    expect(detailEl.textContent).toContain("打开或重启你的 AI 助手会话");
    expect(
      detailEl
        .querySelector('[data-pf-testid="agent-check-1"]')
        ?.getAttribute("data-checked")
    ).toBe("false");
  });

  it("(c) connected / ready shows dynamic client name ('Claude Code'), live current_tool, and 4-item auto-setup checklist", () => {
    const { tab, setPresence } = createHarness({
      lang: "zh",
      presence: {
        state: "connected",
        active_sessions: [
          {
            session_id: "s-live",
            client_name: "claude-code",
            client_version: "2.1.0",
            current_tool: "paperforge_annotate_batch",
            status: "connected",
            setup_steps: {
              connected: true,
              instructions_injected: true,
              vault_reconciled: false,
              skill_ready: false,
            },
          },
        ],
        total_active: 1,
        setup_checklist: {
          connected: true,
          instructions_injected: true,
          vault_reconciled: false,
          tools_ready: false,
        },
      },
    });

    const connectedEl = document.createElement("div");
    tab._renderAgentDetail(connectedEl);
    const badge = connectedEl.querySelector<HTMLElement>(
      '[data-pf-testid="agent-status-badge"]'
    );
    expect(badge?.getAttribute("data-agent-state")).toBe("connected");
    expect(badge?.textContent).toContain("Claude Code");
    expect(badge?.textContent).toContain("已连接");
    expect(badge?.textContent).not.toContain("OpenCode");
    expect(
      connectedEl.querySelector('[data-pf-testid="agent-live-tool"]')
        ?.textContent
    ).toContain("正在执行 paperforge_annotate_batch");

    expect(
      connectedEl
        .querySelector('[data-pf-testid="agent-check-1"]')
        ?.getAttribute("data-checked")
    ).toBe("true");
    expect(
      connectedEl.querySelector('[data-pf-testid="agent-check-1"]')?.textContent
    ).toContain("Claude Code v2.1.0");
    expect(
      connectedEl
        .querySelector('[data-pf-testid="agent-check-2"]')
        ?.getAttribute("data-checked")
    ).toBe("true");
    expect(
      connectedEl
        .querySelector('[data-pf-testid="agent-check-3"]')
        ?.getAttribute("data-checked")
    ).toBe("false");
    expect(
      connectedEl
        .querySelector('[data-pf-testid="agent-check-4"]')
        ?.getAttribute("data-checked")
    ).toBe("false");

    // Transition to ready
    setPresence({
      state: "ready",
      active_sessions: [
        {
          session_id: "s-live",
          client_name: "claude-code",
          client_version: "2.1.0",
          current_tool: null,
          status: "ready",
        },
      ],
      total_active: 1,
      setup_checklist: {
        connected: true,
        instructions_injected: true,
        vault_reconciled: true,
        tools_ready: true,
      },
    });
    const readyEl = document.createElement("div");
    tab._renderAgentDetail(readyEl);
    const readyBadge = readyEl.querySelector<HTMLElement>(
      '[data-pf-testid="agent-status-badge"]'
    );
    expect(readyBadge?.getAttribute("data-agent-state")).toBe("ready");
    expect(readyBadge?.textContent).toContain("Claude Code 已连接 · 全能力就绪");
    for (const i of [1, 2, 3, 4]) {
      expect(
        readyEl
          .querySelector(`[data-pf-testid="agent-check-${i}"]`)
          ?.getAttribute("data-checked")
      ).toBe("true");
    }
  });

  it("(d) live paperforge:agent-presence-changed event refreshes the Settings UI immediately and updates status bar pill", async () => {
    const { workspace, tab } = createHarness({ lang: "zh" });
    tab.activeTab = "module-detail";
    tab._selectedDetailModule = "agent";
    tab.display();

    expect(workspace.listenerCount("paperforge:agent-presence-changed")).toBe(
      1
    );
    expect(
      tab.containerEl
        .querySelector('[data-pf-testid="agent-status-badge"]')
        ?.getAttribute("data-agent-state")
    ).toBe("unconnected");

    // Simulate live MCP handshake event arriving on workspace
    workspace.trigger("paperforge:agent-presence-changed", {
      presence: {
        state: "ready",
        active_sessions: [
          {
            session_id: "s-99",
            client_name: "claude-code",
            client_version: "2.1.0",
            current_tool: "paperforge_annotate_batch",
            status: "ready",
          },
        ],
        total_active: 1,
        setup_checklist: {
          connected: true,
          instructions_injected: true,
          vault_reconciled: true,
          tools_ready: true,
        },
      } satisfies AgentPresenceSnapshotDto,
    });

    const liveBadge = tab.containerEl.querySelector<HTMLElement>(
      '[data-pf-testid="agent-status-badge"]'
    );
    expect(liveBadge?.getAttribute("data-agent-state")).toBe("ready");
    expect(liveBadge?.textContent).toContain("Claude Code 已连接 · 全能力就绪");
    expect(
      tab.containerEl.querySelector('[data-pf-testid="agent-live-tool"]')
        ?.textContent
    ).toContain("paperforge_annotate_batch");

    tab.hide();
    expect(workspace.listenerCount("paperforge:agent-presence-changed")).toBe(
      0
    );

    // Verify main.ts status bar pill + watcher cleanup
    const statusContainer = document.createElement("div");
    const openModuleSettings = vi.fn().mockReturnValue(true);
    const pf = Object.create(PaperForgePlugin.prototype) as PaperForgePlugin & {
      app: unknown;
      _unloaded: boolean;
      _agentPresence: AgentPresenceSnapshotDto | null;
      _statusBarEl: HTMLElement | null;
      _agentStatusBarEl: HTMLElement | null;
      _agentSessionsWatcher: { close?: () => void } | null;
      _agentSessionsDirWatcher: { close?: () => void } | null;
      _agentSessionsWatchTimer: ReturnType<typeof setTimeout> | null;
      _popoutWindows: Set<Window>;
      _daemonJobs: Map<string, unknown>;
      _client: {
        getAgentSessions: () => Promise<AgentPresenceSnapshotDto>;
        cancelActiveOperation: () => void;
        shutdownTransport: () => void;
      } | null;
      getClient: () => {
        getAgentSessions: () => Promise<AgentPresenceSnapshotDto>;
      };
      openModuleSettings: (m: string) => boolean;
      refreshAgentPresence: () => Promise<AgentPresenceSnapshotDto | null>;
    };
    pf._unloaded = false;
    pf._popoutWindows = new Set();
    pf._daemonJobs = new Map();
    pf._statusBarEl = statusContainer;
    pf._agentStatusBarEl = null;
    pf.openModuleSettings = openModuleSettings;
    const mockWs = createMockWorkspace();
    pf.app = {
      vault: { adapter: { basePath: "/vault" } },
      workspace: mockWs,
    };
    let liveSnap: AgentPresenceSnapshotDto = {
      state: "connected",
      active_sessions: [
        {
          session_id: "s-sb",
          client_name: "claude-code",
          current_tool: "paperforge_annotate_batch",
          status: "connected",
        },
      ],
      total_active: 1,
    };
    pf._client = {
      getAgentSessions: vi.fn(async () => liveSnap),
      cancelActiveOperation: vi.fn(),
      shutdownTransport: vi.fn(),
    };
    pf.getClient = () => pf._client!;

    await pf.refreshAgentPresence();
    const statusPill = statusContainer.querySelector<HTMLElement>(
      '[data-pf-testid="pf-status-agent-pill"]'
    );
    expect(statusPill).not.toBeNull();
    expect(statusPill!.style.display).toBe("inline-flex");
    expect(statusPill!.textContent).toContain("Claude Code");
    expect(statusPill!.textContent).toContain("批注中");

    statusPill!.click();
    expect(openModuleSettings).toHaveBeenCalledWith("agent");

    liveSnap = {
      state: "unconnected",
      active_sessions: [],
      total_active: 0,
    };
    await pf.refreshAgentPresence();
    expect(statusPill!.style.display).toBe("none");

    const watcherClose = vi.fn();
    pf._agentSessionsWatcher = { close: watcherClose };
    pf.onunload();
    expect(watcherClose).toHaveBeenCalledOnce();
    expect(pf._agentSessionsWatcher).toBeNull();
  });
});
