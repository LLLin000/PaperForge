/**
 * ActionClient — THE single action transport (T8 closure #169).
 *
 * One argv builder for every action execution surface (CLI dispatch,
 * orchestrator, OCR Workspace): `action run <id> --scope <kind>
 * [--key K ...] [--confirm <exact-id>] [--follow auto] --json`.
 *
 * Env rule (#173/C1): the desktop child env is ALWAYS the redacted
 * paperforgeEnrichedEnv() — never `{...process.env, ...sanitized}` (that
 * re-introduces secret keys) and never the bare process env.
 */

import { runSubprocess, paperforgeEnrichedEnv } from "./python-bridge";

export interface ActionScope {
  kind: string;
  keys?: string[];
}

export interface ActionRequest {
  action_id: string;
  scope: ActionScope;
  /** Exact action id for the confirmation gate (post-user-confirmation). */
  confirm?: string;
  follow?: "none" | "auto";
}

export interface ActionRunResult {
  ok: boolean;
  payload: Record<string, unknown> | null;
  exitCode: number;
}

/** THE one argv builder for action requests. */
export function buildActionArgv(req: ActionRequest): string[] {
  const argv = ["action", "run", req.action_id, "--scope", req.scope.kind];
  if (req.scope.kind === "papers") {
    for (const key of req.scope.keys ?? []) {
      argv.push("--key", key);
    }
  }
  if (req.confirm) {
    argv.push("--confirm", req.confirm);
  }
  if (req.follow === "auto") {
    argv.push("--follow", "auto");
  }
  argv.push("--json");
  return argv;
}

/**
 * Single-result mode: exactly one PFResult JSON on stdout.  The env is the
 * redacted paperforgeEnrichedEnv() — secret env keys never reach the child.
 */
export function runActionRequest(
  pythonExe: string,
  extraArgs: string[],
  vaultPath: string,
  req: ActionRequest,
  timeout = 120000
): Promise<ActionRunResult> {
  const argv = [
    ...extraArgs,
    "-m",
    "paperforge",
    "--vault",
    vaultPath,
    ...buildActionArgv(req),
  ];
  return runSubprocess(
    pythonExe,
    argv,
    vaultPath,
    timeout,
    undefined,
    paperforgeEnrichedEnv()
  ).then((res) => {
    try {
      const payload = JSON.parse(res.stdout) as Record<string, unknown>;
      return {
        ok: payload.ok === true,
        payload,
        exitCode: res.exitCode,
      };
    } catch {
      return { ok: false, payload: null, exitCode: res.exitCode };
    }
  });
}
