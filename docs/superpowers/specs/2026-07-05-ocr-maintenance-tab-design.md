# OCR 维护标签页设计

> 设计讨论：2026-07-05
> 状态：设计稿（待评审）

## 核心规则

**用户面向的标签是 action-first。**

维护标签页的标签描述的是用户可以做的操作，不是内部失败状态。
用户不应该看到 "fail"；应该看到 "重试 OCR"。
用户不应该看到 "health red"；应该看到 "重建结果" 或 "可升级旧结果"。

```text
用户看到的标签 = 操作动词 + 对象名词
                重试 OCR
                重建结果
                升级旧结果
                补充 PDF
                配置 OCR
                处理中
                已完成
```

## 设计哲学

**维护标签页只显示用户有活干的情况。**

- 论文正常 → 用户不需要看到它
- 论文有问题但修不了 → 用户不需要看到它（不制造焦虑）
- 论文有问题且能修 → 显示，给操作入口

## 用户可见标签全集

| 内部状态 / 条件 | 用户看到的标签 | 说明 |
|----------------|---------------|------|
| `failed / retryable_error / done_incomplete` 且 `can_redo` | **重试 OCR** | 上次处理未完成，可以重新尝试 |
| `done + health≠green` 且 `can_rebuild` | **重建结果** | 已有 OCR 数据，可重建新版 fulltext |
| `done_degraded` 且 `can_rebuild` | **重建结果** | 可重新生成更稳定的结果 |
| legacy `v1` | **升级旧结果** | 旧版本结果仍可使用，可选升级 |
| `nopdf` | **补充 PDF** | 去 Zotero 添加 PDF（不进 OCR 维护页） |
| `blocked` | **配置 OCR** | 全局配置问题，不按单篇论文刷红 |
| `running / queued / processing` | **处理中** | 不可操作 |
| `pending` | **等待处理** | 不可操作 |
| `done + green` | **已完成** | 不需要操作 |

### 维护标签页 vs Base views 的分工

**维护标签页（设置 → 维护）** = action-first，只显示可操作项

| 操作标签 | 覆盖条件 | 执行 |
|----------|---------|------|
| 重试 OCR | `failed / done_incomplete / retryable_error` 且 `can_redo` | `paperforge ocr redo {key}` |
| 重建结果 | `done_degraded` 且 `can_rebuild` | `paperforge ocr rebuild {key}` |
| 重建结果 | `done + health≠green` 且 `can_rebuild` | `paperforge ocr rebuild {key}` |
| 升级旧结果（可选） | legacy `v1` | `paperforge ocr redo {key}` |

排除规则：
- `done + health≠green` 且 `!can_rebuild` → **不显示**（修不了，忽略）
- `done_degraded` 且 `!can_rebuild` → 改为 retry（重 OCR 也许能改善）

**Base views（.base 文件 / 论文一览）** = 行动导向状态，不藏信息

| 显示 | 条件 | 说明 |
|------|------|------|
| 已完成 | `done + green` | 正常 |
| 等待处理 | `pending` | 等待 OCR |
| 处理中 | `running / queued / processing` | 管线正在处理 |
| 可重建 | `done_degraded / done+health≠green` | 见维护标签 |
| 可重试 | `failed / done_incomplete / retryable_error / fatal_error` | 见维护标签 |
| 补 PDF | `nopdf` | 去 Zotero 补充 PDF |
| 配置 OCR | `blocked` | 配置 PaddleOCR API token |
| 可升级 | legacy `v1` | 可选升级 |

注意：
- `blocked` 在 Base 不显示 "阻塞" 而是写具体原因（如 "无API Key" / "Token失效"），从 `meta.error` 读取
- `nopdf` 放 Base，不是维护能解决的问题（用户需要去 Zotero 加 PDF）

### 老用户升级场景

老用户升级后最容易看到一堆黄/红。legacy v1 不能显示：

```text
失败
质量差
重试失败
```

而应该显示：

```text
可升级旧结果
```

文案：

> 这些是旧版本生成的 OCR 结果，仍然可以使用。你可以在空闲时升级，以获得更好的章节、图表和问答效果。

维护页里单独分组：**可升级旧结果（可选）**，默认折叠，不和真正失败项混在一起。

## 缓存策略

### 文件位置

```
{vault}/System/PaperForge/cache/ocr_maintenance.json
```

### 文件结构

```json
{
  "manifest": {
    "2BB8VM5W": "abc123def456",
    "53B47JM8": "789ghi012jkl"
  },
  "papers": {
    "2BB8VM5W": { ... full OCRMaintenanceRow dict ... },
    "53B47JM8": { ... }
  },
  "cached_at": "2026-07-05T14:30:00"
}
```

manifest 中每个 hash = `sha256(key + status + health + version + recommended_action)`。

### 加载流程

```
打开维护标签页
    │
    ├─ 1. 读本地缓存（存在 → 立即显示）
    │
    ├─ 2. paperforge ocr list --manifest
    │      ↑ 返回 {"2BB8VM5W": "abc123", ...}
    │      ↑ Python 端直接读 meta.json + health.json，极快（~50ms）
    │
    ├─ 3a. manifest 完全匹配 → 结束。刷新图标不动。
    │
    └─ 3b. manifest 有差异 → 刷新图标旋转
           paperforge ocr list --json --keys=KEY1,KEY2
           ↑ 只拉变化的论文完整数据
           合并到缓存 → 局部更新表格 → 停止旋转
```

首次运行（无缓存）需要全量拉取，之后全部增量。

### Python CLI 新增

`paperforge ocr list` 增加两个 flag：

| Flag | 作用 | 返回 |
|------|------|------|
| `--manifest` | 输出全部论文的 hash 字典 | `{"2BB8VM5W": "abc123", ...}` |
| `--keys KEY1 KEY2` | 只输出指定 key 的完整行 | 标准 JSON 数组（同 `--json`） |

### hash 算法

```
hash = sha256(paper_key + "|" + status + "|" + health + "|" + version + "|" + recommended_action)
```

不进 OCR 管线，只读 `meta.json` + `health.json`，比全量 `collect_maintenance_rows` 快很多。

## UI 结构

### 刷新图标

右上角刷新图标：
- 静止 → 数据最新
- 旋转 → 后台正在更新

### 维护表格

| 列 | 说明 |
|----|------|
| ☑ | 勾选（批量操作用） |
| Key | 论文 ID |
| Title | 标题 |
| 建议操作 | `重试 OCR` / `重建结果` / `升级旧结果` |
| 原因 | 一行简述原因 |
| 操作 | [重试] [重建] 按钮 |

工具栏：

| 按钮 | 作用 |
|------|------|
| 全选 | 选中当前筛选项全部 |
| 取消全选 | — |
| ▶ 执行已选 | 批量重试或重建 |

### 分层展示

```
┌──────────────────────────────────────────────┐
│  ✅ 全部正常                                   │  ← 没事干
│                                                 │
│  ── 或 ──                                        │
│                                                 │
│  ⚠️ 3 篇需要处理                                 │
│  ┌───────────────────────────────────────────┐  │
│  │ ☑ │ Key    │ Title   │ 建议操作 │ 原因     │  │
│  │ ☑ │ 2BB... │ Paper A │ 重试OCR  │ API失败   │  │
│  │ ☐ │ 53B... │ Paper B │ 重建结果 │ 质量降级  │  │
│  │ 全选            ▶ 执行已选                  │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ▸ 可升级旧结果（可选） N 篇           ← 折叠     │
│                                                 │
│  ── 全局操作 ──                                  │
│  [重建索引]  [重建记忆库]                        │
└──────────────────────────────────────────────────┘
```

## 与 Layer 2 的关系

质量指标（quality_indicators）和 readiness 评估 **不在维护标签页展示**。

- 维护标签页只需要知道 `health ≠ green` 且 `can_rebuild` → 显示 "重建结果"
- 质量详情在 Dashboard 的 per-paper mode 展示（供读者参考）
- 维护标签页是操作视角，不是诊断视角

## 最终规则（可写入规范）

```text
User-facing labels are action-first.

Maintenance tab labels must describe the action the user can take, not the internal failure state.

Examples:
- retryable failure → "重试 OCR"
- rebuildable degraded result → "重建结果"
- legacy v1 result → "升级旧结果"
- missing PDF → "补充 PDF"
- missing API token → "配置 OCR"

Internal states such as failed, fatal_error, done_degraded, health≠green, degraded_mode_active,
must not be shown directly to users.
```

`paperforge ocr list` 增加两个 flag：

| Flag | 作用 | 返回 |
|------|------|------|
| `--manifest` | 输出全部论文的 hash 字典 | `{"2BB8VM5W": "abc123", ...}` |
| `--keys KEY1 KEY2` | 只输出指定 key 的完整行 | 标准 JSON 数组（同 `--json`） |

### hash 算法

```
hash = sha256(paper_key + "|" + status + "|" + health + "|" + version + "|" + recommended_action)
```

不进 OCR 管线，只读 `meta.json` + `health.json`，比全量 `collect_maintenance_rows` 快很多。

## UI 结构

### 刷新图标

右上角刷新图标：

- 静止 → 数据最新
- 旋转 → 后台正在更新

### 维护表格

| 列 | 说明 |
|----|------|
| ☑ | 勾选（批量操作用） |
| Key | 论文 ID |
| Title | 标题 |
| 状态 | `retry` / `rebuild` 等操作名 |
| 详情 | 一行简述原因 |
| 操作 | [retry] [rebuild] 按钮 |

工具栏：

| 按钮 | 作用 |
|------|------|
| 全选 | 选中当前筛选项全部 |
| 取消全选 | — |
| ▶ 执行已选 | 批量 retry 或 rebuild |

### 分层展示

```
┌──────────────────────────────────────────────┐
│  ✅ 全部正常                                   │  ← 没活干时
│                                                 │
│  ── 或 ──                                        │
│                                                 │
│  ⚠️ 3 篇需要处理                                 │
│  ┌───────────────────────────────────────────┐  │
│  │ ☑ │ Key    │ Title   │ 状态   │ 详情  │  │
│  │ ☑ │ 2BB... │ Paper A │ retry  │ 上次API失败 │  │
│  │ ☐ │ 53B... │ Paper B │ rebuild│ 质量降级 │  │
│  │ 全选            ▶ 执行已选                  │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ── 全局操作 ──                                  │
│  [重建索引]  [重建记忆库]                        │
└──────────────────────────────────────────────────┘
```

### 视觉规范

基于 Obsidian CSS 变量为主，借用 `paperforge/plugin/docs/design/DESIGN.md` 的配色作为语义色：

- success → `#0070f3`（蓝色，非绿色）
- error → `#ee0000`
- warning → `#f5a623`

## 与 Layer 2 的关系

质量指标（quality_indicators）和 readiness 评估 **不在维护标签页展示**。

- 维护标签页只需要知道 `health ≠ green` 且 `can_rebuild` → 显示 rebuild
- 质量详情在 Dashboard 的 per-paper mode 展示（供读者参考）
- 维护标签页是操作视角，不是诊断视角

## 已排除的设计

| 被排除 | 原因 |
|--------|------|
| fatal_error 单独提示 | 用户看不懂，归入 "失败" |
| blocked 在维护标签显示 | 配置问题应在 System Status 或 Base 提示，不是单篇操作能解决 |
| 质量维度详情在维护标签展示 | 维护标签是操作视角，用户不需要看 5 维度分数 |
| 全部论文（含正常的）展开查看 | 不需要给用户制造焦虑 |