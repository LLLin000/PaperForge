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

function invoke<T>(
  vaultPath: string,
  args: string[],
  settings: PaperForgeSettings | null | undefined
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const py = resolvePythonExecutable(vaultPath, settings, require("fs"), require("child_process").execFileSync);
    if (!py) {
      reject(new Error("PaperForge Python runtime not resolved"));
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
      (err, stdout, stderr) => {
        if (err) {
          reject(new Error(stderr?.trim() || err.message));
          return;
        }
        try {
          const parsed = JSON.parse(stdout) as PfResult<T>;
          if (!parsed.ok || parsed.data === null) {
            const code = parsed.error?.message || parsed.error?.code || "config.error";
            reject(new Error(code));
            return;
          }
          resolve(parsed.data);
        } catch (e) {
          reject(new Error(`Invalid config response: ${String(e)}`));
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
