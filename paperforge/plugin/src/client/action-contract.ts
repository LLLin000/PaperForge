/**
 * Action contract — the ONE typed action request surface (Ticket 07 Stage 2
 * step 6 item 3).  Neutrally owned by the client layer: `buildActionArgv` is
 * the single authoritative argv constructor and the three DTOs are the wire
 * vocabulary every action surface (client.runAction, next-actions
 * orchestrator/bridge, OCR Workspace) shares.  NO child-process knowledge
 * lives here — execution is Transport-only via PaperForgeClient.
 */

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
  cancelled?: boolean;
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
