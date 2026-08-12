/**
 * #137 NDJSON structured-stream parser tests (T8 #169).
 *
 * The colon-token family is RETIRED — no token + NDJSON dual parsing.
 */
import { describe, expect, it } from "vitest";
import {
  processProgressChunk,
  parseProgressLine,
  isTerminalEvent,
} from "../src/services/progress-parser";

describe("processProgressChunk", () => {
  it("parses a start event", () => {
    const { events, buffer, protocolFailure } = processProgressChunk(
      '{"schema_version":1,"event":"start","operation":"ocr.rebuild","total":3}\n',
      ""
    );
    expect(protocolFailure).toBeUndefined();
    expect(buffer).toBe("");
    expect(events).toHaveLength(1);
    expect(events[0].event).toBe("start");
    expect(events[0].operation).toBe("ocr.rebuild");
    expect(events[0].total).toBe(3);
  });

  it("parses progress and item_result events", () => {
    const stream = [
      '{"schema_version":1,"event":"start","operation":"ocr.rebuild","total":2}\n',
      '{"schema_version":1,"event":"progress","operation":"ocr.rebuild","current":1,"total":2,"item_id":"KEY001"}\n',
      '{"schema_version":1,"event":"item_result","operation":"ocr.rebuild","item_id":"KEY001","status":"ok"}\n',
    ].join("");
    const { events, protocolFailure } = processProgressChunk(stream, "");
    expect(protocolFailure).toBeUndefined();
    const kinds = events.map((e) => e.event);
    expect(kinds).toEqual(["start", "progress", "item_result"]);
    const progress = events[1];
    expect(progress.item_id).toBe("KEY001");
    expect(progress.current).toBe(1);
  });

  it("buffers an incomplete trailing line across chunks", () => {
    const first = processProgressChunk('{"schema_version":1,"event":"sta', "");
    expect(first.events).toHaveLength(0);
    expect(first.buffer).toContain('"event":"sta');
    const second = processProgressChunk(
      'rt","operation":"ocr.redo","total":1}\n',
      first.buffer
    );
    expect(second.events).toHaveLength(1);
    expect(second.events[0].event).toBe("start");
  });

  it("exactly-one terminal: result is last", () => {
    const stream = [
      '{"schema_version":1,"event":"start","operation":"embed.build","total":1}\n',
      '{"schema_version":1,"event":"result","operation":"embed.build","result":{"ok":true}}\n',
    ].join("");
    const { events, protocolFailure } = processProgressChunk(stream, "");
    expect(protocolFailure).toBeUndefined();
    expect(events).toHaveLength(2);
    expect(events[1].event).toBe("result");
    expect(isTerminalEvent(events[1].event as never)).toBe(true);
  });

  it("reports a protocol failure on non-JSON lines (fail closed)", () => {
    const { events, protocolFailure } = processProgressChunk(
      "OCR_REDO_START:3\n",
      ""
    );
    expect(events).toHaveLength(0);
    expect(protocolFailure).toContain("non-JSON");
  });

  it("reports a protocol failure on bad schema_version", () => {
    const { protocolFailure } = processProgressChunk(
      '{"schema_version":2,"event":"start","operation":"x"}\n',
      ""
    );
    expect(protocolFailure).toContain("schema_version");
  });

  it("reports a protocol failure on a missing event discriminator", () => {
    const { protocolFailure } = processProgressChunk(
      '{"schema_version":1,"total":3}\n',
      ""
    );
    expect(protocolFailure).toContain("event");
  });

  it("ignores blank lines", () => {
    const { events, protocolFailure } = processProgressChunk("\n\n", "");
    expect(events).toHaveLength(0);
    expect(protocolFailure).toBeUndefined();
  });
});

describe("parseProgressLine", () => {
  it("parses a single NDJSON line", () => {
    const ev = parseProgressLine(
      '{"schema_version":1,"event":"progress","operation":"ocr.rebuild","current":1,"total":2,"item_id":"K"}'
    );
    expect(ev).not.toBeNull();
    expect(ev?.event).toBe("progress");
  });

  it("throws on protocol violations", () => {
    expect(() => parseProgressLine("not json")).toThrow();
    expect(() =>
      parseProgressLine('{"schema_version":9,"event":"start"}')
    ).toThrow(/schema_version/);
  });
});

describe("terminal semantics", () => {
  it("recognizes result/error/cancelled as terminals", () => {
    expect(isTerminalEvent("result" as never)).toBe(true);
    expect(isTerminalEvent("error" as never)).toBe(true);
    expect(isTerminalEvent("cancelled" as never)).toBe(true);
    expect(isTerminalEvent("start" as never)).toBe(false);
    expect(isTerminalEvent("progress" as never)).toBe(false);
  });
});
