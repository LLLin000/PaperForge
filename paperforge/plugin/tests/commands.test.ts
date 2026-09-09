/**
 * Vitest tests for commands.js — ACTIONS.
 *
 * vi.mock to avoid CJS/ESM module mocking limitations in vitest v2.1.x.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

import { ACTIONS } from "../src/constants";

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
