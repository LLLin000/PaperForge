import json
from pathlib import Path

vault = Path(r"D:\L\OB\Literature-hub")
key = "TSCKAVIS"
root = vault / "System" / "PaperForge" / "ocr" / key
meta_path = root / "metadata" / "resolved_metadata.json"
src_meta_path = root / "metadata" / "source_metadata.json"
struct_path = root / "structure" / "blocks.structured.jsonl"

if meta_path.exists():
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    print("=== RESOLVED METADATA ===")
    for k, v in meta.items():
        print(f"  {k}: {json.dumps(v, ensure_ascii=False)[:150]}")
else:
    print("METADATA NOT FOUND")

if src_meta_path.exists():
    src = json.loads(src_meta_path.read_text(encoding="utf-8"))
    print("\n=== SOURCE METADATA ===")
    print(f'  title: {str(src.get("title", ""))[:80]}')
    authors = src.get("authors", [])
    print(f"  authors ({len(authors)}): {authors[:3]}")
else:
    print("\nSOURCE METADATA NOT FOUND")

if struct_path.exists():
    blocks = [json.loads(line) for line in struct_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    title_blocks = [b for b in blocks if b.get("role") in ("paper_title", "doc_title")]
    author_blocks = [b for b in blocks if b.get("role") == "authors"]
    si_blocks = [b for b in blocks if b.get("role") in ("structured_insert", "structured_insert_candidate")]
    ni_blocks = [b for b in blocks if b.get("role") == "non_body_insert"]
    kp_blocks = [b for b in blocks if "key point" in str(b.get("text") or "").lower()]
    print(f"\n=== STRUCTURED BLOCKS ({len(blocks)} total) ===")
    print(f"  paper_title: {len(title_blocks)}")
    for b in title_blocks:
        t = (b.get("text") or "")[:80]
        print(f"    -> {t}")
    print(f"  authors: {len(author_blocks)}")
    for b in author_blocks:
        t = (b.get("text") or "")[:80]
        print(f"    -> {t}")
    print(f"  structured_insert: {len(si_blocks)}")
    for b in si_blocks:
        t = (b.get("text") or "")[:80]
        print(f"    -> {t}")
    print(f"  non_body_insert: {len(ni_blocks)}")
    for b in ni_blocks[:5]:
        t = (b.get("text") or "")[:80]
        print(f"    -> {t}")
    if len(ni_blocks) > 5:
        print(f"    ... ({len(ni_blocks)} total)")
    print(f"  key-point blocks: {len(kp_blocks)}")
    for b in kp_blocks:
        r = b.get("role")
        t = (b.get("text") or "")[:80]
        print(f"    role={r} text={t}")
