#!/usr/bin/env python
"""M3 isolated migration harness: gate, snapshot, rebuild, validate, rollback, faults."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import paperforge.worker.ocr_rebuild as rebuild_mod  # noqa: E402
from paperforge.config import bootstrap_config  # noqa: E402
from paperforge.pdf_resolver import resolve_source_pdf  # noqa: E402
from paperforge.worker.ocr_objects import _recover_materialization_journal  # noqa: E402


def load_status(path: Path) -> dict[str, str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("status", data)

def load_plan(path: Path) -> dict[str, dict]:
    out = {}
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            out[o["key"]] = o
    return out

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def tree_hashes(root: Path) -> dict[str, str]:
    out = {}
    if not root.exists():
        return out
    for p in root.rglob("*"):
        if p.is_file():
            out[str(p.relative_to(root)).replace("\\", "/")] = sha256_file(p)
    return out

def classify_shape(vault: Path, key: str) -> str:
    paper = vault / "System" / "PaperForge" / "ocr" / key
    figs = list((paper / "assets" / "figures").glob("*")) if (paper / "assets" / "figures").exists() else []
    tabs = list((paper / "assets" / "tables").glob("*")) if (paper / "assets" / "tables").exists() else []
    if not figs and not tabs:
        return "no_assets"
    if figs and tabs:
        return "both"
    if figs:
        return "figures"
    return "tables"

def select_keys(status_map, source_vault, n_ready=None):
    ready = sorted(k for k, v in status_map.items() if v == "READY")
    chosen = ready if n_ready is None else ready[:n_ready]
    refused = [
        (k, v) for k, v in sorted(status_map.items())
        if v in {"M2_REVIEW_REQUIRED", "HOLD", "REQUIRES_APPROVAL"}
    ]
    return chosen, refused

def assert_isolated(path, workdir):
    path, root = Path(path).resolve(), Path(workdir).resolve()
    if path != root and root not in path.parents:
        raise ValueError(f"path escapes isolated workdir: {path}")
    return path

def _is_link_or_junction(path):
    is_junction = getattr(path, "is_junction", lambda: False)
    return path.is_symlink() or is_junction()

def _reject_source_links(root):
    root = Path(root).resolve()
    for p in root.rglob("*"):
        if _is_link_or_junction(p):
            target = p.resolve()
            if root not in target.parents and target != root:
                raise ValueError(f"symlink/junction escapes isolated workdir: {p} -> {target}")

def assert_tree_isolated(root, workdir):
    root = Path(root)
    for p in root.rglob("*"):
        assert_isolated(p, workdir)
def assert_source_links(root, source_vault):
    root, source_vault = Path(root).resolve(), Path(source_vault).resolve()
    for path in root.rglob("*"):
        if _is_link_or_junction(path):
            target = path.resolve()
            if source_vault not in target.parents and target != source_vault:
                raise ValueError(f"source symlink/junction escapes source vault: {path} -> {target}")

def stage_vault(source_vault, workdir, keys):
    source_vault, workdir = Path(source_vault).resolve(), Path(workdir).resolve()
    if source_vault == workdir or source_vault in workdir.parents or workdir in source_vault.parents:
        raise ValueError("source vault and isolated workdir must be disjoint")
    vault = workdir / "vault"
    if vault.exists():
        shutil.rmtree(vault)
    vault.mkdir(parents=True)
    ocr_root = vault / "System" / "PaperForge" / "ocr"
    for key in keys:
        src_paper = (source_vault / "System" / "PaperForge" / "ocr" / key).resolve()
        if source_vault not in src_paper.parents:
            raise ValueError(f"source paper escapes source vault: {key}")
        dst_paper = assert_isolated(ocr_root / key, workdir)
        if src_paper.exists():
            assert_source_links(src_paper, source_vault)
            shutil.copytree(
                src_paper,
                dst_paper,
                ignore=shutil.ignore_patterns("backups", "versions"),
            )
        else:
            dst_paper.mkdir(parents=True)
        meta_path = dst_paper / "meta.json"
        if meta_path.is_file():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            pdf = resolve_source_pdf(source_vault, meta.get("source_pdf"))
            if pdf is not None:
                meta["source_pdf"] = str(pdf)
                meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        _reject_source_links(dst_paper)
    bootstrap_config(vault)
    config_text = (vault / "paperforge.json").read_text(encoding="utf-8")
    source_names = {str(source_vault), str(source_vault).replace("\\", "/")}
    if any(name.casefold() in config_text.casefold() for name in source_names):
        raise ValueError("isolated config points to source vault")
    _reject_source_links(vault)
    assert_tree_isolated(vault, workdir)
    return vault


def pre_structured_chars(paper_root):
    sj = paper_root / "structure" / "blocks.structured.jsonl"
    if not sj.exists():
        return 0
    total = 0
    for line in sj.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
            total += len(str(o.get("text", "")))
        except Exception:
            pass
    return total


def pre_chars(paper_root):
    for c in paper_root.rglob("fulltext.md"):
        return len(c.read_text(encoding="utf-8"))
    return 0
def _sha256_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def _norm_block_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def historical_baseline(paper_root):
    fulltext = paper_root / "fulltext.md"
    text = fulltext.read_text(encoding="utf-8") if fulltext.is_file() else ""
    structured_path = paper_root / "structure" / "blocks.structured.jsonl"
    rows, structured_chars, parse_errors = 0, 0, []
    block_hashes = {}
    structured_texts = []
    if structured_path.is_file():
        for number, line in enumerate(structured_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                block = json.loads(line)
                rows += 1
                block_text = str(block.get("text", ""))
                structured_chars += len(block_text)
                structured_texts.append(block_text)
                block_key = f"{block.get('page', 0)}:{block.get('block_id', '')}"
                block_hashes[block_key] = _sha256_text(_norm_block_text(block_text))
            except Exception as exc:
                parse_errors.append(f"{number}:{exc}")
    return {
        "fulltext_chars": len(text),
        "fulltext_sha256": _sha256_text(text),
        "normalized_chars": len(re.sub(r"(?m)^\s*#{1,6}\s*", "", re.sub(r"!?\[\[[^\]]+\]\]", "", text))),
        "structured_sha256": _sha256_text("\n".join(structured_texts)),
        "block_hashes": block_hashes,
        "structured_rows": rows,
        "structured_chars": structured_chars,
        "structured_parse_errors": parse_errors,
        "invalid_image_assets": sorted(
            p.relative_to(paper_root).as_posix()
            for root in (paper_root / "assets",)
            if root.exists()
            for p in root.rglob("*")
            if p.is_file()
            and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
            and not p.name.startswith(".")
            and not _valid_image(p)
        ),
        "asset_files": sorted(
            p.relative_to(paper_root).as_posix()
            for root in (paper_root / "assets",)
            if root.exists()
            for p in root.rglob("*")
            if p.is_file()
            and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
            and not p.name.startswith(".")
        ),
        "render_files": sorted(
            p.relative_to(paper_root).as_posix()
            for root in (paper_root / "render" / "figures", paper_root / "render" / "tables")
            if root.exists()
            for p in root.rglob("*")
            if p.is_file()
            and p.suffix.lower() == ".md"
            and not p.name.startswith(".")
        ),
        "embed_targets": sorted(set(
            match.split("|", 1)[0]
            for match in re.findall(r"!?\[\[(render/(?:figures|tables)/[^\]]+)\]\]", text)
        )),
    }

def validate_plan(paper_root, plan_entry):
    mismatches = []
    if not plan_entry:
        return [{"object": None, "reason": "missing_r1_plan_entry"}]

    inventory_path = paper_root / "structure" / "figure_inventory.json"
    inventory_error = None
    if inventory_path.exists():
        try:
            inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            inventory, inventory_error = {}, str(exc)
    else:
        inventory = {}
    if inventory_error:
        mismatches.append({"object": None, "reason": "figure_inventory_parse_failed", "detail": inventory_error})
    if isinstance(inventory, dict):
        rows = inventory.get("matched_figures", [])
    else:
        rows = inventory if isinstance(inventory, list) else []
    actual_figures = {
        str(row.get("figure_id")): row
        for row in rows
        if isinstance(row, dict) and row.get("figure_id")
    }
    planned_figures = {
        str(obj["new_id"]): obj
        for obj in plan_entry.get("objects", [])
        if obj.get("kind") == "figure" and obj.get("new_id") and obj.get("status") == "planned"
    }
    for fid in sorted(planned_figures.keys() - actual_figures.keys()):
        mismatches.append({"object": fid, "reason": "planned_figure_missing"})
    for fid in sorted(actual_figures.keys() - planned_figures.keys()):
        mismatches.append({"object": fid, "reason": "unplanned_figure"})
    for fid in sorted(planned_figures.keys() & actual_figures.keys()):
        expected_claims = {
            str(block["block_id"])
            for anchor in planned_figures[fid].get("anchors", [])
            for block in anchor.get("asset_blocks", [])
            if isinstance(block, dict) and block.get("block_id") is not None
        }
        row = actual_figures[fid]
        actual_claims = {
            str(asset["block_id"])
            for asset in row.get("matched_assets", [])
            if isinstance(asset, dict) and asset.get("block_id") is not None
        } | {str(x) for x in row.get("asset_block_ids", [])}
        if expected_claims != actual_claims:
            mismatches.append({
                "object": fid,
                "reason": "asset_claim_mismatch",
                "expected": sorted(expected_claims),
                "actual": sorted(actual_claims),
            })

    operations = plan_entry.get("operations", [])
    planned_targets = {
        operation.get("new_path")
        for operation in operations
        if operation.get("status") == "planned" and operation.get("new_path")
    }
    for operation in operations:
        rel = operation.get("new_path")
        if operation.get("status") == "planned" and operation.get("op") != "delete_candidate" and rel:
            target = (paper_root / rel).resolve()
            if paper_root.resolve() not in target.parents:
                mismatches.append({
                    "object": operation.get("object_uid"),
                    "reason": "planned_path_escape",
                    "path": rel,
                })
            elif not target.is_file():
                mismatches.append({
                    "object": operation.get("object_uid"),
                    "reason": "planned_file_missing",
                    "path": rel,
                })
        if operation.get("op") != "delete_candidate" or operation.get("status", "").upper() == "APPROVED":
            continue
        old_rel = operation.get("old_path")
        if not old_rel:
            continue
        old_path = (paper_root / old_rel).resolve()
        if paper_root.resolve() not in old_path.parents:
            mismatches.append({
                "object": operation.get("object_uid"),
                "reason": "approval_delete_path_escape",
                "path": old_rel,
            })
        elif old_rel in planned_targets:
            mismatches.append({
                "object": operation.get("object_uid"),
                "reason": "approval_delete_path_reused",
                "path": old_rel,
            })
        elif not old_path.is_file():
            mismatches.append({
                "object": operation.get("object_uid"),
                "reason": "unapproved_delete",
                "path": old_rel,
            })
        elif operation.get("old_sha256") and sha256_file(old_path) != operation["old_sha256"]:
            mismatches.append({
                "object": operation.get("object_uid"),
                "reason": "unapproved_delete_modified",
                "path": old_rel,
            })
    planned_embeds = {
        embed.get("new_target")
        for embed in plan_entry.get("embeds", [])
        if embed.get("status") == "planned" and embed.get("new_target")
    }
    import re
    actual_embeds = set()
    fulltext = paper_root / "fulltext.md"
    if fulltext.is_file():
        text = fulltext.read_text(encoding="utf-8")
        actual_embeds = {
            match.split("|", 1)[0]
            for match in re.findall(r"!?\[\[(render/(?:figures|tables)/[^\]]+)\]\]", text)
        }
    for target in sorted(planned_embeds - actual_embeds):
        mismatches.append({
            "object": target.rsplit("/", 1)[-1].removesuffix(".md"),
            "reason": "planned_embed_missing",
            "target": target,
        })
    for target in sorted(actual_embeds - planned_embeds):
        mismatches.append({
            "object": target.rsplit("/", 1)[-1].removesuffix(".md"),
            "reason": "unplanned_embed",
            "target": target,
        })
    return mismatches


def _valid_image(path: Path) -> bool:
    try:
        head = path.read_bytes()[:16]
    except OSError:
        return False
    return (
        head.startswith(b"\x89PNG\r\n\x1a\n")
        or head.startswith(b"\xff\xd8\xff")
        or (head.startswith(b"RIFF") and head[8:12] == b"WEBP")
    )


def _waiver_matches(spec: dict, baseline: dict | None, current: dict) -> bool:
    if not baseline:
        return False
    for old_key, new_key in (
        ("old_fulltext_sha256", "fulltext_sha256"),
        ("old_structured_sha256", "structured_sha256"),
    ):
        if spec.get(old_key) and spec[old_key] != baseline.get(new_key):
            return False
    for new_key, current_key in (
        ("new_fulltext_sha256", "fulltext_sha256"),
        ("new_structured_sha256", "structured_sha256"),
    ):
        if spec.get(new_key) and spec[new_key] != current.get(current_key):
            return False
    for block in spec.get("blocks", []):
        block_key = f"{block.get('page', 0)}:{block.get('block_id', '')}"
        if baseline.get("block_hashes", {}).get(block_key) != block.get("old_sha256"):
            return False
        if current.get("block_hashes", {}).get(block_key) != block.get("new_sha256"):
            return False
    return True


def validate_paper(paper_root, pre, plan_entry, pre_structured=0, baseline=None, waivers=None):
    errors = []
    warnings = []
    optional_unreadable = []
    optional_json = {"figure-map.json", "chart-type-map.json"}
    for jf in paper_root.rglob("*.json"):
        try:
            json.loads(jf.read_text(encoding="utf-8"))
        except Exception as e:
            if jf.name in optional_json:
                optional_unreadable.append(f"{jf.name}:{e}")
            else:
                errors.append(f"json_parse:{jf.name}:{e}")
    from paperforge.worker.ocr_hash import has_result_hash_pending
    if has_result_hash_pending(paper_root):
        errors.append("pending_marker_present")
    for bad in paper_root.rglob(".materialization-*"):
        errors.append(f"leftover:{bad.name}")
    fis = list(paper_root.rglob("figure_inventory.json"))
    if fis:
        try:
            inv = json.loads(fis[0].read_text(encoding="utf-8"))
            figs = inv.get("matched_figures", inv.get("figures", inv if isinstance(inv, list) else []))
            if isinstance(figs, list):
                ids = [f.get("figure_id") or f.get("id") for f in figs if isinstance(f, dict)]
                if len(ids) != len(set(ids)):
                    errors.append("duplicate_figure_ids")
        except Exception as e:
            errors.append(f"figure_inventory_parse:{e}")
    fulltext_candidates = list(paper_root.rglob("fulltext.md"))
    if fulltext_candidates:
        ft = fulltext_candidates[0]
        text = ft.read_text(encoding="utf-8")
        import re
        for m in re.finditer(r"\[\[(render/(?:figures|tables)/[^\]]+)\]\]", text):
            target_rel = m.group(1).split("|")[0]
            target_path = paper_root / target_rel
            if not target_path.exists() and not (paper_root / (target_rel + ".md")).exists():
                errors.append(f"dangling_fulltext_target:{target_rel}")
        if baseline is None and len(text) < pre:
            errors.append(f"text_decrease:{len(text)}<{pre}")
    # structured text total
    sj = paper_root / "structure" / "blocks.structured.jsonl"
    if sj.exists():
        total = 0
        for line in sj.read_text(encoding="utf-8").splitlines():
            line=line.strip()
            if not line:
                continue
            try:
                o=json.loads(line)
                total += len(str(o.get("text","")))
            except Exception:
                pass
        if pre_structured and total < pre_structured:
            errors.append(f"structured_text_decrease:{total}<{pre_structured}")
    for inv_path in paper_root.rglob("*_inventory.json"):
        try:
            inv = json.loads(inv_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        objs = []
        if isinstance(inv, dict):
            for v in inv.values():
                if isinstance(v, list):
                    objs.extend(v)
        elif isinstance(inv, list):
            objs = inv
        for o in objs:
            if not isinstance(o, dict):
                continue
            for key in ("image_relpath", "asset_path", "image_path", "render_path"):
                rp = o.get(key)
                if rp:
                    cand = paper_root / rp
                    if not cand.exists() and not (paper_root / "render" / rp).exists() and not (paper_root / "assets" / rp).exists():  # noqa: E501
                        errors.append(f"missing_inventory_asset:{rp}")
    if baseline is not None:
        current = historical_baseline(paper_root)
        if (
            not baseline["fulltext_chars"]
            and not baseline["structured_rows"]
            and not baseline["asset_files"]
            and not baseline["render_files"]
        ):
            errors.append("historical_baseline_empty")
        if baseline["structured_parse_errors"]:
            errors.append(f"historical_structured_parse_errors:{baseline['structured_parse_errors']}")
        if current["normalized_chars"] < baseline["normalized_chars"]:
            errors.append(f"historical_text_decrease:{current['normalized_chars']}<{baseline['normalized_chars']}")
        if current["structured_rows"] < baseline["structured_rows"]:
            errors.append(f"historical_structured_rows_decrease:{current['structured_rows']}<{baseline['structured_rows']}")
        if current["structured_chars"] < baseline["structured_chars"]:
            errors.append(f"historical_structured_chars_decrease:{current['structured_chars']}<{baseline['structured_chars']}")
        operations = plan_entry.get("operations", []) if plan_entry else []
        replacements = {
            operation.get("old_path"): operation.get("new_path")
            for operation in operations
            if operation.get("status") == "planned" and operation.get("old_path") and operation.get("new_path")
        }
        current_files = set(current["asset_files"]) | set(current["render_files"])
        for rel in set(baseline["asset_files"] + baseline["render_files"]) - current_files:
            replacement = replacements.get(rel)
            if replacement and (paper_root / replacement).is_file():
                continue
            old_path = paper_root / rel
            alt = old_path.with_suffix(".jpg")
            invalid_before = rel in set((baseline or {}).get("invalid_image_assets", []))
            if invalid_before and alt.is_file() and _valid_image(alt):
                warnings.append(f"legacy_corrupt_asset_replaced:{rel}->{alt.relative_to(paper_root).as_posix()}")
            else:
                errors.append(f"historical_object_missing:{rel}")
    plan_mismatches = validate_plan(paper_root, plan_entry)
    errors.extend(
        f"plan_mismatch:{mismatch['reason']}:{mismatch.get('object') or mismatch.get('path') or ''}"
        for mismatch in plan_mismatches
    )
    key = (plan_entry or {}).get("key", "")
    waiver_entry = (waivers or {}).get(key, {})
    current = historical_baseline(paper_root)
    waived_errors = []
    waiver_mismatches = []
    for error_class in sorted({e.split(":", 1)[0] for e in errors}):
        spec = waiver_entry.get(error_class)
        if not spec:
            continue
        if not _waiver_matches(spec, baseline, current):
            waiver_mismatches.append(error_class)
            continue
        waived_errors.extend(e for e in errors if e.split(":", 1)[0] == error_class)
    errors = [e for e in errors if e not in waived_errors]
    errors.extend(f"waiver_mismatch:{c}" for c in waiver_mismatches)
    return {
        "ok": not errors,
        "errors": errors,
        "plan_mismatches": plan_mismatches,
        "historical_baseline": baseline,
        "optional_unreadable": optional_unreadable,
        "warnings": warnings,
        "waived_errors": waived_errors,
        "waiver_mismatches": waiver_mismatches,
    }

def snapshot_paper(paper_root, snap_dir):
    if snap_dir.exists():
        shutil.rmtree(snap_dir)
    if paper_root.exists():
        shutil.copytree(paper_root, snap_dir)

def restore_paper(paper_root, snap_dir):
    if paper_root.exists():
        shutil.rmtree(paper_root)
    if snap_dir.exists():
        shutil.copytree(snap_dir, paper_root)

def run_rebuild(vault, key):
    vault = Path(vault)
    paper_root = vault / "System" / "PaperForge" / "ocr" / key
    assert_isolated(paper_root, vault.parent)
    _reject_source_links(paper_root)
    result = rebuild_mod._rebuild_one_paper(vault, key)
    assert_isolated(paper_root, vault.parent)
    _reject_source_links(paper_root)
    return result

def tree_hash_excluding_meta(vault):
    h = hashlib.sha256()
    hashes = tree_hashes(vault)
    for rel in sorted(hashes):
        if rel.endswith("meta.json"):
            continue
        if rel.endswith("render.consistency.json"):
            continue
        if rel.startswith("backups/") or rel.startswith("versions/") or "/backups/" in rel or "/versions/" in rel:
            continue
        if "fulltext.pre-rebuild" in rel:
            continue
        h.update(rel.encode())
        h.update(hashes[rel].encode())
    return h.hexdigest()

def recovery_anomalies(faults):
    checks = {
        "kill": lambda value: value.get("validation", {}).get("ok")
            and value.get("matches_clean"),
        "write_error": lambda value: value.get("validation", {}).get("ok")
            and value.get("old_byte_identical")
            and not value.get("leftovers")
            and value.get("rerun", {}).get("status") == "ok",
        "interrupted_commit": lambda value: value.get("restored_old")
            and value.get("validation", {}).get("ok")
            and value.get("rebuild", {}).get("status") == "ok",
        "concurrent": lambda value: value.get("validation", {}).get("ok")
            and value.get("matches_clean")
            and not value.get("duplicate_ids")
            and value.get("success_count", 0) >= 1,
        "corrupt": lambda value: value.get("detected_before")
            and value.get("valid_after")
            and value.get("matches_clean"),
    }
    return [
        f"{name}_spot_check_failed"
        for name, check in checks.items()
        if not isinstance(faults.get(name), dict) or not check(faults[name])
    ]


def run_batches(args, selected):
    evidence_dir = Path(args.evidence_dir).resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    batch_size = args.batch_size
    if batch_size < 1 or batch_size > 100:
        raise ValueError("--batch-size must be between 1 and 100")
    batches = [selected[i:i + batch_size] for i in range(0, len(selected), batch_size)]
    manifest_path = evidence_dir / "batch-manifest.json"
    manifest = {
        "selected": len(selected), "selected_keys": selected,
        "batch_size": batch_size, "batches": [],
    }
    if manifest_path.is_file():
        prior = json.loads(manifest_path.read_text(encoding="utf-8"))
        if prior.get("selected_keys") == selected and prior.get("batch_size") == batch_size:
            manifest = prior
    previous = {item["batch"]: item for item in manifest["batches"]}
    all_results = []
    idempotence = []
    recovery = {}
    source_changed = []
    source_hashed = 0
    recovery_dir = evidence_dir / "recovery"
    recovery_summary = recovery_dir / "summary.json"
    if selected:
        recovery_command = [
            sys.executable, str(Path(__file__).resolve()),
            "--source-vault", str(args.source_vault),
            "--status", str(args.status), "--plan", str(args.plan),
            "--keys", selected[0],
            "--workdir", str(Path(args.workdir).resolve() / "recovery"),
            "--batch-worker", "--batch-size", "0",
            "--evidence-dir", str(recovery_dir),
            "--run-faults",
        ]
        for status in args.allow_status:
            recovery_command.extend(["--allow-status", status])
        checked = subprocess.run(
            recovery_command, capture_output=True, text=True, check=False
        )
        if checked.returncode == 0 and recovery_summary.is_file():
            recovery = json.loads(
                recovery_summary.read_text(encoding="utf-8")
            ).get("faults", {})
        else:
            recovery = {
                "status": "failed",
                "returncode": checked.returncode,
                "stderr": checked.stderr[-4000:],
                "stdout": checked.stdout[-1000:],
            }
        manifest["recovery_spot_check"] = recovery
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


    for index, keys in enumerate(batches, 1):
        batch_name = f"batch-{index:03d}"
        batch_work = Path(args.workdir).resolve() / batch_name
        batch_evidence = evidence_dir / batch_name
        command = [
            sys.executable, str(Path(__file__).resolve()),
            "--source-vault", str(args.source_vault),
            "--status", str(args.status), "--plan", str(args.plan),
            "--keys", ",".join(keys), "--workdir", str(batch_work),
            "--batch-worker", "--batch-size", "0",
            "--evidence-dir", str(batch_evidence),
        ]
        if args.waivers:
            command.extend(["--waivers", str(args.waivers)])
        for status in args.allow_status:
            command.extend(["--allow-status", status])
        # Recovery is exercised in its own one-paper fresh process above.
        item = previous.get(batch_name, {"batch": batch_name, "keys": keys, "completed": False})
        batch_summary_path = batch_evidence / "summary.json"
        if item.get("completed") and batch_summary_path.is_file():
            completed = None
        else:
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            item.update({
                "keys": keys,
                "returncode": completed.returncode,
                "stderr": completed.stderr[-4000:],
                "stdout": completed.stdout[-1000:],
                "completed": completed.returncode == 0 and batch_summary_path.is_file(),
            })
        if item.get("completed") and batch_summary_path.is_file():
            batch = json.loads(batch_summary_path.read_text(encoding="utf-8"))
            all_results.extend(batch.get("clean_run", []))
            source_changed.extend(batch.get("source_integrity", {}).get("changed_keys", []))
            source_hashed += batch.get("source_integrity", {}).get("all_selected_hashed", 0)
            idempotence.append(batch.get("idempotent", {}).get("equal") is True)
            recovery.update(batch.get("faults", {}))
        else:
            rc = item.get("returncode", "missing_summary")
            reason = item.get("stderr", "")[-500:] or item.get("stdout", "")[-500:]
            all_results.extend({
                "key": key, "status": "failed",
                "rebuild": {"status": "not_run"},
                "validation": {
                    "ok": False,
                    "errors": [f"batch_process_failed:{rc}:{reason}"],
                },
            } for key in keys)
        if batch_name not in previous:
            manifest["batches"].append(item)
        else:
            manifest["batches"] = [item if old["batch"] == batch_name else old for old in manifest["batches"]]
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        if batch_work.exists():
            shutil.rmtree(batch_work)

    pass_count = sum(result.get("status") == "ok" for result in all_results)
    result_by_key = {result["key"]: result for result in all_results}
    for key in selected:
        result = result_by_key.get(key, {
            "key": key, "status": "failed", "rebuild": {"status": "not_run"},
            "validation": {"ok": False, "errors": ["result_missing"]},
        })
        (evidence_dir / "papers" / f"{key}.json").parent.mkdir(parents=True, exist_ok=True)
        (evidence_dir / "papers" / f"{key}.json").write_text(
            json.dumps(result, indent=2, default=str), encoding="utf-8"
        )
    status_map = load_status(Path(args.status))
    rejected = [
        {"key": key, "status": status}
        for key, status in sorted(status_map.items())
        if status != "READY" and status not in set(args.allow_status)
    ]
    plan_mismatch_count = sum(
        len(result.get("validation", {}).get("plan_mismatches", []))
        for result in all_results
    )
    recovery_failures = recovery_anomalies(recovery)
    blocking_anomalies = (
        [f"paper_validation_failed:{len(selected) - pass_count}"]
        if pass_count != len(selected) else []
    )
    if source_changed:
        blocking_anomalies.append(f"source_changed:{','.join(source_changed)}")
    if not source_hashed or source_hashed != len(selected):
        blocking_anomalies.append(f"source_hash_coverage:{source_hashed}/{len(selected)}")
    if not idempotence or not all(idempotence):
        blocking_anomalies.append("idempotence_spot_check_failed")
    blocking_anomalies.extend(recovery_failures)
    summary = {
        "selected_ready": selected,
        "rejected_statuses": rejected,
        "rebuilt_count": sum(result.get("rebuild", {}).get("status") == "ok" for result in all_results),
        "validation_pass": pass_count,
        "validation_fail": len(selected) - pass_count,
        "plan_mismatch_count": plan_mismatch_count,
        "clean_run": [result_by_key.get(key, {"key": key, "status": "failed"}) for key in selected],
        "source_integrity": {
            "all_selected_hashed": source_hashed,
            "unchanged": source_hashed == len(selected) and not source_changed
                and len(manifest["batches"]) == len(batches)
                and all(item["completed"] for item in manifest["batches"]),
            "changed_keys": source_changed,
        },
        "idempotence_by_batch": idempotence,
        "idempotence_pass": bool(idempotence) and all(idempotence),
        "recovery_spot_checks": recovery,
        "recovery_failures": recovery_failures,
        "blocking_anomalies": blocking_anomalies,
        "batch_manifest": manifest,
    }
    (evidence_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report = [
        "# R2 Full READY Isolated Rebuild",
        "",
        f"- Selected READY: {len(selected)}",
        f"- Rebuilt: {summary['rebuilt_count']}/{len(selected)}",
        f"- Validation pass/fail: {pass_count}/{len(selected) - pass_count}",
        f"- Idempotence spot checks passed: {sum(idempotence)}/{len(idempotence)}",
        f"- Plan mismatches: {plan_mismatch_count}",
        f"- Recovery spot checks: {json.dumps(recovery, default=str)}",
        f"- Rejected non-READY papers: {len(rejected)}",
        f"- Source hashes: {source_hashed}/{len(selected)}; "
        f"unchanged={summary['source_integrity']['unchanged']}",
        f"- Batches completed: {sum(item['completed'] for item in manifest['batches'])}/{len(batches)}",
        f"- Blocking anomalies: {summary['blocking_anomalies']}",
        "",
    ]
    for result in summary["clean_run"]:
        errors = result.get("validation", {}).get("errors", [])
        mismatches = result.get("validation", {}).get("plan_mismatches", [])
        report.append(
            f"- {result['key']}: {result['status']}; errors={errors}; "
            f"object_mismatches={mismatches}"
        )
    (evidence_dir / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-vault", required=True)
    ap.add_argument("--status", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--keys", default=None)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--allow-status", action="append", default=[])
    ap.add_argument("--run-faults", action="store_true")
    ap.add_argument("--waivers", default="", help="JSON map key -> waived error classes")
    ap.add_argument("--batch-size", type=int, default=75)
    ap.add_argument("--batch-worker", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--evidence-dir", default=str(REPO / "docs" / "evidence" / "r2"))
    args = ap.parse_args()
    def repo_path(value):
        path = Path(value)
        return (path if path.is_absolute() else REPO / path).resolve()
    args.source_vault = str(repo_path(args.source_vault))
    args.status = str(repo_path(args.status))
    args.plan = str(repo_path(args.plan))
    args.workdir = str(repo_path(args.workdir))
    args.evidence_dir = str(repo_path(args.evidence_dir))

    waivers = json.loads(Path(args.waivers).read_text(encoding="utf-8")) if args.waivers else {}
    source_vault = Path(args.source_vault)
    status_map = load_status(Path(args.status))
    plan_map = load_plan(Path(args.plan))
    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    if args.keys:
        selected = [k.strip() for k in args.keys.split(",") if k.strip()]
    else:
        selected = sorted(k for k, v in status_map.items() if v == "READY")
    refused = [(k, v) for k, v in sorted(status_map.items()) if v != "READY" and v not in set(args.allow_status)]

    allow = set(args.allow_status)
    gate_refusals = []
    gated_keys = []
    for k in selected:
        st = status_map.get(k, "UNKNOWN")
        if st != "READY" and st not in allow:
            gate_refusals.append({"key": k, "status": st, "reason": "status_not_allowed"})
        else:
            gated_keys.append(k)
    if gate_refusals:
        raise SystemExit(f"refusing non-READY selected paper(s): {gate_refusals}")
    if not args.batch_worker:
        summary = run_batches(args, gated_keys)
        print(json.dumps({
            "selected": len(gated_keys),
            "rebuilt": summary["rebuilt_count"],
            "validation_pass": summary["validation_pass"],
            "validation_fail": summary["validation_fail"],
            "source_unchanged": summary["source_integrity"]["unchanged"],
        }, indent=2))
        return

    source_root = source_vault / "System" / "PaperForge" / "ocr"
    missing_source = [key for key in gated_keys if not (source_root / key).is_dir()]
    if missing_source:
        raise FileNotFoundError(f"source paper trees missing: {missing_source}")
    for key in gated_keys:
        assert_source_links(source_root / key, source_vault)
    source_hashes_before = {k: tree_hashes(source_root / k) for k in gated_keys}
    vault = stage_vault(source_vault, workdir, gated_keys)

    results = {
        "selected_ready": gated_keys,
        "refused": [{"key": k, "status": s} for k, s in refused] + [r for r in gate_refusals],
        "gate_refusals": gate_refusals,
        "clean_run": [],
        "faults": {},
    }

    snap_root = workdir / "snapshots"
    snap_root.mkdir(exist_ok=True)
    for key in gated_keys:
        paper_root = vault / "System" / "PaperForge" / "ocr" / key
        snap_dir = snap_root / key
        snapshot_paper(paper_root, snap_dir)
        baseline = historical_baseline(paper_root)
        pre = baseline["fulltext_chars"]
        pre_struct = baseline["structured_chars"]
        try:
            r = run_rebuild(vault, key)
        except Exception as exc:
            r = {"key": key, "status": "exception", "error": str(exc)}
        try:
            v = validate_paper(
                paper_root, pre, plan_map.get(key),
                pre_structured=pre_struct, baseline=baseline, waivers=waivers,
            )
        except Exception as exc:
            v = {"ok": False, "errors": [f"validation_exception:{exc}"], "plan_mismatches": []}
        if not v["ok"] or r.get("status") != "ok":
            restore_paper(paper_root, snap_dir)
            results["clean_run"].append({"key": key, "status": "failed", "rebuild": r, "validation": v})
        else:
            results["clean_run"].append({"key": key, "status": "ok", "rebuild": r, "validation": v})

    before_hash = tree_hash_excluding_meta(vault)
    repeat_ok = []
    for key in gated_keys:
        paper_root = vault / "System" / "PaperForge" / "ocr" / key
        baseline = historical_baseline(paper_root)
        pre = baseline["fulltext_chars"]
        pre_struct = baseline["structured_chars"]
        snap_dir = snap_root / (key + "_run2")
        snapshot_paper(paper_root, snap_dir)
        try:
            r = run_rebuild(vault, key)
        except Exception as exc:
            r = {"key": key, "status": "exception", "error": str(exc)}
        try:
            v = validate_paper(
                paper_root, pre, plan_map.get(key),
                pre_structured=pre_struct, baseline=baseline, waivers=waivers,
            )
        except Exception as exc:
            v = {"ok": False, "errors": [f"validation_exception:{exc}"], "plan_mismatches": []}
        repeat_ok.append(r.get("status") == "ok" and v["ok"])
        if not repeat_ok[-1]:
            restore_paper(paper_root, snap_dir)
    after_hash = tree_hash_excluding_meta(vault)
    results["idempotent"] = {
        "before": before_hash,
        "after": after_hash,
        "equal": before_hash == after_hash,
        "repeat_validation_pass": sum(repeat_ok),
        "repeat_validation_fail": len(repeat_ok) - sum(repeat_ok),
    }

    if args.run_faults and gated_keys:
        fk = gated_keys[0]
        # 1 kill: poll for real staging/journal artifact
        fv = stage_vault(source_vault, workdir / "fault_kill", [fk])
        proc = subprocess.Popen([sys.executable, "-c",
            f"import sys; sys.path.insert(0,r'{REPO}'); from paperforge.worker.ocr_rebuild import _rebuild_one_paper; from pathlib import Path; _rebuild_one_paper(Path(r'{fv}'), '{fk}')"],  # noqa: E501
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        interrupted = False
        marker = None
        for _ in range(60):
            time.sleep(0.5)
            paper_root = fv / "System" / "PaperForge" / "ocr" / fk
            marker = paper_root / "index" / "result-hash.pending"
            if marker.exists():
                interrupted = True
                proc.kill()
                break
        proc.wait()
        proc_rc = proc.returncode
        paper_root = fv / "System" / "PaperForge" / "ocr" / fk
        pending_before = marker.exists() if marker else False
        leftovers_before = [str(x.name) for x in paper_root.glob(".materialization*")]
        if not pending_before and not leftovers_before:
            raise RuntimeError("kill scenario: no pending marker/stage found before kill")
        _recover_materialization_journal(paper_root)
        pre = pre_chars(paper_root)
        pre_struct = pre_structured_chars(paper_root)
        r = run_rebuild(fv, fk)
        v = validate_paper(paper_root, pre if pre else 0, plan_map.get(fk), pre_structured=pre_struct)
        cv = stage_vault(source_vault, workdir / "fault_kill_clean", [fk])
        run_rebuild(cv, fk)
        clean_tree = tree_hash_excluding_meta(cv / "System" / "PaperForge" / "ocr" / fk)
        final_tree = tree_hash_excluding_meta(paper_root)
        results["faults"]["kill"] = {"interrupted": interrupted, "pending_before": pending_before, "leftovers_before": leftovers_before, "proc_rc": proc_rc, "rebuild": r, "validation": v, "matches_clean": clean_tree == final_tree}  # noqa: E501

        # 2 write error / ENOSPC
        fv = stage_vault(source_vault, workdir / "fault_writeerr", [fk])
        import paperforge.worker.ocr_objects as objs
        orig = objs._write_object_markdown
        counter = {"n": 0}
        def boom(md, dst):
            counter["n"] += 1
            if counter["n"] > 3:
                raise OSError("ENOSPC")
            return orig(md, dst)
        objs._write_object_markdown = boom
        paper_root = fv / "System" / "PaperForge" / "ocr" / fk
        before_files = {k: val for k, val in tree_hashes(paper_root).items() if k.startswith("render/") or k.startswith("assets/")}  # noqa: E501
        try:
            r = run_rebuild(fv, fk)
        except Exception as e:
            r = {"status": "exception", "error": str(e)}
        objs._write_object_markdown = orig
        after_files = {k: val for k, val in tree_hashes(paper_root).items() if k.startswith("render/") or k.startswith("assets/")}  # noqa: E501
        identical = all(before_files.get(rel) == after_files.get(rel) for rel in before_files)
        leftovers = [str(p.name) for p in paper_root.glob(".materialization*")]
        r2 = run_rebuild(fv, fk)
        v2 = validate_paper(paper_root, pre_chars(paper_root), plan_map.get(fk), pre_structured=pre_structured_chars(paper_root))  # noqa: E501
        results["faults"]["write_error"] = {"first": r, "rerun": r2, "validation": v2, "old_byte_identical": identical, "leftovers": leftovers}  # noqa: E501

        # 3 interrupted commit: real committing journal
        fv = stage_vault(source_vault, workdir / "fault_journal", [fk])
        vault_j = fv
        paper_root = vault_j / "System" / "PaperForge" / "ocr" / fk
        run_rebuild(vault_j, fk)
        # build journal like test_recovery_restores_old_directories_after_interrupted_commit
        target = paper_root / "render"
        backup_root = paper_root / ".materialization-backup-test"
        backup_root.mkdir(exist_ok=True)
        stage_root = paper_root / ".materialization-stage-test"
        stage_root.mkdir(exist_ok=True)
        # move current render to backup, stage new
        if target.exists():
            target.rename(backup_root / "0")
        target.mkdir(parents=True, exist_ok=True)
        (target / "partial.md").write_text("partial", encoding="utf-8")
        journal = {
            "schema_version": 1,
            "token": "test",
            "status": "committing",
            "stage_root": str(stage_root),
            "backup_root": str(backup_root),
            "targets": [{"target": str(target), "backup": str(backup_root / "0")}],
        }
        (paper_root / ".materialization-journal.json").write_text(__import__("json").dumps(journal), encoding="utf-8")
        _recover_materialization_journal(paper_root)
        # verify old state restored: render should have original content, no partial.md
        restored_ok = not (target / "partial.md").exists()
        pre = pre_chars(paper_root)
        pre_struct = pre_structured_chars(paper_root)
        r = run_rebuild(vault_j, fk)
        v = validate_paper(paper_root, pre, plan_map.get(fk), pre_structured=pre_struct)
        results["faults"]["interrupted_commit"] = {"restored_old": restored_ok, "rebuild": r, "validation": v}

        # 4 concurrent
        fv = stage_vault(source_vault, workdir / "fault_conc", [fk])
        vault_c = fv
        script = (
            f"import sys; sys.path.insert(0,r'{REPO}'); "
            "from paperforge.worker.ocr_rebuild import _rebuild_one_paper; "
            "from pathlib import Path; "
            f"_rebuild_one_paper(Path(r'{vault_c}'), '{fk}')"
        )
        command = [sys.executable, "-c", script]
        p1 = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p2 = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        timed_out = False
        try:
            p1.wait(timeout=180)
            p2.wait(timeout=180)
        except subprocess.TimeoutExpired:
            timed_out = True
            p1.kill()
            p2.kill()
            p1.wait()
            p2.wait()
        paper_root = vault_c / "System" / "PaperForge" / "ocr" / fk
        rcodes = [p1.returncode, p2.returncode]
        v = validate_paper(paper_root, 0, plan_map.get(fk), pre_structured=0)
        cv = stage_vault(source_vault, workdir / "fault_conc_clean", [fk])
        run_rebuild(cv, fk)
        clean_tree = tree_hash_excluding_meta(cv / "System" / "PaperForge" / "ocr" / fk)
        final_tree = tree_hash_excluding_meta(paper_root)
        # duplicate ids check
        fis = list(paper_root.rglob("figure_inventory.json"))
        dup = False
        if fis:
            inv = __import__("json").loads(fis[0].read_text())
            figs = inv.get("matched_figures", inv.get("figures", inv if isinstance(inv, list) else []))
            if isinstance(figs, list):
                ids = [f.get("figure_id") or f.get("id") for f in figs if isinstance(f, dict)]
                dup = len(ids) != len(set(ids))
        results["faults"]["concurrent"] = {
            "returncodes": rcodes,
            "timed_out": timed_out,
            "validation": v,
            "matches_clean": clean_tree == final_tree,
            "duplicate_ids": dup,
            "success_count": sum(code == 0 for code in rcodes),
        }

        # 5 corrupt
        fv = stage_vault(source_vault, workdir / "fault_corrupt", [fk])
        vault_x = fv
        paper_root = vault_x / "System" / "PaperForge" / "ocr" / fk
        run_rebuild(vault_x, fk)
        # target fulltext-referenced render markdown
        renders = list(paper_root.rglob("render/figures/*.md")) + list(paper_root.rglob("render/tables/*.md"))
        if renders:
            renders[0].unlink(missing_ok=True)
        # structure json
        structs = [p for p in paper_root.rglob("structure/*.json")]
        if structs:
            structs[0].write_text("{bad", encoding="utf-8")
        # asset
        assets = list(paper_root.rglob("assets/**/*"))
        assets = [a for a in assets if a.is_file()]
        if assets:
            assets[0].write_bytes(b"")
        v_before = validate_paper(paper_root, pre_chars(paper_root), plan_map.get(fk), pre_structured=pre_structured_chars(paper_root))  # noqa: E501
        r = run_rebuild(vault_x, fk)
        v_after = validate_paper(paper_root, 0, plan_map.get(fk), pre_structured=0)
        cv = stage_vault(source_vault, workdir / "fault_corrupt_clean", [fk])
        run_rebuild(cv, fk)
        clean_tree = tree_hash_excluding_meta(cv / "System" / "PaperForge" / "ocr" / fk)
        final_tree = tree_hash_excluding_meta(paper_root)
        results["faults"]["corrupt"] = {"detected_before": not v_before["ok"], "errors_before": v_before["errors"][:5], "rebuild": r, "valid_after": v_after["ok"], "matches_clean": clean_tree == final_tree}  # noqa: E501

    source_hashes_after = {k: tree_hashes(source_root / k) for k in gated_keys}
    changed_sources = [k for k in gated_keys if source_hashes_before[k] != source_hashes_after[k]]
    results["source_integrity"] = {
        "all_selected_hashed": len(gated_keys),
        "unchanged": not changed_sources,
        "changed_keys": changed_sources,
    }

    ev_dir = Path(args.evidence_dir).resolve()
    (ev_dir / "papers").mkdir(parents=True, exist_ok=True)
    (ev_dir / "summary.json").write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")

    ok_count = sum(1 for r in results["clean_run"] if r["status"] == "ok")
    for paper_result in results["clean_run"]:
        (ev_dir / "papers" / f"{paper_result['key']}.json").write_text(
            json.dumps(paper_result, indent=2, default=str), encoding="utf-8"
        )
    report = [
        "# R2 Full READY Isolated Rebuild",
        "",
        f"- Selected READY papers: {len(gated_keys)}",
        f"- Rebuilt: {ok_count}/{len(results['clean_run'])}",
        f"- Validation pass/fail: {ok_count}/{len(results['clean_run']) - ok_count}",
        f"- Idempotence: {results['idempotent']['equal']}",
        f"- Source hashes ({results['source_integrity']['all_selected_hashed']}): "
        f"unchanged={results['source_integrity']['unchanged']}",
        f"- Blocking failures: {len(results['clean_run']) - ok_count}; source changes={len(changed_sources)}",
        "",
    ]
    for r in results["clean_run"]:
        report.append(f"- {r['key']}: {r['status']} — {r['rebuild']} / {r['validation']['errors']}")
    (ev_dir / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({
        "ok_papers": ok_count,
        "failed_papers": len(results["clean_run"]) - ok_count,
        "source_unchanged": results["source_integrity"]["unchanged"],
        "idempotent": results["idempotent"]["equal"],
    }, indent=2))

if __name__ == "__main__":
    main()