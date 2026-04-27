# /pf-deep Skill Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor ld_deep.py into atoms/molecules pattern with deterministic skeleton rendering and postprocess validation, rewrite prompt_deep_subagent.md to ~150 directive lines.

**Architecture:** Single plan, 3 tasks (1) skeleton rendering with fixed sub-headings, (2) postprocess-pass2 molecule + CLI, (3) prompt rewrite. Tests in task 2.

**Tech Stack:** Python 3.10+, argparse, re

---

### Task 1: Skeleton Rendering with Fixed Sub-Headings

**Files:**
- Modify: `paperforge/skills/literature-qa/scripts/ld_deep.py:838-873` (`render_figure_block`)

- [ ] **Step 1: Understand current `render_figure_block`**

Current code at line 838-844:
```python
def render_figure_block(figure: FigureEntry) -> str:
    page_suffix = f"（第 {figure.page} 页）" if figure.page else ""
    lines = [
        f"> [!note]- Figure {figure.number}：{figure.title}",
        f"> ![[{figure.image_link}]]",
    ]
```

It only has heading + image embed. No internal structure. The AI has to create all content from scratch.

- [ ] **Step 2: Add fixed sub-headings inside figure callout block**

Update `render_figure_block` to include ALL sub-headings from the design spec:

```python
FIGURE_SUBHEADINGS = [
    "图像定位与核心问题",
    "方法与结果",
    "图表质量审查",
    "作者解释",
    "我的理解",
    "疑点 / 局限",
]

def render_figure_block(figure: FigureEntry) -> str:
    page_suffix = f"（第 {figure.page} 页）" if figure.page else ""
    lines = [
        f"> [!note]- Figure {figure.number}：{figure.title}",
        f"> ![[{figure.image_link}]]",
    ]
    # Add figure-level page indicator
    if figure.page:
        lines.append(f">")
        lines.append(f"> *（第 {figure.page} 页）*")
    # Add fixed sub-headings (AI fills content between them)
    for heading in FIGURE_SUBHEADINGS:
        lines.append(">")
        lines.append(f"> **{heading}**")
        lines.append("> ")
    return "\n".join(lines) + "\n\n"
```

- [ ] **Step 3: Verify skeleton output**

Run on a known test paper (e.g., the 骨科 test fixture):
```bash
python paperforge/skills/literature-qa/scripts/ld_deep.py prepare TESTKEY1 --vault "test_vault_path"
```
Expected: Each Figure N callout block contains all 6 sub-headings as unstyled bold text inside the `>` block.

- [ ] **Step 4: Also update `render_table_block` with standardized sub-headings**

Apply the same pattern to table blocks:
```python
TABLE_SUBHEADINGS = [
    "这张表在回答什么问题",
    "关键字段 / 分组",
    "主要结果",
    "我的理解",
    "在全文中的作用",
    "疑点 / 局限",
]
```

Update `render_table_block` at line 875-889 to use these, matching the current structure but with the same stylized format as figure blocks.

- [ ] **Step 5: Write unit test for `render_figure_block`**

Add to a new test file `tests/test_ld_deep_skel.py`:

```python
from paperforge.skills.literature_qa.scripts.ld_deep import (
    render_figure_block, FigureEntry, FIGURE_SUBHEADINGS,
)


def test_render_figure_block_has_all_subheadings():
    """Every figure callout block contains all 6 fixed sub-headings."""
    fig = FigureEntry(
        number=1, title="Test", image_id="fig1",
        image_link="path/img.png", page=3, caption="Test caption",
    )
    result = render_figure_block(fig)
    for heading in FIGURE_SUBHEADINGS:
        assert f"> **{heading}**" in result, f"Missing sub-heading: {heading}"
    assert f"> ![[path/img.png]]" in result
    assert "> [!note]- Figure 1：" in result
```

- [ ] **Step 6: Commit**

```bash
git add paperforge/skills/literature-qa/scripts/ld_deep.py tests/test_ld_deep_skel.py
git commit -m "feat: add fixed sub-headings to figure/table callout blocks in skeleton"
```

---

### Task 2: Postprocess-Pass2 Molecule

**Files:**
- Modify: `paperforge/skills/literature-qa/scripts/ld_deep.py` (new function + CLI command)

- [ ] **Step 1: Implement `postprocess_pass2()` function**

Add the function (and its helper regex patterns) to ld_deep.py. It reads a note path and returns a list of structured error dicts.

Signature:
```python
def postprocess_pass2(
    note_text: str,
    figure_count: int,
) -> list[dict]:
    """Validate Pass 2 figure blocks in a written deep-reading note.

    Args:
        note_text: Full text of the formal note after AI wrote Pass 2.
        figure_count: Expected number of figures from the skeleton.

    Returns:
        List of error dicts with keys: type, severity, figure, line, message.
    """
```

Logic:

**Check 1 — Order**: Scan lines for `> [!note]- Figure N:` patterns. Build ordered list of (figure_number, line_number). Verify sequence is strictly increasing. For each out-of-order figure:
```python
{"type": "order", "severity": "error", "figure": "3", "line": 42, "message": "Figure 3 appears before Figure 2 (line 42)"}
```

**Check 2 — Image bounds**: Find all `![[` occurrences. For each, check that the nearest preceding callout-start line is a `> [!note]-` block (the image is inside it). If the image is before any callout or after the last callout, flag it:
```python
{"type": "image_bounds", "severity": "error", "line": 85, "message": "Stray image at line 85: ![[ocr/KEY/images/fig_3.png]]"}
```

**Check 3 — Empty blocks**: For each `> [!note]- Figure N:` block, extract the content between it and the next `>` line starting a new callout. Check if any sub-heading is immediately followed by another sub-heading (no content between):
```python
{"type": "empty_block", "severity": "warning", "figure": "5", "line": 120, "message": "Figure 5: sub-heading '我的理解' has no content"}
```

**Check 4 — Missing sub-headings**: For each figure block, verify all 6 sub-headings from FIGURE_SUBHEADINGS are present as `> **{heading}**` lines:
```python
{"type": "missing_subheading", "severity": "error", "figure": "3", "line": 45, "message": "Figure 3: sub-heading '我的理解' not found"}
```

**Check 5 — Duplicates**: Check if any figure number appears in more than one callout heading:
```python
{"type": "duplicate", "severity": "error", "figure": "2", "line": 95, "message": "Figure 2 appears at lines 40 and 95"}
```

**Check 6 — Missing**: Check if any figure number from 1..N is absent from the note:
```python
{"type": "missing", "severity": "error", "figure": "4", "line": 0, "message": "Figure 4 is missing from the note"}
```

**Check 7 — Extra**: Detect figures in the note that exceed `figure_count` (AI added a figure not in the skeleton):
```python
{"type": "extra", "severity": "error", "figure": "5", "line": 142, "message": "Figure 5 not in skeleton (found at line 142)"}
```

- [ ] **Step 2: Add `postprocess-pass2` CLI command**

Add a new subparser to `main()`:
```python
pp_parser = subparsers.add_parser("postprocess-pass2", help="Validate Pass 2 figure blocks after AI writing")
pp_parser.add_argument("note", type=Path, help="Path to the formal note")
pp_parser.add_argument("--figures", type=int, required=True, help="Expected number of figures")
pp_parser.add_argument("--format", choices=["json", "text"], default="text", help="Output format")
```

Dispatch block:
```python
if args.command == "postprocess-pass2":
    note_text = args.note.read_text(encoding="utf-8")
    errors = postprocess_pass2(note_text, args.figures)
    if args.format == "json":
        print(json.dumps(errors, ensure_ascii=False, indent=2))
    else:
        if not errors:
            print("OK: Pass 2 structure is clean")
        else:
            print(f"Found {len(errors)} issues:")
            for e in errors:
                print(f"  [{e['severity']}] {e['message']}")
    return 1 if errors else 0
```

- [ ] **Step 3: Write tests**

Create test file `tests/test_ld_deep_postprocess.py`:

```python
import pytest
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from paperforge.skills.literature_qa.scripts.ld_deep import postprocess_pass2


def test_clean_note():
    """Well-formed note with correct figure order returns no errors."""
    note = _make_note_with_figures(3)  # helper: builds note with 3 figures in order
    errors = postprocess_pass2(note, figure_count=3)
    assert errors == []


def test_out_of_order():
    """Figures in wrong order detected."""
    note = _make_note_with_figures([1, 3, 2])  # explicit order
    errors = postprocess_pass2(note, figure_count=3)
    assert any(e["type"] == "order" for e in errors)


def test_stray_image():
    """Image outside callout block detected."""
    note = _make_note_with_figures(2) + "\n![[stray_image.png]]\n"
    errors = postprocess_pass2(note, figure_count=2)
    assert any(e["type"] == "image_bounds" for e in errors)


def test_empty_figure_block():
    """Figure callout with no content detected."""
    note = _make_empty_figure_block(2)  # only sub-headings, no content
    errors = postprocess_pass2(note, figure_count=2)
    assert any(e["type"] == "empty_block" for e in errors)


def test_missing_subheading():
    """Figure block missing a required sub-heading detected."""
    note = _make_note_missing_subheading(1, "我的理解")
    errors = postprocess_pass2(note, figure_count=1)
    assert any(e["type"] == "missing_subheading" for e in errors)


def test_duplicate_figure():
    """Same figure number appearing twice detected."""
    note = _make_note_with_duplicate_figure(2)
    errors = postprocess_pass2(note, figure_count=2)
    assert any(e["type"] == "duplicate" for e in errors)


def test_missing_figure():
    """Figure completely absent from note detected."""
    note = _make_note_with_figures([1, 2])
    errors = postprocess_pass2(note, figure_count=3)  # expects 3, only 2 present
    assert any(e["type"] == "missing" for e in errors)


def test_zero_figures():
    """Note with 0 figures produces no errors."""
    note = "# Test\nNo figures here.\n"
    errors = postprocess_pass2(note, figure_count=0)
    assert errors == []


def test_extra_figure():
    """Figure not in skeleton (exceeds figure_count) detected."""
    note = _make_note_with_figures(3)  # writes figures 1,2,3
    errors = postprocess_pass2(note, figure_count=2)  # skeleton only has 2
    assert any(e["type"] == "extra" for e in errors)
```

Helper function to build test notes (put before test functions):

```python
def _make_note_with_figures(count_or_order):
    """Build a note with figure blocks in given order."""
    if isinstance(count_or_order, int):
        order = list(range(1, count_or_order + 1))
    else:
        order = count_or_order
    parts = []
    for n in order:
        parts.append(
            f"\n> [!note]- Figure {n}: Test caption\n"
            f"> ![[fig_{n}.png]]\n"
            f">\n"
            f"> **图像定位与核心问题**\n"
            f"> Content for {n}\n"
            f">\n"
            f"> **方法与结果**\n"
            f"> Content for {n}\n"
            f">\n"
            f"> **图表质量审查**\n"
            f"> Content for {n}\n"
            f">\n"
            f"> **作者解释**\n"
            f"> Content for {n}\n"
            f">\n"
            f"> **我的理解**\n"
            f"> Content for {n}\n"
            f">\n"
            f"> **疑点 / 局限**\n"
            f"> Content for {n}\n"
        )
    return "\n".join(parts)
```

(Also implement `_make_empty_figure_block`, `_make_note_missing_subheading`, `_make_note_with_duplicate_figure` following the same pattern.)

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_ld_deep_postprocess.py -v
```
Expected: All 8 tests pass.

- [ ] **Step 5: Verify integration with existing CLI**

```bash
python paperforge/skills/literature-qa/scripts/ld_deep.py postprocess-pass2 <test_note_path> --figures 3 --format text
```
Expected: "OK: Pass 2 structure is clean" or specific error list.

```bash
python paperforge/skills/literature-qa/scripts/ld_deep.py postprocess-pass2 <test_note_path> --figures 3 --format json
```
Expected: JSON array of error objects.

- [ ] **Step 6: Add validate_skeleton step to prepare molecule**

In `prepare_deep_reading()` (line 1135+), after inserting the skeleton via `ensure_study_section()`, call `validate_callout_structure()` on the note text. If validation fails, log a warning so the user knows the skeleton has issues before AI starts writing. This is an internal consistency check, not a CLI command.

- [ ] **Step 7: Commit**

```bash
git add paperforge/skills/literature-qa/scripts/ld_deep.py tests/test_ld_deep_postprocess.py
git commit -m "feat: add postprocess-pass2 molecule for validating Pass 2 output"
```

---

### Task 3: Rewrite prompt_deep_subagent.md

**Files:**
- Modify: `paperforge/skills/literature-qa/prompt_deep_subagent.md`

- [ ] **Step 1: Rewrite prompt**

The new prompt should be ~150 lines (down from 297). Structure:

```
# Subagent Prompt for /pf-deep

## 任务
（1句话：对论文完成 journal-club 风格精读，写入 formal note 的 ## 🔍 精读 区域）

## 输入变量
（ZOTERO_KEY, VAULT, SCRIPT — same as before）

## 工作流程（严格按顺序执行）

### 1. 前置准备
- 运行 prepare 命令
- 读取 formal note（骨架已就绪，包含所有 figure/table 的 callout 块，每块内有固定子标题）

### 2. Pass 1: 概览
- 填写 Pass 1 section（5 Cs + figure 导读）
- 保存

### 3. Pass 2: 精读还原（按顺序逐个填写）
- 从 Figure 1 开始，依次填写每个 figure callout 块
- 每个块内有固定子标题，只需在下方填入内容
- 不要修改子标题，不要移动 callout 块，不要移动 ![[image]]
- 每完成一个 figure 保存一次
- Table 同理

### 4. 后处理验证
- 运行 postprocess-pass2
- 如果输出不是 "OK"：
  - 按错误清单逐条修复（错误包含行号，可直接定位）
  - 重新运行 postprocess-pass2
  - 最多 3 轮，如果仍有错误则报告给用户

### 5. Pass 3: 深度理解
- 填写 Pass 3 section（假设挑战、结论评估、启发等）

### 6. 最终验证
- 运行 validate-note

## Callout 规则
（保留：间距要求、类型使用指南 — 简洁版本）

## 错误处理
- prepare 失败 → 报告错误
- postprocess 3 轮仍有错误 → 报告剩余错误给用户

## 参考命令
（prepare, postprocess-pass2, validate-note 的 CLI 用法）
```

- [ ] **Step 2: Verify prompt reads naturally**

Read through the new prompt to ensure it flows well and all instruction steps are clear. The key test: can a developer (or an AI agent) follow it without ambiguity about what to do next?

- [ ] **Step 3: Commit**

```bash
git add paperforge/skills/literature-qa/prompt_deep_subagent.md
git commit -m "refactor: rewrite prompt_deep_subagent.md to directive command style (~150 lines)"
```

---

### Task 4: Full Suite Verification

- [ ] **Step 1: Run the full test suite**

```bash
pytest tests/ -q --ignore=tests/test_prepare_rollback.py
```
Expected: All passing (existing tests must not be broken by the refactoring).

- [ ] **Step 2: Run a manual end-to-end check**

Run `prepare` on a test key, then verify the skeleton structure has sub-headings:
```bash
python -c "
from pathlib import Path
from paperforge.skills.literature_qa.scripts.ld_deep import (
    FigureEntry, render_figure_block,
)
fig = FigureEntry(number=1, title='Test Figure', image_id='fig1',
                  image_link='99_System/PaperForge/ocr/KEY/images/fig_1.png',
                  page=5, caption='Test')
result = render_figure_block(fig)
print(result)
"
```

Expected output shows the callout block with all 6 sub-headings.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: full suite verification and final cleanup"
```

---

## Rollback Plan

If `postprocess-pass2` produces false positives on real deep-reading notes:
- Revert the CLI command addition only
- Keep the skeleton sub-headings change (it doesn't break anything)
- Fix the validation logic and re-deploy

If the new prompt causes confusion:
- Keep both old and new prompts as `prompt_deep_subagent_v1.md` and `prompt_deep_subagent.md`
- Symlink to whichever version is current
