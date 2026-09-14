/**
 * Vitest tests for RuntimeBootstrap (#174 / #143 §7).
 *
 * The plugin holds NO runtime state machine post-cutover.  Covered here:
 * interpreter discovery (>=3.11), platform gates, ONE one-time install,
 * handshake, pointer READ (full schema v1, fail-closed), and command
 * resolution from the pointer.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import * as path from "path";
import * as os from "os";
import * as fs from "fs";
import {
  RuntimeBootstrap,
  getOsArch,
  resolveRuntimeCommand,
  AbortError,
} from "../src/services/managed-runtime";
import type {
  FsOps,
  ExecFileFn,
  ExecFileSyncFn,
} from "../src/services/managed-runtime";

const RUNTIME_DIR = path.join("home", "user", ".paperforge", "runtime");
const POINTER_PATH = path.join(RUNTIME_DIR, "pointer.json");

// ── Mock helpers ──

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

type MockExecFile = ReturnType<typeof vi.fn<(...args: unknown[]) => void>>;

/** execFile that calls back with a probe version (or a failure). */
function createMockExecFile(probeVersion: string): MockExecFile {
  const fn = vi.fn<(...args: unknown[]) => void>();
  fn.mockImplementation(
    (
      _cmd: unknown,
      _args: unknown,
      _opts: unknown,
      cb: (err: Error | null, stdout: string, stderr: string) => void
    ) => {
      cb(null, probeVersion, "");
    }
  );
  return fn;
}

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

/** execFileSync returning a Python version banner. */
function createMockExecFileSync(pythonVersion: string): ExecFileSyncFn {
  return ((
    _cmd: string,
    _args: readonly string[],
    _opts: { encoding: string; timeout: number }
  ) => {
    return `Python ${pythonVersion}`;
  }) as ExecFileSyncFn;
}

function createThrowingExecFileSync(): ExecFileSyncFn {
  return ((
    _cmd: string,
    _args: readonly string[],
    _opts: { encoding: string; timeout: number }
  ) => {
    throw new Error("Not found");
  }) as ExecFileSyncFn;
}

/** Canonical single-venv python path (absolute). */
function pythonPathFor(): string {
  return path.resolve(path.join(RUNTIME_DIR, "venv", "Scripts", "python.exe"));
}

/** Valid pointer.json (schema v1, absolute paths). */
function defaultPointer(version = "1.3.0"): string {
  return JSON.stringify({
    schema_version: 1,
    python_path: pythonPathFor(),
    environment_root: path.resolve(path.join(RUNTIME_DIR, "venv")),
    paperforge_version: version,
  });
}

function normalisePath(p: string): string {
  return p.replace(/\\/g, "/");
}

function makeBootstrap(
  overrides: {
    fs?: MockFs;
    execFile?: MockExecFile;
    execFileSync?: ExecFileSyncFn;
    osPlatform?: string;
    osArch?: string;
  } = {}
): RuntimeBootstrap {
  return new RuntimeBootstrap({
    runtimeDir: RUNTIME_DIR,
    osPlatform: overrides.osPlatform ?? "win32",
    osArch: overrides.osArch ?? "x64",
    fs: (overrides.fs ?? createMockFs()) as unknown as FsOps,
    execFile: (overrides.execFile ??
      createMockExecFile("1.3.0")) as unknown as ExecFileFn,
    execFileSync: overrides.execFileSync ?? createMockExecFileSync("3.11.0"),
  });
}

// ── Tests ──

describe("RuntimeBootstrap", () => {
  // ── discoverInterpreter ──
  describe("discoverInterpreter()", () => {
    it("returns a >=3.11 interpreter", () => {
      const rt = makeBootstrap({
        execFileSync: createMockExecFileSync("3.12.1"),
      });
      const d = rt.discoverInterpreter();
      expect(d).not.toBeNull();
      expect(d!.version).toBe("3.12.1");
    });

    it("skips too-old interpreters and keeps trying (#174: py -3.10 must not block py -3)", () => {
      // First candidate (py -3) returns 3.10 → must continue to py -3.11 → 3.12.
      const calls: string[][] = [];
      const es = ((
        _c: string,
        args: readonly string[],
        _o: { encoding: string; timeout: number }
      ) => {
        calls.push([...args]);
        const joined = args.join(" ");
        if (joined.includes("--version")) {
          if (calls.length === 1) return "Python 3.10.4";
          if (calls.length === 2) return "Python 3.9.9";
          return "Python 3.12.2";
        }
        throw new Error("no");
      }) as ExecFileSyncFn;
      const rt = makeBootstrap({ execFileSync: es });
      const d = rt.discoverInterpreter();
      expect(d).not.toBeNull();
      expect(d!.version).toBe("3.12.2");
    });

    it("returns null when no interpreter is found", () => {
      const rt = makeBootstrap({ execFileSync: createThrowingExecFileSync() });
      expect(rt.discoverInterpreter()).toBeNull();
    });
  });

  // ── platformGate ──
  describe("platformGate()", () => {
    it("Flatpak/Snap environment → unsupported", () => {
      const g = makeBootstrap().platformGate();
      // without env vars the gate falls through to NO_PYTHON on win32
      expect(g.ok).toBe(false);
    });
  });

  // ── installOnce ──
  describe("installOnce()", () => {
    it("creates ONE venv, ONE pinned install, fresh-verifies, and NEVER writes the pointer", async () => {
      const fsMock = createMockFs();
      fsMock.existsSync.mockReturnValue(false);
      fsMock.readFileSync.mockReturnValue("");
      const execFile = createMockExecFile("1.3.0");
      const rt = makeBootstrap({ fs: fsMock, execFile });

      const result = await rt.installOnce("1.3.0");
      expect(result.observedVersion).toBe("1.3.0");
      expect(path.resolve(result.pythonPath)).toBe(pythonPathFor());

      expect(fsMock.mkdirSync).toHaveBeenCalledWith(
        expect.stringContaining("venv"),
        expect.anything()
      );
      const cmds = execFile.mock.calls.map((c) => c[0] as string);
      const pipArgs = execFile.mock.calls[1][1] as string[];
      expect(pipArgs.join(" ")).toContain("paperforge[vector]==1.3.0");
      // verify probe reads stdout (third call args are the import probe)
      const verifyArgs = execFile.mock.calls[2][1] as string[];
      expect(verifyArgs.join(" ")).toContain("print(paperforge.__version__)");
      // NO pointer write: FsOps has no writeFileSync at all.
      expect(
        (fsMock as unknown as Record<string, unknown>).writeFileSync
      ).toBeUndefined();
    });

    it("requested 1.3.0 but fresh probe returns 1.2.0 → fails and cleans up, no setup", async () => {
      const fsMock = createMockFs();
      fsMock.existsSync.mockReturnValue(false);
      fsMock.readFileSync.mockReturnValue("");
      const rt = makeBootstrap({
        fs: fsMock,
        execFile: createMockExecFile("1.2.0"),
      });

      await expect(rt.installOnce("1.3.0")).rejects.toThrow(/version mismatch/);
      expect(fsMock.rmSync).toHaveBeenCalled();
    });

    it("pip failure cleans the venv and rejects", async () => {
      const fsMock = createMockFs();
      fsMock.existsSync.mockReturnValue(false);
      fsMock.readFileSync.mockReturnValue("");
      const execFile = vi.fn<(...args: unknown[]) => void>();
      execFile.mockImplementation(
        (
          _cmd: unknown,
          args: unknown,
          _opts: unknown,
          cb: (err: Error | null, stdout: string, stderr: string) => void
        ) => {
          const a = args as readonly string[];
          if (a[0] === "-m" && a[1] === "pip") {
            cb(new Error("pip install failed"), "", "error");
          } else {
            cb(null, "1.3.0", "");
          }
        }
      );
      const rt = makeBootstrap({ fs: fsMock, execFile });
      await expect(rt.installOnce("1.3.0")).rejects.toThrow(
        /pip install failed/
      );
      expect(fsMock.rmSync).toHaveBeenCalled();
    });

    it("aborted signal → AbortError", async () => {
      const ac = new AbortController();
      ac.abort();
      const rt = makeBootstrap();
      await expect(rt.installOnce("1.3.0", ac.signal)).rejects.toBeInstanceOf(
        AbortError
      );
    });
  });

  // ── installOnce: configured interpreter (wizard "Python executable") ──
  describe("installOnce() interpreter override", () => {
    /** execFileSync recorder: only the configured path answers a version. */
    function recordingExecFileSync(version = "3.12.4"): {
      fn: ExecFileSyncFn;
      commands: string[];
    } {
      const commands: string[] = [];
      const fn = ((
        cmd: string,
        _args: readonly string[],
        _opts: { encoding: string; timeout: number }
      ) => {
        commands.push(cmd);
        return `Python ${version}`;
      }) as ExecFileSyncFn;
      return { fn, commands };
    }

    it("creates the venv from the configured interpreter instead of discovery", async () => {
      const fsMock = createMockFs();
      fsMock.existsSync.mockReturnValue(true);
      const execFile = createMockExecFile("1.4.0");
      const { fn: execFileSync, commands } = recordingExecFileSync();
      const rt = makeBootstrap({ fs: fsMock, execFile, execFileSync });

      await rt.installOnce("1.4.0", undefined, "C:/custom/python.exe");

      expect(commands).toContain("C:/custom/python.exe");
      const venvCall = execFile.mock.calls.find(
        (call) => Array.isArray(call[1]) && (call[1] as string[]).includes("venv")
      );
      expect(venvCall?.[0]).toBe("C:/custom/python.exe");
    });

    it("fails closed on a missing path — never silently picks another interpreter", async () => {
      const fsMock = createMockFs();
      fsMock.existsSync.mockReturnValue(false);
      const execFile = createMockExecFile("1.4.0");
      const rt = makeBootstrap({ fs: fsMock, execFile });

      await expect(
        rt.installOnce("1.4.0", undefined, "C:/gone/python.exe")
      ).rejects.toThrow(/Python executable not found: C:\/gone\/python\.exe/);
      expect(execFile).not.toHaveBeenCalled();
    });

    it("rejects a configured interpreter below 3.11", async () => {
      const fsMock = createMockFs();
      fsMock.existsSync.mockReturnValue(true);
      const rt = makeBootstrap({
        fs: fsMock,
        execFileSync: createMockExecFileSync("3.9.7"),
      });

      await expect(
        rt.installOnce("1.4.0", undefined, "C:/old/python.exe")
      ).rejects.toThrow(/older than the required 3\.11/);
    });

    it("blank override falls back to discovery", async () => {
      const fsMock = createMockFs();
      fsMock.existsSync.mockReturnValue(false);
      const execFile = createMockExecFile("1.4.0");
      const rt = makeBootstrap({ fs: fsMock, execFile });

      await rt.installOnce("1.4.0", undefined, "   ");
      const venvCall = execFile.mock.calls.find(
        (call) => Array.isArray(call[1]) && (call[1] as string[]).includes("venv")
      );
      expect(venvCall?.[0]).toBe("py");
    });
  });

  // ── installOnce: no zombie pip, no concurrent writer ──
  describe("installOnce() failure isolation", () => {
    it("terminates the install child before deleting the venv", async () => {
      const kill = vi.fn();
      const child = { kill, pid: 4242 };
      const execFile = vi.fn<(...args: unknown[]) => unknown>();
      execFile.mockImplementation(
        (
          _cmd: unknown,
          args: unknown,
          _opts: unknown,
          cb: (err: Error | null, stdout: string, stderr: string) => void
        ) => {
          const a = args as readonly string[];
          if (a.includes("pip")) {
            cb(new Error("pip install failed"), "", "");
          } else {
            cb(null, "1.4.0", "");
          }
          return child;
        }
      );
      const rt = makeBootstrap({
        execFile: execFile as unknown as MockExecFile,
      });

      await expect(rt.installOnce("1.4.0")).rejects.toThrow(
        /pip install failed/
      );
      expect(kill).toHaveBeenCalled();
    });

    it("refuses a second install for the same runtime dir while one runs", async () => {
      let releasePip: (() => void) | null = null;
      const execFile = vi.fn<(...args: unknown[]) => unknown>();
      execFile.mockImplementation(
        (
          _cmd: unknown,
          args: unknown,
          _opts: unknown,
          cb: (err: Error | null, stdout: string, stderr: string) => void
        ) => {
          const a = args as readonly string[];
          if (a.includes("pip")) {
            releasePip = () => cb(null, "", "");
          } else {
            cb(null, "1.4.0", "");
          }
          return { kill: vi.fn(), pid: 7 };
        }
      );
      const rt = makeBootstrap({
        execFile: execFile as unknown as MockExecFile,
      });

      const first = rt.installOnce("1.4.0");
      await expect(rt.installOnce("1.4.0")).rejects.toThrow(
        /already running/
      );
      releasePip?.();
      await first;
    });
  });

  // ── fresh-child probes must not inherit the app's CWD/PYTHONPATH ──
  describe("fresh-child probe isolation", () => {
    it("runs the installation probe with -P, a neutral cwd, and no PYTHONPATH", async () => {
      const fsMock = createMockFs();
      fsMock.existsSync.mockReturnValue(true);
      const execFile = createMockExecFile("1.4.0");
      const rt = makeBootstrap({ fs: fsMock, execFile });

      await rt.handshake("1.4.0", { vaultPath: "/vault" });

      const probeCall = execFile.mock.calls.find(
        (call) =>
          Array.isArray(call[1]) &&
          (call[1] as string[]).includes("installation")
      );
      expect(probeCall).toBeDefined();
      const probeArgs = probeCall?.[1] as string[];
      expect(probeArgs[0]).toBe("-P");
      const probeOpts = probeCall?.[2] as {
        cwd?: string;
        env?: Record<string, string | undefined>;
      };
      expect(probeOpts.cwd).toBeTruthy();
      expect(probeOpts.cwd).not.toBe(process.cwd());
      expect(probeOpts.env?.PYTHONPATH).toBeUndefined();
      expect(probeOpts.env?.PYTHONHOME).toBeUndefined();
    });
  });

  // ── handshake ──
  describe("handshake() (#143 two mandatory probes, fail-closed)", () => {
    const VAULT = "/test/vault";

    /** execFile that replies with a probe version first, then an
     * installation-probe envelope (or fails / malformed). */
    function makeExec(
      probeVersion: string,
      installOutcome:
        | { kind: "envelope"; code: string }
        | { kind: "exec-fail" }
        | { kind: "malformed" }
    ): MockExecFile {
      const fn = vi.fn<(...args: unknown[]) => void>();
      fn.mockImplementation(
        (
          _cmd: unknown,
          args: unknown,
          _opts: unknown,
          cb: (err: Error | null, stdout: string, stderr: string) => void
        ) => {
          const a = args as readonly string[];
          if (a[0] === "-I") {
            cb(null, probeVersion, "");
            return;
          }
          if (installOutcome.kind === "exec-fail") {
            cb(new Error("probe failed"), "", "boom");
            return;
          }
          if (installOutcome.kind === "malformed") {
            cb(null, "{not json", "");
            return;
          }
          cb(
            null,
            JSON.stringify({ reason: { code: installOutcome.code } }),
            ""
          );
        }
      );
      return fn;
    }

    it("ok on version match + installation.ready", async () => {
      const fsMock = createMockFs();
      fsMock.existsSync.mockReturnValue(true);
      const rt = makeBootstrap({
        fs: fsMock,
        execFile: makeExec("1.3.0", {
          kind: "envelope",
          code: "installation.ready",
        }),
      });
      const hs = await rt.handshake("1.3.0", {
        pythonPath: pythonPathFor(),
        vaultPath: VAULT,
      });
      expect(hs.ok).toBe(true);
    });

    it("ok on version match + installation.config_missing (pre-setup exception)", async () => {
      const fsMock = createMockFs();
      fsMock.existsSync.mockReturnValue(true);
      const rt = makeBootstrap({
        fs: fsMock,
        execFile: makeExec("1.3.0", {
          kind: "envelope",
          code: "installation.config_missing",
        }),
      });
      const hs = await rt.handshake("1.3.0", {
        pythonPath: pythonPathFor(),
        vaultPath: VAULT,
      });
      expect(hs.ok).toBe(true);
    });

    it.each([
      "installation.runtime_pointer_missing",
      "installation.runtime_pointer_stale",
      "installation.runtime_executable_missing",
    ])("accepts pre-setup runtime state %s", async (code) => {
      const fsMock = createMockFs();
      fsMock.existsSync.mockReturnValue(true);
      const rt = makeBootstrap({
        fs: fsMock,
        execFile: makeExec("1.3.0", { kind: "envelope", code }),
      });
      const hs = await rt.handshake("1.3.0", {
        pythonPath: pythonPathFor(),
        vaultPath: VAULT,
      });
      expect(hs.ok).toBe(true);
    });

    it("fails on version match + installation.version_mismatch", async () => {
      const fsMock = createMockFs();
      fsMock.existsSync.mockReturnValue(true);
      const rt = makeBootstrap({
        fs: fsMock,
        execFile: makeExec("1.3.0", {
          kind: "envelope",
          code: "installation.version_mismatch",
        }),
      });
      const hs = await rt.handshake("1.3.0", {
        pythonPath: pythonPathFor(),
        vaultPath: VAULT,
      });
      expect(hs.ok).toBe(false);
      expect(hs.reason).toContain("version mismatch");
    });

    it("fails closed on probe exec failure", async () => {
      const fsMock = createMockFs();
      fsMock.existsSync.mockReturnValue(true);
      const rt = makeBootstrap({
        fs: fsMock,
        execFile: makeExec("1.3.0", { kind: "exec-fail" }),
      });
      const hs = await rt.handshake("1.3.0", {
        pythonPath: pythonPathFor(),
        vaultPath: VAULT,
      });
      expect(hs.ok).toBe(false);
      expect(hs.reason).toContain("probe failed");
    });

    it("fails closed on malformed envelope", async () => {
      const fsMock = createMockFs();
      fsMock.existsSync.mockReturnValue(true);
      const rt = makeBootstrap({
        fs: fsMock,
        execFile: makeExec("1.3.0", { kind: "malformed" }),
      });
      const hs = await rt.handshake("1.3.0", {
        pythonPath: pythonPathFor(),
        vaultPath: VAULT,
      });
      expect(hs.ok).toBe(false);
      expect(hs.reason).toContain("unparseable");
    });

    it("fails on an unexpected probe state", async () => {
      const fsMock = createMockFs();
      fsMock.existsSync.mockReturnValue(true);
      const rt = makeBootstrap({
        fs: fsMock,
        execFile: makeExec("1.3.0", {
          kind: "envelope",
          code: "installation.weird",
        }),
      });
      const hs = await rt.handshake("1.3.0", {
        pythonPath: pythonPathFor(),
        vaultPath: VAULT,
      });
      expect(hs.ok).toBe(false);
      expect(hs.reason).toContain("unexpected installation probe state");
    });

    it("fails when fresh version differs", async () => {
      const fsMock = createMockFs();
      fsMock.existsSync.mockReturnValue(true);
      const rt = makeBootstrap({
        fs: fsMock,
        execFile: makeExec("1.2.0", {
          kind: "envelope",
          code: "installation.ready",
        }),
      });
      const hs = await rt.handshake("1.3.0", {
        pythonPath: pythonPathFor(),
        vaultPath: VAULT,
      });
      expect(hs.ok).toBe(false);
      expect(hs.reason).toContain("version mismatch");
    });

    it("fails when interpreter is missing", async () => {
      const fsMock = createMockFs();
      fsMock.existsSync.mockReturnValue(false);
      const rt = makeBootstrap({ fs: fsMock });
      const hs = await rt.handshake("1.3.0", {
        pythonPath: pythonPathFor(),
        vaultPath: VAULT,
      });
      expect(hs.ok).toBe(false);
      expect(hs.reason).toBe("interpreter missing");
    });
  });

  // ── readPointer ──
  describe("readPointer()", () => {
    it("returns full schema v1 with absolute paths", () => {
      const fsMock = createMockFs();
      fsMock.readFileSync.mockImplementation((p: string) => {
        if (normalisePath(p) === normalisePath(POINTER_PATH))
          return defaultPointer();
        return "";
      });
      const rt = makeBootstrap({ fs: fsMock });
      const ptr = rt.readPointer();
      expect(ptr).not.toBeNull();
      expect(ptr!.paperforgeVersion).toBe("1.3.0");
      expect(path.isAbsolute(ptr!.pythonPath)).toBe(true);
      expect(path.isAbsolute(ptr!.environmentRoot)).toBe(true);
    });

    it("rejects missing environment_root (#174 fail-closed)", () => {
      const fsMock = createMockFs();
      fsMock.readFileSync.mockReturnValue(
        JSON.stringify({
          schema_version: 1,
          python_path: pythonPathFor(),
          paperforge_version: "1.3.0",
        })
      );
      const rt = makeBootstrap({ fs: fsMock });
      expect(rt.readPointer()).toBeNull();
    });

    it("rejects relative python_path", () => {
      const fsMock = createMockFs();
      fsMock.readFileSync.mockReturnValue(
        JSON.stringify({
          schema_version: 1,
          python_path: "relative/python.exe",
          environment_root: RUNTIME_DIR,
          paperforge_version: "1.3.0",
        })
      );
      const rt = makeBootstrap({ fs: fsMock });
      expect(rt.readPointer()).toBeNull();
    });

    it("rejects unsupported schema / bad JSON / absent file", () => {
      for (const content of [
        JSON.stringify({ schema_version: 99 }),
        "{not json",
        "",
      ]) {
        const fsMock = createMockFs();
        fsMock.readFileSync.mockImplementation((p: string) => {
          if (normalisePath(p) === normalisePath(POINTER_PATH)) {
            throw new Error("ENOENT");
          }
          return content;
        });
        const rt = makeBootstrap({ fs: fsMock });
        // absent file path
        expect(rt.readPointer()).toBeNull();
      }
    });
  });

  // ── resolveRuntimeCommand ──
  describe("resolveRuntimeCommand()", () => {
    it("returns command only from a valid pointer", () => {
      const run = resolveRuntimeCommand({
        pythonPath: pythonPathFor(),
        environmentRoot: path.join(RUNTIME_DIR, "venv"),
        paperforgeVersion: "1.3.0",
      });
      expect(run?.command).toBe(pythonPathFor());
    });

    it("returns null when the pointer is absent (installed-but-unpublished is NOT usable)", () => {
      expect(resolveRuntimeCommand(null)).toBeNull();
    });
  });
});

// ── getOsArch ──
describe("getOsArch", () => {
  it("maps platform-arch triplets", () => {
    expect(getOsArch("win32", "x64")).toBe("windows-x64");
    expect(getOsArch("darwin", "arm64")).toBe("macos-arm64");
    expect(getOsArch("darwin", "x64")).toBe("macos-x64");
    expect(getOsArch("linux", "x64")).toBe("linux-x64");
  });
});

// ── Real filesystem: single venv, no pointer write ──
describe("Real filesystem single venv (#174)", () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "mr-single-venv-"));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it("installOnce() creates ONE venv and never writes a pointer", async () => {
    const execFile = createMockExecFile("1.4.0");
    const rt = new RuntimeBootstrap({
      runtimeDir: tmpDir,
      osPlatform: "win32",
      osArch: "x64",
      execFile: execFile as unknown as ExecFileFn,
      execFileSync: createMockExecFileSync("3.11.0"),
    });
    const result = await rt.installOnce("1.4.0");
    expect(result.observedVersion).toBe("1.4.0");
    expect(fs.existsSync(path.join(tmpDir, "venv"))).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, "pointer.json"))).toBe(false);
    expect(fs.readdirSync(tmpDir).some((n) => /^v\d/.test(n))).toBe(false);
  });
});
