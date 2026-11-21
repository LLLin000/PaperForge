/**
 * Tests for warm stdio daemon multiplexing in NodeProcessTransport and
 * per-paper scoped cache invalidation in PaperForgeClient.
 */

import { EventEmitter } from "events";
import * as os from "os";
import { describe, expect, it, vi } from "vitest";

const runtimeState = vi.hoisted(() => ({ pythonPath: "C:/py/python.exe" }));
vi.mock("../../src/services/managed-runtime", () => ({
  readRuntimePointer: () =>
    runtimeState.pythonPath
      ? {
          pythonPath: runtimeState.pythonPath,
          environmentRoot: "C:/managed",
          paperforgeVersion: "1.0.0",
        }
      : null,
  resolveRuntimeCommand: (pointer: { pythonPath: string } | null) =>
    pointer ? { command: pointer.pythonPath, args: [] } : null,
}));

import { NodeProcessTransport } from "../../src/client/node-transport";
import { PaperForgeClient } from "../../src/client/paperforge-client";
import type { Transport } from "../../src/client/transport";

class MockStream extends EventEmitter {
  public setEncoding = vi.fn();
}

class MockChildProcess extends EventEmitter {
  public stdout = new MockStream();
  public stderr = new MockStream();
  public exitCode: number | null = null;
  public signalCode: NodeJS.Signals | null = null;
  public kill = vi.fn(() => {
    this.exitCode = 0;
    return true;
  });
  public writes: string[] = [];
  public stdin = {
    write: vi.fn((chunk: string) => {
      this.writes.push(chunk);
      return true;
    }),
    end: vi.fn(),
  };
}

describe("NodeProcessTransport warm daemon & scoped invalidation", () => {
  const vaultPath = "C:/mock/vault";

  it("reuses a single warm daemon across sequential execute calls with tmpdir cwd", async () => {
    const daemonChild = new MockChildProcess();
    daemonChild.stdin.write = vi.fn((chunk: string) => {
      daemonChild.writes.push(chunk);
      const req = JSON.parse(chunk.trim()) as { id: number; argv: string[] };
      queueMicrotask(() => {
        daemonChild.stdout.emit(
          "data",
          JSON.stringify({
            id: req.id,
            exit_code: 0,
            stdout: JSON.stringify({ call: req.id, argv: req.argv }),
            stderr: "",
          }) + "\n"
        );
      });
      return true;
    });

    const mockSpawn = vi.fn().mockReturnValue(daemonChild);
    const transport = new NodeProcessTransport({
      vaultPath,
      spawnFn: mockSpawn as unknown as typeof import("child_process").spawn,
      useDaemon: true,
    });

    const r1 = JSON.parse(
      await transport.execute(["config", "paths", "--json"])
    );
    const r2 = JSON.parse(await transport.execute(["probe", "ocr", "--json"]));

    expect(mockSpawn).toHaveBeenCalledTimes(1);
    expect(mockSpawn).toHaveBeenCalledWith(
      "C:/py/python.exe",
      ["-m", "paperforge", "daemon", "--stdio", "--idle-timeout", "300"],
      expect.objectContaining({
        cwd: os.tmpdir(),
        shell: false,
        windowsHide: true,
      })
    );
    expect(r1.call).toBe(1);
    expect(r2.call).toBe(2);

    NodeProcessTransport.reapExecuteChildren();
    expect(daemonChild.kill).toHaveBeenCalledTimes(1);
    expect(transport.executeChildren.size).toBe(0);
  });

  it("falls back to one-shot spawn when daemon exits before settling any RPC", async () => {
    const brokenDaemon = new MockChildProcess();
    brokenDaemon.stdin.write = vi.fn((chunk: string) => {
      brokenDaemon.writes.push(chunk);
      queueMicrotask(() => {
        brokenDaemon.exitCode = 2;
        brokenDaemon.emit("close", 2);
      });
      return true;
    });

    const fallbackChild = new MockChildProcess();
    fallbackChild.stdin.end = vi.fn(() => {
      queueMicrotask(() => {
        fallbackChild.stdout.emit("data", '{"fallback":true}');
        fallbackChild.exitCode = 0;
        fallbackChild.emit("close", 0);
      });
    });

    const mockSpawn = vi
      .fn()
      .mockReturnValueOnce(brokenDaemon)
      .mockReturnValueOnce(fallbackChild);

    const transport = new NodeProcessTransport({
      vaultPath,
      spawnFn: mockSpawn as unknown as typeof import("child_process").spawn,
      useDaemon: true,
    });

    const out = await transport.execute(["probe", "ocr", "--json"]);
    expect(out).toBe('{"fallback":true}');
    expect(mockSpawn).toHaveBeenCalledTimes(2);
    expect(mockSpawn.mock.calls[0][1]).toContain("daemon");
    expect(mockSpawn.mock.calls[1][1]).toEqual([
      "-m",
      "paperforge",
      "--vault",
      vaultPath,
      "probe",
      "ocr",
      "--json",
    ]);
    transport.shutdownDaemon();
  });

  it("invalidatePaperScope evicts target paper cache while keeping probes and sibling papers warm", async () => {
    const executed: string[][] = [];
    let statusCallsForK1 = 0;
    const transport: Transport = {
      execute: vi.fn(async (argv: string[]) => {
        executed.push(argv);
        if (argv[0] === "probe" && argv[1] === "library") {
          return JSON.stringify({
            ok: true,
            command: "probe",
            version: "1.0.0",
            data: {
              schema_version: 2,
              module: "library",
              capability_state: "ready",
              activity_state: "idle",
              user_state: "ready",
              severity: "ok",
            },
          });
        }
        if (argv[0] === "paper-status") {
          const key = argv[1];
          if (key === "K1") statusCallsForK1 += 1;
          return JSON.stringify({ key, seq: statusCallsForK1 });
        }
        if (argv[0] === "annotations" && argv[1] === "delete") {
          return JSON.stringify({
            ok: true,
            command: "annotations",
            version: "1.0.0",
            data: { deleted: true, paper_id: "K1" },
          });
        }
        throw new Error(`Unexpected argv: ${argv.join(" ")}`);
      }),
      stream: vi.fn() as unknown as Transport["stream"],
    };

    const client = new PaperForgeClient({ transport });
    await client.probe("library");
    const firstK1 = await client.paperStatus("K1");
    await client.paperStatus("K2");
    expect(firstK1).toEqual({ key: "K1", seq: 1 });
    expect(executed).toHaveLength(3);

    await client.deleteAnnotation("K1", "ann-1");
    expect(executed).toHaveLength(4);

    // Probe and K2 remain cached; only K1 re-queries backend.
    await client.probe("library");
    await client.paperStatus("K2");
    const secondK1 = await client.paperStatus("K1");
    expect(secondK1).toEqual({ key: "K1", seq: 2 });
    expect(executed).toHaveLength(5);
    expect(executed[4]).toEqual(["paper-status", "K1", "--json"]);
  });

  it("multiplexes concurrent execute calls out-of-order and rejects siblings cleanly on shutdownDaemon respawn", async () => {
    const firstChild = new MockChildProcess();
    const queuedChunks: Array<{ id: number; argv: string[] }> = [];
    firstChild.stdin.write = vi.fn((chunk: string) => {
      firstChild.writes.push(chunk);
      const req = JSON.parse(chunk.trim()) as { id: number; argv: string[] };
      queuedChunks.push(req);
      if (queuedChunks.length === 2) {
        // Emit response for id=2 BEFORE id=1 to prove id-correlation works out of order
        queueMicrotask(() => {
          firstChild.stdout.emit(
            "data",
            JSON.stringify({
              id: queuedChunks[1].id,
              exit_code: 0,
              stdout: "second",
              stderr: "",
            }) +
              "\n" +
              JSON.stringify({
                id: queuedChunks[0].id,
                exit_code: 0,
                stdout: "first",
                stderr: "",
              }) +
              "\n"
          );
        });
      }
      return true;
    });

    const respawnChild = new MockChildProcess();
    respawnChild.stdin.write = vi.fn((chunk: string) => {
      respawnChild.writes.push(chunk);
      const req = JSON.parse(chunk.trim()) as { id: number };
      queueMicrotask(() => {
        respawnChild.stdout.emit(
          "data",
          JSON.stringify({
            id: req.id,
            exit_code: 0,
            stdout: "fresh-daemon",
            stderr: "",
          }) + "\n"
        );
      });
      return true;
    });

    const mockSpawn = vi
      .fn()
      .mockReturnValueOnce(firstChild)
      .mockReturnValueOnce(respawnChild);

    const transport = new NodeProcessTransport({
      vaultPath,
      spawnFn: mockSpawn as unknown as typeof import("child_process").spawn,
      useDaemon: true,
    });

    const [a, b] = await Promise.all([
      transport.execute(["config", "paths", "--json"]),
      transport.execute(["probe", "ocr", "--json"]),
    ]);
    expect(a).toBe("first");
    expect(b).toBe("second");
    expect(mockSpawn).toHaveBeenCalledTimes(1);

    // Trigger an in-flight RPC that stalls, then shut down daemon -> sibling rejects immediately (never hangs)
    const hungPromise = transport.execute(["probe", "library", "--json"]);
    await vi.waitFor(() => expect(firstChild.writes).toHaveLength(3));
    transport.shutdownDaemon();
    await expect(hungPromise).rejects.toThrow(/shut down/i);

    // Subsequent call automatically respawns a fresh warm daemon
    const afterRespawn = await transport.execute(["config", "paths", "--json"]);
    expect(afterRespawn).toBe("fresh-daemon");
    expect(mockSpawn).toHaveBeenCalledTimes(2);
    transport.shutdownDaemon();
  });

  it("dispatches duplex ControlDaemon push events while resolving interleaved RPCs", async () => {
    const daemonChild = new MockChildProcess();
    daemonChild.stdin.write = vi.fn((chunk: string) => {
      daemonChild.writes.push(chunk);
      const req = JSON.parse(chunk.trim()) as { id: number; op?: string };
      queueMicrotask(() => {
        // Interleave an unsolicited server-push event before the RPC response
        daemonChild.stdout.emit(
          "data",
          JSON.stringify({
            event: "task.updated",
            seq: 1,
            vault: vaultPath,
            data: {
              job_id: "job_123",
              kind: "upgrade.heal",
              status: "running",
              current: 3,
              total: 10,
            },
          }) +
            "\n" +
            JSON.stringify({
              id: req.id,
              ok: true,
              exit_code: 0,
              stdout: JSON.stringify({
                ok: true,
                pid: 4242,
                parent_pid: process.pid,
                uptime_sec: 1.5,
                rss_bytes: 18_000_000,
                rss_mb: 17.17,
                heavy_modules_loaded: [],
                active_jobs: [],
                unacked_notice_count: 0,
                cached_vaults: [],
              }),
              stderr: "",
            }) +
            "\n"
        );
      });
      return true;
    });

    const mockSpawn = vi.fn().mockReturnValue(daemonChild);
    const transport = new NodeProcessTransport({
      vaultPath,
      spawnFn: mockSpawn as unknown as typeof import("child_process").spawn,
      useDaemon: true,
    });
    const client = new PaperForgeClient({ transport });
    const receivedEvents: Array<{
      event: string;
      data?: Record<string, unknown>;
    }> = [];
    const unsub = client.onDaemonEvent((ev) => receivedEvents.push(ev));

    const health = await client.daemonHealth();
    expect(health?.ok).toBe(true);
    expect(health?.heavy_modules_loaded).toEqual([]);
    expect(receivedEvents).toHaveLength(1);
    expect(receivedEvents[0].event).toBe("task.updated");
    expect(receivedEvents[0].data?.job_id).toBe("job_123");

    unsub();
    transport.shutdownDaemon();
  });
});
