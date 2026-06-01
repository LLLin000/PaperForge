# Plugin Release Notes & Manual — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `更新与手册` settings tab with versioned Chinese release notes and external manual links, plus an auto-popup on version change.

**Architecture:** Release notes stored as JSON imported by esbuild into settings.ts. New tab renders collapsible version cards. `main.ts` onload compares `manifest.version` against `settings.last_seen_version` and shows a Modal on mismatch.

**Tech Stack:** TypeScript (Obsidian plugin API), JSON, esbuild bundling

---

### Task 1: Release Notes Data File

**Files:**
- Create: `paperforge/plugin/src/release-notes.json`
- Modify: `paperforge/plugin/src/constants.ts:70-92`

- [ ] **Step 1: Create `release-notes.json` with version 1.5.15 entry**

Write `paperforge/plugin/src/release-notes.json`:

```json
{
  "versions": [
    {
      "version": "1.5.15",
      "date": "2026-06-01",
      "title": "OCR 重新设计 — 全文单一真相源 + Redo 闭环 + 阅读顺序修复",
      "breaking_or_migration": [
        "fulltext 正文现在统一位于 System/PaperForge/ocr/<key>/fulltext.md，工作区 Resources/.../fulltext.md 不再保留为正文副本",
        "OCR Redo 现在会立即重跑 OCR（闭环执行），不再只是标记状态后需要手动再跑一次"
      ],
      "new_features": [
        "新增 OCR Redo 闭环执行：勾选重做后自动删除旧产物 → 强制 do_ocr → 立即重跑 OCR → 成功后写回 ocr_redo:false",
        "设置页新增「更新与手册」标签页，可随时查看版本更新记录与使用手册链接",
        "首次更新时自动弹出更新说明"
      ],
      "fixes": [
        "修复 OCR 双栏阅读顺序混乱：2.5 / Discussion / Introduction 等章节标题和正文错位",
        "修复 Kwon et al. 等叙述句被误判为参考文献，导致正文段落被提前截断并插入 Discussion",
        "修复 Fig.3 / Fig.4 等页首图注和图块被重排逻辑整体后移，导致图文断裂",
        "修复首页（page 1）Abstract / Introduction 排序错乱，METHODS 行跑到 Introduction 后",
        "修复并排 panel（如 Fig.2 的左右两块）未合并为单张 composite figure，被拆成两张独立图片",
        "修复 redo OCR 后工作区 fulltext 未被同步覆盖，导致用户看到的仍是旧乱序版本",
        "Dashboard 现在可以识别 System/PaperForge/ocr/<key>/fulltext.md 路径，打开全文后能切到对应 paper 视图"
      ],
      "recommended_actions": [
        "如果论文是此版本前完成的 OCR，建议对重要论文执行一次「重做OCR」（在 Base 视图勾选 ocr_redo 后点 ribbon Redo 按钮），以修复阅读顺序问题",
        "打开全文请直接使用 Dashboard 的「打开全文」按钮，正文已经统一迁至 System/PaperForge/ocr/ 下"
      ]
    }
  ]
}
```

- [ ] **Step 2: Add `last_seen_version` to `PaperForgeSettings` interface**

In `paperforge/plugin/src/constants.ts`, after line 90:

```typescript
  last_seen_version: string;
```

- [ ] **Step 3: Add default value to `DEFAULT_SETTINGS`**

In `paperforge/plugin/src/constants.ts`, after line 116:

```typescript
  last_seen_version: "",
```

- [ ] **Step 4: Commit**

```bash
git add paperforge/plugin/src/release-notes.json paperforge/plugin/src/constants.ts
git commit -m "feat: add release-notes data and last_seen_version setting field"
```

---

### Task 2: Settings Tab – 更新与手册

**Files:**
- Modify: `paperforge/plugin/src/settings.ts`

- [ ] **Step 1: Import release notes and add tab to tab bar**

At top of `settings.ts`, add import:

```typescript
import releaseNotesData from "./release-notes.json";
```

In `display()` method (around line 92-94), add the third tab:

```typescript
const tabs = [
  { id: "setup", label: t("tab_setup") || "安装" },
  { id: "features", label: t("tab_features") || "功能" },
  { id: "release-notes", label: "更新与手册" },
];
```

In the render switch (around line 117-121):

```typescript
if (this.activeTab === "setup") {
  this._renderSetupTab(tabContents.setup);
} else if (this.activeTab === "features") {
  this._renderFeaturesTab(tabContents.features);
} else {
  this._renderReleaseNotesTab(tabContents["release-notes"]);
}
```

- [ ] **Step 2: Implement `_renderReleaseNotesTab()`**

Add new method after `_renderFeaturesTab()`:

```typescript
_renderReleaseNotesTab(containerEl: HTMLElement) {
  containerEl.createEl("h2", { text: "更新与手册" });

  // --- Version Log ---
  containerEl.createEl("h3", { text: "版本更新记录" });

  const versions = (releaseNotesData as any).versions || [];
  for (const ver of versions) {
    const card = containerEl.createEl("div", { cls: "paperforge-release-card" });
    
    // Header row
    const header = card.createEl("div", { cls: "paperforge-release-header" });
    header.createEl("strong", { text: `v${ver.version} — ${ver.title}` });
    header.createEl("span", { cls: "paperforge-release-date", text: `  (${ver.date})` });

    // Breaking / Migration
    if (ver.breaking_or_migration && ver.breaking_or_migration.length > 0) {
      const section = card.createEl("div", { cls: "paperforge-release-section" });
      section.createEl("div", { cls: "paperforge-release-label", text: "行为变更 / 迁移注意" });
      for (const item of ver.breaking_or_migration) {
        section.createEl("div", { cls: "paperforge-release-item", text: `• ${item}` });
      }
    }

    // New Features
    if (ver.new_features && ver.new_features.length > 0) {
      const section = card.createEl("div", { cls: "paperforge-release-section" });
      section.createEl("div", { cls: "paperforge-release-label", text: "新功能" });
      for (const item of ver.new_features) {
        section.createEl("div", { cls: "paperforge-release-item", text: `• ${item}` });
      }
    }

    // Fixes
    if (ver.fixes && ver.fixes.length > 0) {
      const section = card.createEl("div", { cls: "paperforge-release-section" });
      section.createEl("div", { cls: "paperforge-release-label", text: "修复" });
      for (const item of ver.fixes) {
        section.createEl("div", { cls: "paperforge-release-item", text: `• ${item}` });
      }
    }

    // Recommended Actions
    if (ver.recommended_actions && ver.recommended_actions.length > 0) {
      const section = card.createEl("div", { cls: "paperforge-release-section" });
      section.createEl("div", { cls: "paperforge-release-label", text: "建议操作" });
      for (const item of ver.recommended_actions) {
        section.createEl("div", { cls: "paperforge-release-item", text: `• ${item}` });
      }
    }
  }

  // --- Manual Link ---
  containerEl.createEl("h3", { text: "使用手册" });
  const manualSection = containerEl.createEl("div", { cls: "paperforge-manual-links" });
  const manualLink = manualSection.createEl("a", {
    text: "→ 查看完整使用手册（GitHub）",
    href: "https://github.com/LLLin000/PaperForge/blob/main/docs/user-manual.md",
  });
  manualLink.setAttr("target", "_blank");
}
```

- [ ] **Step 3: Add inline CSS for release notes**

In the CSS block in `display()` (around line 73-87), add:

```css
.paperforge-release-card { border: 1px solid var(--background-modifier-border); border-radius: 6px; padding: 12px; margin-bottom: 12px; }
.paperforge-release-header { margin-bottom: 8px; }
.paperforge-release-date { color: var(--text-muted); font-size: 12px; }
.paperforge-release-section { margin-bottom: 6px; }
.paperforge-release-label { font-weight: 600; color: var(--text-accent); margin-bottom: 2px; font-size: 13px; }
.paperforge-release-item { font-size: 13px; margin-left: 8px; color: var(--text-muted); }
.paperforge-manual-links { margin-top: 8px; }
.paperforge-manual-links a { color: var(--text-accent); }
```

- [ ] **Step 4: Build and verify**

```bash
npm run build
```

Check that `main.js` contains the release notes JSON inlined.

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/src/settings.ts paperforge/plugin/src/release-notes.json
git commit -m "feat: add 更新与手册 settings tab with release notes and manual links"
```

---

### Task 3: Auto-Popup on Version Change

**Files:**
- Modify: `paperforge/plugin/src/main.ts`

- [ ] **Step 1: Add `_checkReleaseNotes()` method in main.ts**

After `_firstLaunchSnapshotMigration()` method, add:

```typescript
private _checkReleaseNotes() {
  const currentVersion = this.manifest.version;
  const seen = this.settings.last_seen_version;
  if (seen === currentVersion) return;

  const releaseNotesData = require("./release-notes.json");
  const versions = releaseNotesData.versions || [];
  const currentEntry = versions.find((v: any) => v.version === currentVersion);

  const { Modal } = require("obsidian");
  class ReleaseNotesModal extends Modal {
    constructor(app: any, entry: any) {
      super(app);
      this._entry = entry;
    }
    private _entry: any;
    onOpen() {
      const { contentEl } = this;
      contentEl.createEl("h2", { text: `PaperForge v${currentVersion} 更新说明` });
      if (this._entry) {
        contentEl.createEl("p", { text: this._entry.title, cls: "paperforge-modal-subtitle" });
        if (this._entry.breaking_or_migration && this._entry.breaking_or_migration.length > 0) {
          contentEl.createEl("h4", { text: "行为变更 / 迁移注意" });
          for (const item of this._entry.breaking_or_migration) {
            contentEl.createEl("p", { text: `• ${item}`, cls: "paperforge-modal-item" });
          }
        }
        if (this._entry.recommended_actions && this._entry.recommended_actions.length > 0) {
          contentEl.createEl("h4", { text: "建议操作" });
          for (const item of this._entry.recommended_actions) {
            contentEl.createEl("p", { text: `• ${item}`, cls: "paperforge-modal-item" });
          }
        }
      } else {
        contentEl.createEl("p", { text: "请前往设置 → 更新与手册 查看完整更新记录。" });
      }
      new (require("obsidian").Setting)(contentEl)
        .addButton(btn => btn.setButtonText("知道了").setCta().onClick(() => {
          this.close();
        }));
    }
    onClose() {
      const { contentEl } = this;
      contentEl.empty();
    }
  }

  new ReleaseNotesModal(this.app, currentEntry).open();
  this.settings.last_seen_version = currentVersion;
  this.saveSettings();
}
```

- [ ] **Step 2: Call `_checkReleaseNotes()` in `onload()`**

In `onload()`, after `this._firstLaunchSnapshotMigration()`, add:

```typescript
this._checkReleaseNotes();
```

- [ ] **Step 3: Build, deploy, and verify**

```bash
npm run build
Copy-Item main.js manifest.json styles.css -Destination ".obsidian/plugins/paperforge/" -Force
```

- [ ] **Step 4: Commit**

```bash
git add paperforge/plugin/src/main.ts
git commit -m "feat: auto-popup release notes modal on plugin version change"
```

---

### Task 4: User Manual Stub

**Files:**
- Create: `docs/user-manual.md`

- [ ] **Step 1: Write minimal Chinese user manual**

Create `docs/user-manual.md`:

```markdown
# PaperForge 使用手册

> 版本：1.5.15+

## 快速开始

1. 安装 PaperForge 插件并完成设置向导
2. 在 Zotero 中配置 Better BibTeX 自动导出
3. 打开 PaperForge Dashboard，点击 Sync 同步文献
4. 对需要全文的论文，确保 do_ocr 为 true，点击 Run OCR
5. OCR 完成后即可在 Dashboard 中打开全文、进行精读

## 核心概念

### fulltext（全文）

每篇论文的 OCR 正文统一存放在：
`System/PaperForge/ocr/<ZoteroKey>/fulltext.md`

这是唯一的正文真相源。Dashboard 的「打开全文」按钮会直接定位到此文件。

### OCR Redo（重做 OCR）

当你需要重新提取某篇论文的全文时：

1. 在领域 Base 的「重做OCR」视图中勾选 `ocr_redo`
2. 点击 ribbon 上的 Redo OCR 按钮
3. 系统会自动：删除旧产物 → 重新上传 PDF → 等待 OCR → 生成新全文

完成后 `ocr_redo` 自动变为 `false`。如果失败，标志会保持 `true`，可以再次重试。

### Dashboard 识别

Dashboard 会自动识别你当前打开的文件所属的论文。支持识别：
- 工作区笔记（`Resources/Literature/<domain>/<key> - Title/<key>.md`）
- OCR 全文（`System/PaperForge/ocr/<key>/fulltext.md`）
- PDF 文件（通过 wikilink 匹配）

## 常用工作流

### 新增论文

1. Zotero 中添加文献 → 自动导出
2. Dashboard → Sync
3. 在 Base 视图中确认 do_ocr 为 true
4. Dashboard → Run OCR
5. OCR 完成后 Dashboard 自动显示「打开全文」按钮

### 精读论文

1. Dashboard 中找到目标论文 → 点击打开全文
2. 在 Agent 中输入 `/pf-deep <key>` 开始精读
3. 精读完成后 Dashboard 状态自动更新

## 目录结构

```
Vault/
├── System/PaperForge/
│   ├── ocr/<key>/          ← OCR 全文、图片、原始 JSON
│   ├── exports/             ← Zotero 导出
│   └── indexes/             ← 文献索引
├── Resources/Literature/
│   └── <domain>/<key> - Title/  ← 论文工作区
│       ├── <key>.md         ← 主笔记
│       └── ai/              ← AI 产物
├── Bases/                   ← Base 视图
└── .obsidian/plugins/paperforge/  ← 插件
```
```

- [ ] **Step 2: Commit**

```bash
git add docs/user-manual.md
git commit -m "docs: add Chinese user manual stub"
```

---

### Task 5: Run Verification

- [ ] **Step 1: Build plugin**

```bash
cd paperforge/plugin && npm run build
```

- [ ] **Step 2: Run Python regression**

```bash
pytest tests/test_sync.py tests/test_ocr.py tests/test_ocr_rendering.py tests/test_ocr_layout_zones.py tests/test_ocr_body_spine.py tests/test_asset_index.py
```
Expected: all pass

- [ ] **Step 3: Run plugin vitest**

```bash
cd paperforge/plugin && npx vitest run tests/zotero-path.test.ts
```
Expected: 2 passed

- [ ] **Step 4: Commit any fixes from verification**

```bash
git commit -m "chore: post-implementation verification"
```
