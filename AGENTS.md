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

### ⚠️ 对抗性审查产生的修改必须先讨论，不能直接改

对抗性审查发现的问题 → 先用第一性原理分析根因和方案 → **向用户报告并询问是否要修**，不能直接上手改。

原因是：对抗性审查是挑错模式，倾向于过度工程化（为边缘情况加复杂逻辑）。用户了解全局优先级，可能认为当前方案"足够好"、风险可接受、或已有其他计划。直接改会浪费精力、引入未对齐的复杂度。

唯一例外：**确认是 CRITICAL 安全漏洞或数据丢失 bug**，可以先修再报告。

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

### Codebase Memory MCP（知识图谱）

`codebase-memory-mcp` 已索引整个项目（25K+ nodes, 53K+ edges），支持结构化代码查询。

**典型使用场景：**

| 工具 | 用法 | 示例 |
|------|------|------|
| `search_graph` | 自然语言搜代码 | `search_graph("layout profile column detection")` → 秒出相关函数 |
| `trace_path` | 调用链追踪 | `trace_path("build_figure_inventory", direction="both")` → callees + callers |
| `get_architecture` | 架构总览 + 热点函数 | `get_architecture(aspects=["hotspots"])` → fan-in 排名 |
| `get_code_snippet` | 精确取函数源码 | `get_code_snippet("_classify_page_layout")` → 完整代码 |
| `query_graph` | Cypher 自定义查询 | 查循环深度≥3 的函数、查递归函数等 |
| `detect_changes` | 改动影响分析 | `detect_changes(scope="ocr_document.py")` → 哪些测试受影响 |
| `manage_adr` | 记录架构决策 | `manage_adr(mode="update", ...)` → 跨 session 持久化 |

**搜索优先于文本 grep：**
```python
# 不要：grep / rg / "find references" 文本搜索 — 迷失在 6000+ 行文件里
# 应该：
search_graph("column aware figure heading")        # 自然语言 → 相关函数
trace_path("_recover_figure_heading_prefix")        # 调用链追踪
get_architecture(aspects=["hotspots"])               # 项目热点
```

**索引维护：**
项目已在索引中。代码有较大改动后手动重新索引（fast 模式，跳过语义相似度）：
```
index_repository(mode="fast", persistence=True)
```

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
