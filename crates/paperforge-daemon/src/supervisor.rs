//! Low-Memory Resident Supervisor, Bounded LRU Vault Cache, Notice Center,
//! Ephemeral Python Worker Supervision, and On-Demand Python Delegation.

use crate::config_ops::{pf_err, strip_verbatim_prefix, PF_VERSION};
use crate::platform::{
    atomic_write_bytes, attach_child_to_job, configure_worker_command, current_ppid, is_pid_alive,
    kill_pid_tree, kill_process_tree, now_unix_secs, process_rss_bytes,
};
use crate::query_ops::{open_readonly_db, read_state_seq, resolve_engine_dir};
use serde_json::{json, Value};
use std::collections::{HashMap, HashSet, VecDeque};
use std::env;
use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, AtomicU32, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

const MAX_CACHED_VAULTS: usize = 4;
const MAX_SNAPSHOT_CACHE: usize = 2;
const MAX_WORKSPACES_PER_VAULT: usize = 2048;
const MAX_NOTICES: usize = 100;
const MAX_RECENT_JOBS: usize = 25;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum JobStatus {
    Queued,
    Running,
    Cancelling,
    Succeeded,
    Failed,
    Cancelled,
}

impl JobStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            JobStatus::Queued => "queued",
            JobStatus::Running => "running",
            JobStatus::Cancelling => "cancelling",
            JobStatus::Succeeded => "succeeded",
            JobStatus::Failed => "failed",
            JobStatus::Cancelled => "cancelled",
        }
    }

    pub fn is_terminal(&self) -> bool {
        matches!(
            self,
            JobStatus::Succeeded | JobStatus::Failed | JobStatus::Cancelled
        )
    }
}

pub fn append_stderr_tail(buf: &mut String, line: &str, max_bytes: usize) {
    buf.push_str(line);
    buf.push('\n');
    if buf.len() > max_bytes {
        let mut drain_to = buf.len() - max_bytes;
        while drain_to < buf.len() && !buf.is_char_boundary(drain_to) {
            drain_to += 1;
        }
        buf.drain(..drain_to);
    }
}

/// Extract a concise, single-line error reason from raw stderr without leaking
/// multi-line Python tracebacks into user-facing notices.
pub fn summarize_stderr_line(stderr: &str, rc: i32) -> String {
    let lines: Vec<&str> = stderr
        .lines()
        .map(str::trim)
        .filter(|l| !l.is_empty())
        .collect();
    for line in lines.iter().rev() {
        if line.starts_with("Traceback (")
            || line.starts_with("File \"")
            || line.chars().all(|c| c == '^' || c == '~' || c == ' ')
        {
            continue;
        }
        return line.chars().take(220).collect();
    }
    if let Some(last) = lines.last() {
        return last.chars().take(220).collect();
    }
    format!("exit code {rc}")
}

pub fn infer_kind_and_scope(
    argv: &[String],
    explicit_kind: Option<&str>,
    priority_key: Option<&str>,
) -> (String, String) {
    let kind = if let Some(k) = explicit_kind.filter(|s| !s.trim().is_empty()) {
        k.trim().to_string()
    } else if argv.first().map(|s| s.as_str()) == Some("action")
        && argv.get(1).map(|s| s.as_str()) == Some("run")
    {
        match argv.get(2).map(|s| s.as_str()).unwrap_or("") {
            a if a.starts_with("ocr.") => "ocr".to_string(),
            a if a.starts_with("memory.") => "embed".to_string(),
            a if a.starts_with("library.") => "sync".to_string(),
            other if !other.is_empty() => other.to_string(),
            _ => "action".to_string(),
        }
    } else if argv.first().map(|s| s.as_str()) == Some("upgrade") {
        "upgrade.heal".to_string()
    } else {
        argv.first()
            .cloned()
            .filter(|s| !s.is_empty())
            .unwrap_or_else(|| "task".to_string())
    };

    if let Some(pk) = priority_key.filter(|s| !s.trim().is_empty()) {
        return (kind, format!("key:{}", pk.trim()));
    }
    let mut keys: Vec<String> = Vec::new();
    let mut i = 0;
    while i < argv.len() {
        let arg = argv[i].as_str();
        if matches!(arg, "--keys" | "--key" | "--paper" | "--priority-key") {
            if let Some(val) = argv.get(i + 1) {
                keys.push(val.trim().to_string());
                i += 1;
            }
        } else if let Some(rest) = arg
            .strip_prefix("--keys=")
            .or_else(|| arg.strip_prefix("--key="))
            .or_else(|| arg.strip_prefix("--paper="))
            .or_else(|| arg.strip_prefix("--priority-key="))
        {
            keys.push(rest.trim().to_string());
        }
        i += 1;
    }
    let scope_key = if !keys.is_empty() {
        keys.sort();
        keys.dedup();
        format!("keys:{}", keys.join(","))
    } else {
        "vault".to_string()
    };
    (kind, scope_key)
}

#[derive(Clone)]
pub struct VaultCacheEntry {
    pub vault_key: String,
    pub last_seq: i64,
    pub workspace_map: HashMap<String, String>,
    pub ocr_salvage_counts: HashMap<String, i64>,
    pub hits: u64,
    pub misses: u64,
    pub refreshed_at: f64,
    pub last_access: Instant,
}

pub struct JobRecord {
    pub job_id: String,
    pub trace_id: String,
    pub vault: String,
    pub kind: String,
    pub scope_key: String,
    pub source: String,
    pub stream_id: Option<String>,
    pub status: JobStatus,
    pub current: i64,
    pub total: i64,
    pub phase: String,
    pub item_id: String,
    pub priority_key: Option<String>,
    pub started_at: f64,
    pub finished_at: Option<f64>,
    pub exit_code: Option<i32>,
    pub error: String,
    pub stderr_tail: String,
    pub pid: Option<u32>,
    pub child: Option<Child>,
    pub cancel_flag: Option<Arc<AtomicBool>>,
    pub runtime_child_pid: Option<Arc<AtomicU32>>,
}

impl JobRecord {
    /// Strict finite-state transition gate: terminal states are immutable.
    pub fn transition(&mut self, next: JobStatus) -> Result<(), String> {
        if self.status == next {
            return Ok(());
        }
        let legal = match (self.status, next) {
            (
                JobStatus::Queued,
                JobStatus::Running
                | JobStatus::Cancelling
                | JobStatus::Cancelled
                | JobStatus::Failed,
            ) => true,
            (
                JobStatus::Running,
                JobStatus::Cancelling
                | JobStatus::Succeeded
                | JobStatus::Failed
                | JobStatus::Cancelled,
            ) => true,
            (
                JobStatus::Cancelling,
                JobStatus::Cancelled | JobStatus::Succeeded | JobStatus::Failed,
            ) => true,
            _ => false,
        };
        if legal {
            self.status = next;
            Ok(())
        } else {
            Err(format!(
                "illegal job state transition: {} -> {}",
                self.status.as_str(),
                next.as_str()
            ))
        }
    }

    pub fn to_json(&self) -> Value {
        let duration_ms = self.finished_at.map(|fin| ((fin - self.started_at).max(0.0) * 1000.0).round() as u64);
        json!({
            "job_id": self.job_id,
            "trace_id": self.trace_id,
            "vault": self.vault,
            "kind": self.kind,
            "scope_key": self.scope_key,
            "source": self.source,
            "stream_id": self.stream_id,
            "status": self.status.as_str(),
            "current": self.current,
            "total": self.total,
            "phase": self.phase,
            "item_id": self.item_id,
            "priority_key": self.priority_key,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": duration_ms,
            "exit_code": self.exit_code,
            "error": self.error,
            "pid": self.pid,
        })
    }
}

pub type PushSink = Arc<dyn Fn(Value) + Send + Sync>;

#[derive(Clone)]
struct CachedBaseSnapshot {
    vault_key: String,
    fingerprint: (i64, u64, u64, u64, u64, u64, u64),
    payload: (i32, String, String),
    last_access: Instant,
}

struct InnerState {
    started_at: f64,
    parent_pid: Option<u32>,
    initial_ppid: Option<u32>,
    event_seq: u64,
    job_counter: u64,
    trace_counter: u64,
    notice_counter: u64,
    push_sink: Option<PushSink>,
    vault_lru: VecDeque<VaultCacheEntry>,
    base_snapshot_cache: VecDeque<CachedBaseSnapshot>,
    notices: VecDeque<Value>,
    active_jobs: HashMap<String, Arc<Mutex<JobRecord>>>,
    delegated_pids: HashSet<u32>,
    recent_jobs: VecDeque<Value>,
    exclusive_barriers: HashMap<String, String>,
    followup_heal_priority: HashMap<String, String>,
}

#[derive(Clone)]
pub struct NativeControlDaemon {
    inner: Arc<Mutex<InnerState>>,
}

impl NativeControlDaemon {
    pub fn new(parent_pid: Option<u32>, push_sink: Option<PushSink>) -> Self {
        Self {
            inner: Arc::new(Mutex::new(InnerState {
                started_at: now_unix_secs(),
                parent_pid,
                initial_ppid: current_ppid(),
                event_seq: 0,
                job_counter: 0,
                trace_counter: 0,
                notice_counter: 0,
                push_sink,
                vault_lru: VecDeque::new(),
                base_snapshot_cache: VecDeque::new(),
                notices: VecDeque::new(),
                active_jobs: HashMap::new(),
                delegated_pids: HashSet::new(),
                recent_jobs: VecDeque::new(),
                exclusive_barriers: HashMap::new(),
                followup_heal_priority: HashMap::new(),
            })),
        }
    }

    pub fn next_trace_id(&self, caller_trace: Option<&str>) -> String {
        if let Some(t) = caller_trace.map(str::trim).filter(|s| !s.is_empty()) {
            return t.to_string();
        }
        let mut g = self.inner.lock().unwrap();
        g.trace_counter += 1;
        format!("tr_{}_{}", std::process::id(), g.trace_counter)
    }

    pub fn norm_vault(vault: &Path) -> String {
        let abs = fs::canonicalize(vault).unwrap_or_else(|_| vault.to_path_buf());
        strip_verbatim_prefix(&abs).to_string_lossy().into_owned()
    }

    /// Resolve optional published Python interpreter (`PAPERFORGE_PYTHON_EXE` or `~/.paperforge/runtime/pointer.json`).
    pub fn resolve_python_exe() -> Option<PathBuf> {
        if let Ok(env_py) = env::var("PAPERFORGE_PYTHON_EXE") {
            let p = PathBuf::from(env_py.trim());
            if p.is_file() {
                return Some(p);
            }
        }
        let ptr_path = crate::mcp::paperforge_home_dir()?
            .join("runtime")
            .join("pointer.json");
        let raw = fs::read_to_string(ptr_path).ok()?;
        let val: Value = serde_json::from_str(&raw).ok()?;
        if val.get("schema_version").and_then(|v| v.as_i64()) != Some(1) {
            return None;
        }
        let py = PathBuf::from(val.get("python_path")?.as_str()?);
        if py.is_file() {
            Some(py)
        } else {
            None
        }
    }

    pub fn emit_push(&self, event: &str, vault: Option<&str>, data: Value) {
        let (seq, sink) = {
            let mut g = self.inner.lock().unwrap();
            g.event_seq += 1;
            (g.event_seq, g.push_sink.clone())
        };
        if let Some(s) = sink {
            s(json!({
                "event": event,
                "seq": seq,
                "ts": now_unix_secs(),
                "vault": vault,
                "data": data,
            }));
        }
    }

    fn query_bounded_sqlite(vault: &Path) -> (HashMap<String, String>, HashMap<String, i64>) {
        let mut ws_map = HashMap::new();
        let mut ocr_counts = HashMap::new();
        let db_path = resolve_engine_dir(vault).join("indexes").join("paperforge.db");
        let Some(conn) = open_readonly_db(&db_path) else {
            return (ws_map, ocr_counts);
        };
        if let Ok(mut st) = conn.prepare(&format!(
            "SELECT zotero_key, workspace_relpath FROM workspace_registry LIMIT {MAX_WORKSPACES_PER_VAULT}"
        )) {
            if let Ok(rows) = st.query_map([], |r| Ok((r.get::<_, String>(0)?, r.get::<_, String>(1)?))) {
                for r in rows.flatten() {
                    ws_map.insert(r.0, r.1);
                }
            }
        }
        if let Ok(mut st) = conn.prepare("SELECT salvage_action, COUNT(*) FROM ocr_catalog GROUP BY salvage_action") {
            if let Ok(rows) = st.query_map([], |r| Ok((r.get::<_, String>(0)?, r.get::<_, i64>(1)?))) {
                for r in rows.flatten() {
                    ocr_counts.insert(r.0, r.1);
                }
            }
        }
        (ws_map, ocr_counts)
    }

    pub fn get_or_refresh_vault(&self, vault: &Path) -> VaultCacheEntry {
        let vkey = Self::norm_vault(vault);
        let (seq, _) = read_state_seq(vault);
        {
            let mut g = self.inner.lock().unwrap();
            if let Some(pos) = g.vault_lru.iter().position(|e| e.vault_key == vkey) {
                if g.vault_lru[pos].last_seq == seq {
                    let mut entry = g.vault_lru.remove(pos).unwrap();
                    entry.hits += 1;
                    entry.last_access = Instant::now();
                    let cloned = entry.clone();
                    g.vault_lru.push_back(entry);
                    return cloned;
                }
            }
        }

        let (ws_map, ocr_counts) = Self::query_bounded_sqlite(vault);
        let (out_entry, prev_seq) = {
            let mut g = self.inner.lock().unwrap();
            if let Some(pos) = g.vault_lru.iter().position(|e| e.vault_key == vkey) {
                let mut entry = g.vault_lru.remove(pos).unwrap();
                let prev = entry.last_seq;
                entry.misses += 1;
                entry.last_seq = seq;
                entry.workspace_map = ws_map;
                entry.ocr_salvage_counts = ocr_counts;
                entry.refreshed_at = now_unix_secs();
                entry.last_access = Instant::now();
                let cloned = entry.clone();
                g.vault_lru.push_back(entry);
                (cloned, Some(prev))
            } else {
                while g.vault_lru.len() >= MAX_CACHED_VAULTS {
                    g.vault_lru.pop_front();
                }
                let entry = VaultCacheEntry {
                    vault_key: vkey.clone(),
                    last_seq: seq,
                    workspace_map: ws_map,
                    ocr_salvage_counts: ocr_counts,
                    hits: 0,
                    misses: 1,
                    refreshed_at: now_unix_secs(),
                    last_access: Instant::now(),
                };
                let cloned = entry.clone();
                g.vault_lru.push_back(entry);
                (cloned, None)
            }
        };

        if let Some(prev) = prev_seq {
            if prev >= 0 && prev != seq {
                self.emit_push("state.changed", Some(&vkey), json!({ "seq": seq }));
            }
        }
        self.write_heartbeat(vault);
        out_entry
    }

    /// Resolve a `zotero_key` to its `workspace_relpath`: hits bounded in-memory LRU
    /// first (`<= 2048` entries), and falls back to a direct SQLite point lookup on
    /// cache miss so large vaults (> 2048 papers) never lose keys.
    pub fn resolve_workspace_key(&self, vault: &Path, key: &str) -> (Option<String>, i64) {
        let c = self.get_or_refresh_vault(vault);
        if let Some(rel) = c.workspace_map.get(key) {
            return (Some(rel.clone()), c.last_seq);
        }
        // Only hit SQLite on cache miss when cache may be truncated or empty
        if c.workspace_map.len() >= MAX_WORKSPACES_PER_VAULT || c.workspace_map.is_empty() {
            let db_path = resolve_engine_dir(vault).join("indexes").join("paperforge.db");
            if let Some(conn) = open_readonly_db(&db_path) {
                if let Ok(rel) = conn.query_row(
                    "SELECT workspace_relpath FROM workspace_registry WHERE zotero_key = ?1 LIMIT 1",
                    [key],
                    |r| r.get::<_, String>(0),
                ) {
                    if !rel.is_empty() {
                        return (Some(rel), c.last_seq);
                    }
                }
            }
        }
        (None, c.last_seq)
    }

    pub fn get_or_build_base_snapshot(&self, vault: &Path) -> (i32, String, String) {
        let vkey = Self::norm_vault(vault);
        let fp = crate::query_ops::base_snapshot_fingerprint(vault);
        {
            let mut g = self.inner.lock().unwrap();
            if let Some(pos) = g
                .base_snapshot_cache
                .iter()
                .position(|c| c.vault_key == vkey && c.fingerprint == fp)
            {
                let mut entry = g.base_snapshot_cache.remove(pos).unwrap();
                entry.last_access = Instant::now();
                let res = entry.payload.clone();
                g.base_snapshot_cache.push_back(entry);
                return res;
            }
        }
        let fresh = crate::query_ops::handle_base_snapshot(vault);
        let mut g = self.inner.lock().unwrap();
        if let Some(pos) = g
            .base_snapshot_cache
            .iter()
            .position(|c| c.vault_key == vkey)
        {
            g.base_snapshot_cache.remove(pos);
        }
        while g.base_snapshot_cache.len() >= MAX_SNAPSHOT_CACHE {
            g.base_snapshot_cache.pop_front();
        }
        g.base_snapshot_cache.push_back(CachedBaseSnapshot {
            vault_key: vkey,
            fingerprint: fp,
            payload: fresh.clone(),
            last_access: Instant::now(),
        });
        fresh
    }

    pub fn invalidate_vault(&self, vault: Option<&Path>) -> usize {
        let mut g = self.inner.lock().unwrap();
        if let Some(v) = vault {
            let vkey = Self::norm_vault(v);
            g.base_snapshot_cache.retain(|c| c.vault_key != vkey);
            if let Some(pos) = g.vault_lru.iter().position(|e| e.vault_key == vkey) {
                g.vault_lru.remove(pos);
                return 1;
            }
            0
        } else {
            let n = g.vault_lru.len();
            g.vault_lru.clear();
            g.base_snapshot_cache.clear();
            n
        }
    }

    pub fn trim_idle_memory(&self, idle_secs: f64) -> Value {
        let mut evicted = 0usize;
        if idle_secs >= 120.0 {
            let mut g = self.inner.lock().unwrap();
            if g.active_jobs.is_empty() {
                let before = g.vault_lru.len();
                g.vault_lru
                    .retain(|e| e.last_access.elapsed().as_secs_f64() < 120.0);
                evicted = before.saturating_sub(g.vault_lru.len());
                g.base_snapshot_cache
                    .retain(|c| c.last_access.elapsed().as_secs_f64() < 120.0);
            }
        }
        json!({ "evicted_vaults": evicted, "gc_collected": 0 })
    }

    pub fn push_notice_traced(
        &self,
        level: &str,
        code: &str,
        title: &str,
        detail: &str,
        vault: Option<&Path>,
        trace_id: Option<&str>,
    ) -> Value {
        let norm_v = vault.map(Self::norm_vault);
        let norm_lvl = match level {
            "info" | "success" | "warning" | "error" => level,
            _ => "info",
        };
        let tid = self.next_trace_id(trace_id);
        let notice = {
            let mut g = self.inner.lock().unwrap();
            g.notice_counter += 1;
            let nid = format!("ntc_{}_{}", std::process::id(), g.notice_counter);
            let n = json!({
                "notice_id": nid,
                "trace_id": tid,
                "level": norm_lvl,
                "code": code,
                "title": title,
                "detail": detail,
                "vault": norm_v,
                "created_at": now_unix_secs(),
                "acked": false,
            });
            if g.notices.len() >= MAX_NOTICES {
                g.notices.pop_front();
            }
            g.notices.push_back(n.clone());
            n
        };
        self.emit_push("notice.push", norm_v.as_deref(), notice.clone());
        if let Some(v) = vault {
            self.write_heartbeat(v);
        }
        notice
    }

    pub fn list_notices(&self, vault: Option<&Path>, include_acked: bool) -> Vec<Value> {
        let vkey = vault.map(Self::norm_vault);
        let g = self.inner.lock().unwrap();
        g.notices
            .iter()
            .filter(|n| {
                if !include_acked && n.get("acked").and_then(|v| v.as_bool()) == Some(true) {
                    return false;
                }
                if let Some(ref vk) = vkey {
                    if let Some(nv) = n.get("vault").and_then(|v| v.as_str()) {
                        return nv == vk;
                    }
                }
                true
            })
            .cloned()
            .collect()
    }

    pub fn ack_notice(&self, notice_id: &str) -> bool {
        let mut g = self.inner.lock().unwrap();
        for n in g.notices.iter_mut() {
            if n.get("notice_id").and_then(|v| v.as_str()) == Some(notice_id) {
                if let Some(obj) = n.as_object_mut() {
                    obj.insert("acked".into(), Value::Bool(true));
                    return true;
                }
            }
        }
        false
    }

    pub fn has_exclusive_barrier(&self, vault: &Path) -> Option<String> {
        let vkey = Self::norm_vault(vault);
        self.inner
            .lock()
            .unwrap()
            .exclusive_barriers
            .get(&vkey)
            .cloned()
    }

    pub fn acquire_exclusive_barrier(&self, vault: &Path, reason: &str) {
        let vkey = Self::norm_vault(vault);
        let to_cancel: Vec<String> = {
            let mut g = self.inner.lock().unwrap();
            g.exclusive_barriers.insert(vkey.clone(), reason.to_string());
            g.active_jobs
                .iter()
                .filter_map(|(jid, job_arc)| {
                    let j = job_arc.lock().unwrap();
                    if j.vault == vkey && !j.status.is_terminal() {
                        Some(jid.clone())
                    } else {
                        None
                    }
                })
                .collect()
        };
        for jid in to_cancel {
            let _ = self.cancel_job(&jid, 1500, true);
        }
        self.write_heartbeat(vault);
    }

    pub fn release_exclusive_barrier(&self, vault: &Path) {
        let vkey = Self::norm_vault(vault);
        self.inner.lock().unwrap().exclusive_barriers.remove(&vkey);
        self.write_heartbeat(vault);
    }

    fn default_argv_for_kind(kind: &str, priority_key: Option<&str>, backfill_ocr: bool) -> Result<Vec<String>, String> {
        match kind {
            "sync" => Ok(vec!["sync".into(), "--json".into()]),
            "ocr" => Ok(vec!["ocr".into(), "--stream".into()]),
            "embed" => Ok(vec!["embed".into(), "build".into(), "--stream".into()]),
            "upgrade.heal" => {
                let mut cmd = vec!["upgrade".into(), "--heal".into(), "--json".into()];
                if let Some(pk) = priority_key.filter(|s| !s.is_empty()) {
                    cmd.push("--priority-key".into());
                    cmd.push(pk.into());
                }
                if backfill_ocr {
                    cmd.push("--backfill-ocr".into());
                }
                Ok(cmd)
            }
            other => Err(format!("Unsupported job kind: {other}")),
        }
    }

    pub fn submit_runtime_job(&self, vault: Option<&Path>, action: &str, version: &str) -> Value {
        self.submit_runtime_job_with_opts(
            vault,
            action,
            version,
            crate::runtime_ops::RuntimeInstallOptions::default(),
        )
    }

    pub fn submit_runtime_job_with_opts(
        &self,
        vault: Option<&Path>,
        action: &str,
        version: &str,
        opts: crate::runtime_ops::RuntimeInstallOptions,
    ) -> Value {
        let vkey = vault
            .map(Self::norm_vault)
            .unwrap_or_else(|| "global".to_string());
        let act = match action {
            "install" | "update" | "repair" => action.to_string(),
            _ => "install".to_string(),
        };
        let kind = format!("runtime.{act}");
        let ver = if version.trim().is_empty() {
            PF_VERSION.to_string()
        } else {
            version.trim().to_string()
        };

        let trace_id = self.next_trace_id(None);
        let cancel_flag = Arc::new(AtomicBool::new(false));
        let runtime_child_pid = Arc::new(AtomicU32::new(0));
        let (job_id, job_arc) = {
            let mut g = self.inner.lock().unwrap();
            for active in g.active_jobs.values() {
                let aj = active.lock().unwrap();
                if aj.kind.starts_with("runtime.") && aj.status == JobStatus::Running {
                    return json!({
                        "accepted": true,
                        "coalesced": true,
                        "job": aj.to_json(),
                    });
                }
            }
            g.job_counter += 1;
            let jid = format!("job_{}_{}", std::process::id(), g.job_counter);
            let mut rec_val = JobRecord {
                job_id: jid.clone(),
                trace_id: trace_id.clone(),
                vault: vkey.clone(),
                kind: kind.clone(),
                scope_key: "runtime".into(),
                source: "runtime".into(),
                stream_id: None,
                status: JobStatus::Queued,
                current: 0,
                total: 5,
                phase: "starting".into(),
                item_id: ver.clone(),
                priority_key: None,
                started_at: now_unix_secs(),
                finished_at: None,
                exit_code: None,
                error: String::new(),
                stderr_tail: String::new(),
                pid: Some(std::process::id()),
                child: None,
                cancel_flag: Some(cancel_flag.clone()),
                runtime_child_pid: Some(runtime_child_pid.clone()),
            };
            let _ = rec_val.transition(JobStatus::Running);
            let rec = Arc::new(Mutex::new(rec_val));
            g.active_jobs.insert(jid.clone(), rec.clone());
            (jid, rec)
        };

        let snap = job_arc.lock().unwrap().to_json();
        self.emit_push("task.updated", Some(&vkey), snap.clone());

        let daemon_clone = self.clone();
        let job_worker = job_arc.clone();
        let tid_worker = trace_id.clone();
        let cf_worker = cancel_flag.clone();
        let rpid_worker = runtime_child_pid.clone();
        let opts_worker = opts;
        thread::spawn(move || {
            let v_opt = if vkey == "global" { None } else { Some(vkey.as_str()) };
            let res = crate::runtime_ops::install_runtime_native_with_opts(
                &act,
                &ver,
                &opts_worker,
                Some(cf_worker.as_ref()),
                Some(rpid_worker.as_ref()),
                |phase, cur, tot| {
                    let ev_snap = {
                        let mut j = job_worker.lock().unwrap();
                        if !j.status.is_terminal() {
                            j.phase = phase.to_string();
                            j.current = cur;
                            j.total = tot;
                        }
                        j.to_json()
                    };
                    daemon_clone.emit_push("task.updated", v_opt, ev_snap);
                },
            );

            let (final_status, err_msg, final_snap) = {
                let mut j = job_worker.lock().unwrap();
                j.finished_at = Some(now_unix_secs());
                match res {
                    Ok(_) if !cf_worker.load(Ordering::SeqCst) && j.status != JobStatus::Cancelling => {
                        let _ = j.transition(JobStatus::Succeeded);
                        j.current = 5;
                        j.exit_code = Some(0);
                        (JobStatus::Succeeded, String::new(), j.to_json())
                    }
                    Ok(_) => {
                        let _ = j.transition(JobStatus::Cancelled);
                        j.exit_code = Some(130);
                        (JobStatus::Cancelled, String::new(), j.to_json())
                    }
                    Err(_e) if cf_worker.load(Ordering::SeqCst) || j.status == JobStatus::Cancelling => {
                        let _ = j.transition(JobStatus::Cancelled);
                        j.exit_code = Some(130);
                        j.error = "cancelled".into();
                        (JobStatus::Cancelled, String::new(), j.to_json())
                    }
                    Err(e) => {
                        let _ = j.transition(JobStatus::Failed);
                        j.exit_code = Some(1);
                        j.error = e.clone();
                        (JobStatus::Failed, e, j.to_json())
                    }
                }
            };

            {
                let mut g = daemon_clone.inner.lock().unwrap();
                g.active_jobs.remove(&job_id);
                if g.recent_jobs.len() >= MAX_RECENT_JOBS {
                    g.recent_jobs.pop_front();
                }
                g.recent_jobs.push_back(final_snap.clone());
            }

            daemon_clone.emit_push("task.updated", v_opt, final_snap);
            match final_status {
                JobStatus::Succeeded => {
                    daemon_clone.push_notice_traced(
                        "success",
                        "runtime.install.done",
                        "Python compute engine is ready",
                        "Background sync and OCR fulltext environment are ready.",
                        vault_path_opt(&vkey),
                        Some(&tid_worker),
                    );
                }
                JobStatus::Failed => {
                    daemon_clone.push_notice_traced(
                        "warning",
                        "runtime.install.failed",
                        "Runtime setup did not complete",
                        &summarize_stderr_line(&err_msg, 1),
                        vault_path_opt(&vkey),
                        Some(&tid_worker),
                    );
                }
                _ => {}
            }
        });

        json!({ "accepted": true, "coalesced": false, "trace_id": trace_id, "job": snap })
    }

    pub fn submit_job(
        &self,
        vault: &Path,
        kind: &str,
        custom_argv: Option<Vec<String>>,
        priority_key: Option<String>,
        backfill_ocr: bool,
    ) -> Value {
        let vkey = Self::norm_vault(vault);
        let Some(py_exe) = Self::resolve_python_exe() else {
            return json!({
                "accepted": false,
                "reason": "NO_PYTHON",
                "error": "PaperForge Python worker runtime not installed yet.",
            });
        };

        let resolved_argv = match custom_argv {
            Some(a) if !a.is_empty() => a,
            _ => match Self::default_argv_for_kind(kind, priority_key.as_deref(), backfill_ocr) {
                Ok(a) => a,
                Err(e) => return json!({ "accepted": false, "reason": "invalid_kind", "error": e }),
            },
        };
        let (_, scope_key) = infer_kind_and_scope(&resolved_argv, Some(kind), priority_key.as_deref());
        let trace_id = self.next_trace_id(None);

        let (job_id, job_arc) = {
            let mut g = self.inner.lock().unwrap();
            if let Some(barrier) = g.exclusive_barriers.get(&vkey) {
                return json!({
                    "accepted": false,
                    "reason": "vault_upgrade_barrier_active",
                    "barrier": barrier,
                });
            }
            let mut coalesced: Option<(Value, Option<String>)> = None;
            for active in g.active_jobs.values() {
                let aj = active.lock().unwrap();
                let same_bucket = aj.vault == vkey
                    && aj.kind == kind
                    && (kind == "upgrade.heal" || aj.scope_key == scope_key)
                    && aj.status == JobStatus::Running;
                if same_bucket {
                    let mut new_prio = None;
                    if kind == "upgrade.heal" {
                        if let Some(ref pk) = priority_key {
                            if Some(pk) != aj.priority_key.as_ref() {
                                new_prio = Some(pk.clone());
                            }
                        }
                    }
                    coalesced = Some((aj.to_json(), new_prio));
                    break;
                }
            }
            if let Some((snap_json, maybe_prio)) = coalesced {
                if let Some(pk) = maybe_prio {
                    g.followup_heal_priority.insert(vkey.clone(), pk);
                }
                return json!({
                    "accepted": true,
                    "coalesced": true,
                    "job": snap_json,
                });
            }
            g.job_counter += 1;
            let jid = format!("job_{}_{}", std::process::id(), g.job_counter);
            let rec = Arc::new(Mutex::new(JobRecord {
                job_id: jid.clone(),
                trace_id: trace_id.clone(),
                vault: vkey.clone(),
                kind: kind.to_string(),
                scope_key: scope_key.clone(),
                source: "job.submit".into(),
                stream_id: None,
                status: JobStatus::Queued,
                current: 0,
                total: 0,
                phase: String::new(),
                item_id: String::new(),
                priority_key,
                started_at: now_unix_secs(),
                finished_at: None,
                exit_code: None,
                error: String::new(),
                stderr_tail: String::new(),
                pid: None,
                child: None,
                cancel_flag: None,
                runtime_child_pid: None,
            }));
            g.active_jobs.insert(jid.clone(), rec.clone());
            (jid, rec)
        };

        let mut cmd = Command::new(&py_exe);
        cmd.args(["-m", "paperforge", "--vault", &vkey])
            .args(&resolved_argv)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        if Path::new(&vkey).is_dir() {
            cmd.current_dir(&vkey);
        }
        configure_worker_command(&mut cmd);

        let mut child = match cmd.spawn() {
            Ok(c) => c,
            Err(e) => {
                let mut g = self.inner.lock().unwrap();
                g.active_jobs.remove(&job_id);
                return json!({ "accepted": false, "reason": "spawn_failed", "error": e.to_string() });
            }
        };
        attach_child_to_job(&child);

        let stdout_pipe = child.stdout.take();
        let stderr_pipe = child.stderr.take();
        let snap = {
            let mut j = job_arc.lock().unwrap();
            let _ = j.transition(JobStatus::Running);
            j.pid = Some(child.id());
            j.child = Some(child);
            j.to_json()
        };

        self.emit_push("task.updated", Some(&vkey), snap.clone());
        self.write_heartbeat(Path::new(&vkey));

        if let Some(err_pipe) = stderr_pipe {
            let job_err = job_arc.clone();
            thread::spawn(move || {
                let reader = BufReader::new(err_pipe);
                for line in reader.lines().map_while(Result::ok) {
                    let mut j = job_err.lock().unwrap();
                    append_stderr_tail(&mut j.stderr_tail, &line, 8000);
                }
            });
        }

        let daemon_clone = self.clone();
        let job_out = job_arc.clone();
        let tid_out = trace_id.clone();
        thread::spawn(move || {
            if let Some(out_pipe) = stdout_pipe {
                let reader = BufReader::new(out_pipe);
                for line in reader.lines().map_while(Result::ok) {
                    let trimmed = line.trim();
                    if !trimmed.starts_with('{') {
                        continue;
                    }
                    let Ok(ev) = serde_json::from_str::<Value>(trimmed) else { continue };
                    if ev.get("schema_version").and_then(|v| v.as_i64()) != Some(1) {
                        continue;
                    }
                    let (v_str, snap_ev) = {
                        let mut j = job_out.lock().unwrap();
                        if let Some(c) = ev.get("current").and_then(|v| v.as_i64()) {
                            j.current = c;
                        }
                        if let Some(t) = ev.get("total").and_then(|v| v.as_i64()) {
                            j.total = t;
                        }
                        if let Some(p) = ev.get("phase").and_then(|v| v.as_str()) {
                            j.phase = p.to_string();
                        }
                        if let Some(id) = ev.get("item_id").and_then(|v| v.as_str()) {
                            j.item_id = id.to_string();
                        }
                        if ev.get("event").and_then(|v| v.as_str()) == Some("cancelled") {
                            let _ = j.transition(JobStatus::Cancelled);
                        }
                        (j.vault.clone(), j.to_json())
                    };
                    daemon_clone.emit_push("task.updated", Some(&v_str), snap_ev);
                }
            }

            let rc = {
                let mut child_opt = job_out.lock().unwrap().child.take();
                if let Some(ref mut c) = child_opt {
                    c.wait().ok().and_then(|s| s.code()).unwrap_or(1)
                } else {
                    1
                }
            };

            let (vault_str, kind_str, final_status, err_msg, final_snap) = {
                let mut j = job_out.lock().unwrap();
                j.exit_code = Some(rc);
                j.finished_at = Some(now_unix_secs());
                if !j.status.is_terminal() {
                    if j.status == JobStatus::Cancelling || rc == 130 {
                        let _ = j.transition(JobStatus::Cancelled);
                    } else if rc == 0 {
                        let _ = j.transition(JobStatus::Succeeded);
                    } else {
                        let _ = j.transition(JobStatus::Failed);
                        j.error = summarize_stderr_line(&j.stderr_tail, rc);
                    }
                }
                (
                    j.vault.clone(),
                    j.kind.clone(),
                    j.status,
                    j.error.clone(),
                    j.to_json(),
                )
            };

            let followup_prio = {
                let mut g = daemon_clone.inner.lock().unwrap();
                g.active_jobs.remove(&job_id);
                if g.recent_jobs.len() >= MAX_RECENT_JOBS {
                    g.recent_jobs.pop_front();
                }
                g.recent_jobs.push_back(final_snap.clone());
                if kind_str == "upgrade.heal" && final_status == JobStatus::Succeeded {
                    g.followup_heal_priority.remove(&vault_str)
                } else {
                    None
                }
            };

            daemon_clone.emit_push("task.updated", Some(&vault_str), final_snap);
            let v_path = PathBuf::from(&vault_str);
            let _ = daemon_clone.get_or_refresh_vault(&v_path);
            daemon_clone.write_heartbeat(&v_path);

            if final_status == JobStatus::Failed {
                daemon_clone.push_notice_traced(
                    "warning",
                    &format!("job.{kind_str}.failed"),
                    &format!("Background task did not complete ({kind_str})"),
                    &err_msg,
                    Some(&v_path),
                    Some(&tid_out),
                );
            } else if kind_str == "upgrade.heal" && final_status == JobStatus::Succeeded {
                daemon_clone.push_notice_traced(
                    "success",
                    "job.upgrade.heal.done",
                    "Background library organization completed",
                    "",
                    Some(&v_path),
                    Some(&tid_out),
                );
            }

            if let Some(pk) = followup_prio {
                let _ = daemon_clone.submit_job(&v_path, "upgrade.heal", None, Some(pk), false);
            }
        });

        json!({ "accepted": true, "coalesced": false, "trace_id": trace_id, "job": snap })
    }

    /// Unified streaming job supervisor (`job.stream`): runs interactive long tasks
    /// (OCR, Embedding, Sync, Setup) under the exact same `active_jobs` FSM, OS Job
    /// Object death cleanup, `task.updated` / `notice.push` telemetry, and cooperative
    /// cancellation (`PAPERFORGE_STOP` + grace escalation) while forwarding every
    /// stdout NDJSON line back to the requesting client via `stream.chunk` / `stream.end`.
    #[allow(clippy::too_many_arguments)]
    pub fn submit_stream_job(
        &self,
        vault: &Path,
        argv: Vec<String>,
        stream_id: String,
        caller_trace: Option<&str>,
        close_stdin: bool,
        on_frame: PushSink,
    ) -> Value {
        let vkey = Self::norm_vault(vault);
        let trace_id = self.next_trace_id(caller_trace);
        let Some(py_exe) = Self::resolve_python_exe() else {
            return json!({
                "accepted": false,
                "reason": "NO_PYTHON",
                "trace_id": trace_id,
                "error": "PaperForge Python worker runtime not installed yet.",
            });
        };
        if argv.is_empty() {
            return json!({
                "accepted": false,
                "reason": "invalid_argv",
                "trace_id": trace_id,
                "error": "job.stream requires non-empty argv",
            });
        }

        let (kind, scope_key) = infer_kind_and_scope(&argv, None, None);

        let (job_id, job_arc) = {
            let mut g = self.inner.lock().unwrap();
            if let Some(barrier) = g.exclusive_barriers.get(&vkey) {
                return json!({
                    "accepted": false,
                    "reason": "vault_upgrade_barrier_active",
                    "trace_id": trace_id,
                    "barrier": barrier,
                });
            }
            g.job_counter += 1;
            let jid = format!("job_{}_{}", std::process::id(), g.job_counter);
            let rec = Arc::new(Mutex::new(JobRecord {
                job_id: jid.clone(),
                trace_id: trace_id.clone(),
                vault: vkey.clone(),
                kind: kind.clone(),
                scope_key: scope_key.clone(),
                source: "stream".into(),
                stream_id: Some(stream_id.clone()),
                status: JobStatus::Queued,
                current: 0,
                total: 0,
                phase: String::new(),
                item_id: String::new(),
                priority_key: None,
                started_at: now_unix_secs(),
                finished_at: None,
                exit_code: None,
                error: String::new(),
                stderr_tail: String::new(),
                pid: None,
                child: None,
                cancel_flag: None,
                runtime_child_pid: None,
            }));
            g.active_jobs.insert(jid.clone(), rec.clone());
            (jid, rec)
        };

        let mut cmd = Command::new(&py_exe);
        cmd.args(["-m", "paperforge", "--vault", &vkey])
            .args(&argv)
            .stdin(if close_stdin { Stdio::null() } else { Stdio::piped() })
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        if Path::new(&vkey).is_dir() {
            cmd.current_dir(&vkey);
        }
        configure_worker_command(&mut cmd);

        let mut child = match cmd.spawn() {
            Ok(c) => c,
            Err(e) => {
                let mut g = self.inner.lock().unwrap();
                g.active_jobs.remove(&job_id);
                return json!({
                    "accepted": false,
                    "reason": "spawn_failed",
                    "trace_id": trace_id,
                    "error": e.to_string(),
                });
            }
        };
        attach_child_to_job(&child);

        let stdout_pipe = child.stdout.take();
        let stderr_pipe = child.stderr.take();
        let snap = {
            let mut j = job_arc.lock().unwrap();
            let _ = j.transition(JobStatus::Running);
            j.pid = Some(child.id());
            j.child = Some(child);
            j.to_json()
        };

        self.emit_push("task.updated", Some(&vkey), snap.clone());
        self.write_heartbeat(Path::new(&vkey));

        let err_handle = stderr_pipe.map(|err_pipe| {
            let job_err = job_arc.clone();
            thread::spawn(move || {
                let reader = BufReader::new(err_pipe);
                for line in reader.lines().map_while(Result::ok) {
                    let mut j = job_err.lock().unwrap();
                    append_stderr_tail(&mut j.stderr_tail, &line, 8000);
                }
            })
        });

        let daemon_clone = self.clone();
        let job_out = job_arc.clone();
        let jid_out = job_id.clone();
        let tid_out = trace_id.clone();
        let sid_out = stream_id.clone();
        thread::spawn(move || {
            let mut saw_terminal_ev = false;
            if let Some(out_pipe) = stdout_pipe {
                let reader = BufReader::new(out_pipe);
                for line in reader.lines().map_while(Result::ok) {
                    on_frame(json!({
                        "event": "stream.chunk",
                        "stream_id": sid_out,
                        "job_id": jid_out,
                        "trace_id": tid_out,
                        "line": line,
                    }));

                    let trimmed = line.trim();
                    if !trimmed.starts_with('{') {
                        continue;
                    }
                    let Ok(ev) = serde_json::from_str::<Value>(trimmed) else { continue };
                    if ev.get("schema_version").and_then(|v| v.as_i64()) != Some(1) {
                        continue;
                    }
                    let ev_name = ev.get("event").and_then(|v| v.as_str()).unwrap_or("");
                    if matches!(ev_name, "result" | "error" | "cancelled") {
                        saw_terminal_ev = true;
                    }
                    let (v_str, snap_ev) = {
                        let mut j = job_out.lock().unwrap();
                        if let Some(c) = ev.get("current").and_then(|v| v.as_i64()) {
                            j.current = c;
                        }
                        if let Some(t) = ev.get("total").and_then(|v| v.as_i64()) {
                            j.total = t;
                        }
                        if let Some(p) = ev.get("phase").and_then(|v| v.as_str()) {
                            j.phase = p.to_string();
                        }
                        if let Some(id) = ev.get("item_id").and_then(|v| v.as_str()) {
                            j.item_id = id.to_string();
                        }
                        if ev_name == "cancelled" {
                            let _ = j.transition(JobStatus::Cancelled);
                        }
                        (j.vault.clone(), j.to_json())
                    };
                    daemon_clone.emit_push("task.updated", Some(&v_str), snap_ev);
                }
            }

            let rc = {
                let mut child_opt = job_out.lock().unwrap().child.take();
                if let Some(ref mut c) = child_opt {
                    c.wait().ok().and_then(|s| s.code()).unwrap_or(1)
                } else {
                    1
                }
            };
            if let Some(eh) = err_handle {
                let _ = eh.join();
            }

            let (vault_str, final_status, stderr_full, final_snap) = {
                let mut j = job_out.lock().unwrap();
                j.exit_code = Some(rc);
                j.finished_at = Some(now_unix_secs());
                if !j.status.is_terminal() {
                    if (j.status == JobStatus::Cancelling && !saw_terminal_ev) || rc == 130 {
                        let _ = j.transition(JobStatus::Cancelled);
                    } else if rc == 0 {
                        let _ = j.transition(JobStatus::Succeeded);
                    } else {
                        let _ = j.transition(JobStatus::Failed);
                        j.error = summarize_stderr_line(&j.stderr_tail, rc);
                    }
                }
                (
                    j.vault.clone(),
                    j.status,
                    j.stderr_tail.clone(),
                    j.to_json(),
                )
            };

            {
                let mut g = daemon_clone.inner.lock().unwrap();
                g.active_jobs.remove(&jid_out);
                if g.recent_jobs.len() >= MAX_RECENT_JOBS {
                    g.recent_jobs.pop_front();
                }
                g.recent_jobs.push_back(final_snap.clone());
            }

            on_frame(json!({
                "event": "stream.end",
                "stream_id": sid_out,
                "job_id": jid_out,
                "trace_id": tid_out,
                "exit_code": rc,
                "cancelled": final_status == JobStatus::Cancelled,
                "stderr": stderr_full,
            }));

            daemon_clone.emit_push("task.updated", Some(&vault_str), final_snap);
            let v_path = PathBuf::from(&vault_str);
            let _ = daemon_clone.get_or_refresh_vault(&v_path);
            daemon_clone.write_heartbeat(&v_path);
            // Note: Interactive `job.stream` callers already receive `stream.end`
            // (exit_code + stderr) and own user-facing failure feedback. Do NOT emit
            // a redundant `notice.push` here to prevent duplicate top-right Notices.
        });

        json!({
            "accepted": true,
            "job_id": job_id,
            "stream_id": stream_id,
            "trace_id": trace_id,
            "job": snap,
        })
    }

    pub fn cancel_job(&self, job_or_stream_id: &str, grace_ms: u64, wait: bool) -> Value {
        let (resolved_id, job_arc) = {
            let g = self.inner.lock().unwrap();
            if let Some(ja) = g.active_jobs.get(job_or_stream_id).cloned() {
                (job_or_stream_id.to_string(), ja)
            } else if let Some((jid, ja)) = g.active_jobs.iter().find(|(_, arc)| {
                arc.lock()
                    .ok()
                    .and_then(|j| j.stream_id.clone())
                    .as_deref()
                    == Some(job_or_stream_id)
            }) {
                (jid.clone(), ja.clone())
            } else {
                return json!({ "ok": false, "reason": "not_found", "job_id": job_or_stream_id });
            }
        };

        let (vault_str, snap, transitioned, is_runtime_job, rt_child_pid) = {
            let mut j = job_arc.lock().unwrap();
            let ok = j.transition(JobStatus::Cancelling).is_ok();
            let mut rt_pid = 0u32;
            if ok {
                if let Some(ref cf) = j.cancel_flag {
                    cf.store(true, Ordering::SeqCst);
                }
                if let Some(ref rpid) = j.runtime_child_pid {
                    rt_pid = rpid.load(Ordering::SeqCst);
                }
                if let Some(ref mut c) = j.child {
                    if let Some(ref mut sin) = c.stdin {
                        let _ = sin.write_all(b"PAPERFORGE_STOP\n");
                        let _ = sin.flush();
                    }
                }
            }
            (
                j.vault.clone(),
                j.to_json(),
                ok,
                j.source == "runtime",
                rt_pid,
            )
        };
        if !transitioned {
            return json!({
                "ok": false,
                "reason": "already_terminal",
                "job_id": resolved_id,
                "status": snap["status"],
            });
        }
        if is_runtime_job && rt_child_pid != 0 {
            kill_pid_tree(rt_child_pid);
        }
        self.emit_push("task.updated", Some(&vault_str), snap);

        let escalate = move || {
            let deadline = Instant::now() + Duration::from_millis(grace_ms.max(200));
            while Instant::now() < deadline {
                let done = {
                    let mut j = job_arc.lock().unwrap();
                    if is_runtime_job {
                        if let Some(ref rpid) = j.runtime_child_pid {
                            let p = rpid.load(Ordering::SeqCst);
                            if p != 0 {
                                kill_pid_tree(p);
                            }
                        }
                        j.status.is_terminal()
                    } else {
                        match j.child.as_mut() {
                            Some(c) => matches!(c.try_wait(), Ok(Some(_))),
                            None => true,
                        }
                    }
                };
                if done {
                    return;
                }
                thread::sleep(Duration::from_millis(30));
            }
            let mut j = job_arc.lock().unwrap();
            if is_runtime_job {
                if !j.status.is_terminal() {
                    let _ = j.transition(JobStatus::Cancelled);
                    j.finished_at = Some(now_unix_secs());
                    j.exit_code = Some(130);
                }
            } else if let Some(ref mut c) = j.child {
                kill_process_tree(c);
            }
        };

        if wait {
            escalate();
        } else {
            thread::spawn(escalate);
        }
        json!({ "ok": true, "job_id": resolved_id, "status": "cancelling" })
    }

    pub fn cancel_all_jobs(&self, grace_ms: u64) {
        let (ids, delegated): (Vec<String>, Vec<u32>) = {
            let g = self.inner.lock().unwrap();
            (
                g.active_jobs.keys().cloned().collect(),
                g.delegated_pids.iter().copied().collect(),
            )
        };
        for jid in ids {
            let _ = self.cancel_job(&jid, grace_ms, true);
        }
        for pid in delegated {
            kill_pid_tree(pid);
        }
    }

    pub fn list_jobs(&self, vault: Option<&Path>, include_recent: bool) -> Value {
        let vkey = vault.map(Self::norm_vault);
        let g = self.inner.lock().unwrap();
        let active: Vec<Value> = g
            .active_jobs
            .values()
            .filter_map(|ja| {
                let j = ja.lock().unwrap();
                if vkey.as_deref().is_none_or(|vk| j.vault == vk) {
                    Some(j.to_json())
                } else {
                    None
                }
            })
            .collect();
        let recent: Vec<Value> = if include_recent {
            g.recent_jobs
                .iter()
                .filter(|r| {
                    vkey.as_deref().is_none_or(|vk| {
                        r.get("vault").and_then(|v| v.as_str()) == Some(vk)
                    })
                })
                .cloned()
                .collect()
        } else {
            Vec::new()
        };
        json!({ "active": active, "recent": recent })
    }

    pub fn has_active_jobs(&self) -> bool {
        !self.inner.lock().unwrap().active_jobs.is_empty()
    }

    pub fn check_parent_alive(&self) -> bool {
        let (ppid, init_ppid) = {
            let g = self.inner.lock().unwrap();
            (g.parent_pid, g.initial_ppid)
        };
        match ppid {
            Some(p) if p > 0 => is_pid_alive(p, init_ppid),
            _ => true,
        }
    }

    pub fn write_heartbeat(&self, vault: &Path) {
        let indexes_dir = resolve_engine_dir(vault).join("indexes");
        if !indexes_dir.is_dir() {
            return;
        }
        let vkey = Self::norm_vault(vault);
        let (parent_pid, active, exclusive_barrier, recent_notices) = {
            let g = self.inner.lock().unwrap();
            let act: Vec<Value> = g
                .active_jobs
                .values()
                .filter_map(|ja| {
                    let j = ja.lock().unwrap();
                    if j.vault == vkey {
                        Some(j.to_json())
                    } else {
                        None
                    }
                })
                .collect();
            let barrier = g.exclusive_barriers.get(&vkey).cloned();
            let mut notices_vec: Vec<Value> = g
                .notices
                .iter()
                .rev()
                .filter(|n| {
                    if n.get("acked").and_then(|v| v.as_bool()) == Some(true) {
                        return false;
                    }
                    let lvl = n.get("level").and_then(|v| v.as_str()).unwrap_or("info");
                    let same_vault = n
                        .get("vault")
                        .and_then(|v| v.as_str())
                        .is_none_or(|nv| nv == vkey);
                    same_vault && matches!(lvl, "warning" | "error")
                })
                .take(5)
                .cloned()
                .collect();
            notices_vec.reverse();
            (g.parent_pid, act, barrier, notices_vec)
        };
        let payload = json!({
            "schema_version": 1,
            "backend": "rust-native",
            "pid": std::process::id(),
            "parent_pid": parent_pid,
            "rss_bytes": process_rss_bytes(),
            "active_jobs": active,
            "exclusive_barrier": exclusive_barrier,
            "recent_notices": recent_notices,
            "updated_at": now_unix_secs(),
        });
        if let Ok(bytes) = serde_json::to_vec_pretty(&payload) {
            let _ = atomic_write_bytes(&indexes_dir.join(".daemon-state.json"), &bytes);
        }
    }

    pub fn health(&self, vault: Option<&Path>) -> Value {
        let rss = process_rss_bytes();
        let jobs = self.list_jobs(vault, false);
        let notices = self.list_notices(vault, false);
        let (started_at, parent_pid, cached) = {
            let g = self.inner.lock().unwrap();
            let c: Vec<Value> = g
                .vault_lru
                .iter()
                .map(|v| {
                    json!({
                        "vault": v.vault_key,
                        "seq": v.last_seq,
                        "workspace_count": v.workspace_map.len(),
                        "hits": v.hits,
                        "misses": v.misses,
                    })
                })
                .collect();
            (g.started_at, g.parent_pid, c)
        };
        json!({
            "ok": true,
            "backend": "rust-native",
            "version": PF_VERSION,
            "python_worker_available": Self::resolve_python_exe().is_some(),
            "pid": std::process::id(),
            "parent_pid": parent_pid,
            "uptime_sec": ((now_unix_secs() - started_at) * 100.0).round() / 100.0,
            "rss_bytes": rss,
            "rss_mb": ((rss as f64 / (1024.0 * 1024.0)) * 100.0).round() / 100.0,
            "heavy_modules_loaded": [],
            "active_jobs": jobs["active"],
            "unacked_notice_count": notices.len(),
            "cached_vaults": cached,
        })
    }

    /// Delegate a complex/mutating CLI command to the published Python worker runtime.
    pub fn delegate_to_python(
        &self,
        vault: Option<&Path>,
        argv: &[String],
        stdin_text: Option<&str>,
    ) -> (i32, String, String) {
        let is_exclusive_upgrade = argv.first().map(|s| s.as_str()) == Some("upgrade")
            && argv.iter().any(|a| a == "--apply" || a == "--rollback");

        if let Some(v) = vault {
            if let Some(barrier) = self.has_exclusive_barrier(v) {
                let cmd_name = argv.first().map(|s| s.as_str()).unwrap_or("cli");
                let err = pf_err(
                    cmd_name,
                    "VAULT_UPGRADE_BARRIER_ACTIVE",
                    &format!("Vault exclusive upgrade barrier is active ({barrier}); try again after upgrade completes."),
                    json!({ "barrier": barrier }),
                    &["Wait for the active vault upgrade/rollback operation to finish."],
                );
                return (
                    1,
                    format!("{err}\n"),
                    format!("vault_upgrade_barrier_active: {barrier}"),
                );
            }
        }

        let Some(py_exe) = Self::resolve_python_exe() else {
            let cmd_name = argv.first().map(|s| s.as_str()).unwrap_or("cli");
            let err = pf_err(
                cmd_name,
                "NO_PYTHON",
                "PaperForge Python runtime not ready. Run `paperforge runtime install` or setup in Obsidian.",
                json!({ "native_daemon": true }),
                &["Open PaperForge Settings -> Setup to install the Python worker environment via uv"],
            );
            return (
                1,
                format!("{err}\n"),
                "NO_PYTHON: PaperForge runtime not ready.".into(),
            );
        };

        if let Some(v) = vault {
            if is_exclusive_upgrade {
                self.acquire_exclusive_barrier(v, "upgrade_cutover_or_rollback");
            }
            let _ = self.get_or_refresh_vault(v);
        }

        let mut cmd = Command::new(py_exe);
        cmd.args(["-m", "paperforge"]);
        if let Some(v) = vault {
            if !argv.iter().any(|a| a == "--vault") {
                cmd.arg("--vault").arg(v);
            }
            if v.is_dir() {
                cmd.current_dir(v);
            }
        }
        cmd.args(argv)
            .stdin(if stdin_text.is_some() {
                Stdio::piped()
            } else {
                Stdio::null()
            })
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        configure_worker_command(&mut cmd);

        let is_sync_cmd = argv.first().map(|s| s.as_str()) == Some("sync");
        let vkey_str = vault.map(Self::norm_vault).unwrap_or_default();
        let sync_job_id = format!("cli_sync_{}_{}", std::process::id(), now_unix_secs());
        let sync_started_at = now_unix_secs();

        let outcome = match cmd.spawn() {
            Ok(mut child) => {
                attach_child_to_job(&child);
                let pid = child.id();
                self.inner.lock().unwrap().delegated_pids.insert(pid);
                if let Some(secret_in) = stdin_text {
                    if let Some(mut sin) = child.stdin.take() {
                        let _ = sin.write_all(secret_in.as_bytes());
                    }
                }
                let res = if is_sync_cmd {
                    let v_opt = if vkey_str.is_empty() { None } else { Some(vkey_str.as_str()) };
                    self.emit_push(
                        "task.updated",
                        v_opt,
                        json!({
                            "job_id": sync_job_id,
                            "kind": "sync",
                            "status": "running",
                            "current": 0,
                            "total": 5,
                            "phase": "starting",
                            "item_id": "",
                            "vault": vkey_str,
                            "started_at": sync_started_at,
                        }),
                    );
                    let out_pipe = child.stdout.take();
                    let err_pipe = child.stderr.take();
                    let out_thread = out_pipe.map(|mut op| {
                        thread::spawn(move || {
                            use std::io::Read;
                            let mut buf = Vec::new();
                            let _ = op.read_to_end(&mut buf);
                            String::from_utf8_lossy(&buf).into_owned()
                        })
                    });
                    let mut stderr_clean = String::new();
                    let mut last_phase = String::from("starting");
                    let mut last_cur: i64 = 0;
                    let mut last_tot: i64 = 5;
                    let mut last_emit = Instant::now();
                    if let Some(ep) = err_pipe {
                        let reader = BufReader::new(ep);
                        for line in reader.lines().map_while(Result::ok) {
                            if let Some(raw_json) = line.strip_prefix("PF_PROGRESS:") {
                                if let Ok(ev) = serde_json::from_str::<Value>(raw_json.trim()) {
                                    let phase = ev
                                        .get("phase")
                                        .and_then(|v| v.as_str())
                                        .unwrap_or("starting")
                                        .to_string();
                                    let cur = ev.get("current").and_then(|v| v.as_i64()).unwrap_or(last_cur);
                                    let tot = ev.get("total").and_then(|v| v.as_i64()).unwrap_or(5);
                                    let detail = ev
                                        .get("detail")
                                        .and_then(|v| v.as_str())
                                        .unwrap_or("")
                                        .to_string();
                                    if phase != last_phase || last_emit.elapsed() >= Duration::from_millis(120) {
                                        last_phase = phase.clone();
                                        last_cur = cur;
                                        last_tot = tot;
                                        last_emit = Instant::now();
                                        self.emit_push(
                                            "task.updated",
                                            v_opt,
                                            json!({
                                                "job_id": sync_job_id,
                                                "kind": "sync",
                                                "status": "running",
                                                "current": cur,
                                                "total": tot,
                                                "phase": phase,
                                                "item_id": detail,
                                                "vault": vkey_str,
                                                "started_at": sync_started_at,
                                            }),
                                        );
                                    }
                                    continue;
                                }
                            }
                            stderr_clean.push_str(&line);
                            stderr_clean.push('\n');
                        }
                    }
                    let rc = child
                        .wait()
                        .ok()
                        .and_then(|s| s.code())
                        .unwrap_or(1);
                    let stdout_str = out_thread
                        .and_then(|t| t.join().ok())
                        .unwrap_or_default();
                    self.emit_push(
                        "task.updated",
                        v_opt,
                        json!({
                            "job_id": sync_job_id,
                            "kind": "sync",
                            "status": if rc == 0 { "succeeded" } else { "failed" },
                            "current": last_tot,
                            "total": last_tot,
                            "phase": "done",
                            "item_id": "",
                            "vault": vkey_str,
                            "started_at": sync_started_at,
                            "finished_at": now_unix_secs(),
                        }),
                    );
                    (rc, stdout_str, stderr_clean)
                } else {
                    match child.wait_with_output() {
                        Ok(out) => (
                            out.status.code().unwrap_or(1),
                            String::from_utf8_lossy(&out.stdout).into_owned(),
                            String::from_utf8_lossy(&out.stderr).into_owned(),
                        ),
                        Err(e) => (1, String::new(), format!("Python worker IO error: {e}")),
                    }
                };
                self.inner.lock().unwrap().delegated_pids.remove(&pid);
                res
            }
            Err(e) => (1, String::new(), format!("Failed to spawn Python worker: {e}")),
        };

        if let Some(v) = vault {
            if is_exclusive_upgrade {
                self.release_exclusive_barrier(v);
            }
            let _ = self.get_or_refresh_vault(v);
        }
        outcome
    }
}

fn vault_path_opt(vkey: &str) -> Option<&Path> {
    if vkey.is_empty() || vkey == "global" {
        None
    } else {
        Some(Path::new(vkey))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn runtime_job_coalesces_when_another_runtime_job_is_running() {
        let sup = NativeControlDaemon::new(None, None);
        let active_id = "job_test_runtime_running".to_string();
        {
            let mut g = sup.inner.lock().unwrap();
            g.active_jobs.insert(
                active_id.clone(),
                Arc::new(Mutex::new(JobRecord {
                    job_id: active_id.clone(),
                    trace_id: "tr_test".into(),
                    vault: "global".into(),
                    kind: "runtime.update".into(),
                    scope_key: "global".into(),
                    source: "job.submit".into(),
                    stream_id: None,
                    status: JobStatus::Running,
                    current: 2,
                    total: 5,
                    phase: "downloading".into(),
                    item_id: "2.0.9".into(),
                    priority_key: None,
                    started_at: now_unix_secs(),
                    finished_at: None,
                    exit_code: None,
                    error: String::new(),
                    stderr_tail: String::new(),
                    pid: None,
                    child: None,
                    cancel_flag: None,
                    runtime_child_pid: None,
                })),
            );
        }

        let res = sup.submit_runtime_job_with_opts(
            None,
            "install",
            "2.0.9",
            crate::runtime_ops::RuntimeInstallOptions::default(),
        );
        assert_eq!(res["accepted"], true);
        assert_eq!(res["coalesced"], true);
        assert_eq!(res["job"]["job_id"], active_id);
        assert_eq!(sup.inner.lock().unwrap().active_jobs.len(), 1);
    }
}
