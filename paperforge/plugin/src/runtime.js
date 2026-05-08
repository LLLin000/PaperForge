/**
 * Runtime environment helpers — Python executable resolution and version checking.
 *
 * Extracted from main.js for testability. These functions handle:
 * - Finding a usable Python interpreter (manual, venv, system)
 * - Reading the plugin version from the Obsidian manifest
 * - Checking the installed paperforge package version against the plugin
 *
 * Dependencies are accepted as optional parameters for testability.
 * When omitted, they are eagerly required at the top level.
 */
"use strict";

const fs = require("fs");
const path = require("path");
const { execFile } = require("node:child_process");

/**
 * Resolve a usable Python executable by trying candidates in priority order.
 *
 *  1. Manual override (settings.python_path)
 *  2. Venv candidates (common venv locations under vaultPath)
 *  3. System candidates (py -3, python, python3)
 *  4. Last-resort fallback
 *
 * @param {string} vaultPath    — root path of the Obsidian vault
 * @param {object} settings     — plugin settings (may contain python_path)
 * @param {object} [_fs]        — optional injected fs module (for testing)
 * @param {Function} [_execFileSync] — optional injected execFileSync (for testing)
 * @returns {{ path: string, source: string, extraArgs: string[] }}
 */
function resolvePythonExecutable(vaultPath, settings, _fs, _execFileSync) {
    const f = _fs || fs;
    const execSync = _execFileSync || require("node:child_process").execFileSync;

    // 1. Manual override — absolute source of truth
    if (settings && settings.python_path && settings.python_path.trim()) {
        const manualPath = settings.python_path.trim();
        if (f.existsSync(manualPath)) {
            return { path: manualPath, source: "manual", extraArgs: [] };
        }
    }

    // 2. Venv candidates
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

    // 3. System candidates — test each with --version, pick first that succeeds
    const systemCandidates = [
        { path: "py", extraArgs: ["-3"] },
        { path: "python", extraArgs: [] },
        { path: "python3", extraArgs: [] },
    ];
    for (const candidate of systemCandidates) {
        try {
            const verOut = execSync(candidate.path, [...candidate.extraArgs, "--version"], {
                encoding: "utf-8",
                timeout: 5000,
                windowsHide: true,
            });
            if (verOut && verOut.toLowerCase().includes("python")) {
                return { path: candidate.path, source: "auto-detected", extraArgs: candidate.extraArgs };
            }
        } catch {}
    }

    // 4. Last-resort fallback
    return { path: "python", source: "auto-detected", extraArgs: [] };
}

/**
 * Read the plugin version from the Obsidian app manifest.
 *
 * @param {object} app  — Obsidian App instance (from plugin)
 * @returns {string|null}
 */
function getPluginVersion(app) {
    try {
        const manifest =
            app &&
            app.plugins &&
            app.plugins.plugins &&
            app.plugins.plugins["paperforge"] &&
            app.plugins.plugins["paperforge"].manifest;
        return (manifest && manifest.version) || null;
    } catch {
        return null;
    }
}

/**
 * Check whether the installed paperforge Python package matches the plugin version.
 *
 * Spawns:  pythonExe -c "import paperforge; print(paperforge.__version__)"
 *
 * @param {string} pythonExe      — resolved Python executable path
 * @param {string} pluginVersion  — expected version from manifest
 * @param {string} cwd            — working directory (vault root)
 * @param {number} [timeout=10000] — timeout in ms
 * @param {Function} [_execFile]  — optional injected execFile (for testing)
 * @returns {Promise<{ status: string, pyVersion: string|null, pluginVersion: string, error: string|null }>}
 */
function checkRuntimeVersion(pythonExe, pluginVersion, cwd, timeout, _execFile) {
    if (timeout === undefined) timeout = 10000;
    const exe = _execFile || execFile;

    return new Promise((resolve) => {
        exe(
            pythonExe,
            ["-c", "import paperforge; print(paperforge.__version__)"],
            { cwd, timeout },
            (err, stdout) => {
                if (err) {
                    resolve({
                        status: "not-installed",
                        pyVersion: null,
                        pluginVersion,
                        error: err.message,
                    });
                    return;
                }
                const pyVer = (stdout && stdout.trim()) || null;
                if (pyVer === pluginVersion) {
                    resolve({
                        status: "match",
                        pyVersion: pyVer,
                        pluginVersion,
                        error: null,
                    });
                } else {
                    resolve({
                        status: "mismatch",
                        pyVersion: pyVer,
                        pluginVersion,
                        error: null,
                    });
                }
            },
        );
    });
}

module.exports = {
    resolvePythonExecutable,
    getPluginVersion,
    checkRuntimeVersion,
};
