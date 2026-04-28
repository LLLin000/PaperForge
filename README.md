```
    ______  ___  ______ _________________ ___________ _____  _____
    | ___ \/ _ \ | ___ \  ___| ___ \  ___|  _  | ___ \  __ \|  ___|
    | |_/ / /_\ \| |_/ / |__ | |_/ / |_  | | | | |_/ / |  \/| |__
    |  __/|  _  ||  __/|  __||    /|  _| | | | |    /| | __ |  __|
    | |   | | | || |   | |___| |\ \| |   \ \_/ / |\ \| |_\ \| |___
    \_|   \_| |_/\_|   \____/\_| \_\_|    \___/\_| \_|\____/\____/
```

# PaperForge

[![PyPI version](https://img.shields.io/pypi/v/paperforge?style=for-the-badge&logo=pypi&logoColor=white&color=3775A9)](https://pypi.org/project/paperforge/)
[![Python version](https://img.shields.io/pypi/pyversions/paperforge?style=for-the-badge&logo=python&logoColor=white&color=3775A9)](https://python.org)
[![License](https://img.shields.io/github/license/LLLin000/PaperForge?style=for-the-badge&color=brightgreen)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/LLLin000/PaperForge?style=for-the-badge&logo=github&color=181717)](https://github.com/LLLin000/PaperForge)

[简体中文](README.zh-CN.md) · **English**

**An automated deep-reading workflow for medical literature, powered by Obsidian + Zotero + PaddleOCR. Upload a PDF and get a structured, AI-written reading note — with a single command.**

```bash
# First, cd to the OB vault directory
pip install git+https://github.com/LLLin000/PaperForge.git
paperforge setup
```

*"From PDF to structured reading notes in two commands."*

---

### What PaperForge Builds For You

PaperForge turns your Zotero library into an **AI-ready literature knowledge base**:

| Layer | What you get | How to use it |
|-------|-------------|---------------|
| **Literature index** | Formal notes with structured frontmatter (title, authors, journal, DOI, PMID, tags, abstract) | Semantic search, Zotero-independent browsing |
| **Full-text corpus** | Clean OCR-extracted markdown (`fulltext.md`) | Chunk → embed → RAG, or feed directly to LLMs |
| **Figure database** | Figure-map with image links + captions for every chart and table | Multimodal RAG: "show me Figure 3 + explain" |
| **Expert analysis** | Structured deep-reading notes with Keshav 3-pass analysis, chart review, critical evaluation | LLM reasoning ground truth, literature synthesis, systematic reviews |

**Not just a note-taking tool.** Your vault becomes a queryable knowledge base that any AI tool (OpenCode, Claude Code, Cursor, or custom RAG pipelines with qmd/LlamaIndex) can read, search, and reason over.

---

## Full Workflow

```
┌─────────────────────────────────────────────────────────┐
│              Literature Management                        │
│                                                          │
│  New paper in Zotero                                     │
│    │ Better BibTeX auto-export JSON                      │
│    ▼                                                     │
│  paperforge sync  ─── Sync Zotero → generate notes       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│               OCR (Full-text Extraction)                  │
│                                                          │
│  paperforge ocr    ─── Upload PDF → poll → download      │
│                          │                                │
│    ┌─────────────────────┼─────────────────────┐         │
│    │ fulltext.md         │ images/             │         │
│    │ extracted text      │ chart images        │         │
│    └─────────────────────┴─────────────────────┘         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Deep Reading                                 │
│                                                          │
│  /pf-deep <key>  ─── AI 3-pass reading                   │
│                          │                                │
│    Pass 1: Overview   ─── 5Cs quick assessment           │
│    Pass 2: Close read ─── figure-by-figure + chart review │
│    Pass 3: Synthesis  ─── critique + research transfer   │
│                          │                                │
│    ▼                                                     │
│  Obsidian note ─── ## 🔍 Deep Reading section populated  │
└─────────────────────────────────────────────────────────┘
```

---

## Features

| Feature | Description |
|---------|-------------|
| **One-shot OCR** | Upload → poll → download, all in one command |
| **3-pass deep reading** | Keshav method + 6 fixed sub-heading skeleton, AI fills blanks |
| **Chart review** | 19 chart types auto-detected with expert review checklists |
| **Auto retry** | Exponential backoff on network failures |
| **Structured logging** | Global `--verbose` flag, stderr diagnostics |
| **Progress bars** | tqdm with `--no-progress` flag for quiet mode |
| **Zotero sync** | Better BibTeX auto-export, bidirectional |
| **Obsidian Base** | Literature queue management via Base views |
| **Obsidian plugin** | Status panel + command palette integration |
| **Multi-agent** | OpenCode, Claude Code, Codex, Cursor, Copilot, Windsurf, Cline, Augment, Trae |
| **Pre-commit gates** | ruff lint + format + consistency audit |
| **Cross-platform** | Windows / macOS / Linux |

---

## Quick Start

### Install — Let your AI agent do it (Recommended)

Copy and paste this prompt to your AI agent (OpenCode, Cursor, Claude Code, etc.):

```
Install PaperForge in this vault by following:
https://raw.githubusercontent.com/LLLin000/PaperForge/master/docs/ai-agent-setup-guide.md
```

The agent will ask a few questions, then install everything. Done.

### Install — Do it yourself

First, `cd` to your Obsidian vault root:

```bash
cd /path/to/your/vault
pip install git+https://github.com/LLLin000/PaperForge.git
paperforge setup
```

The interactive wizard handles: agent platform selection, vault directory setup, Zotero data linking, PaddleOCR API key configuration. See [setup-guide.md](docs/setup-guide.md) for a step-by-step walkthrough.

> For AI agents reading this: use the headless mode — `paperforge setup --headless --agent <agent_key>`. Supported agents: opencode, claude, codex, cursor, copilot, windsurf, cline, augment, trae. Full instructions in [docs/ai-agent-setup-guide.md](docs/ai-agent-setup-guide.md).

### Prerequisites

| Software | Purpose | Get it |
|----------|---------|--------|
| Python 3.10+ | Run PaperForge | https://python.org |
| Zotero | Literature management | https://zotero.org |
| Better BibTeX | Zotero plugin | https://retorque.re/zotero-better-bibtex/ |
| Obsidian | Note-taking | https://obsidian.md |
| PaddleOCR API Key | OCR service | https://paddleocr.baidu.com |

---

## Commands

### Terminal

| Category | Command | What it does |
|----------|---------|-------------|
| **Setup** | `paperforge setup` | Run setup wizard |
| | `paperforge doctor` | Diagnose configuration |
| **Sync** | `paperforge sync` | Sync Zotero, generate notes |
| **OCR** | `paperforge ocr` | One-shot OCR (upload → poll → download) |
| | `paperforge ocr --diagnose` | OCR configuration check |
| | `paperforge ocr --no-progress` | Quiet mode |
| **Reading** | `paperforge deep-reading` | Show deep-reading queue |
| **Maintenance** | `paperforge status` | System status |
| | `paperforge status --json` | JSON output for tooling |
| | `paperforge update` | Auto-update |
| | `paperforge --verbose` | DEBUG-level logging |

### Agent (OpenCode / Claude Code / Codex / Cursor / Copilot)

| Command | What it does | Required |
|---------|-------------|----------|
| `/<prefix>pf-deep <key>` | Full 3-pass deep reading | OCR complete |
| `/<prefix>pf-paper <key>` | Quick Q&A | Formal note exists |
| `/pf-sync` | Sync Zotero (OpenCode only) | Installed |
| `/pf-ocr` | Run OCR (OpenCode only) | Installed |
| `/pf-status` | System status (OpenCode only) | Installed |

> Prefix: `/` for Claude Code / OpenCode / Copilot, `$` for Codex. CLI-only commands (sync, ocr, status) are available as OpenCode commands or via terminal.

---

## First Run

```bash
# 1. Sync Zotero
paperforge sync

# 2. Mark papers for reading in Obsidian (set do_ocr: true, analyze: true)

# 3. Run OCR
paperforge ocr

# 4. Deep read (in OpenCode)
/pf-deep XXXXXXX
```

---

## Update

```bash
paperforge update
# or
pip install --upgrade git+https://github.com/LLLin000/PaperForge.git
```

---

## Configuration

### paperforge.json

```json
{
  "version": "1.4.3",
  "system_dir": "99_System",
  "resources_dir": "03_Resources",
  "literature_dir": "Literature",
  "control_dir": "LiteratureControl",
  "base_dir": "05_Bases",
  "auto_analyze_after_ocr": false
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PADDLEOCR_API_TOKEN` | — | PaddleOCR API Key |
| `PADDLEOCR_JOB_URL` | `https://paddleocr.aistudio-app.com/api/v2/ocr/jobs` | API endpoint |
| `PAPERFORGE_LOG_LEVEL` | `INFO` | Logging level |
| `PAPERFORGE_RETRY_MAX` | `5` | Upload retry count |
| `PAPERFORGE_POLL_MAX_CYCLES` | `20` | Max poll cycles |

---

## Documentation

| Document | What it covers |
|----------|---------------|
| [📖 Setup Guide](docs/setup-guide.md) | Step-by-step from zero to running |
| [⚡ Quick Install](docs/INSTALLATION.md) | Concise install instructions |
| [📋 Post-Install Guide](AGENTS.md) | First-time user guide |
| [📝 Changelog](CHANGELOG.md) | Version history |
| [🤝 Contributing](CONTRIBUTING.md) | dev setup and conventions |


---

## License

MIT License
