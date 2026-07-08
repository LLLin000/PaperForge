# OCR 审计发现修复计划 — 4 Commits Implementation Plan

> **来源:** 10 篇论文 truth audit + GPT 交叉验证  
> **目标:** 低风险、逐步修复 audit 发现的 6 类问题  
> **顺序:** Commit 1 → 2 → 3 → 4

---

## 全局约束

- 不改 `_FIGURE_PREFIX_PATTERN`（Figure 罗马数字无真实样本）
- Vector figure 第一阶段不做 PNG 渲染，只做 bbox-only synthetic entry
- 每步有独立测试 + 回归验证

## Implementation Amendments（GPT 二审 — 开工前必读）

以下补丁来自 GPT 代码审查，不修则 Commit 2/4 会引入 regression。

| # | 问题 | Commit | 修正 |
|---|------|--------|------|
| 1 | `ocr_tables.py` plan 里丢掉了 `表\|🤔` | 1d | 恢复中文 table label 支持 |
| 2 | `_roman_to_int()` 放进了 `ocr_roles.py` 但 unused | 1a | 不放 `ocr_roles.py`，只需要 regex |
| 3 | `_is_near_figure_media` 只看 `block_label` 不看 `raw_label` | 2 | 改为 `block_label or raw_label` |
| 4 | synthetic score 无 hard vertical gate → far-body 误配 | 4 | `vertical_gap > 300` → `return 0.0` |
| 5 | synthetic fallback 多个 asset 取最高分时差距小也硬吃 | 4 | top - second < 0.15 时 skip |
| 6 | synthetic 不防已存在的 figure 编号 → 重复 | 4 | 建 `_existing_numbered` 集合 |
| 7 | synthetic entry 缺 `caption_score` / `group_type` | 4 | 补全字段 |
| 8 | 无 `ocr_families.py` 单元测试 | 1 | 加 "Table II" 不被 reference_like 吞的测试 |

### 修法速查

**Amendment 1**（Commit 1d）— `ocr_tables.py` pattern 保留中文：
```python
_TABLE_PREFIX_PATTERN = re.compile(
    rf"^(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table|表|\ufffc)\s*"
    rf"(?:S\.?\s*)?({_TABLE_NUM_TOKEN})\b",
    flags=re.IGNORECASE,
)
```

**Amendment 2**（Commit 1a）— `ocr_roles.py` 不放 `_roman_to_int`，只改 regex。

**Amendment 3**（Commit 2）— `_is_near_figure_media` helper 改：
```python
label = str(other.get("block_label") or other.get("raw_label") or "").strip()
if label not in {"image", "chart", "figure"}:
    continue
```

**Amendment 4-7**（Commit 4）— synthetic helper 收紧，见 Commit 4 详细代码。

**Amendment 8**（Commit 1）— 加 `tests/test_ocr_families.py` 测试：
```python
def test_table_roman_prefix_family_not_reference_like():
    block = {
        "text": "Table II. Mechanical properties...",
        "marker_signature": {"type": "citation_line"},
        "zone": "display_zone",
        "raw_label": "figure_title",
    }
    family, authority = _classify_style_family(block, {}, {})
    assert family == "table_caption_like"
```

---
## File Map

| 文件 | Commit |
|------|--------|
| `paperforge/worker/ocr_roles.py` | 1, 2 |
| `paperforge/worker/ocr_signatures.py` | 1 |
| `paperforge/worker/ocr_tables.py` | 1 |
| `paperforge/worker/ocr_families.py` | 1 |
| `paperforge/worker/ocr_figures.py` | 3, 4 |
| `tests/test_ocr_roles.py` | 1, 2 |
| `tests/test_ocr_signatures.py` | 1 |
| `tests/test_ocr_tables.py` | 1 |
| `tests/test_ocr_figures.py` | 3, 4 |
| `tests/unit/worker/test_figure_containment.py` | 4 |

---

### Commit 1: Table prefix 统一修复 + figure_title guard

**目标**: Table I/II/III 罗马数字 + Table S1 前缀 + figure_title table guard + style family 保险

#### 1a. `ocr_roles.py` — `_TABLE_PREFIX_PATTERN` 支持 Roman + S

```python
_TABLE_NUM_TOKEN = r"(?:\d+(?:\.\d+)?|[IVXLCDM]+)"

_TABLE_PREFIX_PATTERN = re.compile(
    rf"^(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table)\s*"
    rf"(?:S\.?\s*)?({_TABLE_NUM_TOKEN})\b",
    flags=re.IGNORECASE,
)
```

`_has_table_prefix()` 自动生效（它用这个 pattern）。

⚠️ **Amendment 2**：`ocr_roles.py` **不**加 `_roman_to_int()`。此处只需要 regex 匹配 prefix，不需要解析 number。`_roman_to_int()` 应放在 `ocr_signatures.py` 和 `ocr_tables.py` 中。

#### 1b. `ocr_roles.py` — `figure_title` generic fallback 加 guard

找到 generic `if raw_label == "figure_title":` 分支（非 figure-prefix 分支内的），改为：

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
        confidence=0.85,
        evidence=[f"figure_title label: {text[:60]}"],
    )
```

#### 1c. `ocr_signatures.py` — `_TABLE_PREFIX_PATTERN` + marker extraction

同步改 pattern：

```python
_TABLE_NUM_TOKEN = r"(?:\d+(?:\.\d+)?|[IVXLCDM]+)"
_TABLE_PREFIX_PATTERN = re.compile(
    rf"^(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table)\s*"
    rf"(?:S\.?\s*)?({_TABLE_NUM_TOKEN})\b",
    flags=re.IGNORECASE,
)
```

`_extract_marker_signature()` 中 table branch 用这个 pattern + `_roman_to_int`：

```python
elif marker_type == "table_number":
    match = _TABLE_PREFIX_PATTERN.search(stripped)
    if match:
        token = match.group(1)
        result["raw_marker"] = match.group(0)
        if re.fullmatch(r"\d+(?:\.\d+)?", token):
            result["number"] = int(float(token))
        else:
            result["number"] = _roman_to_int(token)
    result["kind"] = "table"
```

#### 1d. `ocr_tables.py` — pattern + `_extract_table_number`

```python
_TABLE_NUM_TOKEN = r"(?:\d+(?:\.\d+)?|[IVXLCDM]+)"
_TABLE_PREFIX_PATTERN = re.compile(
    rf"^(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table|表|\ufffc)\s*"
    rf"(?:S\.?\s*)?({_TABLE_NUM_TOKEN})\b",
    flags=re.IGNORECASE,
)
_TRUNCATED_TABLE_ONLY_PATTERN = re.compile(
    rf"^(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table|表|\ufffc)\s*"
    rf"(?:S\.?\s*)?{_TABLE_NUM_TOKEN}\.?"
    rf"(?:\s*\(cont(?:inued)?\.?\))?$",
    re.IGNORECASE,
)
```

`_extract_table_number()` 改为用 `_parse_table_number_token`：

```python
def _parse_table_number_token(token: str) -> int | None:
    token = token.strip().rstrip(".")
    if re.fullmatch(r"\d+(?:\.\d+)?", token):
        return int(float(token))
    if re.fullmatch(r"[IVXLCDM]+", token, re.IGNORECASE):
        return _roman_to_int(token)
    return None


def _extract_table_number(text: str) -> int | None:
    m = _TABLE_PREFIX_PATTERN.search(text)
    if not m:
        return None
    return _parse_table_number_token(m.group(1))
```

需要 import `_roman_to_int` 或在 `ocr_tables.py` 内也放一份。

#### 1e. `ocr_families.py` — 早期 table guard

在 `_classify_style_family()` 的 reference 检查前插入：

```python
_TABLE_PREFIX_LIKE = re.compile(
    rf"^(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table)\s*"
    rf"(?:S\.?\s*)?(?:\d+(?:\.\d+)?|[IVXLCDM]+)\b",
    flags=re.IGNORECASE,
)

# 在 _classify_style_family 内，reference anchor 检查之前：
if _TABLE_PREFIX_LIKE.match(text):
    return "table_caption_like", "table_marker"
```

#### 1f. Commit 1 测试

加到 `tests/test_ocr_roles.py`：

```python
@pytest.mark.parametrize("raw_label,text,expected", [
    ("figure_title", "Table I. Electrospun polymeric composites...", "table_caption"),
    ("figure_title", "Table II. Mechanical properties...", "table_caption"),
    ("figure_title", "Table 1. Baseline Characteristics...", "table_caption"),
    ("figure_title", "Table S1. Supplementary characteristics...", "table_caption"),
    ("figure_title", "Figure 1. Flow diagram...", "figure_caption"),
    ("figure_title", "Fig. 2. Results...", "figure_caption"),
])
def test_figure_title_table_prefix_routes_to_table_caption(raw_label, text, expected):
    result = assign_block_role({"raw_label": raw_label, "text": text}, [], 1000, 1000)
    assert result.role == expected
```

加到 `tests/test_ocr_signatures.py`：

```python
@pytest.mark.parametrize("text,expected_number", [
    ("Table I. Electrospun...", 1),
    ("Table II. Mechanical...", 2),
    ("Table III. Results...", 3),
    ("Table IV. Results...", 4),
    ("Table 1. Baseline...", 1),
    ("Table S1. Supplementary...", 1),
])
def test_table_roman_and_s_prefix_marker_signature(text, expected_number):
    sig = _extract_marker_signature(text)
    assert sig["type"] == "table_number"
    assert sig["number"] == expected_number
```

加到 `tests/test_ocr_tables.py`：

```python
@pytest.mark.parametrize("text,expected_number", [
    ("Table I. Electrospun...", 1),
    ("Table II. Mechanical...", 2),
    ("Table S1. Supplementary...", 1),
])
def test_extract_table_number_supports_roman_and_s_prefix(text, expected_number):
    assert _extract_table_number(text) == expected_number
```

**Amendment 8** — 加 `tests/test_ocr_families.py` 测试：
```python
def test_table_roman_prefix_family_not_reference_like():
    from paperforge.worker.ocr_families import _classify_style_family
    block = {
        "text": "Table II. Mechanical properties...",
        "marker_signature": {"type": "citation_line"},
        "zone": "display_zone",
        "raw_label": "figure_title",
        "bbox": [100, 100, 800, 130],
    }
    family, authority = _classify_style_family(block, {}, {})
    assert family == "table_caption_like"
    assert authority == "table_marker"

#### 验证命令

```bash
python -m pytest tests/test_ocr_roles.py tests/test_ocr_signatures.py tests/test_ocr_tables.py -q
```

#### Commit message

```
fix: support Roman numeral and S-prefix table captions across roles/signatures/tables

- _TABLE_PREFIX_PATTERN in ocr_roles.py, ocr_signatures.py, ocr_tables.py
  now matches Table I/II/III and Table S1/S2
- _extract_table_number and _extract_marker_signature parse Roman numbers
- figure_title generic fallback checks table prefix before figure caption
- ocr_families.py adds early table-prefix guard before reference family
```

---

### Commit 2: `vision_footnote` figure description rescue

**目标**: `raw_label=vision_footnote` 但文本是 `"This figure..."` 的不再吞成 footnote

#### 2a. `ocr_roles.py` — 加 pattern + 插入 rescue

在 generic footnote fallback **前**：

```python
_FIGURE_DESCRIPTION_OPENING_PATTERN = re.compile(
    r"^(?:This figure|The figure|This Fig\.?|The Fig\.?|"
    r"Figure\s+\d+|Fig\.?\s+\d+)\b",
    flags=re.IGNORECASE,
)


def _looks_like_figure_description_opening(text: str) -> bool:
    return bool(_FIGURE_DESCRIPTION_OPENING_PATTERN.match(text.strip()))
```

在 generic footnote fallback 前插入：

```python
# Figure-description footnotes are not real footnotes.
if raw_label in {"footnote", "vision_footnote"} and _looks_like_figure_description_opening(text):
    near_media = _is_near_figure_media(block, page_blocks)
    return RoleAssignment(
        role="figure_caption" if near_media else "figure_caption_candidate",
        confidence=0.9 if near_media else 0.82,
        evidence=[
            f"{raw_label} with figure-description opening: {text[:60]}",
            f"near_figure_media={near_media}",
        ],
    )
```

#### 2b. Commit 2 测试

```python
def test_vision_footnote_this_figure_routes_to_figure_caption_candidate():
    block = {"raw_label": "vision_footnote",
             "text": "This figure demonstrates the difference...",
             "bbox": [100, 500, 800, 560], "page": 8}
    result = assign_block_role(block, [], 1000, 1000)
    assert result.role == "figure_caption_candidate"


def test_vision_footnote_this_figure_near_media_routes_to_caption():
    block = {"raw_label": "vision_footnote",
             "text": "This figure demonstrates...",
             "bbox": [100, 500, 800, 560], "page": 8}
    media = {"raw_label": "image", "block_label": "image",
             "bbox": [100, 300, 800, 480],
             "block_bbox": [100, 300, 800, 480], "page": 8}
    result = assign_block_role(block, [media], 1000, 1000)
    assert result.role == "figure_caption"


def test_ordinary_vision_footnote_stays_footnote():
    block = {"raw_label": "vision_footnote",
             "text": "Abbreviations: ICU, intensive care unit.",
             "bbox": [100, 900, 800, 940], "page": 5}
    result = assign_block_role(block, [], 1000, 1000)
    assert result.role == "footnote"
```

#### 验证命令

```bash
python -m pytest tests/test_ocr_roles.py -q
```

#### Commit message

```
fix: rescue figure-description text in vision_footnote from footnote role

- Add _FIGURE_DESCRIPTION_OPENING_PATTERN for "This figure..." / "Figure N" etc.
- Insert rescue before generic footnote fallback
- Route to figure_caption (near media) or figure_caption_candidate (far)
```

---

### Commit 3: Final unmatched asset dedup

**目标**: matched 后又被 promotion/infer 引入的重复 unmatched 资产，在 inventory return 前做最终过滤

#### 3a. `ocr_figures.py` — 新增 robust helper

```python
def _collect_matched_figure_asset_ids_from_list(matched_figures: list[dict]) -> set[tuple[int, str]]:
    consumed: set[tuple[int, str]] = set()
    for fig in matched_figures:
        fig_page = int(fig.get("page", 0) or 0)
        asset_pages = [int(p) for p in (fig.get("asset_pages") or []) if p is not None]

        for asset in fig.get("matched_assets", []) or []:
            bid = str(asset.get("block_id") or "")
            if not bid:
                continue
            ap = int(asset.get("page", 0) or 0) or fig_page
            if ap > 0:
                consumed.add((ap, bid))

        for bid_raw in fig.get("asset_block_ids", []) or []:
            bid = str(bid_raw or "")
            if not bid:
                continue
            if len(asset_pages) == 1:
                consumed.add((asset_pages[0], bid))
            elif fig_page > 0:
                consumed.add((fig_page, bid))

    return consumed


def _collect_matched_figure_asset_ids(inventory: dict) -> set[tuple[int, str]]:
    return _collect_matched_figure_asset_ids_from_list(inventory.get("matched_figures", []) or [])


def _dedup_unmatched_assets_against_matched_figures(inventory: dict) -> None:
    consumed = _collect_matched_figure_asset_ids(inventory)
    if not consumed:
        return
    inventory["unmatched_assets"] = [
        a for a in inventory.get("unmatched_assets", []) or []
        if (int(a.get("page", 0) or 0), str(a.get("block_id", "") or "")) not in consumed
    ]


def _dedup_unresolved_clusters_against_matched_figures(inventory: dict) -> None:
    consumed = _collect_matched_figure_asset_ids(inventory)
    if not consumed:
        return
    cleaned = []
    for cluster in inventory.get("unresolved_clusters", []) or []:
        page = int(cluster.get("page", 0) or 0)
        kept = [str(bid) for bid in (cluster.get("media_block_ids", []) or [])
                if (page, str(bid)) not in consumed]
        if not kept:
            continue
        cluster = dict(cluster)
        cluster["media_block_ids"] = kept
        cleaned.append(cluster)
    inventory["unresolved_clusters"] = cleaned
```

把 `_collect_figure_owned_asset_ids` 改为复用新 helper：

```python
def _collect_figure_owned_asset_ids(figure_inventory: dict) -> set[tuple[int, str]]:
    return _collect_matched_figure_asset_ids(figure_inventory)
```

#### 3b. 插入位置

在 `build_figure_inventory` 中，**promotion + infer 之后**、inventory return 之前：

```python
inventory = _promote_sequence_matches(inventory, structured_blocks)
inventory = _infer_missing_main_figure_numbers(inventory, structured_blocks)

_dedup_unmatched_assets_against_matched_figures(inventory)
_dedup_unresolved_clusters_against_matched_figures(inventory)
# ... completeness, collisions, return inventory
```

#### 3c. Commit 3 测试

```python
def test_final_unmatched_assets_excludes_matched_assets_after_promotion():
    inventory = {
        "matched_figures": [{
            "page": 9, "asset_pages": [9],
            "matched_assets": [{"page": 9, "block_id": "11"}],
            "asset_block_ids": ["11"],
        }],
        "unmatched_assets": [
            {"page": 9, "block_id": "11"},
            {"page": 9, "block_id": "12"},
        ],
        "unresolved_clusters": [],
    }
    _dedup_unmatched_assets_against_matched_figures(inventory)
    assert [a["block_id"] for a in inventory["unmatched_assets"]] == ["12"]


def test_collect_matched_figure_asset_ids_uses_asset_page_not_legend_page():
    ids = _collect_matched_figure_asset_ids_from_list([{
        "page": 10, "legend_page": 9, "asset_pages": [10],
        "matched_assets": [{"page": 10, "block_id": "A"}],
        "asset_block_ids": ["A"],
    }])
    assert ids == {(10, "A")}
```

#### 验证命令

```bash
python -m pytest tests/test_ocr_figures.py -q
```

#### Commit message

```
fix: dedup unmatched_assets against matched_figures after promotion/infer

- Add _collect_matched_figure_asset_ids_from_list with cross-page safety
- Reuse for ownership conflicts (fixes existing bug)
- Run dedup after _promote_sequence_matches and _infer_missing_main_figure_numbers
```

---

### Commit 4: Bbox-only synthetic vector figure fallback

**目标**: vector 渲染的 figure（流程图、统计图）在没有 PyMuPDF image object 时，仍能进入 inventory

#### 4a. `ocr_figures.py` — 新增 helper

```python
_FIGURE_DESCRIPTION_OPENING = re.compile(
    r"^(?:This figure|The figure|This Fig\.?|The Fig\.?|"
    r"Figure\s+\d+|Fig\.?\s+\d+)\b",
    flags=re.IGNORECASE,
)


def _is_synthetic_vector_caption_candidate(block: dict) -> bool:
    role = str(block.get("role") or "")
    text = str(block.get("text") or "").strip()
    if role in {"figure_caption", "figure_caption_candidate"}:
        return True
    if _is_validation_first_legend_candidate(block):
        return True
    if _FIGURE_DESCRIPTION_OPENING.match(text):
        return True
    return False


def _score_caption_to_unmatched_asset_for_synthetic(caption: dict, asset: dict) -> float:
    cb = caption.get("bbox") or caption.get("block_bbox") or [0, 0, 0, 0]
    ab = asset.get("bbox") or asset.get("block_bbox") or [0, 0, 0, 0]
    if len(cb) < 4 or len(ab) < 4:
        return 0.0

    cx1, cy1, cx2, cy2 = cb
    ax1, ay1, ax2, ay2 = ab

    # Hard gate: must be same page
    if int(caption.get("page", 0) or 0) != int(asset.get("page", 0) or 0):
        return 0.0

    vertical_gap = max(0.0, max(cy1 - ay2, ay1 - cy2))
    if vertical_gap > 300:
        return 0.0

    x_overlap = max(0.0, min(cx2, ax2) - max(cx1, ax1))
    min_width = max(1.0, min(cx2 - cx1, ax2 - ax1))
    x_ratio = x_overlap / min_width
    if x_ratio < 0.25:
        return 0.0

    score = 0.20  # same-page already verified

    if x_ratio >= 0.5:
        score += 0.45
    elif x_ratio >= 0.25:
        score += 0.25

    if vertical_gap <= 80:
        score += 0.35
    elif vertical_gap <= 180:
        score += 0.20
    elif vertical_gap <= 300:
        score += 0.10

    return min(score, 1.0)


def _build_bbox_only_synthetic_figure(caption, asset, *, index, score):
    text = str(caption.get("text") or "")
    fn = _extract_figure_number(text)
    ns = _extract_figure_namespace(text) if fn is not None else "figure"
    page = int(asset.get("page", caption.get("page", 0)) or 0)
    asset_record = _project_asset_record(asset)
    fig_id = _format_figure_id(ns, fn) if fn is not None else f"synthetic_figure_p{page}_{asset.get('block_id', index)}"
    return {
        "figure_id": fig_id, "figure_namespace": ns,
        "legend_block_id": caption.get("block_id", ""),
        "page": page, "legend_page": int(caption.get("page", 0) or 0),
        "asset_pages": [page] if page else [],
        "text": text, "figure_number": fn,
        "matched_assets": [asset_record],
        "asset_block_ids": [asset_record.get("block_id", "")],
        "cluster_bbox": asset.get("bbox") or asset.get("block_bbox") or [],
        "match_score": {"score": score, "decision": "matched",
                        "evidence": ["bbox_only_synthetic_vector_fallback"]},
        "confidence": min(0.55, score),
        "caption_score": score_figure_caption(
            caption,
            nearby_media=True,
            caption_style_match=False,
            body_prose_likelihood=False,
        ),
        "flags": ["synthetic_vector_asset", "bbox_only_asset"],
        "truth_source": "vector_bbox",
        "strict_status": "bbox_only_synthetic",
        "settlement_type": "bbox_only_synthetic",
        "group_type": "",
        "group_evidence": [],
        "bridge_block_ids": [],
```

    if not unmatched_assets:
        return
    candidates = [c for c in list(unmatched_legends) + list(rejected_legends)
                  if _is_synthetic_vector_caption_candidate(c)]
    if not candidates:
        return

    # Build existing figure number set to avoid duplicates (Amendment 6)
    _existing_numbered = {
        (str(fig.get("figure_namespace") or "figure"), fig.get("figure_number"))
        for fig in matched_figures
        if fig.get("figure_number") is not None
    }

    used_caption_ids: set[str] = set()
    used_asset_ids: set[tuple[int, str]] = set()

    for caption in candidates:
        cap_page = int(caption.get("page", 0) or 0)
        if cap_page <= 0:
            continue

        # Skip if figure number already exists (Amendment 6)
        fn = _extract_figure_number(str(caption.get("text") or ""))
        ns = _extract_figure_namespace(str(caption.get("text") or "")) if fn is not None else "figure"
        if fn is not None and (ns, fn) in _existing_numbered:
            continue

        page_assets = [
            a for a in unmatched_assets
            if int(a.get("page", 0) or 0) == cap_page
            and str(a.get("role") or "") in {"media_asset", "figure_asset"}
            and (a.get("asset_family_hint") == "figure_like"
                 or str(a.get("raw_label") or "") in {"image", "chart", "figure"})
        ]
        scored = []
        for asset in page_assets:
            aid = (int(asset.get("page", 0) or 0), str(asset.get("block_id", "") or ""))
            if aid in used_asset_ids or not ownership.can_consume_assets([aid]):
                continue
            s = _score_caption_to_unmatched_asset_for_synthetic(caption, asset)
            if s >= 0.65:
                scored.append((s, asset))
        if not scored:
            continue

        # Tie-breaking: skip if top two scores are too close (Amendment 5)
        scored.sort(key=lambda x: x[0], reverse=True)
        top_score, top_asset = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else -1.0
        if second_score >= 0 and top_score - second_score < 0.15:
            continue

        score, asset = top_score, top_asset
        aid = (int(asset.get("page", 0) or 0), str(asset.get("block_id", "") or ""))
        synthetic = _build_bbox_only_synthetic_figure(caption, asset, index=len(matched_figures) + 1, score=score)
        matched_figures.append(synthetic)

        # Track figure number for future dedup (Amendment 6)
        if fn is not None:
            _existing_numbered.add((ns, fn))

        if aid[1]:
            ownership.mark_assets_owned([aid], owner_id=str(caption.get("block_id", "")), owner_family="figure")
            used_asset_ids.add(aid)
        cid = str(caption.get("block_id", "") or "")
        if cid:
            used_caption_ids.add(cid)

    # Clean up consumed legends and assets
    if used_caption_ids:
        unmatched_legends[:] = [c for c in unmatched_legends if str(c.get("block_id", "") or "") not in used_caption_ids]
        rejected_legends[:] = [c for c in rejected_legends if str(c.get("block_id", "") or "") not in used_caption_ids]
    if used_asset_ids:
        unmatched_assets[:] = [a for a in unmatched_assets if (int(a.get("page", 0) or 0), str(a.get("block_id", "") or "")) not in used_asset_ids]

    # Clean up consumed legends and assets
    if used_caption_ids:
        unmatched_legends[:] = [c for c in unmatched_legends if str(c.get("block_id", "") or "") not in used_caption_ids]
        rejected_legends[:] = [c for c in rejected_legends if str(c.get("block_id", "") or "") not in used_caption_ids]
    if used_asset_ids:
        unmatched_assets[:] = [a for a in unmatched_assets if (int(a.get("page", 0) or 0), str(a.get("block_id", "") or "")) not in used_asset_ids]
```

#### 4c. 插入位置

在 `build_figure_inventory` 中，dense parent consolidation 之后、inventory return 之前：

```python
_apply_bbox_only_synthetic_vector_fallback(
    matched_figures=matched_figures,
    unmatched_legends=unmatched_legends,
    rejected_legends=rejected_legends,
    unmatched_assets=unmatched_assets,
    ownership=ownership,
)
```

#### 4d. Commit 4 测试

```python
def test_bbox_only_synthetic_fallback_matches_asset_and_caption():
    ownership = FigureOwnershipRegistry()
    mf, ul, rl, ua = [], [{
        "block_id": "cap1", "page": 5, "role": "figure_caption_candidate",
        "text": "Figure 1. Flow Diagram", "bbox": [100, 700, 900, 760],
    }], [], [{
        "block_id": "a1", "page": 5, "role": "media_asset",
        "raw_label": "chart", "asset_family_hint": "figure_like",
        "bbox": [100, 200, 900, 680],
    }]
    _apply_bbox_only_synthetic_vector_fallback(
        matched_figures=mf, unmatched_legends=ul, rejected_legends=rl,
        unmatched_assets=ua, ownership=ownership,
    )
    assert len(mf) == 1
    assert mf[0]["truth_source"] == "vector_bbox"
    assert "bbox_only_asset" in mf[0]["flags"]
    assert ua == []
    assert ul == []


def test_bbox_only_synthetic_fallback_rejects_far_body_mention():
    ownership = FigureOwnershipRegistry()
    mf, ul, rl, ua = [], [{
        "block_id": "cap1", "page": 5, "role": "figure_caption_candidate",
        "text": "This figure demonstrates...", "bbox": [100, 100, 900, 140],
    }], [], [{
        "block_id": "a1", "page": 5, "role": "media_asset",
        "raw_label": "chart", "asset_family_hint": "figure_like",
        "bbox": [100, 900, 900, 1200],
    }]
    _apply_bbox_only_synthetic_vector_fallback(
        matched_figures=mf, unmatched_legends=ul, rejected_legends=rl,
        unmatched_assets=ua, ownership=ownership,
    )
    assert mf == []
    assert len(ua) == 1
```

#### 验证命令

```bash
python -m pytest tests/test_ocr_figures.py tests/unit/worker/test_figure_containment.py -q
```

#### Commit message

```
feat: add bbox-only synthetic vector figure fallback

- Score unmatched figure_like assets against caption candidates by geometry
- Create synthetic matched_figure with flags=synthetic_vector_asset,bbox_only_asset
- No PNG rendering — bbox-only, render layer shows placeholder
- Minimum score threshold 0.65 to prevent false positives
```

---

## 最终回归

```bash
python -m pytest \
  tests/test_ocr_roles.py \
  tests/test_ocr_signatures.py \
  tests/test_ocr_tables.py \
  tests/test_ocr_figures.py \
  tests/unit/worker/test_figure_containment.py \
  -q
```

```bash
# 真实数据验证（需 vault 环境）
python scripts/dev/ocr_rebuild_paper.py KUR9PBJC -q
python scripts/dev/ocr_rebuild_paper.py U746UJ7G -q
```

## 验收标准

| 场景 | Commit | 验收条件 |
|------|--------|---------|
| KUR9PBJC Table I/II caption 正确 | 1 | role=table_caption, marker=table_number |
| KUR9PBJC p9:11 不在 unmatched | 3 | unmatched_assets 不含 p9:11 |
| U746UJ7G p8:4 footnote rescue | 2 | role=figure_caption_candidate（near media） |
| U746UJ7G Figure 1/2 在 inventory | 4 | matched_figures 含 synthetic vector entry |
| 2YW2MJBL HTML tables | 1+3 | 更多 table caption 识别 |
| 现有所有测试无 regression | all | pytest 全绿 |
