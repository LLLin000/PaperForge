# Desktop Runtime / Recovery Patterns for Managed-Runtime Architecture

**Date:** 2026-07-14
**Issue:** [#68 — Research desktop installation/health/recovery patterns](https://github.com/LLLin000/PaperForge/issues/68)
**Parent map:** [#65 — Make the PaperForge control center self-explanatory](https://github.com/LLLin000/PaperForge/issues/65)
**Input to:** [#70 — Managed-runtime architecture](https://github.com/LLLin000/PaperForge/issues/70)
**Products studied:** VS Code, Docker Desktop, Raycast, Ollama, LM Studio, Homebrew, Obsidian (plugin system), Electron autoUpdater

---

## Executive summary

PaperForge requires a managed runtime architecture that coordinates an Obsidian plugin (TypeScript/Electron) and a Python backend across **安装 / 文献库 / OCR / 记忆 / 维护 / 帮助** modules — each with independent health, recovery, and update semantics. This report studies mature desktop tools to extract patterns that apply to PaperForge's constraints:

1. **Constrained host**: Obsidian plugins run inside an Electron renderer but do not own the host app lifecycle, autoUpdater, or native addon lifecycle. Python backend runs via subprocess or HTTP.
2. **Cross-platform**: Windows, macOS, and Linux all primary.
3. **Two-layer runtime**: TypeScript plugin + Python backend, each with its own lifecycle.
4. **Local-first, privacy-sensitive**: Medical research data; diagnostic export and issue reporting must never leak identifiable content.
5. **Derived-artifact-heavy**: OCR outputs, embeddings, vector indices — disposable but expensive to rebuild.

### Key findings

| Pattern | Observed in | PaperForge fit |
|---|---|---|
| **Independent module health probes** with stable reason codes | VS Code (Runtime Status), Docker Desktop (diagnose), Raycast (Extension Diagnostics) | **Adopt**: Backend capability probes own readiness; plugin renders without reclassification |
| **Extension isolation principle** | VS Code (Extension Bisect) | **Note**: Binary-search isolation is VS Code-specific. PaperForge retains the principle of systematic diagnostic isolation but does not implement a bisect command. |
| **Per-module actionable maintenance, never global OK** | VS Code (per-extension Runtime Status), Raycast (Issue Dashboard per-extension) | **Adopt**: Already aligned with #66 audit finding |
| **Reset with graduated destructiveness** | Docker Desktop (restart → clean/purge data → factory reset) | **Adopt**: Clear three-tier recovery model |
| **Local diagnostic export with user review before issue creation** | VS Code (prefilled Report Issue), Docker Desktop (local diagnose collection, user uploads ID separately) | **Adopt**: User reviews local diagnostic bundle before creating a GitHub Issue draft. No upload service; no opaque ID. |
| **Version pinning / rollback** | Ollama (model tags), VS Code (Install Another Version), Homebrew (pin) | **Adapt**: Tag all model/runtime versions; rollback mechanism to be chosen in #70. Acceptance criteria: restore known-good state. |
| **Separate CLI and GUI diagnostics** | LM Studio (lms CLI + Desktop), Docker Desktop (GUI + CLI diagnose) | **Adopt**: Python CLI diagnostics + plugin diagnostics view |
| **Auto-update with compatibility gate** | Raycast (API version check), VS Code (compatibility check), Electron (Squirrel/MSIX) | **Adopt**: Never force-update the Python runtime or plugin without compatibility verification |
| **JIT model loading with TTL eviction** | LM Studio (JIT Loader + Idle TTL + Auto-Evict), Ollama (single-load scheduler) | **Reject** for \#68 scope (model loading is already handled; revisit if memory pressure becomes a problem) |
| **Setup verification / repair commands** | Homebrew (doctor, update-reset), Docker Desktop (factory reset) | **Adopt**: \`paperforge doctor\` as a unified diagnostic entry point |
| **Plugin update via Obsidian** | Obsidian (manual community plugin update) | **Accept constraint**: PaperForge plugin uses Obsidian's community plugin update flow. Python backend update mechanism chosen in #70. |
| **Rollback via package manager pinning** | Homebrew (pin), Ollama (brew pin / apt-mark hold) | **Note**: Pin pattern prevents accidental upgrades. PaperForge defers rollback mechanism to #70. |

---

## 1. Product deep dives

### 1.1 VS Code (Electron, managed extensions)

**Runtime ownership model:**
- VS Code runs extensions in isolated **Extension Host** processes (Node.js, web, or hybrid). \`extensionKind\` determines placement: \`workspace\` runs on the workspace host, \`ui\` runs near the UI. The host selection prefers Node.js, falls back to web-only hosts. Extensions cannot crash the main editor.
- Source: [Extension Host | VS Code Extension API](https://code.visualstudio.com/api/advanced-topics/extension-host)

**Module health model:**
- The **Runtime Status tab** (Extensions view → extension → Runtime Status) shows per-extension: activation time, activation event, and any warnings/errors. Activation time breakdown (code load / activate call / resolved) has been requested but not yet implemented (\#174255).
- Extensions are lazily activated via **Activation Events** (\`onCommand\`, \`onView\`, \`onStartupFinished\`, etc.) to avoid startup bloat.
- Source: [July 2021 (1.59) — Runtime Status tab](https://code.visualstudio.com/updates/v1_59)

**Update/rollback behavior:**
- **Auto-update:** Extensions update automatically by default (configurable via \`extensions.autoUpdate\`; default delay 2 hours via \`extensions.autoUpdateDelay\`). Auto-update only applies compatible extensions — incompatible ones are held until VS Code itself is updated.
- **Rollback:** Right-click → **Install Another Version** → pick any previous version from the marketplace. CLI equivalent: \`code --install-extension publisher.extension@1.2.3\`.
- **Pin version:** No explicit pin UI, but installing a specific version and disabling auto-update achieves the same effect.
- Source: [Extension Marketplace](https://code.visualstudio.com/docs/configure/extensions/extension-marketplace)

**Repair/reset actions:**
- **Extension Bisect** (Help → Start Extension Bisect): Binary search over enabled extensions to isolate a faulty one in O(log N) steps. Works like \`git bisect\`: answer "Good Now" or "This Is Bad" at each step. First step disables all extensions.
- **Disable all extensions**, **Restart Extension Host** (Developer: Reload Window With Extensions Disabled).
- **Reset VS Code** (via \`--user-data-dir\` switch or resetting settings to defaults).
- Source: [Resolving extension issues with bisect](https://code.visualstudio.com/blogs/2021/02/16/extension-bisect)

**Diagnostic export:**
- **Developer: Show Running Extensions** → copies detailed activation/performance data to clipboard.
- Log level setting, developer console (Chromium DevTools), and \`--verbose\` CLI flag.
- Extension bisect session state can be shared.

**Issue-report flow:**
- **Report Issue** from Help menu → opens browser with pre-filled template (VS Code version, extensions, logs).
- Extensions bisect result can be attached to extension-specific GitHub issues.
- GitHub issue templates in each extension repository.

**Security/privacy boundary:**
- Extensions run in the Extension Host process, isolated from the main VS Code process. Multiple extensions typically share one host.
- Extensions declare capabilities in their manifest but are not individually permission-gated; users approve the extension as a whole, not per-API-call.
- Web extensions run in a tighter sandbox (no Node.js APIs).

**Cross-platform behavior:**
- Extensions host architecture identical across Windows, macOS, Linux.
- Remote extensions (WSL, SSH, Dev Containers) require a window reload after update instead of the local in-process restart.

---

### 1.2 Docker Desktop (VM-based runtime, hybrid native+VM)

**Runtime ownership model:**
- Docker Desktop runs a **Linux VM** (via Hyper-V on Windows, Apple Hypervisor on macOS, a qemu VM on Linux) that hosts the Docker engine and containers. The Desktop app is a native Electron/GUI wrapper that communicates with the VM.
- The VM is owned and managed by Docker Desktop — users do not directly manage it.

**Module health model:**
- **Dashboard** shows: Engine running, containers status, resource usage (CPU/memory/disk), Kubernetes status, extensions status.
- **Settings > Troubleshoot** section groups all health and recovery actions.
- Automatic health checks via \`docker desktop status\` (CLI, v4.60+).
- Source: [Docker Desktop CLI reference](https://docs.docker.com/desktop/features/desktop-cli/)

**Update/rollback behavior:**
- **Auto-update:** Docker Desktop checks for updates automatically; user is prompted to download and install.
- **Rollback:** Manual — download and install a previous version from the release notes page. No built-in rollback command.
- **Channel selection:** Stable, Beta, or Dev release channels.
- Source: [Docker Desktop release notes](https://docs.docker.com/desktop/release-notes)

**Repair/reset actions (three-tier):**

| Tier | Action | What it does | Data loss |
|---|---|---|---|
| 1 | Restart | Restarts Docker Desktop process | None |
| 2 | Clean / Purge data | Removes all containers/images/volumes (reported to also purge volumes — [docker/for-mac#6758](https://github.com/docker/for-mac/issues/6758)) | All container data, images, volumes |
| 3 | Reset to factory defaults | Destroys VM, resets all settings, credentials, Kubernetes data; restores to first-install state | Everything |

- Source: [Troubleshoot Docker Desktop](https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/)

**Diagnostic export:**
- **\`docker desktop diagnose\`** (CLI, v4.60+) collects system info, logs, and configuration into a diagnostic bundle.
- **\`docker desktop diagnose --upload\`** uploads the bundle and returns a **Diagnostic ID** (UUID/timestamp format).
- **In-app:** Troubleshoot > Get support → generates and optionally uploads diagnostics.
- Manual fallback: \`com.docker.diagnose\` binary in the install directory.
- **Log location:** \`$HOME/.docker/desktop/log/\`
- Source: [docker desktop diagnose](https://docs.docker.com/reference/cli/docker/desktop/diagnose/)

**Issue-report flow:**
- Paid users: use Diagnostic ID with Docker Support ticket.
- Free users: **report a GitHub bug** with the Diagnostic ID.
- The diagnostic ID is a reference to an already-uploaded bundle; it reduces what the user pastes into a ticket but does not itself create a privacy boundary.
- Source: [Troubleshoot Docker Desktop](https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/)

**Security/privacy boundary:**
- Docker Desktop runs as a user-level process (not system-wide on modern setups).
- Diagnostics bundle may contain container names, image names, and environment variable _names_ (not values, per the privacy policy).
- **Restricted Mode** (Docker Desktop settings) can disable usage statistics collection.

**Cross-platform behavior:**
- macOS, Windows, and Linux all run Linux containers inside a managed VM; the hypervisor and storage paths differ by platform.
- The **backup/restore** procedure differs per platform: \`docker_data.vhdx\` + WSL distros on Windows; \`Docker.raw\` on macOS/Linux.
- \`docker desktop diagnose\` binary path differs per OS.
- Source: [Backup and restore Docker Desktop data](https://docs.docker.com/desktop/settings-and-maintenance/backup-and-restore/)

---

### 1.3 Raycast (Native macOS desktop, managed extensions)

**Runtime ownership model:**
- Raycast extensions run as **Node.js processes** managed by the Raycast app (AppKit native app). A custom React reconciler translates React updates into native AppKit updates via JSON render tree + JSON Patch diff — extensions run in separate processes, communication happens over the render tree protocol.
- Extensions are distributed through the **Raycast Store**. Version and API compatibility are checked before installation.
- Source: [How the Raycast API and extensions work](https://www.raycast.com/blog/how-raycast-api-extensions-work)

**Module health model:**
- **Extension Diagnostics** command: Shows:
  - Loaded Commands (all currently loaded extensions)
  - Commands with Background Refresh
  - Latest Events (activation, errors)
- **Extension Issues Dashboard** (\`raycast.com/extension-issues\`): Real-time visibility into user-reported errors, with per-issue details (stack trace, breadcrumbs, release dates, environment).
- Source: [Changelog — Extension Diagnostics](https://developers.raycast.com/misc/changelog.md)

**Update/rollback behavior:**
- **Auto-update:** Extensions are auto-updated by Raycast only if compatible with the current Raycast version and API version. Users cannot disable auto-update per extension.
- **Versioning:** Single implicit "latest" version. No version pinning in the store model.
- **Rollback:** Not supported through the official mechanism. Developers must push a fix as a new version.
- **Migration:** Raycast provides automated API migrations and deprecation plans for breaking changes.
- Source: [Versioning — Raycast Developers](https://developers.raycast.com/information/versioning)

**Repair/reset actions:**
- **Restart Raycast** (clear all extension state).
- **Reinstall extension** (uninstall → install).
- **Deactivate menu bar commands** without removing them.
- **Force production mode** for dev extensions (Preferences > Advanced > "Use Node production environment").

**Diagnostic export:**
- **Extension Diagnostics** command (built-in).
- **Developer tools:** DevTools-accessible via React DevTools.
- **Console logs** (development only; disabled for store extensions).
- **Error overlay** in-app for unhandled exceptions/Promise rejections (production shows a generic message).

**Issue-report flow:**
- **Extension Issues Dashboard** aggregates all user-reported errors by extension.
- For developers: per-issue details include stack trace, breadcrumbs, release dates, environment.
- No user-initiated issue creation flow — errors are auto-captured.

**Security/privacy boundary:**
- Extensions are sandboxed (no filesystem access beyond what the Raycast API provides).
- Environment modes: store extensions run in Node production mode; development extensions run in development mode.
- Console logging disabled for store extensions (privacy-conscious).

**Cross-platform behavior:**
- Currently **macOS only**. No Windows/Linux version.

---

### 1.4 Ollama (Local AI runtime, Go daemon + CLI)

**Runtime ownership model:**
- Ollama is a **Go daemon** (\`ollama serve\`) that manages a **Llama-based model runner** as a child process. The server is a single-binary with embedded model runner.
- **Scheduler** (\`server/sched.go\`): Only one model actively loaded at a time. Load management is single-threaded; already-loaded models handle concurrent requests. GPU-aware placement with eviction/relocation for memory pressure.
- Source: [Ollama server routes.go](https://github.com/ollama/ollama/blob/c42e9d24/server/routes.go), [server/sched.go](https://github.com/ollama/ollama/blob/e09b3f9f/server/sched.go)

**Module health model:**
- **\`ollama ps\`** — list running models with their PID, VRAM usage, and expiration.
- **\`ollama list\`** — list all downloaded models with tags.
- **\`ollama show <model>\`** — detailed model manifest (modelfile, parameters, quantization, digest).
- **Graceful shutdown** on SIGINT/SIGTERM — scheduler cleanup, model unload, server shutdown.
- Source: [Ollama API docs](https://github.com/ollama/ollama/blob/9db4bdbad6a4981ad761aa2b603e69e8fb83212c/docs/api.md)

**Update/rollback behavior:**
- **Binary updates**: Download new binary from [ollama.com](https://ollama.com) — binary replaces previous.
- **Docker**: \`ollama/ollama:0.x.y\` version tags; rollback = restart container with older tag.
- **Package manager**: \`brew pin ollama\` (macOS) or \`apt-mark hold ollama\` (Linux) to pin version.
- **Model pinning**: Always pin quantization tags (\`llama3.2:8b-instruct-q4_K_M\`); floating tags (\`latest\`) can cause silent regressions.
- **Model digest**: Since v0.4.0, models have reliable digest hashes for true rollback verification.
- Source: [Ollama GitHub README — model tags and versioning](https://github.com/ollama/ollama?tab=readme-ov-file#model-library); [Ollama API docs — /api/tags and model management](https://github.com/ollama/ollama/blob/c42e9d24/docs/api.md)

**Repair/reset actions:**
- **Restart daemon** (\`ollama serve\`).
- **Delete and re-pull model**.
- **\`~/.ollama/models\`** — model cache directory; clear individual model blobs to force re-download.
- **Graceful shutdown** handles cleanup of running model sessions.

**Diagnostic export:**
- **\`ollama serve\`** runs with visible logs; log level via environment variable (\`OLLAMA_DEBUG=1\`).
- GPU discovery and VRAM status logged at startup.
- **API endpoints**: \`GET /api/tags\`, \`GET /api/show\`, \`GET /api/ps\` for current state.
- Source: [Ollama server routes.go](https://github.com/ollama/ollama/blob/c42e9d24/server/routes.go)

**Issue-report flow:**
- **GitHub Issues** on [ollama/ollama](https://github.com/ollama/ollama).
- Debug bundle: \`ollama serve\` logs + model manifest + system info.
- Discord community for troubleshooting.

**Security/privacy boundary:**
- Local-only by default; \`OLLAMA_HOST=0.0.0.0\` for network access.
- Models run locally; no telemetry by default.
- No user authentication mechanism.

**Cross-platform behavior:**
- macOS, Windows, Linux — single binary per platform.
- Linux: systemd service file included.
- Windows: installer manages PATH and auto-start.
- Platform differences in GPU detection (CUDA vs Metal vs ROCm).

---

### 1.5 LM Studio (Local AI runtime, Desktop App + daemon + CLI)

**Runtime ownership model:**
- Three-component architecture:
  - **Desktop App**: GUI for interactive use, model discovery, multi-turn chat, RAG, visual config
  - **llmster** (headless daemon): Server-native core, suitable for remote/automated environments
  - **lms** (CLI): Unified control plane for both Desktop and llmster
- Model management: **JIT Loader** (load model on first request), **Idle TTL** (~60 minutes default), **Auto-Evict** (unloads older JIT models to free memory).
- Source: [LM Studio Developer Docs — CLI, daemon, architecture](https://lmstudio.ai/docs/developer)

**Module health model:**
- **\`lms ps --json\`**: List loaded models with state (Loaded / Idle / Auto-Evict).
- **\`lms daemon status\`**: Check daemon health.
- **\`lms server start/stop/status\`**: API server lifecycle management.
- Server modes: GUI mode (inside desktop app) and Headless mode (standalone \`llmster\` process).
- Source: [LM Studio CLI reference — lms ps, lms daemon, model management](https://lmstudio.ai/docs/cli)

**Update/rollback behavior:**
- **Auto-update** within Desktop App (prompts user to download).
- **CLI** (\`lms\`) can update independently.
- **Rollback**: Manual — download previous version from release archives.
- **Model versioning**: No built-in version pinning for downloaded models; rely on Hugging Face commit hashes.

**Repair/reset actions:**
- **Restart daemon** (\`lms daemon restart\`).
- **Reinstall model** (delete and re-download).
- **Clear cache** (\`~/.lmstudio/models\` — manual cleanup).

**Diagnostic export:**
- **\`lms log stream\`**: Real-time log streaming with options:
  - \`--source model\` (default): model IO logs
  - \`--source server\`: HTTP API server logs
  - \`--source runtime\`: runtime logs
  - \`--filter input\`, \`--filter output\`: directional filtering
  - \`--json\`: structured output
  - \`--stats\`: tok/sec and prediction statistics
- **Server logs** stored at \`~/.lmstudio/server-logs\`.
- Source: [lms log stream](https://lmstudio.ai/docs/cli/serve/log-stream), [src/subcommands/log.ts](https://github.com/lmstudio-ai/lms/blob/bf809b57/src/subcommands/log.ts)

**Issue-report flow:**
- **GitHub Issues** on [lmstudio-ai/lms](https://github.com/lmstudio-ai/lms) or lmstudio-ai/lmstudio (private).
- **Discord community**.
- Diagnostic data shared via log stream exports or server-logs directory.

**Security/privacy boundary:**
- API token authentication (optional; \`x-api-key\` header).
- Local-only by default.
- Desktop App and llmster share the same core; data never leaves the machine.
- \`~/.lmstudio/\` config directory contains user settings but no telemetry.

**Cross-platform behavior:**
- macOS, Windows, Linux.
- Desktop App and llmster available on all platforms.
- GPU backend varies by platform (CUDA, Metal, Vulkan).

---

### 1.6 Homebrew (Package manager — included for update/rollback/repair patterns)

**Runtime ownership model:**
- Homebrew is a **Ruby-based package manager**. Formulae (packages) and Casks (GUI apps) are installed into \`/usr/local\` (Intel) or \`/opt/homebrew\` (Apple Silicon) — the **Cellar** for formulae, \`/Applications\` for casks.
- **No daemon**; \`brew\` is invoked as a CLI command.

**Update/rollback behavior:**
- **\`brew update\`**: Updates Homebrew itself and formulae indexes from GitHub.
- **\`brew upgrade <formula>\`**: Upgrades specific formula to latest.
- **\`brew pin <formula>\`**: Prevents a formula from being upgraded.
- **\`brew unpin <formula>\`**: Removes the pin.
- **\`brew switch <formula> <version>\`**: Switch to an installed older version (if multiple versions are keg-only).
- **\`brew update-reset\`**: Destructive — resets Homebrew and taps to origin/master, discarding local changes.
- **Auto-cleanup**: Old versions removed ~30 days after upgrade.
- Source: [Homebrew Manpage](https://github.com/Homebrew/brew/blob/9b56b133a546d0d40cd6b020290f6a59fc14729f/docs/Manpage.md)

**Diagnostic/repair:**
- **\`brew doctor\`**: Checks system for potential problems. Warns with non-zero exit if issues found. Key checks: untracked files in brew repo, stray config files (e.g., \`.curlrc\`), outdated Homebrew, missing dependencies.
- **\`brew missing\`**: Checks for missing formula dependencies.
- **\`brew cleanup -n\`**: Dry-run cleanup of old versions.
- Source: [Homebrew Common Issues](https://docs.brew.sh/Common-Issues)

---

### 1.7 Obsidian plugin system (host environment for PaperForge)

**Plugin runtime:**
- Plugins run as **Electron renderer process JavaScript** (TypeScript compiled to \`main.js\`).
- Plugins have broad access: "they can read files, access the internet, and install other programs" — Obsidian cannot restrict permissions by plugin.
- **Restricted Mode** (default on) disables all community plugins.
- Source: [Plugin security](https://github.com/obsidianmd/obsidian-help/blob/master/en/Extending%20Obsidian/Plugin%20security.md)

**Plugin update mechanism:**
- **No auto-update**: Users must manually go to Settings → Community Plugins → Check for updates → Update individual or all.
- **Manual install**: Download ZIP, extract to \`.obsidian/plugins/<plugin-id>/\`.
- **Beta plugins**: BRAT plugin manages beta updates (can set frozen version).
- Source: [Community plugins](https://obsidian.md/help/community-plugins)

**Plugin review/diagnostics:**
- **Automated scanning** on every plugin version (security, code quality, malware detection).
- **Scorecards** for plugin safety (declared access: network, filesystem, clipboard).
- **Developer tools**: DevTools (Ctrl+Shift+I) for debugging; Hot Reload plugin for auto-reload during development.
- **No built-in diagnostic export** for plugins — rely on console.log and DevTools.
- Source: [The future of Obsidian plugins](https://obsidian.md/blog/future-of-plugins/)

**Key constraint for PaperForge:**
- Obsidian plugin API does not expose Electron's \`autoUpdater\`.
- Plugins can use native Node addons but these carry ABI/packaging risk across Obsidian versions. Python backend runs via subprocess or HTTP.
- No per-plugin permission model — plugins are all-or-nothing.

---

### 1.8 Electron autoUpdater (reference for update architecture)

**Capabilities:**
- **macOS**: Uses Squirrel.Mac (ZIP-based updates via JSON feed).
- **Windows**: Uses Squirrel.Windows (NuGet packages + RELEASES file) or MSIX (direct MSIX/JSON feed with optional \`allowAnyVersion\` for downgrades).
- **Linux**: No built-in updater; use OS package manager.
- Source: [Electron autoUpdater docs](https://github.com/electron/electron/blob/main/docs/api/auto-updater.md)

**Key API:**
\`\`\`javascript
autoUpdater.setFeedURL({ url: 'https://update.example.com/update' });
autoUpdater.checkForUpdates();  // Don't call twice
// Events: 'update-available', 'update-downloaded', 'error', 'checking-for-update'
autoUpdater.quitAndInstall();
\`\`\`

**Rollback:**
- **Squirrel.Windows**: No built-in rollback; uninstall and install old version.
- **MSIX**: Downgrades supported when \`allowAnyVersion: true\` is passed to \`setFeedURL()\`.
- Source: [Electron autoUpdater](https://electronjs.org/docs/latest/api/auto-updater)

---

## 2. Cross-cutting pattern matrix

### 2.1 Runtime ownership models

| Product | Runtime type | Process model | Plugin isolation |
|---|---|---|---|
| VS Code | Electron app | Shared Extension Host process(es) | Process-level isolation (main process separate from host); multiple extensions share a host |
| Docker Desktop | VM + native app | VM managed by GUI; CLI communicates with engine | Container-level; VM is the isolation boundary |
| Raycast | Native macOS app | Separate Node.js processes per extension | Process-level; React reconciler bridges UI |
| Ollama | Go daemon | Single daemon spawns Llama runner subprocess | Subprocess-level; GPU memory is the shared resource |
| LM Studio | Desktop + daemon + CLI | Three-component; shared core library | JIT-loaded model processes with TTL eviction |
| **PaperForge model** | Obsidian plugin + Python backend | Plugin in Electron renderer, Python as subprocess or REST API (decision in #70) | Process-level between plugin and Python |

### 2.2 Module health model comparison

| Product | Health interface | Granularity | Staleness protection |
|---|---|---|---|
| VS Code | Runtime Status tab | Per-extension | Activation time, event, warnings — refreshed on extension reload |
| Docker Desktop | Dashboard + CLI status | Engine, containers, K8s, extensions | Real-time by default |
| Raycast | Extension Diagnostics command | Per-extension commands + Background Refresh | Refreshed on command invocation |
| Ollama | \`ollama ps\` / API | Per-model process | Real-time by polling |
| LM Studio | \`lms ps --json\` | Per-model state (Loaded/Idle/Auto-Evict) | Real-time by polling |
| **PaperForge target** | Backend capability probes → plugin renders | Per-module (安装/文献库/OCR/记忆/维护/帮助) | TTL gate with revision/computed_at per response |

### 2.3 Update / rollback matrix

| Product | Update mechanism | Rollback mechanism | Version pinning |
|---|---|---|---|
| VS Code | Auto-update with 2h delay | Install Another Version (UI/CLI) | Disable auto-update per extension |
| Docker Desktop | Auto-update prompt | Manual download of old version | Release channel selection (stable/beta/dev) |
| Raycast | Auto (implicit, latest only) | Not supported (dev must push fix) | Not supported |
| Ollama | Binary download / Docker tag | Docker tag rollback / brew pin | Model tag pinning + digest verification |
| LM Studio | App auto-update prompt | Manual download of old version | None for models |
| Homebrew | \`brew upgrade\` | None (but \`brew pin\` prevents upgrades) | \`brew pin\` / \`brew switch\` |
| Obsidian plugins | Manual (Check for Updates) | Manual (download old version) | BRAT can freeze version |
| **PaperForge target** | Auto-check compatibility → prompt | Restore previous version; mechanism chosen in #70 | Version metadata tracked; pinning mechanism chosen in #70 |

### 2.4 Repair/reset actions (three-tier model)

| Tier | VS Code | Docker Desktop | Homebrew | PaperForge analog |
|---|---|---|---|---|
| 1 | Reload Window | Restart Docker Desktop | \`brew update\` | Restart plugin / restart Python backend |
| 2 | Extension Bisect | Clean / Purge data | \`brew doctor\` → fix warnings | Module-specific rebuild (OCR redo, re-embed, re-index) |
| 3 | Reset settings / \`--user-data-dir\` | Reset to factory defaults | \`brew update-reset\` / reinstall | Module-scoped destructive reset → recreate module's derived artifacts only; source materials preserved |

### 2.5 Diagnostic export maturity

| Product | Export method | Content | Privacy boundary |
|---|---|---|---|
| VS Code | Show Running Extensions (clipboard) | Extension names, versions, activation times, errors | No PII by default; logs may contain file paths |
| Docker Desktop | \`docker desktop diagnose --upload\` | System info, logs, config; returns opaque Diagnostic ID | ID is shared with support; bundle uploaded first |
| Raycast | Extension Issues Dashboard (server-side) | Stack traces, breadcrumbs, release dates, environment | User reports are auto-captured; developer sees anonymized data |
| Ollama | \`OLLAMA_DEBUG=1\` logs | Model manifest, GPU info, server logs | Local-only |
| LM Studio | \`lms log stream --json\` | Model IO, server logs, runtime logs with tok/sec stats | Local-only; token-level content in logs (user-review before sharing) |
| **PaperForge target** | \`paperforge doctor --export\` | Module capability states, log tail, config (redacted), OCR health | User reviews local diagnostic bundle and redacts before creating a GitHub Issue draft; no upload service |

---

## 3. PaperForge fit analysis

### 3.1 Architectural constraints

PaperForge operates in a unique architectural position:

1. **Constrained host**: Obsidian plugin does not own the host app lifecycle or autoUpdater. Native Node addons carry ABI/packaging risk. Python backend runs via subprocess or HTTP.
2. **Two-layer system** — the TypeScript plugin renders UI and accepts user input; the Python backend does all computational work (OCR, embedding, memory, sync).
3. **Cross-platform required** — Windows, macOS, and Linux all primary.
4. **Privacy-sensitive** — medical research literature, may contain patient data in PDFs.
5. **Derived artifacts are expensive** — full OCR redo on a 30-page paper takes minutes; full re-embed of 500+ papers takes hours.

### 3.2 What works for constrained Obsidian plugin + Python backend

**Patterns that transfer directly:**

| Pattern | Source | How it applies |
|---|---|---|
| Independent module health probes | VS Code, Docker Desktop, Raycast | Each PaperForge module (安装/文献库/OCR/记忆/维护/帮助) has its own capability probe returning state + reason_code + action. Plugin renders without reclassification. |
| Three-tier repair (restart → rebuild → reset) | Docker Desktop | PaperForge: (1) restart Python backend, (2) rebuild single module's derived artifacts, (3) module-scoped destructive reset that rebuilds all derived artifacts for that module while preserving source materials. |
| Local diagnostic export with privacy review | Docker Desktop (diagnostic collection), VS Code (prefilled issue report) | `paperforge doctor --export` generates a local diagnostic bundle; user reviews and redacts before optional GitHub Issue creation. No upload service. |
| Version pinning for runtime | Homebrew (pin), Ollama (brew pin / apt-mark hold) | Version metadata tracked; exact pinning and upgrade mechanism chosen in #70. Upgrade should be explicit, never automatic. |
| Compatibility gate on update | VS Code (compatible extensions only), Raycast (API version check) | Python backend version vs. plugin API version checked before any update is applied. |
| Per-module actionable maintenance | VS Code (per-extension Runtime Status) | Maintenance view shows only modules needing action, with one concrete action per state. No global "everything is fine" indicator. |
| User reviews diagnostic before issue creation | VS Code (prefilled Report Issue), Docker (local diagnose, user reviews before sharing ID) | PaperForge creates a GitHub Issue draft; user reviews and redacts before submitting. |

**Patterns that need adaptation:**

| Pattern | Source | Adaptation needed |
|---|---|---|
| Extension isolation principle | VS Code | PaperForge adopts the principle of systematic fault isolation — ability to toggle between known-good and current state — without implementing a literal binary-search command. |
| JIT model loading with TTL | LM Studio, Ollama | Reject for this scope: it addresses model memory pressure, not runtime installation or recovery. Revisit only if measurements show a problem. |
| Rollback via package manager pin | Homebrew, Ollama | Pin pattern is noted; PaperForge defers runtime management mechanism to #70. |
| Host-app update mechanism | Electron, Obsidian | PaperForge cannot own the Obsidian host updater. Plugin updates follow Obsidian's community-plugin flow; backend update ownership is decided in #70. |

**Patterns to reject:**

| Pattern | Reason for rejection |
|---|---|
| Docker-style VM isolation | Overkill for PaperForge; process-level subprocess isolation is sufficient |
| Single-implicit-latest-version (Raycast store model) | PaperForge needs explicit version pinning for reproducibility |
| Auto-cleanup of old versions (Homebrew 30-day) | Derived artifact rebuild is too expensive to auto-cleanup; must be explicit user action |
| Cross-process AppKit rendering (Raycast) | Not applicable; PaperForge renders in Obsidian's existing UI framework |

### 3.3 Security/privacy boundary implications

PaperForge holds medical research literature that **may contain identifiable patient information** in PDFs. The diagnostic export pattern must be stricter than general desktop tools:

1. **All diagnostic exports are opt-in** — never auto-uploaded.
2. **Diagnostic bundle structure**:
   - **Safe fields** (always included): module capability states, plugin version, Python version, config keys (not values), error codes, log severity counts.
   - **Review-required fields** (user must redact before sharing): log tail lines, paper keys, file paths, environment variable _names_.
   - **Never-included** (stripped by default): environment variable values, paper titles, PDF text, file contents, network request payloads.
3. **GitHub Issue draft** is user-reviewed before submission.

---

## 4. Adopt / Adapt / Reject decisions

### 4.1 Adopt (use as-is with configuration only)

| # | Decision | Evidence | Rationale |
|---|---|---|---|
| A1 | **Independent module capability probes** returning states | VS Code Runtime Status, Docker Desktop dashboard, Raycast Extension Diagnostics | Directly resolves the #66 audit finding. Each module probe owns its health. |
| A2 | **Three-tier repair model** (restart → module rebuild → module reset) | Docker Desktop Troubleshoot tiers | Graduated escalation. Each tier scoped to a single module. T1 is fast and safe; T3 rebuilds all derived artifacts for that module while preserving source materials. |
| A3 | **User reviews diagnostic before GitHub issue creation** | VS Code (prefilled Report Issue), Docker (local diagnose, user shares ID) | Privacy boundary: user sees what will be shared before sharing. PaperForge uses local export + user-reviewed GitHub Issue draft; no upload token service. VS Code's prefilled Report Issue is the closer precedent for the draft pattern. |
| A4 | **Compatibility gate before any update** | VS Code, Raycast | Prevents update-induced breakage. |
| A5 | **Plugin renders backend facts without reclassification** | VS Code Runtime Status, Raycast Dashboard | Backend emits canonical state; plugin renders them. No frontend heuristic. |
| A6 | **Per-module actionable maintenance view** | VS Code, Raycast | Only modules needing action are shown, with exactly one action per state. |
| A7 | **Python CLI diagnostic command** (\`paperforge doctor\`) | Homebrew \`doctor\`, Docker Desktop \`diagnose\`, LM Studio \`lms log stream\` | Unified entry point for health check, log export, and repair. |

### 4.2 Adapt (modify for PaperForge's context)

| # | Decision | Source pattern | Adaptation |
|---|---|---|---|
| D1 | **Version pinning** | Homebrew \`pin\`, Ollama model tags | Version metadata should be tracked for runtime and models. Exact pinning mechanism chosen in #70. |
| D2 | **Diagnostic isolation principle** | VS Code Extension Bisect | Adopt the principle of systematic isolation (known-good vs. current state) without implementing a bisect command. |
| D3 | **Rollback via versioned installs** | VS Code "Install Another Version", Ollama Docker tags | Releases carry version metadata; system tracks previous version identity for rollback. Exact mechanism chosen in #70. |
| D4 | **Diagnostic bundle with privacy tiers** | Docker Desktop \`diagnose\` | Three tiers: safe, review-required, never-included. Schema part of diagnostic contract. |
| D5 | **Two-channel update** (plugin via Obsidian, backend via \`paperforge update\`) | Electron autoUpdater (two-channel), Obsidian manual updates | Independent channels. Plugin: Obsidian flow. Backend update source chosen in #70. |
| D6 | **Idempotent and resumable repair** | Docker Desktop multi-tier, VS Code bisect resumable | Checkpoint state per repair step. Cooperative stop reused from #64. |

### 4.3 Reject (not applicable or counterproductive)

| # | Decision | Reason |
|---|---|---|
| R1 | JIT model loading with TTL eviction (LM Studio/Ollama) | Adds complexity without demonstrated need. Revisit if memory pressure arises. |
| R2 | VM-level isolation (Docker Desktop) | Process-level subprocess isolation is sufficient. |
| R3 | Single-implicit-latest-version store model (Raycast) | PaperForge needs explicit version pinning for reproducibility. |
| R4 | Auto-cleanup of old versions (Homebrew 30-day) | Derived artifact rebuild is too expensive. User explicitly deletes or rebuilds. |
| R5 | Cross-process AppKit rendering (Raycast) | PaperForge renders in Obsidian's existing UI. |
| R6 | Electron autoUpdater integration | Not accessible from Obsidian plugin context. |
| R7 | Per-extension permission model (none exists in Obsidian) | Accept Obsidian's all-or-nothing model; design internal controls to compensate. |

---

## 5. Managed-runtime architecture implications for #70

### 5.1 Runtime identity and command resolver

**Observation across studied products**: VS Code, Docker Desktop, Raycast, Ollama, LM Studio, and Homebrew each expose a single, well-known runtime identity (code binary, docker CLI + app, Raycast app, ollama binary, lms CLI, brew command). The Obsidian plugin host is the exception — it provides no single runtime identity for its plugins.

- VS Code: \`code\` binary with well-defined extension host
- Docker Desktop: \`docker\` CLI + Desktop app
- Raycast: Raycast app owns all extension processes
- Ollama: \`ollama\` serves as both CLI and daemon
- LM Studio: \`lms\` CLI for all runtime control
- Homebrew: \`brew\` command
- Obsidian plugins: each loads in the Electron renderer

**Implication for PaperForge**: The audit finding (#66) that Python and TypeScript resolve conflicting path values must be resolved by selecting **one command runtime**. Two viable models:

1. **Plugin-invokes-Python via subprocess** (current model but with one canonical resolver). Requires: managed Python runtime installation, version pinning, diagnostic endpoint via CLI.
2. **Python-backend-as-service** (REST API from plugin to a local Python HTTP server). Requires: daemon lifecycle management, health check endpoint, port conflict resolution.

**Recommendation**: Let the evidence inform but do not choose for #70. Both models have precedent (CLI: Homebrew, Ollama; Service: Docker Desktop, LM Studio). The evidence supports either.

### 5.2 Module health probe contract

VS Code (Runtime Status), Docker Desktop (Dashboard), and Raycast (Extension Diagnostics) all describe module-health state with a consistent shape:

\`\`\`
module: { state, reason_code, summary, action, revision, computed_at }
\`\`\`

**For PaperForge** (reusing the #66 audit proposal verbatim):

\`\`\`json
{
  "module": "ocr",
  "state": "ready | needs_input | needs_action | running | limited | unavailable | unknown",
  "reason_code": "stable-machine-code",
  "summary": "localized-human-summary-key",
  "action": {
    "id": "configure_ocr",
    "kind": "open_setting | run_command | open_url | create_issue_draft",
    "destructive": false
  },
  "source_revision": "sha256-of-manifest",
  "computed_at": "2026-07-14T12:00:00Z"
}
\`\`\`

Rules (confirmed by cross-product patterns):
- State is **factual**; plugin never infers severity from counts.
- \`unknown\` and stale are **never** success.
- Every \`needs_action\` has **exactly one** primary next action.
- Destructive actions declare data preserved, replaced, and rollback availability.

### 5.3 Update and rollback contract

From VS Code, Ollama, Homebrew, and Electron patterns:

| Operation | Requirement |
|---|---|
| **Discovery** | Expose an explicit update check. Whether checks also run automatically, and at what cadence, is a product decision for #70. |
| **Compatibility gate** | Before any download, verify compatibility: plugin API ↔ backend version, backend ↔ embedding model, schema version ↔ data. |
| **Download** | Atomic download with checksum verification. Resume support for large downloads (models). |
| **Apply** | Plugin follows Obsidian's update flow. Backend application mechanism is chosen in #70 and must be atomic. |
| **Rollback** | Restore previous known-good state. Version metadata tracked to identify candidates. Exact rollback mechanism chosen in #70. |
| **Failure handling** | If update applies but probe returns bad state, auto-suggest rollback. Never leave system in partially-updated state. |

### 5.4 Diagnostic and issue-report contract

From VS Code (prefilled Report Issue) and Docker Desktop (local diagnose → user-reviewed ID sharing):

\`\`\`
paperforge doctor                          # Quick health overview (plugin view)
paperforge doctor --export <path>          # Full diagnostic bundle to local path
paperforge doctor --check <module>         # Single module deep probe
\`\`\`

The report flow:
1. User experiences an issue.
2. User runs \`paperforge doctor --export diagnostics.zip\`.
3. User reviews the diagnostic bundle (auto-redacted for PII) and may redact further.
4. User selects "Create Issue Draft" → opens a pre-filled GitHub Issue draft with a redacted text summary. The user may manually attach the reviewed export file.
5. User reviews the draft and submits manually. No automatic upload; no opaque Diagnostic ID.

### 5.5 Cross-platform compatibility

From Docker Desktop and Ollama (both true cross-platform):

- Python runtime must be managed identically across platforms (mechanism chosen in #70).
- File paths: \`paperforge.json\` uses platform-independent path references resolved by the config resolver.
- Subprocess signals: \`SIGTERM\` for cooperative stop on Linux/macOS; \`stdin\` control line for Windows (confirmed working in #64).
- Diagnostic export: bundle format must be platform-agnostic (JSON + zipped logs).
- Update sources must work across platforms; exact mechanism chosen in #70.

---

## 6. Acceptance criteria PaperForge can reuse

### 6.1 Health probe acceptance

\`\`\`
GIVEN a module (e.g., OCR) that is fully set up
WHEN the capability probe runs
THEN state = "ready", reason_code is stable, action is empty
AND computed_at is within TTL of current time

GIVEN a module with stale derived artifacts
WHEN the capability probe runs
THEN state = "needs_action", reason_code identifies the artifact type
AND action.id is the concrete rebuild command

GIVEN a module that has never been set up
WHEN the capability probe runs
THEN state = "needs_input" or "unavailable"
AND action.id points to the setup command
\`\`\`

### 6.2 Update acceptance

\`\`\`
GIVEN the current backend version is N
WHEN \`paperforge update\` checks for updates
THEN it discovers version N+1 with a compatible API contract
AND the download produces a checksum-verified artifact

WHEN the user rolls back to a previous version
THEN version N is restored
AND all module probes return state that matches version N's known-good state
\`\`\`

### 6.3 Diagnostic export acceptance

\`\`\`
GIVEN a diagnostic export to path X
WHEN the user inspects X
THEN the bundle contains:
  - Module capability states for all 6 modules
  - Plugin version and build metadata
  - Python backend version
  - Configuration keys (NOT values for sensitive fields)
  - Last N lines of log (tagged as "review-required")
  - Reason codes for any non-ready module

GIVEN an export marked "review-required" fields
WHEN the bundle would be uploaded
THEN the user has reviewed and approved the review-required fields
\`\`\`

### 6.4 Repair acceptance

\`\`\`
GIVEN a module in "needs_action" state with a destructive action
WHEN the user triggers the action
THEN the system warns about data that will be replaced and whether rollback is available
AND the action proceeds only after explicit user confirmation

GIVEN a rebuild operation that can be interrupted
WHEN the user sends a stop signal
THEN the current operation completes, and the system records a resumable checkpoint
AND the module state returns to "needs_action" (not "unknown")
\`\`\`

### 6.5 Cross-platform acceptance

\`\`\`
GIVEN operations on Windows, macOS, and Linux
WHEN any health probe, update, repair, or diagnostic operation runs
THEN it produces the same capability envelope structure
AND it succeeds or fails with the same reason codes
AND file paths are platform-independent in diagnostic output
\`\`\`

---

## 7. Unresolved questions

1. **Python calling pattern for #70**: Subprocess vs. REST API? Both precedented. The choice affects health probe design (CLI exit codes vs. HTTP status codes), diagnostic flow, and update mechanism.

2. **Embedding model update frequency**: If PaperForge's embedding model updates monthly, does updating the model count as a "module action" in the 6-module model, or a sub-action of the 记忆 module?

3. **Obsidian plugin submission timing**: The automated scanning pipeline (announced by Obsidian) is rolling out. PaperForge must ensure the diagnostic and issue-report flow does not trigger false positives in the scanner (e.g., plugin making network requests must be declared).

4. **Offline mode**: Not all products handle offline the same way. Docker Desktop, VS Code auto-update, and Raycast need periodic online access for updates. Ollama and LM Studio serve cached models fully offline. PaperForge must document which operations degrade gracefully offline (health probes: yes; updates: no; local diagnostic export: yes).

5. **Rollback data integrity**: Does rollback restore previously downloaded model weights, or does the user re-download from Hugging Face?

---

## Evidence index

| Finding | Source | URL |
|---|---|---|
| VS Code Extension Host isolation | VS Code Extension API docs | https://code.visualstudio.com/api/advanced-topics/extension-host |
| VS Code Runtime Status tab | VS Code 1.59 release notes | https://code.visualstudio.com/updates/v1_59 |
| VS Code Extension Bisect | VS Code blog | https://code.visualstudio.com/blogs/2021/02/16/extension-bisect |
| VS Code Install Another Version / rollback | Extension Marketplace docs | https://code.visualstudio.com/docs/configure/extensions/extension-marketplace |
| Docker Desktop CLI diagnose | Docker Desktop CLI reference | https://docs.docker.com/desktop/features/desktop-cli/ |
| Docker Desktop troubleshoot and reset | Docker Desktop troubleshoot | https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/ |
| Docker Desktop diagnose command | Docker CLI reference | https://docs.docker.com/reference/cli/docker/desktop/diagnose/ |
| Docker Desktop backup/restore | Docker docs | https://docs.docker.com/desktop/settings-and-maintenance/backup-and-restore/ |
| Docker Desktop purge data issue | docker/for-mac#6758 | https://github.com/docker/for-mac/issues/6758 |
| Raycast extension architecture | Raycast blog | https://www.raycast.com/blog/how-raycast-api-extensions-work |
| Raycast extension diagnostics | Raycast changelog | https://developers.raycast.com/misc/changelog.md |
| Raycast debug an extension | Raycast dev docs | https://developers.raycast.com/basics/debug-an-extension |
| Raycast versioning | Raycast dev docs | https://developers.raycast.com/information/versioning |
| Ollama server routes.go | GitHub (source) | https://github.com/ollama/ollama/blob/c42e9d24/server/routes.go |
| Ollama server/sched.go | GitHub (source) | https://github.com/ollama/ollama/blob/e09b3f9f/server/sched.go |
| Ollama API docs | GitHub | https://github.com/ollama/ollama/blob/9db4bdbad6a4981ad761aa2b603e69e8fb83212c/docs/api.md |
| Ollama model tags and versioning | GitHub README | https://github.com/ollama/ollama?tab=readme-ov-file#model-library |
| LM Studio developer docs | lmstudio.ai | https://lmstudio.ai/docs/developer |
| LM Studio API server | lmstudio.ai | https://lmstudio.ai/docs/api |
| LM Studio CLI reference | lmstudio.ai | https://lmstudio.ai/docs/cli |
| LM Studio lms log stream | lmstudio.ai | https://lmstudio.ai/docs/cli/serve/log-stream |
| Homebrew manpage | GitHub | https://github.com/Homebrew/brew/blob/9b56b133a546d0d40cd6b020290f6a59fc14729f/docs/Manpage.md |
| Homebrew common issues | Homebrew docs | https://docs.brew.sh/Common-Issues |
| Obsidian community plugins | Obsidian help | https://obsidian.md/help/community-plugins |
| Obsidian plugin security | GitHub | https://github.com/obsidianmd/obsidian-help/blob/master/en/Extending%20Obsidian/Plugin%20security.md |
| Obsidian future of plugins | Obsidian blog | https://obsidian.md/blog/future-of-plugins/ |
| Electron autoUpdater | Electron docs | https://github.com/electron/electron/blob/main/docs/api/auto-updater.md |
| Electron updates tutorial | Electron docs | https://github.com/electron/electron/blob/main/docs/tutorial/updates.md |
| PaperForge control-center audit | Working tree | \`docs/research/2026-07-14-control-center-contract-audit.md\` |

---

## Appendix: Comparative decision table

| Capability | VS Code | Docker Desktop | Raycast | Ollama | LM Studio | Homebrew | PaperForge target |
|---|---|---|---|---|---|---|---|
| Multi-module runtime | Yes: Ext. Host | Yes: VM+GUI | Yes: processes | No: single daemon | Yes: 3 components | No: single tool | Yes: plugin+Python |
| Per-module health | Yes: Runtime Status | Yes: Dashboard | Yes: diagnostics cmd | Yes: `ollama ps` | Yes: `lms ps` | No: `brew doctor` is global | Yes: capability probes |
| Actionable maintenance | Yes | Yes | Yes | No: manual model management | No: manual model management | Yes | Yes: module-scoped repair |
| Update compatibility gate | Yes | No: manual rollback | Yes | No: binary swap | No: manual | Partial: pin holds version | Required: plugin/backend/model |
| Rollback mechanism | Install Another Version | Manual download | Not supported | Docker/brew pin | Manual download | `brew switch` | Deferred to #70 |
| Diagnostic export | Clipboard | `diagnose --upload` | Issues Dashboard | Debug logs only | `lms log stream` | `brew doctor` text | `paperforge doctor --export` |
| Privacy review before share | Prefilled draft | Partial: uploads before ID sharing | No: auto-captured | Local only | Local only | Local only | User reviews local export and draft |
| Systematic fault isolation | Extension Bisect | None | None | None | None | None | Principle only; no bisect command |
| Cross-platform | Windows/macOS/Linux | Windows/macOS/Linux | macOS | Windows/macOS/Linux | Windows/macOS/Linux | macOS/Linux | Windows/macOS/Linux |
| Offline capable | Most features | Engine is local; updates/support need network | Store checks need network | Cached models | Cached models | Updates need network | Health probes and local diagnosis |
