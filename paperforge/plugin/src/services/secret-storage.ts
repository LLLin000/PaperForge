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
const SETTINGS_TO_CONFIGURED_FLAG: Record<string, string> = {
  paddleocr_api_key: "_paddleocr_configured",
  vector_db_api_key: "_vector_db_configured",
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
  settings?: {
    vector_db_api_base?: string;
    vector_db_api_model?: string;
  };
}

export interface VectorDbCredentialProfile {
  baseUrl: string;
  model: string;
}

function canonicalVectorDbProfile({
  baseUrl,
  model,
}: VectorDbCredentialProfile): string {
  return `${baseUrl.trim()}\u0000${model.trim() || "text-embedding-3-small"}`;
}

export async function vectorDbSecretId(
  profile: VectorDbCredentialProfile
): Promise<string> {
  const bytes = new TextEncoder().encode(canonicalVectorDbProfile(profile));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const digestHex = [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
  // Obsidian accepts only lowercase/digit/dash secret IDs up to 64 characters.
  return `vector-db-api-key-v2-${digestHex.slice(0, 40)}`;
}

export async function storeVectorDbCredential(
  plugin: PluginForSecrets,
  profile: VectorDbCredentialProfile,
  value: string
): Promise<boolean> {
  if (!value) return false;
  const id = await vectorDbSecretId(profile);
  try {
    await plugin.app.secretStorage.setSecret(id, value);
    return (await plugin.app.secretStorage.getSecret(id)) === value;
  } catch {
    return false;
  }
}

export async function hasVectorDbCredential(
  plugin: PluginForSecrets,
  profile: VectorDbCredentialProfile | null = null
): Promise<boolean> {
  return Boolean(
    await plugin.app.secretStorage.getSecret(
      await vectorDbSecretId(profile ?? { baseUrl: "", model: "" })
    )
  );
}

// ── Migration ──

export async function migrateCredentials(
  plugin: PluginForSecrets,
  settings: Record<string, unknown>
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

    const plaintext =
      typeof settings[key] === "string" ? (settings[key] as string) : "";
    if (!plaintext) continue;

    const secretId =
      key === "vector_db_api_key"
        ? await vectorDbSecretId({
            baseUrl:
              typeof settings.vector_db_api_base === "string"
                ? settings.vector_db_api_base
                : "",
            model:
              typeof settings.vector_db_api_model === "string"
                ? settings.vector_db_api_model
                : "",
          })
        : SETTINGS_TO_SECRET_ID[key] || key;
    const existing = await ss.getSecret(secretId);
    if (existing !== null) {
      if (existing === plaintext) {
        // Crash recovery: secret was stored but plaintext not yet cleared
        settings[key] = "";
        settings[SETTINGS_TO_CONFIGURED_FLAG[key]] = true;
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
    settings[SETTINGS_TO_CONFIGURED_FLAG[key]] = true;
  }

  const vectorProfile = {
    baseUrl:
      typeof settings.vector_db_api_base === "string"
        ? settings.vector_db_api_base
        : "",
    model:
      typeof settings.vector_db_api_model === "string"
        ? settings.vector_db_api_model
        : "",
  };
  // Legacy global secrets lack endpoint/model provenance and must not be
  // assigned to a profile automatically.
  let profileStateChanged = false;
  const profileConfigured = await hasVectorDbCredential(plugin, vectorProfile);
  if (settings._vector_db_configured !== profileConfigured) {
    settings._vector_db_configured = profileConfigured;
    profileStateChanged = true;
  }

  const existingWarnings = Array.isArray(settings._migration_warnings)
    ? (settings._migration_warnings as string[])
    : [];
  const nextWarnings = profileConfigured
    ? [...existingWarnings, ...warnings].filter(
        (key) => key !== "vector_db_api_key"
      )
    : [...existingWarnings, ...warnings];
  const warningsChanged =
    nextWarnings.length !== existingWarnings.length ||
    nextWarnings.some((key, index) => key !== existingWarnings[index]);

  if (
    migrated.length > 0 ||
    warnings.length > 0 ||
    profileStateChanged ||
    warningsChanged
  ) {
    const keys = Array.isArray(settings._migrated_keys)
      ? [...(settings._migrated_keys as string[])]
      : [];
    for (const k of migrated) {
      if (!keys.includes(k)) keys.push(k);
    }
    settings._migrated_keys = keys;
    settings._migration_warnings = nextWarnings;
    await plugin.saveData(settings);
  }

  return { migrated, warnings };
}

// ── Credential resolution ──

function profileFromPlugin(
  plugin: PluginForSecrets
): VectorDbCredentialProfile | undefined {
  const settings = plugin.settings;
  if (!settings) return undefined;
  return {
    baseUrl: settings.vector_db_api_base ?? "",
    model: settings.vector_db_api_model ?? "",
  };
}

export async function resolveCredentialEnv(
  plugin: PluginForSecrets,
  commandType: string,
  vectorProfile?: VectorDbCredentialProfile
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
    const profile = vectorProfile ?? profileFromPlugin(plugin);
    if (!profile) return env;
    const key = await ss.getSecret(await vectorDbSecretId(profile));
    if (key) env.VECTOR_DB_API_KEY = key;
  }

  return env;
}

// ── Env redaction ──

const CREDENTIAL_ENV_PREFIXES = ["PADDLEOCR_", "VECTOR_DB_", "OPENAI_"];

export function stripCredentialEnv(
  env: Record<string, string | undefined>
): Record<string, string | undefined> {
  const result: Record<string, string | undefined> = {};
  for (const [key, value] of Object.entries(env)) {
    if (CREDENTIAL_ENV_PREFIXES.some((prefix) => key.startsWith(prefix)))
      continue;
    result[key] = value;
  }
  return result;
}

// ── Command classification ──

const ALLOWLISTED_COMMANDS = new Set(["ocr", "memory", "embed"]);

export function isAllowlistedCommand(commandType: string): boolean {
  return ALLOWLISTED_COMMANDS.has(commandType);
}
