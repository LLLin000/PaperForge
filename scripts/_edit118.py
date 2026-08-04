# Finish #118 edits: slugify (CRLF) + reader helper (CRCRLF).
from pathlib import Path

# 2. slugify: CRLF file
p = Path("tests/test_utils_slugify.py")
b = p.read_bytes()
old = b'    def test_18xx_not_extracted(self) -> None:'
assert old in b, "slugify anchor missing"
start = b.find(old)
end = b.find(b"\r\n\r\n", start)  # blank line after test body (CRLF file)
assert end != -1, "slugify end anchor missing"
body = b[start : end + 2]
new_body = (
    b"    def test_18xx_extracted_for_slug(self) -> None:\r\n"
    + b"        # _utils._extract_year uses \\d{4} (any 4-digit run) \xe2\x80\x94 19th-century\r\n"
    + b"        # literature is real and the year in a slug filename is harmless.\r\n"
    + b"        # The (19|20) anchor lives in core.date_utils.extract_year, which is\r\n"
    + b"        # a different function; this test asserted the wrong implementation\r\n"
    + b"        # contract (issue #118).\r\n"
    + b'        assert _extract_year("old 1899 ref") == "1899"'
)
b = b[:start] + new_body + b[end + 2 :]
p.write_bytes(b)
print("slugify: replaced")

# 3. reader helper: CRCRLF file
p = Path("tests/test_ocr_real_paper_regressions.py")
b = p.read_bytes()
old = (
    b"def _reader_figure_index(reader_payload: dict) -> tuple[dict[int, dict], dict[int, dict]]:\r\r\n"
    + b'    normalized = reader_payload.get("normalized_inputs", {})\r\r\n'
    + b"    matched = {\r\r\n"
    + b'        int(item["figure_number"]): item\r\r\n'
    + b'        for item in normalized.get("matched_figures", [])\r\r\n'
    + b'        if item.get("figure_number") is not None\r\r\n'
    + b"    }"
)
new = (
    b"def _reader_figure_index(reader_payload: dict) -> tuple[dict[int, dict], dict[int, dict]]:\r\r\n"
    + b'    normalized = reader_payload.get("normalized_inputs", {})\r\r\n'
    + b"    # A figure may span pages as several matched entries (cross-page\r\r\n"
    + b"    # continuation is by design). Dict-comprehension order would keep the\r\r\n"
    + b"    # LAST entry, which can be a zero-asset ghost; keep the entry that\r\r\n"
    + b"    # actually owns assets instead (issue #118).\r\r\n"
    + b"    matched: dict[int, dict] = {}\r\r\n"
    + b'    for item in normalized.get("matched_figures", []):\r\r\n'
    + b'        if item.get("figure_number") is None:\r\r\n'
    + b"            continue\r\r\n"
    + b'        num = int(item["figure_number"])\r\r\n'
    + b"        prev = matched.get(num)\r\r\n"
    + b'        if prev is None or len(item.get("asset_block_ids") or []) > len(\r\r\n'
    + b'            prev.get("asset_block_ids") or []\r\r\n'
    + b"        ):\r\r\n"
    + b"            matched[num] = item"
)
assert old in b, "reader helper anchor missing"
b = b.replace(old, new, 1)
p.write_bytes(b)
print("reader helper replaced")
print("done")
