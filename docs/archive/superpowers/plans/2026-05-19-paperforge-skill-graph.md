# PaperForge Skill Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the PaperForge skill into a compound/molecule/atom layout, add capability-aware bootstrap data, split paper discovery from evidence retrieval, and preserve both concise JSONL capture and rich project reading-log markdown.

**Architecture:** Keep `paperforge/skills/paperforge/SKILL.md` as the single compound entrypoint. Introduce layered `molecules/` and `atoms/` directories, move retrieval and persistence guidance into atoms, and route all research workflows through intent-based molecules. Extend bootstrap with capability discovery while keeping `runtime-health` authoritative for runtime readiness.

**Tech Stack:** Markdown skill files, Python 3.11+, PaperForge CLI, pytest

---

## File Structure

### Files to Modify

- `paperforge/skills/paperforge/SKILL.md`
  - Rewrite as compound router with mechanical-command pre-routing, research aliases, intent routing, and post-action capture rules.
- `paperforge/skills/paperforge/scripts/pf_bootstrap.py`
  - Add a `capabilities` block without creating a second runtime authority.
- `AGENTS.md`
  - Update route examples to the new molecule paths.
- `tests/test_command_docs.py`
  - Update documentation path expectations for the new skill layout.
- `tests/test_setup_wizard.py`
  - Update packaging/path assertions that assume the old `workflows/` structure.

### Files to Create

- `paperforge/skills/paperforge/molecules/read-known-paper.md`
- `paperforge/skills/paperforge/molecules/discover-papers.md`
- `paperforge/skills/paperforge/molecules/find-supporting-evidence.md`
- `paperforge/skills/paperforge/molecules/deep-analyze-paper.md`
- `paperforge/skills/paperforge/molecules/capture-project-knowledge.md`
- `paperforge/skills/paperforge/atoms/clarify-user-intent.md`
- `paperforge/skills/paperforge/atoms/retrieval-routing.md`
- `paperforge/skills/paperforge/atoms/write-reading-log-jsonl.md`
- `paperforge/skills/paperforge/atoms/write-project-reading-log.md`
- `paperforge/skills/paperforge/atoms/write-project-log.md`
- `paperforge/skills/paperforge/atoms/extract-methodology-card.md`
- `tests/test_pf_bootstrap_capabilities.py`
- `tests/test_skill_graph_layout.py`
- `tests/test_skill_graph_contracts.py`

### Files to Move or Remove After Migration

- Replace or delete after migration:
  - `paperforge/skills/paperforge/workflows/paper-qa.md`
  - `paperforge/skills/paperforge/workflows/paper-search.md`
  - `paperforge/skills/paperforge/workflows/deep-reading.md`
  - `paperforge/skills/paperforge/workflows/reading-log.md`
  - `paperforge/skills/paperforge/workflows/project-log.md`
  - `paperforge/skills/paperforge/workflows/methodology.md`
- Move after deep-analysis migration is complete:
  - `paperforge/skills/paperforge/references/chart-reading/*` -> `paperforge/skills/paperforge/atoms/chart-reading/*`

### Files Left As-Is

- `paperforge/skills/paperforge/scripts/pf_deep.py`
- `paperforge/skills/paperforge/workflows/project-engineering.md`
  - This remains outside the literature intent graph in this phase.

---

### Task 1: Add Bootstrap Capability Contract

**Files:**
- Modify: `paperforge/skills/paperforge/scripts/pf_bootstrap.py`
- Test: `tests/test_pf_bootstrap_capabilities.py`

- [ ] **Step 1: Write the failing bootstrap capability test**

Create `tests/test_pf_bootstrap_capabilities.py` with focused assertions such as:

```python
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_bootstrap_outputs_capabilities_block(tmp_path: Path) -> None:
    vault = tmp_path
    (vault / "paperforge.json").write_text("{}", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "paperforge/skills/paperforge/scripts/pf_bootstrap.py",
            "--vault",
            str(vault),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(result.stdout)
    assert set(payload["capabilities"]) >= {
        "rg",
        "metadata_search",
        "paper_context",
        "semantic_enabled",
        "semantic_ready",
    }
```

- [ ] **Step 2: Run the test and verify failure**

Run: `python -m pytest tests/test_pf_bootstrap_capabilities.py -v --tb=short`

Expected: FAIL because `capabilities` does not exist yet.

- [ ] **Step 3: Implement minimal capability discovery**

Extend `pf_bootstrap.py` to:

1. detect `rg` with a subprocess probe
2. set `metadata_search=True` and `paper_context=True`
3. derive `semantic_enabled` from existing vector-enable configuration
4. derive `semantic_ready` conservatively from the same runtime truth source semantics the skill already relies on

Do not create a second independent readiness model.

- [ ] **Step 4: Re-run the test and verify pass**

Run: `python -m pytest tests/test_pf_bootstrap_capabilities.py -v --tb=short`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/skills/paperforge/scripts/pf_bootstrap.py tests/test_pf_bootstrap_capabilities.py
git commit -m "feat(skill): add bootstrap capability contract"
```

---

### Task 2: Create Layered Directories

**Files:**
- Create: `paperforge/skills/paperforge/molecules/`
- Create: `paperforge/skills/paperforge/atoms/`
- Create: `paperforge/skills/paperforge/atoms/chart-reading/`
- Test: `tests/test_skill_graph_layout.py`

- [ ] **Step 1: Write the failing layout test**

Create `tests/test_skill_graph_layout.py`:

```python
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = REPO_ROOT / "paperforge" / "skills" / "paperforge"


def test_skill_uses_atoms_and_molecules_directories() -> None:
    assert (SKILL_ROOT / "atoms").is_dir()
    assert (SKILL_ROOT / "molecules").is_dir()


def test_chart_reading_target_directory_exists() -> None:
    assert (SKILL_ROOT / "atoms" / "chart-reading").is_dir()
```

- [ ] **Step 2: Run the test and verify failure**

Run: `python -m pytest tests/test_skill_graph_layout.py -v --tb=short`

Expected: FAIL because the new directories do not exist yet.

- [ ] **Step 3: Create the new directories only**

Create the target directories, but do not move any existing files yet.

- [ ] **Step 4: Re-run the test and verify pass**

Run: `python -m pytest tests/test_skill_graph_layout.py -v --tb=short`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/skills/paperforge/atoms paperforge/skills/paperforge/molecules tests/test_skill_graph_layout.py
git commit -m "refactor(skill): add atoms and molecules directories"
```

---

### Task 3: Add Skill Contract Tests

**Files:**
- Create: `tests/test_skill_graph_contracts.py`

- [ ] **Step 1: Write failing contract tests for compound routing**

Add assertions for:

1. mechanical command pre-routing
2. research command aliases (`/pf-deep`, `/pf-paper`)
3. primary intent + post-action wording

- [ ] **Step 2: Write failing contract tests for atoms**

Add assertions for:

1. `clarify-user-intent.md` has the fixed question pattern
2. `clarify-user-intent.md` enforces a two-round maximum
3. `retrieval-routing.md` includes the fallback ladder and candidate limits

- [ ] **Step 3: Write failing contract tests for molecule output shapes**

Add assertions for:

1. `discover-papers.md` returns candidate paper lists
2. `find-supporting-evidence.md` returns grouped evidence hits/snippets

- [ ] **Step 4: Run the tests and verify failure**

Run: `python -m pytest tests/test_skill_graph_contracts.py -v --tb=short`

Expected: FAIL because the new files/contracts do not exist yet.

- [ ] **Step 5: Commit**

```bash
git add tests/test_skill_graph_contracts.py
git commit -m "test(skill): add skill graph contract tests"
```

---

### Task 4: Create Shell Molecule and Atom Files

**Files:**
- Create all new molecule and atom markdown files listed in the File Structure section

- [ ] **Step 1: Create empty shells for the five molecule files**

Add title + one-line responsibility only.

- [ ] **Step 2: Create empty shells for these four persistence atom files**

1. `write-reading-log-jsonl.md`
2. `write-project-reading-log.md`
3. `write-project-log.md`
4. `extract-methodology-card.md`

Add title + one-line responsibility only.

- [ ] **Step 3: Create shells for the two routing atoms**

1. `clarify-user-intent.md`
2. `retrieval-routing.md`

These are the two atom files the compound will reference first.

- [ ] **Step 4: Commit**

```bash
git add paperforge/skills/paperforge/molecules paperforge/skills/paperforge/atoms
git commit -m "chore(skill): scaffold molecule and atom files"
```

---

### Task 5: Rewrite SKILL.md as the Compound Router

**Files:**
- Modify: `paperforge/skills/paperforge/SKILL.md`

- [ ] **Step 1: Rewrite the frontmatter and summary**

Reflect the new layered structure and command split.

- [ ] **Step 2: Rewrite the routing section**

Encode:

1. mechanical pre-routing: `/pf-sync`, `/pf-ocr`, `/pf-status`
2. research aliases: `/pf-deep`, `/pf-paper`
3. top-level research intents
4. clarify-user-intent fallback
5. primary intent + post-action model

- [ ] **Step 3: Rewrite the file structure section**

Point to `molecules/` and `atoms/`, not `workflows/` and `references/`.

- [ ] **Step 4: Re-run the contract tests**

Run: `python -m pytest tests/test_skill_graph_contracts.py -v --tb=short`

Expected: still FAIL overall, but `SKILL.md`-related assertions should now pass.

- [ ] **Step 5: Commit**

```bash
git add paperforge/skills/paperforge/SKILL.md
git commit -m "refactor(skill): rewrite compound router for skill graph"
```

---

### Task 6: Implement the Clarify Intent Atom

**Files:**
- Modify: `paperforge/skills/paperforge/atoms/clarify-user-intent.md`

- [ ] **Step 1: Add trigger conditions**

Document:

1. short/ambiguous input
2. multi-intent collisions
3. missing object
4. unresolved `这篇`

- [ ] **Step 2: Add the fixed question pattern**

Use the approved constrained explanation of what PaperForge can do.

- [ ] **Step 3: Add the two-round maximum rule**

Make it explicit and testable.

- [ ] **Step 4: Re-run the contract tests**

Run: `python -m pytest tests/test_skill_graph_contracts.py -v --tb=short`

Expected: clarify atom assertions pass.

- [ ] **Step 5: Commit**

```bash
git add paperforge/skills/paperforge/atoms/clarify-user-intent.md
git commit -m "feat(skill): add clarify-user-intent atom"
```

---

### Task 7: Implement the Retrieval Routing Atom

**Files:**
- Modify: `paperforge/skills/paperforge/atoms/retrieval-routing.md`

- [ ] **Step 1: Add the authority rules**

State:

1. bootstrap is convenience discovery
2. `runtime-health` is runtime authority
3. semantic is optional and supplementary

- [ ] **Step 2: Add the fallback ladder**

Document:

1. metadata candidate generation
2. OCR/fulltext narrowing
3. `rg` over resolved fulltext
4. `grep`/`findstr`/CLI fallback
5. snippet verification with paper-context
6. explicit degradation to metadata-only support when no OCR/fulltext exists for any candidate

- [ ] **Step 3: Add recommended limits**

Document the top-10-20 candidate set and top-3-5 verification scope.

- [ ] **Step 4: Add the `rg` installation/degradation rule**

Document that the agent may try an environment-appropriate install path, but must degrade safely if installation is not practical.

- [ ] **Step 5: Re-run the contract tests**

Run: `python -m pytest tests/test_skill_graph_contracts.py -v --tb=short`

Expected: retrieval-routing assertions pass.

- [ ] **Step 6: Commit**

```bash
git add paperforge/skills/paperforge/atoms/retrieval-routing.md
git commit -m "feat(skill): add retrieval-routing atom"
```

---

### Task 8: Split Search into Two Molecules

**Files:**
- Modify: `paperforge/skills/paperforge/molecules/discover-papers.md`
- Modify: `paperforge/skills/paperforge/molecules/find-supporting-evidence.md`

- [ ] **Step 1: Implement `discover-papers.md`**

Document:

1. metadata-first paper discovery
2. paper candidate list output with concrete fields:
   - `zotero_key`
   - `title`
   - `first_author`
   - `year`
   - `domain`
   - readiness state (`ocr_status`, `deep_reading_status` or equivalent)
3. top-hit enrichment with paper-context
4. transitions to read/deep/refine

- [ ] **Step 2: Implement `find-supporting-evidence.md`**

Document:

1. evidence-oriented request handling
2. use of `retrieval-routing.md`
3. grouped evidence hit output with concrete fields:
   - paper identity (`zotero_key`, title)
   - section or page reference
   - matched snippet
   - short context
4. transitions to capture or single-paper deepening
5. explicit metadata-only degradation message when exact verification is impossible due to missing OCR/fulltext

- [ ] **Step 3: Re-run the contract tests**

Run: `python -m pytest tests/test_skill_graph_contracts.py -v --tb=short`

Expected: output-shape assertions pass.

- [ ] **Step 4: Commit**

```bash
git add paperforge/skills/paperforge/molecules/discover-papers.md paperforge/skills/paperforge/molecules/find-supporting-evidence.md
git commit -m "refactor(skill): split discovery and evidence molecules"
```

---

### Task 9: Migrate Single-Paper and Deep-Read Molecules

**Files:**
- Modify: `paperforge/skills/paperforge/molecules/read-known-paper.md`
- Modify: `paperforge/skills/paperforge/molecules/deep-analyze-paper.md`

- [ ] **Step 1: Implement `read-known-paper.md` from current `paper-qa.md`**

Retain resolution + Q&A behavior and add capture handoff wording.

- [ ] **Step 2: Implement `deep-analyze-paper.md` from current `deep-reading.md`**

Retain prepare / pass / postprocess / validate flow and add capture handoff wording.

- [ ] **Step 3: Commit**

```bash
git add paperforge/skills/paperforge/molecules/read-known-paper.md paperforge/skills/paperforge/molecules/deep-analyze-paper.md
git commit -m "refactor(skill): migrate single-paper and deep-read molecules"
```

---

### Task 10: Implement the Capture Project Knowledge Molecule and Atoms

**Files:**
- Modify: `paperforge/skills/paperforge/molecules/capture-project-knowledge.md`
- Modify: `paperforge/skills/paperforge/atoms/write-reading-log-jsonl.md`
- Modify: `paperforge/skills/paperforge/atoms/write-project-reading-log.md`
- Modify: `paperforge/skills/paperforge/atoms/write-project-log.md`
- Modify: `paperforge/skills/paperforge/atoms/extract-methodology-card.md`

- [ ] **Step 1: Implement `capture-project-knowledge.md`**

Document the direct-intent and post-action modes.

- [ ] **Step 2: Implement `write-reading-log-jsonl.md`**

Make the concise per-paper JSONL role explicit.

- [ ] **Step 3: Implement `write-project-reading-log.md`**

Make the direct-write markdown rule explicit.

- [ ] **Step 4: Implement `write-project-log.md`**

Document only project-log persistence behavior.

- [ ] **Step 5: Implement `extract-methodology-card.md`**

Document only methodology extraction behavior.

- [ ] **Step 6: Commit**

```bash
git add paperforge/skills/paperforge/molecules/capture-project-knowledge.md paperforge/skills/paperforge/atoms/write-reading-log-jsonl.md paperforge/skills/paperforge/atoms/write-project-reading-log.md paperforge/skills/paperforge/atoms/write-project-log.md paperforge/skills/paperforge/atoms/extract-methodology-card.md
git commit -m "feat(skill): add capture-project-knowledge molecule and atoms"
```

---

### Task 11: Move Chart-Reading Into the Atom Layer

**Files:**
- Move: `paperforge/skills/paperforge/references/chart-reading/*` -> `paperforge/skills/paperforge/atoms/chart-reading/*`
- Modify: `paperforge/skills/paperforge/molecules/deep-analyze-paper.md`

- [ ] **Step 1: Update `deep-analyze-paper.md` to the new chart-reading path**

Replace active references to `references/chart-reading` with `atoms/chart-reading`.

- [ ] **Step 2: Move the chart-reading files**

Move files only after the molecule text is updated.

- [ ] **Step 3: Verify no active skill file still points at the old chart-reading path**

Run a repo search scoped to `paperforge/skills/paperforge/`.

- [ ] **Step 4: Commit**

```bash
git add paperforge/skills/paperforge/atoms/chart-reading paperforge/skills/paperforge/molecules/deep-analyze-paper.md
git commit -m "refactor(skill): move chart-reading into atom layer"
```

---

### Task 12: Update Downstream Docs and Packaging Assumptions

**Files:**
- Modify: `AGENTS.md`
- Modify: `tests/test_command_docs.py`
- Modify: `tests/test_setup_wizard.py`

- [ ] **Step 1: Update `AGENTS.md` route examples**

Point `/pf-deep` and `/pf-paper` at the new molecule paths.

- [ ] **Step 2: Update `tests/test_command_docs.py`**

Change assertions that assume old workflow paths.

- [ ] **Step 3: Update `tests/test_setup_wizard.py`**

Adjust setup/package assertions to the new layered skill tree.

- [ ] **Step 4: Run the downstream tests**

Run: `python -m pytest tests/test_command_docs.py tests/test_setup_wizard.py -v --tb=short`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md tests/test_command_docs.py tests/test_setup_wizard.py
git commit -m "test(skill): align downstream docs and setup with layered skill tree"
```

---

### Task 13: Remove Legacy Literature Workflow Entry Points

**Files:**
- Delete or stub:
  - `paperforge/skills/paperforge/workflows/paper-qa.md`
  - `paperforge/skills/paperforge/workflows/paper-search.md`
  - `paperforge/skills/paperforge/workflows/deep-reading.md`
  - `paperforge/skills/paperforge/workflows/reading-log.md`
  - `paperforge/skills/paperforge/workflows/project-log.md`
  - `paperforge/skills/paperforge/workflows/methodology.md`

- [ ] **Step 1: Confirm all new files are live in `SKILL.md`**

Do not remove legacy files until the compound points to the new layout.

- [ ] **Step 2: Remove or stub the old literature workflow files**

Choose deletion or short deprecation stubs based on packaging needs.

- [ ] **Step 3: Search for live references to the removed files**

Search for:

- `workflows/paper-qa.md`
- `workflows/paper-search.md`
- `workflows/deep-reading.md`
- `workflows/reading-log.md`
- `workflows/project-log.md`
- `workflows/methodology.md`

Expected: no active references remain outside historical docs/plans.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor(skill): remove legacy literature workflow entrypoints"
```

---

### Task 14: Run Focused Verification

**Files:**
- Test only

- [ ] **Step 1: Run bootstrap capability tests**

Run: `python -m pytest tests/test_pf_bootstrap_capabilities.py -v --tb=short`

Expected: PASS

- [ ] **Step 2: Run skill layout tests**

Run: `python -m pytest tests/test_skill_graph_layout.py -v --tb=short`

Expected: PASS

- [ ] **Step 3: Run skill contract tests**

Run: `python -m pytest tests/test_skill_graph_contracts.py -v --tb=short`

Expected: PASS

- [ ] **Step 4: Run downstream doc/setup tests**

Run: `python -m pytest tests/test_command_docs.py tests/test_setup_wizard.py -v --tb=short`

Expected: PASS

- [ ] **Step 5: Run existing deep-reading regression tests**

Run: `python -m pytest tests/test_ld_deep_postprocess.py tests/test_ld_deep_skel.py -v --tb=short`

Expected: PASS

- [ ] **Step 6: Manual review of routing-critical files**

Read these one at a time:

1. `paperforge/skills/paperforge/SKILL.md`
2. `paperforge/skills/paperforge/atoms/clarify-user-intent.md`
3. `paperforge/skills/paperforge/atoms/retrieval-routing.md`
4. `paperforge/skills/paperforge/molecules/discover-papers.md`
5. `paperforge/skills/paperforge/molecules/find-supporting-evidence.md`

Checklist:

1. mechanical routing is explicit
2. aliases are explicit
3. `rg` fallback is explicit
4. vector is supplementary only
5. output contracts are explicit

- [ ] **Step 7: Manual review of capture files**

Read these one at a time:

1. `paperforge/skills/paperforge/molecules/capture-project-knowledge.md`
2. `paperforge/skills/paperforge/atoms/write-reading-log-jsonl.md`
3. `paperforge/skills/paperforge/atoms/write-project-reading-log.md`
4. `paperforge/skills/paperforge/atoms/write-project-log.md`
5. `paperforge/skills/paperforge/atoms/extract-methodology-card.md`

Checklist:

1. JSONL is concise/per-paper
2. project reading-log markdown is rich/direct-write
3. no file says markdown is rendered from JSONL

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "chore(skill): verify paperforge skill graph migration"
```

---

## Rollback Plan

If the new layout causes routing confusion or breaks skill discovery:

1. restore the old `workflows/` files from git history
2. revert `SKILL.md` to the previous stable contract
3. keep the bootstrap capability contract only if it proves independently useful

If the dual knowledge capture model proves too confusing:

1. keep `reading-log.jsonl` behavior unchanged
2. defer `write-project-reading-log.md` usage guidance to a later phase

## Risks to Watch

1. `SKILL.md` may still bloat if retrieval detail leaks upward.
2. The distinction between `discover-papers` and `find-supporting-evidence` must stay crisp or routing will drift.
3. Agents may still overuse semantic retrieval unless the atom wording is strict.
4. Downstream docs/tests may continue to assume the old `workflows/` layout if repo-wide cleanup misses references.
