<p align="center">
  <img src="docs/images/paperforge-banner.png" alt="PaperForge banner" width="100%" />
</p>

# PaperForge

[![Version](https://img.shields.io/github/v/release/LLLin000/PaperForge?style=for-the-badge&label=version)](https://github.com/LLLin000/PaperForge/releases)
[![Python](https://img.shields.io/pypi/pyversions/paperforge?style=for-the-badge&logo=python&logoColor=white&color=3775A9)](https://python.org)
[![License](https://img.shields.io/badge/license-CC--BY--NC--SA--4.0-lightgreen?style=for-the-badge)](LICENSE)

[简体中文](README.zh.md) · **English**

> **铸知识为器，启洞见之明。 — Forge Knowledge, Empower Insight.**

PaperForge brings your Zotero library into Obsidian. Sync papers directly from `zotero.sqlite` (no Better BibTeX required), annotate PDFs non-destructively, run V3 OCR with figure extraction, search with SQLite FTS5 + `sqlite-vec`, and collaborate with AI Agents via native MCP — all inside a single vault.

---

## 0. How PaperForge Works (v2.0.x Architecture)

PaperForge uses a **three-part decoupled desktop architecture** with zero Python prerequisites for Obsidian users:

| Component | What | Role | Location |
| :--- | :--- | :--- | :--- |
| **Obsidian Plugin** | `main.js` + `manifest.json` + `styles.css` | Thin-Client UI: single `.base` workbench, PDF Annotator, Companion, 4-tab Settings | `<vault>/.obsidian/plugins/paperforge/` |
| **Native Rust Daemon** | `paperforge-daemon` (6-platform native binary) | Zero-Python fast-path (`base-snapshot`, `search`, `config`), `--mcp` server (7 tools), `install-runtime` bootstrapper | `~/.paperforge/bin/` |
| **Managed Python Core** | `paperforge` (auto-installed via portable `uv` + Python 3.12) | Zotero SQLite sync, V3 OCR & figure extraction, SQLite FTS5 + `sqlite-vec` hybrid retrieval, Living Memory Cards | `~/.paperforge/runtime/` |

---

## 1. Install the Obsidian Plugin

1. **Community Plugin Browser** (or **BRAT** with `https://github.com/LLLin000/PaperForge`, or manual download from [GitHub Releases](https://github.com/LLLin000/PaperForge/releases)): install and enable **PaperForge**.
2. Open **Settings → PaperForge** and click **Enable Engine & Sync Library** in Express Onboarding.
3. PaperForge automatically provisions `paperforge-daemon` + isolated `uv` Python 3.12 runtime under `~/.paperforge/`, connects to `zotero.sqlite` read-only, and builds your single `.base` library workbench.

---

## 2. Standalone CLI & AI Agent MCP Quickstart

```bash
pip install "paperforge[vector]"
paperforge setup --modular
paperforge auth set ocr
paperforge sync
paperforge ocr
paperforge status --json
```

Connect AI Agents (Claude Code, Cursor, Codex, OpenCode, etc.) via native MCP:

```bash
paperforge-daemon mcp-install --vault <VAULT_DIR> --platform claude
paperforge-daemon mcp-check --vault <VAULT_DIR> --platform claude --probe-mcp
```

Use `/pf-deep <zotero_key>` for 3-pass deep reading or `/pf-paper <zotero_key>` for interactive Q&A inside your Agent chat.

---

## Documentation

| If you want to | Read |
| :--- | :--- |
| Full tutorial (CN) | [Getting Started](docs/getting-started.md) |
| Full user manual (CN) | [User Manual](docs/user-manual.md) |
| CLI, Rust Daemon & MCP reference | [Commands](docs/COMMANDS.md) |
| Installation guide | [INSTALLATION.md](INSTALLATION.md) |
| Troubleshooting | [Troubleshooting](docs/troubleshooting.md) |
| Architecture & updates | [Install & Update Architecture](docs/INSTALL-AND-UPDATE-ARCHITECTURE.md) |
| AI Agent collaboration | [AGENTS.md](AGENTS.md) |

---

## License

[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Non-commercial use only.

## Acknowledgments

Built on [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR), [Obsidian](https://obsidian.md), [Zotero](https://www.zotero.org/), and [sqlite-vec](https://github.com/asg017/sqlite-vec).
