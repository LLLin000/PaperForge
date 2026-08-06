/**
 * Vitest tests for next-actions-orchestrator.ts — parsing, allowlist
 * enforcement, dedupe, loop guard, and confirmation flow (#127 PR C).
 */
import { describe, expect, it, beforeEach } from "vitest";
import {
  ALLOWED_ACTIONS,
  orchestrateNextActions,
  parseNextActions,
  resetNextActionTracker,
  type NextAction,
  type OrchestratorDeps,
} from "../src/services/next-actions-orchestrator";

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
    dedupe_key: "memory.build",
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
      next_actions: [action().schema_version && { ...action() }],
    });
    const parsed = parseNextActions(stdout);
    expect(parsed).toHaveLength(1);
    expect(parsed[0].action_id).toBe("memory.build");
  });

  it("consumes the real backend sync --json contract shape (#127 PR D)", async () => {
    // This document mirrors what paperforge/commands/sync.py emits today:
    // schema_version 1, scope {kind}, dedupe_key = action_id.
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
          dedupe_key: "memory.build",
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
          dedupe_key: "embed.resume",
        },
      ],
    });
    const d = deps();
    const started = await orchestrateNextActions(parseNextActions(stdout), d);
    expect(started).toBe(2);
    expect(d.ran).toEqual([
      ["memory", "build"],
      ["embed", "build", "--resume"],
    ]);
    expect(d.confirmed.map((a) => a.action_id)).toEqual(["embed.resume"]);
  });

  it("returns [] for malformed or missing payloads", () => {
    expect(parseNextActions("not json")).toEqual([]);
    expect(parseNextActions(JSON.stringify({ ok: true }))).toEqual([]);
    expect(parseNextActions("")).toEqual([]);
  });
});

describe("allowlist enforcement", () => {
  it("defines the two canonical actions only", () => {
    expect(Object.keys(ALLOWED_ACTIONS).sort()).toEqual([
      "embed.resume",
      "memory.build",
    ]);
    expect(ALLOWED_ACTIONS["embed.resume"].argv).toEqual([
      "embed",
      "build",
      "--resume",
    ]);
  });

  it("refuses unknown action ids (fail closed)", async () => {
    const d = deps();
    const started = await orchestrateNextActions(
      [{ ...action(), action_id: "shell.exec" }],
      d
    );
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
});

describe("execution policy", () => {
  it("runs automatic local actions without confirmation", async () => {
    const d = deps();
    const started = await orchestrateNextActions([action()], d);
    expect(started).toBe(1);
    expect(d.ran).toEqual([["memory", "build"]]);
    expect(d.confirmed).toEqual([]);
  });

  it("confirms remote actions before running", async () => {
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
    expect(d.ran).toEqual([["embed", "build", "--resume"]]);
  });

  it("records refusal when the user declines", async () => {
    const d = deps({
      confirm: async () => false,
    });
    const embed = action({
      action_id: "embed.resume",
      automatic: false,
      cost: "remote_possible",
      confirmation: "required",
    });
    const started = await orchestrateNextActions([embed], d);
    expect(started).toBe(0);
    expect(d.ran).toEqual([]);
    expect(d.notices.some((m) => m.includes("refused by user"))).toBe(true);
  });

  it("dedupes by dedupe_key while in flight", async () => {
    const d = deps({
      runAction: (argv) => {
        d.ran.push(argv);
        // simulate a second delivery while the first is still running
        void orchestrateNextActions([action()], d);
        return true;
      },
    });
    const started = await orchestrateNextActions([action(), action()], d);
    expect(started).toBe(1);
    expect(d.ran).toHaveLength(1);
  });

  it("does not mark actions executed when nothing started (retry allowed)", async () => {
    const d = deps({
      runAction: () => false, // runtime unavailable
    });
    const first = await orchestrateNextActions([action()], d);
    expect(first).toBe(0);
    expect(d.ran).toEqual([]);
    // a later delivery with the runtime now available must still run
    const d2 = deps();
    const second = await orchestrateNextActions([action()], d2);
    expect(second).toBe(1);
    expect(d2.ran).toEqual([["memory", "build"]]);
  });

  it("loop guard: depth > 0 skips confirmed follow-ups", async () => {
    const d = deps();
    const embed = action({
      action_id: "embed.resume",
      automatic: false,
      cost: "remote_possible",
      confirmation: "required",
    });
    const started = await orchestrateNextActions([embed], d, 1);
    expect(started).toBe(0);
    expect(d.ran).toEqual([]);
    expect(d.notices.some((m) => m.includes("depth exceeded"))).toBe(true);
  });
});
