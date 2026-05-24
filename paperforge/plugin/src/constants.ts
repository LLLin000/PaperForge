// ── View type, icon, SVG ──

export const VIEW_TYPE_PAPERFORGE = "paperforge-status";
export const PF_ICON_ID = "paperforge";
export const PF_RIBBON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path><line x1="8" y1="7" x2="16" y2="7"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>`;

// ── Action definitions ──

export interface ActionDef {
  id: string;
  title: string;
  desc?: string;
  icon?: string;
  cmd: string;
  args?: string[];
  needsKey?: boolean;
  needsFilter?: boolean;
  okMsg?: string;
  disabled?: boolean;
  disabledMsg?: string;
}

export const ACTIONS: ActionDef[] = [
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

// ── Settings ──

export interface PaperForgeSettings {
  python_path: string;
  vault_path: string;
  setup_complete: boolean;
  auto_update: boolean;
  auto_update_on_startup: boolean;
  features: Record<string, boolean>;
  frozen_skills: Record<string, string>;
  system_dir: string;
  resources_dir: string;
  literature_dir: string;
  base_dir: string;
  agent_platform: string;
  language: string;
  paddleocr_api_key: string;
  zotero_data_dir: string;
  selected_skill_platform: string;
  vector_db_api_key: string;
  vector_db_api_base: string;
  vector_db_api_model: string;
  _python_path_stale?: boolean;
  [key: string]: unknown;
}

export const DEFAULT_SETTINGS: PaperForgeSettings = {
  vault_path: "",
  setup_complete: false,
  auto_update: true,
  auto_update_on_startup: true,
  agent_platform: "opencode",
  language: "",
  paddleocr_api_key: "",
  zotero_data_dir: "",
  python_path: "",
  features: {
    memory_layer: true,
    vector_db: false,
  },
  selected_skill_platform: "opencode",
  vector_db_api_key: "",
  vector_db_api_base: "",
  vector_db_api_model: "text-embedding-3-small",
  frozen_skills: {},
  system_dir: "",
  resources_dir: "",
  literature_dir: "",
  base_dir: "",
};

// ── Workflow state helpers ──

export interface WorkflowState {
  [key: string]: unknown;
}

export function overlayEntryWorkflowState(app: any, entry: any): WorkflowState {
  if (!entry || !entry.note_path) return entry;
  const noteFile = app.vault.getAbstractFileByPath(entry.note_path);
  if (!noteFile) return entry;
  const cache = app.metadataCache.getFileCache(noteFile);
  const fm = cache && cache.frontmatter;
  if (!fm) return entry;
  const merged = { ...entry };
  for (const key of ["do_ocr", "analyze", "ocr_status", "deep_reading_status"]) {
    if (Object.prototype.hasOwnProperty.call(fm, key)) merged[key] = fm[key];
  }
  return merged;
}

export function patchEntryWorkflowState(entry: any, patch: Partial<WorkflowState>): any {
  return entry ? { ...entry, ...patch } : entry;
}
