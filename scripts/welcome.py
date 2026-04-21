#!/usr/bin/env python3
"""
PaperForge - Literature Research Workflow
Installation Welcome Screen

     ╔════════════════════════════════════════════════════════════════╗
     ║                                                                ║
     ║          ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░            ║
     ║          ░░                                  ░░            ║
     ║          ░░   ▓▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓▓   ░░            ║
     ║          ░░   ▓   ▓  ▓   ▓  ▓      ▓      ▓       ░░            ║
     ║          ░░   ▓▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓   ▓▓▓▓   ▓▓▓▓    ░░            ║
     ║          ░░   ▓      ▓   ▓  ▓      ▓      ▓       ░░            ║
     ║          ░░   ▓      ▓   ▓  ▓▓▓▓▓  ▓▓▓▓▓  ▓       ░░            ║
     ║          ░░                                  ░░            ║
     ║          ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░            ║
     ║                                                                ║
     ║              ⚡  Forge Your Knowledge Into Power  ⚡              ║
     ║                                                                ║
     ╚════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import time


# ANSI color codes
class Colors:
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
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    STRIKETHROUGH = '\033[9m'
    END = '\033[0m'


def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_slow(text, delay=0.01):
    """Print text with a typing effect."""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()


def draw_logo():
    """Draw the PaperForge ASCII logo."""
    logo = f"""
{Colors.BRIGHT_YELLOW}           ▄███████████▄                               {Colors.END}
{Colors.BRIGHT_YELLOW}        ▄██▀{Colors.BOLD}   ▀███▀   {Colors.END}{Colors.BRIGHT_YELLOW}▀██▄                            {Colors.END}
{Colors.BRIGHT_YELLOW}       █▀{Colors.END}       ███       {Colors.BRIGHT_YELLOW}▀█                           {Colors.END}
{Colors.BRIGHT_YELLOW}      █{Colors.END}   ███   ███   ███   {Colors.BRIGHT_YELLOW}█{Colors.END}    {Colors.BRIGHT_RED}{Colors.BOLD}▓▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓▓{Colors.END}      
{Colors.BRIGHT_YELLOW}      █{Colors.END}   ███   ███   ███   {Colors.BRIGHT_YELLOW}█{Colors.END}    {Colors.BRIGHT_RED}{Colors.BOLD}▓      ▓   ▓  ▓{Colors.END}          
{Colors.BRIGHT_YELLOW}      █{Colors.END}   ███   ███   ███   {Colors.BRIGHT_YELLOW}█{Colors.END}    {Colors.BRIGHT_RED}{Colors.BOLD}▓▓▓▓   ▓▓▓▓▓  ▓▓▓▓{Colors.END}       
{Colors.BRIGHT_YELLOW}       █{Colors.END}       █████       {Colors.BRIGHT_YELLOW}█{Colors.END}     {Colors.BRIGHT_RED}{Colors.BOLD}▓      ▓   ▓  ▓{Colors.END}          
{Colors.BRIGHT_YELLOW}        ▀██{Colors.END}   █████   {Colors.BRIGHT_YELLOW}▄██▀{Colors.END}      {Colors.BRIGHT_RED}{Colors.BOLD}▓      ▓   ▓  ▓▓▓▓▓{Colors.END}      
{Colors.BRIGHT_YELLOW}          ▀███████████▀{Colors.END}                                        
{Colors.BRIGHT_YELLOW}              █████{Colors.END}                                            
{Colors.BRIGHT_YELLOW}             ███████{Colors.END}       {Colors.BRIGHT_CYAN}Forge Your Knowledge.{Colors.END}            
{Colors.BRIGHT_YELLOW}            ████ ████{Colors.END}      {Colors.BRIGHT_CYAN}Deep Read.  Archive.{Colors.END}              
{Colors.BRIGHT_YELLOW}           ████   ████{Colors.END}                                         
{Colors.BRIGHT_YELLOW}          ████     ████{Colors.END}    {Colors.BOLD}[ PaperForge v1.0 ]{Colors.END}               
"""
    print(logo)


def draw_border():
    """Draw a decorative border."""
    border = f"""
{Colors.BRIGHT_BLUE}╔══════════════════════════════════════════════════════════════════╗{Colors.END}
{Colors.BRIGHT_BLUE}║{Colors.END}                                                                  {Colors.BRIGHT_BLUE}║{Colors.END}
{Colors.BRIGHT_BLUE}╚══════════════════════════════════════════════════════════════════╝{Colors.END}
"""
    print(border)


def show_welcome():
    """Display the full welcome screen."""
    clear_screen()
    
    # Top border
    print(f"\n{Colors.BRIGHT_BLUE}╔══════════════════════════════════════════════════════════════════════╗{Colors.END}")
    print(f"{Colors.BRIGHT_BLUE}║{Colors.END}                                                                      {Colors.BRIGHT_BLUE}║{Colors.END}")
    
    # Logo
    draw_logo()
    
    # Bottom border
    print(f"{Colors.BRIGHT_BLUE}║{Colors.END}                                                                      {Colors.BRIGHT_BLUE}║{Colors.END}")
    print(f"{Colors.BRIGHT_BLUE}╚══════════════════════════════════════════════════════════════════════╝{Colors.END}")
    
    # Tagline
    print(f"\n{Colors.DIM}          Literature Research Pipeline for Obsidian + Zotero + AI Agent{Colors.END}")
    print(f"{Colors.DIM}                    MIT License | github.com/LLLin000/Research-workflow{Colors.END}\n")
    
    # Features grid
    print(f"{Colors.BOLD}Features:{Colors.END}")
    features = [
        ("⚡", "/LD", "Quick literature lookup"),
        ("🔍", "/LD-deep", "Keshav three-pass deep reading"),
        ("📄", "Auto-OCR", "PaddleOCR-VL API integration"),
        ("📊", "14 Charts", "Scientific chart reading guides"),
        ("🔗", "Zotero Sync", "Bi-directional sync"),
        ("🤖", "Multi-Agent", "OpenCode / Claude / Cursor / ..."),
    ]
    
    for icon, name, desc in features:
        print(f"  {Colors.BRIGHT_GREEN}{icon}{Colors.END}  {Colors.BOLD}{name:<12}{Colors.END}  {Colors.DIM}{desc}{Colors.END}")
    
    print()


def show_install_menu():
    """Show the installation steps menu."""
    print(f"{Colors.BOLD}Installation Steps:{Colors.END}\n")
    
    steps = [
        ("1", "Select Agent Platform", "OpenCode / Claude / Cursor / Copilot / ..."),
        ("2", "Configure Vault Paths", "Customizable folder structure"),
        ("3", "Link Zotero Library", "Auto-detect or manual configuration"),
        ("4", "Deploy Skills", "OCR + Deep Reading + Chart Guides"),
        ("5", "Validate Setup", "Integrity check and test"),
    ]
    
    for num, title, desc in steps:
        print(f"  {Colors.BRIGHT_CYAN}[{num}]{Colors.END}  {Colors.BOLD}{title:<22}{Colors.END}  {Colors.DIM}→ {desc}{Colors.END}")
    
    print()
    input(f"{Colors.BRIGHT_YELLOW}Press Enter to begin forging your knowledge...{Colors.END}")


def show_progress_bar(step: int, total: int, label: str):
    """Display a progress bar."""
    width = 40
    filled = int(width * step / total)
    bar = "█" * filled + "░" * (width - filled)
    percent = int(100 * step / total)
    
    print(f"\r  {Colors.BRIGHT_CYAN}[{bar}]{Colors.END} {Colors.BOLD}{percent}%{Colors.END}  {label}", end='', flush=True)
    if step == total:
        print()  # New line when complete


def show_completion():
    """Show installation completion screen."""
    clear_screen()
    
    print(f"""
{Colors.BRIGHT_GREEN}╔══════════════════════════════════════════════════════════════════════╗{Colors.END}
{Colors.BRIGHT_GREEN}║{Colors.END}                                                                      {Colors.BRIGHT_GREEN}║{Colors.END}
{Colors.BRIGHT_GREEN}║{Colors.END}   {Colors.BOLD}{Colors.BRIGHT_WHITE}✓  INSTALLATION COMPLETE{Colors.END}                                         {Colors.BRIGHT_GREEN}║{Colors.END}
{Colors.BRIGHT_GREEN}║{Colors.END}                                                                      {Colors.BRIGHT_GREEN}║{Colors.END}
{Colors.BRIGHT_GREEN}║{Colors.END}   {Colors.BRIGHT_YELLOW}Your knowledge forge is ready!{Colors.END}                                 {Colors.BRIGHT_GREEN}║{Colors.END}
{Colors.BRIGHT_GREEN}║{Colors.END}                                                                      {Colors.BRIGHT_GREEN}║{Colors.END}
{Colors.BRIGHT_GREEN}╚══════════════════════════════════════════════════════════════════════╝{Colors.END}

{Colors.BOLD}Next Steps:{Colors.END}
  1. Open Obsidian and load your vault
  2. Index your library: Run the index-refresh worker
  3. Queue papers for analysis
  4. Run OCR on queued papers
  5. Start deep reading: {Colors.BRIGHT_CYAN}/LD-deep <zotero_key>{Colors.END}

{Colors.BOLD}Commands:{Colors.END}
  {Colors.BRIGHT_CYAN}/LD{Colors.END}         Quick literature lookup
  {Colors.BRIGHT_CYAN}/LD-deep{Colors.END}    Keshav three-pass deep reading
  {Colors.BRIGHT_CYAN}/LD-queue{Colors.END}   Process queued papers

{Colors.DIM}For help: See AGENTS.md in your vault root{Colors.END}
""")


if __name__ == "__main__":
    try:
        show_welcome()
        show_install_menu()
        
        # Simulate installation steps
        steps = [
            "Detecting agent platform...",
            "Configuring vault paths...",
            "Linking Zotero library...",
            "Deploying workflow scripts...",
            "Installing chart guides...",
            "Validating setup...",
        ]
        
        print(f"\n{Colors.BOLD}Installing PaperForge...{Colors.END}\n")
        for i, step in enumerate(steps, 1):
            show_progress_bar(i, len(steps), step)
            time.sleep(0.5)
        
        time.sleep(0.5)
        show_completion()
        
    except KeyboardInterrupt:
        print(f"\n\n{Colors.BRIGHT_RED}Installation cancelled.{Colors.END}")
        sys.exit(1)
