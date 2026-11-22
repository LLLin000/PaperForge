//! Native SQLite FTS5 search, Base table snapshots, Living Memory reads,
//! and Zero-Python Veteran Provenance detection.

use crate::config_ops::{load_canonical_config, pf_err, pf_ok, resolve_vault_paths};
use rusqlite::{params_from_iter, Connection, OpenFlags};
use serde_json::{json, Map, Value};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

pub fn resolve_engine_dir(vault: &Path) -> PathBuf {
    if let Ok(cfg) = load_canonical_config(vault) {
        let paths = resolve_vault_paths(vault, &cfg.doc);
        if let Some(pf) = paths.get("paperforge").and_then(|v| v.as_str()) {
            return PathBuf::from(pf);
        }
    }
    let dot_pf = vault.join(".paperforge");
    let legacy_pf = vault.join("System").join("PaperForge");
    if dot_pf.exists() || !legacy_pf.exists() {
        dot_pf
    } else {
        legacy_pf
    }
}

pub fn read_state_seq(vault: &Path) -> (i64, String) {
    let engine = resolve_engine_dir(vault);
    let seq_file = engine.join("indexes").join(".state-seq.json");
    if let Ok(raw) = fs::read_to_string(seq_file) {
        if let Ok(val) = serde_json::from_str::<Value>(&raw) {
            let seq = val.get("seq").and_then(|v| v.as_i64()).unwrap_or(0);
            let upd = val
                .get("updated_at")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            return (seq, upd);
        }
    }
    (0, String::new())
}

pub fn open_readonly_db(db_path: &Path) -> Option<Connection> {
    if !db_path.is_file() {
        return None;
    }
    let conn = Connection::open_with_flags(
        db_path,
        OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
    )
    .ok()?;
    let _ = conn.busy_timeout(std::time::Duration::from_millis(1500));
    Some(conn)
}

fn table_exists(conn: &Connection, name: &str) -> bool {
    conn.query_row(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?1",
        [name],
        |_| Ok(()),
    )
    .is_ok()
}

#[derive(Default)]
struct DbPaperRow {
    title: String,
    first_author: String,
    year: String,
    journal: String,
    domain: String,
    ocr_status: String,
    deep_reading_status: String,
    main_note_path: String,
    impact_factor: String,
    journal_partition: String,
    has_pdf: Option<bool>,
    do_ocr: Option<bool>,
    analyze: Option<bool>,
    collections: Option<Vec<Value>>,
}

fn table_columns(conn: &Connection, table: &str) -> Vec<String> {
    let sql = format!("PRAGMA table_info({table})");
    conn.prepare(&sql)
        .and_then(|mut st| {
            let rows = st.query_map([], |r| r.get::<_, String>(1))?;
            Ok(rows.flatten().collect())
        })
        .unwrap_or_default()
}

/// Native `< 2ms` implementation of `paperforge memory-card base-snapshot --json`.
///
/// Authority contract (SQLite SSOT):
/// - When `paperforge.db` contains `papers` / `workspace_registry` rows, SQLite is
///   authoritative for `ocr_status`, `deep_reading_status`, `title`, `first_author`,
///   `year`, `journal`, `domain`, `main_note_path`, annotation counts, and memory facets.
/// - `formal-library.json` is strictly a secondary supplement for display-only extras
///   not yet materialized into SQLite (`impact_factor`, `impact_factor_source`,
///   `collections`, `has_pdf`, `do_ocr`, `analyze`) or legacy fallback when SQLite is empty.
pub fn handle_base_snapshot(vault: &Path) -> (i32, String, String) {
    let engine = resolve_engine_dir(vault);
    let (seq, updated_at) = read_state_seq(vault);
    let index_path = engine.join("indexes").join("formal-library.json");
    let json_items: Vec<Value> = if let Ok(raw) = fs::read_to_string(&index_path) {
        match serde_json::from_str::<Value>(&raw) {
            Ok(Value::Object(m)) => m
                .get("items")
                .and_then(|v| v.as_array())
                .cloned()
                .unwrap_or_default(),
            Ok(Value::Array(arr)) => arr,
            _ => Vec::new(),
        }
    } else {
        Vec::new()
    };

    let mut json_by_key: HashMap<String, Map<String, Value>> = HashMap::new();
    let mut json_order: Vec<String> = Vec::new();
    for item in json_items {
        let Some(obj) = item.as_object() else { continue };
        let key = obj
            .get("zotero_key")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim()
            .to_string();
        if key.is_empty() {
            continue;
        }
        if !json_by_key.contains_key(&key) {
            json_order.push(key.clone());
        }
        json_by_key.insert(key, obj.clone());
    }

    let mut db_papers: HashMap<String, DbPaperRow> = HashMap::new();
    let mut db_order: Vec<String> = Vec::new();
    let mut ocr_cat_ok: HashMap<String, bool> = HashMap::new();
    let mut ann_counts: HashMap<String, (i64, i64)> = HashMap::new();
    let mut mem_counts: HashMap<String, (i64, String)> = HashMap::new();

    let db_path = engine.join("indexes").join("paperforge.db");
    if let Some(conn) = open_readonly_db(&db_path) {
        if table_exists(&conn, "papers") {
            let cols = table_columns(&conn, "papers");
            let has = |c: &str| cols.iter().any(|x| x == c);
            let sel = |c: &str| -> String {
                if has(c) {
                    format!("COALESCE(CAST({c} AS TEXT), '')")
                } else {
                    "''".to_string()
                }
            };
            let sel_int = |c: &str| -> String {
                if has(c) {
                    format!("{c}")
                } else {
                    "NULL".to_string()
                }
            };
            let sel_opt_text = |c: &str| -> String {
                if has(c) {
                    format!("CAST({c} AS TEXT)")
                } else {
                    "NULL".to_string()
                }
            };
            let sql = format!(
                "SELECT zotero_key, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {} FROM papers",
                sel("title"),
                sel("first_author"),
                sel("year"),
                sel("journal"),
                sel("domain"),
                sel("ocr_status"),
                sel("deep_reading_status"),
                sel("main_note_path"),
                sel("impact_factor"),
                sel("journal_partition"),
                sel_int("has_pdf"),
                sel_int("do_ocr"),
                sel_int("analyze"),
                sel_opt_text("collections_json"),
            );
            if let Ok(mut st) = conn.prepare(&sql) {
                if let Ok(rows) = st.query_map([], |r| {
                    let has_pdf = r.get::<_, Option<i64>>(11).ok().flatten().map(|v| v != 0);
                    let do_ocr = r.get::<_, Option<i64>>(12).ok().flatten().map(|v| v != 0);
                    let analyze = r.get::<_, Option<i64>>(13).ok().flatten().map(|v| v != 0);
                    let cols_raw = r.get::<_, Option<String>>(14).ok().flatten();
                    let collections = cols_raw.and_then(|s| {
                        let t = s.trim();
                        if t.is_empty() {
                            return None;
                        }
                        serde_json::from_str::<Value>(t)
                            .ok()
                            .and_then(|v| v.as_array().cloned())
                    });
                    Ok((
                        r.get::<_, String>(0)?,
                        DbPaperRow {
                            title: r.get::<_, String>(1).unwrap_or_default(),
                            first_author: r.get::<_, String>(2).unwrap_or_default(),
                            year: r.get::<_, String>(3).unwrap_or_default(),
                            journal: r.get::<_, String>(4).unwrap_or_default(),
                            domain: r.get::<_, String>(5).unwrap_or_default(),
                            ocr_status: r.get::<_, String>(6).unwrap_or_default(),
                            deep_reading_status: r.get::<_, String>(7).unwrap_or_default(),
                            main_note_path: r.get::<_, String>(8).unwrap_or_default(),
                            impact_factor: r.get::<_, String>(9).unwrap_or_default(),
                            journal_partition: r.get::<_, String>(10).unwrap_or_default(),
                            has_pdf,
                            do_ocr,
                            analyze,
                            collections,
                        },
                    ))
                }) {
                    for (k, row) in rows.flatten() {
                        let tk = k.trim().to_string();
                        if tk.is_empty() {
                            continue;
                        }
                        if !db_papers.contains_key(&tk) {
                            db_order.push(tk.clone());
                        }
                        db_papers.insert(tk, row);
                    }
                }
            }
        }
        if table_exists(&conn, "workspace_registry") {
            let cols = table_columns(&conn, "workspace_registry");
            let has_note = cols.iter().any(|x| x == "main_note_relpath");
            let has_dom = cols.iter().any(|x| x == "domain");
            let has_title = cols.iter().any(|x| x == "title");
            let sql = format!(
                "SELECT zotero_key, {}, {}, {} FROM workspace_registry",
                if has_note { "COALESCE(main_note_relpath,'')" } else { "''" },
                if has_dom { "COALESCE(domain,'')" } else { "''" },
                if has_title { "COALESCE(title,'')" } else { "''" },
            );
            if let Ok(mut st) = conn.prepare(&sql) {
                if let Ok(rows) = st.query_map([], |r| {
                    Ok((
                        r.get::<_, String>(0)?,
                        r.get::<_, String>(1).unwrap_or_default(),
                        r.get::<_, String>(2).unwrap_or_default(),
                        r.get::<_, String>(3).unwrap_or_default(),
                    ))
                }) {
                    for (k, note_rel, dom, title) in rows.flatten() {
                        let tk = k.trim().to_string();
                        if tk.is_empty() {
                            continue;
                        }
                        let entry = db_papers.entry(tk.clone()).or_insert_with(|| {
                            db_order.push(tk.clone());
                            DbPaperRow::default()
                        });
                        if entry.main_note_path.is_empty() && !note_rel.is_empty() {
                            entry.main_note_path = note_rel;
                        }
                        if entry.domain.is_empty() && !dom.is_empty() {
                            entry.domain = dom;
                        }
                        if entry.title.is_empty() && !title.is_empty() {
                            entry.title = title;
                        }
                    }
                }
            }
        }
        if table_exists(&conn, "ocr_catalog") {
            if let Ok(mut st) = conn.prepare("SELECT zotero_key, COALESCE(tier0_result_ok, 0) FROM ocr_catalog") {
                if let Ok(rows) = st.query_map([], |r| {
                    Ok((r.get::<_, String>(0)?, r.get::<_, i64>(1).unwrap_or(0) != 0))
                }) {
                    for (k, ok) in rows.flatten() {
                        ocr_cat_ok.insert(k, ok);
                    }
                }
            }
        }
        if table_exists(&conn, "paper_annotations") {
            let has_author = table_columns(&conn, "paper_annotations")
                .iter()
                .any(|c| c == "author");
            let sql = if has_author {
                "SELECT paper_id, \
                 SUM(CASE WHEN COALESCE(author, 'user') = 'agent' THEN 0 ELSE 1 END), \
                 SUM(CASE WHEN COALESCE(author, 'user') = 'agent' THEN 1 ELSE 0 END) \
                 FROM paper_annotations GROUP BY paper_id"
            } else {
                "SELECT paper_id, COUNT(*), 0 FROM paper_annotations GROUP BY paper_id"
            };
            if let Ok(mut st) = conn.prepare(sql) {
                if let Ok(rows) = st.query_map([], |r| {
                    Ok((
                        r.get::<_, String>(0)?,
                        r.get::<_, i64>(1).unwrap_or(0),
                        r.get::<_, i64>(2).unwrap_or(0),
                    ))
                }) {
                    for r in rows.flatten() {
                        ann_counts.insert(r.0, (r.1, r.2));
                    }
                }
            }
        }
        if table_exists(&conn, "paper_memory_cards") {
            if let Ok(mut st) = conn.prepare(
                "SELECT zotero_key, COUNT(*), COALESCE(MAX(updated_at),'') FROM paper_memory_cards GROUP BY zotero_key",
            ) {
                if let Ok(rows) = st.query_map([], |r| {
                    Ok((
                        r.get::<_, String>(0)?,
                        r.get::<_, i64>(1).unwrap_or(0),
                        r.get::<_, String>(2).unwrap_or_default(),
                    ))
                }) {
                    for r in rows.flatten() {
                        mem_counts.insert(r.0, (r.1, r.2));
                    }
                }
            }
        }
    }

    let sqlite_authoritative = !db_papers.is_empty();
    let mut keys: Vec<String> = Vec::new();
    let mut seen: std::collections::HashSet<String> = std::collections::HashSet::new();
    // Strict SSOT key membership: when SQLite has authoritative paper records,
    // NEVER union stale JSON-only keys (prevents resurrecting deleted papers).
    let source_order = if sqlite_authoritative { db_order } else { json_order };
    for k in source_order {
        if seen.insert(k.clone()) {
            keys.push(k);
        }
    }

    let mut out_rows = Map::new();
    for key in keys {
        let db_p = db_papers.get(&key);
        let obj = json_by_key.get(&key);

        let json_str = |field: &str| -> String {
            match obj.and_then(|m| m.get(field)) {
                Some(Value::String(s)) => s.clone(),
                Some(Value::Number(n)) => n.to_string(),
                _ => String::new(),
            }
        };
        let pick_db_first = |db_val: Option<&str>, json_field: &str, fallback: &str| -> String {
            if let Some(s) = db_val.filter(|v| !v.is_empty()) {
                return s.to_string();
            }
            let jv = json_str(json_field);
            if !jv.is_empty() {
                return jv;
            }
            fallback.to_string()
        };

        // SQLite is authoritative for ocr_status & deep_reading_status when present.
        let ocr_status = db_p
            .map(|p| p.ocr_status.as_str())
            .filter(|s| !s.is_empty())
            .map(String::from)
            .or_else(|| {
                if ocr_cat_ok.get(&key).copied() == Some(true) {
                    Some("done".to_string())
                } else {
                    None
                }
            })
            .or_else(|| {
                let j = json_str("ocr_status");
                if j.is_empty() { None } else { Some(j) }
            })
            .unwrap_or_else(|| "pending".to_string());

        let dr_status = pick_db_first(
            db_p.map(|p| p.deep_reading_status.as_str()),
            "deep_reading_status",
            "pending",
        );

        let ocr_health = obj
            .and_then(|m| m.get("health"))
            .and_then(|h| h.as_object())
            .and_then(|h| h.get("ocr_health"))
            .and_then(|v| v.as_str())
            .unwrap_or("");

        let (mut u_cnt, mut a_cnt) = ann_counts.get(&key).copied().unwrap_or((0, 0));
        let (mut m_cnt, mut m_upd) = mem_counts
            .get(&key)
            .cloned()
            .unwrap_or_else(|| (0, String::new()));

        // Workspace sidecar fallback only when not yet materialized in SQLite
        if !db_papers.contains_key(&key) {
            if let Some(pr) = obj.and_then(|m| m.get("paper_root")).and_then(|v| v.as_str()) {
                let ws_dir = vault.join(pr.trim_end_matches(['/', '\\']));
                let mc_file = ws_dir.join("ai").join("memory-card.json");
                if let Ok(raw_mc) = fs::read_to_string(mc_file) {
                    if let Ok(Value::Object(facets)) = serde_json::from_str::<Value>(&raw_mc) {
                        m_cnt = facets.len() as i64;
                        m_upd = facets
                            .values()
                            .filter_map(|f| f.get("updated_at").and_then(|u| u.as_str()))
                            .max()
                            .unwrap_or("")
                            .to_string();
                    }
                }
                let ann_file = ws_dir.join("annotations.jsonl");
                if let Ok(raw_ann) = fs::read_to_string(ann_file) {
                    let mut active: HashMap<String, String> = HashMap::new();
                    for line in raw_ann.lines() {
                        let Ok(ev) = serde_json::from_str::<Value>(line) else { continue };
                        let aid = ev
                            .get("ann_id")
                            .and_then(|v| v.as_str())
                            .unwrap_or("")
                            .to_string();
                        if aid.is_empty() {
                            continue;
                        }
                        if ev.get("op").and_then(|v| v.as_str()) == Some("delete")
                            || ev.get("deleted").and_then(|v| v.as_bool()) == Some(true)
                        {
                            active.remove(&aid);
                        } else {
                            let auth = ev
                                .get("author")
                                .and_then(|v| v.as_str())
                                .unwrap_or("user")
                                .to_string();
                            active.insert(aid, auth);
                        }
                    }
                    u_cnt = active.values().filter(|a| a.as_str() != "agent").count() as i64;
                    a_cnt = active.values().filter(|a| a.as_str() == "agent").count() as i64;
                }
            }
        }

        let main_note = db_p
            .map(|p| p.main_note_path.as_str())
            .filter(|s| !s.is_empty())
            .map(String::from)
            .unwrap_or_else(|| {
                obj.and_then(|m| m.get("main_note_path").or_else(|| m.get("note_path")))
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string()
            });
        let needs_diag = matches!(ocr_status.as_str(), "failed" | "done_incomplete" | "unknown")
            || (ocr_status == "done" && !ocr_health.is_empty() && ocr_health != "healthy");

        let collections: Vec<Value> = db_p
            .and_then(|p| p.collections.clone())
            .or_else(|| {
                obj.and_then(|m| m.get("collections"))
                    .and_then(|v| v.as_array())
                    .cloned()
            })
            .unwrap_or_default();

        let has_pdf = db_p
            .and_then(|p| p.has_pdf)
            .or_else(|| obj.and_then(|m| m.get("has_pdf")).and_then(|v| v.as_bool()))
            .unwrap_or(false);
        let do_ocr = db_p
            .and_then(|p| p.do_ocr)
            .or_else(|| obj.and_then(|m| m.get("do_ocr")).and_then(|v| v.as_bool()))
            .unwrap_or(false);
        let analyze = db_p
            .and_then(|p| p.analyze)
            .or_else(|| obj.and_then(|m| m.get("analyze")).and_then(|v| v.as_bool()))
            .unwrap_or(false);

        out_rows.insert(
            key.clone(),
            json!({
                "zotero_key": key,
                "title": pick_db_first(db_p.map(|p| p.title.as_str()), "title", &key),
                "first_author": pick_db_first(db_p.map(|p| p.first_author.as_str()), "first_author", ""),
                "year": pick_db_first(db_p.map(|p| p.year.as_str()), "year", ""),
                "journal": pick_db_first(db_p.map(|p| p.journal.as_str()), "journal", ""),
                "impact_factor": pick_db_first(db_p.map(|p| p.impact_factor.as_str()), "impact_factor", ""),
                "impact_factor_source": json_str("impact_factor_source"),
                "journal_partition": pick_db_first(db_p.map(|p| p.journal_partition.as_str()), "journal_partition", ""),
                "domain": pick_db_first(db_p.map(|p| p.domain.as_str()), "domain", ""),
                "collections": collections,
                "has_pdf": has_pdf,
                "do_ocr": do_ocr,
                "analyze": analyze,
                "ocr_status": ocr_status,
                "deep_reading_status": dr_status,
                "main_note_path": main_note,
                "user_ann_count": u_cnt,
                "agent_ann_count": a_cnt,
                "memory_facet_count": m_cnt,
                "memory_updated_at": m_upd,
                "needs_diagnostic": needs_diag,
            }),
        );
    }

    let out = pf_ok(
        "memory-card",
        json!({
            "seq": seq,
            "updated_at": updated_at,
            "state_authority": if sqlite_authoritative { "sqlite" } else { "legacy_json_fallback" },
            "rows": out_rows,
        }),
    );
    (0, format!("{out}\n"), String::new())
}

fn tokenize_for_fts(q: &str) -> Vec<String> {
    let mut tokens = Vec::new();
    let mut cur = String::new();
    for ch in q.chars() {
        let is_word = ch.is_alphanumeric() || ch == '_' || ('\u{4e00}'..='\u{9fff}').contains(&ch);
        if is_word {
            cur.push(ch);
        } else if !cur.is_empty() {
            tokens.push(std::mem::take(&mut cur));
        }
    }
    if !cur.is_empty() {
        tokens.push(cur);
    }
    tokens
}

#[derive(Default)]
struct SearchFlags {
    query: String,
    limit: i64,
    domain: Option<String>,
    year_from: Option<i64>,
    year_to: Option<i64>,
    ocr: Option<String>,
    deep: Option<String>,
    lifecycle: Option<String>,
    next_step: Option<String>,
    evidence: bool,
    json_out: bool,
}

fn parse_search_argv(argv: &[String]) -> Option<SearchFlags> {
    if argv.first().map(|s| s.as_str()) != Some("search") {
        return None;
    }
    let mut flags = SearchFlags {
        limit: 20,
        ..Default::default()
    };
    let mut i = 1;
    let mut query_set = false;
    while i < argv.len() {
        match argv[i].as_str() {
            "--json" => flags.json_out = true,
            "--evidence" => flags.evidence = true,
            "--limit" => {
                i += 1;
                flags.limit = argv.get(i)?.parse().ok()?;
            }
            "--domain" => {
                i += 1;
                flags.domain = Some(argv.get(i)?.clone());
            }
            "--year-from" => {
                i += 1;
                flags.year_from = Some(argv.get(i)?.parse().ok()?);
            }
            "--year-to" => {
                i += 1;
                flags.year_to = Some(argv.get(i)?.parse().ok()?);
            }
            "--ocr" => {
                i += 1;
                flags.ocr = Some(argv.get(i)?.clone());
            }
            "--deep" => {
                i += 1;
                flags.deep = Some(argv.get(i)?.clone());
            }
            "--lifecycle" => {
                i += 1;
                flags.lifecycle = Some(argv.get(i)?.clone());
            }
            "--next-step" => {
                i += 1;
                flags.next_step = Some(argv.get(i)?.clone());
            }
            arg if arg.starts_with('-') => return None,
            positional => {
                if !query_set {
                    flags.query = positional.to_string();
                    query_set = true;
                }
            }
        }
        i += 1;
    }
    if !flags.json_out || !query_set {
        return None;
    }
    Some(flags)
}

/// Native `< 2ms` SQLite FTS5 BM25 implementation of `paperforge search <query> --json`.
/// Note: when results are empty (`count == 0`) AND Python is available, returns `None` so
/// Python's `query_diagnostic` router can populate fallback recommendations; when Python is
/// absent (zero-Python mode), returns valid empty `matches` directly!
pub fn try_handle_search_cli(
    vault: &Path,
    argv: &[String],
    python_available: bool,
) -> Option<(i32, String, String)> {
    let flags = parse_search_argv(argv)?;
    let engine = resolve_engine_dir(vault);
    let db_path = engine.join("indexes").join("paperforge.db");
    if !db_path.is_file() {
        let out = pf_err(
            "search",
            "path_not_found",
            "Memory database not found. Run paperforge memory build.",
            json!({}),
            &[],
        );
        return Some((1, format!("{out}\n"), String::new()));
    }
    let conn = open_readonly_db(&db_path)?;

    let mut conds = Vec::new();
    let mut filter_vals: Vec<rusqlite::types::Value> = Vec::new();
    if let Some(ref d) = flags.domain {
        if !d.is_empty() {
            conds.push("p.domain = ?");
            filter_vals.push(d.clone().into());
        }
    }
    if let Some(yf) = flags.year_from {
        if yf > 0 {
            conds.push("CAST(p.year AS INTEGER) >= ?");
            filter_vals.push(yf.into());
        }
    }
    if let Some(yt) = flags.year_to {
        if yt > 0 {
            conds.push("CAST(p.year AS INTEGER) <= ?");
            filter_vals.push(yt.into());
        }
    }
    if let Some(ref o) = flags.ocr {
        if !o.is_empty() {
            conds.push("p.ocr_status = ?");
            filter_vals.push(o.clone().into());
        }
    }
    if let Some(ref dp) = flags.deep {
        if !dp.is_empty() {
            conds.push("p.deep_reading_status = ?");
            filter_vals.push(dp.clone().into());
        }
    }
    if let Some(ref lc) = flags.lifecycle {
        if !lc.is_empty() {
            conds.push("p.lifecycle = ?");
            filter_vals.push(lc.clone().into());
        }
    }
    if let Some(ref ns) = flags.next_step {
        if !ns.is_empty() {
            conds.push("p.next_step = ?");
            filter_vals.push(ns.clone().into());
        }
    }
    let filter_clause = if conds.is_empty() {
        String::new()
    } else {
        format!(" AND {}", conds.join(" AND "))
    };

    let run_fts = |match_expr: &str| -> Result<Vec<Value>, rusqlite::Error> {
        let sql = format!(
            "SELECT COALESCE(p.zotero_key,''), COALESCE(p.title,''), COALESCE(p.first_author,''), \
             COALESCE(CAST(p.year AS TEXT),''), COALESCE(p.journal,''), COALESCE(p.domain,''), \
             COALESCE(substr(p.abstract, 1, 300),''), COALESCE(p.ocr_status,''), \
             (SELECT COUNT(*) FROM body_units b WHERE b.paper_id = p.zotero_key AND b.indexable = 1), \
             rank \
             FROM paper_fts f JOIN papers p ON p.rowid = f.rowid \
             WHERE paper_fts MATCH ?{filter_clause} ORDER BY rank LIMIT ?"
        );
        let mut all_params: Vec<rusqlite::types::Value> = vec![match_expr.to_string().into()];
        all_params.extend(filter_vals.clone());
        all_params.push(flags.limit.into());
        let mut st = conn.prepare(&sql)?;
        let rows = st.query_map(params_from_iter(all_params), |r| {
            let abs: String = r.get(6)?;
            let body_cnt: i64 = r.get::<_, i64>(8).unwrap_or(0);
            let rank: f64 = r.get::<_, f64>(9).unwrap_or(0.0);
            Ok(json!({
                "zotero_key": r.get::<_, String>(0)?,
                "title": r.get::<_, String>(1)?,
                "first_author": r.get::<_, String>(2)?,
                "year": r.get::<_, String>(3)?,
                "journal": r.get::<_, String>(4)?,
                "domain": r.get::<_, String>(5)?,
                "abstract": abs,
                "score": rank,
                "text": abs,
                "heading": "",
                "source": "fts",
                "fulltext_available": body_cnt > 0,
                "body_units_count": body_cnt,
                "ocr_status": r.get::<_, String>(7)?,
            }))
        })?;
        rows.collect()
    };

    let mut results = run_fts(&flags.query).ok();
    if results.is_none() {
        let toks = tokenize_for_fts(&flags.query);
        if !toks.is_empty() {
            let quoted = toks
                .iter()
                .map(|t| format!("\"{t}\""))
                .collect::<Vec<_>>()
                .join(" OR ");
            results = run_fts(&quoted).ok();
        }
    }
    let matches = results.unwrap_or_default();
    if matches.is_empty() && python_available {
        return None;
    }

    let data = if flags.evidence {
        json!({
            "query": flags.query,
            "evidence_status": "metadata_only",
            "fulltext_verified": false,
            "metadata_candidates": matches,
            "count": matches.len(),
        })
    } else {
        json!({
            "query": flags.query,
            "matches": matches,
            "count": matches.len(),
            "filters_applied": {
                "domain": flags.domain,
                "year_from": flags.year_from,
                "year_to": flags.year_to,
                "ocr": flags.ocr,
                "deep": flags.deep,
                "lifecycle": flags.lifecycle,
                "next_step": flags.next_step,
            },
            "route_explanation": {
                "primary_arm": "paper_fts",
                "compatibility_mode": false,
            },
        })
    };
    let out = pf_ok("search", data);
    Some((0, format!("{out}\n"), String::new()))
}

/// Fast Zero-Python `upgrade --plan --json` fallback so brand-new users see zero
/// prompts and veteran users immediately see the non-blocking upgrade banner even
/// before Python finishes installing!
pub fn handle_zero_python_upgrade_plan(vault: &Path) -> (i32, String, String) {
    let legacy_sys = vault.join("System").join("PaperForge");
    let legacy_99 = vault.join("99_System").join("PaperForge");
    let dot_pf = vault.join(".paperforge");
    let manifest_path = dot_pf.join("vault-manifest.json");
    let cfg_path = vault.join("paperforge.json");

    let has_legacy_dir = legacy_sys.is_dir() || legacy_99.is_dir();
    let legacy_rel = if legacy_sys.is_dir() {
        Some("System/PaperForge")
    } else if legacy_99.is_dir() {
        Some("99_System/PaperForge")
    } else {
        None
    };
    let has_manifest = manifest_path.is_file();

    let (state, needs_upgrade, signals) = if has_legacy_dir {
        (
            "veteran_legacy",
            true,
            vec![format!("legacy_engine_dir:{}", legacy_rel.unwrap_or("System/PaperForge"))],
        )
    } else if has_manifest {
        ("standard_current", false, vec!["vault_manifest_v2".to_string()])
    } else if cfg_path.is_file() || dot_pf.join("indexes").is_dir() {
        ("veteran_legacy", true, vec!["paperforge_config_without_v2_manifest".to_string()])
    } else {
        ("fresh_or_foreign", false, Vec::new())
    };

    let mut auto_items = Vec::new();
    if let Some(lrel) = legacy_rel {
        auto_items.push(json!({
            "id": "storage.move_to_dot_paperforge",
            "area": "storage",
            "title": format!("将底层引擎目录 {lrel} 收拢至隐藏目录 .paperforge/"),
            "count": 1,
            "fast_cutover": true,
            "detail": "保留可见笔记与 Zotero 原库不动。",
        }));
    }

    let rollback_available = dot_pf.join("backups").is_dir();
    let out = pf_ok(
        "upgrade",
        json!({
            "vault": vault.to_string_lossy(),
            "provenance": {
                "state": state,
                "needs_upgrade": needs_upgrade,
                "confidence": if signals.is_empty() { "none" } else { "high" },
                "signals": signals,
                "legacy_engine_dir": legacy_rel,
            },
            "census": {
                "pf_canonical": { "workspaces": 0 }
            },
            "manifest": Value::Null,
            "rollback_available": rollback_available,
            "category_a_auto": auto_items,
            "category_b_reconfig": [],
            "category_c_tamper": [],
            "cleanup_candidates": [],
            "summary": {
                "auto_count": auto_items.len(),
                "fast_cutover_count": auto_items.len(),
                "progressive_heal_count": 0,
                "reconfig_critical_count": 0,
                "reconfig_minor_count": 0,
                "tamper_count": 0,
                "cleanup_candidate_count": 0,
                "ocr_atoms": {
                    "total": 0,
                    "current": 0,
                    "rebuild_derived_local": 0,
                    "backfill_from_result_json": 0,
                    "re_ocr_needed": 0,
                }
            }
        }),
    );
    (0, format!("{out}\n"), String::new())
}

fn parse_zotero_prefs_data_dir(prefs_path: &Path) -> Option<PathBuf> {
    let raw = fs::read_to_string(prefs_path).ok()?;
    for line in raw.lines() {
        let trimmed = line.trim();
        if !trimmed.contains("\"extensions.zotero.dataDir\"") {
            continue;
        }
        if let Some(after_key) = trimmed.split("\"extensions.zotero.dataDir\"").nth(1) {
            if let Some(first_q) = after_key.find('"') {
                let rest = &after_key[first_q + 1..];
                if let Some(end_q) = rest.rfind('"') {
                    let val = rest[..end_q].replace("\\\\", "\\").replace("\\\"", "\"");
                    let p = PathBuf::from(val.trim());
                    if p.join("zotero.sqlite").is_file() {
                        return Some(p);
                    }
                }
            }
        }
    }
    None
}

fn auto_detect_zotero_dir() -> Option<PathBuf> {
    let home = std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .map(PathBuf::from)
        .ok();
    let mut profile_roots: Vec<PathBuf> = Vec::new();
    if cfg!(windows) {
        if let Ok(appdata) = std::env::var("APPDATA") {
            profile_roots.push(PathBuf::from(appdata).join("Zotero").join("Zotero"));
        }
    } else if cfg!(target_os = "macos") {
        if let Some(ref h) = home {
            profile_roots.push(h.join("Library").join("Application Support").join("Zotero"));
        }
    } else if let Some(ref h) = home {
        profile_roots.push(h.join(".zotero").join("zotero"));
        profile_roots.push(h.join(".var/app/org.zotero.Zotero/.zotero/zotero"));
        profile_roots.push(h.join("snap/zotero-snap/common/.zotero/zotero"));
    }

    for root in profile_roots {
        let ini = root.join("profiles.ini");
        let Ok(txt) = fs::read_to_string(&ini) else { continue };
        let mut is_rel = true;
        let mut cur_path: Option<String> = None;
        for line in txt.lines().chain(std::iter::once("[END]")) {
            let t = line.trim();
            if t.starts_with('[') {
                if let Some(p) = cur_path.take() {
                    let prof_dir = if is_rel { root.join(&p) } else { PathBuf::from(&p) };
                    if let Some(hit) = parse_zotero_prefs_data_dir(&prof_dir.join("prefs.js")) {
                        return Some(hit);
                    }
                }
                is_rel = true;
            } else if let Some(v) = t.strip_prefix("IsRelative=") {
                is_rel = v.trim() != "0";
            } else if let Some(v) = t.strip_prefix("Path=") {
                cur_path = Some(v.trim().to_string());
            }
        }
    }

    if let Some(ref h) = home {
        for cand in [
            h.join("Zotero"),
            h.join(".var/app/org.zotero.Zotero/Zotero"),
            h.join("snap/zotero-snap/common/Zotero"),
        ] {
            if cand.join("zotero.sqlite").is_file() {
                return Some(cand);
            }
        }
    }
    None
}

/// Native Zero-Python `paperforge zotero detect [--path DIR] --json`.
pub fn handle_zotero_detect(path_arg: Option<&str>) -> (i32, String, String) {
    let explicit = path_arg
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(|s| crate::config_ops::expand_tilde(s));
    let detected = explicit.or_else(auto_detect_zotero_dir);
    let Some(zdir) = detected else {
        let out = pf_ok(
            "zotero detect",
            json!({
                "found": false,
                "zotero_dir": "",
                "total_papers": 0,
                "collections": [],
            }),
        );
        return (0, format!("{out}\n"), String::new());
    };
    let db_src = zdir.join("zotero.sqlite");
    if !db_src.is_file() {
        let out = pf_ok(
            "zotero detect",
            json!({
                "found": false,
                "zotero_dir": zdir.to_string_lossy(),
                "total_papers": 0,
                "collections": [],
            }),
        );
        return (0, format!("{out}\n"), String::new());
    }

    // Transactionally consistent read-only snapshot using SQLite Online Backup API
    // (safe while Zotero desktop is open and writing to WAL; never writes to zotero.sqlite).
    let tmp_dir = std::env::temp_dir().join(format!(
        "pf_zot_rust_{}_{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or(0)
    ));
    if let Err(e) = fs::create_dir_all(&tmp_dir) {
        let out = pf_err(
            "zotero detect",
            "ZOTERO_SNAPSHOT_FAILED",
            &format!("Failed to prepare temporary snapshot directory: {e}"),
            json!({ "zotero_dir": zdir.to_string_lossy() }),
            &[],
        );
        return (1, format!("{out}\n"), String::new());
    }
    let snap_db = tmp_dir.join("zotero.sqlite");
    let src_db = zdir.join("zotero.sqlite");

    let mut snap_ok = false;
    let mut last_err = String::new();

    // Primary path: SQLite Online Backup API from read-only source connection
    if let Some(src_conn) = open_readonly_db(&src_db) {
        match Connection::open(&snap_db) {
            Ok(mut dst_conn) => {
                match rusqlite::backup::Backup::new(&src_conn, &mut dst_conn)
                    .and_then(|b| b.run_to_completion(100, std::time::Duration::from_millis(10), None))
                {
                    Ok(()) => {
                        snap_ok = true;
                    }
                    Err(e) => {
                        last_err = format!("SQLite online backup failed: {e}");
                    }
                }
            }
            Err(e) => {
                last_err = format!("Failed to open snapshot destination: {e}");
            }
        }
    }

    // Fallback path: double-checked file copy (e.g. if read-only open blocked on WAL without -shm)
    if !snap_ok {
        let stat_sig = |dir: &Path| -> Vec<(String, u64, u128)> {
            ["", "-wal", "-shm"]
                .iter()
                .filter_map(|suf| {
                    let p = dir.join(format!("zotero.sqlite{suf}"));
                    let m = fs::metadata(&p).ok()?;
                    let mt = m
                        .modified()
                        .ok()
                        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
                        .map(|d| d.as_nanos())
                        .unwrap_or(0);
                    Some(((*suf).to_string(), m.len(), mt))
                })
                .collect()
        };
        for _attempt in 0..3 {
            let before = stat_sig(&zdir);
            let mut copy_ok = true;
            for suf in ["", "-wal", "-shm"] {
                let src = zdir.join(format!("zotero.sqlite{suf}"));
                let dst = tmp_dir.join(format!("zotero.sqlite{suf}"));
                if src.is_file() {
                    if let Err(e) = fs::copy(&src, &dst) {
                        last_err = format!("Failed to copy zotero.sqlite{suf}: {e}");
                        copy_ok = false;
                        break;
                    }
                } else {
                    let _ = fs::remove_file(&dst);
                }
            }
            let after = stat_sig(&zdir);
            if copy_ok && before == after {
                if let Some(check_conn) = open_readonly_db(&snap_db) {
                    let qc = check_conn
                        .query_row("PRAGMA quick_check", [], |r| r.get::<_, String>(0))
                        .unwrap_or_default();
                    if qc.eq_ignore_ascii_case("ok") {
                        snap_ok = true;
                        break;
                    }
                    last_err = format!("Snapshot integrity check failed: {qc}");
                }
            }
            std::thread::sleep(std::time::Duration::from_millis(40));
        }
    }

    if !snap_ok {
        let _ = fs::remove_dir_all(&tmp_dir);
        let msg = if last_err.is_empty() {
            "Unable to read a consistent snapshot of zotero.sqlite".to_string()
        } else {
            last_err
        };
        let out = pf_err(
            "zotero detect",
            "ZOTERO_DB_UNREADABLE",
            &msg,
            json!({ "zotero_dir": zdir.to_string_lossy() }),
            &["Close Zotero or retry once Zotero finishes syncing."],
        );
        return (1, format!("{out}\n"), String::new());
    }

    let Some(conn) = open_readonly_db(&snap_db) else {
        let _ = fs::remove_dir_all(&tmp_dir);
        let out = pf_err(
            "zotero detect",
            "ZOTERO_DB_UNREADABLE",
            "Failed to open copied zotero.sqlite snapshot",
            json!({ "zotero_dir": zdir.to_string_lossy() }),
            &[],
        );
        return (1, format!("{out}\n"), String::new());
    };

    let total_papers: i64 = match conn.query_row(
        "SELECT COUNT(*) FROM items i JOIN itemTypes it ON i.itemTypeID = it.itemTypeID \
         WHERE i.itemID NOT IN (SELECT itemID FROM deletedItems) \
         AND it.typeName NOT IN ('attachment','note','annotation')",
        [],
        |r| r.get(0),
    ) {
        Ok(cnt) => cnt,
        Err(e) => {
            drop(conn);
            let _ = fs::remove_dir_all(&tmp_dir);
            let out = pf_err(
                "zotero detect",
                "ZOTERO_DB_UNREADABLE",
                &format!("Failed to query Zotero items table: {e}"),
                json!({ "zotero_dir": zdir.to_string_lossy() }),
                &[],
            );
            return (1, format!("{out}\n"), String::new());
        }
    };

    let out_cols: Vec<Value>;
    {

        struct ColMeta {
            key: String,
            name: String,
            parent_id: Option<i64>,
        }
        let mut cols: HashMap<i64, ColMeta> = HashMap::new();
        if let Ok(mut st) = conn.prepare(
            "SELECT collectionID, key, collectionName, parentCollectionID FROM collections",
        ) {
            if let Ok(rows) = st.query_map([], |r| {
                Ok((
                    r.get::<_, i64>(0)?,
                    r.get::<_, String>(1)?,
                    r.get::<_, String>(2)?,
                    r.get::<_, Option<i64>>(3)?,
                ))
            }) {
                for (cid, key, name, pid) in rows.flatten() {
                    cols.insert(
                        cid,
                        ColMeta {
                            key,
                            name,
                            parent_id: pid,
                        },
                    );
                }
            }
        }

        let mut direct: HashMap<i64, std::collections::HashSet<i64>> = HashMap::new();
        if let Ok(mut st) = conn.prepare(
            "SELECT ci.collectionID, ci.itemID FROM collectionItems ci \
             JOIN items i ON ci.itemID = i.itemID \
             JOIN itemTypes it ON i.itemTypeID = it.itemTypeID \
             WHERE i.itemID NOT IN (SELECT itemID FROM deletedItems) \
             AND it.typeName NOT IN ('attachment','note','annotation')",
        ) {
            if let Ok(rows) = st.query_map([], |r| Ok((r.get::<_, i64>(0)?, r.get::<_, i64>(1)?))) {
                for (cid, iid) in rows.flatten() {
                    direct.entry(cid).or_default().insert(iid);
                }
            }
        }

        let mut children_map: HashMap<i64, Vec<i64>> = HashMap::new();
        for (&cid, meta) in &cols {
            if let Some(pid) = meta.parent_id {
                children_map.entry(pid).or_default().push(cid);
            }
        }

        fn build_path(
            cid: i64,
            cols: &HashMap<i64, ColMeta>,
            depth: usize,
        ) -> String {
            if depth > 32 {
                return String::new();
            }
            let Some(m) = cols.get(&cid) else { return String::new() };
            if let Some(pid) = m.parent_id {
                if cols.contains_key(&pid) {
                    let pp = build_path(pid, cols, depth + 1);
                    if !pp.is_empty() {
                        return format!("{pp}/{}", m.name);
                    }
                }
            }
            m.name.clone()
        }

        fn subtree_count(
            cid: i64,
            direct: &HashMap<i64, std::collections::HashSet<i64>>,
            children_map: &HashMap<i64, Vec<i64>>,
            acc: &mut std::collections::HashSet<i64>,
            visited: &mut std::collections::HashSet<i64>,
        ) {
            if !visited.insert(cid) {
                return;
            }
            if let Some(s) = direct.get(&cid) {
                acc.extend(s);
            }
            if let Some(kids) = children_map.get(&cid) {
                for &k in kids {
                    subtree_count(k, direct, children_map, acc, visited);
                }
            }
        }

        let mut items_vec: Vec<(String, Value)> = Vec::new();
        for (&cid, meta) in &cols {
            let path = build_path(cid, &cols, 0);
            let direct_cnt = direct.get(&cid).map(|s| s.len()).unwrap_or(0);
            let mut sub_set = std::collections::HashSet::new();
            let mut visited = std::collections::HashSet::new();
            subtree_count(cid, &direct, &children_map, &mut sub_set, &mut visited);
            let parent_key = meta
                .parent_id
                .and_then(|pid| cols.get(&pid))
                .map(|pm| Value::String(pm.key.clone()))
                .unwrap_or(Value::Null);
            let top_level = meta.parent_id.map(|pid| !cols.contains_key(&pid)).unwrap_or(true);
            items_vec.push((
                path.to_ascii_lowercase(),
                json!({
                    "key": meta.key,
                    "name": meta.name,
                    "parent_key": parent_key,
                    "path": path,
                    "direct_item_count": direct_cnt,
                    "item_count": sub_set.len(),
                    "top_level": top_level,
                }),
            ));
        }
        items_vec.sort_by(|a, b| a.0.cmp(&b.0));
        out_cols = items_vec.into_iter().map(|(_, v)| v).collect();
    }
    drop(conn);

    let _ = fs::remove_dir_all(&tmp_dir);
    let out = pf_ok(
        "zotero detect",
        json!({
            "found": true,
            "zotero_dir": zdir.to_string_lossy(),
            "total_papers": total_papers,
            "collections": out_cols,
        }),
    );
    (0, format!("{out}\n"), String::new())
}
