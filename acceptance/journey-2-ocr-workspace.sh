#!/usr/bin/env bash
# J2: OCR Workspace — select paper → Process → see result

source "$(dirname "$0")/_lib.sh"

echo "=== J2: OCR Workspace closed loop ==="

# 1. CLI accepts per-paper keys
echo "--- Step 1: ocr run accepts specific key ---"
assert "ocr run with key accepted" \
    'run_paperforge ocr run 2BB8VM5W 2>&1 | grep -q "Processing specific keys"'

# 2. meta.json has version and status
echo "--- Step 2: meta.json has pipeline version and done status ---"
pyassert "ocr_pipeline_version is 2.0.0" '
import json, sys
from pathlib import Path
meta = json.load(open(Path(sys.argv[1])))
assert meta.get("ocr_pipeline_version") == "2.0.0", "got %s" % meta.get("ocr_pipeline_version")
assert meta.get("ocr_status") in ("done", "done_degraded"), "got %s" % meta.get("ocr_status")
' "$VAULT/System/PaperForge/ocr/2BB8VM5W/meta.json"

# 3. Probe returns stale=0
echo "--- Step 3: probe shows all papers on current version ---"
pyassert "stale count is 0" '
import sys
from paperforge.commands.probe import probe_ocr
from pathlib import Path
r = probe_ocr(Path(sys.argv[1]))
s = r["pipeline_version_summary"]
assert s["stale"] == 0, "stale=%d expected 0" % s["stale"]
' "$VAULT"

# 4. formal-library.json has the paper
echo "--- Step 4: formal-library.json includes this paper ---"
pyassert "paper 2BB8VM5W in index" '
import json, sys
from pathlib import Path
idx = json.load(open(Path(sys.argv[1]) / "System/PaperForge/indexes/formal-library.json"))
keys = [item["zotero_key"] for item in idx.get("items", [])]
assert "2BB8VM5W" in keys, "not found in %d items" % len(keys)
' "$VAULT"

# 5. Probe returns ready state (not update_available)
echo "--- Step 5: probe returns ready capability state ---"
pyassert "capability_state is ready" '
import sys
from paperforge.commands.probe import probe_ocr
from pathlib import Path
r = probe_ocr(Path(sys.argv[1]))
assert r.get("capability_state") == "ready", "got %s" % r.get("capability_state")
' "$VAULT"

summary
