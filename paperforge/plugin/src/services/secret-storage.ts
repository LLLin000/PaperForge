/**
 * SecretStorage credential service (Issue #79).
 */

// ── Well-known secret IDs ──

export const SECRET_KEYS: readonly string[] = [
  "paddleocr_api_key",
  "vector_db_api_key",
] as const;

/** Map settings keys to SecretStorage IDs (dash-format per Obsidian API requirement) */
const SETTINGS_TO_SECRET_ID: Record<string, string> = {
  paddleocr_api_key: "paddleocr-api-key",
  vector_db_api_key: "vector-db-api-key",
};

// ── Allowlist ──

export const CREDENTIAL_COMMAND_ALLOWLIST: Record<string, readonly string[]> = {
  ocr: ["PADDLEOCR_API_KEY", "PADDLEOCR_API_TOKEN"],
  memory: ["VECTOR_DB_API_KEY", "VECTOR_DB_API_BASE", "VECTOR_DB_API_MODEL"],
  embed: ["VECTOR_DB_API_KEY", "VECTOR_DB_API_BASE", "VECTOR_DB_API_MODEL"],
};

// ── Types ──

export interface MigrationResult {
  migrated: string[];
  warnings: string[];
}

interface SecretAccess {
  getSecret(id: string): Promise<string | null>;
  setSecret(id: string, secret: string): Promise<void>;
}

export interface PluginForSecrets {
  app: { secretStorage: SecretAccess };
  saveData(data: unknown): Promise<void>;
}

// ── Migration ──

export async function migrateCredentials(
  plugin: PluginForSecrets,
  settings: Record<string, unknown>,
): Promise<MigrationResult> {
  const ss = plugin.app?.secretStorage;
  if (!ss || typeof ss.getSecret !== "function") {
    return { migrated: [], warnings: [] };
  }

  const migrated: string[] = [];
  const warnings: string[] = [];
  const alreadyMigrated: string[] = Array.isArray(settings._migrated_keys)
    ? (settings._migrated_keys as string[])
    : [];

  for (const key of SECRET_KEYS) {
    if (alreadyMigrated.includes(key)) continue;

    const plaintext = typeof settings[key] === "string" ? (settings[key] as string) : "";
    if (!plaintext) continue;

    const secretId = SETTINGS_TO_SECRET_ID[key] || key;
    const existing = await ss.getSecret(secretId);
    if (existing !== null) {
      if (existing === plaintext) {
        // Crash recovery: secret was stored but plaintext not yet cleared
        settings[key] = "";
        migrated.push(key);
        continue;
      }
      warnings.push(key);
      continue;
    }

    try {
      await ss.setSecret(secretId, plaintext);
    } catch {
      warnings.push(key);
      continue;
    }

    const readback = await ss.getSecret(secretId);
    if (readback !== plaintext) {
      warnings.push(key);
      continue;
    }

    settings[key] = "";
    migrated.push(key);
  }

  if (migrated.length > 0 || warnings.length > 0) {
    const keys = Array.isArray(settings._migrated_keys)
      ? [...(settings._migrated_keys as string[])]
      : [];
    for (const k of migrated) {
      if (!keys.includes(k)) keys.push(k);
    }
    settings._migrated_keys = keys;
    if (warnings.length > 0) {
      const existingWarnings = Array.isArray(settings._migration_warnings)
        ? (settings._migration_warnings as string[])
        : [];
      settings._migration_warnings = [...existingWarnings, ...warnings];
    }
    await plugin.saveData(settings);
  }

  return { migrated, warnings };
}

// ── Credential resolution ──

export async function resolveCredentialEnv(
  plugin: PluginForSecrets,
  commandType: string,
): Promise<Record<string, string>> {
  const allowlist = CREDENTIAL_COMMAND_ALLOWLIST[commandType];
  if (!allowlist) return {};

  const ss = plugin.app.secretStorage;
  const env: Record<string, string> = {};

  if (commandType === "ocr") {
    const key = await ss.getSecret("paddleocr-api-key");
    if (key) {
      env.PADDLEOCR_API_KEY = key;
      env.PADDLEOCR_API_TOKEN = key;
    }
  } else if (commandType === "memory" || commandType === "embed") {
    const key = await ss.getSecret("vector-db-api-key");
    if (key) env.VECTOR_DB_API_KEY = key;
  }

  return env;
}

// ── Env redaction ──

const CREDENTIAL_ENV_PREFIXES = ["PADDLEOCR_", "VECTOR_DB_", "OPENAI_"];

export function stripCredentialEnv(
  env: Record<string, string | undefined>,
): Record<string, string | undefined> {
  const result: Record<string, string | undefined> = {};
  for (const [key, value] of Object.entries(env)) {
    if (CREDENTIAL_ENV_PREFIXES.some((prefix) => key.startsWith(prefix))) continue;
    result[key] = value;
  }
  return result;
}

// ── Command classification ──

const ALLOWLISTED_COMMANDS = new Set(["ocr", "memory", "embed"]);

export function isAllowlistedCommand(commandType: string): boolean {
  return ALLOWLISTED_COMMANDS.has(commandType);
}
