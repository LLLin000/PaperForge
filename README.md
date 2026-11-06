<p align="center">
  <img src="docs/images/paperforge-banner.png" alt="PaperForge banner" width="100%" />
</p>

# PaperForge

[![Version](https://img.shields.io/github/v/release/LLLin000/PaperForge?style=for-the-badge&label=version)](https://github.com/LLLin000/PaperForge/releases)
[![Python](https://img.shields.io/pypi/pyversions/paperforge?style=for-the-badge&logo=python&logoColor=white&color=3775A9)](https://python.org)
[![License](https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgreen?style=for-the-badge)](LICENSE)

[简体中文](README.zh.md) · **English**

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

### Option A: Community Plugin Browser (Recommended)

1. Open Obsidian → `Settings` → `Community plugins` → `Browse`
2. Search for **PaperForge**
3. Click `Install`, then `Enable`

> Community plugins auto-update through Obsidian. No extra steps needed.

### Option B: BRAT

If you need beta versions or the plugin hasn't appeared in search yet:

1. Install **BRAT** from the Obsidian community plugin browser
2. Open BRAT settings → `Add Beta Plugin`
3. Enter: `https://github.com/LLLin000/PaperForge`
4. Enable PaperForge in Settings → Community Plugins

### Option C: Manual Download

1. Go to [Releases](https://github.com/LLLin000/PaperForge/releases)
2. Download the three files: `main.js`, `manifest.json`, `styles.css`
3. Create `.obsidian/plugins/paperforge/` in your vault
4. Put the three files there
5. Restart Obsidian → Settings → Community Plugins → enable PaperForge

> Manual install does not auto-update. You'll need to re-download for each new version.

---

## 2. Install PaperForge Core (outside Obsidian)

The Obsidian plugin does not install Python or manage packages. Install the
matching bootstrap CLI from a terminal, then use it to create and verify the
managed Core runtime:

```bash
python -m pip install --user --upgrade "paperforge==<PLUGIN_VERSION>"
python -m paperforge runtime install --expected-version <PLUGIN_VERSION>
```

Replace `<PLUGIN_VERSION>` with the version in the installed plugin's
`manifest.json`. Use the same Python 3.11+ executable for both commands
(`py -3.11 -m ...` on Windows or `python3.11 -m ...` on macOS/Linux).
The installer creates a separate runtime under `~/.paperforge/runtime/` and
publishes its pointer only after verification.

Then open PaperForge in Obsidian. The plugin reads the runtime pointer and
configures the current Vault; it never runs `pip` or creates the Python
environment. One installed Core can serve multiple Vaults.

If the plugin version changes, install the matching bootstrap CLI and update
the managed runtime from a terminal:

```bash
python -m pip install --user --upgrade "paperforge==<NEW_PLUGIN_VERSION>"
python -m paperforge runtime update --expected-version <NEW_PLUGIN_VERSION>
```

For a broken runtime, run this from the same terminal:

```bash
python -m paperforge runtime repair --expected-version <PLUGIN_VERSION>
```

Do not run these lifecycle commands from an Obsidian plugin action.

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

## 文档导航

| 你想做什么                                 | 去看                           |
| ------------------------------------------ | ------------------------------ |
| 完整教程，从安装到精读                     | [使用教程](docs/getting-started.md)    |
| 遇到问题了                                 | [故障排除](docs/troubleshooting.md)    |
| 查某个命令                                 | [命令参考](docs/COMMANDS.md)           |
| 如何升级                                   | [更新指南](docs/update-upgrade.md)     |
| 架构 / 维护 / 发布                         | [架构文档](docs/ARCHITECTURE.md)       |
| AI Agent 协作                               | [AGENTS.md](AGENTS.md)                |

---

## License

[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Non-commercial use only.

## Acknowledgments

Built on [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR), [Obsidian](https://obsidian.md), [Better BibTeX for Zotero](https://retorque.re/zotero-better-bibtex/), and other great open-source projects.
