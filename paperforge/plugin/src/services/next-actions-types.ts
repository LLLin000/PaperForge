/**
 * Next-action wire types (T8 closure #169).
 *
 * Policy authority is the Python registry — the wire carries the resolved
 * descriptor fields.  TS renders and executes; it never re-derives policy.
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

const _inFlight = new Set<string>();

/** Test hook: clear in-flight tracking between scenarios. */
export function resetNextActionTracker(): void {
  _inFlight.clear();
}

export const trackerDeps = {
  isInFlight: (key: string) => _inFlight.has(key),
  markInFlight: (key: string) => _inFlight.add(key),
  clearInFlight: (key: string) => _inFlight.delete(key),
};
