// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { BasePaperRowDto } from "../src/client/paperforge-client";

const openLinkTextMock = vi.fn(async () => undefined);
const noticeMock = vi.fn();
const replaceSelectionMock = vi.fn();
let activeMarkdownView: {
  editor: { replaceSelection: typeof replaceSelectionMock };
} | null = null;

vi.mock("obsidian", () => ({
  Notice: function Notice(msg: string) {
    noticeMock(msg);
  },
  MarkdownView: class MarkdownView {},
  SuggestModal: class SuggestModal<T> {
    app: unknown;
    modalEl = document.createElement("div");
    inputEl = document.createElement("input");
    limit = 50;
    constructor(app: unknown) {
      this.app = app;
    }
    setPlaceholder() {}
    setInstructions() {}
    onOpen() {}
    getSuggestions(_q: string): T[] {
      return [];
    }
    renderSuggestion(_v: T, _el: HTMLElement) {}
    onChooseSuggestion(_v: T, _evt: MouseEvent | KeyboardEvent) {}
  },
}));

import {
  PaperForgeQuickSwitcherModal,
  formatPaperCitation,
  isCommandSuggestion,
  scorePaperQuickMatch,
} from "../src/views/quick-switcher";
import { CommandRegistry } from "../src/uikit/commands";

function makeRow(
  over: Partial<BasePaperRowDto> & { zotero_key: string }
): BasePaperRowDto {
  return {
    title: "Default Title",
    first_author: "Smith",
    year: "2024",
    journal: "Radiology",
    impact_factor: "12.1",
    impact_factor_source: "jcr",
    journal_partition: "Q1",
    domain: "Stroke",
    collections: [],
    has_pdf: true,
    ocr_status: "done",
    deep_reading_status: "done",
    main_note_path: `Literature/${over.zotero_key}.md`,
    pdf_path: `${over.zotero_key}.pdf`,
    user_ann_count: 2,
    agent_ann_count: 1,
    memory_facet_count: 3,
    needs_diagnostic: false,
    ...over,
  };
}

describe("PaperForgeQuickSwitcherModal", () => {
  const rows: Record<string, BasePaperRowDto> = {
    P1: makeRow({
      zotero_key: "P1",
      title: "Attention UNet for Stroke Segmentation",
      first_author: "Chen L",
      year: "2024",
      journal: "MedIA",
      domain: "Segmentation",
      main_note_path: "Literature/Chen 2024 Attention UNet.md",
    }),
    P2: makeRow({
      zotero_key: "P2",
      title: "Diffusion Models in Chest CT",
      first_author: "Smith J",
      year: "2023",
      journal: "Radiology",
      domain: "Chest",
      main_note_path: "",
      has_pdf: true,
    }),
  };

  const host = {
    getBaseSnapshotCache: () => ({
      generated_at: "2026-01-01T00:00:00Z",
      row_count: 2,
      rows,
    }),
    refreshBaseSnapshot: vi.fn(async () => null),
    openPaperPdf: vi.fn(async () => undefined),
    openPaperSplitReading: vi.fn(async () => undefined),
  };

  const app = {
    workspace: {
      openLinkText: openLinkTextMock,
      getActiveViewOfType: () => activeMarkdownView,
    },
  } as unknown as import("obsidian").App;

  beforeEach(() => {
    vi.clearAllMocks();
    activeMarkdownView = null;
  });

  it("scores multi-token queries across title, author, year, and domain", () => {
    expect(
      scorePaperQuickMatch(rows.P1, "attention 2024 chen")
    ).toBeGreaterThan(200);
    expect(scorePaperQuickMatch(rows.P1, "nonexistenttoken")).toBe(0);
    expect(
      scorePaperQuickMatch(rows.P2, "radiology diffusion")
    ).toBeGreaterThan(100);
  });

  it("formats wikilink when note exists and citekey fallback otherwise", () => {
    expect(formatPaperCitation(rows.P1)).toBe("[[Chen 2024 Attention UNet]]");
    expect(formatPaperCitation(rows.P2)).toBe("[@P2]");
  });

  it("filters, renders, and dispatches open / PDF / split / cite actions", () => {
    const modal = new PaperForgeQuickSwitcherModal(app, host, "open");
    modal.onOpen();
    expect(modal.modalEl.classList.contains("pf-qs-modal")).toBe(true);

    const hits = modal.getSuggestions("stroke 2024");
    expect(hits.map((h) => h.zotero_key)).toEqual(["P1"]);

    const itemEl = document.createElement("div");
    modal.renderSuggestion(rows.P1, itemEl);
    expect(itemEl.querySelector(".pf-qs-title")?.textContent).toContain(
      "Attention UNet"
    );
    expect(itemEl.querySelector(".pf-qs-badge-pdf")).not.toBeNull();

    modal.onChooseSuggestion(rows.P1, new MouseEvent("click"));
    expect(openLinkTextMock).toHaveBeenCalledWith(
      rows.P1.main_note_path,
      "",
      false
    );

    modal.onChooseSuggestion(
      rows.P1,
      new KeyboardEvent("keydown", { key: "Enter", ctrlKey: true })
    );
    expect(host.openPaperPdf).toHaveBeenCalledWith("P1");

    modal.onChooseSuggestion(
      rows.P1,
      new KeyboardEvent("keydown", { key: "Enter", altKey: true })
    );
    expect(host.openPaperSplitReading).toHaveBeenCalledWith(
      "P1",
      rows.P1.main_note_path
    );
  });

  it("inserts formatted citation at cursor in cite mode", () => {
    activeMarkdownView = { editor: { replaceSelection: replaceSelectionMock } };
    const modal = new PaperForgeQuickSwitcherModal(app, host, "cite");
    modal.onChooseSuggestion(
      rows.P1,
      new KeyboardEvent("keydown", { key: "Enter" })
    );
    expect(replaceSelectionMock).toHaveBeenCalledWith(
      "[[Chen 2024 Attention UNet]]"
    );
  });

  it("supports > prefix and command mode with match highlighting and execution", () => {
    const reg = new CommandRegistry();
    const runSync = vi.fn();
    reg.register({
      id: "sync-lib",
      title: "Sync Zotero Library",
      category: "Library",
      defaultShortcut: "Mod+Shift+S",
      run: runSync,
    });
    const cmdHost = { ...host, getCommandRegistry: () => reg };

    const modal = new PaperForgeQuickSwitcherModal(app, cmdHost, "open");
    const cmdHits = modal.getSuggestions("> sync");
    expect(cmdHits).toHaveLength(1);
    expect(isCommandSuggestion(cmdHits[0])).toBe(true);

    const itemEl = document.createElement("div");
    modal.renderSuggestion(cmdHits[0], itemEl);
    expect(itemEl.querySelector(".pf-qs-badge-cmd")).not.toBeNull();
    expect(itemEl.querySelector(".pf-qs-hl")?.textContent?.toLowerCase()).toBe(
      "sync"
    );

    modal.onChooseSuggestion(cmdHits[0], new MouseEvent("click"));
    expect(runSync).toHaveBeenCalledOnce();
  });
});
