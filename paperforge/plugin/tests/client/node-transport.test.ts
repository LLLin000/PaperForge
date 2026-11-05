/**
 * NodeProcessTransport unit tests.
 *
 * Verifies Python resolution priority, sanitized environment application,
 * stdin submission, and streaming delegation.
 */

import { describe, it, expect, vi } from "vitest";
import { EventEmitter } from "events";
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

class MockStream extends EventEmitter {
  public setEncoding = vi.fn();
}

class MockChildProcess extends EventEmitter {
  public stdout = new MockStream();
  public stderr = new MockStream();
  public stdin = {
    write: vi.fn(),
    end: vi.fn(),
  };
  public exitCode: number | null = null;
  public kill = vi.fn();
}

describe("NodeProcessTransport", () => {
  const vaultPath = "C:/mock/vault";

  describe("resolvePython", () => {
    it("resolves only the Python-published runtime pointer", async () => {
      runtimeState.pythonPath = "C:/managed/python.exe";
      const transport = new NodeProcessTransport({ vaultPath });

      const result = await transport.resolvePython();
      expect(result).toEqual({
        path: "C:/managed/python.exe",
        args: [],
      });
    });

    it("shows the external installer command when the pointer is absent", async () => {
      runtimeState.pythonPath = "";
      const transport = new NodeProcessTransport({ vaultPath });

      await expect(transport.resolvePython()).rejects.toThrow(
        /paperforge runtime install.*outside Obsidian/
      );
    });
  });

  describe("execute", () => {
    it("spawns python with vault path and executes subcommand", async () => {
      const mockChild = new MockChildProcess();
      const mockSpawn = vi.fn().mockReturnValue(mockChild);

      runtimeState.pythonPath = "C:/py/python.exe";
      const transport = new NodeProcessTransport({
        vaultPath,
        spawnFn: mockSpawn as any,
      });

      const execPromise = transport.execute(["probe", "ocr", "--json"]);
      await Promise.resolve(); // wait for resolvePython microtask

      expect(mockSpawn).toHaveBeenCalledWith(
        "C:/py/python.exe",
        ["-m", "paperforge", "--vault", vaultPath, "probe", "ocr", "--json"],
        expect.objectContaining({
          cwd: vaultPath,
          shell: false,
          windowsHide: true,
          stdio: ["pipe", "pipe", "pipe"],
        })
      );

      // Emit stdout and close
      mockChild.stdout.emit("data", '{"module":"ocr","status":"ok"}');
      mockChild.emit("close", 0);

      const result = await execPromise;
      expect(result).toBe('{"module":"ocr","status":"ok"}');
    });

    it("writes stdin input when provided (for credentials)", async () => {
      const mockChild = new MockChildProcess();
      const mockSpawn = vi.fn().mockReturnValue(mockChild);

      runtimeState.pythonPath = "C:/py/python.exe";
      const transport = new NodeProcessTransport({
        vaultPath,
        spawnFn: mockSpawn as any,
      });

      const execPromise = transport.execute(["auth", "set", "ocr", "--stdin"], {
        stdin: "secret-token-123\n",
      });
      await Promise.resolve(); // wait for resolvePython microtask

      expect(mockChild.stdin.write).toHaveBeenCalledWith("secret-token-123\n");
      expect(mockChild.stdin.end).toHaveBeenCalled();

      mockChild.emit("close", 0);
      await execPromise;
    });

    it("rejects with exit code and stderr on non-zero return", async () => {
      const mockChild = new MockChildProcess();
      const mockSpawn = vi.fn().mockReturnValue(mockChild);

      runtimeState.pythonPath = "C:/py/python.exe";
      const transport = new NodeProcessTransport({
        vaultPath,
        spawnFn: mockSpawn as any,
      });
      const execPromise = transport.execute(["failing", "command"]);
      await Promise.resolve(); // wait for resolvePython microtask

      mockChild.stderr.emit("data", "Error: command failed");
      mockChild.emit("close", 1);

      await expect(execPromise).rejects.toThrow(
        /PaperForge command failed \(exit code 1\)/
      );
    });
  });
});
