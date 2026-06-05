"""Extract figure/clustering functions from origin/master ocr.py."""
import subprocess, re, sys

raw = subprocess.run(
    ["git", "show", "origin/master:paperforge/worker/ocr.py"],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
).stdout

func_starts = [
    "def clean_block_text", "def is_subfigure_label",
    "def media_clusters", "def _bbox_width", "def _bbox_height",
    "def _bbox_horizontal_overlap", "def _bbox_vertical_overlap",
    "def _bbox_horizontal_overlap_ratio", "def _bbox_center_x",
    "def _bbox_center_y", "def _cluster_bbox", "def _union_bboxes",
    "def is_formal_figure_legend", "def is_numbered_figure_caption",
    "def _figure_caption_blocks", "def estimate_body_column_width",
    "def is_body_paragraph_like_text_block",
    "def _precaption_media_region", "def compute_precaption_composite_regions",
    "def is_embedded_figure_text_block",
]

lines = raw.split("\n")

# Find line numbers for each function
func_lines = {}
for i, line in enumerate(lines):
    stripped = line.strip()
    for fname in func_starts:
        if stripped.startswith(fname) and fname not in func_lines:
            func_lines[fname] = i

# Extract function bodies (from def to next def at same indent level)
extracted = {}
for fname, start_line in func_lines.items():
    # Find the indentation of the def
    orig_indent = len(lines[start_line]) - len(lines[start_line].lstrip())
    # Read until next top-level def
    end_line = len(lines)
    for j in range(start_line + 1, len(lines)):
        ls = lines[j]
        if ls.strip() and not ls.startswith("#") and not ls.startswith(" ") and not ls.startswith("\n"):
            curr_indent = len(ls) - len(ls.lstrip())
            if curr_indent <= orig_indent and not ls.startswith(" "):
                end_line = j
                break
    extracted[fname] = "\n".join(lines[start_line:end_line])

# Print all extracted functions
for fname in sorted(extracted.keys()):
    print(f"=== {fname} ===")
    print(extracted[fname])
    print()
