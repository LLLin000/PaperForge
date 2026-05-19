# find-supporting-evidence

为特定论点或问题查找文献中的证据支持。

---

## 前置条件

- bootstrap 已完成（有 `$VAULT`、`$PYTHON`、`$LIT_DIR`）
- `atoms/retrieval-routing.md` 已就绪（提供检索梯级选择）

---

## 步骤

### Step 1: 解析用户证据需求

提取以下信息（缺什么就问用户）：
- **论点/问题**：用户需要支持的具体主张或疑问
- **范围限制**：是否限定特定 domain、作者、年份
- **证据类型**：统计结果、方法引用、临床发现、机制解释等

### Step 2: 检索梯级选择（`atoms/retrieval-routing.md`）

根据运行时状态选择合适的梯级：

1. **Ladder B**（优先）-- 用 `rg` 在全文中定位精确证据
   - 先用 `paperforge search` 生成元数据候选集
   - 用 `runtime-health` 或 `paper-context` 筛选有 OCR/全文的论文
   - 在解析后的全文中运行 `rg` 定位匹配片段
2. **Ladder C**（回退）-- 无 `rg` 时用 `grep`/`findstr`
3. **Ladder D**（补充）-- 语义候选扩展（仅当 `semantic_enabled && semantic_ready`）
4. **元数据降级** -- 当没有任何论文有 OCR/全文时，只出候选论文列表，不做片段验证

### Step 3: 展示分组证据命中（grouped evidence hits with snippets）

格式：

```
找到 N 条与 "<论点>" 相关的证据：

=== Smith 2024 (zotero_key: ABC12345) ===
[1] 第 5 页 · 方法部分
    匹配片段："...we used a randomized controlled trial..."
    上下文：在讨论实验设计时作者描述了...

=== Jones 2023 (zotero_key: DEF67890) ===
[2] 第 12 页 · 讨论部分
    匹配片段："...our findings align with previous meta-analyses..."
    上下文：作者比较本研究与已有综述的一致性...

（共 N 条，来自 M 篇论文）
```

每项包含：
- 论文标识（`zotero_key`、标题）
- 章节或页码引用
- 匹配片段
- 简短上下文

### Step 4: 等用户选择后续操作

- "看 [1] 的详情" → 路由到 `read-known-paper.md`
- "保存 [1]" / "记录这条证据" → 路由到 `capture-project-knowledge.md`
- "换个关键词" → 回到 Step 1
- "够了" → 结束

---

## 过渡路由

| 用户动作 | 路由目标 |
|---------|---------|
| 用户想查看论文详情 | `read-known-paper.md` |
| 用户想保存证据到项目知识 | `capture-project-knowledge.md` |
| 用户想重新搜索 | 回到 Step 1 |

---

## 元数据降级

当 `runtime-health` 显示没有任何论文有 OCR 或全文可用时：

> 精确证据验证受限 -- 降级到元数据级支持

仅输出候选论文列表（不含片段验证），告知用户当前无法做全文级证据检索。

---

## 禁止

- 不要在没有 OCR/全文的情况下虚构引用位置或片段
- 不要在没有 `rg`/`grep` 验证的情况下把语义检索结果当最终证据
- 不要在用户未要求时自动保存证据
