/**
 * Unified user-facing feedback & error translation layer.
 *
 * Enforces the 3-tier Obsidian notification hierarchy:
 * 1. Translates raw technical errors / Python tracebacks / daemon error codes
 *    into calm, plain-language localized messages via `t(...)`.
 * 2. Localizes Rust daemon `notice.push` frames by semantic `code` (so the
 *    daemon never dictates user-facing natural language) and prevents duplicate
 *    toasts when an inline surface (e.g., Express onboarding) already owns UI.
 */

import { t } from "../i18n";

export interface DaemonNoticePayload {
  notice_id?: string;
  code?: string;
  level?: string;
  title?: string;
  detail?: string;
}

export interface FormattedNotice {
  message: string;
  durationMs: number;
}

/** Extract the single most informative error line from a multi-line traceback or stderr dump. */
export function extractConciseErrorLine(raw: unknown): string {
  const text =
    raw instanceof Error
      ? raw.message
      : typeof raw === "string"
        ? raw
        : raw != null
          ? String(raw)
          : "";
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);
  if (lines.length === 0) return "";
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i];
    if (
      line.startsWith("Traceback (") ||
      line.startsWith('File "') ||
      /^[\^~]+$/.test(line)
    ) {
      continue;
    }
    return line.replace(/\s+/g, " ").slice(0, 180);
  }
  return lines[lines.length - 1].replace(/\s+/g, " ").slice(0, 180);
}

/**
 * Convert raw exceptions, HTTP statuses, or daemon error strings into calm,
 * plain-language localized text for inline banners and notices.
 */
export function formatHumanError(
  rawErr: unknown,
  fallbackKey?: string
): string {
  const concise = extractConciseErrorLine(rawErr);
  const lower = concise.toLowerCase();

  if (lower.includes("daemon shut down")) {
    return t("err_human_daemon_restarting");
  }
  if (
    lower.includes("no_python") ||
    lower.includes("python worker runtime not installed") ||
    lower.includes("runtime not installed")
  ) {
    return t("err_human_no_python");
  }
  if (
    lower.includes("zotero_db_unreadable") ||
    lower.includes("database is locked") ||
    lower.includes("sqlite_busy")
  ) {
    return t("err_human_zotero_locked");
  }
  if (lower.includes("vault_upgrade_barrier_active")) {
    return t("err_human_upgrade_barrier");
  }
  if (
    lower.includes("401") ||
    lower.includes("unauthorized") ||
    lower.includes("invalid_api_key") ||
    lower.includes("invalid token") ||
    lower.includes("authentication")
  ) {
    return t("err_human_auth_invalid");
  }
  if (
    lower.includes("429") ||
    lower.includes("rate limit") ||
    lower.includes("quota") ||
    lower.includes("insufficient") ||
    lower.includes("balance")
  ) {
    return t("err_human_quota_exceeded");
  }
  if (lower.includes("404") || lower.includes("model_not_found")) {
    return t("err_human_model_not_found");
  }
  if (
    lower.includes("etimedout") ||
    lower.includes("timed out") ||
    lower.includes("timeout") ||
    lower.includes("econnrefused") ||
    lower.includes("enotfound") ||
    lower.includes("econnreset") ||
    lower.includes("network") ||
    lower.includes("connectionerror") ||
    lower.includes("failed to fetch")
  ) {
    return t("err_human_network");
  }
  if (
    lower.includes("permissionerror") ||
    lower.includes("eacces") ||
    lower.includes("eperm") ||
    lower.includes("ebusy") ||
    lower.includes("file locked") ||
    lower.includes("access is denied")
  ) {
    return t("err_human_file_locked");
  }
  if (lower.includes("enoent") || lower.includes("no such file")) {
    return t("err_human_file_missing");
  }

  if (concise) {
    if (/^exit code \d+$/i.test(concise) && fallbackKey) {
      return `${t(fallbackKey)} (${concise})`;
    }
    return concise;
  }
  return fallbackKey ? t(fallbackKey) : t("err_human_generic");
}

function localizedJobKind(kind: string): string {
  switch (kind) {
    case "ocr":
      return t("daemon_job_kind_ocr");
    case "embed":
      return t("daemon_job_kind_embed");
    case "sync":
      return t("daemon_job_kind_sync");
    case "upgrade.heal":
      return t("daemon_job_kind_upgrade_heal");
    case "setup":
      return t("daemon_job_kind_setup");
    case "runtime.install":
    case "runtime.update":
      return t("daemon_job_kind_runtime");
    default:
      return kind || t("daemon_job_kind_generic");
  }
}

/**
 * Localize and deduplicate a Rust daemon `notice.push` event.
 * Returns `null` when the notice should be suppressed (e.g., already handled
 * inline by Express onboarding).
 */
export function formatDaemonNotice(
  payload: DaemonNoticePayload,
  opts?: { suppressRuntimeInstall?: boolean }
): FormattedNotice | null {
  const code = String(payload.code ?? "").trim();
  const level = String(payload.level ?? "info").trim();
  const rawTitle = String(payload.title ?? "").trim();
  const rawDetail = String(payload.detail ?? "").trim();
  const durationMs = level === "warning" || level === "error" ? 8000 : 5000;

  if (code === "runtime.install.done") {
    if (opts?.suppressRuntimeInstall) return null;
    return {
      message: t("daemon_notice_runtime_install_done"),
      durationMs: 5000,
    };
  }
  if (code === "runtime.install.failed") {
    if (opts?.suppressRuntimeInstall) return null;
    const detail = rawDetail ? formatHumanError(rawDetail) : "";
    const msg = detail
      ? t("daemon_notice_runtime_install_failed_detail").replace(
          "{detail}",
          detail
        )
      : t("daemon_notice_runtime_install_failed");
    return { message: msg, durationMs: 8000 };
  }
  if (code === "job.upgrade.heal.done") {
    return {
      message: t("daemon_notice_upgrade_heal_done"),
      durationMs: 5000,
    };
  }
  if (code.startsWith("job.") && code.endsWith(".failed")) {
    const kind = code.slice("job.".length, -".failed".length);
    const kindLabel = localizedJobKind(kind);
    const detail = rawDetail ? formatHumanError(rawDetail) : "";
    const msg = detail
      ? t("daemon_notice_job_failed_detail")
          .replace("{kind}", kindLabel)
          .replace("{detail}", detail)
      : t("daemon_notice_job_failed").replace("{kind}", kindLabel);
    return { message: msg, durationMs: 8000 };
  }

  if (!rawTitle) return null;
  const cleanDetail = rawDetail ? extractConciseErrorLine(rawDetail) : "";
  return {
    message: cleanDetail ? `${rawTitle}: ${cleanDetail}` : rawTitle,
    durationMs,
  };
}
