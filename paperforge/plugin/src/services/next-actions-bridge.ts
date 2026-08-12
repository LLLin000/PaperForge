/**
 * Next-action bridge (T8 closure #169): wires the pure orchestrator to
 * Obsidian through the ONE ActionClient.  Executes with the redacted
 * desktop env (never the bare process env).
 */
import { App, Notice } from "obsidian";
import { t } from "../i18n";
import { orchestrateNextActions } from "./next-actions-orchestrator";
import {
  parseNextActions,
  trackerDeps,
  type NextAction,
} from "./next-actions-types";
import { runActionRequest, type ActionRequest } from "./action-client";
import { NextActionConfirmModal } from "../views/modals";

export interface NextActionBridgeContext {
  app: App;
  vaultPath: string;
  resolveCommand: (
    vaultPath: string
  ) => { path: string; args: string[] } | null;
}

const _ACTION_TITLES: Record<string, string> = {
  "embed.resume": "next_action_embed_title",
  "memory.build": "next_action_memory_started",
};

const _ACTION_BODIES: Record<string, string> = {
  "embed.resume": "next_action_embed_body",
};

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
  return orchestrateNextActions(actions, {
    runAction: (req: ActionRequest): boolean => {
      const py = ctx.resolveCommand(ctx.vaultPath);
      if (!py?.path) {
        new Notice("PaperForge runtime unavailable; follow-up not started");
        return false;
      }
      void runActionRequest(py.path, py.args, ctx.vaultPath, req).then(
        (res) => {
          if (res.ok) {
            new Notice(t("next_action_done") || "Follow-up completed");
          } else {
            const err = (res.payload?.error as Record<string, unknown> | null)
              ?.message;
            new Notice(`Follow-up failed: ${String(err ?? "unknown error")}`);
          }
        }
      );
      return true;
    },
    confirm: (action: NextAction) =>
      new Promise<boolean>((resolve) => {
        const titleKey = _ACTION_TITLES[action.action_id];
        const bodyKey = _ACTION_BODIES[action.action_id];
        new NextActionConfirmModal(
          ctx.app,
          (titleKey && t(titleKey)) || action.action_id,
          (bodyKey && t(bodyKey)) || action.reason,
          resolve
        ).open();
      }),
    notify: (message) => new Notice(message),
    ...trackerDeps,
  });
}
