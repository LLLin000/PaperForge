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
import { migrateLegacySecret } from "./services/secret-storage";
import { t, setLanguage, langFromApp } from "./i18n";
import {
  EMBEDDING_PRESETS,
  matchEmbeddingPresetId,
  renderDomainModePreview,
} from "./views/domain-preview";
import type { ZoteroDetectDto } from "./client/paperforge-client";
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
  runtimeInstallAction,
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
  scanBbtUnderProfiles,
  scanBbtDirectChildren,
  classifySetupFailure,
} from "./services/python-bridge";
import type {
  ErrorClassification,
  PythonResult,
} from "./services/python-bridge";
import { deferred } from "./services/deferred";
import { orchestrateFromSync } from "./services/next-actions-bridge";
import { PaperForgeClient } from "./client";
import {
  clearTrace,
  dumpTrace,
  setTraceEnabled,
  traceConsoleError,
} from "./client/trace";
import {
  PaperForgeConfirmModal,
  PaperForgeIssueDraftModal,
  buildRedactedDraft,
  PaperForgeOrphanModal,
  checkOrphanState,
  type OrphanItem,
} from "./views/modals";
import {
  renderUpgradeAvailableBanner,
  renderStorageMigrationMaintenanceSection,
} from "./views/upgrade-modal";
import {
  readRuntimePointer,
  resolveRuntimeCommand,
} from "./services/managed-runtime";
import type { RuntimeStatus } from "./client";
import { stripCredentialEnv } from "./services/secret-storage";
import { processProgressChunk } from "./services/progress-parser";
import type { RuntimeInstallerAction } from "./services/runtime-installer-launcher";
import {
  INSTALLER_FAILED_MARKER,
  runtimeInstallerSteps,
} from "./services/runtime-installer-launcher";
import type { ActionRequest } from "./client/action-contract";
import {
  applyPathConfigFromList,
  resolveVaultPaths,
} from "./services/runtime-paths";

// ── Interface ──

/** Display names for the agent platforms Python offers. */
const AGENT_PLATFORM_LABELS: Record<string, string> = {
  opencode: "OpenCode",
  claude: "Claude Code",
  codex: "Codex",
  cursor: "Cursor",
  windsurf: "Windsurf",
  github_copilot: "GitHub Copilot",
  gemini: "Gemini CLI",
  kilo: "Kilo Code",
  pi: "Pi Agent",
  omp: "Oh My Pi",
  crush: "Crush",
  kimi: "Kimi CLI",
  cline: "Cline",
  augment: "Augment",
  trae: "Trae",
};

/** Skill deployment directories per agent platform (fallback: .agents/skills). */
const AGENT_PLATFORM_SKILL_DIRS: Record<string, string> = {
  opencode: ".opencode/skills",
  claude: ".claude/skills",
  codex: ".codex/skills",
  cursor: ".cursor/skills",
  windsurf: ".windsurf/skills",
  github_copilot: ".github/skills",
  gemini: ".gemini/skills",
  cline: ".cline/skills",
  kilo: ".kilocode/skills",
  kimi: ".kimi/skills",
  augment: ".augment/skills",
  trae: ".trae/skills",
  pi: ".agents/skills",
  omp: ".agents/skills",
  crush: ".agents/skills",
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface ISettingPlugin {
  settings: PaperForgeSettings;
  saveSettings(): Promise<void>;
  loadSettings(): Promise<void>;
  manifest: { version: string };
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
  activeTab = "overview";
  private _zoteroDetectData: ZoteroDetectDto | null = null;
  private _zoteroDetectBusy = false;
  private _zoteroDetectRan = false;
  private _setupExpressMode = true;
  private _detectedFolderCollisionMsg: string | null = null;
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
  private _lastOrphanCount: number = 0;
  /** Modules that have already been auto-probed (prevents endless re-probe). */
  private _attemptedProbes: Set<string> = new Set();
  /** Optional modules whose detail page re-probed once this session, so a
   *  persisted last-known envelope (e.g. "API Key: Entered" for a key since
   *  deleted) never stands in for the live state after a restart. */
  private _detailProbedThisSession: Set<string> = new Set();
  /** Currently active sub-view within the Setup tab. */
  _setupView: "overview" | "module-detail" = "overview";
  /** #87: Setup Journey current stage (1-4). */
  _setupStage = 1;
  /** The next runtime action rebuilds the environment instead of reusing it. */
  private _setupReinstallRequested = false;
  /** Log of the installer launched from this panel (null before any launch). */
  private _installerLogPath: string | null = null;
  /** #87: Selected optional capabilities. */
  _setupOptionals: Record<string, boolean> = {
    ocr: false,
    memory: false,
    agent: false,
  };
  private _setupOperation: "idle" | "running" | "failed" = "idle";
  private _setupFeedback: string | null = null;
  /** Raw failure reason for the last install attempt (null when none). */
  private _setupFailureDetail: string | null = null;
  /** #257: last classified install failure, surfaced in the diagnostic. */
  private _lastSetupFailure: {
    category: string;
    reason: string;
    at: string;
  } | null = null;
  /** #257: bootstrap/setup stage breadcrumbs for the diagnostic (capped). */
  private _setupStageLog: string[] = [];
  /** Completion state before an explicitly entered journey (see _goHome). */
  private _setupCompleteBeforeJourney: boolean | null = null;
  /** RC UX Seam P1: user chose "Later" — pure session flag; reset on hide(). */
  private _setupJourneyDismissedForSession = false;
  /** Currently selected module in the detail view. */
  _selectedDetailModule: string = "";
  /** Focus target id after re-render. */
  _focusTargetId: string | null = null;
  private _runtimeStatus: RuntimeStatus | null = null;
  private _runtimeStatusError: string | null = null;
  private _runtimeStatusVersion: string | null = null;
  private _runtimeStatusLoading = false;
  private _runtimePollTimer: ReturnType<typeof setInterval> | null = null;
  private _runtimeStatusWatchdog: ReturnType<typeof setTimeout> | null = null;
  /** Step id the guided library flow keeps expanded after an explicit edit. */
  private _setupOpenStep: string | null = null;
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
      skill_dir: String(s.skill_dir || ".agents/skills"),
      zotero_data_dir: s.zotero_data_dir || "",
    };
  }

  /** ONE way home from anywhere in the tab: clear the detail selection,
   *  leave the setup journey for this session, and re-render the Control
   *  Center.  Without this, leaving a deep wizard stage meant clicking
   *  "back" once per stage (#87 UX). */
  _goHome(): void {
    if (this._setupOperation === "running") return;
    this.activeTab = "overview";
    this._selectedDetailModule = "";
    this._detailReturn = null;
    this._focusTargetId = null;
    this._setupStage = 1;
    this._setupOperation = "idle";
    this._setupFeedback = null;
    this._setupFailureDetail = null;
    this._setupJourneyDismissedForSession = true;
    // Leaving a REINSTALL of an already-configured install must not leave the
    // vault marked unfinished — otherwise the wizard blocks every later
    // Settings open for a machine that is fully working.
    if (this._setupCompleteBeforeJourney === true) {
      this.plugin.settings._setup_complete = true;
      void this.plugin.saveSettings();
    }
    this._setupCompleteBeforeJourney = null;
    this.display();
  }

  display() {
    this._displayInProgress = true;
    const { containerEl } = this;
    containerEl.empty();
    containerEl.classList?.add("pf-settings-shell", "pf-settings-scope");
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
    if (this.activeTab === "help" && !this._attemptedProbes.has("help")) {
      this._attemptedProbes.add("help");
      this._probeModule("help");
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

    // Top: Home — present whenever the user is NOT on the Control Center
    // (module detail, help), so there is always ONE click back to the top.
    const onOverview =
      this.activeTab === "overview" && !this._selectedDetailModule;
    const brandLeft = topbar.createDiv({ cls: "pf-cc-topbar-left" });
    if (!onOverview) {
      const homeBtn = brandLeft.createEl("button", {
        cls: "pf-cc-topbar-home",
        text: "\u2190 " + (t("nav_home") || "Control center"),
      });
      homeBtn.setAttribute("aria-label", t("nav_home") || "Control center");
      homeBtn.addEventListener("click", () => this._goHome());
    }
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
        if (tab.id === "help") this._attemptedProbes.delete("help");
        this._navMemory = { destination: tab.id };
        this._persistNavMemory();
        this.display();
      });
    });

    if (onOverview) {
      const filterWrap = topbar.createDiv({
        cls: "search-input-container pf-cc-quick-filter",
      });
      const filterInput = filterWrap.createEl("input", {
        cls: "pf-cc-filter-input",
        attr: {
          type: "search",
          placeholder:
            langFromApp(this.app) === "zh"
              ? "筛选模块或配置…"
              : "Filter settings…",
          "aria-label":
            langFromApp(this.app) === "zh"
              ? "筛选模块或配置"
              : "Filter settings",
        },
      }) as HTMLInputElement;
      filterInput.addEventListener("input", () => {
        this._applyOverviewQuickFilter(containerEl, filterInput.value);
      });
    }

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
  private _client: PaperForgeClient | null = null;

  getClient(): PaperForgeClient {
    if (this._client) return this._client;
    // Ticket 07 step 6 item 4 (P1 closure condition): Settings NEVER
    // constructs its own client — a second PaperForgeClient would be a
    // second OperationLock/long-task owner. Fail closed on the singleton.
    const singleton = (this.plugin as any)?.getClient;
    if (typeof singleton !== "function") {
      throw new Error(
        "PaperForge client unavailable: plugin.getClient singleton is missing"
      );
    }
    this._client = singleton.call(this.plugin);
    return this._client!;
  }

  /** Start stage 1 from a plugin-owned recovery entry point. */
  openSetupJourney(): void {
    this._startSetupJourney(1);
  }

  private _startSetupJourney(
    stage: 1 | 2 | 3 | 4 = 1,
    reinstall = false
  ): void {
    this._setupStage = stage;
    this._setupReinstallRequested = reinstall;
    this._setupOperation = "idle";
    this._setupFeedback = null;
    this._setupFailureDetail = null;
    // An EXPLICIT request to start the journey always wins: without this,
    // leaving the wizard (Later / Home) left the session flag set and the
    // next "install"/"reinstall" click silently did nothing.
    this._setupJourneyDismissedForSession = false;
    this._setupCompleteBeforeJourney =
      this.plugin.settings._setup_complete !== false;
    this._setupOpenStep = null;
    this.plugin.settings._setup_complete = false;
    void this.plugin.saveSettings().then(() => this.display());
  }

  /** One bounded line naming the real install failure (never the whole log). */
  private _formatSetupFailure(error: unknown): string {
    const raw =
      typeof error === "string"
        ? error
        : error instanceof Error
          ? error.message
          : String(error ?? "unknown error");
    const firstLine = raw.split(/\r?\n/).find((line) => line.trim()) ?? raw;
    const bounded = firstLine.trim();
    return bounded.length > 220 ? `${bounded.slice(0, 220)}…` : bounded;
  }

  /** #257: classified next step; do not echo command lines or raw stderr. */
  private _formatSetupFailureWithHint(failure: ErrorClassification): string {
    const hints: Record<string, string> = {
      network: "setup_fail_hint_network",
      disk_full: "setup_fail_hint_disk_full",
      permission_denied: "setup_fail_hint_permission_denied",
      process_busy: "setup_fail_hint_process_busy",
      artifact_unavailable: "setup_fail_hint_artifact_unavailable",
      wheel_unavailable: "setup_fail_hint_wheel_unavailable",
      import_failed: "setup_fail_hint_import_failed",
      version_mismatch: "setup_fail_hint_version_mismatch",
      no_python: "setup_fail_hint_no_python",
      python_missing: "setup_fail_hint_no_python",
    };
    const hintKey = hints[failure.type] ?? "setup_fail_hint_generic";
    return t(hintKey);
  }

  /** #257: bounded stage breadcrumbs (oldest first) for the diagnostic. */
  private _recordSetupStage(label: string): void {
    this._setupStageLog.push(`${new Date().toISOString()} ${label}`);
    if (this._setupStageLog.length > 16) this._setupStageLog.shift();
  }

  /** #257: public location class; never return a raw or home-relative path. */
  private _diagnosticPath(value: string | null | undefined): string | null {
    const trimmed = value?.trim();
    if (!trimmed) return null;
    const home = os.homedir();
    if (trimmed.startsWith(home)) return "(inside home)";
    return "(outside home)";
  }

  /** Bounded one-line detail for per-key config failures (write/readback). */
  private _formatConfigFailures(
    failures: Array<{ key: string; reason: string }>
  ): string {
    const text = failures.map((f) => `${f.key}: ${f.reason}`).join(" · ");
    return text.length > 400 ? `${text.slice(0, 400)}…` : text;
  }

  /** Pick a native OS directory via Electron dialog or hidden webkitdirectory input. */
  private async _pickFolderPath(hostEl: HTMLElement): Promise<string | null> {
    try {
      const electron = require("electron") as {
        remote?: {
          dialog?: {
            showOpenDialog?: (opts: {
              properties: string[];
            }) => Promise<{ canceled: boolean; filePaths: string[] }>;
          };
        };
        webUtils?: { getPathForFile?: (file: File) => string };
      };
      const dialog = electron?.remote?.dialog;
      if (dialog?.showOpenDialog) {
        const res = await dialog.showOpenDialog({
          properties: ["openDirectory"],
        });
        if (!res.canceled && res.filePaths?.[0]) {
          return res.filePaths[0];
        }
        return null;
      }
    } catch {
      // Electron remote unavailable in newer Obsidian builds; use DOM directory input fallback.
    }
    return new Promise<string | null>((resolve) => {
      const picker = hostEl.createEl("input", {
        attr: {
          type: "file",
          webkitdirectory: "",
          style: "display:none",
        },
      }) as HTMLInputElement & { webkitdirectory: boolean };
      picker.webkitdirectory = true;
      const cleanup = () => {
        try {
          picker.remove();
        } catch {
          // ignore
        }
      };
      picker.addEventListener("change", () => {
        const file = picker.files?.[0] as
          | (File & { path?: string; webkitRelativePath?: string })
          | undefined;
        cleanup();
        if (!file) {
          resolve(null);
          return;
        }
        let fullPath = file.path || "";
        if (!fullPath) {
          try {
            const electron = require("electron") as {
              webUtils?: { getPathForFile?: (f: File) => string };
            };
            fullPath = electron?.webUtils?.getPathForFile?.(file) || "";
          } catch {
            fullPath = "";
          }
        }
        if (!fullPath) {
          resolve(null);
          return;
        }
        const rel = (file.webkitRelativePath || "").replace(/\\/g, "/");
        const parts = rel.split("/").filter(Boolean);
        let dir = path.dirname(fullPath);
        for (let i = 1; i < parts.length - 1; i += 1) {
          dir = path.dirname(dir);
        }
        resolve(dir);
      });
      picker.addEventListener("cancel", () => {
        cleanup();
        resolve(null);
      });
      picker.click();
    });
  }

  private _applyLibraryConfiguration(opts?: {
    autoCompleteOnSuccess?: boolean;
  }): void {
    if (this._setupOperation === "running") return;
    this._setupOperation = "running";
    this._setupFeedback = null;
    this._setupFailureDetail = null;
    const settings = this.plugin.settings;
    const paths: Record<string, string | undefined> = {
      zotero_data_dir: settings.zotero_data_dir,
      system_dir: settings.system_dir,
      resources_dir: settings.resources_dir,
      literature_dir: settings.literature_dir,
      base_dir: settings.base_dir,
    };
    // #142 / C0: mutations route through typed CLI commands; the plugin never
    // writes paperforge.json directly. Run `setup` FIRST so fresh vaults create
    // paperforge.json before configSet/configList read it (fixes config.not_found deadlock).
    void (async () => {
      let libraryConfigured = false;
      const problems: Array<{ key: string; reason: string }> = [];
      const envOverridden: string[] = [];

      let setupClientOwnsFailure = false;
      try {
        await this.plugin.saveSettings();
        const client = this.getClient();
        setupClientOwnsFailure = true;
        const hydrated =
          Boolean(this._getVaultBasePath()) &&
          !resolveVaultPaths(this._getVaultBasePath())?.configWarning;
        const defaultSysDir = hydrated ? "System" : ".paperforge";
        const handle = client.setup(
          {
            systemDir: settings.system_dir?.trim() || defaultSysDir,
            resourcesDir: settings.resources_dir?.trim() || "Resources",
            literatureDir: settings.literature_dir?.trim() || "Literature",
            baseDir: settings.base_dir?.trim() || "Bases",
            zoteroData: settings.zotero_data_dir?.trim() || undefined,
            agent: settings.agent_platform || "opencode",
            modular: true,
          },
          {
            onEvent: (ev) => {
              if (ev.event === "phase") {
                this._setupFeedback = `${t("setup_library_configuring") || "Configuring"}: ${ev.phase ?? ""}`;
                this.display();
              }
            },
          }
        );
        const outcome = await handle.outcome;
        if (!outcome.ok) {
          if (outcome.cancelled) {
            this._setupOperation = "idle";
            this._setupFeedback = t("setup_install_cancelled");
            this.display();
            return;
          }
          this._setupOperation = "failed";
          this._setupFeedback = t("setup_library_config_failed");
          const rawOutcome = outcome as unknown as {
            error?: unknown;
            reason?: unknown;
          };
          const detail =
            typeof rawOutcome?.error === "string"
              ? rawOutcome.error
              : typeof rawOutcome?.reason === "string"
                ? rawOutcome.reason
                : "";
          if (detail) this._setupFailureDetail = detail;
          this.display();
          return;
        }
        setupClientOwnsFailure = false;

        // Read back canonical config and sequentially reconcile any overridden/changed fields.
        let listed = await client.configList();
        const wantedEntries: Array<{ key: string; value: string }> = [];
        let patchedAny = false;
        for (const [key, raw] of Object.entries(paths)) {
          const wanted = raw?.trim();
          if (!wanted) continue;
          wantedEntries.push({ key, value: wanted });
          const existing = listed.fields.find((f) => f.key === key);
          if (String(existing?.stored_value ?? "").trim() !== wanted) {
            patchedAny = true;
            try {
              await client.configSet(key, wanted);
            } catch (e) {
              problems.push({ key, reason: this._formatSetupFailure(e) });
            }
          }
        }

        if (problems.length === 0 && wantedEntries.length > 0) {
          if (patchedAny) listed = await client.configList();
          for (const { key, value } of wantedEntries) {
            const field = listed.fields.find((f) => f.key === key);
            if (!field) {
              problems.push({ key, reason: "missing from the backend config" });
              continue;
            }
            const stored = String(field.stored_value ?? "").trim();
            if (stored !== value) {
              problems.push({
                key,
                reason:
                  `backend stored ${JSON.stringify(stored)}, expected ` +
                  JSON.stringify(value) +
                  (field.source === "environment"
                    ? ` (environment override ${field.environment ?? "set"} in effect)`
                    : ""),
              });
            }
            if (
              field.source === "environment" &&
              String(field.value ?? "").trim() !== value
            ) {
              envOverridden.push(`${key} (${field.environment ?? "env"})`);
            }
          }
        }

        // Save Zotero direct SQLite & Domain preferences alongside folder paths
        const extraKeys: Array<[string, string]> = [
          ["zotero_source_mode", settings.zotero_source_mode || "sqlite"],
          ["domain_mode", settings.domain_mode || "per_collection"],
          ["journal_metrics_mode", settings.journal_metrics_mode || "auto"],
          [
            "zotero_selected_collections",
            Array.isArray(settings.zotero_selected_collections)
              ? JSON.stringify(settings.zotero_selected_collections)
              : "",
          ],
        ];
        for (const [k, v] of extraKeys) {
          const existing = listed.fields.find((f) => f.key === k);
          if (existing && String(existing.stored_value ?? "") !== v) {
            await client.configSet(k, v).catch(() => undefined);
          }
        }

        if (problems.length > 0) {
          this._setupOperation = "failed";
          this._setupFeedback = t("setup_library_config_failed");
          this._setupFailureDetail = this._formatConfigFailures(problems);
          this.display();
          return;
        }

        libraryConfigured = true;
        applyPathConfigFromList(this.plugin.settings, listed.fields);
        this._setupOperation = "idle";
        this._setupFeedback =
          envOverridden.length > 0
            ? `${t("setup_library_configured")} · ${t("setup_library_config_env_override").replace("{keys}", envOverridden.join(", "))}`
            : t("setup_library_configured");
        this._attemptedProbes.add("library");
        this._probeModule("library");
        this.display();

        // Configuration alone cannot make the library ready: `sync` builds the
        // canonical index from the BBT exports. Always run it — deciding from a
        // just-requested probe races the async envelope update.
        this._setupOperation = "running";
        this._setupFeedback = t("setup_library_syncing");
        this.display();
        try {
          await this.getClient().sync();
        } catch (error) {
          console.error("PaperForge library sync failed:", error);
          this._setupOperation = "failed";
          this._setupFeedback = t("setup_library_sync_failed");
          const msg = this._formatSetupFailure(error);
          if (msg) this._setupFailureDetail = msg;
          this.display();
          return;
        }
        this._attemptedProbes.add("library");
        this._probeModule("library");
        this._setupOperation = "idle";
        this._setupFeedback = t("setup_library_configured");
        if (opts?.autoCompleteOnSuccess) {
          this.plugin.settings._setup_complete = true;
          await this.plugin.saveSettings();
        }
        this.display();
      } catch (error) {
        if (!setupClientOwnsFailure) {
          traceConsoleError({
            op: "library.setup",
            stage: "local",
            code: "backend_error",
            exitCode: null,
          });
        }
        this._setupOperation = "failed";
        this._setupFeedback = t(
          libraryConfigured
            ? "setup_library_refresh_failed"
            : "setup_library_config_failed"
        );
        const detail = this._formatSetupFailure(error);
        if (detail) this._setupFailureDetail = detail;
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
    /* The plugin name and version are already in the tab header, so the
       description stands alone rather than repeating the title. */
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

    // ── Non-blocking Veteran Vault Upgrade Banner (ADR-018) ──
    const cachedUpgradePlan =
      typeof this.plugin.getUpgradePlanCache === "function"
        ? this.plugin.getUpgradePlanCache()
        : null;
    const bannerDismissed =
      typeof this.plugin.isUpgradeBannerDismissed === "function"
        ? Boolean(this.plugin.isUpgradeBannerDismissed())
        : false;
    renderUpgradeAvailableBanner(containerEl, cachedUpgradePlan, {
      dismissed: bannerDismissed,
      onOpenModal: () => {
        void this.plugin.openUpgradeModal?.();
      },
      onDismiss: () => {
        this.plugin.dismissUpgradeBannerForSession?.();
        this.display();
      },
    });

    // ── Control Center (Issue #76) ──
    this._renderControlCenter(containerEl);

    // ── Deferred Storage Cleanup & Time-Machine Rollback ──
    if (cachedUpgradePlan && typeof this.plugin.getClient === "function") {
      renderStorageMigrationMaintenanceSection(
        containerEl,
        this.app,
        this.getClient(),
        cachedUpgradePlan,
        () => {
          void (async () => {
            await this.plugin.refreshUpgradePlan?.();
            this.display();
          })();
        }
      );
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

  private _resolveRuntimeCommand(): { path: string; args: string[] } | null {
    const run = resolveRuntimeCommand(readRuntimePointer());
    return run ? { path: run.command, args: [...run.args] } : null;
  }

  private _refreshRuntimeStatus(force = false): void {
    const expectedVersion = this.plugin.manifest.version;
    if (
      this._runtimeStatusLoading ||
      (!force && this._runtimeStatusVersion === expectedVersion)
    ) {
      return;
    }
    this._runtimeStatusVersion = expectedVersion;
    this._runtimeStatus = null;
    this._runtimeStatusError = null;
    const pointer = readRuntimePointer();
    if (!pointer || !fs.existsSync(pointer.pythonPath)) {
      // No published runtime: the persisted envelope is stale by definition.
      const env = this._capabilityState?.installation;
      if (
        env &&
        env.user_state === "ready" &&
        env.activity_state !== "running"
      ) {
        this._capabilityState = this._capabilityState ?? {};
        this._capabilityState.installation = this._setupRequiredEnvelope();
      }
      return;
    }

    this._runtimeStatusLoading = true;
    // A hung status call must not leave the panel without an action: after
    // 20s give up and surface it as an error the user can act on.
    if (this._runtimeStatusWatchdog) clearTimeout(this._runtimeStatusWatchdog);
    this._runtimeStatusWatchdog = setTimeout(() => {
      if (!this._runtimeStatusLoading) return;
      this._runtimeStatusLoading = false;
      this._runtimeStatusError = t("runtime_status_timeout");
      this.display();
    }, 20000);
    void Promise.resolve()
      .then(() => {
        const minEngine = this._minEngineVersion();
        return minEngine
          ? this.getClient().runtimeStatus(expectedVersion, {
              minEngineVersion: minEngine,
            })
          : this.getClient().runtimeStatus(expectedVersion);
      })
      .then((status) => {
        this._runtimeStatus = status;
        const env = this._capabilityState?.installation;
        if (
          env &&
          env.activity_state !== "running" &&
          status.runtime_ready &&
          env.user_state === "setup_required"
        ) {
          // The runtime is published now; the Python probe owns the new facts.
          this._probeModule("installation");
        }
      })
      .catch((error: unknown) => {
        this._runtimeStatusError =
          error instanceof Error ? error.message : String(error);
      })
      .finally(() => {
        if (this._runtimeStatusWatchdog) {
          clearTimeout(this._runtimeStatusWatchdog);
          this._runtimeStatusWatchdog = null;
        }
        this._runtimeStatusLoading = false;
        this.display();
      });
  }

  private _runtimeInstallerCommand(
    action: "install" | "update" | "repair" = "install"
  ): string {
    return runtimeInstallerSteps(action, this.plugin.manifest.version)
      .map((step) => step.replace("{{python}}", "python"))
      .join("\n");
  }

  /** The single entry point for runtime work, derived from the pointer state. */
  private _currentRuntimeAction(): RuntimeInstallerAction {
    const pointer = readRuntimePointer();
    const runtime = this._runtimeStatus;
    return !pointer
      ? "install"
      : runtime?.version_matches_expected === false
        ? "update"
        : "repair";
  }

  private _minEngineVersion(): string | undefined {
    const manifest = this.plugin?.manifest as
      | { minEngineVersion?: string }
      | undefined;
    return manifest?.minEngineVersion || undefined;
  }

  /** Open the background installer and watch the published pointer. */
  private _launchRuntimeInstaller(action: RuntimeInstallerAction): void {
    const result = this.getClient().launchRuntimeInstaller(
      action,
      this.plugin.manifest.version,
      { allowUvDownload: true }
    );
    if (!result.ok) {
      const message = t("runtime_installer_failed").replace(
        "{error}",
        result.error ?? "unknown"
      );
      // A transient Notice is not an outcome: the wizard keeps the reason
      // visible and stops pretending the operation is still running.
      this._setupOperation = "failed";
      this._setupFeedback = message;
      new Notice(message);
      this.display();
      return;
    }
    this._installerLogPath = result.logPath ?? null;
    new Notice(t("runtime_installer_opened"), 8000);
    if (this._setupOperation === "idle") this._setupOperation = "running";
    this._pollRuntimeUntilReady();
    this.display();
  }

  /** Poll while the installer window runs; stop on ready or after 25 min
   * (a cold candidate venv resolving the vector deps can take that long). */
  private _pollRuntimeUntilReady(): void {
    if (this._runtimePollTimer) return;
    const startedAt = Date.now();
    this._runtimePollTimer = setInterval(() => {
      if (this._runtimeStatus?.runtime_ready === true) {
        this._stopRuntimePoll(true);
        return;
      }
      // The installer prints its own outcome: waiting out the full budget
      // after it already died only hides the reason for 25 minutes.
      if (this._installerLogTail().includes(INSTALLER_FAILED_MARKER)) {
        this._stopRuntimePoll(false);
        return;
      }
      if (Date.now() - startedAt > 25 * 60 * 1000) {
        this._stopRuntimePoll(false);
        return;
      }
      this._refreshRuntimeStatus(true);
      this.display();
    }, 3000);
  }

  /** The installer's current phase translated into beginner-friendly progress text. */
  private _installerProgressLine(): string {
    if (!this._installerLogPath) return "";
    try {
      const lines = fs
        .readFileSync(this._installerLogPath, "utf-8")
        .split(/\r?\n/)
        .filter((line) => line.trim());
      const isZh = t("nav_close") === "关闭";
      for (let i = lines.length - 1; i >= 0 && i > lines.length - 60; i -= 1) {
        const line = lines[i].trim();
        if (
          line.includes("Installing paperforge") ||
          (line.startsWith("Downloading ") &&
            !line.includes("uv") &&
            !line.includes("wheel"))
        ) {
          return isZh
            ? "阶段 4/5：正在自动配置 PaperForge 核心与 AI 组件…"
            : "Step 4/5: Installing PaperForge core & AI dependencies…";
        }
        if (line.includes("Downloading wheel")) {
          return isZh
            ? "阶段 3/5：正在下载 PaperForge 计算引擎…"
            : "Step 3/5: Downloading PaperForge compute package…";
        }
        if (line.includes("Installing managed Python")) {
          return isZh
            ? "阶段 2/5：正在自动配置独立运行环境（无需手动安装）…"
            : "Step 2/5: Provisioning isolated Python runtime automatically…";
        }
        if (line.includes("Portable uv ready")) {
          return isZh
            ? "阶段 1/5：自动安装器已就绪，即将配置运行环境…"
            : "Step 1/5: Automatic bootstrapper ready…";
        }
        if (line.includes("Downloading uv")) {
          return isZh
            ? "阶段 1/5：正在准备零依赖自动安装器…"
            : "Step 1/5: Preparing zero-dependency automatic bootstrapper…";
        }
        if (
          /^\[PaperForge\]|^Collecting |^Installing collected|^Successfully installed/.test(
            line
          )
        ) {
          return isZh
            ? "正在后台自动安装与自检组件，请稍候…"
            : "Completing automatic background setup and verification…";
        }
      }
    } catch {
      // The log appears only once the installer starts.
    }
    return "";
  }

  /** Last lines the detached installer wrote (empty when unreadable). */
  private _installerLogTail(): string {
    if (!this._installerLogPath) return "";
    try {
      const text = fs.readFileSync(this._installerLogPath, "utf-8");
      return text.trim().split(/\r?\n/).slice(-6).join(" | ");
    } catch {
      return "";
    }
  }

  private _stopRuntimePoll(ready: boolean, cancelReason?: string): void {
    if (this._runtimePollTimer) {
      clearInterval(this._runtimePollTimer);
      this._runtimePollTimer = null;
    }
    if (this._setupOperation === "running") {
      this._setupOperation = cancelReason ? "idle" : ready ? "idle" : "failed";
      if (!ready) {
        if (cancelReason) {
          this._setupFeedback = cancelReason;
        } else {
          // Say why the poll gave up: a template with an empty slot tells the
          // user nothing and hides the failing command's own message.
          const detail =
            this._runtimeStatusError || this._installerLogTail() || "";
          this._setupFeedback = t("runtime_installer_failed").replace(
            "{error}",
            detail || "the runtime did not become ready in time"
          );
        }
      }
    } else if (cancelReason) {
      this._setupFeedback = cancelReason;
    }
    if (ready) this._setupReinstallRequested = false;
    this._refreshRuntimeStatus(true);
    this.display();
    if (ready) new Notice(t("runtime_install_complete"));
    else if (cancelReason) new Notice(cancelReason);
  }

  private _cancelRuntimePoll(): void {
    this._stopRuntimePoll(false, t("runtime_install_cancelled"));
  }

  /** Render the Installation detail view (Issue #77). */
  /** Render Foundation with the shared module-detail shell. */
  _renderInstallationDetail(containerEl: HTMLElement): void {
    // The shell renders the header first, so a stale "ready" envelope must be
    // corrected before it runs: the pointer is the fact, the envelope a cache.
    const pointer = readRuntimePointer();
    if (
      !pointer &&
      this._capabilityState?.installation?.user_state === "ready"
    ) {
      this._capabilityState = this._capabilityState ?? {};
      this._capabilityState.installation = this._setupRequiredEnvelope();
    }
    this._renderModuleDetailShell(containerEl, "installation", false);
    const env =
      this._capabilityState?.installation ??
      createUnknownEnvelope("installation");
    const body = containerEl.createDiv({ cls: "pf-module-body" });
    body.createEl("h3", { text: t("md_foundation_overview") });
    this._refreshRuntimeStatus();
    const runtime = this._runtimeStatus;
    const runtimeReady = runtime?.runtime_ready === true;
    body.createEl("p", {
      // "Verified" needs a live status, not a cached envelope: a failed or
      // timed-out check must not read as "installed and verified".
      text: runtimeReady
        ? t("md_foundation_ready")
        : (this._runtimeStatusError ??
          this._getModuleConsequence("installation", env)),
      cls: runtimeReady ? "pf-status-ok" : "setting-item-description",
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
      t("cc_badge_ready") || "Ready",
      this.plugin.manifest.version,
      "pf-status-ok"
    );

    const runtimeLabel = this._runtimeStatusLoading
      ? t("runtime_status_checking")
      : (runtime?.runtime_state ??
        this._runtimeStatusError ??
        (pointer
          ? t("runtime_status_needs_attention")
          : t("runtime_status_not_installed")));
    addCheck(
      t("foundation_python"),
      runtimeReady
        ? t("cc_badge_ready") || "Ready"
        : this._runtimeStatusLoading
          ? t("cc_badge_checking") || "Checking"
          : t("cc_badge_setup_required") || "Setup Required",
      runtime?.python_path ?? pointer?.pythonPath ?? runtimeLabel,
      runtimeReady
        ? "pf-status-ok"
        : this._runtimeStatusLoading
          ? "pf-status-checking"
          : "pf-status-warn"
    );

    const vp = this._getVaultBasePath();
    // Vault structure
    const systemDir = path.join(
      vp,
      this.plugin.settings.system_dir || "System"
    );
    const hasSystem = fs.existsSync(systemDir);
    addCheck(
      t("foundation_vault_structure"),
      hasSystem
        ? t("cc_badge_ready") || "Ready"
        : t("cc_badge_setup_required") || "Setup Required",
      hasSystem
        ? path.posix.join(
            this.plugin.settings.system_dir || "System",
            "PaperForge"
          )
        : t("foundation_vault_missing"),
      hasSystem ? "pf-status-ok" : "pf-status-error"
    );

    // Zotero data dir
    const hasZotero =
      this.plugin.settings.zotero_data_dir &&
      fs.existsSync(this.plugin.settings.zotero_data_dir);
    addCheck(
      t("foundation_zotero"),
      hasZotero
        ? t("cc_badge_ready") || "Ready"
        : t("cc_badge_setup_required") || "Setup Required",
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
      hasPaddle
        ? t("config_configured") || "Configured"
        : t("cc_badge_not_enabled") || "Not Set",
      hasPaddle ? t("config_configured") : t("foundation_paddle_missing"),
      hasPaddle ? "pf-status-ok" : "pf-status-error"
    );
    addCheck(
      t("foundation_openai_key"),
      hasOpenai
        ? t("config_configured") || "Configured"
        : t("cc_badge_not_enabled") || "Not Set",
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
      text: t("foundation_migrate_btn"),
    });
    migrateBtn.title = t("foundation_migrate_hint");
    migrateBtn.onclick = () => this._migrateLegacyCredentials(migrateBtn);

    // Obsidian version check removed (RC UX Seam): the previous block
    // hardcoded `obsidianOk = true` — a false green. Obsidian compatibility
    // is enforced by the manifest's minAppVersion at plugin load; Python-side
    // truth lives in the probe envelope, not a presentation-side constant.

    addCheck(
      t("foundation_python_packages"),
      runtime?.vector_ready
        ? t("cc_badge_ready") || "Ready"
        : this._runtimeStatusLoading
          ? t("cc_badge_checking") || "Checking"
          : t("cc_badge_not_enabled") || "Optional",
      runtime?.vector_ready ? t("runtime_vector_ready") : runtimeLabel,
      runtime?.vector_ready
        ? "pf-status-ok"
        : this._runtimeStatusLoading
          ? "pf-status-checking"
          : "pf-status-warn"
    );
    const runtimeAction: RuntimeInstallerAction = !pointer
      ? "install"
      : runtime?.version_matches_expected === false
        ? "update"
        : "repair";
    if (!runtimeReady) {
      if (this._runtimePollTimer) {
        body.createEl("p", {
          cls: "pf-setup-status",
          text: t("runtime_installing"),
        });
        renderActionButton(body, {
          label: t("runtime_cancel_btn"),
          variant: "secondary",
          onClick: () => this._cancelRuntimePoll(),
        });
      } else {
        renderActionButton(body, {
          label:
            runtimeAction === "install"
              ? t("runtime_install_btn")
              : runtimeAction === "update"
                ? t("runtime_update_btn")
                : t("runtime_repair_btn"),
          onClick: () => this._launchRuntimeInstaller(runtimeAction),
        });
      }
      body.createEl("p", {
        text: t("runtime_installer_hint"),
        cls: "setting-item-description",
      });
    }
    const manual = body.createEl("details", { cls: "pf-runtime-manual" });
    manual.createEl("summary", { text: t("runtime_manual_summary") });
    manual.createEl("pre").createEl("code", {
      text: this._runtimeInstallerCommand(runtimeAction),
    });

    // Sequential flow: the runtime is a hard prerequisite, so exactly one
    // entry point is visible at a time — install first, configure the vault
    // afterwards.
    if (!runtimeReady) {
      body.createEl("p", {
        text: t("runtime_next_step_hint"),
        cls: "setting-item-description",
      });
    } else if (env.user_state !== "ready") {
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
  }

  /** Render the Skills inventory for the selected agent platform. */
  private _renderSkillsList(containerEl: HTMLElement): void {
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

    // Show skills for selected platform (fallback to .agents/skills)
    const primarySkillRel =
      AGENT_PLATFORM_SKILL_DIRS[selectedPlatform] ?? ".agents/skills";
    const primarySkillDir = path.join(vaultPath, primarySkillRel);
    const fallbackSkillDir = path.join(vaultPath, ".agents/skills");
    const skillDir = fs.existsSync(primarySkillDir)
      ? primarySkillDir
      : fs.existsSync(fallbackSkillDir)
        ? fallbackSkillDir
        : primarySkillDir;
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

  /** Re-probe an optional module the first time its detail page renders in
   *  this session; later renders reuse the fresh envelope. */
  private _probeDetailOnce(mod: CapabilityModule): void {
    if (this._detailProbedThisSession.has(mod)) return;
    this._detailProbedThisSession.add(mod);
    this._probeModule(mod);
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
      this._probeDetailOnce("ocr");
      this._renderOcrDetail(containerEl);
    } else if (this._selectedDetailModule === "memory") {
      this._probeDetailOnce("memory");
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
      env.user_state !== "not_enabled" &&
      env.reason?.code !== "library.config_missing"
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
    // Ticket 06: sync state + corpus/orphan counts are Python probe facts —
    // no client-side database scans.
    const paperCount = (env.details as Record<string, unknown> | undefined)?.[
      "paper_count"
    ];
    const corpus = facts.createDiv({ cls: "pf-module-fact" });
    corpus.createEl("span", { text: t("md_library_corpus") });
    corpus.createEl("span", {
      text:
        typeof paperCount === "number"
          ? String(paperCount)
          : t("metric_not_available"),
    });
    const orphanCount = (
      this._capabilityState?.maintenance as
        | { orphan?: { count?: number } }
        | undefined
    )?.orphan?.count;
    const orphanRow = facts.createDiv({ cls: "pf-module-fact" });
    orphanRow.createEl("span", { text: t("md_library_orphans") });
    orphanRow.createEl("span", {
      text:
        typeof orphanCount === "number"
          ? String(orphanCount)
          : t("metric_not_available"),
    });
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
      // Client-owned cooperative Stop (#07 step 3): the shared
      // PaperForgeClient owns the single active operation.
      const client = this.getClient();
      if (
        typeof client?.isOperationActive === "function" &&
        client.isOperationActive()
      ) {
        const stop = card.createEl("button", {
          cls: "pf-action-btn mod-warning",
          text: t("ocr_stop_batch"),
        });
        stop.addEventListener("click", () => client.cancelActiveOperation());
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
      // Papers nobody has processed yet are outstanding WORK, not a fault:
      // the module stays "ready" and the run action is an ordinary button.
      if (env.reason?.code === "ocr.pending") {
        body.createEl("p", {
          text: this._getModuleConsequence("ocr", env),
          cls: "pf-setup-status",
        });
        renderActionButton(body, {
          label: env.action?.primary?.label || t("action_ocr_run") || "Run OCR",
          onClick: () => this._dispatchOcrAction("run"),
        });
      }
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
    // Option B: Advanced OCR Workspace stays accessible here under Settings -> OCR.
    const ocrActionRow = body.createDiv({ cls: "pf-module-action-row" });
    renderActionButton(ocrActionRow, {
      label:
        (t("md_ocr_workspace_advanced") ||
          t("md_ocr_workspace") ||
          "Advanced OCR Workspace") + " \u2197",
      variant: "secondary",
      onClick: () =>
        (this.app as any).workspace.getLeaf().setViewState({
          type: "paperforge-ocr-workspace",
        } as any),
    });
    if (!isRunning) {
      renderActionButton(ocrActionRow, {
        label: t("ocr_configure_credential"),
        variant: "secondary",
        onClick: () => this._startSetupJourney(3),
      });

      const ocrCfg = body.createDiv({ cls: "pf-sr-cfg pf-ocr-endpoint-cfg" });
      const ocrUrlRow = ocrCfg.createDiv({ cls: "pf-sr-cfg-row" });
      ocrUrlRow.createEl("label", {
        text: t("ocr_job_url_label") || "PaddleOCR Job URL",
        cls: "pf-sr-cfg-lbl",
      });
      const ocrUrlInput = ocrUrlRow.createEl("input", {
        cls: "pf-ocr-cfg-input",
        attr: {
          type: "text",
          "data-pf-testid": "ocr-job-url-input",
          placeholder: "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
        },
      }) as HTMLInputElement;
      ocrUrlInput.value = this.plugin.settings.paddleocr_job_url || "";
      ocrUrlInput.addEventListener("change", () => {
        this._setVectorDbConfig("paddleocr_job_url", ocrUrlInput);
      });

      const ocrModelRow = ocrCfg.createDiv({ cls: "pf-sr-cfg-row" });
      ocrModelRow.createEl("label", {
        text: t("ocr_model_label") || "PaddleOCR Model",
        cls: "pf-sr-cfg-lbl",
      });
      const ocrModelInput = ocrModelRow.createEl("input", {
        cls: "pf-ocr-cfg-input",
        attr: {
          type: "text",
          "data-pf-testid": "ocr-model-input",
          placeholder: "PaddleOCR-VL-1.6",
        },
      }) as HTMLInputElement;
      ocrModelInput.value = this.plugin.settings.paddleocr_model || "";
      ocrModelInput.addEventListener("change", () => {
        this._setVectorDbConfig("paddleocr_model", ocrModelInput);
      });
    }
  }
  /** Render the Memory detail view (Issue #78). */
  _renderAgentDetail(containerEl: HTMLElement): void {
    this._renderModuleDetailShell(containerEl, "agent");
    const body = containerEl.createDiv({ cls: "pf-module-body" });

    const current = this.plugin.settings.agent_platform || "opencode";
    const vaultBase = this._getVaultBasePath();
    const skillDirectory = path.join(
      vaultBase,
      AGENT_PLATFORM_SKILL_DIRS[current] ?? ".agents/skills"
    );
    const deployed =
      fs.existsSync(skillDirectory) ||
      fs.existsSync(path.join(vaultBase, ".agents/skills"));

    const facts = body.createDiv({ cls: "pf-module-facts" });
    const platform = facts.createDiv({ cls: "pf-module-fact" });
    platform.createEl("span", { text: t("md_agent_platform") });
    platform.createEl("span", {
      text: AGENT_PLATFORM_LABELS[current] ?? current,
    });
    const deployment = facts.createDiv({ cls: "pf-module-fact" });
    deployment.createEl("span", { text: t("md_agent_deployment") });
    deployment.createEl("span", {
      text: deployed ? t("agent_deployed") : t("agent_not_deployed"),
    });
    const connection = facts.createDiv({ cls: "pf-module-fact" });
    connection.createEl("span", { text: t("agent_live_connection") });
    connection.createEl("span", { text: t("md_agent_connection_unknown") });

    body.createEl("p", {
      cls: "caption",
      text: t("agent_external_cli_hint"),
    });

    if (this._agentPlatformDraft === null) {
      renderActionButton(body, {
        label: t("config_change"),
        variant: "secondary",
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
        : Object.keys(AGENT_PLATFORM_LABELS);
      for (const value of editorChoices) {
        const option = select.createEl("option", {
          text: AGENT_PLATFORM_LABELS[value] ?? value,
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
          // #142 / C0: mutation through the typed config command; the
          // mirror and the persisted settings follow backend acceptance,
          // never lead it.
          void this.getClient()
            .configSet("agent_platform", value)
            .then(
              () => {
                this.plugin.settings.agent_platform = value;
                this._agentPlatformDraft = null;
                void this.plugin.saveSettings();
                this.display();
              },
              (e) => {
                new Notice(
                  `PaperForge: config set agent_platform failed: ${String(e)}`
                );
                this.display();
              }
            );
        },
      });
      renderActionButton(actions, {
        label: t("config_cancel"),
        variant: "ghost",
        onClick: () => {
          this._agentPlatformDraft = null;
          this.display();
        },
      });
      renderActionButton(actions, {
        label: t("config_verify"),
        variant: "secondary",
        onClick: () => {
          const value = this._agentPlatformDraft ?? current;
          const dirRel = AGENT_PLATFORM_SKILL_DIRS[value] ?? ".agents/skills";
          const found =
            fs.existsSync(path.join(this._getVaultBasePath(), dirRel)) ||
            fs.existsSync(
              path.join(this._getVaultBasePath(), ".agents/skills")
            );
          new Notice(
            found ? t("agent_verify_found") : t("agent_verify_missing")
          );
        },
      });
    }

    this._renderSkillsList(body);
  }

  /**
   * Database row of the Smart Retrieval info card — derived from the same
   * backend state machine (env.reason.code) and build progress
   * (env.details.build_state.status) that drive the status paragraph, so
   * the card can never contradict it.
   */
  _memoryDbStatusText(env: ProbeEnvelope, bsStatus: string): string {
    const rc = env.reason?.code ?? "";
    if (env.user_state === "ready") return t("sr_db_exists") || "Active";
    if (bsStatus === "running") return t("sr_db_building") || "Building";
    if (bsStatus === "interrupted")
      return t("sr_db_partial") || "Partially built";
    if (bsStatus === "failed") return t("sr_db_failed") || "Build failed";
    if (rc === "memory.db_missing") return t("sr_db_missing") || "Not built";
    if (rc === "memory.db_corrupt") return t("sr_db_corrupt") || "Corrupted";
    if (rc === "memory.index_stale") return t("sr_db_stale") || "Index stale";
    return t("sr_db_missing") || "Not built";
  }

  /** Render the Memory detail view matching prototype layout. */
  _renderMemoryDetail(containerEl: HTMLElement): void {
    this._renderModuleDetailShell(containerEl, "memory", false);
    const env =
      this._capabilityState?.memory ?? createUnknownEnvelope("memory");
    const body = containerEl.createDiv({ cls: "pf-module-body" });
    const reasonCode = env.reason?.code ?? "";
    const client = this.getClient();
    const isOperationActive =
      typeof client?.isOperationActive === "function" &&
      client.isOperationActive();
    const isRunning = env.activity_state === "running" || isOperationActive;

    // ── Status text: single source of truth ──
    let statusText: string | null = null;
    let statusClass = "setting-item-description";
    if (isRunning) {
      statusText = env.activity_label ?? t("cc_activity_running");
      statusClass = "pf-status-ok";
    } else if (env.user_state === "ready") {
      statusText = t("md_retrieval_ready");
      statusClass = "pf-status-ok";
    } else {
      statusText =
        this._localizeReason(reasonCode, t("cc_module_memory")) ??
        env.reason?.text ??
        null;
      statusClass = "pf-status-warn";
    }
    if (statusText) {
      body.createEl("p", { text: statusText, cls: statusClass });
    }

    // ── Primary action button: single source of truth ──
    if (isRunning) {
      if (isOperationActive) {
        renderActionButton(body, {
          label: t("retrieval_stop"),
          onClick: () => {
            client.cancelActiveOperation();
          },
        });
      }
    } else if (
      env.reason?.code === "memory.index_stale" &&
      !env.action?.primary
    ) {
      // Index behind the database: ready with an ordinary rebuild action.
      // A backend-named primary action still wins (the state machine owns
      // the wording) — this is only the ready-with-notice shape.
      renderActionButton(body, {
        label: t("cc_action_rebuild_index") || "Rebuild index",
        onClick: () =>
          this._dispatchMemoryBuild("build", undefined, "memory.rebuild"),
      });
    } else if (
      env.action?.primary &&
      env.user_state !== "ready" &&
      env.user_state !== "not_enabled"
    ) {
      renderActionButton(body, {
        label: this._actionLabel(env.action.primary),
        onClick: () => this._dispatchModuleAction("memory", env),
      });
    }
    // ── Info card (read-only status): details-driven ──
    // Every row comes from env.details (backend authority, same probe that
    // produced the status text) — never from plugin caches that can lag or
    // contradict the state machine (e.g. 811/811 built but "API Key not
    // configured").
    const panelDetails = env.details ?? {};
    const bsStatus = (panelDetails.build_state?.status as string) ?? "idle";
    const dbStatus = this._memoryDbStatusText(env, bsStatus);
    const backend = "vec0";
    const apiKeyConfigured = Boolean(panelDetails.api_key_configured);
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

    // Preset selector at top of Memory config (class pf-sr-cfg-select preserves .pf-sr-cfg-input count = 3)
    const presetRow = cfgBody.createDiv({ cls: "pf-sr-cfg-row" });
    presetRow.createEl("label", {
      text: "服务商预设",
      cls: "pf-sr-cfg-lbl",
    });
    const presetSel = presetRow.createEl("select", {
      cls: "pf-sr-cfg-select",
      attr: { "data-pf-testid": "sr-provider-preset-select" },
    }) as HTMLSelectElement;
    const curPreset = matchEmbeddingPresetId(
      this.plugin.settings.vector_db_api_base || "",
      this.plugin.settings.vector_db_api_model || ""
    );
    for (const p of EMBEDDING_PRESETS) {
      const opt = presetSel.createEl("option", {
        text: t("nav_close") === "关闭" ? p.labelZh : p.labelEn,
        attr: { value: p.id },
      });
      opt.selected = p.id === curPreset;
    }

    // API Key — commit on Save button or blur/change (no mid-typing timer truncation)
    const kr = cfgBody.createDiv({ cls: "pf-sr-cfg-row" });
    kr.createEl("label", {
      text: t("feat_openai_key") || "API Key",
      cls: "pf-sr-cfg-lbl",
    });
    const ki = kr.createEl("input", {
      cls: "pf-sr-cfg-input",
      attr: {
        type: "password",
        "data-pf-testid": "sr-api-key-input",
        placeholder: apiKeyConfigured ? "\u2022\u2022\u2022\u2022" : "sk-...",
      },
    }) as HTMLInputElement;
    const commitApiKey = async () => {
      const v = ki.value.trim();
      if (!v) return;
      if (await this._storeVectorDbCredential(v)) {
        ki.value = "";
        ki.placeholder = "\u2022\u2022\u2022\u2022";
        cfgBody.style.display = "none";
        cfgIcon.textContent = "\u25b6";
      }
    };
    const kSave = kr.createEl("button", {
      cls: "pf-sr-cfg-save-btn",
      text: t("api_key_save_btn") || t("config_save") || "Save",
      attr: { type: "button", "data-pf-testid": "sr-api-key-save" },
    });
    kSave.addEventListener("click", () => {
      void commitApiKey();
    });
    ki.addEventListener("change", () => {
      void commitApiKey();
    });

    // Base URL
    const br = cfgBody.createDiv({ cls: "pf-sr-cfg-row" });
    br.createEl("label", {
      text: t("feat_api_base_url") || "API Base URL",
      cls: "pf-sr-cfg-lbl",
    });
    const bi = br.createEl("input", {
      cls: "pf-sr-cfg-input",
      attr: {
        type: "text",
        "data-pf-testid": "sr-api-base-input",
        placeholder: "https://api.openai.com/v1",
      },
    }) as HTMLInputElement;
    bi.value = this.plugin.settings.vector_db_api_base || "";
    bi.addEventListener("change", () => {
      this._setVectorDbConfig("vector_db_api_base", bi);
    });

    // Model
    const mr = cfgBody.createDiv({ cls: "pf-sr-cfg-row" });
    mr.createEl("label", {
      text: t("feat_api_model") || "Model",
      cls: "pf-sr-cfg-lbl",
    });
    const mi = mr.createEl("input", {
      cls: "pf-sr-cfg-input",
      attr: {
        type: "text",
        "data-pf-testid": "sr-api-model-input",
        placeholder: "text-embedding-3-small",
      },
    }) as HTMLInputElement;
    mi.value =
      this.plugin.settings.vector_db_api_model || "text-embedding-3-small";
    mi.addEventListener("change", () => {
      this._setVectorDbConfig("vector_db_api_model", mi);
    });

    presetSel.addEventListener("change", () => {
      const picked = EMBEDDING_PRESETS.find((p) => p.id === presetSel.value);
      if (!picked || picked.id === "custom") return;
      bi.value = picked.baseUrl;
      mi.value = picked.model;
      this._setVectorDbConfig("vector_db_api_base", bi);
      this._setVectorDbConfig("vector_db_api_model", mi);
    });

    // Live connectivity & vector dimension check right in the panel
    const testRow = cfgBody.createDiv({
      cls: "pf-sr-cfg-row pf-test-conn-row",
    });
    const testBtn = testRow.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: "测试连接并自动匹配维度",
      attr: { type: "button", "data-pf-testid": "sr-test-conn-btn" },
    });
    const testOut = testRow.createEl("span", {
      cls: "pf-test-conn-status",
      text: "",
    });
    testBtn.addEventListener("click", () => {
      testBtn.disabled = true;
      testOut.textContent = "探测中…";
      void this.getClient()
        .embedTestConnection()
        .then((res) => {
          testOut.className = "pf-test-conn-status is-ok";
          testOut.textContent = `✓ 已连通 · ${res.model} (${res.dimension} 维 · ${res.latency_ms}ms)`;
        })
        .catch((err) => {
          testOut.className = "pf-test-conn-status is-err";
          testOut.textContent = `✗ 连接失败：${String(err?.message || err).slice(0, 90)}`;
        })
        .finally(() => {
          testBtn.disabled = false;
        });
    });

    // Advanced compatibility toggle collapsed by default (beginners never need SDK vs requests)
    const advClientDetails = cfgBody.createEl("details", {
      cls: "pf-adv-inline-details",
    });
    advClientDetails.createEl("summary", {
      text: "高级接口模式（一般无需修改，系统已自动容错）",
    });
    const pr = advClientDetails.createDiv({ cls: "pf-sr-cfg-row" });
    pr.createEl("label", {
      text: t("mem_provider_type_label") || "API Client Mode",
      cls: "pf-sr-cfg-lbl",
    });
    const pi = pr.createEl("select", {
      cls: "pf-sr-cfg-select",
      attr: { "data-pf-testid": "sr-provider-type-select" },
    }) as HTMLSelectElement;
    for (const [val, label] of [
      ["openai_sdk", "openai_sdk (OpenAI SDK)"],
      ["requests", "requests (HTTP Direct / Proxy)"],
    ]) {
      const opt = pi.createEl("option", { text: label, attr: { value: val } });
      opt.selected =
        (this.plugin.settings.vector_db_provider_type || "openai_sdk") === val;
    }
    pi.addEventListener("change", () => {
      this._setVectorDbConfig("vector_db_provider_type", pi);
    });

    // ── Impact box (when action needed) ──
    // Same wording as the status paragraph — the backend reason is the
    // single explanation; no per-reasonCode copy that can drift (e.g.
    // "schema outdated" shown for a corrupt DB or a changed embedding
    // config).
    if (
      env.capability_state === "needs_action" &&
      env.user_state !== "not_enabled"
    ) {
      const impact = body.createDiv({ cls: "pf-sr-impact-box" });
      impact.createEl("strong", {
        text: t("cc_badge_action_required") || "Action Required",
      });
      const impactText =
        this._localizeReason(env.reason?.code ?? "", t("cc_module_memory")) ??
        env.reason?.text ??
        t("sr_impact_db_missing");
      impact.createEl("p", { text: impactText });
    }
    // ── Advanced Status (collapsible, detailed diagnostics) ──
    const details = body.createEl("details", { cls: "pf-sr-diagnostics" });
    details.createEl("summary", {
      text: t("cc_diagnostic_toggle") || "Advanced Status",
    });
    const diagBody = details.createDiv({ cls: "pf-sr-diagnostics-body" });

    // ── Debug trace: the client-side boundary log (metadata only) ──
    new Setting(diagBody)
      .setName("Debug trace")
      .setDesc(
        "Log every client↔backend operation (command, ok, duration, epoch, error code — never stdin/env/values) to the console. The last 200 records stay in memory for copying."
      )
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.debug_trace === true)
          .onChange(async (value) => {
            this.plugin.settings.debug_trace = value;
            setTraceEnabled(value);
            await this.plugin.saveSettings();
          })
      )
      .addButton((btn) =>
        btn.setButtonText("Copy").onClick(() => {
          const text = dumpTrace();
          void navigator.clipboard?.writeText(text || "(trace is empty)");
          new Notice(
            text
              ? `Copied ${text.split("\n").length} trace lines`
              : "Trace is empty"
          );
        })
      )
      .addButton((btn) =>
        btn.setButtonText("Clear").onClick(() => {
          clearTrace();
          new Notice("Trace cleared");
        })
      );

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
      void this.getClient()
        .memoryStatus()
        .then((d) => {
          setRow("FTS5 Papers", String(d?.paper_count_db ?? "?"));
          setRow("FTS5 Fresh", d?.fresh ? "Yes" : "Stale");
          setRow("Needs Rebuild", d?.needs_rebuild ? "Yes" : "No");
        })
        .catch(() => undefined);
      void this.getClient()
        .embedStatus()
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
    if (primary.action_id === "ocr.run") {
      this._dispatchOcrAction("run");
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
      if (actionId === "help.restore") {
        // Packaged help lives inside the Python distribution, so restoring it
        // is a runtime repair — the external installer owns that.
        this._launchRuntimeInstaller("repair");
        return;
      }
      if (mod === "library") {
        this._startSetupJourney(2);
      } else {
        this._startSetupJourney(mod === "ocr" || mod === "memory" ? 3 : 1);
      }
      return;
    }

    if (verb === "probe") {
      this._probeModule(mod);
      return;
    }

    if (verb === "update") {
      if (actionId === "foundation.update") {
        this._launchRuntimeInstaller("update");
        return;
      }
      new Notice(
        t("update_python_manual") ||
          "Python 3.11+ upgrade requires a manual install (python.org or your package manager)."
      );
      return;
    }

    if (
      (verb === "install" || actionId === "installation.install_runtime") &&
      mod === "installation"
    ) {
      this._launchRuntimeInstaller(this._currentRuntimeAction());
      return;
    }

    if (verb === "repair" || actionId === "foundation.repair") {
      // #223: `foundation.repair` is a REGISTERED action (the Probe emits it
      // with verb "repair", label "Repair Runtime"), but no branch handled that
      // verb, so it fell through to the unknown-pair re-probe. Route it like
      // foundation.update: the confirm modal already ran (destructive +
      // confirmation_required) and Python's policy owns the rest.
      this._runRepairAction();
      return;
    }

    if (verb === "install" && actionId === "memory.install_vector_deps") {
      this._launchRuntimeInstaller("repair");
      return;
    }

    if (mod === "library") {
      if (verb === "sync" || actionId === "library.sync") {
        this._runManualSync();
        return;
      }
    } else if (mod === "ocr") {
      // #223: an action ID the Probe emits must win over the generic verb. The
      // Probe sends `ocr.rebuild_derived` with verb "run" and `ocr.diagnose`
      // with the same "investigate" verb as `ocr.report_issue`, so verb-only
      // ordering routed both to the wrong handler.
      if (actionId === "ocr.rebuild_derived") {
        this._dispatchOcrAction("rebuild");
        return;
      }
      if (actionId === "ocr.diagnose") {
        // Declared "diagnostics report (verb 'investigate')" — the privacy-safe
        // support diagnostic, not the issue-draft flow.
        this._buildAndCopyDiagnostic();
        return;
      }
      if (verb === "run" || actionId === "ocr.run") {
        this._dispatchOcrAction("run");
        return;
      }
      if (verb === "rebuild_derived" || actionId === "ocr.rebuild_derived") {
        this._dispatchOcrAction("rebuild");
        return;
      }
      if (verb === "investigate") {
        const draft = buildRedactedDraft(
          env.reason.code,
          env.action?.primary?.scope_count ?? 0
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
        // embed.build / embed.resume (probe: missing/failed/interrupted
        // vector index) → remote embed rebuild/resume; memory.upgrade_backend
        // → ChromaDB→sqlite-vec migration; memory.build / memory.rebuild →
        // the local memory build.
        if (actionId === "embed.build") {
          this._dispatchMemoryBuild("embed", "force", "embed.build");
        } else if (actionId === "embed.resume") {
          this._dispatchMemoryBuild("embed", "resume", "embed.resume");
        } else if (
          actionId === "memory.build" ||
          actionId === "memory.rebuild"
        ) {
          // probe-owned legal local memory actions — exact ID, no substitution
          this._dispatchMemoryBuild("build", undefined, actionId);
        } else if (actionId === "memory.upgrade_backend") {
          this._runBackendMigration();
        } else {
          // fail-closed: never substitute an unknown memory action (#05 corrective)
          new Notice(
            (t("action_unknown_pair") || "Unknown action: {verb}").replace(
              "{verb}",
              actionId || verb
            ),
            5000
          );
          this._probeModule(mod);
          return;
        }
        return; // dispatched run/rebuild_index — never fall through to unknown-pair probe
      }
      if (verb === "restore_backup" || actionId === "memory.restore_backup") {
        void this.getClient()
          .memoryRestoreBackup()
          .then(() => new Notice(t("memory_restore_done")))
          .catch((error: unknown) => {
            new Notice(
              t("memory_restore_failed").replace(
                "{error}",
                error instanceof Error ? error.message : "Unknown error"
              ),
              6000
            );
          })
          .finally(() => {
            this._refreshAllReadModels();
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
  }

  /** #174 RC: ChromaDB -> sqlite-vec backend migration (embed migrate). */
  _runBackendMigration(): void {
    void this.getClient()
      .embedMigrate()
      .then(() => {
        new Notice(t("migrate_done") || "Backend migrated to sqlite-vec");
        this._refreshAllReadModels();
      })
      .catch((err: Error) => {
        new Notice(
          (t("migrate_failed") || "Backend migration failed") +
            ": " +
            (err.message || "unknown error")
        );
        this._refreshAllReadModels();
      });
  }

  /** #223: dispatch foundation.repair through the action runner.
   * Registered action, same shape as foundation.update: the confirm modal
   * already ran (destructive + confirmation_required) and Python's
   * perform_repair owns policy, while the client's OperationLock owns the
   * single active operation. */
  _runRepairAction(): void {
    void this.getClient()
      .runAction({
        action_id: "foundation.repair",
        scope: { kind: "all" },
        confirm: "foundation.repair",
      })
      .then((result) => {
        if (result.ok) {
          new Notice(t("repair_done") || "PaperForge runtime repaired");
        } else {
          const reason =
            typeof result.payload?.availability_reason === "string"
              ? result.payload.availability_reason
              : `exit code ${result.exitCode}`;
          new Notice((t("repair_failed") || "Repair failed") + ": " + reason);
        }
        this._refreshAllReadModels();
      })
      .catch((err: Error) => {
        new Notice(
          (t("repair_failed") || "Repair failed") + ": " + err.message
        );
        this._refreshAllReadModels();
      });
  }

  /** Dispatch OCR actions through the shared PaperForgeClient (#07 step 3):
   * the same canonical action registry, #137 NDJSON progress, availability
   * gating, and cooperative Stop the OCR Workspace uses — no second
   * child-process owner. */
  _dispatchOcrAction(mode: "run" | "rebuild"): void {
    if (mode === "run" && typeof this.plugin.requestOcrRun === "function") {
      // The probe-owned confirmation already ran in _dispatchModuleAction.
      this.plugin.requestOcrRun(true);
      return;
    }
    const client = this.getClient();
    if (client.isOperationActive()) {
      new Notice(t("ocr_already_running"));
      return;
    }

    const labelMap: Record<string, string> = {
      run: t("ocr_activity_run"),
      rebuild: t("ocr_activity_rebuild"),
    };

    // Set envelope activity overlay without changing capability/severity/reason
    const envelopes = this._capabilityState ?? {};
    if (envelopes["ocr"]) {
      envelopes["ocr"].activity_state = "running";
      envelopes["ocr"].activity_label =
        labelMap[mode] || t("cc_activity_running");
      envelopes["ocr"].activity_progress = { current: 0, total: 1 };
    }
    this.plugin._ocrProgress = { current: 0, total: 1, key: "" };
    this.display();

    const completeNotice: Record<string, string> = {
      run: t("ocr_run_complete"),
      rebuild: t("ocr_rebuild_complete"),
    };

    // #99 owner decision: redo is internal-only — the registry has no
    // `ocr.redo` primary and the thin client never encodes one. A stale
    // `ocr.redo` envelope falls through to the unknown-pair fail-closed
    // re-probe in _runAllowedDispatch; the user-facing Redo affordance in
    // the OCR Workspace uses the canonical `ocr.run` descriptor.
    const actionId = mode === "rebuild" ? "ocr.rebuild_derived" : "ocr.run";
    const request: ActionRequest = {
      action_id: actionId,
      scope: { kind: "all" },
      confirm: actionId,
    };
    let sawCancelled = false;
    const failedKeys: string[] = [];
    let skippedCount = 0;
    client
      .runAction(request, {
        onEvent: (event) => {
          if (event.event === "cancelled") sawCancelled = true;
          if (
            event.event === "start" ||
            event.event === "phase" ||
            event.event === "progress" ||
            event.event === "item_result"
          ) {
            this.plugin._ocrProgress = {
              current: Number(
                event.current ?? this.plugin._ocrProgress.current
              ),
              total: Number(event.total ?? this.plugin._ocrProgress.total),
              key: String(event.item_id ?? this.plugin._ocrProgress.key),
            };
            if (event.event === "item_result") {
              if (event.status === "succeeded" || event.status === "noop") {
                // settled fine
              } else if (event.status === "skipped") {
                skippedCount += 1;
              } else {
                failedKeys.push(String(event.item_id ?? ""));
              }
            }
            if (envelopes["ocr"]) {
              envelopes["ocr"].activity_progress = {
                current: this.plugin._ocrProgress.current,
                total: this.plugin._ocrProgress.total,
              };
            }
            this.display();
          }
        },
      })
      .then((result) => {
        if (envelopes["ocr"]) {
          envelopes["ocr"].activity_state = "idle";
          envelopes["ocr"].activity_label = null;
          envelopes["ocr"].activity_progress = null;
        }
        if (result.ok) {
          new Notice(completeNotice[mode] || "OCR completed");
        } else if (result.cancelled || sawCancelled) {
          new Notice(t("ocr_stopped_notice"));
        } else {
          // #126: surface the real reason instead of a generic failure —
          // failed keys, then the registry's availability_reason, then the
          // exit code.
          const failed = failedKeys.filter(Boolean).join(", ");
          const payload = result.payload as Record<string, unknown> | null;
          const payloadError = payload?.error as
            | { message?: unknown }
            | undefined;
          const payloadReason =
            typeof payload?.availability_reason === "string"
              ? payload.availability_reason
              : typeof payloadError?.message === "string"
                ? payloadError.message
                : "";
          const base = failed || payloadReason;
          const detail =
            skippedCount > 0
              ? `${base ? base + " " : ""}(${skippedCount} skipped)`
              : base || `exit code ${result.exitCode}`;
          new Notice(t("ocr_failed_notice") + ": " + detail, 8000);
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
  }
  /** Dispatch memory build: distinct build vs embed modes, overlay activity, terminal re-probe (Issue #78). */
  /** RC UX Seam: `embedMode` distinguishes a full rebuild (--force) from a
   * resume (--resume).  The backend action (embed.build vs embed.resume)
   * decides which flag; the frontend never guesses. */
  _dispatchMemoryBuild(
    kind: "build" | "embed",
    embedMode?: "force" | "resume",
    actionIdOverride?: string
  ): void {
    const client = this.getClient();
    if (!client) {
      new Notice(t("runtime_not_available") || "Environment unavailable");
      return;
    }
    if (
      typeof client?.isOperationActive === "function" &&
      client.isOperationActive()
    ) {
      new Notice(t("embed_already_running") || "Operation already running");
      return;
    }

    const envelopes = this._capabilityState ?? {};
    const primaryActionId = envelopes["memory"]?.action?.primary?.action_id;
    let actionId: string;
    if (actionIdOverride) {
      actionId = actionIdOverride;
    } else if (kind === "embed") {
      if (embedMode === "resume") {
        actionId = "embed.resume";
      } else if (embedMode === "force") {
        actionId = "embed.build";
      } else if (
        primaryActionId === "embed.resume" ||
        primaryActionId === "embed.build"
      ) {
        actionId = primaryActionId;
      } else {
        actionId = "embed.build";
      }
    } else {
      if (
        primaryActionId === "memory.build" ||
        primaryActionId === "memory.rebuild"
      ) {
        actionId = primaryActionId;
      } else {
        actionId = "memory.rebuild";
      }
    }

    const ALLOWED_ACTIONS: Record<"embed" | "build", ReadonlySet<string>> = {
      embed: new Set(["embed.build", "embed.resume"]),
      build: new Set(["memory.build", "memory.rebuild"]),
    };

    if (!ALLOWED_ACTIONS[kind].has(actionId)) {
      new Notice(
        (t("action_unknown_pair") || "Unknown action: {verb}").replace(
          "{verb}",
          actionId
        )
      );
      return;
    }
    if (envelopes["memory"]) {
      envelopes["memory"].activity_state = "running";
      envelopes["memory"].activity_label =
        kind === "embed"
          ? t("embed_activity_building") || "Building vector index…"
          : "Building memory…";
    }
    this.display();

    let sawCancelled = false;
    const runPromise = client.runAction(
      {
        action_id: actionId,
        scope: { kind: "all" },
        confirm: actionId,
      },
      {
        onEvent: (event) => {
          if (event.event === "cancelled") sawCancelled = true;
          if (event.event === "progress") {
            const current = Number(event.current ?? 0);
            const total = Number(event.total ?? 1);
            this.plugin._embedProgress = {
              current,
              total,
              key: String(event.item_id ?? ""),
            };
            if (envelopes["memory"]) {
              envelopes["memory"].activity_progress = { current, total };
            }
            this.display();
          }
        },
      }
    );

    void (async () => {
      try {
        const result = await runPromise;
        if (envelopes["memory"]) {
          envelopes["memory"].activity_state = "idle";
          envelopes["memory"].activity_label = null;
          envelopes["memory"].activity_progress = null;
        }

        if (result.ok) {
          new Notice(
            kind === "embed"
              ? t("embed_build_complete")
              : t("feat_memory_rebuild_done")
          );
        } else if (result.cancelled || sawCancelled) {
          new Notice(t("embed_build_stopped"), 8000);
        } else {
          const payload = result.payload as Record<string, unknown> | null;
          const payloadError = payload?.error as
            | { message?: unknown }
            | undefined;
          const reason =
            typeof payload?.availability_reason === "string"
              ? payload.availability_reason
              : typeof payloadError?.message === "string"
                ? payloadError.message
                : `exit code ${result.exitCode}`;
          new Notice(
            (t("sr_build_failed_notice") || "Build failed: {detail}").replace(
              "{detail}",
              reason
            ),
            8000
          );
        }
      } catch (err: any) {
        if (envelopes["memory"]) {
          envelopes["memory"].activity_state = "idle";
          envelopes["memory"].activity_label = null;
          envelopes["memory"].activity_progress = null;
        }
        new Notice(
          (t("sr_build_failed_notice") || "Build failed: {detail}").replace(
            "{detail}",
            err?.message ?? String(err)
          ),
          8000
        );
      } finally {
        this._refreshAllReadModels();
        this.display();
      }
    })();
  }
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
      text: t("help_section_label"),
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

    const helpEnvelope = this._capabilityState?.help;
    const helpAction = helpEnvelope?.action?.primary;
    if (
      helpEnvelope &&
      helpAction?.action_id === "help.restore" &&
      helpAction.availability === "available"
    ) {
      const actionKey = "action_" + helpAction.action_id.replace(/[.-]/g, "_");
      const translated = t(actionKey);
      const restore = containerEl.createDiv({ cls: "pf-help-restore" });
      restore.createEl("p", {
        text: t("help_restore_missing"),
      });
      renderActionButton(restore, {
        label: translated !== actionKey ? translated : helpAction.label,
        onClick: () => this._dispatchModuleAction("help", helpEnvelope),
      });
    }
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

  _runManualSync() {
    const vp =
      (this.app.vault.adapter as unknown as { basePath?: string }).basePath ??
      "";
    const client = this.getClient();
    if (!client) {
      new Notice(t("runtime_not_available") || "Environment unavailable");
      return;
    }

    // Overlay envelope activity
    const envelopes = this._capabilityState ?? {};
    if (envelopes["library"]) {
      envelopes["library"].activity_state = "running";
      envelopes["library"].activity_label = "Syncing library…";
    }

    this.plugin._autoSyncRunning = true;
    this._libraryRunning = true;
    this.display();

    void (async () => {
      let exitCode = 1;
      try {
        const result = await client.sync();
        exitCode = result?.ok === false ? 1 : 0;
        if (exitCode === 0) {
          this._lastSyncTime = new Date().toLocaleTimeString();
          this.plugin._lastSyncTime = this._lastSyncTime;
          // #127: consume backend next_actions. Automatic local work starts
          // now; consent-required work remains visible in the module card.
          void orchestrateFromSync(JSON.stringify(result), {
            runAction: (req) => client.runAction(req),
          });
        }
      } catch (err: unknown) {
        new Notice(
          `Sync failed: ${err instanceof Error ? err.message : String(err)}`,
          8000
        );
      } finally {
        this.plugin._autoSyncRunning = false;
        this._libraryRunning = false;
        this._memoryStatusText = null;
        if (envelopes["library"]) {
          envelopes["library"].activity_state = "idle";
          envelopes["library"].activity_label = null;
        }
        // #161: completed mutation → invalidate all + probe all; the
        // library exit code is forwarded for sync-failure detection (#78).
        this._refreshAllReadModels(exitCode);
        this._refreshSnapshots(vp);
        checkOrphanState(this.app, this.plugin, vp);
      }
    })();
  }

  _refreshSnapshots(_vp: string) {
    // #161/R: snapshot readers are retired; status text comes from probe
    // envelopes. `runtime-health` remains an on-demand diagnostic warm-up,
    // dispatched through the shared client — the transport owns the
    // runtime resolution and sanitized env.
    this._refreshPending = true;
    void this.getClient()
      .runtimeHealth()
      .catch(() => undefined)
      .finally(() => {
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
      });
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

    const resolved = this._resolveRuntimeCommand();
    if (!resolved) {
      this._probing.delete(mod);
      if (mod === "installation") {
        this._updateCapabilityEnvelope(mod, this._setupRequiredEnvelope());
      } else if (mod === "help") {
        // Help/docs do not need the runtime; keep the honest invalid state.
        this._updateCapabilityEnvelope(mod, createInvalidEnvelope(mod));
      } else {
        this._updateCapabilityEnvelope(
          mod,
          this._blockedByRuntimeEnvelope(mod)
        );
      }
      return;
    }

    const client = this.getClient();
    const minEngine = this._minEngineVersion();
    client
      .probe(mod, {
        expectedVersion:
          mod === "installation" ? this.plugin.manifest?.version : undefined,
        ...(mod === "installation" && minEngine
          ? { minEngineVersion: minEngine }
          : {}),
        lastOperationExitCode:
          mod === "library" &&
          lastOperationExitCode != null &&
          lastOperationExitCode !== 0
            ? lastOperationExitCode
            : undefined,
      })
      .then((envelope) => {
        this._probing.delete(mod);
        if (isValidEnvelope(envelope, mod)) {
          this._updateCapabilityEnvelope(mod, envelope);
        } else {
          // Ownership: probe bypasses the typed PFResult choke point (raw
          // envelope read), so this local validation owns the terminal.
          // Never dump the envelope — fixed metadata only.
          traceConsoleError({
            op: `probe.${mod}`,
            stage: "protocol",
            code: "protocol_error",
            exitCode: 0,
          });
          this._updateCapabilityEnvelope(mod, createInvalidEnvelope(mod));
        }
      })
      .catch((err: Error) => {
        this._probing.delete(mod);
        if (
          mod === "installation" &&
          (err.message?.includes("runtime not ready") ||
            err.message?.includes("no managed runtime pointer") ||
            err.message?.includes("not ready"))
        ) {
          this._updateCapabilityEnvelope(mod, this._setupRequiredEnvelope());
        } else {
          this._updateCapabilityEnvelope(mod, createInvalidEnvelope(mod));
        }
      });
  }

  /** A module cannot be probed until Foundation publishes a runtime: report
   * that prerequisite instead of a bogus detection failure. */
  private _blockedByRuntimeEnvelope(mod: CapabilityModule): ProbeEnvelope {
    return {
      schema_version: 2,
      module: mod,
      capability_state: "unknown",
      activity_state: "idle",
      activity_label: null,
      activity_progress: null,
      severity: "warning",
      reason: {
        code: "installation.required",
        text: t("module_blocked_by_runtime"),
      },
      action: { primary: runtimeInstallAction(t("runtime_install_btn")) },
      notices: [],
      user_state: "setup_required",
      capability_kind: mod === "library" ? "required" : "optional",
      maintenance_eligible: false,
      user_visible_failure: false,
      user_impact: null,
      updated_at: new Date().toISOString(),
      ttl_seconds: 60,
    };
  }

  /** One installation envelope for "no usable runtime" — the plugin only
   * guides; installing/updating/repairing happens through the external CLI. */
  private _setupRequiredEnvelope(): ProbeEnvelope {
    return {
      schema_version: 2,
      module: "installation",
      capability_state: "unknown",
      activity_state: "idle",
      activity_label: null,
      activity_progress: null,
      severity: "error",
      reason: {
        code: "installation.no_python",
        text: t("runtime_not_ready_reason"),
      },
      action: { primary: runtimeInstallAction(t("runtime_install_btn")) },
      notices: [],
      user_state: "setup_required",
      capability_kind: "required",
      maintenance_eligible: false,
      user_visible_failure: true,
      user_impact: t("runtime_not_ready_impact"),
      updated_at: new Date().toISOString(),
      ttl_seconds: 60,
    };
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
  /** Localized label for a backend action: the wire label is English. */
  private _actionLabel(primary: ActionPrimary): string {
    const idKey =
      "action_" + (primary.action_id ?? primary.verb).replace(/[.-]/g, "_");
    const byId = t(idKey);
    if (byId !== idKey) return byId;
    const verbKey = "cc_action_" + primary.verb;
    const byVerb = t(verbKey);
    if (byVerb !== verbKey) return byVerb;
    return primary.label;
  }

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

    // Action button — route real probe actions through the shared dispatcher.
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
        this._dispatchModuleAction(mod, env);
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
      this._attemptedProbes.delete("help");
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

    // ── Page heading + lede ──
    // ONE heading per page, at the settings-heading scale (15px/600).  The
    // page name used to be a grey 12px eyebrow under a second title, which
    // left four overlapping text blocks before any content.
    cc.createEl("h2", {
      cls: "pf-cc-heading",
      text: t("cc_heading") || "Control center",
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
    const foundationBlocked = !foundationReady && !baselineChecking;
    const summaryTitle = baselineReady
      ? t("cc_summary_ready")
      : baselineChecking
        ? t("cc_summary_checking")
        : foundationBlocked
          ? t("cc_summary_setup_first")
          : t("cc_summary_connect_library");
    const summaryBody = baselineReady
      ? t("cc_summary_ready_body")
      : baselineChecking
        ? t("cc_summary_checking_body")
        : foundationBlocked
          ? t("module_blocked_by_runtime")
          : t("cc_summary_connect_library_body");
    summaryCopy.createEl("strong", { text: summaryTitle });
    summaryCopy.createEl("span", { cls: "caption", text: summaryBody });

    if (!baselineReady && !baselineChecking) {
      const startStage = foundationReady ? 2 : 1;
      renderActionButton(summaryEl, {
        label:
          this.plugin.settings._setup_complete === false
            ? t("cc_start_setup")
            : t("cc_continue_setup"),
        onClick: () => this._startSetupJourney(startStage),
      });
    }

    const summaryMeta = summaryEl.createDiv({ cls: "pf-cc-summary-meta" });

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
      cls: "pf-cc-section-title",
      text: t("cc_modules_header") || "Modules",
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

    // ── Appearance Palette Mode, Liquid Glass & Reduce Motion ──
    const appearanceGroup = cc.createDiv({ cls: "pf-cc-appearance-group" });

    const themeBar = appearanceGroup.createDiv({ cls: "pf-cc-theme-bar" });
    const themeCopy = themeBar.createDiv({ cls: "pf-cc-theme-copy" });
    themeCopy.createEl("div", {
      cls: "pf-cc-theme-label",
      text: t("settings_theme_label") || "外观与材质",
    });
    themeCopy.createEl("div", {
      cls: "pf-cc-theme-desc",
      text:
        t("settings_theme_desc") ||
        "默认同步当前 Obsidian 主题色与原生圆角，也可切换为 AsterLab 纯净或经典暖灰。",
    });
    const themeSelect = themeBar.createEl("select", {
      cls: "pf-cc-theme-select",
      attr: { "data-pf-testid": "settings-theme-mode" },
    }) as HTMLSelectElement;
    for (const [val, label] of [
      [
        "obsidian",
        t("settings_theme_obsidian") || "跟随 Obsidian 主题与原生圆角（推荐）",
      ],
      [
        "asterlab",
        t("settings_theme_asterlab") || "AsterLab 纯净白纸 · 深空曜石",
      ],
      ["warm", t("settings_theme_warm") || "AsterLab 经典暖纸色盘"],
    ] as const) {
      const opt = themeSelect.createEl("option", { text: label });
      opt.value = val;
    }
    const curTheme = this.plugin.settings.ui_theme_mode;
    themeSelect.value =
      curTheme === "asterlab"
        ? "asterlab"
        : curTheme === "warm"
          ? "warm"
          : "obsidian";
    themeSelect.addEventListener("change", () => {
      const next = themeSelect.value;
      this.plugin.settings.ui_theme_mode =
        next === "asterlab"
          ? "asterlab"
          : next === "warm"
            ? "warm"
            : "obsidian";
      (
        this.plugin as unknown as { applyUiThemeMode?: () => void }
      ).applyUiThemeMode?.();
      void this.plugin.saveSettings();
    });

    const glassRow = appearanceGroup.createDiv({ cls: "pf-cc-theme-bar" });
    const glassCopy = glassRow.createDiv({ cls: "pf-cc-theme-copy" });
    glassCopy.createEl("div", {
      cls: "pf-cc-theme-label",
      text: t("settings_liquid_glass_label") || "Liquid Glass 液态玻璃材质",
    });
    glassCopy.createEl("div", {
      cls: "pf-cc-theme-desc",
      text:
        t("settings_liquid_glass_desc") ||
        "为工具栏与悬浮气泡开启半透折射与微光描边；暗黑模式自动切换为烟熏深灰清透层。",
    });
    const glassSwitch = glassRow.createEl("input", {
      type: "checkbox",
      cls: "pf-switch",
      attr: { "data-pf-testid": "settings-liquid-glass" },
    }) as HTMLInputElement;
    glassSwitch.checked = this.plugin.settings.ui_liquid_glass !== false;
    glassSwitch.addEventListener("change", () => {
      this.plugin.settings.ui_liquid_glass = glassSwitch.checked;
      (
        this.plugin as unknown as { applyUiThemeMode?: () => void }
      ).applyUiThemeMode?.();
      void this.plugin.saveSettings();
    });

    const motionRow = appearanceGroup.createDiv({ cls: "pf-cc-theme-bar" });
    const motionCopy = motionRow.createDiv({ cls: "pf-cc-theme-copy" });
    motionCopy.createEl("div", {
      cls: "pf-cc-theme-label",
      text: t("settings_reduce_motion_label") || "减弱物理动效（无障碍）",
    });
    motionCopy.createEl("div", {
      cls: "pf-cc-theme-desc",
      text:
        t("settings_reduce_motion_desc") ||
        "跳过四档物理弹簧与微缩按压动画，仅保留瞬时状态切换。",
    });
    const motionSwitch = motionRow.createEl("input", {
      type: "checkbox",
      cls: "pf-switch",
      attr: { "data-pf-testid": "settings-reduce-motion" },
    }) as HTMLInputElement;
    motionSwitch.checked = this.plugin.settings.reduce_motion === true;
    motionSwitch.addEventListener("change", () => {
      this.plugin.settings.reduce_motion = motionSwitch.checked;
      (
        this.plugin as unknown as { applyUiThemeMode?: () => void }
      ).applyUiThemeMode?.();
      void this.plugin.saveSettings();
    });
  }

  private _applyOverviewQuickFilter(
    containerEl: HTMLElement,
    rawQuery: string
  ): void {
    const q = rawQuery.trim().toLowerCase();
    const MODULE_KEYWORDS: Record<string, string> = {
      installation: "runtime python core 环境 安装 更新",
      library: "zotero bbt pdf sync exports 同步 文献库 路径",
      ocr: "paddle ocr fulltext 解析 扫描",
      memory: "vector embedding sqlite search api 向量 检索 认知",
      agent: "claude codex opencode cursor skill agents 技能",
    };
    const cards = Array.from(
      containerEl.querySelectorAll<HTMLElement>(
        ".pf-cc-module-card, .pf-maintenance-inbox-item"
      )
    );
    for (const card of cards) {
      if (!q) {
        card.classList.remove("pf-is-filtered-out");
        card.style.display = "";
        continue;
      }
      const mod = card.getAttribute("data-module") || "";
      const haystack = (
        (card.textContent || "") +
        " " +
        mod +
        " " +
        (MODULE_KEYWORDS[mod] || "")
      ).toLowerCase();
      const matched = haystack.includes(q);
      if (matched) {
        card.classList.remove("pf-is-filtered-out");
        card.style.display = "";
      } else {
        card.classList.add("pf-is-filtered-out");
        card.style.display = "none";
      }
    }
  }

  /** Derive Agent availability from the shared .agents/skills or legacy per-platform skill dir. */
  _getAgentPlaceholderEnvelope(): ProbeEnvelope {
    const vaultBase = this._getVaultBasePath();
    const platform = this.plugin.settings.agent_platform || "opencode";
    const configuredSkillDir = String(
      this._pfConfig?.skill_dir ||
        this.plugin.settings.skill_dir ||
        ".agents/skills"
    );
    const legacyDir =
      AGENT_PLATFORM_SKILL_DIRS[platform] ?? AGENT_PLATFORM_SKILL_DIRS.opencode;
    const candidateDirs =
      configuredSkillDir === legacyDir
        ? [configuredSkillDir]
        : [configuredSkillDir, legacyDir];
    const deployed = candidateDirs.some((dir) =>
      fs.existsSync(path.join(vaultBase, dir, "paperforge", "SKILL.md"))
    );
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
    // Chevron
    card.createEl("span", { cls: "pf-cc-card-arrow", text: "\u203A" });
    card.addEventListener("click", () => this._handleCardNavigation(mod));
  }

  /** #86: Plain-language consequence based on module state. */
  _getUserStateLabel(state: string): string {
    return t("cc_badge_" + state);
  }

  _getModuleConsequence(mod: string, env: ProbeEnvelope): string {
    // A missing runtime blocks every downstream module: say that instead of
    // the generic "needs configuration" sentence for this module.
    if (env.reason?.code === "installation.required") {
      return env.reason.text || t("module_blocked_by_runtime");
    }
    const state =
      env.user_state ??
      (env.capability_state === "ready" ? "ready" : "action_required");
    // A ready module that carries a notice has something specific to say
    // ("19 of 968 papers have no OCR output yet") — prefer it over the
    // generic ready sentence.
    const hasNotice = (env.notices ?? []).length > 0;
    if (!(state === "ready" && hasNotice)) {
      const key = "cc_consequence_" + mod + "_" + state;
      const translated = t(key);
      if (translated && translated !== key) return translated;
    }
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
    const client = this.getClient();
    client.invalidateCache();
    const vp =
      (this.app.vault.adapter as unknown as { basePath?: string }).basePath ??
      "";
    if (!vp) {
      this._probing.clear();
      return;
    }
    this._probing.clear();
    const resolved = this._resolveRuntimeCommand();
    if (!resolved) {
      this._capabilityState ??= {};
      for (const mod of CAPABILITY_MODULES) {
        if (mod !== "installation") {
          this._capabilityState[mod] = createInvalidEnvelope(mod);
        }
      }
      this._updateCapabilityEnvelope(
        "installation",
        this._setupRequiredEnvelope()
      );
      return;
    }
    for (const mod of CAPABILITY_MODULES) {
      this._probing.add(mod);
    }
    // Older runtimes accept expected-version on the installation probe but
    // ignore it in probe all. Keep Python's versioned verdict authoritative.
    const minEngine = this._minEngineVersion();
    const engineOpt = minEngine ? { minEngineVersion: minEngine } : {};
    void Promise.all([
      client.probeAll({
        expectedVersion: this.plugin.manifest?.version,
        ...engineOpt,
      }),
      client
        .probe("installation", {
          expectedVersion: this.plugin.manifest?.version,
          ...engineOpt,
        })
        .catch(() => createInvalidEnvelope("installation")),
    ])
      .then(([data, installation]) => {
        this._probing.clear();
        const modules = {
          ...data.modules,
          installation: isValidEnvelope(installation, "installation")
            ? installation
            : createInvalidEnvelope("installation"),
        };
        for (const [mod, env] of Object.entries(modules)) {
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
        // State-machine driven orphan modal (统一出统一回): the maintenance
        // envelope carries the orphan state from the lineage probe.  NEW
        // orphans (none before, some now) pop the confirmation modal once;
        // persistent orphans just stay visible on the module card — never
        // re-pop on every 120s tick.
        const maint = (data.modules?.["maintenance"] ??
          null) as unknown as Record<string, unknown> | null;
        const orphanInfo = (maint?.orphan ?? {}) as {
          count?: number;
          orphans?: { key: string; title?: string }[];
        };
        const orphanCount = orphanInfo.count ?? 0;
        if (orphanCount > 0 && !this._lastOrphanCount) {
          this._openOrphanModal(orphanInfo.orphans ?? []);
        }
        this._lastOrphanCount = orphanCount;
      })
      .catch(() => {
        this._updateCapabilityEnvelope(
          "installation",
          createInvalidEnvelope("installation")
        );
        this._probing.clear();
        this.display();
      });
  }

  /** Open the orphan cleanup modal with the plugin-resolved python runtime
   * (never a hardcoded "python" — the real interpreter may be a venv). */
  private _openOrphanModal(orphans: { key: string; title?: string }[]): void {
    const vp = this._getVaultBasePath();
    if (!vp) return;
    const run = this._resolveRuntimeCommand();
    if (!run) {
      new Notice(t("next_action_runtime_unavailable"));
      return;
    }
    const py: PythonResult = {
      path: run.path,
      extraArgs: [...run.args],
      source: "auto-detected",
    };
    new PaperForgeOrphanModal(
      this.app,
      orphans as unknown as OrphanItem[],
      vp,
      py
    ).open();
  }

  /** #85: Build and copy privacy-safe Support Diagnostic (#257 extended). */
  _buildAndCopyDiagnostic(): void {
    const pluginVersion = this.plugin.manifest?.version ?? "unknown";
    const modules = collectDiagnosticModules(
      this._capabilityState ?? {},
      this._lastKnownState
    );
    const pointer = readRuntimePointer();
    // Allowlist projection: raw setup reason text and stage breadcrumbs stay
    // in memory only — the public report carries category + timestamp.
    const failure = this._lastSetupFailure;
    const diag: DiagnosticInput = {
      pluginVersion,
      modules,
      environment: {
        managedRuntime: this._diagnosticPath(pointer?.environmentRoot ?? null),
        runtimeVersion: pointer?.paperforgeVersion ?? null,
        pythonSetting: null,
      },
      lastSetupFailure: failure
        ? { category: failure.category, at: failure.at }
        : null,
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

  private _detectAndIsolateFolderCollision(vaultPath: string): void {
    if (!vaultPath || this._detectedFolderCollisionMsg !== null) return;
    const s = this.plugin.settings;
    // Skip if user already explicitly configured paths or vault already has paperforge.json
    if (
      s.literature_dir?.trim() ||
      fs.existsSync(path.join(vaultPath, "paperforge.json"))
    ) {
      this._detectedFolderCollisionMsg = "";
      return;
    }
    const collided: string[] = [];
    for (const folder of ["Literature", "Resources", "Bases"]) {
      const full = path.join(vaultPath, folder);
      try {
        if (fs.existsSync(full) && fs.statSync(full).isDirectory()) {
          const entries = fs.readdirSync(full);
          if (entries.length > 0) {
            collided.push(folder);
          }
        }
      } catch {
        // Ignore stat issues
      }
    }
    if (collided.length > 0) {
      s.system_dir = ".paperforge";
      s.literature_dir = "PaperForge/Literature";
      s.resources_dir = "PaperForge/Resources";
      s.base_dir = "PaperForge/Bases";
      this._detectedFolderCollisionMsg =
        t("nav_close") === "关闭"
          ? `检测到库内已存在原有 ${collided.join(" / ")} 文件夹：已自动为你改为存入 PaperForge/ 隔离目录，绝不会混入你的个人笔记。`
          : `Detected existing ${collided.join(" / ")} folder(s): isolated PaperForge notes inside PaperForge/ so your existing files stay untouched.`;
      void this.plugin.saveSettings();
    } else {
      this._detectedFolderCollisionMsg = "";
    }
  }

  _renderSetupJourney(containerEl: HTMLElement): void {
    if (this.plugin.settings._setup_journey_started !== true) {
      this.plugin.settings._setup_journey_started = true;
      this.plugin.saveSettings();
    }
    const vaultPath = this._getVaultBasePath();
    if (vaultPath) {
      this._detectAndIsolateFolderCollision(vaultPath);
    }

    const wrapper = containerEl.createDiv({ cls: "pf-setup-journey" });
    const isZh = t("nav_close") === "关闭";

    if (this._setupExpressMode && this._setupStage === 1) {
      this._renderExpressSetup(wrapper, isZh);
      return;
    }

    const topHead = wrapper.createDiv({ cls: "pf-express-header" });
    topHead.createEl("h2", { text: t("setup_welcome") });
    const backExpress = topHead.createEl("button", {
      cls: "pf-btn pf-btn-ghost",
      text: isZh ? "切回极简一屏配置" : "Back to Express setup",
      attr: { type: "button" },
    });
    backExpress.addEventListener("click", () => {
      this._setupExpressMode = true;
      this._setupStage = 1;
      this.display();
    });
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
      const pill = progress.createEl("button", {
        cls:
          "pf-setup-step" +
          (i + 1 === this._setupStage ? " pf-setup-step--active" : "") +
          (i + 1 < this._setupStage ? " pf-setup-step--done" : ""),
        text: String(i + 1) + ". " + label,
        attr: {
          type: "button",
          "aria-current": i + 1 === this._setupStage ? "step" : "false",
        },
      });
      pill.addEventListener("click", () => {
        this._setupStage = i + 1;
        this.display();
      });
    });

    const body = wrapper.createDiv({ cls: "pf-setup-body" });
    if (this._setupStage === 1) this._renderSetupStageFoundation(body);
    else if (this._setupStage === 2) this._renderSetupStageLibrary(body);
    else if (this._setupStage === 3) this._renderSetupStageOptionals(body);
    else this._renderSetupStageReview(body);
  }

  /** Express 1-page beginner flow: zero jargon, engine + Zotero + AI presets all cleanly accessible on 1 screen. */
  private _renderExpressSetup(wrapper: HTMLElement, isZh: boolean): void {
    this._refreshRuntimeStatus();
    this._maybeAutoDetectZotero();

    const settings = this.plugin.settings;
    const pointer = readRuntimePointer();
    const runtime = this._runtimeStatus;
    const rtReady = runtime?.runtime_ready === true;
    const action: RuntimeInstallerAction = !pointer
      ? "install"
      : runtime?.version_matches_expected === false
        ? "update"
        : "repair";

    const head = wrapper.createDiv({ cls: "pf-express-header" });
    const headCopy = head.createDiv();
    headCopy.createEl("h2", {
      text: isZh
        ? "欢迎使用 PaperForge · 一屏极速开启"
        : "PaperForge Quick Setup",
    });
    headCopy.createEl("p", {
      cls: "pf-setup-desc",
      text: isZh
        ? "全程图形界面操作，不改你的 Zotero 原库。确认 Zotero 位置后点最下方「保存并立即同步」即可。"
        : "Zero terminal or code needed, read-only on your Zotero database. Confirm Zotero below and click Save & Sync.",
    });
    const switchStep = head.createEl("button", {
      cls: "pf-btn pf-btn-ghost",
      text: isZh ? "分步详情模式" : "Step-by-step view",
      attr: { type: "button", "data-pf-testid": "express-to-step-btn" },
    });
    switchStep.addEventListener("click", () => {
      this._setupExpressMode = false;
      this.display();
    });

    // ── Block 1: Compute Engine (1 compact row, never locks Block 2/3) ──
    const c1 = wrapper.createDiv({ cls: "pf-express-card" });
    const c1Head = c1.createDiv({ cls: "pf-express-card-head" });
    c1Head.createEl("span", { cls: "pf-express-num", text: "1" });
    c1Head.createEl("strong", {
      text: isZh
        ? "自动计算引擎（OCR / Zotero / AI 组件）"
        : "Compute Engine (OCR / Sync / AI)",
    });
    const rtPill = c1Head.createEl("span", {
      cls: `pf-express-pill ${rtReady ? "is-ok" : "is-warn"}`,
      text: rtReady
        ? isZh
          ? "✓ 已就绪"
          : "✓ Ready"
        : this._runtimePollTimer
          ? isZh
            ? "正在后台安装…"
            : "Installing…"
          : isZh
            ? "待一键启用"
            : "One-click install",
    });
    void rtPill;
    if (!rtReady) {
      if (this._runtimePollTimer) {
        const prog = this._installerProgressLine();
        const pct = prog.includes("4/5")
          ? 80
          : prog.includes("3/5")
            ? 60
            : prog.includes("2/5")
              ? 40
              : prog.includes("1/5")
                ? 22
                : 15;
        const bar = c1.createDiv({ cls: "pf-runtime-stage-bar" });
        const fill = bar.createDiv({ cls: "pf-runtime-stage-fill" });
        fill.style.width = `${pct}%`;
        c1.createEl("p", {
          cls: "setting-item-description",
          text:
            prog ||
            (isZh
              ? "正在后台下载配置独立 Python 计算组件，同时你可以继续看第 2 步…"
              : "Provisioning engine in background — feel free to configure Zotero below right away…"),
        });
      } else {
        const c1Row = c1.createDiv({ cls: "pf-test-conn-row" });
        renderActionButton(c1Row, {
          label:
            action === "install"
              ? isZh
                ? "一键启用引擎（后台自动配置）"
                : "Enable Engine (Auto)"
              : isZh
                ? "更新 / 修复引擎"
                : "Update / Repair Engine",
          onClick: () => this._launchRuntimeInstaller(action),
        });
        c1Row.createEl("span", {
          cls: "setting-item-description",
          text: isZh
            ? "免手动装环境；点击即可，无需在此干等。"
            : "Runs automatically without leaving Obsidian.",
        });
      }
    }

    // ── Block 2: Zotero Auto-Locate + Anti-Collision + Live Domain Preview ──
    const c2 = wrapper.createDiv({ cls: "pf-express-card" });
    const c2Head = c2.createDiv({ cls: "pf-express-card-head" });
    c2Head.createEl("span", { cls: "pf-express-num", text: "2" });
    c2Head.createEl("strong", {
      text: isZh
        ? "连接 Zotero（自动扫描，无需装 Better BibTeX）"
        : "Connect Zotero (Zero plugins required)",
    });

    if (this._detectedFolderCollisionMsg) {
      c2.createEl("p", {
        cls: "pf-setup-ok pf-collision-guard-banner",
        text: "🛡 " + this._detectedFolderCollisionMsg,
      });
    }

    const zotRow = c2.createDiv({ cls: "pf-setup-path-row" });
    const zotInput = zotRow.createEl("input", {
      cls: "pf-setup-input",
      attr: {
        type: "text",
        placeholder: isZh
          ? "自动扫描 Zotero 数据目录…"
          : "Zotero data directory…",
        "data-pf-testid": "express-zotero-input",
      },
    }) as HTMLInputElement;
    zotInput.value = settings.zotero_data_dir || "";
    const applyZot = (dir: string) => {
      settings.zotero_data_dir = dir.trim();
      settings.zotero_source_mode = "sqlite";
      zotInput.value = settings.zotero_data_dir;
      void this.plugin.saveSettings();
      this._maybeAutoDetectZotero(true);
      this.display();
    };
    zotInput.addEventListener("change", () => applyZot(zotInput.value));
    const browseBtn = zotRow.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: t("setup_zotero_browse"),
      attr: { type: "button" },
    });
    browseBtn.addEventListener("click", () => {
      void this._pickFolderPath(c2).then((picked) => {
        if (picked) applyZot(picked);
      });
    });

    if (this._zoteroDetectData?.found) {
      c2.createEl("p", {
        cls: "pf-setup-ok",
        text: isZh
          ? `✓ 已检测到 ${this._zoteroDetectData.total_papers} 篇 Zotero 文献 · 默认直连同步`
          : `✓ Found ${this._zoteroDetectData.total_papers} papers in Zotero · ready for direct sync`,
      });
    }

    const previewHost = c2.createDiv();
    const allCols = this._zoteroDetectData?.collections ?? [];
    const topCols = allCols.filter((c) => c.top_level !== false);
    const curSel = new Set(
      Array.isArray(settings.zotero_selected_collections)
        ? settings.zotero_selected_collections
        : []
    );
    const curMode =
      settings.domain_mode === "unified" ? "unified" : "per_collection";
    const redrawPreview = () => {
      const pickedCols =
        curSel.size > 0
          ? (topCols.length > 0 ? topCols : allCols).filter((c) =>
              curSel.has(c.key)
            )
          : topCols.length > 0
            ? topCols
            : allCols;
      renderDomainModePreview(previewHost, {
        domainMode:
          settings.domain_mode === "unified" ? "unified" : "per_collection",
        collections: pickedCols,
        litDir: settings.literature_dir || "Literature",
        isZh,
      });
    };

    const modeGrid = c2.createDiv({ cls: "pf-mode-choice-grid" });
    const modeCardEls: HTMLButtonElement[] = [];
    for (const opt of [
      {
        id: "per_collection" as const,
        title: isZh
          ? "按 Zotero 顶级文件夹分专题（推荐）"
          : "Group by Zotero Folders (Recommended)",
        desc: isZh
          ? "文件夹整洁分类，同时所有文献仍在同一张 Base 总表。"
          : "Neat topic subfolders while keeping one master Base table.",
      },
      {
        id: "unified" as const,
        title: isZh
          ? "全部放一起，只靠总表筛选"
          : "Unified Folder + Base Filter Bar",
        desc: isZh
          ? "所有文献统一放进同一目录，在总表顶部随手筛选。"
          : "All papers in one folder, filtered via the sticky Base bar.",
      },
    ]) {
      const card = modeGrid.createEl("button", {
        cls: `pf-mode-choice-card${curMode === opt.id ? " is-selected" : ""}`,
        attr: { type: "button" },
      });
      modeCardEls.push(card);
      card.createEl("span", { cls: "pf-mode-choice-title", text: opt.title });
      card.createEl("span", { cls: "pf-mode-choice-desc", text: opt.desc });
      card.addEventListener("click", () => {
        settings.domain_mode = opt.id;
        settings.zotero_source_mode = "sqlite";
        for (const el of modeCardEls) el.classList.remove("is-selected");
        card.classList.add("is-selected");
        void this.plugin.saveSettings();
        redrawPreview();
      });
    }
    redrawPreview();

    if (allCols.length > 0) {
      const colDet = c2.createEl("details", { cls: "pf-adv-inline-details" });
      colDet.createEl("summary", {
        text: isZh
          ? `挑选只同步哪些 Zotero 文件夹（当前：${curSel.size > 0 ? `已选 ${curSel.size} 个` : "全部文库"}）`
          : `Filter specific Zotero folders (${curSel.size > 0 ? `${curSel.size} selected` : "All papers"})`,
      });
      const colGrid = colDet.createDiv({ cls: "pf-zotero-col-grid" });
      for (const col of topCols.length > 0 ? topCols : allCols) {
        const label = colGrid.createEl("label", { cls: "pf-zotero-col-item" });
        const cb = label.createEl("input", {
          attr: { type: "checkbox" },
        }) as HTMLInputElement;
        cb.checked = curSel.has(col.key);
        cb.addEventListener("change", () => {
          if (cb.checked) curSel.add(col.key);
          else curSel.delete(col.key);
          settings.zotero_selected_collections = Array.from(curSel);
          void this.plugin.saveSettings();
          redrawPreview();
        });
        label.createSpan({ text: col.name });
        label.createEl("span", {
          cls: "pf-zotero-col-cnt",
          text: `${col.item_count}`,
        });
      }
    }

    // ── Block 3: Optional AI Keys (collapsed neatly so beginners never feel pressured) ──
    const c3 = wrapper.createDiv({ cls: "pf-express-card" });
    const c3Head = c3.createDiv({ cls: "pf-express-card-head" });
    c3Head.createEl("span", { cls: "pf-express-num", text: "3" });
    c3Head.createEl("strong", {
      text: isZh
        ? "AI 与期刊分区增强（全部可选，可稍后在设置补充）"
        : "Optional AI & Journal Metrics (Configure later anytime)",
    });

    const aiDetails = c3.createEl("details", { cls: "pf-adv-inline-details" });
    aiDetails.createEl("summary", {
      text: isZh
        ? "展开填写 PDF 解析（OCR）、AI 语义检索（含硅基流动预设）或 EasyScholar 密钥"
        : "Expand to add PaddleOCR, Embedding (with presets), or EasyScholar API keys",
    });

    // OCR quick row
    const ocrBox = aiDetails.createDiv({ cls: "pf-express-subrow" });
    ocrBox.createEl("label", { text: "PaddleOCR API Key" });
    const ocrKeyIn = ocrBox.createEl("input", {
      cls: "pf-setup-input",
      attr: {
        type: "password",
        placeholder: settings._paddleocr_configured
          ? "•••• (已保存)"
          : "粘贴百度 AI Studio OCR 密钥（可选）",
      },
    }) as HTMLInputElement;
    const ocrTestBtn = ocrBox.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: "保存并测通",
      attr: { type: "button" },
    });
    const ocrMsg = ocrBox.createEl("span", { cls: "pf-test-conn-status" });
    ocrTestBtn.addEventListener("click", () => {
      const val = ocrKeyIn.value.trim();
      ocrTestBtn.disabled = true;
      ocrMsg.textContent = "测试中…";
      void (
        val
          ? this._storeSetupSecret("paddleocr-api-key", val)
          : Promise.resolve(true)
      )
        .then(() => this.getClient().ocrTestConnection())
        .then((res) => {
          if (val) ocrKeyIn.value = "";
          ocrMsg.className = `pf-test-conn-status ${res?.passed ? "is-ok" : "is-err"}`;
          ocrMsg.textContent = res?.passed
            ? "✓ 已连通"
            : `✗ ${res?.error || "校验失败"}`;
        })
        .catch((err) => {
          ocrMsg.className = "pf-test-conn-status is-err";
          ocrMsg.textContent = `✗ ${String(err?.message || err).slice(0, 60)}`;
        })
        .finally(() => {
          ocrTestBtn.disabled = false;
        });
    });

    // Embedding quick row with Preset dropdown
    const memBox = aiDetails.createDiv({ cls: "pf-express-subrow" });
    memBox.createEl("label", { text: "AI 语义检索预设" });
    const pSel = memBox.createEl("select", {
      cls: "pf-setup-select",
    }) as HTMLSelectElement;
    const curP = matchEmbeddingPresetId(
      settings.vector_db_api_base || "",
      settings.vector_db_api_model || ""
    );
    for (const p of EMBEDDING_PRESETS) {
      const opt = pSel.createEl("option", {
        text: isZh ? p.labelZh : p.labelEn,
        attr: { value: p.id },
      }) as HTMLOptionElement;
      opt.selected = p.id === curP;
    }
    pSel.addEventListener("change", () => {
      const picked = EMBEDDING_PRESETS.find((x) => x.id === pSel.value);
      if (!picked || picked.id === "custom") return;
      void this.getClient()
        .configSet("vector_db_api_base", picked.baseUrl)
        .catch(() => undefined);
      void this.getClient()
        .configSet("vector_db_api_model", picked.model)
        .catch(() => undefined);
      settings.vector_db_api_base = picked.baseUrl;
      settings.vector_db_api_model = picked.model;
      void this.plugin.saveSettings();
    });
    const memKeyIn = memBox.createEl("input", {
      cls: "pf-setup-input",
      attr: {
        type: "password",
        placeholder: settings._vector_db_configured
          ? "•••• (已保存)"
          : "粘贴 AI 检索 API Key（可选）",
      },
    }) as HTMLInputElement;
    const memTestBtn = memBox.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: "保存并测维度",
      attr: { type: "button" },
    });
    const memMsg = memBox.createEl("span", { cls: "pf-test-conn-status" });
    memTestBtn.addEventListener("click", () => {
      const val = memKeyIn.value.trim();
      memTestBtn.disabled = true;
      memMsg.textContent = "探测中…";
      void (
        val
          ? this._storeSetupSecret("vector-db-api-key", val)
          : Promise.resolve(true)
      )
        .then(() => this.getClient().embedTestConnection())
        .then((res) => {
          if (val) memKeyIn.value = "";
          memMsg.className = "pf-test-conn-status is-ok";
          memMsg.textContent = `✓ ${res.model} (${res.dimension}维)`;
        })
        .catch((err) => {
          memMsg.className = "pf-test-conn-status is-err";
          memMsg.textContent = `✗ ${String(err?.message || err).slice(0, 60)}`;
        })
        .finally(() => {
          memTestBtn.disabled = false;
        });
    });

    if (this._setupFeedback) {
      wrapper.createEl("p", {
        cls:
          this._setupOperation === "failed" ? "pf-setup-warn" : "pf-setup-ok",
        text: this._setupFeedback,
      });
    }
    if (this._setupFailureDetail && this._setupOperation === "failed") {
      wrapper.createEl("p", {
        cls: "pf-setup-failure-detail",
        text: this._setupFailureDetail,
      });
    }

    // ── Single Big Footer CTA ──
    const footer = wrapper.createDiv({ cls: "pf-setup-nav" });
    renderActionButton(footer, {
      label: isZh ? "稍后配置，先逛逛" : t("setup_nav_later"),
      variant: "ghost",
      disabled: this._setupOperation === "running",
      onClick: () => this._goHome(),
    });
    renderActionButton(footer, {
      label:
        this._setupOperation === "running"
          ? isZh
            ? "正在同步文献库…"
            : "Syncing…"
          : isZh
            ? "保存配置并立即同步文献库"
            : "Save & Sync Library Now",
      disabled: this._setupOperation === "running",
      onClick: () =>
        this._applyLibraryConfiguration({ autoCompleteOnSuccess: true }),
    });
  }

  _renderSetupStageFoundation(containerEl: HTMLElement): void {
    this._refreshRuntimeStatus();
    const pointer = readRuntimePointer();
    const runtime = this._runtimeStatus;
    const ready = runtime?.runtime_ready === true;
    const action: RuntimeInstallerAction = this._setupReinstallRequested
      ? "repair"
      : !pointer
        ? "install"
        : runtime?.version_matches_expected === false
          ? "update"
          : "repair";

    containerEl.createEl("h3", { text: t("setup_foundation_title") });
    containerEl.createEl("p", { text: t("setup_foundation_desc") });
    // A published pointer with no status yet is still "checking": never offer
    // repair/install before the status is known.
    // A status we could not obtain is not "ready": treat an error as an
    // actionable not-ready state instead of leaving the panel without a button.
    const statusUnknown =
      !ready &&
      !this._runtimeStatusError &&
      (this._runtimeStatusLoading ||
        (!!pointer && this._runtimeStatus === null));
    containerEl.createEl("p", {
      text: statusUnknown
        ? t("setup_runtime_checking")
        : ready
          ? t("setup_runtime_ready")
          : (this._runtimeStatusError ??
            (pointer
              ? t("setup_runtime_attention")
              : t("setup_runtime_missing"))),
      cls: ready ? "pf-setup-ok" : "pf-setup-status",
    });
    // A requested reinstall is an explicit action even when the runtime is
    // healthy: the user asked to rebuild it, so the button must be there.
    if (this._setupReinstallRequested || (!ready && !statusUnknown)) {
      containerEl.createEl("p", {
        text: t("runtime_installer_hint"),
        cls: "setting-item-description",
      });
      if (this._runtimePollTimer) {
        containerEl.createEl("p", {
          cls: "pf-setup-status",
          text: t("runtime_installing"),
        });
        const progress = this._installerProgressLine();
        const pct = progress.includes("4/5")
          ? 80
          : progress.includes("3/5")
            ? 60
            : progress.includes("2/5")
              ? 40
              : progress.includes("1/5")
                ? 22
                : 15;
        const bar = containerEl.createDiv({ cls: "pf-runtime-stage-bar" });
        const fill = bar.createDiv({ cls: "pf-runtime-stage-fill" });
        fill.style.width = `${pct}%`;
        if (progress) {
          containerEl.createEl("p", {
            cls: "setting-item-description",
            text: progress,
          });
        }
        containerEl.createEl("p", {
          cls: "setting-item-description",
          text:
            t("nav_close") === "关闭"
              ? "提示：无需等待进度条结束，可直接点击下方按钮先配置 Zotero。"
              : "Tip: you can click Next below to configure Zotero while setup finishes in the background.",
        });
        renderActionButton(containerEl, {
          label: t("runtime_cancel_btn"),
          variant: "secondary",
          onClick: () => this._cancelRuntimePoll(),
        });
      } else {
        renderActionButton(containerEl, {
          label: this._setupReinstallRequested
            ? t("runtime_reinstall_btn")
            : action === "install"
              ? t("runtime_install_btn")
              : action === "update"
                ? t("runtime_update_btn")
                : t("runtime_repair_btn"),
          onClick: () => this._launchRuntimeInstaller(action),
        });
      }
    }
    // Manual commands and re-check stay available even while the status is
    // unknown: a stuck check must never leave the panel without an action.
    const manual = containerEl.createEl("details", {
      cls: "pf-runtime-manual",
    });
    manual.createEl("summary", { text: t("runtime_manual_summary") });
    manual.createEl("pre").createEl("code", {
      text: this._runtimeInstallerCommand(action),
    });
    renderActionButton(containerEl, {
      label: t("setup_runtime_refresh"),
      variant: "secondary",
      onClick: () => {
        this._refreshRuntimeStatus(true);
        this.display();
      },
    });

    const nav = containerEl.createDiv({ cls: "pf-setup-nav" });
    renderActionButton(nav, {
      label: t("setup_nav_later"),
      variant: "ghost",
      onClick: () => {
        this._setupStage = 1;
        this.activeTab = "overview";
        this._setupJourneyDismissedForSession = true;
        this.display();
      },
    });
    renderActionButton(nav, {
      label:
        ready || !this._runtimePollTimer
          ? t("setup_nav_continue")
          : t("nav_close") === "关闭"
            ? "边装边配置下一步 →"
            : "Continue while installing →",
      disabled: !ready && !this._runtimePollTimer,
      onClick: () => {
        this._setupStage = 2;
        this.display();
      },
    });
  }

  /** Names of BBT JSON exports already present in the canonical folder. */
  private _listBbtExports(exportsDir: string): string[] {
    try {
      if (!fs.existsSync(exportsDir))
        fs.mkdirSync(exportsDir, { recursive: true });
      return fs
        .readdirSync(exportsDir)
        .filter((f: string) => f.toLowerCase().endsWith(".json"))
        .sort();
    } catch {
      return [];
    }
  }

  private _maybeAutoDetectZotero(force = false): void {
    const client = this.getClient?.();
    if (!client || typeof client.zoteroDetect !== "function") return;
    if (this._zoteroDetectBusy) return;
    if (this._zoteroDetectRan && !force) return;
    this._zoteroDetectRan = true;
    this._zoteroDetectBusy = true;
    const hint = (this.plugin.settings.zotero_data_dir || "").trim();
    void client
      .zoteroDetect(hint || undefined)
      .then((res) => {
        this._zoteroDetectData = res;
        if (
          res.found &&
          res.zotero_dir &&
          !this.plugin.settings.zotero_data_dir?.trim()
        ) {
          this.plugin.settings.zotero_data_dir = res.zotero_dir;
          void this.plugin.saveSettings();
        }
      })
      .catch(() => undefined)
      .finally(() => {
        this._zoteroDetectBusy = false;
        this.display();
      });
  }

  /**
   * Stage 2 is a beginner-friendly 3-step flow powered by direct zotero.sqlite reading:
   *   1 Locate Zotero data folder (auto-detected) -> 2 Pick collections & topic layout
   *   with live interactive preview -> 3 One-click Save & Sync (hidden default dirs).
   */
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

    const settings = this.plugin.settings;
    this._maybeAutoDetectZotero();

    const vaultPath = (this.app.vault.adapter as any).basePath as string;
    const sysDir = settings.system_dir?.trim() || "System";
    const sysLeaf = sysDir
      .replace(/[\\/]+$/, "")
      .split(/[\\/]/)
      .pop();
    const exportsDir =
      sysLeaf === ".paperforge"
        ? path.join(vaultPath, sysDir, "exports")
        : path.join(vaultPath, sysDir, "PaperForge", "exports");
    const zotero = (settings.zotero_data_dir || "").trim();
    const zoteroOk =
      Boolean(this._zoteroDetectData?.found) ||
      (!!zotero && fs.existsSync(zotero));
    const bbtFiles = this._listBbtExports(exportsDir);
    const useLegacyBbt = settings.zotero_source_mode === "bbt";
    const scopeOk = useLegacyBbt ? bbtFiles.length > 0 : zoteroOk;
    const libReady = env.user_state === "ready";
    const running = this._setupOperation === "running";
    const isZh = t("nav_close") === "关闭";

    containerEl.createEl("h3", { text: t("setup_library_title") });
    containerEl.createEl("p", {
      text: isZh
        ? "无需安装任何 Zotero 导出插件，直接自动读取你的 Zotero 文库目录与课题分组。"
        : t("setup_library_desc"),
    });
    if (libReady) {
      containerEl.createEl("p", {
        cls: "pf-setup-ok",
        text: t("setup_library_ready"),
      });
    } else if (env.reason?.code !== "library.config_missing") {
      containerEl.createEl("p", {
        cls: "pf-setup-status",
        text: this._getModuleConsequence("library", env),
      });
    }
    if (this._setupOperation === "running") {
      containerEl.createEl("p", {
        cls: "pf-setup-status",
        text: this._setupFeedback || t("setup_library_configuring"),
      });
    } else if (this._setupFeedback) {
      containerEl.createEl("p", {
        cls:
          this._setupOperation === "failed" ? "pf-setup-warn" : "pf-setup-ok",
        text: this._setupFeedback,
      });
    }

    if (this._setupOperation === "failed" && this._setupFailureDetail) {
      containerEl.createEl("p", {
        cls: "pf-setup-failure-detail",
        text: this._setupFailureDetail,
      });
    }

    const steps = [
      {
        id: "zotero",
        title: t("setup_step_zotero"),
        done: zoteroOk || libReady,
      },
      {
        id: "scope",
        title: isZh ? "选择同步课题与目录组织方式" : "Topics & Folder Layout",
        done: scopeOk || libReady,
      },
      { id: "verify", title: t("setup_step_verify_title"), done: libReady },
    ];
    const currentId = steps.find((step) => !step.done)?.id ?? null;
    const openId = this._setupOpenStep ?? currentId;

    const flow = containerEl.createDiv({ cls: "pf-setup-flow" });
    for (const [index, step] of steps.entries()) {
      const row = flow.createDiv({ cls: "pf-setup-flow-step" });
      row.dataset.state = step.done
        ? "done"
        : step.id === currentId
          ? "current"
          : "pending";
      const head = row.createDiv({ cls: "pf-setup-flow-head" });
      head.createEl("span", { cls: "pf-step-num", text: String(index + 1) });
      head.createEl("span", { cls: "pf-step-title", text: step.title });
      head.createEl("span", {
        cls: "pf-step-state",
        text: step.done
          ? "\u2713 " + t("setup_step_done")
          : step.id === currentId
            ? t("setup_step_todo")
            : "",
      });
      if (!step.done && step.id !== currentId && step.id !== "scope") {
        row.createEl("p", {
          cls: "caption pf-step-hint",
          text: t("setup_step_" + step.id + "_desc"),
        });
      }

      if (step.done && openId !== step.id) {
        const summary = row.createDiv({ cls: "pf-setup-flow-summary" });
        summary.createEl("span", {
          text:
            step.id === "zotero"
              ? zotero +
                (this._zoteroDetectData?.found
                  ? ` (${this._zoteroDetectData.total_papers} 篇)`
                  : "")
              : step.id === "scope"
                ? useLegacyBbt
                  ? bbtFiles.join(", ")
                  : (settings.domain_mode === "unified"
                      ? "全部文献统一汇总"
                      : "按 Zotero 顶级文件夹分专题") +
                    (Array.isArray(settings.zotero_selected_collections) &&
                    settings.zotero_selected_collections.length > 0
                      ? ` · 已选 ${settings.zotero_selected_collections.length} 个文件夹`
                      : " · 同步全库")
                : [
                    settings.literature_dir || "Literature",
                    settings.resources_dir || "Resources",
                    settings.base_dir || "Bases",
                  ].join(" · "),
        });
        summary
          .createEl("button", {
            cls: "pf-setup-flow-edit",
            text: t("setup_step_edit"),
            attr: { type: "button" },
          })
          .addEventListener("click", () => {
            this._setupOpenStep = step.id;
            this.display();
          });
        continue;
      }
      if (step.id !== currentId && !step.done && openId !== step.id) continue;

      const body = row.createDiv({ cls: "pf-setup-flow-body" });
      if (step.id === "zotero") {
        if (this._zoteroDetectData?.found) {
          body.createEl("p", {
            cls: "pf-setup-ok",
            text: isZh
              ? `✓ 已自动定位 Zotero 数据目录（共检测到 ${this._zoteroDetectData.total_papers} 篇文献）`
              : `✓ Auto-detected Zotero library (${this._zoteroDetectData.total_papers} papers)`,
          });
        } else {
          body.createEl("p", {
            cls: "caption",
            text: t("setup_library_zotero_hint"),
          });
        }
        const inputRow = body.createDiv({ cls: "pf-setup-path-row" });
        const input = inputRow.createEl("input", {
          cls: "pf-setup-input",
          attr: {
            type: "text",
            placeholder: t("setup_step_zotero_placeholder"),
          },
        }) as HTMLInputElement;
        input.value = settings.zotero_data_dir || "";
        const applyZoteroDir = (dir: string) => {
          settings.zotero_data_dir = dir.trim();
          input.value = settings.zotero_data_dir;
          this._setupOpenStep = null;
          void this.plugin.saveSettings();
          this._maybeAutoDetectZotero(true);
          this.display();
        };
        input.addEventListener("change", () => applyZoteroDir(input.value));
        inputRow
          .createEl("button", {
            cls: "pf-btn pf-btn-secondary",
            text: t("setup_zotero_browse"),
            attr: { type: "button" },
          })
          .addEventListener("click", () => {
            void this._pickFolderPath(body).then((picked) => {
              if (picked) applyZoteroDir(picked);
            });
          });
        inputRow
          .createEl("button", {
            cls: "pf-btn pf-btn-secondary",
            text: t("setup_zotero_use_default"),
            attr: { type: "button" },
          })
          .addEventListener("click", () => {
            const home = os.homedir();
            const candidates = [
              path.join(home, "Zotero"),
              path.join(home, ".var", "app", "org.zotero.Zotero", "Zotero"),
              path.join(home, "snap", "zotero-snap", "common", "Zotero"),
            ];
            const found =
              candidates.find((cand) => {
                try {
                  return fs.existsSync(cand);
                } catch {
                  return false;
                }
              }) ?? candidates[0];
            applyZoteroDir(found);
          });
        if (
          zotero &&
          (/[/\\]program files(?:\s*\(x86\))?[/\\]/i.test(zotero) ||
            /[/\\]applications[/\\]zotero\.app(?:[/\\]|$)/i.test(zotero) ||
            /zotero\.(?:exe|app)$/i.test(zotero))
        ) {
          body.createEl("p", {
            cls: "pf-setup-warn",
            text: t("setup_zotero_progfiles_warn"),
          });
        }
      } else if (step.id === "scope") {
        const previewHost = body.createDiv();
        const allCols = this._zoteroDetectData?.collections ?? [];
        const topCols = allCols.filter((c) => c.top_level !== false);
        const curSel = new Set(
          Array.isArray(settings.zotero_selected_collections)
            ? settings.zotero_selected_collections
            : []
        );
        const curMode =
          settings.domain_mode === "unified" ? "unified" : "per_collection";

        const redrawPreview = () => {
          const pickedCols =
            curSel.size > 0
              ? (topCols.length > 0 ? topCols : allCols).filter((c) =>
                  curSel.has(c.key)
                )
              : topCols.length > 0
                ? topCols
                : allCols;
          renderDomainModePreview(previewHost, {
            domainMode:
              settings.domain_mode === "unified" ? "unified" : "per_collection",
            collections: pickedCols,
            litDir: settings.literature_dir || "Literature",
            isZh,
          });
        };

        if (!useLegacyBbt) {
          body.createEl("p", {
            cls: "caption",
            text: isZh
              ? "1) 选择需要同步到 Obsidian 的 Zotero 文件夹（不勾选则默认同步整个 Zotero 文库）："
              : "1) Check Zotero collections to sync (leave unchecked to sync your entire Zotero library):",
          });
          if (allCols.length > 0) {
            const colGrid = body.createDiv({ cls: "pf-zotero-col-grid" });
            const listToShow = topCols.length > 0 ? topCols : allCols;
            for (const col of listToShow) {
              const label = colGrid.createEl("label", {
                cls: "pf-zotero-col-item",
              });
              const cb = label.createEl("input", {
                attr: { type: "checkbox" },
              }) as HTMLInputElement;
              cb.checked = curSel.has(col.key);
              cb.addEventListener("change", () => {
                if (cb.checked) curSel.add(col.key);
                else curSel.delete(col.key);
                settings.zotero_selected_collections = Array.from(curSel);
                void this.plugin.saveSettings();
                redrawPreview();
              });
              label.createSpan({ text: col.name });
              label.createEl("span", {
                cls: "pf-zotero-col-cnt",
                text: `${col.item_count}`,
              });
            }
          } else {
            body.createEl("p", {
              cls: "setting-item-description",
              text: this._zoteroDetectBusy
                ? "正在扫描 Zotero 分类…"
                : "将同步你的 Zotero 全部文献（稍后可随时勾选特定分类）。",
            });
          }

          body.createEl("p", {
            cls: "caption",
            text: isZh
              ? "2) 选择同步后 Obsidian 内的组织方式（下方实时预览生效效果）："
              : "2) Choose how folders are organized (live preview updates below):",
          });
          const modeGrid = body.createDiv({ cls: "pf-mode-choice-grid" });
          const modeOptions: Array<{
            id: "per_collection" | "unified";
            title: string;
            desc: string;
          }> = [
            {
              id: "per_collection",
              title: isZh
                ? "按课题文件夹自动分组（推荐）"
                : "Group by Zotero top folders (Recommended)",
              desc: isZh
                ? "每个顶级 Zotero 文件夹对应一个专题分区，同时仍汇总在一张 Base 总表。"
                : "Each top collection maps cleanly to a topic zone inside one master Base.",
            },
            {
              id: "unified",
              title: isZh
                ? "全部放一起，只靠总表筛选"
                : "Single unified folder, filter inside Base",
              desc: isZh
                ? "不拆分子文件夹，所有文献放进同一目录，在总表顶部直接用多维筛选查看。"
                : "Put all papers together and slice purely via the sticky Base filter bar.",
            },
          ];
          const cardEls: HTMLButtonElement[] = [];
          for (const opt of modeOptions) {
            const card = modeGrid.createEl("button", {
              cls: `pf-mode-choice-card${curMode === opt.id ? " is-selected" : ""}`,
              attr: { type: "button" },
            });
            cardEls.push(card);
            card.createEl("span", {
              cls: "pf-mode-choice-title",
              text: opt.title,
            });
            card.createEl("span", {
              cls: "pf-mode-choice-desc",
              text: opt.desc,
            });
            card.addEventListener("click", () => {
              settings.domain_mode = opt.id;
              settings.zotero_source_mode = "sqlite";
              for (const el of cardEls) el.classList.remove("is-selected");
              card.classList.add("is-selected");
              void this.plugin.saveSettings();
              redrawPreview();
            });
          }
          redrawPreview();

          const ifDetails = body.createEl("details", {
            cls: "pf-adv-inline-details",
          });
          ifDetails.createEl("summary", {
            text: isZh
              ? "进阶可选：配置 EasyScholar 密钥获取精确 JCR IF 与中科院分区（不填默认使用开源学术指标 ≈）"
              : "Optional: EasyScholar key for exact JCR IF & CAS partitions",
          });
          const esRow = ifDetails.createDiv({ cls: "pf-test-conn-row" });
          const esKey = esRow.createEl("input", {
            cls: "pf-setup-input",
            attr: {
              type: "password",
              placeholder: settings._easyscholar_configured
                ? "•••• (已保存)"
                : "EasyScholar SecretKey（可选）",
            },
          }) as HTMLInputElement;
          const esBtn = esRow.createEl("button", {
            cls: "pf-btn pf-btn-secondary",
            text: t("config_save"),
            attr: { type: "button" },
          });
          const esMsg = esRow.createEl("span", { cls: "pf-test-conn-status" });
          esBtn.addEventListener("click", () => {
            const v = esKey.value.trim();
            if (!v) return;
            void this.getClient()
              .authSetSecret("easyscholar", v)
              .then(() => {
                settings._easyscholar_configured = true;
                settings.journal_metrics_mode = "auto";
                esKey.value = "";
                esMsg.className = "pf-test-conn-status is-ok";
                esMsg.textContent = "✓ 已保存";
                void this.plugin.saveSettings();
              })
              .catch(() => {
                esMsg.className = "pf-test-conn-status is-err";
                esMsg.textContent = "保存失败";
              });
          });
        }

        const legacyDetails = body.createEl("details", {
          cls: "pf-adv-inline-details",
        });
        legacyDetails.createEl("summary", {
          text: isZh
            ? "兼容选项：切换旧版 Better BibTeX 手工导出 JSON 模式"
            : "Legacy mode: Better BibTeX JSON exports",
        });
        const modeSwitch = legacyDetails.createEl("button", {
          cls: "pf-btn pf-btn-secondary",
          text: useLegacyBbt
            ? "切换回 zotero.sqlite 免插件直连（推荐）"
            : "切换为旧版 BBT JSON 模式",
          attr: { type: "button" },
        });
        modeSwitch.addEventListener("click", () => {
          settings.zotero_source_mode = useLegacyBbt ? "sqlite" : "bbt";
          void this.plugin.saveSettings();
          this.display();
        });
        if (useLegacyBbt) {
          const targetRow = legacyDetails.createDiv({
            cls: "pf-setup-path-row",
          });
          targetRow.createEl("code", {
            cls: "pf-setup-path-value",
            text: exportsDir,
          });
          targetRow
            .createEl("button", {
              cls: "pf-btn pf-btn-secondary",
              text: t("setup_bbt_open_folder"),
              attr: { type: "button" },
            })
            .addEventListener("click", () => {
              try {
                const { shell } = require("electron") as {
                  shell: { openPath: (p: string) => Promise<string> };
                };
                fs.mkdirSync(exportsDir, { recursive: true });
                void shell.openPath(exportsDir);
              } catch {
                new Notice(exportsDir);
              }
            });
        }
      } else {
        body.createEl("p", {
          cls: "caption",
          text: isZh
            ? "一切已按最佳实践预置完成，点击下方按钮立即同步你的 Zotero 文献库。"
            : "Everything is ready with recommended defaults. Click below to save and sync your library.",
        });
        const customFoldersDetails = body.createEl("details", {
          cls: "pf-adv-inline-details",
        });
        customFoldersDetails.createEl("summary", {
          text: isZh
            ? "高级：自定义 Vault 文件夹名称（推荐保持默认）"
            : "Advanced: customize folder names in vault",
        });
        const folders = customFoldersDetails.createDiv({
          cls: "pf-setup-folder-grid",
        });
        const hydratedLib =
          Boolean(this._getVaultBasePath()) &&
          !resolveVaultPaths(this._getVaultBasePath())?.configWarning;
        const defaultSysDirHint = hydratedLib ? "System" : ".paperforge";
        const folders_: Array<
          [
            keyof typeof settings &
              ("system_dir" | "resources_dir" | "literature_dir" | "base_dir"),
            string,
            string,
            string,
          ]
        > = [
          ["system_dir", "dir_system", defaultSysDirHint, "folder_help_system"],
          [
            "resources_dir",
            "dir_resources",
            "Resources",
            "folder_help_resources",
          ],
          ["literature_dir", "dir_notes", "Literature", "folder_help_notes"],
          ["base_dir", "dir_base", "Bases", "folder_help_base"],
        ];
        for (const [key, labelKey, fallback, helpKey] of folders_) {
          const field = folders.createDiv({ cls: "pf-setup-field" });
          field.createEl("label", { text: t(labelKey) });
          const input = field.createEl("input", {
            cls: "pf-setup-input",
            attr: { type: "text", placeholder: fallback },
          }) as HTMLInputElement;
          input.value = settings[key] || "";
          field.createEl("span", { cls: "caption", text: t(helpKey) });
          input.addEventListener("input", () => {
            settings[key] = input.value.trim();
            this._debouncedSave();
          });
        }

        const verify = body.createEl("button", {
          cls: "pf-setup-verify",
          text: t("setup_library_save_sync"),
          attr: { type: "button" },
        }) as HTMLButtonElement;
        verify.disabled = running;
        verify.addEventListener("click", () =>
          this._applyLibraryConfiguration()
        );
      }
    }

    if (!libReady) {
      containerEl.createEl("p", {
        cls: "caption pf-setup-continue-hint",
        text: t("setup_library_continue_hint"),
      });
    }
    const nav = containerEl.createDiv({ cls: "pf-setup-nav" });
    renderActionButton(nav, {
      label: t("setup_nav_exit"),
      variant: "ghost",
      disabled: this._setupOperation === "running",
      onClick: () => this._goHome(),
    });
    renderActionButton(nav, {
      label: t("setup_nav_back"),
      variant: "secondary",
      disabled: this._setupOperation === "running",
      onClick: () => {
        this._setupFeedback = null;
        this._setupOpenStep = null;
        this._setupStage = 1;
        this.display();
      },
    });
    renderActionButton(nav, {
      label: t("setup_nav_continue"),
      disabled: !libReady || running,
      onClick: () => {
        this._setupFeedback = null;
        this._setupOpenStep = null;
        this._setupStage = 3;
        this.display();
      },
    });
  }

  /** #173 corrective: explicit, user-mediated SecretStorage → keyring
   *  migration.  Reads each known legacy id once, stores via `auth set
   *  --stdin`, verifies, then clears the old value. */
  private async _migrateLegacyCredentials(
    btn: HTMLButtonElement
  ): Promise<void> {
    // Host responsibility: where the legacy SecretStorage value lives and
    // how to clear it.  Backend responsibility: the credential write goes
    // through the shared client — `{replace: false}` so a stale host copy
    // can never overwrite a live keyring value.
    const client = this.getClient();
    const deps = {
      writeCredential: (kind: "ocr" | "embedding", value: string) =>
        client.authSetSecret(kind, value, { replace: false }),
    };
    btn.disabled = true;
    const results: string[] = [];
    try {
      await this._collectLegacyMigrations(deps, results);
    } finally {
      // The button must always recover — even if the migration workflow
      // itself throws unexpectedly.
      btn.disabled = false;
    }
    if (results.length === 0) {
      new Notice(t("migrate_none_found"));
    } else {
      results.forEach((line) => new Notice(line, 6000));
    }
    this._refreshVectorDbCredentialStatus();
    this._refreshAllReadModels();
  }

  private async _collectLegacyMigrations(
    deps: {
      writeCredential: (
        kind: "ocr" | "embedding",
        value: string
      ) => Promise<boolean>;
    },
    results: string[]
  ): Promise<void> {
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
  }

  private _refreshVectorDbCredentialStatus(): void {
    // #173/C1: presence comes from the credential authority (`auth status`),
    // never from SecretStorage or settings flags.
    const vp = this._getVaultBasePath();
    if (!vp) return;
    void this.getClient()
      .credentialAvailable("embedding")
      .then((available) => {
        if (available === this.plugin.settings._vector_db_configured) return;
        this.plugin.settings._vector_db_configured = available;
        void this.plugin.saveSettings();
      })
      .catch(() => undefined);
  }
  private _setVectorDbConfig(
    key:
      | "vector_db_api_base"
      | "vector_db_api_model"
      | "vector_db_provider_type"
      | "paddleocr_job_url"
      | "paddleocr_model",
    input: HTMLInputElement | HTMLSelectElement
  ): void {
    let value = input.value.trim();
    if (key === "vector_db_api_base" && value) {
      value = value.replace(/\/+$/, "").replace(/\/embeddings$/i, "");
      input.value = value;
    }
    const previous = String((this.plugin.settings as any)[key] ?? "");
    void this.getClient()
      .configSet(key, value)
      .then(async () => {
        (this.plugin.settings as any)[key] = value;
        await this.plugin.saveSettings();
        this._refreshVectorDbCredentialStatus();
      })
      .catch((error) => {
        input.value = previous;
        new Notice(`PaperForge: config set ${key} failed: ${String(error)}`);
      });
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
    // The API Key row reads the backend probe (env.details), so a saved key
    // must re-probe or the panel keeps showing "Missing" until restart.
    this._refreshAllReadModels();
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
    if (!value) return Promise.resolve(false);
    // #173/C1: the secret travels only via the child stdin — the client
    // passes it through ExecuteOptions.stdin; never argv, env, files, or
    // settings. The transport owns the sanitized env.
    return this.getClient()
      .authSetSecret(kind, value)
      .then(() => true)
      .catch(() => false);
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
    const pendingSecretSaves: Array<() => Promise<unknown>> = [];
    for (const opt of optionals) {
      const row = containerEl.createDiv({ cls: "pf-setup-optional" });
      const head = row.createDiv({ cls: "pf-setup-optional-head" });
      const copy = head.createDiv({ cls: "pf-setup-optional-copy" });
      copy.createEl("label", {
        attr: { for: "pf-setup-opt-" + opt.id },
        text: opt.label,
        cls: "pf-setup-optional-label",
      });
      copy.createEl("div", {
        text: opt.desc,
        cls: "pf-setup-optional-desc",
      });
      const checkbox = head.createEl("input", {
        cls: "pf-switch",
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
      // The chip states what the user must do next, not just "configured":
      // a green "not configured" reads as done and is why people skip it.
      const needsSecret = opt.id === "ocr" || opt.id === "memory";
      const status = copy.createEl("span", {
        cls:
          "pf-setup-optional-state " +
          (needsSecret && !configured
            ? "pf-setup-optional-state--warn"
            : "pf-setup-optional-state--ok"),
        text:
          opt.id === "agent"
            ? t("setup_optional_platform").replace(
                "{platform}",
                AGENT_PLATFORM_LABELS[
                  this.plugin.settings.agent_platform || "opencode"
                ] ??
                  this.plugin.settings.agent_platform ??
                  "opencode"
              )
            : configured
              ? t("config_configured")
              : t("setup_optional_needs_key"),
      });
      if (!checkbox.checked) continue;

      const config = row.createDiv({ cls: "pf-setup-optional-config" });
      if (opt.id === "ocr") {
        config.createEl("label", { text: t("field_paddleocr") });
        config.createEl("p", {
          cls: "caption",
          text: t("setup_optional_ocr_key_hint"),
        });
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
        const ocrAdv = config.createEl("details", {
          cls: "pf-adv-inline-details",
        });
        ocrAdv.createEl("summary", {
          text: "高级接口设置（普通用户无需修改，默认使用官方接口）",
        });
        ocrAdv.createEl("label", {
          text: t("ocr_job_url_label") || "PaddleOCR Job URL",
        });
        const jobUrl = ocrAdv.createEl("input", {
          cls: "pf-setup-ocr-extra-input",
          attr: {
            type: "text",
            placeholder:
              this.plugin.settings.paddleocr_job_url ||
              "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
          },
        }) as HTMLInputElement;
        jobUrl.value = this.plugin.settings.paddleocr_job_url || "";
        jobUrl.addEventListener("change", () => {
          this._setVectorDbConfig("paddleocr_job_url", jobUrl);
        });
        ocrAdv.createEl("label", {
          text: t("ocr_model_label") || "PaddleOCR Model",
        });
        const ocrModel = ocrAdv.createEl("input", {
          cls: "pf-setup-ocr-extra-input",
          attr: {
            type: "text",
            placeholder:
              this.plugin.settings.paddleocr_model || "PaddleOCR-VL-1.6",
          },
        }) as HTMLInputElement;
        ocrModel.value = this.plugin.settings.paddleocr_model || "";
        ocrModel.addEventListener("change", () => {
          this._setVectorDbConfig("paddleocr_model", ocrModel);
        });
        const commitOcrKey = async () => {
          const val = key.value.trim();
          if (!val) return;
          const saved = await this._storeSetupSecret("paddleocr-api-key", val);
          status.setText(
            saved ? t("setup_optional_saved") : t("setup_optional_save_failed")
          );
          if (saved) key.value = "";
        };
        pendingSecretSaves.push(commitOcrKey);
        const ocrSaveFooter = config.createDiv({
          cls: "pf-setup-optional-footer pf-test-conn-row",
        });
        const save = ocrSaveFooter.createEl("button", {
          cls: "pf-setup-verify",
          text: t("config_save"),
          attr: { type: "button" },
        });
        const testOcrBtn = ocrSaveFooter.createEl("button", {
          cls: "pf-btn pf-btn-secondary",
          text: "保存并测试连接",
          attr: { type: "button" },
        });
        const testOcrMsg = ocrSaveFooter.createEl("span", {
          cls: "pf-test-conn-status",
        });
        save.addEventListener("click", () => {
          void commitOcrKey();
        });
        testOcrBtn.addEventListener("click", () => {
          testOcrBtn.disabled = true;
          testOcrMsg.textContent = "测试中…";
          void commitOcrKey()
            .then(() => this.getClient().ocrTestConnection())
            .then((res) => {
              if (res?.passed) {
                testOcrMsg.className = "pf-test-conn-status is-ok";
                testOcrMsg.textContent = "✓ 密钥有效，可正常解析 PDF";
              } else {
                testOcrMsg.className = "pf-test-conn-status is-err";
                testOcrMsg.textContent = `✗ ${res?.error || "校验失败"}`;
              }
            })
            .catch((err) => {
              testOcrMsg.className = "pf-test-conn-status is-err";
              testOcrMsg.textContent = `✗ 测试失败：${String(err?.message || err).slice(0, 80)}`;
            })
            .finally(() => {
              testOcrBtn.disabled = false;
            });
        });
      } else if (opt.id === "memory") {
        config.createEl("label", {
          text: "选择 AI 语义服务商（自动匹配模型与维度）",
        });
        const presetSelect = config.createEl("select", {
          cls: "pf-setup-select",
        }) as HTMLSelectElement;
        const matchedPreset = matchEmbeddingPresetId(
          this.plugin.settings.vector_db_api_base || "",
          this.plugin.settings.vector_db_api_model || ""
        );
        const isZhOpt = t("nav_close") === "关闭";
        for (const p of EMBEDDING_PRESETS) {
          const o = presetSelect.createEl("option", {
            text: isZhOpt ? p.labelZh : p.labelEn,
            attr: { value: p.id },
          }) as HTMLOptionElement;
          o.selected = p.id === matchedPreset;
        }
        config.createEl("label", { text: t("feat_openai_key") });
        config.createEl("p", {
          cls: "caption",
          text: t("setup_optional_embedding_key_hint"),
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
        const memAdv = config.createEl("details", {
          cls: "pf-adv-inline-details",
        });
        memAdv.createEl("summary", {
          text: "高级：自定义模型名称、端点地址与兼容模式（选上方预设可免填）",
        });
        memAdv.createEl("label", { text: t("feat_api_model") });
        const model = memAdv.createEl("input", {
          cls: "pf-setup-input",
          attr: {
            type: "text",
            placeholder:
              this.plugin.settings.vector_db_api_model ||
              "text-embedding-3-small",
          },
        }) as HTMLInputElement;
        model.addEventListener("change", () => {
          this._setVectorDbConfig("vector_db_api_model", model);
        });
        memAdv.createEl("label", { text: t("feat_api_base_url") });
        const base = memAdv.createEl("input", {
          cls: "pf-setup-input",
          attr: {
            type: "text",
            placeholder:
              this.plugin.settings.vector_db_api_base ||
              "https://api.openai.com/v1",
          },
        }) as HTMLInputElement;
        base.addEventListener("change", () => {
          this._setVectorDbConfig("vector_db_api_base", base);
        });
        memAdv.createEl("label", {
          text: t("mem_provider_type_label") || "API Client Mode",
        });
        const ptype = memAdv.createEl("select", {
          cls: "pf-setup-select",
        }) as HTMLSelectElement;
        for (const [val, label] of [
          ["openai_sdk", "openai_sdk (OpenAI SDK)"],
          ["requests", "requests (HTTP Direct / Proxy)"],
        ]) {
          const option = ptype.createEl("option", {
            text: label,
            attr: { value: val },
          }) as HTMLOptionElement;
          option.selected =
            (this.plugin.settings.vector_db_provider_type || "openai_sdk") ===
            val;
        }
        ptype.addEventListener("change", () => {
          this._setVectorDbConfig("vector_db_provider_type", ptype);
        });
        presetSelect.addEventListener("change", () => {
          const picked = EMBEDDING_PRESETS.find(
            (p) => p.id === presetSelect.value
          );
          if (!picked || picked.id === "custom") return;
          model.value = picked.model;
          base.value = picked.baseUrl;
          this._setVectorDbConfig("vector_db_api_model", model);
          this._setVectorDbConfig("vector_db_api_base", base);
        });
        const commitMemKey = async () => {
          const val = key.value.trim();
          if (!val) return;
          const saved = await this._storeSetupSecret("vector-db-api-key", val);
          status.setText(
            saved ? t("setup_optional_saved") : t("setup_optional_save_failed")
          );
          if (saved) key.value = "";
        };
        pendingSecretSaves.push(commitMemKey);
        const memSaveFooter = config.createDiv({
          cls: "pf-setup-optional-footer pf-test-conn-row",
        });
        const save = memSaveFooter.createEl("button", {
          cls: "pf-setup-verify",
          text: t("config_save"),
          attr: { type: "button" },
        });
        const testMemBtn = memSaveFooter.createEl("button", {
          cls: "pf-btn pf-btn-secondary",
          text: "保存并测通维度",
          attr: { type: "button" },
        });
        const testMemMsg = memSaveFooter.createEl("span", {
          cls: "pf-test-conn-status",
        });
        save.addEventListener("click", () => {
          void commitMemKey();
        });
        testMemBtn.addEventListener("click", () => {
          testMemBtn.disabled = true;
          testMemMsg.textContent = "探测中…";
          void commitMemKey()
            .then(() => this.getClient().embedTestConnection())
            .then((res) => {
              testMemMsg.className = "pf-test-conn-status is-ok";
              testMemMsg.textContent = `✓ 已连通 · ${res.model} (${res.dimension} 维 · ${res.latency_ms}ms)`;
            })
            .catch((err) => {
              testMemMsg.className = "pf-test-conn-status is-err";
              testMemMsg.textContent = `✗ 测试失败：${String(err?.message || err).slice(0, 80)}`;
            })
            .finally(() => {
              testMemBtn.disabled = false;
            });
        });
      } else {
        config.createEl("label", { text: t("feat_agent_platform") });
        config.createEl("p", {
          cls: "caption",
          text: t("feat_agent_platform_desc"),
        });
        config.createEl("p", {
          cls: "caption",
          text: t("agent_external_cli_hint"),
        });
        const select = config.createEl("select") as HTMLSelectElement;
        const setupChoices = this.plugin.agentPlatformChoices.length
          ? this.plugin.agentPlatformChoices
          : Object.keys(AGENT_PLATFORM_LABELS);
        for (const value of setupChoices) {
          const option = select.createEl("option", {
            text: AGENT_PLATFORM_LABELS[value] ?? value,
            attr: { value },
          }) as HTMLOptionElement;
          option.selected = value === this.plugin.settings.agent_platform;
        }
        select.addEventListener("change", () => {
          const previous = String(this.plugin.settings.agent_platform ?? "");
          const value = select.value;
          // #142 / C0: mutation through the typed config command; report
          // "saved" only after the backend accepted, and never keep a
          // rejected value in the mirror or the select.
          void this.getClient()
            .configSet("agent_platform", value)
            .then(
              () => {
                this.plugin.settings.agent_platform = value;
                void this.plugin.saveSettings();
                status.setText(t("setup_optional_saved"));
              },
              (e) => {
                new Notice(
                  `PaperForge: config set agent_platform failed: ${String(e)}`
                );
                select.value = previous;
                status.setText(t("setup_optional_config_save_failed"));
              }
            );
        });
      }
    }
    const nav = containerEl.createDiv({ cls: "pf-setup-nav" });
    renderActionButton(nav, {
      label: t("setup_nav_exit"),
      variant: "ghost",
      onClick: () => this._goHome(),
    });
    renderActionButton(nav, {
      label: t("setup_nav_back"),
      variant: "secondary",
      onClick: () => {
        this._setupStage = 2;
        this.display();
      },
    });
    renderActionButton(nav, {
      label: t("setup_nav_continue"),
      onClick: () => {
        void Promise.all(pendingSecretSaves.map((fn) => fn())).finally(() => {
          this._refreshSetupReadiness();
        });
      },
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
      label: t("setup_nav_exit"),
      variant: "ghost",
      onClick: () => this._goHome(),
    });
    renderActionButton(nav, {
      label: t("setup_nav_back"),
      variant: "secondary",
      onClick: () => {
        this._setupStage = 3;
        this.display();
      },
    });
    if (!foundationReady || !libraryReady) {
      renderActionButton(nav, {
        label: t("setup_review_recheck"),
        variant: "secondary",
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
    this._attemptedProbes.delete("help");
    super.hide();
  }
}
