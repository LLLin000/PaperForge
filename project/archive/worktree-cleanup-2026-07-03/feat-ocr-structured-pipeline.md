# Worktree cleanup archive — feat-ocr-structured-pipeline

- Path: `D:/L/Med/Research/99_System/LiteraturePipeline/github-release/.worktrees/feat-ocr-structured-pipeline`
- Branch: `feat/ocr-structured-pipeline`
- HEAD: `6d4ecc3 fix: skip single-block unresolved clusters — lonely subpanel assets are not clusters`
- Branches containing HEAD:

```
"feat/ocr-structured-pipeline"
"master"
```

## git status --short

```
 M paperforge/worker/ocr.py
 M paperforge/worker/ocr_blocks.py
 M paperforge/worker/ocr_figures.py
 M paperforge/worker/ocr_health.py
 M paperforge/worker/ocr_objects.py
 M paperforge/worker/ocr_roles.py
 M tests/test_ocr_figures.py
 M tests/test_ocr_metadata.py
?? docs/superpowers/plans/2026-06-06-ocr-convergence-phase-2-plan.md
?? docs/superpowers/plans/2026-06-06-ocr-dead-code-and-closure-plan.md
?? docs/superpowers/plans/2026-06-06-ocr-final-polish-and-math-normalization-plan.md
?? docs/superpowers/plans/2026-06-06-ocr-full-pipeline-convergence-plan.md
?? docs/superpowers/plans/2026-06-06-ocr-heuristic-gating-remediation-plan.md
?? docs/superpowers/plans/2026-06-06-ocr-layout-aware-tail-reading-plan.md
?? docs/superpowers/plans/2026-06-07-ocr-cross-layout-hardening-plan.md
?? docs/superpowers/plans/2026-06-07-ocr-real-paper-regression-closure-plan.md
?? docs/superpowers/plans/2026-06-07-ocr-structural-convergence-master-plan.md
?? docs/superpowers/plans/2026-06-07-tsckavis-structural-fix-plan.md
?? docs/superpowers/plans/2026-06-08-ocr-decision-log-plan.md
?? docs/superpowers/plans/2026-06-08-ocr-error-taxonomy-plan.md
?? docs/superpowers/plans/2026-06-08-ocr-evidence-scorer-plan.md
?? docs/superpowers/plans/2026-06-08-ocr-p0-bugfix-plan.md
?? docs/superpowers/plans/2026-06-08-ocr-real-fixtures-ci-plan.md
?? docs/superpowers/plans/2026-06-08-ocr-route-audit-plan.md
?? docs/superpowers/plans/2026-06-08-ocr-v1-convergence-master-plan.md
?? docs/superpowers/reports/
?? scripts/dev/audit_10_papers.py
?? scripts/dev/check_m36_figures.py
?? scripts/dev/check_rebuild_results.py
?? scripts/dev/rebuild_10_papers.py
```

## Untracked files

```
docs/superpowers/plans/2026-06-06-ocr-convergence-phase-2-plan.md
docs/superpowers/plans/2026-06-06-ocr-dead-code-and-closure-plan.md
docs/superpowers/plans/2026-06-06-ocr-final-polish-and-math-normalization-plan.md
docs/superpowers/plans/2026-06-06-ocr-full-pipeline-convergence-plan.md
docs/superpowers/plans/2026-06-06-ocr-heuristic-gating-remediation-plan.md
docs/superpowers/plans/2026-06-06-ocr-layout-aware-tail-reading-plan.md
docs/superpowers/plans/2026-06-07-ocr-cross-layout-hardening-plan.md
docs/superpowers/plans/2026-06-07-ocr-real-paper-regression-closure-plan.md
docs/superpowers/plans/2026-06-07-ocr-structural-convergence-master-plan.md
docs/superpowers/plans/2026-06-07-tsckavis-structural-fix-plan.md
docs/superpowers/plans/2026-06-08-ocr-decision-log-plan.md
docs/superpowers/plans/2026-06-08-ocr-error-taxonomy-plan.md
docs/superpowers/plans/2026-06-08-ocr-evidence-scorer-plan.md
docs/superpowers/plans/2026-06-08-ocr-p0-bugfix-plan.md
docs/superpowers/plans/2026-06-08-ocr-real-fixtures-ci-plan.md
docs/superpowers/plans/2026-06-08-ocr-route-audit-plan.md
docs/superpowers/plans/2026-06-08-ocr-v1-convergence-master-plan.md
docs/superpowers/reports/2026-06-07-cross-layout-validation-report.md
scripts/dev/audit_10_papers.py
scripts/dev/check_m36_figures.py
scripts/dev/check_rebuild_results.py
scripts/dev/rebuild_10_papers.py
```

## Binary-safe diff

```diff
diff --git a/paperforge/worker/ocr.py b/paperforge/worker/ocr.py
index bb47777..f4f4926 100644
--- a/paperforge/worker/ocr.py
+++ b/paperforge/worker/ocr.py
@@ -1831,7 +1831,7 @@ def postprocess_ocr_result(vault: Path, key: str, all_results: list[dict]) -> tu
     metadata_dir.mkdir(parents=True, exist_ok=True)
     frontmatter_candidates = extract_frontmatter_candidates(artifacts.blocks_structured)
     page1_raw = [b for b in all_raw_blocks if b.get("page") == 1] if all_raw_blocks else None
-    resolved = resolve_metadata(source_meta, frontmatter_candidates, page1_blocks=page1_raw)
+    resolved = resolve_metadata(source_meta, frontmatter_candidates, page1_blocks=page1_raw, structured_blocks=structured)
     write_resolved_metadata(metadata_dir / "resolved_metadata.json", resolved)
 
     # --- Phase 2: figure inventory ---
diff --git a/paperforge/worker/ocr_blocks.py b/paperforge/worker/ocr_blocks.py
index 3f8b8b3..a31d7f4 100644
--- a/paperforge/worker/ocr_blocks.py
+++ b/paperforge/worker/ocr_blocks.py
@@ -54,9 +54,9 @@ def build_structured_blocks(
             )
             render_default = role.role not in ({"noise", "unknown_structural"} | _CANDIDATE_ROLES)
             index_default = role.role not in _CANDIDATE_ROLES
-            if role.role in {"noise", "page_header", "page_footer", "frontmatter_noise", "non_body_insert", "structured_insert"}:
+            if role.role in {"noise", "page_header", "page_footer", "frontmatter_noise", "non_body_insert", "structured_insert", "figure_inner_text"}:
                 render_default = False
-            if role.role in {"noise", "frontmatter_noise", "table_html", "non_body_insert", "structured_insert"}:
+            if role.role in {"noise", "frontmatter_noise", "table_html", "non_body_insert", "structured_insert", "figure_inner_text"}:
                 index_default = False
             row = {
                 "paper_id": block["paper_id"],
@@ -141,10 +141,10 @@ def build_structured_blocks(
             row["index_default"] = False
         else:
             row["render_default"] = role not in ({"noise", "unknown_structural"} | _CANDIDATE_ROLES)
-            if role in {"noise", "page_header", "page_footer", "frontmatter_noise", "non_body_insert", "structured_insert"}:
+            if role in {"noise", "page_header", "page_footer", "frontmatter_noise", "non_body_insert", "structured_insert", "figure_inner_text"}:
                 row["render_default"] = False
             row["index_default"] = role not in _CANDIDATE_ROLES
-            if role in {"noise", "frontmatter_noise", "table_html", "non_body_insert", "structured_insert"}:
+            if role in {"noise", "frontmatter_noise", "table_html", "non_body_insert", "structured_insert", "figure_inner_text"}:
                 row["index_default"] = False
 
     # Persist document structure artifact for downstream debugging
diff --git a/paperforge/worker/ocr_figures.py b/paperforge/worker/ocr_figures.py
index 5575655..51fffe5 100644
--- a/paperforge/worker/ocr_figures.py
+++ b/paperforge/worker/ocr_figures.py
@@ -54,22 +54,18 @@ def _looks_like_inline_figure_mention(text: str) -> bool:
     if not re.search(r"\bfi(?:g(?:ure)?\.?\s*\d+)", lower):
         return False
 
-    # Explicitly NOT inline: Frontiers format FIGURE N | ...
     if re.match(r"^figure\s+\d+[a-z]?\s*\|", t, re.I):
         return False
 
-    # "as shown in Figure X" / "shown in Figure X" / "see Figure X"
     if re.search(r"\b(as shown in|shown in|see |according to|consistent with)\s+(fig(?:ure)?\.?\s*\d+)", lower):
         return True
 
-    # Long sentence with a prose verb
     words = t.split()
     if len(words) >= 10 and any(re.search(rf"\b{v}\b", lower) for v in _INLINE_FIGURE_MENTION_VERBS):
         return True
 
     return False
 
-
 def _extract_figure_number(text: str) -> int | None:
     m = _FIGURE_NUMBER_PATTERN.search(text)
     if m:
@@ -107,6 +103,10 @@ def _centroid_y(bbox: list[float]) -> float:
     return (bbox[1] + bbox[3]) / 2
 
 
+def _asset_key(block: dict) -> str:
+    return f"{int(block.get('page', 0) or 0)}:{block.get('block_id', '')}"
+
+
 def _looks_like_figure_narrative_prose(text: str) -> bool:
     if not text:
         return False
@@ -303,12 +303,24 @@ def _precaption_media_region(media_cluster: list[dict], caption_block: dict) ->
 def _compute_candidate_figure_regions(blocks: list[dict], page_width: float = 1200) -> list[dict]:
     clusters = _media_clusters(blocks, page_width)
     captions = [b for b in blocks if b.get("role") == "figure_caption"]
+
+    def _is_embedded_caption_like(block: dict) -> bool:
+        text = str(block.get("text", "") or "").strip()
+        if not text or _FIGURE_NUMBER_PATTERN.search(text):
+            return False
+        return is_embedded_figure_text(block, blocks, page_width=page_width)
+
     regions: list[dict] = []
     for i, cluster in enumerate(clusters):
         cluster_bbox = _cluster_bbox([b.get("bbox", [0, 0, 0, 0]) for b in cluster])
         page = cluster[0].get("page", 0)
         attached: list[dict] = []
         unvalidated: list[dict] = []
+        page_blocks = [b for b in blocks if int(b.get("page", 0) or 0) == page]
+        panel_like = any(
+            _PANEL_LABEL_PATTERN.match(str(b.get("text", "") or "").strip()) or _is_embedded_caption_like(b)
+            for b in page_blocks
+        )
         for cap in captions:
             if cap.get("page", 0) != page:
                 continue
@@ -324,11 +336,97 @@ def _compute_candidate_figure_regions(blocks: list[dict], page_width: float = 12
                 "media_blocks": cluster,
                 "attached_captions": attached,
                 "unvalidated_captions": unvalidated,
+                "region_type": "cluster",
+                "panel_like": panel_like,
             }
         )
+    regions.sort(key=lambda r: (r.get("page", 0), r.get("cluster_bbox", [0, 0, 0, 0])[1]))
     return regions
 
 
+def _score_legend_region(
+    legend: dict,
+    region: dict,
+    *,
+    caption_score: dict,
+    same_page_region_exists: bool,
+) -> dict:
+    proxy_asset = {
+        "block_id": region.get("region_id", ""),
+        "page": region.get("page", 0),
+        "bbox": region.get("cluster_bbox", [0, 0, 0, 0]),
+    }
+    if legend.get("page") == region.get("page"):
+        legend_bbox = legend.get("bbox") or legend.get("block_bbox") or [0, 0, 0, 0]
+        if len(region.get("media_blocks", [])) > 1 and len(legend_bbox) >= 4:
+            legend_top = legend_bbox[1]
+            legend_bottom = legend_bbox[3]
+            asset_tops = []
+            asset_bottoms = []
+            for asset in region.get("media_blocks", []):
+                ab = asset.get("bbox") or asset.get("block_bbox") or [0, 0, 0, 0]
+                if len(ab) >= 4:
+                    asset_tops.append(ab[1])
+                    asset_bottoms.append(ab[3])
+            if asset_tops and asset_bottoms:
+                has_asset_above = any(bottom <= legend_top for bottom in asset_bottoms)
+                has_asset_below = any(top >= legend_bottom for top in asset_tops)
+                if has_asset_above and has_asset_below and region.get("region_type") != "page_plate":
+                    return {
+                        "score": 0.45,
+                        "matched_asset_id": region.get("region_id", ""),
+                        "decision": "ambiguous",
+                        "evidence": ["caption_between_assets"],
+                    }
+        return score_figure_match(legend, proxy_asset, caption_score=caption_score)
+
+    if same_page_region_exists:
+        return {
+            "score": 0.0,
+            "matched_asset_id": region.get("region_id", ""),
+            "decision": "rejected",
+            "evidence": ["same_page_region_exists"],
+        }
+
+    if not region.get("panel_like") and len(region.get("media_blocks", [])) <= 1:
+        return {
+            "score": 0.0,
+            "matched_asset_id": region.get("region_id", ""),
+            "decision": "rejected",
+            "evidence": ["adjacent_match_requires_panel_like_cluster"],
+        }
+
+    page_gap = abs(int(legend.get("page", 0) or 0) - int(region.get("page", 0) or 0))
+    if page_gap != 1:
+        return {
+            "score": 0.0,
+            "matched_asset_id": region.get("region_id", ""),
+            "decision": "rejected",
+            "evidence": ["non_adjacent_region"],
+        }
+
+    score = min(0.15, float(caption_score.get("score", 0.0)) * 0.15) + 0.45
+    evidence = ["adjacent_page_region"]
+    legend_bbox = legend.get("bbox") or legend.get("block_bbox") or [0, 0, 0, 0]
+    if len(legend_bbox) >= 4:
+        if region.get("page", 0) < legend.get("page", 0) and legend_bbox[1] < 320:
+            score += 0.15
+            evidence.append("caption_page_after_figure")
+        elif region.get("page", 0) > legend.get("page", 0) and legend_bbox[3] > 900:
+            score += 0.15
+            evidence.append("caption_page_before_figure")
+    if region.get("panel_like"):
+        score += 0.1
+        evidence.append("panel_like_region")
+    score = max(0.0, min(1.0, score))
+    return {
+        "score": score,
+        "matched_asset_id": region.get("region_id", ""),
+        "decision": "matched_adjacent_region" if score >= 0.6 else "ambiguous" if score >= 0.4 else "rejected",
+        "evidence": evidence,
+    }
+
+
 def is_embedded_figure_text(block: dict, all_blocks: list[dict], page_width: float = 1200) -> bool:
     block_bbox = block.get("bbox") or block.get("block_bbox")
     if not block_bbox or len(block_bbox) < 4:
@@ -373,6 +471,8 @@ def build_figure_inventory(structured_blocks: list[dict], page_width: float = 12
         if block.get("page_width"):
             page_width = float(block["page_width"])
 
+    candidate_regions = _compute_candidate_figure_regions(structured_blocks, page_width)
+
     for block in structured_blocks:
         role = block.get("role", "")
         if block.get("_non_body_media") or role == "non_body_insert":
@@ -381,14 +481,21 @@ def build_figure_inventory(structured_blocks: list[dict], page_width: float = 12
         if _PANEL_LABEL_PATTERN.match(str(block.get("text", "")).strip()):
             continue
         if role in ("figure_caption", "figure_caption_candidate"):
+            if (
+                _extract_figure_number(block.get("text", "")) is None
+                and is_embedded_figure_text(block, structured_blocks, page_width)
+            ):
+                continue
             if _is_body_mention(block):
                 continue
+            if role == "figure_caption_candidate" and _looks_like_inline_figure_mention(block.get("text", "")):
+                unmatched_legends.append(block)
+                continue
             if role == "figure_caption_candidate" and _looks_like_figure_narrative_prose(block.get("text", "")):
                 continue
             if not _is_formal_legend(block.get("text", ""), block, page_width):
                 block["caption_score"] = score_figure_caption(
                     block, nearby_media=False, caption_style_match=False,
-                    body_prose_likelihood=_looks_like_inline_figure_mention(block.get("text", "")),
                 )
                 rejected_legends.append(block)
             else:
@@ -438,100 +545,160 @@ def build_figure_inventory(structured_blocks: list[dict], page_width: float = 12
             deduped_legends.append(legend)
     ordered_legends = deduped_legends
 
-    used_asset_indices: set[int] = set()
+    used_asset_ids: set[str] = set()
+    used_region_ids: set[str] = set()
     ambiguous_figures: list[dict] = []
     for legend in ordered_legends:
         legend_page = legend.get("page", 0)
         legend_text = legend.get("text", "")
         fig_num = _extract_figure_number(legend_text)
 
-        body_prose_likelihood = _looks_like_inline_figure_mention(legend_text)
-
         caption_score = score_figure_caption(
             legend,
             nearby_media=any(a.get("page", 0) == legend_page for a in assets),
             caption_style_match=_caption_style_match(legend, structured_blocks),
-            body_prose_likelihood=body_prose_likelihood,
         )
 
         candidates = []
-        for ai, asset in enumerate(assets):
-            if ai in used_asset_indices or asset.get("page", 0) != legend_page:
+        had_ambiguous_region_candidate = False
+        same_page_region_exists = any(
+            r.get("page", 0) == legend_page and r.get("region_id", "") not in used_region_ids
+            for r in candidate_regions
+        )
+        for region in candidate_regions:
+            region_id = region.get("region_id", "")
+            if not region_id or region_id in used_region_ids:
+                continue
+            region_asset_ids = {_asset_key(b) for b in region.get("media_blocks", [])}
+            if region_asset_ids & used_asset_ids:
                 continue
-            match_score = score_figure_match(legend, asset, caption_score=caption_score)
+            match_score = _score_legend_region(
+                legend,
+                region,
+                caption_score=caption_score,
+                same_page_region_exists=same_page_region_exists,
+            )
+            if match_score["decision"] == "ambiguous":
+                had_ambiguous_region_candidate = True
             if match_score["decision"] != "rejected":
-                candidates.append((ai, asset, match_score))
-        candidates.sort(key=lambda item: item[2]["score"], reverse=True)
+                candidates.append((region, match_score))
+        candidates.sort(key=lambda item: item[1]["score"], reverse=True)
 
         matched_assets = []
         region_match = None
         ambiguous = False
 
         if candidates:
-            top_score = candidates[0][2]["score"]
-            close = [item for item in candidates if top_score - item[2]["score"] < 0.15]
+            top_score = candidates[0][1]["score"]
+            close = [item for item in candidates if top_score - item[1]["score"] < 0.15]
             if top_score < 0.4:
                 matched_assets = []
             elif len(close) > 1:
-                # Secondary verification: pick the one in the correct column
-                legend_bb = legend.get("bbox") or legend.get("block_bbox") or [0,0,0,0]
-                lcx = (legend_bb[0] + legend_bb[2]) / 2 if len(legend_bb) >= 4 else 0
-                best = close[0]
-                best_col_match = False
-                for ci, ca, cs in close:
-                    ab = ca.get("bbox") or ca.get("block_bbox") or [0,0,0,0]
-                    acx = (ab[0] + ab[2]) / 2 if len(ab) >= 4 else 0
-                    ca_col_ok = abs(lcx - acx) < abs(lcx - (best[1].get("bbox",[0,0,0,0])[0] + best[1].get("bbox",[0,0,0,0])[2])/2)
-                    if ca_col_ok:
-                        best = (ci, ca, cs)
-                        best_col_match = True
-                        break
-                if best_col_match:
-                    best_idx, best_asset, best_score = best
-                    matched_assets = [best_asset]
-                    used_asset_indices.add(best_idx)
-                    region_match = {"media_blocks": [best_asset], "match_score": best_score}
+                same_page = all(item[0].get("page", 0) == close[0][0].get("page", 0) for item in close)
+                if close[0][0].get("panel_like") and top_score >= 0.7:
+                    best_region, best_score = candidates[0]
+                    matched_assets = list(best_region.get("media_blocks", []))
+                    used_region_ids.add(best_region.get("region_id", ""))
+                    used_asset_ids.update(_asset_key(a) for a in matched_assets)
+                    region_match = {
+                        "page": best_region.get("page", legend_page),
+                        "media_blocks": matched_assets,
+                        "cluster_bbox": best_region.get("cluster_bbox", [0, 0, 0, 0]),
+                        "match_score": best_score,
+                    }
                 else:
-                    ambiguous_figures.append({
-                        "legend_block_id": legend.get("block_id", ""),
-                        "page": legend_page,
-                        "caption_score": caption_score,
-                        "candidates": [
-                            {"asset_block_id": a.get("block_id", ""), "match_score": s}
-                            for _, a, s in close
-                        ],
-                    })
-                    ambiguous = True
-                    matched_assets = []
+                    legend_bb = legend.get("bbox") or legend.get("block_bbox") or [0,0,0,0]
+                    lcx = (legend_bb[0] + legend_bb[2]) / 2 if len(legend_bb) >= 4 else 0
+                    best = close[0]
+                    best_col_match = False
+                    for ca, cs in close:
+                        ab = ca.get("cluster_bbox") or [0,0,0,0]
+                        acx = (ab[0] + ab[2]) / 2 if len(ab) >= 4 else 0
+                        best_ab = best[0].get("cluster_bbox") or [0,0,0,0]
+                        ca_col_ok = abs(lcx - acx) < abs(lcx - (best_ab[0] + best_ab[2]) / 2)
+                        if ca_col_ok:
+                            best = (ca, cs)
+                            best_col_match = True
+                            break
+                    if best_col_match and best[0].get("panel_like") and same_page:
+                        best_region, best_score = best
+                        matched_assets = list(best_region.get("media_blocks", []))
+                        used_region_ids.add(best_region.get("region_id", ""))
+                        used_asset_ids.update(_asset_key(a) for a in matched_assets)
+                        region_match = {
+                            "page": best_region.get("page", legend_page),
+                            "media_blocks": matched_assets,
+                            "cluster_bbox": best_region.get("cluster_bbox", [0, 0, 0, 0]),
+                            "match_score": best_score,
+                        }
+                    else:
+                        ambiguous_figures.append({
+                            "legend_block_id": legend.get("block_id", ""),
+                            "page": legend_page,
+                            "caption_score": caption_score,
+                            "candidates": [
+                                {"region_id": a.get("region_id", ""), "match_score": s}
+                                for a, s in close
+                            ],
+                        })
+                        ambiguous = True
+                        matched_assets = []
             else:
-                best_idx, best_asset, best_score = candidates[0]
-                matched_assets = [best_asset]
-                used_asset_indices.add(best_idx)
-                region_match = {"media_blocks": [best_asset], "match_score": best_score}
+                best_region, best_score = candidates[0]
+                if str(best_score.get("decision", "")).startswith("matched"):
+                    matched_assets = list(best_region.get("media_blocks", []))
+                    used_region_ids.add(best_region.get("region_id", ""))
+                    used_asset_ids.update(_asset_key(a) for a in matched_assets)
+                    region_match = {
+                        "page": best_region.get("page", legend_page),
+                        "media_blocks": matched_assets,
+                        "cluster_bbox": best_region.get("cluster_bbox", [0, 0, 0, 0]),
+                        "match_score": best_score,
+                    }
+                else:
+                    matched_assets = []
 
         # Fallback: if no match found but legends == assets on the same page,
         # assign sequentially by vertical position
-        if not matched_assets and fig_num is not None:
-            page_assets = [
-                (ai, a) for ai, a in enumerate(assets)
-                if ai not in used_asset_indices and a.get("page", 0) == legend_page
+        if not matched_assets and fig_num is not None and not had_ambiguous_region_candidate:
+            page_regions = [
+                r for r in candidate_regions
+                if r.get("region_id", "") not in used_region_ids and r.get("page", 0) == legend_page
             ]
             page_legends = [
                 l for l in ordered_legends
                 if l is not legend and _extract_figure_number(l.get("text", "")) is not None
                 and l.get("page", 0) == legend_page
             ]
-            if page_assets and len(page_assets) >= len(page_legends) + 1:
-                page_assets.sort(key=lambda item: (item[1].get("bbox",[0,0,0,0])[1] if len(item[1].get("bbox",[]))>=4 else 0))
-                # Count how many matched legends already consumed assets on this page
-                consumed_on_page = sum(1 for i in used_asset_indices if assets[i].get("page",0) == legend_page)
-                asset_idx = min(consumed_on_page, len(page_assets) - 1)
-                best_idx, best_asset = page_assets[asset_idx]
-                matched_assets = [best_asset]
-                used_asset_indices.add(best_idx)
-                region_match = {"media_blocks": [best_asset], "match_score": {"score": 0.5, "decision": "matched_fallback", "evidence": ["sequential_fallback"]}}
+            if page_regions and len(page_regions) >= len(page_legends) + 1:
+                page_regions.sort(key=lambda r: (r.get("cluster_bbox",[0,0,0,0])[1] if len(r.get("cluster_bbox",[]))>=4 else 0))
+                consumed_on_page = sum(1 for rid in used_region_ids if any(r.get("page",0) == legend_page and r.get("region_id","") == rid for r in candidate_regions))
+                region_idx = min(consumed_on_page, len(page_regions) - 1)
+                best_region = page_regions[region_idx]
+                matched_assets = list(best_region.get("media_blocks", []))
+                used_region_ids.add(best_region.get("region_id", ""))
+                used_asset_ids.update(_asset_key(a) for a in matched_assets)
+                region_match = {
+                    "page": best_region.get("page", legend_page),
+                    "media_blocks": matched_assets,
+                    "cluster_bbox": best_region.get("cluster_bbox", [0, 0, 0, 0]),
+                    "match_score": {"score": 0.5, "decision": "matched_fallback", "evidence": ["sequential_fallback"]},
+                }
 
         is_legend_only = len(matched_assets) == 0
+        if is_legend_only and had_ambiguous_region_candidate:
+            ambiguous = True
+            if not any(item.get("legend_block_id", "") == legend.get("block_id", "") for item in ambiguous_figures):
+                ambiguous_figures.append({
+                    "legend_block_id": legend.get("block_id", ""),
+                    "page": legend_page,
+                    "caption_score": caption_score,
+                    "candidates": [
+                        {"region_id": region.get("region_id", ""), "match_score": match_score}
+                        for region, match_score in candidates
+                        if match_score.get("decision") == "ambiguous"
+                    ],
+                })
 
         if caption_score.get("score", 0.0) < 0.4:
             unmatched_legends.append(legend)
@@ -551,13 +718,8 @@ def build_figure_inventory(structured_blocks: list[dict], page_width: float = 12
                 "page": legend_page,
                 "text": legend_text,
                 "figure_number": fig_num,
-                "matched_assets": [
-                    {
-                        "block_id": a.get("block_id", ""),
-                        "bbox": a.get("bbox", [0, 0, 0, 0]),
-                    }
-                    for a in matched_assets
-                ],
+                "asset_page": region_match.get("page", legend_page) if region_match is not None else legend_page,
+                "matched_assets": [{"block_id": a.get("block_id", ""), "bbox": a.get("bbox", [0, 0, 0, 0])} for a in matched_assets],
                 "confidence": match_score["score"],
                 "match_score": match_score,
                 "flags": [] if not is_legend_only else ["legend_only"],
@@ -570,8 +732,45 @@ def build_figure_inventory(structured_blocks: list[dict], page_width: float = 12
         if is_legend_only:
             unmatched_legends.append(legend)
 
-    for i, asset in enumerate(assets):
-        if i not in used_asset_indices:
+    # Post-match expansion: iteratively pull in nearby unused assets on the
+    # same page so chained multi-panel layouts can merge into one figure.
+    for entry in matched_figures:
+        fig_page = entry.get("page", 0)
+        mas = entry.get("matched_assets", [])
+        if not mas or entry.get("cluster_bbox"):
+            continue
+        matched = {m.get("block_id", ""): m for m in mas}
+        changed = True
+        while changed:
+            changed = False
+            current_bboxes = [m.get("bbox", [0, 0, 0, 0]) for m in matched.values() if len(m.get("bbox", [])) >= 4]
+            if not current_bboxes:
+                break
+            fig_x1, fig_y1, fig_x2, fig_y2 = _cluster_bbox(current_bboxes)
+            for a in assets:
+                aid = a.get("block_id", "")
+                if not aid or _asset_key(a) in used_asset_ids or aid in matched or a.get("page", 0) != fig_page:
+                    continue
+                ab = a.get("bbox") or a.get("block_bbox") or [0, 0, 0, 0]
+                if len(ab) < 4:
+                    continue
+                ax1, ay1, ax2, ay2 = ab[0], ab[1], ab[2], ab[3]
+                x_overlap = max(0, min(fig_x2, ax2) - max(fig_x1, ax1))
+                x_span = max(1, max(fig_x2, ax2) - min(fig_x1, ax1))
+                overlap_ratio = x_overlap / x_span
+                y_gap = max(ay1 - fig_y2, fig_y1 - ay2, 0)
+                page_h = a.get("page_height") or 1700
+                if overlap_ratio >= 0.25 and y_gap < page_h * 0.18:
+                    matched[aid] = {"block_id": aid, "bbox": a.get("bbox", [0, 0, 0, 0])}
+                    used_asset_ids.add(_asset_key(a))
+                    changed = True
+        if len(matched) > len(mas):
+            entry["matched_assets"] = list(matched.values())
+            entry["cluster_bbox"] = _cluster_bbox([m.get("bbox", [0, 0, 0, 0]) for m in matched.values()])
+            entry["flags"] = [f for f in entry.get("flags", []) if f != "legend_only"]
+
+    for asset in assets:
+        if _asset_key(asset) not in used_asset_ids:
             unmatched_assets.append(asset)
 
     # Build unresolved clusters: spatial clusters of unmatched assets on
diff --git a/paperforge/worker/ocr_health.py b/paperforge/worker/ocr_health.py
index b4127b0..7a749fc 100644
--- a/paperforge/worker/ocr_health.py
+++ b/paperforge/worker/ocr_health.py
@@ -150,6 +150,16 @@ def build_ocr_health(
     }
     report.update(decision_summary)
 
+    from paperforge.worker.ocr_roles import is_preproof_marker
+
+    preproof_pages = list({
+        b.get("page") for b in structured_blocks
+        if b.get("role") == "frontmatter_noise"
+        and is_preproof_marker(str(b.get("text", "") or b.get("block_content", "") or ""))
+    })
+    report["preproof_marker_detected"] = len(preproof_pages) > 0
+    report["preproof_marker_pages"] = preproof_pages
+
     degraded_reasons = []
     if span.get("coverage_quality", "weak") == "weak":
         degraded_reasons.append(f"weak span coverage ({span.get('coverage_ratio', 0):.0%})")
diff --git a/paperforge/worker/ocr_objects.py b/paperforge/worker/ocr_objects.py
index 58d4cac..0350ef5 100644
--- a/paperforge/worker/ocr_objects.py
+++ b/paperforge/worker/ocr_objects.py
@@ -205,7 +205,8 @@ def extract_and_write_objects(
         fig_id = match.get("figure_id", f"figure_{i + 1:03d}")
         caption_text = match.get("text", "")
         page = match.get("page", 0)
-        page_width, page_height = _page_dims(page)
+        asset_page = match.get("asset_page", page)
+        page_width, page_height = _page_dims(asset_page)
         asset_path_rel = f"assets/figures/{fig_id}.jpg"
         asset_path_abs = figures_asset_dir / f"{fig_id}.jpg"
 
@@ -213,7 +214,7 @@ def extract_and_write_objects(
         cluster_bbox = match.get("cluster_bbox")
         if cluster_bbox and all(v > 0 for v in cluster_bbox):
             was_cropped = _crop_asset_from_pdf(
-                pdf_path, page, cluster_bbox, asset_path_abs,
+                pdf_path, asset_page, cluster_bbox, asset_path_abs,
                 page_width=page_width, page_height=page_height,
                 page_cache_dir=page_cache_dir,
             )
@@ -222,7 +223,7 @@ def extract_and_write_objects(
                 bbox = asset_info.get("bbox", [0, 0, 0, 0])
                 if pdf_path and bbox and all(v > 0 for v in bbox) and _crop_asset_from_pdf(
                     pdf_path,
-                    page,
+                    asset_page,
                     bbox,
                     asset_path_abs,
                     page_width=page_width,
diff --git a/paperforge/worker/ocr_roles.py b/paperforge/worker/ocr_roles.py
index bcf37e7..edf534d 100644
--- a/paperforge/worker/ocr_roles.py
+++ b/paperforge/worker/ocr_roles.py
@@ -95,7 +95,7 @@ _FRONTIERS_FIGURE_TITLE_PATTERN = re.compile(
 )
 
 _PANEL_LABEL_PATTERN = re.compile(
-    r"^\(?[A-Z]\)?[\.:]?$",
+    r"^\(?[A-Za-z]\)?[\.:]?$",
 )
 
 _ROMAN_SECTION_PATTERN = re.compile(
diff --git a/tests/test_ocr_figures.py b/tests/test_ocr_figures.py
index 9231892..f093e10 100644
--- a/tests/test_ocr_figures.py
+++ b/tests/test_ocr_figures.py
@@ -189,6 +189,159 @@ def test_compute_candidate_figure_regions_caption_before_media() -> None:
     assert len(regions[0]["attached_captions"]) == 0
 
 
+def test_figure_inventory_ignores_lowercase_panel_labels_and_embedded_inner_text() -> None:
+    from paperforge.worker.ocr_figures import build_figure_inventory
+
+    structured_blocks = [
+        {
+            "paper_id": "K001",
+            "page": 10,
+            "block_id": "p10_b1",
+            "role": "figure_caption",
+            "raw_label": "figure_title",
+            "text": "(a)",
+            "bbox": [80, 80, 110, 110],
+            "page_width": 1200,
+            "page_height": 1600,
+        },
+        {
+            "paper_id": "K001",
+            "page": 10,
+            "block_id": "p10_b2",
+            "role": "figure_caption",
+            "raw_label": "figure_title",
+            "text": "0 mg/mL",
+            "bbox": [120, 220, 200, 240],
+            "page_width": 1200,
+            "page_height": 1600,
+        },
+        {
+            "paper_id": "K001",
+            "page": 10,
+            "block_id": "p10_b3",
+            "role": "figure_caption",
+            "raw_label": "figure_title",
+            "text": "Fig. 2. Multi-panel figure with one formal legend.",
+            "bbox": [60, 1300, 1140, 1450],
+            "page_width": 1200,
+            "page_height": 1600,
+        },
+        {
+            "paper_id": "K001",
+            "page": 10,
+            "block_id": "p10_b4",
+            "role": "media_asset",
+            "raw_label": "image",
+            "text": "",
+            "bbox": [80, 120, 300, 420],
+            "page_width": 1200,
+            "page_height": 1600,
+        },
+        {
+            "paper_id": "K001",
+            "page": 10,
+            "block_id": "p10_b5",
+            "role": "media_asset",
+            "raw_label": "image",
+            "text": "",
+            "bbox": [320, 120, 540, 420],
+            "page_width": 1200,
+            "page_height": 1600,
+        },
+        {
+            "paper_id": "K001",
+            "page": 10,
+            "block_id": "p10_b6",
+            "role": "media_asset",
+            "raw_label": "image",
+            "text": "",
+            "bbox": [80, 450, 300, 780],
+            "page_width": 1200,
+            "page_height": 1600,
+        },
+    ]
+
+    inventory = build_figure_inventory(structured_blocks)
+
+    assert inventory["official_figure_count"] == 1
+    assert len(inventory["matched_figures"]) == 1
+    assert inventory["matched_figures"][0]["figure_number"] == 2
+    assert len(inventory["matched_figures"][0]["matched_assets"]) == 3
+    assert not any(leg.get("text") == "(a)" for leg in inventory["figure_legends"])
+    assert not any(leg.get("text") == "0 mg/mL" for leg in inventory["figure_legends"])
+
+
+def test_figure_inventory_matches_adjacent_caption_page_to_merged_panel_region() -> None:
+    from paperforge.worker.ocr_figures import build_figure_inventory
+
+    structured_blocks = [
+        {
+            "paper_id": "K002",
+            "page": 20,
+            "block_id": "p20_b1",
+            "role": "media_asset",
+            "raw_label": "image",
+            "text": "",
+            "bbox": [120, 120, 380, 420],
+            "page_width": 1200,
+            "page_height": 1600,
+        },
+        {
+            "paper_id": "K002",
+            "page": 20,
+            "block_id": "p20_b2",
+            "role": "media_asset",
+            "raw_label": "chart",
+            "text": "",
+            "bbox": [420, 120, 760, 430],
+            "page_width": 1200,
+            "page_height": 1600,
+        },
+        {
+            "paper_id": "K002",
+            "page": 20,
+            "block_id": "p20_b3",
+            "role": "figure_caption",
+            "raw_label": "figure_title",
+            "text": "(a)",
+            "bbox": [110, 90, 140, 115],
+            "page_width": 1200,
+            "page_height": 1600,
+        },
+        {
+            "paper_id": "K002",
+            "page": 20,
+            "block_id": "p20_b4",
+            "role": "figure_caption",
+            "raw_label": "figure_title",
+            "text": "(b)",
+            "bbox": [410, 90, 440, 115],
+            "page_width": 1200,
+            "page_height": 1600,
+        },
+        {
+            "paper_id": "K002",
+            "page": 21,
+            "block_id": "p21_b1",
+            "role": "figure_caption",
+            "raw_label": "figure_title",
+            "text": "Fig. 3. Caption lives on the following page, but should still match the previous multi-panel figure page.",
+            "bbox": [80, 80, 1120, 260],
+            "page_width": 1200,
+            "page_height": 1600,
+        },
+    ]
+
+    inventory = build_figure_inventory(structured_blocks)
+
+    assert inventory["official_figure_count"] == 1
+    assert len(inventory["matched_figures"]) == 1
+    assert inventory["matched_figures"][0]["figure_number"] == 3
+    assert inventory["matched_figures"][0]["page"] == 21
+    assert len(inventory["matched_figures"][0]["matched_assets"]) == 2
+    assert inventory["matched_figures"][0]["match_score"]["decision"] in {"matched", "matched_adjacent_region"}
+
+
 # --- existing tests ---
 
 
diff --git a/tests/test_ocr_metadata.py b/tests/test_ocr_metadata.py
index 34d5744..20dee84 100644
--- a/tests/test_ocr_metadata.py
+++ b/tests/test_ocr_metadata.py
@@ -223,3 +223,50 @@ def test_normalize_author_name_strips_superscripts() -> None:
 
     assert _normalize_author_name("Smith $^{1}") == "Smith"
     assert _normalize_author_name("Ebrahim Esfandiari $^{1}$") == "Ebrahim Esfandiari"
+
+
+def test_initials_match_ami_yoo() -> None:
+    from paperforge.worker.ocr_metadata import _initials_match
+
+    assert _initials_match("A. Yoo", "Ami Yoo") is True
+
+
+def test_initials_match_w_h_marks() -> None:
+    from paperforge.worker.ocr_metadata import _initials_match
+
+    assert _initials_match("W. H. Marks", "William H. Marks") is True
+
+
+def test_initials_match_g_go() -> None:
+    from paperforge.worker.ocr_metadata import _initials_match
+
+    assert _initials_match("G. Go", "Gwangjun Go") is True
+
+
+def test_initials_no_match() -> None:
+    from paperforge.worker.ocr_metadata import _initials_match
+
+    assert _initials_match("A. Yoo", "John Smith") is False
+
+
+def test_get_ocr_author_names() -> None:
+    from paperforge.worker.ocr_metadata import _get_ocr_author_names
+
+    blocks = [
+        {"role": "authors", "text": "Ami Yoo, Gwangjun Go, Kim Tien Nguyen, Kyungmin Lee"},
+        {"role": "body_paragraph", "text": "Some body text"},
+    ]
+    names = _get_ocr_author_names(blocks)
+    assert "Ami Yoo" in names
+    assert "Gwangjun Go" in names
+    assert len(names) >= 3
+
+
+def test_ocr_authors_verified_by_first_author() -> None:
+    from paperforge.worker.ocr_metadata import resolve_metadata
+
+    source_meta = {"first_author": "A. Yoo", "title": "Test paper", "doi": "10.1234/test"}
+    blocks = [{"role": "authors", "text": "Ami Yoo, Gwangjun Go", "page": 1, "bbox": [100, 100, 500, 130]}]
+    result = resolve_metadata(source_meta, {}, structured_blocks=blocks)
+    assert "Ami Yoo" in result.get("authors", {}).get("value", [])
+    assert result.get("authors", {}).get("source") == "ocr_blocks_verified_by_first_author"
```
