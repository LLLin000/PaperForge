# Figure Pipeline VNext Phase 3 — Special Fallbacks (Sidecar + LegendBundle + LocatorBridge) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the three special fallback passes — `SidecarPass`, `LegendBundlePass`, `LocatorBridgePass` — that handle the non-same-page matching scenarios the legacy pipeline covers in its 400+ line fallback section. These are spec §7.3 Layer 1 (sidecar, locator) and Layer 2 (legend bundle) passes.

**Architecture:** Build on the completed Phase 0–2 vnext seams. Each pass follows the established pattern: collect proposals → arbitrate via `OwnershipLedger` → `accept_match` or `accept_reservation`. The passes reuse existing legacy helper functions (`_same_page_narrow_caption_column`, `_partition_assets_by_caption_bands`, `_identify_bundle_source_legend_ids`, `_is_previous_page_legend_locator`, `_is_tight_asset_cluster`) via lazy import — the helpers are immutable utilities, not legacy pipeline state.

**Tech Stack:** Python 3, pytest, existing OCR helpers in `paperforge/worker/ocr_figures.py`, vnext modules under `paperforge/worker/`, portable repo fixtures under `tests/fixtures/ocr_vnext_real_papers/`

## Global Constraints

- Build on branch/worktree `feat/figure-pipeline-vnext`; do not edit the main checkout.
- Preserve the external interface `build_figure_inventory(structured_blocks, page_width=1200) -> FigureInventory`.
- Legacy implementation remains the immutable baseline.
- Keep `ResourceRef` as the only ownership key.
- Special fallbacks must not steal resources already claimed by same-page or cross-page settlement passes.
- Disabled passes must emit no proposals.
- Final arbitration priority is independent of migration order.
- New pass reports must remain JSON-safe.
- Reuse existing legacy helper functions via lazy import — do not duplicate them.
- Add only the tests directly covering this phase; do not broaden to the whole OCR suite inside task steps.
- Do not implement group-aware sequential, classic sequential, composite-parent settlement, completeness/accounting, or final cutover in this plan.

---

### Task 1: Populate sidecar_candidates and bundle_source_legend_ids in FigureCandidateIndex

**Rationale:** `FigureCandidateIndex` currently leaves `sidecar_candidates={}` and `bundle_source_legend_ids=set()` empty. The special fallback passes need these pre-computed. This task populates them in `from_corpus` without changing any existing field.

**Files:**
- Modify: `paperforge/worker/ocr_figure_vnext_corpus.py`
- Modify: `tests/test_ocr_figure_vnext_corpus.py`

**Interfaces:**
- Consumes:
  - `FigureCorpus` (raw_legends, raw_assets, page_width)
  - `ocr_figures._same_page_narrow_caption_column(legends, page_width) -> list[dict]`
  - `ocr_figures._identify_bundle_source_legend_ids(legends, assets) -> set[str]`
- Produces:
  - `FigureCandidateIndex.sidecar_candidates` populated as `dict[int, list[dict]]` (page → narrow caption set, only pages with ≥2 narrow captions)
  - `FigureCandidateIndex.bundle_source_legend_ids` populated from `_identify_bundle_source_legend_ids`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_ocr_figure_vnext_corpus.py`:

```python
def test_candidate_index_populates_sidecar_candidates_for_narrow_caption_page():
    # 3 narrow captions on page 5, each with width < page_width * 0.4
    # Assert index.sidecar_candidates has page 5 with 3 entries
    ...


def test_candidate_index_populates_bundle_source_legend_ids():
    # legends + assets where _identify_bundle_source_legend_ids returns non-empty
    # Assert index.bundle_source_legend_ids is non-empty
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_figure_vnext_corpus.py -k "sidecar_candidates or bundle_source" -v`
Expected: FAIL

- [ ] **Step 3: Populate the fields in `from_corpus`**

```python
# In FigureCandidateIndex.from_corpus, before the return:
sidecar_candidates: dict[int, list[dict]] = {}
_legends_by_page: dict[int, list[dict]] = {}
for leg in formal_legends:
    _legends_by_page.setdefault(int(leg.get("page", 0) or 0), []).append(leg)
for sp, spl in _legends_by_page.items():
    narrow_set = ocr_figures._same_page_narrow_caption_column(spl, corpus.page_width)
    if len(narrow_set) >= 2:
        sidecar_candidates[sp] = narrow_set

bundle_source_legend_ids = ocr_figures._identify_bundle_source_legend_ids(
    formal_legends, corpus.raw_assets
)

# Update the return cls(...) to pass:
#   sidecar_candidates=sidecar_candidates,
#   bundle_source_legend_ids=bundle_source_legend_ids,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_figure_vnext_corpus.py -v`
Expected: PASS (all existing + new)

- [ ] **Step 5: Run full vnext suite to confirm no regressions**

Run: `python -m pytest tests/test_ocr_figure_vnext_*.py -q`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_figure_vnext_corpus.py tests/test_ocr_figure_vnext_corpus.py
git commit -m "feat(ocr): populate sidecar_candidates and bundle_source_legend_ids in vnext index"
```

### Task 2: Implement SidecarPass

**Rationale:** The legacy sidecar fallback (ocr_figures.py:4043-4258) handles narrow-caption-column pages where normal spatial matching fails. It detects pages with ≥2 narrow captions, partitions assets into caption bands, and re-matches using band geometry instead of gap/overlap. This pass ports that logic into the proposal-then-commit model.

**Files:**
- Modify: `paperforge/worker/ocr_figure_vnext_passes.py`
- Modify: `tests/test_ocr_figure_vnext_passes.py`

**Interfaces:**
- Consumes:
  - `FigurePipelineState` (candidate_index.sidecar_candidates, corpus.raw_assets, state.matches)
  - `OwnershipLedger` (try_claim_assets, owner_of_asset)
  - `ocr_figures._partition_assets_by_caption_bands(captions, assets, page_height) -> dict[str, list[dict]]`
  - `ocr_figures._has_protected_figure_ownership(entry) -> bool`
  - `ocr_figures._fallback_eligible_asset_page_ids(...)`
  - `ocr_figures._extract_figure_number`, `_extract_figure_namespace`, `_format_figure_id`, `_project_asset_record`, `_cluster_bbox`
- Produces:
  - `SidecarPass.run(state) -> PassReport`

- [ ] **Step 1: Write failing sidecar pass tests**

Add to `tests/test_ocr_figure_vnext_passes.py`:

```python
from paperforge.worker.ocr_figure_vnext_passes import SidecarPass


def test_sidecar_pass_matches_narrow_captions_to_asset_bands():
    # Page 5 with 3 narrow captions (width < 400 on page_width=1200)
    # and 3 assets on the same page. PrimarySamePagePass should miss
    # (or mismatch) because narrow captions break spatial matching.
    # SidecarPass should partition assets into bands and match each
    # caption to its band.
    # Assert: report.accepted has matches, state.matches includes
    # sidecar entries with settlement_type="sidecar"
    ...


def test_sidecar_pass_skips_pages_with_fewer_than_two_narrow_captions():
    # Page with only 1 narrow caption → no sidecar trigger
    # Assert: report.accepted is empty
    ...


def test_sidecar_pass_does_not_steal_assets_from_same_page_matches():
    # Page with 2 narrow captions, but one already matched by
    # PrimarySamePagePass with protected ownership.
    # Assert: only the unprotected caption gets a sidecar match
    ...
```

- [ ] **Step 2: Run failing tests**

Run: `python -m pytest tests/test_ocr_figure_vnext_passes.py -k sidecar -v`
Expected: FAIL

- [ ] **Step 3: Implement SidecarPass**

```python
class SidecarPass:
    name = "sidecar"

    def run(self, state):
        from . import ocr_figures
        report = PassReport(pass_name=self.name)

        for sidecar_page, narrow_set in state.candidate_index.sidecar_candidates.items():
            nid_set = {str(cap.get("block_id", "")) for cap in narrow_set}
            # Skip if all narrow captions already matched
            page_narrow_matched = [
                m for m in state.matches
                if str(m.get("legend_block_id", "")) in nid_set
            ]
            if len(page_narrow_matched) == len(narrow_set):
                continue

            page_assets = [
                a for a in state.corpus.raw_assets
                if _resource_page(a) == sidecar_page
            ]
            if not page_assets:
                continue

            # Compute page height from blocks
            page_height = float(
                max(
                    (b.get("bbox") or [0, 0, 0, 0])[3]
                    for b in state.corpus.blocks
                    if _resource_page(b) == sidecar_page
                ) or 1600
            )
            band_map = ocr_figures._partition_assets_by_caption_bands(
                narrow_set, page_assets, page_height
            )

            for cap in narrow_set:
                lid = str(cap.get("block_id", ""))
                if lid in {str(m.get("legend_block_id", "")) for m in page_narrow_matched
                           if ocr_figures._has_protected_figure_ownership(m)}:
                    continue
                band_assets = band_map.get(lid, [])
                if not band_assets:
                    continue

                # Build asset refs and check ownership
                asset_refs = [
                    ResourceRef(kind="asset", page=sidecar_page, block_id=str(a.get("block_id", "")))
                    for a in band_assets if a.get("block_id")
                ]
                # Skip if any asset already owned
                owned = [r for r in asset_refs if state.ledger.owner_of(r) is not None]
                if owned:
                    continue

                cap_text = str(cap.get("text", ""))
                fig_num = ocr_figures._extract_figure_number(cap_text)
                cap_ns = ocr_figures._extract_figure_namespace(cap_text)
                legend_ref = ResourceRef(kind="legend", page=sidecar_page, block_id=lid, figure_no=fig_num)

                proposal = ClaimProposal(
                    pass_name=self.name,
                    figure_no=fig_num,
                    claim_type="match",
                    legends=[legend_ref],
                    assets=asset_refs,
                    groups=[],
                    confidence=0.5,
                    evidence_rank=3,
                    reason="sidecar_band_partition",
                    diagnostics={
                        "evidence": ["narrow_caption_column", "sidecar_fallback", "caption_band_partition"],
                        "sidecar_page": sidecar_page,
                    },
                )
                conflict = state.ledger.try_claim_assets(asset_refs, owner=legend_ref, reason=proposal.reason)
                if conflict is not None:
                    report.conflicts.append(conflict)
                    report.rejected.append(proposal)
                    continue

                fig_id = (
                    ocr_figures._format_figure_id(cap_ns, fig_num)
                    if fig_num
                    else f"figure_sidecar_{len(state.matches):03d}"
                )
                matched_assets = [ocr_figures._project_asset_record(a) for a in band_assets]
                match_record = {
                    "figure_id": fig_id,
                    "figure_namespace": cap_ns,
                    "figure_number": fig_num,
                    "legend_block_id": lid,
                    "page": sidecar_page,
                    "text": cap_text,
                    "matched_assets": matched_assets,
                    "asset_block_ids": sorted(str(r.block_id) for r in asset_refs),
                    "settlement_type": "sidecar",
                    "confidence": 0.5,
                    "match_score": {"score": 0.5, "decision": "matched", "evidence": ["sidecar_fallback"]},
                    "flags": ["sidecar_match"],
                    "bridge_block_ids": [],
                }
                if len(band_assets) > 1:
                    match_record["cluster_bbox"] = ocr_figures._cluster_bbox(
                        [a.get("bbox", [0, 0, 0, 0]) for a in band_assets]
                    )
                state.accept_match(proposal, match_record)
                report.accepted.append(proposal)

        return report
```

- [ ] **Step 4: Run sidecar tests**

Run: `python -m pytest tests/test_ocr_figure_vnext_passes.py -k sidecar -v`
Expected: PASS

- [ ] **Step 5: Run full passes test file**

Run: `python -m pytest tests/test_ocr_figure_vnext_passes.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_figure_vnext_passes.py tests/test_ocr_figure_vnext_passes.py
git commit -m "feat(ocr): add vnext SidecarPass"
```

### Task 3: Implement LegendBundlePass

**Rationale:** The legacy legend-bundle fallback (ocr_figures.py:4260-4381) handles pages with ≥3 figure captions and zero same-page assets — it matches captions 1:1 by page order to subsequent pages that each hold unclaimed assets. This is common in preproof/early-view layouts.

**Files:**
- Modify: `paperforge/worker/ocr_figure_vnext_passes.py`
- Modify: `tests/test_ocr_figure_vnext_passes.py`

**Interfaces:**
- Consumes:
  - `FigurePipelineState` (candidate_index.deduped_legends, candidate_index.bundle_source_legend_ids, corpus.raw_assets, corpus.blocks, state.matches, ledger)
  - `ocr_figures._extract_figure_number`, `_extract_figure_namespace`, `_format_figure_id`, `_project_asset_record`, `score_figure_caption`
- Produces:
  - `LegendBundlePass.run(state) -> PassReport`

- [ ] **Step 1: Write failing legend bundle tests**

```python
from paperforge.worker.ocr_figure_vnext_passes import LegendBundlePass


def test_legend_bundle_pass_matches_captions_to_subsequent_asset_pages():
    # Page 3 with 3 captions (Figure 1, 2, 3) and zero assets.
    # Pages 4, 5, 6 each have 1 unclaimed asset and no body/table blocks.
    # Assert: 3 matches created, each caption → one asset page in order.
    # Assert: settlement_type="legend_bundle", flags includes "legend_bundle_match"
    ...


def test_legend_bundle_pass_requires_minimum_three_captions():
    # Page with only 2 captions → no bundle trigger
    # Assert: report.accepted is empty
    ...


def test_legend_bundle_pass_skips_when_intervening_pages_have_body_text():
    # Captions on page 3, assets on page 5, but page 4 has body_paragraph blocks
    # Assert: no bundle match (intervening body breaks the chain)
    ...
```

- [ ] **Step 2: Run failing tests**

Run: `python -m pytest tests/test_ocr_figure_vnext_passes.py -k legend_bundle -v`
Expected: FAIL

- [ ] **Step 3: Implement LegendBundlePass**

Port the legacy logic (ocr_figures.py:4260-4381) into the proposal-then-commit model. Key structure:

```python
class LegendBundlePass:
    name = "legend_bundle"

    def run(self, state):
        from . import ocr_figures
        report = PassReport(pass_name=self.name)

        matched_legend_ids = {str(m.get("legend_block_id", "")) for m in state.matches}
        unmatched_legends = [
            leg for leg in state.candidate_index.deduped_legends
            if str(leg.get("block_id", "")) not in matched_legend_ids
        ]
        # Compute unmatched assets (not owned by ledger)
        unmatched_assets = [
            a for a in state.corpus.raw_assets
            if (_resource_page(a) is not None
                and state.ledger.owner_of_asset(
                    page=_resource_page(a), block_id=a.get("block_id")
                ) is None)
        ]
        if not unmatched_legends or not unmatched_assets:
            return report

        # Group unmatched numbered legends by page
        page_captions: dict[int, list[dict]] = {}
        for leg in unmatched_legends:
            cp = _resource_page(leg)
            if cp is None:
                continue
            if ocr_figures._extract_figure_number(str(leg.get("text", ""))) is not None:
                page_captions.setdefault(cp, []).append(leg)

        _NON_PURE_ROLES = {
            "body_paragraph", "section_heading", "subsection_heading",
            "table_caption", "table_asset", "table_html",
            "backmatter_heading", "backmatter_body", "reference_item",
        }

        for cp, caps in sorted(page_captions.items()):
            has_bundle_source = any(
                str(cap.get("block_id", "")) in state.candidate_index.bundle_source_legend_ids
                for cap in caps
            )
            if len(caps) < 3 and not has_bundle_source:
                continue
            page_has_assets = any(_resource_page(a) == cp for a in unmatched_assets)
            if page_has_assets:
                continue

            caps_sorted = sorted(caps, key=lambda b: (b.get("bbox") or [0, 0, 0, 0])[1])
            # Collect subsequent pages with unclaimed assets
            asset_pages: dict[int, list[dict]] = {}
            for ast in unmatched_assets:
                ap = _resource_page(ast)
                if ap is None or ap <= cp:
                    continue
                if state.ledger.owner_of_asset(page=ap, block_id=ast.get("block_id")) is not None:
                    continue
                asset_pages.setdefault(ap, []).append(ast)

            page_order = sorted(asset_pages.keys())
            if not page_order:
                continue
            # Check no body/table on intervening pages
            intervening_pages = set(range(cp + 1, page_order[0]))
            intervening_body = any(
                _resource_page(b) in intervening_pages
                and b.get("role", "") in _NON_PURE_ROLES
                for b in state.corpus.blocks
            )
            if intervening_body:
                continue

            valid_pages = []
            for ap in page_order:
                page_has_body = any(
                    _resource_page(b) == ap and b.get("role", "") in _NON_PURE_ROLES
                    for b in state.corpus.blocks
                )
                if not page_has_body:
                    valid_pages.append(ap)

            if len(valid_pages) < len(caps_sorted):
                caps_sorted = caps_sorted[:len(valid_pages)]
            if not valid_pages:
                continue

            for idx, cap in enumerate(caps_sorted):
                if idx >= len(valid_pages):
                    break
                ap = valid_pages[idx]
                page_assets = asset_pages[ap]
                if not page_assets:
                    continue

                fn = ocr_figures._extract_figure_number(str(cap.get("text", "")))
                cap_ns = ocr_figures._extract_figure_namespace(str(cap.get("text", "")))
                fig_id = ocr_figures._format_figure_id(cap_ns, fn)
                cap_ref = ResourceRef(kind="legend", page=cp, block_id=str(cap.get("block_id", "")), figure_no=fn)

                asset_refs = [
                    ResourceRef(kind="asset", page=ap, block_id=str(a.get("block_id", "")))
                    for a in page_assets if a.get("block_id")
                ]
                proposal = ClaimProposal(
                    pass_name=self.name,
                    figure_no=fn,
                    claim_type="match",
                    legends=[cap_ref],
                    assets=asset_refs,
                    groups=[],
                    confidence=0.3,
                    evidence_rank=4,
                    reason="legend_bundle_fallback",
                    diagnostics={
                        "evidence": ["legend_bundle_fallback", "page_order_match"],
                        "legend_page": cp,
                        "asset_page": ap,
                    },
                )
                conflict = state.ledger.try_claim_assets(asset_refs, owner=cap_ref, reason=proposal.reason)
                if conflict is not None:
                    report.conflicts.append(conflict)
                    report.rejected.append(proposal)
                    continue

                matched_assets = [ocr_figures._project_asset_record(a) for a in page_assets]
                match_record = {
                    "figure_id": fig_id,
                    "figure_namespace": cap_ns,
                    "figure_number": fn,
                    "legend_block_id": str(cap.get("block_id", "")),
                    "page": ap,
                    "text": str(cap.get("text", "")),
                    "matched_assets": matched_assets,
                    "asset_block_ids": sorted(str(r.block_id) for r in asset_refs),
                    "settlement_type": "legend_bundle",
                    "confidence": 0.3,
                    "match_score": {"score": 0.3, "decision": "matched", "evidence": ["legend_bundle_fallback"]},
                    "flags": ["legend_bundle_match"],
                    "legend_page": cp,
                    "asset_pages": [ap],
                    "bridge_block_ids": [],
                }
                state.accept_match(proposal, match_record)
                report.accepted.append(proposal)

        return report
```

- [ ] **Step 4: Run legend bundle tests**

Run: `python -m pytest tests/test_ocr_figure_vnext_passes.py -k legend_bundle -v`
Expected: PASS

- [ ] **Step 5: Run full passes test file**

Run: `python -m pytest tests/test_ocr_figure_vnext_passes.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_figure_vnext_passes.py tests/test_ocr_figure_vnext_passes.py
git commit -m "feat(ocr): add vnext LegendBundlePass"
```

### Task 4: Implement LocatorBridgePass

**Rationale:** The legacy locator bridge (ocr_figures.py:4384-4578) connects three components when a paper uses "See legend on previous page" locator captions: (1) full legend on the previous page, (2) visual group on the locator's page, (3) the locator caption itself. This pass ports that three-way bridge into the proposal model.

**Files:**
- Modify: `paperforge/worker/ocr_figure_vnext_passes.py`
- Modify: `tests/test_ocr_figure_vnext_passes.py`

**Interfaces:**
- Consumes:
  - `FigurePipelineState` (candidate_index.locator_candidates, candidate_index.rejected_legends, candidate_index.deduped_legends, corpus.raw_assets, corpus.blocks, state.matches, ledger)
  - `ocr_figures._is_previous_page_legend_locator`, `_extract_figure_number`, `_extract_figure_namespace`, `_format_figure_id`, `_project_asset_record`, `_cluster_bbox`, `_is_tight_asset_cluster`, `score_figure_caption`
- Produces:
  - `LocatorBridgePass.run(state) -> PassReport`

- [ ] **Step 1: Write failing locator bridge tests**

```python
from paperforge.worker.ocr_figure_vnext_passes import LocatorBridgePass


def test_locator_bridge_connects_full_legend_to_visual_group():
    # Page 4: full legend "Figure 5. ..." (unmatched, ≥60 chars)
    # Page 5: locator "Fig. 5 (See legend on previous page.)" + assets above locator
    # Assert: match created with:
    #   - legend_block_id = full legend's block_id
    #   - locator_block_id in bridge_block_ids
    #   - settlement_type = "previous_page_legend_locator"
    #   - flags includes "previous_page_locator_match"
    ...


def test_locator_bridge_skips_when_no_full_legend_on_previous_page():
    # Locator on page 5, but no matching figure number on page 4
    # Assert: report.accepted is empty
    ...


def test_locator_bridge_skips_when_assets_already_owned():
    # Locator on page 5, full legend on page 4, but assets on page 5
    # already claimed by same-page match
    # Assert: no bridge match (assets protected)
    ...
```

- [ ] **Step 2: Run failing tests**

Run: `python -m pytest tests/test_ocr_figure_vnext_passes.py -k locator_bridge -v`
Expected: FAIL

- [ ] **Step 3: Implement LocatorBridgePass**

Port the legacy logic (ocr_figures.py:4384-4578) into the proposal model. Key structure:

```python
class LocatorBridgePass:
    name = "locator_bridge"

    def run(self, state):
        from . import ocr_figures
        report = PassReport(pass_name=self.name)

        locators = state.candidate_index.locator_candidates
        if not locators:
            return report

        matched_legend_ids = {str(m.get("legend_block_id", "")) for m in state.matches}
        unmatched_legends = [
            leg for leg in state.candidate_index.deduped_legends
            if str(leg.get("block_id", "")) not in matched_legend_ids
        ]
        # Also scan rejected_legends for full legends misclassified as body_paragraph
        # (legacy pattern: ocr_figures.py:4402-4415)
        _unmatched_by_number: dict[tuple[str, int], list[dict]] = {}
        for leg in unmatched_legends:
            fn = ocr_figures._extract_figure_number(str(leg.get("text", "")))
            if fn is None:
                continue
            ns = ocr_figures._extract_figure_namespace(str(leg.get("text", "")))
            _unmatched_by_number.setdefault((ns, fn), []).append(leg)
        for leg in state.candidate_index.rejected_legends:
            fn = ocr_figures._extract_figure_number(str(leg.get("text", "")))
            if fn is None:
                continue
            ns = ocr_figures._extract_figure_namespace(str(leg.get("text", "")))
            key = (ns, fn)
            if key in _unmatched_by_number:
                continue
            style = str(leg.get("style_family") or "")
            zone = str(leg.get("zone") or "")
            if style == "legend_like" and zone in ("display_zone", ""):
                _unmatched_by_number.setdefault(key, []).append(leg)

        for locator in locators:
            locator_text = str(locator.get("text", "") or "")
            fn = ocr_figures._extract_figure_number(locator_text)
            if fn is None:
                continue
            ns = ocr_figures._extract_figure_namespace(locator_text)
            locator_page = _resource_page(locator)
            if locator_page is None or locator_page <= 1:
                continue
            prev_page = locator_page - 1

            # Find full legend on previous page with same figure_number
            full_legends = _unmatched_by_number.get((ns, fn), [])
            full_legend = None
            for leg in full_legends:
                lp = _resource_page(leg)
                if lp == prev_page:
                    leg_text = str(leg.get("text", "") or "")
                    if len(leg_text) >= 60 and not ocr_figures._is_previous_page_legend_locator(leg):
                        full_legend = leg
                        break
            if full_legend is None:
                continue

            # Find visual group above locator on locator's page
            locator_bbox = locator.get("bbox") or [0, 0, 0, 0]
            locator_top = locator_bbox[1] if len(locator_bbox) >= 4 else 0

            # Try candidate groups first
            best_group_assets: list[dict] = []
            for g in state.candidate_index.candidate_groups:
                gp = _resource_page(g)
                if gp != locator_page:
                    continue
                g_bbox = g.get("cluster_bbox") or [0, 0, 0, 0]
                if len(g_bbox) < 4 or g_bbox[3] > locator_top:
                    continue
                g_asset_ids = g.get("asset_block_ids", [])
                g_unowned_ids = [
                    bid for bid in g_asset_ids
                    if state.ledger.owner_of_asset(page=locator_page, block_id=bid) is None
                ]
                if not g_unowned_ids:
                    continue
                group_assets = [
                    a for a in state.corpus.raw_assets
                    if _resource_page(a) == locator_page
                    and str(a.get("block_id", "")) in g_unowned_ids
                ]
                if group_assets:
                    best_group_assets = group_assets
                    break

            # Fallback: tight cluster above locator
            if not best_group_assets:
                page_assets = [
                    a for a in state.corpus.raw_assets
                    if _resource_page(a) == locator_page
                    and state.ledger.owner_of_asset(
                        page=locator_page, block_id=a.get("block_id")
                    ) is None
                ]
                above = [a for a in page_assets if (a.get("bbox") or [0,0,0,0])[3] <= locator_top]
                if above and ocr_figures._is_tight_asset_cluster(above, locator_top):
                    best_group_assets = above

            if not best_group_assets:
                continue

            # Build and commit the bridge match
            full_ref = ResourceRef(
                kind="legend", page=prev_page,
                block_id=str(full_legend.get("block_id", "")), figure_no=fn
            )
            asset_refs = [
                ResourceRef(kind="asset", page=locator_page, block_id=str(a.get("block_id", "")))
                for a in best_group_assets if a.get("block_id")
            ]
            proposal = ClaimProposal(
                pass_name=self.name,
                figure_no=fn,
                claim_type="match",
                legends=[full_ref],
                assets=asset_refs,
                groups=[],
                confidence=0.5,
                evidence_rank=3,
                reason="previous_page_legend_locator",
                diagnostics={
                    "evidence": ["previous_page_locator_bridge", "explicit_previous_page_locator"],
                    "locator_block_id": str(locator.get("block_id", "")),
                    "locator_page": locator_page,
                    "full_legend_page": prev_page,
                },
            )
            conflict = state.ledger.try_claim_assets(asset_refs, owner=full_ref, reason=proposal.reason)
            if conflict is not None:
                report.conflicts.append(conflict)
                report.rejected.append(proposal)
                continue

            fig_id = ocr_figures._format_figure_id(ns, fn)
            consumed = [ocr_figures._project_asset_record(a) for a in best_group_assets]
            asset_bboxes = [a.get("bbox") or [0, 0, 0, 0] for a in best_group_assets]
            valid_bboxes = [b for b in asset_bboxes if len(b) >= 4 and b[2] > b[0] and b[3] > b[1]]
            cluster_bbox = ocr_figures._cluster_bbox(valid_bboxes) if valid_bboxes else [0, 0, 0, 0]
            match_record = {
                "figure_id": fig_id,
                "figure_namespace": ns,
                "figure_number": fn,
                "legend_block_id": str(full_legend.get("block_id", "")),
                "legend_page": prev_page,
                "text": str(full_legend.get("text", "")),
                "matched_assets": consumed,
                "asset_block_ids": sorted(str(r.block_id) for r in asset_refs),
                "cluster_bbox": cluster_bbox,
                "group_type": "previous_page_locator_bridge",
                "settlement_type": "previous_page_legend_locator",
                "confidence": 0.5,
                "match_score": {"score": 0.5, "decision": "matched", "evidence": ["previous_page_locator_bridge"]},
                "flags": ["previous_page_locator_match"],
                "page": locator_page,
                "locator_block_id": str(locator.get("block_id", "")),
                "locator_page": locator_page,
                "asset_pages": [locator_page],
                "bridge_block_ids": [str(locator.get("block_id", ""))],
            }
            state.accept_match(proposal, match_record)
            report.accepted.append(proposal)

        return report
```

- [ ] **Step 4: Run locator bridge tests**

Run: `python -m pytest tests/test_ocr_figure_vnext_passes.py -k locator_bridge -v`
Expected: PASS

- [ ] **Step 5: Run full passes test file**

Run: `python -m pytest tests/test_ocr_figure_vnext_passes.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_figure_vnext_passes.py tests/test_ocr_figure_vnext_passes.py
git commit -m "feat(ocr): add vnext LocatorBridgePass"
```

### Task 5: Wire special fallback passes into orchestrator + portable fixture

**Rationale:** The orchestrator must run all passes in the correct order per spec §7.3: Layer 1 (same-page, sidecar, locator) then Layer 2 (cross-page reservation/settlement, legend bundle). This task wires the three new passes and adds a third real-paper fixture.

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Create: `tests/fixtures/ocr_vnext_real_papers/<KEY>/blocks.structured.jsonl` (a sidecar or locator-bridge paper from the OCR vault)
- Modify: `tests/test_ocr_figure_vnext_real_papers.py`

**Pass ordering (spec §7.3):**
1. `PrimarySamePagePass` (Layer 1)
2. `SidecarPass` (Layer 1)
3. `LocatorBridgePass` (Layer 1)
4. `CrossPageReservationPass` (Layer 2)
5. `CrossPageSettlementPass` (Layer 2)
6. `LegendBundlePass` (Layer 2)

- [ ] **Step 1: Update the orchestrator**

```python
# In build_figure_inventory_vnext:
from .ocr_figure_vnext_passes import (
    CrossPageReservationPass,
    CrossPageSettlementPass,
    LegendBundlePass,
    LocatorBridgePass,
    PrimarySamePagePass,
    SidecarPass,
    _resource_page,
)
...
reports = []
for pass_cls in (
    PrimarySamePagePass,
    SidecarPass,
    LocatorBridgePass,
    CrossPageReservationPass,
    CrossPageSettlementPass,
    LegendBundlePass,
):
    reports.append(pass_cls().run(state))
```

- [ ] **Step 2: Add a third real-paper fixture**

Find a paper from `D:/L/OB/Literature-hub/System/PaperForge/ocr/` that triggers sidecar or locator-bridge (check for narrow caption columns or "See legend on previous page" text). Copy its `blocks.structured.jsonl` into `tests/fixtures/ocr_vnext_real_papers/<KEY>/`.

If no suitable paper is found, use `2HEUD5P9` (already in the fixture set) and add assertions for the new pass reports instead.

- [ ] **Step 3: Add fixture-backed test**

```python
def test_real_paper_special_fallbacks_reports_diff_shape():
    blocks_path = Path("tests/fixtures/ocr_vnext_real_papers/<KEY>/blocks.structured.jsonl")
    diff = compare_blocks_file(blocks_path)

    assert diff["paper"] == "<KEY>"
    assert "legacy_matched_count" in diff
    assert "vnext_matched_count" in diff
```

- [ ] **Step 4: Run all vnext tests**

Run: `python -m pytest tests/test_ocr_figure_vnext_*.py -q`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figures.py tests/fixtures/ocr_vnext_real_papers/<KEY>/ tests/test_ocr_figure_vnext_real_papers.py
git commit -m "feat(ocr): wire vnext special fallback passes into orchestrator"
```

## Self-Review

- Spec coverage: This phase implements spec §7.3 Layer 1 (sidecar, locator bridge) and Layer 2 (legend bundle) special fallbacks. It does not implement group-aware sequential, classic sequential, composite-parent settlement, completeness/accounting, or cutover — those are left to Phase 4+.
- Helper reuse: All three passes reuse existing legacy helper functions via lazy import. No helper duplication.
- Layer ordering: Passes are wired in spec §7.3 layer order. Lower layers cannot steal from higher layers because `OwnershipLedger.try_claim_assets` rejects already-owned assets.
- Placeholder scan: No `TBD` or `TODO` in task steps. The `<KEY>` placeholder in Task 5 is resolved during implementation by selecting a real paper from the OCR vault.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-03-figure-pipeline-vnext-phase3-special-fallbacks.md`. Two execution options:

1. **Subagent-Driven (recommended)** - One implementer per task, review gate after each
2. **Inline Execution** - Batch execution with checkpoints

Which approach?
