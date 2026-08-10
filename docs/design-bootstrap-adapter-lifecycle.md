# Bootstrap Adapter and Setup/Update/Repair Lifecycle

> Date: 2026-08-09
> Status: **ACCEPTED — ARCHITECTURE FROZEN** (decision [#143](https://github.com/LLLin000/PaperForge/issues/143))
> Research: [#156](https://github.com/LLLin000/PaperForge/issues/156), Reconciliation: [#147](https://github.com/LLLin000/PaperForge/issues/147), Action contract: [#145](https://github.com/LLLin000/PaperForge/issues/145), Progress protocol: [#137](https://github.com/LLLin000/PaperForge/issues/137)

## 0. Core invariant

> **The plugin may create the first runnable Python environment, but once PaperForge can execute, it never again owns runtime lifecycle semantics or canonical runtime publication.**

This is not "ManagedRuntime v2 under a new name": `managed-runtime.ts` is migration source, not target.

```text
            PRE-RUNTIME                          POST-RUNTIME
  Obsidian Bootstrap Adapter                          Python
  discover / platform gate / consent          setup / config / auth
  one-time venv + pip install                 publish pointer.json
  handshake                                   update / repair / probe
        ─────── CUTOVER ───────               #145 actions where faithful
                                               #137 NDJSON
```

## 1. Boundary

| Owner | Owns |
|---|---|
| Plugin (pre-runtime only) | interpreter discovery chain (settings path → vault venvs → `py` launcher → python/python3, absolute paths, PATH enrichment, macOS stub detection); platform gates (Flatpak/Snap unsupported, macOS no interpreter auto-download, python >= 3.11); consent UX; one-time venv creation + one-time pinned install; **pointer read**; handshake/spawn |
| Python (post-cutover, authority) | `paperforge setup` / `update` / `repair`; vault init and config; **pointer publication** (the only writer); future version-slot rollback (deferred); NDJSON emission (#137); action registration where faithful (#145) |
| Never | daemon; persistent control plane; cross-client job takeover; credentials in bootstrap |

The plugin runs venv/pip management **iff the compatibility handshake fails** and never after it passes. Python is never asked to redo discovery decisions the plugin already made (interpreter passed by absolute path).

## 2. Handshake (no new command)

Compatibility = two existing surfaces, no `selfcheck`:

1. Version probe: `python -I -c "import paperforge; print(paperforge.__version__)"` vs `manifest.version`.
2. Capability probe: `paperforge probe installation --json` reporting `ready`.

Compatible = probe reports `ready` AND version matches.

## 3. Canonical runtime location and pointer

```text
~/.paperforge/runtime/
├── venv/          # plugin-first canonical first-install env
└── pointer.json
```

`~/.paperforge` is the existing machine-local PaperForge namespace; no second platform-path rule.

### Pointer contract

```json
{
  "schema_version": 1,
  "python_path": "...",
  "environment_root": "...",
  "paperforge_version": "..."
}
```

- `environment_root` is generic (a python-first install may not run in a venv) — no required `venv_path`.
- No `activatedAt`, `previousVersion`, `previousPythonPath`, `slot`, or `rollback` fields (deferred runtime-manager semantics).
- **Single writer authority: Python.** After cutover, `paperforge setup` atomically publishes `pointer.json` (tmp + `os.replace`); the plugin is a reader only, forever.
- Plugin-first: plugin creates venv + installs → handshake passes → `paperforge setup` publishes the pointer.
- Python-first: `pip install paperforge` + `paperforge setup --headless` publishes the same pointer.
- Both flows converge on one publication authority. Interrupted install ⇒ no pointer publication ⇒ next handshake fails ⇒ UI offers install again, consent required.

## 4. Support matrix (gated, not pre-claimed)

```text
candidate matrix:  win-x64 · macos-x64 · macos-arm64 · linux-x64
supported:         candidate + dependency wheel gate + bootstrap smoke gate
```

- Flatpak/Snap: explicitly unsupported. macOS interpreter auto-download: disabled until signed/notarized artifacts exist.
- **Release verification gate (not a code change):** repo `pyproject.toml` already declares `requires-python = ">=3.11"`; before bootstrap cutover ships, verify the published PyPI metadata reflects `Requires-Python >=3.11` (a stale `>=3.10` on PyPI can make resolvers pick a failing interpreter).
- Wheel + smoke verification for PyMuPDF / ChromaDB / sqlite-vec across the candidate triplets happens before any `supported` claim.

## 5. Python lifecycle verbs

| Verb | Role | Registry binding |
|---|---|---|
| `paperforge setup` | vault initialization (paperforge.json, dir layout, dependency extras) + pointer publication; `--headless` for python-first | `foundation.setup` — only after the seam can express it as `action_id + scope` with no arbitrary args |
| `paperforge update` | package update (pip + git sources; existing `worker/update.py`) | `foundation.update` — note: **not** `foundation.update_python` (that name implies interpreter updates and would collide with a future 3.11 → 3.12 switch) |
| `paperforge repair` | environment repair (existing) | registered when faithful |

### #145 typed-request boundary (critical)

User input for setup belongs to **typed contracts**, never to the generic action runner:

```text
Setup journey
  ├── Python config/auth typed contracts   (config set …, auth set …)
  └── foundation.setup — scope=all, no arbitrary args
```

- `foundation.setup` is registered only when it can faithfully run as `action_id + scope` with zero extra args ("registry contains only operations with a real faithful handler").
- Until then `paperforge setup <typed options>` remains an unregistered typed command.
- **No `client_hint` field is invented.** The plugin's setup journey calls the typed Python config/setup contract directly.

## 6. Failure semantics

- **Interrupted install:** no pointer publication; next discovery/handshake fails; UI offers install again; explicit consent required. No silent retry.
- **Permission failure:** fail loud with actionable platform guidance.
- **Offline:** implementation DEFERed; document `pip --no-index --find-links` / uv offline mechanisms only.
- **Update failure (package still runnable):** `paperforge repair`.
- **Update failure (package unrunnable — `import paperforge` fails):** Python cannot repair itself; fall back to the pre-runtime boundary: handshake fails → bootstrap consented reinstall. The one-time install capability is the **last recovery boundary for an unrunnable runtime** — this is why bootstrap keeps it.
- **Version-slot rollback:** DEFERed to a future Python-side updater; no slots/retention design now.

## 7. managed-runtime.ts — retain / delete

**TS retains:** interpreter discovery; platform gates; consent UX; one-time venv creation; one-time pinned `pip install "paperforge[vector]==<plugin-version>"`; pointer **read**; handshake/spawn.

**TS deletes:** pointer write after cutover; slot management; rollback; cleanup; update; repair; ensure; version retention; runtime-health semantics.

**Python owns:** pointer publication; setup; update; repair; future slots/rollback.

## 8. Credentials, progress, consent

- Bootstrap never touches credentials: no SecretStorage access, no API-token forwarding. Post-setup auth is the #138 credential provider's job.
- setup/update/repair as long tasks use the frozen #137 NDJSON protocol and cancellation state machine.
- **Consent authorizes only the current bootstrap install attempt.** It never pre-authorizes later update/repair actions; each subsequent action follows its own #145 policy/preflight.
