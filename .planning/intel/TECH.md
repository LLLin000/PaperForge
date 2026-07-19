# Technology Stack

**Analysis Date:** 2026-05-16

## Languages

**Primary:**
- **Python 3.10+** — CLI backend for all data-heavy operations: sync, OCR, memory build, embed build, repair, status, runtime health, agent context. 71 Python modules totaling ~16,700 lines (excluding node_modules, test fixture files).
  - Entry point: `paperforge/__main__.py` -> `paperforge/cli.py` (572 lines)
  - Version defined in single source: `paperforge/__init__.py` (__version__ = "1.5.6rc3")

**Secondary:**
- **JavaScript (Node.js / Obsidian API)** — Obsidian plugin for UI, state display, subprocess orchestration. 2 source files + 4 test files.
  - `paperforge/plugin/main.js` — 4,914 lines (monolithic, single file)
  - `paperforge/plugin/src/testable.js` — 224 lines (extracted pure functions)
  - `paperforge/plugin/tests/*.test.mjs` — 4 test files, 310 lines total

## Runtimes

**Python Runtime:**
- CPython 3.10+
- Package manager: pip
- Package: `paperforge` (installed via pip or git+https://github.com/LLLin000/PaperForge.git)
- Lockfile: Not detected (pip-only, no requirements.lock)

**JS Runtime:**
- Node.js (embedded in Obsidian/Electron)
- Package manager: npm (dev-only, vitest)
- Package config: Not standalone (Obsidian plugin manifest at `paperforge/plugin/manifest.json`)
- Obsidian API version: minAppVersion 1.9.0

## Frameworks

**Core Python Libraries:**
| Library | Version | Purpose |
|---------|---------|---------|
| requests | >=2.31.0 | HTTP calls (PaddleOCR API) |
| pymupdf | >=1.23.0 | PDF parsing |
| Pillow | >=10.0.0 | Image processing |
| tenacity | >=8.2.0 | Retry logic for OCR and subprocess calls |
| tqdm | >=4.66.0 | Progress bars in CLI |
| filelock | >=3.13.0 | Cross-process file locking |
| PyYAML | >=6.0 | YAML field registry parsing |
| chromadb | >=0.5.0 (optional) | Vector database persistence |
| sentence-transformers | >=3.0.0 (optional) | Local embedding models |
| openai | >=1.0.0 (optional) | API-mode embeddings |

**JS Dependencies (Obsidian Plugin):**
- `obsidian` (built-in Electron API) — Plugin, Notice, ItemView, Modal, Setting, PluginSettingTab, addIcon
- `node:child_process` — exec, execFile, spawn, execFileSync
- `fs`, `path`, `os` (Node.js built-in)
- **No JS package.json detected for plugin build process** — plugin ships as raw JS

**Testing:**
| Tool | Purpose |
|------|---------|
| pytest (Python) | Test runner — 173 tests across 6 test levels |
| pytest-snapshot | Snapshot regression testing for JSON contracts |
| pytest-timeout | Timeout handling for tests |
| responses | HTTP mock library |
| pytest-mock | Mock support |
| coverage | Code coverage measurement |
| ruff | Linting + formatting (py310 target, 120 char width) |
| vitest (JS) | JS test runner — 4 test files for testable.js |

**Agent System:**
- OpenCode / Claude Code / Cursor / Windsurf / GitHub Copilot — multiple agent platforms supported
- Compound skill model: SKILL.md (compound) -> workflows/ (molecules) -> scripts/ (atoms)
- Skill files deployed by `paperforge/services/skill_deploy.py`

## Configuration

**Environment:**
- `.env` at vault root — contains PADDLEOCR_API_TOKEN, OPENAI_API_KEY (never read contents, only existence checked)
- Plugin settings in `.obsidian/plugins/paperforge/data.json`
- Central config at vault root `paperforge.json` — vault_config block with path overrides, schema_version
- Python `paperforge/config.py` (346 lines) — DEFAULT_CONFIG, paperforge_paths(), load_vault_config(), read_paperforge_json(), CONFIG_PATH_KEYS

**Build Config Files:**
- `pyproject.toml` — setuptools build, ruff config, pytest config, optional-dependencies
- `ruff.toml` (none — embedded in pyproject.toml)
- `.pre-commit-config.yaml` — ruff check + format (in git repo root)
- `manifest.json` (plugin) — id, name, version, minAppVersion

## Version Management

- Single source of truth: `paperforge/__init__.py` (__version__)
- `scripts/bump.py` automates version bump across: `__init__.py`, `paperforge/plugin/manifest.json`, root `manifest.json`, `paperforge/plugin/versions.json`
- Release process: bump -> git push --tags -> gh release create with 4 plugin files

---

*Stack analysis: 2026-05-16*
