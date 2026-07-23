import { ItemView, WorkspaceLeaf, Notice } from "obsidian";
import * as fs from "fs";
import * as path from "path";
import { execFile } from "child_process";
import { VIEW_TYPE_OCR_WORKSPACE } from "../constants";
import { t } from "../i18n";
import { resolveVaultPaths } from "../services/memory-state";
import { resolveRuntimeCommand } from "../services/managed-runtime";
// ── OcrPaper interface ──

interface OcrPaper {
  key: string;
  title: string;
  status: string;
  pipelineVersion: string;
  lastRun: string;
  hasBackup: boolean;
}

// ── Status helpers ──

function statusLabel(s: string): string {
  const map: Record<string, string> = {
    done: "Processed",
    pending: "Pending",
    failed: "Failed",
    nopdf: "No PDF",
    processing: "Processing\u2026",
  };
  return map[s] ?? s;
}

function statusClass(s: string): string {
  return (
    "pf-ocr-ws-badge--" +
    (s === "done" ? "ok" : s === "failed" ? "err" : "warn")
  );
}

// ── View ──

export class OcrWorkspaceView extends ItemView {
  private papers: OcrPaper[] = [];
  private filter: "all" | "unprocessed" | "review" | "processed" = "all";
  private selectedKey: string | null = null;

  constructor(
    leaf: WorkspaceLeaf,
    private plugin: any
  ) {
    super(leaf);
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

  async onClose(): Promise<void> {
    // cleanup
  }

  /* ── Data loading ── */

  private async _loadPapers(): Promise<void> {
    const vp = (this.app.vault.adapter as any).basePath as string;
    const paths = resolveVaultPaths(vp);

    // 1. Read formal-library.json
    const indexPath = path.join(paths.indexesDir, "formal-library.json");
    let indexItems: any[] = [];
    try {
      const raw = fs.readFileSync(indexPath, "utf-8");
      const index = JSON.parse(raw);
      indexItems = index.items || [];
    } catch {
      indexItems = [];
    }

    // 2. Build paper list
    const papers: OcrPaper[] = [];
    for (const item of indexItems) {
      const key = item.key;
      if (!key) continue;
      const title = item.title || key;

      // Read meta.json
      const metaPath = path.join(paths.ocrDir, key, "meta.json");
      let meta: any = null;
      try {
        meta = JSON.parse(fs.readFileSync(metaPath, "utf-8"));
      } catch {
        // no meta.json = no OCR data for this paper
        continue;
      }

      // Determine status from meta
      let status = "pending";
      const ocrStatus = meta.ocr_status;
      if (ocrStatus === "done" || ocrStatus === "completed") {
        status = "done";
      } else if (ocrStatus === "failed" || ocrStatus === "error") {
        status = "failed";
      } else if (
        ocrStatus === "processing" ||
        (meta.ocr_started_at && !meta.ocr_finished_at)
      ) {
        status = "processing";
      } else if (meta.ocr_no_pdf) {
        status = "nopdf";
      } else if (meta.ocr_finished_at) {
        status = "done";
      }

      papers.push({
        key,
        title,
        status,
        pipelineVersion: meta.ocr_pipeline_version || "",
        lastRun: meta.ocr_finished_at || meta.ocr_started_at || "",
        hasBackup:
          (meta.backups && meta.backups.length > 0) ||
          (meta.backup_count && meta.backup_count > 0),
      });
    }

    this.papers = papers;
  }

  /* ── Render ── */

  private _render(): void {
    const container = this.containerEl.children[1] as HTMLElement;
    container.empty();
    container.addClass("pf-ocr-workspace");

    this._renderSidebar(container);
    this._renderTable(container);
    this._renderBottomBar(container);

    if (this.selectedKey) {
      this._renderDetail(container);
    }
  }

  /* ── Sidebar filters ── */

  private _renderSidebar(container: HTMLElement): void {
    type FilterId = "all" | "unprocessed" | "review" | "processed";
    const filters: Array<{ id: FilterId; label: string }> = [
      { id: "all", label: t("ocr_ws_filter_all") },
      { id: "unprocessed", label: t("ocr_ws_filter_unprocessed") },
      { id: "review", label: t("ocr_ws_filter_review") },
      { id: "processed", label: t("ocr_ws_filter_processed") },
    ];

    const bar = container.createDiv({ cls: "pf-ocr-ws-filters" });
    for (const f of filters) {
      const btn = bar.createEl("button", {
        cls: `pf-ocr-ws-filter${f.id === this.filter ? " pf-active" : ""}`,
        text: f.label,
      });
      btn.addEventListener("click", () => {
        this.filter = f.id;
        this.selectedKey = null;
        this._render();
      });
    }
  }

  /* ── Paper table ── */

  private _filteredPapers(): OcrPaper[] {
    const f = this.filter;
    if (f === "all") return this.papers;
    if (f === "unprocessed")
      return this.papers.filter(
        (p) => p.status === "pending" || p.status === "nopdf"
      );
    if (f === "review")
      return this.papers.filter(
        (p) => p.status === "failed" || p.status === "processing"
      );
    if (f === "processed")
      return this.papers.filter((p) => p.status === "done");
    return this.papers;
  }

  private _renderTable(container: HTMLElement): void {
    const filtered = this._filteredPapers();

    if (filtered.length === 0) {
      container.createDiv({
        cls: "pf-ocr-ws-empty",
        text: t("ocr_ws_no_papers"),
      });
      return;
    }

    const table = container.createDiv({ cls: "pf-ocr-ws-table" });

    for (const paper of filtered) {
      const row = table.createDiv({
        cls: `pf-ocr-ws-row${this.selectedKey === paper.key ? " pf-selected" : ""}`,
      });
      row.addEventListener("click", () => {
        this.selectedKey = paper.key === this.selectedKey ? null : paper.key;
        this._render();
      });

      // Title column
      const titleCol = row.createDiv({ cls: "pf-ocr-ws-col-title" });
      titleCol.setText(paper.title);

      // Status badge column
      const statusCol = row.createDiv({ cls: "pf-ocr-ws-col-status" });
      const badge = statusCol.createEl("span", {
        cls: `pf-ocr-ws-badge ${statusClass(paper.status)}`,
        text: statusLabel(paper.status),
      });

      // Version column
      const verCol = row.createDiv({ cls: "pf-ocr-ws-col-version" });
      verCol.setText(paper.pipelineVersion || "\u2014");

      // Last run column
      const lrCol = row.createDiv({ cls: "pf-ocr-ws-col-lastrun" });
      lrCol.setText(paper.lastRun ? paper.lastRun.slice(0, 10) : "\u2014");

      // Preview button column
      const previewCol = row.createDiv({ cls: "pf-ocr-ws-col-preview" });
      const previewBtn = previewCol.createEl("button", {
        cls: "pf-action-btn",
        text: t("ocr_ws_btn_preview"),
      });
      // Stop event from propagating to row click
      previewBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        this._openFulltext(paper.key);
      });
    }
  }

  /* ── Bottom bar ── */

  private _renderBottomBar(container: HTMLElement): void {
    const unprocessedCount = this.papers.filter(
      (p) => p.status === "pending" || p.status === "nopdf"
    ).length;

    const bar = container.createDiv({ cls: "pf-ocr-ws-bottombar" });
    const btn = bar.createEl("button", {
      cls: "pf-action-btn",
      text: t("ocr_ws_btn_process_all").replace(
        "{count}",
        String(unprocessedCount)
      ),
    });
    btn.addEventListener("click", () => {
      const vp = (this.app.vault.adapter as any).basePath as string;
      new Notice("Starting OCR for all unprocessed papers\u2026");
      const pyCmd = this._resolvePython();
      if (!pyCmd) {
        new Notice("Runtime not ready");
        return;
      }
      const env = { ...process.env };
      execFile(
        pyCmd.path,
        [...pyCmd.args, "-m", "paperforge", "ocr", "rebuild", "--all"],
        { cwd: vp, timeout: 600000, env },
        (err: any) => {
          if (err) {
            new Notice(
              "OCR rebuild failed: " + (err.message || "").slice(0, 120)
            );
          } else {
            new Notice("OCR rebuild completed");
            this._loadPapers().then(() => this._render());
          }
        }
      );
    });
  }

  private _resolvePython(): { path: string; args: string[] } | null {
    const plugin = ((this.app as any).plugins.plugins as any)["paperforge"];
    if (!plugin || typeof plugin.getManagedRuntime !== "function") return null;
    const mr = plugin.getManagedRuntime();
    if (!mr) return null;
    const run = resolveRuntimeCommand(mr.current());
    if (!run) return null;
    return { path: run.command, args: [...run.args] };
  }

  /* ── Per-paper detail panel ── */

  private _renderDetail(container: HTMLElement): void {
    const paper = this.papers.find((p) => p.key === this.selectedKey);
    if (!paper) return;

    const panel = container.createDiv({ cls: "pf-ocr-ws-detail" });

    // Title + status
    const heading = panel.createDiv({ cls: "pf-ocr-ws-detail-heading" });
    heading.createEl("h3", { text: paper.title });
    heading.createEl("span", {
      cls: `pf-ocr-ws-badge ${statusClass(paper.status)}`,
      text: statusLabel(paper.status),
    });

    // Status info box
    const infoBox = panel.createDiv({ cls: "pf-ocr-ws-infobox" });
    infoBox.createEl("p", {
      text: this._statusDescription(paper.status),
    });

    // Config rows
    const facts = panel.createDiv({ cls: "pf-module-facts" });

    const verFact = facts.createDiv({ cls: "pf-module-fact" });
    verFact.createEl("span", { text: t("ocr_ws_col_version") });
    verFact.createEl("span", { text: paper.pipelineVersion || "\u2014" });

    const lrFact = facts.createDiv({ cls: "pf-module-fact" });
    lrFact.createEl("span", { text: t("ocr_ws_col_lastrun") });
    lrFact.createEl("span", { text: paper.lastRun || "\u2014" });

    const bkFact = facts.createDiv({ cls: "pf-module-fact" });
    bkFact.createEl("span", { text: "Backups" });
    bkFact.createEl("span", { text: paper.hasBackup ? "Available" : "None" });

    // Action buttons row
    const actions = panel.createDiv({ cls: "pf-ocr-ws-actions" });

    // View Fulltext
    const viewBtn = actions.createEl("button", {
      cls: "pf-action-btn",
      text: t("ocr_ws_detail_view_fulltext"),
    });
    viewBtn.addEventListener("click", () => this._openFulltext(paper.key));

    // Restore Backup
    const restoreBtn = actions.createEl("button", {
      cls: "pf-action-btn",
      text: t("ocr_ws_detail_restore_backup"),
    });
    if (!paper.hasBackup) restoreBtn.setAttr("disabled", "true");
    restoreBtn.addEventListener("click", () => {
      if (paper.hasBackup) this._openBackupHistory(paper.key);
    });

    // Re-extract This Paper — DISABLED with warning
    const reBtn = actions.createEl("button", {
      cls: "pf-action-btn",
      text: t("ocr_ws_detail_re_extract"),
    });
    reBtn.setAttr("disabled", "true");
    reBtn.classList.add("pf-action-btn--disabled");

    // Warning box for disabled re-extract
    const warnBox = actions.createDiv({ cls: "pf-ocr-ws-warning" });
    warnBox.createEl("strong", { text: t("ocr_ws_re_extract_disabled_title") });
    warnBox.createEl("p", { text: t("ocr_ws_re_extract_disabled_body") });

    // Expandable disclosure
    const disclosureId = "pf-ocr-ws-re-extract-disclosure";
    const disclosureContainer = panel.createDiv({ cls: "pf-disclosure" });
    const disclosureHeader = disclosureContainer.createEl("button", {
      cls: "pf-disclosure-header",
      attr: { "aria-expanded": "false", type: "button" },
    });
    disclosureHeader.createEl("span", {
      cls: "pf-disclosure-icon",
      text: "\u25b6",
    });
    disclosureHeader.createEl("span", {
      cls: "pf-disclosure-title",
      text: t("ocr_ws_what_happens"),
    });
    const disclosureBody = disclosureContainer.createDiv({
      cls: "pf-disclosure-body",
    });
    disclosureBody.createEl("p", { text: t("ocr_ws_disclosure_text") });
    disclosureHeader.addEventListener("click", () => {
      const isOpen = disclosureHeader.getAttribute("aria-expanded") === "true";
      disclosureHeader.setAttribute("aria-expanded", String(!isOpen));
      disclosureBody.classList.toggle("pf-disclosure-body--open", !isOpen);
      const icon = disclosureHeader.querySelector(".pf-disclosure-icon");
      if (icon) icon.textContent = isOpen ? "\u25b6" : "\u25bc";
    });
  }

  /* ── Helpers ── */

  private _statusDescription(status: string): string {
    const map: Record<string, string> = {
      done: "OCR extraction completed successfully.",
      pending: "Paper is queued for OCR extraction.",
      failed: "OCR extraction encountered an error.",
      nopdf: "No PDF attachment found for this paper.",
      processing: "OCR extraction is currently running.",
    };
    return map[status] ?? "";
  }

  private _openFulltext(key: string): void {
    const vp = (this.app.vault.adapter as any).basePath as string;
    const paths = resolveVaultPaths(vp);
    const fulltextPath = path.join(paths.ocrDir, key, "fulltext.md");
    if (!fs.existsSync(fulltextPath)) {
      new Notice("Fulltext not found for this paper");
      return;
    }
    // Open in Obsidian
    const file = this.app.vault.getAbstractFileByPath(
      path.relative(vp, fulltextPath).replace(/\\/g, "/")
    );
    if (file) {
      (this.app as any).workspace.getLeaf().openFile(file);
    } else {
      new Notice("Could not open fulltext file");
    }
  }

  private _openBackupHistory(key: string): void {
    const vp = (this.app.vault.adapter as any).basePath as string;
    const paths = resolveVaultPaths(vp);
    const backupDir = path.join(paths.ocrDir, key, "backups");
    if (!fs.existsSync(backupDir)) {
      new Notice("No backups found for this paper");
      return;
    }
    new Notice("Backup directory: " + backupDir);
  }
}
