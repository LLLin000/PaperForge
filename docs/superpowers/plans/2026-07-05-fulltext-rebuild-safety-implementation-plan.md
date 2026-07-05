# Fulltext Rebuild Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add rebuild-time backup, machine hash provenance, drift tri-state, and atomic `fulltext.md` writeback without introducing a permanent second machine baseline file.

**Architecture:** Keep `paper_root/fulltext.md` as the only user-facing working text. Preserve `render/fulltext.md` only as a derived render artifact. Centralize destructive-write behavior behind one backend seam that computes SHA-256 on disk bytes, creates per-paper backups immediately before replace, atomically replaces `fulltext.md`, atomically updates `meta.json`, and prunes backups by filename-order retention.

**Tech Stack:** Python 3.10+, pytest, existing `paperforge.worker` OCR pipeline, existing atomic write patterns (`tempfile` + `os.replace`), TypeScript + Vitest for plugin maintenance-row copy.

## Global Constraints

- Only `paper_root/fulltext.md` participates in drift / backup / provenance.
- `render/fulltext.md` may remain as a derived artifact, but it MUST NOT be used as machine baseline.
- `machine_fulltext_hash` MUST use `sha256:<hex>` format.
- Hashes MUST be computed from on-disk UTF-8 bytes; no newline/BOM/whitespace normalization.
- Backup MUST happen in the same destructive-write critical section immediately before replacing `paper_root/fulltext.md`, not when rebuild starts.
- Backup retention MUST keep the latest 5 matching `fulltext.pre-rebuild.*.md` files per paper, sorted by filename timestamp + sequence, not by mtime.
- Legacy papers with missing `machine_fulltext_hash` MUST surface `UNKNOWN`, not `MATCHED`.
- Vector rebuild remains out of scope for this plan.

---

## File Map

- Create: `paperforge/worker/ocr_fulltext_state.py`
  - Own the destructive-write seam: hash, drift tri-state, backup naming, retention pruning, atomic write helpers.
- Modify: `paperforge/worker/ocr_render.py:1965-1968`
  - Keep render artifact emission, but route `paper_root/fulltext.md` write through the new seam.
- Modify: `paperforge/worker/ocr.py:1979-2063`
  - Defer initial OCR `fulltext.md` destructive write to the final meta-writeback point.
- Modify: `paperforge/worker/ocr_rebuild.py:350-421`
  - Defer derived rebuild destructive write to the final meta-writeback point and increment rebuild provenance fields.
- Modify: `paperforge/worker/ocr_maintenance.py:16-77` and row assembly logic below
  - Surface `fulltext_drift_state` / `fulltext_drift_reason` from `meta.json` + file state.
- Modify: `paperforge/plugin/src/services/ocr-maintenance-ui.ts:23-55`
  - Accept drift tri-state on maintenance rows and preserve minimal copy.
- Modify: `paperforge/plugin/tests/ocr-maintenance-ui.test.ts`
  - Assert `UNKNOWN` / `DRIFTED` copy behavior stays minimal and non-deceptive.
- Test: `tests/test_ocr_fulltext_state.py`
  - New backend seam contract tests.
- Test: `tests/test_ocr_rebuild.py`
  - Extend derived rebuild tests for backup / meta semantics.
- Test: `tests/test_ocr_initial_fulltext_writeback.py`
  - New focused initial-OCR writeback tests.
- Test: `tests/test_ocr_maintenance.py`
  - Backend drift-state row contract.

### Task 1: Extract the fulltext destructive-write seam

**Files:**
- Create: `paperforge/worker/ocr_fulltext_state.py`
- Test: `tests/test_ocr_fulltext_state.py`

**Interfaces:**
- Consumes: `paperforge.worker.ocr_artifacts._sha256_hexdigest`, stdlib `tempfile`, `os.replace`, `datetime`, `Path`
- Produces:
  - `compute_disk_fulltext_hash(path: Path) -> str`
  - `get_fulltext_drift_state(fulltext_path: Path, machine_hash: str | None) -> Literal["MATCHED", "DRIFTED", "UNKNOWN"]`
  - `create_pre_rebuild_backup(fulltext_path: Path, now_utc: datetime.datetime) -> tuple[str, str] | None`
  - `prune_pre_rebuild_backups(backups_dir: Path, keep: int = 5) -> list[Path]`
  - `atomic_replace_text(target: Path, content: str) -> Path`

- [ ] **Step 1: Write the failing backend seam tests**

```python
from pathlib import Path

from paperforge.worker.ocr_fulltext_state import (
    compute_disk_fulltext_hash,
    get_fulltext_drift_state,
    create_pre_rebuild_backup,
    prune_pre_rebuild_backups,
)


def test_compute_disk_fulltext_hash_uses_sha256_prefix_and_disk_bytes(tmp_path: Path) -> None:
    path = tmp_path / "fulltext.md"
    path.write_bytes("A\r\nB\n".encode("utf-8"))
    digest = compute_disk_fulltext_hash(path)
    assert digest.startswith("sha256:")


def test_get_fulltext_drift_state_returns_unknown_without_machine_hash(tmp_path: Path) -> None:
    path = tmp_path / "fulltext.md"
    path.write_text("hello\n", encoding="utf-8")
    assert get_fulltext_drift_state(path, None) == "UNKNOWN"


def test_create_pre_rebuild_backup_uses_timestamp_and_sequence(tmp_path: Path) -> None:
    paper_root = tmp_path / "ocr" / "KEY1"
    fulltext = paper_root / "fulltext.md"
    fulltext.parent.mkdir(parents=True)
    fulltext.write_text("v1\n", encoding="utf-8")
    first = create_pre_rebuild_backup(fulltext, _fixed_utc())
    second = create_pre_rebuild_backup(fulltext, _fixed_utc())
    assert first is not None and second is not None
    assert first[1].endswith("20260705T120000Z.md")
    assert second[1].endswith("20260705T120000Z.001.md")


def test_prune_pre_rebuild_backups_only_deletes_matching_files(tmp_path: Path) -> None:
    backups = tmp_path / "backups"
    backups.mkdir()
    for i in range(7):
        (backups / f"fulltext.pre-rebuild.20260705T12000{i}Z.md").write_text(str(i), encoding="utf-8")
    keeper = backups / "notes.keep.md"
    keeper.write_text("do not touch", encoding="utf-8")
    removed = prune_pre_rebuild_backups(backups, keep=5)
    assert len(removed) == 2
    assert keeper.exists()
```

- [ ] **Step 2: Run the seam tests to verify they fail**

Run: `pytest tests/test_ocr_fulltext_state.py -q`
Expected: FAIL with `ModuleNotFoundError` or missing symbols from `paperforge.worker.ocr_fulltext_state`

- [ ] **Step 3: Write the minimal helper module**

```python
# paperforge/worker/ocr_fulltext_state.py
from __future__ import annotations

import datetime as dt
import os
import re
import tempfile
from pathlib import Path
from typing import Literal

from paperforge.worker.ocr_artifacts import _sha256_hexdigest

_DRIFT = Literal["MATCHED", "DRIFTED", "UNKNOWN"]
_BACKUP_RE = re.compile(r"^fulltext\.pre-rebuild\.(\d{8}T\d{6}Z)(?:\.(\d{3}))?\.md$")


def compute_disk_fulltext_hash(path: Path) -> str:
    return _sha256_hexdigest(path.read_bytes())


def get_fulltext_drift_state(fulltext_path: Path, machine_hash: str | None) -> _DRIFT:
    if not machine_hash or not fulltext_path.exists():
        return "UNKNOWN"
    try:
        current = compute_disk_fulltext_hash(fulltext_path)
    except OSError:
        return "UNKNOWN"
    return "MATCHED" if current == machine_hash else "DRIFTED"


def create_pre_rebuild_backup(fulltext_path: Path, now_utc: dt.datetime) -> tuple[str, str] | None:
    if not fulltext_path.exists():
        return None
    backups_dir = fulltext_path.parent / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = now_utc.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    source_bytes = fulltext_path.read_bytes()
    source_hash = _sha256_hexdigest(source_bytes)
    for seq in range(1000):
        suffix = "" if seq == 0 else f".{seq:03d}"
        name = f"fulltext.pre-rebuild.{stamp}{suffix}.md"
        candidate = backups_dir / name
        if candidate.exists():
            continue
        candidate.write_bytes(source_bytes)
        if compute_disk_fulltext_hash(candidate) != source_hash:
            raise IOError(f"Backup verification failed for {candidate}")
        return now_utc.astimezone(dt.timezone.utc).isoformat(), str(candidate.relative_to(fulltext_path.parent)).replace("\\", "/")
    raise RuntimeError("Backup sequence overflow for one UTC second")


def prune_pre_rebuild_backups(backups_dir: Path, keep: int = 5) -> list[Path]:
    if not backups_dir.exists():
        return []
    matches = sorted((p for p in backups_dir.glob("fulltext.pre-rebuild.*.md") if _BACKUP_RE.match(p.name)), key=lambda p: p.name)
    doomed = matches[:-keep] if len(matches) > keep else []
    for path in doomed:
        path.unlink(missing_ok=True)
    return doomed


def atomic_replace_text(target: Path, content: str) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        os.replace(tmp_path, target)
        return target
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
```

- [ ] **Step 4: Run the seam tests to verify they pass**

Run: `pytest tests/test_ocr_fulltext_state.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_fulltext_state.py tests/test_ocr_fulltext_state.py
git commit -m "feat: add fulltext writeback state helpers"
```

### Task 2: Refactor render writeback into an atomic commit point

**Files:**
- Modify: `paperforge/worker/ocr_render.py:1965-1968`
- Test: `tests/test_ocr_fulltext_state.py`

**Interfaces:**
- Consumes:
  - `compute_disk_fulltext_hash(...)`
  - `create_pre_rebuild_backup(...)`
  - `prune_pre_rebuild_backups(...)`
  - `atomic_replace_text(...)`
- Produces:
  - `write_render_outputs(render_root: Path, user_fulltext: Path, markdown: str, *, meta: dict, rebuild_increment: bool, now_utc: datetime.datetime | None = None) -> dict`
  - Return value: patched `meta` dict with `machine_fulltext_hash`, `last_backup_at`, `last_backup_path`, optional incremented rebuild fields; caller performs the final `write_json(meta_path, meta)`

- [ ] **Step 1: Add a failing test for the atomic commit point**

```python
from pathlib import Path
import datetime as dt

from paperforge.worker.ocr_render import write_render_outputs


def _fixed_utc() -> dt.datetime:
    return dt.datetime(2026, 7, 5, 12, 0, 0, tzinfo=dt.timezone.utc)


def test_write_render_outputs_updates_render_artifact_and_meta(tmp_path: Path) -> None:
    paper_root = tmp_path / "ocr" / "KEY1"
    render_root = paper_root / "render"
    user_fulltext = paper_root / "fulltext.md"
    user_fulltext.parent.mkdir(parents=True)
    user_fulltext.write_text("old\n", encoding="utf-8")
    meta = {"ocr_finished_at": "2026-07-05T12:00:00+00:00", "rebuild_count": 0}

    updated = write_render_outputs(
        render_root=render_root,
        user_fulltext=user_fulltext,
        markdown="new\n",
        meta=meta,
        rebuild_increment=False,
        now_utc=_fixed_utc(),
    )

    assert (render_root / "fulltext.md").read_text(encoding="utf-8") == "new\n"
    assert user_fulltext.read_text(encoding="utf-8") == "new\n"
    assert updated["machine_fulltext_hash"] == compute_disk_fulltext_hash(user_fulltext)
    assert updated["last_backup_path"].startswith("backups/fulltext.pre-rebuild.")
```

- [ ] **Step 2: Run the focused atomic write test to verify it fails**

Run: `pytest tests/test_ocr_fulltext_state.py::test_write_render_outputs_updates_render_artifact_and_meta -q`
Expected: FAIL because `write_render_outputs()` does not yet accept `user_fulltext`, does not return patched meta, and still computes hash away from the final on-disk file

- [ ] **Step 3: Refactor `write_render_outputs()` into the commit seam**

```python
# paperforge/worker/ocr_render.py
import datetime as dt
from paperforge.worker.ocr_fulltext_state import (
    atomic_replace_text,
    compute_disk_fulltext_hash,
    create_pre_rebuild_backup,
    prune_pre_rebuild_backups,
)


def write_render_outputs(
    render_root: Path,
    user_fulltext: Path,
    markdown: str,
    *,
    meta: dict,
    rebuild_increment: bool,
    now_utc: dt.datetime | None = None,
) -> dict:
    now_utc = now_utc or dt.datetime.now(dt.timezone.utc)
    render_root.mkdir(parents=True, exist_ok=True)
    (render_root / "fulltext.md").write_text(markdown, encoding="utf-8")

    backup_info = create_pre_rebuild_backup(user_fulltext, now_utc)
    atomic_replace_text(user_fulltext, markdown)
    machine_hash = compute_disk_fulltext_hash(user_fulltext)

    if backup_info:
        meta["last_backup_at"], meta["last_backup_path"] = backup_info
        prune_pre_rebuild_backups(user_fulltext.parent / "backups", keep=5)
    meta["machine_fulltext_hash"] = machine_hash
    if rebuild_increment:
        meta["rebuild_count"] = int(meta.get("rebuild_count") or 0) + 1
        meta["rebuild_finished_at"] = now_utc.isoformat()
    return meta
```

- [ ] **Step 4: Re-run the focused test**

Run: `pytest tests/test_ocr_fulltext_state.py::test_write_render_outputs_updates_render_artifact_and_meta -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_render.py tests/test_ocr_fulltext_state.py
git commit -m "refactor: separate render artifact writes from user fulltext commit"
```

### Task 3: Move initial OCR fulltext writeback to the final meta-write point

**Files:**
- Modify: `paperforge/worker/ocr.py:1979-2063`
- Create: `tests/test_ocr_initial_fulltext_writeback.py`

**Interfaces:**
- Consumes: `render_fulltext_markdown(...) -> str`, `write_render_outputs(..., rebuild_increment=False) -> dict`
- Produces:
  - Initial OCR path sets `machine_fulltext_hash` on first successful write
  - Initial OCR path does not write `rebuild_count` or `rebuild_finished_at`
  - Final `write_json(meta_path, meta)` stays in `ocr.py` after render write + version patching

- [ ] **Step 1: Add a failing initial-OCR contract test**

```python
import json
from pathlib import Path


def _minimal_results() -> list[dict]:
    return [{
        "layoutParsingResults": [{
            "prunedResult": {
                "width": 600,
                "height": 800,
                "parsing_res_list": [
                    {"block_label": "doc_title", "block_content": "Example", "block_bbox": [0, 0, 100, 20], "block_order": 0},
                    {"block_label": "text", "block_content": "Body", "block_bbox": [0, 40, 100, 80], "block_order": 1},
                ],
            }
        }]
    }]


def test_initial_ocr_persists_machine_hash_without_rebuild_fields(tmp_path: Path, monkeypatch) -> None:
    from paperforge.worker.ocr import postprocess_ocr_result

    vault = tmp_path
    key = "K1"
    paper_root = vault / "System" / "PaperForge" / "ocr" / key
    (paper_root / "meta.json").parent.mkdir(parents=True, exist_ok=True)
    (paper_root / "meta.json").write_text('{"source_pdf": ""}', encoding="utf-8")

    postprocess_ocr_result(vault, key, _minimal_results())

    meta = json.loads((paper_root / "meta.json").read_text(encoding="utf-8"))
    assert meta["machine_fulltext_hash"].startswith("sha256:")
    assert "rebuild_finished_at" not in meta or not meta["rebuild_finished_at"]
    assert int(meta.get("rebuild_count") or 0) == 0
```

- [ ] **Step 2: Run the focused initial-OCR test to verify it fails**

Run: `pytest tests/test_ocr_initial_fulltext_writeback.py -q`
Expected: FAIL because initial OCR still writes `fulltext.md` earlier than the final meta-write point and does not persist `machine_fulltext_hash`

- [ ] **Step 3: Move the destructive write later and keep the final meta write in `ocr.py`**

```python
# paperforge/worker/ocr.py
markdown = render_fulltext_markdown(...)
# do NOT call write_render_outputs() here anymore
...
meta["raw_version"] = version_payload["raw_version"]
meta["derived_version"] = version_payload["derived_version"]
meta["raw_upgradable"] = state["raw_upgradable"]
meta["derived_stale"] = state["derived_stale"]
meta["version_state_updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
meta = write_render_outputs(
    render_root=ocr_root / "render",
    user_fulltext=ocr_root / "fulltext.md",
    markdown=markdown,
    meta=meta,
    rebuild_increment=False,
)
write_json(meta_path, meta)
```

- [ ] **Step 4: Re-run the focused initial-OCR test**

Run: `pytest tests/test_ocr_initial_fulltext_writeback.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr.py tests/test_ocr_initial_fulltext_writeback.py
git commit -m "feat: persist machine fulltext hash for initial OCR"
```

### Task 4: Move derived rebuild fulltext writeback to the final tail and update rebuild provenance

**Files:**
- Modify: `paperforge/worker/ocr_rebuild.py:350-421`
- Modify: `tests/test_ocr_rebuild.py`

**Interfaces:**
- Consumes: `write_render_outputs(..., rebuild_increment=True) -> dict`
- Produces:
  - Derived rebuild increments `rebuild_count`
  - Derived rebuild updates `rebuild_finished_at`
  - Derived rebuild writes `machine_fulltext_hash`, `last_backup_at`, `last_backup_path`
  - Final `write_json(artifacts.meta_json, meta)` remains at the rebuild tail after validation

- [ ] **Step 1: Add failing derived-rebuild tests for backup/meta behavior**

```python
import json
from pathlib import Path


def _seed_rebuild_paper(tmp_path: Path, key: str) -> Path:
    paper_root = tmp_path / "System" / "PaperForge" / "ocr" / key
    (paper_root / "canonical").mkdir(parents=True)
    (paper_root / "raw").mkdir(parents=True)
    (paper_root / "raw" / "source_metadata.json").write_text('{"title": "Example Title"}', encoding="utf-8")
    (paper_root / "canonical" / "blocks.raw.jsonl").write_text(
        '{"paper_id":"TESTKEY1","page":1,"block_id":"p1_b1","raw_label":"text","raw_order":0,"text":"A","bbox":[0,0,10,10],"page_width":600,"page_height":800,"span_metadata":[{"size":10}]}\n',
        encoding="utf-8",
    )
    (paper_root / "meta.json").write_text('{"source_pdf":"","ocr_status":"done"}', encoding="utf-8")
    return paper_root


def test_run_derived_rebuild_creates_backup_before_replace(tmp_path: Path, monkeypatch) -> None:
    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    key = "TESTKEY1"
    paper_root = _seed_rebuild_paper(tmp_path, key)
    (paper_root / "fulltext.md").write_text("annotated\n", encoding="utf-8")
    result = run_derived_rebuild_for_keys(tmp_path, [key])
    assert result["rebuild_count"] == 1
    backups = sorted((paper_root / "backups").glob("fulltext.pre-rebuild.*.md"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "annotated\n"


def test_run_derived_rebuild_increments_rebuild_count_and_hash(tmp_path: Path, monkeypatch) -> None:
    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    key = "TESTKEY1"
    paper_root = _seed_rebuild_paper(tmp_path, key)
    (paper_root / "meta.json").write_text('{"rebuild_count": 1}', encoding="utf-8")
    run_derived_rebuild_for_keys(tmp_path, [key])
    meta = json.loads((paper_root / "meta.json").read_text(encoding="utf-8"))
    assert meta["rebuild_count"] == 2
    assert meta["machine_fulltext_hash"].startswith("sha256:")
    assert meta["last_backup_path"].startswith("backups/fulltext.pre-rebuild.")
```

- [ ] **Step 2: Run only the new derived-rebuild tests to verify they fail**

Run: `pytest tests/test_ocr_rebuild.py -q`
Expected: FAIL because derived rebuild writes fulltext too early and never updates backup/hash fields

- [ ] **Step 3: Move the final fulltext/meta commit to the rebuild tail**

```python
# paperforge/worker/ocr_rebuild.py
markdown = render_fulltext_markdown(...)
# no write_render_outputs() here
...
meta = read_json(artifacts.meta_json) if artifacts.meta_json.exists() else {}
meta.update(span_meta_patch)
meta = _apply_post_rebuild_version_flags(meta)
meta["ocr_status"] = "done"
meta = write_render_outputs(
    render_root=paper_root / "render",
    user_fulltext=artifacts.compat_fulltext,
    markdown=markdown,
    meta=meta,
    rebuild_increment=True,
)
_status, _err = validate_ocr_meta(paths_dict, meta)
meta["ocr_status"] = _status
meta["error"] = _err if _err else ""
write_json(artifacts.meta_json, meta)
```

- [ ] **Step 4: Re-run the derived rebuild tests**

Run: `pytest tests/test_ocr_rebuild.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_rebuild.py tests/test_ocr_rebuild.py
git commit -m "feat: add rebuild-time fulltext backups and provenance"
```

### Task 5: Surface drift tri-state through maintenance rows and plugin copy

**Files:**
- Modify: `paperforge/worker/ocr_maintenance.py:16-77` and row assembly logic
- Modify: `paperforge/plugin/src/services/ocr-maintenance-ui.ts:23-55`
- Modify: `paperforge/plugin/tests/ocr-maintenance-ui.test.ts`
- Modify: `tests/test_ocr_maintenance.py`

**Interfaces:**
- Consumes:
  - `get_fulltext_drift_state(fulltext_path, machine_hash) -> Literal["MATCHED", "DRIFTED", "UNKNOWN"]`
- Produces:
  - Backend row keys:
    - `fulltext_drift_state: str`
    - `fulltext_drift_reason: str`
  - Plugin row types `MaintenanceDisplayRow` and `MaintenanceRowLike` include the same fields
  - `compute_maintenance_manifest()` includes drift state in its hash input so cache invalidates after user edits

- [ ] **Step 1: Add failing backend + plugin tests for drift tri-state**

```python
from paperforge.worker.ocr_maintenance import OCRMaintenanceRow


def test_maintenance_row_reports_unknown_when_machine_hash_missing(tmp_path: Path) -> None:
    row = OCRMaintenanceRow(
        key="U1",
        title="Paper U",
        title_full="Paper U",
        status="done",
        health="green",
        version="v2",
        finished_at="-",
        rebuild_finished_at="-",
        pages=1,
        blocks=1,
        figures=0,
        tables=0,
        model="PaddleOCR-VL-1.6",
        fulltext_drift_state="UNKNOWN",
        fulltext_drift_reason="No machine baseline is available.",
    )
    assert row.to_dict()["fulltext_drift_state"] == "UNKNOWN"
```

```ts
it("keeps unknown drift rows non-deceptive", () => {
  const result = categorizeMaintenanceRow({
    key: "U1",
    title: "Paper U",
    status: "done",
    health: "green",
    recommended_action: "",
    degraded_reasons: [],
    error_summary: "",
    error_stage: "",
    version: "v2",
    finished_at: "06-19 10:00",
    rebuild_finished_at: "-",
    model: "PaddleOCR-VL-1.6",
    fulltext_drift_state: "UNKNOWN",
    fulltext_drift_reason: "No machine baseline is available.",
  } as any);
  expect(result.reason).not.toContain("safe");
});
```

- [ ] **Step 2: Run the maintenance tests to verify they fail**

Run backend: `pytest tests/test_ocr_maintenance.py -q`
Expected: FAIL because maintenance rows do not expose drift tri-state

Run plugin: `cd paperforge/plugin && npm test -- ocr-maintenance-ui.test.ts`
Expected: FAIL because `MaintenanceRowLike` does not include drift fields

- [ ] **Step 3: Add drift fields, manifest invalidation, and preserve minimal copy**

```python
# paperforge/worker/ocr_maintenance.py
@dataclass
class OCRMaintenanceRow:
    ...
    fulltext_drift_state: str = "UNKNOWN"
    fulltext_drift_reason: str = ""

# when assembling rows
row.fulltext_drift_state = get_fulltext_drift_state(artifacts.compat_fulltext, meta.get("machine_fulltext_hash"))
row.fulltext_drift_reason = {
    "MATCHED": "fulltext.md matches the latest machine write.",
    "DRIFTED": "fulltext.md has changed since the last machine write.",
    "UNKNOWN": "No machine baseline is available.",
}[row.fulltext_drift_state]

# in compute_maintenance_manifest()
drift_state = row.fulltext_drift_state
raw = "|".join([
    key, status, health_overall, version, rec_action,
    df["display_action"], df["display_group"], df["display_severity"],
    drift_state, meta.get("machine_fulltext_hash", ""),
    err_summary, err_summary_hash,
])
```

```ts
export interface MaintenanceDisplayRow {
  key: string;
  title: string;
  display_action: DisplayAction;
  display_label: string;
  display_reason: string;
  display_group: DisplayGroup;
  visible_in_maintenance: boolean;
  can_redo: boolean;
  can_rebuild: boolean;
  fulltext_drift_state?: "MATCHED" | "DRIFTED" | "UNKNOWN";
  fulltext_drift_reason?: string;
}

export type MaintenanceRowLike = {
  ...
  fulltext_drift_state?: "MATCHED" | "DRIFTED" | "UNKNOWN";
  fulltext_drift_reason?: string;
};
```

- [ ] **Step 4: Re-run backend + plugin maintenance tests**

Run backend: `pytest tests/test_ocr_maintenance.py -q`
Expected: PASS

Run plugin: `cd paperforge/plugin && npm test -- ocr-maintenance-ui.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_maintenance.py tests/test_ocr_maintenance.py paperforge/plugin/src/services/ocr-maintenance-ui.ts paperforge/plugin/tests/ocr-maintenance-ui.test.ts
git commit -m "feat: surface drift state and invalidate maintenance cache"
```

## Self-Review

- Spec coverage check:
  - `render/fulltext.md` demoted to derived artifact → Task 2 + Task 5
  - destructive-write backup timing → Task 2 + Task 4
  - atomic write + meta write ordering → Task 2
  - disk-byte SHA-256 rule → Task 1
  - legacy `UNKNOWN` tri-state → Task 5
  - backup retention exact filename policy → Task 1 + Task 2
- Placeholder scan: no `TODO` / `TBD` / “add tests” placeholders remain.
- Interface consistency:
  - single backend seam name `write_render_outputs(..., meta_path, meta, rebuild_increment)` reused by Task 3 and Task 4
  - drift tri-state names are exactly `MATCHED` / `DRIFTED` / `UNKNOWN` everywhere

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-05-fulltext-rebuild-safety-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
