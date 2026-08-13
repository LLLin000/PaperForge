/**
 * Next-action bridge (T8 closure #169): wires the pure orchestrator to
 * Obsidian through the ONE ActionClient.  Executes with the redacted
 * desktop env (never the bare process env).
 */
import { Notice } from "obsidian";
import { t } from "../i18n";
import { orchestrateNextActions } from "./next-actions-orchestrator";
import { parseNextActions, trackerDeps } from "./next-actions-types";
import { runActionRequest, type ActionRequest } from "./action-client";

export interface NextActionBridgeContext {
  vaultPath: string;
  resolveCommand: (
    vaultPath: string
  ) => { path: string; args: string[] } | null;
}

/**
 * Parse and execute the next_actions of a sync PFResult document.
 * Returns the number of actions started (0 when nothing to do).
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
    runAction: (req: ActionRequest): boolean => {
      const py = ctx.resolveCommand(ctx.vaultPath);
      if (!py?.path) {
        new Notice(t("next_action_runtime_unavailable"));
        return false;
      }
      void runActionRequest(py.path, py.args, ctx.vaultPath, req).then(
        (res) => {
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
        }
      );
      return true;
    },
    // Only automatic actions reach this orchestrator call.
    confirm: async () => false,
    notify: (message) => new Notice(message),
    ...trackerDeps,
  });
}
