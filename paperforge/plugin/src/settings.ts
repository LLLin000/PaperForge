import { PluginSettingTab, App, Setting, Notice, setTooltip } from "obsidian";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { execFile, execFileSync, spawn, exec } from "child_process";
import { t, setLanguage } from "./i18n";
import {
  PaperForgeSettings,
  ProbeEnvelope,
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
import {
  getVectorRuntime,
  getRuntimeHealth,
  getMemoryStatusText,
  getVectorStatusText,
} from "./services/memory-state";

import {
  PaperForgeOcrPrivacyModal,
  PaperForgeSetupModal,
  PaperForgeConfirmModal,
  PaperForgeIssueDraftModal,
  buildRedactedDraft,
  checkOrphanState,
} from "./views/modals";
import {
  ManagedRuntime,
  runtimeActionsForHealth,
  resolveRuntimeCommand,
  type RuntimeHealth,
  type RuntimeUiAction,
} from "./services/managed-runtime";
import { getDisclosureState, toggleDisclosureState } from "./utils/disclosure";
import {
  resolveCredentialEnv,
  stripCredentialEnv,
  type PluginForSecrets,
} from "./services/secret-storage";
import { processProgressChunk } from "./services/progress-parser";

// ── SecretStorage credential adapter (Issue #79) ──

function asPluginForSecrets(
  app: any
): import("./services/secret-storage").PluginForSecrets {
  return {
    app: { secretStorage: (app as any).secretStorage },
    saveData: async () => {},
  };
}

// ── Interface ──

interface ISettingPlugin {
  settings: PaperForgeSettings;
  saveSettings(): Promise<void>;
  loadSettings(): Promise<void>;
  manifest: { version: string };
  readPaperforgeJson(): Record<string, string>;
  savePaperforgeJson(pc: Record<string, string>): void;
  getManagedRuntime?(): ManagedRuntime;
  _autoSyncRunning?: boolean;
  _lastSyncTime?: string | null;
  _memoryStatusText?: string | null;
  _embedProcess?: unknown;
  _embedProgress?: { current: number; total: number; key: string };
  _embedStderr?: string;
  _embedBuffer?: string;
  _ocrProcess?: unknown;
  _ocrProgress?: { current: number; total: number; key: string };
  _ocrBuffer?: string;
  _ocrWasStopped?: boolean;
  _embedPollInterval?: ReturnType<typeof setInterval> | null;
  _embedPolling?: boolean;
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
  /** Currently selected module in the detail view. */
  _selectedDetailModule: string = "";
  /** Focus target id after re-render. */
  _focusTargetId: string | null = null;
  /** AbortController for in-flight runtime ensure/install. */
  private _runtimeAbortController: AbortController | null = null;
  /** Cached ManagedRuntime singleton (rebuilt per display() on path change). */
  private _managedRuntime: ManagedRuntime | null = null;
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

  /** Reload path config from paperforge.json */
  _refreshPfConfig() {
    this._pfConfig = this.plugin.readPaperforgeJson();
  }

  display() {
    this._displayInProgress = true;
    const { containerEl } = this;
    containerEl.empty();
    this._refreshPfConfig();
    this._restoreNavMemory();
    this._initCapabilityState();
    this._applyStaleTolerance();

    // #87: Show Setup Journey on first open (never reverse once complete)
    // #87: Only show Setup Journey for first-time users (explicitly false).
    // Existing installations (undefined) skip the journey.
    if (this.plugin.settings._setup_complete === false) {
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
      (this.app as any).workspace.getLeaf().setViewState({
        type: "paperforge-ocr-workspace",
      } as any);
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

    // ── Control Center (Issue #76) ──
    this._renderControlCenter(containerEl);

    // Auto-probe modules that are unknown or stale once per session
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

  /** Ensure ManagedRuntime singleton is initialized for the current machine. */
  private _ensureManagedRuntime(): ManagedRuntime {
    if (this._managedRuntime) return this._managedRuntime;
    this._managedRuntime =
      this.plugin.getManagedRuntime?.() ??
      new ManagedRuntime({ version: this.plugin.manifest.version });
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
    // 2. Fall back to managed runtime detection
    const run = resolveRuntimeCommand(this._ensureManagedRuntime().current());
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
      row.createEl("span", { cls: statusClass, text: status });
      row.createEl("span", { cls: "pf-config-value", text: value });
    };

    // Version
    addCheck(
      t("foundation_version"),
      "✓",
      this.plugin.manifest.version,
      "pf-status-ok"
    );

    // Python check
    const pythonPath = this.plugin.settings.python_path || "python";
    addCheck(t("foundation_python"), "—", pythonPath, "pf-status-checking");

    // Vault structure
    const vp = (this.app.vault.adapter as any).basePath as string;
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

    // API keys
    const hasPaddle = !!this.plugin.settings.paddleocr_api_key;
    const hasOpenai =
      !!this.plugin.settings.vector_db_api_key || !!process.env.OPENAI_API_KEY;
    addCheck(
      t("foundation_paddle_key"),
      hasPaddle ? "✓" : "✗",
      hasPaddle ? "Configured" : t("foundation_paddle_missing"),
      hasPaddle ? "pf-status-ok" : "pf-status-error"
    );
    addCheck(
      t("foundation_openai_key"),
      hasOpenai ? "✓" : "✗",
      hasOpenai ? "Configured" : t("foundation_openai_missing"),
      hasOpenai ? "pf-status-ok" : "pf-status-error"
    );

    // Git
    const { execSync } = require("child_process");
    try {
      execSync("git --version", { timeout: 3000 });
      addCheck(t("foundation_git"), "✓", "Installed", "pf-status-ok");
    } catch {
      addCheck(
        t("foundation_git"),
        "✗",
        t("foundation_git_missing"),
        "pf-status-error"
      );
    }

    // Obsidian version check
    const minVersion = "1.11.4";
    const currentVersion = "1.11.4";
    const obsidianOk = true; // Simplified check
    addCheck(
      t("foundation_obsidian"),
      obsidianOk ? "✓" : "✗",
      obsidianOk ? `≥${minVersion}` : t("foundation_obsidian_old"),
      obsidianOk ? "pf-status-ok" : "pf-status-error"
    );

    // Python packages
    addCheck(
      t("foundation_python_packages"),
      "—",
      t("foundation_python_packages_checking"),
      "pf-status-checking"
    );

    // Python async check
    const { exec } = require("child_process");
    exec(`"${pythonPath}" --version`, { timeout: 5000 }, (err: any) => {
      const row = checks.children[1] as HTMLElement;
      if (row) {
        const statusEl = row.querySelector(".pf-status-checking");
        if (statusEl) {
          statusEl.textContent = err ? "✗" : "✓";
          statusEl.className = err ? "pf-status-error" : "pf-status-ok";
        }
      }
    });

    // Python packages async check
    exec(
      `"${pythonPath}" -c "import paddleocr; import openai; import sqlite3; print('ok')"`,
      { timeout: 10000 },
      (err: any) => {
        const row = checks.children[checks.children.length - 1] as HTMLElement;
        if (row) {
          const statusEl = row.querySelector(".pf-status-checking");
          if (statusEl) {
            statusEl.textContent = err ? "✗" : "✓";
            statusEl.className = err ? "pf-status-error" : "pf-status-ok";
          }
        }
      }
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
            .onClick(() => {
              new Notice(t("foundation_running_setup"));
              // Trigger setup wizard
              this.plugin.settings._setup_complete = false;
              this.plugin.saveSettings();
              this.display();
            })
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
          .onClick(() => {
            new PaperForgeSetupModal(this.app, this.plugin, () => {
              this._probeModule("installation");
              this._probeModule("help");
            }).open();
          })
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
    // Re-probe stale modules before rendering detail
    if (this._selectedDetailModule !== "help") {
      const env = this._capabilityState?.[this._selectedDetailModule];
      if (
        env?.user_state === "detection_failed" &&
        env.reason.code.endsWith(".stale")
      ) {
        this._probeModule(this._selectedDetailModule as CapabilityModule);
      }
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
      onChange: () => {
        new PaperForgeSetupModal(this.app, this.plugin, () => {
          this.plugin.savePaperforgeJson({
            zotero_data_dir: this.plugin.settings.zotero_data_dir,
          });
          this._probeModule("library");
        }).open();
      },
    });
  }

  /** Render the OCR detail view (Issue #96: 3-state UX). */
  _renderOcrDetail(containerEl: HTMLElement): void {
    this._renderModuleDetailShell(containerEl, "ocr");
    const env = this._capabilityState?.ocr ?? createUnknownEnvelope("ocr");
    const body = containerEl.createDiv({ cls: "pf-module-body" });
    body.createEl("h3", { text: t("md_ocr_status") });

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
      // Stop button (ghost style)
      const process = this.plugin._ocrProcess as {
        stdin?: { write: (_: string) => boolean };
        kill?: (_: string) => void;
      } | null;
      if (process) {
        const stop = card.createEl("button", {
          cls: "pf-action-btn mod-warning",
          text: t("ocr_stop_batch"),
        });
        stop.addEventListener("click", () => {
          if (process.stdin?.write) {
            process.stdin.write("PAPERFORGE_STOP\n");
            this.plugin._ocrWasStopped = true;
          } else {
            process.kill?.("SIGINT");
          }
        });
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
      renderStatusBadge(body, "ready");
      const readyText = pipelineVersion
        ? t("ocr_state_ready")
            .replace("{count}", String(env.action?.primary?.scope_count ?? ""))
            .replace("{version}", pipelineVersion)
        : t("ocr_state_ready_no_version").replace(
            "{count}",
            String(env.action?.primary?.scope_count ?? "")
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
  }
  /** Render the Memory detail view (Issue #78). */
  _renderAgentDetail(containerEl: HTMLElement): void {
    this._renderModuleDetailShell(containerEl, "agent");
    const body = containerEl.createDiv({ cls: "pf-module-body" });
    body.createEl("h3", { text: t("md_agent_integration") });
    body.createEl("p", {
      text: t("md_agent_placeholder"),
      cls: "setting-item-description",
    });

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
      for (const [value, label] of Object.entries(platforms)) {
        const option = select.createEl("option", {
          text: label,
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
          this.plugin.savePaperforgeJson({ agent_platform: value });
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
    this._renderModuleDetailShell(containerEl, "memory");
    const env =
      this._capabilityState?.memory ?? createUnknownEnvelope("memory");
    const body = containerEl.createDiv({ cls: "pf-module-body" });
    const reasonCode = env.reason?.code ?? "";
    const isRunning = env.activity_state === "running";

    // ── Badge + description ──
    if (isRunning && env.user_state === "ready") {
      renderStatusBadge(body, "ready");
      body.createEl("p", {
        text: env.activity_label ?? t("cc_activity_running"),
        cls: "pf-status-ok",
      });
    } else if (reasonCode === "memory.disabled") {
      renderStatusBadge(body, "not_enabled");
      body.createEl("p", {
        text: t("sr_state_disabled"),
        cls: "setting-item-description",
      });
    } else if (reasonCode === "memory.db_missing") {
      renderStatusBadge(body, "action_required");
      body.createEl("p", {
        text: t("sr_state_db_missing"),
        cls: "setting-item-description",
      });
    } else if (reasonCode === "memory.backend_upgrade_available") {
      renderStatusBadge(body, "action_required");
      body.createEl("p", {
        text: t("sr_state_upgrade_available"),
        cls: "setting-item-description",
      });
    } else if (reasonCode === "memory.vector_build_failed") {
      renderStatusBadge(body, "action_required");
      body.createEl("p", {
        text: t("sr_state_build_failed"),
        cls: "setting-item-description",
      });
    } else if (reasonCode === "memory.schema_stale") {
      renderStatusBadge(body, "action_required");
      body.createEl("p", {
        text: env.reason.text,
        cls: "setting-item-description",
      });
    } else if (env.user_state === "ready") {
      renderStatusBadge(body, "ready");
      body.createEl("p", {
        text: t("md_retrieval_ready"),
        cls: "pf-status-ok",
      });
    }

    // ── Primary action button ──
    if (reasonCode === "memory.disabled") {
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
          this.plugin.saveSettings().then(() => this._probeModule("memory"));
        },
      });
    } else if (reasonCode === "memory.db_missing") {
      renderActionButton(body, {
        label: t("sr_action_build") || "Build Index",
        onClick: () => this._dispatchMemoryBuild("build"),
      });
    } else if (reasonCode === "memory.backend_upgrade_available") {
      renderActionButton(body, {
        label: t("sr_action_upgrade") || "Upgrade",
        onClick: () => this._dispatchModuleAction("memory", env),
      });
    } else if (
      reasonCode === "memory.vector_build_failed" ||
      reasonCode === "memory.schema_stale"
    ) {
      renderActionButton(body, {
        label: t("cc_action_rebuild_derived") || "Rebuild Index",
        onClick: () => this._dispatchMemoryBuild("embed"),
      });
    } else if (
      env.action?.primary &&
      env.user_state !== "ready" &&
      env.user_state !== "not_enabled"
    ) {
      // ── Generic fallback: any actionable state with a primary action ──
      const actionLabel =
        env.action.primary.label || t("cc_action_rebuild_derived") || "Fix";
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

    // ── Impact box (when action needed) ──
    if (reasonCode !== "ready" && reasonCode !== "memory.disabled") {
      const impact = body.createDiv({ cls: "pf-sr-impact-box" });
      impact.createEl("strong", {
        text: t("cc_badge_action_required") || "Action Required",
      });
      impact.createEl("p", {
        text:
          reasonCode === "memory.db_missing"
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

    // ── Diagnostic details (collapsed) ──
    const details = body.createEl("details", { cls: "pf-sr-diagnostics" });
    details.createEl("summary", {
      text: t("cc_diagnostic_toggle") || "Diagnostic Details",
    });
    const diagBody = details.createDiv({ cls: "pf-sr-diagnostics-body" });
    diagBody.createEl("div", {
      text:
        "module: memory | state: " +
        env.capability_state +
        " | severity: " +
        env.severity +
        " | reason: " +
        reasonCode,
    });
  }
  /** Dispatch a backend action command through exact (verb, command) allowlist (Issue #78). */
  _dispatchModuleAction(mod: CapabilityModule, env: ProbeEnvelope): void {
    const primary = env.action?.primary;
    if (!primary) {
      this._probeModule(mod);
      return;
    }
    const verb = primary.verb;
    const cmd = primary.command ?? "";

    // Destructive confirmation -> accessible modal (Issue #80)
    if (primary.safety_class !== "safe" && primary.confirmation_required) {
      new PaperForgeConfirmModal(
        this.app,
        {
          title: primary.label,
          effectLabel:
            ((primary.replacement_facts || []).join("; ") ||
              primary.confirmation_prompt) ??
            "Proceed?",
        },
        () => {
          this._runAllowedDispatch(
            mod,
            primary.verb,
            primary.command ?? "",
            env
          );
        }
      ).open();
      return;
    }

    this._runAllowedDispatch(mod, primary.verb, primary.command ?? "", env);
  }

  private _runAllowedDispatch(
    mod: CapabilityModule,
    verb: string,
    cmd: string,
    env: ProbeEnvelope
  ): void {
    // Setup/set_config verbs → exact command allowlist
    if (
      (verb === "setup" || verb === "set_config") &&
      cmd === "paperforge setup"
    ) {
      if (
        mod === "installation" ||
        mod === "library" ||
        mod === "ocr" ||
        mod === "memory"
      ) {
        const probeMods: CapabilityModule[] = [mod];
        if (mod === "installation") {
          probeMods.push("help");
        }
        new PaperForgeSetupModal(this.app, this.plugin, () => {
          for (const m of probeMods) this._probeModule(m);
        }).open();
        return;
      }
    }

    // Probe verb → exact command match, directly re-probe without Notice
    if (verb === "probe" && cmd === "probe " + mod) {
      this._probeModule(mod);
      return;
    }

    // Exact (verb, command) allowlist per module
    if (mod === "installation") {
      // setup/set_config handled above
    } else if (mod === "library") {
      if (verb === "sync" && cmd === "paperforge sync") {
        this._runManualSync();
        return;
      }
      // setup/set_config handled above
    } else if (mod === "ocr") {
      if (verb === "run" && cmd === "paperforge ocr run") {
        this._dispatchOcrAction("run");
        return;
      }
      if (
        verb === "rebuild_derived" &&
        cmd === "paperforge ocr rebuild --all"
      ) {
        this._dispatchOcrAction("rebuild");
        return;
      }
      if (verb === "redo" && cmd === "paperforge ocr redo") {
        this._dispatchOcrAction("redo");
        return;
      }
      if (verb === "investigate") {
        if (cmd === "paperforge ocr issue-draft") {
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
        if (cmd === "paperforge ocr doctor") {
          this._callPython(["ocr", "doctor"], {
            timeout: 30000,
            onClose: (_code: number | null) => {
              this._probeModule("ocr");
              this.display();
            },
          });
          return;
        }
        if (cmd === "paperforge ocr list --json") {
          this._callPython(["ocr", "list", "--json"], {
            timeout: 30000,
            onClose: (_code: number | null) => {
              this._probeModule("ocr");
              this.display();
            },
          });
          return;
        }
      }
      // setup/set_config handled above
    } else if (mod === "memory") {
      if (
        (verb === "run" || verb === "rebuild_index") &&
        cmd === "paperforge memory build"
      ) {
        this._dispatchMemoryBuild("build");
        return;
      }
      if (
        verb === "rebuild_index" &&
        cmd === "paperforge embed build --force"
      ) {
        this._dispatchMemoryBuild("embed");
        return;
      }
      if (
        verb === "restore_backup" &&
        cmd === "paperforge memory restore-backup"
      ) {
        this._callPython(["memory", "restore-backup"], {
          timeout: 30000,
          onClose: (_code: number | null) => {
            this._probeModule("memory");
            this.display();
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
  } /** Dispatch OCR action with exact CLI args, progress tracking, cooperative stop (Issue #78). */
  _dispatchOcrAction(mode: "run" | "rebuild" | "redo"): void {
    const vp = (this.app.vault.adapter as any).basePath as string;
    const resolved = this._resolveRuntimeCommand(vp);
    if (!resolved) {
      new Notice(t("runtime_not_available") || "No Python runtime available");
      return;
    }

    // Map mode to exact CLI args
    const cliArgs: string[] =
      mode === "run"
        ? ["ocr", "run"]
        : mode === "rebuild"
          ? ["ocr", "rebuild", "--all"]
          : ["ocr", "redo"];
    const labelMap: Record<string, string> = {
      run: "Running OCR…",
      rebuild: "Rebuilding OCR derived artifacts…",
      redo: "Running OCR redo…",
    };

    // Set envelope activity overlay without changing capability/severity/reason
    const envelopes = this._capabilityState ?? {};
    if (envelopes["ocr"]) {
      envelopes["ocr"].activity_state = "running";
      envelopes["ocr"].activity_label = labelMap[mode] || "Running…";
      envelopes["ocr"].activity_progress = { current: 0, total: 1 };
    }
    this.plugin._ocrBuffer = "";
    this.plugin._ocrProgress = { current: 0, total: 1, key: "" };
    this.plugin._ocrWasStopped = false;
    this.display();

    const child = this._callPython(cliArgs, {
      stream: true,
      onData: (data: unknown) => {
        const text =
          typeof data === "string"
            ? data
            : Buffer.isBuffer(data)
              ? data.toString("utf-8")
              : String(data);
        const { events, buffer } = processProgressChunk(
          text,
          this.plugin._ocrBuffer ?? ""
        );
        this.plugin._ocrBuffer = buffer;
        for (const ev of events) {
          if (ev.event === "START") {
            if (this.plugin._ocrProgress) {
              this.plugin._ocrProgress.total = ev.total || 1;
            }
            if (envelopes["ocr"]) {
              envelopes["ocr"].activity_progress = {
                current: 0,
                total: ev.total || 1,
              };
            }
          } else if (ev.event === "PROGRESS") {
            this.plugin._ocrProgress = {
              current: ev.current || 0,
              total: ev.total || 1,
              key: ev.key || "",
            };
            if (envelopes["ocr"]) {
              envelopes["ocr"].activity_progress = {
                current: ev.current || 0,
                total: ev.total || 1,
              };
            }
          }
        }
        this.display();
      },
      onError: (err: Error) => {
        this.plugin._ocrProcess = null;
        if (envelopes["ocr"]) {
          envelopes["ocr"].activity_state = "idle";
          envelopes["ocr"].activity_label = null;
          envelopes["ocr"].activity_progress = null;
        }
        new Notice(t("ocr_error_notice"), 8000);
        this._probeModule("ocr");
        this.display();
      },
      onClose: (code: number | null) => {
        this.plugin._ocrProcess = null;
        if (envelopes["ocr"]) {
          envelopes["ocr"].activity_state = "idle";
          envelopes["ocr"].activity_label = null;
          envelopes["ocr"].activity_progress = null;
        }
        if (code === 0) {
          new Notice(
            mode === "run"
              ? t("ocr_run_complete")
              : mode === "rebuild"
                ? t("ocr_rebuild_complete")
                : t("ocr_redo_complete")
          );
        } else if (code === 130 || this.plugin._ocrWasStopped) {
          this.plugin._ocrWasStopped = false;
          new Notice(t("ocr_stopped_notice"));
        } else {
          new Notice(t("ocr_failed_notice"), 8000);
        }
        // Terminal re-probe
        this._probeModule("ocr");
        this.display();
      },
    });
    this.plugin._ocrProcess = child;
  } /** Dispatch memory build: distinct build vs embed modes, overlay activity, terminal re-probe (Issue #78). */
  _dispatchMemoryBuild(kind: "build" | "embed"): void {
    const vp = (this.app.vault.adapter as any).basePath as string;
    // Set activity overlay on Memory
    const envelopes = this._capabilityState ?? {};
    if (envelopes["memory"]) {
      envelopes["memory"].activity_state = "running";
      envelopes["memory"].activity_label =
        kind === "embed" ? "Building vector index…" : "Building memory…";
    }
    this.display();

    const cliArgs =
      kind === "embed" ? ["embed", "build", "--force"] : ["memory", "build"];
    const label = kind === "embed" ? "Vector index" : "Memory";

    if (kind === "embed") {
      // Embed build: stream progress
      this.plugin._embedBuffer = "";
      this.plugin._embedProgress = { current: 0, total: 0, key: "" };
      const child = this._callPython(cliArgs, {
        stream: true,
        onData: (data: unknown) => {
          const text =
            typeof data === "string"
              ? data
              : Buffer.isBuffer(data)
                ? data.toString("utf-8")
                : String(data);
          const { events, buffer } = processProgressChunk(
            text,
            this.plugin._embedBuffer ?? ""
          );
          this.plugin._embedBuffer = buffer;
          for (const ev of events) {
            if (ev.event === "PROGRESS") {
              this.plugin._embedProgress = {
                current: ev.current || 0,
                total: ev.total || 0,
                key: ev.key || "",
              };
              if (envelopes["memory"]) {
                envelopes["memory"].activity_progress = {
                  current: ev.current || 0,
                  total: ev.total || 1,
                };
              }
            }
          }
          this.display();
        },
        onError: (err: Error) => {
          this.plugin._embedProcess = null;
          if (envelopes["memory"]) {
            envelopes["memory"].activity_state = "idle";
            envelopes["memory"].activity_label = null;
            envelopes["memory"].activity_progress = null;
          }
          new Notice(label + " build error: " + (err.message || err), 8000);
          this._probeModule("memory");
          this.display();
        },
        onClose: (code: number | null) => {
          this.plugin._embedProcess = null;
          if (envelopes["memory"]) {
            envelopes["memory"].activity_state = "idle";
            envelopes["memory"].activity_label = null;
            envelopes["memory"].activity_progress = null;
          }
          if (code === 0) {
            new Notice(label + " build complete.");
          } else {
            new Notice(
              label + " build failed with exit code " + (code ?? "?"),
              8000
            );
          }
          this._probeModule("memory");
          this.display();
        },
      });
      this.plugin._embedProcess = child;
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
            new Notice(label + " rebuild complete");
          } else {
            new Notice(
              label +
                " build failed" +
                (stderr ? ": " + stderr.slice(0, 120) : ""),
              8000
            );
          }
          this._probeModule("memory");
          this.display();
        },
      });
    }
  } /** Shared module detail shell for Library, OCR, and Memory (Issue #78). */
  /** Shared module detail shell for all five operational modules. */
  _renderModuleDetailShell(
    containerEl: HTMLElement,
    mod: CapabilityModule | "agent"
  ): void {
    containerEl.classList.add("pf-module-detail");
    const headingKey =
      mod === "agent" ? "agent_detail_heading" : mod + "_detail_heading";
    const headingId = "pf-" + mod + "-detail-heading";

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

    containerEl.createEl("h2", {
      cls: "pf-module-detail-heading",
      text: t(headingKey),
      attr: { id: headingId, tabindex: "-1" },
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
    header.createEl("span", {
      cls: "pf-module-summary-name",
      text: this._getUserModuleName(mod),
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
    if (primary && userState !== "ready" && mod !== "agent") {
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

  /** Render the Help tab (top-level destination with docs + release notes). */
  /** Help is task support and privacy-safe diagnostics, never a health module. */
  _renderHelpTab(containerEl: HTMLElement): void {
    // Eyebrow + Title + Lede
    containerEl.createEl("div", {
      cls: "pf-cc-eyebrow",
      text: t("help_eyebrow") || "help",
    });
    containerEl.createEl("h1", {
      cls: "pf-cc-title",
      text: t("help_title") || "Start with the task",
    });
    containerEl.createEl("p", {
      cls: "pf-cc-lede",
      text:
        t("help_lede") ||
        "Open the relevant module, or copy a diagnostic for support.",
    });

    // Task list — 4 task links (Library, OCR, Retrieval, Agent)
    const taskList = containerEl.createDiv({ cls: "pf-help-task-list" });
    const tasks = [
      ["library", t("help_library_task")],
      ["ocr", t("help_ocr_task")],
      ["memory", t("help_retrieval_task")],
      ["agent", t("help_agent_task")],
    ];
    for (const [mod, taskLabel] of tasks) {
      const btn = taskList.createEl("button", {
        cls: "pf-help-task-btn",
        text: taskLabel,
        attr: { "data-module": mod },
      });
      btn.addEventListener("click", () => {
        this._detailReturn = {
          tab: "help",
          selector: `.pf-help-task-btn[data-module="${mod}"]`,
        };
        this._handleCardNavigation(mod);
      });
    }

    // Copy diagnostic button
    containerEl
      .createEl("button", {
        cls: "pf-help-diagnostic-btn",
        text: t("help_copy") || "Copy diagnostic",
      })
      .addEventListener("click", () => this._buildAndCopyDiagnostic());
  }

  _execMemoryStatus(
    pythonPath: string,
    vp: string,
    callback: (text: string) => void
  ) {
    const _menv = paperforgeEnrichedEnv();
    exec(
      `"${pythonPath}" -m paperforge --vault "${vp}" memory status --json`,
      { encoding: "utf-8", timeout: 15000, env: _menv },
      (err, stdout) => {
        if (err) {
          callback("Status unavailable");
          return;
        }
        try {
          const data = JSON.parse(stdout);
          if (data.ok) {
            const s = data.data;
            const freshness = s.fresh ? "fresh" : "stale";
            callback(
              `Papers: ${s.paper_count_db} | ${freshness}${s.needs_rebuild ? " - needs rebuild" : ""}`
            );
          } else {
            callback("DB not found. Run paperforge memory build.");
          }
        } catch (e) {
          callback("Could not parse status.");
        }
      }
    );
  }

  _execEmbedStatus(
    pythonPath: string,
    vp: string,
    callback: (text: string) => void
  ) {
    const _eenv = paperforgeEnrichedEnv();
    exec(
      `"${pythonPath}" -m paperforge --vault "${vp}" embed status --json`,
      { encoding: "utf-8", timeout: 15000, env: _eenv },
      (err, stdout) => {
        if (err) {
          callback("Status unavailable");
          return;
        }
        try {
          const data = JSON.parse(stdout);
          if (data.ok) {
            callback(
              `Chunks: ${data.data.chunk_count} | ${data.data.model} | ${data.data.mode}`
            );
          } else {
            callback("Could not parse status.");
          }
        } catch (e) {
          callback("Could not parse status.");
        }
      }
    );
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
      buildTargetedEnv(
        asPluginForSecrets((this as any).app),
        opts.credentialType
      ).then((env) => {
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
  _renderMemoryStatusText(
    el: HTMLElement,
    text: string,
    extraInfo: string | null | undefined
  ) {
    el.innerHTML = "";
    el.createEl("span", { text: text, cls: "paperforge-memory-text" });

    if (extraInfo === "syncing") {
      el.createEl("span", {
        text: "Syncing...",
        cls: "paperforge-sync-status",
      });
    } else if (extraInfo) {
      el.createEl("span", { text: extraInfo, cls: "paperforge-sync-status" });
    }

    const rebuildBtn = el.createEl("button", {
      cls: "paperforge-rebuild-btn",
      text: t("feat_memory_rebuild_btn"),
    });
    rebuildBtn.title = "Rebuild memory database";
    rebuildBtn.onclick = () => {
      const vp = (this.app.vault.adapter as any).basePath as string;
      const py = this._resolveRuntimeCommand(vp);
      if (!py?.path) {
        new Notice(t("feat_no_python"));
        return;
      }
      console.log("[PaperForge] Rebuilding memory:", py.path);
      rebuildBtn.setText(t("feat_memory_rebuilding"));
      rebuildBtn.setAttr("disabled", "");
      this._callPython(["memory", "build"], {
        timeout: 60000,
        onClose: (code: number | null, stdout: string, stderr: string) => {
          console.log(
            "[PaperForge] memory build exit:",
            code ? "FAIL:" + code : "OK",
            (stdout || "").slice(0, 200),
            (stderr || "").slice(0, 200)
          );
          rebuildBtn.setText(t("feat_memory_rebuild_btn"));
          rebuildBtn.removeAttribute("disabled");
          if (code === 0) {
            new Notice(t("feat_memory_rebuild_done"));
          } else {
            new Notice(
              t("feat_memory_rebuild_failed") +
                (stderr ? " " + stderr.slice(0, 80) : "")
            );
          }
          this._memoryStatusText = getMemoryStatusText(vp);
          this._refreshSnapshots(vp);
        },
      });
    };

    const refreshBtn = el.createEl("button", {
      cls: "paperforge-refresh-btn",
      text: "\u21BB",
    });
    refreshBtn.title = "Sync now";
    refreshBtn.onclick = () => {
      this._memoryStatusText = null;
      this._runManualSync();
    };
  }

  _getBuildCommand(settings: PaperForgeSettings): string | null {
    const vp = (this.app.vault.adapter as any).basePath as string;
    const resolved = this._resolveRuntimeCommand(vp);
    if (!resolved) return null;
    return `"${resolved.path}" -m paperforge --vault "${vp}" sync`;
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
      this._renderMemoryStatusText(
        statusRow as HTMLElement,
        "Checking...",
        "syncing"
      );
    }

    this.plugin._autoSyncRunning = true;
    this._libraryRunning = true;
    this.display();
    this._callPython(["sync"], {
      timeout: 120000,
      onClose: (code: number | null) => {
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
        }
        // Re-probe library on every terminal outcome — pass exit code for sync failure detection
        this._probeModule("library", code ?? 1);
        this.display();
        this._refreshSnapshots(vp);
        checkOrphanState(this.app, this.plugin, vp);
      },
    });
  }

  _refreshSnapshots(vp: string) {
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
      (err, stdout, stderr) => {
        this._refreshPending = false;
        this._memoryStatusText = getMemoryStatusText(vp);
        this._embedStatusText = getVectorStatusText(vp);
        this.display();
      }
    );
  }

  _renderVectorSection(containerEl: HTMLElement) {
    // --- Vector Database ---
    containerEl.createEl("h4", { text: "Smart Retrieval" });

    if (!this.plugin.settings.features) {
      this.plugin.settings.features = { memory_layer: true, vector_db: false };
    }

    const vecDescEl = containerEl.createEl("div", {
      cls: "paperforge-desc-box",
    });
    vecDescEl.setText(t("feat_vector_desc"));

    new Setting(containerEl)
      .setName(t("feat_vector_enable"))
      .setDesc(t("feat_vector_enable_desc"))
      .addToggle((toggle) => {
        toggle
          .setValue(!!this.plugin.settings.features.vector_db)
          .onChange((value) => {
            this.plugin.settings.features.vector_db = value;
            this.plugin.saveSettings();
            this._vectorDepsOk = null;
            this._embedStatusText = null;
            this.display();
          });
      });

    if (!this.plugin.settings.features.vector_db) return;

    const vp = (this.app.vault.adapter as any).basePath as string;

    const vecConfigHeader = containerEl.createEl("div", {
      cls: "paperforge-vec-header",
    });
    const vecArrow = vecConfigHeader.createEl("span", {
      text: "\u25BC",
      cls: "paperforge-skills-arrow",
    });
    vecConfigHeader.createEl("span", {
      cls: "paperforge-vec-header-label",
      text: t("feat_vector_config_label"),
    });
    const vecConfigContent = containerEl.createEl("div", {
      cls: "paperforge-vector-config",
    });

    const applyVectorConfigDisclosure = (collapsed: boolean) => {
      vecConfigContent.style.display = collapsed ? "none" : "";
      vecArrow.style.transform = collapsed ? "rotate(-90deg)" : "rotate(0deg)";
    };

    applyVectorConfigDisclosure(
      getDisclosureState(this._featurePanelsCollapsed, "vectorConfig", false)
    );

    vecConfigHeader.addEventListener("click", () => {
      const collapsed = toggleDisclosureState(
        this._featurePanelsCollapsed,
        "vectorConfig",
        false
      );
      applyVectorConfigDisclosure(collapsed);
    });

    if (this._vectorDepsOk === true) {
      this._renderVectorReady(vecConfigContent, vp);
      return;
    }
    if (this._vectorDepsOk === false) {
      this._renderVectorNoDeps(vecConfigContent);
      return;
    }
    if (this._vectorDepsOk === null) {
      const vr = getVectorRuntime(vp);
      this._vectorDepsOk = vr ? (vr.deps_installed ?? false) : false;
      if (this._vectorDepsOk) {
        this._embedStatusText = getVectorStatusText(vp);
      }
      this.display();
    }
  }

  _renderApiConfig(containerEl: HTMLElement) {
    const configured = this.plugin.settings._vector_db_configured || false;
    // Issue #79: settings persist only boolean status; raw value goes to SecretStorage.
    // The placeholder reflects stored/not-configured state without repopulating the input.
    const keyPlaceholder = configured ? "••••••••" : "sk-...";

    let storeTimer: ReturnType<typeof setTimeout> | null = null;

    new Setting(containerEl)
      .setName(t("feat_openai_key"))
      .setDesc(t("feat_openai_key_desc"))
      .addText((text) => {
        text.inputEl.type = "password";
        text
          .setPlaceholder(keyPlaceholder)
          .setValue("")
          .onChange((value) => {
            if (!value) return;
            // ponytail: debounce per-keystroke SecretStorage writes
            if (storeTimer) clearTimeout(storeTimer);
            storeTimer = setTimeout(async () => {
              const ss = (this.app as any).secretStorage;
              if (!ss?.setSecret) return;
              try {
                await ss.setSecret("vector-db-api-key", value);
                const readback = await ss.getSecret("vector-db-api-key");
                if (readback === value) {
                  this.plugin.settings._vector_db_configured = true;
                  this.plugin.settings.vector_db_api_key = "";
                  await this.plugin.saveSettings();
                  text.setValue("");
                }
              } catch {
                // SecretStorage write failed; leave input as-is for retry
              }
              storeTimer = null;
            }, 600);
          });
      });
    new Setting(containerEl)
      .setName(t("feat_api_base_url"))
      .setDesc(t("feat_api_base_url_desc"))
      .addText((text) => {
        text
          .setPlaceholder("https://api.openai.com/v1")
          .setValue(this.plugin.settings.vector_db_api_base || "")
          .onChange((value) => {
            this.plugin.settings.vector_db_api_base = value;
            this.plugin.saveSettings();
          });
      });
    new Setting(containerEl)
      .setName(t("feat_api_model"))
      .setDesc(t("feat_api_model_desc"))
      .addText((text) => {
        text
          .setPlaceholder("text-embedding-3-small")
          .setValue(
            this.plugin.settings.vector_db_api_model || "text-embedding-3-small"
          )
          .onChange((value) => {
            this.plugin.settings.vector_db_api_model = value;
            this.plugin.saveSettings();
          });
      });
  }

  _renderVectorNoDeps(containerEl: HTMLElement) {
    const box = containerEl.createEl("div", { cls: "paperforge-desc-box" });
    box.setText(t("feat_deps_missing"));

    new Setting(containerEl)
      .setName(t("feat_install_deps"))
      .setDesc(t("feat_install_deps_desc"))
      .addButton((button) => {
        button
          .setButtonText(t("feat_install_btn"))
          .setCta()
          .onClick(async () => {
            const vp = (this.app.vault.adapter as any).basePath as string;
            const pyResult = this._resolveRuntimeCommand(vp);
            if (!pyResult?.path) {
              new Notice(t("feat_no_python"));
              return;
            }
            button.setButtonText(t("feat_installing"));
            button.setDisabled(true);
            const pkgs = "chromadb openai";
            const notice = new Notice(
              t("feat_installing_pkgs").replace("{pkgs}", pkgs),
              0
            );
            try {
              const env = Object.assign(paperforgeEnrichedEnv(), {
                PYTHONIOENCODING: "utf-8",
                PYTHONUTF8: "1",
              });
              const pkgsArg = pkgs.split(" ");
              await new Promise<void>((resolve, reject) => {
                execFile(
                  pyResult.path,
                  [...pyResult.args, "-m", "pip", "install", ...pkgsArg],
                  {
                    cwd: vp,
                    timeout: 300000,
                    env: env,
                    windowsHide: true,
                  },
                  (error) => {
                    error ? reject(error) : resolve();
                  }
                );
              });
              notice.hide();
              new Notice(t("feat_install_done"));
              this._vectorDepsOk = true;
              this._embedStatusText = getVectorStatusText(vp);
              this.display();
            } catch (e: any) {
              notice.hide();
              new Notice(
                t("feat_install_failed") + (e.stderr || e.message || e)
              );
              button.setButtonText(t("feat_retry_btn"));
              button.setDisabled(false);
            }
          });
      });
  }

  _renderVectorReady(containerEl: HTMLElement, vp: string) {
    const statusEl = containerEl.createEl("div", {
      cls: "paperforge-desc-box",
    });
    statusEl.setText(getVectorStatusText(vp));

    this._renderApiConfig(containerEl);

    const embedSection = containerEl.createEl("div", {
      cls: "paperforge-embed-section",
    });

    const embedHeader = embedSection.createEl("div", {
      cls: "paperforge-embed-header",
    });
    embedHeader.createEl("span", {
      text: t("retrieval_rebuild_vectors"),
      cls: "setting-item-name",
    });

    const embedControls = embedSection.createEl("div", {
      cls: "paperforge-embed-controls",
    });

    const embedStatusText = embedSection.createEl("div", {
      cls: "paperforge-embed-status-text",
      attr: { "aria-live": "polite" },
    });

    const renderEmbedUI = () => {
      embedControls.empty();
      embedStatusText.empty();

      const vr = getVectorRuntime(vp);
      const bsRaw = vr?.build_state;
      const buildState: Record<string, unknown> =
        bsRaw && typeof bsRaw === "object" && !Array.isArray(bsRaw)
          ? (bsRaw as Record<string, unknown>)
          : {};
      this.plugin._embedProgress = this.plugin._embedProgress || {
        current: 0,
        total: 0,
        key: "",
      };

      if (!this.plugin._embedProcess && buildState.status === "running") {
        this.plugin._embedProgress = {
          current:
            typeof buildState.current === "number" ? buildState.current : 0,
          total: typeof buildState.total === "number" ? buildState.total : 1,
          key:
            typeof buildState.paper_id === "string" ? buildState.paper_id : "",
        };
      }

      const { current, total, key } = this.plugin._embedProgress;

      // Safely access fields from VectorRuntime index signature
      const bodyChunkCount =
        typeof vr?.body_chunk_count === "number" ? vr.body_chunk_count : 0;
      const objectChunkCount =
        typeof vr?.object_chunk_count === "number" ? vr.object_chunk_count : 0;
      const chunkCount =
        typeof vr?.chunk_count === "number" ? vr.chunk_count : 0;
      const totalChunks = chunkCount + bodyChunkCount + objectChunkCount;
      const hasChunks = totalChunks > 0;
      const isCorrupted =
        vr !== null && typeof vr.corrupted === "boolean" && vr.corrupted;
      const isBuilding = !!this.plugin._embedProcess;
      const isStale =
        !this.plugin._embedProcess && buildState.status === "running";
      // deps_installed is a defined boolean? property on VectorRuntime
      const depsInstalled =
        vr?.deps_installed !== undefined ? !!vr.deps_installed : true;

      const status =
        typeof buildState.status === "string" ? buildState.status : "";
      const buildMessage =
        typeof buildState.message === "string" ? buildState.message : "";

      const startBuild = async (flag: string) => {
        // ── Destructive warnings ──
        if (flag === "--resume" && hasChunks && !isCorrupted) {
          const msg = t("retrieval_rebuild_warning").replace(
            "{n}",
            String(totalChunks)
          );
          if (!confirm(msg)) return;
        }
        if (flag === "--force" && hasChunks && !isCorrupted) {
          const msg =
            "Force rebuild will replace " +
            totalChunks +
            " existing chunk(s). Continue?";
          if (!confirm(msg)) return;
        }

        const py = this._resolveRuntimeCommand(vp);
        if (!py?.path) {
          new Notice(t("retrieval_no_python"));
          return;
        }
        // Issue #79: resolve credentials immediately before embed build launch
        const env = await buildTargetedEnv(
          asPluginForSecrets((this as any).app),
          "embed"
        );
        // Merge non-credential embed settings that aren't secret-managed
        env.PYTHONIOENCODING = "utf-8";
        env.PYTHONUTF8 = "1";
        env.VECTOR_DB_API_BASE = this.plugin.settings.vector_db_api_base || "";
        env.VECTOR_DB_API_MODEL =
          this.plugin.settings.vector_db_api_model || "";
        this.plugin._embedStderr = "";
        this.plugin._embedProgress = { current: 0, total: 0, key: "" };
        this.plugin._embedProcess = this._callPython(["embed", "build", flag], {
          stream: true,
          env: env,
          onData: (data: unknown) => {
            // Node stream emits Buffer; data can also be string
            const text =
              typeof data === "string"
                ? data
                : Buffer.isBuffer(data)
                  ? data.toString("utf-8")
                  : String(data);
            // Use shared parser — inline buffer reset on each build
            const { events, buffer } = processProgressChunk(
              text,
              this.plugin._embedBuffer ?? ""
            );
            this.plugin._embedBuffer = buffer;
            for (const ev of events) {
              if (ev.event === "START") {
                this.plugin._embedProgress!.total = ev.total || 0;
              } else if (ev.event === "PROGRESS") {
                this.plugin._embedProgress!.current = ev.current || 0;
                this.plugin._embedProgress!.key = ev.key || "";
              } else if (ev.event === "DONE") {
                this.plugin._embedProcess = null;
                this.plugin._embedProgress!.current =
                  this.plugin._embedProgress!.total;
              }
            }
            this.display();
          },
          onStderr: (data: unknown) => {
            if (!this.plugin._embedStderr) this.plugin._embedStderr = "";
            this.plugin._embedStderr += String(data);
          },
          onError: (err: Error) => {
            this.plugin._embedProcess = null;
            new Notice(t("feat_build_failed") + ": " + (err.message || err));
            this.display();
          },
          onClose: (code: number | null) => {
            clearInterval(this.plugin._embedPollInterval ?? undefined);
            this.plugin._embedPollInterval = null;
            this.plugin._embedProcess = null;
            if (code === 0) {
              this.plugin._embedProgress!.current =
                this.plugin._embedProgress!.total;
              this.plugin.saveSettings();
              this._embedStatusText = getVectorStatusText(vp);
              new Notice(t("feat_build_complete"));
            } else {
              this._embedStatusText = null;
              const errMsg = (this.plugin._embedStderr || "").slice(0, 200);
              new Notice(
                t("feat_build_failed") + (errMsg ? ": " + errMsg : ""),
                8000
              );
            }
            this.plugin._embedStderr = "";
            this.display();
            this._refreshSnapshots(vp);
          },
        });

        // Poll embed status every 2s during build for live state
        clearInterval(this.plugin._embedPollInterval ?? undefined);
        this.plugin._embedPollInterval = setInterval(() => {
          if (this.plugin._embedPolling) return;
          this.plugin._embedPolling = true;
          this._callPython(["embed", "status", "--json"], {
            timeout: 5000,
            onClose: (_code: number | null, stdout: string) => {
              this.plugin._embedPolling = false;
              if (_code === 0 && stdout) {
                try {
                  const result = JSON.parse(stdout);
                  const data = result.data;
                  if (data && data.build_state) {
                    const bs = data.build_state;
                    if (bs.status === "stopping" || bs.status === "idle") {
                      if (this.plugin._embedProcess) {
                        this.plugin._embedProcess = null;
                        clearInterval(
                          this.plugin._embedPollInterval ?? undefined
                        );
                        this.plugin._embedPollInterval = null;
                        this.display();
                      }
                    }
                    if (bs.current !== undefined && bs.total !== undefined) {
                      this.plugin._embedProgress!.current = bs.current;
                      this.plugin._embedProgress!.total = bs.total || 1;
                      this.plugin._embedProgress!.key = bs.paper_id || "";
                    }
                  }
                } catch {}
              }
            },
          });
        }, 2000);

        this.display();
      };

      // Detect runtime version mismatch from health data
      const health = getRuntimeHealth(vp);
      let runtimeMismatch = false;
      if (
        health &&
        typeof health.summary === "object" &&
        health.summary !== null &&
        "status" in health.summary
      ) {
        runtimeMismatch = health.summary.status === "version_mismatch";
      }

      // ── State determination (priority order) ──
      let uiState: string;
      if (!depsInstalled) {
        uiState = "deps-missing";
      } else if (runtimeMismatch) {
        uiState = "runtime-mismatch";
      } else if (status === "stopping") {
        uiState = "stopping";
      } else if (isBuilding && status === "running") {
        uiState = "building";
      } else if (status === "failed") {
        uiState = "failed";
      } else if (status === "stopped") {
        uiState = "stopped";
      } else if (isStale) {
        uiState = "stale";
      } else if (isCorrupted) {
        uiState = "corrupted";
      } else if (hasChunks) {
        uiState = "ready";
      } else {
        uiState = "idle";
      }

      // ── State rendering ──
      switch (uiState) {
        case "building": {
          const track = embedControls.createEl("div", {
            cls: "paperforge-progress-track",
          });
          track.style.cssText = "flex:1;";
          const pct = total > 0 ? ((current / total) * 100).toFixed(1) : "0";
          const doneSeg = track.createEl("div", {
            cls: "paperforge-progress-seg done",
          });
          doneSeg.style.cssText = `width:${pct}%; min-width:${current > 0 ? "2px" : "0"};`;
          if (current < total) {
            const pendingSeg = track.createEl("div", {
              cls: "paperforge-progress-seg pending",
            });
            pendingSeg.style.cssText = `width:${(100 - parseFloat(pct)).toFixed(1)}%;`;
          }
          embedStatusText.createEl("span", {
            cls: "paperforge-embed-progress-text",
            text: `${current}/${total} papers`,
          });
          if (key) {
            embedStatusText.createEl("span", {
              cls: "paperforge-embed-progress-key",
              text: ` (${key})`,
            });
          }
          // Warning button: Stop
          const stopBtn = embedControls.createEl("button");
          stopBtn.setText(t("retrieval_stop"));
          stopBtn.className = "mod-warning";
          stopBtn.addEventListener("click", () => {
            this._callPython(["embed", "stop", "--json"], {
              timeout: 8000,
            });
            this.display();
          });
          break;
        }

        case "stopping": {
          const track = embedControls.createEl("div", {
            cls: "paperforge-progress-track",
          });
          track.style.cssText = "flex:1; opacity:0.5;";
          const pct = total > 0 ? ((current / total) * 100).toFixed(1) : "0";
          const doneSeg = track.createEl("div", {
            cls: "paperforge-progress-seg done",
          });
          doneSeg.style.cssText = `width:${pct}%; min-width:${current > 0 ? "2px" : "0"};`;
          if (current < total) {
            const pendingSeg = track.createEl("div", {
              cls: "paperforge-progress-seg pending",
            });
            pendingSeg.style.cssText = `width:${(100 - parseFloat(pct)).toFixed(1)}%;`;
          }
          embedStatusText.createEl("span", {
            text: t("retrieval_build_stopping"),
          });
          const stopBtn = embedControls.createEl("button");
          stopBtn.setText(t("retrieval_stop"));
          stopBtn.className = "mod-warning";
          stopBtn.setAttr("disabled", "");
          break;
        }

        case "failed": {
          embedStatusText.createEl("div", {
            cls: "paperforge-desc-box",
            text:
              t("retrieval_build_failed") +
              (buildMessage ? ": " + buildMessage : ""),
            attr: { style: "color:var(--text-error);" },
          });
          // Primary CTA: Retry
          const retryBtn = embedControls.createEl("button");
          retryBtn.setText(t("retrieval_retry"));
          retryBtn.className = "mod-cta";
          retryBtn.addEventListener("click", () => startBuild("--resume"));
          // Secondary: Force Rebuild
          const forceBtn = embedControls.createEl("button");
          forceBtn.setText(t("retrieval_force_rebuild"));
          forceBtn.style.marginLeft = "6px";
          forceBtn.addEventListener("click", () => startBuild("--force"));
          break;
        }

        case "stopped": {
          embedStatusText.setText(t("retrieval_build_stopped"));
          // Primary CTA: Resume
          const resumeBtn = embedControls.createEl("button");
          resumeBtn.setText(t("retrieval_retry"));
          resumeBtn.className = "mod-cta";
          resumeBtn.addEventListener("click", () => startBuild("--resume"));
          break;
        }

        case "corrupted": {
          embedStatusText.createEl("div", {
            cls: "paperforge-desc-box",
            text: t("feat_vector_corrupted"),
            attr: {
              style: "background:var(--background-modifier-warning);",
            },
          });
          // Primary CTA: Force Rebuild (no destructive warning on corrupted)
          const forceBtn = embedControls.createEl("button");
          forceBtn.setText(t("retrieval_force_rebuild"));
          forceBtn.className = "mod-cta";
          forceBtn.addEventListener("click", () => startBuild("--force"));
          break;
        }

        case "stale": {
          embedStatusText.createEl("div", {
            cls: "paperforge-desc-box",
            text: t("retrieval_build_stale"),
            attr: { style: "color:var(--text-warning);" },
          });
          // Primary CTA: Rebuild
          const rebuildBtn = embedControls.createEl("button");
          rebuildBtn.setText(t("retrieval_rebuild_vectors"));
          rebuildBtn.className = "mod-cta";
          rebuildBtn.addEventListener("click", () => startBuild("--resume"));
          break;
        }

        case "ready": {
          embedControls.createEl("span", {
            text: totalChunks + " chunks embedded",
            cls: "setting-item-description",
          });
          // Primary CTA: Rebuild Vectors
          const rebuildBtn = embedControls.createEl("button");
          rebuildBtn.setText(t("retrieval_rebuild_vectors"));
          rebuildBtn.className = "mod-cta";
          rebuildBtn.addEventListener("click", () => startBuild("--resume"));
          // Secondary: Force Rebuild
          const forceBtn = embedControls.createEl("button");
          forceBtn.setText(t("retrieval_force_rebuild"));
          forceBtn.style.marginLeft = "6px";
          forceBtn.addEventListener("click", () => startBuild("--force"));
          break;
        }

        case "deps-missing": {
          embedStatusText.setText(t("retrieval_build_deps_missing"));
          // Link-style: Install Dependencies redirects to full settings display
          const installBtn = embedControls.createEl("a");
          installBtn.setText(t("feat_install_deps"));
          installBtn.style.cssText =
            "cursor:pointer; text-decoration:underline;";
          installBtn.addEventListener("click", () => {
            this.display();
          });
          break;
        }

        case "runtime-mismatch": {
          embedStatusText.createEl("div", {
            cls: "paperforge-desc-box",
            text: t("retrieval_build_runtime_mismatch"),
            attr: { style: "color:var(--text-warning);" },
          });
          // Link-style: Sync Runtime navigates to Runtime Health section
          const syncLink = embedControls.createEl("a");
          syncLink.setText(t("runtime_health_sync"));
          syncLink.style.cssText = "cursor:pointer; text-decoration:underline;";
          syncLink.addEventListener("click", () => {
            this.display();
          });
          break;
        }

        case "idle":
        default: {
          embedStatusText.setText(t("retrieval_build_idle"));
          // Primary CTA: Build
          const buildBtn = embedControls.createEl("button");
          buildBtn.setText(t("feat_build_btn"));
          buildBtn.className = "mod-cta";
          buildBtn.addEventListener("click", () => startBuild("--resume"));
          break;
        }
      }
    };

    renderEmbedUI();
  }

  _getCurrentModelKey(): string {
    return this.plugin.settings.vector_db_api_model || "text-embedding-3-small";
  }

  _parseEmbedStatus(text: string): Record<string, any> {
    const info: Record<string, any> = {};
    if (!text) return info;
    text.split("\n").forEach((line) => {
      const m = line.match(/^\s*([^:]+):\s*(.*)/);
      if (m) info[m[1].trim()] = m[2].trim();
    });
    if (info.db_exists !== undefined)
      info.db_exists = info.db_exists === "True";
    if (info.chunk_count !== undefined)
      info.chunk_count = parseInt(info.chunk_count, 10) || 0;
    return info;
  }

  _getPythonDesc(pyPath: string, source: string): string {
    if (source === "stale") {
      return `[!!] ${pyPath} (stale \u2014 path no longer exists, update or clear the override below)`;
    }
    if (source === "manual") {
      return `${pyPath} (manual)`;
    }
    return `${pyPath} (auto-detected)`;
  }

  _refreshPythonInterpDesc(pyPath: string, source: string) {
    const desc = this._pythonInterpDescEl;
    if (desc) {
      if (source === "stale") {
        desc.textContent = `[!!] ${pyPath} (stale \u2014 path no longer exists, update or clear the override below)`;
      } else if (source === "manual") {
        desc.textContent = `${pyPath} (manual)`;
      } else {
        desc.textContent = `${pyPath} (auto-detected)`;
      }
    }
  }

  _validatePythonOverride() {
    const customPath = this.plugin.settings.python_path
      ? this.plugin.settings.python_path.trim()
      : "";
    const desc = this._customPathDescEl;

    if (!customPath) {
      const msg = "\u8BF7\u8F93\u5165\u8DEF\u5F84 / Enter a path first";
      if (desc)
        desc.innerHTML = `<span style="color:var(--text-error)">\u2717 ${msg}</span>`;
      new Notice(msg);
      return;
    }

    if (!fs.existsSync(customPath)) {
      const msg = "\u8DEF\u5F84\u4E0D\u5B58\u5728 / Path does not exist";
      if (desc)
        desc.innerHTML = `<span style="color:var(--text-error)">\u2717 ${msg}</span>`;
      new Notice(msg, 4000);
      return;
    }

    try {
      fs.accessSync(customPath, fs.constants.X_OK);
    } catch {
      const msg = "\u4E0D\u53EF\u6267\u884C / Not executable";
      if (desc)
        desc.innerHTML = `<span style="color:var(--text-error)">\u2717 ${msg}</span>`;
      new Notice(msg, 4000);
      return;
    }

    execFile(customPath, ["--version"], { timeout: 8000 }, (verErr, verOut) => {
      if (verErr || !verOut) {
        const msg = "\u65E0\u6CD5\u8FD0\u884C / Cannot run";
        if (desc)
          desc.innerHTML = `<span style="color:var(--text-error)">\u2717 ${msg}</span>`;
        new Notice(msg, 4000);
        return;
      }

      const match = verOut.match(/Python (\d+)\.(\d+)/);
      if (!match) {
        const msg =
          "\u65E0\u6CD5\u89E3\u6790\u7248\u672C / Cannot parse version";
        if (desc)
          desc.innerHTML = `<span style="color:var(--text-error)">\u2717 ${msg}</span>`;
        new Notice(msg, 4000);
        return;
      }

      const major = parseInt(match[1], 10);
      const minor = parseInt(match[2], 10);

      if (major < 3 || (major === 3 && minor < 11)) {
        const msg =
          "Python \u7248\u672C\u8FC7\u4F4E\uFF0C\u9700\u8981 3.11+ / Python version too low, need 3.11+";
        if (desc)
          desc.innerHTML = `<span style="color:var(--text-error)">\u2717 ${msg}</span>`;
        new Notice(msg, 4000);
        return;
      }

      execFile(
        customPath,
        ["-m", "pip", "--version"],
        { timeout: 8000 },
        (pipErr) => {
          if (pipErr) {
            const warnMsg = `\u2713 Python ${major}.${minor} \u6709\u6548\uFF0C\u4F46\u672A\u68C0\u6D4B\u5230 pip / Valid, but pip not found`;
            if (desc)
              desc.innerHTML = `<span style="color:var(--text-warning)">\u26A0 ${warnMsg}</span>`;
            new Notice(warnMsg, 4000);
          } else {
            const okMsg = `\u2713 Python ${major}.${minor} \u6709\u6548 / Valid`;
            if (desc)
              desc.innerHTML = `<span style="color:var(--text-accent)">${okMsg}</span>`;
            new Notice(okMsg, 4000);
          }
        }
      );
    });
  }

  _debouncedSave() {
    clearTimeout(this._saveTimeout!);
    this._saveTimeout = setTimeout(() => this.plugin.saveSettings(), 500);
  }

  _preCheck(onPass: () => void) {
    const vaultPath = (this.app.vault.adapter as any).basePath as string;
    const resolved = this._resolveRuntimeCommand(vaultPath);
    if (!resolved) {
      onPass(); // runtime not ready, skip pre-check
      return;
    }
    execFile(
      resolved.path,
      [...resolved.args, "--version"],
      { timeout: 8000 },
      (pyErr, pyOut) => {
        const results: { label: string; ok: boolean; detail: string }[] = [];

        /* Python */
        results.push({
          label: "environment",
          ok: !pyErr,
          detail: pyErr ? t("check_python_fail") : pyOut.trim(),
        });

        /* Zotero */
        let zotOk = false;
        const home =
          process.env.HOME || process.env.USERPROFILE || os.homedir() || "";
        if (process.platform === "darwin") {
          const macZot = [
            "/Applications/Zotero.app",
            path.join(home, "Applications", "Zotero.app"),
          ];
          zotOk = macZot.some((d) => {
            try {
              return fs.existsSync(d);
            } catch {
              return false;
            }
          });
        } else if (process.platform === "win32") {
          const progFiles = process.env.ProgramFiles || "";
          const localAppData = process.env.LOCALAPPDATA || "";
          const zotInstallDirs = [
            path.join(progFiles, "Zotero"),
            path.join(progFiles, "(x86)", "Zotero"),
            path.join(localAppData, "Programs", "Zotero"),
            path.join(localAppData, "Zotero"),
            path.join(home, "AppData", "Local", "Programs", "Zotero"),
          ].filter(Boolean);
          zotOk = zotInstallDirs.some((d) => {
            try {
              return fs.existsSync(d);
            } catch {
              return false;
            }
          });
        } else {
          const linuxPaths = [
            path.join(home, ".local", "share", "zotero", "zotero"),
            "/usr/bin/zotero",
            "/usr/local/bin/zotero",
          ];
          zotOk = linuxPaths.some((d) => {
            try {
              return fs.existsSync(d);
            } catch {
              return false;
            }
          });
        }
        const zotDataDir = this.plugin.settings.zotero_data_dir;
        if (!zotOk && zotDataDir) {
          try {
            zotOk = fs.existsSync(zotDataDir);
          } catch {}
        }
        results.push({
          label: "Zotero",
          ok: zotOk,
          detail: zotOk ? t("check_zotero_ok") : t("check_zotero_fail"),
        });

        /* Better BibTeX */
        let bbtOk = false;
        const appData = process.env.APPDATA || "";
        if (process.platform === "win32" && appData) {
          bbtOk = scanBbtUnderProfiles(
            path.join(appData, "Zotero", "Zotero", "Profiles")
          );
        }
        if (!bbtOk && process.platform === "darwin" && home) {
          bbtOk = scanBbtUnderProfiles(
            path.join(
              home,
              "Library",
              "Application Support",
              "Zotero",
              "Profiles"
            )
          );
        }
        if (
          !bbtOk &&
          process.platform !== "win32" &&
          process.platform !== "darwin" &&
          home
        ) {
          bbtOk = scanBbtUnderProfiles(
            path.join(home, ".zotero", "zotero", "Profiles")
          );
        }
        if (!bbtOk && zotDataDir && String(zotDataDir).trim()) {
          bbtOk = scanBbtDirectChildren(zotDataDir.trim());
        }
        if (!bbtOk && home) {
          bbtOk = scanBbtDirectChildren(path.join(home, "Zotero"));
        }
        results.push({
          label: "Better BibTeX",
          ok: bbtOk,
          detail: bbtOk ? t("check_bbt_ok") : t("check_bbt_fail"),
        });

        /* Render */
        const marks: Record<string, string> = {
          true: "\u2713",
          false: "\u2717",
        };
        if (this._checkEl) {
          this._checkEl.setText(
            results
              .map((r) => `${marks[String(r.ok)]} ${r.label}: ${r.detail}`)
              .join("\n")
          );
          const anyFail = results.some((r) => !r.ok);
          this._checkEl.className = `paperforge-message msg-${anyFail ? "error" : "ok"}`;
        }
        const bad = results.filter((r) => !r.ok);
        if (bad.length > 0) {
          new Notice(
            `[!!] \u672A\u901A\u8FC7: ${bad.map((r) => r.label).join(", ")}`,
            6000
          );
        }

        onPass();
      }
    );
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
            this._updateCapabilityEnvelope(mod, parsed as ProbeEnvelope);
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
    if (env.severity === "ok") return "cc_badge_ok";
    if (env.severity === "error" && mod === "installation")
      return "cc_badge_setup";
    if (env.severity === "warning" || env.severity === "error")
      return "cc_badge_attention";
    return "cc_badge_pending";
  }

  /** CSS severity class from backend severity string. Unknown maps to neutral. */
  _sevClass(severity: string): string {
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
    const sevClass = this._sevClass(env.severity);
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
          new PaperForgeSetupModal(this.app, this.plugin, () => {
            this._probeModule("installation");
            this._probeModule("help");
          }).open();
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
      text: t("cc_modules_label") || "modules",
    });
    sectionHead.createEl("h2", {
      text: t("cc_modules_title") || "Five capabilities",
    });
    sectionHead.createEl("span", {
      cls: "caption",
      text:
        t("cc_modules_caption") ||
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

  /** #86: Agent Integration placeholder — not yet a backend probe. */
  _getAgentPlaceholderEnvelope(): ProbeEnvelope {
    return {
      schema_version: 2,
      module: "agent",
      capability_state: "unknown",
      activity_state: "idle",
      activity_label: null,
      activity_progress: null,
      severity: "unknown",
      reason: {
        code: "agent.not_implemented",
        text: "Agent Integration will be available in a future update.",
      },
      action: { primary: null },
      notices: [],
      user_state: "not_enabled",
      capability_kind: "optional",
      maintenance_eligible: false,
      user_visible_failure: false,
      user_impact: null,
      updated_at: new Date(0).toISOString(),
      ttl_seconds: 0,
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
      env.user_state === "ready" && env.action?.primary?.scope_count
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
    const operationalModules: CapabilityModule[] = [
      "installation",
      "library",
      "ocr",
      "memory",
    ];
    for (const mod of operationalModules) {
      this._probeModule(mod);
    }
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
    containerEl.createEl("h3", { text: t("setup_foundation_title") });
    containerEl.createEl("p", { text: t("setup_foundation_desc") });
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
    if (env.action?.primary && env.user_state !== "ready") {
      const verbKey = "cc_action_" + env.action.primary.verb;
      renderActionButton(containerEl, {
        label: t(verbKey) === verbKey ? t("cc_action_setup") : t(verbKey),
        onClick: () =>
          this._runAllowedDispatch(
            "installation",
            env.action.primary!.verb,
            env.action.primary!.command,
            env
          ),
      });
    }
    const nav = containerEl.createDiv({ cls: "pf-setup-nav" });
    renderActionButton(nav, {
      label: t("setup_nav_continue"),
      disabled: env.user_state !== "ready",
      onClick: () => {
        this._setupStage = 2;
        this.display();
      },
    });
  }

  _renderSetupStageLibrary(containerEl: HTMLElement): void {
    const env =
      this._capabilityState?.library ?? createUnknownEnvelope("library");
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
    if (env.action?.primary && env.user_state !== "ready") {
      const verbKey = "cc_action_" + env.action.primary.verb;
      renderActionButton(containerEl, {
        label: t(verbKey) === verbKey ? t("cc_action_set_config") : t(verbKey),
        onClick: () =>
          this._runAllowedDispatch(
            "library",
            env.action.primary!.verb,
            env.action.primary!.command,
            env
          ),
      });
    }
    const nav = containerEl.createDiv({ cls: "pf-setup-nav" });
    renderActionButton(nav, {
      label: t("setup_nav_back"),
      onClick: () => {
        this._setupStage = 1;
        this.display();
      },
    });
    renderActionButton(nav, {
      label: t("setup_nav_continue"),
      disabled: env.user_state !== "ready",
      onClick: () => {
        this._setupStage = 3;
        this.display();
      },
    });
  }

  _renderSetupStageOptionals(containerEl: HTMLElement): void {
    containerEl.createEl("h3", { text: t("setup_optionals_title") });
    containerEl.createEl("p", { text: t("setup_optionals_desc") });
    const optionals = [
      {
        id: "ocr",
        label: t("cc_module_ocr"),
        desc: t("setup_opt_ocr_desc"),
      },
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
      });
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
      onClick: () => {
        this._setupStage = 4;
        this.display();
      },
    });
  }

  _renderSetupStageReview(containerEl: HTMLElement): void {
    containerEl.createEl("h3", { text: t("setup_review_title") });
    const foundationReady =
      this._capabilityState?.installation?.user_state === "ready";
    const libraryReady = this._capabilityState?.library?.user_state === "ready";
    containerEl.createEl("p", {
      text: foundationReady
        ? t("setup_ready")
        : t("cc_consequence_setup_required"),
      cls: foundationReady ? "pf-setup-ok" : "pf-setup-warn",
    });
    containerEl.createEl("p", {
      text: libraryReady
        ? t("setup_library_ready")
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
    renderActionButton(nav, {
      label: t("setup_nav_complete"),
      disabled: !foundationReady || !libraryReady,
      onClick: () => this._completeSetup(),
    });
    if (!foundationReady || !libraryReady) {
      containerEl.createEl("p", {
        text: t("setup_incomplete_warn"),
        cls: "pf-setup-warn",
      });
    }
  }

  /** #87: Complete setup — persist and transition to normal operation. */
  _completeSetup(): void {
    this.plugin.settings._setup_complete = true;
    this.plugin.saveSettings();
    this.activeTab = "overview";
    this.display();
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
      // Only clear transient state on fresh open, not on re-renders
      this._focusTargetId = null;
      this._detailReturn = null;
      this._setupView = "overview";
    }
  }
}
