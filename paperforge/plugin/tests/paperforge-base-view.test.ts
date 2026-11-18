import { describe, it, expect, vi, beforeEach } from "vitest";
import { JSDOM } from "jsdom";

const dom = new JSDOM("<!doctype html><html><body></body></html>");
(globalThis as any).document = dom.window.document;
(globalThis as any).window = dom.window;
(globalThis as any).HTMLElement = dom.window.HTMLElement;

vi.mock("obsidian", () => ({
  Component: class {
    load() {}
    unload() {}
  },
  Notice: class {
    constructor(_msg: string) {}
  },
}));

import {
  PaperForgeBasesView,
  type PaperForgeBasesHost,
} from "../src/views/paperforge-base-view";
import { VIEW_TYPE_PF_BASE_TABLE } from "../src/constants";
import type { BaseTableSnapshotDto } from "../src/client/paperforge-client";

describe("PaperForgeBasesView & live state reactivity (Phase 1)", () => {
  let snapshot: BaseTableSnapshotDto;
  let stateListeners: Array<() => void>;
  let host: PaperForgeBasesHost;
  let setNoteFlag: ReturnType<typeof vi.fn>;
  let refreshBaseSnapshot: ReturnType<typeof vi.fn>;
  let openPaperPdf: ReturnType<typeof vi.fn>;
  let requestOcrRun: ReturnType<typeof vi.fn>;
  let openOcrDiagnostic: ReturnType<typeof vi.fn>;
  let openLinkText: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    stateListeners = [];
    snapshot = {
      seq: 3,
      updated_at: "2026-11-18T00:00:00Z",
      rows: {
        K_DONE: {
          zotero_key: "K_DONE",
          title: "Electrospun Scaffold Trial",
          first_author: "Zhang",
          year: "2025",
          journal: "Biomaterials",
          impact_factor: "12.8",
          domain: "Ortho",
          has_pdf: true,
          do_ocr: false,
          analyze: true,
          ocr_status: "done",
          deep_reading_status: "done",
          main_note_path: "Resources/Literature/Ortho/K_DONE/K_DONE.md",
          user_ann_count: 3,
          agent_ann_count: 7,
          memory_facet_count: 4,
          memory_updated_at: "2026-11-18T00:00:00Z",
          needs_diagnostic: false,
        },
        K_FAIL: {
          zotero_key: "K_FAIL",
          title: "Scanned Legacy Protocol",
          first_author: "Li",
          year: "2018",
          journal: "CORR",
          impact_factor: "4.2",
          domain: "Ortho",
          has_pdf: true,
          do_ocr: false,
          analyze: false,
          ocr_status: "failed",
          deep_reading_status: "pending",
          main_note_path: "Resources/Literature/Ortho/K_FAIL/K_FAIL.md",
          user_ann_count: 0,
          agent_ann_count: 0,
          memory_facet_count: 0,
          memory_updated_at: "",
          needs_diagnostic: true,
        },
      },
    };
    setNoteFlag = vi.fn().mockResolvedValue({ ok: true });
    refreshBaseSnapshot = vi.fn().mockResolvedValue(snapshot);
    openPaperPdf = vi.fn().mockResolvedValue(undefined);
    requestOcrRun = vi.fn().mockResolvedValue(undefined);
    openOcrDiagnostic = vi.fn();
    openLinkText = vi.fn().mockResolvedValue(undefined);

    host = {
      app: {
        workspace: {
          on: (_ev: string, cb: () => void) => {
            stateListeners.push(cb);
            return cb;
          },
          offref: vi.fn(),
          openLinkText,
        },
      } as any,
      getClient: () => ({ setNoteFlag }) as any,
      getBaseSnapshotCache: () => snapshot,
      refreshBaseSnapshot,
      isOcrRunningForKey: (k: string) => k === "K_FAIL",
      _ocrProgress: { current: 1, total: 2, key: "K_FAIL" },
      openPaperPdf,
      requestOcrRun,
      triggerManualSync: vi.fn(),
      openOcrDiagnostic,
    };
  });

  it("renders Base entries with physical read/write separation, live status, cognitive pills, and actions", async () => {
    const container = dom.window.document.createElement("div");
    const view = new PaperForgeBasesView({} as any, container, host);
    expect(view.type).toBe(VIEW_TYPE_PF_BASE_TABLE);

    // Base QueryResult supplies filtered/sorted subset (respects Obsidian native Filter/Sort)
    (view as any).data = {
      data: [
        {
          file: {
            path: "Resources/Literature/Ortho/K_FAIL/K_FAIL.md",
            basename: "K_FAIL",
          },
          getValue: () => ({ data: "K_FAIL", toString: () => "K_FAIL" }),
        },
        {
          file: {
            path: "Resources/Literature/Ortho/K_DONE/K_DONE.md",
            basename: "K_DONE",
          },
          getValue: () => ({ data: "K_DONE", toString: () => "K_DONE" }),
        },
      ],
    };

    view.onload();
    view.onDataUpdated();

    const rows = Array.from(container.querySelectorAll("tr.pf-base-row"));
    expect(rows).toHaveLength(2);
    // Order matches BasesQueryResult
    expect(rows[0].getAttribute("data-paper-key")).toBe("K_FAIL");
    expect(rows[1].getAttribute("data-paper-key")).toBe("K_DONE");

    // Live OCR running badge for K_FAIL, Done + Deep-read + cognitive counts for K_DONE
    expect(rows[0].textContent).toContain("⚡ OCR (1/2)");
    expect(rows[1].textContent).toContain("🧠 4");
    expect(rows[1].textContent).toContain("🖍️ 3");
    expect(rows[1].textContent).toContain("🤖 7");

    // Checkbox mutation routes through Python authority client.setNoteFlag (never YAML direct write)
    const doOcrCheckbox = rows[0].querySelector(
      'input[data-pf-flag="do_ocr"]'
    ) as HTMLInputElement;
    doOcrCheckbox.checked = true;
    doOcrCheckbox.dispatchEvent(new dom.window.Event("change"));
    await vi.waitFor(() => {
      expect(setNoteFlag).toHaveBeenCalledWith("K_FAIL", "do_ocr", true);
      expect(refreshBaseSnapshot).toHaveBeenCalledWith(["K_FAIL"]);
    });

    // Interactive row action buttons
    const pdfBtn = rows[1].querySelector(
      '[data-pf-testid="base-open-pdf"]'
    ) as HTMLButtonElement;
    pdfBtn.click();
    expect(openPaperPdf).toHaveBeenCalledWith("K_DONE");

    const diagBtn = rows[0].querySelector(
      '[data-pf-testid="base-open-diag"]'
    ) as HTMLButtonElement;
    diagBtn.click();
    expect(openOcrDiagnostic).toHaveBeenCalledWith("K_FAIL");

    // External state-seq update triggers live table re-render
    snapshot.rows.K_DONE.memory_facet_count = 5;
    snapshot.seq = 4;
    stateListeners[0]();
    expect(container.textContent).toContain("seq #4");
    expect(container.textContent).toContain("🧠 5");

    view.onunload();
  });
});
