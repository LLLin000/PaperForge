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
  updateNoteProperty?: (
    file: obsidian.TFile,
    propName: string,
    value: string
  ) => Promise<void>;
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
  parent: Node,
  tag: K,
  opts?: { cls?: string; text?: string; attr?: Record<string, string> }
): HTMLElementTagNameMap[K] {
  const doc = parent.ownerDocument || document;
  const el = doc.createElement(tag);
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

const SEARCH_HAY_CACHE = new WeakMap<BasePaperRowDto, string>();

function getSearchHaystack(row: BasePaperRowDto): string {
  let hay = SEARCH_HAY_CACHE.get(row);
  if (hay === undefined) {
    hay =
      `${row.title} ${row.first_author} ${row.journal} ${row.domain} ${row.zotero_key}`.toLowerCase();
    SEARCH_HAY_CACHE.set(row, hay);
  }
  return hay;
}

function resolveModEvent(
  evt?: MouseEvent | KeyboardEvent
): obsidian.PaneType | boolean {
  if (!evt) return false;
  try {
    const km = (obsidian as Record<string, unknown>).Keymap as
      | {
          isModEvent?: (
            e: MouseEvent | KeyboardEvent
          ) => obsidian.PaneType | boolean;
        }
      | undefined;
    if (typeof km?.isModEvent === "function") {
      return km.isModEvent(evt);
    }
  } catch {
    // Minimal Vitest mock proxy may throw when Keymap is omitted
  }
  if (evt.ctrlKey || evt.metaKey) return "tab";
  return false;
}

/** O(1) main_note_path index cached per snapshot object (eliminates O(N²) render scan). */
const PATH_INDEX_CACHE = new WeakMap<
  BaseTableSnapshotDto,
  Map<string, BasePaperRowDto>
>();

function getPathIndex(
  snapshot: BaseTableSnapshotDto | null
): Map<string, BasePaperRowDto> {
  if (!snapshot || !snapshot.rows) return new Map();
  let idx = PATH_INDEX_CACHE.get(snapshot);
  if (idx) return idx;
  idx = new Map();
  for (const row of Object.values(snapshot.rows)) {
    if (row.main_note_path) {
      idx.set(row.main_note_path.replace(/\\/g, "/"), row);
    }
  }
  PATH_INDEX_CACHE.set(snapshot, idx);
  return idx;
}

function resolveRowForEntry(
  entry: obsidian.BasesEntry,
  rowsByKey: Record<string, BasePaperRowDto>,
  pathIndex: Map<string, BasePaperRowDto>
): BasePaperRowDto | null {
  const entryPath = (entry.file?.path || "").replace(/\\/g, "/");
  const withLivePath = (row: BasePaperRowDto): BasePaperRowDto =>
    entryPath && (row.main_note_path || "").replace(/\\/g, "/") !== entryPath
      ? { ...row, main_note_path: entryPath }
      : row;
  try {
    const val = entry.getValue?.("note.zotero_key" as obsidian.BasesPropertyId);
    const cleaned = readValueString(val).replace(/^["']|["']$/g, "");
    if (cleaned && rowsByKey[cleaned]) {
      return withLivePath(rowsByKey[cleaned]);
    }
  } catch {
    // Ignore malformed formula/property values on individual notes
  }
  if (entryPath) {
    const byPath = pathIndex.get(entryPath);
    if (byPath) return withLivePath(byPath);
  }
  const baseName = entry.file?.basename || "";
  if (baseName) {
    if (rowsByKey[baseName]) return withLivePath(rowsByKey[baseName]);
    const prefix = baseName.split(/\s+-\s+/)[0]?.trim();
    if (prefix && rowsByKey[prefix]) return withLivePath(rowsByKey[prefix]);
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
  const rawHasPdf = readValueString(
    entry.getValue?.("note.has_pdf" as obsidian.BasesPropertyId)
  )
    .trim()
    .toLowerCase();
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
    has_pdf: rawHasPdf === "true" || rawHasPdf === "1",
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

type RenderSlot =
  | { kind: "group"; label: string; count: number }
  | { kind: "row"; item: RenderItem; flatIndex: number };

interface ColumnSpec {
  id: obsidian.BasesPropertyId;
  key: string;
  label: string;
  numeric: boolean;
}

const DEFAULT_COLUMN_LABEL_KEYS: Record<string, string> = {
  title: "base_col_title",
  name: "base_col_title",
  "file.name": "base_col_title",
  first_author: "base_col_first_author",
  year: "base_col_year",
  journal: "base_col_journal",
  domain: "base_col_domain",
  annotations: "base_col_annotations",
  ocr_status: "base_col_status",
  has_pdf: "base_col_has_pdf",
  deep_reading_status: "base_col_deep_reading",
};

function defaultColumnLabel(key: string): string | undefined {
  if (key === "impact_factor") return "IF";
  const i18nKey = DEFAULT_COLUMN_LABEL_KEYS[key];
  return i18nKey ? t(i18nKey) : undefined;
}

const NUMERIC_COLUMNS = new Set(["year", "impact_factor", "annotations"]);

/** Fixed pixel widths for compact scalar/badge columns. */
const FIXED_COL_WIDTHS: Record<string, string> = {
  year: "58px",
  impact_factor: "62px",
  annotations: "118px",
  ocr_status: "108px",
  has_pdf: "52px",
  deep_reading_status: "78px",
};

/** Relative weights for flexible text columns (prioritize paper Title readability). */
const FLEX_COL_WEIGHTS: Record<string, number> = {
  title: 4.8,
  "file.name": 4.8,
  journal: 1.4,
  first_author: 1.15,
  domain: 0.95,
};

function computeColumnWidths(columns: ColumnSpec[]): string[] {
  let totalWeight = 0;
  for (const c of columns) {
    if (!FIXED_COL_WIDTHS[c.key]) {
      totalWeight += FLEX_COL_WEIGHTS[c.key] ?? 1.1;
    }
  }
  return columns.map((c) => {
    if (FIXED_COL_WIDTHS[c.key]) return FIXED_COL_WIDTHS[c.key];
    const w = FLEX_COL_WEIGHTS[c.key] ?? 1.1;
    const pct = totalWeight > 0 ? (w / totalWeight) * 100 : 20;
    return `${pct.toFixed(1)}%`;
  });
}

const INITIAL_CHUNK_SIZE = 80;
const LOAD_MORE_CHUNK_SIZE = 80;

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
  private _focusedRowIdx = -1;
  private _pendingShiftKey = false;
  private _localFilters: BaseFilterState | null = null;
  private _missingPdfHintDismissed = false;

  // Performance & surgical update state
  private _searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;
  private _rafRenderId: number | null = null;
  private _loadMoreObserver: IntersectionObserver | null = null;
  private _shellMounted = false;
  private _activitySlotEl: HTMLElement | null = null;
  private _filterSlotEl: HTMLElement | null = null;
  private _missingPdfSlotEl: HTMLElement | null = null;
  private _selectionSlotEl: HTMLElement | null = null;
  private _emptySlotEl: HTMLElement | null = null;
  private _tableWrapEl: HTMLElement | null = null;
  private _tableEl: HTMLTableElement | null = null;
  private _colgroupEl: HTMLElement | null = null;
  private _theadEl: HTMLElement | null = null;
  private _tbodyEl: HTMLElement | null = null;
  private _tfootEl: HTMLElement | null = null;
  private _selectAllCbEl: HTMLInputElement | null = null;
  private _filterCountEl: HTMLElement | null = null;
  private _filterResetBtnEl: HTMLButtonElement | null = null;
  private _searchInputEl: HTMLInputElement | null = null;
  private _domainSelectEl: HTMLSelectElement | null = null;
  private _collectionSelectEl: HTMLSelectElement | null = null;
  private _ifSelectEl: HTMLSelectElement | null = null;
  private _statusPillBtns = new Map<string, HTMLButtonElement>();
  private _filterOptionSig = "";
  private _lastRawItems: RenderItem[] = [];
  private _collapsedGroups = new Set<string>();
  private _collapsedGroupsLoaded = false;
  private _localSort: { key: string; dir: "ASC" | "DESC" } | null = null;
  private _activeResizeCleanup: (() => void) | null = null;
  private _currentFlatItems: RenderItem[] = [];
  private _currentSlots: RenderSlot[] = [];
  private _currentColumns: ColumnSpec[] = [];
  private _renderedSlotCount = 0;
  private _renderedPaperCount = 0;
  private _virtualActive = false;
  private _virtualRange = { start: -1, end: -1 };
  private _virtualRafId: number | null = null;
  private _tableScrollHandler: (() => void) | null = null;

  private _filterKey(): string {
    const filePath = (
      (this as unknown as { file?: { path?: string } })?.file?.path || ""
    ).trim();
    if (filePath) return filePath;
    const viewName = String(this.config?.name || "").trim();
    const ctrl = (
      this as unknown as {
        controller?: { file?: { path?: string }; viewName?: string };
      }
    )?.controller;
    const ctrlPath = String(ctrl?.file?.path || "").trim();
    if (ctrlPath) {
      return viewName ? `${ctrlPath}#${viewName}` : ctrlPath;
    }
    const rawEntries = this.data?.data;
    const firstDir =
      Array.isArray(rawEntries) && rawEntries[0]?.file?.path
        ? String(rawEntries[0].file.path).split("/").slice(0, -1).join("/")
        : "";
    if (viewName && firstDir) return `${firstDir}::${viewName}`;
    if (viewName) return viewName;
    if (firstDir) return firstDir;
    return "default";
  }

  private _getFilters(): BaseFilterState {
    if (this._localFilters) return this._localFilters;
    const loaded = this.plugin.getBaseFilters?.(this._filterKey()) ?? {};
    this._localFilters = { ...loaded };
    return this._localFilters;
  }

  private _updateFilters(
    patch: Partial<BaseFilterState>,
    opts?: { preserveSearchFocus?: boolean }
  ): void {
    const next: BaseFilterState = { ...this._getFilters(), ...patch };
    if (!next.query) delete next.query;
    if (!next.domain) delete next.domain;
    if (!next.collection) delete next.collection;
    if (!next.status || next.status === "all") delete next.status;
    if (!next.minIf || next.minIf <= 0) delete next.minIf;
    this._localFilters = next;
    this.plugin.setBaseFilters?.(this._filterKey(), next);

    if (opts?.preserveSearchFocus && this._shellMounted && this._filterSlotEl) {
      this._renderBodyOnly();
      return;
    }
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
      if (
        f.status === "deep_done" &&
        row.deep_reading_status !== "done" &&
        row.deep_reading_status !== "complete"
      ) {
        return false;
      }
    }
    if (f.minIf && f.minIf > 0) {
      const num = Number.parseFloat(String(row.impact_factor || ""));
      if (!Number.isFinite(num) || num < f.minIf) return false;
    }
    if (f.query && f.query.trim()) {
      const q = f.query.trim().toLowerCase();
      if (!getSearchHaystack(row).includes(q)) return false;
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
      on?: (
        name: string,
        cb: (payload?: { changedKeys?: string[] }) => void
      ) => obsidian.EventRef;
    };
    if (typeof ws?.on === "function") {
      this._stateRef = ws.on("paperforge:state-changed", (payload) => {
        this._handleStateChanged(payload);
      });
    }
    if (!this.plugin.getBaseSnapshotCache() && !this._loadingSnapshot) {
      this._loadingSnapshot = true;
      void this.plugin
        .refreshBaseSnapshot()
        .catch(() => null)
        .finally(() => {
          this._loadingSnapshot = false;
          this._scheduleRender();
        });
    }
    this.render();
  }

  private _handleStateChanged(payload?: { changedKeys?: string[] }): void {
    const changed = Array.isArray(payload?.changedKeys)
      ? payload!.changedKeys.filter(Boolean)
      : [];
    if (
      changed.length > 0 &&
      this._shellMounted &&
      this._tbodyEl &&
      this._tbodyEl.isConnected
    ) {
      if (this._patchChangedRows(changed)) {
        this._renderActivityStrip(this._lastRawItems);
        return;
      }
    }
    this._scheduleRender();
  }

  private _patchChangedRows(changedKeys: string[]): boolean {
    const tbody = this._tbodyEl;
    if (!tbody) return false;
    const snapshot = this.plugin.getBaseSnapshotCache();
    const rowsByKey = snapshot?.rows;
    if (!rowsByKey) return false;
    let patchedAny = false;
    for (const key of changedKeys) {
      const fresh = rowsByKey[key];
      if (!fresh) continue;
      const tr = tbody.querySelector<HTMLTableRowElement>(
        `tr.pf-base-row[data-paper-key="${CSS?.escape ? CSS.escape(key) : key.replace(/"/g, '\\"')}"]`
      );
      if (!tr) continue;
      const flatItem = this._currentFlatItems.find(
        (it) => it.row.zotero_key === key
      );
      if (flatItem) flatItem.row = fresh;
      const statusCell = tr.querySelector<HTMLElement>(
        "td.pf-base-cell-ocr_status"
      );
      if (statusCell) {
        statusCell.textContent = "";
        this._renderStatusBadge(statusCell, fresh);
        patchedAny = true;
      }
      const annCell = tr.querySelector<HTMLElement>(
        "td.pf-base-cell-annotations"
      );
      if (annCell) {
        const totalAnns =
          (fresh.user_ann_count || 0) + (fresh.agent_ann_count || 0);
        const memCount = fresh.memory_facet_count || 0;
        const parts: string[] = [];
        if (totalAnns > 0)
          parts.push(
            t("base_count_annotations").replace("{n}", String(totalAnns))
          );
        if (memCount > 0)
          parts.push(t("base_count_memory").replace("{n}", String(memCount)));
        annCell.textContent = parts.length > 0 ? parts.join(" · ") : "—";
        annCell.classList.toggle("pf-base-muted", parts.length === 0);
        patchedAny = true;
      }
    }
    return patchedAny;
  }

  onunload(): void {
    if (this._searchDebounceTimer) {
      clearTimeout(this._searchDebounceTimer);
      this._searchDebounceTimer = null;
    }
    if (
      this._rafRenderId !== null &&
      typeof cancelAnimationFrame === "function"
    ) {
      cancelAnimationFrame(this._rafRenderId);
      this._rafRenderId = null;
    }
    if (
      this._virtualRafId !== null &&
      typeof cancelAnimationFrame === "function"
    ) {
      cancelAnimationFrame(this._virtualRafId);
      this._virtualRafId = null;
    }
    if (this._tableWrapEl && this._tableScrollHandler) {
      this._tableWrapEl.removeEventListener("scroll", this._tableScrollHandler);
    }
    this._tableScrollHandler = null;
    this._activeResizeCleanup?.();
    this._activeResizeCleanup = null;
    this._disconnectLoadMoreObserver();
    this._shellMounted = false;
    const app = this.app ?? this.plugin.app;
    const ws = app?.workspace as unknown as {
      offref?: (ref: obsidian.EventRef) => void;
    };
    if (this._stateRef && typeof ws?.offref === "function") {
      ws.offref(this._stateRef);
    }
    this._stateRef = null;
  }

  private _scheduleRender(): void {
    if (
      typeof requestAnimationFrame === "function" &&
      this.containerEl?.isConnected
    ) {
      if (this._rafRenderId !== null) return;
      this._rafRenderId = requestAnimationFrame(() => {
        this._rafRenderId = null;
        if (this.containerEl?.isConnected) {
          this.render();
        }
      });
      return;
    }
    this.render();
  }

  onDataUpdated(): void {
    if (!this.plugin.getBaseSnapshotCache() && !this._loadingSnapshot) {
      this._loadingSnapshot = true;
      void this.plugin
        .refreshBaseSnapshot()
        .catch(() => null)
        .finally(() => {
          this._loadingSnapshot = false;
          this._scheduleRender();
        });
    }
    this._scheduleRender();
  }

  private _disconnectLoadMoreObserver(): void {
    if (this._loadMoreObserver) {
      this._loadMoreObserver.disconnect();
      this._loadMoreObserver = null;
    }
  }

  private _collectGroups(snapshot: BaseTableSnapshotDto | null): RenderGroup[] {
    const rowsByKey = snapshot?.rows ?? {};
    const pathIndex = getPathIndex(snapshot);
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
            resolveRowForEntry(entry, rowsByKey, pathIndex) ??
            stubRowForEntry(entry, snapshot);
          if (matched && !seen.has(matched.zotero_key)) {
            seen.add(matched.zotero_key);
            items.push({ row: matched, entry });
          }
        }
        if (items.length > 0) {
          const rawKey = grp.hasKey?.() ? readValueString(grp.key) : "";
          out.push({
            groupLabel: rawKey || t("base_ungrouped"),
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
          resolveRowForEntry(entry, rowsByKey, pathIndex) ??
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
    const hasUserOrder = Array.isArray(rawOrder) && rawOrder.length > 0;
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
    const order = hasUserOrder ? [...rawOrder] : fallbackOrder;

    // Only strip legacy queue flags when using default fallback order; respect explicit user selection.
    const filtered = hasUserOrder
      ? order
      : order.filter((propId) => {
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
      const cfgName = this.config?.getDisplayName?.(propId)?.trim() ?? "";
      const hasExplicitAlias =
        cfgName.length > 0 && cfgName !== clean && cfgName !== str;
      const display = hasExplicitAlias
        ? cfgName
        : defaultColumnLabel(str) ||
          defaultColumnLabel(clean) ||
          cfgName ||
          clean;
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
        text: `${t("ocr_ws_status_processing")}${pctLabel}`,
      });
      return;
    }

    const status = row.ocr_status || "pending";
    if (status === "failed" || status === "done_incomplete") {
      const isFail = status === "failed";
      const btn = mkEl(cell, "button", {
        cls: `pf-badge-outline is-clickable ${isFail ? "is-fail" : "is-warn"}`,
        text: isFail
          ? t("ocr_ws_status_failed")
          : t("ocr_ws_status_incomplete"),
        attr: {
          type: "button",
          "data-pf-testid": "base-status-diag",
          title: t("base_status_diag_tip"),
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
        text:
          row.deep_reading_status === "done"
            ? t("base_status_deep_done")
            : t("ocr_ws_status_done"),
      });
      return;
    }
    if (status === "processing" || status === "queued") {
      mkEl(cell, "span", {
        cls: "pf-badge-outline is-running",
        text: t("ocr_ws_status_queued"),
      });
      return;
    }
    if (status === "nopdf") {
      mkEl(cell, "span", {
        cls: "pf-badge-outline is-muted",
        text: t("ocr_ws_status_nopdf"),
      });
      return;
    }
    mkEl(cell, "span", {
      cls: "pf-badge-outline is-muted",
      text: t("ocr_ws_status_pending"),
    });
  }

  private _updateFilterBarMeta(
    rawCount: number,
    matchedCount: number,
    filters: BaseFilterState
  ): void {
    if (this._filterCountEl) {
      this._filterCountEl.textContent = this._hasActiveFilters(filters)
        ? t("base_count_filtered")
            .replace("{shown}", String(matchedCount))
            .replace("{total}", String(rawCount))
        : t("base_count_total").replace("{n}", String(rawCount));
    }
    const activeStatus = filters.status || "all";
    for (const [val, btn] of this._statusPillBtns.entries()) {
      btn.classList.toggle("is-active", activeStatus === val);
    }
    if (this._filterResetBtnEl) {
      this._filterResetBtnEl.style.display = this._hasActiveFilters(filters)
        ? ""
        : "none";
    }
  }

  private _renderFilterBar(
    host: HTMLElement,
    rawItems: RenderItem[],
    matchedCount: number,
    filters: BaseFilterState
  ): void {
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

    const sig = `${domains.join("|")}::${collectionPool.join("|")}::${activeDomain}`;
    if (
      this._searchInputEl &&
      this._searchInputEl.isConnected &&
      sig === this._filterOptionSig
    ) {
      if (
        this._searchInputEl.ownerDocument?.activeElement !== this._searchInputEl
      ) {
        this._searchInputEl.value = filters.query || "";
      }
      if (this._domainSelectEl) this._domainSelectEl.value = activeDomain;
      if (this._collectionSelectEl) {
        this._collectionSelectEl.value = filters.collection || "";
      }
      if (this._ifSelectEl) {
        this._ifSelectEl.value = String(filters.minIf || 0);
      }
      this._updateFilterBarMeta(rawItems.length, matchedCount, filters);
      return;
    }

    this._filterOptionSig = sig;
    this._statusPillBtns.clear();
    host.textContent = "";

    const bar = mkEl(host, "div", {
      cls: "pf-base-filter-bar",
      attr: { "data-pf-testid": "base-filter-bar" },
    });

    // 1. Live keyword filter (persistent input element — zero focus loss on typing)
    const searchInput = mkEl(bar, "input", {
      cls: "pf-base-filter-search",
      attr: {
        type: "search",
        placeholder: t("base_filter_search_placeholder"),
        "data-pf-testid": "base-filter-search",
      },
    }) as HTMLInputElement;
    this._searchInputEl = searchInput;
    searchInput.value = filters.query || "";
    searchInput.addEventListener("input", () => {
      if (this._searchDebounceTimer) clearTimeout(this._searchDebounceTimer);
      this._searchDebounceTimer = setTimeout(() => {
        this._searchDebounceTimer = null;
        this._updateFilters(
          { query: searchInput.value.trim() },
          { preserveSearchFocus: true }
        );
      }, 120);
    });
    searchInput.addEventListener("change", () => {
      if (this._searchDebounceTimer) {
        clearTimeout(this._searchDebounceTimer);
        this._searchDebounceTimer = null;
      }
      this._updateFilters(
        { query: searchInput.value.trim() },
        { preserveSearchFocus: true }
      );
    });
    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        if (this._searchDebounceTimer) {
          clearTimeout(this._searchDebounceTimer);
          this._searchDebounceTimer = null;
        }
        this._updateFilters(
          { query: searchInput.value.trim() },
          { preserveSearchFocus: true }
        );
      }
    });

    // 2. Topic / Domain dropdown
    this._domainSelectEl = null;
    if (domains.length > 0) {
      const domSel = mkEl(bar, "select", {
        cls: "pf-base-filter-select",
        attr: { "data-pf-testid": "base-filter-domain" },
      }) as HTMLSelectElement;
      this._domainSelectEl = domSel;
      const allOpt = mkEl(domSel, "option", {
        text: t("base_filter_all_domains"),
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
    this._collectionSelectEl = null;
    if (collectionPool.length > 0) {
      const colSel = mkEl(bar, "select", {
        cls: "pf-base-filter-select",
        attr: { "data-pf-testid": "base-filter-collection" },
      }) as HTMLSelectElement;
      this._collectionSelectEl = colSel;
      const allCol = mkEl(colSel, "option", {
        text: t("base_filter_all_collections"),
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
      ["all", t("base_filter_status_all")],
      ["pending", t("base_filter_status_pending")],
      ["done", t("base_filter_status_done")],
      ["deep_done", t("base_filter_status_deep_done")],
    ];
    const activeStatus = filters.status || "all";
    for (const [val, label] of statusChoices) {
      const btn = mkEl(pills, "button", {
        cls: `pf-base-filter-pill${activeStatus === val ? " is-active" : ""}`,
        text: label,
        attr: { type: "button", "data-pf-filter-status": val },
      });
      this._statusPillBtns.set(val, btn);
      btn.addEventListener("click", () => {
        this._updateFilters({ status: val }, { preserveSearchFocus: true });
      });
    }

    // 5. Minimum IF selector
    const ifSel = mkEl(bar, "select", {
      cls: "pf-base-filter-select pf-tnum",
      attr: { "data-pf-testid": "base-filter-if" },
    }) as HTMLSelectElement;
    this._ifSelectEl = ifSel;
    for (const [val, label] of [
      ["0", t("base_filter_if_any")],
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
      this._updateFilters(
        { minIf: Number(ifSel.value) || 0 },
        { preserveSearchFocus: true }
      );
    });

    const reset = mkEl(bar, "button", {
      cls: "pf-btn pf-btn-ghost pf-base-filter-reset",
      text: t("base_filter_reset"),
      attr: { type: "button", "data-pf-testid": "base-filter-reset" },
    });
    this._filterResetBtnEl = reset;
    reset.style.display = this._hasActiveFilters(filters) ? "" : "none";
    reset.addEventListener("click", () => {
      this._updateFilters({
        query: "",
        domain: "",
        collection: "",
        status: "all",
        minIf: 0,
      });
    });

    // Subtle right-aligned count indicator
    this._filterCountEl = mkEl(bar, "span", {
      cls: "pf-base-filter-count pf-tnum",
      text: "",
    });
    this._updateFilterBarMeta(rawItems.length, matchedCount, filters);
  }

  /** Surgical selection update: updates only selection bar + affected TR classes (<0.4ms). */
  private _syncSelectionUi(): void {
    const flatItems = this._currentFlatItems;
    if (this._tbodyEl) {
      const rows =
        this._tbodyEl.querySelectorAll<HTMLTableRowElement>("tr.pf-base-row");
      for (const tr of Array.from(rows)) {
        const key = tr.getAttribute("data-paper-key") || "";
        const sel = this._selectedKeys.has(key);
        tr.classList.toggle("is-selected", sel);
        const cb = tr.querySelector<HTMLInputElement>(
          "input[data-pf-select-key]"
        );
        if (cb && cb.checked !== sel) cb.checked = sel;
      }
    }
    if (this._selectAllCbEl) {
      const count = this._selectedKeys.size;
      this._selectAllCbEl.checked =
        flatItems.length > 0 && count === flatItems.length;
      this._selectAllCbEl.indeterminate = count > 0 && count < flatItems.length;
    }
    if (this._selectionSlotEl) {
      this._renderSelectionBar(this._selectionSlotEl, flatItems);
    }
  }

  private _renderSelectionBar(
    slot: HTMLElement,
    flatItems: RenderItem[]
  ): void {
    slot.textContent = "";
    const selectedItems = flatItems.filter((it) =>
      this._selectedKeys.has(it.row.zotero_key)
    );
    const selectedKeys = selectedItems.map((it) => it.row.zotero_key);
    if (selectedKeys.length === 0) return;

    const bar = mkEl(slot, "div", {
      cls: "pf-base-selection-bar",
      attr: { "data-pf-testid": "base-selection-bar" },
    });
    const left = mkEl(bar, "div", { cls: "pf-base-selection-left" });
    mkEl(left, "span", {
      cls: "pf-base-selection-count pf-tnum",
      text: t("base_selected_count").replace(
        "{n}",
        String(selectedKeys.length)
      ),
    });
    const clearBtn = mkEl(left, "button", {
      cls: "pf-btn pf-btn-ghost",
      text: t("base_clear_selection"),
      attr: { type: "button", "data-pf-testid": "base-clear-selection" },
    });
    clearBtn.addEventListener("click", () => {
      this._selectedKeys.clear();
      this._lastSelectedIdx = null;
      this._syncSelectionUi();
    });

    const right = mkEl(bar, "div", { cls: "pf-base-selection-actions" });
    if (selectedItems.length === 1 && selectedItems[0].row.has_pdf) {
      const openPdfBtn = mkEl(right, "button", {
        cls: "pf-btn",
        text: t("base_open_pdf"),
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
        text: t("base_open_diag"),
        attr: { type: "button", "data-pf-testid": "base-open-diag" },
      });
      diagBtn.addEventListener("click", () => {
        this.plugin.openOcrDiagnostic(diagTarget.row.zotero_key);
      });
    }

    const parseBtn = mkEl(right, "button", {
      cls: "pf-btn mod-cta",
      text: t("base_run_selected_ocr"),
      attr: { type: "button", "data-pf-testid": "base-run-selected-ocr" },
    });
    parseBtn.addEventListener("click", () => {
      void this.plugin.requestOcrRun({
        kind: "papers",
        keys: selectedKeys,
      });
    });
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
            label: t("base_open_pdf"),
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
        // Semantic <a> link (never <button>) so Obsidian never paints boxed button chrome around titles
        const titleLink = mkEl(titleWrap, "a", {
          cls: "pf-base-title-link",
          text: row.title || row.zotero_key,
          attr: {
            href: "#",
            role: "link",
            "data-pf-testid": "base-open-note",
            title: row.title || row.zotero_key,
          },
        });
        titleLink.addEventListener("click", (e) => {
          e.preventDefault();
          e.stopPropagation();
          const clickAction = String(
            this.config?.get?.("row_click_action") ?? "open_note"
          );
          const mod = resolveModEvent(e);
          if (!mod && clickAction === "open_pdf" && row.has_pdf) {
            void this.plugin.openPaperPdf(row.zotero_key);
            return;
          }
          if (
            !mod &&
            clickAction === "open_split" &&
            row.has_pdf &&
            this.plugin.openPaperSplitReading
          ) {
            void this.plugin.openPaperSplitReading(
              row.zotero_key,
              row.main_note_path
            );
            return;
          }
          this._openNote(row.main_note_path, e, row.zotero_key);
        });
        titleLink.addEventListener("auxclick", (e) => {
          if (e.button !== 1) return;
          e.preventDefault();
          e.stopPropagation();
          this._openNote(row.main_note_path, e, row.zotero_key);
        });
        bindObsidianHoverPreview(
          this.app ?? this.plugin.app,
          titleLink,
          "paperforge",
          row.main_note_path
        );
        const rowActions = mkEl(titleWrap, "div", {
          cls: "pf-base-row-actions",
        });
        if (row.has_pdf && this.plugin.openPaperSplitReading) {
          const splitBtn = createPfIconBtn(rowActions, {
            icon: "columns-2",
            label: t("ctx_split_reading"),
            size: 13,
            cls: "pf-base-row-action-btn",
            testid: "base-row-split",
          });
          splitBtn.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            void this.plugin.openPaperSplitReading?.(
              row.zotero_key,
              row.main_note_path
            );
          });
        }
        const moreBtn = createPfIconBtn(rowActions, {
          icon: "more-horizontal",
          label: t("base_row_more_actions"),
          size: 13,
          cls: "pf-base-row-action-btn",
          testid: "base-row-more",
        });
        moreBtn.addEventListener("click", (e) => {
          e.preventDefault();
          e.stopPropagation();
          this._openRowContextMenu(e, row);
        });
        break;
      }
      case "first_author":
        mkEl(td, "span", {
          cls: "pf-base-text-ellipsis",
          text: row.first_author || "—",
          attr: row.first_author ? { title: row.first_author } : undefined,
        });
        break;
      case "year":
        td.textContent = row.year || "—";
        break;
      case "journal":
        mkEl(td, "span", {
          cls: "pf-base-text-ellipsis pf-base-muted",
          text: row.journal || "—",
          attr: row.journal ? { title: row.journal } : undefined,
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
          td.setAttribute("title", t("base_if_tip_openalex"));
        } else {
          td.textContent = val;
          const tipParts: string[] = [];
          if (src === "jcr") tipParts.push(t("base_if_tip_jcr"));
          else if (src === "zotero_plugin")
            tipParts.push(t("base_if_tip_zotero"));
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
          const domWrap = mkEl(td, "span", {
            cls: "pf-base-domain-chip",
            attr: { title: row.domain },
          });
          const dot = mkEl(domWrap, "span", { cls: "pf-base-dot" });
          dot.style.background = categoricalColor(row.domain);
          mkEl(domWrap, "span", {
            cls: "pf-base-domain-label",
            text: row.domain,
          });
        }
        break;
      }
      case "annotations": {
        const totalAnns =
          (row.user_ann_count || 0) + (row.agent_ann_count || 0);
        const memCount = row.memory_facet_count || 0;
        const parts: string[] = [];
        if (totalAnns > 0)
          parts.push(
            t("base_count_annotations").replace("{n}", String(totalAnns))
          );
        if (memCount > 0)
          parts.push(t("base_count_memory").replace("{n}", String(memCount)));
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
          text:
            row.deep_reading_status === "done"
              ? t("base_status_deep_done")
              : "—",
        });
        break;
      default: {
        const rawVal = entry?.getValue?.(col.id);
        const renderCtx = (
          this.app as unknown as { renderContext?: unknown } | undefined
        )?.renderContext;
        if (
          rawVal &&
          typeof (rawVal as { renderTo?: unknown }).renderTo === "function" &&
          renderCtx
        ) {
          const valHost = mkEl(td, "div", { cls: "pf-base-native-val" });
          try {
            (
              rawVal as {
                renderTo: (el: HTMLElement, ctx: unknown) => void;
              }
            ).renderTo(valHost, renderCtx);
            if (valHost.childNodes.length > 0 || valHost.textContent) {
              break;
            }
          } catch {
            valHost.remove();
          }
        }
        const val = readValueString(rawVal);
        const spanEl = mkEl(td, "span", {
          cls: val ? "pf-base-text-ellipsis" : "pf-base-muted",
          text: val || "—",
          attr: val ? { title: val } : undefined,
        });
        if (col.id.startsWith("note.") && entry?.file) {
          td.classList.add("pf-base-cell-editable");
          td.title = t("base_inline_edit_hint") || "Double-click to edit";
          const startInline = (ev: Event) => {
            ev.stopPropagation();
            const curVal = spanEl.classList.contains("pf-base-muted")
              ? ""
              : spanEl.textContent || "";
            this._beginInlineEdit(td, spanEl, col, item, curVal);
          };
          td.addEventListener("dblclick", startInline);
          const editBtn = mkEl(td, "button", {
            cls: "pf-base-inline-edit-btn",
            text: "✎",
            attr: {
              type: "button",
              "aria-label":
                t("base_inline_edit_hint") || "Double-click to edit",
              "data-pf-testid": "base-inline-edit-btn",
            },
          });
          editBtn.addEventListener("click", startInline);
        }
        break;
      }
    }
  }

  private _beginInlineEdit(
    td: HTMLElement,
    spanEl: HTMLElement,
    col: ColumnSpec,
    item: RenderItem,
    initialVal: string
  ): void {
    if (td.querySelector(".pf-base-inline-input")) return;
    const propName = col.id.startsWith("note.")
      ? col.id.slice("note.".length)
      : col.key;
    const file = item.entry?.file;
    if (!propName || !file) return;

    spanEl.style.display = "none";
    const editBtn = td.querySelector(
      ".pf-base-inline-edit-btn"
    ) as HTMLElement | null;
    if (editBtn) editBtn.style.display = "none";

    const doc = td.ownerDocument || document;
    const input = doc.createElement("input");
    input.type = "text";
    input.className = "pf-base-inline-input";
    input.value = initialVal;
    input.setAttribute("data-pf-testid", "base-inline-input");
    td.appendChild(input);
    input.focus();
    input.select();

    let done = false;
    const restore = (nextText: string) => {
      if (done) return;
      done = true;
      input.remove();
      spanEl.style.display = "";
      spanEl.textContent = nextText || "—";
      spanEl.className = nextText ? "pf-base-text-ellipsis" : "pf-base-muted";
      if (nextText) spanEl.setAttribute("title", nextText);
      else spanEl.removeAttribute("title");
      if (editBtn) editBtn.style.display = "";
    };

    const commit = async () => {
      if (done) return;
      const nextVal = input.value.trim();
      restore(nextVal);
      if (nextVal === initialVal) return;
      if (typeof this.plugin.updateNoteProperty === "function") {
        try {
          await this.plugin.updateNoteProperty(file, propName, nextVal);
          new Notice(t("base_inline_edit_saved") || "Property updated", 2000);
        } catch (err) {
          spanEl.textContent = initialVal || "—";
          spanEl.className = initialVal
            ? "pf-base-text-ellipsis"
            : "pf-base-muted";
          if (initialVal) spanEl.setAttribute("title", initialVal);
          else spanEl.removeAttribute("title");
          const detail =
            err instanceof Error ? err.message : String(err || "Unknown error");
          new Notice(
            `${t("settings_save_failed") || "Save failed"}: ${detail}`,
            4000
          );
        }
      }
    };

    input.addEventListener("keydown", (ev) => {
      ev.stopPropagation();
      if (ev.key === "Enter") {
        ev.preventDefault();
        void commit();
      } else if (ev.key === "Escape") {
        ev.preventDefault();
        restore(initialVal);
      }
    });
    input.addEventListener("blur", () => {
      void commit();
    });
  }

  private _renderSlotIntoFragment(
    frag: DocumentFragment,
    slot: RenderSlot,
    columns: ColumnSpec[],
    showCheckboxes: boolean,
    totalColSpan: number
  ): void {
    if (slot.kind === "group") {
      const isCollapsed = this._collapsedGroups.has(slot.label);
      const gTr = mkEl(frag, "tr", {
        cls: `pf-base-group-row${isCollapsed ? " is-collapsed" : ""}`,
        attr: {
          "data-pf-group": slot.label,
          "aria-expanded": String(!isCollapsed),
          title: t("base_group_toggle_tip"),
        },
      });
      gTr.addEventListener("click", () => {
        this._toggleGroupCollapse(slot.label);
      });
      const gTd = mkEl(gTr, "td", {
        attr: { colspan: String(totalColSpan) },
      });
      const gWrap = mkEl(gTd, "div", { cls: "pf-base-group-head" });
      const chev = mkEl(gWrap, "span", { cls: "pf-base-group-chevron" });
      setPfIcon(chev, isCollapsed ? "chevron-right" : "chevron-down", 12);
      const gDot = mkEl(gWrap, "span", { cls: "pf-base-dot" });
      gDot.style.background = categoricalColor(slot.label);
      mkEl(gWrap, "span", {
        cls: "pf-base-group-name",
        text: slot.label,
      });
      mkEl(gWrap, "span", {
        cls: "pf-base-group-count pf-tnum",
        text: t("base_group_count").replace("{n}", String(slot.count)),
      });
      return;
    }

    const { item, flatIndex } = slot;
    const row = item.row;
    const isSelected = this._selectedKeys.has(row.zotero_key);
    const isKbActive = this._focusedRowIdx === flatIndex;
    const tr = mkEl(frag, "tr", {
      cls: `pf-base-row${isSelected ? " is-selected" : ""}${isKbActive ? " is-kb-active" : ""}`,
      attr: {
        "data-paper-key": row.zotero_key,
        "data-flat-idx": String(flatIndex),
      },
    });
    tr.addEventListener("click", () => {
      this._focusedRowIdx = flatIndex;
      this._syncFocusedRowUi(false);
    });
    tr.addEventListener("contextmenu", (e) => this._openRowContextMenu(e, row));

    if (showCheckboxes) {
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
          const start = Math.min(this._lastSelectedIdx, flatIndex);
          const end = Math.max(this._lastSelectedIdx, flatIndex);
          // Iterate visible row slots only so collapsed-group hidden papers are never selected
          for (const s of this._currentSlots) {
            if (s.kind !== "row") continue;
            if (s.flatIndex < start || s.flatIndex > end) continue;
            const targetKey = s.item.row.zotero_key;
            if (!targetKey) continue;
            if (checked) this._selectedKeys.add(targetKey);
            else this._selectedKeys.delete(targetKey);
          }
        } else {
          if (checked) this._selectedKeys.add(row.zotero_key);
          else this._selectedKeys.delete(row.zotero_key);
        }
        this._pendingShiftKey = false;
        this._lastSelectedIdx = flatIndex;
        this._syncSelectionUi();
      });
    }

    for (const col of columns) {
      this._renderCell(tr, col, item);
    }
  }

  private _renderVirtualWindow(force = false): void {
    const tbody = this._tbodyEl;
    const wrap = this._tableWrapEl;
    if (!tbody || !wrap || !this._virtualActive) return;

    const VIRTUAL_EST_ROW_H = 34;
    const VIRTUAL_OVERSCAN = 12;
    const total = this._currentSlots.length;
    if (total === 0) {
      tbody.textContent = "";
      return;
    }

    const viewportH = Math.max(320, wrap.clientHeight || 600);
    const scrollTop = Math.max(0, wrap.scrollTop || 0);
    const start = Math.max(
      0,
      Math.floor(scrollTop / VIRTUAL_EST_ROW_H) - VIRTUAL_OVERSCAN
    );
    const end = Math.min(
      total,
      Math.ceil((scrollTop + viewportH) / VIRTUAL_EST_ROW_H) + VIRTUAL_OVERSCAN
    );

    if (
      !force &&
      start === this._virtualRange.start &&
      end === this._virtualRange.end
    ) {
      return;
    }
    this._virtualRange = { start, end };

    const doc = tbody.ownerDocument || document;
    const frag = doc.createDocumentFragment();
    const columns = this._currentColumns;
    const showCheckboxes = this.config?.get?.("show_checkboxes") !== false;
    const totalColSpan = columns.length + (showCheckboxes ? 1 : 0);

    if (start > 0) {
      const topSpacer = mkEl(frag, "tr", { cls: "pf-base-virtual-spacer" });
      const topTd = mkEl(topSpacer, "td", {
        attr: { colspan: String(totalColSpan) },
      });
      topTd.style.height = `${start * VIRTUAL_EST_ROW_H}px`;
    }

    for (let idx = start; idx < end; idx += 1) {
      this._renderSlotIntoFragment(
        frag,
        this._currentSlots[idx],
        columns,
        showCheckboxes,
        totalColSpan
      );
    }

    if (end < total) {
      const botSpacer = mkEl(frag, "tr", { cls: "pf-base-virtual-spacer" });
      const botTd = mkEl(botSpacer, "td", {
        attr: { colspan: String(totalColSpan) },
      });
      botTd.style.height = `${(total - end) * VIRTUAL_EST_ROW_H}px`;
    }

    tbody.textContent = "";
    tbody.appendChild(frag);
  }

  /** Append the next chunk of rows in a single DocumentFragment for silky 60fps scrolling. */
  private _appendNextChunk(chunkSize: number): void {
    const tbody = this._tbodyEl;
    if (!tbody) return;
    this._disconnectLoadMoreObserver();
    const existingSentinel = tbody.querySelector("tr.pf-base-load-more-row");
    if (existingSentinel) existingSentinel.remove();

    const doc = tbody.ownerDocument || document;
    const frag = doc.createDocumentFragment();
    const columns = this._currentColumns;
    const showCheckboxes = this.config?.get?.("show_checkboxes") !== false;
    const totalColSpan = columns.length + (showCheckboxes ? 1 : 0);
    let papersAppended = 0;

    while (
      this._renderedSlotCount < this._currentSlots.length &&
      papersAppended < chunkSize
    ) {
      const slot = this._currentSlots[this._renderedSlotCount++];
      if (slot.kind === "row") {
        papersAppended += 1;
        this._renderedPaperCount += 1;
      }
      this._renderSlotIntoFragment(
        frag,
        slot,
        columns,
        showCheckboxes,
        totalColSpan
      );
    }

    const remainingPapers =
      this._currentFlatItems.length - this._renderedPaperCount;
    if (remainingPapers > 0) {
      const sentinelTr = mkEl(frag, "tr", { cls: "pf-base-load-more-row" });
      const sentinelTd = mkEl(sentinelTr, "td", {
        attr: { colspan: String(totalColSpan) },
      });
      const moreBtn = mkEl(sentinelTd, "button", {
        cls: "pf-base-load-more-btn",
        text: t("base_load_more").replace(
          "{remaining}",
          String(remainingPapers)
        ),
        attr: { type: "button", "data-pf-testid": "base-load-more" },
      });
      moreBtn.addEventListener("click", () => {
        this._appendNextChunk(LOAD_MORE_CHUNK_SIZE);
      });
      tbody.appendChild(frag);

      if (typeof IntersectionObserver !== "undefined") {
        this._loadMoreObserver = new IntersectionObserver(
          (entries) => {
            if (entries.some((e) => e.isIntersecting)) {
              this._appendNextChunk(LOAD_MORE_CHUNK_SIZE);
            }
          },
          { rootMargin: "420px 0px" }
        );
        this._loadMoreObserver.observe(sentinelTr);
      }
    } else {
      tbody.appendChild(frag);
    }
  }

  private _openNote(
    notePath: string,
    evt?: MouseEvent | KeyboardEvent,
    zoteroKey?: string
  ): void {
    const app = this.app ?? this.plugin.app;
    const mod = resolveModEvent(evt);
    const auxTab =
      evt instanceof MouseEvent && evt.button === 1 ? ("tab" as const) : mod;
    const normPath = (notePath || "").replace(/\\/g, "/");
    const vaultApi = app?.vault as
      | {
          getAbstractFileByPath?: (p: string) => {
            path?: string;
            basename?: string;
            extension?: string;
            stat?: { size?: number };
          } | null;
          getMarkdownFiles?: () => Array<{
            path: string;
            basename?: string;
            extension?: string;
            stat?: { size?: number };
          }>;
        }
      | undefined;

    if (typeof vaultApi?.getAbstractFileByPath === "function") {
      const direct = normPath ? vaultApi.getAbstractFileByPath(normPath) : null;
      const directIsFile =
        Boolean(direct) &&
        "extension" in (direct as Record<string, unknown>) &&
        ((direct as { stat?: { size?: number } })?.stat?.size ?? 1) > 0;
      let targetFile = directIsFile ? direct : null;

      if (
        !targetFile &&
        zoteroKey &&
        typeof vaultApi.getMarkdownFiles === "function"
      ) {
        const mdFiles = vaultApi.getMarkdownFiles();
        const matches = mdFiles.filter(
          (f) =>
            f.basename === zoteroKey ||
            (typeof f.basename === "string" &&
              f.basename.startsWith(`${zoteroKey} - `))
        );
        targetFile =
          matches.find((f) => (f.stat?.size ?? 1) > 0) ??
          (direct && "extension" in (direct as Record<string, unknown>)
            ? direct
            : null);
      } else if (
        !targetFile &&
        direct &&
        "extension" in (direct as Record<string, unknown>)
      ) {
        targetFile = direct;
      }

      if (targetFile) {
        const wsAny = app?.workspace as
          | {
              getLeaf?: (
                newLeaf?: boolean | "tab" | "split" | "window"
              ) => { openFile?: (f: unknown) => Promise<void> } | null;
            }
          | undefined;
        if (typeof wsAny?.getLeaf === "function") {
          const leaf = wsAny.getLeaf(auxTab || false);
          if (typeof leaf?.openFile === "function") {
            void leaf.openFile(targetFile);
            return;
          }
        }
        const resolvedPath = targetFile.path || normPath;
        if (auxTab) {
          void app.workspace?.openLinkText?.(resolvedPath, "", auxTab);
        } else {
          void app.workspace?.openLinkText?.(resolvedPath, "");
        }
        return;
      }

      new Notice(t("paper_note_missing") || "Note not found in vault.");
      return;
    }

    if (!notePath) {
      new Notice(t("paper_note_missing") || "Note path unavailable.");
      return;
    }
    if (auxTab) {
      void app.workspace?.openLinkText?.(notePath, "", auxTab);
      return;
    }
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
      onOpenNote: () =>
        this._openNote(row.main_note_path, event, row.zotero_key),
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

  private _ensureCollapsedGroupsLoaded(): void {
    if (this._collapsedGroupsLoaded) return;
    this._collapsedGroupsLoaded = true;
    const raw = this.config?.get?.("collapsed_groups");
    if (Array.isArray(raw)) {
      for (const g of raw) {
        if (typeof g === "string" && g) this._collapsedGroups.add(g);
      }
    }
  }

  private _toggleGroupCollapse(label: string): void {
    if (this._collapsedGroups.has(label)) {
      this._collapsedGroups.delete(label);
    } else {
      this._collapsedGroups.add(label);
    }
    try {
      this.config?.set?.("collapsed_groups", Array.from(this._collapsedGroups));
    } catch {
      // Optional in minimal mock configs
    }
    this._renderBodyOnly();
  }

  private _getActiveSort(): { key: string; dir: "ASC" | "DESC" } | null {
    if (this._localSort) return this._localSort;
    try {
      const cfgSort = this.config?.getSort?.();
      if (
        Array.isArray(cfgSort) &&
        cfgSort.length > 0 &&
        cfgSort[0]?.property
      ) {
        const clean = String(cfgSort[0].property).replace(
          /^(note|file|formula)\./,
          ""
        );
        return {
          key: clean === "file.name" ? "title" : clean,
          dir: cfgSort[0].direction === "DESC" ? "DESC" : "ASC",
        };
      }
    } catch {
      // ignore
    }
    return null;
  }

  private _toggleColumnSort(col: ColumnSpec): void {
    const cur = this._getActiveSort();
    let next: { key: string; dir: "ASC" | "DESC" } | null;
    if (!cur || cur.key !== col.key) {
      next = { key: col.key, dir: "ASC" };
    } else if (cur.dir === "ASC") {
      next = { key: col.key, dir: "DESC" };
    } else {
      next = null;
    }
    this._localSort = next;
    try {
      this.config?.set?.(
        "sort",
        next ? [{ property: col.id, direction: next.dir }] : []
      );
    } catch {
      // Optional in minimal mock configs
    }
    this._renderBodyOnly();
  }

  private _sortItems(
    items: RenderItem[],
    sort: { key: string; dir: "ASC" | "DESC" } | null
  ): RenderItem[] {
    if (!sort) return items;
    const { key, dir } = sort;
    const mul = dir === "DESC" ? -1 : 1;
    const readCellVal = (item: RenderItem): string | number => {
      const r = item.row;
      switch (key) {
        case "title":
        case "file.name":
          return (r.title || r.zotero_key || "").toLowerCase();
        case "first_author":
          return (r.first_author || "").toLowerCase();
        case "year": {
          const n = Number.parseFloat(String(r.year || ""));
          return Number.isFinite(n) ? n : -Infinity;
        }
        case "journal":
          return (r.journal || "").toLowerCase();
        case "impact_factor": {
          const n = Number.parseFloat(String(r.impact_factor || ""));
          return Number.isFinite(n) ? n : -Infinity;
        }
        case "domain":
          return (r.domain || "").toLowerCase();
        case "annotations":
          return (
            (r.user_ann_count || 0) +
            (r.agent_ann_count || 0) +
            (r.memory_facet_count || 0)
          );
        case "ocr_status":
          return `${r.ocr_status || ""}_${r.deep_reading_status || ""}`;
        default:
          return readValueString(
            item.entry?.getValue?.(key as obsidian.BasesPropertyId) ??
              item.entry?.getValue?.(`note.${key}` as obsidian.BasesPropertyId)
          ).toLowerCase();
      }
    };
    return [...items].sort((a, b) => {
      const va = readCellVal(a);
      const vb = readCellVal(b);
      if (typeof va === "number" && typeof vb === "number") {
        return (va - vb) * mul;
      }
      return String(va).localeCompare(String(vb)) * mul;
    });
  }

  private _readSavedColumnSizes(): Record<string, number> {
    const raw =
      (this.config?.get?.("columnSize") as
        | Record<string, unknown>
        | undefined) ??
      (this.config?.get?.("widths") as Record<string, unknown> | undefined);
    if (!raw || typeof raw !== "object") return {};
    const out: Record<string, number> = {};
    for (const [k, v] of Object.entries(raw)) {
      const n = Number(v);
      if (Number.isFinite(n) && n >= 40) out[k] = Math.round(n);
    }
    return out;
  }

  private _bindColumnResize(
    resizer: HTMLElement,
    th: HTMLElement,
    colEl: HTMLElement,
    col: ColumnSpec
  ): void {
    resizer.addEventListener("click", (e) => e.stopPropagation());
    resizer.addEventListener("pointerdown", (startEv: PointerEvent) => {
      startEv.preventDefault();
      startEv.stopPropagation();
      const doc = resizer.ownerDocument || document;
      const startX = startEv.clientX;
      const startW = Math.max(48, th.getBoundingClientRect().width || 120);
      let latestW = startW;
      resizer.classList.add("is-dragging");

      const onMove = (moveEv: PointerEvent) => {
        latestW = Math.max(48, Math.round(startW + (moveEv.clientX - startX)));
        colEl.style.width = `${latestW}px`;
      };
      const cleanup = () => {
        doc.removeEventListener("pointermove", onMove);
        doc.removeEventListener("pointerup", onUp);
        doc.removeEventListener("pointercancel", onUp);
        resizer.classList.remove("is-dragging");
        this._activeResizeCleanup = null;
      };
      const onUp = () => {
        cleanup();
        const prev = this._readSavedColumnSizes();
        const next: Record<string, number> = {
          ...prev,
          [String(col.id)]: latestW,
        };
        try {
          this.config?.set?.("columnSize", next);
        } catch {
          // Optional in minimal mock configs
        }
      };
      this._activeResizeCleanup?.();
      this._activeResizeCleanup = cleanup;
      doc.addEventListener("pointermove", onMove);
      doc.addEventListener("pointerup", onUp);
      doc.addEventListener("pointercancel", onUp);
    });
  }

  private _renderSummaryFooter(
    tfoot: HTMLElement,
    columns: ColumnSpec[],
    flatItems: RenderItem[],
    showCheckboxes: boolean
  ): void {
    tfoot.textContent = "";
    if (
      this.config?.get?.("show_summary_footer") !== true ||
      flatItems.length === 0
    ) {
      tfoot.style.display = "none";
      return;
    }
    tfoot.style.display = "";
    const tr = mkEl(tfoot, "tr", {
      cls: "pf-base-summary-row",
      attr: { "data-pf-testid": "base-summary-footer" },
    });
    if (showCheckboxes) {
      mkEl(tr, "td", { cls: "pf-base-cell-check" });
    }
    for (const col of columns) {
      const td = mkEl(tr, "td", {
        cls: col.numeric ? "pf-tnum is-num" : "",
      });
      if (col.key === "title" || col.key === "file.name") {
        td.textContent = t("base_summary_papers").replace(
          "{n}",
          String(flatItems.length)
        );
      } else if (col.key === "impact_factor") {
        const vals = flatItems
          .map((it) => Number.parseFloat(String(it.row.impact_factor || "")))
          .filter((n) => Number.isFinite(n));
        if (vals.length > 0) {
          const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
          td.textContent = t("base_summary_if_avg").replace(
            "{val}",
            avg.toFixed(1)
          );
        }
      } else if (col.key === "year") {
        const yrs = flatItems
          .map((it) => Number.parseInt(String(it.row.year || ""), 10))
          .filter((n) => Number.isFinite(n));
        if (yrs.length > 0) {
          const minY = Math.min(...yrs);
          const maxY = Math.max(...yrs);
          td.textContent = minY === maxY ? String(minY) : `${minY}–${maxY}`;
        }
      }
    }
  }

  private _renderActivityStrip(rawFlatItems: RenderItem[]): void {
    if (!this._activitySlotEl) return;
    this._activitySlotEl.textContent = "";
    const activeProg = this.plugin._ocrProgress;
    const isRunningAny =
      Boolean(activeProg && activeProg.key) ||
      rawFlatItems.some((it) =>
        this.plugin.isOcrRunningForKey(it.row.zotero_key)
      );
    if (!isRunningAny) return;
    const strip = mkEl(this._activitySlotEl, "div", {
      cls: "pf-base-activity-strip pf-tnum",
    });
    const iconHost = mkEl(strip, "span", { cls: "pf-base-activity-icon" });
    setPfIcon(iconHost, "refresh-cw", 13);
    const countText =
      activeProg && activeProg.total > 0
        ? ` ${activeProg.current} / ${activeProg.total}`
        : "";
    mkEl(strip, "span", {
      text: t("base_parsing_progress").replace("{progress}", countText),
    });
  }

  private _ensureShell(): void {
    const root = this.containerEl;
    if (!root) return;
    if (
      this._shellMounted &&
      this._activitySlotEl?.parentElement === root &&
      this._tableWrapEl?.parentElement === root
    ) {
      return;
    }
    root.textContent = "";
    root.classList.add("pf-base-view-root");
    this._activitySlotEl = mkEl(root, "div", { cls: "pf-base-activity-slot" });
    this._filterSlotEl = mkEl(root, "div", { cls: "pf-base-filter-slot" });
    this._missingPdfSlotEl = mkEl(root, "div", {
      cls: "pf-base-missing-pdf-slot",
    });
    this._emptySlotEl = mkEl(root, "div", { cls: "pf-base-empty-slot" });
    this._selectionSlotEl = mkEl(root, "div", {
      cls: "pf-base-selection-slot",
    });
    this._tableWrapEl = mkEl(root, "div", {
      cls: "pf-base-table-wrap",
      attr: { tabindex: "0" },
    });
    this._tableWrapEl.addEventListener("keydown", (e) =>
      this._handleTableKeyDown(e)
    );
    this._tableScrollHandler = () => {
      if (!this._tableWrapEl) return;
      this._tableWrapEl.classList.toggle(
        "is-scrolled",
        this._tableWrapEl.scrollTop > 2
      );
      if (!this._virtualActive) return;
      if (typeof requestAnimationFrame === "function") {
        if (this._virtualRafId !== null) return;
        this._virtualRafId = requestAnimationFrame(() => {
          this._virtualRafId = null;
          this._renderVirtualWindow();
        });
      } else {
        this._renderVirtualWindow();
      }
    };
    this._tableWrapEl.addEventListener("scroll", this._tableScrollHandler, {
      passive: true,
    });
    this._tableEl = mkEl(this._tableWrapEl, "table", { cls: "pf-base-table" });
    this._colgroupEl = mkEl(this._tableEl, "colgroup");
    this._theadEl = mkEl(this._tableEl, "thead");
    this._tbodyEl = mkEl(this._tableEl, "tbody");
    this._tfootEl = mkEl(this._tableEl, "tfoot");
    this._searchInputEl = null;
    this._filterOptionSig = "";
    this._shellMounted = true;
  }

  private _syncFocusedRowUi(scrollIntoView: boolean): void {
    if (this._currentFlatItems.length === 0) {
      this._focusedRowIdx = -1;
    } else if (this._focusedRowIdx >= this._currentFlatItems.length) {
      this._focusedRowIdx = this._currentFlatItems.length - 1;
    }
    if (this._virtualActive && this._focusedRowIdx >= 0 && this._tableWrapEl) {
      const slotIdx = this._currentSlots.findIndex(
        (s) => s.kind === "row" && s.flatIndex === this._focusedRowIdx
      );
      if (
        slotIdx >= 0 &&
        (slotIdx < this._virtualRange.start ||
          slotIdx >= this._virtualRange.end)
      ) {
        this._tableWrapEl.scrollTop = Math.max(0, slotIdx * 34);
        this._renderVirtualWindow(true);
      }
    } else if (
      this._focusedRowIdx >= this._renderedPaperCount &&
      this._renderedSlotCount < this._currentSlots.length
    ) {
      this._appendNextChunk(
        Math.max(
          INITIAL_CHUNK_SIZE,
          this._focusedRowIdx - this._renderedPaperCount + 1
        )
      );
    }
    if (!this._tbodyEl) return;
    let activeTr: HTMLTableRowElement | null = null;
    const rows =
      this._tbodyEl.querySelectorAll<HTMLTableRowElement>("tr.pf-base-row");
    for (const tr of Array.from(rows)) {
      const idx = Number(tr.getAttribute("data-flat-idx") ?? "-1");
      const active = this._focusedRowIdx >= 0 && idx === this._focusedRowIdx;
      tr.classList.toggle("is-kb-active", active);
      if (active) activeTr = tr;
    }
    if (scrollIntoView && activeTr) {
      activeTr.scrollIntoView?.({ block: "nearest" });
    }
  }

  private _handleTableKeyDown(e: KeyboardEvent): void {
    const target = e.target as HTMLElement | null;
    const tag = target?.tagName?.toLowerCase();
    if (
      tag === "input" ||
      tag === "textarea" ||
      tag === "select" ||
      target?.isContentEditable
    ) {
      return;
    }
    if (e.key === "/" && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault();
      this._searchInputEl?.focus();
      return;
    }
    if (this._currentFlatItems.length === 0) return;

    if (e.key === "ArrowDown" || (e.key === "j" && !e.ctrlKey && !e.metaKey)) {
      e.preventDefault();
      this._focusedRowIdx =
        this._focusedRowIdx < 0
          ? 0
          : Math.min(
              this._currentFlatItems.length - 1,
              this._focusedRowIdx + 1
            );
      this._syncFocusedRowUi(true);
      return;
    }
    if (e.key === "ArrowUp" || (e.key === "k" && !e.ctrlKey && !e.metaKey)) {
      e.preventDefault();
      this._focusedRowIdx =
        this._focusedRowIdx <= 0 ? 0 : this._focusedRowIdx - 1;
      this._syncFocusedRowUi(true);
      return;
    }
    if (e.key === "Escape") {
      if (this._focusedRowIdx >= 0 || this._selectedKeys.size > 0) {
        this._focusedRowIdx = -1;
        this._selectedKeys.clear();
        this._lastSelectedIdx = null;
        this._syncFocusedRowUi(false);
        this._syncSelectionUi();
      }
      return;
    }

    if (this._focusedRowIdx < 0) return;
    const item = this._currentFlatItems[this._focusedRowIdx];
    if (!item) return;
    const row = item.row;

    if (e.key === " " || (e.key === "x" && !e.ctrlKey && !e.metaKey)) {
      e.preventDefault();
      if (this._selectedKeys.has(row.zotero_key)) {
        this._selectedKeys.delete(row.zotero_key);
      } else {
        this._selectedKeys.add(row.zotero_key);
      }
      this._lastSelectedIdx = this._focusedRowIdx;
      this._syncSelectionUi();
      return;
    }
    if (e.key === "p" && !e.ctrlKey && !e.metaKey) {
      if (row.has_pdf) {
        e.preventDefault();
        void this.plugin.openPaperPdf(row.zotero_key);
      }
      return;
    }
    if (e.key === "s" && !e.ctrlKey && !e.metaKey) {
      if (row.has_pdf && this.plugin.openPaperSplitReading) {
        e.preventDefault();
        void this.plugin.openPaperSplitReading(
          row.zotero_key,
          row.main_note_path
        );
      }
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      if (e.altKey && row.has_pdf && this.plugin.openPaperSplitReading) {
        void this.plugin.openPaperSplitReading(
          row.zotero_key,
          row.main_note_path
        );
      } else if ((e.ctrlKey || e.metaKey) && row.has_pdf) {
        void this.plugin.openPaperPdf(row.zotero_key);
      } else if (row.main_note_path) {
        this._openNote(row.main_note_path, e, row.zotero_key);
      } else if (row.has_pdf) {
        void this.plugin.openPaperPdf(row.zotero_key);
      }
    }
  }

  private _renderBodyOnly(): void {
    const root = this.containerEl;
    if (!root || !this._shellMounted) {
      this.render();
      return;
    }
    this._disconnectLoadMoreObserver();
    this._ensureCollapsedGroupsLoaded();

    const snapshot = this.plugin.getBaseSnapshotCache();
    const rawGroups = this._collectGroups(snapshot);
    const rawFlatItems = rawGroups.flatMap((g) => g.items);
    this._lastRawItems = rawFlatItems;
    const filters = this._getFilters();
    const activeSort = this._getActiveSort();
    const groups = rawGroups
      .map((g) => ({
        groupLabel: g.groupLabel,
        items: this._sortItems(
          g.items.filter((it) => this._matchesFilters(it.row, filters)),
          activeSort
        ),
      }))
      .filter((g) => g.items.length > 0);
    const flatItems = groups.flatMap((g) => g.items);
    const visibleKeySet = new Set(flatItems.map((it) => it.row.zotero_key));

    for (const k of Array.from(this._selectedKeys)) {
      if (!visibleKeySet.has(k)) this._selectedKeys.delete(k);
    }
    this._currentFlatItems = flatItems;

    if (this._filterSlotEl && this._searchInputEl?.isConnected) {
      this._updateFilterBarMeta(rawFlatItems.length, flatItems.length, filters);
    }

    if (this._emptySlotEl) this._emptySlotEl.textContent = "";
    if (flatItems.length === 0) {
      if (this._selectionSlotEl) this._selectionSlotEl.textContent = "";
      if (this._tableWrapEl) this._tableWrapEl.style.display = "none";
      if (this._emptySlotEl) {
        const empty = mkEl(this._emptySlotEl, "div", { cls: "pf-base-empty" });
        mkEl(empty, "span", {
          text: this._loadingSnapshot
            ? t("pdf_loading")
            : this._hasActiveFilters(filters)
              ? t("base_empty_filtered")
              : t("base_empty_hint"),
        });
        if (this._hasActiveFilters(filters)) {
          const resetBtn = mkEl(empty, "button", {
            cls: "pf-btn",
            text: t("base_empty_reset_filters"),
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
            text: t("base_sync_library"),
            attr: { type: "button", "data-pf-testid": "base-sync-library" },
          });
          syncEmptyBtn.addEventListener("click", () => {
            this.plugin.triggerManualSync();
          });
        }
      }
      return;
    }

    if (this._tableWrapEl) this._tableWrapEl.style.display = "";
    if (this._selectionSlotEl) {
      this._renderSelectionBar(this._selectionSlotEl, flatItems);
    }

    const showCheckboxes = this.config?.get?.("show_checkboxes") !== false;
    const columns = this._resolveColumns();
    this._currentColumns = columns;
    const colWidths = computeColumnWidths(columns);
    const savedSizes = this._readSavedColumnSizes();

    if (this._colgroupEl && this._theadEl) {
      this._colgroupEl.textContent = "";
      this._theadEl.textContent = "";
      if (showCheckboxes) {
        const checkCol = mkEl(this._colgroupEl, "col", {
          cls: "pf-base-colgroup-check",
        });
        checkCol.style.width = "34px";
      }
      const colEls: HTMLElement[] = [];
      columns.forEach((col, i) => {
        const colEl = mkEl(this._colgroupEl!, "col", {
          cls: `pf-base-colgroup-${col.key.replace(/[^a-z0-9_-]/gi, "-")}`,
        });
        const savedW = savedSizes[String(col.id)] ?? savedSizes[col.key];
        colEl.style.width = savedW ? `${savedW}px` : colWidths[i];
        colEls.push(colEl);
      });

      const headRow = mkEl(this._theadEl, "tr");
      this._selectAllCbEl = null;
      if (showCheckboxes) {
        const checkTh = mkEl(headRow, "th", { cls: "pf-base-col-check" });
        const selectAllCb = mkEl(checkTh, "input", {
          attr: {
            type: "checkbox",
            "aria-label": t("base_select_all_aria"),
            "data-pf-testid": "base-select-all",
          },
        }) as HTMLInputElement;
        this._selectAllCbEl = selectAllCb;
        selectAllCb.checked =
          flatItems.length > 0 && this._selectedKeys.size === flatItems.length;
        selectAllCb.indeterminate =
          this._selectedKeys.size > 0 &&
          this._selectedKeys.size < flatItems.length;
        selectAllCb.addEventListener("change", () => {
          if (selectAllCb.checked) {
            for (const it of flatItems)
              this._selectedKeys.add(it.row.zotero_key);
          } else {
            this._selectedKeys.clear();
          }
          this._lastSelectedIdx = null;
          this._syncSelectionUi();
        });
      }

      columns.forEach((col, idx) => {
        const isSorted = activeSort?.key === col.key;
        const th = mkEl(headRow, "th", {
          cls: [
            `pf-base-th-${col.key.replace(/[^a-z0-9_-]/gi, "-")}`,
            col.numeric ? "is-num" : "",
            "is-sortable",
            isSorted ? "is-sorted" : "",
          ]
            .filter(Boolean)
            .join(" "),
          attr: {
            "data-pf-col": col.key,
            "aria-sort": isSorted
              ? activeSort!.dir === "DESC"
                ? "descending"
                : "ascending"
              : "none",
          },
        });
        const inner = mkEl(th, "span", { cls: "pf-base-th-inner" });
        mkEl(inner, "span", { cls: "pf-base-th-label", text: col.label });
        if (isSorted) {
          mkEl(inner, "span", {
            cls: "pf-base-sort-ind",
            text: activeSort!.dir === "DESC" ? "↓" : "↑",
          });
        }
        th.addEventListener("click", () => {
          this._toggleColumnSort(col);
        });
        const resizer = mkEl(th, "span", {
          cls: "pf-base-col-resizer",
          attr: { "aria-hidden": "true" },
        });
        this._bindColumnResize(resizer, th, colEls[idx], col);
      });
    }

    const slots: RenderSlot[] = [];
    let flatIdx = 0;
    for (const grp of groups) {
      if (grp.groupLabel !== null) {
        slots.push({
          kind: "group",
          label: grp.groupLabel,
          count: grp.items.length,
        });
      }
      const isCollapsed =
        grp.groupLabel !== null && this._collapsedGroups.has(grp.groupLabel);
      for (const item of grp.items) {
        if (!isCollapsed) {
          slots.push({ kind: "row", item, flatIndex: flatIdx });
        }
        flatIdx += 1;
      }
    }

    this._currentSlots = slots;
    this._renderedSlotCount = 0;
    this._renderedPaperCount = 0;
    const useVirtual =
      slots.length > 500 &&
      ((this._tableWrapEl?.clientHeight ?? 0) > 0 ||
        this.config?.get?.("virtual_scroll") === true);
    this._virtualActive = useVirtual;
    this._virtualRange = { start: -1, end: -1 };
    if (this._tbodyEl) {
      this._tbodyEl.textContent = "";
      if (useVirtual) {
        this._renderVirtualWindow(true);
      } else {
        this._appendNextChunk(INITIAL_CHUNK_SIZE);
      }
    }
    if (this._tfootEl) {
      this._renderSummaryFooter(
        this._tfootEl,
        columns,
        flatItems,
        showCheckboxes
      );
    }
  }

  render(): void {
    const root = this.containerEl;
    if (!root) return;
    this._ensureShell();
    const density = String(
      this.config?.get?.("row_density") ??
        (this.config?.get?.("compact_rows") === true
          ? "compact"
          : "comfortable")
    );
    root.classList.toggle("is-compact", density === "compact");
    root.classList.toggle("is-spacious", density === "spacious");

    const snapshot = this.plugin.getBaseSnapshotCache();
    const rawGroups = this._collectGroups(snapshot);
    const rawFlatItems = rawGroups.flatMap((g) => g.items);
    this._lastRawItems = rawFlatItems;
    const filters = this._getFilters();
    const matchedCount = rawFlatItems.filter((it) =>
      this._matchesFilters(it.row, filters)
    ).length;

    this._renderActivityStrip(rawFlatItems);

    if (this._filterSlotEl) {
      const showFilterBar = this.config?.get?.("show_filter_bar") !== false;
      if (
        showFilterBar &&
        (rawFlatItems.length > 0 || this._hasActiveFilters(filters))
      ) {
        this._filterSlotEl.style.display = "";
        this._renderFilterBar(
          this._filterSlotEl,
          rawFlatItems,
          matchedCount,
          filters
        );
      } else {
        this._filterSlotEl.style.display = "none";
      }
    }

    if (this._missingPdfSlotEl) {
      this._missingPdfSlotEl.textContent = "";
      if (
        snapshot &&
        Object.keys(snapshot.rows || {}).length > 0 &&
        !this._missingPdfHintDismissed &&
        rawFlatItems.length >= 3
      ) {
        const missingPdfCount = rawFlatItems.filter(
          (it) => !it.row.has_pdf
        ).length;
        if (
          missingPdfCount > 0 &&
          missingPdfCount / rawFlatItems.length >= 0.5
        ) {
          const hintBar = mkEl(this._missingPdfSlotEl, "div", {
            cls: "pf-base-missing-pdf-hint",
            attr: { "data-pf-testid": "base-missing-pdf-hint" },
          });
          mkEl(hintBar, "span", {
            text: t("base_missing_pdf_banner")
              .replace("{missing}", String(missingPdfCount))
              .replace("{total}", String(rawFlatItems.length)),
          });
          const closeHintBtn = mkEl(hintBar, "button", {
            cls: "pf-btn pf-btn-ghost",
            text: t("base_missing_pdf_dismiss"),
            attr: {
              type: "button",
              "data-pf-testid": "base-missing-pdf-dismiss",
            },
          });
          closeHintBtn.addEventListener("click", () => {
            this._missingPdfHintDismissed = true;
            this.render();
          });
        }
      }
    }

    this._renderBodyOnly();
  }
}
