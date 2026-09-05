/**
 * Library & Render Quality Domain Cutover Integration Tests (Ticket 06).
 *
 * Verifies that:
 * 1. Manual Library sync routes through client.sync() (never execFile/spawn).
 * 2. Library overview facts (paper count, orphan count) come from probe
 *    envelopes, not client-side database scans.
 * 3. Render Quality drawer fetches consistency findings via client.renderAudit(key).
 * 4. R/P staging goes through client.renderReconcileStaging(key).
 * 5. R promotion reaches `render promote-r` with the exact object ID.
 * 6. P acceptance forwards the exact SHA-256 plan hash.
 * 7. Every surface fails closed without the shared client.
 */

import "obsidian-test-mocks/jest-setup";
import { describe, it, expect, beforeEach, beforeAll, vi } from "vitest";
import { MockTransport } from "./mock-transport";
import { PaperForgeClient } from "../../src/client/paperforge-client";
import { PaperForgeStatusView } from "../../src/views/dashboard";
import { PaperForgeSettingTab } from "../../src/settings";
import type { ActionPrimary } from "../../src/constants";

const { mockExecFile, mockSpawn } = vi.hoisted(() => ({
  mockExecFile: vi.fn(),
  mockSpawn: vi.fn(),
}));

vi.mock("child_process", () => ({
  execFile: mockExecFile,
  spawn: mockSpawn,
  default: { execFile: mockExecFile, spawn: mockSpawn },
}));

beforeAll(() => {
  const win = globalThis.document?.defaultView;
  const proto = win?.HTMLElement?.prototype;
  if (!proto) return;
  const polyfill = <T>(key: string, fn: T) => {
    if (!(key in proto)) proto[key] = fn;
  };
  polyfill("empty", function (this: HTMLElement) {
    this.innerHTML = "";
  });
  polyfill("appendText", function (this: HTMLElement, text: string) {
    this.appendChild(this.ownerDocument.createTextNode(text));
  });
  polyfill(
    "createDiv",
    function (this: HTMLElement, opts?: Record<string, unknown>) {
      const el = document.createElement("div");
      if (opts?.cls) el.className = String(opts.cls);
      if (opts?.text) el.textContent = String(opts.text);
      this.appendChild(el);
      return el;
    }
  );
  polyfill(
    "createEl",
    function (this: HTMLElement, tag: string, opts?: Record<string, unknown>) {
      const el = document.createElement(tag);
      if (opts?.cls) el.className = String(opts.cls);
      if (opts?.text) el.textContent = String(opts.text);
      this.appendChild(el);
      return el;
    }
  );
  polyfill("setText", function (this: HTMLElement, text: string) {
    this.textContent = text;
  });
});

const PLAN_HASH = "a".repeat(64);

function syncPrimary(): ActionPrimary {
  return {
    verb: "sync",
    action_id: "library.sync",
    label: "Sync library",
    availability: "available",
    safety_class: "safe",
    preservation_facts: [],
    replacement_facts: [],
    interruptible: true,
    confirmation_required: false,
    confirmation_prompt: null,
    scope: "module",
    scope_count: 1,
  } satisfies ActionPrimary;
}

describe("Library & Render Quality Domain Cutover (Ticket 06)", () => {
  let transport: MockTransport;
  let client: PaperForgeClient;

  beforeEach(() => {
    transport = new MockTransport();
    client = new PaperForgeClient({ transport });
    mockExecFile.mockClear();
    mockSpawn.mockClear();
  });

  describe("Library Cutover", () => {
    function makeSettingTab(clientInstance: PaperForgeClient | null) {
      const app = {
        vault: { adapter: { basePath: "/vault" } },
      };
      const plugin = {
        getClient: () => clientInstance,
        settings: {},
        _embedProgress: null,
      };
      const tab = new (PaperForgeSettingTab as unknown as new (
        ...a: unknown[]
      ) => Record<string, (...args: unknown[]) => unknown> & {
        _capabilityState: Record<string, Record<string, unknown>>;
        _refreshAllReadModels: (code?: number) => void;
        _refreshSnapshots: (vp: string) => void;
        _resolveRuntimeCommand: (vp: string) => unknown;
        _lastSyncTime: string | null;
      })(app, plugin);
      tab.containerEl = document.createElement("div");
      tab._capabilityState = {
        library: {
          schema_version: 2,
          module: "library",
          capability_state: "ready",
          activity_state: "idle",
          user_state: "ready",
          severity: "ok",
          reason: {
            code: "library.ready",
            text: "Library synced and index is fresh (42 papers)",
          },
          action: { primary: null },
          updated_at: new Date().toISOString(),
          ttl_seconds: 60,
        },
        maintenance: {
          orphan: { count: 3, orphans: [] },
        },
      };
      tab.display = vi.fn();
      tab._refreshAllReadModels = vi.fn();
      tab._refreshSnapshots = vi.fn();
      tab._resolveRuntimeCommand = vi.fn(() => null);
      return tab;
    }

    it("manual library sync routes through client.sync with the exact argv and no child process", async () => {
      transport.executeHandler = (argv) => {
        if (argv[0] === "sync") {
          return JSON.stringify({
            ok: true,
            data: { papers_synced: 5 },
            next_actions: [],
          });
        }
        if (argv[0] === "reconcile") {
          return JSON.stringify({ deficits: [] });
        }
        return "{}";
      };
      const tab = makeSettingTab(client);
      tab._runAllowedDispatch(
        "library",
        syncPrimary(),
        tab._capabilityState.library
      );

      await vi.waitFor(() => {
        expect(transport.calls.some((c) => c.argv[0] === "sync")).toBe(true);
      });
      const syncCall = transport.calls.find((c) => c.argv[0] === "sync");
      expect(syncCall?.argv).toEqual(["sync", "--json"]);
      await vi.waitFor(() => {
        expect(tab._refreshAllReadModels).toHaveBeenCalledWith(0);
      });
      expect(mockExecFile).not.toHaveBeenCalled();
      expect(mockSpawn).not.toHaveBeenCalled();
    });

    it("library detail facts render probe-owned paper count and orphan count", () => {
      const tab = makeSettingTab(client);
      (tab._capabilityState.library as Record<string, unknown>)["details"] = {
        paper_count: 42,
      };
      const el = document.createElement("div");
      tab._renderLibraryDetail(el);
      const facts = el.querySelectorAll(".pf-module-fact");
      const corpusRow = Array.from(facts).find((f) =>
        f.textContent?.includes("Literature corpus")
      );
      expect(corpusRow?.textContent).toContain("42");
      const orphanRow = Array.from(facts).find((f) =>
        f.textContent?.includes("Orphans")
      );
      expect(orphanRow?.textContent).toContain("3");
    });

    it("library detail facts show not-available when the probe carries no counts", () => {
      const tab = makeSettingTab(client);
      const el = document.createElement("div");
      tab._renderLibraryDetail(el);
      const facts = el.querySelectorAll(".pf-module-fact");
      const corpusRow = Array.from(facts).find((f) =>
        f.textContent?.includes("Literature corpus")
      );
      expect(corpusRow?.textContent).not.toContain("42");
    });

    it("forwards exit code 1 into the read model when sync reports failure", async () => {
      transport.executeHandler = (argv) => {
        if (argv[0] === "sync") {
          return JSON.stringify({ ok: false, error: { code: "SYNC_FAILED" } });
        }
        if (argv[0] === "reconcile") {
          return JSON.stringify({ deficits: [] });
        }
        return "{}";
      };
      const tab = makeSettingTab(client);
      tab._runAllowedDispatch(
        "library",
        syncPrimary(),
        tab._capabilityState.library
      );

      await vi.waitFor(() => {
        expect(tab._refreshAllReadModels).toHaveBeenCalledWith(1);
      });
    });

    // #06 corrective A: EVERY manual sync CTA (Dashboard global/collection/
    // per-paper and Settings) must reach client.sync — never _runAction/spawn.
    describe("Dashboard sync CTAs", () => {
      function makeDashboardForSync() {
        const leaf = {};
        const view = new (PaperForgeStatusView as unknown as new (
          ...a: unknown[]
        ) => Record<string, unknown>)(leaf) as Record<
          string,
          (...args: unknown[]) => unknown
        > & {
          _contentEl: HTMLElement | null;
          _currentDomain: string;
        };
        view.app = {
          vault: { adapter: { basePath: "/vault" } },
          plugins: {
            plugins: {
              paperforge: {
                getClient: () => client,
              },
            },
          },
        };
        view._fetchStats = vi.fn();
        return view;
      }

      const syncHandler = (argv: string[]) => {
        if (argv[0] === "sync") {
          return JSON.stringify({ ok: true, data: { papers_synced: 1 } });
        }
        if (argv[0] === "reconcile") {
          return JSON.stringify({ deficits: [] });
        }
        return "{}";
      };

      async function expectOnlyClientSync(click: () => void) {
        transport.executeHandler = syncHandler;
        click();
        await vi.waitFor(() => {
          expect(transport.calls.some((c) => c.argv[0] === "sync")).toBe(true);
        });
        const nonSync = transport.calls.filter((c) => c.argv[0] !== "sync");
        expect(
          nonSync.every(
            (c) => c.argv[0] === "reconcile" || c.argv[0] === "probe"
          )
        ).toBe(true);
        expect(
          transport.calls.filter((c) => c.argv[0] === "sync").map((c) => c.argv)
        ).toEqual([["sync", "--json"]]);
        // The sync ACTION must never spawn or execFile. (Render-time reads
        // such as the global-mode `auth status ocr` row are unrelated legacy
        // surfaces owned by Ticket 07 — they are not part of the sync path.)
        const childProcArgv = [
          ...mockSpawn.mock.calls,
          ...mockExecFile.mock.calls,
        ].map((c) => JSON.stringify(c[1] ?? []));
        for (const a of childProcArgv) {
          expect(a).not.toContain('"sync"');
        }
      }

      it("global Sync Library button routes through _runLibrarySync", async () => {
        const view = makeDashboardForSync();
        view._contentEl = document.createElement("div");
        view._getCachedIndex = () => [];
        view._loadIndex = () => null;
        view._renderGlobalMode();
        const btn = Array.from(view._contentEl.querySelectorAll("button")).find(
          (b) => b.textContent?.includes("Sync Library")
        );
        expect(btn).toBeDefined();
        await expectOnlyClientSync(() => btn?.click());
      });

      it("collection Sync Library button routes through _runLibrarySync", async () => {
        const view = makeDashboardForSync();
        view._contentEl = document.createElement("div");
        view._currentDomain = "All";
        view._filterByDomain = () => [
          { key: "A", title: "A", has_pdf: true, ocr_status: "done" },
        ];
        view._renderCollectionMode();
        const btn = Array.from(view._contentEl.querySelectorAll("button")).find(
          (b) => b.textContent?.includes("Sync Library")
        );
        expect(btn).toBeDefined();
        await expectOnlyClientSync(() => btn?.click());
      });

      it("per-paper next-step Sync CTA routes through _runLibrarySync", async () => {
        const view = makeDashboardForSync();
        const card = document.createElement("div");
        view._renderNextStepCard(card, { next_step: "sync" }, "ABCD1234");
        const trigger = card.querySelector(
          ".paperforge-next-step-trigger"
        ) as HTMLButtonElement | null;
        expect(trigger?.textContent).toContain("Sync Needed");
        await expectOnlyClientSync(() => trigger?.click());
      });
    });
  });

  describe("Render Quality Cutover", () => {
    const KEY = "ABCD1234";

    function makeDashboard(clientInstance: PaperForgeClient | null) {
      const leaf = {};
      const view = new (PaperForgeStatusView as unknown as new (
        ...a: unknown[]
      ) => Record<string, unknown>)(leaf) as Record<
        string,
        (...args: unknown[]) => unknown
      > & {
        _currentPaperKey: string | null;
        _qualityStagingCache: {
          key: string;
          data: Record<string, unknown>;
        } | null;
      };
      view.app = {
        vault: { adapter: { basePath: "/vault" } },
        plugins: {
          plugins: {
            paperforge: {
              getClient: () => clientInstance,
            },
          },
        },
      };
      view._currentPaperKey = KEY;
      return view;
    }

    const auditResponse = () =>
      JSON.stringify({
        state: "DEGRADED",
        papers: [
          {
            paper_key: KEY,
            state: "DEGRADED",
            issues: [
              {
                code: "figure_missing_render",
                message: "figure_002 has no rendered JPG",
              },
            ],
          },
        ],
      });

    const stagingResponse = () =>
      JSON.stringify({
        summary: { production_write: false },
        papers: [
          {
            paper_key: KEY,
            r_details: [
              {
                object_id: "figure_002",
                staged: true,
                image: "x.jpg",
                markdown: "x.md",
              },
            ],
            p_details: [
              {
                label: "1",
                page: 3,
                staged: true,
                preview: "p.jpg",
                final_plan_hash: PLAN_HASH,
                decision: "high",
                caption_text: "Figure 1: Overall architecture",
                member_refs: [
                  { page: 3, block_id: "p3:b2", bbox: [10, 20, 300, 400] },
                ],
              },
            ],
          },
        ],
      });

    it("drawer fetches consistency findings via client.renderAudit with the exact argv", async () => {
      transport.executeHandler = () => auditResponse();
      const view = makeDashboard(client);
      const body = document.createElement("div");
      await view._loadQualitySection(body, KEY);

      const auditCall = transport.calls.find(
        (c) => c.argv[0] === "render" && c.argv[1] === "audit"
      );
      expect(auditCall?.argv).toEqual(["render", "audit", KEY, "--json"]);
      expect(body.textContent).toContain("Render consistency: DEGRADED");
      expect(body.textContent).toContain("figure_002 has no rendered JPG");
      expect(mockSpawn).not.toHaveBeenCalled();
      expect(mockExecFile).not.toHaveBeenCalled();
    });

    it("staging goes through client.renderReconcileStaging and renders R/P candidates with the plan hash", async () => {
      transport.executeHandler = (argv) => {
        if (argv[0] === "render" && argv[1] === "audit") return auditResponse();
        if (argv[0] === "render" && argv[1] === "reconcile")
          return stagingResponse();
        return "{}";
      };
      const view = makeDashboard(client);
      const body = document.createElement("div");
      await view._loadQualitySection(body, KEY);

      const stagingEl = body.querySelector(".paperforge-quality-staging");
      expect(stagingEl).not.toBeNull();
      const stageBtn = stagingEl?.querySelector("button");
      expect(stageBtn?.textContent).toBe("Stage R/P proposals");
      stageBtn?.click();

      await vi.waitFor(() => {
        expect(
          transport.calls.some(
            (c) => c.argv[0] === "render" && c.argv[1] === "reconcile"
          )
        ).toBe(true);
      });
      expect(
        transport.calls.find(
          (c) => c.argv[0] === "render" && c.argv[1] === "reconcile"
        )?.argv
      ).toEqual(["render", "reconcile", KEY, "--json"]);
      await vi.waitFor(() => {
        expect(stagingEl?.textContent).toContain("R exact repairs");
      });
      expect(stagingEl?.textContent).toContain("figure_002");
      expect(stagingEl?.textContent).toContain("a".repeat(12));
    });

    it("R promotion reaches render promote-r with the exact object ID and invalidates the staging snapshot", async () => {
      transport.executeHandler = (argv) => {
        if (argv[0] === "render" && argv[1] === "audit") return auditResponse();
        if (argv[0] === "render" && argv[1] === "reconcile")
          return stagingResponse();
        if (argv[0] === "render" && argv[1] === "promote-r") {
          return JSON.stringify({ ok: true, data: { promoted: 1 } });
        }
        return "{}";
      };
      const view = makeDashboard(client);
      const body = document.createElement("div");
      await view._loadQualitySection(body, KEY);
      const stagingEl = body.querySelector(".paperforge-quality-staging");
      stagingEl?.querySelector("button")?.click();
      await vi.waitFor(() => {
        expect(stagingEl?.textContent).toContain("Promote");
      });
      const promoteBtn = Array.from(
        stagingEl?.querySelectorAll("button") ?? []
      ).find((b) => b.textContent === "Promote");
      expect(promoteBtn).toBeDefined();
      promoteBtn?.click();

      await vi.waitFor(() => {
        expect(
          transport.calls.some(
            (c) => c.argv[0] === "render" && c.argv[1] === "promote-r"
          )
        ).toBe(true);
      });
      expect(
        transport.calls.find(
          (c) => c.argv[0] === "render" && c.argv[1] === "promote-r"
        )?.argv
      ).toEqual(["render", "promote-r", KEY, "figure_002", "--json"]);
      // Committed mutation → the staging snapshot must be invalidated so the
      // next render re-stages instead of replaying the stale cache.
      await vi.waitFor(() => {
        expect(view._qualityStagingCache).toBeNull();
      });
    });

    it("P acceptance forwards the exact reviewed SHA-256 plan hash", async () => {
      transport.executeHandler = (argv) => {
        if (argv[0] === "render" && argv[1] === "audit") return auditResponse();
        if (argv[0] === "render" && argv[1] === "reconcile")
          return stagingResponse();
        if (argv[0] === "render" && argv[1] === "accept-proposal") {
          return JSON.stringify({
            ok: true,
            data: { accepted: "figure_proposal_1" },
          });
        }
        return "{}";
      };
      const view = makeDashboard(client);
      const body = document.createElement("div");
      await view._loadQualitySection(body, KEY);
      const stagingEl = body.querySelector(".paperforge-quality-staging");
      stagingEl?.querySelector("button")?.click();
      await vi.waitFor(() => {
        expect(stagingEl?.textContent).toContain("Accept");
      });
      const acceptBtn = Array.from(
        stagingEl?.querySelectorAll("button") ?? []
      ).find((b) => b.textContent === "Accept");
      expect(acceptBtn).toBeDefined();
      acceptBtn?.click();

      await vi.waitFor(() => {
        expect(
          transport.calls.some(
            (c) => c.argv[0] === "render" && c.argv[1] === "accept-proposal"
          )
        ).toBe(true);
      });
      expect(
        transport.calls.find(
          (c) => c.argv[0] === "render" && c.argv[1] === "accept-proposal"
        )?.argv
      ).toEqual([
        "render",
        "accept-proposal",
        KEY,
        "1",
        "--plan-hash",
        PLAN_HASH,
        "--json",
      ]);
    });

    it("fails closed with backend-unavailable and zero transport calls when the client is missing", async () => {
      const view = makeDashboard(null);
      const body = document.createElement("div");
      await view._loadQualitySection(body, KEY);
      expect(body.textContent).toContain("Backend unavailable");
      expect(transport.calls).toHaveLength(0);
      expect(mockSpawn).not.toHaveBeenCalled();
      expect(mockExecFile).not.toHaveBeenCalled();
    });

    it("P evidence card renders caption, member blocks, preview, and decision from the staging DTO", async () => {
      transport.executeHandler = (argv) => {
        if (argv[0] === "render" && argv[1] === "audit") return auditResponse();
        if (argv[0] === "render" && argv[1] === "reconcile")
          return stagingResponse();
        return "{}";
      };
      const view = makeDashboard(client);
      const body = document.createElement("div");
      await view._loadQualitySection(body, KEY);
      body.querySelector(".paperforge-quality-staging button")?.click();
      await vi.waitFor(() => {
        expect(body.textContent).toContain("Figure 1");
      });
      expect(body.textContent).toContain("decision: high");
      expect(body.textContent).toContain("Figure 1: Overall architecture");
      expect(body.textContent).toContain("block p3:b2");
      expect(body.textContent).toContain("preview: p.jpg");
      expect(body.textContent).toContain("x.jpg"); // R staged preview
    });

    it("committed R/P mutation refreshes the whole quality view (renderAudit re-run)", async () => {
      transport.executeHandler = (argv) => {
        if (argv[0] === "render" && argv[1] === "audit") return auditResponse();
        if (argv[0] === "render" && argv[1] === "reconcile")
          return stagingResponse();
        if (argv[0] === "render" && argv[1] === "promote-r") {
          return JSON.stringify({ ok: true, data: { promoted: 1 } });
        }
        return "{}";
      };
      const view = makeDashboard(client);
      const body = document.createElement("div");
      await view._loadQualitySection(body, KEY);
      const auditsBefore = transport.calls.filter(
        (c) => c.argv[0] === "render" && c.argv[1] === "audit"
      ).length;
      const stagingEl = body.querySelector(".paperforge-quality-staging");
      stagingEl?.querySelector("button")?.click();
      await vi.waitFor(() => {
        expect(stagingEl?.textContent).toContain("Promote");
      });
      const promoteBtn = Array.from(
        stagingEl?.querySelectorAll("button") ?? []
      ).find((b) => b.textContent === "Promote");
      promoteBtn?.click();

      await vi.waitFor(() => {
        const auditsAfter = transport.calls.filter(
          (c) => c.argv[0] === "render" && c.argv[1] === "audit"
        ).length;
        expect(auditsAfter).toBeGreaterThan(auditsBefore);
      });
      // The audit section itself must be re-rendered, not just the staging block.
      await vi.waitFor(() => {
        expect(body.textContent?.includes("Render consistency: DEGRADED")).toBe(
          true
        );
      });
    });

    it("structured authority rejection (rc=1 + stdout JSON) survives as a normal result and forces re-stage", async () => {
      transport.executeHandler = (argv) => {
        if (argv[0] === "render" && argv[1] === "audit") return auditResponse();
        if (argv[0] === "render" && argv[1] === "reconcile")
          return stagingResponse();
        if (argv[0] === "render" && argv[1] === "accept-proposal") {
          const err = new Error("exit code 1");
          (err as unknown as { stdout: string }).stdout = JSON.stringify({
            ok: false,
            reason: "STALE_PROPOSAL",
            staged_snapshot: "abc",
            live_snapshot: "def",
          });
          throw err;
        }
        return "{}";
      };
      const view = makeDashboard(client);
      const body = document.createElement("div");
      await view._loadQualitySection(body, KEY);
      const stagingEl = body.querySelector(".paperforge-quality-staging");
      stagingEl?.querySelector("button")?.click();
      await vi.waitFor(() => {
        expect(stagingEl?.textContent).toContain("Accept");
      });
      const acceptBtn = Array.from(
        stagingEl?.querySelectorAll("button") ?? []
      ).find((b) => b.textContent === "Accept");
      acceptBtn?.click();

      // Structured rejection preserved → staging invalidated → user must
      // re-stage and re-review (no stale Accept card remains).
      await vi.waitFor(() => {
        expect(view._qualityStagingCache).toBeNull();
      });
      // The full quality section re-renders → re-query the fresh staging block.
      const freshStaging = body.querySelector(".paperforge-quality-staging");
      await vi.waitFor(() => {
        expect(freshStaging?.textContent).toContain("Stage R/P proposals");
      });
      expect(freshStaging?.textContent).not.toContain("Accept");
    });
  });
});
