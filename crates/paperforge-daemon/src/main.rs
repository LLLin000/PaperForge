//! `paperforge-daemon` — Cross-platform native Rust control & query sidecar.
//!
//! Speaks the exact `paperforge daemon --stdio` JSON-RPC + duplex NDJSON push
//! wire protocol so Obsidian connects in `< 5ms` at `~4-6 MB` RSS with ZERO
//! local Rust or Python prerequisite for browsing, Base tables, FTS5 search,
//! config management, and veteran upgrade detection, while delegating heavy
//! OCR / Embedding / Sync workers to Python on demand.

mod brief;
mod config_ops;
mod mcp;
mod platform;
mod query_ops;
mod runtime_ops;
mod supervisor;

use brief::{build_agent_brief, discover_vault_from_cwd};
use config_ops::{pf_err, try_handle_config_cli, PF_VERSION};
use mcp::{
    handle_agent_onboarding, handle_mcp_check_with_options, handle_mcp_config, handle_mcp_install,
    handle_skill_sync_all, maybe_reexec_latest_binary, serve_mcp,
};
use query_ops::{handle_zero_python_upgrade_plan, try_handle_search_cli};
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
            let (rel, seq) = daemon.resolve_workspace_key(vp, key);
            return DispatchOutcome::Immediate(
                json_ok_resp(
                    id,
                    json!({ "key": key, "workspace_relpath": rel, "seq": seq }),
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
                let opts = runtime_ops::RuntimeInstallOptions {
                    proxy_url: req
                        .get("proxy_url")
                        .and_then(|v| v.as_str())
                        .map(str::trim)
                        .filter(|s| !s.is_empty())
                        .map(|s| s.to_string()),
                    prefer_cn_mirror: req.get("prefer_cn_mirror").and_then(|v| v.as_bool()),
                };
                return DispatchOutcome::Immediate(
                    json_ok_resp(
                        id,
                        daemon.submit_runtime_job_with_opts(vault_path.as_deref(), action, ver, opts),
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
        if let Some(barrier) = daemon.has_exclusive_barrier(vp) {
            let cmd_name = argv.first().map(|s| s.as_str()).unwrap_or("cli");
            let err = pf_err(
                cmd_name,
                "VAULT_UPGRADE_BARRIER_ACTIVE",
                &format!("Vault exclusive upgrade barrier is active ({barrier}); try again after upgrade completes."),
                json!({ "barrier": barrier }),
                &["Wait for the active vault upgrade/rollback operation to finish."],
            );
            return DispatchOutcome::Immediate(
                json!({
                    "id": id,
                    "exit_code": 1,
                    "stdout": format!("{err}\n"),
                    "stderr": format!("vault_upgrade_barrier_active: {barrier}"),
                }),
                false,
            );
        }
        if let Some((rc, out, err)) = try_handle_config_cli(vp, &argv) {
            return DispatchOutcome::Immediate(
                json!({ "id": id, "exit_code": rc, "stdout": out, "stderr": err }),
                false,
            );
        }
        if argv.first().map(|s| s.as_str()) == Some("agent-brief") {
            let mut paper_arg: Option<&str> = None;
            let mut idx = 1;
            while idx < argv.len() {
                if argv[idx] == "--paper" {
                    paper_arg = argv.get(idx + 1).map(String::as_str);
                    idx += 1;
                } else if let Some(v) = argv[idx].strip_prefix("--paper=") {
                    paper_arg = Some(v);
                }
                idx += 1;
            }
            let out = build_agent_brief(vp, paper_arg);
            let rc = if out.get("ok").and_then(|v| v.as_bool()) == Some(true) {
                0
            } else {
                1
            };
            return DispatchOutcome::Immediate(
                json!({ "id": id, "exit_code": rc, "stdout": format!("{out}\n"), "stderr": "" }),
                false,
            );
        }
        if argv.first().map(|s| s.as_str()) == Some("skill-sync-all") {
            let out = handle_skill_sync_all();
            return DispatchOutcome::Immediate(
                json!({ "id": id, "exit_code": 0, "stdout": format!("{out}\n"), "stderr": "" }),
                false,
            );
        }
        if let Some(cmd @ ("mcp-config" | "mcp-install" | "mcp-check" | "agent-onboarding")) =
            argv.first().map(|s| s.as_str())
        {
            let mut platform_arg = "claude";
            let mut lang_arg = "zh";
            let mut bin_arg: Option<PathBuf> = None;
            let mut skill_arg: Option<PathBuf> = None;
            let mut cfg_arg: Option<PathBuf> = None;
            let mut probe_mcp = false;
            let mut register = false;
            let mut idx = 1;
            while idx < argv.len() {
                if argv[idx] == "--platform" {
                    if let Some(v) = argv.get(idx + 1) {
                        platform_arg = v.as_str();
                        idx += 1;
                    }
                } else if let Some(v) = argv[idx].strip_prefix("--platform=") {
                    platform_arg = v;
                } else if argv[idx] == "--lang" {
                    if let Some(v) = argv.get(idx + 1) {
                        lang_arg = v.as_str();
                        idx += 1;
                    }
                } else if let Some(v) = argv[idx].strip_prefix("--lang=") {
                    lang_arg = v;
                } else if argv[idx] == "--binary" {
                    if let Some(v) = argv.get(idx + 1) {
                        bin_arg = Some(PathBuf::from(v));
                        idx += 1;
                    }
                } else if let Some(v) = argv[idx].strip_prefix("--binary=") {
                    bin_arg = Some(PathBuf::from(v));
                } else if argv[idx] == "--skill-dir" {
                    if let Some(v) = argv.get(idx + 1) {
                        skill_arg = Some(PathBuf::from(v));
                        idx += 1;
                    }
                } else if let Some(v) = argv[idx].strip_prefix("--skill-dir=") {
                    skill_arg = Some(PathBuf::from(v));
                } else if argv[idx] == "--mcp-config" {
                    if let Some(v) = argv.get(idx + 1) {
                        cfg_arg = Some(PathBuf::from(v));
                        idx += 1;
                    }
                } else if let Some(v) = argv[idx].strip_prefix("--mcp-config=") {
                    cfg_arg = Some(PathBuf::from(v));
                } else if argv[idx] == "--probe-mcp" {
                    probe_mcp = true;
                } else if argv[idx] == "--register" {
                    register = true;
                }
                idx += 1;
            }
            let (rc, out) = match cmd {
                "mcp-config" => (0, handle_mcp_config(vp, platform_arg, bin_arg.as_deref())),
                "mcp-install" => handle_mcp_install(vp, platform_arg, bin_arg.as_deref()),
                "mcp-check" => (
                    0,
                    handle_mcp_check_with_options(
                        vp,
                        platform_arg,
                        skill_arg.as_deref(),
                        cfg_arg.as_deref(),
                        probe_mcp,
                        register,
                        None,
                    ),
                ),
                "agent-onboarding" => (0, handle_agent_onboarding(vp, lang_arg, bin_arg.as_deref())),
                _ => unreachable!(),
            };
            return DispatchOutcome::Immediate(
                json!({ "id": id, "exit_code": rc, "stdout": format!("{out}\n"), "stderr": "" }),
                false,
            );
        }
        if argv.first().map(|s| s.as_str()) == Some("memory-card")
            && argv.get(1).map(|s| s.as_str()) == Some("base-snapshot")
            && argv.iter().any(|a| a == "--json")
        {
            let (rc, out, err) = daemon.get_or_build_base_snapshot(vp);
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

fn parse_cli_kv(args: &[String], flag: &str) -> Option<String> {
    let prefix = format!("{flag}=");
    let mut i = 0;
    while i < args.len() {
        if args[i] == flag {
            return args.get(i + 1).cloned();
        }
        if let Some(rest) = args[i].strip_prefix(&prefix) {
            return Some(rest.to_string());
        }
        i += 1;
    }
    None
}

fn print_cli_usage() {
    println!(
        "paperforge-daemon {PF_VERSION} — Native Rust control, MCP & query sidecar\n\n\
USAGE:\n\
  paperforge-daemon [--stdio] [--idle-timeout SEC] [--parent-pid PID]\n\
  paperforge-daemon --mcp [--vault PATH]\n\
  paperforge-daemon [--vault PATH] <SUBCOMMAND> [OPTIONS]\n\n\
SUBCOMMANDS:\n\
  agent-brief        Session state-machine brief (--vault PATH, --paper KEY, --json)\n\
  agent-onboarding   Generate Agent MCP & Skill onboarding prompt (--vault PATH, --lang zh|en)\n\
  mcp-config         Print MCP config snippet (--vault PATH, --platform NAME)\n\
  mcp-install        Merge paperforge MCP server into vault config (--vault PATH, --platform NAME)\n\
  mcp-check          Verify MCP & Skill status (--vault PATH, --probe-mcp, --register, --json)\n\
  skill-sync-all     Sync registered Agent Skill copies with ~/.paperforge/skills/paperforge\n\
  install-runtime    Bootstrap managed Python runtime via uv (--action install|update|repair)\n\n\
OPTIONS:\n\
  -h, --help         Show this help message and exit\n\
  -V, --version      Print daemon version and exit"
    );
}

fn extract_leading_subcommand(args: &[String]) -> Option<&str> {
    let mut i = 0;
    while i < args.len() {
        let a = args[i].as_str();
        if a == "--vault" {
            i += 2;
            continue;
        }
        if a.starts_with("--vault=") {
            i += 1;
            continue;
        }
        return Some(a);
    }
    None
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.first().map(|s| s.as_str()) == Some("--reap-on-parent-exit") {
        let ppid = args.get(1).and_then(|s| s.parse::<u32>().ok()).unwrap_or(0);
        let cpid = args.get(2).and_then(|s| s.parse::<u32>().ok()).unwrap_or(0);
        platform::run_macos_kqueue_reaper(ppid, cpid);
        return;
    }
    if let Some(code) = maybe_reexec_latest_binary(&args) {
        std::process::exit(code);
    }
    if args.iter().any(|a| a == "--help" || a == "-h") {
        print_cli_usage();
        return;
    }
    if args.iter().any(|a| a == "--mcp") {
        let vault_arg = parse_cli_kv(&args, "--vault").map(PathBuf::from);
        let resolved = discover_vault_from_cwd(vault_arg.as_deref());
        serve_mcp(resolved);
        return;
    }
    let subcmd = extract_leading_subcommand(&args);
    if subcmd == Some("skill-sync-all") {
        let out = handle_skill_sync_all();
        println!("{}", serde_json::to_string_pretty(&out).unwrap());
        std::process::exit(0);
    }
    if matches!(
        subcmd,
        Some("agent-brief" | "agent-onboarding" | "mcp-config" | "mcp-install" | "mcp-check")
    ) {
        let sub = subcmd.unwrap();
        let vault_arg = parse_cli_kv(&args, "--vault").map(PathBuf::from);
        let Some(vp) = discover_vault_from_cwd(vault_arg.as_deref()) else {
            let err = pf_err(
                sub,
                "PATH_NOT_FOUND",
                "paperforge.json not found from CWD upward. Pass --vault <path>.",
                json!({}),
                &["Pass --vault <VAULT_DIR> or run inside an initialized PaperForge vault."],
            );
            println!("{}", serde_json::to_string_pretty(&err).unwrap());
            std::process::exit(1);
        };
        let (rc, payload) = match sub {
            "agent-brief" => {
                let paper = parse_cli_kv(&args, "--paper");
                let out = build_agent_brief(&vp, paper.as_deref());
                let code = if out.get("ok").and_then(|v| v.as_bool()) == Some(true) {
                    0
                } else {
                    1
                };
                (code, out)
            }
            "agent-onboarding" => {
                let lang = parse_cli_kv(&args, "--lang").unwrap_or_else(|| "zh".into());
                let bin = parse_cli_kv(&args, "--binary").map(PathBuf::from);
                (0, handle_agent_onboarding(&vp, &lang, bin.as_deref()))
            }
            "mcp-config" => {
                let plat = parse_cli_kv(&args, "--platform").unwrap_or_else(|| "claude".into());
                let bin = parse_cli_kv(&args, "--binary").map(PathBuf::from);
                (0, handle_mcp_config(&vp, &plat, bin.as_deref()))
            }
            "mcp-install" => {
                let plat = parse_cli_kv(&args, "--platform").unwrap_or_else(|| "claude".into());
                let bin = parse_cli_kv(&args, "--binary").map(PathBuf::from);
                handle_mcp_install(&vp, &plat, bin.as_deref())
            }
            "mcp-check" => {
                let plat = parse_cli_kv(&args, "--platform").unwrap_or_else(|| "claude".into());
                let skill_dir = parse_cli_kv(&args, "--skill-dir").map(PathBuf::from);
                let mcp_cfg = parse_cli_kv(&args, "--mcp-config").map(PathBuf::from);
                let probe_mcp = args.iter().any(|a| a == "--probe-mcp");
                let register = args.iter().any(|a| a == "--register");
                (
                    0,
                    handle_mcp_check_with_options(
                        &vp,
                        &plat,
                        skill_dir.as_deref(),
                        mcp_cfg.as_deref(),
                        probe_mcp,
                        register,
                        None,
                    ),
                )
            }
            _ => unreachable!(),
        };
        println!("{}", serde_json::to_string_pretty(&payload).unwrap());
        std::process::exit(rc);
    }
    if subcmd == Some("install-runtime") {
        let mut action = "install".to_string();
        let mut version = PF_VERSION.to_string();
        let mut idx = 0;
        while idx < args.len() {
            match args[idx].as_str() {
                "install-runtime" | "--json" => {}
                "--action" => {
                    idx += 1;
                    if let Some(v) = args.get(idx) {
                        action = v.clone();
                    }
                }
                s if s.starts_with("--action=") => {
                    action = s.trim_start_matches("--action=").to_string();
                }
                "--version" | "--expected-version" => {
                    idx += 1;
                    if let Some(v) = args.get(idx) {
                        version = v.clone();
                    }
                }
                s if s.starts_with("--version=") => {
                    version = s.trim_start_matches("--version=").to_string();
                }
                s if s.starts_with("--expected-version=") => {
                    version = s.trim_start_matches("--expected-version=").to_string();
                }
                "--vault" => {
                    idx += 1;
                }
                s if s.starts_with("--vault=") => {}
                other => {
                    eprintln!("Unknown argument for install-runtime: {other}");
                    std::process::exit(2);
                }
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
                let Some(val) = args.get(i).and_then(|s| s.parse::<u64>().ok()) else {
                    eprintln!("--idle-timeout requires an integer value");
                    std::process::exit(2);
                };
                idle_timeout_secs = val;
            }
            s if s.starts_with("--idle-timeout=") => {
                let raw = s.trim_start_matches("--idle-timeout=");
                let Ok(val) = raw.parse::<u64>() else {
                    eprintln!("--idle-timeout requires an integer value");
                    std::process::exit(2);
                };
                idle_timeout_secs = val;
            }
            "--parent-pid" => {
                i += 1;
                let Some(val) = args.get(i).and_then(|s| s.parse::<u32>().ok()) else {
                    eprintln!("--parent-pid requires an integer PID");
                    std::process::exit(2);
                };
                parent_pid = Some(val);
            }
            s if s.starts_with("--parent-pid=") => {
                let raw = s.trim_start_matches("--parent-pid=");
                let Ok(val) = raw.parse::<u32>() else {
                    eprintln!("--parent-pid requires an integer PID");
                    std::process::exit(2);
                };
                parent_pid = Some(val);
            }
            other => {
                eprintln!("Unknown argument or subcommand: {other}\nRun `paperforge-daemon --help` for usage.");
                std::process::exit(2);
            }
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
            cancel_flag: None,
            runtime_child_pid: None,
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

        // Concise stderr summary strips Python traceback frames and keeps the real error
        let tb = "Traceback (most recent call last):\n  File \"cli.py\", line 12, in main\n    run()\nRuntimeError: ZOTERO_DB_UNREADABLE\n";
        assert_eq!(
            supervisor::summarize_stderr_line(tb, 1),
            "RuntimeError: ZOTERO_DB_UNREADABLE"
        );
        assert_eq!(supervisor::summarize_stderr_line("   \n ", 2), "exit code 2");

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

    #[test]
    fn base_snapshot_sqlite_only_preserves_pdf_flags_and_collections() {
        let tmp = env::temp_dir().join(format!("pf_ssot_pdf_flags_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let idx = tmp.join(".paperforge").join("indexes");
        fs::create_dir_all(&idx).unwrap();

        // NO formal-library.json at all! SQLite alone must supply has_pdf, do_ocr, analyze, collections.
        let conn = Connection::open(idx.join("paperforge.db")).unwrap();
        conn.execute_batch(
            "CREATE TABLE papers (
                zotero_key TEXT PRIMARY KEY,
                title TEXT,
                has_pdf INTEGER,
                do_ocr INTEGER,
                analyze INTEGER,
                collections_json TEXT,
                ocr_status TEXT
            );
            INSERT INTO papers VALUES (
                'ONLYDB1',
                'Pure SQLite Paper',
                1,
                1,
                0,
                '[\"Ortho/ACL\", \"Biomechanics\"]',
                'done'
            );",
        )
        .unwrap();
        drop(conn);

        let daemon = NativeControlDaemon::new(None, None);
        let (resp, _) = execute_request(
            &daemon,
            &json!({
                "id": 11,
                "vault": tmp.to_string_lossy(),
                "argv": ["memory-card", "base-snapshot", "--json"],
            }),
        );
        assert_eq!(resp["exit_code"], 0);
        let env: Value = serde_json::from_str(resp["stdout"].as_str().unwrap()).unwrap();
        assert_eq!(env["data"]["state_authority"], "sqlite");
        let row = &env["data"]["rows"]["ONLYDB1"];
        assert_eq!(row["has_pdf"], true);
        assert_eq!(row["do_ocr"], true);
        assert_eq!(row["analyze"], false);
        assert_eq!(row["collections"], json!(["Ortho/ACL", "Biomechanics"]));

        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn base_snapshot_does_not_resurrect_stale_json_only_deleted_papers() {
        let tmp = env::temp_dir().join(format!("pf_ssot_deleted_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let idx = tmp.join(".paperforge").join("indexes");
        fs::create_dir_all(&idx).unwrap();

        fs::write(
            idx.join("formal-library.json"),
            serde_json::to_string(&json!({
                "items": [
                    { "zotero_key": "ALIVE01", "title": "Alive Paper" },
                    { "zotero_key": "DELETED99", "title": "Deleted Ghost Paper" }
                ]
            }))
            .unwrap(),
        )
        .unwrap();

        let conn = Connection::open(idx.join("paperforge.db")).unwrap();
        conn.execute_batch(
            "CREATE TABLE papers (zotero_key TEXT PRIMARY KEY, title TEXT, ocr_status TEXT);
            INSERT INTO papers VALUES ('ALIVE01', 'Alive Paper SQLite', 'done');",
        )
        .unwrap();
        drop(conn);

        let daemon = NativeControlDaemon::new(None, None);
        let (resp, _) = execute_request(
            &daemon,
            &json!({
                "id": 12,
                "vault": tmp.to_string_lossy(),
                "argv": ["memory-card", "base-snapshot", "--json"],
            }),
        );
        assert_eq!(resp["exit_code"], 0);
        let env: Value = serde_json::from_str(resp["stdout"].as_str().unwrap()).unwrap();
        assert_eq!(env["data"]["state_authority"], "sqlite");
        let rows = env["data"]["rows"].as_object().unwrap();
        assert!(rows.contains_key("ALIVE01"));
        assert!(!rows.contains_key("DELETED99"), "Deleted paper must never resurrect from stale JSON");

        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn base_snapshot_empty_sqlite_table_does_not_fallback_to_stale_json() {
        let tmp = env::temp_dir().join(format!("pf_ssot_empty_db_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let idx = tmp.join(".paperforge").join("indexes");
        fs::create_dir_all(&idx).unwrap();

        fs::write(
            idx.join("formal-library.json"),
            serde_json::to_string(&json!({
                "items": [
                    { "zotero_key": "GHOST01", "title": "Old Deleted Paper 1" },
                    { "zotero_key": "GHOST02", "title": "Old Deleted Paper 2" }
                ]
            }))
            .unwrap(),
        )
        .unwrap();

        // Legitimately empty SQLite `papers` table (0 rows)
        let conn = Connection::open(idx.join("paperforge.db")).unwrap();
        conn.execute_batch("CREATE TABLE papers (zotero_key TEXT PRIMARY KEY, title TEXT, ocr_status TEXT);")
            .unwrap();
        drop(conn);

        let daemon = NativeControlDaemon::new(None, None);
        let (resp, _) = execute_request(
            &daemon,
            &json!({
                "id": 14,
                "vault": tmp.to_string_lossy(),
                "argv": ["memory-card", "base-snapshot", "--json"],
            }),
        );
        assert_eq!(resp["exit_code"], 0);
        let env: Value = serde_json::from_str(resp["stdout"].as_str().unwrap()).unwrap();
        assert_eq!(env["data"]["state_authority"], "sqlite");
        assert!(
            env["data"]["rows"].as_object().unwrap().is_empty(),
            "Empty authoritative SQLite table must not fall back to stale formal-library.json"
        );

        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn base_snapshot_uses_workspace_registry_when_papers_unbuilt_before_memory_build() {
        let tmp = env::temp_dir().join(format!("pf_ssot_ws_reg_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let idx = tmp.join(".paperforge").join("indexes");
        fs::create_dir_all(&idx).unwrap();

        fs::write(
            idx.join("formal-library.json"),
            serde_json::to_string(&json!({
                "items": [
                    { "zotero_key": "LIVE01", "title": "Synced Paper", "domain": "Sports", "has_pdf": true },
                    { "zotero_key": "ORPHAN99", "title": "Deleted Paper", "domain": "Sports", "has_pdf": true }
                ]
            }))
            .unwrap(),
        )
        .unwrap();

        let conn = Connection::open(idx.join("paperforge.db")).unwrap();
        conn.execute_batch(
            "CREATE TABLE papers (zotero_key TEXT PRIMARY KEY, title TEXT, has_pdf INTEGER, ocr_status TEXT);
             CREATE TABLE workspace_registry (zotero_key TEXT PRIMARY KEY, main_note_relpath TEXT, domain TEXT, title TEXT);
             INSERT INTO workspace_registry VALUES ('LIVE01', 'Resources/Literature/Sports/LIVE01.md', 'Sports', 'Synced Paper');",
        )
        .unwrap();
        drop(conn);

        let daemon = NativeControlDaemon::new(None, None);
        let (resp, _) = execute_request(
            &daemon,
            &json!({
                "id": 15,
                "vault": tmp.to_string_lossy(),
                "argv": ["memory-card", "base-snapshot", "--json"],
            }),
        );
        assert_eq!(resp["exit_code"], 0);
        let env: Value = serde_json::from_str(resp["stdout"].as_str().unwrap()).unwrap();
        assert_eq!(env["data"]["state_authority"], "sqlite");
        let rows = env["data"]["rows"].as_object().unwrap();
        assert!(rows.contains_key("LIVE01"));
        assert_eq!(rows["LIVE01"]["has_pdf"], true);
        assert!(!rows.contains_key("ORPHAN99"));

        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn engine_resolve_key_falls_back_to_sqlite_beyond_2048_cache_limit() {
        let tmp = env::temp_dir().join(format!("pf_resolve_2048_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let idx = tmp.join(".paperforge").join("indexes");
        fs::create_dir_all(&idx).unwrap();

        let mut conn = Connection::open(idx.join("paperforge.db")).unwrap();
        conn.execute_batch(
            "CREATE TABLE workspace_registry (zotero_key TEXT PRIMARY KEY, workspace_relpath TEXT);
             CREATE TABLE ocr_catalog (zotero_key TEXT PRIMARY KEY, salvage_action TEXT);",
        )
        .unwrap();
        {
            let tx = conn.transaction().unwrap();
            for i in 0..2105 {
                let k = format!("KEY{i:04}");
                let rel = format!("Literature/Domain/{k}");
                tx.execute(
                    "INSERT INTO workspace_registry (zotero_key, workspace_relpath) VALUES (?1, ?2)",
                    rusqlite::params![k, rel],
                )
                .unwrap();
            }
            tx.commit().unwrap();
        }
        drop(conn);

        let daemon = NativeControlDaemon::new(None, None);
        // Verify bounded in-memory cache stays capped at <= 2048
        let status = daemon.get_or_refresh_vault(&tmp);
        assert_eq!(status.workspace_map.len(), 2048);

        // Verify key #2104 (outside 2048 in-memory cache) still resolves via SQLite fallback!
        let (resp, _) = execute_request(
            &daemon,
            &json!({
                "id": 13,
                "op": "engine.resolve_key",
                "vault": tmp.to_string_lossy(),
                "key": "KEY2104",
            }),
        );
        assert_eq!(resp["exit_code"], 0);
        let body: Value = serde_json::from_str(resp["stdout"].as_str().unwrap()).unwrap();
        assert_eq!(body["workspace_relpath"], "Literature/Domain/KEY2104");

        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn agent_brief_and_mcp_server_and_installer_work_end_to_end() {
        use std::io::Cursor;

        let tmp = env::temp_dir().join(format!("pf_mcp_e2e_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        fs::create_dir_all(&tmp).unwrap();

        let daemon = NativeControlDaemon::new(None, None);
        let _ = execute_request(
            &daemon,
            &json!({ "id": 1, "vault": tmp.to_string_lossy(), "argv": ["config", "init", "--json"] }),
        );
        let _ = execute_request(
            &daemon,
            &json!({ "id": 2, "vault": tmp.to_string_lossy(), "argv": ["config", "set", "system_dir", ".paperforge", "--json"] }),
        );

        let pf = tmp.join(".paperforge");
        let idx = pf.join("indexes");
        fs::create_dir_all(&idx).unwrap();
        fs::create_dir_all(pf.join("logs")).unwrap();
        fs::create_dir_all(pf.join("ocr").join("MCP001")).unwrap();
        fs::write(pf.join("ocr").join("MCP001").join("fulltext.md"), "Body text").unwrap();

        let conn = Connection::open(idx.join("paperforge.db")).unwrap();
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
                collection_path TEXT,
                collections_json TEXT,
                has_pdf INTEGER,
                do_ocr INTEGER,
                analyze INTEGER,
                lifecycle TEXT,
                ocr_status TEXT,
                deep_reading_status TEXT,
                main_note_path TEXT,
                abstract TEXT
            );
            CREATE TABLE body_units (paper_id TEXT, indexable INTEGER);
            CREATE TABLE paper_annotations (ann_id TEXT PRIMARY KEY, paper_id TEXT, intent TEXT, author TEXT, lens TEXT);
            CREATE TABLE paper_memory_cards (zotero_key TEXT, facet TEXT, updated_at TEXT);
            CREATE VIRTUAL TABLE paper_fts USING fts5(title, abstract, domain, content='papers', content_rowid='rowid');
            INSERT INTO papers VALUES ('MCP001','lin2026mcp','PEMF Regeneration Study',2026,'10.1000/mcp','Lin','Nature','Ortho','Ortho/PEMF','[\"Ortho/PEMF\"]',1,1,1,'fulltext_ready','done','pending','Resources/Literature/Ortho/MCP001.md','Pulsed electromagnetic field study');
            INSERT INTO papers VALUES ('MCP002','chen2025','Failed OCR Paper',2025,'10.1000/f','Chen','Science','Ortho','Ortho/Cartilage','[\"Ortho/Cartilage\"]',1,1,0,'pdf_ready','failed','pending','Resources/Literature/Ortho/MCP002.md','Cartilage repair');
            INSERT INTO paper_fts(rowid, title, abstract, domain) SELECT rowid, title, abstract, domain FROM papers;
            INSERT INTO paper_annotations VALUES ('ann1','MCP001','question','user','');
            INSERT INTO paper_annotations VALUES ('ann2','MCP001','evidence','agent','skeleton');
            INSERT INTO paper_memory_cards VALUES ('MCP001','idea_logic','2026-11-26T00:00:00Z');",
        )
        .unwrap();
        drop(conn);

        // Live daemon heartbeat with current PID + dead PID negative check
        fs::write(
            idx.join(".daemon-state.json"),
            serde_json::to_string(&json!({
                "pid": std::process::id(),
                "active_jobs": [{ "kind": "ocr", "status": "running", "current": 1, "total": 3, "item_id": "MCP002" }],
                "exclusive_barrier": null,
                "recent_notices": []
            }))
            .unwrap(),
        )
        .unwrap();

        // 1. agent-brief with single-paper enrichment
        let brief = build_agent_brief(&tmp, Some("MCP001"));
        assert_eq!(brief["ok"], true);
        assert_eq!(brief["data"]["library"]["paper_count"], 2);
        assert_eq!(brief["data"]["library"]["ocr_failed_count"], 1);
        assert_eq!(brief["data"]["runtime"]["daemon_alive"], true);
        assert_eq!(brief["data"]["paper"]["user_question_count"], 1);
        assert_eq!(brief["data"]["paper"]["agent_lenses"], json!(["skeleton"]));
        assert!(brief["data"]["capabilities"]["blocked_actions"]["ocr"].is_string());
        let hint_codes: Vec<&str> = brief["data"]["hints"]
            .as_array()
            .unwrap()
            .iter()
            .filter_map(|h| h.get("code").and_then(|v| v.as_str()))
            .collect();
        assert!(hint_codes.contains(&"job.ocr.running"));
        assert!(hint_codes.contains(&"paper.has_user_questions"));

        // 2. MCP initialize -> tools/list (exact 7) -> tools/call
        let init_resp = mcp::process_mcp_message(
            &daemon,
            Some(&tmp),
            &json!({ "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": { "protocolVersion": "2025-03-26" } }),
        )
        .unwrap();
        assert_eq!(init_resp["result"]["protocolVersion"], "2025-03-26");
        assert_eq!(init_resp["result"]["serverInfo"]["name"], "paperforge");

        let notif_resp = mcp::process_mcp_message(
            &daemon,
            Some(&tmp),
            &json!({ "jsonrpc": "2.0", "method": "notifications/initialized" }),
        );
        assert!(notif_resp.is_none());

        let tools_resp = mcp::process_mcp_message(
            &daemon,
            Some(&tmp),
            &json!({ "jsonrpc": "2.0", "id": 2, "method": "tools/list" }),
        )
        .unwrap();
        assert_eq!(tools_resp["result"]["tools"].as_array().unwrap().len(), 7);

        let lib_resp = mcp::process_mcp_message(
            &daemon,
            Some(&tmp),
            &json!({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "paperforge_library_query",
                    "arguments": { "ocr_status": "failed", "limit": 10 }
                }
            }),
        )
        .unwrap();
        assert_eq!(lib_resp["result"]["isError"], false);
        let lib_text = lib_resp["result"]["content"][0]["text"].as_str().unwrap();
        let lib_json: Value = serde_json::from_str(lib_text).unwrap();
        assert_eq!(lib_json["data"]["total_matched"], 1);
        assert_eq!(lib_json["data"]["items"][0]["zotero_key"], "MCP002");

        // 3. Content-Length framing roundtrip
        let sample = json!({ "jsonrpc": "2.0", "id": 9, "method": "ping" }).to_string();
        let framed = format!("Content-Length: {}\r\n\r\n{}", sample.len(), sample);
        let mut cur = Cursor::new(framed.into_bytes());
        let (decoded, mode) = mcp::read_next_mcp_message(&mut cur).unwrap().unwrap();
        assert_eq!(mode, mcp::FramingMode::ContentLength);
        assert_eq!(decoded["method"], "ping");

        // 4. mcp-install preserves unrelated servers & refuses corrupt JSON
        let fake_bin = tmp.join(if cfg!(windows) { "paperforge-daemon.exe" } else { "paperforge-daemon" });
        fs::write(&fake_bin, b"bin").unwrap();
        fs::write(
            tmp.join(".mcp.json"),
            serde_json::to_string_pretty(&json!({ "mcpServers": { "other": { "command": "x" } }, "custom": 42 })).unwrap(),
        )
        .unwrap();
        let (rc, inst) = handle_mcp_install(&tmp, "claude", Some(&fake_bin));
        assert_eq!(rc, 0);
        assert_eq!(inst["data"]["created_new"], false);
        let merged: Value = serde_json::from_str(&fs::read_to_string(tmp.join(".mcp.json")).unwrap()).unwrap();
        assert_eq!(merged["custom"], 42);
        assert_eq!(merged["mcpServers"]["other"]["command"], "x");
        assert!(merged["mcpServers"]["paperforge"]["args"].as_array().unwrap().contains(&json!("--mcp")));

        let chk = mcp::handle_mcp_check(&tmp, "claude");
        assert_eq!(chk["data"]["mcp_configured"], true);
        assert_eq!(chk["data"]["mcp_binary_valid"], true);

        // Corrupt JSON guard
        fs::write(tmp.join(".cursor").join("mcp.json").parent().unwrap().join("temp_ignored"), b"").ok();
        fs::create_dir_all(tmp.join(".cursor")).unwrap();
        fs::write(tmp.join(".cursor").join("mcp.json"), "{ invalid json").unwrap();
        let (rc_bad, bad_out) = handle_mcp_install(&tmp, "cursor", Some(&fake_bin));
        assert_eq!(rc_bad, 1);
        assert_eq!(bad_out["ok"], false);
        assert_eq!(fs::read_to_string(tmp.join(".cursor").join("mcp.json")).unwrap(), "{ invalid json");

        // Re-exec version guard prevents downgrading a newer shim to an older cached binary
        assert!(!mcp::is_meta_tag_compatible_for_reexec("2.0.3", "2.0.6"));
        assert!(!mcp::is_meta_tag_compatible_for_reexec("2.0.6-rc.1", "2.0.6"));
        assert!(mcp::is_meta_tag_compatible_for_reexec("2.0.6", "2.0.6-rc.1"));
        assert!(mcp::is_meta_tag_compatible_for_reexec("2.0.6", "2.0.6"));
        assert!(mcp::is_meta_tag_compatible_for_reexec("v2.0.7", "2.0.6"));

        // Self-onboarding prompt, external TOML/skill check + register + probe-mcp + skill-sync-all
        let onb = handle_agent_onboarding(&tmp, "zh", Some(&fake_bin));
        assert_eq!(onb["ok"], true);
        let prompt = onb["data"]["prompt"].as_str().unwrap();
        assert!(prompt.contains("mcp-check") && prompt.contains("--probe-mcp"));

        let ext_root = tmp.join("external_agent_home");
        let hub_dir = ext_root.join("hub_paperforge");
        let copy_skill = ext_root.join("agent_copy").join("skills").join("paperforge");
        let custom_skill = ext_root.join("agent_custom").join("skills").join("paperforge");
        fs::create_dir_all(&hub_dir).unwrap();
        fs::write(hub_dir.join("SKILL.md"), "---\nname: paperforge\n---\nv1\r\n").unwrap();
        fs::create_dir_all(&copy_skill).unwrap();
        fs::write(copy_skill.join("SKILL.md"), "---\nname: paperforge\n---\nv1\n").unwrap();
        fs::create_dir_all(&custom_skill).unwrap();
        fs::write(custom_skill.join("SKILL.md"), "# User Customized\n").unwrap();
        // Digest parity across CRLF vs LF
        assert_eq!(
            mcp::skill_tree_digest(&hub_dir),
            mcp::skill_tree_digest(&copy_skill)
        );

        let codex_toml = ext_root.join("codex_config.toml");
        fs::write(
            &codex_toml,
            format!(
                "[mcp_servers.paperforge]\ncommand = \"{}\"\nargs = [\"--mcp\", \"--vault\", \"{}\"]\n",
                fake_bin.to_string_lossy().replace('\\', "\\\\"),
                tmp.to_string_lossy().replace('\\', "\\\\")
            ),
        )
        .unwrap();
        let reg_file = ext_root.join("agent-installs.json");
        // Dummy non-executable fake_bin -> probe_mcp must report false (never mask broken binary)
        let chk_ext = handle_mcp_check_with_options(
            &tmp,
            "codex",
            Some(&copy_skill),
            Some(&codex_toml),
            true,
            true,
            Some(&reg_file),
        );
        assert_eq!(chk_ext["data"]["config_format"], "toml");
        assert_eq!(chk_ext["data"]["mcp_configured"], true);
        assert_eq!(chk_ext["data"]["mcp_args_ok"], true);
        assert_eq!(chk_ext["data"]["mcp_binary_valid"], true);
        assert_eq!(chk_ext["data"]["mcp_handshake_ok"], false);
        assert_eq!(chk_ext["data"]["registered"], true);

        // Register unmodified copy & customized copy with v1 hub digest in isolated test registry
        let v1_digest = mcp::skill_tree_digest(&hub_dir).unwrap();
        let reg_raw: Value = serde_json::from_str(&fs::read_to_string(&reg_file).unwrap()).unwrap();
        let mut installs: Vec<Value> = reg_raw["installs"]
            .as_array()
            .unwrap()
            .iter()
            .map(|entry| {
                let mut obj = entry.as_object().cloned().unwrap();
                obj.insert("last_synced_digest".into(), json!(v1_digest));
                Value::Object(obj)
            })
            .collect();
        installs.push(json!({
            "skill_dir": custom_skill.to_string_lossy(),
            "link_mode": "copy",
            "last_synced_digest": v1_digest,
        }));
        fs::write(
            &reg_file,
            serde_json::to_string_pretty(&json!({ "schema_version": 1, "installs": installs })).unwrap(),
        )
        .unwrap();

        // Update hub -> sync-all updates unmodified copy and preserves customized copy!
        fs::write(hub_dir.join("SKILL.md"), "---\nname: paperforge\n---\nv2\n").unwrap();
        let synced = mcp::sync_all_registered_installs_with_paths(&hub_dir, &reg_file);
        assert_eq!(synced["data"]["updated"], 1);
        assert_eq!(synced["data"]["customized_preserved"], 1);
        assert!(fs::read_to_string(copy_skill.join("SKILL.md")).unwrap().contains("v2"));
        assert_eq!(
            fs::read_to_string(custom_skill.join("SKILL.md")).unwrap(),
            "# User Customized\n"
        );

        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn runtime_checksum_zip_validation_and_secret_redaction() {
        let valid_hash = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
        let txt = format!("{valid_hash}  *paperforge-2.0.7-py3-none-any.whl\n");
        assert_eq!(
            runtime_ops::parse_checksum_for_asset(&txt, "paperforge-2.0.7-py3-none-any.whl").as_deref(),
            Some(valid_hash)
        );
        assert_eq!(
            runtime_ops::parse_checksum_for_asset(&txt, "other.whl"),
            None
        );

        // Corrupt zip bytes fail validation
        assert!(!runtime_ops::is_valid_wheel_zip(b"not a zip"));
        // Minimal valid zip archive passes validation
        let mut cursor = std::io::Cursor::new(Vec::<u8>::new());
        {
            let mut zw = zip::ZipWriter::new(&mut cursor);
            zw.start_file("METADATA", zip::write::SimpleFileOptions::default()).unwrap();
            std::io::Write::write_all(&mut zw, b"Name: paperforge\n").unwrap();
            zw.finish().unwrap();
        }
        assert!(runtime_ops::is_valid_wheel_zip(&cursor.into_inner()));

        // Secret redaction in installer log lines
        let line = "GET https://user:supersecret@mirror.example/pkg Authorization: Bearer sk-abc12345 api_key=topsecret";
        let red = runtime_ops::redact_log_line(line);
        assert!(!red.contains("supersecret"));
        assert!(!red.contains("sk-abc12345"));
        assert!(!red.contains("topsecret"));
    }

    #[test]
    fn reexec_meta_containment_sha256_and_prerelease_guards() {
        use sha2::{Digest, Sha256};

        let tmp = std::env::temp_dir().join(format!("pf-reexec-test-{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let bin_dir = tmp.join("bin");
        let outside_dir = tmp.join("outside");
        fs::create_dir_all(&bin_dir).unwrap();
        fs::create_dir_all(&outside_dir).unwrap();

        let good_bin = bin_dir.join("paperforge-daemon-2.0.7");
        fs::write(&good_bin, b"daemon-binary-bytes").unwrap();
        let mut hasher = Sha256::new();
        hasher.update(b"daemon-binary-bytes");
        let good_sha = format!("{:x}", hasher.finalize());

        let outside_bin = outside_dir.join("paperforge-daemon-2.0.7");
        fs::write(&outside_bin, b"daemon-binary-bytes").unwrap();

        // Valid entry inside bin_dir with matching sha256 & >= tag succeeds
        let ok_meta = json!({
            "tag": "v2.0.7",
            "sha256": good_sha,
            "binaryPath": good_bin.to_string_lossy(),
        });
        assert!(mcp::validate_meta_binary_for_reexec(&bin_dir, &ok_meta, "2.0.6").is_some());

        // Reject binary outside managed bin_dir even if sha256 matches
        let esc_meta = json!({
            "tag": "v2.0.7",
            "sha256": good_sha,
            "binaryPath": outside_bin.to_string_lossy(),
        });
        assert!(mcp::validate_meta_binary_for_reexec(&bin_dir, &esc_meta, "2.0.6").is_none());

        // Reject mismatched sha256
        let bad_sha = json!({
            "tag": "v2.0.7",
            "sha256": "f".repeat(64),
            "binaryPath": good_bin.to_string_lossy(),
        });
        assert!(mcp::validate_meta_binary_for_reexec(&bin_dir, &bad_sha, "2.0.6").is_none());

        // Reject pre-release downgrade 2.0.6 -> 2.0.6-rc.1
        let pre_meta = json!({
            "tag": "2.0.6-rc.1",
            "sha256": good_sha,
            "binaryPath": good_bin.to_string_lossy(),
        });
        assert!(mcp::validate_meta_binary_for_reexec(&bin_dir, &pre_meta, "2.0.6").is_none());

        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn mcp_security_pin_enum_validation_toml_and_skill_containment() {
        let tmp = std::env::temp_dir().join(format!("pf-mcp-sec-test-{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let pinned = tmp.join("pinned_vault");
        let other = tmp.join("other_vault");
        fs::create_dir_all(&pinned).unwrap();
        fs::create_dir_all(&other).unwrap();

        let daemon = NativeControlDaemon::new(None, None);

        // Reject vault override outside pinned --vault
        let cross = mcp::process_mcp_message(
            &daemon,
            Some(&pinned),
            &json!({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "paperforge_brief",
                    "arguments": { "vault": other.to_string_lossy() }
                }
            }),
        )
        .unwrap();
        assert_eq!(cross["result"]["isError"], true);

        // Reject invalid enum on paperforge_search
        let bad_enum = mcp::process_mcp_message(
            &daemon,
            Some(&pinned),
            &json!({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "paperforge_search",
                    "arguments": { "query": "cancer", "ocr": "--malicious-flag" }
                }
            }),
        )
        .unwrap();
        assert_eq!(bad_enum["result"]["isError"], true);

        // Exclusive upgrade barrier blocks mutating MCP tools and cli.run
        daemon.acquire_exclusive_barrier(&pinned, "test-upgrade");
        let blocked_mcp = mcp::process_mcp_message(
            &daemon,
            Some(&pinned),
            &json!({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": { "name": "paperforge_memory_refine", "arguments": {} }
            }),
        )
        .unwrap();
        assert_eq!(blocked_mcp["result"]["isError"], true);
        assert!(blocked_mcp["result"]["content"][0]["text"]
            .as_str()
            .unwrap()
            .contains("test-upgrade"));

        let (blocked_cli, _) = execute_request(
            &daemon,
            &json!({
                "id": "r1",
                "vault": pinned.to_string_lossy(),
                "argv": ["search", "x"]
            }),
        );
        assert_eq!(blocked_cli["exit_code"], 1);
        let blocked_payload: Value = serde_json::from_str(blocked_cli["stdout"].as_str().unwrap()).unwrap();
        assert_eq!(blocked_payload["ok"], false);
        assert_eq!(blocked_payload["error"]["code"], "VAULT_UPGRADE_BARRIER_ACTIVE");
        daemon.release_exclusive_barrier(&pinned);

        // TOML multi-line args & `#` inside string values
        let fake_bin = tmp.join("pf-dummy");
        fs::write(&fake_bin, b"not-exec").unwrap();
        let codex_toml = tmp.join("codex.toml");
        fs::write(
            &codex_toml,
            format!(
                "[mcp_servers.paperforge]\ncommand = \"{}\"\nargs = [\n  \"--mcp\",\n  \"--vault\",\n  \"{}\", # trailing comment\n]\n# [other.section]\n",
                fake_bin.to_string_lossy().replace('\\', "\\\\"),
                pinned.to_string_lossy().replace('\\', "\\\\")
            ),
        )
        .unwrap();
        let chk = mcp::handle_mcp_check_with_options(
            &pinned,
            "codex",
            None,
            Some(&codex_toml),
            false,
            false,
            None,
        );
        assert_eq!(chk["data"]["mcp_configured"], true);
        assert_eq!(chk["data"]["mcp_args_ok"], true);

        // Skill-sync containment rejects paths outside known skill dirs or with '..' or non-'paperforge' leaf
        let hub_dir = tmp.join("hub");
        let unsafe_non_pf = tmp.join("agent").join("skills").join("other_dir");
        let unsafe_file = unsafe_non_pf.join("keep.txt");
        fs::create_dir_all(&hub_dir).unwrap();
        fs::write(hub_dir.join("SKILL.md"), "# hub v1\n").unwrap();
        fs::create_dir_all(&unsafe_non_pf).unwrap();
        fs::write(&unsafe_file, "must survive").unwrap();
        let reg_path = tmp.join("agent-installs.json");
        fs::write(
            &reg_path,
            serde_json::to_string_pretty(&json!({
                "schema_version": 1,
                "installs": [{
                    "skill_dir": unsafe_non_pf.to_string_lossy(),
                    "link_mode": "copy",
                    "last_synced_digest": "deadbeef"
                }]
            }))
            .unwrap(),
        )
        .unwrap();
        let sync_res = mcp::sync_all_registered_installs_with_paths(&hub_dir, &reg_path);
        assert_eq!(sync_res["data"]["updated"], 0);
        assert!(!sync_res["data"]["errors"].as_array().unwrap().is_empty());
        assert_eq!(fs::read_to_string(&unsafe_file).unwrap(), "must survive");

        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn brief_corrupt_db_config_validation_and_upgrade_plan_schema() {
        let tmp = std::env::temp_dir().join(format!("pf-brief-cfg-{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let pf_dir = tmp.join(".paperforge");
        let idx_dir = pf_dir.join("indexes");
        fs::create_dir_all(&idx_dir).unwrap();
        fs::write(pf_dir.join("paperforge.json"), json!({ "schema_version": 2 }).to_string()).unwrap();
        fs::write(idx_dir.join("paperforge.db"), b"this is corrupt sqlite data").unwrap();

        let brief = brief::build_agent_brief(&tmp, None);
        assert_eq!(brief["data"]["capabilities"]["db_corrupt"], true);
        assert_eq!(brief["data"]["capabilities"]["safe_read"], false);
        assert_eq!(brief["data"]["capabilities"]["safe_write"], false);
        let hints = brief["data"]["hints"].as_array().unwrap();
        assert!(hints.iter().any(|h| h["code"] == "db.corrupt"));

        // Config URL `@` userinfo & profile regex validation + UPPERCASE error codes
        let bad_url = config_ops::try_handle_config_cli(
            &tmp,
            &[
                "config".into(),
                "set".into(),
                "vector_db_api_base".into(),
                "https://user:secret@example.com".into(),
                "--json".into(),
            ],
        )
        .unwrap();
        assert_eq!(bad_url.0, 1);
        let err_val: Value = serde_json::from_str(&bad_url.1).unwrap();
        assert_eq!(err_val["error"]["code"], "VALIDATION_ERROR");

        // Zero-python upgrade --plan parity fields
        let (rc, plan_out, _) = query_ops::handle_zero_python_upgrade_plan(&tmp);
        assert_eq!(rc, 0);
        let plan_json: Value = serde_json::from_str(&plan_out).unwrap();
        assert_eq!(plan_json["ok"], true);
        assert_eq!(plan_json["data"]["schema_version"], 2);
        assert!(plan_json["data"]["census"]["pf_machine_pure"].is_number());
        assert!(plan_json["data"]["census"]["pf_canonical"]["workspaces"].is_number());
        assert!(plan_json["data"]["provenance"]["needs_upgrade"].is_boolean());
        assert!(plan_json["data"]["target_version"].is_string());

        let _ = fs::remove_dir_all(&tmp);
    }
}
