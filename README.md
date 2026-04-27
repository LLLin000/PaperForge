# PaperForge Lite

[![PyPI version](https://img.shields.io/pypi/v/paperforge?style=for-the-badge&logo=pypi&logoColor=white&color=3775A9)](https://pypi.org/project/paperforge/)
[![Python version](https://img.shields.io/pypi/pyversions/paperforge?style=for-the-badge&logo=python&logoColor=white&color=3775A9)](https://python.org)
[![License](https://img.shields.io/github/license/LLLin000/PaperForge?style=for-the-badge&color=brightgreen)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/LLLin000/PaperForge?style=for-the-badge&logo=github&color=181717)](https://github.com/LLLin000/PaperForge)

[简体中文](README.zh-CN.md) · **English**

**An automated deep-reading workflow for medical literature, powered by Obsidian + Zotero + PaddleOCR. Upload a PDF and get a structured, AI-written reading note — with a single command.**

```bash
pip install git+https://github.com/LLLin000/PaperForge.git
paperforge setup
```

*"From PDF to structured reading notes in two commands."*

---

## Pipeline

```
Zotero: new paper added
    │ Better BibTeX auto-exports JSON
    ▼
paperforge sync    ─── Sync Zotero → generate formal notes
    │
    ▼
paperforge ocr     ─── Upload PDF → auto-poll → download fulltext + figures
    │
    ▼
/pf-deep <key>     ─── AI 3-pass deep reading → write to Obsidian note
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
| **Pre-commit gates** | ruff lint + format + consistency audit |
| **Cross-platform** | Windows / macOS / Linux |

---

## Quick Start

### Install

```bash
pip install git+https://github.com/LLLin000/PaperForge.git
paperforge setup
```

The interactive wizard handles: agent platform selection, vault directory setup, Zotero data linking, PaddleOCR API key configuration. See [setup-guide.md](docs/setup-guide.md) for a step-by-step walkthrough.

> Windows one-click installer:
> ```powershell
> powershell -c "iwr -Uri https://raw.githubusercontent.com/LLLin000/PaperForge/master/scripts/install-paperforge.ps1 -OutFile install.ps1; ./install.ps1"
> paperforge setup
> ```

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
| | `paperforge update` | Auto-update |
| | `paperforge --verbose` | DEBUG-level logging |

### Agent (via OpenCode)

| Command | What it does | Required |
|---------|-------------|----------|
| `/pf-deep <key>` | Full 3-pass deep reading | OCR complete |
| `/pf-paper <key>` | Quick summary | Formal note exists |
| `/pf-sync` | Sync Zotero | Installed |
| `/pf-ocr` | Run OCR | Installed |
| `/pf-status` | System status | Installed |

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
  "version": "1.4.1",
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
| [📎 v1.4 Migration](docs/MIGRATION-v1.4.md) | Upgrading from v1.3 |

---

## License

MIT License
