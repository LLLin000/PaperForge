```
    ______  ___  ______ _________________ ___________ _____  _____
    | ___ \/ _ \ | ___ \  ___| ___ \  ___|  _  | ___ \  __ \|  ___|
    | |_/ / /_\ \| |_/ / |__ | |_/ / |_  | | | | |_/ / |  \/| |__
    |  __/|  _  ||  __/|  __||    /|  _| | | | |    /| | __ |  __|
    | |   | | | || |   | |___| |\ \| |   \ \_/ / |\ \| |_\ \| |___
    \_|   \_| |_/\_|   \____/\_| \_\_|    \___/\_| \_|\____/\____/
```

# PaperForge

[![Version](https://img.shields.io/badge/version-1.4.11-blue?style=for-the-badge)](https://github.com/LLLin000/PaperForge/releases)
[![Python](https://img.shields.io/pypi/pyversions/paperforge?style=for-the-badge&logo=python&logoColor=white&color=3775A9)](https://python.org)
[![License](https://img.shields.io/github/license/LLLin000/PaperForge?style=for-the-badge&color=brightgreen)](LICENSE)

[简体中文](README.zh-CN.md) · **English**

**Obsidian + Zotero literature pipeline. One plugin install, no terminal required.**

```text
Download plugin → Enable in Obsidian → Open wizard → Fill config → Click Install → Done
```

*"From PDF to structured reading notes — all inside Obsidian."*

---

## What PaperForge Does

PaperForge turns your Zotero library into an AI-ready literature knowledge base:

| Layer | What you get | How to use it |
|-------|-------------|---------------|
| **Literature index** | Structured notes with frontmatter (title, authors, journal, DOI, tags, abstract) | Search, browse, filter via Base views |
| **Full-text corpus** | OCR-extracted markdown (`fulltext.md`) | Feed to LLMs for RAG or question answering |
| **Figure database** | Figure-map with images + captions for every chart/table | Multimodal AI: "show me Figure 3 and explain" |
| **Deep reading** | AI-written 3-pass analysis with chart review and critical evaluation | Literature synthesis, systematic reviews |

---

## Install

### Obsidian Plugin (Recommended)

1. **Download** the plugin files from the [latest release](https://github.com/LLLin000/PaperForge/releases/latest)

2. **Copy** into your vault: `{vault}/.obsidian/plugins/paperforge/`

3. **Enable** in Obsidian: Settings → Community Plugins → PaperForge

4. **Open the wizard**: Settings → PaperForge → "打开安装向导"

5. **Follow 5 steps**: Overview → Directory Config → Agent & Keys → Install → Done

> The wizard auto-detects Python, Zotero, and Better BibTeX before starting.

### Prerequisites

| Software | Purpose | Get it |
|----------|---------|--------|
| Python 3.9+ | Run PaperForge CLI | https://python.org |
| Zotero | Literature management | https://zotero.org |
| Better BibTeX | Zotero plugin for JSON export | https://retorque.re/zotero-better-bibtex/ |
| PaddleOCR Key | OCR text extraction | https://aistudio.baidu.com/paddleocr |

### CLI (Advanced)

```bash
cd /path/to/your/vault
pip install git+https://github.com/LLLin000/PaperForge.git
python -m paperforge setup --headless --agent opencode --paddleocr-key <key>
```

---

## Usage (All in Obsidian)

| Action | How |
|--------|-----|
| **Open Dashboard** | `Ctrl+P` → "PaperForge: Open Dashboard", or click sidebar book icon |
| **Sync Literature** | Dashboard → "Sync Library" — pulls from Zotero, generates notes |
| **Run OCR** | Dashboard → "Run OCR" — extracts full text & figures |
| **Deep Read** | `/pf-deep <zotero_key>` — AI 3-pass analysis (must run in AI agent) |
| **Quick Query** | `/pf-paper <zotero_key>` — fast paper Q&A |

### Dashboard

```
┌──────────────────────────────────┐
│  PaperForge                   ↻  │
│                                  │
│  [Papers: 550] [Notes: 520] [...]│
│                                  │
│  OCR Pipeline  [Active]          │
│  ████████████░░░░░░░ 80%         │
│  Pending: 10  Active: 2  Done: 8│
│                                  │
│  Quick Actions                   │
│  [Sync Library] [Run OCR]        │
└──────────────────────────────────┘
```

---

## Commands

### Obsidian Command Palette (`Ctrl+P`)

| Command | Description |
|---------|-------------|
| `PaperForge: Open Dashboard` | Open status panel with metrics and quick actions |
| `PaperForge: Sync Library` | Sync Zotero and generate notes |
| `PaperForge: Run OCR` | Extract PDF full text and figures |

### Agent Commands

| Command | Description | Requires |
|---------|-------------|----------|
| `/pf-deep <key>` | Full 3-pass deep reading | OCR complete |
| `/pf-paper <key>` | Quick Q&A | Formal note exists |
| `/pf-sync` | Sync Zotero | Installed |
| `/pf-ocr` | Run OCR | Installed |
| `/pf-status` | System status | Installed |

### CLI (Optional)

| Command | Description |
|---------|-------------|
| `paperforge sync` | Sync Zotero, generate notes |
| `paperforge ocr` | Run OCR |
| `paperforge status` | System overview |
| `paperforge doctor` | Diagnose configuration |
| `paperforge update` | Auto-update |

---

## Supported Agent Platforms

| Platform | Agent Commands | Setup |
|----------|---------------|-------|
| **OpenCode** | Full support (all `/pf-*` commands) | `.opencode/command/` + `.opencode/skills/` |
| **Claude Code** | `/pf-deep`, `/pf-paper` | `.claude/skills/` |
| **Cursor** | `/pf-deep`, `/pf-paper` | `.cursor/skills/` |
| **GitHub Copilot** | `/pf-deep`, `/pf-paper` | `.github/skills/` |
| **Windsurf** | `/pf-deep`, `/pf-paper` | `.windsurf/skills/` |
| **Codex** | `$pf-deep`, `$pf-paper` | `.codex/skills/` |
| **Cline** | `/pf-deep`, `/pf-paper` | `.clinerules/` |

Select your platform in the wizard — files are deployed automatically.

---

## Configuration

All config is handled by the setup wizard. Generated files:

```
vault/
├── paperforge.json          ← directory config + agent platform
├── System/
│   └── PaperForge/
│       ├── .env             ← PaddleOCR API key
│       ├── exports/         ← Better BibTeX JSON exports go here
│       └── config/          ← domain-collections.json
├── Resources/
│   ├── Notes/               ← formal literature notes (metadata + deep reading)
│   └── Index_Cards/         ← index records (one per paper, by domain)
└── Base/                   ← Obsidian Base views (filterable table views)
```

Environment variables (optional overrides):

| Variable | Default | Description |
|----------|---------|-------------|
| `PADDLEOCR_API_TOKEN` | — | PaddleOCR API Key |
| `PAPERFORGE_LOG_LEVEL` | `INFO` | Logging level |

---

## Update

Auto-update on every Obsidian restart (can be disabled in plugin settings). Or manually:

```bash
paperforge update
# or
pip install --upgrade git+https://github.com/LLLin000/PaperForge.git
```

---

## Documentation

| Document | Content |
|----------|---------|
| [Setup Guide](docs/setup-guide.md) | Step-by-step from zero to running |
| [Quick Install](docs/INSTALLATION.md) | Concise install instructions |
| [Post-Install Guide](AGENTS.md) | First-time user guide and workflow |
| [Changelog](CHANGELOG.md) | Version history |
| [Contributing](CONTRIBUTING.md) | Dev setup and conventions |

---

## License

MIT License
