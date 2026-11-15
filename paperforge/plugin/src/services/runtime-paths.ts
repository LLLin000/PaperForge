/**
 * Runtime path projection (#161 / R).
 *
 * #142/#148: the plugin never parses paperforge.json and never guesses
 * canonical paths. Path VALUES are hydrated from Python (`config list` /
 * `config paths` by main.ts); this module only projects them into the
 * ResolvedPaths shape UI code consumes. Fail-closed: no hydration -> empty
 * paths and no semantic work may run (actions stay disabled per #144).
 *
 * The snapshot-reading semantics of the old memory-state.ts are deleted with
 * the snapshot contract (#148 zero readers / zero writers).
 */

import * as path from "path";
import type { PaperForgeSettings } from "../constants";
import type { ConfigField } from "../client/paperforge-client";

export interface PathConfig {
  system_dir: string;
  resources_dir: string;
  literature_dir: string;
  base_dir: string;
  _warning: string | null;
}

export interface ResolvedPaths {
  vault: string;
  systemDir: string;
  indexesDir: string;
  logsDir: string;
  dbPath: string;
  orphanStatePath: string;
  exportsDir: string;
  ocrDir: string;
  configWarning: string | null;
}

let _pathConfigSource: PathConfig | null = null;

export function setPathConfigSource(cfg: PathConfig | null): void {
  _pathConfigSource = cfg;
}

/** Refresh both UI mirrors and path consumers from the same Python readback. */
export function applyPathConfigFromList(
  settings: Pick<
    PaperForgeSettings,
    "system_dir" | "resources_dir" | "literature_dir" | "base_dir" | "zotero_data_dir"
  >,
  fields: ReadonlyArray<Pick<ConfigField, "key" | "value">>
): void {
  const value = (key: string) =>
    String(fields.find((field) => field.key === key)?.value ?? "");
  const paths = {
    system_dir: value("system_dir"),
    resources_dir: value("resources_dir"),
    literature_dir: value("literature_dir"),
    base_dir: value("base_dir"),
  };
  if (Object.values(paths).some((value) => !value.trim())) {
    throw new Error("Incomplete canonical vault paths");
  }
  Object.assign(settings, paths, { zotero_data_dir: value("zotero_data_dir") });
  setPathConfigSource({ ...paths, _warning: null });
}

export function isConfigHydrated(): boolean {
  return _pathConfigSource !== null;
}

export function readPathConfig(vaultPath: string, _fs?: unknown): PathConfig {
  if (_pathConfigSource) {
    return { ..._pathConfigSource, _warning: _pathConfigSource._warning ?? null };
  }
  return {
    system_dir: "",
    resources_dir: "",
    literature_dir: "",
    base_dir: "",
    _warning: "config authority not hydrated; paths unavailable — no semantic work may run",
  };
}

export function resolveVaultPaths(vaultPath: string, _fs?: unknown): ResolvedPaths {
  const cfg = readPathConfig(vaultPath, _fs);
  const systemDir = path.join(vaultPath, cfg.system_dir, "PaperForge");
  return {
    vault: vaultPath,
    systemDir,
    indexesDir: path.join(systemDir, "indexes"),
    logsDir: path.join(systemDir, "logs"),
    dbPath: path.join(systemDir, "indexes", "paperforge.db"),
    orphanStatePath: path.join(systemDir, "indexes", "sync-orphan-state.json"),
    exportsDir: path.join(systemDir, "exports"),
    ocrDir: path.join(systemDir, "ocr"),
    configWarning: cfg._warning,
  };
}
