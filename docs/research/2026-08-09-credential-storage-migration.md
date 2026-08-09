# Cross-Platform Credential Storage & Migration for PaperForge

**Wayfinder ticket:** [LLLin000/PaperForge#141](https://github.com/LLLin000/PaperForge/issues/141)
**Researcher:** CredentialProviderResearch (read-only, source-grounded)
**Versions investigated:** Python `keyring` 25.7.0 (repo commit `7603e7c`, 2026-04-13) · Obsidian SecretStorage API 1.11.4 (2026-01-12) · freedesktop Secret Service API 0.2 draft (2026-04-08)
**Legend:** [REC] = recommendation · [INFERENCE] = inference, not directly sourced

---

## 1. Executive recommendation

Adopt the **Python `keyring` library (≥25) as PaperForge's sole credential authority**, wrapped in a thin module (`paperforge/credentials.py`) exposing exactly four operations: `store`, `retrieve`, `delete`, `status`. Do **not** write custom OS-keychain integration, do **not** ship a plaintext fallback, and do **not** attempt to read Obsidian's SecretStorage from Python.

- **Windows** → `keyring.backends.Windows.WinVaultKeyring` (Credential Manager via `win32cred`, priority 5). Available in interactive user sessions; no lock state; no UI prompts for generic credentials.
- **macOS** → `keyring.backends.macOS.Keyring` (Keychain Services `SecItem*`, priority 5). Works from signed interpreters; the two failure modes to surface are a **locked keychain** and an **unsigned interpreter** (`SecAuthFailure -25293` / `errSecMissingEntitlement -34018`).
- **Linux** → Secret Service first (`SecretService.Keyring` priority 5 via `secretstorage`; `libsecret.Keyring` priority 4.8), KWallet only on KDE. **A secure keyring is NOT guaranteed on Linux**: when no daemon is on the session bus, keyring raises `NoKeyringError` — that is the designed, loud failure, never a silent plaintext fallback.
- **Obsidian → Python migration** is user-mediated only: PaperForge prompts once (getpass or stdin pipe, echo off), writes the value to the OS keyring, read-back verifies, and never writes the value to disk, argv, environment, or logs.
- **Fallback policy:** `NoKeyringError`/`KeyringLocked` → actionable remediation message + non-zero exit. CI/test override is the documented `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring` (an explicit developer choice, not a default).

## 2. Platform evidence

### Windows — Credential Manager

- keyring's `WinVaultKeyring` uses `win32cred.CredWrite/CredRead/CredDelete` with `CRED_TYPE_GENERIC`; persistence defaults to `CRED_PERSIST_ENTERPRISE` and multi-user simulation stores `{username}@{service}` on collision ([Windows.py L31-32, L48-80](https://github.com/jaraco/keyring/blob/main/keyring/backends/Windows.py)).
- Microsoft's [CredWriteW reference](https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credwritew) states the credential "is associated with the logon session of the current token" and returns `ERROR_NO_SUCH_LOGON_SESSION` when "Network logon sessions do not have an associated credential set."
- Credentials are "saved in special encrypted folders on the computer under the user's profile" ([Windows Vault & Credential Manager, Microsoft Learn](https://learn.microsoft.com/en-us/windows-server/security/windows-authentication/credentials-processes-in-windows-authentication)).
- **No lock state and no unlock code path** exist in the backend (it imports no `KeyringLocked`); same-user, same-session reads never prompt. Windows failure modes are environmental: network-logon sessions (some CI/service contexts) and services without a loaded user profile.

### macOS — Keychain

- Backend calls `SecItemAdd/SecItemCopyMatching/SecItemDelete` with `kSecClassGenericPassword` ([macOS/api.py](https://github.com/jaraco/keyring/blob/main/keyring/backends/macOS/api.py)); the keychain is "an encrypted database stored on disk" ([Apple: Keychain items](https://developer.apple.com/documentation/security/keychain-items)).
- Error mapping (from source): `errSecInteractionNotAllowed -25308` (locked keychain with UI disabled — SSH/headless), `keychain_denied -128` → **`KeyringLocked`**, `sec_auth_failed -25293` / `plist_missing -67030` → `SecAuthFailure` **"make sure executable is signed with codesign util"** ([api.py L17-22, L112-126](https://github.com/jaraco/keyring/blob/main/keyring/backends/macOS/api.py); [macOS/__init__.py L49-67](https://github.com/jaraco/keyring/blob/main/keyring/backends/macOS/__init__.py)).
- The codesign failure is observed in the wild: [conda/conda#11808](https://github.com/conda/conda/issues/11808) ("Security Auth Failure: make sure python is signed with codesign util") and [Ultimaker/Cura#9765](https://github.com/Ultimaker/Cura/issues/9765); unsigned binaries also hit [errSecMissingEntitlement −34018](https://developer.apple.com/documentation/security/errsecmissingentitlement) per Apple.
- macOS keychains support explicit lock/unlock, settings, and per-app ACLs ([Apple: Keychains](https://developer.apple.com/documentation/security/keychains)). keyring's own security note: **any script on the same Python executable can read back keyring-created secrets without prompting**; users can restrict via Keychain Access → Access Control ([README L449-458](https://github.com/jaraco/keyring/blob/main/README.rst)). `KEYCHAIN_PATH` env var selects an alternate keychain file ([macOS/__init__.py L29-30](https://github.com/jaraco/keyring/blob/main/keyring/backends/macOS/__init__.py)).

### Linux — Secret Service (GNOME et al.)

- Viability requires the daemon to be running or activatable: *"The Secret Service daemon is neither running nor activatable through D-Bus"* → `RuntimeError`, excluding the backend from detection ([SecretService.py L44-47](https://github.com/jaraco/keyring/blob/main/keyring/backends/SecretService.py)).
- Spec: collections expose `READ Boolean Locked`; locked items' secrets "cannot be accessed" and locked collections "cannot be modified"; the service may re-lock "at any time" ([freedesktop Secret Service: Locking and Unlocking](https://specifications.freedesktop.org/secret-service/latest/unlocking.html); [Collection interface](https://specifications.freedesktop.org/secret-service/latest/org.freedesktop.Secret.Collection.html)).
- Unlock may return a Prompt object (master-password dialog) "displayed by the service on behalf of the client application"; user or client dismissal cancels the operation ([freedesktop Secret Service: Prompts](https://specifications.freedesktop.org/secret-service/latest/prompts.html)). A still-locked collection/item after unlock maps to **`KeyringLocked`** ([SecretService.py L66-75](https://github.com/jaraco/keyring/blob/main/keyring/backends/SecretService.py); same pattern in [libsecret.py](https://github.com/jaraco/keyring/blob/main/keyring/backends/libsecret.py)). Headless ⇒ no prompt agent ⇒ `KeyringLocked`, not a hang.

### Linux — KWallet (KDE)

- Targets `org.kde.kwalletd5`/`/modules/kwalletd5`, priority 5.1 on KDE / 4.9 otherwise; requires `dbus-python`; viability requires the bus name to be **both** owned and activatable ([kwallet.py L36-53](https://github.com/jaraco/keyring/blob/main/keyring/backends/kwallet.py)). Unlock cancel → `KeyringLocked`; set/delete cancel → `PasswordSetError`/`PasswordDeleteError` "Cancelled by user" (L109-110, L128-129).
- **KWallet 6 is a known weak spot:** v25.7.0's viability change regressed it — [issue #734 "25.7.0 stopped working with KWallet6"](https://github.com/jaraco/keyring/issues/734) — and true kwalletd6 support is still an open experimental PR ([#738](https://github.com/jaraco/keyring/pull/738)). [REC] Best-effort on KDE; prefer the Secret Service backend on Plasma 6.

### Headless / CI behavior

- Detection is fully environment-driven: `_detect_backend = load_env() or load_config() or max(viable by priority, default=fail.Keyring())` ([core.py L96-112](https://github.com/jaraco/keyring/blob/main/keyring/core.py)). On headless Linux the winner is `fail.Keyring` (priority 0) → every operation raises `NoKeyringError` with remediation text ([fail.py](https://github.com/jaraco/keyring/blob/main/keyring/backends/fail.py)); `null.Keyring` (priority −1) silently returns `None` ([null.py](https://github.com/jaraco/keyring/blob/main/keyring/backends/null.py)).
- Official headless recipes: `dbus-run-session` + `gnome-keyring-daemon --unlock` (password from stdin; `--foreground` to block) and Docker with `--privileged` to avoid "Operation not permitted" ([README L331-372](https://github.com/jaraco/keyring/blob/main/README.rst); [gnome-keyring-daemon(1)](https://manpages.debian.org/unstable/gnome-keyring/gnome-keyring-daemon.1.en.html)).
- CI gotcha: tox filters env by default — `DBUS_SESSION_BUS_ADDRESS` (plus `DISPLAY`/`WAYLAND_DISPLAY` for pinentry) must be passed through, or keyring reports "No recommended backend was available" ([README L382-395](https://github.com/jaraco/keyring/blob/main/README.rst)).
- macOS CI on unsigned Python → `SecAuthFailure`; Windows CI under a network-logon service account → `ERROR_NO_SUCH_LOGON_SESSION`. [REC] PaperForge CI: null backend for unit tests + one real-store integration test per OS (keyring ships [`keyring.testing.backend.BackendBasicTests`](https://github.com/jaraco/keyring/blob/main/keyring/testing/backend.py)).

## 3. Provider precedence (environment variables, from source)

1. `PYTHON_KEYRING_BACKEND` (fully-qualified backend class) — highest, `load_env()` ([core.py L150-155](https://github.com/jaraco/keyring/blob/main/keyring/core.py)).
2. `keyringrc.cfg` (`[backend] default-keyring=`), stored at the platform config root: Windows `%LOCALAPPDATA%\Python Keyring`; Linux `$XDG_CONFIG_HOME`/`~/.config/python_keyring`; macOS uses the Unix branch ([platform_.py](https://github.com/jaraco/keyring/blob/main/keyring/util/platform_.py)).
3. Auto-detection among viable backends by `priority`; `ChainerBackend` (priority 10 when ≥2 positive-priority backends) reads/writes through all of them ([chainer.py L19-33](https://github.com/jaraco/keyring/blob/main/keyring/backends/chainer.py)).
4. `KEYRING_PROPERTY_{NAME}` env vars set backend attributes at construction — e.g. `KEYRING_PROPERTY_KEYCHAIN` (macOS keychain file), `KEYRING_PROPERTY_APPID` (Secret Service app id) ([backend.py L183-190](https://github.com/jaraco/keyring/blob/main/keyring/backend.py)).
5. `KEYCHAIN_PATH` (macOS), `XDG_DATA_HOME`, `XDG_CONFIG_HOME`, `LOCALAPPDATA` (paths).
6. CLI overrides: `keyring -b <backend>` / `-p <path>`.

[REC] PaperForge precedence: **user prompt/stdin input > OS keyring lookup > fail with remediation**. Environment-sourced secrets only via an explicit `--from-env` opt-in for CI, because env vars are readable via `/proc/<pid>/environ` and leak into shell history and CI logs.

## 4. Migration protocol (Obsidian SecretStorage → Python keyring)

Obsidian 1.11.4 (2026-01-12) added a **Keychain settings section** and the opt-in **SecretStorage API** (`getSecret(id): string | null`, `listSecrets()`, `setSecret(id, secret)`) plus the `SecretComponent` settings widget ([changelog](https://obsidian.md/changelog/2026-01-12-desktop-v1.11.4/), [SecretStorage API reference](https://docs.obsidian.md/Reference/TypeScript+API/SecretStorage)). The official [guide](https://docs.obsidian.md/plugins/guides/secret-storage) establishes the contract: plugin settings store the secret **name**, the value is fetched at runtime via `app.secretStorage.getSecret(name)`, and "the actual secret is stored in local storage, keyed to the specific vault"; `getSecret` returns `null` when absent ([getSecret signature](https://docs.obsidian.md/Reference/TypeScript+API/SecretStorage/getSecret)). **No `deleteSecret` exists in the documented API** (exactly three methods) — deletion is UI-only via Settings > Keychain [INFERENCE: absence in the API reference].

Handshake — the value never leaves the machine:

1. `paperforge secrets migrate --from obsidian <name>` prints: *"Your token currently lives in Obsidian's vault-local secret storage, which PaperForge cannot read. Open Obsidian → Settings → Keychain, copy the value, then paste it below (input is hidden)."*
2. Capture once via `getpass` (echo off) or a stdin pipe — never argv, env, files, or logs.
3. `keyring.set_password("paperforge", <provider>, value)` → read-back verify → print only the provider name and a masked fingerprint (e.g. `token saved for 'openai' (starts with sk-***)`).
4. Optionally instruct deleting the Obsidian copy in Settings → Keychain (only if no other plugin references it).
5. Idempotent: re-running overwrites (`set_password` replaces; Secret Service `CreateItem replace=true` per the [spec](https://specifications.freedesktop.org/secret-service/latest/org.freedesktop.Secret.Collection.html)).

Rejected migration paths: reading Obsidian's storage directly (internal/encrypted Electron storage, vault-keyed — fragile and strictly more exposure) and env-var handoff (process-list leak).

## 5. Minimal PaperForge contract

```python
# paperforge/credentials.py — sole interface (keyring>=25, pinned)
SERVICE = "paperforge"            # stable service name, visible in OS keyring UIs

store(provider, secret) -> None   # input NEVER argv/env/logs; set + read-back verify;
                                  # cleanup partial writes on failure
retrieve(provider) -> str | None  # keyring.get_password; None = absent
delete(provider) -> bool          # keyring.delete_password; False if absent
status() -> dict                  # backend module, priority, ok, environment hints

# env handling (called before first keyring import):
#   PAPERFORGE_KEYRING_BACKEND        -> passthrough to PYTHON_KEYRING_BACKEND
#   PAPERFORGE_SECRET_ENV_<PROVIDER>  -> opt-in CI env secret (prints a warning)
```

CLI surface: `paperforge secrets set|get|del|status|doctor [--stdin] [--from-env <PROVIDER>] [--json]`; `get` masks output; exit codes 0 / 1 (missing) / 2–5 (failure classes below).

**Failure UX:**

| Exception | Meaning | PaperForge message (exit) |
|---|---|---|
| `NoKeyringError` | no secure store available | "No secure credential store is available. On Linux install/start a Secret Service daemon (gnome-keyring) in a desktop/D-Bus session, or set PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring in CI." (2) |
| `KeyringLocked` | keychain/keyring locked or unlock dismissed | "Your OS keychain/keyring is locked. Unlock it and retry." (3) |
| `PasswordSetError` / `PasswordDeleteError` | store refused / not found | Backend message verbatim (contains no secret) (4) |
| `SecAuthFailure` | unsigned interpreter | "Your Python isn't code-signed for Keychain access — use a signed Python (python.org/Homebrew)." (5) |

Noninteractive rule: if stdin is not a TTY and no piped input is present, fail with a clear error — never prompt-loop. These mirror the CLI semantics of the keyring tool itself: `set` reads a pipe when not a TTY, otherwise `getpass`, and never argv ([cli.py L186-194](https://github.com/jaraco/keyring/blob/main/keyring/cli.py)); `get` exits 1 when missing ([cli.py L128-132](https://github.com/jaraco/keyring/blob/main/keyring/cli.py)); `diagnose` prints config path + data root ([cli.py L159-163](https://github.com/jaraco/keyring/blob/main/keyring/cli.py)).

**Redaction rules:** keyring never logs values and its exceptions carry no secret text ([errors.py](https://github.com/jaraco/keyring/blob/main/keyring/errors.py)). PaperForge: no logging/echo of values; getpass with echo off; stdin pipe over env vars; no secrets in argv; masked `get` output. Note the library itself does not encrypt — it delegates to the OS stores (macOS encrypted keychain DB; Windows DPAPI-protected vault; Secret Service encrypted sessions).

**Deletion:** per-backend `delete_password` raises `PasswordDeleteError` when absent (Windows [L63-76](https://github.com/jaraco/keyring/blob/main/keyring/backends/Windows.py); Secret Service/libsecret "No such password!"; KWallet "Password not found"; null = no-op; fail = `NoKeyringError`). Deletion is permanent — require explicit provider-name confirmation.

**Backup/restore:** all three stores are per-user, per-machine, and encrypted with user-level key material; there is no portable export for generic credentials, and Obsidian sync does not carry SecretStorage (vault-local). [REC] Treat the keyring as a convenience cache, not a backup: after OS migration, re-run `paperforge secrets set`; `status` verifies. Never store tokens in vault notes, PaperForge config, or synced settings.

**Explicit unsupported cases:**
1. Linux without a Secret Service daemon (headless servers, minimal containers, WSL without gnome-keyring) → `NoKeyringError`, no plaintext fallback.
2. KWallet 6 / Plasma 6 ([#734](https://github.com/jaraco/keyring/issues/734), experimental [#738](https://github.com/jaraco/keyring/pull/738)) — prefer Secret Service.
3. macOS unsigned or conda Python → `SecAuthFailure -25293` / `errSecMissingEntitlement -34018`.
4. macOS headless SSH (locked keychain, no UI) → `errSecInteractionNotAllowed -25308`.
5. Windows network-logon sessions / services without user profile → `ERROR_NO_SUCH_LOGON_SESSION`.
6. Obsidian SecretStorage programmatic deletion — not in the API.
7. Empty usernames — deprecated in keyring (warning, [issue #668](https://github.com/jaraco/keyring/issues/668)); providers must be non-empty identifiers.

## 6. Rejected alternatives

1. **Direct read of Obsidian's secret store** — internal/encrypted Electron storage, vault-keyed; fragile and more exposure. Rejected.
2. **Plaintext / `keyrings.alt` file backends as default fallback** — documented "alternate, possibly-insecure" backends; contradicts the ticket's "do not assume a secure keyring on every Linux environment". Rejected as default (possible explicit opt-in later, never silent).
3. **Custom D-Bus Secret Service client** — `secretstorage` already implements the spec. Rejected.
4. **Env-var-only credentials** — `/proc/<pid>/environ`, shell history, CI logs. Rejected as default; `--from-env` opt-in only.
5. **Cloud secret managers (Azure Key Vault / 1Password / Bitwarden keyring backends)** — heavy for a local CLI; available later via keyring's entry-point ecosystem. Rejected for this ticket.
6. **Token in PaperForge config or vault notes** — plaintext. Rejected outright.
7. **TPM / Secure-Enclave-only storage** — no cross-platform keyring path. Out of scope.

## 7. Risks / open questions

1. **Obsidian SecretStorage backing store is undocumented** (Electron `safeStorage`? app-local file?) — residual risk of a retained Obsidian copy is unknown [INFERENCE]. Re-verify against Obsidian internals before finalizing user guidance.
2. **KWallet 6 support is in flux** (PR #738 open) — re-check before shipping any KDE-specific guidance.
3. **macOS codesign** depends on PaperForge's Python distribution (python.org/Homebrew signed vs conda vs PyInstaller bundle) — must be validated on the actual shipping artifact.
4. **Windows service / network-logon contexts** are out of the current CLI scope; revisit if PaperForge ever gains a background service.
5. **Parent decision:** whether `get` output is masked even with `--json` (recommended: yes, unless `--raw` is passed explicitly).
6. Defer the optional `keyrings.cryptfile`-style encrypted-file backend for exotic headless Linux — keep fail-loud, revisit on user demand.

## 8. Primary-source bibliography

**Python keyring v25.7.0** ([repo](https://github.com/jaraco/keyring)):
- [core.py L96-112, L150-155](https://github.com/jaraco/keyring/blob/main/keyring/core.py) — backend detection & `PYTHON_KEYRING_BACKEND`
- [backend.py L183-190](https://github.com/jaraco/keyring/blob/main/keyring/backend.py) — `KEYRING_PROPERTY_*`
- [Windows.py L31-32, L63-76](https://github.com/jaraco/keyring/blob/main/keyring/backends/Windows.py); [backends/macOS/__init__.py L29-67](https://github.com/jaraco/keyring/blob/main/keyring/backends/macOS/__init__.py); [backends/macOS/api.py L17-22, L112-126](https://github.com/jaraco/keyring/blob/main/keyring/backends/macOS/api.py); [SecretService.py L44-75](https://github.com/jaraco/keyring/blob/main/keyring/backends/SecretService.py); [kwallet.py L36-53, L109-129](https://github.com/jaraco/keyring/blob/main/keyring/backends/kwallet.py); [null.py](https://github.com/jaraco/keyring/blob/main/keyring/backends/null.py); [fail.py](https://github.com/jaraco/keyring/blob/main/keyring/backends/fail.py); [chainer.py L19-33](https://github.com/jaraco/keyring/blob/main/keyring/backends/chainer.py); [cli.py L128-132, L150-154, L159-163, L186-194](https://github.com/jaraco/keyring/blob/main/keyring/cli.py); [errors.py](https://github.com/jaraco/keyring/blob/main/keyring/errors.py); [util/platform_.py](https://github.com/jaraco/keyring/blob/main/keyring/util/platform_.py)
- [README.rst L280-288 (disable), L331-372 (headless/Docker), L382-395 (tox), L449-458 (macOS security note)](https://github.com/jaraco/keyring/blob/main/README.rst)
- KWallet 6: [issue #734](https://github.com/jaraco/keyring/issues/734), [PR #738](https://github.com/jaraco/keyring/pull/738)

**Obsidian:**
- [Store secrets guide](https://docs.obsidian.md/plugins/guides/secret-storage)
- [SecretStorage API reference](https://docs.obsidian.md/Reference/TypeScript+API/SecretStorage) · [getSecret](https://docs.obsidian.md/Reference/TypeScript+API/SecretStorage/getSecret) · [SecretComponent](https://docs.obsidian.md/Reference/TypeScript+API/SecretComponent)
- [1.11.4 desktop changelog](https://obsidian.md/changelog/2026-01-12-desktop-v1.11.4/)

**Platform / OS:**
- [freedesktop Secret Service: Locking and Unlocking](https://specifications.freedesktop.org/secret-service/latest/unlocking.html) · [Prompts](https://specifications.freedesktop.org/secret-service/latest/prompts.html) · [Collection interface](https://specifications.freedesktop.org/secret-service/latest/org.freedesktop.Secret.Collection.html)
- [gnome-keyring-daemon(1)](https://manpages.debian.org/unstable/gnome-keyring/gnome-keyring-daemon.1.en.html) · [GNOME Keyring wiki](https://wiki.gnome.org/Projects/GnomeKeyring/)
- Apple: [Keychain Services](https://developer.apple.com/documentation/security/keychain-services) · [Keychain items](https://developer.apple.com/documentation/security/keychain-items) · [Keychains](https://developer.apple.com/documentation/security/keychains) · [errSecMissingEntitlement](https://developer.apple.com/documentation/security/errsecmissingentitlement)
- Microsoft: [CredWriteW](https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credwritew) · [Credentials Processes in Windows Authentication](https://learn.microsoft.com/en-us/windows-server/security/windows-authentication/credentials-processes-in-windows-authentication)

**Corroborating real-world failures:** [conda/conda#11808](https://github.com/conda/conda/issues/11808) · [Ultimaker/Cura#9765](https://github.com/Ultimaker/Cura/issues/9765)
