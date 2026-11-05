/**
 * External runtime installer launcher.
 *
 * Authority split (unchanged): only the external installer creates/verifies
 * candidate environments and publishes the machine pointer. The plugin never
 * runs pip, never creates a venv, never writes the pointer — it only opens a
 * terminal that runs the installer, then polls the published pointer.
 *
 * This module is pure command construction; the spawn itself stays in the
 * single child-process authority (`client/node-transport.ts`).
 */

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

/** Windows batch script — avoids every nested-quoting layer of `cmd /k`. */
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
    ":paperforge_done",
    "",
  ].join("\r\n");
}

/** POSIX script content for macOS Terminal windows. */
export function macInstallerScript(shellCommand: string): string {
  return `#!/bin/sh\n${shellCommand}\nprintf '\\n[done — press enter to close]'\nread _\n`;
}

export interface TerminalLaunch {
  command: string;
  args: string[];
}

/**
 * Terminal that stays open after the command finishes, so the user can read
 * the installer output instead of watching a window vanish.
 */
export function terminalLaunch(
  platform: NodeJS.Platform,
  options: { comSpec?: string; scriptPath: string }
): TerminalLaunch {
  if (platform === "win32") {
    return {
      command: options.comSpec || "C:\\Windows\\System32\\cmd.exe",
      // start with an empty title argument, then cmd /k to keep the console.
      args: ["/c", "start", "", "cmd.exe", "/k", options.scriptPath],
    };
  }
  if (platform === "darwin") {
    return {
      command: "open",
      args: ["-a", "Terminal", options.scriptPath],
    };
  }
  return {
    command: "x-terminal-emulator",
    args: ["-e", "sh", options.scriptPath],
  };
}
