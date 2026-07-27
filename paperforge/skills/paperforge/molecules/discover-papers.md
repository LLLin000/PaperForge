# discover-papers

从文献库中发现和检索论文，返回候选清单。

> 这个 molecule 只编排工作流。**检索决策由 `atoms/retrieval-routing.md` 决定。**

---

## Pre-flight Checklist

- [ ] SKILL.md Section 1a Pre-flight 全部通过
- [ ] `$VAULT`、`$PYTHON` 已从 bootstrap 获取
- [ ] intent 已确定为 `discover_papers`

---

## 步骤

### Step 1: 解析搜索意图 + 调用 planner

提取用户搜索意图中的要素（缺什么就问用户）：
- **搜索词**：关键词、作者名、年份
- **范围**：domain（如"骨科"）、不指定 = 全库
- **过滤**：年份范围、OCR 状态

```bash
$PYTHON -m paperforge --vault "$VAULT" \
  query-plan "<user_query>" \
  --intent discover --json
```

打开 `atoms/retrieval-routing.md`，按 **Planner Protocol**（§2）和 **Safe Executor**（§3）执行 `data.primary`。

通常 primary 是 `search`。search 已直接返回 `fulltext_available`、`body_units_count`、`ocr_status`——不需要额外调用 paper-context 做 enrichment。

### Step 2: Zero-results 处理

如果 primary 返回 `data.matches` 为空：

1. 检查 `data.fallback`——如果不为 null 且 scope=library → 执行一次 fallback
2. fallback 通常为 `retrieve`（当有向量索引时）
3. fallback 后不再二次 fallback

如果 fallback 也为空 → 告知用户"未找到匹配"，建议更换关键词。

### Step 3: 按 zotero_key 去重

如果 primary 和 fallback 都产生了结果，按 `zotero_key` 去重，保留 primary 来源的条目。

### Step 4: 展示候选清单

**primary 来自 search 时：**

```
找到 N 篇匹配 "<query>"：

[1] ABC12345 | Smith 2024 | 论文标题
    Fulltext: available | OCR: done
[2] DEF67890 | Jones 2023 | 论文标题
    Fulltext: false | OCR: pending
```

每项展示：`zotero_key`、`first_author`、`year`、`title`、`domain`、`fulltext_available`、`ocr_status`。

**fallback 来自 retrieve 时**（retrieve 输出不保证包含 title/author/year）：

```
正文检索结果：

[1] ABC12345 | Methods | score: 0.85
    "75 Hz bipolar stimulation was applied..."
[2] DEF67890 | Results | score: 0.72
    "frequency of 75 Hz showed significant effect..."
```

按 `zotero_key` 聚合，只展示命中章节、片段和 score。不虚构 title/author/year。
用户选中某篇后，由 `read-known-paper` 获取完整 metadata。

**来源标注**：如果结果来自 fallback，明确标注"来自正文语义检索"。
**不写"已验证证据"**——discover 只返回候选论文。

不要对前十篇全部调用 paper-context。search 已返回足够的状态信息。
只有用户选中某篇后，才进入 `read-known-paper` 并调用 paper-context。
### Step 5: 等待用户选择

展示后不要自己决定下一步。等用户说：

- "读一下 [1]" → `read-known-paper.md`
- "精读 [2]" → `deep-analyze-paper.md`
- "换个关键词" → 回到 Step 1
- "不找了" → 结束

---

## 过渡路由

| 用户动作 | 路由目标 |
|---------|---------|
| 用户选了一篇论文 | `read-known-paper.md` |
| 用户想重新搜索、缩小范围 | 返回 Step 1（refine） |
| 用户想精读 | `deep-analyze-paper.md` |

---

## 禁止

- 不要在搜索结果中替用户决定读哪篇
- 不要在搜索阶段读全文
- 不要对零结果硬猜路径
- 不要主动并行 `search + retrieve`——只走 primary → fallback 顺序
