# PyPI Publish — Design

## Scope
Publish `paperforge` to PyPI, update install URLs to PyPI-first with git fallback, add CI auto-publish.

## Changes

### 1. Plugin install URL (main.js + testable.js)
- `buildRuntimeInstallCommand`: try `pip install paperforge==ver`, fallback to `git+https://...@v{ver}`
- Setup wizard `pipArgs`: same pattern
- Auto-update `url`: same pattern

### 2. Python install URL (runtime.py, setup_wizard.py, update.py)
- `RuntimeInstaller`: try PyPI, fallback git
- `setup_wizard.py`: same
- `update.py` `GITHUB_PIP_SOURCE`: keep git for now (update uses zip fallback already)

### 3. CI workflow (`.github/workflows/publish.yml`)
- Trigger: tag push matching `v*`
- Steps: checkout → python setup → build → twine upload
- Needs: `PYPI_TOKEN` secret

### 4. Not changed
- `pyproject.toml` — already fully configured, no changes needed
- `paperforge update --latest` — already has zip fallback, git URL works fine
