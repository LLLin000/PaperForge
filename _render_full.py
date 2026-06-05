import json, sys, os
from pathlib import Path

sys.path.insert(0, "D:/L/Med/Research/99_System/LiteraturePipeline/ocr-reading-order-layers")
from paperforge.worker.ocr import render_page_blocks, block_sort_key, validate_block_order

json_path = Path("D:/L/OB/Literature-hub/System/PaperForge/ocr/7C8829BD/json/result.json")
data = json.loads(json_path.read_text(encoding="utf-8"))

vault = Path("D:/L/OB/Literature-hub")
images_dir = Path("D:/L/OB/Literature-hub/System/PaperForge/ocr/7C8829BD/images")
page_cache_dir = Path("D:/L/OB/Literature-hub/System/PaperForge/ocr/7C8829BD/pages")

pageno = 0
all_lines = []

for payload in data:
    for res in payload.get("layoutParsingResults", []):
        pageno += 1
        pruned = res.get("prunedResult", {})
        blocks = pruned.get("parsing_res_list", [])
        if not blocks:
            continue
        try:
            rendered = render_page_blocks(vault, pageno, res, images_dir, page_cache_dir, pdf_doc=None)
            all_lines.extend(rendered)
        except Exception as e:
            all_lines.append(f"<!-- page {pageno} ERROR: {e} -->")

output = "\n\n".join(all_lines)
out_path = Path(os.environ.get("TEMP", "/tmp")) / "7c8829bd_layered_fulltext.md"
out_path.write_text(output, encoding="utf-8")

# Stats
heading_count = output.count("### ")
page_count = output.count("<!-- page ")
print(f"Pages: {page_count}")
print(f"Headings: {heading_count}")
print(f"Output: {out_path}")
print(f"Size: {len(output)} chars")

# Show all headings
import re
headings = re.findall(r"^### (.+)$", output, re.MULTILINE)
print("\nSection headings found:")
for h in headings:
    print(f"  ### {h}")
