import { ItemView, WorkspaceLeaf, Notice } from "obsidian";
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

  constructor(
    leaf: WorkspaceLeaf,
    private plugin: any
  ) {
    super(leaf);
  }

  static async open(plugin: any): Promise<void> {
    const { WorkspaceLeaf } = require("obsidian");
    const leaves = plugin.app.workspace.getLeavesOfType(
      VIEW_TYPE_OCR_WORKSPACE
    );
    if (leaves.length > 0) {
      plugin.app.workspace.revealLeaf(leaves[0]);
      return;
    }
    const leaf = plugin.app.workspace.getRightLeaf(false);
    if (leaf) {
      await leaf.setViewState({ type: VIEW_TYPE_OCR_WORKSPACE, active: true });
      plugin.app.workspace.revealLeaf(leaf);
    }
  }

  getViewType(): string {
    return VIEW_TYPE_OCR_WORKSPACE;
  }
  getDisplayText(): string {
    return "OCR Workspace";
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
    const indexPath = path.join(
      vp,
      paths.systemDir,
      "PaperForge",
      "indexes",
      "formal-library.json"
    );
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
        const metaPath = path.join(
          vp,
          paths.systemDir,
          "PaperForge",
          "ocr",
          key,
          "meta.json"
        );
        let meta: any = {};
        if (fs.existsSync(metaPath)) {
          try {
            meta = JSON.parse(fs.readFileSync(metaPath, "utf-8"));
          } catch {}
        }
        const backupsDir = path.join(
          vp,
          paths.systemDir,
          "PaperForge",
          "ocr",
          key,
          "backups"
        );
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

  private _renderHeader(container: HTMLElement): void {
    const header = container.createDiv({ cls: "pf-ocr-ws-header" });
    header.createEl("h1", { text: t("ocr_ws_title") });
    header.createEl("p", { cls: "pf-ocr-ws-lede", text: t("ocr_ws_lede") });
  }

  private _renderActivity(container: HTMLElement): void {
    const act = container.createDiv({
      cls: `pf-ocr-ws-activity${this.running ? " pf-active" : ""}`,
      attr: { "aria-live": "polite" },
    });
    const head = act.createDiv({ cls: "pf-ocr-ws-activity-head" });
    const title = head.createDiv({ cls: "pf-ocr-ws-activity-title" });
    title.setText(t("ocr_ws_processing"));
    const key = this.progress.paperKey;
    if (key) {
      const paper = this.papers.find((p) => p.key === key);
      title.createEl("span", { text: paper?.title ?? key });
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
      this._render();
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
          this._render();
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
    return list;
  }

  private _renderTable(container: HTMLElement): void {
    const filtered = this._filteredPapers();
    const vp = container.createDiv({ cls: "pf-ocr-ws-viewport" });

    if (filtered.length === 0) {
      vp.createDiv({
        cls: "pf-ocr-ws-empty pf-visible",
        text: t("ocr_ws_no_papers"),
      });
      return;
    }

    const table = vp.createEl("table", { cls: "pf-ocr-ws-table" });
    const thead = table.createEl("thead");
    const hr = thead.createEl("tr");
    hr.createEl("th", { cls: "pf-ocr-ws-col-check" }).createEl(
      "input",
      { attr: { type: "checkbox" } },
      (cb: HTMLInputElement) => {
        cb.addEventListener("change", () => {
          if (cb.checked) {
            filtered.forEach((p) => this.checkedKeys.add(p.key));
          } else {
            this.checkedKeys.clear();
          }
          this._render();
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
        this._render();
      });

      // Checkbox
      const tdCheck = tr.createEl("td", { cls: "pf-ocr-ws-col-check" });
      tdCheck.createEl(
        "input",
        { attr: { type: "checkbox" } },
        (cb: HTMLInputElement) => {
          cb.checked = this.checkedKeys.has(paper.key);
          cb.addEventListener("change", () => {
            if (cb.checked) this.checkedKeys.add(paper.key);
            else this.checkedKeys.delete(paper.key);
            this._render();
          });
        }
      );

      // Paper title
      const tdPaper = tr.createEl("td", { cls: "pf-ocr-ws-col-paper" });
      tdPaper.createDiv({ cls: "pf-ocr-ws-paper-title", text: paper.title });
      if (paper.authors || paper.year) {
        tdPaper.createDiv({
          cls: "pf-ocr-ws-paper-meta",
          text: [paper.authors, paper.year].filter(Boolean).join(", "),
        });
      }

      // Status badge
      const tdStatus = tr.createEl("td", { cls: "pf-ocr-ws-col-status" });
      tdStatus.createEl("span", {
        cls: `pf-ocr-ws-status pf-${statusClass(paper.status)}`,
        text: statusLabel(paper.status),
      });

      // Version
      const tdVer = tr.createEl("td", { cls: "pf-ocr-ws-col-version" });
      tdVer.createEl("span", {
        cls: "pf-ocr-ws-version",
        text: paper.pipelineVersion || "\u2014",
      });

      // Date
      const tdDate = tr.createEl("td", { cls: "pf-ocr-ws-col-date" });
      tdDate.setText(paper.lastRun ? paper.lastRun.slice(0, 10) : "\u2014");

      // Preview
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
    const processBtn = actions.createEl("button", {
      cls: "pf-btn pf-btn-primary",
      text: t("ocr_ws_btn_process_selected"),
    });
    processBtn.disabled = selected.length === 0;
    processBtn.addEventListener("click", () =>
      this._runOcr(selected.map((p) => p.key))
    );

    const updateBtn = actions.createEl("button", {
      cls: "pf-btn pf-btn-warning",
      text: t("ocr_ws_btn_update_selected"),
    });
    updateBtn.disabled = selected.length === 0;
    updateBtn.addEventListener("click", () =>
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
      this._render();
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

    // Re-extract disabled warning
    const warning = card.createDiv({ cls: "pf-impact-box" });
    warning.createEl("strong", { text: t("ocr_ws_re_extract_disabled_title") });
    warning.createEl("p", { text: t("ocr_ws_re_extract_disabled_body") });

    // Action buttons
    const actions = card.createDiv({ cls: "pf-ocr-ws-detail-actions" });
    const fulltextBtn = actions.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: t("ocr_ws_detail_view_fulltext"),
    });
    fulltextBtn.addEventListener("click", () => this._openFulltext(paper.key));

    const restoreBtn = actions.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: t("ocr_ws_detail_restore_backup"),
    });
    restoreBtn.disabled = !paper.hasBackup;
    restoreBtn.addEventListener("click", () => {
      new Notice("Version history panel not yet integrated");
    });

    const reExtractBtn = actions.createEl("button", {
      cls: "pf-btn pf-btn-warning",
      text: t("ocr_ws_detail_re_extract"),
    });
    reExtractBtn.disabled = true;

    // Disclosure: "What happens when I re-extract?"
    const details = card.createEl("details");
    details.createEl("summary", { text: t("ocr_ws_what_happens") });
    details.createEl("p", { text: t("ocr_ws_disclosure_text") });
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

  private _runOcr(keys: string[]): void {
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
      [...pyCmd.args, "-m", "paperforge", "ocr", "run", ...keys],
      { cwd: vp, timeout: 600000 },
      (err: any) => {
        this.running = false;
        if (err) new Notice("OCR failed: " + (err.message || err));
        else new Notice("OCR completed");
        this._loadPapers().then(() => this._render());
      }
    );
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
  if (status === "retryable_error") return "pf-error";
  if (status === "processing" || status === "running") return "pf-running";
  if (status === "queued") return "pf-queued";
  if (status === "blocked") return "pf-blocked";
  return "pf-pending";
}

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
