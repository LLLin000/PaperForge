# Plugin Settings Redesign — Tabbed Settings + Feature Toggles

> **Date:** 2026-05-12 | **Research ref:** Claudian + obsidian-skills-manager

## Architecture

```
Settings → PaperForge
  ┌─────────────────┬───────────────────────────────┐
  │ [安装]           │ [功能]                         │
  ├─────────────────┼───────────────────────────────┤
  │ Python 路径      │  Skills                        │
  │ PaddleOCR Key    │  ├─ 系统技能 (per-agent dir)    │
  │ Zotero 数据目录   │  │   ├─ 开关: toggle frontmatter│
  │ Agent 平台       │  │   ├─ 更新: GitHub semver    │
  │ Agent Config路径  │  │   └─ 冻结: 锁版本          │
  │ ...              │  └─ 用户技能 (自定义目录)       │
  │                  │       └─ 开关: toggle frontmatter│
  │                  │                                │
  │                  │  Memory Layer                   │
  │                  │  ├─ FTS5 搜索                   │
  │                  │  ├─ agent-context               │
  │                  │  └─ reading-log                 │
  │                  │                                │
  │                  │  向量数据库                      │
  │                  │  ├─ 开关: 启用/禁用              │
  │                  │  ├─ 模式: 本地 • API            │
  │                  │  ├─ 本地: [安装模型] + 模型名    │
  │                  │  └─ API: API Key                │
  └─────────────────┴───────────────────────────────┘
```

## Tab Implementation

Follow Claudian pattern: custom tab bar with class-toggle, all content divs exist in DOM simultaneously.

```typescript
// PaperforgeSettingsTab.ts
type SettingsTabId = 'setup' | 'features';

// -- render() --
// 1. Tab bar
const tabBar = containerEl.createDiv({ cls: 'paperforge-settings-tabs' });
const tabButtons = new Map<SettingsTabId, HTMLElement>();
const tabContents = new Map<SettingsTabId, HTMLElement>();

// 2. For each tab: create button + content div
for (const [id, label] of [['setup','安装'], ['features','功能']]) {
    const btn = tabBar.createEl('button', { cls: 'paperforge-settings-tab', text: label });
    btn.addEventListener('click', () => switchTab(id));  // toggles --active class
    tabButtons.set(id, btn);
    
    const content = containerEl.createDiv({ cls: 'paperforge-settings-tab-content' });
    tabContents.set(id, content);
}

// 3. Render each tab
renderSetupTab(tabContents.get('setup'));
renderFeaturesTab(tabContents.get('features'));

// 4. Activate default tab
switchTab(this.activeTab);
```

CSS: `.paperforge-settings-tab-content { display: none; }` `.paperforge-settings-tab-content--active { display: block; }`

## Section 1: Skills Management

### System Skill Detection

Scan vault-local agent skill directories (from `AGENT_SKILL_DIRS` mapping):

```
{vault}/.opencode/skills/literature-qa/SKILL.md
{vault}/.opencode/skills/literature-logging/SKILL.md    (new)
{vault}/.claude/skills/literature-qa/SKILL.md
{vault}/.codex/skills/literature-qa/SKILL.md
...
```

Each skill identified by `SKILL.md` frontmatter:
```yaml
name: literature-qa
description: 学术文献库操作
version: 1.5.5
source: PaperForge/paperforge
```

### UI per skill row

```
┌─────────────────────────────────────────────────────┐
│ [✓] literature-qa               v1.5.5  [更新] [冻结] │
│     学术文献库操作：精读、问答、检索                    │
├─────────────────────────────────────────────────────┤
│ [✓] literature-logging          v1.0.0  [更新] [冻结] │
│     阅读日志与工作日志管理                             │
└─────────────────────────────────────────────────────┘
```

- **开关** (`[✓]`): 写入 `SKILL.md` frontmatter `disable-model-invocation: true/false`（obsidian-skills-manager 同款方式）
- **更新**: GitHub API `GET /repos/LLLin000/PaperForge/releases?per_page=25` → semver 比对 → 有新版显示 `[更新]` 按钮 → 重新下载 skill 文件
- **冻结**: 写入 plugin `data.json` → `frozen_skills: { "literature-qa": true }` → 冻结后不显示更新提示

### User Skill Detection

```
{vault}/.claude/skills/     (可配置路径)
```

User skills identified by `SKILL.md` frontmatter field `source: user` (or no `source` field). Features:
- **开关**: same `disable-model-invocation` toggle
- **无更新/冻结功能**

### Source attribution

Frontmatter discriminator for system vs user:
```yaml
# System skill
source: paperforge          # → managed by plugin, has update button

# User skill  
source: user                # → toggle only, no update
# (or no source field)      # → treated as user
```

## Section 2: Feature Toggles

Memory Layer features as simple Obsidian toggles in plugin `data.json`:

| Key | Default | Effect |
|-----|---------|--------|
| `features.fts_search` | `true` | `paperforge memory build` 是否创建 FTS 索引 |
| `features.agent_context` | `true` | 是否允许 `agent-context` 命令 |
| `features.reading_log` | `true` | 是否启用 paper_events 表 |
| `features.vector_db` | `false` | 是否启用向量检索模块 |

When a feature is disabled, the corresponding CLI command returns a clear error message.

## Section 3: Vector Database

```
┌─────────────────────────────────────────┐
│ 向量数据库                  [启用]       │
│                                         │
│ 模式:  ● 本地  ○ API                   │
│                                         │
│ 本地模型: all-MiniLM-L6-v2              │
│ 模型大小: 80 MB                         │
│ 状态: ● 已安装 / ○ 未安装              │
│        [安装模型]                        │
│        [重新安装]                        │
│                                         │
│ API Key:  ┌─────────────────────────────┐│
│           │ sk-...                       ││
│           └─────────────────────────────┘│
│ 模型: text-embedding-3-small             │
└─────────────────────────────────────────┘
```

Implementation notes:
- Model installation: `pip install sentence-transformers` + trigger model download
- Model path: stored in `data.json` under `features.vector_db.model_path`
- API: uses existing `.env` PaddleOCR Key pattern, add `VECTOR_API_KEY`
- `pip install` is async — show progress bar

## Data Storage

All toggles in plugin `data.json`:
```json
{
  "features": {
    "fts_search": true,
    "agent_context": true,
    "reading_log": true,
    "vector_db": false
  },
  "vector_db_mode": "local",
  "vector_db_model": "all-MiniLM-L6-v2",
  "vector_db_api_key": "",
  "frozen_skills": {
    "literature-qa": false
  }
}
```

Skill disable state in `SKILL.md` frontmatter (standard Agent Skills spec):
```yaml
disable-model-invocation: true
```
