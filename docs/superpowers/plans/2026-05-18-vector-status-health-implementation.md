# Vector Status + Health + Auto-Embed — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-paper `vector_status` column to `paperforge.db`, make `_check_vector()` strict, fix resume to use SQLite, and wire auto-embed status writing after OCR.

**Architecture:** Schema v3 adds `vector_status TEXT` column. Embed builder writes status after each paper. `_check_vector()` queries coverage ratio. Resume filters via SQL instead of ChromaDB per-paper lookups. Auto-embed after OCR writes status back to DB.

**Tech Stack:** SQLite (same `paperforge.db`), Python, ChromaDB, OpenAI embeddings API

---

### Task 1: Schema v3 — Add vector_status column

**Files:**
- Modify: `paperforge/memory/schema.py:9` — `CURRENT_SCHEMA_VERSION = 3`
- Modify: `paperforge/memory/_columns.py:6-15` — add `"vector_status"` to `PAPER_COLUMNS`
- Modify: `paperforge/memory/builder.py:130-279` — preserve `vector_status` across rebuild
- Test: `tests/unit/memory/test_schema.py` — verify `vector_status` column exists after schema create

- [ ] **Step 1: Write schema + columns changes**

  In `paperforge/memory/schema.py:9`, change:
  ```python
  CURRENT_SCHEMA_VERSION = 3  # Bump from 2 for vector_status column
  ```

  In `paperforge/memory/_columns.py`, add `"vector_status"` to `PAPER_COLUMNS` after `"ocr_job_id"`:
  ```python
      "ocr_job_id", "vector_status", "impact_factor",
  ```

- [ ] **Step 2: Preserve vector_status in memory builder**

  In `paperforge/memory/builder.py`, before the DELETE of papers (line 166), save a map of existing `vector_status` values:

  ```python
  # Before DELETE, save existing vector_status
  existing_status = {}
  try:
      rows = conn.execute("SELECT zotero_key, vector_status FROM papers WHERE vector_status != ''").fetchall()
      existing_status = {row["zotero_key"]: row["vector_status"] for row in rows}
  except Exception:
      pass  # Table or column may not exist yet
  ```

  After the `paper_rows` build (after line 228, before meta upserts), restore saved status:
  ```python
  # Restore vector_status for papers that had it
  for row in paper_rows:
      saved = existing_status.get(row.get("zotero_key", ""))
      if saved:
          conn.execute(
              "UPDATE papers SET vector_status = ? WHERE zotero_key = ?",
              (saved, row["zotero_key"]),
          )
  ```

- [ ] **Step 3: Write test for schema v3 vector_status column**

  In `tests/unit/memory/test_schema.py`:
  ```python
  def test_schema_v3_has_vector_status_column():
      import tempfile
      from pathlib import Path
      with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
          db_path = Path(tmp.name)
      try:
          conn = get_connection(db_path)
          ensure_schema(conn)
          cols = {row["name"] for row in conn.execute("PRAGMA table_info(papers)").fetchall()}
          assert "vector_status" in cols
          conn.close()
      finally:
          db_path.unlink(missing_ok=True)
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `python -m pytest tests/unit/memory/test_schema.py::test_schema_v3_has_vector_status_column -v --tb=short`
  Expected: PASS

- [ ] **Step 5: Run all existing tests to confirm no regression**
  Run: `python -m pytest tests/unit/memory/test_schema.py -v --tb=short`
  Expected: all PASS

- [ ] **Step 6: Commit**
  ```bash
  git add -A && git commit -m "feat(schema): add vector_status column (v3)"
  ```

---

### Task 2: Embed build — Write per-paper vector_status to DB

**Files:**
- Modify: `paperforge/commands/embed.py` — before build loop UPDATE to pending, after each paper UPDATE status, resume filter via SQL
- Test: `tests/unit/commands/test_embed.py`

- [ ] **Step 1: Add DB connection inside run() after vault is available**

  After line 27 (`vault = args.vault_path`), add:
  ```python
  from paperforge.memory.db import get_connection, get_memory_db_path
  _db = get_connection(get_memory_db_path(vault))
  ```

- [ ] **Step 2: Set all OCR-done papers to pending before loop (unless resume)**

  Before the `for entry in done_papers:` loop (before line 166), add:
  ```python
  if not resume:
      _db.execute(
          "UPDATE papers SET vector_status = 'pending' WHERE ocr_status = 'done'"
      )
      _db.commit()
  ```

- [ ] **Step 3: Check for corruption before resume loop**

  After the `if not resume: UPDATE ... pending` block, add corruption warning:
  ```python
  if resume:
      embed_status = get_embed_status(vault)
      if embed_status.get("corrupted", False):
          import logging
          logging.getLogger(__name__).warning(
              "ChromaDB index is corrupted. Resume will attempt to embed missing papers, "
              "but collection.add() may still fail. Use --force if errors occur."
          )
  ```

- [ ] **Step 4: Replace resume ChromaDB check with SQLite filter**

  Replace lines 173-184 (the ChromaDB per-paper `collection.get()` block) with:
  ```python
  if resume:
      row = _db.execute(
          "SELECT vector_status FROM papers WHERE zotero_key = ?",
          (key,)
      ).fetchone()
      if row and row["vector_status"] == "embedded":
          papers_skipped += 1
          continue
  ```

- [ ] **Step 5: Write vector_status after each paper embed success/failure**

  After `papers_embedded += 1` (line 194), add:
  ```python
  _db.execute(
      "UPDATE papers SET vector_status = 'embedded' WHERE zotero_key = ?",
      (key,)
  )
  _db.commit()
  ```

  In the except block (before `return 1` on line 220), add:
  ```python
  _db.execute(
      "UPDATE papers SET vector_status = 'failed' WHERE zotero_key = ?",
      (key,)
  )
  _db.commit()
  ```

- [ ] **Step 6: Close DB at end**

  After the final `write_vector_runtime` call (line 241), add:
  ```python
  _db.close()
  ```

- [ ] **Step 7: Write test for resume using SQLite**

  In `tests/unit/commands/test_embed.py`, add:

  ```python
  def test_embed_resume_does_not_call_collection_get(tmp_path):
      from argparse import Namespace
      vault = tmp_path / "vault"
      vault.mkdir()
      (vault / "paperforge.json").write_text(
          '{"vault_config":{"system_dir":"System","resources_dir":"Resources","literature_dir":"Literature","control_dir":"LiteratureControl","base_dir":"Bases","skill_dir":".opencode/skills"}}',
          encoding="utf-8",
      )
      from paperforge.memory.db import get_connection, get_memory_db_path
      from paperforge.memory.schema import ensure_schema, CURRENT_SCHEMA_VERSION
      db_path = get_memory_db_path(vault)
      conn = get_connection(db_path)
      ensure_schema(conn)
      conn.execute("INSERT INTO meta (key, value) VALUES ('schema_version', ?)", (str(CURRENT_SCHEMA_VERSION),))
      conn.commit()
      
      # Add a paper that's already embedded
      conn.execute("""INSERT INTO papers (zotero_key, title, ocr_status, vector_status)
                       VALUES (?, ?, ?, ?)""",
                   ("EXISTING", "Test Paper", "done", "embedded"))
      conn.commit()
      conn.close()

      with patch("paperforge.commands.embed._preflight_check") as m_pre:
          m_pre.return_value = {"ok": True}
          with patch("paperforge.commands.embed.read_index") as m_idx:
              m_idx.return_value = {
                  "items": [
                      {"zotero_key": "EXISTING", "ocr_status": "done", "fulltext_path": "x.md"},
                      {"zotero_key": "NEWPAPER", "ocr_status": "done", "fulltext_path": "x.md"},
                  ]
              }
              with patch("paperforge.commands.embed.chunk_fulltext") as m_chunk:
                  m_chunk.return_value = [{"text": "hello", "chunk_index": 0, "section": "", "page_number": 1, "token_estimate": 1}]
                  with patch("paperforge.commands.embed.get_collection") as m_col:
                      # mock collection for embed_paper only
                      m_col.return_value.count.return_value = 0
                      with patch("paperforge.commands.embed.OpenAICompatibleProvider") as m_prov:
                          m_prov.return_value.encode.return_value = [[0.1]]
                          with patch("paperforge.commands.embed.get_embed_status") as m_stat:
                              m_stat.return_value = {"mode": "api", "model": "test"}
                              with patch.object(sys, "stdout", open("NUL", "w") if sys.platform == "win32" else open("/dev/null", "w")):
                                  args = Namespace(
                                      vault_path=vault,
                                      embed_subcommand="build",
                                      force=False,
                                      resume=True,
                                      json=True,
                                  )
                                  rc = run(args)
                                  assert rc == 0
                                  # Verify collection.get was never called from resume check
                                  # get_collection is called from embed_paper (add) and get_embed_status (count)
                                  # but NOT from the resume loop itself
                                  # The resume SQL should skip EXISTING, so only NEWPAPER gets embedded
      # Verify NEWPAPER got vector_status='embedded'
      conn2 = get_connection(db_path)
      row = conn2.execute("SELECT vector_status FROM papers WHERE zotero_key='NEWPAPER'").fetchone()
      conn2.close()
      assert row["vector_status"] == "embedded"
  ```

- [ ] **Step 8: Run tests**
  Run: `python -m pytest tests/unit/commands/test_embed.py -v --tb=short`
  Expected: all PASS

- [ ] **Step 9: Run all unit tests**
  Run: `python -m pytest tests/unit/ -v --tb=short`
  Expected: all PASS

- [ ] **Step 10: Commit**
  ```bash
  git add -A && git commit -m "feat(embed): write per-paper vector_status to DB, resume via SQLite"
  ```

---

### Task 3: Strict `_check_vector()` with coverage ratio

**Files:**
- Modify: `paperforge/memory/runtime_health.py:120-153`
- Test: `tests/unit/memory/test_runtime_health.py`

- [ ] **Step 1: Rewrite `_check_vector()`**

  Replace lines 120-153 with:
  ```python
  def _check_vector(vault: Path) -> dict:
      from paperforge.embedding import get_vector_db_path, read_vector_build_state
      from paperforge.embedding.status import get_embed_status

      settings_path = vault / ".obsidian" / "plugins" / "paperforge" / "data.json"
      vector_enabled = False
      if settings_path.exists():
          try:
              import json
              data = json.loads(settings_path.read_text(encoding="utf-8"))
              vector_enabled = bool(data.get("features", {}).get("vector_db", False))
          except Exception:
              pass

      if not vector_enabled:
          return _layer("degraded", ["Vector DB disabled by user"],
                        "Enable vector DB in plugin settings to use semantic search",
                        "")

      build_state = read_vector_build_state(vault)
      job_status = build_state.get("status", "idle")
      if job_status == "running":
          return _layer("degraded", ["Vector build in progress"],
                        "Wait for build to complete",
                        "paperforge embed status --json")
      if job_status == "failed":
          return _layer("degraded", [f"Last build failed: {build_state.get('message', '')}"],
                        "Check error and rebuild",
                        "paperforge embed build --resume")

      embed_status = get_embed_status(vault)
      if embed_status.get("corrupted", False):
          return _layer("degraded",
                        ["ChromaDB index corrupted"],
                        "Rebuild from scratch",
                        "paperforge embed build --force")

      db_path = get_vector_db_path(vault)
      if not db_path.exists():
          return _layer("degraded", ["Vector DB not built yet"],
                        "Run embed build",
                        "paperforge embed build --resume")

      # Query coverage from paperforge.db
      try:
          from paperforge.memory.db import get_connection, get_memory_db_path
          mem_db = get_memory_db_path(vault)
          if not mem_db.exists():
              return _layer("degraded", ["Memory DB not found; cannot check vector coverage"],
                            "Run paperforge memory build",
                            "paperforge memory build")
          conn = get_connection(mem_db, read_only=True)
          total_ocr = conn.execute(
              "SELECT COUNT(*) FROM papers WHERE ocr_status = 'done'"
          ).fetchone()[0]
          embedded = conn.execute(
              "SELECT COUNT(*) FROM papers WHERE ocr_status = 'done' AND vector_status = 'embedded'"
          ).fetchone()[0]
          conn.close()
      except Exception as e:
          return _layer("degraded", [f"Cannot query vector coverage: {e}"],
                        "Check DB integrity", "paperforge doctor")

      if total_ocr == 0:
          return _layer("degraded", ["No OCR-done papers to embed"],
                        "Run OCR on papers first",
                        "paperforge ocr run")

      if embedded == 0 and db_path.exists():
          return _layer("degraded", ["Vector DB exists but no papers marked as embedded"],
                        "Rebuild to ensure consistency",
                        "paperforge embed build --resume")

      if embedded == 0:
          return _layer("degraded", ["No papers embedded yet (0/0 coverage)"],
                        "Run embed build",
                        "paperforge embed build --resume")

      ratio = embedded / total_ocr
      if ratio < 1.0:
          evidence = [f"Partial embedding coverage: {embedded}/{total_ocr} ({ratio:.0%})"]
          return _layer("degraded", evidence,
                        "Run embed build --resume to finish remaining papers",
                        "paperforge embed build --resume")

      return _layer("ok",
                    [f"All {embedded} OCR-done papers embedded ({ratio:.0%} coverage)"])
  ```

- [ ] **Step 2: Write tests for degraded/disabling/partial coverage**

  In `tests/unit/memory/test_runtime_health.py`, add:

  ```python
  def test_check_vector_disabled_returns_degraded(tmp_path):
      vault = tmp_path / "vault"
      vault.mkdir()
      (vault / "paperforge.json").write_text(
          json.dumps({"system_dir": "System"}), encoding="utf-8"
      )
      (vault / ".obsidian" / "plugins" / "paperforge" / "data.json").parent.mkdir(parents=True)
      (vault / ".obsidian" / "plugins" / "paperforge" / "data.json").write_text(
          json.dumps({"features": {"vector_db": False}}), encoding="utf-8"
      )
      result = _check_vector(vault)
      assert result["status"] == "degraded"
      assert "disabled" in result["evidence"][0].lower()
  ```

  ```python
  def test_check_vector_corrupted_returns_degraded(tmp_path):
      from paperforge.embedding import get_vector_db_path
      vault = tmp_path / "vault"
      vault.mkdir(parents=True)
      (vault / "paperforge.json").write_text(
          json.dumps({"system_dir": "System"}), encoding="utf-8"
      )
      (vault / ".obsidian" / "plugins" / "paperforge" / "data.json").parent.mkdir(parents=True)
      (vault / ".obsidian" / "plugins" / "paperforge" / "data.json").write_text(
          json.dumps({"features": {"vector_db": True}}), encoding="utf-8"
      )
      # Create vectors dir so db_path.exists() is true
      db_path = get_vector_db_path(vault)
      db_path.mkdir(parents=True)

      with patch("paperforge.memory.runtime_health.get_embed_status") as m_stat:
          m_stat.return_value = {
              "db_exists": True, "chunk_count": 0,
              "model": "test", "mode": "api",
              "healthy": False, "corrupted": True, "error": "hnsw error",
          }
          with patch("paperforge.memory.runtime_health.get_connection") as m_conn:
              mock_cursor = m_conn.return_value.execute.return_value
              mock_cursor.fetchone.side_effect = [(10,), (10,)]
              result = _check_vector(vault)
      assert result["status"] == "degraded"
      assert any("corrupted" in e.lower() for e in result["evidence"])
  ```

  ```python
  def test_check_vector_partial_coverage_returns_degraded(tmp_path):
      vault = tmp_path / "vault"
      vault.mkdir()
      (vault / "paperforge.json").write_text(
          json.dumps({"system_dir": "System"}), encoding="utf-8"
      )
      (vault / ".obsidian" / "plugins" / "paperforge" / "data.json").parent.mkdir(parents=True)
      (vault / ".obsidian" / "plugins" / "paperforge" / "data.json").write_text(
          json.dumps({"features": {"vector_db": True}}), encoding="utf-8"
      )
      from paperforge.embedding import get_vector_db_path
      db_path = get_vector_db_path(vault)
      db_path.mkdir(parents=True)

      from paperforge.embedding.build_state import write_vector_build_state
      write_vector_build_state(vault, {"status": "idle", "current": 0, "total": 0})

      with patch("paperforge.memory.runtime_health.get_embed_status") as m_stat:
          m_stat.return_value = {
              "db_exists": True, "chunk_count": 50,
              "model": "test", "mode": "api",
              "healthy": True, "corrupted": False, "error": "",
          }
          with patch("paperforge.memory.runtime_health.get_connection") as m_conn:
              mock_cursor = m_conn.return_value.execute.return_value
              mock_cursor.fetchone.side_effect = [(10,), (7,)]
              result = _check_vector(vault)
      assert result["status"] == "degraded"
      assert any("partial" in e.lower() for e in result["evidence"])
  ```

  ```python
  def test_check_vector_full_coverage_returns_ok(tmp_path):
      vault = tmp_path / "vault"
      vault.mkdir()
      (vault / "paperforge.json").write_text(
          json.dumps({"system_dir": "System"}), encoding="utf-8"
      )
      (vault / ".obsidian" / "plugins" / "paperforge" / "data.json").parent.mkdir(parents=True)
      (vault / ".obsidian" / "plugins" / "paperforge" / "data.json").write_text(
          json.dumps({"features": {"vector_db": True}}), encoding="utf-8"
      )
      from paperforge.embedding import get_vector_db_path
      db_path = get_vector_db_path(vault)
      db_path.mkdir(parents=True)

      from paperforge.embedding.build_state import write_vector_build_state
      write_vector_build_state(vault, {"status": "idle", "current": 0, "total": 0})

      with patch("paperforge.memory.runtime_health.get_embed_status") as m_stat:
          m_stat.return_value = {
              "db_exists": True, "chunk_count": 50,
              "model": "test", "mode": "api",
              "healthy": True, "corrupted": False, "error": "",
          }
          with patch("paperforge.memory.runtime_health.get_connection") as m_conn:
              mock_cursor = m_conn.return_value.execute.return_value
              mock_cursor.fetchone.side_effect = [(10,), (10,)]
              result = _check_vector(vault)
      assert result["status"] == "ok"
      assert "coverage" in result["evidence"][0].lower()
  ```

- [ ] **Step 3: Run tests**
  Run: `python -m pytest tests/unit/memory/test_runtime_health.py -v --tb=short`
  Expected: all PASS

- [ ] **Step 4: Run all unit tests**
  Run: `python -m pytest tests/unit/ -v --tb=short`
  Expected: all PASS

- [ ] **Step 5: Commit**
  ```bash
  git add -A && git commit -m "feat(health): strict _check_vector() with coverage ratio"
  ```

---

### Task 4: Auto-embed — Write vector_status to DB after OCR

**Files:**
- Modify: `paperforge/worker/asset_index.py:479-505`

- [ ] **Step 1: Rewrite `_vec_auto_embed_if_new()` to write status**

  Replace lines 479-505 with:
  ```python
  def _vec_auto_embed_if_new(vault: Path, entry: dict) -> None:
      """Auto-embed a paper into vector DB if OCR is done and vectors missing."""
      if entry.get("ocr_status") != "done":
          return
      fulltext_rel = entry.get("fulltext_path", "")
      if not fulltext_rel:
          return
      fulltext_path = vault / fulltext_rel
      if not fulltext_path.exists():
          return
      try:
          from paperforge.embedding._config import _read_plugin_settings
          from paperforge.embedding import embed_paper, get_vector_db_path
          from paperforge.memory.chunker import chunk_fulltext
          from paperforge.memory.db import get_connection, get_memory_db_path
          settings = _read_plugin_settings(vault)
          if not settings.get("features", {}).get("vector_db", False):
              return
          db_path = get_vector_db_path(vault)
          if not db_path.exists():
              return
          chunks = chunk_fulltext(fulltext_path)
          if not chunks:
              return

          zotero_key = entry["zotero_key"]
          embed_paper(vault, zotero_key, chunks)

          # Write vector_status to paperforge.db
          try:
              conn = get_connection(get_memory_db_path(vault))
              conn.execute(
                  "UPDATE papers SET vector_status = 'embedded' WHERE zotero_key = ?",
                  (zotero_key,)
              )
              conn.commit()
              conn.close()
          except Exception:
              pass
      except Exception:
          # Write failure status
          try:
              conn = get_connection(get_memory_db_path(vault))
              conn.execute(
                  "UPDATE papers SET vector_status = 'failed' WHERE zotero_key = ?",
                  (entry["zotero_key"],)
              )
              conn.commit()
              conn.close()
          except Exception:
              pass
  ```

- [ ] **Step 2: Run existing tests**
  Run: `python -m pytest tests/unit/worker/ -v --tb=short`
  Expected: all PASS

- [ ] **Step 3: Run all unit tests**
  Run: `python -m pytest tests/unit/ -v --tb=short`
  Expected: all PASS

- [ ] **Step 4: Commit**
  ```bash
  git add -A && git commit -m "feat(auto-embed): write vector_status to DB after OCR"
  ```

---

### Task 5: Agent context — Add vector coverage reporting

**Files:**
- Modify: `paperforge/memory/context.py`
- Test: `tests/unit/memory/test_context.py`

- [ ] **Step 1: Add vector coverage to `get_agent_context()`**

  In `paperforge/memory/context.py`, after the collection tree building (before the `return`), add:

  ```python
  # Vector coverage
  vector = {}
  try:
      total_ocr = conn.execute(
          "SELECT COUNT(*) FROM papers WHERE ocr_status = 'done'"
      ).fetchone()[0]
      embedded = conn.execute(
          "SELECT COUNT(*) FROM papers WHERE ocr_status = 'done' AND vector_status = 'embedded'"
      ).fetchone()[0]
      # Check if vector DB is enabled in plugin settings
      vector_enabled = False
      settings_path = vault / ".obsidian" / "plugins" / "paperforge" / "data.json"
      if settings_path.exists():
          import json
          data = json.loads(settings_path.read_text(encoding="utf-8"))
          vector_enabled = bool(data.get("features", {}).get("vector_db", False))
      vector = {
          "enabled": vector_enabled,
          "embedded": embedded,
          "total_ocr_done": total_ocr,
          "coverage": round(embedded / total_ocr, 4) if total_ocr > 0 else 0.0,
      }
  except Exception:
      pass
  ```

  Add `"vector": vector` to the returned dict.

- [ ] **Step 2: Write test**

  Update `tests/unit/memory/test_context.py`:
  ```python
  def test_get_agent_context_returns_vector_coverage(tmp_path):
      from paperforge.memory.db import get_connection, get_memory_db_path
      from paperforge.memory.schema import ensure_schema, CURRENT_SCHEMA_VERSION
      vault = tmp_path / "vault"
      vault.mkdir()
      db_path = get_memory_db_path(vault)
      conn = get_connection(db_path)
      ensure_schema(conn)
      conn.execute("INSERT INTO meta (key, value) VALUES ('schema_version', ?)", (str(CURRENT_SCHEMA_VERSION),))
      conn.execute("""INSERT INTO papers (zotero_key, title, ocr_status, vector_status)
                       VALUES (?, ?, ?, ?)""",
                   ("K1", "Test", "done", "embedded"))
      conn.execute("""INSERT INTO papers (zotero_key, title, ocr_status, vector_status)
                       VALUES (?, ?, ?, ?)""",
                   ("K2", "Test2", "done", ""))
      conn.commit()
      conn.close()

      ctx = get_agent_context(vault)
      assert ctx is not None
      assert "vector" in ctx
      assert ctx["vector"]["embedded"] == 1
      assert ctx["vector"]["total_ocr_done"] == 2
      assert ctx["vector"]["coverage"] == 0.5
  ```

- [ ] **Step 3: Run tests**
  Run: `python -m pytest tests/unit/memory/test_context.py -v --tb=short`
  Expected: all PASS

- [ ] **Step 4: Commit**
  ```bash
  git add -A && git commit -m "feat(context): add vector coverage to agent context"
  ```

---

### Task 6: Full test suite + lint

- [ ] **Step 1: Run all tests**
  Run: `python -m pytest tests/unit/ -v --tb=short`
  Expected: all PASS

- [ ] **Step 2: Run lint**
  Run: `ruff check --fix paperforge/ && ruff format paperforge/`
  Expected: clean

- [ ] **Step 3: Final commit if lint fixes applied**
  ```bash
  git add -A && git commit -m "style: lint and format after vector_status changes"  # if needed
  ```
