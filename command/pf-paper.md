# /pf-paper

基于 Zotero OCR 文本的单篇论文工作台入口。

## 功能

1. 解析 `/pf-paper <query>` 中的查询词
2. 支持 Zotero key、标题片段、DOI、PMID、关键词
3. 优先搜索本地 Zotero，解析到单篇目标论文
4. 根据 Vault 根目录的 `paperforge.json` 加载 `<system_dir>/PaperForge/ocr/<KEY>/fulltext.md` 作为主文本
5. 读取 `meta.json` 显示论文标题、作者、期刊、年份
6. 进入 Q&A 模式，用中文回答用户关于该论文的问题
7. 在当前论文上下文中，用户可再说"精读这篇文章"切换到 deep 层

## 加载后提示语

```
已加载论文: [title] ([year], [journal])
Zotero Key: [key]
请基于论文原文回答问题。如信息未在论文中提及，会明确说明。
请问有什么问题？
```

## 回答原则

- **严格基于** `fulltext.md` 中的文本内容回答
- 引用原文时标注来源页码/章节
- 用中文（简体中文）回答
- 论文中未提及的内容，明确说明"论文中未提及该内容"
- 需要结合论文以外知识的问题，说明"该问题需要结合论文以外的知识回答"

## 多篇论文

多个 key 时依次加载所有 `fulltext.md`，回答时说明来源：
```
来源 [KEY1]: ...
来源 [KEY2]: ...
```

## 解析规则

1. 如果输入看起来像 8 位 Zotero key，则直接按 key 解析。
2. 否则先在本地 Zotero 中搜索标题/摘要。
3. 若命中唯一结果或明显最佳结果，则直接载入。
4. 若存在多个合理候选，则先列候选清单再让用户选。
5. 不要强迫用户先知道 Zotero key。

## 使用示例

```bash
/pf-paper XGT9Z257
/pf-paper Predictive findings on magnetic resonance imaging
/pf-paper 10.1016/j.jse.2018.01.001
/pf-paper XGT9Z257 PQR8KLM
```
