//! Cross-platform OS primitives (Windows, macOS, Linux):
//! - Live RSS memory probe (`process_rss_bytes`)
//! - Zombie-aware & reparenting-aware parent PID liveness (`is_pid_alive`)
//! - Isolated process-group worker spawning & tree termination (`kill_process_tree`)
//! - Crash-safe atomic file writes preserving POSIX permissions (`atomic_write_bytes`)

use std::fs::{self, OpenOptions};
use std::io::{self, Write};
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

pub fn now_unix_secs() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

pub fn current_ppid() -> Option<u32> {
    #[cfg(unix)]
    {
        Some(std::os::unix::process::parent_id())
    }
    #[cfg(not(unix))]
    {
        None
    }
}

#[cfg(windows)]
mod win_ffi {
    use std::ffi::c_void;

    #[repr(C)]
    pub struct ProcessMemoryCounters {
        pub cb: u32,
        pub page_fault_count: u32,
        pub peak_working_set_size: usize,
        pub working_set_size: usize,
        pub quota_peak_paged_pool_usage: usize,
        pub quota_paged_pool_usage: usize,
        pub quota_peak_non_paged_pool_usage: usize,
        pub quota_non_paged_pool_usage: usize,
        pub pagefile_usage: usize,
        pub peak_pagefile_usage: usize,
    }

    pub const SYNCHRONIZE: u32 = 0x0010_0000;
    pub const WAIT_TIMEOUT: u32 = 0x0000_0102;
    pub const ERROR_ACCESS_DENIED: u32 = 5;

    #[link(name = "kernel32")]
    extern "system" {
        pub fn GetCurrentProcess() -> *mut c_void;
        pub fn K32GetProcessMemoryInfo(
            process: *mut c_void,
            ppsmem_counters: *mut ProcessMemoryCounters,
            cb: u32,
        ) -> i32;
        pub fn OpenProcess(desired_access: u32, inherit_handle: i32, process_id: u32) -> *mut c_void;
        pub fn WaitForSingleObject(handle: *mut c_void, milliseconds: u32) -> u32;
        pub fn CloseHandle(object: *mut c_void) -> i32;
        pub fn GetLastError() -> u32;
    }
}

pub fn process_rss_bytes() -> u64 {
    #[cfg(windows)]
    unsafe {
        let mut counters = std::mem::zeroed::<win_ffi::ProcessMemoryCounters>();
        counters.cb = std::mem::size_of::<win_ffi::ProcessMemoryCounters>() as u32;
        let ok = win_ffi::K32GetProcessMemoryInfo(
            win_ffi::GetCurrentProcess(),
            &mut counters,
            counters.cb,
        );
        if ok != 0 {
            return counters.working_set_size as u64;
        }
        0
    }

    #[cfg(target_os = "linux")]
    {
        if let Ok(statm) = fs::read_to_string("/proc/self/statm") {
            if let Some(res_pages) = statm.split_whitespace().nth(1) {
                if let Ok(pages) = res_pages.parse::<u64>() {
                    return pages.saturating_mul(4096);
                }
            }
        }
        0
    }

    #[cfg(target_os = "macos")]
    {
        let pid_str = std::process::id().to_string();
        if let Ok(out) = Command::new("/bin/ps")
            .args(["-o", "rss=", "-p", &pid_str])
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .output()
        {
            if let Ok(s) = String::from_utf8(out.stdout) {
                if let Ok(kb) = s.trim().parse::<u64>() {
                    return kb.saturating_mul(1024);
                }
            }
        }
        0
    }

    #[cfg(not(any(windows, target_os = "linux", target_os = "macos")))]
    {
        0
    }
}

#[cfg_attr(not(target_os = "linux"), allow(dead_code))]
pub fn is_linux_zombie_stat(stat_text: &str) -> bool {
    if let Some(rparen) = stat_text.rfind(')') {
        if let Some(rest) = stat_text.get(rparen + 2..rparen + 3) {
            return matches!(rest, "Z" | "X" | "x");
        }
    }
    false
}

pub fn is_pid_alive(pid: u32, initial_ppid: Option<u32>) -> bool {
    if pid == 0 {
        return true;
    }

    #[cfg(unix)]
    {
        if let Some(init_ppid) = initial_ppid {
            if pid == init_ppid && std::os::unix::process::parent_id() != init_ppid {
                return false;
            }
        }
    }
    #[cfg(not(unix))]
    let _ = initial_ppid;

    #[cfg(windows)]
    unsafe {
        let handle = win_ffi::OpenProcess(win_ffi::SYNCHRONIZE, 0, pid);
        if handle.is_null() {
            return win_ffi::GetLastError() == win_ffi::ERROR_ACCESS_DENIED;
        }
        let rc = win_ffi::WaitForSingleObject(handle, 0);
        let _ = win_ffi::CloseHandle(handle);
        rc == win_ffi::WAIT_TIMEOUT
    }

    #[cfg(unix)]
    {
        #[cfg(target_os = "linux")]
        {
            let stat_path = format!("/proc/{pid}/stat");
            if let Ok(txt) = fs::read_to_string(stat_path) {
                if is_linux_zombie_stat(&txt) {
                    return false;
                }
            }
        }
        extern "C" {
            fn kill(pid: i32, sig: i32) -> i32;
        }
        let rc = unsafe { kill(pid as i32, 0) };
        if rc == 0 {
            return true;
        }
        matches!(io::Error::last_os_error().raw_os_error(), Some(1)) // EPERM == 1 => alive
    }
}

pub fn configure_worker_command(cmd: &mut Command) {
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        cmd.process_group(0);
    }
}

pub fn kill_process_tree(child: &mut Child) {
    if let Ok(Some(_)) = child.try_wait() {
        return;
    }
    let pid = child.id();

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        let _ = Command::new("taskkill")
            .args(["/T", "/F", "/PID", &pid.to_string()])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .creation_flags(CREATE_NO_WINDOW)
            .status();
    }

    #[cfg(unix)]
    {
        extern "C" {
            fn kill(pid: i32, sig: i32) -> i32;
        }
        const SIGKILL: i32 = 9;
        // Negative PID sends SIGKILL to the isolated worker process group (`process_group(0)`).
        unsafe {
            let _ = kill(-(pid as i32), SIGKILL);
        }
    }

    let _ = child.kill();
}

pub fn atomic_write_bytes(path: &Path, data: &[u8]) -> io::Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let file_name = path
        .file_name()
        .and_then(|s| s.to_str())
        .unwrap_or("file");
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    let tmp_name = format!(".{file_name}.{}.{nonce}.tmp", std::process::id());
    let tmp_path = path.with_file_name(tmp_name);

    {
        let mut f = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&tmp_path)?;
        f.write_all(data)?;
        f.sync_all()?;
    }

    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        if let Ok(meta) = fs::metadata(path) {
            let mode = meta.permissions().mode() & 0o777;
            let _ = fs::set_permissions(&tmp_path, fs::Permissions::from_mode(mode));
        }
    }

    let mut last_err = None;
    for attempt in 0..4 {
        match fs::rename(&tmp_path, path) {
            Ok(()) => return Ok(()),
            Err(e) => {
                last_err = Some(e);
                thread::sleep(Duration::from_millis(15 * (attempt + 1)));
            }
        }
    }
    let _ = fs::remove_file(&tmp_path);
    Err(last_err.unwrap_or_else(|| io::Error::other("atomic rename failed")))
}
