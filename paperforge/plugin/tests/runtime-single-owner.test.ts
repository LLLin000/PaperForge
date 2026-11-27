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

import PaperForgePlugin, { tryHandleExternalPdfLinkClick } from "../src/main";
import * as managedRuntime from "../src/services/managed-runtime";
import { setLanguage, t } from "../src/i18n";
import { PaperForgeSettingTab } from "../src/settings";
import type { App } from "obsidian";

describe("single-owner runtime installer & daemon UI progress", () => {
  const tempDirs: string[] = [];

  afterEach(() => {
    clearNoticeCalls();
    vi.useRealTimers();
    vi.restoreAllMocks();
    for (const d of tempDirs.splice(0)) {
      fs.rmSync(d, { recursive: true, force: true });
    }
  });

  function makeTab(opts: {
    hasDaemonRpc?: boolean;
    runtimeUpdating?: boolean;
    daemonUpdating?: boolean;
    liveRuntime?: {
      phaseText: string;
      current: number;
      total: number;
      startedAt: number | null;
    } | null;
    liveSync?: {
      phaseText: string;
      current: number;
      total: number;
      startedAt: number | null;
    } | null;
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
      manifest: { version: "2.0.11" },
      saveSettings: vi.fn(async () => undefined),
      readPaperforgeJson: () => ({}),
      isDaemonUpdating: () => Boolean(opts.daemonUpdating),
      isRuntimeUpdating: () => Boolean(opts.runtimeUpdating),
      getLiveTaskSummary: (kind: "runtime" | "sync") =>
        kind === "runtime"
          ? (opts.liveRuntime ?? null)
          : (opts.liveSync ?? null),
      getClient: () => ({
        hasDaemonRpc: () => Boolean(opts.hasDaemonRpc),
        daemonSubmitRuntimeJob,
        launchRuntimeInstaller,
        runtimeStatus,
        zoteroDetect: vi.fn(async () => ({ found: false })),
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
      "2.0.11",
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

  it("suppresses false 'cancelled' failure during daemon hot-swap and resumes Express auto-chain", () => {
    let daemonSwap = true;
    const daemonSubmitRuntimeJob = vi.fn(async () => ({
      accepted: true,
      coalesced: false,
      job: { job_id: "job_rt_2", status: "running" },
    }));
    const { tab } = makeTab({
      hasDaemonRpc: true,
      daemonSubmitRuntimeJob,
    });
    (
      (tab as any).plugin as { isDaemonUpdating: () => boolean }
    ).isDaemonUpdating = () => daemonSwap;

    (tab as any)._autoContinueSetupAfterInstall = true;
    (tab as any)._daemonDrivenRuntimeInstall = true;
    (tab as any)._setupOperation = "running";

    // Daemon hot-swap cancels the pre-swap runtime job
    tab.onDaemonRuntimeJobFinished("cancelled", "cancelled");
    expect((tab as any)._setupOperation).toBe("running");
    expect((tab as any)._setupFeedback).toBe(
      t("runtime_daemon_swapping_resume")
    );
    expect(String((tab as any)._setupFeedback)).not.toContain(
      "Runtime setup did not complete"
    );
    expect((tab as any)._autoContinueSetupAfterInstall).toBe(true);

    // Once hot-swap finishes, setup automatically resumes installer submission with autoContinueSetup preserved
    daemonSwap = false;
    tab.onDaemonSwapFinished();
    expect(daemonSubmitRuntimeJob).toHaveBeenCalledTimes(1);
    expect((tab as any)._autoContinueSetupAfterInstall).toBe(true);
    (tab as any)._stopRuntimePoll(false, "cleanup");
  });

  it("shows calm localized message on genuine runtime cancel and clears prior failure on retry", () => {
    const { tab } = makeTab({ hasDaemonRpc: true });
    (tab as any)._daemonDrivenRuntimeInstall = true;
    (tab as any)._setupOperation = "running";
    tab.onDaemonRuntimeJobFinished("cancelled", "cancelled");
    expect((tab as any)._setupOperation).toBe("idle");
    expect((tab as any)._setupFeedback).toBe(t("runtime_install_cancelled"));
    expect(String((tab as any)._setupFeedback)).not.toContain(": cancelled");

    (tab as any)._setupOperation = "failed";
    (tab as any)._setupFeedback = "stale error";
    (tab as any)._launchRuntimeInstaller("install", {
      autoContinueSetup: true,
    });
    expect((tab as any)._setupOperation).toBe("running");
    expect((tab as any)._setupFeedback).toBeNull();
    (tab as any)._stopRuntimePoll(false, "cleanup");
  });

  it("renders accurate Express CTA button labels & disabled state across engine install, sync, and ready stages", () => {
    const getPrimaryFooterBtn = (root: HTMLElement): HTMLButtonElement => {
      const btns = Array.from(
        root.querySelectorAll<HTMLButtonElement>(
          ".pf-express-footer-actions button.pf-action-btn"
        )
      );
      expect(btns.length).toBeGreaterThanOrEqual(2);
      return btns[btns.length - 1];
    };

    // Stage 1a: idle, no pointer -> honest Install Engine & Import label
    const ptrSpy = vi
      .spyOn(managedRuntime, "readRuntimePointer")
      .mockReturnValue(null);
    const t1 = makeTab({ hasDaemonRpc: true });
    (t1.tab as any)._runtimeStatusVersion = "2.0.11";
    (t1.tab as any)._runtimeStatus = { runtime_ready: false };
    (t1.tab as any)._zoteroDetectData = { found: true, total_papers: 12 };
    const w1 = document.createElement("div");
    (t1.tab as any)._renderExpressSetup(w1, false);
    const btn1 = getPrimaryFooterBtn(w1);
    expect(btn1.disabled).toBe(false);
    expect(btn1.textContent).toContain("Install Engine & Import 12 Papers");

    // Stage 1b: idle, outdated pointer -> honest Update Engine & Import label
    ptrSpy.mockReturnValue({
      pythonPath: "/opt/pf/python",
      environmentRoot: "/opt/pf",
      paperforgeVersion: "2.0.10",
    });
    (t1.tab as any)._runtimeStatus = {
      runtime_ready: false,
      version_matches_expected: false,
    };
    const w1b = document.createElement("div");
    (t1.tab as any)._renderExpressSetup(w1b, false);
    const btn1b = getPrimaryFooterBtn(w1b);
    expect(btn1b.disabled).toBe(false);
    expect(btn1b.textContent).toContain("Update Engine & Import 12 Papers");

    // Stage 2: installing runtime (step 3/5) -> disabled with Installing engine (3/5)
    ptrSpy.mockReturnValue(null);
    const t2 = makeTab({
      hasDaemonRpc: true,
      runtimeUpdating: true,
      liveRuntime: {
        phaseText: "Step 3/5: Downloading engine",
        current: 3,
        total: 5,
        startedAt: Date.now() - 4000,
      },
    });
    (t2.tab as any)._runtimeStatusVersion = "2.0.11";
    (t2.tab as any)._runtimeStatus = { runtime_ready: false };
    (t2.tab as any)._autoContinueSetupAfterInstall = true;
    const w2 = document.createElement("div");
    (t2.tab as any)._renderExpressSetup(w2, false);
    const btn2 = getPrimaryFooterBtn(w2);
    expect(btn2.disabled).toBe(true);
    expect(btn2.textContent).toContain(
      "Installing engine (3/5), then importing"
    );
    (t2.tab as any)._stopRuntimePoll(false, "cleanup");

    // Stage 3: runtime ready & syncing library (step 2/5) -> disabled with Importing library (2/5)
    const t3 = makeTab({
      hasDaemonRpc: true,
      liveSync: {
        phaseText: "Step 2/5: Generating notes",
        current: 2,
        total: 5,
        startedAt: Date.now() - 2000,
      },
    });
    (t3.tab as any)._runtimeStatusVersion = "2.0.11";
    (t3.tab as any)._runtimeStatus = { runtime_ready: true };
    (t3.tab as any)._setupOperation = "running";
    (t3.tab as any)._setupPhase = "syncing";
    const w3 = document.createElement("div");
    (t3.tab as any)._renderExpressSetup(w3, false);
    const btn3 = getPrimaryFooterBtn(w3);
    expect(btn3.disabled).toBe(true);
    expect(btn3.textContent).toContain("Importing library (2/5)");
  });

  it("intercepts clicks on external OS pdf_path wikilinks in Obsidian Properties", () => {
    const prop = document.createElement("div");
    prop.className = "metadata-property";
    prop.setAttribute("data-property-key", "pdf_path");
    const link = document.createElement("div");
    link.className = "internal-link metadata-link-inner";
    link.textContent = "C:/Users/Researcher/Zotero/storage/Q2245LXK/paper.pdf";
    prop.appendChild(link);
    document.body.appendChild(prop);

    const openPaperPdf = vi.fn();
    const clickEvt = new MouseEvent("click", {
      bubbles: true,
      cancelable: true,
    });
    Object.defineProperty(clickEvt, "target", { value: link });

    const handled = tryHandleExternalPdfLinkClick(clickEvt, {
      app: {
        vault: { getAbstractFileByPath: () => null },
        workspace: {
          getActiveFile: () => ({
            path: "Resources/Literature/Ortho/4M3K4W7C/4M3K4W7C.md",
            basename: "4M3K4W7C",
          }),
        },
        metadataCache: {
          getFileCache: () => ({ frontmatter: { zotero_key: "4M3K4W7C" } }),
        },
      } as unknown as App,
      baseSnapshot: null,
      openPaperPdf,
    });

    prop.remove();
    expect(handled).toBe(true);
    expect(clickEvt.defaultPrevented).toBe(true);
    expect(openPaperPdf).toHaveBeenCalledWith("4M3K4W7C");
  });
});
