//! Low-Memory Resident Supervisor, Bounded LRU Vault Cache, Notice Center,
//! Ephemeral Python Worker Supervision, and On-Demand Python Delegation.

use crate::config_ops::{pf_err, strip_verbatim_prefix, PF_VERSION};
use crate::platform::{
    atomic_write_bytes, configure_worker_command, current_ppid, is_pid_alive, kill_process_tree,
    now_unix_secs, process_rss_bytes,
};
use crate::query_ops::{open_readonly_db, read_state_seq, resolve_engine_dir};
use serde_json::{json, Value};
use std::collections::{HashMap, VecDeque};
use std::env;
use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

const MAX_CACHED_VAULTS: usize = 4;
const MAX_WORKSPACES_PER_VAULT: usize = 2048;
const MAX_NOTICES: usize = 100;
const MAX_RECENT_JOBS: usize = 25;

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
    pub vault: String,
    pub kind: String,
    pub status: String,
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
}

impl JobRecord {
    pub fn to_json(&self) -> Value {
        json!({
            "job_id": self.job_id,
            "vault": self.vault,
            "kind": self.kind,
            "status": self.status,
            "current": self.current,
            "total": self.total,
            "phase": self.phase,
            "item_id": self.item_id,
            "priority_key": self.priority_key,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "exit_code": self.exit_code,
            "error": self.error,
            "pid": self.pid,
        })
    }
}

pub type PushSink = Arc<dyn Fn(Value) + Send + Sync>;

struct InnerState {
    started_at: f64,
    parent_pid: Option<u32>,
    initial_ppid: Option<u32>,
    event_seq: u64,
    job_counter: u64,
    notice_counter: u64,
    push_sink: Option<PushSink>,
    vault_lru: VecDeque<VaultCacheEntry>,
    notices: VecDeque<Value>,
    active_jobs: HashMap<String, Arc<Mutex<JobRecord>>>,
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
                notice_counter: 0,
                push_sink,
                vault_lru: VecDeque::new(),
                notices: VecDeque::new(),
                active_jobs: HashMap::new(),
                recent_jobs: VecDeque::new(),
                exclusive_barriers: HashMap::new(),
                followup_heal_priority: HashMap::new(),
            })),
        }
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
        let home = env::var("HOME")
            .or_else(|_| env::var("USERPROFILE"))
            .ok()?;
        let ptr_path = Path::new(&home)
            .join(".paperforge")
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

    pub fn invalidate_vault(&self, vault: Option<&Path>) -> usize {
        let mut g = self.inner.lock().unwrap();
        if let Some(v) = vault {
            let vkey = Self::norm_vault(v);
            if let Some(pos) = g.vault_lru.iter().position(|e| e.vault_key == vkey) {
                g.vault_lru.remove(pos);
                return 1;
            }
            0
        } else {
            let n = g.vault_lru.len();
            g.vault_lru.clear();
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
            }
        }
        json!({ "evicted_vaults": evicted, "gc_collected": 0 })
    }

    pub fn push_notice(&self, level: &str, code: &str, title: &str, detail: &str, vault: Option<&Path>) -> Value {
        let norm_v = vault.map(Self::norm_vault);
        let norm_lvl = match level {
            "info" | "success" | "warning" | "error" => level,
            _ => "info",
        };
        let notice = {
            let mut g = self.inner.lock().unwrap();
            g.notice_counter += 1;
            let nid = format!("ntc_{}_{}", std::process::id(), g.notice_counter);
            let n = json!({
                "notice_id": nid,
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

    pub fn acquire_exclusive_barrier(&self, vault: &Path, reason: &str) {
        let vkey = Self::norm_vault(vault);
        let to_cancel: Vec<String> = {
            let mut g = self.inner.lock().unwrap();
            g.exclusive_barriers.insert(vkey.clone(), reason.to_string());
            g.active_jobs
                .iter()
                .filter_map(|(jid, job_arc)| {
                    let j = job_arc.lock().unwrap();
                    if j.vault == vkey && j.kind == "upgrade.heal" {
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
    }

    pub fn release_exclusive_barrier(&self, vault: &Path) {
        let vkey = Self::norm_vault(vault);
        self.inner.lock().unwrap().exclusive_barriers.remove(&vkey);
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
                if aj.vault == vkey && aj.kind == kind && aj.status == "running" {
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
                vault: vkey.clone(),
                kind: kind.to_string(),
                status: "running".into(),
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

        let stdout_pipe = child.stdout.take();
        let stderr_pipe = child.stderr.take();
        let snap = {
            let mut j = job_arc.lock().unwrap();
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
                    j.stderr_tail.push_str(&line);
                    j.stderr_tail.push('\n');
                    if j.stderr_tail.len() > 4000 {
                        let drain_to = j.stderr_tail.len() - 4000;
                        j.stderr_tail.drain(..drain_to);
                    }
                }
            });
        }

        let daemon_clone = self.clone();
        let job_out = job_arc.clone();
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
                            j.status = "cancelled".into();
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
                if j.status == "cancelling" || rc == 130 {
                    j.status = "cancelled".into();
                } else if rc == 0 {
                    j.status = "succeeded".into();
                } else {
                    j.status = "failed".into();
                    let tail = j.stderr_tail.trim();
                    j.error = if tail.is_empty() {
                        format!("exit code {rc}")
                    } else {
                        tail.chars().rev().take(300).collect::<String>().chars().rev().collect()
                    };
                }
                (
                    j.vault.clone(),
                    j.kind.clone(),
                    j.status.clone(),
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
                if kind_str == "upgrade.heal" && final_status == "succeeded" {
                    g.followup_heal_priority.remove(&vault_str)
                } else {
                    None
                }
            };

            daemon_clone.emit_push("task.updated", Some(&vault_str), final_snap);
            let v_path = PathBuf::from(&vault_str);
            let _ = daemon_clone.get_or_refresh_vault(&v_path);
            daemon_clone.write_heartbeat(&v_path);

            if final_status == "failed" {
                daemon_clone.push_notice(
                    "warning",
                    &format!("job.{kind_str}.failed"),
                    &format!("后台任务未完成 ({kind_str})"),
                    &err_msg,
                    Some(&v_path),
                );
            } else if kind_str == "upgrade.heal" && final_status == "succeeded" {
                daemon_clone.push_notice(
                    "success",
                    "job.upgrade.heal.done",
                    "文献库后台渐进整理已完成",
                    "",
                    Some(&v_path),
                );
            }

            if let Some(pk) = followup_prio {
                let _ = daemon_clone.submit_job(&v_path, "upgrade.heal", None, Some(pk), false);
            }
        });

        json!({ "accepted": true, "coalesced": false, "job": snap })
    }

    pub fn cancel_job(&self, job_id: &str, grace_ms: u64, wait: bool) -> Value {
        let job_arc = {
            let g = self.inner.lock().unwrap();
            let Some(ja) = g.active_jobs.get(job_id).cloned() else {
                return json!({ "ok": false, "reason": "not_found", "job_id": job_id });
            };
            ja
        };

        let (vault_str, snap) = {
            let mut j = job_arc.lock().unwrap();
            j.status = "cancelling".into();
            if let Some(ref mut c) = j.child {
                if let Some(ref mut sin) = c.stdin {
                    let _ = sin.write_all(b"PAPERFORGE_STOP\n");
                    let _ = sin.flush();
                }
            }
            (j.vault.clone(), j.to_json())
        };
        self.emit_push("task.updated", Some(&vault_str), snap);

        let escalate = move || {
            let deadline = Instant::now() + Duration::from_millis(grace_ms.max(200));
            while Instant::now() < deadline {
                let done = {
                    let mut j = job_arc.lock().unwrap();
                    match j.child.as_mut() {
                        Some(c) => matches!(c.try_wait(), Ok(Some(_))),
                        None => true,
                    }
                };
                if done {
                    return;
                }
                thread::sleep(Duration::from_millis(80));
            }
            let mut j = job_arc.lock().unwrap();
            if let Some(ref mut c) = j.child {
                kill_process_tree(c);
            }
        };

        if wait {
            escalate();
        } else {
            thread::spawn(escalate);
        }
        json!({ "ok": true, "job_id": job_id, "status": "cancelling" })
    }

    pub fn cancel_all_jobs(&self, grace_ms: u64) {
        let ids: Vec<String> = self.inner.lock().unwrap().active_jobs.keys().cloned().collect();
        for jid in ids {
            let _ = self.cancel_job(&jid, grace_ms, true);
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
        let indexes_dir = vault.join(".paperforge").join("indexes");
        if !indexes_dir.is_dir() {
            return;
        }
        let vkey = Self::norm_vault(vault);
        let (parent_pid, active) = {
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
            (g.parent_pid, act)
        };
        let payload = json!({
            "schema_version": 1,
            "backend": "rust-native",
            "pid": std::process::id(),
            "parent_pid": parent_pid,
            "rss_bytes": process_rss_bytes(),
            "active_jobs": active,
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

        let is_exclusive_upgrade = argv.first().map(|s| s.as_str()) == Some("upgrade")
            && argv.iter().any(|a| a == "--apply" || a == "--rollback");

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

        let outcome = match cmd.spawn() {
            Ok(mut child) => {
                if let Some(secret_in) = stdin_text {
                    if let Some(mut sin) = child.stdin.take() {
                        let _ = sin.write_all(secret_in.as_bytes());
                    }
                }
                match child.wait_with_output() {
                    Ok(out) => (
                        out.status.code().unwrap_or(1),
                        String::from_utf8_lossy(&out.stdout).into_owned(),
                        String::from_utf8_lossy(&out.stderr).into_owned(),
                    ),
                    Err(e) => (1, String::new(), format!("Python worker IO error: {e}")),
                }
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
