/**
 * Testable functions extracted from main.js for Vitest.
 * No obsidian dependency — safe to import in Node test environment.
 */
const fs = require('fs');
const path = require('path');
const { execFile, spawn } = require('node:child_process');

function readPathConfig(vaultPath, _fs) {
    const f = _fs || fs;
    const pfPath = path.join(vaultPath, 'paperforge.json');
    const defaults = {
        system_dir: 'System',
        resources_dir: 'Resources',
        literature_dir: 'Literature',
        base_dir: 'Bases',
    };

    try {
        if (!f.existsSync(pfPath)) {
            return { ...defaults, _warning: 'paperforge.json not found; using defaults' };
        }
        const raw = f.readFileSync(pfPath, 'utf-8');
        const data = JSON.parse(raw);
        const vc = data.vault_config || {};
        return {
            system_dir: vc.system_dir || data.system_dir || defaults.system_dir,
            resources_dir: vc.resources_dir || data.resources_dir || defaults.resources_dir,
            literature_dir: vc.literature_dir || data.literature_dir || defaults.literature_dir,
            base_dir: vc.base_dir || data.base_dir || defaults.base_dir,
            _warning: null,
        };
    } catch {
        return { ...defaults, _warning: 'paperforge.json invalid; using defaults' };
    }
}

function resolveRuntimePaths(vaultPath, _fs) {
    const cfg = readPathConfig(vaultPath, _fs);
    const systemRoot = path.join(vaultPath, cfg.system_dir, 'PaperForge');
    return {
        vault: vaultPath,
        systemDir: systemRoot,
        indexesDir: path.join(systemRoot, 'indexes'),
        logsDir: path.join(systemRoot, 'logs'),
        dbPath: path.join(systemRoot, 'indexes', 'paperforge.db'),
        memoryStatePath: path.join(systemRoot, 'indexes', 'memory-runtime-state.json'),
        vectorStatePath: path.join(systemRoot, 'indexes', 'vector-runtime-state.json'),
        healthStatePath: path.join(systemRoot, 'indexes', 'runtime-health.json'),
        buildStatePath: path.join(systemRoot, 'indexes', 'vector-build-state.json'),
        annotationsDbPath: path.join(systemRoot, 'indexes', 'annotations.db'),
        exportsDir: path.join(systemRoot, 'exports'),
        ocrDir: path.join(systemRoot, 'ocr'),
        pluginDataPath: path.join(vaultPath, '.obsidian', 'plugins', 'paperforge', 'data.json'),
        pfJsonPath: path.join(vaultPath, 'paperforge.json'),
        configWarning: cfg._warning,
    };
}

// ── Runtime helpers ──

function resolvePythonExecutable(vaultPath, settings, _fs, _execFileSync) {
    const f = _fs || fs;
    const execSync = _execFileSync || require("node:child_process").execFileSync;

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

function getPluginVersion(app) {
    try {
        const manifest = app && app.plugins && app.plugins.plugins &&
            app.plugins.plugins["paperforge"] && app.plugins.plugins["paperforge"].manifest;
        return (manifest && manifest.version) || null;
    } catch {
        return null;
    }
}

function checkRuntimeVersion(pythonExe, pluginVersion, cwd, timeout, _execFile) {
    if (timeout === undefined) timeout = 10000;
    const exe = _execFile || execFile;

    return new Promise((resolve) => {
        exe(pythonExe, ["-c", "import paperforge; print(paperforge.__version__)"],
            { cwd, timeout },
            (err, stdout) => {
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

function classifyError(errorCode) {
    const code = String(errorCode);
    const patterns = {
        ENOENT: { type: "python_missing", message: "Python executable not found", recoverable: true },
        "python-missing": { type: "python_missing", message: "Python executable not found", recoverable: true },
        MODULE_NOT_FOUND: { type: "import_failed", message: "PaperForge package not installed", recoverable: true },
        "import-failed": { type: "import_failed", message: "PaperForge package not installed", recoverable: true },
        "version-mismatch": { type: "version_mismatch", message: "Plugin and package versions differ", recoverable: true, action: "sync-runtime" },
        "pip-failed": { type: "pip_install_failure", message: "pip install command failed", recoverable: true },
        ETIMEDOUT: { type: "timeout", message: "Subprocess timed out", recoverable: true, action: "retry" },
        timeout: { type: "timeout", message: "Subprocess timed out", recoverable: true, action: "retry" },
    };
    const match = patterns[code];
    if (match) return { ...match };
    return { type: "unknown", message: String(errorCode), recoverable: false };
}

function buildRuntimeInstallCommand(pythonExe, version, extraArgs) {
    if (extraArgs === undefined) extraArgs = [];
    const pypiPkg = `paperforge==${version}`;
    const gitUrl = `git+https://github.com/LLLin000/PaperForge.git@v${version}`;
    const pypiArgs = [...extraArgs, "-m", "pip", "install", "--upgrade", pypiPkg];
    const gitArgs = [...extraArgs, "-m", "pip", "install", "--upgrade", gitUrl];
    return { cmd: pythonExe, url: gitUrl.replace('@v', '@'), args: gitArgs, pypiArgs, gitArgs, timeout: 120000 };
}

function parseRuntimeStatus(err, stdout, stderr) {
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

// ── Action definitions ──

// ── Overlay helpers ──

function detectConflictingPlugins(app) {
    try {
        const plugins = app && app.plugins && app.plugins.plugins;
        if (!plugins) return null;
        if (plugins['pdf-plus']) return 'PDF++';
        if (plugins['obsidian-annotator']) return 'Obsidian Annotator';
        return null;
    } catch { return null; }
}

function canUseAnnotationOverlay(app, isMobile) {
    if (isMobile) return false;
    if (detectConflictingPlugins(app)) return false;
    return true;
}

// ── Bridge helpers ──

function runAnnotationSubprocess(vaultPath, pythonInfo, args, timeout, _spawn) {
    const py = pythonInfo || {};
    const extra = py.extraArgs || [];
    const allArgs = [...extra, '-m', 'paperforge', '--vault', vaultPath, ...args];
    return runSubprocess(py.path || 'python', allArgs, vaultPath, timeout || 30000, _spawn);
}

// ── Annotation helpers ──

const ANNOTATION_COLORS = [
    { name: 'yellow', hex: '#ffd400' },
    { name: 'red', hex: '#ff6666' },
    { name: 'green', hex: '#5fb236' },
    { name: 'blue', hex: '#2ea8e5' },
    { name: 'purple', hex: '#a28ae5' },
    { name: 'magenta', hex: '#e56eee' },
    { name: 'orange', hex: '#f19837' },
    { name: 'gray', hex: '#aaaaaa' },
];

const ANNOTATION_DEFAULT_COLOR = '#ffd400';

function buildAnnotationSubprocessArgs(vaultPath, pythonInfo) {
    const extra = (pythonInfo && pythonInfo.extraArgs) || [];
    return [...extra, '-m', 'paperforge', '--vault', vaultPath];
}

function buildAnnotationListArgs(vaultPath, pythonInfo, pdfPath) {
    const args = buildAnnotationSubprocessArgs(vaultPath, pythonInfo);
    args.push('annotation', 'list');
    if (pdfPath) args.push('--pdf-path', pdfPath);
    args.push('--json');
    return args;
}

function buildAnnotationCreateArgs(vaultPath, pythonInfo, payload) {
    const args = buildAnnotationSubprocessArgs(vaultPath, pythonInfo);
    args.push('annotation', 'create', '--json');
    if (payload.pdf_path) args.push('--pdf-path', payload.pdf_path);
    if (payload.page_index != null) args.push('--page-index', String(payload.page_index));
    if (payload.type) args.push('--type', payload.type);
    if (payload.color) args.push('--color', payload.color);
    if (payload.selected_text) args.push('--selected-text', payload.selected_text);
    if (payload.comment) args.push('--comment', payload.comment);
    if (payload.position_json) args.push('--position-json', payload.position_json);
    return args;
}

function buildAnnotationPatchArgs(vaultPath, pythonInfo, annotationId, patch) {
    const args = buildAnnotationSubprocessArgs(vaultPath, pythonInfo);
    args.push('annotation', 'patch', String(annotationId), '--json');
    if (patch.comment != null) args.push('--comment', patch.comment);
    if (patch.color != null) args.push('--color', patch.color);
    return args;
}

function buildAnnotationDeleteArgs(vaultPath, pythonInfo, annotationId) {
    const args = buildAnnotationSubprocessArgs(vaultPath, pythonInfo);
    args.push('annotation', 'delete', String(annotationId), '--json');
    return args;
}

function parseAnnotationResult(jsonString) {
    try {
        const parsed = JSON.parse(jsonString);
        if (parsed && parsed.ok === true) {
            return { ok: true, data: parsed.result || parsed.data || null, raw: parsed };
        }
        if (parsed && parsed.ok === false) {
            return { ok: false, error: parsed.error || 'Unknown error', raw: parsed };
        }
        return { ok: false, error: 'Unexpected envelope', raw: parsed };
    } catch (e) {
        return { ok: false, error: 'JSON parse failed: ' + e.message, raw: null };
    }
}

function isReadonlyAnnotation(annotation) {
    return !!(annotation && annotation.sync_state === 'zotero_synced');
}

function groupAnnotationsByPage(annotations) {
    if (!annotations || !Array.isArray(annotations)) return {};
    const grouped = {};
    for (const a of annotations) {
        const page = (a.page_index != null) ? a.page_index : 0;
        if (!grouped[page]) grouped[page] = [];
        grouped[page].push(a);
    }
    return grouped;
}

function isAnnotationSupportedType(type) {
    return ['highlight', 'underline', 'note'].includes(type);
}

function buildAnnotationPayloadFromSelection(pdfPath, selectedText, pageIndex, rect, type) {
    const positionJson = JSON.stringify({
        pageIndex: pageIndex,
        rects: [[rect.left, rect.top, rect.right, rect.bottom]],
    });
    return {
        pdf_path: pdfPath,
        page_index: pageIndex,
        type: type || 'highlight',
        color: ANNOTATION_DEFAULT_COLOR,
        selected_text: selectedText,
        position_json: positionJson,
    };
}

function normalizeAnnotationRects(ann) {
    if (!ann) return null;
    if (ann.rects_json) {
        try {
            const parsed = JSON.parse(ann.rects_json);
            if (Array.isArray(parsed)) return parsed;
            return null;
        } catch { return null; }
    }
    if (ann.position && Array.isArray(ann.position.rects)) {
        return ann.position.rects;
    }
    return null;
}

const ACTIONS = [
    {
        id: "paperforge-sync",
        title: "Sync Library",
        desc: "Pull new references from Zotero and generate literature notes",
        icon: "\u21BB",
        cmd: "sync",
        okMsg: "Sync complete",
    },
    {
        id: "paperforge-ocr",
        title: "Run OCR",
        desc: "Extract full text and figures from PDFs via PaddleOCR",
        icon: "\u229E",
        cmd: "ocr",
        okMsg: "OCR started",
    },
    {
        id: "paperforge-doctor",
        title: "Run Doctor",
        desc: "Verify PaperForge setup \u2014 check configs, Zotero, paths, and index health",
        icon: "\u2695",
        cmd: "doctor",
        okMsg: "Doctor complete",
    },
    {
        id: "paperforge-repair",
        title: "Repair Issues",
        desc: "Fix three-way state divergence, path errors, and rebuild index",
        icon: "\u21BA",
        cmd: "repair",
        args: ["--fix", "--fix-paths"],
        okMsg: "Repair complete",
    },
];

function buildCommandArgs(action, key, filter) {
    const args = Array.isArray(action.args) ? [...action.args] : [];
    if (action.needsKey && key) args.push(key);
    if (action.needsFilter || filter) args.push("--all");
    return args;
}

function runSubprocess(pythonExe, args, cwd, timeout, _spawn, env) {
    const sp = _spawn || spawn;

    return new Promise((resolve) => {
        const startTime = Date.now();
        const opts = { cwd, timeout, windowsHide: true };
        if (env) opts.env = env;
        const child = sp(pythonExe, args, opts);
        const stdoutChunks = [];
        const stderrChunks = [];

        child.stdout.on("data", (data) => { stdoutChunks.push(data.toString("utf-8")); });
        child.stderr.on("data", (data) => { stderrChunks.push(data.toString("utf-8")); });

        child.on("close", (code) => {
            resolve({ stdout: stdoutChunks.join(""), stderr: stderrChunks.join(""),
                exitCode: code, elapsed: Date.now() - startTime });
        });

        child.on("error", (err) => {
            resolve({ stdout: stdoutChunks.join(""),
                stderr: stderrChunks.join("") + "\n" + err.message,
                exitCode: -1, elapsed: Date.now() - startTime });
        });
    });
}

function shouldRenderVectorReady(vectorDepsOk, embedStatusText) {
    return vectorDepsOk === true;
}

function getDisclosureState(store, key, defaultCollapsed) {
    if (!store || typeof store !== 'object') return !!defaultCollapsed;
    if (!Object.prototype.hasOwnProperty.call(store, key)) return !!defaultCollapsed;
    return !!store[key];
}

function toggleDisclosureState(store, key, defaultCollapsed) {
    const next = !getDisclosureState(store, key, defaultCollapsed);
    if (store && typeof store === 'object') {
        store[key] = next;
    }
    return next;
}

module.exports = {
    readPathConfig,
    resolveRuntimePaths,
    resolvePythonExecutable,
    getPluginVersion,
    checkRuntimeVersion,
    classifyError,
    buildRuntimeInstallCommand,
    parseRuntimeStatus,
    ACTIONS,
    buildCommandArgs,
    runSubprocess,
    shouldRenderVectorReady,
    getDisclosureState,
    toggleDisclosureState,
    detectConflictingPlugins,
    canUseAnnotationOverlay,
    runAnnotationSubprocess,
    ANNOTATION_COLORS,
    ANNOTATION_DEFAULT_COLOR,
    buildAnnotationSubprocessArgs,
    buildAnnotationListArgs,
    buildAnnotationCreateArgs,
    buildAnnotationPatchArgs,
    buildAnnotationDeleteArgs,
    parseAnnotationResult,
    isReadonlyAnnotation,
    groupAnnotationsByPage,
    isAnnotationSupportedType,
    normalizeAnnotationRects,
    buildAnnotationPayloadFromSelection,
};
