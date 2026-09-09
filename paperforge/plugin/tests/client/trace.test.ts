/**
 * Client trace contract (frontend-interface diagnostics).
 *
 * The trace is the one place that sees both sides of the boundary, so it
 * must be useful AND safe: metadata only (command identity, ok, duration,
 * epoch, error code) — never stdin, env, or argument values.
 */
import { describe, it, expect, beforeEach } from "vitest";
import {
  clearTrace,
  commandIdentity,
  dumpTrace,
  isTraceEnabled,
  setTraceEnabled,
  traceRecord,
} from "../../src/client/trace";
import { MockTransport } from "./mock-transport";
import { PaperForgeClient } from "../../src/client/paperforge-client";

beforeEach(() => {
  clearTrace();
  setTraceEnabled(false);
});

describe("trace module", () => {
  it("records metadata, stays bounded, and dumps copyable lines", () => {
    traceRecord({
      ts: Date.now(),
      kind: "exec",
      op: "sync --json",
      ok: true,
      ms: 12,
      epoch: 3,
    });
    const dump = dumpTrace();
    expect(dump).toContain("exec");
    expect(dump).toContain("sync --json");
    expect(dump).toContain("ok=true");
    expect(dump).toContain("12ms");
    expect(dump).toContain("epoch=3");
  });

  it("commandIdentity never exposes argument VALUES", () => {
    expect(
      commandIdentity([
        "action",
        "run",
        "memory.build",
        "--scope",
        "all",
        "--json",
      ])
    ).toBe("action run --scope --json");
    expect(
      commandIdentity([
        "note",
        "set-flag",
        "--key",
        "ABCD1234",
        "--field",
        "do_ocr",
        "--json",
      ])
    ).toBe("note set-flag --key --field --json");
    expect(commandIdentity(["auth", "set", "--stdin", "--json"])).toBe(
      "auth set --stdin --json"
    );
  });

  it("toggling only affects console emission, not the ring", () => {
    traceRecord({
      ts: Date.now(),
      kind: "exec",
      op: "status --json",
      ok: true,
    });
    expect(dumpTrace()).toContain("status --json");
    setTraceEnabled(true);
    expect(isTraceEnabled()).toBe(true);
    clearTrace();
    expect(dumpTrace()).toBe("");
  });
});

describe("client trace integration", () => {
  it("records the single PFResult choke point (success and authority rejection)", async () => {
    const transport = new MockTransport();
    const client = new PaperForgeClient({ transport });
    transport.executeHandler = (argv) =>
      argv[0] === "sync"
        ? JSON.stringify({ ok: true, data: { papers_synced: 1 } })
        : JSON.stringify({
            ok: false,
            data: null,
            error: { code: "VALIDATION_ERROR", message: "boom" },
          });
    await client.sync();
    let dump = dumpTrace();
    expect(dump).toContain("sync --json");
    expect(dump).toContain("ok=true");
    // authority rejection is traced with its CODE, not its message payload
    await expect(client.versionsRestore("K1", "v1")).rejects.toThrow("boom");
    dump = dumpTrace();
    expect(dump).toContain("code=VALIDATION_ERROR");
    expect(dump).not.toContain("boom");
  });

  it("never records stdin/env content", async () => {
    const transport = new MockTransport();
    const client = new PaperForgeClient({ transport });
    transport.executeHandler = () =>
      JSON.stringify({ ok: true, data: { changed: true } });
    await client.authSetSecret("embedding", "sk-secret-value-12345", {
      replace: false,
    });
    const dump = dumpTrace();
    expect(dump).toContain("auth set");
    expect(dump).not.toContain("sk-secret-value-12345");
  });
});
