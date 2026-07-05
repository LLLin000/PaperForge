import * as fs from "fs";
import * as path from "path";
import { execFile } from "child_process";

export type MaintenanceCategory = "ok" | "rebuild" | "failed" | "limited";
export type MaintenanceAction = "rebuild" | "redo" | null;

export type DisplayAction =
  | "retry_ocr"
  | "rebuild_result"
  | "upgrade_legacy"
  | "add_pdf"
  | "configure_ocr"
  | "none";
export type DisplayGroup =
  | "retry"
  | "rebuild"
  | "legacy_optional"
  | "external_action"
  | "hidden";
export type DisplaySeverity = "actionable" | "optional" | "external" | "normal";

export interface MaintenanceDisplayRow {
  key: string;
  title: string;
  display_action: DisplayAction;
  display_label: string;
  display_reason: string;
  display_group: DisplayGroup;
  visible_in_maintenance: boolean;
  can_redo: boolean;
  can_rebuild: boolean;
  fulltext_drift_state?: "MATCHED" | "DRIFTED" | "UNKNOWN";
  fulltext_drift_reason?: string;
}

export interface MaintenanceCache {
  manifest: Record<string, string>;
  papers: Record<string, MaintenanceDisplayRow>;
  cached_at: string;
}

export type MaintenanceRowLike = {
  key: string;
  title: string;
  title_full: string;
  status: string;
  health: string;
  recommended_action: string;
  degraded_reasons: string[];
  error_summary: string;
  error_stage: string;
  version: string;
  finished_at: string;
  rebuild_finished_at: string;
  model: string;
  fulltext_drift_state?: "MATCHED" | "DRIFTED" | "UNKNOWN";
  fulltext_drift_reason?: string;
};

export function categorizeMaintenanceRow(row: MaintenanceRowLike) {
  if (row.recommended_action === "rebuild") {
    // ponytail: drift message for DRIFTED+rebuild; other drift states keep default
    const driftSuffix =
      row.fulltext_drift_state === "DRIFTED"
        ? " (fulltext has changed since machine wrote it)"
        : "";
    return {
      category: "rebuild" as const,
      label: "Rebuild Recommended",
      primaryAction: "rebuild" as const,
      reason:
        "Derived OCR results can be regenerated from existing OCR data." +
        driftSuffix,
    };
  }

  if (row.status === "failed") {
    return {
      category: "failed" as const,
      label: "OCR Failed",
      primaryAction: "redo" as const,
      reason: row.error_summary || "OCR did not finish successfully.",
    };
  }

  if (
    (row.degraded_reasons || []).length > 0 ||
    row.status === "done_degraded"
  ) {
    return {
      category: "limited" as const,
      label: "Result Limited",
      primaryAction: null,
      reason:
        row.degraded_reasons?.[0] ||
        "This paper has weaker confidence signals, but no clear maintenance action is recommended.",
    };
  }

  if (row.fulltext_drift_state === "UNKNOWN") {
    return {
      category: "ok" as const,
      label: "No Action Needed",
      primaryAction: null,
      reason: row.fulltext_drift_reason || "No machine baseline is available.",
    };
  }

  return {
    category: "ok" as const,
    label: "No Action Needed",
    primaryAction: null,
    reason: "OCR results look usable and no maintenance action is recommended.",
  };
}

export function buildMaintenanceSummary(
  items: Array<{ category: MaintenanceCategory }>
) {
  const counts = { ok: 0, rebuild: 0, failed: 0, limited: 0 };
  for (const item of items) counts[item.category] += 1;
  const tone = counts.failed > 0 || counts.rebuild > 0 ? "warn" : "ok";
  return { counts, tone };
}

function ocrMaintenanceCachePath(vaultPath: string): string {
  return path.join(
    vaultPath,
    "System",
    "PaperForge",
    "cache",
    "ocr_maintenance.json"
  );
}

export function readMaintenanceCache(
  vaultPath: string
): MaintenanceCache | null {
  try {
    const filePath = ocrMaintenanceCachePath(vaultPath);
    const raw = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(raw) as MaintenanceCache;
  } catch {
    return null;
  }
}

export function writeMaintenanceCache(
  vaultPath: string,
  cache: MaintenanceCache
): void {
  const filePath = ocrMaintenanceCachePath(vaultPath);
  const dir = path.dirname(filePath);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(cache, null, 2), "utf-8");
}

function execFilePromise(
  cmd: string,
  args: string[],
  options: { cwd: string; timeout: number }
): Promise<string> {
  return new Promise<string>((resolve, reject) => {
    execFile(cmd, args, options, (err: Error | null, stdout: string) => {
      if (err) reject(err);
      else resolve(stdout);
    });
  });
}

export async function refreshMaintenanceData(
  vaultPath: string,
  pythonExe: string,
  extraArgs: string[],
  currentCache: MaintenanceCache | null
): Promise<{ data: MaintenanceDisplayRow[]; changed: boolean }> {
  const manifestOut = await execFilePromise(
    pythonExe,
    [...extraArgs, "-m", "paperforge", "ocr", "list", "--manifest"],
    { cwd: vaultPath, timeout: 30000 }
  );
  const manifest: Record<string, string> = JSON.parse(manifestOut);

  if (currentCache) {
    const cacheKeys = Object.keys(currentCache.manifest);
    const manifestKeys = Object.keys(manifest);
    const same =
      cacheKeys.length === manifestKeys.length &&
      cacheKeys.every((k) => currentCache.manifest[k] === manifest[k]);
    if (same) {
      const data = Object.values(currentCache.papers).filter(
        (p) => p.visible_in_maintenance
      );
      return { data, changed: false };
    }
  }

  const changedKeys = Object.keys(manifest).filter(
    (key) =>
      !currentCache?.manifest[key] ||
      currentCache.manifest[key] !== manifest[key]
  );

  const dataOut = await execFilePromise(
    pythonExe,
    [
      ...extraArgs,
      "-m",
      "paperforge",
      "ocr",
      "list",
      "--json",
      "--keys",
      ...changedKeys,
    ],
    { cwd: vaultPath, timeout: 30000 }
  );
  const updatedPapers: MaintenanceDisplayRow[] = JSON.parse(dataOut);

  const cache: MaintenanceCache = {
    manifest,
    papers: {},
    cached_at: new Date().toISOString(),
  };
  if (currentCache?.papers) {
    for (const key of Object.keys(manifest)) {
      if (currentCache.papers[key]) {
        cache.papers[key] = currentCache.papers[key];
      }
    }
  }
  for (const p of updatedPapers) {
    cache.papers[p.key] = p;
  }
  writeMaintenanceCache(vaultPath, cache);

  const data = Object.values(cache.papers).filter(
    (p) => p.visible_in_maintenance
  );
  return { data, changed: true };
}
