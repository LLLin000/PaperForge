import { execFileSync } from "node:child_process";
import path from "node:path";
import { describe, expect, test } from "bun:test";

import register from "./matt-guard";

type Handler = (
  event: Record<string, unknown>,
  context?: { cwd: string },
) => unknown | Promise<unknown>;

const root = path.resolve(import.meta.dir, "../../..");

function handlers() {
  const registered: Record<string, Handler> = {};
  register({
    on: (event: string, handler: Handler) => {
      registered[event] = handler;
    },
  } as unknown as Parameters<typeof register>[0]);
  return registered;
}

function foreignWorktree(): string | undefined {
  const current = path.normalize(root).toLowerCase();
  return execFileSync("git", ["worktree", "list", "--porcelain"], {
    cwd: root,
    encoding: "utf8",
  })
    .split(/\r?\n/)
    .filter((line) => line.startsWith("worktree "))
    .map((line) => path.normalize(line.slice("worktree ".length)))
    .find((worktree) => worktree.toLowerCase() !== current);
}

describe("Matt workflow guard", () => {
  test("allows parallel read-only agents and blocks a writer", async () => {
    const hook = handlers();
    const context = { cwd: root };

    expect(
      await hook.tool_call(
        {
          toolName: "task",
          input: { tasks: [{ agent: "reviewer" }, { agent: "scout" }] },
        },
        context,
      ),
    ).toBeUndefined();
    expect(
      await hook.tool_call(
        {
          toolName: "task",
          input: { tasks: [{ agent: "reviewer" }, {}] },
        },
        context,
      ),
    ).toMatchObject({ block: true });
  });

  test("requires verification after the latest mutation", async () => {
    const hook = handlers();
    const context = { cwd: root };
    const commit = { toolName: "bash", input: { command: "git commit --dry-run" } };

    expect(await hook.tool_call(commit, context)).toMatchObject({ block: true });
    await hook.tool_result({
      toolName: "bash",
      input: { command: "npm test" },
      isError: false,
      details: { exitCode: 0 },
    });
    expect(await hook.tool_call(commit, context)).toBeUndefined();

    await hook.tool_call({ toolName: "edit", input: "mutation" }, context);
    expect(await hook.tool_call(commit, context)).toMatchObject({ block: true });
  });

  test.skipIf(!foreignWorktree())("blocks writes into another linked worktree", async () => {
    const hook = handlers();
    const target = path.join(foreignWorktree()!, "CONTEXT.md");

    expect(
      await hook.tool_call(
        { toolName: "write", input: { path: target } },
        { cwd: root },
      ),
    ).toMatchObject({ block: true });
  });
});
