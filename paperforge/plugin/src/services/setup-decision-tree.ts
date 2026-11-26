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
 *  2. checking               — initial/active probe in flight
 *  3. engine_version_mismatch— runtime exists but version != plugin version
 *  4. engine_not_installed   — no managed Python runtime pointer on disk
 *  5. engine_probe_failed    — runtime exists & version matches, yet probe failed/unresponsive
 *  6. legacy_vault_upgrade   — engine ready & veteran vault detected, 1-click lossless cutover available
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
  minEngineVersion?: string;
  installationEnv: ProbeEnvelope;
  libraryEnv: ProbeEnvelope;
  isProbing: boolean;
  zoteroDataDir: string;
  zoteroDetectedPapers: number | null;
  lastAutoSyncError: string | null;
  paperCount: number | null;
}

const STAGE_ORDER: Record<string, number> = {
  a: -3,
  b: -2,
  rc: -1,
  "": 0,
};

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

export function parseReleaseTuple(
  version: string | null | undefined
): [number, number, number, number, number, number] | null {
  const norm = normalizeSemverForCompare(version);
  if (!norm) return null;
  const preMatch = /^(\d+(?:\.\d+)*)(a|b|rc)(\d+)(?:\.post(\d+))?$/.exec(norm);
  let nums: number[];
  let stage = 0;
  let stageNum = 0;
  let postNum = 0;
  if (preMatch) {
    nums = preMatch[1].split(".").map((n) => parseInt(n, 10));
    stage = STAGE_ORDER[preMatch[2]] ?? 0;
    stageNum = parseInt(preMatch[3], 10);
    postNum = preMatch[4] ? parseInt(preMatch[4], 10) : 0;
  } else {
    const finalMatch = /^(\d+(?:\.\d+)*)(?:\.post(\d+))?$/.exec(norm);
    if (!finalMatch) return null;
    nums = finalMatch[1].split(".").map((n) => parseInt(n, 10));
    postNum = finalMatch[2] ? parseInt(finalMatch[2], 10) : 0;
  }
  while (nums.length < 3) nums.push(0);
  return [nums[0], nums[1], nums[2], stage, stageNum, postNum];
}

export function compareReleaseVersions(
  a: string | null | undefined,
  b: string | null | undefined
): number | null {
  const ta = parseReleaseTuple(a);
  const tb = parseReleaseTuple(b);
  if (!ta || !tb) return null;
  for (let i = 0; i < 6; i++) {
    if (ta[i] !== tb[i]) return ta[i] < tb[i] ? -1 : 1;
  }
  return 0;
}

/**
 * Evaluate runtime compatibility matching `paperforge/core/versioning.py`:
 * when `minEngineVersion` is provided, any runtime >= `minEngineVersion` is
 * compatible (so UI-only patch bumps do not force unnecessary backend updates);
 * otherwise falls back to exact normalized equality against `expectedVersion`.
 */
export function isEngineVersionCompatible(
  coreVersion: string | null | undefined,
  expectedVersion: string | null | undefined,
  minEngineVersion?: string | null
): boolean {
  const core = normalizeSemverForCompare(coreVersion);
  if (!core) return false;
  const minEng = normalizeSemverForCompare(minEngineVersion);
  if (minEng) {
    const cmp = compareReleaseVersions(core, minEng);
    if (cmp !== null) return cmp >= 0;
    return core === minEng;
  }
  const exp = normalizeSemverForCompare(expectedVersion);
  if (exp) return core === exp;
  return true;
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

  const instState = input.installationEnv.user_state;
  const libState = input.libraryEnv.user_state;

  // 2. Active checking state
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
  const versionCompatible = ptr
    ? isEngineVersionCompatible(
        ptr.paperforgeVersion,
        input.expectedVersion,
        input.minEngineVersion
      )
    : true;
  const versionMismatch =
    Boolean(ptr && !versionCompatible) ||
    input.installationEnv.reason?.code === "version_mismatch";
  const needsVaultUpgrade =
    input.upgradePlan?.provenance?.needs_upgrade === true;

  // 3. Engine version mismatch (ensure compute engine is aligned before any vault migration)
  if (versionMismatch && ptr) {
    const body = needsVaultUpgrade
      ? `${t("dt_version_mismatch_body")} ${t("dt_legacy_after_engine_hint")}`
      : t("dt_version_mismatch_body");
    return {
      id: "engine_version_mismatch",
      badgeCls: "attention",
      badgeText: t("dt_badge_update_needed"),
      title: t("dt_version_mismatch_title")
        .replace("{expected}", input.expectedVersion || "?")
        .replace("{current}", ptr.paperforgeVersion || "?"),
      body,
      primaryAction: {
        kind: "update_engine",
        label: t("dt_btn_update_engine"),
      },
    };
  }

  // 4. Engine not installed at all (brand-new user or legacy user before new runtime install)
  if (!ptr) {
    const body = needsVaultUpgrade
      ? `${t("dt_step1_body")} ${t("dt_legacy_after_engine_hint")}`
      : t("dt_step1_body");
    return {
      id: "engine_not_installed",
      badgeCls: "attention",
      badgeText: t("dt_badge_step1"),
      title: t("dt_step1_title"),
      body,
      primaryAction: {
        kind: "start_setup_step1",
        label: t("cc_start_setup"),
      },
    };
  }

  // 5. Engine IS installed on disk, but probe failed / unresponsive — NEVER lie and say "install step 1"!
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

  // 6. Veteran vault lossless directory upgrade (compute engine is ready, cutover runs cleanly)
  if (needsVaultUpgrade && !input.upgradeBannerDismissed) {
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

  // 7. Engine ready, Zotero not configured yet (trust backend authority over stale settings)
  const hasZoteroDir = Boolean(input.zoteroDataDir.trim());
  const backendReportsZoteroMissing =
    input.libraryEnv.reason?.code === "library.zotero_missing" ||
    input.libraryEnv.capability_state === "missing_input" ||
    libState === "setup_required";
  if (libState !== "ready" && (!hasZoteroDir || backendReportsZoteroMissing)) {
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
