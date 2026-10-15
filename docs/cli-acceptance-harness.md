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
| `D05` | a flagged paper is re-extracted through **one fresh** provider job | “re-extracts a flagged paper through the workspace redo control” |
| `D07` | a display-version restore writes the display copy, never the canonical text — **BLOCKED on #227** | “restores a display version through the Version History modal” |
| `A04` | legacy config migrates losslessly and the second run is byte-identical | the two matching `A04` cases |
| `E05` | a legacy ChromaDB substrate migrates into sqlite-vec; no store is a no-op | “migrates a legacy ChromaDB substrate into sqlite-vec” |
| `E06` | a missing memory database is detected with an action, and that action repairs it | “detects and repairs a missing memory schema through doctor and repair” |
| `E01` | one action is described, preflighted and executed with visible effects | “executes an action through the client (memory.build)” |
| `A06` | provider requests follow canonical config; a dead endpoint fails instead of falling back | “proves provider config authority through UI, restart, and a controlled embed request” |

`E05` needs the optional `legacy-vector` runtime (chromadb), so job P installs
`.[test,vector,legacy-vector]` — the extras the full-suite job already uses. A case
that branched on an absent dependency would be a skip in disguise (R2), and a
registered skip is what the H version has.

`E04`'s stop leg is verified **with a caveat the evidence pins down**: the stop is
honoured at the build's next safe point, so a forced rebuild of one paper took 46 s
before it answered `cancelled` (rc 130) — a user clicking Stop waits that long. And a
stop written **before** the build reaches its provider is *not* honoured: the child
produces no further output and is killed by the harness deadline (observed at 180 s,
420 s and 90 s). On Windows this stdin token is the only cooperative ingress — SIGTERM
is a hard kill — so the plugin's Stop only ends such a build through its kill
escalation. The case asserts the invariant either way (the live substrate is
byte-identical and still serves) and records the early-stop hazard as its blocker when
that is the path taken.

`D07` reports **BLOCKED**, not VERIFIED: the restore also rewrites OCR-owned
`meta.json`, and issue #227 tracks whether that matches the command's "display-only"
declaration. Its own contract (the canonical text is never replaced by the display
copy) is asserted and passes; the blocker records the declaration drift, so the case
does not read as a clean verification. For the same reason its H case stays.

`D05` also records a fixture-shaped constraint: the redo path resolves a paper by
its ``zotero_key`` and requires exactly eight alphanumerics (``_find_notes_by_key``
in ``worker/ocr.py``), which is the real Zotero key shape — the render fixture's
synthetic ``TSTONE001`` is nine characters, so the keyed redo counts it as failed
by design. That case runs on the standard vault instead.

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

**None left.** Every spec case that a CLI-host oracle can state is now ported; the
remaining ones are host-bound by the boundary rule (plugin load and bundle binding,
view rendering and localization, ribbon/settings surfaces, plugin unload and child
reaping, autosync timers, the client trace, artifact opening through the shell, and
the app/installer matrix itself).

`E06` also records a finding worth an issue: the H case's title claims doctor detects
and repairs a missing memory schema, but with `paperforge.db` deleted, `doctor --json`
reports `FAIL` over its own 71 checks and never mentions memory, and `repair --fix`
does not restore the database. The memory lane is **probe → advertised action**.

## Removal plan (prepared, not applied)

Deleting the ported cases from the spec is mechanical, but it is **not yet
authorised**. This is the prepared list so the shrink is one commit when its
preconditions hold.

### Preconditions (all three)

1. job **P** green in hosted CI on the shrink's product SHA — it has never run
   upstream, the job and the PR-tier matrix exist only on this branch;
2. the owner admits CLI-host evidence into the verification standard. That
   standard defines 真机证据 as H/V/P and places a real-CLI-subprocess case in the
   **I** layer, so today a capability whose only evidence is job P reverts to
   待测试 (R1). Admitting it is a vocabulary decision — `runner_kind=harness_cli`,
   a `host_profile` form, and an archive slot such as `evidence/ci/<run>/cli-p0/`
   — not a code change;
3. the owner approves the reduced acceptance set: the acceptance plan requires
   explicit approval for any scope reduction, and deleting spec cases moves the
   candidate's *acceptance-test identity* while leaving the release source alone.

### Deletion list (the 13 declared cases; D05/D07 follow the same shape)

| Harness case | H block (spec lines) | Orphans to delete with it |
|---|---|---|
| B01 | 2325–2416 | — |
| B02 | 2417–2497 | — |
| J02 | 3203–3482 | `clickProcessSelected`, `addOcrPaper` |
| D04 | 3483–3792 | — |
| D06 | 3900–3979 | — |
| E03 | 3980–4195 | `PF_E2E_VECTOR_CASE` and the skip-registry entries `vector-case-opt-in`, `vector-fixture-lacks-structured-blocks` |
| E02 | 4196–4318 | — |
| E04 | 4319–4666 | (same switch and registry entries) |
| F02+F03 | 4839–5220 | — |
| B07 (both halves) | 6281–6397 | `readFrontmatterFlag`, `clickTechnicalDetails` |
| A03 | 7252–7380 | `doctorChecks` — keep 7381: its reject half asserts UI copy the harness does not |
| A05 | 7581–7750 | `E2E_KEYRING_FILE`, `keyringText`, `filesContaining`, `runAuthDelete`, `credentialAvailable` |

Post-shrink the spec goes from 47 static cases + one six-scenario loop to 34 + 6,
with 13 fewer sandbox re-provisions and 18 fewer in-case Obsidian restarts per
cell. The declared wait budgets inside the deleted blocks total ≈76 minutes
across the three cells — a ceiling, not measured runtime.

`D05` and `D07` are **not** in this list: they were ported after it was drafted and
have not been through the same review, and `D07` is BLOCKED rather than VERIFIED.

### Second batch (ported after the first list was drafted)

| Harness case | H block (spec lines) | Orphans to delete with it | UI-wiring dropped |
|---|---|---|---|
| `E05` | 4667–4725 | nothing (the case drives the migration function through a subprocess, no DOM) | none |
| `A04` | 7440–7524 and 7525–7580 | the shared A-block helpers stay: A03's reject half (7381) keeps `waitForTestId`/`setInputByTestId`/`clickSettingsTestId` | the migration summary text and the settings values it shows |
| `E06` | 4726–4838 | nothing (client calls + CLI subprocess) | none |
| `E01` | 5449–5480 | nothing | to catalogue from the block before deleting |
| `A06` | 5481–5930 | `provisionE2eKeyringFixture` stays (it serves the install cases); its own provider stub is inline | the settings fields + memory module panel (partly shared with A05) |

### UI-wiring each deletion would drop (the rule-3 record)

| Case | Host facts that disappear |
|---|---|
| D04 | the Stop control's test id and enabled state, and the localized stop acknowledgement (the #294-class fact) |
| D06 | Rebuild-Selected's test id and its no-confirmation contract |
| F02/F03 | the whole quality drawer: toggle, staging text, R-row/P-card counts, Promote/Accept located by text with enabled state, optional confirm gate |
| J02 | rejecting a confirmation returns the modal to closed; per-synthesized-title row matching |
| A05 | the memory module panel, the masked-input assertion, the "not configured" copy path |
| B07 | the technical-details toggle, the `flag-analyze`/`flag-do_ocr` checkboxes, the DOM revert on refusal, the client-trace wait |
| A03 | the Save-enabled assertion and stage-2 re-hydration after a restart |
| E02/E04 | nothing — both drive the client, not the DOM |
| D07 (if ported) | the entire Version History modal, including the cancel leg |

Every row must end up either kept in a smaller H case or recorded as dropped at
the release gate; that record is what the shrink commit has to carry.

## Removing an H case

An H case may be deleted only when **all** of the following hold:

1. its harness counterpart is green in hosted CI (job P), on the same source SHA;
2. the harness case asserts the same *observable* contract, not a weaker one;
3. any UI-wiring assertion the H case uniquely owned (button exists and is
   enabled, localized label, stable test id, confirmation gate) is either kept in
   a smaller H case or explicitly recorded as dropped at the release gate.

Rule 3 is what keeps the #294/#218 class (dead affordance, missing i18n key,
unstable selector) covered: those are host facts and cannot be proven from a CLI.
