from pathlib import Path
import json

vault = Path(r"D:\L\OB\Literature-hub")
structured_path = vault / "System" / "PaperForge" / "ocr" / "SAN9AYVR" / "blocks.structured.jsonl"
profiles_path = vault / "System" / "PaperForge" / "ocr" / "SAN9AYVR" / "role_span_profiles.json"

if structured_path.exists():
    print(f"structured blocks: {structured_path.stat().st_size} bytes")
    with open(structured_path, encoding="utf-8") as f:
        line = f.readline()
        row = json.loads(line)
        has_span = "span_metadata" in row
        has_role = row.get("role")
        has_conf = row.get("role_confidence")
        print(f"  first block role={has_role}, conf={has_conf}, has_span_metadata={has_span}")

    total = 0
    with_span = 0
    with open(structured_path, encoding="utf-8") as f:
        for line in f:
            total += 1
            row = json.loads(line)
            if row.get("span_metadata"):
                with_span += 1
    print(f"  total blocks: {total}, with span_metadata: {with_span} ({100*with_span/total:.1f}%)")
else:
    print("structured blocks not found")

if profiles_path.exists():
    profiles = json.loads(profiles_path.read_text(encoding="utf-8"))
    print(f"\nrole_span_profiles.json: {len(profiles)} roles")
    for role, p in sorted(profiles.items()):
        print(f"  {role}: count={p['block_count']}, size={p['mean_size']}, quality={p['quality']}")
else:
    print("role_span_profiles.json not found")

second_pass_total = 0
span_alt_total = 0
with open(structured_path, encoding="utf-8") as f:
    for line in f:
        row = json.loads(line)
        ev = row.get("evidence", [])
        for e in ev:
            if "second_pass" in e:
                second_pass_total += 1
            if "span_alternatives" in e:
                span_alt_total += 1
print(f"\nSecond-pass applied: {second_pass_total} blocks")
print(f"Span alternatives flagged: {span_alt_total} blocks")
