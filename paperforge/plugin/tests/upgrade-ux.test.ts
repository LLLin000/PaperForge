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

  it("renders non-blocking Category-B follow-up items (.env / ChromaDB rebuild / Skill Hub)", () => {
    const planWithFollowups = sampleVeteranPlan({
      category_b_reconfig: [
        {
          id: "vectors.rebuild_sqlite_vec",
          area: "database",
          impact: "minor",
          title: "旧版 ChromaDB 向量索引需在新版中重新构建",
          detail: "新版已切换为 sqlite-vec。",
          remediation: "升级后点击构建向量索引。",
        },
        {
          id: "auth.env_migration_needed",
          area: "auth",
          impact: "experience_critical",
          title: ".env 中的接口密钥尚未导入系统安全凭据库",
          detail: "检测到 OCR_API_KEY。",
          remediation: "建议导入系统凭据库。",
        },
      ],
    });
    const modal = new PaperForgeUpgradeModal(
      {} as never,
      {} as never,
      planWithFollowups
    );
    modal.open();

    const list = modal.contentEl.querySelector(
      '[data-pf-testid="upgrade-followup-list"]'
    );
    expect(list).toBeTruthy();
    expect(list?.textContent).toContain("ChromaDB");
    expect(list?.textContent).toContain("OCR_API_KEY");
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
    const { setLanguage } = await import("../src/i18n");
    vi.mocked(Notice).mockClear();
    setLanguage({} as never, "zh");

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
    // Inline persistent status slot also preserves the failure message
    const inlineStatus = host.querySelector(
      '[data-pf-testid="cleanup-status-msg"]'
    );
    expect(inlineStatus?.textContent).toContain("失败 1 项");

    // Verify English locale renders cleanly too
    vi.mocked(Notice).mockClear();
    setLanguage({} as never, "en");
    const hostEn = document.createElement("div");
    renderStorageMigrationMaintenanceSection(
      hostEn,
      {} as never,
      { vaultUpgradeApply } as never,
      sampleVeteranPlan({ rollback_available: false }),
      onUpdated
    );
    const btnEn = hostEn.querySelector(
      '[data-pf-testid="cleanup-quarantine-btn"]'
    ) as HTMLButtonElement;
    expect(btnEn.textContent).toContain("Safe Trash");
    btnEn.click();
    await vi.waitFor(() => expect(vi.mocked(Notice)).toHaveBeenCalled());
    const noticeEn = String(vi.mocked(Notice).mock.calls[0]?.[0] ?? "");
    expect(noticeEn).toContain("failed 1");
    expect(noticeEn).toContain("locked");
  });

  it("translates raw OCR and Embedding API errors into beginner-friendly Chinese/English guidance", async () => {
    const { formatProviderConnectionError } = await import("../src/settings");
    expect(
      formatProviderConnectionError("HTTP 401 Unauthorized", "ocr", true)
    ).toContain("API Key 无效");
    expect(
      formatProviderConnectionError("429 quota exceeded", "embed", true)
    ).toContain("免费额度已用完");
    expect(
      formatProviderConnectionError(
        "embedding dimension mismatch 1024 vs 1536",
        "embed",
        true
      )
    ).toContain("重建索引");
    expect(
      formatProviderConnectionError("ECONNREFUSED", "ocr", true)
    ).toContain("代理设置");
    expect(
      formatProviderConnectionError("NO_PYTHON runtime missing", "ocr", true)
    ).toContain("一键启用引擎");
  });

  it("preselects matched legacy BBT folders in UpgradeModal, guards empty SQLite selection, and commits Zotero choice before cutover", async () => {
    const callOrder: string[] = [];
    const onCommitZoteroConfig = vi.fn(async () => {
      callOrder.push("commitZotero");
    });
    const vaultUpgradeApply = vi.fn(async () => {
      callOrder.push("vaultUpgradeApply");
      return {
        dry_run: false,
        applied: true,
        fast_cutover: true,
        executed_steps: [{ step: "fast_storage_cutover" }],
        errors: [],
      };
    });
    const daemonSubmitJob = vi.fn().mockResolvedValue({ accepted: true });
    const zoteroDetect = vi.fn().mockResolvedValue({
      found: true,
      zotero_dir: "/zotero",
      total_papers: 500,
      collections: [
        { key: "C1", name: "骨科", item_count: 120, top_level: true },
        { key: "C2", name: "运动医学", item_count: 80, top_level: true },
        { key: "C3", name: "DEMO", item_count: 300, top_level: true },
      ],
    });
    const onUpgraded = vi.fn();

    const modal = new PaperForgeUpgradeModal(
      {} as never,
      {
        zoteroDetect,
        vaultUpgradeApply,
        daemonSubmitJob,
      } as never,
      sampleVeteranPlan(),
      {
        onUpgraded,
        zoteroContext: {
          currentSourceMode: "sqlite",
          currentSelectedCollections: [],
          zoteroDataDir: "/zotero",
          legacyDomainNames: ["骨科"],
          hasManualBbtExports: true,
          explicitSourceModeInConfig: false,
          onCommitZoteroConfig,
        },
      }
    );
    modal.open();

    await vi.waitFor(() => {
      const cb1 = modal.contentEl.querySelector(
        '[data-pf-testid="upgrade-zotero-col-C1"]'
      ) as HTMLInputElement | null;
      expect(cb1?.checked).toBe(true);
    });
    const cb3 = modal.contentEl.querySelector(
      '[data-pf-testid="upgrade-zotero-col-C3"]'
    ) as HTMLInputElement;
    expect(cb3.checked).toBe(false);

    // Clearing all folders must block cutover when SQLite mode has collections
    const clearBtn = modal.contentEl.querySelector(
      '[data-pf-testid="upgrade-zotero-clear"]'
    ) as HTMLButtonElement;
    clearBtn.click();
    const applyBtn = modal.contentEl.querySelector(
      '[data-pf-testid="upgrade-apply-btn"]'
    ) as HTMLButtonElement;
    applyBtn.click();
    expect(vaultUpgradeApply).not.toHaveBeenCalled();
    expect(
      modal.contentEl.querySelector(
        '[data-pf-testid="upgrade-zotero-guard-msg"]'
      )
    ).not.toBeNull();

    // Selecting C2 and applying must commit Zotero config BEFORE vaultUpgradeApply
    const cb2 = modal.contentEl.querySelector(
      '[data-pf-testid="upgrade-zotero-col-C2"]'
    ) as HTMLInputElement;
    cb2.checked = true;
    cb2.dispatchEvent(new Event("change"));
    applyBtn.click();

    await vi.waitFor(() => expect(onUpgraded).toHaveBeenCalledTimes(1));
    expect(vaultUpgradeApply).toHaveBeenCalledWith({
      fastCutover: true,
      zoteroSourceMode: "sqlite",
      zoteroSelectedCollections: ["C2"],
      zoteroDataDir: "/zotero",
    });
    expect(callOrder).toEqual(["vaultUpgradeApply", "commitZotero"]);
    expect(onCommitZoteroConfig).toHaveBeenCalledWith({
      zoteroSourceMode: "sqlite",
      zoteroSelectedCollections: ["C2"],
      zoteroDataDir: "/zotero",
    });

    // If vaultUpgradeApply fails, Zotero config MUST NOT be mutated before snapshot/rollback
    onCommitZoteroConfig.mockClear();
    const failingApply = vi.fn().mockResolvedValue({
      dry_run: false,
      applied: false,
      errors: [{ step: "wal_quiesce", error: "DB locked" }],
    });
    const modalFail = new PaperForgeUpgradeModal(
      {} as never,
      {
        zoteroDetect,
        vaultUpgradeApply: failingApply,
        daemonSubmitJob,
      } as never,
      sampleVeteranPlan(),
      {
        zoteroContext: {
          currentSourceMode: "sqlite",
          currentSelectedCollections: [],
          zoteroDataDir: "/zotero",
          legacyDomainNames: ["骨科"],
          hasManualBbtExports: true,
          explicitSourceModeInConfig: false,
          onCommitZoteroConfig,
        },
      }
    );
    modalFail.open();
    await vi.waitFor(() => {
      expect(
        modalFail.contentEl.querySelector(
          '[data-pf-testid="upgrade-zotero-col-C1"]'
        )
      ).not.toBeNull();
    });
    (
      modalFail.contentEl.querySelector(
        '[data-pf-testid="upgrade-apply-btn"]'
      ) as HTMLButtonElement
    ).click();
    await vi.waitFor(() => expect(failingApply).toHaveBeenCalledTimes(1));
    expect(onCommitZoteroConfig).not.toHaveBeenCalled();

    // Legacy BBT option bypasses folder requirement
    const modalBbt = new PaperForgeUpgradeModal(
      {} as never,
      {
        zoteroDetect,
        vaultUpgradeApply,
        daemonSubmitJob,
      } as never,
      sampleVeteranPlan(),
      {
        zoteroContext: {
          currentSourceMode: "sqlite",
          currentSelectedCollections: [],
          zoteroDataDir: "/zotero",
          legacyDomainNames: [],
          hasManualBbtExports: true,
          explicitSourceModeInConfig: false,
          onCommitZoteroConfig,
        },
      }
    );
    modalBbt.open();
    await vi.waitFor(() => {
      expect(
        modalBbt.contentEl.querySelector(
          '[data-pf-testid="upgrade-zotero-mode-bbt"]'
        )
      ).not.toBeNull();
    });
    const bbtRadio = modalBbt.contentEl.querySelector(
      '[data-pf-testid="upgrade-zotero-mode-bbt"]'
    ) as HTMLInputElement;
    bbtRadio.checked = true;
    bbtRadio.dispatchEvent(new Event("change"));
    (
      modalBbt.contentEl.querySelector(
        '[data-pf-testid="upgrade-apply-btn"]'
      ) as HTMLButtonElement
    ).click();
    await vi.waitFor(() =>
      expect(onCommitZoteroConfig).toHaveBeenLastCalledWith({
        zoteroSourceMode: "bbt",
        zoteroSelectedCollections: [],
        zoteroDataDir: "/zotero",
      })
    );
  });
});
