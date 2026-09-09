/**
 * Vitest tests for next-actions-orchestrator.ts (T8 #169).
 *
 * Policy authority is the Python registry — the wire carries
 * automatic/cost/impact/confirmation.  TS derives execution argv from the
 * wire (`action run <id> --scope ...`) and NEVER owns an allowlist.
 */
import { describe, expect, it, beforeEach } from "vitest";
vi.mock("obsidian", () => ({ Notice: vi.fn() }));
import type {
  ActionRequest,
  ActionRunResult,
} from "../src/client/action-contract";
import { orchestrateNextActions } from "../src/services/next-actions-orchestrator";
import { buildActionArgv } from "../src/client/action-contract";
import {
  parseNextActions,
  resetNextActionTracker,
  type NextAction,
} from "../src/services/next-actions-types";
import { orchestrateFromSync } from "../src/services/next-actions-bridge";

beforeEach(() => resetNextActionTracker());

function action(overrides: Partial<NextAction> = {}): NextAction {
  return {
    schema_version: 1,
    action_id: "memory.build",
    scope: { kind: "all" },
    automatic: true,
    cost: "local",
    impact: "mutating",
    confirmation: "none",
    reason: "library index changed",
    ...overrides,
  };
}

function deps(
  overrides: Partial<{
    runAction: (req: ActionRequest) => Promise<ActionRunResult>;
    confirm: (a: NextAction) => Promise<boolean>;
    notify: (m: string) => void;
    isInFlight: (k: string) => boolean;
    markInFlight: (k: string) => void;
    clearInFlight: (k: string) => void;
  }> = {}
): {
  ran: ActionRequest[];
  notices: string[];
  confirmed: NextAction[];
  runAction: (req: ActionRequest) => Promise<ActionRunResult>;
  confirm: (a: NextAction) => Promise<boolean>;
  notify: (m: string) => void;
  isInFlight: (k: string) => boolean;
  markInFlight: (k: string) => void;
  clearInFlight: (k: string) => void;
} {
  const ran: ActionRequest[] = [];
  const notices: string[] = [];
  const confirmed: NextAction[] = [];
  return {
    runAction: async (req) => {
      ran.push(req);
      return { ok: true, payload: { ok: true }, exitCode: 0 };
    },
    confirm: async (a) => {
      confirmed.push(a);
      return true;
    },
    notify: (m) => notices.push(m),
    isInFlight: () => false,
    markInFlight: () => {},
    clearInFlight: () => {},
    ...overrides,
    ran,
    notices,
    confirmed,
  };
}

describe("parseNextActions", () => {
  it("extracts next_actions from a PFResult document", () => {
    const stdout = JSON.stringify({
      ok: true,
      command: "sync",
      version: "1.0.0",
      next_actions: [{ ...action() }],
    });
    const parsed = parseNextActions(stdout);
    expect(parsed).toHaveLength(1);
    expect(parsed[0].action_id).toBe("memory.build");
  });

  it("consumes the real backend sync --json contract shape", async () => {
    const stdout = JSON.stringify({
      ok: true,
      command: "sync",
      version: "1.5.16",
      data: { papers: 3 },
      next_actions: [
        {
          schema_version: 1,
          action_id: "memory.build",
          scope: { kind: "all" },
          automatic: true,
          cost: "local",
          impact: "mutating",
          confirmation: "none",
          reason: "library index changed after sync",
        },
        {
          schema_version: 1,
          action_id: "embed.resume",
          scope: { kind: "all" },
          automatic: false,
          cost: "remote_possible",
          impact: "mutating",
          confirmation: "required",
          reason: "changed papers need vector embeddings",
        },
      ],
    });
    const d = deps();
    const started = await orchestrateNextActions(parseNextActions(stdout), d);
    expect(started).toBe(2);
    // T8: the orchestrator hands the ActionClient a typed request — argv
    // construction lives in ONE builder, never a plugin-side table.
    expect(d.ran.map((r) => r.action_id)).toEqual([
      "memory.build",
      "embed.resume",
    ]);
    expect(d.ran[0].confirm).toBeUndefined();
    expect(d.ran[1].confirm).toBe("embed.resume"); // user confirmed it
    expect(d.confirmed.map((a) => a.action_id)).toEqual(["embed.resume"]);
  });

  it("returns [] for malformed or missing payloads", () => {
    expect(parseNextActions("not json")).toEqual([]);
    expect(parseNextActions(JSON.stringify({ ok: true }))).toEqual([]);
    expect(parseNextActions("")).toEqual([]);
  });
});

describe("argv derivation", () => {
  it("builds papers-scope argv with REPEATED --key flags", () => {
    const argv = buildActionArgv({
      action_id: "memory.build",
      scope: { kind: "papers", keys: ["B", "A"] },
    });
    expect(argv).toEqual([
      "action",
      "run",
      "memory.build",
      "--scope",
      "papers",
      "--key",
      "B",
      "--key",
      "A",
      "--json",
    ]);
  });

  it("includes --confirm and --follow auto when given", () => {
    const argv = buildActionArgv({
      action_id: "embed.resume",
      scope: { kind: "all" },
      confirm: "embed.resume",
      follow: "auto",
    });
    expect(argv).toContain("--confirm");
    expect(argv).toContain("embed.resume");
    expect(argv).toContain("--follow");
    expect(argv).toContain("auto");
    expect(argv[argv.length - 1]).toBe("--json");
  });

  it("suppresses a second batch while the first is in flight", async () => {
    const inFlight = new Set<string>();
    const d = deps({
      isInFlight: (k) => inFlight.has(k),
      markInFlight: (k) => inFlight.add(k),
      clearInFlight: (k) => inFlight.delete(k),
    });
    inFlight.add("memory.build:all"); // a previous batch is still running
    const started = await orchestrateNextActions([action()], d);
    expect(started).toBe(0);
    expect(d.ran).toHaveLength(0);
  });
});

describe("execution policy", () => {
  it("runs automatic local actions without confirmation", async () => {
    const d = deps();
    const started = await orchestrateNextActions([action()], d);
    expect(started).toBe(1);
    expect(d.ran).toHaveLength(1);
    expect(d.ran[0].action_id).toBe("memory.build");
    expect(d.ran[0].confirm).toBeUndefined();
    expect(d.confirmed).toEqual([]);
  });

  it("confirms non-automatic actions before running", async () => {
    const d = deps();
    const embed = action({
      action_id: "embed.resume",
      automatic: false,
      cost: "remote_possible",
      confirmation: "required",
    });
    const started = await orchestrateNextActions([embed], d);
    expect(started).toBe(1);
    expect(d.confirmed).toEqual([embed]);
    expect(d.ran).toHaveLength(1);
    expect(d.ran[0].action_id).toBe("embed.resume");
    expect(d.ran[0].confirm).toBe("embed.resume");
  });

  it("records refusal when the user declines", async () => {
    const d = deps({ confirm: async () => false });
    const embed = action({
      action_id: "embed.resume",
      automatic: false,
      confirmation: "required",
    });
    const started = await orchestrateNextActions([embed], d);
    expect(started).toBe(0);
    expect(d.ran).toEqual([]);
    expect(d.notices.some((m) => m.includes("refused"))).toBe(true);
  });

  it("refuses unknown schema versions", async () => {
    const d = deps();
    const started = await orchestrateNextActions(
      [{ ...action(), schema_version: 999 }],
      d
    );
    expect(started).toBe(0);
    expect(d.ran).toEqual([]);
  });

  it("skips non-automatic follow-ups beyond depth 0 (loop guard)", async () => {
    const d = deps();
    const embed = action({
      action_id: "embed.resume",
      automatic: false,
      confirmation: "required",
    });
    const started = await orchestrateNextActions([embed], d, 1);
    expect(started).toBe(0);
    expect(d.confirmed).toEqual([]);
    expect(d.notices.some((m) => m.includes("depth"))).toBe(true);
  });

  it("never suppresses a LATER re-repair of the same scope (#169 P0-2)", async () => {
    // No `_executed` set exists: a later legitimate re-repair (new OCR →
    // stale → Python re-emits memory.build[A]) must run again.  Only the
    // in-flight guard applies, and it is cleared when the action settles.
    const d = deps();
    const first = await orchestrateNextActions([action()], d);
    expect(first).toBe(1);
    const second = await orchestrateNextActions([action()], d);
    expect(second).toBe(1);
    expect(d.ran).toHaveLength(2);
  });
});

describe("sync bridge consent boundary", () => {
  it("runs automatic work and leaves consent-required work pending", async () => {
    const runAction = vi.fn(async () => ({
      ok: true,
      payload: { ok: true },
      exitCode: 0,
    }));
    const stdout = JSON.stringify({
      ok: true,
      command: "sync",
      version: "1.5.16",
      next_actions: [
        action(),
        action({
          action_id: "embed.resume",
          automatic: false,
          cost: "remote_possible",
          confirmation: "required",
        }),
      ],
    });

    const started = await orchestrateFromSync(stdout, { runAction });

    expect(started).toBe(1);
    expect(runAction).toHaveBeenCalledOnce();
    expect(runAction.mock.calls[0][0]).toMatchObject({
      action_id: "memory.build",
      confirm: undefined,
    });
  });

  it("backend failure surfaces the authority reason and still settles the guard", async () => {
    const runAction = vi.fn(async () => ({
      ok: false,
      payload: {
        error: {
          code: "VALIDATION_ERROR",
          message: "vector_substrate_incompatible",
        },
      },
      exitCode: 1,
    }));
    const stdout = JSON.stringify({
      ok: true,
      command: "sync",
      version: "1.5.16",
      next_actions: [action()],
    });
    const started = await orchestrateFromSync(stdout, { runAction });
    expect(started).toBe(1);
    // settled — the guard is cleared (tracker state), a later re-repair runs
    const second = await orchestrateFromSync(stdout, {
      runAction: vi.fn(async () => ({ ok: true, payload: {}, exitCode: 0 })),
    });
    expect(second).toBe(1);
  });
});

describe("in-flight guard covers REAL settlement (step 6 item 3)", () => {
  it("blocks the same dedupe key until the action settles, then allows re-repair", async () => {
    let release!: (res: ActionRunResult) => void;
    const gate = new Promise<ActionRunResult>((r) => (release = r));
    const inFlight = new Set<string>();
    const executed: ActionRequest[] = [];
    const d = deps({
      runAction: async (req) => {
        executed.push(req);
        if (executed.length === 1) return gate;
        return { ok: true, payload: { ok: true }, exitCode: 0 };
      },
      isInFlight: (k) => inFlight.has(k),
      markInFlight: (k) => inFlight.add(k),
      clearInFlight: (k) => inFlight.delete(k),
    });

    const first = orchestrateNextActions([action()], d); // pending on gate
    await vi.waitFor(() => expect(executed).toHaveLength(1));

    // a second convergence tick while the first action is UNSETTLED
    const second = await orchestrateNextActions([action()], d);
    expect(second).toBe(0); // in-flight guard holds across the real lifecycle

    release({ ok: true, payload: { ok: true }, exitCode: 0 });
    expect(await first).toBe(1);

    // settled -> guard cleared -> a later legitimate re-repair runs (#169)
    const third = await orchestrateNextActions([action()], d);
    expect(third).toBe(1);
    expect(executed).toHaveLength(2);
  });
});
