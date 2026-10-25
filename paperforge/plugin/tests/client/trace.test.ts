/**
 * Client trace contract (frontend-interface diagnostics).
 *
 * The trace is the one place that sees both sides of the boundary, so it
 * must be useful AND safe: metadata only (command identity, ok, duration,
 * epoch, error code) — never stdin, env, or argument values.
 */
import "obsidian-test-mocks/jest-setup";
import { describe, expect, it, beforeEach, vi } from "vitest";
import {
  clearTrace,
  commandIdentity,
  dumpTrace,
  isTraceEnabled,
  setTraceEnabled,
  traceConsoleError,
  traceRecord,
} from "../../src/client/trace";
import { MockTransport } from "./mock-transport";
import { PaperForgeClient } from "../../src/client/paperforge-client";
import { PaperForgeStatusView } from "../../src/views/dashboard";
import { copySupportDiagnostic } from "../../src/primitives";
import { checkOrphanState } from "../../src/views/modals";

beforeEach(() => {
  clearTrace();
  setTraceEnabled(false);
});

describe("trace module", () => {
  it("records metadata, stays bounded, and dumps copyable lines", () => {
    traceRecord({
      ts: Date.now(),
      kind: "exec",
      op: "sync",
      ok: true,
      ms: 12,
      epoch: 3,
    });
    const dump = dumpTrace();
    expect(dump).toContain("exec");
    expect(dump).toContain("sync");
    expect(dump).toContain("ok=true");
    expect(dump).toContain("12ms");
    expect(dump).toContain("epoch=3");
  });

  it("commandIdentity emits only fixed command + subcommand tokens, never values or flags", () => {
    expect(
      commandIdentity([
        "action",
        "run",
        "memory.build",
        "--scope",
        "all",
        "--json",
      ])
    ).toBe("action run");
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
    ).toBe("note set-flag");
    expect(commandIdentity(["auth", "set", "--stdin", "--json"])).toBe(
      "auth set"
    );
    // No fixed subcommand in slot 2: bare command only, user value dropped.
    expect(commandIdentity(["search", "SECRETQUERY", "--limit", "20", "--json"])).toBe("search");
    expect(commandIdentity(["retrieve", "SECRETQUERY", "--limit", "5", "--json"])).toBe("retrieve");
    expect(commandIdentity(["reading-log", "--search", "SECRETQUERY", "--json"])).toBe("reading-log");
    expect(commandIdentity(["probe", "library", "--json"])).toBe("probe");
    expect(commandIdentity(["config", "set", "SECRETKEY", "SECRETVALUE", "--json"])).toBe("config set");
    expect(commandIdentity(["reconcile", "--scope", "all", "--key", "SECRETKEY", "--json"])).toBe("reconcile");
    expect(commandIdentity(["paper-status", "SECRETQUERY", "--json"])).toBe("paper-status");
    expect(commandIdentity([])).toBe("unknown");
    // Query text that collides with a fixed token stays a value, never a subcommand.
    expect(commandIdentity(["search", "run"])).toBe("search");
    expect(commandIdentity(["search", "status"])).toBe("search");
    expect(commandIdentity(["search", "list"])).toBe("search");
    expect(commandIdentity(["retrieve", "run"])).toBe("retrieve");
    expect(commandIdentity(["retrieve", "status"])).toBe("retrieve");
    expect(commandIdentity(["reading-log", "status"])).toBe("reading-log");
    // Flags never appear, even fixed ones.
    expect(commandIdentity(["sync", "--json"])).toBe("sync");
    expect(commandIdentity(["doctor", "--json"])).toBe("doctor");
  });
  it("toggling only affects console emission, not the ring", () => {
    traceRecord({
      ts: Date.now(),
      kind: "exec",
      op: "status",
      ok: true,
    });
    expect(dumpTrace()).toContain("status");
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
    expect(dump).toContain("sync");
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

describe("traceConsoleError", () => {
  it("emits a redacted Console error with fixed fields only", () => {
    const seen: unknown[][] = [];
    const orig = console.error;
    console.error = (...a: unknown[]) => void seen.push(a);
    try {
      traceConsoleError({ op: "search", stage: "pfresult", code: "PATH_NOT_FOUND", exitCode: 1 });
      expect(seen.length).toBe(1);
      const line = String(seen[0][0]);
      expect(line).toContain("[PF] failed");
      expect(line).toContain("op=search");
      expect(line).toContain("stage=pfresult");
      expect(line).toContain("code=PATH_NOT_FOUND");
      expect(line).toContain("exit=1");
    } finally {
      console.error = orig;
    }
  });

  it("never prints Error objects, stacks, query/key/argv/stdout/stderr/paper text/credentials", () => {
    const seen: unknown[][] = [];
    const orig = console.error;
    console.error = (...a: unknown[]) => void seen.push(a);
    try {
      traceConsoleError({ op: "retrieve", stage: "process", code: "transport_error", exitCode: 0 });
      expect(seen.length).toBe(1);
      const line = String(seen[0][0]) + String(seen[0].slice(1).join(" "));
      for (const secret of ["sk-secret", "my query text", "paper body", "Error: boom", "at Object", "--paper K1", "stdout-text", "stderr-text"]) {
        expect(line).not.toContain(secret);
      }
    } finally {
      console.error = orig;
    }
  });

  it("suppresses expected states: unconfigured/disabled/empty/cancelled are not Console errors", () => {
    const seen: unknown[][] = [];
    const orig = console.error;
    console.error = (...a: unknown[]) => void seen.push(a);
    try {
      for (const code of ["cancelled", "action.cancelled", "action.unavailable", "credential.missing", "memory.disabled", "vector.not_enabled"]) {
        traceConsoleError({ op: "sync", stage: "stream", code, exitCode: 0 });
      }
      expect(seen.length).toBe(0);
    } finally {
      console.error = orig;
    }
  });

  it("two independent identical failures log twice; one rc-failure + PFResult rejection logs once with the real exit", async () => {
    const transport = new MockTransport();
    const client = new PaperForgeClient({ transport });
    const seen: unknown[][] = [];
    const orig = console.error;
    console.error = (...a: unknown[]) => void seen.push(a);
    try {
      // Two independent attempts: no cross-operation suppression.
      transport.executeHandler = () =>
        JSON.stringify({ ok: false, data: null, error: { code: "PRECONDITION_FAILED", message: "need build" } });
      await client.embedStatus().catch(() => undefined);
      client.invalidateCache();
      await client.embedStatus().catch(() => undefined);
      expect(seen.length).toBe(2);
      expect(String(seen[0][0])).toContain("exit=0");

      // One operation whose rc failure carries a structured PFResult: single terminal.
      seen.length = 0;
      transport.executeHandler = () => {
        const e = new Error("rc1") as Error & { exitCode?: number; stdout?: string };
        e.exitCode = 1;
        e.stdout = JSON.stringify({ ok: false, data: { vector_state: "stale" }, error: { code: "PRECONDITION_FAILED", message: "stale" } });
        throw e;
      };
      client.invalidateCache();
      await client.embedStatus().catch(() => undefined);
      expect(seen.length).toBe(1);
      expect(String(seen[0][0])).toContain("exit=1");
    } finally {
      console.error = orig;
    }
  });

  it("empty-DB search rejection maps without a Console error; NO_PYTHON setup failure is suppressed", async () => {
    const seen: unknown[][] = [];
    const orig = console.error;
    console.error = (...a: unknown[]) => void seen.push(a);
    const transport = new MockTransport();
    const client = new PaperForgeClient({ transport });
    try {
      // search+PATH_NOT_FOUND: trace ring keeps the code, Console silent.
      transport.executeHandler = () => {
        const e = new Error("rc1") as Error & { exitCode?: number; stdout?: string };
        e.exitCode = 1;
        e.stdout = JSON.stringify({ ok: false, data: null, error: { code: "PATH_NOT_FOUND", message: "no db" } });
        throw e;
      };
      await expect(client.search("SECRETQUERY")).rejects.toThrow("no db");
      expect(seen.length).toBe(0);
      expect(dumpTrace()).toContain("code=PATH_NOT_FOUND");
      expect(dumpTrace()).not.toContain("SECRETQUERY");

      // NO_PYTHON expected setup state: machine code kept, Console silent.
      clearTrace();
      transport.executeHandler = () => {
        const e = new Error("PaperForge Python runtime not ready.") as Error & { code?: string };
        e.code = "NO_PYTHON";
        throw e;
      };
      await expect(client.runAction({ action_id: "memory.build" }))
        .rejects.toMatchObject({ code: "NO_PYTHON" });
      expect(seen.length).toBe(0);
      expect(dumpTrace()).toContain("code=NO_PYTHON");
    } finally {
      console.error = orig;
    }
  });

  it.each(["not_built", "stale"])("keeps expected vector state %s out of the error Console", async (vectorState) => {
    const seen: unknown[][] = [];
    const orig = console.error;
    console.error = (...args: unknown[]) => void seen.push(args);
    try {
      const transport = new MockTransport();
      transport.executeHandler = () => {
        throw Object.assign(new Error("PRIVATE_EXCEPTION"), {
          exitCode: 1,
          stdout: JSON.stringify({ ok: false, data: { vector_state: vectorState },
            error: { code: "PRECONDITION_FAILED", message: "PRIVATE_EXCEPTION" } }),
        });
      };
      const client = new PaperForgeClient({ transport });
      await expect(client.retrieve("PRIVATE_QUERY")).rejects.toMatchObject({
        code: "PRECONDITION_FAILED", data: { vector_state: vectorState },
      });
      expect(seen).toHaveLength(0);
      expect(dumpTrace()).not.toMatch(/PRIVATE_QUERY|PRIVATE_EXCEPTION/);
    } finally {
      console.error = orig;
    }
  });

  it.each([1, null])("reports a process failure once without private output (exit=%s)", async (exitCode) => {
    const seen: unknown[][] = [];
    const orig = console.error;
    console.error = (...args: unknown[]) => void seen.push(args);
    try {
      const transport = new MockTransport();
      transport.executeHandler = () => {
        throw Object.assign(new Error("PRIVATE_STDERR"), { code: "ECONNREFUSED", exitCode });
      };
      const client = new PaperForgeClient({ transport });
      await expect(client.search("PRIVATE_QUERY")).rejects.toMatchObject({ code: "ECONNREFUSED" });
      expect(seen).toHaveLength(1);
      expect(String(seen[0][0])).toContain(`code=ECONNREFUSED exit=${exitCode ?? "?"}`);
      expect(JSON.stringify(seen)).not.toMatch(/PRIVATE_STDERR|PRIVATE_QUERY/);
    } finally {
      console.error = orig;
    }
  });
  it("runAction protocol contradiction logs once with the protocol code", async () => {
    const seen: unknown[][] = [];
    const orig = console.error;
    console.error = (...a: unknown[]) => void seen.push(a);
    const transport = new MockTransport();
    const client = new PaperForgeClient({ transport });
    try {
      transport.executeHandler = (argv) => {
        if (argv[0] === "action" && argv[1] === "describe")
          return JSON.stringify({ ok: true, data: { action_id: "memory.build", availability: "available", execution_mode: "result", confirmation: "none" } });
        const e = new Error("rc2") as Error & { exitCode?: number; stdout?: string };
        e.exitCode = 2;
        e.stdout = JSON.stringify({ ok: true, data: {} });
        throw e;
      };
      const res = await client.runAction({ action_id: "memory.build" });
      expect(res.ok).toBe(false);
      expect(res.payload?.error).toMatchObject({ code: "protocol_contradiction" });
      // Single terminal: exactly one Console line, protocol code kept.
      expect(seen.length).toBe(1);
      expect(String(seen[0][0])).toContain("stage=result");
      expect(String(seen[0][0])).toContain("code=protocol_contradiction");
    } finally {
      console.error = orig;
    }
  });

  it("local failures log once redacted; typed-client failures stay single-owned", async () => {
    const seen: unknown[][] = [];
    const origErr = console.error;
    const origWarn = console.warn;
    const origLog = console.log;
    const origClipboard = (navigator as unknown as { clipboard?: unknown }).clipboard;
    console.error = (...a: unknown[]) => void seen.push(a);
    console.warn = () => undefined;
    console.log = () => undefined;
    // jsdom ships no clipboard: stub a denied write so the copy-failure
    // terminal is exercised without touching a real clipboard.
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: () => Promise.reject(new Error("denied")) },
      configurable: true,
    });
    try {
      copySupportDiagnostic("diagnostic-body");
      await vi.waitFor(() => expect(seen.length).toBe(1));
      expect(String(seen[0][0])).toContain("op=diagnostic.copy");
      expect(String(seen[0][0])).toContain("stage=local");

      const failingProbe = () => Promise.reject(new Error("lineage down"));
      checkOrphanState({} as never, { getClient: () => ({ probe: failingProbe }) } as never, "/vault");
      await vi.waitFor(() => expect(seen.length).toBe(2));
      expect(String(seen[1][0])).toContain("op=probe.lineage");
      expect(JSON.stringify(seen)).not.toMatch(/lineage down|\/vault|diagnostic-body/);

      seen.length = 0;
      const transport = new MockTransport();
      const client = new PaperForgeClient({ transport });
      transport.executeHandler = () =>
        JSON.stringify({ ok: false, data: null, error: { code: "BACKEND_UNAVAILABLE", message: "down" } });
      await expect(client.configSet("literature_dir", "Lit")).rejects.toMatchObject({
        code: "BACKEND_UNAVAILABLE",
      });
      // Typed-client terminal owns it: exactly one line, no View echo.
      expect(seen.length).toBe(1);
      expect(String(seen[0][0])).toContain("op=config set");
    } finally {
      console.error = origErr;
      console.warn = origWarn;
      console.log = origLog;
      Object.defineProperty(navigator, "clipboard", {
        value: origClipboard,
        configurable: true,
      });
    }
  });
  it("stream transport rejection emits the single stream terminal failure", async () => {
    const seen: unknown[][] = [];
    const orig = console.error;
    console.error = (...a: unknown[]) => void seen.push(a);
    const transport = new MockTransport();
    const client = new PaperForgeClient({ transport });
    try {
      transport.streamHandler = () => {
        throw new Error("spawn ENOENT");
      };
      const handle = client.streamOperation("sync", ["sync", "--json"]);
      await expect(handle.outcome).rejects.toThrow("spawn ENOENT");
      expect(seen.length).toBe(1);
      expect(String(seen[0][0])).toContain("stage=stream");
      expect(String(seen[0][0])).toContain("code=transport_error");
    } finally {
      console.error = orig;
    }
  });

  it("dashboard maps structured codes and Console/dumpTrace never carry the private query", async () => {
    const orig = console.error;
    const seen: unknown[][] = [];
    console.error = (...a: unknown[]) => void seen.push(a);
    try {
      const transport = new MockTransport();
      const client = new PaperForgeClient({ transport });
      const leaf = {};
      const view = new PaperForgeStatusView(leaf as never) as unknown as {
        app: unknown;
        _searchGeneration: number;
        _searchInput: { value: string } | null;
        _searchMode: string;
        _searchState: string;
        executeSearch: () => Promise<void>;
      };
      view.app = {
        vault: { adapter: { basePath: "/vault" } },
        plugins: { plugins: { paperforge: { getClient: () => client } } },
      };
      // Same seam as retrieval-knowledge-cutover makeDashboard: real DOM
      // elements + real _renderSearchState (only the state mapping asserts).
      view._searchInput = document.createElement("input");
      view._searchResultsEl = document.createElement("div");
      view._searchGeneration = 0;
      view._searchInput.value = "@ SECRETRETRIEVEQUERY";
      view._searchMode = "@";
      view._searchState = "idle";
      transport.executeHandler = () =>
        JSON.stringify({ ok: false, data: { vector_state: "not_built" }, error: { code: "PRECONDITION_FAILED", message: "need build" } });
      await view.executeSearch();
      expect(view._searchState).toBe("vectors-not-built");

      transport.executeHandler = () => {
        const e = new Error("rc1") as Error & { exitCode?: number; stdout?: string };
        e.exitCode = 1;
        e.stdout = JSON.stringify({ ok: false, data: null, error: { code: "PATH_NOT_FOUND", message: "no db" } });
        throw e;
      };
      view._searchMode = "M";
      if (view._searchInput) view._searchInput.value = "SECRETSEARCHQUERY";
      await view.executeSearch();
      // Missing Memory DB on metadata search gets its own recovery card.
      expect(view._searchState).toBe("missing-memory-index");

      const consoleText = seen.map((a) => a.map(String).join(" ")).join("\n");
      const ring = dumpTrace();
      for (const secret of ["SECRETRETRIEVEQUERY", "SECRETSEARCHQUERY"]) {
        expect(consoleText).not.toContain(secret);
        expect(ring).not.toContain(secret);
      }
      // reading-log + config set + action keys: same fixed-identity contract.
      expect(commandIdentity(["reading-log", "--search", "SECRETREADINGQUERY", "--json"])).toBe("reading-log");
      expect(commandIdentity(["config", "set", "SECRETKEY", "SECRETVALUE", "--json"])).toBe("config set");
      expect(commandIdentity(["action", "run", "memory.build", "--scope", "papers", "--key", "SECRETKEY1", "--key", "SECRETKEY2", "--json"])).toBe("action run");
      const ring2 = dumpTrace();
      for (const secret of ["SECRETREADINGQUERY", "SECRETKEY", "SECRETVALUE", "SECRETKEY1", "SECRETKEY2"]) {
        expect(ring2).not.toContain(secret);
      }
    } finally {
      console.error = orig;
    }
  });
});
