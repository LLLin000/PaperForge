# Domain Pitfalls — v2.0 Multi-Layer Testing Infrastructure

**Domain:** Brownfield hybrid Python + Obsidian plugin project — adding 6-layer quality gate testing (version sync, Python unit, CLI contract, plugin-backend integration, temp vault E2E, user journey, destructive scenarios)
**Researched:** 2026-05-08
**Confidence:** HIGH

---

## Critical Pitfalls

### Pitfall 1: Mocking External Services Too Early and Too Rigidly

**What goes wrong:**
Tests mock `requests.post()` to PaddleOCR, `load_export_rows()` for BBT JSON, and `requests.get()` for OCR poll results with `MagicMock(return_value=...)`. The mocks are so tightly coupled to the current implementation that:
1. A refactoring that changes how `requests.post()` is called (e.g., adding a header, changing URL) breaks 30+ tests even though the external service contract hasn't changed.
2. The mocks silently drift from the real API — the real PaddleOCR API returns `{"data": {"jobId": "..."}}` but the mock returns `{"data": {"job_id": "..."}}` and nobody notices until integration testing.
3. Tests pass with mocked data that would never occur in production (e.g., PDF paths that the resolver can't actually resolve, abstracts in formats that BBT doesn't export).

**Why it happens:**
The existing pattern in `test_ocr_state_machine.py` already demonstrates 12+ layers of nested `with patch(...):` contexts (see lines 129-159, 242-267, 336-361). Each patch is a MagicMock returning synthetic dicts that match the current function call graph exactly. The mocks are created ad-hoc in tests rather than from a shared contract definition, so every developer adds their own slightly different mock shape.

**How to avoid:**
- **Define mock response fixtures from real snapshots first.** Before writing any test that mocks PaddleOCR, capture a real API response once and save it as `tests/fixtures/paddleocr-response-done.json`. Construct mocks from this real data, not from guessing the API shape.
- **Use autospec=True on all MagicMock patches** to prevent method signature drift:
  ```python
  # BAD: mock = MagicMock() — silently accepts any call signature
  # GOOD: from unittest.mock import create_autospec
  #        mock = create_autospec(requests.Session)
  with patch("paperforge.worker.ocr.requests.post", autospec=True) as mock_post:
  ```
- **Limit patch nesting depth to 3 max.** The current 12-level nesting (test_ocr_state_machine.py lines 129-159) is impossible to debug. Introduce a fixture that returns a pre-configured mock environment:
  ```python
  @pytest.fixture
  def ocr_mocks(ocr_paths):
      """Set up all OCR mocks from fixture data."""
      with (
          patch("paperforge.worker.ocr.pipeline_paths", return_value=ocr_paths),
          patch("paperforge.worker.ocr.load_control_actions") as lca,
          patch("paperforge.worker.ocr.load_export_rows") as ler,
          patch("paperforge.worker.ocr.sync_ocr_queue") as sq,
          patch("paperforge.worker.ocr.requests.post", autospec=True) as post,
      ):
          lca.return_value = {KEY: {"do_ocr": True}}
          ler.return_value = FIXTURE_EXPORT_ROWS
          sq.return_value = FIXTURE_QUEUE_ROWS
          post.return_value.json.return_value = {"data": {"jobId": "fixture-job"}}
          yield
  ```
- **Introduce a VCR.py layer for OCR polling.** Record real polling sequences once, replay them in tests. This catches API contract drift the moment PaddleOCR changes its response shape.

**Warning signs:**
- Tests pass locally but fail in CI because mock shapes differ from real API
- A 3-line production change breaks 50+ test assertions
- "This test hasn't been run against real data in 6 months" realization during a bug hunt
- `MagicMock` names appearing in test failure output instead of meaningful data

**Phase to address:** Phase 2 (Python unit tests) — establish mock response fixtures from real API captures before writing OCR unit tests. Phase 4 (Temp vault E2E) validates mock assumptions against real subprocess runs.

---

### Pitfall 2: CI Matrix Combinatorial Explosion Killing Feedback Loops

**What goes wrong:**
The CI matrix is defined as: `os: [windows, macos, ubuntu] x python: [3.10, 3.11, 3.12] x node: [18, 20]` = 3 x 3 x 2 = 18 jobs. Each job runs the full test suite (Levels 0-6). At 15 minutes per job, the full matrix takes 4.5 hours wall-clock. Developers wait all day for CI results, or worse, push 10 commits in parallel and burn 45 hours of CI credits in a morning.

**Why it happens:**
The natural instinct is "test everything on every platform." But the actual risk profile is not uniform:
- Version sync checker (Level 0): same everywhere — needs 1 platform, 1 Python
- Python unit tests (Level 1): only OS-dependent where path handling differs — Windows path vs POSIX
- CLI --json contract tests (Level 2): OS-independent for JSON output shape
- Plugin-backend integration (Level 3): Node version matters, Python version doesn't
- Temp vault E2E (Level 4): Windows-specific for junction testing, generic for others
- Destructive tests (Level 6): must never run on CI machines shared by other projects

**How to avoid:**
- **Use a smart partitioning strategy, not a full cross-product:**

| Test Level | CI Trigger | OS | Python | Node | Runs |
|------------|-----------|-----|--------|------|------|
| L0: Version sync | Every push | ubuntu-only | latest only | N/A | 1 min |
| L1: Python unit | Every push | ubuntu (path-sensitive: 3 OS) | all 3 | N/A | 3 min |
| L2: CLI contract | Every push | ubuntu-only | latest only | N/A | 1 min |
| L3: Plugin integration | PR + main | ubuntu-only | latest | both | 5 min |
| L4: Temp vault E2E | PR + main | all 3 | latest on each | latest | 10 min |
| L5: User journey | Nightly + main | ubuntu-only | latest | latest | 15 min |
| L6: Destructive | Nightly only | ubuntu-only (Docker) | latest | latest | 10 min |

- **Never run the full matrix on every push.** Use GitHub Actions path filters to run only relevant levels:
  ```yaml
  on:
    push:
      paths:
        - "paperforge/worker/ocr.py"  # triggers L1+L2+L4
        - "paperforge/plugin/main.js"  # triggers L3
        - ".github/workflows/*.yml"    # triggers full audit
  ```
- **Introduce `pytest -m "not slow"` for push-time tests** and `pytest -m "slow"` for nightly. Mark tests explicitly:
  ```python
  @pytest.mark.slow  # Temp vault creation + full sync
  def test_full_pipeline_consistency(test_vault):
      ...
  ```
- **Use `pytest-xdist` with `-n auto`** for Level 1 and Level 2 only (unit tests parallelize well; E2E tests do not).
- **Set a hard CI budget (max 20 concurrent runners).** If the matrix exceeds 20 jobs, reduce granularity until it fits.

**Warning signs:**
- CI pipeline takes longer than developer lunch break
- PRs accumulate because "waiting for CI" is the bottleneck
- CI bill spikes (or free-tier minutes exhausted mid-month)
- Developers skip CI because "it's too slow" and merge without checks
- CI dashboard shows 12/18 jobs green but the 6 red ones are from timeouts, not failures

**Phase to address:** Phase 7 (CI expansion) — design the CI matrix strategy BEFORE writing `ci.yml`. Must include `pyproject.toml` markers and path filters.

---

### Pitfall 3: Snapshot Tests Breaking on Every Refactor

**What goes wrong:**
A golden dataset snapshot of `formal-library.json` is stored at `tests/fixtures/snapshots/formal-library-v2.json`. Every test that writes a formal note, updates an index, or changes frontmatter fields is asserted against this exact file. When a developer:
1. Adds a new frontmatter field (like `impact_factor`)
2. Changes the index envelope format from `{"version": "2"}` to `{"schema_version": "2", "generated_at": "...", "items": [...]}`
3. Adds a new CLI `--json` key (like `total_ocr_done`)

...every snapshot test fails. Not because the change is wrong, but because the snapshot is too broad. The developer must regenerate ALL snapshots with `--snapshot-update`, but now the review diff is thousands of lines of JSON and nobody actually reviews it. Regressions slip through because "I regenerated the snapshots" becomes the default response.

**Why it happens:**
Snapshot testing encourages the "assert everything" mindset: one snapshot assertion per test file, checking a complete output blob. This is particularly tempting for JSON outputs where every key seems important. The project has structured JSON outputs (formal-library.json, paper-meta.json, ocr-queue.json, CLI --json output) and generated markdown files — all natural targets for whole-file snapshots.

**How to avoid:**
- **Never snapshot whole files. Always snapshot specific shapes within files.** Instead of:
  ```python
  # BAD: entire index file
  assert json.loads(index_path.read_text()) == snapshot
  ```
  Do:
  ```python
  # GOOD: specific structural assertions
  index = json.loads(index_path.read_text())
  assert index["schema_version"] == "2"
  assert "generated_at" in index  # check presence, not exact value (timestamps)
  assert len(index["items"]) == 1
  assert index["items"][0]["zotero_key"] == "TSTONE001"
  assert index["items"][0]["has_pdf"] == True
  ```

- **Normalize dynamic fields before snapshotting.** Timestamps, mtimes, UUIDs, generated paths change every run. Strip them before passing to snapshot:
  ```python
  def normalize_index(raw: str) -> dict:
      data = json.loads(raw)
      data.pop("generated_at", None)
      for item in data.get("items", []):
          item.pop("last_updated", None)
      return data
  
  assert normalize_index(index_path.read_text()) == snapshot
  ```

- **Use `inline-snapshot` (pydantic's library) instead of external `.ambr` files.** Inline snapshots are co-located with the test, making it obvious when a snapshot update is needed and what changed:
  ```python
  from inline_snapshot import snapshot
  
  def test_index_keys():
      assert get_index_keys() == snapshot(["zotero_key", "title", "year", "doi"])
  ```

- **Use `dirty-equals` for version-agnostic comparisons.** When asserting data that should be "any valid UUID" or "any ISO timestamp":
  ```python
  from dirty_equals import IsStr, IsUUID
  
  assert item["id"] == IsUUID
  assert item["generated_at"] == IsStr(regex=r"\d{4}-\d{2}-\d{2}T")
  ```

- **For generated markdown (formal notes, discussion.md), use targeted assertions** on specific section content rather than whole-file string comparison:
  ```python
  # BAD: whole file snapshot
  assert note_text == snapshot
  
  # GOOD: targeted assertion
  assert "## Abstract" in note_text
  assert "zotero_key:" in note_text
  assert "biomechanical" in note_text.lower()
  assert "[[99_System/Zotero/storage/" in note_text  # wikilink present
  ```

**Warning signs:**
- PR diffs show 500+ line snapshot changes for a 5-line code change
- "Regenerated all snapshots" appears in commit messages
- Snapshot assertions never fail because nobody reviews the regenerated output
- CI snapshots fail on Monday morning because a date-based field rolled over
- Developers are afraid to touch code with snapshot tests

**Phase to address:** Phase 6 (Golden datasets + snapshot tests) — design snapshot strategy before creating the first snapshot. Define normalization helpers first, then write snapshot tests.

---

### Pitfall 4: Temp Vault Tests Being Slow, Non-Deterministic, or Platform-Specific

**What goes wrong:**
The `test_vault` fixture in `conftest.py` (lines 168-176) creates a full Obsidian vault structure:
- Creates 10+ directories (`99_System`, `PaperForge`, `exports`, `ocr`, `Literature`, etc.)
- Writes `paperforge.json` with 6 config keys
- Writes `.env` with API tokens
- Copies OCR fixture data (`ocr-complete/TSTONE001/`)
- Copies BBT export fixtures (`exports/骨科.json`)
- Creates library records
- Creates formal notes with frontmatter
- Creates Zotero storage mock PDF in TWO locations
- Copies `ld_deep.py` to skill directory

At ~200ms per call and 473+ tests, this works today. But Level 4 temp vault E2E tests add:
- Subprocess calls to `paperforge sync`, `paperforge ocr`, `paperforge status --json` (3-10 seconds each)
- Vault modification during tests (write formal notes, modify frontmatter)
- Cross-platform path resolution (Windows `\` vs POSIX `/`, junctions vs symlinks)
- Cleanup after destructive tests (what if `shutil.rmtree` fails on Windows?)

The result: a single E2E test takes 30-60 seconds. 20 E2E tests = 10-20 minutes. And they fail randomly on macOS because `tempfile` paths differ from what `paperforge.json` expects.

**Why it happens:**
The existing `test_vault` fixture creates a new vault per test function (scope="function"). This is correct for isolation but deadly for E2E tests where setup takes seconds. Additionally, the fixture hardcodes `"99_System"`, `"03_Resources"` etc. as directory names — if the config ever changes, all tests silently use stale names.

The cross-platform issues are worse: `shutil.rmtree` on Windows fails if a file is still open (handles aren't released immediately on process exit in subprocess tests). Temp directory paths on macOS are `/var/folders/...` which is a symlink, and `Path.resolve()` vs `Path.absolute()` behavior differs.

**How to avoid:**

1. **Use `scope="session"` for the vault creation fixture**, with a fast clone strategy for individual tests:
   ```python
   @pytest.fixture(scope="session")
   def base_vault(tmp_path_factory):
       """Create the golden vault structure once per session."""
       vault = tmp_path_factory.mktemp("paperforge-vault")
       build_minimal_vault(vault)
       return vault
   
   @pytest.fixture
   def test_vault(base_vault, tmp_path):
       """Clone the golden vault per test — fast directory copy."""
       vault = tmp_path / "vault"
       shutil.copytree(base_vault, vault, ignore=shutil.ignore_patterns("__pycache__"))
       return vault
   ```

2. **Separate "fast" E2E tests (no subprocess) from "full" E2E tests (subprocess):**
   - Fast E2E: Call Python API functions directly (`run_sync(vault)`)
   - Full E2E: Use `subprocess.run([sys.executable, "-m", "paperforge", "sync"], vault)`
   - Mark full E2E as `@pytest.mark.slow` and run them only on PR + main

3. **Add safe teardown that handles Windows file locks:**
   ```python
   @pytest.fixture
   def test_vault_with_cleanup(test_vault):
       yield test_vault
       # Retry rmtree on Windows (files may be locked briefly)
       for attempt in range(3):
           try:
               shutil.rmtree(test_vault, ignore_errors=False)
               break
           except PermissionError:
               if attempt == 2: raise
               time.sleep(1)
   ```

4. **Normalize paths in assertions.** Never assert on absolute path strings:
   ```python
   # BAD: fails on macOS vs Windows
   assert pdf_path == "D:\\vault\\99_System\\Zotero\\TSTONE001\\file.pdf"
   
   # GOOD: assert on semantics
   assert "TSTONE001" in pdf_path
   assert pdf_path.endswith(".pdf")
   assert pdf_path.count("/") >= 3  # reasonable depth
   ```

5. **Add a `paperforge doctor` post-check after each E2E test fixture creation** to validate the vault is self-consistent. This catches fixture drift early.

**Warning signs:**
- `test_e2e_cli.py` takes 5+ minutes to run
- Tests pass on Windows but fail on macOS (or vice versa)
- `PermissionError` during `conftest.py` teardown on Windows CI
- "file not found" errors for paths that exist when inspected manually
- `TMPDIR` / `TEMP` / `TMP` environment variable differences between CI and local

**Phase to address:** Phase 4 (Temp vault E2E tests) — design vault fixture strategy and cross-platform handling FIRST. Phase 3 (Plugin-backend integration) and Phase 2 (Python unit tests) inform the vault fixture requirements.

---

### Pitfall 5: User Journey Tests Being Too Vague to Automate

**What goes wrong:**
The user journey test plan says: "Test that a new user can install the plugin, configure Zotero, run OCR, and perform deep reading." The UX Contract document describes the journey in prose ("user opens Obsidian, navigates to settings, clicks Install, waits for setup, returns to vault...").

But when the automation engineer tries to write tests, the prose is ambiguous:
- "Configure Zotero" — configure HOW? What values? What if Zotero isn't installed?
- "User waits for setup" — how long? What if it fails? What's the success indicator?
- "Perform deep reading" — on which paper? With what expected output?

The result: the automation engineer either hardcodes assumptions (making the test brittle) or writes a test that checks nothing meaningful (asserting only that the process didn't crash).

**Why it happens:**
User journey tests are a new concept for the project. The team has deep experience with Python unit tests and CLI contract tests, but zero experience defining automated end-to-end journeys. The UX Contract document was written for humans, not machines. Nobody has translated "user opens Obsidian" into "app.workspace.getLeaf()" or "user clicks Install" into "plugin settingTab.installButton.click()".

**How to avoid:**

1. **Write user journey tests as pseudo-code BEFORE implementation**, and verify they can be executed:
   ```
   # Journey: New User Setup
   # Given: No paperforge.json exists, Zotero is installed with at least one paper
   # When: User opens Obsidian plugin settings
   # And: Clicks "Install Configuration" 
   # Then: paperforge.json is created
   # And: Directory structure exists
   # And: OpenCode skills are deployed
   # And: A success notice is shown
   
   # Implementation: plugin_test_helper.run_click("Install Configuration")
   ```

2. **Use a "step" abstraction layer**, not raw Playwright/Node.js APIs:
   ```python
   class UserJourney:
       def __init__(self, vault: Path, plugin: PluginInstance):
           self.vault = vault
           self.plugin = plugin
           self.observed_states = []
       
       def observe(self, state_name: str) -> None:
           """Record an observation for later assertion."""
           self.observed_states.append(state_name)
       
       def assert_state(self, *expected_states: str) -> None:
           missing = set(expected_states) - set(self.observed_states)
           assert not missing, f"Journey states not reached: {missing}"
   ```

3. **Define EXACTLY ONE concrete scenario per journey test.** Not "user can set up" but "user with vault at /tmp/test-vault, Zotero at /tmp/zotero, configures PaperForge, clicks Install, sees paperforge.json created with correct fields." The more concrete, the more automatable.

4. **Mark user journey tests as `@pytest.mark.journey` and run them only on labelled PRs or nightly.** They are the most expensive and least stable tests — don't gate every PR on them.

5. **Create a "journey fixture pack"** — a pre-configured environment that puts the system in a specific state (e.g., "half-setup" = paperforge.json exists but no Zotero junction, "ready-for-deep-reading" = full vault with OCR done). Tests pick a starting pack and assert on the outcome.

**Warning signs:**
- User journey test is 200+ lines with no clear scenario boundary
- Test description in comments is longer than the test code
- Test consistently passes but never catches real bugs
- Test fails inconsistently because "it depends on timing"
- Nobody can articulate what a "passing" user journey test means

**Phase to address:** Phase 5 (User journey tests) — define contracts + scenarios BEFORE writing any code. Must come after Phase 0 (UX Contract docs) is complete.

---

### Pitfall 6: Destructive Tests That Damage Developer Machines or CI Shared State

**What goes wrong:**
A "chaos test" for the `repair` worker is designed to verify it handles corrupted `paperforge.json`. The test:
```python
def test_chaos_corrupted_config(test_vault):
    cfg = test_vault / "paperforge.json"
    cfg.write_text("{{{ NOT JSON }}}")
    result = subprocess.run([sys.executable, "-m", "paperforge", "doctor"], 
                          cwd=test_vault, capture_output=True, text=True, timeout=30)
    assert result.returncode == 1  # doctor should report failure without crashing
```

This is safe because `test_vault` is a temp directory. But a more ambitious chaos test:
```python
def test_chaos_delete_all_notes(test_vault):
    subprocess.run(["rm", "-rf", str(test_vault)], shell=True)
```

...accidentally runs on the developer's real vault if `test_vault` resolves to the wrong path. Or worse:
```python
def test_chaos_delete_paperforge_json():
    """Test what happens when paperforge.json is deleted during sync."""
    # OOPS — no vault fixture, developer accidentally ran real sync first
    vault = Path.home() / "Documents" / "Obsidian" / "MyVault"
    ...
```

**Why it happens:**
Destructive tests are inherently dangerous. The desire to test "what happens when X is deleted" or "what happens when we run `rm -rf`" is valid, but the safety boundary is easy to miss. In CI environments, destructive tests running in parallel can corrupt shared caches, Docker layers, or other projects' working directories.

The `--vault` argument pattern in PaperForge makes this worse: some CLI commands default to the current working directory if `--vault` is omitted. A test that forgets to pass `cwd=test_vault` or `--vault` could operate on the repo root or worse.

**How to avoid:**

1. **All destructive tests MUST use a temp vault created by `tmp_path` or `tmp_path_factory`.** Never accept a path from the environment, a configuration file, or a default.
   ```python
   @pytest.fixture
   def isolated_destruct_vault(tmp_path_factory):
       """Create a vault guaranteed to be temporary and deletable."""
       vault = tmp_path_factory.mktemp("chaos-vault")
       build_minimal_vault(vault)
       return vault
   ```

2. **Destructive tests MUST verify the vault isolation invariant:**
   ```python
   def test_chaos_rmtree(isolated_destruct_vault):
       vault = isolated_destruct_vault
       # SAFETY CHECK: must be a tmp_path, not a real vault
       assert "tmp" in str(vault) or "temp" in str(vault)
       shutil.rmtree(vault)
       assert not vault.exists()
   ```

3. **Never run destructive tests on shared CI runners without Docker isolation.** Use `pytest -m "destructive"` and run in a dedicated ephemeral Docker container:
   ```yaml
   - name: Run destructive tests
     if: github.ref == 'refs/heads/main'  # only on main
     run: |
       docker run --rm -v $PWD:/app paperforge-test:latest \
         pytest -m "destructive" --timeout=120
   ```

4. **Destructive tests must be in their own test module (destructive_test_*.py)** and NEVER imported by non-destructive test runners. Add them to `pytest.ini` ignore lists:
   ```ini
   [tool.pytest.ini_options]
   addopts = "--ignore=tests/sandbox/00_TestVault/ --ignore=tests/destructive/"
   ```

5. **For every destructive test, write a "safety contract" at the top of the test function:**
   ```python
   # SAFETY CONTRACT:
   # - This test ONLY operates on isolated_destruct_vault
   # - It does NOT touch the filesystem outside that directory
   # - It does NOT make network calls
   # - If it fails, no production data is affected
   # - Timeout: 30 seconds max
   ```

**Warning signs:**
- Test has no `tmp_path`, `tmpdir`, or fixture isolation (bare path operations)
- Test calls `os.remove()`, `shutil.rmtree()`, or `Path.unlink()` without verifying the path is a temp directory
- Test uses `shell=True` (allows arbitrary command injection)
- Test modifies files outside the test directory for "setup"
- Test references `Path.home()`, `os.getcwd()`, or `Path(".")` without guards

**Phase to address:** Phase 6 (Destructive/chaos tests) — define safety invariants BEFORE writing any destructive test. Phase 7 (CI expansion) — configure Docker isolation.

---

### Pitfall 7: Golden Dataset and Fixture Bloat

**What goes wrong:**
The golden dataset starts as: 
- `bbt_export_absolute.json` (6KB — one paper)
- `bbt_export_storage.json` (6KB — one paper)
- `blank.pdf` (1KB)

Six months later:
- 3 BBT JSON variants x 5 papers each = 15 JSON files (200KB)
- OCR result snapshots for 5 papers (50MB of JSON)
- Expected snapshot outputs for CLI --json in 4 command variants (50KB)
- Formal note markdown snapshots for 5 papers x 3 formats (200KB)
- PDF fixtures for 5 papers (50MB)
- Temp vault fixture packs for 3 scenarios (5MB each, but duplicated across branches)

The fixtures directory is now 100MB+ in the git repo. `git clone` is slow. CI checkout is slow. Developers don't know which fixtures are still used, so nobody deletes anything. The `tests/fixtures/` directory becomes a "fixture graveyard."

**Why it happens:**
- Every test author adds "just one more fixture variant" for their specific edge case
- Nobody knows which fixtures are referenced by which tests (no cross-references)
- Binary fixtures (PDFs, OCR JSON dumps) bloat git history even if deleted later (git stores them forever)
- No fixture governance: "can I delete this?" requires hunting through all test files

**How to avoid:**

1. **Keep fixtures outside the git repo.** Use a `tests/fixtures/download_fixtures.py` script that fetches or generates fixtures on demand:
   ```python
   # tests/fixtures/download_fixtures.py
   """Download or generate test fixtures. Run `python download_fixtures.py` before testing."""
   
   FIXTURES = {
       "bbt_export_absolute.json": "https://storage.example.com/fixtures/v2/bbt_export_absolute.json",
       "blank.pdf": generate_blank_pdf,  # function that creates it
   }
   ```
   Add `tests/fixtures/cache/` to `.gitignore`. CI pre-populates cache via a GitHub Actions cache step.

2. **Generate fixtures from code, not by hand.** PDF fixtures should be generated by a script:
   ```python
   def generate_blank_pdf(path: Path) -> None:
       """Generate a minimal valid PDF (single blank page)."""
       content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
       path.write_bytes(content)
   ```

3. **Tag fixtures with a metadata file and validate coverage:**
   ```json
   // tests/fixtures/MANIFEST.json
   {
     "version": 2,
     "fixtures": {
       "bbt_export_absolute.json": {
         "used_by": ["test_path_normalization.py", "test_pdf_resolver.py"],
         "generated": "2026-05-01",
         "desc": "BBT export with absolute Windows paths"
       },
       "blank.pdf": {
         "used_by": ["test_ocr_preflight.py", "test_pdf_resolver.py"],
         "generated": "2026-04-15",
         "desc": "Minimal 1-page PDF for resolver tests"
       }
     }
   }
   ```
   Add a CI check: `python scripts/validate_fixtures.py` that verifies every fixture is used by at least one test and every test's referenced fixtures exist.

4. **For OCR fixture data, use synthetic (tiny) JSON instead of real OCR dumps.** The real OCR result for one page of "hello world" could be 2MB of JSON. A synthetic version is 200 bytes:
   ```python
   def make_ocr_result(pages: int = 1) -> dict:
       return {
           "layoutParsingResults": [
               {
                   "prunedResult": {
                       "page_count": pages,
                       "parsing_res_list": [
                           {"block_label": "text", "block_content": f"Page {i} content", 
                            "block_bbox": [10, 10, 100, 30], "block_id": 1}
                           for i in range(pages)
                       ]
                   }
               }
           ]
       }
   ```

5. **Version the BBT fixture JSONs with the schema they test.** When BBT changes its export format (different key names, different path format), add a new fixture (e.g., `bbt_export_v3_mixed.json`) rather than modifying existing ones. Tests that exercise specific versions reference them explicitly.

**Warning signs:**
- `tests/fixtures/` is over 10MB in git
- "Why is this 50MB JSON file here?" isn't answerable
- A fixture file hasn't been referenced by any test import in 6 months
- `git blame` on fixture files shows 15 different authors adding papers
- CI cache for fixtures takes longer than running the tests

**Phase to address:** Phase 6 (Golden dataset + fixtures) — establish manifest and generate-from-code policy BEFORE adding fixtures. Review all existing fixtures (current `tests/fixtures/` is 4 files, small — keep it that way).

---

### Pitfall 8: Version Sync Checking That Tests the Wrong Thing

**What goes wrong:**
The Level 0 version sync checker (`check_version_sync.py`) compares these version strings:
- `paperforge/__init__.py`: `__version__ = "1.4.17rc3"`
- `manifest.json`: `"version": "1.4.17rc3"`
- `paperforge/plugin/versions.json`: `{"1.4.17rc3": "1.9.0", ...}`

The check looks for exact string matches. But:
1. `manifest.json` has `"version": "1.4.17rc3"` while `__init__.py` has `__version__ = "1.4.17rc3"` — these are the same semver but `rc3` in the version string is printed in two different contexts where `rc3` has different meaning (Python packages can't use `rc` suffix with some build backends)
2. `versions.json` has version ranges (`"1.4.17rc3"`) that may not exactly match the release tag (`v1.4.17`)
3. The CI matrix installs from `pip install -e .` which resolves the version from `paperforge/__init__.py` — but a developer who runs `pip install git+https://...@v1.4.16` might have a different installed version than the source code version

The version check passes but the actual deployed artifact has a different version. The test checks the right files but validates the wrong invariant.

**Why it happens:**
Version is distributed across 4+ files (`__init__.py`, `manifest.json`, `versions.json`, `pyproject.toml` dynamic attr), all set independently. The `bump.py` script updates all of them, but manual edits, cherry-picks, or hotfix branches can miss one. The natural reaction is "add more checks" but this creates a false sense of security.

**How to avoid:**

1. **Check DERIVED versions, not just declared versions.** The real question isn't "do all files have the same version string?" but "can the installed package report itself correctly?":
   ```python
   def test_installed_version_matches_source():
       """pip-installed package reports the same version as __init__.py."""
       import paperforge
       source_version = paperforge.__version__
       result = subprocess.run(
           [sys.executable, "-m", "paperforge", "--version"],
           capture_output=True, text=True
       )
       installed_version = result.stdout.strip()
       assert source_version == installed_version, (
           f"Source v{source_version} != installed v{installed_version}"
       )
   ```

2. **Validate version schema (semver), not exact string equality.** `1.4.17rc3` and `1.4.17-rc3` are semantically equivalent but string-different:
   ```python
   import re
   
   SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$")
   
   def test_all_versions_are_valid_semver():
       import paperforge
       manifest = json.loads(Path("manifest.json").read_text())
       assert SEMVER_PATTERN.match(paperforge.__version__)
       assert SEMVER_PATTERN.match(manifest["version"])
   ```

3. **Test the `paperforge --version` CLI output** — this is what users and plugins actually see. If the CLI reports the wrong version, the file-level consistency doesn't matter:
   ```python
   def test_cli_version():
       result = subprocess.run(
           [sys.executable, "-m", "paperforge", "--version"],
           capture_output=True, text=True, timeout=10
       )
       assert result.returncode == 0
       assert re.match(r"paperforge \d+\.\d+\.\d+", result.stdout)
   ```

4. **Remove version from `paperforge.json`.** Currently `paperforge.json` stores `"version": "1.2.0"` (hardcoded in `conftest.py:50`). This is a build-time artifact, not a runtime state. The worker scripts should read the installed package version, not a config file version. Remove this field from the config schema to eliminate one source of drift.

5. **Automate version bump as a CI action, not a script.** When merging to `main`, CI should:
   - Read `__init__.py` version
   - Verify it matches `manifest.json` and `versions.json`
   - Tag the release with `v{version}`
   - If versions mismatch, FAIL THE BUILD

**Warning signs:**
- Version numbers differ between `__init__.py` and `manifest.json` after a cherry-pick
- `paperforge --version` reports a different version than what's in the UI dashboard
- A user reports "I installed v1.4.17 but the plugin says v1.4.16"
- `versions.json` is manually edited without running `bump.py`

**Phase to address:** Phase 1 (Level 0: Version sync checker) — test installed version, not file-level string equality. This is the foundation all other layers depend on.

---

### Pitfall 9: CLI --json Contract Tests That Check Shape But Not Semantics

**What goes wrong:**
The CLI --json contract tests validate that output is valid JSON with expected keys:
```python
def test_paths_json_structure(mock_vault):
    data = json.loads(output)
    required_keys = {"vault", "worker_script", "ld_deep_script"}
    for key in required_keys:
        assert key in data
```

But this only checks that the keys EXIST, not that the VALUES are correct. A refactoring that swaps `vault` and `worker_script` values would pass this test. Worse, if a value contains an unresolved template token like `<system_dir>`, the key exists so the test passes, but the output is broken for consumers.

The existing test `test_paths_json_no_unresolved_tokens` catches `<system_dir>` placeholders, but there's no equivalent check for `<<obsidian_template>>`, `{resources_dir}`, or other token patterns that might leak into output.

**Why it happens:**
JSON output tests are easy to write shallowly: parse JSON, assert key exists. Deep validation (value shape, data type, semantic correctness, cross-field consistency) is harder and more verbose, so tests stop at "valid JSON with the right keys." The same pattern appears in `test_e2e_cli.py` which checks `total_papers >= 1` but not that the count matches actual papers.

**How to avoid:**

1. **Validate VALUE TYPES, not just key presence:**
   ```python
   def test_paths_json_value_types(mock_vault):
       data = json.loads(get_output())
       assert isinstance(data["vault"], str)
       assert data["vault"].endswith("mock_vault_name")
       assert isinstance(data["worker_script"], str)
       assert data["worker_script"].endswith(".py")
   ```

2. **Validate cross-field consistency.** If `paths --json` reports 3 worker scripts, the actual files must exist:
   ```python
   def test_paths_json_scripts_exist(mock_vault):
       data = json.loads(get_output())
       for key in ["worker_script", "ld_deep_script"]:
           script_path = Path(data[key])
           assert script_path.exists(), f"{key}: {script_path} does not exist"
   ```

3. **For each --json command, maintain a SCHEMA definition** and validate against it:
   ```python
   # paperforge/schemas.py or inline in test
   PATHS_JSON_SCHEMA = {
       "type": "object",
       "required": ["vault", "worker_script", "ld_deep_script"],
       "properties": {
           "vault": {"type": "string", "minLength": 1},
           "worker_script": {"type": "string", "pattern": r"\.py$"},
           "ld_deep_script": {"type": "string", "pattern": r"\.py$"},
       }
   }
   
   def test_paths_json_schema(mock_vault):
       import jsonschema  # or a lightweight dict-based validation
       data = json.loads(get_output())
       jsonschema.validate(data, PATHS_JSON_SCHEMA)
   ```

4. **Add cross-command consistency tests.** If `status --json` reports `total_papers: 3`, then `paths --json` must report paths that those papers can be found at:
   ```python
   def test_status_and_paths_consistent(mock_vault):
       status_data = json.loads(run_command(["status", "--json"]))
       paths_data = json.loads(run_command(["paths", "--json"]))
       # If papers exist, paths must include literature dir
       if status_data["total_papers"] > 0:
           assert "Literature" in paths_data["literature"]
   ```

5. **Treat --json output as a THEOREM, not just data.** Every --json output should be:
   - Valid JSON (parses correctly)
   - Type-correct (every value has the expected type)
   - Referentially valid (all paths point to existing files)
   - Cross-consistent (multiple commands agree)

**Warning signs:**
- A `--json` test fails because a value is `None` instead of a path string
- A `--json` test passes but the output contains "ERROR:" text in a value
- JSON output changes format between releases but --json tests still pass
- Output contains resolved paths but points to non-existent files
- Two different CLI commands report contradictory information

**Phase to address:** Phase 2 (CLI contract tests) — define JSON output schema first, implement validation, then write the tests. This is the contract that plugin consumers depend on.

---

### Pitfall 10: Plugin-Backend Integration Tests That Test Subprocess Mechanics Instead of Behavior

**What goes wrong:**
The plugin-backend integration tests test THAT a subprocess spawns, not WHAT the subprocess produces:
```python
def test_plugin_invokes_sync():
    result = subprocess.run([sys.executable, "-m", "paperforge", "sync"], 
                          cwd=test_vault, capture_output=True, timeout=30)
    assert result.returncode == 0
```

This test passes if the subprocess runs and exits 0. But it doesn't test:
- Did `sync` actually write the expected files?
- Did the output conform to the format the plugin expects?
- Did the exit code 0 come from a successful sync or from an early return in an error path?

The same pattern exists in `test_plugin_install_bootstrap.py` which reads `main.js` source code, asserts strings are present, but never actually RUNS the plugin:
```python
def test_setup_args_global_vault_before_subcommand():
    source = PLUGIN_MAIN.read_text(encoding="utf-8")
    vault_pos = source.find("'--vault'")
    setup_pos = source.find("'setup'")
    assert vault_pos < setup_pos
```

This verifies source code structure, not runtime behavior. A minifier or bundler that reorders string literals would break these tests even though the plugin works correctly.

**Why it happens:**
The Obsidian plugin can't be tested in a headless CI environment without Obsidian itself (no Obsidian headless mode exists). So plugin-backend tests fall back to:
1. Parsing plugin source code for expected patterns (tests file structure, not runtime behavior)
2. Running subprocess commands (tests Python, not the plugin)
3. Writing integration tests that only exercise the Python layer and assume the plugin will work

None of these actually test the plugin-backend boundary where the real bugs live (argument passing, output parsing, error handling).

**How to avoid:**

1. **Extract a thin JS module for testing** that can run in Node.js without Obsidian:
   ```javascript
   // paperforge/plugin/paperforge-backend.js (testable without Obsidian)
   const { execSync } = require('child_process');
   const path = require('path');
   
   class PaperForgeBackend {
       constructor(vaultPath) { this.vaultPath = vaultPath; }
       
       runCommand(args) {
           return execSync(
               `python -m paperforge ${args.join(' ')}`,
               { cwd: this.vaultPath, encoding: 'utf-8', timeout: 30000 }
           );
       }
       
       parseJsonOutput(raw) {
           try { return JSON.parse(raw); }
           catch { return { error: 'invalid JSON', raw }; }
       }
   }
   module.exports = { PaperForgeBackend };
   ```
   Test this with Node.js in CI (no Obsidian needed):
   ```javascript
   // tests/plugin/backend.test.js
   const { PaperForgeBackend } = require('../../paperforge/plugin/paperforge-backend');
   
   test('sync produces index file', () => {
       const backend = new PaperForgeBackend(testVaultPath);
       backend.runCommand(['sync']);
       const output = backend.runCommand(['status', '--json']);
       const data = backend.parseJsonOutput(output);
       expect(data).toHaveProperty('total_papers');
   });
   ```

2. **For the remaining plugin JS code, use source-level assertions only for CONSTANTS** (command names, file paths) that don't change between dev and production:
   ```javascript
   assert(MAIN_SOURCE.includes('"sync"'), "Plugin must reference 'sync' command");
   ```
   But test BEHAVIOR through the extracted module, not through source string checks.

3. **Mock the Obsidian plugin API for comprehensive testing.** Use a test harness like `jest` + `obsidian-typings` to run the plugin code:
   ```javascript
   // tests/plugin/harness.js
   const { App, Plugin, Workspace } = require('obsidian-typings/mock');
   
   function createTestApp(vaultPath) {
       const app = new App();
       app.vault.adapter.basePath = vaultPath;
       return app;
   }
   ```

**Warning signs:**
- Tests read `main.js` source code and check for string patterns
- Plugin tests never actually instantiate any plugin class
- Plugin-backend boundary (argument passing, output parsing) has 0 test coverage
- A change to the plugin's `setNotice()` method breaks 5 string-matching tests
- Subprocess tests pass but the plugin dashboard shows no data

**Phase to address:** Phase 3 (Plugin-backend integration) — extract testable module first, then write backend tests. Source-code assertions ONLY for stable constants.

---

### Pitfall 11: Test Layering Conflicts — Different Levels Testing the Same Code in Contradictory Ways

**What goes wrong:**
Level 1 (Python unit tests) patches `requests.post` to return a mock response. Level 2 (CLI contract) runs `paperforge sync` with `--json` and asserts on stdout. Level 4 (temp vault E2E) creates a vault and runs the full pipeline. All three test the `sync` worker, but:

- Level 1 test passes because the mock returns `{"data": {"jobId": "job-123"}}`
- Level 2 test passes because `sync --json` returns `{"synced": 1, "errors": []}`
- Level 4 test fails because the REAL PaddleOCR API returns `{"status": "error", "message": "..."}`
- Developer says "all tests pass" but the feature is broken
- Nobody knows WHICH level is the authoritative source of truth for "does sync work?"

**Why it happens:**
Each test level is written independently by different developers or at different times. There's no cross-reference between levels. Level 1 mocks are not validated against Level 4 real behavior. Level 2 contract assertions don't reference Level 1 unit test assertions. The test pyramid is a collection of silos, not a hierarchy.

**How to avoid:**

1. **Define a "truth hierarchy":**
   - Level 4 (temp vault E2E) is the AUTHORITATIVE truth for "does this feature work?"
   - Level 2 (CLI contract) validates that the CLI layer translates correctly (relies on Level 4 being green)
   - Level 1 (unit tests) validates edge cases and internal logic (relies on Level 4 defining the "happy path" contract)
   - **Level 1 tests must be red when Level 4 tests are red** (if E2E fails, unit tests should also fail for the same feature)

2. **Validate mocks against real behavior.** When Level 4 tests pass, extract the real output and use it to update Level 1 mock fixtures:
   ```python
   # In Level 4 test:
   real_output = subprocess.run([...], capture_output=True)
   SNAPSHOTS["sync_stdout"].save(real_output.stdout)
   
   # Level 1 reads:
   FIXTURE_SYNC_OUTPUT = SNAPSHOTS["sync_stdout"].load()
   ```

3. **Add a "consistency audit" test that runs periodically** and compares Level 1 mock expectations with Level 4 real output:
   ```python
   @pytest.mark.slow
   @pytest.mark.consistency
   def test_unit_mocks_match_real_output():
       """Verify that Level 1 mock fixtures match real OLD IS GOLD output."""
       expected = run_full_pipeline()  # Real E2E run
       mocked = run_with_unit_mocks()  # Same scenario, mocked
       # Compare keys and types, not exact values
       assert set(expected.keys()) == set(mocked.keys())
   ```

4. **Tag tests with the level they belong to** and use `pytest --strict-markers`:
   ```python
   @pytest.mark.level1
   def test_sync_unit():
       ...
   
   @pytest.mark.level4
   def test_sync_e2e():
       ...
   ```
   Run Level 1 ALWAYS, Level 4 on PRs only, and add a CI check: `pytest -m "level4"` must not fail when `pytest -m "level1"` passes (but the reverse isn't required — Level 1 can catch things Level 4 doesn't).

**Warning signs:**
- Level 1 mocks return data that Level 4 would never produce
- A Level 4 test passes but the feature doesn't work for users
- "All tests pass" said confidently right before a production outage
- Adding a new feature requires updating 3 different test suites independently
- Test flakiness correlates with mock data staleness

**Phase to address:** Phase 7 (CI expansion + integration) — establish truth hierarchy and mock validation BEFORE tests are written at all layers. The roadmap phases (1-6) must reference each other's contracts.

---

### Pitfall 12: Windows-Specific Path Hell in Temp Vault and CLI Tests

**What goes wrong:**
The temp vault fixture creates paths like `tmp_path / "99_System" / "PaperForge" / "exports"`. On Linux/macOS, this produces `/tmp/.../99_System/PaperForge/exports`. On Windows, this produces `C:\Users\...\AppData\Local\Temp\...\99_System\PaperForge\exports`.

The code uses `Path.resolve()` which resolves symlinks (on macOS, `/var` -> `/private/var`, breaking expected paths). On Windows, junctions (which PaperForge uses for Zotero data linking) behave differently from symlinks — `Path.is_dir()` returns `True` for junctions, but `shutil.rmtree()` can fail on junctions.

Existing patterns like `assert "\\" not in pdf_link` (test_e2e_pipeline.py:85) explicitly check for forward slashes — but this assertion doesn't test actual path behavior, only the wikilink rendering. Real path resolution behavior between platforms is untested.

**Why it happens:**
The existing codebase has reasonable cross-platform awareness (forward slashes in wikilinks, `Path` objects everywhere), but the TESTS make platform-specific assumptions:
- `conftest.py:151`: `zotero_dir = system_dir / "Zotero" / "TSTONE001"` — works everywhere but different absolute paths per platform
- `test_e2e_cli.py:42`: `idx = test_vault / "99_System" / "PaperForge" / "indexes" / "formal-library.json"` — these paths come from config, not magic, so they should work, but the tests don't verify that CLI commands run FROM the vault directory resolve these correctly
- Junction behavior (Zotero data linking) is entirely untested and different on every platform

**How to avoid:**

1. **Test path resolution with synthetic constraints, not real filesystems.** Create a mock vault with an "impossible" structure and verify the resolver handles it:
   ```python
   def test_path_resolver_windows_to_posix_conversion():
       """Verify resolver converts Windows paths to POSIX-style wikilinks."""
       paths = {"vault": Path("/tmp/vault"), "zotero": Path("/tmp/vault/Zotero")}
       pdf_path = "D:\\Zotero\\storage\\KEY\\file.pdf"  # raw Windows path from BBT
       resolved = resolve_pdf_path(pdf_path, paths)
       assert "/" in resolved  # no backslashes
       assert resolved.startswith("Zotero/storage/KEY/")
   ```

2. **Run path-specific tests on ALL THREE platforms in CI**, not just the fast Linux-only path. The CI matrix MUST include at least one Windows temp vault E2E test.

3. **For junction tests, create a synthetic junction using `os.symlink()` with `target_is_directory=True` on Windows** and verify `paperforge doctor` correctly identifies it:
   ```python
   @pytest.mark.skipif(sys.platform != "win32", reason="Junction test")
   def test_junction_detection():
       vault = tmp_path / "vault"
       vault.mkdir()
       junction_target = tmp_path / "zotero-data"
       junction_target.mkdir()
       junction_link = vault / "Zotero"
       os.symlink(str(junction_target), str(junction_link), target_is_directory=True)
       
       result = subprocess.run([sys.executable, "-m", "paperforge", "doctor"], 
                             cwd=vault, capture_output=True, text=True, timeout=30)
       assert "[OK]" in result.stdout or "Zotero" in result.stdout
   ```

4. **Normalize paths in ALL test assertions.** Never assert raw path strings across platforms:
   ```python
   class PathAssertions:
       @staticmethod
       def is_relative_to(path: Path, base: Path) -> bool:
           """Cross-platform relative path check."""
           try:
               path.relative_to(base)
               return True
           except ValueError:
               return False
   ```

5. **Use `pyfakefs` for filesystem-level unit tests** (Level 1) and real filesystem for E2E tests (Level 4). This separates platform-specific concerns from logic tests.

**Warning signs:**
- Tests pass on macOS but fail on Windows CI
- `PermissionError` during `shutil.rmtree` on Windows
- Path comparisons fail because one is resolved and the other isn't
- Junction creation tests hang or crash on CI
- `NotADirectoryError` when traversing vault structure
- `shutil.copytree` fails on Windows junctions (it tries to follow them)

**Phase to address:** Phases 4 + 7 (temp vault E2E, CI expansion) — must include at least one Windows CI node. Platform-specific tests marked with `@pytest.mark.skipif`. Path normalization utilities extracted first.

---

### Pitfall 13: Test Double Inheritance (When the Wrong Test Reuses the Wrong Fixture)

**What goes wrong:**
A Level 4 (temp vault E2E) test needs a "vault with two papers in different domains." The developer finds `test_vault` in `conftest.py` which creates one paper in 骨科 domain. They add a second paper to the fixture. Now ALL 473+ tests create two papers instead of one. The 10 tests that assert `len(items) == 1` break. The developer has to fix 10 tests for a fixture that only one test needed.

Even worse, a Level 1 (unit test) for path normalization uses `test_vault` because "it's already there." But `test_vault` creates 10 directories, writes 5 files, copies OCR data, creates Zotero storage — all of which are irrelevant to path normalization. The test is now slow and depends on components it shouldn't know about.

**Why it happens:**
`test_vault` in `conftest.py` is the "convenience fixture" that every test reaches for because it's always available. There's no fixture hierarchy — no "small vault" (just config), "medium vault" (config + one paper), "full vault" (config + papers + OCR + Zotero). The single fixture is a kitchen sink that grows with every new test requirement.

**How to avoid:**

1. **Create a fixture HIERARCHY, not a single fixture:**

```python
# conftest.py

@pytest.fixture
def empty_vault(tmp_path) -> Path:
    """Level 0: Minimal vault with config only. Fast (~10ms)."""
    vault = tmp_path / "vault"
    vault.mkdir()
    write_config(vault, {"system_dir": "99_System", "resources_dir": "03_Resources"})
    return vault

@pytest.fixture
def config_vault(empty_vault) -> Path:
    """Level 1: Vault with directories created. Fast (~30ms)."""
    vault = empty_vault
    create_directories(vault)
    return vault

@pytest.fixture
def vault_with_export(config_vault) -> Path:
    """Level 2: Vault with BBT export JSON. Medium (~50ms)."""
    vault = config_vault
    install_export_fixture(vault, "骨科.json")
    return vault

@pytest.fixture
def vault_with_ocr(vault_with_export) -> Path:
    """Level 3: Vault with OCR data. Slow (~100ms)."""
    vault = vault_with_export
    install_ocr_fixture(vault, "TSTONE001")
    return vault

@pytest.fixture
def full_test_vault(vault_with_ocr) -> Path:
    """Level 4: Complete vault with Zotero storage, formal notes. Slowest (~200ms)."""
    vault = vault_with_ocr
    install_zotero_storage(vault, "TSTONE001")
    create_formal_notes(vault, "TSTONE001")
    return vault
```

2. **Level 1 tests should use `empty_vault` or `config_vault`**, NOT `full_test_vault`. Enforce this with a CI linter that flags `full_test_vault` usage outside of Level 4 test files.

3. **When a test needs a specific vault state, compose from the hierarchy**, not by modifying the top-level fixture:
   ```python
   # CORRECT: Compose from existing fixtures
   @pytest.fixture
   def vault_with_two_domains(vault_with_export):
       vault = vault_with_export
       install_export_fixture(vault, "运动医学.json")  # add second domain
       return vault
   ```

4. **Add a FAST test marker that excludes all vault fixture setup** for pure unit tests that don't need filesystem access:
   ```python
   @pytest.mark.fast
   @pytest.mark.level1
   def test_slugify_empty_string():
       from paperforge.worker._utils import slugify
       assert slugify("") == ""
   ```

**Warning signs:**
- `test_vault` is imported by tests in 10+ different test files at different levels
- `conftest.py:create_test_vault()` is >150 lines
- Adding a new field to the vault fixture breaks 30 tests in unrelated modules
- A "unit test" takes 200ms+ because it unnecessarily creates a full vault
- Developers can't explain WHY their test needs the full vault (it just does)

**Phase to address:** Phase 1 (Version sync / fixture cleanup) — refactor vault fixtures FIRST before writing new tests. The fixture hierarchy must be in place before Levels 2-6 add more test files.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Single `test_vault` fixture for all levels | Quick setup, one fixture to maintain | Test bloat, cross-test coupling, slow execution | Never — use fixture hierarchy from day one |
| Nested `with patch(...)` blocks (12+ deep) | No fixture extraction effort | Impossible to debug, brittle mocks, high cognitive load | Never — extract mock fixtures with `@pytest.fixture` |
| Whole-file JSON snapshot assertions | "Comprehensive" in one line | Brittle, regenerating snapshots hides real regressions | Never — snapshot specific shapes, normalize dynamic fields |
| Full CI matrix (3x3x2) on every push | "Maximum coverage" | 4+ hour CI wait, burned free-tier credits | Only for tagged releases; use path-filtered matrix for push |
| Testing plugin via source code string matching | Simple, no dependencies | Tests file structure not behavior, breaks on minification | Only for stable CONSTANTS (command names, file paths) |
| Hand-written JSON fixture files | Easy to create | Drift from real data, no manifest, nobody knows if still used | Only for 3-5 core fixture files; use generated or downloaded rest |
| Version check as string equality | Trivial implementation | False negatives (semver equivalence), false positives (different build contexts) | Never — validate semver structure and installed version |
| All E2E tests create vault as function-scoped | Perfect isolation | 50x overhead for slow tests | Use session-scoped golden vault + per-test clone |
| CI runs all test levels every time | Simple single command | 45-minute+ CI for a typo fix | Use path filters and `-m "not slow"` for push events |
| Mock responses from memory (guessed shapes) | Fastest to write | Silently wrong mock data, false confidence | Never — capture real responses to fixture files first |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Python worker -> subprocess -> CLI --json | Testing that subprocess exits 0 but not validating stdout | Validate that CLI --json output is valid, type-correct, referentially consistent |
| Plugin -> `child_process.spawn('python -m paperforge sync')` | Using `cwd: vaultPath` without verifying Python is available | Pre-flight check: `python -c "import paperforge"` before spawning commands |
| BBT JSON export -> Python parser | Assuming BBT JSON format is stable across Biber versions | Version-check the export file; test with multiple BBT export format fixtures |
| PaddleOCR API -> Python OCR worker | Mocking API responses from guessing (not real recordings) | Use VCR.py to record real PaddleOCR responses; validate mocks against recordings |
| OCR output -> formal note frontmatter | Testing OCR parsing and frontmatter writing independently (they disagree) | Always test the full pipeline: OCR output -> formal note -> rendered frontmatter |
| Python version -> plugin manifest version | Checking file-level string equality | Validate with `pip show paperforge` vs `python -m paperforge --version` |
| temp vault -> subprocess -> filesystem | Using `tmp_path` for vault but `Path.cwd()` inside subprocess | Always pass `--vault` or set `cwd` explicitly; never inherit working directory |
| Windows junctions -> Zotero data linking | Testing only on macOS/Linux where symlinks behave differently | Mark junction tests `@pytest.mark.skipif(sys.platform != "win32")` |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Function-scoped vault fixture in every E2E test | E2E suite takes 15+ min for 20 tests | Session-scoped golden vault + per-test fast clone | 10+ E2E tests |
| All CI jobs run full matrix | 4+ hour total CI runtime | Path-filtered matrix, level-specific jobs | 3+ CI matrix dimensions |
| Snapshot assertions on full JSON output | PR diffs show 500-line snapshot changes | Shape assertions + normalized fields | First refactor after snapshots are created |
| Mock responses never validated against real API | Tests pass, production breaks silently | Periodic mock-vs-real consistency audit | 2+ months after mocks were created |
| All tests import `test_vault` regardless of need | "Unit tests" take 200ms+ each | Fixture hierarchy: use minimal fixture for each test level | 100+ tests using the heavy fixture |
| `shutil.rmtree` on vault cleanup | Windows CI fails with `PermissionError` | Retry-with-backoff cleanup + ignore_errors | Any Windows CI run |
| User journey tests as part of PR gate | PRs blocked on 20-min unstable tests | Run journey tests nightly only, not on every PR | First flaky journey test |

---

## "Looks Done But Isn't" Checklist

- [ ] **Level 0 (Version sync):** Runs `python -m paperforge --version` and confirms installed version matches source — but does it also verify `manifest.json` and `versions.json` agree? Could a `pip install` from a different branch silently install the wrong version?
- [ ] **Level 1 (Python unit):** OCR state machine tests mock `requests.post` and `requests.get` — but do the mock values come from a REAL recorded PaddleOCR response, or from guessing the API shape?
- [ ] **Level 2 (CLI --json):** Tests verify JSON has expected keys — but do they verify VALUE TYPES? Could `vault` be `None` or an empty string?
- [ ] **Level 3 (Plugin-backend):** Tests read `main.js` source code for string patterns — but do they actually RUN the plugin or subprocess to verify behavior?
- [ ] **Level 4 (Temp vault E2E):** Vault is created with `conftest.py:create_test_vault()` — but do the tmp_path fixture names (`00_TestVault`) match the CONFIGURABLE directory names, and would the test break if someone changes `default_config`?
- [ ] **Level 5 (User journey):** Journey is documented in prose — but is there a concrete, executable script that implements each step?
- [ ] **Level 6 (Destructive):** Tests use `isolated_destruct_vault` — but is there a SAFETY CONTRACT at the top of each destructive test that verifies the vault is a temp directory?
- [ ] **Golden datasets:** `tests/fixtures/` has manifest.json — but does every fixture have a `used_by` list that's validated by CI?
- [ ] **Snapshot tests:** Snapshots use inline snapshot or normalized-shape assertions — or are they whole-file JSON compares that will break on every generated_at timestamp change?
- [ ] **CI matrix:** Config has path-filtered jobs — but do the path filters cover ALL relevant file patterns (`.py`, `.js`, `.json`, `.yaml`)?
- [ ] **Cross-platform:** Tests pass on macOS — but is there a Windows CI node running the path-specific E2E tests, including junction tests?

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Mock drift (P1) — mocks mismatch real API | MEDIUM | Capture real PaddleOCR responses with VCR.py; regenerate all mock fixtures; add periodic consistency audit test |
| CI matrix too slow (P2) — 4+ hour CI | HIGH | Restructure CI into level-specific jobs with path filters; move slow tests to nightly; add `pytest -m "slow"` markers |
| Snapshot brittleness (P3) — failing on every refactor | MEDIUM | Replace whole-file snapshots with shape-specific assertions; add normalization helpers for dynamic fields |
| Temp vault slow (P4) — E2E suite takes 15 min | MEDIUM | Refactor to session-scoped golden vault + per-test fast clone; separate "fast" and "full" E2E |
| Vague journey tests (P5) — can't automate | HIGH | Rewrite UX contracts as concrete step sequences; build step abstraction layer; pick ONE concrete scenario per test |
| Destructive test safety (P6) — real vault at risk | CRITICAL | Add isolation assertion (must be tmp_path); move to Docker-only; add safety contract to every destructive test |
| Fixture bloat (P7) — 100MB in repo | HIGH | Remove git-tracked large fixtures; add `download_fixtures.py` script; generate from code where possible; add manifest validation |
| Version sync mismatch (P8) — wrong installed version | LOW | Add `pip show paperforge` check; validate semver structure; remove version from `paperforge.json` |
| CLI --json shallow tests (P9) — keys but no semantics | LOW | Add `jsonschema` validation; add cross-command consistency tests; validate types and referential integrity |
| Plugin tests too shallow (P10) — source matching | MEDIUM | Extract `paperforge-backend.js` module; write Node.js tests; keep source assertions only for constants |
| Test layering conflicts (P11) — levels disagree | HIGH | Establish truth hierarchy (Level 4 > Level 2 > Level 1); add mock validation against real output; level-tag all tests |
| Windows path hell (P12) — cross-platform failures | MEDIUM | Add synthetic path constraint tests; normalize all path assertions; run at least one Windows CI node |
| Fixture inheritance (P13) — wrong test, wrong fixture | MEDIUM | Extract fixture hierarchy (empty_vault -> config_vault -> vault_with_export -> vault_with_ocr -> full_test_vault); CI-lint heavy fixture usage |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Mocking too early/rigidly (P1) | Phase 2 — Python unit tests | Validate mock fixture data came from real API recordings; autospec=True on all mocks |
| CI matrix slow (P2) | Phase 7 — CI expansion | CI completes under 15 min for push events; matrix jobs are partitioned by level |
| Snapshot brittleness (P3) | Phase 6 — Golden datasets | Snapshot assertions use normalized shapes, not whole files; inline-snapshot vs external files |
| Temp vault slow/non-det (P4) | Phase 4 — Temp vault E2E | E2E suite under 5 min; session-scoped golden vault with per-test clone; cross-platform cleanup |
| Vague user journeys (P5) | Phase 5 — User journey tests | Each journey test has exactly ONE concrete scenario; step abstraction layer exists |
| Destructive test safety (P6) | Phase 6 — Destructive/chaos | Safety contract verified by CI; destructive tests run in Docker only |
| Fixture bloat (P7) | Phase 6 — Golden datasets | Fixture manifest exists; CI validates all fixtures are used; generated > hand-written |
| Version sync wrong invariant (P8) | Phase 1 — Version sync | Tests validate installed version, not file string equality; semver schema validated |
| CLI --json shallow tests (P9) | Phase 2 — CLI contract | JSON output validated against schema (keys + types + references + cross-consistency) |
| Plugin subprocess mechanics (P10) | Phase 3 — Plugin-backend | Extract `paperforge-backend.js`; tests run in Node.js without Obsidian |
| Test layering conflicts (P11) | Phase 7 — CI integration | Truth hierarchy documented; mock validation test runs periodically |
| Windows path hell (P12) | Phase 4 + 7 — E2E + CI | Platform-specific tests marked; at least one Windows CI node; path normalization utilities |
| Fixture inheritance wrong (P13) | Phase 1 — Fixture hierarchy | Fixture hierarchy in conftest.py; lint added for heavy fixture usage in level 1 tests |

---

## Sources

- **Existing codebase analysis:** `tests/conftest.py` (fixture patterns), `tests/test_ocr_state_machine.py` (12-level mock nesting), `tests/test_e2e_cli.py` (subprocess testing), `tests/test_e2e_pipeline.py` (integration testing), `tests/test_plugin_install_bootstrap.py` (source-code matching). Confidence: HIGH.
- **Existing test suite:** 473+ tests across 39 test files; current patterns are mostly Level 1 units with a few Level 2 and Level 4 tests. The mock-heavy approach and single fixture reveal the pitfalls waiting to happen. Confidence: HIGH.
- **Pydantic inline-snapshot article (2026-02):** Snapshot testing with normalization, dirty-equals for dynamic fields, and the "assert specific shapes not whole files" principle. Confidence: HIGH.
- **pytest documentation:** Good integration practices, fixture scopes, `tmp_path`/`tmp_path_factory`, markers, and import modes. Confidence: HIGH.
- **CircleCI documentation:** Test splitting, parallelism strategies, and timing-based test distribution for CI matrix optimization. Confidence: MEDIUM (applies to GitHub Actions with pattern adaptation).
- **"Why Snapshot Testing Sucks" (2025-01):** Analysis of brittleness, coordination overhead, and recommendation for targeted behavior-driven assertions over whole-file snapshots. Confidence: HIGH.
- **pytest-with-eric.com (2024-2026):** Fixture management, temp directory strategies, test organization, flaky test stabilization — practical patterns for multi-layer test suites. Confidence: MEDIUM (community blog, but patterns are well-established).
- **Project version schema:** `paperforge/__init__.py`, `manifest.json`, `pyproject.toml` — multiple version sources with `bump.py` coordination. Confidence: HIGH.
- **Project constraints:** Windows compatibility requirement, junction/symlink differences, Chinese path handling, cross-platform CI target. Confidence: HIGH.
- **Previous milestone learnings:** v1.3 path normalization, v1.4 utility extraction, v1.9 frontmatter rationalization — each revealed testing blind spots. Confidence: HIGH.
- **Project architecture:** `.planning/ARCHITECTURE.md` — thin-shell plugin principle, canonical index, worker/agent split. Confidence: HIGH.

---

## What NOT to Test (Pragmatic Boundaries)

These are explicitly out of scope for the v2.0 testing infrastructure:

| Do NOT Test | Rationale | Alternative |
|-------------|-----------|-------------|
| Obsidian API behavior itself | Obsidian is a dependency, not our code. We can't control its behavior. | Test that our plugin correctly INTERPRETS Obsidian's API responses (mock Obsidian API) |
| PaddleOCR API accuracy | We're testing our integration, not OCR quality. | Test that we correctly handle the API's response format and error codes |
| Better BibTeX export correctness | BBT is a Zotero plugin, not our code. | Test that we correctly PARSE BBT's JSON output in all supported formats |
| JavaScript bundler behavior (if used) | Webpack/esbuild are build tools, not our application | Test the BUNDLED OUTPUT, not the bundler |
| Performance regression detection | Falls outside unit/E2E testing scope (needs dedicated benchmarking infrastructure) | Add `pytest-benchmark` markers but don't gate CI on them in v2.0 |
| Zotero's internal data structure | We read BBT's output, not Zotero's internals | Focus testing on BBT JSON parsing, not Zotero database state |
| Python 3.9 or lower | This project requires Python 3.10+ (per pyproject.toml) | Don't add CI nodes for unsupported Python versions |
| Obsidian's frontmatter parsing | Obsidian handles YAML frontmatter — we write valid YAML | Test that our YAML OUTPUT is valid and readable |
| Network latency/resilience of PaddleOCR | Not our infrastructure; we can't control it | Test that we handle timeout errors and retry correctly (mocked) |
| Air-gapped/offline mode | PaperForge requires PaddleOCR API access for full functionality | Focus on testing the internet-available path; offline behavior is a separate feature |

---

*Pitfalls research for: PaperForge v2.0 — Multi-Layer Testing Infrastructure (6-Level Quality Gates)*
*Researched: 2026-05-08*
*Research mode: Project Research — PITFALLS*
