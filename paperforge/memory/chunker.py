from __future__ import annotations

import re
from pathlib import Path

# Section detection keywords (case-insensitive, must appear as short standalone line)
SECTION_PATTERNS = [
    re.compile(r'^\s*(introduction|methods|materials|results|discussion|conclusion|abstract|background|references|supplementary|acknowledgments?)\s*$', re.IGNORECASE),
    re.compile(r'^\s*(figure\s*\d+|fig\.?\s*\d+|table\s*\d+)\s*$', re.IGNORECASE),
]

def _detect_section(line: str) -> str:
    """Try to identify a section title from a line."""
    stripped = line.strip()
    if len(stripped) > 80:
        return ""
    for pat in SECTION_PATTERNS:
        m = pat.match(stripped)
        if m:
            return m.group(0)
    # Heuristic: ALL CAPS short line, no period
    if stripped.isupper() and len(stripped) > 2 and '.' not in stripped:
        return stripped
    # Short line, no period, surrounded by blank lines (checked by caller)
    if len(stripped) < 80 and '.' not in stripped[-5:]:
        return stripped
    return ""


def _clean_text(text: str) -> str:
    """Remove image links and clean text for embedding."""
    # Remove standalone image links: ![[path]]
    text = re.sub(r'^!\[\[.*\]\]\s*$', '', text, flags=re.MULTILINE)
    # Replace inline images with placeholder
    text = re.sub(r'!\[\[.*?\]\]', '[Figure]', text)
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def chunk_fulltext(fulltext_path: Path) -> list[dict]:
    """Chunk a fulltext.md into embeddable segments.

    Returns list of dicts with: text, section, page_number, chunk_index, token_estimate.
    """
    if not fulltext_path.exists():
        return []

    text = _clean_text(fulltext_path.read_text(encoding="utf-8"))

    # Split by page markers
    pages = re.split(r'<!--\s*page\s*(\d+)\s*-->', text)
    # pages[0] = before first marker, pages[1] = page num, pages[2] = content, pages[3] = page num, ...

    current_section = "Text"
    parts = []

    if len(pages) > 1 and not pages[1].strip().isdigit():
        # No page marker found, treat whole text as one page
        parts = [(1, text)]
    else:
        for j in range(1, len(pages), 2):
            if j + 1 < len(pages):
                try:
                    page_num = int(pages[j].strip())
                    page_content = pages[j + 1]
                    parts.append((page_num, page_content))
                except ValueError:
                    continue

    if not parts and text.strip():
        parts = [(1, text)]

    chunks = []
    chunk_index = 0
    for page_num, page_text in parts:
        # Split page into paragraphs by double newlines
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', page_text) if p.strip()]

        # Detect section headers
        for para in paragraphs:
            section = _detect_section(para)
            if section:
                current_section = section

        # Group 2-3 paragraphs per chunk with 1-paragraph overlap
        i = 0
        while i < len(paragraphs):
            chunk_paras = paragraphs[i:i+3]
            chunk_text = "\n\n".join(chunk_paras)
            token_estimate = len(chunk_text.split())  # rough: 1 token ≈ 1 word
            chunks.append({
                "text": chunk_text,
                "section": current_section,
                "page_number": page_num,
                "chunk_index": chunk_index,
                "token_estimate": token_estimate,
            })
            chunk_index += 1
            i += max(1, len(chunk_paras) - 1)  # advance but leave 1 overlap

    return chunks
