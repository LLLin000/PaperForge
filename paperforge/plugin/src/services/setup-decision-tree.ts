/**
 * Deterministic Setup, Upgrade & Readiness Decision Tree.
 *
 * Single source of truth for the Control Center Hero Card so the user ALWAYS
 * sees exactly ONE unambiguous state, ONE plain-language reason, and ONE
 * primary next action — never contradictory banners fighting for attention.
 *
 * Strict priority order:
 *  0. engine_updating        — native daemon hot-swap or runtime install/update in progress
 *  1. engine_quarantined     — native binary vanished (antivirus quarantine)
 *  2. legacy_vault_upgrade   — veteran vault detected, 1-click lossless cutover available
 *  3. checking               — initial/active probe in flight
 *  4. engine_not_installed   — no managed Python runtime pointer on disk
 *  5. engine_version_mismatch— runtime exists but version != plugin version
 *  6. engine_probe_failed    — runtime exists & version matches, yet probe failed/unresponsive
 *  7. zotero_not_configured  — engine ready, Zotero directory not yet connected
 *  8. library_sync_error     — engine & Zotero configured, sync blocked/failed
 *  9. ready                  — core engine + Zotero library healthy and ready
 */

import type { ProbeEnvelope } from "../constants";
import type { VaultUpgradePlanDto } from "../client";
import type { PointerInfo } from "./managed-runtime";
import { t } from "../i18n";

export type SetupDecisionId =
  | "engine_updating"
  | "engine_quarantined"
  | "legacy_vault_upgrade"
  | "checking"
  | "engine_not_installed"
  | "engine_version_mismatch"
  | "engine_probe_failed"
  | "zotero_not_configured"
  | "library_sync_error"
  | "ready";

export type SetupDecisionActionKind =
  | "none"
  | "cancel_install"
  | "copy_quarantine_path"
  | "dismiss_quarantine"
  | "open_vault_upgrade"
  | "dismiss_vault_upgrade"
  | "start_setup_step1"
  | "update_engine"
  | "refresh_status"
  | "repair_engine"
  | "connect_zotero"
  | "retry_sync";

export interface SetupDecisionAction {
  kind: SetupDecisionActionKind;
  label: string;
}

export interface SetupDecision {
  id: SetupDecisionId;
  badgeCls: "ready" | "checking" | "attention";
  badgeText: string;
  title: string;
  body: string;
  codeBlock?: string;
  primaryAction?: SetupDecisionAction;
  secondaryAction?: SetupDecisionAction;
}

export interface SetupDecisionInput {
  daemonUpdating: boolean;
  runtimeUpdating: boolean;
  canCancelInstall: boolean;
  quarantinedBinDir: string | null;
  upgradePlan: VaultUpgradePlanDto | null;
  upgradeBannerDismissed: boolean;
  runtimePointer: PointerInfo | null;
  expectedVersion: string;
  installationEnv: ProbeEnvelope;
  libraryEnv: ProbeEnvelope;
  isProbing: boolean;
  zoteroDataDir: string;
  zoteroDetectedPapers: number | null;
  lastAutoSyncError: string | null;
  paperCount: number | null;
}

export function normalizeSemverForCompare(
  raw: string | null | undefined
): string {
  return String(raw || "")
    .trim()
    .replace(/^[vV]/, "")
    .replace(/[-_.]?(?:rc)\.?(\d+)/i, "rc$1")
    .replace(/[-_.]?(?:beta|b)\.?(\d+)/i, "b$1")
    .replace(/[-_.]?(?:alpha|a)\.?(\d+)/i, "a$1")
    .toLowerCase();
}

export function resolveSetupDecision(input: SetupDecisionInput): SetupDecision {
  // 0. Active hot-swap / engine install / update — suppress transient probe/sync noise
  if (input.daemonUpdating || input.runtimeUpdating) {
    return {
      id: "engine_updating",
      badgeCls: "checking",
      badgeText: t("dt_badge_updating"),
      title: input.daemonUpdating
        ? t("dt_engine_hotswap_title")
        : t("dt_engine_updating_title"),
      body: t("dt_engine_updating_body"),
      primaryAction: input.canCancelInstall
        ? { kind: "cancel_install", label: t("wizard_cancel") }
        : undefined,
    };
  }

  // 1. Antivirus quarantine of native accelerator binary
  if (input.quarantinedBinDir) {
    return {
      id: "engine_quarantined",
      badgeCls: "attention",
      badgeText: t("cc_badge_attention"),
      title: t("main_defender_banner_title"),
      body: t("main_defender_banner_desc"),
      codeBlock: input.quarantinedBinDir,
      primaryAction: {
        kind: "copy_quarantine_path",
        label: t("main_defender_copy_path"),
      },
      secondaryAction: {
        kind: "dismiss_quarantine",
        label: t("base_missing_pdf_dismiss"),
      },
    };
  }

  // 2. Veteran vault lossless directory upgrade (highest user priority after engine alive)
  if (
    input.upgradePlan?.provenance?.needs_upgrade === true &&
    !input.upgradeBannerDismissed
  ) {
    return {
      id: "legacy_vault_upgrade",
      badgeCls: "attention",
      badgeText: t("dt_badge_upgrade"),
      title: t("upgrade_banner_title"),
      body: t("upgrade_banner_desc"),
      primaryAction: {
        kind: "open_vault_upgrade",
        label: t("upgrade_banner_open"),
      },
      secondaryAction: {
        kind: "dismiss_vault_upgrade",
        label: t("upgrade_btn_defer"),
      },
    };
  }

  const instState = input.installationEnv.user_state;
  const libState = input.libraryEnv.user_state;

  // 3. Active checking state
  if (
    instState === "checking" ||
    libState === "checking" ||
    (input.isProbing && input.installationEnv.capability_state === "unknown")
  ) {
    return {
      id: "checking",
      badgeCls: "checking",
      badgeText: t("cc_badge_checking"),
      title: t("cc_summary_checking"),
      body: t("cc_summary_checking_body"),
    };
  }

  const ptr = input.runtimePointer;
  const expNorm = normalizeSemverForCompare(input.expectedVersion);
  const ptrNorm = normalizeSemverForCompare(ptr?.paperforgeVersion);
  const versionMismatch =
    Boolean(ptr && expNorm && ptrNorm && ptrNorm !== expNorm) ||
    input.installationEnv.reason?.code === "version_mismatch";

  // 4. Engine version mismatch (existing user upgraded plugin, engine still on older version)
  if (versionMismatch && ptr) {
    return {
      id: "engine_version_mismatch",
      badgeCls: "attention",
      badgeText: t("dt_badge_update_needed"),
      title: t("dt_version_mismatch_title")
        .replace("{expected}", input.expectedVersion || "?")
        .replace("{current}", ptr.paperforgeVersion || "?"),
      body: t("dt_version_mismatch_body"),
      primaryAction: {
        kind: "update_engine",
        label: t("dt_btn_update_engine"),
      },
    };
  }

  // 5. Engine not installed at all (brand-new user)
  if (instState !== "ready" && !ptr) {
    return {
      id: "engine_not_installed",
      badgeCls: "attention",
      badgeText: t("dt_badge_step1"),
      title: t("dt_step1_title"),
      body: t("dt_step1_body"),
      primaryAction: {
        kind: "start_setup_step1",
        label: t("cc_start_setup"),
      },
    };
  }

  // 6. Engine IS installed on disk, but probe failed / unresponsive — NEVER lie and say "install step 1"!
  if (instState !== "ready" && ptr) {
    return {
      id: "engine_probe_failed",
      badgeCls: "attention",
      badgeText: t("dt_badge_check_failed"),
      title: t("dt_probe_failed_title").replace(
        "{version}",
        ptr.paperforgeVersion || input.expectedVersion || "?"
      ),
      body: t("dt_probe_failed_body"),
      primaryAction: {
        kind: "refresh_status",
        label: t("cc_refresh_btn"),
      },
      secondaryAction: {
        kind: "repair_engine",
        label: t("dt_btn_repair_engine"),
      },
    };
  }

  // 7. Engine ready, Zotero not configured yet
  const hasZoteroDir = Boolean(input.zoteroDataDir.trim());
  if (libState !== "ready" && !hasZoteroDir) {
    const body =
      typeof input.zoteroDetectedPapers === "number" &&
      input.zoteroDetectedPapers > 0
        ? t("dt_step2_body_detected").replace(
            "{count}",
            String(input.zoteroDetectedPapers)
          )
        : t("dt_step2_body");
    return {
      id: "zotero_not_configured",
      badgeCls: "attention",
      badgeText: t("dt_badge_step2"),
      title: t("dt_step2_title"),
      body,
      primaryAction: {
        kind: "connect_zotero",
        label: t("dt_btn_connect_zotero"),
      },
    };
  }

  // 8. Engine & Zotero configured, but sync failed or library probe not ready
  if (libState !== "ready" || input.lastAutoSyncError) {
    const detail =
      input.lastAutoSyncError ||
      input.libraryEnv.reason?.text ||
      t("cc_summary_connect_library_body");
    return {
      id: "library_sync_error",
      badgeCls: "attention",
      badgeText: t("dt_badge_sync_paused"),
      title: t("main_autosync_failed_title"),
      body: detail,
      primaryAction: {
        kind: "retry_sync",
        label: t("main_autosync_retry"),
      },
      secondaryAction: {
        kind: "connect_zotero",
        label: t("dt_btn_check_zotero"),
      },
    };
  }

  // 9. Ready!
  const title =
    typeof input.paperCount === "number" && input.paperCount > 0
      ? t("dt_ready_with_count").replace("{count}", String(input.paperCount))
      : t("cc_summary_ready");
  return {
    id: "ready",
    badgeCls: "ready",
    badgeText: t("cc_badge_ready"),
    title,
    body: t("cc_summary_ready_body"),
  };
}
