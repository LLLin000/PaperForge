import {
  ItemView,
  WorkspaceLeaf,
  Notice,
  MarkdownRenderer,
  App,
  TFile,
} from "obsidian";
import * as fs from "fs";
import * as path from "path";
import { execFile, spawn, execFileSync } from "child_process";
import {
  VIEW_TYPE_PAPERFORGE,
  ACTIONS,
  ActionDef,
  PaperForgeSettings,
  PF_ICON_ID,
  overlayEntryWorkflowState,
  patchEntryWorkflowState,
} from "../constants";
import { t } from "../i18n";
import {
  resolveVaultPaths,
  getMemoryRuntime,
  getVectorRuntime,
  getRuntimeHealth,
  isMemoryReady,
  isVectorReady,
  isHealthOk,
  getMemoryStatusText,
  getVectorStatusText,
  getCachedPython,
  buildSnapshot,
  shouldRenderVectorReady,
} from "../services/memory-state";
import {
  resolvePythonExecutable,
  buildCommandArgs,
  runSubprocess,
  classifyError,
  checkRuntimeVersion,
  paperforgeEnrichedEnv,
} from "../services/python-bridge";
import { getDisclosureState, toggleDisclosureState } from "../utils/disclosure";
import { extractZoteroKeyFromPath } from "../utils/zotero-path";
import { checkOrphanState } from "./modals";
import {
  type PaperVersionInfo,
  listPapersWithBackups,
  scanVersions,
  restoreVersion,
  compareVersions,
} from "../services/version-history";

// ── Interface for plugin ref used by static open ──

interface IPluginRef {
  app: App;
  manifest: { version: string };
  settings?: PaperForgeSettings;
  [key: string]: unknown;
}

export class PaperForgeStatusView extends ItemView {
  _currentMode: "global" | "paper" | "collection" | "versions" | null = null;
  _currentDomain: string | null = null;
  _currentPaperKey: string | null = null;
  _currentPaperEntry: Record<string, any> | null = null;
  _currentFilePath: string | null = null;
  _cachedItems: any[] | null = null;
  _modeSubscribers: { event: string; ref: any }[] = [];
  _leafChangeTimer: ReturnType<typeof setTimeout> | null = null;
  _ocrPrivacyShown = false;
  _cachedStats: any = null;
  _techDetailsExpanded = false;
  _paperforgeVersion = "";
  _dashboardPermissions: Record<string, boolean> = {};
  _headerTitle: HTMLElement | null = null;
  _versionBadge: HTMLElement | null = null;
  _messageEl: HTMLElement | null = null;
  _contentEl!: HTMLElement;
  _modeContextEl!: HTMLElement;
  _metricsEl: HTMLElement | null = null;
  _ocrSection: HTMLElement | null = null;
  _ocrEmpty: HTMLElement | null = null;
  _ocrBadge: HTMLElement | null = null;
  _ocrTrack: HTMLElement | null = null;
  _ocrCounts: HTMLElement | null = null;
  _driftBannerEl: HTMLElement | null = null;
  // ── Search state ──
  // ── Version state ──
  _versionPapers: PaperVersionInfo[] | null = null;
  _versionFilter: string = "";
  // ── Search state ──
  _searchContainer: HTMLElement | null = null;
  _searchInput: HTMLInputElement | null = null;
  _searchResultsEl: HTMLElement | null = null;
  _searchTimer: ReturnType<typeof setTimeout> | undefined = undefined;

  constructor(leaf: WorkspaceLeaf) {
    super(leaf);
    this._currentMode = null;
    this._currentDomain = null;
    this._currentPaperKey = null;
    this._currentPaperEntry = null;
    this._currentFilePath = null;
    this._cachedItems = null;
    this._modeSubscribers = [];
    this._leafChangeTimer = null;
    this._ocrPrivacyShown = false;
  }

  getViewType() {
    return VIEW_TYPE_PAPERFORGE;
  }
  getDisplayText() {
    return "PaperForge";
  }
  getIcon() {
    return PF_ICON_ID;
  }

  async onOpen() {
    this._buildPanel();
    this._modeSubscribers = [];
    this._leafChangeTimer = null;
    this._setupEventSubscriptions();
    this._fetchVersion();
    this._detectAndSwitch();
  }

  async onClose() {
    if (this._modeSubscribers && this._modeSubscribers.length > 0) {
      for (const sub of this._modeSubscribers) {
        if (sub.event === "active-leaf-change") {
          this.app.workspace.off("active-leaf-change", sub.ref);
        } else if (sub.event === "modify") {
          this.app.vault.off("modify", sub.ref);
        }
      }
      this._modeSubscribers = [];
    }
    if (this._leafChangeTimer) {
      clearTimeout(this._leafChangeTimer);
      this._leafChangeTimer = null;
    }
    this._cachedItems = null;
    this._cachedStats = null;
  }

  /* ---------------------------------------------------------------------- */
  /*  Build Panel                                                           */
  /* ---------------------------------------------------------------------- */
  _buildPanel() {
    const root = this.containerEl;
    root.empty();
    root.addClass("paperforge-status-panel");
    const header = root.createEl("div", { cls: "paperforge-header" });
    const headerLeft = header.createEl("div", {
      cls: "paperforge-header-left",
    });
    headerLeft.createEl("div", { cls: "paperforge-header-logo", text: "P" });
    this._modeContextEl = headerLeft.createEl("div", {
      cls: "paperforge-mode-context",
    });
    this._headerTitle = headerLeft.createEl("h3", {
      cls: "paperforge-header-title",
      text: "PaperForge",
    });
    this._versionBadge = headerLeft.createEl("span", {
      cls: "paperforge-header-badge",
      text: "v\u2014",
    });
    const refreshBtn = header.createEl("button", {
      cls: "paperforge-header-refresh",
      attr: { "aria-label": "Refresh" },
    });
    refreshBtn.innerHTML = "\u21BB";
    refreshBtn.addEventListener("click", () => {
      this._invalidateIndex();
      this._detectAndSwitch();
    });
    this._messageEl = root.createEl("div", { cls: "paperforge-message" });
    this._contentEl = root.createEl("div", { cls: "paperforge-content-area" });
  }

  /* ---------------------------------------------------------------------- */
  /*  Fetch & Render Stats                                                  */
  /* ---------------------------------------------------------------------- */
  _fetchVersion() {
    const vp = (this.app.vault.adapter as any).basePath as string;
    const plugin = ((this.app as any).plugins.plugins as any)[
      "paperforge"
    ] as any;
    const pluginVer = plugin?.manifest?.version || "?";
    const { path: pythonExe, extraArgs = [] } = resolvePythonExecutable(
      vp,
      plugin?.settings ?? null,
      undefined,
      undefined
    );
    checkRuntimeVersion(pythonExe, pluginVer, vp, 10000, undefined).then(
      (result: any) => {
        if (result.status === "not-installed") return;
        const v = result.pyVersion || "";
        this._paperforgeVersion = v.startsWith("v") ? v : "v" + v;
        if (this._versionBadge)
          this._versionBadge.setText(this._paperforgeVersion);
        if (
          this._driftBannerEl &&
          pluginVer &&
          this._paperforgeVersion !== "v" + pluginVer.replace(/^v/, "")
        ) {
          this._driftBannerEl.style.display = "block";
          this._driftBannerEl.setText(
            t("dashboard_drift_warning")
              .replace("{0}", this._paperforgeVersion)
              .replace("{1}", "v" + pluginVer.replace(/^v/, ""))
          );
        } else if (this._driftBannerEl) {
          this._driftBannerEl.style.display = "none";
        }
      }
    );
  }

  _fetchStats(quiet: boolean) {
    if (!this._metricsEl) return;
    if (!quiet && !this._cachedStats) {
      this._metricsEl.empty();
      this._metricsEl.createEl("div", {
        cls: "paperforge-status-loading",
        text: "Loading...",
      });
    } else if (quiet && !this._cachedStats) {
      return;
    }
    const vp = (this.app.vault.adapter as any).basePath as string;
    const plugin = ((this.app as any).plugins.plugins as any)[
      "paperforge"
    ] as any;
    const { path: pythonExe, extraArgs = [] } = resolvePythonExecutable(
      vp,
      plugin?.settings ?? null,
      undefined,
      undefined
    );
    (execFile as any)(
      pythonExe,
      [...extraArgs, "-m", "paperforge", "dashboard", "--json"],
      { cwd: vp, timeout: 30000 },
      (err: any, stdout: string) => {
        if (!err) {
          try {
            const body = JSON.parse(stdout);
            if (body.ok && body.data) {
              const d = this._normalizeDashboardData(body.data);
              this._cachedStats = d;
              this._metricsEl!.empty();
              this._renderStats(d);
              this._renderOcr(d);
              this._dashboardPermissions = body.data.permissions || {};
              return;
            }
          } catch (_) {}
        }
        this._fallbackFetchStats(quiet, vp, plugin);
      }
    );
  }

  _normalizeDashboardData(data: any) {
    const stats = data.stats || {};
    const ocrHealth = stats.ocr_health || {};
    const pdfHealth = stats.pdf_health || {};
    const ocrVersionState = data.ocr_version_state || {};
    const ocrTotal =
      (ocrHealth.done || 0) +
      (ocrHealth.pending || 0) +
      (ocrHealth.failed || 0);
    return {
      total_papers: stats.papers || 0,
      formal_notes: stats.papers || 0,
      exports: 0,
      bases: 0,
      ocr: {
        total: ocrTotal,
        pending: ocrHealth.pending || 0,
        processing: 0,
        done: ocrHealth.done || 0,
        failed: ocrHealth.failed || 0,
      },
      path_errors: (pdfHealth.broken || 0) + (pdfHealth.missing || 0),
      ocr_version_state: {
        total_papers: ocrVersionState.total_papers || 0,
        derived_stale_count: ocrVersionState.derived_stale_count || 0,
        raw_upgradable_count: ocrVersionState.raw_upgradable_count || 0,
      },
    };
  }

  _fallbackFetchStats(quiet: boolean, vp: string, plugin: any) {
    const systemDir = plugin?.settings?.system_dir || "System";
    const indexPath = path.join(
      vp,
      systemDir,
      "PaperForge",
      "indexes",
      "formal-library.json"
    );
    try {
      const raw = fs.readFileSync(indexPath, "utf-8");
      const index = JSON.parse(raw);
      const items = index.items || [];
      const lifecycleCounts: Record<string, number> = {};
      const healthCounts: Record<
        string,
        { healthy: number; unhealthy: number }
      > = {
        pdf_health: { healthy: 0, unhealthy: 0 },
        ocr_health: { healthy: 0, unhealthy: 0 },
        note_health: { healthy: 0, unhealthy: 0 },
        asset_health: { healthy: 0, unhealthy: 0 },
      };
      let ocrTotal = 0,
        ocrDone = 0,
        ocrPending = 0,
        ocrProcessing = 0,
        ocrFailed = 0;
      let formalNotes = 0;
      for (const item of items) {
        if (item.note_path) formalNotes++;
        const lifecycle = item.lifecycle || "pdf_ready";
        lifecycleCounts[lifecycle] = (lifecycleCounts[lifecycle] || 0) + 1;
        const health = item.health || {};
        for (const dim of [
          "pdf_health",
          "ocr_health",
          "note_health",
          "asset_health",
        ]) {
          const val = health[dim] || "healthy";
          if (val === "healthy") healthCounts[dim].healthy++;
          else healthCounts[dim].unhealthy++;
        }
        const ocrStatus = item.ocr_status || "";
        ocrTotal++;
        if (ocrStatus === "done") ocrDone++;
        else if (ocrStatus === "pending") ocrPending++;
        else if (
          ocrStatus === "processing" ||
          ocrStatus === "queued" ||
          ocrStatus === "running"
        )
          ocrProcessing++;
        else ocrFailed++;
      }
      this._cachedStats = {
        version:
          index.paperforge_version || this._cachedStats?.version || "\u2014",
        total_papers: items.length,
        formal_notes: formalNotes,
        exports: 0,
        bases: 0,
        ocr: {
          total: ocrTotal,
          pending: ocrPending,
          processing: ocrProcessing,
          done: ocrDone,
          failed: ocrFailed,
        },
        path_errors: 0,
        lifecycle_level_counts: lifecycleCounts,
        health_aggregate: healthCounts,
      };
      this._metricsEl!.empty();
      this._renderStats(this._cachedStats);
      this._renderOcr(this._cachedStats);
    } catch (err) {
      if (!quiet && !this._cachedStats) {
        this._metricsEl!.createEl("div", {
          cls: "paperforge-status-loading",
          text: "No index \u2014 trying CLI...",
        });
      }
      const { path: pythonExe, extraArgs = [] } = resolvePythonExecutable(
        vp,
        plugin?.settings ?? null,
        undefined,
        undefined
      );
      (execFile as any)(
        pythonExe,
        [...extraArgs, "-m", "paperforge", "status", "--json"],
        { cwd: vp, timeout: 30000 },
        (err2: any, stdout: string) => {
          if (err2) {
            if (this._cachedStats) return;
            this._metricsEl!.createEl("div", {
              cls: "paperforge-status-error",
              text: "Cannot reach PaperForge CLI.\nMake sure paperforge is installed and in your PATH.",
            });
            return;
          }
          try {
            const d = JSON.parse(stdout);
            this._cachedStats = d;
            this._metricsEl!.empty();
            this._renderStats(d);
            this._renderOcr(d);
          } catch {
            if (!this._cachedStats) {
              this._metricsEl!.createEl("div", {
                cls: "paperforge-status-error",
                text: "Invalid response from paperforge status.",
              });
            }
          }
        }
      );
    }
  }

  /* ── Loading Skeleton Utility (D-24) ── */
  _renderSkeleton(container: HTMLElement) {
    container.addClass("paperforge-loading");
  }

  /* ── Empty State Utility (D-25) ── */
  _renderEmptyState(container: HTMLElement, message: string) {
    container.createEl("div", {
      cls: "paperforge-empty-state",
      text: message || "No data",
    });
  }

  /* ── Metric Progress Bar Helper (D-05) ── */
  _buildMetricBar(card: HTMLElement, value: number, max: number) {
    if (max <= 0) return;
    const pct = Math.min(100, (value / max) * 100);
    const bar = card.createEl("div", { cls: "paperforge-metric-progress" });
    bar.createEl("div", {
      cls: "paperforge-metric-progress-fill",
      attr: { style: `width:${pct.toFixed(1)}%` },
    });
  }

  /* ── Index Loading (D-11, D-17, D-19) ── */
  _loadIndex(): any {
    const vp = (this.app.vault.adapter as any).basePath as string;
    const plugin = ((this.app as any).plugins.plugins as any)[
      "paperforge"
    ] as any;
    const systemDir = plugin?.settings?.system_dir || "System";
    const indexPath = path.join(
      vp,
      systemDir,
      "PaperForge",
      "indexes",
      "formal-library.json"
    );
    try {
      const raw = fs.readFileSync(indexPath, "utf-8");
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  /* ── Cached Index Accessor (D-14) ── */
  _getCachedIndex(): any {
    if (!this._cachedItems) {
      const index = this._loadIndex();
      this._cachedItems = index ? index.items || [] : [];
    }
    return this._cachedItems;
  }

  /* ── Single Paper Lookup by Key (D-12, D-18) ── */
  _findEntry(key: string): any {
    if (!key) return null;
    const entry =
      this._getCachedIndex().find((item: any) => item.zotero_key === key) ||
      null;
    return overlayEntryWorkflowState(this.app, entry);
  }

  _patchCachedEntry(key: string, patch: any) {
    if (!key || !this._cachedItems) return;
    const idx = this._cachedItems.findIndex(
      (item: any) => item.zotero_key === key
    );
    if (idx === -1) return;
    this._cachedItems[idx] = patchEntryWorkflowState(
      this._cachedItems[idx],
      patch
    );
  }

  /* ── Filter Papers by Domain (D-13, D-16) ── */
  _filterByDomain(domain: string): any[] {
    if (!domain) return [];
    return this._getCachedIndex().filter((item: any) => item.domain === domain);
  }

  /* ── Metric Cards (Enhanced D-04, D-05, D-06) ── */
  _renderStats(d: any) {
    if (this._versionBadge)
      this._versionBadge.setText(
        this._paperforgeVersion || (d.version ? "v" + d.version : "v\u2014")
      );
    if (!d || typeof d.total_papers === "undefined") {
      if (this._metricsEl) this._renderSkeleton(this._metricsEl);
      return;
    }
    if (!this._metricsEl) return;
    this._metricsEl.removeClass("paperforge-loading");
    const totalPapers = d.total_papers || 0;
    const totalFormal = d.formal_notes || 0;
    const metrics = [
      {
        value: totalPapers,
        label: "Papers",
        color: "var(--color-cyan)",
        barMax: 0,
      },
      {
        value: totalFormal,
        label: "Formal Notes",
        color: "var(--color-blue)",
        barMax: totalPapers,
      },
      {
        value: d.exports || 0,
        label: "Exports",
        color: "var(--color-purple)",
        barMax: 0,
      },
    ];
    for (const m of metrics) {
      const card = this._metricsEl.createEl("div", {
        cls: "paperforge-metric-card",
      });
      card.style.setProperty("--metric-color", m.color);
      card.createEl("div", {
        cls: "paperforge-metric-value",
        text: m.value?.toString() || "\u2014",
      });
      card.createEl("div", { cls: "paperforge-metric-label", text: m.label });
      if (m.barMax > 0) {
        this._buildMetricBar(card, m.value, m.barMax);
      }
    }
    const vs = d.ocr_version_state || {};
    if (
      vs.total_papers > 0 &&
      (vs.derived_stale_count > 0 || vs.raw_upgradable_count > 0)
    ) {
      const vsParts: string[] = [];
      if (vs.derived_stale_count > 0)
        vsParts.push(`${vs.derived_stale_count} stale`);
      if (vs.raw_upgradable_count > 0)
        vsParts.push(`${vs.raw_upgradable_count} upgradable`);
      const card = this._metricsEl.createEl("div", {
        cls: "paperforge-metric-card",
      });
      card.style.setProperty("--metric-color", "var(--color-yellow)");
      card.createEl("div", {
        cls: "paperforge-metric-value",
        text: vsParts.join(", "),
      });
      card.createEl("div", {
        cls: "paperforge-metric-label",
        text: "OCR Version",
      });
    }
  }

  /* ── OCR Pipeline ── */
  _renderOcr(d: any) {
    if (!this._ocrSection) return;
    const ocr = d.ocr || {};
    const total = ocr.total || 0;
    if (total === 0) {
      this._ocrSection.style.display = "none";
      return;
    }
    this._ocrSection.style.display = "block";
    if (this._ocrEmpty) this._ocrEmpty.style.display = "none";
    const done = ocr.done || 0;
    const pending = ocr.pending || 0;
    const processing = ocr.processing || 0;
    const failed = ocr.failed || 0;
    if (this._ocrBadge) {
      this._ocrBadge.removeClass("active", "idle");
      if (processing > 0) {
        this._ocrBadge.addClass("active");
        this._ocrBadge.setText("Processing");
      } else if (pending > 0) {
        this._ocrBadge.addClass("idle");
        this._ocrBadge.setText("Pending");
      } else {
        this._ocrBadge.addClass("idle");
        this._ocrBadge.setText("Idle");
      }
    }
    if (this._ocrTrack) {
      this._ocrTrack.empty();
      if (processing > 0) {
        this._ocrTrack.addClass("paperforge-processing");
      } else {
        this._ocrTrack.removeClass("paperforge-processing");
      }
      const segs = [
        { cls: "pending", count: pending },
        { cls: "active", count: processing },
        { cls: "done", count: done },
        { cls: "failed", count: failed },
      ];
      for (const s of segs) {
        if (s.count > 0) {
          const pct = ((s.count / total) * 100).toFixed(1);
          this._ocrTrack.createEl("div", {
            cls: `paperforge-progress-seg ${s.cls}`,
            attr: { style: `width:${pct}%` },
          });
        }
      }
    }
    if (this._ocrCounts) {
      this._ocrCounts.empty();
      const labels = [
        { cls: "pending", value: pending, label: "Pending" },
        { cls: "active", value: processing, label: "Processing" },
        { cls: "done", value: done, label: "Done" },
        { cls: "failed", value: failed, label: "Failed" },
      ];
      for (const l of labels) {
        const cnt = this._ocrCounts.createEl("div", {
          cls: "paperforge-ocr-count",
        });
        cnt.createEl("div", {
          cls: "paperforge-ocr-count-value",
          text: l.value.toString(),
        });
        cnt.createEl("div", {
          cls: "paperforge-ocr-count-label",
          text: l.label,
        });
      }
    }
  }

  /* ── Lifecycle Stepper (D-07 through D-11) ── */
  _renderLifecycleStepper(
    container: HTMLElement,
    lifecycle: any,
    currentStage: string
  ) {
    if (!lifecycle || !currentStage) {
      this._renderSkeleton(container);
      return;
    }
    const stages = [
      { key: "indexed", label: "Indexed" },
      { key: "pdf_ready", label: "PDF Ready" },
      { key: "fulltext_ready", label: "Fulltext Ready" },
      { key: "deep_read_done", label: "Deep Read" },
    ];
    const stepper = container.createEl("div", {
      cls: "paperforge-lifecycle-stepper",
    });
    let foundCurrent = false;
    for (const stage of stages) {
      const step = stepper.createEl("div", { cls: "step" });
      step.createEl("div", { cls: "step-indicator" });
      step.createEl("div", { cls: "step-label", text: stage.label });
      if (stage.key === currentStage) {
        step.addClass("current");
        foundCurrent = true;
      } else if (!foundCurrent) {
        step.addClass("completed");
      } else {
        step.addClass("pending");
      }
    }
  }

  /* ── Health Matrix (D-12 through D-16) ── */
  _renderHealthMatrix(container: HTMLElement, health: any) {
    if (!health) {
      this._renderSkeleton(container);
      return;
    }
    const dimensions = [
      {
        key: "pdf_health",
        label: "PDF Health",
        iconOk: "\u2713",
        iconWarn: "\u26A0",
        iconFail: "\u2717",
      },
      {
        key: "ocr_health",
        label: "OCR Health",
        iconOk: "\u2713",
        iconWarn: "\u26A0",
        iconFail: "\u2717",
      },
      {
        key: "note_health",
        label: "Note Health",
        iconOk: "\u2713",
        iconWarn: "\u26A0",
        iconFail: "\u2717",
      },
      {
        key: "asset_health",
        label: "Asset Health",
        iconOk: "\u2713",
        iconWarn: "\u26A0",
        iconFail: "\u2717",
      },
    ];
    const matrix = container.createEl("div", {
      cls: "paperforge-health-matrix",
    });
    for (const dim of dimensions) {
      const status = health[dim.key] || "healthy";
      const cell = matrix.createEl("div", { cls: "paperforge-health-cell" });
      let icon: string, statusClass: string, tooltip: string;
      if (status === "healthy" || status === "ok") {
        icon = dim.iconOk;
        statusClass = "ok";
        tooltip = `${dim.label}: OK`;
      } else if (
        status === "warn" ||
        status === "warning" ||
        status === "degraded"
      ) {
        icon = dim.iconWarn;
        statusClass = "warn";
        tooltip = `${dim.label}: Needs Attention`;
      } else {
        icon = dim.iconFail;
        statusClass = "fail";
        tooltip = `${dim.label}: Failed`;
      }
      cell.addClass(statusClass);
      cell.setAttribute("title", tooltip);
      cell.createEl("div", { cls: "paperforge-health-cell-icon", text: icon });
      cell.createEl("div", {
        cls: "paperforge-health-cell-label",
        text: dim.label,
      });
    }
  }

  /* ── Maturity Gauge (D-17 through D-20) ── */
  _renderMaturityGauge(
    container: HTMLElement,
    maturityLevel: number | null,
    blockingChecks: any
  ) {
    if (maturityLevel == null || maturityLevel === undefined) {
      this._renderSkeleton(container);
      return;
    }
    const gauge = container.createEl("div", {
      cls: "paperforge-maturity-gauge",
    });
    const track = gauge.createEl("div", { cls: "gauge-track" });
    const maxLevel = 4;
    const currentLevel = Math.max(
      1,
      Math.min(maxLevel, Math.round(maturityLevel))
    );
    for (let i = 1; i <= maxLevel; i++) {
      const seg = track.createEl("div", { cls: "gauge-segment" });
      if (i <= currentLevel) {
        seg.addClass("filled");
        seg.addClass(`level-${i}`);
      }
    }
    gauge.createEl("div", {
      cls: "gauge-level",
      text: `Level ${currentLevel} / ${maxLevel}`,
    });
    if (currentLevel < maxLevel && blockingChecks) {
      const blockers =
        typeof blockingChecks === "string" ? [blockingChecks] : blockingChecks;
      if (blockers.length > 0) {
        const list = gauge.createEl("ul", { cls: "gauge-blockers" });
        for (const check of blockers) {
          list.createEl("li", { text: check });
        }
      }
    }
  }

  /* ── Bar Chart (D-21 through D-23) ── */
  _renderBarChart(
    container: HTMLElement,
    lifecycleCounts: Record<string, number>
  ) {
    if (!lifecycleCounts || Object.keys(lifecycleCounts).length === 0) {
      this._renderEmptyState(container, "No lifecycle data");
      return;
    }
    const stages = [
      { key: "indexed", label: "Indexed", cls: "stage-indexed" },
      { key: "pdf_ready", label: "PDF Ready", cls: "stage-pdf-ready" },
      {
        key: "fulltext_ready",
        label: "Fulltext Ready",
        cls: "stage-fulltext-ready",
      },
      { key: "deep_read_done", label: "Deep Read", cls: "stage-deep-read" },
    ];
    const chart = container.createEl("div", { cls: "paperforge-bar-chart" });
    const maxCount = Math.max(
      1,
      ...stages.map((s) => lifecycleCounts[s.key] || 0)
    );
    for (const stage of stages) {
      const count = lifecycleCounts[stage.key] || 0;
      const pct = (count / maxCount) * 100;
      const row = chart.createEl("div", { cls: "bar-row" });
      row.createEl("div", { cls: "bar-label", text: stage.label });
      const track = row.createEl("div", { cls: "bar-track" });
      track.createEl("div", {
        cls: `bar-fill ${stage.cls}`,
        attr: { style: `width:${pct.toFixed(1)}%` },
      });
      row.createEl("div", { cls: "bar-count", text: count.toString() });
    }
  }

  /* ── Invalidate cached index (D-14) ── */
  _invalidateIndex() {
    this._cachedItems = null;
  }

  /* ── Extract zotero_key from workspace directory name ── */
  _extractZoteroKeyFromPath(filePath: string): string | null {
    return extractZoteroKeyFromPath(filePath);
  }

  /* ── Pure Mode Resolution (D-07, Phase 32) ── */
  _resolveModeForFile(file: any): {
    mode: "global" | "paper" | "collection";
    filePath: string | null;
    key: string | null;
    domain: string | null;
  } {
    if (!file)
      return { mode: "global", filePath: null, key: null, domain: null };
    const ext = file.extension;
    const filePath = file.path;
    if (ext === "base") {
      return {
        mode: "collection",
        filePath,
        key: null,
        domain: file.basename.trim(),
      };
    }
    if (ext === "md") {
      const cache = this.app.metadataCache.getFileCache(file);
      const fmKey = cache && cache.frontmatter && cache.frontmatter.zotero_key;
      if (fmKey) {
        return { mode: "paper", filePath, key: fmKey, domain: null };
      }
    }
    if (ext === "pdf") {
      const items = this._getCachedIndex();
      for (const item of items) {
        const pathMatch = (item.pdf_path || "").match(/\[\[([^\]]+)\]\]/);
        const targetPath = pathMatch ? pathMatch[1] : item.pdf_path;
        if (targetPath === filePath) {
          return {
            mode: "paper",
            filePath,
            key: item.zotero_key,
            domain: null,
          };
        }
      }
    }
    const wsKey = this._extractZoteroKeyFromPath(filePath);
    if (wsKey) {
      return { mode: "paper", filePath, key: wsKey, domain: null };
    }
    return { mode: "global", filePath, key: null, domain: null };
  }

  /* ── Context Detection & Mode Switch (D-01, D-02, D-03, D-04, D-10) ── */
  _detectAndSwitch() {
    const resolved = this._resolveModeForFile(
      this.app.workspace.getActiveFile()
    );
    this._currentDomain = resolved.domain || null;
    this._currentPaperKey = resolved.key || null;
    this._currentPaperEntry = resolved.key
      ? this._findEntry(resolved.key)
      : null;
    this._switchMode(resolved.mode, resolved.filePath);
  }

  /* ── Mode Switching (D-05, D-06) ── */
  _switchMode(mode: string, filePath: string | null) {
    if (this._currentMode === mode && this._currentFilePath === filePath) {
      this._refreshCurrentMode();
      return;
    }
    this._currentMode = mode as "global" | "paper" | "collection";
    this._currentFilePath = filePath;
    this._techDetailsExpanded = false;
    if (!this._contentEl) return;
    this._contentEl.empty();
    this._contentEl.removeClass("switching");
    this._renderModeHeader(mode);
    switch (mode) {
      case "global":
        this._renderGlobalMode();
        break;
      case "paper":
        this._renderPaperMode();
        break;
      case "collection":
        this._renderCollectionMode();
        break;
      case "versions":
        this._renderVersionMode();
        break;
    }
  }

  /* ── Global Mode Render: System Homepage ── */
  _renderGlobalMode() {
    if (!this._contentEl) return;
    const view = this._contentEl.createEl("div", {
      cls: "paperforge-global-view",
    });
    this._driftBannerEl = view.createEl("div", {
      cls: "paperforge-drift-banner",
    });
    this._driftBannerEl.style.display = "none";
    const items = this._getCachedIndex();
    const totalPapers = items.length;
    let pdfReady = 0,
      ocrDone = 0,
      deepReadDone = 0;
    for (const item of items) {
      if (item.has_pdf) pdfReady++;
      if (item.ocr_status === "done") ocrDone++;
      if (item.deep_reading_status === "done") deepReadDone++;
    }
    const snapshot = view.createEl("div", {
      cls: "paperforge-library-snapshot",
    });
    snapshot.createEl("div", {
      cls: "paperforge-section-label",
      text: "Library Snapshot",
    });
    const pills = snapshot.createEl("div", {
      cls: "paperforge-snapshot-pills",
    });
    const snapData = [
      { value: totalPapers, label: "papers" },
      { value: pdfReady, label: "PDFs ready" },
      { value: ocrDone, label: "OCR done" },
      { value: deepReadDone, label: "deep-read done" },
    ];
    for (const s of snapData) {
      const pill = pills.createEl("div", { cls: "paperforge-snapshot-pill" });
      pill.createEl("span", {
        cls: "paperforge-snapshot-value",
        text: String(s.value),
      });
      pill.createEl("span", {
        cls: "paperforge-snapshot-label",
        text: " " + s.label,
      });
    }
    const statusSection = view.createEl("div", {
      cls: "paperforge-system-status",
    });
    statusSection.createEl("div", {
      cls: "paperforge-section-label",
      text: "System Status",
    });
    const statusGrid = statusSection.createEl("div", {
      cls: "paperforge-status-grid",
    });
    const plugin = ((this.app as any).plugins.plugins as any)[
      "paperforge"
    ] as any;
    const pluginVer = plugin?.manifest?.version || "?";
    let pyVer = this._paperforgeVersion;
    if (!pyVer) {
      try {
        const vp = (this.app.vault.adapter as any).basePath as string;
        const { path: pyExe, extraArgs = [] } = resolvePythonExecutable(
          vp,
          plugin?.settings ?? null,
          undefined,
          undefined
        );
        const raw = execFileSync(
          pyExe,
          [
            ...extraArgs,
            "-c",
            "import paperforge; print(paperforge.__version__)",
          ],
          { cwd: vp, timeout: 5000, encoding: "utf-8", windowsHide: true }
        ).trim();
        if (raw) {
          pyVer = raw.startsWith("v") ? raw : "v" + raw;
          this._paperforgeVersion = pyVer;
        }
      } catch {}
    }
    pyVer = pyVer || "\u2014";
    const runtimeOk = pyVer === "v" + pluginVer;
    this._renderSystemStatusRow(
      statusGrid,
      "Runtime",
      runtimeOk ? "healthy" : "mismatch",
      runtimeOk
        ? "v" + pluginVer
        : "plugin v" + pluginVer + " \u2260 CLI " + pyVer
    );
    const index = this._loadIndex();
    const indexOk = index && index.items && index.items.length > 0;
    this._renderSystemStatusRow(
      statusGrid,
      "Index",
      indexOk ? "healthy" : "missing",
      indexOk
        ? index.items.length + " entries"
        : "formal-library.json not found"
    );
    const systemDir = plugin?.settings?.system_dir || "System";
    const vp = (this.app.vault.adapter as any).basePath as string;
    let exportOk = false,
      exportDetail = "No exports found";
    try {
      const exportsDir = path.join(vp, systemDir, "PaperForge", "exports");
      if (fs.existsSync(exportsDir)) {
        const files = fs
          .readdirSync(exportsDir)
          .filter((f: string) => f.endsWith(".json"));
        exportOk = files.length > 0;
        exportDetail = exportOk
          ? files.length + " export(s)"
          : "No JSON exports";
      }
    } catch (_) {}
    this._renderSystemStatusRow(
      statusGrid,
      "Zotero Export",
      exportOk ? "healthy" : "missing",
      exportDetail
    );
    let tokenOk = !!plugin?.settings?.paddleocr_api_key;
    if (!tokenOk) {
      try {
        const sysDir = plugin?.settings?.system_dir || "System";
        const envPath = path.join(vp, sysDir, "PaperForge", ".env");
        if (fs.existsSync(envPath)) {
          const envContent = fs.readFileSync(envPath, "utf-8");
          const tokenMatch = envContent.match(
            /^PADDLEOCR_API_TOKEN\s*=\s*(.+)$/m
          );
          tokenOk = !!(tokenMatch && tokenMatch[1] && tokenMatch[1].trim());
        }
      } catch (_) {}
    }
    if (!tokenOk) {
      tokenOk = !!(
        process.env.PADDLEOCR_API_TOKEN ||
        process.env.PADDLEOCR_API_KEY ||
        process.env.OCR_TOKEN
      );
    }
    this._renderSystemStatusRow(
      statusGrid,
      "OCR Token",
      tokenOk ? "configured" : "missing",
      tokenOk ? "Configured" : "Not set"
    );
    let memOk = false,
      memDetail = "";
    const vp2 = (this.app.vault.adapter as any).basePath as string;
    const rh = getRuntimeHealth(vp2);
    memOk = isHealthOk(vp2);
    memDetail =
      (rh && (rh.summary as any)?.reason) ||
      (rh && (rh.summary as any)?.status) ||
      "Unknown";
    this._renderSystemStatusRow(
      statusGrid,
      "Memory Layer",
      memOk ? "healthy" : "fail",
      memDetail
    );
    const hasVersionMismatch = !runtimeOk && pyVer !== "\u2014";
    const hasIssues = hasVersionMismatch || !indexOk || !exportOk || !tokenOk;
    if (hasIssues) {
      const issueSection = view.createEl("div", {
        cls: "paperforge-issue-summary",
      });
      issueSection.createEl("div", {
        cls: "paperforge-section-label",
        text: "\u9700\u8981\u5904\u7406",
      });
      const issueList = issueSection.createEl("div", {
        cls: "paperforge-issue-list",
      });
      if (hasVersionMismatch)
        issueList.createEl("div", {
          cls: "paperforge-issue-item",
          text: "Runtime version mismatch",
        });
      if (!indexOk)
        issueList.createEl("div", {
          cls: "paperforge-issue-item",
          text: "Index missing or corrupted",
        });
      if (!exportOk)
        issueList.createEl("div", {
          cls: "paperforge-issue-item",
          text: "No Zotero export found",
        });
      if (!tokenOk)
        issueList.createEl("div", {
          cls: "paperforge-issue-item",
          text: "PaddleOCR API key not configured",
        });
      const issueActions = issueSection.createEl("div", {
        cls: "paperforge-issue-actions",
      });
      const doctorBtn = issueActions.createEl("button", {
        cls: "paperforge-contextual-btn",
      });
      doctorBtn.createEl("span", { text: "Run Doctor" });
      doctorBtn.addEventListener("click", () => {
        const action = ACTIONS.find((a) => a.id === "paperforge-doctor");
        if (action) this._runAction(action, doctorBtn);
      });
      const repairBtn = issueActions.createEl("button", {
        cls: "paperforge-contextual-btn",
      });
      repairBtn.createEl("span", { text: "Repair Issues" });
      repairBtn.addEventListener("click", () => {
        const action = ACTIONS.find((a) => a.id === "paperforge-repair");
        if (action) this._runAction(action, repairBtn);
      });
    }
    const actionsRow = view.createEl("div", {
      cls: "paperforge-global-actions",
    });
    actionsRow.createEl("div", {
      cls: "paperforge-section-label",
      text: "Start Working",
    });
    const btnsRow = actionsRow.createEl("div", {
      cls: "paperforge-global-actions-row",
    });
    const hubBtn = btnsRow.createEl("button", {
      cls: "paperforge-contextual-btn primary",
    });
    hubBtn.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\uD83D\uDCC1",
    });
    hubBtn.createEl("span", { text: "Open Literature Hub" });
    hubBtn.addEventListener("click", () => {
      const baseDir = plugin?.settings?.base_dir || "Bases";
      const baseFolder = this.app.vault.getAbstractFileByPath(baseDir);
      if (baseFolder) {
        let baseFile: any = null;
        if ((baseFolder as any).children) {
          baseFile = (baseFolder as any).children.find(
            (f: any) => f.extension === "base"
          );
        }
        if (baseFile) {
          const leaf = this.app.workspace.getLeaf(false);
          if (leaf) leaf.openFile(baseFile);
        } else {
          new Notice("[!!] No .base file found in " + baseDir, 6000);
        }
      } else {
        new Notice("[!!] Base directory not found: " + baseDir, 6000);
      }
    });
    const globalSyncBtn = btnsRow.createEl("button", {
      cls: "paperforge-contextual-btn",
    });
    globalSyncBtn.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    });
    globalSyncBtn.createEl("span", { text: "Sync Library" });
    globalSyncBtn.addEventListener("click", () => {
      const action = ACTIONS.find((a) => a.id === "paperforge-sync");
      if (action) this._runAction(action, globalSyncBtn);
    });
    const globalOcrBtn = btnsRow.createEl("button", {
      cls: "paperforge-contextual-btn",
    });
    globalOcrBtn.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    });
    globalOcrBtn.createEl("span", { text: "Run OCR" });
    globalOcrBtn.addEventListener("click", () => {
      const action = ACTIONS.find((a) => a.id === "paperforge-ocr");
      if (action) this._runAction(action, globalOcrBtn);
    });
    const globalRedoBtn = btnsRow.createEl("button", {
      cls: "paperforge-contextual-btn warn",
    });
    globalRedoBtn.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BA",
    });
    globalRedoBtn.createEl("span", { text: "Redo OCR" });
    globalRedoBtn.addEventListener("click", () => {
      const action = ACTIONS.find((a) => a.id === "paperforge-ocr-redo");
      if (action) this._runAction(action, globalRedoBtn);
    });
  }

  /* ── System Status Row helper ── */
  _renderSystemStatusRow(
    container: HTMLElement,
    label: string,
    status: string,
    detail: string
  ) {
    const row = container.createEl("div", { cls: "paperforge-status-row" });
    const dot = row.createEl("span", { cls: "paperforge-status-dot" });
    dot.addClass(
      status === "healthy" || status === "configured" ? "ok" : "fail"
    );
    row.createEl("span", { cls: "paperforge-status-label", text: label });
    row.createEl("span", {
      cls: "paperforge-status-detail",
      text: detail || "",
    });
  }

  /* ── Per-Paper Mode Render: Reading Companion ── */
  _renderPaperMode() {
    const entry = this._currentPaperEntry;
    const key = this._currentPaperKey;
    if (!this._contentEl) return;
    if (!key) {
      this._renderEmptyState(this._contentEl, "No paper data available.");
      return;
    }
    if (!entry) {
      this._contentEl.createEl("div", {
        cls: "paperforge-content-placeholder",
        text: 'Paper "' + key + '" not found in canonical index. Sync first.',
      });
      return;
    }
    const view = this._contentEl.createEl("div", {
      cls: "paperforge-paper-view",
    });
    const header = view.createEl("div", { cls: "paperforge-paper-header" });
    const titleEl = header.createEl("div", {
      cls: "paperforge-paper-title pf-copy",
      text: entry.title || "Untitled",
    });
    titleEl.addEventListener("click", () => {
      navigator.clipboard.writeText(entry.title || "");
      new Notice("Title copied");
    });
    const meta = header.createEl("div", { cls: "paperforge-paper-meta" });
    if (entry.authors && entry.authors.length > 0) {
      meta.createEl("span", {
        cls: "paperforge-paper-authors",
        text: entry.authors.join(", "),
      });
    }
    if (entry.year) {
      meta.createEl("span", {
        cls: "paperforge-paper-year",
        text: String(entry.year),
      });
    }
    const strip = view.createEl("div", { cls: "paperforge-status-strip" });
    const stripLeft = strip.createEl("div", {
      cls: "paperforge-status-strip-left",
    });
    const stripRight = strip.createEl("div", {
      cls: "paperforge-status-strip-right",
    });
    const items = [
      { key: "pdf", label: "PDF", ok: entry.has_pdf === true },
      {
        key: "ocr",
        label: "OCR",
        ok: entry.ocr_status === "done",
        pending: ["pending", "queued", "processing"].includes(
          entry.ocr_status || ""
        ),
        fail: ["failed", "blocked", "done_incomplete", "nopdf"].includes(
          entry.ocr_status || ""
        ),
      },
      {
        key: "deep",
        label: "\u7CBE\u8BFB",
        ok: entry.deep_reading_status === "done",
      },
    ];
    for (const item of items) {
      const pill = stripLeft.createEl("span", {
        cls: "paperforge-status-pill",
      });
      let statusCls = "pending";
      if (item.ok) statusCls = "ok";
      else if (item.fail) statusCls = "fail";
      else if (item.pending) statusCls = "pending";
      pill.addClass(statusCls);
      const icon = item.ok ? "\u2713" : item.fail ? "\u2717" : "\u25CB";
      pill.createEl("span", { cls: "paperforge-status-pill-icon", text: icon });
      pill.createEl("span", { text: " " + item.label });
    }
    if (entry.pdf_path) {
      const pdfBtn = stripRight.createEl("button", {
        cls: "paperforge-contextual-btn",
      });
      pdfBtn.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\uD83D\uDCC4",
      });
      pdfBtn.createEl("span", { text: "\u6253\u5F00 PDF" });
      pdfBtn.addEventListener("click", () => {
        const pathMatch = entry.pdf_path.match(/\[\[([^\]]+)\]\]/);
        const targetPath = pathMatch ? pathMatch[1] : entry.pdf_path;
        const file = this.app.vault.getAbstractFileByPath(targetPath);
        if (file) {
          this.app.workspace.openLinkText(targetPath, "");
        } else {
          new Notice("[!!] PDF not found: " + targetPath, 6000);
        }
      });
    }
    if (entry.fulltext_path) {
      const ftBtn = stripRight.createEl("button", {
        cls: "paperforge-contextual-btn",
      });
      ftBtn.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\uD83D\uDCDD",
      });
      ftBtn.createEl("span", { text: "\u6253\u5F00\u5168\u6587" });
      ftBtn.addEventListener("click", () =>
        this._openFulltext(entry.fulltext_path)
      );
    }
    // Version history button — always visible, versions mode handles empty state
    const verBtn = stripRight.createEl("button", {
      cls: "paperforge-contextual-btn",
    });
    verBtn.createEl("span", { text: t("version_panel_title") });
    verBtn.addEventListener("click", () => {
      this._switchToVersionMode(key!);
    });
    this._renderPaperOverviewCard(view, entry);
    if (entry.next_step === "ready" && entry.deep_reading_status === "done") {
      const complete = view.createEl("div", { cls: "paperforge-complete-row" });
      complete.createEl("span", { text: "\u2713" });
      complete.createEl("span", {
        text: "\u5DF2\u5B8C\u6210\uFF0C\u53EF\u76F4\u63A5\u4F7F\u7528",
      });
    } else {
      this._renderNextStepCard(view, entry, key);
    }
    this._renderRecentDiscussionCard(view, entry);
    this._renderPaperTechnicalDetails(view, entry);
  }

  /* ── Paper Overview Card: read from formal note body ── */
  _renderPaperOverviewCard(container: HTMLElement, entry: any) {
    const card = container.createEl("div", {
      cls: "paperforge-paper-overview",
    });
    const header = card.createEl("div", {
      cls: "paperforge-paper-overview-header",
    });
    header.createEl("span", {
      cls: "paperforge-paper-overview-title",
      text: "\u6587\u7AE0\u6982\u89C8",
    });
    const body = card.createEl("div", {
      cls: "paperforge-paper-overview-body",
    });
    const excerptEl = body.createEl("div", {
      cls: "paperforge-paper-overview-excerpt",
      text: "\u52A0\u8F7D\u4E2D...",
    });
    if (entry.note_path) {
      const noteFile = this.app.vault.getAbstractFileByPath(entry.note_path);
      if (noteFile) {
        this.app.vault
          .read(noteFile as TFile)
          .then((content: string) => {
            const extracted = this._extractOverviewFromNote(content);
            if (extracted) {
              const truncated =
                extracted.length > 200
                  ? extracted.slice(0, 200) + "..."
                  : extracted;
              excerptEl.setText(truncated);
              if (extracted.length > 200) {
                const expandContainer = body.createEl("div", {
                  cls: "paperforge-expand-container",
                });
                const expandBtn = expandContainer.createEl("button", {
                  cls: "paperforge-expand-icon",
                  title: "\u5C55\u5F00/\u6536\u8D77",
                });
                expandBtn.innerHTML =
                  '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>';
                let expanded = false;
                expandContainer.addEventListener("click", () => {
                  excerptEl.setText(expanded ? truncated : extracted);
                  expandBtn.innerHTML = expanded
                    ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>'
                    : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>';
                  expanded = !expanded;
                });
              }
            } else {
              excerptEl.setText(
                "\u5C1A\u672A\u751F\u6210\u6587\u7AE0\u6982\u89C8\u3002\u8FD0\u884C /pf-deep \u5F00\u59CB\u7CBE\u8BFB\u3002"
              );
            }
          })
          .catch(() => {
            excerptEl.setText(
              "\u65E0\u6CD5\u8BFB\u53D6\u7B14\u8BB0\u5185\u5BB9"
            );
          });
      } else {
        excerptEl.setText("\u7B14\u8BB0\u6587\u4EF6\u4E0D\u5B58\u5728");
      }
    } else {
      excerptEl.setText("\u5C1A\u672A\u751F\u6210\u6587\u7AE0\u6982\u89C8");
    }
  }

  /* ── Extract overview from formal note body ── */
  _extractOverviewFromNote(content: string): string | null {
    if (!content) return null;
    const deepIdx = content.indexOf("## \uD83D\uDD0D \u7CBE\u8BFB");
    if (deepIdx === -1) return null;
    const section = content.slice(deepIdx);
    const markers = [
      "**\u4E00\u53E5\u8BDD\u603B\u89C8:**",
      "**\u4E00\u53E5\u8BDD\u603B\u89C8**",
      "**\u6587\u7AE0\u6458\u8981:**",
      "**\u6587\u7AE0\u6458\u8981**",
    ];
    for (const marker of markers) {
      const idx = section.indexOf(marker);
      if (idx !== -1) {
        const after = section.slice(idx + marker.length);
        const cutMarkers = [
          "**5 Cs",
          "**Figure",
          "**\u8BC1\u636E",
          "### Pass 2",
          "## ",
        ];
        let nextCut = after.length;
        for (const cm of cutMarkers) {
          const ci = after.indexOf(cm);
          if (ci !== -1 && ci < nextCut) nextCut = ci;
        }
        const nnIdx = after.indexOf("\n\n");
        if (nnIdx !== -1 && nnIdx < nextCut) nextCut = nnIdx;
        let text = after.slice(0, nextCut).trim();
        if (text.startsWith("**")) text = text.slice(2);
        if (text.endsWith("**")) text = text.slice(0, -2);
        return text || null;
      }
    }
    const firstNewline = section.indexOf("\n");
    if (firstNewline === -1) return null;
    const para = section
      .slice(firstNewline + 1)
      .split("\n\n")[0]
      .trim();
    if (!para || para.startsWith("###") || para.startsWith("##")) return null;
    return para.length > 300 ? para.slice(0, 300) + "..." : para;
  }

  /* ── Recent Discussion Card: read ai/discussion.md ── */
  _renderRecentDiscussionCard(container: HTMLElement, entry: any) {
    const card = container.createEl("div", {
      cls: "paperforge-discussion-card",
    });
    card.style.display = "none";
    if (!entry.note_path) return;
    const lastSlash = entry.note_path.lastIndexOf("/");
    const wsDir =
      lastSlash !== -1 ? entry.note_path.substring(0, lastSlash) : ".";
    const mdPath = wsDir + "/ai/discussion.md";
    (this.app.vault.adapter as any)
      .exists(mdPath)
      .then((exists: boolean) => {
        if (!exists) return;
        return (this.app.vault.adapter as any).read(mdPath);
      })
      .then(async (raw: string) => {
        if (!raw) return;
        const pairs = this._parseDiscussionMD(raw);
        if (!pairs || pairs.length === 0) return;
        card.style.display = "block";
        const header = card.createEl("div", {
          cls: "paperforge-discussion-header",
        });
        header.createEl("span", {
          cls: "paperforge-discussion-title",
          text: "\u6700\u8FD1\u8BA8\u8BBA",
        });
        for (const qa of pairs) {
          const item = card.createEl("div", {
            cls: "paperforge-discussion-item",
          });
          const qEl = item.createEl("div", { cls: "paperforge-discussion-q" });
          qEl.createEl("span", {
            cls: "paperforge-discussion-q-label",
            text: "\u63D0\u95EE\uFF1A",
          });
          qEl.createEl("span", {
            cls: "paperforge-discussion-q-text",
            text: qa.question,
          });
          const aEl = item.createEl("div", { cls: "paperforge-discussion-a" });
          let longAnswer = false;
          if (qa.answer && qa.answer.length > 500) {
            longAnswer = true;
            aEl.classList.add("paperforge-discussion-a-collapsed");
          }
          await MarkdownRenderer.render(
            this.app,
            qa.answer || "",
            aEl,
            mdPath,
            this
          );
          if (longAnswer) {
            let expanded = false;
            item.style.cursor = "pointer";
            item.addEventListener("click", () => {
              expanded = !expanded;
              aEl.classList.toggle(
                "paperforge-discussion-a-collapsed",
                !expanded
              );
              aEl.classList.toggle(
                "paperforge-discussion-a-expanded",
                expanded
              );
            });
          }
        }
        const viewAll = card.createEl("a", {
          cls: "paperforge-discussion-viewall",
          text: "\u67E5\u770B\u5168\u90E8\u8BA8\u8BBA \u2192",
        });
        viewAll.addEventListener("click", (e: MouseEvent) => {
          e.preventDefault();
          const discFile = this.app.vault.getAbstractFileByPath(mdPath);
          if (discFile) {
            this.app.workspace.openLinkText(mdPath, "");
          } else {
            new Notice("\u8BA8\u8BBA\u6587\u4EF6\u5C1A\u672A\u751F\u6210");
          }
        });
      })
      .catch((e: any) => {
        console.error(
          "PaperForge: discussion.md read error",
          mdPath,
          e.message
        );
      });
  }

  _parseDiscussionMD(
    content: string
  ): { question: string; answer: string }[] | null {
    const sessions = content.split(/\n## /).slice(1);
    if (sessions.length === 0) return null;
    const lastSession = sessions[sessions.length - 1];
    const pairs: { question: string; answer: string }[] = [];
    const qaBlocks = lastSession.split(/\*\*\u95EE\u9898:\*\*/).slice(1);
    for (const block of qaBlocks) {
      const answerMatch = block.match(/\*\*\u89E3\u7B54:\*\*/);
      if (!answerMatch) continue;
      const question = block.substring(0, answerMatch.index).trim();
      const answer = block
        .substring(answerMatch.index! + "\u89E3\u7B54:".length + 4)
        .trim();
      pairs.push({ question, answer });
    }
    return pairs.slice(-3);
  }

  /* ── Paper Technical Details (disclosure with workflow toggles) ── */
  _renderPaperTechnicalDetails(container: HTMLElement, entry: any) {
    const key = this._currentPaperKey;
    const section = container.createEl("div", {
      cls: "paperforge-technical-details",
    });
    const toggle = section.createEl("button", {
      cls: "paperforge-technical-details-toggle",
    });
    const body = section.createEl("div", {
      cls: "paperforge-technical-details-body",
    });
    body.style.display = "none";
    if (this._techDetailsExpanded) {
      body.style.display = "block";
      toggle.setText("\u6280\u672F\u8BE6\u60C5 \u25BE");
    } else {
      toggle.setText("\u6280\u672F\u8BE6\u60C5 \u25B8");
    }
    toggle.addEventListener("click", () => {
      const visible = body.style.display !== "none";
      body.style.display = visible ? "none" : "block";
      toggle.setText(
        visible
          ? "\u6280\u672F\u8BE6\u60C5 \u25B8"
          : "\u6280\u672F\u8BE6\u60C5 \u25BE"
      );
      this._techDetailsExpanded = !visible;
    });
    const togglesRow = body.createEl("div", {
      cls: "paperforge-workflow-toggles",
    });
    const toggleFields = [
      { key: "do_ocr", label: "OCR", hint: "\u52A0\u5165 OCR" },
      {
        key: "analyze",
        label: "\u7CBE\u8BFB",
        hint: "\u6807\u8BB0\u7CBE\u8BFB",
      },
    ];
    for (const tf of toggleFields) {
      const label = togglesRow.createEl("label", {
        cls: "paperforge-workflow-toggle",
      });
      const cb = label.createEl("input", {
        type: "checkbox",
        cls: "paperforge-workflow-checkbox",
      });
      cb.checked = entry[tf.key] === true;
      label.createEl("span", {
        cls: "paperforge-workflow-toggle-label",
        text: tf.label,
      });
      label.createEl("span", {
        cls: "paperforge-workflow-toggle-hint",
        text: tf.hint,
      });
      cb.addEventListener("change", async () => {
        const noteFile = entry.note_path
          ? this.app.vault.getAbstractFileByPath(entry.note_path)
          : null;
        if (!noteFile) {
          new Notice("[!!] Note file not found", 6000);
          return;
        }
        const newVal = cb.checked;
        await this.app.fileManager.processFrontMatter(
          noteFile as TFile,
          (fm: any) => {
            fm[tf.key] = newVal;
          }
        );
        this._patchCachedEntry(key!, { [tf.key]: newVal });
        this._currentPaperEntry = patchEntryWorkflowState(
          this._currentPaperEntry,
          { [tf.key]: newVal }
        );
      });
    }
    const health = entry.health || {};
    const rows = [
      ["PDF Health", health.pdf_health || "\u2014"],
      ["OCR Status", entry.ocr_status || "\u2014"],
      ["Asset Health", health.asset_health || "\u2014"],
      ["Note Path", entry.note_path || "\u2014"],
      ["Fulltext Path", entry.fulltext_path || "\u2014"],
    ];
    const copyableLabels = new Set(["Note Path", "Fulltext Path", "Key"]);
    for (const [l, v] of rows) {
      const row = body.createEl("div", { cls: "paperforge-technical-row" });
      row.createEl("span", { cls: "paperforge-technical-label", text: l });
      const valEl = row.createEl("span", {
        cls: "paperforge-technical-value",
        text: String(v),
      });
      if (copyableLabels.has(l) && v && v !== "\u2014") {
        valEl.addClass("pf-copy");
        valEl.addEventListener("click", () => {
          navigator.clipboard.writeText(v);
          new Notice(l + " copied");
        });
      }
    }
  }

  /* ── Next-Step Recommendation Card (D-08, D-09) ── */
  _renderNextStepCard(container: HTMLElement, entry: any, key: string) {
    const nextStep = entry.next_step || "ready";
    const stepInfo: Record<
      string,
      { label: string; text: string; cmd: string | null; icon: string }
    > = {
      sync: {
        label: "Sync Needed",
        text: "This paper needs to be synced from Zotero. Click to run sync.",
        cmd: "sync",
        icon: "\u21BB",
      },
      ocr: {
        label: "OCR Needed",
        text: "Fulltext is missing but PDF is present. Click to run OCR.",
        cmd: "ocr",
        icon: "\u229E",
      },
      repair: {
        label: "Repair Needed",
        text: "State divergence or path errors detected. Click to repair.",
        cmd: "repair",
        icon: "\u21BA",
      },
      "rebuild index": {
        label: "Rebuild Needed",
        text: "Index may be stale. Click to run sync to rebuild.",
        cmd: "sync",
        icon: "\u21BB",
      },
      "/pf-deep": {
        label: "Ready for Deep Reading",
        text: "Fulltext is ready. Copy /pf-deep command and run in your agent.",
        cmd: null,
        icon: "\uD83D\uDD0D",
      },
      ready: {
        label: "All Set",
        text: "This paper is fully processed and ready for use.",
        cmd: "ready",
        icon: "\u2713",
      },
    };
    const info = stepInfo[nextStep] || stepInfo["ready"];
    const card = container.createEl("div", {
      cls: "paperforge-next-step-card",
    });
    if (nextStep === "ready") card.addClass("ready");
    card.createEl("div", {
      cls: "paperforge-next-step-label",
      text: "Recommended Next Step",
    });
    card.createEl("div", { cls: "paperforge-next-step-text", text: info.text });
    if (info.cmd && info.cmd !== "ready") {
      const trigger = card.createEl("button", {
        cls: "paperforge-next-step-trigger",
      });
      trigger.createEl("span", { text: info.icon + "  " + info.label });
      trigger.addEventListener("click", () => {
        const action = ACTIONS.find((a) => a.cmd === info.cmd);
        if (action) this._runAction(action, trigger);
      });
    } else if (nextStep === "/pf-deep") {
      const trigger = card.createEl("button", {
        cls: "paperforge-next-step-trigger",
      });
      trigger.createEl("span", {
        text: "\uD83D\uDCCB  " + t("copy_pf_deep_cmd"),
      });
      trigger.addEventListener("click", () => {
        const fullCmd = "/pf-deep " + key;
        navigator.clipboard
          .writeText(fullCmd)
          .then(() => {
            trigger.setText("\u2713  " + t("copied"));
            new Notice(fullCmd + " copied");
          })
          .catch(() => {
            new Notice("[!!] Clipboard write failed", 6000);
          });
      });
      const platformKey =
        (((this.app as any).plugins.plugins as any)["paperforge"] as any)
          ?.settings?.agent_platform || "opencode";
      const AGENTS: Record<string, string> = {
        opencode: "OpenCode",
        claude: "Claude Code",
        cursor: "Cursor",
        github_copilot: "GitHub Copilot",
        windsurf: "Windsurf",
        codex: "Codex",
        gemini: "Gemini CLI",
        cline: "Cline",
      };
      const platformName = AGENTS[platformKey] || platformKey;
      const labelEl = card.createEl("div", {
        cls: "paperforge-agent-platform-label",
      });
      labelEl.setText(t("run_in_agent").replace("{0}", platformName));
    } else if (nextStep === "ready") {
      const trigger = card.createEl("button", {
        cls: "paperforge-next-step-trigger",
      });
      trigger.createEl("span", { text: "\u2713  " + info.label });
    }
  }

  /* ── Open Fulltext File in Obsidian (D-12) ── */
  _openFulltext(fulltextPath: string) {
    if (!fulltextPath) {
      new Notice("[!!] No fulltext path available for this paper", 6000);
      return;
    }
    const file = this.app.vault.getAbstractFileByPath(fulltextPath);
    if (file) {
      this.app.workspace.openLinkText(file.path, "");
    } else {
      new Notice("[!!] Fulltext file not found: " + fulltextPath, 6000);
    }
  }

  /* ── Collection Mode Render: Batch Workflow Workspace ── */
  _renderCollectionMode() {
    const domain = this._currentDomain || "Unknown";
    const domainItems = this._filterByDomain(domain);
    if (domainItems.length === 0) {
      this._renderGlobalMode();
      return;
    }
    if (!this._contentEl) return;
    const view = this._contentEl.createEl("div", {
      cls: "paperforge-collection-view",
    });
    const totalPapers = domainItems.length;
    let hasPdf = 0,
      ocrDone = 0,
      analyzeReady = 0,
      deepRead = 0;
    let ocrPending = 0,
      ocrProcessing = 0,
      ocrFailed = 0;
    for (const item of domainItems) {
      if (item.has_pdf) hasPdf++;
      if (item.ocr_status === "done") ocrDone++;
      if (item.ocr_status === "done" && item.analyze === true) analyzeReady++;
      if (item.deep_reading_status === "done") deepRead++;
      const ocs = item.ocr_status || "";
      if (ocs === "pending" || ocs === "queued") ocrPending++;
      else if (ocs === "processing") ocrProcessing++;
      else if (
        ocs === "failed" ||
        ocs === "blocked" ||
        ocs === "done_incomplete" ||
        ocs === "nopdf"
      )
        ocrFailed++;
    }
    const header = view.createEl("div", {
      cls: "paperforge-collection-header",
    });
    header.createEl("div", {
      cls: "paperforge-collection-title",
      text: domain,
    });
    const wfSection = view.createEl("div", {
      cls: "paperforge-workflow-overview",
    });
    wfSection.createEl("div", {
      cls: "paperforge-section-label",
      text: "Workflow Overview",
    });
    const funnel = wfSection.createEl("div", {
      cls: "paperforge-workflow-funnel",
    });
    const stages = [
      { value: totalPapers, label: "Total" },
      { value: hasPdf, label: "PDF Ready" },
      { value: ocrDone, label: "OCR Done" },
      { value: deepRead, label: "Deep Read" },
    ];
    for (let i = 0; i < stages.length; i++) {
      const stage = funnel.createEl("div", {
        cls: "paperforge-workflow-stage",
      });
      stage.createEl("div", {
        cls: "paperforge-workflow-stage-value",
        text: String(stages[i].value),
      });
      stage.createEl("div", {
        cls: "paperforge-workflow-stage-label",
        text: stages[i].label,
      });
      if (i < stages.length - 1) {
        funnel.createEl("div", {
          cls: "paperforge-workflow-arrow",
          text: "\u2192",
        });
      }
    }
    if (ocrPending + ocrProcessing + ocrDone + ocrFailed > 0) {
      const ocrSection = view.createEl("div", {
        cls: "paperforge-ocr-section",
      });
      const ocrHeader = ocrSection.createEl("div", {
        cls: "paperforge-collection-ocr-header",
      });
      ocrHeader.createEl("h4", {
        cls: "paperforge-ocr-title",
        text: "OCR Pipeline",
      });
      const ocrBadge = ocrHeader.createEl("span", {
        cls: "paperforge-ocr-badge idle",
      });
      if (ocrProcessing > 0) {
        ocrBadge.addClass("active");
        ocrBadge.setText("Processing");
      } else if (ocrPending > 0) ocrBadge.setText("Pending");
      else {
        ocrBadge.addClass("idle");
        ocrBadge.setText("Idle");
      }
      const ocrTrack = ocrSection.createEl("div", {
        cls: "paperforge-progress-track",
      });
      if (ocrProcessing > 0) ocrTrack.addClass("paperforge-processing");
      const totalOcr = ocrPending + ocrProcessing + ocrDone + ocrFailed;
      const ocrSegs = [
        { cls: "pending", count: ocrPending },
        { cls: "active", count: ocrProcessing },
        { cls: "done", count: ocrDone },
        { cls: "failed", count: ocrFailed },
      ];
      for (const s of ocrSegs) {
        if (s.count > 0) {
          const pct = ((s.count / totalOcr) * 100).toFixed(1);
          ocrTrack.createEl("div", {
            cls: `paperforge-progress-seg ${s.cls}`,
            attr: { style: `width:${pct}%` },
          });
        }
      }
      const ocrCounts = ocrSection.createEl("div", {
        cls: "paperforge-ocr-counts",
      });
      const ocrLabels = [
        { cls: "pending", value: ocrPending, label: "Pending" },
        { cls: "active", value: ocrProcessing, label: "Processing" },
        { cls: "done", value: ocrDone, label: "Done" },
        { cls: "failed", value: ocrFailed, label: "Attention" },
      ];
      for (const l of ocrLabels) {
        const cnt = ocrCounts.createEl("div", { cls: "paperforge-ocr-count" });
        cnt.createEl("div", {
          cls: "paperforge-ocr-count-value",
          text: l.value.toString(),
        });
        cnt.createEl("div", {
          cls: "paperforge-ocr-count-label",
          text: l.label,
        });
      }
    }
    const actionsRow = view.createEl("div", {
      cls: "paperforge-collection-actions",
    });
    const ocrActionBtn = actionsRow.createEl("button", {
      cls: "paperforge-contextual-btn primary",
    });
    ocrActionBtn.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    });
    ocrActionBtn.createEl("span", { text: "Run OCR" });
    ocrActionBtn.addEventListener("click", () => {
      const action = ACTIONS.find((a) => a.id === "paperforge-ocr");
      if (action) this._runAction(action, ocrActionBtn);
    });
    const syncBtn = actionsRow.createEl("button", {
      cls: "paperforge-contextual-btn",
    });
    syncBtn.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    });
    syncBtn.createEl("span", { text: "Sync Library" });
    syncBtn.addEventListener("click", () => {
      const action = ACTIONS.find((a) => a.id === "paperforge-sync");
      if (action) this._runAction(action, syncBtn);
    });
    const redoBtn = actionsRow.createEl("button", {
      cls: "paperforge-contextual-btn warn",
    });
    redoBtn.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BA",
    });
    redoBtn.createEl("span", { text: "Redo OCR" });
    redoBtn.addEventListener("click", () => {
      const action = ACTIONS.find((a) => a.id === "paperforge-ocr-redo");
      if (action) this._runAction(action, redoBtn);
    });
    this.renderSearchSection(view);
  }

  /* ── Refresh current mode (called on index change, D-09, REFR-01) ── */
  _refreshCurrentMode() {
    if (!this._currentMode || !this._contentEl) return;
    this._contentEl.empty();
    this._contentEl.addClass("switching");
    this._invalidateIndex();
    this._currentPaperEntry = this._currentPaperKey
      ? this._findEntry(this._currentPaperKey)
      : null;
    this._renderModeHeader(this._currentMode);
    try {
      switch (this._currentMode) {
        case "global":
          this._renderGlobalMode();
          break;
        case "paper":
          this._renderPaperMode();
          break;
        case "collection":
          this._renderCollectionMode();
          break;
        case "versions":
          this._renderVersionMode();
          break;
      }
    } finally {
      setTimeout(() => {
        if (this._contentEl) this._contentEl.removeClass("switching");
      }, 50);
    }
  }

  /* ── Switch to Version Mode ── */
  _switchToVersionMode(paperKey: string) {
    const adapter = this.app.vault.adapter as unknown as Record<
      string,
      unknown
    >;
    const vp = adapter.basePath;
    const vaultPath = typeof vp === "string" ? vp : "";
    if (!vaultPath) {
      new Notice("Cannot determine vault path");
      return;
    }
    this._versionPapers = listPapersWithBackups(vaultPath);
    this._versionFilter = "";
    this._currentMode = "versions";
    this._currentFilePath = null;
    this._techDetailsExpanded = false;
    if (!this._contentEl) return;
    this._contentEl.empty();
    this._contentEl.removeClass("switching");
    this._renderModeHeader("versions");
    this._renderVersionMode();
  }

  /* ── Version Mode Render: File Recovery-style Panel ── */
  _renderVersionMode() {
    if (!this._contentEl) return;
    const view = this._contentEl.createEl("div", {
      cls: "paperforge-version-panel",
    });

    const adapter = this.app.vault.adapter as unknown as Record<
      string,
      unknown
    >;
    const vp = adapter.basePath;
    const vaultPath = typeof vp === "string" ? vp : "";
    if (!vaultPath) {
      view.createEl("div", {
        cls: "paperforge-status-error",
        text: "Could not determine vault path",
      });
      return;
    }

    // Re-scan if null
    if (!this._versionPapers || this._versionPapers.length === 0) {
      this._versionPapers = listPapersWithBackups(vaultPath);
    }

    // ── Left Panel: Filter + Paper List ──
    const left = view.createEl("div", { cls: "paperforge-version-left" });
    const right = view.createEl("div", { cls: "paperforge-version-right" });

    // Filter input
    const filterInput = left.createEl("input", {
      cls: "paperforge-version-filter",
      attr: { type: "text", placeholder: t("version_filter_placeholder") },
    }) as HTMLInputElement;
    filterInput.value = this._versionFilter;

    // Paper list container
    const paperList = left.createEl("div", {
      cls: "paperforge-version-paper-list",
    });

    const renderPaperList = () => {
      paperList.empty();
      const filter = this._versionFilter.toLowerCase();
      const filtered = this._versionPapers
        ? this._versionPapers.filter(
            (p) =>
              !filter ||
              p.key.toLowerCase().includes(filter) ||
              p.title.toLowerCase().includes(filter)
          )
        : [];

      if (filtered.length === 0) {
        paperList.createEl("div", {
          cls: "paperforge-meta",
          text: t("version_no_backups"),
        });
        return;
      }

      const countLabel = paperList.createEl("div", {
        cls: "paperforge-meta",
        text: t("version_papers_count").replace("{n}", String(filtered.length)),
      });

      for (const paper of filtered) {
        const row = paperList.createEl("div", {
          cls: "paperforge-version-paper-item",
        });
        const titleEl = row.createEl("span", {
          cls: "paperforge-version-paper-title",
          text: paper.title,
        });
        const badge = row.createEl("span", {
          cls: "paperforge-version-paper-versions",
          text: paper.versions.map((v) => v.label).join(" "),
        });
        row.addEventListener("click", () => {
          // Highlight selected, show version timeline in right panel
          paperList
            .querySelectorAll(".paperforge-version-paper-item.selected")
            .forEach((el) => el.removeClass("selected"));
          row.addClass("selected");
          renderTimeline(paper);
        });
      }
    };

    // Filter on input
    filterInput.addEventListener("input", () => {
      this._versionFilter = filterInput.value;
      renderPaperList();
    });

    // ── Right Panel: Timeline ──
    const timelineArea = right.createEl("div", {
      cls: "paperforge-version-timeline-area",
    });

    const renderTimeline = (paper: PaperVersionInfo) => {
      timelineArea.empty();
      const header = timelineArea.createEl("div", {
        cls: "paperforge-version-timeline-header",
      });
      header.createEl("span", { cls: "pf-title", text: paper.title });

      if (paper.versions.length === 0) {
        timelineArea.createEl("div", {
          cls: "paperforge-meta",
          text: t("version_no_backups"),
        });
        return;
      }

      // Version list as timeline
      const timeline = timelineArea.createEl("div", {
        cls: "paperforge-version-timeline",
      });

      for (const ver of paper.versions) {
        const isCurrent = ver.label === paper.currentLabel;
        const entry = timeline.createEl("div", {
          cls:
            "paperforge-version-entry" +
            (isCurrent ? " paperforge-version-current" : ""),
        });
        const dot = entry.createEl("div", { cls: "paperforge-version-dot" });
        const content = entry.createEl("div", {
          cls: "paperforge-version-content",
        });
        const labelRow = content.createEl("div", {
          cls: "paperforge-version-label-row",
        });
        labelRow.createEl("span", {
          cls: "paperforge-version-label",
          text: ver.label,
        });
        if (isCurrent) {
          labelRow.createEl("span", {
            cls: "paperforge-version-current-tag",
            text: t("version_current"),
          });
        }
        const dateStr = ver.created_at ? ver.created_at.slice(0, 10) : "";
        content.createEl("div", {
          cls: "paperforge-meta",
          text: dateStr + " \u2014 " + ver.source,
        });
        const sizeStr = ver.fulltext_size
          ? ver.fulltext_size > 1024
            ? (ver.fulltext_size / 1024).toFixed(0) + "KB"
            : ver.fulltext_size + "B"
          : "";
        if (sizeStr) {
          content.createEl("div", { cls: "paperforge-meta", text: sizeStr });
        }

        // Action buttons
        const actions = content.createEl("div", {
          cls: "paperforge-version-actions",
        });
        const restoreBtn = actions.createEl("button", {
          cls: "pf-btn-primary",
          text: t("version_restore_btn"),
        });
        restoreBtn.addEventListener("click", () => {
          const ok = restoreVersion(vaultPath, paper.key, ver.label);
          if (ok) {
            new Notice(t("version_restore_done").replace("{label}", ver.label));
          } else {
            new Notice("Restore failed", 6000);
          }
        });

        if (paper.versions.length > 1 && !isCurrent) {
          const compareBtn = actions.createEl("button", {
            cls: "pf-btn-secondary",
            text: t("version_compare_btn"),
          });
          compareBtn.addEventListener("click", () => {
            renderComparison(paper, ver.label, paper.currentLabel);
          });
        }
      }
    };

    // ── Comparison Area ──
    const compareArea = right.createEl("div", {
      cls: "paperforge-version-compare",
    });
    compareArea.style.display = "none";

    const renderComparison = (
      paper: PaperVersionInfo,
      vA: string,
      vB: string
    ) => {
      const diffs = compareVersions(vaultPath, paper.key, vA, vB);
      compareArea.style.display = "block";
      compareArea.empty();
      const header = compareArea.createEl("div", {
        cls: "paperforge-version-compare-header",
      });
      header.createEl("span", {
        cls: "pf-title",
        text: t("version_compare_title")
          .replace("{vA}", vA)
          .replace("{vB}", vB),
      });
      header.createEl("span", {
        cls: "paperforge-meta",
        text: t("version_compare_paragraphs").replace(
          "{n}",
          String(diffs.length)
        ),
      });

      if (diffs.length === 0) {
        compareArea.createEl("div", {
          cls: "paperforge-meta",
          text: "No changes",
        });
        return;
      }

      const diffList = compareArea.createEl("div", {
        cls: "paperforge-version-diff-list",
      });
      for (const d of diffs) {
        const diffRow = diffList.createEl("div", {
          cls: "paperforge-version-diff-row",
        });
        const typeLabel =
          d.type === "added" ? "[+]" : d.type === "removed" ? "[-]" : "[~]";
        const headingLabel = d.heading || "paragraph " + (d.paragraphIndex + 1);
        diffRow.createEl("span", {
          cls: "paperforge-version-diff-label",
          text: typeLabel + " " + headingLabel,
        });
        if (d.oldText) {
          diffRow.createEl("pre", {
            cls: "paperforge-version-diff-old",
            text: d.oldText.slice(0, 200),
          });
        }
        if (d.newText) {
          diffRow.createEl("pre", {
            cls: "paperforge-version-diff-new",
            text: d.newText.slice(0, 200),
          });
        }
      }
    };

    // ── Bottom Action Bar ──
    const actionBar = view.createEl("div", {
      cls: "paperforge-version-actions-bar",
    });
    const restoreSelectedBtn = actionBar.createEl("button", {
      cls: "pf-btn-primary",
      text: t("version_restore_selected"),
    });
    const clearOldBtn = actionBar.createEl("button", {
      cls: "pf-btn-secondary",
      text: t("version_clear_old").replace("{size}", ""),
    });

    // Initial render
    renderPaperList();
  }

  /* ── Search Section ── */

  renderSearchSection(view: HTMLElement) {
    this._searchContainer = view.createEl("div", {
      cls: "paperforge-search-section",
    });
    const header = this._searchContainer.createEl("div", {
      cls: "paperforge-search-header",
    });
    header.createEl("span", {
      cls: "pf-label",
      text: "Search",
    });
    const inputRow = this._searchContainer.createEl("div", {
      cls: "paperforge-search-input-row",
    });
    const modeBadge = inputRow.createEl("span", {
      cls: "paperforge-search-mode",
      text: "M",
    });
    this._searchInput = inputRow.createEl("input", {
      cls: "paperforge-search-input",
      attr: {
        type: "text",
        placeholder: "Search papers... (@ for deep search)",
      },
    }) as HTMLInputElement;
    this._searchResultsEl = this._searchContainer.createEl("div", {
      cls: "paperforge-search-results",
    });

    // Detect @ mode prefix + debounced metadata search
    this._searchInput.addEventListener("input", () => {
      const val = this._searchInput?.value || "";
      if (val.startsWith("@") && !val.startsWith("@ ")) {
        modeBadge.setText("@");
        modeBadge.addClass("deep");
      } else {
        modeBadge.setText("M");
        modeBadge.removeClass("deep");
      }
      // Cancel pending debounce
      clearTimeout(this._searchTimer);
      // Debounced metadata search for non-@ queries
      if (!val.startsWith("@") && val.trim()) {
        this._searchTimer = setTimeout(() => {
          this.executeSearch();
        }, 200);
      }
    });

    // Enter triggers CLI search (full search for @ or explicit)
    this._searchInput.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        if (this._searchTimer) {
          clearTimeout(this._searchTimer);
          this._searchTimer = undefined;
        }
        this.executeSearch();
      }
    });
  }

  async executeSearch() {
    if (!this._searchInput || !this._searchResultsEl) return;
    const raw = this._searchInput.value.trim();
    if (!raw) return;

    const isDeep = raw.startsWith("@");
    const query = isDeep ? raw.slice(1).trim() : raw;
    if (!query) return;

    const mode = isDeep ? "retrieve" : "search";

    // Resolve vault path for CLI search
    const adapter = this.app.vault.adapter;
    let vaultPath = "";
    if (adapter && typeof adapter === "object" && "basePath" in adapter) {
      const bp = (adapter as Record<string, unknown>).basePath;
      vaultPath = typeof bp === "string" ? bp : "";
    }

    this._searchResultsEl.empty();
    // ── CLI search path (deep search only) ──
    this._searchResultsEl.createEl("div", {
      cls: "paperforge-search-loading",
      text: "Searching...",
    });

    if (!vaultPath) {
      this._renderSearchError("Could not determine vault path");
      return;
    }

    let pluginSettings: unknown = null;
    const appRecord = this.app as unknown as Record<string, unknown>;
    const pluginsVal = appRecord["plugins"];
    if (
      pluginsVal &&
      typeof pluginsVal === "object" &&
      "plugins" in pluginsVal
    ) {
      const pluginsMap = (pluginsVal as Record<string, unknown>)["plugins"];
      if (
        pluginsMap &&
        typeof pluginsMap === "object" &&
        "paperforge" in pluginsMap
      ) {
        const pf = (pluginsMap as Record<string, unknown>)["paperforge"];
        if (pf && typeof pf === "object" && "settings" in pf) {
          pluginSettings = (pf as Record<string, unknown>)["settings"];
        }
      }
    }

    const { path: pythonExe, extraArgs: pyExtra = [] } =
      resolvePythonExecutable(
        vaultPath,
        pluginSettings as PaperForgeSettings | null | undefined,
        undefined,
        undefined
      );
    const deepFlag = mode === "retrieve" ? ["--deep"] : [];
    const child = spawn(
      pythonExe,
      [...pyExtra, "-m", "paperforge", mode, query, ...deepFlag, "--json"],
      { cwd: vaultPath, timeout: 30000 }
    );

    const chunks: string[] = [];
    child.stdout.on("data", (data: Buffer) => {
      chunks.push(data.toString("utf-8"));
    });
    child.stderr.on("data", () => {
      // ignore stderr (progress bars, etc.)
    });
    child.on("close", (code: number | null) => {
      if (code !== 0) {
        this._renderSearchError(`Search failed (exit ${code})`);
        return;
      }
      const rawOutput = chunks.join("");
      // Strip INFO/WARNING log lines: find JSON between first { and last }
      const firstBrace = rawOutput.indexOf("{");
      const lastBrace = rawOutput.lastIndexOf("}");
      let jsonStr = "";
      if (firstBrace !== -1 && lastBrace > firstBrace) {
        jsonStr = rawOutput.slice(firstBrace, lastBrace + 1);
      } else {
        // Try array form
        const firstBracket = rawOutput.indexOf("[");
        const lastBracket = rawOutput.lastIndexOf("]");
        if (firstBracket !== -1 && lastBracket > firstBracket) {
          jsonStr = rawOutput.slice(firstBracket, lastBracket + 1);
        }
      }
      if (!jsonStr) {
        this._renderSearchError("No JSON output from CLI");
        return;
      }
      try {
        const parsed = JSON.parse(jsonStr) as Record<string, unknown>;
        let results: unknown[] = [];

        if (parsed && typeof parsed === "object" && "data" in parsed) {
          const d = (parsed as Record<string, unknown>).data;
          if (d && typeof d === "object") {
            const dd = d as Record<string, unknown>;
            // Unified PFResult v1: data.matches
            if ("matches" in dd && Array.isArray(dd.matches)) {
              results = dd.matches as unknown[];
            }
          }
        }

        this.renderSearchResults(results, isDeep);
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        this._renderSearchError("Failed to parse results: " + msg);
      }
    });
    child.on("error", (err: Error) => {
      this._renderSearchError("Process error: " + err.message);
    });
  }

  renderSearchResults(results: unknown[], isDeep: boolean) {
    if (!this._searchResultsEl) return;
    this._searchResultsEl.empty();

    if (results.length === 0) {
      this._searchResultsEl.createEl("div", {
        cls: "paperforge-search-empty",
        text: "No results found.",
      });
      return;
    }

    const header = this._searchResultsEl.createEl("div", {
      cls: "paperforge-search-results-header",
    });
    header.createEl("span", {
      text: `${results.length} result${results.length !== 1 ? "s" : ""}`,
    });
    header.createEl("span", {
      cls: "paperforge-search-mode",
      text: isDeep ? "@" : "M",
    });

    for (const r of results) {
      if (!r || typeof r !== "object") continue;
      const rec = r as Record<string, unknown>;
      const card = this._searchResultsEl.createEl("div", {
        cls: "paperforge-search-result-card",
        attr: { role: "button" },
      });

      // Title
      const titleText =
        typeof rec["title"] === "string"
          ? rec["title"]
          : typeof rec["file_name"] === "string"
            ? rec["file_name"]
            : "(untitled)";
      card.createEl("div", {
        cls: "paperforge-search-result-title",
        text: titleText,
      });

      // Note path resolution: main_note_path → note_path → zotero_key lookup in cached index
      const zoteroKey =
        typeof rec["zotero_key"] === "string" ? rec["zotero_key"] : "";
      const mainNotePath =
        typeof rec["main_note_path"] === "string" && rec["main_note_path"]
          ? rec["main_note_path"]
          : null;
      const notePath =
        typeof rec["note_path"] === "string" && rec["note_path"]
          ? rec["note_path"]
          : null;
      let resolvedPath: string | null = mainNotePath || notePath;

      // Fallback: look up zotero_key in cached index for main_note_path / note_path
      if (!resolvedPath && zoteroKey) {
        const cachedIndex = this._getCachedIndex();
        const entry = cachedIndex.find(
          (item: unknown) =>
            item !== null &&
            typeof item === "object" &&
            "zotero_key" in item &&
            (item as Record<string, unknown>).zotero_key === zoteroKey
        );
        if (entry && typeof entry === "object") {
          const e = entry as Record<string, unknown>;
          resolvedPath =
            typeof e["main_note_path"] === "string" && e["main_note_path"]
              ? e["main_note_path"]
              : typeof e["note_path"] === "string" && e["note_path"]
                ? e["note_path"]
                : null;
        }
      }

      if (resolvedPath) {
        card.addEventListener("click", (e: MouseEvent) => {
          const newLeaf = e.ctrlKey || e.metaKey;
          this.app.workspace.openLinkText(resolvedPath, "", newLeaf);
        });
      } else {
        card.addEventListener("click", () => {
          new Notice("[!!] Note not found: " + (zoteroKey || "unknown"), 6000);
        });
      }

      // Meta row
      const meta = card.createEl("div", {
        cls: "paperforge-search-result-meta",
      });

      if (typeof rec["first_author"] === "string" && rec["first_author"]) {
        meta.createEl("span", {
          cls: "paperforge-search-result-author",
          text: rec["first_author"],
        });
      }
      if (typeof rec["journal"] === "string" && rec["journal"]) {
        meta.createEl("span", {
          cls: "paperforge-search-result-journal",
          text: rec["journal"],
        });
      }
      if (rec["score"] !== undefined) {
        const score = rec["score"];
        const scoreText =
          typeof score === "number" ? score.toFixed(3) : String(score);
        meta.createEl("span", {
          cls: "paperforge-search-result-score",
          text: "Score: " + scoreText,
        });
      }

      // Domain tag
      if (typeof rec["domain"] === "string" && rec["domain"]) {
        card.createEl("span", {
          cls: "paperforge-search-result-tag",
          text: rec["domain"],
        });
      }

      // Abstract snippet
      if (typeof rec["abstract"] === "string" && rec["abstract"]) {
        const abs = rec["abstract"] as string;
        card.createEl("div", {
          cls: "paperforge-search-result-abstract",
          text: abs.length > 200 ? abs.slice(0, 200) + "..." : abs,
        });
      }

      // @ mode: matched text
      if (
        isDeep &&
        typeof rec["text"] === "string" &&
        rec["text"]
      ) {
        const mt = rec["text"] as string;
        card.createEl("div", {
          cls: "paperforge-search-result-source",
          text: mt.length > 300 ? mt.slice(0, 300) + "..." : mt,
        });
      }
    }
  }

  _renderSearchError(msg: string) {
    if (!this._searchResultsEl) return;
    this._searchResultsEl.empty();
    this._searchResultsEl.createEl("div", {
      cls: "paperforge-search-error",
      text: msg,
    });
  }
  /* ── Run Action ── */
  _runAction(a: any, card: HTMLElement) {
    if (a.disabled) {
      new Notice(
        `[i] ${a.disabledMsg || "This action is not yet available."}`,
        6000
      );
      return;
    }
    if (card.classList.contains("running")) {
      return;
    }
    card.addClass("running");
    const vp = (this.app.vault.adapter as any).basePath as string;
    this._showMessage("Processing...", "running");
    let extraArgs = Array.isArray(a.args) ? [...a.args] : [];
    if (a.needsKey) {
      const activeFile = this.app.workspace.getActiveFile();
      let key: string | null = null;
      if (activeFile) {
        const cache = this.app.metadataCache.getFileCache(activeFile);
        if (cache && cache.frontmatter && cache.frontmatter.zotero_key) {
          key = cache.frontmatter.zotero_key;
        } else {
          key = this._extractZoteroKeyFromPath(activeFile.path);
        }
        if (key) {
          extraArgs = [...extraArgs, key];
        } else if (cache && cache.frontmatter) {
          this._showMessage(
            "[!!] No zotero_key in active note frontmatter",
            "error"
          );
          new Notice(
            "[!!] Open a paper note with a zotero_key in its frontmatter first",
            6000
          );
          card.removeClass("running");
          return;
        } else {
          this._showMessage("[!!] No frontmatter in active note", "error");
          new Notice(
            "[!!] The active note has no frontmatter with a zotero_key",
            6000
          );
          card.removeClass("running");
          return;
        }
      } else {
        this._showMessage("[!!] No active note open", "error");
        new Notice(
          "[!!] Open a paper note with a zotero_key in its frontmatter first",
          6000
        );
        card.removeClass("running");
        return;
      }
    }
    if (a.needsFilter) {
      extraArgs = [...extraArgs, "--all"];
    }
    const cmdTimeout = a.needsFilter ? 60000 : a.needsKey ? 30000 : 600000;
    const { path: pythonExe, extraArgs: pyExtra = [] } =
      resolvePythonExecutable(
        vp,
        ((this.app as any).plugins.plugins as any)["paperforge"]?.settings ??
          null,
        undefined,
        undefined
      );
    const child = spawn(
      pythonExe,
      [...pyExtra, "-m", "paperforge", a.cmd, ...extraArgs],
      { cwd: vp, timeout: cmdTimeout }
    );
    const log: string[] = [];
    const startTime = Date.now();
    const pollTimer = setInterval(() => this._fetchStats(true), 4000);
    child.stdout.on("data", (data: Buffer) => {
      const lines = data.toString("utf-8").split("\n").filter(Boolean);
      for (const l of lines) {
        const clean = l.trim();
        if (clean) {
          log.push(clean);
          this._showMessage(log.slice(-8).join("\n"), "running");
        }
      }
    });
    child.stderr.on("data", (data: Buffer) => {
      const lines = data.toString("utf-8").split("\n").filter(Boolean);
      for (const l of lines) {
        if (l.includes("\r") || l.includes("%") || l.includes("\u2588"))
          continue;
        const trim = l.trim();
        if (trim && !trim.match(/^\d+%|^\|/)) {
          log.push(trim);
          this._showMessage(log.slice(-8).join("\n"), "running");
        }
      }
    });
    child.on("close", (code: number | null) => {
      clearInterval(pollTimer);
      card.removeClass("running");
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      if (code !== 0) {
        const last = log.slice(-3).join(" | ") || "exit code " + code;
        if ((a.cmd === "repair" || a.cmd === "ocr") && code === 1) {
          this._showMessage("[WARN] " + last, "running");
          new Notice("[WARN] " + a.cmd + " partial: " + last, 8000);
          this._fetchStats(true);
        } else {
          this._showMessage("[!!] " + last, "error");
          new Notice("[!!] " + a.cmd + " failed: " + last, 8000);
        }
      } else if (a.needsKey || a.needsFilter) {
        const output = log.join("\n");
        if (output.trim()) {
          try {
            JSON.parse(output);
            navigator.clipboard
              .writeText(output)
              .then(() => {
                const summary = `${elapsed}s \u2014 ${output.length} chars copied`;
                this._showMessage("[OK] " + a.title + ": " + summary, "ok");
                new Notice(
                  "[OK] " + a.okMsg + " \u2014 " + output.length + " chars"
                );
              })
              .catch((err: any) => {
                this._showMessage(
                  "[!!] Clipboard write failed: " + err.message,
                  "error"
                );
                new Notice("[!!] Clipboard error", 6000);
              });
          } catch (e: any) {
            this._showMessage("[!!] Invalid JSON from " + a.title, "error");
            new Notice(
              "[!!] " +
                a.title +
                " returned invalid JSON: " +
                e.message.slice(0, 100),
              8000
            );
          }
        } else {
          this._showMessage("[!!] No output from context command", "error");
          new Notice("[!!] Context command returned empty output", 8000);
        }
        this._fetchStats(true);
      } else {
        const updated = log.filter((l) => l.match(/updated \d+/));
        const lastUpdated = updated.pop() || log[log.length - 1] || "";
        const summary = `${elapsed}s \u2014 ${lastUpdated}`;
        this._showMessage("[OK] " + a.title + ": " + summary, "ok");
        new Notice("[OK] " + a.okMsg);
        if (this._contentEl) this._contentEl.removeClass("switching");
        this._cachedStats = null;
        try {
          this._fetchStats(false);
        } catch (e) {
          console.log("[PF] fetchStats error:", e);
        }
        console.log("[PF] close cmd=" + a.cmd + " id=" + a.id);
        if (a.cmd === "sync")
          checkOrphanState(
            this.app,
            ((this.app as any).plugins.plugins as any)["paperforge"],
            vp
          );
      }
    });
    child.on("error", (err: Error) => {
      card.removeClass("running");
      if (this._contentEl) this._contentEl.removeClass("switching");
      this._showMessage("[!!] " + err.message, "error");
      new Notice("[!!] Cannot start: " + err.message, 8000);
    });
  }

  _showMessage(msg: string, cls: string) {
    if (this._messageEl) {
      this._messageEl.setText(msg);
      this._messageEl.className = `paperforge-message msg-${cls}`;
    }
  }

  /* ── Mode-Aware Header (D-07) ── */
  _renderModeHeader(mode: string) {
    if (!this._modeContextEl) return;
    this._modeContextEl.empty();
    const badge = this._modeContextEl.createEl("span", {
      cls: "paperforge-mode-badge",
    });
    let modeName = "";
    switch (mode) {
      case "global":
        badge.addClass("global");
        badge.setText("Global");
        if (this._headerTitle) this._headerTitle.setText("PaperForge");
        break;
      case "paper":
        badge.addClass("paper");
        badge.setText("Paper");
        if (this._headerTitle) this._headerTitle.setText("Paper");
        if (this._currentPaperEntry && this._currentPaperEntry.title) {
          modeName = this._currentPaperEntry.title;
        } else if (this._currentPaperKey) {
          modeName = this._currentPaperKey;
          this._modeContextEl.createEl("span", {
            cls: "paperforge-mode-warning",
            text: "Not found in index",
          });
        } else {
          modeName = "Unknown paper";
        }
        break;
      case "collection":
        badge.addClass("collection");
        badge.setText("Collection");
        if (this._headerTitle) this._headerTitle.setText("Collection");
        modeName = this._currentDomain || "Unknown Domain";
        break;
      case "versions":
        badge.addClass("versions");
        badge.setText(t("version_panel_title"));
        if (this._headerTitle)
          this._headerTitle.setText(t("version_panel_title"));
        break;
    }
    if (modeName) {
      this._modeContextEl.createEl("span", {
        cls: "paperforge-mode-name",
        text: modeName,
      });
    }
  }

  /* ── Event Subscriptions (D-08, D-09, D-19) ── */
  _setupEventSubscriptions() {
    const leafHandler = this.app.workspace.on("active-leaf-change", () => {
      if (this._leafChangeTimer) clearTimeout(this._leafChangeTimer);
      this._leafChangeTimer = setTimeout(() => {
        const resolved = this._resolveModeForFile(
          this.app.workspace.getActiveFile()
        );
        const nextMode = resolved.mode;
        const nextFilePath = resolved.filePath;
        if (
          this._currentMode === nextMode &&
          this._currentFilePath === nextFilePath
        ) {
          return;
        }
        this._detectAndSwitch();
      }, 300);
    });
    this._modeSubscribers.push({
      event: "active-leaf-change",
      ref: leafHandler,
    });
    const modifyHandler = this.app.vault.on("modify", (file: any) => {
      if (file && file.path && file.path.endsWith("formal-library.json")) {
        this._invalidateIndex();
        this._refreshCurrentMode();
      }
    });
    this._modeSubscribers.push({ event: "modify", ref: modifyHandler });
  }

  /* ── Static: open or reveal view ── */
  static async open(plugin: IPluginRef) {
    const leaves = plugin.app.workspace.getLeavesOfType(VIEW_TYPE_PAPERFORGE);
    if (leaves.length > 0) {
      plugin.app.workspace.revealLeaf(leaves[0]);
      return;
    }
    const leaf = plugin.app.workspace.getRightLeaf(false) as WorkspaceLeaf;
    if (leaf) {
      await leaf.setViewState({
        type: VIEW_TYPE_PAPERFORGE,
        active: true,
      } as any);
      plugin.app.workspace.revealLeaf(leaf);
    }
  }
}
