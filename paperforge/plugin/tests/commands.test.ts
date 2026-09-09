/**
 * Vitest tests for commands.js — ACTIONS + buildCommandArgs.
 *
 * vi.mock to avoid CJS/ESM module mocking limitations in vitest v2.1.x.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

import { ACTIONS } from "../src/constants";
import { buildCommandArgs } from "../src/services/python-bridge";

describe("ACTIONS", () => {
  it("has exactly 5 entries", () => {
    expect(ACTIONS).toHaveLength(5);
  });
  it("every entry has id, title, cmd, okMsg", () => {
    for (const a of ACTIONS) {
      expect(a).toHaveProperty("id");
      expect(a).toHaveProperty("title");
      expect(a).toHaveProperty("commandId");
      expect(a).toHaveProperty("okMsg");
    }
  });
  it("sync action has cmd: sync", () => {
    expect(ACTIONS.find((a) => a.id === "paperforge-sync")?.commandId).toBe(
      "sync"
    );
  });
  it("repair action is enabled (no disabled flag)", () => {
    expect(
      ACTIONS.find((a) => a.id === "paperforge-repair")?.disabled
    ).toBeUndefined();
  });
});

describe("buildCommandArgs", () => {
  it("appends key when needsKey", () => {
    expect(
      buildCommandArgs({ args: ["--json"], needsKey: true }, "ABC123")
    ).toEqual(["--json", "ABC123"]);
  });
  it("appends --all when needsFilter", () => {
    expect(buildCommandArgs({ needsFilter: true }, null)).toEqual(["--all"]);
  });
  it("returns empty array when no flags", () => {
    expect(buildCommandArgs({})).toEqual([]);
  });
  it("copies args to avoid mutation", () => {
    const a = { args: ["--json"], needsKey: true };
    expect(buildCommandArgs(a, "K1")).toEqual(["--json", "K1"]);
    expect(buildCommandArgs(a, "K2")).toEqual(["--json", "K2"]);
  });
});
