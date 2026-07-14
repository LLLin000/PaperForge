# Maintenance Issue Reporting — 原型设计说明

**日期:** 2026-07-15
**方式:** Issue #72
**配套原型:** `2026-07-14-maintenance-issue-reporting.html`
**涉及方式:** #69 (能力状态模型), #70 (托管运行时架构), #71 (Control Center 原型)
**文件路径:** `docs/prototypes/2026-07-14-maintenance-issue-reporting.html`

---

## 1. 设计目标

原生原型用于探索和维护导航 **actionable-only 维护收件箱** 概念验证：

1. 只显示用户需要关心的维护项（不显示"正常"项，不制造焦虑）
2. 每个维护项提供明确的可操作入口按钮
3. 展示能力状态模型（availability × activity × attention）
4. 提供隐私安全的 Issue 报告流程（可编辑草稿 + 显式打开 GitHub）
5. 确定性的场景控制方便评审

### 非目标

- 不是插件代码，不涉及真实数据加载
- 不替代生产维护标签页的实现
- 不涉及缓存策略、TTL 刷新、后端探测
- 不涉及批量操作（全选/执行已选）

---

## 2. 对应的能力状态合同关系（#69）

本原型严格按照 [2026-07-14-capability-state-action-contract.md](../research/2026-07-14-capability-state-action-contract.md) 定义的三维能力模型：

### 2.1 可用性轴 (Availability)

| 状态 | 原型场景 | 显示含义 |
|------|---------|---------|
| `needs_action` | 过期 OCR、OCR 失败、不合格 OCR | 黄色提示，可操作 |
| `unavailable` | 索引损坏 | 红色提示，需要修复 |
| `ready` | 全部正常 | 不显示任何维护项 |

### 2.2 活动轴 (Activity)

`running` 状态下，物品保持可见但按钮变为 `disabled` 并显示"处理中"。
进展栏和进度文本也一同显示。**Running 不隐藏 attention：** 即使在运行也保持显示。

### 2.3 注意力轴 (Attention)

- 普通状态保持安静，底部和徽章显示计数
- `running` 从不掩盖 warning/error 徽章（合同 §2 明确）

### 2.4 单一主要行动不变量

每个模块至多一个 `action.primary`。原型中：
- `needs_action` → `rebuild_derived` / `redo` / `investigate`
- `unavailable` → `restore_backup`
- `ready` → 无操作，收件箱为空

---

## 3. 维护投影规则（#69 §8）

维护是派生视图（Derived View），不是独立模块。本原型通过汇总各模块状态来模拟：

- **入口条件：** 模块从 `ready` / `unknown` 转换成 `unavailable` / `needs_action`
- **出口条件：** 用户执行操作 → 项消失 → 如果所有项都消失，回到`全部正常`
- **空状态：** `0 项需要处理` → 显示空状态引导

---

## 4. 破坏性操作确认流程（#69 §5, #68）

继承自 Desktop Runtime Recovery Patterns 研究中的三阶恢复模型（§4.2.1）：

| 操作 | 场景 | 确认要求 | 生效范围 |
|------|------|---------|---------|
| `rebuild_derived` | 过期 OCR | 不需要（非破坏性） | selection |
| `redo` | OCR 失败 | 需要确认 | paper |
| `restore_backup` | 索引损坏 | 需要确认 | module |

确认弹窗显示：
- **标题：** `确认 <操作名>`（保留用户看到的操作描述）
- **确认提示：** 描述后果
- **破坏范围：** `范围: <scope> · <effect>`

---

## 5. 隐私安全 Issue 报告流程（#42, #69 §9）

直接继承 VS Code（预填 Issue Report）和 Docker Desktop（诊断导出供本地检查再提交）的模式。

### 流程

1. 用户点击 "报告 Issue"
2. 弹窗显示 **包含的字段**（模块、reason.code、reason.text、error_summary、key）
3. 弹窗显示 **排除的字段**（论文标题、vault 路径、zotero 路径、配置值、API Key），全部标记为 `[redacted]`
4. 用户可以在文本框中任意编辑草稿
5. **⚠ 显式警告：** "草稿仅本地展示，不会自动提交。编辑完成后，点击下方按钮再 Github 新建 Issue。"
6. 用户点击"在 GitHub 新建 Issue" → `window.open(github.com/LLLin000/PaperForge/issues/new?...)` → 用户仍需在 GitHub 页面手动点击 "Submit new issue"
7. 点击后不关闭弹窗（方便用户继续编辑）
8. 草稿不上传、不提交 API、不包含 token

### 不变量

- ❌ NEVER 自动打开 GitHub（用户必须显式点击按钮）
- ❌ NEVER 自动提交 Issue
- ❌ NEVER 上传任何数据
- ❌ 不包含 token、API key、本地路径、环境变量

---

## 6. UI 设计决策

### 6.1 设计语言

继承 Vercel 灰阶设计体系（来自 DESIGN.md）：

| Token | 使用位置 | 值 |
|-------|---------|-----|
| ink | 标题、主文本 | #171717 |
| body | 辅助文本、原因 | #4d4d4d |
| mute | 元信息、徽章数字 | #888888 |
| hairline | 卡片描边 | #ebebeb |
| link | 主要操作按钮 | #0070f3 |
| error | 破坏性操作/严重状态 | #ee0000 |
| warning | 警告状态 | #f5a623 |

### 6.2 组件映射

- **场景工具栏：** pill 样式按钮（符合 nav-link 组件定义）
- **物品卡片：** card-marketing-large 变体（圆角 8px, padding 16px, hairline 描边）
- **空状态：** ex-empty-state-card（48px 圆形图标 + 标题 + 描述）
- **确认弹窗：** ex-modal-card（圆角 12px, shadow-md, 最大宽 480px）
- **浮动层：** 半透明 ink 遮罩（rgba(23,23,23,.4)）

### 6.3 响应式

- 768px 断点：折成单列堆叠布局
- 标题改为纵向排列
- 场景栏改为堆叠
- 物品卡片：信息区域和按钮纵向排列

### 6.4 无状态

- 没有外部依赖（vanilla HTML/CSS/JS）
- 直接打开 HTML 文件即可完整工作
- 不需要服务端、WebSocket、localStorage

---

## 7. 场景设计理由

| 场景 | 测试的能力模型 | 覆盖的操作类型 |
|------|---------------|---------------|
| 过期 OCR 结果 | `needs_action` + `idle` | 非破坏性的 `rebuild_derived` |
| OCR 失败 | `needs_action` + `idle` | 破坏性的 `redo`（需确认） |
| 索引损坏 | `unavailable` + `idle` | 破坏性的 `restore_backup`（模块级） |
| 正在重建 | `needs_action` + `running` | 混合状态（一个在运行 + 一个待处理） |
| → 解决一项 | 从收件箱移除项 | 跳过 running 项，只解决 idle 项 |
| 质量不合格 | `needs_action` + 可报告 Issue | Issue 草稿流（包含/排除预览） |
| 全部正常 | `ready` | 空状态 |

---

## 8. 从 #69/#70 到本原型的关键路径

```
#69 capability contract              #70 managed runtime
│                                     │
│  ┌──────────────────────────────────┘
│  │
│  ▼
│  Action verbs & reason codes
│  Maintenance projection rules
│  Destructive confirmation contract
│  Issue draft privacy rules
│
│  ┌──────────────────────────────────┐
│  │                                  │
│  ▼                                  │
│  #71 Control Center Prototype       │
│  (module cards from envelope)       │
│                                     │
│  ▼                                  │
│  #72 Maintenance Issue Reporting    │
│  (actionable inbox + Issue draft)   │
```

---

## 9. 浏览器验证步骤

### 9.1 快速验证（桌面端，~1200px 宽）

1. 打开 `docs/prototypes/2026-07-14-maintenance-issue-reporting.html`
2. **初始状态：** 看到 "全部正常" 空状态，徽章显示 "0"
3. **点击 "过期 OCR 结果"：** 看到 1 条物品，有 "重建" 徽章和 "重建结果" 按钮（蓝色 primary）
4. **点击 "重建结果"：** 物品消失，回到空状态
5. **点击 "OCR 失败"：** 看到 "重试" 徽章和 "重试 OCR" 按钮
6. **点击 "重试 OCR"：** 弹出确认弹窗（显示范围："paper"级破坏性）
7. **按 Esc** 关闭弹窗。再次点击 "重试 OCR" → **点击 "确认执行"** → 物品消失
8. **点击 "索引损坏"：** 看到 "损坏" 徽章、"恢复备份" 按钮。点击 → 看到模块级确认
9. **点击 "正在重建"：** 看到 2 条物品。第一条标记 "运行中" 有进度条和 "处理中" 禁用按钮；第二条有 "重建结果" 按钮
10. **点击 "→ 解决一项"：** 运行中物品保留，非运行中的物品被移除
11. **点击 "质量不合格"：** 看到 "质量不合格" 徽章和 "报告 Issue" 按钮
12. **点击 "报告 Issue"：** 弹出 Issue 草稿面板
13. **查看"包含的字段"和"排除的字段"：** 标题、路径、配置等已脱敏
14. **点击 "在 GitHub 新建 Issue"：** 新标签页打开 GitHub Issues，不自动提交，草稿面板保持打开
15. **按 Esc** 关闭草稿面板
16. **点击 "重置"：** 回到空状态

### 9.2 响应式验证（768px 宽）

1. 调整浏览器窗口到 768px 或使用 DevTools 的设备仿真
2. 验证场景栏折为纵向布局
3. 验证物品卡片堆叠排列
4. 确认所有操作按钮仍可点击
5. 确认弹窗仍可读（文本自适应）

### 9.3 键盘验证

1. `Tab` 导航所有场景按钮和操作按钮
2. 确认所有 `:focus-visible` 出现蓝色（`--link`）光环
3. `Enter` 激活焦点按钮
4. `Esc` 关闭弹窗和草稿面板
5. 弹出确认弹窗时焦点自动移到"确认执行"按钮

### 9.4 隐私安全验证

1. 点击 "报告 Issue" → 确认草稿面板没有用户路径、文件内容、API key
2. 确认"排除的字段"区域显示 `[redacted]`
3. 确认草稿面板有关于"不会自动提交"的警告
4. 确认 "在 GitHub 新建 Issue" 按钮行为：在真实浏览器中打开新标签页，不在当前标签页导航
5. 确认 URL 参数仅包含 `title` 和 `body`（不包含 token/secret）

---

## 10. 已知限制

| 限制 | 描述 | 计划解决方案 |
|------|------|------------|
| 数据完全模拟 | 没有真正的后端探测 | 集成时替换为真实 envelope |
| 无缓存层 | 每次重新加载都重置状态 | #71 阶段加入缓存 |
| 无批量操作 | 不支持全选/执行已选 | #73 或后续迭代 |
| 仅限桌面焦点 | 没有针对移动端布局优化 | 后续可选 |
| 无 i18n | 全部中文硬编码 | 后续接入 `t()` 系统 |
| 无动画 | 移除物品时使用过渡过度动画 | 后续添加入/出动画 |

## 11. 评审修复记录

### 11.1 Fix 1 — 模态框焦点陷阱 + 背景 inert + 焦点恢复

**问题：** 弹窗打开后没有焦点陷阱，Tab 可以跳出到背景内容；没有 inert 阻断，键盘用户（屏幕阅读器）可以访问背景元素；关闭后焦点没有回到触发元素。

**方案：**
- `openModal(overlay)`：设置 `.page-wrap` 的 `inert = true`、保存 `lastFocusedElement`、打开弹窗
- `closeModal(overlay)`：移除 `.open`、恢复 `inert = false`、将焦点恢复到 `lastFocusedElement`
- `closeAnyOverlay()`：一次性关闭所有可能的弹窗并恢复 inert 和焦点
- 全局 `keydown` 监听 Tab 键：当焦点在弹窗第一个/最后一个可聚焦元素时，循环回到另一端的 `preventDefault` + `focus()`
- 使用 `openModal` 时主动关闭另一个弹窗，确保任何时候只有一个弹窗可见

**验证结果：** inert 在弹窗打开时设置，关闭时恢复；Escape 调用 `closeAnyOverlay()` 正确关闭所有弹窗并恢复焦点。

### 11.2 Fix 2 — Issue 标题可编辑 + 在 URL 中使用编辑后标题

**问题：** 原标题在 draft-body 中硬编码，用户无法在标题区域编辑，GitHub URL 中 title 参数是固定的。

**方案：**
- 在 Issue 草稿面板头部添加可编辑的 `<input type="text" id="draft-title-input">`
- `showIssueDraft()` 时预填入 `[PaperForge] OCR quality unacceptable — <key>`
- 用户可自由编辑标题文本
- `draft-open-github` 点击时从 `draft-title-input.value` 读取标题，传入 URL 参数
- 焦点默认移到标题输入框，用户可以直接开始编辑

**验证结果：** 标题输入框存在（type="text"），预填入正确值，URL 使用编辑后标题。

### 11.3 Fix 3 — 索引损坏确认文本明确替换内容与保留数据

**问题：** 原确认提示 "用最近的备份替换当前的索引" 没有说明哪些数据会替换、哪些保留。

**方案：**
- 新确认文本：*"将替换损坏的 memory.db 索引文件为最近备份。原始 PDF 来源、OCR 派生数据、论文元数据和设置配置均不受影响。如备份也损坏，后续需完全重建搜索索引。"*
- 明确列出被替换的内容：`memory.db` 索引文件
- 明确列出保留的内容：原始 PDF 来源、OCR 派生数据、论文元数据、设置配置
- 描述后续故障模式：如备份也损坏，需完全重建

**验证结果：** 确认文本和范围文本均已包含上述信息。

### 11.4 Fix 4 — `[hidden]` 样式权重修复

**问题：** 浏览发现两个弹窗的遮罩同时可见。原因是 `.open { display: flex }` 选择器权重 > HTML `[hidden]` 属性，导致 `hidden` 被覆盖。

**方案：**
- 在 CSS 顶部添加 `[hidden]{display:none!important}`
- `openModal()` 主动关闭另一个弹窗（双重保险）

**验证结果：** 打开草稿面板时确认弹窗不可见，打开确认弹窗时草稿面板不可见。两个弹窗不会同时出现。
