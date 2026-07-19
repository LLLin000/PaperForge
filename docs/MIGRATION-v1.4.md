# Migration Guide: v1.3 to v1.4

> This guide covers all breaking changes when upgrading PaperForge from v1.3 to v1.4.
>
> **Who should read this:** Anyone upgrading from v1.3 — whether you installed via `pip install paperforge`, cloned the repo, or use custom scripts referencing worker modules directly.
>
> **Estimated time:** 5-10 minutes to follow the steps, plus time to update any custom scripts or env configurations.

---

## What's New in v1.4

v1.4 is a **code health and UX hardening release**. The core literature pipeline (Zotero sync, OCR, deep reading) is unchanged, but the infrastructure under the hood has been significantly improved.

Key improvements:

- **Structured logging with dual output:** `print()` stays for user-facing formatted stdout (piped commands keep working), while all diagnostic/trace/error messages now go through Python's `logging` module to stderr. A `--verbose`/`-v` flag enables DEBUG-level output for troubleshooting.
- **Resilient OCR with retry:** Transient PaddleOCR API failures (HTTP 429, 502, 503, timeouts) now trigger automatic retry with exponential backoff (1s → 2s → 4s → 8s → 30s max) and jitter. Zombie `processing` jobs older than 30 minutes are automatically reset to `pending` on worker restart.
- **Pre-commit hooks + Ruff:** Automated code quality guardrails via `pre-commit` hooks with Ruff linting and formatting, YAML/TOML validation, end-of-file fixing, trailing whitespace cleanup, and a custom consistency audit hook.
- **Opt-in workflow automation:** `auto_analyze_after_ocr` option in `paperforge.json` — when enabled, OCR completion automatically sets `analyze: true` on the library-record, eliminating the manual step of editing frontmatter between OCR and deep reading.

> **Backward compatibility note:** v1.4 is fully backward-compatible with v1.3 library-records, formal notes, OCR output, and CLI command names. No existing data requires migration. The only changes are to environment variables (new optional vars), developer workflow (pre-commit hooks), and an opt-in automation flag.

---

## Breaking Changes Summary

| Change | Old (v1.3) | New (v1.4) | Impact |
|--------|-----------|-----------|--------|
| Diagnostic output | Mixed `print()` on stdout/stderr | Structured `logging` to stderr | Piped commands unaffected; `--verbose` for debug |
| Log level config | N/A | `PAPERFORGE_LOG_LEVEL` env var (DEBUG/INFO/WARNING/ERROR) | Optional; default is INFO |
| Retry config | No retry on API failure | `PAPERFORGE_RETRY_MAX` (default 5) and `PAPERFORGE_RETRY_BACKOFF` (default 2.0) | Optional; enables automatic retry |
| Pre-commit hooks | None | `pre-commit install` required for developers | New dev dependency (`pip install -e ".[dev]"`) |
| OCR auto-analyze | Manual set `analyze: true` | `auto_analyze_after_ocr` in `paperforge.json` (bool, default false) | Opt-in; no behavioral change by default |
| Progress bars | N/A | `tqdm` progress bars on OCR uploads | Auto-disables in CI/pipe; `--no-progress` to suppress |
| Progress bar control | N/A | `--no-progress` flag on `paperforge ocr` | New optional flag |

---

## Detailed Changes

### 1. Dual-Output Logging

In v1.3 and earlier, the codebase used ad-hoc `print()` calls for all output — user-facing status, diagnostic traces, and error messages. This made it impossible to filter log levels and broke piped command output when diagnostic text appeared on stdout.

**What changed:**

- `print()` is **preserved** for user-facing formatted output on stdout only. Piped commands (`paperforge status | grep ocr`) and Agent scripts that parse stdout remain unmodified.
- `logging.getLogger(__name__)` is used for all diagnostic/trace/error output to **stderr**.
- A `configure_logging(verbose: bool)` function in `paperforge/logging_config.py` configures the root logger.
- Log level defaults to `INFO` (from `PAPERFORGE_LOG_LEVEL` env var) and switches to `DEBUG` when `--verbose`/`-v` is passed.

**New environment variable:**

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `PAPERFORGE_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` | Controls default log level |

**What you need to do:**
- No action required — existing CLI usage works identically.
- To see debug output, add `--verbose` to any command: `paperforge sync --verbose`
- To change default log level, set `PAPERFORGE_LOG_LEVEL=DEBUG` in your `.env` file.

**Why this changed:** Debugging issues required either adding print statements or running Python with `-v` flags. Structured logging with levels, module names, and timestamps makes troubleshooting dramatically easier.

### 2. Retry Behavior

In v1.3, a single PaddleOCR API failure (network timeout, rate limit, server error) would abort the entire batch and mark the paper as `failed`.

**What changed:**

- OCR uploads now retry on transient failures with **exponential backoff**: 1s → 2s → 4s → 8s → 16s → max 30s (with jitter).
- `meta.json` records `retry_count`, `last_error`, and `last_attempt_at` fields after each attempt.
- Zombie `processing` jobs older than 30 minutes are reset to `pending` on worker restart.
- A single OCR upload failure does not abort the entire batch — failed items are logged, state updated, and processing continues.

**New environment variables:**

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `PAPERFORGE_RETRY_MAX` | Integer | `5` | Maximum retry attempts per PDF |
| `PAPERFORGE_RETRY_BACKOFF` | Float | `2.0` | Backoff multiplier |

**What you need to do:**
- No action required — retry is automatic and transparent.
- To customize retry behavior, set `PAPERFORGE_RETRY_MAX=3` or `PAPERFORGE_RETRY_BACKOFF=1.5` in your `.env` or `paperforge.json`.

**Why this changed:** Network failures are inevitable with cloud API calls. Automatic retry with backoff makes OCR runs more resilient without manual intervention.

### 3. Pre-commit + Ruff

v1.4 introduces automated code quality guardrails for developers contributing to PaperForge.

**What changed:**

- `.pre-commit-config.yaml` is active with hooks: `ruff` (lint + format), `check-yaml`, `check-toml`, `end-of-file-fixer`, `trailing-whitespace`, and a custom `consistency-audit` hook.
- Ruff is configured with: line length 120, `E501` suppressed, `per-file-ignores` for pre-existing simplifications.
- Custom consistency audit hook blocks commits if duplicate utility functions are detected in any worker module.

**What you need to do:**

```bash
# Developers must install pre-commit hooks once
pip install -e ".[dev]"
pre-commit install
```

After installation, `git commit` automatically runs all hooks. If hooks fail, the commit is blocked with clear error messages.

**Why this changed:** Without automated guardrails, code quality degrades over time — unused imports accumulate, formatting drifts, and utility functions get copy-pasted across workers.

### 4. auto_analyze_after_ocr

v1.4 introduces an opt-in workflow automation option that reduces manual frontmatter editing.

**What changed:**

- New `auto_analyze_after_ocr` boolean option in `paperforge.json`.
- When `true`: after OCR completes on a paper (status transitions to `done`), the system automatically sets `analyze: true` on that paper's library-record.
- When `false` (default): behavior is identical to v1.3 — user must manually set `analyze: true` in the library-record.

**What you need to do:**
- No action required — default is `false`, preserving the existing manual workflow.
- To enable: add `"auto_analyze_after_ocr": true` to your `paperforge.json`.

```json
{
  "vault_config": {
    "resources_dir": "01_Resources",
    "system_dir": "99_System",
    "agent_config_dir": ".opencode"
  },
  "auto_analyze_after_ocr": true
}
```

**Why this changed:** The OCR → analyze → deep-reading workflow required three manual steps. For power users processing many papers, this automation eliminates one friction point while preserving the Worker/Agent separation — Worker still never triggers Agent automatically.

---

## Migration Steps

Follow these steps in order. Each step is copy-pasteable.

### Step 1: Backup Your Vault

> [!WARNING]
> Always back up your data before upgrading. While v1.4 does not modify your notes or library-records, it's good practice.

```bash
# Option A: Copy the entire vault
cp -r "你的Vault路径" "你的Vault路径-backup-$(date +%Y%m%d)"

# Option B: If using git, commit current state
cd "你的Vault路径"
git add -A
git commit -m "backup before v1.4 upgrade"
```

At minimum, back up these directories:
- `<resources_dir>/` — your literature notes and library-records
- `<system_dir>/PaperForge/ocr/` — OCR results (can be regenerated, but takes time)
- `.env` — your API keys

### Step 2: Update PaperForge

```bash
# If installed via pip
pip install --upgrade git+https://github.com/LLLin000/PaperForge.git

# If installed via git (editable install)
cd "你的Vault路径"
git pull origin master
pip install -e .

# Or use the auto-update command
paperforge update
```

### Step 3: Install Pre-commit Hooks (Developers Only)

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Install hooks
pre-commit install
```

### Step 4: Verify Installation

```bash
# Should show v1.4 in version output
python -m paperforge --version

# Verify logging setup works
paperforge status --verbose

# Verify retry config is available
paperforge ocr --help | grep retry
```

Expected output for `--version`:
```
PaperForge Lite v1.4
```

### Step 5: Configure Optional Features

**Enable auto_analyze_after_ocr (optional):**

Edit your `paperforge.json`:
```json
{
  "auto_analyze_after_ocr": true
}
```

**Configure logging level (optional):**

Add to your `.env`:
```env
PAPERFORGE_LOG_LEVEL=DEBUG
```

**Configure retry behavior (optional):**

Add to your `.env` or `paperforge.json`:
```env
PAPERFORGE_RETRY_MAX=10
PAPERFORGE_RETRY_BACKOFF=1.5
```

### Step 6: Run Smoke Test

```bash
# Run a sync (dry-run mode if available)
paperforge sync

# Check system status
paperforge status
```

---

## Rollback Instructions

If something goes wrong after upgrading to v1.4, you can downgrade to v1.3.

### Option A: Rollback via Git (Recommended if you cloned the repo)

```bash
cd "你的Vault路径"

# Check out the v1.3 tag or branch
git checkout v1.3
# OR
git checkout <commit-hash-of-v1.3>

# Reinstall
pip install -e .
```

### Option B: Rollback via PyPI

```bash
# Uninstall v1.4
pip uninstall paperforge

# Install the last v1.3 release
pip install paperforge==1.3.x
```

Replace `1.3.x` with the specific version you were using.

### What to Watch Out For

**State compatibility:** v1.4 does not change the format of `library-records`, formal notes, or OCR output. If you downgrade to v1.3 after running v1.4:
- Your `library-records` will still work (frontmatter format unchanged)
- Your formal notes will still work
- Your OCR output will still work (v1.4 adds `retry_count`, `last_error`, `last_attempt_at` fields to `meta.json` — v1.3 will ignore them)
- **Pre-commit hooks:** If you ran `pre-commit install`, the hooks remain in `.git/hooks/`. Uninstall them: `pre-commit uninstall`
- **auto_analyze_after_ocr:** v1.3 ignores the `auto_analyze_after_ocr` key in `paperforge.json` — remove it to avoid confusion.

---

## FAQ

### Q: Do I need to reconfigure my vault?

**A:** No. `paperforge.json`, `.env`, directory structure, and all your data remain compatible with v1.4. All changes are additive — new environment variables, new optional flags, new config keys.

### Q: Will my existing notes break?

**A:** No. v1.4 does not modify existing notes or library-records during sync unless you explicitly run `paperforge sync` and new items are detected. Existing notes keep their frontmatter, content, and `## 精读` sections unchanged.

### Q: Will piped commands still work?

**A:** Yes. User-facing output on stdout is unchanged. Piped commands like `paperforge status | grep ocr` continue to work exactly as before. Only diagnostic output (previously mixed on stdout) now goes to stderr.

### Q: What if I don't want retry behavior?

**A:** Set `PAPERFORGE_RETRY_MAX=1` to effectively disable retries. The first failure will mark the paper as `failed`, matching v1.3 behavior.

### Q: What if I don't want progress bars?

**A:** Use `paperforge ocr --no-progress` to suppress the `tqdm` progress bar. Progress bars also auto-disable in CI/pipe contexts.

### Q: I see new log output on my terminal. Is this normal?

**A:** Yes. Diagnostic messages that were previously silent or mixed into stdout now appear on stderr with `[INFO]`, `[WARNING]`, `[ERROR]` prefixes. This is the new structured logging. Run with `paperforge <command> --verbose` to see DEBUG-level detail. If you don't want to see log output at all, set `PAPERFORGE_LOG_LEVEL=WARNING` or `PAPERFORGE_LOG_LEVEL=ERROR`.

### Q: Do I need to install pre-commit hooks?

**A:** Only if you are developing PaperForge (contributing code, running tests). If you are a user who only runs the CLI commands, pre-commit hooks are not required.

### Q: How do I uninstall pre-commit hooks?

```bash
pre-commit uninstall
```

### Q: The automatic `analyze` flag after OCR sounds useful. Will it break my workflow?

**A:** It's opt-in (`auto_analyze_after_ocr: true` in `paperforge.json`). By default, nothing changes — you must still manually set `analyze: true`. When enabled, it only affects papers whose OCR transitions to `done`. Papers you haven't OCR'd are unaffected.

### Q: I get `ModuleNotFoundError: No module named 'tqdm'`.

**A:** v1.4 adds `tqdm` as a dependency. Reinstall with: `pip install -e .` or `pip install paperforge`.

---

## Quick Reference Card

Print this and keep it handy:

```
+---------------------------+-------------------------------+---------------------------+
| Feature                   | v1.3                          | v1.4                      |
+---------------------------+-------------------------------+---------------------------+
| Diagnostic output         | Mixed print() on stdout/stderr| Structured logging stderr |
| Log level env var         | N/A                           | PAPERFORGE_LOG_LEVEL      |
| --verbose flag            | deep-reading, repair only     | All commands (global)     |
| OCR failure handling      | Abort batch, mark failed      | Retry 5x exponential      |
| Retry config env vars     | N/A                           | PAPERFORGE_RETRY_MAX,     |
|                           |                               | PAPERFORGE_RETRY_BACKOFF  |
| Zombie job detection      | N/A                           | Auto-reset >30min         |
| Progress bars             | N/A                           | tqdm (auto-CI, --no-progress)|
| Code quality              | Manual review                 | pre-commit + Ruff          |
| auto_analyze_after_ocr    | N/A (manual only)             | paperforge.json opt-in    |
+---------------------------+-------------------------------+---------------------------+
```

---

## Need Help?

- **Architecture details:** See [`ARCHITECTURE.md`](ARCHITECTURE.md)
- **Command reference:** See [`COMMANDS.md`](COMMANDS.md)
- **Installation guide:** See [`INSTALLATION.md`](INSTALLATION.md)
- **User guide:** See [`AGENTS.md`](../AGENTS.md)
- **v1.2 migration:** See [`MIGRATION-v1.2.md`](MIGRATION-v1.2.md)
- **Report issues:** Open an issue with the tag `migration-v1.4`

---

*PaperForge Lite | Migration Guide | v1.3 -> v1.4*
