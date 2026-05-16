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
- 未完成 paper-context 检查前不读原文（deep-reading、paper-qa）。
- Reading-log 不是事实源，只能用做复查定位。
- 未知或拼错的 `/pf-*` 必须提示用户，禁止静默掉进 `project-engineering`。

---

## 4. 机械 vs 思考路由

| Route | 类型 | 动作 |
|-------|------|------|
| `/pf-sync` | 机械 | 执行 `paperforge sync`，解释结果 |
| `/pf-ocr` | 机械 | 执行 `paperforge ocr`，解释结果 |
| `/pf-status` | 机械 | 执行 `paperforge status --json` 或 `paperforge runtime-health --json`，解读状态 |
| `/pf-deep` | 思考 | 打开 `workflows/deep-reading.md` 执行完整流程 |
| `/pf-paper` | 思考 | 打开 `workflows/paper-qa.md` 执行完整流程 |

---

## 5. 测试

```bash
# Python
python -m pytest tests/unit/ tests/cli/ -v --tb=short

# JS
cd paperforge/plugin && npx vitest run

# Lint
ruff check --fix paperforge/ && ruff format paperforge/
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
