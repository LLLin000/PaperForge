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

All hidden indexes, OCR intermediates, and `paperforge.db` live inside `<vault>/.paperforge/`, keeping Obsidian's file indexer fast and uncluttered.

---

## 1. Install the Obsidian Plugin

### Option A: Community Plugin Browser (Recommended)

1. Open Obsidian → **Settings** → **Community plugins** → **Browse**
2. Search for **PaperForge**
3. Click **Install**, then **Enable**

### Option B: BRAT (Pre-releases & Early Builds)

1. Install **BRAT** from Obsidian Community Plugins
2. Open BRAT settings → **Add Beta Plugin**
3. Enter `https://github.com/LLLin000/PaperForge`
4. Enable **PaperForge** in Community Plugins

### Option C: Manual Download

1. Download `main.js`, `manifest.json`, and `styles.css` from [GitHub Releases](https://github.com/LLLin000/PaperForge/releases)
2. Place them in `<vault>/.obsidian/plugins/paperforge/`
3. Restart Obsidian and enable **PaperForge**

---

## 2. Express Onboarding (Zero Terminal Setup)

Once the plugin is enabled, open **Settings → PaperForge**:

1. **One-Screen Express Setup**: Click **Enable Engine & Sync Library**. The native `paperforge-daemon` automatically downloads portable `uv`, provisions an isolated Python 3.12 runtime in `~/.paperforge/runtime/`, and verifies integrity via SHA-256 — no system Python or manual `pip` required.
2. **Direct Zotero Connection**: PaperForge reads `zotero.sqlite` directly via read-only SQLite Online Backup snapshots (Better BibTeX JSON remains supported as an optional mode). Choose between **per-collection subfolders** or a **flat library** with live preview.
3. **4-Tab Control Center & 10-State Decision Tree**: Settings are organized into **Overview**, **Modules**, **Appearance**, and **Help**, backed by a deterministic 10-state decision tree and `<3s` lossless upgrade for legacy `System/PaperForge/` vaults.
4. **Optional AI & Vector Search**: Configure PaddleOCR keys (stored securely in the OS Keyring, never plaintext `.env`) and OpenAI-compatible embedding providers (`sqlite-vec` `vec0` — no ChromaDB required) whenever you are ready.

---

## 3. Standalone / Headless CLI & AI Agent MCP Setup

For terminal workflows, CI automation, or headless servers:

```bash
pip install "paperforge[vector]"
paperforge setup --modular
paperforge auth set ocr          # prompts securely for PaddleOCR token (writes to OS Keyring)
paperforge sync
paperforge ocr
paperforge status --json
```

To connect AI Agents (Claude Code, Cursor, Codex, OpenCode, Windsurf, Copilot, Cline) via native MCP + Skill Hub:

```bash
paperforge-daemon mcp-install --vault <VAULT_DIR> --platform claude
paperforge-daemon mcp-check --vault <VAULT_DIR> --platform claude --probe-mcp
paperforge-daemon skill-sync-all
```

In your AI Agent chat, trigger `/pf-deep <zotero_key>` for Keshav 3-pass deep reading or `/pf-paper <zotero_key>` for interactive Q&A.

---

## Documentation

| If you want to | Read |
| :--- | :--- |
| Quickstart tutorial (CN) | [Getting Started](docs/getting-started.md) |
| Full user manual (CN) | [User Manual](docs/user-manual.md) |
| CLI, Rust Daemon & MCP command reference | [Commands](docs/COMMANDS.md) |
| Standalone / headless installation details | [Installation Guide](INSTALLATION.md) |
| Troubleshooting | [Troubleshooting](docs/troubleshooting.md) |
| Update & architecture blueprint | [Install & Update Architecture](docs/INSTALL-AND-UPDATE-ARCHITECTURE.md) |
| AI Agent collaboration rules | [AGENTS.md](AGENTS.md) |

---

## License

[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Non-commercial use only.

## Acknowledgments

Built on [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR), [Obsidian](https://obsidian.md), [Zotero](https://www.zotero.org/), and [sqlite-vec](https://github.com/asg017/sqlite-vec).
