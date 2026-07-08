# OCR Audit Findings — Spec for GPT Implementation (v2 — 经 GPT 交叉验证修正)

> **Source:** 10-paper truth audit (2026-07-01), vision-verified  
> **Reviewer:** GPT code review 2026-07-01 — 根因分析经交叉验证修正  
> **目的:** 精确描述每个 bug 的位置、复现条件、根因、修复方案，交给 GPT 直接实施  
> **优先级:** P0 > P1 > P2  
> **推荐提交顺序:** Commit 1 → 2 → 3 → 4（见文末）

---

## 总体判断

真正该立刻修的：

| # | 问题 | 类型 |
|---|------|------|
| P0-1 | `_TABLE_PREFIX_PATTERN` 三处不支持罗马数字 | regex + marker |
| P0-2 | `raw_label=figure_title` 的 Table caption 无 guard | role routing |
| P1 | `vision_footnote` 里 `"This figure..."` 不应直接当 footnote | role rescue |
| P2 | `unmatched_assets` 重复计数 | dedup |
| P2 | HTML table 断连(多数被 P0 修复带动解决) | side effect |

不做：Figure 罗马数字（没有真实样本），vector 渲染 PNG（先做 bbox-only 合成）。

---

## P0-1: `_TABLE_PREFIX_PATTERN` 三处不支持罗马数字

### 真实路径

不是单纯 `figure_title` early return 问题。当前 role assignment 顺序是：

1. `_has_figure_prefix(text)` — **False**（"Table II" 不匹配 Figure 正则）
2. `_has_table_prefix(text)` — **False**（regex `\d+` 不认 `II`）
3. 落到 `raw_label == "figure_title"` fallback → `figure_caption`

如果文本是 `Table 1`，第 2 步已经能正确命中 `table_caption`。**真正必炸的是罗马数字（I / II / III / IV）。**

### 位置（三处同步改）

#### A. `paperforge/worker/ocr_roles.py:24-27`

```python
# 当前（只认阿拉伯数字）
_TABLE_PREFIX_PATTERN = re.compile(
    r"^(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table)\s+\d+",
    flags=re.IGNORECASE,
)

# 改为（支持罗马数字 + 可选 .X 子编号）
_TABLE_PREFIX_PATTERN = re.compile(
    r"^(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table)\s+(?:\d+(?:\.\d+)?|[IVXLCDM]+)\b",
    flags=re.IGNORECASE,
)
```

#### B. `paperforge/worker/ocr_signatures.py`

此处有一份独立的 `_TABLE_PREFIX_PATTERN`，当前也只支持 `\d+`。**marker detection 是 style family / marker_signature 的上游——只改 `ocr_roles.py` 不够。**

同步改：

```python
_TABLE_PREFIX_PATTERN = re.compile(
    r"^(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table)\s+(?:\d+(?:\.\d+)?|[IVXLCDM]+)\b",
    flags=re.IGNORECASE,
)
```

`_extract_marker_signature()` 中 `table_number` 的提取也要返回 roman：

```python
_TABLE_NUM_RE = re.compile(
    r"(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table)\s+(\d+(?:\.\d+)?|[IVXLCDM]+)",
    re.IGNORECASE,
)
```

number 字段处理：

```python
result["raw_marker"] = match.group(0)
token = match.group(1)
if re.fullmatch(r"\d+(?:\.\d+)?", token):
    result["number"] = int(float(token))
elif re.fullmatch(r"[IVXLCDM]+", token, re.I):
    result["number"] = _roman_to_int(token)
else:
    result["number"] = None
```

需要 `_roman_to_int` 工具函数：

```python
def _roman_to_int(s: str) -> int | None:
    """Convert Roman numeral to integer. Returns None on invalid input."""
    roman_map = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    s = s.strip().upper()
    if not re.fullmatch(r"[IVXLCDM]+", s):
        return None
    total = 0
    prev = 0
    for ch in reversed(s):
        val = roman_map.get(ch, 0)
        if val < prev:
            total -= val
        else:
            total += val
        prev = val
    return total
```

#### C. `paperforge/worker/ocr_tables.py`

该文件也有自己的 `_TABLE_PREFIX_PATTERN` 和 `_TRUNCATED_TABLE_ONLY_PATTERN`。同步改：

```python
_TABLE_NUM_TOKEN = r"(?:\d+(?:\.\d+)?|[IVXLCDM]+)"

_TABLE_PREFIX_PATTERN = re.compile(
    rf"^(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table)\s*"
    rf"(?:S\.?\s*)?({_TABLE_NUM_TOKEN})\b",
    flags=re.IGNORECASE,
)

_TRUNCATED_TABLE_ONLY_PATTERN = re.compile(
    rf"^(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table)\s*"
    rf"(?:S\.?\s*)?{_TABLE_NUM_TOKEN}\.?"
    rf"(?:\s*\(cont(?:inued)?\.?\))?$",
    re.IGNORECASE,
)
```

`_extract_table_number()` 中的 `int(float(...))` 改为 `_parse_table_number_token`：

```python
def _parse_table_number_token(token: str) -> int | None:
    token = token.strip().rstrip(".")
    if re.fullmatch(r"\d+(?:\.\d+)?", token):
        return int(float(token))
    if re.fullmatch(r"[IVXLCDM]+", token, re.I):
        return _roman_to_int(token)
    return None
```

### 不做：Figure 罗马数字

`_FIGURE_PREFIX_PATTERN` **不改**。`Figure I` 缺乏真实样本，且可能与 section roman / heading 混淆。只修 Table。

### 验证

```python
@pytest.mark.parametrize("text", [
    "Table I. Electrospun polymeric composites...",
    "Table II. Mechanical properties...",
    "Table 1. Baseline Characteristics...",
    "Table III. Results...",
])
def test_table_roman_prefix_matches(text):
    assert _TABLE_PREFIX_PATTERN.match(text)

@pytest.mark.parametrize("text", [
    "Table I. Continued.",
    "Table 1.5. Sub-table",
    "Table S1. Supplementary",
])
def test_table_roman_marker_signature(text):
    sig = _extract_marker_signature(text)
    assert sig["type"] == "table_number"
```

---

## P0-2: `raw_label=figure_title` 的 Table caption guard

### 位置
`paperforge/worker/ocr_roles.py:923-928`

### 场景
KUR9PBJC p4:3 — `raw_label=figure_title`, text=`"Table I. Electrospun..."`。

P0-1 修完后，"Table I" 会在 step 2 被 `_has_table_prefix` 命中 → 正常走 `table_caption`。**但作为保险，还要在 generic `figure_title` fallback 前加 table prefix 检查。**

### 修法

```python
if raw_label == "figure_title":
    if _has_table_prefix(text):
        return RoleAssignment(
            role="table_caption",
            confidence=0.92,
            evidence=[f"figure_title with table prefix: {text[:60]}"],
        )
    return RoleAssignment(
        role="figure_caption",
        confidence=0.85,  # 保持原状，无 table prefix 时才 figure
        evidence=[f"figure_title label: {text[:60]}"],
    )
```

### 验证

```python
@pytest.mark.parametrize("raw_label,text,expected", [
    ("figure_title", "Table I. Electrospun polymeric composites...", "table_caption"),
    ("figure_title", "Table II. Mechanical properties...", "table_caption"),
    ("figure_title", "Table 1. Baseline Characteristics...", "table_caption"),
    ("figure_title", "Figure 1. Flow diagram...", "figure_caption"),
])
def test_figure_title_table_prefix_routes_to_table_caption(raw_label, text, expected):
    result = assign_block_role({"raw_label": raw_label, "text": text}, [], 1000, 1000)
    assert result.role == expected
```

---

## P1: `vision_footnote` 中 `"This figure..."` rescue

### 位置
`paperforge/worker/ocr_roles.py` — generic footnote fallback 之前

### 场景
U746UJ7G p8:4, text=`"This figure demonstrates the difference between time zero and time of sepsis threshold..."`，`raw_label=vision_footnote`。

### 当前代码
```python
if raw_label in {"footnote", "vision_footnote"}:
    return RoleAssignment(
        role="footnote",
        confidence=0.7,
        evidence=[f"{raw_label} label: {text[:60]}"],
    )
```

### 修法

在 generic footnote fallback **前**加：

```python
_FIGURE_DESCRIPTION_OPENING_PATTERN = re.compile(
    r"^(?:This figure|The figure|This Fig\.?|The Fig\.?|Figure\s+\d+|Fig\.?\s+\d+)\b",
    flags=re.IGNORECASE,
)
```

```python
if raw_label in {"footnote", "vision_footnote"}:
    if _FIGURE_DESCRIPTION_OPENING_PATTERN.match(text.strip()):
        near_media = _is_near_figure_media(block, page_blocks)
        role = "figure_caption" if near_media else "figure_caption_candidate"
        confidence = 0.9 if near_media else 0.82
        return RoleAssignment(
            role=role,
            confidence=confidence,
            evidence=[
                f"{raw_label} with figure-description opening: {text[:60]}",
                f"near_figure_media={near_media}",
            ],
        )
```

给 `figure_caption_candidate` 而非直接 `figure_caption`——`"This figure demonstrates..."` 可能是描述型文本，不一定是 formal legend。附近 200px 内有 media asset 时可提升到 `figure_caption`。

### 验证

```python
def test_vision_footnote_this_figure_routes_to_figure_caption_candidate():
    block = {
        "raw_label": "vision_footnote",
        "text": "This figure demonstrates the difference between time zero and time of sepsis threshold.",
        "bbox": [100, 500, 800, 560],
        "page": 8,
    }
    result = assign_block_role(block, [], 1000, 1000)
    assert result.role in {"figure_caption_candidate", "figure_caption"}
    assert "figure" in result.role
```

---

## P1: Style family 误判成 `reference_like`

### 判断
现象可信，但**根因不在 `ocr_families.py`，在上游 `ocr_signatures.py` 的 marker detection**。

### 真实路径
1. `_TABLE_PREFIX_PATTERN` 不识别 Roman → `marker_type != "table_number"`
2. `_CITATION_LINE_PATTERN` 可能匹配 → `marker_type = "citation_line"`
3. `ocr_families.py` 判断 `marker_type in _REFERENCE_MARKER_TYPES` → `reference_like`

### 修法
**不单独修 ocr_families.py。P0-1 修完后，marker 正确识别为 `table_number`，family 自然进入 `table_caption_like`。**

可加一条保险：
```python
# 在 ocr_families.py 的 reference check 前
if _looks_like_table_prefix(text):
    return "table_caption_like", "table_marker"
```

---

## P2: Unmatched asset 重复计数

### 位置
`paperforge/worker/ocr_figures.py` — `_recompute_final_unmatched_assets` 或 inventory return 前

### 场景
KUR9PBJC p9:11：同时出现在 `matched_figures[3].matched_assets` 和 `unmatched_assets`。

### 根因（经 GPT 修正）
当前 pipeline 有 `used_asset_page_ids` 和 `ownership.mark_assets_owned()`，但某些 matched path 写入了 `matched_assets` / `asset_block_ids` 后**没有同步写入 `used_asset_page_ids`**。`_recompute_final_unmatched_assets` 只看 `used_asset_page_ids`，不反查 `matched_figures` 全量 consumed ids。

### 修法

做最终兜底 helper，在 inventory return 前最后一次过滤：

```python
def _collect_matched_figure_asset_ids(matched_figures: list[dict]) -> set[tuple[int, str]]:
    """从已匹配的 figures 反查所有已消费的 asset (page, block_id)。"""
    consumed: set[tuple[int, str]] = set()
    for fig in matched_figures:
        fig_page = int(fig.get("page", 0) or 0)
        asset_pages: list[int] = fig.get("asset_pages") or []
        for asset in fig.get("matched_assets", []):
            bid = str(asset.get("block_id") or "")
            if not bid:
                continue
            ap = int(asset.get("page", 0) or 0) or fig_page
            consumed.add((ap, bid))
        for bid in fig.get("asset_block_ids", []):
            bid = str(bid)
            if not bid:
                continue
            if len(asset_pages) == 1:
                consumed.add((int(asset_pages[0]), bid))
            else:
                consumed.add((fig_page, bid))
    return consumed


# 在 inventory return 前：
_final_consumed = _collect_matched_figure_asset_ids(matched_figures)
unmatched_assets = [
    a for a in unmatched_assets
    if (int(a.get("page", 0) or 0), str(a.get("block_id", ""))) not in _final_consumed
]
```

**注意：** figure 的 asset page 不一定等于 legend page。不能用 `fig.get("page")` 盲匹配，必须看 `matched_assets[].page` 或 `asset_pages`。

### 验证
```python
# KUR9PBJC — 修前 p9:11 同时出现在 matched + unmatched，修后从 unmatched 移除
```

---

## P2: Vector figure 盲区 — bbox-only synthetic figure

### 位置
`paperforge/worker/ocr_figures.py` — `build_figure_inventory`

### 场景
U746UJ7G pages 5 + 8：Figure 1 流程图 + Figure 2 时间序图是 vector 绘制，PyMuPDF 找不到 image object。

### 修正后的理解（经 GPT）
当前 figure inventory **不是**只依赖 PyMuPDF image object。`build_figure_inventory` 会把 `raw_label in {"image", "chart", "figure_title", "figure"}` 的 `media_asset` 放进 figure assets。所以 U746UJ7G 的问题更准确是：

> PaddleOCR 有 bbox，但 figure caption / description 被误分成 footnote 或 rejected legend；同时 vector asset 没有可渲染 image payload，所以即使 bbox 存在，也不能形成 reader 可展示 figure。

### 修法（第一阶段 — 不上 vector→PNG 渲染）

在 unmatched assets 处理中加入 synthetic vector figure fallback：

```python
条件：
1. 同页存在 unmatched media_asset，raw_label in {image, chart, figure}
   或 asset_family_hint=figure_like
2. 同页附近存在 figure_caption / figure_caption_candidate / validation-first caption
3. 或存在 text 以 "This figure" / "The figure" / "Figure N" / "Fig. N" 开头
4. asset bbox 有效，但没有 image object / image payload

动作：
构造 matched_figures entry：
- matched_assets 使用 bbox record
- flags 加 ["synthetic_vector_asset", "bbox_only_asset"]
- truth_source = "vector_bbox"
- render 层如果没有 image，显示 placeholder/card
```

**不上 PNG 渲染**。第二阶段再考虑 `page.get_pixmap(clip=...)`——那是可选 enhancement，不能作为 matcher 的必要条件。

---

## P2: HTML table block 断连

### 判断
多数会被 P0-1（Roman 修复）+ P0-2（figure_title guard）修复带动解决。KUR9PBJC 的 `Table I / II` 错标修复后，caption 正确进入 table inventory → 配对 `raw_label=table` asset。

### 修复后仍需检查
```python
# 2YW2MJBL — 5 个 unmatched table assets，0 unmatched captions
# 修后检查 caption 是否出现，能否配对。
```

---

## 推荐提交顺序与测试

### Commit 1: Table roman + figure_title table guard（P0-1 + P0-2）

改 3 文件：
- `paperforge/worker/ocr_roles.py`
- `paperforge/worker/ocr_signatures.py`
- `paperforge/worker/ocr_tables.py`

测试：
```bash
python -m pytest tests/test_ocr_tables.py tests/test_ocr_roles.py tests/test_ocr_signatures.py -q
```

加 parametrize 测试（见各节验证代码）。

### Commit 2: vision_footnote figure description rescue（P1）

改：
- `paperforge/worker/ocr_roles.py`

测试：
```bash
python -m pytest tests/test_ocr_roles.py::test_vision_footnote_this_figure_routes_to_figure_caption_candidate -q
```

### Commit 3: Final unmatched asset de-dup（P2）

改：
- `paperforge/worker/ocr_figures.py`

加 `_collect_matched_figure_asset_ids()` + inventory return 前过滤。

测试：
```bash
python -m pytest tests/test_ocr_figures.py -q
# KUR9PBJC p9:11 不应出现在 unmatched_assets
```

### Commit 4: bbox-only synthetic vector figure fallback（P2）

改：
- `paperforge/worker/ocr_figures.py`

先让 inventory 产生 synthetic entry，不上 PNG 渲染。

测试：
```bash
python -m pytest tests/test_ocr_figures.py tests/unit/worker/test_figure_containment.py -q
```

### 完整回归
```bash
python -m pytest tests/test_ocr_tables.py tests/test_ocr_figures.py tests/test_ocr_roles.py tests/test_ocr_signatures.py tests/unit/worker/test_figure_containment.py -q
```
