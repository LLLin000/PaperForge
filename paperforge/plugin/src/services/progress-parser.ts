/**
 * #137 structured-stream parser — NDJSON events from long-task commands.
 *
 * stdout is machine output only: one JSON object per line, `schema_version: 1`,
 * `event` discriminator required, EXACTLY ONE terminal (result | error |
 * cancelled) then EOF.  The colon-token family (EMBED_*, OCR_REBUILD_*,
 * OCR_REDO_*) and tolerant "ignore unknown lines" parsing are RETIRED — no
 * token + NDJSON dual parsing.
 *
 * Protocol failures (per #137 §5) are surfaced, never guessed:
 * non-JSON line, bad schema_version, EOF without terminal, second terminal,
 * events after the terminal, unknown event type.
 */

export type NdjsonEventType =
  | "start"
  | "phase"
  | "progress"
  | "item_result"
  | "result"
  | "error"
  | "cancelled";

export interface NdjsonEvent {
  schema_version: number;
  event: NdjsonEventType;
  operation: string;
  total?: number;
  scope?: unknown;
  phase?: string;
  current?: number;
  item_id?: string;
  status?: string;
  result?: Record<string, unknown> | null;
  [key: string]: unknown;
}

export interface ParseChunkResult {
  events: NdjsonEvent[];
  buffer: string;
  protocolFailure?: string;
}

const TERMINAL_EVENTS: ReadonlySet<string> = new Set([
  "result",
  "error",
  "cancelled",
]);

/**
 * Parse an arbitrarily chunked NDJSON stream.
 *
 * @param chunk  Raw text from the latest stdout data event.
 * @param buffer Accumulated incomplete line from a previous call.
 * @returns Parsed events, leftover fragment, and any protocol failure.
 *          A protocol failure is sticky: once reported, the caller should
 *          stop feeding chunks (the stream is unparseable by contract).
 */
export function processProgressChunk(
  chunk: string,
  buffer: string
): ParseChunkResult {
  const full = buffer + chunk;
  const lines = full.split("\n");
  const incomplete = lines.pop() ?? "";

  const events: NdjsonEvent[] = [];
  let protocolFailure: string | undefined;

  for (const line of lines) {
    if (!line.trim()) continue;
    if (protocolFailure) break;
    try {
      const parsed = JSON.parse(line) as NdjsonEvent;
      if (parsed.schema_version !== 1) {
        protocolFailure = `schema_version ${parsed.schema_version} != 1`;
        break;
      }
      if (typeof parsed.event !== "string" || !parsed.event) {
        protocolFailure = "event discriminator required";
        break;
      }
      if (TERMINAL_EVENTS.has(parsed.event) && !("result" in parsed)) {
        protocolFailure = `terminal ${parsed.event} missing result payload`;
        break;
      }
      events.push(parsed);
    } catch {
      protocolFailure = `non-JSON stdout line: ${line.slice(0, 80)}`;
      break;
    }
  }

  return { events, buffer: incomplete, protocolFailure };
}

/**
 * Parse a single complete NDJSON line (newline-aligned stdout, e.g.
 * execFile output).  Returns the event or null for blank lines; throws a
 * descriptive error on protocol violations.
 */
export function parseProgressLine(line: string): NdjsonEvent | null {
  if (!line.trim()) return null;
  const parsed = JSON.parse(line) as NdjsonEvent;
  if (parsed.schema_version !== 1) {
    throw new Error(
      `protocol failure: schema_version ${parsed.schema_version} != 1`
    );
  }
  if (typeof parsed.event !== "string" || !parsed.event) {
    throw new Error("protocol failure: event discriminator required");
  }
  return parsed;
}

/** True when the event terminates the stream. */
export function isTerminalEvent(event: NdjsonEventType): boolean {
  return TERMINAL_EVENTS.has(event);
}

/** Project a start/progress event onto the old ProgressEvent-ish shape used
 * by UI renderers (additive adapter; the wire stays NDJSON). */
export function toLegacyProgressShape(event: NdjsonEvent): {
  prefix: string;
  event: string;
  total?: number;
  current?: number;
  key?: string;
  resultStatus?: string;
} | null {
  if (event.event === "start") {
    return { prefix: event.operation, event: "START", total: event.total };
  }
  if (event.event === "progress") {
    return {
      prefix: event.operation,
      event: "PROGRESS",
      current: event.current,
      total: event.total,
      key: event.item_id,
    };
  }
  if (event.event === "item_result") {
    return {
      prefix: event.operation,
      event: "RESULT",
      key: event.item_id,
      resultStatus: event.status,
    };
  }
  return null;
}
