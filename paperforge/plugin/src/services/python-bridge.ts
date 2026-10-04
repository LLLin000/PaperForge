/**
 * python-bridge — pure PaperForge helpers (Ticket 07 step 6 item 5).
 *
 * NOT a bridge and NOT an execution surface: child-process authority lives
 * exclusively at `client/node-transport.ts`.  The former runtime bootstrap
 * helpers (resolvePythonExecutable / checkRuntimeVersion / runQueryPlan /
 * install-command builders / python probing) were dead after the client
 * cutover and were deleted; PATH/env bootstrap moved to the transport root
 * where the child is actually spawned.  What remains is presentation
 * classification, legacy argv derivation, and host fs probes — all pure.
 */

import * as fs from "fs";
import * as path from "path";

export interface PythonResult {
  path: string;
  source: "manual" | "auto-detected";
  extraArgs: string[];
}

export interface ErrorClassification {
  type: string;
  message: string;
  recoverable: boolean;
  action?: string;
}

export function classifyError(errorCode: string): ErrorClassification {
  const code = String(errorCode);
  const patterns: Record<string, ErrorClassification> = {
    ENOENT: {
      type: "python_missing",
      message: "Python executable not found",
      recoverable: true,
    },
    "python-missing": {
      type: "python_missing",
      message: "Python executable not found",
      recoverable: true,
    },
    MODULE_NOT_FOUND: {
      type: "import_failed",
      message: "PaperForge package not installed",
      recoverable: true,
    },
    "import-failed": {
      type: "import_failed",
      message: "PaperForge package not installed",
      recoverable: true,
    },
    "version-mismatch": {
      type: "version_mismatch",
      message: "Plugin and package versions differ",
      recoverable: true,
      action: "sync-runtime",
    },
    "pip-failed": {
      type: "pip_install_failure",
      message: "pip install command failed",
      recoverable: true,
    },
    ETIMEDOUT: {
      type: "timeout",
      message: "Subprocess timed out",
      recoverable: true,
      action: "retry",
    },
    timeout: {
      type: "timeout",
      message: "Subprocess timed out",
      recoverable: true,
      action: "retry",
    },
    NO_PYTHON: {
      type: "no_python",
      message: "Python executable not found",
      recoverable: true,
      action: "open-setup",
    },
    VECTOR_NOT_BUILT: {
      type: "vectors_not_built",
      message: "Vector index has not been built yet",
      recoverable: true,
      action: "open-vector-settings",
    },
    VECTOR_CORRUPTED: {
      type: "vectors_corrupted",
      message: "Vector index is corrupted",
      recoverable: true,
      action: "force-rebuild",
    },
    MODEL_CHANGED: {
      type: "model_changed",
      message: "Embedding model has changed since vectors were built",
      recoverable: true,
      action: "rebuild-vectors",
    },
    BACKEND_UNAVAILABLE: {
      type: "backend_unavailable",
      message: "Python CLI search backend is not responding",
      recoverable: true,
      action: "run-doctor",
    },
    TIMEOUT: {
      type: "timeout",
      message: "Search timed out",
      recoverable: true,
      action: "retry",
    },
    INTERNAL_ERROR: {
      type: "internal_error",
      message: "An internal error occurred",
      recoverable: false,
    },
  };
  const match = patterns[code];
  if (match) return { ...match };
  return { type: "unknown", message: String(errorCode), recoverable: false };
}

/**
 * Free-text setup/install failures (venv/pip/handshake messages) get a
 * pattern pass over the SAME taxonomy `classifyError` uses, so the wizard
 * and the dashboard cannot drift into two classifiers.  Exact codes win
 * first; unmatched input stays "unknown".
 */
const SETUP_FAILURE_PATTERNS: Array<[RegExp, ErrorClassification]> = [
  [
    /no space left|disk full|enospc/,
    {
      type: "disk_full",
      message: "Not enough disk space",
      recoverable: true,
      action: "free-space",
    },
  ],
  [
    /being used by another process|winerror 32|is not empty|could not be removed/,
    {
      type: "process_busy",
      message: "A PaperForge process is still using the runtime",
      recoverable: true,
      action: "close-process",
    },
  ],
  [
    /permission denied|access is denied|winerror 5\b|eperm|eacces/,
    {
      type: "permission_denied",
      message: "The runtime directory could not be written",
      recoverable: true,
      action: "fix-permission",
    },
  ],
  [
    /no matching distribution|could not find a version|404|not available/,
    {
      type: "artifact_unavailable",
      message:
        "This PaperForge version is not available from the package index",
      recoverable: true,
      action: "check-release",
    },
  ],
  [
    /no compatible wheel|unsupported platform|requires-python|requires python/,
    {
      type: "wheel_unavailable",
      message: "No compatible package build for this Python/platform",
      recoverable: true,
      action: "check-python",
    },
  ],
  [
    /timed out|timeout|connection|tls|ssl|certificate|proxy|getaddrinfo|econn|enotfound|network is unreachable|10060|10054/,
    {
      type: "network",
      message: "The download could not reach the package index",
      recoverable: true,
      action: "retry-network",
    },
  ],
  [
    /module not found|modulenotfounderror|no module named|cannot import|fresh-child verify failed|verify failed/,
    {
      type: "import_failed",
      message: "PaperForge package not installed",
      recoverable: true,
    },
  ],
  [
    /version mismatch|installed version mismatch/,
    {
      type: "version_mismatch",
      message: "Plugin and package versions differ",
      recoverable: true,
      action: "sync-runtime",
    },
  ],
  [
    /no python|interpreter missing|python .*not found|older than the required/,
    {
      type: "no_python",
      message: "Python executable not found",
      recoverable: true,
      action: "open-setup",
    },
  ],
];

export function classifySetupFailure(message: string): ErrorClassification {
  const exact = classifyError(message);
  if (exact.type !== "unknown") return exact;
  const lowered = String(message ?? "").toLowerCase();
  for (const [pattern, classification] of SETUP_FAILURE_PATTERNS) {
    if (pattern.test(lowered)) return { ...classification };
  }
  return exact;
}

function dirLooksLikeBetterBibtexFolder(entryName: string): boolean {
  const compact = String(entryName)
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
  return compact.includes("betterbibtex");
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
      const extDir = path.join(profilesDir, prof, "extensions");
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
