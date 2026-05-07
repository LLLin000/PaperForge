"""Detailed inspection of flagged papers."""
import re
from pathlib import Path

OCR_DIR = Path(r"D:\L\Med\Research_LitControl_Sandbox\System\PaperForge\ocr")
KEYS = ["2AGGSMVQ", "2BFG5P6B", "2BYRLKQS", "2E4EPHN2", "2GN9LMCW", "2H8MZ27H"]

for key in KEYS:
    md = OCR_DIR / key / "fulltext.md"
    text = md.read_text(encoding="utf-8")
    lines = text.splitlines()

    print(f"=== {key} ({len(lines)} lines) ===")

    # List all Figure captions and preceding image
    fig_lines = []
    for i, l in enumerate(lines):
        if re.match(r'^Figure \d+', l):
            # Find preceding non-comment, non-blank line
            prev = None
            for j in range(i-1, -1, -1):
                s = lines[j].strip()
                if s and not s.startswith("<!--"):
                    prev = (j, s)
                    break
            before = "IMAGE" if prev and prev[1].startswith("![[") else (prev[1][:80] if prev else "NONE")
            fig_lines.append((i+1, l[:100], before))

    for ln, caption, before in fig_lines:
        print(f"  L{ln:4d}: {before:30s} | {caption}")

    # Check bare *p< patterns — show actual lines
    for i, l in enumerate(lines):
        m = re.search(r'(?<!\$)\*\s*p\s*<', l)
        if m:
            # Find context around match
            start = max(0, m.start() - 20)
            end = min(len(l), m.end() + 20)
            ctx = l[start:end]
            print(f"  *p at L{i+1}: ...{ctx}...")

    print()
