import { describe, it, expect, vi } from "vitest";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";

import { NodeProcessTransport, paperforgeEnrichedEnv } from "../src/client/node-transport";
import {
  bootstrapPythonSource,
  installerRun,
  installerShellCommand,
  posixInstallerScript,
  runtimeInstallerShellCommand,
  runtimeInstallerSteps,
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

  it("runs the script without a console (headless hosts must work)", () => {
    expect(
      installerRun("win32", {
        comSpec: "C:\\cmd.exe",
        scriptPath: "C:\\tmp\\installer.cmd",
      })
    ).toEqual({ command: "C:\\cmd.exe", args: ["/c", "C:\\tmp\\installer.cmd"] });
    expect(installerRun("linux", { scriptPath: "/tmp/installer.command" })).toEqual(
      { command: "/bin/sh", args: ["/tmp/installer.command"] }
    );
    expect(installerRun("darwin", { scriptPath: "/tmp/installer.command" })).toEqual(
      { command: "/bin/sh", args: ["/tmp/installer.command"] }
    );
    // POSIX script fails fast like the batch one.
    expect(posixInstallerScript("echo hi")).toContain(
      "[PaperForge] Installer finished."
    );
    expect(posixInstallerScript("echo hi")).toContain(
      "if echo hi; then"
    );
    expect(posixInstallerScript("echo hi")).toContain("echo hi");
    // The batch prints the same markers the wizard polls for.
    expect(windowsInstallerScript("first && second")).toContain(
      "[PaperForge] Installer finished."
    );
  });

  // Windows-only: asserts the .cmd bootstrap, ComSpec launch and the `py`
  // launcher candidate. The Linux/macOS script shapes are covered above.
  it.runIf(process.platform === "win32")(
    "launches the installer without resolving a published runtime",
    () => {
    const spawnFn = vi.fn(() => ({ unref: vi.fn() })) as never;
    const execFileSyncFn = vi.fn((cmd: string, args: string[]) => {
      if (cmd !== "py") throw new Error("missing");
      if (args[0] === "-c") return "C:\\Python312\\python.exe";
      return "Python 3.12.4";
    }) as never;
    const transport = new NodeProcessTransport({
      vaultPath: "C:\\vault",
      spawnFn,
      execFileSyncFn,
      installerLogPath: () => path.join(os.tmpdir(), "pf-installer-test.log"),
    });

    const result = transport.launchRuntimeInstaller("install", "1.5.15");

    expect(result.ok).toBe(true);
    // The installer script must embed the ABSOLUTE interpreter: a bare `py`
    // is not resolvable by the child cmd on hosts where only Node's PATH has
    // the launcher shim (the CI failure that motivated this).
    expect(result.python).toBe("C:\\Python312\\python.exe");
    expect(result.logPath?.endsWith("pf-installer-test.log")).toBe(true);
    const [command, args] = (spawnFn as unknown as ReturnType<typeof vi.fn>).mock
      .calls[0] as [string, string[]];
    expect(command).toBe(process.env.ComSpec || "C:\\Windows\\System32\\cmd.exe");
    const scriptPath = args[args.length - 1];
    expect(scriptPath.endsWith(".cmd")).toBe(true);
    const script = fs.readFileSync(scriptPath, "utf-8");
    expect(script).toContain("paperforge runtime install --expected-version 1.5.15");
    // pip lives in the bootstrap file now: it is skipped when the CLI is
    // already importable at this version.
    const bootstrapMatch = script.match(
      /(?:"([^"]+\.bootstrap\.py)")|(\S+\.bootstrap\.py)/
    );
    expect(bootstrapMatch).toBeTruthy();
    const bootstrap =
      (bootstrapMatch?.[1] ?? bootstrapMatch?.[2]) as string;
    const bootstrapSource = fs.readFileSync(bootstrap, "utf-8");
    expect(bootstrapSource).toContain('"pip"');
    expect(bootstrapSource).toContain('"--user"');
    expect(bootstrapSource).toContain('"paperforge==" + VERSION');
    fs.rmSync(bootstrap, { force: true });
      fs.rmSync(scriptPath, { force: true });
    }
  );

  it("skips the pip step when the CLI is already at the target version", () => {
    const source = bootstrapPythonSource("2.0.0rc5");
    // The version is baked in and compared before any pip call.
    expect(source).toContain('VERSION = "2.0.0rc5"');
    expect(source).toContain('if installed == VERSION:');
    expect(source).toContain('raise SystemExit(0)');
    // PEP 668 interpreters get the only flag that makes --user legal there.
    expect(source).toContain("EXTERNALLY-MANAGED");
    expect(source).toContain("--break-system-packages");
    // The install target is still the user site of the discovered interpreter.
    expect(source).toContain('"--user"');
  });

  it("runs the bootstrap before the CLI install step", () => {
    const command = installerShellCommand(
      "C:\\Python\\python.exe",
      "install",
      "2.0.0rc5",
      "C:\\Temp\\bootstrap.py"
    );
    const [first, second] = command.split(" && ");
    expect(first).toContain("C:\\Temp\\bootstrap.py");
    expect(second).toContain("-m paperforge runtime install");
    // A python path with spaces must stay one token.
    expect(
      installerShellCommand("C:\\Program Files\\Py\\python.exe", "update", "1.0.0", "/tmp/b.py")
    ).toContain('"C:\\Program Files\\Py\\python.exe" /tmp/b.py');
  });

  it("keeps a usable PATH for the installer child", () => {
    const saved = process.env.PATH;
    try {
      delete process.env.PATH;
      const env = paperforgeEnrichedEnv();
      expect(env.PATH && env.PATH.length > 0).toBe(true);
      // Never an empty string: a child with PATH="" resolves nothing.
      expect(env.PATH).not.toBe("");
    } finally {
      if (saved === undefined) delete process.env.PATH;
      else process.env.PATH = saved;
    }
  });

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
