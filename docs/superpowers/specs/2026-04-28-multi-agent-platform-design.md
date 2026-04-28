# SPEC: 多 Agent 平台适配 (v1.5)

**Date:** 2026-04-28
**Status:** Draft
**Parent:** v1.4 Code Health & UX Hardening

---

## 1. 背景与目标

PaperForge 当前支持 8 个 Agent 平台，但缺少 Codex 和 Claude Code 的完整支持。本 SPEC 统一管理所有 Agent 平台的 skill 部署逻辑。

**核心目标：**
- 添加 Codex 和 Claude Code 完整支持
- 统一 `AGENT_CONFIGS` 配置结构
- 复用部署函数，按 skill 格式分类处理

---

## 2. Agent Platform 分类

| 类型 | Agent 列表 | Skill 格式 | 调用前缀 |
|------|-----------|-----------|---------|
| **SKILL.md 目录** | claude, copilot, cursor, windsurf, augment, trae, qwen, codebuddy | `dir/SKILL.md` | `/` |
| **扁平 Command** | opencode | `.md` 文件 | `/` |
| **`$` 前缀** | codex | `dir/SKILL.md` | `$` |
| **Rules 文件** | cline | `.clinerules` 单文件 | `/` |

---

## 3. AGENT_CONFIGS 新结构

```python
AGENT_CONFIGS = {
    "opencode": {
        "name": "OpenCode",
        "skill_dir": ".opencode/skills",
        "command_dir": ".opencode/command",     # 扁平 command 文件
        "format": "flat_command",
        "prefix": "/",
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
    },
    "cursor": {
        "name": "Cursor",
        "skill_dir": ".cursor/skills",
        "format": "skill_directory",
        "prefix": "/",
        "config_file": ".cursor/settings.json",
    },
    "copilot": {
        "name": "GitHub Copilot",
        "skill_dir": ".github/skills",
        "format": "skill_directory",
        "prefix": "/",
        "config_file": ".github/copilot-instructions.md",
    },
    "windsurf": {
        "name": "Windsurf",
        "skill_dir": ".windsurf/skills",
        "format": "skill_directory",
        "prefix": "/",
    },
    "cline": {
        "name": "Cline",
        "skill_dir": ".clinerules",
        "format": "rules_file",
        "prefix": "/",
    },
    "augment": {
        "name": "Augment",
        "skill_dir": ".augment/skills",
        "format": "skill_directory",
        "prefix": "/",
    },
    "trae": {
        "name": "Trae",
        "skill_dir": ".trae/skills",
        "format": "skill_directory",
        "prefix": "/",
    },
}
```

**字段说明：**
- `skill_dir`: SKILL.md 目录格式的 agent 用此路径
- `command_dir`: OpenCode 扁平 command 文件用此路径
- `format`: `skill_directory` | `flat_command` | `rules_file`
- `prefix`: 命令调用前缀，`/` 或 `$`
- `config_file`: 可选配置文件路径

---

## 4. Skill 命名规范

所有平台统一使用 `pf-` 前缀：

| Skill 名称 | 功能 |
|-----------|------|
| `pf-deep` | 完整 Keshav 三阶段精读 |
| `pf-paper` | 快速摘要 |
| `pf-sync` | 同步 Zotero |
| `pf-ocr` | 运行 OCR |
| `pf-status` | 查看状态 |

调用示例：
- `/pf-deep ABCDEFG` (大多数 agent)
- `$pf-deep ABCDEFG` (Codex)

---

## 5. 部署函数设计

```
deploy_agent_skills(agent, vault, skill_names)
    ├── deploy_skill_directory(agent, vault, skill_name)  # SKILL.md 目录格式
    ├── deploy_flat_command(agent, vault, skill_name)   # OpenCode 扁平格式
    └── deploy_rules_file(agent, vault, skill_name)      # Cline 专用
```

### 5.1 SKILL.md 目录格式 (skill_directory)

用于：claude, codex, copilot, cursor, windsurf, augment, trae, qwen, codebuddy

```
.<agent>/skills/pf-deep/
├── SKILL.md       # 主文件
└── (可选) scripts/, references/, assets/
```

**SKILL.md frontmatter:**
```yaml
---
name: pf-deep
description: "PaperForge 完整精读 — Keshav 三阶段"
argument-hint: "<zotero_key>"
allowed-tools:
  - Read
  - Bash
  - Edit
---
```

### 5.2 扁平 Command 格式 (flat_command)

用于：OpenCode

```
.opencode/command/pf-deep.md   # 单文件，无目录
```

**文件格式：** 纯 markdown，无 frontmatter（OpenCode 用 permission: block）

### 5.3 Rules 文件格式 (rules_file)

用于：Cline

```
.clinerules   # 单文件，包含 PaperForge 规则
```

---

## 6. 目录结构（部署后）

以 OpenCode 为例，local 安装到 vault 后：

```
vault/
├── .opencode/
│   ├── command/
│   │   ├── pf-deep.md
│   │   ├── pf-paper.md
│   │   ├── pf-sync.md
│   │   ├── pf-ocr.md
│   │   └── pf-status.md
│   └── skills/          # 预留，暂不使用
└── .claude/
    └── skills/
        └── pf-deep/
            └── SKILL.md
```

---

## 7. 实现任务

### 7.1 重构 AGENT_CONFIGS (20-01 扩展)

- 新增 `codex` 条目
- 新增 `format` 字段
- 新增 `command_dir` 字段（OpenCode 专用）
- 补全 `config_file` 字段

### 7.2 拆分 deploy_agent_skills()

- `deploy_skill_directory()`: SKILL.md 目录格式统一处理
- `deploy_flat_command()`: OpenCode 扁平文件处理
- `deploy_rules_file()`: Cline 单文件处理

### 7.3 生成各平台 Skill 文件

- 为每个 agent 平台生成对应的 skill 文件
- OpenCode 生成扁平 .md 文件
- Claude Code/Codex 等生成 SKILL.md 目录

---

## 8. 验证

- `paperforge setup --headless --agent opencode` 生成的 `.opencode/command/pf-deep.md` 格式正确
- `paperforge setup --headless --agent claude` 生成的 `.claude/skills/pf-deep/SKILL.md` 格式正确
- `paperforge setup --headless --agent codex` 生成的 `.codex/skills/pf-deep/SKILL.md` 格式正确
- 各平台 skill 命名统一为 `pf-*`

---

## 9. Success Criteria

- [ ] AGENT_CONFIGS 包含所有 10 个 agent 平台（新增 codex）
- [ ] `format` 字段正确区分 skill_directory / flat_command / rules_file
- [ ] OpenCode 生成扁平 command 文件（非目录）
- [ ] Claude Code/Codex/Copilot 等生成 SKILL.md 目录
- [ ] 所有 skill 命名统一使用 `pf-` 前缀
- [ ] Codex 使用 `$` 前缀调用
- [ ] Cline 部署为单 `.clinerules` 文件
- [ ] 现有测试全部通过
