# /pf-paper

## Purpose

基于 Zotero OCR 文本的单篇论文工作台入口。

1. 解析 `/pf-paper <query>` 中的查询词
2. 支持 Zotero key、标题片段、DOI、PMID、关键词
3. 优先搜索本地 Zotero，解析到单篇目标论文
4. 根据 Vault 根目录的 `paperforge.json` 加载 `<system_dir>/PaperForge/ocr/<KEY>/fulltext.md` 作为主文本
5. 读取 `meta.json` 显示论文标题、作者、期刊、年份
6. 进入 Q&A 模式，用中文回答用户关于该论文的问题
7. 在当前论文上下文中，用户可再说"精读这篇文章"切换到 deep 层

## CLI Equivalent

```bash
# 准备阶段（间接）
paperforge sync      # 生成正式笔记
```

> `/pf-paper` 是 **Agent 层命令**，无直接 CLI 等效命令。

## Prerequisites

- [ ] 正式笔记已生成（`paperforge sync` 生成）
- [ ] 正式笔记已生成（用于定位论文）
- [ ] `fulltext.md` 存在（推荐，用于基于原文回答；如不存在则基于元数据回答）

> **注意**：与 `/pf-deep` 不同，`/pf-paper` **不强制要求** OCR 完成。没有 OCR 时基于论文元数据和公开信息回答。

## Arguments

| 参数 | 必需 | 说明 |
|------|------|------|
| `<query>` | 是 | Zotero key、标题片段、DOI、PMID 或关键词 |
| `<query2> ...` | 否 | 可同时加载多篇论文 |

### 解析规则

1. 如果输入看起来像 8 位 Zotero key，则直接按 key 解析。
2. 否则先在本地 Zotero 中搜索标题/摘要。
3. 若命中唯一结果或明显最佳结果，则直接载入。
4. 若存在多个合理候选，则先列候选清单再让用户选。
5. 不要强迫用户先知道 Zotero key。

## Example

```bash
/pf-paper XGT9Z257
/pf-paper Predictive findings on magnetic resonance imaging
/pf-paper 10.1016/j.jse.2018.01.001
/pf-paper XGT9Z257 PQR8KLM
```

## Output

加载成功后显示：

```
已加载论文: [title] ([year], [journal])
Zotero Key: [key]
请基于论文原文回答问题。如信息未在论文中提及，会明确说明。
请问有什么问题？
```

### 多篇论文模式

多个 key 时依次加载所有 `fulltext.md`，回答时说明来源：
```
来源 [KEY1]: ...
来源 [KEY2]: ...
```

### 回答原则

- **严格基于** `fulltext.md` 中的文本内容回答
- 引用原文时标注来源页码/章节
- 用中文（简体中文）回答
- 论文中未提及的内容，明确说明"论文中未提及该内容"
- 需要结合论文以外知识的问题，说明"该问题需要结合论文以外的知识回答"

## Error Handling

### 论文未找到
- **表现**：Zotero key 无效或搜索无结果
- **解决**：确认 key 正确，或尝试用标题片段搜索

### 多个候选结果
- **表现**：搜索返回多个匹配的论文
- **处理**：Agent 列出候选清单，让用户选择目标论文

### OCR 文件缺失
- **表现**：`fulltext.md` 不存在
- **处理**：Agent 基于元数据和公开信息回答，并告知用户"OCR 文本不可用，回答基于元数据"

## Platform Notes

### OpenCode

- `/pf-paper` 在对话窗口直接输入
- Agent 使用 `paperforge paths --json` 获取 Vault 路径配置
- 单篇加载时直接读取文件内容到对话上下文
- 多篇加载时分别读取每篇的 `fulltext.md`
- 用户可在同一上下文中说"精读这篇文章"无缝切换到 `/pf-deep` 模式

### Codex

> **Future**：计划支持。预计通过 API 调用实现类似功能。

### Claude Code

> **Future**：计划支持。预计通过工具调用或文件附件实现。

## See Also

- [pf-deep](pf-deep.md) — 完整三阶段精读
- [AGENTS.md](../AGENTS.md) — 完整使用指南、架构说明、常见问题
- [docs/COMMANDS.md](../docs/COMMANDS.md) — 命令总览与矩阵
