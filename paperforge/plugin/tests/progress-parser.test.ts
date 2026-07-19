/**
 * Vitest tests for progress-parser.ts — chunk boundary safety,
 * prefix matching for EMBED / OCR_REBUILD / OCR_REDO.
 */
import { describe, expect, it } from "vitest";
import {
  processProgressChunk,
  parseProgressLine,
} from "../src/services/progress-parser";

// ── processProgressChunk ──

describe("processProgressChunk", () => {
  it("parses OCR_REBUILD_START:total", () => {
    const { events, buffer } = processProgressChunk("OCR_REBUILD_START:5\n", "");
    expect(events).toHaveLength(1);
    expect(events[0]).toEqual({
      prefix: "OCR_REBUILD",
      event: "START",
      total: 5,
    });
    expect(buffer).toBe("");
  });

  it("parses OCR_REBUILD_PROGRESS:current:total:key", () => {
    const { events, buffer } = processProgressChunk(
      "OCR_REBUILD_PROGRESS:1:5:some-key\n",
      "",
    );
    expect(events).toHaveLength(1);
    expect(events[0]).toEqual({
      prefix: "OCR_REBUILD",
      event: "PROGRESS",
      current: 1,
      total: 5,
      key: "some-key",
    });
    expect(buffer).toBe("");
  });

  it("parses OCR_REBUILD_DONE exact match", () => {
    const { events } = processProgressChunk("OCR_REBUILD_DONE\n", "");
    expect(events).toHaveLength(1);
    expect(events[0]).toEqual({
      prefix: "OCR_REBUILD",
      event: "DONE",
    });
  });

  it("parses multiple OCR_REDO tokens from one chunk", () => {
    const chunk =
      "OCR_REDO_START:3\nOCR_REDO_PROGRESS:1:3:key-1\nOCR_REDO_DONE\n";
    const { events, buffer } = processProgressChunk(chunk, "");
    expect(events).toHaveLength(3);
    expect(events[0]).toEqual({
      prefix: "OCR_REDO",
      event: "START",
      total: 3,
    });
    expect(events[1]).toEqual({
      prefix: "OCR_REDO",
      event: "PROGRESS",
      current: 1,
      total: 3,
      key: "key-1",
    });
    expect(events[2]).toEqual({ prefix: "OCR_REDO", event: "DONE" });
    expect(buffer).toBe("");
  });

  it("parses EMBED tokens for backward compatibility", () => {
    const chunk =
      "EMBED_START:10\nEMBED_PROGRESS:2:10:paper-abc\nEMBED_DONE\n";
    const { events, buffer } = processProgressChunk(chunk, "");
    expect(events).toHaveLength(3);
    expect(events[0]).toEqual({ prefix: "EMBED", event: "START", total: 10 });
    expect(events[1]).toEqual({
      prefix: "EMBED",
      event: "PROGRESS",
      current: 2,
      total: 10,
      key: "paper-abc",
    });
    expect(events[2]).toEqual({ prefix: "EMBED", event: "DONE" });
    expect(buffer).toBe("");
  });

  it("buffers an incomplete last line", () => {
    const { events, buffer } = processProgressChunk(
      "OCR_REBUILD_PROGRESS:1:5:",
      "",
    );
    expect(events).toHaveLength(0);
    expect(buffer).toBe("OCR_REBUILD_PROGRESS:1:5:");
  });

  it("resumes from buffer on the next chunk", () => {
    const first = processProgressChunk("OCR_REBUILD_PROGRESS:1:", "");
    expect(first.events).toHaveLength(0);
    expect(first.buffer).toBe("OCR_REBUILD_PROGRESS:1:");

    const second = processProgressChunk("5:paper-key\n", first.buffer);
    expect(second.events).toHaveLength(1);
    expect(second.events[0]).toEqual({
      prefix: "OCR_REBUILD",
      event: "PROGRESS",
      current: 1,
      total: 5,
      key: "paper-key",
    });
    expect(second.buffer).toBe("");
  });

  it("passes through non-token lines silently and keeps buffer", () => {
    const { events, buffer } = processProgressChunk(
      "normal stdout line\nanother\n",
      "",
    );
    expect(events).toHaveLength(0);
    expect(buffer).toBe("");
  });

  it("handles interleaved normal output and tokens", () => {
    const chunk =
      "info: starting\nOCR_REBUILD_START:2\nsome log\nOCR_REBUILD_PROGRESS:1:2:k1\nmore output\nOCR_REBUILD_DONE\ndone\n";
    const { events, buffer } = processProgressChunk(chunk, "");
    expect(events).toHaveLength(3);
    expect(events[0]).toEqual({ prefix: "OCR_REBUILD", event: "START", total: 2 });
    expect(events[1]).toEqual({
      prefix: "OCR_REBUILD",
      event: "PROGRESS",
      current: 1,
      total: 2,
      key: "k1",
    });
    expect(events[2]).toEqual({ prefix: "OCR_REBUILD", event: "DONE" });
    expect(buffer).toBe("");
  });

  it("handles empty chunk gracefully", () => {
    const { events, buffer } = processProgressChunk("", "existing-buffer");
    expect(events).toHaveLength(0);
    expect(buffer).toBe("existing-buffer");
  });

  it("uses empty buffer on first call when omitted", () => {
    // With empty string buffer
    const { events, buffer } = processProgressChunk("EMBED_DONE\n", "");
    expect(events).toHaveLength(1);
    expect(buffer).toBe("");
  });

  it("parses EMBED_START split at prefix boundary", () => {
    // First chunk has partial prefix
    const first = processProgressChunk("EM", "");
    expect(first.events).toHaveLength(0);
    expect(first.buffer).toBe("EM");

    // Second chunk completes the token
    const second = processProgressChunk("BED_START:3\n", first.buffer);
    expect(second.events).toHaveLength(1);
    expect(second.events[0]).toEqual({
      prefix: "EMBED",
      event: "START",
      total: 3,
    });
    expect(second.buffer).toBe("");
  });

  it("parses OCR_REBUILD_START split across chunks", () => {
    const first = processProgressChunk("OCR_REB", "");
    expect(first.events).toHaveLength(0);
    expect(first.buffer).toBe("OCR_REB");

    const second = processProgressChunk("UILD_START:5\n", first.buffer);
    expect(second.events).toHaveLength(1);
    expect(second.events[0]).toEqual({
      prefix: "OCR_REBUILD",
      event: "START",
      total: 5,
    });
    expect(second.buffer).toBe("");
  });

  it("parses EMBED_PROGRESS split between prefix and colon", () => {
    const first = processProgressChunk("EMBED_PROGRESS", "");
    expect(first.events).toHaveLength(0);
    expect(first.buffer).toBe("EMBED_PROGRESS");

    const second = processProgressChunk(":2:5:my-key\n", first.buffer);
    expect(second.events).toHaveLength(1);
    expect(second.events[0]).toEqual({
      prefix: "EMBED",
      event: "PROGRESS",
      current: 2,
      total: 5,
      key: "my-key",
    });
    expect(second.buffer).toBe("");
  });

  it("parses EMBED_DONE across two chunks", () => {
    const first = processProgressChunk("EMBED_D", "");
    expect(first.events).toHaveLength(0);
    expect(first.buffer).toBe("EMBED_D");

    const second = processProgressChunk("ONE\n", first.buffer);
    expect(second.events).toHaveLength(1);
    expect(second.events[0]).toEqual({
      prefix: "EMBED",
      event: "DONE",
    });
    expect(second.buffer).toBe("");
  });
  it("parses EMBED tokens with interleaved normal output across chunks", () => {
    // First chunk: START is complete, PROGRESS line is split without trailing \n
    const first = processProgressChunk(
      "log line\nEMBED_START:2\nmore log\nEMBED_PROGRESS:1:2:",
      "",
    );
    expect(first.events).toHaveLength(1);
    expect(first.events[0]).toEqual({ prefix: "EMBED", event: "START", total: 2 });
    // Buffer holds only the last incomplete fragment
    expect(first.buffer).toBe("EMBED_PROGRESS:1:2:");

    // Second chunk completes the PROGRESS line and has complete DONE
    const second = processProgressChunk("k1\nEMBED_DONE\n", first.buffer);
    expect(second.events).toHaveLength(2);
    expect(second.events[0]).toEqual({
      prefix: "EMBED", event: "PROGRESS",
      current: 1, total: 2, key: "k1",
    });
    expect(second.events[1]).toEqual({ prefix: "EMBED", event: "DONE" });
    expect(second.buffer).toBe("");
  });

  it("parses all EMBED tokens across chunk boundaries", () => {
    const first = processProgressChunk("EMBED_START:2\nEMBED_PR", "");
    expect(first.events).toHaveLength(1);
    expect(first.events[0]).toEqual({ prefix: "EMBED", event: "START", total: 2 });
    expect(first.buffer).toBe("EMBED_PR");

    const second = processProgressChunk("OGRESS:1:2:k1\nEMBED_DONE\n", first.buffer);
    expect(second.events).toHaveLength(2);
    expect(second.events[0]).toEqual({
      prefix: "EMBED", event: "PROGRESS",
      current: 1, total: 2, key: "k1",
    });
    expect(second.events[1]).toEqual({ prefix: "EMBED", event: "DONE" });
    expect(second.buffer).toBe("");
  });
});

// ── parseProgressLine ──

describe("parseProgressLine", () => {
  it("returns START for OCR_REBUILD_START:5", () => {
    expect(parseProgressLine("OCR_REBUILD_START:5")).toEqual({
      prefix: "OCR_REBUILD",
      event: "START",
      total: 5,
    });
  });

  it("returns PROGRESS for full token", () => {
    expect(parseProgressLine("OCR_REDO_PROGRESS:3:10:paper-z")).toEqual({
      prefix: "OCR_REDO",
      event: "PROGRESS",
      current: 3,
      total: 10,
      key: "paper-z",
    });
  });

  it("returns DONE for exact match", () => {
    expect(parseProgressLine("EMBED_DONE")).toEqual({
      prefix: "EMBED",
      event: "DONE",
    });
  });

  it("returns null for non-token line", () => {
    expect(parseProgressLine("hello world")).toBeNull();
  });

  it("returns null for empty string", () => {
    expect(parseProgressLine("")).toBeNull();
  });
});
