/**
 * Mixed-state stress tests for plugin NDJSON streaming, OperationLock,
 * runLongTask callback isolation, and mixed item_result classification.
 */

import "obsidian-test-mocks/jest-setup";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { EventEmitter } from "events";
import { NdjsonStreamParser, runLongTask } from "../src/client/node-transport";
import { PaperForgeClient } from "../src/client/paperforge-client";
import { MockTransport } from "./client/mock-transport";
import type { NdjsonEvent } from "../src/client/transport";

const { notices } = vi.hoisted(() => ({
  notices: { list: [] as string[] },
}));

vi.mock("obsidian", () => ({
  Plugin: class {},
  PluginSettingTab: class {},
  Notice: class {
    constructor(msg: string) {
      notices.list.push(msg);
    }
  },
  Modal: class {
    open() {}
  },
  Setting: class {},
  addIcon: () => {},
  ItemView: class {},
  TFile: class {},
  TFolder: class {},
  MarkdownView: class {},
  Platform: { isMobile: false, isDesktopApp: true },
  requestUrl: () => ({}),
  normalizePath: (p: string) => p,
  debounce: (fn: unknown) => fn,
  FileSystemAdapter: class {},
}));

function make16PaperMixedOcrEvents(): NdjsonEvent[] {
  const events: NdjsonEvent[] = [
    { schema_version: 1, event: "start", operation: "ocr.run", total: 16 },
    { schema_version: 1, event: "phase", operation: "ocr.run", phase: "ocr" },
  ];
  const statuses = [
    "done",
    "done_degraded",
    "done",
    "nopdf",
    "blocked",
    "done",
    "error",
    "fatal_error",
    "done",
    "done",
    "blocked",
    "error",
    "done_degraded",
    "done",
    "ok",
    "done",
  ];
  statuses.forEach((st, idx) => {
    const key = `P${String(idx + 1).padStart(2, "0")}`;
    events.push({
      schema_version: 1,
      event: "progress",
      operation: "ocr.run",
      current: idx + 1,
      total: 16,
      item_id: key,
    });
    if (idx % 4 === 3) {
      events.push({
        schema_version: 1,
        event: "heartbeat",
        operation: "ocr.run",
        active: Math.max(0, 16 - idx - 1),
      });
    }
    events.push({
      schema_version: 1,
      event: "item_result",
      operation: "ocr.run",
      item_id: key,
      status: st,
    });
  });
  events.push({
    schema_version: 1,
    event: "error",
    operation: "ocr.run",
    result: {
      ok: false,
      error: {
        code: "OCR_RESULT_INVALID",
        message: "Mixed batch finished with partial failures",
      },
      data: {
        failed_keys: ["P07", "P08", "P12"],
        blocked_keys: ["P05", "P11"],
      },
    },
  });
  return events;
}

describe("Plugin streaming stress loops", () => {
  beforeEach(() => {
    notices.list.length = 0;
  });

  it("parses 16-paper mixed-state OCR NDJSON storm split across arbitrary chunks", () => {
    const parser = new NdjsonStreamParser();
    const rawStream = make16PaperMixedOcrEvents()
      .map((e) => JSON.stringify(e) + "\n")
      .join("");

    // Slice stream into adversarial tiny pieces (including inside JSON keys/UTF-8 text)
    const parsed: NdjsonEvent[] = [];
    for (let i = 0; i < rawStream.length; i += 17) {
      parsed.push(...parser.feed(rawStream.slice(i, i + 17)));
    }
    parser.finishEOF();

    expect(parser.protocolFailure).toBeUndefined();
    expect(parser.terminalSeen).toBe(true);
    expect(parsed.filter((e) => e.event === "item_result")).toHaveLength(16);
    expect(parsed[parsed.length - 1].event).toBe("error");
  });

  it("isolates throwing onEvent listener in runLongTask so terminal and remaining events survive", async () => {
    const events = make16PaperMixedOcrEvents();
    const ndjsonPayload = events.map((e) => JSON.stringify(e) + "\n").join("");

    const child = new EventEmitter() as any;
    child.pid = 424242;
    child.exitCode = null;
    child.signalCode = null;
    child.stdin = { write: vi.fn(), end: vi.fn() };
    child.stdout = new EventEmitter();
    child.stdout.setEncoding = vi.fn();
    child.stderr = new EventEmitter();
    child.stderr.setEncoding = vi.fn();
    child.kill = vi.fn();

    const seenItems: string[] = [];
    const handle = runLongTask(
      "python",
      [],
      "/vault",
      ["action", "run", "ocr.run"],
      {
        spawnFn: (() => child) as any,
        onEvent: (ev) => {
          if (ev.event === "item_result") {
            seenItems.push(String(ev.item_id));
            if (ev.item_id === "P05") {
              throw new Error("Simulated transient UI render throw");
            }
          }
        },
      }
    );

    // Deliver entire mixed-state payload across split chunks then close rc=1
    const mid = Math.floor(ndjsonPayload.length / 2);
    child.stdout.emit("data", ndjsonPayload.slice(0, mid));
    child.stdout.emit("data", ndjsonPayload.slice(mid));
    child.exitCode = 1;
    child.emit("close", 1);

    const outcome = await handle.promise;
    expect(outcome.protocolFailure).toBeUndefined();
    expect(outcome.exitCode).toBe(1);
    expect(seenItems).toHaveLength(16);
    expect(seenItems[15]).toBe("P16");
    expect(outcome.events[outcome.events.length - 1].event).toBe("error");
  });

  it("enforces OperationLock during 16-paper stream and unlocks for subsequent embed.build", async () => {
    const transport = new MockTransport();
    transport.executeHandler = async (argv) => {
      if (argv.includes("describe") && argv.includes("ocr.run")) {
        return JSON.stringify({
          ok: true,
          data: {
            action_id: "ocr.run",
            availability: "available",
            execution_mode: "stream",
          },
        });
      }
      if (argv.includes("describe") && argv.includes("embed.build")) {
        return JSON.stringify({
          ok: true,
          data: {
            action_id: "embed.build",
            availability: "available",
            execution_mode: "stream",
          },
        });
      }
      return JSON.stringify({ ok: true, data: {} });
    };

    const mixedEvents = make16PaperMixedOcrEvents();
    transport.streamHandler = async (argv) => {
      if (argv.includes("ocr.run")) {
        return {
          delayMs: 25,
          events: mixedEvents,
          outcome: { ok: false, exitCode: 1 },
        };
      }
      return {
        events: [
          {
            schema_version: 1,
            event: "start",
            operation: "embed.build",
            total: 2,
          },
          {
            schema_version: 1,
            event: "item_result",
            operation: "embed.build",
            item_id: "P01",
            status: "succeeded",
          },
          {
            schema_version: 1,
            event: "result",
            operation: "embed.build",
            result: { ok: true, data: {} },
          },
        ],
        outcome: { ok: true, exitCode: 0 },
      };
    };

    const client = new PaperForgeClient({ transport });
    const received: string[] = [];
    const ocrPromise = client.runAction(
      { action_id: "ocr.run", scope: { kind: "all" }, confirm: "ocr.run" },
      {
        onEvent: (ev) => {
          if (ev.event === "item_result")
            received.push(`${ev.item_id}:${ev.status}`);
        },
      }
    );

    // Wait briefly so describeAction settles and stream starts, then assert contention rejection
    await new Promise((r) => setTimeout(r, 10));
    expect(client.isOperationActive()).toBe(true);
    const busyRes = await client.runAction({
      action_id: "embed.build",
      scope: { kind: "all" },
      confirm: "embed.build",
    });
    expect(busyRes.ok).toBe(false);
    expect((busyRes.payload?.error as any)?.code).toBe("action.busy");

    const ocrRes = await ocrPromise;
    expect(ocrRes.ok).toBe(false);
    expect(received).toHaveLength(16);
    expect(client.isOperationActive()).toBe(false);

    // Follow-up embed.build proceeds once lock released
    const embedRes = await client.runAction({
      action_id: "embed.build",
      scope: { kind: "all" },
      confirm: "embed.build",
    });
    expect(embedRes.ok).toBe(true);
    expect(client.isOperationActive()).toBe(false);
  });

  it("handles cooperative stop mid-stream without wedging OperationLock and recovers on restart", async () => {
    const transport = new MockTransport();
    transport.executeHandler = async (argv) =>
      JSON.stringify({
        ok: true,
        data: {
          action_id: argv.includes("embed.resume")
            ? "embed.resume"
            : "embed.build",
          availability: "available",
          execution_mode: "stream",
        },
      });
    let runCount = 0;
    transport.streamHandler = async () => {
      runCount += 1;
      if (runCount === 1) {
        return {
          delayMs: 30,
          events: [
            {
              schema_version: 1,
              event: "start",
              operation: "embed.build",
              total: 14,
            },
            {
              schema_version: 1,
              event: "item_result",
              operation: "embed.build",
              item_id: "P01",
              status: "succeeded",
            },
          ],
        };
      }
      return {
        events: [
          {
            schema_version: 1,
            event: "start",
            operation: "embed.resume",
            total: 13,
          },
          {
            schema_version: 1,
            event: "result",
            operation: "embed.resume",
            result: { ok: true, data: {} },
          },
        ],
        outcome: { ok: true, exitCode: 0 },
      };
    };

    const client = new PaperForgeClient({ transport });
    const first = client.runAction({
      action_id: "embed.build",
      scope: { kind: "all" },
      confirm: "embed.build",
    });
    await new Promise((r) => setTimeout(r, 10));
    expect(client.isOperationActive()).toBe(true);
    client.cancelActiveOperation();

    const firstRes = await first;
    expect(firstRes.cancelled).toBe(true);
    expect(client.isOperationActive()).toBe(false);

    const resumed = await client.runAction({
      action_id: "embed.resume",
      scope: { kind: "all" },
    });
    expect(resumed.ok).toBe(true);
    expect(client.isOperationActive()).toBe(false);
  });

  it("does not misclassify done/done_degraded/ok/skipped OCR item_results as failedKeys in requestOcrRun", async () => {
    const main = await import("../src/main");
    const PaperForgePlugin = (main as unknown as { default: any }).default;
    const { PaperForgeConfirmModal } = await import("../src/views/modals");

    vi.spyOn(PaperForgeConfirmModal.prototype, "open").mockImplementation(
      function (this: any) {
        this._onConfirm();
      }
    );

    const client = {
      isOperationActive: vi.fn(() => false),
      dashboardStats: vi.fn(async () => ({ items: [] })),
      runAction: vi.fn(
        async (
          _req: unknown,
          opts?: { onEvent?: (ev: NdjsonEvent) => void }
        ) => {
          const items = [
            ["P01", "done"],
            ["P02", "done_degraded"],
            ["P03", "ok"],
            ["P04", "skipped"],
            ["P05", "noop"],
            ["P06", "blocked"],
            ["P07", "fatal_error"],
          ];
          items.forEach(([id, st], i) => {
            opts?.onEvent?.({
              schema_version: 1,
              event: "progress",
              operation: "ocr.run",
              current: i + 1,
              total: items.length,
              item_id: id,
            });
            opts?.onEvent?.({
              schema_version: 1,
              event: "item_result",
              operation: "ocr.run",
              item_id: id,
              status: st,
            });
          });
          return { ok: false, payload: null, exitCode: 1 };
        }
      ),
    };

    const plugin = Object.create(PaperForgePlugin.prototype);
    plugin._ocrProgress = { current: 0, total: 1, key: "" };
    plugin._settingTab = { display: vi.fn() };
    plugin._autoSync = vi.fn();
    plugin._client = client;
    plugin.getClient = () => client;
    plugin.app = { vault: { adapter: { basePath: "/vault" } } };

    await plugin.requestOcrRun(true);
    await vi.waitFor(() => {
      expect(plugin._autoSync).toHaveBeenCalledWith("/vault");
    });

    const notice = notices.list[notices.list.length - 1] ?? "";
    expect(notice).toContain("P06");
    expect(notice).toContain("P07");
    expect(notice).not.toContain("P01");
    expect(notice).not.toContain("P02");
    expect(notice).not.toContain("P03");
    expect(notice).not.toContain("P04");
    expect(notice).not.toContain("P05");
  });
});
