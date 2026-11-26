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
import { setLanguage } from "../src/i18n";
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
      get: (k: string) =>
        k === "show_annotations"
          ? true
          : k === "compact_rows"
            ? false
            : undefined,
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

    // Live running progress & calm outline status labels (follows active i18n locale)
    setLanguage({} as any, "zh");
    view.render();
    const rowsZh = Array.from(container.querySelectorAll("tr.pf-base-row"));
    expect(rowsZh[0].textContent).toContain("解析异常");
    expect(rowsZh[1].textContent).toContain("解析中 1/2");
    expect(rowsZh[2].textContent).toContain("已精读");
    expect(rowsZh[2].textContent).toContain("10 批注 · 4 记忆");

    setLanguage({} as any, "en");
    view.render();
    const rowsEn = Array.from(container.querySelectorAll("tr.pf-base-row"));
    expect(rowsEn[0].textContent).toContain("Failed");
    expect(rowsEn[1].textContent).toContain("Processing 1/2");
    expect(rowsEn[2].textContent).toContain("Deep Read");
    expect(rowsEn[2].textContent).toContain("10 notes · 4 memory");

    // Leading PDF icon opens PDF; title click opens main note
    const pdfBtn = rowsEn[2].querySelector(
      '[data-pf-testid="base-open-pdf"]'
    ) as HTMLButtonElement;
    pdfBtn.click();
    expect(openPaperPdf).toHaveBeenCalledWith("K_DONE");

    const noteBtn = rowsEn[2].querySelector(
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
    expect(container.textContent).toContain("10 notes · 5 memory");
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

    setLanguage({} as any, "zh");
    view.onDataUpdated();
    const groups = Array.from(
      container.querySelectorAll("tr.pf-base-group-row")
    );
    expect(groups).toHaveLength(2);
    expect(groups[0].textContent).toContain("Ortho");
    expect(groups[0].textContent).toContain("1 篇");
    expect(groups[1].textContent).toContain("Sports");
    setLanguage({} as any, "en");
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

  it("renders title as frameless <a> link with proportional <colgroup>, surgical selection updates, and chunked rendering for 250+ papers", () => {
    const bigRows: Record<string, BaseTableSnapshotDto["rows"][string]> = {};
    for (let i = 0; i < 250; i += 1) {
      const k = `PAPER_${String(i).padStart(4, "0")}`;
      bigRows[k] = {
        zotero_key: k,
        title: `Biomechanical Evaluation of Scaffold Variant #${i}`,
        first_author: `Author ${i}`,
        year: "2025",
        journal: "Biomaterials",
        impact_factor: "11.2",
        domain: i % 2 === 0 ? "Ortho" : "Sports",
        has_pdf: true,
        do_ocr: false,
        analyze: false,
        ocr_status: "done",
        deep_reading_status: "pending",
        main_note_path: `Literature/Ortho/${k}.md`,
        user_ann_count: 1,
        agent_ann_count: 0,
        memory_facet_count: 0,
        memory_updated_at: "",
        needs_diagnostic: false,
      };
    }
    snapshot = { seq: 99, updated_at: "2026-11-24T00:00:00Z", rows: bigRows };

    const container = dom.window.document.createElement("div");
    const view = new PaperForgeBasesView({} as any, container, host);
    setLanguage({} as any, "en");
    view.render();

    // 1. Title uses semantic <a> link (never boxed <button>) & table has proportional <colgroup>
    const firstTitle = container.querySelector(
      '[data-pf-testid="base-open-note"]'
    )!;
    expect(firstTitle.tagName).toBe("A");
    expect(
      container.querySelectorAll("table.pf-base-table colgroup col").length
    ).toBeGreaterThanOrEqual(5);

    // 2. Chunked rendering mounts only initial 80 rows + load-more sentinel (fast initial paint)
    expect(container.querySelectorAll("tr.pf-base-row")).toHaveLength(80);
    const loadMoreBtn = container.querySelector<HTMLButtonElement>(
      '[data-pf-testid="base-load-more"]'
    )!;
    expect(loadMoreBtn).not.toBeNull();
    expect(loadMoreBtn.textContent).toContain("170");

    // 3. Surgical selection toggle NEVER tears down the <table> element
    const tableBefore = container.querySelector("table.pf-base-table");
    const cb0 = container.querySelector<HTMLInputElement>(
      'input[data-pf-select-key="PAPER_0000"]'
    )!;
    cb0.checked = true;
    cb0.dispatchEvent(new dom.window.Event("change"));
    expect(container.querySelector("table.pf-base-table")).toBe(tableBefore);
    expect(
      container.querySelector('[data-pf-testid="base-selection-bar"]')
        ?.textContent
    ).toMatch(/1 selected|已选 1 篇/);

    // 4. Clicking Load More appends the next chunk seamlessly
    loadMoreBtn.click();
    expect(container.querySelectorAll("tr.pf-base-row")).toHaveLength(160);
    expect(container.querySelector("table.pf-base-table")).toBe(tableBefore);

    view.onunload();
  });

  it("preserves filter input identity while typing, isolates filter keys by view, respects displayName & user columns, and renders Value.renderTo", () => {
    const container = dom.window.document.createElement("div");
    const viewA = new PaperForgeBasesView({} as any, container, host);
    const renderContext = { app: host.app };
    (viewA as any).app = { ...host.app, renderContext };
    const customRenderTo = vi.fn((el: HTMLElement) => {
      const tag = el.ownerDocument.createElement("span");
      tag.textContent = "RenderedTag";
      el.appendChild(tag);
    });
    (viewA as any).config = {
      name: "Orthopedics View",
      get: (k: string) =>
        k === "show_summary_footer"
          ? true
          : k === "row_density"
            ? "spacious"
            : undefined,
      getOrder: () => [
        "note.title",
        "note.zotero_key",
        "note.tags",
        "note.impact_factor",
        "note.year",
      ],
      getDisplayName: (id: string) =>
        id === "note.title" ? "论文题目" : id.replace(/^note\./, ""),
      set: vi.fn(),
    };
    (viewA as any).data = {
      data: [
        {
          file: {
            basename: "K_DONE",
            path: snapshot.rows.K_DONE.main_note_path,
          },
          getValue: (id: string) =>
            id === "note.zotero_key"
              ? { data: "K_DONE" }
              : id === "note.tags"
                ? { renderTo: customRenderTo }
                : null,
        },
        {
          file: {
            basename: "K_WAIT",
            path: snapshot.rows.K_WAIT.main_note_path,
          },
          getValue: (id: string) =>
            id === "note.zotero_key" ? { data: "K_WAIT" } : null,
        },
      ],
    };

    viewA.render();
    expect(container.classList.contains("is-spacious")).toBe(true);
    expect(container.textContent).toContain("论文题目");
    expect(container.textContent).toContain("zotero_key");
    expect(customRenderTo).toHaveBeenCalled();
    expect(container.textContent).toContain("RenderedTag");
    expect(
      container.querySelector('[data-pf-testid="base-summary-footer"]')
        ?.textContent
    ).toContain("11.1");

    // Typing search query keeps the exact <input> DOM node intact (zero focus loss)
    const searchBefore = container.querySelector<HTMLInputElement>(
      '[data-pf-testid="base-filter-search"]'
    )!;
    (viewA as any)._updateFilters(
      { query: "Hydrogel" },
      { preserveSearchFocus: true }
    );
    const searchAfter = container.querySelector<HTMLInputElement>(
      '[data-pf-testid="base-filter-search"]'
    )!;
    expect(searchAfter).toBe(searchBefore);
    expect(container.querySelectorAll("tr.pf-base-row")).toHaveLength(1);

    // Header sort click orders rows & sets aria-sort
    (viewA as any)._updateFilters({ query: "" }, { preserveSearchFocus: true });
    const yearTh = container.querySelector<HTMLElement>(
      'th[data-pf-col="year"]'
    )!;
    yearTh.click();
    const sortedRows = Array.from(
      container.querySelectorAll<HTMLElement>("tr.pf-base-row")
    );
    expect(sortedRows[0].getAttribute("data-paper-key")).toBe("K_WAIT");
    expect(
      container
        .querySelector('th[data-pf-col="year"]')
        ?.getAttribute("aria-sort")
    ).toBe("ascending");

    // Per-view filter key isolation
    const containerB = dom.window.document.createElement("div");
    const viewB = new PaperForgeBasesView({} as any, containerB, host);
    (viewB as any).config = { name: "Sports View" };
    expect((viewA as any)._filterKey()).not.toBe((viewB as any)._filterKey());

    viewA.onunload();
  });

  it("collapses and expands groups on click and patches changed rows surgically", () => {
    const container = dom.window.document.createElement("div");
    const view = new PaperForgeBasesView({} as any, container, host);
    (view as any).data = {
      groupedData: [
        {
          hasKey: () => true,
          key: { data: "Ortho" },
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
          key: { data: "Sports" },
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

    view.onload();
    expect(container.querySelectorAll("tr.pf-base-row")).toHaveLength(2);

    const orthoGroup = container.querySelector<HTMLElement>(
      'tr.pf-base-group-row[data-pf-group="Ortho"]'
    )!;
    orthoGroup.click();
    expect(container.querySelectorAll("tr.pf-base-row")).toHaveLength(1);
    expect(
      container
        .querySelector('tr.pf-base-group-row[data-pf-group="Ortho"]')
        ?.getAttribute("aria-expanded")
    ).toBe("false");

    // Re-expand group
    container
      .querySelector<HTMLElement>(
        'tr.pf-base-group-row[data-pf-group="Ortho"]'
      )!
      .click();
    expect(container.querySelectorAll("tr.pf-base-row")).toHaveLength(2);

    // Surgical state-changed patch updates status without rebuilding <table>
    const tableBefore = container.querySelector("table.pf-base-table");
    snapshot.rows.K_DONE.memory_facet_count = 9;
    (view as any)._patchChangedRows(["K_DONE"]);
    expect(container.querySelector("table.pf-base-table")).toBe(tableBefore);
    expect(container.textContent).toContain("9 memory");

    view.onunload();
  });

  it("supports modifier-key opening and hidden filter/checkbox options", () => {
    const container = dom.window.document.createElement("div");
    const view = new PaperForgeBasesView({} as any, container, host);
    (view as any).config = {
      get: (k: string) =>
        k === "show_filter_bar" || k === "show_checkboxes" ? false : undefined,
    };
    (view as any).data = {
      data: [
        {
          file: {
            basename: "K_DONE",
            path: snapshot.rows.K_DONE.main_note_path,
          },
          getValue: () => ({ data: "K_DONE" }),
        },
      ],
    };
    view.render();

    expect(
      container.querySelector('[data-pf-testid="base-filter-bar"]')
    ).toBeNull();
    expect(
      container.querySelector('[data-pf-testid="base-select-all"]')
    ).toBeNull();

    const titleLink = container.querySelector<HTMLElement>(
      '[data-pf-testid="base-open-note"]'
    )!;
    const ev = new dom.window.MouseEvent("click", {
      bubbles: true,
      cancelable: true,
      ctrlKey: true,
    });
    titleLink.dispatchEvent(ev);
    expect(openLinkText).toHaveBeenCalledWith(
      snapshot.rows.K_DONE.main_note_path,
      "",
      "tab"
    );
  });

  it("supports keyboard row navigation (j/k/Space/p/s/Enter/Escape) and floating hover quick actions", () => {
    const container = dom.window.document.createElement("div");
    const openPaperSplitReading = vi.fn().mockResolvedValue(undefined);
    const localHost = {
      ...host,
      openPaperSplitReading,
    };
    const view = new PaperForgeBasesView({} as any, container, localHost);
    (view as any).data = {
      data: [
        {
          file: {
            basename: "K_DONE",
            path: snapshot.rows.K_DONE.main_note_path,
          },
          getValue: () => ({ data: "K_DONE" }),
        },
        {
          file: {
            basename: "K_WAIT",
            path: snapshot.rows.K_WAIT.main_note_path,
          },
          getValue: () => ({ data: "K_WAIT" }),
        },
      ],
    };
    view.render();

    // Floating quick actions: split button triggers openPaperSplitReading
    const splitBtn = container.querySelector<HTMLButtonElement>(
      '[data-pf-testid="base-row-split"]'
    );
    expect(splitBtn).not.toBeNull();
    splitBtn!.click();
    expect(openPaperSplitReading).toHaveBeenCalledWith(
      "K_DONE",
      snapshot.rows.K_DONE.main_note_path
    );

    const wrap = container.querySelector<HTMLElement>(".pf-base-table-wrap")!;
    wrap.dispatchEvent(
      new dom.window.KeyboardEvent("keydown", { key: "j", bubbles: true })
    );
    expect(
      container
        .querySelector('tr.pf-base-row[data-paper-key="K_DONE"]')
        ?.classList.contains("is-kb-active")
    ).toBe(true);

    // Space toggles checkbox selection
    wrap.dispatchEvent(
      new dom.window.KeyboardEvent("keydown", { key: " ", bubbles: true })
    );
    expect(
      container
        .querySelector('tr.pf-base-row[data-paper-key="K_DONE"]')
        ?.classList.contains("is-selected")
    ).toBe(true);

    // p opens PDF
    wrap.dispatchEvent(
      new dom.window.KeyboardEvent("keydown", { key: "p", bubbles: true })
    );
    expect(openPaperPdf).toHaveBeenCalledWith("K_DONE");

    // Escape clears keyboard active and selection
    wrap.dispatchEvent(
      new dom.window.KeyboardEvent("keydown", { key: "Escape", bubbles: true })
    );
    expect(
      container
        .querySelector('tr.pf-base-row[data-paper-key="K_DONE"]')
        ?.classList.contains("is-kb-active")
    ).toBe(false);
    expect(
      container
        .querySelector('tr.pf-base-row[data-paper-key="K_DONE"]')
        ?.classList.contains("is-selected")
    ).toBe(false);

    view.onunload();
  });

  it("supports viewport virtualization (> 500 papers) and inline frontmatter editing on custom note.* columns", async () => {
    const bigRows: Record<string, BaseTableSnapshotDto["rows"][string]> = {};
    for (let i = 0; i < 650; i += 1) {
      const k = `V_${String(i).padStart(4, "0")}`;
      bigRows[k] = {
        zotero_key: k,
        title: `Virtual Study #${i}`,
        first_author: `Auth ${i}`,
        year: "2025",
        journal: "Radiology",
        impact_factor: "9.1",
        domain: "Ortho",
        has_pdf: true,
        do_ocr: false,
        analyze: false,
        ocr_status: "done",
        deep_reading_status: "pending",
        main_note_path: `Literature/Ortho/${k}.md`,
        user_ann_count: 0,
        agent_ann_count: 0,
        memory_facet_count: 0,
        memory_updated_at: "",
        needs_diagnostic: false,
      };
    }
    snapshot = { seq: 120, updated_at: "2026-11-25T00:00:00Z", rows: bigRows };

    const updateNoteProperty = vi.fn(async () => undefined);
    const vHost = {
      ...host,
      updateNoteProperty,
    };

    const container = dom.window.document.createElement("div");
    const view = new PaperForgeBasesView({} as any, container, vHost);
    (view as any).config = {
      get: (k: string) => (k === "virtual_scroll" ? true : undefined),
      getOrder: () => ["note.title", "note.topic", "note.ocr_status"],
      getDisplayName: () => "",
    };
    (view as any).data = {
      data: Object.keys(bigRows).map((k) => ({
        file: { basename: k, path: bigRows[k].main_note_path },
        getValue: (propId: string) =>
          propId === "note.zotero_key"
            ? { data: k, toString: () => k }
            : propId === "note.topic"
              ? { data: "Old Topic", toString: () => "Old Topic" }
              : null,
      })),
    };
    view.render();

    // Virtual windowing mounts < 80 visible rows + bottom spacer
    const renderedRows = container.querySelectorAll("tr.pf-base-row");
    expect(renderedRows.length).toBeGreaterThan(0);
    expect(renderedRows.length).toBeLessThan(80);
    expect(container.querySelector(".pf-base-virtual-spacer")).not.toBeNull();

    // Double-click editable custom cell -> Enter persists frontmatter
    const editableTd = container.querySelector<HTMLElement>(
      "td.pf-base-cell-editable"
    )!;
    expect(editableTd).not.toBeNull();
    editableTd.dispatchEvent(
      new dom.window.MouseEvent("dblclick", { bubbles: true })
    );
    const input = editableTd.querySelector<HTMLInputElement>(
      '[data-pf-testid="base-inline-input"]'
    )!;
    expect(input).not.toBeNull();
    input.value = "Revised Priority";
    input.dispatchEvent(
      new dom.window.KeyboardEvent("keydown", { key: "Enter", bubbles: true })
    );
    expect(updateNoteProperty).toHaveBeenCalledWith(
      expect.objectContaining({ basename: "V_0000" }),
      "topic",
      "Revised Priority"
    );
    expect(editableTd.textContent).toContain("Revised Priority");

    view.onunload();
  });

  it("keeps global Sync Library out of row selection bar while retaining it in empty-library state", () => {
    const cSel = dom.window.document.createElement("div");
    const vSel = new PaperForgeBasesView({} as any, cSel, host);
    (vSel as any).data = {
      data: [
        {
          file: {
            basename: "K_DONE",
            path: snapshot.rows.K_DONE.main_note_path,
          },
          getValue: () => ({ data: "K_DONE" }),
        },
      ],
    };
    (vSel as any)._selectedKeys = new Set(["K_DONE"]);
    vSel.render();
    const selBar = cSel.querySelector('[data-pf-testid="base-selection-bar"]')!;
    expect(selBar).not.toBeNull();
    expect(
      selBar.querySelector('[data-pf-testid="base-sync-library"]')
    ).toBeNull();
    expect(
      selBar.querySelector('[data-pf-testid="base-run-selected-ocr"]')
    ).not.toBeNull();
    vSel.onunload();

    const cEmpty = dom.window.document.createElement("div");
    const vEmpty = new PaperForgeBasesView({} as any, cEmpty, host);
    (vEmpty as any).data = { data: [] };
    vEmpty.render();
    expect(
      cEmpty.querySelector('[data-pf-testid="base-sync-library"]')
    ).not.toBeNull();
    vEmpty.onunload();
  });
});
