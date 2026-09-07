/**
 * Environment hygiene for credential-free subprocesses (#173 / C1).
 *
 * C1 removed SecretStorage runtime authority: the plugin no longer reads,
 * stores, or injects credentials.  Legacy env names (PAPERFORGE_CREDENTIAL_/
 * PADDLEOCR_/VECTOR_DB_/OPENAI_) are redacted from the environment the
 * plugin passes to child processes — Python resolves credentials itself from
 * the canonical env or the OS keyring (paperforge/credentials.py).
 *
 * The ONLY remaining SecretStorage touch is the explicit, user-mediated
 * MIGRATION bridge below (#138 §6): a one-time read → `auth set --stdin` →
 * verified → old value cleared.  Normal runtime never consults it.
 */

// ── Env redaction ──

const LEGACY_CREDENTIAL_ENV_PREFIXES = [
  "PAPERFORGE_CREDENTIAL_",
  "PADDLEOCR_",
  "VECTOR_DB_",
  "OPENAI_",
];

export function stripCredentialEnv(
  env: Record<string, string | undefined>
): Record<string, string | undefined> {
  const result: Record<string, string | undefined> = {};
  for (const [key, value] of Object.entries(env)) {
    if (LEGACY_CREDENTIAL_ENV_PREFIXES.some((prefix) => key.startsWith(prefix)))
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

// ── SecretStorage → keyring migration bridge (explicit, user-mediated) ───

export interface SecretAccess {
  getSecret(id: string): Promise<string | null>;
  setSecret(id: string, secret: string): Promise<void>;
}

export interface MigrationDeps {
  /** Backend credential-write capability — injected by the caller as
   * `client.authSetSecret(kind, value, {replace: false})`.  This module
   * owns ONLY the host side of the migration bridge (where the legacy
   * SecretStorage value lives, how to clear it); it never assembles
   * backend argv. */
  writeCredential: (
    kind: "ocr" | "embedding",
    value: string
  ) => Promise<boolean>;
}

export interface LegacyMigrationResult {
  migrated: string[];
  warnings: string[];
}

/** Known legacy SecretStorage ids (dash format per Obsidian API). */
const LEGACY_OCR_SECRET_ID = "paddleocr-api-key";
const LEGACY_EMBEDDING_GLOBAL_ID = "vector-db-api-key";

/**
 * Legacy profile-scoped embedding id formula — MIGRATION KNOWLEDGE ONLY.
 * The deleted runtime used `vector-db-api-key-v2-<sha256(baseUrl\0model)>`
 * for embedding secrets; real old users hold their key under that id, not
 * the fixed global one.  This must never become a runtime credential
 * identity again.
 */
export async function legacyEmbeddingSecretIds(
  baseUrl: string,
  model: string
): Promise<string[]> {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(
      `${baseUrl.trim()}\u0000${model.trim() || "text-embedding-3-small"}`
    )
  );
  const digestHex = [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
  return [
    `vector-db-api-key-v2-${digestHex.slice(0, 40)}`,
    LEGACY_EMBEDDING_GLOBAL_ID,
  ];
}

/**
 * #173 corrective: one-time migration of a legacy Obsidian SecretStorage
 * value into the Python credential authority.  Explicit user action only —
 * runtime never reads SecretStorage.  Reads once → `auth set --stdin` →
 * verified via `auth status` → old value cleared (empty set is the Obsidian
 * deletion primitive; when unsupported the warning carries manual steps).
 */
export async function migrateLegacySecret(
  kind: "ocr" | "embedding",
  ss: SecretAccess | undefined,
  deps: MigrationDeps,
  embeddingProfile?: { baseUrl: string; model: string }
): Promise<LegacyMigrationResult> {
  if (!ss || typeof ss.getSecret !== "function") {
    return { migrated: [], warnings: ["SecretStorage unavailable"] };
  }
  // #173 corrective: real old embedding secrets live under the
  // profile-hashed v2 id — check it (plus the fixed global fallback)
  // before reporting "no legacy credentials".
  const ids =
    kind === "embedding"
      ? await legacyEmbeddingSecretIds(
          embeddingProfile?.baseUrl ?? "",
          embeddingProfile?.model ?? ""
        )
      : [LEGACY_OCR_SECRET_ID];
  for (const id of ids) {
    const value = await ss.getSecret(id);
    if (!value) continue;
    // The capability's contract is true-or-throw (PaperForgeClient
    // semantics); the migration workflow normalizes a rejection into a
    // host-level result — never lets it escape (e.g. the canonical keyring
    // already holds a value and replace:false was declined).
    let ok = false;
    try {
      ok = await deps.writeCredential(kind, value);
    } catch {
      ok = false;
    }
    if (!ok) {
      return {
        migrated: [],
        warnings: [
          "Keyring write failed — the legacy SecretStorage value was kept. " +
            "Run `paperforge auth set " +
            kind +
            " --stdin` manually.",
        ],
      };
    }
    try {
      await ss.setSecret(id, "");
    } catch {
      return {
        migrated: [id],
        warnings: [
          "Credential migrated and verified, but the old SecretStorage value " +
            "could not be cleared — delete it manually in Obsidian.",
        ],
      };
    }
    return { migrated: [id], warnings: [] };
  }
  return { migrated: [], warnings: [] };
}
