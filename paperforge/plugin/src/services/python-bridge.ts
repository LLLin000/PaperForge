import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { execFile, execFileSync, spawn, exec } from "child_process";
import type { PaperForgeSettings } from "../constants";

// ── Types ──

export interface PythonResult {
  path: string;
  source: "manual" | "auto-detected";
  extraArgs: string[];
}

export interface InstallCommand {
  cmd: string;
  url: string;
  args: string[];
  pypiArgs: string[];
  gitArgs: string[];
  timeout: number;
}

export interface SubprocessResult {
  stdout: string;
  stderr: string;
  exitCode: number;
  elapsed: number;
}

export interface ErrorClassification {
  type: string;
  message: string;
  recoverable: boolean;
  action?: string;
}

export interface RuntimeStatus {
  status: string;
  version: string | null;
  type?: string;
  message?: string;
  recoverable?: boolean;
  action?: string;
}

export interface QueryPlanResult {
  ok: boolean;
  command: string;
  version: string;
  data: Record<string, unknown> | null;
  error: Record<string, unknown> | null;
}

// ── Cross-platform state ──

let _gitDir: string | null = null;
let _gitDirResolved = false;

// ── Runtime helpers ──

export function resolvePythonExecutable(vaultPath: string, settings: PaperForgeSettings | null | undefined, _fs: any, _execFileSync: any): PythonResult {
    const f = _fs || fs;
    const execSync = _execFileSync || execFileSync;

    if (settings && settings.python_path && settings.python_path.trim()) {
        const manualPath = settings.python_path.trim();
        if (f.existsSync(manualPath)) {
            return { path: manualPath, source: "manual", extraArgs: [] };
        }
    }

    const venvCandidates = [
        path.join(vaultPath, ".paperforge-test-venv", "Scripts", "python.exe"),
        path.join(vaultPath, ".venv", "Scripts", "python.exe"),
        path.join(vaultPath, "venv", "Scripts", "python.exe"),
    ];
    for (const candidate of venvCandidates) {
        try {
            if (f.existsSync(candidate)) {
                return { path: candidate, source: "auto-detected", extraArgs: [] };
            }
        } catch {}
    }

    const systemCandidates = [
        { path: "py", extraArgs: ["-3"] },
        { path: "python", extraArgs: [] },
        { path: "python3", extraArgs: [] },
    ];
    for (const candidate of systemCandidates) {
        try {
            const verOut = execSync(candidate.path, [...candidate.extraArgs, "--version"], {
                encoding: "utf-8", timeout: 5000, windowsHide: true,
            });
            if (verOut && verOut.toLowerCase().includes("python")) {
                return { path: candidate.path, source: "auto-detected", extraArgs: candidate.extraArgs };
            }
        } catch {}
    }

    return { path: "python", source: "auto-detected", extraArgs: [] };
}

export function getPluginVersion(app: any): string | null {
    try {
        const manifest = app && app.plugins && app.plugins.plugins &&
            app.plugins.plugins["paperforge"] && app.plugins.plugins["paperforge"].manifest;
        return (manifest && manifest.version) || null;
    } catch {
        return null;
    }
}

export function checkRuntimeVersion(pythonExe: string, pluginVersion: string | null, cwd: string, timeout: number | undefined, _execFile: any): Promise<{ status: string; pyVersion: string | null; pluginVersion: string | null; error: string | null }> {
    if (timeout === undefined) timeout = 10000;
    const exe = _execFile || execFile;

    return new Promise((resolve) => {
        exe(pythonExe, ["-c", "import paperforge; print(paperforge.__version__)"],
            { cwd, timeout },
            (err: any, stdout: any) => {
                if (err) {
                    resolve({ status: "not-installed", pyVersion: null, pluginVersion, error: err.message });
                    return;
                }
                const pyVer = (stdout && stdout.trim()) || null;
                if (pyVer === pluginVersion) {
                    resolve({ status: "match", pyVersion: pyVer, pluginVersion, error: null });
                } else {
                    resolve({ status: "mismatch", pyVersion: pyVer, pluginVersion, error: null });
                }
            });
    });
}

// ── Error helpers ──

export function classifyError(errorCode: string): ErrorClassification {
    const code = String(errorCode);
    const patterns: Record<string, ErrorClassification> = {
        ENOENT: { type: "python_missing", message: "Python executable not found", recoverable: true },
        "python-missing": { type: "python_missing", message: "Python executable not found", recoverable: true },
        MODULE_NOT_FOUND: { type: "import_failed", message: "PaperForge package not installed", recoverable: true },
        "import-failed": { type: "import_failed", message: "PaperForge package not installed", recoverable: true },
        "version-mismatch": { type: "version_mismatch", message: "Plugin and package versions differ", recoverable: true, action: "sync-runtime" },
        "pip-failed": { type: "pip_install_failure", message: "pip install command failed", recoverable: true },
        ETIMEDOUT: { type: "timeout", message: "Subprocess timed out", recoverable: true, action: "retry" },
        timeout: { type: "timeout", message: "Subprocess timed out", recoverable: true, action: "retry" },
        NO_PYTHON: { type: "no_python", message: "Python executable not found", recoverable: true, action: "open-setup" },
        VECTOR_NOT_BUILT: { type: "vectors_not_built", message: "Vector index has not been built yet", recoverable: true, action: "open-vector-settings" },
        VECTOR_CORRUPTED: { type: "vectors_corrupted", message: "Vector index is corrupted", recoverable: true, action: "force-rebuild" },
        MODEL_CHANGED: { type: "model_changed", message: "Embedding model has changed since vectors were built", recoverable: true, action: "rebuild-vectors" },
        BACKEND_UNAVAILABLE: { type: "backend_unavailable", message: "Python CLI search backend is not responding", recoverable: true, action: "run-doctor" },
        TIMEOUT: { type: "timeout", message: "Search timed out", recoverable: true, action: "retry" },
        INTERNAL_ERROR: { type: "internal_error", message: "An internal error occurred", recoverable: false },
    };
    const match = patterns[code];
    if (match) return { ...match };
    return { type: "unknown", message: String(errorCode), recoverable: false };
}

export function buildRuntimeInstallCommand(pythonExe: string, version: string, extraArgs: string[]): InstallCommand {
    if (extraArgs === undefined) extraArgs = [];
    const pypiPkg = `paperforge==${version}`;
    const gitUrl = `git+https://github.com/LLLin000/PaperForge.git@${version}`;
    const pypiArgs = [...extraArgs, "-m", "pip", "install", "--upgrade", pypiPkg];
    const gitArgs = [...extraArgs, "-m", "pip", "install", "--upgrade", gitUrl];
    return { cmd: pythonExe, url: gitUrl, args: gitArgs, pypiArgs, gitArgs, timeout: 120000 };
}

export function parseRuntimeStatus(err: any, stdout: any, stderr: any): RuntimeStatus {
    if (!err && stdout) {
        return { status: "ok", version: stdout.trim() };
    }
    if (err && err.code === "ENOENT") {
        const classified = classifyError("ENOENT");
        return { status: "error", version: null, ...classified };
    }
    if (stderr && stderr.includes("No module named paperforge")) {
        const classified = classifyError("import-failed");
        return { status: "error", version: null, ...classified };
    }
    if (err && err.killed) {
        const classified = classifyError("timeout");
        return { status: "error", version: null, ...classified };
    }
    if (stderr && stderr.includes("ModuleNotFoundError")) {
        const classified = classifyError("import-failed");
        return { status: "error", version: null, ...classified };
    }
    return { status: "error", version: null, type: "unknown",
        message: err ? err.message : String(stderr), recoverable: false };
}

// ── Action definitions ── (ACTIONS already in constants.ts)

export function buildCommandArgs(action: any, key: any, filter: any): string[] {
    const args = Array.isArray(action.args) ? [...action.args] : [];
    if (action.needsKey && key) args.push(key);
    if (action.needsFilter || filter) args.push("--all");
    return args;
}

export function runSubprocess(pythonExe: string, args: string[], cwd: string, timeout: number, _spawn: any, env?: any): Promise<SubprocessResult> {
    const sp = _spawn || spawn;

    return new Promise((resolve) => {
        const startTime = Date.now();
        const opts: any = { cwd, timeout, windowsHide: true };
        if (env) opts.env = env;
        const child = sp(pythonExe, args, opts);
        const stdoutChunks: string[] = [];
        const stderrChunks: string[] = [];

        child.stdout.on("data", (data: any) => { stdoutChunks.push(data.toString("utf-8")); });
        child.stderr.on("data", (data: any) => { stderrChunks.push(data.toString("utf-8")); });

        child.on("close", (code: any) => {
            resolve({ stdout: stdoutChunks.join(""), stderr: stderrChunks.join(""),
                exitCode: code, elapsed: Date.now() - startTime });
        });

        child.on("error", (err: any) => {
            resolve({ stdout: stdoutChunks.join(""),
                stderr: stderrChunks.join("") + "\n" + err.message,
                exitCode: -1, elapsed: Date.now() - startTime });
        });
    });
}

export function runQueryPlan(
  pythonExe: string,
  extraArgs: string[],
  vaultPath: string,
  query: string,
  intent: "discover" | "content" | "known-paper",
  timeout = 20000,
  _execFile?: any,
): Promise<QueryPlanResult> {
  const exe = _execFile || execFile;
  return new Promise((resolve) => {
    const args = [...extraArgs, "-m", "paperforge", "--vault", vaultPath, "query-plan", query, "--intent", intent, "--json"];
    exe(pythonExe, args, { cwd: vaultPath, timeout, windowsHide: true }, (err: any, stdout: any, stderr: any) => {
      if (err) {
        resolve({
          ok: false,
          command: "query-plan",
          version: "",
          data: null,
          error: { message: stderr || err.message || "query-plan failed" },
        });
        return;
      }
      try {
        resolve(JSON.parse(stdout));
      } catch (parseErr: any) {
        resolve({
          ok: false,
          command: "query-plan",
          version: "",
          data: null,
          error: { message: parseErr.message || "Invalid query-plan JSON" },
        });
      }
    });
  });
}

// ── Cross-platform Python and BBT detection (macOS/Linux) ──

export function resolveGitDir(): string | null {
    if (_gitDirResolved) return _gitDir;
    _gitDirResolved = true;
    try {
        let out: string;
        if (process.platform === 'win32') {
            const cmdExe = process.env.ComSpec || 'C:\\Windows\\System32\\cmd.exe';
            out = execFileSync(cmdExe, ['/c', 'where', 'git'], { timeout: 5000, windowsHide: true, encoding: 'utf-8' });
        } else {
            out = execFileSync('which', ['git'], { timeout: 5000, encoding: 'utf-8' });
        }
        if (out) {
            const line = out.split('\n')[0].trim();
            if (line) _gitDir = path.dirname(line);
        }
    } catch (_) {}
    return _gitDir;
}

export function paperforgeEnrichedEnv(): Record<string, string | undefined> {
    const env: Record<string, string | undefined> = { ...process.env };
    const plat = process.platform;
    const home = os.homedir();
    const extras: string[] = [];
    const gitDir = resolveGitDir();
    if (gitDir) extras.push(gitDir);
    if (plat === 'darwin') {
        extras.push('/opt/homebrew/bin', '/usr/local/bin', '/usr/bin', `${home}/.local/bin`);
    } else if (plat === 'linux') {
        extras.push('/usr/local/bin', '/usr/bin', `${home}/.local/bin`);
    }
    const cur = env.PATH || '';
    env.PATH = [...extras, cur].filter(Boolean).join(path.delimiter);
    return env;
}

export function shellQuoteForExec(cmd: string): string {
    if (!cmd) return "''";
    if (/[\s'"\\]/.test(cmd)) return `'${cmd.replace(/'/g, "'\\''")}'`;
    return cmd;
}

export function isLikelyAppleStubPython(resolvedAbsPath: string): boolean {
    const n = String(resolvedAbsPath).toLowerCase().replace(/\\/g, '/');
    return n.includes('commandlinetools') || n.includes('/library/developer/commandlinetools');
}

export function collectDarwinPythonCandidates(home: string): string[] {
    return [
        '/opt/homebrew/bin/python3',
        '/usr/local/bin/python3',
        path.join(home, '.local', 'bin', 'python3'),
        path.join(home, '.pyenv', 'shims', 'python3'),
        '/usr/bin/python3',
    ];
}

export function getPaperforgePythonCmd(): string {
    const plat = process.platform;
    const home = os.homedir();
    if (plat === 'darwin') {
        let stubFallback: string | null = null;
        for (const p of collectDarwinPythonCandidates(home)) {
            try {
                if (!p || !fs.existsSync(p)) continue;
                let resolved = p;
                try { resolved = fs.realpathSync(p); } catch (_) {}
                if (isLikelyAppleStubPython(resolved)) {
                    if (!stubFallback) stubFallback = p;
                    continue;
                }
                return p;
            } catch (_) {}
        }
        if (stubFallback) return stubFallback;
        return 'python3';
    }
    const candidates: string[] = [];
    if (plat === 'linux') {
        candidates.push('/usr/bin/python3', '/usr/local/bin/python3', path.join(home, '.local', 'bin', 'python3'), path.join(home, '.pyenv', 'shims', 'python3'));
    }
    for (const p of candidates) {
        try { if (p && fs.existsSync(p)) return p; } catch (_) {}
    }
    if (plat === 'win32') return 'python';
    return 'python3';
}

export function paperforgePythonExecArgs(scriptTail: string): string {
    const py = shellQuoteForExec(getPaperforgePythonCmd());
    return `${py} ${scriptTail}`;
}

export function tryExecPythonVersion(callback: any): void {
    const plat = process.platform;
    const home = os.homedir();
    const tried = new Set<string>();
    const list: string[] = [];
    if (plat === 'darwin') {
        const nonStub: string[] = [], stub: string[] = [];
        for (const p of collectDarwinPythonCandidates(home)) {
            try {
                if (!fs.existsSync(p)) continue;
                let resolved = p;
                try { resolved = fs.realpathSync(p); } catch (_) {}
                if (isLikelyAppleStubPython(resolved)) stub.push(p);
                else nonStub.push(p);
            } catch (_) {}
        }
        list.push(...nonStub, ...stub);
    } else if (plat === 'linux') {
        list.push('/usr/bin/python3', '/usr/local/bin/python3', path.join(home, '.local', 'bin', 'python3'), path.join(home, '.pyenv', 'shims', 'python3'));
    }
    list.push(plat === 'win32' ? 'python' : 'python3', 'python');
    const candidates = list.filter((c: string) => { if (!c || tried.has(c)) return false; tried.add(c); return true; });
    let i = 0;
    const next = () => {
        if (i >= candidates.length) { callback(new Error('Python not found'), '', null); return; }
        const py = candidates[i++];
        if (py.includes(path.sep) || py.startsWith('/')) {
            try { if (!fs.existsSync(py)) { next(); return; } } catch (_) { next(); return; }
        }
        exec(`${shellQuoteForExec(py)} --version`, { timeout: 8000, env: paperforgeEnrichedEnv() as any }, (err: any, stdout: any) => {
            if (!err && stdout) callback(null, stdout.trim(), py);
            else next();
        });
    };
    next();
}

export function dirLooksLikeBetterBibtexFolder(entryName: string): boolean {
    const compact = String(entryName).toLowerCase().replace(/[^a-z0-9]/g, '');
    return compact.includes('betterbibtex');
}

export function scanBbtDirectChildren(dir: string): boolean {
    if (!dir) return false;
    try {
        if (!fs.existsSync(dir)) return false;
        for (const entry of fs.readdirSync(dir)) {
            if (dirLooksLikeBetterBibtexFolder(entry)) return true;
        }
    } catch (_) {}
    return false;
}

export function scanBbtUnderProfiles(profilesDir: string): boolean {
    if (!profilesDir) return false;
    try {
        if (!fs.existsSync(profilesDir)) return false;
        for (const prof of fs.readdirSync(profilesDir)) {
            const extDir = path.join(profilesDir, prof, 'extensions');
            try {
                if (!fs.existsSync(extDir)) continue;
                for (const entry of fs.readdirSync(extDir)) {
                    if (dirLooksLikeBetterBibtexFolder(entry)) return true;
                }
            } catch (_) {}
        }
    } catch (_) {}
    return false;
}
