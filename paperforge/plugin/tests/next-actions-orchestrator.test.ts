/**
 * Vitest tests for next-actions-orchestrator.ts (T8 #169).
 *
 * Policy authority is the Python registry — the wire carries
 * automatic/cost/impact/confirmation.  TS derives execution argv from the
 * wire (`action run <id> --scope ...`) and NEVER owns an allowlist.
 */
import { describe, expect, it, beforeEach } from "vitest";
import {
  orchestrateNextActions,
  buildActionArgv,
  actionDedupeKey,
} from "../src/services/next-actions-orchestrator";
import {
  parseNextActions,
  resetNextActionTracker,
  type NextAction,
  type OrchestratorDeps,
} from "../src/services/next-actions-types";

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

function deps(overrides: Partial<OrchestratorDeps> = {}): OrchestratorDeps & {
  ran: string[][];
  notices: string[];
  confirmed: NextAction[];
} {
  const ran: string[][] = [];
  const notices: string[] = [];
  const confirmed: NextAction[] = [];
  return {
    runAction: (argv) => {
      ran.push(argv);
      return true;
    },
    confirm: async (a) => {
      confirmed.push(a);
      return true;
    },
    notify: (m) => notices.push(m),
    isInFlight: () => false,
    hasExecuted: () => false,
    markInFlight: () => {},
    clearInFlight: () => {},
    markExecuted: () => {},
    ran,
    notices,
    confirmed,
    ...overrides,
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
    // T8: argv is derived from the wire — `action run <id> --scope ...`,
    // never a plugin-side (verb, command) table.
    expect(d.ran).toEqual([
      ["action", "run", "memory.build", "--scope", "all"],
      ["action", "run", "embed.resume", "--scope", "all"],
    ]);
    expect(d.confirmed.map((a) => a.action_id)).toEqual(["embed.resume"]);
  });

  it("returns [] for malformed or missing payloads", () => {
    expect(parseNextActions("not json")).toEqual([]);
    expect(parseNextActions(JSON.stringify({ ok: true }))).toEqual([]);
    expect(parseNextActions("")).toEqual([]);
  });
});

describe("argv derivation", () => {
  it("builds papers-scope argv with keys", () => {
    const argv = buildActionArgv(
      action({ scope: { kind: "papers", keys: ["B", "A"] } })
    );
    expect(argv).toEqual([
      "action",
      "run",
      "memory.build",
      "--scope",
      "papers",
      "--key",
      "B",
      "A",
    ]);
  });

  it("dedupes by normalized scope keys", () => {
    expect(
      actionDedupeKey(
        action({ scope: { kind: "papers", keys: ["B", "A", "B"] } })
      )
    ).toBe("memory.build:papers:A,B");
    expect(
      actionDedupeKey(action({ scope: { kind: "papers", keys: ["A", "B"] } }))
    ).toBe("memory.build:papers:A,B");
  });
});

describe("execution policy", () => {
  it("runs automatic local actions without confirmation", async () => {
    const d = deps();
    const started = await orchestrateNextActions([action()], d);
    expect(started).toBe(1);
    expect(d.ran).toEqual([
      ["action", "run", "memory.build", "--scope", "all"],
    ]);
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
    expect(d.ran).toEqual([
      ["action", "run", "embed.resume", "--scope", "all"],
    ]);
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

  it("dedupes an already-executed action", async () => {
    let executed = false;
    const d = deps({
      hasExecuted: () => executed,
      markExecuted: () => {
        executed = true;
      },
    });
    const started = await orchestrateNextActions([action(), action()], d);
    // First runs and is marked; the duplicate is skipped.
    expect(started).toBe(1);
    expect(d.ran).toHaveLength(1);
  });
});
