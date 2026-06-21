import json; from pathlib import Path
audit=Path('audit')
papers=['6QNRHRKX','7S5ZEVSK','8K39NHUQ','5DIEAVPW','RKSLQRIM']
for k in papers:
    fp=audit/k/'figure_table_ownership_summary.json'
    if not fp.exists(): continue
    d=json.load(open(fp,'r',encoding='utf-8'))
    print(f'\n=== {k} ===')
    matched=d['figures']['matched_count']; amb=d['figures']['ambiguous_count']
    print(f'fig={matched}/{matched+amb}')
    for a in d['figures'].get('ambiguous',[]):
        fn=a.get('figure_number','?')
        ca=len(a.get('candidate_asset_ids',[]))
        hr=a.get('hold_reason','?')
        pg=a.get('page','?')
        print(f'  Fig {fn} p{pg}: {ca}cand {hr}')
