/**
 * Client trace — a switchable, redaction-safe diagnostic ring.
 *
 * The thin client is the only place that sees BOTH sides of the boundary
 * (frontend call → argv → PFResult/NDJSON), so it is the right place to
 *  - log stdin payloads (secrets are written over stdin by contract),
 *  - log the child environment (credential-bearing),
 *  - log full argv or flag tokens (values travel as positionals or behind
 *    flags) — only the fixed command + subcommand tokens.
 *
 * Records are metadata: op name, ok, duration, epoch, error code, stream
 * terminal shape. The ring is bounded so a long session cannot grow memory;
 * `dumpTrace()` yields copy-pasteable lines for a bug report.
 *
 * Host-agnostic: console + memory only — no filesystem, no Obsidian API.
 */

export interface TraceRecord {
  ts: number;
  kind: "exec" | "stream" | "action" | "error";
  /** Command identity only (e.g. "sync", "action run"), never values. */
  op: string;
  ok?: boolean;
  ms?: number;
  epoch?: number;
  code?: string;
  detail?: string;
}

const MAX_RECORDS = 200;
const _ring: TraceRecord[] = [];
let _enabled = false;

export function setTraceEnabled(enabled: boolean): void {
  _enabled = enabled;
}

export function isTraceEnabled(): boolean {
  return _enabled;
}

const EXPECTED_STATE_CODES: Record<string, true> = {
  cancelled: true,
  NO_PYTHON: true,
  "action.cancelled": true,
  "action.busy": true,
  "action.unavailable": true,
  "credential.missing": true,
  "credential.input_required": true,
  "credential.confirm_required": true,
};

function isExpectedState(code: string | undefined): boolean {
  if (!code) return false;
  if (EXPECTED_STATE_CODES[code]) return true;
  return code.endsWith(".disabled") || code.endsWith(".not_enabled");
}

/**
 * Stable machine code from a structured PFResult rejection Error.
 * Reads the narrowed `code` field the client attaches, never the free-form
 * message. Unknown shapes stay undefined so callers keep their fallback.
 */
export function rejectionCode(err: unknown): string | undefined {
  if (err === null || typeof err !== "object") return undefined;
  if (!("code" in err)) return undefined;
  const code: unknown = err.code;
  return typeof code === "string" && code.length > 0 ? code : undefined;
}

/**
 * Opaque PFResult data from a structured rejection (`vector_state` lives
 * here). Passed through uninspected — the caller narrows one known field.
 */
export function rejectionData(err: unknown): unknown {
  if (err === null || typeof err !== "object") return undefined;
  if (!("data" in err)) return undefined;
  return err.data;
}

export function traceConsoleError(input: {
  op: string;
  stage: string;
  code: string;
  exitCode?: number | null;
}): void {
  const op = input.op.trim().slice(0, 80) || "unknown";
  const stage = input.stage.trim().slice(0, 40) || "unknown";
  const code = input.code.trim().slice(0, 80) || "backend_error";
  if (isExpectedState(code) || code === "ok") return;
  const exitPart =
    input.exitCode === null || input.exitCode === undefined
      ? "exit=?"
      : `exit=${Math.trunc(input.exitCode)}`;
  console.error(`[PF] failed op=${op} stage=${stage} code=${code} ${exitPart}`);
}
export function traceRecord(record: TraceRecord): void {
  _ring.push(record);
  if (_ring.length > MAX_RECORDS) _ring.splice(0, _ring.length - MAX_RECORDS);
  if (!_enabled) return;
  const parts = [
    `[PF:trace] ${record.kind} ${record.op}`,
    record.ok === undefined ? "" : `ok=${record.ok}`,
    record.ms === undefined ? "" : `${record.ms}ms`,
    record.epoch === undefined ? "" : `epoch=${record.epoch}`,
    record.code ? `code=${record.code}` : "",
    record.detail ? `detail=${record.detail}` : "",
  ].filter(Boolean);
  console.debug(parts.join(" "));
}

export function dumpTrace(): string {
  return _ring
    .map((r) => {
      const time = new Date(r.ts).toISOString().slice(11, 23);
      const parts = [
        time,
        r.kind,
        r.op,
        r.ok === undefined ? "" : `ok=${r.ok}`,
        r.ms === undefined ? "" : `${r.ms}ms`,
        r.epoch === undefined ? "" : `epoch=${r.epoch}`,
        r.code ? `code=${r.code}` : "",
        r.detail ? `detail=${r.detail}` : "",
      ].filter(Boolean);
      return parts.join(" ");
    })
    .join("\n");
}

export function clearTrace(): void {
  _ring.length = 0;
}

/** Fixed subcommand tokens per command family, from the client argv builders.
 * Structural allowlist only — no business registry. Second-position values
 * that are not in their family's set are user data (search/retrieve/
 * reading-log query, module name, paper key, label) and are dropped. Flags
 * are never shown: values travel behind flags (`--key K1`, `--limit 20`).
 * Families with no fixed subcommand (search/retrieve/reading-log/read/
 * paper-status/probe/reconcile/setup/sync/doctor/repair/…) always emit the
 * bare command, whatever the second token contains. */
const SUBCOMMANDS_BY_COMMAND: Record<string, Record<string, true>> = {
  action: { run: true, preflight: true, list: true, describe: true },
  config: { list: true, validate: true, migrate: true, set: true },
  auth: { status: true, set: true },
  memory: { status: true, "restore-backup": true, build: true, rebuild: true },
  embed: { status: true, build: true, migrate: true, resume: true },
  versions: { list: true, show: true, backups: true, paths: true, restore: true },
  note: { "set-flag": true },
  ocr: { list: true },
  render: { audit: true, reconcile: true, "promote-r": true, "accept-proposal": true },
};

/** Command identity for a trace record: the fixed command token, plus the
 * fixed subcommand token only when the family defines one. Never user
 * values (search/retrieve/reading-log query, config value, paper keys) and
 * never flags — so Console lines and dumpTrace stay redacted by
 * construction. */
export function commandIdentity(argv: string[]): string {
  const cmd = argv[0] ?? "";
  if (!cmd || cmd.startsWith("-")) return "unknown";
  const family = SUBCOMMANDS_BY_COMMAND[cmd];
  if (!family) return cmd;
  const sub = argv[1];
  if (sub !== undefined && !sub.startsWith("-") && family[sub]) {
    return `${cmd} ${sub}`;
  }
  return cmd;
}
