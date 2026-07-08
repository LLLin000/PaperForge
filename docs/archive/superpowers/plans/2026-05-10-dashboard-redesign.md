# PaperForge Dashboard 重设计 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 PaperForge Dashboard 从 "功能展示墙" 重构为 "工作流控制台"，只保留 global / collection / paper 三个视图，删除 Copy Context 类按钮和 dead deep-reading 代码。

**Architecture:** 3 个模式（global=系统首页, collection=批量工作台, paper=阅读辅助侧栏）。Workspace 检测用 `dirname(filePath)` 提取 zotero_key。精读内容从 formal note 正文 `## 🔍 精读` section 直接读取。Discussion 卡片做 UI 壳+空态（数据尚未生产）。Actions 由全局静态网格改为各视图内 contextual 按钮。

**Tech Stack:** Vanilla Obsidian DOM API (`createEl`, `addClass`, `setText`), Node.js fs/path, single-file plugin (`main.js`)

---

## 文件结构

| 文件 | 改动类型 | 职责 |
|------|---------|------|
| `paperforge/plugin/main.js` | 大量修改 | 所有渲染方法、路由、actions |
| `paperforge/plugin/src/testable.js` | 小改 | 删除 Copy Context actions |
| `paperforge/plugin/styles.css` | 中等改动 | 新组件样式 |
| `docs/ux-contract.md` | 更新 | workflow specification |

---

## Vault 实际数据结构（来自 D:\L\Med\test1\ 勘探）

```
Workspace 路径: Resources/Literature/{domain}/{zotero_key} - {title}/
Formal note:    {workspace}/{zotero_key} - {title}.md
Fulltext:       {workspace}/fulltext.md  （OCR 后的副本）
AI dir:         {workspace}/ai/  （目前为空，无 discussion.json）
```

**Workspace 检测策略（用户指定）:** `dirname(filePath)` → 正则 `^([A-Z0-9]{8})` 提取 zotero_key

**精读内容格式（来自 3EWBBTAS formal note 正文）:**
```
## 🔍 精读
### Pass 1: 概览
  **一句话总览**: ...
  **5 Cs 快速评估**: ...
  **Figure 导读**: ...
### Pass 2: 精读还原
  ...
### Pass 3: 深度理解
  ...
```

**Discussion 现状:** 不存在。所有 `ai/` 目录为空。做 UI 壳+空态。

---

### Task 1: 清理 testable.js — 删除 Copy Context actions

**Files:**
- Modify: `paperforge/plugin/src/testable.js:172-187`

- [ ] **Step 1: 从 ACTIONS 数组中删除两个 Copy Context action**

删除 `paperforge-copy-context` 和 `paperforge-copy-collection-context` 两个 action 对象（lines 172-187）。保留其余 4 个 action（sync, ocr, doctor, repair）。注意删除后数组尾部逗号清理。

- [ ] **Step 2: 运行测试确认**

```bash
cd paperforge/plugin && npx vitest run --reporter=verbose
```

预期：所有现有测试通过（ACTIONS 数组长度从 6 变为 4）。

---

### Task 2: 清理 main.js — 删除 dead deep-reading 代码

**Files:**
- Modify: `paperforge/plugin/main.js`

- [ ] **Step 1: 删除 `_renderDeepStatusCard` 方法 (lines 1222-1245)**

- [ ] **Step 2: 删除 `_getPassCompletion` 方法 (lines 1247-1251)**

- [ ] **Step 3: 删除 `_renderDeepPass1Card` 方法 (lines 1253-1280)**

- [ ] **Step 4: 删除 `_extractPass1Content` 方法 (lines 1282-1299)**

- [ ] **Step 5: 删除 `_renderDeepQACard` 方法 (lines 1301-1342)**

- [ ] **Step 6: 更新 `_currentMode` 注释 (line 375)**

将 `'global' | 'paper' | 'collection' | 'deep-reading'` 改为 `'global' | 'paper' | 'collection'`

---

### Task 3: 清理 main.js — 删除 Copy Context UI + 静态 Quick Actions 网格

**Files:**
- Modify: `paperforge/plugin/main.js`

- [ ] **Step 1: 从 `_renderPaperMode` 删除 Copy Context 按钮 (lines 1073-1080)**

删除 ctxBtn 创建和事件监听。

- [ ] **Step 2: 从 `_buildPanel` 删除静态 Quick Actions section (lines 461-465)**

删除 `.paperforge-actions-section` 的创建、`this._actionsGrid` 引用、`this._renderActions()` 调用。

- [ ] **Step 3: 删除 `_renderActions` 方法 (lines 937-949)**

- [ ] **Step 4: 从 `_runAction` 删除两个 Copy Context handler (lines 1478-1526)**

删除 `paperforge-copy-context` 和 `paperforge-copy-collection-context` 的纯 JS clipboard 处理分支。

- [ ] **Step 5: 从 `_renderModeHeader` 删除 deep-reading case (lines 1703-1714)**

- [ ] **Step 6: 从 Plugin.onload 删除 Copy Context 命令注册 (lines 2881-2913)**

- [ ] **Step 7: 从 `_renderNextStepCard` 删除 ready 状态的 Copy Context fallback (lines 1195-1203)**

---

### Task 4: 修复 mode routing — workspace path 检测

**Files:**
- Modify: `paperforge/plugin/main.js:_resolveModeForFile (lines 957-978)`

- [ ] **Step 1: 添加 `_extractZoteroKeyFromPath(filePath)` 辅助方法**

在 `_resolveModeForFile` 前新增方法。逻辑：
1. `dirname = path.dirname(filePath)`
2. `basename = path.basename(dirname)`
3. 正则 `^([A-Z0-9]{8})(\s*-\s*)` 提取第一个 token
4. 返回 zotero_key 或 null

- [ ] **Step 2: 修改 `_resolveModeForFile`**

在 `.md` 分支的 `zotero_key` 检测之后，新增 fallback：如果是 `.md` 且无 frontmatter zotero_key，调用 `_extractZoteroKeyFromPath(filePath)` 检测。如果提取到 key 且在 index 中存在，返回 `{ mode: 'paper', ... }`。

同时在 `ext` 判断的最后（return global 之前），对任意文件类型也做一次 workspace path 检测（用于 fulltext.md 等非 formal note 文件的归属）。

完整逻辑：
```js
_resolveModeForFile(file) {
    if (!file) return { mode: 'global', filePath: null, key: null, domain: null };
    const ext = file.extension;
    const filePath = file.path;

    if (ext === 'base') {
        return { mode: 'collection', filePath, key: null, domain: file.basename };
    }

    if (ext === 'md') {
        const cache = this.app.metadataCache.getFileCache(file);
        const fmKey = cache && cache.frontmatter && cache.frontmatter.zotero_key;
        if (fmKey) {
            return { mode: 'paper', filePath, key: fmKey, domain: null };
        }
    }

    // Workspace path detection for any file
    const wsKey = this._extractZoteroKeyFromPath(filePath);
    if (wsKey && this._findEntry(wsKey)) {
        return { mode: 'paper', filePath, key: wsKey, domain: null };
    }

    return { mode: 'global', filePath, key: null, domain: null };
}
```

---

### Task 5: 重做 Global 视图 — 系统首页

**Files:**
- Modify: `paperforge/plugin/main.js:_renderGlobalMode (lines 1024-1044)`

- [ ] **Step 1: 重写 `_renderGlobalMode`**

新布局：
```text
[Drift Banner]  (hidden by default)
[Library Snapshot]: papers · PDFs ready · OCR done · deep-read done
[System Status]: runtime ✓ · index ✓ · Zotero export ✓ · OCR token ✓
[Issues Panel]: 仅有问题时显示
[Actions]: Open Literature Hub · Sync Library
```

实现：
1. Header + version + 总体状态一行（`系统正常` / `检测到 N 个问题`）
2. Library Snapshot: 从 `_fetchStats` 获取数据，显示 4 个 compact metric pill（papers, PDFs, OCR done, deep-read done）
3. System Status: 4 行 status pill（runtime match/mismatch, index healthy/corrupt, Zotero export detected/missing, OCR token configured/missing）
4. Issues Panel: 当 path_errors > 0 或 runtime mismatch 时显示，包含 `Run Doctor` / `Repair Issues` 按钮
5. Contextual Actions: `Open Literature Hub` (+ 如果全库 queued OCR > 0 显示 `Run OCR`)

- [ ] **Step 2: 删除从 global 的 `_renderOcr` 引用和 OCR section DOM 构建**

不再在 `_renderGlobalMode` 中创建 `this._ocrSection`、`this._ocrBadge`、`this._ocrTrack`、`this._ocrCounts`。

- [ ] **Step 3: 调整 `_renderStats` 中的 metric cards**

从 "Papers / Formal Notes / Exports" 3 张卡改为只保留对用户有意义的总量。数据源改为从 `this._getCachedIndex()` 单次聚合（不再依赖 CLI dashboard --json）。

聚合逻辑（复用 `_fallbackFetchStats` 中的部分代码）：
- papers = items.length
- pdfReady = items.filter(i => i.has_pdf).length
- ocrDone = items.filter(i => i.ocr_status === 'done').length
- deepReadDone = items.filter(i => i.deep_reading_status === 'done').length

---

### Task 6: 重做 Collection/Base 视图 — 批量工作台

**Files:**
- Modify: `paperforge/plugin/main.js:_renderCollectionMode (lines 1344-1410)`

- [ ] **Step 1: 重写 `_renderCollectionMode`**

新布局：
```text
[Header]: 其他 · 150 papers
[Workflow Overview]: 150 total → 148 PDF → 8 OCR → 8 analyze-ready → 1 deep-read
[OCR Pipeline]: 待处理142 | 处理中0 | 已完成8 | 需处理0  [████████░░]  [Run OCR]
[Next Work]: 待OCR: 142 · 可进入精读: 7 · 精读完成: 1
[Issue Summary]: 紧凑版，仅在有问题时展开详情
[Actions]: Sync Library · Run OCR
```

**单次聚合逻辑:**
```js
const items = domainItems;
const total = items.length;
const pdfReady = items.filter(i => i.has_pdf).length;
const ocrDone = items.filter(i => i.ocr_status === 'done').length;
const analyzeReady = items.filter(i => i.ocr_status === 'done' && i.analyze === true).length;
const deepReadDone = items.filter(i => i.deep_reading_status === 'done').length;

// OCR pipeline 4-bucket aggregation
const ocrPending = items.filter(i => ['pending','queued'].includes(i.ocr_status)).length;
const ocrProcessing = items.filter(i => i.ocr_status === 'processing').length;
const ocrDone2 = items.filter(i => i.ocr_status === 'done').length;
const ocrAttention = items.filter(i => ['failed','blocked','done_incomplete','nopdf'].includes(i.ocr_status)).length;
```

- [ ] **Step 2: 实现 `_renderWorkflowOverview` 辅助方法（或在 render 内部直接构建）**

Workflow 漏斗使用 5 个横向串联的 stage pill。

- [ ] **Step 3: 实现 base 内的 OCR Pipeline（复用 `_renderOcr` 的进度条逻辑）**

4-bucket 进度条 + count labels。需要单独的容器引用（不与 global 共享 `this._ocrSection`）。

- [ ] **Step 4: 实现 Issue Summary 紧凑版**

默认显示 "暂无阻塞问题"。有异常时显示 `N 篇 PDF 缺失 · N 篇 OCR 失败 · N 篇 Asset drift`。

- [ ] **Step 5: 重写 Contextual Actions**

base 模式 actions 区域：`Sync Library` + `Run OCR`。维护动作仅在异常时出现。

---

### Task 7: 重做 Per-paper 视图 — 阅读辅助侧栏

**Files:**
- Modify: `paperforge/plugin/main.js:_renderPaperMode + 相关方法 (lines 1047-1204)`

- [ ] **Step 1: 重写 `_renderPaperMode`**

新布局：
```text
[Header]: title · authors · year
[Status Strip]: PDF ✓  OCR ✓  精读 已完成
[文章概览]: Pass 1 一句话总览 / abstract / 空态
[最近讨论]: 最新 session 最近 2-3 条 Q&A / 空态隐藏
[下一步]: 精读已完成 · 可继续讨论
[文件]: Open PDF · Open Fulltext
[技术详情]: 默认折叠（PDF health, OCR raw status, asset state, paths）
```

- [ ] **Step 2: 实现 `_renderPaperStatusStrip(container, entry)`**

删除 lifecycle stepper + health matrix + maturity gauge，压缩为一行 compact status pills：

状态判断：
- PDF: `has_pdf` ? '✓ 可用' : '✗ 缺失'
- OCR: `ocr_status === 'done'` ? '✓ 完成' : `['pending','queued'].includes(ocr_status)` ? '待处理' : `ocr_status === 'processing'` ? '处理中' : '✗ 异常'
- 精读: `deep_reading_status === 'done'` ? '✓ 完成' : '待完成'

- [ ] **Step 3: 实现 `_renderPaperOverviewCard(container, entry)`**

数据源：formal note 正文（通过 `app.vault.read(noteFile)` 读取）

提取逻辑：
1. 如果正文包含 `## 🔍 精读`，在 section 内找 `**一句话总览**` 或 `**文章摘要**`
2. Fallback：显示 entry 中的 `abstract`（如果 frontmatter 有）
3. 最终 fallback：显示 "尚未生成文章概览"

默认只显示短摘要（截断 200 字符），展开按钮显示更多。

- [ ] **Step 4: 实现 `_renderRecentDiscussionCard(container, entry)`**

数据源：`{workspace}/ai/discussion.json`（通过 `app.vault.adapter.read()` 读取）

Discussion.json 格式（来自 2Y9M3ILK 实际数据）：
```json
{ "sessions": [{ "agent":"pf-paper", "model":"deepseek-v4-pro", "qa_pairs": [{"question": "...", "answer": "..."}] }] }
```
回答可能较长（500+ 中文字符）。

渲染：
- 无数据时：整张卡隐藏
- 有数据时：取 `sessions[-1]` 最近 session，展示最近 2-3 个 `qa_pairs`
- 每条显示：`提问：完整问题` + `解答：{截断150字符}... [展开]`
- 点击 [展开] 后显示完整回答（inline expand，不跳转）
- 底部 "查看全部讨论 →" 链接（打开 discussion.md）
- 截断函数：中文按字符计，英文按词计，保证不会在 Obsidian wikilink 中间截断

- [ ] **Step 5: 实现 `_renderPaperNextStepCard(container, entry)`**

简化版下一步推荐（删除 lifecycle maturity 视角）：
```
无 PDF → "等待 PDF"
有 PDF 未入 OCR → "可加入 OCR 队列"
OCR pending/queued/processing → "OCR 进行中"
OCR failed/blocked → "OCR 需要处理"
OCR 完成 精读未完成 → "可开始精读"
精读完成 → "已完成 · 可继续讨论"
```

- [ ] **Step 6: 实现 `_renderPaperFilesRow(container, entry)`**

两个按钮：`Open PDF`（使用 pdf_path wikilink）、`Open Fulltext`（使用 fulltext_path）

- [ ] **Step 7: 实现 `_renderPaperTechnicalDetails(container, entry)`**

默认折叠的 section，包含：PDF health, OCR raw status, asset state, note path, fulltext path。仅在异常时展开或用户手动展开。

---

### Task 8: 更新 CSS 样式

**Files:**
- Modify: `paperforge/plugin/styles.css`

- [ ] **Step 1: 添加新组件样式**

```css
/* Status Strip — compact horizontal pills */
.paperforge-status-strip { ... }
.paperforge-status-pill { ... }  /* pill.ok / pill.warn / pill.fail */

/* Paper Overview Card */
.paperforge-paper-overview { ... }
.paperforge-paper-overview-excerpt { ... }

/* Recent Discussion Card */
.paperforge-discussion-card { ... }
.paperforge-discussion-item { ... }

/* Paper Files Row */
.paperforge-paper-files { ... }

/* Paper Technical Details (collapsible) */
.paperforge-technical-details { ... }
.paperforge-technical-details-toggle { ... }

/* Workflow Overview (base) */
.paperforge-workflow-overview { ... }
.paperforge-workflow-stage { ... }

/* Issue Summary (base + global) */
.paperforge-issue-summary { ... }

/* Library Snapshot (global) */
.paperforge-library-snapshot { ... }

/* System Status (global) */
.paperforge-system-status { ... }
```

- [ ] **Step 2: 清理旧样式**

保持以下样式的兼容性（因为其他模式可能仍复用部分结构）：
- `.paperforge-header`, `.paperforge-mode-badge`
- `.paperforge-paper-view`, `.paperforge-paper-header`, `.paperforge-paper-title`
- `.paperforge-collection-view`
- `.paperforge-metrics`, `.paperforge-metric-card`（global 仍用）
- `.paperforge-ocr-section`, `.paperforge-progress-track`, `.paperforge-ocr-counts`（base 用）

---

### Task 9: 更新 UX contract 文档

**Files:**
- Modify: `docs/ux-contract.md`

- [ ] **Step 1: 更新 Workflow 4 — Dashboard View**

更新 W4-S3 per-paper dashboard 描述：从 "lifecycle stepper, health matrix, next-step recommendation" 改为 "status strip, paper overview, recent discussion, next-step, files row, technical details"。

更新 W4-S2 添加 workflow overview columns 描述。

- [ ] **Step 2: 添加全局和 collection 视图描述**

添加 Workflow 4 新的 sub-steps 描述 global（系统首页）和 collection（批量工作台）。

---

### Task 10: 验证

- [ ] **Step 1: 在 Obsidian 中加载插件**

1. 用 Symbolic link 或直接复制插件文件到 test vault 的 `.obsidian/plugins/paperforge/`
2. 打开 Obsidian，确认 PaperForge 图标出现在左侧 sidebar
3. 点击图标打开 Dashboard

- [ ] **Step 2: 验证 mode routing**

- 不打开任何文件 → global mode ✓
- 打开 `.base` 文件 → collection mode ✓
- 打开 formal note → paper mode ✓
- 打开 `fulltext.md` → paper mode ✓（workspace detection）
- 打开 workshop 目录下其他文件 → paper mode ✓

- [ ] **Step 3: 验证 global 视图**

- Library snapshot 显示计数正确
- System status 显示 runtime/index/Zotero/OCR token 状态
- Issues 仅在有问题时出现
- Actions 有 Open Literature Hub + Sync Library

- [ ] **Step 4: 验证 base 视图**

- Workflow overview 漏斗显示正确
- OCR pipeline 进度条对应当前 base
- Issue summary 紧凑显示
- No Copy Collection Context

- [ ] **Step 5: 验证 paper 视图**

- Status strip 显示正确
- 文章概览从 formal note 提取内容
- Discussion 卡有数据时显示，无数据时隐藏
- 下一步推荐文字正确
- 技术详情默认折叠
- No Copy Context

- [ ] **Step 6: 检查控制台**

确认无 JS 错误、无 console.error。

---

## 非目标（明确不做的）

1. 不做 Copy Context / Copy Collection Context
2. 不做独立 deep-reading dashboard
3. 不让每个 view 挂同一套 Quick Actions
4. 不把 global 做成第二个 collection overview
5. 不在 per-paper 保留 lifecycle stepper / health matrix / maturity gauge
6. 不放所有健康指标全部展开
7. 不在 dashboard 里弥补 skill 检索能力不足
