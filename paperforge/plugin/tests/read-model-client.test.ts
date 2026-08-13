/**
 * Read-model client argv contract (#161 / R).
 *
 * The generic transport is private; the typed methods must emit exactly
 * `paperforge <subcommand> ... --json`. Regression guard for the #175
 * review finding: read-model queries previously routed through
 * `paperforge config <cmd>` and returned a double-unwrapped PFResult.
 */

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

import {
  probeAll,
  queryMemoryDetail,
  queryEmbedStatus,
  queryOcrPapers,
  paperContext,
  configList,
  invalidateAll,
  refreshAll,
} from "../src/services/config-client";
import { resolvePythonExecutable } from "../src/services/python-bridge";

vi.mock("../src/services/python-bridge", () => ({
  resolvePythonExecutable: vi.fn(() => ({
    path: "/fake/python",
    source: "manual",
    extraArgs: [],
  })),
}));

const { mockExecFile } = vi.hoisted(() => ({
  mockExecFile: vi.fn(
    (
      _path: string,
      argv: string[],
      _opts: unknown,
      cb: (err: null, stdout: string) => void
    ) => {
      const isProbeAll = argv.includes("probe") && argv.includes("all");
      // probe all emits a BARE envelope; other typed methods emit PFResult.
      const payload = isProbeAll
        ? {
            schema_version: 2,
            module: "all",
            updated_at: "2026-01-01T00:00:00Z",
            modules: { installation: { module: "installation" } },
          }
        : {
            ok: true,
            command: argv.join(" "),
            data: { hi: "there" },
            error: null,
          };
      cb(null, JSON.stringify(payload));
    }
  ),
}));

vi.mock("child_process", () => ({
  default: {
    execFile: mockExecFile,
    execFileSync: () => "Python 3.11.0",
    spawn: vi.fn(),
    exec: vi.fn(),
  },
  execFile: mockExecFile,
  execFileSync: () => "Python 3.11.0",
  spawn: vi.fn(),
  exec: vi.fn(),
}));

import { execFile } from "child_process";

const execFileMock = vi.mocked(execFile);

function lastArgv(): string[] {
  const call = execFileMock.mock.calls[execFileMock.mock.calls.length - 1];
  return call[1] as string[];
}

describe("read-model client argv contract (#161/R)", () => {
  beforeEach(() => {
    execFileMock.mockClear();
  });
  afterEach(() => {
    invalidateAll();
  });

  it("probeAll emits `paperforge probe all --json`", async () => {
    await probeAll("/vault", null);
    expect(lastArgv()).toEqual([
      "-m",
      "paperforge",
      "--vault",
      "/vault",
      "probe",
      "all",
      "--json",
    ]);
  });

  it("queryMemoryDetail emits `paperforge memory status --json`", async () => {
    await queryMemoryDetail("/vault", null);
    expect(lastArgv()).toEqual([
      "-m",
      "paperforge",
      "--vault",
      "/vault",
      "memory",
      "status",
      "--json",
    ]);
  });

  it("queryEmbedStatus emits `paperforge embed status --json`", async () => {
    await queryEmbedStatus("/vault", null);
    expect(lastArgv()).toEqual([
      "-m",
      "paperforge",
      "--vault",
      "/vault",
      "embed",
      "status",
      "--json",
    ]);
  });

  it("queryOcrPapers emits `paperforge ocr list --json`", async () => {
    await queryOcrPapers("/vault", null);
    expect(lastArgv()).toEqual([
      "-m",
      "paperforge",
      "--vault",
      "/vault",
      "ocr",
      "list",
      "--json",
    ]);
  });

  it("paperContext emits `paperforge paper-context <key> --json`", async () => {
    await paperContext("/vault", "KEY1", null);
    expect(lastArgv()).toEqual([
      "-m",
      "paperforge",
      "--vault",
      "/vault",
      "paper-context",
      "KEY1",
      "--json",
    ]);
  });

  it("config methods still route through the config subcommand (C0)", async () => {
    await configList("/vault", null);
    expect(lastArgv()).toEqual([
      "-m",
      "paperforge",
      "--vault",
      "/vault",
      "config",
      "list",
      "--json",
    ]);
  });

  it("typed methods return the PFResult data payload directly (no .data); probeAll returns the bare envelope", async () => {
    const data = await configList("/vault", null);
    expect(data).toEqual({ hi: "there" });
    expect((data as { data?: unknown }).data).toBeUndefined();
    const all = await probeAll("/vault", null);
    expect(all.module).toBe("all");
    expect(all.modules).toEqual({ installation: { module: "installation" } });
  });

  it("refreshAll invalidates then re-probes; invalidateAll clears the cache", async () => {
    await refreshAll("/vault", null);
    expect(lastArgv()).toEqual([
      "-m",
      "paperforge",
      "--vault",
      "/vault",
      "probe",
      "all",
      "--json",
    ]);
    invalidateAll();
    // invalidateAll is synchronous cache clearing; a subsequent probeAll
    // must not be short-circuited by any stale cache.
    await probeAll("/vault", null);
    expect(execFileMock).toHaveBeenCalledTimes(2);
  });
});

describe("resolvePythonExecutable passthrough", () => {
  it("keeps extraArgs before -m (managed runtime)", async () => {
    vi.mocked(resolvePythonExecutable).mockReturnValueOnce({
      path: "/fake/python",
      source: "managed",
      extraArgs: ["--flag"],
    });
    await queryEmbedStatus("/vault", null);
    expect(lastArgv()).toEqual([
      "--flag",
      "-m",
      "paperforge",
      "--vault",
      "/vault",
      "embed",
      "status",
      "--json",
    ]);
  });
});
