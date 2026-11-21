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

use crate::platform::{atomic_write_bytes, configure_worker_command};
use sha2::{Digest, Sha256};
use std::env;
use std::fs::{self, OpenOptions};
use std::io::{BufRead, BufReader, Cursor, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

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

fn append_log(log_path: &Path, line: &str) {
    if let Some(parent) = log_path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    if let Ok(mut f) = OpenOptions::new().create(true).append(true).open(log_path) {
        let _ = writeln!(f, "{line}");
        let _ = f.flush();
    }
}

fn http_get_bytes(url: &str, timeout_secs: u64) -> Result<Vec<u8>, String> {
    let agent = ureq::AgentBuilder::new()
        .timeout(std::time::Duration::from_secs(timeout_secs))
        .build();
    let resp = agent
        .get(url)
        .set("User-Agent", "PaperForge-Native-Daemon/2.0")
        .call()
        .map_err(|e| format!("HTTP error for {url}: {e}"))?;
    let mut reader = resp.into_reader();
    let mut buf = Vec::new();
    reader
        .read_to_end(&mut buf)
        .map_err(|e| format!("Read body failed for {url}: {e}"))?;
    Ok(buf)
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

fn find_or_install_uv(home: &Path, log_path: &Path) -> Result<PathBuf, String> {
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
    let mirror_url = format!("https://ghfast.top/{direct_url}");

    let mut archive_bytes: Option<Vec<u8>> = None;
    for url in [&direct_url, &mirror_url] {
        append_log(log_path, &format!("[PaperForge] Downloading uv ({UV_VERSION}) from {url} ..."));
        if let Ok(bytes) = http_get_bytes(url, 120) {
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

fn run_logged_command(
    exe: &Path,
    args: &[&str],
    envs: &[(&str, &str)],
    log_path: &Path,
) -> Result<(), String> {
    let mut cmd = Command::new(exe);
    cmd.args(args)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    for (k, v) in envs {
        cmd.env(k, v);
    }
    configure_worker_command(&mut cmd);

    let mut child = cmd
        .spawn()
        .map_err(|e| format!("Failed to spawn {}: {e}", exe.display()))?;
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
    if let Some(pipe) = stdout {
        let reader = BufReader::new(pipe);
        for line in reader.lines().map_while(Result::ok) {
            append_log(log_path, &line);
        }
    }
    let _ = err_thread.join();
    let status = child.wait().map_err(|e| e.to_string())?;
    if status.success() {
        Ok(())
    } else {
        Err(format!(
            "{} exited with code {}",
            exe.file_name().and_then(|s| s.to_str()).unwrap_or("cmd"),
            status.code().unwrap_or(1)
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
        let uv_bin = find_or_install_uv(&home, &log_path)?;

        let cache_str = cache_dir.to_string_lossy().into_owned();
        let py_dir_str = py_dir.to_string_lossy().into_owned();
        let base_envs = [
            ("UV_CACHE_DIR", cache_str.as_str()),
            ("UV_PYTHON_INSTALL_DIR", py_dir_str.as_str()),
            ("UV_LINK_MODE", "hardlink"),
            ("UV_PYTHON_DOWNLOADS", "automatic"),
        ];

        on_phase("installing_python", 2, 5);
        append_log(&log_path, "[PaperForge] Installing managed Python 3.12 via uv ...");
        if run_logged_command(&uv_bin, &["python", "install", "3.12"], &base_envs, &log_path).is_err() {
            let mut mirror_envs = base_envs.to_vec();
            mirror_envs.push((
                "UV_PYTHON_INSTALL_MIRROR",
                "https://registry.npmmirror.com/-/binary/python-build-standalone",
            ));
            run_logged_command(&uv_bin, &["python", "install", "3.12"], &mirror_envs, &log_path)?;
        }

        let boot_str = boot_dir.to_string_lossy().into_owned();
        run_logged_command(
            &uv_bin,
            &["venv", "--clear", "--python", "3.12", &boot_str],
            &base_envs,
            &log_path,
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
            if !wheel_file.is_file() {
                let w1 = format!("https://github.com/{GITHUB_REPO}/releases/download/{clean_tag}/{wheel_name}");
                let w2 = format!("https://ghfast.top/{w1}");
                for wu in [&w1, &w2] {
                    append_log(&log_path, &format!("[PaperForge] Downloading wheel {wu} ..."));
                    if let Ok(bytes) = http_get_bytes(wu, 90) {
                        if bytes.starts_with(b"PK") && atomic_write_bytes(&wheel_file, &bytes).is_ok() {
                            break;
                        }
                    }
                }
            }
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

        let mirrors = [
            "",
            "https://pypi.tuna.tsinghua.edu.cn/simple",
            "https://mirrors.aliyun.com/pypi/simple/",
        ];
        let mut installed = false;
        for idx in mirrors {
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
            if run_logged_command(&uv_bin, &args, &base_envs, &log_path).is_ok() {
                installed = true;
                break;
            }
        }
        if !installed {
            return Err("uv pip install failed across default and mirror indexes.".into());
        }

        on_phase("verifying_runtime", 5, 5);
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
        run_logged_command(&boot_py, &rt_args, &base_envs, &log_path)?;
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
