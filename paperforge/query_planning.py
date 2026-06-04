from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

HIGH_SIGNAL_PRIORITY = [
    "doi",
    "zotero_key",
    "citation_key",
    "author",
    "year",
    "title",
    "topic",
]


@dataclass
class QuerySignals:
    doi: str | None
    zotero_key: str | None
    citation_key: str | None
    author_tokens: list[str]
    year_tokens: list[int]
    title_like_tokens: list[str]
    content_terms: list[str]
    collection_hint: str | None = None
    domain_hint: str | None = None


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def detect_doi(text: str) -> str | None:
    match = re.search(r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", text, re.IGNORECASE)
    return match.group(1) if match else None


def detect_zotero_key(text: str) -> str | None:
    if re.fullmatch(r"[A-Z0-9]{8}", text.strip().upper()):
        return text.strip().upper()
    return None


def detect_citation_key(text: str) -> str | None:
    candidate = text.strip()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{5,}", candidate):
        return None
    if not any(ch.isdigit() for ch in candidate) and "-" not in candidate and "_" not in candidate:
        return None
    return candidate


def extract_years(text: str) -> list[int]:
    years = []
    for raw in re.findall(r"\b((?:19|20)\d{2})\b", text):
        years.append(int(raw))
    return years


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9.+-]*|[\u4e00-\u9fff]{2,}", text)


def classify_signals(query: str) -> QuerySignals:
    doi = detect_doi(query)
    zotero_key = detect_zotero_key(query)
    citation_key = None if (doi or zotero_key) else detect_citation_key(query)
    year_tokens = extract_years(query)

    raw_tokens = tokenize(query)
    author_tokens: list[str] = []
    title_like_tokens: list[str] = []
    content_terms: list[str] = []

    lowered = [t.lower() for t in raw_tokens]
    content_keywords = {
        "hz", "v/cm", "v", "ma", "mv", "galvanotaxis", "electrotaxis",
        "dc", "ac", "cc", "pemf", "field", "scaffold", "stimulation",
        "migration", "chondrocyte", "cartilage", "method", "parameter",
    }

    for token in raw_tokens:
        if any(ch.isdigit() for ch in token):
            content_terms.append(token)
            continue
        low = token.lower()
        if low in {"doi", "pmid", "title", "paper", "article"}:
            continue
        if low in content_keywords:
            content_terms.append(token)
            title_like_tokens.append(token)
            continue
        if token[0].isupper() and len(token) >= 3 and not year_tokens:
            author_tokens.append(token)
            continue
        if token[0].isupper() and len(token) >= 3 and year_tokens and not author_tokens:
            author_tokens.append(token)
            continue
        title_like_tokens.append(token)

    if not author_tokens and year_tokens:
        author_tokens = [t for t in raw_tokens if t.lower() not in content_keywords and len(t) >= 3][:1]

    return QuerySignals(
        doi=doi,
        zotero_key=zotero_key,
        citation_key=citation_key,
        author_tokens=_dedupe_keep_order(author_tokens),
        year_tokens=year_tokens,
        title_like_tokens=_dedupe_keep_order(title_like_tokens),
        content_terms=_dedupe_keep_order(content_terms),
    )


def build_query_plan(query: str, intent: str) -> dict:
    signals = classify_signals(query)
    query_class = "metadata_topic"

    if signals.doi or signals.zotero_key or signals.citation_key:
        query_class = "identifier_exact"
    elif signals.author_tokens and signals.year_tokens:
        query_class = "author_year" if len(signals.title_like_tokens) == 0 else "mixed_query"
    elif intent == "content":
        query_class = "content_term"
    elif signals.content_terms and not signals.author_tokens:
        query_class = "metadata_topic"

    query_rules: list[str] = []
    fallback_plan: list[dict] = []

    if query_class == "identifier_exact":
        identifier = signals.doi or signals.zotero_key or signals.citation_key or query.strip()
        primary = {"command": "paper-context", "args": {"key": identifier}}
        query_rules.append("Use exact identifiers directly with paper-context; do not rewrite them.")
        fallback_plan.append({"when": "not_found", "action": "fallback_to_paper_status"})
    elif intent == "content":
        content_query = " ".join(signals.content_terms or signals.title_like_tokens or tokenize(query)[:6]).strip() or query.strip()
        primary = {"command": "retrieve", "args": {"query": content_query, "limit": 30}}
        query_rules.extend([
            "For content lookup, start with retrieve rather than metadata search.",
            "Use content-bearing terms, parameters, and method phrases as they would appear in fulltext.",
        ])
        fallback_plan.extend([
            {"when": "retrieve_unavailable", "action": "interactive_fulltext_fallback"},
            {"when": "zero_results", "action": "interactive_fulltext_fallback"},
        ])
    elif signals.author_tokens and signals.year_tokens:
        primary = {
            "command": "search",
            "args": {
                "query": signals.author_tokens[0],
                "year_from": min(signals.year_tokens),
                "year_to": max(signals.year_tokens),
                "limit": 10,
            },
        }
        query_rules.extend([
            "For metadata search, prefer author and year over mixed natural-language query strings.",
            "When author and year are known, do not include title words in the first-pass search query.",
        ])
        fallback_plan.extend([
            {"when": "zero_results", "action": "report_noncanonical_query_risk"},
            {"when": "multiple_results", "action": "visually_narrow_with_title_terms"},
        ])
    else:
        topic_query = " ".join(signals.title_like_tokens or tokenize(query)[:6]).strip() or query.strip()
        primary = {"command": "search", "args": {"query": topic_query, "limit": 30}}
        query_rules.extend([
            "Use short metadata-facing terms for search: title keywords, author names, domain, or collection.",
            "Do not treat search as semantic fulltext discovery.",
        ])
        fallback_plan.extend([
            {"when": "zero_results", "action": "report_metadata_miss_not_library_absence"},
            {"when": "large_result_set", "action": "narrow_by_domain_year_or_author"},
        ])

    return {
        "intent": intent,
        "query_class": query_class,
        "signals": {
            "doi": signals.doi,
            "zotero_key": signals.zotero_key,
            "citation_key": signals.citation_key,
            "author_tokens": signals.author_tokens,
            "year_tokens": signals.year_tokens,
            "title_like_tokens": signals.title_like_tokens,
            "content_terms": signals.content_terms,
        },
        "signal_priority": HIGH_SIGNAL_PRIORITY,
        "recommended_primary": primary,
        "query_writing_rules": query_rules,
        "fallback_plan": fallback_plan,
    }


def enrich_query_plan_with_runtime(plan: dict, vault: Path) -> dict:
    from paperforge.embedding import get_embed_status
    from paperforge.worker.asset_index import read_index

    embed = get_embed_status(vault)
    retrieve_available = bool(embed.get("healthy", True) and embed.get("db_exists") and embed.get("chunk_count", 0) > 0)
    plan["runtime"] = {
        "retrieve_available": retrieve_available,
        "vector_status": {
            "db_exists": embed.get("db_exists", False),
            "chunk_count": embed.get("chunk_count", 0),
            "healthy": embed.get("healthy", True),
            "error": embed.get("error", ""),
        },
    }

    data = read_index(vault)
    items = []
    if isinstance(data, dict):
        items = data.get("items", [])
    elif isinstance(data, list):
        items = data

    scope = _assess_scope(items, plan["signals"])
    plan["scope_assessment"] = scope

    if plan["intent"] == "discover" and scope["source"] in {"domain", "collection"}:
        if scope["source"] == "domain":
            plan["recommended_primary"] = {
                "command": "context",
                "args": {"domain": scope["label"]},
            }
            plan["query_writing_rules"].append("When the user names a known domain, prefer context --domain over metadata search.")
        else:
            plan["recommended_primary"] = {
                "command": "context",
                "args": {"collection": scope["label"]},
            }
            plan["query_writing_rules"].append("When the user names a known collection, prefer context --collection over metadata search.")
        plan["fallback_plan"].insert(0, {"when": "large_inventory", "action": "summarize_and_offer_narrowing"})

    if plan["intent"] == "content":
        plan["suggested_modes"] = _suggest_content_fallback_modes(scope)
    if plan["intent"] == "content" and not retrieve_available:
        plan["interactive_fallback_required"] = True
    elif plan["intent"] == "content":
        plan["interactive_fallback_required"] = False

    return plan


def _assess_scope(items: list[dict], signals: dict) -> dict:
    matched_items = items
    source = "library"
    label = "full library"

    title_terms = [str(t) for t in signals.get("title_like_tokens", [])]
    content_terms = [str(t) for t in signals.get("content_terms", [])]
    query_terms = title_terms + content_terms

    domain_counts: dict[str, int] = {}
    collection_counts: dict[str, int] = {}
    for entry in items:
        domain = entry.get("domain", "")
        if domain:
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        for collection in entry.get("collections", []) or []:
            if isinstance(collection, str) and collection:
                collection_counts[collection] = collection_counts.get(collection, 0) + 1

    normalized_terms = [str(t).strip().lower() for t in query_terms if str(t).strip()]
    matched_domain = next(
        (
            d for d in domain_counts
            if any(str(d).strip().lower() == token or token in str(d).strip().lower() for token in normalized_terms)
        ),
        None,
    )
    if matched_domain:
        matched_items = [entry for entry in items if entry.get("domain") == matched_domain]
        source = "domain"
        label = matched_domain
    else:
        matched_collection = next(
            (
                c for c in collection_counts
                if any(
                    str(c).strip().lower() == token
                    or token in str(c).strip().lower()
                    or any(part.strip().lower() == token for part in str(c).split("/"))
                    for token in normalized_terms
                )
            ),
            None,
        )
        if matched_collection:
            matched_items = [
                entry for entry in items
                if any(isinstance(col, str) and col.startswith(matched_collection) for col in entry.get("collections", []) or [])
            ]
            source = "collection"
            label = matched_collection

    estimated = len(matched_items)
    fulltext_ready = sum(1 for entry in matched_items if entry.get("lifecycle") in {"fulltext_ready", "deep_read_done", "ai_context_ready"})

    if estimated <= 20:
        recommended_mode = "rg_now"
    elif estimated <= 60:
        recommended_mode = "rg_with_warning"
    else:
        recommended_mode = "ask_user_before_broad_grep"

    return {
        "source": source,
        "label": label,
        "estimated_paper_count": estimated,
        "fulltext_ready_count": fulltext_ready,
        "recommended_mode": recommended_mode,
    }


def _suggest_content_fallback_modes(scope: dict) -> list[dict]:
    source = scope.get("source", "library")
    label = scope.get("label", "current scope")
    modes = [
        {
            "mode": "fulltext_rg_or_grep",
            "description": f"Run literal fulltext search within {label} ({source}) for exact verification.",
        },
        {
            "mode": "metadata_narrow_then_fulltext",
            "description": "Use metadata search to narrow candidate papers first, then run fulltext verification.",
        },
    ]
    if scope.get("recommended_mode") == "ask_user_before_broad_grep":
        modes.insert(
            0,
            {
                "mode": "ask_for_scope_limit",
                "description": "Ask the user to limit collection, domain, or year before broad fulltext search.",
            },
        )
    return modes
