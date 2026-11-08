from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
_NUMERIC = re.compile(r"^[\s(+-]*\d[\d,]*(?:\.\d+)?(?:\s*[eE][+-]?\d+)?\s*%?\s*[)]?$")
_PVALUE = re.compile(r"\bp\s*(?:=|<|>|≤|≥)\s*\.?\d", re.I)
_UNIT = re.compile(
    r"(?:\b(?:mm|cm|m|μm|µm|nm|km|kg|mg|g|ml|μl|µl|l|s|min|h|day|days|year|years|%)\b"
    r"|\bn\s*/\s*10\s*\^?\s*\d+)",
    re.I,
)
_TAG = re.compile(r"</?(?:table|thead|tbody|tfoot|tr|td|th|caption|ul|ol|li|div|p|br)\b", re.I)
_MD_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$", re.M)


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.rows = self.max_columns = self.row_columns = 0
        self.header_rows_heur = self.cells = self.numeric_cells = 0
        self.cells_with_rowspan = self.cells_with_colspan = 0
        self.cells_with_pvalue = self.cells_with_unit = 0
        self._cell_depth = 0
        self._cell_text: list[str] = []
        self.errors = 0
        self._row_started = False
        self._row_cell_count = self._row_numeric_count = 0
        self._row_non_numeric_count = 0
        self._row_stats: list[tuple[bool, int, int]] = []
        self.current_row_header = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "tr":
            if self._row_started:
                self.errors += 1
                self._finish_row()
            self._row_started = True
            self.rows += 1
            self.row_columns = 0
            self.current_row_header = False
            self._row_cell_count = self._row_numeric_count = self._row_non_numeric_count = 0
        elif tag in {"td", "th"}:
            self._finish_cell()
            self._cell_depth = 1
            self._cell_text = []
            self.cells += 1
            self.row_columns += self._span(attrs_dict.get("colspan"))
            self.cells_with_colspan += attrs_dict.get("colspan") is not None
            self.cells_with_rowspan += attrs_dict.get("rowspan") is not None
            self.current_row_header |= tag == "th"
        elif self._cell_depth:
            self._cell_depth += 1
        if tag not in _VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"}:
            if not self._cell_depth:
                self.errors += 1
            else:
                self._finish_cell()
        elif tag == "tr":
            self._finish_row()
        if tag not in self.stack:
            self.errors += 1
            return
        idx = len(self.stack) - 1 - self.stack[::-1].index(tag)
        if idx != len(self.stack) - 1:
            self.errors += 1
        del self.stack[idx:]

    def handle_data(self, data: str) -> None:
        if self._cell_depth:
            self._cell_text.append(data)

    def close(self) -> None:
        super().close()
        self._finish_cell()
        self._finish_row()
        self.errors += len(self.stack)
        self.header_rows_heur = sum(th for th, _, _ in self._row_stats)
        if len(self._row_stats) > 1:
            first_th, first_cells, first_numeric = self._row_stats[0]
            later_numeric = any(numeric for _, _, numeric in self._row_stats[1:])
            if not first_th and first_cells >= 2 and first_cells - first_numeric > first_cells / 2 and later_numeric:
                self.header_rows_heur += 1

    def _finish_cell(self) -> None:
        if not self._cell_depth:
            return
        text = " ".join("".join(self._cell_text).split())
        numeric = bool(text and _NUMERIC.fullmatch(text))
        self.numeric_cells += numeric
        self._row_cell_count += 1
        self._row_numeric_count += numeric
        self._row_non_numeric_count += not numeric
        self.cells_with_pvalue += bool(_PVALUE.search(text))
        self.cells_with_unit += bool(_UNIT.search(text))
        self._cell_depth = 0
        self._cell_text = []

    def _finish_row(self) -> None:
        if not self._row_started:
            return
        self.max_columns = max(self.max_columns, self.row_columns)
        self._row_stats.append((self.current_row_header, self._row_cell_count, self._row_numeric_count))
        self._row_started = False

    @staticmethod
    def _span(value: str | None) -> int:
        try:
            return max(1, int(value or 1))
        except ValueError:
            return 1

def audit_table_html(html: str) -> dict[str, Any]:
    parser = _TableParser()
    try:
        parser.feed(html or "")
        parser.close()
    except Exception:
        parser.errors += 1
    return {
        "html_present": bool(html and html.strip()),
        "html_parse_errors": parser.errors,
        "rows": parser.rows,
        "max_columns": parser.max_columns,
        "header_rows_heur": parser.header_rows_heur,
        "cells_with_rowspan": parser.cells_with_rowspan,
        "cells_with_colspan": parser.cells_with_colspan,
        "numeric_cell_ratio": parser.numeric_cells / parser.cells if parser.cells else 0.0,
        "cells_with_pvalue": parser.cells_with_pvalue,
        "cells_with_unit": parser.cells_with_unit,
    }


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _caption_matches(caption: str, markdown: str) -> bool:
    def normalize(value: str) -> str:
        return re.sub(r"[\s$]+", "", value).casefold()

    return bool(caption and normalize(caption) in normalize(markdown))

def audit_paper(paper_dir: Path) -> dict[str, Any]:
    paper_dir = Path(paper_dir)
    inventory = _read_json(paper_dir / "structure" / "table_inventory.json") or {}
    tables = inventory.get("tables", [])
    if not isinstance(tables, list):
        tables = []
    fulltext_path = paper_dir / "render" / "fulltext.md"
    fulltext = fulltext_path.read_text(encoding="utf-8", errors="replace") if fulltext_path.is_file() else ""
    rows: list[dict[str, Any]] = []
    truth_sources: Counter[str] = Counter()
    (
        html_total,
        html_errors,
        total_rows,
        max_columns,
        header_rows,
        rowspans,
        colspans,
        pvalues,
        units,
        notes,
        caption_length,
        numeric,
        cells,
    ) = (0,) * 13
    for index, table in enumerate(tables):
        if not isinstance(table, dict):
            continue
        table_id = str(table.get("table_id") or f"table_{index + 1:03d}")
        html = str(table.get("assistive_text") or "")
        metric = audit_table_html(html)
        md_path = paper_dir / "render" / "tables" / f"{table_id}.md"
        markdown = md_path.read_text(encoding="utf-8", errors="replace") if md_path.is_file() else ""
        caption = str(table.get("caption_text") or "")
        image_ref = bool(re.search(r"!\[[^]]*\]\([^)]*\)|!\[\[[^]]+\]\]", markdown))
        caption_in_markdown = _caption_matches(caption, markdown)
        structured = bool(_TAG.search(markdown) or _MD_TABLE_ROW.search(markdown))
        source = str(table.get("truth_source") or "unknown")
        truth_sources[source] += 1
        metric.update({
            "table_id": table_id,
            "caption_length": len(caption),
            "notes_count": len(table.get("note_block_ids") or table.get("notes") or []),
            "truth_source": source,
            "markdown_exists": md_path.is_file(),
            "markdown_contains_image": image_ref,
            "markdown_contains_caption": caption_in_markdown,
            "markdown_emits_html_or_structured_content": structured,
        })
        rows.append(metric)
        html_total += metric["html_present"]
        html_errors += metric["html_parse_errors"]
        total_rows += metric["rows"]
        max_columns = max(max_columns, metric["max_columns"])
        header_rows += metric["header_rows_heur"]
        rowspans += metric["cells_with_rowspan"]
        colspans += metric["cells_with_colspan"]
        pvalues += metric["cells_with_pvalue"]
        units += metric["cells_with_unit"]
        notes += metric["notes_count"]
        caption_length += metric["caption_length"]
        cell_count = sum(1 for _ in re.finditer(r"<(?:td|th)\b", html, re.I))
        cells += cell_count
        numeric += round(metric["numeric_cell_ratio"] * cell_count)
    return {
        "key": paper_dir.name,
        "tables_total": len(tables),
        "html_present": html_total,
        "html_parse_errors": html_errors,
        "rows": total_rows,
        "max_columns": max_columns,
        "header_rows_heur": header_rows,
        "cells_with_rowspan": rowspans,
        "cells_with_colspan": colspans,
        "numeric_cell_ratio": numeric / cells if cells else 0.0,
        "cells_with_pvalue": pvalues,
        "cells_with_unit": units,
        "caption_length": caption_length,
        "notes_count": notes,
        "truth_source_distribution": dict(sorted(truth_sources.items())),
        "markdown_tables": rows,
        "markdown_contains_image": sum(row["markdown_contains_image"] for row in rows),
        "markdown_contains_caption": sum(row["markdown_contains_caption"] for row in rows),
        "markdown_emits_html_or_structured_content": sum(
            row["markdown_emits_html_or_structured_content"] for row in rows
        ),
        "fulltext_emits_html_or_structured_content": bool(_TAG.search(fulltext) or _MD_TABLE_ROW.search(fulltext)),
    }


def audit_corpus(ocr_root: Path, keys: list[str] | None = None, limit: int | None = None) -> dict[str, Any]:
    ocr_root = Path(ocr_root)
    selected = list(keys) if keys else sorted(path.name for path in ocr_root.iterdir() if path.is_dir())
    if limit is not None:
        selected = selected[:max(0, limit)]
    papers = [audit_paper(ocr_root / key) for key in selected if (ocr_root / key).is_dir()]
    return {"papers": papers, "summary": _summary(papers)}


def _summary(papers: list[dict[str, Any]]) -> dict[str, Any]:
    summed = (
        "tables_total",
        "html_present",
        "html_parse_errors",
        "rows",
        "header_rows_heur",
        "cells_with_rowspan",
        "cells_with_colspan",
        "cells_with_pvalue",
        "cells_with_unit",
        "caption_length",
        "notes_count",
        "markdown_contains_image",
        "markdown_contains_caption",
        "markdown_emits_html_or_structured_content",
    )
    result: dict[str, Any] = {name: sum(paper[name] for paper in papers) for name in summed}
    result["papers"] = len(papers)
    result["max_columns"] = max((paper["max_columns"] for paper in papers), default=0)
    result["numeric_cell_ratio"] = sum(p["numeric_cell_ratio"] for p in papers) / len(papers) if papers else 0.0
    dist: Counter[str] = Counter()
    for paper in papers:
        dist.update(paper["truth_source_distribution"])
    result["truth_source_distribution"] = dict(sorted(dist.items()))
    result["fulltext_emits_html_or_structured_content"] = sum(p["fulltext_emits_html_or_structured_content"] for p in papers)  # noqa: E501
    return result


def _markdown(report: dict[str, Any]) -> str:
    headers = "| Papers | Tables | HTML | Parse errors | Rows | Max cols | Header rows | Rowspan | Colspan | Numeric ratio | P-value cells | Unit cells | Notes | Markdown images | Captions | Structured markdown | Structured fulltext |"  # noqa: E501
    separator = "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    s = report["summary"]
    row = f"| {s['papers']} | {s['tables_total']} | {s['html_present']} | {s['html_parse_errors']} | {s['rows']} | {s['max_columns']} | {s['header_rows_heur']} | {s['cells_with_rowspan']} | {s['cells_with_colspan']} | {s['numeric_cell_ratio']:.3f} | {s['cells_with_pvalue']} | {s['cells_with_unit']} | {s['notes_count']} | {s['markdown_contains_image']} | {s['markdown_contains_caption']} | {s['markdown_emits_html_or_structured_content']} | {s['fulltext_emits_html_or_structured_content']} |"  # noqa: E501
    return "\n".join((headers, separator, row))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only assistive table HTML fidelity audit")
    parser.add_argument("--ocr-root", "--vault", dest="ocr_root", required=True, type=Path)
    parser.add_argument("--keys", nargs="*", help="paper keys, or a text file containing keys")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--out", type=Path, help="write JSON report")
    parser.add_argument("--summary", action="store_true", help="print a Markdown summary table")
    args = parser.parse_args(argv)
    keys = args.keys
    if keys and len(keys) == 1 and Path(keys[0]).is_file():
        keys = Path(keys[0]).read_text(encoding="utf-8").split()
    report = audit_corpus(args.ocr_root, keys, args.limit)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(_markdown(report) if args.summary else json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
