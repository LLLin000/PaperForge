# Migration Guide: v1.1 to v1.2

> This guide covers all breaking changes when upgrading PaperForge from v1.1 to v1.2.
>
> **Who should read this:** Anyone upgrading from v1.1 — whether you installed via `pip install paperforge-lite`, cloned the repo, or use custom scripts referencing the old package or command names.
>
> **Estimated time:** 5-10 minutes to follow the steps, plus time to update any custom scripts or templates.

---

## What's New in v1.2

v1.2 is a **systematization release**. The core functionality is unchanged — Zotero sync, OCR, deep reading, and note generation all work the same way — but the command interface has been unified to reduce confusion and simplify the mental model.

Key improvements:

- **Unified CLI commands:** `paperforge sync` replaces `selection-sync` and `index-refresh`; `paperforge ocr` replaces `ocr run` and `ocr doctor`. Fewer commands to remember.
- **Unified Agent namespace:** All Agent commands now use `/pf-*` (`/pf-deep`, `/pf-paper`, `/pf-ocr`, etc.), replacing the fragmented `/LD-*` and `/lp-*` prefixes from v1.1.
- **Package rename:** The Python package is now `paperforge` (not `paperforge_lite`), matching the CLI command name.
- **Shared command modules:** CLI and Agent commands now share the same implementation in `paperforge/commands/`, reducing code duplication and making the system easier to extend (see [`ARCHITECTURE.md`](ARCHITECTURE.md) for details).

> **Backward compatibility note:** v1.2 still accepts the old CLI command names (`selection-sync`, `index-refresh`, `ocr run`) as aliases, so existing scripts will not break immediately. However, these aliases are deprecated and may be removed in v1.3. Agent commands (`/LD-*`, `/lp-*`) are **not** backward compatible — your Agent platform must use the new `/pf-*` namespace.

---

## Breaking Changes Summary

| Change | Old (v1.1) | New (v1.2) | Impact |
|--------|-----------|-----------|--------|
| Package name | `paperforge_lite` | `paperforge` | `pip uninstall` + reinstall required |
| CLI sync (full) | `paperforge selection-sync` then `paperforge index-refresh` | `paperforge sync` | Single command; old names still work as aliases |
| CLI sync (selection only) | `paperforge selection-sync` | `paperforge sync --selection` | Old name still works as alias |
| CLI sync (index only) | `paperforge index-refresh` | `paperforge sync --index` | Old name still works as alias |
| CLI OCR (run) | `paperforge ocr run` | `paperforge ocr` | Old name still works as alias |
| CLI OCR (diagnose) | `paperforge ocr doctor` | `paperforge ocr --diagnose` | Old name still works as alias |
| Agent deep reading | `/LD-deep <key>` | `/pf-deep <key>` | **Not backward compatible** |
| Agent paper summary | `/LD-paper <key>` | `/pf-paper <key>` | **Not backward compatible** |
| Agent OCR | `/lp-ocr` | `/pf-ocr` | **Not backward compatible** |
| Agent sync | `/lp-selection-sync`, `/lp-index-refresh` | `/pf-sync` | **Not backward compatible** |
| Agent status | `/lp-status` | `/pf-status` | **Not backward compatible** |
| Python import | `from paperforge_lite.cli import main` | `from paperforge.cli import main` | Update all custom scripts |
| Module import | `from paperforge_lite.config import load_config` | `from paperforge.config import load_config` | Update all custom scripts |

---

## Detailed Breaking Changes

### 1. Package Rename: `paperforge_lite` -> `paperforge`

The Python package installed by pip has been renamed to match the CLI command name.

**What you need to do:**
- Uninstall the old package: `pip uninstall paperforge-lite`
- Install the new package: `pip install -e .` (from the repo root) or `pip install paperforge`

**Why this changed:** Having `paperforge_lite` as the Python package but `paperforge` as the CLI command was confusing. Now they match.

### 2. CLI Commands Unified

In v1.1, syncing required two separate commands:
```bash
paperforge selection-sync   # Create library-records
paperforge index-refresh    # Generate formal notes
```

In v1.2, these are unified under `paperforge sync`:
```bash
paperforge sync             # Runs both selection and index
paperforge sync --selection # Only selection-sync
paperforge sync --index     # Only index-refresh
```

Similarly, OCR commands were unified:
```bash
# v1.1
paperforge ocr run
paperforge ocr doctor

# v1.2
paperforge ocr
paperforge ocr --diagnose
```

**Backward compatibility:** The old command names (`selection-sync`, `index-refresh`, `ocr run`, `ocr doctor`) still work in v1.2 as internal aliases, but they are deprecated. Update your scripts and muscle memory to the new names.

### 3. Agent Commands Unified to `/pf-*`

All Agent commands now use the `/pf-*` (PaperForge) namespace:

| Old Command | New Command | Purpose |
|-------------|-------------|---------|
| `/LD-deep <key>` | `/pf-deep <key>` | Deep reading (Keshav three-pass) |
| `/LD-paper <key>` | `/pf-paper <key>` | Quick paper summary |
| `/lp-ocr` | `/pf-ocr` | Run OCR on marked papers |
| `/lp-selection-sync` | `/pf-sync` | Sync Zotero to library-records |
| `/lp-index-refresh` | *(part of /pf-sync)* | Generate formal notes |
| `/lp-status` | `/pf-status` | Show system status |

**No backward compatibility:** Your Agent platform (OpenCode, Codex, Claude Code, etc.) must be configured to use the new command names. The old `/LD-*` and `/lp-*` prefixes will not be recognized.

---

## Migration Steps

Follow these steps in order. Each step is copy-pasteable.

### Step 1: Backup Your Vault

> [!WARNING]
> Always back up your data before upgrading. While v1.2 does not modify your notes or library-records automatically, it's good practice.

```bash
# Option A: Copy the entire vault
cp -r "你的Vault路径" "你的Vault路径-backup-$(date +%Y%m%d)"

# Option B: If using git, commit current state
cd "你的Vault路径"
git add -A
git commit -m "backup before v1.2 upgrade"
```

At minimum, back up these directories:
- `<resources_dir>/` — your literature notes and library-records
- `<system_dir>/PaperForge/ocr/` — OCR results (can be regenerated, but takes time)
- `.env` — your API keys

### Step 2: Uninstall the Old Package

```bash
pip uninstall paperforge-lite
```

If you see `WARNING: Skipping paperforge-lite as it is not installed`, that's fine — you may have installed it in a different environment.

### Step 3: Install the New Package

**If installing from the repo (recommended for development/customization):**

```bash
cd "你的Vault路径"
pip install -e .
```

**If installing from PyPI (when available):**

```bash
pip install paperforge
```

### Step 4: Verify Installation

```bash
# Should show the new unified help output
python -m paperforge --help

# Verify the package name changed
python -c "from paperforge.cli import main; print('OK: import works')"
```

Expected output for `--help`:
```
usage: paperforge [-h] [--version] {sync,ocr,deep-reading,repair,status,doctor} ...

PaperForge Lite v1.2 — Literature workflow for Zotero + Obsidian

positional arguments:
  {sync,ocr,deep-reading,repair,status,doctor}
    sync                Sync Zotero library and generate notes
    ocr                 Run OCR on marked PDFs
    ...
```

### Step 5: Update Scripts and Aliases

Search your system for references to old commands and update them:

```bash
# Find old command references in your shell history, aliases, scripts
grep -r "paperforge selection-sync" ~/scripts/ ~/.bashrc ~/.zshrc 2>/dev/null || true
grep -r "paperforge index-refresh" ~/scripts/ ~/.bashrc ~/.zshrc 2>/dev/null || true
grep -r "paperforge ocr run" ~/scripts/ ~/.bashrc ~/.zshrc 2>/dev/null || true

# Find old Python imports
grep -r "from paperforge_lite" ~/scripts/ 2>/dev/null || true
```

**Update checklist:**
- [ ] Shell aliases in `.bashrc`, `.zshrc`, or `.bash_profile`
- [ ] Custom scripts in `~/scripts/` or your vault
- [ ] Makefile targets
- [ ] CI/CD pipeline scripts
- [ ] Obsidian Templater or Dataview scripts that invoke CLI commands

**Example updates:**
```bash
# Old alias
alias pfs='paperforge selection-sync && paperforge index-refresh'

# New alias
alias pfs='paperforge sync'

# Old script line
python -m paperforge_lite.cli selection-sync

# New script line
python -m paperforge sync
```

### Step 6: Update Obsidian Notes and Templates

If any of your Obsidian notes, templates, or Dataview queries reference old command names, update them:

**Common places to check:**
- Templater templates that insert command examples
- DataviewJS scripts that call `dv.view()` with CLI commands
- Documentation notes in your vault
- Checklists or SOP notes for literature workflow

**Old references to search for:**
```
/LD-deep
/LD-paper
/lp-ocr
/lp-selection-sync
/lp-index-refresh
/lp-status
paperforge selection-sync
paperforge index-refresh
paperforge ocr run
paperforge ocr doctor
paperforge_lite
```

> **Tip:** Use Obsidian's global search (`Ctrl+Shift+F` or `Cmd+Shift+F`) to search for these strings across your vault.

### Step 7: Verify Sync Works

Run a dry-run sync to confirm everything is wired correctly:

```bash
paperforge sync --dry-run
```

Expected behavior:
- No files are modified
- You see a preview of what would happen (new items detected, records that would be created)
- No import errors or path resolution errors

If the dry-run succeeds, run the real sync:

```bash
paperforge sync
```

Then verify:
1. New library-records are created in `<resources_dir>/<control_dir>/library-records/`
2. Formal notes are generated in `<resources_dir>/<literature_dir>/`
3. Existing notes and records are **not** corrupted

---

## Import Path Changes

If you have custom Python scripts that import from `paperforge_lite`, update the import paths:

### CLI Main Entry Point

```python
# v1.1
from paperforge_lite.cli import main

# v1.2
from paperforge.cli import main
```

### Configuration

```python
# v1.1
from paperforge_lite.config import load_config, load_vault_config, paperforge_paths

# v1.2
from paperforge.config import load_config, load_vault_config, paperforge_paths
```

### Command Modules (Advanced)

```python
# v1.1 — commands were inline in cli.py or literature_pipeline.py
from paperforge_lite.cli import run_selection_sync

# v1.2 — commands are in shared modules
from paperforge.commands.sync import sync
from paperforge.commands.ocr import ocr
from paperforge.commands.deep import deep_reading_queue
from paperforge.commands.status import show_status
```

### Script Invocation

```python
# v1.1
import subprocess
subprocess.run(["python", "-m", "paperforge_lite", "selection-sync"])

# v1.2
import subprocess
subprocess.run(["python", "-m", "paperforge", "sync", "--selection"])
```

---

## Rollback Instructions

If something goes wrong after upgrading to v1.2, you can downgrade to v1.1.

### Option A: Rollback via Git (Recommended if you cloned the repo)

```bash
cd "你的Vault路径"

# Check out the v1.1 tag or branch
git checkout v1.1
# OR
git checkout <commit-hash-of-v1.1>

# Reinstall the old package
pip uninstall paperforge
pip install -e .
```

### Option B: Rollback via PyPI (If installed from PyPI)

```bash
# Uninstall v1.2
pip uninstall paperforge

# Install the last v1.1 release
pip install paperforge-lite==1.1.x
```

Replace `1.1.x` with the specific version you were using.

### Option C: Quick Restore from Backup

If you created a backup in Step 1:

```bash
# Remove the upgraded vault
rm -rf "你的Vault路径"

# Restore from backup
cp -r "你的Vault路径-backup-YYYYMMDD" "你的Vault路径"

# Reinstall v1.1 package
pip uninstall paperforge
pip install paperforge-lite==1.1.x
```

### What to Watch Out For

**State compatibility:** v1.2 does not change the format of `library-records`, formal notes, or OCR output. If you downgrade to v1.1 after running v1.2:
- Your `library-records` will still work (frontmatter format unchanged)
- Your formal notes will still work
- Your OCR output will still work
- **Exception:** If you used new v1.2 features (e.g., `paperforge repair`), the v1.1 scripts may not recognize new fields. These fields are harmless — v1.1 will ignore them.

**Agent commands:** If you downgraded the package but your Agent platform still has `/pf-*` commands configured, those commands will fail. Revert your Agent configuration to use `/LD-deep`, `/LD-paper`, etc.

---

## FAQ

### Q: Do I need to reconfigure my vault?

**A:** No. `paperforge.json`, `.env`, directory structure, and all your data remain compatible. The only changes are command names and the Python package name.

### Q: Will my existing notes break?

**A:** No. v1.2 does not modify existing notes or library-records during sync unless you explicitly run `paperforge sync` and new items are detected. Existing notes keep their frontmatter, content, and `## 精读` sections unchanged.

### Q: Can I use both old and new commands at the same time?

**A:** For CLI commands: yes, temporarily. v1.2 accepts `selection-sync`, `index-refresh`, and `ocr run` as deprecated aliases. However, these aliases may be removed in v1.3, so update your habits and scripts.

For Agent commands: no. `/LD-deep`, `/LD-paper`, `/lp-*` are not recognized in v1.2. You must use `/pf-deep`, `/pf-paper`, `/pf-*`.

### Q: What about my custom scripts that import `paperforge_lite`?

**A:** You must update the import paths. `paperforge_lite` no longer exists after you uninstall it. Search your scripts for `from paperforge_lite` and `import paperforge_lite` and replace with `paperforge`.

### Q: The sync command seems slower — is this normal?

**A:** `paperforge sync` (full) runs both selection-sync and index-refresh sequentially. If you previously ran them separately and only ran one at a time, the full sync will take longer because it does more work. Use `paperforge sync --selection` or `paperforge sync --index` if you only need one phase.

If it's significantly slower than running the old commands back-to-back, check:
1. Are there many new items in Zotero? First sync after upgrade may take longer.
2. Is your vault on a slow drive (network drive, spinning disk)?
3. Run with `--verbose` to see per-step timing: `paperforge sync --verbose`

### Q: How do I update my Obsidian templates?

**A:** If your templates contain command examples (e.g., in a "Literature Workflow" template), update the command references:

```markdown
<!-- Old -->
1. Run `paperforge selection-sync`
2. Run `paperforge index-refresh`
3. Run `/LD-deep {{zotero_key}}`

<!-- New -->
1. Run `paperforge sync`
2. Run `/pf-deep {{zotero_key}}`
```

Use Obsidian's global search (`Ctrl+Shift+F`) to find old command names in your templates.

### Q: I get `ModuleNotFoundError: No module named 'paperforge_lite'` after upgrading.

**A:** You have a script, alias, or Obsidian plugin still referencing the old package name. Search for `paperforge_lite` in:
- Your shell aliases (`~/.bashrc`, `~/.zshrc`)
- Custom Python scripts
- Obsidian Templater or DataviewJS scripts
- Systemd services or cron jobs

Replace all occurrences with `paperforge`.

### Q: Do I need to update my `.opencode/skills/` or `.opencode/command/` files?

**A:** Yes, if you manually copied or symlinked the Agent command files. The v1.2 repository includes updated `command/pf-*.md` files and updated skill scripts. Re-copy or re-symlink them from the v1.2 repo:

```bash
# If you previously symlinked:
ln -sf "$(pwd)/command/pf-deep.md" .opencode/command/pf-deep.md
ln -sf "$(pwd)/command/pf-paper.md" .opencode/command/pf-paper.md
# ... etc for all 5 command files
```

Also update the skill script if you symlinked it:
```bash
ln -sf "$(pwd)/.agents/skills/literature-qa/scripts/ld_deep.py" .opencode/skills/literature-qa/scripts/ld_deep.py
```

### Q: Will v1.1 command aliases be removed?

**A:** They are deprecated in v1.2 and may be removed in v1.3. There is no set timeline, but the recommendation is to migrate your scripts and documentation to the new command names as soon as convenient.

---

## Quick Reference Card

Print this and keep it handy:

```
+------------------+---------------------------+---------------------------+
| Task             | Old (v1.1)                | New (v1.2)                |
+------------------+---------------------------+---------------------------+
| Full sync        | selection-sync +          | paperforge sync           |
|                  | index-refresh             |                           |
| Selection only   | paperforge selection-sync | paperforge sync --selection|
| Index only       | paperforge index-refresh  | paperforge sync --index   |
| Run OCR          | paperforge ocr run        | paperforge ocr            |
| Diagnose OCR     | paperforge ocr doctor     | paperforge ocr --diagnose |
| Deep reading     | /LD-deep <key>            | /pf-deep <key>            |
| Paper summary    | /LD-paper <key>           | /pf-paper <key>           |
| Agent OCR        | /lp-ocr                   | /pf-ocr                   |
| Agent sync       | /lp-selection-sync        | /pf-sync                  |
| Agent status     | /lp-status                | /pf-status                |
| Python package   | paperforge_lite           | paperforge                |
+------------------+---------------------------+---------------------------+
```

---

## Need Help?

- **Architecture details:** See [`ARCHITECTURE.md`](ARCHITECTURE.md)
- **Command reference:** See [`COMMANDS.md`](COMMANDS.md)
- **Installation guide:** See [`INSTALLATION.md`](INSTALLATION.md)
- **User guide:** See [`AGENTS.md`](../AGENTS.md)
- **Report issues:** Open an issue with the tag `migration-v1.2`

---

*PaperForge Lite | Migration Guide | v1.1 -> v1.2*
