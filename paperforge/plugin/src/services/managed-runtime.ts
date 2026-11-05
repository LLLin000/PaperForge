import * as fs from "fs";
import * as os from "os";
import * as path from "path";

export interface PointerInfo {
  readonly pythonPath: string;
  readonly environmentRoot: string;
  readonly paperforgeVersion: string;
}

export interface RuntimeRun {
  readonly command: string;
  readonly args: readonly string[];
}

/** Read the Python-owned schema-v1 pointer. Never creates or changes runtime state. */
export function readRuntimePointer(home = os.homedir()): PointerInfo | null {
  const pointerPath = path.join(
    home,
    ".paperforge",
    "runtime",
    "pointer.json"
  );
  let raw: unknown;
  try {
    raw = JSON.parse(fs.readFileSync(pointerPath, "utf8"));
  } catch {
    return null;
  }
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;

  const pointer = raw as Record<string, unknown>;
  const pythonPath = pointer.python_path;
  const environmentRoot = pointer.environment_root;
  const paperforgeVersion = pointer.paperforge_version;
  if (
    pointer.schema_version !== 1 ||
    typeof pythonPath !== "string" ||
    typeof environmentRoot !== "string" ||
    typeof paperforgeVersion !== "string" ||
    !pythonPath ||
    !environmentRoot ||
    !paperforgeVersion ||
    !path.isAbsolute(pythonPath) ||
    !path.isAbsolute(environmentRoot)
  ) {
    return null;
  }
  return { pythonPath, environmentRoot, paperforgeVersion };
}

export function resolveRuntimeCommand(
  pointer: PointerInfo | null
): RuntimeRun | null {
  return pointer ? { command: pointer.pythonPath, args: [] } : null;
}
