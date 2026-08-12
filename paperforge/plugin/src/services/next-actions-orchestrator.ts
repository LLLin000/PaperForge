/**
 * Next-action orchestrator (T8 #169).
 *
 * The backend (registry + reconcile) is the SINGLE policy authority: the
 * wire carries `action_id`, `scope`, `automatic`, `cost`, `impact`,
 * `confirmation`.  This module has NO action-policy tables — no
 * ALLOWED_ACTIONS, no (verb, command) dispatch, no isAutomaticLocal /
 * requiresConfirmation reimplementation.  Execution argv is derived from
 * the wire: `action run <id> --scope <kind> [--key ...]`.
 *
 * Policy:
 * - automatic intents (registry invariant: local, non-destructive, no
 *   confirmation) run inline
 * - everything else needs the user's confirmation (rendered from the
 *   descriptor fields on the wire)
 * - unknown action_id / schema → refuse (fail closed — but never via a
 *   plugin-side allowlist; the registry already resolved the id)
 * - dedupe by canonical (action_id, normalized scope) while in flight
 * - follow-up depth guard: deeper layers only run automatic intents
 */
import type { OrchestratorDeps, NextAction } from "./next-actions-types";

export { resetNextActionTracker } from "./next-actions-types";

export const NEXT_ACTIONS_SCHEMA_VERSION = 1;

/** Derive the canonical dedupe key: action_id + normalized scope. */
export function actionDedupeKey(action: NextAction): string {
  const keys = action.scope?.kind === "papers" ? (action.scope.keys ?? []) : [];
  const norm = [...new Set(keys)].sort().join(",");
  return `${action.action_id}:${action.scope?.kind ?? "all"}:${norm}`;
}

/** Build the CLI argv for one action from the wire (never a policy table). */
export function buildActionArgv(action: NextAction): string[] {
  const argv = [
    "action",
    "run",
    action.action_id,
    "--scope",
    action.scope?.kind ?? "all",
  ];
  if (action.scope?.kind === "papers" && (action.scope.keys ?? []).length > 0) {
    argv.push("--key", ...(action.scope.keys as string[]));
  }
  return argv;
}

/**
 * Execute a batch of next actions. Returns the number of actions that were
 * started (automatic + confirmed). Depth > 0 refuses everything except
 * automatic intents (loop guard: confirmed follow-ups must not chain).
 */
export async function orchestrateNextActions(
  actions: NextAction[],
  deps: OrchestratorDeps,
  depth = 0
): Promise<number> {
  let started = 0;
  for (const action of actions) {
    if (action.schema_version !== NEXT_ACTIONS_SCHEMA_VERSION) {
      deps.notify(
        `Unknown next-action schema v${action.schema_version}; refused`
      );
      continue;
    }
    if (!action.action_id) {
      deps.notify("Next action without action_id; refused");
      continue;
    }
    const key = action.dedupe_key || actionDedupeKey(action);
    if (deps.isInFlight(key)) continue;
    if (deps.hasExecuted(key)) continue;

    if (action.automatic === true) {
      deps.markInFlight(key);
      let startedNow = false;
      try {
        startedNow = deps.runAction(buildActionArgv(action), action) === true;
      } finally {
        deps.clearInFlight(key);
      }
      if (startedNow) {
        deps.markExecuted(key);
        started += 1;
      }
      continue;
    }

    if (depth > 0) {
      deps.notify(
        `Follow-up depth exceeded for '${action.action_id}'; skipped`
      );
      continue;
    }
    const ok = await deps.confirm(action);
    if (!ok) {
      deps.notify(`Follow-up '${action.action_id}' refused by user`);
      continue;
    }
    deps.markInFlight(key);
    let startedNow = false;
    try {
      startedNow = deps.runAction(buildActionArgv(action), action) === true;
    } finally {
      deps.clearInFlight(key);
    }
    if (startedNow) {
      deps.markExecuted(key);
      started += 1;
    }
  }
  return started;
}
