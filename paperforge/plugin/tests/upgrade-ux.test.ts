/**
 * @vitest-environment jsdom
 */
import * as fs from "fs";
import * as path from "path";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("obsidian", () => {
  class Modal {
    app: unknown;
    contentEl = document.createElement("div");
    constructor(app: unknown) {
      this.app = app;
    }
    open() {
      (this as unknown as { onOpen?: () => void }).onOpen?.();
    }
    close() {
      (this as unknown as { onClose?: () => void }).onClose?.();
    }
  }
  class ItemView {
    containerEl = document.createElement("div");
    app: unknown;
    leaf: unknown;
    constructor(leaf: unknown) {
      this.leaf = leaf;
    }
    registerEvent() {}
  }
  const Notice = vi.fn();
  return {
    Modal,
    ItemView,
    Notice,
    Plugin: class {},
    PluginSettingTab: class {},
    Scope: class {
      register() {}
    },
    WorkspaceLeaf: class {},
    TFile: class {},
    Platform: {},
    setIcon: () => {},
    MarkdownRenderer: { renderMarkdown: vi.fn() },
  };
});

import {
  PaperForgeUpgradeModal,
  renderUpgradeAvailableBanner,
  renderStorageMigrationMaintenanceSection,
} from "../src/views/upgrade-modal";
import type { VaultUpgradePlanDto } from "../src/client";

function attachDomHelpers(): void {
  const proto = HTMLElement.prototype as unknown as Record<string, unknown>;
  if (!proto.empty) {
    proto.empty = function (this: HTMLElement) {
      this.innerHTML = "";
    };
  }
  if (!proto.addClass) {
    proto.addClass = function (this: HTMLElement, ...cls: string[]) {
      for (const c of cls) {
        for (const p of String(c).split(/\s+/).filter(Boolean)) {
          this.classList.add(p);
        }
      }
    };
  }
  if (!proto.setText) {
    proto.setText = function (this: HTMLElement, txt: string) {
      this.textContent = txt;
    };
  }
  if (!proto.createDiv) {
    proto.createDiv = function (this: HTMLElement, opts?: unknown) {
      return (this as unknown as { createEl: Function }).createEl("div", opts);
    };
  }
  if (!proto.createSpan) {
    proto.createSpan = function (this: HTMLElement, opts?: unknown) {
      return (this as unknown as { createEl: Function }).createEl("span", opts);
    };
  }
  if (!proto.createEl) {
    proto.createEl = function (
      this: HTMLElement,
      tag: string,
      opts?:
        | string
        | {
            cls?: string;
            text?: string;
            type?: string;
            attr?: Record<string, string>;
          }
    ) {
      const child = document.createElement(tag);
      if (typeof opts === "string") {
        child.className = opts;
      } else if (opts) {
        if (opts.cls) child.className = opts.cls;
        if (opts.text !== undefined) child.textContent = opts.text;
        if (opts.type && "type" in child) {
          (child as HTMLInputElement).type = opts.type;
        }
        if (opts.attr) {
          for (const [k, v] of Object.entries(opts.attr)) {
            child.setAttribute(k, v);
          }
        }
      }
      this.appendChild(child);
      return child;
    };
  }
}

function sampleVeteranPlan(
  overrides: Partial<VaultUpgradePlanDto> = {}
): VaultUpgradePlanDto {
  return {
    vault: "/vault",
    provenance: {
      state: "veteran_legacy",
      needs_upgrade: true,
      confidence: "high",
      signals: ["legacy_engine_dir:System/PaperForge"],
      legacy_engine_dir: "System/PaperForge",
    },
    census: {
      pf_canonical: { workspaces: 128 },
    },
    manifest: null,
    rollback_available: false,
    category_a_auto: [
      {
        id: "storage.move_to_dot_paperforge",
        area: "storage",
        title: "将底层引擎目录 System/PaperForge 收拢至隐藏目录 .paperforge/",
        detail: "保留可见笔记与 Zotero 原库不动。",
        fast_cutover: true,
      },
      {
        id: "ocr.local_salvage_backfill",
        area: "ocr",
        title: "从已保存的 OCR 原件免费离线恢复 6 篇派生全文",
        detail: "后台离线重建，无需重复消耗 OCR 额度。",
        fast_cutover: false,
      },
    ],
    category_b_reconfig: [],
    category_c_tamper: [],
    cleanup_candidates: [
      {
        id: "cleanup.venv_corrupt",
        path: "/vault/.venv-corrupt",
        bytes: 4_194_304,
        reason: "历史损坏的虚拟环境残留 (.venv-corrupt)",
      },
    ],
    summary: {
      auto_count: 2,
      fast_cutover_count: 1,
      progressive_heal_count: 1,
      reconfig_critical_count: 0,
      reconfig_minor_count: 0,
      tamper_count: 0,
      cleanup_candidate_count: 1,
      ocr_atoms: {
        total: 10,
        current: 4,
        rebuild_derived_local: 0,
        backfill_from_result_json: 6,
        re_ocr_needed: 0,
      },
    },
    ...overrides,
  };
}

describe("ADR-018: Iceberg Non-Blocking Vault Upgrade UX", () => {
  beforeEach(() => {
    attachDomHelpers();
  });

  it("upgrade-modal.ts contains zero UI emojis and zero [!!]/[OK] log prefixes", () => {
    const src = fs.readFileSync(
      path.resolve(__dirname, "../src/views/upgrade-modal.ts"),
      "utf-8"
    );
    expect(src).not.toMatch(/\[!!\]|\[OK\]/);
    expect(src).not.toMatch(/[\u{1F300}-\u{1FAFF}]/u);
  });

  it("hides banner on fresh_or_foreign vaults and renders dismissible non-blocking banner on veteran vaults", () => {
    const host = document.createElement("div");
    const foreignPlan = sampleVeteranPlan({
      provenance: {
        state: "fresh_or_foreign",
        needs_upgrade: false,
        confidence: "none",
        signals: [],
      },
    });
    expect(
      renderUpgradeAvailableBanner(host, foreignPlan, {
        onOpenModal: () => {},
        onDismiss: () => {},
      })
    ).toBe(false);
    expect(host.children.length).toBe(0);

    const onOpen = vi.fn();
    const onDismiss = vi.fn();
    expect(
      renderUpgradeAvailableBanner(host, sampleVeteranPlan(), {
        onOpenModal: onOpen,
        onDismiss,
      })
    ).toBe(true);
    const openBtn = host.querySelector(
      '[data-pf-testid="vault-upgrade-banner-open"]'
    ) as HTMLButtonElement;
    const dismissBtn = host.querySelector(
      '[data-pf-testid="vault-upgrade-banner-dismiss"]'
    ) as HTMLButtonElement;
    openBtn.click();
    dismissBtn.click();
    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("supports progressive disclosure, executes <3s fastCutover, and hands off heal to ControlDaemon", async () => {
    const vaultUpgradeApply = vi.fn().mockResolvedValue({
      dry_run: false,
      applied: true,
      fast_cutover: true,
      executed_steps: [{ step: "fast_storage_cutover" }],
      errors: [],
    });
    const daemonSubmitJob = vi.fn().mockResolvedValue({
      accepted: true,
      job: { job_id: "job_heal_1" },
    });
    const onUpgraded = vi.fn();

    const modal = new PaperForgeUpgradeModal(
      {} as never,
      {
        vaultUpgradeApply,
        daemonSubmitJob,
      } as never,
      sampleVeteranPlan(),
      { onUpgraded }
    );
    modal.open();

    // Progressive disclosure starts collapsed (`aria-expanded="false"`)
    const toggle = modal.contentEl.querySelector(
      '[data-pf-testid="upgrade-disclosure-toggle"]'
    ) as HTMLButtonElement;
    const drawer = modal.contentEl.querySelector(
      '[data-pf-testid="upgrade-disclosure-drawer"]'
    ) as HTMLElement;
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(drawer.classList.contains("is-expanded")).toBe(false);

    toggle.click();
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(drawer.classList.contains("is-expanded")).toBe(true);

    const applyBtn = modal.contentEl.querySelector(
      '[data-pf-testid="upgrade-apply-btn"]'
    ) as HTMLButtonElement;
    applyBtn.click();

    await vi.waitFor(() => expect(onUpgraded).toHaveBeenCalledTimes(1));
    expect(vaultUpgradeApply).toHaveBeenCalledWith({ fastCutover: true });
    expect(daemonSubmitJob).toHaveBeenCalledWith("upgrade.heal", {
      backfillOcr: true,
    });
  });

  it("shakes blocker card (.pf-nudge) instead of running cutover when SQLite DB is locked", () => {
    const vaultUpgradeApply = vi.fn();
    const lockedPlan = sampleVeteranPlan({
      category_c_tamper: [
        {
          id: "db.file_locked",
          area: "db",
          title: "数据库当前正被其他进程占用",
          detail: "请先关闭外部数据库查看器后重试。",
        },
      ],
    });
    const modal = new PaperForgeUpgradeModal(
      {} as never,
      { vaultUpgradeApply } as never,
      lockedPlan
    );
    modal.open();

    const applyBtn = modal.contentEl.querySelector(
      '[data-pf-testid="upgrade-apply-btn"]'
    ) as HTMLButtonElement;
    applyBtn.click();

    expect(vaultUpgradeApply).not.toHaveBeenCalled();
    const blocker = modal.contentEl.querySelector(
      '[data-pf-testid="upgrade-blocker-card"]'
    );
    expect(blocker?.classList.contains("pf-nudge")).toBe(true);
  });

  it("renders selective trash quarantine checkboxes and 1-click rollback in Settings maintenance", async () => {
    const vaultUpgradeApply = vi
      .fn()
      .mockResolvedValue({ applied: true, errors: [] });
    const vaultUpgradeRollback = vi
      .fn()
      .mockResolvedValue({ rolled_back: true });
    const onUpdated = vi.fn();
    const host = document.createElement("div");

    renderStorageMigrationMaintenanceSection(
      host,
      {} as never,
      { vaultUpgradeApply, vaultUpgradeRollback } as never,
      sampleVeteranPlan({ rollback_available: true }),
      onUpdated
    );

    const quarantineBtn = host.querySelector(
      '[data-pf-testid="cleanup-quarantine-btn"]'
    ) as HTMLButtonElement;
    quarantineBtn.click();

    await vi.waitFor(() => expect(vaultUpgradeApply).toHaveBeenCalledTimes(1));
    expect(vaultUpgradeApply).toHaveBeenCalledWith({
      fastCutover: true,
      quarantineIds: ["cleanup.venv_corrupt"],
      noRebuildDb: true,
    });
    expect(
      host.querySelector('[data-pf-testid="vault-upgrade-rollback-btn"]')
    ).not.toBeNull();
  });

  it("reports partial or failed cleanup honestly without false success and keeps retry enabled", async () => {
    const { Notice } = await import("obsidian");
    vi.mocked(Notice).mockClear();

    const vaultUpgradeApply = vi.fn().mockResolvedValue({
      applied: true,
      status: "partial_success",
      executed_steps: [{ step: "quarantine_residuals", quarantined: 0 }],
      errors: [
        {
          step: "quarantine:cleanup.venv_corrupt",
          error: "PermissionError: file locked",
        },
      ],
    });
    const onUpdated = vi.fn();
    const host = document.createElement("div");

    renderStorageMigrationMaintenanceSection(
      host,
      {} as never,
      { vaultUpgradeApply } as never,
      sampleVeteranPlan({ rollback_available: false }),
      onUpdated
    );

    const quarantineBtn = host.querySelector(
      '[data-pf-testid="cleanup-quarantine-btn"]'
    ) as HTMLButtonElement;
    quarantineBtn.click();

    await vi.waitFor(() => expect(vaultUpgradeApply).toHaveBeenCalledTimes(1));
    await vi.waitFor(() => expect(vi.mocked(Notice)).toHaveBeenCalled());
    const noticeMsg = String(vi.mocked(Notice).mock.calls[0]?.[0] ?? "");
    expect(noticeMsg).toContain("失败 1 项");
    expect(noticeMsg).not.toMatch(/^已将 \d+ 项历史残余安全移入/);
    expect(quarantineBtn.disabled).toBe(false);
  });
});
