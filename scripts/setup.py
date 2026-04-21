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


# Agent platform configurations
AGENT_CONFIGS = {
    "opencode": {
        "name": "OpenCode",
        "skill_dir": ".opencode/skills",
        "config_file": None,
    },
    "claude": {
        "name": "Claude Code",
        "skill_dir": ".claude/skills",
        "config_file": ".claude/skills.json",
    },
    "cursor": {
        "name": "Cursor",
        "skill_dir": ".cursor/skills",
        "config_file": ".cursor/settings.json",
    },
    "windsurf": {
        "name": "Windsurf",
        "skill_dir": ".windsurf/skills",
        "config_file": None,
    },
    "github_copilot": {
        "name": "GitHub Copilot",
        "skill_dir": ".github/skills",
        "config_file": ".github/copilot-instructions.md",
    },
    "cline": {
        "name": "Cline",
        "skill_dir": ".clinerules/skills",
        "config_file": ".clinerules",
    },
    "augment": {
        "name": "Augment",
        "skill_dir": ".augment/skills",
        "config_file": None,
    },
    "trae": {
        "name": "Trae",
        "skill_dir": ".trae/skills",
        "config_file": None,
    },
}


def select_agent() -> tuple[str, dict]:
    """Ask user to select their AI agent platform."""
    print_header("Step 0: Agent Platform Selection")
    print("Which AI agent do you use with this vault?")
    print("(This determines where skill files and configurations are placed)\n")
    
    agents = list(AGENT_CONFIGS.items())
    for i, (key, cfg) in enumerate(agents, 1):
        print(f"  {i}. {cfg['name']} ({key})")
    print(f"  {len(agents) + 1}. Other (custom)")
    
    choice = ask("Select agent", default="1")
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(agents):
            return agents[idx]
        elif idx == len(agents):
            # Custom agent
            custom_name = ask("Enter agent name")
            custom_dir = ask("Enter skill directory (relative to vault)", default=".custom/skills")
            return "custom", {
                "name": custom_name,
                "skill_dir": custom_dir,
                "config_file": None,
            }
    except ValueError:
        pass
    
    # Default to OpenCode
    print_warning("Invalid choice, defaulting to OpenCode")
    return "opencode", AGENT_CONFIGS["opencode"]


def configure_vault_paths(vault_path: Path) -> dict:
    """Ask user for vault directory structure preferences."""
    print_header("Step 0.5: Vault Directory Configuration")
    print("Configure your vault folder structure (press Enter to accept defaults):\n")
    
    paths = {
        "system_dir": ask("System folder name", default="99_System"),
        "inbox_dir": ask("Inbox folder name", default="00_Inbox"),
        "resources_dir": ask("Resources folder name", default="03_Resources"),
        "literature_dir": ask("Literature subfolder", default="Literature"),
        "bases_dir": ask("Bases folder name", default="05_Bases"),
        "archives_dir": ask("Archives folder name", default="04_Archives"),
        "wiki_dir": ask("AI Wiki folder name", default="06_AI_Wiki"),
    }
    
    # Build derived paths
    paths["literature_path"] = f"{paths['resources_dir']}/{paths['literature_dir']}"
    paths["pipeline_path"] = f"{paths['system_dir']}/LiteraturePipeline"
    paths["template_path"] = f"{paths['system_dir']}/Template"
    
    return paths


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


def create_directory_structure(vault_path: Path, paths: dict) -> None:
    """Create required directory structure with configurable paths."""
    dirs = [
        f"{paths['pipeline_path']}/ocr",
        f"{paths['pipeline_path']}/worker/scripts",
        f"{paths['system_dir']}/Zotero",
        f"{paths['template_path']}",
        f"{paths['literature_path']}",
        f"{paths['inbox_dir']}",
        f"{paths['bases_dir']}",
        f"{paths['archives_dir']}",
        f"{paths['wiki_dir']}",
    ]
    
    for d in dirs:
        (vault_path / d).mkdir(parents=True, exist_ok=True)
    
    print_success(f"Directory structure created ({len(dirs)} folders)")


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


def create_agents_md(vault_path: Path, config: dict, paths: dict, agent_config: dict) -> None:
    """Create generic AGENTS.md template."""
    agents_path = vault_path / "AGENTS.md"
    
    if agents_path.exists():
        if not ask_yes_no("AGENTS.md already exists. Overwrite?", default=False):
            print_warning("Skipping AGENTS.md creation")
            return
    
    content = f"""# Agent Guide for Literature Research Vault

This repository is an Obsidian Vault dedicated to Literature Research.
It integrates closely with Zotero via automated pipeline tools.

## Agent Configuration

- **Platform**: {agent_config['name']}
- **Skill Directory**: `{agent_config['skill_dir']}`
- **Config File**: {agent_config.get('config_file', 'None')}

## Vault Structure

```
{paths['system_dir']}/
  LiteraturePipeline/       # Pipeline workers
    ocr/                    # OCR outputs
    worker/                 # Worker scripts
  Template/                 # Templates
    文献阅读.md
    科研读图指南.md
    读图指南/               # Chart reading guides
  Zotero/                   # Zotero data (junction)

{paths['inbox_dir']}/                     # Inbox for new papers
{paths['literature_path']}/     # Literature notes
{paths['bases_dir']}/                     # Obsidian Bases
{paths['archives_dir']}/                  # Archives
{paths['wiki_dir']}/                      # AI Wiki
```

## 1. Environment & Tech Stack

- **Platform**: Obsidian (Knowledge Management)
- **Reference Manager**: Zotero (via MCP & Direct SQLite Access)
- **Data Source**: PubMed (via MCP)
- **Primary Language**: Simplified Chinese (简体中文)
- **Scripting**: Python (Zotero interaction)

## 2. Workflows & Commands

### Literature Search
1.  **Analyze**: Use `parse_pico` to structure the research question.
2.  **Search**: Use `zotero-lit-review` (Local Library first) or `pubmed_search`
3.  **Verify**: Confirm what was found
4.  **Import**: Batch import from PubMed

### Deep Reading (/LD-deep)
1. Parse query (Zotero key / title / DOI / PMID)
2. Bind OCR fulltext and metadata
3. Generate `## 🔍 精读` scaffold
4. Fill with Keshav three-pass reading method
5. Validate output

## 3. Style Guidelines

### Markdown & Note Structure
Follow the template in `{paths['template_path']}/文献阅读.md`.

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
- Skill Dir: `{agent_config['skill_dir']}`

Generated by setup.py on {platform.system()}
"""
    
    agents_path.write_text(content, encoding="utf-8")
    print_success(f"AGENTS.md created at {agents_path}")
    
    agents_path.write_text(content, encoding="utf-8")
    print_success(f"AGENTS.md created at {agents_path}")


def deploy_workflow_scripts(vault_path: Path, agent_key: str, agent_config: dict, paths: dict) -> bool:
    """Deploy workflow scripts from repo to vault.
    
    This copies the core pipeline code from the repository into the user's vault,
    ensuring the latest scripts are available while keeping private data (.env, API keys) separate.
    """
    print_header("Step 4.5: Deploying Workflow Scripts")
    
    # Determine repo root (where this script is located)
    repo_root = Path(__file__).resolve().parent.parent
    
    # Get agent-specific skill directory
    skill_dir = agent_config.get("skill_dir", ".opencode/skills")
    
    # Files to deploy: (source_relative_path, dest_relative_path)
    deployments = [
        # OCR pipeline worker
        (f"99_System/LiteraturePipeline/worker/scripts/literature_pipeline.py",
         f"{paths['pipeline_path']}/worker/scripts/literature_pipeline.py"),
        
        # Deep reading scripts (into agent-specific skill dir)
        (f".opencode/skills/literature-qa/scripts/ld_deep.py",
         f"{skill_dir}/literature-qa/scripts/ld_deep.py"),
        
        # Subagent prompt (into agent-specific skill dir)
        (f".opencode/skills/literature-qa/prompt_deep_subagent.md",
         f"{skill_dir}/literature-qa/prompt_deep_subagent.md"),
    ]
    
    success_count = 0
    fail_count = 0
    
    for src_rel, dst_rel in deployments:
        src_path = repo_root / src_rel
        dst_path = vault_path / dst_rel
        
        if not src_path.exists():
            print_warning(f"Source file not found (skipping): {src_rel}")
            fail_count += 1
            continue
        
        try:
            # Ensure parent directory exists
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(src_path, dst_path)
            print_success(f"Deployed: {dst_rel}")
            success_count += 1
        except Exception as e:
            print_error(f"Failed to deploy {src_rel}: {e}")
            fail_count += 1
    
    # Deploy chart reading guides
    chart_guide_src = repo_root / "99_System/Template/读图指南"
    chart_guide_dst = vault_path / paths["template_path"] / "读图指南"
    
    if chart_guide_src.exists() and chart_guide_src.is_dir():
        chart_files = list(chart_guide_src.glob("*.md"))
        if chart_files:
            chart_guide_dst.mkdir(parents=True, exist_ok=True)
            for chart_file in chart_files:
                try:
                    dst_file = chart_guide_dst / chart_file.name
                    shutil.copy2(chart_file, dst_file)
                    success_count += 1
                except Exception as e:
                    print_error(f"Failed to deploy chart guide {chart_file.name}: {e}")
                    fail_count += 1
            print_success(f"Deployed {len(chart_files)} chart reading guides")
    
    print(f"\nDeployment summary: {success_count} succeeded, {fail_count} failed")
    return fail_count == 0


def validate_setup(vault_path: Path, config: dict, paths: dict) -> list[str]:
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
        f"{paths['pipeline_path']}/ocr",
        f"{paths['pipeline_path']}/worker/scripts",
        f"{paths['literature_path']}",
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
    # Show welcome screen
    try:
        from welcome import show_welcome, show_install_menu
        show_welcome()
        show_install_menu()
    except ImportError:
        print_header("Literature Workflow Installer")
    
    print("This script will help you configure the literature research pipeline.\n")
    
    # Step 0: Select agent platform
    agent_key, agent_config = select_agent()
    print_success(f"Selected agent: {agent_config['name']}")
    
    # Step 0.5: Configure vault paths
    print_header("Step 0.5: Vault Configuration")
    vault_path_str = ask(
        "Where is your Obsidian vault located?",
        default=str(Path.cwd()),
    )
    vault_path = Path(vault_path_str).resolve()
    
    if not vault_path.exists():
        print_error(f"Vault path does not exist: {vault_path}")
        return 1
    
    print_success(f"Using vault: {vault_path}")
    
    # Configure directory structure
    paths = configure_vault_paths(vault_path)
    print_success("Directory structure configured")
    
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
    create_directory_structure(vault_path, paths)
    
    # Step 6: Deploy workflow scripts
    deploy_workflow_scripts(vault_path, agent_key, agent_config, paths)
    
    # Step 7: Create junction or config
    print_header("Step 5: Configuring Zotero Integration")
    zotero_link = vault_path / paths["system_dir"] / "Zotero"
    
    if zotero_link.exists() or zotero_link.is_symlink():
        print_warning("Zotero link already exists")
    else:
        if create_junction(zotero_link, zotero_path):
            print_success("Zotero junction created")
        else:
            print_warning("Failed to create junction, will use config file instead")
    
    # Step 8: Save configuration
    print_header("Step 6: Saving Configuration")
    config = {
        "zotero_path": str(zotero_path),
        "storage_path": str(storage_path),
        "ocr_api_key": ocr_api_key,
        "agent": agent_key,
        "agent_name": agent_config["name"],
        "skill_dir": agent_config["skill_dir"],
    }
    create_env_file(vault_path, config)
    create_agents_md(vault_path, config, paths, agent_config)
    
    # Step 9: Validation
    print_header("Step 7: Validating Setup")
    issues = validate_setup(vault_path, config, paths)
    
    if issues:
        print_error("\nValidation failed with the following issues:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    
    print_header("Installation Complete!")
    print(f"""
{Colors.OKGREEN}Your literature workflow is ready to use!{Colors.ENDC}

Configuration Summary:
- Agent: {agent_config['name']}
- Skill Directory: {agent_config['skill_dir']}
- System Folder: {paths['system_dir']}
- Literature Path: {paths['literature_path']}

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
