import { describe, it, expect, vi } from "vitest";
import * as fs from "fs";

import { NodeProcessTransport } from "../src/client/node-transport";
import {
  macInstallerScript,
  runtimeInstallerShellCommand,
  runtimeInstallerSteps,
  terminalLaunch,
  windowsInstallerScript,
} from "../src/services/runtime-installer-launcher";

describe("external runtime installer launcher", () => {
  it("installs the CLI, then lets the CLI publish the runtime", () => {
    expect(runtimeInstallerSteps("install", "1.5.15")).toEqual([
      "{{python}} -m pip install --user --upgrade paperforge==1.5.15",
      "{{python}} -m paperforge runtime install --expected-version 1.5.15",
    ]);
  });

  it("quotes a python path containing spaces", () => {
    expect(
      runtimeInstallerShellCommand("C:\\Program Files\\Py\\python.exe", "update", "2.0.0")
    ).toBe(
      '"C:\\Program Files\\Py\\python.exe" -m pip install --user --upgrade paperforge==2.0.0 && ' +
        '"C:\\Program Files\\Py\\python.exe" -m paperforge runtime update --expected-version 2.0.0'
    );
  });

  it("stops the Windows script when the bootstrap step fails", () => {
    const script = windowsInstallerScript("first && second");
    expect(script.indexOf("first")).toBeLessThan(script.indexOf("second"));
    expect(script).toContain("if errorlevel 1 goto :paperforge_failed");
    expect(script).toContain(":paperforge_failed");
  });

  it("opens a console that stays open on Windows", () => {
    const launch = terminalLaunch("win32", {
      comSpec: "C:\\cmd.exe",
      scriptPath: "C:\\tmp\\installer.cmd",
    });
    expect(launch.command).toBe("C:\\cmd.exe");
    expect(launch.args).toEqual([
      "/c",
      "start",
      "",
      "cmd.exe",
      "/k",
      "C:\\tmp\\installer.cmd",
    ]);
  });

  it("runs the script through Terminal on macOS and a terminal on Linux", () => {
    expect(
      terminalLaunch("darwin", { scriptPath: "/tmp/installer.command" }).args
    ).toEqual(["-a", "Terminal", "/tmp/installer.command"]);
    expect(
      terminalLaunch("linux", { scriptPath: "/tmp/installer.command" }).args
    ).toEqual(["-e", "sh", "/tmp/installer.command"]);
    expect(macInstallerScript("echo hi")).toContain("echo hi");
  });

  // Windows-only: asserts the .cmd bootstrap, ComSpec launch and the `py`
  // launcher candidate. The Linux/macOS script shapes are covered above.
  it.runIf(process.platform === "win32")(
    "launches the installer without resolving a published runtime",
    () => {
    const spawnFn = vi.fn(() => ({ unref: vi.fn() })) as never;
    const execFileSyncFn = vi.fn((cmd: string) => {
      if (cmd !== "py") throw new Error("missing");
      return "Python 3.12.4";
    }) as never;
    const transport = new NodeProcessTransport({
      vaultPath: "C:\\vault",
      spawnFn,
      execFileSyncFn,
    });

    const result = transport.launchRuntimeInstaller("install", "1.5.15");

    expect(result).toEqual({ ok: true, python: "py" });
    const [command, args] = (spawnFn as unknown as ReturnType<typeof vi.fn>).mock
      .calls[0] as [string, string[]];
    expect(command).toBe(process.env.ComSpec || "C:\\Windows\\System32\\cmd.exe");
    const scriptPath = args[args.length - 1];
    expect(scriptPath.endsWith(".cmd")).toBe(true);
    const script = fs.readFileSync(scriptPath, "utf-8");
    expect(script).toContain("paperforge runtime install --expected-version 1.5.15");
    expect(script).toContain("py -m pip install --user --upgrade paperforge==1.5.15");
      fs.rmSync(scriptPath, { force: true });
    }
  );

  it("reports a missing interpreter instead of installing anything", () => {
    const spawnFn = vi.fn() as never;
    const execFileSyncFn = vi.fn(() => {
      throw new Error("no python");
    }) as never;
    const transport = new NodeProcessTransport({
      vaultPath: "C:\\vault",
      spawnFn,
      execFileSyncFn,
    });

    const result = transport.launchRuntimeInstaller("install", "1.5.15");

    expect(result.ok).toBe(false);
    expect(result.error).toContain("Python 3.11+");
    expect(spawnFn).not.toHaveBeenCalled();
  });
});
