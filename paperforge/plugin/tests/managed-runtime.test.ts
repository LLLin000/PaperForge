import { afterEach, beforeEach, describe, expect, it } from "vitest";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import {
  readRuntimePointer,
  resolveRuntimeCommand,
} from "../src/services/managed-runtime";

let home: string;

beforeEach(() => {
  home = fs.mkdtempSync(path.join(os.tmpdir(), "paperforge-runtime-pointer-"));
});

afterEach(() => {
  fs.rmSync(home, { recursive: true, force: true });
});

function writePointer(value: unknown): void {
  const runtimeDir = path.join(home, ".paperforge", "runtime");
  fs.mkdirSync(runtimeDir, { recursive: true });
  fs.writeFileSync(
    path.join(runtimeDir, "pointer.json"),
    JSON.stringify(value),
    "utf8"
  );
}

function validPointer(): Record<string, unknown> {
  return {
    schema_version: 1,
    python_path: path.join(home, "runtime", "python"),
    environment_root: path.join(home, "runtime"),
    paperforge_version: "1.5.15",
  };
}

describe("read-only runtime pointer", () => {
  it("reads the Python-published schema and resolves only its interpreter", () => {
    const raw = validPointer();
    writePointer({ ...raw, additive_field: "ignored" });

    const pointer = readRuntimePointer(home);

    expect(pointer).toEqual({
      pythonPath: raw.python_path,
      environmentRoot: raw.environment_root,
      paperforgeVersion: raw.paperforge_version,
    });
    expect(resolveRuntimeCommand(pointer)).toEqual({
      command: raw.python_path,
      args: [],
    });
  });

  it("fails closed for missing, unsupported, incomplete, or relative pointers", () => {
    expect(readRuntimePointer(home)).toBeNull();

    writePointer({ ...validPointer(), schema_version: 2 });
    expect(readRuntimePointer(home)).toBeNull();

    writePointer({ schema_version: 1, python_path: "python" });
    expect(readRuntimePointer(home)).toBeNull();

    writePointer({ ...validPointer(), python_path: "python" });
    expect(readRuntimePointer(home)).toBeNull();
    expect(resolveRuntimeCommand(null)).toBeNull();
  });
});
