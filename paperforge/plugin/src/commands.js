/**
 * Action definitions and subprocess dispatch for PaperForge plugin commands.
 *
 * Extracted from main.js for testability. Provides:
 * - ACTIONS array (same as main.js lines 189-243)
 * - buildCommandArgs — resolves action arguments (key, filter flags)
 * - runSubprocess — Promisified spawn with stdout/stderr capture
 *
 * `runSubprocess` accepts an optional `_spawn` parameter for testing.
 */
"use strict";

const { spawn } = require("node:child_process");

/**
 * Action definitions for the PaperForge dashboard quick-action buttons.
 *
 * Each action maps to a `paperforge <cmd>` CLI invocation.
 */
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
        disabled: true,
        disabledMsg: "Repair Issues will be available in a future update.",
    },
    {
        id: "paperforge-copy-context",
        title: "Copy Context",
        desc: "Copy this paper\u2019s canonical index entry JSON to clipboard for AI use",
        icon: "\u2139",
        cmd: "context",
        needsKey: true,
        okMsg: "Context copied",
    },
    {
        id: "paperforge-copy-collection-context",
        title: "Copy Collection Context",
        desc: "Copy canonical index entries for all visible papers to clipboard",
        icon: "\u2261",
        cmd: "context",
        needsFilter: true,
        okMsg: "Collection context copied",
    },
];

/**
 * Resolve extra CLI arguments for an action based on needsKey and needsFilter flags.
 *
 * @param {object} action    — action object from ACTIONS array
 * @param {string|null} key  — zotero_key for per-paper actions
 * @param {boolean} [filter] — whether to add --all filter
 * @returns {string[]}
 */
function buildCommandArgs(action, key, filter) {
    const args = Array.isArray(action.args) ? [...action.args] : [];
    if (action.needsKey && key) {
        args.push(key);
    }
    if (action.needsFilter || filter) {
        args.push("--all");
    }
    return args;
}

/**
 * Run a subprocess with full stdout/stderr capture, wrapped in a Promise.
 *
 * @param {string} pythonExe   — resolved Python executable path
 * @param {string[]} args      — CLI arguments
 * @param {string} cwd         — working directory (vault root)
 * @param {number} [timeout]   — timeout in ms
 * @param {Function} [_spawn]  — optional injected spawn (for testing)
 * @returns {Promise<{ stdout: string, stderr: string, exitCode: number|null, elapsed: number }>}
 */
function runSubprocess(pythonExe, args, cwd, timeout, _spawn) {
    const sp = _spawn || spawn;

    return new Promise((resolve) => {
        const startTime = Date.now();
        const child = sp(pythonExe, args, { cwd, timeout, windowsHide: true });
        const stdoutChunks = [];
        const stderrChunks = [];

        child.stdout.on("data", (data) => {
            stdoutChunks.push(data.toString("utf-8"));
        });
        child.stderr.on("data", (data) => {
            stderrChunks.push(data.toString("utf-8"));
        });

        child.on("close", (code) => {
            const elapsed = Date.now() - startTime;
            resolve({
                stdout: stdoutChunks.join(""),
                stderr: stderrChunks.join(""),
                exitCode: code,
                elapsed,
            });
        });

        child.on("error", (err) => {
            const elapsed = Date.now() - startTime;
            resolve({
                stdout: stdoutChunks.join(""),
                stderr: stderrChunks.join("") + "\n" + err.message,
                exitCode: -1,
                elapsed,
            });
        });
    });
}

module.exports = {
    ACTIONS,
    buildCommandArgs,
    runSubprocess,
};
