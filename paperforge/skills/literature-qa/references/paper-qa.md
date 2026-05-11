# 论文问答

交互式论文 Q&A 工作台。不强制要求 OCR，但 OCR 完成后回答更准确。

**所有 Python 命令用 `$PYTHON`（来自 pf_bootstrap 的 `python_candidate`），vault 路径用 `$VAULT`。**

---

## 前置条件

- [ ] 已完成论文定位（参考 [paper-resolution.md](paper-resolution.md)），拿到 zotero_key 和 workspace
- [ ] OCR 完成（推荐但非强制）

---

## 执行流程

### Step 1: 加载论文

1. 确认 workspace 路径
2. 读 `fulltext.md`（如果存在）作为主要回答依据
3. 读 formal note frontmatter 获取元数据（标题、作者、期刊、年份）
4. 如果 fulltext.md 不存在，告知用户 "OCR 文本不可用，回答将基于元数据和公开信息"

### Step 2: 显示论文信息

```
已加载论文: [title] ([year], [journal])
作者: [authors]
Zotero Key: [key]
领域: [domain]
OCR 状态: [done / 不可用]
结束对话时说 "保存" 即可保存讨论。
请问有什么问题？
```

### Step 3: 进入 Q&A 模式

- 等待用户提问
- 每次回答后等待下一个问题
- 持续到用户说 "保存"、"结束"、"完成" 等关键词

---

## 回答原则

- **严格基于** fulltext.md 中的文本内容回答
- 引用原文时标注来源页码/章节（如 "第 3 页，Methods 部分"）
- 用中文（简体中文）回答
- 论文中未提及的内容，明确说明 "论文中未提及该内容"
- 需要结合论文以外知识的问题，说明 "该问题需要结合论文以外的知识"

---

## 切换模式

用户在当前对话中可以说 "精读这篇文章" 切换到 deep-reading 模式。此时加载 [deep-reading.md](deep-reading.md) 执行精读流程。

---

## 保存记录

用户说 "保存"、"结束"、"完成"、"保存讨论" 时，加载 [save-session.md](save-session.md) 执行保存。不要自动保存。
