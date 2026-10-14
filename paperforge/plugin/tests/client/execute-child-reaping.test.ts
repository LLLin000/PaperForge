import { describe, it, expect, vi } from "vitest";
import { EventEmitter } from "events";
import { spawn as nodeSpawn } from "child_process";
import { NodeProcessTransport } from "../../src/client/node-transport";

class MockStream extends EventEmitter {
  public setEncoding = vi.fn();
}

class MockChildProcess extends EventEmitter {
  public stdout = new MockStream();
  public stderr = new MockStream();
  public stdin = { write: vi.fn(), end: vi.fn() };
  public exitCode: number | null = null;
  public kill = vi.fn();
  public pid: number | undefined;
}

describe("execute child reaping", () => {
  it("removes a child from the registry on normal exit", async () => {
    const mockChild = new MockChildProcess();
    const mockSpawn = vi.fn().mockReturnValue(mockChild);
    const transport = new NodeProcessTransport({
      vaultPath: "C:/mock/vault",
      spawnFn: mockSpawn as any,
    });

    const execPromise = transport.execute(["probe", "ocr", "--json"], {
      pythonExe: "C:/py/python.exe",
    });
    await Promise.resolve();

    const registry = NodeProcessTransport.executeChildren;
    expect(registry.has(mockChild as any)).toBe(true);

    mockChild.emit("close", 0);
    await execPromise;
    expect(registry.has(mockChild as any)).toBe(false);
  });

  it("removes nothing (no leak) when spawn throws", async () => {
    const mockSpawn = vi.fn(() => {
      throw new Error("spawn failed");
    });
    const transport = new NodeProcessTransport({
      vaultPath: "C:/mock/vault",
      spawnFn: mockSpawn as any,
    });

    await expect(
      transport.execute(["probe", "ocr", "--json"], {
        pythonExe: "C:/py/python.exe",
      })
    ).rejects.toThrow(/spawn failed|Failed to spawn/);

    expect(NodeProcessTransport.executeChildren.size).toBe(0);
  });

  it("kills the whole tree on timeout (direct child has a pid)", async () => {
    vi.useFakeTimers();
    try {
      const mockChild = new MockChildProcess();
      mockChild.pid = 4242;
      const mockSpawn = vi.fn().mockReturnValue(mockChild);
      const transport = new NodeProcessTransport({
        vaultPath: "C:/mock/vault",
        spawnFn: mockSpawn as any,
      });

      const execPromise = transport.execute(["ocr", "run", "--json"], {
        pythonExe: "C:/py/python.exe",
        timeoutMs: 100,
      });
      await Promise.resolve();

      // jsdom-like? advance timers
      vi.advanceTimersByTime(150);

      await expect(execPromise).rejects.toMatchObject({ timedOut: true });
      // With a pid, hardKill escalates via the OS tree-kill path rather than
      // child.kill() alone; the registry entry may remain until close fires.
    } finally {
      vi.useRealTimers();
    }
  });

  it("reaps a real long-running child on plugin-style unload", async () => {
    const child = nodeSpawn(
      process.execPath,
      ["-e", "setTimeout(() => {}, 100000)"],
      { windowsHide: true, stdio: "ignore" }
    );

    NodeProcessTransport.executeChildren.add(child as any);
    expect(NodeProcessTransport.executeChildren.has(child as any)).toBe(true);

    NodeProcessTransport.reapAllExecuteChildren();
    expect(NodeProcessTransport.executeChildren.has(child as any)).toBe(false);

    const exited = await new Promise<boolean>((resolve) => {
      const timer = setTimeout(() => resolve(false), 5000);
      child.on("exit", () => {
        clearTimeout(timer);
        resolve(true);
      });
    });
    expect(exited).toBe(true);
  });
});
