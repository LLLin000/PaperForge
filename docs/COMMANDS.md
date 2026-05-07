# PaperForge 命令总览

> PaperForge 完整命令参考。Agent 命令与 CLI 命令对照表。
>
> 另见：[AGENTS.md](../AGENTS.md) — 完整使用指南与架构说明

---

## 命令矩阵

| Agent 命令 | CLI 命令 | 说明 | 前置条件 | 示例 |
|-----------|---------|------|---------|------|
| `/pf-deep` | `paperforge sync` + `paperforge ocr` | 完整三阶段精读（Keshav 法） | OCR 完成 (`ocr_status: done`) | `/pf-deep ABCDEFG` |
| `/pf-paper` | `paperforge sync` | 快速摘要与问答工作台 | 正式笔记已生成 | `/pf-paper ABCDEFG` |
| `/pf-ocr` | `paperforge ocr` | PDF OCR 文本与图表提取 | PDF 存在 + `do_ocr: true` | `paperforge ocr` |
| `/pf-sync` | `paperforge sync` | 同步 Zotero 到文献库 | Better BibTeX JSON 导出 | `paperforge sync --domain 骨科` |
| `/pf-status` | `paperforge status` | 查看系统安装与运行状态 | 配置完成 | `paperforge status` |

> **说明**：Agent 命令（`/pf-*`）在对话窗口中输入，由 AI Agent 执行。CLI 命令在终端中输入，由 Python worker 执行。

---

## 快速参考

| 命令 | 一句话说明 |
|------|-----------|
| `/pf-deep <key>` | 对单篇论文进行 figure-by-figure 深度精读 |
| `/pf-paper <key>` | 加载论文 OCR 文本，进入问答模式 |
| `paperforge ocr` | 处理所有标记 `do_ocr: true` 的文献 |
| `paperforge sync` | 检测 Zotero 新条目，直接生成正式笔记 |
| `paperforge status` | 检查安装状态、配置、路径连通性 |

---

## 工作流参考

典型使用顺序（首次安装后）：

### 第一步：同步文献
```bash
paperforge sync
```
- 检测 Zotero JSON 中的新条目
- 生成正式笔记 `<resources_dir>/<literature_dir>/<domain>/<key> - Title.md`

### 第二步：标记 OCR
在 Obsidian 中打开 formal note 文件，将 `do_ocr: false` 改为 `do_ocr: true`。

或使用命令行批量修改（高级用户）：
```bash
# 示例：批量标记某领域的所有文献
grep -l "do_ocr: false" <resources_dir>/<literature_dir>/骨科/*.md | xargs sed -i 's/do_ocr: false/do_ocr: true/'
```

### 第三步：运行 OCR
```bash
paperforge ocr
```
- 上传 PDF 到 PaddleOCR API
- 提取全文文本和图表
- 输出到 `<system_dir>/PaperForge/ocr/<key>/`

### 第四步：标记精读
在 formal note 中将 `analyze: false` 改为 `analyze: true`。

### 第五步：执行精读
在 Agent 对话中输入：
```
/pf-deep ABCDEFG
```
Agent 自动：
1. 检查 OCR 状态和 formal note
2. 生成 `## 精读` 骨架
3. 逐阶段填写精读内容（Pass 1/2/3）
4. 验证结构完整性

---

## 命令详情

各命令的详细文档见对应文件：

- [`command/pf-deep.md`](../command/pf-deep.md) — 深度精读
- [`command/pf-paper.md`](../command/pf-paper.md) — 快速摘要
- [`command/pf-ocr.md`](../command/pf-ocr.md) — OCR 提取
- [`command/pf-sync.md`](../command/pf-sync.md) — 文献同步
- [`command/pf-status.md`](../command/pf-status.md) — 状态检查

---

## 平台说明

### OpenCode

- Agent 命令以 `/pf-` 前缀输入，支持文件附件
- `/pf-deep` 和 `/pf-paper` 需要 OCR 完成的 PDF 作为上下文
- Agent 使用 `paperforge paths --json` 获取 Vault 路径配置
- 多篇文章并行精读时使用 `Task` tool 启动 subagent

### Codex

> **Future**：Codex 平台支持计划开发中。预计采用类似的 `/pf-*` 命令前缀，通过 API 调用 PaperForge CLI。

### Claude Code

> **Future**：Claude Code 平台支持计划开发中。预计通过 `@paperforge` 提及或专用工具调用实现集成。

---

## 相关文档

- [AGENTS.md](../AGENTS.md) — 完整使用指南、架构说明、常见问题
- [docs/INSTALLATION.md](INSTALLATION.md) — 安装步骤
- [docs/MIGRATION-v1.2.md](MIGRATION-v1.2.md) — v1.1 → v1.2 迁移指南
- [docs/ARCHITECTURE.md](ARCHITECTURE.md) — 系统架构与设计决策

---

*PaperForge Lite v1.2 | 命令参考文档*
