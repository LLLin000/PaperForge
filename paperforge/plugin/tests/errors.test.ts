import { describe, it, expect } from "vitest";

import {
  classifyError,
  classifySetupFailure,
} from "../src/services/python-bridge";

describe("classifyError", () => {
  it("classifies ENOENT as python_missing", () => {
    const result = classifyError("ENOENT");
    expect(result.type).toBe("python_missing");
    expect(result.recoverable).toBe(true);
    expect(result.message).toContain("Python");
  });

  it("classifies MODULE_NOT_FOUND as import_failed", () => {
    const result = classifyError("MODULE_NOT_FOUND");
    expect(result.type).toBe("import_failed");
    expect(result.recoverable).toBe(true);
  });

  it("classifies version-mismatch with sync-runtime action", () => {
    const result = classifyError("version-mismatch");
    expect(result.type).toBe("version_mismatch");
    expect(result.recoverable).toBe(true);
    expect(result.action).toBe("sync-runtime");
  });

  it("classifies pip-failed as pip_install_failure", () => {
    const result = classifyError("pip-failed");
    expect(result.type).toBe("pip_install_failure");
    expect(result.recoverable).toBe(true);
  });

  it("classifies ETIMEDOUT as timeout with retry action", () => {
    const result = classifyError("ETIMEDOUT");
    expect(result.type).toBe("timeout");
    expect(result.recoverable).toBe(true);
    expect(result.action).toBe("retry");
  });

  it("classifies NO_PYTHON as no_python with open-setup action", () => {
    const result = classifyError("NO_PYTHON");
    expect(result.type).toBe("no_python");
    expect(result.recoverable).toBe(true);
    expect(result.action).toBe("open-setup");
  });

  it("classifies VECTOR_NOT_BUILT as vectors_not_built with open-vector-settings action", () => {
    const result = classifyError("VECTOR_NOT_BUILT");
    expect(result.type).toBe("vectors_not_built");
    expect(result.recoverable).toBe(true);
    expect(result.action).toBe("open-vector-settings");
  });

  it("classifies VECTOR_CORRUPTED as vectors_corrupted with force-rebuild action", () => {
    const result = classifyError("VECTOR_CORRUPTED");
    expect(result.type).toBe("vectors_corrupted");
    expect(result.recoverable).toBe(true);
    expect(result.action).toBe("force-rebuild");
  });

  it("classifies MODEL_CHANGED as model_changed with rebuild-vectors action", () => {
    const result = classifyError("MODEL_CHANGED");
    expect(result.type).toBe("model_changed");
    expect(result.recoverable).toBe(true);
    expect(result.action).toBe("rebuild-vectors");
  });

  it("classifies BACKEND_UNAVAILABLE as backend_unavailable with run-doctor action", () => {
    const result = classifyError("BACKEND_UNAVAILABLE");
    expect(result.type).toBe("backend_unavailable");
    expect(result.recoverable).toBe(true);
    expect(result.action).toBe("run-doctor");
  });

  it("classifies TIMEOUT as timeout with retry action", () => {
    const result = classifyError("TIMEOUT");
    expect(result.type).toBe("timeout");
    expect(result.recoverable).toBe(true);
    expect(result.action).toBe("retry");
    expect(result.message).toContain("Search");
  });

  it("classifies INTERNAL_ERROR as internal_error not recoverable", () => {
    const result = classifyError("INTERNAL_ERROR");
    expect(result.type).toBe("internal_error");
    expect(result.recoverable).toBe(false);
  });
  it("classifies unknown error strings as unknown", () => {
    const result = classifyError("SOME_RANDOM_ERROR");
    expect(result.type).toBe("unknown");
    expect(result.recoverable).toBe(false);
    expect(result.message).toBe("SOME_RANDOM_ERROR");
  });

  it("classifies numeric exit codes as unknown", () => {
    const result = classifyError(1);
    expect(result.type).toBe("unknown");
    expect(result.recoverable).toBe(false);
  });
});

describe("classifySetupFailure (#257)", () => {
  it("reuses the exact-code table first", () => {
    const result = classifySetupFailure("ETIMEDOUT");
    expect(result.type).toBe("timeout");
    expect(result.action).toBe("retry");
  });

  it("classifies pip network failures as network", () => {
    const result = classifySetupFailure(
      "pip install failed: Command failed — Could not fetch URL: Read timed out."
    );
    expect(result.type).toBe("network");
    expect(result.action).toBe("retry-network");
  });

  it("classifies an unpublished version as artifact_unavailable", () => {
    const result = classifySetupFailure(
      "pip install failed: ERROR: Could not find a version that satisfies the requirement paperforge[vector]==9.9.9"
    );
    expect(result.type).toBe("artifact_unavailable");
    expect(result.action).toBe("check-release");
  });

  it("classifies disk/permission/process conditions", () => {
    expect(classifySetupFailure("OSError: No space left on device").type).toBe(
      "disk_full"
    );
    expect(
      classifySetupFailure("pip install failed: Permission denied: venv").type
    ).toBe("permission_denied");
    expect(
      classifySetupFailure(
        "The previous runtime directory could not be removed (WinError 32). Close any running PaperForge process and try again."
      ).type
    ).toBe("process_busy");
  });

  it("classifies version/handshake and missing-python messages", () => {
    expect(
      classifySetupFailure("version mismatch: observed 1.2.0 != expected 2.0.0")
        .type
    ).toBe("version_mismatch");
    expect(classifySetupFailure("interpreter missing").type).toBe("no_python");
  });

  it("falls back to unknown without a pattern match", () => {
    const result = classifySetupFailure("something entirely new happened");
    expect(result.type).toBe("unknown");
    expect(result.recoverable).toBe(false);
  });
});
