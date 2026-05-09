<p align="center">
  <img src="docs/images/paperforge-banner.png" alt="PaperForge banner" width="100%" />
</p>

# PaperForge

[![Version](https://img.shields.io/github/v/release/LLLin000/PaperForge?style=for-the-badge&label=version)](https://github.com/LLLin000/PaperForge/releases)
[![Python](https://img.shields.io/pypi/pyversions/paperforge?style=for-the-badge&logo=python&logoColor=white&color=3775A9)](https://python.org)
[![License](https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgreen?style=for-the-badge)](LICENSE)

[简体中文](README.md) · **English**

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

### Option A: BRAT (Recommended)

1. Install **BRAT** from the Obsidian community plugin browser
2. Open BRAT settings → `Add Beta Plugin`
3. Enter: `https://github.com/LLLin000/PaperForge`
4. BRAT downloads the latest `main.js`, `manifest.json`, and `styles.css` and installs them
5. Settings → Community Plugins → enable PaperForge

> BRAT auto-detects GitHub Release updates. No manual downloads needed.

### Option B: Manual Download

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
Plugin v1.4.17 → Python Package v1.4.17 ✓ Matched
```

- If it says "Not installed" → click **Sync Runtime**, or run manually:
  ```bash
  pip install --upgrade git+https://github.com/LLLin000/PaperForge.git@1.4.17
  ```
- If it says "Mismatch" → the versions are out of sync. Click "Sync Runtime" to pull the matching package version.

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

`Ctrl+P` → `PaperForge: Run Setup Wizard` walks you through configuration. Here's what every step does.

### 4.1 Vault Path

Your Obsidian vault root. Auto-detected, usually no need to change.

### 4.2 AI Agent Platform

PaperForge's deep reading features run through an AI Agent. Choose your platform, and the wizard deploys the command files to the right location.

| Agent | Files deployed to | Prefix | How to trigger deep reading |
|-------|------------------|--------|---------------------------|
| **OpenCode** | `.opencode/command/` + `.opencode/skills/` | `/` | Open OpenCode, type `/pf-deep <key>` |
| **Claude Code** | `.claude/skills/` | `/` | Open Claude Code, type `/pf-deep <key>` |
| **Cursor** | `.cursor/skills/` | `/` | Open Cursor AI Chat, type `/pf-deep <key>` |
| **GitHub Copilot** | `.github/skills/` | `/` | Open Copilot Chat, type `/pf-deep <key>` |
| **Windsurf** | `.windsurf/skills/` | `/` | Open Windsurf, type `/pf-deep <key>` |
| **Codex** | `.codex/skills/` | `$` | Open Codex, type `$pf-deep <key>` |
| **Cline** | `.clinerules/` | `/` | Open Cline, type `/pf-deep <key>` |

> Important: `/pf-deep` and `/pf-paper` are **NOT terminal commands**. You must first launch the Agent application, then type the command into that Agent's chat input. The Agent will invoke PaperForge's deep reading scripts to analyze your paper.

### 4.3 Directory Names

The wizard asks what to name several directories. These are for organizing files inside your vault. **Defaults work for most users.**

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `system_dir` | `99_System` | Root for PaperForge internal data. Contains `exports/` (Zotero JSON exports), `ocr/` (OCR results), `config/`. You rarely need to open this manually. |
| `resources_dir` | `03_Resources` | Resources root. Your formal literature notes live under this directory, inside `literature_dir`. |
| `literature_dir` | `Literature` | Where formal literature notes (`.md` files with frontmatter) are saved by `paperforge sync`. This is where you read and edit your notes. |
| `control_dir` | `LiteratureControl` | Internal control data directory. Stores index cards and library records. No manual access needed. |
| `base_dir` | `05_Bases` | Obsidian Base view definitions. Dashboard filters ("Pending OCR", "Ready to Read", etc.) are stored here. |

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
3. **Setup wizard**: `Ctrl+P` → `PaperForge: Run Setup Wizard`
4. **PaddleOCR key**: Enter your API token in `.env` (wizard guides this)
5. **Export from Zotero**: Right-click your library → `Export...` → format `Better BibTeX JSON` → check `Keep updated` → save to `<system_dir>/PaperForge/exports/`
6. **Run Doctor**: Dashboard → `Run Doctor` → all checks should pass

---

## 6. Daily Use

All mechanical operations from the Dashboard:

| What you want | How |
|---------------|-----|
| Open dashboard | `Ctrl+P` → `PaperForge: Open Dashboard` |
| Sync library | Dashboard → `Sync Library` |
| Run OCR | Dashboard → `Run OCR` |
| Check health | Dashboard → `Run Doctor` |

### AI Deep Reading (Requires Agent)

| Command | Does | Prerequisites |
|---------|------|--------------|
| `/pf-deep <zotero_key>` | Full three-pass deep reading | OCR done, analyze set to true |
| `/pf-paper <zotero_key>` | Quick paper summary | Formal note exists |
| `/pf-sync` | Agent syncs Zotero for you | Installed |
| `/pf-ocr` | Agent runs OCR for you | Installed |
| `/pf-status` | Agent checks system status | Installed |

> **How to use**: Launch your chosen Agent app (OpenCode / Claude Code / Cursor / ...), then type these commands into its chat input. Prefixes vary by platform (mostly `/`, Codex uses `$`).

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
```

---

## 8. Troubleshooting

### Plugin fails to load

- Confirm `.obsidian/plugins/paperforge/` has `main.js`, `manifest.json`, `styles.css`
- If upgrading via BRAT from an old version: delete the entire `paperforge` plugin folder and let BRAT re-download
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

BRAT auto-detects plugin updates. For the Python package:

```bash
paperforge update
# or
pip install --upgrade git+https://github.com/LLLin000/PaperForge.git
```

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
