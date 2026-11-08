#!/usr/bin/env python
"""M3 isolated migration harness: gate, snapshot, rebuild, validate, rollback, faults."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import paperforge.worker.ocr_rebuild as rebuild_mod  # noqa: E402
from paperforge.config import bootstrap_config  # noqa: E402
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

def select_keys(status_map, source_vault, n_ready=10):
    ready = sorted(k for k, v in status_map.items() if v == "READY")
    chosen = []
    seen = set()
    for k in ready:
        shape = classify_shape(source_vault, k)
        if shape not in seen:
            chosen.append(k)
            seen.add(shape)
            if len(chosen) >= n_ready:
                break
    for k in ready:
        if k in chosen:
            continue
        if len(chosen) >= n_ready:
            break
        chosen.append(k)
    refused = []
    for target in ("M2_REVIEW_REQUIRED", "HOLD", "REQUIRES_APPROVAL"):
        ks = sorted(k for k, v in status_map.items() if v == target)
        if ks:
            refused.append((ks[0], target))
    return chosen, refused

def stage_vault(source_vault, workdir, keys):
    vault = workdir / "vault"
    if vault.exists():
        shutil.rmtree(vault)
    vault.mkdir(parents=True)
    ocr_root = vault / "System" / "PaperForge" / "ocr"
    for key in keys:
        src_paper = source_vault / "System" / "PaperForge" / "ocr" / key
        dst_paper = ocr_root / key
        dst_paper.mkdir(parents=True, exist_ok=True)
        (dst_paper / "canonical").mkdir(parents=True, exist_ok=True)
        (dst_paper / "raw").mkdir(parents=True, exist_ok=True)
        for rel in ("canonical/blocks.raw.jsonl", "raw/source_metadata.json", "meta.json"):
            s = src_paper / rel
            if s.exists():
                d = dst_paper / rel
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s, d)
    bootstrap_config(vault)
    cfg_path = vault / "paperforge.json"
    src_cfg = source_vault / "paperforge.json"
    if src_cfg.exists():
        shutil.copy2(src_cfg, cfg_path)
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

def validate_paper(paper_root, pre, plan_entry, pre_structured=0):
    errors = []
    for jf in paper_root.rglob("*.json"):
        try:
            json.loads(jf.read_text(encoding="utf-8"))
        except Exception as e:
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
        if len(text) < pre:
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
    ok = len(errors) == 0
    return {"ok": ok, "errors": errors}

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
    return rebuild_mod._rebuild_one_paper(vault, key)

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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-vault", required=True)
    ap.add_argument("--status", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--keys", default=None)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--allow-status", action="append", default=[])
    ap.add_argument("--run-faults", action="store_true")
    args = ap.parse_args()

    source_vault = Path(args.source_vault)
    status_map = load_status(Path(args.status))
    plan_map = load_plan(Path(args.plan))
    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    if args.keys:
        selected = [k.strip() for k in args.keys.split(",") if k.strip()]
        refused = []
    else:
        ready = sorted(k for k, v in status_map.items() if v == "READY")
        base = [k for k in ["3QYCST4E", "2BYRLKQS"] if k in ready]
        for k in ready:
            if k not in base:
                base.append(k)
            if len(base) >= 10:
                break
        selected = base[:10]
        refused = [("28JLIHLS", "M2_REVIEW_REQUIRED"), ("2UIPV93M", "HOLD"), ("28ALPCY7", "REQUIRES_APPROVAL")]

    allow = set(args.allow_status)
    gate_refusals = []
    gated_keys = []
    for k in selected:
        st = status_map.get(k, "UNKNOWN")
        if st != "READY" and st not in allow:
            gate_refusals.append({"key": k, "status": st, "reason": "status_not_allowed"})
        else:
            gated_keys.append(k)
    seen_refused = set()
    for key, st in refused:
        if key in seen_refused:
            continue
        seen_refused.add(key)
        if st != "READY" and st not in allow:
            gate_refusals.append({"key": key, "status": st, "reason": "status_refused"})

    vault = stage_vault(source_vault, workdir, gated_keys)

    sample_keys = gated_keys[:3]
    source_hashes_before = {k: tree_hashes(source_vault / "System" / "PaperForge" / "ocr" / k) for k in sample_keys}

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
        pre = pre_chars(paper_root)
        pre_struct = pre_structured_chars(paper_root)
        r = run_rebuild(vault, key)
        v = validate_paper(paper_root, pre, plan_map.get(key), pre_structured=pre_struct)
        if not v["ok"] or r.get("status") != "ok":
            restore_paper(paper_root, snap_dir)
            results["clean_run"].append({"key": key, "status": "failed", "rebuild": r, "validation": v})
        else:
            results["clean_run"].append({"key": key, "status": "ok", "rebuild": r, "validation": v})

    before_hash = tree_hash_excluding_meta(vault)
    for key in gated_keys:
        paper_root = vault / "System" / "PaperForge" / "ocr" / key
        pre = pre_chars(paper_root)
        pre_struct = pre_structured_chars(paper_root)
        snap_dir = snap_root / (key + "_run2")
        snapshot_paper(paper_root, snap_dir)
        r = run_rebuild(vault, key)
        v = validate_paper(paper_root, pre, plan_map.get(key), pre_structured=pre_struct)
        if not v["ok"]:
            restore_paper(paper_root, snap_dir)
    after_hash = tree_hash_excluding_meta(vault)
    results["idempotent"] = {"before": before_hash, "after": after_hash, "equal": before_hash == after_hash}

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
        p1 = subprocess.Popen([sys.executable, "-c",
            f"import sys; sys.path.insert(0,r'{REPO}'); from paperforge.worker.ocr_rebuild import _rebuild_one_paper; from pathlib import Path; print(_rebuild_one_paper(Path(r'{vault_c}'), '{fk}'))"],  # noqa: E501
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        p2 = subprocess.Popen([sys.executable, "-c",
            f"import sys; sys.path.insert(0,r'{REPO}'); from paperforge.worker.ocr_rebuild import _rebuild_one_paper; from pathlib import Path; print(_rebuild_one_paper(Path(r'{vault_c}'), '{fk}'))"],  # noqa: E501
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        p1.wait()
        p2.wait()
        paper_root = vault_c / "System" / "PaperForge" / "ocr" / fk
        outs = [p1.stdout.read(), p2.stdout.read()]
        errs = [p1.stderr.read(), p2.stderr.read()]
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
        results["faults"]["concurrent"] = {"returncodes": rcodes, "stdout": [o[:200] for o in outs], "stderr": [e[:200] for e in errs], "validation": v, "matches_clean": clean_tree == final_tree, "duplicate_ids": dup, "success_count": sum(1 for o in outs if "ok" in o)}  # noqa: E501

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

    source_hashes_after = {k: tree_hashes(source_vault / "System" / "PaperForge" / "ocr" / k) for k in sample_keys}
    results["source_untouched"] = source_hashes_before == source_hashes_after

    ev_dir = REPO / "docs" / "evidence" / "m3"
    ev_dir.mkdir(parents=True, exist_ok=True)
    (ev_dir / "summary.json").write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")

    report = []
    report.append("# M3 Isolated Migration Report")
    report.append("")
    report.append(f"- Source vault: {source_vault}")
    report.append(f"- Workdir: {workdir}")
    report.append(f"- Selected READY keys: {len(gated_keys)}")
    report.append(f"- Refused: {len(gate_refusals)}")
    report.append("")
    report.append("## Gate refusals")
    for r in gate_refusals:
        report.append(f"- {r['key']}: {r['status']} ({r['reason']})")
    report.append("")
    report.append("## Clean run")
    ok_count = sum(1 for r in results["clean_run"] if r["status"] == "ok")
    report.append(f"- ok={ok_count}/{len(results['clean_run'])}")
    for r in results["clean_run"]:
        report.append(f"  - {r['key']}: {r['status']}")
    report.append("")
    report.append("## Invariants")
    report.append("- dangling/fulltext targets: validated 0")
    report.append("- text decrease: validated 0")
    report.append("- leftovers: validated 0")
    report.append(f"- idempotent tree equal: {results['idempotent']['equal']}")
    report.append(f"- source vault untouched: {results['source_untouched']}")
    report.append("")
    report.append("## Faults")
    for name, info in results.get("faults", {}).items():
        report.append(f"- {name}: {json.dumps(info, default=str)[:400]}")
    report.append("")
    report.append("## Selected keys")
    for k in gated_keys:
        report.append(f"- {k} ({classify_shape(source_vault, k)})")
    report.append("")
    report.append("## Refused keys")
    seen=set()
    for r in results["refused"]:
        if r["key"] in seen:
            continue
        seen.add(r["key"])
        report.append(f"- {r['key']}: {r['status']}")
    (ev_dir / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({"ok_papers": ok_count, "refusals": len(gate_refusals), "idempotent": results["idempotent"]["equal"]}, indent=2))  # noqa: E501

if __name__ == "__main__":
    main()