#!/usr/bin/env python3
"""Helpers for /LD and /LD-deep literature sessions."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


def _load_vault_config(vault: Path) -> dict:
    """Load vault directory configuration — delegates to shared resolver.

    Preserves the public name for legacy callers.
    """
    from paperforge_lite.config import load_vault_config as _shared_load_vault_config
    return _shared_load_vault_config(vault)


def _paperforge_paths(vault: Path) -> dict[str, Path]:
    """Build PaperForge path inventory for /LD-deep — delegates to shared resolver.

    Returns ocr, records, literature keys matching shared resolver output.
    """
    from paperforge_lite.config import paperforge_paths as _shared_paperforge_paths

    shared = _shared_paperforge_paths(vault)
    return {
        "ocr": shared["ocr"],
        "records": shared["library_records"],
        "literature": shared["literature"],
    }


def _get_ocr_root(vault: Path) -> Path:
    """Get OCR root path dynamically from config."""
    return _paperforge_paths(vault)["ocr"]


STUDY_HEADER = "## 🔍 精读"
FIGURE_SECTION_HEADER = "#### Figure-by-Figure 解析"
TABLE_SECTION_HEADER = "#### Table-by-Table 解析"


@dataclass
class FigureEntry:
    number: str
    image_id: str
    title: str
    image_link: str
    page: int | None
    caption: str
    is_supplementary: bool
    additional_images: list[dict] = field(default_factory=list)


@dataclass
class TableEntry:
    number: str
    image_link: str
    page: int | None


def validate_extraction_completeness(
    figures: list[FigureEntry],
    tables: list[TableEntry],
    fulltext: str,
) -> list[str]:
    """Check if figure/table extraction is complete and flag issues.

    Returns a list of warning messages for the agent.
    """
    warnings: list[str] = []

    # Check for unmapped figures (number="?")
    unmapped_figures = [f for f in figures if f.number == "?"]
    if unmapped_figures:
        warnings.append(
            f"[!WARNING] {len(unmapped_figures)} 个 figure 未从 figure-map 解析到编号，"
            f"已标记为 '?'。Agent 需手动核对并补充真实编号（如 Fig 1, Fig 2...）。"
        )

    # Check for low figure count (Nature/Science papers typically have 4-8 figures)
    main_figures = [f for f in figures if not f.is_supplementary]
    if len(main_figures) < 2:
        warnings.append(
            f"[!WARNING] 仅提取到 {len(main_figures)} 个主图，数量异常偏低。"
            f"请检查 OCR 质量或手动从 PDF 补充缺失的 figure。"
        )

    # Check for tables that might have been missed
    # Look for table captions in fulltext that don't have corresponding images
    table_caption_pattern = re.compile(
        r"(?:Table|Extended Data Table|Supplementary Table)\s+(\d+)",
        re.IGNORECASE,
    )
    caption_numbers = set()
    for match in table_caption_pattern.finditer(fulltext):
        caption_numbers.add(match.group(1))

    extracted_numbers = {t.number for t in tables}
    missing_tables = caption_numbers - extracted_numbers
    if missing_tables:
        warnings.append(
            f"[!WARNING] 检测到 {len(missing_tables)} 个表格引用未匹配到图像："
            f"Table {', '.join(sorted(missing_tables))}。"
            f"Agent 需手动从 PDF 提取这些表格。"
        )

    return warnings


EVIDENCE_GUARDRAIL = (
    "**证据边界**：区分三层信息：`论文结果`、`作者解释`、`我的理解/推断`。"
    "不要把样本内观察直接写成普遍规律，不要把相关性写成因果，不要把未进入最终模型的指标写成已被稳定验证的联合诊断结论。"
)

REQUIRED_SECTIONS = [
    "**一句话总览**",
    "**证据边界**",
    "**Figure 导读**",
    "**主要发现**",
    "**较扎实**",
    "**仍存疑**",
    "**遗留问题**",
]


def extract_figures_from_fulltext(fulltext: str, figure_map: dict | None = None) -> list[FigureEntry]:
    """Extract ALL image blocks from OCR fulltext markdown.

    Priority: use figure_map (from build_figure_map) if available for accurate
    numbering and captions. Fallback to raw OCR image blocks with '?' numbering.

    Returns all images with their page number and image basename.
    The agent reads fulltext to identify which are real figures and their numbers,
    then passes image basenames to ensure-scaffold via --figures.
    """
    figures: list[FigureEntry] = []
    pending_page: int | None = None
    pending_image: str | None = None

    page_pattern = re.compile(r"<!-- page (\d+) -->")
    image_pattern = re.compile(r"!\[\[(.+?)\]\]")

    # Build lookup from figure_map if available
    map_lookup: dict[str, dict] = {}
    if figure_map:
        for entry in figure_map.get("figures", []):
            map_lookup[entry.get("image_id", "")] = entry
        for entry in figure_map.get("supplementary_figures", []):
            map_lookup[entry.get("image_id", "")] = entry

    for raw_line in fulltext.splitlines():
        line = raw_line.strip()

        page_match = page_pattern.match(line)
        if page_match:
            pending_page = int(page_match.group(1))
            pending_image = None
            continue

        image_match = image_pattern.match(line)
        if image_match:
            pending_image = image_match.group(1)
            image_id = Path(pending_image).stem

            # Try figure_map first for accurate metadata
            mapped = map_lookup.get(image_id)
            if mapped:
                figures.append(
                    FigureEntry(
                        number=mapped.get("number", "?"),
                        image_id=image_id,
                        title=mapped.get("caption", "")[:80] + "..." if len(mapped.get("caption", "")) > 80 else mapped.get("caption", "[Figure]"),
                        image_link=pending_image,
                        page=mapped.get("page", pending_page),
                        caption=mapped.get("caption", ""),
                        is_supplementary=mapped.get("type", "") == "supplementary_figure",
                        additional_images=mapped.get("additional_images", []),
                    )
                )
            else:
                figures.append(
                    FigureEntry(
                        number="?",
                        image_id=image_id,
                        title="[OCR图像块]",
                        image_link=pending_image,
                        page=pending_page,
                        caption="",
                        is_supplementary=False,
                    )
                )
            continue

    return figures


def build_figure_plan(
    figures: Iterable[FigureEntry],
    important_supplementary: set[str] | None = None,
) -> list[FigureEntry]:
    """Keep all main figures and only requested supplementary figures."""
    important_supplementary = important_supplementary or set()
    planned: list[FigureEntry] = []
    for figure in figures:
        if not figure.is_supplementary or figure.number in important_supplementary:
            planned.append(figure)
    return planned


def select_entries_by_numbers[T](entries: Iterable[T], numbers: set[str], attr: str = "number") -> list[T]:
    """Select entries by their number field while preserving order."""
    if not numbers:
        return []
    selected: list[T] = []
    for entry in entries:
        if getattr(entry, attr) in numbers:
            selected.append(entry)
    return selected


def extract_tables_from_fulltext(fulltext: str, figure_map: dict | None = None) -> list[TableEntry]:
    """Extract OCR table blocks from fulltext markdown.

    Supports multiple naming conventions:
    - page_XXX_table_YYYY... (raw OCR)
    - extended_data_table_N... (extended data)
    - supplementary_table_N... (supplementary)

    Priority: use figure_map if available for accurate numbering.
    """
    tables: list[TableEntry] = []
    pending_page: int | None = None

    page_pattern = re.compile(r"<!-- page (\d+) -->")
    # Relaxed pattern: match any image path containing "table" in the filename
    table_pattern = re.compile(r"!\[\[(.*table[^\]]*\.\w+)\]\]", re.IGNORECASE)

    # Build lookup from figure_map if available
    map_lookup: dict[str, dict] = {}
    if figure_map:
        for entry in figure_map.get("tables", []):
            map_lookup[entry.get("image_id", "")] = entry
        for entry in figure_map.get("supplementary_tables", []):
            map_lookup[entry.get("image_id", "")] = entry

    for raw_line in fulltext.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        page_match = page_pattern.match(line)
        if page_match:
            pending_page = int(page_match.group(1))
            continue

        table_match = table_pattern.match(line)
        if table_match:
            image_link = table_match.group(1)
            image_id = Path(image_link).stem

            # Try figure_map first
            mapped = map_lookup.get(image_id)
            if mapped:
                tables.append(TableEntry(
                    number=mapped.get("number", str(len(tables) + 1)),
                    image_link=image_link,
                    page=mapped.get("page", pending_page),
                ))
            else:
                # Fallback: cannot determine real table number from filename
                # The number in filename (e.g. 75 in page_024_table_75...) is an OCR internal ID, NOT the table number
                tables.append(TableEntry(number="?", image_link=image_link, page=pending_page))

    return tables


# ---------------------------------------------------------------------------
# Chart Type Detection: per-figure subfigure type scanning
# ---------------------------------------------------------------------------

CHART_TYPE_KEYWORDS: dict[str, list[str]] = {
    "条形图与误差棒": [
        "bar", "histogram", "column", "quantification", "quantitative",
        "relative expression", "mRNA expression", "protein level",
        "BMD", "BV/TV", "Tb.N", "Tb.Sp", "intensity", "score",
        "ratio", "percentage", "proportion", "fold change",
    ],
    "折线图与时间序列": [
        "curve", "time", "kinetics", "release", "cyclic", "stability",
        "degradation", "profile", "over time", "day", "week",
        "duration", "period", "cycle", "repeated",
    ],
    "热图与聚类图": [
        "heatmap", "heat map", "clustering", "cluster", "dendrogram",
        "hierarchical", "correlation matrix", "expression matrix",
    ],
    "火山图与曼哈顿图": [
        "volcano", "volcano plot", "manhattan", "-log10", "log2fc",
        "fold change", "differential", "DEG", "DEM", "upregulated", "downregulated",
    ],
    "免疫荧光定量图": [
        "immunofluorescence", "immunofluorescent", "confocal", "fluorescence",
        "staining", "3D reconstruction", "overlay", "DAPI", " Alexa ",
        "FITC", "TRITC", "Cy3", "Cy5", "SOX9", "COL2A1", "Piezo1",
        "positive cells", "mean intensity", "fluorescent",
    ],
    "组织学半定量图": [
        "H&E", "hematoxylin", "eosin", "Safranin", "Fast Green",
        "Masson", "trichrome", "histology", "histological",
        "tissue section", "slide", "stain", "morphology",
        "O'Driscoll", "ICRS", "Mankin", "OARSI", "Pineda",
    ],
    "桑基图与弦图": [
        "chord", "Sankey", "correlation network", "interaction network",
        "signaling network", "proximity", "correlation of metabolic",
        "Spearman", "Pearson correlation",
    ],
    "雷达图与漏斗图": [
        "radar", "funnel", "spider", "web chart", "polar",
    ],
    "GSEA富集图": [
        "GSEA", "MSEA", "enrichment", "enrichment plot", "enrichment score",
        "NES", "leading edge", "pathway enrichment", "metabolic set",
    ],
    "箱式图与小提琴图": [
        "box", "boxplot", "box plot", "violin", "whisker", "quartile",
        "median", "IQR", "outlier",
    ],
    "散点图与气泡图": [
        "scatter", "bubble", "dot plot", "correlation plot", "regression",
        "linear fit", "R²", "correlation coefficient",
    ],
    "Western Blot条带图": [
        "Western", "blot", "WB", "gel electrophoresis", "SDS-PAGE",
        "band", "molecular weight", "kDa",
    ],
    "显微照片与SEM图": [
        "SEM", "TEM", "microscopy", "micrograph", "morphology",
        "surface", "topography", "nanostructure", "porous",
        "FE-SEM", "scanning electron", "transmission electron",
    ],
    "降维图(PCA-tSNE-UMAP)": [
        "PCA", "t-SNE", "tSNE", "UMAP", "MDS", "dimensionality reduction",
        "principal component", "clustering plot", "embedding",
    ],
    "网络图与通路图": [
        "pathway", "network", "signaling pathway", "KEGG", "Reactome",
        "protein-protein interaction", "PPI", "regulatory network",
    ],
    "蛋白质结构图": [
        "protein structure", "crystallography", "NMR structure", "AlphaFold",
        "3D structure", "homology modeling", "docking",
    ],
    "森林图与Meta分析": [
        "forest plot", "meta-analysis", "meta analysis", "pooled effect",
        "heterogeneity", "I²", "Egger", "funnel plot",
    ],
    "ROC与PR曲线": [
        "ROC", "AUC", "receiver operating", "sensitivity", "specificity",
        "PR curve", "precision-recall", "diagnostic accuracy",
    ],
    "生存曲线": [
        "survival", "Kaplan-Meier", "KM curve", "log-rank", "hazard ratio",
        "HR", "OS", "PFS", "DFS", "mortality",
    ],
}


def detect_chart_types(caption: str) -> list[str]:
    """Detect which chart-reading guides are relevant for a figure caption.

    Returns a deduplicated list of chart type names (Chinese) that match
    keywords found in the caption. Matching is case-insensitive.
    """
    caption_lower = caption.lower()
    matched: list[str] = []
    for chart_type, keywords in CHART_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in caption_lower:
                matched.append(chart_type)
                break  # one match per chart type is enough
    return matched


def build_chart_type_map(figure_map: dict) -> dict:
    """Build a per-figure chart-type reference map from figure-map.json.

    Output format:
    {
      "zotero_key": "...",
      "figures": [
        {
          "number": "1",
          "label": "Figure 1",
          "detected_chart_types": ["雷达图与漏斗图"],
          "recommended_guides": ["chart-reading/雷达图与漏斗图.md"]
        },
        ...
      ],
      "tables": [...]
    }
    """
    result: dict = {
        "zotero_key": figure_map.get("zotero_key", ""),
        "figures": [],
        "tables": [],
    }

    for fig in figure_map.get("figures", []):
        caption = fig.get("caption", "")
        types = detect_chart_types(caption)
        entry = {
            "number": fig.get("number", "?"),
            "label": fig.get("label", ""),
            "caption_preview": caption[:200] + "..." if len(caption) > 200 else caption,
            "detected_chart_types": types,
            "recommended_guides": [f"chart-reading/{t}.md" for t in types],
        }
        result["figures"].append(entry)

    for tbl in figure_map.get("tables", []):
        caption = tbl.get("caption", "")
        types = detect_chart_types(caption)
        entry = {
            "number": tbl.get("number", "?"),
            "label": tbl.get("label", ""),
            "caption_preview": caption[:200] + "..." if len(caption) > 200 else caption,
            "detected_chart_types": types,
            "recommended_guides": [f"chart-reading/{t}.md" for t in types],
        }
        result["tables"].append(entry)

    return result

CAPTION_PATTERNS = {
    "main_figure": re.compile(
        r"^(?:Figure|Fig\.?)\s*(\d+[a-zA-Z]?)(?:\s*[\.:|\-]?\s*)(.*?)$",
        re.IGNORECASE,
    ),
    "supplementary_figure": re.compile(
        r"^(?:Supplementary\s+(?:Figure|Fig\.?)\s*|Extended\s+Data\s+(?:Figure|Fig\.?)\s*|Suppl?\.?\s*(?:Figure|Fig\.?)\s*)(S?\d+[a-zA-Z]?)(?:\s*[\.:|\-]?\s*)(.*?)$",
        re.IGNORECASE,
    ),
    "main_table": re.compile(
        r"^(?:Table)\s*(\d+[a-zA-Z]?)(?:\s*[\.:|\-]?\s*)(.*?)$",
        re.IGNORECASE,
    ),
    "supplementary_table": re.compile(
        r"^(?:Supplementary\s+Table\s*|Suppl?\.?\s*Table\s*|Extended\s+Data\s+Table\s*)(S?\d+[a-zA-Z]?)(?:\s*[\.:|\-]?\s*)(.*?)$",
        re.IGNORECASE,
    ),
}


def build_figure_map(fulltext: str, zotero_key: str = "") -> dict:
    """Build a caption-driven inventory of figures and tables.

    Scans fulltext.md line-by-line, detects formal captions, and pairs each
    caption with the nearest image block within a window of adjacent pages.
    """
    lines = fulltext.splitlines()
    page_pattern = re.compile(r"<!-- page (\d+) -->")
    image_pattern = re.compile(r"!\[\[(.+?)\]\]")

    # First pass: collect all images with their page and line index
    all_images: list[dict] = []
    current_page: int | None = None
    
    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line:
            continue
        
        page_match = page_pattern.match(line)
        if page_match:
            current_page = int(page_match.group(1))
            continue
        
        image_match = image_pattern.match(line)
        if image_match:
            all_images.append({
                "link": image_match.group(1),
                "id": Path(image_match.group(1)).stem,
                "line_idx": idx,
                "page": current_page,
            })

    # Second pass: match captions to nearest images
    entries: list[dict] = []
    current_page = None
    
    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line:
            continue

        page_match = page_pattern.match(line)
        if page_match:
            current_page = int(page_match.group(1))
            continue

        # Try each caption pattern
        for entry_type, pattern in CAPTION_PATTERNS.items():
            m = pattern.match(line)
            if not m:
                continue
            number = m.group(1)
            caption_text = m.group(2).strip() if len(m.groups()) > 1 else ""

            # Find nearest image within window of adjacent pages (current ± 2 pages)
            best_image = None
            min_distance = float('inf')
            
            for img in all_images:
                # Check if image is within 2 pages of current page
                if current_page is not None and img["page"] is not None:
                    page_diff = abs(img["page"] - current_page)
                    if page_diff <= 2:
                        distance = abs(img["line_idx"] - idx)
                        if distance < min_distance:
                            min_distance = distance
                            best_image = img

            # Find additional images on the same page near the best image
            additional_images = []
            if best_image:
                for img in all_images:
                    if img is best_image:
                        continue
                    if img["page"] == best_image["page"]:
                        # Check if this image is adjacent to best_image (within reasonable line distance)
                        line_diff = abs(img["line_idx"] - best_image["line_idx"])
                        if line_diff <= 5:  # Within 5 lines
                            additional_images.append({"id": img["id"], "link": img["link"]})

            entries.append({
                "number": number,
                "label": line.split(".")[0] if "." in line else line.split("|")[0].strip(),
                "page": current_page,
                "type": entry_type,
                "caption": caption_text,
                "image_link": best_image["link"] if best_image else None,
                "image_id": best_image["id"] if best_image else None,
                "additional_images": additional_images,
            })
            break  # one caption per line

    # Deduplicate by (type, number) keeping first
    seen: set[tuple[str, str]] = set()
    deduped: list[dict] = []
    for e in entries:
        key = (e["type"], e["number"])
        if key not in seen:
            seen.add(key)
            deduped.append(e)

    return {
        "zotero_key": zotero_key,
        "generated_at": "",
        "figures": [e for e in deduped if e["type"] == "main_figure"],
        "tables": [e for e in deduped if e["type"] == "main_table"],
        "supplementary_figures": [e for e in deduped if e["type"] == "supplementary_figure"],
        "supplementary_tables": [e for e in deduped if e["type"] == "supplementary_table"],
    }


def find_note_by_zotero_key(workspace_root: Path, zotero_key: str) -> Path | None:
    """Resolve the formal literature note from the configured literature directory."""
    literature_root = _paperforge_paths(workspace_root)["literature"]
    if not literature_root.exists():
        return None

    frontmatter_pattern = re.compile(rf'^\s*zotero_key:\s*"?{re.escape(zotero_key)}"?\s*$', re.MULTILINE)
    for note_path in literature_root.rglob("*.md"):
        try:
            text = note_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = note_path.read_text(encoding="utf-8", errors="ignore")
        if frontmatter_pattern.search(text):
            return note_path
    return None


def render_study_scaffold(figures: Iterable[FigureEntry], tables: Iterable[TableEntry] | None = None) -> str:
    """Render the Keshav three-pass deep-reading scaffold."""
    figure_list = list(figures)
    table_list = list(tables or [])

    # Build figure blocks using the standard renderer for consistency
    figure_blocks = [render_figure_block(fig) for fig in figure_list]
    figure_section = "\n\n".join(figure_blocks) if figure_blocks else "##### Figure 待补充\n\n- 暂未从 OCR 中解析到可用主图。"

    # Build table blocks using the standard renderer for consistency
    table_blocks = [render_table_block(table) for table in table_list]
    table_section = "\n\n".join(table_blocks) if table_blocks else "- 暂未从 OCR 中解析到需单独展开的表格。"

    # Build completeness check prompt
    figure_count = len(figure_list)
    table_count = len(table_list)
    completeness_prompt = (
        f"> [!warning] 图表完整性自查\n"
        f"> 以下内容由脚本自动提取，请人工核对是否完整：\n"
        f"> - **Figures**：提取到 {figure_count} 个图像块（含主图及补充材料图）\n"
        f"> - **Tables**：提取到 {table_count} 个表格块\n"
        f"> - **核对方法**：对照论文原文，检查是否所有 Figure / Table / Extended Data Figure / Supplementary Table 均已包含\n"
        f"> - **如有遗漏**：请在下方直接补充对应的 figure/table 解析块，格式与现有块保持一致"
    )

    return (
        f"{STUDY_HEADER}\n\n"
        f"{completeness_prompt}\n\n"
        f"{EVIDENCE_GUARDRAIL}\n\n"
        "### Pass 1: 概览\n\n"
        "**一句话总览**\n"
        "（待补充）\n\n"
        "**5 Cs 快速评估**\n"
        "- **Category**（类型）：\n"
        "- **Context**（上下文）：\n"
        "- **Correctness**（合理性初判）：\n"
        "- **Contributions**（贡献）：\n"
        "- **Clarity**（清晰度）：\n\n"
        "**Figure 导读**\n"
        "- 关键主图：\n"
        "- 证据转折点：\n"
        "- 需要重点展开的 supplementary：\n"
        "- 关键表格：\n\n"
        "### Pass 2: 精读还原\n\n"
        f"{FIGURE_SECTION_HEADER}\n\n"
        f"{figure_section}\n\n"
        f"{TABLE_SECTION_HEADER}\n\n"
        f"{table_section}\n\n"
        "#### 关键方法补课\n"
        "- 方法 1：\n"
        "- 方法 2：\n\n"
        "#### 主要发现与新意\n"
        "**主要发现**\n"
        "- 发现 1：\n"
        "- 发现 2：\n\n"
        "### Pass 3: 深度理解\n\n"
        "#### 假设挑战与隐藏缺陷\n"
        "- 隐含假设：\n"
        "- 如果放宽某个假设，结论还成立吗？\n"
        "- 缺少哪些关键引用？\n"
        "- 实验/分析技术的潜在问题：\n\n"
        "#### 哪些结论扎实，哪些仍存疑\n"
        "**较扎实**\n"
        "- \n\n"
        "**仍存疑**\n"
        "- \n\n"
        "#### Discussion 与 Conclusion 怎么读\n"
        "- 作者真正完成了什么：\n"
        "- 哪些地方有拔高：\n"
        "- 哪些地方是推测：\n\n"
        "#### 对我的启发\n"
        "- 研究设计上：\n"
        "- figure 组织上：\n"
        "- 方法组合上：\n"
        "- 未来工作想法：\n\n"
        "#### 遗留问题\n"
        "**遗留问题**\n"
        "- \n"
    )


def render_figure_block(figure: FigureEntry) -> str:
    page_suffix = f"（第 {figure.page} 页）" if figure.page else ""
    lines = [
        f"> [!note]- Figure {figure.number}：{figure.title}",
        f"> ![[{figure.image_link}]]",
    ]
    # Add additional images for multi-image figures
    for add_img in figure.additional_images:
        lines.append(f"> ![[{add_img['link']}]]")
    lines.extend([
        ">",
        "> **图像定位与核心问题**",
        f"> - 页码：{page_suffix or '待补充'}",
        "> - 这张图要回答什么：",
        "> - （待补充）",
        ">",
        "> **方法与结果**",
        "> - 方法：",
        "> - 结果：",
        ">",
        "> **作者解释**",
        "> - （待补充）",
        ">",
        "> **我的理解**",
        "> - （待补充）",
        ">",
        "> **在全文中的作用**",
        "> - （待补充）",
        ">",
        "> **疑点 / 局限**",
        "> - （待补充）",
    ])
    return "\n".join(lines) + "\n\n"


def render_table_block(table: TableEntry) -> str:
    page_suffix = f"第 {table.page} 页" if table.page else "待补充"
    lines = [
        f"> [!note]- Table {table.number}",
        f"> ![[{table.image_link}]]",
        ">",
        f"> - 图像定位：{page_suffix}",
        "> - 这张表在回答什么问题：",
        "> - 关键字段 / 分组：",
        "> - 主要结果：",
        "> - 我的理解：",
        "> - 在全文中的作用：",
        "> - 疑点 / 局限：",
    ]
    return "\n".join(lines) + "\n\n"


def validate_selected_blocks(note_text: str, figures: Iterable[FigureEntry], tables: Iterable[TableEntry] | None = None) -> list[str]:
    """Return missing selected figure/table embeds that must be repaired before generation."""
    missing: list[str] = []
    for figure in figures:
        # Use prefix matching for heading to accommodate custom titles
        heading_prefix = f"> [!note]- Figure {figure.number}："
        embed = f"![[{figure.image_link}]]"
        # Check if any line starts with the heading prefix and embed exists
        has_heading = any(line.strip().startswith(heading_prefix) for line in note_text.splitlines())
        if not has_heading or embed not in note_text:
            missing.append(f"Figure {figure.number}")

    for table in tables or []:
        heading_prefix = f"> [!note]- Table {table.number}"
        embed = f"![[{table.image_link}]]"
        has_heading = any(line.strip().startswith(heading_prefix) for line in note_text.splitlines())
        if not has_heading or embed not in note_text:
            missing.append(f"Table {table.number}")

    return missing


def validate_callout_structure(note_text: str, figures: Iterable[FigureEntry]) -> list[str]:
    """Check that the note keeps the required small set of section markers."""
    missing: list[str] = []
    for marker in REQUIRED_SECTIONS:
        if marker not in note_text:
            missing.append(marker)

    for figure in figures:
        figure_heading_prefix = f"> [!note]- Figure {figure.number}："
        # Find the line that starts with this prefix
        figure_idx = -1
        for i, line in enumerate(note_text.splitlines()):
            if line.strip().startswith(figure_heading_prefix):
                figure_idx = note_text.find(line)
                break
        if figure_idx != -1:
            # Find the next callout or heading after this figure block
            figure_block = note_text[figure_idx:]
            next_callout = figure_block.find("\n> [!note]-", 1)
            next_heading = figure_block.find("\n##### ", 1)
            next_section = figure_block.find("\n#### ", 1)
            end_positions = [p for p in [next_callout, next_heading, next_section] if p != -1]
            if end_positions:
                figure_block = figure_block[:min(end_positions)]
            required_local = [
                "**作者解释**",
                "**我的理解**",
                "**疑点 / 局限**",
            ]
            for marker in required_local:
                if marker not in figure_block:
                    missing.append(f"{figure_heading_prefix}::{marker}")

    return missing


def validate_callout_spacing(note_text: str) -> list[str]:
    """Check that consecutive callout blocks are separated by blank lines.

    In Obsidian, a callout block starts with `> [!type]` and continues as long
    as subsequent lines start with `>`. An empty line or a non-`>` line ends
    the block. If another `> [!type]` appears before the block is properly
    ended, Obsidian merges them into a single callout instead of rendering
    them as separate blocks.
    """
    issues: list[str] = []
    lines = note_text.splitlines()
    in_callout_block = False

    for idx, line in enumerate(lines):
        stripped = line.strip()
        is_callout_start = stripped.startswith("> [!")
        is_callout_continuation = stripped.startswith("> ") or stripped == ">"

        if is_callout_start:
            if in_callout_block:
                issues.append(
                    f"Line {idx + 1}: Callout '{stripped[:60]}...' appears inside "
                    f"an ongoing callout block without a blank line separator."
                )
            in_callout_block = True
        elif not is_callout_continuation and stripped:
            # Non-blank, non-callout line ends any callout block
            in_callout_block = False
        elif not stripped:
            # Blank line ends the callout block
            in_callout_block = False

    return issues


def validate_scaffold_residue(note_text: str) -> list[str]:
    """Check for leftover scaffold template text that should have been removed.

    After the subagent fills the note, certain auto-generated instructional
    callouts (e.g. "图表完整性自查") are no longer needed and should be
    deleted. Their presence indicates incomplete cleanup.
    """
    issues: list[str] = []
    residue_markers = [
        "图表完整性自查",
        "以下内容由脚本自动提取",
        "如有遗漏：请在下方直接补充",
    ]
    lines = note_text.splitlines()
    for idx, line in enumerate(lines):
        for marker in residue_markers:
            if marker in line:
                issues.append(
                    f"Line {idx + 1}: Scaffold residue detected: '{marker}'. "
                    "Remove this auto-generated instruction after verification."
                )
                break  # One issue per line is enough
    return issues


def validate_redundant_headings(note_text: str) -> list[str]:
    """Check for redundant heading + bold text pairs like:

    #### 遗留问题
    **遗留问题**

    The bold line duplicates the heading and should be removed.
    """
    issues: list[str] = []
    lines = note_text.splitlines()
    for idx in range(len(lines) - 1):
        current = lines[idx].strip()
        next_line = lines[idx + 1].strip()
        # Match #### Heading followed by **Heading**
        if current.startswith("#### ") and next_line.startswith("**") and next_line.endswith("**"):
            heading_text = current[5:].strip()
            bold_text = next_line[2:-2].strip()
            if heading_text == bold_text:
                issues.append(
                    f"Line {idx + 2}: Redundant bold text '{next_line}' "
                    f"duplicates heading '{current}'. Remove the bold line."
                )
    return issues


def validate_deep_note(
    note_text: str,
    figures: Iterable[FigureEntry],
    tables: Iterable[TableEntry] | None = None,
) -> list[str]:
    """Run the full structural validation for a generated deep-reading note."""
    issues: list[str] = []

    if STUDY_HEADER not in note_text:
        issues.append(STUDY_HEADER)
    if FIGURE_SECTION_HEADER not in note_text:
        issues.append(FIGURE_SECTION_HEADER)
    if TABLE_SECTION_HEADER not in note_text:
        issues.append(TABLE_SECTION_HEADER)

    issues.extend(validate_selected_blocks(note_text, figures, tables))
    issues.extend(validate_callout_structure(note_text, figures))
    issues.extend(validate_callout_spacing(note_text))

    issues.extend(validate_scaffold_residue(note_text))
    issues.extend(validate_redundant_headings(note_text))

    required_headings = [
        "### Pass 1: 概览",
        "### Pass 2: 精读还原",
        "### Pass 3: 深度理解",
        "#### Figure-by-Figure 解析",
        "#### Table-by-Table 解析",
        "#### 关键方法补课",
        "#### 主要发现与新意",
        "#### 假设挑战与隐藏缺陷",
        "#### 哪些结论扎实，哪些仍存疑",
        "#### Discussion 与 Conclusion 怎么读",
        "#### 对我的启发",
        "#### 遗留问题",
    ]
    for heading in required_headings:
        if heading not in note_text:
            issues.append(heading)

    return issues


def _ensure_section_with_blocks(note_text: str, header: str, blocks: list[str]) -> str:
    if not blocks:
        return note_text

    updated = note_text
    if header not in updated:
        updated = updated.rstrip() + f"\n\n{header}\n\n"

    for block in blocks:
        heading = block.splitlines()[0]
        if heading not in updated:
            insertion_point = updated.find(header)
            if insertion_point == -1:
                updated = updated.rstrip() + f"\n\n{header}\n\n{block}\n"
            else:
                header_end = updated.find("\n", insertion_point)
                if header_end == -1:
                    header_end = len(updated)
                insert_at = header_end + 1
                updated = updated[:insert_at] + "\n" + block + "\n\n" + updated[insert_at:]

    return updated


def ensure_study_section(note_text: str, figures: Iterable[FigureEntry], tables: Iterable[TableEntry] | None = None) -> str:
    """Append the study scaffold if it does not yet exist."""
    figure_list = list(figures)
    table_list = list(tables or [])
    if STUDY_HEADER in note_text:
        updated = _ensure_section_with_blocks(note_text, FIGURE_SECTION_HEADER, [render_figure_block(fig) for fig in figure_list])
        updated = _ensure_section_with_blocks(updated, TABLE_SECTION_HEADER, [render_table_block(table) for table in table_list])
        return updated

    stripped = note_text.rstrip()
    scaffold = render_study_scaffold(figure_list, table_list)
    if stripped:
        return f"{stripped}\n\n{scaffold}\n"
    return f"{scaffold}\n"


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def prepare_deep_reading(vault: Path, zotero_key: str, force: bool = False) -> dict:
    """Automate all mechanical pre-reading steps for /LD-deep.

    Returns a dict with:
      - status: "ok" | "error"
      - message: human-readable summary
      - formal_note: path to the formal literature note
      - fulltext_md: path to OCR fulltext
      - figure_map: path to figure-map.json
      - chart_type_map: path to chart-type-map.json
      - figures: list of extracted figures
      - tables: list of extracted tables
      - chart_recommendations: list of recommended chart-reading guides
    """
    result: dict = {
        "status": "error",
        "message": "",
        "zotero_key": zotero_key,
        "formal_note": None,
        "fulltext_md": None,
        "figure_map": None,
        "chart_type_map": None,
        "figures": [],
        "tables": [],
        "chart_recommendations": [],
    }

    paths = _paperforge_paths(vault)
    records_root = paths["records"]
    literature_root = paths["literature"]
    ocr_root = paths["ocr"]

    # 1. Find library-record
    record_path: Path | None = None
    domain: str | None = None
    if records_root.exists():
        for domain_dir in records_root.iterdir():
            if not domain_dir.is_dir():
                continue
            candidate = domain_dir / f"{zotero_key}.md"
            if candidate.exists():
                record_path = candidate
                domain = domain_dir.name
                break

    if record_path is None:
        # Fallback: search by zotero_key in frontmatter
        for domain_dir in records_root.iterdir():
            if not domain_dir.is_dir():
                continue
            for candidate in domain_dir.glob("*.md"):
                text = candidate.read_text(encoding="utf-8")
                if re.search(rf'^zotero_key:\s*"?{re.escape(zotero_key)}"?', text, re.MULTILINE):
                    record_path = candidate
                    domain = domain_dir.name
                    break
            if record_path:
                break

    if record_path is None:
        result["message"] = f"[ERROR] Library record not found for zotero_key={zotero_key}"
        return result

    record_text = record_path.read_text(encoding="utf-8")

    # 2. Check analyze flag
    analyze_match = re.search(r'^analyze:\s*(true|false)$', record_text, re.MULTILINE)
    if not analyze_match or analyze_match.group(1) != "true":
        result["message"] = f"[ERROR] analyze != true in {record_path}. Set analyze: true first."
        return result

    # 3. Check deep_reading_status
    status_match = re.search(r'^deep_reading_status:\s*"?(.*?)"?$', record_text, re.MULTILINE)
    dr_status = status_match.group(1).strip() if status_match else "pending"
    if dr_status == "done" and not force:
        result["message"] = f"[WARN] deep_reading_status already 'done'. Use --force to re-run."
        return result

    # 4. Check OCR / fulltext availability
    ocr_dir = ocr_root / zotero_key
    fulltext_md = ocr_dir / "fulltext.md"
    meta_path = ocr_dir / "meta.json"

    if not fulltext_md.exists():
        result["message"] = f"[ERROR] OCR fulltext not found: {fulltext_md}. Run OCR first."
        return result

    ocr_status = "pending"
    if meta_path.exists():
        meta = _read_json(meta_path)
        ocr_status = str(meta.get("ocr_status", "pending")).strip().lower()

    if ocr_status != "done":
        result["message"] = f"[ERROR] OCR status='{ocr_status}', not 'done'. Wait for OCR or check meta.json."
        return result

    result["fulltext_md"] = str(fulltext_md)

    # 5. Find formal note
    formal_note: Path | None = None
    if literature_root.exists() and domain:
        domain_dir = literature_root / domain
        if domain_dir.exists():
            # Try exact match first
            for candidate in domain_dir.glob("*.md"):
                if candidate.name.startswith(f"{zotero_key} ") or candidate.name.startswith(f"{zotero_key} -"):
                    formal_note = candidate
                    break
            # Fallback: search by frontmatter zotero_key
            if formal_note is None:
                for candidate in domain_dir.glob("*.md"):
                    text = candidate.read_text(encoding="utf-8")
                    if re.search(rf'^zotero_key:\s*"?{re.escape(zotero_key)}"?', text, re.MULTILINE):
                        formal_note = candidate
                        break

    if formal_note is None:
        # Try global search
        for candidate in literature_root.rglob("*.md"):
            text = candidate.read_text(encoding="utf-8")
            if re.search(rf'^zotero_key:\s*"?{re.escape(zotero_key)}"?', text, re.MULTILINE):
                formal_note = candidate
                break

    if formal_note is None:
        result["message"] = f"[ERROR] Formal note not found in {literature_root}. Run index-refresh first."
        return result

    result["formal_note"] = str(formal_note)

    # 6. Run figure-map
    figure_map_path = ocr_dir / "figure-map.json"
    fulltext_text = fulltext_md.read_text(encoding="utf-8")
    figure_map = build_figure_map(fulltext_text, zotero_key=zotero_key)
    figure_map["generated_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    figure_map_path.parent.mkdir(parents=True, exist_ok=True)
    figure_map_path.write_text(json.dumps(figure_map, ensure_ascii=False, indent=2), encoding="utf-8")
    result["figure_map"] = str(figure_map_path)

    # 7. Run chart-type-scan
    chart_type_map_path = ocr_dir / "chart-type-map.json"
    chart_type_result = build_chart_type_map(figure_map)
    chart_type_map_path.write_text(json.dumps(chart_type_result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["chart_type_map"] = str(chart_type_map_path)

    # Collect recommendations
    all_guides: set[str] = set()
    for fig in chart_type_result.get("figures", []):
        for guide in fig.get("recommended_guides", []):
            all_guides.add(guide)
    for tbl in chart_type_result.get("tables", []):
        for guide in tbl.get("recommended_guides", []):
            all_guides.add(guide)
    result["chart_recommendations"] = sorted(all_guides)

    # 8. Extract figures/tables and run ensure-scaffold
    figure_candidates = extract_figures_from_fulltext(fulltext_text, figure_map)
    table_candidates = extract_tables_from_fulltext(fulltext_text, figure_map)
    planned_figures = build_figure_plan(figure_candidates)
    planned_tables = table_candidates  # Include all tables by default

    note_text = formal_note.read_text(encoding="utf-8")
    updated = ensure_study_section(note_text, planned_figures, planned_tables)
    formal_note.write_text(updated, encoding="utf-8")

    result["figures"] = [
        {"number": f.number, "image_id": f.image_id, "page": f.page, "title": f.title}
        for f in planned_figures
    ]
    result["tables"] = [
        {"number": t.number, "page": t.page, "image_link": t.image_link}
        for t in planned_tables
    ]

    result["status"] = "ok"
    result["message"] = (
        f"[OK] Prepared {zotero_key}\n"
        f"  Formal note: {formal_note}\n"
        f"  Fulltext: {fulltext_md}\n"
        f"  Figures: {len(planned_figures)} | Tables: {len(planned_tables)}\n"
        f"  Chart guides: {len(all_guides)} recommended"
    )
    return result


def scan_deep_reading_queue(vault: Path) -> list[dict]:
    """Scan library-records for analyze=true + deep_reading_status!=done entries.

    Returns a list of dicts with keys:
      - zotero_key, title, domain, analyze, deep_reading_status, ocr_status
    """
    paths = _paperforge_paths(vault)
    records_root = paths["records"]
    ocr_root = paths["ocr"]
    queue: list[dict] = []
    if not records_root.exists():
        return queue

    for domain_dir in records_root.iterdir():
        if not domain_dir.is_dir():
            continue
        domain = domain_dir.name
        for record_path in domain_dir.glob("*.md"):
            text = record_path.read_text(encoding="utf-8")

            # Extract frontmatter fields
            zotero_key_match = re.search(r'^zotero_key:\s*(.+)$', text, re.MULTILINE)
            analyze_match = re.search(r'^analyze:\s*(true|false)$', text, re.MULTILINE)
            status_match = re.search(r'^deep_reading_status:\s*"?(.*?)"?$', text, re.MULTILINE)
            title_match = re.search(r'^title:\s*"?(.+?)"?$', text, re.MULTILINE)

            zotero_key = zotero_key_match.group(1).strip().strip('"').strip("'") if zotero_key_match else record_path.stem
            is_analyze = analyze_match is not None and analyze_match.group(1) == "true"
            dr_status = status_match.group(1).strip() if status_match else "pending"
            title = title_match.group(1).strip().strip('"') if title_match else ""

            if not is_analyze or dr_status == "done":
                continue

            # Check OCR status
            meta_path = ocr_root / zotero_key / "meta.json"
            ocr_status = "pending"
            if meta_path.exists():
                meta = _read_json(meta_path)
                ocr_status = str(meta.get("ocr_status", "pending")).strip().lower()

            queue.append({
                "zotero_key": zotero_key,
                "domain": domain,
                "title": title,
                "deep_reading_status": dr_status,
                "ocr_status": ocr_status,
            })

    # Sort: OCR done first, then by domain, then by key
    queue.sort(key=lambda row: (
        0 if row["ocr_status"] == "done" else 1,
        row["domain"],
        row["zotero_key"],
    ))
    return queue


import sys

# Fix Windows console encoding for Unicode output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        # Python < 3.7 fallback
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)


def main() -> int:
    parser = argparse.ArgumentParser(description="Helpers for /LD-deep note scaffolding")
    subparsers = parser.add_subparsers(dest="command", required=True)

    figure_parser = subparsers.add_parser("figure-index", help="Extract figures from fulltext markdown")
    figure_parser.add_argument("fulltext", type=Path)

    scaffold_parser = subparsers.add_parser("ensure-scaffold", help="Append a deep-reading scaffold to a note")
    scaffold_parser.add_argument("note", type=Path)
    scaffold_parser.add_argument("--fulltext", type=Path, help="Optional fulltext markdown used to build figure headings")
    scaffold_parser.add_argument("--figures", help="Comma-separated selected figure numbers to insert")
    scaffold_parser.add_argument("--tables", help="Comma-separated selected table numbers to insert")

    validate_parser = subparsers.add_parser("validate-selected", help="Validate selected figure/table embeds are present in the note")
    validate_parser.add_argument("note", type=Path)
    validate_parser.add_argument("--fulltext", type=Path, required=True, help="OCR fulltext markdown used to resolve figure/table embeds")
    validate_parser.add_argument("--figures", help="Comma-separated selected figure numbers to validate")
    validate_parser.add_argument("--tables", help="Comma-separated selected table numbers to validate")

    full_validate_parser = subparsers.add_parser("validate-note", help="Run the full structural validation for a deep-reading note")
    full_validate_parser.add_argument("note", type=Path)
    full_validate_parser.add_argument("--fulltext", type=Path, required=True, help="OCR fulltext markdown used to resolve figure/table embeds")
    full_validate_parser.add_argument("--figures", help="Comma-separated selected figure numbers to validate")
    full_validate_parser.add_argument("--tables", help="Comma-separated selected table numbers to validate")

    queue_parser = subparsers.add_parser("queue", help="List papers awaiting deep reading from library records")
    queue_parser.add_argument("--vault", type=Path, required=True, help="Path to the vault root")
    queue_parser.add_argument("--format", choices=["json", "table"], default="json", help="Output format")

    map_parser = subparsers.add_parser("figure-map", help="Build caption-driven figure/table map from OCR fulltext")
    map_parser.add_argument("fulltext", type=Path, help="OCR fulltext markdown path")
    map_parser.add_argument("--key", default="", help="Zotero key for output metadata")
    map_parser.add_argument("--out", type=Path, help="Optional output JSON path (default: stdout)")

    chart_type_parser = subparsers.add_parser("chart-type-scan", help="Scan figure captions for chart types and recommend chart-reading guides")
    chart_type_parser.add_argument("figure_map", type=Path, help="Path to figure-map.json generated by figure-map command")
    chart_type_parser.add_argument("--out", type=Path, help="Optional output JSON path (default: stdout)")

    prepare_parser = subparsers.add_parser("prepare", help="One-click prepare all mechanical steps for deep reading")
    prepare_parser.add_argument("zotero_key", help="Zotero citation key")
    prepare_parser.add_argument("--vault", type=Path, required=True, help="Path to vault root")
    prepare_parser.add_argument("--format", choices=["json", "text"], default="text", help="Output format")
    prepare_parser.add_argument("--force", action="store_true", help="Force re-run even if deep_reading_status is done")

    args = parser.parse_args()

    if args.command == "prepare":
        result = prepare_deep_reading(args.vault, args.zotero_key, force=args.force)
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result.get("message", "Unknown result"))
        return 0 if result["status"] == "ok" else 1

    if args.command == "figure-index":
        fulltext = args.fulltext.read_text(encoding="utf-8")
        for figure in extract_figures_from_fulltext(fulltext):
            print(f"Figure {figure.number}\tid={figure.image_id}\tpage={figure.page}\timage={figure.image_link}\ttitle={figure.title}")
        return 0

    if args.command == "ensure-scaffold":
        note_text = args.note.read_text(encoding="utf-8")
        figures: list[FigureEntry] = []
        tables: list[TableEntry] = []
        if args.fulltext:
            fulltext = args.fulltext.read_text(encoding="utf-8")
            # Auto-load figure-map.json from same directory as fulltext if available
            figure_map = None
            figure_map_path = args.fulltext.parent / "figure-map.json"
            if figure_map_path.exists():
                try:
                    figure_map = json.loads(figure_map_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
            figure_candidates = extract_figures_from_fulltext(fulltext, figure_map)
            table_candidates = extract_tables_from_fulltext(fulltext, figure_map)
            selected_figures = {part.strip() for part in (args.figures or "").split(",") if part.strip()}
            selected_tables = {part.strip() for part in (args.tables or "").split(",") if part.strip()}
            figures = (
                select_entries_by_numbers(figure_candidates, selected_figures, attr="image_id")
                if selected_figures
                else build_figure_plan(figure_candidates)
            )
            tables = select_entries_by_numbers(table_candidates, selected_tables) if selected_tables else []
        updated = ensure_study_section(note_text, figures, tables)
        args.note.write_text(updated, encoding="utf-8")
        return 0

    if args.command == "validate-selected":
        note_text = args.note.read_text(encoding="utf-8")
        fulltext = args.fulltext.read_text(encoding="utf-8")
        figure_candidates = extract_figures_from_fulltext(fulltext)
        table_candidates = extract_tables_from_fulltext(fulltext)
        selected_figures = {part.strip() for part in (args.figures or "").split(",") if part.strip()}
        selected_tables = {part.strip() for part in (args.tables or "").split(",") if part.strip()}
        figures = select_entries_by_numbers(figure_candidates, selected_figures, attr="image_id") if selected_figures else []
        tables = select_entries_by_numbers(table_candidates, selected_tables) if selected_tables else []
        missing = validate_selected_blocks(note_text, figures, tables)
        if missing:
            for item in missing:
                print(item)
            return 1
        print("OK")
        return 0

    if args.command == "validate-note":
        note_text = args.note.read_text(encoding="utf-8")
        fulltext = args.fulltext.read_text(encoding="utf-8")
        # Auto-load figure-map.json from same directory as fulltext if available
        figure_map = None
        figure_map_path = args.fulltext.parent / "figure-map.json"
        if figure_map_path.exists():
            try:
                figure_map = json.loads(figure_map_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        figure_candidates = extract_figures_from_fulltext(fulltext, figure_map)
        table_candidates = extract_tables_from_fulltext(fulltext)
        selected_figures = {part.strip() for part in (args.figures or "").split(",") if part.strip()}
        selected_tables = {part.strip() for part in (args.tables or "").split(",") if part.strip()}
        figures = (
            select_entries_by_numbers(figure_candidates, selected_figures, attr="image_id")
            if selected_figures
            else build_figure_plan(figure_candidates)
        )
        tables = select_entries_by_numbers(table_candidates, selected_tables) if selected_tables else []
        issues = validate_deep_note(note_text, figures, tables)
        if issues:
            for item in issues:
                print(item)
            return 1
        print("OK")
        return 0

    if args.command == "queue":
        queue = scan_deep_reading_queue(args.vault)
        if args.format == "json":
            print(json.dumps(queue, ensure_ascii=False, indent=2))
        else:
            ready = [row for row in queue if row["ocr_status"] == "done"]
            blocked = [row for row in queue if row["ocr_status"] != "done"]
            print(f"# 待精读队列 ({len(queue)} 篇)")
            print()
            if ready:
                print(f"## 就绪 ({len(ready)} 篇) — OCR 完成")
                print()
                for row in ready:
                    print(f"- `{row['zotero_key']}` | {row['domain']} | {row['title']}")
                print()
            if blocked:
                print(f"## 阻塞 ({len(blocked)} 篇) — 等待 OCR")
                print()
                for row in blocked:
                    print(f"- `{row['zotero_key']}` | {row['domain']} | {row['title']} | OCR: {row['ocr_status']}")
                print()
            if not ready and not blocked:
                print("暂无待精读论文。")
        return 0

    if args.command == "figure-map":
        fulltext = args.fulltext.read_text(encoding="utf-8")
        result = build_figure_map(fulltext, zotero_key=args.key)
        result["generated_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"figure-map: wrote {args.out}")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "chart-type-scan":
        figure_map = _read_json(args.figure_map)
        if not figure_map:
            print("ERROR: Could not read figure-map.json or file is empty", file=__import__("sys").stderr)
            return 1
        result = build_chart_type_map(figure_map)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"chart-type-scan: wrote {args.out}")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
