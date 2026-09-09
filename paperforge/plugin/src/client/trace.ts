/**
 * Client trace — a switchable, redaction-safe diagnostic ring.
 *
 * The thin client is the only place that sees BOTH sides of the boundary
 * (frontend call → argv → PFResult/NDJSON), so it is the right place to
 * record what crossed it. What this MUST NOT do:
 *  - log stdin payloads (secrets are written over stdin by contract),
 *  - log the child environment (credential-bearing),
 *  - log full argv (values may be paths/keys) — only the subcommand tokens.
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

/** Copy-pasteable trace lines (works even while tracing is off). */
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

/** Command identity for a trace record: subcommand tokens, never values. */
export function commandIdentity(argv: string[]): string {
  const flags = argv.filter((a) => a.startsWith("--"));
  const tokens = argv.filter((a) => !a.startsWith("-")).slice(0, 2);
  return [tokens.join(" "), ...flags].join(" ").trim();
}
