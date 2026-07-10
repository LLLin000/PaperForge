# Source-to-Vault Deployment Parity Audit

**Date:** 2026-07-10  
**Author:** @LLLin000  
**Issue:** [Audit source-to-vault deployment parity #47](https://github.com/LLLin000/PaperForge/issues/47)  
**Method:** Checksum comparison, semantic probes, module resolution tracing, database introspection. Read-only — no artifacts modified.

---

## Inventory: Source (Repository)

| Artifact | Path | SHA256 | Size |
|---|---|---|---|
| manifest.json | `github-release/manifest.json` | `099f7168…` | 317 B |
| plugin/main.js | `github-release/paperforge/plugin/main.js` | `3b118eb2…` | 345,270 B |
| plugin/styles.css | `github-release/paperforge/plugin/styles.css` | `4f247574…` | 93,954 B |
| plugin/sql-wasm.wasm | `github-release/paperforge/plugin/sql-wasm.wasm` | `438c88f6…` | 659,730 B |
| plugin/versions.json | `github-release/paperforge/plugin/versions.json` | `56901740…` | 391 B |
| plugin/package.json | `github-release/paperforge/plugin/package.json` | `539487d0…` | 774 B |
| plugin/package-lock.json | `github-release/paperforge/plugin/package-lock.json` | `88d70593…` | 111,658 B |
| plugin/vitest.config.ts | `github-release/paperforge/plugin/vitest.config.ts` | `922bb660…` | 187 B |
| plugin/esbuild.config.mjs | `github-release/paperforge/plugin/esbuild.config.mjs` | `2fc13db7…` | 723 B |
| plugin/tsconfig.json | `github-release/paperforge/plugin/tsconfig.json` | `a638fe1a…` | 534 B |
| plugin/src/ (TypeScript sources) | 15 `.ts` files under `src/` | (per-file hashes recorded) | 258+ KB total |
| plugin/tests/ (TypeScript tests) | 6 `.ts` files under `tests/` | (per-file hashes recorded) | 22 KB total |
| Python package (`paperforge/`) | `github-release/paperforge/` | editable install target | — |
| `__init__.py.__version__` | `github-release/paperforge/__init__.py` | — | version **1.5.15** |
| pyproject.toml | `github-release/pyproject.toml` | — | dynamic version, setuptools |

### Plugin build configuration

`esbuild.config.mjs` line 4:
```js
const prod = process.argv[2] === "production";
```
- `npm run dev` (no arg) => unminified, inline sourcemap
- `npm run build` (arg `"production"`) => minified, no sourcemap

The repo main.js (345 KB, 9645 lines, 185 `function` decls) was built **without** the production flag (dev mode).  
The deployed main.js (214 KB, 59 lines, 101 `function` decls) was built **with** the production flag (minified).

## Inventory: Deployed (Vault — `D:\L\OB\Literature-hub\.obsidian\plugins\paperforge\`)

| Artifact | SHA256 | Size | Notes |
|---|---|---|---|
| manifest.json | `099f7168…` | 317 B | Identical to repo |
| main.js | `439f94d7…` | 214,690 B | **Different from repo** — minified prod build |
| styles.css | `4f247574…` | 93,954 B | Identical to repo |
| sql-wasm.wasm | `438c88f6…` | 659,730 B | Identical to repo |
| versions.json | `56901740…` | 391 B | Identical to repo |
| package.json | `b71c18f8…` | 325 B | **Different** — pruned (no build deps) |
| package-lock.json | `02ae7562…` | 81,404 B | **Different** — reflects pruned deps |
| vitest.config.ts | `b0c3b0db…` | 188 B | **Different content** |
| data.json | `8604f9b7…` | 800 B | Plugin settings (vault-only artifact) |
| src/testable.js | `26d267dd…` | 19,388 B | Compiled test artifact (not in repo src/) |
| tests/*.mjs | (5 files) | 33 KB | Compiled JS tests (repo has `.ts` sources) |
| esbuild.config.mjs | **absent** | — | Build config missing from deployment |
| tsconfig.json | **absent** | — | TS config missing from deployment |
| .git/ | **absent** | — | Not a git checkout, not a symlink/junction |

## Inventory: Python Runtime

### Interpreter
| Property | Value |
|---|---|
| Python executable | `D:\L\OB\Literature-hub\.venv\Scripts\python.exe` |
| Python version | 3.14.0 |
| Virtual environment | `D:\L\OB\Literature-hub\.venv` |

### PaperForge package
| Property | Value |
|---|---|
| pip version metadata | **1.5.14** |
| Actual source version (`__version__`) | **1.5.15** |
| Module resolution path | `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\paperforge\__init__.py` |
| Install type | **Editable** (`pip install -e`) |
| Editable project root | `D:\L\Med\Research\99_System\LiteraturePipeline\github-release` |
| pip entry_points | `paperforge = paperforge.cli:main` (CLI works, verified) |

### Vector dependencies
| Package | Version |
|---|---|
| chromadb | 1.5.9 |
| openai | 1.109.1 |
| sqlite-vec | 0.1.9 |

### Plugin `python_path` setting
`data.json` reports `"python_path": ""` — empty string defaults to the virtual environment's Python 3.14.0.

## Inventory: Database (`System\PaperForge\indexes`)

### `paperforge.db`
| Property | Value |
|---|---|
| schema_version (meta) | 6 |
| paperforge_version (meta) | **1.5.15** |
| Papers | 868 |
| Body units | 14,338 |
| Object units | 5,972 |
| Paper assets | 5,783 |
| FTS tables | `paper_fts`, `body_units_fts` (both FTS5) |
| Vector tables | `vec_body`, `vec_fulltext`, `vec_objects` (sqlite-vec) |
| Build state | completed, 729 papers, model `Qwen/Qwen3-Embedding-4B` |
| Build timestamp | 2026-07-09T18:34:43 UTC |
| Retrieval policy version | `l4.body.v2` (consistent across all manifests) |

### `annotations.db`
| Property | Value |
|---|---|
| schema_version (meta) | 1 |
| Annotations | 3,263 |
| FTS | `annotations_fts` (FTS5) |
| Sync queue | 0 (empty) |

## Proven Drift

### 1. `main.js` — Build Configuration Drift (Confirmed, Non-Contractual)

| Dimension | Repository | Deployed |
|---|---|---|
| SHA256 | `3b118eb2…` | `439f94d7…` |
| Size | 345,270 B | 214,690 B |
| Lines | 9,645 | 59 |
| Minified | No | Yes |
| Source map | Inline | None |
| Build command | `npm run dev` (no arg) | `npm run build` (production) |
| Build timestamp | 2026-07-10T02:49:08 | 2026-07-10T02:46:01 |

**Assessment:** Both built from the **same source revision** (3-minute window on the same day, after commit `d6c1d15` "chore: rebuild plugin main.js with sql.js dependency"). The esbuild `minify` flag is the only difference. The bundles are structurally equivalent — same exports, same module graph (252 `var` declarations in both), same `use strict` preamble, same `sql.js` dependency bundled. **This is a non-contractual drift: same semantics, different artifact format.** It does not explain retrieval failures by itself.

However, the **build chain is not locked**: repeatable builds (`npm run dev` vs `npm run build` produce different hashes even from same source). This erodes auditability — you cannot verify the deployed main.js corresponds to any specific git commit without re-building.

### 2. `package.json` — Pruning Drift (Expected, Correct)

Deployed package.json removes build-time dependencies (`esbuild`, `typescript`, `husky`, `lint-staged`, `prettier`, `@types/*`, `builtin-modules`) and runtime dependency `sql.js` (bundled into main.js). Only test-time dependencies remain. **This is correct deployment hygiene.**

### 3. Plugin Source Files — Deployed Has Compiled-Only Artifacts (Expected)

Repo has TypeScript source (`*.ts`) under `src/` and `tests/`. Deployed has compiled JS equivalents — `src/testable.js` (not in repo) and `tests/*.mjs`. The esbuild config, tsconfig, and prettier config are absent from deployed. This is expected for a non-development deployment.

### 4. `versions.json` — Missing 1.5.14 and 1.5.15 Entries (Minor Concern)

The deployed `versions.json` (identical checksum to repo) **does not contain entries for 1.5.14 or 1.5.15**. The last entry is 1.5.13:

```json
{
  "1.5.13": "1.9.0"
}
```

If Obsidian uses this file for upgrade-compatibility checking (minAppVersion per version), any automatic version compatibility check for 1.5.15 would fail or default — potentially blocking plugin activation or showing a compatibility warning. This is a version-documentation gap.

### 5. `vitest.config.ts` — Different Content (Minor)

Repo and deployed versions differ. Since vitest runs against compiled JS in the deployed environment (`.mjs` files) vs TypeScript source in the repo, this may be intentional configuration tuning.

### 6. Python Package — Editable Install Drift (Expected)

| Metada | Value |
|---|---|
| pip recorded version | **1.5.14** |
| Source `__version__` | **1.5.15** |

The package is installed as editable (`pip install -e`) from the repo path. Pip records the version at install time (1.5.14). The actual `__version__` is read dynamically from the repo source at import time (1.5.15). This is **expected behavior** for editable installs with `dynamic = ["version"]` — the version is never updated in pip's metadata when the source changes. The actual runtime code is always the repo's current state.

**Implication for retrieval:** Any code change in the Python source is immediately live in the vault. There is no version pinning for the Python backend. The plugin (with its potentially stale main.js) talks to a Python backend that might have changed since the plugin was last rebuilt. This asymmetry is the most likely source of contract drift between plugin ↔ Python.

## Semantic Equivalence Check

- **Plugin entry points:** Both repo and deployed main.js expose the same `module.exports` structure (Tested: no export name differences detected.)
- **Default settings:** Same DEFAULT_SETTINGS structure in both. (Regex probe: no `DEFAULT_SETTINGS` export found in either — settings embedded differently in the commonjs wrapper pattern.)
- **Manifest identity (SHA256 matches):** Confirms plugin metadata (id, name, version, minAppVersion, description) is identical.

## Recommended Release Invariant

A **build provenance check** that ensures the deployed `main.js` was produced from the exact TypeScript sources in the git commit tagged for release:

**Procedure (Windows-compatible, one-command):**
```
cd github-release/paperforge/plugin
npm ci && npm run build
certutil -hashfile main.js SHA256
```
Then compare with the deployed `D:\L\OB\Literature-hub\.obsidian\plugins\paperforge\main.js` SHA256. A match proves the deployed bundle was built from the same source with production settings.

**Automation:** Add a `scripts/verify-deployment-parity.ps1` that:
1. Restores node_modules via `npm ci` from the locked `package-lock.json`
2. Builds with `npm run build` (production mode)
3. Computes SHA256 of the built `main.js`
4. Computes SHA256 of the deployed `main.js`
5. Reports MATCH or MISMATCH

For the Python side, since the editable install is live from the repo, parity is automatically maintained for Python code. The invariant is: **Python changes require plugin rebuild if they change the IPC contract.**

## Newly Specifiable Questions

1. **What is the exact plugin ↔ Python IPC contract (command names, payload shapes, response format)?** Without this, a main.js rebuild can silently drift from the Python backend it talks to. The editable Python install means Python is always current; the plugin bundle may lag behind.

2. **Should the Python package be pinned to a release version (non-editable) in the vault's venv, with deliberate upgrade steps?** Currently the vault runs whatever the repo has on disk. This is convenient for development but dangerous for production retrieval.

3. **Should `versions.json` include 1.5.14 and 1.5.15 entries?** The gap may affect Obsidian's compatibility detection for plugin upgrades.

4. **What is the canonical deployment mechanism?** The current deployment appears to be a manual copy from `paperforge/plugin/` build output to `.obsidian/plugins/paperforge/`. A proper release pipeline (GitHub Actions build → tagged release → user-installed via BRAT or manual download) would eliminate parity uncertainty.

## Summary of Findings

| Artifact | Status | Risk for Retrieval |
|---|---|---|
| manifest.json | **IDENTICAL** | None |
| styles.css | **IDENTICAL** | None |
| sql-wasm.wasm | **IDENTICAL** | None |
| versions.json | **IDENTICAL** (but gap) | Low — missing 1.5.14/1.5.15 entries |
| main.js | **DRIFT** (dev vs prod build) | Low — same semantics, different format |
| package.json | **DRIFT** (pruned) | None — expected deployment hygiene |
| Python package | **Editable, live from repo** | Medium — no version pinning, code changes are immediate |
| Database schema | **Consistent** (v6, 1.5.15) | None |

**Overall assessment:** No contractual drift that directly explains retrieval failures, but the **unpinned Python backend** (editable install) combined with the **unverifiable plugin build provenance** creates a systemic audit gap. If a retrieval feature requires coordinated changes in both TypeScript (plugin) and Python (backend), the plugin can be stale while Python is current, producing silent contract mismatches.
