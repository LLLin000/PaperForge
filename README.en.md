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
Plugin v1.5.0 → Python Package v1.5.0 ✓ Matched
```

- If it says "Not installed" → click **Open Wizard** to re-run the setup process
- If it says "Mismatch" → the Python package auto-updates when the plugin updates. If it didn't succeed, click **Update Runtime** to manually trigger

---

## 3. Quickstart

```bash
# 1. Export from Zotero (Better BibTeX JSON, Keep updated) to exports/
# 2. Sync
paperforge sync

# 3. Mark a paper for OCR in its frontmatter: do_ocr: true
# 4. Run OCR
paperforge ocr

# 5. Mark for deep reading: analyze: true
# 6. In your Agent chat:
/pf-deep <zotero_key>
```

---

## Documentation

| If you want to                          | Read                                      |
| --------------------------------------- | ----------------------------------------- |
| Full tutorial, from install to deep read | [Getting Started](docs/getting-started.md) |
| Troubleshooting                         | [Troubleshooting](docs/troubleshooting.md) |
| Command reference                       | [Commands](docs/COMMANDS.md)              |
| How to update                           | [Update Guide](docs/update-upgrade.md)    |
| Architecture / Maintenance / Release    | [Architecture](docs/ARCHITECTURE.md)      |
| AI Agent collaboration                  | [AGENTS.md](AGENTS.md)                    |

---

## License

[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Non-commercial use only.

## Acknowledgments

Built on [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR), [Obsidian](https://obsidian.md), [Better BibTeX for Zotero](https://retorque.re/zotero-better-bibtex/), and other great open-source projects.
