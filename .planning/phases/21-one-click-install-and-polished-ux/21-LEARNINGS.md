---
phase: 21
phase_name: "One-Click Install and Polished UX"
project: "PaperForge Lite"
generated: "2026-05-02"
counts:
  decisions: 10
  lessons: 4
  patterns: 5
  surprises: 4
missing_artifacts:
  - "UAT.md"
---

## Decisions

### Additive-only approach to settings tab
All additions to `PaperForgeSettingTab.display()` are purely additive — no modifications to `PaperForgeStatusView` sidebar or `ACTIONS[]` definitions.

**Rationale/Context:** Zero-regression guarantee. The install button exists in the settings tab only and must not affect existing sidebar functionality or command palette actions (INST-04 requirement).

**Source:** 21-01-PLAN.md, 21-01-SUMMARY.md, 21-VERIFICATION.md

---

### Client-side field validation only
Uses simple string trim checks (`!s.key || !s.key.trim()`), no filesystem calls.

**Rationale/Context:** Initial consideration included `fs.existsSync()` for path validation, but that requires Node sync I/O which blocks the event loop. Non-empty validation is sufficient to prevent empty-field subprocess spawns. Path validation is deferred to the subprocess which fails gracefully with a friendly error message.

**Source:** 21-01-PLAN.md, 21-01-SUMMARY.md

---

### zotero_data_dir excluded from validation
The Zotero data directory field is optional and NOT checked by `_validate()`.

**Rationale/Context:** Zotero data dir is auto-detected by `headless_setup()` when not provided. Making it optional reduces friction for users who don't need to override it.

**Source:** 21-01-PLAN.md, 21-01-SUMMARY.md

---

### All error messages in Chinese
Error messages from `_validate()`, `_formatSetupError()`, and `_showNotice()` are all in Chinese.

**Rationale/Context:** Required by INST-03. The target user base is Chinese-speaking medical researchers. Even technical error messages (Python not found, module missing) are localized.

**Source:** 21-01-SUMMARY.md, 21-02-PLAN.md, 21-02-SUMMARY.md

---

### spawn over exec for subprocess
Use `node:child_process.spawn` (not `exec`) for non-blocking subprocess execution with stdout streaming.

**Rationale/Context:** `spawn` streams stdout line-by-line so `_processSetupOutput()` can show step progress in real-time. `exec` buffers all output until completion — no intermediate feedback possible.

**Source:** 21-02-PLAN.md, 21-02-SUMMARY.md, 21-VERIFICATION.md

---

### --headless flag, not --non-interactive
The correct CLI flag for headless setup is `--headless`, not `--non-interactive`.

**Rationale/Context:** The CLI interface defines `--headless` as the flag for non-interactive mode. The initial plan draft incorrectly used `--non-interactive` — corrected during code review.

**Source:** 21-02-PLAN.md, 21-02-SUMMARY.md, 21-VERIFICATION.md

---

### API key via --paddleocr-key CLI flag
API key is passed via `--paddleocr-key` CLI argument, not from `PADDLEOCR_API_TOKEN` env var.

**Rationale/Context:** The `headless_setup()` function reads API key from the CLI argument (`cli.py` line 424-440), not from environment variable. Confirmed by reading the actual Python CLI code.

**Source:** 21-02-PLAN.md, 21-02-SUMMARY.md

---

### Explicit directory args override defaults
Plugin defaults (20_Resources, Control) must override headless_setup's built-in defaults (03_Resources, LiteratureControl) via --resources-dir and --control-dir.

**Rationale/Context:** The plugin's DEFAULT_SETTINGS use different defaults for resources_dir and control_dir than the Python headless_setup function. Without explicit override, the subprocess would create directories in different locations than what the plugin expects.

**Source:** 21-02-PLAN.md, 21-02-SUMMARY.md

---

### try/finally for button lifecycle
Button is disabled BEFORE `await`, re-enabled in `finally` — guarantees no double-click even if spawn throws synchronously.

**Rationale/Context:** Prevents race conditions. If `spawn()` throws synchronously, the `finally` block still runs and re-enables the button. The button text also changes to "正在安装..." during execution for visual feedback.

**Source:** 21-02-PLAN.md, 21-02-SUMMARY.md, 21-VERIFICATION.md

---

### 5 error patterns mapped to Chinese
`_formatSetupError()` matches 5 common subprocess error patterns: Python not found, module missing, permission denied, path not found, timeout.

**Rationale/Context:** Covers the most common failure modes for first-time users (no Python, no pip install, file permissions, wrong path, network timeout). Full error always available via `console.error()` for debugging. Fallback truncates stderr to 3 lines, 200 chars.

**Source:** 21-02-PLAN.md, 21-02-SUMMARY.md, 21-VERIFICATION.md

---

## Lessons

### Obsidian CSS variables provide automatic theme compatibility
Using `--radius-m`, `--font-ui-small`, `--background-secondary`, `--color-green`, `--text-error`, `--color-blue` ensures install status styles work in both light and dark mode.

**Context:** By using Obsidian's built-in CSS variables rather than hardcoded colors, the install status area automatically adapts to the user's theme without any additional CSS work.

**Source:** 21-01-PLAN.md Task 3

---

### color-mix() creates clean tinted backgrounds
`color-mix(in srgb, var(--color-green) 10%, var(--background-secondary))` creates subtle tinted backgrounds without overlapping full theme colors.

**Context:** The 8-10% opacity creates a gentle tint that indicates status (green/red/blue) without being visually overwhelming. This is cleaner than using `opacity` on the entire element.

**Source:** 21-01-PLAN.md, 21-01-SUMMARY.md, 21-VERIFICATION.md

---

### headless_setup has different defaults than plugin
The Python `headless_setup()` function's built-in defaults (resources_dir="03_Resources", control_dir="LiteratureControl") differ from the plugin's DEFAULT_SETTINGS (resources_dir="20_Resources", control_dir="Control").

**Context:** Without explicit `--resources-dir` and `--control-dir` args in the spawn call, the subprocess would create directories in locations the plugin doesn't expect, causing silent misconfiguration.

**Source:** 21-02-PLAN.md

---

### Pre-existing code has raw stderr in Notice
Line 484 of `main.js` (pre-existing, not from Phase 21) exposes raw stderr in `new Notice`.

**Context:** The verification report flagged a pre-existing anti-pattern in the command palette actions dispatch code. Phase 21's `_showNotice()` in PaperForgeSettingTab correctly uses `_formatSetupError()` to avoid raw error exposure. This pre-existing issue is outside Phase 21 scope.

**Source:** 21-VERIFICATION.md

---

## Patterns

### Obsidian CSS variables for theme consistency
All install status styling uses Obsidian's built-in CSS variables for automatic light/dark theme compatibility.

**When to use:** Any Obsidian plugin CSS should use Obsidian CSS variables (`--background-secondary`, `--color-green`, `--text-error`, etc.) instead of hardcoded colors.

**Source:** 21-01-PLAN.md, 21-01-SUMMARY.md, 21-VERIFICATION.md

---

### color-mix() for status backgrounds
Three color variants using `color-mix(in srgb, <color> <opacity>%, var(--background-secondary))` for tinted backgrounds.

**When to use:** When you need subtly colored status indicators that blend with the existing theme. The 8-10% range provides visible tint without being distracting.

**Source:** 21-01-PLAN.md, 21-VERIFICATION.md

---

### spawn (not exec) for non-blocking subprocess
Use `spawn` when you need real-time progress updates from a long-running subprocess.

**When to use:** Any time a plugin spawns a subprocess that produces stepped output and you want to show progress to the user. `spawn` streams stdout line-by-line; `exec` buffers everything.

**Source:** 21-02-PLAN.md, 21-02-SUMMARY.md, 21-VERIFICATION.md

---

### try/finally for guaranteed resource cleanup
Button disable/enable wrapped in try/finally to ensure resources are always released.

**When to use:** Any async operation that acquires a resource (disabling a button, showing a modal, locking a state). The finally block guarantees cleanup whether the operation succeeds, fails, or throws synchronously.

**Source:** 21-02-PLAN.md, 21-02-SUMMARY.md, 21-VERIFICATION.md

---

### Pattern-based error mapping
Regex patterns mapped to user-facing Chinese messages for common subprocess error codes.

**When to use:** When a subprocess can fail with cryptic system error messages (ENOENT, EACCES, ModuleNotFoundError) that need to be translated into user-friendly text. Pattern matching captures the error class while the full message is logged to console for debugging.

**Source:** 21-02-PLAN.md, 21-02-SUMMARY.md, 21-VERIFICATION.md

---

## Surprises

### Headless setup CLI flag confusion
Initially planned to use `--non-interactive`, but the correct CLI flag was `--headless`.

**Impact:** Could have caused silent failure (CLI would ignore unrecognized flags). Highlights the importance of reading the actual Python CLI code (cli.py) rather than guessing flag names from context.

**Source:** 21-02-PLAN.md, 21-02-SUMMARY.md

---

### Non-obvious default differences between plugin and CLI
headless_setup's built-in defaults (03_Resources, LiteratureControl) differ from plugin defaults (20_Resources, Control).

**Impact:** This would cause the subprocess to create directories in unexpected locations, appearing to succeed but actually misconfiguring the vault. Required explicit --resources-dir and --control-dir overrides.

**Source:** 21-02-PLAN.md

---

### Pre-existing raw error exposure in command palette actions
Existing code line 484 exposed raw stderr in `new Notice`, which Phase 21's careful error handling specifically avoids.

**Impact:** Phase 21's INST-02 compliance (no raw tracebacks in user-facing messages) is stricter than the existing codebase. Highlights the need to audit pre-existing error handling patterns.

**Source:** 21-VERIFICATION.md

---

### Validation approach simplified from initial plan
Initial plan considered `fs.existsSync()` for path existence checks but simplified to just non-empty validation since subprocess handles path validation.

**Impact:** Saved complexity (no sync I/O, no error handling for filesystem calls) while still preventing the main failure case (empty fields). The subprocess path validation is then mapped to a friendly Chinese message.

**Source:** 21-01-PLAN.md Task 2
