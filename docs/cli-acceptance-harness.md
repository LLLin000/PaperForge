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

`status` is `VERIFIED`, `FAILED`, or `BLOCKED`: a case whose subject is
implemented but unreachable records `case.blocked(reason)` and reports BLOCKED,
because an unreachable capability is not evidence and the index must not read it
as covered.

## Ported cases

| Harness case | Subject | Replaces the H spec case |
|---|---|---|
| `B01` | initial sync materializes notes + canonical index, re-sync is a no-op | “performs an initial sync from the export into empty derived state” |
| `B02` | a changed export entry syncs; bystanders stay byte-identical | “syncs exactly the changed export entry and preserves the bystander paper” |
| `D04` | a running OCR batch stops cooperatively, `cancelled` terminal, rc 130 | “stops a running OCR batch through the workspace Stop control” |
| `D06` | derived OCR artifacts rebuild with zero provider requests | “rebuilds derived OCR artifacts locally without provider traffic” |
| `J02` | two-paper batch settles per paper; scope stays scoped | “runs a two-paper OCR batch with a rejected confirm, one success and one failure” |
| `F02` | staging writes nothing canonical; the reviewed R plan promotes; a second promote is a no-op | “stages render repairs in isolation and promotes the reviewed candidates” |
| `F03` | acceptance refuses without its evidence, then commits the reviewed plan by its exact hash | same H case (its accept half) |
| `A03` | a config edit is canonical, resolvable, and refused edits write nothing | “A03 config edit: a path set in Settings reaches paperforge.json, doctor reads it back, and a restart keeps it” |
| `A05` | a secret reaches the keyring, never argv, never a vault file | “A05 credential storage: a key saved in Settings reaches the keyring — never config/vault …” |
| `B07` | a workflow flag persists on the canonical note; a refused toggle writes nothing | “persists a workflow flag toggled in the UI, across a restart” + its refusal branch |
| `E03` | the substrate builds against the configured provider (its ledger proves it) and serves a search | “builds the vector substrate against a controlled provider and serves deep search” |
| `E04` | a stopped vector build leaves the live substrate byte-identical and still serving | “stops a running vector build without corrupting the substrate” |
| `E02` | a valid `paperforge.db.backup` restores atomically; corrupt copy kept, backup untouched | “restores the memory database from its backup after corruption” |

Two rules the retrieval cases had to learn, both written into their docstrings:

* the substrate binds to the provider endpoint it was built with, so a case must
  keep **one** stub for build and query — re-pointing the endpoint between them
  makes the query return nothing;
* **nothing in the CLI creates `paperforge.db.backup`** — the restore case seeds it
  the way the H case does (a copy of a known-good database).

`A03` also documents a resolution rule worth knowing before writing another case:
the directory fields are **resources-relative**, so `literature_dir = Resources/Literature`
is accepted and resolves to `Resources/Resources/Literature`. The case pins the
resolved path rather than the raw field for that reason.

`F03` also carries the finding that made it worth porting: the P lane used to be
unreachable in three layers — the Windows reparse guard refused every path, a
missing report crashed the CLI, and the staged plan and the canonical report named
the same proposal differently while no CLI command wrote the report. All three are
fixed; the flow it asserts is the one a real vault takes now:
audit → stage → promote (which refreshes the report acceptance checks against) →
stage again → accept by exact plan hash.

## Next candidates (host-agnostic, still on H today)

Ordered by value — the first two are cases whose H versions have already failed
silently once, so a CLI oracle buys correctness, not just speed:

| Candidate | Harness subject | H case it would replace |
|---|---|---|
| `E05` | legacy ChromaDB → sqlite-vec migration | “migrates a legacy ChromaDB substrate into sqlite-vec” |
| `A04` | legacy config migration is idempotent (byte-identical on the second run) | the two matching `A04` cases |
| `D05/D07` | OCR redo for a flagged paper; version restore | “re-extracts a flagged paper …”; “restores a display version through the Version History modal” |

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
