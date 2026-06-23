export type MaintenanceCategory = 'ok' | 'rebuild' | 'failed' | 'limited';
export type MaintenanceAction = 'rebuild' | 'redo' | null;

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
};

export function categorizeMaintenanceRow(row: MaintenanceRowLike) {
  if (row.recommended_action === 'rebuild') {
    return {
      category: 'rebuild' as const,
      label: 'Rebuild Recommended',
      primaryAction: 'rebuild' as const,
      reason: 'Derived OCR results can be regenerated from existing OCR data.',
    };
  }

  if (row.status === 'failed') {
    return {
      category: 'failed' as const,
      label: 'OCR Failed',
      primaryAction: 'redo' as const,
      reason: row.error_summary || 'OCR did not finish successfully.',
    };
  }

  if ((row.degraded_reasons || []).length > 0 || row.status === 'done_degraded') {
    return {
      category: 'limited' as const,
      label: 'Result Limited',
      primaryAction: null,
      reason: row.degraded_reasons?.[0] || 'This paper has weaker confidence signals, but no clear maintenance action is recommended.',
    };
  }

  return {
    category: 'ok' as const,
    label: 'No Action Needed',
    primaryAction: null,
    reason: 'OCR results look usable and no maintenance action is recommended.',
  };
}

export function buildMaintenanceSummary(items: Array<{ category: MaintenanceCategory }>) {
  const counts = { ok: 0, rebuild: 0, failed: 0, limited: 0 };
  for (const item of items) counts[item.category] += 1;
  const tone = counts.failed > 0 || counts.rebuild > 0 ? 'warn' : 'ok';
  return { counts, tone };
}
