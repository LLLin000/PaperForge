# OCR 维护标签页 — Implementation Plan (v2)

> Based on: `docs/superpowers/specs/2026-07-05-ocr-maintenance-tab-design.md`
> Review: 7.8/10 → P0/P1 fixes applied. Status: Ready for execution.

## 执行顺序

```
PR A → PR B → PR C → PR D (可选)

PR A: 后端 display contract + manifest
PR B: CLI keyed actions + manifest/keys
PR C: Plugin 维护标签 UI + 缓存
PR D: Base view action labels（可选，见下方讨论）
```

**⚠️ 不是独立 PR。A 必须先合并，B 基于 A，C 依赖 A+B。**
如果想 A/B 并行，PR B 需要自己 stub manifest 函数，不建议。

---

## Non-goals（本轮不做）

- **Layer 2 质量指标展示** — quality_indicators、user_readiness 不在维护标签展示
- **Dashboard per-paper quality detail** — 留给后续 Layer 3
- **Base view action label migration** — 本轮 **不** 改 Base views

> 关于 Base：plan 只实现维护标签页。PR A 的 `display_label` 可以被 Base 未来消费，但本 plan 不包含 Base 改造。Base 仍然使用 `status/health` 原始值。

如果要求在 Base 也避免显示 `failed/degraded`，需要加 PR D。

---

# PR A: 后端 display contract + manifest

**文件：**
- `paperforge/worker/ocr_maintenance.py` — `OCRMaintenanceRow` + `_compute_display_fields()` + `compute_maintenance_manifest()`
- `tests/test_ocr_maintenance.py` — 新增（现存无）

## A1. Row model 新增 display 字段

在 `OCRMaintenanceRow` dataclass 底部追加：

```python
display_action: str = "none"         # retry_ocr / rebuild_result / upgrade_legacy / add_pdf / configure_ocr / none
display_label: str = "已完成"        # 用户可见的中文标签（fallback；前端可用 i18n 覆盖）
display_label_key: str = ""          # i18n key，前端优先用这个
display_reason: str = ""             # 用户可见的中文原因（一行）
display_reason_key: str = ""         # i18n key，前端优先用这个
display_group: str = "hidden"        # retry / rebuild / legacy_optional / external_action / hidden
display_severity: str = "normal"     # actionable / optional / external / normal
visible_in_maintenance: bool = False
```

`to_dict()` 加入全部新增字段。

## A2. `_compute_display_fields()` — 映射规则

新增函数，签名：

```python
def _compute_display_fields(
    status: str,
    health_overall: str,
    version: str,
    can_redo: bool,
    can_rebuild: bool,
    error_stage: str = "",
    error_summary: str = "",
    degraded_reasons: list[str] | None = None,
) -> dict:
```

### 规则（顺序敏感，第一条匹配即返回）

```python
# ── ready 状态：不显示在维护页，但 label 对 Base 正确 ──
if status in ("pending",):
    return {display_action="none", label="等待处理", group="hidden", severity="normal", visible=False}

if status in ("running", "queued", "processing"):
    return {display_action="none", label="处理中", group="hidden", severity="normal", visible=False}

# ── retry: 需要重跑的 ──
# 覆盖真实管线中所有表示失败的状态值
if status in ("failed", "error", "fatal_error", "done_incomplete", "retryable_error") and can_redo:
    return {display_action="retry_ocr", label="重试 OCR", group="retry", severity="actionable", visible=True,
            reason="上次处理未完成，可以重新尝试"}

# ── legacy: 可选升级 ──
if version == "v1" and can_redo:
    return {display_action="upgrade_legacy", label="升级旧结果", group="legacy_optional", severity="optional", visible=True,
            reason="旧版本结果仍然可用，升级后可获得更好的章节、图表和问答效果"}

# ── rebuild: 可重建 ──
# 注意：health ≠ green 必须限于已知的 yellow/red
# health="-" / "" / "unknown" / missing 不能当异常
_health_is_bad = health_overall in {"yellow", "red"}
if status == "done_degraded" and can_rebuild:
    return {display_action="rebuild_result", label="重建结果", group="rebuild", severity="actionable", visible=True,
            reason="已有OCR数据，可重建获得更稳定的结果"}

if status == "done" and _health_is_bad and can_rebuild:
    return {display_action="rebuild_result", label="重建结果", group="rebuild", severity="actionable", visible=True,
            reason="已有OCR数据，可重建新版结果"}

if status == "done_degraded" and not can_rebuild and can_redo:
    return {display_action="retry_ocr", label="重试 OCR", group="retry", severity="actionable", visible=True,
            reason="降级结果无法重建，可重新OCR"}

# ── 不进维护页的外部行动 ──
if status == "nopdf":
    return {display_action="add_pdf", label="补充 PDF", group="external_action", severity="external", visible=False,
            reason="请去 Zotero 添加 PDF 文件"}

if status == "blocked":
    return {display_action="configure_ocr", label="配置 OCR", group="external_action", severity="external", visible=False,
            reason="请配置 PaddleOCR API Token"}

# ── 正常 / 其他 → 已完成 ──
if status == "done" and not _health_is_bad:
    return {display_action="none", label="已完成", group="hidden", severity="normal", visible=False}

# ── 排除规则：修不了的不显示 ──
# done + health_bad 但 !can_rebuild 且 !can_redo → hidden
# done_degraded 但 !can_rebuild 且 !can_redo → hidden
if not can_redo and not can_rebuild:
    return {display_action="none", label="已完成", group="hidden", severity="normal", visible=False}

# ── fallback ──
return {display_action="none", label="已完成", group="hidden", severity="normal", visible=False}
```

### 关键边界规则

1. `health≠green` 必须显式只认 `health_overall in {"yellow", "red"}`。`-` / `""` / `"unknown"` / missing 不算"可重建"
2. `pending/running/queued/processing` 的 `display_label` 是 `"等待处理"` / `"处理中"`，不是 `"已完成"`
3. `status` 覆盖 `error`（现有 pipeline 会写 `meta["ocr_status"] = "error"`）

## A3. 在 `collect_maintenance_rows()` 中集成

在 row 构造后调用 `_compute_display_fields()` 赋值。

## A4. `compute_maintenance_manifest()` — 轻量 manifest

```python
def compute_maintenance_manifest(vault: Path) -> dict[str, str]:
    """Return {key: sha256} for all OCR papers.
    Only reads meta.json + health/ocr_health.json.
    Does NOT read source_metadata, raw blocks, or formal-library index.
    """
```

hash 输入字段（`|` 分隔，顺序固定）：

```
key | status | health | version | recommended_action
  | display_action | display_group | display_severity | display_reason_key
  | can_redo | can_rebuild
  | error_stage | error_summary | degraded_reasons
```

**`display_label` 和 `display_reason` 不进 hash**，因为中文文案变化不应导致全量缓存过期。
用 `display_reason_key` 或 `display_action` 代替。

## A5. 测试

`tests/test_ocr_maintenance.py`：

| # | 场景 | 预期 |
|---|------|------|
| 1 | `failed` + `can_redo` | `retry_ocr` / `重试 OCR` / group=retry / visible=True |
| 2 | `error` + `can_redo` | `retry_ocr`（覆盖真实管线状态） |
| 3 | `done_degraded` + `can_rebuild` | `rebuild_result` / `重建结果` |
| 4 | `done` + health=red + `can_rebuild` | `rebuild_result` |
| 5 | `done` + health=yellow + `can_rebuild` | `rebuild_result` |
| 6 | `done` + health=`"-"` + `can_rebuild` | `none` / hidden（不属于已知异常） |
| 7 | `done` + health=`"unknown"` + `can_rebuild` | `none` / hidden |
| 8 | version=v1 + `can_redo` | `upgrade_legacy` / `升级旧结果` / group=legacy_optional |
| 9 | `done_degraded` + `!can_rebuild` + `can_redo` | `retry_ocr` |
| 10 | `done_degraded` + `!can_rebuild` + `!can_redo` | `none` / hidden |
| 11 | `done` + health=red + `!can_rebuild` + `!can_redo` | `none` / hidden |
| 12 | `nopdf` | `add_pdf` / visible=False |
| 13 | `blocked` | `configure_ocr` / visible=False |
| 14 | `pending` | `等待处理` / hidden（label 对 Base 正确） |
| 15 | `running` / `queued` / `processing` | `处理中` / hidden |
| 16 | `done` + green | `已完成` / hidden |
| 17 | display_reason 不含内部诊断词 | assert no "failed"/"degraded"/"health"/"质量降级"/"fatal" |
| 18 | manifest hash 一致性 | 同一输入 → 相同 hash |
| 19 | manifest hash 对 display_action 敏感 | 改 display_action → hash 变 |
| 20 | manifest 不依赖 title_by_key | 不读 source_metadata / formal-library |

---

# PR B: CLI — manifest/keys + keyed redo

**文件：**
- `paperforge/cli.py` — `list_parser` 和 `redo_parser`
- `paperforge/commands/ocr.py` — `_run_ocr_list()` + `_run_ocr_redo()`
- `tests/test_ocr_maintenance.py` — 追加 CLI 测试

## B1. `list` 子命令新增参数

```python
list_parser.add_argument("--manifest", action="store_true",
    help="Output key→hash manifest instead of full rows")
list_parser.add_argument("--keys", nargs="*", metavar="KEY",
    help="Only output rows for these specific keys")
```

## B2. `redo` 子命令添加 keys 参数

**P0：现有 `redo` 不支持 positional keys，必须加。**

```python
redo_parser.add_argument("keys", nargs="*", metavar="KEY",
    help="Paper keys to redo (all actionable if empty)")
```

扩展 `_run_ocr_redo()`：

```python
def _run_ocr_redo(vault, keys=None, dry_run=False, verbose=False, no_progress=False):
    papers = [...]  # 如 keys 则仅处理 keys，否则处理全部
```

## B3. `_run_ocr_list()` 逻辑

```python
def _run_ocr_list(vault, json_output=False, output_file=None,
                   manifest=False, keys=None):
```

- `manifest=True`：调用 `compute_maintenance_manifest()` → JSON 输出。`collect_maintenance_rows()` 不调用。
- `keys` 非空：调用 `collect_maintenance_rows()` → 只输出 key 在 `keys` 中的行。
- 优先级：`manifest` > `keys`

## B4. 测试

| # | 场景 | 预期 |
|---|------|------|
| 1 | `paperforge ocr list --manifest` | JSON `{"key": "hash", ...}` |
| 2 | manifest 不调用 `collect_maintenance_rows()` | mock 验证（非时间比） |
| 3 | `paperforge ocr list --json --keys KEY1 KEY2` | 只输出 2 行 |
| 4 | `--keys` 含不存在的 key | 忽略，不报错 |
| 5 | 签名兼容 | 不破坏已有 `json_output` / `output_file` |
| 6 | `paperforge ocr redo KEY1 KEY2` | 只重跑这 2 篇 |
| 7 | `paperforge ocr redo`（无 keys） | 重跑全部（兼容旧行为） |

---

# PR C: Plugin 维护标签 UI + 缓存

**文件：**
- `paperforge/plugin/src/services/ocr-maintenance-ui.ts` — 扩展（缓存的函数 + 类型）
- `paperforge/plugin/src/settings.ts` — `_renderMaintenanceTab()` 重写
- `paperforge/plugin/i18n.ts` — 新增文案
- `tests/ocr-maintenance-ui.test.ts` — 追加

## C1. 服务层新增

`ocr-maintenance-ui.ts`：

```typescript
export interface MaintenanceCache {
  manifest: Record<string, string>;
  papers: Record<string, MaintenanceDisplayRow>;
  cached_at: string;
}

export function readMaintenanceCache(vaultPath: string): MaintenanceCache | null;
export function writeMaintenanceCache(vaultPath: string, cache: MaintenanceCache): void;
```

**重要：`categorizeMaintenanceRow()` 不再被新 UI 调用。**
PR C 会删除 settings.ts 中对旧函数的引用，或者将它适配成 display fields 的薄包装。

## C2. 三阶段渲染

```
Phase 1: 读缓存 → 立即显示（<2ms）
Phase 2: 后台 paperforge ocr list --manifest
         ├─ 匹配 → 不动，停止
         └─ 不匹配 → 刷新图标旋转
           paperforge ocr list --json --keys K1 K2
           合并缓存 → 局部更新表格 → 停转
Phase 3: 无缓存 → 全量拉取并写入缓存
```

**`--keys` 调用格式：**

```typescript
// ✅ 正确
const args = ["-m", "paperforge", "ocr", "list", "--json", "--keys", ...changedKeys];

// ❌ 错误
// "--keys=K1,K2" 不可用（nargs="*" 不会拆分逗号）
```

## C3. 分组渲染

| 组 | group | 标题 | 默认 |
|----|-------|------|------|
| 1 | `retry` | 需要重试 | 展开 |
| 2 | `rebuild` | 可重建结果 | 展开 |
| 3 | `legacy_optional` | 可升级旧结果（可选） | 折叠 |

表格列：

```
☑ | Key | Title | 建议操作 | 原因 | 操作按钮
```

操作按钮映射：

| display_action | 按钮文字 | CLI 命令 |
|---------------|---------|---------|
| `retry_ocr` | 重试 | `paperforge ocr redo KEY` |
| `rebuild_result` | 重建 | `paperforge ocr rebuild KEY` |
| `upgrade_legacy` | 升级 | `paperforge ocr redo KEY` |

工具栏：全选 → 取消全选 → ▶ 执行已选

## C4. `visible_in_maintenance=false` 的处理

- `nopdf` / `blocked` / `done+green` / `pending` / `running` — 不进表格
- `external_action` 组不渲染

## C5. 刷新图标

```css
.pf-maint-spinner { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
```

- 无缓存首次加载 → 不显示 spinner（整体加载中）
- 缓存 + manifest 变化 → 旋转 → 更新完成 → 停止

## C6. i18n 新增

```typescript
"maintenance_group_retry": "需要重试",
"maintenance_group_rebuild": "可重建结果",
"maintenance_group_legacy": "可升级旧结果（可选）",
"maintenance_btn_retry": "重试",
"maintenance_btn_rebuild": "重建",
"maintenance_btn_upgrade": "升级",
"maintenance_refresh_spinning": "正在更新…",
```

## C7. 测试

| # | 场景 | 预期 |
|---|------|------|
| 1 | `visible_in_maintenance=false` 不进表格 | 过滤正确 |
| 2 | 3 组分开展示 | retry / rebuild / legacy 分离 |
| 3 | 批量操作只执行 `visible=true` 的论文 | 不操作 hidden |
| 4 | 缓存读 — manifest 匹配 → 无刷新 | 不触发 execFile |
| 5 | manifest 不匹配 → 增量拉取 | 只请求变化 key |
| 6 | `--keys` 调用格式为 `["--keys", ...keys]` | 不拼接 `--keys=` |
| 7 | 刷新图标状态切换 | 静止 ↔ 旋转 |
| 8 | 旧 `categorizeMaintenanceRow` 不再渲染 visible 路径 | 无 "OCR Failed" / "Rebuild Recommended" |

---

# PR D: Base view action labels（可选 — 按需决定）

**如果要求在 Base 也避免显示 `failed/degraded/health`，这轮做。**

**文件：**
- base generator — 依赖具体实现，需要先确认哪个文件

**改什么：**
- Base 读 `display_label` 替代 `status` + `health` 的原始拼接
- `nopdf` → `"补充 PDF"`
- `blocked` → `"配置 OCR"`（或从 `meta.error` 读具体原因）
- version=v1 → `"可升级"`
- `done+green` → `"已完成"`
- `pending` → `"等待处理"`
- `running/queued/processing` → `"处理中"`

**时机：** PR D 应等 PR A 合并后开发，可在 PR C 之后或并行。
