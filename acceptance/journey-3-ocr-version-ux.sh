#!/usr/bin/env bash
# J3: OCR Settings — see status → "Update Available" → Re-extract → Ready

source "$(dirname "$0")/_lib.sh"

echo "=== J3: OCR Settings version detection and rebuild ==="

# 1. Probe returns pipeline_version
echo "--- Step 1: probe returns pipeline version 2.0.0 ---"
pyassert "pipeline_version is 2.0.0" '
import sys
from paperforge.commands.probe import probe_ocr
from pathlib import Path
r = probe_ocr(Path(sys.argv[1]))
assert r["pipeline_version"] == "2.0.0", "got %s" % r.get("pipeline_version")
' "$VAULT"

# 2. When all papers current, stale=0 -> Ready
echo "--- Step 2: all papers on current → stale=0 → Ready state ---"
pyassert "probe shows Ready state" '
import sys
from paperforge.commands.probe import probe_ocr
from pathlib import Path
r = probe_ocr(Path(sys.argv[1]))
assert r.get("capability_state") == "ready", "got %s" % r.get("capability_state")
s = r.get("pipeline_version_summary", {})
assert s.get("stale") == 0, "stale=%d" % s.get("stale", -1)
' "$VAULT"

# 3. Every paper meta.json has ocr_pipeline_version
echo "--- Step 3: all paper meta.json have ocr_pipeline_version ---"
pyassert "all papers have ocr_pipeline_version" '
import json, sys
from pathlib import Path
ocr_root = Path(sys.argv[1]) / "System/PaperForge/ocr"
missing = []
for meta_path in sorted(ocr_root.rglob("meta.json")):
    meta = json.load(open(meta_path))
    if meta.get("ocr_status") in ("done", "done_degraded"):
        ver = meta.get("ocr_pipeline_version")
        if ver != "2.0.0":
            missing.append("%s: %s" % (meta_path.parent.name, ver))
assert not missing, "missing: %s" % missing
' "$VAULT"

# 4. Per-paper version array consistent with summary
echo "--- Step 4: per-paper version array matches summary ---"
pyassert "per-paper versions are consistent" '
import sys
from paperforge.commands.probe import probe_ocr
from pathlib import Path
r = probe_ocr(Path(sys.argv[1]))
s = r.get("pipeline_version_summary", {})
per_paper = r.get("per_paper_pipeline_version", [])
on_current = [p for p in per_paper if p.get("last_pipeline_version") == "2.0.0"]
assert len(on_current) == s.get("on_current", 0), "%d vs summary %d" % (len(on_current), s.get("on_current", 0))
' "$VAULT"

# 5. capability_state never shows update_available when stale=0
echo "--- Step 5: capability_state reflects actual state ---"
pyassert "capability_state is ready when stale=0" '
import sys
from paperforge.commands.probe import probe_ocr
from pathlib import Path
r = probe_ocr(Path(sys.argv[1]))
if r["pipeline_version_summary"]["stale"] == 0:
    assert r["capability_state"] == "ready", "stale=0 but capability_state=%s" % r["capability_state"]
' "$VAULT"

summary
