# PaperForge Installation Guide

> Canonical install reference. For other docs, see [README.md](README.md).

---

## Method 1: Obsidian Plugin (Recommended)

1. Download the plugin files from the [latest release](https://github.com/LLLin000/PaperForge/releases/latest).
2. Extract and copy the files into `vault/.obsidian/plugins/paperforge/`.
3. Open Obsidian -> Settings -> Community Plugins -> Enable `PaperForge`.
4. Open PaperForge settings and click `Open Installation Wizard`.
5. Follow the 5-step guided setup: Overview -> Directory Config -> Agent & Keys -> Install -> Done.

> The wizard auto-detects Python, Zotero, and Better BibTeX before installation starts.

---

## Method 2: CLI via pip (Developers)

```bash
pip install paperforge
```

Then run the headless setup:

```bash
python -m paperforge setup --headless --agent opencode --paddleocr-key <key>
```

For the latest stable release, replace `master` with a version tag:

```bash
pip install paperforge==1.5.2
```

---

## Method 3: AI Agent Setup

Copy the following to your AI agent for a guided headless install:

- English: [docs/ai-agent-setup-guide.md](docs/ai-agent-setup-guide.md)
- 中文: [docs/ai-agent-setup-guide-zh.md](docs/ai-agent-setup-guide-zh.md)

---

## Prerequisites

| Software | Purpose | Get it |
|----------|---------|--------|
| Python 3.10+ | Run PaperForge CLI and backend tasks | https://python.org |
| Zotero | Literature management | https://zotero.org |
| Better BibTeX | Auto-export metadata as JSON | https://retorque.re/zotero-better-bibtex/ |
| PaddleOCR Key | OCR text and layout extraction | https://aistudio.baidu.com/paddleocr |

---

## Post-Installation

After installing, see [AGENTS.md](AGENTS.md) for first-use workflow and detailed command reference.
