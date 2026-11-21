# 第 15 章：Vault 升级普查、四重防误触归属门禁与双速无感迁移架构

> 本文档完整梳理 PaperForge 面向存量老用户与跨版本演进构建的 **统一真相源升级与归属保护体系（ADR-018）**：涵盖三层老用户溯源检测（`detect_vault_provenance`）、五桶全库只读普查（Five-Bucket Census）、四重防误触克隆门禁（`is_verified_legacy_flat_note` 与原生 `.base` / `./assets` 保护）、Tier-0 OCR 原子级真相抢救（`assess_ocr_bundle_atoms`）、`< 3s` 双速原子切流与后台渐进自愈（`fast_cutover` + `heal_vault_progressive`）、一键时光机无损回滚（`rollback_vault_upgrade`）、轻内存全局控制守护进程（`ControlDaemon`）协同机制，以及遵循冰山披露与四级物理动效的非阻塞 Obsidian 升级界面（`PaperForgeUpgradeModal`）。关联章节参见 [第 01 章：系统架构、分层约束与磁盘存储契约](01-architecture-and-storage.md)、[第 03 章：CLI 路由、PFResult 协议与流式取消机制](03-protocol-pfresult-and-stream.md)、[第 10 章：SQLite Memory DB v7、Embedding 与混合检索](10-memory-db-and-retrieval.md) 与 [第 13 章：Obsidian Thin-Client 插件、IPC 传输与五大视图交互](13-obsidian-plugin-and-views.md)。

---

## 1. 职责与非目标边界

- **结构化身份解析与防误触边界（`paperforge/services/identity_resolver.py`）**：彻底淘汰脆弱的目录前缀匹配（`<KEY> - <Title>`）、固定层级假设（`len(rel.parts) == 2`）与标题拼写推断；一律以 `paper-meta.json` 中的 `zotero_key` 与 Markdown Frontmatter 结构化字段为唯一身份锚点，并通过四重门禁严格区分“系统历史扁平镜像”与“用户手动复制的读书草稿 / 个人笔记 / 原生附件目录”。
- **三层老用户溯源与五桶全库普查（`paperforge/services/vault_upgrade.py`）**：在执行任何磁盘写操作之前，先进行零副作用全库扫描，准确识别陌生/新建 Obsidian 库（`fresh_or_foreign`）、当前标准库（`standard_current`）、标准旧版库（`veteran_legacy`）与配置丢失抢救库（`veteran_rescue`），将全部文件精确归入五大所有权桶。
- **原子级 OCR 真相源抢救（`paperforge/materialization/ocr.py`）**：将付费高价值 Tier-0 原始云端响应（`json/result.json`）与零成本本地可重算的 Tier-1 派生产物（`canonical/blocks.raw.jsonl`、`render/`、`fulltext.md`）解耦校验；只要 `result.json` 通过结构与字节非空校验，即使派生产物缺失或损坏也一律离线免费回填，绝不阻塞整库迁移或重复消耗云端 OCR 额度。
- **双速无感升级与一键时光机回滚（`execute_vault_upgrade` / `heal_vault_progressive` / `rollback_vault_upgrade`）**：
  - **前台快速切流（`< 3s` Fast Cutover）**：备份关键控制文件后执行 `O(1)` 引擎目录归拢（`System/PaperForge` → `.paperforge/`）、配置 Schema v2 升级、PaperForge 专属 `.base` 视图刷新与 `vault-manifest.json` 落盘，3 秒内交还全部阅读与检索能力。
  - **后台渐进自愈（Progressive Healing）**：由 `ControlDaemon` 监管短生命周期子进程在后台逐篇清理过期元数据路径、重命名历史主笔记并自动注入 Obsidian `aliases` 保护 `[[双链]]`、同步图表资产与离线回填 OCR；单篇异常遵循 **Skip & Isolate（跳过并隔离）**，绝不拖垮整批任务。
  - **一键时光机回滚**：基于 `.paperforge/backups/upgrade-<ts>/` 快照与 `moved-pairs.json` 账本，随时支持无损还原至升级前的目录布局与视图内容。
- **轻内存全局控制引擎（`paperforge/services/control_daemon.py`）**：常驻内存严格控制在 `< 30 MB`（零重型库导入、有界 LRU 缓存、空闲自动 `gc.collect()` 与冷缓存驱逐），通过子进程监管重负载任务（完成后 100% 归还系统物理内存）、维护升级排他屏障与双工消息推送。

### 非目标边界（Non-Goals）

- **绝不在非 PaperForge 库或纯新建库上弹出迁移打扰**：当 `detect_vault_provenance()` 判定为 `fresh_or_foreign` 时，迁移横幅静默隐藏，不触碰任何用户 Markdown、原生 `.base` 或 `./assets` 文件夹。
- **绝不执行物理裸删（Zero Bare Unlink / Rmtree）**：任何工作区旧笔记收敛、冲突归档或残余开发垃圾清理（如 `.venv-corrupt`）一律经 `quarantine_move()` / `trash_remove()` 移入带清单的 `.paperforge/trash/` 或 `.paperforge/backups/`，且残余候选仅在用户在设置面板显式勾选后才执行隔离。
- **绝不用全屏阻断弹窗锁死阅读器**：即使老用户暂缓点击升级，文献阅读、双链跳转、PDF 批注与全文搜索依然保持可用；后台自动同步在旧版布局未切流前自动静默挂起，防止污染待迁移目录。

---

## 2. 核心源码与单测映射表

### 2.1 核心源码模块

| 模块路径 | 核心职责 | 关键符号 |
| --- | --- | --- |
| `paperforge/services/identity_resolver.py` | 结构化工作区身份扫描、软链接/同步冲突跳越与四重克隆保护 | `WorkspaceIdentity`、`FlatNoteIdentity`、`VaultIdentityScan`、`scan_vault_identities()`、`is_verified_legacy_flat_note()`、`is_reparse_or_symlink()`、`is_sync_conflict_artifact()`、`read_text_tolerant()` |
| `paperforge/services/vault_engine.py` | 统一引擎 SQLite SSOT 注册表、`vault-manifest.json` 与安全隔离原语 | `VAULT_LAYOUT_VERSION`、`read_vault_manifest()`、`write_vault_manifest()`、`quarantine_move()`、`sync_workspace_registry()`、`sync_ocr_catalog()`、`rebuild_db_from_truth()` |
| `paperforge/services/vault_upgrade.py` | 三层老用户检测、五桶普查、双速升级、渐进自愈与一键回滚 | `detect_vault_provenance()`、`inspect_vault_upgrade()`、`execute_vault_upgrade()`、`heal_vault_progressive()`、`rollback_vault_upgrade()`、`_is_paperforge_owned_base_file()` |
| `paperforge/services/storage_migration.py` | 引擎目录合并迁移、同名冲突备份、用户全文保留与事务日志恢复 | `migrate_vault_storage()`、`rollback_incomplete_migration()`、`rewrite_visual_embeds_for_key()`、`_move_tree_entries()` |
| `paperforge/materialization/ocr.py` | Tier-0 `result.json` 原子校验与 Tier-1 派生完整性分级 | `validate_result_json()`、`assess_ocr_bundle_atoms()`、`verify_bundle_integrity()` |
| `paperforge/core/io.py` | 跨平台 `mkstemp` + `fsync` + 重试替换、CAS 防并发覆盖与容错 JSONL | `write_bytes_atomic()`、`write_text_atomic()`、`write_text_cas()`、`CASConflictError`、`read_jsonl()` |
| `paperforge/services/control_daemon.py` | 轻内存全局控制守护进程（Python 后备实现）、排他屏障、子进程监管与双工通知中心 | `ControlDaemon`、`SupervisedJob`、`get_process_rss_bytes()`、`is_pid_alive()`、`kill_process_tree()` |
| `crates/paperforge-daemon/src/main.rs` | 跨平台原生 Rust 极速控制与检索侧车（免本地 Rust/Python 开箱即用，`< 6 MB` RSS） | `NativeControlDaemon`、`try_handle_config_cli()`、`handle_base_snapshot()`、`try_handle_search_cli()`、`handle_zero_python_upgrade_plan()` |
| `paperforge/plugin/src/services/native-daemon.ts` | 6 平台预编译侧车定位、SHA-256 校验自动拉取与可执行权限维护 | `nativeDaemonTargetTriple()`、`resolveNativeDaemonBinary()`、`ensureNativeDaemonDownloaded()` |
| `paperforge/commands/upgrade.py` | `paperforge upgrade` CLI 编排入口 | `run()`（支持 `--plan`、`--apply`、`--fast-cutover`、`--heal`、`--priority-key`、`--rollback`、`--quarantine-ids`） |
| `paperforge/commands/engine.py` | `paperforge engine` SQLite 注册表诊断与重建入口 | `run()`（`status` / `sync-registry` / `rebuild-db`） |
| `paperforge/plugin/src/views/upgrade-modal.ts` | 冰山式非阻塞升级横幅、一键无感升级弹窗与存储维护抽屉 | `PaperForgeUpgradeModal`、`renderUpgradeAvailableBanner()`、`renderStorageMigrationMaintenanceSection()` |

### 2.2 配套单元测试与门禁

| 测试文件路径 | 验证目标与断言重点 |
| --- | --- |
| `tests/unit/test_vault_engine_and_upgrade.py` | 验证重命名目录身份识别、四重门禁保护用户克隆草稿、陌生库零误触、原生 `.base` 保护、`< 3s` 快速切流、双链 `aliases` 注入、一键回滚与 `CASConflictError` |
| `tests/unit/test_storage_migration_safety.py` | 验证故障注入回滚、Zotero 目录原位保留、用户编辑过的工作区 `fulltext.md` 无损备份恢复及 `.migration-journal.json` 幂等自愈 |
| `tests/unit/test_control_daemon.py` | 验证常驻守护进程零重型模块导入、RSS/父进程存活探针、空闲冷缓存驱逐、升级排他屏障、短生命周期子进程监管与双工 `notice.push` / `task.updated` 推送 |
| `paperforge/plugin/tests/client/daemon-transport.test.ts` | 验证 `NodeProcessTransport` 暖守护进程复用、双工服务端推送事件与交错 RPC 并发隔离 |
| `paperforge/plugin/tests/upgrade-ux.test.ts` | 验证非阻塞升级横幅、冰山渐进披露抽屉、快速切流与后台自愈交接、维护清理勾选与一键回滚交互 |

---

## 3. 磁盘文件、数据库表与协议 JSON 字段字典

### 3.1 `.paperforge/vault-manifest.json` 引擎清单契约

| 字段名 | 类型 | 说明 |
| --- | --- | --- |
| `schema_version` | `int` | 清单协议版本（当前为 `1`） |
| `layout_version` | `int` | 标准磁盘布局代数（当前 `VAULT_LAYOUT_VERSION = 2`） |
| `engine_version` | `str` | 最近一次升级或校验该库的 `paperforge.__version__` |
| `upgraded_at` | `str` | ISO-8601 UTC 升级完成时间戳 |
| `last_backup_dir` | `str` | 最近一次升级前快照目录（供 `upgrade --rollback` 读取） |
| `CutoverMode` / `notes` | `dict` | 记录切流模式（`fast_cutover` 或 `full`）及待渐进自愈状态摘要 |

### 3.2 SQLite 统一引擎状态表（`paperforge/memory/schema.py`，Schema v7）

除检索表外，`paperforge.db` 内置四张引擎控制面表（损坏时均可由磁盘真相源 `paperforge engine rebuild-db` 100% 重建）：

1. **`workspace_registry`**：主键 `zotero_key`，存储 `workspace_relpath`、`main_note_relpath`、`domain`、`title`、`has_paper_meta`、`note_mtime_ns`、`meta_mtime_ns`、`identity_source`、`updated_at` —— 提供 `O(1)` 文献工作区定位，彻底取代运行时全目录正则扫描。
2. **`ocr_catalog`**：主键 `zotero_key`，存储 `ocr_relpath`、`tier0_result_ok`、`tier0_sha256`、`has_blocks_raw`、`has_fulltext_md`、`derived_version`、`salvage_action`、`updated_at` —— 记录每篇论文的原子级 OCR 真相状态。
3. **`vault_kv`**：主键 `key`，存储 `value_json` 与 `updated_at` —— 替代易碎的零散状态小 JSON 文件。
4. **`engine_jobs`**：主键 `job_id`，记录后台任务类型、状态、进度与时间戳审计轨迹。

### 3.3 `paperforge upgrade --plan --json` 核心返回结构

| 顶层字段 | 类型 | 说明 |
| --- | --- | --- |
| `provenance` | `dict` | `{state, needs_upgrade, confidence, signals, legacy_engine_dir}`；`state` 取值 `fresh_or_foreign` / `standard_current` / `veteran_legacy` / `veteran_rescue` |
| `census` | `dict` | 五桶全库普查统计：`user_sovereign`（个人主权资产）、`pf_canonical`（标准工作区）、`pf_legacy_migratable`（可无损升级旧产物）、`ambiguous_clones`（受保护疑似副本）、`residuals_and_conflicts`（开发残留与同步冲突） |
| `category_a_auto` | `list[dict]` | 可自动无损执行的升级项（含 `fast_cutover: bool` 标记区分 `< 3s` 前台切流项与后台渐进自愈项） |
| `category_b_reconfig` | `list[dict]` | 环境/凭据/按需补跑项（按 `impact: "experience_critical" \| "minor"` 分级） |
| `category_c_tamper` | `list[dict]` | 文件占用锁、配置语法损坏或键值冲突告警（含明确 `remediation` 指引） |
| `cleanup_candidates` | `list[dict]` | 延后至设置页由用户自主勾选移入回收站的历史残余项（`id`、`path`、`bytes`、`reason`） |
| `rollback_available` | `bool` | 是否存在可用的升级前快照供一键还原 |

---

## 4. 核心执行链路、状态机与顺序不变量

### 4.1 三层老用户触发检测状态机（`detect_vault_provenance`）

1. **`fresh_or_foreign`（陌生库或全新空库）**：既无 `paperforge.json`，无 `System/PaperForge` / `99_System/PaperForge` 旧目录，无 `.obsidian/plugins/paperforge/data.json` 历史键，文献目录下亦无含 PaperForge 工作流签名（`zotero_key` + `ocr_status`/`deep_reading_status`）的笔记 → **绝对静默，零迁移提示**。
2. **`standard_current`（最新标准库）**：已具备 `.paperforge/vault-manifest.json`（`layout_version >= 2`），无遗留外置引擎目录、无旧版 Schema v1 配置、无旧式 `type: table` PaperForge Base 视图 → **正常运行态**。
3. **`veteran_legacy`（明确存量老用户）**：命中 `System/PaperForge`、`99_System/PaperForge`、Schema v1 `paperforge.json`、含退役 9 视图的 `.base` 文件或旧式扁平镜像笔记 → **激活非阻塞升级横幅**。
4. **`veteran_rescue`（配置缺失抢救态）**：`paperforge.json` 被误删或未提交，但磁盘上存在明确的 `ocr/<KEY>/json/result.json` 或多篇带完整 PaperForge 签名的工作区 → **自动进入抢救式无损建库归拢**。

### 4.2 双速无感切流与后台渐进自愈时序

```mermaid
sequenceDiagram
    participant UI as "Obsidian (Banner / UpgradeModal)"
    participant CD as "ControlDaemon (<30MB Resident)"
    participant UP as "vault_upgrade (Fast Cutover)"
    participant WK as "Ephemeral Heal Worker"

    UI->>CD: "upgrade --plan --json"
    CD-->>UI: "provenance='veteran_legacy' + 5-Bucket Census"
    Note over UI: "Non-blocking banner shown; reading & PDF stay unlocked"
    UI->>CD: "upgrade --apply --fast-cutover --json"
    CD->>CD: "acquire_exclusive_barrier(vault)"
    CD->>UP: "1. Snapshot paperforge.json & PF .base to .paperforge/backups/"
    UP->>UP: "2. O(1) move System/PaperForge -> .paperforge/ + write moved-pairs.json"
    UP->>UP: "3. Upgrade PF-owned .base views + stamp vault-manifest.json (v2)"
    CD->>CD: "release_exclusive_barrier(vault)"
    CD-->>UI: "Applied in < 3s (UI unlocked immediately)"
    UI->>CD: "rpc(job.submit, kind='upgrade.heal', backfill_ocr=true)"
    CD->>WK: "Spawn isolated child worker: upgrade --heal --backfill-ocr"
    WK-->>CD: "Progress & Skip-and-Isolate settlement"
    CD-->>UI: "Duplex push: task.updated -> Global Activity Strip + notice.push"
    Note over WK: "Worker exits -> OS reclaims 100% of worker RAM"
```

### 4.3 顺序不变量（Ordering Invariants）

1. **先快照、后切流**：修改 `paperforge.json` 或刷新 `.base` 前，必须先将原始文件完整拷贝至 `.paperforge/backups/upgrade-<ts>/` 并持久化 `moved-pairs.json`，确保任何时刻触发 `rollback_vault_upgrade()` 均可对称逆转。
2. **先注入双链别名、再对外暴露新笔记**：当渐进自愈将 `<KEY> - <Title>.md` 规范化重命名为 `<KEY>.md` 时，必须在同一原子步骤向 YAML Frontmatter 的 `aliases` 列表追加旧文件名词干（`<KEY> - <Title>`），保证用户在每日笔记或课题综述中手写的 `[[KEY - Title]]` 双链 100% 不断链。
3. **Tier-0 备份先于离线回填**：对缺失派生产物的论文执行 `backfill_from_result()` 前，先生成 `json/result.json.pre-backfill.bak` 只读保护副本（若尚不存在），确保即使极端异常也绝不污染云端原始解析结果。

---

## 5. 配置项、环境变量、CLI 入口与错误码

### 5.1 CLI 命令与参数字典

- **全库只读普查（零写入）**：
  `paperforge --vault <VAULT> upgrade --plan --json`
- **前台 `< 3s` 快速原子切流**：
  `paperforge --vault <VAULT> upgrade --apply --fast-cutover --json`
- **完整同步升级（适合命令行一次性执行）**：
  `paperforge --vault <VAULT> upgrade --apply --backfill-ocr --json`
- **后台渐进自愈与单篇插队（JIT Priority）**：
  `paperforge --vault <VAULT> upgrade --heal [--priority-key <KEY>] [--limit <N>] [--backfill-ocr] --json`
- **选择性隔离残余垃圾至回收站**：
  `paperforge --vault <VAULT> upgrade --apply --quarantine-ids cleanup.venv_corrupt --json`
- **一键时光机回滚**：
  `paperforge --vault <VAULT> upgrade --rollback --json`
- **统一引擎 SQLite 注册表运维**：
  `paperforge --vault <VAULT> engine status --json`
  `paperforge --vault <VAULT> engine sync-registry --json`
  `paperforge --vault <VAULT> engine rebuild-db --json`

### 5.2 守护进程环境变量与控制面协议

- `PAPERFORGE_PARENT_PID`：由宿主（Obsidian `NodeProcessTransport`）注入父进程 PID；`ControlDaemon` 每 `1.5s` 探活，宿主崩溃时自动终止在途子进程并退出，杜绝僵尸进程。
- `PAPERFORGE_DAEMON_PUSH`：设为 `"1"` 时开启 stdout 双工异步事件帧推送（`task.updated`、`notice.push`、`state.changed`），与带 `id` 的普通 RPC 响应帧无锁冲突共存。
- 控制面内置 RPC 操作码：`daemon.health`、`daemon.trim`、`engine.status`、`engine.resolve_key`、`engine.invalidate`、`job.submit`（含原生 `runtime.*` 与 Python 派发队列）、`job.list`、`job.cancel`、`notice.list`、`notice.ack`、`notice.push`。
- 原生零脚本部署（ADR-019）：`paperforge-daemon` 内置纯 Rust `install-runtime` 子命令与 `runtime.*` 控制面作业，直接在后台完成 `uv` SHA-256 校验、解压、`Python 3.12` 与 `paperforge[vector]` 安装并推送 `installer.log` / `task.updated` 进度，彻底消除跨平台临时 `.ps1`/`.cmd`/`.sh` 脚本依赖。

---

## 6. 边界防护与 Fail-Closed 防呆规则

### 6.1 四重防误触归属门禁（杜绝误伤“长得像”的用户文件）

1. **门禁一：克隆笔记与读书草稿保护（`is_verified_legacy_flat_note`）**
   用户常在 Obsidian 中右键“创建副本”制作精读草稿，导致新文件同样携带 `zotero_key`。`clean_flat_notes()` 仅在同时满足以下 **4 项条件** 时才将其移入回收站，缺一不可：
   - 位于旧版固定域根目录 `<Literature>/<Domain>/<File>.md`（嵌套子文件夹中的副本一律豁免）；
   - 文件名严格符合生成器命名（`<KEY>.md` 或 `<KEY> - <Title>.md`）；
   - Frontmatter 具备 PaperForge 工作流签名字段（`ocr_status` / `deep_reading_status` / `do_ocr`），排除普通 Better BibTeX 引用笔记；
   - **正文差异集为空（`unique_to_flat == 0`）**：逐行比对去除空白与模板占位符后的正文，只要扁平笔记中存在哪怕一行工作区主笔记没有的个人批注或草稿文字，立即归类为 `ambiguous_clone` 原地保留！
2. **门禁二：原生 Obsidian `.base` 数据库保护（`_is_paperforge_owned_base_file`）**
   绝不把所有含 `- type: table` 的 `.base` 文件盲目改成 `paperforge-table`。仅当文件包含显式 `# paperforge-base-schema` 头部、`paperforge-table`、退役 PaperForge 视图名（如 `控制面板`、`待深度阅读`）、`!zotero_key.isEmpty()` 过滤器，或文件名精确匹配已知文献域且指向文献目录时，才认定为 PaperForge 视图；用户自建的实验记录表、课题进度表 100% 原样保留。
3. **门禁三：通用 `./assets` 与 `System/Attachments` 目录保护**
   大量 Obsidian 用户将默认附件目录设为 `./assets` 或 `System/Attachments`。`_is_workspace_candidate()` 明确禁止单独依据 `assets/` 子目录判定文献工作区；`migrate_vault_storage()` 仅迁移 `System/PaperForge` 专属子目录，绝不触碰同级的 `System/Attachments`、`System/Templates` 或 `System/Zotero`。
4. **门禁四：10 类极端文件系统异常防护**
   - **NTFS 目录联接点 / 符号链接（Junctions & Symlinks）**：`is_reparse_or_symlink()` 结合 `FILE_ATTRIBUTE_REPARSE_POINT (0x0400)` 与 `os.walk(..., followlinks=False)`，严禁跨盘递归或误移外部挂载盘。
   - **网盘同步冲突副本**：`is_sync_conflict_artifact()` 自动识别 OneDrive / iCloud / 坚果云 / Syncthing 冲突文件并冻结保留在原处。
   - **非 UTF-8 历史编码**：`read_text_tolerant()` 按 `utf-8-sig` → `utf-8` → `gb18030` → `utf-16` 只读探测，绝不用损坏替换符回写用户文件。
   - **SQLite 锁占用与磁盘余量预检**：切流前预检 `paperforge.db` 排他写锁与至少 `32 MB` 磁盘可用空间，不满足时平滑阻断并给出单步指引。
   - **并发编辑防覆盖（CAS）**：`note.py` 与工作区改写使用 `write_text_cas(expected_sha256=...)`，若升级或后台任务期间用户在编辑器修改了笔记，立即抛出 `CASConflictError` 放弃覆盖，用户手写内容永远优先。

5. **门禁五：新库目录同名防冲突隔离与用户自定义 `aliases` 无损合并**：
   - **根目录非空文件夹自动让位（`_detectAndIsolateFolderCollision`）**：首次引导打开尚未写入 `paperforge.json` 的个人 Obsidian 库时，若根目录下已存在非空的 `Literature/`、`Resources/` 或 `Bases/`，自动将 PaperForge 根目录隔离为 `PaperForge/Literature`、`PaperForge/Resources`、`PaperForge/Bases` 并展示防冲突横幅，从源头杜绝挤占用户原有知识库目录。
   - **手写 YAML `aliases` 同步保留（`frontmatter_note`）**：Zotero 元数据刷新重构笔记 Frontmatter 时，自动合并保留用户自行追加的所有历史 `aliases` 与 `custom_fm` 自定义字段，仅维护工作流锚点与衍生区，不破坏用户在笔记内部建立的个人别名与双链体系。

---

## 7. 维修、调试与升级 Checklist

1. **对生产库执行零风险升级预演**：
   始终先运行只读普查 `python -m paperforge --vault <VAULT> upgrade --plan --json`，核对 `provenance.state`、`census` 五桶统计、`category_a_auto` 与 `category_c_tamper` 是否符合预期。
2. **排查单篇跳过隔离（Skip & Isolate）记录**：
   若后台自愈报告 `skipped_isolated` 非空，可针对该文献键单独运行 `python -m paperforge --vault <VAULT> upgrade --heal --priority-key <KEY> --json` 查看具体原因（如 YAML 手工改坏或文件被外部 PDF 阅读器锁死）。
3. **验证守护进程轻内存与健康指标**：
   通过守护进程发送 `{"id": 1, "op": "daemon.health"}` 或检查 `.paperforge/indexes/.daemon-state.json`，确认 `heavy_modules_loaded == []` 且空闲 `rss_mb < 30`。
4. **数据库缓存损坏时的秒级重建**：
   若 `paperforge.db` 被网盘截断或报 `malformed`，直接运行 `python -m paperforge --vault <VAULT> engine rebuild-db --json` 从磁盘笔记、`paper-meta.json` 与 `ocr/` 目录无损重建注册表。
5. **需要回退至旧版目录结构时**：
   在设置页「存储与迁移维护」点击「还原至升级前目录结构」，或执行 `python -m paperforge --vault <VAULT> upgrade --rollback --json`。
6. **提交修改前的回归门禁**：
   凡修改 `identity_resolver.py`、`vault_upgrade.py`、`storage_migration.py` 或 `control_daemon.py`，必须同时通过：
   - `python scripts/check_module_graph.py --check`
   - `python scripts/build_technical_reference.py --check`
   - `python -m pytest tests/unit/test_vault_engine_and_upgrade.py tests/unit/test_storage_migration_safety.py tests/unit/test_control_daemon.py tests/test_technical_docs_sync.py -q`
   - `cd paperforge/plugin && npm test`
