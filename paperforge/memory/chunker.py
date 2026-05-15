from __future__ import annotations

import re
from pathlib import Path

_IMG_LINK_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
_IMG_MD_RE = re.compile(r"!\[\[.*?\]\]")
_SECTION_RE = re.compile(
    r"^\s*(Introduction|Methods|Materials|Results|Discussion|Conclusion"
    r"|Abstract|Background|References|Supplementary"
    r"|Figure\s+\d+|Fig\.?\s*\d+|Table\s+\d+)",
    re.IGNORECASE,
)


def chunk_fulltext(fulltext_path: Path) -> list[dict]:
    """Split OCR fulltext.md into overlapping chunks for embedding.

    Returns list of dicts with keys: text, section, page_number, chunk_index, token_estimate.
    """
    if not fulltext_path.exists():
        return []

    raw = fulltext_path.read_text(encoding="utf-8")
    raw = _IMG_LINK_RE.sub("[Figure]", raw)
    raw = _IMG_MD_RE.sub("[Figure]", raw)

    pages = re.split(r"<!-- page \d+ -->", raw)
    chunks: list[dict] = []
    chunk_idx = 0

    for page_num, page in enumerate(pages, start=1):
        if not page.strip():
            continue

        paragraphs = [p.strip() for p in page.split("\n\n") if p.strip()]
        section_name = "Text"

        i = 0
        while i < len(paragraphs):
            para = paragraphs[i]
            sect_match = _SECTION_RE.match(para)
            if sect_match and len(para) < 80:
                section_name = sect_match.group(1)
                i += 1
                continue

            group = [para]
            j = i + 1
            while j < len(paragraphs) and j < i + 3:
                next_p = paragraphs[j]
                if _SECTION_RE.match(next_p) and len(next_p) < 80:
                    break
                group.append(next_p)
                j += 1

            text = "\n\n".join(group)
            chunk_idx += 1
            token_estimate = len(text) // 4

            chunks.append({
                "text": text,
                "section": section_name,
                "page_number": page_num,
                "chunk_index": chunk_idx,
                "token_estimate": token_estimate,
            })

            i = j - 1 if j > i + 1 else j
            if i == j:
                i += 1

    return chunks
