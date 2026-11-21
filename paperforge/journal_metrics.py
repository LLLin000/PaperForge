"""Multi-source journal impact factor & partition resolver.

Resolution precedence (fast-first, zero-config fallback):
1. Vault/Zotero local plugin caches (``zoterostyle.json`` in vault or ``zotero_dir``)
2. Explicit Zotero ``extra`` metadata (``影响因子:``, ``IF:``, ``JCR:``, ``中科院分区:``)
3. Persistent SQLite ``journal_metrics`` cache inside ``paperforge.db`` (90d TTL)
4. Optional EasyScholar API (when ``easyscholar`` credential is configured) -> ``source="jcr"``
5. Free OpenAlex ``/sources`` open metrics (``2yr_mean_citedness``) -> ``source="openalex_2yr"``

Never raises during sync; offline failures fail soft and preserve empty or cached values.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from pathlib import Path

from paperforge.core.io import read_json

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 90 * 86400
_INMEM_CACHE: dict[str, dict[str, str]] = {}
_OPENALEX_BACKOFF_UNTIL = 0.0

CREATE_JOURNAL_METRICS_TABLE = """
CREATE TABLE IF NOT EXISTS journal_metrics (
    journal_key TEXT PRIMARY KEY,
    journal_name TEXT NOT NULL DEFAULT '',
    issn TEXT NOT NULL DEFAULT '',
    impact_factor TEXT NOT NULL DEFAULT '',
    impact_factor_source TEXT NOT NULL DEFAULT '',
    journal_partition TEXT NOT NULL DEFAULT '',
    fetched_at REAL NOT NULL DEFAULT 0
);
"""


def normalize_journal_key(name: str, issn: str = "") -> str:
    clean_issn = re.sub(r"[^0-9Xx]", "", str(issn or "")).upper()
    clean_name = re.sub(r"[^a-z0-9]+", " ", str(name or "").lower()).strip()
    if clean_issn:
        return f"issn:{clean_issn}|{clean_name}"
    return clean_name


def _ensure_journal_metrics_table(conn: sqlite3.Connection) -> None:
    conn.execute(CREATE_JOURNAL_METRICS_TABLE)


def _read_sqlite_cache(vault: Path, key: str, journal_name: str, issn: str) -> dict[str, str] | None:
    try:
        from paperforge.memory.db import get_memory_db_path, open_live_reader

        db_path = get_memory_db_path(vault)
        if not db_path.is_file():
            return None
        with open_live_reader(vault, db_path) as conn:
            has_tbl = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='journal_metrics'"
            ).fetchone()
            if not has_tbl:
                return None
            clean_name = normalize_journal_key(journal_name, "")
            row = conn.execute(
                """
                SELECT impact_factor, impact_factor_source, journal_partition, fetched_at
                FROM journal_metrics
                WHERE journal_key = ? OR journal_key = ?
                ORDER BY fetched_at DESC LIMIT 1
                """,
                (key, clean_name),
            ).fetchone()
            if not row:
                return None
            if time.time() - float(row[3] or 0) > _CACHE_TTL_SECONDS:
                return None
            return {
                "impact_factor": str(row[0] or ""),
                "impact_factor_source": str(row[1] or ""),
                "journal_partition": str(row[2] or ""),
            }
    except Exception:
        return None


def _write_sqlite_cache(
    vault: Path,
    *,
    key: str,
    journal_name: str,
    issn: str,
    metric: dict[str, str],
) -> None:
    if not key:
        return
    try:
        from paperforge.memory.db import WriterLock, get_connection, get_memory_db_path

        db_path = get_memory_db_path(vault)
        if not db_path.is_file():
            return
        with WriterLock(vault, timeout=2.0):
            with get_connection(vault) as conn:
                _ensure_journal_metrics_table(conn)
                now = time.time()
                for k in {key, normalize_journal_key(journal_name, "")} - {""}:
                    conn.execute(
                        """
                        INSERT INTO journal_metrics(
                            journal_key, journal_name, issn,
                            impact_factor, impact_factor_source, journal_partition, fetched_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(journal_key) DO UPDATE SET
                            impact_factor=excluded.impact_factor,
                            impact_factor_source=excluded.impact_factor_source,
                            journal_partition=excluded.journal_partition,
                            fetched_at=excluded.fetched_at
                        """,
                        (
                            k,
                            journal_name,
                            issn,
                            metric.get("impact_factor", ""),
                            metric.get("impact_factor_source", ""),
                            metric.get("journal_partition", ""),
                            now,
                        ),
                    )
                conn.commit()
    except Exception:
        pass


def parse_extra_journal_metric(extra: str) -> dict[str, str]:
    """Extract IF and CAS/JCR partitions from Zotero Extra text lines."""
    if not extra:
        return {"impact_factor": "", "impact_factor_source": "", "journal_partition": ""}
    if_val = ""
    m_if = re.search(
        r"(?:影响因子|SCI(?:影响因子)?|IF)\s*[:：]\s*([0-9]+(?:\.[0-9]+)?)",
        extra,
        re.IGNORECASE,
    )
    if m_if:
        if_val = m_if.group(1)

    parts: list[str] = []
    m_jcr = re.search(r"JCR\s*[:：]\s*(Q[1-4])", extra, re.IGNORECASE)
    if m_jcr:
        parts.append(m_jcr.group(1).upper())
    m_cas = re.search(r"中科院(?:分区)?\s*[:：]\s*([^\r\n;]+)", extra)
    if m_cas:
        cas_text = m_cas.group(1).strip()
        if cas_text and cas_text not in parts:
            parts.append(cas_text)

    return {
        "impact_factor": if_val,
        "impact_factor_source": "extra" if if_val else "",
        "journal_partition": " · ".join(parts),
    }


def _find_zotero_plugin_db_candidates(vault: Path, zotero_dir: Path | None) -> list[Path]:
    candidates: list[Path] = []
    try:
        from paperforge.config import load_vault_config

        candidates.append(vault / load_vault_config(vault)["system_dir"] / "Zotero" / "zoterostyle.json")
    except Exception:
        pass
    if zotero_dir is not None and zotero_dir.is_dir():
        for name in ("zoterostyle.json", "easyscholar.json", "if_cache.json"):
            candidates.append(zotero_dir / name)
            candidates.append(zotero_dir / "zoterostyle" / name)
    return candidates


def _lookup_local_zoterostyle(
    journal_name: str,
    vault: Path,
    zotero_dir: Path | None,
    preloaded_db: dict | None = None,
) -> dict[str, str] | None:
    dbs: list[dict] = []
    if preloaded_db:
        dbs.append(preloaded_db)
    for path in _find_zotero_plugin_db_candidates(vault, zotero_dir):
        if path.is_file():
            try:
                loaded = read_json(path)
                if isinstance(loaded, dict):
                    dbs.append(loaded)
            except Exception:
                continue

    norm_target = re.sub(r"[^a-z0-9]+", " ", journal_name.lower()).strip()
    for db in dbs:
        entry = db.get(journal_name)
        if not isinstance(entry, dict):
            for k, v in db.items():
                if isinstance(k, str) and isinstance(v, dict):
                    if re.sub(r"[^a-z0-9]+", " ", k.lower()).strip() == norm_target:
                        entry = v
                        break
        if not isinstance(entry, dict):
            continue
        rank = entry.get("rank", entry)
        if not isinstance(rank, dict):
            continue
        sciif = rank.get("sciif", "") or rank.get("sci", "") or ""
        jcr = str(rank.get("sciUp") or rank.get("jcr") or "").strip()
        cas = str(rank.get("sciUpSmall") or rank.get("cas") or "").strip()
        parts = [p for p in (jcr, cas) if p]
        if sciif:
            return {
                "impact_factor": str(sciif),
                "impact_factor_source": "zotero_plugin",
                "journal_partition": " · ".join(parts),
            }
    return None


def _fetch_easyscholar(journal_name: str) -> dict[str, str] | None:
    try:
        from paperforge.credentials import CredentialError, CredentialKey, resolve

        secret_key = resolve(CredentialKey("easyscholar"))
    except Exception:
        return None
    if not secret_key:
        return None

    url = (
        "https://www.easyscholar.cn/open/getPublicationRank?"
        + urllib.parse.urlencode({"secretKey": secret_key, "publicationName": journal_name})
    )
    req = urllib.request.Request(url, headers={"User-Agent": "PaperForge/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if int(payload.get("code", -1)) != 200:
            return None
        data = payload.get("data") or {}
        official = data.get("officialRank", {})
        all_rank = official.get("all") or official.get("select") or {}
        if_val = str(all_rank.get("sciif") or "").strip()
        if not if_val:
            return None
        jcr = str(all_rank.get("sci") or "").strip()
        cas = str(all_rank.get("sciUp") or all_rank.get("sciUpTop") or "").strip()
        parts = [p for p in (jcr, f"中科院{cas}" if cas and "区" not in cas else cas) if p]
        return {
            "impact_factor": if_val,
            "impact_factor_source": "jcr",
            "journal_partition": " · ".join(parts),
        }
    except Exception as exc:
        logger.debug("EasyScholar lookup failed for %s: %s", journal_name, exc)
        return None


def _fetch_openalex_source(journal_name: str, issn: str = "") -> dict[str, str] | None:
    global _OPENALEX_BACKOFF_UNTIL
    if time.time() < _OPENALEX_BACKOFF_UNTIL:
        return None

    clean_issn = re.sub(r"[^0-9Xx-]", "", str(issn or "")).strip()
    if clean_issn and "-" not in clean_issn and len(clean_issn) == 8:
        clean_issn = f"{clean_issn[:4]}-{clean_issn[4:]}"

    urls: list[str] = []
    if clean_issn:
        urls.append(f"https://api.openalex.org/sources/issn:{urllib.parse.quote(clean_issn)}?select=display_name,summary_stats")
    urls.append(
        "https://api.openalex.org/sources?"
        + urllib.parse.urlencode(
            {"search": journal_name, "per-page": "1", "select": "display_name,summary_stats"}
        )
    )

    for url in urls:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "PaperForge/2.0 (mailto:support@paperforge.local)"},
        )
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            src = data if "summary_stats" in data else ((data.get("results") or [None])[0])
            if not isinstance(src, dict):
                continue
            cited = (src.get("summary_stats") or {}).get("2yr_mean_citedness")
            if cited is None:
                continue
            val = float(cited)
            if val <= 0:
                continue
            return {
                "impact_factor": f"{val:.1f}",
                "impact_factor_source": "openalex_2yr",
                "journal_partition": "",
            }
        except Exception as exc:
            logger.debug("OpenAlex lookup skipped for %s: %s", journal_name, exc)
            _OPENALEX_BACKOFF_UNTIL = time.time() + 120.0
            return None
    return None


def lookup_journal_metric(
    journal_name: str,
    extra: str,
    vault: Path,
    *,
    issn: str = "",
    zotero_dir: Path | None = None,
    preloaded_db: dict | None = None,
    allow_network: bool = False,
) -> dict[str, str]:
    """Resolve journal IF, source provenance, and partition without breaking sync offline."""
    empty = {"impact_factor": "", "impact_factor_source": "", "journal_partition": ""}
    if not journal_name:
        return empty

    cache_key = normalize_journal_key(journal_name, issn)

    # 1. Local zoterostyle / plugin DB
    local = _lookup_local_zoterostyle(journal_name, vault, zotero_dir, preloaded_db=preloaded_db)
    if local and local.get("impact_factor"):
        return local

    # 2. Extra field explicit IF/partition
    extra_m = parse_extra_journal_metric(extra)
    if extra_m.get("impact_factor"):
        return extra_m

    # 3. In-memory or SQLite cached metric (covers EasyScholar & OpenAlex from earlier runs)
    if cache_key in _INMEM_CACHE:
        return dict(_INMEM_CACHE[cache_key])

    cached = _read_sqlite_cache(vault, cache_key, journal_name, issn)
    if cached and cached.get("impact_factor"):
        _INMEM_CACHE[cache_key] = dict(cached)
        return cached

    if not allow_network:
        return empty

    mode = "auto"
    try:
        from paperforge.config import load_config

        snap = load_config(vault)
        mode = str(snap.values.get("journal_metrics_mode").value or "auto")
    except Exception:
        mode = "auto"

    if mode == "local_only":
        return empty

    # 4. EasyScholar official JCR + CAS if secretKey is saved
    es = _fetch_easyscholar(journal_name)
    if es and es.get("impact_factor"):
        _INMEM_CACHE[cache_key] = dict(es)
        _write_sqlite_cache(vault, key=cache_key, journal_name=journal_name, issn=issn, metric=es)
        return es

    if mode == "easyscholar":
        return empty

    # 5. OpenAlex free open 2-year citation proxy
    oa = _fetch_openalex_source(journal_name, issn=issn)
    if oa and oa.get("impact_factor"):
        _INMEM_CACHE[cache_key] = dict(oa)
        _write_sqlite_cache(vault, key=cache_key, journal_name=journal_name, issn=issn, metric=oa)
        return oa

    return empty
