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
import { createPfIconBtn, setPfIcon } from "./icons";
import {
  bindObsidianHoverPreview,
  openUnifiedPaperContextMenu,
} from "./paper-interactions";

export interface BaseFilterState {
  query?: string;
  domain?: string;
  collection?: string;
  status?: string;
  minIf?: number;
}

export interface PaperForgeBasesHost {
  app: obsidian.App;
  getClient(): PaperForgeClient;
  getBaseSnapshotCache(): BaseTableSnapshotDto | null;
  getBaseFilters?(viewKey: string): BaseFilterState;
  setBaseFilters?(viewKey: string, next: BaseFilterState): void;
  refreshBaseSnapshot(
    changedKeys?: string[]
  ): Promise<BaseTableSnapshotDto | null>;
  isOcrRunningForKey(key: string): boolean;
  openPaperPdf(
    paperKey: string,
    opts?: { page?: number; annId?: string }
  ): Promise<void>;
  openPaperSplitReading?: (
    paperKey: string,
    notePath?: string
  ) => Promise<void>;
  requestOcrRun(scopeOrSkipConfirm?: ActionScope | boolean): Promise<void>;
  triggerManualSync(): void;
  openOcrDiagnostic(paperKey?: string): void;
  _ocrProgress?: { current: number; total: number; key: string };
}

class FallbackBaseComponent {
  load(): void {}
  unload(): void {}
}

// Runtime-safe base class: Obsidian 1.10+ provides BasesView; Vitest mocks may omit it.
function resolveRuntimeBasesView(): new (
  ...args: unknown[]
) => obsidian.Component {
  const mod = obsidian as Record<string, unknown>;
  try {
    if (typeof mod.BasesView === "function") {
      return mod.BasesView as new (...args: unknown[]) => obsidian.Component;
    }
  } catch {
    // Minimal Vitest mock
  }
  try {
    if (typeof mod.Component === "function") {
      return mod.Component as new (...args: unknown[]) => obsidian.Component;
    }
  } catch {
    // Minimal Vitest mock
  }
  return FallbackBaseComponent as unknown as new (
    ...args: unknown[]
  ) => obsidian.Component;
}

const RuntimeBasesView = resolveRuntimeBasesView();

/** AsterLab 8-color accessible scientific categorical palette for domain / group indicators. */
const CATEGORICAL_COLORS = [
  "#3b6fd8",
  "#2f7a4f",
  "#c47f17",
  "#7a49c4",
  "#c94a5a",
  "#1b8a88",
  "#5d6bb8",
  "#9e6235",
];

function categoricalColor(label: string): string {
  if (!label) return CATEGORICAL_COLORS[0];
  let idx = 0;
  for (let i = 0; i < label.length; i += 1) {
    idx = (idx * 31 + label.charCodeAt(i)) % CATEGORICAL_COLORS.length;
  }
  return CATEGORICAL_COLORS[Math.abs(idx)];
}

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

function readValueString(val: unknown): string {
  if (val === null || val === undefined) return "";
  if (typeof val === "object" && "data" in (val as Record<string, unknown>)) {
    const d = (val as { data?: unknown }).data;
    if (d === null || d === undefined) return "";
    if (Array.isArray(d)) return d.map(String).join(", ");
    return String(d).trim();
  }
  const s = String(val).trim();
  return s === "null" || s === "undefined" || s === "[object Object]" ? "" : s;
}

function resolveRowForEntry(
  entry: obsidian.BasesEntry,
  rowsByKey: Record<string, BasePaperRowDto>
): BasePaperRowDto | null {
  try {
    const val = entry.getValue?.("note.zotero_key" as obsidian.BasesPropertyId);
    const cleaned = readValueString(val).replace(/^["']|["']$/g, "");
    if (cleaned && rowsByKey[cleaned]) {
      return rowsByKey[cleaned];
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

function stubRowForEntry(
  entry: obsidian.BasesEntry,
  snapshot: BaseTableSnapshotDto | null
): BasePaperRowDto | null {
  const baseName = entry.file?.basename || "";
  const guessedKey = baseName.split(/\s+-\s+/)[0]?.trim() || baseName;
  if (!guessedKey) return null;
  return {
    zotero_key: guessedKey,
    title:
      readValueString(
        entry.getValue?.("note.title" as obsidian.BasesPropertyId)
      ) ||
      baseName ||
      entry.file?.path ||
      guessedKey,
    first_author: readValueString(
      entry.getValue?.("note.first_author" as obsidian.BasesPropertyId)
    ),
    year: readValueString(
      entry.getValue?.("note.year" as obsidian.BasesPropertyId)
    ),
    journal: readValueString(
      entry.getValue?.("note.journal" as obsidian.BasesPropertyId)
    ),
    impact_factor: readValueString(
      entry.getValue?.("note.impact_factor" as obsidian.BasesPropertyId)
    ),
    domain: readValueString(
      entry.getValue?.("note.domain" as obsidian.BasesPropertyId)
    ),
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
  };
}

interface RenderItem {
  row: BasePaperRowDto;
  entry?: obsidian.BasesEntry;
}

interface RenderGroup {
  groupLabel: string | null;
  items: RenderItem[];
}

interface ColumnSpec {
  id: obsidian.BasesPropertyId;
  key: string;
  label: string;
  numeric: boolean;
}

const DEFAULT_COLUMN_LABELS: Record<string, string> = {
  title: "文献标题",
  name: "文献标题",
  "file.name": "文献标题",
  first_author: "第一作者",
  year: "年份",
  journal: "期刊",
  impact_factor: "IF",
  domain: "领域",
  annotations: "批注与记忆",
  ocr_status: "状态",
  has_pdf: "附件",
  deep_reading_status: "精读",
};

const NUMERIC_COLUMNS = new Set(["year", "impact_factor", "annotations"]);

export class PaperForgeBasesView extends RuntimeBasesView {
  type = VIEW_TYPE_PF_BASE_TABLE;
  declare app: obsidian.App;
  declare data: obsidian.BasesQueryResult | undefined;
  declare config: obsidian.BasesViewConfig | undefined;

  containerEl: HTMLElement;
  plugin: PaperForgeBasesHost;
  private _loadingSnapshot = false;
  private _stateRef: obsidian.EventRef | null = null;
  private _selectedKeys = new Set<string>();
  private _lastSelectedIdx: number | null = null;
  private _pendingShiftKey = false;
  private _localFilters: BaseFilterState | null = null;

  private _filterKey(): string {
    return (
      (
        (this as unknown as { file?: { path?: string } })?.file?.path || ""
      ).trim() || "default"
    );
  }

  private _getFilters(): BaseFilterState {
    if (this._localFilters) return this._localFilters;
    const loaded = this.plugin.getBaseFilters?.(this._filterKey()) ?? {};
    this._localFilters = { ...loaded };
    return this._localFilters;
  }

  private _updateFilters(patch: Partial<BaseFilterState>): void {
    const next: BaseFilterState = { ...this._getFilters(), ...patch };
    if (!next.query) delete next.query;
    if (!next.domain) delete next.domain;
    if (!next.collection) delete next.collection;
    if (!next.status || next.status === "all") delete next.status;
    if (!next.minIf || next.minIf <= 0) delete next.minIf;
    this._localFilters = next;
    this.plugin.setBaseFilters?.(this._filterKey(), next);
    this.render();
  }

  private _hasActiveFilters(f: BaseFilterState): boolean {
    return Boolean(
      (f.query && f.query.trim()) ||
      f.domain ||
      f.collection ||
      (f.status && f.status !== "all") ||
      (f.minIf && f.minIf > 0)
    );
  }

  private _matchesFilters(row: BasePaperRowDto, f: BaseFilterState): boolean {
    if (f.domain && row.domain !== f.domain) return false;
    if (f.collection) {
      const cols = Array.isArray(row.collections) ? row.collections : [];
      if (
        !cols.some(
          (c) => c === f.collection || c.startsWith(f.collection + "/")
        )
      ) {
        return false;
      }
    }
    if (f.status && f.status !== "all") {
      if (f.status === "pending" && row.ocr_status !== "pending") return false;
      if (f.status === "done" && row.ocr_status !== "done") return false;
      if (f.status === "deep_done" && row.deep_reading_status !== "done") {
        return false;
      }
    }
    if (f.minIf && f.minIf > 0) {
      const num = Number.parseFloat(String(row.impact_factor || ""));
      if (!Number.isFinite(num) || num < f.minIf) return false;
    }
    if (f.query && f.query.trim()) {
      const q = f.query.trim().toLowerCase();
      const hay =
        `${row.title} ${row.first_author} ${row.journal} ${row.domain} ${row.zotero_key}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  }

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

  private _collectGroups(snapshot: BaseTableSnapshotDto | null): RenderGroup[] {
    const rowsByKey = snapshot?.rows ?? {};
    const grouped = this.data?.groupedData;
    if (
      Array.isArray(grouped) &&
      grouped.length > 0 &&
      (grouped.length > 1 || Boolean(grouped[0]?.hasKey?.()))
    ) {
      const seen = new Set<string>();
      const out: RenderGroup[] = [];
      for (const grp of grouped) {
        const items: RenderItem[] = [];
        for (const entry of grp.entries ?? []) {
          const matched =
            resolveRowForEntry(entry, rowsByKey) ??
            stubRowForEntry(entry, snapshot);
          if (matched && !seen.has(matched.zotero_key)) {
            seen.add(matched.zotero_key);
            items.push({ row: matched, entry });
          }
        }
        if (items.length > 0) {
          const rawKey = grp.hasKey?.() ? readValueString(grp.key) : "";
          out.push({
            groupLabel: rawKey || "未分组",
            items,
          });
        }
      }
      return out;
    }

    const entries = this.data?.data;
    if (Array.isArray(entries)) {
      const items: RenderItem[] = [];
      const seen = new Set<string>();
      for (const entry of entries) {
        const matched =
          resolveRowForEntry(entry, rowsByKey) ??
          stubRowForEntry(entry, snapshot);
        if (matched && !seen.has(matched.zotero_key)) {
          seen.add(matched.zotero_key);
          items.push({ row: matched, entry });
        }
      }
      return items.length > 0 ? [{ groupLabel: null, items }] : [];
    }

    const items = Object.values(rowsByKey).map((row) => ({ row }));
    return items.length > 0 ? [{ groupLabel: null, items }] : [];
  }

  private _resolveColumns(): ColumnSpec[] {
    const showAnnotations = this.config?.get?.("show_annotations") !== false;
    const rawOrder = this.config?.getOrder?.();
    const fallbackOrder: obsidian.BasesPropertyId[] = [
      "note.title",
      "note.first_author",
      "note.year",
      "note.journal",
      "note.impact_factor",
      "note.domain",
      ...(showAnnotations
        ? (["note.annotations"] as obsidian.BasesPropertyId[])
        : []),
      "note.ocr_status",
    ];
    const order =
      Array.isArray(rawOrder) && rawOrder.length > 0
        ? [...rawOrder]
        : fallbackOrder;

    // Exclude legacy frontmatter workflow flags from main table clutter even if present in old YAML
    const filtered = order.filter((propId) => {
      const clean = String(propId).replace(/^(note|file|formula)\./, "");
      return (
        clean !== "do_ocr" &&
        clean !== "analyze" &&
        clean !== "zotero_key" &&
        clean !== "pdf_path"
      );
    });

    if (
      showAnnotations &&
      !filtered.some(
        (id) =>
          String(id).replace(/^(note|file|formula)\./, "") === "annotations"
      )
    ) {
      const statusIdx = filtered.findIndex(
        (id) =>
          String(id).replace(/^(note|file|formula)\./, "") === "ocr_status"
      );
      if (statusIdx >= 0) {
        filtered.splice(
          statusIdx,
          0,
          "note.annotations" as obsidian.BasesPropertyId
        );
      } else {
        filtered.push("note.annotations" as obsidian.BasesPropertyId);
      }
    }

    const specs: ColumnSpec[] = [];
    const seenKey = new Set<string>();
    for (const propId of filtered) {
      const str = String(propId);
      const clean =
        str === "file.name"
          ? "title"
          : str.replace(/^(note|file|formula)\./, "");
      if (seenKey.has(clean)) continue;
      seenKey.add(clean);
      let display = DEFAULT_COLUMN_LABELS[str] || DEFAULT_COLUMN_LABELS[clean];
      if (!display) {
        const cfgName = this.config?.getDisplayName?.(propId);
        display = cfgName && cfgName.trim() ? cfgName.trim() : clean;
      }
      specs.push({
        id: propId,
        key: clean,
        label: display,
        numeric: NUMERIC_COLUMNS.has(clean),
      });
    }
    return specs;
  }

  private _renderStatusBadge(cell: HTMLElement, row: BasePaperRowDto): void {
    if (this.plugin.isOcrRunningForKey(row.zotero_key)) {
      const prog = this.plugin._ocrProgress;
      const pctLabel =
        prog && prog.total > 0 ? ` ${prog.current}/${prog.total}` : "";
      mkEl(cell, "span", {
        cls: "pf-badge-outline is-running pf-tnum",
        text: `解析中${pctLabel}`,
      });
      return;
    }

    const status = row.ocr_status || "pending";
    if (status === "failed" || status === "done_incomplete") {
      const isFail = status === "failed";
      const btn = mkEl(cell, "button", {
        cls: `pf-badge-outline is-clickable ${isFail ? "is-fail" : "is-warn"}`,
        text: isFail ? "解析异常" : "部分解析",
        attr: {
          type: "button",
          "data-pf-testid": "base-status-diag",
          title: "点击查看全文解析诊断",
        },
      });
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        this.plugin.openOcrDiagnostic(row.zotero_key);
      });
      return;
    }

    if (status === "done") {
      mkEl(cell, "span", {
        cls: "pf-badge-outline is-done",
        text: row.deep_reading_status === "done" ? "已精读" : "已解析",
      });
      return;
    }
    if (status === "processing") {
      mkEl(cell, "span", {
        cls: "pf-badge-outline is-running",
        text: "排队中",
      });
      return;
    }
    if (status === "nopdf") {
      mkEl(cell, "span", {
        cls: "pf-badge-outline is-muted",
        text: "无附件",
      });
      return;
    }
    mkEl(cell, "span", {
      cls: "pf-badge-outline is-muted",
      text: "未解析",
    });
  }

  private _renderFilterBar(
    root: HTMLElement,
    rawItems: RenderItem[],
    filters: BaseFilterState
  ): void {
    const bar = mkEl(root, "div", {
      cls: "pf-base-filter-bar",
      attr: { "data-pf-testid": "base-filter-bar" },
    });

    const domains = Array.from(
      new Set(rawItems.map((it) => it.row.domain).filter(Boolean))
    ).sort();
    const activeDomain = filters.domain || "";
    const collectionPool = Array.from(
      new Set(
        rawItems
          .filter((it) => !activeDomain || it.row.domain === activeDomain)
          .flatMap((it) => it.row.collections || [])
          .filter(Boolean)
      )
    ).sort();

    // 1. Live keyword filter
    const searchInput = mkEl(bar, "input", {
      cls: "pf-base-filter-search",
      attr: {
        type: "search",
        placeholder: "筛选标题 / 作者 / 期刊…",
        "data-pf-testid": "base-filter-search",
      },
    }) as HTMLInputElement;
    searchInput.value = filters.query || "";
    searchInput.addEventListener("change", () => {
      this._updateFilters({ query: searchInput.value.trim() });
    });
    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        this._updateFilters({ query: searchInput.value.trim() });
      }
    });

    // 2. Topic / Domain dropdown
    if (domains.length > 0) {
      const domSel = mkEl(bar, "select", {
        cls: "pf-base-filter-select",
        attr: { "data-pf-testid": "base-filter-domain" },
      }) as HTMLSelectElement;
      const allOpt = mkEl(domSel, "option", {
        text: "全部专题",
        attr: { value: "" },
      }) as HTMLOptionElement;
      allOpt.selected = !activeDomain;
      for (const d of domains) {
        const opt = mkEl(domSel, "option", {
          text: d,
          attr: { value: d },
        }) as HTMLOptionElement;
        opt.selected = activeDomain === d;
      }
      domSel.addEventListener("change", () => {
        this._updateFilters({ domain: domSel.value, collection: "" });
      });
    }

    // 3. Cascading Zotero Collection dropdown
    if (collectionPool.length > 0) {
      const colSel = mkEl(bar, "select", {
        cls: "pf-base-filter-select",
        attr: { "data-pf-testid": "base-filter-collection" },
      }) as HTMLSelectElement;
      const allCol = mkEl(colSel, "option", {
        text: "全部子分类",
        attr: { value: "" },
      }) as HTMLOptionElement;
      allCol.selected = !filters.collection;
      for (const c of collectionPool) {
        const opt = mkEl(colSel, "option", {
          text: c,
          attr: { value: c },
        }) as HTMLOptionElement;
        opt.selected = filters.collection === c;
      }
      colSel.addEventListener("change", () => {
        this._updateFilters({ collection: colSel.value });
      });
    }

    // 4. Quick status pills
    const pills = mkEl(bar, "div", { cls: "pf-base-filter-pills" });
    const statusChoices: Array<[string, string]> = [
      ["all", "全部"],
      ["pending", "待解析"],
      ["done", "已解析"],
      ["deep_done", "已精读"],
    ];
    const activeStatus = filters.status || "all";
    for (const [val, label] of statusChoices) {
      const btn = mkEl(pills, "button", {
        cls: `pf-base-filter-pill${activeStatus === val ? " is-active" : ""}`,
        text: label,
        attr: { type: "button", "data-pf-filter-status": val },
      });
      btn.addEventListener("click", () => {
        this._updateFilters({ status: val });
      });
    }

    // 5. Minimum IF selector
    const ifSel = mkEl(bar, "select", {
      cls: "pf-base-filter-select pf-tnum",
      attr: { "data-pf-testid": "base-filter-if" },
    }) as HTMLSelectElement;
    for (const [val, label] of [
      ["0", "IF 不限"],
      ["5", "IF ≥ 5"],
      ["10", "IF ≥ 10"],
      ["20", "IF ≥ 20"],
    ]) {
      const opt = mkEl(ifSel, "option", {
        text: label,
        attr: { value: val },
      }) as HTMLOptionElement;
      opt.selected = String(filters.minIf || 0) === val;
    }
    ifSel.addEventListener("change", () => {
      this._updateFilters({ minIf: Number(ifSel.value) || 0 });
    });

    if (this._hasActiveFilters(filters)) {
      const reset = mkEl(bar, "button", {
        cls: "pf-btn pf-btn-ghost",
        text: "重置",
        attr: { type: "button", "data-pf-testid": "base-filter-reset" },
      });
      reset.addEventListener("click", () => {
        this._updateFilters({
          query: "",
          domain: "",
          collection: "",
          status: "all",
          minIf: 0,
        });
      });
    }
  }

  private _renderCell(
    tr: HTMLElement,
    col: ColumnSpec,
    item: RenderItem
  ): void {
    const { row, entry } = item;
    const td = mkEl(tr, "td", {
      cls: [
        `pf-base-cell-${col.key.replace(/[^a-z0-9_-]/gi, "-")}`,
        col.numeric ? "pf-tnum is-num" : "",
      ]
        .filter(Boolean)
        .join(" "),
    });

    switch (col.key) {
      case "title":
      case "file.name": {
        const titleWrap = mkEl(td, "div", { cls: "pf-base-title-cell" });
        if (row.has_pdf) {
          const pdfBtn = createPfIconBtn(titleWrap, {
            icon: "file-text",
            label: "打开 PDF",
            size: 14,
            cls: "pf-base-pdf-trigger",
            testid: "base-open-pdf",
          });
          pdfBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            void this.plugin.openPaperPdf(row.zotero_key);
          });
        } else {
          mkEl(titleWrap, "span", {
            cls: "pf-base-no-pdf-slot",
            attr: { "aria-hidden": "true" },
          });
        }
        const titleBtn = mkEl(titleWrap, "button", {
          cls: "pf-base-title-link",
          text: row.title || row.zotero_key,
          attr: {
            type: "button",
            "data-pf-testid": "base-open-note",
            title: row.title || row.zotero_key,
          },
        });
        titleBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          this._openNote(row.main_note_path);
        });
        bindObsidianHoverPreview(
          this.app ?? this.plugin.app,
          titleBtn,
          "paperforge",
          row.main_note_path
        );
        break;
      }
      case "first_author":
        mkEl(td, "span", {
          cls: "pf-base-text-ellipsis",
          text: row.first_author || "—",
        });
        break;
      case "year":
        td.textContent = row.year || "—";
        break;
      case "journal":
        mkEl(td, "span", {
          cls: "pf-base-text-ellipsis pf-base-muted",
          text: row.journal || "—",
        });
        break;
      case "impact_factor": {
        const val = row.impact_factor || "";
        const src = row.impact_factor_source || "";
        const part = row.journal_partition || "";
        if (!val) {
          td.textContent = "—";
          td.classList.add("pf-base-muted");
        } else if (src === "openalex_2yr") {
          mkEl(td, "span", { text: val });
          mkEl(td, "span", { cls: "pf-if-approx", text: "≈" });
          td.setAttribute(
            "title",
            "来自 OpenAlex 开源 2 年篇均引文指标（可在设置填写 EasyScholar Key 升级为精确 JCR IF 与中科院分区）"
          );
        } else {
          td.textContent = val;
          const tipParts: string[] = [];
          if (src === "jcr") tipParts.push("官方 JCR IF");
          else if (src === "zotero_plugin") tipParts.push("Zotero 期刊库");
          else if (src === "extra") tipParts.push("Zotero Extra");
          if (part) tipParts.push(part);
          if (tipParts.length > 0) {
            td.setAttribute("title", tipParts.join(" · "));
          }
        }
        break;
      }
      case "domain": {
        if (!row.domain) {
          mkEl(td, "span", { cls: "pf-base-muted", text: "—" });
        } else {
          const domWrap = mkEl(td, "span", { cls: "pf-base-domain-chip" });
          const dot = mkEl(domWrap, "span", { cls: "pf-base-dot" });
          dot.style.background = categoricalColor(row.domain);
          mkEl(domWrap, "span", { text: row.domain });
        }
        break;
      }
      case "annotations": {
        const totalAnns =
          (row.user_ann_count || 0) + (row.agent_ann_count || 0);
        const memCount = row.memory_facet_count || 0;
        const parts: string[] = [];
        if (totalAnns > 0) parts.push(`${totalAnns} 批注`);
        if (memCount > 0) parts.push(`${memCount} 记忆`);
        td.textContent = parts.length > 0 ? parts.join(" · ") : "—";
        if (parts.length === 0) td.classList.add("pf-base-muted");
        break;
      }
      case "ocr_status":
        this._renderStatusBadge(td, row);
        break;
      case "has_pdf":
        mkEl(td, "span", {
          cls: "pf-base-muted",
          text: row.has_pdf ? "PDF" : "—",
        });
        break;
      case "deep_reading_status":
        mkEl(td, "span", {
          cls: "pf-base-muted",
          text: row.deep_reading_status === "done" ? "已精读" : "—",
        });
        break;
      default: {
        const val = readValueString(entry?.getValue?.(col.id));
        td.textContent = val || "—";
        if (!val) td.classList.add("pf-base-muted");
        break;
      }
    }
  }

  private _openNote(notePath: string): void {
    if (!notePath) {
      new Notice(t("paper_note_missing") || "Note path unavailable.");
      return;
    }
    const app = this.app ?? this.plugin.app;
    void app.workspace?.openLinkText?.(notePath, "");
  }

  private _openRowContextMenu(event: MouseEvent, row: BasePaperRowDto): void {
    openUnifiedPaperContextMenu(event, {
      key: row.zotero_key,
      title: row.title,
      notePath: row.main_note_path,
      hasPdf: row.has_pdf,
      needsDiagnostic:
        row.needs_diagnostic ||
        row.ocr_status === "failed" ||
        row.ocr_status === "done_incomplete",
      onOpenNote: () => this._openNote(row.main_note_path),
      onOpenPdf: () => void this.plugin.openPaperPdf(row.zotero_key),
      onOpenSplit: this.plugin.openPaperSplitReading
        ? () =>
            void this.plugin.openPaperSplitReading!(
              row.zotero_key,
              row.main_note_path
            )
        : undefined,
      onRunOcr: () =>
        void this.plugin.requestOcrRun({
          kind: "papers",
          keys: [row.zotero_key],
        }),
      onOpenDiagnostic: () => this.plugin.openOcrDiagnostic(row.zotero_key),
    });
  }

  render(): void {
    const root = this.containerEl;
    if (!root) return;
    root.innerHTML = "";
    root.classList.add("pf-base-view-root");
    const compact = this.config?.get?.("compact_rows") === true;
    root.classList.toggle("is-compact", compact);

    const snapshot = this.plugin.getBaseSnapshotCache();
    const rawGroups = this._collectGroups(snapshot);
    const rawFlatItems = rawGroups.flatMap((g) => g.items);
    const filters = this._getFilters();
    const groups = rawGroups
      .map((g) => ({
        groupLabel: g.groupLabel,
        items: g.items.filter((it) => this._matchesFilters(it.row, filters)),
      }))
      .filter((g) => g.items.length > 0);
    const flatItems = groups.flatMap((g) => g.items);
    const visibleKeySet = new Set(flatItems.map((it) => it.row.zotero_key));

    // Prune stale selections not in current view slice
    for (const k of Array.from(this._selectedKeys)) {
      if (!visibleKeySet.has(k)) this._selectedKeys.delete(k);
    }

    const selectedItems = flatItems.filter((it) =>
      this._selectedKeys.has(it.row.zotero_key)
    );
    const selectedKeys = selectedItems.map((it) => it.row.zotero_key);

    // Subtle runtime activity strip (only shown while an OCR batch is active)
    const activeProg = this.plugin._ocrProgress;
    const isRunningAny =
      Boolean(activeProg && activeProg.key) ||
      rawFlatItems.some((it) =>
        this.plugin.isOcrRunningForKey(it.row.zotero_key)
      );
    if (isRunningAny) {
      const strip = mkEl(root, "div", {
        cls: "pf-base-activity-strip pf-tnum",
      });
      const iconHost = mkEl(strip, "span", { cls: "pf-base-activity-icon" });
      setPfIcon(iconHost, "refresh-cw", 13);
      const countText =
        activeProg && activeProg.total > 0
          ? ` ${activeProg.current} / ${activeProg.total}`
          : "";
      mkEl(strip, "span", {
        text: `正在解析全文${countText}`,
      });
    }

    // Persistent multi-filter bar (survives Obsidian view switches & restarts)
    if (rawFlatItems.length > 0 || this._hasActiveFilters(filters)) {
      this._renderFilterBar(root, rawFlatItems, filters);
    }

    if (flatItems.length === 0) {
      const empty = mkEl(root, "div", { cls: "pf-base-empty" });
      mkEl(empty, "span", {
        text: this._loadingSnapshot
          ? t("pdf_loading") || "正在加载文献数据…"
          : this._hasActiveFilters(filters)
            ? "当前筛选条件下没有匹配的文献。"
            : t("base_empty_hint") || "当前筛选条件下暂无文献。",
      });
      if (this._hasActiveFilters(filters)) {
        const resetBtn = mkEl(empty, "button", {
          cls: "pf-btn",
          text: "重置筛选条件",
          attr: {
            type: "button",
            "data-pf-testid": "base-reset-filters-empty",
          },
        });
        resetBtn.addEventListener("click", () => {
          this._updateFilters({
            query: "",
            domain: "",
            collection: "",
            status: "all",
            minIf: 0,
          });
        });
      } else if (!this._loadingSnapshot) {
        const syncEmptyBtn = mkEl(empty, "button", {
          cls: "pf-btn",
          text: t("base_sync_library") || "同步文献库",
          attr: { type: "button", "data-pf-testid": "base-sync-library" },
        });
        syncEmptyBtn.addEventListener("click", () => {
          this.plugin.triggerManualSync();
        });
      }
      return;
    }

    // Contextual Multi-Select Header Bar (appears strictly when >=1 row selected)
    if (selectedKeys.length > 0) {
      const bar = mkEl(root, "div", {
        cls: "pf-base-selection-bar",
        attr: { "data-pf-testid": "base-selection-bar" },
      });
      const left = mkEl(bar, "div", { cls: "pf-base-selection-left" });
      mkEl(left, "span", {
        cls: "pf-base-selection-count pf-tnum",
        text: (t("base_selected_count") || "已选 {n} 篇").replace(
          "{n}",
          String(selectedKeys.length)
        ),
      });
      const clearBtn = mkEl(left, "button", {
        cls: "pf-btn pf-btn-ghost",
        text: t("base_clear_selection") || "取消选择",
        attr: { type: "button", "data-pf-testid": "base-clear-selection" },
      });
      clearBtn.addEventListener("click", () => {
        this._selectedKeys.clear();
        this._lastSelectedIdx = null;
        this.render();
      });

      const right = mkEl(bar, "div", { cls: "pf-base-selection-actions" });
      if (selectedItems.length === 1 && selectedItems[0].row.has_pdf) {
        const openPdfBtn = mkEl(right, "button", {
          cls: "pf-btn",
          text: t("base_open_pdf") || "打开 PDF",
          attr: { type: "button", "data-pf-testid": "base-selection-open-pdf" },
        });
        openPdfBtn.addEventListener("click", () => {
          void this.plugin.openPaperPdf(selectedItems[0].row.zotero_key);
        });
      }
      const diagTarget = selectedItems.find(
        (it) =>
          it.row.needs_diagnostic ||
          it.row.ocr_status === "failed" ||
          it.row.ocr_status === "done_incomplete"
      );
      if (diagTarget) {
        const diagBtn = mkEl(right, "button", {
          cls: "pf-btn",
          text: t("base_open_diag") || "查看诊断",
          attr: { type: "button", "data-pf-testid": "base-open-diag" },
        });
        diagBtn.addEventListener("click", () => {
          this.plugin.openOcrDiagnostic(diagTarget.row.zotero_key);
        });
      }
      const syncBtn = mkEl(right, "button", {
        cls: "pf-btn",
        text: t("base_sync_library") || "同步文献库",
        attr: { type: "button", "data-pf-testid": "base-sync-library" },
      });
      syncBtn.addEventListener("click", () => {
        this.plugin.triggerManualSync();
      });

      const parseBtn = mkEl(right, "button", {
        cls: "pf-btn mod-cta",
        text: t("base_run_selected_ocr") || "解析全文",
        attr: { type: "button", "data-pf-testid": "base-run-selected-ocr" },
      });
      parseBtn.addEventListener("click", () => {
        void this.plugin.requestOcrRun({
          kind: "papers",
          keys: selectedKeys,
        });
      });
    }

    const columns = this._resolveColumns();
    const wrap = mkEl(root, "div", { cls: "pf-base-table-wrap" });
    const table = mkEl(wrap, "table", { cls: "pf-base-table" });

    // Header Row: Checkbox column + Dynamic Base Columns
    const thead = mkEl(table, "thead");
    const headRow = mkEl(thead, "tr");
    const checkTh = mkEl(headRow, "th", { cls: "pf-base-col-check" });
    const selectAllCb = mkEl(checkTh, "input", {
      attr: {
        type: "checkbox",
        "aria-label": "全选文献",
        "data-pf-testid": "base-select-all",
      },
    }) as HTMLInputElement;
    selectAllCb.checked =
      flatItems.length > 0 && selectedKeys.length === flatItems.length;
    selectAllCb.indeterminate =
      selectedKeys.length > 0 && selectedKeys.length < flatItems.length;
    selectAllCb.addEventListener("change", () => {
      if (selectAllCb.checked) {
        for (const it of flatItems) this._selectedKeys.add(it.row.zotero_key);
      } else {
        this._selectedKeys.clear();
      }
      this._lastSelectedIdx = null;
      this.render();
    });

    for (const col of columns) {
      mkEl(headRow, "th", {
        cls: col.numeric ? "is-num" : "",
        text: col.label,
      });
    }

    const tbody = mkEl(table, "tbody");
    let flatIdx = 0;
    const totalColSpan = columns.length + 1;

    for (const grp of groups) {
      if (grp.groupLabel !== null) {
        const gTr = mkEl(tbody, "tr", { cls: "pf-base-group-row" });
        const gTd = mkEl(gTr, "td", {
          attr: { colspan: String(totalColSpan) },
        });
        const gWrap = mkEl(gTd, "div", { cls: "pf-base-group-head" });
        const gDot = mkEl(gWrap, "span", { cls: "pf-base-dot" });
        gDot.style.background = categoricalColor(grp.groupLabel);
        mkEl(gWrap, "span", {
          cls: "pf-base-group-name",
          text: grp.groupLabel,
        });
        mkEl(gWrap, "span", {
          cls: "pf-base-group-count pf-tnum",
          text: `${grp.items.length} 篇`,
        });
      }

      for (const item of grp.items) {
        const row = item.row;
        const rowIndex = flatIdx++;
        const isSelected = this._selectedKeys.has(row.zotero_key);
        const tr = mkEl(tbody, "tr", {
          cls: `pf-base-row${isSelected ? " is-selected" : ""}`,
          attr: { "data-paper-key": row.zotero_key },
        });
        tr.addEventListener("contextmenu", (e) =>
          this._openRowContextMenu(e, row)
        );

        const checkTd = mkEl(tr, "td", { cls: "pf-base-cell-check" });
        const rowCb = mkEl(checkTd, "input", {
          attr: {
            type: "checkbox",
            "data-pf-select-key": row.zotero_key,
            "aria-label": row.title || row.zotero_key,
          },
        }) as HTMLInputElement;
        rowCb.checked = isSelected;
        rowCb.addEventListener("click", (e) => {
          this._pendingShiftKey = e.shiftKey;
        });
        rowCb.addEventListener("change", () => {
          const checked = rowCb.checked;
          if (this._pendingShiftKey && this._lastSelectedIdx !== null) {
            const start = Math.min(this._lastSelectedIdx, rowIndex);
            const end = Math.max(this._lastSelectedIdx, rowIndex);
            for (let idx = start; idx <= end; idx += 1) {
              const targetKey = flatItems[idx]?.row.zotero_key;
              if (!targetKey) continue;
              if (checked) this._selectedKeys.add(targetKey);
              else this._selectedKeys.delete(targetKey);
            }
          } else {
            if (checked) this._selectedKeys.add(row.zotero_key);
            else this._selectedKeys.delete(row.zotero_key);
          }
          this._pendingShiftKey = false;
          this._lastSelectedIdx = rowIndex;
          this.render();
        });

        for (const col of columns) {
          this._renderCell(tr, col, item);
        }
      }
    }
  }
}
