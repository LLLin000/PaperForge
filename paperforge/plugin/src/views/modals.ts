import { Modal, App, Notice } from "obsidian";
import * as fs from "fs";
import * as path from "path";
import * as https from "https";
import { t } from "../i18n";
import { PaperForgeSettings } from "../constants";
import {
  RuntimeBootstrap,
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

export interface OrphanItem {
  citation_key?: string;
  key: string;
  has_pdf?: boolean;
  collection_path?: string;
  title?: string;
  authors?: string;
  year?: string;
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
      const keys = selected.map((o) => o.key);
      const plugin = ((this.app as any).plugins?.plugins as any)?.[
        "paperforge"
      ];
      const client = plugin?.getClient?.();
      if (!client) {
        new Notice("PaperForge: client unavailable");
        this.close();
        return;
      }

      client
        .describeAction("library.prune")
        .then((desc: any) => {
          const actionId = desc?.action_id ?? "library.prune";
          const confirm =
            desc?.confirmation === "required" ? actionId : undefined;
          return client.runAction({
            action_id: actionId,
            scope: { kind: "papers", keys },
            confirm,
          });
        })
        .then((res: any) => {
          if (res.ok) {
            const deleted = (res.payload?.data as any)?.deleted ?? keys;
            new Notice("Deleted " + deleted.length + " orphan workspace(s)");
          } else {
            new Notice("PaperForge: prune failed");
          }
          this.close();
        })
        .catch(() => {
          new Notice("PaperForge: prune failed");
          this.close();
        });
    });
  }

  onClose() {
    this.contentEl.empty();
  }
}

/* ── Orphan state checker ── */

export function checkOrphanState(app: App, plugin: IPluginRef, vp: string) {
  console.log("[PF] checkOrphanState called");
  const client = (plugin as any)?.getClient?.();
  if (!client) {
    console.log("[PF] orphan file NOT FOUND");
    return;
  }

  // The residual report is Python's authority for "this key is in a carrier but
  // gone from Zotero", and it is exactly what `library.prune` acts on. The
  // previous implementation read a `deficits[].paper_keys` field on the
  // reconcile payload — a shape reconcile never emits — so the modal could
  // never open (#222).
  client
    .probe("lineage")
    .then((envelope: any) => {
      const papers: Array<{ key?: string; title?: string }> = Array.isArray(
        envelope?.residuals?.papers
      )
        ? envelope.residuals.papers
        : [];
      const resolved = papers
        .map((p: any) => ({
          key: String(p?.key ?? "").trim(),
          title: p?.title,
        }))
        .filter((p: { key: string }) => p.key.length > 0);
      if (resolved.length > 0) {
        console.log("[PF] orphan file FOUND");
        const orphans: OrphanItem[] = resolved.map(
          (p: { key: string; title?: string }) => ({
            key: p.key,
            title: p.title || p.key,
          })
        );
        new PaperForgeOrphanModal(app, orphans, vp, null).open();
      } else {
        console.log("[PF] orphan file NOT FOUND");
      }
    })
    .catch((err: any) => {
      // A failure to detect must be visible: a silent catch made a broken
      // reconcile indistinguishable from "no orphans" in the field log.
      console.log("[PF] checkOrphanState exception:", err?.message || err);
      new Notice("PaperForge: orphan detection failed");
    });
}

/* ── Setup Wizard Modal ── */

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
      text: t("confirm_effect_label") + ": ",
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
