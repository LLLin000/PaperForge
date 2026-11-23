import type { ActionRequest, ActionScope } from "./client/action-contract";
import * as fs from "fs";
import * as path from "path";
import { Plugin, Notice, Modal, Setting, App } from "obsidian";

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
  PF_ICON_ID,
  ACTIONS,
  DEFAULT_SETTINGS,
  PaperForgeSettings,
} from "./constants";
import { t, setLanguage } from "./i18n";
import { formatDaemonNotice, formatHumanError } from "./services/feedback";
import {
  readRuntimePointer,
  resolveRuntimeCommand,
  type PointerInfo,
} from "./services/managed-runtime";
import {
  ensureNativeDaemonDownloaded,
  readNativeDaemonMeta,
  resolveNativeDaemonBinary,
} from "./services/native-daemon";
import { normalizeSemverForCompare } from "./services/setup-decision-tree";
import { PaperForgeSettingTab } from "./settings";
import { orchestrateFromSync } from "./services/next-actions-bridge";
import { PaperForgeStatusView } from "./views/dashboard";
import { OcrWorkspaceView } from "./views/ocr-workspace";
import { PaperForgeBasesView } from "./views/paperforge-base-view";
import {
  PaperForgePdfView,
  type PdfAnnotatorOpenState,
} from "./views/pdf-annotator";
import {
  PaperForgeConfirmModal,
  PaperForgeSetupWizardModal,
} from "./views/modals";
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
  kind: "sync" | "ocr" | "embed" | "heal";
  label: string;
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
  private _startupDeferTimer: ReturnType<typeof setTimeout> | null = null;
  private _lastSyncedZoteroSig: string | null = null;

  private _client: PaperForgeClient | null = null;

  isDaemonUpdating(): boolean {
    return this._daemonUpdating;
  }

  isRuntimeUpdating(): boolean {
    for (const dj of this._daemonJobs.values()) {
      if (dj.kind === "runtime.install" || dj.kind === "runtime.update") {
        return true;
      }
    }
    return false;
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
        if (job.kind === "runtime.install" || job.kind === "runtime.update") {
          if (!isActive) {
            this._settingTab?._refreshAllReadModels({ background: true });
          }
          this._refreshSettingTabIfOpen();
        }
      }
      return;
    }
    if (ev.event === "notice.push" && ev.data) {
      const nid = String(ev.data.notice_id ?? "");
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
          code: String(ev.data.code ?? ""),
          level: String(ev.data.level ?? "info"),
          title: String(ev.data.title ?? ""),
          detail: String(ev.data.detail ?? ""),
        },
        { suppressRuntimeInstall }
      );
      if (formatted) {
        new Notice(formatted.message, formatted.durationMs);
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
                event.status !== "skipped"
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
            key: "show_annotations",
            type: "toggle",
            displayName: t("main_base_opt_annotations"),
            default: true,
          },
          {
            key: "compact_rows",
            type: "toggle",
            displayName: t("main_base_opt_compact"),
            default: false,
          },
        ],
      });
    }

    this.addRibbonIcon(PF_ICON_ID, "PaperForge Dashboard", () =>
      PaperForgeStatusView.open(this as any)
    );
    this.addRibbonIcon("library", "PaperForge Literature Hub", () => {
      void this.openLiteratureBase();
    });

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
      name: "Open OCR Workspace",
      callback: () => OcrWorkspaceView.open(this as any),
    });
    this.addCommand({
      id: "focus-companion-search",
      name: "Focus Companion search",
      callback: async () => {
        const view = await PaperForgeStatusView.open(this as any);
        view?._searchInput?.focus();
      },
    });
    this.addCommand({
      id: "open-paper-split-reading",
      name: "Open current paper in split PDF and Note view",
      callback: async () => {
        const activeLeaf = (
          this.app.workspace as unknown as {
            activeLeaf?: {
              view?: {
                getViewType?: () => string;
                getState?: () => Record<string, unknown>;
              };
            } | null;
          }
        ).activeLeaf;
        if (activeLeaf?.view?.getViewType?.() === VIEW_TYPE_PAPERFORGE_PDF) {
          const k = String(activeLeaf.view.getState?.()?.paperKey ?? "").trim();
          if (k) {
            await this.openPaperSplitReading(k);
            return;
          }
        }
        const activeFile = this.app.workspace.getActiveFile?.();
        if (activeFile?.path) {
          const ctx = await this.getClient()
            .resolvePaperContext(activeFile.path)
            .catch(() => null);
          if (ctx?.kind === "paper" && ctx.zotero_key) {
            await this.openPaperSplitReading(ctx.zotero_key, activeFile.path);
            return;
          }
        }
        new Notice(t("paper_note_missing") || "No active paper selected.");
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
      name: "Migrate PaperForge legacy configuration",
      callback: () => this._runLegacyConfigMigration(),
    });

    this.addCommand({
      id: "paperforge-vault-upgrade",
      name: t("main_cmd_check_upgrade"),
      callback: () => {
        void this.openUpgradeModal();
      },
    });

    this._checkReleaseNotes();

    const vaultBase = (
      this.app.vault.adapter as unknown as { basePath?: string }
    ).basePath;

    const pluginVersion = this.manifest?.version ?? "";
    const prevNativeBin = resolveNativeDaemonBinary({ vaultPath: vaultBase });
    const prevMeta = readNativeDaemonMeta();
    const needsDaemonSwap = Boolean(
      pluginVersion &&
      (!prevNativeBin ||
        !prevMeta?.tag ||
        normalizeSemverForCompare(prevMeta.tag) !==
          normalizeSemverForCompare(pluginVersion))
    );

    const runStartupHydration = () => {
      if (!vaultBase) return;
      this._startStateSeqWatcher(vaultBase);
      // Fast Rust-native upgrade plan check (< 3ms, zero Python spawned)
      void this.refreshUpgradePlan()
        .then((plan) => {
          this._refreshSettingTabIfOpen();
          if (
            this.settings._setup_complete === false &&
            this.settings._setup_journey_started !== true &&
            !readRuntimePointer() &&
            !plan?.provenance?.needs_upgrade
          ) {
            new Notice(t("main_first_open_ready"), 8000);
          }
        })
        .catch(() => undefined);
      // Non-blocking config mirror hydration (only when Python runtime exists)
      if (readRuntimePointer()) {
        void this._hydrateConfigMirrors(vaultBase).then(() => {
          this._startConvergenceTimer();
        });
      } else {
        this._startConvergenceTimer();
      }
    };

    const scheduleDeferredStartup = () => {
      this._startupDeferTimer = setTimeout(() => {
        this._startupDeferTimer = null;
        if (needsDaemonSwap) {
          this._daemonUpdating = true;
        } else {
          runStartupHydration();
        }

        void ensureNativeDaemonDownloaded(pluginVersion, {
          checkVersionUpdate: true,
          onBeforeReplace: () => this._client?.shutdownTransportAsync(),
          onQuarantineSuspected: (binDir) => {
            this._quarantinedBinDir = binDir;
            this._emitStateChanged();
            this._refreshSettingTabIfOpen();
            new Notice(t("main_defender_notice_short"), 8000);
          },
        })
          .then((downloadedBin) => {
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
                .then(() => this._refreshSettingTabIfOpen())
                .catch(() => undefined);
              void this.refreshBaseSnapshot().catch(() => undefined);
              this._settingTab?._refreshAllReadModels({ background: true });
              this._refreshSettingTabIfOpen();
            }
            if (!downloadedBin || !vaultBase) return;
            const ptr = readRuntimePointer();
            if (ptr && pluginVersion) {
              if (
                normalizeSemverForCompare(ptr.paperforgeVersion) !==
                normalizeSemverForCompare(pluginVersion)
              ) {
                void this.getClient()
                  .daemonSubmitRuntimeUpdate(pluginVersion)
                  .catch(() => undefined);
              }
            }
          })
          .catch(() => {
            this._daemonUpdating = false;
            if (needsDaemonSwap) {
              runStartupHydration();
              this._refreshSettingTabIfOpen();
            }
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
    const vaultPath = (this.app.vault.adapter as any).basePath as string;
    const cadenceMs =
      Math.max(30, this.settings.autoSyncIntervalSeconds ?? 120) * 1000;

    if (this.settings.autoSyncEnabled === false) {
      return;
    }
    this._maybeAutoSync(vaultPath);
    this._pollTimer = setInterval(() => {
      if (!isConfigHydrated()) return;
      this._maybeAutoSync(vaultPath);
    }, cadenceMs);
  }

  // T8: mtime scanner deleted — the convergence tick fires sync directly.

  private _autoSync(vaultPath: string, expectedZoteroSig?: string) {
    if (this._autoSyncRunning) return;
    if (this._upgradePlanCache?.provenance?.needs_upgrade === true) {
      return;
    }
    this._autoSyncRunning = true;
    this._emitStateChanged();

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
          const errObj = (result as { error?: { message?: string } })?.error;
          this._lastAutoSyncError = {
            message: formatHumanError(errObj?.message || "sync_failed"),
            at: Date.now(),
          };
        }
      } catch (err: unknown) {
        ok = false;
        const rawMsg = err instanceof Error ? err.message : String(err ?? "");
        // Never surface transient internal daemon hot-swap restarts as sync errors
        if (
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
        this._memoryStatusText = null;
        this._emitStateChanged();
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
    if (!targetPath) return;
    const splitLeaf = this.app.workspace.getLeaf("split", "vertical");
    const file = this.app.vault.getAbstractFileByPath?.(targetPath);
    if (file && "extension" in file && splitLeaf) {
      await splitLeaf.openFile(file as any);
      await this.app.workspace.revealLeaf(splitLeaf);
      return;
    }
    await this.app.workspace.openLinkText?.(targetPath, "", "split");
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
    const map = this.settings._baseFilters ?? {};
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
    if (!this.settings._baseFilters) {
      this.settings._baseFilters = {};
    }
    this.settings._baseFilters[viewKey || "default"] = { ...next };
    void this.saveSettings();
  }

  /** Zero-idle shared background activity projection for Companion / Base UI strips. */
  getActiveBackgroundTasks(): ActiveBackgroundTask[] {
    const tasks: ActiveBackgroundTask[] = [];
    if (this._autoSyncRunning) {
      tasks.push({
        kind: "sync",
        label: t("activity_syncing") || "Syncing library",
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
    for (const dj of this._daemonJobs.values()) {
      const mappedKind: ActiveBackgroundTask["kind"] =
        dj.kind === "upgrade.heal"
          ? "heal"
          : dj.kind === "ocr"
            ? "ocr"
            : dj.kind === "embed"
              ? "embed"
              : "sync";
      if (mappedKind !== "heal" && tasks.some((x) => x.kind === mappedKind)) {
        continue;
      }
      tasks.push({
        kind: mappedKind,
        label:
          mappedKind === "heal"
            ? t("main_activity_heal")
            : mappedKind === "ocr"
              ? t("activity_ocr") || "Parsing fulltext"
              : mappedKind === "embed"
                ? t("activity_embed") || "Building embeddings"
                : t("activity_syncing") || "Syncing library",
        current: dj.total > 0 ? dj.current : undefined,
        total: dj.total > 0 ? dj.total : undefined,
        key: dj.item_id || undefined,
        jobId: dj.job_id,
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
      new Notice(t("main_syncing_library"));
      this._autoSync(vaultPath);
    }
  }

  openOcrDiagnostic(_paperKey?: string): void {
    void OcrWorkspaceView.open(this as any);
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
    if (this._stateSeqWatcher || !vaultBase || !isConfigHydrated()) return;
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

  applyUiThemeMode(): void {
    if (typeof document === "undefined" || !document.body) return;
    const raw = this.settings?.ui_theme_mode;
    const mode =
      raw === "asterlab" ? "asterlab" : raw === "warm" ? "warm" : "obsidian";
    document.body.classList.toggle("pf-theme-obsidian", mode === "obsidian");
    document.body.classList.toggle("pf-theme-asterlab", mode === "asterlab");
    document.body.classList.toggle("pf-theme-warm", mode === "warm");
    document.body.classList.toggle(
      "pf-no-glass",
      this.settings?.ui_liquid_glass !== true
    );
    document.body.classList.toggle(
      "pf-reduce-motion",
      this.settings?.reduce_motion === true
    );
  }

  onunload() {
    if (this._startupDeferTimer) {
      clearTimeout(this._startupDeferTimer);
      this._startupDeferTimer = null;
    }
    if (typeof document !== "undefined" && document.body) {
      document.body.classList.remove(
        "pf-theme-obsidian",
        "pf-theme-asterlab",
        "pf-theme-warm",
        "pf-no-glass",
        "pf-reduce-motion"
      );
    }
    if (this._pollTimer) clearInterval(this._pollTimer);
    if (this._stateSeqTimer) clearTimeout(this._stateSeqTimer);
    try {
      this._stateSeqWatcher?.close?.();
    } catch {
      // ignore watcher close errors
    }
    this._stateSeqWatcher = null;
    this._unsubscribeDaemon?.();
    this._unsubscribeDaemon = null;
    this._daemonJobs.clear();
    // In-flight embed/OCR operations are owned by the shared client's
    // OperationLock — cancelled below via cancelActiveOperation.
    this.app.workspace.detachLeavesOfType(VIEW_TYPE_PAPERFORGE);
    this.app.workspace.detachLeavesOfType(VIEW_TYPE_PAPERFORGE_PDF);
    this._client?.cancelActiveOperation();
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
    // that already carried durable pre-redesign state and never started the journey.
    const establishedInstall =
      !!saved.capabilityState ||
      !!saved.last_seen_version ||
      !!saved.vault_path;
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
