"""Batch re-process all OCR papers and scan for common defects."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, r"D:\L\Med\Research\99_System\LiteraturePipeline\github-release")
from paperforge.worker.ocr import postprocess_ocr_result

VAULT = Path(r"D:\L\Med\Research_LitControl_Sandbox")
OCR_DIR = VAULT / "System" / "PaperForge" / "ocr"

# Collect all papers with result.json
papers = sorted([d.name for d in OCR_DIR.iterdir() if (d / "json" / "result.json").exists()])
print(f"Processing {len(papers)} papers...\n")

results = []
for key in papers:
    ocr_root = OCR_DIR / key
    json_path = ocr_root / "json" / "result.json"
    all_results = json.loads(json_path.read_text(encoding="utf-8"))

    page_count, _, _, error = postprocess_ocr_result(VAULT, key, all_results)

    text = (ocr_root / "fulltext.md").read_text(encoding="utf-8")
    lines = text.splitlines()

    defects = []

    # 1. Image count
    images = [l for l in lines if l.startswith("![[")]
    img_count = len(images)

    # 2. Bare < outside math (HTML bleed indicator)
    text_no_math = re.sub(r'\$[^$]+\$', '', text)
    text_no_math = re.sub(r'<!--.*?-->', '', text_no_math)
    text_no_math = re.sub(r'<table.*?</table>', '', text_no_math, flags=re.DOTALL)
    bare_lt_lines = set()
    for i, l in enumerate(text_no_math.splitlines(), 1):
        if '<' in l and any(c.isalpha() for c in l):
            bare_lt_lines.add(i)
    if bare_lt_lines:
        defects.append(f"bare < at {sorted(bare_lt_lines)[:3]}")

    # 3. [^correspondence] in captions
    corr_in_caption = sum(1 for l in lines if '[^correspondence]' in l and 'Figure' in l)
    if corr_in_caption:
        defects.append(f"[^correspondence] in {corr_in_caption} captions")

    # 4. *p bleed (bare *p NOT in math)
    bare_star = sum(1 for l in lines if re.search(r'(?<!\$)\*\s*p\s*<', l))
    if bare_star:
        defects.append(f"bare *p< in {bare_star} lines")

    # 5. Triple-asterisk strong in *p context (e.g. "***")
    strong_p = sum(1 for l in lines if '**p' in l and re.search(r'\*{3,}', l))
    if strong_p:
        defects.append(f"strong **p potential in {strong_p} lines")

    # 6. Anand split
    anand = sum(1 for l in lines if 'An and ' in l and 'Thirupathi' in lines[lines.index(l)] if False)
    # simpler check
    anand_any = sum(1 for l in lines if ' An and ' in l or 'An and T' in l)
    if anand_any:
        defects.append("Anand split detected")

    # 7. Orphan captions (Figure N with no preceding image)
    fig_caps = [i for i, l in enumerate(lines) if re.match(r'^Figure \d+', l)]
    orphan_caps = 0
    for idx in fig_caps:
        # Check previous non-empty line before this caption
        prev = None
        for j in range(idx - 1, -1, -1):
            if lines[j].strip() and not lines[j].startswith("<!--"):
                prev = lines[j]
                break
        if prev and not prev.startswith("![["):
            orphan_caps += 1
    if orphan_caps:
        defects.append(f"{orphan_caps} captions have no preceding image")

    # 8. Suspicious merged images (very wide + tall single image)
    found_suspicious = 0
    for l in lines:
        if l.startswith("![[") and "images/blocks" in l:
            m = re.search(r'(\d+)_(\d+)_(\d+)_(\d+)\.jpg', l)
            if m:
                w = int(m.group(3)) - int(m.group(1))
                h = int(m.group(4)) - int(m.group(2))
                if w > 700 and h > 700:
                    found_suspicious += 1
    if found_suspicious:
        defects.append(f"{found_suspicious} large images (>700x700)")

    # 9. Cross-page hyphenation
    for i, l in enumerate(lines):
        stripped = l.strip()
        if stripped.endswith('-') and len(stripped) > 3 and i + 1 < len(lines):
            next_l = lines[i+1].strip()
            if next_l.startswith(('a','b','c','d','e','f','g','h','i','j','k','l','m',
                                   'n','o','p','q','r','s','t','u','v','w','x','y','z')):
                defects.append("cross-page hyphenation")
                break

    # 10. LaTeX spacing
    loose_dollar = sum(1 for l in lines if '$ ' in l or ' $' in l)
    if loose_dollar > 0.5 * len(lines):
        defects.append(f"many loose $ ({loose_dollar})")

    verdict = "CLEAN" if not defects else "; ".join(defects)
    results.append((key, img_count, page_count, verdict, len(lines)))

# Summary
clean = sum(1 for _, _, _, v, _ in results if v == "CLEAN")
print(f"Processed {len(papers)} papers: {clean} clean, {len(papers)-clean} with issues\n")

for key, imgs, pages, verdict, lines in results:
    if verdict != "CLEAN":
        print(f"  {key} ({pages}p, {imgs}img): {verdict}")

print("\nDone.")
