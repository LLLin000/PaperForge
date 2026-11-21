//! `paperforge-daemon` — Cross-platform native Rust control & query sidecar.
//!
//! Speaks the exact `paperforge daemon --stdio` JSON-RPC + duplex NDJSON push
//! wire protocol so Obsidian connects in `< 5ms` at `~4-6 MB` RSS with ZERO
//! local Rust or Python prerequisite for browsing, Base tables, FTS5 search,
//! config management, and veteran upgrade detection, while delegating heavy
//! OCR / Embedding / Sync workers to Python on demand.

mod config_ops;
mod platform;
mod query_ops;
mod supervisor;

use config_ops::{try_handle_config_cli, PF_VERSION};
use query_ops::{
    handle_base_snapshot, handle_zero_python_upgrade_plan, try_handle_search_cli,
};
use serde_json::{json, Value};
use std::env;
use std::io::{self, BufRead, Write};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};
use supervisor::{NativeControlDaemon, PushSink};

fn json_ok_resp(id: Value, payload: Value) -> Value {
    json!({
        "id": id,
        "ok": true,
        "exit_code": 0,
        "stdout": payload.to_string(),
        "stderr": "",
    })
}

fn json_err_resp(id: Value, message: &str, code: i32) -> Value {
    json!({
        "id": id,
        "ok": false,
        "exit_code": code,
        "stdout": "",
        "stderr": message,
    })
}

fn execute_request(daemon: &NativeControlDaemon, req: &Value) -> (Value, bool) {
    let id = req.get("id").cloned().unwrap_or(Value::Null);
    let op = req
        .get("op")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .trim()
        .to_ascii_lowercase();
    let vault_path = req
        .get("vault")
        .and_then(|v| v.as_str())
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(PathBuf::from);

    match op.as_str() {
        "ping" => {
            return (
                json!({ "id": id, "ok": true, "exit_code": 0, "stdout": "pong", "stderr": "" }),
                false,
            )
        }
        "shutdown" => {
            daemon.cancel_all_jobs(1000);
            return (
                json!({ "id": id, "ok": true, "exit_code": 0, "stdout": "", "stderr": "" }),
                true,
            );
        }
        "daemon.health" => return (json_ok_resp(id, daemon.health(vault_path.as_deref())), false),
        "daemon.trim" => {
            let idle = req
                .get("idle_seconds")
                .and_then(|v| v.as_f64())
                .unwrap_or(120.0);
            return (json_ok_resp(id, daemon.trim_idle_memory(idle)), false);
        }
        "engine.status" => {
            let payload = if let Some(ref vp) = vault_path {
                let c = daemon.get_or_refresh_vault(vp);
                json!({
                    "vault": c.vault_key,
                    "seq": c.last_seq,
                    "workspace_count": c.workspace_map.len(),
                    "ocr_salvage_counts": c.ocr_salvage_counts,
                    "cache_hits": c.hits,
                    "cache_misses": c.misses,
                })
            } else {
                let h = daemon.health(None);
                json!({ "cached_vaults": h["cached_vaults"] })
            };
            return (json_ok_resp(id, payload), false);
        }
        "engine.resolve_key" => {
            let key = req
                .get("key")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .trim();
            let Some(ref vp) = vault_path else {
                return (json_err_resp(id, "vault and key required", 2), false);
            };
            if key.is_empty() {
                return (json_err_resp(id, "vault and key required", 2), false);
            }
            let c = daemon.get_or_refresh_vault(vp);
            let rel = c.workspace_map.get(key).cloned();
            return (
                json_ok_resp(
                    id,
                    json!({ "key": key, "workspace_relpath": rel, "seq": c.last_seq }),
                ),
                false,
            );
        }
        "engine.invalidate" => {
            let cleared = daemon.invalidate_vault(vault_path.as_deref());
            return (json_ok_resp(id, json!({ "cleared": cleared })), false);
        }
        "job.submit" => {
            let kind = req
                .get("kind")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .trim();
            let Some(ref vp) = vault_path else {
                return (json_err_resp(id, "vault and kind required", 2), false);
            };
            if kind.is_empty() {
                return (json_err_resp(id, "vault and kind required", 2), false);
            }
            let custom_argv = req.get("argv").and_then(|v| v.as_array()).map(|arr| {
                arr.iter()
                    .filter_map(|x| x.as_str().map(String::from))
                    .collect::<Vec<_>>()
            });
            let prio = req
                .get("priority_key")
                .and_then(|v| v.as_str())
                .map(str::trim)
                .filter(|s| !s.is_empty())
                .map(String::from);
            let backfill = req
                .get("backfill_ocr")
                .and_then(|v| v.as_bool())
                .unwrap_or(false);
            return (
                json_ok_resp(
                    id,
                    daemon.submit_job(vp, kind, custom_argv, prio, backfill),
                ),
                false,
            );
        }
        "job.list" => {
            let inc_recent = req
                .get("include_recent")
                .and_then(|v| v.as_bool())
                .unwrap_or(true);
            return (
                json_ok_resp(id, daemon.list_jobs(vault_path.as_deref(), inc_recent)),
                false,
            );
        }
        "job.cancel" => {
            let jid = req
                .get("job_id")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .trim();
            if jid.is_empty() {
                return (json_err_resp(id, "job_id required", 2), false);
            }
            let wait = req.get("wait").and_then(|v| v.as_bool()).unwrap_or(false);
            return (json_ok_resp(id, daemon.cancel_job(jid, 3000, wait)), false);
        }
        "notice.list" => {
            let inc = req
                .get("include_acked")
                .and_then(|v| v.as_bool())
                .unwrap_or(false);
            return (
                json_ok_resp(
                    id,
                    json!({ "notices": daemon.list_notices(vault_path.as_deref(), inc) }),
                ),
                false,
            );
        }
        "notice.ack" => {
            let nid = req
                .get("notice_id")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .trim();
            return (
                json_ok_resp(id, json!({ "acked": daemon.ack_notice(nid) })),
                false,
            );
        }
        "notice.push" => {
            let ntc = daemon.push_notice(
                req.get("level").and_then(|v| v.as_str()).unwrap_or("info"),
                req.get("code").and_then(|v| v.as_str()).unwrap_or("custom"),
                req.get("title").and_then(|v| v.as_str()).unwrap_or(""),
                req.get("detail").and_then(|v| v.as_str()).unwrap_or(""),
                vault_path.as_deref(),
            );
            return (json_ok_resp(id, ntc), false);
        }
        _ => {}
    }

    // Standard `argv` CLI multiplexing
    let Some(arr) = req.get("argv").and_then(|v| v.as_array()) else {
        return (
            json_err_resp(id, "daemon request requires string list 'argv'", 2),
            false,
        );
    };
    let mut argv = Vec::with_capacity(arr.len());
    for item in arr {
        let Some(s) = item.as_str() else {
            return (
                json_err_resp(id, "daemon request requires string list 'argv'", 2),
                false,
            );
        };
        argv.push(s.to_string());
    }
    if argv.first().map(|s| s.as_str()) == Some("daemon") {
        return (
            json_err_resp(id, "Nested daemon invocation is not supported", 2),
            false,
        );
    }

    // 1. Instant `--version`
    if argv.len() == 1 && argv[0] == "--version" {
        return (
            json!({
                "id": id,
                "exit_code": 0,
                "stdout": format!("paperforge {PF_VERSION}\n"),
                "stderr": "",
            }),
            false,
        );
    }

    let python_available = NativeControlDaemon::resolve_python_exe().is_some();

    // 2. Native `< 2ms` fast-paths when vault is supplied
    if let Some(ref vp) = vault_path {
        if let Some((rc, out, err)) = try_handle_config_cli(vp, &argv) {
            return (
                json!({ "id": id, "exit_code": rc, "stdout": out, "stderr": err }),
                false,
            );
        }
        if argv.first().map(|s| s.as_str()) == Some("memory-card")
            && argv.get(1).map(|s| s.as_str()) == Some("base-snapshot")
            && argv.iter().any(|a| a == "--json")
        {
            let (rc, out, err) = handle_base_snapshot(vp);
            return (
                json!({ "id": id, "exit_code": rc, "stdout": out, "stderr": err }),
                false,
            );
        }
        if let Some((rc, out, err)) = try_handle_search_cli(vp, &argv, python_available) {
            return (
                json!({ "id": id, "exit_code": rc, "stdout": out, "stderr": err }),
                false,
            );
        }
        if !python_available
            && argv.first().map(|s| s.as_str()) == Some("upgrade")
            && argv.iter().any(|a| a == "--plan")
            && argv.iter().any(|a| a == "--json")
        {
            let (rc, out, err) = handle_zero_python_upgrade_plan(vp);
            return (
                json!({ "id": id, "exit_code": rc, "stdout": out, "stderr": err }),
                false,
            );
        }
    }

    // 3. On-demand delegation to Python worker runtime
    let stdin_opt = req.get("stdin").and_then(|v| v.as_str());
    let (rc, out, err) = daemon.delegate_to_python(vault_path.as_deref(), &argv, stdin_opt);
    (
        json!({ "id": id, "exit_code": rc, "stdout": out, "stderr": err }),
        false,
    )
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    let mut idle_timeout_secs: u64 = 300;
    let mut parent_pid: Option<u32> = env::var("PAPERFORGE_PARENT_PID")
        .ok()
        .and_then(|s| s.trim().parse::<u32>().ok());

    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--version" | "-V" => {
                println!("paperforge-daemon {PF_VERSION}");
                return;
            }
            "--stdio" => {}
            "--idle-timeout" => {
                i += 1;
                if let Some(val) = args.get(i).and_then(|s| s.parse::<u64>().ok()) {
                    idle_timeout_secs = val;
                }
            }
            "--parent-pid" => {
                i += 1;
                if let Some(val) = args.get(i).and_then(|s| s.parse::<u32>().ok()) {
                    parent_pid = Some(val);
                }
            }
            _ => {}
        }
        i += 1;
    }

    let push_enabled = env::var("PAPERFORGE_DAEMON_PUSH")
        .map(|v| matches!(v.trim().to_ascii_lowercase().as_str(), "1" | "true" | "yes"))
        .unwrap_or(false);

    let stdout_lock: Arc<Mutex<io::Stdout>> = Arc::new(Mutex::new(io::stdout()));
    let write_frame = {
        let out_ref = stdout_lock.clone();
        move |frame: Value| {
            if let Ok(line) = serde_json::to_string(&frame) {
                if let Ok(mut guard) = out_ref.lock() {
                    let _ = writeln!(guard, "{line}");
                    let _ = guard.flush();
                }
            }
        }
    };

    let push_sink: Option<PushSink> = if push_enabled {
        let wf = write_frame.clone();
        Some(Arc::new(wf))
    } else {
        None
    };

    let daemon = NativeControlDaemon::new(parent_pid, push_sink);
    let busy = Arc::new(AtomicBool::new(false));
    let stop = Arc::new(AtomicBool::new(false));
    let start_instant = Instant::now();
    let last_activity_ms = Arc::new(AtomicU64::new(0));

    if idle_timeout_secs > 0 || parent_pid.is_some() {
        let d_watch = daemon.clone();
        let b_watch = busy.clone();
        let s_watch = stop.clone();
        let la_watch = last_activity_ms.clone();
        thread::spawn(move || {
            while !s_watch.load(Ordering::Relaxed) {
                thread::sleep(Duration::from_millis(1500));
                if s_watch.load(Ordering::Relaxed) {
                    return;
                }
                if !d_watch.check_parent_alive() {
                    d_watch.cancel_all_jobs(1000);
                    std::process::exit(0);
                }
                let is_busy = b_watch.load(Ordering::Relaxed) || d_watch.has_active_jobs();
                if !is_busy {
                    let now_ms = start_instant.elapsed().as_millis() as u64;
                    let idle_secs =
                        now_ms.saturating_sub(la_watch.load(Ordering::Relaxed)) as f64 / 1000.0;
                    let _ = d_watch.trim_idle_memory(idle_secs);
                    if idle_timeout_secs > 0 && idle_secs >= idle_timeout_secs as f64 {
                        std::process::exit(0);
                    }
                }
            }
        });
    }

    let stdin = io::stdin();
    for raw_line in stdin.lock().lines() {
        let Ok(line) = raw_line else { break };
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        last_activity_ms.store(start_instant.elapsed().as_millis() as u64, Ordering::Relaxed);
        busy.store(true, Ordering::Relaxed);

        let (resp, should_shutdown) = match serde_json::from_str::<Value>(trimmed) {
            Ok(val) if val.is_object() => execute_request(&daemon, &val),
            Ok(_) => (
                json_err_resp(Value::Null, "Invalid daemon request: expected JSON object", 2),
                false,
            ),
            Err(e) => (
                json_err_resp(Value::Null, &format!("Invalid daemon request: {e}"), 2),
                false,
            ),
        };

        busy.store(false, Ordering::Relaxed);
        last_activity_ms.store(start_instant.elapsed().as_millis() as u64, Ordering::Relaxed);

        write_frame(resp);
        if should_shutdown {
            break;
        }
    }

    stop.store(true, Ordering::Relaxed);
    daemon.cancel_all_jobs(1000);
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::Connection;
    use std::fs;

    #[test]
    fn native_config_init_set_list_and_fts_search_work_without_python() {
        let tmp = env::temp_dir().join(format!("pf_rust_daemon_test_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        fs::create_dir_all(&tmp).unwrap();

        let daemon = NativeControlDaemon::new(None, None);

        // 1. config init --json
        let (r_init, _) = execute_request(
            &daemon,
            &json!({
                "id": 1,
                "vault": tmp.to_string_lossy(),
                "argv": ["config", "init", "--json"],
            }),
        );
        assert_eq!(r_init["exit_code"], 0);
        let init_env: Value = serde_json::from_str(r_init["stdout"].as_str().unwrap()).unwrap();
        assert_eq!(init_env["ok"], true);

        // 2. config set system_dir .paperforge --json
        let (r_set, _) = execute_request(
            &daemon,
            &json!({
                "id": 2,
                "vault": tmp.to_string_lossy(),
                "argv": ["config", "set", "system_dir", ".paperforge", "--json"],
            }),
        );
        assert_eq!(r_set["exit_code"], 0);

        // 3. Create SQLite FTS5 paperforge.db and run native `search --json` + `base-snapshot --json`
        let idx_dir = tmp.join(".paperforge").join("indexes");
        fs::create_dir_all(&idx_dir).unwrap();
        fs::write(
            idx_dir.join("formal-library.json"),
            serde_json::to_vec(&json!({
                "version": 1,
                "items": [{
                    "zotero_key": "RUST0001",
                    "title": "Cartilage Hydrogel Regeneration",
                    "first_author": "Lin",
                    "year": "2026",
                    "domain": "Ortho",
                    "has_pdf": true,
                    "ocr_status": "done"
                }]
            }))
            .unwrap(),
        )
        .unwrap();

        let conn = Connection::open(idx_dir.join("paperforge.db")).unwrap();
        conn.execute_batch(
            "CREATE TABLE papers (
                zotero_key TEXT PRIMARY KEY,
                citation_key TEXT,
                title TEXT,
                year INTEGER,
                doi TEXT,
                first_author TEXT,
                journal TEXT,
                domain TEXT,
                lifecycle TEXT,
                ocr_status TEXT,
                deep_reading_status TEXT,
                next_step TEXT,
                abstract TEXT
            );
            CREATE TABLE body_units (paper_id TEXT, indexable INTEGER);
            CREATE VIRTUAL TABLE paper_fts USING fts5(title, abstract, domain, content='papers', content_rowid='rowid');
            INSERT INTO papers VALUES ('RUST0001','lin2026','Cartilage Hydrogel Regeneration',2026,'10.1000/1','Lin','Nature','Ortho','ocr_ready','done','pending','analyze','Injectable hydrogel scaffold');
            INSERT INTO paper_fts(rowid, title, abstract, domain) SELECT rowid, title, abstract, domain FROM papers;",
        )
        .unwrap();
        drop(conn);

        let (r_search, _) = execute_request(
            &daemon,
            &json!({
                "id": 3,
                "vault": tmp.to_string_lossy(),
                "argv": ["search", "Hydrogel", "--json"],
            }),
        );
        assert_eq!(r_search["exit_code"], 0);
        let s_env: Value = serde_json::from_str(r_search["stdout"].as_str().unwrap()).unwrap();
        assert_eq!(s_env["data"]["count"], 1);
        assert_eq!(s_env["data"]["matches"][0]["zotero_key"], "RUST0001");

        let (r_snap, _) = execute_request(
            &daemon,
            &json!({
                "id": 4,
                "vault": tmp.to_string_lossy(),
                "argv": ["memory-card", "base-snapshot", "--json"],
            }),
        );
        assert_eq!(r_snap["exit_code"], 0);
        let snap_env: Value = serde_json::from_str(r_snap["stdout"].as_str().unwrap()).unwrap();
        assert_eq!(snap_env["data"]["rows"]["RUST0001"]["title"], "Cartilage Hydrogel Regeneration");

        let _ = fs::remove_dir_all(&tmp);
    }
}
