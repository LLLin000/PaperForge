import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

p = Path(r'D:\L\OB\Literature-hub\System\PaperForge\ocr\TSCKAVIS\structure\blocks.structured.jsonl')
rows = [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines() if line.strip()]

for i in range(123, 132):
    r = rows[i]
    print((i, r.get('page'), r.get('role'), r.get('bbox'), (r.get('text') or '')[:140], r.get('_in_visual_container')))

print('---')
ftxt = Path(r'D:\L\OB\Literature-hub\System\PaperForge\ocr\TSCKAVIS\fulltext.md').read_text(encoding='utf-8', errors='replace')
for needle in ['In addition to the mitochondrial', 'Osteoarthritic chondrocytes also']:
    idx = ftxt.lower().find(needle.lower())
    if idx != -1:
        print('FOUND:', needle[:60], 'context:', repr(ftxt[max(0, idx-60):idx+120]))
    else:
        print('NOT FOUND:', needle[:60])
