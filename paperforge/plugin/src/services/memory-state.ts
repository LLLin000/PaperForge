import * as fs from "fs";
import * as path from "path";
import { execFileSync } from "child_process";
import type { PaperForgeSettings } from "../constants";

// ── Types ──

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
  memoryStatePath: string;
  vectorStatePath: string;
  healthStatePath: string;
  buildStatePath: string;
  orphanStatePath: string;
  exportsDir: string;
  ocrDir: string;
  pluginDataPath: string;
  pfJsonPath: string;
  configWarning: string | null;
}

export interface MemoryRuntime {
  paper_count_db?: number;
  needs_rebuild?: boolean;
  fresh?: boolean;
  updated_at?: string;
  [key: string]: unknown;
}

export interface VectorRuntime {
  enabled?: boolean;
  deps_installed?: boolean;
  db_exists?: boolean;
  healthy?: boolean | null;
  chunk_count?: number;
  model?: string;
  mode?: string;
  updated_at?: string;
  [key: string]: unknown;
}

export interface PythonResult {
  path: string;
  source: "manual" | "auto-detected";
  extraArgs: string[];
}

export interface Snapshot {
  memory: MemoryRuntime | null;
  vector: VectorRuntime | null;
  health: Record<string, unknown> | null;
  updatedAt: string;
  summary: {
    status: string;
    memoryReady: boolean;
    vectorReady: boolean;
    healthOk: boolean;
  };
}

// ── Module-level closure state ──

let _cachedPython: PythonResult | null = null;

// ── Functions ──

export function readPathConfig(vaultPath: string): PathConfig {
  const pfPath = path.join(vaultPath, 'paperforge.json');
  const defaults = {
    system_dir: 'System',
    resources_dir: 'Resources',
    literature_dir: 'Literature',
    base_dir: 'Bases',
  };

  try {
    if (!fs.existsSync(pfPath)) {
      return { ...defaults, _warning: 'paperforge.json not found; using defaults' };
    }
    const raw = fs.readFileSync(pfPath, 'utf-8');
    const data = JSON.parse(raw);
    const vc = data.vault_config || {};
    return {
      system_dir: vc.system_dir || data.system_dir || defaults.system_dir,
      resources_dir: vc.resources_dir || data.resources_dir || defaults.resources_dir,
      literature_dir: vc.literature_dir || data.literature_dir || defaults.literature_dir,
      base_dir: vc.base_dir || data.base_dir || defaults.base_dir,
      _warning: null,
    };
  } catch (e) {
    console.warn('PaperForge: Failed to read paperforge.json, using defaults', e);
    return { ...defaults, _warning: 'paperforge.json invalid; using defaults' };
  }
}

export function resolveVaultPaths(vaultPath: string): ResolvedPaths {
  const cfg = readPathConfig(vaultPath);
  const systemDir = path.join(vaultPath, cfg.system_dir, 'PaperForge');
  return {
    vault: vaultPath,
    systemDir,
    indexesDir: path.join(systemDir, 'indexes'),
    logsDir: path.join(systemDir, 'logs'),
    dbPath: path.join(systemDir, 'indexes', 'paperforge.db'),
    memoryStatePath: path.join(systemDir, 'indexes', 'memory-runtime-state.json'),
    vectorStatePath: path.join(systemDir, 'indexes', 'vector-runtime-state.json'),
    healthStatePath: path.join(systemDir, 'indexes', 'runtime-health.json'),
    buildStatePath: path.join(systemDir, 'indexes', 'vector-build-state.json'),
    orphanStatePath: path.join(systemDir, 'indexes', 'sync-orphan-state.json'),
    exportsDir: path.join(systemDir, 'exports'),
    ocrDir: path.join(systemDir, 'ocr'),
    pluginDataPath: path.join(vaultPath, '.obsidian', 'plugins', 'paperforge', 'data.json'),
    pfJsonPath: path.join(vaultPath, 'paperforge.json'),
    configWarning: cfg._warning,
  };
}

export function readJSONFile(filePath: string): Record<string, unknown> | null {
  try {
    if (!fs.existsSync(filePath)) return null;
    return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
  } catch (_) { return null; }
}

export function getMemoryRuntime(vaultPath: string): MemoryRuntime | null {
  const paths = resolveVaultPaths(vaultPath);
  return readJSONFile(paths.memoryStatePath) as MemoryRuntime | null;
}

export function getVectorRuntime(vaultPath: string): VectorRuntime | null {
  const paths = resolveVaultPaths(vaultPath);
  return readJSONFile(paths.vectorStatePath) as VectorRuntime | null;
}

export function getRuntimeHealth(vaultPath: string): Record<string, unknown> | null {
  const paths = resolveVaultPaths(vaultPath);
  return readJSONFile(paths.healthStatePath);
}

export function isMemoryReady(vaultPath: string): boolean {
  const s = getMemoryRuntime(vaultPath);
  return !!(s && (s.paper_count_db ?? 0) > 0 && !s.needs_rebuild);
}

export function isVectorReady(vaultPath: string): boolean {
  const s = getVectorRuntime(vaultPath);
  if (!s) return false;
  if (!s.enabled) return false;
  if (!s.deps_installed) return false;
  if (!s.db_exists) return false;
  if (s.healthy === false) return false;
  if (s.chunk_count === 0) return false;
  return true;
}

export function isHealthOk(vaultPath: string): boolean {
  const s = getRuntimeHealth(vaultPath);
  return !!(s && (s.summary as { status?: string })?.status === 'ok');
}

export function getMemoryStatusText(vaultPath: string): string {
  const s = getMemoryRuntime(vaultPath);
  if (!s || s.paper_count_db === 0) return 'DB not found. Run paperforge memory build.';
  return 'Papers: ' + s.paper_count_db + ' | ' + (s.fresh ? 'fresh' : 'stale');
}

export function getVectorStatusText(vaultPath: string): string {
  const s = getVectorRuntime(vaultPath);
  if (!s) return 'Status unavailable';
  if (s.healthy === false) return 'Vector index unreadable - rebuild required';
  return 'Chunks: ' + s.chunk_count + ' | ' + s.model + ' | ' + s.mode;
}

export function getCachedPython(vaultPath: string, settings: PaperForgeSettings): PythonResult {
  if (_cachedPython) return _cachedPython;
  if (settings && settings.python_path && settings.python_path.trim()) {
    const p = settings.python_path.trim();
    if (fs.existsSync(p)) { _cachedPython = { path: p, source: 'manual', extraArgs: [] }; return _cachedPython; }
  }
  const venvCandidates = [
    path.join(vaultPath, '.paperforge-test-venv', 'Scripts', 'python.exe'),
    path.join(vaultPath, '.venv', 'Scripts', 'python.exe'),
    path.join(vaultPath, 'venv', 'Scripts', 'python.exe'),
  ];
  for (let i = 0; i < venvCandidates.length; i++) {
    if (fs.existsSync(venvCandidates[i])) {
      _cachedPython = { path: venvCandidates[i], source: 'auto-detected', extraArgs: [] };
      return _cachedPython;
    }
  }
  const sysCandidates = [{path:'py',extraArgs:['-3']},{path:'python',extraArgs:[]},{path:'python3',extraArgs:[]}];
  for (let j = 0; j < sysCandidates.length; j++) {
    try {
      const c = sysCandidates[j];
      const out = execFileSync(c.path, c.extraArgs.concat(['--version']), {encoding:'utf-8',timeout:5000,windowsHide:true});
      if (out && out.toLowerCase().indexOf('python') !== -1) {
        _cachedPython = { path: c.path, source: 'auto-detected', extraArgs: c.extraArgs };
        return _cachedPython;
      }
    } catch (_) {}
  }
  _cachedPython = { path: 'python', source: 'auto-detected', extraArgs: [] };
  return _cachedPython;
}

export function buildSnapshot(
  vaultPath: string,
  _readFn?: (filePath: string) => Record<string, unknown> | null,
  _resolvePaths?: (vaultPath: string) => ResolvedPaths,
): Snapshot {
  const readFn = _readFn || readJSONFile;
  const resolvePaths = _resolvePaths || resolveVaultPaths;
  const paths = resolvePaths(vaultPath);
  const memory = readFn(paths.memoryStatePath) as MemoryRuntime | null;
  const vector = readFn(paths.vectorStatePath) as VectorRuntime | null;
  const health = readFn(paths.healthStatePath);
  const memoryOk = !!(memory && (memory.paper_count_db ?? 0) > 0 && !memory.needs_rebuild);
  const vectorOk = !!(vector && vector.enabled && vector.deps_installed && vector.db_exists && (vector.chunk_count ?? 0) > 0);
  return {
    memory: memory, vector: vector, health: health,
    updatedAt: (memory && memory.updated_at) || (vector && vector.updated_at) || '',
    summary: {
      status: memoryOk && vectorOk ? 'ready' : 'degraded',
      memoryReady: memoryOk, vectorReady: vectorOk,
      healthOk: !!(health && (health.summary as { status?: string })?.status === 'ok'),
    },
  };
}

export function shouldRenderVectorReady(vectorDepsOk: boolean | null, embedStatusText: string): boolean {
  return vectorDepsOk === true;
}
