import json
with open('D:/L/OB/Literature-hub/System/PaperForge/ocr/VFS8CBW2/structure/blocks.structured.jsonl','r',encoding='utf-8') as f:
    lines = [json.loads(l) for l in f.read().strip().split('\n') if l.strip()]
p11 = [b for b in lines if b.get('page')==11]
p10 = [b for b in lines if b.get('page')==10]
p12 = [b for b in lines if b.get('page')==12]

print('=== PAGE 10 ===')
for b in p10:
    bid = b['block_id']
    role = b.get('role','?')
    txt = str(b.get('text','') or '')[:80]
    bbox = b.get('bbox',[])
    print(f'  id={bid:3d} role={role:25s} text_len={len(txt):4d} bbox={bbox}')
    if txt:
        print(f'    [{txt}]')

print('\n=== PAGE 11 ===')
for b in p11:
    bid = b['block_id']
    role = b.get('role','?')
    txt = str(b.get('text','') or '')[:80]
    bbox = b.get('bbox',[])
    print(f'  id={bid:3d} role={role:25s} text_len={len(txt):4d} bbox={bbox}')
    if txt:
        print(f'    [{txt}]')

print('\n=== PAGE 12 ===')
for b in p12:
    bid = b['block_id']
    role = b.get('role','?')
    txt = str(b.get('text','') or '')[:80]
    bbox = b.get('bbox',[])
    print(f'  id={bid:3d} role={role:25s} text_len={len(txt):4d} bbox={bbox}')
    if txt:
        print(f'    [{txt}]')
