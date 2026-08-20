# S1–S6 Certification Matrix — Lightweight Disposable Gates

**Executable SHA:** `462398cb77b7ca7671763aa683c11c1c6faa9f77` (lightweight evidence; hosted `32269242351` failed `F821`)
**New EXECUTABLE_FROZEN:** `a42f8bb7fab2c85510dd020e41e35f4b4c65d037` — dead `AGENT_SKILL_DIRS` block removed (415 deletions, `ruff` clean), no re-OCR/rebuild/embed, lightweight evidence remains valid for `a42f8bb7`
**Python:** `3.14.0` (cert venv `pf-cert-s1-venv`), `3.12.10` audit venv also present
**OS:** `win32 10.0.26200` (Windows 11 Home China, x64, Intel Ultra 7 255H)
**PaperForge --version:** `1.5.15`
**Vault type:** `disposable minimal` (fresh empty + existing minimal with 2 papers)
**Obsidian process:** `absent` (no Obsidian launched during gates)
**.obsidian:** `absent` in all cert vaults (`pf-cert-s1-vault`, `pf-cert-s2-minimal`)
**Plugin:** `absent` (no `.obsidian/plugins/paperforge`, no `data.json`)
**Provider:** `opencode-go/muse-spark-1.2-contributor` present in OMP but not used for these gates; OCR/embedding credentials via keyring/env (vector 401 expected without valid key)

> Bind: do not claim “latest master”. Every row below is bound to `462398cb`. Docs-only `781910f3` does not change executable. Run order `S1 → S2 → S4 → S5 → S3 → S6` as instructed. No full production migration was performed (too large); all gates use disposable minimal fixtures (2-paper `formal-library` + copied `Resources/Literature` + `System/PaperForge/ocr` fulltext when needed). This satisfies the “no-client Core + release already-supported clients” S8 definition without silently requiring DSH.

---

## Matrix

| Gate | Environment | Evidence (command + result) | Result | Classification |
|------|-------------|------------------------------|--------|----------------|
| **S1 Clean Install** | `C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-vault` — fresh empty dir, fresh venv `pf-cert-s1-venv` from `D:/L/Med/Research/99_System/LiteraturePipeline/.cert-462398cb`, `paperforge --version` = `1.5.15`, no `.obsidian`, no plugin, no existing config | `paperforge --vault <fresh> setup --modular --skip-checks --json` → `ok:true`, 5 phases all `ok` (config_writer, vault_initializer, zotero_junction skip, runtime_dependencies ok / already present, agent_installer ok). `probe installation --json` → `installation.ready`, `capability_state:ready`, `severity:ok`. `status --json` → `total_papers:0`, `formal_notes:0`, `bases:1`, `path_errors:0`, `health_aggregate` healthy. `doctor --json` → `verdict:FAIL` but only on optional `Zotero 目录不存在`, `exports 目录不存在`, `未找到 JSON 导出文件` + 2 warns (package path mismatch, Zotero outside vault). All `Vault 结构/Config Migration/OCR 配置/Worker 脚本` pass. `setup` repeat → `Created 0 director(ies), 5 already exist`, same `ok:true`. `dir` shows `System/Resources/Bases/.agents/skills/paperforge/SKILL.md` present, `.obsidian` absent. | **PASS** | No RC blocker. Foundation READY independent of Library/OCR/Vector. Fails are optional capabilities, not Foundation. **#191 gap census:** `setup` still deploys `.agents/skills` (AgentInstaller not removed from SetupPlan) and `paperforge.json` still contains `skill_dir/.opencode/command` + `agent_platform` (should be retired to observation-only). Recorded as gap, not blocker. |
| **S2 Existing Vault Without .obsidian** | `C:/Users/Lin/AppData/Local/Temp/pf-cert-s2-minimal` — created via same `setup --modular`, then injected minimal library: `System/PaperForge/indexes/formal-library.json` (2 items `ME6BJZVS`, `3P98ZJJA` from production), copied `Resources/Literature/运动医学/<key> - .../` (fulltext.md + .md + paper-meta.json), copied fulltext to `System/PaperForge/ocr/<key>/fulltext.md` for read path, `memory build` → `papers_indexed:2`. `.obsidian` never created, Obsidian process absent. Full production copy explicitly avoided per user instruction. | `status --json` → `total_papers:2`, `formal_notes:4`, `lifecycle.fulltext_ready:2`, `health healthy:2`. `probe installation --json` → `ready`. `runtime-health --json` → `bootstrap:ok`, `read:degraded (Memory DB not found before build) → after build ok`, `vector:ok (disabled)` — no mention of `.obsidian`. `paper-status ME6BJZVS --json` (before build → `PATH_NOT_FOUND` multi-path, after `memory build` → `ok:true`, `lifecycle:fulltext_ready`, `health healthy`). `search "platelet" --json` (before build → `Memory database not found`, after build → `count:1` `ME6BJZVS`). `read ME6BJZVS --find platelet --json` (before OCR copy → `no_readable_source`, after copy → `matched` 21 hits, `source:fulltext`). `retrieve "platelet plasma" --paper ME6BJZVS --json` → `ok:true`, `count:0`, `fulltext_unavailable:false` (0 chunks because no body_units, but not `.obsidian` error). `ocr status --json` → `complete count 0`. `embed status --json` → `not_built`, `healthy:true`. `action preflight memory.build --json` → `available`. `sync --dry-run --json` → `ok:true`. `reconcile --json` → `per_paper missing` + `next_actions ocr.run` (honest). | **PASS** | No RC blocker. Core commands do **not** require `.obsidian`/`plugin data.json`/`frontend cache`/`Obsidian process`. Failures before `memory build` are explicit `Memory database not found` / `no_readable_source`, not false `ready` or obsidian-related. After `memory build` all lookups succeed. No complete `D:/L/OB/Literature-hub` migration needed. |
| **S4 Maintenance** | Same `pf-cert-s2-minimal` after `memory build` | `action list --json` → 9 actions with `confirmation` and `scope_kinds` correct. `reconcile --json` → `facet_summary missing:6` (honest, no fabricated healthy), `next_actions ocr.run` for 2 papers. `prune --json` → `deleted:[]` (no orphans). `action preflight memory.build/library.prune/embed.build --json` → correct `available/unavailable` with reason codes. `paper-status UNKNOWNKEY --json` → `ok:false`, `code:PATH_NOT_FOUND`, `absence_proof:multi-path lookup exhausted` (honest, no crash). `config validate --json` → `state:valid` (and after injected corrupt → `state:invalid`, `code:config.corrupt`, no silent fallback). `status/doctor/runtime-health/paper-status/ocr status/embed status` all agree on carp. No文学 `search/retrieve` used for maintenance. | **PASS** | No RC blocker. Observation honest, `next_action` correct, no fabricated `healthy`, no `prune` without orphans incorrectly deleting. `config.corrupt` correctly detected. All optional vs required separation preserved. |
| **S5 Destructive Safety** | Same vault, testing `action runner` confirmation boundary | `action run ocr.run --json` (no confirm) → `ok:false`, `code:action.confirmation_required`, `message:confirmation required — rerun with --confirm ocr.run`, `rc:3`. `action run ocr.run --confirm ocr.run --json` → `ok:true` (0 items, no silent --force). `action run embed.build --json` → same `confirmation_required`; with `--confirm` → attempts remote embedding and fails with explicit `401 invalid_api_key` (fail-closed, not silent success). `action run library.prune --json` → `action.unavailable` (no orphans) not confirmation bypass. `action run ocr.run --force --json` → `unrecognized arguments: --force` (no fabricated flag). `prune --json` (no --force) → dry-run `deleted:[]`; `prune --force --json` → same `deleted:[]` (no orphans, safe). No destructive command executed without explicit confirmation. | **PASS** | No RC blocker. Confirmation boundary enforced, no `--force`/`--confirm` fabrication, no auto-delete. Would be **release blocker** if failed — it did not. Qwen3-4B gate not rerun here but CLI contract proves the boundary the agent would hit. |
| **S3 Full Library Journey** | `pf-cert-s2-minimal` as disposable journey (1–3 papers, here 2) | Chain: `setup --modular` → `memory build` (2 indexed) → `read --find` (matched) → `search` (1 hit) → `paper-context` (derived, not exercised after fulltext copy but `paper-status` proves context) → `retrieve --paper` (0 hits but correctly scoped, not crash) → `embed status` → `action run embed.build --confirm` → explicit `401` (remote cost, no silent skip). Process restart simulated by re-invoking `read`/`status`/`probe` after `memory build` and after corrupt-recover cycle — all still `matched`/`ready`. No Obsidian needed for any step. Credentials via `auth set` not transcript; embedding key correctly absent → 401 not hidden. | **PASS (with remote-credential note)** | No RC blocker. Authority → Raw OCR (simulated via copied `System/PaperForge/ocr` fulltext; real provider OCR not exercised in this lightweight gate, but previous RC canary showed real PaddleOCR job) → Derived (memory build) → Retrieval (FTS) → Vector (attempted, correctly 401) → Serving (read) chain intact without Obsidian. Vector failure is expected without valid key, not a materialization bug. Re-OCR/rebuild not required. |
| **S6 Lifecycle / Recovery** | Same vault, disposable lifecycle checks | `config validate` after injected corrupt `"{ invalid json"` → `state:invalid`, `config.corrupt` (fail-closed, no fallback to old owner). Restore via valid `paperforge.json` → `state:valid`, `revision:sha256:10414ab...`. `setup --modular --skip-checks --json` repeat after restore → `ok:true`, `Created 0 director(ies), 5 already exist` (idempotent, no data loss). `probe installation --json` after restore → `ready`. `read --find` after restore → still `matched`. `memory build --json` idempotent (2 indexed). Stale pointer / malformed pointer / offline / OCR interruption / embed cancellation not exhaustively exercised in this lightweight run; `ocr status`/`embed status` show idle, no stale cache. Previous Release-N reinstall and full `update → restart → interrupted → rollback` matrix remains **owner gate** per #81 (not claimed here). No tag/package published, #81 stays open. | **PASS (partial)** | No RC blocker for exercised paths. Corrupt config does not silently fall back, `setup` repeat is safe, `probe` remains authoritative. Untested S6 sub-paths (`stale runtime pointer`, `malformed pointer`, `offline 401/transport`, `OCR interruption/resume`, `Release-N reinstall`, `stale-cache UI injection`) remain **evidence open / owner gate**, not failures. They are not re-classified as blockers from this lightweight run. |

---

## Triage

| Finding | Classification | Rationale |
|---------|----------------|-----------|
| `.agents/skills` still deployed by `setup` | **#191 gap** | Current SetupPlan still contains `AgentInstaller`; Foundation-only separation not yet implemented. S1 shows skill deployed even though spec says Foundation should not. |
| `paperforge.json` still contains `skill_dir`/`command_dir`/`agent_platform` | **#191 gap** | Should be retired to observation (`skill status --json`). Current `paperforge.json` (S1/S2) still writes them. |
| No `setup inspect` / `plan` / `apply` / `verify` protocol | **#191 gap** | Future onboarding `inspect (facts+requirements+questions) → plan → apply → verify` with `observation_fingerprint`/`plan_hash` and `setup.plan_stale` not present. Current `setup --modular` is the existing Foundation flow. |
| No verified-switch `relocate` lifecycle | **#191 gap** | Direct `config set <path>` still allowed; no `relocate plan → preflight → confirmation → move → verify → commit` with old-location-authoritative on failure. |
| No `setup inspect` single-call bundling, no `external_action`/`secure_external` secret contract | **#191 gap** | Current credential handling via `auth set` exists but not via `questions[]` with `input_mode:secure_external`. |
| `doctor` FAIL on `Zotero 目录不存在` / `exports 目录不存在` in fresh vault | **Not a blocker** | Optional Library capability; Foundation `probe installation` is `ready`. Correct per “Foundation READY independent of Library/OCR/Vector”. |
| `search` before `memory build` → `Memory database not found` | **Not a blocker** | Explicit degraded, not false `healthy` or obsidian-related. |
| `read` before OCR fulltext at `System/PaperForge/ocr` → `no_readable_source` | **Not a blocker** | Correct fail-closed; after placing fulltext at canonical location `matched`. No path fallback to unrelated paper. |
| `retrieve --paper` 0 hits but `fulltext_unavailable:false` with 0 `body_units` | **Not a blocker / debt** | FTS body_units not built because OCR json missing; retrieval correctly scoped and not fabricating. Vector not built similarly honest. |
| `action run embed.build --confirm` → `401 invalid_api_key` | **Not a blocker** | Remote credential correctly required; fail-closed with explicit error, not silent success. Re-embed only needed with valid key. |
| `reconcile` reports `missing` for 2 papers despite copied fulltext | **Not a blocker / gap** | Our minimal `meta.json` (`{"status":"done"}`) not full lineage; reconcile correctly sees missing lineage (honest). Real OCR lineage would be `current`. No data loss. |
| Observation/reconcile/retrieve latency (144s → 48s → 20s, scoped 2.49s) | **Post-RC performance debt** | Already tracked; not a correctness blocker. |
| Remaining S6 sub-paths (stale pointer, malformed pointer, offline transport, OCR resume, embed resume, Release-N reinstall, stale-cache UI injection) | **Evidence open / owner gate** | Not exercised in this lightweight disposable run; #81 remains open until owner provides N+1 reinstall/support-window evidence. Not reclassified as blocker. |

---

## Decision Answers

### 1. 当前 executable 还有没有 release blocker？

**No — 在 S1–S6 轻量 disposable 认证范围内未发现违反当前已冻结 invariant 的 RC blocker。**

- 无 Obsidian 时 Core 命令均未因 `.obsidian`/plugin/frontend cache 而失败（S1/S2）。
- 未出现 `runtime/pointer/config` 回退旧 owner 或数据丢失（S6 corrupt→valid 回退正确，setup 重复幂等）。
- Destructive confirmation 未被绕过，未出现自造 `--force` 成功（S5）。
- 当前 `update/restart` 未在轻量范围内暴露失败；`setup`/`probe`/`memory build` 均可重复执行。
- 所有失败均为显式 `config.corrupt` / `Memory database not found` / `confirmation_required` / `401`，无 silent fallback 或 false `healthy`。

> 注意：此结论仅对 `462398cb` + 轻量 2-paper fixture 有效。完整 RC 矩阵（`project/current/2026-08-17-rc-gate-matrix.md`）中仍有 `PARTIAL PASS` / `OWNER GATE` / `EVIDENCE OPEN` 行（如 `#81-02` plugin managed-runtime stale-pointer browser evidence、`#81-10` Release-N reinstall、`REC-02`/`M2-01` 等需 `46c4ddaf` 修复后重建候选），那些不在 S1–S6 轻量范围内重判。

### 2. #81 是否已经有足够证据 owner-close？

**No — 仍需 owner 决策。**

- S1–S6 轻量证据覆盖了 “无 Obsidian 时 Core 不失败” 和 “destructive confirmation” 等当前 invariant，但 **未覆盖** #81 的 `N+1 support window 内 Release-N 通过 reinstall 可恢复`、`offline/stale-cache/failed-migration` 全矩阵、`plugin managed-runtime` 真实浏览器路径等 owner-gated 证据。
- 仓库仍在 `master` (`781910f3` docs-only)，无 tag/package，`#81` 仍 `open + ready-for-human`，符合 “release remains owner-gated” 约束。
- 建议保持 `#81` open，待 S6 完整矩阵（含真实 Release-N artifact 重装、stale pointer 真实文件、offline 传输错误）补充后由 owner 关闭。

### 3. #191 gap census 到底剩哪些真实失败，而不是设计假设？

**Real gaps observed in this run (not assumed):**

- `setup` still deploys Agent skill to `.agents/skills/paperforge` (S1/S2 `dir` 证据) — future `Foundation-only` 未实现。
- `paperforge.json` still persists `skill_dir` / `command_dir` / `agent_platform` (S1 `paperforge.json` 明文) — 应迁移为观察态。
- Missing `setup inspect --json` single-call `facts+requirements+questions[]` (current only `setup --modular` + `probe`/`doctor`/`status`)。
- Missing `setup plan` / `apply` with `observation_fingerprint`+`plan_hash` and `setup.plan_stale` zero-mutation guard。
- Missing `relocate plan → preflight → confirmation → move → verify → commit` verified-switch；当前可直接改 `paperforge.json` 路径（未测试但按代码仍允许）。
- Missing `kind: external_action` / `input_mode: secure_external` + `interaction: {type: secure_cli, argv:[paperforge, auth, set, ocr]}` 秘密契约；当前 `auth set` 存在但未通过 `questions[]` 暴露。
- S8 多客户端中立：当前能证明 `no-client Core` 正常，但 `release中已有的 >=2 clients` 共存（OpenCode + Claude + Obsidian 等）未在轻量 gate 中并发验证；`skill status --json` 观察多份 skill 拷贝的能力已落地（`action list`/`skill deploy --to`），但多客户端同时驱动同一 vault 的 Core 状态一致性未在此轮 live 证明。

**Not gaps (design assumption, not observed as failure):**

- `lineage/reconcile` 慢、`retrieve` 35–159s 等已明确为 post-RC performance debt，不入 census。
- 未实现的 `observation cache` / `Goal/Ensure kernel` / `daemon` 亦为 debt。

---

## Evidence Bundle (repro)

```text
# S1
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --version  # 1.5.15
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-vault setup --modular --skip-checks --json  # ok:true
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-vault probe installation --json  # ready
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-vault status --json  # total_papers:0
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-vault doctor --json  # FAIL only on Zotero/BBT optional

# S2 minimal (2 papers)
# setup same as S1, then:
# - inject System/PaperForge/indexes/formal-library.json (2 items)
# - copy Resources/Literature/运动医学/<key> - .../fulltext.md
# - copy to System/PaperForge/ocr/<key>/fulltext.md
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s2-minimal memory build --json  # papers_indexed:2
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s2-minimal status --json
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s2-minimal paper-status ME6BJZVS --json
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s2-minimal read ME6BJZVS --find platelet --json  # matched
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s2-minimal search "platelet" --json  # count:1
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s2-minimal retrieve "platelet plasma" --paper ME6BJZVS --json

# S4
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s2-minimal action list --json
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s2-minimal reconcile --json
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s2-minimal prune --json
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s2-minimal paper-status UNKNOWNKEY --json  # PATH_NOT_FOUND
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s2-minimal config validate --json

# S5
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s2-minimal action run ocr.run --json  # confirmation_required rc3
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s2-minimal action run ocr.run --confirm ocr.run --json  # ok:true
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s2-minimal action run ocr.run --force --json  # unrecognized arguments: --force

# S3 vector (expected 401)
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s2-minimal action run embed.build --confirm embed.build --json  # 401 invalid_api_key

# S6
# corrupt paperforge.json -> config validate -> state:invalid config.corrupt
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s2-minimal config validate --json
# restore + setup repeat + probe/read
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s2-minimal setup --modular --skip-checks --json
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s2-minimal probe installation --json
C:/Users/Lin/AppData/Local/Temp/pf-cert-s1-venv/Scripts/paperforge.exe --vault C:/Users/Lin/AppData/Local/Temp/pf-cert-s2-minimal read ME6BJZVS --find platelet --json
```

---

## Recommendation

- `EXECUTABLE_FROZEN a42f8bb7fab2c85510dd020e41e35f4b4c65d037` is the dead-code hygiene fix on top of `462398cb` (no re-OCR/rebuild/embed); `PROTOCOL_DOCS 781910f3` adds only 2 docs commits. **Do not build `462398cb+46c4ddaf+b66fde53` candidate.**
- `462398cb` local full suite `3312 passed / 0 failed`; hosted CI run `32353318123` on docs-only descendant `a2e18fa4` is **All Checks Passed / 14/14 green**, including `Python 3.11` Ubuntu/macOS/Windows, J-Matrix, Ruff, plugin, OCR, E2E. No executable change occurred after `a42f8bb7`; treat this as candidate-tree CI evidence, not a claim that the run head SHA equals `a42f8bb7`.
- Keep `#81` **OPEN / owner gate** pending **RC Owner Closure**: 1) Managed Runtime / Plugin browser (stale/non-ready/restart/fail-closed/cache), 2) M2/M3 live process (mixed outcomes/cancellation/Ctrl+C/scoped embed), 3) S6 full recovery (malformed/stale pointer/offline/interrupted update/OCR resume/embed resume), 4) Release-N reinstall + support-window owner decision.
- Keep `#191` **FROZEN / ready-for-agent / implementation not started** — gap census is complete (Foundation/client split, retired fields, `inspect/plan/apply/verify` + `plan_stale` + verified-switch `relocate` + `external_action`/`secure_external`, S8). Research `Source Routing` (local-library-first / web fallback) and `Visual Evidence` (OCR/object = discovery, canonical PDF render = visual authority) deferred post-RC, not `462398cb` blockers.
- Language: **S1–S6 lightweight certification complete; S6 partial / owner gates remain** (not `S1–S6 PASS`). Next S1–S6 full run should reuse disposable minimal pattern unless explicitly approved.
