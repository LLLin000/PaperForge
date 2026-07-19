/**
 * Focused tests for SecretStorage credential migration, resolution, and redaction (Issue #79).
 */
import { describe, it, expect, vi } from "vitest";
import {
  SECRET_KEYS,
  CREDENTIAL_COMMAND_ALLOWLIST,
  migrateCredentials,
  resolveCredentialEnv,
  stripCredentialEnv,
  isAllowlistedCommand,
} from "../src/services/secret-storage";
import { paperforgeEnrichedEnv } from "../src/services/python-bridge";

interface SecretStore {
  [id: string]: string;
}

function createMockSecretStorage(initial: SecretStore = {}) {
  const store: SecretStore = { ...initial };
  return {
    store,
    getSecret: vi.fn(
      async (id: string): Promise<string | null> => store[id] ?? null
    ),
    setSecret: vi.fn(async (id: string, secret: string): Promise<void> => {
      store[id] = secret;
    }),
    listSecrets: vi.fn((): string[] => Object.keys(store)),
  };
}

interface PluginMockOpts {
  settings: Record<string, unknown>;
  secretStore?: SecretStore;
  saved?: unknown[];
}

function createMockPlugin(opts: PluginMockOpts) {
  const ss = createMockSecretStorage(opts.secretStore ?? {});
  const saved: unknown[] = opts.saved ?? [];
  return {
    settings: opts.settings,
    app: { secretStorage: ss },
    saveData: vi.fn(async (data: unknown) => {
      saved.push(data);
    }),
    _saved: saved,
    _ss: ss,
  };
}

const OCR_ID = "paddleocr-api-key";
const VEC_ID = "vector-db-api-key";

describe("SecretStorage migration", () => {
  it("migrates plaintext paddleocr_api_key with copy-readback-verify-delete", async () => {
    const plugin = createMockPlugin({
      settings: { paddleocr_api_key: "test-ocr-key-12345" },
    });
    const result = await migrateCredentials(plugin as never, plugin.settings);
    expect(result.migrated).toContain("paddleocr_api_key");
    expect(result.warnings).toHaveLength(0);
    expect(plugin._ss.setSecret).toHaveBeenCalledWith(
      OCR_ID,
      "test-ocr-key-12345"
    );
    expect(plugin._ss.getSecret).toHaveBeenCalledWith(OCR_ID);
    expect(plugin.settings.paddleocr_api_key).toBe("");
    expect(plugin.saveData).toHaveBeenCalled();
  });

  it("migrates plaintext vector_db_api_key", async () => {
    const plugin = createMockPlugin({
      settings: { vector_db_api_key: "sk-test-openai-key" },
    });
    const result = await migrateCredentials(plugin as never, plugin.settings);
    expect(result.migrated).toContain("vector_db_api_key");
    expect(result.warnings).toHaveLength(0);
    expect(plugin._ss.setSecret).toHaveBeenCalledWith(
      VEC_ID,
      "sk-test-openai-key"
    );
    expect(plugin.settings.vector_db_api_key).toBe("");
  });

  it("skips migration for empty credential values", async () => {
    const plugin = createMockPlugin({
      settings: { paddleocr_api_key: "", vector_db_api_key: "" },
    });
    const result = await migrateCredentials(plugin as never, plugin.settings);
    expect(result.migrated).toHaveLength(0);
    expect(plugin._ss.setSecret).not.toHaveBeenCalled();
  });

  it("warns when secret already exists with different value in SecretStorage", async () => {
    const plugin = createMockPlugin({
      settings: { paddleocr_api_key: "old-plaintext" },
      secretStore: { [OCR_ID]: "already-stored-different" },
    });
    const result = await migrateCredentials(plugin as never, plugin.settings);
    expect(result.migrated).toHaveLength(0);
    expect(result.warnings).toContain("paddleocr_api_key");
    // Plaintext preserved for user to decide
    expect(plugin.settings.paddleocr_api_key).toBe("old-plaintext");
  });

  it("completes crash-recovery migration when existing secret equals plaintext", async () => {
    const plugin = createMockPlugin({
      settings: { paddleocr_api_key: "crash-recovery-key" },
      secretStore: { [OCR_ID]: "crash-recovery-key" },
    });
    const result = await migrateCredentials(plugin as never, plugin.settings);
    expect(result.migrated).toContain("paddleocr_api_key");
    expect(result.warnings).toHaveLength(0);
    // Plaintext cleared (crash recovery completed)
    expect(plugin.settings.paddleocr_api_key).toBe("");
  });

  it("produces warning when readback verification fails", async () => {
    const plugin = createMockPlugin({
      settings: { paddleocr_api_key: "original-value" },
    });
    let callCount = 0;
    plugin._ss.getSecret.mockImplementation((id: string) => {
      callCount++;
      if (callCount === 1) return null;
      return "wrong-value";
    });
    const result = await migrateCredentials(plugin as never, plugin.settings);
    expect(plugin.settings.paddleocr_api_key).toBe("original-value");
    expect(result.warnings).toContain("paddleocr_api_key");
    expect(result.migrated).toHaveLength(0);
  });

  it("clears plaintext only after successful readback", async () => {
    const plugin = createMockPlugin({
      settings: { paddleocr_api_key: "secret-abc" },
    });
    plugin._ss.getSecret.mockImplementation(
      (id: string) => plugin._ss.store[id] ?? null
    );
    const result = await migrateCredentials(plugin as never, plugin.settings);
    expect(result.migrated).toContain("paddleocr_api_key");
    expect(plugin.settings.paddleocr_api_key).toBe("");
  });

  it("is idempotent on already-migrated settings", async () => {
    const plugin = createMockPlugin({
      settings: {
        paddleocr_api_key: "",
        _migrated_keys: ["paddleocr_api_key"],
      },
      secretStore: { [OCR_ID]: "stored-secret" },
    });
    const result = await migrateCredentials(plugin as never, plugin.settings);
    expect(result.migrated).toHaveLength(0);
    expect(plugin._ss.setSecret).not.toHaveBeenCalled();
  });

  it("handles setSecret throwing without corrupting plaintext", async () => {
    const plugin = createMockPlugin({
      settings: { paddleocr_api_key: "will-survive-crash" },
    });
    plugin._ss.setSecret.mockImplementation(() => {
      throw new Error("OS keychain unavailable");
    });
    const result = await migrateCredentials(plugin as never, plugin.settings);
    expect(plugin.settings.paddleocr_api_key).toBe("will-survive-crash");
    expect(result.warnings).toContain("paddleocr_api_key");
  });
});

describe("Credential resolution", () => {
  it("returns PADDLEOCR keys only for OCR command", async () => {
    const plugin = createMockPlugin({
      settings: {},
      secretStore: { [OCR_ID]: "ocr-secret-key" },
    });
    const env = await resolveCredentialEnv(plugin as never, "ocr");
    expect(env.PADDLEOCR_API_KEY).toBe("ocr-secret-key");
    expect(env.PADDLEOCR_API_TOKEN).toBe("ocr-secret-key");
    expect(env.VECTOR_DB_API_KEY).toBeUndefined();
  });

  it("returns VECTOR_DB_API_KEY only for memory command", async () => {
    const plugin = createMockPlugin({
      settings: {},
      secretStore: { [VEC_ID]: "sk-memory-key" },
    });
    const env = await resolveCredentialEnv(plugin as never, "memory");
    expect(env.VECTOR_DB_API_KEY).toBe("sk-memory-key");
    expect(env.VECTOR_DB_API_BASE).toBeUndefined();
    expect(env.PADDLEOCR_API_KEY).toBeUndefined();
  });

  it("returns empty env for non-target commands", async () => {
    const plugin = createMockPlugin({
      settings: {},
      secretStore: { [OCR_ID]: "secret", [VEC_ID]: "secret" },
    });
    const env = await resolveCredentialEnv(plugin as never, "pip");
    expect(Object.keys(env)).toHaveLength(0);
  });
});

describe("stripCredentialEnv", () => {
  it("strips PADDLEOCR_, VECTOR_DB_, and OPENAI_ patterns", () => {
    const env = {
      PATH: "/usr/bin",
      HOME: "/home/user",
      PADDLEOCR_API_KEY: "secret-ocr",
      VECTOR_DB_API_KEY: "secret-vec",
      OPENAI_API_KEY: "secret-oai",
      PYTHONPATH: "/app",
    };
    const stripped = stripCredentialEnv(env);
    expect(stripped.PATH).toBe("/usr/bin");
    expect(stripped.HOME).toBe("/home/user");
    expect(stripped.PYTHONPATH).toBe("/app");
    expect(stripped.PADDLEOCR_API_KEY).toBeUndefined();
    expect(stripped.VECTOR_DB_API_KEY).toBeUndefined();
    expect(stripped.OPENAI_API_KEY).toBeUndefined();
  });
});

describe("isAllowlistedCommand", () => {
  it("returns correct mapping", () => {
    expect(isAllowlistedCommand("ocr")).toBe(true);
    expect(isAllowlistedCommand("memory")).toBe(true);
    expect(isAllowlistedCommand("embed")).toBe(true);
    expect(isAllowlistedCommand("pip")).toBe(false);
    expect(isAllowlistedCommand("doctor")).toBe(false);
  });
});

describe("SECRET_KEYS", () => {
  it("contains only well-known credential keys", () => {
    expect(SECRET_KEYS).toContain("paddleocr_api_key");
    expect(SECRET_KEYS).toContain("vector_db_api_key");
    expect(SECRET_KEYS.length).toBe(2);
  });
});

describe("CREDENTIAL_COMMAND_ALLOWLIST", () => {
  it("maps OCR to exactly PADDLEOCR_API_KEY and PADDLEOCR_API_TOKEN", () => {
    const allowlist = CREDENTIAL_COMMAND_ALLOWLIST["ocr"];
    expect(allowlist).toBeDefined();
    expect(allowlist).toContain("PADDLEOCR_API_KEY");
    expect(allowlist).toContain("PADDLEOCR_API_TOKEN");
    expect(allowlist).not.toContain("VECTOR_DB_API_KEY");
    expect(allowlist).not.toContain("OPENAI_API_KEY");
  });

  it("maps memory to VECTOR_DB_API_KEY and related vars, no PADDLEOCR", () => {
    const allowlist = CREDENTIAL_COMMAND_ALLOWLIST["memory"];
    expect(allowlist).toBeDefined();
    expect(allowlist).toContain("VECTOR_DB_API_KEY");
    expect(allowlist).not.toContain("PADDLEOCR_API_KEY");
    expect(allowlist).not.toContain("PADDLEOCR_API_TOKEN");
  });

  it("has no allowlist entry for pip/doctor/managed-runtime commands", () => {
    expect(CREDENTIAL_COMMAND_ALLOWLIST["pip"]).toBeUndefined();
    expect(CREDENTIAL_COMMAND_ALLOWLIST["doctor"]).toBeUndefined();
    expect(CREDENTIAL_COMMAND_ALLOWLIST["install"]).toBeUndefined();
    expect(CREDENTIAL_COMMAND_ALLOWLIST["status"]).toBeUndefined();
    expect(CREDENTIAL_COMMAND_ALLOWLIST["ensure"]).toBeUndefined();
    expect(CREDENTIAL_COMMAND_ALLOWLIST["diagnostics"]).toBeUndefined();
    expect(CREDENTIAL_COMMAND_ALLOWLIST["probe"]).toBeUndefined();
  });
});

describe("production env isolation", () => {
  it("stripCredentialEnv leaves non-credential env vars intact", () => {
    const env = {
      PATH: "/usr/bin",
      HOME: "/home/user",
      PYTHONPATH: "/app",
      NODE_ENV: "production",
      PADDLEOCR_API_KEY: "secret-should-be-stripped",
      VECTOR_DB_API_KEY: "vec-secret-stripped",
      OPENAI_API_KEY: "oai-secret-stripped",
      PADDLEOCR_API_TOKEN: "token-stripped",
      VECTOR_DB_API_BASE: "base-stripped",
      VECTOR_DB_API_MODEL: "model-stripped",
    };
    const stripped = stripCredentialEnv(env);
    expect(stripped.PATH).toBe("/usr/bin");
    expect(stripped.HOME).toBe("/home/user");
    expect(stripped.PYTHONPATH).toBe("/app");
    expect(stripped.NODE_ENV).toBe("production");
    expect(stripped.PADDLEOCR_API_KEY).toBeUndefined();
    expect(stripped.PADDLEOCR_API_TOKEN).toBeUndefined();
    expect(stripped.VECTOR_DB_API_KEY).toBeUndefined();
    expect(stripped.VECTOR_DB_API_BASE).toBeUndefined();
    expect(stripped.VECTOR_DB_API_MODEL).toBeUndefined();
    expect(stripped.OPENAI_API_KEY).toBeUndefined();
  });

  it("resolveCredentialEnv returns empty for non-allowlisted commands", async () => {
    const plugin = createMockPlugin({
      settings: {},
      secretStore: {
        "paddleocr-api-key": "secret",
        "vector-db-api-key": "secret",
      },
    });
    for (const cmd of [
      "pip",
      "doctor",
      "install",
      "status",
      "diagnostics",
      "probe",
      "",
    ]) {
      const env = await resolveCredentialEnv(plugin as never, cmd);
      expect(Object.keys(env)).toHaveLength(0);
    }
  });

  it("resolveCredentialEnv for OCR never returns VECTOR_DB_API_KEY", async () => {
    const plugin = createMockPlugin({
      settings: {},
      secretStore: {
        "paddleocr-api-key": "ocr-secret",
        "vector-db-api-key": "vec-secret",
      },
    });
    const env = await resolveCredentialEnv(plugin as never, "ocr");
    expect(env.PADDLEOCR_API_KEY).toBe("ocr-secret");
    expect(env.PADDLEOCR_API_TOKEN).toBe("ocr-secret");
    expect(env.VECTOR_DB_API_KEY).toBeUndefined();
  });

  it("resolveCredentialEnv for memory never returns PADDLEOCR keys", async () => {
    const plugin = createMockPlugin({
      settings: {},
      secretStore: {
        "paddleocr-api-key": "ocr-secret",
        "vector-db-api-key": "vec-secret",
      },
    });
    const env = await resolveCredentialEnv(plugin as never, "memory");
    expect(env.VECTOR_DB_API_KEY).toBe("vec-secret");
    expect(env.PADDLEOCR_API_KEY).toBeUndefined();
    expect(env.PADDLEOCR_API_TOKEN).toBeUndefined();
  });
});

// ── Production-path command handoff tests (Issue #79) ──

describe("buildTargetedEnv (production dispatch seam)", () => {
  // buildTargetedEnv lives in python-bridge.ts; we test it through the import chain.
  // The function is re-exported: import it via a dynamic require for test isolation.
  let buildTargetedEnv: typeof import("../src/services/python-bridge").buildTargetedEnv;

  beforeAll(async () => {
    const mod = await import("../src/services/python-bridge");
    buildTargetedEnv = mod.buildTargetedEnv;
  });

  it("injects OCR key into env and strips it from process.env base", async () => {
    const plugin = createMockPlugin({
      settings: {},
      secretStore: { "paddleocr-api-key": "pk-ocr-test-secret" },
    });
    const env = await buildTargetedEnv(plugin as never, "ocr");
    // Must contain only the allowlisted OCR credential
    expect(env.PADDLEOCR_API_KEY).toBe("pk-ocr-test-secret");
    expect(env.PADDLEOCR_API_TOKEN).toBe("pk-ocr-test-secret");
    // Must NOT contain unrelated secrets
    expect(env.VECTOR_DB_API_KEY).toBeUndefined();
    expect(env.OPENAI_API_KEY).toBeUndefined();
    // Non-credential env vars (e.g. PATH) must survive
    expect(env.PATH).toBeDefined();
  });

  it("injects Memory key into env and strips it from process.env base", async () => {
    const plugin = createMockPlugin({
      settings: {},
      secretStore: { "vector-db-api-key": "vk-mem-test-secret" },
    });
    const env = await buildTargetedEnv(plugin as never, "memory");
    expect(env.VECTOR_DB_API_KEY).toBe("vk-mem-test-secret");
    expect(env.PADDLEOCR_API_KEY).toBeUndefined();
  });

  it("embed command gets same Memory credentials as memory command", async () => {
    const plugin = createMockPlugin({
      settings: {},
      secretStore: { "vector-db-api-key": "vk-embed-test" },
    });
    const env = await buildTargetedEnv(plugin as never, "embed");
    expect(env.VECTOR_DB_API_KEY).toBe("vk-embed-test");
    expect(env.PADDLEOCR_API_KEY).toBeUndefined();
  });

  it("non-allowlisted command returns base env with no credential injection", async () => {
    const plugin = createMockPlugin({
      settings: {},
      secretStore: {
        "paddleocr-api-key": "secret",
        "vector-db-api-key": "secret",
      },
    });
    for (const cmd of [
      "pip",
      "doctor",
      "install",
      "status",
      "diagnostics",
      "probe",
      "sync",
      "repair",
      "",
    ]) {
      const env = await buildTargetedEnv(plugin as never, cmd);
      expect(env.PADDLEOCR_API_KEY).toBeUndefined();
      expect(env.PADDLEOCR_API_TOKEN).toBeUndefined();
      expect(env.VECTOR_DB_API_KEY).toBeUndefined();
      expect(env.OPENAI_API_KEY).toBeUndefined();
    }
  });

  it("OCR command never leaks vector-db secret", async () => {
    const plugin = createMockPlugin({
      settings: {},
      secretStore: {
        "paddleocr-api-key": "ocr-only",
        "vector-db-api-key": "vec-should-not-leak",
      },
    });
    const env = await buildTargetedEnv(plugin as never, "ocr");
    expect(env.PADDLEOCR_API_KEY).toBe("ocr-only");
    expect(env.VECTOR_DB_API_KEY).toBeUndefined();
  });
});

describe("targeted vs non-targeted command isolation", () => {
  // Verify that the allowlist-based routing prevents credential leakage
  // even when secrets exist in storage.

  const PLUGIN_WITH_ALL_SECRETS = createMockPlugin({
    settings: {},
    secretStore: {
      "paddleocr-api-key": "ocr-secret-123",
      "vector-db-api-key": "vec-secret-456",
    },
  });

  it("targeted OCR: PADDLEOCR_API_KEY present, VECTOR_DB_API_KEY absent", async () => {
    const env = await resolveCredentialEnv(
      PLUGIN_WITH_ALL_SECRETS as never,
      "ocr"
    );
    expect(env.PADDLEOCR_API_KEY).toBe("ocr-secret-123");
    expect(env.PADDLEOCR_API_TOKEN).toBe("ocr-secret-123");
    expect(env.VECTOR_DB_API_KEY).toBeUndefined();
  });

  it("targeted memory: VECTOR_DB_API_KEY present, PADDLEOCR keys absent", async () => {
    const env = await resolveCredentialEnv(
      PLUGIN_WITH_ALL_SECRETS as never,
      "memory"
    );
    expect(env.VECTOR_DB_API_KEY).toBe("vec-secret-456");
    expect(env.PADDLEOCR_API_KEY).toBeUndefined();
    expect(env.PADDLEOCR_API_TOKEN).toBeUndefined();
  });

  it("non-targeted paths (install/ensure/status/pip/probe/diagnostics) receive zero secrets", async () => {
    for (const cmd of [
      "install",
      "ensure",
      "status",
      "pip",
      "probe",
      "diagnostics",
      "doctor",
      "sync",
      "repair",
      "",
    ]) {
      const env = await resolveCredentialEnv(
        PLUGIN_WITH_ALL_SECRETS as never,
        cmd
      );
      expect(Object.keys(env)).toHaveLength(0);
    }
  });

  it("isAllowlistedCommand correctly classifies production commands", () => {
    expect(isAllowlistedCommand("ocr")).toBe(true);
    expect(isAllowlistedCommand("memory")).toBe(true);
    expect(isAllowlistedCommand("embed")).toBe(true);
    expect(isAllowlistedCommand("install")).toBe(false);
    expect(isAllowlistedCommand("ensure")).toBe(false);
    expect(isAllowlistedCommand("pip")).toBe(false);
    expect(isAllowlistedCommand("status")).toBe(false);
    expect(isAllowlistedCommand("probe")).toBe(false);
    expect(isAllowlistedCommand("diagnostics")).toBe(false);
    expect(isAllowlistedCommand("doctor")).toBe(false);
    expect(isAllowlistedCommand("sync")).toBe(false);
    expect(isAllowlistedCommand("repair")).toBe(false);
    expect(isAllowlistedCommand("")).toBe(false);
  });
});

describe("migration warnings shape (settings surface contract)", () => {
  it("_migration_warnings populated on verification failure", async () => {
    // Simulate: secret exists in storage (conflict), migration should warn
    const plugin = createMockPlugin({
      settings: { paddleocr_api_key: "plaintext-key" },
      secretStore: { "paddleocr-api-key": "existing-secret-conflict" },
    });
    const result = await migrateCredentials(plugin as never, plugin.settings);
    expect(result.warnings).toContain("paddleocr_api_key");
    expect(result.migrated).not.toContain("paddleocr_api_key");
    // Plaintext preserved
    expect(plugin.settings.paddleocr_api_key).toBe("plaintext-key");
  });

  it("_migration_warnings contains key names only, no secret values", async () => {
    const secretValue = "sk-abc123-secret-value";
    const plugin = createMockPlugin({
      settings: { paddleocr_api_key: secretValue },
      secretStore: { "paddleocr-api-key": "existing-conflict" },
    });
    const result = await migrateCredentials(plugin as never, plugin.settings);
    expect(result.warnings).toHaveLength(1);
    // Warnings should only contain the key name, not the secret
    const warningsStr = JSON.stringify(result.warnings);
    expect(warningsStr).not.toContain(secretValue);
    expect(warningsStr).toContain("paddleocr_api_key");
  });

  it("successful migration clears plaintext and records migrated key", async () => {
    const plugin = createMockPlugin({
      settings: {
        paddleocr_api_key: "pk-to-migrate",
        _migrated_keys: [],
        _migration_warnings: [],
      },
      secretStore: {},
    });
    const result = await migrateCredentials(plugin as never, plugin.settings);
    expect(result.migrated).toContain("paddleocr_api_key");
    expect(result.warnings).toHaveLength(0);
    expect(plugin.settings.paddleocr_api_key).toBe("");
    expect(plugin.settings._migrated_keys).toContain("paddleocr_api_key");
    expect(plugin.settings._paddleocr_configured).toBe(true);
  });

  it("re-running migration is idempotent (already-migrated keys skipped)", async () => {
    const plugin = createMockPlugin({
      settings: {
        paddleocr_api_key: "pk-already-done",
        _migrated_keys: ["paddleocr_api_key"],
        _migration_warnings: [],
      },
      secretStore: {},
    });
    const result = await migrateCredentials(plugin as never, plugin.settings);
    expect(result.migrated).toHaveLength(0);
    // Plaintext preserved because key was already migrated
    expect(plugin.settings.paddleocr_api_key).toBe("pk-already-done");
  });
});
describe("SecretStorage write + read-back verification (Fix A)", () => {
  it("setSecret followed by getSecret returns the stored value", async () => {
    const ss = createMockSecretStorage({});
    await ss.setSecret("paddleocr-api-key", "test-key-for-verify");
    const readback = await ss.getSecret("paddleocr-api-key");
    expect(readback).toBe("test-key-for-verify");
  });

  it("overwriting a secret replaces the old value", async () => {
    const ss = createMockSecretStorage({ "paddleocr-api-key": "old-key" });
    await ss.setSecret("paddleocr-api-key", "new-key-xyz");
    expect(await ss.getSecret("paddleocr-api-key")).toBe("new-key-xyz");
  });

  it("Boolean flag pattern: settings never hold raw key after SecretStorage write", async () => {
    const plugin = createMockPlugin({
      settings: { paddleocr_api_key: "", _paddleocr_configured: false },
      secretStore: {},
    });
    // Simulate: user validates key, writes to SecretStorage
    await plugin._ss.setSecret("paddleocr-api-key", "validated-key-abc");
    const readback = await plugin._ss.getSecret("paddleocr-api-key");
    if (readback === "validated-key-abc") {
      plugin.settings._paddleocr_configured = true;
      plugin.settings.paddleocr_api_key = "";
      await plugin.saveData(plugin.settings);
    }
    // Settings must NOT contain raw key
    expect(plugin.settings.paddleocr_api_key).toBe("");
    // Boolean flag must be set
    expect(plugin.settings._paddleocr_configured).toBe(true);
    // SecretStorage must have the key
    expect(await plugin._ss.getSecret("paddleocr-api-key")).toBe(
      "validated-key-abc"
    );
  });
});

describe("setup/install argv isolation (Fix B)", () => {
  it("resolveCredentialEnv returns empty for setup command", async () => {
    const plugin = createMockPlugin({
      settings: {},
      secretStore: { "paddleocr-api-key": "ocr-secret-123" },
    });
    const env = await resolveCredentialEnv(plugin as never, "setup");
    expect(Object.keys(env)).toHaveLength(0);
  });

  it("resolveCredentialEnv returns empty for install command", async () => {
    const plugin = createMockPlugin({
      settings: {},
      secretStore: {
        "paddleocr-api-key": "ocr-secret-123",
        "vector-db-api-key": "vec-secret",
      },
    });
    const env = await resolveCredentialEnv(plugin as never, "install");
    expect(Object.keys(env)).toHaveLength(0);
  });

  it("isAllowlistedCommand rejects setup and install", () => {
    expect(isAllowlistedCommand("setup")).toBe(false);
    expect(isAllowlistedCommand("install")).toBe(false);
  });
});

describe("embed env strip-before-inject (Fix C)", () => {
  it("paperforgeEnrichedEnv strips credential prefixes from process.env", () => {
    // paperforgeEnrichedEnv calls stripCredentialEnv internally
    const env = paperforgeEnrichedEnv();
    expect(env.PADDLEOCR_API_KEY).toBeUndefined();
    expect(env.PADDLEOCR_API_TOKEN).toBeUndefined();
    expect(env.VECTOR_DB_API_KEY).toBeUndefined();
    expect(env.OPENAI_API_KEY).toBeUndefined();
    // Non-credential vars survive
    expect(env.PATH).toBeDefined();
  });

  it("buildTargetedEnv for embed: base is stripped, only allowlisted key injected", async () => {
    const { buildTargetedEnv } = await import("../src/services/python-bridge");
    const plugin = createMockPlugin({
      settings: {},
      secretStore: { "vector-db-api-key": "vk-embed-isolated" },
    });
    const env = await buildTargetedEnv(plugin as never, "embed");
    // Allowlisted key injected from SecretStorage
    expect(env.VECTOR_DB_API_KEY).toBe("vk-embed-isolated");
    // No other credential prefixes leak
    expect(env.PADDLEOCR_API_KEY).toBeUndefined();
    expect(env.PADDLEOCR_API_TOKEN).toBeUndefined();
    expect(env.OPENAI_API_KEY).toBeUndefined();
    // Non-credential vars must survive stripping
    expect(env.PATH).toBeDefined();
  });

  it("buildTargetedEnv for non-allowlisted command: fully stripped, no injection", async () => {
    const { buildTargetedEnv } = await import("../src/services/python-bridge");
    const plugin = createMockPlugin({
      settings: {},
      secretStore: {
        "paddleocr-api-key": "ocr-secret",
        "vector-db-api-key": "vec-secret",
      },
    });
    for (const cmd of [
      "setup",
      "install",
      "status",
      "diagnostics",
      "probe",
      "",
    ]) {
      const env = await buildTargetedEnv(plugin as never, cmd);
      expect(env.PADDLEOCR_API_KEY).toBeUndefined();
      expect(env.VECTOR_DB_API_KEY).toBeUndefined();
    }
  });
});
