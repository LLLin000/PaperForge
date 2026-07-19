/**
 * Shared progress token parser — handles EMBED, OCR_REBUILD, and OCR_REDO
 * tokens across arbitrary stdout chunks.
 *
 * Token formats:
 *   {PREFIX}_START:{total}
 *   {PREFIX}_PROGRESS:{current}:{total}:{key}
 *   {PREFIX}_DONE
 *
 * PREFIX in: EMBED, OCR_REBUILD, OCR_REDO
 *
 * This is the stable plugin boundary contract from the CLI backend.
 */

export type ProgressEventType = "START" | "PROGRESS" | "DONE";

export interface ProgressEvent {
  prefix: string;
  event: ProgressEventType;
  total?: number;
  current?: number;
  key?: string;
}

const KNOWN_PREFIXES = ["EMBED", "OCR_REBUILD", "OCR_REDO"];

/**
 * Parse an arbitrarily chunked stdout stream for progress tokens.
 *
 * @param chunk  Raw text from the latest stdout data event.
 * @param buffer Accumulated incomplete line from a previous call (empty string initially).
 * @returns Parsed events and any leftover line fragment to pass to the next call.
 */
export function processProgressChunk(
  chunk: string,
  buffer: string,
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
        const total = parseInt(line.slice(pLen + 7) /* "_START:".length */, 10) || 0;
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

      if (line === prefix + "_DONE" || line.startsWith(prefix + "_DONE:")) {
        events.push({ prefix, event: "DONE" });
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

    if (line === prefix + "_DONE" || line.startsWith(prefix + "_DONE:")) {
      return { prefix, event: "DONE" };
    }
  }

  return null;
}
