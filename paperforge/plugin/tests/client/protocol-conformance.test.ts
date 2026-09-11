/**
 * Protocol conformance through the REAL Python process.
 *
 * Layer: real-process integration. A mocked transport cannot prove that the
 * Python side emits what this side parses, so every assertion here spawns
 * `python -m paperforge` and reads its real stdout, stderr and exit code.
 *
 * The interpreter is pinned through `resolveRuntime` because the managed
 * runtime pointer is machine-local; CI installs the package into the job's
 * Python for the same reason.
 *
 * A temp copy of the committed `test/vaults/simple` vault is used for every
 * case, so a command that unexpectedly writes cannot dirty the repository —
 * and the read-only case can hash the whole tree.
 */
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import {
  cpSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  rmSync,
  statSync,
} from "node:fs";
import { tmpdir } from "node:os";
import * as path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { NodeProcessTransport } from "../../src/client/node-transport";
import type { NdjsonEvent } from "../../src/client/transport";

const PLUGIN_DIR = process.cwd();
const REPO_ROOT = path.resolve(PLUGIN_DIR, "..", "..");
const SIMPLE_VAULT = path.resolve(PLUGIN_DIR, "test", "vaults", "simple");

// The CLI is spawned from the plugin directory, where `import paperforge`
// only resolves if the package is installed — locally it is not (the repo is
// importable through cwd), so the repository root goes on PYTHONPATH. The
// transport still applies its own sanitized environment on top; this only
// makes the package findable.
process.env.PYTHONPATH = [REPO_ROOT, process.env.PYTHONPATH]
  .filter(Boolean)
  .join(path.delimiter);
/**
 * An interpreter that can actually import paperforge.
 *
 * `python` on PATH is not necessarily the one CI provisioned: with
 * setup-python the tool cache holds the package while `/usr/bin/python` is a
 * different installation, and the failure looks like a broken product rather
 * than a wrong interpreter. Candidates are probed in order and the message
 * names what was tried.
 */
function resolveInterpreter(): string {
  const candidates = [process.env.PF_PYTHON, "python3", "python"].filter(
    (value): value is string => Boolean(value)
  );
  const tried: string[] = [];
  for (const candidate of candidates) {
    try {
      // `import paperforge` is not enough: a different interpreter can import
      // the source through PYTHONPATH while lacking the package's own
      // dependencies (filelock), and the failure then looks like a broken
      // product. Prove the CLI entry point actually loads.
      execFileSync(candidate, ["-m", "paperforge", "--version"], {
        stdio: "ignore",
        cwd: REPO_ROOT,
      });
      return candidate;
    } catch (error) {
      const reason = String((error as Error).message ?? error)
        .split("\n")[0]
        .slice(0, 120);
      tried.push(`${candidate} (${reason})`);
    }
  }
  throw new Error(
    `no interpreter can import paperforge; tried: ${tried.join(" | ")}. ` +
      "set PF_PYTHON to the interpreter the package is installed into"
  );
}

const PYTHON = resolveInterpreter();

/** #137 froze this vocabulary; a new event name is a contract change. */
const FROZEN_EVENTS = new Set([
  "start",
  "preflight",
  "phase",
  "progress",
  "paper_settled",
  "heartbeat",
  "item_result",
  "result",
  "error",
  "cancelled",
]);
const TERMINAL_EVENTS = new Set(["result", "error", "cancelled"]);

/** Registry policy, measured from `action list --json` (9 actions). */
const CONFIRMATION_REQUIRED = [
  "embed.build",
  "embed.resume",
  "foundation.repair",
  "foundation.update",
  "library.prune",
  "memory.build",
  "memory.rebuild",
  "ocr.run",
];
const STREAM_ACTIONS = [
  "embed.build",
  "embed.resume",
  "foundation.update",
  "ocr.rebuild_derived",
  "ocr.run",
];

function hashTree(root: string): string {
  const hash = createHash("sha256");
  const walk = (dir: string): void => {
    for (const entry of readdirSync(dir, { withFileTypes: true }).sort((a, b) =>
      a.name.localeCompare(b.name)
    )) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else {
        hash.update(path.relative(root, full).split(path.sep).join("/"));
        hash.update(readFileSync(full));
      }
    }
  };
  walk(root);
  return hash.digest("hex");
}

let vault = "";
let transport: NodeProcessTransport;

beforeAll(() => {
  vault = mkdtempSync(path.join(tmpdir(), "pf-protocol-"));
  cpSync(SIMPLE_VAULT, vault, { recursive: true });
  transport = new NodeProcessTransport({
    vaultPath: vault,
    resolveRuntime: async () => ({ path: PYTHON, args: [] }),
  });
});

afterAll(() => {
  if (vault) rmSync(vault, { recursive: true, force: true });
});

// Each case spawns the real CLI (some of them several times), so the default
// 5s budget is not enough once the rest of the suite runs in parallel.
describe(
  "Protocol conformance (real Python process)",
  { timeout: 30_000 },
  () => {
    it("emits exactly one JSON object on stdout, and nothing else", async () => {
      // Two output contracts share the stream: command results are PFResult
      // envelopes, module probes are schema-v2 capability envelopes.
      const result = await transport.execute(["config", "paths", "--json"]);
      const resultText = result.trim();
      // A prefix (banner, ANSI, a stray print) would break every consumer that
      // parses stdout, so the whole stream must be the one object.
      expect(resultText.startsWith("{")).toBe(true);
      expect(resultText.endsWith("}")).toBe(true);
      const envelope = JSON.parse(resultText) as Record<string, unknown>;
      expect(Object.keys(envelope)).toEqual(
        expect.arrayContaining(["ok", "command", "version", "data"])
      );
      expect(envelope.ok).toBe(true);
      expect(typeof envelope.command).toBe("string");

      const probe = JSON.parse(
        (await transport.execute(["probe", "installation", "--json"])).trim()
      ) as Record<string, unknown>;
      expect(probe.schema_version).toBe(2);
      expect(probe.module).toBe("installation");
      // These are the fields the plugin renders from; a probe that stops
      // emitting them would leave the UI with nothing to show.
      for (const field of [
        "capability_state",
        "activity_state",
        "user_state",
        "severity",
      ]) {
        expect(typeof probe[field]).toBe("string");
      }
    });

    it("keeps stderr diagnostics out of stdout", async () => {
      // --verbose turns on DEBUG-level output, which belongs on stderr; if the
      // two streams were merged the parse below would fail.
      const stdout = await transport.execute([
        "--verbose",
        "probe",
        "installation",
        "--json",
      ]);
      expect(() => JSON.parse(stdout.trim())).not.toThrow();
    });

    it("returns plain text (not an envelope) when --json is absent", async () => {
      const stdout = await transport.execute(["paths"]);
      expect(stdout.trimStart().startsWith("{")).toBe(false);
      expect(stdout).toContain("system:");
      expect(stdout).toContain("vault:");
    });

    it("refuses an unknown action id instead of guessing", async () => {
      await expect(
        transport.execute(["action", "describe", "no.such.action", "--json"])
      ).rejects.toMatchObject({ exitCode: 2 });
    });

    it("refuses a scope the action does not accept", async () => {
      // memory.rebuild is all-scope only; a papers scope must be a validation
      // failure (exit 2), not a silently ignored argument.
      await expect(
        transport.execute([
          "action",
          "run",
          "memory.rebuild",
          "--scope",
          "papers",
          "--key",
          "NOPE",
          "--json",
        ])
      ).rejects.toMatchObject({ exitCode: 2 });
    });

    it("refuses a confirmation-required action without confirmation, before any work", async () => {
      // Which gate fires first depends on the environment: preflight precedes
      // the confirmation gate, so an unavailable action reports why it cannot
      // run (1) instead of asking for consent. What must hold everywhere is
      // that the exit code matches the reported availability, and that the
      // action never runs.
      const { PaperForgeClient } =
        await import("../../src/client/paperforge-client");
      const client = new PaperForgeClient({ transport });

      for (const actionId of CONFIRMATION_REQUIRED) {
        const descriptor = await client.describeAction(actionId);
        const expected = descriptor.availability === "available" ? 3 : 1;
        await expect(
          transport.execute([
            "action",
            "run",
            actionId,
            "--scope",
            "all",
            "--json",
          ]),
          `${actionId} reported availability=${descriptor.availability}`
        ).rejects.toMatchObject({ exitCode: expected });
      }
    });

    it("reports the registry policy through the client boundary", async () => {
      const { PaperForgeClient } =
        await import("../../src/client/paperforge-client");
      const client = new PaperForgeClient({ transport });

      const actions = await client.listActions();
      const byId = new Map(actions.map((a) => [a.action_id, a]));
      expect([...byId.keys()].sort()).toEqual(
        [
          "embed.build",
          "embed.resume",
          "foundation.repair",
          "foundation.update",
          "library.prune",
          "memory.build",
          "memory.rebuild",
          "ocr.rebuild_derived",
          "ocr.run",
        ].sort()
      );

      for (const actionId of CONFIRMATION_REQUIRED) {
        expect(byId.get(actionId)?.confirmation).toBe("required");
      }
      // The action pipeline routes on this field, so a wrong mode would send a
      // streaming action down the single-result path (or the reverse).
      for (const actionId of STREAM_ACTIONS) {
        expect(byId.get(actionId)?.execution_mode).toBe("stream");
      }
    });

    it("streams a frozen-vocabulary NDJSON sequence with exactly one terminal", async () => {
      const handle = transport.stream([
        "action",
        "run",
        "ocr.rebuild_derived",
        "--scope",
        "all",
        "--json",
      ]);
      const events: NdjsonEvent[] = [];
      for await (const event of handle.events) {
        events.push(event);
      }
      const outcome = await handle.outcome;

      expect(events.length).toBeGreaterThan(0);
      for (const event of events) {
        expect(event.schema_version).toBe(1);
        expect(FROZEN_EVENTS.has(String(event.event))).toBe(true);
        expect(typeof event.operation).toBe("string");
      }
      const terminals = events.filter((e) =>
        TERMINAL_EVENTS.has(String(e.event))
      );
      expect(terminals).toHaveLength(1);
      // The terminal must be last: anything after it is a protocol violation.
      expect(events[events.length - 1]).toBe(terminals[0]);
      expect(outcome.exitCode).toBe(0);
      expect(
        typeof (terminals[0].result as Record<string, unknown> | null)?.ok
      ).toBe("boolean");
    });

    it("leaves the vault byte-identical for the read-only surfaces", async () => {
      const before = hashTree(vault);
      const { PaperForgeClient } =
        await import("../../src/client/paperforge-client");
      const client = new PaperForgeClient({ transport });

      await client.listActions();
      await client.describeAction("ocr.run");
      await client.preflightAction("ocr.run", { kind: "all" });
      await client.reconcile("all");

      // A query that writes is how a "read-only" surface corrupts state the user
      // never asked to change (plan X13).
      expect(hashTree(vault)).toBe(before);
    });
  }
);
