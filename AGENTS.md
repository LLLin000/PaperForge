# PaperForge - Agent Operating Guide

> 本文档面向 **AI Agent**（OpenCode / Claude Code / GPT / Cursor 等）。终端用户请阅读 [使用教程](docs/getting-started.md)。

---

## 0. 文献入口规则 — 必须无条件遵守

**当用户提到以下任何内容时，你必须先加载 paperforge skill，再执行任何操作：**

```
"查文献" "搜文献" "找文献" "搜一下" "找一下" "查一下"
"搜论文" "找论文" "查论文" "搜文章" "找文章" "查文章"
"文献里" "库里" "collection"
"找证据" "找支持" "找依据" "找参数"
"读一下" "看看这篇" "精读"
"DC电场" "电刺激" "galvanotaxis" "电泳" 或其他学术术语
"保存这次" "记录一下" "提取方法论"
"review" "看到篇" "这篇论文"
```

**禁止行为（犯过一次的错误，不再犯）：**
- ❌ 用 `grep`/`rg`/`glob` 直接搜 vault 文件系统 — 必须用 `$PYTHON -m paperforge search/retrieve/context`
- ❌ 只用一个搜索工具就下结论 — 必须用多臂策略（retrieve 全文 + search 元数据 + context collection）
- ❌ 跳过大量搜索结果不告诉用户 — 超过 20 篇必须告知用户总数并提供缩小选项
- ❌ 在 `retrieve`（语义全文搜索）可用时只用 `search`（元数据搜索）— `retrieve` 能找到正文 Methods 中的内容

**加载方法：**

如果是 OpenCode：`<skill name="paperforge">`
如果是其他 Agent：读取 `.opencode/skills/paperforge/SKILL.md` 并按流程执行。

---

## 1. 核心不变式

1. **CLI 是命令真相源。** 所有 skill、workflow、文档命令引用必须对齐 `paperforge/cli.py`。
2. **Python 是运行时真相源。** Plugin 只读 canonical 快照，不做业务推断。
3. **`paperforge.json` 是路径真相源。** Plugin 和 Python 共享同源路径解析，不硬编码目录名。
4. **Agent 机械命令和思考工作流分层。** `/pf-sync` `/pf-ocr` `/pf-status` 是机械执行，`/pf-deep` `/pf-paper` 是思考工作流。

---

## 2. 架构边界

| 层 | 做什么 | 不做什么 |
|----|--------|---------|
| Plugin JS | 读快照、render UI、`execFile` 调 Python | 不读 SQLite、不推断 runtime 状态 |
| Python CLI | 写快照、sync/ocr/repair/embed/memory | 不被 JS 轮询驱动 |
| Memory DB | SQLite + FTS5，由 Python 全权重建 | JS 不读 memory DB |
| Vector DB | ChromaDB，由 `embed build` 管理 | 不与 memory DB 合并语义 |
| Skill/workflow | 路由 → 执行 CLI → 解释结果 | 不绕过 CLI 直操作文件 |

**Skill Graph 分层（`paperforge/skills/paperforge/`）：**

| 层 | 位置 | 职责 |
|----|------|------|
| Compound | `SKILL.md` | bootstrap → capability check → intent routing → dispatch to molecule |
| Molecules | `molecules/*.md` | 1 intent = 1 molecule，完整的用户意图执行流程 |
| Atoms | `atoms/*.md` | 可复用的检索/持久化/澄清子步骤 |

**Intent Routing 判定顺序（在 SKILL.md 中编码）：**
```text
0. 机械命令 → 直接执行
1. 研究别名 → /pf-deep→deep_analyze, /pf-paper→read_known
2. capture_project_knowledge — 用户要保存/归档
3. read_known_paper — 用户给定了明确 paper
4. discover_papers — 用户要论文列表
5. find_supporting_evidence — 用户要具体证据/参数
6. 无法判定 / 多 intent 冲突 → clarify-user-intent
7. Post-action: 其他 molecule 输出后用户要保存 → capture
```

**运行时快照契约：**

```
Python 写（每次相关 CLI 命令结束时）:
  runtime-health --json     → runtime-health.json
  memory status --json      → memory-runtime-state.json
  embed status --json       → vector-runtime-state.json
  embed build               → vector-build-state.json

JS 读（同步，不推断）:
  memoryState.getMemoryRuntime()
  memoryState.getVectorRuntime()
  memoryState.getRuntimeHealth()
```

---

## 3. 安全命令惯例

- 搜索用 `$PYTHON -m paperforge search` / `retrieve` / `context`，不用 `grep`/`rg`/`glob` 扫库。
- 路径从 bootstrap 或 paper-context 获取，禁止自行拼接。
- 未完成 paper-context 检查前不读原文（适用于 read-known-paper、deep-analyze-paper）。
- Reading-log 不是事实源，只能用做复查定位。
- 未知或拼错的 `/pf-*` 必须提示用户，禁止静默掉进 `project-engineering`。
- **每个 molecule 开头有 Pre-flight Checklist，必须逐项打勾再执行，不跳步。**

---

## 4. Codebase Memory (Knowledge Graph)

This project has **codebase-memory-mcp** installed — a knowledge graph of the entire repo. Use it instead of grep/glob for structural queries.

### When to Use

| Agent task | Use this tool | Instead of |
|-----------|--------------|------------|
| Find definition of X | `search_graph` | grep/glob |
| Who calls this function | `trace_path` | recursive grep |
| Architecture overview | `get_architecture` | manual reading |
| Find all routes/views | `search_graph(label="Route")` | glob guessing |
| Impact of changing X | `detect_changes` | grep + manual tracing |
| Complex relationship query | `query_graph` (Cypher) | multiple greps |
| Search by semantic meaning | `search_graph(semantic_query=[...])` | keyword guessing |
| Read source code | `get_code_snippet` | reading around |

### Rules

1. **Graph first.** For any structural question (definitions, callers, call chains, routes, imports), use graph tools before grep/glob.
2. **`search_graph` before `get_code_snippet`.** Discover the `qualified_name` first, then read the source.
3. **Use `project=<name>` filter.** Check with `list_projects` if unsure.
4. **`trace_path` replaces recursive grep.** Find all callers: `trace_path(function_name="X", direction="inbound")`. Depth up to 5.
5. **`detect_changes` for change impact.** Before modifying shared code, check what depends on it.

### Quick Reference

```
search_graph(query="find all handlers", label="Function")
search_graph(name_pattern=".*Handler.*", label="Function")
search_graph(semantic_query=["send", "publish"])
trace_path(function_name="search", direction="inbound", depth=3)
trace_path(function_name="search", direction="outbound")
get_architecture(aspects=["all"])
detect_changes(since="HEAD~5")
query_graph(query="MATCH (f:Function) WHERE f.complexity > 10 RETURN f.name, f.complexity")
```

---

## 5. 路由

| Route | 类型 | 动作 |
|-------|------|------|
| `/pf-sync` | 机械 | 执行 `paperforge sync`，解释结果 |
| `/pf-ocr` | 机械 | 执行 `paperforge ocr`，解释结果 |
| `/pf-status` | 机械 | 执行 `paperforge status --json` 或 `paperforge runtime-health --json`，解读状态 |
| `/pf-deep` | 思考 | 打开 `molecules/deep-analyze-paper.md` 执行完整流程 |
| `/pf-paper` | 思考 | 打开 `molecules/read-known-paper.md` 执行完整流程 |

---

## 6. 版本发布流程

发布新版前确认测试通过，然后 bump 版本：

```bash
# Bump patch (1.5.x → 1.5.x+1)
python scripts/bump.py patch

# Bump minor (1.x.0 → 1.x+1.0)
python scripts/bump.py minor

# Bump to specific version
python scripts/bump.py 1.6.0

# 预览（不实际修改）
python scripts/bump.py patch --dry-run
```

bump.py 会自动：更新 `__init__.py` / `manifest.json` → commit → tag。
完成后需推送：

```bash
git push && git push --tags
```

GitHub Actions（release.yml / publish.yml）会自动在 tag push 后创建 Release 并构建插件。

---

## 7. Skill 部署

Skill 文件在 `paperforge/skills/paperforge/` 中。部署到 vault 由 `paperforge/services/skill_deploy.py` 处理：
- **setup wizard**：首次安装时部署
- **`paperforge update`**：更新时覆盖部署（`overwrite=True`）
- 手动部署到 vault 的 `.opencode/skills/paperforge/`：直接 copy 整个目录

---

## 8. 测试

```bash
# Python
python -m pytest tests/unit/ tests/cli/ -v --tb=short

# JS
cd paperforge/plugin && npx vitest run

# Lint
ruff check --fix paperforge/ && ruff format paperforge/

# Skill Graph contract tests
python -m pytest tests/test_skill_graph_contracts.py tests/test_skill_graph_layout.py tests/test_pf_bootstrap_capabilities.py -v --tb=short
```

---

## 9. Ponytail 模式 — 始终默认激活

> **本 section 是** ***开发纪律*** **，不是可选模式。** 无论用户是否提到 ponytail，每次编写/修改代码前必须先读本节并默认遵守。

### 核心原则

```
1. 这个东西真的需要写吗？（YAGNI）
2. 标准库能搞定吗？用标准库。
3. 平台原生功能覆盖了吗？用平台功能。
4. 已经装好的依赖能解决吗？用已有依赖。
5. 能不能一行写完？写一行。
6. 只有以上都否定，才写最少可行代码。
```

从未被要求的抽象、可避免的依赖、没人要的样板——删。boring 优于 clever。最少的文件数。

### 三级模式

级别通过以下方式设定：
- 用户说 `ponytail lite|full|ultra` 切换
- 用户不指定时默认 **full**
- 用户说 `stop ponytail` / `normal mode` 退出

| 级别 | 何时用 | 怎么做 |
|------|--------|--------|
| **lite** | 添加小功能 | 单文件 + 无依赖，跳过非必要抽象层 |
| **full** (default) | 修复 bug | 删体积、不加额外防护、延迟校验到异常时 |
| **ultra** | 探索/原型 | 最少行，用注释声明已知上限不走完整方案 |

### 纪律

- `@ponytail: {limit, upgrade_path}` 注释标注每个 shortcut 的已知上限和升级路径
- Laziness 不是偷懒——**不动比多写强，删比加好，减一行大于加十行**
- 从不简化：信任边界输入校验、防数据丢失的错误处理、安全措施、基础设施可访问性、硬件所需的校准、用户要求保留的内容
- 非平凡的逻辑至少留下一个可运行的自检（assert demo 或一个小测试文件）

### 自动触发规则

即使没有明确听到 "ponytail"，以下场景应自动激活 ponytail full 模式：

| 触发信号 | 说明 |
|----------|------|
| 用户上来就给需求，没有说"设计"、"架构"、"考虑" | 默认 full：精准修，不额外抽象 |
| 对话中已经有很多轮讨论 | 默认 full：删体积，不加新结构 |
| 用户说"快速"、"简单"、"修一下"、"改一下" | 默认 full |
| 用户说了自己的修改方案 | 尊重方案，不做过度设计 |

---


## 10. Role Pipeline Notes

### `table_html` 来源

`table_html` 不仅可以由 `write_back_table_roles()`（table matching 后）产生，现在也由 `assign_block_role()` 对 inline `<table>` HTML 块直接分配。`ocr_document.py:6120-6121` 的 `table_html → table_html_candidate` 转换已删除（无下游处理）。

### `_recover_figure_heading_prefix()`

位于 `ocr_figures.py` 末尾，当 PaddleOCR 漏掉 "Figure N" 前缀时从 PDF 文本层恢复 caption heading。在 `build_figure_inventory()` 的 zone/style filter 前调用，前置恢复 prefix 使 `_extract_figure_number()` 能识别。

### 修改文件清单
此会话修改了 4 个文件:
- `paperforge/worker/ocr_figures.py` — `_recover_figure_heading_prefix()` + `body_zone` filter guard
- `paperforge/worker/ocr_roles.py` — inline `<table>` 在 raw_label=table 前检查
- `paperforge/worker/ocr_document.py` — 删除 `table_html_candidate` 死路径
- `paperforge/worker/ocr_structural_gate.py` — `table_html` 验证器
## 11. PROJECT-MANAGEMENT 实时更新规则

每个开发会话结束时（或阶段性完成后），必须更新 `PROJECT-MANAGEMENT.md`。规则：

1. **每完成一个 fix，立即记录**：不要攒到会话最后。每个 fix 完成后即追加条目。
2. **记录格式**：`### N.M 标题 (YYYY-MM-DD)`，包含问题 → 根因 → 修复 → 结果 → 测试状态。
3. **Remaining known issues 同步**：如果修复解决了某个已知 issue，从列表中删除或注明 resolved。
4. **Parked Hard Case 同步**：如果发现新的边界情况无法在当前 fix 中处理，追加到 Parked Hard Case。
5. **会话结束前提交**：PROJECT-MANAGEMENT 的更新必须随最后的 push 一起提交。

---

## 文档地图

| 受众 | 文件 |
|------|------|
| 终端用户教程 | [docs/getting-started.md](docs/getting-started.md) |
| 故障排除 | [docs/troubleshooting.md](docs/troubleshooting.md) |
| 命令参考 | [docs/COMMANDS.md](docs/COMMANDS.md) |
| 更新升级 | [docs/update-upgrade.md](docs/update-upgrade.md) |
| 架构 | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| 维护者 | [docs/maintainer-guide.md](docs/maintainer-guide.md) |
| 迁移历史 | [docs/MIGRATION-v1.2.md](docs/MIGRATION-v1.2.md) |
| Skill Graph Spec (设计文档) | [docs/superpowers/specs/2026-05-19-paperforge-skill-graph-design.md](docs/superpowers/specs/2026-05-19-paperforge-skill-graph-design.md) |
