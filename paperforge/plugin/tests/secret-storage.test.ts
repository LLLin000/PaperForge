/**
 * Environment hygiene + migration bridge tests (#173 / C1).
 *
 * The SecretStorage runtime authority was deleted with C1; the only
 * remaining touch is the explicit, user-mediated migration bridge.
 */
import { describe, it, expect, vi } from "vitest";

import {
  stripCredentialEnv,
  isAllowlistedCommand,
  migrateLegacySecret,
  type SecretAccess,
  type MigrationSpawn,
} from "../src/services/secret-storage";

interface SpawnCall {
  command: string;
  args: string[];
  opts: Record<string, unknown>;
  written: string;
}

interface FakeSpawnHandle {
  calls: SpawnCall[];
  spawn: (
    command: string,
    args: string[],
    opts: Record<string, unknown>
  ) => {
    stdin: { write(s: string): void; end(): void };
    stdout: { on(ev: "data", cb: (d: unknown) => void): void };
    on(ev: "error" | "close", cb: (arg?: unknown) => void): void;
  };
}

/** A spawn that completes deterministically on a microtask — no wall-clock
 *  timers; the close/stdout events fire before the awaited promise resolves. */
function fakeSpawn(result: { code: number; stdout: string }): FakeSpawnHandle {
  const calls: SpawnCall[] = [];
  const spawn: FakeSpawnHandle["spawn"] = (command, args, opts) => {
    const rec: SpawnCall = { command, args, opts, written: "" };
    calls.push(rec);
    const handlers: Record<string, (arg?: unknown) => void> = {};
    let dataCb: ((d: unknown) => void) | null = null;
    return {
      stdin: {
        write(s: string) {
          rec.written = s;
        },
        end() {},
      },
      stdout: {
        on(ev: "data", cb: (d: unknown) => void) {
          dataCb = cb;
        },
      },
      on(ev: "error" | "close", cb: (arg?: unknown) => void) {
        handlers[ev] = cb;
        queueMicrotask(() => {
          if (result.stdout) dataCb?.(result.stdout);
          handlers["close"]?.(result.code);
        });
      },
    };
  };
  return { calls, spawn };
}

function depsFor(fake: FakeSpawnHandle, vault = "/vault"): MigrationSpawn {
  return {
    spawn: fake.spawn as never,
    pythonPath: "/fake/python",
    pythonArgs: [],
    vaultPath: vault,
    env: { PATH: "/usr/bin" },
  };
}

describe("stripCredentialEnv", () => {
  it("redacts canonical AND legacy credential env from child environments", () => {
    const env = {
      PATH: "/usr/bin",
      PAPERFORGE_CREDENTIAL_OCR__DEFAULT: "canonical-token",
      PADDLEOCR_API_TOKEN: "legacy-1",
      VECTOR_DB_API_KEY: "legacy-2",
      OPENAI_API_KEY: "legacy-3",
    };
    const stripped = stripCredentialEnv(env);
    expect(stripped.PATH).toBe("/usr/bin");
    // #173 corrective: desktop children never inherit credential env —
    // Python resolves through the keyring on desktop.
    expect(stripped.PAPERFORGE_CREDENTIAL_OCR__DEFAULT).toBeUndefined();
    expect(stripped.PADDLEOCR_API_TOKEN).toBeUndefined();
    expect(stripped.VECTOR_DB_API_KEY).toBeUndefined();
    expect(stripped.OPENAI_API_KEY).toBeUndefined();
  });
});

describe("isAllowlistedCommand", () => {
  it("classifies ocr/memory/embed as allowlisted", () => {
    expect(isAllowlistedCommand("ocr")).toBe(true);
    expect(isAllowlistedCommand("memory")).toBe(true);
    expect(isAllowlistedCommand("embed")).toBe(true);
    expect(isAllowlistedCommand("pip")).toBe(false);
    expect(isAllowlistedCommand("doctor")).toBe(false);
  });
});

describe("migrateLegacySecret (explicit bridge only)", () => {
  it("migrates via auth set --stdin and clears the old value after success", async () => {
    const fake = fakeSpawn({ code: 0, stdout: JSON.stringify({ ok: true }) });
    const ss: SecretAccess = {
      getSecret: vi.fn(async (id: string) =>
        id === "paddleocr-api-key" ? "legacy-secret" : null
      ),
      setSecret: vi.fn(async () => undefined),
    };
    const r = await migrateLegacySecret("ocr", ss, depsFor(fake));
    expect(r.migrated).toEqual(["paddleocr-api-key"]);
    expect(r.warnings).toEqual([]);
    expect(fake.calls.length).toBe(1);
    const call = fake.calls[0];
    expect(call.args).toContain("auth");
    expect(call.args).toContain("set");
    expect(call.args).toContain("ocr");
    expect(call.args).toContain("--stdin");
    // secret travels via stdin only, never argv
    expect(call.args.join(" ")).not.toContain("legacy-secret");
    expect(call.written).toBe("legacy-secret");
    expect(ss.setSecret).toHaveBeenCalledWith("paddleocr-api-key", "");
  });

  it("keeps the old SecretStorage value when the keyring write fails", async () => {
    const fake = fakeSpawn({ code: 1, stdout: JSON.stringify({ ok: false }) });
    const ss: SecretAccess = {
      getSecret: vi.fn(async () => "legacy-secret"),
      setSecret: vi.fn(async () => undefined),
    };
    const r = await migrateLegacySecret("ocr", ss, depsFor(fake));
    expect(r.migrated).toEqual([]);
    expect(r.warnings.length).toBeGreaterThan(0);
    expect(ss.setSecret).not.toHaveBeenCalled();
  });

  it("no-op when no legacy value exists", async () => {
    const fake = fakeSpawn({ code: 0, stdout: "{}" });
    const ss: SecretAccess = {
      getSecret: vi.fn(async () => null),
      setSecret: vi.fn(async () => undefined),
    };
    const r = await migrateLegacySecret("embedding", ss, depsFor(fake));
    expect(r.migrated).toEqual([]);
    expect(fake.calls.length).toBe(0);
  });

  it("runtime never reads SecretStorage — migration is the only consumer", () => {
    const src = require("fs").readFileSync(
      require("path").join(__dirname, "../src/services/python-bridge.ts"),
      "utf-8"
    );
    expect(src).not.toContain("secretStorage");
    expect(src).not.toContain("getSecret");
  });
});
