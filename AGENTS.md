# PaperForge - Agent Operating Guide

> 本文档面向 **AI Agent**（OpenCode / Claude Code / GPT / Cursor 等）。终端用户请阅读 [使用教程](docs/getting-started.md)。

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

- 搜索用 `$PYTHON -m paperforge search`，不用 `grep`/`glob` 扫库。
- 路径从 bootstrap 或 paper-context 获取，禁止自行拼接。
- 未完成 paper-context 检查前不读原文（适用于 read-known-paper、deep-analyze-paper）。
- Reading-log 不是事实源，只能用做复查定位。
- 未知或拼错的 `/pf-*` 必须提示用户，禁止静默掉进 `project-engineering`。
- **每个 molecule 开头有 Pre-flight Checklist，必须逐项打勾再执行，不跳步。**

---

## 4. 路由

| Route | 类型 | 动作 |
|-------|------|------|
| `/pf-sync` | 机械 | 执行 `paperforge sync`，解释结果 |
| `/pf-ocr` | 机械 | 执行 `paperforge ocr`，解释结果 |
| `/pf-status` | 机械 | 执行 `paperforge status --json` 或 `paperforge runtime-health --json`，解读状态 |
| `/pf-deep` | 思考 | 打开 `molecules/deep-analyze-paper.md` 执行完整流程 |
| `/pf-paper` | 思考 | 打开 `molecules/read-known-paper.md` 执行完整流程 |

---

## 5. 版本发布流程

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

## 6. Skill 部署

Skill 文件在 `paperforge/skills/paperforge/` 中。部署到 vault 由 `paperforge/services/skill_deploy.py` 处理：
- **setup wizard**：首次安装时部署
- **`paperforge update`**：更新时覆盖部署（`overwrite=True`）
- 手动部署到 vault 的 `.opencode/skills/paperforge/`：直接 copy 整个目录

---

## 7. 测试

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
