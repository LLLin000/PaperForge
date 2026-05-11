# 批量文献阅读

用户需要阅读多篇文献并总结——综述写作、找引用、研究方向调研等。

---

## 触发条件

- 用户给了一个 collection 名（Zotero 收藏夹）
- 用户给了模糊方向（"帮我看一下骨科里关于支架材料的文章"）
- 用户给了多篇文献要求一起读
- 用户说"总结库里XXX方向的文献"、"写一段文献综述"

---

## 执行流程

### Step 1: 确定文献范围

和用户确认要读哪些文献：
- 用户给了 collection 名 → 读 `$IDX_PATH`，筛 `collection_path` 包含该名称的条目
- 用户给了关键词方向 → 用 paper_resolver search 或直接 grep `$IDX_PATH`
- 用户给了多篇 key → 直接确认 key 列表

列出候选让用户确认：

```
找到 N 篇匹配 (<collection名/关键词>):

[1] ABC12345 — Title (Author, Year, Domain, OCR: done/pending)
[2] DEF67890 — Title (Author, Year, Domain, OCR: done/pending)
...

要全部读，还是选几篇？(输入编号如 "1,3,5" 或 "all")
```

### Step 2: 逐篇阅读

对每篇选定文献：

1. `$PYTHON -m paperforge.worker.paper_resolver resolve-key <KEY> --vault "$VAULT"` → 获取 workspace 路径
2. 读 formal note frontmatter → 元数据
3. 如果有 `fulltext.md` → 读 Abstract、Results、Discussion
4. 如果有 `ocr_status == "done"` 但 fulltext 内容太长 → 先读 caption + figure 描述定位关键段落
5. 如果没有 fulltext → 如实告知用户，仅基于已知信息

### Step 3: 写 Reading Log（JSON → MD）

**先构建 JSON（Agent 内部，不写入文件）：**

```json
{
  "task": "用户原始指令原文",
  "papers": [
    {
      "key": "ABC12345",
      "title": "Paper Title",
      "authors": "Smith et al.",
      "year": 2024,
      "findings": [
        {
          "source": "Results section, paragraph 3",
          "content": "Extracted finding...",
          "citation_use": "可用于支撑 XXX 观点"
        }
      ]
    }
  ]
}
```

**再渲染为 MD，追加写入 `$VAULT/Bases/reading-log-<timestamp>.md`：**

```markdown
# Reading Log — 用户要求: <原文引用用户指令>

---

## ABC12345 | Paper Title | Smith et al., 2024

### 提取点 1
- **来源**: Results section, paragraph 3
- **内容**: Extracted finding...
- **引用建议**: 可用于支撑 XXX 观点

### 提取点 2
- **来源**: Discussion, final paragraph
- **内容**: ...
- **引用建议**: ...

---

## DEF67890 | Another Title | Jones et al., 2023

（同上格式）

---
```

**关键规则：**
- JSON 确保格式稳定，MD 是最终交付产物
- zotero_key、标题、作者及年份 **缺一不可**
- 每个提取点必须注明 **来源**（文章哪句话/哪个段落）
- 同一任务的多篇文献 **追加写入同一个文件**，不要每篇新建

### Step 4: 整合输出

全部读完，根据用户原始意图输出总结：

**综述写作**：
```
从 N 篇文献中：
- 主题A 共识: ...
- 主题A 争议: ...
- 方法论趋势: ...
- 关键引用:
  1. "...[结论]" — ABC12345 (Author, Year), Fig.X
  2. ...
```

**找引用**：
```
以下文献适合引用：
- 支撑 "XXX" 观点 → ABC12345 (Author, Year), Results
- 支撑 "YYY" 方法 → DEF67890 (Author, Year), Methods
```

### Step 5: 问用户保存位置

```
Reading log 已生成。要保存到哪里？
(留空 → 默认 $VAULT/Bases/reading-log-<ts>.md)
```

让用户指定路径。如果用户说不清，默认放到 `$VAULT/Bases/`。

---

## 注意事项

- **暂时不支持多篇阅读后运行 pf-end / 结束讨论**（该功能待定）
- 如果某篇文献没有 fulltext，如实告知用户，不要捏造内容
- Reading log 中每条提取点必须在原文中有据可查
- JSON → MD 转换由 Agent 完成，用户只看到 MD 文件
