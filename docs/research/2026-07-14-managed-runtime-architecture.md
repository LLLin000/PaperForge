# PaperForge Managed-Runtime Architecture

- **Date:** 2026-07-14
- **Issue:** [#70](https://github.com/LLLin000/PaperForge/issues/70)
- **Parent map:** [#65](https://github.com/LLLin000/PaperForge/issues/65)
- **Prerequisites:** [#66 audit](https://github.com/LLLin000/PaperForge/issues/66#issuecomment-4968837257), [RuntimeVenv]('C:\Users\Lin\.omp\agent\sessions\--D--L-Med-Research-99_System-LiteraturePipeline-github-release--\2026-07-14T05-05-31-302Z_019f5f04-16a6-7000-8a55-8ed6ffe71104\RuntimeVenv.md'), [RuntimeBundled]('C:\Users\Lin\.omp\agent\sessions\--D--L-Med-Research-99_System-LiteraturePipeline-github-release--\2026-07-14T05-05-31-302Z_019f5f04-16a6-7000-8a55-8ed6ffe71104\RuntimeBundled.md'), [RuntimeSystem]('C:\Users\Lin\.omp\agent\sessions\--D--L-Med-Research-99_System-LiteraturePipeline-github-release--\2026-07-14T05-05-31-302Z_019f5f04-16a6-7000-8a55-8ed6ffe71104\RuntimeSystem.md'), [RuntimeService]('C:\Users\Lin\.omp\agent\sessions\--D--L-Med-Research-99_System-LiteraturePipeline-github-release--\2026-07-14T05-05-31-302Z_019f5f04-16a6-7000-8a55-8ed6ffe71104\RuntimeService.md')
- **Scope:** Architecture decision, interface, lifecycle, failure matrix, migration, acceptance criteria. No production code changed.

---

## Decision: Plugin-Managed Venv (System Python Preferred, Conditional Fallback)

**Adopt a plugin-managed virtual environment bootstrapped from system Python as the primary runtime. Optionally fall back to a release-validated python-build-standalone download on triplets where an artifact is published, checksummed, and integration-tested. Fallback is not assumed for every OS/arch -- unsupported triplets expose a manual action.**

This is the smallest mechanism satisfying all six [#66](https://github.com/LLLin000/PaperForge/issues/66#issuecomment-4968837257) requirements: stable runtime identity; atomic install/update/rollback; no silent fallback to an unrelated system Python; one resolver shared by every plugin command; actionable unsupported-platform and missing-runtime states.

Both bootstrap paths converge into the same immutable version-slot structure, the same `ManagedRuntime` class, and the same single pointer-file resolver.

### Why not the other designs?

**Design C (canonical resolver only):** Eliminates duplicate resolvers but provides no isolation, no rollback, no solution for users without Python 3.10+. pip installs into system site-packages -- the #66 requirement for stable runtime identity is unmet because the system package set is outside PaperForge's control.

**Design B (bundled only):** Requires every user to download a large artifact even when Python is already installed. macOS code-signing ($99/yr) and missing ARM64 Windows builds add platform risk that >90% of users do not need.

**Design D (HTTP service/sidecar):** Its own analysis rejects it. ~2,800 lines, port management, auth tokens, orphan-process risk, self-update danger. Service wins 3 of 14 comparison criteria against the hardened subprocess model.

| Scenario | Action | Python source |
|---|---|---|
| System Python 3.10+ found | create venv, pip install (preferred) | OS |
| No Python, triplet validated | download python-build-standalone (fallback) | GitHub Release |
| No Python, triplet not validated | manual install_python action | python.org / package manager |
| Python too old (<3.10) | actionable error or validated fallback | user choice |

---

## Four-Design Comparison

| Criterion | A: Venv | B: Bundled | C: Resolver | D: Service |
|---|---|---|---|---|
| OS Python required | Yes (fallback opt.) | No | Yes | Yes |
| Isolation | Venv | Bundled venv | System site-packages | Service env |
| Rollback | Pointer file swap | Pointer file swap | pip reinstall only | pip + backup |
| Single resolver | ManagedRuntime | ManagedRuntime | resolve-python CLI | HTTP client |
| No-Python bootstrap | Error / validated dl | Built-in | Error only | Error only |
| Offline repair | Full (cached pip) | Full (cached artifact) | Partial (needs network) | Partial |
| Code signing needed | No | Yes (macOS) | No | No |
| New code | ~400 lines | ~800 lines | ~300 lines | ~2,800 lines |

---

## Lifecycle State Machine

```
            not_installed
                  │
             ensure()
                  ▼
         resolvePython ──┬── system Python found ──▶ .runtime/v{ver}/
         (bootstrap)     │                            venv + pip install
                         ├── validated triplet ──────▶ (same path, auto-download)
                         └── no Python / no triplet ──▶ unavailable
                                                         (actionable error)

    verify: python -I -c "import paperforge; print(__version__)"
         │
    ┌────┴────┐
    ▼         ▼
  pass      fail ──▶ needs_repair (slot deleted, retry or rollback)
    │
    ▼
  write active-runtime.json (atomic pointer)
    │
    ▼
  ready  ◀── status() probe passes
    │
    ├── ensure({version}) → new slot → verify → rewrite pointer
    ├── health probe fails → needs_repair
    └── cache stale, no probe → unknown (never ready w/o verification)
```

### Transitions

| From | Trigger | Effect |
|---|---|---|
| not_installed | ensure() | Bootstrap → slot in .runtime/v{ver}/ → verify → write pointer |
| installing | verify pass | Pointer written, runtime ready |
| installing | verify fail | Slot deleted, needs_repair |
| ready | ensure({version: X}) | New slot, verify, rewrite pointer; old slot intact |
| ready | stale cache, no probe | unknown (probe required to return ready) |
| unknown | status() probe passes | ready |
| unknown | status() probe fails | needs_repair |
| needs_repair | ensure() | Install new slot or rewrite pointer to rollback slot |

---

## Plugin-Facing Interface

### Types and class

```typescript
export type RuntimeState =
  | 'ready'            // probe passed: interpreter runs, paperforge imports, version matches
  | 'not_installed'    // no runtime directory or pointer file
  | 'needs_repair'     // slot exists but probe failed
  | 'unknown'          // no recent probe; cached state may be stale; NEVER returned as ready
  | 'unavailable';     // no bootstrap Python, no validated fallback triplet

export interface RuntimeHealth {
  readonly state: RuntimeState;
  readonly pythonPath: string | null;
  readonly version: string | null;
  readonly source: 'venv' | 'system' | 'manual' | 'none';
  readonly error: ErrorInfo | null;
  readonly lastVerifiedAt: string | null;   // ISO-8601, null if never probed
  readonly stale: boolean;                  // true when cache outside freshness TTL
}

export interface ErrorInfo {
  readonly code: string;
  readonly message: string;
  readonly platformAction: string;
}

export interface StatusOptions {
  /** Return cached result even if stale. UI uses this for non-critical displays. */
  readonly allowStale?: boolean;
}

export interface EnsureOptions {
  readonly version?: string;     // target (default: plugin manifest version)
  readonly force?: boolean;      // build fresh slot regardless, verify, rewrite pointer
  readonly signal?: AbortSignal;
}
```

### ManagedRuntime class

```typescript
export class ManagedRuntime {
  /** Sync: last-known cached health from the most recent probe or ensure().
   *  Never blocks, never spawns processes. Returns 'unknown' with stale:true
   *  if no probe has run this session or the cache is expired.
   *
   *  Command dispatch uses this -- it fails closed: if the returned health
   *  is not 'ready' with !stale, the command shows "Runtime not ready" instead
   *  of falling back to an unverified system Python. The caller must await
   *  status() or ensure() to refresh the cache. */
  current(): RuntimeHealth;

  /** Async probe. Runs the interpreter in Python -I (isolated) mode:
   *    <python> -I -c "import paperforge; print(paperforge.__version__)"
   *  Isolated mode ignores PYTHONPATH, user site-packages, env vars -- ensures
   *  only the managed venv's site-packages satisfy the import.
   *
   *  Returns 'ready' ONLY when a probe has just passed and the cache is fresh.
   *  Returns 'unknown' when cache is stale or no probe has run, unless allowStale.
   *  NEVER returns 'ready' without a passing probe.
   *  Updates the cache consumed by current(). */
  async status(options?: StatusOptions): Promise<RuntimeHealth>;

  /** Ensure a working runtime at the target version.
   *  - ready: quick probe, return.
   *  - version differs: build new slot, verify, rewrite active-runtime.json.
   *  - not_installed/needs_repair: full bootstrap → slot → verify → pointer.
   *  - force=true: build fresh slot regardless, verify, rewrite pointer.
   *  - Cancellation via AbortSignal at any phase.
   *  Terminates with a fresh probe.
   *  Updates the cache consumed by current(). */
  async ensure(options?: EnsureOptions): Promise<RuntimeHealth>;
}
```

### Cache and freshness

- Successful probe cached with 5-minute TTL (configurable).
- `status()` without allowStale: fresh cache → cached state; stale cache → runs new probe.
- `status({allowStale: true})`: returns cached result with `stale: true`. UI must not render stale as ready.
- `ensure()` always probes at the end, never returns ready without a passing probe.
- UI rule: `unknown` displays as "Unknown -- check runtime health" with Refresh action. `stale: true` shows "Last checked: X ago" with Refresh. Only `state === 'ready' && !stale` is healthy.

---

## Directory Layout (Immutable Version Slots)

```
.vault/99_System/PaperForge/
└── .runtime/
    ├── v1.2.3/                     ← created once, never modified
    │   └── venv/Scripts/python.exe
    ├── v1.3.0/                     ← another immutable slot
    │   └── venv/Scripts/python.exe
    ├── v1.1.0/                     ← kept for rollback
    └── active-runtime.json         ← single atomically-replaced pointer
```

### active-runtime.json

```json
{
  "schema_version": 1,
  "version": "1.3.0",
  "pythonPath": ".runtime/v1.3.0/venv/Scripts/python.exe",
  "activatedAt": "2026-07-14T12:00:00Z",
  "previousVersion": "1.2.3",
  "previousPythonPath": ".runtime/v1.2.3/venv/Scripts/python.exe"
}
```

The resolver reads `active-runtime.json` to find the active Python. This is the **only** pointer -- no symlinks, no directory renames, no magic. On all platforms, write-temp-file + rename is atomic (NTFS, APFS, ext4 guarantee it for same-volume file renames).

### Immutability invariant

A version slot, once verified, is **never modified**. This eliminates the rename-fragility problem entirely:

- **Upgrade**: builds `v1.3.0/`, verifies, writes `active-runtime.json`. Old slot intact.
- **Rollback**: rewrites `active-runtime.json` pointing at existing old slot. No data moves.
- **Force rebuild**: builds `v1.3.0_build2/` (disambiguated path), verifies, rewrites pointer. Old slot retained for cleanup.
- **Interrupted write**: old `active-runtime.json` content still references a valid slot. No partial state possible.

### Install flow (no directory renames)

1. `resolvePython()` -- find bootstrap Python (system or validated download)
2. `python -m venv .runtime/v{version}/venv/`
3. `pip install paperforge=={version}`
4. Verify with `python -I -c "import paperforge; print(__version__)"`
5. Pass → atomically write `active-runtime.json` (write temp, rename)
6. Fail → delete slot directory, return needs_repair

### Cleanup

Old slots beyond keep limit (default: 2) deleted on next successful `ensure()`. Safe because the pointer no longer references them.

---

## Bootstrap Fallback: Release-Owned Artifact Matrix

### Preferred: system Python

```python
resolvePython():
  1. Manual override (settings.python_path)
  2. Windows: py -3.10 → py -3 → registered Python paths
     macOS:   /usr/bin/python3 → which python3
     Linux:   /usr/bin/python3 → $PATH python3
  3. Validate >=3.10, validate import venv
```

### Conditional fallback: release-validated artifacts

`allowAutoDownload` downloads python-build-standalone from the **same GitHub Release** that ships the plugin. This is not an unconditional promise -- the release pipeline must validate each triplet:

| Triplet | Artifact status | macOS signing | Release gate |
|---|---|---|---|
| win-x64 | Published, checksummed, CI-smoke-tested | N/A | Passed |
| macos-x64 | Published, checksummed, CI-smoke-tested | Required | Gate: signed artifact |
| macos-arm64 | Published, checksummed, CI-smoke-tested | Required | Gate: signed artifact |
| linux-x64 | Published, checksummed, CI-smoke-tested | N/A | Passed |
| win-arm64 | Not available from upstream | N/A | Not validated |
| linux-arm64 | Published, not CI-smoke-tested | N/A | Not validated |

A triplet is "validated" when CI: downloads python-build-standalone, creates venv, pip-installs paperforge, runs `python -I -c "import paperforge; print(__version__)"`, and records the download SHA-256 in a release-owned checksums file.

### Fallback decision tree

```
No system Python found
  ├─ Triplet validated, checksums match → auto-download → proceed
  ├─ Triplet validated, no network → NO_PYTHON: "Retry when online"
  ├─ Triplet not validated (win-arm64 etc.) → NO_PYTHON: "Install Python 3.10+ manually"
  └─ Validated but CI smoke test failed this release → FALLBACK_UNAVAILABLE
```

### Platform notes

| OS | Notes |
|---|---|
| Windows | `py -3.10` launcher preferred. LongPathsEnabled may be needed for deep vault paths. |
| macOS | System Python shipped since 12.3. Release must either notarize the downloaded binary or document that users will need right-click → Open. **macOS signing is a release gate**, not assumed solved. |
| Linux | python3-venv is separate on Debian/Ubuntu. Flatpak/Snap may restrict vault write access. |

---

## Compatibility Gate

Before touching `.runtime/`, `ensure()` runs three checks:

1. Bootstrap Python >= 3.10. Fail → `PYTHON_TOO_OLD`.
2. `python -c "import venv"` succeeds. Fail → `VENV_MISSING_MODULE`.
3. Requested version is compatible with plugin manifest. Fail → `INCOMPATIBLE_VERSION` (indicates broken release, should not happen).

Any gate failure returns `needs_repair`, leaving `.runtime/` untouched.

---

## Atomic Activation Protocol

| Phase | Action | Failure mode | State after |
|---|---|---|---|
| 1 | Bootstrap resolution | No bootstrap found | No change to .runtime/ |
| 2 | Compatibility gate | Python <3.10, no venv | No change |
| 3 | Build slot: venv + pip | Network, subprocess crash | Incomplete slot deleted, needs_repair |
| 4 | Verify: `python -I -c "import paperforge"` | Import fails | Slot deleted, pointer unchanged |
| 5 | Write pointer: temp + rename | Crash mid-rename | Old pointer intact or new pointer valid |
| 6 | Cleanup old slots (best-effort) | Crash during delete | Extra slot remains, cleaned next time |

---

## Failure Matrix

### Bootstrap failures

| Code | Detection | State | Action |
|---|---|---|---|
| `NO_PYTHON` | No system Python, no validated triplet | unavailable | "Install Python 3.10+ from python.org" |
| `NO_PYTHON_AUTO` | No system Python, validated triplet, auto-download on | installing | Automatic |
| `FALLBACK_UNAVAILABLE` | Triplet not validated or CI test failed | unavailable | Manual Python install |
| `PYTHON_TOO_OLD` | Python <3.10 | needs_repair | Upgrade Python or set python_path |
| `VENV_MISSING_MODULE` | `import venv` fails | needs_repair | Install python3-venv |

### Installation failures

| Code | Detection | Recovery |
|---|---|---|
| `VENV_FAILED` | venv creation fails | Retry once; show error |
| `PIP_FAILED` | pip install fails | PyPI → git+https fallback |
| `NETWORK_UNAVAILABLE` | pip timeout | Retry next ensure(); offline badge |
| `MAX_PATH` | ENAMETOOLONG on Windows | Shorten vault path or enable LongPathsEnabled |

### Runtime failures (detected by probe)

| Detection | State | Recovery |
|---|---|---|
| Interpreter missing at pointer path | needs_repair | ensure() installs |
| import paperforge fails | needs_repair | ensure({force: true}) builds fresh slot |
| Version mismatch | needs_repair | ensure({version}) upgrade or rollback |
| Cache stale, no probe | unknown | Probe with status() |

---

## Offline Behavior

| Operation | Online | Offline |
|---|---|---|
| status() / probe | Full | Full (local by nature) |
| ensure() when ready | Verify + return | Same |
| ensure() not_installed | Pip + maybe fallback download | NETWORK_UNAVAILABLE |
| ensure() needs_repair | Pip reinstall | NETWORK_UNAVAILABLE |
| Rollback (old slot exists) | Rewrite pointer | Same (local file write) |

Ready runtime works fully offline. Only install/repair/upgrade need network.

---

## Security

- Bootstrap Python path never stored -- only venv path from `active-runtime.json`.
- Network only during: pip install from PyPI/GitHub, conditional fallback download from same GitHub Release.
- No credentials through ManagedRuntime. API keys in existing storage.
- No system-wide Python modifications -- everything inside `.runtime/v{ver}/venv/`.
- Only commands executed: `python -m venv`, `pip install`, `python -I -c "import paperforge"`.
- Downloaded binary verified via SHA-256 from release-owned checksums file.
- `status()` returns version metadata and state codes only -- no log contents, no secrets.

---

## Migration from Current Setup

### Phase 0: Add ManagedRuntime alongside existing resolvers (Release N)

New file `plugin/src/services/managed-runtime.ts`. `status()` reads `active-runtime.json`; if absent, falls back to current resolver. `ensure()` delegates. No functional change.

### Phase 1: Adopt in setup wizard (Release N+1)

Replace RuntimeInstaller with `runtime.ensure()`. New installs use managed runtime. Existing users get one prompt.

### Phase 2: Consolidate resolvers (Release N+2)

| Old function | Replaced by |
|---|---|
| `resolvePythonExecutable()` | `runtime.current().pythonPath` (sync, fails closed) |
| `getCachedPython()` | `runtime.current().pythonPath` |
| `getVectorRuntime()` venv search | `runtime.current().pythonPath` |
| `checkRuntimeVersion()` | `runtime.current().version` |
| `buildRuntimeInstallCommand()` | `runtime.ensure({version})` |

Remove `_cachedPython`. Remove duplicated venv candidate arrays.

### Phase 3: Wire into update flow (Release N+2)

`_autoUpdate` calls `runtime.ensure({version: latest})` instead of its own PyPI-to-git path.

### Phase 4: Decommission (Release N+3)

Remove old resolvers, `checkRuntimeVersion`, `buildRuntimeInstallCommand`, `_autoUpdate` inline path. Backward compatible: old paperforge.json without `runtime` section falls back to current resolver. Manual `python_path` continues to take priority.

---

## Acceptance Criteria

1. **status() probes the interpreter**: Runs selected Python with `-I -c "import paperforge; print(__version__)"`. Returns `ready` only on passing probe with correct version. Returns `unknown` when cache stale and no fresh probe run.

2. **unknown is never ready**: Plugin UI never displays unverified result as healthy.

3. **ensure() atomicity**: Interrupted `ensure()` never leaves a dangling pointer or partial slot as active. Either old pointer references a valid slot or new pointer references a verified slot.

4. **Immutable slots**: Once built and verified, a slot directory is never modified. Upgrade builds a new directory.

5. **Rollback via pointer rewrite**: `ensure({version: previous})` rewrites `active-runtime.json`. No directory renaming.

6. **Fallback conditional on validation**: `allowAutoDownload` only succeeds on validated triplets. Unsupported triplets show manual action.

7. **Compatibility gate**: Rejects Python <3.10 before touching `.runtime/`.

8. **Cross-platform pointer atomicity**: Temp-file + rename pattern verified on Windows, macOS, Linux CI.

9. **Single resolver**: After Phase 2, every command dispatch reads from `runtime.current().pythonPath` (sync, fails closed on stale/missing). Callers must await `status()` or `ensure()` first to warm the cache.

---

## Primary-Source Links

| Link |
|---|
| <https://github.com/LLLin000/PaperForge/issues/70> |
| <https://github.com/LLLin000/PaperForge/issues/66#issuecomment-4968837257> |
| <https://github.com/LLLin000/PaperForge/issues/65> |
| <agent://RuntimeVenv>, <agent://RuntimeBundled> |
| <agent://RuntimeSystem>, <agent://RuntimeService> |
| `python-bridge.ts:62`, `memory-state.ts:173,274` |
| `setup_wizard.py:429-865`, `plan.py:19-96`, `main.ts:105-137` |
| <https://github.com/astral-sh/python-build-standalone> |
| <https://docs.astral.sh/uv/guides/install-python/> |

---

*End of research document for Issue #70. Planning artifact only; no production code changed by this document.*
