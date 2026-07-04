# OCR 维护标签页 — Implementation Plan

> Based on: `docs/superpowers/specs/2026-07-05-ocr-maintenance-tab-design.md`
> Status: Draft plan

## 概述

3 个独立 PR，可并行执行：

| PR | 范围 | 依赖 |
|----|------|------|
| **A** | 后端 row model + display contract | 无 |
| **B** | CLI `--manifest` / `--keys` 增量接口 | 无（依赖 A 的 to_dict 扩展，但接口可先做） |
| **C** | Plugin 维护标签 UI + 缓存 | A + B |

---

# PR A: Row Model Display Contract

**文件：**
- `paperforge/worker/ocr_maintenance.py` — `OCRMaintenanceRow` + display 映射 + `compute_maintenance_manifest()`
- `tests/test_ocr_maintenance.py` — 新增（不存在）

## A1. OCRMaintenanceRow 新增 display 字段

在现有 `@dataclass` 底部追加：

```python
display_action: str = "none"
display_label: str = "已完成"
display_reason: str = ""
display_group: str = "hidden"
display_severity: str = "normal"
visible_in_maintenance: bool = False
```

`to_dict()` 加入这 6 个字段。

## A2. `_compute_display_fields()` 函数

新增函数，接收 `(meta, health, has_raw, has_source_meta, status, health_overall, version)`，返回 display 字段 dict。

实现 spec §Row Model 新增字段 → 映射规则的完整 if/elif 链：

```
failed / done_incomplete / retryable_error + can_redo
    → display_action=retry_ocr, label=重试 OCR, group=retry, visible=True

version==v1 + can_redo
    → display_action=upgrade_legacy, label=升级旧结果, group=legacy_optional, visible=True

done_degraded + can_rebuild
    → display_action=rebuild_result, label=重建结果, group=rebuild, visible=True

done + health≠green + can_rebuild
    → display_action=rebuild_result, label=重建结果, group=rebuild, visible=True

done_degraded + !can_rebuild + can_redo
    → display_action=retry_ocr, label=重试 OCR, group=retry, visible=True

nopdf
    → display_action=add_pdf, label=补充 PDF, group=external_action, visible=False

blocked
    → display_action=configure_ocr, label=配置 OCR, group=external_action, visible=False

else
    → display_action=none, label=已完成, group=hidden, visible=False

最后：如果 visible 但 !can_redo 且 !can_rebuild → 改为 hidden
```

`display_reason` 随分支填入中文简述。

## A3. 在 `collect_maintenance_rows()` 中调用

在 `OCRMaintenanceRow(...)` 构造完成后，调用 `_compute_display_fields()`，将返回的 display 字段赋值到 row。

也可以在构造时直接传入——取决于方便程度。

## A4. `compute_maintenance_manifest()` 新增函数

```python
def compute_maintenance_manifest(vault: Path) -> dict[str, str]:
    """Return {key: sha256(concat(...))} for all OCR papers.
    
    Lighter than collect_maintenance_rows — no big file reads.
    Only reads meta.json + health/ocr_health.json + title_by_key.
    """
```

hash 输入字段（按顺序拼接，`|` 分隔）：

```
key | status | health | version | recommended_action |
display_action | display_label | display_reason | display_group |
can_redo | can_rebuild |
error_stage | error_summary | degraded_reasons
```

可复用 `collect_maintenance_rows` 的 paper_dir 遍历逻辑，但跳过 raw blocks / source_metadata 等大文件读取。

## A5. 测试

`tests/test_ocr_maintenance.py`：

| # | 场景 | 预期 |
|---|------|------|
| 1 | failed + can_redo | `retry_ocr` / `重试 OCR` / group=retry / visible=True |
| 2 | done_degraded + can_rebuild | `rebuild_result` / `重建结果` |
| 3 | done + health=red + can_rebuild | `rebuild_result` / 同上 |
| 4 | version=v1 + can_redo | `upgrade_legacy` / `升级旧结果` / group=legacy_optional |
| 5 | done_degraded + !can_rebuild + can_redo | `retry_ocr` |
| 6 | done_degraded + !can_rebuild + !can_redo | hidden |
| 7 | done + health≠green + !can_rebuild + !can_redo | hidden |
| 8 | nopdf | `add_pdf` / visible=False |
| 9 | blocked | `configure_ocr` / visible=False |
| 10 | done + green | `none` / hidden |
| 11 | pending / running / queued | `none` / hidden |
| 12 | display_reason 不为空 | 至少 3 个场景有中文原因 |
| 13 | manifest hash 一致性 | 同一输入产出相同 hash |
| 14 | manifest hash 对 display 字段敏感 | display_label 变化 → hash 变化 |

---

# PR B: CLI `--manifest` / `--keys`

**文件：**
- `paperforge/cli.py` — 参数定义
- `paperforge/commands/ocr.py` — `_run_ocr_list()` 扩展
- `paperforge/worker/ocr_maintenance.py` — （PR A 已加 `compute_maintenance_manifest`）
- `tests/test_ocr_maintenance.py` — 追加 CLI 测试

## B1. CLI 参数

在 `list_parser` 追加：

```python
list_parser.add_argument("--manifest", action="store_true",
    help="Output key→hash manifest instead of full rows")
list_parser.add_argument("--keys", nargs="*", metavar="KEY",
    help="Only output rows for these specific keys")
```

## B2. `_run_ocr_list()` 扩展

```python
def _run_ocr_list(vault, json_output=False, output_file=None,
                   manifest=False, keys=None):
```

### --manifest 模式
- 如果 `manifest=True`：
  - 调用 `compute_maintenance_manifest(vault)` 获取 `{key: hash}` dict
  - JSON 输出到 stdout 或 output_file
  - 不执行 `collect_maintenance_rows()`（快很多）

### --keys 过滤模式
- 如果提供了 `keys`（list[str]）：
  - 调用 `collect_maintenance_rows(vault)` 获取全部 rows
  - 只输出 key 在 `keys` 中的 rows
  - 保持 JSON 完整格式

### 优先级：--manifest 优先于 --keys

逻辑：

```
if manifest:
    output manifest dict
else:
    full = collect_maintenance_rows(vault)
    if keys:
        full = [r for r in full if r.key in keys]
    if json_output:
        output [r.to_dict() for r in full]
```

## B3. 测试

| # | 场景 | 预期 |
|---|------|------|
| 1 | `paperforge ocr list --manifest` | 输出 JSON dict，key=hash |
| 2 | manifest 包含 display 字段变化 | hash 不一致时触发 |
| 3 | `paperforge ocr list --json --keys KEY1 KEY2` | 只输出 2 行 |
| 4 | `--keys` 有不存在的 key | 忽略，不报错 |
| 5 | `--manifest` 速度测试 | 应比全量快 10x+ |
| 6 | `_run_ocr_list` 签名兼容 | 不破坏已部署的 json_output / output_file |

---

# PR C: Plugin 维护标签 UI + 缓存

**文件：**
- `paperforge/plugin/src/services/ocr-maintenance-ui.ts` — 扩展
- `paperforge/plugin/src/settings.ts` — `_renderMaintenanceTab()` 重写
- `paperforge/plugin/i18n.ts` — 中文文案
- `tests/ocr-maintenance-ui.test.ts` — 追加

## C1. 服务层扩展

`ocr-maintenance-ui.ts`：

### 新增类型

```typescript
export type DisplayAction = "retry_ocr" | "rebuild_result" | "upgrade_legacy" | "add_pdf" | "configure_ocr" | "none";
export type DisplayGroup = "retry" | "rebuild" | "legacy_optional" | "external_action" | "hidden";
export type DisplaySeverity = "actionable" | "optional" | "external" | "normal";

export interface MaintenanceDisplayRow {
  key: string;
  title: string;
  display_action: DisplayAction;
  display_label: string;
  display_reason: string;
  display_group: DisplayGroup;
  visible_in_maintenance: boolean;
  // 后端已有字段
  can_redo: boolean;
  can_rebuild: boolean;
}
```

### `categorizeMaintenanceRow()` 保持兼容

现有函数已返回 `{category, label, primaryAction, reason}`。保持它运行，新增一个对等函数给新 UI 用。

可以考虑加一个适配层，或者直接让新 UI 解析 `display_action/display_group`。

决策：**新 UI 直接读 `display_action` / `display_group`**，不通过 `categorizeMaintenanceRow()`。

## C2. 缓存管理

### `readMaintenanceCache()` / `writeMaintenanceCache()`

```typescript
interface MaintenanceCache {
  manifest: Record<string, string>;
  papers: Record<string, MaintenanceDisplayRow>;
  cached_at: string;
}
```

路径：`{vault}/System/PaperForge/cache/ocr_maintenance.json`

### 刷新逻辑

```typescript
async function refreshMaintenanceData(
  vaultPath: string,
  pythonExe: string,
  extraArgs: string[],
  currentCache: MaintenanceCache | null
): Promise<{ data: MaintenanceDisplayRow[]; manifest: Record<string, string>; changed: boolean }>
```

1. execFile `paperforge ocr list --manifest`
2. 比对 manifest：
   - 一致 → 返回缓存数据，changed=false
   - 不一致 → 找出变化 key，execFile `paperforge ocr list --json --keys=K1,K2`
3. 合并到缓存并写入文件
4. 返回完整数据 + changed

## C3. `_renderMaintenanceTab()` 重写

### 三阶段渲染

```typescript
// Phase 1: 读缓存 → 立即显示
const cache = readMaintenanceCache(vaultPath);
if (cache) {
  renderTable(filterVisible(cache.papers));
}

// Phase 2: 后台刷新
const result = await refreshMaintenanceData(...);
if (result.changed) {
  updateTable(result.data);      // 局部更新
  stopSpin();                    // 停转
}
// Phase 3: 首次无缓存
if (!cache) {
  const result = await fullFetch(...);
  renderTable(result.data);
  writeCache(result);
}
```

### 分组渲染

```
组 1: retry      → 标题 "需要重试"
组 2: rebuild    → 标题 "可重建结果"
组 3: legacy     → 标题 "可升级旧结果（可选）"（默认折叠 <details>）
```

每组的表格：

| ☑ | Key | Title | 建议操作 | 原因 | 操作 |
|---|---|---|---|---|---|
| ☑ | 2BB... | 标题 | 重试 OCR | API 失败 | [重试] |
| ☐ | 53B... | 标题 | 重建结果 | 质量降级 | [重建] |

工具栏：全选 → 取消全选 → ▶ 执行已选

### 操作执行

- "重试" → `execFile(pythonExe, ["-m", "paperforge", "ocr", "redo", ...keys])`
- "重建" → `execFile(pythonExe, ["-m", "paperforge", "ocr", "rebuild", ...keys])`
- "升级" → `execFile(pythonExe, ["-m", "paperforge", "ocr", "redo", ...keys])`（与重试相同命令）

### 所有正常 / 无操作的论文不进表格

`visible_in_maintenance === false` 的一律不渲染（含 `nopdf`, `blocked`, `done+green`, `pending` 等）。

## C4. 刷新图标

在设置标签页的 tab bar 区域，维护标签按钮旁加一个刷新图标。

```css
.paperforge-maintenance-refresh {
  width: 16px; height: 16px;
  display: inline-block;
  vertical-align: middle;
  transition: transform 0.3s;
}
.paperforge-maintenance-refresh--spinning {
  animation: spin 1s linear infinite;
}
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
```

- `spin()` / `stopSpin()` 控制
- 无缓存首次加载 → 不出现（整个页面在加载，不需要额外指示）
- 缓存存在 + manifest 有变化 → 旋转 → 更新完成 → 停止

## C5. i18n 新增文案

```typescript
"maintenance_group_retry": "需要重试",
"maintenance_group_rebuild": "可重建结果", 
"maintenance_group_legacy": "可升级旧结果（可选）",
"maintenance_retry_btn": "重试",
"maintenance_rebuild_btn": "重建",
"maintenance_upgrade_btn": "升级",
"maintenance_all_good": "✅ 全部正常",
"maintenance_refreshing": "正在更新...",
```

## C6. 测试

`tests/ocr-maintenance-ui.test.ts` 追加：

| # | 场景 | 预期 |
|---|------|------|
| 1 | `visible_in_maintenance=false` 不进表格 | 过滤正确 |
| 2 | 3 组分组渲染 | retry / rebuild / legacy 分开 |
| 3 | 批量操作只执行 visible 的论文 | 不操作 hidden 的 |
| 4 | 缓存读写 | manifest 一致时不触发刷新 |
| 5 | hash 不匹配触发增量拉取 | 只拉变化的 key |
| 6 | 刷新图标状态切换 | 旋转 / 静止 |

---

## 执行顺序

```
PR A ──→ PR C
  │         ↑
  ↓         │
PR B ───────┘
```

- PR A 和 PR B 可并行（无代码冲突，修改不同函数）
- PR C 需要 A（display 字段存在）和 B（manifest/keys CLI 存在）
- PR C 开始前，先合并 A 和 B 到 master
