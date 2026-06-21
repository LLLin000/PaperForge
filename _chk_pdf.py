import json
from pathlib import Path

for paper in ['RKSLQRIM', '6DIINFHX', 'GTRPMM56', 'KIX7SKXQ']:
    meta_path = Path(f'D:/L/OB/Literature-hub/System/PaperForge/ocr/{paper}/raw/source_metadata.json')
    if not meta_path.exists():
        print(f'{paper}: NO METADATA')
        continue
    meta = json.load(open(meta_path,'r',encoding='utf-8'))
    src = meta.get('source_pdf','')
    exists = Path(src).exists() if src else False
    print(f'{paper}: pdf={src[:60]}... exists={exists}')

    # Check backfill status on structured blocks
    blk_path = Path(f'D:/L/OB/Literature-hub/System/PaperForge/ocr/{paper}/structure/blocks.structured.jsonl')
    if blk_path.exists():
        lines = [json.loads(l) for l in blk_path.read_text(encoding='utf-8').strip().split('\n') if l.strip()]
        empty_us = [b for b in lines if b.get('role','')=='unknown_structural' and len(str(b.get('text','') or ''))==0]
        recovered = sum(1 for b in lines if b.get('_ocr_raw_status')=='missing_text_recovered')
        print(f'  empty unknown_structural: {len(empty_us)}, recovered: {recovered}')
        if empty_us:
            b = empty_us[0]
            print(f'  sample: p{b.get("page")}:{b.get("block_id")} raw_label={b.get("raw_label")} spans={len(b.get("span_metadata",[]))} status={b.get("_ocr_raw_status")}')
