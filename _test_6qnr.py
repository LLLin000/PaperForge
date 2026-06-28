import json, sys
sys.path.insert(0, '.')
from paperforge.worker.ocr_figures import build_figure_inventory

for paper in ['6QNRHRKX', 'KIX7SKXQ']:
    with open(f'D:/L/OB/Literature-hub/System/PaperForge/ocr/{paper}/structure/blocks.structured.jsonl','r',encoding='utf-8') as f:
        blocks = [json.loads(l) for l in f.read().strip().split('\n') if l.strip()]
    result = build_figure_inventory(blocks)
    mt = len(result.get('matched_figures', []))
    amb = len(result.get('ambiguous_figures', []))
    print(f'{paper}: matched={mt} ambiguous={amb}')
    for a in result.get('ambiguous_figures',[]):
        fn = a.get('figure_number','?')
        hr = a.get('hold_reason','?')
        ca = len(a.get('candidates',[]))
        pg = a.get('page','?')
        print(f'  Fig {fn} p{pg}: {ca}cand {hr}')
    for m in result.get('matched_figures',[]):
        fn = m.get('figure_number','?')
        pg = m.get('page')
        n = len(m.get('matched_assets',[]))
        fl = m.get('flags',[])
        print(f'  MATCHED Fig {fn} p{pg}: {n} assets {fl}')
