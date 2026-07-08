# Plugin TypeScript Source Migration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate 4977-line monolithic `main.js` to a modular TypeScript source tree under `src/`, bundled into `main.js` via esbuild, matching Obsidian community plugin conventions.

**Architecture:** Extract 9 focused modules from the monolith — services (memory-state, python-bridge), views (dashboard, settings, modals), i18n, constants, utils — each a standalone `.ts` file. Rewrite `main.ts` as a thin ~80-line lifecycle entry that imports from the extracted modules. Build with esbuild > CJS bundle at `main.js`. Migrate all 5 vitest test files from `.mjs` to `.ts`.

**Tech Stack:** TypeScript 5.x, esbuild 0.25.x, vitest 2.x (jsdom), obsidian npm types

**Source of truth:** This worktree: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\plugin-ts-migration`

---

## File Map

```
paperforge/plugin/
├── main.js                      # [GENERATED] CJS bundle ← esbuild output
├── main.js.bak                  # [ONCE] Backup of original main.js before deletion
├── manifest.json                # [KEEP] Unchanged
├── styles.css                   # [KEEP] Unchanged (2591 lines CSS)
├── package.json                 # [MODIFY] Add esbuild, typescript, @types/node; add scripts
├── tsconfig.json                # [CREATE] TypeScript config
├── esbuild.config.mjs           # [CREATE] Build script
├── vitest.config.ts             # [MODIFY] Match .ts test files
├── versions.json                # [KEEP] Unchanged
├── src/                         # [RESTRUCTURE] Source tree
│   ├── main.ts                  # [CREATE] Thin plugin lifecycle entry (~80 lines)
│   ├── constants.ts             # [CREATE] ACTIONS, DEFAULT_SETTINGS, view type, icon SVG
│   ├── i18n.ts                  # [CREATE] Language pack (zh/en)
│   ├── settings.ts              # [CREATE] PaperForgeSettingTab (~1250 lines)
│   ├── views/
│   │   ├── dashboard.ts         # [CREATE] PaperForgeStatusView (~1660 lines)
│   │   └── modals.ts            # [CREATE] OCR privacy, orphan, setup modals + checkOrphanState (~790 lines)
│   ├── services/
│   │   ├── memory-state.ts      # [CREATE] Path config + runtime state readers (~200 lines)
│   │   └── python-bridge.ts     # [CREATE] Python detection, version check, subprocess, BBT (~500 lines)
│   └── utils/
│       └── disclosure.ts        # [CREATE] Disclosure state toggle (~20 lines)
├── tests/                       # [MIGRATE] .mjs → .ts
│   ├── commands.test.ts         # [MIGRATE] from commands.test.mjs
│   ├── errors.test.ts           # [MIGRATE] from errors.test.mjs
│   ├── runtime.test.ts          # [MIGRATE] from runtime.test.mjs
│   ├── settings-panels.test.ts  # [MIGRATE] from settings-panels.test.mjs
│   └── vector-ready.test.ts     # [MIGRATE] from vector-ready.test.mjs
└── src/testable.js              # [DELETE] Absorbed into typed modules
```

---

## Phase 1: Build System Scaffold

### Task 1: Install TypeScript + esbuild dependencies

**Files:**
- Modify: `paperforge/plugin/package.json`

- [ ] **Step 1: Add devDependencies and scripts**

```json
{
  "name": "paperforge-plugin",
  "version": "1.0.0",
  "private": true,
  "type": "commonjs",
  "scripts": {
    "dev": "node esbuild.config.mjs",
    "build": "tsc -noEmit -skipLibCheck && node esbuild.config.mjs production",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "devDependencies": {
    "vitest": "^2.1.0",
    "obsidian-test-mocks": "^2.0.0",
    "jsdom": "^25.0.0",
    "obsidian": "^1.12.0",
    "typescript": "^5.4.0",
    "esbuild": "^0.25.0",
    "builtin-modules": "^3.3.0",
    "@types/node": "^20.0.0"
  }
}
```

- [ ] **Step 2: Run npm install**

```bash
npm install
```
Expected: packages install cleanly, no errors.

- [ ] **Step 3: Commit**

```bash
git add paperforge/plugin/package.json paperforge/plugin/package-lock.json
git commit -m "chore(plugin): add esbuild, typescript, @types/node devDeps"
```

---

### Task 2: Create tsconfig.json

**Files:**
- Create: `paperforge/plugin/tsconfig.json`

- [ ] **Step 1: Write tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2018",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noEmit": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    },
    "lib": ["ES2018", "DOM"]
  },
  "include": ["src/**/*.ts", "tests/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 2: Verify config is valid**

```bash
npx tsc --noEmit --skipLibCheck
```
Expected: "No inputs were found in config file" (no .ts files yet — this is expected).

- [ ] **Step 3: Commit**

```bash
git add paperforge/plugin/tsconfig.json
git commit -m "chore(plugin): add tsconfig.json"
```

---

### Task 3: Create esbuild.config.mjs

**Files:**
- Create: `paperforge/plugin/esbuild.config.mjs`

- [ ] **Step 1: Write esbuild.config.mjs**

```js
import esbuild from "esbuild";
import builtins from "builtin-modules";

const prod = process.argv[2] === "production";

await esbuild.build({
  entryPoints: ["src/main.ts"],
  bundle: true,
  external: [
    "obsidian",
    "electron",
    "@codemirror/autocomplete",
    "@codemirror/collab",
    "@codemirror/commands",
    "@codemirror/language",
    "@codemirror/lint",
    "@codemirror/search",
    "@codemirror/state",
    "@codemirror/view",
    "@lezer/common",
    "@lezer/highlight",
    "@lezer/lr",
    ...builtins,
  ],
  format: "cjs",
  target: "es2018",
  logLevel: "info",
  sourcemap: prod ? false : "inline",
  treeShaking: true,
  outfile: "main.js",
  minify: prod,
});
```

- [ ] **Step 2: Verify esbuild runs (will fail — no src/main.ts yet)**

```bash
node esbuild.config.mjs
```
Expected: Fails with "Could not resolve entry point" — correct at this stage.

- [ ] **Step 3: Commit**

```bash
git add paperforge/plugin/esbuild.config.mjs
git commit -m "chore(plugin): add esbuild.config.mjs"
```

---

## Phase 2: Extract Core Services & Utilities

### Task 4: Create `src/utils/disclosure.ts`

**Files:**
- Create: `paperforge/plugin/src/utils/disclosure.ts`

Source: `main.js` lines 407-420 (getDisclosureState, toggleDisclosureState)

- [ ] **Step 1: Write the module**

```typescript
/**
 * Disclosure state management for collapsible sections.
 * Store is an arbitrary object (e.g., plugin.settings).
 */
export function getDisclosureState(
  store: Record<string, unknown> | null | undefined,
  key: string,
  defaultCollapsed: boolean
): boolean {
  if (!store || typeof store !== "object") return !!defaultCollapsed;
  if (!Object.prototype.hasOwnProperty.call(store, key)) return !!defaultCollapsed;
  return !!store[key];
}

export function toggleDisclosureState(
  store: Record<string, unknown> | null | undefined,
  key: string,
  defaultCollapsed: boolean
): boolean {
  const next = !getDisclosureState(store, key, defaultCollapsed);
  if (store && typeof store === "object") {
    store[key] = next;
  }
  return next;
}
```

- [ ] **Step 2: Commit**

```bash
git add paperforge/plugin/src/utils/disclosure.ts
git commit -m "feat(plugin): extract disclosure utils to src/utils/disclosure.ts"
```

---

### Task 5: Create `src/constants.ts`

**Files:**
- Create: `paperforge/plugin/src/constants.ts`

Source: `main.js` lines 336-371 (ACTIONS), 591-599 (VIEW_TYPE, PF_ICON_ID, PF_RIBBON_SVG), 907-929 (DEFAULT_SETTINGS), and workflow state helpers (lines 930-946)

- [ ] **Step 1: Write the module**

```typescript
export const VIEW_TYPE_PAPERFORGE = "paperforge-status";
export const PF_ICON_ID = "paperforge";
export const PF_RIBBON_SVG = `
<svg ...><!-- exact SVG from main.js line 593-600 --></svg>`;

export interface ActionDef {
  id: string;
  title: string;
  desc?: string;
  icon?: string;
  cmd: string;
  args?: string[];
  needsKey?: boolean;
  needsFilter?: boolean;
  okMsg?: string;
  disabled?: boolean;
  disabledMsg?: string;
}

export const ACTIONS: ActionDef[] = [
  {
    id: "paperforge-sync",
    title: "Sync Library",
    desc: "Pull new references from Zotero and generate literature notes",
    icon: "\u21BB",
    cmd: "sync",
    okMsg: "Sync complete",
  },
  {
    id: "paperforge-ocr",
    title: "Run OCR",
    desc: "Extract full text and figures from PDFs via PaddleOCR",
    icon: "\u229E",
    cmd: "ocr",
    okMsg: "OCR started",
  },
  {
    id: "paperforge-doctor",
    title: "Run Doctor",
    desc: "Verify PaperForge setup \u2014 check configs, Zotero, paths, and index health",
    icon: "\u2695",
    cmd: "doctor",
    okMsg: "Doctor complete",
  },
  {
    id: "paperforge-repair",
    title: "Repair Issues",
    desc: "Fix three-way state divergence, path errors, and rebuild index",
    icon: "\u21BA",
    cmd: "repair",
    args: ["--fix", "--fix-paths"],
    okMsg: "Repair complete",
  },
];

export interface PaperForgeSettings {
  python_path: string;
  setup_complete: boolean;
  auto_update_on_startup: boolean;
  features: Record<string, boolean>;
  frozen_skills: Record<string, string>;
  system_dir: string;
  resources_dir: string;
  literature_dir: string;
  base_dir: string;
  _python_path_stale?: boolean;
  [key: string]: unknown;
}

export const DEFAULT_SETTINGS: PaperForgeSettings = {
  python_path: "",
  setup_complete: false,
  auto_update_on_startup: true,
  features: {
    // Exact keys from main.js lines 915-928
  },
  frozen_skills: {},
  system_dir: "System",
  resources_dir: "Resources",
  literature_dir: "Literature",
  base_dir: "Bases",
};

// Workflow state helpers — main.js lines 930-946
export interface WorkflowState {
  // ... fields from overlayEntryWorkflowState
}

export function overlayEntryWorkflowState(
  app: unknown,
  entry: unknown
): WorkflowState {
  // ... exact logic from main.js lines 930-943
}

export function patchEntryWorkflowState(
  entry: unknown,
  patch: Partial<WorkflowState>
): void {
  // ... exact logic from main.js lines 944-946
}
```

**[!] CRITICAL:** When writing the actual file, copy the exact constant values from `main.js`. Do not invent or approximate values. The SVG string, DEFAULT_SETTINGS.features keys, and workflow state interfaces must be byte-for-byte identical to the originals.

- [ ] **Step 2: Commit**

```bash
git add paperforge/plugin/src/constants.ts
git commit -m "feat(plugin): extract constants to src/constants.ts"
```

---

### Task 6: Create `src/services/memory-state.ts`

**Files:**
- Create: `paperforge/plugin/src/services/memory-state.ts`

Source: `main.js` lines 6-206 (inline memoryState IIFE)

- [ ] **Step 1: Write the module**

```typescript
import * as fs from "fs";
import * as path from "path";

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

const DEFAULTS: PathConfig = {
  system_dir: "System",
  resources_dir: "Resources",
  literature_dir: "Literature",
  base_dir: "Bases",
  _warning: null,
};

export function readPathConfig(vaultPath: string): PathConfig {
  const pfPath = path.join(vaultPath, "paperforge.json");
  try {
    if (!fs.existsSync(pfPath)) {
      return { ...DEFAULTS, _warning: "paperforge.json not found; using defaults" };
    }
    const raw = fs.readFileSync(pfPath, "utf-8");
    const data = JSON.parse(raw);
    const vc = data.vault_config || {};
    return {
      system_dir: vc.system_dir || data.system_dir || DEFAULTS.system_dir,
      resources_dir: vc.resources_dir || data.resources_dir || DEFAULTS.resources_dir,
      literature_dir: vc.literature_dir || data.literature_dir || DEFAULTS.literature_dir,
      base_dir: vc.base_dir || data.base_dir || DEFAULTS.base_dir,
      _warning: null,
    };
  } catch (e) {
    console.warn("PaperForge: Failed to read paperforge.json, using defaults", e);
    return { ...DEFAULTS, _warning: "paperforge.json invalid; using defaults" };
  }
}

export function resolveVaultPaths(vaultPath: string): ResolvedPaths {
  const cfg = readPathConfig(vaultPath);
  const systemDir = path.join(vaultPath, cfg.system_dir, "PaperForge");
  return {
    vault: vaultPath,
    systemDir,
    indexesDir: path.join(systemDir, "indexes"),
    logsDir: path.join(systemDir, "logs"),
    dbPath: path.join(systemDir, "indexes", "paperforge.db"),
    memoryStatePath: path.join(systemDir, "indexes", "memory-runtime-state.json"),
    vectorStatePath: path.join(systemDir, "indexes", "vector-runtime-state.json"),
    healthStatePath: path.join(systemDir, "indexes", "runtime-health.json"),
    buildStatePath: path.join(systemDir, "indexes", "vector-build-state.json"),
    orphanStatePath: path.join(systemDir, "indexes", "sync-orphan-state.json"),
    exportsDir: path.join(systemDir, "exports"),
    ocrDir: path.join(systemDir, "ocr"),
    pluginDataPath: path.join(vaultPath, ".obsidian", "plugins", "paperforge", "data.json"),
    pfJsonPath: path.join(vaultPath, "paperforge.json"),
    configWarning: cfg._warning,
  };
}

function readJSONFile(filePath: string): Record<string, unknown> | null {
  try {
    if (!fs.existsSync(filePath)) return null;
    return JSON.parse(fs.readFileSync(filePath, "utf-8"));
  } catch {
    return null;
  }
}

export interface MemoryRuntime {
  paper_count_db: number;
  needs_rebuild: boolean;
  [key: string]: unknown;
}

export function getMemoryRuntime(vaultPath: string): MemoryRuntime | null {
  const paths = resolveVaultPaths(vaultPath);
  return readJSONFile(paths.memoryStatePath) as MemoryRuntime | null;
}

export interface VectorRuntime {
  enabled: boolean;
  deps_installed: boolean;
  db_exists: boolean;
  healthy: boolean;
  chunk_count: number;
  [key: string]: unknown;
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
  return !!(s && s.paper_count_db > 0 && !s.needs_rebuild);
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
  return !!(s && s.summary && (s.summary as Record<string, unknown>).status === "ok");
}

export function getMemoryStatusText(vaultPath: string): string {
  const s = getMemoryRuntime(vaultPath);
  if (!s || s.paper_count_db === 0) return "DB not found. Run paperforge memory build.";
  return "Papers: " + s.paper_count_db + " | " + ((s as Record<string, unknown>).fresh ? "fresh" : "stale");
}

export function getVectorStatusText(vaultPath: string): string {
  const s = getVectorRuntime(vaultPath);
  if (!s) return "Status unavailable";
  if (s.healthy === false) return "Vector index unreadable - rebuild required";
  return "Chunks: " + s.chunk_count + " | " + s.model + " | " + s.mode;
}

let _cachedPython: PythonResult | null = null;

export function getCachedPython(
  vaultPath: string,
  settings: PaperForgeSettings
): PythonResult {
  if (_cachedPython) return _cachedPython;
  if (settings && settings.python_path && settings.python_path.trim()) {
    const p = settings.python_path.trim();
    if (fs.existsSync(p)) {
      _cachedPython = { path: p, source: "manual", extraArgs: [] };
      return _cachedPython;
    }
  }
  const venvCandidates = [
    path.join(vaultPath, ".paperforge-test-venv", "Scripts", "python.exe"),
    path.join(vaultPath, ".venv", "Scripts", "python.exe"),
    path.join(vaultPath, "venv", "Scripts", "python.exe"),
  ];
  for (const candidate of venvCandidates) {
    if (fs.existsSync(candidate)) {
      _cachedPython = { path: candidate, source: "auto-detected", extraArgs: [] };
      return _cachedPython;
    }
  }
  const sysCandidates = [
    { path: "py", extraArgs: ["-3"] },
    { path: "python", extraArgs: [] },
    { path: "python3", extraArgs: [] },
  ];
  for (const c of sysCandidates) {
    try {
      const out = execFileSync(c.path, [...c.extraArgs, "--version"], {
        encoding: "utf-8",
        timeout: 5000,
        windowsHide: true,
      });
      if (out && out.toLowerCase().includes("python")) {
        _cachedPython = { path: c.path, source: "auto-detected", extraArgs: c.extraArgs };
        return _cachedPython;
      }
    } catch (_) {}
  }
  _cachedPython = { path: "python", source: "auto-detected", extraArgs: [] };
  return _cachedPython;
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

export function buildSnapshot(
  vaultPath: string,
  _readFn?: (filePath: string) => Record<string, unknown> | null,
  _resolvePaths?: (vaultPath: string) => ResolvedPaths
): Snapshot {
  const readFn = _readFn || readJSONFile;
  const resolvePaths = _resolvePaths || resolveVaultPaths;
  const paths = resolvePaths(vaultPath);
  const memory = readFn(paths.memoryStatePath) as MemoryRuntime | null;
  const vector = readFn(paths.vectorStatePath) as VectorRuntime | null;
  const health = readFn(paths.healthStatePath);
  const memoryOk = !!(memory && memory.paper_count_db > 0 && !memory.needs_rebuild);
  const vectorOk = !!(vector && vector.enabled && vector.deps_installed && vector.db_exists && vector.chunk_count > 0);
  return {
    memory,
    vector,
    health,
    updatedAt: (memory && memory.updated_at) || (vector && vector.updated_at) || "",
    summary: {
      status: memoryOk && vectorOk ? "ready" : "degraded",
      memoryReady: memoryOk,
      vectorReady: vectorOk,
      healthOk: !!(health && health.summary && (health.summary as Record<string, unknown>).status === "ok"),
    },
  };
}

export function shouldRenderVectorReady(
  vectorDepsOk: boolean | null,
  embedStatusText: string
): boolean {
  return vectorDepsOk === true;
}
```

**[!] CRITICAL:** All string values and paths must match the original `main.js` exactly. Do not change path separators or naming conventions. The functions `getMemoryStatusText`, `getVectorStatusText`, `isHealthOk`, `getCachedPython`, and `buildSnapshot` are REQUIRED by the dashboard view and settings tab — they must be exported.

- [ ] **Step 2: Verify TypeScript compiles**

```bash
npx tsc --noEmit --skipLibCheck
```
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add paperforge/plugin/src/services/memory-state.ts
git commit -m "feat(plugin): extract memory-state service to src/services/memory-state.ts"
```

---

### Task 7: Create `src/services/python-bridge.ts`

**Files:**
- Create: `paperforge/plugin/src/services/python-bridge.ts`

Source: `main.js` lines 209-420 (inlined testable.js functions) + lines 421-589 (cross-platform Python/BBT detection)

- [ ] **Step 1: Write the module combining both python resolution and BBT detection**

This module absorbs all functions currently in `src/testable.js` PLUS the Python/BBT detection logic from `main.js` lines 421-589:

```typescript
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { execFile, execFileSync, ExecFileOptions } from "child_process";
import { PaperForgeSettings } from "../constants";
import { ResolvedPaths } from "./memory-state";

// ── Python executable resolution ──

export interface PythonResult {
  path: string;
  source: "manual" | "auto-detected";
  extraArgs: string[];
}

export function resolvePythonExecutable(
  vaultPath: string,
  settings: PaperForgeSettings,
  _fs?: typeof fs,
  _execFileSync?: typeof execFileSync
): PythonResult {
  // ... exact logic from main.js lines 61-102 of testable.js
  // IMPORTANT: _fs and _execFileSync are DI parameters for testability — preserve them
}

// ── Plugin version ──

export function getPluginVersion(app: { plugins?: { plugins?: Record<string, { manifest?: { version?: string } }> } }): string | null {
  // ... exact logic from testable.js lines 104-112
}

// ── Runtime version check ──

export function checkRuntimeVersion(
  pythonExe: string,
  pluginVersion: string,
  cwd: string,
  timeout?: number,
  _execFile?: typeof execFile
): Promise<{ status: string; pyVersion: string | null; pluginVersion: string; error: string | null }> {
  // ... exact logic from testable.js lines 114-134
  // IMPORTANT: _execFile is a DI parameter for testability — preserve it
}

// ── Error classification ──

export function classifyError(errorCode: string): ErrorClassification {
  // ... exact logic from testable.js lines 138-153
}

// ── Install command builder ──

export function buildRuntimeInstallCommand(
  pythonExe: string,
  version: string,
  extraArgs?: string[]
): InstallCommand {
  // ... exact logic from testable.js lines 155-162
}

// ── Status parsing ──

export function parseRuntimeStatus(
  err: NodeJS.ErrnoException | null,
  stdout: string,
  stderr: string
): RuntimeStatus {
  // ... exact logic from testable.js lines 164-186
}

// ── Command args builder ──

export function buildCommandArgs(
  action: ActionDef,
  key: string | null,
  filter?: string | null
): string[] {
  // ... exact logic from testable.js lines 226-231
}

// ── Subprocess runner ──

export function runSubprocess(
  pythonExe: string,
  args: string[],
  cwd: string,
  timeout: number,
  _spawn?: typeof import("child_process").spawn,
  env?: NodeJS.ProcessEnv
): Promise<SubprocessResult> {
  // ... exact logic from testable.js lines 233-258
}

// ── Cross-platform Python helpers (main.js lines 421-589) ──

export function resolveGitDir(): string {
  // ... exact logic from main.js lines 426-444
}

export function paperforgeEnrichedEnv(): NodeJS.ProcessEnv {
  // ... exact logic from main.js lines 445-461
}

export function shellQuoteForExec(cmd: string): string {
  // ... exact logic from main.js lines 462-467
}

export function isLikelyAppleStubPython(resolvedAbsPath: string): boolean {
  // ... exact logic from main.js lines 468-472
}

export function collectDarwinPythonCandidates(home: string): string[] {
  // ... exact logic from main.js lines 473-482
}

export function getPaperforgePythonCmd(): string {
  // ... exact logic from main.js lines 483-513
}

export function paperforgePythonExecArgs(scriptTail: string): string[] {
  // ... exact logic from main.js lines 514-518
}

export function tryExecPythonVersion(callback: (version: string | null) => void): void {
  // ... exact logic from main.js lines 519-555
}

// ── BBT detection (main.js lines 556-589) ──

export function dirLooksLikeBetterBibtexFolder(entryName: string): boolean {
  // ... exact logic from main.js lines 556-560
}

export function scanBbtDirectChildren(dir: string): string[] {
  // ... exact logic from main.js lines 561-571
}

export function scanBbtUnderProfiles(profilesDir: string): string[] {
  // ... exact logic from main.js lines 572-589
}
```

**[!] CRITICAL:** Every function body must be copied verbatim from the source files, with only import/export syntax changed. Do not refactor, rename, or reorder logic at this stage.

- [ ] **Step 2: Verify TypeScript compiles**

```bash
npx tsc --noEmit --skipLibCheck
```
Expected: No errors. Fix any type issues before committing.

- [ ] **Step 3: Commit**

```bash
git add paperforge/plugin/src/services/python-bridge.ts
git commit -m "feat(plugin): extract python-bridge service to src/services/python-bridge.ts"
```

---

### Task 8: Create `src/i18n.ts`

**Files:**
- Create: `paperforge/plugin/src/i18n.ts`

Source: `main.js` lines 601-906 (LANG object + langFromApp + t())

- [ ] **Step 1: Write the module**

```typescript
import { App } from "obsidian";

interface LangPack {
  // ... all keys from main.js LANG.en and LANG.zh objects
}

// Copy LANG object verbatim from main.js lines 602-888
const LANG: { en: LangPack; zh: LangPack } = {
  en: {
    // ... exact key-value pairs from main.js
  },
  zh: {
    // ... exact key-value pairs from main.js
  },
};

let T: LangPack | null = null;

export function langFromApp(app: App): "zh" | "en" {
  // ... exact logic from main.js lines 889-904
}

export function setLanguage(app: App): void {
  T = langFromApp(app) === "zh" ? LANG.zh : LANG.en;
}

export function t(key: string): string {
  return (T && (T as Record<string, string>)[key]) || (LANG.en as Record<string, string>)[key] || key;
}
```

**[!] CRITICAL:** The LANG object is ~280 lines. Copy it exactly from `main.js` lines 602-888. Do not modify any translation strings.

- [ ] **Step 2: Verify TypeScript compiles**

```bash
npx tsc --noEmit --skipLibCheck
```
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add paperforge/plugin/src/i18n.ts
git commit -m "feat(plugin): extract i18n language pack to src/i18n.ts"
```

---

## Phase 3: Extract Views

### Task 9: Create `src/views/dashboard.ts`

**Files:**
- Create: `paperforge/plugin/src/views/dashboard.ts`

Source: `main.js` lines 948-2610 (`PaperForgeStatusView` class, ~1662 lines)

- [ ] **Step 1: Write the module**

```typescript
import { ItemView, WorkspaceLeaf, Notice } from "obsidian";
import { VIEW_TYPE_PAPERFORGE, ACTIONS, ActionDef } from "../constants";
import { t } from "../i18n";
import { getMemoryRuntime, isMemoryReady, getVectorRuntime, isVectorReady, getRuntimeHealth, resolveVaultPaths, shouldRenderVectorReady } from "../services/memory-state";
import { resolvePythonExecutable, buildCommandArgs, runSubprocess } from "../services/python-bridge";
import { getDisclosureState, toggleDisclosureState } from "../utils/disclosure";

export class PaperForgeStatusView extends ItemView {
  // ... EXACT class body from main.js lines 948-2610
  // Convert `this.app` usage to typed `this.app` (Obsidian App type)
  // Convert `memoryState.xxx()` calls to direct function imports
  // Convert `T` (global) to `t()` function import
}
```

**[!] CRITICAL:** This is the largest single module (~1660 lines). Key migration points:
1. Replace `this.app.vault.adapter.basePath` → `this.app.vault.adapter.basePath` (unchanged, but now typed)
2. Replace `memoryState.resolveVaultPaths(vp)` → `resolveVaultPaths(vp)` (direct import)
3. Replace `memoryState.getMemoryRuntime(vp)` → `getMemoryRuntime(vp)` (direct import)
4. Replace `T.xxx` or `T[key]` → `t(key)` (i18n function)
5. Replace `resolvePythonExecutable(vp, this.settings)` → imported function
6. Replace `buildCommandArgs(action, key, filter)` → imported function
7. Replace `runSubprocess(py, args, vp, timeout)` → imported function
8. Replace `getDisclosureState(this.settings, key, default)` → imported function
9. Replace `toggleDisclosureState(this.settings, key, default)` → imported function
10. Add proper TypeScript types to all method parameters and return values

- [ ] **Step 2: Verify TypeScript compiles**

```bash
npx tsc --noEmit --skipLibCheck
```
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add paperforge/plugin/src/views/dashboard.ts
git commit -m "feat(plugin): extract dashboard view to src/views/dashboard.ts"
```

---

### Task 10: Create `src/views/modals.ts`

**Files:**
- Create: `paperforge/plugin/src/views/modals.ts`

Source: `main.js` lines 3863-4619 (3 modal classes) + lines 183-207 (`checkOrphanState` standalone function, ~790 lines total)

- [ ] **Step 1: Write the module**

```typescript
import { Modal, App, Setting, Notice } from "obsidian";
import { t } from "../i18n";
import { PaperForgeSettings } from "../constants";
import { resolvePythonExecutable, buildCommandArgs, runSubprocess, getPaperforgePythonCmd, PythonResult } from "../services/python-bridge";
import { resolveVaultPaths, isMemoryReady, getCachedPython } from "../services/memory-state";

export class PaperForgeOcrPrivacyModal extends Modal {
  // ... EXACT class body from main.js lines 3863-3898
}

export class PaperForgeOrphanModal extends Modal {
  // ... EXACT class body from main.js lines 3899-3996
}

export class PaperForgeSetupModal extends Modal {
  // ... EXACT class body from main.js lines 3997-4619
}

/**
 * Checks for orphan papers after sync and prompts user via modal.
 * Called from dashboard view after sync completes and during auto-sync.
 * (main.js lines 183-207)
 */
export function checkOrphanState(
  app: App,
  plugin: { settings: PaperForgeSettings },
  vp: string
): void {
  // ... EXACT logic from main.js lines 183-207
  // Uses: memoryState.resolveVaultPaths (→ import resolveVaultPaths)
  //       memoryState.getCachedPython (→ import getCachedPython)
  //       PaperForgeOrphanModal
}
```

**[!] CRITICAL:** Same migration rules as Task 9. The SetupModal references `PaperForgeSettingTab` — use an interface or `import type` to avoid circular dependency. Define the minimal interface needed:

```typescript
interface ISettingTab {
  display(): void;
}
```

And accept it as a constructor parameter typed as `ISettingTab`.

- [ ] **Step 2: Verify TypeScript compiles**

```bash
npx tsc --noEmit --skipLibCheck
```
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add paperforge/plugin/src/views/modals.ts
git commit -m "feat(plugin): extract modals to src/views/modals.ts"
```

---

### Task 11: Create `src/settings.ts`

**Files:**
- Create: `paperforge/plugin/src/settings.ts`

Source: `main.js` lines 2611-3862 (`PaperForgeSettingTab` class, ~1251 lines)

- [ ] **Step 1: Write the module**

```typescript
import { PluginSettingTab, App, Setting } from "obsidian";
import { t, setLanguage } from "../i18n";
import { DEFAULT_SETTINGS, PaperForgeSettings } from "../constants";
import { resolvePythonExecutable, getPluginVersion, checkRuntimeVersion, buildRuntimeInstallCommand, classifyError, paperforgeEnrichedEnv, getPaperforgePythonCmd, shellQuoteForExec, resolveGitDir, collectDarwinPythonCandidates, tryExecPythonVersion, scanBbtUnderProfiles } from "../services/python-bridge";
import { resolveVaultPaths, getMemoryRuntime, getVectorRuntime, getRuntimeHealth, isMemoryReady } from "../services/memory-state";
import { getDisclosureState, toggleDisclosureState } from "../utils/disclosure";
// Modals are instantiated here — import them
import { PaperForgeOcrPrivacyModal, PaperForgeOrphanModal, PaperForgeSetupModal } from "./views/modals";

export class PaperForgeSettingTab extends PluginSettingTab {
  // ... EXACT class body from main.js lines 2611-3862
  // Same migration rules as Task 9 & 10
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
npx tsc --noEmit --skipLibCheck
```
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add paperforge/plugin/src/settings.ts
git commit -m "feat(plugin): extract settings tab to src/settings.ts"
```

---

## Phase 4: Rewrite Entry Point

### Task 12: Create `src/main.ts` (thin lifecycle entry)

**Files:**
- Create: `paperforge/plugin/src/main.ts`

Source: `main.js` lines 4620-4977 (`PaperForgePlugin` class + onload/onunload, ~357 lines) — compressed to ~100 lines

- [ ] **Step 1: Write the thin entry point**

```typescript
import { Plugin, addIcon } from "obsidian";
import { VIEW_TYPE_PAPERFORGE, PF_ICON_ID, PF_RIBBON_SVG, ACTIONS, DEFAULT_SETTINGS, PaperForgeSettings, overlayEntryWorkflowState, patchEntryWorkflowState } from "./constants";
import { t, setLanguage } from "./i18n";
import { PaperForgeSettingTab } from "./settings";
import { PaperForgeStatusView } from "./views/dashboard";
import { resolvePythonExecutable, resolveGitDir, paperforgePythonExecArgs, getPaperforgePythonCmd, shellQuoteForExec } from "./services/python-bridge";
import { resolveVaultPaths, readPathConfig } from "./services/memory-state";
import * as fs from "fs";
import { execFile, exec } from "child_process";

export default class PaperForgePlugin extends Plugin {
  settings!: PaperForgeSettings;
  private _lastExportMtime = 0;
  private _lastOcrMtimes: Record<string, number> = {};
  private _autoSyncRunning = false;
  private _lastSyncTime: string | null = null;
  private _pollTimer: ReturnType<typeof setInterval> | null = null;
  private _embedProcess: unknown = null;
  private _embedProgress = { current: 0, total: 0, key: "" };
  private _embedStderr = "";
  _memoryStatusText: string | null = null;

  async onload() {
    await this.loadSettings();
    this.saveSettings();
    setLanguage(this.app);
    this.registerView(VIEW_TYPE_PAPERFORGE, (leaf) => new PaperForgeStatusView(leaf));

    try { addIcon(PF_ICON_ID, PF_RIBBON_SVG); } catch (_) {}
    this.addRibbonIcon(PF_ICON_ID, "PaperForge Dashboard", () => PaperForgeStatusView.open(this));

    this.addSettingTab(new PaperForgeSettingTab(this.app, this));

    this.addCommand({
      id: "paperforge-status-panel",
      name: `PaperForge: ${t("guide_open")}`,
      callback: () => PaperForgeStatusView.open(this),
    });

    // Register action commands
    for (const a of ACTIONS) {
      this.addCommand({
        id: a.id,
        name: `PaperForge: ${a.title}`,
        callback: () => {
          const vp = this.app.vault.adapter.basePath;
          const { path: cmdPythonExe, extraArgs: cmdExtra = [] } = resolvePythonExecutable(vp, this.settings);
          execFile(cmdPythonExe, [...cmdExtra, "-m", "paperforge", a.cmd], { cwd: vp, timeout: 300000 }, (err, stdout, stderr) => {
            if (err) {
              new Notice(`[!!] ${a.cmd} failed: ${(stderr || err.message).slice(0, 120)}`, 8000);
              return;
            }
            new Notice(`[OK] ${a.okMsg || stdout.trim().split("\n")[0].slice(0, 80)}`);
          });
        },
      });
    }

    // Auto-update on startup
    if (this.settings.auto_update_on_startup === true && this.settings.setup_complete) {
      setTimeout(() => this._autoUpdate(), 3000);
    }
    this._startFilePolling();

    // First-launch snapshot migration
    this._firstLaunchSnapshotMigration();
  }

  private _firstLaunchSnapshotMigration() {
    const vp = this.app.vault.adapter.basePath;
    if (!vp) return;
    const paths = resolveVaultPaths(vp);
    if (!fs.existsSync(paths.memoryStatePath)) {
      const py = resolvePythonExecutable(vp, this.settings);
      const commands = [
        ["runtime-health", "--json"],
        ["memory", "status", "--json"],
        ["embed", "status", "--json"],
      ];
      commands.forEach((cmdArgs) => {
        const args = [...py.extraArgs, "-m", "paperforge", "--vault", vp, ...cmdArgs];
        execFile(py.path, args, { cwd: vp, timeout: 60000, windowsHide: true }, () => {});
      });
    }
  }

  // _autoUpdate — copied verbatim from main.js lines 4703-4738
  private _autoUpdate() { /* ... */ }

  // _startFilePolling, _checkExports, _autoSync, _checkOcr — verbatim from main.js lines 4742-4833
  private _startFilePolling() { /* ... */ }
  private _checkExports(vaultPath: string, fs: typeof import("fs"), path: typeof import("path"), exec: typeof import("child_process").exec) { /* ... */ }
  private _autoSync(vaultPath: string, exec: typeof import("child_process").exec) { /* ... */ }
  private _checkOcr(vaultPath: string, fs: typeof import("fs"), path: typeof import("path"), exec: typeof import("child_process").exec) { /* ... */ }

  // readPaperforgeJson / savePaperforgeJson — verbatim from main.js lines 4840-4932
  readPaperforgeJson() { /* ... */ }
  savePaperforgeJson(pathConfig: Partial<Record<string, string>>) { /* ... */ }

  onunload() {
    if (this._pollTimer) clearInterval(this._pollTimer);
    this.app.workspace.detachLeavesOfType(VIEW_TYPE_PAPERFORGE);
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData()) as PaperForgeSettings;
    if (this.settings.features && DEFAULT_SETTINGS.features) {
      this.settings.features = Object.assign({}, DEFAULT_SETTINGS.features, this.settings.features || {});
    }
    if (!this.settings.frozen_skills) { this.settings.frozen_skills = {}; }
    const pfConfig = readPathConfig(this.app.vault.adapter.basePath);
    this.settings.system_dir = pfConfig.system_dir;
    this.settings.resources_dir = pfConfig.resources_dir;
    this.settings.literature_dir = pfConfig.literature_dir;
    this.settings.base_dir = pfConfig.base_dir;
    if (this.settings.python_path && this.settings.python_path.trim()) {
      const pp = this.settings.python_path.trim();
      if (!fs.existsSync(pp)) {
        console.warn(`PaperForge: Saved python_path "${pp}" no longer exists — showing stale warning`);
        this.settings._python_path_stale = true;
      } else {
        this.settings._python_path_stale = false;
      }
    }
  }

  async saveSettings() {
    const dataToSave: Record<string, unknown> = {};
    for (const key of Object.keys(DEFAULT_SETTINGS)) {
      if (key in this.settings) {
        dataToSave[key] = (this.settings as Record<string, unknown>)[key];
      }
    }
    await this.saveData(dataToSave);
  }
}
```

**[!] CRITICAL:** 
1. All private methods (`_autoUpdate`, `_startFilePolling`, `_checkExports`, `_autoSync`, `_checkOcr`, `_firstLaunchSnapshotMigration`) must be copied verbatim from `main.js` lines 4703-4833 with only variable reference updates.
2. `readPaperforgeJson` and `savePaperforgeJson` (lines 4840-4932) must be copied verbatim.
3. Keep `module.exports = class` → `export default class` conversion.
4. The `data.json` saved by `this.saveData()` must produce identical output to the original plugin.

- [ ] **Step 2: Build with esbuild**

```bash
node esbuild.config.mjs
```
Expected: Build succeeds, `main.js` is generated in the plugin root.

- [ ] **Step 3: Compare bundle size**

```bash
# Check that the bundle is not unreasonably larger than original
wc -c main.js
```
Expected: Should be within ~20% of original 247KB (esbuild bundles node built-in shims, but tree-shaking removes dead code).

- [ ] **Step 4: Verify TypeScript compiles**

```bash
npx tsc --noEmit --skipLibCheck
```
Expected: No errors.

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/src/main.ts
git commit -m "feat(plugin): rewrite main.ts as thin lifecycle entry"
```

---

## Phase 5: Migrate Tests

### Task 13: Migrate test infrastructure

**Files:**
- Modify: `paperforge/plugin/vitest.config.ts`

- [ ] **Step 1: Update vitest.config.ts for .ts tests**

```typescript
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["tests/**/*.test.ts"],
    globals: true,
    // Mock Obsidian module for tests that don't mount full plugin
    setupFiles: [],
  },
});
```

- [ ] **Step 2: Verify vitest still loads**

```bash
npx vitest run
```
Expected: "No test files found" or similar — correct, since .mjs files no longer match.

- [ ] **Step 3: Commit**

```bash
git add paperforge/plugin/vitest.config.ts
git commit -m "test(plugin): switch vitest config to .ts test files"
```

---

### Task 14: Migrate each test file from .mjs to .ts

Migrate all 5 test files one at a time. Each sub-task: rewrite imports, verify test bodies still pass, commit.

---

#### Task 14a: `commands.test.mjs` → `commands.test.ts`

**Imports to change:**
```typescript
// OLD: import { ACTIONS, buildCommandArgs, runSubprocess } from '../src/testable.js';
// NEW:
import { ACTIONS, buildCommandArgs, runSubprocess } from "../src/services/python-bridge";
```

Test bodies: IDENTICAL. Only `ACTIONS`, `buildCommandArgs`, `runSubprocess` are used.

- [ ] Write the file, run `npx vitest run tests/commands.test.ts`, verify all pass
- [ ] Commit

---

#### Task 14b: `errors.test.mjs` → `errors.test.ts`

**Imports to change:**
```typescript
// OLD: import { classifyError, parseRuntimeStatus } from '../src/testable.js';
// NEW:
import { classifyError, parseRuntimeStatus } from "../src/services/python-bridge";
```

Test bodies: IDENTICAL.

- [ ] Write the file, run `npx vitest run tests/errors.test.ts`, verify all pass
- [ ] Commit

---

#### Task 14c: `runtime.test.mjs` → `runtime.test.ts`

**Imports to change:**
```typescript
// OLD: import { readPathConfig, resolveRuntimePaths, resolvePythonExecutable, checkRuntimeVersion } from '../src/testable.js';
// NEW:
import { readPathConfig } from "../src/services/memory-state";
import { resolveVaultPaths } from "../src/services/memory-state"; // renamed: resolveRuntimePaths → resolveVaultPaths
import { resolvePythonExecutable, checkRuntimeVersion } from "../src/services/python-bridge";
```

**Body changes needed:**
- `resolveRuntimePaths(vaultPath, _fs)` → `resolveVaultPaths(vaultPath)` (signature changed: no `_fs` param in memory-state.ts — the function always uses real `fs`).
  - If tests inject mock `_fs`, adapt to use `vi.mock("fs")` pattern instead.
- `resolvePythonExecutable(vp, settings, _fs, _execFileSync)` — DI params preserved, test bodies unchanged.
- `checkRuntimeVersion(py, ver, cwd, timeout, _execFile)` — DI param preserved, test bodies unchanged.

- [ ] Write the file, run `npx vitest run tests/runtime.test.ts`, fix any failures
- [ ] Commit

---

#### Task 14d: `settings-panels.test.mjs` → `settings-panels.test.ts`

**Imports to change:**
```typescript
// OLD: imports from '../src/testable.js'
// NEW:
import { shouldRenderVectorReady } from "../src/services/memory-state";
import { getDisclosureState, toggleDisclosureState } from "../src/utils/disclosure";
```

Test bodies: IDENTICAL.

- [ ] Write the file, run `npx vitest run tests/settings-panels.test.ts`, verify all pass
- [ ] Commit

---

#### Task 14e: `vector-ready.test.mjs` → `vector-ready.test.ts`

**Imports to change:**
```typescript
// OLD: import { shouldRenderVectorReady } from '../src/testable.js';
// NEW:
import { shouldRenderVectorReady } from "../src/services/memory-state";
```

Test bodies: IDENTICAL.

- [ ] Write the file, run `npx vitest run tests/vector-ready.test.ts`, verify all pass
- [ ] Commit

---

## Phase 6: Cleanup & Verify

### Task 15: Delete legacy files

**Files:**
- Delete: `paperforge/plugin/src/testable.js` (absorbed into `src/services/python-bridge.ts`)
- Backup: `paperforge/plugin/main.js` → `paperforge/plugin/main.js.bak`

- [ ] **Step 1: Rename original main.js as backup**

```bash
mv paperforge/plugin/main.js paperforge/plugin/main.js.bak
```

- [ ] **Step 2: Delete testable.js**

```bash
rm paperforge/plugin/src/testable.js
```

- [ ] **Step 3: Delete old .mjs test files (verify first)**

```bash
# First check which .mjs files still exist
ls paperforge/plugin/tests/*.test.mjs 2>/dev/null
# For each remaining .mjs file:
git rm paperforge/plugin/tests/<name>.test.mjs
```
(They should have been removed during Task 14 sub-commits. This step ensures none remain tracked.)

- [ ] **Step 4: Build final bundle**

```bash
npm run build
```
Expected: TypeScript checks pass, esbuild produces `main.js`.

- [ ] **Step 5: Verify main.js is valid CJS**

```bash
node -e "require('./main.js')"
```
Expected: Should fail with "obsidian module not found" (expected — obsidian only exists in Obsidian runtime), but NOT with syntax errors.

- [ ] **Step 6: Run full test suite**

```bash
npm test
```
Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add paperforge/plugin/main.js paperforge/plugin/main.js.bak
git commit -m "chore(plugin): finalize TS migration — delete legacy testable.js, keep main.js.bak"
```

---

### Task 16: Final verification checklist

- [ ] **Step 1: `npm test` — all tests pass**

```bash
npm test
```

- [ ] **Step 2: `npm run build` — clean build**

```bash
npm run build
```

- [ ] **Step 3: Diff main.js.bak vs main.js for structural correctness**

```bash
# Compare that exported class name and key structures match
rg "module.exports" main.js.bak
rg "module.exports" main.js
```
Expected: Both files export the same class (name may differ due to bundling, but structure should match).

- [ ] **Step 4: Verify styles.css and manifest.json untouched**

```bash
git diff main.js.bak -- styles.css manifest.json
```
Expected: No diff.

- [ ] **Step 5: Commit final verification**

```bash
git add -A
git commit -m "chore(plugin): final verification — all tests pass, build clean"
```

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Type errors from loose JS patterns | Build breaks | `tsc --noEmit` after each task; use `@ts-ignore` sparingly for Obsidian API holes |
| Bundle includes node built-ins | Runtime crash in Obsidian | `external: [...builtins]` in esbuild config prevents bundling fs/path/child_process |
| i18n T global replaced incorrectly | UI shows raw keys | All `T.xxx` → `t("xxx")` calls must use exact string keys from LANG object |
| Settings data.json format changes | User settings lost on upgrade | `saveSettings()` serialization must produce identical keys to original |
| Test mocks break on migration | Tests fail | Dependency injection params (`_spawn`, `_fs`, `_execFile`, `_execFileSync`) preserved in TypeScript signatures. Some test files may need `vi.mock("fs")` instead of DI for `resolveVaultPaths` (which uses real fs by default). |
| `resolveRuntimePaths` renamed to `resolveVaultPaths` | runtime.test.ts breaks | Explicit rename documented in Task 14c with migration instructions |
| `checkOrphanState` has no module home | Import errors in dashboard | Assigned to `views/modals.ts` (alongside `PaperForgeOrphanModal` which it instantiates) |
| Build output differs from original | Plugin fails to load in Obsidian | Compare `module.exports` of old vs new main.js; verify CJS format |
| Circular import: settings.ts ↔ modals.ts | Build/type error | Use interface-only import in modals.ts for setting tab reference |

---

## Dependency Graph

```text
main.ts
├── constants.ts              (no deps)
├── i18n.ts                   (obsidian App type)
├── services/memory-state.ts  (fs, path, child_process — external; constants.ts for PythonResult type)
├── services/python-bridge.ts (fs, path, os, child_process — external; constants.ts)
├── utils/disclosure.ts       (no deps)
├── settings.ts               (→ i18n, constants, python-bridge, memory-state, disclosure, modals)
│   └── views/modals.ts       (→ i18n, constants, python-bridge, memory-state)
│       └── exports: checkOrphanState (called from dashboard after sync)
└── views/dashboard.ts        (→ i18n, constants, python-bridge, memory-state, disclosure, modals.checkOrphanState)
```

---

## Post-Migration: What Gains

1. **TypeScript type checking** — catches API misuse at build time (`tsc --noEmit`)
2. **Modular codebase** — 9 focused files instead of 1 monolith; agent edits hit smaller targets
3. **Standard Obsidian plugin structure** — matches community conventions, easier for contributors
4. **esbuild sourcemaps** — `dev` builds include inline sourcemaps for Obsidian dev console
5. **Tree-shaking** — unused code eliminated from bundle
6. **Minification** — `production` builds are minified
7. **`main.js` still exists at root** — Obsidian, BRAT, and manual install all work identically
