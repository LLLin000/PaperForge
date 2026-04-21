#!/usr/bin/env python3
"""Interactive installer for the Literature Workflow."""

from __future__ import annotations

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path
from typing import Optional


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str) -> None:
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")


def print_success(text: str) -> None:
    print(f"{Colors.OKGREEN}[OK]{Colors.ENDC} {text}")


def print_warning(text: str) -> None:
    print(f"{Colors.WARNING}[WARN]{Colors.ENDC} {text}")


def print_error(text: str) -> None:
    print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} {text}")


def ask(question: str, default: Optional[str] = None) -> str:
    """Ask user a question with optional default."""
    if default:
        prompt = f"{question} [{default}]: "
    else:
        prompt = f"{question}: "
    
    answer = input(prompt).strip()
    if not answer and default:
        return default
    return answer


def ask_yes_no(question: str, default: bool = False) -> bool:
    """Ask a yes/no question."""
    suffix = " [Y/n]: " if default else " [y/N]: "
    answer = input(f"{question}{suffix}").strip().lower()
    if not answer:
        return default
    return answer in ('y', 'yes', 'true', '1')


def detect_zotero_path() -> Optional[Path]:
    """Auto-detect Zotero data directory."""
    system = platform.system()
    
    if system == "Windows":
        # Check common locations
        home = Path.home()
        candidates = [
            home / "Zotero",
            home / "AppData" / "Roaming" / "Zotero" / "Zotero",
            Path("C:/Users") / os.environ.get("USERNAME", "") / "Zotero",
        ]
    elif system == "Darwin":  # macOS
        home = Path.home()
        candidates = [
            home / "Zotero",
            home / "Library" / "Application Support" / "Zotero",
        ]
    else:  # Linux
        home = Path.home()
        candidates = [
            home / "Zotero",
            home / ".zotero",
        ]
    
    for candidate in candidates:
        if candidate.exists() and (candidate / "zotero.sqlite").exists():
            return candidate
    
    return None


def create_junction(source: Path, target: Path) -> bool:
    """Create junction/symlink from source to target."""
    system = platform.system()
    
    try:
        if system == "Windows":
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(source), str(target)],
                check=True,
                capture_output=True,
                shell=False,
            )
        else:
            source.symlink_to(target, target_is_directory=True)
        return True
    except (subprocess.CalledProcessError, OSError) as e:
        print_error(f"Failed to create junction: {e}")
        return False


def check_python_deps() -> list[str]:
    """Check if required Python packages are installed."""
    required = ["requests", "pymupdf", "PIL", "pytest"]
    missing = []
    
    for package in required:
        try:
            __import__(package.lower().replace("pil", "PIL"))
        except ImportError:
            missing.append(package)
    
    return missing


def install_deps(deps: list[str]) -> bool:
    """Install missing Python dependencies."""
    if not deps:
        return True
    
    print(f"Installing dependencies: {', '.join(deps)}")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install"] + deps,
            check=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install dependencies: {e}")
        return False


def create_directory_structure(vault_path: Path) -> None:
    """Create required directory structure."""
    dirs = [
        "99_System/LiteraturePipeline/ocr",
        "99_System/LiteraturePipeline/worker/scripts",
        "99_System/Zotero",
        "99_System/Template",
        "03_Resources/Literature",
        "00_Inbox",
    ]
    
    for d in dirs:
        (vault_path / d).mkdir(parents=True, exist_ok=True)
    
    print_success("Directory structure created")


def create_env_file(vault_path: Path, config: dict) -> None:
    """Create .env configuration file."""
    env_path = vault_path / ".env"
    
    lines = [
        "# Literature Workflow Configuration",
        f"ZOTERO_DATA_DIR={config['zotero_path']}",
        f"ZOTERO_STORAGE_DIR={config.get('storage_path', config['zotero_path'])}",
        f"PADDLEOCR_API_KEY={config['ocr_api_key']}",
        "PADDLEOCR_API_URL=https://paddleocr.baidu.com/api/v1/ocr",
        "",
        "# Optional: Custom paths",
        f"VAULT_PATH={vault_path}",
    ]
    
    env_path.write_text("\n".join(lines), encoding="utf-8")
    print_success(f"Configuration saved to {env_path}")


def create_agents_md(vault_path: Path, config: dict) -> None:
    """Create generic AGENTS.md template."""
    agents_path = vault_path / "AGENTS.md"
    
    if agents_path.exists():
        if not ask_yes_no("AGENTS.md already exists. Overwrite?", default=False):
            print_warning("Skipping AGENTS.md creation")
            return
    
    content = f"""# Agent Guide for Literature Research Vault

This repository is an Obsidian Vault dedicated to Literature Research.
It integrates closely with Zotero via automated pipeline tools.

## 0. AGENT PROTOCOL (MANDATORY)

### Skill Audit
**Before executing ANY task, perform this audit:**

1. **CLASSIFY**: What is the domain? (Literature, Clinical, Bioinformatics)
2. **SCAN**: Look at the available skills
3. **SELECT**: Pick the best tool for the job
4. **LOAD**: Execute `skill({{ name: "selected-skill" }})`

### Environment

- **Platform**: Obsidian (Knowledge Management)
- **Reference Manager**: Zotero
- **Data Source**: PubMed
- **Primary Language**: Simplified Chinese (简体中文)
- **Scripting**: Python, Markdown

## 1. Workflows

### Literature Search Loop
1. **Analyze**: Use `parse_pico` to structure the research question
2. **Search**: Use `zotero-lit-review` (Local Library first) or `pubmed_search`
3. **Verify**: Confirm what was found
4. **Import**: Batch import from PubMed

### Deep Reading (/LD-deep)
1. Parse query (Zotero key / title / DOI / PMID)
2. Bind OCR fulltext and metadata
3. Generate `## 🔍 精读` scaffold
4. Fill with Keshav three-pass reading method
5. Validate output

## 2. Style Guidelines

### Markdown & Note Structure
Follow the template in `99_System/Template/文献阅读.md`.

**Frontmatter (YAML) is MANDATORY:**
```yaml
---
title: " {{{{Title}}}} "
year: {{{{Year}}}}
type: {{{{Type}}}}
journal: " {{{{Journal}}}} "
category: {{{{Category}}}}
tags:
  - 文献阅读
  - {{{{Subject_Tag}}}}
---
```

### Output Language
- **Output**: Simplified Chinese (简体中文) ONLY, unless asked otherwise.
- **Search Terms**: English (for PubMed), but explain in Chinese.

## 3. Directory Structure

```
{{vault_path}}/
├── 00_Inbox/                    # Inbox for new papers
├── 01_Projects/                 # Project-specific notes
├── 02_Areas/                    # Area notes
├── 03_Resources/                # Resources
│   └── Literature/              # Literature notes
│       ├── 骨科/                # Orthopedics
│       ├── 运动医学/            # Sports Medicine
│       └── ...
├── 04_Archives/                 # Archives
├── 05_Bases/                    # Obsidian Bases
├── 06_AI_Wiki/                  # AI Wiki
├── 99_System/                   # System files
│   ├── LiteraturePipeline/      # Pipeline workers
│   │   ├── ocr/                 # OCR outputs
│   │   └── worker/              # Worker scripts
│   ├── Template/                # Templates
│   │   ├── 文献阅读.md
│   │   ├── 科研读图指南.md
│   │   └── 读图指南/            # Chart reading guides
│   └── Zotero/                  # Zotero data (junction)
└── AGENTS.md                    # This file
```

## 4. Interaction Rules

### Protocol
1. **No Hallucinations**: Never invent PMIDs or citations.
2. **User Confirmation**:
   - Confirm **Search Strategy** before executing deep searches.
   - Confirm **Target Collection** before importing to Zotero.
3. **Session Awareness**: Track context across sessions.

## 5. Commands

- `/LD <query>` - Quick literature lookup
- `/LD-deep <query>` - Deep reading (Keshav three-pass)
- `/LD-deep queue` - Process queued papers

## 6. Configuration

- Zotero Data: `{zotero_path}`
- Zotero Storage: `{storage_path}`
- Vault Path: `{vault_path}`
- OCR API: PaddleOCR

Generated by setup.py on {platform.system()}
"""
    
    agents_path.write_text(content, encoding="utf-8")
    print_success(f"AGENTS.md created at {agents_path}")


def validate_setup(vault_path: Path, config: dict) -> list[str]:
    """Validate the setup and return issues."""
    issues = []
    
    # Check Zotero SQLite
    zotero_db = Path(config['zotero_path']) / "zotero.sqlite"
    if not zotero_db.exists():
        issues.append(f"Zotero database not found: {zotero_db}")
    else:
        print_success("Zotero database accessible")
    
    # Check directory structure
    required_dirs = [
        "99_System/LiteraturePipeline/ocr",
        "99_System/LiteraturePipeline/worker/scripts",
        "03_Resources/Literature",
    ]
    for d in required_dirs:
        if not (vault_path / d).exists():
            issues.append(f"Missing directory: {d}")
    
    if not issues:
        print_success("Directory structure correct")
    
    # Check AGENTS.md
    if not (vault_path / "AGENTS.md").exists():
        issues.append("AGENTS.md missing")
    else:
        print_success("AGENTS.md exists")
    
    # Check .env
    if not (vault_path / ".env").exists():
        issues.append(".env configuration missing")
    else:
        print_success("Configuration file exists")
    
    return issues


def main() -> int:
    """Main installer entry point."""
    print_header("Literature Workflow Installer")
    print("This script will help you configure the literature research pipeline.\n")
    
    # Step 0: Detect vault path
    vault_path_str = ask(
        "Where is your Obsidian vault located?",
        default=str(Path.cwd()),
    )
    vault_path = Path(vault_path_str).resolve()
    
    if not vault_path.exists():
        print_error(f"Vault path does not exist: {vault_path}")
        return 1
    
    print_success(f"Using vault: {vault_path}")
    
    # Step 1: Check Python deps
    print_header("Step 1: Checking Python Dependencies")
    missing_deps = check_python_deps()
    if missing_deps:
        print_warning(f"Missing packages: {', '.join(missing_deps)}")
        if ask_yes_no("Install now?", default=True):
            if not install_deps(missing_deps):
                return 1
        else:
            print_error("Required packages must be installed to continue")
            return 1
    else:
        print_success("All dependencies installed")
    
    # Step 2: Detect/Ask for Zotero path
    print_header("Step 2: Zotero Configuration")
    detected_zotero = detect_zotero_path()
    
    if detected_zotero:
        print_success(f"Detected Zotero at: {detected_zotero}")
        if ask_yes_no("Use this path?", default=True):
            zotero_path = detected_zotero
        else:
            zotero_path = Path(ask("Enter Zotero data directory:"))
    else:
        print_warning("Could not auto-detect Zotero")
        zotero_path = Path(ask("Enter Zotero data directory (contains zotero.sqlite):"))
    
    if not (zotero_path / "zotero.sqlite").exists():
        print_error(f"zotero.sqlite not found in {zotero_path}")
        print("Please ensure Zotero is installed and the path is correct.")
        return 1
    
    # Step 3: Storage path
    storage_path = zotero_path
    if ask_yes_no("Is your Zotero storage directory in a different location?", default=False):
        storage_path = Path(ask("Enter Zotero storage directory:"))
    
    # Step 4: OCR API Key
    print_header("Step 3: OCR Configuration")
    ocr_api_key = ask("Enter your PaddleOCR API key:")
    if not ocr_api_key:
        print_warning("No API key provided. OCR features will not work.")
    
    # Step 5: Create directories
    print_header("Step 4: Creating Directory Structure")
    create_directory_structure(vault_path)
    
    # Step 6: Create junction or config
    print_header("Step 5: Configuring Zotero Integration")
    zotero_link = vault_path / "99_System" / "Zotero"
    
    if zotero_link.exists() or zotero_link.is_symlink():
        print_warning("Zotero link already exists")
    else:
        if create_junction(zotero_link, zotero_path):
            print_success("Zotero junction created")
        else:
            print_warning("Failed to create junction, will use config file instead")
    
    # Step 7: Save configuration
    print_header("Step 6: Saving Configuration")
    config = {
        "zotero_path": str(zotero_path),
        "storage_path": str(storage_path),
        "ocr_api_key": ocr_api_key,
    }
    create_env_file(vault_path, config)
    create_agents_md(vault_path, config)
    
    # Step 8: Validation
    print_header("Step 7: Validating Setup")
    issues = validate_setup(vault_path, config)
    
    if issues:
        print_error("\nValidation failed with the following issues:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    
    print_header("Installation Complete!")
    print(f"""
{Colors.OKGREEN}Your literature workflow is ready to use!{Colors.ENDC}

Next steps:
1. Open Obsidian and ensure your vault is loaded
2. Index your library: Run the index-refresh worker
3. Queue papers for analysis in the Base system
4. Run OCR on queued papers
5. Start deep reading with /LD-deep <zotero_key>

For detailed usage, see the documentation in docs/.
""")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
