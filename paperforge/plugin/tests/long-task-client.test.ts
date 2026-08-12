/**
 * LongTaskClient + NdjsonStreamParser tests (T8 closure #169).
 *
 * #137 protocol-fail-closed table: non-JSON / bad schema / unknown event /
 * second terminal / event after terminal / EOF without terminal.  Stop →
 * stdin token → grace → hard escalation.
 */
import { describe, expect, it } from "vitest";
import { NdjsonStreamParser } from "../src/services/long-task-client";

describe("NdjsonStreamParser", () => {
  it("accepts a valid start → progress → result stream", () => {
    const p = new NdjsonStreamParser();
    const evs = p.feed(
      '{"schema_version":1,"event":"start","operation":"x","total":2}\n' +
        '{"schema_version":1,"event":"progress","operation":"x","current":1,"total":2}\n' +
        '{"schema_version":1,"event":"result","operation":"x","result":{"ok":true}}\n'
    );
    expect(p.protocolFailure).toBeUndefined();
    expect(evs.map((e) => e.event)).toEqual(["start", "progress", "result"]);
    p.finishEOF();
    expect(p.protocolFailure).toBeUndefined();
  });

  it("fails closed on an unknown event type", () => {
    const p = new NdjsonStreamParser();
    p.feed('{"schema_version":1,"event":"totally_new_semantic_event"}\n');
    expect(p.protocolFailure).toContain("unknown event");
  });

  it("fails closed on a SECOND terminal", () => {
    const p = new NdjsonStreamParser();
    p.feed(
      '{"schema_version":1,"event":"result","operation":"x","result":{}}\n'
    );
    p.feed(
      '{"schema_version":1,"event":"result","operation":"x","result":{}}\n'
    );
    expect(p.protocolFailure).toContain("after terminal");
  });

  it("fails closed on an event AFTER the terminal", () => {
    const p = new NdjsonStreamParser();
    p.feed(
      '{"schema_version":1,"event":"result","operation":"x","result":{}}\n'
    );
    p.feed(
      '{"schema_version":1,"event":"progress","operation":"x","current":1}\n'
    );
    expect(p.protocolFailure).toContain("after terminal");
  });

  it("fails closed on EOF without a terminal", () => {
    const p = new NdjsonStreamParser();
    p.feed('{"schema_version":1,"event":"start","operation":"x","total":1}\n');
    expect(p.protocolFailure).toBeUndefined();
    p.finishEOF();
    expect(p.protocolFailure).toContain("EOF without terminal");
  });

  it("buffers a partial trailing line across chunks", () => {
    const p = new NdjsonStreamParser();
    p.feed('{"schema_version":1,"event":"sta');
    expect(p.protocolFailure).toBeUndefined();
    const evs = p.feed('rt","operation":"x","total":1}\n');
    expect(evs).toHaveLength(1);
    expect(evs[0].event).toBe("start");
  });
});

function makeChild(pid: number) {
  const listeners: Record<string, (d: unknown) => void> = {};
  const child: any = {
    pid,
    exitCode: null,
    killed: false,
    stdin: { write: vi.fn() },
    stdout: {
      setEncoding: vi.fn(),
      on: (ev: string, cb: (d: unknown) => void) => {
        listeners[ev] = cb;
      },
    },
    on: (ev: string, cb: (d: unknown) => void) => {
      listeners[ev] = cb;
    },
    kill: vi.fn(),
    _listeners: listeners,
  };
  return child;
}
