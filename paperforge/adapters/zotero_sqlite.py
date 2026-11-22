"""Direct read-only Zotero SQLite adapter (Zero Better BibTeX requirement).

Reads Zotero collections, bibliographic metadata, creators, attachments, and
citation keys directly from an isolated temporary copy of ``zotero.sqlite``
(+ optional ``better-bibtex.sqlite``) so PaperForge never triggers SQLite lock
conflicts with a running Zotero desktop instance and never alters Zotero's files.
"""

from __future__ import annotations

import configparser
import contextlib
import json
import logging
import os
import re
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Iterator

from paperforge.core.date_utils import extract_year
from paperforge.core.io import read_json, write_json

logger = logging.getLogger(__name__)

_NON_DOCUMENT_TYPES = frozenset({"attachment", "note", "annotation"})


def _parse_prefs_js(prefs_path: Path) -> dict[str, str]:
    """Extract relevant Zotero string preferences from Firefox-style prefs.js."""
    out: dict[str, str] = {}
    if not prefs_path.is_file():
        return out
    try:
        text = prefs_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return out
    pat = re.compile(
        r'user_pref\(\s*"(extensions\.zotero\.(?:dataDir|baseAttachmentPath))"\s*,\s*"((?:[^"\\]|\\.)*)"\s*\)\s*;'
    )
    for m in pat.finditer(text):
        key = m.group(1)
        val = m.group(2).replace("\\\\", "\\").replace('\\"', '"')
        out[key] = val
    return out


def _zotero_profile_dirs() -> list[Path]:
    """Return candidate Zotero Firefox/Gecko profile directories across OSes."""
    home = Path.home()
    roots: list[Path] = []
    if os.name == "nt":
        appdata = os.environ.get("APPDATA") or str(home / "AppData" / "Roaming")
        roots.append(Path(appdata) / "Zotero" / "Zotero")
    elif sys_is_darwin():
        roots.append(home / "Library" / "Application Support" / "Zotero")
    else:
        roots.extend(
            [
                home / ".zotero" / "zotero",
                home / ".var" / "app" / "org.zotero.Zotero" / ".zotero" / "zotero",
                home / "snap" / "zotero-snap" / "common" / ".zotero" / "zotero",
            ]
        )

    profiles: list[Path] = []
    for root in roots:
        ini = root / "profiles.ini"
        if not ini.is_file():
            continue
        cfg = configparser.RawConfigParser()
        try:
            cfg.read(ini, encoding="utf-8")
        except Exception:  # noqa: BLE001
            continue
        for sec in cfg.sections():
            if not sec.startswith("Profile"):
                continue
            raw_path = cfg.get(sec, "Path", fallback="").strip()
            if not raw_path:
                continue
            is_rel = cfg.get(sec, "IsRelative", fallback="1").strip() == "1"
            p = (root / raw_path) if is_rel else Path(raw_path)
            if p.is_dir():
                profiles.append(p)
    return profiles


def sys_is_darwin() -> bool:
    import sys

    return sys.platform == "darwin"


def read_zotero_base_attachment_path() -> Path | None:
    """Resolve Zotero's linked attachment base directory from prefs.js if configured."""
    for prof in _zotero_profile_dirs():
        prefs = _parse_prefs_js(prof / "prefs.js")
        raw = prefs.get("extensions.zotero.baseAttachmentPath", "").strip()
        if raw:
            p = Path(raw).expanduser()
            if p.exists():
                return p
    return None


def auto_detect_zotero_data_dir() -> Path | None:
    """Auto-detect Zotero data directory via profiles.ini/prefs.js then OS defaults.

    Handles custom user-moved data directories (e.g. D:\\Zotero) as well as
    Windows, macOS, Linux native, Flatpak, and Snap defaults.
    """
    candidates: list[Path] = []
    for prof in _zotero_profile_dirs():
        prefs = _parse_prefs_js(prof / "prefs.js")
        custom_dir = prefs.get("extensions.zotero.dataDir", "").strip()
        if custom_dir:
            candidates.append(Path(custom_dir).expanduser())

    home = Path.home()
    candidates.extend(
        [
            home / "Zotero",
            home / ".var" / "app" / "org.zotero.Zotero" / "Zotero",
            home / "snap" / "zotero-snap" / "common" / "Zotero",
        ]
    )
    for cand in candidates:
        try:
            if (cand / "zotero.sqlite").is_file():
                return cand
        except OSError:
            continue
    return None


def _stat_sqlite_group(db_path: Path) -> list[tuple[str, int, int]]:
    sig: list[tuple[str, int, int]] = []
    for suffix in ("", "-wal", "-shm"):
        p = db_path.parent / f"{db_path.name}{suffix}"
        try:
            st = p.stat()
            sig.append((suffix, st.st_size, st.st_mtime_ns))
        except OSError:
            continue
    return sig


def _snapshot_sqlite_ro(src_db: Path, dst_db: Path) -> None:
    """Create a transactionally consistent read-only snapshot of a live SQLite DB.

    Primary path uses SQLite's Online Backup API (`sqlite3.Connection.backup`)
    from a strict read-only URI connection (`?mode=ro`) so concurrent WAL writes
    and checkpoints in a running Zotero desktop instance never produce torn reads
    and Zotero's source files are never written.

    Falls back to a double-checked stat-verified file copy + `PRAGMA quick_check`
    only if read-only open is blocked (e.g., OS-level exclusive lock or WAL mode
    without existing `-shm` file).
    """
    import time

    uri = f"{src_db.resolve().as_uri()}?mode=ro"
    last_err: Exception | None = None
    try:
        src_conn = sqlite3.connect(uri, uri=True, timeout=2.0)
        try:
            dst_conn = sqlite3.connect(str(dst_db))
            try:
                src_conn.backup(dst_conn, pages=100, sleep=0.01)
            finally:
                dst_conn.close()
        finally:
            src_conn.close()
        return
    except sqlite3.Error as exc:
        last_err = exc
        for suffix in ("", "-wal", "-shm"):
            p = dst_db.parent / f"{dst_db.name}{suffix}"
            with contextlib.suppress(OSError):
                p.unlink()

    # Fallback: double-checked file copy + quick_check integrity validation
    for _ in range(3):
        before = _stat_sqlite_group(src_db)
        try:
            for suffix in ("", "-wal", "-shm"):
                src = src_db.parent / f"{src_db.name}{suffix}"
                dst = dst_db.parent / f"{dst_db.name}{suffix}"
                if src.is_file():
                    shutil.copy2(src, dst)
                elif dst.exists():
                    dst.unlink()
            after = _stat_sqlite_group(src_db)
            if before == after:
                chk = sqlite3.connect(str(dst_db))
                try:
                    row = chk.execute("PRAGMA quick_check").fetchone()
                    if row and str(row[0]).lower() == "ok":
                        return
                    last_err = sqlite3.DatabaseError(f"Snapshot quick_check failed: {row}")
                finally:
                    chk.close()
        except (OSError, sqlite3.Error) as exc:
            last_err = exc
        time.sleep(0.05)

    raise sqlite3.OperationalError(
        f"Failed to capture a consistent snapshot of {src_db}: {last_err}"
    )


@contextlib.contextmanager
def open_zotero_snapshot_ro(zotero_dir: Path) -> Iterator[tuple[sqlite3.Connection, sqlite3.Connection | None]]:
    """Yield read-only connections to a consistent temp snapshot of zotero.sqlite (+ optional BBT sqlite)."""
    src_db = zotero_dir / "zotero.sqlite"
    if not src_db.is_file():
        raise FileNotFoundError(f"zotero.sqlite not found in {zotero_dir}")

    with tempfile.TemporaryDirectory(prefix="pf-zot-snap-") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        conn: sqlite3.Connection | None = None
        bbt_conn: sqlite3.Connection | None = None
        try:
            snap_db = tmp_dir / "zotero.sqlite"
            _snapshot_sqlite_ro(src_db, snap_db)
            conn = sqlite3.connect(str(snap_db))
            conn.row_factory = sqlite3.Row

            bbt_src = zotero_dir / "better-bibtex.sqlite"
            if bbt_src.is_file():
                try:
                    bbt_snap = tmp_dir / "better-bibtex.sqlite"
                    _snapshot_sqlite_ro(bbt_src, bbt_snap)
                    bbt_conn = sqlite3.connect(str(bbt_snap))
                    bbt_conn.row_factory = sqlite3.Row
                except (OSError, sqlite3.Error):
                    bbt_conn = None

            yield conn, bbt_conn
        finally:
            for c in (bbt_conn, conn):
                if c is not None:
                    try:
                        c.close()
                    except Exception:
                        pass


def list_zotero_collections(zotero_dir: Path) -> dict:
    """List Zotero collections (with hierarchy & item counts) for UI selection."""
    if not (zotero_dir / "zotero.sqlite").is_file():
        return {"found": False, "zotero_dir": str(zotero_dir), "total_papers": 0, "collections": []}

    with open_zotero_snapshot_ro(zotero_dir) as (conn, _):
        total_row = conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM items i
            JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            WHERE i.itemID NOT IN (SELECT itemID FROM deletedItems)
              AND it.typeName NOT IN ('attachment', 'note', 'annotation')
            """
        ).fetchone()
        total_papers = int(total_row["cnt"] if total_row else 0)

        col_rows = conn.execute(
            """
            SELECT collectionID, key, collectionName, parentCollectionID
            FROM collections
            WHERE collectionID NOT IN (SELECT collectionID FROM deletedCollections)
            ORDER BY collectionName COLLATE NOCASE
            """
        ).fetchall()

        # Some Zotero versions may not have deletedCollections; guard via try if needed,
        # above table exists in Zotero 5/6/7/8. Fallback handled below just in case.
        by_id: dict[int, dict] = {}
        for r in col_rows:
            by_id[int(r["collectionID"])] = {
                "id": int(r["collectionID"]),
                "key": str(r["key"]),
                "name": str(r["collectionName"]),
                "parent_id": int(r["parentCollectionID"]) if r["parentCollectionID"] is not None else None,
            }

        path_cache: dict[int, str] = {}

        def _full_path(cid: int, seen: set[int] | None = None) -> str:
            if cid in path_cache:
                return path_cache[cid]
            seen = seen or set()
            if cid in seen or cid not in by_id:
                return ""
            seen.add(cid)
            node = by_id[cid]
            pid = node["parent_id"]
            if pid and pid in by_id:
                parent_p = _full_path(pid, seen)
                p = f"{parent_p}/{node['name']}" if parent_p else node["name"]
            else:
                p = node["name"]
            path_cache[cid] = p
            return p

        direct_counts: dict[int, set[int]] = {cid: set() for cid in by_id}
        ci_rows = conn.execute(
            """
            SELECT ci.collectionID, ci.itemID
            FROM collectionItems ci
            JOIN items i ON ci.itemID = i.itemID
            JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            WHERE i.itemID NOT IN (SELECT itemID FROM deletedItems)
              AND it.typeName NOT IN ('attachment', 'note', 'annotation')
            """
        ).fetchall()
        for r in ci_rows:
            cid = int(r["collectionID"])
            if cid in direct_counts:
                direct_counts[cid].add(int(r["itemID"]))

        children_map: dict[int, list[int]] = {cid: [] for cid in by_id}
        for cid, node in by_id.items():
            pid = node["parent_id"]
            if pid and pid in children_map:
                children_map[pid].append(cid)

        subtree_memo: dict[int, set[int]] = {}

        def _subtree_items(cid: int) -> set[int]:
            if cid in subtree_memo:
                return subtree_memo[cid]
            s = set(direct_counts.get(cid, set()))
            for child in children_map.get(cid, []):
                s |= _subtree_items(child)
            subtree_memo[cid] = s
            return s

        out_cols = []
        for cid, node in sorted(by_id.items(), key=lambda kv: _full_path(kv[0]).lower()):
            pid = node["parent_id"]
            out_cols.append(
                {
                    "key": node["key"],
                    "name": node["name"],
                    "parent_key": by_id[pid]["key"] if pid and pid in by_id else None,
                    "path": _full_path(cid),
                    "direct_item_count": len(direct_counts.get(cid, set())),
                    "item_count": len(_subtree_items(cid)),
                    "top_level": pid is None or pid not in by_id,
                }
            )
    return {
        "found": True,
        "zotero_dir": str(zotero_dir),
        "total_papers": total_papers,
        "collections": out_cols,
    }


def _safe_domain_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", str(name or "").strip()).strip(". ")
    return cleaned or "Literature"


def _resolve_sqlite_attachment_path(
    raw_path: str,
    att_key: str,
    link_mode: int,
    zotero_dir: Path,
    base_att_dir: Path | None,
) -> tuple[str, str, int]:
    """Return (bbt_like_path, resolved_disk_hint, byte_size)."""
    raw = str(raw_path or "").strip()
    if raw.startswith("storage:"):
        rel = raw[len("storage:") :].lstrip("/\\")
        norm = f"storage:{att_key}/{rel}" if att_key and "/" not in rel else f"storage:{rel}"
        disk = zotero_dir / "storage" / att_key / rel
        size = int(disk.stat().st_size) if disk.is_file() else 0
        return (norm, raw, size)
    if raw.startswith("attachments:") and base_att_dir is not None:
        rel = raw[len("attachments:") :].lstrip("/\\")
        disk = base_att_dir / rel
        size = int(disk.stat().st_size) if disk.is_file() else 0
        return (str(disk), raw, size)
    if raw:
        cand = Path(raw)
        if cand.is_file():
            return (str(cand), raw, int(cand.stat().st_size))
        return (raw, raw, 0)
    # link_mode 0/1 rarely has empty path; check storage/<att_key>/*pdf
    if link_mode in (0, 1) and att_key:
        st_dir = zotero_dir / "storage" / att_key
        if st_dir.is_dir():
            pdfs = sorted(p for p in st_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf")
            if pdfs:
                return (f"storage:{att_key}/{pdfs[0].name}", f"storage:{pdfs[0].name}", int(pdfs[0].stat().st_size))
    return ("", raw, 0)


def build_bbt_export_documents_from_sqlite(
    zotero_dir: Path,
    *,
    selected_collections: list[str] | None = None,
    domain_mode: str = "per_collection",
    unified_domain: str = "Literature",
) -> dict[str, dict]:
    """Read zotero.sqlite and return ``{DomainName: <BBT-JSON-compatible doc>}``.

    Produces the exact `{collections: ..., items: ..., __managed_by: "zotero_sqlite"}`
    structure consumed by ``paperforge.adapters.bbt.load_export_rows`` and
    ``paperforge.worker._domain.export_collection_paths``.
    """
    base_att_dir = read_zotero_base_attachment_path()

    with open_zotero_snapshot_ro(zotero_dir) as (conn, bbt_conn):
        # 1. Collection hierarchy
        col_rows = conn.execute(
            """
            SELECT collectionID, key, collectionName, parentCollectionID
            FROM collections
            """
        ).fetchall()
        cols_by_id: dict[int, dict] = {}
        key_to_cid: dict[str, int] = {}
        for r in col_rows:
            cid = int(r["collectionID"])
            ckey = str(r["key"])
            cols_by_id[cid] = {
                "id": cid,
                "key": ckey,
                "name": str(r["collectionName"]),
                "parent_id": int(r["parentCollectionID"]) if r["parentCollectionID"] is not None else None,
            }
            key_to_cid[ckey] = cid

        children_map: dict[int, list[int]] = {cid: [] for cid in cols_by_id}
        for cid, node in cols_by_id.items():
            pid = node["parent_id"]
            if pid and pid in children_map:
                children_map[pid].append(cid)

        # 2. Better-BibTeX citation keys if present on disk
        bbt_ck_by_item_key: dict[str, str] = {}
        if bbt_conn is not None:
            try:
                for row in bbt_conn.execute("SELECT itemKey, citationKey FROM citationkey").fetchall():
                    if row["itemKey"] and row["citationKey"]:
                        bbt_ck_by_item_key[str(row["itemKey"])] = str(row["citationKey"])
            except sqlite3.Error:
                pass

        # 3. Collection membership
        col_items_by_cid: dict[int, list[int]] = {}
        item_to_col_keys: dict[int, list[str]] = {}
        for row in conn.execute("SELECT collectionID, itemID FROM collectionItems").fetchall():
            cid = int(row["collectionID"])
            iid = int(row["itemID"])
            if cid in cols_by_id:
                col_items_by_cid.setdefault(cid, []).append(iid)
                item_to_col_keys.setdefault(iid, []).append(cols_by_id[cid]["key"])

        # 4. Items (non-deleted documents)
        doc_rows = conn.execute(
            """
            SELECT i.itemID, i.key, it.typeName
            FROM items i
            JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            WHERE i.itemID NOT IN (SELECT itemID FROM deletedItems)
              AND it.typeName NOT IN ('attachment', 'note', 'annotation')
            ORDER BY i.itemID
            """
        ).fetchall()
        docs_by_id: dict[int, dict] = {
            int(r["itemID"]): {"itemID": int(r["itemID"]), "key": str(r["key"]), "itemType": str(r["typeName"])}
            for r in doc_rows
        }

        # 5. Item fields
        field_rows = conn.execute(
            """
            SELECT id.itemID, f.fieldName, idv.value
            FROM itemData id
            JOIN fields f ON id.fieldID = f.fieldID
            JOIN itemDataValues idv ON id.valueID = idv.valueID
            WHERE f.fieldName IN (
                'title', 'abstractNote', 'publicationTitle', 'ISSN',
                'date', 'DOI', 'extra', 'citationKey'
            )
            """
        ).fetchall()
        fields_by_item: dict[int, dict[str, str]] = {}
        for r in field_rows:
            iid = int(r["itemID"])
            if iid in docs_by_id:
                fields_by_item.setdefault(iid, {})[str(r["fieldName"])] = str(r["value"] or "")

        # 6. Creators
        cr_rows = conn.execute(
            """
            SELECT ic.itemID, ct.creatorType, c.firstName, c.lastName, c.fieldMode
            FROM itemCreators ic
            JOIN creators c ON ic.creatorID = c.creatorID
            JOIN creatorTypes ct ON ic.creatorTypeID = ct.creatorTypeID
            ORDER BY ic.itemID, ic.orderIndex
            """
        ).fetchall()
        creators_by_item: dict[int, list[dict]] = {}
        for r in cr_rows:
            iid = int(r["itemID"])
            if iid not in docs_by_id:
                continue
            fmode = int(r["fieldMode"] or 0)
            first = str(r["firstName"] or "")
            last = str(r["lastName"] or "")
            if fmode == 1 and last:
                entry = {"creatorType": str(r["creatorType"]), "name": last}
            else:
                entry = {"creatorType": str(r["creatorType"]), "firstName": first, "lastName": last}
            creators_by_item.setdefault(iid, []).append(entry)

        # 7. Attachments (with local storage size & path resolution)
        att_rows = conn.execute(
            """
            SELECT ia.parentItemID, ia.itemID, i.key AS attKey, ia.linkMode, ia.contentType, ia.path
            FROM itemAttachments ia
            JOIN items i ON ia.itemID = i.itemID
            WHERE ia.parentItemID IS NOT NULL
              AND ia.itemID NOT IN (SELECT itemID FROM deletedItems)
            """
        ).fetchall()
        att_title_rows = conn.execute(
            """
            SELECT id.itemID, idv.value
            FROM itemData id
            JOIN fields f ON id.fieldID = f.fieldID
            JOIN itemDataValues idv ON id.valueID = idv.valueID
            WHERE f.fieldName = 'title' AND id.itemID IN (SELECT itemID FROM itemAttachments)
            """
        ).fetchall()
        att_titles = {int(r["itemID"]): str(r["value"] or "") for r in att_title_rows}

        atts_by_item: dict[int, list[dict]] = {}
        for r in att_rows:
            pid = int(r["parentItemID"])
            if pid not in docs_by_id:
                continue
            att_id = int(r["itemID"])
            att_key = str(r["attKey"] or "")
            link_mode = int(r["linkMode"] or 0)
            ctype = str(r["contentType"] or "")
            raw_path = str(r["path"] or "")
            norm_path, _raw_hint, byte_size = _resolve_sqlite_attachment_path(
                raw_path, att_key, link_mode, zotero_dir, base_att_dir
            )
            if not ctype and norm_path.lower().endswith(".pdf"):
                ctype = "application/pdf"
            if not norm_path:
                continue
            atts_by_item.setdefault(pid, []).append(
                {
                    "title": att_titles.get(att_id, Path(norm_path).name),
                    "path": norm_path,
                    "contentType": ctype,
                    "size": byte_size,
                }
            )

    def _assemble_item(iid: int) -> dict:
        doc = docs_by_id[iid]
        flds = fields_by_item.get(iid, {})
        creators = creators_by_item.get(iid, [])
        extra = flds.get("extra", "")
        zkey = doc["key"]

        # Citation key cascade: Zotero 8 native -> better-bibtex.sqlite -> Extra -> AuthorYear fallback
        ckey = flds.get("citationKey", "").strip() or bbt_ck_by_item_key.get(zkey, "").strip()
        if not ckey and extra:
            for line in extra.splitlines():
                if line.strip().lower().startswith("citation key:"):
                    ckey = line.split(":", 1)[1].strip()
                    break
        if not ckey:
            first_last = ""
            for c in creators:
                if c.get("creatorType") == "author":
                    first_last = re.sub(r"[^A-Za-z0-9]+", "", str(c.get("lastName") or c.get("name") or "")).lower()
                    break
            yr = extract_year(flds.get("date", ""))
            ckey = f"{first_last}{yr}" if first_last else zkey

        pmid = ""
        if extra:
            pm = re.search(r"(?im)^PMID:\s*(\d+)", extra)
            if pm:
                pmid = pm.group(1)

        out = {
            "itemID": iid,
            "key": zkey,
            "itemKey": zkey,
            "itemType": doc["itemType"],
            "title": flds.get("title", "") or zkey,
            "creators": creators,
            "abstractNote": flds.get("abstractNote", ""),
            "publicationTitle": flds.get("publicationTitle", ""),
            "ISSN": flds.get("ISSN", ""),
            "date": flds.get("date", ""),
            "DOI": flds.get("DOI", ""),
            "PMID": pmid,
            "extra": extra,
            "citationKey": ckey,
            "collections": item_to_col_keys.get(iid, []),
            "attachments": atts_by_item.get(iid, []),
        }
        return out

    def _descendant_cids(root_cid: int) -> list[int]:
        out: list[int] = []
        stack = [root_cid]
        seen = set()
        while stack:
            cur = stack.pop()
            if cur in seen or cur not in cols_by_id:
                continue
            seen.add(cur)
            out.append(cur)
            stack.extend(children_map.get(cur, []))
        return out

    def _serialize_collections(cids: list[int], allowed_item_ids: set[int]) -> dict:
        cid_set = set(cids)
        out: dict[str, dict] = {}
        for cid in cids:
            node = cols_by_id[cid]
            pid = node["parent_id"]
            parent_key = cols_by_id[pid]["key"] if pid and pid in cid_set else ""
            out[node["key"]] = {
                "key": node["key"],
                "name": node["name"],
                "parent": parent_key,
                "items": [iid for iid in col_items_by_cid.get(cid, []) if iid in allowed_item_ids],
            }
        return out

    sel = [s.strip() for s in (selected_collections or []) if str(s or "").strip()]
    use_all = not sel or sel == ["*"]

    # Resolve selected collection IDs (accept either collection key or path/name)
    resolved_root_cids: list[int] = []
    if not use_all:
        name_to_cid = {node["name"]: cid for cid, node in cols_by_id.items()}
        for token in sel:
            if token in key_to_cid:
                resolved_root_cids.append(key_to_cid[token])
            elif token in name_to_cid:
                resolved_root_cids.append(name_to_cid[token])

    docs_out: dict[str, dict] = {}
    if domain_mode == "per_collection" and resolved_root_cids:
        used_names: set[str] = set()
        for root_cid in resolved_root_cids:
            cids = _descendant_cids(root_cid)
            iids_set: set[int] = set()
            for cid in cids:
                iids_set.update(col_items_by_cid.get(cid, []))
            iids = sorted(iid for iid in iids_set if iid in docs_by_id)
            dom_name = _safe_domain_filename(cols_by_id[root_cid]["name"])
            if dom_name in used_names:
                dom_name = f"{dom_name}_{cols_by_id[root_cid]['key']}"
            used_names.add(dom_name)
            docs_out[dom_name] = {
                "__managed_by": "zotero_sqlite",
                "collections": _serialize_collections(cids, set(iids)),
                "items": [_assemble_item(iid) for iid in iids],
            }
        return docs_out

    # Unified mode (or full library when no specific collections filtered)
    if resolved_root_cids:
        all_cids_set: set[int] = set()
        iids_set: set[int] = set()
        for rc in resolved_root_cids:
            sub = _descendant_cids(rc)
            all_cids_set.update(sub)
            for cid in sub:
                iids_set.update(col_items_by_cid.get(cid, []))
        cids_list = sorted(all_cids_set)
        iids = sorted(iid for iid in iids_set if iid in docs_by_id)
    else:
        cids_list = sorted(cols_by_id.keys())
        iids = sorted(docs_by_id.keys())

    dom_name = _safe_domain_filename(unified_domain)
    docs_out[dom_name] = {
        "__managed_by": "zotero_sqlite",
        "collections": _serialize_collections(cids_list, set(iids)),
        "items": [_assemble_item(iid) for iid in iids],
    }
    return docs_out


def materialize_zotero_sqlite_exports(
    vault: Path,
    exports_dir: Path,
    zotero_dir: Path,
    *,
    selected_collections: list[str] | None = None,
    domain_mode: str = "per_collection",
    unified_domain: str = "Literature",
) -> list[Path]:
    """Write canonical materialized export files into ``exports_dir`` from ``zotero.sqlite``.

    Leaves manually exported user BBT JSON files untouched; only creates/updates/prunes
    files marked ``"__managed_by": "zotero_sqlite"``.
    """
    exports_dir.mkdir(parents=True, exist_ok=True)
    docs = build_bbt_export_documents_from_sqlite(
        zotero_dir,
        selected_collections=selected_collections,
        domain_mode=domain_mode,
        unified_domain=unified_domain,
    )
    target_names = {f"{dom}.json": doc for dom, doc in docs.items()}

    # Prune stale sqlite-managed export JSONs that are no longer selected
    for existing in sorted(exports_dir.glob("*.json")):
        if existing.name in target_names:
            continue
        try:
            old_doc = read_json(existing)
            if isinstance(old_doc, dict) and old_doc.get("__managed_by") == "zotero_sqlite":
                existing.unlink(missing_ok=True)
        except Exception:
            pass

    written: list[Path] = []
    for fname, doc in sorted(target_names.items()):
        dest = exports_dir / fname
        write_json(dest, doc)
        written.append(dest)
    logger.info(
        "Materialized %d Zotero SQLite export slice(s) into %s (%d total items)",
        len(written),
        exports_dir,
        sum(len(d.get("items", [])) for d in target_names.values()),
    )
    return written
