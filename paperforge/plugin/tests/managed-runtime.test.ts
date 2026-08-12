/**
 * Focused Vitest tests for ManagedRuntime (Issue #77).
 *
 * Covers: synchronous fail-closed, status probe/cache, Python version gating,
 * immutable slot build/activate, rollback, cancellation, atomic pointer,
 * platform detection, canonical actions, and command resolution.
 *
 * Uses dependency injection (constructor parameters) rather than vi.mock.
 * All paths are computed via the `path` module for OS portability.
 *
 * DI type pattern: each mock factory returns both the DI interface and
 * individual vi.fn() references stored in closures for mock control.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import * as path from "path";
import * as os from "os";
import * as fs from "fs";
import type { Dirent } from "fs";
import {
  ManagedRuntime,
  getOsArch,
  runtimeActionsForHealth,
  resolveRuntimeCommand,
} from "../src/services/managed-runtime";
import type {
  RuntimeHealth,
  FsOps,
  ExecFileFn,
  ExecFileSyncFn,
} from "../src/services/managed-runtime";

// ── OS-independent path constants ──
const RUNTIME_DIR = path.join("home", "user", ".paperforge", "runtime");
const POINTER_PATH = path.join(RUNTIME_DIR, "pointer.json");
const PLUGIN_VER = "1.3.0";

// ── Mock helper types (not exported, only used in tests) ──

interface MockFs extends FsOps {
  existsSync: ReturnType<typeof vi.fn<(p: string) => boolean>>;
  readFileSync: ReturnType<
    typeof vi.fn<(p: string, encoding?: string | null) => string>
  >;
  mkdirSync: ReturnType<
    typeof vi.fn<
      (p: string, opts?: { recursive?: boolean }) => string | undefined
    >
  >;
  rmSync: ReturnType<
    typeof vi.fn<
      (p: string, opts?: { recursive?: boolean; force?: boolean }) => void
    >
  >;
}

/** Create a mock FsOps with full mock-control access. */
function createMockFs(): MockFs {
  return {
    existsSync: vi.fn<(p: string) => boolean>(),
    readFileSync: vi.fn<(p: string, encoding?: string | null) => string>(),
    mkdirSync:
      vi.fn<
        (p: string, opts?: { recursive?: boolean }) => string | undefined
      >(),
    rmSync:
      vi.fn<
        (p: string, opts?: { recursive?: boolean; force?: boolean }) => void
      >(),
  };
}

// ExecFile mock type
type MockExecFile = ReturnType<typeof vi.fn<(...args: unknown[]) => void>>;

/** Create a mock ExecFileFn with mock control. Default: calls back with null error and probe version. */
function createMockExecFile(probeVersion: string): MockExecFile {
  const fn = vi.fn<(...args: unknown[]) => void>();
  fn.mockImplementation(
    (
      cmd: unknown,
      args: unknown,
      opts: unknown,
      cb: (err: Error | null, stdout: string, stderr: string) => void
    ) => {
      cb(null, probeVersion, "");
    }
  );
  return fn;
}

/** Create a failing mock ExecFileFn. */
function createFailingExecFile(errorMsg: string): MockExecFile {
  const fn = vi.fn<(...args: unknown[]) => void>();
  fn.mockImplementation(
    (
      _cmd: unknown,
      _args: unknown,
      _opts: unknown,
      cb: (err: Error | null, stdout: string, stderr: string) => void
    ) => {
      cb(new Error(errorMsg), "", "stderr");
    }
  );
  return fn;
}

/** Create a mock ExecFileSyncFn with mock control. Default: returns "Python 3.11.0". */
function createMockExecFileSync(pythonVersion: string): ExecFileSyncFn {
  return ((
    _cmd: string,
    _args: readonly string[],
    _opts: { encoding: string; timeout: number }
  ) => {
    return `Python ${pythonVersion}`;
  }) as ExecFileSyncFn;
}

/** Create a throwing mock ExecFileSyncFn. */
function createThrowingExecFileSync(): ExecFileSyncFn {
  return ((
    _cmd: string,
    _args: readonly string[],
    _opts: { encoding: string; timeout: number }
  ) => {
    throw new Error("Not found");
  }) as ExecFileSyncFn;
}

/** Create a minimal Dirent mock. */
function mkDirent(name: string, isDir = true): Dirent {
  return {
    name,
    isDirectory: () => isDir,
    isFile: () => !isDir,
    isBlockDevice: () => false,
    isCharacterDevice: () => false,
    isFIFO: () => false,
    isSocket: () => false,
    isSymbolicLink: () => false,
  } as unknown as Dirent;
}

/** Canonical single-venv python path (absolute, schema v1). */
function pythonPathFor(version: string): string {
  return path.join(RUNTIME_DIR, "venv", "Scripts", "python.exe");
}

/** Default pointer.json content (#174 schema v1, published by Python). */
function defaultPointer(version = "1.3.0"): string {
  return JSON.stringify({
    schema_version: 1,
    python_path: pythonPathFor(version),
    environment_root: path.join(RUNTIME_DIR, "venv"),
    paperforge_version: version,
  });
}

/** Normalise a path for comparison (handles Windows backslash vs forward slash). */
function normalisePath(p: string): string {
  return p.replace(/\\/g, "/");
}

// ── Tests ──

describe("ManagedRuntime", () => {
  // ── current(): synchronous fail-closed ──
  describe("current()", () => {
    it("returns unknown stale on cold cache (fail-closed, no silent ambient interpreter)", () => {
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(false);
      fs.readFileSync.mockReturnValue("");

      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: PLUGIN_VER,
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: createMockExecFile("1.3.0") as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.11.0"
        ) as unknown as ExecFileSyncFn,
      });

      const h = rt.current();
      expect(h.state).toBe("unknown");
      expect(h.pythonPath).toBeNull();
      expect(h.stale).toBe(true);
      expect(h.lastVerifiedAt).toBeNull();
    });

    it("never returns ready from stale cache — returns unknown with stale:true", async () => {
      const fs = createMockFs();
      setupDefaultMockFs(fs, "1.3.0");

      const execFile = createMockExecFile("1.3.0");
      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: PLUGIN_VER,
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: execFile as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.11.0"
        ) as unknown as ExecFileSyncFn,
      });
      await rt.status();

      const h1 = rt.current();
      expect(h1.state).toBe("ready");
      expect(h1.stale).toBe(false);

      vi.useFakeTimers();
      vi.advanceTimersByTime(5 * 60 * 1000 + 1);

      const h2 = rt.current();
      expect(h2.state).toBe("unknown");
      expect(h2.stale).toBe(true);
      expect(h2.pythonPath).toBe(h1.pythonPath);
      expect(h2.version).toBe(h1.version);

      vi.useRealTimers();
    });

    it("returns cached ready when within TTL", async () => {
      const fs = createMockFs();
      setupDefaultMockFs(fs, "1.3.0");

      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: PLUGIN_VER,
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: createMockExecFile("1.3.0") as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.11.0"
        ) as unknown as ExecFileSyncFn,
      });
      await rt.status();

      const h = rt.current();
      expect(h.state).toBe("ready");
      expect(h.stale).toBe(false);
    });
  });

  // ── status(): async probe ──
  describe("status()", () => {
    it("returns not_installed when no pointer file exists", async () => {
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(false);
      fs.readFileSync.mockReturnValue("");

      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: PLUGIN_VER,
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: createMockExecFile("1.3.0") as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.11.0"
        ) as unknown as ExecFileSyncFn,
      });

      const h = await rt.status();
      expect(h.state).toBe("not_installed");
      expect(h.pythonPath).toBeNull();
      expect(h.version).toBeNull();
      expect(h.stale).toBe(false);
    });

    it("returns ready when probe passes", async () => {
      const fs = createMockFs();
      setupDefaultMockFs(fs, "1.3.0");

      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: PLUGIN_VER,
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: createMockExecFile("1.3.0") as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.11.0"
        ) as unknown as ExecFileSyncFn,
      });

      const h = await rt.status();
      expect(h.state).toBe("ready");
      expect(h.pythonPath).toBeTruthy();
      expect(h.version).toBe("1.3.0");
      expect(h.source).toBe("venv");
      expect(h.error).toBeNull();
      expect(h.stale).toBe(false);
      expect(h.lastVerifiedAt).toBeTruthy();
    });

    it("returns needs_repair when probe fails", async () => {
      const fs = createMockFs();
      setupDefaultMockFs(fs, "1.3.0");

      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: PLUGIN_VER,
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: createFailingExecFile(
          "Probe failed"
        ) as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.11.0"
        ) as unknown as ExecFileSyncFn,
      });

      const h = await rt.status();
      expect(h.state).toBe("needs_repair");
      expect(h.error?.code).toBe("PROBE_FAILED");
      expect(h.stale).toBe(false);
    });

    it("returns needs_repair when python not found at pointer path", async () => {
      const fs = createMockFs();
      setupDefaultMockFs(fs, "1.3.0");
      // Override — python exe doesn't exist
      const resolvedPy = path.resolve(pythonPathFor("1.3.0"));
      fs.existsSync.mockImplementation((p: string) => {
        if (normalisePath(p) === normalisePath(resolvedPy)) return false;
        return true;
      });

      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: PLUGIN_VER,
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: createMockExecFile("1.3.0") as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.11.0"
        ) as unknown as ExecFileSyncFn,
      });

      const h = await rt.status();
      expect(h.state).toBe("needs_repair");
      expect(h.error?.code).toBe("PYTHON_NOT_FOUND");
    });

    it("returns stale cached health with stale:true when allowStale and expired", async () => {
      const fs = createMockFs();
      setupDefaultMockFs(fs, "1.3.0");

      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: PLUGIN_VER,
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: createMockExecFile("1.3.0") as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.11.0"
        ) as unknown as ExecFileSyncFn,
      });
      await rt.status(); // populate cache

      vi.useFakeTimers();
      vi.advanceTimersByTime(5 * 60 * 1000 + 1);

      const h = await rt.status({ allowStale: true });
      expect(h.stale).toBe(true);
      expect(h.state).toBe("ready");
      expect(h.pythonPath).toBeTruthy();

      vi.useRealTimers();
    });

    it("returns needs_repair when pointer has no pythonPath", async () => {
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(true);
      fs.readFileSync.mockReturnValue(
        JSON.stringify({
          schema_version: 1,
          version: "1.3.0",
          pythonPath: null,
        })
      );

      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: PLUGIN_VER,
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: createMockExecFile("1.3.0") as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.11.0"
        ) as unknown as ExecFileSyncFn,
      });

      const h = await rt.status();
      expect(h.state).toBe("needs_repair");
      expect(h.error?.code).toBe("POINTER_MISSING_PATH");
    });
  });

  // ── ensure(): build, verify, activate ──
  describe("ensure()", () => {
    it("creates ONE venv, ONE pinned install, verifies, and does NOT write the pointer", async () => {
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(true);
      fs.readFileSync.mockReturnValue(""); // no existing pointer

      const execFile = createMockExecFile("1.3.0");
      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: "1.3.0",
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: execFile as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.11.0"
        ) as unknown as ExecFileSyncFn,
      });

      const h = await rt.ensure();
      expect(h.state).toBe("ready");
      expect(h.version).toBe("1.3.0");
      expect(h.source).toBe("venv");
      expect(h.error).toBeNull();

      // #174: the plugin never writes the pointer — Python publishes it.
      expect(fs.mkdirSync).toHaveBeenCalledWith(
        expect.stringContaining("venv"),
        expect.anything()
      );
      // venv + pip install + verify = 3 execFile calls
      const cmds = execFile.mock.calls.map((c) => c[0] as string);
      expect(cmds.length).toBe(3);
      expect(cmds[1]).toContain("python.exe");
      const pipArgs = execFile.mock.calls[1][1] as string[];
      expect(pipArgs.join(" ")).toContain("paperforge[vector]==1.3.0");
    });

    it("cancellation returns needs_repair", async () => {
      const ac = new AbortController();
      ac.abort();

      const fs = createMockFs();
      setupDefaultMockFs(fs, "1.3.0");

      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: PLUGIN_VER,
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: createMockExecFile("1.3.0") as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.11.0"
        ) as unknown as ExecFileSyncFn,
      });

      const h = await rt.ensure({ signal: ac.signal });
      expect(h.state).toBe("needs_repair");
      expect(h.error?.code).toBe("ABORTED");
    });

    it("forces a reinstall into the SAME single venv", async () => {
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(true);
      fs.readFileSync.mockImplementation((p: string) => {
        if (normalisePath(p) === normalisePath(POINTER_PATH))
          return defaultPointer("1.3.0");
        return "";
      });

      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: "1.3.0",
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: createMockExecFile("1.3.0") as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.11.0"
        ) as unknown as ExecFileSyncFn,
      });

      const h = await rt.ensure({ force: true, version: "1.3.0" });
      expect(h.state).toBe("ready");
    });

    it("venv creation failure cleans up and returns needs_repair", async () => {
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(true);
      fs.readFileSync.mockImplementation((p: string) => {
        if (normalisePath(p) === normalisePath(POINTER_PATH))
          return defaultPointer();
        return "";
      });

      const execFile = vi.fn<(...args: unknown[]) => void>();
      execFile.mockImplementation(
        (
          _cmd: unknown,
          _args: unknown,
          _opts: unknown,
          cb: (err: Error | null, stdout: string, stderr: string) => void
        ) => {
          cb(new Error("venv creation failed"), "", "error");
        }
      );

      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: "1.3.0",
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: execFile as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.11.0"
        ) as unknown as ExecFileSyncFn,
      });

      const h = await rt.ensure();
      expect(h.state).toBe("needs_repair");
      expect(h.error?.code).toBe("VENV_CREATION_FAILED");
      expect(fs.rmSync).toHaveBeenCalled();
    });

    it("pip install failure returns needs_repair with PIP_INSTALL_FAILED", async () => {
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(true);
      fs.readFileSync.mockReturnValue("");

      const callLog: Array<{ cmd: string; args: readonly string[] }> = [];
      const execFile = vi.fn<(...args: unknown[]) => void>();
      execFile.mockImplementation(
        (
          cmd: unknown,
          args: unknown,
          _opts: unknown,
          cb: (err: Error | null, stdout: string, stderr: string) => void
        ) => {
          const a = args as readonly string[];
          callLog.push({ cmd: cmd as string, args: a });
          if (a[0] === "-m" && a[1] === "venv") {
            cb(null, "", "");
          } else if (a[0] === "-m" && a[1] === "pip") {
            cb(new Error("pip install failed"), "", "error");
          } else {
            cb(null, "", "");
          }
        }
      );

      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: "1.3.0",
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: execFile as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.11.0"
        ) as unknown as ExecFileSyncFn,
      });

      const h = await rt.ensure();
      expect(h.error?.code).toBe("PIP_INSTALL_FAILED");
      expect(h.state).toBe("needs_repair");
      expect(fs.rmSync).toHaveBeenCalled();
    });

    it("status() returns ready for valid existing install regardless of Python 3.x version", async () => {
      // status() checks the installed runtime, not bootstrap version;
      // version gating is enforced by ensure() at build/repair time.
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(true);
      fs.readFileSync.mockImplementation((p: string) => {
        if (normalisePath(p) === normalisePath(POINTER_PATH))
          return defaultPointer("1.2.3");
        return "";
      });

      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: "1.3.0",
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: createMockExecFile("1.2.3") as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.11.0"
        ) as unknown as ExecFileSyncFn,
      });

      const h = await rt.status();
      expect(h.state).toBe("ready");
      expect(h.warnings).toEqual([]);
    });

    it("rejects ensure() with Python below 3.11", async () => {
      const fs = createMockFs();
      fs.existsSync.mockImplementation((p: string) => {
        if (normalisePath(p) === normalisePath(POINTER_PATH)) return true;
        if (p.includes(path.join("venv"))) return false;
        return true;
      });
      fs.readFileSync.mockReturnValue("");

      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: "1.3.0",
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: createMockExecFile("1.3.0") as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.10.0"
        ) as unknown as ExecFileSyncFn,
      });

      const h = await rt.ensure();
      expect(h.state).toBe("unavailable");
      expect(h.error?.code).toBe("PYTHON_TOO_OLD");
    });

    it("rejects ensure() with Python 3.9", async () => {
      const fs = createMockFs();
      fs.existsSync.mockImplementation((p: string) => {
        if (normalisePath(p) === normalisePath(POINTER_PATH)) return true;
        if (p.includes(path.join("venv"))) return false;
        return true;
      });
      fs.readFileSync.mockReturnValue("");

      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: "1.3.0",
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: createMockExecFile("1.3.0") as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.9.0"
        ) as unknown as ExecFileSyncFn,
      });

      const h = await rt.ensure();
      expect(h.state).toBe("unavailable");
      expect(h.error?.code).toBe("PYTHON_TOO_OLD");
    });
  });

  // ── Platform support ──
  describe("Platform support", () => {
    beforeEach(() => {
      delete process.env.FLATPAK_ID;
      delete process.env.SNAP;
    });

    it("macOS reports unavailable with NO_PYTHON (auto-download disabled)", async () => {
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(false);
      const execFileSync =
        vi.fn<
          (
            cmd: string,
            args: readonly string[],
            opts: { encoding: string; timeout: number }
          ) => string
        >();
      execFileSync.mockImplementation(() => {
        throw new Error("Not found");
      });
      const execFile = vi.fn<(...args: unknown[]) => void>();
      execFile.mockImplementation(
        (
          _cmd: unknown,
          _args: unknown,
          _opts: unknown,
          cb: (err: Error | null, stdout: string, stderr: string) => void
        ) => {
          cb(null, "1.3.0", "");
        }
      );
      const rt = new ManagedRuntime({
        runtimeDir: path.join(
          "home",
          "user",
          ".paperforge",
          "runtime",
          "macos-arm64"
        ),
        pluginVersion: "1.3.0",
        osPlatform: "darwin",
        osArch: "arm64",
        fs: fs as unknown as FsOps,
        execFile: execFile as unknown as ExecFileFn,
        execFileSync: execFileSync as unknown as ExecFileSyncFn,
      });
      const h = await rt.ensure();
      expect(h.state).toBe("unavailable");
      expect(h.error?.code).toBe("NO_PYTHON");
      expect(h.error?.message).toContain("macOS auto-download disabled");
    });

    it("macOS x64 also reports unavailable (system Python not found)", async () => {
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(false);
      const execFileSync =
        vi.fn<
          (
            cmd: string,
            args: readonly string[],
            opts: { encoding: string; timeout: number }
          ) => string
        >();
      execFileSync.mockImplementation(() => {
        throw new Error("Not found");
      });
      const execFile = vi.fn<(...args: unknown[]) => void>();
      execFile.mockImplementation(
        (
          _cmd: unknown,
          _args: unknown,
          _opts: unknown,
          cb: (err: Error | null, stdout: string, stderr: string) => void
        ) => {
          cb(null, "1.3.0", "");
        }
      );
      const rt = new ManagedRuntime({
        runtimeDir: path.join(
          "home",
          "user",
          ".paperforge",
          "runtime",
          "macos-x64"
        ),
        pluginVersion: "1.3.0",
        osPlatform: "darwin",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: execFile as unknown as ExecFileFn,
        execFileSync: execFileSync as unknown as ExecFileSyncFn,
      });
      const h = await rt.ensure();
      expect(h.state).toBe("unavailable");
      expect(h.error?.code).toBe("NO_PYTHON");
      expect(h.error?.message).toContain("macOS auto-download disabled");
    });

    it("Windows validated fallback returns NO_PYTHON with manual instruction when bootstrap fails", async () => {
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(false);
      const execFileSync =
        vi.fn<
          (
            cmd: string,
            args: readonly string[],
            opts: { encoding: string; timeout: number }
          ) => string
        >();
      execFileSync.mockImplementation(() => {
        throw new Error("Not found");
      });
      const execFile = vi.fn<(...args: unknown[]) => void>();
      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: "1.3.0",
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: execFile as unknown as ExecFileFn,
        execFileSync: execFileSync as unknown as ExecFileSyncFn,
      });
      const h = await rt.ensure();
      expect(h.state).toBe("unavailable");
      expect(h.error?.code).toBe("NO_PYTHON");
      expect(h.error?.message).toContain("automatic download failed");
    });

    it("Linux validated fallback returns NO_PYTHON with manual instruction", async () => {
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(false);
      const execFileSync =
        vi.fn<
          (
            cmd: string,
            args: readonly string[],
            opts: { encoding: string; timeout: number }
          ) => string
        >();
      execFileSync.mockImplementation(() => {
        throw new Error("Not found");
      });
      const execFile = vi.fn<(...args: unknown[]) => void>();
      const rt = new ManagedRuntime({
        runtimeDir: path.join(
          "home",
          "user",
          ".paperforge",
          "runtime",
          "linux-x64"
        ),
        pluginVersion: "1.3.0",
        osPlatform: "linux",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: execFile as unknown as ExecFileFn,
        execFileSync: execFileSync as unknown as ExecFileSyncFn,
      });
      const h = await rt.ensure();
      expect(h.state).toBe("unavailable");
      expect(h.error?.code).toBe("NO_PYTHON");
    });

    it("unsupported triplet returns FALLBACK_UNAVAILABLE", async () => {
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(false);
      const execFileSync =
        vi.fn<
          (
            cmd: string,
            args: readonly string[],
            opts: { encoding: string; timeout: number }
          ) => string
        >();
      execFileSync.mockImplementation(() => {
        throw new Error("Not found");
      });
      const execFile = vi.fn<(...args: unknown[]) => void>();
      const rt = new ManagedRuntime({
        runtimeDir: path.join(
          "home",
          "user",
          ".paperforge",
          "runtime",
          "linux-arm64"
        ),
        pluginVersion: "1.3.0",
        osPlatform: "linux",
        osArch: "arm64",
        fs: fs as unknown as FsOps,
        execFile: execFile as unknown as ExecFileFn,
        execFileSync: execFileSync as unknown as ExecFileSyncFn,
      });
      const h = await rt.ensure();
      expect(h.state).toBe("unavailable");
      expect(h.error?.code).toBe("FALLBACK_UNAVAILABLE");
    });

    it("Flatpak environment returns FLATPAK_SNAP_UNSUPPORTED", async () => {
      process.env.FLATPAK_ID = "org.flatpak.Flatpak";
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(false);
      const execFileSync =
        vi.fn<
          (
            cmd: string,
            args: readonly string[],
            opts: { encoding: string; timeout: number }
          ) => string
        >();
      execFileSync.mockImplementation(() => {
        throw new Error("Not found");
      });
      const execFile = vi.fn<(...args: unknown[]) => void>();
      const rt = new ManagedRuntime({
        runtimeDir: path.join(
          "home",
          "user",
          ".paperforge",
          "runtime",
          "linux-x64"
        ),
        pluginVersion: "1.3.0",
        osPlatform: "linux",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: execFile as unknown as ExecFileFn,
        execFileSync: execFileSync as unknown as ExecFileSyncFn,
      });
      const h = await rt.ensure();
      expect(h.state).toBe("unavailable");
      expect(h.error?.code).toBe("FLATPAK_SNAP_UNSUPPORTED");
    });

    it("Snap environment returns FLATPAK_SNAP_UNSUPPORTED", async () => {
      process.env.SNAP = "/snap/core/current";
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(false);
      const execFileSync =
        vi.fn<
          (
            cmd: string,
            args: readonly string[],
            opts: { encoding: string; timeout: number }
          ) => string
        >();
      execFileSync.mockImplementation(() => {
        throw new Error("Not found");
      });
      const execFile = vi.fn<(...args: unknown[]) => void>();
      const rt = new ManagedRuntime({
        runtimeDir: path.join(
          "home",
          "user",
          ".paperforge",
          "runtime",
          "linux-x64"
        ),
        pluginVersion: "1.3.0",
        osPlatform: "linux",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: execFile as unknown as ExecFileFn,
        execFileSync: execFileSync as unknown as ExecFileSyncFn,
      });
      const h = await rt.ensure();
      expect(h.state).toBe("unavailable");
      expect(h.error?.code).toBe("FLATPAK_SNAP_UNSUPPORTED");
    });
  });

  // ── Pointer content ──
  describe("Pointer content", () => {
    it("reads ONLY the Python-published schema v1 — machine-local interpreter paths, no credentials or vault paths", async () => {
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(true);
      fs.readFileSync.mockImplementation((p: string) => {
        if (normalisePath(p) === normalisePath(POINTER_PATH))
          return defaultPointer();
        return "";
      });

      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: "1.3.0",
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: createMockExecFile("1.3.0") as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.11.0"
        ) as unknown as ExecFileSyncFn,
      });

      const h = await rt.status();
      expect(h.state).toBe("ready");
      expect(h.pythonPath).toBe(path.resolve(pythonPathFor("1.3.0")));
      expect(h.version).toBe("1.3.0");
      expect(h.pythonPath).not.toContain("vault");
      expect(h.pythonPath).not.toContain("credential");
      expect(h.pythonPath).not.toContain("secret");
    });

    it("rejects an unsupported pointer schema as not_installed (fail-closed)", async () => {
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(true);
      fs.readFileSync.mockReturnValue(
        JSON.stringify({ schema_version: 99, python_path: "/x" })
      );

      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: "1.3.0",
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: createMockExecFile("1.3.0") as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.11.0"
        ) as unknown as ExecFileSyncFn,
      });

      const h = await rt.status();
      expect(h.state).toBe("not_installed");
    });
  });

  // ── getOsArch helper ──
  describe("getOsArch", () => {
    it("maps win32-x64 to windows-x64", () => {
      expect(getOsArch("win32", "x64")).toBe("windows-x64");
    });

    it("maps darwin-arm64 to macos-arm64", () => {
      expect(getOsArch("darwin", "arm64")).toBe("macos-arm64");
    });

    it("maps darwin-x64 to macos-x64", () => {
      expect(getOsArch("darwin", "x64")).toBe("macos-x64");
    });

    it("maps linux-x64 to linux-x64", () => {
      expect(getOsArch("linux", "x64")).toBe("linux-x64");
    });
  });

  // ── runtimeActionsForHealth ──
  describe("runtimeActionsForHealth", () => {
    function health(
      overrides: Partial<RuntimeHealth> & { state: RuntimeHealth["state"] }
    ): RuntimeHealth {
      return {
        state: overrides.state,
        pythonPath: overrides.pythonPath ?? null,
        version: overrides.version ?? null,
        source: overrides.source ?? "none",
        error: overrides.error ?? null,
        lastVerifiedAt: overrides.lastVerifiedAt ?? null,
        stale: overrides.stale ?? false,
      };
    }

    it("not_installed → install action (primary)", () => {
      const acts = runtimeActionsForHealth(health({ state: "not_installed" }));
      expect(acts).toHaveLength(1);
      expect(acts[0].id).toBe("install");
      expect(acts[0].primary).toBe(true);
      expect(acts[0].destructive).toBe(false);
    });

    it("needs_repair with pythonPath → repair only (rollback deleted, #174)", () => {
      const acts = runtimeActionsForHealth(
        health({ state: "needs_repair", pythonPath: "/usr/bin/python" })
      );
      expect(acts).toHaveLength(1);
      expect(acts[0].id).toBe("repair");
      expect(acts[0].primary).toBe(true);
    });

    it("needs_repair without pythonPath → repair only", () => {
      const acts = runtimeActionsForHealth(health({ state: "needs_repair" }));
      expect(acts).toHaveLength(1);
      expect(acts[0].id).toBe("repair");
    });

    it("ready → status + update", () => {
      const acts = runtimeActionsForHealth(health({ state: "ready" }));
      expect(acts).toHaveLength(2);
      expect(acts[0].id).toBe("status");
      expect(acts[1].id).toBe("update");
    });

    it("unknown → probe (primary)", () => {
      const acts = runtimeActionsForHealth(health({ state: "unknown" }));
      expect(acts).toHaveLength(1);
      expect(acts[0].id).toBe("probe");
      expect(acts[0].primary).toBe(true);
    });

    it("unavailable → setup (primary)", () => {
      const acts = runtimeActionsForHealth(health({ state: "unavailable" }));
      expect(acts).toHaveLength(1);
      expect(acts[0].id).toBe("setup");
      expect(acts[0].primary).toBe(true);
    });
  });

  // ── resolveRuntimeCommand ──
  describe("resolveRuntimeCommand", () => {
    it("returns command only when ready and pythonPath set", () => {
      const result = resolveRuntimeCommand({
        state: "ready",
        pythonPath: path.join(
          "home",
          "user",
          ".paperforge",
          "runtime",
          "windows-x64",
          "v1.3.0",
          "venv",
          "Scripts",
          "python.exe"
        ),
        version: "1.3.0",
        source: "venv",
        error: null,
        lastVerifiedAt: "2026-07-15T00:00:00Z",
        stale: false,
      });
      expect(result).not.toBeNull();
      expect(result!.command).toContain("python.exe");
    });

    it("returns null when not ready", () => {
      const result = resolveRuntimeCommand({
        state: "not_installed",
        pythonPath: null,
        version: null,
        source: "none",
        error: null,
        lastVerifiedAt: null,
        stale: false,
      });
      expect(result).toBeNull();
    });

    it("returns null when ready but no pythonPath", () => {
      const result = resolveRuntimeCommand({
        state: "ready",
        pythonPath: null,
        version: null,
        source: "none",
        error: null,
        lastVerifiedAt: null,
        stale: false,
      });
      expect(result).toBeNull();
    });
  });
});

// ── Real filesystem slot retention tests ──

/** Create a slot directory structure for real-FS tests. */
describe("Real filesystem single venv (#174)", () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "mr-single-venv-"));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it("ensure() creates ONE venv and never writes a pointer (Python owns publication)", async () => {
    const rt = new ManagedRuntime({
      runtimeDir: tmpDir,
      pluginVersion: "1.4.0",
      osPlatform: "win32",
      osArch: "x64",
      execFile: createMockExecFile("1.4.0") as unknown as ExecFileFn,
      execFileSync: createMockExecFileSync(
        "3.11.0"
      ) as unknown as ExecFileSyncFn,
    });

    const h = await rt.ensure({ version: "1.4.0" });
    expect(h.state).toBe("ready");
    expect(h.version).toBe("1.4.0");

    // ONE venv dir, no version-slot dirs, no pointer.json (TS never writes).
    expect(fs.existsSync(path.join(tmpDir, "venv"))).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, "pointer.json"))).toBe(false);
    expect(fs.readdirSync(tmpDir).some((n) => /^v\\d/.test(n))).toBe(false);
  });
});

// ── Shared helper ──

/** Set up a default MockFs that returns valid pointer content. */
function setupDefaultMockFs(fs: MockFs, version: string): void {
  fs.existsSync.mockReturnValue(true);
  fs.readFileSync.mockImplementation((p: string) => {
    if (normalisePath(p) === normalisePath(POINTER_PATH))
      return defaultPointer(version);
    return "";
  });
}
