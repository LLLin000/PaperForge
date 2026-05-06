---
name: pf-paper
description: Quick paper Q&A workbench. Load a paper by Zotero key, title, DOI, or PMID and answer questions. Does not require OCR.
allowed-tools: [Read, Bash]
---

# <prefix>pf-paper

## Purpose

基于 Zotero OCR 文本的单篇论文工作台入口。

1. 解析 `<prefix>pf-paper <query>` 中的查询词
2. 支持 Zotero key、标题片段、DOI、PMID、关键词
3. 优先搜索本地 Zotero，解析到单篇目标论文
4. 根据 Vault 根目录的 `paperforge.json` 加载 `<system_dir>/PaperForge/ocr/<KEY>/fulltext.md` 作为主文本
5. 读取 `meta.json` 显示论文标题、作者、期刊、年份
6. 进入 Q&A 模式，用中文回答用户关于该论文的问题
7. 在当前论文上下文中，用户可再说"精读这篇文章"切换到 deep 层

## CLI Equivalent

```bash
# 准备阶段（间接）
paperforge sync      # 生成正式笔记和 library-records
```

> `<prefix>pf-paper` 是 **Agent 层命令**，无直接 CLI 等效命令。

## Prerequisites

- [ ] 正式笔记已生成（`paperforge sync` 生成）
- [ ] library-record 存在（用于定位论文）
- [ ] `fulltext.md` 存在（推荐，用于基于原文回答；如不存在则基于元数据回答）
- [ ] discussion.py 模块可用（`python -m paperforge.worker.discussion --help` 可执行）

> **注意**：与 `/pf-deep` 不同，`<prefix>pf-paper` **不强制要求** OCR 完成。没有 OCR 时基于论文元数据和公开信息回答。

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
<prefix>pf-paper XGT9Z257
<prefix>pf-paper Predictive findings on magnetic resonance imaging
<prefix>pf-paper 10.1016/j.jse.2018.01.001
<prefix>pf-paper XGT9Z257 PQR8KLM
```

## Output

加载成功后显示：

```
已加载论文: [title] ([year], [journal])
Zotero Key: [key]
请基于论文原文回答问题。如信息未在论文中提及，会明确说明。
请问有什么问题？
```

会话结束后，讨论记录将自动保存至论文工作区 `ai/discussion.json` 和 `ai/discussion.md`。

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

## 8. 保存讨论记录

在 Q&A 会话结束时，Agent 必须将本次讨论记录保存到论文工作区的 `ai/` 目录中。

**操作步骤：**

1. 在会话中积累所有 Q&A 对 —— 每次用户提问和 Agent 回答都记录为一对：
   ```json
   {
     "question": "用户的问题",
     "answer": "Agent 的回答",
     "source": "user_question",
     "timestamp": "2026-05-06T12:00:00+08:00"
   }
   ```
   其中 `source` 为 `"user_question"`（用户提问）或 `"agent_analysis"`（Agent 主动分析）。

2. 会话结束时，将 Q&A 对序列化为 JSON 字符串，调用 CLI：
   ```bash
   python -m paperforge.worker.discussion record <ZOTERO_KEY> \
       --vault "<VAULT_PATH>" \
       --agent pf-paper \
       --model "<MODEL_NAME>" \
       --qa-pairs '<JSON_ARRAY>'
   ```

3. CLI 返回 JSON：
   ```json
   {"status": "ok", "json_path": "Literature/{domain}/{key} - {title}/ai/discussion.json", "md_path": "Literature/{domain}/{key} - {title}/ai/discussion.md"}
   ```
   如果 `status` 为 `"error"`，记录错误信息但不中断会话流程。

**注意：**
- 仅 `/pf-paper` 记录讨论。`/pf-deep` 不记录（精读内容已写入正式笔记）。
- 如果论文没有 library-record（无法解析 domain/title），记录会失败但不影响正常使用。
- 所有 Q&A 内容以 UTF-8 编码写入，支持中文。

## See Also

- [pf-deep](pf-deep.md) — 完整三阶段精读
