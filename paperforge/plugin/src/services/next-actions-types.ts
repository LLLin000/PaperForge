/**
 * Next-action wire types (T8 #169).
 *
 * Policy authority is the Python registry — the wire carries the resolved
 * descriptor fields (automatic/cost/impact/confirmation).  TS never
 * re-derives policy; it only renders and executes.
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
  /** Launch a follow-up via the action client; true only when started. */
  runAction: (argv: string[], action: NextAction) => boolean;
  confirm: (action: NextAction) => Promise<boolean>;
  notify: (message: string) => void;
  isInFlight: (key: string) => boolean;
  hasExecuted: (key: string) => boolean;
  markInFlight: (key: string) => void;
  clearInFlight: (key: string) => void;
  markExecuted: (key: string) => void;
}

const _inFlight = new Set<string>();
const _executed = new Set<string>();

export function resetNextActionTracker(): void {
  _inFlight.clear();
  _executed.clear();
}

export const trackerDeps = {
  isInFlight: (key: string) => _inFlight.has(key),
  hasExecuted: (key: string) => _executed.has(key),
  markInFlight: (key: string) => _inFlight.add(key),
  clearInFlight: (key: string) => _inFlight.delete(key),
  markExecuted: (key: string) => _executed.add(key),
};

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
