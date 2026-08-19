# PaperForge Installation Guide

> Canonical install reference. For other docs, see [README.md](README.md).
> PaperForge is a standalone Python application; Obsidian is an optional
> GUI client, not the host.

---

## Method 1: CLI via pip (Recommended)

```bash
pip install paperforge
```

Then initialize in a vault:

```bash
paperforge setup --modular
```

`setup` is interactive-friendly and headless-safe:
- unlisted directory flags keep existing config values (fresh vaults get
  canonical defaults: `System` / `Resources/Literature` /
  `Resources/LiteratureControl` / `Bases`);
- credentials NEVER go on the command line — set them via the credential
  authority after setup:
  ```bash
  paperforge auth set ocr        # prompts for the PaddleOCR token securely
  ```
- verify the installation:
  ```bash
  paperforge doctor --json
  paperforge status --json
  ```

Optional flags: `--system-dir`, `--resources-dir`, `--literature-dir`,
`--base-dir`, `--zotero-data <path>`, `--agent <platform>`.

## Method 2: Obsidian Plugin (Optional Client)

1. Download the plugin files from the [latest release](https://github.com/LLLin000/PaperForge/releases/latest).
2. Extract and copy the files into `vault/.obsidian/plugins/paperforge/`.
3. Open Obsidian -> Settings -> Community Plugins -> Enable `PaperForge`.

The plugin is a presentation layer over the same Python core; all state,
configuration, and lifecycle authority lives in PaperForge.

## Method 3: AI Agent Setup

Copy the following to your AI agent for a guided install:

- English: [docs/ai-agent-setup-guide.md](docs/ai-agent-setup-guide.md)
- 中文: [docs/ai-agent-setup-guide-zh.md](docs/ai-agent-setup-guide-zh.md)

The agent runs `paperforge setup inspect` (or `setup --modular`) and
follows the skill protocol; it never asks you to paste API keys into chat
or onto the command line.

---

## Prerequisites

| Software | Purpose | Get it |
|----------|---------|--------|
| Python 3.11+ | Run PaperForge CLI and backend tasks | https://python.org |
| Zotero | Literature management | https://zotero.org |
| Better BibTeX | Auto-export metadata as JSON | https://retorque.re/zotero-better-bibtex/ |
| PaddleOCR Key (optional) | OCR text and layout extraction | https://aistudio.baidu.com/paddleocr |

---

## Post-Installation

After installing, see [AGENTS.md](AGENTS.md) for first-use workflow and detailed command reference.
