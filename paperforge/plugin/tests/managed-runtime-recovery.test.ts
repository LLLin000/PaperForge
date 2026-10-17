/** #269: install recovery — candidate cleanup/retirement and failure classes. */
import { describe, it, expect } from "vitest";
import * as path from "node:path";

import {
  classifySetupFailure,
  type ErrorClassification,
} from "../src/services/python-bridge";
import {
  RuntimeBootstrap,
  type ExecFileFn,
  type ExecFileSyncFn,
  type FsOps,
} from "../src/services/managed-runtime";

const ROOT = path.join("C:", "pf-runtime");

function fakeFs(overrides: Partial<FsOps> = {}): {
  fs: FsOps;
  removed: string[];
  written: string[];
} {
  const removed: string[] = [];
  const written: string[] = [];
  const fs: FsOps = {
    existsSync: () => false,
    readFileSync: () => "{}",
    mkdirSync: () => undefined,
    rmSync: (p: string) => {
      removed.push(p);
    },
    readdirSync: () => [],
    writeFileSync: (p: string) => {
      written.push(p);
    },
    ...overrides,
  };
  return { fs, removed, written };
}

describe("install recovery (#269)", () => {
  it("retires only candidates a failed install marked abandoned", () => {
    const { fs, removed } = fakeFs({
      readdirSync: () => ["venv-a", "venv-b", "other"],
      existsSync: (p: string) =>
        p.includes("venv-a") && p.endsWith(".abandoned"),
    });
    const runtime = new RuntimeBootstrap({
      runtimeDir: ROOT,
      fs,
      osPlatform: "win32",
    });
    expect(runtime.retireAbandonedCandidates()).toEqual(["venv-a"]);
    expect(removed).toHaveLength(1);
    expect(removed[0]).toContain("venv-a");
  });

  it("names the timeout and marks the candidate when removal fails", async () => {
    const { fs, written } = fakeFs({
      rmSync: () => {
        throw new Error("EBUSY");
      },
    });
    const execFileSync: ExecFileSyncFn = () => "Python 3.12.0";
    const execFile: ExecFileFn = (_command, _args, _opts, cb) => {
      (cb as unknown as (err: unknown) => void)(
        Object.assign(new Error("Command failed: pip"), {
          killed: true,
          signal: "SIGTERM",
          code: 1,
        })
      );
      return {};
    };
    const runtime = new RuntimeBootstrap({
      runtimeDir: ROOT,
      fs,
      osPlatform: "win32",
      execFileSync,
      execFile,
    });
    await expect(runtime.installOnce("2.0.0")).rejects.toThrow(
      /timed out after/
    );
    expect(written.some((p) => p.endsWith(".abandoned"))).toBe(true);
  });

  it("classifies a timeout and an external kill as different classes", () => {
    const timeout = classifySetupFailure(
      "pip install timed out after 600s: Command failed"
    ) as ErrorClassification;
    const killed = classifySetupFailure(
      "pip install failed: X — [killed signal=SIGTERM]"
    ) as ErrorClassification;
    const eof = classifySetupFailure(
      "EOF without terminal event (exit 1, signal SIGTERM)"
    ) as ErrorClassification;
    expect(timeout.type).toBe("network");
    expect(killed.type).toBe("install_interrupted");
    expect(eof.type).toBe("install_interrupted");

  // #269 real-kill evidence: the child was terminated from outside, so the
  // message carries no signal name and only the Windows termination exit code.
  // A stray "connection" line from the dying pip must not turn this into a
  // network failure.
  const externalKill = classifySetupFailure(
    "pip install failed: Command failed: C:\\tmp\\venv\\Scripts\\python.exe -m pip install paperforge[vector]==2.0.0rc5\n" +
      " — [exit=4294967295]\nERROR: ConnectionResetError: peer closed"
  );
  expect(externalKill.type).toBe("install_interrupted");
  expect(externalKill.recoverable).toBe(true);
  const unixKill = classifySetupFailure("pip install failed: — [exit=-1]");
  expect(unixKill.type).toBe("install_interrupted");
  const ordinary = classifySetupFailure("pip install failed: — [exit=1]\nERROR: Could not find a version");
  expect(ordinary.type).not.toBe("install_interrupted");
  });
});
