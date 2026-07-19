import json, os

errs = []

# Check MANIFEST exists
manifest_path = 'fixtures/MANIFEST.json'
if not os.path.exists(manifest_path):
    errs.append('MANIFEST.json missing')
else:
    m = json.load(open(manifest_path, encoding='utf-8'))
    if 'fixtures' not in m:
        errs.append('MANIFEST.json missing fixtures array')
    else:
        paths = {f['path'] for f in m['fixtures']}
        required = [
            'zotero/orthopedic.json', 'zotero/empty.json', 'zotero/malformed.json',
            'zotero/absolute_paths.json', 'zotero/storage_prefix.json', 'zotero/bare_relative.json',
            'zotero/cjk_content.json', 'zotero/multi_attachment.json', 'zotero/no_pdf.json',
            'zotero/missing_keys.json',
            'pdf/generate_fixtures.py',
            'ocr/paddleocr_submit.json', 'ocr/paddleocr_poll_done.json', 'ocr/paddleocr_error.json',
        ]
        for r in required:
            if r not in paths:
                errs.append('MANIFEST missing fixture: ' + r)
        for f in m['fixtures']:
            for field in ['path', 'desc', 'used_by', 'generated']:
                if field not in f:
                    errs.append('Fixture ' + f.get('path', '?') + ' missing field: ' + field)

# Check each zotero fixture is valid JSON (except malformed)
zotero_dir = 'fixtures/zotero'
for fname in os.listdir(zotero_dir):
    fpath = os.path.join(zotero_dir, fname)
    if not fname.endswith('.json'):
        continue
    with open(fpath, encoding='utf-8') as f:
        content = f.read()
    if fname == 'malformed.json':
        try:
            json.loads(content)
            errs.append('malformed.json parsed as valid JSON (should fail)')
        except json.JSONDecodeError:
            pass
        continue
    if fname == 'empty.json':
        data = json.loads(content)
        if data != []:
            errs.append('empty.json should be []')
        continue
    data = json.loads(content)
    if 'items' not in data:
        errs.append(fname + ' missing items key')
    if 'collections' not in data:
        errs.append(fname + ' missing collections key')

zotero_count = sum(1 for f in os.listdir(zotero_dir) if f.endswith('.json'))
if zotero_count < 8:
    errs.append('Only ' + str(zotero_count) + ' zotero fixtures (need 8+)')

if errs:
    for e in errs:
        print('FAIL: ' + e)
    exit(1)
else:
    print('All Zotero fixture checks PASS')
    print('  ' + str(zotero_count) + ' JSON files in fixtures/zotero/')
