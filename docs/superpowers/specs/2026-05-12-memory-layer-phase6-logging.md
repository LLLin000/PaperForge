# Memory Layer Phase 6+ — Reading Events, Logs, Vector Retrieval

> **Date:** 2026-05-12 | **Depends on:** Memory Layer Phase 1-5

## Feature 1: paper_events — Reading Log Backend

### Schema

```sql
CREATE TABLE IF NOT EXISTS paper_events (
    event_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id     TEXT NOT NULL,
    event_type   TEXT NOT NULL,        -- 'reading_note', 'ocr_done', 'sync_updated', 'deep_done'
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    payload_json TEXT,                 -- flexible per event_type
    FOREIGN KEY (paper_id) REFERENCES papers(zotero_key)
);
```

### reading_note payload

```json
{
    "excerpt": "the fundamental disjunction between materials science and biology",
    "section": "Section 7-8",
    "page": "P29",
    "usage": "F 段核心论点",
    "note": "与 DDGMQ7RW 独立诊断同一问题"
}
```

### Integration

Agent 在 `/pf-deep` 精读完一个段落后自动调用：
```
paper_events INSERT (paper_id, 'reading_note', payload_json)
```

或通过 CLI：
```bash
paperforge reading-log --write LQZ2FWIW \
    --section "Discussion P12" \
    --excerpt "magnetoelectric 被定位为压电的增强/补偿" \
    --usage "F 段 Liang 定位"
```

---

## Feature 2: reading-log / working-log — Export & Slash Commands

### reading-log export

```bash
paperforge reading-log --output Project/<name>/reading-log.md [--since DATE]
```

按 `created_at DESC` 导出所有 `reading_note` events，格式：

```markdown
## 2026-05-12

### LQZ2FWIW — Alvarez-Lorenzo et al. 2023
- **Discussion P12**："magnetoelectric 被定位为压电的增强/补偿"
  → 用途: F 段 Liang 定位的文献支撑
```

### Slash command: `/pf-log-reading`

嵌入式 prompt（在 agent skill 或 slash command 定义中）：

```
读完当前段落或章节后，记录以下信息到 paper_events:
- 来源: zotero_key + section + page
- 信息内容: 原文关键句（逐字引用）
- 用途: 这个信息支持当前写作的哪个论点
- 备注: 任何交叉验证/矛盾/注意事项

执行: paperforge reading-log --write KEY --section "..." --excerpt "..." --usage "..."
```

### Slash command: `/pf-log-session`

```
会话结束前回顾本次所有决策节点，按以下格式追加到 Project/<name>/working-log.md:

## <日期> — <小节名>

### 核心决策
- 做了什么、为什么

### 弯路与修正
- 错误方向 → 用户纠正 → 最终方案

### 可复用方法论
- 本段的 pattern 是什么

### 待办
- [ ] ...

格式参考: Project/综述写作/working-log.md
```

---

## Feature 3: Vector Retrieval (Deferred)

| 特性 | 方案 |
|------|------|
| 模型 | 本地 `all-MiniLM-L6-v2`（80MB，CPU 可跑） |
| API 备选 | OpenAI `text-embedding-3-small` |
| 向量库 | ChromaDB |
| 构建 | `paperforge embed build` |
| 增量 | `refresh_paper()` 自动 re-embed |
| 检索 | `paperforge retrieve <query> --json` |

### Command output

```json
{
  "chunks": [
    {
      "zotero_key": "ABC123",
      "title": "...",
      "page": 6,
      "section_title": "Results",
      "chunk_text": "At 24h post-stimulation, chondrocyte proliferation...",
      "score": 0.92
    }
  ]
}
```

Agent 流程不变：retrieve → 候选段落（带论文身份） → paper-status → 读 fulltext 验证。

---

## Implementation Order

1. paper_events table + reading-log write/export
2. `/pf-log-reading` + `/pf-log-session` slash commands
3. Working-log template (embedded in slash command prompt)
4. Vector retrieval (deferred, start when library > 500)
