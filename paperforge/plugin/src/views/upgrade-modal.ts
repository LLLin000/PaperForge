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
} from "../client";
import { createPfIconBtn, setPfIcon } from "./icons";
import { PaperForgeConfirmModal } from "./modals";

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export interface UpgradeModalCallbacks {
  onUpgraded?: () => Promise<void> | void;
  onDismissForSession?: () => void;
}

export class PaperForgeUpgradeModal extends Modal {
  private _plan: VaultUpgradePlanDto;
  private readonly _client: PaperForgeClient;
  private readonly _callbacks: UpgradeModalCallbacks;
  private _expanded = false;
  private _busy = false;

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
  }

  onOpen(): void {
    this._render();
  }

  onClose(): void {
    this.contentEl.empty();
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
      text: "升级至新一代文献库引擎",
    });
    titleWrap.createEl("p", {
      cls: "pf-upgrade-modal-promise",
      text: "全部个人笔记、双链、PDF 批注与 Zotero 原库保持原位不动；底层索引与缓存将在数秒内安全收拢至隐藏目录 .paperforge/，并支持随时一键还原。",
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
    addMetric("受保护文献工作区", String(wsCount));
    addMetric("可自动归拢优化项", String(autoCount));
    addMetric("零成本离线恢复全文", String(salvageCount));

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
        text: "重新检测状态",
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

    // ── Iceberg Progressive Disclosure (`查看变更摘要`) ──
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
        text: `查看变更摘要（${this._plan.category_a_auto.length} 项）`,
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
        rowHead.createSpan({ cls: "pf-upgrade-item-title", text: item.title });
        rowHead.createSpan({
          cls: "pf-upgrade-item-tag",
          text: item.fast_cutover ? "即时切流" : "后台静默整理",
        });
        row.createEl("div", {
          cls: "pf-upgrade-item-detail",
          text: item.detail,
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

    // ── Status Feedback Slot ──
    const statusSlot = contentEl.createDiv({
      cls: "pf-upgrade-status-slot",
      attr: { "aria-live": "polite", "data-pf-testid": "upgrade-status-slot" },
    });

    // ── Footer Actions (Single Primary CTA discipline) ──
    const footer = contentEl.createDiv({ cls: "pf-upgrade-modal-footer" });
    const deferBtn = footer.createEl("button", {
      cls: "pf-action-btn",
      type: "button",
      text: "稍后提醒",
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
      text: "立即无损升级",
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

  private async _executeFastCutover(
    applyBtn: HTMLButtonElement,
    deferBtn: HTMLButtonElement,
    statusSlot: HTMLElement
  ): Promise<void> {
    this._busy = true;
    applyBtn.disabled = true;
    deferBtn.disabled = true;
    applyBtn.setText("正在执行原子切流…");
    statusSlot.empty();
    statusSlot.createSpan({
      cls: "pf-upgrade-running-hint",
      text: "正在备份配置并归拢底层目录至 .paperforge/…",
    });

    try {
      const res = await this._client.vaultUpgradeApply({ fastCutover: true });
      if (!res.applied || (res.errors && res.errors.length > 0)) {
        const msg =
          res.errors?.map((e) => e.error).join("; ") || "升级切流未完成";
        statusSlot.empty();
        statusSlot.createDiv({
          cls: "pf-upgrade-error-msg",
          text: msg,
        });
        applyBtn.disabled = false;
        deferBtn.disabled = false;
        applyBtn.setText("重试升级");
        this._busy = false;
        return;
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
        text: "核心目录已完成切流，剩余文献整理已在后台静默接管。",
      });

      await this._callbacks.onUpgraded?.();
      new Notice("PaperForge: 文献库已完成无损切流，后台正在静默整理细节。");
      this.close();
    } catch (err: unknown) {
      statusSlot.empty();
      statusSlot.createDiv({
        cls: "pf-upgrade-error-msg",
        text: err instanceof Error ? err.message : String(err),
      });
      applyBtn.disabled = false;
      deferBtn.disabled = false;
      applyBtn.setText("重试升级");
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
    text: "检测到旧版 PaperForge 目录布局，可一键无损升级",
  });
  copy.createEl("div", {
    cls: "pf-upgrade-banner-desc",
    text: "升级不影响当前阅读、个人笔记与双链引用，约 3 秒完成切流。",
  });

  const actions = banner.createDiv({ cls: "pf-upgrade-banner-actions" });
  const openBtn = actions.createEl("button", {
    cls: "pf-action-btn pf-upgrade-banner-btn",
    type: "button",
    text: "查看并升级",
    attr: { "data-pf-testid": "vault-upgrade-banner-open" },
  });
  openBtn.addEventListener("click", opts.onOpenModal);

  const dismissBtn = createPfIconBtn(actions, {
    icon: "x",
    label: "本次会话暂不提示",
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
    text: "存储与迁移维护",
  });
  section.createEl("p", {
    cls: "setting-item-description",
    text: "管理升级后的历史残余文件（仅移入 .paperforge/trash 安全回收站，绝不直接物理删除）或还原升级前的目录布局。",
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
      text: "将勾选项移入安全回收站",
      attr: { "data-pf-testid": "cleanup-quarantine-btn" },
    });
    quarantineBtn.addEventListener("click", () => {
      const ids = [...selected];
      if (!ids.length) return;
      void (async () => {
        quarantineBtn.disabled = true;
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
            const firstErr = errs[0]?.error || "未能应用清理操作";
            new Notice(`清理未完成: ${firstErr}`, 8000);
            quarantineBtn.disabled = false;
            return;
          }
          if (errs.length > 0) {
            const firstErr = errs[0]?.error || "部分项目移入失败";
            new Notice(
              `部分残余清理未完成：已移入 ${quarantinedCount} 项，失败 ${errs.length} 项（${firstErr}），失败项已保留可重试。`,
              8000
            );
            quarantineBtn.disabled = false;
            onUpdated();
            return;
          }
          new Notice(
            `已将 ${quarantinedCount} 项历史残余安全移入 .paperforge/trash/`
          );
          onUpdated();
        } catch (err: unknown) {
          new Notice(
            `清理未完成: ${err instanceof Error ? err.message : String(err)}`,
            8000
          );
          quarantineBtn.disabled = false;
        }
      })();
    });
  }

  if (canRollback) {
    const rbRow = section.createDiv({ cls: "pf-upgrade-rollback-row" });
    rbRow.createEl("span", {
      cls: "pf-upgrade-rollback-hint",
      text: "如需切回升级前的旧目录结构，可使用升级快照无损还原：",
    });
    const rbBtn = rbRow.createEl("button", {
      cls: "pf-action-btn",
      type: "button",
      text: "还原至升级前目录结构",
      attr: { "data-pf-testid": "vault-upgrade-rollback-btn" },
    });
    rbBtn.addEventListener("click", () => {
      new PaperForgeConfirmModal(
        app,
        {
          title: "还原至升级前目录结构",
          effectLabel:
            "将从 .paperforge/backups/ 快照恢复升级前的目录布局、配置文件与 Base 视图，您的任何个人笔记与批注均不会丢失。",
          confirmLabel: "确认还原",
          cancelLabel: "取消",
        },
        () => {
          void (async () => {
            rbBtn.disabled = true;
            try {
              const res = await client.vaultUpgradeRollback();
              if (res.rolled_back) {
                new Notice("已无损还原至升级前目录结构。");
                onUpdated();
              } else {
                new Notice(`无法还原: ${res.reason ?? "未找到快照"}`, 8000);
                rbBtn.disabled = false;
              }
            } catch (err: unknown) {
              new Notice(
                `还原失败: ${err instanceof Error ? err.message : String(err)}`,
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
