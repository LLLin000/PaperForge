from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_FIELDS = [
    "block_id",
    "page",
    "review_status",
    "truth_role",
    "truth_zone",
    "truth_reference_membership",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify OCR truth-review coverage against audit_scope.json")
    parser.add_argument("audit_dir", help="Path like audit/CAQNW9Q2")
    return parser


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def verify(audit_dir: Path) -> tuple[int, dict]:
    scope_path = audit_dir / "audit_scope.json"
    review_path = audit_dir / "block_review.jsonl"
    if not scope_path.exists():
        raise SystemExit(f"Missing audit scope: {scope_path}")
    if not review_path.exists():
        raise SystemExit(f"Missing block review file: {review_path}")

    scope = _load_json(scope_path)
    reviews = _load_jsonl(review_path)
    required = {str(item): True for item in scope.get("required_block_ids", [])}
    reviewed_valid: dict[str, dict] = {}
    invalid_rows: list[dict] = []
    page_counts: dict[int, int] = {}

    for row in reviews:
        block_id = str(row.get("block_id", "")).strip()
        if not block_id:
            invalid_rows.append({"block_id": None, "reason": "missing_block_id", "row": row})
            continue
        missing_fields = [field for field in REQUIRED_FIELDS if row.get(field) in (None, "")]
        if row.get("review_status") != "reviewed":
            missing_fields.append("review_status=reviewed")
        evidence = row.get("evidence") or {}
        if not isinstance(evidence, dict) or not evidence.get("annotated_page"):
            missing_fields.append("evidence.annotated_page")
        if missing_fields:
            invalid_rows.append({"block_id": block_id, "reason": "missing_fields", "fields": missing_fields})
            continue
        reviewed_valid[block_id] = row
        page = int(row.get("page", 0) or 0)
        if page > 0:
            page_counts[page] = page_counts.get(page, 0) + 1

    missing_block_ids = sorted([block_id for block_id in required if block_id not in reviewed_valid])
    missing_pages = []
    for page_row in scope.get("selected_page_requirements", []):
        page = int(page_row.get("page", 0) or 0)
        if page_row.get("must_review_page") and page_counts.get(page, 0) == 0:
            missing_pages.append(page)

    status = "PASS"
    if invalid_rows or missing_block_ids or missing_pages:
        status = "FAIL"

    coverage_ratio = (len(required) - len(missing_block_ids)) / len(required) if required else 1.0
    report = {
        "paper_key": audit_dir.name,
        "mode": scope.get("mode"),
        "required_block_ids": sorted(required.keys()),
        "reviewed_block_ids": sorted(reviewed_valid.keys()),
        "missing_block_ids": missing_block_ids,
        "missing_pages": missing_pages,
        "invalid_rows": invalid_rows,
        "coverage_ratio": coverage_ratio,
        "status": status,
    }
    return (0 if status == "PASS" else 1), report


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    audit_dir = Path(args.audit_dir)
    if not audit_dir.exists():
        raise SystemExit(f"Audit dir not found: {audit_dir}")
    code, report = verify(audit_dir)
    _write_json(audit_dir / "coverage_check.json", report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
