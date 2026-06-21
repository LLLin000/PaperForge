import json; from pathlib import Path
audit=Path('audit')
papers=sorted([d.name for d in audit.iterdir() if (d/'figure_table_ownership_summary.json').exists()])
total_fm=0; total_fa=0
for k in papers:
    d=json.load(open(audit/k/'figure_table_ownership_summary.json','r',encoding='utf-8'))
    fm=d['figures']['matched_count']; fa=d['figures']['ambiguous_count']
    tm=d['tables']['matched_count']; ta=d['tables']['ambiguous_count']
    total_fm+=fm; total_fa+=fa
    print(f'{k:<10} fig={fm}/{fm+fa}  tbl={tm}/{tm+ta}')
print(f'\nTotal: {total_fm}/{total_fm+total_fa} = {total_fm/(total_fm+total_fa)*100:.0f}%' if total_fm+total_fa else '')
