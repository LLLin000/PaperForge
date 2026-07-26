import { scanVersions, restoreVersion } from "../services/version-history";
import { ItemView, WorkspaceLeaf, Notice, Modal } from "obsidian";
import * as fs from "fs";
import * as path from "path";
import { execFile } from "child_process";
import { VIEW_TYPE_OCR_WORKSPACE } from "../constants";
import { t } from "../i18n";
import { resolveVaultPaths } from "../services/memory-state";
import { resolveRuntimeCommand } from "../services/managed-runtime";

/* ── OcrPaper interface ── */

interface OcrPaper {
  key: string;
  title: string;
  status: string;
  pipelineVersion: string;
  lastRun: string;
  hasBackup: boolean;
  authors: string;
  year: string;
  pages: string;
  backupCount: number;
}

/* ── View ── */

export class OcrWorkspaceView extends ItemView {
  private papers: OcrPaper[] = [];
  private filter: "all" | "unprocessed" | "review" | "processed" = "all";
  private versionFilter: string | null = null;
  private selectedKey: string | null = null;
  private checkedKeys: Set<string> = new Set();
  private running: boolean = false;
  private progress = { current: 0, total: 0, paperKey: "" };
  private _searchQuery: string = "";
  private _searchTimer: ReturnType<typeof setTimeout> | undefined;

  constructor(
    leaf: WorkspaceLeaf,
    private plugin: any
  ) {
    super(leaf);
  }

  static async open(plugin: any): Promise<void> {
    const leaves = plugin.app.workspace.getLeavesOfType(
      VIEW_TYPE_OCR_WORKSPACE
    );
    if (leaves.length > 0) {
      plugin.app.workspace.revealLeaf(leaves[0]);
      return;
    }
    const leaf = plugin.app.workspace.getLeaf("tab");
    if (leaf) {
      await leaf.setViewState({ type: VIEW_TYPE_OCR_WORKSPACE, active: true });
      plugin.app.workspace.revealLeaf(leaf);
    }
  }

  getViewType(): string {
    return VIEW_TYPE_OCR_WORKSPACE;
  }
  getDisplayText(): string {
    return t("ocr_ws_title");
  }
  getIcon(): string {
    return "scan-text";
  }

  async onOpen(): Promise<void> {
    await this._loadPapers();
    this._render();
  }

  /* ── Data loading ── */

  private async _loadPapers(): Promise<void> {
    const vp = (this.app.vault.adapter as any).basePath as string;
    const paths = resolveVaultPaths(vp);
    const indexPath = path.join(paths.indexesDir, "formal-library.json");
    if (!fs.existsSync(indexPath)) {
      this.papers = [];
      return;
    }
    try {
      const index = JSON.parse(fs.readFileSync(indexPath, "utf-8"));
      const items: any[] = index?.items ?? [];
      this.papers = [];
      for (const item of items) {
        const key = item.zotero_key;
        if (!key) continue;
        const metaPath = path.join(paths.ocrDir, key, "meta.json");
        let meta: any = {};
        if (fs.existsSync(metaPath)) {
          try {
            meta = JSON.parse(fs.readFileSync(metaPath, "utf-8"));
          } catch {}
        }
        const backupsDir = path.join(paths.ocrDir, key, "backups");
        let backupCount = 0;
        if (fs.existsSync(backupsDir)) {
          backupCount = fs
            .readdirSync(backupsDir)
            .filter((f: string) => f.startsWith("fulltext.pre-rebuild")).length;
        }
        this.papers.push({
          key,
          title: item.title ?? key,
          status: meta.ocr_status ?? meta.ocrStatus ?? "pending",
          pipelineVersion: meta.ocr_pipeline_version ?? "",
          lastRun: meta.ocr_finished_at ?? meta.ocrFinishedAt ?? "",
          hasBackup: backupCount > 0,
          authors: item.authors?.join?.(", ") ?? "",
          year: item.year ?? "",
          pages: meta.page_count ? String(meta.page_count) : "",
          backupCount,
        });
      }
    } catch {
      this.papers = [];
    }
  }

  /* ── Render ── */
  /* ── Full render (structure) ── */

  private _render(): void {
    const container = this.containerEl.children[1] as HTMLElement;
    container.empty();
    container.addClass("pf-ocr-workspace");

    this._renderHeader(container);
    this._renderActivity(container);
    this._renderToolbar(container);
    this._renderTable(container);
    this._renderBatchBar(container);
    if (this.selectedKey) {
      this._renderDetail(container);
    }
  }

  /* ── Partial table refresh (preserves input focus) ── */
  private _refreshTable(): void {
    const container = this.containerEl.children[1] as HTMLElement;
    const filtered = this._filteredPapers();

    // Update count
    const countEl = container.querySelector(".pf-ocr-ws-toolbar-count");
    if (countEl) {
      countEl.innerHTML = t("ocr_ws_showing")
        .replace("{count}", String(filtered.length))
        .replace("{total}", String(this.papers.length));
    }

    // DOM-reuse: keep table and thead, only replace tbody
    const existingTable =
      container.querySelector<HTMLTableElement>(".pf-ocr-ws-table");
    if (existingTable) {
      const oldTbody = existingTable.querySelector("tbody");
      if (oldTbody) oldTbody.remove();
      this._buildTableRows(existingTable, filtered);
    } else {
      // First render — build full table
      const vp = container.createDiv({ cls: "pf-ocr-ws-viewport" });
      this._buildTableBody(vp, filtered);
    }

    // Replace batch bar
    const existingBatchBar = container.querySelector(".pf-ocr-ws-batchbar");
    if (existingBatchBar) existingBatchBar.remove();
    this._renderBatchBar(container);

    // Toggle detail
    const existingDetail = container.querySelector(".pf-ocr-ws-detail");
    if (existingDetail) existingDetail.remove();
    if (this.selectedKey) {
      this._renderDetail(container);
    }
  }

  private _renderHeader(container: HTMLElement): void {
    const header = container.createDiv({ cls: "pf-ocr-ws-header" });
    header.createEl("h1", { text: t("ocr_ws_title") });
    header.createEl("p", { cls: "pf-ocr-ws-lede", text: t("ocr_ws_lede") });
  }
  private _renderActivity(container: HTMLElement): void {
    if (!this.running) return;
    const act = container.createDiv({
      cls: "pf-ocr-ws-activity pf-active",
      attr: { "aria-live": "polite" },
    });
    const head = act.createDiv({ cls: "pf-ocr-ws-activity-head" });
    const title = head.createDiv({ cls: "pf-ocr-ws-activity-title" });
    title.setText(t("ocr_ws_processing"));
    const key = this.progress.paperKey;
    if (key) {
      const paper = this.papers.find((p) => p.key === key);
      if (paper) {
        const titleSpan = title.createEl("span");
        titleSpan.setText(paper.title ?? key);
      }
    }
    const stopBtn = head.createEl("button", {
      cls: "pf-btn pf-btn-ghost",
      text: t("ocr_ws_stop"),
    });
    stopBtn.addEventListener("click", () => this._stopBuild());

    const track = act.createDiv({ cls: "pf-ocr-ws-progress-track" });
    const fill = track.createDiv({ cls: "pf-ocr-ws-progress-fill" });
    const pct =
      this.progress.total > 0
        ? Math.round((this.progress.current / this.progress.total) * 100)
        : 0;
    fill.style.transform = `scaleX(${pct / 100})`;

    const meta = act.createDiv({ cls: "pf-ocr-ws-progress-meta" });
    meta.createEl("span", {
      text: `${this.progress.current} / ${this.progress.total} papers`,
    });
    meta.createEl("span", { text: `${pct}%` });
  }

  private _renderToolbar(container: HTMLElement): void {
    const filtered = this._filteredPapers();
    const versions = [
      ...new Set(this.papers.map((p) => p.pipelineVersion).filter(Boolean)),
    ]
      .sort()
      .reverse();

    const tb = container.createDiv({ cls: "pf-ocr-ws-toolbar" });
    const count = tb.createDiv({ cls: "pf-ocr-ws-toolbar-count" });
    count.innerHTML = t("ocr_ws_showing")
      .replace("{count}", String(filtered.length))
      .replace("{total}", String(this.papers.length));

    // Search input
    const searchField = tb.createDiv({ cls: "pf-ocr-ws-search" });
    const searchInput = searchField.createEl("input", {
      cls: "pf-ocr-ws-search-input",
      attr: {
        type: "text",
        placeholder:
          t("ocr_ws_search_placeholder") ||
          "Search papers by title, author, year...",
      },
    }) as HTMLInputElement;
    searchInput.value = this._searchQuery;
    searchInput.addEventListener("input", () => {
      this._searchQuery = searchInput.value;
      this.selectedKey = null;
      this.checkedKeys.clear();
      clearTimeout(this._searchTimer);
      this._searchTimer = setTimeout(() => this._refreshTable(), 100);
    });
    searchInput.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        searchInput.value = "";
        this._searchQuery = "";
        this.selectedKey = null;
        this.checkedKeys.clear();
        clearTimeout(this._searchTimer);
        this._refreshTable();
        searchInput.blur();
      }
    });
    const field = tb.createDiv({ cls: "pf-ocr-ws-field" });
    field.createEl("label", { text: t("ocr_ws_filter_status") });
    const select = field.createEl("select");
    for (const [val, label] of [
      ["all", t("ocr_ws_filter_all")],
      ["unprocessed", t("ocr_ws_filter_unprocessed")],
      ["review", t("ocr_ws_filter_review")],
      ["processed", t("ocr_ws_filter_processed")],
    ]) {
      const opt = select.createEl("option", {
        text: String(label),
        attr: { value: String(val) },
      });
      if (val === this.filter) opt.selected = true;
    }
    select.addEventListener("change", () => {
      this.filter = select.value as any;
      this.selectedKey = null;
      this.checkedKeys.clear();
      this._refreshTable();
    });

    if (versions.length > 0) {
      const vf = tb.createDiv({ cls: "pf-ocr-ws-version-field" });
      for (const v of versions) {
        const chip = vf.createEl("button", {
          cls: `pf-ocr-ws-chip${this.versionFilter === v ? " pf-active" : ""}`,
          text: `v${v}`,
        });
        chip.addEventListener("click", () => {
          this.versionFilter = this.versionFilter === v ? null : v;
          this._refreshTable();
        });
      }
    }
  }

  private _filteredPapers(): OcrPaper[] {
    let list = this.papers;
    if (this.filter === "unprocessed")
      list = list.filter((p) => p.status === "pending" || p.status === "nopdf");
    else if (this.filter === "review")
      list = list.filter(
        (p) => p.status === "failed" || p.status === "processing"
      );
    else if (this.filter === "processed")
      list = list.filter((p) => p.status === "done");
    if (this.versionFilter)
      list = list.filter((p) => p.pipelineVersion === this.versionFilter);
    if (this._searchQuery.trim()) {
      const q = this._searchQuery.trim().toLowerCase();
      list = list.filter(
        (p) =>
          p.title.toLowerCase().includes(q) ||
          p.authors.toLowerCase().includes(q) ||
          p.year.toLowerCase().includes(q) ||
          p.key.toLowerCase().includes(q)
      );
    }
    return list;
  }

  private _renderTable(container: HTMLElement): void {
    const filtered = this._filteredPapers();
    const vp = container.createDiv({ cls: "pf-ocr-ws-viewport" });
    this._buildTableBody(vp, filtered);
  }

  private _buildTableBody(vp: HTMLElement, filtered: OcrPaper[]): void {
    if (filtered.length === 0) {
      vp.createDiv({
        cls: "pf-ocr-ws-empty pf-visible",
        text: t("ocr_ws_no_papers"),
      });
      return;
    }
    const table = vp.createEl("table", { cls: "pf-ocr-ws-table" });
    this._buildTableHead(table);
    this._buildTableRows(table, filtered);
  }

  private _buildTableHead(table: HTMLTableElement): void {
    const thead = table.createEl("thead");
    const hr = thead.createEl("tr");
    hr.createEl("th", { cls: "pf-ocr-ws-col-check" }).createEl(
      "input",
      { attr: { type: "checkbox" } },
      (cb: HTMLInputElement) => {
        cb.addEventListener("change", () => {
          const current = this._filteredPapers();
          if (cb.checked) {
            current.forEach((p) => this.checkedKeys.add(p.key));
          } else {
            this.checkedKeys.clear();
          }
          this._refreshTable();
        });
      }
    );
    hr.createEl("th", {
      cls: "pf-ocr-ws-col-paper",
      text: t("ocr_ws_col_title"),
    });
    hr.createEl("th", {
      cls: "pf-ocr-ws-col-status",
      text: t("ocr_ws_col_status"),
    });
    hr.createEl("th", {
      cls: "pf-ocr-ws-col-version",
      text: t("ocr_ws_col_version"),
    });
    hr.createEl("th", {
      cls: "pf-ocr-ws-col-date",
      text: t("ocr_ws_col_lastrun"),
    });
    hr.createEl("th", { cls: "pf-ocr-ws-col-action" });
  }

  private _buildTableRows(table: HTMLTableElement, filtered: OcrPaper[]): void {
    const tbody = table.createEl("tbody");
    for (const paper of filtered) {
      const versionBehind = Boolean(
        this.papers.find(
          (p) =>
            p.pipelineVersion &&
            paper.pipelineVersion &&
            p.pipelineVersion > paper.pipelineVersion
        )
      );
      const tr = tbody.createEl("tr", {
        cls: versionBehind ? "pf-update" : "",
      });
      tr.addEventListener("click", (e) => {
        if ((e.target as HTMLElement).tagName === "INPUT") return;
        this.selectedKey = paper.key === this.selectedKey ? null : paper.key;
        this._refreshTable();
      });

      const tdCheck = tr.createEl("td", { cls: "pf-ocr-ws-col-check" });
      tdCheck.createEl(
        "input",
        { attr: { type: "checkbox" } },
        (cb: HTMLInputElement) => {
          cb.checked = this.checkedKeys.has(paper.key);
          cb.addEventListener("change", () => {
            if (cb.checked) this.checkedKeys.add(paper.key);
            else this.checkedKeys.delete(paper.key);
            this._refreshTable();
          });
        }
      );

      const tdPaper = tr.createEl("td", { cls: "pf-ocr-ws-col-paper" });
      tdPaper.createDiv({ cls: "pf-ocr-ws-paper-title", text: paper.title });
      if (paper.authors || paper.year) {
        const meta = tdPaper.createDiv({ cls: "pf-ocr-ws-paper-meta" });
        if (paper.authors) {
          const first = paper.authors.split(",")[0].trim();
          const etAl = paper.authors.includes(",") ? " et al." : "";
          meta.createEl("span", {
            cls: "pf-ocr-ws-meta-author",
            text: first + etAl,
          });
        }
        if (paper.year) {
          meta.createEl("span", {
            cls: "pf-ocr-ws-meta-year",
            text: paper.year,
          });
        }
      }

      const tdStatus = tr.createEl("td", { cls: "pf-ocr-ws-col-status" });
      tdStatus.createEl("span", {
        cls: `pf-ocr-ws-status pf-${statusClass(paper.status)}`,
        text: statusLabel(paper.status),
      });

      const tdVer = tr.createEl("td", { cls: "pf-ocr-ws-col-version" });
      tdVer.createEl("span", {
        cls: "pf-ocr-ws-version",
        text: paper.pipelineVersion || "\u2014",
      });

      const tdDate = tr.createEl("td", { cls: "pf-ocr-ws-col-date" });
      tdDate.setText(paper.lastRun ? paper.lastRun.slice(0, 10) : "\u2014");

      const tdAction = tr.createEl("td", { cls: "pf-ocr-ws-col-action" });
      const previewBtn = tdAction.createEl("button", {
        cls: "pf-btn pf-btn-secondary",
        text: t("ocr_ws_btn_preview"),
      });
      previewBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        this._openFulltext(paper.key);
      });
    }
  }

  private _renderBatchBar(container: HTMLElement): void {
    const selected = this.papers.filter((p) => this.checkedKeys.has(p.key));
    const bar = container.createDiv({ cls: "pf-ocr-ws-batchbar" });

    const sel = bar.createDiv({ cls: "pf-ocr-ws-selection" });
    if (selected.length === 0) {
      sel.createEl("strong", { text: t("ocr_ws_none_selected") });
      sel.createEl("span", { text: t("ocr_ws_select_hint") });
    } else {
      sel.createEl("strong", {
        text: t("ocr_ws_selected").replace("{count}", String(selected.length)),
      });
    }

    const actions = bar.createDiv({ cls: "pf-ocr-ws-batch-actions" });
    const rebuildBtn = actions.createEl("button", {
      cls: "pf-btn pf-btn-warning",
      text: t("ocr_ws_btn_rebuild_selected"),
    });
    rebuildBtn.title = t("ocr_ws_tooltip_rebuild");
    rebuildBtn.disabled = selected.length === 0;
    rebuildBtn.addEventListener("click", () =>
      this._runRebuild(selected.map((p) => p.key))
    );
  }

  private _renderDetail(container: HTMLElement): void {
    const paper = this.papers.find((p) => p.key === this.selectedKey);
    if (!paper) return;

    const detail = container.createDiv({ cls: "pf-ocr-ws-detail pf-open" });
    const card = detail.createDiv({ cls: "pf-ocr-ws-detail-card" });

    const head = card.createDiv({ cls: "pf-ocr-ws-detail-head" });
    const left = head.createDiv({});
    left.createEl("h2", { text: paper.title });
    left.createEl("span", {
      cls: `pf-ocr-ws-status pf-${statusClass(paper.status)}`,
      text: statusLabel(paper.status),
    });

    const closeBtn = head.createEl("button", {
      cls: "pf-btn pf-btn-ghost",
      text: t("ocr_ws_close"),
    });
    closeBtn.addEventListener("click", () => {
      this.selectedKey = null;
      this._refreshTable();
    });

    // Fact grid
    const grid = card.createDiv({ cls: "pf-ocr-ws-detail-grid" });
    this._addFact(
      grid,
      t("ocr_ws_fact_version"),
      paper.pipelineVersion || "\u2014"
    );
    this._addFact(
      grid,
      t("ocr_ws_fact_last_run"),
      paper.lastRun ? paper.lastRun.slice(0, 10) : "\u2014"
    );
    this._addFact(grid, t("ocr_ws_fact_authors"), paper.authors || "\u2014");
    this._addFact(grid, t("ocr_ws_fact_year"), paper.year || "\u2014");
    this._addFact(grid, t("ocr_ws_fact_pages"), paper.pages || "\u2014");
    this._addFact(
      grid,
      t("ocr_ws_fact_backups"),
      paper.backupCount > 0 ? String(paper.backupCount) : "\u2014"
    );

    // Action buttons
    const actions = card.createDiv({ cls: "pf-ocr-ws-detail-actions" });
    const fulltextBtn = actions.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: t("ocr_ws_detail_view_fulltext"),
    });
    fulltextBtn.addEventListener("click", () => this._openFulltext(paper.key));

    // Restore backup — uses version-history service
    const restoreBtn = actions.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: t("ocr_ws_detail_restore_backup"),
    });
    restoreBtn.disabled = !paper.hasBackup;
    restoreBtn.addEventListener("click", () => {
      const self = this;
      const vp = (self.app.vault.adapter as any).basePath as string;
      const paths = resolveVaultPaths(vp);
      // Try version manifest first
      const versions = scanVersions(vp, paper.key);
      if (versions && versions.versions.length > 0) {
        const modal = new VersionRestoreModal(
          self.app, vp, paper.key,
          versions.versions.map(v => ({label:v.label,created_at:v.created_at,source:v.source,renderer_version:v.renderer_version,fulltext_size:v.fulltext_size})),
          versions.currentLabel,
          () => { self._loadPapers().then(() => self._render()); }
        );
        modal.open();
        return;
      }
      // Fallback: scan backups/ directory for pre-rebuild files
      const backupsDir = path.join(paths.ocrDir, paper.key, "backups");
      if (!fs.existsSync(backupsDir)) {
        new Notice("No backup versions available");
        return;
      }
      const backupFiles = fs.readdirSync(backupsDir)
        .filter(f => f.startsWith("fulltext.pre-rebuild"))
        .sort();
      if (backupFiles.length === 0) {
        new Notice("No backup versions available");
        return;
      }
      const backupEntries = backupFiles.map(f => {
        const ts = f.replace("fulltext.pre-rebuild.", "").replace(/\.md$/, "");
        const iso = ts.length >= 16
          ? ts.slice(0,4) + "-" + ts.slice(4,6) + "-" + ts.slice(6,8) + "T" + ts.slice(9,11) + ":" + ts.slice(11,13) + ":" + ts.slice(13,15) + "Z"
          : ts;
        let size = 0;
        try { size = fs.statSync(path.join(backupsDir, f)).size; } catch {}
        return { label: "backup-" + ts, created_at: iso, source: "pre-rebuild", fulltext_size: size };
      });
      const modal = new VersionRestoreModal(
        self.app, vp, paper.key,
        backupEntries, "",
        () => { self._loadPapers().then(() => self._render()); }
      );
      modal.open();
    });

    // Re-extract — runs paperforge ocr redo <key>
  }

  private _addFact(grid: HTMLElement, label: string, value: string): void {
    const fact = grid.createDiv({ cls: "pf-ocr-ws-fact" });
    fact.createEl("dt", { text: label });
    fact.createEl("dd", { text: value });
  }

  /* ── Actions ── */

  private _resolvePython(): { path: string; args: string[] } | null {
    // 1. Use custom python_path from plugin settings if set
    const plugin = ((this.app as any).plugins.plugins as any)["paperforge"];
    const customPath = plugin?.settings?.python_path?.trim();
    if (customPath && require("fs").existsSync(customPath)) {
      return { path: customPath, args: [] };
    }
    // 2. Fall back to managed runtime
    if (!plugin || typeof plugin.getManagedRuntime !== "function") return null;
    const mr = plugin.getManagedRuntime();
    if (!mr) return null;
    const run = resolveRuntimeCommand(mr.current());
    if (!run) return null;
    return { path: run.command, args: [...run.args] };
  }


  private _runRebuild(keys: string[]): void {
    const pyCmd = this._resolvePython();
    if (!pyCmd) {
      new Notice("Runtime not ready");
      return;
    }
    const vp = (this.app.vault.adapter as any).basePath as string;
    this.running = true;
    this.progress = { current: 0, total: keys.length, paperKey: "" };
    this._render();
    execFile(
      pyCmd.path,
      [...pyCmd.args, "-m", "paperforge", "ocr", "rebuild", ...keys],
      { cwd: vp, timeout: 600000 },
      (err: any) => {
        this.running = false;
        if (err) new Notice("Rebuild failed: " + (err.message || err));
        else new Notice("Rebuild completed");
        this._loadPapers().then(() => this._render());
      }
    );
  }

  private _stopBuild(): void {
    this.running = false;
    this._render();
  }

  private _openFulltext(key: string): void {
    const vp = (this.app.vault.adapter as any).basePath as string;
    const paths = resolveVaultPaths(vp);
    const fulltextPath = path.join(
      vp,
      paths.systemDir,
      "PaperForge",
      "ocr",
      key,
      "fulltext.md"
    );
    if (!fs.existsSync(fulltextPath)) {
      new Notice("Fulltext not found");
      return;
    }
    const file = this.app.vault.getAbstractFileByPath(
      path.relative(vp, fulltextPath).replace(/\\/g, "/")
    );
    if (file) {
      (this.app.workspace as any).getLeaf().openFile(file);
    } else {
      new Notice("Fulltext not found in vault");
    }
  }
}

/* ── Helpers ── */

function statusClass(status: string): string {
  if (status === "done") return "pf-done";
  if (status === "done_degraded") return "pf-done-degraded";
  if (status === "done_incomplete") return "pf-done-incomplete";
  if (status === "failed" || status === "error" || status === "fatal_error")
    return "pf-failed";
  return "";
}
/* ── Version Restore Modal ── */


function statusLabel(status: string): string {
  if (status === "done") return t("ocr_ws_status_done") || "Processed";
  if (status === "done_degraded")
    return t("ocr_ws_status_degraded") || "Partial";
  if (status === "done_incomplete")
    return t("ocr_ws_status_incomplete") || "Incomplete";
  if (status === "failed" || status === "error" || status === "fatal_error")
    return t("ocr_ws_status_failed") || "Failed";
  if (status === "retryable_error") return t("ocr_ws_status_error") || "Error";
  if (status === "processing" || status === "running")
    return t("ocr_ws_status_processing") || "Processing";
  if (status === "queued") return t("ocr_ws_status_queued") || "Queued";
  if (status === "blocked") return t("ocr_ws_status_blocked") || "Blocked";
  if (status === "nopdf") return t("ocr_ws_status_nopdf") || "No PDF";
  return t("ocr_ws_status_pending") || "Pending";
}

/* ── Version Restore Modal ── */

interface VersionEntry {
  label: string;
  created_at: string;
  source: string;
  renderer_version?: string;
  fulltext_size: number;
}

function versionContentPath(ocrDir: string, key: string, label: string): string {
  if (label.startsWith("backup-")) {
    const ts = label.slice("backup-".length);
    return path.join(ocrDir, key, "backups", "fulltext.pre-rebuild." + ts + ".md");
  }
  return path.join(ocrDir, key, "versions", label, "fulltext.md");
}

function diffParagraphs(textA: string, textB: string): { type: "added" | "removed" | "unchanged"; text: string }[] {
  const split = (t: string) => t.split(/\n\n+/).filter(Boolean);
  const pa = split(textA);
  const pb = split(textB);
  const max = Math.max(pa.length, pb.length);
  const result: { type: "added" | "removed" | "unchanged"; text: string }[] = [];
  for (let i = 0; i < max; i++) {
    const a = i < pa.length ? pa[i] : "";
    const b = i < pb.length ? pb[i] : "";
    if (!a && b) result.push({ type: "added", text: b });
    else if (a && !b) result.push({ type: "removed", text: a });
    else if (a !== b) {
      result.push({ type: "removed", text: a });
      result.push({ type: "added", text: b });
    } else {
      result.push({ type: "unchanged", text: a });
    }
  }
  return result;
}

class VersionRestoreModal extends Modal {
  private versions: VersionEntry[];
  private currentLabel: string;
  private vaultPath: string;
  private paperKey: string;
  private ocrDir: string;
  private selectedIdx: number = 0;
  private onRestored: (() => void) | null;
  private contentCache: Map<string, string> = new Map();

  constructor(app: any, vaultPath: string, paperKey: string, versions: VersionEntry[], currentLabel: string, onRestored?: () => void) {
    super(app);
    this.vaultPath = vaultPath;
    this.paperKey = paperKey;
    this.ocrDir = path.join(vaultPath, "System", "PaperForge", "ocr");
    this.versions = versions;
    this.currentLabel = currentLabel;
    this.onRestored = onRestored ?? null;
  }

  private getContent(label: string): string {
    const cached = this.contentCache.get(label);
    if (cached !== undefined) return cached;
    try {
      const fp = versionContentPath(this.ocrDir, this.paperKey, label);
      if (fs.existsSync(fp)) {
        const text = fs.readFileSync(fp, "utf-8");
        this.contentCache.set(label, text);
        return text;
      }
    } catch {}
    this.contentCache.set(label, "");
    return "";
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.addClass("paperforge-modal");
    contentEl.empty();

    // Cache current render content
    const curPath = path.join(this.ocrDir, this.paperKey, "render", "fulltext.md");
    try { if (fs.existsSync(curPath)) this.contentCache.set("__current__", fs.readFileSync(curPath, "utf-8")); } catch {}

    // Wait, need to reference buttons created in the render functions
    // Use a simpler approach — render everything in onOpen
    this.renderAll();
  }

  private renderAll() {
    const { contentEl } = this;
    contentEl.empty();

    const layout = contentEl.createDiv({ cls: "pf-vr-layout" });
    const sidebar = layout.createDiv({ cls: "pf-vr-sidebar" });
    const preview = layout.createDiv({ cls: "pf-vr-preview" });

    // ── Sidebar ──
    sidebar.createEl("div", { cls: "pf-vr-sidebar-title", text: t("ocr_ws_restore_versions") || "Versions" });
    const timeline = sidebar.createDiv({ cls: "pf-vr-timeline" });
    this.versions.forEach((ver, i) => {
      const date = new Date(ver.created_at).toLocaleDateString();
      const entry = timeline.createDiv({
        cls: "pf-vr-entry" + (i === this.selectedIdx ? " pf-vr-entry--active" : "") + (ver.label === this.currentLabel ? " pf-vr-entry--current" : ""),
        attr: { "data-idx": String(i) },
      });
      entry.createEl("span", { cls: "pf-vr-entry-label", text: ver.label });
      entry.createEl("span", { cls: "pf-vr-entry-date", text: date });
      if (ver.label === this.currentLabel) entry.createEl("span", { cls: "pf-vr-entry-badge", text: t("ocr_ws_restore_current") || "current" });
      entry.addEventListener("click", () => { this.selectedIdx = i; this.renderAll(); });
    });

    // ── Preview ──
    const ver = this.versions[this.selectedIdx];
    const isCurrent = ver.label === this.currentLabel;

    const toolbar = preview.createDiv({ cls: "pf-vr-toolbar" });
    const info = toolbar.createDiv({ cls: "pf-vr-info" });
    const actionsDiv = toolbar.createDiv({ cls: "pf-vr-actions" });

    const date = new Date(ver.created_at).toLocaleString();
    const sizeStr = ver.fulltext_size > 1024 ? (ver.fulltext_size / 1024).toFixed(0) + "KB" : ver.fulltext_size + "B";
    info.innerHTML = "<strong>" + ver.label + "</strong>" + (isCurrent ? " <span class=\"pf-vr-current-tag\">" + (t("ocr_ws_restore_current") || "current") + "</span>" : "") + "<br><span class=\"pf-vr-info-meta\">" + date + " · " + ver.source + " · " + sizeStr + (ver.renderer_version ? " · renderer v" + ver.renderer_version : "") + "</span>";

    const contentArea = preview.createDiv({ cls: "pf-vr-content" });
    const diffArea = preview.createDiv({ cls: "pf-vr-diff" });
    diffArea.style.display = "none";

    contentArea.setText(this.getContent(ver.label));

    if (!isCurrent) {
      const compareBtn = actionsDiv.createEl("button", { cls: "btn-secondary pf-vr-btn", text: t("ocr_ws_restore_compare") || "Compare with current" });
      compareBtn.addEventListener("click", () => {
        const textA = this.getContent("__current__");
        const textB = this.getContent(ver.label);
        contentArea.style.display = "none";
        diffArea.style.display = "block";
        diffArea.empty();
        const hdr = diffArea.createEl("div", { cls: "pf-vr-diff-header" });
        hdr.setText((t("ocr_ws_restore_diff_title") || "Changes from current").replace("{v}", ver.label));
        const body = diffArea.createEl("div", { cls: "pf-vr-diff-body" });
        const diffs = diffParagraphs(textA, textB);
        for (const d of diffs) {
          const line = body.createEl("div", { cls: "pf-vr-diff-line pf-vr-diff-" + d.type });
          line.createEl("span", { cls: "pf-vr-diff-prefix", text: d.type === "added" ? "+ " : d.type === "removed" ? "\u2212 " : "  " });
          line.createEl("span", { cls: "pf-vr-diff-text", text: d.text.slice(0, 200) + (d.text.length > 200 ? "\u2026" : "") });
        }
        if (diffs.length === 0) body.createEl("div", { cls: "pf-vr-diff-empty", text: t("ocr_ws_restore_no_diff") || "No differences" });
        const backBtn = diffArea.createEl("button", { cls: "btn-secondary pf-vr-btn", text: t("ocr_ws_restore_back") || "Back" });
        backBtn.addEventListener("click", () => { contentArea.style.display = "block"; diffArea.style.display = "none"; diffArea.empty(); });
      });

      const restoreBtn = actionsDiv.createEl("button", { cls: "btn-primary pf-vr-btn", text: t("ocr_ws_restore_btn") || "Restore this version" });
      restoreBtn.addEventListener("click", () => this.doRestore(ver));
    }

    // Close
    const closeBtn = contentEl.createEl("button", { cls: "pf-btn pf-btn-ghost pf-vr-close", text: t("ocr_ws_close") || "Close" });
    closeBtn.addEventListener("click", () => this.close());
  }

  private doRestore(ver: VersionEntry) {
    if (ver.label === this.currentLabel) return;
    let ok = false;
    if (ver.label.startsWith("backup-")) {
      const source = versionContentPath(this.ocrDir, this.paperKey, ver.label);
      const targetDir = path.join(this.ocrDir, this.paperKey, "render");
      const target = path.join(targetDir, "fulltext.md");
      try {
        if (fs.existsSync(source)) {
          if (!fs.existsSync(targetDir)) fs.mkdirSync(targetDir, { recursive: true });
          fs.copyFileSync(source, target);
          ok = true;
        }
      } catch (e) { console.warn("[PaperForge] Restore backup failed:", e); }
    } else {
      ok = restoreVersion(this.vaultPath, this.paperKey, ver.label);
    }
    if (ok) {
      new Notice(t("ocr_ws_detail_restore_done").replace("{label}", ver.label));
      this.close();
      this.onRestored?.();
    } else {
      new Notice("Restore failed");
    }
  }

  onClose() {
    try { this.contentEl.empty(); } catch {}
    this.contentCache.clear();
  }
}
