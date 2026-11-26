//! Native MCP stdio server (`paperforge-daemon --mcp`), stable binary routing,
//! and safe vault-local Agent MCP installer / self-check commands.
//!
//! Zero external dependencies beyond `serde_json` + `rusqlite`:
//! - Dual-framing JSON-RPC 2.0 on stdin/stdout (`NDJSON` + `Content-Length` LSP framing)
//! - Exposes 7 tightly scoped high-signal tools backed by Rust `<5ms` queries and
//!   on-demand Python worker delegation
//! - Non-destructive vault-local MCP config installation (`.mcp.json`,
//!   `.cursor/mcp.json`, `opencode.json`) that never clobbers unrelated servers

use crate::brief::{build_agent_brief, discover_vault_from_cwd, query_library_filtered};
use crate::config_ops::{load_canonical_config, pf_err, pf_ok, strip_verbatim_prefix, PF_VERSION};
use crate::platform::{atomic_write_bytes, now_unix_secs};
use crate::query_ops::{resolve_engine_dir, try_handle_search_cli};
use crate::supervisor::NativeControlDaemon;
use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::io::{self, BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FramingMode {
    Ndjson,
    ContentLength,
}

fn user_home_dir() -> Option<PathBuf> {
    env::var("HOME")
        .or_else(|_| env::var("USERPROFILE"))
        .ok()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .map(PathBuf::from)
}

pub fn stable_daemon_bin_path() -> Option<PathBuf> {
    let home = user_home_dir()?;
    let exe = if cfg!(windows) {
        "paperforge-daemon.exe"
    } else {
        "paperforge-daemon"
    };
    Some(home.join(".paperforge").join("bin").join(exe))
}

fn daemon_meta_file_path() -> Option<PathBuf> {
    let home = user_home_dir()?;
    Some(
        home.join(".paperforge")
            .join("bin")
            .join(".daemon-meta.json"),
    )
}

/// Resolve the binary path to write into Agent MCP configurations.
/// Prefers the stable symlink/shim `~/.paperforge/bin/paperforge-daemon(.exe)` if
/// it exists, otherwise falls back to versioned `.daemon-meta.json` or `current_exe()`.
pub fn resolve_stable_binary_path(explicit_override: Option<&Path>) -> PathBuf {
    if let Some(p) = explicit_override {
        if !p.as_os_str().is_empty() {
            return strip_verbatim_prefix(&fs::canonicalize(p).unwrap_or_else(|_| p.to_path_buf()));
        }
    }
    if let Some(stable) = stable_daemon_bin_path() {
        if stable.is_file() {
            return strip_verbatim_prefix(&stable);
        }
    }
    if let Some(meta_path) = daemon_meta_file_path() {
        if let Ok(raw) = fs::read_to_string(&meta_path) {
            if let Ok(val) = serde_json::from_str::<Value>(&raw) {
                if let Some(bp) = val.get("binaryPath").and_then(|v| v.as_str()) {
                    let p = PathBuf::from(bp);
                    if p.is_file() {
                        return strip_verbatim_prefix(&p);
                    }
                }
            }
        }
    }
    env::current_exe()
        .map(|p| strip_verbatim_prefix(&p))
        .unwrap_or_else(|_| PathBuf::from("paperforge-daemon"))
}

fn parse_semver_core(raw: &str) -> Option<(u64, u64, u64, String)> {
    let trimmed = raw.trim().trim_start_matches(['v', 'V']);
    if trimmed.is_empty() {
        return None;
    }
    let (core, pre) = match trimmed.split_once('-') {
        Some((c, p)) => (c, p.to_string()),
        None => (trimmed, String::new()),
    };
    let mut parts = core.split('.');
    let major = parts.next()?.parse::<u64>().ok()?;
    let minor = parts.next().unwrap_or("0").parse::<u64>().ok()?;
    let patch = parts.next().unwrap_or("0").parse::<u64>().ok()?;
    Some((major, minor, patch, pre))
}

pub fn is_meta_tag_compatible_for_reexec(meta_tag: &str, current_version: &str) -> bool {
    let Some((maj_m, min_m, pat_m, _)) = parse_semver_core(meta_tag) else {
        return true;
    };
    let Some((maj_c, min_c, pat_c, _)) = parse_semver_core(current_version) else {
        return true;
    };
    (maj_m, min_m, pat_m) >= (maj_c, min_c, pat_c)
}

/// When invoked via the stable shim `~/.paperforge/bin/paperforge-daemon(.exe)` while
/// `.daemon-meta.json` points to an equal-or-newer versioned binary in the same
/// managed bin dir, transparently forward execution with `PAPERFORGE_DAEMON_NO_REEXEC=1`
/// (prevents loops, never hijacks explicit `cargo`/`--binary` invocations, and never
/// downgrades to an older binary version).
pub fn maybe_reexec_latest_binary(raw_args: &[String]) -> Option<i32> {
    if env::var("PAPERFORGE_DAEMON_NO_REEXEC")
        .map(|v| v.trim() == "1")
        .unwrap_or(false)
    {
        return None;
    }
    let stable = stable_daemon_bin_path()?;
    let cur = env::current_exe().ok()?;
    let stable_canon = fs::canonicalize(&stable).unwrap_or(stable);
    let cur_canon = fs::canonicalize(&cur).unwrap_or(cur);
    if cur_canon != stable_canon {
        return None;
    }

    let meta_path = daemon_meta_file_path()?;
    let raw = fs::read_to_string(&meta_path).ok()?;
    let val: Value = serde_json::from_str(&raw).ok()?;
    let tag = val.get("tag").and_then(|v| v.as_str()).unwrap_or("");
    if !tag.is_empty() && !is_meta_tag_compatible_for_reexec(tag, PF_VERSION) {
        return None;
    }
    let bp = val.get("binaryPath").and_then(|v| v.as_str())?.trim();
    if bp.is_empty() {
        return None;
    }
    let target = PathBuf::from(bp);
    if !target.is_file() {
        return None;
    }
    let tgt_canon = fs::canonicalize(&target).unwrap_or_else(|_| target.clone());
    if cur_canon == tgt_canon {
        return None;
    }
    let mut cmd = Command::new(&target);
    cmd.args(raw_args)
        .env("PAPERFORGE_DAEMON_NO_REEXEC", "1")
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit());
    match cmd.status() {
        Ok(st) => Some(st.code().unwrap_or(0)),
        Err(_) => None,
    }
}

fn normalize_platform(platform: &str) -> String {
    let p = platform.trim().to_ascii_lowercase();
    if p.is_empty() {
        "claude".to_string()
    } else {
        p
    }
}

fn mcp_target_relpath(platform: &str) -> &'static str {
    match platform {
        "opencode" => "opencode.json",
        "cursor" => ".cursor/mcp.json",
        _ => ".mcp.json",
    }
}

fn build_mcp_entry_and_snippet(
    vault: &Path,
    platform: &str,
    binary_path: &Path,
) -> (Value, Option<String>) {
    let bin_str = strip_verbatim_prefix(binary_path).to_string_lossy().into_owned();
    let vault_str = strip_verbatim_prefix(&fs::canonicalize(vault).unwrap_or_else(|_| vault.to_path_buf()))
        .to_string_lossy()
        .into_owned();

    if platform == "opencode" {
        let snippet = json!({
            "mcp": {
                "paperforge": {
                    "type": "local",
                    "command": [bin_str, "--mcp", "--vault", vault_str],
                    "enabled": true
                }
            }
        });
        return (snippet, None);
    }

    let snippet = json!({
        "mcpServers": {
            "paperforge": {
                "command": bin_str,
                "args": ["--mcp", "--vault", vault_str]
            }
        }
    });
    let toml_snippet = if platform == "codex" {
        let esc = |s: &str| s.replace('\\', "\\\\").replace('"', "\\\"");
        Some(format!(
            "[mcp_servers.paperforge]\ncommand = \"{}\"\nargs = [\"--mcp\", \"--vault\", \"{}\"]",
            esc(&bin_str),
            esc(&vault_str)
        ))
    } else {
        None
    };
    (snippet, toml_snippet)
}

pub fn handle_mcp_config(vault: &Path, platform: &str, binary_override: Option<&Path>) -> Value {
    let norm_plat = normalize_platform(platform);
    let clean_vault = strip_verbatim_prefix(&fs::canonicalize(vault).unwrap_or_else(|_| vault.to_path_buf()));
    let bin = resolve_stable_binary_path(binary_override);
    let rel = mcp_target_relpath(&norm_plat);
    let target_file = clean_vault.join(rel);
    let (snippet, toml_snippet) = build_mcp_entry_and_snippet(&clean_vault, &norm_plat, &bin);

    let mut data = json!({
        "platform": norm_plat,
        "vault": clean_vault.to_string_lossy(),
        "binary_path": bin.to_string_lossy(),
        "target_file": target_file.to_string_lossy(),
        "target_relpath": rel,
        "config_snippet": snippet,
    });
    if let Some(toml) = toml_snippet {
        data.as_object_mut()
            .unwrap()
            .insert("toml_snippet".into(), json!(toml));
    }
    pf_ok("mcp-config", data)
}

pub fn handle_mcp_install(
    vault: &Path,
    platform: &str,
    binary_override: Option<&Path>,
) -> (i32, Value) {
    let norm_plat = normalize_platform(platform);
    let clean_vault = strip_verbatim_prefix(&fs::canonicalize(vault).unwrap_or_else(|_| vault.to_path_buf()));
    let bin = resolve_stable_binary_path(binary_override);
    let rel = mcp_target_relpath(&norm_plat);
    let target_file = clean_vault.join(rel);
    let (snippet, toml_snippet) = build_mcp_entry_and_snippet(&clean_vault, &norm_plat, &bin);

    let mut created_new = true;
    let mut root_obj: Map<String, Value> = if target_file.exists() {
        created_new = false;
        match fs::read_to_string(&target_file) {
            Ok(raw) if raw.trim().is_empty() => Map::new(),
            Ok(raw) => match serde_json::from_str::<Value>(&raw) {
                Ok(Value::Object(obj)) => obj,
                Ok(_) => {
                    return (
                        1,
                        pf_err(
                            "mcp-install",
                            "VALIDATION_ERROR",
                            &format!(
                                "Existing {} is not a JSON object; refusing to overwrite.",
                                target_file.display()
                            ),
                            json!({ "target_file": target_file.to_string_lossy() }),
                            &["Fix the JSON syntax manually or copy the snippet via `paperforge-daemon mcp-config`."],
                        ),
                    );
                }
                Err(e) => {
                    return (
                        1,
                        pf_err(
                            "mcp-install",
                            "VALIDATION_ERROR",
                            &format!(
                                "Existing {} contains invalid JSON ({e}); refusing to overwrite.",
                                target_file.display()
                            ),
                            json!({ "target_file": target_file.to_string_lossy() }),
                            &["Fix the JSON syntax manually or copy the snippet via `paperforge-daemon mcp-config`."],
                        ),
                    );
                }
            },
            Err(e) => {
                return (
                    1,
                    pf_err(
                        "mcp-install",
                        "IO_ERROR",
                        &format!("Cannot read {}: {e}", target_file.display()),
                        json!({ "target_file": target_file.to_string_lossy() }),
                        &[],
                    ),
                );
            }
        }
    } else {
        Map::new()
    };

    let (top_key, entry_val) = if norm_plat == "opencode" {
        ("mcp", snippet["mcp"]["paperforge"].clone())
    } else {
        ("mcpServers", snippet["mcpServers"]["paperforge"].clone())
    };

    let section = root_obj
        .entry(top_key.to_string())
        .or_insert_with(|| Value::Object(Map::new()));
    let Some(section_obj) = section.as_object_mut() else {
        return (
            1,
            pf_err(
                "mcp-install",
                "VALIDATION_ERROR",
                &format!(
                    "Existing key '{}' in {} is not an object; refusing to overwrite.",
                    top_key,
                    target_file.display()
                ),
                json!({ "target_file": target_file.to_string_lossy() }),
                &[],
            ),
        );
    };
    section_obj.insert("paperforge".to_string(), entry_val);

    let mut out_bytes = serde_json::to_vec_pretty(&Value::Object(root_obj)).unwrap();
    out_bytes.push(b'\n');
    if let Err(e) = atomic_write_bytes(&target_file, &out_bytes) {
        return (
            1,
            pf_err(
                "mcp-install",
                "IO_ERROR",
                &format!("Failed to write {}: {e}", target_file.display()),
                json!({ "target_file": target_file.to_string_lossy() }),
                &[],
            ),
        );
    }

    let mut data = json!({
        "installed": true,
        "created_new": created_new,
        "platform": norm_plat,
        "vault": clean_vault.to_string_lossy(),
        "binary_path": bin.to_string_lossy(),
        "target_file": target_file.to_string_lossy(),
        "target_relpath": rel,
    });
    if let Some(toml) = toml_snippet {
        data.as_object_mut()
            .unwrap()
            .insert("toml_snippet".into(), json!(toml));
    }
    (0, pf_ok("mcp-install", data))
}

fn platform_skill_relpath(platform: &str) -> &'static str {
    match platform {
        "opencode" => ".opencode/skills",
        "claude" => ".claude/skills",
        "codex" => ".codex/skills",
        "cursor" => ".cursor/skills",
        "windsurf" => ".windsurf/skills",
        "github_copilot" => ".github/skills",
        "gemini" => ".gemini/skills",
        "cline" => ".cline/skills",
        "kilo" => ".kilocode/skills",
        "kimi" => ".kimi/skills",
        "augment" => ".augment/skills",
        "trae" => ".trae/skills",
        _ => ".agents/skills",
    }
}

pub fn machine_skill_hub_dir() -> Option<PathBuf> {
    Some(
        user_home_dir()?
            .join(".paperforge")
            .join("skills")
            .join("paperforge"),
    )
}

pub fn agent_installs_registry_path() -> Option<PathBuf> {
    Some(user_home_dir()?.join(".paperforge").join("agent-installs.json"))
}

pub fn resolve_skill_source_dir() -> Option<PathBuf> {
    if let Some(hub) = machine_skill_hub_dir() {
        if hub.join("SKILL.md").is_file() {
            return Some(strip_verbatim_prefix(&hub));
        }
    }
    let home = user_home_dir()?;
    let ptr_path = home.join(".paperforge").join("runtime").join("pointer.json");
    let raw = fs::read_to_string(&ptr_path).ok()?;
    let val: Value = serde_json::from_str(&raw).ok()?;
    let env_root = PathBuf::from(val.get("environment_root")?.as_str()?.trim());
    let win_cand = env_root
        .join("Lib")
        .join("site-packages")
        .join("paperforge")
        .join("skills")
        .join("paperforge");
    if win_cand.join("SKILL.md").is_file() {
        return Some(strip_verbatim_prefix(&win_cand));
    }
    let lib_dir = env_root.join("lib");
    if let Ok(rd) = fs::read_dir(&lib_dir) {
        for entry in rd.flatten() {
            let p = entry
                .path()
                .join("site-packages")
                .join("paperforge")
                .join("skills")
                .join("paperforge");
            if p.join("SKILL.md").is_file() {
                return Some(strip_verbatim_prefix(&p));
            }
        }
    }
    None
}

fn collect_skill_files(root: &Path, dir: &Path, out: &mut Vec<(String, PathBuf)>) {
    let Ok(rd) = fs::read_dir(dir) else {
        return;
    };
    for entry in rd.flatten() {
        let p = entry.path();
        let name = entry.file_name();
        let name_str = name.to_string_lossy();
        if name_str == "__pycache__" {
            continue;
        }
        if p.is_dir() {
            collect_skill_files(root, &p, out);
        } else if p.is_file() {
            if name_str.to_ascii_lowercase().ends_with(".pyc") {
                continue;
            }
            if let Ok(rel) = p.strip_prefix(root) {
                let rel_posix = rel
                    .components()
                    .map(|c| c.as_os_str().to_string_lossy().into_owned())
                    .collect::<Vec<_>>()
                    .join("/");
                out.push((rel_posix, p));
            }
        }
    }
}

/// Deterministic SHA-256 digest matching `paperforge/services/skill_deploy.py::_skill_tree_digest`
/// byte-for-byte (sorted POSIX relative paths, `\x00`, CRLF -> LF normalized).
pub fn skill_tree_digest(root: &Path) -> Option<String> {
    if !root.is_dir() {
        return None;
    }
    let mut files = Vec::new();
    collect_skill_files(root, root, &mut files);
    if files.is_empty() {
        return None;
    }
    files.sort_by(|a, b| a.0.cmp(&b.0));
    let mut hasher = Sha256::new();
    for (rel, path) in files {
        let bytes = fs::read(&path).ok()?;
        hasher.update(rel.as_bytes());
        hasher.update([0u8]);
        let mut i = 0;
        while i < bytes.len() {
            if i + 1 < bytes.len() && bytes[i] == b'\r' && bytes[i + 1] == b'\n' {
                hasher.update([b'\n']);
                i += 2;
            } else {
                hasher.update([bytes[i]]);
                i += 1;
            }
        }
    }
    Some(format!("{:x}", hasher.finalize()))
}

fn is_link_to_dir(dst: &Path, hub: &Path) -> bool {
    if let Ok(meta) = fs::symlink_metadata(dst) {
        if meta.file_type().is_symlink() {
            return true;
        }
    }
    match (fs::canonicalize(dst), fs::canonicalize(hub)) {
        (Ok(a), Ok(b)) => a == b && dst != hub,
        _ => false,
    }
}

fn copy_dir_recursive(src: &Path, dst: &Path) -> io::Result<()> {
    fs::create_dir_all(dst)?;
    for entry in fs::read_dir(src)? {
        let entry = entry?;
        let sp = entry.path();
        let dp = dst.join(entry.file_name());
        if sp.is_dir() {
            copy_dir_recursive(&sp, &dp)?;
        } else if sp.is_file() {
            fs::copy(&sp, &dp)?;
        }
    }
    Ok(())
}

fn atomic_replace_dir(src: &Path, dst: &Path) -> Result<(), String> {
    let parent = dst
        .parent()
        .ok_or_else(|| "Target skill dir has no parent".to_string())?;
    fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    let nonce = format!("{}_{}", std::process::id(), now_unix_secs().to_bits());
    let stage = parent.join(format!(".paperforge-skill-stage-{nonce}"));
    let backup = parent.join(format!(".paperforge-skill-bak-{nonce}"));

    if let Err(e) = copy_dir_recursive(src, &stage) {
        let _ = fs::remove_dir_all(&stage);
        return Err(e.to_string());
    }
    if skill_tree_digest(&stage) != skill_tree_digest(src) {
        let _ = fs::remove_dir_all(&stage);
        return Err("Staged skill digest mismatch".into());
    }
    if dst.exists() {
        fs::rename(dst, &backup).map_err(|e| {
            let _ = fs::remove_dir_all(&stage);
            e.to_string()
        })?;
        if let Err(e) = fs::rename(&stage, dst) {
            let _ = fs::rename(&backup, dst);
            let _ = fs::remove_dir_all(&stage);
            return Err(e.to_string());
        }
        let _ = fs::remove_dir_all(&backup);
    } else {
        fs::rename(&stage, dst).map_err(|e| {
            let _ = fs::remove_dir_all(&stage);
            e.to_string()
        })?;
    }
    Ok(())
}

fn read_agent_installs_file(reg_path: &Path) -> Vec<Value> {
    let Ok(raw) = fs::read_to_string(reg_path) else {
        return Vec::new();
    };
    let Ok(val) = serde_json::from_str::<Value>(&raw) else {
        return Vec::new();
    };
    val.get("installs")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default()
}

fn write_agent_installs_file(reg_path: &Path, installs: &[Value]) -> Result<(), String> {
    let doc = json!({ "schema_version": 1, "installs": installs });
    let mut bytes = serde_json::to_vec_pretty(&doc).map_err(|e| e.to_string())?;
    bytes.push(b'\n');
    atomic_write_bytes(reg_path, &bytes).map_err(|e| e.to_string())
}

pub fn sync_all_registered_installs_with_paths(hub: &Path, reg_path: &Path) -> Value {
    let Some(hub_digest) = skill_tree_digest(hub) else {
        return pf_ok(
            "skill-sync-all",
            json!({
                "hub_exists": false,
                "hub_digest": Value::Null,
                "updated": 0,
                "up_to_date": 0,
                "customized_preserved": 0,
                "pruned": 0,
            }),
        );
    };

    let installs = read_agent_installs_file(reg_path);
    let mut next_installs: Vec<Value> = Vec::with_capacity(installs.len());
    let mut updated = 0usize;
    let mut up_to_date = 0usize;
    let mut customized_preserved = 0usize;
    let mut pruned = 0usize;
    let mut errors: Vec<String> = Vec::new();

    for entry in installs {
        let Some(mut obj) = entry.as_object().cloned() else {
            continue;
        };
        let raw_dir = obj
            .get("skill_dir")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim()
            .to_string();
        if raw_dir.is_empty() {
            pruned += 1;
            continue;
        }
        let dst = PathBuf::from(&raw_dir);
        if !dst.exists() && fs::symlink_metadata(&dst).is_err() {
            pruned += 1;
            continue;
        }

        let recorded = obj
            .get("last_synced_digest")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let mode = obj
            .get("link_mode")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();

        if is_link_to_dir(&dst, hub) || mode == "link" {
            obj.insert("link_mode".into(), json!("link"));
            obj.insert("last_synced_digest".into(), json!(hub_digest));
            up_to_date += 1;
            next_installs.push(Value::Object(obj));
            continue;
        }

        let cur_digest = skill_tree_digest(&dst).unwrap_or_default();
        if cur_digest == hub_digest {
            obj.insert("last_synced_digest".into(), json!(hub_digest));
            up_to_date += 1;
        } else if !recorded.is_empty() && cur_digest == recorded {
            match atomic_replace_dir(hub, &dst) {
                Ok(()) => {
                    obj.insert("last_synced_digest".into(), json!(hub_digest));
                    obj.insert("updated_at".into(), json!(now_unix_secs()));
                    updated += 1;
                }
                Err(e) => {
                    errors.push(format!("{raw_dir}: {e}"));
                }
            }
        } else {
            customized_preserved += 1;
        }
        next_installs.push(Value::Object(obj));
    }

    if let Err(e) = write_agent_installs_file(reg_path, &next_installs) {
        errors.push(e);
    }

    pf_ok(
        "skill-sync-all",
        json!({
            "hub_exists": true,
            "hub_dir": strip_verbatim_prefix(hub).to_string_lossy(),
            "hub_digest": hub_digest,
            "updated": updated,
            "up_to_date": up_to_date,
            "customized_preserved": customized_preserved,
            "pruned": pruned,
            "total_registered": next_installs.len(),
            "errors": errors,
        }),
    )
}

pub fn handle_skill_sync_all() -> Value {
    let Some(hub) = machine_skill_hub_dir() else {
        return pf_err(
            "skill-sync-all",
            "PATH_NOT_FOUND",
            "Cannot determine home directory for ~/.paperforge/skills",
            json!({}),
            &[],
        );
    };
    let Some(reg) = agent_installs_registry_path() else {
        return pf_err(
            "skill-sync-all",
            "PATH_NOT_FOUND",
            "Cannot determine home directory for ~/.paperforge/agent-installs.json",
            json!({}),
            &[],
        );
    };
    sync_all_registered_installs_with_paths(&hub, &reg)
}

pub fn handle_agent_onboarding(
    vault: &Path,
    lang: &str,
    binary_override: Option<&Path>,
) -> Value {
    let clean_vault = strip_verbatim_prefix(&fs::canonicalize(vault).unwrap_or_else(|_| vault.to_path_buf()));
    let bin = resolve_stable_binary_path(binary_override);
    let bin_str = bin.to_string_lossy().into_owned();
    let vault_str = clean_vault.to_string_lossy().into_owned();
    let skill_src_opt = resolve_skill_source_dir();
    let skill_src_str = skill_src_opt
        .as_ref()
        .map(|p| p.to_string_lossy().into_owned())
        .unwrap_or_else(|| {
            machine_skill_hub_dir()
                .map(|p| strip_verbatim_prefix(&p).to_string_lossy().into_owned())
                .unwrap_or_else(|| "~/.paperforge/skills/paperforge".into())
        });
    let is_zh = lang.trim().to_ascii_lowercase().starts_with("zh");
    let mcp_args = json!(["--mcp", "--vault", vault_str]);
    let self_check_tpl = format!(
        "\"{bin_str}\" mcp-check --vault \"{vault_str}\" --skill-dir \"<SKILL_DIR>\" --mcp-config \"<MCP_CONFIG_PATH>\" --register --probe-mcp --json"
    );

    let prompt = if is_zh {
        format!(
            "请为当前 Agent 环境配置 PaperForge 研究记忆配套设施（**不要往用户的 Obsidian Vault 根目录写入 `.agents/` 或 `.mcp.json` 等杂项文件**，优先安装到你自身平台的原生全局/工作区目录）：\n\n\
### 本机真实路径（禁止猜测或自行拼接）\n\
- Vault 路径：`{vault_str}`\n\
- MCP 稳定入口：`{bin_str}`\n\
- MCP 启动参数：`[\"--mcp\", \"--vault\", \"{vault_str}\"]`\n\
- 官方 Skill 源目录：`{skill_src_str}`\n\n\
### 请按以下 3 步完成安装并做端到端自检\n\
1. **接入 `paperforge` MCP 服务**：按你自身平台的原生配置格式（如 Claude/Cursor/Antigravity 的 `mcpServers` JSON、OpenCode 的 `mcp` JSON、Codex 的 `[mcp_servers.paperforge]` TOML 等），非破坏性地合并添加名为 `paperforge` 的 stdio 服务，严禁覆盖用户已有其他 MCP 服务。\n\
2. **安装 PaperForge Skill**：将上方 `官方 Skill 源目录` 链接或复制到你自身原生识别的全局 skills 目录（优先用符号链接/Windows NTFS Junction `New-Item -ItemType Junction -Path \"<你的skills目录>\\paperforge\" -Target \"{skill_src_str}\"`，无需管理员权限即可随软件升级自动同步；若复制完整目录也支持自动更新）。\n\
3. **运行端到端自检并登记自动更新**：\n\
   执行以下命令（替换为你实际安装的路径）：\n\
   ```bash\n\
   {self_check_tpl}\n\
   ```\n\
   确认输出 `data.status == \"ready\"` 且 `data.mcp_handshake_ok == true`。如当前会话支持热加载，顺便调用一次 `paperforge_brief` 验证实时握手；若需重启会话生效，请在汇报末尾明确提醒用户新开/重载会话。\n\
   最后用清晰清单向用户汇报：MCP 注册、Skill 安装（链接/复制）、Vault 库状态、实时握手四项结果。"
        )
    } else {
        format!(
            "Set up the PaperForge Research Memory integration for your own Agent harness (**do NOT write `.agents/` or `.mcp.json` clutter into the user's Obsidian Vault root**; install into your platform's native config/skills locations instead):\n\n\
### Verified Local Paths (do not guess paths)\n\
- Vault path: `{vault_str}`\n\
- Stable MCP binary: `{bin_str}`\n\
- MCP args: `[\"--mcp\", \"--vault\", \"{vault_str}\"]`\n\
- Canonical Skill source: `{skill_src_str}`\n\n\
### Execute these 3 steps and verify\n\
1. **Register the `paperforge` stdio MCP server** in your harness's native config (`mcpServers` JSON, OpenCode `mcp` JSON, or Codex `[mcp_servers.paperforge]` TOML) without overwriting existing servers.\n\
2. **Install the PaperForge Skill** from the Canonical Skill source above into your native skills directory (prefer symlink or Windows NTFS Junction `New-Item -ItemType Junction -Path \"<skills_dir>\\paperforge\" -Target \"{skill_src_str}\"` for zero-touch live updates; full directory copy is also auto-synced).\n\
3. **Run self-check & register for auto-updates**:\n\
   ```bash\n\
   {self_check_tpl}\n\
   ```\n\
   Verify `data.status == \"ready\"` and `data.mcp_handshake_ok == true`. Report the 4-item checklist (MCP config, Skill install, Vault readiness, Live MCP handshake) and let the user know if a session reload is needed to activate new MCP tools."
        )
    };

    pf_ok(
        "agent-onboarding",
        json!({
            "vault": vault_str,
            "binary_path": bin_str,
            "binary_exists": bin.is_file(),
            "mcp_args": mcp_args,
            "skill_source_dir": skill_src_str,
            "skill_source_exists": skill_src_opt.is_some(),
            "self_check_template": self_check_tpl,
            "prompt": prompt,
        }),
    )
}

#[derive(Default)]
struct McpCheckResult {
    configured: bool,
    binary_valid: bool,
    configured_cmd: String,
    args_ok: bool,
    format: &'static str,
}

fn parse_toml_paperforge_section(raw: &str) -> McpCheckResult {
    let mut in_section = false;
    let mut cmd = String::new();
    let mut args_raw = String::new();
    for raw_line in raw.lines() {
        let line = raw_line.split('#').next().unwrap_or("").trim();
        if line.is_empty() {
            continue;
        }
        if line.starts_with('[') && line.ends_with(']') {
            let sec = line[1..line.len() - 1].trim();
            in_section = sec == "mcp_servers.paperforge";
            continue;
        }
        if !in_section {
            continue;
        }
        if let Some((k, v)) = line.split_once('=') {
            let key = k.trim();
            let val = v.trim();
            if key == "command" {
                let unq = val.trim_matches('"').trim_matches('\'');
                cmd = unq.replace("\\\\", "\\").replace("\\\"", "\"");
            } else if key == "args" {
                args_raw = val.to_string();
            }
        }
    }
    if cmd.is_empty() && args_raw.is_empty() {
        return McpCheckResult::default();
    }
    McpCheckResult {
        configured: true,
        binary_valid: !cmd.is_empty() && Path::new(&cmd).is_file(),
        configured_cmd: cmd,
        args_ok: args_raw.contains("--mcp"),
        format: "toml",
    }
}

fn inspect_mcp_config_file(path: &Path) -> McpCheckResult {
    let Ok(raw) = fs::read_to_string(path) else {
        return McpCheckResult::default();
    };
    if path.extension().and_then(|s| s.to_str()) == Some("toml") {
        return parse_toml_paperforge_section(&raw);
    }
    if let Ok(val) = serde_json::from_str::<Value>(&raw) {
        if let Some(entry) = val.get("mcp").and_then(|m| m.get("paperforge")) {
            let arr = entry
                .get("command")
                .and_then(|c| c.as_array())
                .cloned()
                .unwrap_or_default();
            let cmd0 = arr
                .first()
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            let args_ok = arr.iter().any(|v| v.as_str() == Some("--mcp"));
            return McpCheckResult {
                configured: true,
                binary_valid: !cmd0.is_empty() && Path::new(&cmd0).is_file(),
                configured_cmd: cmd0,
                args_ok,
                format: "json_opencode",
            };
        }
        if let Some(entry) = val.get("mcpServers").and_then(|m| m.get("paperforge")) {
            let cmd0 = entry
                .get("command")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            let args_ok = entry
                .get("args")
                .and_then(|a| a.as_array())
                .map(|arr| arr.iter().any(|v| v.as_str() == Some("--mcp")))
                .unwrap_or(false);
            return McpCheckResult {
                configured: true,
                binary_valid: !cmd0.is_empty() && Path::new(&cmd0).is_file(),
                configured_cmd: cmd0,
                args_ok,
                format: "json",
            };
        }
    }
    McpCheckResult::default()
}

fn normalize_installed_skill_dir(candidate: &Path) -> Option<PathBuf> {
    if candidate.join("SKILL.md").is_file() {
        return Some(strip_verbatim_prefix(candidate));
    }
    let nested = candidate.join("paperforge");
    if nested.join("SKILL.md").is_file() {
        return Some(strip_verbatim_prefix(&nested));
    }
    None
}

#[allow(clippy::too_many_arguments)]
pub fn handle_mcp_check_with_options(
    vault: &Path,
    platform: &str,
    skill_dir_override: Option<&Path>,
    mcp_config_override: Option<&Path>,
    probe_mcp: bool,
    register: bool,
    reg_path_override: Option<&Path>,
) -> Value {
    let norm_plat = normalize_platform(platform);
    let clean_vault = strip_verbatim_prefix(&fs::canonicalize(vault).unwrap_or_else(|_| vault.to_path_buf()));
    let bin = resolve_stable_binary_path(None);
    let binary_exists = bin.is_file();

    let cfg_ok = load_canonical_config(&clean_vault).is_ok();
    let engine_dir = resolve_engine_dir(&clean_vault);
    let db_exists = engine_dir.join("indexes").join("paperforge.db").is_file();

    let reg_path_opt = reg_path_override
        .map(PathBuf::from)
        .or_else(agent_installs_registry_path);
    let existing_installs = reg_path_opt
        .as_ref()
        .map(|p| read_agent_installs_file(p))
        .unwrap_or_default();

    let hub_opt = resolve_skill_source_dir();
    let hub_digest = hub_opt.as_ref().and_then(|h| skill_tree_digest(h));

    // Resolve installed skill directory: explicit -> registered -> vault-local fallback
    let mut resolved_skill_dir: Option<PathBuf> = skill_dir_override.and_then(normalize_installed_skill_dir);
    if resolved_skill_dir.is_none() {
        for item in &existing_installs {
            if let Some(sd) = item.get("skill_dir").and_then(|v| v.as_str()) {
                if let Some(norm) = normalize_installed_skill_dir(Path::new(sd)) {
                    resolved_skill_dir = Some(norm);
                    break;
                }
            }
        }
    }
    if resolved_skill_dir.is_none() {
        for cand in [
            clean_vault.join(platform_skill_relpath(&norm_plat)),
            clean_vault.join(".agents").join("skills"),
        ] {
            if let Some(norm) = normalize_installed_skill_dir(&cand) {
                resolved_skill_dir = Some(norm);
                break;
            }
        }
    }

    let skill_deployed = resolved_skill_dir.is_some();
    let skill_link_mode = match (&resolved_skill_dir, &hub_opt) {
        (Some(sd), Some(hub)) if is_link_to_dir(sd, hub) => "link",
        (Some(_), _) => "copy",
        _ => "none",
    };
    let installed_skill_digest = resolved_skill_dir.as_ref().and_then(|sd| skill_tree_digest(sd));
    let skill_up_to_date = match (&installed_skill_digest, &hub_digest) {
        (Some(a), Some(b)) => a == b,
        (Some(_), None) => true,
        _ => false,
    };

    // Resolve MCP config file: explicit -> registered -> vault-local fallback
    let rel = mcp_target_relpath(&norm_plat);
    let mut config_file_used = mcp_config_override.map(PathBuf::from);
    if config_file_used.is_none() {
        for item in &existing_installs {
            if item.get("vault").and_then(|v| v.as_str()) == Some(clean_vault.to_string_lossy().as_ref()) {
                if let Some(mc) = item.get("mcp_config").and_then(|v| v.as_str()).filter(|s| !s.is_empty()) {
                    let p = PathBuf::from(mc);
                    if p.is_file() {
                        config_file_used = Some(p);
                        break;
                    }
                }
            }
        }
    }
    let target_file = config_file_used.unwrap_or_else(|| clean_vault.join(rel));
    let mcp_res = inspect_mcp_config_file(&target_file);

    let brief = build_agent_brief(&clean_vault, None);
    let brief_ok = brief.get("ok").and_then(|v| v.as_bool()) == Some(true)
        && brief
            .get("data")
            .and_then(|d| d.get("capabilities"))
            .and_then(|c| c.get("safe_read"))
            .and_then(|v| v.as_bool())
            == Some(true);

    // Optional live MCP JSON-RPC handshake probe
    let mut mcp_handshake_ok: Option<bool> = None;
    let mut mcp_tool_count: Option<usize> = None;
    if probe_mcp {
        let daemon = NativeControlDaemon::new(None, None);
        let init_r = process_mcp_message(
            &daemon,
            Some(&clean_vault),
            &json!({ "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": { "protocolVersion": "2025-03-26" } }),
        );
        let tools_r = process_mcp_message(
            &daemon,
            Some(&clean_vault),
            &json!({ "jsonrpc": "2.0", "id": 2, "method": "tools/list" }),
        );
        let tool_len = tools_r
            .as_ref()
            .and_then(|v| v.get("result"))
            .and_then(|r| r.get("tools"))
            .and_then(|t| t.as_array())
            .map(|a| a.len())
            .unwrap_or(0);
        mcp_tool_count = Some(tool_len);
        mcp_handshake_ok = Some(init_r.is_some() && tool_len == 7);
    }

    // Optional registration in ~/.paperforge/agent-installs.json for zero-touch auto-updates
    let mut registered = false;
    if register && skill_deployed {
        if let (Some(reg_path), Some(sd)) = (reg_path_opt.as_ref(), resolved_skill_dir.as_ref()) {
            let sd_str = sd.to_string_lossy().into_owned();
            let mc_str = if target_file.is_file() {
                strip_verbatim_prefix(&target_file).to_string_lossy().into_owned()
            } else {
                String::new()
            };
            let mut next: Vec<Value> = existing_installs
                .into_iter()
                .filter(|v| v.get("skill_dir").and_then(|s| s.as_str()) != Some(sd_str.as_str()))
                .collect();
            next.push(json!({
                "skill_dir": sd_str,
                "mcp_config": mc_str,
                "vault": clean_vault.to_string_lossy(),
                "link_mode": skill_link_mode,
                "last_synced_digest": installed_skill_digest.clone().unwrap_or_default(),
                "updated_at": now_unix_secs(),
            }));
            if write_agent_installs_file(reg_path, &next).is_ok() {
                registered = true;
            }
        }
    }

    let mut next_steps: Vec<String> = Vec::new();
    let status = if !mcp_res.configured || !mcp_res.args_ok || !skill_deployed {
        if !skill_deployed {
            next_steps.push("Install PaperForge Skill into your Agent skills directory (see `agent-onboarding`).".into());
        }
        if !mcp_res.configured || !mcp_res.args_ok {
            next_steps.push("Register the `paperforge` stdio MCP entry (`--mcp --vault <VAULT>`) in your Agent MCP config.".into());
        }
        "needs_install"
    } else if !mcp_res.binary_valid {
        next_steps.push(format!(
            "Update `paperforge` MCP `command` to `{}`.",
            bin.display()
        ));
        "stale_binary"
    } else if !skill_up_to_date {
        next_steps.push("Run `paperforge-daemon skill-sync-all --json` or re-link from Skill Hub.".into());
        "skill_outdated"
    } else if !cfg_ok || !db_exists || !brief_ok || mcp_handshake_ok == Some(false) {
        if !cfg_ok {
            next_steps.push("Run `paperforge config init` to initialize paperforge.json.".into());
        }
        if !db_exists {
            next_steps.push("Run `paperforge memory build` or Sync Library in Obsidian.".into());
        }
        "degraded"
    } else {
        "ready"
    };

    let mut data = json!({
        "status": status,
        "platform": norm_plat,
        "vault": clean_vault.to_string_lossy(),
        "binary_path": bin.to_string_lossy(),
        "binary_exists": binary_exists,
        "target_file": strip_verbatim_prefix(&target_file).to_string_lossy(),
        "config_format": mcp_res.format,
        "vault_config_ok": cfg_ok,
        "memory_db_exists": db_exists,
        "skill_deployed": skill_deployed,
        "skill_dir": resolved_skill_dir.as_ref().map(|p| Value::String(p.to_string_lossy().into_owned())).unwrap_or(Value::Null),
        "skill_link_mode": skill_link_mode,
        "skill_up_to_date": skill_up_to_date,
        "skill_digest": installed_skill_digest,
        "mcp_configured": mcp_res.configured,
        "mcp_args_ok": mcp_res.args_ok,
        "mcp_binary_valid": mcp_res.binary_valid,
        "configured_command": mcp_res.configured_cmd,
        "brief_ok": brief_ok,
        "registered": registered,
        "next_steps": next_steps,
    });
    if let Some(ok) = mcp_handshake_ok {
        data.as_object_mut()
            .unwrap()
            .insert("mcp_handshake_ok".into(), json!(ok));
    }
    if let Some(cnt) = mcp_tool_count {
        data.as_object_mut()
            .unwrap()
            .insert("mcp_tool_count".into(), json!(cnt));
    }
    pf_ok("mcp-check", data)
}

#[cfg(test)]
pub fn handle_mcp_check(vault: &Path, platform: &str) -> Value {
    handle_mcp_check_with_options(vault, platform, None, None, false, false, None)
}

pub fn mcp_tools_list() -> Value {
    json!({
        "tools": [
            {
                "name": "paperforge_brief",
                "description": "Fast (<5ms) session handoff returning vault paths, runtime health, live Obsidian daemon jobs/barriers, library stats, collection hierarchy, capabilities, blocked actions, actionable hints, and optional single-paper snapshot.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "vault": { "type": "string", "description": "Optional vault root path; defaults to daemon vault or CWD discovery." },
                        "paper_key": { "type": "string", "description": "Optional canonical Zotero key, citation_key, or DOI for single-paper preflight context." }
                    }
                }
            },
            {
                "name": "paperforge_search",
                "description": "Fast (<2ms) metadata FTS5 search over title, abstract, authors, journal, domain, and collections.",
                "inputSchema": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": { "type": "string", "description": "Search query string." },
                        "vault": { "type": "string" },
                        "domain": { "type": "string" },
                        "year_from": { "type": "integer" },
                        "year_to": { "type": "integer" },
                        "ocr": { "type": "string", "enum": ["done", "pending", "failed", "processing", "done_incomplete"] },
                        "deep": { "type": "string", "enum": ["done", "pending"] },
                        "limit": { "type": "integer", "minimum": 1, "maximum": 100 },
                        "evidence": { "type": "boolean" }
                    }
                }
            },
            {
                "name": "paperforge_library_query",
                "description": "Filtered and paginated SQLite SSOT library snapshot (Base table view) without flooding context.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "vault": { "type": "string" },
                        "domain": { "type": "string" },
                        "collection": { "type": "string", "description": "Substring filter on collection path." },
                        "ocr_status": { "type": "string" },
                        "deep_reading_status": { "type": "string" },
                        "needs_diagnostic": { "type": "boolean" },
                        "has_pdf": { "type": "boolean" },
                        "query": { "type": "string", "description": "Case-insensitive substring match across key/title/author/journal." },
                        "limit": { "type": "integer", "minimum": 1, "maximum": 100, "default": 30 },
                        "offset": { "type": "integer", "minimum": 0, "default": 0 }
                    }
                }
            },
            {
                "name": "paperforge_paper_context",
                "description": "Load full context pack for a single paper including structure tree, fulltext path, user PDF annotations/questions, AI annotations, and Living Paper Memory Card facets.",
                "inputSchema": {
                    "type": "object",
                    "required": ["key"],
                    "properties": {
                        "key": { "type": "string", "description": "Zotero key, citation_key, or DOI." },
                        "vault": { "type": "string" },
                        "structure": { "type": "boolean", "default": true }
                    }
                }
            },
            {
                "name": "paperforge_retrieve",
                "description": "Fulltext evidence retrieval across OCR body units and vector embeddings (use deep=true to force FTS5 BM25 when vectors are disabled/building).",
                "inputSchema": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": { "type": "string" },
                        "vault": { "type": "string" },
                        "limit": { "type": "integer", "minimum": 1, "maximum": 50 },
                        "deep": { "type": "boolean" },
                        "domain": { "type": "string" }
                    }
                }
            },
            {
                "name": "paperforge_annotate_batch",
                "description": "Atomically ground and save a batch of AI review annotations onto the PDF sidecar layer (validates OCR readiness, enforces batch limit, rejects pure paraphrases, deduplicates existing marks, optional replace_lens).",
                "inputSchema": {
                    "type": "object",
                    "required": ["paper_key", "items"],
                    "properties": {
                        "paper_key": { "type": "string" },
                        "vault": { "type": "string" },
                        "lens": { "type": "string", "enum": ["skeleton", "methods", "critique", "custom"], "default": "skeleton" },
                        "replace_lens": { "type": "boolean", "default": false },
                        "max_items": { "type": "integer", "minimum": 1, "maximum": 25, "default": 15 },
                        "items": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 25,
                            "items": {
                                "type": "object",
                                "required": ["comment"],
                                "properties": {
                                    "quote": { "type": "string", "description": "Verbatim substring copied from fulltext.md." },
                                    "figure_id": { "type": "string", "description": "Figure/table ID such as figure_001 or table_001." },
                                    "comment": { "type": "string", "description": "Non-paraphrase analytical/review insight (>=8 chars)." },
                                    "color": { "type": "string", "enum": ["yellow", "green", "blue", "red", "purple"] },
                                    "lens": { "type": "string", "enum": ["skeleton", "methods", "critique", "custom"] },
                                    "page_hint": { "type": "integer", "minimum": 1 },
                                    "section_hint": { "type": "string" },
                                    "tags": { "type": "array", "items": { "type": "string" } }
                                }
                            }
                        }
                    }
                }
            },
            {
                "name": "paperforge_memory_refine",
                "description": "Evolve one cognitive facet of a paper's Living Paper Memory Card.",
                "inputSchema": {
                    "type": "object",
                    "required": ["paper_key", "facet", "content"],
                    "properties": {
                        "paper_key": { "type": "string" },
                        "facet": { "type": "string", "enum": ["idea_logic", "methods_params", "research_craft", "critique_limits", "my_connection"] },
                        "content": { "type": "string" },
                        "vault": { "type": "string" }
                    }
                }
            }
        ]
    })
}

fn resolve_tool_vault(args: &Value, default_vault: Option<&Path>) -> Result<PathBuf, String> {
    let arg_vault = args
        .get("vault")
        .and_then(|v| v.as_str())
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(PathBuf::from);
    if let Some(vp) = arg_vault.as_deref().or(default_vault) {
        return Ok(strip_verbatim_prefix(
            &fs::canonicalize(vp).unwrap_or_else(|_| vp.to_path_buf()),
        ));
    }
    discover_vault_from_cwd(None)
        .ok_or_else(|| "Vault path not resolved. Pass `vault` or start `--mcp --vault <path>`.".to_string())
}

fn tool_ok(payload: Value) -> Value {
    let text = serde_json::to_string_pretty(&payload).unwrap_or_else(|_| payload.to_string());
    let is_err = payload.get("ok").and_then(|v| v.as_bool()) == Some(false);
    json!({
        "content": [{ "type": "text", "text": text }],
        "isError": is_err,
    })
}

fn tool_err(msg: &str) -> Value {
    json!({
        "content": [{ "type": "text", "text": msg }],
        "isError": true,
    })
}

fn call_python_tool(
    daemon: &NativeControlDaemon,
    vault: &Path,
    argv: &[String],
    stdin_text: Option<&str>,
) -> Value {
    let (rc, out, err) = daemon.delegate_to_python(Some(vault), argv, stdin_text);
    let trimmed = out.trim();
    if let Ok(parsed) = serde_json::from_str::<Value>(trimmed) {
        let ok_flag = parsed.get("ok").and_then(|v| v.as_bool()).unwrap_or(rc == 0);
        return json!({
            "content": [{ "type": "text", "text": serde_json::to_string_pretty(&parsed).unwrap_or_else(|_| trimmed.to_string()) }],
            "isError": !ok_flag || rc != 0,
        });
    }
    if rc == 0 {
        json!({
            "content": [{ "type": "text", "text": if trimmed.is_empty() { "{}" } else { trimmed } }],
            "isError": false,
        })
    } else {
        let msg = if err.trim().is_empty() {
            if trimmed.is_empty() {
                format!("Python worker exited with code {rc}")
            } else {
                trimmed.to_string()
            }
        } else {
            err.trim().to_string()
        };
        tool_err(&msg)
    }
}

fn execute_mcp_tool(
    daemon: &NativeControlDaemon,
    default_vault: Option<&Path>,
    name: &str,
    args: &Value,
) -> Result<Value, (i32, String)> {
    let vault = match resolve_tool_vault(args, default_vault) {
        Ok(v) => v,
        Err(e) => return Ok(tool_err(&e)),
    };

    match name {
        "paperforge_brief" => {
            let pk = args.get("paper_key").and_then(|v| v.as_str());
            Ok(tool_ok(build_agent_brief(&vault, pk)))
        }
        "paperforge_library_query" => Ok(tool_ok(query_library_filtered(&vault, args))),
        "paperforge_search" => {
            let query = args
                .get("query")
                .and_then(|v| v.as_str())
                .map(str::trim)
                .unwrap_or("");
            if query.is_empty() {
                return Ok(tool_err("`query` is required and cannot be empty."));
            }
            let mut argv = vec!["search".to_string(), query.to_string(), "--json".to_string()];
            for (arg_k, flag) in [
                ("domain", "--domain"),
                ("ocr", "--ocr"),
                ("deep", "--deep"),
            ] {
                if let Some(val) = args
                    .get(arg_k)
                    .and_then(|v| v.as_str())
                    .map(str::trim)
                    .filter(|s| !s.is_empty())
                {
                    argv.push(flag.into());
                    argv.push(val.into());
                }
            }
            for (arg_k, flag) in [
                ("year_from", "--year-from"),
                ("year_to", "--year-to"),
                ("limit", "--limit"),
            ] {
                if let Some(n) = args.get(arg_k).and_then(|v| v.as_i64()) {
                    argv.push(flag.into());
                    argv.push(n.to_string());
                }
            }
            if args.get("evidence").and_then(|v| v.as_bool()) == Some(true) {
                argv.push("--evidence".into());
            }

            let python_available = NativeControlDaemon::resolve_python_exe().is_some();
            if let Some((rc, out, err)) = try_handle_search_cli(&vault, &argv, python_available) {
                if let Ok(parsed) = serde_json::from_str::<Value>(out.trim()) {
                    return Ok(tool_ok(parsed));
                }
                return Ok(if rc == 0 {
                    tool_err(&out)
                } else {
                    tool_err(if err.trim().is_empty() { &out } else { &err })
                });
            }
            Ok(call_python_tool(daemon, &vault, &argv, None))
        }
        "paperforge_paper_context" => {
            let key = args
                .get("key")
                .and_then(|v| v.as_str())
                .map(str::trim)
                .unwrap_or("");
            if key.is_empty() {
                return Ok(tool_err("`key` is required."));
            }
            let mut argv = vec!["paper-context".to_string(), key.to_string()];
            if args
                .get("structure")
                .and_then(|v| v.as_bool())
                .unwrap_or(true)
            {
                argv.push("--structure".into());
            }
            argv.push("--json".into());
            Ok(call_python_tool(daemon, &vault, &argv, None))
        }
        "paperforge_retrieve" => {
            let query = args
                .get("query")
                .and_then(|v| v.as_str())
                .map(str::trim)
                .unwrap_or("");
            if query.is_empty() {
                return Ok(tool_err("`query` is required."));
            }
            let mut argv = vec!["retrieve".to_string(), query.to_string(), "--json".to_string()];
            if let Some(lim) = args.get("limit").and_then(|v| v.as_i64()) {
                argv.push("--limit".into());
                argv.push(lim.to_string());
            }
            if args.get("deep").and_then(|v| v.as_bool()) == Some(true) {
                argv.push("--deep".into());
            }
            if let Some(dom) = args
                .get("domain")
                .and_then(|v| v.as_str())
                .map(str::trim)
                .filter(|s| !s.is_empty())
            {
                argv.push("--domain".into());
                argv.push(dom.into());
            }
            Ok(call_python_tool(daemon, &vault, &argv, None))
        }
        "paperforge_annotate_batch" => {
            let key = args
                .get("paper_key")
                .and_then(|v| v.as_str())
                .map(str::trim)
                .unwrap_or("");
            if key.is_empty() {
                return Ok(tool_err("`paper_key` is required."));
            }
            let Some(items) = args.get("items").and_then(|v| v.as_array()) else {
                return Ok(tool_err("`items` must be a non-empty array."));
            };
            if items.is_empty() {
                return Ok(tool_err("`items` must contain at least 1 annotation."));
            }
            let lens = args
                .get("lens")
                .and_then(|v| v.as_str())
                .unwrap_or("skeleton");
            let replace_lens = args
                .get("replace_lens")
                .and_then(|v| v.as_bool())
                .unwrap_or(false);
            let max_items = args
                .get("max_items")
                .and_then(|v| v.as_i64())
                .unwrap_or(15)
                .clamp(1, 25);

            let mut argv = vec![
                "annotations".into(),
                "agent-apply".into(),
                key.into(),
                "--input".into(),
                "-".into(),
                "--lens".into(),
                lens.into(),
                "--max-items".into(),
                max_items.to_string(),
                "--json".into(),
            ];
            if replace_lens {
                argv.push("--replace-lens".into());
            }
            let stdin_payload = json!({
                "items": items,
                "lens": lens,
                "replace_lens": replace_lens,
                "max_items": max_items,
            })
            .to_string();
            Ok(call_python_tool(daemon, &vault, &argv, Some(&stdin_payload)))
        }
        "paperforge_memory_refine" => {
            let key = args
                .get("paper_key")
                .and_then(|v| v.as_str())
                .map(str::trim)
                .unwrap_or("");
            let facet = args
                .get("facet")
                .and_then(|v| v.as_str())
                .map(str::trim)
                .unwrap_or("");
            let content = args
                .get("content")
                .and_then(|v| v.as_str())
                .map(str::trim)
                .unwrap_or("");
            if key.is_empty() || facet.is_empty() || content.is_empty() {
                return Ok(tool_err("`paper_key`, `facet`, and `content` are required."));
            }
            let argv = vec![
                "memory-card".into(),
                "refine".into(),
                key.into(),
                "--facet".into(),
                facet.into(),
                "--content".into(),
                content.into(),
                "--json".into(),
            ];
            Ok(call_python_tool(daemon, &vault, &argv, None))
        }
        _ => Err((-32602, format!("Unknown tool: {name}"))),
    }
}

/// Process a single decoded MCP JSON-RPC message; returns `None` for notifications.
pub fn process_mcp_message(
    daemon: &NativeControlDaemon,
    default_vault: Option<&Path>,
    req: &Value,
) -> Option<Value> {
    let id_opt = req.get("id").filter(|v| !v.is_null()).cloned();
    let method = req.get("method").and_then(|v| v.as_str()).unwrap_or("");

    // Notifications (no id, or notifications/*) MUST NOT receive a response frame
    if id_opt.is_none() || method.starts_with("notifications/") {
        return None;
    }
    let id = id_opt.unwrap();
    let params = req.get("params").cloned().unwrap_or_else(|| json!({}));

    let ok_resp = |res: Value| -> Option<Value> {
        Some(json!({
            "jsonrpc": "2.0",
            "id": id,
            "result": res,
        }))
    };
    let err_resp = |code: i32, msg: String| -> Option<Value> {
        Some(json!({
            "jsonrpc": "2.0",
            "id": id,
            "error": { "code": code, "message": msg },
        }))
    };

    match method {
        "initialize" => {
            let client_ver = params
                .get("protocolVersion")
                .and_then(|v| v.as_str())
                .unwrap_or("2024-11-05");
            let negotiated = match client_ver {
                "2025-03-26" | "2024-11-05" => client_ver,
                _ => "2024-11-05",
            };
            ok_resp(json!({
                "protocolVersion": negotiated,
                "capabilities": {
                    "tools": { "listChanged": false },
                    "resources": { "listChanged": false }
                },
                "serverInfo": {
                    "name": "paperforge",
                    "version": PF_VERSION
                }
            }))
        }
        "ping" => ok_resp(json!({})),
        "tools/list" => ok_resp(mcp_tools_list()),
        "tools/call" => {
            let name = params.get("name").and_then(|v| v.as_str()).unwrap_or("");
            let args = params.get("arguments").cloned().unwrap_or_else(|| json!({}));
            match execute_mcp_tool(daemon, default_vault, name, &args) {
                Ok(res) => ok_resp(res),
                Err((code, msg)) => err_resp(code, msg),
            }
        }
        "resources/list" => ok_resp(json!({
            "resources": [{
                "uri": "paperforge://brief",
                "name": "PaperForge Vault Brief",
                "description": "Live vault runtime health, library stats, active daemon jobs, and actionable agent hints.",
                "mimeType": "application/json"
            }]
        })),
        "resources/read" => {
            let uri = params.get("uri").and_then(|v| v.as_str()).unwrap_or("");
            if uri != "paperforge://brief" {
                return err_resp(-32602, format!("Unknown resource URI: {uri}"));
            }
            match resolve_tool_vault(&json!({}), default_vault) {
                Ok(vp) => {
                    let brief = build_agent_brief(&vp, None);
                    let text = serde_json::to_string_pretty(&brief).unwrap_or_else(|_| brief.to_string());
                    ok_resp(json!({
                        "contents": [{
                            "uri": "paperforge://brief",
                            "mimeType": "application/json",
                            "text": text
                        }]
                    }))
                }
                Err(e) => err_resp(-32603, e),
            }
        }
        _ => err_resp(-32601, format!("Method not found: {method}")),
    }
}

pub fn read_next_mcp_message<R: BufRead>(reader: &mut R) -> io::Result<Option<(Value, FramingMode)>> {
    let mut line = String::new();
    loop {
        line.clear();
        let n = reader.read_line(&mut line)?;
        if n == 0 {
            return Ok(None);
        }
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        if trimmed.to_ascii_lowercase().starts_with("content-length:") {
            let mut content_len: usize = trimmed
                .split_once(':')
                .and_then(|(_, rhs)| rhs.trim().parse::<usize>().ok())
                .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "Invalid Content-Length header"))?;
            loop {
                let mut hdr = String::new();
                let hn = reader.read_line(&mut hdr)?;
                if hn == 0 {
                    return Ok(None);
                }
                let ht = hdr.trim();
                if ht.is_empty() {
                    break;
                }
                if ht.to_ascii_lowercase().starts_with("content-length:") {
                    if let Some(len) = ht.split_once(':').and_then(|(_, r)| r.trim().parse::<usize>().ok()) {
                        content_len = len;
                    }
                }
            }
            let mut body = vec![0u8; content_len];
            reader.read_exact(&mut body)?;
            let val: Value = serde_json::from_slice(&body)
                .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
            return Ok(Some((val, FramingMode::ContentLength)));
        }

        let val: Value = serde_json::from_str(trimmed)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
        return Ok(Some((val, FramingMode::Ndjson)));
    }
}

pub fn write_mcp_message<W: Write>(writer: &mut W, msg: &Value, mode: FramingMode) -> io::Result<()> {
    let body = serde_json::to_string(msg)?;
    match mode {
        FramingMode::Ndjson => {
            writeln!(writer, "{body}")?;
        }
        FramingMode::ContentLength => {
            write!(writer, "Content-Length: {}\r\n\r\n{}", body.len(), body)?;
        }
    }
    writer.flush()
}

/// Serve Model Context Protocol (MCP) JSON-RPC 2.0 over stdio until EOF.
pub fn serve_mcp(default_vault: Option<PathBuf>) {
    let daemon = NativeControlDaemon::new(None, None);
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut reader = BufReader::new(stdin.lock());
    let mut writer = io::BufWriter::new(stdout.lock());

    while let Ok(Some((req, mode))) = read_next_mcp_message(&mut reader) {
        if let Some(resp) = process_mcp_message(&daemon, default_vault.as_deref(), &req) {
            if write_mcp_message(&mut writer, &resp, mode).is_err() {
                break;
            }
        }
    }
    daemon.cancel_all_jobs(1000);
}
