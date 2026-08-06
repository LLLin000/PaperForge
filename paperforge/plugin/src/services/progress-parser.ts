/**
 * Shared progress token parser — handles EMBED, OCR_REBUILD, OCR_REDO, OCR_RUN
 * tokens across arbitrary stdout chunks.
 *
 * Token formats:
 *   {PREFIX}_START:{total}
 *   {PREFIX}_PROGRESS:{current}:{total}:{key}
 *   {PREFIX}_DONE
 *
 * PREFIX in: EMBED, OCR_REBUILD, OCR_REDO, OCR_RUN
 *
 * This is the stable plugin boundary contract from the CLI backend.
 */

export type ProgressEventType =
  | "START"
  | "PROGRESS"
  | "RESULT"
  | "DONE"
  | "PHASE"
  | "NOTICE";

export interface ProgressEvent {
  prefix: string;
  event: ProgressEventType;
  total?: number;
  current?: number;
  key?: string;
  /** #126: OCR_REBUILD_RESULT:<key>:ok|failed|skipped */
  resultStatus?: string;
  /** #126: OCR_REBUILD_DONE:<success>:<failed>:<skipped> */
  success?: number;
  failed?: number;
  skipped?: number;
  phase?: string;
  notice?: string;
}

const KNOWN_PREFIXES = ["EMBED", "OCR_REBUILD", "OCR_REDO", "OCR_RUN"];

/**
 * Parse an arbitrarily chunked stdout stream for progress tokens.
 *
 * @param chunk  Raw text from the latest stdout data event.
 * @param buffer Accumulated incomplete line from a previous call (empty string initially).
 * @returns Parsed events and any leftover line fragment to pass to the next call.
 */
export function processProgressChunk(
  chunk: string,
  buffer: string
): { events: ProgressEvent[]; buffer: string } {
  const full = buffer + chunk;
  const lines = full.split("\n");
  // The last element may be an incomplete line — hold for next chunk.
  const incomplete = lines.pop() ?? "";

  const events: ProgressEvent[] = [];

  for (const line of lines) {
    for (const prefix of KNOWN_PREFIXES) {
      const pLen = prefix.length;

      if (line.startsWith(prefix + "_START:")) {
        const total =
          parseInt(line.slice(pLen + 7) /* "_START:".length */, 10) || 0;
        events.push({ prefix, event: "START", total });
        break;
      }

      if (line.startsWith(prefix + "_PROGRESS:")) {
        const rest = line.slice(pLen + 10); /* "_PROGRESS:".length */
        const parts = rest.split(":");
        events.push({
          prefix,
          event: "PROGRESS",
          current: parseInt(parts[0], 10) || 0,
          total: parseInt(parts[1], 10) || 0,
          key: parts[2] ?? "",
        });
        break;
      }

      if (line.startsWith(prefix + "_RESULT:")) {
        // #126: {PREFIX}_RESULT:<key>:ok|failed|skipped — key never contains
        // the protocol separator; status is the final field.
        const rest = line.slice(pLen + 8); /* "_RESULT:".length */
        const parts = rest.split(":");
        events.push({
          prefix,
          event: "RESULT",
          key: parts[0] ?? "",
          resultStatus: parts[1] ?? "",
        });
        break;
      }

      if (line === prefix + "_DONE" || line.startsWith(prefix + "_DONE:")) {
        const rest = line.slice(pLen + 6); /* "_DONE:".length */
        const parts = rest.split(":");
        events.push({
          prefix,
          event: "DONE",
          success: parseInt(parts[0], 10) || 0,
          failed: parseInt(parts[1], 10) || 0,
          skipped: parseInt(parts[2], 10) || 0,
        });
        break;
      }

      // #120 forward-compat: EMBED_PHASE:<phase> and EMBED_NOTICE:<text>.
      // The backend does not emit these yet — parsing is additive.
      if (line.startsWith(prefix + "_PHASE:")) {
        events.push({
          prefix,
          event: "PHASE",
          phase: line.slice(pLen + 7) /* "_PHASE:".length */,
        });
        break;
      }

      if (line.startsWith(prefix + "_NOTICE:")) {
        events.push({
          prefix,
          event: "NOTICE",
          notice: line.slice(pLen + 8) /* "_NOTICE:".length */,
        });
        break;
      }
    }
  }

  return { events, buffer: incomplete };
}

/**
 * Parse a single complete line for a progress token.
 * Useful when text is already newline-aligned (e.g. execFile stdout).
 */
export function parseProgressLine(line: string): ProgressEvent | null {
  for (const prefix of KNOWN_PREFIXES) {
    const pLen = prefix.length;

    if (line.startsWith(prefix + "_START:")) {
      const total = parseInt(line.slice(pLen + 7), 10) || 0;
      return { prefix, event: "START", total };
    }

    if (line.startsWith(prefix + "_PROGRESS:")) {
      const rest = line.slice(pLen + 10);
      const parts = rest.split(":");
      return {
        prefix,
        event: "PROGRESS",
        current: parseInt(parts[0], 10) || 0,
        total: parseInt(parts[1], 10) || 0,
        key: parts[2] ?? "",
      };
    }

    if (line.startsWith(prefix + "_RESULT:")) {
      const parts = line.slice(pLen + 8).split(":");
      return {
        prefix,
        event: "RESULT",
        key: parts[0] ?? "",
        resultStatus: parts[1] ?? "",
      };
    }

    if (line === prefix + "_DONE" || line.startsWith(prefix + "_DONE:")) {
      const parts = line.slice(pLen + 6).split(":");
      return {
        prefix,
        event: "DONE",
        success: parseInt(parts[0], 10) || 0,
        failed: parseInt(parts[1], 10) || 0,
        skipped: parseInt(parts[2], 10) || 0,
      };
    }

    if (line.startsWith(prefix + "_PHASE:")) {
      return { prefix, event: "PHASE", phase: line.slice(pLen + 7) };
    }

    if (line.startsWith(prefix + "_NOTICE:")) {
      return { prefix, event: "NOTICE", notice: line.slice(pLen + 8) };
    }
  }

  return null;
}
