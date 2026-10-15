# CLI-host acceptance harness

`tests/harness/` proves behaviour by driving the real `paperforge` CLI as a
subprocess against a disposable vault.  It exists because cases that need no
Obsidian were still being proven through real Obsidian + WebDriver — the slowest,
flakiest and least informative runner in the project — so the H matrix grew to
carry semantics it was never needed for.

## The boundary rule

A case belongs to the **CLI host** when its oracle can be stated from process- or
file-level facts: exit codes, NDJSON terminals, `probe` envelopes, file digests,
provider request ledgers.

A case stays on **H** (`paperforge/plugin/test/specs/paperforge.e2e.ts`) when its
subject *is* the host:

| Stays on H | Why |
|---|---|
| plugin load, bundle↔artifact binding, sandbox isolation | the Obsidian runtime is the subject |
| vault adapter / external note registration, path resolution through the Vault API | Obsidian's API is the subject |
| view rendering, localization, keyboard/focus, ribbon & settings surfaces | only a real DOM proves these |
| plugin unload, child reaping, autosync timers, native keyring | process/宿主 lifecycle owned by the adapter |
| app/installer version matrix (earliest/latest) | compatibility is host-specific by definition |

Everything else — install/pointer switch, sync convergence, OCR run/stop/redo/
rebuild, embed build/resume/stop, prune, reconcile R/P, versions restore, config
and credential authority, note flags — is a CLI contract and belongs here.

## How it runs

Local (any OS, no Obsidian, no wheel build):

```bash
python -m pytest tests/harness/ -m harness -v
```

CI: job **P — CLI-host acceptance** in `.github/workflows/ci.yml`, one Windows
cell (the declared P0 profile), uploading both the junit report and the evidence
directory.  L1b ignores `tests/harness/`, so each case runs once, in P.

## Evidence

Every case writes `tests/evidence/cli-acceptance/<CASE_ID>.json` and the run
writes `index.json`:

```json
{
  "case_id": "D04",
  "status": "VERIFIED",
  "runner_kind": "harness_cli",
  "source_sha": "<HEAD>",
  "host_profile": {"os": "Windows", "arch": "AMD64", "python": "3.11.x"},
  "commands": [{"argv": ["python", "-m", "paperforge", "--vault", "...", "ocr", "--json", "run", "FIXT0001"],
                "returncode": 130, "duration_ms": 12345, "stderr_tail": "..."}],
  "assertions": [{"name": "...", "ok": true, "detail": ""}],
  "artifacts": {"ocr-dir/meta.json": "<sha256>"}
}
```

`runner_kind` and `host_profile` are the fields the real-machine verification
standard already binds capability claims to; a per-area report can cite the
index instead of a hand-maintained table, and the index cannot drift from a
report because it is generated from the run that just happened.

A recorded assertion failure **also fails the pytest test** (the fixture raises
in teardown) — an evidence-only failure would let a red case report green, which
is the gate-that-cannot-fail class (#224).

## Ported cases

| Harness case | Subject | Replaces the H spec case |
|---|---|---|
| `B01` | initial sync materializes notes + canonical index, re-sync is a no-op | “performs an initial sync from the export into empty derived state” |
| `B02` | a changed export entry syncs; bystanders stay byte-identical | “syncs exactly the changed export entry and preserves the bystander paper” |
| `D04` | a running OCR batch stops cooperatively, `cancelled` terminal, rc 130 | “stops a running OCR batch through the workspace Stop control” |
| `D06` | derived OCR artifacts rebuild with zero provider requests | “rebuilds derived OCR artifacts locally without provider traffic” |
| `J02` | two-paper batch settles per paper; scope stays scoped | “runs a two-paper OCR batch with a rejected confirm, one success and one failure” |
| `F02` | staging writes nothing canonical; the reviewed R plan promotes; a second promote is a no-op | “stages render repairs in isolation and promotes the reviewed candidates” |
| `F03` | acceptance refuses without its evidence, and the commit half is recorded BLOCKED | same H case (its accept half) |

`F03` also carries the finding that made it worth porting: the P lane is
unreachable today — the staged final-plan and the canonical report disagree on
`proposal_id` (`figure_proposal_2` vs `inventory_proposal:figure:2`) and no CLI
command writes the report at all. The case asserts the refusal contract, records
`status: BLOCKED` in its evidence, and grows the commit half once an owner picks
the producer.

## Next candidates (host-agnostic, still on H today)

Ordered by value — the first two are cases whose H versions have already failed
silently once, so a CLI oracle buys correctness, not just speed:

| Candidate | Harness subject | H case it would replace |
|---|---|---|
| `E02` | memory restore from backup after corruption | “restores the memory database from its backup after corruption” |
| `E04` | stop a vector build; substrate uncorrupted | “stops a running vector build without corrupting the substrate” |
| `E05` | legacy ChromaDB → sqlite-vec migration | “migrates a legacy ChromaDB substrate into sqlite-vec” |
| `A03/A04/A05` | config write/readback/restart; legacy migration idempotence; credential reaches the keyring | the three matching `A0x` cases (keep their UI-label assertions on H) |
| `D05/D07` | OCR redo for a flagged paper; version restore | “re-extracts a flagged paper …”; “restores a display version through the Version History modal” |
| `B07` | workflow flag persists across a restart, and reverts when the backend refuses | the two B07 cases |
| `C03/E03` | build the vector substrate against a controlled provider, then serve deep search | “builds the vector substrate … and serves deep search” |

Roughly 15–20 further spec cases are portable by the boundary rule. Each one
moves only under the removal rule above.

## Removing an H case

An H case may be deleted only when **all** of the following hold:

1. its harness counterpart is green in hosted CI (job P), on the same source SHA;
2. the harness case asserts the same *observable* contract, not a weaker one;
3. any UI-wiring assertion the H case uniquely owned (button exists and is
   enabled, localized label, stable test id, confirmation gate) is either kept in
   a smaller H case or explicitly recorded as dropped at the release gate.

Rule 3 is what keeps the #294/#218 class (dead affordance, missing i18n key,
unstable selector) covered: those are host facts and cannot be proven from a CLI.
