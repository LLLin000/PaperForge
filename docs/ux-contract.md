# UX Contract — Verifiable Workflow Specifications

> This document defines concrete, single-measurement step sequences for every PaperForge user workflow.
> Every step has a Trigger (what the user does), a Measurable Outcome (what we verify), and an Error Contract (how failure presents).
> Journey tests validate against this contract.

---

## Workflow 1: First-Time Installation

| Step ID | Trigger | Action | Measurable Outcome | Error Contract |
|---------|---------|--------|-------------------|----------------|
| W1-S1 | Run `paperforge setup --headless --vault /tmp/pf-test` | Vault selection / directory creation | `{vault}/paperforge.json` exists with valid JSON containing `system_dir`, `resources_dir`, `literature_dir` | Exit code != 0; stderr: "Failed to create vault directory" |
| W1-S2 | Setup writes config file | Config file generated | `{vault}/paperforge.json` keys: `version` (string), `system_dir` (string), `resources_dir` (string), `literature_dir` (string), `base_dir` (string) | Exit code != 0; stderr: "Failed to write paperforge.json" |
| W1-S3 | Setup writes .env with API token | Environment file created | `{vault}\System\PaperForge\.env` exists and contains line `PADDLEOCR_API_TOKEN=<non-empty>` | Exit code != 0; stderr: "Failed to create .env" |
| W1-S4 | Setup creates directory structure | Directory tree generated | Directories exist: `System/PaperForge/exports/`, `System/PaperForge/ocr/`, `System/PaperForge/indexes/`, `Resources/Literature/`, `Bases/`, `.opencode/skills/` | Exit code != 0; stderr: "Failed to create directory: {path}" |
| W1-S5 | User runs `paperforge sync` | First sync from BBT JSON | `paperforge sync` exits code 0; stdout contains "Created" or "Found" to indicate new items | Exit code != 0; stderr: "Error reading exports directory" |
| W1-S6 | Verify formal note created | First paper appears | `{vault}/Resources/Literature/{domain}/{key} - {title}.md` exists with frontmatter containing `zotero_key`, `domain`, `has_pdf`, `pdf_path` | No note created; stderr: "Failed to create formal note for {key}" |

---

## Workflow 2: Daily Sync

| Step ID | Trigger | Action | Measurable Outcome | Error Contract |
|---------|---------|--------|-------------------|----------------|
| W2-S1 | User adds paper in Zotero | Zotero entry created | Better BibTeX auto-exports updated JSON to `{vault}/System/PaperForge/exports/{collection}.json` with new item entry | N/A — outside PaperForge scope |
| W2-S2 | Better BibTeX auto-exports | JSON appears in exports/ | File `{vault}/System/PaperForge/exports/{collection}.json` is valid JSON with `items` array containing the new paper's object | N/A — Zotero/BBT handles export |
| W2-S3 | User runs `paperforge sync` | Sync processes new export | Exit code 0; stdout contains the new paper's title or key; log shows "Formal note created" or "1 new items" | Exit code != 0; stderr: "Sync failed" |
| W2-S4 | Verify new formal note | Formal note exists with correct state | New `.md` file found at `{vault}/Resources/Literature/{domain}/{key} - {title}.md`; frontmatter has `has_pdf: true`, `do_ocr: false`, `ocr_status: "pending"`, `analyze: false` | File not created; stderr shows error about missing key or title |

---

## Workflow 3: OCR Pipeline

| Step ID | Trigger | Action | Measurable Outcome | Error Contract |
|---------|---------|--------|-------------------|----------------|
| W3-S1 | User sets `do_ocr: true` in formal note frontmatter | OCR trigger flag | Formal note frontmatter contains `do_ocr: true`, `ocr_status: "pending"` | N/A — manual file edit |
| W3-S2 | User runs `paperforge ocr` | OCR job submitted | Exit code 0; stdout contains "Submitting" or "Processing" or job reference; `meta.json` created at `{vault}/System/PaperForge/ocr/{key}/meta.json` with `ocr_status: "processing"` | Exit code != 0; stderr: "OCR API authentication failed" or "Network error" |
| W3-S3 | Wait for OCR job to complete | Polling OCR status | `meta.json` shows `ocr_status: "done"`; `fulltext.md` exists in OCR output directory with text content | `ocr_status: "failed"`; stderr: "OCR job {id} did not complete" |
| W3-S4 | OCR artifacts extracted | Full text and figures available | `{vault}/System/PaperForge/ocr/{key}/fulltext.md` exists with >= 1 page; `{vault}/System/PaperForge/ocr/{key}/images/` exists with at least 1 image or empty | Missing artifacts; ocr_status: "failed" with error detail |
| W3-S5 | Formal note updated with OCR status | Frontmatter reflects OCR done | Formal note frontmatter `ocr_status` updated to `"done"`; `fulltext_md_path` references OCR fulltext file | `ocr_status` remains "pending" or "processing"; no error logged |

---

## Workflow 4: Dashboard View (Obsidian Plugin)

| Step ID | Trigger | Action | Measurable Outcome | Error Contract |
|---------|---------|--------|-------------------|----------------|
| W4-S1 | User opens Obsidian vault | Obsidian loads vault | Plugin view is registered; user navigates to `Bases/` directory and sees `.base` files rendered as interactive tables with filterable columns | Plugin not loaded; stderr in dev console shows "Failed to register PaperForge view" |
| W4-S2 | Base view renders with workflow-gate columns | Lifecycle columns visible | Base view displays columns: `has_pdf`, `do_ocr`, `analyze`, `ocr_status`, `deep_reading_status`. Each paper appears as one row with status values. Filter UI present for `do_ocr`, `analyze`, `ocr_status` | Missing columns; all values appear as empty or "N/A" |
| W4-S3 | Per-paper dashboard shows lifecycle stepper | Detailed view renders | Clicking a paper row reveals: lifecycle stepper (PENDING -> PROCESSING -> DONE), health matrix (pdf, ocr, metadata status), next-step recommendation badge; all components render without console errors | Lifecycle stepper missing; health matrix shows all red; recommendation badge absent |

---

## Assertion Library

Use these shell commands in journey tests to verify each step:

```bash
# W1-S1: Config file exists
test -f "{vault}/paperforge.json" && python -c "import json; json.load(open('{vault}/paperforge.json'))"

# W1-S3: .env exists with token
grep -q "PADDLEOCR_API_TOKEN" "{vault}/System/PaperForge/.env"

# W1-S4: Directory structure complete
test -d "{vault}/System/PaperForge/exports" && test -d "{vault}/Resources/Literature"

# W1-S6: Formal note created
test -f "{vault}/Resources/Literature/"{domain}/*.md

# W2-S4: Frontmatter fields present
python -c "
import yaml; m=open('{note_path}').read()
fm=yaml.safe_load(m.split('---')[1])
assert fm.get('has_pdf')==True
assert fm.get('ocr_status') in ('pending','done')
"

# W3-S5: OCR status updated in note frontmatter
python -c "
import yaml; m=open('{note_path}').read()
fm=yaml.safe_load(m.split('---')[1])
assert fm.get('ocr_status')=='done'
assert fm.get('fulltext_md_path','')!=''
"
```
