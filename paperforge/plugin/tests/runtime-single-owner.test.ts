import { afterEach, describe, expect, it, vi } from "vitest";
import "obsidian-test-mocks/jest-setup";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";

const { noticeCalls, clearNoticeCalls } = vi.hoisted(() => {
  const calls: { msg: string; timeout?: number }[] = [];
  return {
    noticeCalls: calls,
    clearNoticeCalls: () => {
      calls.length = 0;
    },
  };
});

vi.mock("obsidian", () => ({
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
    addText() {
      return this;
    }
    addToggle() {
      return this;
    }
    addDropdown() {
      return this;
    }
    addButton() {
      return this;
    }
    addExtraButton() {
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
    open() {}
    close() {}
  },
  Notice: class {
    constructor(msg: string, timeout?: number) {
      noticeCalls.push({ msg, timeout });
    }
  },
  Plugin: class {
    app: Record<string, unknown> = {};
  },
  ItemView: class {
    leaf: unknown;
    app: Record<string, unknown> = {};
    containerEl: HTMLDivElement;
    constructor(leaf?: unknown) {
      this.leaf = leaf;
      this.containerEl = document.createElement("div");
    }
  },
  MarkdownRenderer: class {},
  Component: class {
    load() {}
    unload() {}
  },
  TFile: class {},
  Vault: class {},
  MarkdownView: class {},
  Scope: class {},
  Keymap: class {},
  setIcon: () => {},
  debounce: (fn: (...args: unknown[]) => void) => fn,
  prepareSimpleSearch: () => () => null,
  setTooltip: () => {},
  Platform: {},
}));

import PaperForgePlugin from "../src/main";
import { setLanguage, t } from "../src/i18n";
import { PaperForgeSettingTab } from "../src/settings";
import type { App } from "obsidian";

describe("single-owner runtime installer & daemon UI progress", () => {
  const tempDirs: string[] = [];

  afterEach(() => {
    clearNoticeCalls();
    vi.useRealTimers();
    for (const d of tempDirs.splice(0)) {
      fs.rmSync(d, { recursive: true, force: true });
    }
  });

  function makeTab(opts: {
    hasDaemonRpc?: boolean;
    runtimeUpdating?: boolean;
    daemonSubmitRuntimeJob?: ReturnType<typeof vi.fn>;
    launchRuntimeInstaller?: ReturnType<typeof vi.fn>;
    runtimeStatus?: ReturnType<typeof vi.fn>;
  }) {
    const daemonSubmitRuntimeJob =
      opts.daemonSubmitRuntimeJob ??
      vi.fn(async () => ({
        accepted: true,
        coalesced: false,
        job: { job_id: "job_rt_1", status: "running" },
      }));
    const launchRuntimeInstaller =
      opts.launchRuntimeInstaller ??
      vi.fn(() => ({ ok: true, logPath: "/tmp/unused.log" }));
    const runtimeStatus =
      opts.runtimeStatus ??
      vi.fn(async () => ({ runtime_ready: false, needs_update: true }));

    const plugin = {
      settings: {
        _setup_complete: true,
        language: "en",
        system_dir: ".paperforge",
        zotero_data_dir: "/Zotero",
        proxy_url: "",
        prefer_cn_mirror: false,
        allow_uv_download: true,
      },
      manifest: { version: "2.0.9" },
      saveSettings: vi.fn(),
      readPaperforgeJson: () => ({}),
      isRuntimeUpdating: () => Boolean(opts.runtimeUpdating),
      getClient: () => ({
        hasDaemonRpc: () => Boolean(opts.hasDaemonRpc),
        daemonSubmitRuntimeJob,
        launchRuntimeInstaller,
        runtimeStatus,
        probeAll: vi.fn(),
        probe: vi.fn(),
        invalidateCache: vi.fn(),
        isOperationActive: () => false,
      }),
    };
    const app = {
      vault: {
        adapter: { basePath: "/vault" },
        getConfig: () => "en",
      },
    } as unknown as App;
    const tab = new PaperForgeSettingTab(app, plugin as never);
    setLanguage(app, "en");
    (tab as any).display = vi.fn();
    return {
      tab,
      daemonSubmitRuntimeJob,
      launchRuntimeInstaller,
      runtimeStatus,
    };
  }

  it("routes runtime install/update through Rust daemon RPC instead of spawning detached Python", async () => {
    const { tab, daemonSubmitRuntimeJob, launchRuntimeInstaller } = makeTab({
      hasDaemonRpc: true,
    });

    (tab as any)._launchRuntimeInstaller("update");
    await vi.waitFor(() => {
      expect(daemonSubmitRuntimeJob).toHaveBeenCalledTimes(1);
    });
    expect(daemonSubmitRuntimeJob).toHaveBeenCalledWith(
      "update",
      "2.0.9",
      expect.objectContaining({
        proxyUrl: undefined,
        preferCnMirror: undefined,
      })
    );
    expect(launchRuntimeInstaller).not.toHaveBeenCalled();
    expect(
      noticeCalls.some((n) => n.msg === t("runtime_installer_opened"))
    ).toBe(true);
    (tab as any)._stopRuntimePoll(false, "done");
  });

  it("attaches to an already-running background runtime update and hides duplicate Update buttons", () => {
    const { tab, daemonSubmitRuntimeJob, launchRuntimeInstaller } = makeTab({
      hasDaemonRpc: true,
      runtimeUpdating: true,
    });

    (tab as any)._launchRuntimeInstaller("update");
    expect(daemonSubmitRuntimeJob).not.toHaveBeenCalled();
    expect(launchRuntimeInstaller).not.toHaveBeenCalled();
    expect(
      noticeCalls.some((n) => n.msg === t("runtime_update_already_running"))
    ).toBe(true);

    (tab as any)._installerLogPath = path.join(
      os.tmpdir(),
      `pf-nonexistent-${Date.now()}.log`
    );
    (tab as any)._runtimeStatus = {
      runtime_ready: false,
      compatible: false,
      needs_update: true,
      current_version: "2.0.8",
      expected_version: "2.0.9",
    };
    const host = document.createElement("div");
    (tab as any)._renderInstallationDetail(host, { inline: true });
    expect(host.textContent || "").toContain(t("runtime_installing"));
    expect(host.textContent || "").toContain(t("runtime_cancel_btn"));
    const buttonTexts = Array.from(host.querySelectorAll("button")).map((b) =>
      (b.textContent || "").trim()
    );
    expect(buttonTexts).not.toContain(t("btn_update_runtime"));
    expect(buttonTexts).not.toContain(t("runtime_update_btn"));
    (tab as any)._stopRuntimePoll(false, "done");
  });

  it("reads installer logs from run offset, ignores transient lock contention, and formats step failure cleanly", async () => {
    vi.useFakeTimers();
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "pf-log-offset-"));
    tempDirs.push(tmpDir);
    const logPath = path.join(tmpDir, "installer.log");

    // Stale error from an earlier aborted install must be ignored once offset is captured.
    fs.writeFileSync(
      logPath,
      "[PaperForge] Old run line\n[PaperForge] Installer step failed.\n",
      "utf-8"
    );

    const { tab } = makeTab({ hasDaemonRpc: true });
    (tab as any)._installerLogPath = logPath;
    (tab as any)._installerLogStartOffset = (
      tab as any
    )._captureInstallerLogStartOffset(logPath);
    (tab as any)._setupOperation = "running";
    expect((tab as any)._readInstallerLogSinceStart()).toBe("");

    // Concurrent lock contention + failed marker during overlap should keep polling.
    fs.appendFileSync(
      logPath,
      "Error: Another PaperForge runtime install is already running.\nlock: install.lock\n[PaperForge] Installer step failed.\n",
      "utf-8"
    );
    (tab as any)._pollRuntimeUntilReady();

    await vi.advanceTimersByTimeAsync(3100);
    expect((tab as any)._runtimePollTimer).not.toBeNull();
    expect((tab as any).display).toHaveBeenCalled();

    // Advance start offset to a fresh run and append a real step failure without lock contention.
    (tab as any)._installerLogStartOffset = (
      tab as any
    )._captureInstallerLogStartOffset(logPath);
    fs.appendFileSync(
      logPath,
      "[PaperForge] Publishing verified runtime environment...\npython.exe exited with code 1\n[PaperForge] Installer step failed.\n",
      "utf-8"
    );
    await vi.advanceTimersByTimeAsync(3100);

    expect((tab as any)._runtimePollTimer).toBeNull();
    expect((tab as any)._setupOperation).toBe("failed");
    const feedback = String((tab as any)._setupFeedback || "");
    expect(feedback).toContain("Installer step failed");
    expect(feedback).toContain("Runtime setup did not complete:");
    expect(feedback).not.toContain("Could not open the installer");
  });

  it("maps daemon runtime.update jobs to kind='runtime' in getActiveBackgroundTasks", () => {
    const clientMock = {
      isOperationActive: () => false,
    };
    const daemonJobs = new Map([
      [
        "job_rt_update",
        {
          job_id: "job_rt_update",
          kind: "runtime.update",
          status: "running",
          current: 3,
          total: 5,
          vault: "global",
          phase: "downloading",
          source: "job.submit",
        },
      ],
      [
        "job_sync_1",
        {
          job_id: "job_sync_1",
          kind: "sync",
          status: "running",
          current: 1,
          total: 4,
          vault: "/vault",
          phase: "syncing",
          source: "job.submit",
        },
      ],
    ]);
    const tasks = PaperForgePlugin.prototype.getActiveBackgroundTasks.call({
      _client: clientMock,
      getClient: () => clientMock,
      _daemonJobs: daemonJobs,
      _ocrRunning: false,
      _runningIndexTask: false,
      _runningOcrKey: null,
      _syncInFlight: false,
      app: { vault: { getConfig: () => "en" } },
      settings: { language: "en" },
    });

    const rtTask = tasks.find((task) => task.kind === "runtime");
    expect(rtTask).toBeDefined();
    expect(rtTask!.label).toBe(t("activity_runtime_updating"));
    expect(rtTask!.current).toBe(3);
    expect(rtTask!.total).toBe(5);

    const syncTask = tasks.find((task) => task.kind === "sync");
    expect(syncTask).toBeDefined();
    expect(tasks).toHaveLength(2);
  });

  it("exposes live daemon updating & sync phase summary in getActiveBackgroundTasks and getLiveTaskSummary", () => {
    const clientMock = {
      isOperationActive: () => false,
    };
    const nowSec = Math.floor(Date.now() / 1000) - 5;
    const daemonJobs = new Map([
      [
        "cli_sync_1",
        {
          job_id: "cli_sync_1",
          kind: "sync",
          status: "running",
          current: 3,
          total: 5,
          phase: "build_index",
          item_id: "",
          vault: "/vault",
          started_at: nowSec,
        },
      ],
    ]);
    const pluginCtx = {
      _client: clientMock,
      getClient: () => clientMock,
      _daemonJobs: daemonJobs,
      _daemonUpdating: true,
      _ocrRunning: false,
      _runningIndexTask: false,
      _runningOcrKey: null,
      _syncInFlight: false,
      _autoSyncRunning: true,
      _syncStartedAt: nowSec * 1000,
      app: { vault: { getConfig: () => "zh" } },
      settings: { language: "zh" },
    };
    setLanguage(pluginCtx.app as unknown as App, "zh");
    const tasks =
      PaperForgePlugin.prototype.getActiveBackgroundTasks.call(pluginCtx);
    expect(tasks.some((x) => x.kind === "runtime")).toBe(true);
    const syncSummary = PaperForgePlugin.prototype.getLiveTaskSummary.call(
      pluginCtx,
      "sync"
    );
    expect(syncSummary).not.toBeNull();
    expect(syncSummary!.current).toBe(3);
    expect(syncSummary!.total).toBe(5);
    expect(syncSummary!.phaseText).toContain("步骤 3/5");
  });
});
