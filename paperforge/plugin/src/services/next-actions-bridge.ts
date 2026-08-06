/**
 * Next-action bridge (#127 PR C): wires the pure orchestrator to Obsidian.
 *
 * Both manual sync (settings.ts) and auto sync (main.ts) feed the PFResult
 * stdout of `sync --json` here; this module assembles the executor deps
 * (allowlisted argv via execFile, confirmation modal, Notices) and runs the
 * orchestration policy.
 */
import { App, Notice } from "obsidian";
import { execFile } from "child_process";
import { t } from "../i18n";
import {
  orchestrateNextActions,
  parseNextActions,
  type NextAction,
} from "./next-actions-orchestrator";
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
    runAction: (argv) => {
      const py = ctx.resolveCommand(ctx.vaultPath);
      if (!py?.path) {
        new Notice("PaperForge runtime unavailable; follow-up not started");
        return false;
      }
      execFile(
        py.path,
        [...py.args, "-m", "paperforge", ...argv],
        { cwd: ctx.vaultPath, timeout: 120000, windowsHide: true },
        (err) => {
          if (err) {
            new Notice(`Follow-up failed: ${err.message || String(err)}`);
          } else {
            new Notice(t("next_action_done") || "Follow-up completed");
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
  });
}
