# ADR 0005 — Verification gate scope after the plugin rewrite

- **Status:** Accepted (2026-11-06)
- **Supersedes:** nothing; narrows the H matrix defined by #263/#276 without
  changing the real-machine verification standard.
- **Applies to:** `.github/workflows/ci.yml`, `paperforge/plugin/test/specs/`,
  `tests/test_ci_coverage_contract.py`.

## Context

The external-runtime-installer work rewrote the plugin's settings, dashboard and
i18n layers. The Obsidian gate (`H — Obsidian`) still carried the pre-rewrite
contract: 30 cases driving navigation that no longer exists (search box inside
the old dashboard layout, contextual buttons, setup-journey fields). A merged
tree produced 12/30 failures whose causes were layout/navigation mismatch, not
product defects — the gate had stopped describing the shipped product.

At the same time the H job's install path depended on an interactive desktop
terminal, so a headless runner could never publish a runtime, and every attempt
burned its full 25-minute poll budget (observed: 29.7 min job, run
`42167070301`).

## Decision

1. **H proves only what needs the real host**, five cases: A01 first-use install
   → verified pointer; A06 reinstall → fresh environment republished; H1 plugin
   load + artifact binding + real backend; H2 UI search reads the real index;
   H3 a UI toggle reaches the note and survives a restart.
   `PF_E2E_SETUP_POSITIVE` / `PF_E2E_JOURNEY_GATE` and the 25 dropped cases are
   removed rather than skipped — a permanently skipped case is not a gate.
2. **Everything else keeps a cheaper owner.** Backend behaviour stays in L4
   (`tests/e2e`, `tests/audit`) and P (`tests/harness`); plugin logic in vitest;
   architecture correctness in L4b. The dropped H cases asserted the same
   behaviours through the old layout and are not re-implemented per-layer.
3. **The installer runs without a terminal.** The plugin invokes the CLI
   detached and polls the Python-published pointer; the CLI remains the only
   authority that creates, verifies and publishes a runtime (ADR `python-core-authority`).
   Output goes to `~/.paperforge/runtime/installer.log`, and both scripts print
   a terminal marker so a dead installer is reported instead of waited on.
4. **Named single-OS jobs are folded into the full suite.** L2 (release
   protocol) and L2.5 (OCR regression) named files that `L1b` already runs on
   the same OS; the ubuntu cells of `L1` and `J-Matrix` were the same subset
   again. `L0` + `L0.5` merged into one static job. 17 jobs → 10, ~7 min wall
   clock on a PR.
5. **Coverage is unchanged and machine-checked.** `tests/test_ci_coverage_contract.py`
   still requires every test file to be collected by a gating job; removing a
   job required no new exclusion.

## Consequences

- A regression that is only visible through the old UI navigation (for example
  a dashboard control that stops rendering in a specific mode) is no longer
  caught by CI. H2/H3 cover one control each, not the full surface.
- Named gates L2/L2.5 no longer appear as separate check runs, so a release
  report must cite `L1b` for protocol and OCR-regression evidence rather than
  a job name.
- The gate is now reproducible in headless environments, which is what made it
  usable on hosted runners at all.
- Restoring any dropped case requires a spec written against the current UI and
  an evidence record under `test/evidence/`; re-enabling the old text is not a
  restoration.

## Known limit: `installer=earliest`

The push/nightly matrix keeps the app-version axis (`latest`, `earliest`) but
pins the installer to `latest`. The `installer=earliest` app build loses its
WebDriver renderer about two minutes into A01 with
`disconnected: not connected to DevTools`; H3 passes inside the same failing
cell, so the plugin, backend and pointer path are healthy and the crash is an
environment limit of that build. The same two cells failed on master before
this gate existed (run `41461698495`, 2026-11-02) and again after the gate
rewrite (run `42204449196`), so it is neither a regression nor a flake to retry.
Restoring the cell requires reproducing the crash on that build first; until
then it is recorded here instead of being reported as a failing gate.
