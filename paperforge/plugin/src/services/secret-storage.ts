/**
 * Environment hygiene for credential-free subprocesses (#173 / C1).
 *
 * C1 removed SecretStorage runtime authority: the plugin no longer reads,
 * stores, or injects credentials.  Legacy env names (PADDLEOCR_/VECTOR_DB_/
 * OPENAI_) are redacted from the environment the plugin passes to child
 * processes — Python resolves credentials itself from the canonical
 * PAPERFORGE_CREDENTIAL_* env or the OS keyring (paperforge/credentials.py).
 */

// ── Env redaction ──

const LEGACY_CREDENTIAL_ENV_PREFIXES = ["PADDLEOCR_", "VECTOR_DB_", "OPENAI_"];

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
