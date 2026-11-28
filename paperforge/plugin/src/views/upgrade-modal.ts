/**
 * Iceberg Non-Blocking Vault Upgrade UI & Deferred Maintenance Drawer (ADR-018).
 *
 * Design principles (aligned with DESIGN.md, ADR-016, ADR-017):
 * 1. Never lock out reading: Companion & Settings render a calm inline banner
 *    only when `provenance.needs_upgrade === true`; dismissing hides it for the
 *    session while reading, search, and PDF annotation stay unlocked.
 * 2. Iceberg Progressive Disclosure: 1-sentence safety promise + compact
 *    tabular-numeral summary + single primary CTA (`立即无损升级`), with technical
 *    change rows tucked inside a smooth 220ms chevron disclosure drawer.
 * 3. Two-Speed Cutover + Background Handoff: executes `< 3s` O(1) `fastCutover`
 *    in the modal, draws a spring completion check, and hands off progressive
 *    workspace/OCR healing to `ControlDaemon` + `.pf-global-activity-strip`.
 * 4. Deferred Storage Cleanup & Time-Machine Rollback in Settings: residual
 *    candidates are moved to `.paperforge/trash/` ONLY when explicitly selected,
 *    and 1-click rollback restores the pre-upgrade layout losslessly.
 */

import { App, Modal, Notice } from "obsidian";
import type {
  PaperForgeClient,
  VaultUpgradePlanDto,
  VaultCleanupCandidateDto,
  ZoteroDetectDto,
} from "../client";
import { t } from "../i18n";
import { formatHumanError } from "../services/feedback";
import {
  computeVeteranZoteroPreselection,
  evaluateZoteroImportScope,
  type VeteranZoteroPreselection,
} from "../services/zotero-import-scope";
import { createPfIconBtn, setPfIcon } from "./icons";
import { PaperForgeConfirmModal } from "./modals";

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export interface UpgradeZoteroContext {
  currentSourceMode: "sqlite" | "bbt";
  currentSelectedCollections: string[];
  zoteroDataDir: string;
  legacyDomainNames: string[];
  hasManualBbtExports: boolean;
  explicitSourceModeInConfig: boolean;
  onCommitZoteroConfig: (choice: {
    zoteroSourceMode: "sqlite" | "bbt";
    zoteroSelectedCollections: string[];
    zoteroDataDir?: string;
  }) => Promise<void>;
}

export interface UpgradeModalCallbacks {
  onUpgraded?: (meta?: { healSubmitted?: boolean }) => Promise<void> | void;
  onDismissForSession?: () => void;
  zoteroContext?: UpgradeZoteroContext;
}

export class PaperForgeUpgradeModal extends Modal {
  private _plan: VaultUpgradePlanDto;
  private readonly _client: PaperForgeClient;
  private readonly _callbacks: UpgradeModalCallbacks;
  private _expanded = false;
  private _busy = false;
  private _zoteroMode: "sqlite" | "bbt";
  private _zoteroSelected: string[];
  private _zoteroDetectData: ZoteroDetectDto | null = null;
  private _zoteroDetectLoading = false;
  private _zoteroPreselection: VeteranZoteroPreselection | null = null;
  private _zoteroSectionEl: HTMLElement | null = null;
  private _statusSlotEl: HTMLElement | null = null;
  private _closed = false;

  constructor(
    app: App,
    client: PaperForgeClient,
    plan: VaultUpgradePlanDto,
    callbacks: UpgradeModalCallbacks = {}
  ) {
    super(app);
    this._client = client;
    this._plan = plan;
    this._callbacks = callbacks;
    const zctx = callbacks.zoteroContext;
    this._zoteroMode =
      zctx &&
      zctx.explicitSourceModeInConfig &&
      zctx.currentSourceMode === "bbt"
        ? "bbt"
        : "sqlite";
    this._zoteroSelected = Array.isArray(zctx?.currentSelectedCollections)
      ? [...zctx.currentSelectedCollections]
      : [];
  }

  onOpen(): void {
    this._closed = false;
    this._render();
    if (this._callbacks.zoteroContext) {
      void this._loadZoteroCollections();
    }
  }

  onClose(): void {
    this._closed = true;
    this._zoteroSectionEl = null;
    this._statusSlotEl = null;
    this.contentEl.empty();
  }

  private async _loadZoteroCollections(): Promise<void> {
    const zctx = this._callbacks.zoteroContext;
    if (!zctx || typeof this._client?.zoteroDetect !== "function") return;
    this._zoteroDetectLoading = true;
    this._renderZoteroSection();
    try {
      const detected = await this._client.zoteroDetect(
        zctx.zoteroDataDir || undefined
      );
      if (this._closed) return;
      this._zoteroDetectData = detected;
      if (detected.found && Array.isArray(detected.collections)) {
        const pre = computeVeteranZoteroPreselection({
          collections: detected.collections,
          existingSelected: this._zoteroSelected,
          legacyDomainNames: zctx.legacyDomainNames,
        });
        this._zoteroPreselection = pre;
        this._zoteroSelected = [...pre.selectedKeys];
      }
    } catch {
      // Leave Zotero library optional if local DB probe is unavailable
    } finally {
      this._zoteroDetectLoading = false;
      if (!this._closed) {
        this._renderZoteroSection();
      }
    }
  }

  private _blockingIssues(): Array<{
    id: string;
    title: string;
    detail: string;
    remediation?: string;
  }> {
    const blockingIds = new Set(["config.corrupt_json", "db.file_locked"]);
    return (this._plan.category_c_tamper ?? []).filter((it) =>
      blockingIds.has(it.id)
    );
  }

  private _render(): void {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("pf-upgrade-modal");

    // ── Header ──
    const head = contentEl.createDiv({ cls: "pf-upgrade-modal-head" });
    const iconBadge = head.createDiv({ cls: "pf-upgrade-modal-badge" });
    setPfIcon(iconBadge, "layers", 18);
    const titleWrap = head.createDiv({ cls: "pf-upgrade-modal-title-wrap" });
    titleWrap.createEl("h2", {
      cls: "pf-upgrade-modal-title",
      text: t("upgrade_modal_title"),
    });
    titleWrap.createEl("p", {
      cls: "pf-upgrade-modal-promise",
      text: t("upgrade_modal_promise"),
    });

    // ── Compact Metric Strip (.pf-tnum) ──
    const census = (this._plan.census ?? {}) as Record<
      string,
      Record<string, number>
    >;
    const wsCount = Number(census?.pf_canonical?.workspaces ?? 0);
    const salvageCount =
      Number(this._plan.summary?.ocr_atoms?.backfill_from_result_json ?? 0) +
      Number(this._plan.summary?.ocr_atoms?.rebuild_derived_local ?? 0);
    const autoCount = Number(this._plan.summary?.auto_count ?? 0);

    const metrics = contentEl.createDiv({
      cls: "pf-upgrade-metrics",
      attr: { "data-pf-testid": "upgrade-metrics" },
    });
    const addMetric = (label: string, val: string) => {
      const cell = metrics.createDiv({ cls: "pf-upgrade-metric-cell" });
      cell.createEl("span", {
        cls: "pf-upgrade-metric-val pf-tnum",
        text: val,
      });
      cell.createEl("span", { cls: "pf-upgrade-metric-label", text: label });
    };
    addMetric(t("upgrade_metric_workspaces"), String(wsCount));
    addMetric(t("upgrade_metric_auto"), String(autoCount));
    addMetric(t("upgrade_metric_salvage"), String(salvageCount));

    // ── Optional Single-Question Blocker Card (only if file locked / corrupt JSON) ──
    const blockers = this._blockingIssues();
    let blockerCardEl: HTMLElement | null = null;
    if (blockers.length > 0) {
      const b = blockers[0];
      blockerCardEl = contentEl.createDiv({
        cls: "pf-upgrade-blocker-card",
        attr: { role: "alert", "data-pf-testid": "upgrade-blocker-card" },
      });
      const bHead = blockerCardEl.createDiv({ cls: "pf-upgrade-blocker-head" });
      const bIcon = bHead.createSpan({ cls: "pf-upgrade-blocker-icon" });
      setPfIcon(bIcon, "alert-triangle", 15);
      bHead.createSpan({ cls: "pf-upgrade-blocker-title", text: b.title });
      blockerCardEl.createEl("p", {
        cls: "pf-upgrade-blocker-detail",
        text: b.remediation || b.detail,
      });
      const bActions = blockerCardEl.createDiv({
        cls: "pf-upgrade-blocker-actions",
      });
      const retryBtn = bActions.createEl("button", {
        cls: "pf-action-btn",
        type: "button",
        text: t("upgrade_recheck_btn"),
        attr: { "data-pf-testid": "upgrade-recheck-btn" },
      });
      retryBtn.addEventListener("click", () => {
        void (async () => {
          const refreshed = await this._client.vaultUpgradePlan();
          this._plan = refreshed;
          this._render();
          if (this._blockingIssues().length > 0) {
            const card = this.contentEl.querySelector(
              '[data-pf-testid="upgrade-blocker-card"]'
            );
            card?.classList.remove("pf-nudge");
            card?.classList.add("pf-nudge");
          }
        })();
      });
    }

    // ── Iceberg Progressive Disclosure ──
    if (this._plan.category_a_auto.length > 0) {
      const discWrap = contentEl.createDiv({ cls: "pf-upgrade-disclosure" });
      const toggleBtn = discWrap.createEl("button", {
        cls: "pf-upgrade-disclosure-btn",
        type: "button",
        attr: {
          "aria-expanded": this._expanded ? "true" : "false",
          "data-pf-testid": "upgrade-disclosure-toggle",
        },
      });
      const chev = toggleBtn.createSpan({
        cls: this._expanded
          ? "pf-upgrade-chevron is-expanded"
          : "pf-upgrade-chevron",
      });
      setPfIcon(chev, "chevron-right", 14);
      toggleBtn.createSpan({
        text: t("upgrade_disclosure_summary").replace(
          "{count}",
          String(this._plan.category_a_auto.length)
        ),
      });

      const drawer = discWrap.createDiv({
        cls: this._expanded
          ? "pf-upgrade-drawer is-expanded"
          : "pf-upgrade-drawer",
        attr: { "data-pf-testid": "upgrade-disclosure-drawer" },
      });
      const drawerInner = drawer.createDiv({ cls: "pf-upgrade-drawer-inner" });
      this._plan.category_a_auto.forEach((item, idx) => {
        const row = drawerInner.createDiv({ cls: "pf-upgrade-item-row" });
        row.style.animationDelay = `${Math.min(idx * 28, 140)}ms`;
        const rowHead = row.createDiv({ cls: "pf-upgrade-item-head" });
        const dot = rowHead.createSpan({ cls: "pf-upgrade-item-check" });
        setPfIcon(dot, "check", 13);
        const itemTitle =
          item.id === "storage.move_to_dot_paperforge"
            ? t("upgrade_item_move_title").replace(
                "{dir}",
                String(
                  (item as { legacy_dir?: string }).legacy_dir ||
                    this._plan.provenance?.legacy_engine_dir ||
                    "System/PaperForge"
                )
              )
            : item.title;
        const itemDetail =
          item.id === "storage.move_to_dot_paperforge"
            ? t("upgrade_item_move_detail")
            : item.detail;
        rowHead.createSpan({ cls: "pf-upgrade-item-title", text: itemTitle });
        rowHead.createSpan({
          cls: "pf-upgrade-item-tag",
          text: item.fast_cutover ? t("upgrade_tag_fast") : t("upgrade_tag_bg"),
        });
        row.createEl("div", {
          cls: "pf-upgrade-item-detail",
          text: itemDetail,
        });
      });

      toggleBtn.addEventListener("click", () => {
        this._expanded = !this._expanded;
        toggleBtn.setAttribute(
          "aria-expanded",
          this._expanded ? "true" : "false"
        );
        chev.classList.toggle("is-expanded", this._expanded);
        drawer.classList.toggle("is-expanded", this._expanded);
      });
    }

    // ── Non-blocking Category-B Follow-up Items (e.g., .env migration, Chroma rebuild, Skill Hub) ──
    const followups = this._plan.category_b_reconfig ?? [];
    if (followups.length > 0) {
      const fuWrap = contentEl.createDiv({
        cls: "pf-upgrade-followup",
        attr: { "data-pf-testid": "upgrade-followup-list" },
      });
      fuWrap.createDiv({
        cls: "pf-upgrade-followup-heading",
        text: t("upgrade_followup_heading").replace(
          "{count}",
          String(followups.length)
        ),
      });
      for (const item of followups) {
        const row = fuWrap.createDiv({ cls: "pf-upgrade-followup-row" });
        const rowHead = row.createDiv({ cls: "pf-upgrade-item-head" });
        rowHead.createSpan({
          cls: "pf-upgrade-item-title",
          text: item.title,
        });
        rowHead.createSpan({
          cls:
            item.impact === "experience_critical"
              ? "pf-upgrade-item-tag is-critical"
              : "pf-upgrade-item-tag",
          text:
            item.impact === "experience_critical"
              ? t("upgrade_tag_critical")
              : t("upgrade_tag_minor"),
        });
        const detailText = item.remediation
          ? `${item.detail} ${item.remediation}`
          : item.detail;
        if (detailText) {
          row.createDiv({
            cls: "pf-upgrade-followup-detail",
            text: detailText,
          });
        }
      }
    }

    // ── Veteran Zotero Source Mode & Folder Scope Confirmation ──
    if (this._callbacks.zoteroContext) {
      this._zoteroSectionEl = contentEl.createDiv({
        cls: "pf-upgrade-zotero-section",
        attr: { "data-pf-testid": "upgrade-zotero-section" },
      });
      this._renderZoteroSection();
    } else {
      this._zoteroSectionEl = null;
    }

    // ── Status Feedback Slot ──
    const statusSlot = contentEl.createDiv({
      cls: "pf-upgrade-status-slot",
      attr: { "aria-live": "polite", "data-pf-testid": "upgrade-status-slot" },
    });
    this._statusSlotEl = statusSlot;

    // ── Footer Actions (Single Primary CTA discipline) ──
    const footer = contentEl.createDiv({ cls: "pf-upgrade-modal-footer" });
    const deferBtn = footer.createEl("button", {
      cls: "pf-action-btn",
      type: "button",
      text: t("upgrade_btn_defer"),
      attr: { "data-pf-testid": "upgrade-defer-btn" },
    });
    deferBtn.addEventListener("click", () => {
      if (this._busy) return;
      this._callbacks.onDismissForSession?.();
      this.close();
    });

    const applyBtn = footer.createEl("button", {
      cls: "paperforge-contextual-btn primary pf-upgrade-primary-btn",
      type: "button",
      text: t("upgrade_btn_apply"),
      attr: { "data-pf-testid": "upgrade-apply-btn" },
    });
    applyBtn.addEventListener("click", () => {
      if (this._busy) return;
      if (this._blockingIssues().length > 0) {
        blockerCardEl?.classList.remove("pf-nudge");
        // Force reflow when re-triggering shake
        void blockerCardEl?.offsetWidth;
        blockerCardEl?.classList.add("pf-nudge");
        return;
      }
      void this._executeFastCutover(applyBtn, deferBtn, statusSlot);
    });
  }

  private _renderZoteroSection(): void {
    const el = this._zoteroSectionEl;
    const zctx = this._callbacks.zoteroContext;
    if (!el || !zctx) return;
    el.empty();

    el.createDiv({
      cls: "pf-upgrade-zotero-heading",
      text: t("upgrade_zotero_heading"),
    });

    if (zctx.hasManualBbtExports || zctx.currentSourceMode === "bbt") {
      el.createEl("p", {
        cls: "pf-upgrade-zotero-desc",
        text: t("upgrade_zotero_bbt_hint"),
      });
    }

    const modesEl = el.createDiv({ cls: "pf-upgrade-zotero-modes" });
    const addModeCard = (
      mode: "sqlite" | "bbt",
      title: string,
      desc: string,
      testid: string
    ) => {
      const card = modesEl.createEl("label", {
        cls:
          this._zoteroMode === mode
            ? "pf-upgrade-zotero-mode-card is-selected"
            : "pf-upgrade-zotero-mode-card",
      });
      const radio = card.createEl("input", {
        type: "radio",
        attr: {
          name: "pf-upgrade-zotero-mode",
          value: mode,
          "data-pf-testid": testid,
        },
      }) as HTMLInputElement;
      radio.checked = this._zoteroMode === mode;
      radio.addEventListener("change", () => {
        if (!radio.checked || this._busy) return;
        this._zoteroMode = mode;
        this._statusSlotEl?.empty();
        this._renderZoteroSection();
      });
      const copy = card.createDiv({ cls: "pf-upgrade-zotero-mode-copy" });
      copy.createSpan({ cls: "pf-upgrade-zotero-mode-title", text: title });
      copy.createSpan({ cls: "pf-upgrade-zotero-mode-sub", text: desc });
    };

    addModeCard(
      "sqlite",
      t("upgrade_zotero_sqlite_title"),
      t("upgrade_zotero_sqlite_desc"),
      "upgrade-zotero-mode-sqlite"
    );
    addModeCard(
      "bbt",
      t("upgrade_zotero_bbt_title"),
      t("upgrade_zotero_bbt_desc"),
      "upgrade-zotero-mode-bbt"
    );

    if (this._zoteroMode === "bbt") {
      el.createDiv({
        cls: "pf-upgrade-zotero-hint",
        text: t("upgrade_zotero_bbt_active_hint"),
      });
      return;
    }

    if (this._zoteroDetectLoading) {
      el.createDiv({
        cls: "pf-upgrade-zotero-hint",
        text: t("upgrade_zotero_detecting"),
      });
      return;
    }

    const detected = this._zoteroDetectData;
    const cols = Array.isArray(detected?.collections)
      ? detected.collections
      : [];
    if (!detected?.found || cols.length === 0) {
      if (detected !== null) {
        el.createDiv({
          cls: "pf-upgrade-zotero-hint",
          text: t("upgrade_zotero_not_found_hint"),
        });
      }
      return;
    }

    const topCols = cols.filter((c) => c.top_level !== false);
    const displayCols = topCols.length > 0 ? topCols : cols;
    const scopeEval = evaluateZoteroImportScope({
      totalPapers: detected.total_papers,
      collections: cols,
      selected: this._zoteroSelected,
    });

    if (
      this._zoteroPreselection?.mode === "matched_legacy" &&
      !scopeEval.requiresFolderChoice
    ) {
      el.createDiv({
        cls: "pf-upgrade-zotero-hint is-ok",
        text: t("upgrade_zotero_matched_hint").replace(
          "{names}",
          this._zoteroPreselection.matchedNames.join("、")
        ),
      });
    } else if (scopeEval.requiresFolderChoice) {
      el.createDiv({
        cls: "pf-upgrade-zotero-hint is-warn",
        text: t("upgrade_zotero_pick_hint"),
      });
    }

    const toolbar = el.createDiv({ cls: "pf-upgrade-zotero-toolbar" });
    const summaryText = scopeEval.explicitAll
      ? t("upgrade_zotero_scope_all").replace(
          "{count}",
          String(scopeEval.estimatedPapers)
        )
      : scopeEval.selectedKeys.length > 0
        ? t("upgrade_zotero_scope_cols")
            .replace("{folders}", String(scopeEval.selectedKeys.length))
            .replace("{count}", String(scopeEval.estimatedPapers))
        : t("upgrade_zotero_scope_pick");
    toolbar.createSpan({
      cls: scopeEval.requiresFolderChoice
        ? "pf-upgrade-zotero-hint is-warn"
        : "pf-upgrade-zotero-hint is-ok",
      text: summaryText,
    });

    const btns = toolbar.createDiv({ cls: "pf-upgrade-zotero-toolbar-btns" });
    const selectAllBtn = btns.createEl("button", {
      cls: "pf-action-btn pf-upgrade-zotero-mini-btn",
      type: "button",
      text: t("upgrade_zotero_select_all"),
      attr: { "data-pf-testid": "upgrade-zotero-select-all" },
    });
    selectAllBtn.addEventListener("click", () => {
      if (this._busy) return;
      this._zoteroSelected = displayCols.map((c) => c.key);
      this._statusSlotEl?.empty();
      this._renderZoteroSection();
    });
    const clearBtn = btns.createEl("button", {
      cls: "pf-action-btn pf-upgrade-zotero-mini-btn",
      type: "button",
      text: t("upgrade_zotero_clear"),
      attr: { "data-pf-testid": "upgrade-zotero-clear" },
    });
    clearBtn.addEventListener("click", () => {
      if (this._busy) return;
      this._zoteroSelected = [];
      this._statusSlotEl?.empty();
      this._renderZoteroSection();
    });

    const listEl = el.createDiv({ cls: "pf-upgrade-zotero-list" });
    const pickedSet = new Set(scopeEval.selectedKeys);
    for (const col of displayCols) {
      const row = listEl.createEl("label", {
        cls: "pf-upgrade-zotero-col-row",
      });
      const cb = row.createEl("input", {
        type: "checkbox",
        attr: { "data-pf-testid": `upgrade-zotero-col-${col.key}` },
      }) as HTMLInputElement;
      cb.checked = pickedSet.has(col.key);
      cb.disabled = scopeEval.explicitAll;
      cb.addEventListener("change", () => {
        if (this._busy) return;
        const cur = new Set(this._zoteroSelected.filter((k) => k !== "*"));
        if (cb.checked) cur.add(col.key);
        else cur.delete(col.key);
        this._zoteroSelected = Array.from(cur);
        this._statusSlotEl?.empty();
        this._renderZoteroSection();
      });
      row.createSpan({ text: col.name });
      if (typeof col.item_count === "number") {
        row.createSpan({
          cls: "pf-upgrade-zotero-col-count",
          text: String(col.item_count),
        });
      }
    }

    const allRow = el.createEl("label", { cls: "pf-upgrade-zotero-all-row" });
    const allCb = allRow.createEl("input", {
      type: "checkbox",
      attr: { "data-pf-testid": "upgrade-zotero-all" },
    }) as HTMLInputElement;
    allCb.checked = scopeEval.explicitAll;
    allCb.addEventListener("change", () => {
      if (this._busy) return;
      this._zoteroSelected = allCb.checked ? ["*"] : [];
      this._statusSlotEl?.empty();
      this._renderZoteroSection();
    });
    allRow.createSpan({
      text: t("upgrade_zotero_all_label").replace(
        "{count}",
        String(detected.total_papers)
      ),
    });
  }

  private async _executeFastCutover(
    applyBtn: HTMLButtonElement,
    deferBtn: HTMLButtonElement,
    statusSlot: HTMLElement
  ): Promise<void> {
    const zctx = this._callbacks.zoteroContext;
    if (
      zctx &&
      this._zoteroMode === "sqlite" &&
      this._zoteroDetectData?.found &&
      Array.isArray(this._zoteroDetectData.collections) &&
      this._zoteroDetectData.collections.length > 0
    ) {
      const scopeCheck = evaluateZoteroImportScope({
        totalPapers: this._zoteroDetectData.total_papers,
        collections: this._zoteroDetectData.collections,
        selected: this._zoteroSelected,
      });
      if (scopeCheck.requiresFolderChoice) {
        statusSlot.empty();
        statusSlot.createDiv({
          cls: "pf-upgrade-error-msg",
          attr: { "data-pf-testid": "upgrade-zotero-guard-msg" },
          text: t("upgrade_zotero_pick_required"),
        });
        return;
      }
    }

    this._busy = true;
    applyBtn.disabled = true;
    deferBtn.disabled = true;
    applyBtn.setText(t("upgrade_btn_applying"));
    statusSlot.empty();
    statusSlot.createSpan({
      cls: "pf-upgrade-running-hint",
      text: t("upgrade_status_applying"),
    });

    try {
      const applyOpts: {
        fastCutover: true;
        zoteroSourceMode?: "sqlite" | "bbt";
        zoteroSelectedCollections?: string[];
        zoteroDataDir?: string;
      } = { fastCutover: true };
      if (zctx) {
        applyOpts.zoteroSourceMode = this._zoteroMode;
        applyOpts.zoteroSelectedCollections =
          this._zoteroMode === "sqlite" ? [...this._zoteroSelected] : [];
        const zDir = (
          this._zoteroDetectData?.zotero_dir ||
          zctx.zoteroDataDir ||
          ""
        ).trim();
        if (zDir) {
          applyOpts.zoteroDataDir = zDir;
        }
      }
      const res = await this._client.vaultUpgradeApply(applyOpts);
      if (!res.applied || (res.errors && res.errors.length > 0)) {
        const msg =
          res.errors?.map((e) => formatHumanError(e.error)).join("; ") ||
          t("upgrade_err_incomplete");
        statusSlot.empty();
        statusSlot.createDiv({
          cls: "pf-upgrade-error-msg",
          text: msg,
        });
        applyBtn.disabled = false;
        deferBtn.disabled = false;
        applyBtn.setText(t("upgrade_btn_retry"));
        this._busy = false;
        return;
      }

      if (zctx?.onCommitZoteroConfig) {
        await zctx.onCommitZoteroConfig({
          zoteroSourceMode: this._zoteroMode,
          zoteroSelectedCollections:
            this._zoteroMode === "sqlite" ? [...this._zoteroSelected] : [],
          zoteroDataDir:
            this._zoteroDetectData?.zotero_dir || zctx.zoteroDataDir,
        });
      }

      // Hand off progressive workspace normalization & zero-cost OCR salvage to ControlDaemon
      const sub = await this._client
        .daemonSubmitJob("upgrade.heal", { backfillOcr: true })
        .catch(() => ({ accepted: false }));
      if (!sub.accepted) {
        void this._client
          .vaultUpgradeHeal({ backfillOcr: true })
          .catch(() => undefined);
      }

      statusSlot.empty();
      const doneRow = statusSlot.createDiv({
        cls: "pf-upgrade-done-row",
        attr: { "data-pf-testid": "upgrade-done-row" },
      });
      const checkBadge = doneRow.createSpan({ cls: "pf-upgrade-done-icon" });
      setPfIcon(checkBadge, "check", 15);
      doneRow.createSpan({
        text: t("upgrade_status_done"),
      });

      await this._callbacks.onUpgraded?.({
        healSubmitted: Boolean(sub.accepted),
      });
      new Notice(t("upgrade_notice_done"));
      this.close();
    } catch (err: unknown) {
      statusSlot.empty();
      statusSlot.createDiv({
        cls: "pf-upgrade-error-msg",
        text: formatHumanError(err, "upgrade_err_incomplete"),
      });
      applyBtn.disabled = false;
      deferBtn.disabled = false;
      applyBtn.setText(t("upgrade_btn_retry"));
      this._busy = false;
    }
  }
}

/**
 * Render a calm, non-blocking inline upgrade banner when `plan.provenance.needs_upgrade` is true.
 * Returns true if rendered, false if hidden (`fresh_or_foreign` / `standard_current` / dismissed).
 */
export function renderUpgradeAvailableBanner(
  hostEl: HTMLElement,
  plan: VaultUpgradePlanDto | null | undefined,
  opts: {
    dismissed?: boolean;
    onOpenModal: () => void;
    onDismiss: () => void;
  }
): boolean {
  if (!plan || !plan.provenance?.needs_upgrade || opts.dismissed) {
    return false;
  }
  const banner = hostEl.createDiv({
    cls: "pf-upgrade-banner",
    attr: { "data-pf-testid": "vault-upgrade-banner" },
  });
  const left = banner.createDiv({ cls: "pf-upgrade-banner-main" });
  const iconSpan = left.createSpan({ cls: "pf-upgrade-banner-icon" });
  setPfIcon(iconSpan, "layers", 15);
  const copy = left.createDiv({ cls: "pf-upgrade-banner-copy" });
  copy.createEl("div", {
    cls: "pf-upgrade-banner-title",
    text: t("upgrade_banner_title"),
  });
  copy.createEl("div", {
    cls: "pf-upgrade-banner-desc",
    text: t("upgrade_banner_desc"),
  });

  const actions = banner.createDiv({ cls: "pf-upgrade-banner-actions" });
  const openBtn = actions.createEl("button", {
    cls: "pf-action-btn pf-upgrade-banner-btn",
    type: "button",
    text: t("upgrade_banner_open"),
    attr: { "data-pf-testid": "vault-upgrade-banner-open" },
  });
  openBtn.addEventListener("click", opts.onOpenModal);

  const dismissBtn = createPfIconBtn(actions, {
    icon: "x",
    label: t("upgrade_banner_dismiss"),
    size: 13,
    cls: "pf-upgrade-banner-dismiss",
    testid: "vault-upgrade-banner-dismiss",
  });
  dismissBtn.addEventListener("click", opts.onDismiss);
  return true;
}

/**
 * Deferred Post-Upgrade Storage Cleanup & Time-Machine Rollback section for Settings.
 */
export function renderStorageMigrationMaintenanceSection(
  containerEl: HTMLElement,
  app: App,
  client: PaperForgeClient,
  plan: VaultUpgradePlanDto | null,
  onUpdated: () => void
): void {
  if (!plan) return;
  const hasCandidates = (plan.cleanup_candidates?.length ?? 0) > 0;
  const canRollback = plan.rollback_available === true;
  const needsUpgrade = plan.provenance?.needs_upgrade === true;
  if (!hasCandidates && !canRollback && !needsUpgrade) return;

  const section = containerEl.createDiv({
    cls: "pf-upgrade-maint-section",
    attr: { "data-pf-testid": "storage-migration-maintenance" },
  });
  section.createEl("h3", {
    cls: "pf-upgrade-maint-heading",
    text: t("upgrade_maint_heading"),
  });
  section.createEl("p", {
    cls: "setting-item-description",
    text: t("upgrade_maint_desc"),
  });

  if (hasCandidates) {
    const selected = new Set<string>(
      plan.cleanup_candidates.map((c: VaultCleanupCandidateDto) => c.id)
    );
    const listEl = section.createDiv({ cls: "pf-upgrade-cleanup-list" });
    for (const cand of plan.cleanup_candidates) {
      const row = listEl.createEl("label", { cls: "pf-upgrade-cleanup-row" });
      const cb = row.createEl("input", {
        type: "checkbox",
        attr: { "data-pf-testid": `cleanup-check-${cand.id}` },
      }) as HTMLInputElement;
      cb.checked = true;
      cb.addEventListener("change", () => {
        if (cb.checked) selected.add(cand.id);
        else selected.delete(cand.id);
      });
      const info = row.createDiv({ cls: "pf-upgrade-cleanup-info" });
      info.createEl("span", {
        cls: "pf-upgrade-cleanup-reason",
        text: cand.reason,
      });
      info.createEl("span", {
        cls: "pf-upgrade-cleanup-path",
        text: cand.path,
      });
      row.createEl("span", {
        cls: "pf-upgrade-cleanup-size pf-tnum",
        text: formatBytes(cand.bytes),
      });
    }

    const quarantineBtn = section.createEl("button", {
      cls: "pf-action-btn",
      type: "button",
      text: t("upgrade_maint_quarantine_btn"),
      attr: { "data-pf-testid": "cleanup-quarantine-btn" },
    });
    const statusMsg = section.createDiv({
      cls: "pf-upgrade-maint-status",
      attr: { "aria-live": "polite", "data-pf-testid": "cleanup-status-msg" },
    });
    quarantineBtn.addEventListener("click", () => {
      const ids = [...selected];
      if (!ids.length) return;
      void (async () => {
        quarantineBtn.disabled = true;
        statusMsg.empty();
        try {
          const res = await client.vaultUpgradeApply({
            fastCutover: true,
            quarantineIds: ids,
            noRebuildDb: true,
          });
          const errs = Array.isArray(res?.errors) ? res.errors : [];
          const qStep = Array.isArray(res?.executed_steps)
            ? res.executed_steps.find(
                (s) => s && s.step === "quarantine_residuals"
              )
            : undefined;
          const quarantinedCount =
            typeof qStep?.quarantined === "number"
              ? qStep.quarantined
              : res?.applied && errs.length === 0
                ? ids.length
                : 0;

          if (!res || res.applied === false) {
            const firstErr = errs[0]?.error
              ? formatHumanError(errs[0].error)
              : t("upgrade_maint_err_unapplied");
            const msg = t("upgrade_maint_notice_failed").replace(
              "{detail}",
              firstErr
            );
            statusMsg.setText(msg);
            new Notice(msg, 8000);
            quarantineBtn.disabled = false;
            return;
          }
          if (errs.length > 0) {
            const firstErr = errs[0]?.error
              ? formatHumanError(errs[0].error)
              : t("upgrade_maint_err_partial_item");
            const msg = t("upgrade_maint_notice_partial")
              .replace("{moved}", String(quarantinedCount))
              .replace("{failed}", String(errs.length))
              .replace("{detail}", firstErr);
            statusMsg.setText(msg);
            new Notice(msg, 8000);
            quarantineBtn.disabled = false;
            onUpdated();
            return;
          }
          new Notice(
            t("upgrade_maint_notice_done").replace(
              "{count}",
              String(quarantinedCount)
            )
          );
          onUpdated();
        } catch (err: unknown) {
          const msg = t("upgrade_maint_notice_failed").replace(
            "{detail}",
            formatHumanError(err)
          );
          statusMsg.setText(msg);
          new Notice(msg, 8000);
          quarantineBtn.disabled = false;
        }
      })();
    });
  }

  if (canRollback) {
    const rbRow = section.createDiv({ cls: "pf-upgrade-rollback-row" });
    rbRow.createEl("span", {
      cls: "pf-upgrade-rollback-hint",
      text: t("upgrade_maint_rollback_hint"),
    });
    const rbBtn = rbRow.createEl("button", {
      cls: "pf-action-btn",
      type: "button",
      text: t("upgrade_maint_rollback_btn"),
      attr: { "data-pf-testid": "vault-upgrade-rollback-btn" },
    });
    rbBtn.addEventListener("click", () => {
      new PaperForgeConfirmModal(
        app,
        {
          title: t("upgrade_maint_rollback_btn"),
          effectLabel: t("upgrade_maint_rollback_body"),
          confirmLabel: t("upgrade_maint_rollback_confirm"),
          cancelLabel: t("maintenance_confirm_cancel"),
        },
        () => {
          void (async () => {
            rbBtn.disabled = true;
            try {
              const res = await client.vaultUpgradeRollback();
              if (res.rolled_back) {
                new Notice(t("upgrade_maint_rollback_done"));
                onUpdated();
              } else {
                new Notice(
                  t("upgrade_maint_rollback_unable").replace(
                    "{detail}",
                    res.reason ?? t("upgrade_maint_rollback_missing")
                  ),
                  8000
                );
                rbBtn.disabled = false;
              }
            } catch (err: unknown) {
              new Notice(
                t("upgrade_maint_rollback_failed").replace(
                  "{detail}",
                  formatHumanError(err)
                ),
                8000
              );
              rbBtn.disabled = false;
            }
          })();
        }
      ).open();
    });
  }
}
