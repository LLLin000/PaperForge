import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

p = Path(r"D:\L\OB\Literature-hub\System\PaperForge\ocr\TSCKAVIS\structure\blocks.structured.jsonl")
rows = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]

for i in range(123, 132):
    r = rows[i]
    ctxt = r.get("_container_text") or ""
    print(i, r.get("role"), "has_ct=" + str(bool(ctxt)), r.get("bbox"),
          (r.get("text") or "")[:100],
          "|CT:" + ctxt[:160] if ctxt else "")

print("---")
ftxt = Path(r"D:\L\OB\Literature-hub\System\PaperForge\ocr\TSCKAVIS\fulltext.md").read_text(encoding="utf-8", errors="replace")
for needle in ["Box 1", "mitochondrial", "Osteoarthritic"]:
    idx = ftxt.lower().find(needle.lower())
    if idx != -1:
        line_start = ftxt.rfind("\n", 0, idx) + 1
        line_end = ftxt.find("\n", idx)
        ctx = ftxt[max(0, idx-40):idx+120]
        print(needle, "->", ctx)
    else:
        print(needle, "-> NOT FOUND")
