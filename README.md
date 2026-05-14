<p align="center">
  <img src="docs/images/paperforge-banner.png" alt="PaperForge banner" width="100%" />
</p>

# PaperForge

[![Version](https://img.shields.io/github/v/release/LLLin000/PaperForge?style=for-the-badge&label=version)](https://github.com/LLLin000/PaperForge/releases)
[![Python](https://img.shields.io/pypi/pyversions/paperforge?style=for-the-badge&logo=python&logoColor=white&color=3775A9)](https://python.org)
[![License](https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgreen?style=for-the-badge)](LICENSE)

[简体中文](README.zh.md) · **English**

> **铸知识为器，启洞见之明。 — Forge Knowledge, Empower Insight.**

PaperForge brings your Zotero library into Obsidian. Sync papers, run OCR, extract figures, and do AI-assisted deep reading — all inside a single vault.

---

## 0. What PaperForge Is

PaperForge is **not just an Obsidian plugin**. It has two parts:

| Part | What | Does | Where |
|------|------|------|-------|
| Obsidian Plugin | `main.js` + `manifest.json` + `styles.css` | Dashboard, buttons, settings UI | `.obsidian/plugins/paperforge/` in your vault |
| Python Package | `paperforge` | Sync, OCR, Doctor, repair | Your system Python (`pip install`) |

The plugin is the **interface**. The Python package is the **engine**. Every button you click in the plugin actually runs a Python command behind the scenes.

**After installing the plugin, you MUST verify that the Python package is also installed and version-matched.**

---

## 1. Install the Obsidian Plugin

### Option A: Community Plugin Browser (Recommended)

1. Open Obsidian → `Settings` → `Community plugins` → `Browse`
2. Search for **PaperForge**
3. Click `Install`, then `Enable`

> Community plugins auto-update through Obsidian. No extra steps needed.

### Option B: BRAT

If you need beta versions or the plugin hasn't appeared in search yet:

1. Install **BRAT** from the Obsidian community plugin browser
2. Open BRAT settings → `Add Beta Plugin`
3. Enter: `https://github.com/LLLin000/PaperForge`
4. Enable PaperForge in Settings → Community Plugins

### Option C: Manual Download

1. Go to [Releases](https://github.com/LLLin000/PaperForge/releases)
2. Download the three files: `main.js`, `manifest.json`, `styles.css`
3. Create `.obsidian/plugins/paperforge/` in your vault
4. Put the three files there
5. Restart Obsidian → Settings → Community Plugins → enable PaperForge

> Manual install does not auto-update. You'll need to re-download for each new version.

---

## 2. Install the Python Package

After enabling the plugin, open the PaperForge settings tab. You'll see a **Runtime Status** section:

```
Plugin v1.5.0 → Python Package v1.5.0 ✓ Matched
```

- If it says "Not installed" → click **Open Wizard** to re-run the setup process
- If it says "Mismatch" → the Python package auto-updates when the plugin updates. If it didn't succeed, click **Update Runtime** to manually trigger

---

## 3. How Python Interpreter Resolution Works

PaperForge needs to find a working Python on your system. It searches in this order:

| Priority | Source | Description |
|----------|--------|-------------|
| 1 | **Manual override** | Settings → `Custom Python Path`, enter the full path (e.g., `C:\Users\you\...\python.exe`). **This is the most reliable method.** |
| 2 | **venv auto-detect** | Scans `.paperforge-test-venv`, `.venv`, `venv` under your vault root |
| 3 | **System auto-detect** | Tries `py -3`, `python`, `python3` in order, verifies with `--version` |
| 4 | **Fallback** | Defaults to `python` if nothing else works |

> If you have multiple Python installations (e.g., system 3.9 + self-installed 3.11), **strongly recommend setting a manual path** in settings to avoid hitting the wrong one.
>
> The **Validate** button in settings immediately tests the resolved interpreter and shows its version.

---

## 4. Setup Wizard — What Each Step Means

Open the plugin settings panel (`Settings` → `Community plugins` → `PaperForge`) and click the **Open Wizard** button. The wizard walks you through configuration. Here's what every step does.

### 4.1 Vault Path

Your Obsidian vault root. Auto-detected, usually no need to change.

### 4.2 AI Agent Platform

PaperForge's deep reading features run through an AI Agent. The core mechanism is **trigger phrases**, not registered plugins: you type `/pf-deep <key>` directly into the Agent chat, and the Agent recognizes the trigger and loads the `literature-qa` Skill automatically.

The setup wizard deploys Skill files to the correct location:

| Agent | Skill location | Trigger example |
|-------|---------------|-----------------|
| **OpenCode** | `.opencode/skills/` + `.opencode/command/` | `/pf-deep <key>` |
| **Claude Code** | `.claude/skills/` | `/pf-deep <key>` |
| **Cursor** | `.cursor/skills/` | `/pf-deep <key>` |
| **GitHub Copilot** | `.github/skills/` | `/pf-deep <key>` |
| **Windsurf** | `.windsurf/skills/` | `/pf-deep <key>` |
| **Codex** | `.codex/skills/` | `$pf-deep <key>` |
| **Cline** | `.clinerules/` | `/pf-deep <key>` |

> **Key concept**: `/pf-deep` is NOT a plugin you install on the Agent platform — it's a Skill file deployed inside your Vault. Once the setup wizard copies the files into place, the Agent auto-discovers the triggers on startup. You type the trigger phrase just like any other chat input.

### 4.3 Directory Names

The wizard asks what to name several directories. These are for organizing files inside your vault. **Defaults work for most users.**

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `system_dir` | `System` | Root for PaperForge internal data. Contains `exports/` (Zotero JSON exports), `ocr/` (OCR results), `config/`. You rarely need to open this manually. |
| `resources_dir` | `Resources` | Resources root. Your formal literature notes live under this directory, inside `literature_dir`. |
| `literature_dir` | `Literature` | Formal literature notes directory. `paperforge sync` generates frontmatter `.md` notes here. |
| `base_dir` | `Bases` | Obsidian Base view definitions. Dashboard filters ("Pending OCR", "Ready to Read", etc.) are stored here. |

### 4.4 PaddleOCR API Token

OCR requires a PaddleOCR API key. Configured in `.env`:

```
PADDLEOCR_API_TOKEN=your-api-key
```

The wizard guides you through setting this. You can also edit `.env` later. The OCR URL usually stays at the default.

### 4.5 Zotero Data Directory

PaperForge creates a junction (Windows) or symlink (macOS/Linux) linking your Zotero data directory into the vault. This is how Obsidian wikilinks resolve to PDF files.

The wizard auto-detects your Zotero installation. If detection fails, manually enter the path to your Zotero data directory — the folder that contains the `storage/` subdirectory (not the Zotero executable).

### 4.6 What Happens During Setup

After confirming your choices, the wizard automatically:
- Creates all needed directory structures
- Deploys Agent command files to the correct locations
- Installs Obsidian plugin files
- Creates the Zotero junction/symlink
- Writes `paperforge.json` and `.env`

The process is **incremental** — if files already exist in the chosen directories, the wizard only adds what's missing and never deletes existing content.

---

## 5. First-Time Setup Checklist

1. **Version match**: Settings → Runtime Status → confirm plugin and Python package match
2. **Python path**: Settings → Validate button → confirm it's the Python you want
3. **Setup wizard**: Settings → PaperForge → Open Wizard
4. **PaddleOCR key**: Enter your API token in `.env` (wizard guides this)
5. **Export from Zotero**: Right-click your library → `Export...` → format `Better BibTeX JSON` → check `Keep updated` → save to `<system_dir>/PaperForge/exports/`
6. **Run Doctor**: Dashboard → `Run Doctor` → all checks should pass

---

## 6. Daily Use

### Dashboard (Three-Mode Views)

`Ctrl+P` → `PaperForge: Open Dashboard` opens the control panel with three views:

| View | Purpose |
|------|---------|
| **Global** | System homepage: run Sync, OCR, Doctor, and other mechanical operations |
| **Collection** | Batch workspace: browse paper queues by domain, batch tagging |
| **Per-paper** | Reading companion: `do_ocr` / `analyze` toggle checkboxes, discussion record cards |

> PDF files in the Dashboard automatically switch to Per-paper mode — no manual switching needed.

### AI Deep Reading & Q&A (Requires Agent)

Launch your Agent app and type commands into its chat input. **The more specific you are about the paper (Zotero Key, title, DOI), the faster the Agent locates it.**

| Route | Command | Does | Trigger examples | Prerequisites |
|-------|---------|------|-----------------|--------------|
| Deep Read | `/pf-deep <key>` | Keshav three-pass deep reading, writes to formal note | `deep read XX`, `walk me through`, `journal club` | OCR done, analyze: true |
| Q&A | `/pf-paper <key>` | Interactive paper Q&A, OCR not required | `take a look at XX`, `what does this paper say` | Formal note exists |
| Archive | `/pf-end` | Save current `/pf-paper` Q&A session | `save`, `end discussion` | During `/pf-paper` session |

### `/pf-end` Details

- `/pf-end` only applies to `/pf-paper` Q&A sessions. Deep reading (`/pf-deep`) writes directly to the formal note and does not need `/pf-end`.
- When executed, two files are created in the paper's workspace:
  - `discussion.md` — human-readable Q&A discussion record
  - `discussion.json` — structured Q&A data (with timestamps, source tags)
- Dashboard **Per-paper** view automatically displays these as discussion record cards

> Command prefixes vary by platform (mostly `/`, Codex uses `$`).

---

## 7. Full Workflow

```
Add paper to Zotero
  ↓ Better BibTeX auto-exports JSON to exports/
Dashboard → Sync Library
  ↓ Generates formal note (in Literature/, with frontmatter metadata)
Set do_ocr: true in the note's frontmatter
  ↓
Dashboard → Run OCR
  ↓ PaddleOCR extracts full text + figures → ocr/ directory
Set analyze: true in the note's frontmatter
  ↓
Open Agent → type /pf-deep <zotero_key>
  ↓ Agent performs three-pass deep reading
## 🔍 Deep Reading section appears in the note
  ↓ (for additional Q&A)
Open Agent → type /pf-paper <zotero_key>
  ↓ Interactive Q&A
Type /pf-end to save the discussion record
  ↓
Dashboard Per-paper view shows discussion cards
```

---

## 8. Troubleshooting

### Plugin fails to load

- Confirm `.obsidian/plugins/paperforge/` has `main.js`, `manifest.json`, `styles.css`
- If upgrading from an old version: delete the entire `paperforge` plugin folder and reinstall via the community plugin browser
- Open Developer Console (`Ctrl+Shift+I`) and check the red errors

### "Sync Runtime" doesn't update the version

- The plugin may be calling a different Python than your terminal. Check Settings → Python path
- Try with `--no-cache-dir` to bypass pip cache
- Confirm `https://github.com/LLLin000/PaperForge` is reachable

### OCR stays pending

- Confirm `.env` has `PADDLEOCR_API_TOKEN`
- Run `paperforge ocr --diagnose` to check API connectivity
- PDF paths may be broken: run `paperforge repair --fix-paths`

### No notes generated after sync

- Is Better BibTeX auto-export configured in Zotero? Are JSON files in `exports/`?
- Run `paperforge doctor` to find which step failed

### /pf-deep command does nothing

- Make sure you're running it in your Agent app, not a terminal
- Confirm OCR is done (`ocr_status: done`)
- Confirm `analyze` is set to `true`

---

## 9. Updating

The Obsidian plugin auto-updates through the community plugin browser. For the Python package:

```bash
paperforge update
# or
pip install --upgrade paperforge
```

If you installed via BRAT, it also auto-detects GitHub Release updates.

---

## 10. Architecture

```
paperforge/
├── core/          Contract layer — PFResult/ErrorCode/state machine
├── adapters/      Adapter layer — BBT parsing, paths, frontmatter I/O
├── services/      Service layer — SyncService orchestration
├── worker/        Worker layer — OCR, status, repair
├── commands/      CLI dispatch
├── setup/         Setup wizard (directories, agent deployment, Zotero linking)
├── plugin/        Obsidian plugin (Dashboard, settings panel)
└── schema/        Field registry
```

---

## License

[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Non-commercial use only.

## Acknowledgments

Built on [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR), [Obsidian](https://obsidian.md), [Better BibTeX for Zotero](https://retorque.re/zotero-better-bibtex/), and other great open-source projects.
