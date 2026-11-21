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
mod runtime_ops;
mod supervisor;

use config_ops::{try_handle_config_cli, PF_VERSION};
use query_ops::{
    handle_base_snapshot, handle_zero_python_upgrade_plan, try_handle_search_cli,
};
use serde_json::{json, Value};
use std::env;
use std::io::{self, BufRead, Write};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, AtomicU64, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};
use supervisor::{NativeControlDaemon, PushSink};

enum DispatchOutcome {
    Immediate(Value, bool),
    DelegatePython {
        id: Value,
        trace_id: String,
        vault_path: Option<PathBuf>,
        argv: Vec<String>,
        stdin_text: Option<String>,
    },
}

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

fn dispatch_request(
    daemon: &NativeControlDaemon,
    req: &Value,
    frame_sink: Option<PushSink>,
) -> DispatchOutcome {
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
    let caller_trace = req.get("trace_id").and_then(|v| v.as_str());

    match op.as_str() {
        "ping" => {
            return DispatchOutcome::Immediate(
                json!({ "id": id, "ok": true, "exit_code": 0, "stdout": "pong", "stderr": "" }),
                false,
            );
        }
        "shutdown" => {
            daemon.cancel_all_jobs(1000);
            return DispatchOutcome::Immediate(
                json!({ "id": id, "ok": true, "exit_code": 0, "stdout": "", "stderr": "" }),
                true,
            );
        }
        "daemon.health" => {
            return DispatchOutcome::Immediate(
                json_ok_resp(id, daemon.health(vault_path.as_deref())),
                false,
            );
        }
        "daemon.trim" => {
            let idle = req
                .get("idle_seconds")
                .and_then(|v| v.as_f64())
                .unwrap_or(120.0);
            return DispatchOutcome::Immediate(
                json_ok_resp(id, daemon.trim_idle_memory(idle)),
                false,
            );
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
            return DispatchOutcome::Immediate(json_ok_resp(id, payload), false);
        }
        "engine.resolve_key" => {
            let key = req
                .get("key")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .trim();
            let Some(ref vp) = vault_path else {
                return DispatchOutcome::Immediate(
                    json_err_resp(id, "vault and key required", 2),
                    false,
                );
            };
            if key.is_empty() {
                return DispatchOutcome::Immediate(
                    json_err_resp(id, "vault and key required", 2),
                    false,
                );
            }
            let c = daemon.get_or_refresh_vault(vp);
            let rel = c.workspace_map.get(key).cloned();
            return DispatchOutcome::Immediate(
                json_ok_resp(
                    id,
                    json!({ "key": key, "workspace_relpath": rel, "seq": c.last_seq }),
                ),
                false,
            );
        }
        "engine.invalidate" => {
            let cleared = daemon.invalidate_vault(vault_path.as_deref());
            return DispatchOutcome::Immediate(
                json_ok_resp(id, json!({ "cleared": cleared })),
                false,
            );
        }
        "job.submit" => {
            let kind = req
                .get("kind")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .trim();
            if let Some(action) = kind.strip_prefix("runtime.") {
                let ver = req
                    .get("version")
                    .and_then(|v| v.as_str())
                    .unwrap_or(PF_VERSION);
                return DispatchOutcome::Immediate(
                    json_ok_resp(
                        id,
                        daemon.submit_runtime_job(vault_path.as_deref(), action, ver),
                    ),
                    false,
                );
            }
            let Some(ref vp) = vault_path else {
                return DispatchOutcome::Immediate(
                    json_err_resp(id, "vault and kind required", 2),
                    false,
                );
            };
            if kind.is_empty() {
                return DispatchOutcome::Immediate(
                    json_err_resp(id, "vault and kind required", 2),
                    false,
                );
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
            return DispatchOutcome::Immediate(
                json_ok_resp(
                    id,
                    daemon.submit_job(vp, kind, custom_argv, prio, backfill),
                ),
                false,
            );
        }
        "job.stream" => {
            let Some(ref vp) = vault_path else {
                return DispatchOutcome::Immediate(
                    json_err_resp(id, "job.stream requires vault", 2),
                    false,
                );
            };
            let stream_id = req
                .get("stream_id")
                .and_then(|v| v.as_str())
                .map(str::trim)
                .filter(|s| !s.is_empty())
                .map(String::from)
                .unwrap_or_else(|| format!("st_{}", id));
            let Some(arr) = req.get("argv").and_then(|v| v.as_array()) else {
                return DispatchOutcome::Immediate(
                    json_err_resp(id, "job.stream requires string list 'argv'", 2),
                    false,
                );
            };
            let mut argv = Vec::with_capacity(arr.len());
            for item in arr {
                let Some(s) = item.as_str() else {
                    return DispatchOutcome::Immediate(
                        json_err_resp(id, "job.stream requires string list 'argv'", 2),
                        false,
                    );
                };
                argv.push(s.to_string());
            }
            let close_stdin = req
                .get("close_stdin")
                .and_then(|v| v.as_bool())
                .unwrap_or(false);
            let sink = frame_sink.unwrap_or_else(|| Arc::new(|_| {}));
            return DispatchOutcome::Immediate(
                json_ok_resp(
                    id,
                    daemon.submit_stream_job(vp, argv, stream_id, caller_trace, close_stdin, sink),
                ),
                false,
            );
        }
        "job.list" => {
            let inc_recent = req
                .get("include_recent")
                .and_then(|v| v.as_bool())
                .unwrap_or(true);
            return DispatchOutcome::Immediate(
                json_ok_resp(id, daemon.list_jobs(vault_path.as_deref(), inc_recent)),
                false,
            );
        }
        "job.cancel" => {
            let jid = req
                .get("job_id")
                .or_else(|| req.get("stream_id"))
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .trim();
            if jid.is_empty() {
                return DispatchOutcome::Immediate(
                    json_err_resp(id, "job_id or stream_id required", 2),
                    false,
                );
            }
            let grace_ms = req
                .get("grace_ms")
                .and_then(|v| v.as_u64())
                .unwrap_or(3000);
            let wait = req.get("wait").and_then(|v| v.as_bool()).unwrap_or(false);
            return DispatchOutcome::Immediate(
                json_ok_resp(id, daemon.cancel_job(jid, grace_ms, wait)),
                false,
            );
        }
        "notice.list" => {
            let inc = req
                .get("include_acked")
                .and_then(|v| v.as_bool())
                .unwrap_or(false);
            return DispatchOutcome::Immediate(
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
            return DispatchOutcome::Immediate(
                json_ok_resp(id, json!({ "acked": daemon.ack_notice(nid) })),
                false,
            );
        }
        "notice.push" => {
            let ntc = daemon.push_notice_traced(
                req.get("level").and_then(|v| v.as_str()).unwrap_or("info"),
                req.get("code").and_then(|v| v.as_str()).unwrap_or("custom"),
                req.get("title").and_then(|v| v.as_str()).unwrap_or(""),
                req.get("detail").and_then(|v| v.as_str()).unwrap_or(""),
                vault_path.as_deref(),
                caller_trace,
            );
            return DispatchOutcome::Immediate(json_ok_resp(id, ntc), false);
        }
        _ => {}
    }

    // Standard `argv` CLI multiplexing
    let Some(arr) = req.get("argv").and_then(|v| v.as_array()) else {
        return DispatchOutcome::Immediate(
            json_err_resp(id, "daemon request requires string list 'argv'", 2),
            false,
        );
    };
    let mut argv = Vec::with_capacity(arr.len());
    for item in arr {
        let Some(s) = item.as_str() else {
            return DispatchOutcome::Immediate(
                json_err_resp(id, "daemon request requires string list 'argv'", 2),
                false,
            );
        };
        argv.push(s.to_string());
    }
    if argv.first().map(|s| s.as_str()) == Some("daemon") {
        return DispatchOutcome::Immediate(
            json_err_resp(id, "Nested daemon invocation is not supported", 2),
            false,
        );
    }

    // 1. Instant `--version`
    if argv.len() == 1 && argv[0] == "--version" {
        return DispatchOutcome::Immediate(
            json!({
                "id": id,
                "exit_code": 0,
                "stdout": format!("paperforge {PF_VERSION}\n"),
                "stderr": "",
            }),
            false,
        );
    }

    // 1b. Instant Zero-Python `zotero detect [--path DIR] --json`
    if argv.first().map(|s| s.as_str()) == Some("zotero")
        && argv.get(1).map(|s| s.as_str()) == Some("detect")
    {
        let mut path_arg: Option<&str> = None;
        let mut i = 2;
        while i < argv.len() {
            if argv[i] == "--path" {
                if let Some(val) = argv.get(i + 1) {
                    path_arg = Some(val.as_str());
                    i += 1;
                }
            } else if let Some(val) = argv[i].strip_prefix("--path=") {
                path_arg = Some(val);
            }
            i += 1;
        }
        let (rc, out, err) = crate::query_ops::handle_zotero_detect(path_arg);
        return DispatchOutcome::Immediate(
            json!({ "id": id, "exit_code": rc, "stdout": out, "stderr": err }),
            false,
        );
    }

    let python_available = NativeControlDaemon::resolve_python_exe().is_some();

    // 2. Native `< 2ms` fast-paths when vault is supplied
    if let Some(ref vp) = vault_path {
        if let Some((rc, out, err)) = try_handle_config_cli(vp, &argv) {
            return DispatchOutcome::Immediate(
                json!({ "id": id, "exit_code": rc, "stdout": out, "stderr": err }),
                false,
            );
        }
        if argv.first().map(|s| s.as_str()) == Some("memory-card")
            && argv.get(1).map(|s| s.as_str()) == Some("base-snapshot")
            && argv.iter().any(|a| a == "--json")
        {
            let (rc, out, err) = handle_base_snapshot(vp);
            return DispatchOutcome::Immediate(
                json!({ "id": id, "exit_code": rc, "stdout": out, "stderr": err }),
                false,
            );
        }
        if let Some((rc, out, err)) = try_handle_search_cli(vp, &argv, python_available) {
            return DispatchOutcome::Immediate(
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
            return DispatchOutcome::Immediate(
                json!({ "id": id, "exit_code": rc, "stdout": out, "stderr": err }),
                false,
            );
        }
    }

    // 3. Non-blocking on-demand delegation to Python worker runtime
    let trace_id = daemon.next_trace_id(caller_trace);
    let stdin_text = req.get("stdin").and_then(|v| v.as_str()).map(String::from);
    DispatchOutcome::DelegatePython {
        id,
        trace_id,
        vault_path,
        argv,
        stdin_text,
    }
}

#[cfg(test)]
fn execute_request(daemon: &NativeControlDaemon, req: &Value) -> (Value, bool) {
    match dispatch_request(daemon, req, None) {
        DispatchOutcome::Immediate(resp, shutdown) => (resp, shutdown),
        DispatchOutcome::DelegatePython {
            id,
            trace_id,
            vault_path,
            argv,
            stdin_text,
        } => {
            let (rc, out, err) =
                daemon.delegate_to_python(vault_path.as_deref(), &argv, stdin_text.as_deref());
            (
                json!({
                    "id": id,
                    "trace_id": trace_id,
                    "exit_code": rc,
                    "stdout": out,
                    "stderr": err,
                }),
                false,
            )
        }
    }
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.first().map(|s| s.as_str()) == Some("install-runtime") {
        let mut action = "install".to_string();
        let mut version = PF_VERSION.to_string();
        let mut idx = 1;
        while idx < args.len() {
            match args[idx].as_str() {
                "--action" => {
                    idx += 1;
                    if let Some(v) = args.get(idx) {
                        action = v.clone();
                    }
                }
                "--version" | "--expected-version" => {
                    idx += 1;
                    if let Some(v) = args.get(idx) {
                        version = v.clone();
                    }
                }
                _ => {}
            }
            idx += 1;
        }
        match runtime_ops::install_runtime_native(&action, &version, |phase, cur, tot| {
            eprintln!("[PaperForge] {phase} ({cur}/{tot})");
        }) {
            Ok(log_p) => {
                println!("{}", log_p.display());
                return;
            }
            Err(e) => {
                eprintln!("{e}");
                std::process::exit(1);
            }
        }
    }

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

    let frame_sink: PushSink = Arc::new(write_frame.clone());
    let push_sink: Option<PushSink> = if push_enabled {
        Some(frame_sink.clone())
    } else {
        None
    };

    let daemon = NativeControlDaemon::new(parent_pid, push_sink);
    let inflight = Arc::new(AtomicUsize::new(0));
    let stop = Arc::new(AtomicBool::new(false));
    let start_instant = Instant::now();
    let last_activity_ms = Arc::new(AtomicU64::new(0));

    if idle_timeout_secs > 0 || parent_pid.is_some() {
        let d_watch = daemon.clone();
        let inf_watch = inflight.clone();
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
                let is_busy =
                    inf_watch.load(Ordering::Relaxed) > 0 || d_watch.has_active_jobs();
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

        let parsed = serde_json::from_str::<Value>(trimmed);
        let outcome = match parsed {
            Ok(val) if val.is_object() => dispatch_request(&daemon, &val, Some(frame_sink.clone())),
            Ok(_) => DispatchOutcome::Immediate(
                json_err_resp(Value::Null, "Invalid daemon request: expected JSON object", 2),
                false,
            ),
            Err(e) => DispatchOutcome::Immediate(
                json_err_resp(Value::Null, &format!("Invalid daemon request: {e}"), 2),
                false,
            ),
        };

        match outcome {
            DispatchOutcome::Immediate(resp, should_shutdown) => {
                last_activity_ms
                    .store(start_instant.elapsed().as_millis() as u64, Ordering::Relaxed);
                write_frame(resp);
                if should_shutdown {
                    break;
                }
            }
            DispatchOutcome::DelegatePython {
                id,
                trace_id,
                vault_path,
                argv,
                stdin_text,
            } => {
                // Non-blocking worker thread: keeps stdin loop responsive to
                // health checks, native queries, job.cancel, and shutdown.
                let d_worker = daemon.clone();
                let wf = write_frame.clone();
                let inf = inflight.clone();
                let la = last_activity_ms.clone();
                inf.fetch_add(1, Ordering::Relaxed);
                thread::spawn(move || {
                    let (rc, out, err) = d_worker.delegate_to_python(
                        vault_path.as_deref(),
                        &argv,
                        stdin_text.as_deref(),
                    );
                    inf.fetch_sub(1, Ordering::Relaxed);
                    la.store(start_instant.elapsed().as_millis() as u64, Ordering::Relaxed);
                    wf(json!({
                        "id": id,
                        "trace_id": trace_id,
                        "exit_code": rc,
                        "stdout": out,
                        "stderr": err,
                    }));
                });
            }
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

    #[test]
    fn native_runtime_asset_metadata_and_pep440_normalization() {
        assert_eq!(runtime_ops::normalize_pep440("v2.0.0-rc.6"), "2.0.0rc6");
        assert_eq!(runtime_ops::normalize_pep440("2.0.0-beta.2"), "2.0.0b2");
        assert_eq!(runtime_ops::normalize_pep440("2.0.0"), "2.0.0");
        assert!(runtime_ops::uv_target_asset_and_sha().is_some());
        assert!(runtime_ops::verify_sha256_bytes(
            b"abc",
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        ));
    }

    #[test]
    fn native_zotero_detect_reads_sqlite_collections_without_python() {
        let tmp = env::temp_dir().join(format!("pf_zot_test_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        fs::create_dir_all(&tmp).unwrap();

        let zdb = tmp.join("zotero.sqlite");
        let conn = Connection::open(&zdb).unwrap();
        conn.execute_batch(
            "CREATE TABLE itemTypes (itemTypeID INTEGER PRIMARY KEY, typeName TEXT);
             CREATE TABLE items (itemID INTEGER PRIMARY KEY, itemTypeID INTEGER, key TEXT);
             CREATE TABLE deletedItems (itemID INTEGER PRIMARY KEY);
             CREATE TABLE collections (collectionID INTEGER PRIMARY KEY, collectionName TEXT, parentCollectionID INTEGER, key TEXT);
             CREATE TABLE collectionItems (collectionID INTEGER, itemID INTEGER);
             INSERT INTO itemTypes VALUES (1, 'journalArticle'), (2, 'attachment');
             INSERT INTO items VALUES (1, 1, 'ABC12345'), (2, 2, 'ATT99999');
             INSERT INTO collections VALUES (10, 'Cartilage', NULL, 'CROOT1'), (11, 'InVivo', 10, 'CSUB01');
             INSERT INTO collectionItems VALUES (11, 1);",
        )
        .unwrap();
        drop(conn);

        let daemon = NativeControlDaemon::new(None, None);
        let (resp, _) = execute_request(
            &daemon,
            &json!({
                "id": 9,
                "argv": ["zotero", "detect", "--path", tmp.to_string_lossy(), "--json"],
            }),
        );
        assert_eq!(resp["exit_code"], 0);
        let env: Value = serde_json::from_str(resp["stdout"].as_str().unwrap()).unwrap();
        assert_eq!(env["ok"], true);
        assert_eq!(env["data"]["found"], true);
        assert_eq!(env["data"]["total_papers"], 1);
        assert_eq!(env["data"]["collections"].as_array().unwrap().len(), 2);
        assert_eq!(env["data"]["collections"][1]["path"], "Cartilage/InVivo");
        assert_eq!(env["data"]["collections"][0]["item_count"], 1);

        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn job_fsm_blocks_illegal_terminal_transitions_and_utf8_stderr_never_panics() {
        use supervisor::{append_stderr_tail, infer_kind_and_scope, JobRecord, JobStatus};

        let mut rec = JobRecord {
            job_id: "job_1".into(),
            trace_id: "tr_1".into(),
            vault: "/v".into(),
            kind: "ocr".into(),
            scope_key: "keys:K1".into(),
            source: "stream".into(),
            stream_id: Some("st_1".into()),
            status: JobStatus::Queued,
            current: 0,
            total: 0,
            phase: String::new(),
            item_id: String::new(),
            priority_key: None,
            started_at: 1.0,
            finished_at: None,
            exit_code: None,
            error: String::new(),
            stderr_tail: String::new(),
            pid: None,
            child: None,
        };
        assert!(rec.transition(JobStatus::Running).is_ok());
        assert!(rec.transition(JobStatus::Cancelling).is_ok());
        assert!(rec.transition(JobStatus::Cancelled).is_ok());
        // Terminal states must be immutable
        assert!(rec.transition(JobStatus::Running).is_err());
        assert!(rec.transition(JobStatus::Succeeded).is_err());
        assert!(rec.transition(JobStatus::Failed).is_err());
        assert_eq!(rec.status, JobStatus::Cancelled);

        // UTF-8 multi-byte stderr truncation must never panic on char boundary
        let mut buf = String::new();
        for _ in 0..40 {
            append_stderr_tail(&mut buf, "中文错误日志——测试截断边界！", 64);
        }
        assert!(buf.len() <= 64);
        assert!(buf.is_char_boundary(0));

        // Scope key distinguishes individual paper jobs from vault-wide jobs
        let (k1, s1) = infer_kind_and_scope(
            &["action".into(), "run".into(), "ocr.run".into(), "--keys".into(), "A1".into()],
            None,
            None,
        );
        let (k2, s2) = infer_kind_and_scope(
            &["action".into(), "run".into(), "ocr.run".into(), "--keys".into(), "B2".into()],
            None,
            None,
        );
        assert_eq!(k1, "ocr");
        assert_eq!(k2, "ocr");
        assert_ne!(s1, s2);
    }

    #[test]
    fn base_snapshot_prefers_sqlite_ssot_over_stale_legacy_json() {
        let tmp = env::temp_dir().join(format!("pf_ssot_test_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let idx = tmp.join(".paperforge").join("indexes");
        fs::create_dir_all(&idx).unwrap();

        // Stale legacy JSON claims pending & old title
        fs::write(
            idx.join("formal-library.json"),
            serde_json::to_string(&json!({
                "items": [{
                    "zotero_key": "SSOT01",
                    "title": "Stale JSON Title",
                    "ocr_status": "pending",
                    "deep_reading_status": "pending",
                    "impact_factor": "12.5",
                    "has_pdf": true
                }]
            }))
            .unwrap(),
        )
        .unwrap();

        // Authoritative SQLite has done + fresh title AND a second paper missing from JSON
        let conn = Connection::open(idx.join("paperforge.db")).unwrap();
        conn.execute_batch(
            "CREATE TABLE papers (
                zotero_key TEXT PRIMARY KEY,
                title TEXT,
                first_author TEXT,
                year INTEGER,
                journal TEXT,
                domain TEXT,
                ocr_status TEXT,
                deep_reading_status TEXT
            );
            INSERT INTO papers VALUES ('SSOT01', 'SQLite Authoritative Title', 'Lin', 2026, 'Nature', 'Ortho', 'done', 'done');
            INSERT INTO papers VALUES ('SSOT02', 'SQLite Only Paper', 'Chen', 2025, 'Science', 'Neuro', 'done', 'pending');",
        )
        .unwrap();
        drop(conn);

        let daemon = NativeControlDaemon::new(None, None);
        let (resp, _) = execute_request(
            &daemon,
            &json!({
                "id": 10,
                "vault": tmp.to_string_lossy(),
                "argv": ["memory-card", "base-snapshot", "--json"],
            }),
        );
        assert_eq!(resp["exit_code"], 0);
        let env: Value = serde_json::from_str(resp["stdout"].as_str().unwrap()).unwrap();
        assert_eq!(env["data"]["state_authority"], "sqlite");
        assert_eq!(env["data"]["rows"]["SSOT01"]["ocr_status"], "done");
        assert_eq!(env["data"]["rows"]["SSOT01"]["deep_reading_status"], "done");
        assert_eq!(env["data"]["rows"]["SSOT01"]["title"], "SQLite Authoritative Title");
        // Display-only supplement still preserved from JSON
        assert_eq!(env["data"]["rows"]["SSOT01"]["impact_factor"], "12.5");
        assert_eq!(env["data"]["rows"]["SSOT01"]["has_pdf"], true);
        // SQLite-only paper is returned even when absent from formal-library.json
        assert_eq!(env["data"]["rows"]["SSOT02"]["title"], "SQLite Only Paper");
        assert_eq!(env["data"]["rows"]["SSOT02"]["ocr_status"], "done");

        let _ = fs::remove_dir_all(&tmp);
    }
}
