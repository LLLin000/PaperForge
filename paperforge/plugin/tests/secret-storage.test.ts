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
  legacyEmbeddingSecretIds,
  type SecretAccess,
  type MigrationDeps,
} from "../src/services/secret-storage";

/** A deterministic writer capability standing in for
 * `client.authSetSecret(kind, value, {replace: false})` — records calls
 * without any transport/protocol surface. */
interface WriterCall {
  kind: string;
  value: string;
}

function writerFor(result: boolean): {
  calls: WriterCall[];
  deps: MigrationDeps;
} {
  const calls: WriterCall[] = [];
  return {
    calls,
    deps: {
      writeCredential: async (kind, value) => {
        calls.push({ kind, value });
        return result;
      },
    },
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
  it("writes via the injected credential capability and clears the old value", async () => {
    const { calls, deps } = writerFor(true);
    const ss: SecretAccess = {
      getSecret: vi.fn(async (id: string) =>
        id === "paddleocr-api-key" ? "legacy-secret" : null
      ),
      setSecret: vi.fn(async () => undefined),
    };
    const r = await migrateLegacySecret("ocr", ss, deps);
    expect(r.migrated).toEqual(["paddleocr-api-key"]);
    expect(r.warnings).toEqual([]);
    // host side stays host-side; the write is a capability call, not argv
    expect(calls).toEqual([{ kind: "ocr", value: "legacy-secret" }]);
    expect(ss.setSecret).toHaveBeenCalledWith("paddleocr-api-key", "");
  });

  it("keeps the old SecretStorage value when the capability write fails", async () => {
    const { deps } = writerFor(false);
    const ss: SecretAccess = {
      getSecret: vi.fn(async () => "legacy-secret"),
      setSecret: vi.fn(async () => undefined),
    };
    const r = await migrateLegacySecret("ocr", ss, deps);
    expect(r.migrated).toEqual([]);
    expect(r.warnings.length).toBeGreaterThan(0);
    expect(ss.setSecret).not.toHaveBeenCalled();
  });

  it("no-op when no legacy value exists", async () => {
    const { calls, deps } = writerFor(true);
    const ss: SecretAccess = {
      getSecret: vi.fn(async () => null),
      setSecret: vi.fn(async () => undefined),
    };
    const r = await migrateLegacySecret("embedding", ss, deps);
    expect(r.migrated).toEqual([]);
    expect(calls.length).toBe(0);
  });

  it("migrates a profile-hashed legacy embedding secret (real upgrade path)", async () => {
    // Old runtime stored embedding keys under vector-db-api-key-v2-<hash>.
    const [hashedId] = await legacyEmbeddingSecretIds(
      "https://api.openai.com/v1",
      "text-embedding-3-small"
    );
    expect(hashedId).toMatch(/^vector-db-api-key-v2-[0-9a-f]{40}$/);
    const { calls, deps } = writerFor(true);
    const ss: SecretAccess = {
      getSecret: vi.fn(async (id: string) =>
        id === hashedId ? "old-embedding-secret" : null
      ),
      setSecret: vi.fn(async () => undefined),
    };
    const r = await migrateLegacySecret("embedding", ss, deps, {
      baseUrl: "https://api.openai.com/v1",
      model: "text-embedding-3-small",
    });
    expect(r.migrated).toEqual([hashedId]);
    expect(r.warnings).toEqual([]);
    expect(calls).toEqual([
      { kind: "embedding", value: "old-embedding-secret" },
    ]);
    // the old hashed value is cleared after the verified keyring write
    expect(ss.setSecret).toHaveBeenCalledWith(hashedId, "");
  });

  it("does not report 'no legacy credentials' when only the hashed id exists", async () => {
    const [hashedId] = await legacyEmbeddingSecretIds("https://custom/v1", "m");
    const { deps } = writerFor(true);
    const ss: SecretAccess = {
      getSecret: vi.fn(async (id: string) =>
        id === hashedId ? "secret" : null
      ),
      setSecret: vi.fn(async () => undefined),
    };
    const r = await migrateLegacySecret("embedding", ss, deps, {
      baseUrl: "https://custom/v1",
      model: "m",
    });
    expect(r.migrated).toEqual([hashedId]); // NOT empty — the fixed global id
    // was absent but the hashed id carried the value
  });

  it("migration module carries no transport/protocol surface", () => {
    const src = require("fs").readFileSync(
      require("path").join(__dirname, "../src/services/secret-storage.ts"),
      "utf-8"
    );
    // backend argv knowledge lives ONLY in PaperForgeClient
    expect(src).not.toContain("child_process");
    expect(src).not.toContain('"-m"');
    expect(src).not.toContain("MigrationSpawn");
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
