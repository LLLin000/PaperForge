import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NodeProcessTransport } from "../src/client/node-transport";
import {
  INSTALLER_FAILED_MARKER,
  INSTALLER_FINISHED_MARKER,
  posixUvInstallerScript,
  uvInstallerRun,
  uvInstallerScript,
  windowsUvInstallerScript,
} from "../src/services/runtime-installer-launcher";

describe("zero-Python uv installer bootstrapper", () => {
  const tempDirs: string[] = [];

  afterEach(() => {
    while (tempDirs.length > 0) {
      const dir = tempDirs.pop()!;
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  function makeTempDir(): string {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "pf-uv-test-"));
    tempDirs.push(dir);
    return dir;
  }

  it("generates portable Windows PowerShell uv bootstrap script with mirrors and markers", () => {
    const home = makeTempDir();
    const script = windowsUvInstallerScript({
      action: "install",
      version: "2.0.0rc6",
      home,
    });
    expect(script).toContain("UV_CACHE_DIR");
    expect(script).toContain("UV_PYTHON_INSTALL_DIR");
    expect(script).toContain("UV_LINK_MODE = 'hardlink'");
    expect(script).toContain("astral-sh/uv/releases/download/0.13.9/uv-");
    expect(script).not.toContain("releases/latest/download");
    expect(script).toContain("Get-FileHash -Algorithm SHA256");
    expect(script).toContain(
      "https://registry.npmmirror.com/-/binary/python-build-standalone"
    );
    expect(script).toContain("paperforge[vector]==2.0.0rc6");
    expect(script).toContain("https://pypi.tuna.tsinghua.edu.cn/simple");
    expect(script).toContain("https://mirrors.aliyun.com/pypi/simple/");
    expect(script).toContain(
      "-m paperforge runtime install --expected-version"
    );
    expect(script).toContain(INSTALLER_FINISHED_MARKER);
    expect(script).toContain(INSTALLER_FAILED_MARKER);
  });

  it("generates POSIX /bin/sh uv bootstrap script without bash-only ERR traps", () => {
    const home = makeTempDir();
    const script = posixUvInstallerScript({
      action: "update",
      version: "2.0.0-rc.6",
      home,
      platform: "linux",
      arch: "x64",
    });
    expect(script).toContain("#!/bin/sh");
    expect(script).not.toContain("trap 'fail' ERR");
    expect(script).not.toContain("releases/latest/download");
    expect(script).toContain("astral-sh/uv/releases/download/0.13.9/uv-");
    expect(script).toContain("verify_sha256");
    expect(script).toContain("trap on_exit EXIT");
    expect(script).toContain("x86_64-unknown-linux-gnu.tar.gz");
    expect(script).toContain("paperforge[vector]==2.0.0rc6");
    expect(script).toContain('"$BOOT_PY" -m paperforge runtime update');
    expect(script).toContain(INSTALLER_FINISHED_MARKER);
    expect(script).toContain(INSTALLER_FAILED_MARKER);
  });

  it("dispatches uvInstallerScript and uvInstallerRun per platform", () => {
    expect(uvInstallerRun("win32", "C:\\tmp\\setup.ps1")).toEqual({
      command: "powershell.exe",
      args: [
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "C:\\tmp\\setup.ps1",
      ],
    });
    expect(uvInstallerRun("darwin", "/tmp/setup.sh")).toEqual({
      command: "/bin/sh",
      args: ["/tmp/setup.sh"],
    });
    const darwin = uvInstallerScript({
      action: "repair",
      version: "2.0.0rc6",
      platform: "darwin",
      arch: "arm64",
      home: makeTempDir(),
    });
    expect(darwin).toContain("aarch64-apple-darwin.tar.gz");
  });

  it("spawns uv installer when allowUvDownload=true and no Python exists", () => {
    const dir = makeTempDir();
    const logPath = path.join(dir, "installer.log");
    const spawnCalls: { command: string; args: string[]; options: unknown }[] =
      [];
    const mockSpawn = vi.fn(
      (command: string, args: string[], options: unknown) => {
        spawnCalls.push({ command, args, options });
        return { unref: vi.fn() } as unknown as ReturnType<
          typeof import("child_process").spawn
        >;
      }
    );
    const transport = new NodeProcessTransport({
      vaultPath: dir,
      spawnFn: mockSpawn as unknown as typeof import("child_process").spawn,
      installerLogPath: () => logPath,
    });
    vi.spyOn(transport, "discoverBasePython").mockReturnValue(null);
    vi.spyOn(transport, "discoverUv").mockReturnValue(null);

    const denied = transport.launchRuntimeInstaller("install", "2.0.0rc6");
    expect(denied.ok).toBe(false);
    expect(denied.error).toContain("No Python 3.11+");
    expect(spawnCalls).toHaveLength(0);

    const allowed = transport.launchRuntimeInstaller("install", "2.0.0rc6", {
      allowUvDownload: true,
    });
    expect(allowed.ok).toBe(true);
    expect(allowed.python).toBe("uv");
    expect(allowed.logPath).toBe(logPath);
    expect(spawnCalls).toHaveLength(1);
    expect(spawnCalls[0].options).toEqual(
      expect.objectContaining({
        shell: false,
        detached: true,
        windowsHide: true,
      })
    );
  });

  it("reuses discovered uv when allowUvDownload=true and Python is missing", () => {
    const dir = makeTempDir();
    const logPath = path.join(dir, "installer.log");
    const fakeUv = path.join(dir, "uv.exe");
    const mockSpawn = vi.fn(() => {
      return { unref: vi.fn() } as unknown as ReturnType<
        typeof import("child_process").spawn
      >;
    });
    const transport = new NodeProcessTransport({
      vaultPath: dir,
      spawnFn: mockSpawn as unknown as typeof import("child_process").spawn,
      installerLogPath: () => logPath,
    });
    vi.spyOn(transport, "discoverBasePython").mockReturnValue(null);
    vi.spyOn(transport, "discoverUv").mockReturnValue(fakeUv);

    const res = transport.launchRuntimeInstaller("repair", "2.0.0rc6", {
      allowUvDownload: true,
    });
    expect(res.ok).toBe(true);
    expect(res.python).toBe(fakeUv);
    expect(mockSpawn).toHaveBeenCalledTimes(1);
  });
});
