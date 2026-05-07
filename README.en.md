<p align="center">
  <img src="docs/images/paperforge-banner.png" alt="PaperForge banner" width="100%" />
</p>

# PaperForge

[![Version](https://img.shields.io/github/v/release/LLLin000/PaperForge?style=for-the-badge&label=version)](https://github.com/LLLin000/PaperForge/releases)
[![Python](https://img.shields.io/pypi/pyversions/paperforge?style=for-the-badge&logo=python&logoColor=white&color=3775A9)](https://python.org)
[![License](https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgreen?style=for-the-badge)](LICENSE)

[简体中文](README.md) · **English**

> **Forge Knowledge, Empower Insight.**

PaperForge is an Obsidian-based literature workspace for researchers.
It turns Zotero libraries, PDFs, figures, and OCR output into structured notes, searchable corpora, and AI-ready reading workflows.

The tone of the project is inspired by a forge: raw papers go in, usable knowledge assets come out. The product itself stays practical, installation-focused, and built for real research work.

```text
Download plugin → Enable in Obsidian → Open wizard → Fill config → Click Install → Done
```

## What PaperForge Does

PaperForge connects the full path from source literature to structured insight.

| Layer | Output | Use it for |
|-------|--------|------------|
| **Index cards** | Structured metadata records with frontmatter | Search, browse, Base views |
| **Full-text corpus** | OCR-generated `fulltext.md` | LLM workflows, RAG, QA |
| **Figure database** | Figure images, captions, and figure maps | Multimodal analysis and evidence tracing |
| **Deep reading notes** | 3-pass AI analysis with chart review and critique | Reviews, synthesis, writing prep |

## Why It Feels Different

- **Short setup path**: plugin install plus guided wizard, not a terminal-heavy onboarding.
- **Full workflow**: sync, OCR, figures, notes, and agent commands live around the same vault.
- **AI-ready outputs**: not just files, but research assets that are easy to retrieve, inspect, and reuse.
- **Built around existing tools**: PaperForge extends Zotero and Obsidian instead of replacing them.

## Install

### Obsidian Plugin (Recommended)

1. Download the plugin files from the [latest release](https://github.com/LLLin000/PaperForge/releases/latest).
2. Copy them into `vault/.obsidian/plugins/paperforge/`.
3. Enable `PaperForge` in Obsidian community plugins.
4. Open the settings page and click `打开安装向导`.
5. Follow the 5-step wizard: Overview → Directory Config → Agent & Keys → Install → Done.

> The wizard auto-detects Python, Zotero, and Better BibTeX before installation starts.

### Prerequisites

| Software | Purpose | Get it |
|----------|---------|--------|
| Python 3.10+ | Run PaperForge CLI and backend tasks | https://python.org |
| Zotero | Literature management | https://zotero.org |
| Better BibTeX | Auto-export metadata as JSON | https://retorque.re/zotero-better-bibtex/ |
| PaddleOCR Key | OCR text and layout extraction | https://aistudio.baidu.com/paddleocr |

### CLI (Advanced)

```bash
cd /path/to/your/vault
pip install git+https://github.com/LLLin000/PaperForge.git
python -m paperforge setup --headless --agent opencode --paddleocr-key <key>
```

## Usage

| Action | How |
|--------|-----|
| **Open Dashboard** | `Ctrl+P` → `PaperForge: Open Dashboard`, or click the sidebar icon |
| **Sync Literature** | Dashboard → `Sync Library` |
| **Run OCR** | Dashboard → `Run OCR` |
| **Deep Read** | `/pf-deep <zotero_key>` |
| **Quick Query** | `/pf-paper <zotero_key>` |

### Dashboard

<p align="center">
  <img src="docs/images/paperforge-dashboard.png" alt="PaperForge dashboard" width="78%" />
</p>

## Commands

### Obsidian Commands

| Command | Description |
|---------|-------------|
| `PaperForge: Open Dashboard` | Open the status panel and quick actions |
| `PaperForge: Sync Library` | Sync Zotero and generate notes |
| `PaperForge: Run OCR` | Extract full text and figures |

### Agent Commands

| Command | Description | Requires |
|---------|-------------|----------|
| `/pf-deep <key>` | Full 3-pass deep reading | OCR complete |
| `/pf-paper <key>` | Quick paper QA | Formal note exists |
| `/pf-sync` | Sync Zotero | Installed |
| `/pf-ocr` | Run OCR | Installed |
| `/pf-status` | System status | Installed |

### CLI Commands

| Command | Description |
|---------|-------------|
| `paperforge sync` | Sync Zotero and generate notes |
| `paperforge ocr` | Run OCR |
| `paperforge status` | Show system overview |
| `paperforge doctor` | Diagnose configuration |
| `paperforge update` | Update PaperForge |

## Supported Agent Platforms

| Platform | Agent Commands | Setup |
|----------|---------------|-------|
| **OpenCode** | Full `/pf-*` support | `.opencode/command/` + `.opencode/skills/` |
| **Claude Code** | `/pf-deep`, `/pf-paper` | `.claude/skills/` |
| **Cursor** | `/pf-deep`, `/pf-paper` | `.cursor/skills/` |
| **GitHub Copilot** | `/pf-deep`, `/pf-paper` | `.github/skills/` |
| **Windsurf** | `/pf-deep`, `/pf-paper` | `.windsurf/skills/` |
| **Codex** | `$pf-deep`, `$pf-paper` | `.codex/skills/` |
| **Cline** | `/pf-deep`, `/pf-paper` | `.clinerules/` |

## Docs

| Document | Content |
|----------|---------|
| [Setup Guide](docs/setup-guide.md) | Full setup walkthrough |
| [Quick Install](docs/INSTALLATION.md) | Short install path |
| [Post-Install Guide](AGENTS.md) | First-use workflow guide |
| [Changelog](CHANGELOG.md) | Version history |
| [Contributing](CONTRIBUTING.md) | Dev setup and conventions |

## License

[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Non-commercial use only.

## Acknowledgments

PaperForge builds on excellent open-source foundations:

| Project | Role |
|---------|------|
| [PaddleOCR / PaddleOCR-VL](https://github.com/PaddlePaddle/PaddleOCR) | PDF OCR, layout detection, and figure extraction |
| [Obsidian](https://obsidian.md) | Knowledge workspace and plugin host |
| [Better BibTeX for Zotero](https://retorque.re/zotero-better-bibtex/) | Metadata auto-export |
| [PyMuPDF (fitz)](https://github.com/pymupdf/PyMuPDF) | Local PDF validation and sanitization |
| [requests](https://github.com/psf/requests) | OCR API client |
| [tenacity](https://github.com/jd/tenacity) | Retry logic |
| [Pillow](https://python-pillow.org) | Figure image processing |
| [tqdm](https://github.com/tqdm/tqdm) | Progress bars |
| [textual](https://github.com/Textualize/textual) | TUI components |

> PaperForge aims to turn scattered papers, figures, and notes into research assets you can actually work with.
