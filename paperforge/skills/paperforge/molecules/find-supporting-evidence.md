# find-supporting-evidence

为特定论点或问题查找文献中的证据支持。

---

## Pre-flight Checklist

进入此 molecule 前，确认以下检查已完成：

- [ ] SKILL.md Section 1a Pre-flight 全部通过
- [ ] `$VAULT`、`$PYTHON`、`$LIT_DIR` 已从 bootstrap 获取
- [ ] `capabilities` 已读取（关键：`rg`、`semantic_enabled`、`semantic_ready`）
- [ ] `atoms/retrieval-routing.md` 已就绪（提供检索梯级选择）
- [ ] intent 已确定为 `find_supporting_evidence`

---

## 步骤

### Step 1: 解析用户证据需求

提取以下信息（缺什么就问用户）：
- **论点/问题**：用户需要支持的具体主张或疑问
- **范围限制**：是否限定特定 domain、作者、年份
- **证据类型**：统计结果、方法引用、临床发现、机制解释等

**先调用 query-plan：**

```bash
$PYTHON -m paperforge --vault "$VAULT" query-plan "<user_query>" --intent content --json
```

如果 `query-plan` 推荐 `retrieve`，直接从 `retrieve` 开始，不要先走一遍 paper discovery。

### Step 2: 检索梯级选择（`atoms/retrieval-routing.md`）

**先检查 `retrieve` 是否可用：**

```bash
$PYTHON -m paperforge --vault "$VAULT" embed status --json
```

仅当 `data.db_exists == true && data.chunk_count > 0` 时 `retrieve` 可用。

根据运行时状态，从以下路径中选择：

1. **Ladder B1**（首选，当 `retrieve` 可用）-- 语义全文快速定位
   - 直接调 `paperforge retrieve <query> --json --limit 30` 获取语义匹配的全文块
   - `retrieve` 返回的 chunks 已包含 `section`、`page_number`、`chunk_text`、`paper_id`
   - 按论文分组组织结果 → 直接进入 Step 3 展示
   - 如需精确定位验证，再用 `rg` / `grep` 在论文全文中确认

2. **Ladder B2**（备选，无 `retrieve` 但有 `rg`）-- 元数据→全文 grep
   - 默认不要静默降级到 metadata search
   - 先根据 query-plan 返回向用户解释：retrieve 不可用 / 0 结果，需要选择 fallback 模式
   - 如果用户同意 metadata 缩一轮，再用 `paperforge search` 生成候选集
   - 用 `runtime-health` 或 `paper-context` 筛选有 OCR/全文的论文
   - 在解析后的全文中运行 `rg` 定位匹配片段

3. **Ladder C**（回退）-- 无 `rg` 时用 `grep`/`findstr`
   - 同上流程但用系统搜索工具代替 rg

4. **Ladder D**（补充）-- 当 Ladder B1 命中太少时，用 `search` 做元数据补充
   - 取 `retrieve` 结果 + `search` 结果的并集
   - 去重后展示更完整的证据列表

5. **元数据降级** -- 当没有任何论文有 OCR/全文时，只出候选论文列表，不做片段验证

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
