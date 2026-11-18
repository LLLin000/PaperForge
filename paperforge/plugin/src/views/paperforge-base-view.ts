import * as obsidian from "obsidian";
import { Notice } from "obsidian";
import { VIEW_TYPE_PF_BASE_TABLE } from "../constants";
import { t } from "../i18n";
import type { ActionScope } from "../client/action-contract";
import type {
  BasePaperRowDto,
  BaseTableSnapshotDto,
  PaperForgeClient,
} from "../client/paperforge-client";

export interface PaperForgeBasesHost {
  app: obsidian.App;
  getClient(): PaperForgeClient;
  getBaseSnapshotCache(): BaseTableSnapshotDto | null;
  refreshBaseSnapshot(
    changedKeys?: string[]
  ): Promise<BaseTableSnapshotDto | null>;
  isOcrRunningForKey(key: string): boolean;
  openPaperPdf(
    paperKey: string,
    opts?: { page?: number; annId?: string }
  ): Promise<void>;
  requestOcrRun(scopeOrSkipConfirm?: ActionScope | boolean): Promise<void>;
  triggerManualSync(): void;
  openOcrDiagnostic(paperKey?: string): void;
  _ocrProgress?: { current: number; total: number; key: string };
}

class FallbackBaseComponent {
  load(): void {}
  unload(): void {}
}

// Runtime-safe base class: Obsidian 1.10+ provides BasesView; Vitest mocks may throw on unmocked property access.
function resolveRuntimeBasesView(): new (
  ...args: unknown[]
) => obsidian.Component {
  const mod = obsidian as Record<string, unknown>;
  try {
    if (typeof mod.BasesView === "function") {
      return mod.BasesView as new (...args: unknown[]) => obsidian.Component;
    }
  } catch {
    // Vitest mock proxy throws when BasesView is not defined on mocked module
  }
  try {
    if (typeof mod.Component === "function") {
      return mod.Component as new (...args: unknown[]) => obsidian.Component;
    }
  } catch {
    // Vitest mock proxy throws when Component is omitted from minimal mocks
  }
  return FallbackBaseComponent as unknown as new (
    ...args: unknown[]
  ) => obsidian.Component;
}

const RuntimeBasesView = resolveRuntimeBasesView();

function mkEl<K extends keyof HTMLElementTagNameMap>(
  parent: HTMLElement,
  tag: K,
  opts?: { cls?: string; text?: string; attr?: Record<string, string> }
): HTMLElementTagNameMap[K] {
  const el = (parent.ownerDocument || document).createElement(tag);
  if (opts?.cls) {
    for (const c of opts.cls.split(/\s+/).filter(Boolean)) {
      el.classList.add(c);
    }
  }
  if (opts?.text !== undefined) {
    el.textContent = opts.text;
  }
  if (opts?.attr) {
    for (const [k, v] of Object.entries(opts.attr)) {
      el.setAttribute(k, v);
    }
  }
  parent.appendChild(el);
  return el;
}

function resolveRowForEntry(
  entry: obsidian.BasesEntry,
  rowsByKey: Record<string, BasePaperRowDto>
): BasePaperRowDto | null {
  try {
    const val = entry.getValue?.("note.zotero_key" as obsidian.BasesPropertyId);
    if (val !== null && val !== undefined) {
      const rawData = (val as unknown as { data?: unknown }).data;
      const raw = typeof rawData === "string" ? rawData : String(val);
      const cleaned = raw.trim().replace(/^["']|["']$/g, "");
      if (cleaned && cleaned !== "null" && rowsByKey[cleaned]) {
        return rowsByKey[cleaned];
      }
    }
  } catch {
    // Ignore malformed formula/property values on individual notes
  }
  const entryPath = (entry.file?.path || "").replace(/\\/g, "/");
  if (entryPath) {
    for (const row of Object.values(rowsByKey)) {
      if (
        row.main_note_path &&
        row.main_note_path.replace(/\\/g, "/") === entryPath
      ) {
        return row;
      }
    }
  }
  const baseName = entry.file?.basename || "";
  if (baseName) {
    if (rowsByKey[baseName]) return rowsByKey[baseName];
    const prefix = baseName.split(/\s+-\s+/)[0]?.trim();
    if (prefix && rowsByKey[prefix]) return rowsByKey[prefix];
  }
  return null;
}

export class PaperForgeBasesView extends RuntimeBasesView {
  type = VIEW_TYPE_PF_BASE_TABLE;
  declare app: obsidian.App;
  declare data: obsidian.BasesQueryResult | undefined;
  declare config: obsidian.BasesViewConfig | undefined;

  containerEl: HTMLElement;
  plugin: PaperForgeBasesHost;
  private _loadingSnapshot = false;
  private _stateRef: obsidian.EventRef | null = null;
  private _inflightFlags = new Set<string>();

  constructor(
    controller: obsidian.QueryController,
    containerEl: HTMLElement,
    plugin: PaperForgeBasesHost
  ) {
    super(controller);
    this.containerEl = containerEl;
    this.plugin = plugin;
  }

  onload(): void {
    const app = this.app ?? this.plugin.app;
    const ws = app?.workspace as unknown as {
      on?: (name: string, cb: () => void) => obsidian.EventRef;
    };
    if (typeof ws?.on === "function") {
      this._stateRef = ws.on("paperforge:state-changed", () => {
        this.render();
      });
    }
    if (!this.plugin.getBaseSnapshotCache() && !this._loadingSnapshot) {
      this._loadingSnapshot = true;
      void this.plugin
        .refreshBaseSnapshot()
        .catch(() => null)
        .finally(() => {
          this._loadingSnapshot = false;
          this.render();
        });
    }
    this.render();
  }

  onunload(): void {
    const app = this.app ?? this.plugin.app;
    const ws = app?.workspace as unknown as {
      offref?: (ref: obsidian.EventRef) => void;
    };
    if (this._stateRef && typeof ws?.offref === "function") {
      ws.offref(this._stateRef);
    }
    this._stateRef = null;
  }

  onDataUpdated(): void {
    if (!this.plugin.getBaseSnapshotCache() && !this._loadingSnapshot) {
      this._loadingSnapshot = true;
      void this.plugin
        .refreshBaseSnapshot()
        .catch(() => null)
        .finally(() => {
          this._loadingSnapshot = false;
          this.render();
        });
    }
    this.render();
  }

  private _collectRows(
    snapshot: BaseTableSnapshotDto | null
  ): BasePaperRowDto[] {
    const rowsByKey = snapshot?.rows ?? {};
    const entries = this.data?.data;
    if (Array.isArray(entries)) {
      const resolved: BasePaperRowDto[] = [];
      const seen = new Set<string>();
      for (const entry of entries) {
        const matched = resolveRowForEntry(entry, rowsByKey);
        if (matched && !seen.has(matched.zotero_key)) {
          seen.add(matched.zotero_key);
          resolved.push(matched);
          continue;
        }
        // Fallback stub when Base matches a note before snapshot finishes loading
        const baseName = entry.file?.basename || "";
        const guessedKey = baseName.split(/\s+-\s+/)[0]?.trim() || baseName;
        if (guessedKey && !seen.has(guessedKey)) {
          seen.add(guessedKey);
          resolved.push({
            zotero_key: guessedKey,
            title: baseName || entry.file?.path || guessedKey,
            first_author: "",
            year: "",
            journal: "",
            impact_factor: "",
            domain: "",
            has_pdf: false,
            do_ocr: false,
            analyze: false,
            ocr_status: snapshot ? "unknown" : "pending",
            deep_reading_status: "pending",
            main_note_path: entry.file?.path || "",
            user_ann_count: 0,
            agent_ann_count: 0,
            memory_facet_count: 0,
            memory_updated_at: "",
            needs_diagnostic: false,
          });
        }
      }
      return resolved;
    }
    return Object.values(rowsByKey);
  }

  private _renderStatusBadge(cell: HTMLElement, row: BasePaperRowDto): void {
    if (this.plugin.isOcrRunningForKey(row.zotero_key)) {
      const prog = this.plugin._ocrProgress;
      const pctLabel =
        prog && prog.total > 0 ? ` (${prog.current}/${prog.total})` : "";
      mkEl(cell, "span", {
        cls: "pf-base-badge is-running",
        text: `⚡ OCR${pctLabel}`,
      });
    } else {
      const status = row.ocr_status || "pending";
      const cls =
        status === "done"
          ? "is-ok"
          : status === "failed" || status === "done_incomplete"
            ? "is-fail"
            : status === "processing"
              ? "is-running"
              : "is-pending";
      const label =
        status === "done"
          ? "✓ OCR"
          : status === "nopdf"
            ? "无 PDF"
            : status === "failed"
              ? "✗ OCR 失败"
              : status === "done_incomplete"
                ? "⚠ 不完整"
                : status === "processing"
                  ? "⚡ 处理中"
                  : "○ 待 OCR";
      mkEl(cell, "span", {
        cls: `pf-base-badge ${cls}`,
        text: label,
      });
    }
    if (row.deep_reading_status === "done") {
      mkEl(cell, "span", {
        cls: "pf-base-badge is-ok",
        text: "精读 ✓",
      });
    }
  }

  private _renderFlagCheckbox(
    cell: HTMLElement,
    row: BasePaperRowDto,
    field: "do_ocr" | "analyze",
    label: string
  ): void {
    const wrap = mkEl(cell, "label", { cls: "pf-base-flag-label" });
    const input = mkEl(wrap, "input", {
      attr: {
        type: "checkbox",
        "data-pf-flag": field,
        "data-paper-key": row.zotero_key,
        "aria-label": `${field} ${row.zotero_key}`,
      },
    });
    input.checked = Boolean(row[field]);
    const inflightId = `${row.zotero_key}:${field}`;
    input.disabled = this._inflightFlags.has(inflightId);
    mkEl(wrap, "span", { text: label });

    input.addEventListener("change", () => {
      const next = input.checked;
      input.disabled = true;
      this._inflightFlags.add(inflightId);
      void this.plugin
        .getClient()
        .setNoteFlag(row.zotero_key, field, next)
        .then(async () => {
          row[field] = next;
          await this.plugin
            .refreshBaseSnapshot([row.zotero_key])
            .catch(() => null);
        })
        .catch((err: unknown) => {
          input.checked = !next;
          new Notice(
            `Flag update failed: ${err instanceof Error ? err.message : String(err)}`
          );
        })
        .finally(() => {
          this._inflightFlags.delete(inflightId);
          input.disabled = false;
        });
    });
  }

  private _openNote(notePath: string): void {
    if (!notePath) {
      new Notice(t("paper_note_missing") || "Note path unavailable.");
      return;
    }
    const app = this.app ?? this.plugin.app;
    void app.workspace?.openLinkText?.(notePath, "");
  }

  render(): void {
    const root = this.containerEl;
    if (!root) return;
    root.innerHTML = "";
    root.classList.add("pf-base-view-root");

    const snapshot = this.plugin.getBaseSnapshotCache();
    const rows = this._collectRows(snapshot);

    // 1. Top summary + quick-action toolbar (works alongside native Base Filter/Sort toolbar)
    const toolbar = mkEl(root, "div", { cls: "pf-base-toolbar" });
    const statsEl = mkEl(toolbar, "div", { cls: "pf-base-toolbar-stats" });
    const doneCount = rows.filter((r) => r.ocr_status === "done").length;
    const queuedCount = rows.filter((r) => r.do_ocr).length;
    mkEl(statsEl, "span", {
      cls: "pf-base-stat-pill",
      text: `${rows.length} 篇`,
    });
    mkEl(statsEl, "span", {
      cls: "pf-base-stat-pill",
      text: `OCR ${doneCount}/${rows.length}`,
    });
    mkEl(statsEl, "span", {
      cls: "pf-base-stat-pill",
      text: `待处理队列 ${queuedCount}`,
    });
    if (snapshot) {
      mkEl(statsEl, "span", {
        cls: "pf-base-seq-tag",
        text: `seq #${snapshot.seq}`,
      });
    }

    const actionsBar = mkEl(toolbar, "div", { cls: "pf-base-toolbar-actions" });
    const runAllBtn = mkEl(actionsBar, "button", {
      cls: "pf-btn mod-cta",
      text: t("base_run_pending_ocr") || "⚡ 运行待处理 OCR",
      attr: { type: "button", "data-pf-testid": "base-run-pending-ocr" },
    });
    runAllBtn.addEventListener("click", () => {
      void this.plugin.requestOcrRun({ kind: "all" });
    });

    const syncBtn = mkEl(actionsBar, "button", {
      cls: "pf-btn pf-btn-secondary",
      text: t("base_sync_library") || "🔄 同步文献库",
      attr: { type: "button", "data-pf-testid": "base-sync-library" },
    });
    syncBtn.addEventListener("click", () => {
      this.plugin.triggerManualSync();
    });

    if (rows.length === 0) {
      mkEl(root, "div", {
        cls: "pf-base-empty",
        text: this._loadingSnapshot
          ? t("pdf_loading") || "Loading..."
          : t("base_empty_hint") || "当前筛选条件下暂无文献。",
      });
      return;
    }

    // 2. Interactive Literature Workbench Table
    const wrap = mkEl(root, "div", { cls: "pf-base-table-wrap" });
    const table = mkEl(wrap, "table", { cls: "pf-base-table" });
    const thead = mkEl(table, "thead");
    const headRow = mkEl(thead, "tr");
    for (const colTitle of [
      t("base_col_paper") || "文献",
      t("base_col_flags") || "队列意图",
      t("base_col_status") || "处理状态 (只读)",
      t("base_col_memory") || "认知沉淀",
      t("base_col_actions") || "操作",
    ]) {
      mkEl(headRow, "th", { text: colTitle });
    }

    const tbody = mkEl(table, "tbody");
    for (const row of rows) {
      const tr = mkEl(tbody, "tr", {
        cls: "pf-base-row",
        attr: { "data-paper-key": row.zotero_key },
      });

      // Column 1: Title & Bibliographic subline
      const paperTd = mkEl(tr, "td", { cls: "pf-base-cell-paper" });
      const titleBtn = mkEl(paperTd, "button", {
        cls: "pf-base-title-link",
        text: row.title || row.zotero_key,
        attr: { type: "button", title: row.zotero_key },
      });
      titleBtn.addEventListener("click", () =>
        this._openNote(row.main_note_path)
      );

      const metaBits = [
        row.first_author,
        row.year,
        row.journal,
        row.impact_factor ? `IF ${row.impact_factor}` : "",
        row.domain,
      ].filter(Boolean);
      if (metaBits.length > 0) {
        mkEl(paperTd, "div", {
          cls: "pf-base-submeta",
          text: metaBits.join(" · "),
        });
      }

      // Column 2: Physical Write Separation checkboxes (`do_ocr`, `analyze`)
      const flagsTd = mkEl(tr, "td", { cls: "pf-base-cell-flags" });
      this._renderFlagCheckbox(flagsTd, row, "do_ocr", "OCR");
      this._renderFlagCheckbox(flagsTd, row, "analyze", "精读");

      // Column 3: Read-Only Live Machine Status
      const statusTd = mkEl(tr, "td", { cls: "pf-base-cell-status" });
      this._renderStatusBadge(statusTd, row);

      // Column 4: Cognitive Memory Counts (read-only pills from SQLite/snapshot)
      const memTd = mkEl(tr, "td", { cls: "pf-base-cell-memory" });
      const cogWrap = mkEl(memTd, "div", { cls: "pf-base-cog-pills" });
      if (row.memory_facet_count > 0) {
        mkEl(cogWrap, "span", {
          cls: "pf-base-cog-pill is-memory",
          text: `🧠 ${row.memory_facet_count}`,
          attr: { title: "Living Paper Memory facets" },
        });
      }
      if (row.user_ann_count > 0) {
        mkEl(cogWrap, "span", {
          cls: "pf-base-cog-pill is-user",
          text: `🖍️ ${row.user_ann_count}`,
          attr: { title: "My PDF highlights" },
        });
      }
      if (row.agent_ann_count > 0) {
        mkEl(cogWrap, "span", {
          cls: "pf-base-cog-pill is-agent",
          text: `🤖 ${row.agent_ann_count}`,
          attr: { title: "AI PDF annotations" },
        });
      }
      if (
        row.memory_facet_count === 0 &&
        row.user_ann_count === 0 &&
        row.agent_ann_count === 0
      ) {
        mkEl(cogWrap, "span", { cls: "pf-base-muted", text: "—" });
      }

      // Column 5: Interactive Actions
      const actTd = mkEl(tr, "td", { cls: "pf-base-cell-actions" });
      if (row.has_pdf) {
        const pdfBtn = mkEl(actTd, "button", {
          cls: "pf-btn pf-btn-secondary pf-base-act-btn",
          text: "📄 PDF",
          attr: { type: "button", "data-pf-testid": "base-open-pdf" },
        });
        pdfBtn.addEventListener("click", () => {
          void this.plugin.openPaperPdf(row.zotero_key);
        });
      }
      if (row.main_note_path) {
        const noteBtn = mkEl(actTd, "button", {
          cls: "pf-btn pf-btn-secondary pf-base-act-btn",
          text: "📝 笔记",
          attr: { type: "button", "data-pf-testid": "base-open-note" },
        });
        noteBtn.addEventListener("click", () =>
          this._openNote(row.main_note_path)
        );
      }
      if (row.has_pdf && row.ocr_status !== "done") {
        const ocrBtn = mkEl(actTd, "button", {
          cls: "pf-btn pf-btn-secondary pf-base-act-btn",
          text: "⚡ OCR",
          attr: { type: "button", "data-pf-testid": "base-run-ocr" },
        });
        ocrBtn.addEventListener("click", () => {
          void this.plugin.requestOcrRun({
            kind: "papers",
            keys: [row.zotero_key],
          });
        });
      }
      if (row.needs_diagnostic) {
        const diagBtn = mkEl(actTd, "button", {
          cls: "pf-btn pf-btn-secondary pf-base-act-btn",
          text: "🔧 诊断",
          attr: { type: "button", "data-pf-testid": "base-open-diag" },
        });
        diagBtn.addEventListener("click", () => {
          this.plugin.openOcrDiagnostic(row.zotero_key);
        });
      }
    }
  }
}
