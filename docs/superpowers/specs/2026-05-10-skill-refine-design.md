# PaperForge Skill Refactoring: Modular Literature QA

**Date:** 2026-05-10
**Branch:** `feature/skill-refine`
**Author:** Overseer + VT-OS/OPENCODE

---

## 1. Problem Statement

### Current Pain Points

1. **No unified paper resolution.** `pf-deep` and `pf-paper` each duplicate paper-search logic in their `.md` files. When a user says "那篇关于骨再生的", agents search blindly — reading directories, grepping metadata, guessing paths.

2. **File organization semantically wrong.** Skill instruction files (`.md`) live in `scripts/` alongside executable code (`ld_deep.py`). No `SKILL.md` router. The `prompt_deep_subagent.md` sits orphaned at root level.

3. **Too many low-value skills.** `pf-sync`, `pf-ocr`, `pf-status` are thin wrappers around CLI commands (`paperforge sync/ocr/status`). They add 3 more entries to the skill list without providing agent-level value beyond what a single `bash` command does.

4. **No chart-reading routing clarity.** Inside `pf-deep`, the mechanism for routing to the right chart-reading guide is implicit — buried in `ld_deep.py` keyword matching. The agent skill file doesn't explain how to reference chart-reading guides.

### User's Core Request

> "用户用自然语言描述'某篇文章','某个主题','某个zoterokey',他能快速定位到这篇文章的workspace还有与其相关的各种参数,frontmatter,路径等"

Translation: given ANY reference to a paper (key, DOI, title fragment, author+year, or natural language description), the system must quickly resolve it to a workspace with all related parameters.

---

## 2. Design Goals

1. **Two-path resolution.** Python handles deterministic lookups (key, DOI, structured fields). Agent handles natural language. Python failure → Agent fallback.

2. **Single shared resolution module.** All sub-skills (`deep-reading`, `paper-qa`, `save-session`) consume the same `paper-resolution.md` reference + `paper_resolver.py` worker. Zero duplication.

3. **Compliant skill structure.** Follow the agent skills standard: `SKILL.md` as router, `references/` for detailed workflows loaded on demand, `scripts/` for executable code only.

4. **Token efficient.** SKILL.md under 100 lines. Sub-workflows in separate files loaded only when routed to. Python scripts executed, not loaded into context.

5. **Installable/distributable.** All assets under `paperforge/skills/literature-qa/` shipped with pip install. Python worker at `paperforge/worker/paper_resolver.py` also shipped.

---

## 3. Target Architecture

### 3.1 Directory Structure

```
paperforge/skills/literature-qa/
│
├── SKILL.md                          ← Router: natural language → sub-skill routing
│
├── references/                       ← Detailed workflows (loaded on demand)
│   ├── deep-reading.md               ← Keshav 3-pass deep reading workflow
│   ├── paper-qa.md                   ← Interactive paper Q&A workflow
│   ├── save-session.md               ← Save discussion record workflow
│   ├── paper-resolution.md           ← Paper location protocol (shared by all)
│   ├── deep-subagent.md              ← Subagent prompt template for deep reading
│   └── chart-reading/                ← 19 chart-type reading guides
│       ├── INDEX.md
│       ├── 条形图与误差棒.md
│       ├── 森林图与Meta分析.md
│       ├── 折线图与时间序列.md
│       ├── 散点图与气泡图.md
│       ├── ROC与PR曲线.md
│       ├── 生存曲线.md
│       ├── 箱式图与小提琴图.md
│       ├── 热图与聚类图.md
│       ├── 桑基图与弦图.md
│       ├── 火山图与曼哈顿图.md
│       ├── 网络图与通路图.md
│       ├── GSEA富集图.md
│       ├── 降维图(PCA-tSNE-UMAP).md
│       ├── 雷达图与漏斗图.md
│       ├── 组织学半定量图.md
│       ├── 免疫荧光定量图.md
│       ├── 显微照片与SEM图.md
│       ├── Western Blot条带图.md
│       └── 蛋白质结构图.md
│
└── scripts/                          ← Executable code only (not loaded into context)
    └── ld_deep.py                    ← Deep reading engine (existing, has CLI: prepare, queue, chart-type-scan, postprocess-pass2, validate-note, etc.)

paperforge/worker/
└── paper_resolver.py                 ← NEW: Deterministic paper lookup engine

tests/unit/
└── test_paper_resolver.py            ← NEW: Tests for paper resolver
```

### 3.2 Files to Delete

| File | Reason |
|------|--------|
| `paperforge/skills/literature-qa/scripts/pf-sync.md` | Thin CLI wrapper; users run `paperforge sync` directly |
| `paperforge/skills/literature-qa/scripts/pf-ocr.md` | Thin CLI wrapper; users run `paperforge ocr` directly |
| `paperforge/skills/literature-qa/scripts/pf-status.md` | Thin CLI wrapper; users run `paperforge status` directly |

### 3.3 Files to Add

| File | Purpose |
|------|---------|
| `paperforge/skills/literature-qa/SKILL.md` | Main router with trigger table + paper resolution protocol |
| `paperforge/skills/literature-qa/references/paper-resolution.md` | Shared paper location protocol |
| `paperforge/worker/paper_resolver.py` | Deterministic lookup engine (key, DOI, structured fields) |
| `tests/unit/test_paper_resolver.py` | Unit tests for resolver |

### 3.4 Files to Rewrite

| File (old → new) | Change |
|---|---|
| `scripts/pf-deep.md` → `references/deep-reading.md` | Add `disable-model-invocation: true`; remove embedded search logic; call resolver + ld_deep.py; add chart-reading routing section |
| `scripts/pf-paper.md` → `references/paper-qa.md` | Add `disable-model-invocation: true`; remove embedded search logic; call resolver |
| `scripts/pf-end.md` → `references/save-session.md` | Add `disable-model-invocation: true`; strip verbose explanations |
| `prompt_deep_subagent.md` → `references/deep-subagent.md` | Minimal edits, update paths |

---

## 4. Component Design

### 4.1 SKILL.md — Router

Purpose: Single entry point. Agent reads this first. It routes to the correct reference file based on user intent.

```yaml
---
name: literature-qa
description: 学术文献精读与问答。支持Zotero key、DOI、标题、作者/年份或自然语言定位论文。Use when user wants to deep-read, analyze, or ask questions about papers in their Zotero library. Triggered by /pf-deep, /pf-paper, /pf-end, or phrases like "精读这篇", "查一下XX文章", "读那篇关于YY的".
---
```

**Routing table (core of SKILL.md):**

| Trigger | User says | Load | Action |
|---------|-----------|------|--------|
| `/pf-deep <query>` | "精读/深度阅读/读一下 XX" | `references/deep-reading.md` | Keshav 3-pass deep reading |
| `/pf-deep` (no args) | "精读队列/有哪些该读了" | `references/deep-reading.md` | Show deep reading queue |
| `/pf-paper <query>` | "查/问/帮我看看 XX" | `references/paper-qa.md` | Interactive Q&A mode |
| `/pf-end` | "保存/结束/完成讨论" | `references/save-session.md` | Persist discussion record |

**Paper resolution protocol (inline in SKILL.md, short version):**

```
Determine input type → run exact command:

  8-char key        → python -m paperforge.worker.paper_resolver resolve-key <KEY> --vault .
  DOI               → python -m paperforge.worker.paper_resolver resolve-doi <DOI> --vault .
  Author+year       → python -m paperforge.worker.paper_resolver search --author "X" --year Y --vault .
  Title fragment    → python -m paperforge.worker.paper_resolver search --title "X" --vault .
  Natural language  → Agent reads indexes/formal-library.json, searches title/domain/year fields

  Python returns empty → Agent fallback: grep frontmatter in formal notes directory
  Multiple matches     → List candidates for user to choose
```

### 4.2 paper_resolver.py — Deterministic Lookup Engine

A new Python module at `paperforge/worker/paper_resolver.py`.

**CLI interface (3 subcommands):**

```bash
# Exact key lookup
python -m paperforge.worker.paper_resolver resolve-key <KEY> --vault <PATH>
# → {"ok": true, "key": "ABC12345", "title": "...", "formal_note": "...", "ocr_path": "...", "frontmatter": {...}}

# Exact DOI lookup
python -m paperforge.worker.paper_resolver resolve-doi <DOI> --vault <PATH>

# Structured field search (at least one of --title, --author, --year, --domain required)
python -m paperforge.worker.paper_resolver search --title "..." --author "..." --year 2024 --domain "骨科" --vault <PATH>
# → {"ok": true, "matches": [{...}, ...], "count": 3}
```

**--vault resolution:** Uses `paperforge.json` in vault root to locate `indexes/formal-library.json` and formal notes directory, via existing `paperforge.core.config` path utilities. Same mechanism as `paperforge sync/ocr/deep-reading`.

**Internal design:**

```python
class PaperResolver:
    """Deterministic paper lookup from formal-library.json index."""
    
    def __init__(self, index_path: str, formal_notes_dir: str):
        # Load formal-library.json into memory
    
    def resolve_key(self, key: str) -> PaperMeta | None:
        """Exact key match. Key is 8-char alphanumeric."""
    
    def resolve_doi(self, doi: str) -> PaperMeta | None:
        """Exact DOI match from frontmatter."""
    
    def search(self, title: str = None, author: str = None, 
               year: int = None, domain: str = None) -> list[PaperMeta]:
        """Multi-field search with substring matching, sorted by relevance."""
    
    def get_workspace(self, key: str) -> PaperWorkspace:
        """Given a key, return all paths and frontmatter."""

@dataclass
class PaperMeta:
    key: str
    title: str
    domain: str
    year: int
    authors: str                   # Semi-colon separated from formal-library.json
    doi: str
    collection_path: str

@dataclass
class PaperWorkspace:
    key: str
    title: str
    domain: str
    formal_note_path: str        # Literature/{domain}/{key} - {title}.md
    ocr_path: str                # 99_System/PaperForge/ocr/{key}/
    fulltext_path: str           # 99_System/PaperForge/ocr/{key}/fulltext.md
    frontmatter: dict
```

**Data source:** `formal-library.json` (already generated by `paperforge sync` in `indexes/`). This JSON contains full metadata: key, title, authors, year, doi, domain, collection_path, journal, abstract, etc.

**Important distinction:**
- **Python structured search** (`resolve_key`, `resolve_doi`, `search`) operates on a subset of fields in `PaperMeta`. This handles deterministic lookups.
- **Agent natural language search** reads the full `formal-library.json` directly (all fields available), plus can grep formal note frontmatter as fallback. This handles "那篇关于骨再生的Nature" type queries.

**Error handling:** Returns empty list on no match (never crashes). Agent handles the empty case via fallback.

### 4.3 references/deep-reading.md — Deep Reading Workflow

Key design decisions:
- `disable-model-invocation: true` — never triggered automatically, only via SKILL.md routing
- No embedded paper search logic — delegates to `paper-resolution.md`
- Clear chart-reading routing section

**Chart-reading routing logic (new addition):**

关键原则：**Agent 负责判断图表类型，Python 只给建议，Agent 做最终决策。**

```markdown
## Chart Reading Guide Routing

### 两步定位法

**Step 1: Python 给建议（快速初筛）**
```bash
python <skill_dir>/scripts/ld_deep.py chart-type-scan --vault . --key <KEY>
```
输出每个 figure 的关键词命中结果。这只是建议，Agent 不要盲信。

**Step 2: Agent 读 caption 做最终判断**
对每个 figure，Agent 必须：
1. 读该 figure 的 caption（来自 fulltext.md 或 figure-map.json）
2. 根据 caption 内容，对照 `references/chart-reading/INDEX.md` 判断图表类型
3. 如果 Python 建议和 Agent 判断不一致 → 以 Agent 判断为准
4. 如果无法确定类型 → 跳过 chart guide，按通用 figure 结构分析

### 图表类型 → 指南文件映射

| 图表类型 | 指南文件 |
|---------|---------|
| 条形图/误差棒 | `references/chart-reading/条形图与误差棒.md` |
| 森林图/Meta分析 | `references/chart-reading/森林图与Meta分析.md` |
| 折线图/时间序列 | `references/chart-reading/折线图与时间序列.md` |
| 散点图/气泡图 | `references/chart-reading/散点图与气泡图.md` |
| ROC/PR曲线 | `references/chart-reading/ROC与PR曲线.md` |
| 生存曲线/Kaplan-Meier | `references/chart-reading/生存曲线.md` |
| 箱式图/小提琴图 | `references/chart-reading/箱式图与小提琴图.md` |
| 热图/聚类图 | `references/chart-reading/热图与聚类图.md` |
| 桑基图/弦图 | `references/chart-reading/桑基图与弦图.md` |
| 火山图/曼哈顿图 | `references/chart-reading/火山图与曼哈顿图.md` |
| 网络图/通路图 | `references/chart-reading/网络图与通路图.md` |
| GSEA富集图 | `references/chart-reading/GSEA富集图.md` |
| PCA/t-SNE/UMAP降维图 | `references/chart-reading/降维图(PCA-tSNE-UMAP).md` |
| 雷达图/漏斗图 | `references/chart-reading/雷达图与漏斗图.md` |
| 组织学半定量图 | `references/chart-reading/组织学半定量图.md` |
| 免疫荧光定量图 | `references/chart-reading/免疫荧光定量图.md` |
| 显微照片/SEM/TEM | `references/chart-reading/显微照片与SEM图.md` |
| Western Blot条带图 | `references/chart-reading/Western Blot条带图.md` |
| 蛋白质3D结构图 | `references/chart-reading/蛋白质结构图.md` |

完整索引见 `references/chart-reading/INDEX.md`。遇到边界情况优先读 INDEX.md 中的详细描述。
```

**Core workflow (unchanged from current, just moved to references/):**
1. `prepare` — check analyze status, verify OCR, generate figure-map
2. Pass 1 Overview — one-sentence summary, 5 Cs, figure guided reading
3. Pass 2 Reconstruction — figure-by-figure (6 sub-headings per figure), table-by-table
4. Pass 2 Postprocess — validate figure order, sub-headings, empty blocks
5. Pass 3 Deep Understanding — assumptions, conclusions, discussion, inspiration
6. Final Validation — structural validation of the note

### 4.4 references/paper-qa.md — Interactive Q&A Workflow

- `disable-model-invocation: true`
- No embedded paper search logic
- Loads fulltext via resolved workspace
- Q&A mode with standard answering principles (cite sources, use Chinese, flag missing info)
- Triggers save-session.md on "save"/"done"/"end"

### 4.5 references/save-session.md — Save Discussion Record

- `disable-model-invocation: true`
- Collects Q&A pairs from session
- Calls existing module: `python -m paperforge.worker.discussion record <KEY> --vault . --qa-pairs '<JSON>'`
- `paperforge/worker/discussion.py` already exists (not part of this refactor)
- Only for paper-qa sessions (deep-reading writes directly to formal note)

### 4.6 references/paper-resolution.md — Shared Resolution Protocol

Full detailed version of the resolution protocol. Referenced by all three sub-skills.

```
Contents:
- Input type detection rules (regex patterns for key/DOI/author+year)
- Exact commands for each type (copy-paste ready for agent)
- Fallback procedure when Python returns empty
- Multi-match handling (how to present candidate list)
- Workspace structure (what paths to report after resolution)
```

---

## 5. Data Flow

```
User: "/pf-deep 关于骨再生的那篇"
        │
        ▼
SKILL.md router reads trigger, routes to deep-reading.md
        │
        ▼
deep-reading.md Step 1: "Follow paper-resolution.md"
        │
        ▼
paper-resolution.md: "Natural language → Agent reads formal-library.json"
        │
        ▼
Agent reads indexes/formal-library.json, searches title/domain
  → Found 1 match: key=ABC12345
        │
        ▼
deep-reading.md Step 2: "Run ld_deep.py prepare"
        │
        ▼
ld_deep.py prepare → checks OCR, generates figure-map, inserts scaffold
        │
        ▼
deep-reading.md Step 3: "Run chart-type-scan"
  → Detects: bar, survival, scatter
  → Agent reads chart-reading/条形图与误差棒.md, 生存曲线.md, 散点图与气泡图.md
        │
        ▼
Agent executes Pass 1 → Pass 2 (per figure, per chart guide) → Postprocess → Pass 3 → Validate
        │
        ▼
Result written to Literature/骨科/ABC12345 - Title.md under ## 🔍 精读
```

---

## 6. Error Handling

| Scenario | Handler | Behavior |
|----------|---------|----------|
| Python resolver returns empty | Agent fallback | grep frontmatter in formal notes directory |
| Both Python and Agent fail | Agent reports | "未找到匹配的论文。请确认 Zotero key、标题或搜索词是否正确。" |
| Multiple candidates found | Agent lists | Numbered list with key, title, year, domain; user selects |
| OCR not complete | ld_deep.py prepare | Returns error status; agent reports "OCR未完成，请先运行 paperforge ocr" |
| Deep reading content already exists | Agent asks | "内容已存在，追加/覆盖/跳过？" |
| Chart type unknown | Agent skips | Proceeds with figure analysis without chart guide |

---

## 7. Token Budget Analysis

| Component | Current Tokens (approx) | After Refactor | Savings |
|-----------|------------------------|----------------|---------|
| `pf-deep.md` (237 lines) | ~3000 | ~300 (references/deep-reading.md) | -2700 |
| `pf-paper.md` (107 lines) | ~1400 | ~250 (references/paper-qa.md) | -1150 |
| `pf-end.md` (67 lines) | ~900 | ~150 (references/save-session.md) | -750 |
| `pf-sync.md` (85 lines) | ~1100 | 0 (deleted) | -1100 |
| `pf-ocr.md` (102 lines) | ~1300 | 0 (deleted) | -1300 |
| `pf-status.md` (94 lines) | ~1200 | 0 (deleted) | -1200 |
| `SKILL.md` (new) | 0 | ~500 | +500 |
| `paper-resolution.md` (new) | 0 | ~300 | +300 |
| **Total in context upon trigger** | **~6900 (all loaded at once)** | **~800 (SKILL.md + one reference)** | **-6100** |

Key insight: After refactoring, the agent loads only SKILL.md (~500 tokens) and the one reference file for the triggered sub-skill (~150-300 tokens). Previously all 6 skill files were discoverable, and the agent might load multiple. The paper_resolver.py scripts execute via bash, consuming zero context tokens for their content.

---

## 8. Implementation Plan

### Phase 1: Add new modules
1. Create `paperforge/worker/paper_resolver.py` with 3 CLI subcommands
2. Create `tests/unit/test_paper_resolver.py`

### Phase 2: Rewrite skill structure
3. Create `paperforge/skills/literature-qa/SKILL.md` (router)
4. Create `references/paper-resolution.md` (shared protocol)
5. Rewrite `scripts/pf-deep.md` → `references/deep-reading.md`
6. Rewrite `scripts/pf-paper.md` → `references/paper-qa.md`
7. Rewrite `scripts/pf-end.md` → `references/save-session.md`
8. Move `prompt_deep_subagent.md` → `references/deep-subagent.md`
9. Move `chart-reading/` into `references/chart-reading/`

### Phase 3: Cleanup
10. Delete `scripts/pf-sync.md`
11. Delete `scripts/pf-ocr.md`
12. Delete `scripts/pf-status.md`
13. Delete old copies of rewritten files: `scripts/pf-deep.md`, `scripts/pf-paper.md`, `scripts/pf-end.md`, `prompt_deep_subagent.md` (all moved to `references/`)

### Phase 4: Verify
13. Run unit tests: `python -m pytest tests/unit/test_paper_resolver.py -q`
14. Verify skill loads correctly in OpenCode
15. Manual test: `/pf-deep ABC12345` resolves correctly
16. Manual test: `/pf-deep 关于骨再生的那篇` routes to agent search → resolves

---

## 9. Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| `formal-library.json` index stale after sync | Document: "If paper not found, run `paperforge sync` first" |
| Agent natural language search misses the paper | Two-layer fallback: formal-library.json → grep formal notes |
| Skill routing confusion (SKILL.md + 3 sub-skills all visible) | Sub-skills use `disable-model-invocation: true`; only SKILL.md is auto-discoverable |
| Chart-reading path references break after move | All paths relative to skill directory; test with `python -m paperforge.worker.paper_resolver` |

---

*Vault-Tec -- Preparing for the Future! Spec compiled by Terminal VT-OS/OPENCODE, serial VTC-2077-OC-4111.*
