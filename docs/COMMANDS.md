# PaperForge 命令参考

> 所有 Python CLI（`paperforge`）、原生 Rust 守护进程（`paperforge-daemon`）与 MCP 工具速查。Agent 技能中的检索路由协议权威定义见 `paperforge/skills/paperforge/atoms/retrieval-routing.md`。

---

## 命令矩阵（Agent / CLI / Rust Daemon）

| 场景 / 意图 | 推荐入口 | 说明 |
| :--- | :--- | :--- |
| Agent 会话冷启动 | `paperforge-daemon agent-brief --vault <DIR>` | 零 Python 极速返回库统计、配置、可用工具与阻塞提示 |
| Agent MCP 接入与自检 | `paperforge-daemon mcp-install` / `mcp-check --probe-mcp` | 自动写入主流 Agent MCP 配置并验证连通与 Skill 链接 |
| 一键同步所有已注册 Skill | `paperforge-daemon skill-sync-all` | 从 `~/.paperforge/skills/paperforge` 同步至各 Agent 工作区 |
| 检索意图规划 | `paperforge query-plan "<query>" --intent locate\|discover\|content --json` | 按意图路由至 `paper-context` / `search` / `retrieve` |
| 单篇论文完整上下文 | `paperforge paper-context <KEY> [--structure] --json` | 含元数据、章节树、`user_annotations` 与 `living_memory` |
| 元数据全文搜索（FTS5） | `paperforge search "<query>" --json` | 跨标题、摘要、作者、期刊检索（不要求 OCR） |
| 正文混合语义检索 | `paperforge retrieve "<query>" [--deep] [--paper <KEY>] --json` | BM25 + `sqlite-vec`（`vec0`）全并集 RRF（无向量时回退 BM25） |
| Zotero 同步与索引重建 | `paperforge sync [--dry-run] [--prune] --json` | 直连 `zotero.sqlite`（或 BBT 导出）生成笔记与 Base |
| 单篇 6 阶段只读诊断 | `paperforge inspect <KEY\|DOI\|title> --json` | SQLite `?mode=ro` 只读排查全链路瓶颈 |
| 运维体检与修复 | `paperforge doctor --json` / `paperforge repair --fix --json` | 检查并修复路径、索引与状态不一致 |
| OCR 解析与离线重建 | `paperforge ocr` / `paperforge ocr rebuild` | 云端版面解析与零成本本地 Stage V3 重建 |
| 无损 PDF 批注与记忆卡片 | `paperforge annotations ...` / `paperforge memory-card ...` | 侧车 `annotations.jsonl` 与 5 维 Living Memory Card |
| 旧版 Vault 平滑升级 | `paperforge upgrade --plan\|--apply --fast-cutover\|--heal --json` | O(1) `<3s` 收拢至 `.paperforge/` 架构 |

---

## 原生 Rust 守护进程与 MCP 服务（`paperforge-daemon`）

`paperforge-daemon` 位于 `~/.paperforge/bin/`，负责 Obsidian 零卡顿快路径、Zotero SQLite 直连快照、MCP 服务器与零 Python 运行时引导。

### 运行模式与基础参数

```bash
paperforge-daemon --version                                  # 输出守护进程版本号
paperforge-daemon --stdio [--idle-timeout 300] [--parent-pid PID]  # Obsidian JSON-RPC + NDJSON 双工模式
paperforge-daemon --mcp [--vault <VAULT_DIR>]                # 启动 MCP stdio 服务器（锁定指定 Vault）
paperforge-daemon install-runtime [--action install|update|repair] [--expected-version <VER>]
```

### MCP Server 工具清单（`paperforge-daemon --mcp`）

`--mcp` 模式向 Claude Code、Cursor、Codex、OpenCode 等客户端暴露 7 个原生工具：

| MCP 工具名 | 用途 | 关键参数 |
| :--- | :--- | :--- |
| `paperforge_brief` | 获取当前 Vault 全景概览与可用性检查 | `paper?` |
| `paperforge_search` | 元数据 FTS5 搜索 | `query`, `domain?`, `ocr?`, `year_from?`, `year_to?`, `limit?` |
| `paperforge_library_query` | 按条件列举或筛选文献库条目 | `domain?`, `ocr?`, `has_pdf?`, `limit?` |
| `paperforge_paper_context` | 读取单篇论文完整上下文、批注与记忆卡片 | `key`, `structure?` |
| `paperforge_retrieve` | 正文混合语义/BM25 检索 | `query`, `paper?`, `deep?`, `limit?` |
| `paperforge_annotate_batch` | 批量写入/更新 Agent PDF 批注层 | `key`, `items`, `lens?`, `replace_lens?` |
| `paperforge_memory_refine` | 更新论文 Living Memory Card 指定认知维度 | `key`, `facet`, `content` |

### Agent 引导、MCP 配置与 Skill Hub 命令

```bash
paperforge-daemon agent-brief [--vault <DIR>] [--paper <KEY>] [--json]
paperforge-daemon agent-onboarding [--vault <DIR>] [--lang zh|en] [--binary <PATH>]
paperforge-daemon mcp-config [--vault <DIR>] [--platform <PLATFORM>] [--binary <PATH>]
paperforge-daemon mcp-install [--vault <DIR>] [--platform <PLATFORM>] [--binary <PATH>]
paperforge-daemon mcp-check [--vault <DIR>] [--platform <PLATFORM>] [--skill-dir <DIR>] [--mcp-config <PATH>] [--probe-mcp] [--register]
paperforge-daemon skill-sync-all
```

---

## 检索命令体系（Python CLI）

检索系统分三个意图，一个规划器，三个执行命令：

```text
query-plan (规划器) — 决定使用哪条路径
├── intent=locate    → paper-context（定位论文）
├── intent=discover  → search（发现论文）
└── intent=content   → retrieve（正文检索）
```

### `paperforge query-plan`

```bash
paperforge query-plan "<query>" --intent locate|discover|content --json
```

返回 JSON：
- `data.intent` — 回显检索意图
- `data.query` — 规范化后的检索 query
- `data.scope` — `paper`（单篇）| `library`（全库）
- `data.paper_key` — scope=paper 时的 identifier
- `data.primary` — 推荐命令 + 参数（`command` / `args`）
- `data.fallback` — 触发声明条件时的备选（或 `null`）；trigger 包括 `zero_results`、`no_direct_answer`

### `paperforge paper-context`

```bash
paperforge paper-context <KEY|DOI|citation_key> --json
paperforge paper-context <KEY> --structure --json   # 附加 StructureTree
```

`--structure` 返回章节导航地图（`node_id`、`parent_id`、`path`、`depth`、`page_span`），用于确定 evidence 所在章节。

### `paperforge search`

元数据 FTS5 全文搜索。跨论文标题、摘要、作者、期刊：

```bash
paperforge search "<query>" --json
paperforge search "<query>" --domain <domain> --json
paperforge search "<query>" --year-from <Y> --year-to <Y> --json
paperforge search "<query>" --ocr done|pending|failed|processing --json
paperforge search "<query>" --deep --lifecycle <STAGE> --next-step <STEP> --limit <N> --json
paperforge search "<query>" --evidence --json      # 返回 data.metadata_candidates[]
```

### `paperforge retrieve`

```bash
paperforge retrieve "<query>" --json
paperforge retrieve "<query>" --limit <N> --json
paperforge retrieve "<query>" --paper <KEY> --json
paperforge retrieve "<query>" --deep --json                # 全并集混合检索（BM25 + sqlite-vec；无向量时回退 BM25）
paperforge retrieve "<query>" --paper <KEY> --deep --json  # 单篇混合检索
paperforge retrieve "<query>" --expand --json              # 扩展邻接上下文单元（默认开启，可用 --no-expand 关闭）
```

---

## Python CLI 全量命令参考（50 个顶层子命令）

> 全局参数：`paperforge [--vault <VAULT_DIR>] <subcommand> ...`

### 1. 运行时、安装与配置

#### `paperforge runtime`（机器级运行时管理，无需 Vault）

```bash
python -m paperforge runtime status --expected-version <VERSION> [--min-engine-version <MIN_ENGINE>] [--base-python <PY>] --json
python -m paperforge runtime install --expected-version <VERSION> [--min-engine-version <MIN_ENGINE>] [--base-python <PY>] [--wheel <WHL>] --json
python -m paperforge runtime update --expected-version <VERSION> [--min-engine-version <MIN_ENGINE>] [--base-python <PY>] [--wheel <WHL>] --json
python -m paperforge runtime repair --expected-version <VERSION> [--min-engine-version <MIN_ENGINE>] [--base-python <PY>] [--wheel <WHL>] --json
```

`install` 保留已就绪环境；`update` 仅在候选环境自检通过后原子发布 `~/.paperforge/runtime/pointer.json`；`repair` 强制重建候选环境。

#### `paperforge setup`

```bash
paperforge setup                                  # 交互式初始化
paperforge setup --modular [--headless] --json    # 模块化/非交互初始化（Express & AI Agent 使用）
paperforge setup --agent opencode --zotero-data <DIR> --skip-checks --stream
```

支持路径覆盖参数：`--system-dir`、`--resources-dir`、`--literature-dir`、`--base-dir`、`--zotero-data`。**严禁在命令行参数中传递任何 API Key**，请使用 `paperforge auth set`。

#### `paperforge auth`

安全凭据权威（OS Keyring 存储，禁止命令行明文传参）：

```bash
paperforge auth status [--profile default] --json
paperforge auth set ocr|embed [--profile default] [--stdin] [--replace] --json
paperforge auth migrate [--from <ENV_PATH>] [--kind ocr|embed] [--profile default] [--dry-run] [--replace] --json
paperforge auth delete ocr|embed [--profile default] --yes --json
```

#### `paperforge config`

```bash
paperforge config init [--json]
paperforge config list [--json]
paperforge config get <KEY> [--json]
paperforge config set <KEY> <VALUE> [--json]
paperforge config unset <KEY> [--json]
paperforge config validate [--json]
paperforge config paths [--json]
paperforge config migrate [--dry-run] [--json]
```

#### `paperforge paths` & `paperforge probe`

```bash
paperforge paths [--json]
paperforge probe all|installation|library|ocr|memory|maintenance|help [--last-operation-exit-code N] [--expected-version VER] [--min-engine-version VER] --json
```

#### `paperforge daemon`

```bash
paperforge daemon [--stdio] [--idle-timeout 300] [--parent-pid <PID>]
```

#### `paperforge engine`

```bash
paperforge engine status [--json]
paperforge engine rebuild-db [--json]             # 重建 SQLite/registry 一致性状态
paperforge engine sync-registry [--json]
```

#### `paperforge zotero`

```bash
paperforge zotero detect [--path <ZOTERO_DATA_DIR>] --json
```

### 2. 同步、工作区与迁移

#### `paperforge sync`

```bash
paperforge sync [--dry-run] [--domain <DOMAIN>] [--json]
paperforge sync [--selection] [--index] [--rebuild-index] [--prune] [--prune-force] [--json]
```

兼容别名（保留向后兼容，日常推荐使用 `paperforge sync`）：

```bash
paperforge selection-sync
paperforge index-refresh
```

#### `paperforge upgrade`

```bash
paperforge upgrade --plan [--json]                                   # 检测旧版 Vault 并生成升级计划
paperforge upgrade --apply --fast-cutover [--dry-run] [--json]       # O(1) <3s 切入 .paperforge/ 架构
paperforge upgrade --heal [--priority-key <KEY>] [--limit N] [--backfill-ocr] [--quarantine-residuals] [--quarantine-ids ...] [--no-rebuild-db] [--json]
paperforge upgrade --rollback [--json]                               # 回滚最近一次升级快照
```

#### `paperforge migrate-storage`

```bash
paperforge migrate-storage [--dry-run] [--json]
```

#### `paperforge base-refresh`

```bash
paperforge base-refresh [--force|-f]
```

#### `paperforge prune` & `paperforge trash`

```bash
paperforge prune [KEY...] [--force] [--json]
paperforge trash list
paperforge trash restore <ITEM_ID>
paperforge trash purge [--older-than <DAYS>]
```

#### `paperforge note`

```bash
paperforge note set-flag --key <KEY> --field <FIELD> --value <VALUE> [--json]
```

#### `paperforge action` & `paperforge reconcile`

```bash
paperforge action list [--json]
paperforge action describe <ACTION_ID> [--json]
paperforge action preflight <ACTION_ID> [--scope all|paper|papers|collection] [--key <KEY>...] [--keys-file <FILE>] [--json]
paperforge action run <ACTION_ID> [--scope ...] [--key <KEY>...] [--keys-file <FILE>] [--confirm] [--follow] [--stream] [--json]

paperforge reconcile [--scope <SCOPE>] [--key <KEY>] [--json]
```

### 3. OCR 解析、版本与渲染审计

#### `paperforge ocr`

```bash
paperforge ocr [--key <KEY>] [--diagnose] [--stream] [--json]
paperforge ocr run [KEY...] [--keys-file <FILE>] [--stream]
paperforge ocr status [--batch <BATCH_ID>] [--json]
paperforge ocr resume [--batch <BATCH_ID>] [--json]
paperforge ocr redo [KEY...] [--dry-run] [--stream]
paperforge ocr list [--json] [--output <PATH>] [--manifest] [--keys <KEY>...]
paperforge ocr rebuild [KEY...] [--all] [--status <STATUS>] [--dry-run] [--resume] [--parallel|--no-parallel] [--stream]
paperforge ocr doctor [--live]
paperforge ocr test-connection [--json]
paperforge ocr pipeline-versions [--json]
```

显式范围不会回退到全库：未知 key、混合有效/未知 key、空白 key 或空文件会拒绝执行，不提交远程任务。

#### `paperforge versions`

```bash
paperforge versions list [--json]
paperforge versions show --key <KEY> [--json]
paperforge versions paths --key <KEY> [--label <LABEL>] [--json]
paperforge versions backups --key <KEY> [--json]
paperforge versions restore --key <KEY> --label <LABEL> [--json]
paperforge versions reset-live --key <KEY> [--json]
```

#### `paperforge render`

```bash
paperforge render audit [KEY...] [--json]
paperforge render reconcile [KEY...] [--include-pdf-media] [--apply-r] [--json]
paperforge render promote-r <KEY> [OBJECT_ID...] [--all] [--json]
paperforge render accept-proposal <KEY> <LABEL> --plan-hash <SHA256_FINAL_PLAN> [--json]
```

### 4. 记忆层、向量检出与状态诊断

#### `paperforge memory`

```bash
paperforge memory build [--key <KEY>] [--json]
paperforge memory status [--json]
paperforge memory restore-backup [--json]
```

#### `paperforge embed`

基于 SQLite + `sqlite-vec`（`vec0`）的 API-only 向量索引（无 ChromaDB 依赖）：

```bash
paperforge embed build [--resume] [--force] [--stream] [--json]
paperforge embed status [--probe] [--json]
paperforge embed list-models [--base-url <URL>] [--json]
paperforge embed test-connection [--json]
paperforge embed migrate [--json]
```

#### `paperforge memory-card`

维护 5 维动态认知记忆（`idea_logic` / `methods_params` / `research_craft` / `critique_limits` / `my_connection`）与 Obsidian Base 快照：

```bash
paperforge memory-card get <KEY> [--json]
paperforge memory-card refine <KEY> --facet <FACET> --content "..." [--json]
paperforge memory-card history <KEY> [--facet <FACET>] [--json]
paperforge memory-card clear <KEY> [--facet <FACET>] [--json]
paperforge memory-card base-snapshot [--json]
```

#### `paperforge status`、`paperforge doctor`、`paperforge repair`、`paperforge runtime-health`、`paperforge dashboard`

```bash
paperforge status [--json]
paperforge doctor [--json]
paperforge repair [--fix] [--fix-paths] [--json]
paperforge runtime-health [--json]
paperforge dashboard [--json]
```

#### `paperforge inspect` & `paperforge paper-status`

```bash
paperforge inspect <KEY|DOI|citation_key|title> [--json]   # 严格只读 6 阶段全链路诊断 (?mode=ro)
paperforge paper-status <QUERY> [--json]
```

开发者离线调试 OCR V3 分阶段跃迁（不修改 Vault）：

```bash
python scripts/dev/ocr_rebuild_paper.py --dump-stages-only --ocr-dir <vault/.paperforge/ocr> <KEY>
```

### 5. 阅读、批注、精读与网关命令

#### `paperforge annotations`

无损旁路 PDF 批注子系统（读写 `<workspace>/annotations.jsonl` 并同步至 `paperforge.db` `paper_annotations` 表；严格不改写源 PDF）：

```bash
paperforge annotations pdf-info <KEY> [--json]
paperforge annotations list <KEY> [--json]
paperforge annotations add <KEY> --page <N> --rects-json '[[0.1,0.2,0.8,0.24]]' [--kind highlight] [--color yellow] [--intent evidence] [--exact-text "..."] [--comment "..."] [--tags-json '[]'] [--style-json '{}'] [--json]
paperforge annotations update <KEY> <ANN_ID> [--color ...] [--intent ...] [--comment "..."] [--tags-json ...] [--style-json ...] [--rects-json ...] [--json]
paperforge annotations delete <KEY> <ANN_ID> [--json]
paperforge annotations promote <KEY> <ANN_ID> [--usage ...] [--project "..."] [--json]
paperforge annotations fulltext-preview <KEY> [--max-chars 80000] [--json]
paperforge annotations agent-mark <KEY> --quote "<原文>" [--figure-id figure_001] [--page-hint N] [--section-hint "..."] [--comment "<洞见>"] [--color purple] [--lens skeleton|methods|critique|custom] [--tags-json '[]'] [--json]
paperforge annotations agent-apply <KEY> [--items-json '<JSON>' | --input <FILE>] [--lens <LENS>] [--replace-lens] [--max-items N] [--json]
paperforge annotations adopt <KEY> <ANN_ID> [--json]
paperforge annotations clear-agent <KEY> [--lens <LENS>] [--json]
```

#### `paperforge reading-log` & `paperforge read`

```bash
paperforge reading-log --write <KEY> --section "Discussion P12" --excerpt "..." --usage "..." [--source-json '{...}'] [--json]
paperforge reading-log --search "<keywords>" [--paper <KEY>] [--include-history] [--limit 20] [--json]
paperforge reading-log --source-check <RECORD_ID> --paper <KEY> [--json]
paperforge reading-log --correct <ID> --correction "..." --reason "..." [--json]
paperforge reading-log --lookup <KEY> [--json]
paperforge reading-log --render
paperforge reading-log --since <YYYY-MM-DD> --limit 100 --output notes.md
paperforge reading-log --validate reading-log.md
paperforge reading-log --import reading-log.md

paperforge read <KEY> [--find "<TEXT>"] [--source] [--json]
```

#### `paperforge project-log`

```bash
paperforge project-log --write --project "ProjectX" --payload '{"hours":2,"status":"progress"}'
paperforge project-log --list --project "ProjectX"
paperforge project-log --render --project "ProjectX"
paperforge project-log --project "ProjectX" --json
```

#### `paperforge deep-reading` & `paperforge deep-finalize`

```bash
paperforge deep-reading [--json]
paperforge deep-finalize <KEY> [--json]
```

#### `paperforge context`、`paperforge agent-context` & L4 检索网关

```bash
paperforge context <KEY> | --domain <DOMAIN> | --collection <COLL> | --all
paperforge agent-context [--json]
paperforge paper-lookup "<query>" [--from-path <PATH>] [--limit 10] [--json]
paperforge content-discovery "<query>" [--limit 10] [--json]
paperforge paper-navigation "<query>" [--json]
paperforge scoped-fetch "<query>" [--limit 10] [--json]
```

#### `paperforge skill`

```bash
paperforge skill deploy [--to <DIR>] [--overwrite] [--json]
paperforge skill sync [--to <DIR>] [--json]
paperforge skill sync-hub [--json]
```

---

## 相关文档

- [使用教程](getting-started.md)
- [完整使用手册](user-manual.md)
- [故障排除](troubleshooting.md)
- [更新指南](update-upgrade.md)

---

## 测试

### 合成 OCR 测试（CI 默认）

```bash
python -m pytest tests/test_ocr_synthetic_fixtures.py -q --tb=short
```

### 真实文献 OCR 回归测试（可选集成测试）

```powershell
$env:PAPERFORGE_REAL_OCR_VAULT="D:\path\to\Literature-hub"; $env:PAPERFORGE_REAL_OCR_KEYS="SAN9AYVR,2GN9LMCW"; python -m pytest tests/test_ocr_real_paper_regressions.py -q
```
