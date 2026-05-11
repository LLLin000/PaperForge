# 文献检索工作流

轻量流程：用户想**在库里找文献**（不涉及精读或问答）。

**所有 Python 命令用 `$PYTHON`（来自 pf_bootstrap 的 `python_candidate`），vault 路径用 `$VAULT`。**

---

## Stage 状态机

你必须明确知道当前在哪个 stage。每完成一个 stage 问自己："下一步是什么？" 不要在 stage 之间来回跳跃。

| Stage | 你在干什么                       | 完成后做什么                         |
| ----- | -------------------------------- | ------------------------------------ |
| S1    | 理解用户要找什么（domain/关键词） | 进入 S2                              |
| S2    | 执行搜索（paper_resolver 或 JSON） | 进入 S3                              |
| S3    | 展示候选清单给用户               | 等用户选择                           |
| S4    | 用户选了文献，决定下一步路由     | 进入对应 reference 流程，不再回来   |
| S5    | 写作辅助：读完文献后整合输出     | 结束                                 |

**不要做的事**：
- 不要在 S2 阶段去读论文全文
- 不要在 S3 阶段自作主张替用户选文献
- 不要在找不到结果时硬猜文件路径

---

## 触发场景

- "找一下骨科里面关于骨再生的文献"
- "查一下 TGF-beta 相关的文章"
- "库里有没有讲支架材料的"
- "这个 collection 有哪些文献"
- "搜一下 Smith 2024 的文章"

## 流程

### Step 1: 获取路径

已经由 pf_bootstrap 完成。直接用 `paths` JSON 里的 `index_path` 和 `literature_dir`。

### Step 2: 解析用户意图

从用户输入提取：
- **domain**（如果有）：`骨科`、`运动医学` 等 → 对应 `literature_dir` 子目录
- **关键词**：标题、作者、年份、期刊、主题词
- **collection 路径**：Zotero 子分类，如 `电刺激软骨修复综述`

### Step 3: 搜索

**优先：Python paper_resolver**（确定性匹配）

```
$PYTHON -m paperforge.worker.paper_resolver search --title "关键词" --author "Smith" --year 2024 --domain "骨科" --vault "$VAULT"
```

**Fallback：读 formal-library.json**

Agent 直接读 `index_path`，在 JSON 中筛选：
-`domain` 匹配
- `title`/`first_author`/`journal` 包含关键词

### Step 4: 返回结果

列出候选清单，每篇显示：

```
找到 N 篇匹配：

[1] ABC12345 — TGF-beta in Bone Regeneration (Smith, 2024, 骨科, OCR: done)
[2] DEF67890 — Bone Healing Mechanisms (Jones, 2023, 骨科, OCR: done)
```

关键字段：key, title, first_author, year, domain, ocr_status

### Step 5: 用户选择后续操作

> 请选择要操作的文献编号，或输入"refine"缩小范围。

选中文献后，按用户意图自动进入对应路由：
- `精读这篇` → 进入 [deep-reading.md](deep-reading.md) 流程
- `这篇讲了什么` → 进入 [paper-qa.md](paper-qa.md) 流程
- 不需要继续 → 结束

### Step 6: 写作辅助场景

如果用户原始意图包含**写作/优化/参考文献/综述/引用**等，搜索结果不是终点：

1. 提示用户圈选最相关的 3-5 篇
2. 对每篇进入 [deep-reading.md](deep-reading.md) 或至少通读 formal note + fulltext 关键段落
3. 读完所有选定论文后，Agent 整合知识辅助写作

> 示例："我从库里 X 篇文献中提取了以下关键发现……要不要基于这些帮你写 XX 部分？"

## 注意事项

- 如果是大型 library（>500 篇），优先用 paper_resolver 而不是全量读 JSON
- OCR status 为 `done` 的论文可以读 fulltext 内容
- OCR status 为 `pending` 的只有 formal note frontmatter
