import {
  PluginSettingTab,
  App,
  Setting,
  Notice,
  setTooltip,
  MarkdownRenderer,
  Component,
} from "obsidian";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { execFile, execFileSync, spawn, exec } from "child_process";
import { configSet } from "./services/config-client";
import { t, setLanguage, langFromApp } from "./i18n";
import {
  PaperForgeSettings,
  ProbeEnvelope,
  ActionPrimary,
  CapabilityModule,
  CAPABILITY_MODULES,
  createUnknownEnvelope,
  createStaleEnvelope,
  createInvalidEnvelope,
  isValidEnvelope,
  isEnvelopeStale,
  isReadyEnvelope,
  probeAction,
  setupAction,
  validatePersistedEnvelopes,
  classifyCapabilityAction,
} from "./constants";
import releaseNotesData from "./release-notes.json";
import {
  renderStatusBadge,
  renderActivityRow,
  renderActionButton,
  renderDisclosure,
  renderErrorAnatomy,
  renderConfigurationSummary,
  renderImpactConfirmation,
  buildSupportDiagnostic,
  copySupportDiagnostic,
  captureLastKnown,
  shouldUpdateLastKnown,
  collectDiagnosticModules,
  type LastKnownState,
  type DiagnosticInput,
} from "./primitives";
import {
  paperforgeEnrichedEnv,
  buildTargetedEnv,
  scanBbtUnderProfiles,
  scanBbtDirectChildren,
  runSubprocess,
} from "./services/python-bridge";
import { EmbedBuildController } from "./services/embed-build-controller";
import { deferred } from "./services/deferred";
import { orchestrateFromSync } from "./services/next-actions-bridge";
import {
  queryMemoryDetail,
  queryEmbedStatus,
  queryEmbeddingCredentialStatus,
  probeAll,
  invalidateAll,
} from "./services/config-client";
import {
  PaperForgeConfirmModal,
  PaperForgeIssueDraftModal,
  buildRedactedDraft,
  checkOrphanState,
} from "./views/modals";
import {
  RuntimeBootstrap,
  resolveRuntimeCommand,
} from "./services/managed-runtime";
import { getDisclosureState, toggleDisclosureState } from "./utils/disclosure";
import { stripCredentialEnv } from "./services/secret-storage";
import { processProgressChunk } from "./services/progress-parser";
import type { OcrProcessOutcome } from "./services/ocr-process-controller";

// ── Interface ──

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface ISettingPlugin {
  settings: PaperForgeSettings;
  saveSettings(): Promise<void>;
  loadSettings(): Promise<void>;
  manifest: { version: string };
  getManagedRuntime(): RuntimeBootstrap | null;
  [key: string]: any;
}

export class PaperForgeSettingTab extends PluginSettingTab {
  plugin: ISettingPlugin;
  private _saveTimeout: ReturnType<typeof setTimeout> | null = null;
  private _pfConfig: Record<string, string> | null = null;
  private _lastSyncTime: string | null = null;
  private _memoryStatusText: string | null = null;
  private _vectorDepsOk: boolean | null = null;
  private _embedStatusText: string | null = null;
  private _skillsCollapsed: Record<string, boolean> = { user: true };
  private _featurePanelsCollapsed: Record<string, unknown> = {};
  private _advCollapsed = true;
  private _refreshPending = false;
  private _pythonInterpDescEl: HTMLElement | null = null;
  private _customPathDescEl: HTMLElement | null = null;
  private _checkEl: HTMLDivElement | null = null;
  activeTab = "overview";
  private _buildState: string = "idle";
  private _buildProgress: { current: number; total: number; key: string } = {
    current: 0,
    total: 0,
    key: "",
  };
  /** Cached capability probe envelopes, keyed by module name. */
  private _capabilityState: Record<string, ProbeEnvelope> | null = null;
  /** #85: Last Known State — preserved across probe runs, never cleared on stale/fail. */
  private _lastKnownState: Map<string, LastKnownState> = new Map();
  /** #85: Navigation memory — persisted across reopen. */
  private _navMemory: { destination: string; module?: string } = {
    destination: "overview",
  };
  /** #85: True only for the first display() call — guards _restoreNavMemory. */
  private _initialDisplay: boolean = true;
  /** Tracks which modules are currently being probed. */
  private _probing: Set<string> = new Set();
  /** Modules that have already been auto-probed (prevents endless re-probe). */
  private _attemptedProbes: Set<string> = new Set();
  /** Currently active sub-view within the Setup tab. */
  _setupView: "overview" | "module-detail" = "overview";
  /** #87: Setup Journey current stage (1-4). */
  _setupStage = 1;
  /** #87: Selected optional capabilities. */
  _setupOptionals: Record<string, boolean> = {
    ocr: false,
    memory: false,
    agent: false,
  };
  /** Explicit reinstall stays inside the current setup journey. */
  private _setupReinstallRequested = false;
  private _setupOperation: "idle" | "running" | "failed" = "idle";
  private _setupFeedback: string | null = null;
  /** RC UX Seam P1: user chose "Later" — pure session flag; reset on hide(). */
  private _setupJourneyDismissedForSession = false;
  /** Currently selected module in the detail view. */
  _selectedDetailModule: string = "";
  /** Focus target id after re-render. */
  _focusTargetId: string | null = null;
  /** AbortController for in-flight runtime ensure/install. */
  private _runtimeAbortController: AbortController | null = null;
  /** Cached RuntimeBootstrap singleton (rebuilt per display() on path change). */
  private _managedRuntime: RuntimeBootstrap | null = null;
  /** True while a runtime operation is in flight. */
  private _runtimeBusy: boolean = false;
  /** True while a library sync or memory build is in flight. */
  _libraryRunning: boolean = false;
  private _displayInProgress: boolean = false;
  _detailReturn: { tab: string; selector: string } | null = null;
  private _agentPlatformDraft: string | null = null;

  /** #86: Five operational modules in display order with user-facing names. */
  private _getOverviewModules(): { id: string; label: string }[] {
    return [
      { id: "installation", label: t("cc_module_foundation") || "Foundation" },
      { id: "library", label: t("cc_module_library") || "Library" },
      { id: "ocr", label: t("cc_module_ocr") || "OCR" },
      { id: "memory", label: t("cc_module_memory") || "Smart Retrieval" },
      { id: "agent", label: t("cc_module_agent") || "Agent Integration" },
    ];
  }

  private _getUserModuleName(mod: string): string {
    const key =
      "cc_module_" +
      (mod === "installation"
        ? "foundation"
        : mod === "memory"
          ? "memory"
          : mod);
    return t(key) || mod.charAt(0).toUpperCase() + mod.slice(1);
  }

  constructor(app: App, plugin: ISettingPlugin) {
    super(app, plugin as any);
    this.plugin = plugin;
  }

  /** Reload path config — #142/C0: display mirrors hydrated from Python by
   * main.ts; the plugin never parses paperforge.json. */
  _refreshPfConfig() {
    const s = this.plugin.settings;
    this._pfConfig = {
      system_dir: s.system_dir || "System",
      resources_dir: s.resources_dir || "Resources",
      literature_dir: s.literature_dir || "Literature",
      base_dir: s.base_dir || "Bases",
      zotero_data_dir: s.zotero_data_dir || "",
    };
  }

  display() {
    this._displayInProgress = true;
    const { containerEl } = this;
    containerEl.empty();
    this._refreshPfConfig();
    if (this._initialDisplay) {
      this._restoreNavMemory();
      this._initialDisplay = false;
    }
    this._initCapabilityState();

    // #87: Show Setup Journey on first open (never reverse once complete)
    // #87: Only show Setup Journey for first-time users (explicitly false).
    // Existing installations (undefined) skip the journey.
    // RC UX Seam P1: "Later" sets a pure session flag so the Overview is
    // reachable even while _setup_complete stays false — but the flag is
    // reset when Settings closes, so reopening resumes the Journey at the
    // exact stage the user left.
    if (
      this.plugin.settings._setup_complete === false &&
      !this._setupJourneyDismissedForSession
    ) {
      this._renderSetupJourney(containerEl);
      this._displayInProgress = false;
      return;
    }

    // Inject tab CSS once
    if (!document.getElementById("paperforge-tab-styles")) {
      const style = document.createElement("style");
      style.id = "paperforge-tab-styles";
      style.textContent = `
                .paperforge-settings-tabs { display: flex; gap: 4px; margin-bottom: 16px; border-bottom: 1px solid var(--background-modifier-border); }
                .paperforge-settings-tab { padding: 6px 16px; border: none; background: none; cursor: pointer; border-bottom: 2px solid transparent; font-size: 14px; color: var(--text-muted); }
                .paperforge-settings-tab--active { color: var(--text-accent); border-bottom-color: var(--text-accent); }
                .paperforge-tab-content { display: none; }
                .paperforge-tab-content--active { display: block; }
                .paperforge-skills-collapse-header { display: flex !important; align-items: center; cursor: pointer; padding: 6px 0 !important; margin: 0 !important; }
                .paperforge-skills-collapse-header h4 { margin: 0 !important; }
                .paperforge-skills-collapse-content { margin: 0 !important; padding: 0 !important; }
                .paperforge-skills-group { margin-bottom: 10px; }
                .paperforge-skills-group:last-child { margin-bottom: 0; }
                .vertical-tab-content-container { overflow-y: scroll !important; }
                .paperforge-release-card { border: 1px solid var(--background-modifier-border); border-radius: 6px; padding: 12px; margin-bottom: 12px; }
                .paperforge-release-header { margin-bottom: 8px; }
                .paperforge-release-date { color: var(--text-muted); font-size: 12px; }
                .paperforge-release-section { margin-bottom: 6px; }
                .paperforge-release-label { font-weight: 600; color: var(--text-accent); margin-bottom: 2px; font-size: 13px; }
                .paperforge-release-item { font-size: 13px; margin-left: 8px; color: var(--text-muted); }
                .paperforge-release-item-bold { font-size: 13px; margin-left: 8px; font-weight: 600; color: var(--text-normal); }
                .paperforge-release-recommended { background: rgba(var(--color-orange-rgb, 255,166,0), 0.08); border-radius: 4px; padding: 6px 8px; }
                .paperforge-manual-links { margin-top: 8px; }
                .paperforge-manual-links a { color: var(--text-accent); }
                .paperforge-modal-item { font-size: 13px; margin-left: 8px; color: var(--text-muted); }
                .paperforge-migration-warning { border: 1px solid var(--text-warning); border-radius: 6px; padding: 10px 14px; margin-bottom: 12px; background: rgba(var(--color-yellow-rgb, 255, 208, 0), 0.08); color: var(--text-warning); font-size: 13px; }
                .paperforge-migration-warning strong { color: var(--text-warning); }
                .paperforge-migration-warning code { background: var(--background-modifier-border); padding: 1px 4px; border-radius: 3px; }
                .pf-maintenance-inbox { margin-bottom: 24px; container-type: inline-size; }
                .pf-maintenance-inbox-empty { color: var(--text-muted); font-style: italic; padding: 12px 0; }
                .pf-maintenance-inbox-summary { font-weight: 600; margin-bottom: 8px; }
                .pf-maintenance-inbox-list { display: flex; flex-direction: column; gap: 8px; }
                .pf-maintenance-inbox-item { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding: 8px 12px; border: 1px solid var(--background-modifier-border); border-radius: 6px; background: var(--background-primary); flex-wrap: wrap; }
                @container (max-width: 730px) { .pf-maintenance-inbox-item { flex-direction: column; } .pf-maintenance-inbox-item-actions { width: 100%; justify-content: flex-end; } }
                .pf-maintenance-inbox-item--dismissed { opacity: 0.45; }
                .pf-maintenance-inbox-item-info { flex: 1; min-width: 0; }
                .pf-maintenance-inbox-item-module { font-weight: 600; cursor: pointer; background: none; border: none; color: var(--text-accent); padding: 0; font-size: inherit; text-align: left; }
                .pf-maintenance-inbox-item-module:hover { text-decoration: underline; }
                .pf-maintenance-inbox-item-reason { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
                .pf-maintenance-inbox-item-activity { font-size: 11px; color: var(--text-accent); margin-top: 2px; }
                .pf-maintenance-inbox-item-actions { display: flex; align-items: center; gap: 6px; flex-shrink: 0; flex-wrap: wrap; }
                .pf-maintenance-inbox-item-badge { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: var(--background-modifier-border); white-space: nowrap; }
                .pf-maintenance-inbox-item-badge--warn { background: rgba(var(--color-yellow-rgb),0.15); color: var(--text-warning); }
                .pf-maintenance-inbox-item-badge--error { background: rgba(var(--color-red-rgb),0.12); color: var(--text-error); }
                .pf-maintenance-inbox-item-badge--unknown { background: var(--background-modifier-border); color: var(--text-muted); }
                .pf-maintenance-inbox-item-action { font-size: 12px; padding: 3px 10px; cursor: pointer; }
                .pf-maintenance-inbox-item-dismiss { font-size: 11px; padding: 2px 6px; background: none; border: 1px solid var(--background-modifier-border); border-radius: 4px; cursor: pointer; color: var(--text-muted); }
                .paperforge-confirm-effect { margin: 8px 0; font-size: 13px; }
                .paperforge-confirm-effect-label { font-weight: 600; }
                .paperforge-confirm-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px; }
                .paperforge-issue-draft-desc { font-size: 13px; color: var(--text-muted); margin-bottom: 12px; }
                .paperforge-issue-draft-field { margin-bottom: 12px; }
                .paperforge-issue-draft-field label { display: block; font-weight: 600; margin-bottom: 4px; font-size: 13px; }
                .paperforge-issue-draft-input { width: 100%; padding: 6px 8px; border: 1px solid var(--background-modifier-border); border-radius: 4px; font-size: 13px; }
                .paperforge-issue-draft-textarea { width: 100%; padding: 6px 8px; border: 1px solid var(--background-modifier-border); border-radius: 4px; font-size: 13px; resize: vertical; min-height: 120px; }
                .paperforge-issue-draft-preview { margin: 12px 0; padding: 8px 12px; background: var(--background-secondary); border-radius: 6px; font-size: 12px; }
                .paperforge-issue-draft-preview-label { font-weight: 600; }
                .paperforge-issue-draft-included { color: var(--text-success); margin-bottom: 2px; }
                .paperforge-issue-draft-redacted { color: var(--text-warning); }
                .paperforge-issue-draft-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px; }
                .pf-diag-table { width: 100%; border-collapse: collapse; font-size: 12px; }
                .pf-diag-table tr + tr { border-top: 1px solid var(--background-modifier-border); }
                .pf-diag-label { padding: 4px 8px; color: var(--text-muted); white-space: nowrap; vertical-align: top; width: 140px; }
                .pf-diag-value { padding: 4px 8px; color: var(--text-normal); font-family: var(--font-monospace); }
                .pf-sr-diagnostics { margin-top: 16px; padding: 8px 12px; border: 1px solid var(--background-modifier-border); border-radius: 6px; }
                .pf-sr-diagnostics summary { cursor: pointer; font-weight: 600; font-size: 13px; color: var(--text-muted); }
                .pf-sr-diagnostics summary:hover { color: var(--text-normal); }
                .pf-sr-diagnostics-body { margin-top: 8px; }
            `;
      document.head.appendChild(style);
    }

    // Issue #79: render persisted migration warnings (visible after restart)
    const warnings = this.plugin.settings._migration_warnings;
    if (Array.isArray(warnings) && warnings.length > 0) {
      const banner = containerEl.createDiv({
        cls: "paperforge-migration-warning",
      });
      const keyNames = warnings
        .map((k: string) =>
          k === "paddleocr_api_key" ? "OCR" : "Smart Retrieval"
        )
        .join(", ");
      banner.createEl("strong", {
        text: t("migration_banner_title"),
      });
      banner.createEl("p", {
        text: t("migration_banner_body").replace("{modules}", keyNames),
      });
      banner.createEl("p", {
        text: t("migration_banner_next"),
        cls: "paperforge-manual-links",
      });
    }
    // --- Topbar ---
    const topbar = containerEl.createDiv({ cls: "pf-cc-topbar" });

    // Left: Brand + Version
    const brandLeft = topbar.createDiv({ cls: "pf-cc-topbar-left" });
    brandLeft.createEl("span", {
      cls: "pf-cc-topbar-brand",
      text: "PaperForge",
    });
    brandLeft.createEl("span", {
      cls: "pf-cc-topbar-version",
      text: "v" + (this.plugin.manifest?.version ?? "?"),
    });

    // Center: Tab buttons
    const tabCenter = topbar.createDiv({ cls: "pf-cc-topbar-center" });
    const tabs = [
      { id: "overview", label: t("tab_overview") || "Overview" },
      { id: "help", label: t("tab_help") || "Help" },
    ];
    const tabContents: Record<string, HTMLDivElement> = {};

    tabs.forEach((tab) => {
      const btn = tabCenter.createEl("button", {
        cls:
          "pf-cc-topbar-tab" +
          (tab.id === this.activeTab ? " pf-cc-topbar-tab--active" : ""),
        text: tab.label,
      });
      btn.addEventListener("click", () => {
        this._detailReturn = null;
        this.activeTab = tab.id;
        this._navMemory = { destination: tab.id };
        this._persistNavMemory();
        this.display();
      });
    });

    // Right: OCR Workspace link
    const rightLink = topbar.createDiv({ cls: "pf-cc-topbar-right" });
    const ocrLink = rightLink.createEl("a", {
      cls: "pf-cc-topbar-ocr-link",
      text: (t("md_ocr_workspace") || "OCR Workspace") + " \u2197",
      attr: { href: "#", role: "button" },
    });
    ocrLink.addEventListener("click", (e: MouseEvent) => {
      e.preventDefault();
      (this.app as any).setting.close();
      (this.app as any).workspace.getLeaf().setViewState({
        type: "paperforge-ocr-workspace",
      });
    });

    // --- Tab content containers ---
    tabs.forEach((tab) => {
      tabContents[tab.id] = containerEl.createDiv({
        cls:
          "paperforge-tab-content" +
          (tab.id === this.activeTab ? " paperforge-tab-content--active" : ""),
      });
    });

    // Module Detail is contextual (not a top-level tab), always create its container
    tabContents["module-detail"] = containerEl.createDiv({
      cls:
        "paperforge-tab-content" +
        (this.activeTab === "module-detail"
          ? " paperforge-tab-content--active"
          : ""),
    });

    // --- Render active tab ---
    if (this.activeTab === "overview") {
      this._renderOverviewTab(tabContents.overview);
    } else if (this.activeTab === "module-detail") {
      this._renderModuleDetailTab(tabContents["module-detail"]);
    } else if (this.activeTab === "help") {
      this._renderHelpTab(tabContents.help);
    }

    // Focus restoration after render (Issue #77)
    // Do NOT consume _focusTargetId while Help tab is active —
    // focus targets for Overview must survive until Overview renders again.
    if (this._focusTargetId && this.activeTab !== "help") {
      let target = containerEl.querySelector<HTMLElement>(this._focusTargetId);
      // #86: If target not found (e.g., help card removed from overview),
      // fall back to first overview card
      if (!target && this.activeTab === "overview") {
        target = containerEl.querySelector(".pf-cc-module-card");
      }
      if (target) {
        try {
          target.focus();
        } catch {}
        this._focusTargetId = null;
      }
    }
    this._displayInProgress = false;
  }
  private _startSetupJourney(
    stage: 1 | 2 | 3 | 4 = 1,
    reinstall = false
  ): void {
    this._setupStage = stage;
    this._setupReinstallRequested = reinstall;
    this._setupOperation = "idle";
    this._setupFeedback = null;
    this.plugin.settings._setup_complete = false;
    void this.plugin.saveSettings().then(() => this.display());
  }

  private _runSetupPython(
    args: string[],
    pythonOverride?: string,
    signal?: AbortSignal
  ): Promise<void> {
    // RC UX Seam P0: after Stage 1 publishes the managed pointer, every
    // later setup step MUST run on that runtime — never ambient `python`.
    // pythonOverride is used ONLY by Stage 1 pre-publication (the bootstrap
    // candidate); every other caller resolves the managed pointer and fails
    // closed when it is missing.
    let pythonExe = pythonOverride?.trim();
    if (!pythonExe) {
      const resolved = this._resolveRuntimeCommand(this._getVaultBasePath());
      pythonExe = resolved?.path ?? "";
    }
    if (!pythonExe) {
      return Promise.reject(new Error("no managed runtime pointer"));
    }
    const child = spawn(pythonExe, args, {
      cwd: this._getVaultBasePath(),
      env: paperforgeEnrichedEnv(),
      windowsHide: true,
      signal,
    });
    return new Promise<void>((resolve, reject) => {
      let stderr = "";
      let closed = false;
      let pendingAbort = false;
      const settle = (err: Error | null) => {
        if (closed) return;
        closed = true;
        err ? reject(err) : resolve();
      };
      child.stderr?.on("data", (chunk: Buffer) => {
        stderr += chunk.toString("utf-8");
      });
      child.once("error", (err: Error) => {
        if (signal?.aborted || err.name === "AbortError") {
          // RC UX Seam P0: abort is cooperative (SIGTERM sets a Python
          // flag, the child cleans up and exits by itself). Record the
          // cancellation but DO NOT settle until close() fires, so the UI
          // never returns to idle while the old setup child is still
          // running (which would allow an immediate Retry racing it).
          pendingAbort = true;
        } else {
          settle(err);
        }
      });
      child.once("close", (code) => {
        if (pendingAbort || signal?.aborted || code === null) {
          settle(new DOMException("Operation was cancelled", "AbortError"));
        } else {
          settle(code === 0 ? null : new Error(stderr || `exit code ${code}`));
        }
      });
    });
  }

  private _installFoundation(forceInstall: boolean): void {
    if (this._setupOperation === "running") return;
    this._setupOperation = "running";
    this._setupFeedback = null;
    this.display();

    // #174: the Setup Journey no longer runs its own pip — the ONLY
    // bootstrap install path is RuntimeBootstrap.installOnce into
    // ~/.paperforge/runtime/venv (ONE pinned paperforge[vector] install,
    // never --user).  After install, handshake → `paperforge setup --json`
    // (the #137 NDJSON machine stream) publishes the pointer — Python is
    // the only writer.
    // RC UX Seam: the whole chain (install → handshake → setup) is
    // cancellable through one AbortController; installOnce deletes the
    // half-installed venv on abort, and a cancelled install must NOT
    // republish the pointer or flip _setup_complete.
    this._runtimeAbortController = new AbortController();
    const signal = this._runtimeAbortController.signal;
    void (async () => {
      try {
        const vaultPath = this._getVaultBasePath();
        const bootstrap = this._ensureManagedRuntime();
        const installed = await bootstrap.installOnce(
          this.plugin.manifest.version,
          signal
        );
        const hs = await bootstrap.handshake(this.plugin.manifest.version, {
          pythonPath: installed.pythonPath,
          vaultPath,
          signal,
        });
        if (!hs.ok) {
          throw new Error(hs.reason ?? "handshake failed");
        }
        // Post-runtime setup (config/vault/deps/agent) + pointer publication,
        // through the #137 NDJSON stream (setup --json).
        const s = this.plugin.settings;
        const setupArgs = [
          "-m",
          "paperforge",
          "--vault",
          vaultPath,
          "setup",
          "--modular",
          "--json",
          "--system-dir",
          s.system_dir?.trim() || "System",
          "--resources-dir",
          s.resources_dir?.trim() || "Resources",
          "--literature-dir",
          s.literature_dir?.trim() || "Literature",
          "--base-dir",
          s.base_dir?.trim() || "Bases",
          "--agent",
          s.agent_platform || "opencode",
        ];
        if (s.zotero_data_dir?.trim()) {
          setupArgs.push("--zotero-data", s.zotero_data_dir.trim());
        }
        await this.plugin.saveSettings();
        await this._runSetupPython(setupArgs, installed.pythonPath, signal);
        this._setupOperation = "idle";
        this._setupReinstallRequested = false;
        this._setupFeedback = t("setup_install_complete");
        this._probeModule("installation");
        this._probeModule("help");
        this.display();
      } catch (error) {
        const isAbort =
          signal.aborted ||
          (typeof error === "object" &&
            error !== null &&
            (error as { name?: unknown }).name === "AbortError");
        if (isAbort) {
          // User cancelled: keep the wizard in place, show a neutral
          // message.  Never flip _setup_complete, never treat it as a
          // failure state.
          this._setupOperation = "idle";
          this._setupFeedback = t("setup_install_cancelled");
          this.display();
          return;
        }
        console.error("PaperForge runtime installation failed:", error);
        this._setupOperation = "failed";
        this._setupFeedback = t("setup_install_failed");
        this.display();
      } finally {
        this._runtimeAbortController = null;
      }
    })();
  }

  private _applyLibraryConfiguration(): void {
    if (this._setupOperation === "running") return;
    this._setupOperation = "running";
    this._setupFeedback = null;
    const settings = this.plugin.settings;
    const vaultPath = this._getVaultBasePath();
    const paths = {
      zotero_data_dir: settings.zotero_data_dir,
      system_dir: settings.system_dir,
      resources_dir: settings.resources_dir,
      literature_dir: settings.literature_dir,
      base_dir: settings.base_dir,
    };
    // #142 / C0: mutations route through the typed config commands; the
    // plugin never writes paperforge.json.
    void (async () => {
      const writes: Promise<unknown>[] = [];
      for (const [key, value] of Object.entries(paths)) {
        if (value && value.trim()) {
          writes.push(
            configSet(vaultPath, key, value.trim(), settings).catch((e) => {
              console.error(`PaperForge: config set ${key} failed`, e);
            })
          );
        }
      }
      await Promise.all(writes).catch(() => undefined);
      this.display();

      const args = [
        "-m",
        "paperforge",
        "--vault",
        vaultPath,
        "setup",
        "--modular",
        "--json",
        "--system-dir",
        settings.system_dir?.trim() || "System",
        "--resources-dir",
        settings.resources_dir?.trim() || "Resources",
        "--literature-dir",
        settings.literature_dir?.trim() || "Literature",
        "--base-dir",
        settings.base_dir?.trim() || "Bases",
        "--agent",
        settings.agent_platform || "opencode",
      ];
      if (settings.zotero_data_dir?.trim()) {
        args.push("--zotero-data", settings.zotero_data_dir.trim());
      }
      try {
        await this.plugin.saveSettings();
        await this._runSetupPython(args);
        this._setupOperation = "idle";
        this._setupFeedback = t("setup_library_configured");
        this._attemptedProbes.add("library");
        this._probeModule("library");
        this.display();
      } catch (error) {
        console.error("PaperForge library configuration failed:", error);
        this._setupOperation = "failed";
        this._setupFeedback = t("setup_library_config_failed");
        this.display();
      }
    })();
  }
  /** Render the Overview tab (header + control center + advanced settings). */
  _renderOverviewTab(containerEl: HTMLElement) {
    const vaultPath = this._getVaultBasePath();
    if (!this.plugin.settings.vault_path) {
      this.plugin.settings.vault_path = vaultPath;
      this._debouncedSave();
    }

    // ── Overview ──
    /* Header */
    containerEl.createEl("h2", { text: t("header_title") || "PaperForge" });
    containerEl.createEl("p", {
      text: t("desc"),
      cls: "paperforge-settings-desc",
    });

    // Auto-probe stale/unknown modules BEFORE rendering so cards show "Checking..."
    for (const mod of CAPABILITY_MODULES) {
      const env = this._capabilityState?.[mod];
      if (!env) continue;
      const neverProbed =
        env.capability_state === "unknown" &&
        env.updated_at === new Date(0).toISOString();
      const isStale =
        env.user_state === "detection_failed" &&
        env.reason.code.endsWith(".stale");
      if ((neverProbed || isStale) && !this._attemptedProbes.has(mod)) {
        this._attemptedProbes.add(mod);
        if (mod !== "maintenance") {
          this._probeModule(mod);
        }
      }
    }

    // ── Control Center (Issue #76) ──
    this._renderControlCenter(containerEl);
  }

  /** Safe vault base path extraction. */
  private _getVaultBasePath(): string {
    const adapter: unknown = this.app.vault.adapter;
    if (adapter && typeof adapter === "object" && "basePath" in adapter) {
      const bp: unknown = (adapter as Record<string, unknown>).basePath;
      return typeof bp === "string" ? bp : "";
    }
    return "";
  }

  /** Ensure RuntimeBootstrap singleton is initialized for the current machine. */
  private _ensureManagedRuntime(): RuntimeBootstrap {
    if (this._managedRuntime) return this._managedRuntime;
    this._managedRuntime =
      this.plugin.getManagedRuntime?.() ?? new RuntimeBootstrap();
    return this._managedRuntime;
  }

  /**
   * Resolve python command via managed runtime exclusively.
   * Returns null when managed runtime is not ready.
   */
  private _resolveRuntimeCommand(
    vp: string
  ): { path: string; args: string[] } | null {
    // 1. Use custom python_path from settings if set
    const customPath = this.plugin.settings.python_path?.trim();
    if (customPath && fs.existsSync(customPath)) {
      return { path: customPath, args: [] };
    }
    // 2. Fall back to the published pointer (#174): only a pointer-backed
    // runtime is usable — never an installed-but-unpublished one.
    const run = resolveRuntimeCommand(
      this._ensureManagedRuntime().readPointer()
    );
    if (run) {
      return { path: run.command, args: [...run.args] };
    }
    return null;
  }

  /** Render the Installation detail view (Issue #77). */
  /** Render Foundation with the shared module-detail shell. */
  _renderInstallationDetail(containerEl: HTMLElement): void {
    this._renderModuleDetailShell(containerEl, "installation");
    const env =
      this._capabilityState?.installation ??
      createUnknownEnvelope("installation");
    const body = containerEl.createDiv({ cls: "pf-module-body" });
    body.createEl("h3", { text: t("md_foundation_overview") });
    body.createEl("p", {
      text:
        env.user_state === "ready"
          ? t("md_foundation_ready")
          : this._getModuleConsequence("installation", env),
      cls:
        env.user_state === "ready"
          ? "pf-status-ok"
          : "setting-item-description",
    });

    // ── Comprehensive checks ──
    const checks = body.createDiv({ cls: "pf-config" });

    const addCheck = (
      key: string,
      status: string,
      value: string,
      statusClass: string
    ) => {
      const row = checks.createDiv({ cls: "pf-config-row" });
      row.createEl("span", { cls: "pf-config-key", text: key });
      const right = row.createDiv({ cls: "pf-config-right" });
      right.createEl("span", { cls: statusClass, text: status });
      right.createEl("span", { cls: "pf-config-value", text: value });
    };

    // Version
    addCheck(
      t("foundation_version"),
      "✓",
      this.plugin.manifest.version,
      "pf-status-ok"
    );

    // Python check — project the resolved runtime command (managed pointer
    // first, then the explicit override), not a bare settings fallback.
    const vp = (this.app.vault.adapter as any).basePath as string;
    const pythonPath =
      this._resolveRuntimeCommand(vp)?.path ??
      (this.plugin.settings.python_path || "python");
    addCheck(
      t("foundation_python"),
      env.user_state === "ready" ? "✓" : "—",
      pythonPath,
      env.user_state === "ready" ? "pf-status-ok" : "pf-status-checking"
    );

    // Vault structure
    const systemDir = path.join(
      vp,
      this.plugin.settings.system_dir || "System"
    );
    const hasSystem = fs.existsSync(systemDir);
    addCheck(
      t("foundation_vault_structure"),
      hasSystem ? "✓" : "✗",
      hasSystem ? systemDir : t("foundation_vault_missing"),
      hasSystem ? "pf-status-ok" : "pf-status-error"
    );

    // Zotero data dir
    const hasZotero =
      this.plugin.settings.zotero_data_dir &&
      fs.existsSync(this.plugin.settings.zotero_data_dir);
    addCheck(
      t("foundation_zotero"),
      hasZotero ? "✓" : "✗",
      hasZotero
        ? this.plugin.settings.zotero_data_dir
        : t("foundation_zotero_missing"),
      hasZotero ? "pf-status-ok" : "pf-status-error"
    );

    // API keys — check SecretStorage configured flags, not raw key values
    const hasPaddle = !!this.plugin.settings._paddleocr_configured;
    // #173/C1: presence comes from the credential authority (auth status);
    // process-env checks in the browser are gone.
    const hasOpenai = !!this.plugin.settings._vector_db_configured;
    addCheck(
      t("foundation_paddle_key"),
      hasPaddle ? "✓" : "✗",
      hasPaddle ? t("config_configured") : t("foundation_paddle_missing"),
      hasPaddle ? "pf-status-ok" : "pf-status-error"
    );
    addCheck(
      t("foundation_openai_key"),
      hasOpenai ? "✓" : "✗",
      hasOpenai ? t("config_configured") : t("foundation_openai_missing"),
      hasOpenai ? "pf-status-ok" : "pf-status-error"
    );

    // #173 corrective: explicit SecretStorage → keyring migration bridge.
    // User-mediated, one-time; runtime never reads SecretStorage.
    const migrateRow = checks.createDiv({ cls: "pf-config-row" });
    migrateRow.createEl("span", {
      cls: "pf-config-key",
      text: t("md_foundation_legacy_migrate") ?? "Migrate legacy credentials",
    });
    const migrateRight = migrateRow.createDiv({ cls: "pf-config-right" });
    const migrateBtn = migrateRight.createEl("button", {
      cls: "paperforge-refresh-btn",
      text: "Migrate",
    });
    migrateBtn.title =
      "One-time migration of Obsidian SecretStorage values into the keyring (auth set)";
    migrateBtn.onclick = () => this._migrateLegacyCredentials(migrateBtn);

    // Obsidian version check removed (RC UX Seam): the previous block
    // hardcoded `obsidianOk = true` — a false green. Obsidian compatibility
    // is enforced by the manifest's minAppVersion at plugin load; Python-side
    // truth lives in the probe envelope, not a presentation-side constant.

    // Python packages: projected from the probe envelope — the backend owns
    // dependency truth (probe memory / embed status deps_installed).  The
    // retired `import openai; import sqlite3` exec check ran against
    // settings.python_path instead of the managed runtime and duplicated
    // backend authority, so it is gone.
    addCheck(
      t("foundation_python_packages"),
      env.user_state === "ready" ? "✓" : "—",
      env.user_state === "ready"
        ? t("check_bbt_ok") || "Ready"
        : (env.reason?.text ?? "—"),
      env.user_state === "ready" ? "pf-status-ok" : "pf-status-checking"
    );

    // Action buttons
    if (env.user_state !== "ready") {
      new Setting(body)
        .setName(t("foundation_setup"))
        .setDesc(t("foundation_setup_desc"))
        .addButton((btn) =>
          btn
            .setButtonText(t("foundation_setup_btn"))
            .setCta()
            .onClick(() => this._startSetupJourney(1))
        );
    }

    // Reinstall button - triggers full setup wizard
    new Setting(body)
      .setName(t("foundation_reinstall"))
      .setDesc(t("foundation_reinstall_desc"))
      .addButton((btn) =>
        btn
          .setButtonText(t("foundation_reinstall_btn"))
          .setWarning()
          .onClick(() => this._startSetupJourney(1, true))
      );
  }

  /** Render the Skills inventory for the selected agent platform. */
  private _renderSkillsList(containerEl: HTMLElement): void {
    const agentDirs: Record<string, string> = {
      opencode: ".opencode/skills",
      claude: ".claude/skills",
      codex: ".codex/skills",
      cursor: ".cursor/skills",
      windsurf: ".windsurf/skills",
      github_copilot: ".github/skills",
      gemini: ".gemini/skills",
    };
    const vaultPath = this._getVaultBasePath();
    const selectedPlatform: string =
      this.plugin.settings.agent_platform || "opencode";

    // Skills section
    containerEl.createEl("h3", { text: t("md_agent_skills") });
    const skillsDescEl = containerEl.createEl("div", {
      cls: "paperforge-desc-box",
    });
    skillsDescEl.setText(t("feat_skills_desc"));
    skillsDescEl.createEl("br");
    skillsDescEl.createEl("span", { text: t("feat_skills_system") });

    // Show skills for selected platform
    const skillDir = path.join(vaultPath, agentDirs[selectedPlatform]);
    interface SkillEntry {
      name: string;
      desc: string;
      source: string;
      disabled: boolean;
      version: string;
      path: string;
      content: string;
      dirName: string;
    }
    const systemSkills: SkillEntry[] = [];
    const userSkills: SkillEntry[] = [];

    if (fs.existsSync(skillDir)) {
      fs.readdirSync(skillDir, { withFileTypes: true }).forEach((entry) => {
        if (!entry.isDirectory()) return;
        const skillFile = path.join(skillDir, entry.name, "SKILL.md");
        if (!fs.existsSync(skillFile)) return;
        const content = fs.readFileSync(skillFile, "utf-8");
        const nameMatch = content.match(/^name:\s*(.+)$/m);
        const lines = content.split("\n");
        const descIdx = lines.findIndex((l) => /^description:/.test(l));
        let desc = "";
        if (descIdx >= 0) {
          const first = lines[descIdx].match(/^description:\s*(.+)$/);
          if (
            first &&
            first[1] &&
            first[1] !== ">" &&
            first[1] !== "|-" &&
            first[1] !== "|"
          ) {
            desc = first[1].trim();
          } else {
            for (let i = descIdx + 1; i < lines.length; i++) {
              if (/^\s{2,}/.test(lines[i]) || lines[i].trim() === "") {
                desc += lines[i].trim() + " ";
              } else break;
            }
            desc = desc.trim();
          }
        }
        const sourceMatch = content.match(/^source:\s*(.+)$/m);
        const disableMatch = content.match(
          /^disable-model-invocation:\s*(.+)$/m
        );
        const versionMatch = content.match(/^version:\s*(.+)$/m);
        const skill: SkillEntry = {
          name: nameMatch ? nameMatch[1].trim() : entry.name,
          desc,
          source: sourceMatch ? sourceMatch[1].trim() : "user",
          disabled: !!disableMatch && disableMatch[1].trim() === "true",
          version: versionMatch ? versionMatch[1].trim() : "",
          path: skillFile,
          content,
          dirName: entry.name,
        };
        if (skill.source === "paperforge") {
          systemSkills.push(skill);
        } else {
          userSkills.push(skill);
        }
      });
    }

    const skillsBox = containerEl.createEl("div", {
      cls: "paperforge-skills-box",
    });

    const renderCollapsibleSkills = (
      label: string,
      skills: SkillEntry[],
      isSystem: boolean
    ): void => {
      if (skills.length === 0) return;
      const group = skillsBox.createEl("div", {
        cls: "paperforge-skills-group",
      });
      const header = group.createEl("div", {
        cls: "paperforge-skills-collapse-header",
      });
      const content = group.createEl("div", {
        cls: "paperforge-skills-collapse-content",
      });
      const arrow = header.createEl("span", {
        text: "\u25BC",
        cls: "paperforge-skills-arrow",
      });
      header.createEl("h4", {
        text: `${label} (${skills.length})`,
        cls: "paperforge-skills-subheader",
      });
      skills.forEach((s: SkillEntry) => {
        const nameText = s.name + (s.version ? " v" + s.version : "");
        const sourceLabel = isSystem
          ? " [" + t("skills_system") + "]"
          : " [" + t("skills_user") + "]";
        const descText = s.desc || "";
        const setting = new Setting(content)
          .setName(nameText + sourceLabel)
          .setDesc(descText);
        setting.settingEl.style.opacity = s.disabled ? "0.4" : "1";
        setting.addToggle((toggle) => {
          toggle.setValue(!s.disabled).onChange((value) => {
            const newDisabled = !value;
            const disableMatch = s.content.match(
              /^disable-model-invocation:\s*(.+)$/m
            );
            const newContent = disableMatch
              ? s.content.replace(
                  /^disable-model-invocation:\s*.+$/m,
                  `disable-model-invocation: ${newDisabled}`
                )
              : s.content.replace(
                  /^(---\r?\n)/,
                  `$1disable-model-invocation: ${newDisabled}\n`
                );
            fs.writeFileSync(s.path, newContent, "utf-8");
            s.disabled = newDisabled;
            s.content = newContent;
            setting.settingEl.style.opacity = s.disabled ? "0.4" : "1";
          });
        });
      });
      const stateKey = isSystem ? "system" : "user";
      const collapsed = this._skillsCollapsed[stateKey] || false;
      if (collapsed) {
        content.style.display = "none";
        arrow.style.transform = "rotate(-90deg)";
      }
      header.addEventListener("click", () => {
        const nowCollapsed = content.style.display !== "none";
        if (nowCollapsed) {
          content.style.display = "none";
          arrow.style.transform = "rotate(-90deg)";
        } else {
          content.style.display = "";
          arrow.style.transform = "rotate(0deg)";
        }
        this._skillsCollapsed[stateKey] = content.style.display === "none";
      });
    };

    renderCollapsibleSkills(t("skills_system"), systemSkills, true);
    renderCollapsibleSkills(t("skills_user"), userSkills, false);

    if (systemSkills.length === 0 && userSkills.length === 0) {
      skillsBox.createEl("p", {
        text: t("skills_empty"),
        cls: "setting-item-description",
      });
    }
  }

  /** Render the Module Detail tab (top-level destination). */
  _renderModuleDetailTab(containerEl: HTMLElement): void {
    // Default to Installation if no module selected
    if (!this._selectedDetailModule) {
      this._selectedDetailModule = "installation";
    }
    if (this._selectedDetailModule === "installation") {
      this._renderInstallationDetail(containerEl);
    } else if (this._selectedDetailModule === "library") {
      this._renderLibraryDetail(containerEl);
    } else if (this._selectedDetailModule === "ocr") {
      this._renderOcrDetail(containerEl);
    } else if (this._selectedDetailModule === "memory") {
      this._renderMemoryDetail(containerEl);
    } else if (this._selectedDetailModule === "agent") {
      this._renderAgentDetail(containerEl);
    } else {
      // Fallback to installation
      this._selectedDetailModule = "installation";
      this._renderInstallationDetail(containerEl);
    }
  }

  /** #88: Library module workbench. */
  _renderLibraryDetail(containerEl: HTMLElement): void {
    this._renderModuleDetailShell(containerEl, "library");
    const env =
      this._capabilityState?.library ?? createUnknownEnvelope("library");
    const body = containerEl.createDiv({ cls: "pf-module-body" });
    body.createEl("h3", { text: t("md_library_connection") });
    if (env.user_state === "ready") {
      body.createEl("p", {
        text: t("md_library_ready"),
        cls: "pf-status-ok",
      });
    } else if (
      env.user_state !== "checking" &&
      env.user_state !== "not_enabled"
    ) {
      renderErrorAnatomy(body, {
        whatHappened:
          t("cc_module_library") +
          " — " +
          this._getUserStateLabel(env.user_state),
        impact: t("library_problem_impact"),
        nextStep: t("problem_use_action"),
        impactLabel: t("problem_impact"),
        nextLabel: t("problem_next"),
        copyLabel: t("problem_copy"),
        onCopyDiagnostic: () => this._buildAndCopyDiagnostic(),
      });
    }

    const facts = body.createDiv({ cls: "pf-module-facts" });
    const corpus = facts.createDiv({ cls: "pf-module-fact" });
    corpus.createEl("span", { text: t("md_library_corpus") });
    corpus.createEl("span", { text: t("metric_after_sync") });
    const lastSync = facts.createDiv({ cls: "pf-module-fact" });
    lastSync.createEl("span", { text: t("md_library_last_sync") });
    lastSync.createEl("span", {
      text: this.plugin._lastSyncTime || t("metric_not_available"),
    });

    body.createEl("h3", { text: t("md_configuration") });
    renderConfigurationSummary(body, {
      items: [
        {
          label: t("config_zotero_dir"),
          value:
            this.plugin.settings.zotero_data_dir || t("config_not_configured"),
        },
      ],
      configuredLabel: t("config_configured"),
      notConfiguredLabel: t("config_not_configured"),
      onChangeLabel: t("config_change"),
      onChange: () => this._startSetupJourney(2),
    });
  }

  /** Render the OCR detail view (Issue #96: 3-state UX). */
  _renderOcrDetail(containerEl: HTMLElement): void {
    this._renderModuleDetailShell(containerEl, "ocr");
    const env = this._capabilityState?.ocr ?? createUnknownEnvelope("ocr");
    const body = containerEl.createDiv({ cls: "pf-module-body" });
    body.createEl("h3", { text: t("md_ocr_status") });
    if (env.user_state === "detection_failed") {
      body.createEl("p", {
        cls: "pf-status-checking",
        text: t("md_status_refresh_hint"),
      });
    }

    const pipelineVersion = env.pipeline_version;
    const lastPipelineVersion = env.last_pipeline_version;
    const staleCount = env.pipeline_version_summary?.stale ?? 0;
    const updateAvailable = staleCount > 0;
    const isRunning = env.activity_state === "running";

    if (isRunning) {
      // ── State: Running ──
      renderStatusBadge(body, "checking", t("ocr_state_running"));
      const progress = this.plugin._ocrProgress;
      const card = body.createDiv({ cls: "pf-ocr-progress-card" });
      if (progress?.total) {
        const label = t("ocr_progress")
          .replace("{current}", String(progress.current))
          .replace("{total}", String(progress.total));
        const scope = progress.key ? " \u2014 " + progress.key : "";
        card.createEl("span", {
          cls: "pf-detail-progress",
          text: t("ocr_state_running") + " " + label + scope,
        });
        const bar = card.createDiv({ cls: "pf-activity-bar" });
        const pct = Math.round((progress.current / progress.total) * 100);
        bar.createDiv({
          cls: "pf-activity-bar-fill",
          attr: {
            style: `width: ${pct}%`,
            role: "progressbar",
            "aria-valuenow": String(progress.current),
            "aria-valuemin": "1",
            "aria-valuemax": String(progress.total),
          },
        });
      }
      const controller = this.plugin.ocrProcessController;
      if (controller.isRunning) {
        const stop = card.createEl("button", {
          cls: "pf-action-btn mod-warning",
          text: t("ocr_stop_batch"),
        });
        stop.addEventListener("click", () => void controller.stop());
      }
    } else if (updateAvailable) {
      // ── State: Update Available ──
      const versionLabel = pipelineVersion
        ? t("ocr_state_update_available").replace("{version}", pipelineVersion)
        : t("ocr_state_update_available").replace("{version}", "");
      renderStatusBadge(body, "action_required", versionLabel);
      body.createEl("p", {
        text: t("ocr_state_update_description"),
        cls: "setting-item-description",
      });
      body.createEl("p", {
        text: t("ocr_state_update_safety"),
        cls: "setting-item-description",
      });
      // Primary action with confirmation modal
      const reExtractBtn = body.createEl("button", {
        cls: "pf-action-btn mod-warning",
        text: t("ocr_action_re_extract"),
      });
      reExtractBtn.addEventListener("click", () => {
        new PaperForgeConfirmModal(
          this.app,
          {
            title: t("ocr_modal_title"),
            effectLabel:
              t("ocr_modal_description") + " " + t("ocr_state_update_safety"),
            confirmLabel: t("ocr_action_re_extract"),
            cancelLabel: t("maintenance_confirm_cancel"),
          },
          () => this._dispatchOcrAction("rebuild")
        ).open();
      });
    } else if (env.user_state === "ready") {
      // ── State: Ready ──
      renderStatusBadge(body, "ready", t("cc_state_ready"));
      const readyText = pipelineVersion
        ? t("ocr_state_ready")
            .replace(
              "{count}",
              String(
                env.action?.primary?.scope_count ??
                  (env.pipeline_version_summary as any)?.total ??
                  ""
              )
            )
            .replace("{version}", pipelineVersion)
        : t("ocr_state_ready_no_version").replace(
            "{count}",
            String(
              env.action?.primary?.scope_count ??
                (env.pipeline_version_summary as any)?.total ??
                ""
            )
          );
      body.createEl("p", { text: readyText, cls: "pf-status-ok" });
      // Open OCR Workspace (secondary action)
      renderActionButton(body, {
        label: t("md_ocr_workspace"),
        onClick: () =>
          (this.app as any).workspace.getLeaf().setViewState({
            type: "paperforge-ocr-workspace",
          } as any),
      });
      // Update banner (secondary notice when a newer pipeline is available)
      if (
        pipelineVersion &&
        lastPipelineVersion &&
        pipelineVersion !== lastPipelineVersion
      ) {
        const banner = body.createDiv({ cls: "pf-ocr-update-banner" });
        banner.createEl("span", {
          text: t("ocr_state_update_available").replace(
            "{version}",
            pipelineVersion
          ),
        });
      }
    }
    if (!isRunning) {
      renderActionButton(body, {
        label: t("ocr_configure_credential"),
        onClick: () => this._startSetupJourney(3),
      });
    }
  }
  /** Render the Memory detail view (Issue #78). */
  _renderAgentDetail(containerEl: HTMLElement): void {
    this._renderModuleDetailShell(containerEl, "agent");
    const body = containerEl.createDiv({ cls: "pf-module-body" });

    const platforms: Record<string, string> = {
      opencode: "OpenCode",
      claude: "Claude Code",
      codex: "Codex",
      cursor: "Cursor",
      windsurf: "Windsurf",
      github_copilot: "GitHub Copilot",
      gemini: "Gemini CLI",
    };
    const directories: Record<string, string> = {
      opencode: ".opencode/skills",
      claude: ".claude/skills",
      codex: ".codex/skills",
      cursor: ".cursor/skills",
      windsurf: ".windsurf/skills",
      github_copilot: ".github/skills",
      gemini: ".gemini/skills",
    };
    const current = this.plugin.settings.agent_platform || "opencode";
    const skillDirectory = path.join(
      this._getVaultBasePath(),
      directories[current]
    );
    const deployed = fs.existsSync(skillDirectory);

    const facts = body.createDiv({ cls: "pf-module-facts" });
    const platform = facts.createDiv({ cls: "pf-module-fact" });
    platform.createEl("span", { text: t("md_agent_platform") });
    platform.createEl("span", { text: platforms[current] ?? current });
    const deployment = facts.createDiv({ cls: "pf-module-fact" });
    deployment.createEl("span", { text: t("md_agent_deployment") });
    deployment.createEl("span", {
      text: deployed ? t("agent_deployed") : t("agent_not_deployed"),
    });
    const connection = facts.createDiv({ cls: "pf-module-fact" });
    connection.createEl("span", { text: t("agent_live_connection") });
    connection.createEl("span", { text: t("md_agent_connection_unknown") });

    if (this._agentPlatformDraft === null) {
      renderActionButton(body, {
        label: t("config_change"),
        onClick: () => {
          this._agentPlatformDraft = current;
          this.display();
        },
      });
    } else {
      const editor = body.createDiv({ cls: "pf-agent-config-editor" });
      const select = editor.createEl("select", {
        attr: { "aria-label": t("md_agent_platform") },
      });
      // #142: choices come from Python's config list when hydrated; the
      // hardcoded map is a presentation label lookup only.
      const editorChoices = this.plugin.agentPlatformChoices.length
        ? this.plugin.agentPlatformChoices
        : Object.keys(platforms);
      for (const value of editorChoices) {
        const option = select.createEl("option", {
          text: platforms[value] ?? value,
          attr: { value },
        }) as HTMLOptionElement;
        option.selected = value === this._agentPlatformDraft;
      }
      select.addEventListener("change", () => {
        this._agentPlatformDraft = select.value;
      });
      const actions = editor.createDiv({ cls: "pf-agent-config-actions" });
      renderActionButton(actions, {
        label: t("config_save"),
        onClick: () => {
          const value = this._agentPlatformDraft ?? current;
          this.plugin.settings.agent_platform = value;
          // #142 / C0: mutation through the typed config command.
          void configSet(
            this._getVaultBasePath(),
            "agent_platform",
            value,
            this.plugin.settings
          ).catch(
            (e) =>
              new Notice(
                `PaperForge: config set agent_platform failed: ${String(e)}`
              )
          );
          this.plugin.saveSettings();
          this._agentPlatformDraft = null;
          this.display();
        },
      });
      renderActionButton(actions, {
        label: t("config_cancel"),
        onClick: () => {
          this._agentPlatformDraft = null;
          this.display();
        },
      });
      renderActionButton(actions, {
        label: t("config_verify"),
        onClick: () => {
          const value = this._agentPlatformDraft ?? current;
          const found = fs.existsSync(
            path.join(this._getVaultBasePath(), directories[value])
          );
          new Notice(
            found ? t("agent_verify_found") : t("agent_verify_missing")
          );
        },
      });
    }

    this._renderSkillsList(body);
  }

  /** Render the Memory detail view matching prototype layout. */
  _renderMemoryDetail(containerEl: HTMLElement): void {
    this._renderModuleDetailShell(containerEl, "memory", false);
    const env =
      this._capabilityState?.memory ?? createUnknownEnvelope("memory");
    const body = containerEl.createDiv({ cls: "pf-module-body" });
    const reasonCode = env.reason?.code ?? "";
    const embedController = this.plugin._embedController;
    const isRunning =
      env.activity_state === "running" || Boolean(embedController?.busy);
    const liveFailure =
      embedController?.state === "failed" ? embedController.warning : null;

    // The shared summary owns persistent state. The controller owns the
    // current attempt, so its running/error truth takes precedence.
    let statusText: string | null = null;
    let statusClass = "setting-item-description";
    if (isRunning) {
      statusText = env.activity_label ?? t("cc_activity_running");
      statusClass = "pf-status-ok";
    } else if (liveFailure) {
      statusText = `${t("retrieval_build_failed")}: ${liveFailure}`;
      statusClass = "pf-status-error";
    } else if (reasonCode === "memory.disabled") {
      statusText = t("sr_state_disabled");
    } else if (reasonCode === "memory.db_missing") {
      statusText = t("sr_state_db_missing");
    } else if (reasonCode === "memory.backend_upgrade_available") {
      statusText = t("sr_state_upgrade_available");
    } else if (reasonCode === "memory.vector_build_failed") {
      statusText = t("sr_state_build_failed");
    } else if (reasonCode === "memory.schema_stale") {
      statusText = env.reason.text;
    } else if (env.user_state === "ready") {
      statusText = t("md_retrieval_ready");
      statusClass = "pf-status-ok";
    }
    if (statusText) {
      body.createEl("p", { text: statusText, cls: statusClass });
    }

    // ── Primary action button ──
    if (isRunning && embedController) {
      renderActionButton(body, {
        label: t("retrieval_stop"),
        onClick: () => void embedController.stop(),
      });
    } else if (liveFailure) {
      renderActionButton(body, {
        label: t("retrieval_retry"),
        onClick: () => this._dispatchModuleAction("memory", env),
      });
    } else if (reasonCode === "memory.disabled") {
      renderActionButton(body, {
        label: t("sr_action_enable") || "Enable Smart Retrieval",
        onClick: () => {
          if (!this.plugin.settings.features) {
            this.plugin.settings.features = {
              memory_layer: true,
              vector_db: false,
            };
          }
          this.plugin.settings.features.vector_db = true;
          this.plugin.saveSettings().then(() => this._refreshAllReadModels());
        },
      });
    } else if (
      reasonCode === "memory.db_missing" ||
      reasonCode === "memory.index_stale"
    ) {
      renderActionButton(body, {
        label: t("sr_action_build") || "Build Index",
        onClick: () => this._dispatchModuleAction("memory", env),
      });
    } else if (reasonCode === "memory.backend_upgrade_available") {
      renderActionButton(body, {
        label: t("sr_action_upgrade") || "Upgrade",
        onClick: () => this._dispatchModuleAction("memory", env),
      });
    } else if (
      reasonCode === "memory.vector_build_failed" ||
      reasonCode === "memory.vector_build_interrupted"
    ) {
      renderActionButton(body, {
        label: t("cc_action_rebuild_derived") || "Rebuild Index",
        onClick: () => this._dispatchModuleAction("memory", env),
      });
    } else if (
      env.action?.primary &&
      env.user_state !== "ready" &&
      env.user_state !== "not_enabled"
    ) {
      const actionKey =
        "action_" +
        (env.action.primary.action_id ?? env.action.primary.verb).replace(
          /[.-]/g,
          "_"
        );
      const actionLabel =
        t(actionKey) !== actionKey
          ? t(actionKey)
          : t("cc_action_" + env.action.primary.verb) !==
              "cc_action_" + env.action.primary.verb
            ? t("cc_action_" + env.action.primary.verb)
            : t("cc_action_probe");
      renderActionButton(body, {
        label: actionLabel,
        onClick: () => this._dispatchModuleAction("memory", env),
      });
    }

    // ── Info card (read-only status) ──
    const dbStatus =
      env.user_state === "ready"
        ? t("sr_db_exists") || "Active"
        : t("sr_db_missing") || "Not built";
    const backend = "vec0";
    const apiKeyConfigured =
      this.plugin.settings._vector_db_configured || false;
    const apiKeyStatus = apiKeyConfigured
      ? t("api_key_set") || "Configured"
      : t("api_key_missing") || "Not configured";

    const infoCard = body.createDiv({ cls: "pf-sr-info-card" });
    const rows: [string, string][] = [
      [t("sr_db_status") || "Database", dbStatus],
      [t("sr_backend") || "Backend", backend],
      [t("sr_api_key") || "API Key", apiKeyStatus],
    ];
    for (const [label, value] of rows) {
      const row = infoCard.createDiv({ cls: "pf-sr-info-row" });
      row.createEl("span", { cls: "pf-sr-info-label", text: label });
      row.createEl("span", { cls: "pf-sr-info-value", text: value });
    }

    // ── Configuration (single collapsible section) ──
    const cfgOpen = !apiKeyConfigured;
    const cfgSection = body.createDiv({ cls: "pf-sr-cfg" });
    const cfgHead = cfgSection.createDiv({ cls: "pf-sr-cfg-head" });
    cfgHead.createEl("span", {
      cls: "pf-sr-cfg-title",
      text: t("sr_config_label") || "\u914d\u7f6e",
    });
    const cfgIcon = cfgHead.createEl("span", {
      cls: "pf-sr-cfg-icon",
      text: cfgOpen ? "\u25bc" : "\u25b6",
    });
    const cfgBody = cfgSection.createDiv({ cls: "pf-sr-cfg-body" });
    cfgBody.style.display = cfgOpen ? "" : "none";
    cfgHead.addEventListener("click", () => {
      const open = cfgBody.style.display !== "none";
      cfgBody.style.display = open ? "none" : "";
      cfgIcon.textContent = open ? "\u25b6" : "\u25bc";
    });

    // API Key
    const kr = cfgBody.createDiv({ cls: "pf-sr-cfg-row" });
    kr.createEl("label", {
      text: t("feat_openai_key") || "API Key",
      cls: "pf-sr-cfg-lbl",
    });
    const ki = kr.createEl("input", {
      cls: "pf-sr-cfg-input",
      attr: {
        type: "password",
        placeholder: apiKeyConfigured ? "\u2022\u2022\u2022\u2022" : "sk-...",
      },
    }) as HTMLInputElement;
    let kt: ReturnType<typeof setTimeout> | null = null;
    ki.addEventListener("input", () => {
      const v = ki.value;
      if (!v) return;
      if (kt) clearTimeout(kt);
      kt = setTimeout(async () => {
        if (await this._storeVectorDbCredential(v)) {
          ki.value = "";
          ki.placeholder = "\u2022\u2022\u2022\u2022";
          cfgBody.style.display = "none";
          cfgIcon.textContent = "\u25b6";
        }
        kt = null;
      }, 600);
    });

    // Base URL
    const br = cfgBody.createDiv({ cls: "pf-sr-cfg-row" });
    br.createEl("label", {
      text: t("feat_api_base_url") || "API Base URL",
      cls: "pf-sr-cfg-lbl",
    });
    const bi = br.createEl("input", {
      cls: "pf-sr-cfg-input",
      attr: { type: "text", placeholder: "https://api.openai.com/v1" },
    }) as HTMLInputElement;
    bi.value = this.plugin.settings.vector_db_api_base || "";
    bi.addEventListener("change", () => {
      this.plugin.settings.vector_db_api_base = bi.value;
      void configSet(
        this._getVaultBasePath(),
        "vector_db_api_base",
        bi.value,
        this.plugin.settings
      ).catch(
        (e) =>
          new Notice(
            `PaperForge: config set vector_db_api_base failed: ${String(e)}`
          )
      );
      this._refreshVectorDbCredentialStatus();
    });

    // Model
    const mr = cfgBody.createDiv({ cls: "pf-sr-cfg-row" });
    mr.createEl("label", {
      text: t("feat_api_model") || "Model",
      cls: "pf-sr-cfg-lbl",
    });
    const mi = mr.createEl("input", {
      cls: "pf-sr-cfg-input",
      attr: { type: "text", placeholder: "text-embedding-3-small" },
    }) as HTMLInputElement;
    mi.value =
      this.plugin.settings.vector_db_api_model || "text-embedding-3-small";
    mi.addEventListener("change", () => {
      this.plugin.settings.vector_db_api_model = mi.value;
      void configSet(
        this._getVaultBasePath(),
        "vector_db_api_model",
        mi.value,
        this.plugin.settings
      ).catch(
        (e) =>
          new Notice(
            `PaperForge: config set vector_db_api_model failed: ${String(e)}`
          )
      );
      this._refreshVectorDbCredentialStatus();
    });

    // ── Impact box (when action needed) ──
    if (
      env.capability_state === "needs_action" &&
      reasonCode !== "memory.disabled"
    ) {
      const impact = body.createDiv({ cls: "pf-sr-impact-box" });
      impact.createEl("strong", {
        text: t("cc_badge_action_required") || "Action Required",
      });
      impact.createEl("p", {
        text:
          reasonCode === "memory.db_missing" ||
          reasonCode === "memory.index_stale"
            ? t("sr_impact_db_missing") ||
              "Smart Retrieval needs an OpenAI API key and vector index. Click Build Index to get started."
            : reasonCode === "memory.backend_upgrade_available"
              ? t("sr_impact_upgrade") ||
                "A new vector backend is available. Upgrade to improve search quality."
              : reasonCode === "memory.vector_build_failed"
                ? t("sr_impact_build_failed") ||
                  "The last build failed. Check your API key and try again."
                : t("sr_impact_schema_stale") ||
                  "The vector schema is outdated. Rebuild to match the current library.",
      });
    }
    // ── Advanced Status (collapsible, detailed diagnostics) ──
    const details = body.createEl("details", { cls: "pf-sr-diagnostics" });
    details.createEl("summary", {
      text: t("cc_diagnostic_toggle") || "Advanced Status",
    });
    const diagBody = details.createDiv({ cls: "pf-sr-diagnostics-body" });

    const vp = this._getVaultBasePath();
    const baseUrl = this.plugin.settings.vector_db_api_base || "-";

    const tbl = diagBody.createEl("table", { cls: "pf-diag-table" });
    const diagRows = new Map<string, HTMLTableRowElement>();
    const setRow = (label: string, value: string) => {
      if (!diagRows.has(label)) {
        const tr = tbl.createEl("tr");
        tr.createEl("td", { cls: "pf-diag-label", text: label });
        const vd = tr.createEl("td", { cls: "pf-diag-value" });
        diagRows.set(label, tr);
        vd.textContent = value;
        return;
      }
      const vd = diagRows.get(label)!.children[1] as HTMLTableCellElement;
      vd.textContent = value;
    };

    setRow("FTS5 Papers", "…");
    setRow("FTS5 Fresh", "…");
    setRow("Needs Rebuild", "…");
    setRow("", ""); // spacer
    setRow("Vector Backend", "vec0 (sqlite-vec)");
    setRow("Vector Model", "…");
    setRow("Vector Mode", "…");
    setRow("Vector Dimension", "…");
    setRow("Base URL", baseUrl);
    // #161/R: detail rows come from the typed read-model queries — the
    // plugin never reads snapshot files.
    if (vp) {
      void queryMemoryDetail(vp, this.plugin.settings)
        .then((d) => {
          setRow("FTS5 Papers", String(d?.paper_count_db ?? "?"));
          setRow("FTS5 Fresh", d?.fresh ? "Yes" : "Stale");
          setRow("Needs Rebuild", d?.needs_rebuild ? "Yes" : "No");
        })
        .catch(() => undefined);
      void queryEmbedStatus(vp, this.plugin.settings)
        .then((d) => {
          setRow("Vector Model", String(d?.model ?? "-"));
          setRow("Vector Mode", String(d?.mode ?? "-"));
          setRow("Body Chunks", String(d?.body_chunk_count ?? 0));
          setRow("Object Chunks", String(d?.object_chunk_count ?? 0));
          setRow("Total Chunks", String(d?.total_chunks ?? 0));
          const bs = d?.build_state ?? undefined;
          setRow("Build Status", String(bs?.status ?? "-"));
          setRow("Build Progress", `${bs?.current ?? "?"}/${bs?.total ?? "?"}`);
        })
        .catch(() => undefined);
    }
    setRow("", ""); // spacer
    setRow("Capability State", env.capability_state);
    setRow("Severity", env.severity);
    setRow("Reason Code", reasonCode);
  }
  /** Dispatch a backend action command through exact (verb, command) allowlist (Issue #78). */
  _dispatchModuleAction(mod: CapabilityModule, env: ProbeEnvelope): void {
    const primary = env.action?.primary;
    if (!primary) {
      this._probeModule(mod);
      return;
    }

    // Destructive confirmation -> accessible modal (Issue #80)
    // Policy comes from Python; this switch only localizes presentation for
    // the two remote media actions.
    if (primary.safety_class !== "safe" && primary.confirmation_required) {
      const title =
        primary.action_id === "ocr.run"
          ? t("ocr_run_confirm_title")
          : primary.action_id === "embed.build"
            ? t("embed_rebuild_title")
            : primary.label;
      const effectLabel =
        primary.action_id === "ocr.run"
          ? t("ocr_run_confirm_body")
          : primary.action_id === "embed.build"
            ? t("embed_rebuild_body")
            : (((primary.replacement_facts || []).join("; ") ||
                primary.confirmation_prompt) ??
              t("confirmation_default_effect"));
      new PaperForgeConfirmModal(this.app, { title, effectLabel }, () =>
        this._runAllowedDispatch(mod, primary, env)
      ).open();
      return;
    }

    this._runAllowedDispatch(mod, primary, env);
  }

  private _runAllowedDispatch(
    mod: CapabilityModule,
    primary: ActionPrimary,
    env: ProbeEnvelope
  ): void {
    // T8 (#169): dispatch is TYPED by action_id/verb — the backend
    // `command` string is retired; no (verb, command) table exists.
    const verb = primary.verb;
    const actionId = primary.action_id;

    if (verb === "setup" || verb === "set_config") {
      if (mod === "library") {
        this._startSetupJourney(2);
      } else {
        const reinstall =
          mod === "installation" &&
          env.reason.code === "installation.version_mismatch";
        this._startSetupJourney(
          mod === "ocr" || mod === "memory" ? 3 : 1,
          reinstall
        );
      }
      return;
    }

    if (verb === "probe") {
      this._probeModule(mod);
      return;
    }

    if (verb === "update") {
      if (actionId === "foundation.update") {
        // Registered remote action (#174) — the confirm modal already ran
        // (safety_class destructive + confirmation_required).  Dispatch
        // through the action runner so Python policy stays the authority.
        this._runUpdateAction();
        return;
      }
      // foundation.update_python: interpreter upgrade has NO automated path.
      new Notice(
        t("update_python_manual") ||
          "Python 3.11+ upgrade requires a manual install (python.org or your package manager)."
      );
      this._probeModule(mod);
      return;
    }

    if (verb === "install" && actionId === "memory.install_vector_deps") {
      // Smart Retrieval deps missing -> setup journey re-ensures
      // paperforge[vector] in the runtime (ensure_runtime_dependencies).
      this._startSetupJourney(3);
      return;
    }

    if (mod === "library") {
      if (verb === "sync" || actionId === "library.sync") {
        this._runManualSync();
        return;
      }
    } else if (mod === "ocr") {
      if (verb === "run" || actionId === "ocr.run") {
        this._dispatchOcrAction("run");
        return;
      }
      if (verb === "rebuild_derived" || actionId === "ocr.rebuild_derived") {
        this._dispatchOcrAction("rebuild");
        return;
      }
      if (verb === "redo" || actionId === "ocr.redo") {
        this._dispatchOcrAction("redo");
        return;
      }
      if (verb === "investigate") {
        const vp = this._getVaultBasePath();
        const draft = buildRedactedDraft(
          env.reason.code,
          env.reason.text,
          env.action?.primary?.scope_count ?? 0,
          vp
        );
        new PaperForgeIssueDraftModal(
          this.app,
          draft,
          "https://github.com/LLLin000/PaperForge/issues/new"
        ).open();
        return;
      }
    } else if (mod === "memory") {
      if (verb === "run" || verb === "rebuild_index") {
        // embed.build (probe: missing/failed vector index) → remote embed
        // rebuild; memory.upgrade_backend → ChromaDB→sqlite-vec migration;
        // memory.build / memory.rebuild → the local memory build.
        if (actionId === "embed.build") {
          this._dispatchMemoryBuild("embed");
        } else if (actionId === "memory.upgrade_backend") {
          this._runBackendMigration();
        } else {
          this._dispatchMemoryBuild("build");
        }
        return;
      }
      if (verb === "restore_backup" || actionId === "memory.restore_backup") {
        this._callPython(["memory", "restore-backup"], {
          timeout: 30000,
          onClose: () => {
            this._refreshAllReadModels();
          },
        });
        return;
      }
    }

    // Unknown pair → Notice + re-probe
    new Notice(
      (t("action_unknown_pair") || "Unknown action: {verb}").replace(
        "{verb}",
        verb
      ),
      5000
    );
    this._probeModule(mod);
  } /** Dispatch OCR action through the shared OcrProcessController (#126 PR B). */
  /** #174 RC: dispatch foundation.update through the action runner.
   * The confirm modal already ran (destructive + confirmation_required);
   * Python's perform_update owns policy + fresh-child verification. */
  _runUpdateAction(): void {
    const vp = this._getVaultBasePath();
    const resolved = this._resolveRuntimeCommand(vp);
    if (!resolved) {
      new Notice(t("retrieval_no_python") || "No Python runtime available");
      return;
    }
    execFile(
      resolved.path,
      [
        ...resolved.args,
        "-m",
        "paperforge",
        "--vault",
        vp,
        "action",
        "run",
        "foundation.update",
        "--confirm",
        "foundation.update",
        "--json",
      ],
      { cwd: vp, timeout: 600000, env: paperforgeEnrichedEnv() },
      (err, _stdout, stderr) => {
        if (err) {
          new Notice(
            t("update_failed") ||
              `Update failed: ${stderr?.trim() || err.message}`
          );
        } else {
          new Notice(t("update_done") || "PaperForge updated");
        }
        this._refreshAllReadModels();
      }
    );
  }

  /** #174 RC: ChromaDB -> sqlite-vec backend migration (embed migrate). */
  _runBackendMigration(): void {
    this._callPython(["embed", "migrate", "--json"], {
      timeout: 600000,
      onClose: (code: number, _stdout: string, stderr: string) => {
        if (code === 0) {
          new Notice(t("migrate_done") || "Backend migrated to sqlite-vec");
        } else {
          new Notice(
            t("migrate_failed") ||
              `Backend migration failed: ${stderr?.trim() || "unknown error"}`
          );
        }
        this._refreshAllReadModels();
      },
    });
  }

  _dispatchOcrAction(mode: "run" | "rebuild" | "redo"): void {
    const controller = this.plugin.ocrProcessController;
    if (mode === "run" && typeof this.plugin.requestOcrRun === "function") {
      // The probe-owned confirmation already ran in _dispatchModuleAction.
      this.plugin.requestOcrRun(true);
      return;
    }
    if (controller.isRunning) {
      new Notice(t("ocr_already_running"));
      return;
    }

    const labelMap: Record<string, string> = {
      run: t("ocr_activity_run"),
      rebuild: t("ocr_activity_rebuild"),
      redo: t("ocr_activity_redo"),
    };

    // Set envelope activity overlay without changing capability/severity/reason
    const envelopes = this._capabilityState ?? {};
    if (envelopes["ocr"]) {
      envelopes["ocr"].activity_state = "running";
      envelopes["ocr"].activity_label =
        labelMap[mode] || t("cc_activity_running");
      envelopes["ocr"].activity_progress = { current: 0, total: 1 };
    }
    this.plugin._ocrBuffer = "";
    this.plugin._ocrProgress = { current: 0, total: 1, key: "" };
    this.plugin._ocrStderr = "";
    this.plugin._ocrWasStopped = false;
    this.display();

    const completeNotice: Record<string, string> = {
      run: t("ocr_run_complete"),
      rebuild: t("ocr_rebuild_complete"),
      redo: t("ocr_redo_complete"),
    };

    controller
      .start(mode, {
        all: mode === "rebuild",
        callbacks: {
          onProgress: (current: number, total: number, key: string) => {
            this.plugin._ocrProgress = { current, total, key };
            if (envelopes["ocr"]) {
              envelopes["ocr"].activity_progress = { current, total };
            }
            this.display();
          },
          onNotice: (message: string) => new Notice(message, 8000),
        },
      })
      .then((outcome: OcrProcessOutcome) => {
        if (envelopes["ocr"]) {
          envelopes["ocr"].activity_state = "idle";
          envelopes["ocr"].activity_label = null;
          envelopes["ocr"].activity_progress = null;
        }
        if (outcome.ok) {
          new Notice(completeNotice[mode] || "OCR completed");
        } else if (outcome.stopped) {
          this.plugin._ocrWasStopped = false;
          new Notice(t("ocr_stopped_notice"));
        } else {
          // #126: surface the failing keys instead of claiming success.
          const failed = outcome.failedKeys.join(", ");
          const detail =
            outcome.skippedKeys.length > 0
              ? `${failed ? failed + " " : ""}(${outcome.skippedKeys.length} skipped)`
              : failed;
          new Notice(
            t("ocr_failed_notice") + (detail ? ": " + detail : ""),
            8000
          );
        }
        this._refreshAllReadModels();
        this.display();
      })
      .catch((err: Error) => {
        if (envelopes["ocr"]) {
          envelopes["ocr"].activity_state = "idle";
          envelopes["ocr"].activity_label = null;
          envelopes["ocr"].activity_progress = null;
        }
        new Notice(
          t("ocr_failed_notice") +
            ": " +
            (err?.message || t("ocr_error_notice")),
          8000
        );
        this._refreshAllReadModels();
        this.display();
      });
  } /** Dispatch memory build: distinct build vs embed modes, overlay activity, terminal re-probe (Issue #78). */
  _dispatchMemoryBuild(kind: "build" | "embed"): void {
    const vp = (this.app.vault.adapter as any).basePath as string;
    // Set activity overlay on Memory — the embed branch defers this to the
    // controller's onStateChange so a cancelled confirmation modal never
    // leaves the card stuck on "Building vector index…".
    const envelopes = this._capabilityState ?? {};
    if (kind !== "embed" && envelopes["memory"]) {
      envelopes["memory"].activity_state = "running";
      envelopes["memory"].activity_label = "Building memory…";
    }
    this.display();

    const cliArgs =
      kind === "embed" ? ["embed", "build", "--force"] : ["memory", "build"];

    if (kind === "embed") {
      // #120-fix (P1-2): never stack a second controller while one is
      // mid-flight — the busy getter is per-instance, so the guard lives
      // here, at the only creation site.
      if (this.plugin._embedController?.busy) {
        new Notice(t("embed_already_running"));
        return;
      }
      // #120: embed lifecycle is owned by EmbedBuildController — the old
      // path stored _callPython's null return (async credential branch),
      // making stop / duplicate-start guards / unload cleanup impossible.
      const resolved = this._resolveRuntimeCommand(vp);
      if (!resolved) {
        new Notice(t("retrieval_no_python"));
        this._refreshAllReadModels();
        return;
      }
      const startEmbed = () => {
        // #120-fix: the controller spawns `python pythonArgs embed build`
        // directly — without the module prefix the child would be
        // `python embed ...` (can't open file 'embed'). _resolveRuntimeCommand
        // returns bare `{path, args: []}`, so the full CLI base is built
        // here, matching the runShort invocation below.
        const baseCliArgs = [
          ...resolved.args,
          "-m",
          "paperforge",
          "--vault",
          vp,
        ];
        const controller = new EmbedBuildController({
          vaultPath: vp,
          pythonPath: resolved.path,
          pythonArgs: baseCliArgs,
          resolveEnv: () => buildTargetedEnv(null, "embed"),
          runShort: (args: string[], timeoutMs: number) => {
            const { promise, resolve } = deferred<{
              code: number;
              stdout: string;
              stderr: string;
            }>();
            execFile(
              resolved.path,
              [...resolved.args, "-m", "paperforge", "--vault", vp, ...args],
              { cwd: vp, timeout: timeoutMs, env: paperforgeEnrichedEnv() },
              (err, stdout, stderr) => {
                resolve({
                  code: err ? 1 : 0,
                  stdout: stdout ?? "",
                  stderr: stderr ?? "",
                });
              }
            );
            return promise;
          },
          callbacks: {
            onStateChange: (state, progress, warning, _stopResult) => {
              this.plugin._embedProgress = {
                current: progress.current,
                total: progress.total,
                key: progress.key,
              };
              if (envelopes["memory"]) {
                if (
                  state === "running" ||
                  state === "resolving_credentials" ||
                  state === "stopping"
                ) {
                  envelopes["memory"].activity_state = "running";
                  envelopes["memory"].activity_label =
                    state === "stopping"
                      ? t("embed_activity_stopping")
                      : t("embed_activity_building");
                  envelopes["memory"].activity_progress = {
                    current: progress.current,
                    total: progress.total || 1,
                  };
                } else {
                  envelopes["memory"].activity_state = "idle";
                  envelopes["memory"].activity_label = null;
                  envelopes["memory"].activity_progress = null;
                }
              }
              let terminal = false;
              if (state === "success") {
                terminal = true;
                new Notice(t("embed_build_complete"));
              } else if (state === "success_with_warning") {
                terminal = true;
                new Notice(
                  t("embed_build_warning").replace(
                    "{detail}",
                    warning || t("embed_bookkeeping_incomplete")
                  ),
                  8000
                );
              } else if (state === "failed") {
                terminal = true;
                new Notice(
                  t("sr_build_failed_notice").replace(
                    "{detail}",
                    warning || "exit code ?"
                  ),
                  8000
                );
              } else if (state === "cancelled") {
                terminal = true;
                new Notice(t("embed_build_stopped"), 8000);
              }
              if (terminal) {
                // RC UX Seam P1: mutation settled → invalidate all + probe
                // all. Without this the envelope keeps the pre-build
                // needs_action truth until the next convergence tick, so the
                // card would keep offering "Build" right after a success.
                this._refreshAllReadModels();
              }
              this.display();
            },
          },
        });
        this.plugin._embedController = controller;
        void controller.start("--force");
      };
      startEmbed();
    } else {
      // Memory build: timeout-based (no streaming)
      this._callPython(cliArgs, {
        timeout: 120000,
        onClose: (code: number | null, _stdout: string, stderr: string) => {
          if (envelopes["memory"]) {
            envelopes["memory"].activity_state = "idle";
            envelopes["memory"].activity_label = null;
          }
          if (code === 0) {
            new Notice(t("feat_memory_rebuild_done"));
          } else {
            new Notice(
              t("feat_memory_rebuild_failed") +
                (stderr ? " " + stderr.slice(0, 120) : ""),
              8000
            );
          }
          this._refreshAllReadModels();
          this.display();
        },
      });
    }
  } /** Shared module detail shell for Library, OCR, and Memory (Issue #78). */
  /** Shared module detail shell for all five operational modules. */
  _renderModuleDetailShell(
    containerEl: HTMLElement,
    mod: CapabilityModule | "agent",
    showPrimary = true
  ): void {
    containerEl.classList.add("pf-module-detail");

    const backBtn = containerEl.createEl("button", {
      cls: "pf-back-btn",
      text: t("btn_back_to_overview"),
    });
    backBtn.addEventListener("click", () => {
      if (this._detailReturn) {
        this.activeTab = this._detailReturn.tab;
        this._focusTargetId = this._detailReturn.selector;
        this._detailReturn = null;
      } else {
        this.activeTab = "overview";
        this._focusTargetId = `button.pf-cc-module-card[data-module="${mod}"]`;
      }
      this._selectedDetailModule = "";
      this.display();
    });

    const detailModules = this._getOverviewModules();
    const selector = containerEl.createDiv({
      cls: "pf-module-detail-selector",
      attr: { role: "tablist", "aria-label": t("md_module_switcher") },
    });
    for (const dm of detailModules) {
      const btn = selector.createEl("button", {
        cls:
          "pf-module-detail-btn" +
          (dm.id === mod ? " pf-module-detail-btn--active" : ""),
        text: dm.label,
        attr: {
          role: "tab",
          "aria-selected": String(dm.id === mod),
        },
      });
      btn.addEventListener("click", () => {
        this._selectedDetailModule = dm.id;
        this._focusTargetId = "#pf-" + dm.id + "-detail-heading";
        this.display();
      });
    }

    const nativeSelect = containerEl.createEl("select", {
      cls: "pf-module-switcher",
      attr: { "aria-label": t("md_module_switcher") },
    });
    for (const dm of detailModules) {
      const option = nativeSelect.createEl("option", {
        text: dm.label,
        attr: { value: dm.id },
      }) as HTMLOptionElement;
      option.selected = dm.id === mod;
    }
    nativeSelect.addEventListener("change", () => {
      this._selectedDetailModule = nativeSelect.value;
      this._focusTargetId = "#pf-" + nativeSelect.value + "-detail-heading";
      this.display();
    });

    const env =
      mod === "agent"
        ? this._getAgentPlaceholderEnvelope()
        : (this._capabilityState?.[mod] ?? createUnknownEnvelope(mod));
    const userState =
      env.user_state ??
      (env.capability_state === "ready" ? "ready" : "action_required");
    const summary = containerEl.createDiv({
      cls: "pf-module-summary",
      attr: { "aria-live": "polite" },
    });
    const header = summary.createDiv({ cls: "pf-module-summary-header" });
    header.createEl("h2", {
      cls: "pf-module-summary-name pf-module-detail-heading",
      text: this._getUserModuleName(mod),
      attr: { id: "pf-" + mod + "-detail-heading", tabindex: "-1" },
    });
    renderStatusBadge(header, userState, this._getUserStateLabel(userState));
    summary.createEl("p", {
      cls: "pf-module-summary-consequence",
      text: this._getModuleConsequence(mod, env),
    });

    if (env.activity_state === "running") {
      renderActivityRow(summary, {
        label: t("cc_activity_running"),
        progress: env.activity_progress,
      });
    }
    const primary = env.action?.primary;

    if (showPrimary && primary && userState !== "ready" && mod !== "agent") {
      const actionKey =
        "action_" + (primary.action_id ?? primary.verb).replace(/[.-]/g, "_");
      const translated = t(actionKey);
      const label =
        translated !== actionKey
          ? translated
          : t("cc_action_" + primary.verb) !== "cc_action_" + primary.verb
            ? t("cc_action_" + primary.verb)
            : t("cc_action_probe");
      renderActionButton(summary, {
        label,
        loading: env.activity_state === "running",
        onClick: () => this._dispatchModuleAction(mod, env),
      });
    }

    const details = summary.createEl("details", {
      cls: "pf-module-diagnostics",
    });
    details.createEl("summary", { text: t("advanced_diagnostics") });
    const diagnostics = details.createDiv({
      cls: "pf-module-diagnostics-body",
    });
    diagnostics.createEl("div", {
      text: t("cc_diag_module") + ": " + env.module,
    });
    diagnostics.createEl("div", {
      text: t("cc_diag_state") + ": " + this._getUserStateLabel(userState),
    });
    diagnostics.createEl("div", {
      text: t("cc_diag_severity") + ": " + env.severity,
    });
    diagnostics.createEl("div", {
      text: t("cc_diag_activity") + ": " + env.activity_state,
    });
    diagnostics.createEl("div", {
      text: t("cc_diag_reason") + ": " + env.reason.code,
    });
    diagnostics.createEl("div", {
      text: t("cc_diag_ttl") + ": " + env.ttl_seconds + "s",
    });
    for (const notice of env.notices ?? []) {
      diagnostics.createEl("div", { text: notice.message });
    }
    diagnostics.createEl("div", {
      text:
        t("cc_diag_updated") + ": " + new Date(env.updated_at).toLocaleString(),
    });
  }

  /** Render the Help tab — fetches Markdown from GitHub for live-editable docs. */
  _renderHelpTab(containerEl: HTMLElement): void {
    containerEl.createEl("div", {
      cls: "pf-cc-eyebrow",
      text: t("help_eyebrow") || "help",
    });
    containerEl.createEl("h1", {
      cls: "pf-cc-title",
      text: t("help_title") || "Help",
    });
    containerEl.createEl("p", {
      cls: "pf-cc-lede",
      text:
        t("help_lede") ||
        "Open the relevant module, or copy a diagnostic for support.",
    });

    // Loading indicator
    const loading = containerEl.createEl("p", {
      cls: "pf-help-loading",
      text: "Loading help content\u2026",
    });

    const lang = langFromApp(this.app);
    const base =
      "https://api.github.com/repos/LLLin000/PaperForge/contents/docs/help";
    const files = ["guide", "faq", "support"];
    const self = this;

    Promise.all(
      files.map((f) =>
        fetch(`${base}/${lang}/${f}.md`)
          .then((r) => (r.ok ? r.json() : Promise.reject()))
          .then((j: { content: string }) => {
            const bin = atob(j.content.replace(/\n/g, ""));
            const bytes = new Uint8Array(bin.length);
            for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
            return new TextDecoder().decode(bytes);
          })
          .then((text) => ({ name: f, text }))
          .catch(() => ({ name: f, text: "" }))
      )
    )
      .then((results) => {
        loading.remove();
        for (const { name, text } of results) {
          if (!text) continue;
          const titleMatch = text.match(/^#\s+(.+)/m);
          const title = titleMatch ? titleMatch[1] : name;
          const body = text.replace(/^#\s+.+(\r?\n|$)/, "").trim();

          const section = containerEl.createEl("details", {
            cls: "pf-help-section",
            attr: name === "support" ? { open: "true" } : {},
          });
          section.createEl("summary", {
            cls: "pf-help-section-title",
            text: title,
          });
          const bodyEl = section.createDiv({ cls: "pf-help-section-body" });
          if (name === "support") {
            MarkdownRenderer.render(
              self.app,
              body,
              bodyEl,
              "",
              self.plugin as unknown as Component
            );
            bodyEl
              .createEl("button", {
                cls: "pf-help-diagnostic-btn",
                text: t("help_copy") || "Copy Support Diagnostic",
              })
              .addEventListener("click", () => self._buildAndCopyDiagnostic());
          } else {
            MarkdownRenderer.render(
              self.app,
              body,
              bodyEl,
              "",
              self.plugin as unknown as Component
            );
          }
        }
      })
      .catch(() => {
        loading.setText(t("help_load_error") || "Failed to load help content.");
      });
  }

  _callPython(command: string[], opts?: any) {
    const vp = (this.app.vault.adapter as any).basePath as string;
    const resolved = this._resolveRuntimeCommand(vp);
    if (!resolved) {
      if (opts && opts.onClose)
        opts.onClose(1, "", "No python runtime available");
      return null;
    }
    const args = [
      ...resolved.args,
      "-m",
      "paperforge",
      "--vault",
      vp,
      ...command,
    ];
    // Env: caller-supplied takes precedence; credentialType triggers on-demand secret resolution
    const hasCredentialType = opts?.credentialType && !opts?.env;

    const spawnChild = (env: Record<string, string | undefined>) => {
      const child = spawn(resolved.path, args, {
        cwd: vp,
        env,
        windowsHide: true,
      });
      if (opts.onData) child.stdout.on("data", opts.onData);
      if (opts.onStderr) child.stderr.on("data", opts.onStderr);
      if (opts.onError) child.on("error", opts.onError);
      child.on("close", opts.onClose);
      return child;
    };

    const execChild = (env: Record<string, string | undefined>) => {
      execFile(
        resolved.path,
        args,
        { cwd: vp, timeout: (opts && opts.timeout) || 60000, env },
        (err, stdout, stderr) => {
          if (opts && opts.onClose) opts.onClose(err ? 1 : 0, stdout, stderr);
        }
      );
    };

    if (hasCredentialType) {
      // Async: resolve SecretStorage credentials before launch
      buildTargetedEnv(null, opts.credentialType).then((env) => {
        if (opts && opts.stream) {
          spawnChild(env);
        } else {
          execChild(env);
        }
      });
      return null;
    }

    // Sync: no credential resolution needed — launch immediately
    const env = opts?.env || paperforgeEnrichedEnv();
    if (opts && opts.stream) {
      return spawnChild(env);
    }
    execChild(env);
    return null;
  }

  _runManualSync() {
    const vp = (this.app.vault.adapter as any).basePath as string;
    const py = this._resolveRuntimeCommand(vp);
    if (!py?.path) return;

    // Overlay envelope activity
    const envelopes = this._capabilityState ?? {};
    if (envelopes["library"]) {
      envelopes["library"].activity_state = "running";
      envelopes["library"].activity_label = "Syncing library…";
    }

    const statusRow = document.querySelector(".paperforge-memory-status");
    if (statusRow) {
      // RC UX Seam: legacy status row retired with the old Smart Retrieval
      // UI — the read model owns activity truth now.
      (statusRow as HTMLElement).setText("Checking...");
    }

    this.plugin._autoSyncRunning = true;
    this._libraryRunning = true;
    this.display();
    this._callPython(["sync", "--json"], {
      timeout: 120000,
      onClose: (code: number | null, stdout: string) => {
        this.plugin._autoSyncRunning = false;
        this._libraryRunning = false;
        this._memoryStatusText = null;
        // Clear activity overlay
        if (envelopes["library"]) {
          envelopes["library"].activity_state = "idle";
          envelopes["library"].activity_label = null;
        }
        if (code === 0) {
          this._lastSyncTime = new Date().toLocaleTimeString();
          this.plugin._lastSyncTime = this._lastSyncTime;
          // #127: consume backend next_actions. Automatic local work starts
          // now; consent-required work remains visible in the module card.
          void orchestrateFromSync(stdout, {
            vaultPath: vp,
            resolveCommand: (v) => this._resolveRuntimeCommand(v),
          });
        }
        // #161: completed mutation → invalidate all + probe all; the
        // library exit code is forwarded for sync-failure detection (#78).
        this._refreshAllReadModels(code ?? 1);
        this._refreshSnapshots(vp);
        checkOrphanState(this.app, this.plugin, vp);
      },
    });
  }

  _refreshSnapshots(vp: string) {
    // #161/R: snapshot readers are retired; status text comes from probe
    // envelopes. The runtime-health command remains an on-demand diagnostic.
    const py = this._resolveRuntimeCommand(vp);
    if (!py) return;
    const args = [
      ...py.args,
      "-m",
      "paperforge",
      "--vault",
      vp,
      "runtime-health",
      "--json",
    ];

    this._refreshPending = true;

    execFile(
      py.path,
      args,
      { cwd: vp, timeout: 30000, windowsHide: true },
      () => {
        this._refreshPending = false;
        const memEnv = this._capabilityState?.["memory"];
        const embedEnv = this._capabilityState?.["embed"];
        this._memoryStatusText = memEnv
          ? ((memEnv as { reason?: { text?: string } }).reason?.text ?? null)
          : null;
        this._embedStatusText = embedEnv
          ? ((embedEnv as { reason?: { text?: string } }).reason?.text ?? null)
          : null;
        this.display();
      }
    );
  }

  _debouncedSave() {
    clearTimeout(this._saveTimeout!);
    this._saveTimeout = setTimeout(() => this.plugin.saveSettings(), 500);
  }

  _renderReleaseNotesTab(containerEl: HTMLElement) {
    containerEl.createEl("h2", { text: "\u66F4\u65B0\u4E0E\u624B\u518C" });

    containerEl.createEl("h3", {
      text: "\u7248\u672C\u66F4\u65B0\u8BB0\u5F55",
    });

    const versions = (releaseNotesData as any).versions || [];
    for (const ver of versions) {
      const card = containerEl.createEl("div", {
        cls: "paperforge-release-card",
      });

      const header = card.createEl("div", { cls: "paperforge-release-header" });
      header.createEl("strong", {
        text: `v${ver.version} \u2014 ${ver.title}`,
      });
      header.createEl("span", {
        cls: "paperforge-release-date",
        text: `  (${ver.date})`,
      });

      if (ver.breaking_or_migration && ver.breaking_or_migration.length > 0) {
        const section = card.createEl("div", {
          cls: "paperforge-release-section",
        });
        section.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u884C\u4E3A\u53D8\u66F4 / \u8FC1\u79FB\u6CE8\u610F",
        });
        for (const item of ver.breaking_or_migration) {
          section.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${item}`,
          });
        }
      }

      if (ver.new_features && ver.new_features.length > 0) {
        const section = card.createEl("div", {
          cls: "paperforge-release-section",
        });
        section.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u65B0\u529F\u80FD",
        });
        for (const item of ver.new_features) {
          section.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${item}`,
          });
        }
      }

      if (ver.fixes && ver.fixes.length > 0) {
        const section = card.createEl("div", {
          cls: "paperforge-release-section",
        });
        section.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u4FEE\u590D",
        });
        for (const item of ver.fixes) {
          section.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${item}`,
          });
        }
      }

      if (ver.recommended_actions && ver.recommended_actions.length > 0) {
        const section = card.createEl("div", {
          cls: "paperforge-release-section paperforge-release-recommended",
        });
        section.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u5EFA\u8BAE\u64CD\u4F5C",
        });
        for (const item of ver.recommended_actions) {
          section.createEl("div", {
            cls: "paperforge-release-item paperforge-release-item-bold",
            text: `\u2022 ${item}`,
          });
        }
      }
    }

    containerEl.createEl("h3", { text: "\u4F7F\u7528\u624B\u518C" });
    const manualSection = containerEl.createEl("div", {
      cls: "paperforge-manual-links",
    });
    const manualLink = manualSection.createEl("a", {
      text: "\u2192 \u67E5\u770B\u5B8C\u6574\u4F7F\u7528\u624B\u518C\uFF08GitHub\uFF09",
      href: "https://github.com/LLLin000/PaperForge/blob/master/docs/user-manual.md",
    });
    manualLink.setAttr("target", "_blank");
  }

  // ── Capability state management (Issue #76) ──

  /**
   * Ensure capabilityState exists for all six modules.
   * Always materializes unknown envelopes when stored map is absent/partial,
   * so first-run immediately probes Installation+Help.
   */
  _initCapabilityState(): void {
    const stored = this.plugin.settings.capabilityState;
    this._capabilityState = validatePersistedEnvelopes(
      (stored ?? {}) as Record<string, unknown>,
      CAPABILITY_MODULES as unknown as string[]
    );
    this._persistCapabilityState();
  }

  /** Persist capability state to plugin settings. */
  _persistCapabilityState(): void {
    if (!this._capabilityState) return;
    this.plugin.settings.capabilityState = this._capabilityState;
    this.plugin.saveSettings();
  }

  /** Call `paperforge probe <module> --json` and store the validated envelope unchanged. */
  _probeModule(mod: CapabilityModule, lastOperationExitCode?: number): void {
    if (this._probing.has(mod)) return;
    this._probing.add(mod);

    // Show probing state immediately
    const current = this._capabilityState?.[mod];
    const probing: ProbeEnvelope = {
      schema_version: 2,
      module: mod,
      capability_state: current?.capability_state ?? "unknown",
      activity_state: "running",
      activity_label: "Probing...",
      activity_progress: null,
      severity: "unknown",
      reason: { code: `${mod}.probing`, text: `Checking ${mod} status...` },
      action: { primary: probeAction(mod) },
      notices: current?.notices ?? [],
      user_state: "checking",
      capability_kind:
        mod === "installation" || mod === "library" ? "required" : "optional",
      maintenance_eligible: false,
      user_visible_failure: false,
      user_impact: null,
      updated_at: new Date().toISOString(),
      ttl_seconds: current?.ttl_seconds ?? 0,
    };
    this._updateCapabilityEnvelope(mod, probing);

    const vp = (this.app.vault.adapter as any).basePath as string;
    const resolved = this._resolveRuntimeCommand(vp);
    if (!resolved) {
      this._probing.delete(mod);
      // Contract Gap 2: first-run machines with no Python at all must
      // show a concrete Setup CTA, not a generic "Check" button.
      if (mod === "installation") {
        const setupEnvelope: ProbeEnvelope = {
          schema_version: 2,
          module: "installation",
          capability_state: "unknown",
          activity_state: "idle",
          activity_label: null,
          activity_progress: null,
          severity: "error",
          reason: {
            code: "installation.no_python",
            text: "No Python found. Run the Setup Wizard to install the managed runtime.",
          },
          action: { primary: setupAction() },
          notices: [],
          user_state: "setup_required",
          capability_kind: "required",
          maintenance_eligible: false,
          user_visible_failure: false,
          user_impact: null,
          updated_at: new Date().toISOString(),
          ttl_seconds: 60,
        };
        this._updateCapabilityEnvelope(mod, setupEnvelope);
      } else {
        this._updateCapabilityEnvelope(mod, createInvalidEnvelope(mod));
      }
      return;
    }

    const args = [
      ...resolved.args,
      "-m",
      "paperforge",
      "--vault",
      vp,
      "probe",
      mod,
      "--json",
    ];
    if (
      mod === "library" &&
      lastOperationExitCode != null &&
      lastOperationExitCode !== 0
    ) {
      args.push("--last-operation-exit-code", String(lastOperationExitCode));
    }
    if (mod === "installation") {
      args.push("--expected-version", this.plugin.manifest.version);
    }

    execFile(
      resolved.path,
      args,
      { cwd: vp, timeout: 15000 },
      (err: Error | null, stdout: string, stderr: string) => {
        this._probing.delete(mod);
        if (err) {
          console.warn(`[PaperForge] Probe ${mod} failed:`, err.message);
          this._updateCapabilityEnvelope(mod, createInvalidEnvelope(mod));
          return;
        }
        try {
          const parsed: unknown = JSON.parse(stdout);
          // Backend JSON passed through unchanged after strict validation
          if (isValidEnvelope(parsed, mod)) {
            const envelope = parsed as ProbeEnvelope;
            // #174 / #143 §8: version mismatch is NEVER auto-repaired —
            // bootstrap consent authorizes ONE initial install only; later
            // update/reinstall must go through the user's explicit action
            // (Install/Reinstall button → _installFoundation → the sole
            // bootstrap installer).  Zero pip calls before user action.
            this._updateCapabilityEnvelope(mod, envelope);
          } else {
            console.warn(
              `[PaperForge] Probe ${mod}: invalid envelope schema`,
              stdout?.slice(0, 200)
            );
            this._updateCapabilityEnvelope(mod, createInvalidEnvelope(mod));
          }
        } catch {
          console.warn(
            `[PaperForge] Probe ${mod}: unparseable JSON`,
            stdout?.slice(0, 200)
          );
          this._updateCapabilityEnvelope(mod, createInvalidEnvelope(mod));
        }
      }
    );
  }

  /** Update a single module envelope and refresh the display (#85: Last Known State). */
  _updateCapabilityEnvelope(mod: string, envelope: ProbeEnvelope): void {
    if (!this._capabilityState) this._capabilityState = {};
    const prev = this._capabilityState[envelope.module];

    // #85: Capture Last Known State on successful Ready
    if (shouldUpdateLastKnown(prev, envelope)) {
      this._lastKnownState.set(mod, captureLastKnown(envelope));
    }

    if (mod === "installation" && envelope.user_state === "ready") {
      this._setupReinstallRequested = false;
    }
    this._capabilityState[envelope.module] = envelope;
    this._persistCapabilityState();
    if (
      prev?.activity_state === "running" &&
      envelope.activity_state !== "running"
    ) {
      new Notice(t("cc_notice_refreshed"), 3000);
    }
    if (!this._displayInProgress) {
      this.display();
    }
  }

  /** Derive badge i18n key from envelope severity + module. */
  private _ccBadgeKey(env: ProbeEnvelope, mod: CapabilityModule): string {
    if (env.activity_state === "running") return "cc_badge_checking";
    if (env.severity === "ok") return "cc_badge_ok";
    if (env.severity === "error" && mod === "installation")
      return "cc_badge_setup";
    if (env.severity === "warning" || env.severity === "error")
      return "cc_badge_attention";
    return "cc_badge_pending";
  }

  /** CSS severity class from backend severity string. Unknown maps to neutral. */
  _sevClass(severity: string, activity?: string): string {
    if (activity === "running") return "checking";
    if (severity === "error") return "error";
    if (severity === "warning") return "warn";
    if (severity === "unknown") return "unknown";
    return "ok";
  }

  /** Reason code → localized string via i18n key, or null if unmapped.
   *  Tries full dotted code normalized to underscores first (e.g. "installation.ready" → "cc_reason_installation_ready"),
   *  then falls back to bare code (e.g. "ready" → "cc_reason_ready"). */
  private _localizeReason(code: string, module: string): string | null {
    // Try full dotted code: "installation.ready" → "cc_reason_installation_ready"
    const fullKey = "cc_reason_" + code.replace(/\./g, "_");
    const fullTranslated = t(fullKey);
    if (fullTranslated !== fullKey) {
      return fullTranslated.replace("{module}", module);
    }
    // Fallback to bare code: "installation.ready" → "ready" → "cc_reason_ready"
    const bare = code.replace(/^[a-z]+\./, "");
    const bareKey = "cc_reason_" + bare;
    const bareTranslated = t(bareKey);
    if (bareTranslated === bareKey) return null;
    return bareTranslated.replace("{module}", module);
  }

  /** Modules with real Python probe support. */
  private static _REAL_PROBE = new Set([
    "installation",
    "library",
    "ocr",
    "memory",
    "help",
  ]);
  /** Modules that have a navigation entry in the overview card grid. */
  private static _NAVIGABLE = new Set([
    "installation",
    "library",
    "ocr",
    "memory",
    "help",
  ]);

  _renderCard(
    container: HTMLElement,
    mod: CapabilityModule,
    envelope: ProbeEnvelope
  ): void {
    const env = envelope;
    const sevClass = this._sevClass(env.severity, env.activity_state);
    const isReal = PaperForgeSettingTab._REAL_PROBE.has(mod);
    const isNavigable = PaperForgeSettingTab._NAVIGABLE.has(mod);
    const card = container.createEl("div", {
      cls: "pf-cc-card pf-open-module-btn",
      attr: {
        role: "listitem",
        tabindex: "0",
        "data-module": mod,
        "aria-label": `${t("cc_module_" + mod)} — ${t(this._ccBadgeKey(env, mod))}`,
      },
    });

    // Header: name area with optional navigation entry
    const header = card.createEl("div", { cls: "pf-cc-card-header" });
    const nameArea = header.createEl("div", { cls: "pf-cc-card-name-area" });
    if (isNavigable) {
      // Navigation entry — Enter/Space or click opens module detail
      const openLabel =
        mod === "installation"
          ? t("module_detail_open_installation")
          : mod === "library"
            ? t("module_detail_open_library")
            : mod === "ocr"
              ? t("module_detail_open_ocr")
              : mod === "memory"
                ? t("module_detail_open_memory")
                : mod === "help"
                  ? t("module_detail_open_help")
                  : t("md_select_installation");
      const navBtn = nameArea.createEl("button", {
        cls: "pf-open-module-btn",
        text: t("cc_module_" + mod),
        attr: { "data-module": mod, "aria-label": openLabel },
      });
      navBtn.addEventListener("click", () => this._handleCardNavigation(mod));
      navBtn.addEventListener("keydown", (e: KeyboardEvent) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          this._handleCardNavigation(mod);
        }
      });
    } else {
      nameArea.createEl("div", {
        cls: "pf-cc-card-name",
        text: t("cc_module_" + mod),
      });
    }
    header.createEl("div", {
      cls: `pf-cc-card-badge pf-cc-card-badge--${sevClass}`,
      text: t(this._ccBadgeKey(env, mod)),
    });

    // Reason text — localized via code map, fallback to backend text
    // Placeholder modules (library, ocr, memory, maintenance) show "pending integration"
    let reasonText: string;
    if (!isReal) {
      reasonText = t("cc_reason_placeholder").replace(
        "{module}",
        t("cc_module_" + mod)
      );
    } else {
      const l10nReason = this._localizeReason(env.reason.code, mod);
      reasonText = l10nReason ?? env.reason.text;
    }
    card.createEl("div", { cls: "pf-cc-card-reason", text: reasonText });

    // Activity label + progress bar (DOM style.width, never inline attribute)
    if (env.activity_state === "running" && env.activity_label) {
      const activityRow = card.createEl("div", {
        cls: "pf-cc-card-activity",
        attr: { "aria-live": "polite" },
      });
      activityRow.createEl("span", { text: env.activity_label });
      if (env.activity_progress && env.activity_progress.total > 0) {
        const pct = Math.round(
          (env.activity_progress.current / env.activity_progress.total) * 100
        );
        const bar = activityRow.createEl("div", {
          cls: "pf-cc-card-progress",
          attr: {
            role: "progressbar",
            "aria-valuenow": String(env.activity_progress.current),
            "aria-valuemin": "0",
            "aria-valuemax": String(env.activity_progress.total),
          },
        });
        const fill = bar.createEl("div", { cls: "pf-cc-card-progress-fill" });
        fill.style.width = pct + "%";
      }
    }

    // Footer: action button + diagnostics
    const footer = card.createEl("div", { cls: "pf-cc-card-footer" });

    // Action button — only for real modules (installation/help); placeholders show no action
    if (isReal && env.action.primary && !isReadyEnvelope(env)) {
      const action = classifyCapabilityAction(env);
      const isCta = action.kind === "setup";
      const btnCls = isCta
        ? "pf-cc-card-action pf-cc-card-action--primary"
        : "pf-cc-card-action";
      const btn = footer.createEl("button", {
        cls: btnCls,
        text: action.label,
        attr: { "aria-label": action.label },
      });
      btn.addEventListener("click", () => {
        if (action.kind === "setup") {
          this._startSetupJourney(1);
        } else {
          this._dispatchModuleAction(mod, env);
        }
      });
    }

    // Diagnostics — native <details><summary> with localized field labels and values
    const details = card.createEl("details", { cls: "pf-cc-card-diagnostic" });
    details.createEl("summary", { text: t("cc_diagnostic_toggle") });
    const body = details.createEl("div", { cls: "pf-cc-card-diagnostic-body" });

    // Localized values
    const stateLabel =
      t("cc_state_" + env.capability_state) || env.capability_state;
    const sevLabel = t("cc_severity_" + env.severity) || env.severity;
    const activityLabel =
      t("cc_activity_" + env.activity_state) || env.activity_state;

    // Format updated_at with locale
    let dateLabel: string;
    try {
      dateLabel = new Date(env.updated_at).toLocaleString();
    } catch {
      dateLabel = env.updated_at;
    }

    body.createEl("div", { text: `${t("cc_diag_module")}: ${env.module}` });
    body.createEl("div", { text: `${t("cc_diag_state")}: ${stateLabel}` });
    body.createEl("div", { text: `${t("cc_diag_severity")}: ${sevLabel}` });
    body.createEl("div", {
      text: `${t("cc_diag_activity")}: ${activityLabel}`,
    });
    // Reason: localized text (or placeholder message) plus technical code in <code>
    const reasonRow = body.createEl("div");
    reasonRow.appendText(t("cc_diag_reason") + ": " + reasonText + " ");
    const codeEl = reasonRow.createEl("code", { text: env.reason.code });
    body.createEl("div", {
      text: `${t("cc_diag_ttl")}: ${String(env.ttl_seconds)}s`,
    });
    body.createEl("div", { text: `${t("cc_diag_updated")}: ${dateLabel}` });
  }

  /** Navigate from overview card to module detail or another tab. */
  /** Navigate from a card to its detail/maintenance/help destination. */
  _handleCardNavigation(mod: string): void {
    if (mod === "help") {
      this.activeTab = "help";
      this._selectedDetailModule = "";
      this._focusTargetId = "div.pf-open-module-btn[data-module=help]";
    } else {
      this.activeTab = "module-detail";
      this._selectedDetailModule = mod;
      this._focusTargetId = "#pf-" + mod + "-detail-heading";
    }
    // Nav memory is intentionally NOT updated here — only the topbar tab
    // click handler persists it. _restoreNavMemory runs only on the first
    // display() call, so subsequent programmatic navigations are unaffected.
    this.display();
  }

  /** #86: Overview — operational baseline + five navigation-only module cards. */
  _renderControlCenter(containerEl: HTMLElement): void {
    const cc = containerEl.createEl("div", { cls: "pf-control-center" });
    const envelopes: Record<string, ProbeEnvelope> =
      this._capabilityState ?? {};

    // ── Eyebrow + Title + Lede ──
    cc.createEl("div", {
      cls: "pf-cc-eyebrow",
      text: t("cc_eyebrow") || "control center",
    });
    cc.createEl("h1", {
      cls: "pf-cc-title",
      text: t("cc_title") || "Your literature pipeline",
    });
    cc.createEl("p", {
      cls: "pf-cc-lede",
      text:
        t("cc_lede") ||
        "See what is working and what needs attention across your pipeline.",
    });

    // ── Summary Card ──
    const foundationEnv =
      envelopes["installation"] ?? createUnknownEnvelope("installation");
    const libraryEnv = envelopes["library"] ?? createUnknownEnvelope("library");
    const foundationReady = foundationEnv.user_state === "ready";
    const libraryReady = libraryEnv.user_state === "ready";
    const baselineReady = foundationReady && libraryReady;
    const baselineChecking = [foundationEnv, libraryEnv].some(
      (env) => env.user_state === "checking"
    );
    const needsAttention = Object.values(envelopes).filter(
      (e) =>
        e.user_state &&
        e.user_state !== "ready" &&
        e.user_state !== "not_enabled"
    ).length;

    const summaryEl = cc.createEl("div", { cls: "pf-cc-summary" });
    const badgeCls = baselineReady
      ? "ready"
      : baselineChecking
        ? "checking"
        : "attention";
    const badgeText = baselineReady
      ? t("cc_badge_ready") || "Ready"
      : baselineChecking
        ? t("cc_badge_checking") || "Checking"
        : t("cc_badge_attention") || "Needs attention";
    summaryEl.createEl("span", {
      cls: `pf-cc-summary-badge pf-cc-summary-badge--${badgeCls}`,
      text: badgeText,
    });

    const summaryCopy = summaryEl.createDiv({ cls: "pf-cc-summary-copy" });
    const summaryTitle = baselineReady
      ? t("cc_summary_ready")
      : baselineChecking
        ? t("cc_summary_checking")
        : this.plugin.settings._setup_complete === false
          ? t("cc_summary_incomplete")
          : t("cc_summary_attention");
    const summaryBody = baselineReady
      ? t("cc_summary_ready_body")
      : baselineChecking
        ? t("cc_summary_checking_body")
        : this.plugin.settings._setup_complete === false
          ? t("cc_summary_incomplete_body")
          : t("cc_summary_attention_body");
    summaryCopy.createEl("strong", { text: summaryTitle });
    summaryCopy.createEl("span", { cls: "caption", text: summaryBody });

    const summaryMeta = summaryEl.createDiv({ cls: "pf-cc-summary-meta" });
    const needItem = summaryMeta.createEl("span");
    needItem.createEl("strong", { text: String(needsAttention) });
    needItem.appendText(
      " " + (t("cc_needs_attention") || "item needs attention")
    );

    // Last checked time
    const latest = Object.values(envelopes)
      .map((e) => e.updated_at)
      .filter(Boolean)
      .sort()
      .pop();
    summaryMeta.createEl("span", {
      text: latest
        ? (t("cc_last_checked") || "Checked just now: ") +
          new Date(latest).toLocaleString()
        : t("cc_checked_pending") || "Not checked yet",
    });

    const refreshBtn = summaryMeta.createEl("button", {
      cls: "pf-cc-summary-refresh",
      text: t("cc_refresh_btn") || "Refresh status",
    });
    refreshBtn.addEventListener("click", () => this._refreshAllModules());

    // ── Section Head ──
    const sectionHead = cc.createDiv({ cls: "pf-cc-section-head" });
    sectionHead.createEl("div", {
      cls: "pf-cc-eyebrow",
      text: t("cc_modules_header") || "modules",
    });
    sectionHead.createEl("span", {
      cls: "caption",
      text:
        t("cc_optional_note") ||
        "Optional modules do not affect core readiness.",
    });

    // ── Module List (5 cards with numbering 01-05) ──
    const moduleList = cc.createDiv({ cls: "pf-cc-module-list" });
    for (const [idx, mod] of this._getOverviewModules().entries()) {
      const env =
        mod.id === "agent"
          ? this._getAgentPlaceholderEnvelope()
          : (envelopes[mod.id] ??
            createUnknownEnvelope(mod.id as CapabilityModule));
      this._renderOverviewCard(moduleList, mod.id, mod.label, env, idx + 1);
    }
  }

  /** Derive Agent availability from the selected platform's deployed skill. */
  _getAgentPlaceholderEnvelope(): ProbeEnvelope {
    const platform = this.plugin.settings.agent_platform || "opencode";
    const directories: Record<string, string> = {
      opencode: ".opencode/skills",
      claude: ".claude/skills",
      codex: ".codex/skills",
      cursor: ".cursor/skills",
      windsurf: ".windsurf/skills",
      github_copilot: ".github/skills",
      gemini: ".gemini/skills",
    };
    const skill = path.join(
      this._getVaultBasePath(),
      directories[platform] ?? directories.opencode,
      "paperforge",
      "SKILL.md"
    );
    const deployed = fs.existsSync(skill);
    return {
      schema_version: 2,
      module: "agent",
      capability_state: deployed ? "ready" : "needs_action",
      activity_state: "idle",
      activity_label: null,
      activity_progress: null,
      severity: deployed ? "ok" : "warning",
      reason: {
        code: deployed ? "agent.skills_deployed" : "agent.skills_not_deployed",
        text: deployed
          ? "PaperForge Skills are deployed for the selected platform."
          : "PaperForge Skills have not been deployed for the selected platform.",
      },
      action: { primary: null },
      notices: [],
      user_state: deployed ? "ready" : "not_enabled",
      capability_kind: "optional",
      maintenance_eligible: false,
      user_visible_failure: false,
      user_impact: null,
      updated_at: new Date().toISOString(),
      ttl_seconds: 300,
    };
  }

  /** #86: Render a navigation-only overview card for one operational module. */
  _renderOverviewCard(
    grid: HTMLElement,
    mod: string,
    label: string,
    env: ProbeEnvelope,
    num: number
  ): void {
    const card = grid.createEl("div", {
      cls: "pf-cc-module-card pf-open-module-btn",
      attr: {
        "data-module": mod,
        "aria-label": label + " — " + this._getUserStateLabel(env.user_state),
        role: "button",
        tabindex: "0",
      },
    });
    card.style.cursor = "pointer";
    // Number
    card.createEl("span", {
      cls: "pf-cc-num",
      text: String(num).padStart(2, "0"),
    });
    // Name
    card.createEl("span", {
      cls: "pf-cc-card-name",
      text: label,
    });
    // Badge
    renderStatusBadge(
      card,
      env.user_state,
      this._getUserStateLabel(env.user_state)
    );
    // Sentence (one-line status)
    card.createEl("span", {
      cls: "pf-cc-card-sentence",
      text: this._getModuleConsequence(mod, env),
    });
    // Metric (version / papers info)
    const metricText =
      env.user_state === "ready" &&
      env.action?.primary?.scope_count &&
      env.action.primary.scope_count > 1
        ? (t("cc_metric_papers") || "Papers: ") + env.action.primary.scope_count
        : env.updated_at && env.updated_at !== new Date(0).toISOString()
          ? (t("cc_last_checked") || "") +
            new Date(env.updated_at).toLocaleString()
          : "";
    card.createEl("span", {
      cls: "pf-cc-card-metric",
      text: metricText,
    });
    // Arrow
    card.createEl("span", { cls: "pf-cc-card-arrow", text: "\u2192" });
    card.addEventListener("click", () => this._handleCardNavigation(mod));
  }

  /** #86: Plain-language consequence based on module state. */
  _getUserStateLabel(state: string): string {
    return t("cc_badge_" + state);
  }

  _getModuleConsequence(mod: string, env: ProbeEnvelope): string {
    const state =
      env.user_state ??
      (env.capability_state === "ready" ? "ready" : "action_required");
    const key = "cc_consequence_" + mod + "_" + state;
    const translated = t(key);
    if (translated && translated !== key) return translated;
    const reason = this._localizeReason(
      env.reason?.code ?? "",
      this._getUserModuleName(mod)
    );
    if (reason) return reason;
    const fallbackKey = "cc_consequence_" + state;
    const fallback = t(fallbackKey);
    return fallback !== fallbackKey ? fallback : t("cc_consequence_default");
  }

  /** Apply stale-tolerance: if an envelope is stale, replace with unknown+probe. */
  _applyStaleTolerance(): void {
    if (!this._capabilityState) return;
    let changed = false;
    for (const mod of CAPABILITY_MODULES) {
      const env = this._capabilityState[mod];
      if (env && isEnvelopeStale(env)) {
        this._capabilityState[mod] = createStaleEnvelope(mod);
        changed = true;
      }
    }
    if (changed) this._persistCapabilityState();
  }

  /** #85: Refresh all operational modules. */
  _refreshAllModules(): void {
    this._refreshAllReadModels();
  }

  /**
   * #161 acceptance: any completed mutation invalidates the whole read-model
   * cache (all six envelopes + detail cache) and re-probes via `probe all`.
   * #144: no dependency map — invalidate everything, refresh everything.
   * Stale actions stay disabled until fresh envelopes land (last-known kept).
   */
  _refreshAllReadModels(lastLibraryExitCode?: number): void {
    invalidateAll();
    const vp =
      (this.app.vault.adapter as unknown as { basePath?: string }).basePath ??
      "";
    if (!vp) {
      this._probing.clear();
      return;
    }
    this._probing.clear();
    for (const mod of CAPABILITY_MODULES) {
      this._probing.add(mod);
    }
    void probeAll(vp, this.plugin.settings)
      .then((data) => {
        this._probing.clear();
        for (const [mod, env] of Object.entries(data.modules ?? {})) {
          if (isValidEnvelope(env, mod as CapabilityModule)) {
            this._updateCapabilityEnvelope(
              mod as CapabilityModule,
              env as ProbeEnvelope
            );
          }
        }
        // #78: the library sync-failure exit code is forwarded into the
        // library probe (probe all carries no exit-code context).
        if (lastLibraryExitCode != null && lastLibraryExitCode !== 0) {
          this._probeModule("library", lastLibraryExitCode);
        }
      })
      .catch(() => {
        this._probing.clear();
        this.display();
      });
  }

  /** #85: Build and copy privacy-safe Support Diagnostic. */
  _buildAndCopyDiagnostic(): void {
    const pluginVersion = this.plugin.manifest?.version ?? "unknown";
    const modules = collectDiagnosticModules(
      this._capabilityState ?? {},
      this._lastKnownState
    );
    const diag: DiagnosticInput = {
      pluginVersion,
      modules,
    };
    const text = buildSupportDiagnostic(diag);
    copySupportDiagnostic(text, () => {
      new Notice(t("support_diagnostic_copied"), 3000);
    });
  }

  /** #85: Persist navigation destination/module only. */
  _persistNavMemory(): void {
    this.plugin.settings._navMemory = { ...this._navMemory };
    this.plugin.saveSettings();
  }

  /** #85: Restore navigation, never restore drafts/scroll/focus/disclosure. */
  // ═══════════════════════════════════════════════════════════════
  // #87: Setup Journey — 4-stage first-use wizard
  // ═══════════════════════════════════════════════════════════════

  _renderSetupJourney(containerEl: HTMLElement): void {
    if (this.plugin.settings._setup_journey_started !== true) {
      this.plugin.settings._setup_journey_started = true;
      this.plugin.saveSettings();
    }
    const wrapper = containerEl.createDiv({ cls: "pf-setup-journey" });
    wrapper.createEl("h2", { text: t("setup_welcome") });
    wrapper.createEl("p", {
      text: t("setup_desc"),
      cls: "pf-setup-desc",
    });

    const stages = [
      t("setup_stage_1"),
      t("setup_stage_2"),
      t("setup_stage_3"),
      t("setup_stage_4"),
    ];
    const progress = wrapper.createDiv({
      cls: "pf-setup-progress",
      attr: { "aria-label": t("setup_progress") },
    });
    stages.forEach((label, i) => {
      progress.createEl("span", {
        cls:
          "pf-setup-step" +
          (i + 1 === this._setupStage ? " pf-setup-step--active" : "") +
          (i + 1 < this._setupStage ? " pf-setup-step--done" : ""),
        text: String(i + 1) + ". " + label,
        attr: {
          "aria-current": i + 1 === this._setupStage ? "step" : "false",
        },
      });
    });

    const body = wrapper.createDiv({ cls: "pf-setup-body" });
    if (this._setupStage === 1) this._renderSetupStageFoundation(body);
    else if (this._setupStage === 2) this._renderSetupStageLibrary(body);
    else if (this._setupStage === 3) this._renderSetupStageOptionals(body);
    else this._renderSetupStageReview(body);
  }

  _renderSetupStageFoundation(containerEl: HTMLElement): void {
    const env =
      this._capabilityState?.installation ??
      createUnknownEnvelope("installation");
    const needsProbe =
      (env.capability_state === "unknown" &&
        env.updated_at === new Date(0).toISOString()) ||
      (env.user_state === "detection_failed" &&
        env.reason.code.endsWith(".stale"));
    if (needsProbe && !this._attemptedProbes.has("installation")) {
      this._attemptedProbes.add("installation");
      this._probeModule("installation");
    }
    containerEl.createEl("h3", { text: t("setup_foundation_title") });
    containerEl.createEl("p", { text: t("setup_foundation_desc") });
    const pythonField = containerEl.createDiv({ cls: "pf-setup-field" });
    pythonField.createEl("label", { text: t("setup_foundation_python") });
    pythonField.createEl("span", {
      cls: "caption",
      text: t("setup_foundation_python_hint"),
    });
    const pythonInput = pythonField.createEl("input", {
      cls: "pf-setup-input",
      attr: { type: "text", placeholder: "python" },
    }) as HTMLInputElement;
    pythonInput.value = this.plugin.settings.python_path || "";
    pythonInput.addEventListener("input", () => {
      this.plugin.settings.python_path = pythonInput.value.trim();
      this._debouncedSave();
    });
    renderStatusBadge(
      containerEl,
      env.user_state,
      this._getUserStateLabel(env.user_state)
    );
    containerEl.createEl("p", {
      text:
        env.user_state === "ready"
          ? t("setup_ready")
          : this._getModuleConsequence("installation", env),
      cls: env.user_state === "ready" ? "pf-setup-ok" : "pf-setup-status",
    });
    if (this._setupOperation === "running") {
      containerEl.createEl("p", {
        cls: "pf-setup-status",
        text: t("setup_installing"),
      });
    } else {
      if (this._setupFeedback) {
        containerEl.createEl("p", {
          cls:
            this._setupOperation === "failed" ? "pf-setup-warn" : "pf-setup-ok",
          text: this._setupFeedback,
        });
      }
      if (
        env.user_state !== "ready" &&
        (this._setupReinstallRequested ||
          env.reason.code === "installation.version_mismatch")
      ) {
        containerEl.createEl("p", {
          cls: "pf-setup-warn",
          text: t("setup_reinstall_notice"),
        });
        renderActionButton(containerEl, {
          label: t("foundation_reinstall_btn"),
          onClick: () => this._installFoundation(true),
        });
      } else if (
        env.user_state !== "ready" ||
        this._setupOperation === "failed"
      ) {
        renderActionButton(containerEl, {
          label: t("setup_foundation_install_btn"),
          onClick: () => this._installFoundation(false),
        });
      }
    }
    const nav = containerEl.createDiv({ cls: "pf-setup-nav" });
    // RC UX Seam: Stage 1 must never trap the user.
    //  - running: a real Cancel aborts installOnce/handshake/setup through
    //    the AbortController (installOnce deletes the half-installed venv).
    //  - idle/failed: "Later" exits the wizard; _setup_complete stays false
    //    so reopening Settings resumes at this exact stage.
    if (this._setupOperation === "running") {
      renderActionButton(nav, {
        label: t("setup_nav_cancel"),
        onClick: () => {
          this._runtimeAbortController?.abort();
          // The install chain's catch(finally) handles UI settle; keep the
          // button live so repeated clicks are harmless.
        },
      });
    } else {
      renderActionButton(nav, {
        label: t("setup_nav_later"),
        onClick: () => {
          this._setupOperation = "idle";
          this._setupFeedback = null;
          this._setupStage = 1;
          this.activeTab = "overview";
          // RC UX Seam P1: without this the display() gate
          // (_setup_complete === false) would immediately re-render the
          // journey and the user could never leave Stage 1.
          this._setupJourneyDismissedForSession = true;
          this.display();
        },
      });
    }
    renderActionButton(nav, {
      label: t("setup_nav_continue"),
      disabled: env.user_state !== "ready",
      onClick: () => {
        this._setupFeedback = null;
        this._setupStage = 2;
        this.display();
      },
    });
  }

  _renderSetupStageLibrary(containerEl: HTMLElement): void {
    const env =
      this._capabilityState?.library ?? createUnknownEnvelope("library");
    const needsProbe =
      (env.capability_state === "unknown" &&
        env.updated_at === new Date(0).toISOString()) ||
      (env.user_state === "detection_failed" &&
        env.reason.code.endsWith(".stale"));
    if (needsProbe && !this._attemptedProbes.has("library")) {
      this._attemptedProbes.add("library");
      this._probeModule("library");
    }

    containerEl.createEl("h3", { text: t("setup_library_title") });
    containerEl.createEl("p", { text: t("setup_library_desc") });
    renderStatusBadge(
      containerEl,
      env.user_state,
      this._getUserStateLabel(env.user_state)
    );
    containerEl.createEl("p", {
      text:
        env.user_state === "ready"
          ? t("setup_library_ready")
          : this._getModuleConsequence("library", env),
      cls: env.user_state === "ready" ? "pf-setup-ok" : "pf-setup-status",
    });
    if (this._setupOperation === "running") {
      containerEl.createEl("p", {
        cls: "pf-setup-status",
        text: t("setup_library_configuring"),
      });
    } else if (this._setupFeedback) {
      containerEl.createEl("p", {
        cls:
          this._setupOperation === "failed" ? "pf-setup-warn" : "pf-setup-ok",
        text: this._setupFeedback,
      });
    }

    const form = containerEl.createDiv({ cls: "pf-setup-library-form" });
    form.createEl("p", {
      cls: "pf-setup-form-intro",
      text: t("setup_library_config_desc"),
    });
    const addField = (
      parent: HTMLElement,
      label: string,
      key:
        | "zotero_data_dir"
        | "system_dir"
        | "resources_dir"
        | "literature_dir"
        | "base_dir",
      hint?: string
    ) => {
      const field = parent.createDiv({ cls: "pf-setup-field" });
      field.createEl("label", { text: label });
      if (hint) field.createEl("span", { cls: "caption", text: hint });
      const input = field.createEl("input", {
        cls: "pf-setup-input",
        attr: { type: "text" },
      }) as HTMLInputElement;
      input.value = this.plugin.settings[key] || "";
      input.addEventListener("input", () => {
        this.plugin.settings[key] = input.value.trim();
        this._debouncedSave();
      });
    };

    addField(
      form,
      t("field_zotero_data"),
      "zotero_data_dir",
      t("setup_library_zotero_hint")
    );
    form.createEl("h4", { text: t("setup_library_folder_heading") });
    const folders = form.createDiv({ cls: "pf-setup-folder-grid" });
    addField(folders, t("dir_system"), "system_dir");
    addField(folders, t("dir_resources"), "resources_dir");
    addField(folders, t("dir_notes"), "literature_dir");
    addField(folders, t("dir_base"), "base_dir");

    const verify = form.createEl("button", {
      cls: "pf-setup-verify",
      text: t("setup_library_verify"),
      attr: { type: "button" },
    });
    verify.disabled = this._setupOperation === "running";
    verify.addEventListener("click", () => this._applyLibraryConfiguration());

    // ── BBT JSON Export ──
    const importSection = containerEl.createDiv({ cls: "pf-setup-import" });
    importSection.createEl("h4", {
      text: t("setup_bbt_title") || "BBT JSON Export",
    });
    const vp = (this.app.vault.adapter as any).basePath as string;
    const paths = require("./services/runtime-paths").resolveVaultPaths(vp);
    importSection.createEl("p", {
      cls: "pf-setup-form-intro",
      text:
        t("setup_bbt_desc") ||
        "Export your Zotero library as Better BibTeX JSON into the folder below. Enable 'Keep updated' for automatic re-exports.",
    });
    // Exports path
    const pathRow = importSection.createDiv({ cls: "pf-setup-path-row" });
    pathRow.createEl("span", {
      cls: "pf-setup-path-label",
      text: t("setup_bbt_path") || "Exports folder:",
    });
    pathRow.createEl("code", {
      cls: "pf-setup-path-value",
      text: paths.exportsDir,
    });
    const copyBtn = pathRow.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: t("setup_bbt_copy") || "Copy",
    });
    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(paths.exportsDir);
      new Notice(t("setup_bbt_copied") || "Path copied");
    });

    // Expandable guide
    const guide = importSection.createEl("details", { cls: "pf-setup-guide" });
    guide.createEl("summary", {
      cls: "pf-setup-guide-summary",
      text: t("setup_bbt_guide") || "How to export from Zotero \u2192",
    });
    const guideBody = guide.createDiv({ cls: "pf-setup-guide-body" });
    const base =
      "https://raw.githubusercontent.com/LLLin000/PaperForge/master/docs/help/images";
    const steps = [
      {
        img: "bbt-plugin-installed.jpg",
        title: t("setup_bbt_step1") || "1. Install Better BibTeX",
        desc:
          t("setup_bbt_step1_desc") ||
          "In Zotero, go to Tools \u2192 Add-ons, search for Better BibTeX and install it. If you cannot find it, download from: https://github.com/retorquere/zotero-better-bibtex/releases/tag/v9.0.50",
      },
      {
        img: "bbt-export-dialog.jpg",
        title: t("setup_bbt_step2") || "2. Export with auto-update",
        desc:
          t("setup_bbt_step2_desc") ||
          "Right-click your library or collection \u2192 Export Library\u2026 \u2192 choose 'Better BibTeX JSON' format. Check 'Keep updated'.",
      },
      {
        img: "bbt-save-dialog.jpg",
        title: t("setup_bbt_step3") || "3. Save to exports folder",
        desc:
          t("setup_bbt_step3_desc") ||
          "Point the export destination to the folder above. Once saved, click 'Detect' below.",
      },
    ];
    for (const step of steps) {
      const entry = guideBody.createDiv({ cls: "pf-setup-guide-step" });
      entry.createEl("strong", { text: step.title });
      entry.createEl("p", { text: step.desc });
      const img = entry.createEl("img", {
        attr: {
          src: base + "/" + step.img,
          alt: step.title,
          loading: "lazy",
          onerror: "this.style.display='none'",
        },
      });
      img.addClass("pf-setup-guide-img");
    }
    const detectRow = importSection.createDiv({ cls: "pf-setup-detect-row" });
    const detectStatus = detectRow.createEl("span", {
      cls: "pf-setup-detect-status",
    });
    const nav = containerEl.createDiv({ cls: "pf-setup-nav" });

    // Shared: update Continue from BBT file state
    const _refreshBbtStatus = () => {
      try {
        if (!fs.existsSync(paths.exportsDir))
          fs.mkdirSync(paths.exportsDir, { recursive: true });
        const files = fs
          .readdirSync(paths.exportsDir)
          .filter((f: string) => f.endsWith(".json"));
        if (files.length === 0) {
          detectStatus.setText(
            t("setup_bbt_no_files") || "No JSON files found."
          );
        } else {
          detectStatus.setText(
            "\u2713 " + (t("setup_bbt_found") || "Found: ") + files.join(", ")
          );
        }
        const contBtn = nav.querySelector(
          ".pf-action-btn:last-child"
        ) as HTMLButtonElement | null;
        if (contBtn) {
          const shouldDisable =
            files.length === 0 ||
            env.user_state !== "ready" ||
            this._setupOperation === "running";
          contBtn.disabled = shouldDisable;
          contBtn.classList.toggle("pf-action-btn--disabled", shouldDisable);
        }
      } catch {
        /* ignore */
      }
    };

    detectRow
      .createEl("button", {
        cls: "pf-btn pf-btn-primary",
        text: t("setup_bbt_detect") || "Detect",
      })
      .addEventListener("click", _refreshBbtStatus);

    // ── Navigation (at the very bottom) ──

    renderActionButton(nav, {
      label: t("setup_nav_back"),
      onClick: () => {
        this._setupFeedback = null;
        this._setupStage = 1;
        this.display();
      },
    });
    renderActionButton(nav, {
      label: t("setup_nav_continue"),
      disabled: true,
      onClick: () => {
        this._setupFeedback = null;
        this._setupStage = 3;
        this.display();
      },
    });

    // Auto-run after nav buttons exist
    _refreshBbtStatus();
  }

  /** #173 corrective: explicit, user-mediated SecretStorage → keyring
   *  migration.  Reads each known legacy id once, stores via `auth set
   *  --stdin`, verifies, then clears the old value. */
  private async _migrateLegacyCredentials(
    btn: HTMLButtonElement
  ): Promise<void> {
    const vaultPath = this._getVaultBasePath();
    const py = this._resolveRuntimeCommand(vaultPath);
    if (!py || !vaultPath) {
      new Notice("Runtime not ready — cannot migrate credentials");
      return;
    }
    const { migrateLegacySecret, isAllowlistedCommand: _unused } =
      await import("./services/secret-storage");
    void _unused;
    const deps = {
      spawn: (
        command: string,
        args: string[],
        opts: {
          cwd: string;
          env: Record<string, string | undefined>;
          windowsHide: boolean;
          stdio: string[];
        }
      ) => spawn(command, args, opts as never),
      pythonPath: py.path,
      pythonArgs: py.args,
      vaultPath,
      env: paperforgeEnrichedEnv(),
    };
    btn.disabled = true;
    const results: string[] = [];
    for (const kind of ["ocr", "embedding"] as const) {
      const r = await migrateLegacySecret(
        kind,
        (
          this.app as unknown as {
            secretStorage?: {
              getSecret(id: string): Promise<string | null>;
              setSecret(id: string, s: string): Promise<void>;
            };
          }
        ).secretStorage,
        deps,
        // #173 corrective: real old embedding secrets live under the
        // profile-hashed v2 id computed from the current endpoint/model.
        {
          baseUrl: this.plugin.settings.vector_db_api_base ?? "",
          model: this.plugin.settings.vector_db_api_model ?? "",
        }
      );
      if (r.migrated.length) results.push(`${kind}: migrated`);
      for (const w of r.warnings) results.push(w);
    }
    btn.disabled = false;
    if (results.length === 0) {
      new Notice("No legacy credentials found in SecretStorage");
    } else {
      results.forEach((line) => new Notice(line, 6000));
    }
    this._refreshVectorDbCredentialStatus();
    this._refreshAllReadModels();
  }

  private _refreshVectorDbCredentialStatus(): void {
    // #173/C1: presence comes from the credential authority (`auth status`),
    // never from SecretStorage or settings flags.
    const vp = this._getVaultBasePath();
    if (!vp) return;
    void queryEmbeddingCredentialStatus(vp, this.plugin.settings)
      .then((available) => {
        if (available === this.plugin.settings._vector_db_configured) return;
        this.plugin.settings._vector_db_configured = available;
        void this.plugin.saveSettings();
      })
      .catch(() => undefined);
  }

  private async _storeVectorDbCredential(value: string): Promise<boolean> {
    // #173/C1: durable secrets go to the credential authority via
    // `auth set embedding --stdin` — never SecretStorage, .env, or data.json.
    const saved = await this._authSetSecret("embedding", value);
    if (!saved) return false;
    this.plugin.settings._vector_db_configured = true;
    this.plugin.settings.vector_db_api_key = "";
    this.plugin.settings._migration_warnings = Array.isArray(
      this.plugin.settings._migration_warnings
    )
      ? this.plugin.settings._migration_warnings.filter(
          (key) => key !== "vector_db_api_key"
        )
      : [];
    await this.plugin.saveSettings();
    this.display();
    return true;
  }

  private async _storeSetupSecret(
    secretId: "paddleocr-api-key" | "vector-db-api-key",
    value: string
  ): Promise<boolean> {
    if (secretId === "vector-db-api-key")
      return this._storeVectorDbCredential(value);
    if (!value) return false;
    const saved = await this._authSetSecret("ocr", value);
    if (!saved) return false;
    this.plugin.settings._paddleocr_configured = true;
    this.plugin.settings.paddleocr_api_key = "";
    await this.plugin.saveSettings();
    return true;
  }

  /** #173/C1: `paperforge auth set <kind> --stdin` — the secret travels only
   *  via child stdin, never argv, env, files, or settings. */
  private _authSetSecret(
    kind: "ocr" | "embedding",
    value: string
  ): Promise<boolean> {
    const vp = this._getVaultBasePath();
    const py = this._resolveRuntimeCommand(vp);
    if (!py || !value) return Promise.resolve(false);
    return new Promise((resolvePromise) => {
      const child = spawn(
        py.path,
        [
          ...py.args,
          "-m",
          "paperforge",
          "--vault",
          vp,
          "auth",
          "set",
          kind,
          "--stdin",
          "--json",
        ],
        {
          cwd: vp,
          windowsHide: true,
          stdio: ["pipe", "pipe", "pipe"],
          // #173 corrective: never inherit credential env from the desktop
          // process — the child resolves through the keyring.
          env: paperforgeEnrichedEnv(),
        }
      );
      let stdout = "";
      child.stdout.on("data", (d) => (stdout += String(d)));
      child.on("error", () => resolvePromise(false));
      child.on("close", (code: number | null) => {
        try {
          const parsed = JSON.parse(stdout) as { ok?: boolean };
          resolvePromise(code === 0 && parsed?.ok === true);
        } catch {
          resolvePromise(false);
        }
      });
      child.stdin.write(value);
      child.stdin.end();
    });
  }

  _renderSetupStageOptionals(containerEl: HTMLElement): void {
    containerEl.createEl("h3", { text: t("setup_optionals_title") });
    containerEl.createEl("p", { text: t("setup_optionals_desc") });
    const optionals = [
      { id: "ocr", label: t("cc_module_ocr"), desc: t("setup_opt_ocr_desc") },
      {
        id: "memory",
        label: t("cc_module_memory"),
        desc: t("setup_opt_memory_desc"),
      },
      {
        id: "agent",
        label: t("cc_module_agent"),
        desc: t("setup_opt_agent_desc"),
      },
    ];
    for (const opt of optionals) {
      const row = containerEl.createDiv({ cls: "pf-setup-optional" });
      const checkbox = row.createEl("input", {
        attr: { type: "checkbox", id: "pf-setup-opt-" + opt.id },
      }) as HTMLInputElement;
      checkbox.checked = this._setupOptionals[opt.id];
      checkbox.addEventListener("change", () => {
        this._setupOptionals[opt.id] = checkbox.checked;
        this.display();
      });
      const configured =
        opt.id === "ocr"
          ? !!this.plugin.settings._paddleocr_configured
          : opt.id === "memory"
            ? !!this.plugin.settings._vector_db_configured
            : true;
      const copy = row.createDiv({ cls: "pf-setup-optional-copy" });
      copy.createEl("label", {
        attr: { for: "pf-setup-opt-" + opt.id },
        text: opt.label,
        cls: "pf-setup-optional-label",
      });
      copy.createEl("div", {
        text: opt.desc,
        cls: "pf-setup-optional-desc",
      });
      const status = copy.createEl("span", {
        cls: "pf-setup-optional-state",
        text: configured ? t("config_configured") : t("config_not_configured"),
      });
      if (!checkbox.checked) continue;

      const config = row.createDiv({ cls: "pf-setup-optional-config" });
      if (opt.id === "ocr") {
        config.createEl("label", { text: t("field_paddleocr") });
        config.createEl("p", {
          cls: "caption",
          text: t("ocr_privacy_warning"),
        });
        const key = config.createEl("input", {
          cls: "pf-setup-input",
          attr: {
            type: "password",
            autocomplete: "off",
            placeholder: this.plugin.settings._paddleocr_configured
              ? "••••"
              : t("field_paddleocr"),
          },
        }) as HTMLInputElement;
        const save = config.createEl("button", {
          cls: "pf-setup-verify",
          text: t("config_save"),
          attr: { type: "button" },
        });
        save.addEventListener("click", () => {
          void this._storeSetupSecret("paddleocr-api-key", key.value).then(
            (saved) => {
              status.setText(
                saved
                  ? t("setup_optional_saved")
                  : t("setup_optional_save_failed")
              );
              if (saved) key.value = "";
            }
          );
        });
      } else if (opt.id === "memory") {
        config.createEl("label", { text: t("feat_openai_key") });
        config.createEl("p", {
          cls: "caption",
          text: t("feat_openai_key_desc"),
        });
        const key = config.createEl("input", {
          cls: "pf-setup-input",
          attr: {
            type: "password",
            autocomplete: "off",
            placeholder: this.plugin.settings._vector_db_configured
              ? "••••"
              : "sk-...",
          },
        }) as HTMLInputElement;
        config.createEl("label", { text: t("feat_api_model") });
        const model = config.createEl("input", {
          cls: "pf-setup-input",
          attr: {
            type: "text",
            placeholder:
              this.plugin.settings.vector_db_api_model ||
              "text-embedding-3-small",
          },
        }) as HTMLInputElement;
        model.addEventListener("change", () => {
          this.plugin.settings.vector_db_api_model = model.value.trim();
          void this.plugin.saveSettings();
          this._refreshVectorDbCredentialStatus();
        });
        config.createEl("label", { text: t("feat_api_base_url") });
        const base = config.createEl("input", {
          cls: "pf-setup-input",
          attr: {
            type: "text",
            placeholder:
              this.plugin.settings.vector_db_api_base ||
              "https://api.openai.com/v1",
          },
        }) as HTMLInputElement;
        base.addEventListener("change", () => {
          this.plugin.settings.vector_db_api_base = base.value.trim();
          void this.plugin.saveSettings();
          this._refreshVectorDbCredentialStatus();
        });
        const save = config.createEl("button", {
          cls: "pf-setup-verify",
          text: t("config_save"),
          attr: { type: "button" },
        });
        save.addEventListener("click", () => {
          void this._storeSetupSecret("vector-db-api-key", key.value).then(
            (saved) => {
              status.setText(
                saved
                  ? t("setup_optional_saved")
                  : t("setup_optional_save_failed")
              );
              if (saved) key.value = "";
            }
          );
        });
      } else {
        config.createEl("label", { text: t("feat_agent_platform") });
        config.createEl("p", {
          cls: "caption",
          text: t("feat_agent_platform_desc"),
        });
        const select = config.createEl("select") as HTMLSelectElement;
        const setupPlatformLabels: Record<string, string> = {
          opencode: "OpenCode",
          claude: "Claude Code",
          codex: "Codex",
          cursor: "Cursor",
          windsurf: "Windsurf",
          github_copilot: "GitHub Copilot",
          gemini: "Gemini CLI",
        };
        const setupChoices = this.plugin.agentPlatformChoices.length
          ? this.plugin.agentPlatformChoices
          : Object.keys(setupPlatformLabels);
        for (const value of setupChoices) {
          const option = select.createEl("option", {
            text: setupPlatformLabels[value] ?? value,
            attr: { value },
          }) as HTMLOptionElement;
          option.selected = value === this.plugin.settings.agent_platform;
        }
        select.addEventListener("change", () => {
          this.plugin.settings.agent_platform = select.value;
          // #142 / C0: mutation through the typed config command.
          void configSet(
            this._getVaultBasePath(),
            "agent_platform",
            select.value,
            this.plugin.settings
          ).catch(
            (e) =>
              new Notice(
                `PaperForge: config set agent_platform failed: ${String(e)}`
              )
          );
          void this.plugin.saveSettings();
          status.setText(t("setup_optional_saved"));
        });
      }
    }
    const nav = containerEl.createDiv({ cls: "pf-setup-nav" });
    renderActionButton(nav, {
      label: t("setup_nav_back"),
      onClick: () => {
        this._setupStage = 2;
        this.display();
      },
    });
    renderActionButton(nav, {
      label: t("setup_nav_continue"),
      onClick: () => this._refreshSetupReadiness(),
    });
  }

  private _refreshSetupReadiness(): void {
    this._setupStage = 4;
    for (const mod of ["installation", "library"] as const) {
      this._attemptedProbes.add(mod);
      this._probeModule(mod);
    }
    this.display();
  }

  _renderSetupStageReview(containerEl: HTMLElement): void {
    containerEl.createEl("h3", { text: t("setup_review_title") });
    const foundation = this._capabilityState?.installation;
    const library = this._capabilityState?.library;
    const foundationReady = foundation?.user_state === "ready";
    const libraryReady = library?.user_state === "ready";
    const checking =
      foundation?.user_state === "checking" ||
      library?.user_state === "checking";
    containerEl.createEl("p", {
      text: foundationReady
        ? t("setup_ready")
        : checking
          ? t("setup_review_checking")
          : t("cc_consequence_setup_required"),
      cls: foundationReady ? "pf-setup-ok" : "pf-setup-warn",
    });
    containerEl.createEl("p", {
      text: libraryReady
        ? t("setup_library_ready")
        : checking
          ? t("setup_review_checking")
          : t("cc_consequence_setup_required"),
      cls: libraryReady ? "pf-setup-ok" : "pf-setup-warn",
    });
    const selected = Object.entries(this._setupOptionals)
      .filter(([, enabled]) => enabled)
      .map(([module]) => this._getUserModuleName(module));
    containerEl.createEl("p", {
      text:
        selected.length > 0
          ? t("setup_review_selected") + selected.join(", ")
          : t("setup_no_optionals"),
    });
    const nav = containerEl.createDiv({ cls: "pf-setup-nav" });
    renderActionButton(nav, {
      label: t("setup_nav_back"),
      onClick: () => {
        this._setupStage = 3;
        this.display();
      },
    });
    if (!foundationReady || !libraryReady) {
      renderActionButton(nav, {
        label: t("setup_review_recheck"),
        disabled: checking,
        onClick: () => this._refreshSetupReadiness(),
      });
    }
    renderActionButton(nav, {
      label: t("setup_nav_complete"),
      disabled: !foundationReady || !libraryReady,
      onClick: () => this._completeSetup(),
    });
    if (!foundationReady || !libraryReady) {
      containerEl.createEl("p", {
        text: checking
          ? t("setup_review_checking")
          : t("setup_incomplete_warn"),
        cls: "pf-setup-warn",
      });
    }
  }

  /** #87: Complete setup — persist and transition to normal operation. */
  _completeSetup(): void {
    this.plugin.settings._setup_complete = true;
    this.plugin.saveSettings().then(() => this.display());
  }

  _restoreNavMemory(): void {
    const saved = this.plugin.settings._navMemory as
      | { destination?: string; module?: string }
      | undefined;
    if (
      saved?.destination &&
      ["overview", "help"].includes(saved.destination)
    ) {
      this.activeTab = saved.destination;
      this._navMemory = { destination: saved.destination };
      // Only clear _focusTargetId for genuine session restore (no target set).
      // If _handleCardNavigation set it just before display(), keep it alive.
      if (!this._focusTargetId) {
        this._focusTargetId = null;
        this._detailReturn = null;
        this._setupView = "overview";
      }
    }
  }

  /** RC UX Seam P1: closing Settings ends the session — the next open must
   * resume the Setup Journey at the stage the user left. */
  hide(): void {
    this._setupJourneyDismissedForSession = false;
    super.hide();
  }
}
