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

describe("PaperForgeBasesView (AsterLab native Base + multi-select header)", () => {
  let snapshot: BaseTableSnapshotDto;
  let stateListeners: Array<() => void>;
  let host: PaperForgeBasesHost;
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
        K_WAIT: {
          zotero_key: "K_WAIT",
          title: "Meniscus Hydrogel Mechanics",
          first_author: "Wang",
          year: "2024",
          journal: "Acta Biomater.",
          impact_factor: "9.4",
          domain: "Sports",
          has_pdf: true,
          do_ocr: false,
          analyze: false,
          ocr_status: "pending",
          deep_reading_status: "pending",
          main_note_path: "Resources/Literature/Sports/K_WAIT/K_WAIT.md",
          user_ann_count: 1,
          agent_ann_count: 0,
          memory_facet_count: 0,
          memory_updated_at: "",
          needs_diagnostic: false,
        },
      },
    };
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
      getClient: () => ({}) as any,
      getBaseSnapshotCache: () => snapshot,
      refreshBaseSnapshot,
      isOcrRunningForKey: (k: string) => k === "K_WAIT",
      _ocrProgress: { current: 1, total: 2, key: "K_WAIT" },
      openPaperPdf,
      requestOcrRun,
      triggerManualSync: vi.fn(),
      openOcrDiagnostic,
    };
  });

  it("renders calm Base rows with custom config order, leading PDF icon, and contextual selection header bar", async () => {
    const container = dom.window.document.createElement("div");
    const view = new PaperForgeBasesView({} as any, container, host);
    expect(view.type).toBe(VIEW_TYPE_PF_BASE_TABLE);

    // Custom column order including a custom user property `note.topic`
    (view as any).config = {
      get: (k: string) => (k === "show_annotations" ? true : false),
      getOrder: () => [
        "note.title",
        "note.topic",
        "note.year",
        "note.ocr_status",
      ],
      getDisplayName: (id: string) =>
        id === "note.topic" ? "研究课题" : id.replace(/^note\./, ""),
    };

    const mkEntry = (key: string, topic: string) => ({
      file: {
        path: snapshot.rows[key].main_note_path,
        basename: key,
      },
      getValue: (propId: string) => {
        if (propId === "note.zotero_key") {
          return { data: key, toString: () => key };
        }
        if (propId === "note.topic") {
          return { data: topic, toString: () => topic };
        }
        return null;
      },
    });

    (view as any).data = {
      data: [
        mkEntry("K_FAIL", "肩袖损伤"),
        mkEntry("K_WAIT", "半月板水凝胶"),
        mkEntry("K_DONE", "电纺支架"),
      ],
    };

    view.onload();
    view.onDataUpdated();

    // No duplicate top toolbar, no seq tag, no row emojis, no selection bar at rest
    expect(container.querySelector(".pf-base-toolbar")).toBeNull();
    expect(container.querySelector(".pf-base-selection-bar")).toBeNull();
    expect(container.textContent).not.toContain("seq #");
    expect(container.textContent).not.toContain("🧠");
    expect(container.textContent).not.toContain("⚡");

    // Custom user column rendered from config.getOrder() & getDisplayName()
    expect(container.textContent).toContain("研究课题");
    expect(container.textContent).toContain("肩袖损伤");
    expect(container.textContent).toContain("电纺支架");

    const rows = Array.from(container.querySelectorAll("tr.pf-base-row"));
    expect(rows).toHaveLength(3);
    expect(rows[0].getAttribute("data-paper-key")).toBe("K_FAIL");
    expect(rows[1].getAttribute("data-paper-key")).toBe("K_WAIT");
    expect(rows[2].getAttribute("data-paper-key")).toBe("K_DONE");

    // Live running progress & calm outline status labels
    expect(rows[0].textContent).toContain("解析异常");
    expect(rows[1].textContent).toContain("解析中 1/2");
    expect(rows[2].textContent).toContain("已精读");
    expect(rows[2].textContent).toContain("10 批注 · 4 记忆");

    // Leading PDF icon opens PDF; title click opens main note
    const pdfBtn = rows[2].querySelector(
      '[data-pf-testid="base-open-pdf"]'
    ) as HTMLButtonElement;
    pdfBtn.click();
    expect(openPaperPdf).toHaveBeenCalledWith("K_DONE");

    const noteBtn = rows[2].querySelector(
      '[data-pf-testid="base-open-note"]'
    ) as HTMLButtonElement;
    noteBtn.click();
    expect(openLinkText).toHaveBeenCalledWith(
      "Resources/Literature/Ortho/K_DONE/K_DONE.md",
      ""
    );

    // Click failed status pill -> opens diagnostic
    const diagPill = rows[0].querySelector(
      '[data-pf-testid="base-status-diag"]'
    ) as HTMLButtonElement;
    diagPill.click();
    expect(openOcrDiagnostic).toHaveBeenCalledWith("K_FAIL");

    // Check first row -> contextual header bar appears with Parse Fulltext & View Diagnostic
    const cbFail = rows[0].querySelector(
      'input[data-pf-select-key="K_FAIL"]'
    ) as HTMLInputElement;
    cbFail.checked = true;
    cbFail.dispatchEvent(new dom.window.Event("change"));

    const selBar = container.querySelector(
      '[data-pf-testid="base-selection-bar"]'
    );
    expect(selBar).not.toBeNull();
    expect(selBar?.textContent).toMatch(/1 selected|已选 1 篇/);
    expect(
      selBar?.querySelector('[data-pf-testid="base-open-diag"]')
    ).not.toBeNull();

    // Shift+Click third row -> range selects rows 0..2
    const cbDone = container.querySelector(
      'input[data-pf-select-key="K_DONE"]'
    ) as HTMLInputElement;
    cbDone.dispatchEvent(
      new dom.window.MouseEvent("click", { shiftKey: true })
    );
    cbDone.checked = true;
    cbDone.dispatchEvent(new dom.window.Event("change"));

    const selBarRange = container.querySelector(
      '[data-pf-testid="base-selection-bar"]'
    );
    expect(selBarRange?.textContent).toMatch(/3 selected|已选 3 篇/);

    // Parse Fulltext dispatches Python ActionScope { kind: "papers", keys }
    const runBtn = container.querySelector(
      '[data-pf-testid="base-run-selected-ocr"]'
    ) as HTMLButtonElement;
    runBtn.click();
    expect(requestOcrRun).toHaveBeenCalledWith({
      kind: "papers",
      keys: ["K_FAIL", "K_WAIT", "K_DONE"],
    });

    // Live state-changed update preserves selection & updates counts
    snapshot.rows.K_DONE.memory_facet_count = 5;
    stateListeners[0]();
    expect(container.textContent).toContain("10 批注 · 5 记忆");
    expect(
      container.querySelector('[data-pf-testid="base-selection-bar"]')
        ?.textContent
    ).toMatch(/3 selected|已选 3 篇/);

    // Clear selection hides contextual bar
    const clearBtn = container.querySelector(
      '[data-pf-testid="base-clear-selection"]'
    ) as HTMLButtonElement;
    clearBtn.click();
    expect(
      container.querySelector('[data-pf-testid="base-selection-bar"]')
    ).toBeNull();

    view.onunload();
  });

  it("supports Obsidian groupedData sections", () => {
    const container = dom.window.document.createElement("div");
    const view = new PaperForgeBasesView({} as any, container, host);
    (view as any).data = {
      groupedData: [
        {
          hasKey: () => true,
          key: { data: "Ortho", toString: () => "Ortho" },
          entries: [
            {
              file: {
                basename: "K_DONE",
                path: snapshot.rows.K_DONE.main_note_path,
              },
              getValue: () => ({ data: "K_DONE" }),
            },
          ],
        },
        {
          hasKey: () => true,
          key: { data: "Sports", toString: () => "Sports" },
          entries: [
            {
              file: {
                basename: "K_WAIT",
                path: snapshot.rows.K_WAIT.main_note_path,
              },
              getValue: () => ({ data: "K_WAIT" }),
            },
          ],
        },
      ],
    };

    view.onDataUpdated();
    const groups = Array.from(
      container.querySelectorAll("tr.pf-base-group-row")
    );
    expect(groups).toHaveLength(2);
    expect(groups[0].textContent).toContain("Ortho");
    expect(groups[0].textContent).toContain("1 篇");
    expect(groups[1].textContent).toContain("Sports");
  });

  it("provides sticky multi-condition filter bar (domain -> cascading collection, IF threshold, status, openalex_2yr marker)", () => {
    snapshot.rows.K_DONE.collections = ["BoneRegen/Hydrogels"];
    snapshot.rows.K_WAIT.collections = ["SportsMed/Meniscus"];
    snapshot.rows.K_WAIT.impact_factor_source = "openalex_2yr";

    let savedFilters: Record<string, unknown> = {};
    host.getBaseFilters = () => savedFilters as any;
    host.setBaseFilters = (_key, next) => {
      savedFilters = next as Record<string, unknown>;
    };

    const container = dom.window.document.createElement("div");
    const view = new PaperForgeBasesView({} as any, container, host);
    view.onDataUpdated();

    // OpenAlex fallback metric displays ≈ provenance mark
    expect(container.textContent).toContain("9.4≈");

    // 1. Filter by Domain = Ortho -> cascades collections list and filters rows
    const domSel = container.querySelector<HTMLSelectElement>(
      '[data-pf-testid="base-filter-domain"]'
    )!;
    domSel.value = "Ortho";
    domSel.dispatchEvent(new dom.window.Event("change"));
    expect(container.querySelectorAll("tr.pf-base-row")).toHaveLength(2);
    expect(savedFilters.domain).toBe("Ortho");

    // 2. Stack IF >= 10 -> narrows Ortho down to K_DONE (IF 12.8)
    const ifSel = container.querySelector<HTMLSelectElement>(
      '[data-pf-testid="base-filter-if"]'
    )!;
    ifSel.value = "10";
    ifSel.dispatchEvent(new dom.window.Event("change"));
    expect(container.querySelectorAll("tr.pf-base-row")).toHaveLength(1);
    expect(container.textContent).toContain("Electrospun Scaffold Trial");

    // 3. Reset clears filters cleanly
    const resetBtn = container.querySelector<HTMLButtonElement>(
      '[data-pf-testid="base-filter-reset"]'
    )!;
    resetBtn.click();
    expect(container.querySelectorAll("tr.pf-base-row")).toHaveLength(3);
  });
});
