#!/usr/bin/env bash
# J5: Progress bar — backend must emit OCR_RUN tokens

source "$(dirname "$0")/_lib.sh"

echo "=== J5: Progress bar — backend emits tokens ==="

# 1. ocr rebuild emits progress tokens
echo "--- Step 1: ocr rebuild emits OCR_REBUILD tokens ---"
assert "OCR_REBUILD_START emitted" '
    run_paperforge ocr rebuild 2BB8VM5W 2AGGSMVQ 2>&1 | grep -q "OCR_REBUILD_START"
'

echo "--- Step 2: OCR_REBUILD_PROGRESS emitted ---"
assert "OCR_REBUILD_PROGRESS emitted" '
    run_paperforge ocr rebuild 2BB8VM5W 2AGGSMVQ 2>&1 | grep -q "OCR_REBUILD_PROGRESS"
'

echo "--- Step 3: OCR_REBUILD_DONE emitted ---"
assert "OCR_REBUILD_DONE emitted" '
    run_paperforge ocr rebuild 2BB8VM5W 2AGGSMVQ 2>&1 | grep -q "OCR_REBUILD_DONE"
'

# 2. ocr redo emits REDO tokens (source check)
echo "--- Step 4: redo_papers_for_keys has progress callback wiring ---"
pyassert "redo has OCR_REDO tokens" '
import inspect
from paperforge.commands.ocr import _run_ocr_redo
src = inspect.getsource(_run_ocr_redo)
assert "OCR_REDO_START" in src, "missing OCR_REDO_START"
assert "OCR_REDO_PROGRESS" in src, "missing OCR_REDO_PROGRESS"
assert "OCR_REDO_DONE" in src, "missing OCR_REDO_DONE"
'

# 3. ocr run emits RUN tokens (EXPECTED TO FAIL — bug)
echo "--- Step 5: ocr run emits OCR_RUN tokens (EXPECTED FAIL — bug #101) ---"
pyassert "run_ocr has OCR_RUN tokens" '
import inspect
from paperforge.worker.ocr import run_ocr
src = inspect.getsource(run_ocr)
has_start = "OCR_RUN_START" in src
has_progress = "OCR_RUN_PROGRESS" in src
has_done = "OCR_RUN_DONE" in src
assert has_start, "OCR_RUN_START not found — progress bar stays at 0%"
assert has_progress, "OCR_RUN_PROGRESS not found"
assert has_done, "OCR_RUN_DONE not found"
'

# 4. Frontend progress-parser.ts knows all prefixes
echo "--- Step 6: progress-parser.ts has all OCR_ prefixes ---"
assert "progress-parser has OCR_RUN" '
    grep -q "OCR_RUN" paperforge/plugin/src/services/progress-parser.ts
'
assert "progress-parser has OCR_REBUILD" '
    grep -q "OCR_REBUILD" paperforge/plugin/src/services/progress-parser.ts
'
assert "progress-parser has OCR_REDO" '
    grep -q "OCR_REDO" paperforge/plugin/src/services/progress-parser.ts
'

# 5. Embed build emits progress
echo "--- Step 7: embed build emits EMBED tokens ---"
pyassert "embed build has EMBED token emission" '
import inspect
from paperforge.commands.embed import run as build_embed
src = inspect.getsource(build_embed)
assert "EMBED_START" in src, "EMBED_START not found"
assert "EMBED_DONE" in src, "EMBED_DONE not found"
'

summary
