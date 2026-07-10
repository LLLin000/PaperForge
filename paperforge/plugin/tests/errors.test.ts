import { describe, it, expect } from "vitest";

import {
  classifyError,
  parseRuntimeStatus,
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

describe("parseRuntimeStatus", () => {
  it("returns ok with version on success", () => {
    const result = parseRuntimeStatus(null, "1.4.17rc3\n", "");
    expect(result.status).toBe("ok");
    expect(result.version).toBe("1.4.17rc3");
  });

  it("classifies ENOENT as python_missing", () => {
    const err = new Error("spawn ENOENT");
    err.code = "ENOENT";
    const result = parseRuntimeStatus(err, null, "");
    expect(result.status).toBe("error");
    expect(result.type).toBe("python_missing");
  });

  it("classifies ModuleNotFoundError in stderr as import_failed", () => {
    const result = parseRuntimeStatus(
      new Error("fail"),
      null,
      "No module named paperforge"
    );
    expect(result.status).toBe("error");
    expect(result.type).toBe("import_failed");
  });

  it("classifies killed/timeout subprocess as timeout", () => {
    const err = new Error("timeout");
    err.killed = true;
    const result = parseRuntimeStatus(err, null, "");
    expect(result.status).toBe("error");
    expect(result.type).toBe("timeout");
  });

  it("classifies generic error as unknown", () => {
    const err = new Error("Something went wrong");
    const result = parseRuntimeStatus(err, null, "some output");
    expect(result.status).toBe("error");
    expect(result.type).toBe("unknown");
  });
});
