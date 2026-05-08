/**
 * Error classification and runtime install command builder for PaperForge plugin.
 *
 * Extracted from main.js for testability. Covers 5 error patterns:
 * 1. Python missing     — ENOENT or python-missing
 * 2. Import failed      — MODULE_NOT_FOUND or import-failed
 * 3. Version mismatch   — version-mismatch
 * 4. Pip install failure — pip-failed
 * 5. Timeout            — ETIMEDOUT or timeout
 */
"use strict";

/**
 * Classify a subprocess error code/string into a structured error object.
 *
 * @param {string|number} errorCode — error.code from subprocess, or a string label
 * @returns {{ type: string, message: string, recoverable: boolean, action?: string }}
 */
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
    if (match) {
        return { ...match };
    }

    return { type: "unknown", message: String(errorCode), recoverable: false };
}

/**
 * Build the command and arguments for installing a specific version of paperforge via pip.
 *
 * @param {string} pythonExe   — resolved Python executable
 * @param {string} version     — version tag (e.g., "1.4.17rc3")
 * @param {string[]} [extraArgs=[]] — extra Python CLI args (e.g., venv activation flags)
 * @returns {{ cmd: string, args: string[], url: string, timeout: number }}
 */
function buildRuntimeInstallCommand(pythonExe, version, extraArgs) {
    if (extraArgs === undefined) extraArgs = [];
    const url = `git+https://github.com/LLLin000/PaperForge.git@${version}`;
    const args = [...extraArgs, "-m", "pip", "install", "--upgrade", url];
    return { cmd: pythonExe, args, url, timeout: 120000 };
}

/**
 * Parse the result of a subprocess version check into a structured status object.
 *
 * @param {Error|null}  err     — subprocess error object (or null on success)
 * @param {string|null} stdout  — subprocess stdout
 * @param {string|null} stderr  — subprocess stderr
 * @returns {{ status: string, version: string|null, type?: string, message?: string, recoverable?: boolean, action?: string }}
 */
function parseRuntimeStatus(err, stdout, stderr) {
    if (!err && stdout) {
        const version = stdout.trim();
        return { status: "ok", version };
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

    return { status: "error", version: null, type: "unknown", message: err ? err.message : String(stderr), recoverable: false };
}

module.exports = {
    classifyError,
    buildRuntimeInstallCommand,
    parseRuntimeStatus,
};
