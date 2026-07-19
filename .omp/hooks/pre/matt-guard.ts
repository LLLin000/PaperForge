import { execFileSync } from "node:child_process";
import path from "node:path";
import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";

const READ_ONLY_AGENTS: Record<string, true> = {
  scout: true,
  reviewer: true,
  librarian: true,
};
const RELEASE_COMMAND =
  /\bgit(?:\.exe)?\b[^\r\n;&|]*\b(?:commit|merge|push)\b|\bgh(?:\.exe)?\s+(?:issue\s+close|pr\s+(?:create|merge))\b/i;
const VERIFICATION_COMMAND =
  /\b(?:pytest|unittest|vitest|jest|ruff|mypy|pyright|tsc)\b|\b(?:npm|pnpm|yarn|bun)\s+(?:test|run\s+(?:test|typecheck|build|lint))\b|\bcargo\s+(?:test|check)\b|\bgo\s+test\b|\bdotnet\s+test\b/i;
const URI = /^[a-z][a-z0-9+.-]*:\/\//i;

interface GuardState {
  verifiedAfterMutation: boolean;
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object"
    ? (value as Record<string, unknown>)
    : {};
}

function json(value: unknown): Record<string, unknown> {
  try {
    return record(JSON.parse(String(value ?? "")));
  } catch {
    return {};
  }
}

function runGit(cwd: string, args: string[]): string {
  try {
    return execFileSync("git", args, {
      cwd,
      encoding: "utf8",
      windowsHide: true,
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return "";
  }
}

function normalized(value: string): string {
  const resolved = path.resolve(value);
  return process.platform === "win32" ? resolved.toLowerCase() : resolved;
}

function isWithin(root: string, candidate: string): boolean {
  const relative = path.relative(root, candidate);
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

function crossesWorktrees(candidate: string, cwd: string): boolean {
  if (!candidate || URI.test(candidate)) return false;

  const current = runGit(cwd, ["rev-parse", "--show-toplevel"]);
  if (!current) return false;

  const target = normalized(path.resolve(cwd, candidate));
  const currentRoot = normalized(current);
  const worktrees = runGit(cwd, ["worktree", "list", "--porcelain"])
    .split(/\r?\n/)
    .filter((line) => line.startsWith("worktree "))
    .map((line) => normalized(line.slice("worktree ".length)));
  return worktrees.some(
    (root) => root !== currentRoot && isWithin(root, target),
  );
}

function pathsFromCall(toolName: string, input: unknown): string[] {
  const fields = record(input);

  if (toolName === "edit") {
    const patch = typeof input === "string" ? input : String(fields.input ?? "");
    return [...patch.matchAll(/^\[([^#\r\n]+)#[0-9A-F]{4}\]$/gm)].map(
      (match) => match[1],
    );
  }

  if (toolName === "ast_edit") {
    return Array.isArray(fields.paths) ? fields.paths.map(String) : [];
  }

  if (toolName === "lsp") {
    return typeof fields.file === "string" ? [fields.file] : [];
  }

  if (toolName !== "write") return [];
  const target = String(fields.path ?? "");
  if (target === "xd://ast_edit") {
    const payload = json(fields.content);
    return Array.isArray(payload.paths) ? payload.paths.map(String) : [];
  }
  if (target === "xd://lsp") {
    const payload = json(fields.content);
    return typeof payload.file === "string" ? [payload.file] : [];
  }
  return URI.test(target) ? [] : [target];
}

function tasksFromCall(input: unknown): Record<string, unknown>[] {
  const tasks = record(input).tasks;
  return Array.isArray(tasks) ? tasks.map(record) : [];
}

function hasWriterTask(input: unknown): boolean {
  return tasksFromCall(input).some(
    (task) => READ_ONLY_AGENTS[String(task.agent ?? "")] !== true,
  );
}

function isMutatingCall(toolName: string, input: unknown): boolean {
  if (toolName === "edit" || toolName === "ast_edit") return true;
  if (toolName === "task") return hasWriterTask(input);
  if (toolName === "lsp") {
    const fields = record(input);
    return (
      fields.action === "rename" ||
      fields.action === "rename_file" ||
      (fields.action === "code_actions" && fields.apply === true)
    );
  }
  if (toolName !== "write") return false;

  const fields = record(input);
  const target = String(fields.path ?? "");
  if (!URI.test(target)) return true;
  if (target === "xd://ast_edit") return true;
  if (target !== "xd://lsp") return false;

  const payload = json(fields.content);
  return (
    payload.action === "rename" ||
    payload.action === "rename_file" ||
    (payload.action === "code_actions" && payload.apply === true)
  );
}

function releaseAction(toolName: string, input: unknown): boolean {
  const fields = record(input);
  if (toolName === "bash") return RELEASE_COMMAND.test(String(fields.command ?? ""));
  if (toolName === "github") {
    return ["pr_create", "pr_push"].includes(String(fields.op ?? ""));
  }
  if (toolName !== "write" || fields.path !== "xd://github") return false;
  return ["pr_create", "pr_push"].includes(String(json(fields.content).op ?? ""));
}

function successfulVerification(event: Record<string, unknown>): boolean {
  if (event.toolName !== "bash" || event.isError === true) return false;
  const input = record(event.input);
  if (!VERIFICATION_COMMAND.test(String(input.command ?? ""))) return false;

  const details = record(event.details);
  const exitCode = details.exitCode ?? details.exit_code ?? details.code;
  if (typeof exitCode === "number") return exitCode === 0;

  const content = Array.isArray(event.content) ? event.content : [];
  const text = content.map((chunk) => String(record(chunk).text ?? "")).join("\n");
  return !/command exited with code\s+[1-9]\d*/i.test(text);
}

export default function mattGuard(pi: ExtensionAPI): void {
  const state: GuardState = { verifiedAfterMutation: false };

  pi.on("tool_call", async (event, ctx) => {
    const toolName = String(event.toolName);
    const input = event.input;

    if (toolName === "task") {
      const tasks = tasksFromCall(input);
      if (tasks.length > 1 && hasWriterTask(input)) {
        return {
          block: true,
          reason:
            "Matt guard: parallel task batches may contain only scout, reviewer, or librarian agents. Use one writer.",
        };
      }
    }

    const crossWorktree = pathsFromCall(toolName, input).find((candidate) =>
      crossesWorktrees(candidate, ctx.cwd),
    );
    if (crossWorktree) {
      return {
        block: true,
        reason: `Matt guard: refusing write into another Git worktree: ${crossWorktree}`,
      };
    }

    if (releaseAction(toolName, input) && !state.verifiedAfterMutation) {
      return {
        block: true,
        reason:
          "Matt guard: run the issue-specific verification gate after the last mutation before commit, merge, push, PR creation, or issue close.",
      };
    }

    if (isMutatingCall(toolName, input)) state.verifiedAfterMutation = false;
  });

  pi.on("tool_result", async (event) => {
    if (successfulVerification(event as unknown as Record<string, unknown>)) {
      state.verifiedAfterMutation = true;
    }
  });
}
