# PaperForge Headless Setup — For LLM Agents (English)

> **IMPORTANT**: Read this file directly. Do NOT use WebFetch or summarization — you will lose critical CLI flags and decision logic.

---

## For Humans

Copy this and paste it to your AI agent:

```
Install PaperForge in this vault by following:
https://raw.githubusercontent.com/LLLin000/PaperForge/master/docs/ai-agent-setup-guide.md
```

---

## For LLM Agents

You are installing PaperForge into the user's Obsidian Vault. Follow each step in order. **Do not skip steps.** Report results at each step before proceeding.

**Speak to the user in English.**

---

### Step 0: Collect information — ask before doing anything

Ask ALL questions below before running any command. Do not guess. Do not skip.

**Q1: Vault Path**

> What is the absolute path to your Obsidian Vault?
> (If you don't know: Open Obsidian → bottom-left vault name → "Manage Vaults" → right-click → "Show in system explorer". Send me the full path.)

Require an absolute path. Do not accept relative paths.

**Q2: AI Agent Platform**

> Which AI Agent are you using?

Show the table and wait for one choice:

| Key | Name |
|-----|------|
| `opencode` | OpenCode |
| `cursor` | Cursor |
| `claude` | Claude Code |
| `windsurf` | Windsurf |
| `github_copilot` | GitHub Copilot |
| `cline` | Cline |
| `augment` | Augment |
| `trae` | Trae |

Default if no answer: `opencode`.

**Q3: Zotero Data Directory**

First try auto-detection:
```bash
python -c "from pathlib import Path; d = Path.home() / 'Zotero'; print(str(d) if (d / 'zotero.sqlite').exists() else 'NOT_FOUND')"
```

Then tell the user and ask for confirmation:

> I detected a Zotero data directory at: `<path>`
> This should contain zotero.sqlite and a storage/ folder.
> — Reply "yes" if correct
> — Otherwise send me the full path to your Zotero data directory

If `NOT_FOUND`:

> Could not auto-detect Zotero data directory. Please send me the full path.
> (Should contain zotero.sqlite and storage/)

**Do not proceed without this path.**

**Q4: PaddleOCR API Key**

> PaperForge needs a PaddleOCR API Key for OCR. Do you have one?
> If not, sign up at https://paddleocr.baidu.com (free tier).
> If you skip now, OCR won't work until configured later. Skip?

**Q5: Directory Names**

Explain each directory and ask user to confirm or change, one by one:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| System dir | `99_System` | PaperForge internal files (plugin, OCR results, export JSON) |
| Resources dir | `03_Resources` | Literature notes and state tracking |
| Literature dir | `Literature` | Formal literature note cards |
| Control dir | `LiteratureControl` | Per-paper state tracking (OCR/deep-reading status) |
| Base dir | `05_Bases` | Obsidian Base view files (tabular queue browser) |

Final vault structure:
```
<Vault>/
├── <system-dir>/
│   └── PaperForge/       ← OCR, exports, workers
├── <resources-dir>/
│   ├── <literature-dir>/  ← formal notes
│   └── <control-dir>/     ← state tracking
└── <base-dir>/            ← Obsidian Base views
```

Ask:
> 1. System directory, default `99_System`. Keep or change?
> 2. Resources directory, default `03_Resources`?
> 3. Literature directory, default `Literature`?
> 4. Control directory, default `LiteratureControl`?
> 5. Base directory, default `05_Bases`?

Use defaults for any the user doesn't change.

---

### Step 1: Check Python version

```bash
python --version
```

- Python >= 3.10 → proceed to Step 2
- Python < 3.10 or missing → **STOP**.

> PaperForge requires Python 3.10+. Please install from https://python.org (check "Add Python to PATH"), then tell me when done.

**Wait for user before continuing.**

---

### Step 2: Install paperforge package

```bash
pip install git+https://github.com/LLLin000/PaperForge.git
```

- Success → "paperforge installed." Proceed to Step 3.
- Permission error → retry: `pip install --user git+https://github.com/LLLin000/PaperForge.git`
- Other errors → show the error to user, **STOP**.

---

### Step 3: Check Zotero

```bash
python -c "from paperforge.setup_wizard import EnvChecker; from pathlib import Path; c = EnvChecker(Path('<vault_path>')); r = c.check_zotero(); print('OK' if r.passed else 'NOT_FOUND'); print(r.detail)"
```

- `OK` → proceed to Step 4
- `NOT_FOUND` → **STOP**.

> Zotero not found. Please install from https://zotero.org, then tell me when done.

**Wait for user before continuing.**

---

### Step 4: Check Better BibTeX plugin

```bash
python -c "from paperforge.setup_wizard import EnvChecker; from pathlib import Path; c = EnvChecker(Path('<vault_path>')); r = c.check_bbt(); print('OK' if r.passed else 'NOT_FOUND'); print(r.detail)"
```

- `OK` → proceed to Step 5
- `NOT_FOUND` → **STOP**.

> Better BibTeX plugin not found. Please install:
> 1. Download: https://retorque.re/zotero-better-bibtex/
> 2. Zotero → Tools → Add-ons → gear icon → Install Add-on From File
> 3. Select the .xpi → restart Zotero
> Tell me when done.

**Wait for user before continuing.**

---

### Step 5: Create directories and deploy files

Important safety rule: this setup flow is additive. If the target vault or selected directories already contain files, PaperForge should create only missing directories/files and preserve existing content.

Assemble one command from all Step 0 values:

```bash
paperforge setup --headless \
  --vault "<vault_path>" \
  --agent "<agent_key>" \
  --zotero-data "<zotero_data_dir>" \
  --system-dir "<system_dir>" \
  --resources-dir "<resources_dir>" \
  --literature-dir "<literature_dir>" \
  --control-dir "<control_dir>" \
  --base-dir "<base_dir>" \
  --paddleocr-key "<api_key>" \
  --skip-checks
```

- Replace each `<...>` with the actual value from Step 0
- If user skipped PaddleOCR in Q4, remove `--paddleocr-key` line
- If any directory kept the default, use the default value
- `--skip-checks` because Steps 1-4 already verified everything

**Example (Windows, all defaults):**
```bash
paperforge setup --headless --vault "D:\Documents\MyVault" --agent opencode --zotero-data "C:\Users\name\Zotero" --system-dir "99_System" --resources-dir "03_Resources" --literature-dir "Literature" --control-dir "LiteratureControl" --base-dir "05_Bases" --paddleocr-key "sk-xxx" --skip-checks
```

**Expected output:**
```
[*] Phase 2: Creating directories...    [OK] 10 directories ready
[*] Phase 4: Deploying files...         [OK] worker scripts / skill files / ...
[*] Phase 5: Creating config files...   [OK] .env / paperforge.json
[*] Phase 6: Registering CLI...         [OK] paperforge CLI registered
[*] Phase 7: Verifying installation...  [OK] All 12 checks passed
```

**Failure exit codes:**

| Exit code | Meaning | Action |
|-----------|---------|--------|
| 1 | Package root not found | Reinstall: `pip install --force-reinstall git+https://github.com/LLLin000/PaperForge.git` |
| 4 | Worker scripts missing | Same as above |
| 5 | Skill files missing | Same as above |
| 6 | File integrity check failed | Check disk space and write permissions on vault path |

---

### Step 6: Verify installation

```bash
paperforge status
```

If `paperforge` command not found, try:
```bash
python -m paperforge status
```

---

### Step 7: Tell user next steps

> Installation complete. Three things to do next:
>
> **1. Configure Zotero auto-export JSON (required)**
> This is PaperForge's data source. Sync won't work without it:
> - Open Zotero
> - Right-click the library or collection you want to sync → Export
> - Format: Better BibTeX JSON
> - Must check "Keep Updated"
> - Save to <system_dir>/PaperForge/exports/ in your vault
>
> **2. Enable PaperForge plugin in Obsidian**
> - Settings → Community Plugins → Installed → PaperForge → Enable
> - Ctrl+P, type "PaperForge" and open the dashboard
>
> **3. Sync literature**
> - In the dashboard, click `Sync Library`
>
> **4. If you skipped PaddleOCR Key**
> - Add to <system_dir>/PaperForge/.env:
>   PADDLEOCR_API_TOKEN=<your key>

---

## Common Issues

### User stuck on a step

Go back to that step and re-check. Confirm user completed it before continuing.

### Vault path has spaces

Wrap in quotes: `--vault "D:\My Documents\MyVault"`

### pip permission error on macOS/Linux

Add `--user`:
```bash
pip install --user git+https://github.com/LLLin000/PaperForge.git
```

### User already has PaperForge (upgrade scenario)

Skip Steps 0-1. Run:
```bash
paperforge setup --headless --vault "<path>" --agent "<key>" --skip-checks
```
