/**
 * LongTaskClient — THE single long-task transport (T8 closure #169).
 *
 * Structured-stream mode (#137): NDJSON events + EXACTLY ONE terminal
 * (result | error | cancelled) then EOF.  The parser is STATEFUL and fails
 * closed per the frozen protocol table:
 *
 *   non-JSON line / bad schema_version / unknown event / second terminal /
 *   event after terminal / EOF without terminal → protocol failure.
 *
 * Cancellation: Stop → stdin `PAPERFORGE_STOP\n` → grace window → hard
 * escalation (Windows `taskkill /T /F`, POSIX process-group SIGKILL).
 */

import { spawn, type ChildProcess } from "child_process";
import { paperforgeEnrichedEnv } from "./python-bridge";

export interface NdjsonEvent {
  schema_version: number;
  event: string;
  operation: string;
  total?: number;
  current?: number;
  item_id?: string;
  status?: string;
  result?: Record<string, unknown> | null;
  [key: string]: unknown;
}

const KNOWN_EVENTS: ReadonlySet<string> = new Set([
  "start",
  "phase",
  "progress",
  "item_result",
  "result",
  "error",
  "cancelled",
]);
const TERMINAL_EVENTS: ReadonlySet<string> = new Set([
  "result",
  "error",
  "cancelled",
]);

/** Stateful, protocol-fail-closed NDJSON stream parser (#137 §5). */
export class NdjsonStreamParser {
  private _buffer = "";
  private _terminalSeen = false;
  private _protocolFailure: string | undefined;

  get protocolFailure(): string | undefined {
    return this._protocolFailure;
  }

  get terminalSeen(): boolean {
    return this._terminalSeen;
  }

  /** Feed a raw chunk; returns the parsed events (empty after failure). */
  feed(chunk: string): NdjsonEvent[] {
    if (this._protocolFailure) return [];
    const full = this._buffer + chunk;
    const lines = full.split("\n");
    this._buffer = lines.pop() ?? "";

    const out: NdjsonEvent[] = [];
    for (const line of lines) {
      if (!line.trim()) continue;
      let parsed: NdjsonEvent;
      try {
        parsed = JSON.parse(line) as NdjsonEvent;
      } catch {
        this._protocolFailure = `non-JSON stdout line: ${line.slice(0, 80)}`;
        break;
      }
      if (parsed.schema_version !== 1) {
        this._protocolFailure = `schema_version ${parsed.schema_version} != 1`;
        break;
      }
      if (typeof parsed.event !== "string" || !KNOWN_EVENTS.has(parsed.event)) {
        this._protocolFailure = `unknown event: ${String(parsed.event)}`;
        break;
      }
      if (this._terminalSeen) {
        this._protocolFailure = "event after terminal";
        break;
      }
      if (TERMINAL_EVENTS.has(parsed.event)) {
        this._terminalSeen = true;
      }
      out.push(parsed);
    }
    return out;
  }

  /** EOF without a terminal event is a protocol failure. */
  finishEOF(): void {
    if (!this._protocolFailure && !this._terminalSeen) {
      this._protocolFailure = "EOF without terminal event";
    }
  }
}

export interface LongTaskOptions {
  onEvent: (event: NdjsonEvent) => void;
  env?: Record<string, string | undefined>;
  /** Grace window after the stop token before hard escalation. */
  graceMs?: number;
}

export interface LongTaskOutcome {
  ok: boolean;
  exitCode: number | null;
  cancelled: boolean;
  events: NdjsonEvent[];
  protocolFailure?: string;
}

export interface LongTaskHandle {
  /** Cooperative stop: stdin token, then grace, then hard escalation. */
  stop: () => void;
  promise: Promise<LongTaskOutcome>;
}

function hardKill(child: ChildProcess): void {
  if (!child.pid) return;
  if (process.platform === "win32") {
    try {
      spawn("taskkill", ["/T", "/F", "/PID", String(child.pid)], {
        stdio: "ignore",
      });
    } catch {
      child.kill("SIGKILL");
    }
  } else {
    try {
      // Process-group kill (detached children live in their own group).
      process.kill(-child.pid, "SIGKILL");
    } catch {
      child.kill("SIGKILL");
    }
  }
}

/**
 * THE single structured-stream client.  Spawns with shell:false, pipes
 * stdin for the cooperative stop token, parses stdout with the stateful
 * protocol-fail-closed parser, escalates hard after the grace window.
 * Env is the redacted paperforgeEnrichedEnv() unless explicitly provided —
 * never merged with process.env.
 */
export function runLongTask(
  pythonExe: string,
  extraArgs: string[],
  vaultPath: string,
  argv: string[],
  opts: LongTaskOptions
): LongTaskHandle {
  const env = opts.env ?? paperforgeEnrichedEnv();
  const child = spawn(
    pythonExe,
    [...extraArgs, "-m", "paperforge", "--vault", vaultPath, ...argv],
    {
      cwd: vaultPath,
      shell: false,
      windowsHide: true,
      env,
      stdio: ["pipe", "pipe", "pipe"],
    }
  );

  const parser = new NdjsonStreamParser();
  const events: NdjsonEvent[] = [];
  let hardKilled = false;
  let graceTimer: ReturnType<typeof setTimeout> | null = null;

  child.stdout?.setEncoding("utf-8");
  child.stdout?.on("data", (chunk: string) => {
    for (const ev of parser.feed(chunk)) {
      events.push(ev);
      opts.onEvent(ev);
    }
  });

  const outcome = new Promise<LongTaskOutcome>((resolve) => {
    child.on("close", (code: number | null) => {
      if (graceTimer) clearTimeout(graceTimer);
      parser.finishEOF();
      resolve({
        ok: !parser.protocolFailure && code === 0,
        exitCode: code,
        cancelled: code === 130,
        events,
        protocolFailure: parser.protocolFailure,
      });
    });
    child.on("error", (err: Error) => {
      if (graceTimer) clearTimeout(graceTimer);
      resolve({
        ok: false,
        exitCode: -1,
        cancelled: false,
        events,
        protocolFailure: `spawn error: ${err.message}`,
      });
    });
  });

  return {
    stop: () => {
      try {
        child.stdin?.write("PAPERFORGE_STOP\n");
      } catch {
        // stdin closed — the exit path still settles.
      }
      if (graceTimer) return;
      const graceMs = opts.graceMs ?? 5000;
      graceTimer = setTimeout(() => {
        if (child.exitCode === null && !hardKilled) {
          hardKilled = true;
          hardKill(child);
        }
      }, graceMs);
    },
    promise: outcome,
  };
}
