# Literature QA Harness Redesign

> **问题：** Skill 里写条件路由 `if memory else grep`，笨 agent 可能读错分支。

## 解法：技能内不做路由，路由下沉到脚本

```
┌──────────────────────────────────────┐
│  SKILL.md                            │
│                                      │
│  1. bootstrap → 记下 $PYTHON $VAULT  │
│  2. 跑 pf_search.py, 读 JSON 输出    │
│  3. 格式化结果给用户                  │
│                                      │
│  agent 不用做决策，只是执行步骤        │
└─────────────┬────────────────────────┘
              │ 调用
              ▼
┌──────────────────────────────────────┐
│  scripts/pf_search.py                │
│                                      │
│  memory_layer.enabled?               │
│   ├─ YES → paperforge search --json   │
│   └─ NO  → grep -r .md files         │
│                                      │
│  输出: 统一 JSON 格式                 │
│  { results: [{key, title, ...}] }    │
└──────────────────────────────────────┘
```

## 核心原则

| | 错误的做法 | 正确的做法 |
|---|---|---|
| 决策位置 | SKILL.md 里写 if/else | 脚本里路由，skill 只调用脚本 |
| 输出格式 | 自由格式文字 | 脚本返回统一 JSON，agent 格式化 |
| 重复 | 每个 skill 自己写 grep | 共享 `pf_query.py` 统一入口 |
| 笨 agent | 可能走错分支 | 只执行 `run script → read output` |

## Harness 三件套

```
scripts/
├── pf_bootstrap.py    # 已有 — 输出 vault + python + memory 状态
├── pf_search.py       # 新 — 统一搜索入口（memory→sqlite, no memory→grep）
└── pf_context.py      # 新 — 统一上下文入口（paper-status / agent-context）
```

每次 skill 调用都走 `bootstrap → 脚本 → 格式化结果` 流程，agent 不需要做任何条件判断。
