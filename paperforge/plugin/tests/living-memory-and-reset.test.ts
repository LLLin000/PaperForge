/**
 * Interactive Living Paper Memory Card, MemoryFacetHistoryModal, and
 * VersionRestoreModal reset-live wiring tests.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import "obsidian-test-mocks/jest-setup";

vi.mock("obsidian", () => {
  class MockComponent {
    register() {}
    registerEvent() {}
    registerDomEvent() {}
    registerInterval() {
      return 0;
    }
    load() {}
    unload() {}
  }
  class MockView extends MockComponent {
    app: unknown;
    contentEl: HTMLElement;
    constructor(_leaf: unknown) {
      super();
      this.contentEl = document.createElement("div");
    }
  }
  return {
    ItemView: MockView,
    WorkspaceLeaf: class {},
    View: MockView,
    Component: MockComponent,
    Notice: class {
      noticeEl: HTMLElement;
      constructor(msg: string) {
        this.noticeEl = document.createElement("div");
        this.noticeEl.textContent = msg;
      }
    },
    Modal: class {
      app: unknown;
      contentEl: HTMLElement;
      constructor(app: unknown) {
        this.app = app;
        this.contentEl = document.createElement("div");
      }
      open() {
        document.body.append(this.contentEl);
        if (
          "onOpen" in this &&
          typeof (this as { onOpen?: () => void }).onOpen === "function"
        ) {
          (this as { onOpen: () => void }).onOpen();
        }
      }
      close() {
        this.contentEl.remove();
      }
    },
    MarkdownRenderer: { render: () => {} },
    App: class {},
    TFile: class {},
    Platform: { isMobile: false, isDesktop: true },
    Scope: class {},
  };
});

import { PaperForgeClient } from "../src/client/paperforge-client";
import type { Transport } from "../src/client/transport";
import { PaperForgeStatusView } from "../src/views/dashboard";
import { VersionRestoreModal } from "../src/views/ocr-workspace";

describe("Living Paper Memory interactive controls & versionsResetLive", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("wires versionsResetLive, refineMemoryCard, getMemoryCardHistory, and clearMemoryFacet with scoped invalidation", async () => {
    const calls: string[][] = [];
    let statusCalls = 0;
    const transport: Transport = {
      execute: vi.fn(async (argv: string[]) => {
        calls.push(argv);
        if (argv[0] === "paper-status") {
          statusCalls += 1;
          return JSON.stringify({ key: argv[1], seq: statusCalls });
        }
        if (argv[0] === "probe") {
          return JSON.stringify({
            ok: true,
            command: "probe",
            version: "1.0.0",
            data: {
              schema_version: 2,
              module: "library",
              capability_state: "ready",
              activity_state: "idle",
              user_state: "ready",
              severity: "ok",
            },
          });
        }
        if (argv[0] === "memory-card" && argv[1] === "refine") {
          return JSON.stringify({
            ok: true,
            command: "memory-card",
            version: "1.0.0",
            data: {
              paper_id: "K1",
              card: {
                paper_id: "K1",
                updated_at: "2026-11-19T00:00:00Z",
                facet_count: 1,
                facets: [
                  {
                    facet: "idea_logic",
                    label: "研究思路与逻辑链",
                    content: "Refined claim",
                    revision: 2,
                    updated_at: "2026-11-19T00:00:00Z",
                  },
                ],
              },
            },
          });
        }
        if (argv[0] === "memory-card" && argv[1] === "history") {
          return JSON.stringify({
            ok: true,
            command: "memory-card",
            version: "1.0.0",
            data: {
              paper_id: "K1",
              facet: "idea_logic",
              history: [
                {
                  facet: "idea_logic",
                  label: "研究思路与逻辑链",
                  content: "Previous claim",
                  revision: 1,
                  created_at: "2026-11-18T12:00:00Z",
                },
              ],
            },
          });
        }
        if (argv[0] === "memory-card" && argv[1] === "clear") {
          return JSON.stringify({
            ok: true,
            command: "memory-card",
            version: "1.0.0",
            data: { paper_id: "K1", facet: "idea_logic", removed: 1 },
          });
        }
        if (argv[0] === "versions" && argv[1] === "reset-live") {
          return JSON.stringify({
            ok: true,
            command: "versions",
            version: "1.0.0",
            data: {
              intent: "versions-reset-live",
              key: "K1",
              source_path: "/tmp/fulltext.md",
              target_path: "/tmp/display.md",
              provenance_cleared: true,
            },
          });
        }
        throw new Error(`Unexpected argv: ${argv.join(" ")}`);
      }),
      stream: vi.fn() as unknown as Transport["stream"],
    };

    const client = new PaperForgeClient({ transport });
    await client.probe("library");
    await client.paperStatus("K1");

    const updated = await client.refineMemoryCard(
      "K1",
      "idea_logic",
      "Refined claim"
    );
    expect(updated.facets[0].content).toBe("Refined claim");

    // Probe stays cached; paperStatus for K1 was invalidated by refineMemoryCard
    await client.probe("library");
    const status2 = await client.paperStatus("K1");
    expect(status2).toEqual({ key: "K1", seq: 2 });

    const history = await client.getMemoryCardHistory("K1", "idea_logic");
    expect(history).toHaveLength(1);
    expect(history[0].content).toBe("Previous claim");

    const cleared = await client.clearMemoryFacet("K1", "idea_logic");
    expect(cleared.removed).toBe(1);

    const reset = await client.versionsResetLive("K1");
    expect(reset.provenance_cleared).toBe(true);
    expect(calls[calls.length - 1]).toEqual([
      "versions",
      "reset-live",
      "--key",
      "K1",
      "--json",
    ]);
  });

  it("supports inline editing, creating on empty cards, and clearing facets in dashboard", async () => {
    let cardState = {
      paper_id: "PAPER001",
      updated_at: "2026-11-19T00:00:00Z",
      facet_count: 0,
      facets: [] as Array<{
        facet: string;
        label: string;
        content: string;
        revision: number;
        updated_at: string;
      }>,
    };

    const mockClient = {
      getMemoryCard: vi.fn(async () => cardState),
      refineMemoryCard: vi.fn(
        async (_key: string, facet: string, content: string) => {
          cardState = {
            paper_id: "PAPER001",
            updated_at: "2026-11-19T01:00:00Z",
            facet_count: 1,
            facets: [
              {
                facet,
                label: "研究思路与逻辑链",
                content,
                revision: 1,
                updated_at: "2026-11-19T01:00:00Z",
              },
            ],
          };
          return cardState;
        }
      ),
      getMemoryCardHistory: vi.fn(async () => []),
      clearMemoryFacet: vi.fn(async () => {
        cardState = {
          paper_id: "PAPER001",
          updated_at: "2026-11-19T02:00:00Z",
          facet_count: 0,
          facets: [],
        };
        return { paper_id: "PAPER001", facet: "idea_logic", removed: 1 };
      }),
    };

    const view = new PaperForgeStatusView({} as never);
    Object.assign(view, {
      app: {
        plugins: { plugins: { paperforge: { getClient: () => mockClient } } },
      },
    });
    view._contentEl = document.createElement("div");
    document.body.append(view._contentEl);
    view._currentPaperKey = "PAPER001";
    view._currentPaperEntry = { title: "Interactive Memory Test" };
    view._renderPaperMode();

    await vi.waitFor(() =>
      expect(
        view._contentEl.querySelector(
          '[data-pf-testid="memory-facet-add-idea_logic"]'
        )
      ).not.toBeNull()
    );

    const addBtn = view._contentEl.querySelector<HTMLButtonElement>(
      '[data-pf-testid="memory-facet-add-idea_logic"]'
    )!;
    addBtn.click();

    const editor = view._contentEl.querySelector<HTMLTextAreaElement>(
      '[data-pf-testid="memory-facet-editor-idea_logic"]'
    )!;
    editor.value = "First structured takeaway";
    view._contentEl
      .querySelector<HTMLButtonElement>('[data-pf-testid="memory-facet-save"]')!
      .click();

    await vi.waitFor(() =>
      expect(view._contentEl.textContent).toContain("First structured takeaway")
    );
    expect(mockClient.refineMemoryCard).toHaveBeenCalledWith(
      "PAPER001",
      "idea_logic",
      "First structured takeaway"
    );

    // Inline edit existing facet
    view._contentEl
      .querySelector<HTMLButtonElement>(
        '[data-pf-testid="memory-facet-edit-idea_logic"]'
      )!
      .click();
    const editBox = view._contentEl.querySelector<HTMLTextAreaElement>(
      '[data-pf-testid="memory-facet-editor-idea_logic"]'
    )!;
    editBox.value = "Edited takeaway";
    view._contentEl
      .querySelector<HTMLButtonElement>('[data-pf-testid="memory-facet-save"]')!
      .click();

    await vi.waitFor(() =>
      expect(view._contentEl.textContent).toContain("Edited takeaway")
    );

    // Clear facet
    view._contentEl
      .querySelector<HTMLButtonElement>(
        '[data-pf-testid="memory-facet-clear-idea_logic"]'
      )!
      .click();
    await vi.waitFor(() => {
      expect(mockClient.clearMemoryFacet).toHaveBeenCalledWith(
        "PAPER001",
        "idea_logic"
      );
      expect(
        view._contentEl.querySelector(".pf-living-memory-empty")
      ).not.toBeNull();
    });
  });

  it("renders VersionRestoreModal reset-live button and invokes callback", async () => {
    const resetLive = vi.fn(async () => ({
      intent: "versions-reset-live",
      key: "PAPER001",
      source_path: "",
      target_path: "",
      provenance_cleared: true,
    }));
    const onRestored = vi.fn();

    const modal = new VersionRestoreModal(
      {} as never,
      "PAPER001",
      [
        {
          label: "v1",
          created_at: "2026-11-18T00:00:00Z",
          source: "pre-rebuild",
          fulltext_size: 120,
        },
      ],
      "v1",
      "",
      async () => ({
        target_path: "",
        label: "v1",
        provenance_persisted: true,
      }),
      onRestored,
      resetLive
    );
    modal.open();

    const resetBtn = modal.contentEl.querySelector<HTMLButtonElement>(
      '[data-pf-testid="version-reset-live"]'
    );
    expect(resetBtn).not.toBeNull();
    resetBtn!.click();

    await vi.waitFor(() => {
      expect(resetLive).toHaveBeenCalledTimes(1);
      expect(onRestored).toHaveBeenCalledTimes(1);
    });
  });
});
