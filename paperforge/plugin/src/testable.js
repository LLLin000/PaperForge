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
        note: row.note,
        imagePath: row.image_path != null ? row.image_path : row.imagePath,
        imageData: row.image_data != null ? row.image_data : row.imageData,
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
 * Create a lifecycle controller for active-paper annotation refresh decisions.
 *
 * Models Obsidian plugin active-paper transitions without importing any
 * Obsidian API, so tests can prove missing-paper skipping, key transitions,
 * and stale-result guarding in a pure Node environment.
 *
 * @param {object} [opts]
 * @param {Function} [opts.loader] - Async function(key, reason) that returns
 *   a load state (one of ANNOTATION_LOAD_STATES). Default no-op.
 * @returns {LifecycleController}
 */
function createAnnotationLifecycleController(opts) {
    const o = opts || {};
    const loadFn = typeof o.loader === 'function'
        ? o.loader
        : async () => makeAnnotationState(ANNOTATION_LOAD_STATES.IDLE);

    let _currentPaperKey = null;
    let _annotationState = makeAnnotationState(ANNOTATION_LOAD_STATES.IDLE);
    let _loadSeq = 0;

    /** Return the current stored annotation state. */
    function getAnnotationState() {
        return _annotationState;
    }

    /** Return the current paper key. */
    function getCurrentPaperKey() {
        return _currentPaperKey;
    }

    /**
     * Set the current paper key and begin a load if key is non-null/empty.
     * Returns the promise of the load (for testing).
     *
     * @param {string|null} key
     * @param {string} [reason='auto']
     * @returns {Promise<object>|null} Load promise, or null if missing-paper.
     */
    function setCurrentPaperKey(key, reason) {
        const r = reason || 'auto';
        _currentPaperKey = key != null ? key : null;

        // Missing paper → set state and skip loader
        if (!_currentPaperKey) {
            _annotationState = makeAnnotationState(ANNOTATION_LOAD_STATES.MISSING_PAPER, {
                paperKey: null,
                message: 'No paper is currently active. Open a paper note or PDF to view its annotations.',
            });
            return null;
        }

        // Key is set — start a load
        return loadAnnotationsForCurrentPaper(r);
    }

    /**
     * Load annotations for the current paper key.
     * Includes stale-result guard via monotonic loadSeq.
     *
     * @param {string} [reason='auto']
     * @returns {Promise<object>|null} Promise of load state, or null if no key.
     */
    function loadAnnotationsForCurrentPaper(reason) {
        const r = reason || 'auto';

        if (!_currentPaperKey) {
            _annotationState = makeAnnotationState(ANNOTATION_LOAD_STATES.MISSING_PAPER, {
                paperKey: null,
                message: 'No paper is currently active. Open a paper note or PDF to view its annotations.',
            });
            return null;
        }

        // Mark loading
        _annotationState = makeAnnotationState(ANNOTATION_LOAD_STATES.LOADING, {
            paperKey: _currentPaperKey,
            message: 'Loading annotations...',
        });

        const capturedSeq = ++_loadSeq;
        const capturedKey = _currentPaperKey;

        return loadFn(capturedKey, r).then((result) => {
            // Stale-result guard: discard if paper key changed during load
            if (_currentPaperKey !== capturedKey || _loadSeq !== capturedSeq) {
                return _annotationState;
            }

            // Ensure the result has the correct paperKey
            result.paperKey = capturedKey;
            _annotationState = result;
            return result;
        });
    }

    return {
        getAnnotationState,
        getCurrentPaperKey,
        setCurrentPaperKey,
        loadAnnotationsForCurrentPaper,
    };
}

// ── Annotation list view-model helpers (Phase 6, Plan 02) ──

/**
 * Create a fresh, session-local annotation list UI state.
 *
 * @returns {{ query: string, groupMode: string, typeColorFilter: string, expandedIds: string[] }}
 */
function createDefaultAnnotationListUiState() {
    return {
        query: '',
        groupMode: 'none',
        typeColorFilter: 'all',
        expandedIds: [],
    };
}

/**
 * Compute a stable, unique identity string for a normalized annotation row.
 *
 * Uses the source annotation key when available, then falls back to
 * pdfLocation rowId, then to a composite of display + pdfLocation fields.
 *
 * @param {object} row - A normalized annotation row ({ display, provenance, pdfLocation }).
 * @returns {string}
 */
function getAnnotationIdentity(row) {
    if (!row) return '';
    const p = row.provenance || {};
    const loc = row.pdfLocation || {};
    const d = row.display || {};

    if (p.sourceAnnotationKey) return String(p.sourceAnnotationKey);
    if (loc.rowId) return String(loc.rowId);
    if (p.source) return p.source + '|' + (p.sourceAttachmentKey || '') + '|' + (d.page != null ? d.page : '') + '|' + (loc.sortIndex != null ? loc.sortIndex : 0);
    return 'row|' + (d.page != null ? d.page : '') + '|' + (loc.sortIndex != null ? loc.sortIndex : 0);
}

/**
 * Sort normalized annotation rows in PDF reading order:
 *   1. Page index ascending (missing pages sort last).
 *   2. sortIndex ascending within the same page.
 *   3. Stable identity tiebreaker for deterministic ordering.
 *
 * Does NOT mutate the input array.
 *
 * @param {Array<object>} rows - Normalized annotation rows.
 * @returns {Array<object>} New array sorted in reading order.
 */
function sortAnnotationsForReadingOrder(rows) {
    if (!Array.isArray(rows)) return [];
    const copy = rows.slice();
    copy.sort((a, b) => {
        const locA = a && a.pdfLocation || {};
        const locB = b && b.pdfLocation || {};

        // Page index (null/missing sorts last)
        const pageA = locA.pageIndex != null ? locA.pageIndex : Number.MAX_SAFE_INTEGER;
        const pageB = locB.pageIndex != null ? locB.pageIndex : Number.MAX_SAFE_INTEGER;
        if (pageA !== pageB) return pageA - pageB;

        // sortIndex within page
        const sortA = locA.sortIndex != null ? locA.sortIndex : Number.MAX_SAFE_INTEGER;
        const sortB = locB.sortIndex != null ? locB.sortIndex : Number.MAX_SAFE_INTEGER;
        if (sortA !== sortB) return sortA - sortB;

        // Stable identity tiebreaker
        const idA = getAnnotationIdentity(a);
        const idB = getAnnotationIdentity(b);
        if (idA < idB) return -1;
        if (idA > idB) return 1;
        return 0;
    });
    return copy;
}

/**
 * Group annotation rows by the specified mode.
 *
 * Modes:
 *   "none"       — single group containing all rows.
 *   "page"       — groups by pageIndex, sorted by page ascending.
 *   "type-color" — groups by type + color combination, sorted by type then color.
 *
 * Within each group, rows preserve reading-order sort.
 *
 * @param {Array<object>} rows - Normalized annotation rows.
 * @param {string} groupMode - One of "none", "page", "type-color".
 * @returns {{ mode: string, groups: Array<{ key: string, label: string, rows: object[] }> }}
 */
function groupAnnotationRows(rows, groupMode) {
    const sorted = sortAnnotationsForReadingOrder(rows);

    if (groupMode === 'none' || !groupMode) {
        return {
            mode: 'none',
            groups: [{ key: 'all', label: 'All annotations', rows: sorted }],
        };
    }

    if (groupMode === 'page') {
        const pageMap = new Map();
        for (const row of sorted) {
            const loc = row && row.pdfLocation || {};
            const page = loc.pageIndex != null ? loc.pageIndex : -1;
            const pageLabel = loc.pageLabel || String(page);
            const key = 'page-' + page;
            if (!pageMap.has(key)) {
                pageMap.set(key, { key, label: 'Page ' + pageLabel, rows: [] });
            }
            pageMap.get(key).rows.push(row);
        }
        // Sort groups by page
        const groups = Array.from(pageMap.values());
        groups.sort((a, b) => {
            const pA = parseInt(a.key.replace('page-', ''), 10);
            const pB = parseInt(b.key.replace('page-', ''), 10);
            return pA - pB;
        });
        return { mode: 'page', groups };
    }

    if (groupMode === 'type-color') {
        const tcMap = new Map();
        for (const row of sorted) {
            const d = row && row.display || {};
            const type = d.type || 'unknown';
            const color = d.color != null ? d.color : 'null';
            const key = 'type-color-' + type + '-' + color;
            if (!tcMap.has(key)) {
                const label = color !== 'null'
                    ? type + ' [' + color + ']'
                    : type;
                tcMap.set(key, { key, label, rows: [] });
            }
            tcMap.get(key).rows.push(row);
        }
        // Sort groups by type then color
        const groups = Array.from(tcMap.values());
        groups.sort((a, b) => {
            const aType = (a.key.split('-').slice(2, -1).join('-') || '');
            const bType = (b.key.split('-').slice(2, -1).join('-') || '');
            if (aType !== bType) return aType < bType ? -1 : 1;
            const aColor = a.key.split('-').pop() || '';
            const bColor = b.key.split('-').pop() || '';
            return aColor < bColor ? -1 : (aColor > bColor ? 1 : 0);
        });
        return { mode: 'type-color', groups };
    }

    // Unknown mode → treat as none
    return {
        mode: 'none',
        groups: [{ key: 'all', label: 'All annotations', rows: sorted }],
    };
}

/**
 * Build a list of unique type/color filter options from the given rows.
 *
 * Each option has { type, color, label }.
 *
 * @param {Array<object>} rows - Normalized annotation rows.
 * @returns {Array<{ type: string, color: string|null, label: string }>}
 */
function buildAnnotationFilterOptions(rows) {
    if (!Array.isArray(rows) || rows.length === 0) return [];

    const seen = new Set();
    const options = [];
    for (const row of rows) {
        const d = row && row.display || {};
        const type = d.type || 'unknown';
        const color = d.color != null ? d.color : null;
        const key = type + '|' + (color !== null ? color : 'null');
        if (!seen.has(key)) {
            seen.add(key);
            const label = color !== null
                ? type + ' [' + color + ']'
                : type;
            options.push({ type, color, label });
        }
    }
    return options;
}

/**
 * Check whether a normalized annotation row's display text matches a search query.
 *
 * Matches against `selectedText` and `comment` ONLY.
 * Does NOT match raw, provenance, source, attachment, annotation key, timestamps,
 * or any debug fields.
 *
 * Empty/null/undefined query matches everything.
 *
 * @param {object} row - Normalized annotation row.
 * @param {string|null|undefined} query - Search string.
 * @returns {boolean}
 */
function matchesAnnotationSearch(row, query) {
    if (!query || typeof query !== 'string' || query.trim() === '') return true;
    const q = query.toLowerCase().trim();
    const d = row && row.display || {};
    const selectedText = (d.selectedText || '').toLowerCase();
    const comment = (d.comment || '').toLowerCase();
    return selectedText.includes(q) || comment.includes(q);
}

/**
 * Check if a row matches a type/color filter value.
 *
 * Filter values:
 *   "all"               — matches everything
 *   "highlight"         — matches type only
 *   "highlight|#ffd400" — matches type + color
 *   "" / null / undefined — matches everything
 *
 * @param {object} row - Normalized annotation row.
 * @param {string|null|undefined} filter - Filter value.
 * @returns {boolean}
 */
function matchesAnnotationTypeColorFilter(row, filter) {
    if (!filter || filter === 'all' || filter === '') return true;
    const d = row && row.display || {};
    const rowType = d.type || 'unknown';
    const rowColor = d.color != null ? d.color : 'null';

    // Support both "type" and "type|color" formats
    const parts = filter.split('|');
    const filterType = parts[0];
    const filterColor = parts.length > 1 ? parts[1] : null;

    if (rowType !== filterType) return false;
    if (filterColor !== null && rowColor !== filterColor) return false;
    return true;
}

// ── Preview and expansion helpers ──

/**
 * Compute preview metadata for a text content block.
 *
 * "selected-text" text gets two-line preview (~140 chars),
 * "comment" text gets one-line preview (~70 chars).
 *
 * Returns { text, kind, truncated, expandable } without DOM measurement.
 *
 * @param {string|null|undefined} text - The content to preview.
 * @param {"selected-text"|"comment"} kind - The kind of content.
 * @returns {{ text: string, kind: string, truncated: boolean, expandable: boolean }}
 */
function getAnnotationPreview(text, kind) {
    const safeText = (text != null ? String(text) : '');
    const limit = kind === 'selected-text' ? 140 : 70;

    if (safeText.length <= limit) {
        return { text: safeText, kind, truncated: false, expandable: false };
    }

    const truncated = safeText.substring(0, limit) + '…';
    return { text: truncated, kind, truncated: true, expandable: true };
}

/**
 * Toggle a row ID in the expansion set.
 *
 * Returns a NEW uiState object (immutable update) with the ID added
 * if absent or removed if present. Does not mutate the input.
 *
 * @param {{ query, groupMode, typeColorFilter, expandedIds }} uiState - Current UI state.
 * @param {string} rowId - Stable annotation identity to toggle.
 * @returns {{ query, groupMode, typeColorFilter, expandedIds }}
 */
function toggleAnnotationExpansion(uiState, rowId) {
    const currentExpanded = uiState.expandedIds || [];
    const index = currentExpanded.indexOf(rowId);
    let newExpanded;
    if (index === -1) {
        newExpanded = currentExpanded.concat([rowId]);
    } else {
        newExpanded = currentExpanded.slice(0, index).concat(currentExpanded.slice(index + 1));
    }
    return {
        query: uiState.query || '',
        groupMode: uiState.groupMode || 'none',
        typeColorFilter: uiState.typeColorFilter || 'all',
        expandedIds: newExpanded,
    };
}

// ── View-model builder ──

/**
 * Build a complete annotation list view-model from the bridge annotation state
 * and the current session-local UI state.
 *
 * The view-model centralizes everything the Phase 6 UI needs:
 *   state, rows (filtered, sorted), total (unfiltered), groups, banner,
 *   emptyMessage, errorMessage, filterOptions, and current uiState.
 *
 * State mapping:
 *   idle        → { state: 'idle', rows: [] }
 *   loading     → { state: 'loading', rows: [], banner: 'Loading…' }
 *   ready       → { state: 'ready', rows: [filtered+sorted], groups: …, total: N }
 *   empty       → { state: 'empty', rows: [], emptyMessage: '…' }
 *   missing-db  → { state: 'missing-db', rows: [], errorMessage: '…' }
 *   missing-paper → { state: 'missing-paper', rows: [], errorMessage: '…' }
 *   cli-error   → { state: 'cli-error', rows: [], errorMessage: '…' }
 *   invalid-json → { state: 'invalid-json', rows: [], errorMessage: '…' }
 *
 * @param {{ state, paperKey, annotations, message, errorCode, raw, stale }} annotationState
 * @param {{ query, groupMode, typeColorFilter, expandedIds }} uiState
 * @returns {object}
 */
function buildAnnotationListViewModel(annotationState, uiState) {
    const aState = annotationState || { state: 'idle', annotations: [] };
    const ui = uiState || createDefaultAnnotationListUiState();
    const rows = Array.isArray(aState.annotations) ? aState.annotations : [];

    // Total before filtering
    const total = rows.length;
    const state = aState.state || 'idle';

    // ── Banner-only states (no rows) ──
    if (state === 'loading') {
        return {
            state: 'loading',
            rows: [],
            total: 0,
            banner: aState.message || 'Loading annotations…',
            filterOptions: [],
            groups: undefined,
            uiState: ui,
        };
    }

    if (state === 'idle') {
        return {
            state: 'idle',
            rows: [],
            total: 0,
            filterOptions: [],
            groups: undefined,
            uiState: ui,
        };
    }

    // ── Error/empty states (no rows, but with messages) ──
    if (state === 'empty') {
        return {
            state: 'empty',
            rows: [],
            total: 0,
            emptyMessage: aState.message || 'This paper has no annotations yet. Import annotations from Zotero first.',
            filterOptions: [],
            groups: undefined,
            uiState: ui,
            stale: aState.stale || false,
        };
    }

    if (state === 'missing-db') {
        return {
            state: 'missing-db',
            rows: [],
            total: 0,
            errorMessage: aState.message || 'The annotation database is not yet available. Initialize or repair annotation data first.',
            filterOptions: [],
            groups: undefined,
            uiState: ui,
            stale: aState.stale || false,
        };
    }

    if (state === 'missing-paper') {
        return {
            state: 'missing-paper',
            rows: [],
            total: 0,
            errorMessage: aState.message || 'No paper is currently active. Open a recognized paper note or PDF to view its annotations.',
            filterOptions: [],
            groups: undefined,
            uiState: ui,
            stale: aState.stale || false,
        };
    }

    if (state === 'cli-error') {
        return {
            state: 'cli-error',
            rows: [],
            total: 0,
            errorMessage: aState.message || 'Failed to load annotations. Retry or check PaperForge annotation status.',
            filterOptions: [],
            groups: undefined,
            uiState: ui,
            stale: aState.stale || false,
        };
    }

    if (state === 'invalid-json') {
        return {
            state: 'invalid-json',
            rows: [],
            total: 0,
            errorMessage: aState.message || 'Could not read annotation data. Check the local CLI output for details.',
            filterOptions: [],
            groups: undefined,
            uiState: ui,
            stale: aState.stale || false,
        };
    }

    // ── Ready state with rows ──
    if (state === 'ready') {
        // Sort first
        let visibleRows = sortAnnotationsForReadingOrder(rows);

        // Apply type/color filter
        if (ui.typeColorFilter && ui.typeColorFilter !== 'all') {
            visibleRows = visibleRows.filter(r => matchesAnnotationTypeColorFilter(r, ui.typeColorFilter));
        }

        // Apply search filter
        if (ui.query && ui.query.trim() !== '') {
            visibleRows = visibleRows.filter(r => matchesAnnotationSearch(r, ui.query));
        }

        // Build groups if needed
        let groups;
        if (ui.groupMode && ui.groupMode !== 'none') {
            groups = groupAnnotationRows(visibleRows, ui.groupMode);
        }

        // Build filter options from ALL annotations (not just filtered)
        const filterOptions = buildAnnotationFilterOptions(rows);

        return {
            state: 'ready',
            rows: visibleRows,
            total,
            filterOptions,
            groups: groups,
            uiState: ui,
            stale: aState.stale || false,
        };
    }

    // Unknown state → fallback
    return {
        state: 'idle',
        rows: [],
        total: 0,
        filterOptions: [],
        groups: undefined,
        uiState: ui,
    };
}

/**
 * Merge a refresh result with the previous renderable annotation state.
 *
 * When a refresh fails after a previous successful (ready/empty) state,
 * the previous state is preserved and marked `stale: true` with an
 * updated message indicating the failure and that the data is stale.
 *
 * When refresh succeeds, the new state is returned as-is.
 * When there is no previous success, the new state is returned as-is
 * (no stale data to preserve).
 *
 * @param {object|null} previousRenderable - Previous annotation state (or null).
 * @param {object} nextState - New annotation state from refresh.
 * @returns {object} The merged annotation state (never null).
 */
function mergeAnnotationRefreshResult(previousRenderable, nextState) {
    // If refresh succeeded (ready/empty), return new state directly
    if (nextState.state === 'ready' || nextState.state === 'empty') {
        return nextState;
    }

    // Refresh failed — check if we have a previous successful state
    if (previousRenderable) {
        const prevState = previousRenderable.state || '';
        if (prevState === 'ready' || prevState === 'empty') {
            // Preserve previous state but mark as stale
            const merged = JSON.parse(JSON.stringify(previousRenderable));
            merged.stale = true;
            merged.message = (nextState.message || 'Refresh failed.') + ' — Showing previously loaded (stale) data.';
            return merged;
        }
    }

    // No previous success to fall back to
    return nextState;
}

// ── PDF jump-target navigation helpers (Phase 7, Plan 01) ──

/**
 * Extract a vault-relative canonical PDF path from a value that should be an
 * Obsidian wikilink.  Rejects absolute paths, URI schemes, directory traversal,
 * non-PDF extensions, raw storage: values, bare relative paths, malformed
 * wikilinks, and non-string input per D-05.
 *
 * @param {*} value - Input value (expected: a wikilink string like "[[path/to/file.pdf]]").
 * @returns {{ ok: boolean, path: string|null, reason: string|null }}
 */
function extractVaultPdfPath(value) {
    // Non-string and null reject
    if (value == null || typeof value !== 'string') {
        return { ok: false, path: null, reason: 'PDF path must be a string.' };
    }

    const input = value;

    // ── Reject non-wikilink patterns first ──
    // Absolute Windows paths (e.g. D:\...)
    if (/^[A-Za-z]:\\/.test(input)) {
        return { ok: false, path: null, reason: 'Absolute paths are not supported.' };
    }
    // URI scheme (e.g. file://, https://)
    if (/^[A-Za-z][A-Za-z0-9+.-]*:\/\//.test(input)) {
        return { ok: false, path: null, reason: 'URI scheme paths are not supported.' };
    }
    // Raw storage: prefix without wikilink
    if (/^storage:/i.test(input)) {
        return { ok: false, path: null, reason: 'Storage paths must be wrapped in a wikilink.' };
    }
    // Bare relative path without wikilink brackets (contains / or \ but no [[)
    if ((input.includes('/') || input.includes('\\')) && !input.includes('[[')) {
        return { ok: false, path: null, reason: 'Path must be wrapped in a wikilink.' };
    }

    // ── Extract wikilink content ──
    const match = input.match(/^\[\[([^\]]+)\]\]$/);
    if (!match) {
        return { ok: false, path: null, reason: 'Malformed wikilink.' };
    }

    const inner = match[1];

    // ── Security checks on inner path ──
    // Directory traversal
    if (inner.includes('..')) {
        return { ok: false, path: null, reason: 'Directory traversal is not allowed.' };
    }
    // Non-PDF extension
    const ext = inner.split('.').pop().toLowerCase();
    if (ext !== 'pdf') {
        return { ok: false, path: null, reason: 'Only PDF files are supported.' };
    }

    // Normalise backslashes to forward slashes
    const normalised = inner.replace(/\\/g, '/');

    return { ok: true, path: normalised, reason: null };
}

/**
 * Build the set of canonical PDF candidates from a paper entry.
 *
 * Reads `pdf_path` (the main PDF wikilink) and `supplementary` (array of
 * wikilinks) from the entry.  Each candidate gets an `attachmentKey` derived
 * from `zotero_storage_key` or from the canonical `/storage/{key}/` path
 * segment.  Candidates are deduplicated by path.
 *
 * @param {object|null|undefined} entry - Paper entry with pdf_path, zotero_storage_key, supplementary.
 * @returns {Array<{ path: string, attachmentKey: string }>}
 */
function buildPaperPdfCandidates(entry) {
    if (!entry) return [];

    const seen = new Set();
    const candidates = [];

    /**
     * Try to add a candidate from a raw value.
     * Returns true if added, false if skipped (invalid or duplicate).
     */
    function tryAddCandidate(rawValue, fallbackStorageKey) {
        const extracted = extractVaultPdfPath(rawValue);
        if (!extracted.ok) return false;

        const path = extracted.path;
        if (seen.has(path)) return false;
        seen.add(path);

        // Derive attachmentKey: use zotero_storage_key if path contains it,
        // otherwise try to extract from /storage/{key}/ segment
        let attachmentKey = null;
        if (fallbackStorageKey && path.includes('/storage/' + fallbackStorageKey + '/')) {
            attachmentKey = fallbackStorageKey;
        }
        if (!attachmentKey) {
            // Try to extract from /storage/{KEY}/
            const storageMatch = path.match(/\/storage\/([A-Za-z0-9_]+)\//);
            if (storageMatch) {
                attachmentKey = storageMatch[1];
            }
        }

        candidates.push({ path, attachmentKey: attachmentKey || path });
        return true;
    }

    const storageKey = entry.zotero_storage_key || null;

    // Main PDF
    if (entry.pdf_path != null) {
        tryAddCandidate(entry.pdf_path, storageKey);
    }

    // Supplementary PDFs
    if (Array.isArray(entry.supplementary)) {
        for (const supp of entry.supplementary) {
            tryAddCandidate(supp, storageKey);
        }
    }

    return candidates;
}

/**
 * Resolve the PDF jump target for a normalized annotation row against a paper
 * entry.
 *
 * Resolution order per D-04 through D-07:
 *   1. If `pdfLocation.sourceAttachmentKey` exists and exactly matches a
 *      candidate's attachmentKey, use that candidate.
 *   2. If no sourceAttachmentKey exists and entry has exactly one candidate,
 *      use that candidate (D-06 identity-free single-candidate rule).
 *   3. Otherwise fail closed with ok:false and a stable non-sensitive reason.
 *
 * Page conversion per D-08: only a non-negative integer pageIndex is accepted;
 * page = pageIndex + 1, linkText = "{path}#page={page}".
 * Invalid/missing page data preserves the PDF target (D-11) with a degraded
 * reason and linkText = path.
 *
 * @param {object|null|undefined} row - Normalized annotation row with pdfLocation.
 * @param {object|null|undefined} entry - Paper entry with pdf_path etc.
 * @returns {{ ok: boolean, path: string|null, page: number|null, linkText: string, reason: string|null }}
 */
function resolveAnnotationPdfTarget(row, entry) {
    // ── Guard: missing or invalid inputs ──
    if (!row) {
        return { ok: false, path: null, page: null, linkText: '', reason: 'No annotation row provided.' };
    }
    if (!entry) {
        return { ok: false, path: null, page: null, linkText: '', reason: 'No paper entry provided.' };
    }

    const pdfLoc = row.pdfLocation;
    if (!pdfLoc) {
        return { ok: false, path: null, page: null, linkText: '', reason: 'Annotation row has no PDF location data.' };
    }

    // ── Build candidates ──
    const candidates = buildPaperPdfCandidates(entry);
    if (candidates.length === 0) {
        return { ok: false, path: null, page: null, linkText: '', reason: 'No valid PDF candidates found in paper entry.' };
    }

    // ── Resolve candidate ──
    let resolvedCandidate = null;
    const identity = pdfLoc.sourceAttachmentKey;

    if (identity != null && identity !== '') {
        // Exact identity match (D-04)
        resolvedCandidate = candidates.find(c => c.attachmentKey === identity) || null;
        if (!resolvedCandidate) {
            return {
                ok: false,
                path: null,
                page: null,
                linkText: '',
                reason: 'Could not resolve the annotation to a PDF in the paper entry.',
            };
        }
    } else {
        // No identity — single-candidate fallback (D-06)
        if (candidates.length === 1) {
            resolvedCandidate = candidates[0];
        } else {
            // Zero or multiple candidates — fail closed (D-07)
            return {
                ok: false,
                path: null,
                page: null,
                linkText: '',
                reason: candidates.length === 0
                    ? 'No PDF candidates found.'
                    : 'Multiple PDF candidates found; cannot choose without attachment identity.',
            };
        }
    }

    // ── Page conversion (D-08) ──
    const pageIndex = pdfLoc.pageIndex;
    let page = null;
    let pageDegraded = false;

    if (typeof pageIndex === 'number' && Number.isFinite(pageIndex) && pageIndex >= 0 && Number.isInteger(pageIndex)) {
        page = pageIndex + 1;
    } else {
        pageDegraded = true;
    }

    const path = resolvedCandidate.path;
    let linkText;
    let reason;

    if (page !== null) {
        linkText = path + '#page=' + page;
        reason = null;
    } else {
        linkText = path;
        reason = 'Page location is not available.';
    }

    return { ok: true, path, page, linkText, reason };
}

// ── Overlay rendering helpers (Phase 8, Plan 02) ──

/**
 * Restrained default highlight color for overlay marks (D-06).
 * Used when annotation color is missing, invalid, or unrecognized.
 * @type {string}
 */
const DEFAULT_OVERLAY_HIGHLIGHT_COLOR = '#ffd400';

/**
 * Create a fresh, session-local annotation overlay state object.
 *
 * Tracks runtime overlay availability, active PDF identity, and
 * popover interaction. Must not persist to plugin settings or
 * localStorage.
 *
 * @returns {{ status: string, reason: string, paperKey: string|null, pdfPath: string|null, viewerAttached: boolean, activePopoverId: string|null }}
 */
function createDefaultAnnotationOverlayState() {
    return {
        status: 'idle',
        reason: '',
        paperKey: null,
        pdfPath: null,
        viewerAttached: false,
        activePopoverId: null,
    };
}

/**
 * Parse and validate an annotation `positionJson` string.
 *
 * Accepts a JSON object with a `rects` array of rectangles, each
 * having finite non-negative `x`, `y`, `w`, `h` numeric fields.
 * Returns `{ ok: true, rects: [...] }` on success or
 * `{ ok: false, rects: [], reason: '...' }` on failure.
 * Never throws.
 *
 * @param {string|null|undefined} positionJson - Raw JSON string from pdfLocation.positionJson.
 * @returns {{ ok: boolean, rects: Array<{x: number, y: number, w: number, h: number}>, reason: string|null }}
 */
function parseAnnotationPositionJson(positionJson) {
    // Non-string reject
    if (positionJson == null || typeof positionJson !== 'string') {
        return { ok: false, rects: [], reason: 'Position data must be a JSON string.' };
    }

    // JSON parse
    var parsed;
    try {
        parsed = JSON.parse(positionJson);
    } catch (_) {
        return { ok: false, rects: [], reason: 'Position data is not valid JSON.' };
    }

    // Must be a non-null, non-array object
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        return { ok: false, rects: [], reason: 'Position data must be a JSON object.' };
    }

    // Must have a rects array
    if (!Array.isArray(parsed.rects)) {
        return { ok: false, rects: [], reason: 'Position data has no rectangle coordinates.' };
    }

    // Empty rects
    if (parsed.rects.length === 0) {
        return { ok: false, rects: [], reason: 'Position data has an empty rectangle list.' };
    }

    // Validate each rect
    var rects = [];
    for (var i = 0; i < parsed.rects.length; i++) {
        var r = parsed.rects[i];
        if (typeof r !== 'object' || r === null) {
            return { ok: false, rects: [], reason: 'Position data contains an invalid rectangle entry.' };
        }

        var x = r.x;
        var y = r.y;
        var w = r.w;
        var h = r.h;

        if (typeof x !== 'number' || typeof y !== 'number' || typeof w !== 'number' || typeof h !== 'number') {
            return { ok: false, rects: [], reason: 'Position data contains a rectangle with non-numeric values.' };
        }

        if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(w) || !Number.isFinite(h)) {
            return { ok: false, rects: [], reason: 'Position data contains a rectangle with non-finite values.' };
        }

        if (x < 0 || y < 0 || w < 0 || h < 0) {
            return { ok: false, rects: [], reason: 'Position data contains a rectangle with negative values.' };
        }

        rects.push({ x: x, y: y, w: w, h: h });
    }

    return { ok: true, rects: rects, reason: null };
}

/**
 * Normalize an annotation color to a usable CSS value.
 *
 * Accepts hex (#rgb, #rrggbb, #rrggbbaa), rgb/rgba functional notation,
 * and common named colors. Returns the restrained default yellow (D-06)
 * when the input is missing, empty, or unrecognized.
 *
 * @param {*} color - The annotation color value from display.color.
 * @returns {string} A CSS-usable color string, never empty.
 */
function normalizeAnnotationColor(color) {
    if (typeof color !== 'string' || color.trim() === '') {
        return DEFAULT_OVERLAY_HIGHLIGHT_COLOR;
    }

    var trimmed = color.trim();

    // Hex colors: #rgb, #rrggbb, #rrggbbaa
    if (/^#[0-9a-fA-F]{3}$/.test(trimmed) ||
        /^#[0-9a-fA-F]{6}$/.test(trimmed) ||
        /^#[0-9a-fA-F]{8}$/.test(trimmed)) {
        return trimmed;
    }

    // rgb() / rgba() functional notation
    if (/^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+(\s*,\s*[\d.]+)?\s*\)$/.test(trimmed)) {
        return trimmed;
    }

    // Common named colors
    var namedColors = new Set([
        'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink',
        'cyan', 'magenta', 'lime', 'teal', 'navy', 'maroon', 'olive',
        'aqua', 'fuchsia', 'silver', 'gray', 'black', 'white',
    ]);

    if (namedColors.has(trimmed.toLowerCase())) {
        return trimmed.toLowerCase();
    }

    // Unrecognized → restrained default yellow
    return DEFAULT_OVERLAY_HIGHLIGHT_COLOR;
}

/**
 * Build renderable overlay mark view-models from annotation state.
 *
 * Requires a confirmed active PDF path and paper entry. Rows are
 * filtered through `resolveAnnotationPdfTarget()` and matched to
 * the active PDF path. Only rows with usable pageIndex and
 * position/rect data produce marks.
 *
 * Returns a stable `{ ok, status, marks, skipped, reason }` shape.
 * Does not mutate inputs.
 *
 * @param {{ state: string, annotations: Array }} annotationState - Current annotation load state.
 * @param {object|null|undefined} entry - Paper entry with pdf_path, supplementary, etc.
 * @param {string|null|undefined} activePdfPath - The canonical vault-relative path of the currently open PDF.
 * @param {{}} [options] - Reserved for future options.
 * @returns {{ ok: boolean, status: string, marks: Array, skipped: number, reason: string|null }}
 */
function buildAnnotationOverlayMarks(annotationState, entry, activePdfPath, options) {
    // Guard: annotation state must be ready
    if (!annotationState || annotationState.state !== 'ready') {
        return { ok: false, status: 'disabled', marks: [], skipped: 0, reason: 'Annotation data is not ready.' };
    }

    // Guard: paper entry required
    if (!entry) {
        return { ok: false, status: 'disabled', marks: [], skipped: 0, reason: 'No paper entry provided.' };
    }

    // Guard: active PDF path required
    if (!activePdfPath || typeof activePdfPath !== 'string') {
        return { ok: false, status: 'disabled', marks: [], skipped: 0, reason: 'No active PDF path available.' };
    }

    var rows = Array.isArray(annotationState.annotations) ? annotationState.annotations : [];
    if (rows.length === 0) {
        return { ok: true, status: 'empty', marks: [], skipped: 0, reason: null };
    }

    var marks = [];
    var skipped = 0;

    for (var i = 0; i < rows.length; i++) {
        var row = rows[i];

        // Step 1: Resolve PDF target — identity guard (T-annotation-08-02-S)
        var target = resolveAnnotationPdfTarget(row, entry);
        if (!target.ok || !target.path) {
            skipped++;
            continue;
        }

        // Step 2: Match active PDF path (D-11)
        if (target.path !== activePdfPath) {
            skipped++;
            continue;
        }

        // Step 3: Require valid pageIndex
        var pdfLoc = row.pdfLocation || {};
        var pageIndex = pdfLoc.pageIndex;
        if (typeof pageIndex !== 'number' || !Number.isFinite(pageIndex) || pageIndex < 0 || !Number.isInteger(pageIndex)) {
            skipped++;
            continue;
        }

        // Step 4: Parse positionJson (D-12)
        var position = parseAnnotationPositionJson(pdfLoc.positionJson);
        if (!position.ok || position.rects.length === 0) {
            skipped++;
            continue;
        }

        // Step 5: Build mark view-model
        var display = row.display || {};
        var provenance = row.provenance || {};
        var color = normalizeAnnotationColor(display.color);

        marks.push({
            id: getAnnotationIdentity(row),
            pageIndex: pageIndex,
            rects: position.rects.map(function (r) { return { x: r.x, y: r.y, w: r.w, h: r.h }; }),
            color: color,
            selectedText: display.selectedText || '',
            comment: display.comment || '',
            pageLabel: pdfLoc.pageLabel || String(pageIndex + 1),
            source: provenance.source || '',
            isReadonly: Boolean(provenance.isReadonly),
            attachmentKey: pdfLoc.sourceAttachmentKey || '',
            pdfPath: target.path,
        });
    }

    return {
        ok: true,
        status: marks.length > 0 ? 'rendered' : 'empty',
        marks: marks,
        skipped: skipped,
        reason: null,
    };
}

/**
 * Build a read-only popover view-model from a normalized annotation row.
 *
 * Exposes selected text, comment, page label/number, type, color, source,
 * read-only state, and annotation identity. No edit/delete/create/write-back/
 * database/evidence actions (D-14 through D-17).
 *
 * @param {object|null|undefined} row - A normalized annotation row ({ display, provenance, pdfLocation }).
 * @returns {{ ok: boolean, data: object|null, reason: string|null }}
 */
function buildAnnotationPopoverViewModel(row) {
    if (!row) {
        return { ok: false, data: null, reason: 'No annotation row provided.' };
    }

    var display = row.display || {};
    var provenance = row.provenance || {};
    var pdfLoc = row.pdfLocation || {};

    var pageNumber = pdfLoc.pageIndex != null ? pdfLoc.pageIndex + 1 : null;

    return {
        ok: true,
        data: {
            selectedText: display.selectedText || '',
            comment: display.comment || '',
            pageLabel: pdfLoc.pageLabel || '',
            pageNumber: pageNumber,
            type: display.type || '',
            color: normalizeAnnotationColor(display.color),
            source: provenance.source || '',
            isReadonly: Boolean(provenance.isReadonly),
            attachmentKey: pdfLoc.sourceAttachmentKey || '',
            annotationKey: provenance.sourceAnnotationKey || '',
        },
        reason: null,
    };
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
    // Annotation list view-model helpers (Phase 6, Plan 02)
    createDefaultAnnotationListUiState,
    getAnnotationIdentity,
    sortAnnotationsForReadingOrder,
    groupAnnotationRows,
    buildAnnotationFilterOptions,
    matchesAnnotationSearch,
    matchesAnnotationTypeColorFilter,
    getAnnotationPreview,
    toggleAnnotationExpansion,
    buildAnnotationListViewModel,
    mergeAnnotationRefreshResult,
    // PDF jump-target navigation helpers (Phase 7, Plan 01)
    extractVaultPdfPath,
    buildPaperPdfCandidates,
    resolveAnnotationPdfTarget,
    // Overlay rendering helpers (Phase 8, Plan 02)
    DEFAULT_OVERLAY_HIGHLIGHT_COLOR,
    createDefaultAnnotationOverlayState,
    parseAnnotationPositionJson,
    normalizeAnnotationColor,
    buildAnnotationOverlayMarks,
    buildAnnotationPopoverViewModel,
};
