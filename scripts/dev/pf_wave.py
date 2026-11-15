#!/usr/bin/env python3
"""Run one PaperForge work wave: one isolated ovnfs checkout per card, one omp each.

Each card is a Markdown brief in ``.work/waves/<wave>/cards/``. The runner:

1. creates ``ovnfs`` checkout ``pf-<wave>-<slug>`` from ``--base``,
2. starts ``omp -p --cwd <checkout>`` with an isolated HOME/TEMP so parallel
   workers cannot race on ``~/.paperforge`` or the user profile,
3. waits for every worker, then records exit codes, commits and dirty files in
   ``.work/waves/<wave>/manifest.json``.

Workers need `--approval-mode yolo`: a headless session cannot answer an
approval prompt, so the exec-tier tools (bash, eval) fail closed and a card
that must run a command silently does nothing. Checkouts share this
repository's git dir, so the Integrator merges worker branches directly.

Do not edit the main checkout while a wave runs: its changes surface inside
every worker checkout and pollute their diffs. Shared rollup files (CHANGELOG.md, tests/ci-shards.json) belong to the
Integrator, never to a worker.

Usage:
    python scripts/dev/pf_wave.py --wave w2 --base master --dry-run
    python scripts/dev/pf_wave.py --wave w2 --base master
    python scripts/dev/pf_wave.py --wave w2 --status
    python scripts/dev/pf_wave.py --wave w2 --integrate
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STATE = REPO / ".work" / "waves"
OVNFS_FALLBACK = Path.home() / "go" / "bin" / ("ovnfs.exe" if os.name == "nt" else "ovnfs")


def ovnfs_bin() -> str:
    found = shutil.which("ovnfs")
    if found:
        return found
    if OVNFS_FALLBACK.exists():
        return str(OVNFS_FALLBACK)
    raise SystemExit("ovnfs not found: put it on PATH or set OVNFS_BIN")


def run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, cwd=str(cwd) if cwd else None, env=env, text=True, capture_output=True, encoding="utf-8", errors="replace"
    )


def cards(wave: str) -> list[tuple[str, Path]]:
    directory = STATE / wave / "cards"
    if not directory.is_dir():
        raise SystemExit(f"no cards: {directory}")
    return [(path.stem.split("-", 1)[-1], path) for path in sorted(directory.glob("*.md"))]


def checkout_path(wave: str, slug: str) -> Path:
    """ovnfs prints the checkout root; re-derive it the same way it names them."""
    root = os.environ.get("OVNFS_ROOT") or ("O:/" if os.name == "nt" else str(Path.home() / ".ovnfs"))
    return Path(root) / f"pf-{wave}-{slug}"


def worker_env(checkout: Path) -> dict[str, str]:
    """Isolate the scratch directories a subprocess may litter.

    HOME/USERPROFILE stay untouched on purpose: omp reads its provider and model
    configuration from there, and an empty HOME makes every worker fail with
    "model not found". Only TEMP/TMP move inside the checkout (.work/ is
    gitignored), which is what the product's subprocesses actually write to.
    """
    scratch = checkout / ".work" / "wave-home" / "tmp"
    scratch.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    for key in ("TEMP", "TMP", "TMPDIR"):
        env[key] = str(scratch)
    env["PAPERFORGE_WAVE_HOME"] = str(scratch)
    return env


def prompt_for(wave: str, slug: str, checkout: Path, base: str, card: Path) -> str:
    branch = f"wave/{wave}/{slug}"
    return (
        f"You are one worker in PaperForge wave {wave}. Your ONLY workspace is {checkout}\n"
        f"(a full copy of the repo at {base}). Work there; never touch the main checkout.\n\n"
        f"Commit your work on branch {branch}: `git -C {checkout} switch -c {branch}` (or reuse it),\n"
        f"`git add -A`, `git -C {checkout} commit -n -m '<what changed and why>'` (skip the\n"
        f"pre-commit hook: the Integrator runs the full gate once on the merged tree).\n"
        f"Do not merge, push, tag, or edit\n"
        f"CHANGELOG.md or tests/ci-shards.json — the Integrator owns those.\n\n"
        f"Run only the checks your card names. Report what you ran, the exact result,\n"
        f"and any claim you could not verify. If the card turns out to be wrong or\n"
        f"blocked, stop and say so instead of inventing scope.\n\n"
        f"--- CARD ---\n{card.read_text(encoding='utf-8')}"
    )


def launch(wave: str, slug: str, base: str, card: Path, args: argparse.Namespace) -> dict:
    checkout = checkout_path(wave, slug)
    log = STATE / wave / "logs" / f"{slug}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    record: dict = {"slug": slug, "checkout": str(checkout), "branch": f"wave/{wave}/{slug}", "log": str(log)}

    created = run([ovnfs_bin(), "new", "--name", checkout.name, "--rev", base], cwd=REPO)
    record["ovnfs"] = (created.stdout + created.stderr).strip()[-2000:]
    if not checkout.is_dir():
        record.update(status="checkout-failed", exit=created.returncode)
        return record
    record["checkout_reused"] = created.returncode != 0

    env = worker_env(checkout)
    cmd = [
        "omp", "-p", "--cwd", str(checkout),
        "--max-time", args.max_time,
        "--approval-mode", "yolo",
        "--model", args.model,
        prompt_for(wave, slug, checkout, base, card),
    ]
    with log.open("w", encoding="utf-8") as handle:
        proc = subprocess.run(cmd, env=env, text=True, stdout=handle, stderr=subprocess.STDOUT)
    record["exit"] = proc.returncode

    head = run(["git", "log", "--oneline", f"{base}..HEAD"], cwd=checkout)
    record["commits"] = [line for line in head.stdout.splitlines() if line.strip()]
    dirty = run(["git", "status", "--short"], cwd=checkout).stdout.splitlines()
    record["dirty"] = [line for line in dirty if line.strip()]
    record["status"] = "ok" if proc.returncode == 0 else "failed"
    return record


def write_manifest(wave: str, records: list[dict]) -> Path:
    manifest = STATE / wave / "manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"wave": wave, "workers": records}, indent=2) + "\n", encoding="utf-8")
    return manifest


def print_status(wave: str) -> int:
    manifest = STATE / wave / "manifest.json"
    if not manifest.exists():
        print(f"no manifest yet: {manifest}")
        return 1
    data = json.loads(manifest.read_text(encoding="utf-8"))
    for worker in data["workers"]:
        commits = len(worker.get("commits", []))
        dirty = len(worker.get("dirty", []))
        print(
            f"{worker['status']:<16} {worker['slug']:<22} "
            f"exit={worker.get('exit')} commits={commits} dirty={dirty}"
        )
        for commit in worker.get("commits", []):
            print(f"    {commit}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one PaperForge wave.")
    parser.add_argument("--wave", required=True)
    parser.add_argument("--base", default="master")
    parser.add_argument("--parallel", type=int, default=3)
    parser.add_argument("--max-time", default="40m")
    parser.add_argument("--model", default="sudocode/deepseek-v4-1-flash")
    parser.add_argument("--only", action="append", default=[], help="run only this slug (repeatable)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--integrate", action="store_true")
    args = parser.parse_args(argv)

    if args.status:
        return print_status(args.wave)
    if args.integrate:
        return integrate(args)

    selected = [(slug, card) for slug, card in cards(args.wave) if not args.only or slug in args.only]
    if not selected:
        raise SystemExit("no cards selected")
    if args.dry_run:
        for slug, _card in selected:
            print(f"would launch {slug:<22} from {args.base:<12} as {checkout_path(args.wave, slug)}")
        return 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.parallel)) as pool:
        futures = [pool.submit(launch, args.wave, slug, args.base, card, args) for slug, card in selected]
        records = [future.result() for future in futures]
    manifest = write_manifest(args.wave, records)
    print(f"manifest: {manifest}")
    return print_status(args.wave)


def integrate(args: argparse.Namespace) -> int:
    """One dedicated Integrator checkout, merging every wave branch in order."""
    manifest = STATE / "waves" / args.wave / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    branches = [worker["branch"] for worker in data["workers"] if worker.get("commits")]
    if not branches:
        raise SystemExit("no worker committed anything; nothing to integrate")
    # Worker commits live in the checkout's own git dir; import each branch into
    # this repository before anything can merge them.
    for worker in data["workers"]:
        if not worker.get("commits"):
            continue
        imported = run(
            [ovnfs_bin(), "apply", Path(worker["checkout"]).name, "--branch", worker["branch"]],
            cwd=REPO,
        )
        detail = (imported.stdout + imported.stderr).strip()[-160:]
        print(f"import {worker['branch']}: rc={imported.returncode} {detail}")
    checkout = checkout_path(args.wave, "integrator")
    created = run([ovnfs_bin(), "new", "--name", checkout.name, "--rev", args.base], cwd=REPO)
    if created.returncode != 0 or not checkout.is_dir():
        print((created.stdout + created.stderr)[-2000:])
        return 1
    command = (
        "You are the integrator for PaperForge wave " + args.wave + " in " + str(checkout) + ".\n\n"
        "Merge these worker branches one at a time, in this order:\n  " + "\n  ".join(branches) + "\n\n"
        "Rules: keep master as the product authority; resolve conflicts by the intent of both\n"
        "sides; you alone edit CHANGELOG.md and tests/ci-shards.json (regenerate the map with\n"
        "`python scripts/ci_shard.py --write`). Run the L2 gate once on the merged tree:\n"
        "`python -m pytest tests/test_architecture_boundaries.py tests/test_ci_coverage_contract.py\n"
        "tests/test_ci_shard_map.py -q`, `cd paperforge/plugin && npm run typecheck && npx vitest run`.\n"
        "Commit the merge on branch `wave/" + args.wave + "/integration` and report every gate result,\n"
        "including anything you could not verify.\n"
    )
    env = worker_env(checkout)
    log = STATE / args.wave / "logs" / "integrator.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as handle:
        proc = subprocess.run(
            ["omp", "-p", "--cwd", str(checkout), "--max-time", args.max_time,
             "--approval-mode", "yolo", "--model", args.model, command],
            env=env, text=True, stdout=handle, stderr=subprocess.STDOUT,
        )
    print(f"integrator exit={proc.returncode} log={log}")
    print(run(["git", "log", "--oneline", f"{args.base}..HEAD"], cwd=checkout).stdout.strip())
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
