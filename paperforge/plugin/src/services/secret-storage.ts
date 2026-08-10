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

export interface MigrationSpawn {
  spawn: (
    command: string,
    args: string[],
    opts: { cwd: string; env: Record<string, string | undefined>; windowsHide: boolean; stdio: string[] }
  ) => {
    stdin: { write(s: string): void; end(): void };
    stdout: { on(ev: "data", cb: (d: unknown) => void): void };
    on(ev: "error" | "close", cb: (arg?: unknown) => void): void;
  };
  pythonPath: string;
  pythonArgs: string[];
  vaultPath: string;
  env: Record<string, string | undefined>;
}

export interface LegacyMigrationResult {
  migrated: string[];
  warnings: string[];
}

/** Known legacy SecretStorage ids (dash format per Obsidian API). */
const LEGACY_SECRET_IDS: Record<"ocr" | "embedding", string> = {
  ocr: "paddleocr-api-key",
  embedding: "vector-db-api-key",
};

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
  deps: MigrationSpawn
): Promise<LegacyMigrationResult> {
  if (!ss || typeof ss.getSecret !== "function") {
    return { migrated: [], warnings: ["SecretStorage unavailable"] };
  }
  const id = LEGACY_SECRET_IDS[kind];
  const value = await ss.getSecret(id);
  if (!value) {
    return { migrated: [], warnings: [] };
  }
  const ok = await _authSetViaSpawn(kind, value, deps);
  if (!ok) {
    return {
      migrated: [],
      warnings: [
        "Keyring write failed — the legacy SecretStorage value was kept. " +
          "Run `paperforge auth set " + kind + " --stdin` manually.",
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

function _authSetViaSpawn(
  kind: "ocr" | "embedding",
  value: string,
  deps: MigrationSpawn
): Promise<boolean> {
  return new Promise((resolvePromise) => {
    const child = deps.spawn(
      deps.pythonPath,
      [
        ...deps.pythonArgs,
        "-m",
        "paperforge",
        "--vault",
        deps.vaultPath,
        "auth",
        "set",
        kind,
        "--stdin",
        "--json",
      ],
      {
        cwd: deps.vaultPath,
        env: deps.env,
        windowsHide: true,
        stdio: ["pipe", "pipe", "pipe"],
      }
    );
    let stdout = "";
    child.stdout.on("data", (d) => (stdout += String(d)));
    child.on("error", () => resolvePromise(false));
    child.on("close", (code) => {
      try {
        const parsed = JSON.parse(stdout) as { ok?: boolean };
        resolvePromise(code === 0 && parsed?.ok === true);
      } catch {
        resolvePromise(false);
      }
    });
    child.stdin.write(value);
    child.stdin.end();
  });
}
