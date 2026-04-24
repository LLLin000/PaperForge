#!/usr/bin/env python3
"""PaperForge Welcome Screen - ASCII-safe for Windows terminals."""

from __future__ import annotations

import time
import sys


class Colors:
    """ANSI color codes (safe for most terminals)."""
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ENDC = '\033[0m'


def clear_screen():
    """Clear terminal screen."""
    print("\033[2J\033[H", end="")


def draw_border(width: int = 80, char: str = "-", color: str = Colors.BRIGHT_BLUE):
    """Draw a simple horizontal border."""
    print(f"{color}{char * width}{Colors.ENDC}")


def show_welcome():
    """Display the PaperForge welcome screen."""
    clear_screen()

    # Top border
    draw_border(70, "=", Colors.BRIGHT_BLUE)

    # Title
    print(f"\n{Colors.BRIGHT_CYAN}{Colors.BOLD}  PAPERFORGE - Literature Workflow Installer{Colors.ENDC}")
    print(f"  {Colors.DIM}v1.0.0 | Forging Knowledge from Research Papers{Colors.ENDC}\n")

    # ASCII Logo - Horizontal line style (raw strings for safety)
    print(r"    ______  ___  ______ _________________ ___________ _____  _____ ")
    print(r"    | ___ \/ _ \ | ___ \  ___| ___ \  ___|  _  | ___ \  __ \|  ___|")
    print(r"    | |_/ / /_\ \| |_/ / |__ | |_/ / |_  | | | | |_/ / |  \/| |__  ")
    print(r"    |  __/|  _  ||  __/|  __||    /|  _| | | | |    /| | __ |  __| ")
    print(r"    | |   | | | || |   | |___| |\ \| |   \ \_/ / |\ \| |_\ \| |___ ")
    print(r"    \_|   \_| |_/\_|   \____/\_| \_\_|    \___/\_| \_|\____/\____/ ")
    print(r"                                                                   ")
    print(r"              [+]  Forge Your Knowledge Into Power  [+]             ")
    print()

    # Steps
    print(f"\n{Colors.BOLD}Installation Steps:{Colors.ENDC}")
    steps = [
        ("1", "Vault Configuration", "Set vault path and structure"),
        ("2", "Zotero Integration", "Connect reference manager"),
        ("3", "OCR Configuration", "Set up PaddleOCR API"),
        ("4", "Directory Setup", "Create vault folders"),
        ("5", "Script Deployment", "Install workflow scripts"),
        ("6", "Validation", "Verify installation"),
    ]
    for num, title, desc in steps:
        print(f"  {Colors.BRIGHT_CYAN}[{num}]{Colors.ENDC}  {Colors.BOLD}{title:<22}{Colors.ENDC}  {Colors.DIM}-> {desc}{Colors.ENDC}")

    # Bottom border
    draw_border(70, "=", Colors.BRIGHT_BLUE)
    print()


def show_progress(step: int, total: int, message: str):
    """Display progress bar."""
    width = 40
    filled = int(width * step / total)
    bar = "#" * filled + "-" * (width - filled)
    percent = int(100 * step / total)

    print(f"\r{Colors.BRIGHT_CYAN}[{bar}]{Colors.ENDC} {Colors.BOLD}{percent}%{Colors.ENDC} {Colors.DIM}{message}{Colors.ENDC}", end="")
    sys.stdout.flush()

    if step == total:
        print()  # New line when complete


def show_completion():
    """Display completion screen."""
    clear_screen()

    # Completion frame
    completion = f"""
{Colors.BRIGHT_GREEN}======================================================================{Colors.ENDC}
                                                                      
   {Colors.BOLD}{Colors.BRIGHT_WHITE}[OK]  INSTALLATION COMPLETE{Colors.ENDC}                                         
                                                                      
   {Colors.BRIGHT_YELLOW}Your knowledge forge is ready!{Colors.ENDC}                                 
                                                                      
{Colors.BRIGHT_GREEN}======================================================================{Colors.ENDC}
"""
    print(completion)

    print(f"\n{Colors.BOLD}Next Steps:{Colors.ENDC}")
    print(f"  {Colors.BRIGHT_CYAN}1.{Colors.ENDC} Open Obsidian and load your vault")
    print(f"  {Colors.BRIGHT_CYAN}2.{Colors.ENDC} Run: {Colors.BOLD}python scripts/index_refresh.py{Colors.ENDC}")
    print(f"  {Colors.BRIGHT_CYAN}3.{Colors.ENDC} Queue papers for OCR processing")
    print(f"  {Colors.BRIGHT_CYAN}4.{Colors.ENDC} Start deep reading: {Colors.BOLD}/pf-deep <zotero_key>{Colors.ENDC}")

    print(f"\n{Colors.DIM}For help: https://github.com/LLLin000/PaperForge{Colors.ENDC}\n")


def show_install_menu():
    """Show the interactive installation menu."""
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_WHITE}Please select an option:{Colors.ENDC}\n")
    print(f"  {Colors.BRIGHT_GREEN}[1]{Colors.ENDC}  {Colors.BOLD}Start Installation{Colors.ENDC}")
    print(f"      Configure vault, Zotero, OCR, and deploy scripts")
    print()
    print(f"  {Colors.BRIGHT_YELLOW}[2]{Colors.ENDC}  {Colors.BOLD}Verify Setup{Colors.ENDC}")
    print(f"      Check existing installation and fix issues")
    print()
    print(f"  {Colors.BRIGHT_BLUE}[3]{Colors.ENDC}  {Colors.BOLD}View Documentation{Colors.ENDC}")
    print(f"      Open README and usage guide")
    print()
    print(f"  {Colors.BRIGHT_RED}[4]{Colors.ENDC}  {Colors.BOLD}Exit{Colors.ENDC}")
    print()


def main():
    """Test the welcome screen."""
    show_welcome()
    input(f"{Colors.DIM}Press Enter to simulate installation...{Colors.ENDC}")

    # Simulate installation steps
    steps = [
        "Detecting vault path...",
        "Checking Python dependencies...",
        "Configuring Zotero...",
        "Setting up OCR...",
        "Creating directories...",
        "Deploying scripts...",
        "Validating setup...",
    ]

    for i, step in enumerate(steps, 1):
        show_progress(i, len(steps), step)
        time.sleep(0.5)

    show_completion()


if __name__ == "__main__":
    main()
