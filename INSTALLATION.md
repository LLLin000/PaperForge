# PaperForge Installation Guide

> Canonical installation reference for **Obsidian Desktop (zero-Python Express Onboarding)** and **Standalone CLI / Headless environments**.

---

## Method 1: Obsidian Plugin + Zero-Python Express Onboarding (Recommended for Desktop Users)

1. Install and enable **PaperForge** from the Obsidian Community Plugin Browser (or via BRAT: `https://github.com/LLLin000/PaperForge`, or manual download from [GitHub Releases](https://github.com/LLLin000/PaperForge/releases/latest) into `<vault>/.obsidian/plugins/paperforge/`).
2. Open **Settings → PaperForge**.
3. Click **Enable Engine & Sync Library** in Express Onboarding:
   - The native `paperforge-daemon` binary is downloaded to `~/.paperforge/bin/` and verified by SHA-256.
   - Portable `uv` automatically provisions an isolated Python 3.12 runtime under `~/.paperforge/runtime/` (no system Python or manual `pip` required).
   - Zotero is connected directly via read-only `zotero.sqlite` snapshots (Better BibTeX JSON is optional).

---

## Method 2: Standalone / Headless CLI via `pip`

```bash
pip install paperforge
# Or include optional API vector-search dependencies (openai + sqlite-vec):
pip install "paperforge[vector]"
```

Initialize a vault (`paperforge.json` + `.paperforge/` hidden system layout):

```bash
paperforge setup --modular
```

Key CLI behaviors:
- Fresh vaults default to `.paperforge/` for internal engine artifacts (or keep existing `System` / custom directories unless migrated via `paperforge upgrade --apply --fast-cutover`);
- Credentials **never** go on the command line — store them securely in the OS Keyring via stdin/prompt:
  ```bash
  paperforge auth set ocr
  paperforge auth set embed
  ```
- Verify health and status:
  ```bash
  paperforge doctor --json
  paperforge status --json
  ```

Optional setup flags: `--headless`, `--system-dir`, `--resources-dir`, `--literature-dir`, `--base-dir`, `--zotero-data <path>`, `--agent <platform>`, `--skip-checks`.

---

## Method 3: AI Agent MCP & Skill Hub Integration

Connect Claude Code, Cursor, Codex, OpenCode, Windsurf, Copilot, or Cline via the native Rust MCP server (`paperforge-daemon --mcp`):

```bash
paperforge-daemon agent-onboarding --vault <VAULT_DIR> --lang en
paperforge-daemon mcp-install --vault <VAULT_DIR> --platform claude
paperforge-daemon mcp-check --vault <VAULT_DIR> --platform claude --probe-mcp
```

For manual agent-guided setup instructions, see:
- English: [docs/ai-agent-setup-guide.md](docs/ai-agent-setup-guide.md)
- 中文: [docs/ai-agent-setup-guide-zh.md](docs/ai-agent-setup-guide-zh.md)

---

## Prerequisites

| Software | Purpose | Notes |
| :--- | :--- | :--- |
| Obsidian Desktop (`>= 1.11.4`) | GUI workbench & built-in PDF Annotator | Optional for headless CLI / MCP usage |
| Zotero 7 / 8 | Literature library (`zotero.sqlite`) | Better BibTeX is optional (SQLite direct is default) |
| Python 3.11+ | Only needed for standalone `pip install` | Not required for Obsidian Express Onboarding (`uv` manages Python 3.12 automatically) |
| PaddleOCR Key (optional) | Cloud layout OCR & figure extraction | Stored in OS Keyring via `paperforge auth set ocr` |

---

## Post-Installation

See [docs/COMMANDS.md](docs/COMMANDS.md) for the full Python CLI + Rust daemon + MCP tool reference, and [AGENTS.md](AGENTS.md) for agent workflow rules.
