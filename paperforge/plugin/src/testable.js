/**
 * Testable functions extracted from main.js for Vitest.
 * No obsidian dependency — safe to import in Node test environment.
 */
const fs = require('fs');
const path = require('path');
const { execFile, spawn } = require('node:child_process');

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
    return { cmd: pythonExe, pypiArgs, gitArgs, timeout: 120000 };
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

// ── Annotation bridge helpers ──

/**
 * Stable state names for the annotation load state machine.
 *
 * @enum {string}
 */
const ANNOTATION_LOAD_STATES = Object.freeze({
    IDLE: 'idle',
    LOADING: 'loading',
    READY: 'ready',
    EMPTY: 'empty',
    MISSING_PAPER: 'missing-paper',
    MISSING_DB: 'missing-db',
    CLI_ERROR: 'cli-error',
    INVALID_JSON: 'invalid-json',
});

/**
 * Normalize a single annotation export row into UI-ready sections.
 *
 * @param {object} row - A raw row from annotation export --json (annotations array item).
 * @returns {{ display, provenance, pdfLocation, raw }}
 */
function normalizeAnnotationExportRow(row) {
    const display = {
        page: row.page_index,
        pageLabel: row.page_label,
        type: row.type,
        color: row.color,
        selectedText: row.selected_text,
        comment: row.comment,
    };

    const provenance = {
        source: row.source,
        isReadonly: Boolean(row.is_readonly),
        sourceLibraryId: row.source_library_id,
        sourceParentKey: row.source_parent_key,
        sourceAttachmentKey: row.source_attachment_key,
        sourceAnnotationKey: row.source_annotation_key,
        syncState: row.sync_state,
        sourceModifiedAt: row.source_modified_at != null ? row.source_modified_at : null,
        createdAt: row.created_at != null ? row.created_at : null,
        updatedAt: row.updated_at != null ? row.updated_at : null,
        deletedAt: row.deleted_at != null ? row.deleted_at : null,
    };

    const pdfLocation = {
        pageIndex: row.page_index,
        pageLabel: row.page_label,
        sourceAttachmentKey: row.source_attachment_key,
        positionJson: row.position_json,
        selectorJson: row.selector_json,
        sortIndex: row.sort_index,
        rowId: row.id,
    };

    return { display, provenance, pdfLocation, raw: row };
}

/**
 * Construct a complete annotation load state object.
 *
 * @param {string} stateName - One of ANNOTATION_LOAD_STATES values.
 * @param {object} [opts] - Optional fields.
 * @param {string|null} [opts.paperKey]
 * @param {Array} [opts.annotations]
 * @param {string} [opts.message]
 * @param {string|null} [opts.errorCode]
 * @param {*} [opts.raw]
 * @returns {{ state: string, paperKey, annotations: Array, message: string, errorCode, raw }}
 */
function makeAnnotationState(stateName, opts) {
    const o = opts || {};
    return {
        state: stateName,
        paperKey: o.paperKey != null ? o.paperKey : null,
        annotations: Array.isArray(o.annotations) ? o.annotations : [],
        message: typeof o.message === 'string' ? o.message : '',
        errorCode: o.errorCode != null ? o.errorCode : null,
        raw: o.raw !== undefined ? o.raw : null,
    };
}

/**
 * Build CLI arguments for `paperforge annotation status --json`.
 *
 * @param {string[]} extraArgs - Extra CLI args (e.g. --vault, --verbose).
 * @returns {string[]}
 */
function buildAnnotationStatusArgs(extraArgs) {
    const base = ['-m', 'paperforge', 'annotation', 'status', '--json'];
    if (Array.isArray(extraArgs) && extraArgs.length > 0) {
        return base.concat(extraArgs);
    }
    return base;
}

/**
 * Build CLI arguments for `paperforge annotation export --paper KEY --json`.
 *
 * @param {string} paperKey - The Zotero paper key to export annotations for.
 * @param {string[]} extraArgs - Extra CLI args (e.g. --vault, --verbose).
 * @returns {string[]}
 */
function buildAnnotationExportArgs(paperKey, extraArgs) {
    const base = ['-m', 'paperforge', 'annotation', 'export', '--paper', paperKey, '--json'];
    if (Array.isArray(extraArgs) && extraArgs.length > 0) {
        return base.concat(extraArgs);
    }
    return base;
}

/**
 * Load annotations for a paper through the PaperForge CLI.
 *
 * Two-step process:
 *   1. `paperforge annotation status --json` — checks whether annotations.db is available.
 *   2. `paperforge annotation export --paper KEY --json` — fetches annotations when DB is ready.
 *
 * Returns a complete load state (one of ANNOTATION_LOAD_STATES values) so callers
 * (including Phase 6 UI) can render list, empty, and error states without reparsing
 * raw CLI output.
 *
 * @param {object} options
 * @param {string|null} options.paperKey - Zotero paper key. null/blank → missing-paper (no subprocess).
 * @param {string} [options.pythonExe='python'] - Python executable path.
 * @param {string[]} [options.pythonExtraArgs] - Extra Python/CLI args.
 * @param {string} [options.cwd] - Working directory for subprocess.
 * @param {number} [options.timeout=30000] - Subprocess timeout in ms.
 * @param {Function} [options.runSubprocessFn] - Injected subprocess runner matching
 *   `runSubprocess` return shape: `(pythonExe, args, cwd, timeout, undefined, env) =>
 *   Promise<{stdout, stderr, exitCode}>`. Uses `runSubprocess` by default.
 * @param {object} [options.env] - Extra environment variables for subprocess.
 * @returns {Promise<{state, paperKey, annotations, message, errorCode, raw}>}
 */
async function loadAnnotationsForPaper(options) {
    const {
        paperKey,
        pythonExe = 'python',
        pythonExtraArgs = [],
        cwd,
        timeout = 30000,
        runSubprocessFn,
        env,
    } = options || {};

    // ── Early exit: no paper key → missing-paper ──
    if (!paperKey) {
        return makeAnnotationState(ANNOTATION_LOAD_STATES.MISSING_PAPER, {
            paperKey: null,
            message: 'No paper is currently active. Open a paper note or PDF to view its annotations.',
        });
    }

    // The subprocess runner: use injected fn or the default runSubprocess
    const exec = typeof runSubprocessFn === 'function'
        ? runSubprocessFn
        : (py, args, cwdArg, to) => runSubprocess(py, args, cwdArg, to, undefined, env);

    /**
     * Parse a subprocess result into { pfResult, errorState }.
     * Returns null for errorState when parsing succeeds and ok=true.
     */
    function parseSubprocessResult(subprocessResult, commandName) {
        // Subprocess threw → cli-error
        if (subprocessResult instanceof Error) {
            return {
                pfResult: null,
                errorState: makeAnnotationState(ANNOTATION_LOAD_STATES.CLI_ERROR, {
                    paperKey,
                    message: commandName === 'status'
                        ? 'Failed to check annotation database status.'
                        : 'Could not load annotations for this paper.',
                    errorCode: 'SUBPROCESS_ERROR',
                    raw: { error: subprocessResult.message, command: commandName },
                }),
            };
        }

        // Try JSON parsing
        let parsed;
        try {
            parsed = JSON.parse(subprocessResult.stdout);
        } catch {
            // Invalid JSON
            if (subprocessResult.exitCode !== 0) {
                return {
                    pfResult: null,
                    errorState: makeAnnotationState(ANNOTATION_LOAD_STATES.CLI_ERROR, {
                        paperKey,
                        message: commandName === 'status'
                            ? 'Failed to check annotation database status.'
                            : 'Failed to load annotations from the CLI.',
                        errorCode: 'CLI_ERROR',
                        raw: {
                            stdout: subprocessResult.stdout,
                            stderr: subprocessResult.stderr,
                            exitCode: subprocessResult.exitCode,
                            command: commandName,
                        },
                    }),
                };
            }
            return {
                pfResult: null,
                errorState: makeAnnotationState(ANNOTATION_LOAD_STATES.INVALID_JSON, {
                    paperKey,
                    message: commandName === 'status'
                        ? 'Could not read the annotation system status.'
                        : 'Could not read the annotation data for this paper.',
                    errorCode: null,
                    raw: {
                        stdout: subprocessResult.stdout,
                        stderr: subprocessResult.stderr,
                        exitCode: subprocessResult.exitCode,
                        command: commandName,
                    },
                }),
            };
        }

        // JSON parsed — check PFResult ok flag
        if (parsed && parsed.ok === false) {
            const errCode = parsed.error && parsed.error.code
                ? parsed.error.code
                : 'CLI_ERROR';
            return {
                pfResult: null,
                errorState: makeAnnotationState(ANNOTATION_LOAD_STATES.CLI_ERROR, {
                    paperKey,
                    message: commandName === 'status'
                        ? 'Failed to check annotation database status.'
                        : 'Failed to load annotations from the CLI.',
                    errorCode: errCode,
                    raw: { pfResult: parsed, command: commandName },
                }),
            };
        }

        return { pfResult: parsed, errorState: null };
    }

    // ── Step 1: status — is annotations.db available? ──
    const statusArgs = buildAnnotationStatusArgs(pythonExtraArgs);

    let statusSubprocessResult;
    try {
        statusSubprocessResult = await exec(pythonExe, statusArgs, cwd, timeout);
    } catch (subprocessErr) {
        statusSubprocessResult = subprocessErr;
    }

    const statusParsed = parseSubprocessResult(statusSubprocessResult, 'status');
    if (statusParsed.errorState) {
        return statusParsed.errorState;
    }
    const statusPfResult = statusParsed.pfResult;

    // Check DB availability
    const dbAvailable = statusPfResult &&
        statusPfResult.data &&
        statusPfResult.data.db_available === true;

    if (!dbAvailable) {
        return makeAnnotationState(ANNOTATION_LOAD_STATES.MISSING_DB, {
            paperKey,
            message: 'The annotation database is not yet available. Sync your library first.',
            errorCode: null,
            raw: { statusPfResult },
        });
    }

    // ── Step 2: export — get annotations for the specific paper ──
    const exportArgs = buildAnnotationExportArgs(paperKey, pythonExtraArgs);

    let exportSubprocessResult;
    try {
        exportSubprocessResult = await exec(pythonExe, exportArgs, cwd, timeout);
    } catch (subprocessErr) {
        exportSubprocessResult = subprocessErr;
    }

    const exportParsed = parseSubprocessResult(exportSubprocessResult, 'export');
    if (exportParsed.errorState) {
        return exportParsed.errorState;
    }
    const exportPfResult = exportParsed.pfResult;

    // Extract annotations
    const rawAnnotations = (exportPfResult.data && exportPfResult.data.annotations) || [];
    const total = (exportPfResult.data && exportPfResult.data.total) || 0;

    if (total === 0 || rawAnnotations.length === 0) {
        return makeAnnotationState(ANNOTATION_LOAD_STATES.EMPTY, {
            paperKey,
            message: 'This paper has no annotations yet. Add annotations in Zotero and re-sync.',
            errorCode: null,
            raw: { exportPfResult, statusPfResult },
        });
    }

    // Normalize each row
    const normalizedAnnotations = rawAnnotations.map(normalizeAnnotationExportRow);

    return makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
        paperKey,
        annotations: normalizedAnnotations,
        message: `${normalizedAnnotations.length} annotation(s) loaded.`,
        errorCode: null,
        raw: { exportPfResult, statusPfResult },
    });
}

/**
 * Create an annotation lifecycle controller that models active-paper refresh decisions.
 *
 * This is a testable helper that mirrors the lifecycle logic PaperForgeStatusView
 * will implement, without importing Obsidian APIs. It encapsulates:
 *   - current paper key tracking
 *   - annotation state storage
 *   - monotonic load sequence guard for stale-result protection
 *   - missing-paper guard (no subprocess call when key is null)
 *   - getAnnotationState() accessor
 *   - loadAnnotationsForCurrentPaper(reason, options) loader
 *
 * @param {object} [initialState] - Initial state overrides.
 * @returns {{
 *   _currentPaperKey: string|null,
 *   _annotationState: object,
 *   _annotationLoadSeq: number,
 *   getAnnotationState: () => object,
 *   setCurrentPaperKey: (key: string|null) => void,
 *   loadAnnotationsForCurrentPaper: (reason: string, options: object) => Promise<object>,
 * }}
 */
function createAnnotationLifecycleController(initialState) {
    const ctrl = {
        _currentPaperKey: (initialState && initialState.currentPaperKey) || null,
        _annotationState: makeAnnotationState(ANNOTATION_LOAD_STATES.IDLE, {
            paperKey: (initialState && initialState.currentPaperKey) || null,
            message: (initialState && initialState.message) || '',
        }),
        _annotationLoadSeq: 0,
    };

    /**
     * Return the current stored annotation state.
     */
    ctrl.getAnnotationState = function getAnnotationState() {
        return ctrl._annotationState;
    };

    /**
     * Set the current paper key (e.g. on mode switch).
     * If the key changes, the controller is ready for a new load.
     */
    ctrl.setCurrentPaperKey = function setCurrentPaperKey(key) {
        ctrl._currentPaperKey = key || null;
    };

    /**
     * Load annotations for the current paper, with stale-result protection.
     *
     * @param {string} [reason='auto'] - Reason for the load ('auto' | 'manual').
     * @param {object} [options] - Options passed through to loadAnnotationsForPaper.
     *   Must include `runSubprocessFn` in test scenarios.
     * @returns {Promise<object>} The annotation state after loading.
     */
    ctrl.loadAnnotationsForCurrentPaper = async function loadAnnotationsForCurrentPaper(reason, options) {
        const seq = ++ctrl._annotationLoadSeq;
        const paperKey = ctrl._currentPaperKey;

        // Missing paper guard: set missing-paper, do not call CLI/subprocess
        if (!paperKey) {
            const state = makeAnnotationState(ANNOTATION_LOAD_STATES.MISSING_PAPER, {
                paperKey: null,
                message: 'No paper is currently active. Open a paper note or PDF to view its annotations.',
            });
            ctrl._annotationState = state;
            return state;
        }

        // Set loading state
        ctrl._annotationState = makeAnnotationState(ANNOTATION_LOAD_STATES.LOADING, {
            paperKey,
            message: reason === 'manual' ? 'Refreshing annotations...' : 'Loading annotations...',
        });

        // Perform the actual load
        const loadOptions = Object.assign({}, options, { paperKey });
        const result = await loadAnnotationsForPaper(loadOptions);

        // Stale-result guard: only accept if no newer load started
        if (seq !== ctrl._annotationLoadSeq) {
            // A newer load was started; discard this stale result
            return ctrl._annotationState;
        }

        ctrl._annotationState = result;
        return result;
    };

    return ctrl;
}

module.exports = {
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
    // Annotation bridge
    ANNOTATION_LOAD_STATES,
    normalizeAnnotationExportRow,
    makeAnnotationState,
    buildAnnotationStatusArgs,
    buildAnnotationExportArgs,
    loadAnnotationsForPaper,
    // Lifecycle controller
    createAnnotationLifecycleController,
};
