# Memory Runtime Health Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single runtime-health contract for the memory layer and make vector build state persistent, resumable, and UI-safe.

**Architecture:** Add a new `runtime-health` CLI entry that computes layered health from existing memory/vector subsystems plus a persistent vector job-state file. Keep the plugin thin: it triggers CLI commands and renders persisted status instead of treating in-memory JS state as truth.

**Tech Stack:** Python stdlib JSON/filesystem/subprocess, existing PFResult CLI pattern, SQLite/JSONL/ChromaDB, Obsidian plugin JS, Vitest.

---

## File Structure Map

```text
Create:
  paperforge/commands/runtime_health.py           — CLI run() for runtime-health
  paperforge/memory/runtime_health.py             — layer checks + summary derivation
  paperforge/plugin/tests/runtime-health.test.mjs — plugin-side small state helpers tests

Modify:
  paperforge/cli.py                               — register + dispatch runtime-health, embed stop
  paperforge/commands/embed.py                    — persistent vector-build-state lifecycle
  paperforge/memory/vector_db.py                  — read/write job-state helpers
  paperforge/plugin/main.js                       — system status + vector section polling/recovery
  paperforge/plugin/src/testable.js               — pure helpers for UI state decisions
```

---

### Task 1: Define persistent vector build state helpers

**Files:**
- Modify: `paperforge/memory/vector_db.py`
- Test: `tests/unit/memory/test_vector_db.py` or existing vector tests file

- [ ] **Step 1: Write the failing test**

Add tests for:

```python
def test_vector_build_state_roundtrip(tmp_path):
    ...

def test_vector_build_state_defaults_when_missing(tmp_path):
    ...
```

Expect a missing state file to resolve to `idle`, and saved state to roundtrip exactly.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/memory/test_vector_db.py -q --tb=short`

- [ ] **Step 3: Write minimal implementation**

Add helpers like:

```python
def get_vector_build_state_path(vault: Path) -> Path: ...
def read_vector_build_state(vault: Path) -> dict: ...
def write_vector_build_state(vault: Path, state: dict) -> None: ...
def mark_vector_build_state(vault: Path, **fields) -> dict: ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/memory/test_vector_db.py -q --tb=short`

- [ ] **Step 5: Commit**

```bash
git add tests/unit/memory/test_vector_db.py paperforge/memory/vector_db.py
git commit -m "feat: add persistent vector build state helpers"
```

---

### Task 2: Persist embed build lifecycle and add stop command

**Files:**
- Modify: `paperforge/commands/embed.py`
- Modify: `paperforge/cli.py`
- Test: `tests/unit/commands/test_embed.py`

- [ ] **Step 1: Write the failing tests**

Cover:

```python
def test_embed_build_writes_running_and_completed_state(...):
    ...

def test_embed_stop_returns_ok_when_no_active_job(...):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/commands/test_embed.py -q --tb=short`

- [ ] **Step 3: Write minimal implementation**

In `embed.py`:

- write `running` state before loop
- update `current/total/paper_id/last_update` after each paper
- set `completed` or `failed` on exit
- add `stop` subcommand that marks `stopping` and terminates active PID if present
- extend `embed status --json` to include job-state payload

In `cli.py`:

- register `paperforge embed stop`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/commands/test_embed.py -q --tb=short`

- [ ] **Step 5: Commit**

```bash
git add tests/unit/commands/test_embed.py paperforge/commands/embed.py paperforge/cli.py
git commit -m "feat: persist embed lifecycle and add stop command"
```

---

### Task 3: Add runtime health core computation

**Files:**
- Create: `paperforge/memory/runtime_health.py`
- Test: `tests/unit/memory/test_runtime_health.py`

- [ ] **Step 1: Write the failing tests**

Add tests for:

```python
def test_runtime_health_blocks_without_paperforge_json(...):
    ...

def test_runtime_health_degrades_when_vector_is_broken_but_read_write_are_safe(...):
    ...

def test_runtime_health_summary_flags_capabilities(...):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/memory/test_runtime_health.py -q --tb=short`

- [ ] **Step 3: Write minimal implementation**

Implement pure functions:

```python
def get_runtime_health(vault: Path) -> dict: ...
def _check_bootstrap(vault: Path) -> dict: ...
def _check_read(vault: Path) -> dict: ...
def _check_write(vault: Path) -> dict: ...
def _check_index(vault: Path) -> dict: ...
def _check_vector(vault: Path) -> dict: ...
def _derive_summary(layers: dict) -> dict: ...
```

Use existing helpers where possible; avoid hidden mutations.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/memory/test_runtime_health.py -q --tb=short`

- [ ] **Step 5: Commit**

```bash
git add tests/unit/memory/test_runtime_health.py paperforge/memory/runtime_health.py
git commit -m "feat: add layered runtime health computation"
```

---

### Task 4: Expose `paperforge runtime-health --json`

**Files:**
- Create: `paperforge/commands/runtime_health.py`
- Modify: `paperforge/cli.py`
- Test: `tests/unit/commands/test_runtime_health.py`

- [ ] **Step 1: Write the failing test**

```python
def test_runtime_health_command_returns_pfresult_json(...):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/commands/test_runtime_health.py -q --tb=short`

- [ ] **Step 3: Write minimal implementation**

Create command module that wraps `get_runtime_health(vault)` into PFResult and add parser/dispatch in `cli.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/commands/test_runtime_health.py -q --tb=short`

- [ ] **Step 5: Commit**

```bash
git add tests/unit/commands/test_runtime_health.py paperforge/commands/runtime_health.py paperforge/cli.py
git commit -m "feat: add runtime-health CLI command"
```

---

### Task 5: Make plugin vector UI rehydrate from persisted state

**Files:**
- Modify: `paperforge/plugin/main.js`
- Modify: `paperforge/plugin/src/testable.js`
- Create: `paperforge/plugin/tests/runtime-health.test.mjs`

- [ ] **Step 1: Write the failing tests**

Add Vitest coverage for small pure helpers such as:

```javascript
shouldRenderVectorReady(true, null) === true
deriveVectorUiState({ job: { status: 'running', current: 5, total: 20 }})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- tests/runtime-health.test.mjs`

- [ ] **Step 3: Write minimal implementation**

In `main.js`:

- fetch runtime health or embed status to rehydrate state on render
- render progress from persisted job payload, not only `_embedProcess`
- Start button shells out and then polls status
- Stop button calls CLI stop
- keep ready/config UI visible even when status text is temporarily unknown
- System Status shows overall runtime badge + primary next action

In `testable.js`:

- add minimal pure helpers consumed by tests

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- tests/runtime-health.test.mjs && node --check "main.js"`

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/tests/runtime-health.test.mjs paperforge/plugin/src/testable.js paperforge/plugin/main.js
git commit -m "feat: rehydrate vector build UI from persisted runtime state"
```

---

### Task 6: Wire dashboard system status to runtime-health summary

**Files:**
- Modify: `paperforge/plugin/main.js`
- Test: `paperforge/plugin/tests/runtime-health.test.mjs`

- [ ] **Step 1: Write the failing test**

Add a pure helper test for parsing a runtime-health summary into a concise dashboard status line.

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- tests/runtime-health.test.mjs`

- [ ] **Step 3: Write minimal implementation**

Update dashboard/system status fetch path to prefer `paperforge runtime-health --json` and display:

- status badge
- reason
- primary next action
- vector progress subline if running

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- tests/runtime-health.test.mjs && node --check "main.js"`

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/tests/runtime-health.test.mjs paperforge/plugin/main.js
git commit -m "feat: drive dashboard system status from runtime health"
```

---

### Task 7: Teach bootstrap and skill flows to consume runtime-health

**Files:**
- Modify: `paperforge/skills/paperforge/SKILL.md`
- Modify: `paperforge/skills/paperforge/workflows/paper-search.md`
- Modify: `paperforge/skills/paperforge/workflows/paper-qa.md`
- Modify: `paperforge/skills/paperforge/workflows/deep-reading.md`
- Modify: `paperforge/skills/paperforge/workflows/reading-log.md`
- Modify: `paperforge/skills/paperforge/workflows/project-log.md`

- [ ] **Step 1: Write the failing check**

Add a manual verification checklist in the plan execution notes: every workflow that reads/writes memory must mention runtime-health preflight.

- [ ] **Step 2: Update the skill files**

Add a global rule after bootstrap:

```bash
$PYTHON -m paperforge runtime-health --json --vault "$VAULT"
```

Then route behavior by `safe_read`, `safe_write`, and `layers.vector` status.

- [ ] **Step 3: Verify references**

Run: `rg "runtime-health|safe_read|safe_write" paperforge/skills/paperforge`

- [ ] **Step 4: Commit**

```bash
git add paperforge/skills/paperforge/SKILL.md paperforge/skills/paperforge/workflows/*.md
git commit -m "chore: add runtime-health preflight to paperforge skill workflows"
```

---

### Task 8: End-to-end smoke test

**Files:**
- No new production files required

- [ ] **Step 1: Run runtime health smoke test**

Run:

```bash
python -m paperforge runtime-health --json --vault "<test_vault>"
```

Expected: PFResult JSON with `summary`, `layers`, and `capabilities`.

- [ ] **Step 2: Run embed lifecycle smoke test**

Run:

```bash
python -m paperforge embed status --json --vault "<test_vault>"
python -m paperforge embed build --resume --vault "<test_vault>"
python -m paperforge embed stop --json --vault "<test_vault>"
```

Expected: persisted job-state transitions are visible across commands.

- [ ] **Step 3: Run targeted Python and plugin tests**

Run:

```bash
python -m pytest tests/unit/memory/test_runtime_health.py tests/unit/commands/test_runtime_health.py tests/unit/commands/test_embed.py -q --tb=short
npm test -- tests/runtime-health.test.mjs
```

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "test: verify runtime health and vector build lifecycle"
```
