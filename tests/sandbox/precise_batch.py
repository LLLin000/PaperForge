"""Precise batch defect report."""
import re
import json
import sys
from pathlib import Path

sys.path.insert(0, r"D:\L\Med\Research\99_System\LiteraturePipeline\github-release")

VAULT = Path(r"D:\L\Med\Research_LitControl_Sandbox")
OCR_DIR = VAULT / "System" / "PaperForge" / "ocr"
papers = sorted([d.name for d in OCR_DIR.iterdir() if (d / "json" / "result.json").exists()])

print(f"=== BIG BATCH REPORT === ({len(papers)} papers)\n")

for key in papers:
    md = OCR_DIR / key / "fulltext.md"
    text = md.read_text(encoding="utf-8")
    lines = text.splitlines()

    issues = []

    # Image count vs caption count
    images = [l for l in lines if l.startswith("![[")]
    fig_caps = [(i, l) for i, l in enumerate(lines) if re.match(r'^Figure \d+', l)]
    img_num = len(images)
    cap_num = len(fig_caps)

    # Captions without preceding image (REAL issue)
    orphan = 0
    for idx, _ in fig_caps:
        prev = None
        for j in range(idx-1, -1, -1):
            s = lines[j].strip()
            if s and not s.startswith("<!--"):
                prev = (j, s)
                break
        if not (prev and prev[1].startswith("![[") and "images/blocks" in prev[1]):
            orphan += 1
    if orphan:
        issues.append(f"{orphan}/{cap_num} captions lack preceding image")

    # Check: is there an image within 5 lines above each caption?
    remote = 0
    for idx, _ in fig_caps:
        found = False
        for j in range(idx-1, max(-1, idx-6), -1):
            if lines[j].strip().startswith("![["):
                found = True
                break
        if not found:
            remote += 1
    if remote and remote < cap_num:
        issues.append(f"{remote}/{cap_num} captions have image >5 lines away")

    # Large images that could be merged figures
    huge_merges = 0
    for l in lines:
        m = re.search(r'(\d+)_(\d+)_(\d+)_(\d+)\.jpg', l)
        if m:
            w = int(m.group(3)) - int(m.group(1))
            h = int(m.group(4)) - int(m.group(2))
            if w > 600 and h > 1000:
                huge_merges += 1
    if huge_merges:
        issues.append(f"{huge_merges} extremely tall images (>1000px)")

    # Bare < in text lines (not math, not table, not comment) — REAL ISSUE
    bare_lt = 0
    for i, l in enumerate(lines):
        s = l.strip()
        if s.startswith("<!--") or s.startswith("<table") or s.startswith("</table"):
            continue
        no_math = re.sub(r'\$[^$]+\$', '', l)
        if '<' in no_math and any(c.isalpha() for c in no_math):
            bare_lt += 1
    if bare_lt:
        issues.append(f"{bare_lt} bare < in text (may trigger HTML)")

    # [^correspondence] bleeding
    corr = sum(1 for l in lines if '[^correspondence]' in l and 'Figure' in l)
    if corr:
        issues.append(f"{corr} [^correspondence] in Figure captions")

    # *p bleeding — only check lines where NOT preceded by $ anywhere on the line
    star_issues = 0
    for l in lines:
        no_math = re.sub(r'\$[^$]+\$', '', l)
        if re.search(r'\*\s*p\s*<', no_math):
            star_issues += 1
    if star_issues:
        issues.append(f"{star_issues} *p< outside math")

    # Anand
    if any('An and' in l for l in lines):
        issues.append("Anand split found")

    # Text ordering: check for obviously broken headers
    for l in lines[:20]:
        if l.strip().startswith("### ") and l.strip().count("###") > 2:
            issues.append("broken heading")
            break

    # Cross-page hyphen
    for i, l in enumerate(lines):
        s = l.strip()
        if s.endswith('-') and len(s) > 3:
            prev_words = s.rstrip('-')
            if prev_words and not prev_words.endswith('\\') and not prev_words.rstrip('-')[0].isupper():
                issues.append("possible cross-page hyphen")
                break

    verdict = ", ".join(issues) if issues else "CLEAN"
    print(f"  {key}: {img_num}i/{cap_num}c | {verdict}")

print(f"\nDone.")
