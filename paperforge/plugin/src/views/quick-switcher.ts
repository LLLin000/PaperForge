import * as obsidian from "obsidian";
import { t } from "../i18n";
import type {
  BasePaperRowDto,
  BaseTableSnapshotDto,
} from "../client/paperforge-client";
import type { CommandRegistry, CommandSpec } from "../uikit/commands";
import { renderKeycap } from "../uikit/primitives";
import { setPfIcon } from "./icons";

export interface PaperForgeQuickSwitcherHost {
  getBaseSnapshotCache(): BaseTableSnapshotDto | null;
  refreshBaseSnapshot(
    changedKeys?: string[]
  ): Promise<BaseTableSnapshotDto | null>;
  openPaperPdf(
    paperKey: string,
    opts?: { page?: number; annId?: string }
  ): Promise<void>;
  openPaperSplitReading(paperKey: string, notePath?: string): Promise<void>;
  getCommandRegistry?: () => CommandRegistry | undefined;
}

export type QuickSwitcherMode = "open" | "cite" | "command";

export interface QuickSwitcherCommandItem {
  _pfKind: "command";
  command: CommandSpec;
}

export type QuickSwitcherSuggestion =
  | BasePaperRowDto
  | QuickSwitcherCommandItem;

export function isCommandSuggestion(
  item: QuickSwitcherSuggestion
): item is QuickSwitcherCommandItem {
  return (
    typeof item === "object" &&
    item !== null &&
    "_pfKind" in item &&
    (item as QuickSwitcherCommandItem)._pfKind === "command"
  );
}

export interface ScoredPaperMatch {
  row: BasePaperRowDto;
  score: number;
}

/**
 * Render matched search tokens wrapped in `<mark class="pf-qs-hl">` safely via DOM nodes.
 */
function renderHighlightedText(
  el: HTMLElement,
  text: string,
  query: string
): void {
  const cleanQ = query.replace(/^>\s*/, "").trim().toLowerCase();
  if (!cleanQ || !text) {
    el.textContent = text;
    return;
  }
  const tokens = Array.from(
    new Set(cleanQ.split(/\s+/).filter((tok) => tok.length >= 2))
  );
  if (tokens.length === 0) {
    el.textContent = text;
    return;
  }
  const escaped = tokens.map((tok) =>
    tok.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  );
  const re = new RegExp(`(${escaped.join("|")})`, "gi");
  let lastIdx = 0;
  let match: RegExpExecArray | null;
  while ((match = re.exec(text)) !== null) {
    if (match.index > lastIdx) {
      el.appendChild(document.createTextNode(text.slice(lastIdx, match.index)));
    }
    const mark = document.createElement("mark");
    mark.className = "pf-qs-hl";
    mark.textContent = match[0];
    el.appendChild(mark);
    lastIdx = match.index + match[0].length;
    if (match[0].length === 0) break;
  }
  if (lastIdx < text.length) {
    el.appendChild(document.createTextNode(text.slice(lastIdx)));
  }
}

/**
 * Pure multi-token relevance scorer over cached BasePaperRowDto items.
 * Zero RPC calls — runs completely in memory in sub-millisecond time.
 */
export function scorePaperQuickMatch(
  row: BasePaperRowDto,
  query: string
): number {
  const q = query.trim().toLowerCase();
  if (!q) {
    const yr = Number.parseInt(String(row.year || "0"), 10) || 0;
    return 1000 + Math.min(3000, yr);
  }
  const tokens = q.split(/\s+/).filter(Boolean);
  const title = (row.title || "").toLowerCase();
  const author = (row.first_author || "").toLowerCase();
  const year = (row.year || "").toLowerCase();
  const journal = (row.journal || "").toLowerCase();
  const domain = (row.domain || "").toLowerCase();
  const key = (row.zotero_key || "").toLowerCase();

  let totalScore = 0;
  for (const tok of tokens) {
    let bestTok = 0;
    if (key === tok || year === tok) {
      bestTok = Math.max(bestTok, 120);
    }
    if (title.startsWith(tok)) {
      bestTok = Math.max(bestTok, 110);
    } else if (title.includes(tok)) {
      bestTok = Math.max(bestTok, 80);
    }
    if (author.startsWith(tok)) {
      bestTok = Math.max(bestTok, 95);
    } else if (author.includes(tok)) {
      bestTok = Math.max(bestTok, 70);
    }
    if (journal.includes(tok)) {
      bestTok = Math.max(bestTok, 55);
    }
    if (domain.includes(tok)) {
      bestTok = Math.max(bestTok, 45);
    }
    if (key.includes(tok) || year.includes(tok)) {
      bestTok = Math.max(bestTok, 60);
    }
    if (bestTok === 0) {
      return 0;
    }
    totalScore += bestTok;
  }

  if (title.includes(q)) totalScore += 60;
  if (row.has_pdf) totalScore += 4;
  if (row.main_note_path) totalScore += 4;
  return totalScore;
}

/**
 * Format an Obsidian citation/wikilink for inserting into an active Markdown editor
 * or copying to the system clipboard.
 */
export function formatPaperCitation(row: BasePaperRowDto): string {
  const notePath = String(row.main_note_path || "").trim();
  if (notePath) {
    const base = notePath.replace(/^.*[\\/]/, "").replace(/\.md$/i, "");
    if (base) return `[[${base}]]`;
  }
  return `[@${row.zotero_key}]`;
}

function resolveSuggestModalBase(): typeof obsidian.SuggestModal {
  try {
    const mod = (obsidian as unknown as Record<string, unknown>)[
      "SuggestModal"
    ];
    if (typeof mod === "function") {
      return mod as typeof obsidian.SuggestModal;
    }
  } catch {
    // Partial mock in non-modal unit tests
  }
  return class {} as unknown as typeof obsidian.SuggestModal;
}

function resolveMarkdownViewClass():
  | (new (...args: unknown[]) => obsidian.MarkdownView)
  | null {
  try {
    const mod = (obsidian as unknown as Record<string, unknown>)[
      "MarkdownView"
    ];
    if (typeof mod === "function") {
      return mod as new (...args: unknown[]) => obsidian.MarkdownView;
    }
  } catch {
    // Partial mock fallback
  }
  return null;
}

const BaseSuggestModal = resolveSuggestModalBase();

export class PaperForgeQuickSwitcherModal extends BaseSuggestModal<QuickSwitcherSuggestion> {
  plugin: PaperForgeQuickSwitcherHost;
  mode: QuickSwitcherMode;
  private _refreshRequested = false;
  private _lastQuery = "";

  constructor(
    app: obsidian.App,
    plugin: PaperForgeQuickSwitcherHost,
    mode: QuickSwitcherMode = "open"
  ) {
    super(app);
    this.plugin = plugin;
    this.mode = mode;
    this.limit = 40;
    this.setPlaceholder(
      mode === "cite"
        ? t("qs_placeholder_cite")
        : mode === "command"
          ? t("qs_placeholder_command") ||
            "Type a PaperForge command or switch to paper search..."
          : t("qs_placeholder_open")
    );
    this.setInstructions([
      {
        command: "↵",
        purpose:
          mode === "cite" ? t("qs_inst_insert_cite") : t("qs_inst_open_note"),
      },
      { command: "Ctrl/⌘ ↵", purpose: t("qs_inst_open_pdf") },
      { command: "Alt ↵", purpose: t("qs_inst_split_reading") },
      { command: "Shift ↵", purpose: t("qs_inst_copy_cite") },
      {
        command: ">",
        purpose: t("qs_inst_commands_hint") || "Prefix > for commands",
      },
    ]);
  }

  onOpen(): void {
    super.onOpen?.();
    this.modalEl?.classList?.add("pf-qs-modal");
    if (this.mode === "command" && this.inputEl) {
      this.inputEl.value = "> ";
      this.inputEl.dispatchEvent(new Event("input"));
    }
    if (!this.plugin.getBaseSnapshotCache() && !this._refreshRequested) {
      this._refreshRequested = true;
      void this.plugin.refreshBaseSnapshot().then(() => {
        if (this.inputEl) {
          this.inputEl.dispatchEvent(new Event("input"));
        }
      });
    }
  }

  getSuggestions(query: string): QuickSwitcherSuggestion[] {
    this._lastQuery = query;
    const trimmed = query.trimStart();
    if (this.mode === "command" || trimmed.startsWith(">")) {
      const reg = this.plugin.getCommandRegistry?.();
      if (!reg) return [];
      const cmdQuery = trimmed.startsWith(">")
        ? trimmed.slice(1).trim()
        : trimmed;
      return reg
        .search(cmdQuery)
        .slice(0, this.limit || 40)
        .map((command) => ({ _pfKind: "command", command }));
    }

    const snap = this.plugin.getBaseSnapshotCache();
    const rows = Object.values(snap?.rows ?? {});
    if (rows.length === 0) return [];
    const scored: ScoredPaperMatch[] = [];
    for (const row of rows) {
      const score = scorePaperQuickMatch(row, query);
      if (score > 0) {
        scored.push({ row, score });
      }
    }
    scored.sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return (a.row.title || a.row.zotero_key).localeCompare(
        b.row.title || b.row.zotero_key
      );
    });
    return scored.slice(0, this.limit || 40).map((s) => s.row);
  }

  renderSuggestion(item: QuickSwitcherSuggestion, el: HTMLElement): void {
    if (isCommandSuggestion(item)) {
      const cmd = item.command;
      el.classList.add("pf-qs-item", "pf-qs-item-cmd");
      const main = document.createElement("div");
      main.className = "pf-qs-item-main";
      el.appendChild(main);

      const titleEl = document.createElement("div");
      titleEl.className = "pf-qs-title";
      renderHighlightedText(titleEl, cmd.title, this._lastQuery);
      main.appendChild(titleEl);

      const metaEl = document.createElement("div");
      metaEl.className = "pf-qs-meta pf-tnum";
      metaEl.textContent = cmd.subtitle
        ? `${cmd.category} · ${cmd.subtitle}`
        : cmd.category || t("qs_cmd_badge") || "Command";
      main.appendChild(metaEl);

      const badges = document.createElement("div");
      badges.className = "pf-qs-badges";
      el.appendChild(badges);

      const cmdBadge = document.createElement("span");
      cmdBadge.className = "pf-qs-badge pf-qs-badge-cmd";
      if (cmd.icon) {
        const ic = document.createElement("span");
        ic.className = "pf-kit-list-item-icon";
        setPfIcon(ic, cmd.icon, 12);
        cmdBadge.appendChild(ic);
      }
      cmdBadge.appendChild(
        document.createTextNode(cmd.category || t("qs_cmd_badge") || "Command")
      );
      badges.appendChild(cmdBadge);

      const shortcut =
        this.plugin.getCommandRegistry?.()?.shortcutFor(cmd.id) ||
        cmd.defaultShortcut;
      if (shortcut) {
        renderKeycap(badges, shortcut);
      }
      return;
    }

    const row = item;
    el.classList.add("pf-qs-item");
    const main = document.createElement("div");
    main.className = "pf-qs-item-main";
    el.appendChild(main);

    const titleEl = document.createElement("div");
    titleEl.className = "pf-qs-title";
    renderHighlightedText(
      titleEl,
      row.title || row.zotero_key,
      this._lastQuery
    );
    main.appendChild(titleEl);

    const metaParts: string[] = [];
    if (row.first_author) metaParts.push(row.first_author);
    if (row.year) metaParts.push(row.year);
    if (row.journal) metaParts.push(row.journal);
    if (row.impact_factor) metaParts.push(`IF ${row.impact_factor}`);

    const metaEl = document.createElement("div");
    metaEl.className = "pf-qs-meta pf-tnum";
    renderHighlightedText(
      metaEl,
      metaParts.length > 0 ? metaParts.join(" · ") : row.zotero_key,
      this._lastQuery
    );
    main.appendChild(metaEl);

    const badges = document.createElement("div");
    badges.className = "pf-qs-badges";
    el.appendChild(badges);

    if (row.domain) {
      const domBadge = document.createElement("span");
      domBadge.className = "pf-qs-badge pf-qs-badge-domain";
      domBadge.textContent = row.domain;
      badges.appendChild(domBadge);
    }
    if (row.ocr_status && row.ocr_status !== "none") {
      const stBadge = document.createElement("span");
      stBadge.className = `pf-qs-badge pf-qs-badge-${row.ocr_status}`;
      stBadge.textContent = row.ocr_status.toUpperCase();
      badges.appendChild(stBadge);
    }
    if (row.has_pdf) {
      const pdfBadge = document.createElement("span");
      pdfBadge.className = "pf-qs-badge pf-qs-badge-pdf";
      pdfBadge.textContent = "PDF";
      badges.appendChild(pdfBadge);
    }
  }

  onChooseSuggestion(
    item: QuickSwitcherSuggestion,
    evt: MouseEvent | KeyboardEvent
  ): void {
    if (isCommandSuggestion(item)) {
      item.command.run();
      return;
    }
    const row = item;
    const isAlt = Boolean(evt?.altKey);
    const isMod = Boolean(evt?.ctrlKey || evt?.metaKey);
    const isShift = Boolean(evt?.shiftKey);

    if (isAlt) {
      void this.plugin.openPaperSplitReading(
        row.zotero_key,
        row.main_note_path
      );
      return;
    }
    if (isMod) {
      if (row.has_pdf) {
        void this.plugin.openPaperPdf(row.zotero_key);
      } else if (row.main_note_path) {
        void this.app.workspace?.openLinkText?.(row.main_note_path, "", false);
      }
      return;
    }
    if (isShift || this.mode === "cite") {
      void this._insertOrCopyCitation(row);
      return;
    }
    if (row.main_note_path) {
      void this.app.workspace?.openLinkText?.(row.main_note_path, "", false);
      return;
    }
    if (row.has_pdf) {
      void this.plugin.openPaperPdf(row.zotero_key);
    }
  }

  private async _insertOrCopyCitation(row: BasePaperRowDto): Promise<void> {
    const citation = formatPaperCitation(row);
    const MdView = resolveMarkdownViewClass();
    const activeView = MdView
      ? this.app.workspace?.getActiveViewOfType?.(MdView)
      : null;
    if (activeView?.editor?.replaceSelection) {
      activeView.editor.replaceSelection(citation);
      new obsidian.Notice(
        t("qs_notice_inserted").replace("{cite}", citation),
        2500
      );
      return;
    }
    try {
      await navigator.clipboard?.writeText?.(citation);
      new obsidian.Notice(
        t("qs_notice_copied").replace("{cite}", citation),
        2500
      );
    } catch {
      new obsidian.Notice(citation, 3000);
    }
  }
}
