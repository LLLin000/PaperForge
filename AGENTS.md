# PaperForge — Agent Operating Guide

> 面向 AI Agent 的工作指示。项目文档在 `project/`，代码文档在 `docs/`。

---

## 0. 完成检查 — 对抗性审查 + 第一性原理

**每个开发任务完成后（commit 前），必须运行以下检查：**

### 0.1 对抗性审查（切换为批评者角色）

把自己当做**专门挑错的审查者**，不信任自己刚写的代码：

- **安全与边界**：输入校验在哪？信任边界在哪？如果传恶意/畸形数据会怎样？
- **正确性**：条件分支都覆盖了吗？负逻辑、空值、边界值？竞态条件？
- **错误处理**：失败路径都处理了吗？异常后会留下脏状态吗？
- **隐藏依赖**：有没有假设某个函数/变量/环境一定存在？如果它变了呢？
- **Spec 对齐**：代码真的解决了需求里的问题，还是只修了症状？

每条审查发现必须标注 severity（CRITICAL / MAJOR / MINOR），CRITICAL 必须修复才能提交。

### 0.2 第一性原理检查

回归最基本的问题，质疑所有假设：

- **这真的是要解决的问题吗？** 还是我修了表面症状？
- **为什么现有方案不够？** 根因是什么？为什么不直接在根因上修？
- **有没有更简单的方法？** 标准库 / 平台功能 / 已有依赖能不能搞定？能不能删代码而不是加代码？
- **这个改动值的吗？** 复杂度 vs 收益合理吗？有没有过度设计？
- **如果从零开始，我还会这么设计吗？** 现有代码的哪些假设在误导我？

### 0.3 自动化验证

1. 类型检查通过
2. 已有测试全部通过（`python -m pytest tests/ -q --tb=short`）
3. 新增代码有对应测试覆盖（至少一条断言走通新路径）
4. lint clean（`ruff check paperforge/`）

---

## 1. 工作指示

### Codebase Memory 优先

有 `codebase-memory-mcp` 知识图，结构查询优先用 `search_graph` / `trace_path`，不用 grep/glob。

### 测试命令

```bash
# Python 全量
python -m pytest tests/ -q --tb=short

# 按模块
python -m pytest tests/ -q --tb=short -k "figure or table or role"
pytest tests/test_ocr_blocks.py -q --tb=short

# JS plugin
cd paperforge/plugin && npx vitest run
```

### Ponytail 模式 — 始终默认激活

每次写代码前先激活：

```
1. 这东西真的需要写吗？（YAGNI）
2. 标准库能搞定吗？用标准库。
3. 平台原生功能覆盖了吗？用平台功能。
4. 已经装好的依赖能解决吗？用已有依赖。
5. 能不能一行写完？写一行。
6. 只有以上都否定，才写最少可行代码。
```

`@ponytail: {limit, upgrade_path}` 标注每个 shortcut 的上限。非平凡逻辑留一个可运行的自检。

### PROJECT-MANAGEMENT 更新规则

每个会话结束前更新 `PROJECT-MANAGEMENT.md`：每条 fix 记录问题→根因→修复→结果→测试状态。同步 resolved/remaining issues。

---

## 文档地图

| 受众 | 文件 |
|------|------|
| 终端用户教程 | [docs/getting-started.md](docs/getting-started.md) |
| 命令参考 | [docs/COMMANDS.md](docs/COMMANDS.md) |
| 架构 | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| 故障排除 | [docs/troubleshooting.md](docs/troubleshooting.md) |
| 项目计划/状态 | `project/current/*.md` |
| 设计文档 | `docs/superpowers/specs/` |
