# Multi-Agent Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Codex and Claude Code support to PaperForge setup, unify AGENT_CONFIGS with `format` field, and refactor skill deployment into format-specific functions.

**Architecture:** Extend AGENT_CONFIGS with `format` and `prefix` fields, split skill deployment into `deploy_skill_directory()` / `deploy_flat_command()` / `deploy_rules_file()`, and generate per-agent skill files.

**Tech Stack:** Python 3.10+, shutil, pathlib

---

## File Changes Overview

| File | Change |
|------|--------|
| `paperforge/setup_wizard.py` | Modify AGENT_CONFIGS, add format-specific deploy functions, refactor headless_deploy() Phase 4 |
| `command/pf-deep.md` | (existing - source) |
| `paperforge/skills/literature-qa/` | (existing - source for SKILL.md directory content) |

---

## Task 1: Extend AGENT_CONFIGS

**Files:**
- Modify: `paperforge/setup_wizard.py:46-64`

- [ ] **Step 1: Read current AGENT_CONFIGS**

```python
# Current (lines 46-64):
AGENT_CONFIGS = {
    "opencode": {
        "name": "OpenCode",
        "skill_dir": ".opencode/skills",
        "command_dir": ".opencode/command",
        "config_file": None,
    },
    "cursor": {"name": "Cursor", "skill_dir": ".cursor/skills", "config_file": ".cursor/settings.json"},
    "claude": {"name": "Claude Code", "skill_dir": ".claude/skills", "config_file": ".claude/skills.json"},
    "windsurf": {"name": "Windsurf", "skill_dir": ".windsurf/skills", "config_file": None},
    "github_copilot": {
        "name": "GitHub Copilot",
        "skill_dir": ".github/skills",
        "config_file": ".github/copilot-instructions.md",
    },
    "cline": {"name": "Cline", "skill_dir": ".clinerules/skills", "config_file": ".clinerules"},
    "augment": {"name": "Augment", "skill_dir": ".augment/skills", "config_file": None},
    "trae": {"name": "Trae", "skill_dir": ".trae/skills", "config_file": None},
}
```

- [ ] **Step 2: Replace with new AGENT_CONFIGS**

```python
AGENT_CONFIGS = {
    "opencode": {
        "name": "OpenCode",
        "skill_dir": ".opencode/skills",
        "command_dir": ".opencode/command",
        "format": "flat_command",
        "prefix": "/",
        "config_file": None,
    },
    "claude": {
        "name": "Claude Code",
        "skill_dir": ".claude/skills",
        "format": "skill_directory",
        "prefix": "/",
        "config_file": ".claude/skills.json",
    },
    "codex": {
        "name": "Codex",
        "skill_dir": ".codex/skills",
        "format": "skill_directory",
        "prefix": "$",
        "config_file": None,
    },
    "cursor": {
        "name": "Cursor",
        "skill_dir": ".cursor/skills",
        "format": "skill_directory",
        "prefix": "/",
        "config_file": ".cursor/settings.json",
    },
    "windsurf": {
        "name": "Windsurf",
        "skill_dir": ".windsurf/skills",
        "format": "skill_directory",
        "prefix": "/",
        "config_file": None,
    },
    "github_copilot": {
        "name": "GitHub Copilot",
        "skill_dir": ".github/skills",
        "format": "skill_directory",
        "prefix": "/",
        "config_file": ".github/copilot-instructions.md",
    },
    "cline": {
        "name": "Cline",
        "skill_dir": ".clinerules",
        "format": "rules_file",
        "prefix": "/",
        "config_file": ".clinerules",
    },
    "augment": {
        "name": "Augment",
        "skill_dir": ".augment/skills",
        "format": "skill_directory",
        "prefix": "/",
        "config_file": None,
    },
    "trae": {
        "name": "Trae",
        "skill_dir": ".trae/skills",
        "format": "skill_directory",
        "prefix": "/",
        "config_file": None,
    },
}
```

- [ ] **Step 3: Verify test expectations need updating**

Run: `pytest tests/test_setup_wizard.py -v -k "agent" 2>&1 | head -40`
Expected: Test failures on `expected_agents` and `format` field checks (we will fix tests in Task 6)

- [ ] **Step 4: Commit**

```bash
git add paperforge/setup_wizard.py
git commit -m "refactor: extend AGENT_CONFIGS with format and prefix fields, add codex"
```

---

## Task 2: Add format-specific deploy functions

**Files:**
- Modify: `paperforge/setup_wizard.py` (after line 1700, before Phase 4 deploy code)

- [ ] **Step 1: Write the three deploy helper functions**

Add these functions right before the `headless_deploy()` function definition (around line 1530):

```python
def _deploy_skill_directory(
    vault: Path,
    skill_dir: str,
    repo_root: Path,
    system_dir: str,
    resources_dir: str,
    literature_dir: str,
    control_dir: str,
    base_dir: str,
) -> list[str]:
    """Deploy skills in SKILL.md directory format (Claude Code, Codex, Copilot, etc.)."""
    imported = []
    skill_src = repo_root / "paperforge" / "skills" / "literature-qa"
    skill_dst_base = vault / skill_dir / "literature-qa"

    for skill_name in ["pf-deep", "pf-paper", "pf-sync", "pf-ocr", "pf-status"]:
        skill_dst = skill_dst_base / skill_name
        skill_dst.mkdir(parents=True, exist_ok=True)

        # SKILL.md
        src_md = skill_src / "scripts" / f"{skill_name}.md"
        if src_md.exists():
            text = src_md.read_text(encoding="utf-8")
            text = _substitute_vars(text, system_dir, resources_dir, literature_dir, control_dir, base_dir, skill_dir)
            (skill_dst / "SKILL.md").write_text(text, encoding="utf-8")
            imported.append(skill_name)

        # chart-reading guides (only for pf-deep)
        if skill_name == "pf-deep":
            chart_src = skill_src / "chart-reading"
            chart_dst = skill_dst / "chart-reading"
            if chart_src.exists() and chart_src.is_dir():
                chart_dst.mkdir(parents=True, exist_ok=True)
                for f in chart_src.glob("*.md"):
                    shutil.copy2(f, chart_dst / f.name)

    return imported


def _deploy_flat_command(
    vault: Path,
    command_dir: str,
    repo_root: Path,
    system_dir: str,
    resources_dir: str,
    literature_dir: str,
    control_dir: str,
    base_dir: str,
    skill_dir: str,
) -> list[str]:
    """Deploy skills in flat .md command format (OpenCode)."""
    imported = []
    command_src = repo_root / "command"
    command_dst = vault / command_dir
    if not (command_src.exists() and command_src.is_dir()):
        return imported

    command_dst.mkdir(parents=True, exist_ok=True)
    for f in command_src.glob("pf-*.md"):
        text = f.read_text(encoding="utf-8")
        text = _substitute_vars(text, system_dir, resources_dir, literature_dir, control_dir, base_dir, skill_dir)
        (command_dst / f.name).write_text(text, encoding="utf-8")
        imported.append(f.stem)

    return imported


def _deploy_rules_file(
    vault: Path,
    skill_dir: str,
    repo_root: Path,
    system_dir: str,
    resources_dir: str,
    literature_dir: str,
    control_dir: str,
    base_dir: str,
    skill_dir_path: str,
) -> list[str]:
    """Deploy skills as a single .clinerules file (Cline)."""
    imported = []
    rules_src = repo_root / "command"
    rules_dst = vault / skill_dir  # e.g., .clinerules

    combined = []
    for f in sorted((rules_src / "pf-deep.md").read_text(encoding="utf-8").split("\n")):
        combined.append(f)

    # For Cline, concatenate all command files into a single .clinerules file
    sections = []
    for cmd_file in sorted(rules_src.glob("pf-*.md")):
        content = cmd_file.read_text(encoding="utf-8")
        content = _substitute_vars(content, system_dir, resources_dir, literature_dir, control_dir, base_dir, skill_dir_path)
        sections.append(f"# {cmd_file.stem}\n\n{content}")

    rules_dst.write_text("\n\n---\n\n".join(sections), encoding="utf-8")
    imported.append("clinerules")
    return imported


def _substitute_vars(
    text: str,
    system_dir: str,
    resources_dir: str,
    literature_dir: str,
    control_dir: str,
    base_dir: str,
    skill_dir: str,
) -> str:
    """Substitute path variables in skill content."""
    for old, new in [
        ("<system_dir>", system_dir),
        ("<resources_dir>", resources_dir),
        ("<literature_dir>", literature_dir),
        ("<control_dir>", control_dir),
        ("<base_dir>", base_dir),
        ("<skill_dir>", skill_dir),
    ]:
        text = text.replace(old, new)
    return text
```

- [ ] **Step 2: Verify functions are syntactically correct**

Run: `python -c "import ast; ast.parse(open('paperforge/setup_wizard.py').read())"`
Expected: No SyntaxError

- [ ] **Step 3: Commit**

```bash
git add paperforge/setup_wizard.py
git commit -m "feat: add format-specific deploy helper functions"
```

---

## Task 3: Refactor headless_deploy Phase 4

**Files:**
- Modify: `paperforge/setup_wizard.py:1662-1726` (Phase 4 deploy section)

- [ ] **Step 1: Replace the OpenCode-only command block with format dispatch**

Replace lines 1708-1726 (the `if agent_key == "opencode":` block and OpenCode-specific code) with:

```python
    # Deploy skills based on agent format
    fmt = agent_config.get("format", "skill_directory")
    imported_skills = []

    if fmt == "flat_command":
        imported_skills = _deploy_flat_command(
            vault, agent_config["command_dir"], repo_root,
            system_dir, resources_dir, literature_dir, control_dir, base_dir, skill_dir,
        )
    elif fmt == "rules_file":
        imported_skills = _deploy_rules_file(
            vault, agent_config["skill_dir"], repo_root,
            system_dir, resources_dir, literature_dir, control_dir, base_dir, skill_dir,
        )
    else:
        # skill_directory (default)
        imported_skills = _deploy_skill_directory(
            vault, skill_dir, repo_root,
            system_dir, resources_dir, literature_dir, control_dir, base_dir,
        )

    if imported_skills:
        print(f"    [OK] {len(imported_skills)} skill(s): {', '.join(imported_skills)}")
```

- [ ] **Step 2: Remove the separate OpenCode command block and the ld_deep/chart-reading manual deploy**

The old code at lines 1684-1706 (ld_deep.py copy, prompt copy, chart-reading copy) should be removed since `_deploy_skill_directory()` handles it.

- [ ] **Step 3: Verify Phase 4 still works**

Run: `python -c "from paperforge.setup_wizard import headless_deploy; print('import ok')"`
Expected: No import errors

- [ ] **Step 4: Commit**

```bash
git add paperforge/setup_wizard.py
git commit -m "refactor: replace OpenCode-only deploy with format-based dispatch"
```

---

## Task 4: Create source SKILL.md files

**Files:**
- Create: `paperforge/skills/literature-qa/scripts/pf-deep.md`
- Create: `paperforge/skills/literature-qa/scripts/pf-paper.md`
- Create: `paperforge/skills/literature-qa/scripts/pf-sync.md`
- Create: `paperforge/skills/literature-qa/scripts/pf-ocr.md`
- Create: `paperforge/skills/literature-qa/scripts/pf-status.md`

- [ ] **Step 1: Create pf-deep.md (SKILL.md format with frontmatter)**

```markdown
---
name: pf-deep
description: "PaperForge 完整精读 — Keshav 三阶段深度阅读"
argument-hint: "<zotero_key>"
allowed-tools:
  - Read
  - Bash
  - Edit
---

# /pf-deep

## Purpose

基于单篇论文的组会式精读入口。

1. 解析 `/pf-deep <query>` 中的查询词
2. 支持 Zotero key、标题片段、DOI、PMID、关键词
3. 优先搜索本地 Zotero 并锁定单篇论文
4. 绑定该论文对应的：
   - `<system_dir>/PaperForge/ocr/<KEY>/fulltext.md`
   - `<system_dir>/PaperForge/ocr/<KEY>/meta.json`
   - `<resources_dir>/<literature_dir>/.../KEY - Title.md`
5. 在正式文献卡片中检查或创建 `## 精读`
6. 以"研究思路 + figure-by-figure"方式一次性完成精读写回

## CLI Equivalent

paperforge sync      # 生成 library-records 和正式笔记
paperforge ocr       # 完成 OCR 提取
paperforge deep-reading  # 查看精读队列状态

> `/pf-deep` 是 Agent 层命令，无直接 CLI 等效命令。其依赖的数据由上述 CLI 命令准备。

## Prerequisites

- library-record 已创建（paperforge sync 生成）
- analyze: true 已设置（在 library-record frontmatter 中）
- OCR 已完成（ocr_status: done）
- fulltext.md 存在且非空
- 正式笔记文件存在

## Arguments

| 参数 | 必需 | 说明 |
|------|------|------|
| <query> | 是（queue 模式除外） | Zotero key、标题片段、DOI、PMID 或关键词 |
| queue | 否 | 启动批量精读队列模式 |

## Example

/pf-deep XGT9Z257
/pf-deep Predictive findings on magnetic resonance imaging

当不提供具体 key/标题时，agent 自动执行以下流程：

1. 运行 paperforge deep-reading 查看精读队列
2. 解析输出的队列状态（analyze=true + deep_reading_status != done + ocr_status）
3. 按 OCR 状态分组展示
4. 由用户选择篇目后批量处理

## Output

Agent 在正式笔记中创建或更新 ## 精读 区域，包含：

- Pass 1: 概览 — 一句话总览、5 Cs 快速评估、Figure 导读
- Pass 2: 精读还原 — Figure-by-Figure 解析、Table-by-Table 解析、关键方法补课、主要发现与新意
- Pass 3: 深度理解 — 假设挑战与隐藏缺陷、结论扎实性评估、Discussion 解读、个人启发、遗留问题

## Standard Skeleton

## 精读

**证据边界**：区分三层信息：论文结果、作者解释、我的理解/推断。

### Pass 1: 概览

**一句话总览**
（待补充）

**5 Cs 快速评估**
- Category（类型）：
- Context（上下文）：
- Correctness（合理性初判）：
- Contributions（贡献）：
- Clarity（清晰度）：

**Figure 导读**
- 关键主图：
- 证据转折点：
- 需要重点展开的 supplementary：
- 关键表格：

### Pass 2: 精读还原

#### Figure-by-Figure 解析
（每张 figure 下方按以下顺序填写）
- 图像定位与核心问题：页码 + 要回答什么问题
- 方法与结果：方法 + 结果
- 作者解释：作者对该图的解读
- 我的理解：自己的理解（区分于作者解释）
- 在全文中的作用：该图在整体故事线中的位置
- 疑点 / 局限：读图时发现的疑问

#### Table-by-Table 解析

#### 关键方法补课
- 方法 1：
- 方法 2：

#### 主要发现与新意
**主要发现**
- 发现 1：
- 发现 2：

### Pass 3: 深度理解

#### 假设挑战与隐藏缺陷
- 隐含假设：
- 如果放宽某个假设，结论还成立吗？
- 缺少哪些关键引用？

#### 哪些结论扎实，哪些仍存疑
**较扎实**
-
**仍存疑**
-

#### Discussion 与 Conclusion 怎么读
- 作者真正完成了什么：
- 哪些地方有拔高：
- 哪些地方是推测：

#### 对我的启发
- 研究设计上：
- figure 组织上：
- 方法组合上：
- 未来工作想法：

#### 遗留问题
**遗留问题**
-

## Platform Notes

### Claude Code

- /pf-deep 在对话窗口直接输入
- Agent 使用 paperforge paths --json 获取 Vault 路径配置
- 多篇文章并行时使用 Task tool 启动 subagent

### Codex

- $pf-deep 在对话窗口直接输入（美元符号前缀）
- 其他行为与 Claude Code 一致

## See Also

- pf-paper — 快速摘要与问答
- pf-sync — 同步 Zotero
- pf-ocr — 运行 OCR
- pf-status — 查看状态
```

- [ ] **Step 2: Create pf-paper.md**

```markdown
---
name: pf-paper
description: "PaperForge 快速摘要与问答"
argument-hint: "<zotero_key>"
allowed-tools:
  - Read
  - Bash
---

# /pf-paper

## Purpose

快速摘要单篇论文的核心内容，不做深度精读。

## Prerequisites

- library-record 已创建

## Arguments

| 参数 | 必需 | 说明 |
|------|------|------|
| <query> | 是 | Zotero key、标题片段、DOI、PMID 或关键词 |

## Output

在正式笔记中创建或更新 ## 摘要 区域：

- 一句话总览
- 研究问题
- 方法
- 主要结论
- 关键 Figure
- 简短评价
```

- [ ] **Step 3: Create pf-sync.md**

```markdown
---
name: pf-sync
description: "PaperForge 同步 Zotero 并生成文献笔记"
allowed-tools:
  - Bash
---

# /pf-sync

## Purpose

运行 paperforge sync，检测 Zotero 新条目并生成正式文献笔记。

## Usage

/pf-sync

paperforge sync
```

- [ ] **Step 4: Create pf-ocr.md**

```markdown
---
name: pf-ocr
description: "PaperForge 运行 PDF OCR"
allowed-tools:
  - Bash
---

# /pf-ocr

## Purpose

运行 paperforge ocr，对标记了 do_ocr: true 的文献执行 OCR。

## Usage

/pf-ocr

paperforge ocr
```

- [ ] **Step 5: Create pf-status.md**

```markdown
---
name: pf-status
description: "PaperForge 查看系统状态"
allowed-tools:
  - Bash
---

# /pf-status

## Purpose

运行 paperforge status，查看系统整体状态。

## Usage

/pf-status

paperforge status
```

- [ ] **Step 6: Commit**

```bash
git add paperforge/skills/literature-qa/scripts/
git commit -m "feat: add SKILL.md source files for skill_directory agents"
```

---

## Task 5: Fix directory creation for new structure

**Files:**
- Modify: `paperforge/setup_wizard.py:1587-1603`

- [ ] **Step 1: Update Phase 2 directory creation**

The current Phase 2 creates `<skill_dir>/literature-qa/scripts` and `<skill_dir>/literature-qa/chart-reading` directly. After refactoring, these subdirs are created inside the per-skill directories. Update Phase 2 to not create these hardcoded paths:

```python
    # Base directories (skill_dir may differ per agent)
    dirs = [
        pf_path / "exports",
        pf_path / "ocr",
        pf_path / "config",
        pf_path / "worker/scripts",
        vault / resources_dir / literature_dir,
        vault / resources_dir / control_dir / "library-records",
        vault / base_dir,
        vault / ".obsidian" / "plugins" / "paperforge",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 2: Commit**

```bash
git add paperforge/setup_wizard.py
git commit -m "fix: remove hardcoded literature-qa subdirs from Phase 2 directory creation"
```

---

## Task 6: Update tests

**Files:**
- Modify: `tests/test_setup_wizard.py:31-63`

- [ ] **Step 1: Update expected_agents**

```python
expected_agents = {
    "opencode", "claude", "codex", "cursor", "windsurf",
    "github_copilot", "cline", "augment", "trae",
}
```

- [ ] **Step 2: Add format field assertions**

```python
def test_agent_config_format_field():
    for key, cfg in AGENT_CONFIGS.items():
        assert "format" in cfg, f"{key} missing format field"
        assert cfg["format"] in {"skill_directory", "flat_command", "rules_file"}

def test_agent_config_prefix_field():
    for key, cfg in AGENT_CONFIGS.items():
        assert "prefix" in cfg, f"{key} missing prefix field"
        assert cfg["prefix"] in {"/", "$"}

def test_opencode_has_command_dir():
    assert AGENT_CONFIGS["opencode"].get("command_dir") == ".opencode/command"

def test_codex_format():
    assert AGENT_CONFIGS["codex"]["format"] == "skill_directory"
    assert AGENT_CONFIGS["codex"]["prefix"] == "$"
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_setup_wizard.py -v 2>&1 | tail -30`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add tests/test_setup_wizard.py
git commit -m "test: add AGENT_CONFIGS format/prefix field tests, update expected agents"
```

---

## Task 7: Integration smoke test

- [ ] **Step 1: Dry-run headless_deploy with different agents**

Create a temp directory and test:

```python
import tempfile, shutil
from pathlib import Path
tmp = Path(tempfile.mkdtemp())
rv = headless_deploy(
    vault=tmp,
    agent_key="claude",
    system_dir="99_System",
    resources_dir="03_Resources",
    literature_dir="Literature",
    control_dir="LiteratureControl",
    base_dir="05_Bases",
    skip_checks=True,
)
assert rv == 0, f"claude install failed: {rv}"
assert (tmp / ".claude" / "skills" / "literature-qa").exists()
shutil.rmtree(tmp)
```

Run: `python -c "from paperforge.setup_wizard import headless_deploy; from pathlib import Path; import tempfile, shutil; tmp = Path(tempfile.mkdtemp()); rv = headless_deploy(vault=tmp, agent_key='claude', system_dir='99_System', resources_dir='03_Resources', literature_dir='Literature', control_dir='LiteratureControl', base_dir='05_Bases', skip_checks=True); print(rv, (tmp / '.claude' / 'skills').exists()); shutil.rmtree(tmp)"`
Expected: `0 True`

- [ ] **Step 2: Test OpenCode flat_command**

Run: `python -c "from paperforge.setup_wizard import headless_deploy; from pathlib import Path; import tempfile, shutil; tmp = Path(tempfile.mkdtemp()); rv = headless_deploy(vault=tmp, agent_key='opencode', system_dir='99_System', resources_dir='03_Resources', literature_dir='Literature', control_dir='LiteratureControl', base_dir='05_Bases', skip_checks=True); print(rv, (tmp / '.opencode' / 'command' / 'pf-deep.md').exists()); shutil.rmtree(tmp)"`
Expected: `0 True`

- [ ] **Step 3: Test Codex**

Run: `python -c "from paperforge.setup_wizard import headless_deploy; from pathlib import Path; import tempfile, shutil; tmp = Path(tempfile.mkdtemp()); rv = headless_deploy(vault=tmp, agent_key='codex', system_dir='99_System', resources_dir='03_Resources', literature_dir='Literature', control_dir='LiteratureControl', base_dir='05_Bases', skip_checks=True); print(rv, (tmp / '.codex' / 'skills' / 'literature-qa').exists()); shutil.rmtree(tmp)"`
Expected: `0 True`

- [ ] **Step 4: Commit**

```bash
git commit -m "test: add integration smoke tests for multi-agent deploy"
```

---

## Task 8: Final verification

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v --tb=short 2>&1 | tail -40`
Expected: All tests pass, 0 regressions

- [ ] **Step 2: Push**

```bash
git push origin master
```
