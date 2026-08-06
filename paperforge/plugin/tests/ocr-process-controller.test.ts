/**
 * Vitest tests for ocr-process-controller.ts — singleton lifecycle,
 * credential policy, token aggregation, stop, and duplicate guards
 * (#126 PR B).
 */
import { describe, expect, it, vi } from "vitest";
import { EventEmitter } from "events";
import {
  OcrProcessController,
  type OcrProcessCallbacks,
  type OcrProcessControllerOptions,
} from "../src/services/ocr-process-controller";

/** Fake child: EventEmitter with pipe-like stdout/stderr/stdin. */
function fakeChild() {
  const child = new EventEmitter() as any;
  child.stdout = new EventEmitter();
  child.stderr = new EventEmitter();
  (child.stdout as any).setEncoding = () => {};
  (child.stderr as any).setEncoding = () => {};
  let stdinWritten = "";
  child.stdin = {
    write: (data: string) => {
      stdinWritten += data;
      return true;
    },
  };
  child.emitStdout = (chunk: string) => child.stdout.emit("data", chunk);
  child.emitStderr = (chunk: string) => child.stderr.emit("data", chunk);
  child.emitClose = (code: number | null) => child.emit("close", code);
  child.emitError = (err: Error) => child.emit("error", err);
  child.stdinWritten = () => stdinWritten;
  return child;
}

function makeController(overrides: Partial<OcrProcessControllerOptions> = {}): {
  ctrl: OcrProcessController;
  child: ReturnType<typeof fakeChild>;
  spawnedArgs: string[][];
} {
  const child = fakeChild();
  const spawnedArgs: string[][] = [];
  const ctrl = new OcrProcessController({
    vaultPath: "C:/vault",
    resolveCommand: () => ({ path: "python.exe", args: [] }),
    resolveEnv: async () => ({ PADDLEOCR_TOKEN: "tok" }),
    needsCredential: (mode) => mode === "run" || mode === "redo",
    spawnFn: ((_path: string, args: string[]) => {
      spawnedArgs.push(args);
      return child;
    }) as any,
    ...overrides,
  });
  return { ctrl, child, spawnedArgs };
}

function callbacks() {
  const progress: string[] = [];
  const results: string[] = [];
  const notices: string[] = [];
  const cb: OcrProcessCallbacks = {
    onProgress: (current, total, key) =>
      progress.push(`${current}/${total}:${key}`),
    onResult: (key, status) => results.push(`${key}:${status}`),
    onNotice: (m) => notices.push(m),
  };
  return { cb, progress, results, notices };
}

describe("OcrProcessController", () => {
  it("rebuild maps keys to argv without credential env", async () => {
    const { ctrl, child, spawnedArgs } = makeController();
    const { cb, results } = callbacks();
    const promise = ctrl.start("rebuild", { keys: ["A", "B"], callbacks: cb });
    expect(spawnedArgs[0]).toContain("ocr");
    expect(spawnedArgs[0]).toContain("rebuild");
    expect(spawnedArgs[0]).toContain("A");
    child.emitStdout("OCR_REBUILD_START:2\n");
    child.emitStdout("OCR_REBUILD_RESULT:A:ok\n");
    child.emitStdout("OCR_REBUILD_RESULT:B:ok\n");
    child.emitStdout("OCR_REBUILD_DONE:2:0:0\n");
    child.emitClose(0);
    const outcome = await promise;
    expect(outcome.ok).toBe(true);
    expect(outcome.successKeys).toEqual(["A", "B"]);
    expect(outcome.failedKeys).toEqual([]);
    expect(results).toEqual(["A:ok", "B:ok"]);
  });

  it("rebuild --all when no keys given", async () => {
    const { ctrl, spawnedArgs } = makeController();
    const promise = ctrl.start("rebuild", { all: true });
    expect(spawnedArgs[0]).toContain("--all");
    const child = (ctrl as any)._child;
    child?.emitClose(0);
    await promise;
  });

  it("aggregates mixed outcomes and reports non-ok", async () => {
    const { ctrl, child } = makeController();
    const promise = ctrl.start("rebuild", { keys: ["A", "B", "C"] });
    child.emitStdout("OCR_REBUILD_RESULT:A:ok\n");
    child.emitStdout("OCR_REBUILD_RESULT:B:failed\n");
    child.emitStdout("OCR_REBUILD_RESULT:C:skipped\n");
    child.emitClose(1);
    const outcome = await promise;
    expect(outcome.ok).toBe(false);
    expect(outcome.successKeys).toEqual(["A"]);
    expect(outcome.failedKeys).toEqual(["B"]);
    expect(outcome.skippedKeys).toEqual([{ key: "C", reason: "backend_skip" }]);
    expect(outcome.exitCode).toBe(1);
  });

  it("rejects duplicate start while running (singleton guard)", async () => {
    const { ctrl, child } = makeController();
    const first = ctrl.start("rebuild", { keys: ["A"] });
    await expect(ctrl.start("rebuild", { keys: ["B"] })).rejects.toThrow(
      "already running"
    );
    child.emitClose(0);
    await first;
  });

  it("stop writes PAPERFORGE_STOP and marks outcome stopped", async () => {
    const { ctrl, child } = makeController();
    const promise = ctrl.start("rebuild", { keys: ["A", "B"] });
    child.emitStdout("OCR_REBUILD_RESULT:A:ok\n");
    ctrl.stop();
    expect(child.stdinWritten()).toContain("PAPERFORGE_STOP");
    // idempotent
    ctrl.stop();
    child.emitClose(130);
    const outcome = await promise;
    expect(outcome.stopped).toBe(true);
    expect(outcome.ok).toBe(false);
    expect(outcome.exitCode).toBe(130);
  });

  it("run/redo require credential and fail closed when env resolution fails", async () => {
    const { ctrl } = makeController({
      resolveEnv: async () => {
        throw new Error("no token");
      },
    });
    await expect(ctrl.start("run")).rejects.toThrow("credential unavailable");
    await expect(ctrl.start("redo")).rejects.toThrow("credential unavailable");
  });

  it("rebuild never requires the credential", async () => {
    const resolveEnv = vi.fn(async () => ({}));
    const { ctrl, child } = makeController({ resolveEnv });
    const promise = ctrl.start("rebuild", { keys: ["A"] });
    expect(resolveEnv).not.toHaveBeenCalled();
    child.emitClose(0);
    await promise;
  });

  it("rejects when runtime is unavailable", async () => {
    const { ctrl } = makeController({
      resolveCommand: () => null,
    });
    await expect(ctrl.start("rebuild")).rejects.toThrow("runtime");
  });

  it("settles exactly once across close and error", async () => {
    const { ctrl, child } = makeController();
    let settled = 0;
    const promise = ctrl.start("rebuild", { keys: ["A"] });
    promise.then(() => (settled += 1));
    child.emitError(new Error("boom"));
    child.emitClose(1);
    await promise;
    expect(settled).toBe(1);
  });

  it("forwards stderr tail as a notice on settle", async () => {
    const { ctrl, child } = makeController();
    const { cb, notices } = callbacks();
    const promise = ctrl.start("rebuild", { keys: ["A"], callbacks: cb });
    child.emitStderr("some diagnostic line\n");
    child.emitClose(1);
    await promise;
    expect(notices.some((m) => m.includes("diagnostic"))).toBe(true);
  });
});
