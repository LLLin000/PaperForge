//! Native cross-platform Zero-Python runtime bootstrapper (`paperforge[vector]`).
//!
//! Eliminates fragile `.ps1` / `.cmd` / `/bin/sh` temporary installer scripts:
//! 1. Downloads & SHA-256 verifies portable `uv` in pure Rust (`ureq` + `sha2`),
//!    extracting with `zip` (Windows) or `flate2`+`tar` (macOS/Linux).
//! 2. Installs isolated Python 3.12 (`npmmirror` fallback) & `.bootstrap-uv` venv.
//! 3. Installs `paperforge[vector]==<pep440>` (with GitHub wheel cache + Tuna/Aliyun mirrors).
//! 4. Executes `<boot_py> -m paperforge runtime <install|update|repair>` to publish
//!    `~/.paperforge/runtime/pointer.json`, streaming all output to `installer.log`
//!    and `ControlDaemon` progress callbacks.

use crate::platform::{atomic_write_bytes, attach_child_to_job, configure_worker_command, kill_process_tree};
use sha2::{Digest, Sha256};
use std::env;
use std::fs::{self, OpenOptions};
use std::io::{BufRead, BufReader, Cursor, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, AtomicU32, Ordering};
use std::sync::mpsc;
use std::time::Duration;

pub const UV_VERSION: &str = "0.13.9";
pub const GITHUB_REPO: &str = "LLLin000/PaperForge";
pub const INSTALLER_FINISHED_MARKER: &str = "[PaperForge] Installer finished.";
pub const INSTALLER_FAILED_MARKER: &str = "[PaperForge] Installer step failed.";

pub fn uv_target_asset_and_sha() -> Option<(&'static str, &'static str, &'static str)> {
    let os = env::consts::OS;
    let arch = env::consts::ARCH;
    let norm_arch = if arch == "aarch64" || arch == "arm64" {
        "aarch64"
    } else {
        "x86_64"
    };
    match (os, norm_arch) {
        ("windows", "x86_64") => Some((
            "uv-x86_64-pc-windows-msvc.zip",
            "edd61f7f5728a56cc62455386661860bdfc7bab65872f39b0c25bdcc1d8e1beb",
            "zip",
        )),
        ("windows", "aarch64") => Some((
            "uv-aarch64-pc-windows-msvc.zip",
            "72eed595983a4d7d22d79f21065b0f4479cc7e5c7a89104bb410c8f47559a878",
            "zip",
        )),
        ("macos", "x86_64") => Some((
            "uv-x86_64-apple-darwin.tar.gz",
            "617a3211261b0fc739562f0071aa34e9739797c510208ede8e2977c30903d041",
            "targz",
        )),
        ("macos", "aarch64") => Some((
            "uv-aarch64-apple-darwin.tar.gz",
            "5aeca67f2283f75235de40d0bd9c0a5bbc5fce23b6d48b3bf9fa1b2db08382ca",
            "targz",
        )),
        ("linux", "x86_64") => Some((
            "uv-x86_64-unknown-linux-gnu.tar.gz",
            "a7fbaff2b9a271d85c1bdb540941090fd1ce011797b4abeb48e4dcd39c2471d5",
            "targz",
        )),
        ("linux", "aarch64") => Some((
            "uv-aarch64-unknown-linux-gnu.tar.gz",
            "0797542018e541a9288855df555c8077eed06f7a47d206362030480e8ecc9f3d",
            "targz",
        )),
        _ => None,
    }
}

pub fn normalize_pep440(version: &str) -> String {
    let cleaned = version.trim().trim_start_matches(['v', 'V']);
    for (tag, short) in [("alpha", "a"), ("beta", "b"), ("rc", "rc")] {
        if let Some(pos) = cleaned.to_ascii_lowercase().find(tag) {
            let prefix = cleaned[..pos].trim_end_matches(['-', '.']);
            let suffix = cleaned[pos + tag.len()..].trim_start_matches(['.', '-']);
            if !prefix.is_empty() && suffix.chars().all(|c| c.is_ascii_digit()) && !suffix.is_empty() {
                let num: u32 = suffix.parse().unwrap_or(0);
                return format!("{prefix}{short}{num}");
            }
        }
    }
    cleaned.to_string()
}

pub fn user_home_dir() -> Result<PathBuf, String> {
    env::var("HOME")
        .or_else(|_| env::var("USERPROFILE"))
        .map(PathBuf::from)
        .map_err(|_| "Cannot determine user home directory".to_string())
}

pub fn installer_log_path(home: &Path) -> PathBuf {
    home.join(".paperforge").join("runtime").join("installer.log")
}

const MAX_CHECKSUMS_BYTES: usize = 512 * 1024;
const MAX_ARCHIVE_BYTES: usize = 128 * 1024 * 1024;

const CREDENTIAL_ENV_PREFIXES: &[&str] = &[
    "PAPERFORGE_CREDENTIAL_",
    "PADDLEOCR_",
    "VECTOR_DB_",
    "OPENAI_",
    "EASYSCHOLAR_",
    "ZOTERO_API_",
    "ANTHROPIC_",
    "MISTRAL_",
];

pub fn redact_log_line(line: &str) -> String {
    let mut out = String::with_capacity(line.len());
    let chars: Vec<char> = line.chars().collect();
    let mut i = 0;
    while i < chars.len() {
        // Redact URL userinfo `://user:pass@`
        if i + 3 <= chars.len() && chars[i..i + 3] == [':', '/', '/'] {
            out.push_str("://");
            i += 3;
            let rest_start = i;
            let mut at_pos = None;
            let mut j = i;
            while j < chars.len() && !chars[j].is_whitespace() && chars[j] != '/' && chars[j] != '"' && chars[j] != '\'' {
                if chars[j] == '@' {
                    at_pos = Some(j);
                    break;
                }
                j += 1;
            }
            if let Some(ap) = at_pos {
                if ap > rest_start {
                    out.push_str("<redacted>@");
                    i = ap + 1;
                    continue;
                }
            }
            continue;
        }
        // Redact `Bearer <token>`
        let rem: String = chars[i..].iter().collect();
        let rem_lower = rem.to_ascii_lowercase();
        if rem_lower.starts_with("bearer ") {
            let after = &chars[i + 7..];
            let mut k = 0;
            while k < after.len() && after[k] == ' ' {
                k += 1;
            }
            let tok_start = k;
            while k < after.len()
                && (after[k].is_ascii_alphanumeric()
                    || matches!(after[k], '.' | '_' | '~' | '+' | '/' | '=' | '-'))
            {
                k += 1;
            }
            if k - tok_start >= 8 {
                out.push_str(&rem[..7]);
                out.push_str("<redacted>");
                i += 7 + k;
                continue;
            }
        }
        // Redact `sk-...`, `ghp_...`, `gho_...`, `ghu_...`, `ghs_...`, `ghr_...`, `AIza...`
        let is_token_prefix = rem.starts_with("sk-")
            || rem.starts_with("ghp_")
            || rem.starts_with("gho_")
            || rem.starts_with("ghu_")
            || rem.starts_with("ghs_")
            || rem.starts_with("ghr_")
            || rem.starts_with("AIza");
        if is_token_prefix && (i == 0 || !chars[i - 1].is_ascii_alphanumeric()) {
            let mut k = 0;
            while i + k < chars.len()
                && (chars[i + k].is_ascii_alphanumeric() || matches!(chars[i + k], '_' | '-'))
            {
                k += 1;
            }
            if k >= 12 {
                out.push_str("<redacted-key>");
                i += k;
                continue;
            }
        }
        // Redact `key=value` secret parameters
        let mut matched_kv = false;
        for kw in ["api_key=", "api-key=", "token=", "secret=", "password=", "authorization="] {
            if rem_lower.starts_with(kw)
                && (i == 0 || !(chars[i - 1].is_ascii_alphanumeric() || chars[i - 1] == '_'))
            {
                let mut k = kw.len();
                while i + k < chars.len()
                    && !chars[i + k].is_whitespace()
                    && !matches!(chars[i + k], '&' | '"' | '\'' | ',' | ';')
                {
                    k += 1;
                }
                if k > kw.len() {
                    out.push_str(&rem[..kw.len()]);
                    out.push_str("<redacted>");
                    i += k;
                    matched_kv = true;
                    break;
                }
            }
        }
        if matched_kv {
            continue;
        }
        out.push(chars[i]);
        i += 1;
    }
    out
}

fn append_log(log_path: &Path, line: &str) {
    if let Some(parent) = log_path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    let clean = redact_log_line(line);
    if let Ok(mut f) = OpenOptions::new().create(true).append(true).open(log_path) {
        let _ = writeln!(f, "{clean}");
        let _ = f.flush();
    }
}

fn is_cancelled(cancel_flag: Option<&AtomicBool>) -> bool {
    cancel_flag
        .map(|f| f.load(Ordering::Relaxed))
        .unwrap_or(false)
}

fn resolve_proxy_from_lookup<F>(lookup: F) -> Option<String>
where
    F: Fn(&str) -> Option<String>,
{
    for key in [
        "PAPERFORGE_PROXY",
        "HTTPS_PROXY",
        "https_proxy",
        "HTTP_PROXY",
        "http_proxy",
    ] {
        if let Some(raw) = lookup(key) {
            let trimmed = raw.trim();
            if !trimmed.is_empty() {
                return Some(trimmed.to_string());
            }
        }
    }
    None
}

fn extract_url_host(url: &str) -> Option<String> {
    let trimmed = url.trim();
    let after_scheme = trimmed.split_once("://").map(|(_, r)| r).unwrap_or(trimmed);
    let authority = after_scheme.split('/').next()?.split('?').next()?.split('#').next()?;
    let host_port = authority.rsplit('@').next()?;
    if host_port.is_empty() {
        return None;
    }
    if let Some(rest) = host_port.strip_prefix('[') {
        let end = rest.find(']')?;
        return Some(rest[..end].to_ascii_lowercase());
    }
    let host = match host_port.rsplit_once(':') {
        Some((h, p)) if !p.is_empty() && p.chars().all(|c| c.is_ascii_digit()) => h,
        _ => host_port,
    };
    let lower = host.trim().to_ascii_lowercase();
    if lower.is_empty() { None } else { Some(lower) }
}

pub(crate) fn matches_no_proxy(url: &str, no_proxy: &str) -> bool {
    let Some(host) = extract_url_host(url) else {
        return false;
    };
    for raw_rule in no_proxy.split([',', ';']) {
        let rule = raw_rule.trim().to_ascii_lowercase();
        if rule.is_empty() {
            continue;
        }
        if rule == "*" {
            return true;
        }
        if let Some(prefix) = rule.strip_suffix('*') {
            if !prefix.is_empty() && host.starts_with(prefix) {
                return true;
            }
        }
        let clean_rule = if let Some(rest) = rule.strip_prefix('[') {
            rest.split(']').next().unwrap_or(rest)
        } else if let Some((h, p)) = rule.rsplit_once(':') {
            if !p.is_empty() && p.chars().all(|c| c.is_ascii_digit()) { h } else { rule.as_str() }
        } else {
            rule.as_str()
        };
        let suffix = clean_rule.trim_start_matches("*.").trim_start_matches('.');
        if suffix.is_empty() {
            continue;
        }
        if host == suffix || host.ends_with(&format!(".{suffix}")) {
            return true;
        }
    }
    false
}

fn resolve_proxy_for_url_with_lookup<F>(url: &str, lookup: F) -> Option<String>
where
    F: Fn(&str) -> Option<String>,
{
    for np_key in ["NO_PROXY", "no_proxy"] {
        if let Some(np) = lookup(np_key) {
            if matches_no_proxy(url, &np) {
                return None;
            }
        }
    }
    resolve_proxy_from_lookup(lookup)
}

fn resolve_proxy_from_env() -> Option<String> {
    resolve_proxy_from_lookup(|k| env::var(k).ok())
}

fn normalize_proxy_url(raw: &str, default_scheme: &str) -> Option<String> {
    let trimmed = raw.trim().trim_end_matches('/');
    if trimmed.is_empty() || trimmed.chars().any(|c| c.is_whitespace()) {
        return None;
    }
    if trimmed.contains("://") {
        let lower = trimmed.to_ascii_lowercase();
        if lower.starts_with("http://")
            || lower.starts_with("https://")
            || lower.starts_with("socks5://")
            || lower.starts_with("socks://")
        {
            return Some(trimmed.to_string());
        }
        return None;
    }
    Some(format!("{default_scheme}://{trimmed}"))
}

pub(crate) fn parse_windows_reg_proxy_output(stdout: &str) -> Option<String> {
    let mut enabled = false;
    let mut server = String::new();
    for line in stdout.lines() {
        let trimmed = line.trim();
        if let Some(rest) = trimmed.strip_prefix("ProxyEnable") {
            let val = rest.split_whitespace().last().unwrap_or("");
            enabled = val == "0x1" || val == "1";
        } else if trimmed.starts_with("ProxyServer") {
            let tokens: Vec<&str> = trimmed.split_whitespace().collect();
            if tokens.len() >= 3 {
                server = tokens[2..].join(" ");
            }
        }
    }
    if !enabled || server.trim().is_empty() {
        return None;
    }
    if server.contains('=') {
        let mut https_val: Option<String> = None;
        let mut http_val: Option<String> = None;
        let mut socks_val: Option<String> = None;
        for part in server.split(';') {
            if let Some((k, v)) = part.split_once('=') {
                match k.trim().to_ascii_lowercase().as_str() {
                    "https" => https_val = normalize_proxy_url(v, "http"),
                    "http" => http_val = normalize_proxy_url(v, "http"),
                    "socks" => socks_val = normalize_proxy_url(v, "socks5"),
                    _ => {}
                }
            }
        }
        https_val.or(http_val).or(socks_val)
    } else {
        normalize_proxy_url(&server, "http")
    }
}

pub(crate) fn parse_mac_scutil_proxy_output(stdout: &str) -> Option<String> {
    let mut https_enable = false;
    let mut http_enable = false;
    let mut socks_enable = false;
    let mut https_host = String::new();
    let mut https_port = String::new();
    let mut http_host = String::new();
    let mut http_port = String::new();
    let mut socks_host = String::new();
    let mut socks_port = String::new();
    for line in stdout.lines() {
        let trimmed = line.trim();
        if let Some((k, v)) = trimmed.split_once(':') {
            let key = k.trim();
            let val = v.trim();
            match key {
                "HTTPSEnable" => https_enable = val == "1",
                "HTTPEnable" => http_enable = val == "1",
                "SOCKSEnable" => socks_enable = val == "1",
                "HTTPSProxy" => https_host = val.to_string(),
                "HTTPSPort" => https_port = val.to_string(),
                "HTTPProxy" => http_host = val.to_string(),
                "HTTPPort" => http_port = val.to_string(),
                "SOCKSProxy" => socks_host = val.to_string(),
                "SOCKSPort" => socks_port = val.to_string(),
                _ => {}
            }
        }
    }
    if https_enable && !https_host.is_empty() {
        let hp = if https_port.is_empty() {
            https_host
        } else {
            format!("{https_host}:{https_port}")
        };
        return normalize_proxy_url(&hp, "http");
    }
    if http_enable && !http_host.is_empty() {
        let hp = if http_port.is_empty() {
            http_host
        } else {
            format!("{http_host}:{http_port}")
        };
        return normalize_proxy_url(&hp, "http");
    }
    if socks_enable && !socks_host.is_empty() {
        let hp = if socks_port.is_empty() {
            socks_host
        } else {
            format!("{socks_host}:{socks_port}")
        };
        return normalize_proxy_url(&hp, "socks5");
    }
    None
}

fn detect_os_system_proxy() -> Option<String> {
    if cfg!(test) {
        return None;
    }
    #[cfg(target_os = "windows")]
    {
        let mut cmd = Command::new("reg");
        cmd.args([
            "query",
            r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ]);
        configure_worker_command(&mut cmd);
        if let Ok(out) = cmd.output() {
            if out.status.success() {
                return parse_windows_reg_proxy_output(&String::from_utf8_lossy(&out.stdout));
            }
        }
        return None;
    }
    #[cfg(target_os = "macos")]
    {
        let mut cmd = Command::new("scutil");
        cmd.arg("--proxy");
        configure_worker_command(&mut cmd);
        if let Ok(out) = cmd.output() {
            if out.status.success() {
                return parse_mac_scutil_proxy_output(&String::from_utf8_lossy(&out.stdout));
            }
        }
        return None;
    }
    #[cfg(not(any(target_os = "windows", target_os = "macos")))]
    {
        None
    }
}

fn resolve_effective_proxy() -> Option<String> {
    resolve_proxy_from_env().or_else(detect_os_system_proxy)
}

fn resolve_effective_proxy_for_url(url: &str) -> Option<String> {
    for np_key in ["NO_PROXY", "no_proxy"] {
        if let Ok(np) = env::var(np_key) {
            if matches_no_proxy(url, &np) {
                return None;
            }
        }
    }
    resolve_effective_proxy()
}

#[derive(Debug, Clone, Default)]
pub struct RuntimeInstallOptions {
    pub proxy_url: Option<String>,
    pub prefer_cn_mirror: Option<bool>,
}

fn http_get_bytes_cancellable(
    url: &str,
    timeout_secs: u64,
    max_bytes: usize,
    cancel_flag: Option<&AtomicBool>,
) -> Result<Vec<u8>, String> {
    http_get_bytes_cancellable_with_proxy(url, timeout_secs, max_bytes, cancel_flag, None)
}

fn http_get_bytes_cancellable_with_proxy(
    url: &str,
    timeout_secs: u64,
    max_bytes: usize,
    cancel_flag: Option<&AtomicBool>,
    proxy_override: Option<&str>,
) -> Result<Vec<u8>, String> {
    if is_cancelled(cancel_flag) {
        return Err("Runtime job cancelled".into());
    }
    let url_owned = url.to_string();
    let explicit_proxy = proxy_override
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string());
    let (tx, rx) = mpsc::channel();
    std::thread::spawn(move || {
        let mut builder = ureq::AgentBuilder::new()
            .timeout_connect(Duration::from_secs(10))
            .timeout_read(Duration::from_secs(timeout_secs))
            .timeout(Duration::from_secs(timeout_secs));
        let chosen_proxy = explicit_proxy.or_else(|| resolve_effective_proxy_for_url(&url_owned));
        if let Some(trimmed) = chosen_proxy {
            if let Ok(proxy) = ureq::Proxy::new(&trimmed) {
                builder = builder.proxy(proxy);
            }
        }
        let agent = builder.build();
        let res = (|| -> Result<Vec<u8>, String> {
            let resp = agent
                .get(&url_owned)
                .set("User-Agent", "PaperForge-Native-Daemon/2.0")
                .call()
                .map_err(|e| format!("HTTP error for {url_owned}: {e}"))?;
            let mut reader = resp.into_reader().take((max_bytes as u64) + 1);
            let mut buf = Vec::new();
            reader
                .read_to_end(&mut buf)
                .map_err(|e| format!("Read body failed for {url_owned}: {e}"))?;
            if buf.len() > max_bytes {
                return Err(format!("Response exceeded max limit ({max_bytes} bytes) for {url_owned}"));
            }
            Ok(buf)
        })();
        let _ = tx.send(res);
    });

    loop {
        if is_cancelled(cancel_flag) {
            return Err("Runtime job cancelled".into());
        }
        match rx.recv_timeout(Duration::from_millis(50)) {
            Ok(res) => return res,
            Err(mpsc::RecvTimeoutError::Timeout) => continue,
            Err(mpsc::RecvTimeoutError::Disconnected) => {
                return Err(format!("HTTP worker disconnected for {url}"))
            }
        }
    }
}

pub fn parse_checksum_for_asset(checksums_text: &str, asset_name: &str) -> Option<String> {
    let target = asset_name.trim();
    if target.is_empty() {
        return None;
    }
    for line in checksums_text.lines() {
        let mut parts = line.split_whitespace();
        let Some(hash) = parts.next() else { continue };
        let Some(raw_name) = parts.next() else { continue };
        let hex = hash.trim().to_ascii_lowercase();
        if hex.len() != 64 || !hex.bytes().all(|b| b.is_ascii_hexdigit()) {
            continue;
        }
        let fname = raw_name
            .trim_start_matches('*')
            .rsplit(['/', '\\'])
            .next()
            .unwrap_or("");
        if fname == target {
            return Some(hex);
        }
    }
    None
}

pub fn is_valid_wheel_zip(bytes: &[u8]) -> bool {
    if !bytes.starts_with(b"PK") {
        return false;
    }
    let Ok(mut archive) = zip::ZipArchive::new(Cursor::new(bytes)) else {
        return false;
    };
    if archive.is_empty() {
        return false;
    }
    for i in 0..archive.len() {
        let Ok(mut entry) = archive.by_index(i) else {
            return false;
        };
        if std::io::copy(&mut entry, &mut std::io::sink()).is_err() {
            return false;
        }
    }
    true
}

fn candidate_release_tags(clean_tag: &str, pep440: &str) -> Vec<String> {
    let mut tags = Vec::new();
    for raw in [clean_tag, pep440] {
        let t = raw.trim();
        if !t.is_empty() && !tags.iter().any(|x| x == t) {
            tags.push(t.to_string());
        }
    }
    // Also map PEP440 `2.0.7rc1` -> SemVer `2.0.7-rc.1`
    let lower = pep440.to_ascii_lowercase();
    for (short, full) in [("rc", "rc"), ("a", "alpha"), ("b", "beta")] {
        if let Some(pos) = lower.rfind(short) {
            let prefix = &pep440[..pos];
            let suffix = &pep440[pos + short.len()..];
            if !prefix.is_empty()
                && !suffix.is_empty()
                && suffix.chars().all(|c| c.is_ascii_digit())
            {
                if let Ok(num) = suffix.parse::<u32>() {
                    let sv = format!("{prefix}-{full}.{num}");
                    if !tags.iter().any(|x| x == &sv) {
                        tags.push(sv);
                    }
                }
            }
        }
    }
    tags
}

fn fetch_official_release_checksum(
    tags: &[String],
    asset_name: &str,
    cancel_flag: Option<&AtomicBool>,
    proxy_override: Option<&str>,
) -> Option<(String, String)> {
    // Trust anchor: checksums.txt MUST come exclusively from official github.com,
    // NEVER from third-party mirrors (ghfast.top / gh-proxy.com).
    for tag in tags {
        if is_cancelled(cancel_flag) {
            return None;
        }
        let url = format!("https://github.com/{GITHUB_REPO}/releases/download/{tag}/checksums.txt");
        if let Ok(bytes) =
            http_get_bytes_cancellable_with_proxy(&url, 20, MAX_CHECKSUMS_BYTES, cancel_flag, proxy_override)
        {
            if let Ok(txt) = std::str::from_utf8(&bytes) {
                if let Some(sha) = parse_checksum_for_asset(txt, asset_name) {
                    return Some((tag.clone(), sha));
                }
            }
        }
    }
    None
}

fn prefer_cn_mirrors() -> bool {
    prefer_cn_mirrors_with_override(None)
}

fn prefer_cn_mirrors_with_override(override_val: Option<bool>) -> bool {
    if let Some(explicit) = override_val {
        if explicit {
            return true;
        }
    }
    if env::var("PAPERFORGE_PREFER_CN_MIRROR")
        .map(|v| v.trim() == "1" || v.eq_ignore_ascii_case("true"))
        .unwrap_or(false)
    {
        return true;
    }
    for key in ["LC_ALL", "LANG"] {
        if let Ok(v) = env::var(key) {
            if v.to_ascii_lowercase().starts_with("zh") {
                return true;
            }
        }
    }
    false
}

fn github_candidate_urls_with_pref(direct_url: &str, prefer_cn: bool) -> Vec<String> {
    let mirrors = [
        format!("https://ghfast.top/{direct_url}"),
        format!("https://gh-proxy.com/{direct_url}"),
    ];
    if prefer_cn {
        vec![mirrors[0].clone(), mirrors[1].clone(), direct_url.to_string()]
    } else {
        vec![direct_url.to_string(), mirrors[0].clone(), mirrors[1].clone()]
    }
}

fn github_candidate_urls(direct_url: &str) -> Vec<String> {
    github_candidate_urls_with_pref(direct_url, prefer_cn_mirrors())
}

fn sha256_lower(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

fn extract_uv_from_zip(archive_bytes: &[u8], dest_exe: &Path) -> Result<(), String> {
    let reader = Cursor::new(archive_bytes);
    let mut archive = zip::ZipArchive::new(reader).map_err(|e| format!("Invalid uv zip: {e}"))?;
    for i in 0..archive.len() {
        let mut entry = archive.by_index(i).map_err(|e| e.to_string())?;
        let name = entry.name().replace('\\', "/");
        if name == "uv.exe" || name.ends_with("/uv.exe") {
            let mut out_bytes = Vec::new();
            entry.read_to_end(&mut out_bytes).map_err(|e| e.to_string())?;
            atomic_write_bytes(dest_exe, &out_bytes).map_err(|e| e.to_string())?;
            return Ok(());
        }
    }
    Err("uv.exe not found inside zip archive".into())
}

fn extract_uv_from_targz(archive_bytes: &[u8], dest_bin: &Path) -> Result<(), String> {
    let gz = flate2::read::GzDecoder::new(Cursor::new(archive_bytes));
    let mut tar_archive = tar::Archive::new(gz);
    for entry_res in tar_archive.entries().map_err(|e| e.to_string())? {
        let mut entry = entry_res.map_err(|e| e.to_string())?;
        if !entry.header().entry_type().is_file() {
            continue;
        }
        let path_str = entry
            .path()
            .map(|p| p.to_string_lossy().replace('\\', "/"))
            .unwrap_or_default();
        if path_str == "uv" || path_str.ends_with("/uv") {
            let mut out_bytes = Vec::new();
            entry.read_to_end(&mut out_bytes).map_err(|e| e.to_string())?;
            atomic_write_bytes(dest_bin, &out_bytes).map_err(|e| e.to_string())?;
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                fs::set_permissions(dest_bin, fs::Permissions::from_mode(0o755))
                    .map_err(|e| e.to_string())?;
            }
            return Ok(());
        }
    }
    Err("uv binary not found inside tar.gz archive".into())
}

fn find_or_install_uv(
    home: &Path,
    log_path: &Path,
    cancel_flag: Option<&AtomicBool>,
    proxy_override: Option<&str>,
    prefer_cn: bool,
) -> Result<PathBuf, String> {
    if is_cancelled(cancel_flag) {
        return Err("Runtime job cancelled".into());
    }
    let bin_name = if cfg!(windows) { "uv.exe" } else { "uv" };
    let local_uv = home.join(".paperforge").join("runtime").join("bin").join(bin_name);
    if local_uv.is_file() {
        return Ok(local_uv);
    }
    if let Ok(path_env) = env::var("PATH") {
        for dir in env::split_paths(&path_env) {
            let cand = dir.join(bin_name);
            if cand.is_file() {
                return Ok(cand);
            }
        }
    }

    let (asset, expected_sha, kind) =
        uv_target_asset_and_sha().ok_or_else(|| "Unsupported OS/architecture for uv".to_string())?;
    let direct_url = format!("https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/{asset}");
    let urls = github_candidate_urls_with_pref(&direct_url, prefer_cn);

    let mut archive_bytes: Option<Vec<u8>> = None;
    for url in &urls {
        if is_cancelled(cancel_flag) {
            return Err("Runtime job cancelled".into());
        }
        append_log(log_path, &format!("[PaperForge] Downloading uv ({UV_VERSION}) from {url} ..."));
        if let Ok(bytes) =
            http_get_bytes_cancellable_with_proxy(url, 60, MAX_ARCHIVE_BYTES, cancel_flag, proxy_override)
        {
            let actual = sha256_lower(&bytes);
            if actual == expected_sha {
                archive_bytes = Some(bytes);
                break;
            }
            append_log(
                log_path,
                &format!("[PaperForge] SHA-256 mismatch for {url}: got {actual}, want {expected_sha}"),
            );
        }
    }

    if is_cancelled(cancel_flag) {
        return Err("Runtime job cancelled".into());
    }
    let bytes = archive_bytes
        .ok_or_else(|| "Failed to download and SHA-256 verify portable uv.".to_string())?;
    if let Some(parent) = local_uv.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    if kind == "zip" {
        extract_uv_from_zip(&bytes, &local_uv)?;
    } else {
        extract_uv_from_targz(&bytes, &local_uv)?;
    }
    append_log(log_path, &format!("[PaperForge] Portable uv ready at {}", local_uv.display()));
    Ok(local_uv)
}

fn run_logged_command_cancellable(
    exe: &Path,
    args: &[&str],
    envs: &[(&str, &str)],
    log_path: &Path,
    cancel_flag: Option<&AtomicBool>,
    active_child_pid: Option<&AtomicU32>,
) -> Result<(), String> {
    if is_cancelled(cancel_flag) {
        return Err("Runtime job cancelled".into());
    }
    let mut cmd = Command::new(exe);
    cmd.args(args)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    for (k, _) in env::vars() {
        if CREDENTIAL_ENV_PREFIXES.iter().any(|p| k.starts_with(p)) {
            cmd.env_remove(&k);
        }
    }
    for (k, v) in envs {
        cmd.env(k, v);
    }
    configure_worker_command(&mut cmd);

    let mut child = cmd
        .spawn()
        .map_err(|e| format!("Failed to spawn {}: {e}", exe.display()))?;
    attach_child_to_job(&child);
    if let Some(pid_slot) = active_child_pid {
        pid_slot.store(child.id(), Ordering::SeqCst);
    }

    let stdout = child.stdout.take();
    let stderr = child.stderr.take();
    let log_err = log_path.to_path_buf();
    let err_thread = std::thread::spawn(move || {
        if let Some(pipe) = stderr {
            let reader = BufReader::new(pipe);
            for line in reader.lines().map_while(Result::ok) {
                append_log(&log_err, &line);
            }
        }
    });
    let log_out = log_path.to_path_buf();
    let out_thread = std::thread::spawn(move || {
        if let Some(pipe) = stdout {
            let reader = BufReader::new(pipe);
            for line in reader.lines().map_while(Result::ok) {
                append_log(&log_out, &line);
            }
        }
    });

    let status = loop {
        match child.try_wait() {
            Ok(Some(st)) => break Ok(st),
            Ok(None) => {
                if is_cancelled(cancel_flag) {
                    kill_process_tree(&mut child);
                    let _ = child.wait();
                    break Err("Runtime job cancelled".to_string());
                }
                std::thread::sleep(Duration::from_millis(50));
            }
            Err(e) => break Err(e.to_string()),
        }
    };
    if let Some(pid_slot) = active_child_pid {
        pid_slot.store(0, Ordering::SeqCst);
    }
    let _ = out_thread.join();
    let _ = err_thread.join();

    let st = status?;
    if st.success() {
        Ok(())
    } else {
        Err(format!(
            "{} exited with code {}",
            exe.file_name().and_then(|s| s.to_str()).unwrap_or("cmd"),
            st.code().unwrap_or(1)
        ))
    }
}

/// Execute the full cross-platform runtime setup in pure Rust without any OS shell script.
pub fn install_runtime_native<F>(
    action: &str,
    version: &str,
    on_phase: F,
) -> Result<PathBuf, String>
where
    F: Fn(&str, i64, i64),
{
    install_runtime_native_cancellable(action, version, None, None, on_phase)
}

pub fn install_runtime_native_cancellable<F>(
    action: &str,
    version: &str,
    cancel_flag: Option<&AtomicBool>,
    active_child_pid: Option<&AtomicU32>,
    on_phase: F,
) -> Result<PathBuf, String>
where
    F: Fn(&str, i64, i64),
{
    install_runtime_native_with_opts(
        action,
        version,
        &RuntimeInstallOptions::default(),
        cancel_flag,
        active_child_pid,
        on_phase,
    )
}

pub fn install_runtime_native_with_opts<F>(
    action: &str,
    version: &str,
    opts: &RuntimeInstallOptions,
    cancel_flag: Option<&AtomicBool>,
    active_child_pid: Option<&AtomicU32>,
    on_phase: F,
) -> Result<PathBuf, String>
where
    F: Fn(&str, i64, i64),
{
    let home = user_home_dir()?;
    let log_path = installer_log_path(&home);
    if let Ok(meta) = fs::metadata(&log_path) {
        if meta.len() > 1_048_576 {
            let _ = fs::rename(&log_path, log_path.with_extension("log.1"));
        }
    }

    let action_clean = match action {
        "install" | "update" | "repair" => action,
        _ => "install",
    };
    let pep440 = normalize_pep440(version);
    let clean_tag = version.trim().trim_start_matches(['v', 'V']);
    let spec = if pep440.is_empty() {
        "paperforge[vector]".to_string()
    } else {
        format!("paperforge[vector]=={pep440}")
    };
    let explicit_proxy = opts
        .proxy_url
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty());
    let prefer_cn = prefer_cn_mirrors_with_override(opts.prefer_cn_mirror);

    let rt_root = home.join(".paperforge").join("runtime");
    let cache_dir = rt_root.join("cache").join("uv");
    let wheel_dir = rt_root.join("cache").join("wheels");
    let py_dir = rt_root.join("python");
    let boot_dir = rt_root.join(".bootstrap-uv");
    let _ = fs::create_dir_all(&cache_dir);
    let _ = fs::create_dir_all(&wheel_dir);
    let _ = fs::create_dir_all(&py_dir);

    let res: Result<PathBuf, String> = (|| {
        on_phase("downloading_uv", 1, 5);
        let uv_bin = find_or_install_uv(&home, &log_path, cancel_flag, explicit_proxy, prefer_cn)?;

        let cache_str = cache_dir.to_string_lossy().into_owned();
        let py_dir_str = py_dir.to_string_lossy().into_owned();
        let os_proxy_fallback = if explicit_proxy.is_some() {
            None
        } else if resolve_proxy_from_env().is_none() {
            detect_os_system_proxy()
        } else {
            None
        };
        let mut base_envs: Vec<(&str, &str)> = vec![
            ("UV_CACHE_DIR", cache_str.as_str()),
            ("UV_PYTHON_INSTALL_DIR", py_dir_str.as_str()),
            ("UV_LINK_MODE", "hardlink"),
            ("UV_PYTHON_DOWNLOADS", "automatic"),
        ];
        if prefer_cn {
            base_envs.push(("PAPERFORGE_PREFER_CN_MIRROR", "1"));
        }
        if let Some(px) = explicit_proxy.or(os_proxy_fallback.as_deref()) {
            base_envs.push(("PAPERFORGE_PROXY", px));
            base_envs.push(("HTTPS_PROXY", px));
            base_envs.push(("HTTP_PROXY", px));
            base_envs.push(("https_proxy", px));
            base_envs.push(("http_proxy", px));
            base_envs.push(("NO_PROXY", "localhost,127.0.0.1,::1"));
            base_envs.push(("no_proxy", "localhost,127.0.0.1,::1"));
        }

        on_phase("installing_python", 2, 5);
        append_log(&log_path, "[PaperForge] Installing managed Python 3.12 via uv ...");
        let mut cn_py_envs = base_envs.to_vec();
        cn_py_envs.push((
            "UV_PYTHON_INSTALL_MIRROR",
            "https://registry.npmmirror.com/-/binary/python-build-standalone",
        ));
        let py_attempts: [&[(&str, &str)]; 2] = if prefer_cn {
            [cn_py_envs.as_slice(), base_envs.as_slice()]
        } else {
            [base_envs.as_slice(), cn_py_envs.as_slice()]
        };
        let mut py_ok = false;
        let mut py_err = String::new();
        for env_set in py_attempts {
            if is_cancelled(cancel_flag) {
                return Err("Runtime job cancelled".into());
            }
            match run_logged_command_cancellable(
                &uv_bin,
                &["python", "install", "3.12"],
                env_set,
                &log_path,
                cancel_flag,
                active_child_pid,
            ) {
                Ok(()) => {
                    py_ok = true;
                    break;
                }
                Err(e) => {
                    py_err = e;
                }
            }
        }
        if !py_ok {
            return Err(py_err);
        }

        let boot_str = boot_dir.to_string_lossy().into_owned();
        run_logged_command_cancellable(
            &uv_bin,
            &["venv", "--clear", "--python", "3.12", &boot_str],
            &base_envs,
            &log_path,
            cancel_flag,
            active_child_pid,
        )?;
        let boot_py = if cfg!(windows) {
            boot_dir.join("Scripts").join("python.exe")
        } else {
            boot_dir.join("bin").join("python")
        };
        let boot_py_str = boot_py.to_string_lossy().into_owned();

        on_phase("downloading_wheel", 3, 5);
        if !pep440.is_empty() && !clean_tag.is_empty() {
            let wheel_name = format!("paperforge-{pep440}-py3-none-any.whl");
            let wheel_file = wheel_dir.join(&wheel_name);
            let tags = candidate_release_tags(clean_tag, &pep440);
            let official_checksum =
                fetch_official_release_checksum(&tags, &wheel_name, cancel_flag, explicit_proxy);

            if wheel_file.is_file() {
                let valid_cached = fs::read(&wheel_file)
                    .ok()
                    .is_some_and(|existing| {
                        is_valid_wheel_zip(&existing)
                            && official_checksum
                                .as_ref()
                                .is_some_and(|(_, exp)| sha256_lower(&existing) == *exp)
                    });
                if !valid_cached {
                    append_log(
                        &log_path,
                        &format!("[PaperForge] Removing unverified or corrupt cached wheel {wheel_name}"),
                    );
                    let _ = fs::remove_file(&wheel_file);
                }
            }

            if !wheel_file.is_file() {
                if let Some((verified_tag, expected_sha)) = official_checksum {
                    let w_direct = format!(
                        "https://github.com/{GITHUB_REPO}/releases/download/{verified_tag}/{wheel_name}"
                    );
                    for wu in github_candidate_urls_with_pref(&w_direct, prefer_cn) {
                        if is_cancelled(cancel_flag) {
                            return Err("Runtime job cancelled".into());
                        }
                        append_log(&log_path, &format!("[PaperForge] Downloading wheel {wu} ..."));
                        if let Ok(bytes) = http_get_bytes_cancellable_with_proxy(
                            &wu,
                            60,
                            MAX_ARCHIVE_BYTES,
                            cancel_flag,
                            explicit_proxy,
                        ) {
                            let actual_sha = sha256_lower(&bytes);
                            if actual_sha != expected_sha {
                                append_log(
                                    &log_path,
                                    &format!(
                                        "[PaperForge] Wheel SHA-256 mismatch for {wu}: got {actual_sha}, want {expected_sha}"
                                    ),
                                );
                                continue;
                            }
                            if !is_valid_wheel_zip(&bytes) {
                                append_log(
                                    &log_path,
                                    &format!("[PaperForge] Wheel ZIP integrity check failed for {wu}"),
                                );
                                continue;
                            }
                            if atomic_write_bytes(&wheel_file, &bytes).is_ok() {
                                break;
                            }
                        }
                    }
                } else {
                    append_log(
                        &log_path,
                        "[PaperForge] Authoritative GitHub checksums.txt unavailable; skipping wheel pre-cache.",
                    );
                }
            }
        }

        if is_cancelled(cancel_flag) {
            return Err("Runtime job cancelled".into());
        }
        on_phase("installing_paperforge", 4, 5);
        append_log(&log_path, &format!("[PaperForge] Installing {spec} ..."));
        let has_wheels = fs::read_dir(&wheel_dir)
            .map(|rd| {
                rd.flatten()
                    .any(|e| e.path().extension().and_then(|s| s.to_str()) == Some("whl"))
            })
            .unwrap_or(false);
        let wheel_dir_str = wheel_dir.to_string_lossy().into_owned();

        let mirrors: [&str; 3] = if prefer_cn_mirrors() {
            [
                "https://pypi.tuna.tsinghua.edu.cn/simple",
                "https://mirrors.aliyun.com/pypi/simple/",
                "",
            ]
        } else {
            [
                "",
                "https://pypi.tuna.tsinghua.edu.cn/simple",
                "https://mirrors.aliyun.com/pypi/simple/",
            ]
        };
        let mut installed = false;
        for idx in mirrors {
            if is_cancelled(cancel_flag) {
                return Err("Runtime job cancelled".into());
            }
            let mut args: Vec<&str> = vec!["pip", "install", "--python", &boot_py_str, "--upgrade"];
            if has_wheels {
                args.push("--find-links");
                args.push(&wheel_dir_str);
            }
            if !idx.is_empty() {
                args.push("--index-url");
                args.push(idx);
            }
            args.push(&spec);
            if run_logged_command_cancellable(
                &uv_bin,
                &args,
                &base_envs,
                &log_path,
                cancel_flag,
                active_child_pid,
            )
            .is_ok()
            {
                installed = true;
                break;
            }
        }
        if !installed {
            return Err("uv pip install failed across default and mirror indexes.".into());
        }

        if is_cancelled(cancel_flag) {
            return Err("Runtime job cancelled".into());
        }
        on_phase("verifying_runtime", 5, 5);
        append_log(&log_path, "[PaperForge] Publishing verified runtime environment...");
        let expected_ver = if pep440.is_empty() {
            version.trim()
        } else {
            pep440.as_str()
        };
        let mut rt_args = vec!["-m", "paperforge", "runtime", action_clean];
        if !expected_ver.is_empty() {
            rt_args.push("--expected-version");
            rt_args.push(expected_ver);
        }
        let mut step5_envs = base_envs.clone();
        if has_wheels {
            step5_envs.push(("PAPERFORGE_NO_GITHUB_WHEEL", "1"));
        }
        run_logged_command_cancellable(
            &boot_py,
            &rt_args,
            &step5_envs,
            &log_path,
            cancel_flag,
            active_child_pid,
        )?;
        Ok(log_path.clone())
    })();

    match &res {
        Ok(_) => append_log(&log_path, INSTALLER_FINISHED_MARKER),
        Err(msg) => {
            append_log(&log_path, msg);
            append_log(&log_path, INSTALLER_FAILED_MARKER);
        }
    }
    res
}

/// Sanity test helpers so checksums/normalization stay locked in cargo test.
#[cfg(test)]
pub fn verify_sha256_bytes(bytes: &[u8], expected_hex: &str) -> bool {
    sha256_lower(bytes) == expected_hex.to_ascii_lowercase()
}

#[cfg(test)]
mod tests {
    use super::{
        matches_no_proxy, parse_mac_scutil_proxy_output, parse_windows_reg_proxy_output,
        resolve_proxy_for_url_with_lookup, resolve_proxy_from_lookup,
    };

    #[test]
    fn resolve_proxy_honors_priority_and_lowercase() {
        let p = resolve_proxy_from_lookup(|k| match k {
            "https_proxy" => Some(" http://127.0.0.1:7897 ".into()),
            "HTTP_PROXY" => Some("http://127.0.0.1:8080".into()),
            _ => None,
        });
        assert_eq!(p.as_deref(), Some("http://127.0.0.1:7897"));

        let override_p = resolve_proxy_from_lookup(|k| match k {
            "PAPERFORGE_PROXY" => Some("http://127.0.0.1:9000".into()),
            "HTTPS_PROXY" => Some("http://127.0.0.1:7897".into()),
            _ => None,
        });
        assert_eq!(override_p.as_deref(), Some("http://127.0.0.1:9000"));
    }

    #[test]
    fn parses_windows_and_macos_system_proxy_outputs() {
        let reg_out = "\
HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings\r\n\
    ProxyEnable    REG_DWORD    0x1\r\n\
    ProxyServer    REG_SZ    127.0.0.1:7897\r\n";
        assert_eq!(
            parse_windows_reg_proxy_output(reg_out).as_deref(),
            Some("http://127.0.0.1:7897")
        );

        let reg_disabled = "\
    ProxyEnable    REG_DWORD    0x0\r\n\
    ProxyServer    REG_SZ    127.0.0.1:7897\r\n";
        assert_eq!(parse_windows_reg_proxy_output(reg_disabled), None);

        let mac_out = "<dictionary> {\n  HTTPSEnable : 1\n  HTTPSProxy : 127.0.0.1\n  HTTPSPort : 7897\n}\n";
        assert_eq!(
            parse_mac_scutil_proxy_output(mac_out).as_deref(),
            Some("http://127.0.0.1:7897")
        );
    }

    #[test]
    fn no_proxy_bypasses_matching_urls_consistently() {
        assert!(matches_no_proxy("https://github.com/a/b", "*"));
        assert!(matches_no_proxy("https://github.com/a/b", "github.com"));
        assert!(matches_no_proxy("https://api.github.com/a/b", ".github.com:443"));
        assert!(matches_no_proxy("http://127.0.0.1:8080/x", "localhost,127.*"));
        assert!(!matches_no_proxy("https://github.com/a/b", "localhost,*.internal"));

        let bypassed = resolve_proxy_for_url_with_lookup("https://api.github.com/x", |k| match k {
            "NO_PROXY" => Some("localhost,.github.com".into()),
            "HTTPS_PROXY" => Some("http://127.0.0.1:7897".into()),
            _ => None,
        });
        assert_eq!(bypassed, None);

        let proxied = resolve_proxy_for_url_with_lookup("https://pypi.org/simple", |k| match k {
            "NO_PROXY" => Some("localhost,.github.com".into()),
            "HTTPS_PROXY" => Some("http://127.0.0.1:7897".into()),
            _ => None,
        });
        assert_eq!(proxied.as_deref(), Some("http://127.0.0.1:7897"));
    }
}
