import type { ActionRequest, ActionScope } from "./client/action-contract";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import {
  Plugin,
  Notice,
  Modal,
  Setting,
  App,
  TFile,
  requestUrl,
} from "obsidian";

/** Thin confirm modal for the one-time plugin-assisted config migration. */
class ConfirmMigrationModal extends Modal {
  constructor(
    app: App,
    summary: string,
    private readonly onConfirm: () => Promise<void>
  ) {
    super(app);
    this.setTitle(t("migrate_modal_title"));
    this.contentEl.createEl("p", {
      text: t("migrate_modal_intro"),
    });
    const pre = this.contentEl.createEl("pre", { cls: "pf-migration-summary" });
    pre.setText(summary);
    this.contentEl.createEl("p", {
      text: t("migrate_modal_rules"),
      cls: "setting-item-description",
    });
    const actions = this.contentEl.createDiv({ cls: "pf-modal-actions" });
    const cancel = actions.createEl("button", {
      text: t("migrate_modal_cancel"),
    });
    cancel.addEventListener("click", () => this.close());
    const go = actions.createEl("button", { text: t("migrate_modal_confirm") });
    go.addEventListener("click", () => {
      void this.onConfirm().finally(() => this.close());
    });
  }
}
import {
  VIEW_TYPE_PAPERFORGE,
  VIEW_TYPE_OCR_WORKSPACE,
  VIEW_TYPE_PAPERFORGE_PDF,
  VIEW_TYPE_PF_BASE_TABLE,
  VIEW_TYPE_UI_GALLERY,
  PF_ICON_ID,
  ACTIONS,
  DEFAULT_SETTINGS,
  PaperForgeSettings,
} from "./constants";
import { t, setLanguage } from "./i18n";
import {
  formatDaemonNotice,
  formatElapsedDuration,
  formatHumanError,
  formatLiveTaskPhase,
} from "./services/feedback";
import {
  readRuntimePointer,
  resolveRuntimeCommand,
  type PointerInfo,
} from "./services/managed-runtime";
import {
  createObsidianRequestFetcher,
  ensureNativeDaemonDownloaded,
  readNativeDaemonMeta,
  resolveNativeDaemonBinary,
} from "./services/native-daemon";
import {
  isEngineVersionCompatible,
  normalizeSemverForCompare,
} from "./services/setup-decision-tree";
import {
  resolveElectronSessionProxy,
  setCachedSystemProxy,
} from "./services/system-proxy";
import { PaperForgeSettingTab } from "./settings";
import { orchestrateFromSync } from "./services/next-actions-bridge";
import { PaperForgeStatusView } from "./views/dashboard";
import { OcrWorkspaceView } from "./views/ocr-workspace";
import { PaperForgeBasesView } from "./views/paperforge-base-view";
import { PaperForgeQuickSwitcherModal } from "./views/quick-switcher";
import { openVaultFileSafely } from "./views/paper-interactions";
import { PaperForgeGalleryView } from "./views/ui-gallery";
import {
  PaperForgePdfView,
  type PdfAnnotatorOpenState,
} from "./views/pdf-annotator";
import {
  PaperForgeConfirmModal,
  PaperForgeSetupWizardModal,
  checkOrphanState,
} from "./views/modals";
import { CommandRegistry } from "./uikit/commands";
import { PaperForgeUpgradeModal } from "./views/upgrade-modal";
import {
  applyPathConfigFromList,
  isConfigHydrated,
  readPathConfig,
  resolveVaultPaths,
} from "./services/runtime-paths";
import {
  PaperForgeClient,
  NodeProcessTransport,
  type BaseTableSnapshotDto,
  type VaultUpgradePlanDto,
  type DaemonJobDto,
} from "./client";
import { dumpTrace, setTraceEnabled } from "./client/trace";

export interface ActiveBackgroundTask {
  kind: "sync" | "ocr" | "embed" | "heal" | "runtime";
  label: string;
  phase?: string;
  detail?: string;
  startedAt?: number;
  current?: number;
  total?: number;
  key?: string;
  jobId?: string;
}

export default class PaperForgePlugin extends Plugin {
  /** agent_platform choices from Python's config list (#142) — empty until hydrated. */
  agentPlatformChoices: string[] = [];

  /** #161/R: embed status read model cache (embed status --json). */
  _embedStatusCache: Record<string, unknown> = {};

  settings!: PaperForgeSettings;
  private _autoSyncRunning = false;
  private _lastSyncTime: string | null = null;
  private _pollTimer: ReturnType<typeof setInterval> | null = null;
  private _embedProcess: unknown = null;
  private _embedProgress = { current: 0, total: 0, key: "" };
  private _embedStderr = "";
  private _ocrRunning = false;
  _memoryStatusText: string | null = null;
  _ocrProgress = { current: 0, total: 1, key: "" };
  private _settingTab: PaperForgeSettingTab | null = null;
  private _baseSnapshotCache: BaseTableSnapshotDto | null = null;
  private _lastStateSeq = -1;
  private _stateSeqWatcher: fs.FSWatcher | null = null;
  private _stateSeqTimer: ReturnType<typeof setTimeout> | null = null;
  private _daemonJobs = new Map<string, DaemonJobDto>();
  private _unsubscribeDaemon: (() => void) | null = null;
  private _upgradePlanCache: VaultUpgradePlanDto | null = null;
  private _upgradeBannerDismissedForSession = false;
  private _quarantinedBinDir: string | null = null;
  private _lastAutoSyncError: { message: string; at: number } | null = null;
  private _pendingReleaseNotesVersion: string | null = null;
  private _daemonUpdating = false;
  private _startupDaemonCheckPending = false;
  private _syncStartedAt: number | null = null;
  private _statusBarHeartbeat: ReturnType<typeof setInterval> | null = null;
  private _settingTabRefreshThrottleTimer: ReturnType<
    typeof setTimeout
  > | null = null;
  private _lastSettingTabRefreshAt = 0;
  private _unloaded = false;
  private _startupDeferTimer: ReturnType<typeof setTimeout> | null = null;
  private _lastSyncedZoteroSig: string | null = null;
  private _statusBarEl: HTMLElement | null = null;
  private _recentDaemonNotices: Array<{
    id: string;
    level: string;
    message: string;
    at: number;
  }> = [];
  private _statusPopoverEl: HTMLElement | null = null;
  private _statusPopoverCleanup: (() => void) | null = null;
  private _popoutWindows = new Set<Window>();
  private _localFiltersCache: Record<
    string,
    {
      query?: string;
      domain?: string;
      collection?: string;
      status?: string;
      minIf?: number;
    }
  > | null = null;

  private _client: PaperForgeClient | null = null;
  readonly commandRegistry = new CommandRegistry();

  getCommandRegistry(): CommandRegistry {
    return this.commandRegistry;
  }

  isDaemonUpdating(): boolean {
    return this._daemonUpdating;
  }

  isStartupDaemonCheckPending(): boolean {
    return this._startupDaemonCheckPending;
  }

  isRuntimeUpdating(): boolean {
    for (const dj of this._daemonJobs.values()) {
      if (
        dj.kind === "runtime.install" ||
        dj.kind === "runtime.update" ||
        dj.kind === "runtime.repair"
      ) {
        return true;
      }
    }
    return false;
  }

  isSyncing(): boolean {
    if (this._autoSyncRunning) return true;
    for (const dj of this._daemonJobs.values()) {
      if (dj.kind === "sync") return true;
    }
    return false;
  }

  setManualSyncActive(active: boolean): void {
    this._autoSyncRunning = active;
    this._syncStartedAt = active ? Date.now() : null;
    this._emitStateChanged();
  }

  getLiveTaskSummary(kind: "runtime" | "sync"): {
    phaseText: string;
    current: number;
    total: number;
    startedAt: number | null;
  } | null {
    if (kind === "runtime") {
      let rtJob: DaemonJobDto | null = null;
      for (const dj of this._daemonJobs.values()) {
        if (
          dj.kind === "runtime.install" ||
          dj.kind === "runtime.update" ||
          dj.kind === "runtime.repair"
        ) {
          rtJob = dj;
          break;
        }
      }
      if (!rtJob && !this._daemonUpdating) return null;
      if (!rtJob) {
        return {
          phaseText: t("activity_daemon_updating") || "Updating local service",
          current: 0,
          total: 5,
          startedAt: null,
        };
      }
      const tot = rtJob.total > 0 ? rtJob.total : 5;
      return {
        phaseText: formatLiveTaskPhase(
          rtJob.kind,
          rtJob.phase,
          rtJob.current,
          tot,
          rtJob.item_id
        ),
        current: rtJob.current,
        total: tot,
        startedAt: rtJob.started_at > 0 ? rtJob.started_at * 1000 : null,
      };
    }

    let syncJob: DaemonJobDto | null = null;
    for (const dj of this._daemonJobs.values()) {
      if (dj.kind === "sync") {
        syncJob = dj;
        break;
      }
    }
    if (!syncJob && !this._autoSyncRunning) return null;
    const tot = syncJob && syncJob.total > 0 ? syncJob.total : 5;
    const cur = syncJob ? syncJob.current : 0;
    const startedAt =
      syncJob && syncJob.started_at > 0
        ? syncJob.started_at * 1000
        : this._syncStartedAt;
    return {
      phaseText: syncJob
        ? formatLiveTaskPhase("sync", syncJob.phase, cur, tot, syncJob.item_id)
        : t("phase_sync_starting"),
      current: cur,
      total: tot,
      startedAt,
    };
  }

  private _scheduleThrottledSettingsRefresh(): void {
    const now = Date.now();
    if (now - this._lastSettingTabRefreshAt >= 200) {
      this._lastSettingTabRefreshAt = now;
      if (this._settingTabRefreshThrottleTimer) {
        clearTimeout(this._settingTabRefreshThrottleTimer);
        this._settingTabRefreshThrottleTimer = null;
      }
      this._refreshSettingTabIfOpen();
      return;
    }
    if (this._settingTabRefreshThrottleTimer) return;
    this._settingTabRefreshThrottleTimer = setTimeout(() => {
      this._settingTabRefreshThrottleTimer = null;
      this._lastSettingTabRefreshAt = Date.now();
      this._refreshSettingTabIfOpen();
    }, 200);
  }

  getQuarantinedBinDir(): string | null {
    return this._quarantinedBinDir;
  }

  private _refreshSettingTabIfOpen(): void {
    const tab = this._settingTab as unknown as {
      refreshIfOpen?: () => void;
      display?: () => void;
    } | null;
    if (!tab) return;
    if (typeof tab.refreshIfOpen === "function") {
      tab.refreshIfOpen();
    } else if (typeof tab.display === "function") {
      tab.display();
    }
  }

  dismissQuarantineBanner(): void {
    this._quarantinedBinDir = null;
    this._emitStateChanged();
    this._refreshSettingTabIfOpen();
  }

  getLastAutoSyncError(): { message: string; at: number } | null {
    return this._lastAutoSyncError;
  }

  clearLastAutoSyncError(): void {
    this._lastAutoSyncError = null;
    this._emitStateChanged();
  }

  getPendingReleaseNotesVersion(): string | null {
    return this._pendingReleaseNotesVersion;
  }

  dismissPendingReleaseNotes(): void {
    const v = this._pendingReleaseNotesVersion || this.manifest?.version;
    this._pendingReleaseNotesVersion = null;
    if (v) {
      this.settings.last_seen_version = v;
      void this.saveSettings();
    }
    this._emitStateChanged();
    this._refreshSettingTabIfOpen();
  }

  getClient(): PaperForgeClient {
    if (!this._client) {
      const vaultPath =
        (this.app.vault.adapter as unknown as { basePath?: string })
          ?.basePath ?? "";
      const transport = new NodeProcessTransport({
        vaultPath,
      });
      this._client = new PaperForgeClient({ transport });
      this._unsubscribeDaemon?.();
      this._unsubscribeDaemon = this._client.onDaemonEvent((ev) => {
        this._handleDaemonPushEvent(ev);
      });
    }
    return this._client;
  }

  private _handleDaemonPushEvent(ev: {
    event: string;
    data?: Record<string, unknown>;
  }): void {
    if (ev.event === "task.updated" && ev.data) {
      const job = ev.data as unknown as DaemonJobDto;
      if (job.job_id) {
        const isActive =
          job.status === "queued" ||
          job.status === "running" ||
          job.status === "cancelling";
        if (isActive) {
          this._daemonJobs.set(job.job_id, job);
        } else {
          this._daemonJobs.delete(job.job_id);
        }
        this._emitStateChanged(job.item_id ? [job.item_id] : []);
        if (
          job.kind === "runtime.install" ||
          job.kind === "runtime.update" ||
          job.kind === "runtime.repair"
        ) {
          if (!isActive) {
            const termStatus: "succeeded" | "failed" | "cancelled" =
              job.status === "succeeded"
                ? "succeeded"
                : job.status === "cancelled"
                  ? "cancelled"
                  : "failed";
            (
              this._settingTab as unknown as {
                onDaemonRuntimeJobFinished?: (
                  status: "succeeded" | "failed" | "cancelled",
                  detail?: string
                ) => void;
              } | null
            )?.onDaemonRuntimeJobFinished?.(
              termStatus,
              String(job.error ?? "")
            );
            if (job.status === "succeeded") {
              void this.refreshBaseSnapshot().catch(() => undefined);
            }
            this._settingTab?._refreshAllReadModels({ background: true });
            this._refreshSettingTabIfOpen();
          } else {
            this._scheduleThrottledSettingsRefresh();
          }
        } else if (job.kind === "sync") {
          if (isActive) {
            this._scheduleThrottledSettingsRefresh();
          } else {
            this._refreshSettingTabIfOpen();
          }
        }
      }
      return;
    }
    if (ev.event === "notice.push" && ev.data) {
      const nid = String(ev.data.notice_id ?? "");
      const code = String(ev.data.code ?? "");
      const suppressRuntimeInstall = Boolean(
        (
          this._settingTab as unknown as {
            isRuntimeInstallPollingActive?: () => boolean;
          } | null
        )?.isRuntimeInstallPollingActive?.()
      );
      const formatted = formatDaemonNotice(
        {
          notice_id: nid,
          code,
          level: String(ev.data.level ?? "info"),
          title: String(ev.data.title ?? ""),
          detail: String(ev.data.detail ?? ""),
        },
        { suppressRuntimeInstall }
      );
      const rawLevel = String(ev.data.level ?? "info").toLowerCase();
      if (formatted) {
        this._recordDaemonNotice(
          nid || formatted.message,
          rawLevel,
          formatted.message
        );
        if (rawLevel === "error" || code === "runtime.install.done") {
          new Notice(formatted.message, formatted.durationMs);
        }
      }
      if (nid) {
        void this._client?.daemonAckNotice(nid).catch(() => undefined);
      }
      this._settingTab?._refreshAllReadModels({ background: true });
      return;
    }
    if (ev.event === "state.changed") {
      const seq = Number(ev.data?.seq ?? -1);
      if (seq > 0 && seq !== this._lastStateSeq) {
        this._lastStateSeq = seq;
        this._client?.invalidateCache();
        void this.refreshBaseSnapshot().catch(() => undefined);
      }
    }
  }

  getUpgradePlanCache(): VaultUpgradePlanDto | null {
    return this._upgradePlanCache;
  }

  isUpgradeBannerDismissed(): boolean {
    return this._upgradeBannerDismissedForSession;
  }

  dismissUpgradeBannerForSession(): void {
    this._upgradeBannerDismissedForSession = true;
    this._emitStateChanged();
  }

  async refreshUpgradePlan(): Promise<VaultUpgradePlanDto | null> {
    try {
      const plan = await this.getClient().vaultUpgradePlan();
      this._upgradePlanCache = plan;
      this._emitStateChanged();
      return plan;
    } catch {
      return this._upgradePlanCache;
    }
  }

  async openUpgradeModal(): Promise<void> {
    const plan = this._upgradePlanCache ?? (await this.refreshUpgradePlan());
    if (!plan) {
      new Notice(t("main_upgrade_plan_unavailable"));
      return;
    }
    new PaperForgeUpgradeModal(this.app, this.getClient(), plan, {
      onDismissForSession: () => this.dismissUpgradeBannerForSession(),
      onUpgraded: async () => {
        await this.refreshUpgradePlan();
        await this.refreshBaseSnapshot().catch(() => undefined);
        this._settingTab?.display();
      },
    }).open();
  }

  /** Read-only view of the Python-published runtime pointer.
   *
   * The pointer is the only runtime truth (#174): the plugin never resolves an
   * installed-but-unpublished environment. Nothing here creates or changes
   * runtime state — installation is the CLI's job. */
  getManagedRuntime(): { readPointer(): PointerInfo | null } {
    return { readPointer: () => readRuntimePointer() };
  }

  /** Resolved backend command for diagnostics, or null when no pointer is
   * published yet. */
  _getPythonCommand(): { path: string; args: string[] } | null {
    const run = resolveRuntimeCommand(readRuntimePointer());
    return run ? { path: run.command, args: [...run.args] } : null;
  }

  /**
   * Small Plugin-owned module-navigation entrypoint (#356 recovery seam).
   * Opens the PaperForge settings tab, then reuses the settings tab's own
   * `_handleCardNavigation` so cards land on the real module detail — never
   * the settings homepage. The private `_settingTab` stays private: Views
   * reach navigation only through this method. No action is dispatched, no
   * build/embedding runs. Returns false when navigation is unavailable so
   * callers show an explicit "unavailable" message instead of silently
   * doing nothing.
   */
  openModuleSettings(module: string): boolean {
    const tab = this._settingTab;
    // this.app.setting is Obsidian-internal (absent from the public App
    // type): narrow through unknown so narrowing, not `any`, governs.
    const settingApp = this.app as unknown as {
      setting?: {
        open?: unknown;
        openTabById?: unknown;
      };
    };
    const setting = settingApp.setting;
    // Obsidian 1.14: Setting.open() crashes when no settings tab has ever
    // been registered (openTabById finds the tab AND parents the modal, so
    // open() must come second). Order: tab → detail → open.
    const openSettings =
      typeof setting?.open === "function"
        ? setting.open.bind(setting)
        : undefined;
    const openTab =
      typeof setting?.openTabById === "function"
        ? (setting.openTabById as (id: string) => void).bind(setting)
        : undefined;
    if (
      !tab ||
      typeof tab._handleCardNavigation !== "function" ||
      !openSettings ||
      !openTab
    ) {
      new Notice(t("main_settings_nav_unavailable"), 6000);
      return false;
    }
    const found = openTab("paperforge");
    tab._handleCardNavigation(module);
    openSettings();
    return found !== null && found !== undefined;
  }

  /** Dashboard recovery entry: open Installation settings and start Setup. */
  openSetupJourney(): boolean {
    const tab = this._settingTab;
    if (!tab || !this.openModuleSettings("installation")) return false;
    tab.openSetupJourney();
    return true;
  }

  /** Diagnostic handle for the console: `app.plugins.plugins.paperforge
   * .getDebugTrace()` prints the client↔backend boundary log (metadata only). */
  getDebugTrace(): string {
    return dumpTrace();
  }

  /** Diagnostic toggle (mirrors the Settings switch; persists the pref). */
  async setDebugTrace(enabled: boolean): Promise<void> {
    this.settings.debug_trace = enabled;
    setTraceEnabled(enabled);
    await this.saveSettings();
  }

  /** One user-facing OCR run path for Settings, Dashboard, and commands. */
  async requestOcrRun(
    scopeOrSkipConfirm: ActionScope | boolean = { kind: "all" }
  ): Promise<void> {
    if (this.getClient().isOperationActive()) {
      new Notice(t("ocr_already_running"));
      return;
    }
    const skipConfirm =
      typeof scopeOrSkipConfirm === "boolean" ? scopeOrSkipConfirm : false;
    const scope: ActionScope =
      typeof scopeOrSkipConfirm === "boolean"
        ? { kind: "all" }
        : scopeOrSkipConfirm;
    if (scope.kind === "papers" && scope.keys?.some((key) => !key.trim())) {
      new Notice(t("ocr_scope_empty"));
      return;
    }
    const snapshot: ActionScope =
      scope.kind === "papers"
        ? {
            kind: "papers",
            keys: [
              ...new Set(
                (scope.keys ?? []).map((key) => key.trim()).filter(Boolean)
              ),
            ],
          }
        : { kind: scope.kind };
    if (
      snapshot.kind !== "all" &&
      (snapshot.kind !== "papers" || !snapshot.keys?.length)
    ) {
      new Notice(t("ocr_scope_empty"));
      return;
    }
    let scopeLabel =
      snapshot.kind === "papers"
        ? `${t("ocr_scope_papers")} (${snapshot.keys!.length}): ${snapshot.keys!.join(", ")}`
        : "";
    let checkedCount = -1;
    if (snapshot.kind === "all") {
      try {
        const data = await this.getClient().dashboardStats();
        if (!Array.isArray(data.items))
          throw new Error("Library impact unavailable");
        checkedCount = data.items.filter(
          (item: any) => item?.do_ocr === true
        ).length;
        scopeLabel =
          checkedCount > 0
            ? `${t("ocr_scope_all")} (${data.items.length}, ${checkedCount} do_ocr)`
            : `${t("ocr_scope_all")} (${data.items.length}) — ${t("ocr_scope_all_unselected_warn")}`;
      } catch {
        new Notice(t("ocr_scope_unavailable"));
        return;
      }
    }

    const start = () => {
      if (this.getClient().isOperationActive()) {
        new Notice(t("ocr_already_running"));
        return;
      }
      this._ocrRunning = true;
      this._ocrProgress = { current: 0, total: 1, key: "" };
      this._settingTab?.display();
      this._emitStateChanged();
      void (async () => {
        // Ticket 07 step 3: the shared client owns the OCR run — the same
        // canonical `ocr.run` action, #137 NDJSON progress, availability
        // gating, and cooperative Stop that the OCR Workspace uses. No
        // second argv assembly, no second child-process owner.
        const request: ActionRequest = {
          action_id: "ocr.run",
          scope: snapshot,
          confirm: "ocr.run",
        };
        let sawCancelled = false;
        const failedKeys: string[] = [];
        const result = await this.getClient().runAction(request, {
          onEvent: (event) => {
            if (event.event === "cancelled") sawCancelled = true;
            if (
              event.event === "start" ||
              event.event === "phase" ||
              event.event === "progress" ||
              event.event === "item_result"
            ) {
              this._ocrProgress = {
                current: Number(event.current ?? this._ocrProgress.current),
                total: Number(event.total ?? this._ocrProgress.total),
                key: String(event.item_id ?? this._ocrProgress.key),
              };
              if (
                event.event === "item_result" &&
                event.status !== "succeeded" &&
                event.status !== "noop" &&
                event.status !== "skipped" &&
                event.status !== "done" &&
                event.status !== "done_degraded" &&
                event.status !== "ok"
              ) {
                failedKeys.push(String(event.item_id ?? ""));
              }
              this._refreshSettingTabIfOpen();
              this._emitStateChanged(
                this._ocrProgress.key ? [this._ocrProgress.key] : []
              );
            }
          },
        });
        if (result.ok) {
          new Notice(t("ocr_run_complete"));
        } else if (result.cancelled || sawCancelled) {
          new Notice(t("ocr_stopped_notice"));
        } else {
          // Surface the real reason instead of a generic failure — failed
          // keys, then the registry's availability_reason, then the exit
          // code.
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
          const detail =
            failedKeys.filter(Boolean).join(", ") ||
            (payloadReason ? formatHumanError(payloadReason) : "") ||
            formatHumanError(
              `exit code ${result.exitCode}`,
              "ocr_error_notice"
            );
          new Notice(t("ocr_failed_notice") + ": " + detail, 8000);
        }
        this._ocrRunning = false;
        this._emitStateChanged();
        this._refreshSettingTabIfOpen();
        const vaultPath = (this.app.vault.adapter as any).basePath as string;
        this._autoSync(vaultPath);
      })().catch((error: Error) => {
        this._ocrRunning = false;
        this._emitStateChanged();
        new Notice(
          t("ocr_failed_notice") +
            ": " +
            formatHumanError(error, "ocr_error_notice"),
          8000
        );
        this._refreshSettingTabIfOpen();
      });
    };

    if (skipConfirm && (snapshot.kind !== "all" || checkedCount > 0)) {
      start();
      return;
    }

    new PaperForgeConfirmModal(
      this.app,
      {
        title: t("ocr_run_confirm_title"),
        effectLabel: `${scopeLabel}. ${t("ocr_run_confirm_body")}`,
        confirmLabel: t("ocr_run_confirm_title"),
        cancelLabel: t("maintenance_confirm_cancel"),
      },
      start
    ).open();
  }
  async onload() {
    this._unloaded = false;
    await this.loadSettings();
    this.applyUiThemeMode();
    // Diagnostic boundary trace (metadata only; see client/trace.ts).
    setTraceEnabled(this.settings.debug_trace === true);
    setLanguage(this.app, this.settings.language);

    // (OCR run/redo credential gating is Python-side: the canonical action
    // registry owns availability; the client gates on it — #173/C1.)

    this.registerView(
      VIEW_TYPE_PAPERFORGE,
      (leaf) => new PaperForgeStatusView(leaf)
    );

    this.registerView(
      VIEW_TYPE_OCR_WORKSPACE,
      (leaf) => new OcrWorkspaceView(leaf, this)
    );

    this.registerView(
      VIEW_TYPE_PAPERFORGE_PDF,
      (leaf) => new PaperForgePdfView(leaf, this)
    );

    this.registerView(
      VIEW_TYPE_UI_GALLERY,
      (leaf) => new PaperForgeGalleryView(leaf, this)
    );

    const regBases = (
      this as unknown as {
        registerBasesView?: (
          viewType: string,
          registration: unknown
        ) => boolean;
      }
    ).registerBasesView;
    if (typeof regBases === "function") {
      regBases.call(this, VIEW_TYPE_PF_BASE_TABLE, {
        name: t("base_view_name") || "PaperForge Library",
        icon: "library",
        factory: (controller: unknown, containerEl: HTMLElement) =>
          new PaperForgeBasesView(controller as any, containerEl, this),
        options: () => [
          {
            type: "group",
            displayName: t("base_opt_group_layout") || "Layout & Density",
            items: [
              {
                key: "row_density",
                type: "dropdown",
                displayName: t("base_opt_density") || "Row density",
                default: "comfortable",
                options: {
                  comfortable: t("base_opt_density_comfortable") || "Standard",
                  compact: t("base_opt_density_compact") || "Compact",
                  spacious: t("base_opt_density_spacious") || "Spacious",
                },
              },
              {
                key: "show_annotations",
                type: "toggle",
                displayName: t("main_base_opt_annotations"),
                default: true,
              },
              {
                key: "show_summary_footer",
                type: "toggle",
                displayName:
                  t("base_opt_summary_footer") || "Show summary footer",
                default: false,
              },
            ],
          },
          {
            type: "group",
            displayName: t("base_opt_group_workbench") || "Workbench & Embed",
            items: [
              {
                key: "show_filter_bar",
                type: "toggle",
                displayName: t("base_opt_show_filter_bar") || "Show filter bar",
                default: true,
              },
              {
                key: "show_checkboxes",
                type: "toggle",
                displayName:
                  t("base_opt_show_checkboxes") ||
                  "Show multi-select checkboxes",
                default: true,
              },
              {
                key: "row_click_action",
                type: "dropdown",
                displayName: t("base_opt_click_action") || "Title click action",
                default: "open_note",
                options: {
                  open_note: t("base_opt_click_note") || "Open note",
                  open_pdf: t("base_opt_click_pdf") || "Open PDF",
                  open_split: t("base_opt_click_split") || "Split PDF & Note",
                },
              },
            ],
          },
        ],
      });
    }

    this.addRibbonIcon(
      PF_ICON_ID,
      t("ribbon_dashboard") || "PaperForge Dashboard",
      () => PaperForgeStatusView.open(this as any)
    );
    this.addRibbonIcon(
      "library",
      t("ribbon_literature_hub") || "PaperForge Literature Hub",
      () => {
        void this.openLiteratureBase();
      }
    );

    // #99 (owner decision): redo is an internal maintenance command, NOT
    // exposed to users. No ribbon, no command — the CLI keeps it.
    this._settingTab = new PaperForgeSettingTab(this.app, this as any);
    this.addSettingTab(this._settingTab);

    this.addCommand({
      id: "paperforge-status-panel",
      name: t("guide_open"),
      callback: () => PaperForgeStatusView.open(this as any),
    });
    this.addCommand({
      id: "paperforge-open-literature-base",
      name: t("base_open_hub") || "Open Literature Hub Base",
      callback: () => {
        void this.openLiteratureBase();
      },
    });
    this.addCommand({
      id: "paperforge-ocr-workspace",
      name: t("cmd_ocr_workspace") || "Open OCR Workspace",
      callback: () => OcrWorkspaceView.open(this as any),
    });
    this.addCommand({
      id: "open-ui-gallery",
      name: t("cmd_open_ui_gallery") || "Open UI Gallery & Design System",
      callback: () => {
        void this.openUiGallery();
      },
    });
    this.addCommand({
      id: "focus-companion-search",
      name: t("cmd_focus_companion") || "Focus Companion search",
      callback: async () => {
        const view = await PaperForgeStatusView.open(this as any);
        view?._searchInput?.focus();
      },
    });
    this.addCommand({
      id: "open-paper-split-reading",
      name:
        t("cmd_split_reading") ||
        "Open current paper in split PDF and Note view",
      checkCallback: (checking: boolean) => {
        const pdfView = this.app.workspace.getActiveViewOfType?.(
          PaperForgePdfView as any
        ) as PaperForgePdfView | null;
        if (pdfView) {
          const k = String(pdfView.getState?.()?.paperKey ?? "").trim();
          if (k) {
            if (!checking) void this.openPaperSplitReading(k);
            return true;
          }
        }
        const activeFile = this.app.workspace.getActiveFile?.();
        if (activeFile?.path) {
          const cached = this._resolvePaperByPath(activeFile.path);
          if (cached) {
            if (!checking) {
              void this.openPaperSplitReading(
                cached.zotero_key,
                activeFile.path
              );
            }
            return true;
          }
          if (!checking) {
            void this.getClient()
              .resolvePaperContext(activeFile.path)
              .then((ctx) => {
                if (ctx?.kind === "paper" && ctx.zotero_key) {
                  return this.openPaperSplitReading(
                    ctx.zotero_key,
                    activeFile.path
                  );
                }
                new Notice(
                  t("paper_note_missing") || "No active paper selected."
                );
              })
              .catch(() => {
                new Notice(
                  t("paper_note_missing") || "No active paper selected."
                );
              });
          }
          return true;
        }
        return false;
      },
    });

    (
      this.app.workspace as unknown as {
        registerHoverLinkSource?: (
          id: string,
          info: { display: string; defaultMod?: boolean }
        ) => void;
      }
    )?.registerHoverLinkSource?.("paperforge", {
      display: "PaperForge",
      defaultMod: true,
    });

    this.registerDomEvent(
      document,
      "click",
      (evt: MouseEvent) => {
        tryHandleExternalPdfLinkClick(evt, {
          app: this.app,
          baseSnapshot: this._baseSnapshotCache ?? null,
          openPaperPdf: (paperKey: string) => this.openPaperPdf(paperKey),
        });
      },
      true
    );

    for (const a of ACTIONS) {
      // #99 (owner decision): redo is internal-only — never a user command.
      if (a.id === "paperforge-ocr-redo") continue;
      this.addCommand({
        id: a.id,
        name: a.title,
        callback: async () => {
          if (a.id === "paperforge-ocr") {
            this.requestOcrRun();
            return;
          }
          if (a.disabled) {
            new Notice(a.disabledMsg || t("main_action_unavailable"), 6000);
            return;
          }
          // Ticket 07 step 5: command palette routes through the shared
          // client — no second argv assembly, no child_process authority.
          const client = this.getClient();
          try {
            if (a.id === "paperforge-sync") {
              const vp = (this.app.vault.adapter as any).basePath as string;
              this._autoSync(vp);
              return;
            }
            if (a.id === "paperforge-doctor") {
              new Notice(t("dash_checking") || `Running ${a.commandId}...`);
              const report = await client.doctor();
              const ok = (report as { ok?: boolean })?.ok !== false;
              new Notice(
                ok
                  ? a.okMsg || t("dash_doctor_ok")
                  : t("dash_doctor_issues") || "Doctor reported issues",
                ok ? 6000 : 8000
              );
              return;
            }
            if (a.id === "paperforge-repair") {
              new Notice(t("dash_checking") || `Running ${a.commandId}...`);
              await client.repair();
              new Notice(a.okMsg || t("dash_repair_ok"));
              this._settingTab?._refreshAllReadModels();
              return;
            }
            // Unknown tool identity — fail closed, never substitute.
            new Notice(
              t("main_unsupported_tool").replace("{id}", String(a.id)),
              8000
            );
          } catch (err: any) {
            new Notice(
              t("main_tool_failed")
                .replace("{cmd}", String(a.commandId || a.id))
                .replace("{detail}", formatHumanError(err)),
              8000
            );
          }
        },
      });
    }

    this.addCommand({
      id: "paperforge-migrate-config",
      name: t("cmd_migrate_config") || "Migrate legacy configuration",
      callback: () => this._runLegacyConfigMigration(),
    });

    this.addCommand({
      id: "paperforge-vault-upgrade",
      name: t("main_cmd_check_upgrade"),
      callback: () => {
        void this.openUpgradeModal();
      },
    });

    this.addCommand({
      id: "paperforge-quick-switcher",
      name: t("cmd_quick_switcher") || "PaperForge: Quick Switcher (Papers)",
      callback: () => {
        new PaperForgeQuickSwitcherModal(this.app, this, "open").open();
      },
    });

    this.addCommand({
      id: "paperforge-insert-citation",
      name: t("cmd_insert_citation") || "PaperForge: Insert Citation at Cursor",
      editorCallback: () => {
        new PaperForgeQuickSwitcherModal(this.app, this, "cite").open();
      },
    });

    this._registerExtendedCommands();

    this._setupEcosystemHooks();

    this._checkReleaseNotes();

    const vaultBase = (
      this.app.vault.adapter as unknown as { basePath?: string }
    ).basePath;

    const pluginVersion = this.manifest?.version ?? "";

    const minEngineVersion = (
      this.manifest as { minEngineVersion?: string } | undefined
    )?.minEngineVersion;

    const runStartupHydration = () => {
      if (this._unloaded || !vaultBase) return;
      // Fast Rust-native upgrade plan check (< 3ms, zero Python spawned)
      void this.refreshUpgradePlan()
        .then((plan) => {
          if (this._unloaded) return;
          this._refreshSettingTabIfOpen();
          if (
            this.settings._setup_complete === false &&
            this.settings._setup_journey_started !== true &&
            !plan?.provenance?.needs_upgrade
          ) {
            if (!readRuntimePointer()) {
              new Notice(t("main_first_open_ready"), 8000);
            } else {
              new Notice(t("main_new_vault_connect_zotero"), 10000);
            }
          }
        })
        .catch(() => undefined);
      // Non-blocking config mirror hydration (only when Python runtime exists).
      // PF-ARCH-007: _startStateSeqWatcher() MUST run AFTER _hydrateConfigMirrors()
      // so isConfigHydrated() and resolveVaultPaths() are populated first.
      if (readRuntimePointer()) {
        void this._hydrateConfigMirrors(vaultBase).then(() => {
          if (this._unloaded) return;
          this._startStateSeqWatcher(vaultBase);
          this._startConvergenceTimer();
        });
      } else {
        this._startStateSeqWatcher(vaultBase);
        this._startConvergenceTimer();
      }
    };

    const scheduleDeferredStartup = () => {
      if (this._unloaded) return;
      this._startupDeferTimer = setTimeout(() => {
        this._startupDeferTimer = null;
        if (this._unloaded) return;
        const prevNativeBin = resolveNativeDaemonBinary({
          vaultPath: vaultBase,
        });
        const prevMeta = readNativeDaemonMeta();
        const needsDaemonSwap = Boolean(
          pluginVersion &&
          (!prevNativeBin ||
            !prevMeta?.tag ||
            normalizeSemverForCompare(prevMeta.tag) !==
              normalizeSemverForCompare(pluginVersion))
        );
        if (needsDaemonSwap) {
          this._daemonUpdating = true;
          this._emitStateChanged();
          this._refreshSettingTabIfOpen();
        } else {
          runStartupHydration();
        }

        void resolveElectronSessionProxy("https://github.com")
          .then((proxyUrl) => {
            if (proxyUrl && !this._unloaded) {
              setCachedSystemProxy(proxyUrl);
            }
          })
          .catch(() => undefined);

        this._startupDaemonCheckPending = true;
        void ensureNativeDaemonDownloaded(pluginVersion, {
          checkVersionUpdate: true,
          useRemoteTtl: true,
          fetchBuffer:
            typeof requestUrl === "function"
              ? createObsidianRequestFetcher(requestUrl)
              : undefined,
          onBeforeReplace: () => this._client?.shutdownTransportAsync(),
          onReplace: (swapFn) =>
            this._client
              ? this._client.runWithTransportSwap(swapFn)
              : Promise.resolve(swapFn()),
          onQuarantineSuspected: (binDir) => {
            if (this._unloaded) return;
            this._quarantinedBinDir = binDir;
            this._emitStateChanged();
            this._refreshSettingTabIfOpen();
            new Notice(t("main_defender_notice_short"), 8000);
          },
        })
          .then((downloadedBin) => {
            if (this._unloaded) {
              this._daemonUpdating = false;
              return;
            }
            const swapped = Boolean(
              downloadedBin && downloadedBin !== prevNativeBin
            );
            this._daemonUpdating = false;
            if (needsDaemonSwap) {
              this._lastAutoSyncError = null;
              runStartupHydration();
              this._settingTab?._refreshAllReadModels({ background: true });
              this._refreshSettingTabIfOpen();
            } else if (swapped && vaultBase) {
              this._lastAutoSyncError = null;
              void this.refreshUpgradePlan()
                .then(() => {
                  if (!this._unloaded) this._refreshSettingTabIfOpen();
                })
                .catch(() => undefined);
              void this.refreshBaseSnapshot().catch(() => undefined);
              this._settingTab?._refreshAllReadModels({ background: true });
              this._refreshSettingTabIfOpen();
            }
            if (!downloadedBin || !vaultBase) {
              this._notifySettingTabDaemonSwapFinished();
              return;
            }
            const ptr = readRuntimePointer();
            const hubSkillMd = path.join(
              os.homedir(),
              ".paperforge",
              "skills",
              "paperforge",
              "SKILL.md"
            );
            const agentRegFile = path.join(
              os.homedir(),
              ".paperforge",
              "agent-installs.json"
            );
            if (ptr && !fs.existsSync(hubSkillMd)) {
              void this.getClient()
                .skillSyncHub()
                .catch(() => undefined);
            } else if (swapped || fs.existsSync(agentRegFile)) {
              void this.getClient()
                .skillSyncAll()
                .catch(() => undefined);
            }
            if (
              ptr &&
              pluginVersion &&
              !isEngineVersionCompatible(
                ptr.paperforgeVersion,
                pluginVersion,
                minEngineVersion
              )
            ) {
              void this.getClient()
                .daemonSubmitRuntimeUpdate(pluginVersion)
                .then((res) => {
                  if (this._unloaded) return;
                  if (res?.accepted && !res?.coalesced) {
                    new Notice(
                      t("main_runtime_autoupdate_started").replace(
                        "{version}",
                        pluginVersion
                      ),
                      6000
                    );
                  }
                  this._emitStateChanged();
                  this._refreshSettingTabIfOpen();
                })
                .catch(() => undefined)
                .finally(() => {
                  if (!this._unloaded)
                    this._notifySettingTabDaemonSwapFinished();
                });
              return;
            }
            this._notifySettingTabDaemonSwapFinished();
          })
          .catch(() => {
            this._daemonUpdating = false;
            if (this._unloaded) return;
            if (needsDaemonSwap) {
              runStartupHydration();
              this._refreshSettingTabIfOpen();
            }
            this._notifySettingTabDaemonSwapFinished();
          })
          .finally(() => {
            this._startupDaemonCheckPending = false;
          });
      }, 1500);
    };

    // Defer ALL heavy startup hydration until after Obsidian's layout is ready + idle
    const ws = this.app.workspace as unknown as {
      onLayoutReady?: (cb: () => void) => void;
    };
    if (typeof ws?.onLayoutReady === "function") {
      ws.onLayoutReady(scheduleDeferredStartup);
    } else {
      scheduleDeferredStartup();
    }
  }

  private _needsConfigMigration = false;

  /** Thin plugin-assisted migration (#142 §12): dry-run -> confirm -> migrate
   * -> re-hydrate -> purge legacy domain values from data.json. */
  private _runLegacyConfigMigration(): void {
    const vaultPath = (
      this.app.vault.adapter as unknown as { basePath?: string }
    ).basePath;
    if (!vaultPath) return;
    void (async () => {
      let dryError: unknown = null;
      const dry = await this.getClient()
        .configMigrate(true)
        .catch((e) => {
          dryError = e;
          return null;
        });
      if (dryError) {
        // The dry run is the authority's verdict: a legacy file it cannot
        // migrate must not be offered as "No conflicts".
        new Notice(
          t("main_config_migrate_failed").replace(
            "{detail}",
            formatHumanError(dryError)
          ),
          10000
        );
        return;
      }
      const summary =
        dry && dry.warnings?.length
          ? dry.warnings.join("\n")
          : "No conflicts; legacy path keys will move under vault_config.";
      new ConfirmMigrationModal(this.app, summary, async () => {
        try {
          await this.getClient().configMigrate(false);
        } catch (e) {
          // A failed migrate must not fall through to the success path
          // (re-hydrate, clear the flag, "configuration migrated").
          new Notice(
            t("main_config_migrate_failed").replace(
              "{detail}",
              formatHumanError(e)
            ),
            10000
          );
          return;
        }
        // Re-hydrate mirrors from the canonical config, then purge the
        // legacy domain values from data.json (#142 §12 step 4/5).
        try {
          const list = await this.getClient().configList();
          applyPathConfigFromList(this.settings, list.fields);
          const pick = (key: string) =>
            list.fields.find((f) => f.key === key)?.value;
          const apiBase = String(pick("vector_db_api_base") ?? "");
          const apiModel = String(pick("vector_db_api_model") ?? "");
          const providerType = String(pick("vector_db_provider_type") ?? "");
          const ocrJobUrl = String(pick("paddleocr_job_url") ?? "");
          const ocrModel = String(pick("paddleocr_model") ?? "");
          const agentPlatform = String(pick("agent_platform") ?? "");
          if (apiBase) this.settings.vector_db_api_base = apiBase;
          if (apiModel) this.settings.vector_db_api_model = apiModel;
          if (providerType)
            this.settings.vector_db_provider_type = providerType;
          if (ocrJobUrl) this.settings.paddleocr_job_url = ocrJobUrl;
          if (ocrModel) this.settings.paddleocr_model = ocrModel;
          if (agentPlatform) this.settings.agent_platform = agentPlatform;
        } catch {
          /* mirrors keep prior values; canonical file is authoritative */
        }
        this._needsConfigMigration = false;
        await this.saveSettings();
        new Notice(t("main_config_migrated"));
      }).open();
    })();
  }

  /** Fast non-blocking stat fingerprint of Zotero DB so idle ticks spawn 0 Python processes. */
  private async _readZoteroFingerprint(): Promise<string | null> {
    const zDir = this.settings?.zotero_data_dir?.trim();
    if (!zDir) return null;
    try {
      const dbStat = await fs.promises.stat(path.join(zDir, "zotero.sqlite"));
      let walPart = "";
      try {
        const walStat = await fs.promises.stat(
          path.join(zDir, "zotero.sqlite-wal")
        );
        walPart = `|${walStat.mtimeMs}:${walStat.size}`;
      } catch {
        // WAL file absent when Zotero is closed
      }
      return `${dbStat.mtimeMs}:${dbStat.size}${walPart}`;
    } catch {
      return null;
    }
  }

  /** Periodic convergence check: skips Python sync completely if Zotero DB hasn't changed. */
  private _maybeAutoSync(vaultPath: string): void {
    if (this._autoSyncRunning) return;
    if (this.settings?._setup_complete === false) return;
    const libCap = this.settings?.capabilityState?.library;
    if (
      libCap?.reason?.code === "library.zotero_missing" ||
      libCap?.capability_state === "missing_input" ||
      libCap?.user_state === "setup_required"
    ) {
      return;
    }
    if (!readRuntimePointer()) return;
    void (async () => {
      const sig = await this._readZoteroFingerprint();
      if (
        sig &&
        this._lastSyncedZoteroSig &&
        sig === this._lastSyncedZoteroSig
      ) {
        return;
      }
      this._autoSync(vaultPath, sig ?? undefined);
    })();
  }

  private _startConvergenceTimer() {
    if (this._unloaded) return;
    const vaultPath = (this.app.vault.adapter as any).basePath as string;
    const cadenceMs =
      Math.max(30, this.settings.autoSyncIntervalSeconds ?? 120) * 1000;

    if (this.settings.autoSyncEnabled === false) {
      return;
    }
    if (this._pollTimer) {
      clearInterval(this._pollTimer);
      this._pollTimer = null;
    }
    this._maybeAutoSync(vaultPath);
    this._pollTimer = setInterval(() => {
      if (this._unloaded || !isConfigHydrated()) return;
      this._maybeAutoSync(vaultPath);
    }, cadenceMs);
  }

  // T8: mtime scanner deleted — the convergence tick fires sync directly.

  private _autoSync(vaultPath: string, expectedZoteroSig?: string) {
    if (this._autoSyncRunning) return;
    if (this.settings?._setup_complete === false) return;
    if (this._upgradePlanCache?.provenance?.needs_upgrade === true) {
      return;
    }
    this._autoSyncRunning = true;
    this._syncStartedAt = Date.now();
    this._emitStateChanged();
    this._refreshSettingTabIfOpen();

    void (async () => {
      let ok = false;
      try {
        const client = this.getClient();
        const result = await client.sync();
        ok = result?.ok !== false;
        if (ok) {
          this._lastAutoSyncError = null;
          this._lastSyncTime = new Date().toLocaleTimeString();
          this._lastSyncedZoteroSig =
            expectedZoteroSig ?? (await this._readZoteroFingerprint());
          void orchestrateFromSync(JSON.stringify(result), {
            runAction: (req) => client.runAction(req),
            silentPending: true,
          });
          this._settingTab?._refreshAllReadModels({ background: true });
          if (vaultPath) this._startStateSeqWatcher(vaultPath);
          if (
            typeof (
              this.app as unknown as { workspace?: { trigger?: unknown } }
            )?.workspace?.trigger === "function"
          ) {
            void this.refreshBaseSnapshot().catch(() => undefined);
          }
        } else {
          const errObj = (
            result as { error?: { code?: string; message?: string } }
          )?.error;
          const isZoteroUnconfigured =
            errObj?.code === "library.zotero_missing" ||
            /zotero data directory not configured/i.test(errObj?.message || "");
          this._lastAutoSyncError = isZoteroUnconfigured
            ? null
            : {
                message: formatHumanError(errObj?.message || "sync_failed"),
                at: Date.now(),
              };
        }
      } catch (err: unknown) {
        ok = false;
        const rawMsg = err instanceof Error ? err.message : String(err ?? "");
        const isZoteroUnconfigured =
          /library\.zotero_missing|zotero data directory not configured/i.test(
            rawMsg
          );
        if (isZoteroUnconfigured) {
          this._lastAutoSyncError = null;
        } else if (
          // Never surface transient internal daemon hot-swap restarts as sync errors
          !this._daemonUpdating &&
          !rawMsg.toLowerCase().includes("daemon shut down")
        ) {
          this._lastAutoSyncError = {
            message: formatHumanError(err),
            at: Date.now(),
          };
        }
      } finally {
        this._autoSyncRunning = false;
        this._syncStartedAt = null;
        this._memoryStatusText = null;
        this._emitStateChanged();
        this._refreshSettingTabIfOpen();
      }
    })();
  }

  // T8: OCR mtime scanning deleted — the convergence tick fires sync only.

  readPaperforgeJson(): Record<string, string> {
    // #142 / C0: removed — the plugin never parses paperforge.json. Values
    // come from `paperforge config list` (hydrated into settings mirrors).
    return {};
  }

  savePaperforgeJson(_pathConfig: Record<string, string | undefined>): void {
    // #142 / C0: removed — the plugin never writes paperforge.json. Mutations
    // route through `paperforge config set/unset` (config-client). Retired
    // stub: no Console noise, no behavior change.
  }

  /** Open a paper inside the built-in Obsidian sidecar PDF annotator tab. */
  async openPaperPdf(
    paperKey: string,
    opts?: { page?: number; annId?: string }
  ): Promise<void> {
    if (!paperKey) return;
    const state: PdfAnnotatorOpenState = {
      paperKey,
      page: opts?.page,
      annId: opts?.annId,
    };
    const existing = this.app.workspace
      .getLeavesOfType(VIEW_TYPE_PAPERFORGE_PDF)
      .find((leaf) => {
        const st = leaf.getViewState().state as
          | Partial<PdfAnnotatorOpenState>
          | undefined;
        return st?.paperKey === paperKey;
      });
    const leaf = existing ?? this.app.workspace.getLeaf("tab");
    await leaf.setViewState({
      type: VIEW_TYPE_PAPERFORGE_PDF,
      active: true,
      state: { ...state },
    });
    await this.app.workspace.revealLeaf(leaf);
    if (existing && opts?.page && existing.view instanceof PaperForgePdfView) {
      existing.view.scrollToPage(opts.page, opts.annId);
    }
  }

  /** Open PDF reader side-by-side with its formal Markdown note in a vertical split. */
  async openPaperSplitReading(
    paperKey: string,
    notePath?: string
  ): Promise<void> {
    if (!paperKey) return;
    await this.openPaperPdf(paperKey);
    let targetPath =
      notePath ||
      this._baseSnapshotCache?.rows?.[paperKey]?.main_note_path ||
      "";
    if (!targetPath) {
      try {
        const dash = await this.getClient().dashboardStats();
        const found = (dash?.items ?? []).find(
          (it: {
            zotero_key?: string;
            main_note_path?: string;
            note_path?: string;
          }) => it?.zotero_key === paperKey
        );
        targetPath = String(
          found?.main_note_path || found?.note_path || ""
        ).trim();
      } catch {
        // Ignore fallback lookup errors
      }
    }
    await openVaultFileSafely(this.app, {
      filePath: targetPath || null,
      zoteroKey: paperKey,
      mod: "split",
    });
  }

  /** Open the 4-stage setup wizard inside a dedicated Obsidian modal. */
  openSetupWizardModal(): boolean {
    if (!this._settingTab) return false;
    (this._settingTab as unknown as { _setupStage: number })._setupStage = 1;
    (
      this._settingTab as unknown as {
        _setupJourneyDismissedForSession?: boolean;
      }
    )._setupJourneyDismissedForSession = false;
    new PaperForgeSetupWizardModal(this.app, this._settingTab as any).open();
    return true;
  }

  getBaseSnapshotCache(): BaseTableSnapshotDto | null {
    return this._baseSnapshotCache ?? null;
  }

  getBaseFilters(viewKey: string): {
    query?: string;
    domain?: string;
    collection?: string;
    status?: string;
    minIf?: number;
  } {
    if (!this._localFiltersCache) {
      const appAny = this.app as unknown as {
        loadLocalStorage?: (k: string) => unknown;
      };
      let loaded: unknown = null;
      if (typeof appAny?.loadLocalStorage === "function") {
        try {
          loaded = appAny.loadLocalStorage("paperforge:base-filters");
        } catch {
          loaded = null;
        }
      }
      if (loaded && typeof loaded === "object" && !Array.isArray(loaded)) {
        this._localFiltersCache = {
          ...(loaded as Record<string, Record<string, unknown>>),
        } as NonNullable<PaperForgePlugin["_localFiltersCache"]>;
      } else {
        this._localFiltersCache = { ...(this.settings._baseFilters ?? {}) };
      }
    }
    const map = this._localFiltersCache;
    return { ...(map[viewKey] ?? map.default ?? {}) };
  }

  setBaseFilters(
    viewKey: string,
    next: {
      query?: string;
      domain?: string;
      collection?: string;
      status?: string;
      minIf?: number;
    }
  ): void {
    const map = this._localFiltersCache ?? {
      ...(this.settings._baseFilters ?? {}),
    };
    map[viewKey || "default"] = { ...next };
    this._localFiltersCache = map;
    const appAny = this.app as unknown as {
      saveLocalStorage?: (k: string, v: unknown) => void;
    };
    if (typeof appAny?.saveLocalStorage === "function") {
      try {
        appAny.saveLocalStorage("paperforge:base-filters", map);
        return;
      } catch {
        // Fall through to settings fallback
      }
    }
    if (!this.settings._baseFilters) {
      this.settings._baseFilters = {};
    }
    this.settings._baseFilters[viewKey || "default"] = { ...next };
    void this.saveSettings();
  }

  /** Zero-idle shared background activity projection for Companion / Base UI strips. */
  getActiveBackgroundTasks(): ActiveBackgroundTask[] {
    const tasks: ActiveBackgroundTask[] = [];
    for (const dj of this._daemonJobs.values()) {
      const isRuntimeJob = dj.kind.startsWith("runtime.");
      const mappedKind: ActiveBackgroundTask["kind"] =
        dj.kind === "upgrade.heal"
          ? "heal"
          : isRuntimeJob
            ? "runtime"
            : dj.kind === "ocr"
              ? "ocr"
              : dj.kind === "embed"
                ? "embed"
                : "sync";
      if (mappedKind !== "heal" && tasks.some((x) => x.kind === mappedKind)) {
        continue;
      }
      const tot = dj.total > 0 ? dj.total : undefined;
      const cur = dj.total > 0 ? dj.current : undefined;
      const livePhase =
        mappedKind === "sync" || mappedKind === "runtime"
          ? formatLiveTaskPhase(dj.kind, dj.phase, cur, tot, dj.item_id)
          : undefined;
      tasks.push({
        kind: mappedKind,
        label:
          mappedKind === "heal"
            ? t("main_activity_heal")
            : mappedKind === "runtime"
              ? t("activity_runtime_updating") || "Updating compute engine"
              : mappedKind === "ocr"
                ? t("activity_ocr") || "Parsing fulltext"
                : mappedKind === "embed"
                  ? t("activity_embed") || "Building embeddings"
                  : t("activity_syncing") || "Syncing library",
        phase: livePhase,
        startedAt: dj.started_at > 0 ? dj.started_at * 1000 : undefined,
        current: cur,
        total: tot,
        key: dj.item_id || undefined,
        jobId: dj.job_id,
      });
    }
    if (this._daemonUpdating && !tasks.some((x) => x.kind === "runtime")) {
      tasks.push({
        kind: "runtime",
        label: t("activity_daemon_updating") || "Updating local service",
      });
    }
    if (this._autoSyncRunning && !tasks.some((x) => x.kind === "sync")) {
      tasks.push({
        kind: "sync",
        label: t("activity_syncing") || "Syncing library",
        phase: t("phase_sync_starting"),
        startedAt: this._syncStartedAt ?? undefined,
      });
    }
    if (this._ocrRunning || this.getClient().isOperationActive()) {
      const prog = this._ocrProgress;
      tasks.push({
        kind: "ocr",
        label: t("activity_ocr") || "Parsing fulltext",
        current: prog?.total > 0 ? prog.current : undefined,
        total: prog?.total > 0 ? prog.total : undefined,
        key: prog?.key || undefined,
      });
    }
    if (this._embedProcess) {
      const ep = this._embedProgress;
      tasks.push({
        kind: "embed",
        label: t("activity_embed") || "Building embeddings",
        current: ep?.total > 0 ? ep.current : undefined,
        total: ep?.total > 0 ? ep.total : undefined,
        key: ep?.key || undefined,
      });
    }
    return tasks;
  }

  isOcrRunningForKey(key: string): boolean {
    if (!key || this._ocrProgress?.key !== key) return false;
    try {
      return this.getClient().isOperationActive();
    } catch {
      return false;
    }
  }

  private _emitStateChanged(changedKeys: string[] = []): void {
    this._updateStatusBar();
    const ws = (
      this.app as unknown as {
        workspace?: { trigger?: (name: string, data?: unknown) => void };
      }
    )?.workspace;
    if (typeof ws?.trigger === "function") {
      ws.trigger("paperforge:state-changed", {
        snapshot: this._baseSnapshotCache,
        changedKeys,
      });
    }
  }

  private _notifySettingTabDaemonSwapFinished(): void {
    (
      this._settingTab as unknown as {
        onDaemonSwapFinished?: () => void;
      } | null
    )?.onDaemonSwapFinished?.();
  }

  private _resolvePaperByPath(
    filePath: string
  ): import("./client/paperforge-client").BasePaperRowDto | null {
    const norm = (filePath || "").replace(/\\/g, "/");
    if (!norm) return null;
    const rows = this._baseSnapshotCache?.rows;
    if (!rows) return null;
    for (const row of Object.values(rows)) {
      if ((row.main_note_path || "").replace(/\\/g, "/") === norm) {
        return row;
      }
    }
    return null;
  }

  private _recordDaemonNotice(
    id: string,
    level: string,
    message: string
  ): void {
    const cleanMsg = String(message || "").trim();
    if (!cleanMsg) return;
    this._recentDaemonNotices = [
      { id, level, message: cleanMsg, at: Date.now() },
      ...this._recentDaemonNotices.filter((x) => x.id !== id),
    ].slice(0, 5);
    this._updateStatusBar();
  }

  private _closeStatusPopover(): void {
    this._statusPopoverCleanup?.();
    this._statusPopoverCleanup = null;
    this._statusPopoverEl?.remove();
    this._statusPopoverEl = null;
  }

  private _toggleStatusPopover(): void {
    if (this._statusPopoverEl) {
      this._closeStatusPopover();
      return;
    }
    const anchor = this._statusBarEl;
    const doc =
      anchor?.ownerDocument ??
      (typeof document !== "undefined" ? document : null);
    if (!doc?.body) return;

    const pop = doc.createElement("div");
    pop.className = "pf-status-popover";
    pop.setAttribute("data-pf-testid", "pf-status-popover");
    pop.setAttribute("role", "dialog");

    const tasks = this.getActiveBackgroundTasks();
    const notices = this._recentDaemonNotices;
    const hasWarn = notices.some(
      (n) => n.level === "error" || n.level === "warning"
    );
    const isZh = t("nav_close") === "关闭";

    const head = doc.createElement("div");
    head.className = "pf-status-popover-head";
    const title = doc.createElement("span");
    title.className = "pf-status-popover-title";
    title.textContent = "PaperForge";
    const pill = doc.createElement("span");
    pill.className = `pf-status-popover-pill${
      tasks.length > 0 ? " is-busy" : hasWarn ? " is-warn" : ""
    }`;
    pill.textContent =
      tasks.length > 0
        ? isZh
          ? "后台任务中"
          : "Working"
        : hasWarn
          ? isZh
            ? `${notices.length} 项提醒`
            : `${notices.length} alerts`
          : isZh
            ? "运行正常"
            : "Healthy";
    head.appendChild(title);
    head.appendChild(pill);
    pop.appendChild(head);

    if (tasks.length > 0) {
      const sec = doc.createElement("div");
      sec.className = "pf-status-popover-section";
      for (const task of tasks) {
        const row = doc.createElement("div");
        row.className = "pf-status-popover-row";
        const prog =
          typeof task.total === "number" && task.total > 0
            ? ` (${task.current ?? 0}/${task.total})`
            : "";
        const elapsed =
          typeof task.startedAt === "number" && task.startedAt > 0
            ? ` · ${formatElapsedDuration(task.startedAt)}`
            : "";
        row.textContent = `${task.phase || task.label}${prog}${elapsed}`;
        sec.appendChild(row);
      }
      pop.appendChild(sec);
    } else if (this._lastAutoSyncError) {
      const sec = doc.createElement("div");
      sec.className = "pf-status-popover-section";
      const row = doc.createElement("div");
      row.className = "pf-status-popover-row";
      row.textContent = this._lastAutoSyncError.message;
      sec.appendChild(row);
      pop.appendChild(sec);
    } else {
      const count = this._baseSnapshotCache?.rows
        ? Object.keys(this._baseSnapshotCache.rows).length
        : null;
      const sec = doc.createElement("div");
      sec.className = "pf-status-popover-section";
      const row = doc.createElement("div");
      row.className = "pf-status-popover-row";
      row.textContent =
        count !== null
          ? isZh
            ? `已就绪 · 本地管理 ${count} 篇文献`
            : `Ready · ${count} papers synced`
          : isZh
            ? "Rust 守护服务运行正常"
            : "Local service ready";
      sec.appendChild(row);
      pop.appendChild(sec);
    }

    if (notices.length > 0) {
      const nSec = doc.createElement("div");
      nSec.className = "pf-status-popover-section";
      for (const n of notices.slice(0, 3)) {
        const row = doc.createElement("div");
        row.className = "pf-status-popover-row";
        row.textContent = n.message;
        nSec.appendChild(row);
      }
      const clr = doc.createElement("button");
      clr.type = "button";
      clr.className = "pf-btn pf-btn-ghost";
      clr.setAttribute("data-pf-testid", "pf-status-clear-notices");
      clr.textContent = isZh ? "清空提醒" : "Clear alerts";
      clr.addEventListener("click", () => {
        this._recentDaemonNotices = [];
        this._lastAutoSyncError = null;
        this._updateStatusBar();
        this._closeStatusPopover();
      });
      nSec.appendChild(clr);
      pop.appendChild(nSec);
    }

    const actions = doc.createElement("div");
    actions.className = "pf-status-popover-actions";
    const mkBtn = (label: string, testId: string, onClick: () => void) => {
      const b = doc.createElement("button");
      b.type = "button";
      b.className = "pf-btn pf-btn-secondary";
      b.setAttribute("data-pf-testid", testId);
      b.textContent = label;
      b.addEventListener("click", () => {
        this._closeStatusPopover();
        onClick();
      });
      actions.appendChild(b);
    };
    mkBtn(isZh ? "立即同步" : "Sync now", "pf-status-sync", () => {
      this.triggerManualSync();
    });
    mkBtn(isZh ? "伴读面板" : "Companion", "pf-status-companion", () => {
      void PaperForgeStatusView.open(this as any);
    });
    mkBtn(isZh ? "OCR 工作台" : "OCR Workspace", "pf-status-ocr", () => {
      void OcrWorkspaceView.open(this as any);
    });
    mkBtn(isZh ? "插件设置" : "Settings", "pf-status-settings", () => {
      this.openSettingsControlCenter();
    });
    pop.appendChild(actions);

    doc.body.appendChild(pop);
    this._statusPopoverEl = pop;

    const onDocDown = (ev: MouseEvent) => {
      const target = ev.target as Node | null;
      if (!target) return;
      if (pop.contains(target) || anchor?.contains(target)) return;
      this._closeStatusPopover();
    };
    const onDocKey = (ev: KeyboardEvent) => {
      if (ev.key === "Escape") this._closeStatusPopover();
    };
    doc.addEventListener("mousedown", onDocDown);
    doc.addEventListener("keydown", onDocKey);
    this._statusPopoverCleanup = () => {
      doc.removeEventListener("mousedown", onDocDown);
      doc.removeEventListener("keydown", onDocKey);
    };
  }

  private _updateStatusBar(): void {
    const el = this._statusBarEl;
    if (!el) return;
    const doc = el.ownerDocument;
    if (!doc) return;
    const tasks = this.getActiveBackgroundTasks();
    const alerts = this._recentDaemonNotices.filter(
      (n) => n.level === "error" || n.level === "warning"
    );

    el.style.display = "inline-flex";
    el.textContent = "";

    const dot = doc.createElement("span");
    dot.className = `pf-sb-dot${
      tasks.length > 0 ? " is-busy" : alerts.length > 0 ? " is-warn" : ""
    }`;
    const label = doc.createElement("span");
    label.className = "pf-sb-label";

    if (tasks.length > 0) {
      if (!this._statusBarHeartbeat) {
        this._statusBarHeartbeat = setInterval(() => {
          if (this._unloaded || this.getActiveBackgroundTasks().length === 0) {
            if (this._statusBarHeartbeat) {
              clearInterval(this._statusBarHeartbeat);
              this._statusBarHeartbeat = null;
            }
          }
          this._updateStatusBar();
        }, 1000);
      }
      const primary = tasks[0];
      const prog =
        typeof primary.total === "number" && primary.total > 0
          ? ` (${primary.current ?? 0}/${primary.total})`
          : "";
      const elapsed =
        typeof primary.startedAt === "number" && primary.startedAt > 0
          ? ` · ${formatElapsedDuration(primary.startedAt)}`
          : "";
      label.textContent = `PaperForge · ${primary.phase || primary.label}${prog}${elapsed}`;
    } else {
      if (this._statusBarHeartbeat) {
        clearInterval(this._statusBarHeartbeat);
        this._statusBarHeartbeat = null;
      }
      if (alerts.length > 0) {
        label.textContent = `PaperForge · ${alerts.length}`;
      } else {
        const cnt = this._baseSnapshotCache?.rows
          ? Object.keys(this._baseSnapshotCache.rows).length
          : null;
        label.textContent = cnt !== null ? `PaperForge · ${cnt}` : "PaperForge";
      }
    }

    el.appendChild(dot);
    el.appendChild(label);
  }

  private _setupEcosystemHooks(): void {
    if (
      typeof (this as { addStatusBarItem?: unknown }).addStatusBarItem ===
      "function"
    ) {
      this._statusBarEl = this.addStatusBarItem();
      this._statusBarEl.addClass?.("pf-status-bar-item");
      this._statusBarEl.addEventListener("click", () => {
        this._toggleStatusPopover();
      });
      this._updateStatusBar();
    }

    if (
      typeof (this as { registerObsidianProtocolHandler?: unknown })
        .registerObsidianProtocolHandler === "function"
    ) {
      this.registerObsidianProtocolHandler("paperforge", (params) => {
        const act = String(params?.action || "").trim();
        const key = String(params?.key || "").trim();
        const page = params?.page ? Number(params.page) : undefined;
        const annId = params?.ann ? String(params.ann) : undefined;
        if (act === "open-pdf" && key) {
          void this.openPaperPdf(key, {
            page: Number.isFinite(page) ? page : undefined,
            annId,
          });
        } else if (act === "open-split" && key) {
          void this.openPaperSplitReading(key);
        } else if (act === "open-hub") {
          void this.openLiteratureBase();
        }
      });
    }

    if (
      typeof (this as { registerEvent?: unknown }).registerEvent === "function"
    ) {
      const addPaperItems = (menu: unknown, file: unknown) => {
        if (!(file instanceof TFile) || file.extension !== "md") return;
        const row = this._resolvePaperByPath(file.path);
        if (!row) return;
        const m = menu as {
          addSeparator?: () => void;
          addItem?: (cb: (item: any) => void) => void;
        };
        m.addSeparator?.();
        if (row.has_pdf) {
          m.addItem?.((item) => {
            item
              .setTitle(`PaperForge: ${t("ctx_open_pdf")}`)
              .setIcon("book-open")
              .onClick(() => void this.openPaperPdf(row.zotero_key));
          });
          m.addItem?.((item) => {
            item
              .setTitle(`PaperForge: ${t("ctx_split_reading")}`)
              .setIcon("columns-2")
              .onClick(
                () =>
                  void this.openPaperSplitReading(
                    row.zotero_key,
                    row.main_note_path
                  )
              );
          });
        }
        m.addItem?.((item) => {
          item
            .setTitle(`PaperForge: ${t("base_run_selected_ocr")}`)
            .setIcon("play")
            .onClick(
              () =>
                void this.requestOcrRun({
                  kind: "papers",
                  keys: [row.zotero_key],
                })
            );
        });
      };

      const wsAny = this.app.workspace as unknown as {
        on: (ev: string, cb: (...args: any[]) => void) => any;
      };
      if (typeof wsAny?.on === "function") {
        this.registerEvent(wsAny.on("file-menu", addPaperItems));
        this.registerEvent(
          wsAny.on("editor-menu", (menu, _editor, info) => {
            addPaperItems(menu, (info as { file?: unknown } | undefined)?.file);
          })
        );
        this.registerEvent(
          wsAny.on("window-open", (_wsWin, win: Window) => {
            if (win?.document) {
              this._popoutWindows.add(win);
              this._applyThemeClassesToDoc(win.document);
            }
          })
        );
        this.registerEvent(
          wsAny.on("window-close", (_wsWin, win: Window) => {
            if (win) this._popoutWindows.delete(win);
          })
        );
      }
    }
  }

  async refreshBaseSnapshot(
    changedKeys: string[] = []
  ): Promise<BaseTableSnapshotDto | null> {
    try {
      const snap = await this.getClient().getBaseTableSnapshot();
      this._baseSnapshotCache = snap;
      if (typeof snap?.seq === "number") {
        this._lastStateSeq = snap.seq;
      }
      this._emitStateChanged(changedKeys);
      return snap;
    } catch {
      return this._baseSnapshotCache;
    }
  }

  triggerManualSync(): void {
    const vaultPath = (
      this.app.vault.adapter as unknown as { basePath?: string }
    )?.basePath;
    if (vaultPath) {
      this._autoSync(vaultPath);
      this._updateStatusBar();
    }
  }

  openOcrDiagnostic(paperKey?: string): void {
    void (OcrWorkspaceView.open as any)(this, paperKey);
  }

  async openLiteratureBase(): Promise<void> {
    const vaultBase =
      (this.app.vault.adapter as unknown as { basePath?: string })?.basePath ??
      "";
    const cfgBase = vaultBase ? readPathConfig(vaultBase).base_dir : "";
    const baseDir = (cfgBase || this.settings.base_dir || "").replace(
      /[\\/]+$/,
      ""
    );
    const preferredPath = baseDir ? `${baseDir}/Literature Hub.base` : "";
    const targetFile =
      (preferredPath &&
        this.app.vault.getAbstractFileByPath?.(preferredPath)) ||
      this.app.vault
        .getFiles?.()
        ?.find((f) => f.name === "Literature Hub.base") ||
      null;
    if (targetFile) {
      if (
        "extension" in targetFile &&
        typeof this.app.workspace?.getLeaf === "function"
      ) {
        const leaf = this.app.workspace.getLeaf(false);
        if (typeof leaf?.openFile === "function") {
          await leaf.openFile(targetFile as TFile);
          return;
        }
      }
      await this.app.workspace.openLinkText(targetFile.path, "");
      return;
    }
    if (preferredPath && typeof this.app.vault.adapter?.exists === "function") {
      try {
        if (await this.app.vault.adapter.exists(preferredPath)) {
          await this.app.workspace.openLinkText(preferredPath, "");
          return;
        }
      } catch {
        // Fall through to dashboard
      }
    }
    PaperForgeStatusView.open(this as any);
  }

  private _startStateSeqWatcher(vaultBase: string): void {
    if (
      this._unloaded ||
      this._stateSeqWatcher ||
      !vaultBase ||
      !isConfigHydrated()
    )
      return;
    let indexesDir = "";
    try {
      indexesDir = resolveVaultPaths(vaultBase).indexesDir;
    } catch {
      return;
    }
    if (!indexesDir || !fs.existsSync(indexesDir)) return;
    const seqFile = path.join(indexesDir, ".state-seq.json");
    const scheduleRefresh = () => {
      if (this._stateSeqTimer) clearTimeout(this._stateSeqTimer);
      this._stateSeqTimer = setTimeout(() => {
        this._stateSeqTimer = null;
        try {
          if (!fs.existsSync(seqFile)) return;
          const raw = JSON.parse(fs.readFileSync(seqFile, "utf-8")) as {
            seq?: unknown;
            changed_keys?: unknown;
          };
          const nextSeq = typeof raw.seq === "number" ? raw.seq : -1;
          if (nextSeq > 0 && nextSeq === this._lastStateSeq) return;
          if (nextSeq > 0) this._lastStateSeq = nextSeq;
          const changedKeys = Array.isArray(raw.changed_keys)
            ? raw.changed_keys.map((k) => String(k))
            : [];
          this.getClient().invalidateCache();
          void this.refreshBaseSnapshot(changedKeys);
        } catch {
          // Ignore transient partial/locked read during atomic replace
        }
      }, 150);
    };
    try {
      this._stateSeqWatcher = fs.watch(indexesDir, (_event, filename) => {
        if (!filename || filename === ".state-seq.json") {
          scheduleRefresh();
        }
      });
    } catch {
      this._stateSeqWatcher = null;
    }
  }

  private _resolveActivePaperKey(): { key: string; notePath?: string } | null {
    const pdfView = this.app.workspace.getActiveViewOfType?.(
      PaperForgePdfView as any
    ) as PaperForgePdfView | null;
    if (pdfView) {
      const k = String(pdfView.getState?.()?.paperKey ?? "").trim();
      if (k) return { key: k };
    }
    const activeFile = this.app.workspace.getActiveFile?.();
    if (activeFile?.path) {
      const cached = this._resolvePaperByPath(activeFile.path);
      if (cached) {
        return { key: cached.zotero_key, notePath: activeFile.path };
      }
    }
    return null;
  }

  openSettingsControlCenter(): boolean {
    const tab = this._settingTab;
    const settingApp = this.app as unknown as {
      setting?: {
        open?: unknown;
        openTabById?: unknown;
      };
    };
    const setting = settingApp.setting;
    const openSettings =
      typeof setting?.open === "function"
        ? setting.open.bind(setting)
        : undefined;
    const openTab =
      typeof setting?.openTabById === "function"
        ? (setting.openTabById as (id: string) => void).bind(setting)
        : undefined;
    if (!tab || !openSettings || !openTab) {
      new Notice(t("main_settings_nav_unavailable"), 6000);
      return false;
    }
    // Obsidian 1.14 requirement: openTabById before setting.open()
    const found = openTab("paperforge");
    (tab as unknown as { activeTab?: string }).activeTab = "overview";
    openSettings();
    return found !== null && found !== undefined;
  }

  cycleUiThemeMode(): void {
    const order = ["obsidian", "asterlab", "zinc", "warm"] as const;
    const cur = this.settings?.ui_theme_mode;
    const idx = order.indexOf(
      cur === "asterlab" || cur === "zinc" || cur === "warm" ? cur : "obsidian"
    );
    const next = order[(idx + 1) % order.length];
    this.settings.ui_theme_mode = next;
    this.applyUiThemeMode();
    void this.saveSettings();
  }

  cycleUiDensity(): void {
    const order = ["compact", "default", "comfortable"] as const;
    const cur = this.settings?.ui_density;
    const idx = order.indexOf(
      cur === "compact" || cur === "comfortable" ? cur : "default"
    );
    const next = order[(idx + 1) % order.length];
    this.settings.ui_density = next;
    this.applyUiThemeMode();
    void this.saveSettings();
  }

  toggleLiquidGlass(): void {
    this.settings.ui_liquid_glass = this.settings.ui_liquid_glass === false;
    this.applyUiThemeMode();
    void this.saveSettings();
  }

  toggleReduceMotion(): void {
    this.settings.reduce_motion = !this.settings.reduce_motion;
    this.applyUiThemeMode();
    void this.saveSettings();
  }

  async triggerBuildEmbeddings(skipConfirm = false): Promise<void> {
    const client = this.getClient();
    if (client.isOperationActive?.()) {
      new Notice(
        t("embed_already_running") || "Vector build is already in progress."
      );
      return;
    }

    const executeBuild = async (): Promise<void> => {
      try {
        new Notice(
          t("embed_activity_building") ||
            t("activity_embed") ||
            "Building vector retrieval index..."
        );
        let sawCancelled = false;
        const result = await client.runAction(
          {
            action_id: "embed.build",
            scope: { kind: "all" },
            confirm: "embed.build",
          },
          {
            onEvent: (event) => {
              if (event.event === "cancelled") sawCancelled = true;
              if (event.event === "progress") {
                this._embedProgress = {
                  current: Number(event.current ?? this._embedProgress.current),
                  total: Number(event.total ?? this._embedProgress.total),
                  key: String(event.item_id ?? this._embedProgress.key),
                };
              }
            },
          }
        );
        if (result.ok) {
          new Notice(
            t("embed_build_complete") ||
              t("feat_build_complete") ||
              "Vector index build complete."
          );
        } else if (result.cancelled || sawCancelled) {
          new Notice(
            t("embed_build_stopped") || "Build stopped. Run again to resume.",
            8000
          );
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
          const formatted = formatHumanError(reason) || reason;
          new Notice(
            (
              t("sr_build_failed_notice") ||
              "Vector index build failed: {detail}"
            ).replace("{detail}", formatted),
            8000
          );
        }
      } catch (err) {
        const msg =
          formatHumanError(err) ||
          (err instanceof Error ? err.message : String(err));
        new Notice(
          (
            t("sr_build_failed_notice") || "Vector index build failed: {detail}"
          ).replace("{detail}", msg),
          8000
        );
      }
    };

    if (skipConfirm) {
      await executeBuild();
      return;
    }

    new PaperForgeConfirmModal(
      this.app,
      {
        title:
          t("embed_confirm_title") ||
          t("cmd_build_embeddings") ||
          "Build vector retrieval index",
        effectLabel:
          t("embed_confirm_body") ||
          "Generate or update vector embeddings for all OCR-completed papers in the library.",
        confirmLabel: t("feat_build_btn") || "Build",
        cancelLabel: t("maintenance_confirm_cancel") || "Cancel",
      },
      () => {
        void executeBuild();
      }
    ).open();
  }

  private _registerExtendedCommands(): void {
    this.addCommand({
      id: "paperforge-command-palette",
      name: t("cmd_command_palette") || "PaperForge: Unified Command Palette",
      callback: () => {
        new PaperForgeQuickSwitcherModal(this.app, this, "command").open();
      },
    });
    this.addCommand({
      id: "paperforge-open-current-pdf",
      name: t("cmd_open_current_pdf") || "Open current paper PDF",
      checkCallback: (checking: boolean) => {
        const ctx = this._resolveActivePaperKey();
        if (!ctx) return false;
        if (!checking) void this.openPaperPdf(ctx.key);
        return true;
      },
    });
    this.addCommand({
      id: "paperforge-ocr-current-paper",
      name: t("cmd_ocr_current_paper") || "Run OCR on current paper",
      checkCallback: (checking: boolean) => {
        const ctx = this._resolveActivePaperKey();
        if (!ctx) return false;
        if (!checking) {
          void this.requestOcrRun({ kind: "papers", keys: [ctx.key] });
        }
        return true;
      },
    });
    this.addCommand({
      id: "paperforge-build-embeddings",
      name: t("cmd_build_embeddings") || "Build vector retrieval index",
      callback: () => {
        void this.triggerBuildEmbeddings();
      },
    });
    this.addCommand({
      id: "paperforge-open-settings",
      name: t("cmd_open_settings") || "Open PaperForge Control Center",
      callback: () => {
        this.openSettingsControlCenter();
      },
    });
    this.addCommand({
      id: "paperforge-cycle-theme",
      name:
        t("cmd_cycle_theme") ||
        "Cycle theme palette (Obsidian / Minimal / Slate / Warm)",
      callback: () => {
        this.cycleUiThemeMode();
      },
    });
    this.addCommand({
      id: "paperforge-cycle-density",
      name:
        t("cmd_cycle_density") ||
        "Cycle UI spacing density (Compact / Default / Comfortable)",
      callback: () => {
        this.cycleUiDensity();
      },
    });
    this.addCommand({
      id: "paperforge-toggle-liquid-glass",
      name: t("cmd_toggle_liquid_glass") || "Toggle Liquid Glass translucency",
      callback: () => {
        this.toggleLiquidGlass();
      },
    });
    this.addCommand({
      id: "paperforge-toggle-reduce-motion",
      name: t("cmd_toggle_reduce_motion") || "Toggle Reduce Motion",
      callback: () => {
        this.toggleReduceMotion();
      },
    });
    this.addCommand({
      id: "paperforge-check-orphans",
      name: t("cmd_check_orphans") || "Check orphan literature workspaces",
      callback: () => {
        const vp =
          (
            this.app.vault.adapter as unknown as {
              basePath?: string;
            }
          ).basePath ?? "";
        checkOrphanState(this.app, this as any, vp);
      },
    });

    const specs = [
      {
        id: "paperforge-status-panel",
        title: t("guide_open") || "Open PaperForge Companion",
        category: t("cmd_cat_navigation") || "Navigation",
        icon: "book-open" as const,
        run: () => void PaperForgeStatusView.open(this as any),
      },
      {
        id: "paperforge-open-literature-base",
        title: t("base_open_hub") || "Open Literature Hub Base",
        category: t("cmd_cat_library") || "Library",
        icon: "layers" as const,
        run: () => void this.openLiteratureBase(),
      },
      {
        id: "paperforge-ocr-workspace",
        title: t("cmd_ocr_workspace") || "Open OCR Workspace",
        category: "OCR",
        icon: "file-text" as const,
        run: () => void OcrWorkspaceView.open(this as any),
      },
      {
        id: "open-ui-gallery",
        title: t("cmd_open_ui_gallery") || "Open UI Gallery & Design System",
        category: t("cmd_cat_appearance") || "Appearance",
        icon: "palette" as const,
        run: () => void this.openUiGallery(),
      },
      {
        id: "focus-companion-search",
        title: t("cmd_focus_companion") || "Focus Companion search",
        category: t("cmd_cat_search") || "Search",
        icon: "search" as const,
        run: () => {
          void PaperForgeStatusView.open(this as any).then((v) =>
            v?._searchInput?.focus()
          );
        },
      },
      {
        id: "open-paper-split-reading",
        title: t("cmd_split_reading") || "Open current paper in split reading",
        category: t("cmd_cat_reading") || "Reading",
        icon: "columns-2" as const,
        run: () => {
          const ctx = this._resolveActivePaperKey();
          if (ctx) void this.openPaperSplitReading(ctx.key, ctx.notePath);
        },
      },
      {
        id: "paperforge-open-current-pdf",
        title: t("cmd_open_current_pdf") || "Open current paper PDF",
        category: t("cmd_cat_reading") || "Reading",
        icon: "book-open" as const,
        run: () => {
          const ctx = this._resolveActivePaperKey();
          if (ctx) void this.openPaperPdf(ctx.key);
        },
      },
      {
        id: "paperforge-ocr-current-paper",
        title: t("cmd_ocr_current_paper") || "Run OCR on current paper",
        category: "OCR",
        icon: "play" as const,
        run: () => {
          const ctx = this._resolveActivePaperKey();
          if (ctx) {
            void this.requestOcrRun({ kind: "papers", keys: [ctx.key] });
          }
        },
      },
      {
        id: "paperforge-sync",
        title: t("cmd_sync_library") || "Sync Zotero Library",
        category: t("cmd_cat_library") || "Library",
        icon: "refresh-cw" as const,
        run: () => this.triggerManualSync(),
      },
      {
        id: "paperforge-ocr",
        title: t("cmd_run_ocr_batch") || "Run OCR Batch",
        category: "OCR",
        icon: "sparkles" as const,
        run: () => void this.requestOcrRun(),
      },
      {
        id: "paperforge-build-embeddings",
        title: t("cmd_build_embeddings") || "Build vector retrieval index",
        category: t("cmd_cat_retrieval") || "Smart Retrieval",
        icon: "database" as const,
        run: () => void this.triggerBuildEmbeddings(),
      },
      {
        id: "paperforge-open-settings",
        title: t("cmd_open_settings") || "Open PaperForge Control Center",
        category: t("cmd_cat_system") || "System",
        icon: "settings" as const,
        run: () => {
          this.openSettingsControlCenter();
        },
      },
      {
        id: "paperforge-cycle-theme",
        title: t("cmd_cycle_theme") || "Cycle theme preset",
        category: t("cmd_cat_appearance") || "Appearance",
        icon: "palette" as const,
        run: () => this.cycleUiThemeMode(),
      },
      {
        id: "paperforge-cycle-density",
        title: t("cmd_cycle_density") || "Cycle UI spacing density",
        category: t("cmd_cat_appearance") || "Appearance",
        icon: "sliders" as const,
        run: () => this.cycleUiDensity(),
      },
      {
        id: "paperforge-toggle-liquid-glass",
        title: t("cmd_toggle_liquid_glass") || "Toggle Liquid Glass",
        category: t("cmd_cat_appearance") || "Appearance",
        icon: "sparkles" as const,
        run: () => this.toggleLiquidGlass(),
      },
      {
        id: "paperforge-toggle-reduce-motion",
        title: t("cmd_toggle_reduce_motion") || "Toggle Reduce Motion",
        category: t("cmd_cat_appearance") || "Appearance",
        icon: "eye" as const,
        run: () => this.toggleReduceMotion(),
      },
      {
        id: "paperforge-check-orphans",
        title: t("cmd_check_orphans") || "Check orphan literature workspaces",
        category: t("cmd_cat_maintenance") || "Maintenance",
        icon: "trash-2" as const,
        run: () => {
          const vp =
            (this.app.vault.adapter as unknown as { basePath?: string })
              .basePath ?? "";
          checkOrphanState(this.app, this as any, vp);
        },
      },
      {
        id: "paperforge-vault-upgrade",
        title: t("main_cmd_check_upgrade") || "Check Vault upgrade plan",
        category: t("cmd_cat_maintenance") || "Maintenance",
        icon: "wrench" as const,
        run: () => void this.openUpgradeModal(),
      },
    ];

    for (const s of specs) {
      this.commandRegistry.register(s);
    }
  }

  async openUiGallery(): Promise<void> {
    await PaperForgeGalleryView.open(this as any);
  }

  async updateNoteProperty(
    file: TFile,
    propName: string,
    value: string
  ): Promise<void> {
    if (!file || !propName) return;
    await this.app.fileManager.processFrontMatter(file, (fm) => {
      fm[propName] = value;
    });
  }

  private _applyThemeClassesToDoc(doc: Document | null | undefined): void {
    if (!doc?.body) return;
    const raw = this.settings?.ui_theme_mode;
    const mode =
      raw === "asterlab"
        ? "asterlab"
        : raw === "zinc"
          ? "zinc"
          : raw === "warm"
            ? "warm"
            : "obsidian";
    doc.body.classList.toggle("pf-theme-obsidian", mode === "obsidian");
    doc.body.classList.toggle("pf-theme-asterlab", mode === "asterlab");
    doc.body.classList.toggle("pf-theme-zinc", mode === "zinc");
    doc.body.classList.toggle("pf-theme-warm", mode === "warm");
    const rawDensity = this.settings?.ui_density;
    const density =
      rawDensity === "compact"
        ? "compact"
        : rawDensity === "comfortable"
          ? "comfortable"
          : "default";
    doc.body.classList.toggle("pf-density-compact", density === "compact");
    doc.body.classList.toggle("pf-density-default", density === "default");
    doc.body.classList.toggle(
      "pf-density-comfortable",
      density === "comfortable"
    );
    doc.body.classList.toggle(
      "pf-no-glass",
      this.settings?.ui_liquid_glass !== true
    );
    doc.body.classList.toggle(
      "pf-reduce-motion",
      this.settings?.reduce_motion === true
    );
  }

  applyUiThemeMode(): void {
    if (typeof document !== "undefined") {
      this._applyThemeClassesToDoc(document);
    }
    for (const win of Array.from(this._popoutWindows)) {
      if (win.closed) {
        this._popoutWindows.delete(win);
        continue;
      }
      this._applyThemeClassesToDoc(win.document);
    }
  }

  onunload() {
    this._unloaded = true;
    this._closeStatusPopover();
    if (this._statusBarHeartbeat) {
      clearInterval(this._statusBarHeartbeat);
      this._statusBarHeartbeat = null;
    }
    if (this._settingTabRefreshThrottleTimer) {
      clearTimeout(this._settingTabRefreshThrottleTimer);
      this._settingTabRefreshThrottleTimer = null;
    }
    if (this._startupDeferTimer) {
      clearTimeout(this._startupDeferTimer);
      this._startupDeferTimer = null;
    }
    try {
      this._settingTab?.hide?.();
    } catch {
      // ignore setting tab hide errors on unload
    }
    const clearClasses = (doc: Document | null | undefined) => {
      doc?.body?.classList?.remove(
        "pf-theme-obsidian",
        "pf-theme-asterlab",
        "pf-theme-zinc",
        "pf-theme-warm",
        "pf-density-compact",
        "pf-density-default",
        "pf-density-comfortable",
        "pf-no-glass",
        "pf-reduce-motion"
      );
    };
    if (typeof document !== "undefined") clearClasses(document);
    for (const win of this._popoutWindows) {
      clearClasses(win.document);
    }
    this._popoutWindows.clear();
    if (this._pollTimer) {
      clearInterval(this._pollTimer);
      this._pollTimer = null;
    }
    if (this._stateSeqTimer) {
      clearTimeout(this._stateSeqTimer);
      this._stateSeqTimer = null;
    }
    try {
      this._stateSeqWatcher?.close?.();
    } catch {
      // ignore watcher close errors
    }
    this._stateSeqWatcher = null;
    this._unsubscribeDaemon?.();
    this._unsubscribeDaemon = null;
    this._daemonJobs.clear();
    this._client?.cancelActiveOperation();
    this._client?.shutdownTransport?.();
    // Reap ordinary (non-streamed) execute children so they do not outlive
    // the plugin/Window (issue #266).
    try {
      NodeProcessTransport.reapAllExecuteChildren();
    } catch {
      // ignore
    }
  }

  async loadSettings() {
    const saved = ((await this.loadData()) ?? {}) as Record<string, unknown>;
    this.settings = Object.assign({}, DEFAULT_SETTINGS, saved);
    if (this.settings.features && DEFAULT_SETTINGS.features) {
      this.settings.features = Object.assign(
        {},
        DEFAULT_SETTINGS.features,
        this.settings.features || {}
      );
    }
    if (!this.settings.frozen_skills) {
      this.settings.frozen_skills = {};
    }

    // Existing installations predate the Setup Journey. The previous rollout
    // wrote the new default false into their data, so migrate only profiles
    // that genuinely finished library setup (`last_seen_version` + ready library)
    // and never started the journey — never fresh vaults with `vault_path` or
    // `setup_required` / `library.zotero_missing` capability caches.
    const savedCap = saved.capabilityState as
      | Record<string, { user_state?: string; capability_state?: string }>
      | undefined;
    const savedLibReady =
      savedCap?.library?.user_state === "ready" ||
      savedCap?.library?.capability_state === "ready";
    const establishedInstall =
      Boolean(saved.last_seen_version) && savedLibReady;
    if (
      saved._setup_complete === false &&
      establishedInstall &&
      saved._setup_journey_started !== true
    ) {
      this.settings._setup_complete = true;
      void this.saveSettings();
    }
  }

  /** Hydrate display mirrors asynchronously AFTER Obsidian layout is ready (never blocks onload). */
  private async _hydrateConfigMirrors(vaultPath: string): Promise<void> {
    if (!vaultPath) return;
    try {
      const list = await this.getClient().configList();
      applyPathConfigFromList(this.settings, list.fields);
      const pick = (key: string) =>
        list.fields.find((f) => f.key === key)?.value;
      const apiBase = String(pick("vector_db_api_base") ?? "");
      const apiModel = String(pick("vector_db_api_model") ?? "");
      const providerType = String(pick("vector_db_provider_type") ?? "");
      const ocrJobUrl = String(pick("paddleocr_job_url") ?? "");
      const ocrModel = String(pick("paddleocr_model") ?? "");
      const agentPlatform = String(pick("agent_platform") ?? "");
      if (apiBase) this.settings.vector_db_api_base = apiBase;
      if (apiModel) this.settings.vector_db_api_model = apiModel;
      if (providerType) this.settings.vector_db_provider_type = providerType;
      if (ocrJobUrl) this.settings.paddleocr_job_url = ocrJobUrl;
      if (ocrModel) this.settings.paddleocr_model = ocrModel;
      if (agentPlatform) this.settings.agent_platform = agentPlatform;
      const platformField = list.fields.find((f) => f.key === "agent_platform");
      this.agentPlatformChoices = platformField?.choices ?? [];
      this._refreshSettingTabIfOpen();
    } catch {
      // Display mirrors keep defaults until Python is reachable
    }
  }

  async saveSettings() {
    const dataToSave: Record<string, unknown> = {};
    for (const key of Object.keys(DEFAULT_SETTINGS)) {
      if (key in this.settings) {
        dataToSave[key] = this.settings[key];
      }
    }
    await this.saveData(dataToSave);
  }

  private _checkReleaseNotes() {
    const currentVersion = this.manifest.version;
    const seen = this.settings.last_seen_version;
    // A fresh profile has no previous version to compare against: release
    // notes for an upgrade they never ran are noise before first setup.
    if (!seen || seen === currentVersion) return;
    // Non-blocking: record pending release notes for an inline banner in
    // Settings / Help instead of interrupting startup with an unsolicited Modal.
    this._pendingReleaseNotesVersion = currentVersion;
  }

  openReleaseNotesModal(): void {
    const currentVersion =
      this._pendingReleaseNotesVersion || this.manifest.version;
    const releaseNotesData = require("./release-notes.json");
    const versions = releaseNotesData.versions || [];
    const currentEntry = versions.find(
      (v: any) => v.version === currentVersion
    );

    class ReleaseNotesModal extends Modal {
      private _entry: any;
      constructor(app: any, entry: any) {
        super(app);
        this._entry = entry;
      }
      onOpen() {
        const { contentEl } = this;
        contentEl.createEl("h2", {
          text: t("main_release_modal_title").replace(
            "{version}",
            currentVersion
          ),
        });
        if (this._entry) {
          contentEl.createEl("p", {
            text: this._entry.title,
            cls: "paperforge-modal-subtitle",
          });
          if (
            this._entry.breaking_or_migration &&
            this._entry.breaking_or_migration.length > 0
          ) {
            contentEl.createEl("h4", {
              text: t("main_release_recommended"),
            });
            for (const item of this._entry.breaking_or_migration) {
              contentEl.createEl("p", {
                text: `\u2022 ${item}`,
                cls: "paperforge-modal-item",
              });
            }
          }
          if (this._entry.new_features && this._entry.new_features.length > 0) {
            contentEl.createEl("h4", { text: t("main_release_new_features") });
            for (const item of this._entry.new_features) {
              contentEl.createEl("p", {
                text: `\u2022 ${item}`,
                cls: "paperforge-modal-item",
              });
            }
          }
          if (this._entry.fixes && this._entry.fixes.length > 0) {
            contentEl.createEl("h4", { text: t("main_release_fixes") });
            for (const item of this._entry.fixes) {
              contentEl.createEl("p", {
                text: `\u2022 ${item}`,
                cls: "paperforge-modal-item",
              });
            }
          }
          if (
            this._entry.recommended_actions &&
            this._entry.recommended_actions.length > 0
          ) {
            const section = contentEl.createEl("div", {
              cls: "paperforge-release-recommended",
            });
            section.createEl("h4", {
              text: t("main_release_recommended"),
              cls: "",
            });
            section.style.marginBottom = "8px";
            for (const item of this._entry.recommended_actions) {
              section.createEl("p", {
                text: `\u2022 ${item}`,
                cls: "paperforge-release-item-bold",
              });
            }
          }
        } else {
          contentEl.createEl("p", {
            text: t("main_release_fallback_body").replace(
              "{version}",
              currentVersion
            ),
          });
        }
        new Setting(contentEl).addButton((btn) =>
          btn
            .setButtonText(t("main_release_got_it"))
            .setCta()
            .onClick(() => {
              this.close();
            })
        );
      }
      onClose() {
        const { contentEl } = this;
        contentEl.empty();
      }
    }

    new ReleaseNotesModal(this.app, currentEntry).open();
    this.dismissPendingReleaseNotes();
  }
}

/**
 * Intercept clicks on external OS `pdf_path` wikilinks in Obsidian Properties
 * so Obsidian does not fail with "File name cannot contain any of the following characters".
 */
export function tryHandleExternalPdfLinkClick(
  evt: MouseEvent,
  ctx: {
    app: App;
    baseSnapshot: BaseTableSnapshotDto | null;
    openPaperPdf: (paperKey: string) => Promise<void> | void;
  }
): boolean {
  if (evt.button !== 0) return false;
  const target = evt.target as HTMLElement | null;
  if (!target || typeof target.closest !== "function") return false;

  const pdfPropLink = target.closest(
    '.metadata-property[data-property-key="pdf_path"] .internal-link, ' +
      '.metadata-property[data-property-key="pdf_path"] .metadata-link-inner, ' +
      '.metadata-property[data-property-key="pdf_path"] .metadata-link, ' +
      '.metadata-property[data-property-key="pdf_path"] .multi-select-pill-content'
  ) as HTMLElement | null;
  const internalLink = pdfPropLink
    ? null
    : (target.closest(
        ".internal-link, .cm-hmd-internal-link"
      ) as HTMLElement | null);
  const linkEl = pdfPropLink ?? internalLink;
  if (!linkEl) return false;

  const activeFile = ctx.app?.workspace?.getActiveFile?.();
  const activeFm = activeFile
    ? ctx.app?.metadataCache?.getFileCache?.(activeFile)?.frontmatter
    : undefined;
  let rawHref = (
    linkEl.getAttribute("data-href") ||
    linkEl.getAttribute("href") ||
    linkEl.textContent ||
    ""
  ).trim();
  if (
    pdfPropLink &&
    typeof activeFm?.pdf_path === "string" &&
    activeFm.pdf_path.trim()
  ) {
    rawHref = activeFm.pdf_path.trim();
  }
  const cleanPath = rawHref
    .replace(/^\[\[/, "")
    .replace(/\]\]$/, "")
    .replace(/^absolute:/i, "")
    .replace(/^file:\/\/\/?/i, (m) => (m === "file:///" ? "" : "/"))
    .trim();
  if (!cleanPath) return false;

  const isExternalOsPath =
    /^[A-Za-z]:[/\\]/.test(cleanPath) ||
    cleanPath.startsWith("/") ||
    /^file:\/\//i.test(rawHref);
  const isPdfPropertyOutsideVault =
    Boolean(pdfPropLink) &&
    cleanPath.toLowerCase().endsWith(".pdf") &&
    !ctx.app?.vault?.getAbstractFileByPath?.(cleanPath.replace(/\\/g, "/"));

  if (
    !isPdfPropertyOutsideVault &&
    !(isExternalOsPath && cleanPath.toLowerCase().endsWith(".pdf"))
  ) {
    return false;
  }

  evt.preventDefault();
  evt.stopPropagation();
  if (typeof evt.stopImmediatePropagation === "function") {
    evt.stopImmediatePropagation();
  }

  let zoteroKey = "";
  if (activeFile?.path) {
    const fm = activeFm;
    if (typeof fm?.zotero_key === "string" && fm.zotero_key.trim()) {
      zoteroKey = fm.zotero_key.trim();
    }
    if (!zoteroKey && ctx.baseSnapshot?.rows) {
      const normActive = activeFile.path.replace(/\\/g, "/");
      for (const row of Object.values(ctx.baseSnapshot.rows)) {
        if ((row.main_note_path || "").replace(/\\/g, "/") === normActive) {
          zoteroKey = row.zotero_key;
          break;
        }
      }
    }
    if (!zoteroKey && activeFile.basename) {
      const m = activeFile.basename.match(/^([A-Za-z0-9]{8})(?:\s+-|$)/);
      if (m) zoteroKey = m[1];
    }
  }

  if (zoteroKey) {
    void ctx.openPaperPdf(zoteroKey);
    return true;
  }

  if (fs.existsSync(cleanPath)) {
    try {
      const { shell } = require("electron") as {
        shell?: { openPath?: (p: string) => Promise<string> };
      };
      if (typeof shell?.openPath === "function") {
        void shell.openPath(cleanPath);
        return true;
      }
    } catch {
      // Non-Electron environment fallback
    }
  }
  new Notice(t("paper_note_missing") || "PDF link cannot be opened directly.");
  return true;
}
