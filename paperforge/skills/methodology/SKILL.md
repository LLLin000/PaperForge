---
name: methodology
description: >
  Extract reusable methodology from project work logs. Triggered by:
  methodology, /methodology, 提取方法论, 存档写作规律,
  总结本项目方法, 提取可复用规则, 提取写作规律.
source: paperforge
---

# Methodology Extract

---

## 1. Bootstrap

```python $SKILL_DIR/scripts/pf_bootstrap.py```

Remember: `$VAULT`, `$PYTHON`.

---

## 2. Determine Project

Ask user: which project to extract methodology from?

If user doesn't specify, scan `Project/` directory for complete working-log.md files and list them.

---

## 3. Read working-log

Read `<vault>/Project/<project>/working-log.md`.

---

## 4. Identify Extractable Patterns

Scan the working-log for these signals:

| Signal in working-log | Extract to |
|----------------------|-------------|
| "弯路" + "修正" or "教训" sections | Pattern rules |
| "最终逻辑:" or "最终结构:" | Section templates |
| "复用" keyword + methodology block | Reusable practices |
| Cross-study audit sections (跨研究可比性) | Analysis methodology |
| "methodology" header sections | Full methodology block |
| Review feedback patterns (审阅/修正) | Writing checklists |

For each found pattern, classify into one of:
- `review-writing` — 综述写作 framework design, gap analysis, cross-study audit
- `argument-writing` — 段落写作, 参数框架, 论证结构
- `analysis-methods` — 文献审计, 跨研究比较, 参数提取
- `general` — fallback

---

## 5. Present and Confirm

For each extracted pattern, show:
- Category
- Source (working-log section number)
- Brief summary (1-2 sentences)

Ask user to confirm/edit before writing.

---

## 6. Write Methodology Files

Write confirmed patterns to `<system_dir>/PaperForge/methodologies/<category>.md`.

If file exists, APPEND (do not overwrite).

Format per method:
```
## <Method Name>
**Category:** <category>
**Source:** Project/<project>/working-log.md Section X.Y
**Extracted:** YYYY-MM-DD

### Pattern
<reusable methodology>

### Example
<concrete example from project>
```
