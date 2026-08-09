# Bootstrap Adapter Lifecycle Research

- Date: 2026-08-09
- Wayfinder ticket: [#156](https://github.com/LLLin000/PaperForge/issues/156)
- Parent map: [#135](https://github.com/LLLin000/PaperForge/issues/135)
- Scope: Plugin bootstrap/setup/update/repair boundary research; no production implementation.

Research date 2026-08-09. Grounding: PaperForge repo master c56d2f6 (plugin `main.ts`, `python-bridge.ts`, `managed-runtime.ts`, `progress-parser.ts`, `commands/probe.py`, `runtime_health.py`, `worker/update.py`, `pyproject.toml`, docs), PyPI metadata, PEP 668, pip/pipx/uv official docs, Apple/electron-builder signing docs, VS Code Python env docs, Obsidian plugin sources (obsidian-ai, Local Runner, sample-plugin#18), uv#16003, Squirrel.Windows, Microsoft MAX_PATH, Python `os.replace`. Labels: [FACT] primary source, [INFERENCE] derived, [REC] decision.

## 1. Destination restated (the boundary)

The plugin bootstrap adapter owns **only** two things: (1) *pre-PaperForge discovery* (find an interpreter, gate platform preconditions) and (2) a *minimal first-install handoff* used **only when the package cannot yet run**. Once a compatible `paperforge` exists, Python owns setup/update/repair/rollback/runtime-slot semantics; the plugin's only remaining duty is spawning Python verbs and rendering #139's versioned NDJSON events. `managed-runtime.ts` (slots, pointer, rollback) is **migration source, not the target** — its slot/pointer concepts feed a future Python-side updater; the plugin-side copy is to be stripped to the thin bootstrap.

## 2. Vertical cutover and the chicken-and-egg boundary (explicit)

**Cutover rule:** the plugin may run venv/pip management **iff the compatibility handshake fails**; it MUST NOT run it once the handshake passes. Python must never be asked to redo discovery decisions the plugin already made (interpreter is passed by absolute path).

```
PLUGIN (pre-runtime, thin)                                        PYTHON (post-cutover, authority)
──────────────────────────────────────                            ────────────────────────────────────
1. discover interpreter (settings path → vault venvs →            
   py -3.11/-3.10/-3 / python3, absolute paths, PATH            
   enrichment, Apple-stub detection) [FACT]                      
2. platform gates: Flatpak/Snap unsupported, macOS               
   no auto-download, python >=3.11 (PYTHON_TOO_OLD) [FACT]        
3. compatibility handshake (see §3):
     ├─ pass ──────────────────────────────►  CUTOVER: record env path in handoff
     │                                        pointer (os.replace); plugin delegates
     │                                        to `paperforge update/repair/doctor` +
     │                                        NDJSON event stream (#139) forever.
     └─ fail (not installed / import error):  ONE-TIME minimal bootstrap:
        python -m venv <canonical user-level dir>;
        pip install "paperforge[vector]==<plugin-version>" [FACT: this exact
        spec already exists in buildRuntimeInstallCommand];
        re-run handshake. Pass → cutover. Fail → present platformAction,
        never silently retry.                                    5. (post-cutover) Python owns venv/package
                                                                   lifecycle: update (worker/update.py pip
                                                                   + git sources [FACT]), repair (paperforge
                                                                   repair [FACT]), future version-slot
                                                                   rollback (DEFER), NDJSON emission (#139),
                                                                   signal-driven cancellation.
```

**Chicken-and-egg resolution:** to run Python's own updater you need a runnable package; the plugin's only job is to reach that first runnable state exactly once. The handoff artifact (env path pointer written via tmp+`os.replace`, atomic [FACT]) stays — it is the plugin↔Python handover, not a runtime manager.

## 3. Smallest compatibility handshake (no new command)

Do NOT add `selfcheck` — it duplicates `probe all` / the installation probe. Handshake = two existing surfaces, both implemented:
1. Version probe: `python -I -c "import paperforge; print(paperforge.__version__)"` vs `manifest.version` — importability + exact version coupling [FACT: checkRuntimeVersion in python-bridge.ts].
2. Capability probe: `paperforge probe installation --json` — schema-v2 envelope with `user_state` (ready / setup_required / action_required / detection_failed), `action_id`, `availability`, `safety_class` [FACT: commands/probe.py, SUPPORTED_MODULES incl. `installation`].
Compatible = probe installation reports ready AND version matches. No new JSON surface, no plugin-side runtime-slot logic.

## 4. ADOPT

| Item | Evidence | Why at this boundary |
|---|---|---|
| Plugin = pre-runtime discovery + minimal first-install only | destination; current plugin already does discovery in `resolvePythonExecutable`/`_resolveBootstrapPython` [FACT] | Keeps adapter thin; runtime semantics stay in Python |
| Discovery chain as-is (settings path → vault venvs → `py` launcher → python/python3; macOS stub detection; GUI PATH enrichment; absolute paths) | python-bridge.ts, managed-runtime.ts [FACT]; VS Code auto-select order venv→system [FACT] | Already the mature order (matches VS Code/pipx/uv discovery); no new engine |
| Platform gates: Flatpak/Snap → FLATPAK_SNAP_UNSUPPORTED; macOS interpreter auto-download disabled until signed/notarized artifacts; python <3.11 → PYTHON_TOO_OLD | managed-runtime.ts [FACT]; Apple notarization doc [FACT]; uv#16003 [FACT] | These are pre-runtime preconditions — exactly the plugin's remit |
| First-install spec pinned: `pip install "paperforge[vector]==<plugin-version>"` | buildRuntimeInstallCommand / ensure() [FACT]; `[vector]` required (openai, sqlite_vec) [FACT] | Repeatable, version-coupled, extras-correct; no floating deps |
| Handoff pointer file via tmp+`os.replace` (atomic same-volume rename) | managed-runtime.ts; os.replace docs [FACT] | Smallest artifact; no symlink/junction (Windows privilege/dangling) [FACT+INFERENCE] |
| Handshake = version probe + `probe installation --json` (existing surfaces) | checkRuntimeVersion; probe.py [FACT] | No duplicated contract |
| Progress: #139 versioned NDJSON wire contract (wire major versions, additive fields, structured errors, stdout/stderr split) | issue #139 (closed research) | Supersedes token lines; token parser is migration source |
| Plugin-first bootstrap (interactive, consent-gated wizard) vs Python-first headless (`pip install paperforge` + `paperforge setup --headless`) kept distinct | INSTALLATION.md, README [FACT] | Two audiences (GUI vs Agent/CLI); never auto-install without explicit action [REC] |
| `paperforge update` (pip + git sources) and `paperforge repair` as the post-cutover verbs | worker/update.py, COMMANDS.md [FACT] | Python owns update/repair today |

## 5. DEFER

| Item | Defer to | Trigger / rationale |
|---|---|---|
| Version-slot rollback (retained slots, pointer previousVersion/previousPythonPath) | Python-side updater (extend worker/update.py with pinned-version slots; managed-runtime.ts as migration source) | Plugin must not own it post-cutover; no observed user need for multi-version retention yet — `paperforge update` + re-run bootstrap covers the failure today [INFERENCE] |
| Offline support (UV_OFFLINE reuse / vendored wheelhouse) | When an offline cohort reports the need | No evidence of offline users; mechanisms are known (uv --offline [FACT], pip --no-index --find-links [FACT]) and can be documented without building |
| Cancellation beyond AbortSignal + kill semantics | #139 implementation | #139 already scopes Windows tree-kill vs POSIX SIGTERM (Local Runner [FACT]); adopt with the NDJSON work |

## 6. REJECT

| Item | Why |
|---|---|
| New `paperforge selfcheck --json` mega-command | Duplicates `probe all` / installation probe — rejected per destination; handshake uses existing surfaces |
| Plugin-side runtime manager as target (managed-runtime.ts slots/rollback/cleanup in plugin) | Destination: Python owns runtime slots; plugin copy is migration source to strip |
| Preferring uv just because it is present | Rejected: adds a required third-party binary and a preference branch; existing chain is sufficient; uv stays a user-level option only |
| Narrowing the support matrix (e.g., dropping win-arm64/linux-arm64 claims) without wheel evidence | Rejected: no wheel evidence gathered; keep 3-OS matrix (win-x64, macos x64+arm64, linux-x64) and verify pymupdf/chromadb/sqlite-vec platform wheels on PyPI before promising or trimming |
| Checksum manifests / activatedAt last-good markers | Rejected: no observed corruption need (destination instruction) |
| Token-line progress as the forward contract | Rejected: #139 versioned NDJSON supersedes; token parser = migration source |
| PyInstaller/cx_Freeze single-binary self-update | In-place replace locked on Windows; per-OS signing; redundant for pure-Python; violates thin-adapter rule |
| zipapp | No isolation; no clean update/rollback |
| conda/miniconda as app runtime | Heavy, admin on Windows, channel/TOS drift; pip solves it |
| CPython embeddable-zip runtime | No pip/venv; re-implements package management |
| electron-updater/Squirrel for the Python side | Targets packaged Electron payloads (Squirrel.Mac/NSIS/AppImage) [FACT]; Python runtime is not in the Electron bundle; NSIS fights non-installed content (electron-builder#7868) |
| `pip install --user` / `--break-system-packages` | PEP 668 blocks on Ubuntu 23.04+/Debian 12+/Fedora 38+ [FACT]; poisons system env; no rollback |
| Distro packaging (deb/rpm/AppImage/Flatpak/Snap) as primary channel | Maintainer burden, version skew, Flatpak/Snap break subprocess/PATH; PyPI wheel is universal |
| Symlink/junction runtime pointers on Windows | Privilege/Developer Mode; dangling junctions; pointer file is strictly simpler |
| Auto-downloading interpreters on macOS | Unsigned interpreters killed at launch (uv#16003 [FACT]); python.org/Homebrew are the sanctioned sources |

## 7. Open questions (carry to implementation tickets)
1. PyPI metadata mismatch (`requires-python >=3.10` on PyPI vs `>=3.11` in repo) can make resolvers pick a failing interpreter — fix metadata before first-install ships [FACT].
2. Verify pymupdf/chromadb/sqlite-vec wheels for win-x64 / macos-x64 / macos-arm64 / manylinux-x64 before finalizing the matrix.
3. Post-cutover env-path handoff: single canonical user-level venv location for first-install (e.g., `~/.paperforge/runtime/…` or `~/.local/share/paperforge/…`) — pick one; keep pointer schema_version.
4. When Python gains version-slot rollback, the plugin's retained-slot/rollback code is deleted (vertical cutover completes).
5. Flatpak/Snap Obsidian cohort size is unknown — keep the explicit unsupported state, quantify later.

## 8. Primary sources (direct URLs)
PEP 668 — https://peps.python.org/pep-0668/ · pip install — https://pip.pypa.io/en/stable/cli/pip_install/ · pipx (how-it-works / JSON output / standalone-python / install) — https://pipx.pypa.io/stable/explanation/how-pipx-works.html + /reference/json-output.html + /how-to/standalone-python.html + /how-to/install-pipx.html · uv (tools / python-versions / storage / cli) — https://docs.astral.sh/uv/concepts/tools/ + /concepts/python-versions/ + /reference/storage/ + /reference/cli/ · uv#16003 — https://github.com/astral-sh/uv/issues/16003 · Apple notarization — https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution · electron-builder code signing — https://www.electron.build/docs/features/code-signing/ · electron-updater — https://github.com/electron-userland/electron-builder/blob/master/packages/electron-updater/README.md · electron-builder#7868 — https://github.com/electron-userland/electron-builder/issues/7868 · Squirrel.Windows — https://github.com/Squirrel/Squirrel.Windows · MAX_PATH — https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation · os.replace — https://docs.python.org/3/library/os.html · VS Code environments — https://code.visualstudio.com/docs/python/environments · obsidian-sample-plugin#18 — https://github.com/obsidianmd/obsidian-sample-plugin/issues/18 · Local Runner — https://community.obsidian.md/plugins/local-runner · obsidian-ai — https://github.com/spencermarx/obsidian-ai · PaperForge issue #139 (versioned CLI streaming/cancellation) — https://github.com/LLLin000/PaperForge/issues/139 · issue #156 — https://github.com/LLLin000/PaperForge/issues/156 · PyPI paperforge — https://pypi.org/pypi/paperforge/json · PaperForge repo (master c56d2f6) — pyproject.toml; paperforge/plugin/manifest.json; plugin/src/main.ts; services/python-bridge.ts; services/managed-runtime.ts; services/progress-parser.ts; services/embed-build-controller.ts; commands/probe.py; commands/runtime_health.py; worker/update.py; docs/COMMANDS.md; docs/update-upgrade.md; docs/ARCHITECTURE.md; INSTALLATION.md; README.md