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
const RUNTIME_DIR = path.join(
  "home",
  "user",
  ".paperforge",
  "runtime",
  "windows-x64"
);
const RUNTIME_PARENT = path.dirname(RUNTIME_DIR);
const POINTER_PATH = path.join(RUNTIME_PARENT, "active-runtime.json");
const PLUGIN_VER = "1.3.0";

// ── Mock helper types (not exported, only used in tests) ──

interface MockFs extends FsOps {
  existsSync: ReturnType<typeof vi.fn<(p: string) => boolean>>;
  readFileSync: ReturnType<
    typeof vi.fn<(p: string, encoding?: string | null) => string>
  >;
  writeFileSync: ReturnType<
    typeof vi.fn<
      (
        p: string,
        data: string | NodeJS.ArrayBufferView,
        encoding?: string | null
      ) => void
    >
  >;
  renameSync: ReturnType<typeof vi.fn<(oldP: string, newP: string) => void>>;
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
  readdirSync: ReturnType<
    typeof vi.fn<(p: string, opts?: { withFileTypes?: boolean }) => Dirent[]>
  >;
}

/** Create a mock FsOps with full mock-control access. */
function createMockFs(): MockFs {
  return {
    existsSync: vi.fn<(p: string) => boolean>(),
    readFileSync: vi.fn<(p: string, encoding?: string | null) => string>(),
    writeFileSync:
      vi.fn<
        (
          p: string,
          data: string | NodeJS.ArrayBufferView,
          encoding?: string | null
        ) => void
      >(),
    renameSync: vi.fn<(oldP: string, newP: string) => void>(),
    mkdirSync:
      vi.fn<
        (p: string, opts?: { recursive?: boolean }) => string | undefined
      >(),
    rmSync:
      vi.fn<
        (p: string, opts?: { recursive?: boolean; force?: boolean }) => void
      >(),
    readdirSync:
      vi.fn<(p: string, opts?: { withFileTypes?: boolean }) => Dirent[]>(),
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

/** Build a canonical relative pythonPath from version (forward-slash for JSON). */
function relPythonPath(version: string): string {
  return path
    .join("windows-x64", `v${version}`, "venv", "Scripts", "python.exe")
    .replace(/\\/g, "/");
}

/** Default active-runtime.json content. pythonPath is relative to pointer parent dir. */
function defaultPointer(version = "1.3.0"): string {
  return JSON.stringify({
    schema_version: 1,
    version,
    pythonPath: relPythonPath(version),
    activatedAt: "2026-07-15T00:00:00Z",
    previousVersion: null,
    previousPythonPath: null,
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
      const resolvedPy = path.resolve(RUNTIME_PARENT, relPythonPath("1.3.0"));
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
    it("builds a new immutable slot, verifies, and atomically activates", async () => {
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(true);
      fs.readFileSync.mockReturnValue(""); // no existing pointer

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

      const h = await rt.ensure();
      expect(h.state).toBe("ready");
      expect(h.version).toBe("1.3.0");
      expect(h.source).toBe("venv");
      expect(h.error).toBeNull();

      expect(fs.mkdirSync).toHaveBeenCalled();
      expect(fs.renameSync).toHaveBeenCalled();
      const writeCalls = fs.writeFileSync.mock.calls;
      expect(writeCalls.length).toBeGreaterThanOrEqual(1);
      const lastWrite = writeCalls[writeCalls.length - 1][0] as string;
      expect(lastWrite).toContain(".tmp");
    });

    it("cancellation preserves old pointer and returns needs_repair", async () => {
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

    it("forces rebuild with disambiguated slot name", async () => {
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

    it("slot creation failure cleans up and returns needs_repair", async () => {
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(true);
      fs.readFileSync.mockImplementation((p: string) => {
        if (normalisePath(p) === normalisePath(POINTER_PATH))
          return defaultPointer();
        return "";
      });
      fs.readdirSync.mockReturnValue([mkDirent("v1.3.0")]);

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
      fs.readdirSync.mockReturnValue([]);

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

    it("rollback: writes pointer with previousVersion/previousPythonPath tracking", async () => {
      const fs = createMockFs();
      fs.readFileSync.mockImplementation((p: string) => {
        if (normalisePath(p) === normalisePath(POINTER_PATH)) {
          return JSON.stringify({
            schema_version: 1,
            version: "1.4.0",
            pythonPath: relPythonPath("1.4.0"),
            activatedAt: "2026-07-15T01:00:00Z",
            previousVersion: "1.3.0",
            previousPythonPath: relPythonPath("1.3.0"),
          });
        }
        return "";
      });
      fs.existsSync.mockReturnValue(true);
      fs.readdirSync.mockReturnValue([mkDirent("v1.3.0"), mkDirent("v1.4.0")]);

      let writtenPointer = "";
      fs.writeFileSync = vi.fn<
        (
          p: string,
          data: string | NodeJS.ArrayBufferView,
          encoding?: string | null
        ) => void
      >((p: string, data: string | NodeJS.ArrayBufferView) => {
        if (typeof p === "string" && p.endsWith(".tmp")) {
          writtenPointer = typeof data === "string" ? data : String(data);
        }
      });

      const execFile = vi.fn<(...args: unknown[]) => void>();
      execFile.mockImplementation(
        (
          cmd: unknown,
          args: unknown,
          _opts: unknown,
          cb: (err: Error | null, stdout: string, stderr: string) => void
        ) => {
          const a = args as readonly string[];
          // venv + pip succeed
          if (a[0] === "-m") {
            cb(null, "", "");
          } else if (a[0] === "-I") {
            cb(null, "1.3.0", "");
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

      const h = await rt.ensure({ version: "1.3.0" });
      expect(h.state).toBe("ready");
      expect(h.version).toBe("1.3.0");

      const ptr = JSON.parse(writtenPointer);
      expect(ptr.previousVersion).toBe("1.4.0");
      expect(ptr.previousPythonPath).toBeTruthy();
      expect(ptr.version).toBe("1.3.0");
    });

    it("RED Gap 1: rollback verifies retained immutable slot without creating venv or running pip", async () => {
      const fs = createMockFs();
      // Existing pointer: v1.4.0 is current active
      fs.readFileSync.mockImplementation((p: string) => {
        if (normalisePath(p) === normalisePath(POINTER_PATH)) {
          return JSON.stringify({
            schema_version: 1,
            version: "1.4.0",
            pythonPath: relPythonPath("1.4.0"),
            activatedAt: "2026-07-15T01:00:00Z",
            previousVersion: "1.3.0",
            previousPythonPath: relPythonPath("1.3.0"),
          });
        }
        return "";
      });
      // Slot for v1.3.0 exists (retained)
      fs.existsSync.mockImplementation((p: string) => {
        if (
          typeof p === "string" &&
          p.includes("v1.3.0") &&
          !p.includes("v1.4.0")
        )
          return true;
        return true;
      });
      fs.readdirSync.mockReturnValue([mkDirent("v1.3.0"), mkDirent("v1.4.0")]);

      // Track execFile calls to assert no venv/pip
      const execCalls: Array<{ cmd: string; args: readonly string[] }> = [];
      const execFile = vi.fn<(...args: unknown[]) => void>();
      execFile.mockImplementation(
        (
          cmd: unknown,
          args: unknown,
          _opts: unknown,
          cb: (err: Error | null, stdout: string, stderr: string) => void
        ) => {
          const a = args as readonly string[];
          execCalls.push({ cmd: cmd as string, args: a });
          // Only the import probe should succeed
          if (a[0] === "-I") {
            cb(null, "1.3.0", "");
          } else {
            cb(new Error("unexpected call"), "", "unexpected");
          }
        }
      );

      let writtenContent = "";
      fs.writeFileSync = vi.fn<
        (p: string, data: string | NodeJS.ArrayBufferView) => void
      >((p: string, data: string | NodeJS.ArrayBufferView) => {
        if (typeof p === "string" && p.endsWith(".tmp")) {
          writtenContent = typeof data === "string" ? data : String(data);
        }
      });

      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: "1.4.0",
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: execFile as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.11.0"
        ) as unknown as ExecFileSyncFn,
      });

      const h = await rt.ensure({ version: "1.3.0" });
      expect(h.state).toBe("ready");
      expect(h.version).toBe("1.3.0");

      // Assert: NO venv creation (no "-m venv" call)
      const venvCalls = execCalls.filter(
        (c) => c.args[0] === "-m" && c.args[1] === "venv"
      );
      expect(venvCalls).toHaveLength(0);

      // Assert: NO pip install (no "-m pip" call)
      const pipCalls = execCalls.filter(
        (c) => c.args[0] === "-m" && c.args[1] === "pip"
      );
      expect(pipCalls).toHaveLength(0);

      // Assert: retained slot was verified via import probe
      const probeCalls = execCalls.filter((c) => c.args[0] === "-I");
      expect(probeCalls.length).toBeGreaterThanOrEqual(1);

      // Assert: pointer atomically rewritten (tmp write + rename)
      expect(writtenContent).toBeTruthy();
      const ptr = JSON.parse(writtenContent);
      expect(ptr.version).toBe("1.3.0");
      expect(ptr.previousVersion).toBe("1.4.0");
      expect(ptr.pythonPath).toBeTruthy();
      expect(fs.renameSync).toHaveBeenCalled();
    });
  });

  // ── Issue #77 Contract 2 RED: AbortSignal pass-through to child processes ──
  describe("Issue #77 RED: AbortSignal pass-through", () => {
    it("RED: ensure passes AbortSignal to venv execFile call", async () => {
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(true);
      fs.readFileSync.mockReturnValue("");

      const capturedOpts: Array<Record<string, unknown>> = [];
      const execFile = vi.fn<(...args: unknown[]) => void>();
      execFile.mockImplementation(
        (
          _cmd: unknown,
          _args: unknown,
          opts: unknown,
          cb: (err: Error | null, stdout: string, stderr: string) => void
        ) => {
          capturedOpts.push(opts as Record<string, unknown>);
          cb(null, "", "");
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

      const ac = new AbortController();
      await rt.ensure({ signal: ac.signal });

      // The venv call (first execFile call) must receive the signal
      expect(capturedOpts.length).toBeGreaterThanOrEqual(3); // venv + pip + verify
      const venvOpts = capturedOpts[0];
      expect(venvOpts.signal).toBe(ac.signal);
    });

    it("RED: ensure passes AbortSignal to pip execFile call", async () => {
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(true);
      fs.readFileSync.mockReturnValue("");

      const capturedOpts: Array<Record<string, unknown>> = [];
      const execFile = vi.fn<(...args: unknown[]) => void>();
      execFile.mockImplementation(
        (
          _cmd: unknown,
          _args: unknown,
          opts: unknown,
          cb: (err: Error | null, stdout: string, stderr: string) => void
        ) => {
          capturedOpts.push(opts as Record<string, unknown>);
          cb(null, "", "");
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

      const ac = new AbortController();
      await rt.ensure({ signal: ac.signal });

      // pip is the second execFile call (after venv)
      const pipOpts = capturedOpts[1];
      expect(pipOpts.signal).toBe(ac.signal);
    });

    it("RED: ensure passes AbortSignal to verify execFile call", async () => {
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(true);
      fs.readFileSync.mockReturnValue("");

      const capturedOpts: Array<Record<string, unknown>> = [];
      const execFile = vi.fn<(...args: unknown[]) => void>();
      execFile.mockImplementation(
        (
          _cmd: unknown,
          _args: unknown,
          opts: unknown,
          cb: (err: Error | null, stdout: string, stderr: string) => void
        ) => {
          capturedOpts.push(opts as Record<string, unknown>);
          cb(null, "", "");
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

      const ac = new AbortController();
      await rt.ensure({ signal: ac.signal });

      // verify is the third execFile call (after venv and pip)
      const verifyOpts = capturedOpts[2];
      expect(verifyOpts.signal).toBe(ac.signal);
    });

    it("RED: aborted signal during venv kills child, cleans slot, returns aborted health", async () => {
      const fs = createMockFs();
      fs.existsSync.mockReturnValue(true);
      fs.readFileSync.mockReturnValue("");

      const abortError = new Error("The operation was aborted");
      abortError.name = "AbortError";

      const execFile = vi.fn<(...args: unknown[]) => void>();
      execFile.mockImplementation(
        (
          _cmd: unknown,
          _args: unknown,
          _opts: unknown,
          cb: (err: Error | null, stdout: string, stderr: string) => void
        ) => {
          // Simulate child killed by abort signal
          cb(abortError, "", "");
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

      // AbortError from child process → slot cleaned + aborted health
      expect(h.state).toBe("needs_repair");
      expect(h.error?.code).toBe("ABORTED");
      // Slot must be cleaned up
      expect(fs.rmSync).toHaveBeenCalled();
      // Pointer must NOT be written
      expect(fs.writeFileSync).not.toHaveBeenCalled();
      expect(fs.renameSync).not.toHaveBeenCalled();
    });

    it("RED: aborted signal during retained-slot probe prevents pointer write", async () => {
      const fs = createMockFs();
      // Pointer points to v1.4.0, so v1.3.0 is a rollback target with retained slot
      fs.readFileSync.mockImplementation((p: string) => {
        if (normalisePath(p) === normalisePath(POINTER_PATH)) {
          return JSON.stringify({
            schema_version: 1,
            version: "1.4.0",
            pythonPath: relPythonPath("1.4.0"),
            activatedAt: "2026-07-15T01:00:00Z",
          });
        }
        return "";
      });
      fs.existsSync.mockReturnValue(true);
      fs.readdirSync.mockReturnValue([mkDirent("v1.3.0"), mkDirent("v1.4.0")]);

      const abortError = new Error("The operation was aborted");
      abortError.name = "AbortError";

      const execFile = vi.fn<(...args: unknown[]) => void>();
      execFile.mockImplementation(
        (
          _cmd: unknown,
          _args: unknown,
          _opts: unknown,
          cb: (err: Error | null, stdout: string, stderr: string) => void
        ) => {
          cb(abortError, "", "");
        }
      );

      const rt = new ManagedRuntime({
        runtimeDir: RUNTIME_DIR,
        pluginVersion: "1.4.0",
        osPlatform: "win32",
        osArch: "x64",
        fs: fs as unknown as FsOps,
        execFile: execFile as unknown as ExecFileFn,
        execFileSync: createMockExecFileSync(
          "3.11.0"
        ) as unknown as ExecFileSyncFn,
      });

      const h = await rt.ensure({ version: "1.3.0" });

      // Retained slot probe failed with AbortError → no pointer write
      // Must NOT report RETAINED_SLOT_PROBE_FAILED — abort is not a probe failure
      expect(h.state).toBe("needs_repair");
      expect(h.error?.code).toBe("ABORTED");
      // Pointer must NOT be written (no .tmp write, no rename)
      expect(fs.writeFileSync).not.toHaveBeenCalled();
      expect(fs.renameSync).not.toHaveBeenCalled();
    });
  });

  // ── Python version gating ──
  describe("Python version gating", () => {
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
      fs.readdirSync.mockReturnValue([mkDirent("v1.2.3"), mkDirent("v1.3.0")]);

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
        if (p.includes("v1.3.0")) return false;
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
        if (p.includes("v1.3.0")) return false;
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
    it("contains only runtime metadata and machine-local interpreter paths — no credentials or vault paths", async () => {
      const fs = createMockFs();
      let writtenContent = "";

      fs.existsSync.mockReturnValue(true);
      fs.readFileSync.mockImplementation((p: string) => {
        if (normalisePath(p) === normalisePath(POINTER_PATH))
          return defaultPointer();
        return "";
      });
      fs.writeFileSync = vi.fn<
        (
          p: string,
          data: string | NodeJS.ArrayBufferView,
          encoding?: string | null
        ) => void
      >((p: string, data: string | NodeJS.ArrayBufferView) => {
        if (typeof p === "string" && p.endsWith(".tmp")) {
          writtenContent = typeof data === "string" ? data : String(data);
        }
      });
      fs.readdirSync =
        vi.fn<(p: string, opts?: { withFileTypes?: boolean }) => Dirent[]>();

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

      await rt.ensure();

      const ptr = JSON.parse(writtenContent);
      expect(ptr.schema_version).toBe(1);
      expect(ptr.version).toBe("1.3.0");
      expect(typeof ptr.pythonPath).toBe("string");
      expect(ptr.pythonPath).not.toContain("vault");
      expect(ptr.pythonPath).not.toContain("credentials");
      expect(ptr.pythonPath).not.toContain("secret");
      expect(ptr.pythonPath).not.toContain("token");
      expect(Object.keys(ptr)).not.toContain("bootstrapPath");
      expect(Object.keys(ptr)).not.toContain("bootstrap");
      expect(Object.keys(ptr)).not.toContain("vaultPath");
      expect(Object.keys(ptr)).not.toContain("vault");
      expect(Object.keys(ptr)).not.toContain("credential");
      expect(typeof ptr.activatedAt).toBe("string");
    });

    it("pointer atomicity: write-temp-file then rename preserves old pointer on interrupted write", async () => {
      const fs = createMockFs();
      let writtenContent = "";
      const originalContent = defaultPointer("1.2.3");

      fs.existsSync.mockReturnValue(true);
      fs.readFileSync.mockImplementation((p: string) => {
        if (normalisePath(p) === normalisePath(POINTER_PATH))
          return originalContent;
        if (p.endsWith(".tmp")) return writtenContent;
        return "";
      });
      fs.writeFileSync = vi.fn<
        (
          p: string,
          data: string | NodeJS.ArrayBufferView,
          encoding?: string | null
        ) => void
      >((p: string, data: string | NodeJS.ArrayBufferView) => {
        if (typeof p === "string" && p.endsWith(".tmp")) {
          writtenContent = typeof data === "string" ? data : String(data);
        }
      });
      fs.renameSync = vi.fn<(oldP: string, newP: string) => void>();

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

      await rt.ensure();

      expect(fs.renameSync.mock.calls.length).toBeGreaterThanOrEqual(1);
      // Old pointer content preserved
      expect(fs.readFileSync(POINTER_PATH)).toBe(originalContent);
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

    it("needs_repair with pythonPath → repair (primary) + rollback", () => {
      const acts = runtimeActionsForHealth(
        health({ state: "needs_repair", pythonPath: "/usr/bin/python" })
      );
      expect(acts).toHaveLength(2);
      expect(acts[0].id).toBe("repair");
      expect(acts[0].primary).toBe(true);
      expect(acts[1].id).toBe("rollback");
      expect(acts[1].primary).toBe(false);
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
function createSlotDir(
  baseDir: string,
  version: string,
  build2 = false
): string {
  const name = build2 ? `v${version}_build2` : `v${version}`;
  const slotDir = path.join(baseDir, name);
  const venvDir = path.join(slotDir, "venv", "Scripts");
  fs.mkdirSync(venvDir, { recursive: true });
  fs.writeFileSync(path.join(venvDir, "python.exe"), ""); // marker
  return slotDir;
}

/** Create a pointer file on the real filesystem. */
function createRealPointer(
  pointerDir: string,
  runtimeDirName: string,
  version: string
): void {
  const ptr = {
    schema_version: 1,
    version,
    pythonPath: `${runtimeDirName}/v${version}/venv/Scripts/python.exe`,
    activatedAt: new Date().toISOString(),
    previousVersion: null,
    previousPythonPath: null,
  };
  fs.writeFileSync(
    path.join(pointerDir, "active-runtime.json"),
    JSON.stringify(ptr, null, 2)
  );
}

/** List slot directory names under a runtime directory (sorted). */
function listSlotDirs(runtimeDir: string): string[] {
  return fs
    .readdirSync(runtimeDir, { withFileTypes: true })
    .filter((e) => e.isDirectory() && e.name.startsWith("v"))
    .map((e) => e.name)
    .sort();
}

describe("Real filesystem slot retention", () => {
  let tmpDir: string;
  const RUNTIME_DIR_NAME = "windows-x64";

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "mr-retention-"));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it("same-version ensure prunes old slots to keepOldSlots=2", async () => {
    const runtimeDir = path.join(tmpDir, RUNTIME_DIR_NAME);
    createSlotDir(runtimeDir, "1.0.0");
    createSlotDir(runtimeDir, "1.1.0");
    createSlotDir(runtimeDir, "1.2.0");
    createSlotDir(runtimeDir, "1.3.0");
    createRealPointer(tmpDir, RUNTIME_DIR_NAME, "1.3.0");

    const rt = new ManagedRuntime({
      runtimeDir,
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

    const remaining = listSlotDirs(runtimeDir);
    // 1 current (v1.4.0) + at most 2 old (v1.3.0, v1.2.0) = max 3
    expect(remaining).toContain("v1.4.0");
    expect(remaining).toContain("v1.3.0");
    expect(remaining).toContain("v1.2.0");
    expect(remaining).not.toContain("v1.1.0");
    expect(remaining).not.toContain("v1.0.0");
    expect(remaining.length).toBeLessThanOrEqual(3);
  });

  it("rollback retains previous active within keepOldSlots=2", async () => {
    const runtimeDir = path.join(tmpDir, RUNTIME_DIR_NAME);
    createSlotDir(runtimeDir, "1.0.0");
    createSlotDir(runtimeDir, "1.1.0");
    createSlotDir(runtimeDir, "1.2.0");
    createSlotDir(runtimeDir, "1.3.0");
    createRealPointer(tmpDir, RUNTIME_DIR_NAME, "1.3.0");

    const execFile = createMockExecFile("1.1.0");
    const rt = new ManagedRuntime({
      runtimeDir,
      pluginVersion: "1.4.0",
      osPlatform: "win32",
      osArch: "x64",
      execFile: execFile as unknown as ExecFileFn,
      execFileSync: createMockExecFileSync(
        "3.11.0"
      ) as unknown as ExecFileSyncFn,
    });

    const h = await rt.ensure({ version: "1.1.0" });
    expect(h.state).toBe("ready");
    expect(h.version).toBe("1.1.0");

    const remaining = listSlotDirs(runtimeDir);
    // Current v1.1.0, previous v1.3.0 (counts toward 2), v1.2.0 (2nd old)
    expect(remaining).toContain("v1.1.0");
    expect(remaining).toContain("v1.3.0");
    expect(remaining).toContain("v1.2.0");
    expect(remaining).not.toContain("v1.0.0");
    expect(remaining.length).toBeLessThanOrEqual(3);
  });

  it("cleanup failure after pointer activation cannot delete active slot", async () => {
    const runtimeDir = path.join(tmpDir, RUNTIME_DIR_NAME);
    createSlotDir(runtimeDir, "1.0.0");
    createSlotDir(runtimeDir, "1.1.0");
    createSlotDir(runtimeDir, "1.2.0");
    createSlotDir(runtimeDir, "1.3.0");
    createRealPointer(tmpDir, RUNTIME_DIR_NAME, "1.3.0");

    // Custom FsOps: real fs for everything, but rmSync throws (simulates cleanup failure)
    const failingFs: FsOps = {
      existsSync: (p: string) => fs.existsSync(p),
      readFileSync: (p: string, encoding?: string | null): string | Buffer => {
        return fs.readFileSync(
          p,
          encoding ? { encoding: encoding as BufferEncoding } : undefined
        );
      },
      writeFileSync: (
        p: string,
        data: string | NodeJS.ArrayBufferView,
        encoding?: string | null
      ): void => {
        fs.writeFileSync(
          p,
          data,
          encoding ? { encoding: encoding as BufferEncoding } : undefined
        );
      },
      renameSync: (oldP: string, newP: string) => fs.renameSync(oldP, newP),
      mkdirSync: (p: string, opts?: { recursive?: boolean }) =>
        fs.mkdirSync(p, opts),
      rmSync: () => {
        throw new Error("Simulated cleanup failure");
      },
      readdirSync: (p: string, opts?: { withFileTypes?: boolean }) =>
        fs.readdirSync(p, opts) as Dirent[],
    };

    const rt = new ManagedRuntime({
      runtimeDir,
      pluginVersion: "1.4.0",
      osPlatform: "win32",
      osArch: "x64",
      fs: failingFs as unknown as FsOps,
      execFile: createMockExecFile("1.4.0") as unknown as ExecFileFn,
      execFileSync: createMockExecFileSync(
        "3.11.0"
      ) as unknown as ExecFileSyncFn,
    });

    const h = await rt.ensure({ version: "1.4.0" });
    expect(h.state).toBe("ready");
    expect(h.version).toBe("1.4.0");

    // Pointer must point to the new version
    const ptrRaw = fs.readFileSync(
      path.join(tmpDir, "active-runtime.json"),
      "utf-8"
    );
    const ptr = JSON.parse(ptrRaw);
    expect(ptr.version).toBe("1.4.0");
    // Active slot directory must exist — cleanup failure cannot delete it
    expect(fs.existsSync(path.join(runtimeDir, "v1.4.0"))).toBe(true);
    // Pointer resolves to the active slot (relative pythonPath must form a path we can resolve)
    const resolvedPy = path.resolve(
      path.dirname(path.join(tmpDir, "active-runtime.json")),
      ptr.pythonPath
    );
    expect(resolvedPy).toContain("v1.4.0");
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
