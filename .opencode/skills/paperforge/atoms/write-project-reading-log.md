# write-project-reading-log

将叙述性证据直接写入 `Resources/Projects/<project>/reading-log.md`。

**定位：丰富内容层**——完整段落、写作素材、按 claim 组织的叙述性记录。

---

## 核心原则

**由 Agent 直接写入 markdown，不从 JSONL 渲染，不自动生成。**

这是给你（人类作者）看的文档，不是给机器解析的数据。因此应该用自然段落写作，按论点和 claim 组织，而非逐条粘贴 JSON。

---

## 前置条件

- bootstrap 已完成（有 `$VAULT`、`$PYTHON`）
- 已知 `project` 名称
- 目标文件路径：`$VAULT/Resources/Projects/<project>/reading-log.md`

---

## 步骤

### Step 1: 确认项目

从上下文获取 project 名称。如果未指定，询问用户。

### Step 2: 组织叙述内容

按 claim/论点组织写作素材，而非按论文。每段包含：

- **Claim 标题**（`##` 级别）
- **来源论文**（标题 + 年份 + 作者）
- **关键证据**（原文引用 + 你的解读）
- **与其他证据的关系**（支持/矛盾/补充）

### Step 3: 展示确认

```
即将写入 Resources/Projects/综述写作/reading-log.md:

# PEMF 对 GAG 合成的影响

## PEMF 促进软骨基质合成
Smith 2024 在体外软骨细胞实验中报告，PEMF 暴露后 GAG 含量增加 40%（原文：...）。
这与 Jones 2023 的结果一致......

确认写入？(y/n)
```

### Step 4: 写入文件

使用 `write` 工具追加到目标文件：

```text
目标路径：$VAULT/Resources/Projects/<project>/reading-log.md
写入模式：追加
内容：按 claim 组织的 markdown 段落
```

如果文件不存在，先创建空文件，再追加内容。

### Step 5: 确认写入成功

读取目标文件最后几行，确认内容已正确追加。

---

## 与 JSONL 的关系

| | JSONL | Project reading-log |
|---|-------|-------------------|
| 粒度 | 单句/单点 | 段落/claim 级 |
| 格式 | JSON 对象 | Markdown 叙述 |
| 使用者 | 机器搜索/渲染 | 人类阅读/写作 |
| 生成方式 | atom 写 | Agent 直接写 |
| 频率 | 高频 | 低频（仅在材料累积到可成段时） |

两者互补——JSONL 是索引，project reading-log 是内容。

---

## 禁止

- 不要从 JSONL 自动渲染——这是人工写作区域
- 不要只粘贴 JSON——这是给人看的文档
- 不要用单句代替完整段落
- 不要在用户确认前写入
