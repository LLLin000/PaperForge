/**
 * Environment hygiene tests (#173 / C1).
 *
 * The migration / resolution surfaces (migrateCredentials,
 * resolveCredentialEnv, vectorDbSecretId, ...) were deleted with the
 * SecretStorage runtime authority; only the env-redaction and command
 * classification helpers remain.
 */
import { describe, it, expect } from "vitest";

import { stripCredentialEnv, isAllowlistedCommand } from "../src/services/secret-storage";

describe("stripCredentialEnv", () => {
  it("removes legacy credential env names from child environments", () => {
    const env = {
      PATH: "/usr/bin",
      PAPERFORGE_CREDENTIAL_OCR__DEFAULT: "canonical-token",
      PADDLEOCR_API_TOKEN: "legacy-1",
      VECTOR_DB_API_KEY: "legacy-2",
      OPENAI_API_KEY: "legacy-3",
      VECTOR_DB_API_BASE: "https://example.com",
    };
    const stripped = stripCredentialEnv(env);
    expect(stripped.PATH).toBe("/usr/bin");
    // #173/C1: canonical credential env passes through (Python resolves it);
    // legacy names are redacted — Python no longer reads them.
    expect(stripped.PAPERFORGE_CREDENTIAL_OCR__DEFAULT).toBe("canonical-token");
    expect(stripped.PADDLEOCR_API_TOKEN).toBeUndefined();
    expect(stripped.VECTOR_DB_API_KEY).toBeUndefined();
    expect(stripped.OPENAI_API_KEY).toBeUndefined();
    // Endpoint/model are non-secret config and live in paperforge.json —
    // legacy env plumbing is gone entirely.
    expect(stripped.VECTOR_DB_API_BASE).toBeUndefined();
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
