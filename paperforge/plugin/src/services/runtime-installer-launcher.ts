/**
 * External runtime installer launcher.
 *
 * Authority split (unchanged): only the external installer creates/verifies
 * candidate environments and publishes the machine pointer. The plugin never
 * runs pip, never creates a venv, never writes the pointer — it runs the
 * installer script as a detached child and polls the published pointer.
 *
 * The script runs WITHOUT a console window: a terminal (`start`, `open -a
 * Terminal`, `x-terminal-emulator`) only exists in an interactive desktop
 * session, so headless hosts (CI, remote desktops, some sandboxes) could never
 * finish a first-use install. Output goes to `installer.log`, which the
 * wizard reads when the poll gives up.
 *
 * This module is pure command construction; the spawn itself stays in the
 * single child-process authority (`client/node-transport.ts`).
 */

import * as os from "os";
import * as path from "path";

export type RuntimeInstallerAction = "install" | "update" | "repair";

const PYTHON_PLACEHOLDER = "{{python}}";

/** The two steps the external installer runs, in order. */
export function runtimeInstallerSteps(
  action: RuntimeInstallerAction,
  version: string
): string[] {
  return [
    `${PYTHON_PLACEHOLDER} -m pip install --user --upgrade paperforge==${version}`,
    `${PYTHON_PLACEHOLDER} -m paperforge runtime ${action} --expected-version ${version}`,
  ];
}

/** One shell line chaining the steps (fails fast on the first error). */
export function runtimeInstallerShellCommand(
  python: string,
  action: RuntimeInstallerAction,
  version: string
): string {
  const quoted = /\s/.test(python) ? `"${python}"` : python;
  return runtimeInstallerSteps(action, version)
    .map((step) => step.replace(PYTHON_PLACEHOLDER, quoted))
    .join(" && ");
}

/** Windows batch script — avoids every nested-quoting layer of `cmd /c`. */
export function windowsInstallerScript(shellCommand: string): string {
  const [first, second] = shellCommand.split(" && ");
  return [
    "@echo off",
    first,
    "if errorlevel 1 goto :paperforge_failed",
    second,
    "goto :paperforge_done",
    ":paperforge_failed",
    "echo.",
    "echo [PaperForge] Installer step failed. Fix the error above and retry.",
    "goto :paperforge_exit",
    ":paperforge_done",
    "echo [PaperForge] Installer finished.",
    ":paperforge_exit",
    "",
  ].join("\r\n");
}

/** POSIX script: same fail-fast semantics and the same terminal markers. */
export function posixInstallerScript(shellCommand: string): string {
  return [
    "#!/bin/sh",
    `if ${shellCommand}; then`,
    '  echo "[PaperForge] Installer finished."',
    "else",
    '  echo "[PaperForge] Installer step failed. Fix the error above and retry."',
    "  exit 1",
    "fi",
    "",
  ].join("\n");
}

/** Markers the poll watches for, so a dead installer is detected at once. */
export const INSTALLER_FINISHED_MARKER = "[PaperForge] Installer finished.";
export const INSTALLER_FAILED_MARKER = "[PaperForge] Installer step failed.";

/** Where the detached installer writes its output. */
export function installerLogPath(home = os.homedir()): string {
  return path.join(home, ".paperforge", "runtime", "installer.log");
}

export interface InstallerRun {
  command: string;
  args: string[];
}

/**
 * Run the script directly. No `start` / Terminal.app / terminal emulator:
 * those need an interactive session and fail silently elsewhere.
 */
export function installerRun(
  platform: NodeJS.Platform,
  options: { comSpec?: string; scriptPath: string }
): InstallerRun {
  if (platform === "win32") {
    return {
      command: options.comSpec || "C:\\Windows\\System32\\cmd.exe",
      args: ["/c", options.scriptPath],
    };
  }
  return { command: "/bin/sh", args: [options.scriptPath] };
}
