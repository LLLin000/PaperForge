# OCR-v2 Active Queue

> **Current priority (2026-09-20): Plugin major-release acceptance — ACTIVE, rc.5 prerelease validated, final release blocked.** Frozen identities: `candidate_evidence_sha=56407222f2782c616518f55a3e0d3fe33d200aeb` (candidate acceptance tests), `release_source_sha=76c179451f6ca6d6dfa863a1ad8f00cf3aa7ce27` (2.0.0 product code/artifact source), and `metadata_head=8d04f02a63549c5837ce00420b306d350cb1b525` (public metadata state). W22 `RELEASE_READY` is **NO-GO**; rc.5 is a bounded installer/Obsidian validation artifact, not final `2.0.0` authorization. Complete the owner support contract and W18–W21 before W23 final publication. W19 PR #252 head `7f2215f1` passes Hosted `35521317438` across all three declared Windows app/installer cells; candidate rebinding is still required because the repair changed product/artifact content.
> **Architecture gate / Block B + Review v2 final closure (2026-09-11):** #229 delivered in `b89e745f`; #222 orphan-prune wire coverage verified in `421867d9`, #223 probe action classification verified in `2215a4bf`, and #231 live architecture generator + golden-pin checks delivered in `48cb888f` with follow-up `b04bff5a`. Review v2 final closure `6f15160f` binds `emit` to a saved deterministic plan, re-derives its normalized selector against the digest-bound Contract/Survey, rejects tampered scope and gate packets, and removes independent emit-time narrowing. Focused process tests are **54/54** and the deterministic benchmark is **11/11** executable fixtures. Hosted run `34617059623` passes all 15 CI jobs, including L1b, all three J-Matrix jobs, L4b, E2E, plugin, Ruff, and aggregate checks. Empirical v1/v2 A/B remains deferred/not-run; owner release gates remain authoritative.
> **Effort assessment:** §15 of the plan, [INFERENCE] 60–100 new real-host scenarios, 110–180 new/extended I·U tests, 15–40 product fixes, 57–75 issues (±40%).
> **Release acceptance checkpoint (2026-09-20):** W04 A06 remains bounded positive and mismatch-preservation evidence using Release-N `1.5.15`, remote `master` version `2.0.0`, the candidate wheel, fresh-child verification, and runtime-pointer publication rules. rc.5 GitHub/PyPI publication, clean-vEnv install, real Obsidian retry, pointer republication, and final five-module control-center state are verified on Windows 11 / Obsidian 1.13.7. W18 resilience/performance, W20 live provider/quality, and W21 final artifact/rollback/docs evidence remain open. W19's PR-branch H matrix is green on `35521317438`, but candidate rebinding and owner release acceptance remain pending.
> **Last updated:** 2026-11-05. Runtime ownership is cut over: installation/update/repair run only through the external installer, which the plugin opens from a single Foundation action; vault setup appears after the runtime is ready. Published PyPI `1.5.15` predates the `runtime` subcommand, so the bootstrap needs a matching release before the button works against PyPI. Architecture deterministic substrate and Review v2 remain hosted-CI verified; `RELEASE_READY=NO-GO` and no `2.0.0` publication decision.

## 2026-11-05 Runtime ownership cutover + installer-first UI
| Item | Status |
|---|---|
| Plugin authority | The plugin no longer runs pip, creates venvs, publishes/repairs the pointer, or carries in-app install/update code. `NodeProcessTransport.launchRuntimeInstaller()` is the only child-process entry for runtime work; it writes a platform script (`.cmd` / `.command`) and opens a visible terminal (`start "" cmd /k …` / `open -a Terminal …` / `x-terminal-emulator -e sh …`). |
| Installer steps | The terminal runs `python -m pip install --user --upgrade paperforge==<version>` then `python -m paperforge runtime <install\|update\|repair> --expected-version <version>`; the pointer is published only by that second step, after candidate verification. |
| UI sequencing | Foundation detail renders ONE entry point: `安装运行环境`/`更新运行环境`/`修复运行环境` while the pointer is missing or unready; `打开配置向导` (vault config) only after the runtime is ready. The overview card dispatches `installation.install_runtime` (verb `install`). Manual commands stay available under a collapsed `手动安装命令`. |
| State truth | An absent pointer overrides a cached `ready` envelope, and a newly published pointer re-probes installation, so the header can no longer contradict the runtime rows. |
| Localization | Added runtime status/installer keys (EN+ZH); fixed leaked raw keys `foundation_setup`, `foundation_vault_missing`, OCR status keys and the memory panel's English gaps; removed the dead refresh toast and stale installer strings. |
| UX audit (screens) | Fresh profile no longer pops release notes; the overview drops the duplicate title and reads "先完成基础环境 / 请先完成基础环境——受管运行环境尚未安装。"; the attention count only covers rendered modules and ignores transient `checking`; blocked modules report `installation.required` instead of `invalid_response`; no per-module refresh toasts. |
| Library stage (guided) | Stage 2 is a three-step walkthrough — 1 choose Zotero directory (with the menu path to find it) → 2 Better BibTeX export *into* the exports folder with “Keep updated” (folder path with 复制/打开文件夹/重新检测; copying a file in is not offered at all, because only Zotero’s own export keeps the JSON current) → 3 “配置文件夹” lists the four folders inline, then 保存并同步. Only the current step is expanded, finished steps collapse to a summary with 修改, and Continue unlocks only when the library is `ready`. Verified on a fresh vault: typed Zotero path → real file-picker import (landed in `<vault>/System/PaperForge/exports`) → save + sync → `library.ready`, `paper_count=1`, Continue enabled. |
| New-user pass | Overview gained a single “开始设置 / 继续设置” action and one statement of the blocker (the triple “需要注意 / 部分模块需要关注 / N 项需要关注” and the dead counter are gone); stage 1 never offers “repair” before the runtime status is known, hides installer controls once ready, and shows “正在安装…” while polling; optional features show an amber “需要填写 API 密钥” instead of a green “未配置”, name the selected agent platform, and explain where each key comes from; folder labels are plain (系统/资源/文献笔记/文献表格). Full four-stage walk on a reset vault (ready → Zotero → export → folders + sync → optionals → review → 完成) ended on the overview with `_setup_complete=true`. |
| Backend risk fixes | Applied every open finding from the 2026-11-05 scan: runtime environments are pruned to current + one previous (`_prune_environments`, tested three ways, cancel removes the candidate and keeps the pointer); OCR version census now logs and counts an unreadable `meta.json` as stale instead of dropping it; audit git probes bounded; the 44 unmapped backend reason codes all have zh/en copy now (audit resolves full then bare code, 0 unmapped). |
| Whole-UI user pass | Walked the remaining surfaces (OCR workspace, orphan/confirm/issue/version modals, migration modal, dashboard search + issue panel) and closed the English leaks: orphan modal buttons/badges (`Deselect all` / `Delete N selected` / `Keep all` / `no PDF`), issue-draft labels and redaction line, migration modal, 29 dashboard strings (issue titles, R/P staging, next-step sentences, search), and the memory row now uses the localized reason instead of the raw `config.not_found` sentence. The OCR empty state no longer claims "no OCR data": an empty library explains that the library is not synced and offers 打开仪表盘, while an empty filter offers 清除筛选. The dashboard banner distinguishes a missing config from an unresponsive Core. |
| Dashboard + ribbon | Ribbon uses the built-in `book-open` icon (the custom `addIcon(<svg>)` string rendered a nested SVG and collapsed to a tiny box). Dashboard opens as a main tab instead of the fixed-width sidebar leaf, and the panel is responsive: `min-width:0` on flex children, wrapping status rows, 2-column pills under 420px (measured 300/382/982px with no horizontal overflow). Chrome localized (banner, 文献概览 / 系统状态 / 开始工作, rows, buttons); the failure banner clears via a flag rather than by matching English copy. |
| Settings tabs audit | Walked 帮助 and the 基础环境 / 文献库 / OCR / 智能检索 / Agent 详情 panels. Fixed: help no longer repeats "帮助" as eyebrow (now 使用指南); library drops the duplicated error block for a simply-missing config and shows 孤立记录 instead of "Orphans"; memory shows the localized reason and “打开安装向导” instead of the backend’s English “Setup PaperForge” (shared `_actionLabel`), including the impact box; 基础环境 header can no longer claim 已就绪 while the runtime status is missing/timed out (pointer-first correction before the header render, plus a 20 s status watchdog that surfaces a timeout instead of hanging without an action). |
| Visual pass | Setup flow and control-center summary restyled on Obsidian theme variables: step cards with numbered badges, green completed chips, accent current step, underline "修改" links, pill progress chips, monospace path chip with 复制/打开文件夹, accent primary button and a bordered secondary. Control-center summary is now badge + one title + one sentence + one action. |
| Backend fixes from that run | `setup/checker.py` no longer reports "pip not found" when the `python -m pip --version` probe merely times out (10 s → 60 s, timeout is inconclusive); the wizard derives the exports folder as `<vault>/<system_dir>/PaperForge/exports` instead of from un-hydrated config, so an import can never land outside the folder `sync` reads; the save step always chains `sync` instead of guessing from a just-requested probe. |
| Library stage (guided) | Stage 2 is now a three-step walkthrough — 1 choose Zotero directory → 2 export/import Better BibTeX JSON (**required**, the folder list is the only optional disclosure) → 3 save + sync. Only the current step is expanded; finished steps collapse to a summary with 修改. The drop zone and click-to-select actually copy files into the canonical exports folder, and step 3 chains `sync` so `library.index_missing` cannot dead-end; Continue unlocks only when the library is `ready`. |
| Dependency finding (open) | `[vector]` still installs `chromadb` on this branch although runtime health/probe prefer sqlite-vec; the lean split exists on `master`. Porting it changes download size and install verification, so it is tracked separately in §3 rather than mixed into this UX change. |
| Verification | Plugin **439/439**, tsc clean, bundle **330.6kb**; Python focused gate **183 passed**; disposable-vault Obsidian 1.15.0: not-ready → single install button, click → terminal script spawned (observed `cmd /k …paperforge-runtime-*.cmd` → `pip install --user`), ready → single setup entry; overview and wizard stages 1–2 re-captured after the UX pass. Isolated no-Obsidian install with the branch wheel reached `runtime.ready`, `vector_ready=true`. |
| Open blocker | Published PyPI `1.5.15` has no `runtime` subcommand and its `[vector]` extra omits `sqlite-vec`, so the button's bootstrap only completes end-to-end once a matching release ships. Bump the plugin and package version together at release; do not claim the button works against the current published package. |
| Release impact | Product change in the plugin; candidate rebinding required. `RELEASE_READY=NO-GO` unchanged. |

## 2026-09-28 Runtime install-path hardening (frontend UX lane)
| Item | Status |
|---|---|
| Detection | `RuntimeBootstrap.inspectRuntimeState()` added: reports pointer presence/version, venv presence, discovered vs configured interpreter, and whether the venv's paperforge matches the expected version. Read-only; no guessing. |
| Decision | `ensureRuntime()` added and is now the single production entry from `SettingTab._installFoundation`: nothing → fresh install; venv-without-pointer → repair; older pointer → in-place update; matching runtime → `none` (skips install, proceeds to `setup`). |
| Old-package handling | Upgrade/repair keeps the existing venv and runs `pip install --upgrade --force-reinstall paperforge[vector]==<pinned>` instead of recreating it, so stale/conflicting packages are replaced without dropping the rest of the venv. |
| Cleanup safety | The previous unconditional `rm -rf venv` on any failure is gone. Only a venv created by the current run is removed; a pre-existing runtime survives a failed upgrade. |
| Configured python_path | `settings.python_path` is now honored as the venv **base** interpreter (previously ignored entirely). Acceptance is decided by running `--version` (>=3.11), not `existsSync`, because discovery yields bare command names (`py`, `python3`). pip always targets the venv interpreter — never a system Python. |
| Verification | Plugin suite **480 passed / 480 (all green)**; tsc clean; bundle 335.1kb. Real host probe: pointer `2.0.0rc5`, venv match `true`, discovered `py 3.14.0`. |
| Handshake bug fixed | The lane uncovered a real fail-closed defect: `handshake` accepted only 3 of the 6 probe states Python emits. `paperforge/commands/probe.py` returns `installation.runtime_pointer_missing` / `_stale` / `runtime_executable_missing` before `setup` publishes the pointer — the exact state `ensureRuntime`'s repair path creates. `handshake` rejected them as "unexpected", which would have failed the repair install. Three tests already encoded the correct contract and were red on HEAD; the accepted list now matches Python's emission. |
| E2E baseline | Real-Obsidian e2e (22 specs) is **18 passing / 2 failing / 2 skipped**, failing only on candidate version binding (`Expected "2.0.0", Received "2.0.0rc1"` at spec lines 414 and 1911). **Proven pre-existing**: an identical run with the plugin checked out at HEAD fails the same two tests at the same lines. Cause is sandbox provisioning — the sandbox runtime venv still holds `2.0.0rc1` while `manifest.json` is `2.0.0`. The spec never drives the install path (it only reads `_setupOperation`), so `ensureRuntime` is not exercised by e2e and this change cannot affect it. |
| Known limitation | `compareVersions` is numeric-only, so prerelease-suffixed versions (`2.0.0rc5` vs `2.0.0`) yield `NaN` and take the `reinstall` label instead of `upgrade`. Install behaviour is identical either way (same pinned pip command); only the surfaced label is coarse. |
| Release impact | Product change in the plugin; candidate rebinding required. `RELEASE_READY=NO-GO` unchanged. |

## 2026-09-14 Candidate certification checkpoint
| Item | Status |
|---|---|
| Slim cleanup PR #234 | Merged to `master` at `9f770d130b27a8c699a4fec06310485facd2d965`; architecture authority files retained without generated projections. |
| Sanitized public candidate | `candidate_evidence_sha=56407222f2782c616518f55a3e0d3fe33d200aeb`; internal planning/agent paths absent; product release source `76c179451f6ca6d6dfa863a1ad8f00cf3aa7ce27`; branch `release/2.0.0-public-candidate`. |
| Hosted certification | Candidate CI `34805876718` 15/15; product-source master CI `34806652889` 15/15; Pages `34806652917` 2/2; public manifest PR #236 CI `34808724645` 15/15; post-merge Pages `34809127248` 2/2. |
| A06 remote lifecycle | Bounded disposable Release-N `1.5.15` positive switch and fresh-child `2.0.0` verification passed; forced mismatch preserved the old pointer; this is not public artifact acquisition. |
| Release gate | `RELEASE_READY=NO-GO`; freeze the owner support contract first, then complete W18–W21 and owner acceptance; public PyPI/GitHub distribution and actual-download smoke are W23; no publication performed. |
| Owner support contract | BLOCKED — owner must decide supported OS/arch/Python/Obsidian/installer/providers/Release-N/upgrade/rollback/performance/quality/spend/privacy before W18–W21 can certify a scope. |
| W18 resilience/performance | OPEN — budget, soak, fault/竞态, and first-failure evidence not frozen/accepted. |
| W19 supported environment / installer | **PR-BRANCH H VERIFIED, RELEASE GATE OPEN** — PR #252 head `7f2215f1`; Hosted `35521317438` passes all required jobs and all three declared Windows combinations (`earliest/earliest`, `latest/earliest`, `latest/latest`). J01 now registers physically existing external notes through the Obsidian Vault boundary with restore-on-failure protection. This does not bind the frozen candidate or close owner support, native keyring/SQLite/file-lock, first-use setup, W18, W20, or W21 gates. |
| W19 repair bundle follow-up | **IMPLEMENTED AND HOSTED-VERIFIED, NOT CANDIDATE-BOUND** — production `main.js` rebuilt at `d1ee3f9d`; final PR head `7f2215f1`; candidate rebinding remains mandatory. |
| W20 live provider / quality | OPEN — owner-approved live OCR/embedding samples, keyring, quality, privacy, and spend evidence remain incomplete. |
| W21 release artifact / rollback / docs | OPEN — candidate clean install/upgrade/rollback, artifact consistency, migration/support docs, and publish-failure recovery remain incomplete. |


## 2026-09-15 RC.5 prerelease checkpoint
| Item | Status |
|---|---|
| Release commit | Master bump `8a1a45a1`; probeAll fix PR #242 merged at `22cacc21`. |
| Hosted gates | CI `34933570855` **15/15**; Pages `34933570902` **2/2**; Publish `34934126941` **success**. |
| Public prerelease | GitHub `2.0.0-rc.5` prerelease plus PyPI `2.0.0rc5` wheel/sdist verified. |
| Real install | Initial UI attempt failed; exact clean-vEnv spec installed in **208s**; UI retry completed and pointer is `2.0.0rc5`. |
| Real Obsidian state | Windows 11 / Obsidian 1.13.7: all five modules `已就绪`, OCR/memory expected notices, `0 项需要关注`; cold `probe all` measured **145s**. |
| Final gate | `RELEASE_READY=NO-GO`; final `2.0.0` publication remains blocked on owner support scope and W18–W21. |

## 2026-09-16 Lean vector dependency checkpoint
| Item | Status |
|---|---|
| Core install | `[vector]` now contains only `openai`, `socksio`, and `sqlite-vec`; ChromaDB is no longer installed for normal users. |
| Legacy migration | ChromaDB is isolated under `[legacy-vector]`; old-store migration reports the combined `[vector,legacy-vector]` install when the optional dependency is absent. |
| Verification | Focused Python **26 passed / 1 warning**; final wheel metadata verified; clean lean vEnv **38 distributions / 7,217 files**, `pip check` clean, no `chromadb`; combined legacy-extra import passed. |
| Release impact | Product change in the candidate worktree; candidate rebinding is required after commit. `RELEASE_READY=NO-GO`; W18–W21 and owner support acceptance remain open. |
## 2026-09-17 Runtime/bootstrap hardening checkpoint
| Item | Status |
|---|---|
| Runtime authority | Managed `~/.paperforge/runtime/pointer.json` is authoritative after installation; invalid or failing pointers fail closed instead of falling back to stale vault/global interpreters. |
| Health boundary | `runtime-health --json` returns structured `ok=true` degraded capability status when optional vector imports fail; core read/write/build health remains visible. |
| Bootstrap contract | Uses the executing absolute skill directory, actual isolated import verification, pointer status, verified interpreter, and observed runtime version; no shell/CWD path guessing. |
| Verification | Focused regression/runtime gate **71 passed / 1 warning**; broken vault venv returned valid degraded JSON; managed pointer runtime returned green health; source bootstrap selected the published pointer. |
| Release impact | Working-tree product change; candidate rebinding and candidate-bound hosted gates are required. `RELEASE_READY=NO-GO`; owner support scope and W18–W21 remain open. |

## 2026-09-18 Clean rc.5 integration checkpoint
| Item | Status |
|---|---|
| Authoritative base | Fresh `chore/integrate-stale-root` worktree at `origin/master` `8a1a45a1`; dirty root remains untouched. |
| UX source | Local `61bc8400` replayed as `1af72888`; obsolete internal ledgers and old `main.js` were excluded, then the current source rebuilt the bundle. |
| Runtime hardening | Pointer-first fail-closed bootstrap, lazy optional embedding imports, structured health boundary, degraded optional-vector status, and pointed-interpreter repair verification migrated without lean-vector/package/version changes. |
| Verification | Focused runtime **70 passed / 1 warning**; scoped Ruff clean; Literature-hub source `runtime-health --json` returned fully healthy; two builds produced `main.js` hash `5d117108eae15ca3be6042c513088922`. |
| Release impact | Product work is integrated but not candidate-bound or owner-accepted. `RELEASE_READY=NO-GO`; candidate rebinding and W18–W21 remain required. |
| PR / review | PR #243 merged (`cd6d9fc86e1110b4edf9e32df54cff8ece782658`), CI 15/15 at `35d2189e`; PR #245 squash merged on `chore/integrate-stale-root` (`5902c8ac`, fixes #244). Owner instruction: "继续吧". `origin/master` advanced from `8a1a45a1` → `cd6d9fc8`. Local dirty root still at `61bc8400` (preserved, untouched, not rebased/pulled/reset). `RELEASE_READY=NO-GO`; candidate remains unbound. |
## 2026-09-20 W19 hosted matrix checkpoint
| Item | Status |
|---|---|
| Evidence branch | PR #252, head `7f2215f1`; the product bundle was rebuilt at `d1ee3f9d`. |
| Failure preservation | JUnit/Vitest/audit artifacts upload only after failure; no retry or `continue-on-error` laundering. |
| Hosted matrix | Hosted `35521317438` is green: `earliest/earliest`, `latest/earliest`, and `latest/latest` all pass, together with the existing required jobs. |
| Repair | Dashboard re-registers an adapter-created note by reading and removing the physical file, recreating it through `Vault.create`, and restoring the original content if registration fails. Local dashboard runtime is **16/16**; typecheck/build pass. |
| Release impact | W19 H evidence is verified for the PR branch. Candidate rebinding, owner support scope, W18/W20/W21, and `RELEASE_READY` remain open; no publication is authorized. |
## 2026-09-18 PR merge decision
Owner instruction: “你没测试好的测试一下吧” followed by “继续吧”. Verified post-merge state: both stacked PRs merged cleanly (no conflicts), hosted CI absent on #245 by workflow design, real-Obsidian smoke not run. Merging = acceptance onto master; **not** release — W18–W21 / owner contract / candidate rebinding still required before any rc/candidate/bundle publish. |
| Verification | `npx vitest run` → **500 passed / 27 files**; `npm run build` passed; regression tests cover refresh failure after a successful global load and the same failure in paper mode. |
| Review | Standards: no findings. Spec: prior P1 resolved; no new P0/P1. #244 closed. |
| Evidence limits | No hosted CI (workflow triggers only on `main`/`master`); no real-Obsidian visual smoke (executable not discoverable). `RELEASE_READY=NO-GO`; candidate remains unbound. |
| Merge evidence | `git fetch origin master` → origin/master = `cd6d9fc8` (was `8a1a45a1`). Local dirty root unchanged: HEAD = `61bc8400`, 37 modified + 16 untracked paths preserved. Worktrees intact; no git add -A incident after recovery lesson recorded. |
## 2026-09-17 Whole-repository design audit
| Severity | Finding | Evidence / required closure |
|---|---|---|
| P0 | Source `ManagedRuntime` handshake and tracked `main.js` disagree. | Selected plugin architecture/runtime gate has **3 failures**; rebuild/remove divergence and make the same handshake contract pass. |
| P0 | Node transport, settings, dashboard, and worker status can bypass the published runtime pointer. | Restore one pointer-owned dispatch seam; configured/vault/global Python cannot be a post-install command target. |
| P1 | Vector packaging/setup/health disagree on whether Chroma is normal or legacy-only. | Reconcile extras and capability contract in one source of truth. |
| P1 | Updater accepts unvalidated archive extraction and sequential in-place copies; rollback cannot remove newly created files. | Validate archive layout and prove atomic replacement plus rollback through traversal/mid-copy/new-file tests. |
| P1 | UI receives raw stderr/argv/path/error text; bootstrap copies lack parity enforcement. | Redact at Node→UI seam and test canonical/deployed bootstrap equality. |
| P2 | Full Ruff has **478 diagnostics in 94 files** while CI selects only undefined-name failures. | Choose and enforce the baseline; do not equate the narrow CI check with repository style health. |
| Scope | Audit applies to the current dirty working tree only. | Focused Python **13 passed**; selected Vitest has **3 failures**; full Ruff exits non-zero. `RELEASE_READY=NO-GO`. |
| Revalidation | `origin/master` at `8a1a45a1` already has pointer-only dispatch in Node transport, Settings, and Dashboard; focused runtime/bundle gate **58/58** and production bundle rebuild has no textual diff. These P0s apply to stale dirty local `master` (`61bc8400`, 1 ahead / 31 behind), not current release base. Preserve and integrate local work in a dedicated worktree; do not pull/rebase the root directly. |


## 2026-09-16 Frontend interaction blocker audit (UX review)
| Phase | Blocker | Severity | Root cause |
|---|---|---|---|
| Install | Python missing → Dashboard inert, no path to Settings wizard | P0 | `resolvePython()` null → all ops silent; error text generic |
| Install | Setup Journey `failed` state has no retry button | P0 | `_installFoundation` catch sets `_setupOperation="failed"`, no re-dispatch |
| Install | Flatpak/Snap/macOS auto-download disabled → cryptic message | P0 | `platformGate()` returns three codes, UI only shows one generic string |
| Daily | Global-mode search input does nothing | P1 | `executeSearch()` only wired in collection/paper mode |
| Daily | "Open Literature Hub" fails with `[!!]` if `.base` missing | P1 | no fallback / no Settings guidance |
| Daily | Version restore has no loading state | P1 | `versionsRestore()` awaited with no progress UI |
| Daily | Auto-sync vs OCR OperationLock not mutually exclusive | P1 | separate guards; Python process contention possible |
| Edge | Release-notes modal force-blocks first open | P2 | `_checkReleaseNotes()` unconditional |
| Edge | OCR Workspace view does not auto-refresh on reveal | P2 | `open()` uses `revealLeaf`, no reload |
| Edge | Version compare reads symlink/cross-volume path → hard fail | P2 | `fs.readFileSync` on Python-returned `source_path` |
| Decision pending | User wants a smooth install UX design for non-technical users — see discussion below; not yet scoped into an issue. |

## Historical checkpoints (not current candidate certification)

The dated checkpoints below preserve prior evidence and prior next-step wording. They do not supersede the current priority above or certify a new major-release candidate.

> Status: `EXECUTABLE_FROZEN a42f8bb7` / `PROTOCOL_DOCS 781910f3` — S1–S6 lightweight **COMPLETE** on `462398cb` (valid for `a42f8bb7`, `ruff` clean). Hosted CI `32353318123` on docs-only descendant `a2e18fa4` is **green: All Checks Passed, 14/14**, with `3.11` Ubuntu/macOS/Windows, J-Matrix, Ruff, plugin, OCR, E2E; no executable change after `a42f8bb7`. #191 FROZEN / ready-for-agent; #81 OPEN / owner gate. Reconcile recovery/fulltext safety follow-up is closed on disposable fixtures; P authority acceptance is transaction-safe and bound to the exact human-reviewed plan hash; the 969-paper unverified-content census is clean; semantic coverage and all production writes remain owner-gated.
> Last updated: 2026-09-08
> Tickets 01–06 all CLOSED (06 — 31c5a321, owner-verified after corrective rounds 1+2): Library and Render Quality fully route through `PaperForgeClient`; sync follow-up semantics preserved via the shared orchestrator; R/P review renders actual staged crops with Open preview. Next: Ticket 07 (legacy bridge deletion + architecture enforcement).
> Stage 2 step 6 item 6 presentation-path containment (owner audit): single exit `_safe_artifact_path` (resolved containment) now gates every Python-returned presentation path — `list_backups` drops escaping entries, `versions list` validates each child via `_paper_root`, `show`/`list` `current_path` and `_with_paths` sources fail closed; producer consumes the SSOT via `format_pre_rebuild_backup_name`. Evidence: Python versions **10 passed + 2 skipped** (symlink tests POSIX-only); ruff clean on touched files; no TS change.

> Stage 2 step 6 item 6 final corrective (owner audit): `versions` key/label canonical containment (key = OCR root direct child; label must exact-match an authority label; resolve() containment on paper_root/source/target; unsafe manifest entries dropped) + legacy backup filename/timestamp SSOT extracted to `parse_pre_rebuild_backup_name`/`backup_stamp_to_iso` and consumed by producer/pruner/versions (real producer-format regressions incl. `.NNN` seq identity); provenance reported as best-effort (`provenance_persisted`); dead `toolArgvFor`/`buildCommandArgs`/import-only helpers removed; tombstone count corrected to 8. Evidence: Python 9+9 passed; plugin **446/446**; tsc clean; Gate A/B/C/D 11/11.

> Stage 2 step 6 items 5+6 + FINAL CLOSURE — (A) python-bridge contracted to a pure helper module (child_process import = 0; dead runtime surfaces deleted; env/PATH bootstrap moved to the transport root; node-transport authority 2→4). (B) version-history.ts TOMBSTONED — new Python authority `paperforge versions list|show|backups|paths|restore` (discovery/manifest/legacy-backup timestamps/canonical paths/restore copy/provenance); pure version-diff.ts keeps only the text diff. (C) Gate D final zero-census + single-construction gate; tombstones 7 files; plugin **450/450**, Python focused **87 passed**, tsc clean, Gate A/B/C/D 11/11, bundle rebuilt. Ticket 07 closure candidate pushed for owner audit.

> Stage 2 step 6 item 4 DONE — LongTaskClient engine merged into `client/node-transport.ts` (engine block diff = 0 lines vs HEAD: pure move); `services/long-task-client.ts` tombstoned; #137 10-event parser + fail-closed semantics and PAPERFORGE_STOP/grace/taskkill/POSIX-group cancellation preserved verbatim; **Settings fallback client deleted** (getClient binds plugin.getClient or throws — no second OperationLock owner); Gate: node-transport = sole authority (2), long-task-client tombstoned, python-bridge Gate B 7→6 (dead runLongTask engine removed). Evidence: plugin **475/475**; tsc clean. Remaining: python-bridge contraction to the root, final zero-census gate, Ticket 07 close.

> Stage 2 step 6 item 3 packaging corrective: the action-client.ts deletion was missing from the item 3 commit's staging list (working tree had it deleted; HEAD shipped the stale file + its dead runSubprocess import) — deletion now actually committed together with the dead `SubprocessResult` interface. Gates re-run against the committed state: tsc clean, Gate A/B/C 9/9, plugin **473/473**. Item 4 precondition recorded: Settings' fallback `new PaperForgeClient({ NodeProcessTransport })` must be deleted (plugin.getClient singleton only).

> Stage 2 step 6 item 3 DONE — action-client/next-actions execution convergence: `action-client.ts` tombstoned (DTOs + `buildActionArgv` → `client/action-contract.ts`); bridge contract = one async `runAction` capability bound to the SAME singleton `client.runAction` at all 3 `orchestrateFromSync` callers (main/Settings/Dashboard); orchestrator in-flight guard covers REAL settlement (async await, settle-then-clear #169); no automatic unlocked bypass; `runSubprocess` + legacy `runAction` deleted from python-bridge (Gate B 8→7). Evidence: plugin **473/473** (5 deleted-surface tests removed); tsc clean. Remaining: long-task-client → NodeProcessTransport merge, python-bridge contraction to the root, final zero-census gate.

> Stage 2 step 6 item 2 corrective (round 4): unterminated-frontmatter false-success closed — shared `split_frontmatter_block` parser (adapter), command validates the block BEFORE mutation (invalid → VALIDATION_ERROR rc 1, no write, changed never true); command I/O now raw (read+write newline="") → byte-preserving CRLF/LF on every platform; CRLF fixture writes explicit bytes (no OS translation dependency); BOM tolerated at the CLI entry. Evidence: Python note-flag **13 passed**; ruff clean.

> Stage 2 step 6 item 2 corrective (round 3): the round-2 fence handling was substring `split("---", 2)` — an inline `---` inside a frontmatter VALUE truncated the block and corrupted the title on reassembly. `set_frontmatter_flag` is now line-anchored (exact-fence lines only, BOM tolerated, per-line CRLF/LF preserved, unterminated fence refuses). Evidence: Python note-flag **11 passed**; ruff clean. Item 3 design APPROVED WITH AMENDMENTS (6 rules in ticket 07 doc; code HELD until item 2 closes): singleton `client.runAction` injection (3 callers: main/Settings/Dashboard), action-client.ts full tombstone → `client/action-contract.ts`, orchestrator in-flight covers real settlement (async), NO automatic bypass, same-commit `runSubprocess` deletion → python-bridge Gate B 8→7.

> Stage 2 step 6 item 2 corrective (round 2): P1-1 `setNoteFlag` now settles with `finally { invalidateCache() }` — epoch advances on success AND rejection (frozen generation invariant); P1-2 `set_frontmatter_flag` operates strictly on the frontmatter segment (strict `---` split, append inside the block, body byte-identical; frontmatter-less note fails closed). Evidence: plugin **476/476**; Python **7 note-flag regressions**; tsc + ruff clean. Census scope ruling (owner): `version-history.ts` is semantic read-model + artifact mutation — must converge to Python (discovery/manifest/current-label/restore/provenance); OCR-workspace version preview: presentation-only artifact display (Python-returned path → read → diff) may stay host-side, but backup filename recognition, timestamp semantics, path construction, restore copy, and provenance mutation are Python surface work.

> Stage 2 step 6 in progress — item 1 DONE (`ef32ff52`): cast-form provenance probe fixed (TypeAssertion/AsExpression/paren/non-null unwrap), Gate B snapshots stayed exact. Item 2 DONE: final-leaf census first closure — `processFrontMatter(do_ocr/analyze)` retired; new Python surface `note set-flag` (strict field allowlist, unquoted YAML bool via `set_frontmatter_flag`, idempotent no-op, fail-closed unknown field/key/missing note); client `setNoteFlag`; toggle reverts on backend rejection. Evidence: plugin **475/475**; Python focused **73 passed**; tsc + ruff (touched files) clean. Next: remaining census items (action-client/next-actions convergence → long-task-client → NodeProcessTransport → python-bridge contraction → zero-census gate).

> Post-closure frontend-interface completion: client layer is now host-agnostic (`client/probe-types.ts` owns probe DTOs; `transport.ts` owns stream types; no obsidian/constants/host-impl imports) and fully typed (`Promise<any>` gone; `AuthorityMutationResult`/`RenderAuditDTO`/`PaperStatusDTO`/`ActionPreflightDTO`); Gate E pins host-agnosticism + the 21-method surface. OB wiring verified via real-bundle smoke against an Obsidian API stub (all 25 public methods present; plugin dir is a reparse point into the test vault). Evidence: plugin **447/447**; tsc clean.

> **Ticket 07 CLOSED / SEALED — 7ed1930c** (owner-audited 2026-09-08). Thin-client authority cutover complete: step 5 sealed 27c33f4b; step 6 items 1–6 closed (cast-form gate, note mutation authority, action/next-actions convergence, LongTask→NodeProcessTransport, python-bridge contraction, final census + Gate D + read-side containment). Frozen invariants: process authority = `client/node-transport.ts`; action authority = `PaperForgeClient`; semantic interpretation/identity/durable mutation = Python; long-task ownership = singleton client; UI fs use = host context + contained Python-returned presentation paths. Ticket 07 is closed to further hardening — next work is a new architecture frontier (kernel/control-plane), not cleanup of this ticket. Known non-blocker: TOCTOU symlink retargeting needs fd-level opens (filesystem-capability concern, deliberately out of scope).

> **Stage 2 step 5 CLOSED / SEALED — 27c33f4b** (owner-verified 2026-09-08 after 3 corrective rounds): semantic boundary (frontmatter overlay, canonical-file reads, filename inference, export fs scan, filename watcher all deleted), cold-start wiring (`_bootstrapDashboard` = load first, then resolve), failed-load recovery contract (quiet always fetches; acquire/render split; single fetch per path), real-onOpen regressions. Step 6 UNBLOCKED: cast-form architecture probe fix → final leaf semantic census (incl. `processFrontMatter(do_ocr/analyze)`) → action-client/next-actions convergence → long-task-client → NodeProcessTransport → python-bridge contraction → zero-census gate → Ticket 07 close.

> Stage 2 step 5 recovery-contract corrective (round 3) — round 2 left a sticky-failure hole: the quiet loader's legacy `quiet && !_cachedStats` race guard made Refresh/Doctor/Repair permanent no-ops after a failed cold open, and Doctor/Repair refreshed cache without re-rendering. Fixed by contract only: quiet = fetch without presentation side effects; `_loadDashboardData` acquires, `_refreshCurrentMode` renders (every caller exactly one fetch); Doctor/Repair = invalidate + re-render; successful acquisition clears the stale failure message. Evidence: plugin **470/470** with two recovery-on-real-onOpen regressions; Python focused **31 passed**; tsc + ruff clean. > Stage 2 step 5 production-wiring corrective (round 2) — the semantic-boundary fix left the cold path broken: `onOpen()` never called `dashboardStats()` and acquisition was gated by the never-created `_metricsEl`, so every mode rendered an empty cache ("Not found in index", export missing). Fixed by splitting acquisition from presentation: `_loadDashboardData()` (no DOM gate) + `_bootstrapDashboard()` (load first, then resolve) wired into `onOpen()`; dead `_fetchStats`/`_renderStats`/`_renderOcr` metrics path deleted; `_refreshCurrentMode` awaits the fresh payload; leaf-change resolves `paper-lookup` once (P2); `paper-lookup` query/--from-path is exactly-one-of (P2). Evidence: plugin **468/468**; Python focused **40 passed**; tsc + ruff clean. Prior round: > Stage 2 step 5 semantic-boundary corrective — `overlayEntryWorkflowState` (frontmatter overlay into the Python DTO) deleted; `_resolveModeForFile` is Python authority via new narrow surface `paper-lookup --from-path --json` (canonical index → note frontmatter → workspace key matched against the index, fail-closed unknown → Base basename → literature domain); `zotero-path.ts` tombstoned; System-Status export health reads `check_permissions().can_sync` (exports-dir fs scan retired); `formal-library.json` filename watcher deleted. Evidence: plugin **467/467**; focused Python **66 passed**; tsc + ruff (touched files) clean.

> Stage 1 CLOSED — 97fa1e6d (binding-provenance authority gate + exact-snapshot ratchet). Stage 2 step 1 done: `main._autoSync` → `client.sync()` + shared orchestrator; main.ts provenance snapshot 2 → 1.
> Stage 2 step 1 CLOSED — production 504825e5 + evidence 092fdea0. Stage 2 step 2 done + contract corrective: config-client.ts dissolved by responsibility; `config-client.ts` tombstoned; migrate DTO split to the real Python wire (ConfigSetData ≠ ConfigMigrateData); `_executePfResult` recovers the authority reason from transport-rejection stdout (layer split: process semantics in Transport, PFResult semantics in client).
> Stage 2 step 3 done + contract corrective: `main.requestOcrRun` + `settings._dispatchOcrAction` (run/rebuild) → shared `client.runAction` (`ocr.run`/`ocr.rebuild_derived` only — the fake canonical `ocr.redo` route deleted, stale envelopes fail-closed to re-probe); Stop → `cancelActiveOperation`; failure notices surface availability_reason; production-entry regression for `requestOcrRun`. `ocr-process-controller.ts` + its test tombstoned. Stage 2 step 4 done: settings semantic commands → typed client (foundation.update via runAction; embed migrate / memory restore-backup / runtime-health / auth set --stdin typed; `_callPython` + dead `_runSetupPython` deleted); step 4 corrective: authSetSecret/memoryRestoreBackup invalidate in finally (mutation contract, regressions pin the stale-cache bug); legacy credential migration split — secret-storage keeps only SecretStorage read/clear and receives a `writeCredential` capability bound to `client.authSetSecret(..., {replace:false})`; MigrationSpawn/backend argv knowledge deleted; settings.ts now has ZERO child-process sites (off HOST_SEAMS). Stage 2 step 5 done: dashboard/modals leaf callers → client (version/doctor/repair/dashboardStats typed; `_runAction` + main command palette routed; gate-probe undercount of cast-form `(execFile as any)` corrected); dead PaperForgeSetupModal + embed-build-controller deleted. Ratchet: main/dashboard/modals all 0. step 5 corrective: _fetchStats consumes the unwrapped dashboard DTO (+2 production-entry regressions); Dashboard canonical-file inspection retired — Python `dashboard --json` now carries the canonical `items` (narrow read surface), `_loadIndex`/fs reads gone, collector assertion flipped to enforce the retirement. Stage 2 complete pending owner verification.


## 2026-09-03: Ticket 04 OCR Workspace & Processing Domain Cutover — corrective closure

- **Initial cutover:** paper rows use `probe("lineage")` plus typed `queryOcrPapers()`; Run OCR, user-facing Redo, and Rebuild Derived use descriptor-gated canonical actions; Stop uses the client-owned cancellation handle.
- **Review corrections:** `ActionExecutionHooks` now pass stop/progress/item-result callbacks into real OCR and rebuild workers; the Workspace consumes wire `event.phase`, fails closed without a shared client, clears dynamic descriptors on read refresh, and sends OCR keys as separate CLI arguments.
- **Verification:** real CLI tests cover rebuild event ordering and worker-safe-point cancellation (`PAPERFORGE_STOP`, `rc=130`); **103 passed, 1 skipped** focused Python tests; **63 plugin tests passed**; `npm run typecheck` clean. No OCR/render materialization ran.
## 2026-09-03: Ticket 05 Knowledge & Retrieval Domain Cutover

- **Vocabulary:** Python and TypeScript agree on the 10 frozen #137 stream events (`start`, `preflight`, `phase`, `progress`, `paper_settled`, `heartbeat`, `item_result`, `result`, `error`, `cancelled`).
- **Worker streaming:** `ActionExecutionHooks` passes `stop_check`, `on_progress`, and `on_item_result` directly into `run_embedding_build`; silent service mode eliminates stdout capture and legacy `EMBED_PROGRESS:` tokens; single token owner.
- **Pre-publish safe point:** `run_embedding_build` checks `_is_stopped()` after verification before irreversible `_shadow.publish()`.
- **Search & Retrieval:** `dashboard.ts` cuts over `executeSearch()` to `client.search(query, options)` and `client.retrieve(query, options)` with unwrap normalization; `--no-expand` added to CLI for wire parity.
- **Smart Retrieval:** `settings.ts` memory/embed build dispatches route through `client.runAction()`, streaming progress, strictly failing closed on cross-domain action IDs, and wiring Stop only when `client.isOperationActive()`.
- **Verification:** **107 passed, 1 skipped** focused Python tests; **448 plugin tests passed**; `npm run typecheck` clean. No production write ran.

### 2026-09-05: Ticket 05 corrective round 2

- **Fail-closed entrypoint:** `_runAllowedDispatch("memory")` is an exhaustive exact-ID chain — `embed.build`/`embed.resume`/`memory.build`/`memory.rebuild`/`memory.upgrade_backend` dispatch, unknown IDs fail closed (Notice + re-probe, no substitution); the dispatched run/rebuild_index branch `return`s so legal actions never fall through to the unknown-pair probe; production-entry `it.each` regression proves `memory.build` and `memory.rebuild` reach `client.runAction` with the exact ID while unknown IDs never run.
- **Stop ownership:** `_renderMemoryDetail` Stop renders only when `client.isOperationActive()`; legacy `embedController.busy/stop` fallback and tests pinning execFile memory-build dispatch deleted.
- **Verification:** Python focused **169 passed**; plugin **448/448** (incl. production-entry allowlist regression); `tsc --noEmit` clean; ruff clean on changed files.

## 2026-09-05: Ticket 06 Library & Render Quality Domain Cutover — corrective closure

- **Review verdict:** initial cutover complete but reviewer found 5 contract gaps (4 P1); all closed in one corrective.
- **A (sync CTAs):** Dashboard Global / Collection / per-paper next-step sync buttons route through the shared `_runLibrarySync()` → `client.sync()`; sync never re-enters `_runAction`/`spawn`.
- **B (wire):** `renderReconcileStaging` sends `render reconcile KEY --json` (positional; `--keys` never existed); real-parser regression rejects `--keys`.
- **C (authority results):** client `_executeStructuredJson` preserves rc=1 stdout JSON (`STALE_PROPOSAL`, `STALE_REVIEWED_PLAN`, `R_GATE_FAILED`) as normal responses on `renderAudit`/`promoteR`/`acceptProposal`.
- **D (refresh):** committed R/P mutation clears staging AND re-runs `renderAudit`; structured rejections force re-stage + re-review.
- **E (evidence):** Python staging DTO projects `decision`/`caption_text`/`member_refs` from the reviewed final plan (DTO == plan bytes, asserted); P cards render caption/member blocks/preview/decision/hash; R rows show staged preview. TS never reads staging files.
- **Verification:** plugin **461/461**; `tsc` clean; Python focused **266 passed**; ruff adds no new findings.

### Corrective round 2 (final 2 P1)

- **A′ sync follow-up:** `_runLibrarySync` feeds the sync PFResult through the SAME `orchestrateFromSync` consumer as Settings — automatic-local next_actions still execute, consent-required work stays pending; no legacy spawn re-introduced.
- **E′ preview artifacts:** staged crops render inline (`<img>` from the Python-returned path) with an explicit **Open preview** action (Electron shell / window.open fallback) on R rows and P cards — human review sees the exact candidate, never a bare path.
- **Verification:** plugin **463/463** (17 cutover cases); `tsc` clean; reconcile core untouched.

## 2026-09-02: Reconcile Core Frozen & Backend Contract Mapping Established

- **Reconcile Core Frozen:** Core mutation engine (Audit → Staging → R/P/Blocked → CAS/Journal/Rollback → Commit) is frozen under `docs/RECONCILE-EXTENSION-CONTRACT.md`. No new heuristic detectors or mutation logic will be added to Reconcile. Future detectors operate strictly as read-only finding producers conforming to the minimal finding schema.
- **Backend Contract Blueprint:** Established `docs/BACKEND-FRONTEND-CONTRACT-MAPPING.md` defining Python Backend Authority as SSOT across 5 contracts (Observation, Deficit, Policy, Operation, Authority-Write) and 6 product projection domains (Foundation, Library, Processing, Knowledge/Retrieval, Maintenance, Render Quality).
- **Next Lane:** Transition to Backend Surface Rationalization & Frontend Thin-Client Mapping (`PaperForgeClient`).

## 2026-09-02: Stale render-consistency report invalidation

- **Fail-closed boundary:** `write_render_outputs` validates the automatic audit result and, on an exception or non-object result, atomically replaces any prior `render.consistency.json` with a structured `state=FAILED` execution-failure report. If replacement itself fails, it attempts to remove the old report.
- **Projection:** lineage therefore exposes `FAILED` (or `NOT_RUN` after best-effort cleanup) after a new render's automatic audit failure; it never projects the prior `CLEAN`/`DEGRADED` status as current.
- **Verification:** focused reconcile suite **132 passed, 2 skipped, 1 warning**; `render_audit.py` targeted Ruff, both changed Python modules `py_compile`, and `git diff --check` passed. No production mutation.

## 2026-09-02: P authority acceptance hardening

- **Authority action:** `accept-proposal` now shares the paper-scoped writer lock with R, requires the exact SHA-256 of the human-reviewed `final-plan.json`, a nonempty lowercase 16-hex live snapshot, exact staged paths, and the plan's exact `member_refs`; it never selects a same-label plan by mtime.
- **Atomic production boundary:** one schema-v2 journal covers the canonical JPG, Markdown, `figure_inventory.json`, materialization provenance, and proposal report. Each target uses atomic replacement; failed post-audit restores all snapshots before commit; a committed journal keeps production authoritative through cleanup/report-refresh failure and remains recoverable.
- **Verification:** **5 new review-token regression tests passed; focused reconcile suite 126 passed, 2 skipped, 1 warning**. The two symlink tests remain skipped on Windows `WinError 1314` due missing privilege. No production mutation or front OCR/render change.

## 2026-09-02: Exact human-reviewed plan binding

- **Review token:** `render reconcile --json` exposes `p_details[].final_plan_hash`, computed from the exact staged `final-plan.json` bytes. `accept-proposal KEY LABEL --plan-hash HASH` scans all safe matching staging candidates by that hash; no match returns `STALE_REVIEWED_PLAN`.
- **Deterministic duplicates:** identical plan bytes use a stable path tie-break; live snapshot, destination CAS, journal, rollback, and post-audit gates remain unchanged.

## 2026-09-01: Recovery and fulltext safety follow-up

- **R journal recovery:** schema version 2 is required; transaction paths must be exactly `.paperforge-r-promotion/<32-hex-id>`, destinations are limited to `assets/figures/*.jpg`, `render/figures/*.md`, and `render/materialization.provenance.json`, and backups must be integer `.bak` files inside that transaction directory. Symlinked roots/entries are rejected.
- **Fulltext authority:** missing, unreadable, or malformed canonical inventories produce `F0_CANONICAL_AUTHORITY_UNAVAILABLE`, set `mutation_blocked`, and emit no patches, including orphan/reserved embed candidates.
- **Committed reporting:** a post-commit report refresh failure is explicit (`ok=true`, `committed=true`, `report_refresh=failed`) and never triggers rollback of committed artifacts.
- **Verification:** focused reconcile suite **114 passed, 1 warning**; Ruff `E,F,I,UP` and `py_compile` clean. No production mutation or front OCR/render change.

## 2026-09-01: Committed cleanup hardening and R-content census

- **Committed journal recovery:** after `state=committed`, production remains authoritative; recovery no longer requires backup files, cleanup is best-effort, and the journal is removed without rollback. A cleanup `OSError` on the original committed call returns `committed=true, cleanup=pending` with `cleanup_error`; the journal remains for the next recovery.
- **Raw path safety:** destination and backup checks inspect raw path components before `.resolve()`; symlinked production, transaction, and backup paths fail closed.
- **Final audit semantics:** report-write success is `report_refresh=written`; a returned audit `state=FAILED` is separately exposed as `report_audit_state=FAILED`; exceptions/non-object results remain `report_refresh=failed`.
- **Read-only census:** `D:\L\OB\Literature-hub\System\PaperForge\ocr` scanned **969** paper directories with `write_report=False`: **0 affected papers, 0 affected objects, 0 audit failures**. No production mutation.
- **Verification:** focused reconcile suite **116 passed, 2 skipped, 1 warning**; symlink tests skipped on Windows `WinError 1314` due missing privilege. Ruff, `py_compile`, and `git diff --check` passed.

## 2026-08-31: D1 status sync

- **R:** duplicate canonical IDs, cross-canonical asset claims, duplicate provenance paths, malformed provenance/journal states, and unsafe object IDs are detected and blocked; selected exact R plans stage in isolation; manifest v2, plan hash, destination CAS, journaled rollback/recovery, post-audit checks, and explicit promotion scope are implemented.
- **Canary:** disposable evidence remains PASS: 12 objects tested, 11 successful promotions, 1 expected page-range/materialization failure, and 11 second-promote no-ops. Fresh isolated `2ZBAK9VY/figure_003` fails only its own staged-source gates. No production write has run.
- **R production blockers:** implementation P0-A/P0-B gates are closed and focused-covered. Production rollout remains owner-blocked; semantic figure-coverage defects are still report-only.
- **R detection boundary:** report and dry-run expose `R_CONTENT_UNVERIFIED` for existing artifacts without authoritative output hashes and block provenance mismatch/ambiguity; they do not prove semantic coverage loss such as a panel absorbed by `table_html`. No automatic merge or overwrite.
- **P/fulltext:** bounded-slot anchors now derive from unique, non-conflicted `main` rows; missing-page candidates block safely. Fulltext duplicate canonical IDs and unavailable fulltext block all patches. No production mutation.


## 2026-08-26: Reconcile-only R promoter

- Reconcile remains independent from the stable OCR/front-render pipeline; no `ocr_figures.py`, `ocr_objects.py`, `ocr.py`, or `ocr_rebuild.py` changes.
- Read-only census: 965 papers scanned; 182 papers contain 250 duplicate canonical figure-ID groups (224 conflicting, 26 identical).
- Audit/reconcile now blocks ambiguous IDs and R staging passes only selected exact plans.
- Added `paperforge render promote-r KEY [OBJECT_ID...] --json`; mutation scope is explicit (`OBJECT_ID` or `--all`). It consumes a verified `r-manifest.json`, checks live snapshot, canonical uniqueness, cross-object `(page, block_id, bbox)` claims, destination CAS, staged image/markdown facts, markdown link, and staging provenance before journaled atomic promotion. Production inventory is not rewritten.
- Verification: focused promoter + reconcile/audit/lineage/CLI/docs suite **114 passed, 1 warning**; targeted Ruff `E,F,I,UP` clean. Post-audit rollback, four hard-kill recovery points, paper writer lock, and cross-object claims passed. A 12-object disposable set produced **11 successful promotions + 1 expected page-range failure**; all 11 second promotes were no-ops.
- Next gate: explicit owner authorization only. No production batch rollout. Evidence: `project/current/render-reconciliation/r-canary-results.json`.

## 2026-08-20: S1–S6 lightweight certification (EXECUTABLE_FROZEN 462398cb → a42f8bb7)
- **S1 PASS:** `setup --modular` → `probe installation ready`, `status` 0 papers, `doctor` only Zotero/BBT optional fails. #191 gap: still deploys `.agents/skills` and retains `skill_dir/command_dir/agent_platform`.
- **S2 PASS:** `status` 2 papers, `probe` ready, `runtime-health`, `paper-status`/`read`/`search` succeed after `memory build`, `retrieve --paper` scoped, `reconcile`/`sync --dry-run` honest. No failure due to `.obsidian`/plugin cache.
- **S4 PASS:** `action list`, `reconcile`, `prune` dry-run, `action preflight`, `UNKNOWNKEY` → `PATH_NOT_FOUND`, `config validate` valid→corrupt→valid. No fabricated `healthy`.
- **S5 PASS:** `action run ocr.run` without `--confirm` → `confirmation_required` rc3; with `--confirm` → ok; `action run --force` → `unrecognized arguments`; `prune --force` safe. Boundary enforced.
- **S3 PASS:** `setup → memory build → search → read → retrieve --paper → embed status/preflight` chain without Obsidian; `embed.build --confirm` → explicit `401 invalid_api_key` (fail-closed, expected without valid key). Restart re-`read` persists.
- **S6 PASS (partial):** `config corrupt` → `config.corrupt` fail-closed; restore → `valid` + `setup` repeat idempotent + `probe ready` + `read` persists. Remaining S6 sub-paths (stale/malformed pointer, offline, OCR resume, Release-N reinstall) remain owner gate.
- Triage: **No RC blocker** in lightweight gates. #191 real gaps: skill deploy in SetupPlan, retired config fields, missing `setup inspect/plan/apply/verify` + `plan_stale` + verified-switch `relocate` + `external_action/secure_external`. Performance remains debt. Matrix: `project/current/cert-462398cb-S1-S6-matrix.md`. Correct language: **S1–S6 lightweight certification complete; S6 partial / owner gates remain** (not `S1–S6 PASS`).
- Next: **Do not build `462398cb+46c4ddaf+b66fde53` candidate.** `EXECUTABLE_FROZEN a42f8bb7` is the dead-code release-hygiene fix on top of `462398cb` (`3312/0` local + hosted tree green). Remaining **RC Owner Closure**: 1) Managed Runtime / Plugin browser (stale/non-ready/restart/fail-closed/cache), 2) M2/M3 live process (mixed outcomes/cancellation/Ctrl+C/scoped embed), 3) S6 full recovery (malformed/stale pointer/offline/interrupted update/OCR resume/embed resume), 4) Release-N reinstall + support-window owner decision. Hosted CI run `32353318123` is green on docs-only descendant `a2e18fa4` (no executable change after `a42f8bb7`); no new code candidate needed. Keep `#191` FROZEN. Research `Source Routing` / `Visual Evidence` deferred post-RC.

## 2026-08-18: Census closure and remaining RC gates

- Frozen recovery scope `R=958`; current formal/live-export scope `F=964`:
  seven normal Authority additions and one confirmed residual removal.
- Current production state is frozen as **964 Authority = 944
  OCR/retrieval current + 19 `nopdf` terminal + 1 `pdf_missing`**.
- Vector state is **933 current + 3 `no_content` terminal + 8
  `not_embedded` actionable**. No retrieval-current paper is stale/unknown and
  no `memory.build` candidate exists.
- The eight vector deficits are the exact scoped `embed.resume` evidence set:
  owner-approved preflight → explicit confirmation → settlement → fresh probe.
  No production mutation was run.
- `R2PSFXY4` is a sync-confirmed residual outside Authority. Reader-gate
  exclusion is contract-proven; targeted live serving evidence remains open.
  Do not prune solely for census presentation.
- Next: complete the scoped embed gate, residual serving smoke, exact-candidate
  frontend/hosted evidence, and rollback/support-window owner decision. No
  release/tag/package publication.

## 2026-08-18: Sync latency diagnosis

- Full `sync --json` latency was dominated by full reconcile, not the
  unchanged-index path: per-paper lineage lookup reparsed the canonical
  `formal-library.json`.
- Working-tree fix builds one canonical-PDF map per lineage observation.
  Production read-only reconcile measured **144.61 s → 48.38 s**; no
  re-OCR, rebuild, embed, prune, or production sync rerun was performed.
- Disposable sync plus lineage/reconcile regressions: **167 passed, 1
  warning**.

## 2026-08-17: M4 blocker checkpoint

- Frozen candidate `6ef0dfe9` reported retrieval `current` over a corrupt
  published carrier after a body-unit mutation; repair commit `46c4ddaf` maps
  this to retrieval/vector `stale` and `memory.build`.
- Preflight and reconcile disagreed on the canonical per-paper first frontier;
  repair commit `46c4ddaf` makes preflight project reconcile's intent.
- Focused regression gate: **126 passed, 1 warning** across lineage, reconcile,
  embedding eligibility, and action registry.
- No re-OCR/rebuild/embed is required for valid existing materializations.
  Corrupt retrieval carriers require `memory.build`; embed follows only after
  retrieval becomes eligible.
- The census divergence is now closed separately; repaired code remains outside
  the frozen candidate and follows the normal candidate/dependent-gate path.

## 2026-08-13: RC audit checkpoint

- Wayfinder #135 and final authority cutover #174 are complete, owner-accepted, and closed.
- Real Obsidian exercised setup/config, Python-owned credentials, sync/reconcile, OCR run/rebuild/redo/cancel, embed confirmation/build/cancel/retry, memory automatic actions, runtime recovery, navigation, and restart persistence.
- All 9 observed defects are repaired: stale credential truth, 30s probe timeout, missing credential remediation, hidden/incorrect cancellation state, stale embed failure/corruption projection, registry-policy drift, dashboard reopen/setup dead ends, raw i18n keys, and OCR NDJSON stdout/scope faults.
- Audit evidence is in the disposable vault at `System/PaperForge/audits/ui-e2e-findings.json` and `operation-timing.json`; source vault data was not mutated.
- Only #81 remains on the release path, but the frozen candidate is currently
  blocked by the M4 findings above. Owner-controlled version sync, candidate
  promotion, PyPI/GitHub release, and plugin manifest publication resume only
  after the repaired candidate passes the dependent gates.

## Current checkpoint

- Retrieval recovery is merged to `master`; the real Literature-hub vault has a healthy 2560-dimensional vec0 index and working M / @ search paths.
- [OCR rebuild: streaming progress + maintenance UI redesign](https://github.com/LLLin000/PaperForge/issues/64) is implemented, reviewed, verified, and closed.
- Multi-key `ocr rebuild` and full `ocr redo` emit separate, flushed progress streams and accept a cross-platform cooperative stop request between papers.
- The maintenance tab now exposes all papers plus the canonical `_needs_derived_rebuild()` recommendation set, selected batch actions, an above-table progress state, and full refresh on completion.
- Per-row maintenance actions now route through `maintenanceActionForRow()` — rebuild/redo follow the canonical backend `display_action` rather than raw booleans.
- Destructive `redo` requires user confirmation via `maintenanceActionRequiresConfirmation()`.
- Cache refresh preserves the backend manifest (was overwriting it with empty on each refresh).
- Source Corpus data remains authoritative and was not modified during verification. Only the deployed plugin bundle and disposable maintenance cache were refreshed.
- [Current-contract audit](https://github.com/LLLin000/PaperForge/issues/66#issuecomment-4968837257) identified the migration boundary: preserve durable OCR/SQLite truth and recovery actions; replace global setup state, duplicate runtime/config resolution, and freshness-free snapshots.
- The approved `control-center-ux-redesign.md` is implemented: five operational modules, three top-level destinations, contextual Module Detail, progressive setup, user-problem-only Maintenance, and Obsidian-native presentation.
- `paperforge/plugin/DESIGN.md` and `paperforge/plugin/CONTEXT.md` now govern the production surface.
- Ticket 04 OCR Workspace & Processing Domain Cutover is complete after corrective closure: its read/action/progress/cancellation paths use `PaperForgeClient`, real worker events are streamed, missing-client fallback is removed, and dynamic descriptors refresh with the read model.
- **[#83–#93](https://github.com/LLLin000/PaperForge/issues/83) implemented**: schema-v2 presentation, shared primitives, five-card Overview, four-stage Setup Journey, Library/OCR/Smart Retrieval/Agent details, Maintenance/Help, and cutover cleanup are merged to `master`.
- **[#69](https://github.com/LLLin000/PaperForge/issues/69) resolved** at `issuecomment-4971161072`: orthogonal availability/activity/attention axes, 6-state capability ordinal, 12 canonical verbs, backend-owned severity and primary actions, maintenance projection.
- **[#70](https://github.com/LLLin000/PaperForge/issues/70) resolved** at `issuecomment-4971239398`: plugin-managed immutable runtime slots, system-Python bootstrap with validated-triplet fallback, single `active-runtime.json` pointer, `ManagedRuntime` class with `current()`/`status()`/`ensure()`, fail-closed command resolution.

- **[#71](https://github.com/LLLin000/PaperForge/issues/71) resolved**: six-module control-center HTML prototype with 5 scenarios, plain-button switcher, primary attention zone, responsive layout (768px breakpoint), and capability-gated actions. Independent Critical/Important PASS review. Design decisions recorded in `docs/prototypes/2026-07-14-six-module-control-center.{html,md}`.
- **[#72](https://github.com/LLLin000/PaperForge/issues/72) resolved**: actionable-only maintenance inbox prototype with single-action rows, inline issue-draft review, local redacted export, and confirmation-first report flow. Independent Critical/Important PASS review. Design decisions recorded in `docs/prototypes/2026-07-14-maintenance-issue-reporting.{html,md}`.
- **[#73](https://github.com/LLLin000/PaperForge/issues/73) resolved**: locked migration, security, platform, accessibility, and release-gate acceptance contract after five-domain audit and independent review.
- **[#74](https://github.com/LLLin000/PaperForge/issues/74) closed as superseded**: completed #75–#80 remain the control-plane baseline; the product model and remaining work moved to #83.
- **[#75](https://github.com/LLLin000/PaperForge/issues/75) implemented and reviewed**: bare/headless/modular setup share `SetupPlan`; schema-v2 `vault_config` wins; v1 path keys are warned read fallback; all configured directories are forwarded; required failures return non-zero.
- **[#76](https://github.com/LLLin000/PaperForge/issues/76) implemented**: schema-v1 Installation/Help probes flow through the six-module Overview; persisted malformed/stale envelopes fail closed; backend set_config/update actions route to setup.
- **Current navigation is cut over**: Overview / Maintenance / Help are the only top-level destinations; Foundation, Library, OCR, Smart Retrieval, and Agent Integration open as contextual Module Details.
- **[#77](https://github.com/LLLin000/PaperForge/issues/77) implemented**: Managed Runtime lifecycle with immutable slots, synchronous fail-closed `current`, probed `status`, install/repair/update/rollback/cancel/retention, managed-first dispatch, Release-N fallback, four-destination navigation shell. Verification: 192 focused + 289 full tests; typecheck/build clean. Merged to `master`.
- **[#78](https://github.com/LLLin000/PaperForge/issues/78) implemented**: real Library/OCR/Memory capability probes with module-detail-navigation, installation-navigation, and capability-state views. Python owns capability facts; TypeScript exact allowlist/fail-closed rendering. Verification: 58 backend + 171 plugin tests; typecheck/build clean; Obsidian smoke verified.
- **[#79](https://github.com/LLLin000/PaperForge/issues/79) implemented**: SecretStorage for capability secrets. Backend-focused gate passes; plugin full suite passes; typecheck/build clean.
- **[#80](https://github.com/LLLin000/PaperForge/issues/80) implemented**: Maintenance probe with backend-derived actionable-only rows, privacy-safe local issue drafts, and accessible destructive confirmation. Backend owns exact actions from `probe maintenance --json`; frontend renders via derived VerbModel with primary null for quality-ok items. Verification: backend focused gate 77/77; plugin full suite 381/382 (pre-existing capability-state test expecting help.stale but receiving help.invalid_response); typecheck/build clean; production bundle 264.4KB; Obsidian 1.12.7 smoke 730/768: entry focus, actionable-only rows, keyboard Enter, accessible destructive confirmation with exact backend effect, focus trap/restoration, owned inert cleanup, redacted editable issue draft, no token input/auto-open, explicit GitHub open only, URL re-redaction, no horizontal overflow.
- **Literature-hub deployment recovered, then safely rolled back**: duplicate plugin discovery and plaintext credentials remain fixed. The active pointer now targets the probe-capable `v1.5.15` slot because the published `1.5.15` installed into `v1.5.15_build2` lacks `paperforge probe`; do not update/repair until a probe-capable package is published and clean-venv verified.

- **Test-vault UI repair deployed:** OCR Workspace now loads the 593-paper formal index through `ResolvedPaths`, opens as a main tab rather than a right sidebar, hides idle activity, localizes the live Chinese Control Center/Smart Retrieval labels, and uses an accent primary action despite Obsidian core button styling.
- **Setup Journey boundary repair deployed:** Foundation exposes the Python executable and installs/verifies only the PaperForge package; Stage 2 alone presents the editable Zotero plus four vault paths and runs modular setup to save and verify them. Reinstall remains in-flow and no longer opens the legacy wizard.
- **Optional setup configuration deployed:** selected Stage 3 OCR, Smart Retrieval, and Agent cards expand their credential/model/base-URL/platform fields. Credentials are saved through Obsidian SecretStorage, not plugin settings.
- **Smart Retrieval live rebuild repaired:** test-vault `构建索引` now rebuilds the 593-paper vec0 index to `memory.ready`. The unified detail has one configuration disclosure for API key, Base URL, and model; terminal failures display their final stderr diagnostic; a ready index has no stale warning panel.
## Verification status

- Focused Python OCR paths: **99 passed, 1 Windows SIGINT test skipped, 1 unrelated empty-result regression deselected**.
- Plugin: **414/414 passed**; TypeScript check and production build passed (**303.7KB**).
- Maintenance regression tests: **19/19 passed** (canonical action routing, confirmation gate, cache manifest preservation).
- Live Obsidian verification: PaperForge 1.5.15 loaded without captured errors; maintenance rendered **734 All** rows and **700 Recommended** rows from the canonical backend flag.
- Live progress-state harness showed the floating progress bar, current key, Stop control, and disabled row actions.
- Prototype #71 (control center): **Critical PASS (5/5), Important PASS (11/11)** — independent reviewer dimensions confirmed.
- Prototype #72 (maintenance inbox): **Critical PASS (4/4), Important PASS (6/6)** — independent reviewer dimensions confirmed.
- Both prototypes browser-verified at 768px viewport with scenario-switching, action-button interactions, expand/collapse diagnostics, and issue-draft flow.
- Issue #77 verification: **192 focused + 289 full tests passed**; typecheck/build clean.
- Issue #78 verification: **58 backend + 171 plugin tests passed**; typecheck/build clean; Obsidian 730px/768px smoke.
- Issue #79 verification: **backend-focused gate, plugin full suite pass**; typecheck/build clean.
- Issue #80 verification: **backend focused gate 77/77; plugin full suite 381/382** (only pre-existing capability-state test expecting help.stale but receiving help.invalid_response); typecheck/build clean; production bundle 264.4KB; real Obsidian 1.12.7 smoke at 730 and 768 confirmed all acceptance criteria.
- Issue #75 verification: **61/61 focused tests passed**; independent review returned **Spec PASS / Quality APPROVED**.
- Issue #76 verification: **21/21 backend probe tests and 169/169 plugin tests passed**; TypeScript check and production build passed; live Obsidian stale-cache/action-label smoke test and independent review passed.
- Live rollback verification: active Runtime is `windows-x64\\v1.5.15\\venv\\Scripts\\python.exe`; Installation and Help are ready, Library/OCR/Memory return real probe envelopes, Maintenance returns three backend-derived items, and Obsidian captured no errors.
- Control Center live acceptance: Obsidian 1.12.7 exercised Overview, all five Module Details, Maintenance, Help, and all four Setup Journey stages in English and Chinese; no untranslated keys or horizontal overflow. Corrected bundle deployed to Literature-hub.
- Live Setup Journey verification: Foundation auto-refreshed to ready; Library Stage 2 rendered five editable fields with no raw i18n keys. An invalid Zotero path failed validation and disabled Continue; restoring the path re-enabled it.
- Live Foundation-run verification: completed with no legacy modal and no Library stage transition; `D:\L\Med\test\paperforge.json` retained SHA-256 `856d89520a766e927dbae7e00880b912cfbf89a3747fa0f109329dc864f5a36c`.
- Live optional-stage verification: all three selected cards rendered in the in-flow setup with two SecretStorage password fields, four total configuration inputs, one Agent platform selector, enabled Continue, vertical page scroll, and no raw i18n keys.
- Production plugin code was modified only for the deployed test-vault UX repairs; prototype-only records above remain historical.
- The repository-wide Python suite remains blocked during collection by two pre-existing removed-symbol imports: `test_pr9a_resume_rebuild.py` imports `_assert_collections_healthy`, and `test_layer4_vector_backend.py` imports `get_vector_backend`.
## Frontier

- [x] Prototype the six-module control center ([#71](https://github.com/LLLin000/PaperForge/issues/71)).
- [x] Design the actionable-only maintenance inbox ([#72](https://github.com/LLLin000/PaperForge/issues/72)).
- [x] Lock migration/acceptance contract (#73), publish PRD #74, and create dependency-linked issues #75–#82.
- [x] Canonicalize setup and configuration migration ([#75](https://github.com/LLLin000/PaperForge/issues/75)).
- [x] Implement Installation/Help capability tracer ([#76](https://github.com/LLLin000/PaperForge/issues/76)).
- [x] Implement Managed Runtime lifecycle + navigation shell ([#77](https://github.com/LLLin000/PaperForge/issues/77)).
- [x] Expose Library, OCR, Memory capability tracers ([#78](https://github.com/LLLin000/PaperForge/issues/78)).
- [x] Implement SecretStorage for capability secrets ([#79](https://github.com/LLLin000/PaperForge/issues/79)).
- [x] Implement Maintenance probe with backend-derived rows, privacy-safe draft, destructive confirmation ([#80](https://github.com/LLLin000/PaperForge/issues/80)).
- [x] Complete and verify Release N+1 implementation code ([#81](https://github.com/LLLin000/PaperForge/issues/81)); keep the issue open for the owner-controlled release gate.
- [ ] Complete Release N+2 deletion ([#82](https://github.com/LLLin000/PaperForge/issues/82)) only after an N+1 package and support window.
- [x] Implement replacement PRD [#83](https://github.com/LLLin000/PaperForge/issues/83) and dependency-ordered issues #84–#93.
- [x] Browser-audit every English and Chinese Control Center page and deploy the corrected bundle to Literature-hub.
- [x] Cut OCR Workspace and processing interactions over to `PaperForgeClient` (Ticket 04), including real worker-backed progress/item-result events, cooperative cancellation, phase-field consumption, fail-closed client ownership, multi-key argv, and descriptor refresh.
- [x] Cut Knowledge & Retrieval interactions over to `PaperForgeClient` (Ticket 05), including frozen #137 vocabulary, worker-backed embed progress streaming, single cancellation token, dashboard search/retrieve normalization, and Smart Retrieval action dispatch.

## Deferred

- Vector rebuild UX and Memory/global maintenance naming are superseded by the approved Smart Retrieval and user-problem-only Maintenance design; implementation remains pending in the new slices.
- OCR ETA and real-time per-row mutation: out of scope for the completed OCR slice.
- Compatibility naming cleanup remains deferred post-release.


## 2026-07-27: #112 — Agent Skill retrieval contract sync

- [x] Rewrite `atoms/retrieval-routing.md` as 5-part canonical protocol (intent determination, planner protocol, safe executor, one-fallback rule, evidence interpretation + session state)
- [x] Update `SKILL.md`: version bump `2026-07-27.1`, remove `rg`/`semantic` from pre-flight, replace `known-paper` intent with `locate`, remove "vector status gates retrieval routing" from runtime-health
- [x] Rewrite `molecules/discover-papers.md`: delete multi-arm search, use plan→primary→fallback, delete top-10 paper-context enrichment
- [x] Rewrite `molecules/find-supporting-evidence.md`: delete `rg`/`grep` ladder, use structure coordinates for evidence, scope-paper safety rules
- [x] Rewrite `molecules/read-known-paper.md`: two-phase (locate → Q&A), session cache, question-type routing, no default fulltext load
- [x] Rewrite `molecules/deep-analyze-paper.md`: Step 0 uses `--structure`, StructureTree as navigation map, no hardcoded section titles
- [x] Sync `docs/ARCHITECTURE.md`, `docs/COMMANDS.md`, `docs/help/en/guide.md`, `docs/help/zh/guide.md`
- [x] Mark issues #106–#110 closed