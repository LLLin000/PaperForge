# PaperForge 后端系统性审计框架与问题台账（PBAF v2.1）

> 借鉴 **SQLite TH3**（故障注入/崩溃一致性）、**Anki (`rslib`)**（Rust 内核 + 事务与云盘隔离边界）、**Calibre**（目录+catalog 写序列化）、**Syncthing**（跨 OS 文件系统敌对语义）以及 **Google SRE Production Readiness Review (PRR)**。
>
> 目标：把“靠临场撞 Bug”升级为**可重复、可量化、可阻断发版**的 **12 支柱（P1–P12）** 静态 + 动态 + 混沌恢复演练体系。

---

## 1. 为什么单点测试总会漏掉真实故障（6 大盲区复盘）

1. **小样本玩具库盲区**：单元测试常用 3–10 篇文献、`20 KB` SQLite 库，热缓存一切 <50 ms；真实用户库（1,300+ 篇、`1 GB+` `paperforge.db`、数千个 `fulltext.md` / `result.json`）在冷盘 I/O 上会产生 **10–100 倍退化**（如 `PRAGMA quick_check(1)` 扫描 1 GB 需 1.6s–5s，`rglob("*.md")` 误扫 `assets/` 与正文耗时 54.5s）。
2. **缺少多平台故障注入**：`.github/workflows/ci-chaos.yml` 仅周跑 `ubuntu-latest`，导致 Windows `PermissionError`/长路径/保留字、macOS APFS `NFD`、POSIX 建议锁失效等问题长期潜伏。
3. **`L0` 静态门禁缺架构反模式检查**：现有 `ruff` 仅卡 `F821/F822/F823` 未定义变量，未扫描热路径全表检查、循环内 N+1 SQL、未分块线程池、硬编码 `mklink`、静默丢弃 `quiesce_sqlite_wal` 返回值等模式。
4. **缺少全谱系老兵库矩阵**：真实老兵库并非标准空库，而是混合了 v1.2/v1.4/v1.5 历史遗产、中断过半的迁移、双引擎目录冲突、僵尸 `running` 状态、网盘同步冲突副本与跨 OS 同步路径。
5. **缺少定量预算门禁**：没有为只读 CLI / 插件高频接口设定延迟上限、SQL 查询次数上限与重型 SDK 禁止导入红线（如 `embed status` 仅读本地 DB 却加载 `openai` SDK 白耗 1.1s）。
6. **缺少持久化缺陷台账**：发现与修复零散留在对话记录中，没有形成“新增必登记、回归必防复发”的台账与门禁联动。

---

## 2. PaperForge 后端 12 大审计支柱（PBAF v2.1）

| 支柱 | 名称 | 核心原则与不变量 | 对应自动化检查 |
|---|---|---|---|
| **P1** | **数据主权与原子写盘** | 严格区分**五桶所有权**（机器纯派生 / 用户增强 / 确认残留 / 用户主权绝对不碰 / 冲突冻结）；核心状态写盘必须走同目录 `mkstemp` + `fsync` + `os.replace`（POSIX 保权限、Win 杀软重试）+ CAS，严禁静默覆盖用户笔记与手写注释。 | `S8`, `check_no_destructive_delete` |
| **P2** | **SQLite / WAL / FTS5 / 向量底座完整性** | 维护 `schema_version` / `user_version` 向前不兼容拒绝；搬迁/快照前强制 `PRAGMA wal_checkpoint(TRUNCATE)` + `journal_mode=DELETE` 且**失败必须阻断**；修改 `body_units` 禁止先删表再触发 FTS5 外部内容删行导致 rowid 错位；只读热路径大库（>50 MB）严禁全库 `quick_check`。 | `S1`, `S4`, `D4` |
| **P3** | **升级状态机、幂等性与时光机回滚** | 升级严格按 `G0_preflight -> G1_snapshot -> G2_cutover -> G3_reconcile/heal -> G4_verify` FSM 推进；迁移前跑 `audit_file_action_conflicts() == []`；支持中断续传、跨版本跳级（v1.2/v1.4/v1.5 → v2）、G2/G4 任意 Tier-0 萎缩自动完整回滚（含 JSONL 合并前备份）。 | `S6`, `PER_FILE_ACTION_CONTRACT` |
| **P4** | **多平台与敌对文件系统** | Windows / macOS / Linux 全覆盖：POSIX 下用 SQLite `BEGIN IMMEDIATE` 真锁而非 `open("r+b")`；macOS APFS `NFD -> NFC` 文件名归一化；Linux 大小写敏感探测；Windows 保留字（`CON`/`NUL`/`COM1`）、`MAX_PATH` 260 字符防护、跨卷 `EXDEV` 与动态 `2× + 128 MB` 磁盘空间预检；跨 OS 同步库 `pdf_path` 兜底；平台专属命令按 OS 分流。 | `S2`, `S3`, `S4` |
| **P5** | **规模、耗时与资源预算** | 见下表：限定冷路径 SQL 次数、禁止无用重型依赖导入、`ThreadPoolExecutor` 必须分块防止 GIL/锁反噬、插件 `timeoutMs >= 3 × P99`。 | `S1`, `S2`, `S5`, `S7`, `S9`, `D1`, `D2`, `D3` |
| **P6** | **并发、锁与进程生命周期** | 单写者 `WriterLock` 互斥；Rust Daemon 热切换不泄露错误、插件卸载必收割子进程；僵尸 `running` 自愈需校验心跳与进程存活；外网探活离线超时可控不阻塞 UI。 | Daemon/Client E2E, `test_execute_child_reaping` |
| **P7** | **安全、凭据与路径隔离** | 凭据统一走系统凭据库（`.env` 仅迁移兼容且日志绝对脱敏）；所有搬迁/回滚路径强制通过 `_validate_vault_contained_path` 防止路径穿越与误删 Vault 外目录；子进程全程 `shell=False`；对 Zotero 原库严格只读打开（`?mode=ro`）。 | `check_machine_paths`, `protocol_conformance` |
| **P8** | **混沌与故障注入** | 覆盖迁移写盘 `SIGKILL` 断电恢复、满盘 `ENOSPC`、单篇 `EACCES`/`PermissionError` Skip-and-Isolate、活跃写者并发锁冲突 `SQLITE_BUSY`、断网探活、云盘冲突副本与在线占位符。 | `tests/chaos/`（需扩至 Win/macOS） |
| **P9** | **多语言契约与二进制漂移（Polyglot Skew）** | Rust Daemon ↔ Python CLI ↔ TypeScript Plugin ↔ MCP 四端围绕 SQLite 表/列、`vault-manifest.json`、NDJSON 词汇表保持严格契约一致；支持插件热升级/Daemon 热切换与版本门禁。 | `S12`（动态解析 Rust SQL）, `protocol_conformance` |
| **P10** | **外部 AI/API 熔断与 Zotero 实时竞争** | 外部 API（OCR / Embedding）必须具备显式请求超时、限速 429 重试上限、返回向量 NaN/维度漂移门禁与断网快速降级；读取 Zotero 活库（含 `-wal`）强制只读/快照隔离，严禁阻塞正在运行的 Zotero 客户端。 | `S13`, `test_embed_extreme_resilience`, `test_p10_live_zotero_wal_contention_snapshot_ro` |
| **P11** | **无界增长、句柄泄漏与 5 载体一致性** | `.paperforge/backups/` 与 `trash/` 需受保留策略与体积门禁约束防无限膨胀；每次 `sqlite3.connect` 必有确定关闭防止句柄耗尽与 WAL 长尾；5 大真相载体（Markdown / `formal-library.json` / `papers` / `workspace_registry` / FTS5+vec）数量与身份互洽。 | `S11`, `S14`, `D5`, `D6`, `test_p11_bounded_backup_and_trash_retention_fail_closed` |
| **P12** | **自动恢复演练与静默吞错零容忍** | 未经自动还原验证的备份等于没有备份：每次大迁移后定期运行 `upgrade -> verify -> rollback -> diff` 演练；关键状态路径禁止 `except Exception: pass` 静默吞掉核心错误。 | `S10`, `test_p12_upgrade_mid_cutover_failure_triggers_full_rollback_and_diff` |

### P5 性能与资源预算硬指标（以 1,500 篇 / 1 GB DB Vault 为基准）

| 操作 | P95 耗时预算 | SQL 查询数上限 | Import / 并发硬约束 |
|---|---:|---:|---|
| `config validate --json` | < 0.5 s | 0 | 不得加载 DB/SDK |
| `embed status --json` | < 1.0 s | <= 12 | 严禁导入 `openai` / `pymupdf` |
| `status --json` | < 1.5 s | <= 10 | 仅 1 次 `lit_root` 遍历 + 分块读头；严禁导入 `openai` / `pymupdf` |
| `probe all --json`（离线/缓存） | < 3.0 s | <= 50 | `probe_lineage` 内批量预加载，零 N+1 查询 |
| `doctor --json` | < 4.5 s | <= 15 | 复用单次笔记扫描，指针依赖探测合入单进程 |
| `upgrade --plan --json`（1,500 篇冷盘） | < 8.0 s | <= 20 | 跳过全库 B-Tree `quick_check`；插件超时 >= `120_000 ms` |
| `upgrade --apply`（插件 Fast Cutover） | < 5.0 s | <= 30 | O(1) 目录割接，重型整理延后后台 |

---

## 3. 完整问题与风险台账（Issue & Risk Ledger）

> 状态约定：`FIXED`（已修复并有验证记录） / `OPEN`（已审计定位，待排期修复）。

### A. 已修复问题清单（`PF-AUD-001` .. `PF-AUD-014`）

| ID | 支柱 | 级别 | 状态 | 位置与根因摘要 | 修复与验证记录 |
|---|---|---|---|---|---|
| `PF-AUD-001` | P2 | P0 | **FIXED** | `paperforge/memory/builder.py`, `db.py`：`_upsert_body_units` 先删后插引发外部内容 FTS5 `rowid` 漂移与删行损坏；存在 4 处裸 `DELETE FROM body_units_fts`；热日志未恢复。 | 统一改用 `safe_delete_body_units_fts`、纠正删除顺序、增量构建前自愈 `check_and_heal_fts`、`open_live_reader` 前置热日志清理；`pytest` 全过。 |
| `PF-AUD-002` | P1/P2 | P0 | **FIXED** | `paperforge/memory/builder.py`：`memory build` 在大规模缺失本地 OCR 文件时会直接覆盖清空旧全文/摘要索引。 | 增加大规模失效熔断器（`>= 20` 篇且缺失比例 `>= 50%` 拒删保旧）并已在仿真库 `D4_memory_build`（5.53s rc=0）验证。 |
| `PF-AUD-003` | P1/P2 | P0 | **FIXED** | `paperforge/memory/schema.py`：pre-v3 破坏性 schema 迁移会丢失用户侧 Tier-0 表（`reading_log`/`project_log`/`paper_annotations`/`paper_memory_cards`）。 | 迁移前快照并在重建后恢复 4 张用户主权表；`pytest` 验证通过。 |
| `PF-AUD-004` | P5 | P0 | **FIXED** | `identity_resolver.py`, `materialization/ocr.py`, `paperforge-client.ts`：冷盘 `upgrade --plan` 全量逐个读取 markdown + 全量 JSON + sha256 导致 >60s 超时。 | 增加只读前部 frontmatter 解析、并发预热、`validate_result_json(fast=True)` 与 `assess_ocr_bundle_atoms(fast=True)`，插件 `vaultUpgradePlan` 超时提至 120s；`upgrade --plan` 实测降至 3.6–7.2s。 |
| `PF-AUD-005` | P4 | P1 | **FIXED** | `paperforge/core/fs_safe.py`：缺少对 Windows 设备保留字（`CON`/`NUL`/`COM1`）、失效 symlink/junction 与弹性 I/O 并发度的统一保护。 | 落地 `fs_safe.py` 与 `adaptive_io_workers()` 并在核心扫描路径全面接入。 |
| `PF-AUD-006` | P5/P6 | P2 | **FIXED** | `doctor/field_validator.py`, `worker/status.py`：多行 YAML 缩进误报 `Unknown field` 且数千篇逐条刷屏（报告膨胀数百 KB）。 | 跳过多行续行、限读前 16 KB、同类问题合并采样输出（`15+1`）；`doctor` 输出从数百 KB 降至 3.9 KB，0 条误报。 |
| `PF-AUD-007` | P1/P3 | P0 | **FIXED** | `migration_contract.py`, `storage_migration.py`, `vault_upgrade.py`：缺少显式状态机、文件动作契约审计、搬迁前 WAL 静默、双库 Rich-Wins、JSONL 并集及 G4 7 表零萎缩门禁。 | 建立 G0–G4 FSM、`PER_FILE_ACTION_CONTRACT`（15 条规则 0 冲突）、Rich-Wins、ID 并集与 G4 10 项终检自动回滚；仿真库 `D2` 10/10 全部保留（18,191 body / 7,542 objects / 17 reading_log）。 |
| `PF-AUD-008` | P6 | P1 | **FIXED** | `services/upgrade_reconcile.py`：历史崩溃遗留的僵尸 `ocr_status = 'running'` 永不自愈。 | 增至 `CURRENT_RECONCILE_EPOCH = 2`，在无 30 分钟内活跃 OCR 作业时按磁盘 `result.json`+`fulltext.md` 自愈为 `done`/`interrupted`；仿真库 4 个僵尸全部自愈。 |
| `PF-AUD-009` | P1/P5 | P1 | **FIXED** | `plugin/src/services/zotero-import-scope.ts`, `settings.ts`：任何用户点开插件直接全量导入易拖垮大库或造成目录混乱。 | 所有含 Zotero 文件夹的文库默认强制要求勾选文件夹（或显式勾选“导入整个文库”）；Vitest `768 passed`。 |
| `PF-AUD-010` | P5 | P0 | **FIXED** | `worker/status.py`：`check_wikilink_format` 对含 1,904 个旧 `fulltext.md` 与 `assets/` 做 `rglob("*.md")` 并通篇 `read_text`（54.5s）；`run_status` 连跑 3 次 `rglob`。 | 统一 `_scan_literature_notes` + `_read_note_head`（8 KB）；`A3_doctor_pre` 从 **54.5s → 2.7s**（20 倍），`status` 从 **3.4s → 1.2s**。 |
| `PF-AUD-011` | P5 | P1 | **FIXED** | `commands/embed.py`, `embedding/substrate.py`：`embed status` 含死代码 `import openai`（1.1s）且每次对 1 GB 库跑全表 `PRAGMA quick_check(1)`（1.3–5s）。 | 移除死导入 + `substrate.py` 对 `>50 MB` 库在只读观测下走 O(1) 结构探针；`embed status` 从 **6.9s → 0.46s**（15 倍）。 |
| `PF-AUD-012` | P5 | P1 | **FIXED** | `lineage.py`：`_probe_lineage` 循环内执行 5,478 次逐篇 N+1 SQL 查询且重复校验 `body_units`/`object_units` 哈希。 | `_load_lineage_bulk_caches` 批量预加载 + `integrity_cache` 复用；`probe all` 从 **8.2s → 4.8s**。 |
| `PF-AUD-013` | P5 | P2 | **FIXED** | `ocr_diagnostics.py`：`ocr_doctor` 对已返回 HTTP 400 的端点重复发第 2 次必得 400 的 HTTPS POST 且超时 30s。 | 超时收紧为 10s，HTTP 400 且非 `--live` 直接返回跳过 L3 结论。 |
| `PF-AUD-014` | P5 | P1 | **FIXED** | `vault_upgrade.py`：`execute_vault_upgrade` 全量模式在 `progressive_heal` 前后连跑 2 次 `ensure_vault_reconciled` 与 2 次 `verify_vault_upgrade`。 | 合并为单次最终对账与 G4 终检并并发校验 OCR；`DERIVED_VIEW_AND_INDEX_RECONCILE` 从 **9.38s → 0.64s**。 |

---

### B. 闭环与长期演进问题清单（`PF-AUD-015` .. `PF-AUD-029`）

| ID | 支柱 | 级别 | 状态 | 位置（相对路径） | 根因与风险描述 | 修复 / 演进验证记录 |
|---|---|---|---|---|---|---|
| `PF-AUD-015` | **P4** | **P0** | **FIXED** | `paperforge/services/vault_upgrade.py` (`_check_sqlite_movable`) | **POSIX 建议锁盲区**：原仅用 `open(db_path, "r+b")` 在 macOS/Linux 上恒为真。 | 在 Windows `r+b` 之外全平台增加 `sqlite3` `BEGIN IMMEDIATE -> ROLLBACK`（0.25s 超时）真写锁探针；`S4` 转绿。 |
| `PF-AUD-016` | **P2/P3** | **P0** | **FIXED** | `paperforge/services/storage_migration.py`, `vault_upgrade.py` | **WAL 静默失败未阻断搬迁**：原调用 `quiesce_sqlite_wal(...)` 丢弃返回值。 | 新增 `_ensure_wal_quiesced` 及 G1 门禁检查：非空 `-wal` 且 checkpoint 失败时强制中止或触发事务回滚；`S4` 转绿。 |
| `PF-AUD-017` | **P3/P4** | **P1** | **FIXED** | `paperforge/services/vault_upgrade.py` (`execute_vault_upgrade`) | **磁盘余量门禁固定 32/64 MB 过低**：无法兜底 1 GB+ 大库及跨分区 `EXDEV`。 | 改为按 `max(32MB, db_size//2 + 32MB)` 与跨 `st_dev` 全目录体积动态预检。 |
| `PF-AUD-018` | **P4** | **P1** | **FIXED** | `paperforge/pdf_resolver.py` (`resolve_pdf_path`) | **跨 OS 同步库绝对路径失效**：Win↔macOS 绝对路径错把盘符当相对路径，且缺本地 Zotero 目录兜底。 | 识别异构 OS 绝对路径直接跳过 vault 拼接并提取 `storage/<KEY>`，未传 `zotero_dir` 时缓存兜底本机默认 Zotero 目录。 |
| `PF-AUD-019` | **P5** | **P1** | **FIXED** | `core/fs_safe.py`, `identity_resolver.py`, `vault_upgrade.py`, `worker/status.py` | **线程池未分块 GIL 开销反噬**：2,330–4,660 次微 Future 调度占耗时 63%–79%。 | 抽象 `fs_safe.chunked_io_map(chunk_size=64)` 并替换全部 7 处 `pool.map`；`S7` 全部收敛。 |
| `PF-AUD-020` | **P5** | **P1** | **FIXED** | `paperforge/lineage.py`, `materialization/ocr.py` | **`probe_lineage` 重复残留扫描与 4 倍 `read_meta`**：连跑两次 `_detect_residuals` 且 `meta=None` 时重复读盘。 | 合并 `_orphans_from_residuals`；新增 `META_MISSING` 哨兵消除重复 `read_meta`（并修复 `_ocr_execution_detail` 兼容）。 |
| `PF-AUD-021` | **P5/P4** | **P1** | **FIXED** | `paperforge/services/storage_migration.py`, `worker/asset_index.py` | **全量迁移对冗余旧 `fulltext.md` 重复写盘备份**：冷盘读写 63s 且触碰 260 字符 `MAX_PATH`。 | 复用单次读入字节 + 短路优先核验主 `fulltext.md`，字节一致的冗余镜像在备份清单一律引用 `.paperforge/ocr/<key>/fulltext.md`（或 `.paperforge/trash/`），免写 1,904 份冗余副本。 |
| `PF-AUD-022` | **P4** | **P2** | **FIXED** | `paperforge/worker/status.py` (`_zotero_link_remediation`) | **Windows `mklink /J` 修复建议硬编码**。 | 按 `os.name == "nt"` 分支输出 `mklink /J` 与 `ln -s`；`S3` 转绿。 |
| `PF-AUD-023` | **P4** | **P2** | **FIXED** | `paperforge/services/vault_upgrade.py`, `storage_migration.py` | **macOS APFS NFD / Linux 大小写边界**：资源名 `![[...jpg]]` 匹配未做 NFC 归一化，Linux 小写 `system/paperforge` 未被探测。 | `storage_migration.py` 已统一 `unicodedata.normalize("NFC", ...)`；新增 `_find_legacy_engine_dirs` 支持大小写不敏感老兵引擎目录探测与迁移回落。 |
| `PF-AUD-024` | **P5** | **P2** | **FIXED** | `paperforge/services/upgrade_reconcile.py`, `worker/status.py` | **`reconcile` 逐行 SQL 与 `doctor` 7 次子进程**。 | `upgrade_reconcile.py` 已改为 `executemany` 批写及循环外缓存；`worker/status.py` 新增 `_query_resolved_environment` 将有指针时的 7 次子进程合并为单次批探。 |
| `PF-AUD-025` | **P6/P5** | **P2** | **FIXED** | `paperforge/services/upgrade_reconcile.py`, `ocr_diagnostics.py`, `probes/ocr.py` | **僵尸 `running` 缺 PID 存活检查 & `probe all` 重复离线探测与全量飘移哈希**。 | `_has_active_ocr_job` 增加 `_is_pid_alive()`；`ocr_doctor` 新增 120s 原子指纹缓存，`collect_maintenance_rows(..., include_drift=False)` 跳过 `probe_ocr` 无关 `fulltext.md` 哈希。 |
| `PF-AUD-026` | **P3/P8** | **P2** | **FIXED** | `vault_upgrade.py`, `.github/workflows/ci-chaos.yml` | **回滚 JSONL 合并覆盖 & 混沌 CI 仅限 Linux**。 | `rollback_vault_upgrade` 支持从 `jsonl_merge/dst__*` 还原旧日志；`ci-chaos.yml` 已扩充 `[ubuntu-latest, windows-latest, macos-latest]` 三端矩阵并接入 `backend_audit.py --strict`。 |
| `PF-AUD-027` | **P4/P5** | **P1** | **FIXED** | `commands/dashboard.py`, `finalize.py`, `services/sync_service.py`, `worker/{_utils,ocr,repair,sync}.py` | **`S2` 检出 15 处裸 `.rglob("*.md")`**。 | 全部 15 处均已替换为 `safe_rglob(..., suffix=".md", skip_dirs=LITERATURE_SKIP_DIRS)` 并合并 `dashboard.py` 3 次遍历为 1 次头扫；`S2` 转绿。 |
| `PF-AUD-028` | **P1** | **P2** | **FIXED** | `paperforge/config.py:623`, `services/storage_migration.py` | **`S8` 检出 2 处回滚路径非原子 `.write_bytes()`**。 | 全部替换为 `write_bytes_atomic()`；`S8` 转绿。 |
| `PF-AUD-029` | **P5** | **P1** | **FIXED** | `paperforge/lineage.py` (`write_vector_lineage`, `write_legacy_fulltext_lineage`) | **`S9` 检出向量血缘写入侧 N+1 SQL**。 | 改为一次性预读 `meta`/`lineage` 后统一 `conn.executemany` 落库；`S9` 转绿。 |
| `PF-AUD-030` | **P12** | **P2** | **FIXED** | `memory/{builder,db,schema}.py`, `services/{upgrade_reconcile,vault_upgrade}.py` | **`S10` 检出 11 处关键状态路径 `except: pass` 静默吞异常**。 | 全部改为显式 `logger.debug(...)` 可观测记录，`S10` 与全部 14 项静态门禁 `--strict` 转绿。 |
| `PF-AUD-031` | **P9/P10/P11** | **P1** | **FIXED** | `paperforge/services/vault_engine.py`, `scripts/backend_audit.py` | **备份目录无界保留、Rust SQL 契约静态清单滞后及外部请求/Zotero 锁缺失门禁**。 | 新增 `prune_old_backups` 有界保留策略；`S12` 升级为 Rust SQL 表名动态提取，`scripts/backend_audit.py` 扩充 `S13`/`S14` 与 `D6`。 |
| `PF-AUD-032` | **P6/P10/P12** | **P1** | **FIXED** | `tests/chaos/test_backend_chaos_and_recovery.py` | **缺少升级断电自回滚、WAL 并发读写、Zotero 活库 WAL 竞争、跨 OS/保留自动化混沌验证**。 | 新增 6 项 PBAF v2.1 混沌与恢复演练测试，实测验证端到端自回滚零数据丢失与并发锁安全。 |

### C. 自动化审计基线与 PBAF v2.1 收口实测（`scripts/backend_audit.py`）

- **PBAF v1.0 首轮基线**（273 文件 / 1,358 篇隔离仿真库）：检出 `S3`/`S4`/`S2`/`S7`/`S8`/`S9`/`S10`，`D1=24 SQL (3.25s)`，`D3` `doctor=5289.8ms` 与 `probe_all=4866.4ms` 超预算（均已记入并修复）。
- **PBAF v2.1 最新实测（严格模式 `--strict` + 1,358 篇隔离仿真库）**：
  - 静态 **14 项门禁（`S1–S14`）全部 PASS（0 FAIL, 0 WARN）**，`check_machine_paths.py` 脱敏 CLEAN，Chaos/回归套件 `257 passed, 1 skipped, 1 deselected`。
  - `D1_lineage_sql_budget`：**PASS**（1,358 篇仅 **18 次 SQL**，`2.23 s`，预算 `<= 50`）
  - `D2_import_hygiene_runtime`：**PASS**（`status=[]`, `embed_status=[]`，0 重型 SDK 加载）
  - `D3_latency_budgets`：`config_validate=424.8ms`、`embed_status=591.1ms`、`status=1865.3ms`、`doctor=4299.0ms`（`<4500ms` 达标）、`upgrade_plan=2797.9ms`（`<8000ms`）；`probe_all=3524.3ms–3657.7ms`（较首轮 `4866.4ms` 下降，接近 `3500ms` 冷启临界值，记作观测余量 `WARN`）
  - `D4_vault_integrity_readonly`：**PASS**（`manifest=True`, `papers=1358`, `zombies=0`）
  - `D5_cross_carrier_coherence`：**PASS**（`index_items=1358`, `papers=1358`, `workspace_registry=1358`, `body_units=18441`, `body_units_fts=18441`）
  - `D6_unbounded_growth_and_wal_tail`：**PASS**（`backups=6.96MB(2)`, `trash=95.79MB(57)`, `wal=0.0MB`, `jm=delete`, `v=7`）

---

## 4. 12 类老兵库仿真矩阵 & 发版签核门禁

任何大版本迁移器、状态机、索引器上线前，需在隔离克隆环境上通过下列 12 类测试画像中的代表场景：

1. **巨型混合老兵库（千篇 + 1 GB+ DB + 上千旧 `fulltext.md`）** — 已由隔离 `Literature-hub` 实证验证
2. **中断半迁移恢复库**（残留 `.migration-journal.json` `in_progress` + 双引擎目录各有新数据）
3. **损坏 SQLite + 完整明文 Markdown/OCR 兜底重建库**
4. **FTS5 rowid 错位损坏库 + `-wal` 热日志残留库**
5. **macOS APFS NFD 中文/重音文件名库**
6. **跨设备同步库**（含 Windows `D:/...` 与 macOS `/Users/...` 混用绝对 `pdf_path` + 网盘冲突副本 `*conflicted copy*`）
7. **Windows 敌对文件系统库**（目录内混入 `CON.md` / `NUL` / 超长路径 / 坏 junction / 只读属性）
8. **外部进程并发持锁库**（Daemon 或 Zotero 正在写入时触发升级，必须触发 G0 `db.file_locked` 阻断而非损毁）
9. **零 OCR / 纯 Zotero 元数据轻量新手库**（<=50 篇 + 含多个 Zotero 文件夹）
10. **用户深度二创库**（自带大量用户手写 Obsidian `.base`、`deep-reading.md`、`aliases` 与额外附件）
11. **低磁盘余量 / 跨分区（`EXDEV`）库**
12. **纯离线无外网环境**（验证 `probe all` / `doctor` / `upgrade` 不长时间挂起）

### 自动化审计脚本运行方式

```bash
# 1. 全仓库静态反模式与契约审计（< 1s，零修改）
python scripts/backend_audit.py

# 2. 机器学习路径隐私门禁
python scripts/check_machine_paths.py

# 3. 静态 + 针对指定隔离测试库的只读动态行为/性能审计（严禁传入生产库！）
PAPERFORGE_HOME=<SCRATCH_PF_HOME> python scripts/backend_audit.py --vault <ISOLATED_CLONE_VAULT>
```
