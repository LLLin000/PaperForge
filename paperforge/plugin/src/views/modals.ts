import { Modal, App, Notice } from "obsidian";
import * as fs from "fs";
import * as path from "path";
import * as https from "https";
import { execFile, spawn } from "child_process";
import { t } from "../i18n";
import { PaperForgeSettings } from "../constants";
import { resolveVaultPaths } from "../services/memory-state";
import {
  resolveGitDir,
  paperforgeEnrichedEnv,
} from "../services/python-bridge";
import {
  ManagedRuntime,
  resolveRuntimeCommand,
} from "../services/managed-runtime";
import type { PythonResult } from "../services/python-bridge";
import { shouldBlockStep3 } from "./step3-gate";

// ── Interfaces ──

export interface IPluginRef {
  settings: PaperForgeSettings;
  saveSettings(): Promise<void>;
  loadSettings(): Promise<void>;
  manifest: { version: string };
}

export interface ISettingTab {
  display(): void;
}

interface OrphanItem {
  citation_key?: string;
  key: string;
  has_pdf?: boolean;
  collection_path?: string;
  title?: string;
  authors?: string;
  year?: string;
}

/* ── OCR Privacy Modal ── */

export class PaperForgeOcrPrivacyModal extends Modal {
  private _onConfirm: (() => void) | undefined;

  constructor(app: App, onConfirm?: () => void) {
    super(app);
    this._onConfirm = onConfirm;
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.addClass("paperforge-modal");
    contentEl.addClass("paperforge-ocr-privacy-modal");

    // Title
    contentEl.createEl("h2", { text: t("ocr_privacy_title") });

    // Warning text
    const warningEl = contentEl.createEl("div", {
      cls: "paperforge-ocr-privacy-warning",
    });
    warningEl.createEl("p", { text: t("ocr_privacy_warning") });

    // "I Understand" button
    const btnRow = contentEl.createEl("div", {
      cls: "paperforge-ocr-privacy-actions",
    });
    const confirmBtn = btnRow.createEl("button", {
      cls: "paperforge-step-btn mod-cta",
      text: t("ocr_understand"),
    });
    confirmBtn.addEventListener("click", () => {
      this.close();
      if (this._onConfirm) this._onConfirm();
    });
  }

  onClose() {
    this.contentEl.empty();
  }
}

/* ── Orphan Paper Cleanup Modal ── */

export class PaperForgeOrphanModal extends Modal {
  private orphans: (OrphanItem & { _selected: boolean; _idx: number })[];
  private vaultPath: string;
  private py: PythonResult | null;
  private _rowEls: HTMLElement[] = [];
  private _countEl!: HTMLElement;
  private _selectAllBtn!: HTMLElement;

  constructor(
    app: App,
    orphans: OrphanItem[],
    vaultPath: string,
    py: PythonResult | null
  ) {
    super(app);
    this.orphans = orphans.map((o, i) => ({ ...o, _selected: true, _idx: i }));
    this.vaultPath = vaultPath;
    this.py = py;
  }

  _updateUI() {
    const sel = this.orphans.filter((o) => o._selected);
    this._countEl.setText(
      t("orphan_delete_selected").replace("{count}", String(sel.length))
    );
    this._selectAllBtn.setText(
      sel.length === this.orphans.length
        ? t("orphan_deselect_all")
        : t("orphan_select_all")
    );
    for (const o of this.orphans) {
      const row = this._rowEls[o._idx];
      if (!row) continue;
      row.toggleClass("paperforge-orphan-dimmed", !o._selected);
    }
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.addClass("paperforge-modal");
    contentEl.createEl("h2", {
      text: t("orphan_title").replace("{count}", String(this.orphans.length)),
    });
    contentEl.createEl("p", {
      cls: "paperforge-modal-desc",
      text: t("orphan_desc"),
    });

    this._rowEls = [];
    const listEl = contentEl.createEl("div", { cls: "paperforge-orphan-list" });
    for (const o of this.orphans) {
      const row = listEl.createEl("div", {
        cls:
          "paperforge-orphan-row" +
          (o._selected ? "" : " paperforge-orphan-dimmed"),
      });
      this._rowEls.push(row);

      const left = row.createEl("div", { cls: "paperforge-orphan-info" });

      // Header: citation key + tags
      const hdr = left.createEl("div", { cls: "paperforge-orphan-header" });
      hdr.createEl("span", {
        cls: "paperforge-orphan-key",
        text: o.citation_key || o.key,
      });
      const tags = hdr.createEl("span", { cls: "paperforge-orphan-tags" });
      tags.createEl("span", {
        cls: "paperforge-tag " + (o.has_pdf ? "tag-pdf" : "tag-nopdf"),
        text: o.has_pdf ? "PDF" : "no PDF",
      });
      if (o.collection_path)
        tags.createEl("span", {
          cls: "paperforge-tag tag-collection",
          text: o.collection_path,
        });

      if (o.title)
        left.createEl("div", { cls: "paperforge-orphan-title", text: o.title });
      const meta = [];
      if (o.authors) meta.push(o.authors);
      if (o.year) meta.push(o.year);
      if (meta.length > 0)
        left.createEl("div", {
          cls: "paperforge-orphan-meta",
          text: meta.join(" \u00B7 "),
        });
      left.createEl("div", {
        cls: "paperforge-orphan-explain",
        text: t("orphan_explain"),
      });

      row.addEventListener("click", () => {
        o._selected = !o._selected;
        this._updateUI();
      });
    }

    const btnRow = contentEl.createEl("div", {
      cls: "paperforge-modal-actions",
    });
    this._selectAllBtn = btnRow.createEl("button", {
      cls: "paperforge-step-btn",
      text: "Deselect all",
    });
    this._selectAllBtn.addEventListener("click", () => {
      const allSel = this.orphans.every((o) => o._selected);
      for (const o of this.orphans) o._selected = !allSel;
      this._updateUI();
    });

    this._countEl = btnRow.createEl("button", {
      cls: "paperforge-step-btn mod-cta",
      text: "Delete " + this.orphans.length + " selected",
    });

    btnRow
      .createEl("button", { cls: "paperforge-step-btn", text: "Keep all" })
      .addEventListener("click", () => this.close());

    this._countEl.addEventListener("click", () => {
      const selected = this.orphans.filter((o) => o._selected);
      if (selected.length === 0) {
        new Notice(t("orphan_none_selected"));
        return;
      }
      this._countEl.setText("Deleting...");
      this._countEl.setAttr("disabled", "");
      this._selectAllBtn.setAttr("disabled", "");
      if (!this.py || !this.py.path) {
        new Notice("PaperForge: Python not found");
        this.close();
        return;
      }
      const keys = selected.map((o) => o.key);
      execFile(
        this.py.path,
        [
          ...this.py.extraArgs,
          "-m",
          "paperforge",
          "--vault",
          this.vaultPath,
          "prune",
          "--force",
          "--json",
          ...keys,
        ],
        { cwd: this.vaultPath, timeout: 60000 },
        (err, stdout) => {
          if (err) {
            new Notice("PaperForge: prune failed");
            this.close();
            return;
          }
          try {
            const r = JSON.parse(stdout);
            const deleted = (r.data && r.data.deleted) || [];
            new Notice("Deleted " + deleted.length + " orphan workspace(s)");
          } catch (_) {
            new Notice("PaperForge: prune done");
          }
          this.close();
        }
      );
    });
  }

  onClose() {
    this.contentEl.empty();
  }
}

/* ── Orphan state checker ── */

export function checkOrphanState(app: App, plugin: IPluginRef, vp: string) {
  console.log("[PF] checkOrphanState called");
  try {
    const paths = resolveVaultPaths(vp);
    const orphanPath = paths.orphanStatePath;
    if (!fs.existsSync(orphanPath)) {
      console.log("[PF] orphan file NOT FOUND");
      return;
    }
    console.log("[PF] orphan file FOUND");
    const raw = fs.readFileSync(orphanPath, "utf-8");
    const data = JSON.parse(raw);
    const orphans = data;
    const py = {
      path: "python",
      extraArgs: [] as string[],
      source: "auto-detected" as const,
    };
    console.log("[PF] py.path:", py ? py.path : "null");
    new PaperForgeOrphanModal(app, orphans, vp, py).open();
    fs.unlinkSync(orphanPath);
    console.log("[PF] orphan file cleaned");
  } catch (e) {
    console.log("[PF] checkOrphanState exception:", (e as Error).message || e);
  }
}

/* ── Setup Wizard Modal ── */

export class PaperForgeSetupModal extends Modal {
  private plugin: IPluginRef;
  private _step: number;
  private _installLog!: HTMLElement;
  private _pendingSave: ReturnType<typeof setTimeout> | null = null;
  private _apiKeyValidated!: boolean;
  private _apiKeyStatus!: HTMLElement;
  private _showSkipConfirm: boolean = false;
  private _onComplete: (() => void) | undefined;

  constructor(app: App, plugin: IPluginRef, onComplete?: () => void) {
    super(app);
    this.plugin = plugin;
    this._step = 1;
    this._onComplete = onComplete;
  }

  _resolvePython(): { path: string; args: string[] } {
    const vp = this.plugin.settings.vault_path?.trim() || ".";
    const rt = new ManagedRuntime({
      runtimeDir: path.join(vp, ".paperforge-test-venv"),
      pluginVersion: this.plugin.manifest.version,
      osPlatform: process.platform,
      osArch: process.arch,
      fs: fs as any,
      execFile: execFile as any,
      execFileSync: require("child_process").execFileSync as any,
    });
    const run = resolveRuntimeCommand(rt.current());
    return run
      ? { path: run.command, args: [...run.args] }
      : { path: "python", args: [] };
  }

  onOpen() {
    this._render();
  }

  onClose() {
    this.contentEl.empty();
  }

  _render() {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("paperforge-modal");

    this._renderStepIndicator();
    this._renderStepContent();
    this._renderNavigation();
  }

  _renderStepIndicator() {
    const steps = [
      t("wizard_step1"),
      t("wizard_step2"),
      t("wizard_step3"),
      t("wizard_step4"),
      t("wizard_step5"),
    ];
    const bar = this.contentEl.createEl("div", { cls: "paperforge-step-bar" });
    steps.forEach((label, i) => {
      const n = i + 1;
      const dot = bar.createEl("div", {
        cls: `paperforge-step-dot ${n === this._step ? "active" : ""} ${n < this._step ? "done" : ""}`,
      });
      dot.createEl("span", { cls: "paperforge-step-num", text: `${n}` });
      dot.createEl("span", { cls: "paperforge-step-label", text: label });
    });
  }

  _renderStepContent() {
    const el = this.contentEl.createEl("div", {
      cls: "paperforge-step-content",
    });
    switch (this._step) {
      case 1:
        this._stepOverview(el);
        break;
      case 2:
        this._stepDirectories(el);
        break;
      case 3:
        this._stepKeys(el);
        break;
      case 4:
        this._stepInstall(el);
        break;
      case 5:
        this._stepComplete(el);
        break;
    }
  }

  _renderNavigation() {
    const nav = this.contentEl.createEl("div", { cls: "paperforge-step-nav" });
    if (this._step > 1) {
      nav
        .createEl("button", { cls: "paperforge-step-btn", text: t("nav_prev") })
        .addEventListener("click", () => {
          this._step--;
          this._showSkipConfirm = false;
          this._render();
        });
    }
    if (this._step < 5) {
      const nextBtn = nav.createEl("button", {
        cls: "paperforge-step-btn mod-cta",
        text: t("nav_next"),
      });
      nextBtn.addEventListener("click", () => {
        if (this._step === 3) {
          const result = this._validateStep3();
          if (result.blocked) {
            if (result.reason === "zotero") return;
            if (result.reason === "ocr") {
              this._showSkipConfirm = true;
              this._render();
              return;
            }
          }
        }
        this._step++;
        this._showSkipConfirm = false;
        this._render();
      });
    } else {
      nav
        .createEl("button", {
          cls: "paperforge-step-btn",
          text: t("nav_close"),
        })
        .addEventListener("click", () => this.close());
    }
  }

  _validateStep3(): { blocked: boolean; reason?: "ocr" | "zotero" } {
    const s = this.plugin.settings;

    const gate = shouldBlockStep3(this._apiKeyValidated, s.zotero_data_dir);
    if (gate.reason === "ocr") {
      return gate;
    }

    // Zotero filesystem checks — run for zotero reason AND for "all clear"
    const zotPath = (s.zotero_data_dir || "").trim();
    if (!zotPath) {
      new Notice(
        "Zotero \u6570\u636E\u76EE\u5F55\u4E3A\u5FC5\u586B\u9879\uFF0C\u8BF7\u586B\u5199\u8DEF\u5F84"
      );
      return { blocked: true, reason: "zotero" };
    }
    if (!fs.existsSync(zotPath)) {
      new Notice(
        "Zotero \u6570\u636E\u76EE\u5F55\u8DEF\u5F84\u4E0D\u5B58\u5728"
      );
      return { blocked: true, reason: "zotero" };
    }
    if (!fs.statSync(zotPath).isDirectory()) {
      new Notice(
        "Zotero \u6570\u636E\u76EE\u5F55\u8DEF\u5F84\u4E0D\u662F\u4E00\u4E2A\u76EE\u5F55"
      );
      return { blocked: true, reason: "zotero" };
    }
    const storagePath = path.join(zotPath, "storage");
    if (
      !fs.existsSync(storagePath) ||
      !fs.statSync(storagePath).isDirectory()
    ) {
      new Notice(
        "Zotero \u6570\u636E\u76EE\u5F55\u4E2D\u672A\u627E\u5230 storage/ \u5B50\u76EE\u5F55"
      );
      return { blocked: true, reason: "zotero" };
    }

    return { blocked: false };
  }

  /* ── Step 1: Overview ── */
  _stepOverview(el: HTMLElement) {
    el.createEl("h2", { text: t("wizard_title") });
    el.createEl("p", { text: t("wizard_intro") });

    const s = this.plugin.settings;
    const vault = (this.app.vault.adapter as any).basePath;
    const tree = el.createEl("div", { cls: "paperforge-dir-tree" });
    // HARDEN-05: Use createEl() DOM API instead of innerHTML to prevent XSS
    // from user-configured directory names containing HTML/script tags.
    const rootNode = tree.createEl("div", { cls: "paperforge-dir-node root" });
    rootNode.textContent = `\uD83D\uDCC1 Vault (${vault})`;

    const children = tree.createEl("div", { cls: "paperforge-dir-children" });

    const resourcesFolder = children.createEl("div", {
      cls: "paperforge-dir-node folder",
    });
    resourcesFolder.textContent = `\uD83D\uDCC1 ${s.resources_dir || "Resources"}/ \u2014 \u6587\u732E\u5361\u7247\u76EE\u5F55\uFF08Base \u6570\u636E\u6765\u6E90\uFF09`;
    const resourcesChildren = resourcesFolder.createEl("div", {
      cls: "paperforge-dir-children",
    });
    resourcesChildren.createEl("div", {
      cls: "paperforge-dir-node file",
      text: `\uD83D\uDCC1 ${s.literature_dir || "Literature"}/ \u2014 \u6587\u732E\u5361\u7247`,
    });

    children.createEl("div", {
      cls: "paperforge-dir-node folder",
      text: `\uD83D\uDCC1 ${s.base_dir || "Bases"}/ \u2014 \u6570\u636E\u7BA1\u7406\u9762\u677F`,
    });
    children.createEl("div", {
      cls: "paperforge-dir-node folder",
      text: `\uD83D\uDCC1 ${s.system_dir || "System"}/ \u2014 Zotero \u8F6F\u94FE\u63A5 + PaperForge \u7CFB\u7EDF\u6587\u4EF6\u5939`,
    });

    el.createEl("p", {
      text: t("wizard_preview"),
      cls: "paperforge-modal-hint",
    });
    el.createEl("p", {
      text: t("wizard_safety"),
      cls: "paperforge-modal-hint",
    });

    const summary = el.createEl("div", { cls: "paperforge-summary" });
    const overviewItems = [
      {
        label: t("dir_resources"),
        val: `${vault}/${s.resources_dir || "Resources"}`,
      },
      {
        label: t("dir_notes"),
        val: `${vault}/${s.resources_dir || "Resources"}/${s.literature_dir || "Literature"}`,
      },
      { label: t("dir_base"), val: `${vault}/${s.base_dir || "Bases"}` },
      { label: t("dir_system"), val: `${vault}/${s.system_dir || "System"}` },
    ];
    for (const item of overviewItems) {
      const row = summary.createEl("div", { cls: "paperforge-summary-row" });
      row.createEl("span", {
        cls: "paperforge-summary-label",
        text: item.label,
      });
      row.createEl("span", { cls: "paperforge-summary-value", text: item.val });
    }
  }

  /* ── Step 2: Directory Config (editable) ── */
  _stepDirectories(el: HTMLElement) {
    el.createEl("h2", { text: t("wizard_step2") });
    el.createEl("p", { text: t("wizard_intro") });

    const s = this.plugin.settings;
    const vault = (this.app.vault.adapter as any).basePath;

    this._modalField(el, t("dir_vault"), vault, true);

    el.createEl("p", {
      text: t("wizard_dir_hint"),
      cls: "paperforge-modal-hint",
    });

    this._modalInput(
      el,
      "\u8D44\u6E90\u76EE\u5F55\uFF08\u521B\u5EFA\u6587\u732E\u5361\u7247\u76EE\u5F55\u7684\u5730\u65B9\uFF09",
      "resources_dir",
      s.resources_dir,
      "Resources"
    );

    el.createEl("p", {
      text: t("wizard_dir_sub_hint"),
      cls: "paperforge-modal-hint",
    });

    this._modalInput(
      el,
      "\u6587\u732E\u5361\u7247\u76EE\u5F55\uFF08\u5B58\u653E\u6587\u732E\u5361\u7247\u7684\u5730\u65B9\uFF0CBase \u6570\u636E\u6765\u6E90\uFF09",
      "literature_dir",
      s.literature_dir,
      "Literature"
    );

    el.createEl("p", {
      text: t("wizard_sys_hint"),
      cls: "paperforge-modal-hint",
    });

    this._modalInput(
      el,
      "\u7CFB\u7EDF\u76EE\u5F55\uFF08\u5B58\u653E Zotero \u8F6F\u94FE\u63A5\u548C PaperForge \u7CFB\u7EDF\u6587\u4EF6\uFF09",
      "system_dir",
      s.system_dir,
      "System"
    );
    this._modalInput(
      el,
      "Base \u76EE\u5F55\uFF08\u5B58\u653E\u6570\u636E\u7BA1\u7406\u9762\u677F\u7684\u5730\u65B9\uFF09",
      "base_dir",
      s.base_dir,
      "Bases"
    );

    el.createEl("p", {
      text: t("wizard_safety"),
      cls: "paperforge-modal-hint",
    });
    const preview = el.createEl("div", { cls: "paperforge-summary" });
    const previewItems = [
      { label: t("dir_resources"), val: `${vault}/${s.resources_dir || ""}` },
      {
        label: t("dir_notes"),
        val: `${vault}/${s.resources_dir || ""}/${s.literature_dir || ""}`,
      },
      { label: t("dir_system"), val: `${vault}/${s.system_dir || ""}` },
      { label: t("dir_base"), val: `${vault}/${s.base_dir || ""}` },
    ];
    for (const item of previewItems) {
      const row = preview.createEl("div", { cls: "paperforge-summary-row" });
      row.createEl("span", {
        cls: "paperforge-summary-label",
        text: item.label,
      });
      row.createEl("span", { cls: "paperforge-summary-value", text: item.val });
    }
  }

  /* ── Step 3: Keys, Zotero & Agent ── */
  _stepKeys(el: HTMLElement) {
    el.createEl("h2", { text: t("wizard_step3") });

    if (this._showSkipConfirm) {
      this._renderSkipConfirm(el);
      return;
    }

    const s = this.plugin.settings;

    el.createEl("p", {
      text: t("wizard_agent_hint"),
      cls: "paperforge-modal-hint",
    });

    const AGENTS = [
      { key: "opencode", name: "OpenCode" },
      { key: "claude", name: "Claude Code" },
      { key: "cursor", name: "Cursor" },
      { key: "github_copilot", name: "GitHub Copilot" },
      { key: "windsurf", name: "Windsurf" },
      { key: "codex", name: "Codex" },
      { key: "gemini", name: "Gemini CLI" },
      { key: "cline", name: "Cline" },
    ];
    const agentRow = el.createEl("div", { cls: "paperforge-modal-field" });
    agentRow.createEl("label", {
      cls: "paperforge-modal-label",
      text: t("label_agent"),
    });
    const select = agentRow.createEl("select", {
      cls: "paperforge-modal-select",
    });
    for (const a of AGENTS) {
      const opt = select.createEl("option", {
        text: a.name,
        attr: { value: a.key },
      });
      if (a.key === (s.agent_platform || "opencode")) opt.selected = true;
    }
    select.addEventListener("change", () => {
      s.agent_platform = select.value;
      if (this._pendingSave) clearTimeout(this._pendingSave);
      this._pendingSave = setTimeout(() => {
        this.plugin.saveSettings();
        this._pendingSave = null;
      }, 500);
    });

    el.createEl("p", {
      text: t("wizard_keys_hint"),
      cls: "paperforge-modal-hint",
    });

    // PaddleOCR API Key with validate button
    const apiRow = el.createEl("div", { cls: "paperforge-modal-field" });
    apiRow.createEl("label", {
      cls: "paperforge-modal-label",
      text: t("field_paddleocr"),
    });
    const apiInput = apiRow.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "password", placeholder: "API Key" },
    });
    // Issue #79: never display or persist raw key; check configured flag (SecretStorage is async)
    const _hasOcrKey = this.plugin.settings._paddleocr_configured || false;
    apiInput.placeholder = _hasOcrKey
      ? "•••••••• (stored securely)"
      : "API Key";
    apiInput.value = "";
    this._apiKeyValidated = false;
    this._apiKeyStatus = apiRow.createEl("span", {
      cls: "paperforge-apikey-status",
      text: "",
    });
    const validateBtn = apiRow.createEl("button", {
      cls: "paperforge-step-btn",
      text: "\u9A8C\u8BC1",
    });
    validateBtn.addEventListener("click", () =>
      this._validateApiKey(apiInput.value, validateBtn)
    );
    apiInput.addEventListener("input", () => {
      // Issue #79: never persist raw key to settings; SecretStorage on validation success only
      this._apiKeyValidated = false;
      this._apiKeyStatus.textContent = "";
      this._apiKeyStatus.className = "paperforge-apikey-status";
    });
    if (this._pendingSave) clearTimeout(this._pendingSave);
    this._pendingSave = setTimeout(() => {
      this.plugin.saveSettings();
      this._pendingSave = null;
    }, 500);

    el.createEl("p", {
      text: t("wizard_api_hint_skip"),
      cls: "paperforge-modal-hint",
    });

    // Zotero data directory (now required)
    const zotRow = el.createEl("div", { cls: "paperforge-modal-field" });
    zotRow.createEl("label", {
      cls: "paperforge-modal-label",
      text: t("field_zotero_data"),
    });
    const zotInput = zotRow.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text", placeholder: t("field_zotero_placeholder") },
    });
    zotInput.value = s.zotero_data_dir || "";
    zotInput.addEventListener("input", () => {
      s.zotero_data_dir = zotInput.value;
      if (this._pendingSave) clearTimeout(this._pendingSave);
      this._pendingSave = setTimeout(() => {
        this.plugin.saveSettings();
        this._pendingSave = null;
      }, 500);
    });
  }

  _validateApiKey(key: string, btn: HTMLButtonElement) {
    if (!key || key.length < 10) {
      this._apiKeyStatus.textContent =
        "\u5BC6\u94A5\u683C\u5F0F\u4E0D\u6B63\u786E\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002";
      this._apiKeyStatus.className = "paperforge-apikey-status error";
      return;
    }
    btn.disabled = true;
    btn.textContent = "\u9A8C\u8BC1\u4E2D\u2026";
    this._apiKeyStatus.textContent = "\u6B63\u5728\u9A8C\u8BC1\u2026";
    this._apiKeyStatus.className = "paperforge-apikey-status";

    const postData = JSON.stringify({ model: "PaddleOCR-VL-1.5" });
    const options = {
      hostname: "paddleocr.aistudio-app.com",
      path: "/api/v2/ocr/jobs",
      method: "POST",
      headers: {
        Authorization: "bearer " + key,
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(postData),
      },
      timeout: 10000,
    } as https.RequestOptions;
    const req = https.request(options, async (res) => {
      btn.disabled = false;
      btn.textContent = "\u9A8C\u8BC1";
      let body = "";
      res.on("data", (chunk) => (body += chunk));
      res.on("end", async () => {
        try {
          const json = JSON.parse(body);
          if (res.statusCode === 400 && json.code === 10001) {
            // 400 code=10001 = auth passed, file missing (expected)
            // Issue #79: store validated key in SecretStorage, never in plaintext settings
            const ss = (this.app as any).secretStorage;
            try {
              await ss?.setSecret?.("paddleocr-api-key", key);
              const readback = await ss?.getSecret?.("paddleocr-api-key");
              if (readback === key) {
                const s2 = this.plugin.settings;
                s2._paddleocr_configured = true;
                s2.paddleocr_api_key = "";
                this.plugin.saveSettings();
              }
            } catch {
              // SecretStorage write failed; key not stored, validation not persisted
            }
            this._apiKeyStatus.textContent = "\u2713 \u5BC6\u94A5\u6709\u6548";
            this._apiKeyStatus.className = "paperforge-apikey-status ok";
            this._apiKeyValidated = true;
          } else if (res.statusCode === 401) {
            this._apiKeyStatus.textContent =
              "\u9A8C\u8BC1\u5931\u8D25\uFF1A\u5BC6\u94A5\u65E0\u6548\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002";
            this._apiKeyStatus.className = "paperforge-apikey-status error";
            this._apiKeyValidated = false;
          } else {
            this._apiKeyStatus.textContent =
              "\u9A8C\u8BC1\u5931\u8D25\uFF1AAPI \u8FD4\u56DE " +
              res.statusCode +
              "\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002";
            this._apiKeyStatus.className = "paperforge-apikey-status error";
            this._apiKeyValidated = false;
          }
        } catch (e) {
          this._apiKeyStatus.textContent =
            "\u9A8C\u8BC1\u5931\u8D25\uFF1A\u65E0\u6CD5\u89E3\u6790\u54CD\u5E94\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002";
          this._apiKeyStatus.className = "paperforge-apikey-status error";
          this._apiKeyValidated = false;
        }
      });
    });
    req.on("error", (e) => {
      btn.disabled = false;
      btn.textContent = "\u9A8C\u8BC1";
      this._apiKeyStatus.textContent =
        "\u9A8C\u8BC1\u5931\u8D25\uFF1A\u65E0\u6CD5\u8FDE\u63A5 (" +
        e.message +
        ")\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002";
      this._apiKeyStatus.className = "paperforge-apikey-status error";
      this._apiKeyValidated = false;
    });
    req.write(postData);
    req.end();
  }

  _renderSkipConfirm(el: HTMLElement) {
    el.createEl("p", {
      text: t("wizard_skip_ocr_desc"),
      cls: "paperforge-modal-desc",
    });

    const btnRow = el.createEl("div", { cls: "paperforge-modal-actions" });
    btnRow
      .createEl("button", {
        cls: "paperforge-step-btn mod-cta",
        text: t("wizard_skip_ocr_continue"),
      })
      .addEventListener("click", () => {
        this._showSkipConfirm = false;
        this._step++;
        this._render();
      });
    btnRow
      .createEl("button", {
        cls: "paperforge-step-btn",
        text: t("wizard_skip_ocr_back"),
      })
      .addEventListener("click", () => {
        this._showSkipConfirm = false;
        this._render();
      });
  }

  /* ── Modal form helpers ── */
  _modalField(
    el: HTMLElement,
    label: string,
    value: string,
    disabled: boolean
  ) {
    const row = el.createEl("div", { cls: "paperforge-modal-field" });
    row.createEl("label", { cls: "paperforge-modal-label", text: label });
    const input = row.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text" },
    });
    input.value = value;
    input.disabled = !!disabled;
  }

  _modalInput(
    el: HTMLElement,
    label: string,
    key: string,
    value: string,
    placeholder: string
  ) {
    const row = el.createEl("div", { cls: "paperforge-modal-field" });
    row.createEl("label", { cls: "paperforge-modal-label", text: label });
    const input = row.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text", placeholder: placeholder || "" },
    });
    input.value = value;
    const settings = this.plugin.settings;
    input.addEventListener("input", () => {
      settings[key] = input.value;
      if (this._pendingSave) clearTimeout(this._pendingSave);
      this._pendingSave = setTimeout(() => {
        this.plugin.saveSettings();
        this._pendingSave = null;
      }, 500);
    });
  }

  _modalSecret(
    el: HTMLElement,
    label: string,
    key: string,
    value: string,
    placeholder: string
  ) {
    const row = el.createEl("div", { cls: "paperforge-modal-field" });
    row.createEl("label", { cls: "paperforge-modal-label", text: label });
    const input = row.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "password", placeholder: placeholder || "" },
    });
    input.value = value;
    const settings = this.plugin.settings;
    input.addEventListener("input", () => {
      settings[key] = input.value;
      if (this._pendingSave) clearTimeout(this._pendingSave);
      this._pendingSave = setTimeout(() => {
        this.plugin.saveSettings();
        this._pendingSave = null;
      }, 500);
    });
  }

  /* ── Step 4: Install ── */
  _stepInstall(el: HTMLElement) {
    el.createEl("h2", { text: t("wizard_step4") });
    this._installLog = el.createEl("div", { cls: "paperforge-install-log" });

    const startBtn = el.createEl("button", {
      cls: "paperforge-step-btn mod-cta",
      text: t("install_btn"),
    });
    startBtn.addEventListener("click", () => this._runInstall(startBtn));
  }

  async _runInstall(btn: HTMLButtonElement) {
    btn.disabled = true;
    btn.textContent = t("install_btn_running");
    this._installLog.setText(t("install_validating") + "\n");
    this._log(t("install_validating"));

    const s = this.plugin.settings;
    const errors = this._validate();
    if (errors.length > 0) {
      this._log(t("validate_fail") + ":");
      errors.forEach((e) => this._log("  \u2717 " + e));
      btn.disabled = false;
      btn.textContent = t("install_btn_retry");
      return;
    }

    const runPython = (args: string[], options: any = {}) =>
      new Promise<{ stdout: string; stderr: string }>((resolve, reject) => {
        const { path: pyExe, args: pyExtra = [] } = this._resolvePython();
        const child = spawn(pyExe, [...pyExtra, ...args], {
          cwd: s.vault_path.trim(),
          env: paperforgeEnrichedEnv(),
          timeout: 120000,
          ...options,
        });
        let stdout = "";
        let stderr = "";
        child.stdout.on("data", (data) => {
          const text = data.toString("utf-8");
          stdout += text;
          if (options.logStdout) this._processSetupOutput(text);
        });
        child.stderr.on("data", (data) => {
          const text = data.toString("utf-8");
          stderr += text;
          this._log("[stderr] " + text.trim());
        });
        child.on("close", (code) => {
          code === 0
            ? resolve({ stdout, stderr })
            : reject(
                new Error(stderr.trim() || stdout.trim() || `exit code ${code}`)
              );
        });
        child.on("error", (err) => reject(err));
      });

    const setupArgs = [
      "-m",
      "paperforge",
      "--vault",
      s.vault_path.trim(),
      "setup",
      "--headless",
      "--system-dir",
      s.system_dir.trim(),
      "--resources-dir",
      s.resources_dir.trim(),
      "--literature-dir",
      s.literature_dir.trim(),
      "--base-dir",
      s.base_dir.trim(),
      "--agent",
      s.agent_platform || "opencode",
    ];
    if (s.zotero_data_dir && s.zotero_data_dir.trim())
      setupArgs.push("--zotero-data", s.zotero_data_dir.trim());
    // Issue #79: setup/install is forbidden from receiving secrets;
    // headless CLI uses its own .env / env contract independently.

    try {
      let hasPaperforge = true;
      try {
        await runPython(["-c", "import paperforge"]);
      } catch {
        hasPaperforge = false;
      }

      if (!hasPaperforge) {
        this._log(t("install_bootstrapping"));
        const ver = this.plugin.manifest.version;
        this._log(`[install] Trying PyPI: pip install paperforge==${ver}`);
        const pypiArgs = ["-m", "pip", "install", "--upgrade"];
        if (process.platform !== "win32") pypiArgs.push("--user");
        pypiArgs.push(`paperforge==${ver}`);
        try {
          await runPython(pypiArgs, { logStdout: true });
        } catch (pypiErr) {
          this._log(
            `[install] PyPI failed, falling back to git: git+https://...@v${ver}`
          );
          console.warn(
            "[PaperForge] PyPI install failed, falling back to git:",
            (pypiErr as Error).message?.slice(0, 200)
          );
          const gitArgs = ["-m", "pip", "install", "--upgrade"];
          if (process.platform !== "win32") gitArgs.push("--user");
          gitArgs.push(
            `git+https://github.com/LLLin000/PaperForge.git@v${ver}`
          );
          await runPython(gitArgs, { logStdout: true });
        }
      }

      await runPython(setupArgs, {
        logStdout: true,
        env: paperforgeEnrichedEnv(),
      });
      this._log(t("install_complete"));
      await this.plugin.saveSettings();
      if (this._onComplete) this._onComplete();
      setTimeout(() => {
        this._step = 5;
        this._render();
      }, 800);
    } catch (err) {
      console.error("PaperForge setup failed:", (err as Error).message);
      const errorMsg = this._formatSetupError((err as Error).message);
      this._log(t("install_failed") + errorMsg);

      // Add "Copy diagnostic" button
      const diagBtn = this._installLog.parentElement?.createEl("button", {
        cls: "paperforge-copy-diag-btn",
        text: t("error_copy_diagnostic") || "Copy diagnostic",
      });
      if (diagBtn) {
        const rawError = (err as Error).message;
        const pyInfo = this.plugin?.settings?.python_path || "auto";
        const pluginVer = this.plugin?.manifest?.version || "?";
        const osInfo = process.platform + " " + process.arch;
        let gitDir, resolvedPy;
        try {
          gitDir = resolveGitDir() || "(not found)";
        } catch (_) {
          gitDir = "(error)";
        }
        try {
          resolvedPy = this._resolvePython();
        } catch (_) {
          resolvedPy = null;
        }
        const pathLen = (process.env.PATH || "").length;
        const pathHasGit = (process.env.PATH || "")
          .toLowerCase()
          .includes("git");
        const diagnostic = [
          "[PaperForge Diagnostic]",
          "Category: " + errorMsg,
          "Plugin version: " + pluginVer,
          "Python: " + pyInfo,
          "Resolved Python: " + ((resolvedPy as any)?.path || "?"),
          "OS: " + osInfo,
          "Vault path: " + (s.vault_path || "?"),
          "--- Git ---",
          "Git dir (resolved): " + gitDir,
          "PATH length: " + pathLen + " chars",
          "PATH contains git: " + pathHasGit,
          "--- Raw error ---",
          rawError.slice(0, 2000),
        ].join("\n");
        diagBtn.addEventListener("click", () => {
          navigator.clipboard
            .writeText(diagnostic)
            .then(() => {
              diagBtn.setText(t("error_copied") || "Copied!");
              setTimeout(() => {
                diagBtn.setText(
                  t("error_copy_diagnostic") || "Copy diagnostic"
                );
              }, 3000);
            })
            .catch(() => {
              new Notice("[!!] Clipboard write failed", 6000);
            });
        });
      }

      btn.disabled = false;
      btn.textContent = t("install_btn_retry");
    }
  }

  _log(msg: string) {
    if (this._installLog) {
      this._installLog.setText(this._installLog.textContent + msg + "\n");
    }
  }

  _validate() {
    const errors: string[] = [];
    const s = this.plugin.settings;
    if (!s.vault_path || !s.vault_path.trim()) errors.push(t("validate_vault"));
    if (!s.resources_dir || !s.resources_dir.trim())
      errors.push(t("validate_resources"));
    if (!s.literature_dir || !s.literature_dir.trim())
      errors.push(t("validate_notes"));
    if (!s.base_dir || !s.base_dir.trim()) errors.push(t("validate_base"));
    // Issue #79: check configured flag; settings never hold raw key
    const _hasStoredOcrKey =
      this.plugin.settings._paddleocr_configured || false;
    if (!_hasStoredOcrKey)
      this._log("  ! " + t("validate_key") + " " + t("optional_later"));
    if (!s.zotero_data_dir || !s.zotero_data_dir.trim())
      this._log("  ! " + t("validate_zotero") + " " + t("optional_later"));
    return errors;
  }

  _processSetupOutput(text: string) {
    const lines = text.split("\n").filter(Boolean);
    for (const line of lines) {
      if (
        line.includes("[*]") ||
        line.includes("[OK]") ||
        line.includes("[FAIL]")
      ) {
        const clean = line
          .replace(/^\[\*\].*\d+:?\s*/, "")
          .replace(/^\[OK\]\s*/, "")
          .replace(/^\[FAIL\]\s*/, "");
        this._log("  " + clean);
      }
    }
  }

  _formatSetupError(raw: string) {
    if (
      process.platform === "darwin" &&
      /No module named ['"]?paperforge/i.test(raw)
    ) {
      return "PaperForge not installed \u2014 install Python from Homebrew or python.org (Apple CLT /Library/Developer/CommandLineTools python often fails); then: python3 -m pip install --user git+https://github.com/LLLin000/PaperForge.git";
    }
    const patterns = [
      // New: pip not found (before generic command not found)
      {
        match: /pip.*not found|No module named.*pip|command not found.*pip/i,
        msg: "pip not found",
      },
      // Existing: Python not found (keep broad)
      {
        match: /command not found|No such file|not recognized/i,
        msg: "Python not found",
      },
      // New: Network error (DNS resolution, connection refused, etc.)
      {
        match:
          /resolve host|getaddrinfo.*nodename|connect ETIMEDOUT|connect ECONNREFUSED|fetch failed|Network error|ENOTFOUND|ECONNREFUSED|ECONNRESET/i,
        msg: "Network error",
      },
      // New: SSL certificate
      {
        match:
          /certificate verify failed|SSL.*certificate|self.signed.cert|CERTIFICATE_VERIFY_FAILED/i,
        msg: "SSL certificate error",
      },
      // New: Disk full
      { match: /No space left on device|disk full|ENOSPC/i, msg: "Disk full" },
      // Existing: PaperForge not installed
      {
        match:
          /paperforge.*not found|cannot import|ModuleNotFoundError|No module named/i,
        msg: "PaperForge not installed",
      },
      // Existing + New: Permission denied (expand pattern)
      { match: /permission denied|EACCES|EPERM/i, msg: "Permission denied" },
      // Existing: Path not found
      { match: /ENOENT/i, msg: "Path not found" },
      // Existing: Timeout
      { match: /timeout|timed out/i, msg: "Timeout" },
    ];
    for (const p of patterns) {
      if (p.match.test(raw)) return p.msg;
    }
    const fallback = raw.split("\n").filter(Boolean).slice(0, 3).join(" | ");
    return fallback.slice(0, 200) || "Unknown error";
  }

  /* ── Step 5: Complete ── */
  _stepComplete(el: HTMLElement) {
    el.createEl("h2", { text: t("complete_title") });
    const summary = el.createEl("div", { cls: "paperforge-summary" });
    summary.createEl("div", {
      cls: "paperforge-summary-title",
      text: t("complete_summary"),
    });
    const s = this.plugin.settings;
    const vault = (this.app.vault.adapter as any).basePath;
    const items = [
      { label: t("dir_vault"), val: vault },
      { label: t("dir_resources"), val: `${vault}/${s.resources_dir}` },
      {
        label: t("dir_notes"),
        val: `${vault}/${s.resources_dir}/${s.literature_dir}`,
      },
      { label: t("dir_base"), val: `${vault}/${s.base_dir}` },
      { label: t("dir_system"), val: `${vault}/${s.system_dir}` },
      // Issue #79: check configured flag; settings never hold raw key
      {
        label: "API Key",
        val: this.plugin.settings._paddleocr_configured
          ? t("api_key_set")
          : t("api_key_missing"),
      },
      { label: t("field_zotero_data"), val: s.zotero_data_dir || t("not_set") },
    ];
    for (const item of items) {
      const row = summary.createEl("div", { cls: "paperforge-summary-row" });
      row.createEl("span", {
        cls: "paperforge-summary-label",
        text: item.label,
      });
      row.createEl("span", { cls: "paperforge-summary-value", text: item.val });
    }
    // PaperForge version (fetched async)
    const verRow = summary.createEl("div", { cls: "paperforge-summary-row" });
    verRow.createEl("span", {
      cls: "paperforge-summary-label",
      text: "PaperForge",
    });
    const verVal = verRow.createEl("span", {
      cls: "paperforge-summary-value",
      text: "\u2014",
    });
    {
      const vp = vault;
      const { path: pythonExe, args: extraArgs = [] } = this._resolvePython();
      execFile(
        pythonExe,
        [
          ...extraArgs,
          "-c",
          "import paperforge; print(paperforge.__version__)",
        ],
        { cwd: vp, timeout: 10000 },
        (err, stdout) => {
          if (!err && stdout) verVal.textContent = "v" + stdout.trim();
        }
      );
    }
    for (const item of items) {
      const row = summary.createEl("div", { cls: "paperforge-summary-row" });
      row.createEl("span", {
        cls: "paperforge-summary-label",
        text: item.label,
      });
      row.createEl("span", { cls: "paperforge-summary-value", text: item.val });
    }
    el.createEl("h3", { text: t("complete_next") });
    const nextList = el.createEl("div", { cls: "paperforge-nextsteps" });
    const steps: [string, string][] = [
      [t("complete_step4"), t("complete_step4_desc")],
      [
        "",
        `${t("complete_export_path")} ${vault}/${s.system_dir}/PaperForge/exports/`,
      ],
      [t("complete_step1"), t("complete_step1_desc")],
      [t("complete_step2"), t("complete_step2_desc")],
      [t("complete_step3"), t("complete_step3_desc")],
    ];
    for (const [title, desc] of steps) {
      const item = nextList.createEl("div", {
        cls: "paperforge-nextstep-item",
      });
      if (title) item.createEl("strong", { text: title });
      item.createEl("span", { text: desc });
    }
  }
}

/* ── Destructive Confirmation Modal (Issue #80) ── */

export interface ConfirmModalConfig {
  title: string;
  effectLabel: string;
  confirmLabel?: string;
  cancelLabel?: string;
}

function _trapFocus(container: HTMLElement, e: KeyboardEvent): void {
  if (e.key !== "Tab") return;
  const focusable = container.querySelectorAll<HTMLElement>(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  if (focusable.length === 0) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (e.shiftKey) {
    if (document.activeElement === first) {
      e.preventDefault();
      last.focus();
    }
  } else {
    if (document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }
}

export class PaperForgeConfirmModal extends Modal {
  private _config: ConfirmModalConfig;
  private _onConfirm: (() => void) | undefined;
  private _returnFocusEl: HTMLElement | null = null;
  private _inertedEls: HTMLElement[] = [];
  private _boundKeydown!: (e: KeyboardEvent) => void;

  constructor(app: App, config: ConfirmModalConfig, onConfirm?: () => void) {
    super(app);
    this._config = config;
    this._onConfirm = onConfirm;
    this._returnFocusEl = document.activeElement as HTMLElement | null;
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.addClass("paperforge-modal");
    contentEl.addClass("paperforge-confirm-modal");
    contentEl.setAttr("role", "alertdialog");
    contentEl.setAttr("aria-modal", "true");

    const modalContainer = (contentEl as unknown as HTMLElement).closest(
      ".modal-container"
    );
    if (modalContainer) {
      const bg = modalContainer.parentElement;
      if (bg) {
        for (const child of Array.from(bg.children)) {
          if (child !== modalContainer && !child.hasAttribute("inert")) {
            child.setAttribute("inert", "");
            this._inertedEls.push(child as HTMLElement);
          }
        }
      }
    }

    contentEl.createEl("h2", { text: this._config.title });
    const effect = contentEl.createEl("div", {
      cls: "paperforge-confirm-effect",
    });
    effect.createEl("span", {
      cls: "paperforge-confirm-effect-label",
      text: "Effect: ",
    });
    effect.createEl("span", { text: this._config.effectLabel });

    const btnRow = contentEl.createEl("div", {
      cls: "paperforge-confirm-actions",
    });
    const cancelBtn = btnRow.createEl("button", {
      text:
        this._config.cancelLabel || t("maintenance_confirm_cancel") || "Cancel",
    });
    cancelBtn.addEventListener("click", () => this.close());

    const confirmBtn = btnRow.createEl("button", {
      cls: "mod-warning",
      text:
        this._config.confirmLabel || t("maintenance_confirm_ok") || "Proceed",
    });
    confirmBtn.addEventListener("click", () => {
      if (this._onConfirm) this._onConfirm();
      this.close();
    });

    this._boundKeydown = (e: KeyboardEvent) =>
      _trapFocus(contentEl as unknown as HTMLElement, e);
    contentEl.addEventListener("keydown", this._boundKeydown);
    cancelBtn.focus();
  }

  onClose() {
    for (const el of this._inertedEls) {
      el.removeAttribute("inert");
    }
    this._inertedEls.length = 0;
    if (this._boundKeydown) {
      this.contentEl.removeEventListener("keydown", this._boundKeydown);
    }
    this.contentEl.empty();
    if (
      this._returnFocusEl &&
      typeof this._returnFocusEl.focus === "function"
    ) {
      try {
        this._returnFocusEl.focus();
      } catch {}
    }
  }
}

/* ── OCR Issue Draft Modal (Issue #80) ── */

export interface IssueDraftFields {
  title: string;
  body: string;
  labels: string[];
}

const REDACT_PATTERNS: Array<{
  pattern: RegExp;
  label: string;
  class_: string;
}> = [
  { pattern: /sk-[A-Za-z0-9]{16,}/g, label: "API key", class_: "credential" },
  {
    pattern: /[A-Za-z0-9+/]{20,}={0,2}/g,
    label: "Credential token",
    class_: "credential",
  },
  {
    pattern: /api[_-]?key[=:]\s*['"]?\S+['"]?/gi,
    label: "API key",
    class_: "credential",
  },
  {
    pattern: /token[=:]\s*['"]?\S+['"]?/gi,
    label: "Token",
    class_: "credential",
  },
  {
    pattern: /[A-Za-z]:\\[^"'\n,;]+/gi,
    label: "Absolute path",
    class_: "vault-path",
  },
  {
    pattern: /(?<=^|\s)\/[^/\s][^"'\n,;]*/g,
    label: "Absolute path",
    class_: "vault-path",
  },
  {
    pattern: /Zotero[^"'\s,;]*/gi,
    label: "Zotero path",
    class_: "zotero-path",
  },
  { pattern: /Paper:\s*[^\n]+/gi, label: "Paper title", class_: "paper-title" },
  { pattern: /Title:\s*[^\n]+/gi, label: "Paper title", class_: "paper-title" },
];

function redactText(text: string): {
  clean: string;
  redactions: Array<{ label: string; class_: string; count: number }>;
} {
  const byClass: Record<
    string,
    { label: string; class_: string; count: number }
  > = {};
  let clean = text;
  for (const { pattern, label, class_ } of REDACT_PATTERNS) {
    let count = 0;
    clean = clean.replace(pattern, () => {
      count++;
      return "[REDACTED]";
    });
    if (count > 0) {
      if (!byClass[class_]) {
        byClass[class_] = { label, class_, count: 0 };
      }
      byClass[class_].count += count;
    }
  }
  return { clean, redactions: Object.values(byClass) };
}

export function buildRedactedDraft(
  reasonCode: string,
  reasonText: string,
  paperCount: number,
  _vaultPath: string
): IssueDraftFields {
  const title = `OCR: ${reasonCode} (${paperCount} papers)`;
  const body = [
    `## Diagnostic Summary`,
    `- Reason: ${reasonCode}`,
    `- Detail: ${reasonText}`,
    `- Papers affected: ${paperCount}`,
    "",
    `## Environment`,
    `- Vault: [REDACTED]`,
    `- Plugin version: PaperForge`,
    "",
    `## Steps to reproduce`,
    `1. Run OCR on affected papers`,
    `2. Review output quality`,
    `3. Review this draft, then open GitHub to submit`,
  ].join("\n");
  const labels = ["ocr", "quality", "auto-generated"];
  return { title, body, labels };
}

export class PaperForgeIssueDraftModal extends Modal {
  private _draft: IssueDraftFields;
  private _githubUrl: string;
  private _titleInput!: HTMLInputElement;
  private _bodyTextarea!: HTMLTextAreaElement;
  private _returnFocusEl: HTMLElement | null = null;
  private _inertedEls: HTMLElement[] = [];
  private _boundKeydown!: (e: KeyboardEvent) => void;

  constructor(app: App, draft: IssueDraftFields, githubUrl: string) {
    super(app);
    this._draft = draft;
    this._githubUrl = githubUrl;
    this._returnFocusEl = document.activeElement as HTMLElement | null;
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.addClass("paperforge-modal");
    contentEl.addClass("paperforge-issue-draft-modal");
    contentEl.setAttr("role", "dialog");
    contentEl.setAttr("aria-modal", "true");

    const modalContainer = (contentEl as unknown as HTMLElement).closest(
      ".modal-container"
    );
    if (modalContainer) {
      const bg = modalContainer.parentElement;
      if (bg) {
        for (const child of Array.from(bg.children)) {
          if (child !== modalContainer && !child.hasAttribute("inert")) {
            child.setAttribute("inert", "");
            this._inertedEls.push(child as HTMLElement);
          }
        }
      }
    }

    contentEl.createEl("h2", {
      text: t("maintenance_issue_draft_title") || "OCR Issue Draft",
    });
    contentEl.createEl("p", {
      cls: "paperforge-issue-draft-desc",
      text:
        t("maintenance_issue_draft_preview") ||
        "Review the issue draft below before opening GitHub.",
    });

    const titleRow = contentEl.createEl("div", {
      cls: "paperforge-issue-draft-field",
    });
    titleRow.createEl("label", { text: "Title" });
    const safeTitle = redactText(this._draft.title).clean;
    this._titleInput = titleRow.createEl("input", {
      cls: "paperforge-issue-draft-input",
      attr: { type: "text", value: safeTitle },
    }) as unknown as HTMLInputElement;

    const bodyRow = contentEl.createEl("div", {
      cls: "paperforge-issue-draft-field",
    });
    bodyRow.createEl("label", { text: "Body" });
    const safeBody = redactText(this._draft.body).clean;
    this._bodyTextarea = bodyRow.createEl("textarea", {
      cls: "paperforge-issue-draft-textarea",
      attr: { rows: "12" },
      text: safeBody,
    }) as unknown as HTMLTextAreaElement;

    const { redactions } = redactText(
      this._draft.title + "\n" + this._draft.body
    );
    const preview = contentEl.createEl("div", {
      cls: "paperforge-issue-draft-preview",
    });

    const includedEl = preview.createEl("div", {
      cls: "paperforge-issue-draft-included",
    });
    includedEl.createEl("span", {
      cls: "paperforge-issue-draft-preview-label",
      text: (t("maintenance_issue_draft_included") || "Included") + ": ",
    });
    includedEl.createEl("span", {
      text: `Title, Body, Labels (${this._draft.labels.join(", ")})`,
    });

    const redactedEl = preview.createEl("div", {
      cls: "paperforge-issue-draft-redacted",
    });
    redactedEl.createEl("span", {
      cls: "paperforge-issue-draft-preview-label",
      text: (t("maintenance_issue_draft_redacted") || "Redacted") + ": ",
    });
    redactedEl.createEl("span", {
      text:
        "Credentials, vault/Zotero paths, paper titles, paper content are excluded" +
        (redactions.length > 0
          ? " (" +
            redactions.map((r) => `${r.count} ${r.label}`).join(", ") +
            ")"
          : ""),
    });

    const btnRow = contentEl.createEl("div", {
      cls: "paperforge-issue-draft-actions",
    });
    const closeBtn = btnRow.createEl("button", {
      text: t("maintenance_confirm_cancel") || "Cancel",
    });
    closeBtn.addEventListener("click", () => this.close());

    const openBtn = btnRow.createEl("button", {
      cls: "mod-cta",
      text: t("maintenance_issue_draft_open_github") || "Open GitHub Issue",
    });
    openBtn.addEventListener("click", () => {
      const finalTitle = encodeURIComponent(
        redactText(this._titleInput.value).clean
      );
      const finalBody = encodeURIComponent(
        redactText(this._bodyTextarea.value).clean
      );
      const labels = encodeURIComponent(this._draft.labels.join(","));
      const url = `${this._githubUrl}?title=${finalTitle}&body=${finalBody}&labels=${labels}`;
      window.open(url, "_blank", "noopener,noreferrer");
    });

    this._boundKeydown = (e: KeyboardEvent) =>
      _trapFocus(contentEl as unknown as HTMLElement, e);
    contentEl.addEventListener("keydown", this._boundKeydown);
    this._titleInput.focus();
  }

  onClose() {
    for (const el of this._inertedEls) {
      el.removeAttribute("inert");
    }
    this._inertedEls.length = 0;
    if (this._boundKeydown) {
      this.contentEl.removeEventListener("keydown", this._boundKeydown);
    }
    this.contentEl.empty();
    if (
      this._returnFocusEl &&
      typeof this._returnFocusEl.focus === "function"
    ) {
      try {
        this._returnFocusEl.focus();
      } catch {}
    }
  }
}
