import { PluginSettingTab, App, Setting, Notice, setTooltip } from "obsidian";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { execFile, execFileSync, spawn, exec } from "child_process";
import { t, setLanguage } from "./i18n";
import { PaperForgeSettings, ProbeEnvelope, CapabilityModule, CAPABILITY_MODULES, createUnknownEnvelope, createStaleEnvelope, createInvalidEnvelope, isValidEnvelope, isEnvelopeStale, isReadyEnvelope, probeAction, setupAction, validatePersistedEnvelopes, classifyCapabilityAction } from "./constants";
import releaseNotesData from "./release-notes.json";
import {
  resolvePythonExecutable,
  buildRuntimeInstallCommand,
  paperforgeEnrichedEnv,
  scanBbtUnderProfiles,
  scanBbtDirectChildren,
  runSubprocess,
} from "./services/python-bridge";
import {
  resolveVaultPaths,
  getMemoryRuntime,
  getVectorRuntime,
  getRuntimeHealth,
  isMemoryReady,
  isVectorReady,
  getMemoryStatusText,
  getVectorStatusText,
  getCachedPython,
} from "./services/memory-state";

import {
  PaperForgeOcrPrivacyModal,
  PaperForgeSetupModal,
  checkOrphanState,
} from "./views/modals";
import {
  categorizeMaintenanceRow,
  buildMaintenanceSummary,
  maintenanceActionForRow,
  maintenanceActionRequiresConfirmation,
  MaintenanceDisplayRow,
  MaintenanceCache,
  readMaintenanceCache,
  refreshMaintenanceData,
} from "./services/ocr-maintenance-ui";
import {
  ManagedRuntime,
  runtimeActionsForHealth,
  resolveRuntimeCommand,
  type RuntimeHealth,
  type RuntimeUiAction,
} from "./services/managed-runtime";
import { getDisclosureState, toggleDisclosureState } from "./utils/disclosure";
import { processProgressChunk } from "./services/progress-parser";


// ── Interface ──

interface ISettingPlugin {
  settings: PaperForgeSettings;
  saveSettings(): Promise<void>;
  loadSettings(): Promise<void>;
  manifest: { version: string };
  readPaperforgeJson(): Record<string, string>;
  savePaperforgeJson(pc: Record<string, string>): void;
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
  /** Tracks which modules are currently being probed. */
  private _probing: Set<string> = new Set();
  /** Modules that have already been auto-probed (prevents endless re-probe). */
  private _attemptedProbes: Set<string> = new Set();
  /** Currently active sub-view within the Setup tab. */
  _setupView: "overview" | "module-detail" = "overview";
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

  constructor(app: App, plugin: ISettingPlugin) {
    super(app, plugin as any);
    this.plugin = plugin;
  }

  /** Reload path config from paperforge.json */
  _refreshPfConfig() {
    this._pfConfig = this.plugin.readPaperforgeJson();
  }

  display() {
    const { containerEl } = this;
    containerEl.empty();
    this._refreshPfConfig();
    this._initCapabilityState();
    this._applyStaleTolerance();

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
                .paperforge-modal-subtitle { color: var(--text-muted); font-size: 13px; margin-bottom: 12px; }
                .paperforge-modal-item { font-size: 13px; margin-left: 8px; color: var(--text-muted); }
            `;
      document.head.appendChild(style);
    }

    // --- Tab bar ---
    const tabBar = containerEl.createDiv({ cls: "paperforge-settings-tabs" });
    const tabs = [
      { id: "overview", label: t("tab_overview") || "Overview" },
      { id: "module-detail", label: t("tab_modules") || "Module Detail" },
      { id: "maintenance", label: t("tab_maintenance") || "Maintenance" },
      { id: "help", label: t("tab_help") || "Help" },
    ];
    const tabContents: Record<string, HTMLDivElement> = {};

    tabs.forEach((tab) => {
      const btn = tabBar.createEl("button", {
        cls:
          "paperforge-settings-tab" +
          (tab.id === this.activeTab ? " paperforge-settings-tab--active" : ""),
        text: tab.label,
      });
      btn.addEventListener("click", () => {
        this.activeTab = tab.id;
        this.display();
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

    // --- Render active tab ---
    if (this.activeTab === "overview") {
      this._renderOverviewTab(tabContents.overview);
    } else if (this.activeTab === "module-detail") {
      this._renderModuleDetailTab(tabContents["module-detail"]);
    } else if (this.activeTab === "maintenance") {
      this._renderMaintenanceTab(tabContents.maintenance);
    } else if (this.activeTab === "help") {
      this._renderHelpTab(tabContents.help);
    }
 
     // Focus restoration after render (Issue #77)
     // Do NOT consume _focusTargetId while Help tab is active —
     // focus targets for Overview must survive until Overview renders again.
     if (this._focusTargetId && this.activeTab !== "help") {
       const target = containerEl.querySelector<HTMLElement>(this._focusTargetId);
       if (target) {
         try { target.focus(); } catch {}
         this._focusTargetId = null;
       }
     }
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

    // ── Advanced: Memory + Vector (preserved from old Features tab) ──
    this._renderAdvancedSection(containerEl);

    // Auto-probe never-probed/migrated modules once per session
    for (const mod of CAPABILITY_MODULES) {
      const env = this._capabilityState?.[mod];
      if (env && env.capability_state === "unknown" && env.updated_at === new Date(0).toISOString() && !this._attemptedProbes.has(mod)) {
        this._attemptedProbes.add(mod);
        if (mod !== "maintenance") {
          this._probeModule(mod);
        }
      }
    }

  }

  /** Render the Advanced collapsible section with Memory + Vector (from old Features tab). */
  _renderAdvancedSection(containerEl: HTMLElement): void {
    if (this._advCollapsed === undefined) this._advCollapsed = true;
    const advHeader = containerEl.createEl("div", {
      cls: "paperforge-collapsible-header",
    });
    const advArrow = advHeader.createEl("span", {
      text: "\u25B6",
      cls: "paperforge-collapsible-arrow",
    });
    advArrow.style.transform = this._advCollapsed
      ? "rotate(0deg)"
      : "rotate(90deg)";
    const advTitle = advHeader.createEl("span", {
      cls: "paperforge-collapsible-title",
      text: "Advanced",
    });
    const advSub = advHeader.createEl("span", {
      cls: "paperforge-collapsible-sub",
      text: "Memory + Vector DB + Embedding",
    });

    const advContent = containerEl.createEl("div", {
      cls: "paperforge-collapsible-content",
    });
    advContent.style.display = this._advCollapsed ? "none" : "";

    advHeader.addEventListener("click", () => {
      this._advCollapsed = !this._advCollapsed;
      advContent.style.display = this._advCollapsed ? "none" : "";
      advArrow.style.transform = this._advCollapsed
        ? "rotate(0deg)"
        : "rotate(90deg)";
    });

    // Memory Layer section
    advContent.createEl("h4", { text: "Memory Layer" });
    const memoryDescEl = advContent.createEl("div", {
      cls: "paperforge-desc-box",
    });
    memoryDescEl.setText(t("feat_memory_desc"));

    const statusRow = advContent.createEl("div", {
      cls: "paperforge-memory-status",
    });

    const vp = (this.app.vault.adapter as unknown as Record<string, unknown>).basePath as string;

    if (this.plugin._lastSyncTime && !this._lastSyncTime) {
      this._lastSyncTime = this.plugin._lastSyncTime;
    }

    if (this._memoryStatusText === null) {
      this._memoryStatusText = getMemoryStatusText(vp);
    }
    this._renderMemoryStatusText(
      statusRow,
      this._memoryStatusText,
      this._lastSyncTime
    );

    this._renderVectorSection(advContent);
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
    this._managedRuntime = new ManagedRuntime({
      version: this.plugin.manifest.version,
    });
    return this._managedRuntime;
  }

  /**
   * Resolve python command via managed runtime first, falling back to
   * legacy getCachedPython adapter. Returns null when neither available.
   * Issues Release-N warning on legacy fallback.
   */
  private _resolveRuntimeCommand(vp: string): { path: string; args: string[] } | null {
    const run = resolveRuntimeCommand(this._ensureManagedRuntime().current());
    if (run) {
      return { path: run.command, args: [...run.args] };
    }
    // Release N: legacy fallback
    console.warn(
      "[PaperForge] Release N: Managed runtime not ready (cold/stale), falling back to legacy resolver"
    );
    const py = getCachedPython(vp, this.plugin.settings);
    if (!py.path) return null;
    return { path: py.path, args: py.extraArgs };
  }

  /** Render the Installation detail view (Issue #77). */
  _renderInstallationDetail(containerEl: HTMLElement): void {
    // ── Back button ──
    const backBtn = containerEl.createEl("button", {
      cls: "pf-back-btn",
      text: t("btn_back_to_overview"),
    });
    backBtn.addEventListener("click", () => {
      this.activeTab = "overview";
      this._selectedDetailModule = "";
      this._focusTargetId = "button.pf-open-module-btn[data-module=installation]";
      this.display();
    });

    // ── Heading ──
    const heading = containerEl.createEl("h2", {
      cls: "pf-installation-detail-heading",
      text: t("installation_detail_heading") || "Installation Details",
      attr: { id: "pf-installation-detail-heading", tabindex: "-1" },
    });

    // ── Module detail selector (only Installation until #78) ──
    const detailModules: { id: string; labelKey: string; disabled: boolean }[] = [
      { id: "installation", labelKey: "md_select_installation", disabled: false },
    ];
    const selector = containerEl.createEl("div", { cls: "pf-module-detail-selector" });
    for (const dm of detailModules) {
      const btn = selector.createEl("button", {
        cls: "pf-module-detail-btn"
          + (dm.id === "installation" ? " pf-module-detail-btn--active" : "")
          + (dm.disabled ? " pf-module-detail-btn--disabled" : ""),
        text: t(dm.labelKey),
      });
      if (dm.disabled) btn.disabled = true;
    }

    // ── Backend envelope display (same envelope as overview card) ──
    const envelopes: Record<string, ProbeEnvelope> = this._capabilityState ?? {};
    const mod: CapabilityModule = "installation";
    const env: ProbeEnvelope = envelopes[mod] ?? createUnknownEnvelope(mod);
    const sevClass: string = this._sevClass(env.severity);
    const isReady: boolean = isReadyEnvelope(env);

    // Minimal envelope summary row
    const summaryRow = containerEl.createEl("div", { cls: "pf-cc-card", attr: { style: "margin-bottom: 12px;" } });
    const summaryHeader = summaryRow.createEl("div", { cls: "pf-cc-card-header" });
    summaryHeader.createEl("span", { cls: "pf-cc-card-name", text: t("cc_module_installation") });
    summaryHeader.createEl("span", {
      cls: `pf-cc-card-badge pf-cc-card-badge--${sevClass}`,
      text: t(this._ccBadgeKey(env, mod)),
    });
    const l10nReason = this._localizeReason(env.reason.code, "installation");
    summaryRow.createEl("div", { cls: "pf-cc-card-reason", text: l10nReason ?? env.reason.text });

    // Action button (same logic as overview card — setup opens wizard, else probe)
    if (env.action.primary && !isReady) {
      const action = classifyCapabilityAction(env);
      const isCta = action.kind === "setup";
      const btnCls = isCta ? "pf-cc-card-action pf-cc-card-action--primary" : "pf-cc-card-action";
      const actionBtn = summaryRow.createEl("button", {
        cls: btnCls,
        text: action.label,
      });
      actionBtn.addEventListener("click", () => {
        if (action.kind === "setup") {
          new PaperForgeSetupModal(this.app, this.plugin, () => {
            this._probeModule("installation");
            this._probeModule("help");
          }).open();
        } else {
          this._probeModule(mod);
        }
      });
    }

    // ── ManagedRuntime section ──
    containerEl.createEl("h3", { text: t("managed_runtime_status") });
    const healthCard = containerEl.createEl("div", { cls: "pf-runtime-status-card" });

    // Helper to render runtime actions as buttons
    const renderRuntimeActions = (actions: readonly RuntimeUiAction[], health: RuntimeHealth, busy: boolean) => {
      const actionRow = healthCard.createEl("div", { cls: "pf-runtime-actions" });
      for (const act of actions) {
        const btn = actionRow.createEl("button", {
          cls: "pf-runtime-action-btn",
          text: act.label,
        });
        // Never disable the Stop button — must be reachable when busy
        if (busy && act.verb !== "stop") btn.disabled = true;
        btn.addEventListener("click", async () => {
          // Stop verb: abort the in-flight operation immediately
          if (act.verb === "stop") {
            const controller = this._runtimeAbortController;
            // Guard: already aborted or already cleaned up → no-op
            if (!controller || controller.signal.aborted) return;
            controller.abort();
            new Notice(t("managed_runtime_action_cancelled"));
            // Do NOT null _runtimeAbortController here — leave it for the
            // original handler's finally block so the AbortSignal is still
            // accessible and unwinding completes normally.
            this.display();
            this._probeModule("installation");
            this._probeModule("help");
            return;
          }

          const rt = this._ensureManagedRuntime();
          const ac = new AbortController();
          this._runtimeAbortController = ac;
          this._runtimeBusy = true;
          new Notice(t("managed_runtime_running"));

          try {
            if (act.verb === "install" || act.verb === "repair" || act.verb === "update") {
              await rt.ensure({ signal: ac.signal, force: act.verb === "update" || act.verb === "repair" });
            } else if (act.verb === "rollback") {
              await rt.ensure({ signal: ac.signal, version: health.previousVersion ?? undefined });
            } else {
              // retry/status → just re-probe
              await rt.status();
            }
            if (!ac.signal.aborted) new Notice(t("managed_runtime_action_complete"));
          } catch (err: unknown) {
            // Cooperative Stop: AbortError means the operation was cancelled — skip "failed" notice
            if ((err as Error)?.name !== "AbortError") {
              const msg: string = err instanceof Error ? err.message : String(err);
              new Notice(t("managed_runtime_action_failed").replace("{error}", msg), 8000);
            }
          } finally {
            this._runtimeAbortController = null;
            this._runtimeBusy = false;
            // Re-probe and re-render
            this._probeModule("installation");
            this._probeModule("help");
            this.display();
          }
        });
      }
    };

    // Sync display with runtime health
    const renderRuntimeHealth = () => {
      healthCard.empty();
      const rt: ManagedRuntime = this._ensureManagedRuntime();
      const health: RuntimeHealth = rt.current();

      // Header row
      const headerRow = healthCard.createEl("div", { cls: "pf-runtime-status-header" });
      headerRow.createEl("div", { cls: "pf-runtime-status-label", text: t("managed_runtime_status") });

      let stateClass: string;
      let stateLabel: string;
      switch (health.state) {
        case "ready":
          stateClass = "ok";
          stateLabel = t("managed_runtime_ok_state");
          break;
        case "not_installed":
          stateClass = "warn";
          stateLabel = t("managed_runtime_not_installed");
          break;
        case "needs_repair":
          stateClass = "warn";
          stateLabel = t("managed_runtime_needs_repair");
          break;
        case "unavailable":
          stateClass = "error";
          stateLabel = t("managed_runtime_unavailable");
          break;
        default:
          stateClass = "unknown";
          stateLabel = t("managed_runtime_unknown_state");
      }
      headerRow.createEl("span", {
        cls: `pf-runtime-status-state pf-runtime-status-state--${stateClass}`,
        text: stateLabel,
      });

      // Version info
      if (health.version) {
        healthCard.createEl("div", { cls: "pf-meta", text: `Python ${health.version}` });
      }
      if (health.pythonPath) {
        healthCard.createEl("div", { cls: "pf-meta", text: health.pythonPath, attr: { style: "word-break: break-all;" } });
      }
      if (health.lastVerifiedAt) {
        healthCard.createEl("div", {
          cls: "pf-meta",
          text: t("managed_runtime_last_verified").replace("{time}", new Date(health.lastVerifiedAt).toLocaleString()),
        });
      }

      // Error info
      if (health.error) {
        healthCard.createEl("div", { cls: "pf-runtime-error", text: `${health.error.code}: ${health.error.message}` });
      }

      // Warnings (e.g. Python 3.10 Release-N deprecation)
      if (health.warnings && health.warnings.length > 0) {
        for (const w of health.warnings) {
          const warnEl = healthCard.createEl("div", { cls: "pf-runtime-warning", text: `\u26A0 ${w.message}` });
          if (w.platformAction) {
            warnEl.createEl("div", { cls: "pf-runtime-warning-action", text: w.platformAction });
          }
        }
      }

      // Error platformAction guidance (e.g. unsupported platform manual setup)
      if (health.error?.platformAction) {
        healthCard.createEl("div", { cls: "pf-runtime-error-action", text: health.error.platformAction });
      }

      // Derived canonical actions
      const actions: readonly RuntimeUiAction[] = runtimeActionsForHealth(health, this.plugin.manifest.version, this._runtimeBusy);
      renderRuntimeActions(actions, health, this._runtimeBusy);
    };

    renderRuntimeHealth();

    // On first visit, status() refreshes health from disk and re-renders
    // canonical actions (Install/Update) without requiring manual Retry.
    // Guard: mock status() may return undefined in test environments.
    const statusPromise = this._ensureManagedRuntime().status();
    if (statusPromise) {
      statusPromise.then(() => {
        if (!containerEl.isConnected) return; // guard detached DOM
        renderRuntimeHealth();
      }).catch(() => { /* best-effort; sync render already shown */ });
    }

    // ── Current Configuration section (Python, path, Zotero controls) ──
    containerEl.createEl("h3", { text: t("section_config") || "Current Configuration" });

    // Copy of setup/runtime/path controls from original setup tab
    const vaultPath: string = this._getVaultBasePath();
    const pyResult: { path: string; source: string } = resolvePythonExecutable(
      vaultPath,
      this.plugin.settings,
      undefined,
      undefined
    ) as unknown as { path: string; source: string };
    const pyPathDesc: string = this._getPythonDesc(pyResult.path, pyResult.source);

    new Setting(containerEl)
      .setName(t("field_python_interp") || "Python Interpreter")
      .setDesc(pyPathDesc)
      .addExtraButton((btn) => {
        btn
          .setIcon("reset")
          .setTooltip("Re-detect")
          .onClick(() => {
            this._pythonInterpDescEl = null;
            this._managedRuntime = null;
            this.display();
          });
      })
      .addButton((button) => {
        button.setButtonText(t("runtime_health_sync") || "Sync Runtime").onClick(() => {
          this._syncRuntime(button);
        });
      });

    // Custom Python path (override)
    const customPathDescEl: HTMLDivElement = containerEl.createEl("div", {
      cls: "setting-item-description",
    });
    this._customPathDescEl = customPathDescEl;

    new Setting(containerEl)
      .setName(t("field_python_custom") || "Custom Python Path")
      .setDesc(t("optional_later"))
      .addText((text) => {
        text
          .setPlaceholder("e.g. C:\\Python311\\python.exe")
          .setValue(this.plugin.settings.python_path || "")
          .onChange((value) => {
            this.plugin.settings.python_path = value.trim();
            this._debouncedSave();
            this._managedRuntime = null;
          });
      })
      .addButton((button) => {
        button.setButtonText(t("feat_verify") || "Validate").onClick(() => {
          this._validatePythonOverride();
        });
      });

    // Zotero data dir
    new Setting(containerEl)
      .setName(t("field_zotero_data") || "Zotero Data Dir")
      .setDesc(t("field_zotero_placeholder"))
      .addText((text) => {
        text
          .setPlaceholder("C:\\Users\\...\\Zotero")
          .setValue(this.plugin.settings.zotero_data_dir || "")
          .onChange((value) => {
            this.plugin.settings.zotero_data_dir = value.trim();
            this._debouncedSave();
          });
      });

    // ── Agent Integration section ──
    containerEl.createEl("h3", { text: t("agent_integration_section") || "Agent Integration" });
    // ── Agent Platform + Skills list (Issue #77) ──
     this._renderSkillsList(containerEl);

    // Focus heading on render
    try {
      heading.focus();
    } catch {
      // ignore focus failure
    }
  }
 
   /** Render Agent Platform selector and skills list (Issue #77). */
   private _renderSkillsList(containerEl: HTMLElement): void {
     const agentPlatforms: Record<string, string> = {
       opencode: "OpenCode",
       claude: "Claude Code",
       codex: "Codex",
       cursor: "Cursor",
       windsurf: "Windsurf",
       github_copilot: "GitHub Copilot",
       gemini: "Gemini CLI",
     };
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
     const selectedPlatform: string = this.plugin.settings.agent_platform || "opencode";
 
     new Setting(containerEl)
       .setName(t("label_agent") || "Agent Platform")
       .setDesc(t("feat_agent_platform_desc"))
       .addDropdown((dropdown) => {
         Object.entries(agentPlatforms).forEach(([key, label]) =>
           dropdown.addOption(key, label)
         );
         dropdown.setValue(selectedPlatform).onChange((value) => {
           this.plugin.settings.agent_platform = value;
           this.plugin.saveSettings();
           this.display();
         });
       })
       .addExtraButton((btn) => {
         btn
           .setIcon("folder")
           .setTooltip("Open skills folder")
           .onClick(() => {
             const dir: string = agentDirs[selectedPlatform] || ".opencode/skills";
             const fullPath: string = path.join(vaultPath, dir);
             if (fs.existsSync(fullPath)) {
               exec(`start "" "${fullPath}"`);
             } else {
               new Notice(`Skills folder not found: ${dir}`);
             }
           });
       });
 
     // Skills section
     containerEl.createEl("h3", { text: "Skills" });
     const skillsDescEl = containerEl.createEl("div", { cls: "paperforge-desc-box" });
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
           if (first && first[1] && first[1] !== ">" && first[1] !== "|-" && first[1] !== "|") {
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
         const disableMatch = content.match(/^disable-model-invocation:\s*(.+)$/m);
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
 
     const skillsBox = containerEl.createEl("div", { cls: "paperforge-skills-box" });
 
     const renderCollapsibleSkills = (label: string, skills: SkillEntry[], isSystem: boolean): void => {
       if (skills.length === 0) return;
       const group = skillsBox.createEl("div", { cls: "paperforge-skills-group" });
       const header = group.createEl("div", { cls: "paperforge-skills-collapse-header" });
       const content = group.createEl("div", { cls: "paperforge-skills-collapse-content" });
       const arrow = header.createEl("span", { text: "\u25BC", cls: "paperforge-skills-arrow" });
       header.createEl("h4", { text: `${label} (${skills.length})`, cls: "paperforge-skills-subheader" });
       skills.forEach((s: SkillEntry) => {
         const nameText = s.name + (s.version ? " v" + s.version : "");
         const sourceLabel = isSystem ? " [system]" : " [user]";
         const descText = s.desc || "";
         const setting = new Setting(content).setName(nameText + sourceLabel).setDesc(descText);
         setting.settingEl.style.opacity = s.disabled ? "0.4" : "1";
         setting.addToggle((toggle) => {
           toggle.setValue(!s.disabled).onChange((value) => {
             const newDisabled = !value;
             const disableMatch = s.content.match(/^disable-model-invocation:\s*(.+)$/m);
             const newContent = disableMatch
               ? s.content.replace(/^disable-model-invocation:\s*.+$/m, `disable-model-invocation: ${newDisabled}`)
               : s.content.replace(/^(---\r?\n)/, `$1disable-model-invocation: ${newDisabled}\n`);
             fs.writeFileSync(s.path, newContent, "utf-8");
             s.disabled = newDisabled;
             s.content = newContent;
             setting.settingEl.style.opacity = s.disabled ? "0.4" : "1";
           });
         });
       });
       const stateKey = isSystem ? "system" : "user";
       const collapsed = this._skillsCollapsed[stateKey] || false;
       if (collapsed) { content.style.display = "none"; arrow.style.transform = "rotate(-90deg)"; }
       header.addEventListener("click", () => {
         const nowCollapsed = content.style.display !== "none";
         if (nowCollapsed) { content.style.display = "none"; arrow.style.transform = "rotate(-90deg)"; }
         else { content.style.display = ""; arrow.style.transform = "rotate(0deg)"; }
         this._skillsCollapsed[stateKey] = content.style.display === "none";
       });
     };
 
     renderCollapsibleSkills("System Skills", systemSkills, true);
     renderCollapsibleSkills("User Skills", userSkills, false);
 
     if (systemSkills.length === 0 && userSkills.length === 0) {
       skillsBox.createEl("p", {
         text: `No skills found in ${agentDirs[selectedPlatform]}. Run setup to deploy skills.`,
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
    } else {
      // Fallback to installation
      this._selectedDetailModule = "installation";
      this._renderInstallationDetail(containerEl);
    }
  }


  /** Render the Library detail view (Issue #78). */
  _renderLibraryDetail(containerEl: HTMLElement): void {
    this._renderModuleDetailShell(containerEl, "library");
    // Library detail surface consumes the shared envelope shell — no duplicate CTA.
  }

  /** Render the OCR detail view (Issue #78). */
  _renderOcrDetail(containerEl: HTMLElement): void {
    this._renderModuleDetailShell(containerEl, "ocr");
    // ── Owner controls: cooperative stop only when _ocrProcess exists ──
    const isRunning = this.plugin._ocrProcess != null;
    if (isRunning) {
      const ctrl = containerEl.createEl("div", { cls: "pf-detail-controls" });
      const stopBtn = ctrl.createEl("button", {
        cls: "mod-warning",
        text: t("ocr_stop_batch") || "Stop OCR batch",
      });
      stopBtn.addEventListener("click", () => {
        const child = this.plugin._ocrProcess as unknown as {
          stdin?: { write: (_: string) => boolean };
          kill?: (_: string) => void;
        };
        if (child?.stdin?.write) {
          child.stdin.write("PAPERFORGE_STOP\n");
          this.plugin._ocrWasStopped = true;
        } else if (child?.kill) {
          child.kill("SIGINT");
        }
      });
      const prog = this.plugin._ocrProgress;
      if (prog && prog.total > 0) {
        ctrl.createEl("span", {
          cls: "pf-detail-progress",
          text: `${prog.current}/${prog.total} papers`,
        });
      }
    }
  }
  /** Render the Memory detail view (Issue #78). */
  _renderMemoryDetail(containerEl: HTMLElement): void {
    this._renderModuleDetailShell(containerEl, "memory");
    // Memory detail surface consumes the shared envelope shell — no duplicate CTA.
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

    // Destructive confirmation from backend envelope
    if (primary.destructive && primary.confirmation_required) {
      const prompt = primary.confirmation_prompt ?? "Proceed?";
      if (!confirm(prompt)) return;
    }

    // Setup/set_config verbs → exact command allowlist
    if ((verb === "setup" || verb === "set_config") && cmd === "paperforge setup") {
      if (mod === "installation" || mod === "library" || mod === "ocr") {
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
      if (verb === "rebuild_derived" && cmd === "paperforge ocr rebuild --all") {
        this._dispatchOcrAction("rebuild");
        return;
      }
      if (verb === "redo" && cmd === "paperforge ocr redo") {
        this._dispatchOcrAction("redo");
        return;
      }
      if (verb === "investigate") {
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
      if ((verb === "run" || verb === "rebuild_index") && cmd === "paperforge memory build") {
        this._dispatchMemoryBuild("build");
        return;
      }
      if (verb === "rebuild_index" && cmd === "paperforge embed build --force") {
        this._dispatchMemoryBuild("embed");
        return;
      }
      if (verb === "restore_backup" && cmd === "paperforge memory restore-backup") {
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
      (t("action_unknown_pair") || "Unknown action: {verb}").replace("{verb}", verb),
      5000,
    );
    this._probeModule(mod);
  }/** Dispatch OCR action with exact CLI args, progress tracking, cooperative stop (Issue #78). */
  _dispatchOcrAction(mode: "run" | "rebuild" | "redo"): void {
    const vp = (this.app.vault.adapter as any).basePath as string;
    const resolved = this._resolveRuntimeCommand(vp);
    if (!resolved) {
      new Notice(t("runtime_not_available") || "No Python runtime available");
      return;
    }

    // Map mode to exact CLI args
    const cliArgs: string[] = mode === "run"
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

    const child = this._callPython(
      cliArgs,
      {
        stream: true,
        onData: (data: unknown) => {
          const text = typeof data === "string" ? data : Buffer.isBuffer(data) ? data.toString("utf-8") : String(data);
          const { events, buffer } = processProgressChunk(text, this.plugin._ocrBuffer ?? "");
          this.plugin._ocrBuffer = buffer;
          for (const ev of events) {
            if (ev.event === "START") {
              if (this.plugin._ocrProgress) {
                this.plugin._ocrProgress.total = ev.total || 1;
              }
              if (envelopes["ocr"]) {
                envelopes["ocr"].activity_progress = { current: 0, total: ev.total || 1 };
              }
            } else if (ev.event === "PROGRESS") {
              this.plugin._ocrProgress = { current: ev.current || 0, total: ev.total || 1, key: ev.key || "" };
              if (envelopes["ocr"]) {
                envelopes["ocr"].activity_progress = { current: ev.current || 0, total: ev.total || 1 };
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
          new Notice("OCR error: " + (err.message || err), 8000);
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
            new Notice(mode === "run" ? "OCR run complete." : mode === "rebuild" ? "OCR rebuild complete." : "OCR redo complete.");
          } else if (code === 130 || this.plugin._ocrWasStopped) {
            this.plugin._ocrWasStopped = false;
            new Notice("OCR batch stopped by user.");
          } else {
            new Notice("OCR operation failed with exit code " + (code ?? "?"), 8000);
          }
          // Terminal re-probe
          this._probeModule("ocr");
          this.display();
        },
      },
    );
    this.plugin._ocrProcess = child;
  }  /** Dispatch memory build: distinct build vs embed modes, overlay activity, terminal re-probe (Issue #78). */
  _dispatchMemoryBuild(kind: "build" | "embed"): void {
    const vp = (this.app.vault.adapter as any).basePath as string;
    // Set activity overlay on Memory
    const envelopes = this._capabilityState ?? {};
    if (envelopes["memory"]) {
      envelopes["memory"].activity_state = "running";
      envelopes["memory"].activity_label = kind === "embed" ? "Building vector index…" : "Building memory…";
    }
    this.display();

    const cliArgs = kind === "embed" ? ["embed", "build", "--force"] : ["memory", "build"];
    const label = kind === "embed" ? "Vector index" : "Memory";

    if (kind === "embed") {
      // Embed build: stream progress
      this.plugin._embedBuffer = "";
      this.plugin._embedProgress = { current: 0, total: 0, key: "" };
      const child = this._callPython(
        cliArgs,
        {
          stream: true,
          onData: (data: unknown) => {
            const text = typeof data === "string" ? data : Buffer.isBuffer(data) ? data.toString("utf-8") : String(data);
            const { events, buffer } = processProgressChunk(text, this.plugin._embedBuffer ?? "");
            this.plugin._embedBuffer = buffer;
            for (const ev of events) {
              if (ev.event === "PROGRESS") {
                this.plugin._embedProgress = { current: ev.current || 0, total: ev.total || 0, key: ev.key || "" };
                if (envelopes["memory"]) {
                  envelopes["memory"].activity_progress = { current: ev.current || 0, total: ev.total || 1 };
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
              new Notice(label + " build failed with exit code " + (code ?? "?"), 8000);
            }
            this._probeModule("memory");
            this.display();
          },
        },
      );
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
              label + " build failed" + (stderr ? ": " + stderr.slice(0, 120) : ""),
              8000,
            );
          }
          this._probeModule("memory");
          this.display();
        },
      });
    }
  }/** Shared module detail shell for Library, OCR, and Memory (Issue #78). */
  _renderModuleDetailShell(containerEl: HTMLElement, mod: CapabilityModule): void {
    const headingKey = mod + "_detail_heading";
    const headingId = "pf-" + mod + "-detail-heading";

    // ── Back button ──
    const backBtn = containerEl.createEl("button", {
      cls: "pf-back-btn",
      text: t("btn_back_to_overview"),
    });
    backBtn.addEventListener("click", () => {
      this.activeTab = "overview";
      this._selectedDetailModule = "";
      this._focusTargetId = "button.pf-open-module-btn[data-module=" + mod + "]";
      this.display();
    });

    // ── Heading ──
    const heading = containerEl.createEl("h2", {
      cls: "pf-module-detail-heading",
      text: t(headingKey) || t("cc_module_" + mod),
      attr: { id: headingId, tabindex: "-1" },
    });

    // ── Module detail selector (all implemented modules) ──
    const detailModules: { id: string; labelKey: string }[] = [
      { id: "installation", labelKey: "md_select_installation" },
      { id: "library", labelKey: "md_select_library" },
      { id: "ocr", labelKey: "md_select_ocr" },
      { id: "memory", labelKey: "md_select_memory" },
    ];
    const selector = containerEl.createEl("div", { cls: "pf-module-detail-selector" });
    for (const dm of detailModules) {
      const btn = selector.createEl("button", {
        cls: "pf-module-detail-btn"
          + (dm.id === mod ? " pf-module-detail-btn--active" : ""),
        text: t(dm.labelKey),
      });
      btn.addEventListener("click", () => {
        this._selectedDetailModule = dm.id;
        this._focusTargetId = dm.id === "installation"
          ? "#pf-installation-detail-heading"
          : "#pf-" + dm.id + "-detail-heading";
        this.display();
      });
    }

    // ── Backend envelope summary card ──
    const envelopes: Record<string, ProbeEnvelope> = this._capabilityState ?? {};
    const env: ProbeEnvelope = envelopes[mod] ?? createUnknownEnvelope(mod);
    const sevClass: string = this._sevClass(env.severity);
    const isReady: boolean = isReadyEnvelope(env);

    const summaryRow = containerEl.createEl("div", { cls: "pf-cc-card pf-module-detail-card" });
    const summaryHeader = summaryRow.createEl("div", { cls: "pf-cc-card-header" });
    summaryHeader.createEl("span", { cls: "pf-cc-card-name", text: t("cc_module_" + mod) });
    summaryHeader.createEl("span", {
      cls: "pf-cc-card-badge pf-cc-card-badge--" + sevClass,
      text: t(this._ccBadgeKey(env, mod)),
    });

    // Activity label
    if (env.activity_state === "running" && env.activity_label) {
      const activityRow = summaryRow.createEl("div", { cls: "pf-cc-card-activity", attr: { "aria-live": "polite" } });
      activityRow.createEl("span", { text: env.activity_label });
      if (env.activity_progress && env.activity_progress.total > 0) {
        const pct = Math.round((env.activity_progress.current / env.activity_progress.total) * 100);
        const bar = activityRow.createEl("div", { cls: "pf-cc-card-progress", attr: { role: "progressbar", "aria-valuenow": String(env.activity_progress.current), "aria-valuemin": "0", "aria-valuemax": String(env.activity_progress.total) } });
        const fill = bar.createEl("div", { cls: "pf-cc-card-progress-fill" });
        fill.style.width = pct + "%";
      }
    }

    const l10nReason = this._localizeReason(env.reason.code, mod);
    summaryRow.createEl("div", { cls: "pf-cc-card-reason", text: l10nReason ?? env.reason.text });

    // Destructive metadata before action
    const primary = env.action?.primary;
    if (primary && !isReady) {
      if (primary.destructive && primary.confirmation_required) {
        const destructiveRow = summaryRow.createEl("div", { cls: "pf-destructive-notice" });
        destructiveRow.createEl("span", { text: primary.destructive_effect ?? "" });
      }

      // Action button — disabled while this module's activity is running
      const isModuleRunning = env.activity_state === "running";
      const action = classifyCapabilityAction(env);
      const actionBtn = summaryRow.createEl("button", {
        cls: "pf-cc-card-action pf-cc-card-action--primary",
        text: action.label,
      });
      if (isModuleRunning) {
        actionBtn.setAttr("disabled", "disabled");
      }
      actionBtn.addEventListener("click", () => {
        if (isModuleRunning) return;
        this._dispatchModuleAction(mod, env);
      });
    }

    // Timestamp and TTL
    const metaRow = summaryRow.createEl("div", { cls: "pf-meta" });
    let dateLabel: string;
    try { dateLabel = new Date(env.updated_at).toLocaleString(); } catch { dateLabel = env.updated_at; }
    metaRow.createEl("span", { text: t("cc_diag_updated") + ": " + dateLabel + " | TTL: " + String(env.ttl_seconds) + "s" });

    // Notices
    if (env.notices && env.notices.length > 0) {
      for (const notice of env.notices) {
        containerEl.createEl("div", {
          cls: "pf-notice pf-notice--" + (notice.level || "info"),
          text: notice.message,
        });
      }
    }

    // Diagnostics disclosure
    const details = summaryRow.createEl("details", { cls: "pf-cc-card-diagnostic" });
    details.createEl("summary", { text: t("cc_diagnostic_toggle") });
    const body = details.createEl("div", { cls: "pf-cc-card-diagnostic-body" });
    const stateLabel = t("cc_state_" + env.capability_state) || env.capability_state;
    const sevLabel = t("cc_severity_" + env.severity) || env.severity;
    const activityLabel = t("cc_activity_" + env.activity_state) || env.activity_state;
    body.createEl("div", { text: t("cc_diag_module") + ": " + env.module });
    body.createEl("div", { text: t("cc_diag_state") + ": " + stateLabel });
    body.createEl("div", { text: t("cc_diag_severity") + ": " + sevLabel });
    body.createEl("div", { text: t("cc_diag_activity") + ": " + activityLabel });
    const reasonRow = body.createEl("div");
    reasonRow.appendText(t("cc_diag_reason") + ": " + (l10nReason ?? env.reason.text) + " ");
    reasonRow.createEl("code", { text: env.reason.code });

    // Focus heading on render
    try {
      heading.focus();
    } catch {
      // ignore focus failure
    }
  }

  /** Render the Help tab (top-level destination with docs + release notes). */
  _renderHelpTab(containerEl: HTMLElement): void {
    const envelopes: Record<string, ProbeEnvelope> = this._capabilityState ?? {};
    const mod: CapabilityModule = "help";
    const env: ProbeEnvelope = envelopes[mod] ?? createUnknownEnvelope(mod);
    const sevClass: string = this._sevClass(env.severity);
    const isReal: boolean = PaperForgeSettingTab._REAL_PROBE.has(mod);

    // Heading
    containerEl.createEl("h2", { text: t("cc_module_help") || "Help & Docs" });

    // Envelope summary card
    const summaryRow = containerEl.createEl("div", { cls: "pf-cc-card", attr: { style: "margin-bottom: 12px;" } });
    const summaryHeader = summaryRow.createEl("div", { cls: "pf-cc-card-header" });
    summaryHeader.createEl("span", { cls: "pf-cc-card-name", text: t("cc_module_help") });
    summaryHeader.createEl("span", {
      cls: `pf-cc-card-badge pf-cc-card-badge--${sevClass}`,
      text: t(this._ccBadgeKey(env, mod)),
    });

    // Reason text — localized via code map, fallback to backend text
    let reasonText: string;
    if (!isReal) {
      reasonText = t("cc_reason_placeholder").replace("{module}", t("cc_module_" + mod));
    } else {
      const l10nReason = this._localizeReason(env.reason.code, mod);
      reasonText = l10nReason ?? env.reason.text;
    }
    summaryRow.createEl("div", { cls: "pf-cc-card-reason", text: reasonText });

    // Action button (same logic as overview card — setup opens wizard, else probe)
    if (env.action.primary && !isReadyEnvelope(env)) {
      const action = classifyCapabilityAction(env);
      const isCta = action.kind === "setup";
      const btnCls = isCta ? "pf-cc-card-action pf-cc-card-action--primary" : "pf-cc-card-action";
      const actionBtn = summaryRow.createEl("button", {
        cls: btnCls,
        text: action.label,
        attr: { "aria-label": action.label },
      });
      actionBtn.addEventListener("click", () => {
        if (action.kind === "setup") {
          new PaperForgeSetupModal(this.app, this.plugin, () => {
            this._probeModule("installation");
            this._probeModule("help");
          }).open();
        } else {
          this._probeModule(mod);
        }
      });
    }

    // Diagnostics — native <details><summary> with localized field labels and values
    const details = summaryRow.createEl("details", { cls: "pf-cc-card-diagnostic" });
    details.createEl("summary", { text: t("cc_diagnostic_toggle") });
    const body = details.createEl("div", { cls: "pf-cc-card-diagnostic-body" });

    const stateLabel = t("cc_state_" + env.capability_state) || env.capability_state;
    const sevLabel = t("cc_severity_" + env.severity) || env.severity;
    const activityLabel = t("cc_activity_" + env.activity_state) || env.activity_state;

    let dateLabel: string;
    try {
      dateLabel = new Date(env.updated_at).toLocaleString();
    } catch {
      dateLabel = env.updated_at;
    }

    body.createEl("div", { text: `${t("cc_diag_module")}: ${env.module}` });
    body.createEl("div", { text: `${t("cc_diag_state")}: ${stateLabel}` });
    body.createEl("div", { text: `${t("cc_diag_severity")}: ${sevLabel}` });
    body.createEl("div", { text: `${t("cc_diag_activity")}: ${activityLabel}` });
    const reasonRow = body.createEl("div");
    reasonRow.appendText(t("cc_diag_reason") + ": " + reasonText + " ");
    const codeEl = reasonRow.createEl("code", { text: env.reason.code });
    body.createEl("div", { text: `${t("cc_diag_ttl")}: ${String(env.ttl_seconds)}s` });
    body.createEl("div", { text: `${t("cc_diag_updated")}: ${dateLabel}` });

    // Release notes from old release-notes tab
    this._renderReleaseNotesTab(containerEl);
  }


  _execMemoryStatus(
    pythonPath: string,
    vp: string,
    callback: (text: string) => void
  ) {
    exec(
      `"${pythonPath}" -m paperforge --vault "${vp}" memory status --json`,
      { encoding: "utf-8", timeout: 15000 },
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
    exec(
      `"${pythonPath}" -m paperforge --vault "${vp}" embed status --json`,
      { encoding: "utf-8", timeout: 15000 },
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
      if (opts && opts.onClose) opts.onClose(1, "", "No python runtime available");
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
    if (opts && opts.stream) {
      const child = spawn(resolved.path, args, {
        cwd: vp,
        env: opts.env || process.env,
        windowsHide: true,
      });
      if (opts.onData) child.stdout.on("data", opts.onData);
      if (opts.onStderr) child.stderr.on("data", opts.onStderr);
      if (opts.onError) child.on("error", opts.onError);
      child.on("close", opts.onClose);
      return child;
    }
    execFile(
      resolved.path,
      args,
      { cwd: vp, timeout: (opts && opts.timeout) || 60000 },
      (err, stdout, stderr) => {
        if (opts && opts.onClose) opts.onClose(err ? 1 : 0, stdout, stderr);
      }
    );
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
      const py = getCachedPython(vp, this.plugin.settings);
      if (!py.path) {
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
    const pyResult = resolvePythonExecutable(
      vp,
      settings,
      undefined,
      undefined
    );
    if (!pyResult.path) return null;
    return `"${pyResult.path}" -m paperforge --vault "${vp}" sync`;
  }

  _runManualSync() {
    const vp = (this.app.vault.adapter as any).basePath as string;
    const py = getCachedPython(vp, this.plugin.settings);
    if (!py.path) return;

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
    const py = getCachedPython(vp, this.plugin.settings);
    const args = [
      ...py.extraArgs,
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
    containerEl.createEl("h4", { text: "Vector Database" });

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
    new Setting(containerEl)
      .setName(t("feat_openai_key"))
      .setDesc(t("feat_openai_key_desc"))
      .addText((text) => {
        text
          .setPlaceholder("sk-...")
          .setValue(this.plugin.settings.vector_db_api_key || "")
          .onChange((value) => {
            this.plugin.settings.vector_db_api_key = value;
            this.plugin.saveSettings();
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
            const pyResult = getCachedPython(vp, this.plugin.settings);
            if (!pyResult.path) {
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
              const env = Object.assign({}, process.env, {
                PYTHONIOENCODING: "utf-8",
                PYTHONUTF8: "1",
              });
              const pkgsArg = pkgs.split(" ");
              await new Promise<void>((resolve, reject) => {
                execFile(
                  pyResult.path,
                  [...pyResult.extraArgs, "-m", "pip", "install", ...pkgsArg],
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

      const startBuild = (flag: string) => {
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

        const py = getCachedPython(vp, this.plugin.settings);
        if (!py.path) {
          new Notice(t("retrieval_no_python"));
          return;
        }
        const env = Object.assign({}, process.env, {
          PYTHONIOENCODING: "utf-8",
          PYTHONUTF8: "1",
          VECTOR_DB_API_KEY: this.plugin.settings.vector_db_api_key || "",
          VECTOR_DB_API_BASE: this.plugin.settings.vector_db_api_base || "",
          VECTOR_DB_API_MODEL: this.plugin.settings.vector_db_api_model || "",
        });
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
              this.plugin._embedBuffer ?? "",
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

      if (major < 3 || (major === 3 && minor < 10)) {
        const msg =
          "Python \u7248\u672C\u8FC7\u4F4E\uFF0C\u9700\u8981 3.10+ / Python version too low, need 3.10+";
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

  _syncRuntime(btn: any) {
    const vp = (this.app.vault.adapter as any).basePath as string;
    const { path: pythonExe, extraArgs = [] } = resolvePythonExecutable(
      vp,
      this.plugin.settings,
      undefined,
      undefined
    );
    const ver = this.plugin.manifest.version;
    const installCmd = buildRuntimeInstallCommand(pythonExe, ver, extraArgs);

    btn.setDisabled(true);
    btn.setButtonText(t("runtime_health_syncing"));

    const tryInstall = (args: string[], label: string) => {
      console.log(`[PaperForge] Sync Runtime: trying ${label}`);
      return runSubprocess(
        installCmd.cmd,
        args,
        vp,
        installCmd.timeout,
        undefined,
        paperforgeEnrichedEnv()
      );
    };

    const deploySkills = () => {
      let agentKey = "opencode";
      try {
        const cfgRaw = fs.readFileSync(
          path.join(vp, "paperforge.json"),
          "utf-8"
        );
        const cfg = JSON.parse(cfgRaw);
        if (cfg.agent_key) agentKey = cfg.agent_key;
      } catch {}
      const deployArgs = [
        ...extraArgs,
        "-c",
        "from paperforge.services.skill_deploy import deploy_skills; " +
          "from pathlib import Path; " +
          'r=deploy_skills(vault=Path(r"' +
          vp.replace(/\\/g, "\\\\") +
          '"), agent_key="' +
          agentKey +
          '", overwrite=True); ' +
          'print("skills deployed" if r["skill_deployed"] else "skills skipped", flush=True)',
      ];
      const child = spawn(pythonExe, deployArgs, {
        cwd: vp,
        timeout: 30000,
        windowsHide: true,
      });
      let out = "";
      child.stdout.on("data", (d) => {
        out += d.toString("utf-8");
      });
      child.on("close", (code) => {
        console.log(`[PaperForge] Skill deploy: ${out.trim()} (exit ${code})`);
      });
    };

    tryInstall(installCmd.pypiArgs, "PyPI").then((result) => {
      if (result.exitCode === 0) {
        console.log("[PaperForge] Sync Runtime: installed via PyPI");
        deploySkills();
        new Notice(t("runtime_health_sync_done").replace("{0}", ver), 5000);
        this.display();
        return;
      }
      console.warn(
        "[PaperForge] Sync Runtime: PyPI failed, falling back to git..."
      );
      tryInstall(installCmd.gitArgs, "git").then((r2) => {
        if (r2.exitCode === 0) {
          console.log("[PaperForge] Sync Runtime: installed via git");
          deploySkills();
          new Notice(t("runtime_health_sync_done").replace("{0}", ver), 5000);
          this.display();
        } else {
          btn.setDisabled(false);
          btn.setButtonText(t("runtime_health_sync"));
          console.error("[PaperForge] git fallback stderr:", r2.stderr);
          new Notice(
            t("runtime_health_sync_fail").replace(
              "{0}",
              "pip exit code " + r2.exitCode
            ),
            8000
          );
        }
      });
    });
  }

  _debouncedSave() {
    clearTimeout(this._saveTimeout!);
    this._saveTimeout = setTimeout(() => this.plugin.saveSettings(), 500);
  }

  _preCheck(onPass: () => void) {
    const vaultPath = (this.app.vault.adapter as any).basePath as string;
    const { path: pythonExe, extraArgs = [] } = resolvePythonExecutable(
      vaultPath,
      this.plugin?.settings,
      undefined,
      undefined
    );
    execFile(
      pythonExe,
      [...extraArgs, "--version"],
      { timeout: 8000 },
      (pyErr, pyOut) => {
        const results: { label: string; ok: boolean; detail: string }[] = [];

        /* Python */
        results.push({
          label: "Python",
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

  _renderMaintenanceTab(containerEl: HTMLElement) {
    containerEl.createEl("h2", {
      text: t("tab_maintenance") || "维护",
    });

    // vault path — DataAdapter.basePath is undocumented but stable
    const adapter = this.app.vault
      .adapter as unknown as { basePath?: string };
    const vaultPath = adapter.basePath ?? "";
    const statusEl = containerEl.createEl("div");

    // Filter state
    const filterState = { active: "all" as "all" | "recommended" };

    // ── Phase 1: Read cache ──
    let cache: MaintenanceCache | null = null;
    try {
      cache = readMaintenanceCache(vaultPath);
    } catch {}

    // ── Phase 2: Try manifest refresh ──
    const py = resolvePythonExecutable(
      vaultPath,
      // PaperForgeSettings — no cast needed, ISettingPlugin has it
      this.plugin.settings,
      fs,
      execFileSync
    );
    if (!py.path) {
      statusEl.createEl("p", {
        text: "⚠ Python 未配置，请先在「安装」标签页配置。",
        cls: "setting-item-description",
      });
      return;
    }

      const isBatchRunning = () => !!this.plugin._ocrProcess;

      const renderTable = (papers: MaintenanceDisplayRow[]) => {
        statusEl.empty();
        const allVisible = papers;

        // Filter tabs — render before empty check so user can always switch back
        const filterRow = statusEl.createEl("div", {
          cls: "pf-maint-filters",
        });

        const allTab = filterRow.createEl("button", {
          cls:
            "pf-maint-filter" +
            (filterState.active === "all" ? " active" : ""),
          text: t("maintenance_filter_all") || "All",
        });
        allTab.addEventListener("click", () => {
          filterState.active = "all";
          renderTable(papers);
        });

        const recTab = filterRow.createEl("button", {
          cls:
            "pf-maint-filter" +
            (filterState.active === "recommended" ? " active" : ""),
          text: t("maintenance_filter_recommended") || "Recommended",
        });
        recTab.addEventListener("click", () => {
          filterState.active = "recommended";
          renderTable(papers);
        });

        // Recommended = papers whose derived results need rebuilding (excludes retry/failed)
        const visible =
          filterState.active === "recommended"
            ? allVisible.filter((p) => p.needs_derived_rebuild === true)
          : allVisible;

      // If the active filter yields nothing, show a message and skip the table/progress
      if (visible.length === 0) {
        statusEl.createEl("p", {
          text: "当前筛选条件下无数据",
          cls: "setting-item-description",
        });
      } else {
        const pyPath = py.path;
        const pyExtra = (py.extraArgs || []) as string[];


      // ── Progress bar (if batch running) — mutable DOM refs, no full re-render ──
      const progressContainer = statusEl.createEl("div", {
        cls: "pf-maint-progress",
      });
      progressContainer.style.display = "none";

      const track = progressContainer.createEl("div", {
        cls: "paperforge-progress-track",
      });
      track.style.cssText = "flex:1;";
      const doneSeg = track.createEl("div", {
        cls: "paperforge-progress-seg done",
      });
      const pendingSeg = track.createEl("div", {
        cls: "paperforge-progress-seg pending",
      });
      const label = progressContainer.createEl("span", {
        cls: "pf-maint-progress-text",
      });
      const keyLabel = progressContainer.createEl("span", {
        cls: "pf-maint-progress-key",
      });

      // Stop button — cooperative: stdin control line, fallback to SIGINT
      const stopBtn = progressContainer.createEl("button", {
        text: t("maintenance_stop") || "Stop",
      });
      stopBtn.className = "mod-warning";
      stopBtn.addEventListener("click", () => {
        const child = this.plugin._ocrProcess as unknown as {
          stdin?: { write: (_: string) => boolean };
          kill?: (_: string) => void;
        };
        if (child) {
          // Prefer stdin control line (cooperative — backend finishes current paper)
          if (child.stdin && typeof child.stdin.write === "function") {
            child.stdin.write("PAPERFORGE_STOP\n");
          } else if (typeof child.kill === "function") {
            child.kill("SIGINT");
          }
        }
        // Flag, don't null — onClose handles cleanup
        this.plugin._ocrWasStopped = true;
        stopBtn.disabled = true;
        stopBtn.textContent = (t("maintenance_stop") || "Stop") + "…";
      });

      // In-place DOM update — called from runBatch start + onData events
      const updateProgress = () => {
        const prog = this.plugin._ocrProgress;
        if (!prog || prog.total === 0 || !this.plugin._ocrProcess) {
          progressContainer.style.display = "none";
          return;
        }
        progressContainer.style.display = "flex";

        const pct =
          prog.total > 0
            ? ((prog.current / prog.total) * 100).toFixed(1)
            : "0";

        doneSeg.style.width = `${pct}%`;
        doneSeg.style.minWidth = prog.current > 0 ? "2px" : "0";

        if (prog.current < prog.total) {
          pendingSeg.style.display = "";
          pendingSeg.style.flex = "1";
        } else {
          pendingSeg.style.display = "none";
        }

        label.textContent = (
          t("maintenance_progress_label") ||
          "{current}/{total} papers"
        )
          .replace("{current}", String(prog.current))
          .replace("{total}", String(prog.total));

        keyLabel.textContent = prog.key ? ` (${prog.key})` : "";
      };

      updateProgress();

      // Selection state
      const selState = new Map<string, boolean>();
      for (const p of visible) selState.set(p.key, false);

      // ── Table ──
      const wrapper = statusEl.createEl("div", {
        cls: "pf-maint-table-wrap",
      });
      const table = wrapper.createEl("table", { cls: "pf-maint-table" });
      const thead = table.createEl("thead");
      const tbody = table.createEl("tbody");
      const headerRow = thead.insertRow();
      ["", "Paper", "Status Reason", "Actions"].forEach((h) => {
        const th = document.createElement("th");
        th.textContent = h;
        headerRow.appendChild(th);
      });

      const isBusy = isBatchRunning();

      for (const p of visible) {
        const tr = tbody.insertRow();

        // Checkbox
        const selTd = tr.insertCell();
        selTd.style.cssText =
          "padding:3px 4px;text-align:center;width:24px;";
        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.className = "pf-maint-sel";
        cb.checked = selState.get(p.key) || false;
        cb.addEventListener("change", () => {
          selState.set(p.key, cb.checked);
          updateBatchLabel();
        });
        selTd.appendChild(cb);

        // Paper info (title + key)
        const infoTd = tr.insertCell();
        infoTd.style.cssText = "padding:3px 4px;";
        const infoDiv = infoTd.createEl("div", {
          cls: "pf-maint-paper-info",
        });
        infoDiv.createEl("div", {
          cls: "pf-maint-paper-title",
          text: p.title || p.key,
        });
        infoDiv.createEl("div", {
          cls: "pf-maint-paper-key",
          text: p.key,
        });

        // Status reason
        const reasonTd = tr.insertCell();
        reasonTd.style.cssText = "padding:3px 4px;";
        reasonTd.createEl("div", {
          cls: "pf-maint-reason",
          text: p.display_reason || "",
        });

        // Action buttons — [Rebuild] [Redo]
        const actionTd = tr.insertCell();
        actionTd.style.cssText =
          "padding:3px 4px;white-space:nowrap;";
        const actionDiv = actionTd.createEl("div", {
          cls: "pf-maint-actions",
        });

        const primaryAction = maintenanceActionForRow(p);
        if (primaryAction === "rebuild") {
          const rebuildBtn = actionDiv.createEl("button", {
            cls: "pf-maint-action-btn rebuild",
            text: t("maintenance_btn_rebuild") || "Rebuild",
          });
          if (isBusy) rebuildBtn.disabled = true;
          rebuildBtn.addEventListener("click", () => {
            execFile(
              pyPath,
              [...pyExtra, "-m", "paperforge", "ocr", "rebuild", p.key],
              {
                cwd: vaultPath,
                timeout: 120000,
                windowsHide: true,
              },
              () => {
                new Notice(
                  (t("maintenance_btn_rebuild") || "Rebuild") +
                    " — " +
                    p.key
                );
              }
            );
          });
        } else if (primaryAction === "redo") {
          const redoBtn = actionDiv.createEl("button", {
            cls: "pf-maint-action-btn redo",
            text: t("ocr_maint_redo_btn") || "Redo",
          });
          if (isBusy) redoBtn.disabled = true;
          redoBtn.addEventListener("click", () => {
            if (
              maintenanceActionRequiresConfirmation("redo") &&
              !confirm(
                (t("ocr_maint_redo_confirm") ||
                  "Rerun OCR for {n} paper(s)? Existing derived OCR artifacts will be replaced.").replace(
                  "{n}",
                  "1"
                )
              )
            ) {
              return;
            }
            execFile(
              pyPath,
              [...pyExtra, "-m", "paperforge", "ocr", "redo", p.key],
              {
                cwd: vaultPath,
                timeout: 300000,
                windowsHide: true,
              },
              () => {
                new Notice(
                  (t("ocr_maint_redo_btn") || "Redo OCR") + " — " + p.key
                );
              }
            );
          });
        }
      }

      // ── Batch action bar ──
      const batchBar = statusEl.createEl("div", {
        cls: "pf-maint-batch-bar",
      });
      const batchLabel = batchBar.createEl("span", {
        cls: "pf-maint-batch-label",
        text: "0 selected",
      });

      const updateBatchLabel = () => {
        const n = visible.filter((p) => selState.get(p.key)).length;
        batchLabel.textContent = n + " selected";
      };

      const rebuildBatchBtn = batchBar.createEl("button", {
        cls: "mod-cta",
        text:
          t("maintenance_batch_rebuild") || "▶ Rebuild selected",
      });
      rebuildBatchBtn.disabled = isBusy;

      const redoBatchBtn = batchBar.createEl("button", {
        cls: "mod-cta",
        text:
          t("maintenance_batch_redo") || "▶ Full OCR redo selected",
      });
      redoBatchBtn.disabled = isBusy;

      const runBatch = (action: "rebuild" | "redo") => {
        // Filter selected by eligibility for the chosen action (matches per-row canonical action)
        const selected = visible.filter(
          (p) =>
            selState.get(p.key) &&
            maintenanceActionForRow(p) === action,
        );
        if (selected.length === 0) {
          const label =
            action === "rebuild"
              ? t("maintenance_btn_rebuild") || "Rebuild"
              : t("ocr_maint_redo_btn") || "Redo";
          new Notice(
            "Selected papers are not eligible for " +
              label +
              ". Uncheck ineligible rows and try again.",
            6000,
          );
          return;
        }
        if (
          maintenanceActionRequiresConfirmation(action) &&
          !confirm(
            (t("ocr_maint_redo_confirm") ||
              "Rerun OCR for {n} paper(s)? Existing derived OCR artifacts will be replaced.").replace(
              "{n}",
              String(selected.length)
            )
          )
        ) {
          return;
        }
        const keys = selected.map((p) => p.key);
        this.plugin._ocrProgress = {
          current: 0,
          total: keys.length,
          key: "",
        };
        this.plugin._ocrBuffer = "";
        this.plugin._ocrWasStopped = false;

        const prefix =
          action === "rebuild" ? "OCR_REBUILD" : "OCR_REDO";

        // Disable batch + per-row action buttons during the batch
        rebuildBatchBtn.disabled = true;
        redoBatchBtn.disabled = true;
        Array.from(
          wrapper.querySelectorAll<HTMLButtonElement>(".pf-maint-action-btn"),
        ).forEach((btn) => {
          btn.disabled = true;
        });
        // Also disable checkboxes to prevent selection changes during batch
        Array.from(
          wrapper.querySelectorAll<HTMLInputElement>(".pf-maint-sel"),
        ).forEach((cb) => {
          cb.disabled = true;
        });
        // Disable filter tabs to prevent filter switch mid-batch
        allTab.disabled = true;
        recTab.disabled = true;
        stopBtn.disabled = false;
        stopBtn.textContent = t("maintenance_stop") || "Stop";

        const child = this._callPython(
          ["ocr", action, ...keys],
          {
            stream: true,
            onData: (data: unknown) => {
              const text =
                typeof data === "string"
                  ? data
                  : Buffer.isBuffer(data)
                    ? data.toString("utf-8")
                    : String(data);
              // Shared parser with chunk buffer
              const { events, buffer } = processProgressChunk(
                text,
                this.plugin._ocrBuffer ?? "",
              );
              this.plugin._ocrBuffer = buffer;
              for (const ev of events) {
                if (ev.event === "START") {
                  if (this.plugin._ocrProgress) {
                    this.plugin._ocrProgress.total =
                      ev.total || keys.length;
                  }
                } else if (ev.event === "PROGRESS") {
                  this.plugin._ocrProgress = {
                    current: ev.current || 0,
                    total: ev.total || keys.length,
                    key: ev.key || "",
                  };
                }
                // DONE handled in onClose
              }
              // In-place DOM update — no full re-render
              updateProgress();
            },
            onError: (err: Error) => {
              this.plugin._ocrProcess = null;
              new Notice(
                "Batch error: " + (err.message || err),
              );
              renderTable(papers);
            },
            onClose: (code: number | null) => {
              // code 130 = SIGINT caught cooperatively by the backend
              if (this.plugin._ocrWasStopped || code === 130) {
                this.plugin._ocrWasStopped = false;
                // Leave progress as-is; no finalize
                this.plugin._ocrProcess = null;
                updateProgress();
                new Notice("OCR batch stopped by user.");
              } else if (code === 0) {
                // Finalize progress to show completion even if no tokens came through
                if (this.plugin._ocrProgress) {
                  this.plugin._ocrProgress.current =
                    this.plugin._ocrProgress.total;
                }
                this.plugin._ocrProcess = null;
                updateProgress();
                new Notice(
                  (
                    t("maintenance_batch_complete") ||
                    "Batch operation complete — {n} papers processed."
                  ).replace("{n}", String(keys.length)),
                );
              } else {
                this.plugin._ocrProcess = null;
                updateProgress();
                new Notice(
                  "Batch operation finished with exit code " +
                    code +
                    ".",
                  8000,
                );
              }
              // Full refresh
              refreshMaintenanceData(
                vaultPath,
                pyPath,
                pyExtra,
                cache,
              )
                .then((result) => {
                  cache = readMaintenanceCache(vaultPath);
                  renderTable(result.data);
                })
                .catch(() => {
                  renderTable(allVisible);
                });
            },
          },
        );
        this.plugin._ocrProcess = child;
        updateProgress();
      };

      rebuildBatchBtn.addEventListener("click", () =>
        runBatch("rebuild")
      );
      redoBatchBtn.addEventListener("click", () =>
        runBatch("redo")
      );

      updateBatchLabel();
      }  // end else (visible non-empty)
    };

    // ── Phase 1: Show cache immediately ──
    if (cache) {
      const papers = Object.values(
        cache.papers
      ) as MaintenanceDisplayRow[];
      renderTable(papers);
    } else {
      statusEl.createEl("p", {
        text: "正在加载 OCR 维护数据…",
      });
    }

    // ── Phase 2: Background refresh ──
    refreshMaintenanceData(
      vaultPath,
      py.path,
      py.extraArgs || [],
      cache || null
    )
      .then((result) => {
        cache = readMaintenanceCache(vaultPath);
        if (result.changed || !cache) {
          renderTable(result.data);
        }
      })
      .catch(() => {
        if (!cache) {
          statusEl.empty();
          statusEl.createEl("p", {
            text:
              "无法加载 OCR 数据。请确保已安装 paperforge 并运行过 OCR。",
            cls: "setting-item-description",
          });
        }
      });
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
   * regardless of setup_complete, so first-run immediately probes Installation+Help.
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
      schema_version: 1,
      module: mod,
      capability_state: current?.capability_state ?? "unknown",
      activity_state: "running",
      activity_label: "Probing...",
      activity_progress: null,
      severity: "unknown",
      reason: { code: `${mod}.probing`, text: `Checking ${mod} status...` },
      action: { primary: probeAction(mod) },
      notices: current?.notices ?? [],
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
          schema_version: 1,
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
    if (mod === "library" && lastOperationExitCode != null && lastOperationExitCode !== 0) {
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
            console.warn(`[PaperForge] Probe ${mod}: invalid envelope schema`, stdout?.slice(0, 200));
            this._updateCapabilityEnvelope(mod, createInvalidEnvelope(mod));
          }
        } catch {
          console.warn(`[PaperForge] Probe ${mod}: unparseable JSON`, stdout?.slice(0, 200));
          this._updateCapabilityEnvelope(mod, createInvalidEnvelope(mod));
        }
      }
    );
  }

  /** Update a single module envelope and refresh the display. */
  _updateCapabilityEnvelope(mod: string, envelope: ProbeEnvelope): void {
    if (!this._capabilityState) this._capabilityState = {};
    const prev = this._capabilityState[envelope.module];
    this._capabilityState[envelope.module] = envelope;
    this._persistCapabilityState();
    // Show notice when probe completes (transition from running to idle)
    if (prev?.activity_state === "running" && envelope.activity_state !== "running") {
      new Notice(t("cc_notice_refreshed"), 3000);
    }
    // Re-render the current tab to reflect changes
    this.display();
  }

  /** Derive badge i18n key from envelope severity + module. */
  private _ccBadgeKey(env: ProbeEnvelope, mod: CapabilityModule): string {
    if (env.severity === "ok") return "cc_badge_ok";
    if (env.severity === "error" && mod === "installation") return "cc_badge_setup";
    if (env.severity === "warning" || env.severity === "error") return "cc_badge_attention";
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
  private static _REAL_PROBE = new Set(["installation", "library", "ocr", "memory", "help"]);
  /** Modules that have a navigation entry in the overview card grid. */
  private static _NAVIGABLE = new Set(["installation", "library", "ocr", "memory", "maintenance", "help"]);

  _renderCard(container: HTMLElement, mod: CapabilityModule, envelope: ProbeEnvelope): void {
    const env = envelope;
    const sevClass = this._sevClass(env.severity);
    const isReal = PaperForgeSettingTab._REAL_PROBE.has(mod);
    const isNavigable = PaperForgeSettingTab._NAVIGABLE.has(mod);
    const card = container.createEl("div", {
      cls: "pf-cc-card",
      attr: { role: "listitem", tabindex: "0", "data-module": mod, "aria-label": `${t("cc_module_" + mod)} — ${t(this._ccBadgeKey(env, mod))}` },
    });

    // Header: name area with optional navigation entry
    const header = card.createEl("div", { cls: "pf-cc-card-header" });
    const nameArea = header.createEl("div", { cls: "pf-cc-card-name-area" });
    if (isNavigable) {
      // Navigation entry — Enter/Space or click opens module detail
      const openLabel = mod === "installation"
        ? t("module_detail_open_installation")
        : mod === "library"
          ? t("module_detail_open_library")
          : mod === "ocr"
            ? t("module_detail_open_ocr")
            : mod === "memory"
              ? t("module_detail_open_memory")
              : mod === "help"
                ? t("module_detail_open_help")
                : mod === "maintenance"
                  ? t("module_detail_open_maintenance")
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
      nameArea.createEl("div", { cls: "pf-cc-card-name", text: t("cc_module_" + mod) });
    }
    header.createEl("div", {
      cls: `pf-cc-card-badge pf-cc-card-badge--${sevClass}`,
      text: t(this._ccBadgeKey(env, mod)),
    });

    // Reason text — localized via code map, fallback to backend text
    // Placeholder modules (library, ocr, memory, maintenance) show "pending integration"
    let reasonText: string;
    if (!isReal) {
      reasonText = t("cc_reason_placeholder").replace("{module}", t("cc_module_" + mod));
    } else {
      const l10nReason = this._localizeReason(env.reason.code, mod);
      reasonText = l10nReason ?? env.reason.text;
    }
    card.createEl("div", { cls: "pf-cc-card-reason", text: reasonText });

    // Activity label + progress bar (DOM style.width, never inline attribute)
    if (env.activity_state === "running" && env.activity_label) {
      const activityRow = card.createEl("div", { cls: "pf-cc-card-activity", attr: { "aria-live": "polite" } });
      activityRow.createEl("span", { text: env.activity_label });
      if (env.activity_progress && env.activity_progress.total > 0) {
        const pct = Math.round((env.activity_progress.current / env.activity_progress.total) * 100);
        const bar = activityRow.createEl("div", { cls: "pf-cc-card-progress", attr: { role: "progressbar", "aria-valuenow": String(env.activity_progress.current), "aria-valuemin": "0", "aria-valuemax": String(env.activity_progress.total) } });
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
      const btnCls = isCta ? "pf-cc-card-action pf-cc-card-action--primary" : "pf-cc-card-action";
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
    const stateLabel = t("cc_state_" + env.capability_state) || env.capability_state;
    const sevLabel = t("cc_severity_" + env.severity) || env.severity;
    const activityLabel = t("cc_activity_" + env.activity_state) || env.activity_state;

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
    body.createEl("div", { text: `${t("cc_diag_activity")}: ${activityLabel}` });
    // Reason: localized text (or placeholder message) plus technical code in <code>
    const reasonRow = body.createEl("div");
    reasonRow.appendText(t("cc_diag_reason") + ": " + reasonText + " ");
    const codeEl = reasonRow.createEl("code", { text: env.reason.code });
    body.createEl("div", { text: `${t("cc_diag_ttl")}: ${String(env.ttl_seconds)}s` });
    body.createEl("div", { text: `${t("cc_diag_updated")}: ${dateLabel}` });
  }

  /** Navigate from overview card to module detail or another tab. */
  _handleCardNavigation(mod: string): void {
    if (mod === "installation") {
      this.activeTab = "module-detail";
      this._selectedDetailModule = "installation";
      this._focusTargetId = "#pf-installation-detail-heading";
    } else if (mod === "library") {
      this.activeTab = "module-detail";
      this._selectedDetailModule = "library";
      this._focusTargetId = "#pf-library-detail-heading";
    } else if (mod === "ocr") {
      this.activeTab = "module-detail";
      this._selectedDetailModule = "ocr";
      this._focusTargetId = "#pf-ocr-detail-heading";
    } else if (mod === "memory") {
      this.activeTab = "module-detail";
      this._selectedDetailModule = "memory";
      this._focusTargetId = "#pf-memory-detail-heading";
    } else if (mod === "help") {
      this.activeTab = "help";
      this._selectedDetailModule = "";
      this._focusTargetId = "button.pf-open-module-btn[data-module=help]";
    } else if (mod === "maintenance") {
      this.activeTab = "maintenance";
      this._selectedDetailModule = "";
      this._focusTargetId = null;
    }
    this.display();
  }

  /** Render Vercel-inspired control center: summary card + six-card responsive grid. */
  _renderControlCenter(containerEl: HTMLElement): void {
    const cc = containerEl.createEl("div", { cls: "pf-control-center" });

    // Compute summary counts from envelopes
    const modules = CAPABILITY_MODULES;
    const envelopes: Record<string, ProbeEnvelope> = this._capabilityState ?? {};
    let realReady = 0;
    let realAttention = 0;
    let placeholderCount = 0;

    for (const mod of modules) {
      const env = envelopes[mod] ?? createUnknownEnvelope(mod);
      if (env.severity === "ok" && env.capability_state === "ready" && env.action.primary === null) {
        // Backend-confirmed ready, no pending action
        realReady++;
      } else if (PaperForgeSettingTab._REAL_PROBE.has(mod)) {
        // Real module that has been probed but isn't ready
        if (env.severity === "error" || env.severity === "warning" || env.severity === "unknown") {
          realAttention++;
        }
      } else {
        // Placeholder module (library, ocr, memory, maintenance) — not yet connected
        placeholderCount++;
      }
    }

    // ── Summary Card ──
    const summaryEl = cc.createEl("div", { cls: "pf-cc-summary" });
    summaryEl.createEl("div", { cls: "pf-cc-summary-eyebrow", text: t("cc_title") });

    // Decisive title based on state
    let summaryTitle: string;
    let summaryBodyText: string;
    if (realAttention > 0) {
      summaryTitle = t("cc_summary_attention");
      summaryBodyText = t("cc_summary_attention_body");
    } else if (realReady === modules.length) {
      summaryTitle = t("cc_summary_ok");
      summaryBodyText = t("cc_summary_ok_body");
    } else if (realReady > 0 && placeholderCount > 0 && realAttention === 0) {
      summaryTitle = t("cc_summary_core_ok").replace("{n}", String(placeholderCount));
      summaryBodyText = t("cc_summary_core_ok_body");
    } else {
      summaryTitle = t("cc_summary_core_ok").replace("{n}", String(modules.length - realReady));
      summaryBodyText = t("cc_desc");
    }
    summaryEl.createEl("div", { cls: "pf-cc-summary-title", text: summaryTitle });
    summaryEl.createEl("div", { cls: "pf-cc-summary-body", text: summaryBodyText });

    // Summary counts row
    const countsEl = summaryEl.createEl("div", { cls: "pf-cc-summary-counts" });
    countsEl.createEl("div", {
      cls: "pf-cc-summary-count",
      text: t("cc_n_ready").replace("{n}", String(realReady)),
    });
    if (placeholderCount > 0) {
      countsEl.createEl("div", {
        cls: "pf-cc-summary-count",
        text: t("cc_n_pending").replace("{n}", String(placeholderCount)),
      });
    }

    // ── Module Grid ──
    const grid = cc.createEl("div", { cls: "pf-cc-grid", attr: { role: "list", "aria-label": t("cc_zone_modules") } });
    for (const mod of modules) {
      const env = envelopes[mod] ?? createUnknownEnvelope(mod);
      this._renderCard(grid, mod, env);
    }
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
}
