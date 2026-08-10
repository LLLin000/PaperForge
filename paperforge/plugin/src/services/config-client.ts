/**
 * Config client (#172 / C0) — typed transport for the canonical config
 * authority.  The plugin NEVER parses or writes paperforge.json; every read
 * and mutation routes through `paperforge config <verb> --json`.
 *
 * This is the minimal config surface C0 introduces; the full typed
 * PaperForgeClient (probe/action/detail methods) lands with R (#161).
 */

import { execFile } from "child_process";
import { resolvePythonExecutable } from "./python-bridge";
import type { PaperForgeSettings } from "../constants";

export interface ConfigField {
  key: string;
  value: string | boolean;
  stored_value: string | boolean | null;
  source: "default" | "file" | "environment" | "override";
  is_set: boolean;
  type: string;
  default: string | boolean;
  environment: string | null;
  choices: string[];
  writable: boolean;
  allow_empty: boolean;
  vault_relative: boolean;
}

export interface ConfigListData {
  schema_version: number;
  revision: string;
  unknown_keys: string[];
  fields: ConfigField[];
}

export interface ConfigMutationData {
  schema_version: number;
  revision: string;
  unknown_keys: string[];
  changed: boolean;
  field: ConfigField;
  warnings?: string[];
}

export interface ConfigPathsData {
  revision: string;
  paths: Record<string, string>;
}

export interface ConfigValidateData {
  state: string;
  revision: string | null;
  errors: Array<Record<string, unknown>>;
  warnings: Array<Record<string, unknown>>;
  migration: Record<string, unknown> | null;
}

interface PfResult<T> {
  ok: boolean;
  command: string;
  data: T | null;
  error: { code: string; message: string; details: Record<string, unknown> } | null;
}

export class ConfigClientError extends Error {
  readonly configCode: string;
  readonly details: Record<string, unknown>;

  constructor(configCode: string, details: Record<string, unknown>, message?: string) {
    super(message ?? configCode);
    this.configCode = configCode;
    this.details = details;
  }
}

function invoke<T>(
  vaultPath: string,
  args: string[],
  settings: PaperForgeSettings | null | undefined
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const py = resolvePythonExecutable(vaultPath, settings, require("fs"), require("child_process").execFileSync);
    if (!py) {
      reject(new ConfigClientError("config.python_unresolved", {}));
      return;
    }
    const argv = [
      ...py.extraArgs,
      "-m",
      "paperforge",
      "--vault",
      vaultPath,
      "config",
      ...args,
      "--json",
    ];
    execFile(
      py.path,
      argv,
      { encoding: "utf-8", timeout: 30000, windowsHide: true },
      (err, stdout) => {
        // #137 machine contract: --json emits exactly one PFResult JSON on
        // stdout (success OR failure); stderr is diagnostics only.
        try {
          const parsed = JSON.parse(stdout) as PfResult<T>;
          if (parsed.ok && parsed.data !== null) {
            resolve(parsed.data);
            return;
          }
          const code = parsed.error?.message || parsed.error?.code || "config.error";
          reject(
            new ConfigClientError(
              code,
              parsed.error?.details ?? {},
              parsed.error?.message ?? code
            )
          );
          return;
        } catch (parseError) {
          const diag = err?.message ?? "";
          reject(
            new ConfigClientError(
              "config.invalid_response",
              { stdout: stdout?.slice(0, 200) ?? "", stderr: diag?.slice(0, 200) ?? "" },
              `Invalid config response: ${String(parseError)}`
            )
          );
        }
      }
    );
  });
}

export function configList(
  vaultPath: string,
  settings?: PaperForgeSettings | null
): Promise<ConfigListData> {
  return invoke<ConfigListData>(vaultPath, ["list"], settings);
}

export function configGet(
  vaultPath: string,
  key: string,
  settings?: PaperForgeSettings | null
): Promise<ConfigField> {
  return invoke<{ field: ConfigField }>(vaultPath, ["get", key], settings).then((d) => d.field);
}

export function configSet(
  vaultPath: string,
  key: string,
  value: string | boolean,
  settings?: PaperForgeSettings | null
): Promise<ConfigMutationData> {
  return invoke<ConfigMutationData>(vaultPath, ["set", key, String(value)], settings);
}

export function configUnset(
  vaultPath: string,
  key: string,
  settings?: PaperForgeSettings | null
): Promise<ConfigMutationData> {
  return invoke<ConfigMutationData>(vaultPath, ["unset", key], settings);
}

export function configPaths(
  vaultPath: string,
  settings?: PaperForgeSettings | null
): Promise<ConfigPathsData> {
  return invoke<ConfigPathsData>(vaultPath, ["paths"], settings);
}

export function configValidate(
  vaultPath: string,
  settings?: PaperForgeSettings | null
): Promise<ConfigValidateData> {
  return invoke<ConfigValidateData>(vaultPath, ["validate"], settings);
}

export function configMigrate(
  vaultPath: string,
  dryRun: boolean,
  settings?: PaperForgeSettings | null
): Promise<ConfigMutationData> {
  return invoke<ConfigMutationData>(
    vaultPath,
    dryRun ? ["migrate", "--dry-run"] : ["migrate"],
    settings
  );
}

// ── Read-model detail queries (#161 / R) ────────────────────────────────
// Typed wrappers over existing detail commands; the plugin never parses
// canonical files for these facts.

export function queryMemoryDetail(
  vaultPath: string,
  settings?: PaperForgeSettings | null
): Promise<Record<string, unknown>> {
  return invoke<Record<string, unknown>>(vaultPath, ["memory", "status"], settings);
}

export function queryEmbedStatus(
  vaultPath: string,
  settings?: PaperForgeSettings | null
): Promise<Record<string, unknown>> {
  return invoke<Record<string, unknown>>(vaultPath, ["embed", "status"], settings);
}

export function queryOcrPapers(
  vaultPath: string,
  settings?: PaperForgeSettings | null
): Promise<Record<string, unknown>> {
  return invoke<Record<string, unknown>>(vaultPath, ["ocr", "list"], settings);
}

export function paperContext(
  vaultPath: string,
  key: string,
  settings?: PaperForgeSettings | null
): Promise<Record<string, unknown>> {
  return invoke<Record<string, unknown>>(vaultPath, ["paper-context", key], settings);
}

export function probeAll(
  vaultPath: string,
  settings?: PaperForgeSettings | null
): Promise<Record<string, unknown>> {
  return invoke<Record<string, unknown>>(vaultPath, ["probe", "all"], settings);
}
