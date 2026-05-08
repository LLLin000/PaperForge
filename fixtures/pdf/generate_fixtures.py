"""Generate minimal valid PDF fixtures for test golden datasets.

Run: python fixtures/pdf/generate_fixtures.py
Output: blank.pdf, two_page.pdf, with_figures.pdf, CJK_文件名.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import fitz  # pymupdf
except ImportError:
    print("ERROR: pymupdf not installed. Run: pip install pymupdf")
    sys.exit(1)

OUT_DIR = Path(__file__).resolve().parent
WIDTH, HEIGHT = 612, 792  # US Letter


def blank_pdf(path: Path) -> None:
    """Generate a single-page blank PDF with a title."""
    doc = fitz.open()
    page = doc.new_page(width=WIDTH, height=HEIGHT)
    page.insert_text((72, 72), "Blank PDF for PaperForge testing", fontsize=12)
    doc.save(str(path))
    doc.close()
    print(f"  Created: {path.name} ({path.stat().st_size} bytes)")


def two_page_pdf(path: Path) -> None:
    """Generate a two-page PDF for multi-page resolution tests."""
    doc = fitz.open()
    page1 = doc.new_page(width=WIDTH, height=HEIGHT)
    page1.insert_text((72, 72), "Page 1 of 2", fontsize=12)
    page2 = doc.new_page(width=WIDTH, height=HEIGHT)
    page2.insert_text((72, 72), "Page 2 of 2", fontsize=12)
    doc.save(str(path))
    doc.close()
    print(f"  Created: {path.name} ({path.stat().st_size} bytes)")


def with_figures_pdf(path: Path) -> None:
    """Generate a PDF with placeholder rectangles simulating embedded figures."""
    doc = fitz.open()
    page = doc.new_page(width=WIDTH, height=HEIGHT)
    page.insert_text((72, 72), "Paper with embedded figures", fontsize=12)
    page.insert_text((72, 100), "Figure 1: Testing setup", fontsize=10)
    page.draw_rect((72, 120, 300, 300), color=(0, 0, 0), width=1)
    page.insert_text((72, 320), "Figure 2: Results chart", fontsize=10)
    page.draw_rect((72, 340, 300, 500), color=(0, 0, 0), width=1)
    doc.save(str(path))
    doc.close()
    print(f"  Created: {path.name} ({path.stat().st_size} bytes)")


def cjk_filename_pdf(path: Path) -> None:
    """Generate a PDF with CJK filename for CJK path resolution tests."""
    doc = fitz.open()
    page = doc.new_page(width=WIDTH, height=HEIGHT)
    page.insert_text((72, 72), "中文论文测试文件", fontsize=12)
    page.insert_text(
        (72, 100),
        "This PDF tests CJK filename handling in path resolution.",
        fontsize=10,
    )
    doc.save(str(path))
    doc.close()
    print(f"  Created: {path.name} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    print("Generating PDF fixtures...")
    blank_pdf(OUT_DIR / "blank.pdf")
    two_page_pdf(OUT_DIR / "two_page.pdf")
    with_figures_pdf(OUT_DIR / "with_figures.pdf")
    cjk_filename_pdf(OUT_DIR / "CJK_文件名.pdf")
    print("Done. 4 PDF files created.")
