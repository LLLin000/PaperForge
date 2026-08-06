/**
 * Next-action orchestrator (#127 PR C).
 *
 * Consumes the `next_actions` payload of a PFResult (produced by the backend
 * command core) and executes follow-ups under a fixed allowlist. The backend
 * never ships command strings; the plugin maps `action_id` → argv here.
 *
 * Policy:
 * - automatic + local + non-destructive → run inline
 * - remote-possible or destructive or confirmation=required → ask first
 * - unknown action_id / schema → refuse (fail closed)
 * - dedupe by `dedupe_key` while in flight
 * - follow-up depth guard (an action's result must not re-enqueue itself)
 */
export interface NextActionScope {
  kind: string;
  keys?: string[];
}

export interface NextAction {
  schema_version: number;
  action_id: string;
  scope: NextActionScope;
  automatic: boolean;
  cost: string;
  impact: string;
  confirmation: string;
  reason: string;
  dedupe_key?: string;
}

export interface OrchestratorDeps {
  /** Launch a follow-up; must return true only when it actually started. */
  runAction: (argv: string[]) => boolean;
  confirm: (action: NextAction) => Promise<boolean>;
  notify: (message: string) => void;
}

export const NEXT_ACTIONS_SCHEMA_VERSION = 1;

/** Fixed plugin-side allowlist: action_id → argv. Unknown ids are refused. */
export const ALLOWED_ACTIONS: Record<
  string,
  { argv: string[]; description: string }
> = {
  "memory.build": {
    argv: ["memory", "build"],
    description: "Rebuild the local memory index",
  },
  "embed.resume": {
    argv: ["embed", "build", "--resume"],
    description:
      "Resume vector embedding for changed papers (may call a paid API)",
  },
};

const _inFlight = new Set<string>();
const _executed = new Set<string>();

/** Test hook: clear in-flight/executed tracking between scenarios. */
export function resetNextActionTracker(): void {
  _inFlight.clear();
  _executed.clear();
}

/** Parse `next_actions` from a PFResult JSON document; malformed → []. */
export function parseNextActions(stdout: string): NextAction[] {
  try {
    const payload = JSON.parse(stdout);
    const actions = payload?.next_actions;
    return Array.isArray(actions) ? (actions as NextAction[]) : [];
  } catch {
    return [];
  }
}

function isAutomaticLocal(action: NextAction): boolean {
  return (
    action.automatic === true &&
    action.cost === "local" &&
    action.impact !== "destructive"
  );
}

function requiresConfirmation(action: NextAction): boolean {
  return (
    action.confirmation === "required" ||
    action.cost === "remote_possible" ||
    action.impact === "destructive"
  );
}

/**
 * Execute a batch of next actions. Returns the number of actions that were
 * started (automatic local + confirmed). Depth > 0 refuses everything except
 * automatic-local (loop guard: remote/confirmed follow-ups must not chain).
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
    const spec = ALLOWED_ACTIONS[action.action_id];
    if (!spec) {
      deps.notify(`Unknown next action '${action.action_id}'; refused`);
      continue;
    }
    const key = action.dedupe_key || action.action_id;
    if (_inFlight.has(key)) continue;
    if (_executed.has(key)) continue;

    if (isAutomaticLocal(action)) {
      _inFlight.add(key);
      let startedNow = false;
      try {
        startedNow = deps.runAction([...spec.argv]) === true;
      } finally {
        _inFlight.delete(key);
      }
      if (startedNow) {
        _executed.add(key);
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
    if (requiresConfirmation(action)) {
      const ok = await deps.confirm(action);
      if (!ok) {
        deps.notify(`Follow-up '${action.action_id}' refused by user`);
        continue;
      }
      _inFlight.add(key);
      let startedNow = false;
      try {
        startedNow = deps.runAction([...spec.argv]) === true;
      } finally {
        _inFlight.delete(key);
      }
      if (startedNow) {
        _executed.add(key);
        started += 1;
      }
    }
  }
  return started;
}
