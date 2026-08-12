/**
 * Next-action orchestrator (T8 closure #169).
 *
 * The backend (registry + reconcile) is the SINGLE policy authority; the
 * wire carries the resolved descriptor fields.  This module has NO
 * action-policy tables and NO argv construction — it builds an
 * ActionRequest and hands it to the ActionClient.
 *
 * State discipline (#169 P0-2): TS keeps ONLY the in-flight
 * duplicate-click guard.  There is NO `_executed` set — cross-invocation
 * re-emission/suppression is owned by the Python W2 gate (input digest +
 * last-attempt), and a later legitimate re-repair of the same scope must
 * never be suppressed by a stale plugin-side mark.
 */
import type { NextAction } from "./next-actions-types";
import type { ActionRequest } from "./action-client";

export { resetNextActionTracker } from "./next-actions-types";

export const NEXT_ACTIONS_SCHEMA_VERSION = 1;

/** Build the ActionRequest for one wire action (confirm passes the exact id). */
export function actionRequestFor(
  action: NextAction,
  confirmed: boolean
): ActionRequest {
  return {
    action_id: action.action_id,
    scope: action.scope ?? { kind: "all" },
    confirm: confirmed ? action.action_id : undefined,
    follow: "auto",
  };
}

/**
 * Execute a batch of next actions. Returns the number of actions that were
 * started. Automatic intents run inline; everything else is confirmed first
 * (the confirmed request carries the exact `--confirm <id>`).  Depth > 0
 * refuses everything except automatic intents (loop guard).
 */
export async function orchestrateNextActions(
  actions: NextAction[],
  deps: {
    runAction: (req: ActionRequest) => boolean;
    confirm: (action: NextAction) => Promise<boolean>;
    notify: (message: string) => void;
    isInFlight: (key: string) => boolean;
    markInFlight: (key: string) => void;
    clearInFlight: (key: string) => void;
  },
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
    const key =
      action.dedupe_key || `${action.action_id}:${action.scope?.kind ?? "all"}`;
    if (deps.isInFlight(key)) continue;

    let confirmed = false;
    if (action.automatic !== true) {
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
      confirmed = true;
    }

    deps.markInFlight(key);
    let startedNow = false;
    try {
      startedNow = deps.runAction(actionRequestFor(action, confirmed)) === true;
    } finally {
      deps.clearInFlight(key);
    }
    if (startedNow) started += 1;
  }
  return started;
}
