import {
  PluginSettingTab,
  App,
  Setting,
  Notice,
  setTooltip,
  MarkdownRenderer,
  Component,
  requestUrl,
} from "obsidian";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { migrateLegacySecret } from "./services/secret-storage";
import {
  managedNativeDaemonPath,
  resolveNativeDaemonBinary,
  syncStableDaemonEntry,
} from "./services/native-daemon";
import { t, setLanguage, langFromApp, getActiveLang } from "./i18n";
import { formatElapsedDuration, formatHumanError } from "./services/feedback";
import { resolveSetupDecision } from "./services/setup-decision-tree";
import {
  EMBEDDING_PRESETS,
  matchEmbeddingPresetId,
  renderDomainModePreview,
} from "./views/domain-preview";

interface InlineRenderOpts {
  inline?: boolean;
}

/** Translate raw provider/HTTP errors into plain beginner-friendly guidance. */
export function formatProviderConnectionError(
  rawErr: string,
  kind: "ocr" | "embed",
  isZh: boolean
): string {
  const lower = String(rawErr || "").toLowerCase();
  if (
    lower.includes("401") ||
    lower.includes("unauthorized") ||
    lower.includes("invalid_api_key") ||
    lower.includes("invalid token") ||
    lower.includes("authentication")
  ) {
    return isZh
      ? "API Key 无效或已过期，请核对是否复制完整"
      : "API Key is invalid or expired. Please check and re-paste it.";
  }
  if (
    lower.includes("429") ||
    lower.includes("quota") ||
    lower.includes("rate limit") ||
    lower.includes("insufficient") ||
    lower.includes("balance")
  ) {
    return isZh
      ? "免费额度已用完或触发限流，请稍后再试或检查账户余额"
      : "Quota exceeded or rate-limited. Check provider balance or retry later.";
  }
  if (lower.includes("dimension") || lower.includes("dims")) {
    return isZh
      ? "模型向量维度变化，保存后在「智能检索」点击重建索引即可（不影响笔记与 OCR）"
      : "Embedding dimension changed. Rebuild the vector index in Smart Retrieval (notes & OCR stay untouched).";
  }
  if (lower.includes("404") || lower.includes("model_not_found")) {
    return isZh
      ? "模型名称或接口地址不匹配，建议先选用内置预设"
      : "Model or endpoint URL not found. Try selecting a built-in preset.";
  }
  if (
    lower.includes("timeout") ||
    lower.includes("timed out") ||
    lower.includes("econnrefused") ||
    lower.includes("enotfound") ||
    lower.includes("network") ||
    lower.includes("connection")
  ) {
    return isZh
      ? "无法连接服务接口，请检查网络或代理设置"
      : "Cannot reach provider endpoint. Check network or proxy settings.";
  }
  if (lower.includes("no_python") || lower.includes("python")) {
    return isZh
      ? "请先点击第 1 步「一键启用引擎」，完成后再测通"
      : "Enable the Compute Engine in Step 1 first, then test connection.";
  }
  const compact = String(rawErr || "")
    .replace(/\s+/g, " ")
    .trim();
  const fallback =
    kind === "ocr"
      ? isZh
        ? "OCR 连通测试失败"
        : "OCR connection failed"
      : isZh
        ? "向量模型探测失败"
        : "Embedding probe failed";
  return compact ? `${fallback}：${compact.slice(0, 72)}` : fallback;
}
import type {
  AgentPresenceSnapshotDto,
  ZoteroDetectDto,
} from "./client/paperforge-client";
import {
  formatAgentClientName,
  normalizeAgentPresenceSnapshot,
} from "./client/paperforge-client";
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
import { setPfIcon } from "./views/icons";
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
import { isEngineVersionCompatible } from "./services/setup-decision-tree";
import type { RuntimeStatus } from "./client";
import { stripCredentialEnv } from "./services/secret-storage";
import { processProgressChunk } from "./services/progress-parser";
import type { RuntimeInstallerAction } from "./services/runtime-installer-launcher";
import {
  INSTALLER_FAILED_MARKER,
  installerLogPath,
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
  private _setupExpressAiOpen = false;
  private _setupExpressAiTab: "ocr" | "embed" | "easyscholar" = "ocr";
  private _expressCustomMode = false;
  private _expressFetchedModels: string[] = [];
  private _exploreChecklistDismissed = false;
  private _detectedFolderCollisionMsg: string | null = null;
  private _autoContinueSetupAfterInstall = false;
  private _pendingRuntimeRestartAfterDaemonSwap: RuntimeInstallerAction | null =
    null;
  private _setupPhase:
    | "idle"
    | "daemon_updating"
    | "installing_engine"
    | "configuring"
    | "syncing" = "idle";
  private _setupProxyUrl = "";
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
  private _pendingOrphans: { key: string; title?: string }[] = [];
  private _upgradePlanRequestedThisSession: boolean = false;
  /** Modules that have already been auto-probed (prevents endless re-probe). */
  private _attemptedProbes: Set<string> = new Set();
  /** Cached modules past TTL waiting for silent background revalidation (never flashed to Checking). */
  private _staleModulesNeedingSilentRefresh: Set<string> = new Set();
  private _overviewAutoProbedThisSession = false;
  private _silentRevalidating = false;
  /** Expanded accordion row ids on the 1-screen Control Center. */
  private _expandedInlineModules: Set<string> = new Set();
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
  /** Byte offset in installer.log when this run started (-1 = attaching mid-run). */
  private _installerLogStartOffset = 0;
  /** True when the active install/update is owned by the native Rust daemon queue. */
  private _daemonDrivenRuntimeInstall = false;
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
  private _liveActivityTimer: ReturnType<typeof setInterval> | null = null;
  private _liveElapsedEl: HTMLElement | null = null;
  private _liveElapsedStartedAt: number | null = null;
  /** Step id the guided library flow keeps expanded after an explicit edit. */
  private _setupOpenStep: string | null = null;
  /** True while a library sync or memory build is in flight. */
  _libraryRunning: boolean = false;
  private _displayInProgress: boolean = false;
  private _isOpen: boolean = false;
  private _readModelsDirty: boolean = false;
  private _lastPersistedCapJson: string | null = null;
  private _quickFilterQuery: string = "";
  private _lastRenderedTab: string = "overview";
  _detailReturn: { tab: string; selector: string } | null = null;
  private _agentPlatformDraft: string | null = null;
  private _agentPresenceCache: AgentPresenceSnapshotDto | null = null;
  private _agentPresenceProbedThisSession = false;
  private _agentPresenceWsRef: unknown = null;

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

  /** Re-render only when Settings modal is actually open (0 CPU/DOM churn in background). */
  refreshIfOpen(): void {
    if (!this._isOpen || this._displayInProgress) return;
    this.display();
  }

  display() {
    this._isOpen = true;
    this._displayInProgress = true;
    const wsPresence = (
      this.app as unknown as {
        workspace?: {
          on?: (ev: string, cb: (payload?: unknown) => void) => unknown;
        };
      }
    )?.workspace;
    if (!this._agentPresenceWsRef && typeof wsPresence?.on === "function") {
      this._agentPresenceWsRef = wsPresence.on(
        "paperforge:agent-presence-changed",
        (payload?: unknown) => {
          const next = (
            payload as { presence?: AgentPresenceSnapshotDto } | undefined
          )?.presence;
          if (next && typeof next === "object") {
            this._agentPresenceCache = normalizeAgentPresenceSnapshot(
              next,
              this._getVaultBasePath() || undefined
            );
          } else if (typeof this.plugin.getAgentPresence === "function") {
            const cached = this.plugin.getAgentPresence();
            if (cached) {
              this._agentPresenceCache = cached;
            }
          }
          this.refreshIfOpen();
        }
      );
    }
    this._refreshAgentPresenceOnce();
    if (this.plugin?.settings?.language) {
      setLanguage(this.app, this.plugin.settings.language);
    }
    if (this._readModelsDirty) {
      this._readModelsDirty = false;
      this._overviewAutoProbedThisSession = false;
    }
    const { containerEl } = this;
    const preserveScroll = this._lastRenderedTab === this.activeTab;
    const prevScrollTop = preserveScroll
      ? containerEl.scrollTop || containerEl.parentElement?.scrollTop || 0
      : 0;
    this._lastRenderedTab = this.activeTab;
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

    const pfHost = this.plugin as unknown as {
      getPendingReleaseNotesVersion?: () => string | null;
      openReleaseNotesModal?: () => void;
    };
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
    const pendingRelVer = pfHost.getPendingReleaseNotesVersion?.();
    if (pendingRelVer) {
      const relPill = brandLeft.createEl("button", {
        cls: "pf-cc-topbar-whatsnew",
        type: "button",
        text: t("topbar_whats_new"),
        attr: { "data-pf-testid": "release-notes-banner-open" },
      });
      relPill.addEventListener("click", () => {
        pfHost.openReleaseNotesModal?.();
      });
    }

    // Center: 4 focused pages — Overview, Modules, Appearance, Help
    const tabCenter = topbar.createDiv({ cls: "pf-cc-topbar-center" });
    const tabs = [
      { id: "overview", label: t("tab_overview") || "Overview" },
      { id: "module-detail", label: t("tab_modules") || "Modules" },
      { id: "appearance", label: t("tab_appearance") || "Appearance" },
      { id: "help", label: t("tab_help") || "Help" },
    ];
    const tabContents: Record<string, HTMLDivElement> = {};

    tabs.forEach((tab) => {
      const btn = tabCenter.createEl("button", {
        cls:
          "pf-cc-topbar-tab" +
          (tab.id === this.activeTab ? " pf-cc-topbar-tab--active" : ""),
        text: tab.label,
        attr: { type: "button", "data-pf-tab": tab.id },
      });
      btn.addEventListener("click", () => {
        this._detailReturn = null;
        this.activeTab = tab.id;
        if (tab.id === "module-detail" && !this._selectedDetailModule) {
          this._selectedDetailModule = "library";
        }
        if (tab.id === "help") this._attemptedProbes.delete("help");
        this._navMemory = { destination: tab.id };
        this._persistNavMemory();
        this.display();
      });
    });

    if (this.activeTab === "overview") {
      const quickWrap = topbar.createDiv({ cls: "pf-cc-topbar-right" });
      const quickInput = quickWrap.createEl("input", {
        cls: "pf-cc-quick-filter",
        type: "search",
        placeholder: t("cc_quick_filter_placeholder") || "Quick filter…",
        attr: {
          "aria-label": t("cc_quick_filter_aria") || "Quick filter modules",
          "data-pf-testid": "cc-quick-filter",
        },
      }) as HTMLInputElement;
      quickInput.value = this._quickFilterQuery;
      quickInput.addEventListener("input", () => {
        this._quickFilterQuery = quickInput.value.trim().toLowerCase();
        this._applyControlCenterQuickFilter(containerEl);
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

    // --- Render active tab ---
    if (this.activeTab === "overview") {
      this._renderOverviewTab(tabContents.overview);
    } else if (this.activeTab === "module-detail") {
      this._renderModuleDetailTab(tabContents["module-detail"]);
    } else if (this.activeTab === "appearance") {
      this._renderAppearanceTab(tabContents.appearance);
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
    if (this._quickFilterQuery && this.activeTab === "overview") {
      this._applyControlCenterQuickFilter(containerEl);
    }
    if (prevScrollTop > 0) {
      if (containerEl.scrollHeight >= prevScrollTop) {
        containerEl.scrollTop = prevScrollTop;
      } else if (containerEl.parentElement) {
        containerEl.parentElement.scrollTop = prevScrollTop;
      }
    }
    this._displayInProgress = false;
  }

  private _applyControlCenterQuickFilter(root: HTMLElement): void {
    const q = this._quickFilterQuery;
    const rows = root.querySelectorAll<HTMLElement>(
      ".pf-cc-module-card, .pf-cc-row, .pf-cc-nav-row"
    );
    rows.forEach((row) => {
      if (!q) {
        row.style.display = "";
        return;
      }
      const txt = (row.textContent || "").toLowerCase();
      row.style.display = txt.includes(q) ? "" : "none";
    });
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
    this._setupPhase = "configuring";
    this._setupFeedback = null;
    this._setupFailureDetail = null;
    const settings = this.plugin.settings;
    const effectiveZoteroDir =
      settings.zotero_data_dir?.trim() ||
      (this._zoteroDetectData?.found
        ? this._zoteroDetectData.zotero_dir?.trim()
        : "") ||
      "";
    if (effectiveZoteroDir && !settings.zotero_data_dir?.trim()) {
      settings.zotero_data_dir = effectiveZoteroDir;
    }
    const paths: Record<string, string | undefined> = {
      zotero_data_dir: effectiveZoteroDir || settings.zotero_data_dir,
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
            zoteroData: effectiveZoteroDir || undefined,
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
            this._setupPhase = "idle";
            this._setupFeedback = t("setup_install_cancelled");
            this.display();
            return;
          }
          this._setupOperation = "failed";
          this._setupPhase = "idle";
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
          this._setupPhase = "idle";
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
        // canonical index from Zotero. Always run it — deciding from a
        // just-requested probe races the async envelope update.
        this._setupOperation = "running";
        this._setupPhase = "syncing";
        const syncStartedAt = Date.now();
        const initialLive = this.plugin?.getLiveTaskSummary?.("sync");
        this._setupFeedback = initialLive?.phaseText
          ? `${initialLive.phaseText} (0s)`
          : `${t("setup_library_syncing")} (0s)`;
        this.display();
        const syncTicker = setInterval(() => {
          if (this._setupOperation !== "running") return;
          const elapsedSec = Math.max(
            1,
            Math.floor((Date.now() - syncStartedAt) / 1000)
          );
          const live = this.plugin?.getLiveTaskSummary?.("sync");
          const label = live?.phaseText || t("setup_library_syncing");
          this._setupFeedback = `${label} (${elapsedSec}s)`;
          if (this._isOpen && elapsedSec % 2 === 0) {
            this.display();
          }
        }, 1000);
        try {
          await this.getClient().sync();
        } catch (error) {
          console.error("PaperForge library sync failed:", error);
          this._setupOperation = "failed";
          this._setupPhase = "idle";
          this._setupFeedback = t("setup_library_sync_failed");
          const msg = this._formatSetupFailure(error);
          if (msg) this._setupFailureDetail = msg;
          this.display();
          return;
        } finally {
          clearInterval(syncTicker);
        }
        this._attemptedProbes.add("library");
        this._probeModule("library");
        this._setupOperation = "idle";
        this._setupPhase = "idle";
        this._setupFeedback = t("setup_library_configured");
        if (opts?.autoCompleteOnSuccess) {
          this.plugin.settings._setup_complete = true;
          await this.plugin.saveSettings();
        }
        await (
          this.plugin as unknown as {
            refreshUpgradePlan?: () => Promise<unknown>;
          }
        )
          .refreshUpgradePlan?.()
          .catch(() => undefined);
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
        this._setupPhase = "idle";
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

  /** Render the serene Overview tab (Decision-Tree Hero + 1-line module directory). */
  _renderOverviewTab(containerEl: HTMLElement) {
    const vaultPath = this._getVaultBasePath();
    if (!this.plugin.settings.vault_path) {
      this.plugin.settings.vault_path = vaultPath;
      this._debouncedSave();
    }

    // Coalesce startup checks into ONE background refresh without flashing cached cards to "Checking...".
    let hasNeverProbed = false;
    for (const mod of CAPABILITY_MODULES) {
      if (mod === "maintenance") continue;
      const env = this._capabilityState?.[mod];
      if (!env) continue;
      if (
        env.capability_state === "unknown" &&
        env.updated_at === new Date(0).toISOString()
      ) {
        hasNeverProbed = true;
      }
    }
    const clientObj =
      typeof (this.plugin as unknown as { getClient?: unknown })?.getClient ===
      "function"
        ? (
            this.plugin as unknown as {
              getClient: () => { probeAll?: unknown };
            }
          ).getClient()
        : null;
    if (
      clientObj &&
      typeof clientObj.probeAll === "function" &&
      !this._overviewAutoProbedThisSession &&
      (hasNeverProbed || this._staleModulesNeedingSilentRefresh.size > 0)
    ) {
      this._overviewAutoProbedThisSession = true;
      this._staleModulesNeedingSilentRefresh.clear();
      this._refreshAllReadModels({ silent: !hasNeverProbed });
    }

    // ── Ensure Veteran Vault Upgrade Plan is fetched even if startup missed it ──
    const cachedUpgradePlan =
      typeof this.plugin.getUpgradePlanCache === "function"
        ? this.plugin.getUpgradePlanCache()
        : null;
    if (
      !cachedUpgradePlan &&
      !this._upgradePlanRequestedThisSession &&
      typeof this.plugin.refreshUpgradePlan === "function"
    ) {
      this._upgradePlanRequestedThisSession = true;
      void this.plugin
        .refreshUpgradePlan()
        .then((plan: unknown) => {
          if (plan && !this._displayInProgress) {
            this.display();
          }
        })
        .catch(() => undefined);
    }

    // ── Serene Control Center (Decision-Tree Hero + Compact Navigation Rows) ──
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

  private _captureInstallerLogStartOffset(logPath: string): number {
    try {
      return fs.statSync(logPath).size;
    } catch {
      return 0;
    }
  }

  /** Attach Settings progress UI if a daemon background runtime job is already active. */
  private _syncRuntimePollFromBackground(): boolean {
    if (this._runtimePollTimer) return true;
    if (!this.plugin?.isRuntimeUpdating?.()) return false;
    this._daemonDrivenRuntimeInstall = true;
    this._installerLogPath = installerLogPath();
    this._installerLogStartOffset = -1;
    if (this._setupOperation === "failed") {
      this._setupFeedback = null;
      this._setupFailureDetail = null;
    }
    this._setupOperation = "running";
    this._setupPhase = "installing_engine";
    this._pollRuntimeUntilReady();
    return true;
  }

  /** Fast-path transition invoked by main.ts when daemon task.updated reports terminal runtime state. */
  onDaemonRuntimeJobFinished(
    status: "succeeded" | "failed" | "cancelled" | boolean,
    errorDetail?: string
  ): void {
    const normStatus: "succeeded" | "failed" | "cancelled" =
      status === true ? "succeeded" : status === false ? "failed" : status;
    const hasActiveObserver =
      this._daemonDrivenRuntimeInstall ||
      Boolean(this._runtimePollTimer) ||
      this._autoContinueSetupAfterInstall;
    if (!hasActiveObserver) return;

    if (normStatus === "succeeded") {
      this._pendingRuntimeRestartAfterDaemonSwap = null;
      this._refreshRuntimeStatus(true);
      this._stopRuntimePoll(true);
      return;
    }

    if (normStatus === "cancelled") {
      // Old daemon cancels in-flight runtime jobs during binary hot-swap.
      // Preserve Express auto-chain and queue seamless resume on the new daemon.
      if (this.plugin?.isDaemonUpdating?.()) {
        if (this._runtimePollTimer) {
          clearInterval(this._runtimePollTimer);
          this._runtimePollTimer = null;
        }
        this._daemonDrivenRuntimeInstall = false;
        this._pendingRuntimeRestartAfterDaemonSwap =
          this._currentRuntimeAction();
        this._setupOperation = "running";
        this._setupPhase = "daemon_updating";
        this._setupFeedback = t("runtime_daemon_swapping_resume");
        this._setupFailureDetail = null;
        this.display();
        return;
      }

      const ptr = readRuntimePointer();
      const pluginVersion = String(this.plugin?.manifest?.version ?? "");
      if (
        ptr &&
        pluginVersion &&
        isEngineVersionCompatible(
          ptr.paperforgeVersion,
          pluginVersion,
          this._minEngineVersion()
        )
      ) {
        this._pendingRuntimeRestartAfterDaemonSwap = null;
        this._refreshRuntimeStatus(true);
        this._stopRuntimePoll(true);
        return;
      }

      this._stopRuntimePoll(false, t("runtime_install_cancelled"));
      return;
    }

    this._stopRuntimePoll(
      false,
      undefined,
      errorDetail || this._installerLogTail() || "runtime setup failed",
      "runtime_install_step_failed"
    );
  }

  /** Resume a runtime install/auto-chain queued while the daemon binary hot-swapped. */
  onDaemonSwapFinished(): void {
    const pendingAction = this._pendingRuntimeRestartAfterDaemonSwap;
    this._pendingRuntimeRestartAfterDaemonSwap = null;
    this._refreshRuntimeStatus(true);
    if (!pendingAction) {
      this.display();
      return;
    }
    const ptr = readRuntimePointer();
    const pluginVersion = String(this.plugin?.manifest?.version ?? "");
    if (
      ptr &&
      pluginVersion &&
      isEngineVersionCompatible(
        ptr.paperforgeVersion,
        pluginVersion,
        this._minEngineVersion()
      )
    ) {
      this._stopRuntimePoll(true);
      return;
    }
    this._launchRuntimeInstaller(pendingAction, {
      autoContinueSetup: this._autoContinueSetupAfterInstall,
    });
  }

  /** Launch or attach to the single runtime installer owner (Rust daemon coalesced queue first). */
  private _launchRuntimeInstaller(
    action: RuntimeInstallerAction,
    opts?: { autoContinueSetup?: boolean }
  ): void {
    if (opts?.autoContinueSetup) {
      this._autoContinueSetupAfterInstall = true;
    }
    this._setupFeedback = null;
    this._setupFailureDetail = null;
    if (this.plugin?.isDaemonUpdating?.()) {
      this._pendingRuntimeRestartAfterDaemonSwap = action;
      this._setupOperation = "running";
      this._setupPhase = "daemon_updating";
      this._setupFeedback = t("runtime_daemon_swapping_resume");
      this.display();
      return;
    }
    if (this.plugin?.isRuntimeUpdating?.()) {
      this._syncRuntimePollFromBackground();
      new Notice(t("runtime_update_already_running"), 8000);
      this.display();
      return;
    }
    const isZh = getActiveLang(this.app) === "zh";
    const launchOpts: {
      allowUvDownload: boolean;
      proxyUrl?: string;
      preferCnMirror?: boolean;
    } = { allowUvDownload: true };
    if (this._setupProxyUrl.trim()) {
      launchOpts.proxyUrl = this._setupProxyUrl.trim();
    }
    if (isZh) {
      launchOpts.preferCnMirror = true;
    }
    const client = this.getClient();
    if (
      typeof client.hasDaemonRpc === "function" &&
      client.hasDaemonRpc() &&
      typeof client.daemonSubmitRuntimeJob === "function"
    ) {
      const logPath = installerLogPath();
      this._installerLogPath = logPath;
      this._installerLogStartOffset =
        this._captureInstallerLogStartOffset(logPath);
      this._daemonDrivenRuntimeInstall = true;
      this._setupOperation = "running";
      this._setupPhase = "installing_engine";
      this._pollRuntimeUntilReady();
      this.display();
      void client
        .daemonSubmitRuntimeJob(action, this.plugin.manifest.version, {
          proxyUrl: launchOpts.proxyUrl,
          preferCnMirror: launchOpts.preferCnMirror,
        })
        .then(
          (res) => {
            if (res?.accepted) {
              new Notice(
                res.coalesced
                  ? t("runtime_update_already_running")
                  : t("runtime_installer_opened"),
                8000
              );
              return;
            }
            this._daemonDrivenRuntimeInstall = false;
            if (this._runtimePollTimer) {
              clearInterval(this._runtimePollTimer);
              this._runtimePollTimer = null;
            }
            this._launchDetachedInstallerFallback(action, launchOpts);
          },
          () => {
            this._daemonDrivenRuntimeInstall = false;
            if (this._runtimePollTimer) {
              clearInterval(this._runtimePollTimer);
              this._runtimePollTimer = null;
            }
            this._launchDetachedInstallerFallback(action, launchOpts);
          }
        );
      return;
    }
    this._launchDetachedInstallerFallback(action, launchOpts);
  }

  private _launchDetachedInstallerFallback(
    action: RuntimeInstallerAction,
    launchOpts: {
      allowUvDownload: boolean;
      proxyUrl?: string;
      preferCnMirror?: boolean;
    }
  ): void {
    const defaultLog = installerLogPath();
    this._installerLogStartOffset =
      this._captureInstallerLogStartOffset(defaultLog);
    const result = this.getClient().launchRuntimeInstaller(
      action,
      this.plugin.manifest.version,
      launchOpts
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
    const chosenLog = result.logPath ?? defaultLog;
    if (chosenLog !== defaultLog) {
      this._installerLogStartOffset =
        this._captureInstallerLogStartOffset(chosenLog);
    }
    this._installerLogPath = chosenLog;
    new Notice(t("runtime_installer_opened"), 8000);
    if (this._setupOperation === "idle") this._setupOperation = "running";
    this._pollRuntimeUntilReady();
    this.display();
  }

  /** Read installer.log strictly from the start of the active run (never stale prior errors). */
  private _readInstallerLogSinceStart(): string {
    if (!this._installerLogPath) return "";
    try {
      const buf = fs.readFileSync(this._installerLogPath);
      if (this._installerLogStartOffset < 0) {
        const full = buf.toString("utf-8");
        const markers = [
          "[PaperForge] Publishing verified runtime environment",
          "[PaperForge] Installing managed Python",
          "[PaperForge] Downloading uv",
        ];
        let cutIdx = -1;
        for (const m of markers) {
          const idx = full.lastIndexOf(m);
          if (idx > cutIdx) cutIdx = idx;
        }
        return cutIdx >= 0 ? full.slice(cutIdx) : full.slice(-4096);
      }
      const slice =
        buf.length >= this._installerLogStartOffset
          ? buf.subarray(this._installerLogStartOffset)
          : buf;
      return slice.toString("utf-8");
    } catch {
      return "";
    }
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
      const logSinceStart = this._readInstallerLogSinceStart();
      // If another installer already holds install.lock and is finishing, keep polling
      // instead of aborting early — runtime_ready will flip true when it finishes.
      const lockContentionOnly = logSinceStart.includes(
        "Another PaperForge runtime install is already running"
      );
      if (
        logSinceStart.includes(INSTALLER_FAILED_MARKER) &&
        !lockContentionOnly
      ) {
        this._stopRuntimePoll(
          false,
          undefined,
          undefined,
          "runtime_install_step_failed"
        );
        return;
      }
      if (Date.now() - startedAt > 25 * 60 * 1000) {
        this._stopRuntimePoll(
          false,
          undefined,
          undefined,
          "runtime_install_step_failed"
        );
        return;
      }
      this._refreshRuntimeStatus(true);
      this.display();
    }, 3000);
  }

  /** The installer's current phase translated into beginner-friendly progress text. */
  private _installerProgressLine(): string {
    const raw = this._readInstallerLogSinceStart();
    if (!raw) return "";
    const lines = raw.split(/\r?\n/).filter((line) => line.trim());
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
    return "";
  }

  /** Last lines the detached installer wrote (empty when unreadable). */
  private _installerLogTail(): string {
    const raw = this._readInstallerLogSinceStart();
    if (!raw) return "";
    return raw.trim().split(/\r?\n/).slice(-6).join(" | ");
  }

  isRuntimeInstallPollingActive(): boolean {
    return Boolean(this._runtimePollTimer);
  }

  private _triggerRuntimeUpgrade(): void {
    this._launchRuntimeInstaller("update");
  }

  private _stopRuntimePoll(
    ready: boolean,
    cancelReason?: string,
    errorDetailOverride?: string,
    templateKey:
      | "runtime_install_step_failed"
      | "runtime_installer_failed" = "runtime_install_step_failed"
  ): void {
    if (this._runtimePollTimer) {
      clearInterval(this._runtimePollTimer);
      this._runtimePollTimer = null;
    }
    this._daemonDrivenRuntimeInstall = false;
    this._pendingRuntimeRestartAfterDaemonSwap = null;
    this._setupPhase = "idle";
    if (ready) {
      this._setupOperation = "idle";
      this._setupFeedback = null;
      this._setupFailureDetail = null;
    } else if (this._setupOperation === "running") {
      this._setupOperation = cancelReason ? "idle" : "failed";
      if (cancelReason) {
        this._setupFeedback = cancelReason;
      } else {
        // Say why the poll gave up: a template with an empty slot tells the
        // user nothing and hides the failing command's own message.
        const detail =
          errorDetailOverride ||
          this._runtimeStatusError ||
          this._installerLogTail() ||
          "";
        this._setupFeedback = t(templateKey).replace(
          "{error}",
          detail || "the runtime did not become ready in time"
        );
      }
    } else if (cancelReason) {
      this._setupFeedback = cancelReason;
    }
    if (ready) this._setupReinstallRequested = false;
    const shouldChainSetup = ready && this._autoContinueSetupAfterInstall;
    this._autoContinueSetupAfterInstall = false;
    this._refreshRuntimeStatus(true);
    this.display();
    if (ready) {
      new Notice(t("runtime_install_complete"));
      if (shouldChainSetup) {
        this._applyLibraryConfiguration({ autoCompleteOnSuccess: true });
      }
    } else if (cancelReason) {
      new Notice(cancelReason);
    }
  }

  private _cancelRuntimePoll(): void {
    this._stopRuntimePoll(false, t("runtime_install_cancelled"));
  }

  /** Render the Installation detail view (Issue #77). */
  /** Render Foundation with the shared module-detail shell. */
  _renderInstallationDetail(
    containerEl: HTMLElement,
    opts?: InlineRenderOpts
  ): void {
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
    if (!opts?.inline) {
      this._renderModuleDetailShell(containerEl, "installation", false);
    }
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
    const sysDirRaw = this.plugin.settings.system_dir || "System";
    const sysLeaf = sysDirRaw
      .replace(/[\\/]+$/, "")
      .split(/[\\/]/)
      .pop();
    const systemDir =
      sysLeaf === ".paperforge"
        ? path.join(vp, sysDirRaw)
        : path.join(vp, sysDirRaw, "PaperForge");
    const systemDisplayPath =
      sysLeaf === ".paperforge"
        ? sysDirRaw
        : `${sysDirRaw.replace(/[\\/]+$/, "")}/PaperForge`;
    const hasSystem = fs.existsSync(systemDir);
    addCheck(
      t("foundation_vault_structure"),
      hasSystem
        ? t("cc_badge_ready") || "Ready"
        : t("cc_badge_setup_required") || "Setup Required",
      hasSystem ? systemDisplayPath : t("foundation_vault_missing"),
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
    const runtimeInProgress =
      this._syncRuntimePollFromBackground() || Boolean(this._runtimePollTimer);
    if (!runtimeReady) {
      if (runtimeInProgress) {
        body.createEl("p", {
          cls: "pf-setup-status",
          text: this._installerProgressLine() || t("runtime_installing"),
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

    // Deferred Storage Cleanup & Time-Machine Rollback (scoped inside Engine maintenance)
    if (!opts?.inline) {
      const cachedUpgradePlan =
        typeof this.plugin.getUpgradePlanCache === "function"
          ? this.plugin.getUpgradePlanCache()
          : null;
      if (cachedUpgradePlan && typeof this.plugin.getClient === "function") {
        renderStorageMigrationMaintenanceSection(
          body,
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

      const reconcileClient =
        typeof this.plugin.getClient === "function" ? this.getClient() : null;
      if (
        reconcileClient &&
        typeof reconcileClient.reconcileVault === "function"
      ) {
        const isZhReconcile = t("nav_close") === "关闭";
        const reconcileSection = body.createDiv({
          cls: "pf-upgrade-maint-section",
          attr: { "data-pf-testid": "reconcile-local-cache-section" },
        });
        new Setting(reconcileSection)
          .setName(
            isZhReconcile
              ? "重建本地索引与视图缓存"
              : "Rebuild Local Index Cache"
          )
          .setDesc(
            isZhReconcile
              ? "非破坏性同步 workspace_registry、衍生索引路径与默认视图模板，绝不修改您的笔记正文、批注或阅读记录。"
              : "Non-destructively reconcile workspace_registry, derived index paths, and canonical Base views without modifying note bodies, annotations, or reading logs."
          )
          .addButton((btn) =>
            btn
              .setButtonText(
                isZhReconcile
                  ? "重建本地索引与视图缓存"
                  : "Rebuild Local Index Cache"
              )
              .onClick(() => {
                void (async () => {
                  btn.setDisabled(true);
                  try {
                    await reconcileClient.reconcileVault(true);
                    new Notice(
                      isZhReconcile
                        ? "本地索引与视图缓存已重建完成"
                        : "Local index & view cache rebuilt"
                    );
                    const pluginCtl = this.plugin as unknown as {
                      refreshBaseSnapshot?: () => Promise<unknown>;
                      refreshUpgradePlan?: () => Promise<unknown>;
                    };
                    await pluginCtl
                      .refreshBaseSnapshot?.()
                      .catch(() => undefined);
                    await pluginCtl
                      .refreshUpgradePlan?.()
                      .catch(() => undefined);
                  } catch (err: unknown) {
                    new Notice(
                      (isZhReconcile
                        ? "重建本地索引失败："
                        : "Index rebuild failed: ") + formatHumanError(err),
                      8000
                    );
                  } finally {
                    btn.setDisabled(false);
                  }
                })();
              })
          );
      }
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
    const existing = this._capabilityState?.[mod];
    const hasCachedState =
      Boolean(existing) &&
      existing!.updated_at !== new Date(0).toISOString() &&
      existing!.user_state !== "detection_failed";
    this._probeModule(mod, undefined, { silent: hasCachedState });
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
  _renderLibraryDetail(
    containerEl: HTMLElement,
    opts?: InlineRenderOpts
  ): void {
    if (!opts?.inline) {
      this._renderModuleDetailShell(containerEl, "library");
    }
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
  _renderOcrDetail(containerEl: HTMLElement, opts?: InlineRenderOpts): void {
    if (!opts?.inline) {
      this._renderModuleDetailShell(containerEl, "ocr");
    }
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
  private _mcpTargetRelpath(platform: string): string {
    const p = (platform || "claude").toLowerCase();
    if (p === "opencode") return "opencode.json";
    if (p === "cursor") return ".cursor/mcp.json";
    return ".mcp.json";
  }

  private _getVaultMcpConfigStatus(
    vaultBase: string,
    platform: string
  ): "ready" | "stale_binary" | "not_configured" {
    if (!vaultBase) return "not_configured";
    const rel = this._mcpTargetRelpath(platform);
    const targetFile = path.join(vaultBase, rel);
    if (!fs.existsSync(targetFile)) return "not_configured";
    try {
      const parsed = JSON.parse(fs.readFileSync(targetFile, "utf-8")) as Record<
        string,
        unknown
      >;
      if ((platform || "").toLowerCase() === "opencode") {
        const mcp = parsed.mcp as
          | Record<string, Record<string, unknown>>
          | undefined;
        const pf = mcp?.paperforge;
        if (!pf) return "not_configured";
        const cmdArr = Array.isArray(pf.command) ? pf.command : [];
        const bin = String(cmdArr[0] || "");
        return bin && fs.existsSync(bin) ? "ready" : "stale_binary";
      }
      const servers = parsed.mcpServers as
        | Record<string, Record<string, unknown>>
        | undefined;
      const pf = servers?.paperforge;
      if (!pf) return "not_configured";
      const bin = String(pf.command || "");
      return bin && fs.existsSync(bin) ? "ready" : "stale_binary";
    } catch {
      return "not_configured";
    }
  }

  private _resolvePreferredDaemonBin(vaultBase: string): string {
    const stable = managedNativeDaemonPath();
    if (fs.existsSync(stable)) return stable;
    const found = resolveNativeDaemonBinary({ vaultPath: vaultBase });
    if (found) {
      return syncStableDaemonEntry(found);
    }
    return stable;
  }

  private _buildLocalMcpConfig(
    vaultBase: string,
    platform: string,
    binPath: string
  ): { targetRel: string; snippet: Record<string, unknown>; text: string } {
    const p = (platform || "claude").toLowerCase();
    const targetRel = this._mcpTargetRelpath(p);
    if (p === "opencode") {
      const snippet = {
        mcp: {
          paperforge: {
            type: "local",
            command: [binPath, "--mcp", "--vault", vaultBase],
            enabled: true,
          },
        },
      };
      return { targetRel, snippet, text: JSON.stringify(snippet, null, 2) };
    }
    const snippet = {
      mcpServers: {
        paperforge: {
          command: binPath,
          args: ["--mcp", "--vault", vaultBase],
        },
      },
    };
    if (p === "codex") {
      const esc = (s: string) => s.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
      const toml = `[mcp_servers.paperforge]\ncommand = "${esc(binPath)}"\nargs = ["--mcp", "--vault", "${esc(vaultBase)}"]`;
      return { targetRel, snippet, text: toml };
    }
    return { targetRel, snippet, text: JSON.stringify(snippet, null, 2) };
  }

  private _installLocalMcpFallback(
    vaultBase: string,
    platform: string,
    binPath: string
  ): string {
    const p = (platform || "claude").toLowerCase();
    const { targetRel, snippet } = this._buildLocalMcpConfig(
      vaultBase,
      p,
      binPath
    );
    const targetFile = path.join(vaultBase, targetRel);
    let root: Record<string, unknown> = {};
    if (fs.existsSync(targetFile)) {
      const raw = fs.readFileSync(targetFile, "utf-8").trim();
      if (raw) {
        const parsed = JSON.parse(raw) as unknown;
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
          throw new Error(`${targetRel} is not a JSON object`);
        }
        root = parsed as Record<string, unknown>;
      }
    }
    const topKey = p === "opencode" ? "mcp" : "mcpServers";
    const existingSection = root[topKey];
    if (
      existingSection !== undefined &&
      (!existingSection ||
        typeof existingSection !== "object" ||
        Array.isArray(existingSection))
    ) {
      throw new Error(`Key '${topKey}' in ${targetRel} is not a JSON object`);
    }
    const mergedSection = {
      ...((existingSection as Record<string, unknown>) ?? {}),
      ...((snippet[topKey] as Record<string, unknown>) ?? {}),
    };
    root[topKey] = mergedSection;
    fs.mkdirSync(path.dirname(targetFile), { recursive: true });
    const tmp = `${targetFile}.${process.pid}.${Date.now()}.tmp`;
    fs.writeFileSync(tmp, JSON.stringify(root, null, 2) + "\n", "utf-8");
    fs.renameSync(tmp, targetFile);
    return targetRel;
  }

  private _readSkillHubAndInstallCount(): {
    hubReady: boolean;
    hubDir: string;
    installCount: number;
  } {
    const home = os.homedir();
    const hubDir = path.join(home, ".paperforge", "skills", "paperforge");
    const hubReady = fs.existsSync(path.join(hubDir, "SKILL.md"));
    let installCount = 0;
    try {
      const regFile = path.join(home, ".paperforge", "agent-installs.json");
      if (fs.existsSync(regFile)) {
        const parsed = JSON.parse(fs.readFileSync(regFile, "utf-8")) as {
          installs?: unknown[];
        };
        if (Array.isArray(parsed?.installs)) {
          installCount = parsed.installs.length;
        }
      }
    } catch {
      // Ignore corrupt registry during status display
    }
    return { hubReady, hubDir, installCount };
  }

  private _buildLocalOnboardingPrompt(
    vaultBase: string,
    binPath: string,
    skillHubDir: string,
    isZh: boolean
  ): string {
    const checkCmd = `"${binPath}" mcp-check --vault "${vaultBase}" --mcp-config "<MCP_CONFIG_PATH>" --probe-mcp --json`;
    if (isZh) {
      return (
        `请为当前 Agent 环境接入 PaperForge 全局轻量 MCP 服务（**推荐写入你自身平台的全局 MCP 配置**以便跨项目随时调用；在无关编程/闲聊中保持完全静默，**不要往用户的 Obsidian Vault 根目录写入 \`.agents/\` 或 \`.mcp.json\` 等杂项文件**）：\n\n` +
        `### 本机真实路径（禁止猜测或自行拼接）\n` +
        `- Vault 路径：\`${vaultBase}\`\n` +
        `- MCP 稳定入口：\`${binPath}\`\n` +
        `- MCP 启动参数：\`["--mcp", "--vault", "${vaultBase}"]\`\n` +
        `- 可选 Skill 源目录：\`${skillHubDir}\`\n\n` +
        `### 请按以下 2 步接入并验证\n` +
        `1. **注册 \`paperforge\` 全局 stdio MCP 服务**：按你自身平台的原生全局配置格式，非破坏性地合并添加名为 \`paperforge\` 的 stdio 服务，严禁覆盖用户已有其他 MCP 服务。连接后服务端会在握手时自动注入精简操作规程与 11 个 MCP 工具。\n` +
        `2. **运行握手自检**：\n   \`\`\`bash\n   ${checkCmd}\n   \`\`\`\n` +
        `   确认 \`data.mcp_handshake_ok == true\`；如当前会话支持热加载，立即调用 \`paperforge_brief\` 完成实时握手。`
      );
    }
    return (
      `Connect your Agent harness to the PaperForge global lightweight MCP server (**recommended: register in your harness's global MCP config** so it works across projects while staying silent on unrelated coding chats; **do NOT write \`.agents/\` or \`.mcp.json\` clutter into the user's Obsidian Vault root**):\n\n` +
      `### Verified Local Paths\n` +
      `- Vault path: \`${vaultBase}\`\n` +
      `- Stable MCP binary: \`${binPath}\`\n` +
      `- MCP args: \`["--mcp", "--vault", "${vaultBase}"]\`\n` +
      `- Optional Skill source: \`${skillHubDir}\`\n\n` +
      `### Execute these 2 steps and verify\n` +
      `1. **Register \`paperforge\` stdio MCP server globally** and non-destructively in your native config without overwriting existing servers. PaperForge auto-injects concise instructions and all 11 tools on handshake.\n` +
      `2. **Run handshake check**:\n   \`\`\`bash\n   ${checkCmd}\n   \`\`\`\n` +
      `   Confirm \`data.mcp_handshake_ok == true\`, then call \`paperforge_brief\` if hot-reload is active.`
    );
  }

  private _detectLocalVaultConfiguredPlatforms(vaultBase: string): string[] {
    if (!vaultBase) return [];
    const found: string[] = [];
    for (const [plat, rel] of [
      ["claude", ".mcp.json"],
      ["cursor", ".cursor/mcp.json"],
      ["opencode", "opencode.json"],
    ] as const) {
      if (this._getVaultMcpConfigStatus(vaultBase, plat) === "ready") {
        found.push(plat);
      } else {
        void rel;
      }
    }
    return found;
  }

  private _getEffectiveAgentPresence(): AgentPresenceSnapshotDto {
    const vaultBase = this._getVaultBasePath() || undefined;
    if (this._agentPresenceCache) {
      return this._agentPresenceCache;
    }
    if (typeof this.plugin.getAgentPresence === "function") {
      const fromPlugin = this.plugin.getAgentPresence() as
        | AgentPresenceSnapshotDto
        | null
        | undefined;
      if (fromPlugin && typeof fromPlugin === "object") {
        return fromPlugin;
      }
    }
    const localPlatforms = this._detectLocalVaultConfiguredPlatforms(
      vaultBase ?? ""
    );
    return normalizeAgentPresenceSnapshot({}, vaultBase, localPlatforms);
  }

  private _tryGetClient(): PaperForgeClient | null {
    try {
      return this.getClient();
    } catch {
      return null;
    }
  }

  private _refreshAgentPresenceOnce(): void {
    if (this._agentPresenceProbedThisSession) return;
    this._agentPresenceProbedThisSession = true;
    if (typeof this.plugin.refreshAgentPresence === "function") {
      void (
        this.plugin.refreshAgentPresence() as Promise<AgentPresenceSnapshotDto | null>
      )
        .then((next) => {
          if (next && typeof next === "object") {
            const prevSig = this._agentPresenceCache
              ? JSON.stringify(this._agentPresenceCache)
              : null;
            this._agentPresenceCache = next;
            if (prevSig !== JSON.stringify(next)) {
              this.refreshIfOpen();
            }
          }
        })
        .catch(() => undefined);
      return;
    }
    const client = this._tryGetClient();
    if (!client || typeof client.getAgentSessions !== "function") return;
    const vaultBase = this._getVaultBasePath() || undefined;
    void client
      .getAgentSessions(vaultBase)
      .then((next) => {
        if (!next || typeof next !== "object") return;
        const prevSig = this._agentPresenceCache
          ? JSON.stringify(this._agentPresenceCache)
          : null;
        this._agentPresenceCache = next;
        if (prevSig !== JSON.stringify(next)) {
          this.refreshIfOpen();
        }
      })
      .catch(() => undefined);
  }

  private _formatAgentPresenceBadgeText(
    presence: AgentPresenceSnapshotDto,
    includeTool = false
  ): string {
    const primary = presence.active_sessions[0];
    const clientName = primary
      ? formatAgentClientName(primary.client_name)
      : "";
    if (presence.state === "ready" && clientName) {
      const base = `${clientName} ${t("agent_state_ready")}`;
      if (includeTool && primary?.current_tool) {
        return `${base} · ${t("agent_running_tool").replace("{tool}", primary.current_tool)}`;
      }
      return base;
    }
    if (presence.state === "connected" && clientName) {
      const base = `${clientName} ${t("agent_state_connected")}`;
      if (includeTool && primary?.current_tool) {
        return `${base} · ${t("agent_running_tool").replace("{tool}", primary.current_tool)}`;
      }
      return base;
    }
    if (presence.state === "configured_idle") {
      if (presence.has_connected_before) {
        const lastRaw =
          presence.last_client_name || presence.historical_clients?.[0] || "";
        const lastLabel = lastRaw ? formatAgentClientName(lastRaw) : "AI Agent";
        return t("agent_state_standby").replace("{client}", lastLabel);
      }
      return t("agent_state_configured_idle");
    }
    return t("agent_state_unconnected");
  }

  private _renderAgentPresenceBadge(
    parent: HTMLElement,
    presence: AgentPresenceSnapshotDto,
    includeTool = false
  ): HTMLElement {
    const clsMap: Record<AgentPresenceSnapshotDto["state"], string> = {
      unconnected: "pf-agent-badge pf-agent-badge--unconnected",
      configured_idle: "pf-agent-badge pf-agent-badge--configured-idle",
      connected: "pf-agent-badge pf-agent-badge--connected",
      ready: "pf-agent-badge pf-agent-badge--ready",
    };
    const badge = parent.createEl("span", {
      cls: clsMap[presence.state],
      attr: {
        role: "status",
        "data-pf-testid": "agent-status-badge",
        "data-agent-state": presence.state,
      },
    });
    if (presence.state === "connected" || presence.state === "ready") {
      badge.createEl("span", {
        cls: "pf-agent-pulse-dot",
        attr: { "aria-hidden": "true" },
      });
    }
    badge.createEl("span", {
      cls: "pf-agent-badge-text",
      text: this._formatAgentPresenceBadgeText(presence, includeTool),
    });
    return badge;
  }

  private _getAgentPresenceSentence(
    presence: AgentPresenceSnapshotDto
  ): string {
    const primary = presence.active_sessions[0];
    if (presence.state === "ready" && primary) {
      const client = formatAgentClientName(primary.client_name);
      const base = t("agent_overview_ready_sentence").replace(
        "{client}",
        client
      );
      return primary.current_tool
        ? `${base} · ${t("agent_running_tool").replace("{tool}", primary.current_tool)}`
        : base;
    }
    if (presence.state === "connected" && primary) {
      const client = formatAgentClientName(primary.client_name);
      const base = t("agent_overview_connected_sentence").replace(
        "{client}",
        client
      );
      return primary.current_tool
        ? `${base} · ${t("agent_running_tool").replace("{tool}", primary.current_tool)}`
        : base;
    }
    if (presence.state === "configured_idle") {
      if (presence.has_connected_before) {
        const lastRaw =
          presence.last_client_name || presence.historical_clients?.[0] || "";
        const lastLabel = lastRaw ? formatAgentClientName(lastRaw) : "AI Agent";
        return t("agent_overview_standby_sentence").replace(
          "{client}",
          lastLabel
        );
      }
      const platforms =
        presence.configured_platforms &&
        presence.configured_platforms.length > 0
          ? presence.configured_platforms
              .map((p) => AGENT_PLATFORM_LABELS[p] ?? formatAgentClientName(p))
              .join(", ")
          : "MCP";
      return t("agent_overview_configured_idle_sentence").replace(
        "{platforms}",
        platforms
      );
    }
    return t("agent_overview_unconnected_sentence");
  }

  private _renderAgentOnboardingBox(
    parent: HTMLElement,
    vaultBase: string,
    currentPlatform: string,
    isZh: boolean
  ): void {
    const binPath = this._resolvePreferredDaemonBin(vaultBase);
    const hubInfo = this._readSkillHubAndInstallCount();
    const fallbackPrompt = this._buildLocalOnboardingPrompt(
      vaultBase,
      binPath,
      hubInfo.hubDir,
      isZh
    );

    const box = parent.createDiv({
      cls: "pf-agent-onboarding-box",
      attr: { "data-pf-testid": "agent-onboarding-box" },
    });
    box.createEl("p", {
      cls: "pf-agent-onboarding-hint",
      text: t("agent_onboarding_preview_hint"),
    });
    const preview = box.createEl("textarea", {
      cls: "pf-agent-prompt-preview",
      attr: {
        readonly: "true",
        rows: "7",
        "aria-label": t("agent_copy_onboarding_primary"),
        "data-pf-testid": "agent-onboarding-prompt-preview",
      },
    }) as HTMLTextAreaElement;
    preview.value = fallbackPrompt;

    const liveDaemon = resolveNativeDaemonBinary({
      vaultPath: vaultBase,
    });
    const client = this._tryGetClient();
    if (liveDaemon && client && typeof client.agentOnboarding === "function") {
      const langCode = isZh ? "zh" : "en";
      void client
        .agentOnboarding(langCode, binPath)
        .then((res) => {
          if (res?.prompt && preview.isConnected) {
            preview.value = res.prompt;
          }
        })
        .catch(() => undefined);
    }

    const primaryActions = box.createDiv({ cls: "pf-agent-config-actions" });
    const copyOnboardingBtn = renderActionButton(primaryActions, {
      label: t("agent_copy_onboarding_primary"),
      variant: "primary",
      onClick: () => {
        void (async () => {
          const cli = this.getClient();
          const curBinPath = this._resolvePreferredDaemonBin(vaultBase);
          const langCode = isZh ? "zh" : "en";
          if (!hubInfo.hubReady && typeof cli.skillSyncHub === "function") {
            try {
              await cli.skillSyncHub();
            } catch {
              // Best-effort Skill Hub hydration before generating onboarding prompt
            }
          }
          let promptText = preview.value || fallbackPrompt;
          const daemonBin = resolveNativeDaemonBinary({
            vaultPath: vaultBase,
          });
          if (daemonBin && typeof cli.agentOnboarding === "function") {
            try {
              const res = await cli.agentOnboarding(langCode, curBinPath);
              if (res?.prompt) {
                promptText = res.prompt;
                if (preview.isConnected) preview.value = promptText;
              }
            } catch {
              // Keep deterministic local prompt fallback
            }
          }
          try {
            await navigator.clipboard?.writeText(promptText);
            new Notice(t("agent_onboarding_copied"), 6000);
          } catch {
            new Notice(promptText, 8000);
          }
        })();
      },
    });
    copyOnboardingBtn.setAttribute(
      "data-pf-testid",
      "agent-copy-onboarding-btn"
    );
    renderActionButton(primaryActions, {
      label: t("agent_copy_mcp"),
      variant: "secondary",
      onClick: () => {
        void (async () => {
          const curBinPath = this._resolvePreferredDaemonBin(vaultBase);
          const fallback = this._buildLocalMcpConfig(
            vaultBase,
            currentPlatform,
            curBinPath
          );
          let copyText = fallback.text;
          let fileLabel = fallback.targetRel;
          const daemonBin = resolveNativeDaemonBinary({
            vaultPath: vaultBase,
          });
          if (daemonBin && typeof this.getClient().mcpConfig === "function") {
            try {
              const res = await this.getClient().mcpConfig(
                currentPlatform,
                curBinPath
              );
              copyText =
                res.toml_snippet || JSON.stringify(res.config_snippet, null, 2);
              fileLabel = res.target_relpath || fallback.targetRel;
            } catch {
              // Keep local snippet fallback
            }
          }
          try {
            await navigator.clipboard?.writeText(copyText);
            new Notice(t("agent_mcp_copied").replace("{file}", fileLabel));
          } catch {
            new Notice(copyText, 8000);
          }
        })();
      },
    });
  }

  _renderAgentDetail(containerEl: HTMLElement, opts?: InlineRenderOpts): void {
    if (!opts?.inline) {
      this._renderModuleDetailShell(containerEl, "agent");
    }
    this._refreshAgentPresenceOnce();
    const body = containerEl.createDiv({ cls: "pf-module-body" });

    const current = this.plugin.settings.agent_platform || "opencode";
    const vaultBase = this._getVaultBasePath();
    const installedBin = this._resolvePreferredDaemonBin(vaultBase);
    const binReady = fs.existsSync(installedBin);
    const hubInfo = this._readSkillHubAndInstallCount();
    const isZh = (
      this.plugin.settings.language || langFromApp(this.app)
    ).startsWith("zh");
    const presence = this._getEffectiveAgentPresence();
    const primarySession = presence.active_sessions[0];

    // ── Live 4-State Poki Presence Card ──
    const presenceCard = body.createDiv({
      cls: "pf-agent-presence-card",
      attr: {
        "data-pf-testid": "agent-presence-card",
        "data-agent-state": presence.state,
      },
    });
    const presenceHead = presenceCard.createDiv({
      cls: "pf-agent-presence-head",
    });
    this._renderAgentPresenceBadge(presenceHead, presence, false);

    if (
      (presence.state === "connected" || presence.state === "ready") &&
      primarySession
    ) {
      const clientLabel = formatAgentClientName(primarySession.client_name);
      const metaParts = [clientLabel];
      if (primarySession.client_version) {
        metaParts.push(`v${primarySession.client_version}`);
      }
      if (presence.total_active > 1) {
        metaParts.push(
          isZh
            ? `共 ${presence.total_active} 个在线会话`
            : `${presence.total_active} active sessions`
        );
      }
      presenceHead.createEl("span", {
        cls: "pf-agent-presence-meta",
        text: metaParts.join(" · "),
      });
      if (primarySession.current_tool) {
        const toolEl = presenceCard.createDiv({
          cls: "pf-agent-tool-activity",
          attr: { "data-pf-testid": "agent-live-tool" },
        });
        toolEl.createEl("span", {
          cls: "pf-agent-pulse-dot",
          attr: { "aria-hidden": "true" },
        });
        toolEl.createEl("span", {
          text: t("agent_running_tool").replace(
            "{tool}",
            primarySession.current_tool
          ),
        });
      }
      if (presence.active_sessions.length > 1) {
        const sessionList = presenceCard.createDiv({
          cls: "pf-agent-sessions-list",
        });
        sessionList.createEl("div", {
          cls: "pf-agent-sessions-title",
          text: t("agent_active_sessions_title"),
        });
        for (const sess of presence.active_sessions) {
          const row = sessionList.createDiv({ cls: "pf-agent-session-row" });
          const name = formatAgentClientName(sess.client_name);
          const ver = sess.client_version ? ` v${sess.client_version}` : "";
          const tool = sess.current_tool
            ? ` · ${t("agent_running_tool").replace("{tool}", sess.current_tool)}`
            : "";
          row.createEl("span", { text: `● ${name}${ver}${tool}` });
        }
      }
    } else if (presence.state === "configured_idle") {
      const platforms =
        presence.configured_platforms &&
        presence.configured_platforms.length > 0
          ? presence.configured_platforms
              .map((p) => AGENT_PLATFORM_LABELS[p] ?? formatAgentClientName(p))
              .join(", ")
          : "MCP";
      presenceCard.createEl("p", {
        cls: "pf-agent-presence-sub",
        text: t("agent_configured_waiting_hint").replace(
          "{platforms}",
          platforms
        ),
      });
    } else {
      presenceCard.createEl("p", {
        cls: "pf-agent-presence-sub",
        text: this._getAgentPresenceSentence(presence),
      });
    }

    // ── Live Auto-Setup Progress Checklist (4 rows) ──
    const checklistState = presence.setup_checklist ?? {
      connected: false,
      instructions_injected: false,
      vault_reconciled: false,
      tools_ready: false,
    };
    const checklistCard = body.createDiv({
      cls: "pf-agent-checklist",
      attr: { "data-pf-testid": "agent-setup-checklist" },
    });
    checklistCard.createEl("div", {
      cls: "pf-agent-checklist-title",
      text: t("agent_checklist_title"),
    });
    const handshakeDetail =
      checklistState.connected && primarySession
        ? `${formatAgentClientName(primarySession.client_name)}${
            primarySession.client_version
              ? ` v${primarySession.client_version}`
              : ""
          }`
        : t("agent_check_1_waiting");
    const checklistRows: Array<{
      id: string;
      done: boolean;
      label: string;
      detail?: string;
    }> = [
      {
        id: "agent-check-1",
        done: Boolean(checklistState.connected),
        label: t("agent_check_1_handshake"),
        detail: handshakeDetail,
      },
      {
        id: "agent-check-2",
        done: Boolean(checklistState.instructions_injected),
        label: t("agent_check_2_instructions"),
      },
      {
        id: "agent-check-3",
        done: Boolean(checklistState.vault_reconciled),
        label: t("agent_check_3_reconciled"),
      },
      {
        id: "agent-check-4",
        done: Boolean(checklistState.tools_ready),
        label: t("agent_check_4_tools"),
      },
    ];
    for (const item of checklistRows) {
      const row = checklistCard.createDiv({
        cls: `pf-agent-check-item ${
          item.done
            ? "pf-agent-check-item--done"
            : "pf-agent-check-item--pending"
        }`,
        attr: {
          "data-pf-testid": item.id,
          "data-checked": item.done ? "true" : "false",
        },
      });
      row.createEl("span", {
        cls: "pf-agent-check-icon",
        text: item.done ? "✓" : "○",
        attr: { "aria-hidden": "true" },
      });
      const textWrap = row.createDiv({ cls: "pf-agent-check-text" });
      textWrap.createEl("span", {
        cls: "pf-agent-check-label",
        text: item.label,
      });
      if (item.detail) {
        textWrap.createEl("span", {
          cls: "pf-agent-check-detail",
          text: item.detail,
        });
      }
    }

    body.createEl("p", {
      cls: "caption",
      text: t("agent_external_cli_hint"),
    });

    if (presence.state === "connected" || presence.state === "ready") {
      const connectMoreDetails = body.createEl("details", {
        cls: "pf-adv-details",
      });
      connectMoreDetails.createEl("summary", {
        text: t("agent_connect_another"),
      });
      const connectMoreBody = connectMoreDetails.createDiv({
        cls: "pf-adv-body",
      });
      this._renderAgentOnboardingBox(connectMoreBody, vaultBase, current, isZh);
    } else {
      this._renderAgentOnboardingBox(body, vaultBase, current, isZh);
    }

    const facts = body.createDiv({ cls: "pf-module-facts" });
    const binFact = facts.createDiv({ cls: "pf-module-fact" });
    binFact.createEl("span", { text: t("agent_mcp_bin_label") });
    binFact.createEl("span", {
      text: binReady ? t("agent_mcp_bin_ready") : t("agent_mcp_bin_missing"),
    });

    const hubFact = facts.createDiv({ cls: "pf-module-fact" });
    hubFact.createEl("span", { text: t("agent_skill_hub_label") });
    hubFact.createEl("span", {
      text:
        presence.total_active > 0
          ? t("agent_skill_hub_ready").replace(
              "{count}",
              String(presence.total_active)
            )
          : hubInfo.installCount > 0
            ? t("agent_skill_hub_ready").replace(
                "{count}",
                String(hubInfo.installCount)
              )
            : hubInfo.hubReady
              ? t("agent_skill_hub_unconnected")
              : t("agent_skill_hub_pending"),
    });

    const vaultSkillDirs = [
      path.join(
        vaultBase,
        AGENT_PLATFORM_SKILL_DIRS[current] ?? ".agents/skills"
      ),
      path.join(vaultBase, ".agents/skills"),
    ];
    const hasVaultSkills = vaultSkillDirs.some((dir) => {
      if (!fs.existsSync(dir)) return false;
      try {
        return fs
          .readdirSync(dir, { withFileTypes: true })
          .some(
            (entry) =>
              entry.isDirectory() &&
              fs.existsSync(path.join(dir, entry.name, "SKILL.md"))
          );
      } catch {
        return false;
      }
    });
    if (hasVaultSkills) {
      const skillsDetails = body.createEl("details", {
        cls: "pf-adv-details",
      });
      skillsDetails.createEl("summary", { text: t("md_agent_skills") });
      const skillsBody = skillsDetails.createDiv({ cls: "pf-adv-body" });
      this._renderSkillsList(skillsBody);
    }
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
  _renderMemoryDetail(containerEl: HTMLElement, opts?: InlineRenderOpts): void {
    if (!opts?.inline) {
      this._renderModuleDetailShell(containerEl, "memory", false);
    }
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

    const isZhMem = t("nav_close") === "关闭";
    // Preset selector at top of Memory config (class pf-sr-cfg-select preserves .pf-sr-cfg-input count = 3)
    const presetRow = cfgBody.createDiv({ cls: "pf-sr-cfg-row" });
    presetRow.createEl("label", {
      text: t("settings_provider_preset"),
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
        text: isZhMem ? p.labelZh : p.labelEn,
        attr: { value: p.id },
      });
      opt.selected = p.id === curPreset;
    }
    const srMetaBar = presetRow.createDiv({ cls: "pf-embed-meta-bar" });
    const srTraitEl = srMetaBar.createEl("span", { cls: "pf-embed-trait" });
    const srSignupLink = srMetaBar.createEl("a", {
      cls: "pf-express-help-link",
      attr: { target: "_blank", rel: "noopener noreferrer" },
    });
    const syncSrPresetMeta = (presetId: string) => {
      const pr =
        EMBEDDING_PRESETS.find((p) => p.id === presetId) ??
        EMBEDDING_PRESETS[0];
      srTraitEl.setText(isZhMem ? pr.traitZh : pr.traitEn);
      if (pr.signupUrl) {
        srSignupLink.style.display = "";
        srSignupLink.setAttr("href", pr.signupUrl);
        srSignupLink.setText(
          isZhMem
            ? `获取 ${pr.shortLabelZh.split(" ·")[0]} 密钥 ↗`
            : `Get ${pr.shortLabelEn.split(" ·")[0]} key ↗`
        );
      } else {
        srSignupLink.style.display = "none";
      }
    };
    syncSrPresetMeta(curPreset);

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
        placeholder: "https://api.siliconflow.cn/v1",
      },
    }) as HTMLInputElement;
    bi.value = this.plugin.settings.vector_db_api_base || "";
    bi.addEventListener("change", () => {
      this._setVectorDbConfig("vector_db_api_base", bi);
    });

    const hasExistingVectors =
      env.user_state === "ready" ||
      Number(panelDetails.paper_count_index ?? 0) > 0;
    const initialModelVal =
      this.plugin.settings.vector_db_api_model || "text-embedding-3-small";
    const rebuildWarnEl = cfgBody.createEl("p", {
      cls: "pf-embed-inline-hint",
      text: isZhMem
        ? "提示：更换向量模型后，下次检索前点击上方「重建索引」即可对齐语义空间（不影响笔记和 OCR）。"
        : "Note: After switching models, rebuild the vector index once (notes & OCR stay untouched).",
    });
    rebuildWarnEl.style.display = "none";

    // Model + on-demand model list probe
    const mr = cfgBody.createDiv({ cls: "pf-sr-cfg-row" });
    mr.createEl("label", {
      text: t("feat_api_model") || "Model",
      cls: "pf-sr-cfg-lbl",
    });
    const mrRow = mr.createDiv({ cls: "pf-embed-model-row" });
    const mi = mrRow.createEl("input", {
      cls: "pf-sr-cfg-input",
      attr: {
        type: "text",
        "data-pf-testid": "sr-api-model-input",
        placeholder: "BAAI/bge-m3",
      },
    }) as HTMLInputElement;
    mi.value = initialModelVal;
    mi.addEventListener("change", () => {
      this._setVectorDbConfig("vector_db_api_model", mi);
      if (hasExistingVectors && mi.value.trim() !== initialModelVal) {
        rebuildWarnEl.style.display = "";
      }
    });
    const srFetchBtn = mrRow.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: isZhMem ? "拉取模型" : "Fetch models",
      attr: { type: "button", "data-pf-testid": "sr-fetch-models-btn" },
    });
    const srFetchedSlot = mr.createDiv({ cls: "pf-embed-fetched-chips" });
    srFetchedSlot.style.display = "none";
    srFetchBtn.addEventListener("click", () => {
      srFetchBtn.disabled = true;
      srFetchedSlot.style.display = "flex";
      srFetchedSlot.textContent = isZhMem ? "正在探测…" : "Probing…";
      void this.getClient()
        .embedListModels(bi.value.trim() || undefined)
        .then((res) => {
          srFetchedSlot.textContent = "";
          const picks =
            res.embedding_models.length > 0 ? res.embedding_models : res.models;
          if (!res.reachable || picks.length === 0) {
            srFetchedSlot.createEl("span", {
              cls: "pf-embed-inline-hint",
              text: isZhMem
                ? "未拉取到向量模型列表，可直接手填模型名。"
                : "No model list returned; enter model name manually.",
            });
            return;
          }
          for (const id of picks.slice(0, 8)) {
            const c = srFetchedSlot.createEl("button", {
              cls: `pf-express-preset-chip${mi.value.trim() === id ? " is-active" : ""}`,
              text: id,
              attr: { type: "button" },
            });
            c.addEventListener("click", () => {
              mi.value = id;
              this._setVectorDbConfig("vector_db_api_model", mi);
              if (hasExistingVectors && id !== initialModelVal) {
                rebuildWarnEl.style.display = "";
              }
            });
          }
        })
        .catch(() => {
          srFetchedSlot.textContent = "";
          srFetchedSlot.createEl("span", {
            cls: "pf-embed-inline-hint",
            text: isZhMem
              ? "探测失败，可手填模型名。"
              : "Probe failed; enter manually.",
          });
        })
        .finally(() => {
          srFetchBtn.disabled = false;
        });
    });

    presetSel.addEventListener("change", () => {
      syncSrPresetMeta(presetSel.value);
      const picked = EMBEDDING_PRESETS.find((p) => p.id === presetSel.value);
      if (!picked || picked.id === "custom") return;
      bi.value = picked.baseUrl;
      mi.value = picked.model;
      this._setVectorDbConfig("vector_db_api_base", bi);
      this._setVectorDbConfig("vector_db_api_model", mi);
      if (hasExistingVectors && picked.model !== initialModelVal) {
        rebuildWarnEl.style.display = "";
      }
    });

    // Live connectivity & vector dimension check right in the panel
    const testRow = cfgBody.createDiv({
      cls: "pf-sr-cfg-row pf-test-conn-row",
    });
    const testBtn = testRow.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: t("settings_test_embed_btn"),
      attr: { type: "button", "data-pf-testid": "sr-test-conn-btn" },
    });
    const testOut = testRow.createEl("span", {
      cls: "pf-test-conn-status",
      text: "",
    });
    testBtn.addEventListener("click", () => {
      const isZhNow = getActiveLang(this.app) === "zh";
      testBtn.disabled = true;
      testOut.textContent = t("settings_probing");
      void this.getClient()
        .embedTestConnection()
        .then((res) => {
          testOut.className = "pf-test-conn-status is-ok";
          testOut.textContent =
            "✓ " +
            t("settings_embed_connected")
              .replace("{model}", String(res.model))
              .replace("{dim}", String(res.dimension))
              .replace("{ms}", String(res.latency_ms));
        })
        .catch((err) => {
          testOut.className = "pf-test-conn-status is-err";
          testOut.textContent =
            "✗ " +
            formatProviderConnectionError(
              String(err?.message || err),
              "embed",
              isZhNow
            );
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
      text: t("settings_adv_api_mode"),
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
        btn.setButtonText(t("dash_btn_clear")).onClick(() => {
          clearTrace();
          new Notice(t("settings_trace_cleared"));
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
              if (
                event.status === "succeeded" ||
                event.status === "noop" ||
                event.status === "done" ||
                event.status === "done_degraded" ||
                event.status === "ok"
              ) {
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
          const base =
            failed || (payloadReason ? formatHumanError(payloadReason) : "");
          const detail =
            skippedCount > 0
              ? `${base ? base + " " : ""}(${skippedCount} skipped)`
              : base ||
                formatHumanError(
                  `exit code ${result.exitCode}`,
                  "ocr_error_notice"
                );
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
            formatHumanError(err, "ocr_error_notice"),
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

    const topNav = containerEl.createDiv({ cls: "pf-module-detail-nav" });
    const backBtn = topNav.createEl("button", {
      cls: "pf-back-btn",
      text: t("btn_back_to_overview"),
      attr: { type: "button" },
    });
    backBtn.addEventListener("click", () => {
      if (this._detailReturn) {
        this.activeTab = this._detailReturn.tab;
        this._focusTargetId = this._detailReturn.selector;
        this._detailReturn = null;
      } else {
        this.activeTab = "overview";
        this._focusTargetId = `.pf-open-module-btn[data-module="${mod}"]`;
      }
      this._selectedDetailModule = "";
      this.display();
    });

    const detailModules = this._getOverviewModules();
    const selector = topNav.createDiv({
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
    if (mod === "agent") {
      const presence = this._getEffectiveAgentPresence();
      this._renderAgentPresenceBadge(header, presence, true);
      summary.createEl("p", {
        cls: "pf-module-summary-consequence",
        text: this._getAgentPresenceSentence(presence),
      });
    } else {
      renderStatusBadge(header, userState, this._getUserStateLabel(userState));
      summary.createEl("p", {
        cls: "pf-module-summary-consequence",
        text: this._getModuleConsequence(mod, env),
      });
    }

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
    if (this.plugin?.settings?.language) {
      setLanguage(this.app, this.plugin.settings.language);
    }
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
    // Developer UI Gallery moved out of Appearance into Help -> Developer Tools
    const isZhHelp = t("nav_close") === "关闭";
    const devDetails = containerEl.createEl("details", {
      cls: "pf-help-section pf-help-dev-details",
      attr: { "data-pf-testid": "help-developer-tools" },
    });
    devDetails.createEl("summary", {
      cls: "pf-help-section-title",
      text: isZhHelp
        ? "开发者与界面调试（UI 组件画廊）"
        : "Developer & UI Debugging",
    });
    const devBody = devDetails.createDiv({ cls: "pf-help-section-body" });
    const devRow = devBody.createDiv({ cls: "pf-cc-theme-bar" });
    const devCopy = devRow.createDiv({ cls: "pf-cc-theme-copy" });
    devCopy.createEl("div", {
      cls: "pf-cc-theme-label",
      text: t("settings_gallery_label"),
    });
    devCopy.createEl("div", {
      cls: "pf-cc-theme-desc",
      text: t("settings_gallery_desc"),
    });
    const galleryBtn = devRow.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: t("settings_gallery_btn"),
      attr: { type: "button", "data-pf-testid": "settings-open-gallery" },
    });
    galleryBtn.addEventListener("click", () => {
      void (
        this.plugin as unknown as { openUiGallery?: () => Promise<void> }
      ).openUiGallery?.();
    });

    // Support & Diagnostics section is always rendered locally BEFORE remote doc fetch
    // so users offline or behind firewalls never lose Copy Support Diagnostic (PF-UI-004).
    const supportCard = containerEl.createEl("details", {
      cls: "pf-help-section pf-help-support-card",
      attr: { open: "true", "data-pf-testid": "help-support-section" },
    });
    supportCard.createEl("summary", {
      cls: "pf-help-section-title",
      text: t("help_support") || "Support & Diagnostics",
    });
    const supportBody = supportCard.createDiv({ cls: "pf-help-section-body" });
    supportBody.createEl("p", {
      cls: "setting-item-description",
      text:
        t("help_support_desc") ||
        "Copies module state and versions only; excludes keys, notes, and paths.",
    });
    const supportActions = supportBody.createDiv({
      cls: "pf-help-support-actions",
    });
    supportActions
      .createEl("button", {
        cls: "pf-btn pf-btn-primary pf-help-diagnostic-btn",
        text: t("help_copy") || "Copy Support Diagnostic",
        attr: { type: "button", "data-pf-testid": "help-copy-diagnostic" },
      })
      .addEventListener("click", () => this._buildAndCopyDiagnostic());
    const manualBtn = supportActions.createEl("a", {
      cls: "pf-btn pf-btn-secondary pf-help-manual-link",
      text:
        t("settings_manual_link") ||
        t("help_open_documentation") ||
        "Open Documentation",
      href: "https://github.com/LLLin000/PaperForge/blob/master/docs/user-manual.md",
    });
    manualBtn.setAttr("target", "_blank");
    manualBtn.setAttr("rel", "noopener noreferrer");

    // Loading indicator for live online docs
    const loading = containerEl.createEl("p", {
      cls: "pf-help-loading",
      text:
        getActiveLang(this.app) === "zh"
          ? "正在加载在线帮助文档…"
          : "Loading help content\u2026",
    });

    const lang = getActiveLang(this.app);
    const base =
      "https://api.github.com/repos/LLLin000/PaperForge/contents/docs/help";
    const files = ["guide", "faq", "support"];
    const self = this;
    const docsHost = containerEl.createDiv({ cls: "pf-help-docs-host" });

    const fetchHelpDoc = async (url: string): Promise<{ content: string }> => {
      if (typeof requestUrl === "function") {
        const res = await requestUrl({ url });
        if (!res || (typeof res.status === "number" && res.status >= 400)) {
          throw new Error(`HTTP ${res?.status ?? "error"}`);
        }
        if (
          res.json &&
          typeof (res.json as { content?: unknown }).content === "string"
        ) {
          return res.json as { content: string };
        }
        if (typeof res.text === "string" && res.text.trim()) {
          return JSON.parse(res.text) as { content: string };
        }
        throw new Error("Empty help response");
      }
      if (typeof fetch === "function") {
        const r = await fetch(url);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return (await r.json()) as { content: string };
      }
      throw new Error("No HTTP client available");
    };

    Promise.all(
      files.map((f) =>
        fetchHelpDoc(`${base}/${lang}/${f}.md`)
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
        if (loading.parentElement !== containerEl) return;
        loading.remove();
        let renderedCount = 0;
        for (const { name, text } of results) {
          if (!text) continue;
          renderedCount++;
          const titleMatch = text.match(/^#\s+(.+)/m);
          const title = titleMatch ? titleMatch[1] : name;
          const body = text.replace(/^#\s+.+(\r?\n|$)/, "").trim();

          const section = docsHost.createEl("details", {
            cls: "pf-help-section",
          });
          section.createEl("summary", {
            cls: "pf-help-section-title",
            text: title,
          });
          const bodyEl = section.createDiv({ cls: "pf-help-section-body" });
          MarkdownRenderer.render(
            self.app,
            body,
            bodyEl,
            "",
            self.plugin as unknown as Component
          );
        }
        if (renderedCount === 0) {
          const errBox = docsHost.createDiv({
            cls: "pf-help-load-error",
            attr: { "data-pf-testid": "help-offline-fallback" },
          });
          errBox.createEl("p", {
            cls: "pf-help-error-title",
            text: t("help_load_error") || "Failed to load help content.",
          });
          errBox.createEl("p", {
            cls: "setting-item-description",
            text:
              t("help_offline_manual_note") ||
              "Online documentation could not be loaded. Use Copy Support Diagnostic above or open the user manual directly.",
          });
        }
      })
      .catch(() => {
        if (loading.parentElement !== containerEl) return;
        loading.setText(t("help_load_error") || "Failed to load help content.");
      });
  }

  _runManualSync() {
    if (this._libraryRunning || this.plugin._autoSyncRunning) {
      new Notice(t("settings_sync_already_running"), 4000);
      this.display();
      return;
    }
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

    const pluginCtl = this.plugin as unknown as {
      clearLastAutoSyncError?: () => void;
      setManualSyncActive?: (active: boolean) => void;
      _emitStateChanged?: () => void;
      refreshBaseSnapshot?: () => Promise<unknown>;
    };
    pluginCtl.clearLastAutoSyncError?.();
    if (typeof pluginCtl.setManualSyncActive === "function") {
      pluginCtl.setManualSyncActive(true);
    } else {
      this.plugin._autoSyncRunning = true;
      pluginCtl._emitStateChanged?.();
    }
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
          pluginCtl.clearLastAutoSyncError?.();
          void pluginCtl.refreshBaseSnapshot?.().catch(() => undefined);
          new Notice(t("settings_sync_complete"), 4000);
          // #127: consume backend next_actions. Automatic local work starts
          // now; consent-required work remains visible in the module card.
          void orchestrateFromSync(JSON.stringify(result), {
            runAction: (req) => client.runAction(req),
            silentPending: true,
          });
        } else {
          const errMsg = (
            result as { error?: { message?: string } } | null | undefined
          )?.error?.message;
          new Notice(
            t("settings_sync_failed").replace(
              "{detail}",
              formatHumanError(errMsg || "sync_failed")
            ),
            8000
          );
        }
      } catch (err: unknown) {
        new Notice(
          t("settings_sync_failed").replace("{detail}", formatHumanError(err)),
          8000
        );
      } finally {
        if (typeof pluginCtl.setManualSyncActive === "function") {
          pluginCtl.setManualSyncActive(false);
        } else {
          this.plugin._autoSyncRunning = false;
          pluginCtl._emitStateChanged?.();
        }
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
    containerEl.createEl("h2", { text: t("tab_help") || "Help & Changelog" });

    containerEl.createEl("h3", {
      text: t("settings_changelog_heading"),
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
          text: t("main_release_recommended"),
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
          text: t("main_release_new_features"),
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
          text: t("main_release_fixes"),
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
          text: t("main_release_recommended"),
        });
        for (const item of ver.recommended_actions) {
          section.createEl("div", {
            cls: "paperforge-release-item paperforge-release-item-bold",
            text: `\u2022 ${item}`,
          });
        }
      }
    }

    containerEl.createEl("h3", { text: t("settings_manual_heading") });
    const manualSection = containerEl.createEl("div", {
      cls: "paperforge-manual-links",
    });
    const manualLink = manualSection.createEl("a", {
      text: t("settings_manual_link"),
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
    const appAny = this.app as unknown as {
      loadLocalStorage?: (k: string) => unknown;
    };
    let localStored: unknown = null;
    if (typeof appAny?.loadLocalStorage === "function") {
      try {
        localStored = appAny.loadLocalStorage("paperforge:capability-state");
      } catch {
        localStored = null;
      }
    }
    const stored = (
      localStored && typeof localStored === "object"
        ? localStored
        : (this.plugin.settings.capabilityState ?? {})
    ) as Record<string, unknown>;
    const validated = validatePersistedEnvelopes(
      stored,
      CAPABILITY_MODULES as unknown as string[]
    );
    // Keep last valid state visible across TTL expiration (Stale-While-Revalidate)
    // and silently verify in background rather than flashing "Checking..." on every open.
    for (const mod of CAPABILITY_MODULES) {
      const raw = stored[mod];
      if (
        raw &&
        typeof raw === "object" &&
        isValidEnvelope(raw, mod) &&
        isEnvelopeStale(raw as ProbeEnvelope) &&
        (raw as ProbeEnvelope).user_state !== "checking"
      ) {
        validated[mod] = raw as ProbeEnvelope;
        this._staleModulesNeedingSilentRefresh.add(mod);
      }
    }
    this._capabilityState = validated;
    this._persistCapabilityState();
  }

  /** Persist capability state to localStorage when available, else plugin settings (skips write when unchanged). */
  _persistCapabilityState(): void {
    if (!this._capabilityState) return;
    const serialized = JSON.stringify(this._capabilityState);
    if (serialized === this._lastPersistedCapJson) return;
    this._lastPersistedCapJson = serialized;
    const appAny = this.app as unknown as {
      saveLocalStorage?: (k: string, v: unknown) => void;
    };
    if (typeof appAny?.saveLocalStorage === "function") {
      try {
        appAny.saveLocalStorage(
          "paperforge:capability-state",
          this._capabilityState
        );
        return;
      } catch {
        // Fall through to settings fallback
      }
    }
    this.plugin.settings.capabilityState = this._capabilityState;
    this.plugin.saveSettings();
  }

  /** Call `paperforge probe <module> --json` and store the validated envelope unchanged. */
  _probeModule(
    mod: CapabilityModule,
    lastOperationExitCode?: number,
    opts?: { silent?: boolean }
  ): void {
    if (this._probing.has(mod)) return;
    this._probing.add(mod);

    if (!opts?.silent) {
      // Show probing state immediately for explicit user-triggered / first-run checks
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
    }

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

  /**
   * Unified 1-Screen Control Center:
   * - Merges runtime & library into one core row (zero sub-page jumping)
   * - Inline accordion expansion for Library / OCR / Smart Retrieval / Agent
   * - Keeps deep-link _handleCardNavigation + _render*Detail API compatibility.
   */
  _renderControlCenter(containerEl: HTMLElement): void {
    if (this.plugin?.settings?.language) {
      setLanguage(this.app, this.plugin.settings.language);
    }
    const cc = containerEl.createEl("div", { cls: "pf-control-center" });
    const envelopes: Record<string, ProbeEnvelope> =
      this._capabilityState ?? {};
    const isZh = getActiveLang(this.app) === "zh";

    // ── Single Deterministic Decision-Tree Hero Card ──
    const runtimePtr = readRuntimePointer();
    let foundationEnv =
      envelopes["installation"] ?? createUnknownEnvelope("installation");
    if (!runtimePtr && foundationEnv.user_state === "ready") {
      foundationEnv = this._setupRequiredEnvelope();
    }
    const libraryEnv = envelopes["library"] ?? createUnknownEnvelope("library");
    const pfState = this.plugin as unknown as {
      isDaemonUpdating?: () => boolean;
      isRuntimeUpdating?: () => boolean;
      isSyncing?: () => boolean;
      getLiveTaskSummary?: (kind: "runtime" | "sync") => {
        phaseText: string;
        current: number;
        total: number;
        startedAt: number | null;
      } | null;
      getQuarantinedBinDir?: () => string | null;
      dismissQuarantineBanner?: () => void;
      getLastAutoSyncError?: () => { message: string; at: number } | null;
      getUpgradePlanCache?: () => import("./client").VaultUpgradePlanDto | null;
      isUpgradeBannerDismissed?: () => boolean;
      openUpgradeModal?: () => Promise<void>;
      dismissUpgradeBannerForSession?: () => void;
    };
    const expectedVersion = this.plugin.manifest?.version ?? "";
    const paperCountRaw = (
      libraryEnv.details as Record<string, unknown> | undefined
    )?.["paper_count"];
    const runtimeActive =
      Boolean(pfState.isRuntimeUpdating?.()) || Boolean(this._runtimePollTimer);
    const syncActive = Boolean(
      this._libraryRunning ||
      this.plugin._autoSyncRunning ||
      pfState.isSyncing?.()
    );
    const runtimeSummary = runtimeActive
      ? (pfState.getLiveTaskSummary?.("runtime") ?? null)
      : null;
    const syncSummary = syncActive
      ? (pfState.getLiveTaskSummary?.("sync") ?? null)
      : null;
    const activeSummary = runtimeActive ? runtimeSummary : syncSummary;
    const engineUpdateDetail = runtimeActive
      ? runtimeSummary?.phaseText || this._installerProgressLine() || null
      : null;
    const activeStartedAt = activeSummary?.startedAt ?? null;
    const elapsedText = activeStartedAt
      ? t("live_elapsed_running").replace(
          "{elapsed}",
          formatElapsedDuration(activeStartedAt)
        )
      : null;
    const decision = resolveSetupDecision({
      daemonUpdating: Boolean(pfState.isDaemonUpdating?.()),
      runtimeUpdating: runtimeActive,
      canCancelInstall: Boolean(this._runtimePollTimer),
      quarantinedBinDir: pfState.getQuarantinedBinDir?.() ?? null,
      upgradePlan: pfState.getUpgradePlanCache?.() ?? null,
      upgradeBannerDismissed: Boolean(pfState.isUpgradeBannerDismissed?.()),
      runtimePointer: runtimePtr,
      expectedVersion,
      minEngineVersion: this._minEngineVersion(),
      installationEnv: foundationEnv,
      libraryEnv,
      isProbing: this._probing.size > 0,
      zoteroDataDir: this.plugin.settings.zotero_data_dir || "",
      zoteroDetectedPapers: this._zoteroDetectData?.found
        ? this._zoteroDetectData.total_papers
        : null,
      lastAutoSyncError: pfState.getLastAutoSyncError?.()?.message ?? null,
      paperCount: typeof paperCountRaw === "number" ? paperCountRaw : null,
      librarySyncing: syncActive,
      engineUpdateDetail,
      syncDetail: syncSummary?.phaseText || null,
      progressCurrent: activeSummary?.current,
      progressTotal: activeSummary?.total,
      progressElapsedText: elapsedText,
    });

    const summaryEl = cc.createEl("div", {
      cls: "pf-cc-summary",
      attr: { "data-pf-decision": decision.id },
    });
    summaryEl.createEl("span", {
      cls: `pf-cc-summary-badge pf-cc-summary-badge--${decision.badgeCls}`,
      text: decision.badgeText,
    });

    const summaryCopy = summaryEl.createDiv({ cls: "pf-cc-summary-copy" });
    summaryCopy.createEl("strong", { text: decision.title });
    summaryCopy.createEl("span", { cls: "caption", text: decision.body });
    if (decision.progress) {
      const pWrap = summaryCopy.createDiv({ cls: "pf-cc-progress-wrap" });
      const bar = pWrap.createDiv({ cls: "pf-runtime-stage-bar" });
      const fill = bar.createDiv({ cls: "pf-runtime-stage-fill" });
      if (decision.progress.current > 0 && decision.progress.total > 0) {
        const pct = Math.max(
          12,
          Math.min(
            100,
            Math.round(
              (decision.progress.current / decision.progress.total) * 100
            )
          )
        );
        fill.style.width = `${pct}%`;
      } else {
        fill.classList.add("is-indeterminate");
      }
      const metaRow = pWrap.createDiv({ cls: "pf-cc-progress-meta" });
      metaRow.createEl("span", {
        text: decision.progress.detail || "",
      });
      const elSpan = metaRow.createEl("span", {
        text: decision.progress.elapsed || "",
      });
      this._liveElapsedEl = elSpan;
      this._liveElapsedStartedAt = activeStartedAt;
      if (this._isOpen && !this._liveActivityTimer && activeStartedAt) {
        this._liveActivityTimer = setInterval(() => {
          if (
            !this._isOpen ||
            !this._liveElapsedEl ||
            !this._liveElapsedEl.isConnected ||
            !this._liveElapsedStartedAt
          ) {
            if (this._liveActivityTimer) {
              clearInterval(this._liveActivityTimer);
              this._liveActivityTimer = null;
            }
            return;
          }
          this._liveElapsedEl.textContent = t("live_elapsed_running").replace(
            "{elapsed}",
            formatElapsedDuration(this._liveElapsedStartedAt)
          );
        }, 1000);
      }
    } else {
      this._liveElapsedEl = null;
      this._liveElapsedStartedAt = null;
      if (this._liveActivityTimer) {
        clearInterval(this._liveActivityTimer);
        this._liveActivityTimer = null;
      }
    }
    if (decision.codeBlock) {
      summaryCopy.createEl("code", {
        cls: "pf-defender-path-code",
        text: decision.codeBlock,
      });
    }

    const runDecisionAction = (kind: string): void => {
      switch (kind) {
        case "cancel_install":
          this._cancelRuntimePoll();
          break;
        case "copy_quarantine_path":
          if (decision.codeBlock) {
            void navigator.clipboard
              ?.writeText?.(decision.codeBlock)
              .then(() => {
                new Notice(t("main_defender_path_copied"));
              });
          }
          break;
        case "dismiss_quarantine":
          pfState.dismissQuarantineBanner?.();
          break;
        case "open_vault_upgrade":
          void pfState.openUpgradeModal?.();
          break;
        case "dismiss_vault_upgrade":
          pfState.dismissUpgradeBannerForSession?.();
          this.display();
          break;
        case "start_setup_step1":
          this._startSetupJourney(1);
          break;
        case "update_engine":
          this._triggerRuntimeUpgrade();
          break;
        case "refresh_status":
          this._refreshAllModules();
          break;
        case "repair_engine":
          this._startSetupJourney(1, true);
          break;
        case "connect_zotero":
          this._startSetupJourney(2);
          break;
        case "retry_sync":
          this._runManualSync();
          break;
      }
    };

    if (decision.primaryAction || decision.secondaryAction) {
      const actionRow = summaryEl.createDiv({ cls: "pf-cc-summary-actions" });
      if (decision.primaryAction) {
        const pAct = decision.primaryAction;
        renderActionButton(actionRow, {
          label: pAct.label,
          onClick: () => runDecisionAction(pAct.kind),
        });
      }
      if (decision.secondaryAction) {
        const sAct = decision.secondaryAction;
        renderActionButton(actionRow, {
          label: sAct.label,
          variant: "ghost",
          onClick: () => runDecisionAction(sAct.kind),
        });
      }
    }

    const summaryMeta = summaryEl.createDiv({ cls: "pf-cc-summary-meta" });
    const latest = Object.values(envelopes)
      .map((e) => e.updated_at)
      .filter((ts) => ts && ts !== new Date(0).toISOString())
      .sort()
      .pop();
    summaryMeta.createEl("span", {
      text: this._silentRevalidating
        ? isZh
          ? "正在后台轻检…"
          : "Revalidating…"
        : latest
          ? (t("cc_last_checked") || "Checked: ") +
            new Date(latest).toLocaleString()
          : t("cc_checked_pending") || "Not checked yet",
    });

    const refreshBtn = summaryMeta.createEl("button", {
      cls: "pf-cc-summary-refresh",
      text: t("cc_refresh_btn") || "Refresh status",
      attr: { type: "button" },
    });
    refreshBtn.addEventListener("click", () => this._refreshAllModules());

    if (this._pendingOrphans.length > 0 && decision.id === "ready") {
      const oBanner = cc.createDiv({
        cls: "pf-upgrade-banner pf-orphan-banner",
        attr: { "data-pf-testid": "settings-orphan-banner" },
      });
      const copy = oBanner.createDiv({ cls: "pf-upgrade-banner-copy" });
      copy.createEl("div", {
        cls: "pf-upgrade-banner-title",
        text: t("orphan_banner_title").replace(
          "{count}",
          String(this._pendingOrphans.length)
        ),
      });
      const reviewBtn = oBanner.createEl("button", {
        cls: "pf-action-btn",
        type: "button",
        text: t("orphan_banner_btn"),
        attr: { "data-pf-testid": "settings-orphan-review-btn" },
      });
      reviewBtn.addEventListener("click", () => {
        this._openOrphanModal(this._pendingOrphans);
      });
    }

    // ── Group 1: Core Setup (clean 1-line rows → click jumps to dedicated Module page) ──
    const coreHead = cc.createDiv({ cls: "pf-cc-section-head" });
    coreHead.createEl("div", {
      cls: "pf-cc-section-title",
      text: t("cc_group_core") || (isZh ? "核心基础" : "Core Setup"),
    });

    const versionTag =
      runtimePtr?.paperforgeVersion ||
      this._runtimeStatusVersion ||
      this.plugin.manifest?.version ||
      "";
    const coreList = cc.createDiv({ cls: "pf-cc-module-list" });
    this._renderOverviewNavRow(
      coreList,
      "installation",
      t("cc_module_foundation") || (isZh ? "计算引擎" : "Compute Engine"),
      foundationEnv,
      versionTag
        ? isZh
          ? `本地服务 v${versionTag}`
          : `Local engine v${versionTag}`
        : undefined
    );
    this._renderOverviewNavRow(
      coreList,
      "library",
      t("cc_module_library") || (isZh ? "Zotero 文献库" : "Zotero Library"),
      libraryEnv,
      this.plugin.settings.zotero_data_dir || undefined
    );

    // ── Group 2: AI & Extensions (clean 1-line rows → dedicated sub-pages) ──
    const optHead = cc.createDiv({ cls: "pf-cc-section-head" });
    optHead.createEl("div", {
      cls: "pf-cc-section-title",
      text: t("cc_group_ai") || (isZh ? "AI 与扩展" : "AI & Extensions"),
    });
    optHead.createEl("span", {
      cls: "caption",
      text:
        t("cc_optional_note") ||
        "Optional modules do not affect core readiness.",
    });

    const optList = cc.createDiv({ cls: "pf-cc-module-list" });
    const ocrEnv = envelopes["ocr"] ?? createUnknownEnvelope("ocr");
    this._renderOverviewNavRow(
      optList,
      "ocr",
      t("cc_module_ocr") || "PDF 解析 (OCR)",
      ocrEnv,
      ocrEnv.user_state === "ready"
        ? undefined
        : isZh
          ? "把 PDF 里的图表、公式与扫描件拆成可编辑 Markdown 笔记（按需启用）"
          : "Turn scanned PDFs & figures into editable Markdown notes (unlock anytime)"
    );

    const memEnv = envelopes["memory"] ?? createUnknownEnvelope("memory");
    this._renderOverviewNavRow(
      optList,
      "memory",
      t("cc_module_memory") || "智能检索",
      memEnv,
      this.plugin.settings.vector_db_api_model
        ? `${this.plugin.settings.vector_db_api_model} · ${this._getModuleConsequence("memory", memEnv)}`
        : memEnv.user_state === "ready"
          ? undefined
          : isZh
            ? "忘掉论文标题也能用大白话跨全库找回某段结论（按需启用）"
            : "Search across hundreds of papers using plain questions (unlock anytime)"
    );

    const agentEnv = this._getAgentPlaceholderEnvelope();
    const agentPresence = this._getEffectiveAgentPresence();
    this._renderOverviewNavRow(
      optList,
      "agent",
      t("cc_module_agent") || "AI Agent 技能",
      agentEnv,
      this._getAgentPresenceSentence(agentPresence)
    );

    // ── VS Code Walkthrough-style Dismissible Exploration Checklist (when core is ready) ──
    if (decision.id === "ready" && !this._exploreChecklistDismissed) {
      const nextTasks: Array<{
        id: string;
        title: string;
        desc: string;
        targetMod: string;
      }> = [];
      if (ocrEnv.user_state !== "ready") {
        nextTasks.push({
          id: "ocr",
          title: isZh
            ? "开启 PDF 图表与全文提取"
            : "Unlock PDF Chart & Fulltext Extraction",
          desc: isZh
            ? "只需 1 个 PaddleOCR 免费密钥，自动拆出图表与正文。"
            : "Add 1 free PaddleOCR key to extract charts, tables & text.",
          targetMod: "ocr",
        });
      }
      if (memEnv.user_state !== "ready") {
        nextTasks.push({
          id: "memory",
          title: isZh
            ? "开启跨文献 AI 语义深检"
            : "Unlock Cross-Paper AI Semantic Search",
          desc: isZh
            ? "可选硅基流动或本地 Ollama，支持自然语言跨全文检索。"
            : "Use SiliconFlow preset or local Ollama for fulltext semantic Q&A.",
          targetMod: "memory",
        });
      }
      if (!this.plugin.settings._easyscholar_configured) {
        nextTasks.push({
          id: "easyscholar",
          title: isZh
            ? "补全精确 JCR 影响因子与分区"
            : "Add Exact JCR IF & Partitions",
          desc: isZh
            ? "目前已有开源学术指标 ≈，填入 EasyScholar 密钥即可精确对齐。"
            : "Upgrade from open ≈ metrics with an optional EasyScholar key.",
          targetMod: "library",
        });
      }
      if (nextTasks.length > 0) {
        const expCard = cc.createDiv({
          cls: "pf-cc-explore-card",
          attr: { "data-pf-testid": "cc-explore-checklist" },
        });
        const expHead = expCard.createDiv({ cls: "pf-cc-explore-head" });
        expHead.createEl("span", {
          cls: "pf-cc-explore-title",
          text: isZh
            ? "按需解锁进阶科研能力（不用也能正常管理文献与批注 PDF）"
            : "Unlock Optional Research Superpowers (Optional)",
        });
        const dismissBtn = expHead.createEl("button", {
          cls: "pf-btn pf-btn-ghost",
          text: isZh ? "暂不需要" : "Dismiss",
          attr: { type: "button", "data-pf-testid": "cc-explore-dismiss" },
        });
        dismissBtn.addEventListener("click", () => {
          this._exploreChecklistDismissed = true;
          this.display();
        });
        const expList = expCard.createDiv({ cls: "pf-cc-explore-list" });
        for (const task of nextTasks) {
          const itemBtn = expList.createEl("button", {
            cls: "pf-cc-explore-item",
            attr: {
              type: "button",
              "data-pf-testid": `cc-explore-${task.id}`,
            },
          });
          itemBtn.createEl("span", {
            cls: "pf-cc-explore-item-title",
            text: `${task.title} →`,
          });
          itemBtn.createEl("span", {
            cls: "pf-cc-explore-item-desc",
            text: task.desc,
          });
          itemBtn.addEventListener("click", () => {
            this._handleCardNavigation(task.targetMod);
          });
        }
      }
    }
  }

  private _renderOverviewNavRow(
    listEl: HTMLElement,
    mod: string,
    label: string,
    env: ProbeEnvelope,
    sentenceOverride?: string
  ): void {
    const agentPresence =
      mod === "agent" ? this._getEffectiveAgentPresence() : null;
    const row = listEl.createEl("div", {
      cls: "pf-cc-module-card pf-open-module-btn pf-cc-nav-row",
      attr: {
        "data-module": mod,
        "aria-label":
          label +
          " — " +
          (agentPresence
            ? this._formatAgentPresenceBadgeText(agentPresence, false)
            : this._getUserStateLabel(env.user_state)),
        role: "button",
        tabindex: "0",
      },
    });
    row.createEl("span", { cls: "pf-cc-card-name", text: label });
    if (agentPresence) {
      this._renderAgentPresenceBadge(row, agentPresence, false);
    } else {
      renderStatusBadge(
        row,
        env.user_state,
        this._getUserStateLabel(env.user_state)
      );
    }
    row.createEl("span", {
      cls: "pf-cc-card-sentence",
      text: sentenceOverride ?? this._getModuleConsequence(mod, env),
    });
    const metricText =
      env.user_state === "ready" &&
      env.action?.primary?.scope_count &&
      env.action.primary.scope_count > 1
        ? (t("cc_metric_papers") || "Papers: ") + env.action.primary.scope_count
        : "";
    row.createEl("span", {
      cls: "pf-cc-card-metric",
      text: metricText,
    });
    row.createEl("span", {
      cls: "pf-cc-card-arrow",
      text: "\u203A",
    });

    const openPage = () => this._handleCardNavigation(mod);
    row.addEventListener("click", openPage);
    row.addEventListener("keydown", (ev: KeyboardEvent) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        openPage();
      }
    });
  }

  /** Dedicated Appearance & Experience tab (keeps Overview calm and uncluttered). */
  _renderAppearanceTab(containerEl: HTMLElement): void {
    const page = containerEl.createDiv({ cls: "pf-appearance-page" });
    const head = page.createDiv({ cls: "pf-settings-page-head" });
    head.createEl("h2", {
      cls: "pf-settings-page-title",
      text: t("cc_appearance_heading") || "Appearance & Experience",
    });
    head.createEl("p", {
      cls: "pf-settings-page-lede",
      text:
        t("cc_appearance_lede") ||
        "Adjust theme palette, translucent surfaces, and motion preferences.",
    });

    const appearanceGroup = page.createDiv({ cls: "pf-cc-appearance-group" });

    const themeBar = appearanceGroup.createDiv({ cls: "pf-cc-theme-bar" });
    const themeCopy = themeBar.createDiv({ cls: "pf-cc-theme-copy" });
    themeCopy.createEl("div", {
      cls: "pf-cc-theme-label",
      text: t("settings_theme_label"),
    });
    themeCopy.createEl("div", {
      cls: "pf-cc-theme-desc",
      text: t("settings_theme_desc"),
    });
    const themeSelect = themeBar.createEl("select", {
      cls: "pf-cc-theme-select",
      attr: { "data-pf-testid": "settings-theme-mode" },
    }) as HTMLSelectElement;
    for (const [val, label] of [
      ["obsidian", t("settings_theme_obsidian")],
      ["asterlab", t("settings_theme_asterlab")],
      ["zinc", t("settings_theme_zinc")],
      ["warm", t("settings_theme_warm")],
    ] as const) {
      const opt = themeSelect.createEl("option", { text: label });
      opt.value = val;
    }
    const curTheme = this.plugin.settings.ui_theme_mode;
    themeSelect.value =
      curTheme === "asterlab"
        ? "asterlab"
        : curTheme === "zinc"
          ? "zinc"
          : curTheme === "warm"
            ? "warm"
            : "obsidian";
    themeSelect.addEventListener("change", () => {
      const next = themeSelect.value;
      this.plugin.settings.ui_theme_mode =
        next === "asterlab"
          ? "asterlab"
          : next === "zinc"
            ? "zinc"
            : next === "warm"
              ? "warm"
              : "obsidian";
      (
        this.plugin as unknown as { applyUiThemeMode?: () => void }
      ).applyUiThemeMode?.();
      void this.plugin.saveSettings();
    });

    const densityRow = appearanceGroup.createDiv({ cls: "pf-cc-theme-bar" });
    const densityCopy = densityRow.createDiv({ cls: "pf-cc-theme-copy" });
    densityCopy.createEl("div", {
      cls: "pf-cc-theme-label",
      text: t("settings_density_label"),
    });
    densityCopy.createEl("div", {
      cls: "pf-cc-theme-desc",
      text: t("settings_density_desc"),
    });
    const densitySelect = densityRow.createEl("select", {
      cls: "dropdown pf-select pf-cc-theme-select",
      attr: { "data-pf-testid": "settings-density-mode" },
    }) as HTMLSelectElement;
    for (const [val, label] of [
      ["compact", t("settings_density_compact")],
      ["default", t("settings_density_default")],
      ["comfortable", t("settings_density_comfortable")],
    ] as const) {
      const opt = densitySelect.createEl("option", { text: label });
      opt.value = val;
    }
    const curDensity = this.plugin.settings.ui_density;
    densitySelect.value =
      curDensity === "compact"
        ? "compact"
        : curDensity === "comfortable"
          ? "comfortable"
          : "default";
    densitySelect.addEventListener("change", () => {
      const next = densitySelect.value;
      this.plugin.settings.ui_density =
        next === "compact"
          ? "compact"
          : next === "comfortable"
            ? "comfortable"
            : "default";
      (
        this.plugin as unknown as { applyUiThemeMode?: () => void }
      ).applyUiThemeMode?.();
      void this.plugin.saveSettings();
    });

    // Advanced visual & accessibility tweaks tucked inside collapsed details (zero clutter)
    const isZhApp = t("nav_close") === "关闭";
    const moreDet = page.createEl("details", {
      cls: "pf-adv-inline-details pf-appearance-more",
      attr: { "data-pf-testid": "settings-appearance-more" },
    });
    moreDet.createEl("summary", {
      text: isZhApp
        ? "视觉细节与无障碍（毛玻璃 / 减弱动效）▾"
        : "Visual effects & accessibility (Glass / Reduce motion) ▾",
    });
    const moreGroup = moreDet.createDiv({ cls: "pf-cc-appearance-group" });

    const glassRow = moreGroup.createDiv({ cls: "pf-cc-theme-bar" });
    const glassCopy = glassRow.createDiv({ cls: "pf-cc-theme-copy" });
    glassCopy.createEl("div", {
      cls: "pf-cc-theme-label",
      text: t("settings_liquid_glass_label"),
    });
    glassCopy.createEl("div", {
      cls: "pf-cc-theme-desc",
      text: t("settings_liquid_glass_desc"),
    });
    const glassSwitch = glassRow.createEl("input", {
      type: "checkbox",
      cls: "pf-switch",
      attr: { "data-pf-testid": "settings-liquid-glass" },
    }) as HTMLInputElement;
    glassSwitch.checked = this.plugin.settings.ui_liquid_glass === true;
    glassSwitch.addEventListener("change", () => {
      this.plugin.settings.ui_liquid_glass = glassSwitch.checked;
      (
        this.plugin as unknown as { applyUiThemeMode?: () => void }
      ).applyUiThemeMode?.();
      void this.plugin.saveSettings();
    });

    const motionRow = moreGroup.createDiv({ cls: "pf-cc-theme-bar" });
    const motionCopy = motionRow.createDiv({ cls: "pf-cc-theme-copy" });
    motionCopy.createEl("div", {
      cls: "pf-cc-theme-label",
      text: t("settings_reduce_motion_label"),
    });
    motionCopy.createEl("div", {
      cls: "pf-cc-theme-desc",
      text: t("settings_reduce_motion_desc"),
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
      library:
        "zotero bbt pdf sync exports runtime python core 同步 文献库 路径 环境",
      ocr: "paddle ocr fulltext 解析 扫描",
      memory: "vector embedding sqlite search api 向量 检索 认知 硅基",
      agent: "claude codex opencode cursor skill agents 技能",
    };
    const items = Array.from(
      containerEl.querySelectorAll<HTMLElement>(
        ".pf-cc-accordion-item, .pf-cc-module-card, .pf-maintenance-inbox-item"
      )
    );
    for (const el of items) {
      if (!q) {
        el.classList.remove("pf-is-filtered-out");
        el.style.display = "";
        continue;
      }
      const mod = el.getAttribute("data-module") || "";
      const haystack = (
        (el.textContent || "") +
        " " +
        mod +
        " " +
        (MODULE_KEYWORDS[mod] || "")
      ).toLowerCase();
      const matched = haystack.includes(q);
      if (matched) {
        el.classList.remove("pf-is-filtered-out");
        el.style.display = "";
      } else {
        el.classList.add("pf-is-filtered-out");
        el.style.display = "none";
      }
    }
  }

  /** Derive Agent availability from live MCP session presence (never fake-green). */
  _getAgentPlaceholderEnvelope(): ProbeEnvelope {
    const presence = this._getEffectiveAgentPresence();
    const isLive = presence.state === "connected" || presence.state === "ready";
    const isIdle = presence.state === "configured_idle";
    const isStandby = isIdle && Boolean(presence.has_connected_before);
    const isHealthy = isLive || isStandby;
    return {
      schema_version: 2,
      module: "agent",
      capability_state: isHealthy ? "ready" : "needs_action",
      activity_state: "idle",
      activity_label: null,
      activity_progress: null,
      severity: isHealthy ? "ok" : isIdle ? "unknown" : "warning",
      reason: {
        code:
          presence.state === "ready"
            ? "agent.ready"
            : presence.state === "connected"
              ? "agent.connected"
              : isStandby
                ? "agent.standby"
                : isIdle
                  ? "agent.configured_idle"
                  : "agent.unconnected",
        text: this._getAgentPresenceSentence(presence),
      },
      action: { primary: null },
      notices: [],
      user_state: isHealthy
        ? "ready"
        : isIdle
          ? "action_required"
          : "not_enabled",
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
  _refreshAllReadModels(
    lastLibraryExitCodeOrOpts?:
      | number
      | { lastLibraryExitCode?: number; silent?: boolean; background?: boolean }
  ): void {
    const background =
      typeof lastLibraryExitCodeOrOpts === "object" &&
      lastLibraryExitCodeOrOpts?.background === true;
    if (background && !this._isOpen) {
      // Settings is closed: mark dirty without spawning Python probeAll or rebuilding hidden DOM
      this._readModelsDirty = true;
      return;
    }
    const lastLibraryExitCode =
      typeof lastLibraryExitCodeOrOpts === "number"
        ? lastLibraryExitCodeOrOpts
        : lastLibraryExitCodeOrOpts?.lastLibraryExitCode;
    const silent =
      typeof lastLibraryExitCodeOrOpts === "object" &&
      lastLibraryExitCodeOrOpts?.silent === true;
    const client = this.getClient();
    if (!client || typeof client.probeAll !== "function") {
      this._probing.clear();
      this._silentRevalidating = false;
      return;
    }
    if (!silent) {
      client.invalidateCache?.();
    }
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

    const fingerprintState = (
      state?: Record<string, ProbeEnvelope> | null
    ): string =>
      JSON.stringify(
        CAPABILITY_MODULES.map((m) => {
          const e = state?.[m];
          return e
            ? [
                m,
                e.user_state,
                e.capability_state,
                e.reason?.code,
                e.action?.primary?.action_id,
                e.details,
              ]
            : [m];
        })
      );
    const prevFingerprint = silent
      ? fingerprintState(this._capabilityState)
      : "";

    if (silent) {
      this._silentRevalidating = true;
    } else {
      for (const mod of CAPABILITY_MODULES) {
        this._probing.add(mod);
      }
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
        this._silentRevalidating = false;
        const modules = {
          ...data.modules,
          installation: isValidEnvelope(installation, "installation")
            ? installation
            : createInvalidEnvelope("installation"),
        };
        if (silent) {
          this._capabilityState = this._capabilityState ?? {};
          for (const [mod, env] of Object.entries(modules)) {
            if (!isValidEnvelope(env, mod as CapabilityModule)) continue;
            const prevMod = this._capabilityState[mod];
            // Never let a transient silent probe error overwrite a healthy "ready" module in Settings
            if (
              prevMod?.user_state === "ready" &&
              (env as ProbeEnvelope).user_state === "detection_failed"
            ) {
              continue;
            }
            this._capabilityState[mod] = env as ProbeEnvelope;
          }
          this._persistCapabilityState();
          const changed =
            fingerprintState(this._capabilityState) !== prevFingerprint;
          if (changed && !this._displayInProgress) {
            this.display();
          }
        } else {
          for (const [mod, env] of Object.entries(modules)) {
            if (isValidEnvelope(env, mod as CapabilityModule)) {
              this._updateCapabilityEnvelope(
                mod as CapabilityModule,
                env as ProbeEnvelope
              );
            }
          }
        }
        // #78: the library sync-failure exit code is forwarded into the
        // library probe (probe all carries no exit-code context).
        if (lastLibraryExitCode != null && lastLibraryExitCode !== 0) {
          this._probeModule("library", lastLibraryExitCode);
        }
        // Non-blocking orphan detection: record orphans for a calm persistent
        // inline banner & explicit Review button instead of auto-popping a
        // blocking Modal during background probes.
        const maint = (data.modules?.["maintenance"] ??
          null) as unknown as Record<string, unknown> | null;
        const orphanInfo = (maint?.orphan ?? {}) as {
          count?: number;
          orphans?: { key: string; title?: string }[];
        };
        const orphanCount = orphanInfo.count ?? 0;
        const nextOrphans = orphanCount > 0 ? (orphanInfo.orphans ?? []) : [];
        const orphanChanged = orphanCount !== this._lastOrphanCount;
        this._pendingOrphans = nextOrphans;
        this._lastOrphanCount = orphanCount;
        if (orphanChanged && !this._displayInProgress) {
          this.display();
        }
      })
      .catch(() => {
        this._probing.clear();
        this._silentRevalidating = false;
        if (!silent) {
          this._updateCapabilityEnvelope(
            "installation",
            createInvalidEnvelope("installation")
          );
          this.display();
        }
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
          if (typeof fs.opendirSync === "function") {
            const dir = fs.opendirSync(full);
            try {
              if (dir.readSync() !== null) {
                collided.push(folder);
              }
            } finally {
              dir.closeSync();
            }
          } else if (fs.readdirSync(full).length > 0) {
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

    if (
      this._setupExpressMode &&
      this._setupStage === 1 &&
      !this._setupReinstallRequested
    ) {
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

  /** Single resolved literature folder path used by collision guard, Ready summary & preview. */
  private _resolveSetupLiteratureDir(): string {
    const raw = (this.plugin.settings.literature_dir || "Literature").trim();
    return (raw || "Literature").replace(/\/+$/, "");
  }

  /** Express 1-page beginner flow inspired by Linear / Cherry Studio / VS Code Walkthrough. */
  private _renderExpressSetup(wrapper: HTMLElement, isZh: boolean): void {
    this._refreshRuntimeStatus();
    this._maybeAutoDetectZotero();

    const settings = this.plugin.settings;
    const pointer = readRuntimePointer();
    const runtime = this._runtimeStatus;
    const ptrReady = Boolean(
      pointer &&
      fs.existsSync(pointer.pythonPath) &&
      !this._runtimeStatusError &&
      isEngineVersionCompatible(
        pointer.paperforgeVersion,
        String(this.plugin?.manifest?.version ?? ""),
        this._minEngineVersion()
      )
    );
    const rtReady =
      runtime?.runtime_ready === true || (runtime === null && ptrReady);
    const action: RuntimeInstallerAction = !pointer
      ? "install"
      : runtime?.version_matches_expected === false
        ? "update"
        : "repair";

    const zoteroDir = (settings.zotero_data_dir || "").trim();
    const zoteroReady =
      Boolean(this._zoteroDetectData?.found) ||
      Boolean(zoteroDir && fs.existsSync(zoteroDir));
    const aiConfiguredCount =
      (settings._paddleocr_configured ? 1 : 0) +
      (settings._vector_db_configured ? 1 : 0) +
      (settings._easyscholar_configured ? 1 : 0);
    const reqDone = (rtReady ? 1 : 0) + (zoteroReady ? 1 : 0);
    const progressPct = reqDone === 2 ? 100 : reqDone === 1 ? 56 : 16;

    /** Shared helper: password input + crisp Show/Hide Eye toggle. */
    const appendSecretInput = (
      parent: HTMLElement,
      placeholder: string,
      testIdPrefix: string
    ): HTMLInputElement => {
      const wrap = parent.createDiv({ cls: "pf-secret-field-wrap" });
      const input = wrap.createEl("input", {
        cls: "pf-setup-input",
        attr: {
          type: "password",
          autocomplete: "off",
          placeholder,
          "data-pf-testid": `${testIdPrefix}-input`,
        },
      }) as HTMLInputElement;
      const eyeBtn = wrap.createEl("button", {
        cls: "pf-secret-eye-btn",
        attr: {
          type: "button",
          "aria-label": isZh ? "显示或隐藏密钥" : "Show or hide API key",
          "data-pf-testid": `${testIdPrefix}-eye`,
        },
      });
      setPfIcon(eyeBtn, "eye", 13);
      eyeBtn.addEventListener("click", () => {
        const nextType = input.type === "password" ? "text" : "password";
        input.type = nextType;
        eyeBtn.setAttribute(
          "aria-pressed",
          nextType === "text" ? "true" : "false"
        );
      });
      return input;
    };

    const head = wrapper.createDiv({ cls: "pf-express-header" });
    const headCopy = head.createDiv();
    headCopy.createEl("h2", {
      text: isZh
        ? "欢迎使用 PaperForge · 把 Zotero 文献搬进 Obsidian"
        : "PaperForge Quick Start · Zotero inside Obsidian",
    });
    headCopy.createEl("p", {
      cls: "pf-setup-desc",
      text: isZh
        ? "只读访问你的 Zotero，绝不修改原库；30 秒即可看到文献总表并直接做 PDF 批注。"
        : "Read-only on your Zotero DB. Start browsing your library and annotating PDFs in 30 seconds.",
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

    // ── Section A: 10-Second Capability Map (Immediate Free vs Unlock When Needed) ──
    const capMap = wrapper.createDiv({
      cls: "pf-setup-cap-map",
      attr: { "data-pf-testid": "setup-capability-map" },
    });
    const capCards: Array<{
      icon: "database" | "book-open" | "file-text" | "sparkles";
      title: string;
      badge: string;
      free: boolean;
      desc: string;
    }> = [
      {
        icon: "database",
        title: isZh ? "文献总表与筛选" : "Master Library Table",
        badge: isZh ? "开箱可用" : "Ready Now",
        free: true,
        desc: isZh
          ? "自动汇总全部 Zotero 文献，按专题、年份与影响因子随时筛选。"
          : "All Zotero papers in one filterable table with topics, years & metrics.",
      },
      {
        icon: "book-open",
        title: isZh ? "内置 PDF 伴读批注" : "Built-in PDF Reader",
        badge: isZh ? "开箱可用" : "Ready Now",
        free: true,
        desc: isZh
          ? "直接在 Obsidian 打开 PDF 阅读，高亮与图形批注自动记入笔记。"
          : "Read PDFs side-by-side with highlights and callouts synced to notes.",
      },
      {
        icon: "file-text",
        title: isZh ? "PDF 图表与全文提取" : "PDF Chart & Fulltext OCR",
        badge: isZh ? "按需配置" : "Optional Setup",
        free: false,
        desc: isZh
          ? "把扫描件、公式和论文插图提取为可检索的结构化 Markdown（OCR）。"
          : "Turn scanned PDFs, equations and figures into structured Markdown.",
      },
      {
        icon: "sparkles",
        title: isZh ? "跨文献 AI 语义深检" : "AI Semantic Deep Search",
        badge: isZh ? "按需配置" : "Optional Setup",
        free: false,
        desc: isZh
          ? "忘掉论文标题也能用大白话搜回几百篇文献中的某段实验结论。"
          : "Recall findings across hundreds of papers using natural questions.",
      },
    ];
    for (const item of capCards) {
      const card = capMap.createDiv({ cls: "pf-setup-cap-card" });
      const topRow = card.createDiv({ cls: "pf-setup-cap-head" });
      const iconHost = topRow.createEl("span", { cls: "pf-setup-cap-icon" });
      setPfIcon(iconHost, item.icon, 13);
      topRow.createEl("span", {
        cls: "pf-setup-cap-title",
        text: item.title,
      });
      topRow.createEl("span", {
        cls: `pf-setup-cap-pill ${item.free ? "is-free" : "is-later"}`,
        text: item.badge,
      });
      card.createEl("p", {
        cls: "pf-setup-cap-desc",
        text: item.desc,
      });
    }

    // ── Section B: Card 1 — 唯一需要确认的事：连接你的 Zotero ──
    const c1 = wrapper.createDiv({
      cls: "pf-express-card pf-express-primary-card",
    });
    const c1Head = c1.createDiv({ cls: "pf-express-card-head" });
    c1Head.createEl("span", { cls: "pf-express-num", text: "1" });
    c1Head.createEl("strong", {
      text: isZh
        ? "确认你的 Zotero 文献库（无需装插件）"
        : "Confirm Your Zotero Library (Zero plugins)",
    });
    c1Head.createEl("span", {
      cls: "pf-express-trust-chip",
      text: isZh ? "只读访问 · 不改原库" : "Read-only · Safe",
    });
    c1Head.createEl("span", {
      cls: `pf-express-pill ${zoteroReady ? "is-ok" : "is-warn"}`,
      text: this._zoteroDetectData?.found
        ? isZh
          ? `✓ 已找到 ${this._zoteroDetectData.total_papers} 篇`
          : `✓ ${this._zoteroDetectData.total_papers} papers`
        : zoteroReady
          ? isZh
            ? "✓ 目录已定位"
            : "✓ Folder ready"
          : this._zoteroDetectBusy
            ? isZh
              ? "自动扫描中…"
              : "Scanning…"
            : isZh
              ? "请选择目录"
              : "Pick folder",
    });

    if (this._detectedFolderCollisionMsg) {
      c1.createEl("p", {
        cls: "pf-setup-ok pf-collision-guard-banner",
        text: isZh
          ? `已开启目录防冲突保护：${this._detectedFolderCollisionMsg}`
          : this._detectedFolderCollisionMsg,
      });
    }

    const curMode =
      settings.domain_mode === "unified" ? "unified" : "per_collection";
    const litTargetDir = this._resolveSetupLiteratureDir();
    const paperCnt = this._zoteroDetectData?.total_papers;
    const summaryEl = c1.createEl("div", {
      cls: "pf-express-default-summary",
    });
    const updateReadySummary = () => {
      const targetDir = this._resolveSetupLiteratureDir();
      const activeMode =
        settings.domain_mode === "unified" ? "unified" : "per_collection";
      summaryEl.textContent = zoteroReady
        ? isZh
          ? `✓ 已自动就绪：只读读取 Zotero 原库，并在 Vault 的 ${targetDir}/ 目录生成${paperCnt ? ` ${paperCnt} 篇` : ""}文献笔记（${activeMode === "unified" ? "全部统一放进目录并在总表筛选" : "按 Zotero 顶级文件夹分专题归类"}）。`
          : `✓ Ready: reads your Zotero DB read-only and creates${paperCnt ? ` ${paperCnt}` : ""} notes inside ${targetDir}/ (${activeMode === "unified" ? "unified folder + Base filters" : "grouped by your top Zotero folders"}).`
        : isZh
          ? `未自动找到 Zotero 默认目录，请在下方选择或粘贴你的 Zotero 数据目录（导入后将写入 Vault 的 ${targetDir}/）。`
          : `Zotero default folder was not detected automatically. Browse or paste your Zotero directory below (notes will be created in ${targetDir}/).`;
    };
    updateReadySummary();

    // Seamless Engine Auto-Pipeline notice/progress inside Card 1
    const daemonUpdating = Boolean(this.plugin?.isDaemonUpdating?.());
    const liveRuntime = this.plugin?.getLiveTaskSummary?.("runtime") ?? null;
    const liveSync = this.plugin?.getLiveTaskSummary?.("sync") ?? null;
    const expressRuntimeInProgress =
      !rtReady &&
      (this._syncRuntimePollFromBackground() ||
        Boolean(this._runtimePollTimer) ||
        Boolean(this.plugin?.isRuntimeUpdating?.()) ||
        Boolean(this._pendingRuntimeRestartAfterDaemonSwap));
    const rtChecking =
      !rtReady &&
      !this._runtimeStatusError &&
      !daemonUpdating &&
      !expressRuntimeInProgress &&
      (this._runtimeStatusLoading ||
        (Boolean(pointer) && this._runtimeStatus === null));
    const isImporting =
      this._setupOperation === "running" &&
      !expressRuntimeInProgress &&
      !daemonUpdating;
    const ctaBusy =
      daemonUpdating || rtChecking || expressRuntimeInProgress || isImporting;

    if (daemonUpdating) {
      const pipeBox = c1.createDiv({ cls: "pf-express-pipeline-box" });
      pipeBox.createDiv({
        cls: "pf-express-pipeline-steps",
        text: isZh
          ? "正在切换至新版后台服务组件 → 完成后自动继续安装引擎与导入…"
          : "Updating local background service → Engine & import will resume automatically…",
      });
      const bar = pipeBox.createDiv({ cls: "pf-runtime-stage-bar" });
      const fill = bar.createDiv({ cls: "pf-runtime-stage-fill" });
      fill.classList.add("is-indeterminate");
    } else if (!rtReady) {
      if (expressRuntimeInProgress) {
        const prog =
          liveRuntime?.phaseText || this._installerProgressLine() || "";
        const elapsedText =
          liveRuntime?.startedAt && liveRuntime.startedAt > 0
            ? ` · ${Math.max(1, Math.floor((Date.now() - liveRuntime.startedAt) / 1000))}s`
            : "";
        let pct = 15;
        if (liveRuntime && liveRuntime.total > 0 && liveRuntime.current > 0) {
          pct = Math.max(
            10,
            Math.min(
              100,
              Math.round((liveRuntime.current / liveRuntime.total) * 100)
            )
          );
        } else if (prog.includes("4/5")) {
          pct = 80;
        } else if (prog.includes("3/5")) {
          pct = 60;
        } else if (prog.includes("2/5")) {
          pct = 40;
        } else if (prog.includes("1/5")) {
          pct = 22;
        }
        const pipeBox = c1.createDiv({ cls: "pf-express-pipeline-box" });
        pipeBox.createDiv({
          cls: "pf-express-pipeline-steps",
          text: this._autoContinueSetupAfterInstall
            ? isZh
              ? `① 正在安装计算引擎 (${prog || "进行中…"}${elapsedText})  →  ② 自动导入 Zotero 文献`
              : `1. Installing compute engine (${prog || "working…"}${elapsedText})  →  2. Auto-importing Zotero`
            : isZh
              ? `正在后台安装 PaperForge 计算引擎 (${prog || "进行中…"}${elapsedText})`
              : `Installing PaperForge compute engine (${prog || "working…"}${elapsedText})`,
        });
        const bar = pipeBox.createDiv({ cls: "pf-runtime-stage-bar" });
        const fill = bar.createDiv({ cls: "pf-runtime-stage-fill" });
        fill.style.width = `${pct}%`;
      } else {
        c1.createEl("p", {
          cls: "pf-express-card-sub",
          text: isZh
            ? "提示：点击右下角按钮会先全自动安装 PaperForge 计算引擎（约 20 秒，无需手动装 Python），就绪后自动开始导入文献。"
            : "Note: Clicking the button below first installs the PaperForge compute engine (~20s, zero terminal needed), then automatically imports your library.",
        });
      }
    } else if (isImporting) {
      const syncLabel =
        liveSync?.phaseText ||
        (this._setupPhase === "configuring"
          ? isZh
            ? "正在写入文献库配置…"
            : "Writing library configuration…"
          : t("setup_library_syncing"));
      const syncElapsed =
        liveSync?.startedAt && liveSync.startedAt > 0
          ? ` · ${Math.max(1, Math.floor((Date.now() - liveSync.startedAt) / 1000))}s`
          : "";
      const syncPct =
        liveSync && liveSync.total > 0 && liveSync.current > 0
          ? Math.max(
              10,
              Math.min(
                100,
                Math.round((liveSync.current / liveSync.total) * 100)
              )
            )
          : 25;
      const pipeBox = c1.createDiv({ cls: "pf-express-pipeline-box" });
      pipeBox.createDiv({
        cls: "pf-express-pipeline-steps",
        text: isZh
          ? `✓ 计算引擎已就绪  →  正在导入 Zotero 文献 (${syncLabel}${syncElapsed})`
          : `✓ Compute engine ready  →  Importing Zotero (${syncLabel}${syncElapsed})`,
      });
      const bar = pipeBox.createDiv({ cls: "pf-runtime-stage-bar" });
      const fill = bar.createDiv({ cls: "pf-runtime-stage-fill" });
      fill.style.width = `${syncPct}%`;
    }

    // Collapsed Smart Defaults (open automatically only if Zotero not found yet)
    const customizeDet = c1.createEl("details", {
      cls: "pf-express-customize-details",
    });
    if (!zoteroReady) {
      customizeDet.open = true;
    }
    customizeDet.createEl("summary", {
      text: isZh
        ? "调整 Zotero 位置、目录归档方式或筛选特定文件夹 ▾"
        : "Customize Zotero path, folder layout or collections ▾",
      attr: { "data-pf-testid": "express-customize-toggle" },
    });
    const customBody = customizeDet.createDiv({
      cls: "pf-express-customize-body",
    });

    const zotRow = customBody.createDiv({ cls: "pf-setup-path-row" });
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
    zotInput.value =
      settings.zotero_data_dir ||
      (this._zoteroDetectData?.found
        ? this._zoteroDetectData.zotero_dir || ""
        : "");
    const applyZot = (dir: string) => {
      settings.zotero_data_dir = dir.trim();
      settings.zotero_source_mode = "sqlite";
      zotInput.value = settings.zotero_data_dir;
      void this.plugin.saveSettings();
      this._maybeAutoDetectZotero(true);
      this.display();
    };
    zotInput.addEventListener("change", () => applyZot(zotInput.value));
    const rescanBtn = zotRow.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: isZh ? "重新扫描" : "Re-scan",
      attr: { type: "button", "data-pf-testid": "express-zotero-rescan" },
    });
    rescanBtn.addEventListener("click", () =>
      this._maybeAutoDetectZotero(true)
    );
    const browseBtn = zotRow.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: t("setup_zotero_browse"),
      attr: { type: "button" },
    });
    browseBtn.addEventListener("click", () => {
      void this._pickFolderPath(customBody).then((picked) => {
        if (picked) applyZot(picked);
      });
    });

    const targetDirRow = customBody.createDiv({ cls: "pf-setup-path-row" });
    const targetDirIn = targetDirRow.createEl("input", {
      cls: "pf-setup-input",
      attr: {
        type: "text",
        placeholder: isZh
          ? "Obsidian 写入目录（如 PaperForge/Literature）"
          : "Vault output folder (e.g. PaperForge/Literature)",
        "data-pf-testid": "express-lit-dir-input",
      },
    }) as HTMLInputElement;
    targetDirIn.value = litTargetDir;

    const previewHost = customBody.createDiv();
    const allCols = this._zoteroDetectData?.collections ?? [];
    const topCols = allCols.filter((c) => c.top_level !== false);
    const curSel = new Set(
      Array.isArray(settings.zotero_selected_collections)
        ? settings.zotero_selected_collections
        : []
    );
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
        litDir: this._resolveSetupLiteratureDir(),
        isZh,
      });
      updateReadySummary();
    };
    targetDirIn.addEventListener("change", () => {
      const cleaned =
        targetDirIn.value.trim().replace(/^\/+|\/+$/g, "") || "Literature";
      settings.literature_dir = cleaned;
      targetDirIn.value = cleaned;
      void this.plugin.saveSettings();
      redrawPreview();
    });

    const modeGrid = customBody.createDiv({ cls: "pf-mode-choice-grid" });
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
      const colDet = customBody.createEl("details", {
        cls: "pf-adv-inline-details",
      });
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
        label.createEl("span", { text: col.name });
        label.createEl("span", {
          cls: "pf-zotero-col-cnt",
          text: `${col.item_count}`,
        });
      }
    }

    // ── Section C: Card 2 — 进阶功能（全部可选，以后用到再开） ──
    const c2 = wrapper.createDiv({
      cls: "pf-express-card pf-express-optional-card",
    });
    const aiExpanded = this._setupExpressAiOpen;
    const c2HeadBtn = c2.createEl("button", {
      cls: "pf-express-ai-head-btn",
      attr: {
        type: "button",
        "aria-expanded": aiExpanded ? "true" : "false",
        "data-pf-testid": "express-ai-toggle",
      },
    });
    const c2Head = c2HeadBtn.createDiv({ cls: "pf-express-card-head" });
    c2Head.style.width = "100%";
    c2Head.style.marginBottom = "0";
    c2Head.createEl("span", { cls: "pf-express-num", text: "2" });
    c2Head.createEl("strong", {
      text: isZh
        ? "进阶科研能力（全部可选 · 按需启用）"
        : "Optional AI & Metrics (Skip for now, unlock later)",
    });
    c2Head.createEl("span", {
      cls: `pf-express-pill ${aiConfiguredCount > 0 ? "is-ok" : "is-warn"}`,
      text: isZh
        ? aiConfiguredCount > 0
          ? `已配置 ${aiConfiguredCount}/3`
          : aiExpanded
            ? "收起"
            : "提前配置 ▾"
        : aiConfiguredCount > 0
          ? `${aiConfiguredCount}/3 configured`
          : aiExpanded
            ? "Collapse"
            : "Configure ▾",
    });
    c2HeadBtn.addEventListener("click", () => {
      this._setupExpressAiOpen = !aiExpanded;
      this.display();
    });
    c2.createEl("p", {
      cls: "pf-express-card-sub",
      text: isZh
        ? "现在直接跳过完全不影响管理文献与阅读 PDF 批注；需要提取图表公式或跨文献 AI 问答时再来开启即可。"
        : "Skipping now does not affect library management or PDF annotations; enable OCR or AI search whenever you need them.",
    });

    if (aiExpanded) {
      const tabBar = c2.createDiv({
        cls: "pf-express-ai-tabs",
        attr: { "data-pf-testid": "express-ai-tabs" },
      });
      const aiTabDefs: Array<{
        id: "ocr" | "embed" | "easyscholar";
        label: string;
        ok: boolean;
      }> = [
        {
          id: "ocr",
          label: isZh ? "提取 PDF 图表与全文 (OCR)" : "PDF OCR",
          ok: Boolean(settings._paddleocr_configured),
        },
        {
          id: "embed",
          label: isZh ? "AI 语义深检 (向量检索)" : "AI Semantic Search",
          ok: Boolean(settings._vector_db_configured),
        },
        {
          id: "easyscholar",
          label: isZh ? "精确影响因子与分区" : "EasyScholar IF",
          ok: Boolean(settings._easyscholar_configured),
        },
      ];
      for (const tb of aiTabDefs) {
        const b = tabBar.createEl("button", {
          cls: `pf-express-ai-tab${this._setupExpressAiTab === tb.id ? " is-active" : ""}`,
          text: `${tb.ok ? "✓ " : ""}${tb.label}`,
          attr: {
            type: "button",
            "data-pf-testid": `express-ai-tab-${tb.id}`,
          },
        });
        b.addEventListener("click", () => {
          this._setupExpressAiTab = tb.id;
          this.display();
        });
      }

      const pane = c2.createDiv({ cls: "pf-express-ai-pane" });
      if (this._setupExpressAiTab === "ocr") {
        const lblRow = pane.createDiv({ cls: "pf-express-label-row" });
        lblRow.createEl("strong", {
          text: isZh
            ? "PaddleOCR VL · 将扫描件/图表转为可检索结构化 Markdown"
            : "PaddleOCR · Structured Markdown & Figure Extraction",
        });
        lblRow.createEl("a", {
          cls: "pf-express-help-link",
          text: isZh ? "获取免费密钥 ↗" : "Get free key ↗",
          attr: {
            href: "https://aistudio.baidu.com/paddleocr/task",
            target: "_blank",
            rel: "noopener noreferrer",
          },
        });
        const ocrRow = pane.createDiv({ cls: "pf-secret-input-row" });
        const ocrKeyIn = appendSecretInput(
          ocrRow,
          settings._paddleocr_configured
            ? t("settings_secret_saved_placeholder")
            : t("settings_ocr_key_placeholder"),
          "express-ocr"
        );
        const ocrBtn = ocrRow.createEl("button", {
          cls: "pf-btn pf-btn-secondary",
          text: rtReady
            ? isZh
              ? "保存并测通"
              : "Save & Test"
            : isZh
              ? "保存密钥"
              : "Save Key",
          attr: { type: "button", "data-pf-testid": "express-ocr-save" },
        });
        const ocrMsg = pane.createEl("span", { cls: "pf-test-conn-status" });
        ocrBtn.addEventListener("click", () => {
          const val = ocrKeyIn.value.trim();
          ocrBtn.disabled = true;
          ocrMsg.className = "pf-test-conn-status";
          ocrMsg.textContent = rtReady
            ? isZh
              ? "测试中…"
              : "Testing…"
            : isZh
              ? "保存中…"
              : "Saving…";
          void (
            val
              ? this._storeSetupSecret("paddleocr-api-key", val)
              : Promise.resolve(true)
          )
            .then((saved) => {
              if (!saved) {
                throw new Error(isZh ? "保存失败" : "Save failed");
              }
              if (val) ocrKeyIn.value = "";
              if (!rtReady) {
                ocrMsg.className = "pf-test-conn-status is-ok";
                ocrMsg.textContent = isZh
                  ? "✓ 已安全保存，启用引擎后自动生效"
                  : "✓ Saved securely; active once engine starts";
                return;
              }
              return this.getClient()
                .ocrTestConnection()
                .then((res) => {
                  ocrMsg.className = `pf-test-conn-status ${res?.passed ? "is-ok" : "is-err"}`;
                  ocrMsg.textContent = res?.passed
                    ? isZh
                      ? "✓ 已连通"
                      : "✓ Connected"
                    : formatProviderConnectionError(
                        res?.error || "",
                        "ocr",
                        isZh
                      );
                });
            })
            .catch((err) => {
              ocrMsg.className = "pf-test-conn-status is-err";
              ocrMsg.textContent = formatProviderConnectionError(
                String(err?.message || err),
                "ocr",
                isZh
              );
            })
            .finally(() => {
              ocrBtn.disabled = false;
            });
        });
      } else if (this._setupExpressAiTab === "embed") {
        const matchedPreset = matchEmbeddingPresetId(
          settings.vector_db_api_base || "",
          settings.vector_db_api_model || ""
        );
        const curP = this._expressCustomMode ? "custom" : matchedPreset;
        const activePreset =
          EMBEDDING_PRESETS.find((x) => x.id === curP) ?? EMBEDDING_PRESETS[0];

        // Row 1: Provider header + signup link + 6 compact chips
        const lblRow = pane.createDiv({ cls: "pf-express-label-row" });
        lblRow.createEl("strong", {
          text: isZh ? "选择向量服务商" : "Select Embedding Provider",
        });
        if (activePreset.signupUrl) {
          const shortName = isZh
            ? activePreset.shortLabelZh.split(" ·")[0]
            : activePreset.shortLabelEn.split(" ·")[0];
          lblRow.createEl("a", {
            cls: "pf-express-help-link",
            text: isZh ? `获取 ${shortName} 密钥 ↗` : `Get ${shortName} key ↗`,
            attr: {
              href: activePreset.signupUrl,
              target: "_blank",
              rel: "noopener noreferrer",
              "data-pf-testid": "express-embed-signup",
            },
          });
        }
        const chips = pane.createDiv({ cls: "pf-express-preset-chips" });
        for (const p of EMBEDDING_PRESETS) {
          const chip = chips.createEl("button", {
            cls: `pf-express-preset-chip${p.id === curP ? " is-active" : ""}`,
            text: isZh ? p.shortLabelZh : p.shortLabelEn,
            attr: {
              type: "button",
              "data-pf-testid": `express-embed-preset-${p.id}`,
            },
          });
          chip.addEventListener("click", () => {
            this._expressCustomMode = p.id === "custom";
            this._expressFetchedModels = [];
            const cli = this.getClient() as unknown as {
              configSet?: (k: string, v: string) => Promise<unknown>;
            };
            if (p.id !== "custom") {
              settings.vector_db_api_base = p.baseUrl;
              settings.vector_db_api_model = p.model;
              void cli
                ?.configSet?.("vector_db_api_base", p.baseUrl)
                ?.catch(() => undefined);
              void cli
                ?.configSet?.("vector_db_api_model", p.model)
                ?.catch(() => undefined);
            } else {
              settings.vector_db_api_base = "";
            }
            void this.plugin.saveSettings?.();
            this.display();
          });
        }

        // Row 2: Single-line Trait + Curated Model Picker (keeps official presets clutter-free)
        const metaBar = pane.createDiv({ cls: "pf-embed-meta-bar" });
        metaBar.createEl("span", {
          cls: "pf-embed-trait",
          text: isZh ? activePreset.traitZh : activePreset.traitEn,
        });
        if (curP !== "custom" && activePreset.models.length > 0) {
          const modelCandidates = Array.from(
            new Set([
              ...activePreset.models,
              ...this._expressFetchedModels,
              ...(settings.vector_db_api_model?.trim()
                ? [settings.vector_db_api_model.trim()]
                : []),
            ])
          );
          const mSel = metaBar.createEl("select", {
            cls: "pf-embed-model-select",
            attr: {
              "aria-label": isZh ? "选择向量模型" : "Embedding model",
              "data-pf-testid": "express-embed-model-select",
            },
          }) as HTMLSelectElement;
          const activeModel =
            (settings.vector_db_api_model || "").trim() || activePreset.model;
          for (const mName of modelCandidates) {
            const opt = mSel.createEl("option", {
              text: mName,
              attr: { value: mName },
            }) as HTMLOptionElement;
            opt.selected = mName === activeModel;
          }
          mSel.addEventListener("change", () => {
            settings.vector_db_api_model = mSel.value;
            const cli = this.getClient() as unknown as {
              configSet?: (k: string, v: string) => Promise<unknown>;
            };
            void cli
              ?.configSet?.("vector_db_api_model", mSel.value)
              ?.catch(() => undefined);
            void this.plugin.saveSettings?.();
          });
        }

        // Row 3: Adaptive Action Area
        if (curP === "ollama") {
          const olRow = pane.createDiv({ cls: "pf-secret-input-row" });
          const probeBtn = olRow.createEl("button", {
            cls: "pf-btn pf-btn-secondary",
            text: isZh ? "检测本机模型" : "Detect Local Models",
            attr: { type: "button", "data-pf-testid": "express-ollama-probe" },
          });
          const testOlBtn = olRow.createEl("button", {
            cls: "pf-btn pf-btn-secondary",
            text: isZh ? "测试连接" : "Test Connection",
            attr: { type: "button", "data-pf-testid": "express-embed-save" },
          });
          const olMsg = olRow.createEl("span", { cls: "pf-test-conn-status" });
          const pullHint = pane.createDiv({ cls: "pf-secret-input-row" });
          pullHint.style.display = "none";

          probeBtn.addEventListener("click", () => {
            probeBtn.disabled = true;
            olMsg.className = "pf-test-conn-status";
            olMsg.textContent = isZh
              ? "正在扫描本机 11434 端口…"
              : "Probing localhost:11434…";
            void this.getClient()
              .embedListModels("http://127.0.0.1:11434/v1")
              .then((res) => {
                if (!res.reachable) {
                  olMsg.className = "pf-test-conn-status is-err";
                  olMsg.textContent = isZh
                    ? "未检测到运行中的 Ollama"
                    : "Ollama is not running";
                  return;
                }
                if (res.embedding_models.length > 0) {
                  this._expressFetchedModels = res.embedding_models;
                  settings.vector_db_api_base = "http://127.0.0.1:11434/v1";
                  if (!settings.vector_db_api_model) {
                    settings.vector_db_api_model = res.embedding_models[0];
                  }
                  olMsg.className = "pf-test-conn-status is-ok";
                  olMsg.textContent = isZh
                    ? `✓ 已检测到 ${res.embedding_models.length} 个向量模型`
                    : `✓ Found ${res.embedding_models.length} embedding models`;
                  pullHint.style.display = "none";
                  void this.plugin.saveSettings();
                  this.display();
                } else {
                  olMsg.className = "pf-test-conn-status is-err";
                  olMsg.textContent = isZh
                    ? "Ollama 已运行，但尚未拉取向量模型"
                    : "Ollama running, no embedding model installed";
                  pullHint.textContent = "";
                  pullHint.style.display = "flex";
                  pullHint.createEl("span", {
                    cls: "pf-embed-inline-hint",
                    text: isZh
                      ? "终端执行一行即可安装："
                      : "Run once in terminal:",
                  });
                  const copyPull = pullHint.createEl("button", {
                    cls: "pf-btn pf-btn-ghost",
                    text: isZh
                      ? "复制 ollama pull bge-m3"
                      : "Copy ollama pull bge-m3",
                    attr: { type: "button" },
                  });
                  copyPull.addEventListener("click", () => {
                    void navigator.clipboard?.writeText?.("ollama pull bge-m3");
                    new Notice(
                      isZh ? "已复制 ollama pull bge-m3" : "Copied command"
                    );
                  });
                }
              })
              .catch(() => {
                olMsg.className = "pf-test-conn-status is-err";
                olMsg.textContent = isZh
                  ? "本机探测失败"
                  : "Local probe failed";
              })
              .finally(() => {
                probeBtn.disabled = false;
              });
          });
          testOlBtn.addEventListener("click", () => {
            testOlBtn.disabled = true;
            olMsg.className = "pf-test-conn-status";
            olMsg.textContent = isZh ? "测试中…" : "Testing…";
            void this.getClient()
              .embedTestConnection()
              .then((res) => {
                olMsg.className = "pf-test-conn-status is-ok";
                olMsg.textContent = isZh
                  ? `✓ 已连通 · ${res.model} (${res.latency_ms}ms)`
                  : `✓ Connected · ${res.model} (${res.latency_ms}ms)`;
              })
              .catch((err) => {
                olMsg.className = "pf-test-conn-status is-err";
                olMsg.textContent = formatProviderConnectionError(
                  String(err?.message || err),
                  "embed",
                  isZh
                );
              })
              .finally(() => {
                testOlBtn.disabled = false;
              });
          });
        } else {
          let customBaseIn: HTMLInputElement | null = null;
          let customModelIn: HTMLInputElement | null = null;
          if (curP === "custom") {
            const cGrid = pane.createDiv({ cls: "pf-embed-custom-grid" });
            customBaseIn = cGrid.createEl("input", {
              cls: "pf-setup-input",
              attr: {
                type: "text",
                placeholder: "https://your-gateway/v1",
                "data-pf-testid": "express-embed-custom-base",
              },
            }) as HTMLInputElement;
            customBaseIn.value = settings.vector_db_api_base || "";
            customBaseIn.addEventListener("change", () => {
              this._setVectorDbConfig("vector_db_api_base", customBaseIn!);
            });

            const mRow = cGrid.createDiv({ cls: "pf-embed-model-row" });
            customModelIn = mRow.createEl("input", {
              cls: "pf-setup-input",
              attr: {
                type: "text",
                placeholder: isZh ? "模型名（如 BAAI/bge-m3）" : "Model name",
                "data-pf-testid": "express-embed-custom-model",
              },
            }) as HTMLInputElement;
            customModelIn.value = settings.vector_db_api_model || "";
            customModelIn.addEventListener("change", () => {
              this._setVectorDbConfig("vector_db_api_model", customModelIn!);
            });
            const fetchBtn = mRow.createEl("button", {
              cls: "pf-btn pf-btn-secondary",
              text: isZh ? "拉取模型" : "Fetch",
              attr: {
                type: "button",
                "data-pf-testid": "express-embed-fetch-models",
              },
            });
            const fetchedSlot = pane.createDiv({
              cls: "pf-embed-fetched-chips",
            });
            fetchedSlot.style.display = "none";
            fetchBtn.addEventListener("click", () => {
              const targetBase = customBaseIn?.value.trim();
              if (!targetBase) return;
              fetchBtn.disabled = true;
              fetchedSlot.style.display = "flex";
              fetchedSlot.textContent = isZh ? "拉取中…" : "Fetching…";
              void this.getClient()
                .embedListModels(targetBase)
                .then((res) => {
                  fetchedSlot.textContent = "";
                  const picks =
                    res.embedding_models.length > 0
                      ? res.embedding_models
                      : res.models;
                  if (!res.reachable || picks.length === 0) {
                    fetchedSlot.createEl("span", {
                      cls: "pf-embed-inline-hint",
                      text: isZh
                        ? "该网关未返回模型列表，请在上方直接手填。"
                        : "Gateway returned no list; type model name above.",
                    });
                    return;
                  }
                  for (const id of picks.slice(0, 8)) {
                    const mChip = fetchedSlot.createEl("button", {
                      cls: `pf-express-preset-chip${customModelIn?.value.trim() === id ? " is-active" : ""}`,
                      text: id,
                      attr: { type: "button" },
                    });
                    mChip.addEventListener("click", () => {
                      if (customModelIn) {
                        customModelIn.value = id;
                        this._setVectorDbConfig(
                          "vector_db_api_model",
                          customModelIn
                        );
                      }
                    });
                  }
                })
                .catch(() => {
                  fetchedSlot.textContent = "";
                  fetchedSlot.createEl("span", {
                    cls: "pf-embed-inline-hint",
                    text: isZh
                      ? "拉取失败，可直接手填模型名。"
                      : "Fetch failed; type manually.",
                  });
                })
                .finally(() => {
                  fetchBtn.disabled = false;
                });
            });
          }

          const memRow = pane.createDiv({ cls: "pf-secret-input-row" });
          const memKeyIn = appendSecretInput(
            memRow,
            settings._vector_db_configured
              ? t("settings_secret_saved_placeholder")
              : t("settings_embed_key_placeholder"),
            "express-embed"
          );
          const memBtn = memRow.createEl("button", {
            cls: "pf-btn pf-btn-secondary",
            text: rtReady
              ? isZh
                ? "保存并测试连接"
                : "Save & Test"
              : isZh
                ? "保存密钥"
                : "Save Key",
            attr: { type: "button", "data-pf-testid": "express-embed-save" },
          });
          const memMsg = pane.createEl("span", { cls: "pf-test-conn-status" });
          memBtn.addEventListener("click", () => {
            const val = memKeyIn.value.trim();
            memBtn.disabled = true;
            memMsg.className = "pf-test-conn-status";
            memMsg.textContent = rtReady
              ? isZh
                ? "测试中…"
                : "Testing…"
              : isZh
                ? "保存中…"
                : "Saving…";
            void (
              val
                ? this._storeSetupSecret("vector-db-api-key", val)
                : Promise.resolve(true)
            )
              .then((saved) => {
                if (!saved) {
                  throw new Error(isZh ? "保存失败" : "Save failed");
                }
                if (val) memKeyIn.value = "";
                if (!rtReady) {
                  memMsg.className = "pf-test-conn-status is-ok";
                  memMsg.textContent = isZh
                    ? "✓ 已安全保存，导入时自动生效"
                    : "✓ Saved securely; active after setup";
                  return;
                }
                return this.getClient()
                  .embedTestConnection()
                  .then((res) => {
                    memMsg.className = "pf-test-conn-status is-ok";
                    memMsg.textContent = isZh
                      ? `✓ 已连通 · ${res.model} (${res.latency_ms}ms)`
                      : `✓ Connected · ${res.model} (${res.latency_ms}ms)`;
                  });
              })
              .catch((err) => {
                memMsg.className = "pf-test-conn-status is-err";
                memMsg.textContent = formatProviderConnectionError(
                  String(err?.message || err),
                  "embed",
                  isZh
                );
              })
              .finally(() => {
                memBtn.disabled = false;
              });
          });
        }
      } else {
        const lblRow = pane.createDiv({ cls: "pf-express-label-row" });
        lblRow.createEl("strong", {
          text: isZh
            ? "EasyScholar · 精确获取 JCR 影响因子与中科院分区（不填默认使用开源指标 ≈）"
            : "EasyScholar · Exact JCR Impact Factor & Partitions",
        });
        lblRow.createEl("a", {
          cls: "pf-express-help-link",
          text: isZh ? "前往 EasyScholar ↗" : "Visit EasyScholar ↗",
          attr: {
            href: "https://www.easyscholar.cc/",
            target: "_blank",
            rel: "noopener noreferrer",
          },
        });
        const esRow = pane.createDiv({ cls: "pf-secret-input-row" });
        const esKeyIn = appendSecretInput(
          esRow,
          settings._easyscholar_configured
            ? t("settings_secret_saved_placeholder")
            : t("settings_easyscholar_placeholder"),
          "express-es"
        );
        const esSaveBtn = esRow.createEl("button", {
          cls: "pf-btn pf-btn-secondary",
          text: t("config_save"),
          attr: { type: "button", "data-pf-testid": "express-es-save" },
        });
        const esMsg = pane.createEl("span", { cls: "pf-test-conn-status" });
        esSaveBtn.addEventListener("click", () => {
          const val = esKeyIn.value.trim();
          if (!val) return;
          esSaveBtn.disabled = true;
          void this.getClient()
            .authSetSecret("easyscholar", val)
            .then(() => {
              settings._easyscholar_configured = true;
              settings.journal_metrics_mode = "auto";
              esKeyIn.value = "";
              esMsg.className = "pf-test-conn-status is-ok";
              esMsg.textContent = "✓ " + t("settings_saved_ok");
              void this.plugin.saveSettings();
            })
            .catch(() => {
              esMsg.className = "pf-test-conn-status is-err";
              esMsg.textContent = t("settings_save_failed");
            })
            .finally(() => {
              esSaveBtn.disabled = false;
            });
        });
      }
    }

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

    // Inline 1-line proxy recovery bar (only shown when download/setup fails!)
    if (this._setupOperation === "failed" && !rtReady) {
      const proxyBox = wrapper.createDiv({
        cls: "pf-express-card pf-proxy-recovery",
        attr: { "data-pf-testid": "express-proxy-recovery" },
      });
      proxyBox.createEl("p", {
        cls: "setting-item-description",
        text: isZh
          ? "校园网 / 医院内网下载受限？可填写本地代理地址（如 http://127.0.0.1:7890）后重试："
          : "Network restricted? Enter a local proxy URL (e.g. http://127.0.0.1:7890) and retry:",
      });
      const proxyRow = proxyBox.createDiv({ cls: "pf-setup-path-row" });
      const proxyIn = proxyRow.createEl("input", {
        cls: "pf-setup-input",
        attr: {
          type: "text",
          placeholder: "http://127.0.0.1:7890",
          "data-pf-testid": "express-proxy-input",
        },
      }) as HTMLInputElement;
      proxyIn.value = this._setupProxyUrl;
      proxyIn.addEventListener("input", () => {
        this._setupProxyUrl = proxyIn.value;
      });
      renderActionButton(proxyRow, {
        label: isZh ? "使用代理重试安装" : "Retry with Proxy",
        variant: "secondary",
        onClick: () => {
          this._setupProxyUrl = proxyIn.value.trim();
          this._launchRuntimeInstaller(action, { autoContinueSetup: true });
        },
      });
    }

    // ── Sticky Action Bar (Linear / Raycast style) ──
    const footer = wrapper.createDiv({ cls: "pf-express-footer" });
    footer.createEl("span", {
      cls: "pf-express-footer-summary",
      text: zoteroReady
        ? isZh
          ? `只读导入${paperCnt ? ` ${paperCnt} 篇` : ""}文献 → ${litTargetDir}/ · 免费功能立即生效`
          : `Read-only import → ${litTargetDir}/ · Free features ready right away`
        : isZh
          ? "先在上一步确认 Zotero 目录即可开始导入"
          : "Confirm your Zotero folder above to start importing",
    });
    const fActions = footer.createDiv({ cls: "pf-express-footer-actions" });
    renderActionButton(fActions, {
      label: isZh ? "稍后配置，先逛逛" : t("setup_nav_later"),
      variant: "ghost",
      disabled:
        this._setupOperation === "running" ||
        expressRuntimeInProgress ||
        isImporting,
      onClick: () => this._goHome(),
    });
    const rtStepTag =
      liveRuntime && liveRuntime.total > 0 && liveRuntime.current > 0
        ? ` (${liveRuntime.current}/${liveRuntime.total})`
        : "";
    const syncStepTag =
      liveSync && liveSync.total > 0 && liveSync.current > 0
        ? ` (${liveSync.current}/${liveSync.total})`
        : "";
    let primaryLabel: string;
    if (daemonUpdating) {
      primaryLabel = isZh ? "正在更新本地服务…" : "Updating local service…";
    } else if (rtChecking) {
      primaryLabel = isZh ? "正在检测运行环境…" : "Checking engine…";
    } else if (expressRuntimeInProgress) {
      primaryLabel = this._autoContinueSetupAfterInstall
        ? isZh
          ? `正在安装引擎${rtStepTag}，完成后自动导入…`
          : `Installing engine${rtStepTag}, then importing…`
        : isZh
          ? `正在安装 PaperForge 引擎${rtStepTag}…`
          : `Installing PaperForge engine${rtStepTag}…`;
    } else if (isImporting) {
      primaryLabel =
        this._setupPhase === "configuring"
          ? isZh
            ? "正在写入文献库配置…"
            : "Configuring library…"
          : isZh
            ? `正在导入文献库${syncStepTag}…`
            : `Importing library${syncStepTag}…`;
    } else if (!rtReady) {
      if (action === "update") {
        primaryLabel = isZh
          ? `更新引擎并导入${paperCnt ? ` ${paperCnt} 篇` : ""}文献`
          : `Update Engine & Import${paperCnt ? ` ${paperCnt}` : ""} Papers`;
      } else {
        primaryLabel = isZh
          ? `安装引擎并导入${paperCnt ? ` ${paperCnt} 篇` : ""}文献`
          : `Install Engine & Import${paperCnt ? ` ${paperCnt}` : ""} Papers`;
      }
    } else {
      primaryLabel = isZh
        ? `立即导入${paperCnt ? ` ${paperCnt} 篇` : ""}文献并开始使用`
        : `Import${paperCnt ? ` ${paperCnt}` : ""} Papers & Start`;
    }
    renderActionButton(fActions, {
      label: primaryLabel,
      disabled: ctaBusy,
      onClick: () => {
        if (ctaBusy) return;
        if (!rtReady) {
          void this.plugin.saveSettings();
          this._launchRuntimeInstaller(action, { autoContinueSetup: true });
          return;
        }
        this._applyLibraryConfiguration({ autoCompleteOnSuccess: true });
      },
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
      const stageRuntimeInProgress =
        this._syncRuntimePollFromBackground() ||
        Boolean(this._runtimePollTimer);
      if (stageRuntimeInProgress) {
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
        // Keep auto-detected Zotero path in memory only until the user
        // confirms setup/save so unconfigured vaults never leak a configured path.
        this._zoteroDetectData = res;
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
                  ? t("settings_zotero_papers_count").replace(
                      "{count}",
                      String(this._zoteroDetectData.total_papers)
                    )
                  : "")
              : step.id === "scope"
                ? useLegacyBbt
                  ? bbtFiles.join(", ")
                  : (settings.domain_mode === "unified"
                      ? t("settings_zotero_mode_flat")
                      : t("settings_zotero_mode_topic")) +
                    (Array.isArray(settings.zotero_selected_collections) &&
                    settings.zotero_selected_collections.length > 0
                      ? t("settings_zotero_selected_cols").replace(
                          "{count}",
                          String(settings.zotero_selected_collections.length)
                        )
                      : t("settings_zotero_all_cols"))
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
        input.value =
          settings.zotero_data_dir ||
          (this._zoteroDetectData?.found
            ? this._zoteroDetectData.zotero_dir || ""
            : "");
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
                ? t("settings_zotero_scanning_cols")
                : t("settings_zotero_sync_all_hint"),
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
                ? t("settings_secret_saved_placeholder")
                : t("settings_easyscholar_placeholder"),
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
                esMsg.textContent = "✓ " + t("settings_saved_ok");
                void this.plugin.saveSettings();
              })
              .catch(() => {
                esMsg.className = "pf-test-conn-status is-err";
                esMsg.textContent = t("settings_save_failed");
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
            ? t("settings_zotero_switch_sqlite")
            : t("settings_zotero_switch_bbt"),
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
      if (r.migrated.length) {
        results.push(
          t("migrate_secret_migrated_ok").replace("{kind}", kind.toUpperCase())
        );
      }
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
        new Notice(
          t("settings_config_set_failed")
            .replace("{key}", key)
            .replace("{detail}", formatHumanError(error)),
          6000
        );
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
      const agentPresence =
        opt.id === "agent" ? this._getEffectiveAgentPresence() : null;
      const configured =
        opt.id === "ocr"
          ? !!this.plugin.settings._paddleocr_configured
          : opt.id === "memory"
            ? !!this.plugin.settings._vector_db_configured
            : agentPresence?.state === "connected" ||
              agentPresence?.state === "ready";
      // The chip states what the user must do next, not just "configured":
      // a green "not configured" reads as done and is why people skip it.
      const needsSecret = opt.id === "ocr" || opt.id === "memory";
      const agentStateCls =
        agentPresence?.state === "ready" ||
        agentPresence?.state === "connected" ||
        (agentPresence?.state === "configured_idle" &&
          Boolean(agentPresence?.has_connected_before))
          ? "pf-setup-optional-state--ok"
          : agentPresence?.state === "configured_idle"
            ? "pf-setup-optional-state--info"
            : "pf-setup-optional-state--neutral";
      const status = copy.createEl("span", {
        cls:
          "pf-setup-optional-state " +
          (opt.id === "agent"
            ? agentStateCls
            : needsSecret && !configured
              ? "pf-setup-optional-state--warn"
              : "pf-setup-optional-state--ok"),
        text:
          opt.id === "agent" && agentPresence
            ? this._formatAgentPresenceBadgeText(agentPresence, false)
            : configured
              ? t("config_configured")
              : t("setup_optional_needs_key"),
        attr:
          opt.id === "agent" && agentPresence
            ? {
                "data-pf-testid": "setup-optional-agent-state",
                "data-agent-state": agentPresence.state,
              }
            : undefined,
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
          text: t("settings_ocr_adv_endpoint"),
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
          text: t("settings_ocr_save_test_btn"),
          attr: { type: "button" },
        });
        const testOcrMsg = ocrSaveFooter.createEl("span", {
          cls: "pf-test-conn-status",
        });
        save.addEventListener("click", () => {
          void commitOcrKey();
        });
        testOcrBtn.addEventListener("click", () => {
          const isZhNow = getActiveLang(this.app) === "zh";
          testOcrBtn.disabled = true;
          testOcrMsg.textContent = t("settings_testing");
          void commitOcrKey()
            .then(() => this.getClient().ocrTestConnection())
            .then((res) => {
              if (res?.passed) {
                testOcrMsg.className = "pf-test-conn-status is-ok";
                testOcrMsg.textContent = "✓ " + t("settings_ocr_test_ok");
              } else {
                testOcrMsg.className = "pf-test-conn-status is-err";
                testOcrMsg.textContent =
                  "✗ " +
                  (res?.error
                    ? formatProviderConnectionError(res.error, "ocr", isZhNow)
                    : t("settings_ocr_test_verify_failed"));
              }
            })
            .catch((err) => {
              testOcrMsg.className = "pf-test-conn-status is-err";
              testOcrMsg.textContent =
                "✗ " +
                formatProviderConnectionError(
                  String(err?.message || err),
                  "ocr",
                  isZhNow
                );
            })
            .finally(() => {
              testOcrBtn.disabled = false;
            });
        });
      } else if (opt.id === "memory") {
        config.createEl("label", {
          text: t("settings_embed_select_provider"),
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
          text: t("settings_embed_adv_custom"),
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
          text: t("settings_embed_save_test_btn"),
          attr: { type: "button" },
        });
        const testMemMsg = memSaveFooter.createEl("span", {
          cls: "pf-test-conn-status",
        });
        save.addEventListener("click", () => {
          void commitMemKey();
        });
        testMemBtn.addEventListener("click", () => {
          const isZhNow = getActiveLang(this.app) === "zh";
          testMemBtn.disabled = true;
          testMemMsg.textContent = t("settings_probing");
          void commitMemKey()
            .then(() => this.getClient().embedTestConnection())
            .then((res) => {
              testMemMsg.className = "pf-test-conn-status is-ok";
              testMemMsg.textContent =
                "✓ " +
                t("settings_embed_connected")
                  .replace("{model}", String(res.model))
                  .replace("{dim}", String(res.dimension))
                  .replace("{ms}", String(res.latency_ms));
            })
            .catch((err) => {
              testMemMsg.className = "pf-test-conn-status is-err";
              testMemMsg.textContent =
                "✗ " +
                formatProviderConnectionError(
                  String(err?.message || err),
                  "embed",
                  isZhNow
                );
            })
            .finally(() => {
              testMemBtn.disabled = false;
            });
        });
      } else {
        const isZhOpt = (
          this.plugin.settings.language || langFromApp(this.app)
        ).startsWith("zh");
        const vaultBase = this._getVaultBasePath();
        const curPlatform = this.plugin.settings.agent_platform || "opencode";
        this._renderAgentOnboardingBox(config, vaultBase, curPlatform, isZhOpt);
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
                  t("settings_config_set_failed")
                    .replace("{key}", "agent_platform")
                    .replace("{detail}", formatHumanError(e)),
                  6000
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
    this._isOpen = false;
    this._agentPresenceProbedThisSession = false;
    if (this._agentPresenceWsRef) {
      const ws = (
        this.app as unknown as {
          workspace?: {
            offref?: (ref: unknown) => void;
            off?: (ev: string, ref: unknown) => void;
          };
        }
      )?.workspace;
      if (typeof ws?.offref === "function") {
        ws.offref(this._agentPresenceWsRef);
      } else if (typeof ws?.off === "function") {
        ws.off("paperforge:agent-presence-changed", this._agentPresenceWsRef);
      }
      this._agentPresenceWsRef = null;
    }
    this._setupJourneyDismissedForSession = false;
    this._attemptedProbes.delete("help");
    if (this._saveTimeout) {
      clearTimeout(this._saveTimeout);
      this._saveTimeout = null;
    }
    if (this._runtimePollTimer) {
      clearInterval(this._runtimePollTimer);
      this._runtimePollTimer = null;
    }
    if (this._liveActivityTimer) {
      clearInterval(this._liveActivityTimer);
      this._liveActivityTimer = null;
    }
    this._liveElapsedEl = null;
    this._liveElapsedStartedAt = null;
    if (this._runtimeStatusWatchdog) {
      clearTimeout(this._runtimeStatusWatchdog);
      this._runtimeStatusWatchdog = null;
    }
    super.hide();
  }
}
