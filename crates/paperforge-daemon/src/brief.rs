//! Native `< 5ms` Agent State-Machine Handoff (`agent-brief`) and Filtered Library Query.
//!
//! Replaces multi-step Python startup chains (`pf_bootstrap.py` -> `agent-context` ->
//! `runtime-health`) with a single authoritative, token-bounded snapshot containing:
//! - Resolved vault paths & runtime pointer identity
//! - SQLite SSOT library overview & collection hierarchy
//! - Liveness-verified `.daemon-state.json` active jobs, exclusive barriers & notices
//! - Action-changing deterministic `blocked_actions` & capped `hints`

use crate::config_ops::{
    load_canonical_config, pf_err, pf_ok, resolve_vault_paths, strip_verbatim_prefix, ConfigIssue,
    PF_VERSION,
};
use crate::platform::is_pid_alive;
use crate::query_ops::{handle_base_snapshot, open_readonly_db, read_state_seq, resolve_engine_dir};
use crate::supervisor::NativeControlDaemon;
use rusqlite::Connection;
use serde_json::{json, Map, Value};
use std::collections::{BTreeMap, HashMap, HashSet};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

/// Walk upward up to 10 levels from CWD (or return `explicit`) to locate `paperforge.json`.
pub fn discover_vault_from_cwd(explicit: Option<&Path>) -> Option<PathBuf> {
    if let Some(p) = explicit {
        if !p.as_os_str().is_empty() {
            let abs = fs::canonicalize(p).unwrap_or_else(|_| p.to_path_buf());
            return Some(strip_verbatim_prefix(&abs));
        }
    }
    let mut cur = env::current_dir().ok()?;
    for _ in 0..10 {
        if cur.join("paperforge.json").is_file() {
            let abs = fs::canonicalize(&cur).unwrap_or(cur);
            return Some(strip_verbatim_prefix(&abs));
        }
        let Some(parent) = cur.parent() else {
            break;
        };
        if parent == cur {
            break;
        }
        cur = parent.to_path_buf();
    }
    None
}

fn table_exists(conn: &Connection, name: &str) -> bool {
    conn.query_row(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?1",
        [name],
        |_| Ok(()),
    )
    .is_ok()
}

fn read_runtime_pointer_info() -> Value {
    let Some(pf_home) = crate::mcp::paperforge_home_dir() else {
        return json!({ "status": "missing", "python_path": Value::Null, "paperforge_version": Value::Null });
    };
    let ptr_path = pf_home.join("runtime").join("pointer.json");
    if !ptr_path.is_file() {
        return json!({
            "status": "missing",
            "path": ptr_path.to_string_lossy(),
            "python_path": Value::Null,
            "paperforge_version": Value::Null
        });
    }
    let Ok(raw) = fs::read_to_string(&ptr_path) else {
        return json!({
            "status": "invalid",
            "path": ptr_path.to_string_lossy(),
            "python_path": Value::Null,
            "paperforge_version": Value::Null
        });
    };
    let Ok(val) = serde_json::from_str::<Value>(&raw) else {
        return json!({
            "status": "invalid",
            "path": ptr_path.to_string_lossy(),
            "python_path": Value::Null,
            "paperforge_version": Value::Null
        });
    };
    if val.get("schema_version").and_then(|v| v.as_i64()) != Some(1) {
        return json!({
            "status": "invalid",
            "path": ptr_path.to_string_lossy(),
            "python_path": Value::Null,
            "paperforge_version": Value::Null
        });
    }
    let py = val
        .get("python_path")
        .and_then(|v| v.as_str())
        .unwrap_or("");
    let ver = val
        .get("paperforge_version")
        .and_then(|v| v.as_str())
        .unwrap_or("");
    let env_root = val
        .get("environment_root")
        .and_then(|v| v.as_str())
        .unwrap_or("");
    let valid = !py.is_empty()
        && !ver.is_empty()
        && !env_root.is_empty()
        && Path::new(py).is_absolute()
        && Path::new(env_root).is_absolute()
        && Path::new(py).is_file();
    json!({
        "status": if valid { "valid" } else { "invalid" },
        "path": ptr_path.to_string_lossy(),
        "python_path": if py.is_empty() { Value::Null } else { Value::String(py.to_string()) },
        "paperforge_version": if ver.is_empty() { Value::Null } else { Value::String(ver.to_string()) },
    })
}

fn build_collection_tree(conn: &Connection) -> Vec<Value> {
    let mut rows_vec: Vec<(String, i64)> = Vec::new();
    if let Ok(mut st) = conn.prepare(
        "SELECT collection_path, COUNT(*) as cnt FROM papers WHERE COALESCE(collection_path, '') != '' GROUP BY collection_path ORDER BY cnt DESC",
    ) {
        if let Ok(rows) = st.query_map([], |r| {
            Ok((r.get::<_, String>(0)?, r.get::<_, i64>(1).unwrap_or(0)))
        }) {
            for r in rows.flatten() {
                rows_vec.push(r);
            }
        }
    }

    struct TopCol {
        count: i64,
        sub: HashSet<String>,
    }
    let mut top: HashMap<String, TopCol> = HashMap::new();
    for (raw_path, cnt) in rows_vec {
        let branches: Vec<&str> = raw_path
            .split('|')
            .map(str::trim)
            .filter(|s| !s.is_empty())
            .collect();
        if branches.is_empty() {
            continue;
        }
        if branches.iter().any(|b| b.contains('/')) {
            let mut seen_roots: HashSet<String> = HashSet::new();
            for branch in branches {
                let segs: Vec<&str> = branch
                    .split('/')
                    .map(str::trim)
                    .filter(|s| !s.is_empty())
                    .collect();
                if segs.is_empty() {
                    continue;
                }
                let root = segs[0].to_string();
                let entry = top.entry(root.clone()).or_insert_with(|| TopCol {
                    count: 0,
                    sub: HashSet::new(),
                });
                if seen_roots.insert(root) {
                    entry.count += cnt;
                }
                if segs.len() > 1 {
                    entry.sub.insert(segs[1..].join("/"));
                }
            }
        } else {
            let root = branches[0].to_string();
            let entry = top.entry(root).or_insert_with(|| TopCol {
                count: 0,
                sub: HashSet::new(),
            });
            entry.count += cnt;
            if branches.len() > 1 {
                entry.sub.insert(branches[branches.len() - 1].to_string());
            }
        }
    }

    let mut list: Vec<(String, i64, Vec<String>)> = top
        .into_iter()
        .map(|(name, col)| {
            let mut subs: Vec<String> = col.sub.into_iter().collect();
            subs.sort();
            (name, col.count, subs)
        })
        .collect();
    list.sort_by(|a, b| b.1.cmp(&a.1).then_with(|| a.0.cmp(&b.0)));
    list.into_iter()
        .map(|(name, count, sub)| json!({ "name": name, "count": count, "sub": sub }))
        .collect()
}

fn scan_methodology_archive(engine_dir: &Path) -> Vec<Value> {
    let archive_dir = engine_dir.join("methodology").join("archive");
    if !archive_dir.is_dir() {
        return Vec::new();
    }
    let mut files: Vec<PathBuf> = fs::read_dir(&archive_dir)
        .ok()
        .into_iter()
        .flatten()
        .flatten()
        .map(|e| e.path())
        .filter(|p| p.is_file() && p.extension().and_then(|s| s.to_str()) == Some("md"))
        .collect();
    files.sort();

    let mut out = Vec::new();
    for path in files {
        let Ok(text) = fs::read_to_string(&path) else {
            continue;
        };
        let stem = path
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("")
            .to_string();
        let mut title = String::new();
        let mut description = String::new();
        let mut in_use_when = false;
        for line in text.lines() {
            let stripped = line.trim();
            if stripped.starts_with("# ") && title.is_empty() {
                title = stripped.trim_start_matches("# ").trim().to_string();
            } else if stripped.starts_with("## Use when") {
                in_use_when = true;
            } else if in_use_when && !stripped.is_empty() && !stripped.starts_with('#') {
                description = stripped.to_string();
                in_use_when = false;
            }
        }
        out.push(json!({
            "id": stem,
            "title": if title.is_empty() { stem } else { title },
            "description": if description.is_empty() { "(no description)".to_string() } else { description },
        }));
    }
    out
}

fn read_daemon_heartbeat(engine_dir: &Path) -> (bool, Vec<Value>, Option<String>, Vec<Value>) {
    let hb_path = engine_dir.join("indexes").join(".daemon-state.json");
    let Ok(raw) = fs::read_to_string(&hb_path) else {
        return (false, Vec::new(), None, Vec::new());
    };
    let Ok(val) = serde_json::from_str::<Value>(&raw) else {
        return (false, Vec::new(), None, Vec::new());
    };
    let pid = val.get("pid").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
    let alive = pid > 0 && is_pid_alive(pid, None);
    if !alive {
        return (false, Vec::new(), None, Vec::new());
    }
    let active_jobs = val
        .get("active_jobs")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();
    let exclusive_barrier = val
        .get("exclusive_barrier")
        .and_then(|v| v.as_str())
        .map(String::from);
    let recent_notices = val
        .get("recent_notices")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();
    (true, active_jobs, exclusive_barrier, recent_notices)
}

fn check_logs_writable(engine_dir: &Path, vault: &Path) -> bool {
    let logs_dir = engine_dir.join("logs");
    if let Ok(meta) = fs::metadata(&logs_dir) {
        return meta.is_dir() && !meta.permissions().readonly();
    }
    for cand in [engine_dir, vault] {
        if let Ok(meta) = fs::metadata(cand) {
            return meta.is_dir() && !meta.permissions().readonly();
        }
    }
    false
}

fn read_vector_status(vault: &Path, conn_opt: Option<&Connection>) -> (bool, bool, Value) {
    let settings_path = vault
        .join(".obsidian")
        .join("plugins")
        .join("paperforge")
        .join("data.json");
    let mut explicit_setting: Option<bool> = None;
    if let Ok(raw) = fs::read_to_string(settings_path) {
        if let Ok(val) = serde_json::from_str::<Value>(&raw) {
            explicit_setting = val
                .get("features")
                .and_then(|f| f.get("vector_db"))
                .and_then(|v| v.as_bool());
        }
    }
    if explicit_setting == Some(false) {
        return (false, false, json!({ "status": "disabled", "chunks": 0 }));
    }

    let Some(conn) = conn_opt else {
        let enabled = explicit_setting == Some(true);
        return (
            enabled,
            false,
            json!({ "status": if enabled { "not_built" } else { "disabled" }, "chunks": 0 }),
        );
    };

    let mut build_status = String::from("idle");
    let mut current: i64 = 0;
    let mut total: i64 = 0;
    let mut message = String::new();
    let mut identity_changed = false;
    if table_exists(conn, "build_state") {
        if let Ok(mut st) = conn.prepare("SELECT key, value FROM build_state") {
            if let Ok(rows) = st.query_map([], |r| {
                Ok((r.get::<_, String>(0)?, r.get::<_, String>(1)?))
            }) {
                for (k, v) in rows.flatten() {
                    let parsed = serde_json::from_str::<Value>(&v).unwrap_or(Value::String(v));
                    match k.as_str() {
                        "status" => {
                            if let Some(s) = parsed.as_str() {
                                build_status = s.to_string();
                            }
                        }
                        "current" => current = parsed.as_i64().unwrap_or(0),
                        "total" => total = parsed.as_i64().unwrap_or(0),
                        "message" => {
                            if let Some(s) = parsed.as_str() {
                                message = s.to_string();
                            }
                        }
                        "identity_changed" | "identity_mismatch" => {
                            identity_changed = parsed.as_bool().unwrap_or(false);
                        }
                        _ => {}
                    }
                }
            }
        }
    }

    let body_chunks: i64 = if table_exists(conn, "vec_body_meta") {
        conn.query_row("SELECT COUNT(*) FROM vec_body_meta", [], |r| r.get(0))
            .unwrap_or(0)
    } else {
        0
    };
    let obj_chunks: i64 = if table_exists(conn, "vec_objects_meta") {
        conn.query_row("SELECT COUNT(*) FROM vec_objects_meta", [], |r| r.get(0))
            .unwrap_or(0)
    } else {
        0
    };
    let chunks = body_chunks + obj_chunks;

    let enabled = explicit_setting == Some(true) || chunks > 0 || build_status != "idle";
    if !enabled {
        return (false, false, json!({ "status": "disabled", "chunks": 0 }));
    }

    let vec_tables_ok = (body_chunks == 0 || table_exists(conn, "vec_body"))
        && (obj_chunks == 0 || table_exists(conn, "vec_objects"));
    let ready = (build_status == "completed" || chunks > 0)
        && vec_tables_ok
        && !identity_changed
        && !matches!(
            build_status.as_str(),
            "running" | "failed" | "interrupted" | "stale" | "corrupted"
        );
    (
        true,
        ready,
        json!({
            "status": build_status,
            "current": current,
            "total": total,
            "message": message,
            "chunks": chunks,
        }),
    )
}

fn query_paper_brief(conn: &Connection, engine_dir: &Path, identifier: &str) -> Option<Value> {
    if !table_exists(conn, "papers") {
        return None;
    }
    let key_row = conn
        .query_row(
            "SELECT zotero_key, COALESCE(title,''), COALESCE(first_author,''), COALESCE(CAST(year AS TEXT),''), \
             COALESCE(journal,''), COALESCE(domain,''), COALESCE(ocr_status,'pending'), \
             COALESCE(deep_reading_status,'pending'), COALESCE(has_pdf, 0), COALESCE(main_note_path,'') \
             FROM papers WHERE zotero_key = ?1 OR citation_key = ?1 OR doi = ?1 LIMIT 1",
            [identifier],
            |r| {
                Ok((
                    r.get::<_, String>(0)?,
                    r.get::<_, String>(1)?,
                    r.get::<_, String>(2)?,
                    r.get::<_, String>(3)?,
                    r.get::<_, String>(4)?,
                    r.get::<_, String>(5)?,
                    r.get::<_, String>(6)?,
                    r.get::<_, String>(7)?,
                    r.get::<_, i64>(8).unwrap_or(0) != 0,
                    r.get::<_, String>(9)?,
                ))
            },
        )
        .ok()?;

    let (zkey, title, first_author, year, journal, domain, ocr_status, deep_reading_status, has_pdf, mut main_note_path) = key_row;
    if main_note_path.is_empty() && table_exists(conn, "workspace_registry") {
        if let Ok(rel) = conn.query_row(
            "SELECT COALESCE(main_note_relpath,'') FROM workspace_registry WHERE zotero_key = ?1 LIMIT 1",
            [&zkey],
            |r| r.get::<_, String>(0),
        ) {
            let norm = rel.replace('\\', "/");
            if !norm.is_empty() && engine_dir.parent().map_or(true, |v| v.join(&norm).is_file()) {
                main_note_path = norm;
            }
        }
    }

    let ft_path = engine_dir.join("ocr").join(&zkey).join("fulltext.md");
    let blocks_path = engine_dir
        .join("ocr")
        .join(&zkey)
        .join("structure")
        .join("blocks.structured.jsonl");
    let fulltext_ready = ft_path.is_file() || blocks_path.is_file();

    let mut user_ann_count: i64 = 0;
    let mut user_question_count: i64 = 0;
    let mut agent_ann_count: i64 = 0;
    let mut agent_lenses: Vec<String> = Vec::new();
    if table_exists(conn, "paper_annotations") {
        if let Ok((u, uq, a)) = conn.query_row(
            "SELECT \
             COALESCE(SUM(CASE WHEN COALESCE(author,'user') != 'agent' THEN 1 ELSE 0 END), 0), \
             COALESCE(SUM(CASE WHEN COALESCE(author,'user') != 'agent' AND intent = 'question' THEN 1 ELSE 0 END), 0), \
             COALESCE(SUM(CASE WHEN COALESCE(author,'user') = 'agent' THEN 1 ELSE 0 END), 0) \
             FROM paper_annotations WHERE paper_id = ?1",
            [&zkey],
            |r| Ok((r.get::<_, i64>(0)?, r.get::<_, i64>(1)?, r.get::<_, i64>(2)?)),
        ) {
            user_ann_count = u;
            user_question_count = uq;
            agent_ann_count = a;
        }
        if let Ok(mut st) = conn.prepare(
            "SELECT DISTINCT COALESCE(lens,'') FROM paper_annotations WHERE paper_id = ?1 AND COALESCE(author,'user') = 'agent' AND COALESCE(lens,'') != '' ORDER BY lens",
        ) {
            if let Ok(rows) = st.query_map([&zkey], |r| r.get::<_, String>(0)) {
                agent_lenses = rows.flatten().collect();
            }
        }
    }

    let mut memory_facets: Vec<Value> = Vec::new();
    if table_exists(conn, "paper_memory_cards") {
        if let Ok(mut st) = conn.prepare(
            "SELECT facet, COALESCE(updated_at,'') FROM paper_memory_cards WHERE zotero_key = ?1 ORDER BY facet",
        ) {
            if let Ok(rows) = st.query_map([&zkey], |r| {
                Ok(json!({ "facet": r.get::<_, String>(0)?, "updated_at": r.get::<_, String>(1)? }))
            }) {
                memory_facets = rows.flatten().collect();
            }
        }
    }

    Some(json!({
        "zotero_key": zkey,
        "title": title,
        "first_author": first_author,
        "year": year,
        "journal": journal,
        "domain": domain,
        "ocr_status": ocr_status,
        "deep_reading_status": deep_reading_status,
        "has_pdf": has_pdf,
        "main_note_path": main_note_path,
        "fulltext_ready": fulltext_ready,
        "user_ann_count": user_ann_count,
        "user_question_count": user_question_count,
        "agent_ann_count": agent_ann_count,
        "agent_lenses": agent_lenses,
        "memory_facets": memory_facets,
    }))
}

#[derive(Clone)]
struct RawHint {
    rank: u8,
    severity: &'static str,
    code: String,
    message: String,
    repair_command: Option<String>,
}

fn push_hint(
    hints: &mut Vec<RawHint>,
    rank: u8,
    severity: &'static str,
    code: impl Into<String>,
    message: impl Into<String>,
    repair_command: Option<String>,
) {
    hints.push(RawHint {
        rank,
        severity,
        code: code.into(),
        message: message.into(),
        repair_command,
    });
}

/// Build the compact, authoritative Rust state-machine handoff (`agent-brief`).
pub fn build_agent_brief(vault: &Path, paper_key: Option<&str>) -> Value {
    let clean_vault = strip_verbatim_prefix(&fs::canonicalize(vault).unwrap_or_else(|_| vault.to_path_buf()));
    let runtime_ptr = read_runtime_pointer_info();
    let py_exe = NativeControlDaemon::resolve_python_exe();
    let python_available = py_exe.is_some();

    let mut hints: Vec<RawHint> = Vec::new();
    let mut blocked_actions: Map<String, Value> = Map::new();

    let cfg_res = load_canonical_config(&clean_vault);
    let (config_ok, paths_map, engine_dir) = match cfg_res {
        Ok(loaded) => {
            let paths = resolve_vault_paths(&clean_vault, &loaded.doc);
            let eng = paths
                .get("paperforge")
                .and_then(|v| v.as_str())
                .map(PathBuf::from)
                .unwrap_or_else(|| resolve_engine_dir(&clean_vault));
            (true, Value::Object(paths), eng)
        }
        Err(ref issue) => {
            let repair = match issue {
                ConfigIssue::NotFound(_) => "paperforge config init",
                ConfigIssue::MigrationRequired(_) => "paperforge config migrate --dry-run",
                _ => "paperforge doctor",
            };
            blocked_actions.insert(
                "all".into(),
                json!(format!("Vault config issue: {}", issue.code())),
            );
            push_hint(
                &mut hints,
                0,
                "blocker",
                "config.issue",
                format!(
                    "paperforge.json 状态异常 ({})，请先修复后再操作。",
                    issue.code()
                ),
                Some(repair.to_string()),
            );
            (
                false,
                json!({ "vault": clean_vault.to_string_lossy() }),
                resolve_engine_dir(&clean_vault),
            )
        }
    };

    let (seq, updated_at) = read_state_seq(&clean_vault);
    let (daemon_alive, active_jobs, exclusive_barrier, recent_notices) =
        read_daemon_heartbeat(&engine_dir);

    let db_path = engine_dir.join("indexes").join("paperforge.db");
    let db_file_exists = db_path.is_file();
    let raw_conn = open_readonly_db(&db_path);
    let db_probe_ok = raw_conn.as_ref().is_some_and(|c| {
        c.query_row("SELECT COUNT(*) FROM sqlite_master", [], |r| r.get::<_, i64>(0))
            .is_ok()
    });
    let db_corrupt = db_file_exists && !db_probe_ok;
    let conn_opt = if db_probe_ok { raw_conn } else { None };
    let db_exists = db_probe_ok;

    let mut paper_count: i64 = 0;
    let mut ocr_failed_count: i64 = 0;
    let mut domain_counts: Map<String, Value> = Map::new();
    let mut lifecycle_counts: Map<String, Value> = Map::new();
    let mut ocr_counts: Map<String, Value> = Map::new();
    let mut deep_reading_counts: Map<String, Value> = Map::new();
    let mut collections: Vec<Value> = Vec::new();
    let mut paper_brief: Option<Value> = None;

    if let Some(ref conn) = conn_opt {
        if table_exists(conn, "papers") {
            paper_count = conn
                .query_row("SELECT COUNT(*) FROM papers", [], |r| r.get(0))
                .unwrap_or(0);
            ocr_failed_count = conn
                .query_row(
                    "SELECT COUNT(*) FROM papers WHERE ocr_status IN ('failed', 'done_incomplete')",
                    [],
                    |r| r.get(0),
                )
                .unwrap_or(0);

            let count_group = |col: &str| -> Map<String, Value> {
                let mut m = Map::new();
                let sql = format!("SELECT COALESCE({col}, ''), COUNT(*) FROM papers GROUP BY {col} ORDER BY COUNT(*) DESC");
                if let Ok(mut st) = conn.prepare(&sql) {
                    if let Ok(rows) = st.query_map([], |r| {
                        Ok((r.get::<_, String>(0)?, r.get::<_, i64>(1).unwrap_or(0)))
                    }) {
                        for (k, c) in rows.flatten() {
                            m.insert(k, json!(c));
                        }
                    }
                }
                m
            };
            domain_counts = count_group("domain");
            lifecycle_counts = count_group("lifecycle");
            ocr_counts = count_group("ocr_status");
            deep_reading_counts = count_group("deep_reading_status");
            collections = build_collection_tree(conn);
        }

        if let Some(pk) = paper_key.map(str::trim).filter(|s| !s.is_empty()) {
            paper_brief = query_paper_brief(conn, &engine_dir, pk);
        }
    }

    let logs_writable = check_logs_writable(&engine_dir, &clean_vault);
    let (vector_enabled, vector_ready, vector_info) =
        read_vector_status(&clean_vault, conn_opt.as_ref());

    let safe_read = config_ok && db_exists;
    let safe_write = config_ok
        && db_exists
        && python_available
        && logs_writable
        && exclusive_barrier.is_none();
    let fts_search = safe_read;

    if db_corrupt {
        blocked_actions.insert(
            "read_and_search".into(),
            json!("paperforge.db is corrupt. Run `paperforge memory build` or `paperforge engine rebuild-db` to recover."),
        );
        push_hint(
            &mut hints,
            0,
            "blocker",
            "db.corrupt",
            "paperforge.db 索引数据库已损坏（file is not a database），请先重建后再检索或读取。",
            Some("paperforge memory build".to_string()),
        );
    } else if config_ok && !db_exists {
        blocked_actions.insert(
            "read_and_search".into(),
            json!("paperforge.db not found. Run `paperforge memory build` first."),
        );
        push_hint(
            &mut hints,
            0,
            "blocker",
            "db.missing",
            "尚未生成 paperforge.db 记忆索引库，无法检索或读取论文。",
            Some("paperforge memory build".to_string()),
        );
    }

    if config_ok && !logs_writable {
        blocked_actions.insert(
            "write_log".into(),
            json!("Engine logs directory is read-only or not writable."),
        );
        push_hint(
            &mut hints,
            1,
            "warn",
            "logs.not_writable",
            "引擎 logs 目录不可写，写操作已暂时锁定，请检查目录权限。",
            None,
        );
    }

    if let Some(ref barrier) = exclusive_barrier {
        blocked_actions.insert(
            "write_operations".into(),
            json!(format!("Vault exclusive upgrade barrier active: {barrier}")),
        );
        push_hint(
            &mut hints,
            0,
            "blocker",
            "barrier.exclusive_active",
            format!("Vault 正在执行独占升级切换 ({barrier})，写操作暂时锁定。"),
            None,
        );
    }

    if !python_available {
        for act in ["ocr", "sync", "embed", "annotate_batch", "memory_refine", "write_log"] {
            blocked_actions.insert(
                act.into(),
                json!("Python compute worker not installed; native FTS5 read/search still works."),
            );
        }
        push_hint(
            &mut hints,
            1,
            "warn",
            "runtime.python_missing",
            "Python 计算引擎尚未安装：原生搜索与库查询可用，但 OCR / 同步 / 批注 / 记忆卡写入不可用。",
            Some("paperforge-daemon install-runtime".to_string()),
        );
    }

    for job in &active_jobs {
        let kind = job.get("kind").and_then(|v| v.as_str()).unwrap_or("");
        let cur = job.get("current").and_then(|v| v.as_i64()).unwrap_or(0);
        let tot = job.get("total").and_then(|v| v.as_i64()).unwrap_or(0);
        let item_id = job.get("item_id").and_then(|v| v.as_str()).unwrap_or("");
        if kind == "ocr" {
            blocked_actions.insert(
                "ocr".into(),
                json!(format!("OCR job already running ({cur}/{tot}).")),
            );
            push_hint(
                &mut hints,
                1,
                "warn",
                "job.ocr.running",
                format!("后台正在执行 OCR ({cur}/{tot}，当前 {item_id})，请勿重复触发 OCR 或对未完成论文下定论。"),
                None,
            );
        } else if kind == "sync" {
            blocked_actions.insert("sync".into(), json!("Sync job already running."));
            push_hint(
                &mut hints,
                1,
                "warn",
                "job.sync.running",
                "后台正在同步 Zotero 文献库，请等待完成后再做全库盘点。",
                None,
            );
        } else if kind == "embed" {
            blocked_actions.insert(
                "embed".into(),
                json!(format!("Embedding build running ({cur}/{tot}).")),
            );
            push_hint(
                &mut hints,
                1,
                "warn",
                "job.embed.running",
                format!("后台正在构建向量索引 ({cur}/{tot})，检索请优先使用 FTS5/关键词模式。"),
                None,
            );
        }
    }

    if vector_enabled && !vector_ready {
        let vec_st = vector_info
            .get("status")
            .and_then(|v| v.as_str())
            .unwrap_or("not_built");
        let code = if vec_st == "running" {
            "vector.building"
        } else {
            "vector.not_ready"
        };
        push_hint(
            &mut hints,
            2,
            "tip",
            code,
            format!("向量索引未就绪 (status={vec_st})，语义检索请使用 retrieve --deep 或 FTS5 search 降级路径。"),
            None,
        );
    }

    if ocr_failed_count > 0 {
        push_hint(
            &mut hints,
            2,
            "tip",
            "library.ocr_failed",
            format!("库中有 {ocr_failed_count} 篇论文 OCR 失败或不完整，涉及这些文献时请提醒用户诊断。"),
            None,
        );
    }

    if let Some(ref pb) = paper_brief {
        let ocr_st = pb
            .get("ocr_status")
            .and_then(|v| v.as_str())
            .unwrap_or("pending");
        let ft_ready = pb
            .get("fulltext_ready")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);
        let has_pdf = pb
            .get("has_pdf")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);
        if !has_pdf {
            blocked_actions.insert(
                "annotate_batch".into(),
                json!("Paper has no bound PDF (has_pdf=false). Sync or attach a PDF first."),
            );
            push_hint(
                &mut hints,
                1,
                "warn",
                "paper.no_pdf",
                "目标论文尚未绑定 PDF，无法读取原文或写入 PDF 批注。",
                None,
            );
        } else if !ft_ready && ocr_st != "done" {
            push_hint(
                &mut hints,
                3,
                "tip",
                "paper.native_pdf_mode",
                format!(
                    "目标论文尚未完成 OCR (status={ocr_st})，已启用原生 PDF 模式：可直接通过 paperforge_read_paper 逐页阅读，并直接调用 paperforge_annotate_batch 批注；如需结构化全文也可通过 paperforge_job 排队 OCR。"
                ),
                None,
            );
        }
        let uq = pb
            .get("user_question_count")
            .and_then(|v| v.as_i64())
            .unwrap_or(0);
        if uq > 0 {
            push_hint(
                &mut hints,
                2,
                "tip",
                "paper.has_user_questions",
                format!("目标论文存在 {uq} 条用户提问型高亮，请优先回原文核实并回应这些段落。"),
                None,
            );
        }
        let ac = pb
            .get("agent_ann_count")
            .and_then(|v| v.as_i64())
            .unwrap_or(0);
        if ac > 0 {
            let lenses = pb
                .get("agent_lenses")
                .and_then(|v| v.as_array())
                .map(|arr| {
                    arr.iter()
                        .filter_map(|v| v.as_str())
                        .collect::<Vec<_>>()
                        .join(",")
                })
                .unwrap_or_default();
            push_hint(
                &mut hints,
                2,
                "tip",
                "paper.has_existing_ai_marks",
                format!("目标论文已有 {ac} 条 AI 批注 (lenses={lenses})，重跑同一视角时可传 replace_lens=true 避免堆叠。"),
                None,
            );
        }
    }

    // Check if any registered copy-mode Agent Skill lags the machine Skill Hub
    if let Some(pf_home) = crate::mcp::paperforge_home_dir() {
        let meta_path = pf_home.join("skills").join(".skill-meta.json");
        let reg_path = pf_home.join("agent-installs.json");
        if let (Ok(meta_raw), Ok(reg_raw)) =
            (fs::read_to_string(meta_path), fs::read_to_string(reg_path))
        {
            if let (Ok(meta_val), Ok(reg_val)) = (
                serde_json::from_str::<Value>(&meta_raw),
                serde_json::from_str::<Value>(&reg_raw),
            ) {
                let hub_digest = meta_val.get("digest").and_then(|v| v.as_str()).unwrap_or("");
                let stale_count = reg_val
                    .get("installs")
                    .and_then(|v| v.as_array())
                    .map(|arr| {
                        arr.iter()
                            .filter(|item| {
                                item.get("link_mode").and_then(|v| v.as_str()) != Some("link")
                                    && item
                                        .get("last_synced_digest")
                                        .and_then(|v| v.as_str())
                                        .is_some_and(|d| !hub_digest.is_empty() && d != hub_digest)
                            })
                            .count()
                    })
                    .unwrap_or(0);
                if stale_count > 0 {
                    push_hint(
                        &mut hints,
                        2,
                        "tip",
                        "skill.update_available",
                        format!("检测到 {stale_count} 个已登记的 Agent Skill 副本可自动同步到最新版。"),
                        Some("paperforge-daemon skill-sync-all --json".to_string()),
                    );
                }
            }
        }
    }

    hints.sort_by(|a, b| a.rank.cmp(&b.rank).then_with(|| a.code.cmp(&b.code)));
    hints.truncate(5);
    let hint_values: Vec<Value> = hints
        .into_iter()
        .map(|h| {
            let mut obj = Map::new();
            obj.insert("severity".into(), json!(h.severity));
            obj.insert("code".into(), json!(h.code));
            obj.insert("message".into(), json!(h.message));
            if let Some(rc) = h.repair_command {
                obj.insert("repair_command".into(), json!(rc));
            }
            Value::Object(obj)
        })
        .collect();

    let methods = scan_methodology_archive(&engine_dir);

    let mut data = Map::new();
    data.insert(
        "vault".into(),
        json!({
            "root": clean_vault.to_string_lossy(),
            "seq": seq,
            "updated_at": updated_at,
            "paths": paths_map,
        }),
    );
    data.insert(
        "runtime".into(),
        json!({
            "daemon_version": PF_VERSION,
            "daemon_alive": daemon_alive,
            "python_worker_available": python_available,
            "python_exe": py_exe.map(|p| Value::String(p.to_string_lossy().into_owned())).unwrap_or(Value::Null),
            "pointer": runtime_ptr,
            "active_jobs": active_jobs,
            "exclusive_barrier": exclusive_barrier,
            "recent_notices": recent_notices,
        }),
    );
    data.insert(
        "library".into(),
        json!({
            "paper_count": paper_count,
            "ocr_failed_count": ocr_failed_count,
            "domain_counts": domain_counts,
            "lifecycle_counts": lifecycle_counts,
            "ocr_counts": ocr_counts,
            "deep_reading_counts": deep_reading_counts,
            "collections": collections,
        }),
    );
    data.insert("methodology_index".into(), json!(methods));
    data.insert(
        "capabilities".into(),
        json!({
            "safe_read": safe_read,
            "safe_write": safe_write,
            "db_corrupt": db_corrupt,
            "fts_search": fts_search,
            "vector_enabled": vector_enabled,
            "vector_retrieve": vector_ready,
            "vector_info": vector_info,
            "blocked_actions": blocked_actions,
        }),
    );
    data.insert("hints".into(), json!(hint_values));
    if let Some(pb) = paper_brief {
        data.insert("paper".into(), pb);
    }

    pf_ok("agent-brief", Value::Object(data))
}

/// Filtered, paginated Base snapshot for token-safe Agent queries (`paperforge_library_query`).
pub fn query_library_filtered(vault: &Path, args: &Value) -> Value {
    let (_rc, out_str, _err) = handle_base_snapshot(vault);
    let Ok(snap_env) = serde_json::from_str::<Value>(&out_str) else {
        return pf_err(
            "library-query",
            "INTERNAL_ERROR",
            "Failed to parse base-snapshot output",
            json!({}),
            &[],
        );
    };
    if snap_env.get("ok").and_then(|v| v.as_bool()) != Some(true) {
        return snap_env;
    }

    let snap_data = snap_env.get("data").cloned().unwrap_or(Value::Null);
    let seq = snap_data.get("seq").and_then(|v| v.as_i64()).unwrap_or(0);
    let state_authority = snap_data
        .get("state_authority")
        .and_then(|v| v.as_str())
        .unwrap_or("sqlite");

    let empty_map = Map::new();
    let rows_obj = snap_data
        .get("rows")
        .and_then(|v| v.as_object())
        .unwrap_or(&empty_map);
    let total_in_library = rows_obj.len();

    let opt_str = |k: &str| -> Option<String> {
        args.get(k)
            .and_then(|v| v.as_str())
            .map(str::trim)
            .filter(|s| !s.is_empty())
            .map(str::to_ascii_lowercase)
    };
    let domain_f = opt_str("domain");
    let col_f = opt_str("collection");
    let ocr_f = opt_str("ocr_status");
    let deep_f = opt_str("deep_reading_status");
    let query_f = opt_str("query");
    let diag_f = args.get("needs_diagnostic").and_then(|v| v.as_bool());
    let has_pdf_f = args.get("has_pdf").and_then(|v| v.as_bool());

    let limit = args
        .get("limit")
        .and_then(|v| v.as_u64())
        .unwrap_or(30)
        .clamp(1, 100) as usize;
    let offset = args.get("offset").and_then(|v| v.as_u64()).unwrap_or(0) as usize;

    let mut matched: Vec<&Map<String, Value>> = Vec::new();
    for val in rows_obj.values() {
        let Some(row) = val.as_object() else {
            continue;
        };
        if let Some(ref d) = domain_f {
            let rv = row
                .get("domain")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_ascii_lowercase();
            if rv != *d {
                continue;
            }
        }
        if let Some(ref c) = col_f {
            let cols = row
                .get("collections")
                .and_then(|v| v.as_array())
                .map(|arr| {
                    arr.iter().any(|x| {
                        x.as_str()
                            .unwrap_or("")
                            .to_ascii_lowercase()
                            .contains(c.as_str())
                    })
                })
                .unwrap_or(false);
            if !cols {
                continue;
            }
        }
        if let Some(ref o) = ocr_f {
            let rv = row
                .get("ocr_status")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_ascii_lowercase();
            if rv != *o {
                continue;
            }
        }
        if let Some(ref dp) = deep_f {
            let rv = row
                .get("deep_reading_status")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_ascii_lowercase();
            if rv != *dp {
                continue;
            }
        }
        if let Some(nd) = diag_f {
            let rv = row
                .get("needs_diagnostic")
                .and_then(|v| v.as_bool())
                .unwrap_or(false);
            if rv != nd {
                continue;
            }
        }
        if let Some(hp) = has_pdf_f {
            let rv = row.get("has_pdf").and_then(|v| v.as_bool()).unwrap_or(false);
            if rv != hp {
                continue;
            }
        }
        if let Some(ref q) = query_f {
            let hay = ["zotero_key", "title", "first_author", "journal", "domain"]
                .iter()
                .filter_map(|f| row.get(*f).and_then(|v| v.as_str()))
                .collect::<Vec<_>>()
                .join(" ")
                .to_ascii_lowercase();
            if !hay.contains(q.as_str()) {
                continue;
            }
        }
        matched.push(row);
    }

    // Deterministic sort: year descending, then zotero_key ascending
    matched.sort_by(|a, b| {
        let ya = a.get("year").and_then(|v| v.as_str()).unwrap_or("");
        let yb = b.get("year").and_then(|v| v.as_str()).unwrap_or("");
        yb.cmp(ya).then_with(|| {
            let ka = a.get("zotero_key").and_then(|v| v.as_str()).unwrap_or("");
            let kb = b.get("zotero_key").and_then(|v| v.as_str()).unwrap_or("");
            ka.cmp(kb)
        })
    });

    let total_matched = matched.len();
    let end = (offset + limit).min(total_matched);
    let slice = if offset < total_matched {
        &matched[offset..end]
    } else {
        &[]
    };
    let truncated = end < total_matched;

    let items: Vec<Value> = slice
        .iter()
        .map(|row| {
            let mut compact = BTreeMap::new();
            for k in [
                "zotero_key",
                "title",
                "first_author",
                "year",
                "journal",
                "domain",
                "ocr_status",
                "deep_reading_status",
                "has_pdf",
                "user_ann_count",
                "agent_ann_count",
                "memory_facet_count",
                "needs_diagnostic",
            ] {
                if let Some(v) = row.get(k) {
                    compact.insert(k, v.clone());
                }
            }
            json!(compact)
        })
        .collect();

    pf_ok(
        "library-query",
        json!({
            "seq": seq,
            "state_authority": state_authority,
            "total_in_library": total_in_library,
            "total_matched": total_matched,
            "offset": offset,
            "limit": limit,
            "truncated": truncated,
            "items": items,
        }),
    )
}
