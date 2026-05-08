import json, os, sys
from pathlib import Path

errs = []

# Check snapshot files exist
snap_dir = 'fixtures/snapshots'
snapshots = [
    ('paths_json/default_config.json', json),
    ('status_json/empty_vault.json', json),
    ('index_json/after_sync.json', json),
]
for rel_path, parser in snapshots:
    fpath = os.path.join(snap_dir, rel_path)
    if not os.path.exists(fpath):
        errs.append('Missing snapshot: ' + rel_path)
    else:
        data = parser.load(open(fpath, encoding='utf-8'))
        if not isinstance(data, dict):
            errs.append('Snapshot ' + rel_path + ' should be a JSON object')

# Check vault_builder.py exists and is valid Python
vb_path = 'fixtures/vault_builder.py'
if not os.path.exists(vb_path):
    errs.append('Missing vault_builder.py')
else:
    import py_compile
    try:
        py_compile.compile(vb_path, doraise=True)
    except py_compile.PyCompileError as e:
        errs.append('vault_builder.py syntax error: ' + str(e))

# Check formal note frontmatter snapshot
yaml_path = os.path.join(snap_dir, 'formal_note_frontmatter/orthopedic_article.yaml')
if not os.path.exists(yaml_path):
    errs.append('Missing formal_note_frontmatter snapshot')

# Quick integration: import VaultBuilder and build a minimal vault
try:
    sys.path.insert(0, 'fixtures')
    from vault_builder import VaultBuilder
    builder = VaultBuilder()
    vault = builder.build('minimal')
    assert vault.exists(), 'Vault not created'
    assert (vault / 'paperforge.json').exists(), 'paperforge.json missing'
    assert (vault / 'System/PaperForge/.env').exists(), '.env missing'
    assert (vault / 'Resources/Literature').exists(), 'Literature dir missing'

    # Build standard vault
    vault2 = builder.build('standard')
    exports = list((vault2 / 'System/PaperForge/exports').glob('*.json'))
    print('  Standard vault: ' + str(len(exports)) + ' export files')

    print('  VaultBuilder integration: PASS')
except Exception as e:
    errs.append('VaultBuilder integration failed: ' + str(e))

import shutil
# Clean up test vaults created by this verification
for p in [vault, vault2]:
    try:
        if p.exists():
            shutil.rmtree(str(p), ignore_errors=True)
    except:
        pass

if errs:
    for e in errs:
        print('FAIL: ' + e)
    exit(1)
else:
    print('All snapshot and vault builder checks PASS')
