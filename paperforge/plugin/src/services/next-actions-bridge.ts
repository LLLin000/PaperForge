/**
 * Next-action bridge (T8 closure #169): wires the pure orchestrator to
 * the plugin through ONE injected execution capability — the SAME
 * singleton PaperForgeClient.runAction that just executed the sync
 * (Ticket 07 step 6 item 3).  The bridge never knows the Python
 * executable, `-m paperforge`, env, or runtime resolution: it parses,
 * filters, notifies, and hands ActionRequests to the capability.
 */
import { Notice } from "obsidian";
import { t } from "../i18n";
import { orchestrateNextActions } from "./next-actions-orchestrator";
import { parseNextActions, trackerDeps } from "./next-actions-types";
import type { ActionRequest, ActionRunResult } from "../client/action-contract";

export interface NextActionBridgeContext {
  /** The SAME client instance that executed the sync — next_actions share
   * its epoch/OperationLock semantics with user-initiated actions. */
  runAction: (req: ActionRequest) => Promise<ActionRunResult>;
}

/**
 * Parse and execute the next_actions of a sync PFResult document.
 * Returns the number of actions that were executed to settlement.
 * Automatic intents run inline; everything else is confirmed first
 * (the confirmed request carries the exact `--confirm <id>`).
 */
export async function orchestrateFromSync(
  stdout: string,
  ctx: NextActionBridgeContext
): Promise<number> {
  const actions = parseNextActions(stdout);
  if (actions.length === 0) return 0;

  // Background/manual sync may run local automatic work immediately, but
  // consent-required work stays pending in the Python read model. The module
  // card is the durable place to review and start it; a 120 s convergence
  // tick must never reopen a modal.
  const runnable = actions.filter((action) => {
    if (action.automatic) return true;
    new Notice(t("next_action_pending"), 8000);
    return false;
  });
  if (runnable.length === 0) return 0;

  return orchestrateNextActions(runnable, {
    // No unlocked bypass: an automatic action with a streaming descriptor
    // takes the SAME OperationLock as a user-initiated action — Python's
    // descriptor/policy owns that decision, never this bridge.
    runAction: async (req: ActionRequest): Promise<ActionRunResult> => {
      try {
        const res = await ctx.runAction(req);
        if (res.ok) {
          new Notice(t("next_action_done"));
        } else {
          const err = (res.payload?.error as Record<string, unknown> | null)
            ?.message;
          new Notice(
            t("next_action_failed").replace(
              "{detail}",
              String(err ?? "unknown error")
            )
          );
        }
        return res;
      } catch (err: unknown) {
        new Notice(
          t("next_action_failed").replace(
            "{detail}",
            String((err as Error)?.message ?? err ?? "unknown error")
          )
        );
        return { ok: false, payload: null, exitCode: -1 };
      }
    },
    // Only automatic actions reach this orchestrator call.
    confirm: async () => false,
    notify: (message) => new Notice(message),
    ...trackerDeps,
  });
}
