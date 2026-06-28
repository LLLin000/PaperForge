import json
from pathlib import Path

json_path = Path("D:/L/OB/Literature-hub/System/PaperForge/ocr/7C8829BD/json/result.json")
data = json.loads(json_path.read_text(encoding="utf-8"))

pageno = 0
for payload in data:
    for res in payload.get("layoutParsingResults", []):
        pageno += 1
        if pageno != 7:
            continue
        blocks = res.get("prunedResult", {}).get("parsing_res_list", [])

        from paperforge.worker.ocr import block_sort_key, validate_block_order, is_embedded_figure_text_block
        from paperforge.worker.ocr_orchestrator import reorder_blocks_layered

        sorted_blocks = sorted(blocks, key=block_sort_key)
        validated = validate_block_order(sorted_blocks, 1191)

        print("=== is_embedded_figure_text_block on VALIDATED blocks ===")
        for b in validated:
            lbl = b.get("block_label", "")
            if lbl == "paragraph_title":
                result = is_embedded_figure_text_block(b, validated, page_width=1191, page_height=1684)
                txt = b.get("block_content", "")[:60]
                print(f"  [{txt}] => embedded={result}")

        layered = reorder_blocks_layered(validated, page_width=1191, page_height=1684)

        print()
        print("=== is_embedded_figure_text_block on LAYERED blocks ===")
        for b in layered:
            lbl = b.get("block_label", "")
            if lbl == "paragraph_title":
                result = is_embedded_figure_text_block(b, layered, page_width=1191, page_height=1684)
                txt = b.get("block_content", "")[:60]
                print(f"  [{txt}] => embedded={result}")

        print()
        print("=== Role assignment ===")
        from paperforge.worker.ocr_roles import assign_block_role
        for b in validated:
            lbl = b.get("block_label", "")
            if lbl == "paragraph_title":
                role = assign_block_role(b, validated, page_width=1191, page_height=1684)
                txt = b.get("block_content", "")[:60]
                print(f"  [{txt}] => role={role.role} conf={role.confidence}")
        break
    break
