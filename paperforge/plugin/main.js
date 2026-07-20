"use strict";
var Sr = Object.create;
var et = Object.defineProperty;
var Pr = Object.getOwnPropertyDescriptor;
var Cr = Object.getOwnPropertyNames;
var Rr = Object.getPrototypeOf,
  Ar = Object.prototype.hasOwnProperty;
var Tr = (d, l) => () => (l || d((l = { exports: {} }).exports, l), l.exports),
  Dr = (d, l) => {
    for (var e in l) et(d, e, { get: l[e], enumerable: !0 });
  },
  It = (d, l, e, t) => {
    if ((l && typeof l == "object") || typeof l == "function")
      for (let r of Cr(l))
        !Ar.call(d, r) &&
          r !== e &&
          et(d, r, {
            get: () => l[r],
            enumerable: !(t = Pr(l, r)) || t.enumerable,
          });
    return d;
  };
var z = (d, l, e) => (
    (e = d != null ? Sr(Rr(d)) : {}),
    It(
      l || !d || !d.__esModule
        ? et(e, "default", { value: d, enumerable: !0 })
        : e,
      d
    )
  ),
  Fr = (d) => It(et({}, "__esModule", { value: !0 }), d);
var xt = Tr((ln, Ir) => {
  Ir.exports = {
    versions: [
      {
        version: "1.5.15",
        date: "2026-06-01",
        title:
          "\u5168\u6587\u5B58\u50A8\u91CD\u6784 + OCR \u9605\u8BFB\u987A\u5E8F\u4FEE\u590D + Redo \u4E00\u952E\u91CD\u505A",
        breaking_or_migration: [
          "\u5168\u6587\u6587\u4EF6\u73B0\u5728\u7EDF\u4E00\u5B58\u653E\u4E8E System/PaperForge/ocr/ \u4E0B\uFF0C\u4E0D\u518D\u5728\u5DE5\u4F5C\u533A\u4FDD\u7559\u526F\u672C",
          "Redo OCR \u73B0\u5728\u4F1A\u7ACB\u5373\u6267\u884C\uFF08\u4E00\u952E\u5B8C\u6210\uFF09\uFF0C\u4E0D\u518D\u9700\u8981\u624B\u52A8\u518D\u8DD1\u4E00\u6B21",
        ],
        new_features: [
          "Redo OCR \u4E00\u952E\u95ED\u73AF\uFF1A\u52FE\u9009 \u2192 \u70B9\u6309\u94AE \u2192 \u81EA\u52A8\u5B8C\u6210\u5168\u90E8\u6D41\u7A0B",
          "\u8BBE\u7F6E\u9875\u65B0\u589E\u300C\u66F4\u65B0\u4E0E\u624B\u518C\u300D\u6807\u7B7E\u9875\uFF0C\u53EF\u968F\u65F6\u67E5\u770B\u7248\u672C\u66F4\u65B0\u8BB0\u5F55\u548C\u4F7F\u7528\u624B\u518C",
          "\u63D2\u4EF6\u66F4\u65B0\u540E\u81EA\u52A8\u5F39\u51FA\u66F4\u65B0\u8BF4\u660E",
        ],
        fixes: [
          "\u4FEE\u590D\u5168\u6587\u9605\u8BFB\u987A\u5E8F\u6DF7\u4E71\uFF0C\u4F18\u5316\u6574\u4F53\u6392\u7248\u4F53\u9A8C",
          "\u4FEE\u590D\u7AE0\u8282\u6807\u9898\u548C\u6B63\u6587\u6BB5\u843D\u9519\u4F4D\u65AD\u5F00\u7684\u95EE\u9898",
          "\u4FEE\u590D\u56FE\u8868\u548C\u5BF9\u5E94\u56FE\u6CE8\u88AB\u5206\u5F00\u7684\u95EE\u9898",
          "\u4FEE\u590D\u9996\u9875\u6458\u8981\u533A\u5757\u6392\u5E8F\u5F02\u5E38",
          "\u4FEE\u590D\u5E76\u6392\u56FE\u7247\u672A\u80FD\u81EA\u52A8\u5408\u5E76\u7684\u95EE\u9898",
          "Dashboard \u73B0\u5728\u80FD\u6B63\u786E\u8BC6\u522B\u65B0\u7684\u5168\u6587\u6587\u4EF6\u4F4D\u7F6E",
        ],
        recommended_actions: [
          "\u65E7\u7248 OCR \u5168\u6587\u53EF\u80FD\u5B58\u5728\u9605\u8BFB\u987A\u5E8F\u95EE\u9898\uFF0C\u5EFA\u8BAE\u5BF9\u91CD\u8981\u8BBA\u6587\u6267\u884C\u4E00\u6B21 Redo OCR",
          "\u6253\u5F00\u5168\u6587\u8BF7\u76F4\u63A5\u4F7F\u7528 Dashboard \u7684\u300C\u6253\u5F00\u5168\u6587\u300D\u6309\u94AE",
        ],
      },
    ],
  };
});
var nn = {};
Dr(nn, { default: () => ft });
module.exports = Fr(nn);
var J = require("obsidian"),
  Z = z(require("fs")),
  Ie = z(require("path")),
  Ne = require("child_process");
var Se = "paperforge-status",
  He = "paperforge",
  jt =
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path><line x1="8" y1="7" x2="16" y2="7"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>',
  ie = [
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
    {
      id: "paperforge-ocr-redo",
      title: "Redo OCR",
      desc: "Re-run OCR for papers marked ocr_redo: true",
      icon: "\u21BA",
      cmd: "ocr",
      args: ["redo"],
      okMsg: "OCR redo started",
    },
  ],
  Ve = {
    vault_path: "",
    frozen_skills: {},
    language: "",
    paddleocr_api_key: "",
    zotero_data_dir: "",
    agent_platform: "opencode",
    python_path: "",
    features: { memory_layer: !0, vector_db: !1 },
    vector_db_api_key: "",
    vector_db_api_base: "",
    vector_db_api_model: "text-embedding-3-small",
    system_dir: "",
    resources_dir: "",
    literature_dir: "",
    base_dir: "",
    capabilityState: {},
    last_seen_version: "",
    _migrated_keys: [],
    _migration_warnings: [],
    _paddleocr_configured: !1,
    _vector_db_configured: !1,
    _setup_complete: !1,
  };
function $t(d, l) {
  if (!l || !l.note_path) return l;
  let e = d.vault.getAbstractFileByPath(l.note_path);
  if (!e) return l;
  let t = d.metadataCache.getFileCache(e),
    r = t && t.frontmatter;
  if (!r) return l;
  let n = { ...l };
  for (let s of [
    "do_ocr",
    "analyze",
    "ocr_status",
    "ocr_redo",
    "deep_reading_status",
  ])
    Object.prototype.hasOwnProperty.call(r, s) && (n[s] = r[s]);
  return n;
}
function gt(d, l) {
  return d && { ...d, ...l };
}
var tt = 2,
  je = ["installation", "library", "ocr", "memory", "maintenance", "help"],
  Mr = new Set([
    "checking",
    "ready",
    "not_enabled",
    "setup_required",
    "action_required",
    "detection_failed",
  ]),
  Nt = new Set([
    "unknown",
    "unavailable",
    "missing_input",
    "needs_action",
    "limited",
    "ready",
  ]),
  Lr = new Set(["unknown", "ok", "warning", "error"]),
  Ht = new Set(["idle", "running"]),
  Or = new Set(["safe", "destructive", "irreversible"]);
function Vt(d) {
  if (!d || typeof d != "object" || Array.isArray(d)) return !1;
  let l = d;
  return !(
    typeof l.action_id != "string" ||
    !l.action_id ||
    typeof l.verb != "string" ||
    typeof l.label != "string" ||
    typeof l.availability != "string" ||
    typeof l.safety_class != "string" ||
    !Or.has(l.safety_class) ||
    !Array.isArray(l.preservation_facts) ||
    !Array.isArray(l.replacement_facts) ||
    typeof l.interruptible != "boolean" ||
    typeof l.confirmation_required != "boolean" ||
    (l.confirmation_prompt !== null &&
      typeof l.confirmation_prompt != "string") ||
    typeof l.command != "string" ||
    typeof l.scope != "string" ||
    typeof l.scope_count != "number"
  );
}
function $e(d) {
  return {
    action_id: d + ".probe",
    verb: "probe",
    label: "Retry",
    availability: "available",
    safety_class: "safe",
    preservation_facts: [],
    replacement_facts: [],
    interruptible: !0,
    confirmation_required: !1,
    confirmation_prompt: null,
    command: "probe " + d,
    scope: d,
    scope_count: 1,
  };
}
function zt() {
  return {
    action_id: "foundation.setup",
    verb: "setup",
    label: "Open Setup Wizard",
    availability: "available",
    safety_class: "safe",
    preservation_facts: [],
    replacement_facts: [],
    interruptible: !0,
    confirmation_required: !1,
    confirmation_prompt: null,
    command: "setup",
    scope: "installation",
    scope_count: 1,
  };
}
function mt(d, l) {
  if (!d || typeof d != "object") return !1;
  let e = d;
  if (
    e.schema_version !== tt ||
    typeof e.module != "string" ||
    !e.module ||
    !je.includes(e.module) ||
    (l !== void 0 && e.module !== l) ||
    typeof e.capability_state != "string" ||
    !Nt.has(e.capability_state) ||
    typeof e.activity_state != "string" ||
    !Ht.has(e.activity_state) ||
    typeof e.user_state != "string" ||
    !Mr.has(e.user_state) ||
    typeof e.capability_kind != "string" ||
    typeof e.maintenance_eligible != "boolean" ||
    typeof e.user_visible_failure != "boolean" ||
    (e.user_impact !== null && typeof e.user_impact != "string") ||
    (e.activity_label !== null && typeof e.activity_label != "string")
  )
    return !1;
  if (e.activity_progress !== null) {
    if (typeof e.activity_progress != "object") return !1;
    let n = e.activity_progress;
    if (typeof n.current != "number" || typeof n.total != "number") return !1;
  }
  if (!Array.isArray(e.notices) || !e.reason || typeof e.reason != "object")
    return !1;
  let t = e.reason;
  if (
    typeof t.code != "string" ||
    typeof t.text != "string" ||
    !e.action ||
    typeof e.action != "object"
  )
    return !1;
  let r = e.action;
  if (
    (r.primary !== null && !Vt(r.primary)) ||
    typeof e.updated_at != "string" ||
    !e.updated_at ||
    typeof e.ttl_seconds != "number"
  )
    return !1;
  if (e.module === "maintenance") {
    if (r.primary !== null || !Array.isArray(e.items)) return !1;
    for (let n of e.items) {
      if (!n || typeof n != "object") return !1;
      let s = n,
        a = ["installation", "library", "ocr", "memory", "help"];
      if (
        typeof s.capability_state != "string" ||
        !Nt.has(s.capability_state) ||
        typeof s.severity != "string" ||
        !Lr.has(s.severity) ||
        typeof s.activity_state != "string" ||
        !Ht.has(s.activity_state) ||
        (s.activity_label !== null && typeof s.activity_label != "string")
      )
        return !1;
      if (s.activity_progress !== null) {
        if (typeof s.activity_progress != "object") return !1;
        let i = s.activity_progress;
        if (typeof i.current != "number" || typeof i.total != "number")
          return !1;
      }
      if (
        typeof s.reason_code != "string" ||
        !s.reason_code ||
        typeof s.reason_text != "string" ||
        (s.action !== null && !Vt(s.action))
      )
        return !1;
    }
  }
  return !0;
}
function oe(d) {
  return {
    schema_version: tt,
    module: d,
    capability_state: "unknown",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    severity: "unknown",
    reason: { code: d + ".no_probe", text: d + " has not been probed yet." },
    action: { primary: d === "maintenance" ? null : $e(d) },
    notices: [],
    user_state: "detection_failed",
    capability_kind: "required",
    maintenance_eligible: !1,
    user_visible_failure: !1,
    user_impact: null,
    updated_at: new Date(0).toISOString(),
    ttl_seconds: 0,
  };
}
function yt(d) {
  return {
    schema_version: tt,
    module: d,
    capability_state: "unknown",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    severity: "unknown",
    reason: {
      code: d + ".stale",
      text: "Cached probe data for " + d + " is stale.",
    },
    action: { primary: d === "maintenance" ? null : $e(d) },
    notices: [],
    user_state: "detection_failed",
    capability_kind: "required",
    maintenance_eligible: !1,
    user_visible_failure: !1,
    user_impact: null,
    updated_at: new Date(0).toISOString(),
    ttl_seconds: 0,
  };
}
function Ae(d) {
  return {
    schema_version: tt,
    module: d,
    capability_state: "unknown",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    severity: "unknown",
    reason: {
      code: d + ".invalid_response",
      text: "Probe response for " + d + " was invalid.",
    },
    action: { primary: d === "maintenance" ? null : $e(d) },
    notices: [],
    user_state: "detection_failed",
    capability_kind: "required",
    maintenance_eligible: !1,
    user_visible_failure: !1,
    user_impact: null,
    updated_at: new Date(0).toISOString(),
    ttl_seconds: 0,
  };
}
function bt(d) {
  if (d.activity_state === "running") return !1;
  if (d.ttl_seconds <= 0) return !0;
  let l = new Date(d.updated_at).getTime();
  return isNaN(l) ? !0 : Date.now() - l > d.ttl_seconds * 1e3;
}
function ze(d) {
  return d.capability_state === "ready" && d.action.primary === null;
}
function Ke(d) {
  var r, n, s;
  let l = (r = d.action) == null ? void 0 : r.primary,
    e = (n = l == null ? void 0 : l.verb) != null ? n : "probe",
    t = (s = l == null ? void 0 : l.label) != null ? s : e;
  return e === "setup" || e === "set_config" || e === "update"
    ? { kind: "setup", verb: e, label: t }
    : e === "probe"
      ? { kind: "probe", verb: e, label: t }
      : { kind: "action", verb: e, label: t };
}
function Kt(d, l) {
  let e = {};
  for (let t of l) {
    let r = d[t];
    if (!r || typeof r != "object") {
      e[t] = oe(t);
      continue;
    }
    if (!mt(r, t)) {
      e[t] = Ae(t);
      continue;
    }
    if (bt(r)) {
      e[t] = yt(t);
      continue;
    }
    e[t] = r;
  }
  return e;
}
var vt = {
    en: {
      action_running: "Running ",
      api_key_missing: "Missing",
      api_key_set: "Entered",
      btn_install: "Open Setup Wizard",
      btn_install_desc:
        "Check whether the environment is ready, then open the step-by-step setup wizard",
      btn_reconfig: "Reconfigure",
      btn_reconfig_desc:
        "Open the setup wizard again to change directories, platform, or API keys",
      btn_validate: "Validate",
      check_bbt_fail: "Not detected",
      check_bbt_ok: "Installed",
      check_python_fail: "Not found",
      check_python_ok: "Ready",
      check_zotero_fail: "Not detected",
      check_zotero_ok: "Found",
      complete_export_path: "Save Better BibTeX JSON exports into:",
      complete_next: "Recommended next steps",
      complete_step1: "Open Dashboard",
      complete_step1_desc:
        'Press Ctrl+P and run "PaperForge: Open Main Panel", or click the PaperForge icon in the left sidebar.',
      complete_step2: "Sync Literature",
      complete_step2_desc:
        "In the main panel, click Sync Library to bring papers from Zotero into Obsidian and generate notes.",
      complete_step3: "Run OCR",
      complete_step3_desc:
        "In the Obsidian Base view, mark do_ocr:true on papers, then run OCR in the main panel.",
      complete_step4: "Configure Better BibTeX Auto-export",
      complete_step4_desc:
        'In Zotero, right-click the library or collection you want to sync -> Export -> Better BibTeX JSON -> enable "Keep updated".',
      complete_summary: "Saved Configuration",
      complete_title: "Setup Complete",
      copied: "Copied!",
      copy_pf_deep_cmd: "Copy /pf-deep Command",
      dashboard_drift_warning:
        "PaperForge CLI (v{0}) differs from plugin (v{1}). Open Settings \u2192 Runtime Health to sync.",
      deep_reading_not_found: "Deep reading file not found",
      desc: "Obsidian + Zotero literature pipeline. Sync papers, generate notes, run OCR, and read deeply in one place.",
      dir_base: "Base Dir",
      dir_index: "Index Dir",
      dir_notes: "Notes Dir",
      dir_resources: "Resource Dir",
      dir_system: "System Dir",
      dir_vault: "Vault Path",
      error_copied: "Copied!",
      error_copy_diagnostic: "Copy diagnostic",
      feat_agent_platform: "Agent Platform",
      feat_agent_platform_desc:
        "Select which agent platform to manage skills for.",
      feat_api_base_url: "API Base URL",
      feat_api_base_url_desc:
        "Custom OpenAI-compatible API endpoint. Leave empty for default.",
      feat_api_model: "API Model",
      feat_api_model_desc: "Embedding model name for this endpoint.",
      feat_build_btn: "Build",
      feat_build_complete: "Vector build complete.",
      feat_build_failed: "Build failed. See terminal output.",
      feat_building: "Building...",
      feat_cache_remove_failed: "Failed: {0}",
      feat_cache_removed: "Model cache removed.",
      feat_checking: "Checking...",
      feat_checking_btn: "Checking...",
      feat_deps_checking: "Checking dependencies...",
      feat_deps_missing:
        "Dependencies not installed. Required: chromadb, openai.",
      feat_enter_key: "Enter a valid OpenAI API key.",
      feat_install_btn: "Install",
      feat_install_deps: "Install Dependencies",
      feat_install_deps_desc: "pip install chromadb openai (~35MB).",
      feat_install_done: "Dependencies installed. Building vectors...",
      feat_install_failed: "Install failed: ",
      feat_installing: "Installing...",
      feat_installing_pkgs: "Installing {pkgs}...",
      feat_key_rejected: "API key rejected.",
      feat_memory_desc:
        "The Memory Layer is the core data engine of PaperForge, powered by SQLite. It integrates literature metadata (papers, assets, aliases, reading events), provides FTS5 metadata search across titles, abstracts, authors, domains, and collections, and powers agent-context and paper-status. Always active \u2014 no toggle needed.",
      feat_memory_rebuild_btn: "Rebuild",
      feat_memory_rebuild_done: "Memory DB rebuilt.",
      feat_memory_rebuild_failed: "Rebuild failed.",
      feat_memory_rebuilding: "Rebuilding...",
      feat_model_changed_warn:
        "Model changed ({0} -> {1}). Existing vectors are incompatible \u2014 rebuild required.",
      feat_network_error: "Network error: ",
      feat_no_python: "No Python found. Check Installation tab.",
      feat_not_cached: "Not cached",
      feat_openai_key: "OpenAI API Key",
      feat_openai_key_desc:
        "Used for API embedding calls. Model is defined below.",
      feat_output_copied: "Output copied to clipboard.",
      feat_rebuild_btn: "Rebuild",
      feat_rebuild_vectors: "Rebuild Vectors",
      feat_rebuild_vectors_changed:
        "Model changed \u2014 rebuild to update all vectors.",
      feat_rebuild_vectors_desc:
        "Rebuild all OCR fulltext vectors. Required after model or mode change.",
      feat_removing: "Removing...",
      feat_retry_btn: "Retry",
      feat_skills_desc:
        "Manage and enable/disable agent skills installed in your vault. Each row corresponds to a SKILL.md file \u2014 toggle off to prevent the agent from auto-invoking that skill.",
      feat_skills_system:
        "System Skills ship with PaperForge and are updated alongside PaperForge.",
      feat_skills_user:
        "User Skills are custom skills you install from community or create yourself.",
      feat_uninstall_btn: "Uninstall",
      feat_valid_key: "API key valid.",
      feat_vector_config_label: "Vector Settings",
      feat_vector_corrupted:
        "Vector index corrupted \u2014 needs force rebuild.",
      feat_vector_desc:
        "Vector Database enables semantic search across OCR-extracted fulltext via API embedding. Documents are split into chunks, embedded via OpenAI-compatible API, and stored in ChromaDB.",
      feat_vector_enable: "Enable Vector Retrieval",
      feat_vector_enable_desc:
        "Semantic search across OCR fulltext. Requires: pip install openai chromadb (~35MB).",
      feat_vector_rebuild_force_btn: "Force Rebuild",
      feat_verify: "Verify",
      feat_verify_btn: "Verify",
      field_paddleocr: "PaddleOCR API Key",
      field_python_custom: "Custom Path",
      field_python_interp: "Python Interpreter",
      field_zotero_data: "Zotero Data Dir",
      field_zotero_placeholder:
        "Required. Path to Zotero data directory for PDF attachment resolution.",
      guide_ocr: "Run OCR",
      guide_ocr_desc:
        "In the main panel, click Run OCR to extract full text and figures from PDFs for later reading and analysis.",
      guide_open: "Open Main Panel",
      guide_open_desc:
        'Press Ctrl+P and run "PaperForge: Open Main Panel", or click the PaperForge icon in the left sidebar.',
      guide_sync: "Sync Literature",
      guide_sync_desc:
        "After Better BibTeX JSON export is configured, click Sync Library to import papers from Zotero into Obsidian and generate notes automatically.",
      header_title: "PaperForge",
      install_bootstrapping:
        "PaperForge Python package not found. Installing automatically...",
      install_btn: "Start Install",
      install_btn_retry: "Retry",
      install_btn_running: "Installing...",
      install_complete: "Installation complete!",
      install_failed: "Installation failed: ",
      install_validating: "Validating setup...",
      jump_to_deep_reading: "Open Deep Reading",
      label_agent: "Agent Platform",
      nav_close: "Close",
      nav_next: "Next",
      nav_prev: "Back",
      not_set: "Not entered",
      notice_check_fail: "Missing: ",
      notice_python_missing:
        "Python was not detected. Install Python 3.11+ and add it to PATH.",
      ocr_privacy_title: "OCR Privacy Notice",
      ocr_privacy_warning:
        "OCR will upload PDFs to the PaddleOCR API. Do not upload sensitive or confidential documents.",
      ocr_queue_add: "Add to OCR Queue",
      ocr_queue_added: "Added to OCR queue",
      ocr_queue_remove: "Remove from OCR Queue",
      ocr_queue_removed: "Removed from OCR queue",
      ocr_understand: "I understand, continue",
      optional_later: "(can be set later in Settings)",
      orphan_delete_failed: "Prune failed",
      orphan_delete_selected: "Delete {count} selected",
      orphan_deleted: "Deleted {count} orphan workspace(s)",
      orphan_desc: "These papers are no longer in your Zotero library.",
      orphan_deselect_all: "Deselect all",
      orphan_explain: "Removed from Zotero. Workspace files remain on disk.",
      orphan_keep_all: "Keep all",
      orphan_none_selected: "No papers selected for deletion",
      orphan_select_all: "Select all",
      orphan_title: "Found {count} orphan paper(s)",
      panel_actions: "Quick Actions",
      prep_bbt: "Better BibTeX",
      prep_bbt_desc: "In Zotero: Tools -> Add-ons -> install Better BibTeX.",
      prep_export: "Better BibTeX Auto-export",
      prep_export_desc:
        'In Zotero, right-click the collection you want to sync -> Export Collection -> BetterBibTeX JSON -> enable "Keep updated" -> save the JSON file into the exports folder shown below. Obsidian Base views will use the JSON filename as the Base name:',
      prep_export_path_label: "Save the exported JSON file into this folder:",
      prep_key: "PaddleOCR Key",
      prep_key_desc:
        "Get your API key from https://aistudio.baidu.com/paddleocr",
      prep_python: "Python 3.11+",
      prep_python_desc:
        "Python must be available from the command line. If you are not sure, click below to auto-detect.",
      prep_zotero: "Zotero Desktop",
      prep_zotero_desc: "Install Zotero from https://www.zotero.org",
      run_in_agent: "Run in {0}",
      runtime_health: "Runtime Health",
      runtime_health_checking: "Checking...",
      runtime_health_desc:
        "Check whether the installed paperforge Python package matches the plugin version and whether the deployed skill contract is current.",
      runtime_health_match: "Match",
      runtime_health_mismatch: "Mismatch",
      runtime_health_package_ver: "Python package v{0}",
      runtime_health_plugin_ver: "Plugin v{0}",
      runtime_health_sync: "Sync Runtime",
      runtime_health_sync_done: "Runtime synced to v{0}",
      runtime_health_sync_fail: "Sync failed: {0}",
      runtime_health_syncing: "Syncing...",
      section_config: "Current Configuration",
      section_guide: "How To Use",
      section_prep: "Preparation",
      section_prep_desc:
        "Before first use, finish these 4 preparation items. Better BibTeX auto-export is configured after setup:",
      setup_done: "PaperForge environment is ready",
      setup_pending:
        "Not installed yet. Finish the preparation items below, then open the wizard.",
      tab_overview: "Overview",
      tab_modules: "Module Detail",
      tab_help: "Help",
      tab_setup: "Installation",
      tab_features: "Features",
      tab_maintenance: "Maintenance",
      validate_base: "Base directory is required",
      validate_fail: "Please complete the required fields below",
      validate_index: "Index directory is required",
      validate_key: "PaddleOCR API key (optional, needed for OCR)",
      validate_notes: "Notes directory is required",
      validate_resources: "Resources directory is required",
      validate_system: "System directory is required",
      validate_vault: "Vault path is required",
      validate_zotero:
        "Zotero data directory (optional, needed for PDF linking)",
      wizard_agent_hint:
        "Choose the AI agent platform you use most often. PaperForge will place the matching command and skill files in the correct location.",
      wizard_dir_hint:
        "PaperForge stores user-facing literature data under the resources directory. These folders will live there:",
      wizard_dir_sub_hint: "Resolved folder preview based on the names below:",
      wizard_intro:
        "This wizard walks you through the full setup. In most cases, the default values are fine to keep.",
      wizard_keys_hint:
        "Enter your PaddleOCR API key below. If you want PaperForge to auto-locate Zotero PDFs, you can also fill in the Zotero data directory.",
      wizard_preview:
        "After installation, system files stay at the vault root while literature data stays under the resources directory.",
      wizard_safety:
        "Safety: if the selected folders already contain files, setup preserves existing files and only creates missing PaperForge folders and files.",
      wizard_step1: "Overview",
      wizard_step2: "Directory Setup",
      wizard_step3: "Platform & Keys",
      wizard_step4: "Install",
      wizard_step5: "Done",
      wizard_skip_ocr_desc:
        "OCR will not be available until you configure a valid PaddleOCR API key. You can continue setup now and configure it later in Settings.",
      wizard_skip_ocr_continue: "Continue without OCR key",
      wizard_skip_ocr_back: "Back to configure",
      wizard_api_hint_skip:
        "OCR key is optional \u2014 you may skip it and configure later.",
      wizard_sys_hint:
        "These folders live at the vault root, outside the resources directory:",
      wizard_title: "PaperForge Setup Wizard",
      ocr_maint_no_action: "No Action Needed",
      ocr_maint_rebuild: "Rebuild Recommended",
      ocr_maint_failed: "OCR Failed",
      ocr_maint_limited: "Result Limited",
      ocr_maint_needs_attention: "Needs Attention",
      ocr_maint_limitations: "Result Limitations",
      ocr_maint_hero_ok: "OCR looks usable overall.",
      ocr_maint_hero_warn:
        "OCR needs attention: {rebuild} rebuild recommended, {failed} failed.",
      ocr_maint_hero_note:
        "This page only promotes issues where maintenance is likely to help. Some papers may have limitations that maintenance will not improve.",
      ocr_maint_limitations_intro:
        "These papers look less certain, but PaperForge does not currently have a high-confidence maintenance action to recommend.",
      ocr_maint_all_papers: "All Papers",
      ocr_maint_rebuild_btn: "Rebuild results",
      ocr_maint_redo_btn: "Rerun OCR",
      ocr_maint_redo_confirm:
        "Rerun OCR for {n} paper(s)? Existing derived OCR artifacts will be replaced.",
      maintenance_group_retry: "Needs Retry",
      maintenance_group_rebuild: "Can Rebuild",
      maintenance_group_legacy: "Upgrade Available (Optional)",
      maintenance_btn_retry: "Retry",
      maintenance_btn_rebuild: "Rebuild",
      maintenance_btn_upgrade: "Upgrade",
      maintenance_refresh_spinning: "Updating\u2026",
      maintenance_all_good: "\u2705 All good \u2014 no action needed",
      maintenance_n_pending: "{n} need attention",
      maintenance_filter_all: "All",
      maintenance_filter_recommended: "Recommended",
      maintenance_batch_rebuild: "\u25B6 Rebuild selected",
      maintenance_batch_redo: "\u25B6 Full OCR redo selected",
      maintenance_stop: "Stop",
      maintenance_batch_complete:
        "Batch operation complete \u2014 {n} papers processed.",
      maintenance_progress_label: "{current}/{total} papers",
      version_panel_title: "Version History",
      version_panel_back: "Back",
      version_filter_placeholder: "Filter papers...",
      version_papers_count: "{n} papers",
      version_current: "current",
      version_restore_btn: "Restore",
      version_compare_btn: "Compare",
      version_restore_selected: "Restore selected",
      version_clear_old: "Clear old versions (free {size})",
      version_no_backups: "No version history available",
      version_restore_confirm: "Restore {label} for {paper}?",
      version_restore_done: "Restored {label}",
      version_compare_title: "{vA} vs {vB}",
      version_compare_paragraphs: "{n} paragraphs changed",
      version_error_read: "Cannot read version data",
      retrieval_search_placeholder: "Search papers... (@ for deep search)",
      retrieval_search_placeholder_deep: "Search paper content...",
      retrieval_search_idle_hint: "Type a keyword or @ to search paper content",
      retrieval_searching_metadata: "Searching metadata...",
      retrieval_searching_deep: "Deep searching...",
      retrieval_search_cancel: "Cancel",
      retrieval_results_count: "{n} result(s)",
      retrieval_empty: "No matching papers found.",
      retrieval_empty_tips: "Try broader terms or use @ deep search.",
      retrieval_vectors_not_built: "Vector index not built",
      retrieval_vectors_not_built_desc:
        "Build vectors to enable @ deep search with semantic matching.",
      retrieval_open_vector_settings: "Open Vector Settings",
      retrieval_backend_unavailable: "Search backend unavailable",
      retrieval_backend_unavailable_desc:
        "The Python CLI search backend is not responding correctly.",
      retrieval_run_doctor: "Run Doctor",
      retrieval_retry: "Retry",
      retrieval_timeout_title: "Search timed out",
      retrieval_timeout_desc:
        "The search took too long. Try a more specific query.",
      retrieval_model_changed: "Model changed",
      retrieval_model_changed_desc:
        "The embedding model has changed since vectors were built. Rebuild to use deep search.",
      retrieval_rebuild_vectors: "Rebuild Vectors",
      retrieval_build_idle: "Vector database ready",
      retrieval_build_ready: "{n} vector(s) built",
      retrieval_build_stopping: "Stopping...",
      retrieval_build_stopped: "Build stopped ({n}/{t} papers)",
      retrieval_build_failed: "Build failed",
      retrieval_build_stale: "Vectors are stale \u2014 rebuild recommended",
      retrieval_build_deps_missing:
        "Dependencies missing. Install chromadb and openai.",
      retrieval_build_runtime_mismatch: "Python runtime version mismatch.",
      retrieval_stop: "Stop",
      retrieval_no_python: "Python not found",
      retrieval_internal_error: "An internal error occurred",
      retrieval_force_rebuild: "Force Rebuild",
      retrieval_rebuild_warning:
        "Rebuild will replace {n} existing chunk(s). Continue?",
      md_select_installation: "Installation",
      md_select_library: "Library",
      md_select_ocr: "OCR",
      md_select_memory: "Memory",
      installation_detail_heading: "Installation Details",
      btn_back_to_overview: "\u2190 Back to Overview",
      agent_integration_section: "Agent Integration",
      module_detail_open_installation: "Open Installation",
      module_detail_open_help: "Help & Docs",
      module_detail_open_maintenance: "Maintenance",
      module_detail_open_library: "Open Library",
      module_detail_open_ocr: "Open OCR",
      module_detail_open_memory: "Open Memory",
      action_unknown_pair: "Unknown action: {verb}",
      ocr_stop_batch: "Stop OCR batch",
      runtime_not_available: "No Python runtime available",
      md_unavailable_module: "Not available yet",
      library_detail_heading: "Library Details",
      ocr_detail_heading: "OCR Details",
      memory_detail_heading: "Memory Details",
      managed_runtime_status: "Runtime Status",
      managed_runtime_install: "Install Runtime",
      managed_runtime_repair: "Repair Runtime",
      managed_runtime_rollback: "Rollback",
      managed_runtime_update: "Update Runtime",
      managed_runtime_check_status: "Check Status",
      managed_runtime_refresh: "Refresh Status",
      managed_runtime_manual_setup: "Manual Setup",
      managed_runtime_stop: "Stop",
      managed_runtime_unknown_state: "Unknown",
      managed_runtime_ok_state: "Ready",
      managed_runtime_not_installed: "Not Installed",
      managed_runtime_needs_repair: "Needs Repair",
      managed_runtime_unavailable: "Unavailable",
      managed_runtime_last_verified: "Last verified: {time}",
      managed_runtime_running: "Runtime operation in progress...",
      managed_runtime_action_complete: "Runtime operation completed.",
      managed_runtime_action_failed: "Runtime operation failed: {error}",
      managed_runtime_action_cancelled: "Runtime operation cancelled.",
      cc_summary_ok: "All systems ready",
      cc_summary_core_ok:
        "Core environment ready; {n} modules pending detection",
      cc_summary_attention: "Some modules need attention",
      cc_summary_ok_body:
        "PaperForge environment is fully operational. Installation and documentation are verified.",
      cc_summary_core_ok_body:
        "Installation and Help modules are active. Library, OCR, Memory, and Maintenance will show live status once their backends are connected.",
      cc_summary_attention_body:
        "One or more core modules require your attention to function properly.",
      cc_badge_ok: "Ready",
      cc_badge_pending: "Pending",
      cc_badge_setup: "Setup needed",
      cc_badge_attention: "Needs attention",
      cc_diagnostic_toggle: "Details",
      cc_n_ready: "{n} ready",
      cc_n_pending: "{n} pending",
      cc_title: "System Status",
      cc_desc:
        "Real-time status of PaperForge core modules. Modules with a pending action need your attention.",
      cc_zone_attention: "Needs Attention",
      cc_zone_modules: "All Modules",
      cc_module_installation: "Foundation",
      cc_module_help: "Help & Docs",
      cc_module_library: "Library",
      cc_module_ocr: "OCR Engine",
      cc_module_memory: "Smart Retrieval",
      cc_module_maintenance: "Maintenance",
      cc_state_ready: "Ready",
      cc_state_limited: "Limited",
      cc_state_unavailable: "Unavailable",
      cc_state_unknown: "Unknown",
      cc_severity_ok: "OK",
      cc_severity_unknown: "Unknown",
      cc_severity_warning: "Warning",
      cc_severity_error: "Error",
      cc_state_missing_input: "Missing Input",
      cc_state_needs_action: "Needs Action",
      cc_action_setup: "Open Setup Wizard",
      cc_action_probe: "Check",
      cc_action_set_config: "Set Config",
      cc_action_update: "Update",
      cc_reason_installation_ready:
        "PaperForge environment is set up correctly.",
      cc_reason_config_missing:
        "Configuration file is missing. Run setup to create one.",
      cc_reason_config_corrupt:
        "Configuration file is corrupt. Run setup to repair.",
      cc_reason_python_version_unsupported:
        "Python version is not supported. Install Python 3.11+.",
      cc_reason_help_ready: "Help documentation is available.",
      cc_reason_docs_missing: "Help documentation is not yet installed.",
      cc_reason_placeholder:
        "Detection pending \u2014 will show live status once connected.",
      cc_reason_library_ready: "Library is synced and indexed.",
      cc_reason_library_config_missing:
        "Configuration not found \u2014 run setup to configure library.",
      cc_reason_library_config_corrupt:
        "Configuration file is corrupt \u2014 library cannot proceed.",
      cc_reason_library_zotero_missing:
        "Zotero data directory is not configured.",
      cc_reason_library_zotero_not_found:
        "Zotero data directory path does not exist.",
      cc_reason_library_index_missing:
        "Library index has not been built yet \u2014 run sync.",
      cc_reason_library_index_stale:
        "Library index is stale \u2014 sync to refresh.",
      cc_reason_ocr_ready: "OCR pipeline is configured and functional.",
      cc_reason_ocr_config_missing:
        "Configuration not found \u2014 run setup to configure OCR.",
      cc_reason_ocr_config_corrupt:
        "Configuration file is corrupt \u2014 OCR cannot proceed.",
      cc_reason_ocr_api_key_missing:
        "No OCR API key configured \u2014 add one in setup.",
      cc_reason_ocr_artifacts_missing:
        "No OCR output found \u2014 run OCR on papers.",
      cc_reason_memory_ready: "Memory database is healthy and indexed.",
      cc_reason_memory_db_missing:
        "Memory database not built \u2014 run memory build.",
      cc_reason_memory_db_corrupt:
        "Memory database is corrupted \u2014 restore from backup.",
      cc_reason_memory_index_stale:
        "Memory index needs rebuild to match current library.",
      cc_diag_module: "Module",
      cc_diag_state: "State",
      cc_diag_severity: "Severity",
      cc_diag_activity: "Activity",
      cc_diag_reason: "Reason",
      cc_diag_ttl: "TTL",
      cc_diag_updated: "Updated",
      cc_reason_no_probe: "{module} has not been probed yet.",
      cc_reason_stale: "Cached probe data for {module} is stale.",
      cc_reason_invalid_response: "Probe response for {module} was invalid.",
      activity_syncing: "Syncing...",
      activity_ocr_running: "Processing OCR... {pct}%",
      activity_ocr_running_noprogress: "Processing OCR...",
      cc_action_unknown_verb: "Unknown backend action: {verb}",
      cc_action_investigate: "Running diagnostics...",
      cc_reason_probing: "Checking {module} status...",
      cc_notice_placeholder:
        "{module} module probing is not yet available; it will be added in a future update.",
      cc_notice_refreshed: "Module status refreshed.",
      cc_notice_refresh_failed: "Failed to refresh module status.",
      cc_activity_idle: "Idle",
      cc_activity_running: "Running",
      maintenance_inbox_title: "Maintenance Inbox",
      maintenance_checking: "Checking maintenance status\u2026",
      maintenance_all_clear:
        "All modules are ready \u2014 no maintenance needed.",
      maintenance_n_pending_inbox: "{n} module(s) need attention",
      maintenance_dismiss: "Dismiss",
      maintenance_undismiss: "Show",
      maintenance_ocr_section: "OCR Maintenance",
      maintenance_action_result_success:
        "Action complete \u2014 module is now ready.",
      maintenance_action_result_failure:
        "Action failed \u2014 module still needs attention.",
      maintenance_confirm_redo_title: "Confirm Rerun",
      maintenance_confirm_redo_body:
        "This will delete and re-run OCR for the selected papers. Existing derived artifacts will be replaced.",
      maintenance_confirm_restore_title: "Confirm Restore",
      maintenance_confirm_restore_body:
        "This will restore the memory database from backup. Current data will be replaced.",
      maintenance_confirm_ok: "Proceed",
      maintenance_confirm_cancel: "Cancel",
      maintenance_issue_draft_title: "OCR Issue Draft",
      maintenance_issue_draft_preview:
        "Review the issue draft below before opening GitHub.",
      maintenance_issue_draft_included: "Included",
      maintenance_issue_draft_redacted: "Redacted",
      maintenance_issue_draft_open_github: "Open GitHub Issue",
      maintenance_issue_draft_edit: "Edit Draft",
    },
    zh: {
      action_running: "\u6B63\u5728\u6267\u884C ",
      api_key_missing: "\u672A\u914D\u7F6E \u2717",
      api_key_set: "\u5DF2\u914D\u7F6E \u2713",
      btn_install: "\u6253\u5F00\u5B89\u88C5\u5411\u5BFC",
      btn_install_desc:
        "\u81EA\u52A8\u68C0\u6D4B Python + \u524D\u7F6E\u73AF\u5883\uFF0C\u901A\u8FC7\u540E\u6253\u5F00\u5206\u6B65\u5B89\u88C5\u5411\u5BFC",
      btn_reconfig: "\u91CD\u65B0\u914D\u7F6E",
      btn_reconfig_desc:
        "\u91CD\u65B0\u8FD0\u884C\u5B89\u88C5\u5411\u5BFC\uFF0C\u4FEE\u6539\u76EE\u5F55\u6216\u5BC6\u94A5\u914D\u7F6E",
      btn_validate: "\u9A8C\u8BC1",
      check_bbt_fail: "\u672A\u68C0\u6D4B\u5230",
      check_bbt_ok: "\u5DF2\u5B89\u88C5",
      check_python_fail: "\u672A\u5B89\u88C5",
      check_python_ok: "\u5DF2\u5C31\u7EEA",
      check_zotero_fail: "\u672A\u68C0\u6D4B\u5230",
      check_zotero_ok: "\u5DF2\u5B89\u88C5",
      complete_next: "\u4E0B\u4E00\u6B65\u64CD\u4F5C",
      complete_step1: "\u6253\u5F00 PaperForge Dashboard",
      complete_step1_desc:
        "Ctrl+P \u2192 \u8F93\u5165 PaperForge: Open Dashboard\uFF0C\u6216\u70B9\u5DE6\u4FA7\u4E66\u672C\u56FE\u6807",
      complete_step2: "\u540C\u6B65\u6587\u732E",
      complete_step2_desc:
        "Dashboard \u4E2D\u70B9 Sync Library\uFF0C\u4ECE Zotero \u62C9\u53D6\u6587\u732E\u751F\u6210\u7B14\u8BB0",
      complete_step3: "\u8FD0\u884C OCR",
      complete_step3_desc:
        "Dashboard \u4E2D\u70B9 Run OCR\uFF0C\u63D0\u53D6 PDF \u5168\u6587\u4E0E\u56FE\u8868",
      complete_step4: "\u914D\u7F6E BBT \u81EA\u52A8\u5BFC\u51FA",
      complete_summary: "\u5F53\u524D\u5B8C\u6574\u914D\u7F6E",
      complete_title: "\u2713 PaperForge \u5B89\u88C5\u5B8C\u6210",
      copied: "\u5DF2\u590D\u5236\uFF01",
      copy_pf_deep_cmd: "\u590D\u5236 /pf-deep \u547D\u4EE4",
      dashboard_drift_warning:
        '\u63D2\u4EF6\u7248\u672C\u4E0E Python \u8FD0\u884C\u65F6\u7248\u672C\u4E0D\u5339\u914D\u3002\u8BF7\u5728\u8BBE\u7F6E\u4E2D\u70B9\u51FB"\u540C\u6B65\u8FD0\u884C\u65F6"\u3002',
      deep_reading_not_found: "\u7CBE\u8BFB\u6587\u4EF6\u672A\u627E\u5230",
      desc: "Obsidian + Zotero \u6587\u732E\u7BA1\u7406\u6D41\u6C34\u7EBF\u3002\u81EA\u52A8\u540C\u6B65\u6587\u732E\u3001\u751F\u6210\u7B14\u8BB0\u3001OCR \u63D0\u53D6\u5168\u6587\uFF0C\u4E00\u7AD9\u5F0F\u6587\u732E\u7CBE\u8BFB\u5DE5\u4F5C\u6D41\u3002",
      dir_base: "Base \u76EE\u5F55",
      dir_index: "\u7D22\u5F15\u76EE\u5F55",
      dir_notes: "\u6B63\u6587\u76EE\u5F55",
      dir_resources: "\u8D44\u6E90\u76EE\u5F55",
      dir_system: "\u7CFB\u7EDF\u76EE\u5F55",
      dir_vault: "Vault \u8DEF\u5F84",
      error_copied: "\u5DF2\u590D\u5236\uFF01",
      error_copy_diagnostic: "\u590D\u5236\u8BCA\u65AD\u4FE1\u606F",
      feat_agent_platform: "Agent \u5E73\u53F0",
      feat_agent_platform_desc:
        "\u9009\u62E9\u8981\u7BA1\u7406\u7684 Agent \u5E73\u53F0\u3002",
      feat_api_base_url: "API \u5730\u5740",
      feat_api_base_url_desc:
        "\u81EA\u5B9A\u4E49 OpenAI \u517C\u5BB9 API \u7AEF\u70B9\u3002\u7559\u7A7A\u4F7F\u7528\u9ED8\u8BA4\u5730\u5740\u3002",
      feat_api_model: "API \u6A21\u578B",
      feat_api_model_desc:
        "\u8BE5\u7AEF\u70B9\u4F7F\u7528\u7684\u5D4C\u5165\u6A21\u578B\u540D\u79F0\u3002",
      feat_build_btn: "\u6784\u5EFA",
      feat_build_complete: "\u5411\u91CF\u6784\u5EFA\u5B8C\u6210\u3002",
      feat_build_failed:
        "\u6784\u5EFA\u5931\u8D25\u3002\u8BF7\u67E5\u770B\u7EC8\u7AEF\u8F93\u51FA\u3002",
      feat_building: "\u6784\u5EFA\u4E2D\u2026",
      feat_cache_remove_failed: "\u5931\u8D25\uFF1A{0}",
      feat_cache_removed: "\u6A21\u578B\u7F13\u5B58\u5DF2\u6E05\u9664\u3002",
      feat_checking: "\u68C0\u6D4B\u4E2D\u2026",
      feat_checking_btn: "\u68C0\u6D4B\u4E2D\u2026",
      feat_deps_checking: "\u6B63\u5728\u68C0\u6D4B\u4F9D\u8D56\u2026",
      feat_deps_missing:
        "\u4F9D\u8D56\u672A\u5B89\u88C5\u3002\u9700\u8981\uFF1Achromadb, openai\u3002",
      feat_enter_key:
        "\u8BF7\u8F93\u5165\u6709\u6548\u7684 OpenAI API Key\u3002",
      feat_install_btn: "\u5B89\u88C5",
      feat_install_deps: "\u5B89\u88C5\u4F9D\u8D56",
      feat_install_done:
        "\u4F9D\u8D56\u5DF2\u5B89\u88C5\u3002\u6B63\u5728\u6784\u5EFA\u5411\u91CF\u2026",
      feat_install_failed: "\u5B89\u88C5\u5931\u8D25\uFF1A",
      feat_installing: "\u5B89\u88C5\u4E2D\u2026",
      feat_installing_pkgs: "\u6B63\u5728\u5B89\u88C5 {pkgs}...",
      feat_key_rejected: "API Key \u88AB\u62D2\u7EDD\u3002",
      feat_memory_desc:
        "\u8BB0\u5FC6\u5C42\u662F PaperForge \u7684\u6838\u5FC3\u6570\u636E\u5F15\u64CE\uFF0C\u57FA\u4E8E SQLite \u6784\u5EFA\u3002\u5B83\u6574\u5408\u4E86\u6587\u732E\u5143\u6570\u636E\uFF08\u8BBA\u6587\u3001\u8D44\u6E90\u6587\u4EF6\u3001\u522B\u540D\u3001\u9605\u8BFB\u4E8B\u4EF6\uFF09\uFF0C\u652F\u6301 FTS5 \u5143\u6570\u636E\u68C0\u7D22\uFF08\u6807\u9898\u3001\u6458\u8981\u3001\u4F5C\u8005\u3001domain\u3001collection\uFF09\uFF0C\u5E76\u4E3A agent-context \u548C paper-status \u547D\u4EE4\u63D0\u4F9B\u6570\u636E\u652F\u6491\u3002\u59CB\u7EC8\u8FD0\u884C\uFF0C\u65E0\u9700\u624B\u52A8\u5F00\u542F\u3002",
      feat_memory_rebuild_btn: "\u91CD\u5EFA\u6570\u636E\u5E93",
      feat_memory_rebuild_done:
        "\u8BB0\u5FC6\u6570\u636E\u5E93\u91CD\u5EFA\u5B8C\u6210\u3002",
      feat_memory_rebuild_failed: "\u91CD\u5EFA\u5931\u8D25\u3002",
      feat_memory_rebuilding: "\u91CD\u5EFA\u4E2D\u2026",
      feat_model: "\u6A21\u578B",
      feat_model_changed_warn:
        "\u6A21\u578B\u5DF2\u66F4\u6362\uFF08{0} -> {1}\uFF09\u3002\u5DF2\u6709\u5411\u91CF\u4E0D\u517C\u5BB9\u2014\u2014\u9700\u8981\u91CD\u5EFA\u3002",
      feat_network_error: "\u7F51\u7EDC\u9519\u8BEF\uFF1A",
      feat_no_python:
        "\u672A\u627E\u5230 Python\u3002\u8BF7\u67E5\u770B\u5B89\u88C5\u6807\u7B7E\u9875\u3002",
      feat_not_cached: "\u672A\u7F13\u5B58",
      feat_openai_key: "OpenAI API Key",
      feat_openai_key_desc:
        "\u7528\u4E8E API \u5D4C\u5165\u8C03\u7528\uFF0C\u6A21\u578B\u5728\u4E0B\u65B9\u5B9A\u4E49\u3002",
      feat_output_copied:
        "\u8F93\u51FA\u5DF2\u590D\u5236\u5230\u526A\u8D34\u677F\u3002",
      feat_rebuild_btn: "\u91CD\u5EFA",
      feat_rebuild_vectors: "\u91CD\u5EFA\u5411\u91CF",
      feat_rebuild_vectors_changed:
        "\u6A21\u578B\u5DF2\u66F4\u6362 \u2014 \u9700\u8981\u91CD\u5EFA\u5411\u91CF\u3002",
      feat_rebuild_vectors_desc:
        "\u91CD\u5EFA\u6240\u6709 OCR \u5168\u6587\u5411\u91CF\u3002\u66F4\u6362\u6A21\u578B\u6216\u6A21\u5F0F\u540E\u9700\u8981\u91CD\u5EFA\u3002",
      feat_removing: "\u5220\u9664\u4E2D\u2026",
      feat_retry_btn: "\u91CD\u8BD5",
      feat_skills_desc:
        "\u7BA1\u7406 Vault \u4E2D\u5DF2\u5B89\u88C5\u7684 Agent \u6280\u80FD\u3002\u6BCF\u884C\u5BF9\u5E94\u4E00\u4E2A SKILL.md \u6587\u4EF6\uFF0C\u5173\u95ED\u5F00\u5173\u53EF\u963B\u6B62 Agent \u81EA\u52A8\u8C03\u7528\u8BE5\u6280\u80FD\u3002",
      feat_skills_system:
        "\u7CFB\u7EDF\u6280\u80FD\u968F PaperForge \u4E00\u540C\u53D1\u5E03\uFF0C\u4F1A\u8DDF\u968F PaperForge \u7248\u672C\u66F4\u65B0\u3002",
      feat_skills_user:
        "\u7528\u6237\u6280\u80FD\u662F\u4F60\u81EA\u884C\u5B89\u88C5\u6216\u521B\u5EFA\u7684\u81EA\u5B9A\u4E49\u6280\u80FD\u3002",
      feat_uninstall_btn: "\u5378\u8F7D",
      feat_valid_key: "API Key \u6709\u6548\u3002",
      feat_vector_config_label: "\u5411\u91CF\u5E93\u914D\u7F6E",
      feat_vector_corrupted:
        "\u5411\u91CF\u7D22\u5F15\u5DF2\u635F\u574F \u2014 \u9700\u8981\u5F3A\u5236\u91CD\u5EFA\u3002",
      feat_vector_desc:
        "\u5411\u91CF\u6570\u636E\u5E93\u901A\u8FC7\u5D4C\u5165\u6A21\u578B\u5B9E\u73B0 OCR \u5168\u6587\u7684\u8BED\u4E49\u641C\u7D22\u3002\u6587\u6863\u88AB\u5207\u5206\u4E3A\u6587\u672C\u5757\uFF08chunk\uFF09\uFF0C\u7F16\u7801\u4E3A\u5411\u91CF\u5B58\u5165 ChromaDB\u3002\u652F\u6301\u672C\u5730\u6A21\u578B\uFF08\u514D\u8D39\uFF0CCPU \u8FD0\u884C\uFF09\u6216 OpenAI API\uFF08\u4ED8\u8D39\uFF0C\u66F4\u5FEB\u901F\uFF09\u3002",
      feat_vector_enable: "\u542F\u7528\u5411\u91CF\u68C0\u7D22",
      feat_vector_enable_desc:
        "\u5BF9 OCR \u5168\u6587\u8FDB\u884C\u8BED\u4E49\u641C\u7D22\u3002\u9700\u5B89\u88C5: pip install chromadb sentence-transformers openai (~500MB)\u3002",
      feat_vector_rebuild_force_btn: "\u5F3A\u5236\u91CD\u5EFA",
      feat_verify: "\u9A8C\u8BC1",
      feat_verify_btn: "\u9A8C\u8BC1",
      field_paddleocr: "PaddleOCR API \u5BC6\u94A5",
      field_python_custom: "\u81EA\u5B9A\u4E49 Python \u8DEF\u5F84",
      field_python_interp: "\u5F53\u524D Python \u89E3\u91CA\u5668",
      field_zotero_data: "Zotero \u6570\u636E\u76EE\u5F55",
      field_zotero_placeholder:
        "\u53EF\u9009\uFF0C\u7528\u4E8E\u81EA\u52A8\u68C0\u6D4B PDF",
      guide_ocr: "\u8FD0\u884C OCR",
      guide_ocr_desc:
        "Dashboard \u4E2D\u70B9 Run OCR\uFF0C\u63D0\u53D6 PDF \u5168\u6587\u4E0E\u56FE\u8868",
      guide_open: "\u6253\u5F00 Dashboard",
      guide_open_desc:
        "Ctrl+P \u2192 \u8F93\u5165 PaperForge: Open Dashboard\uFF0C\u6216\u70B9\u5DE6\u4FA7\u4E66\u672C\u56FE\u6807",
      guide_sync: "\u540C\u6B65\u6587\u732E",
      guide_sync_desc:
        "Dashboard \u4E2D\u70B9 Sync Library\uFF0C\u4ECE Zotero \u62C9\u53D6\u6587\u732E\u751F\u6210\u7B14\u8BB0",
      header_title: "PaperForge",
      install_bootstrapping:
        "\u672A\u68C0\u6D4B\u5230 PaperForge Python \u5305\uFF0C\u6B63\u5728\u81EA\u52A8\u5B89\u88C5\u2026",
      install_btn: "\u5F00\u59CB\u5B89\u88C5",
      install_btn_retry: "\u91CD\u8BD5",
      install_btn_running: "\u6B63\u5728\u5B89\u88C5...",
      install_complete: "\u2713 \u5B89\u88C5\u5B8C\u6210\uFF01",
      install_failed: "\u2717 \u5B89\u88C5\u5931\u8D25\uFF1A",
      install_validating:
        "\u6B63\u5728\u6821\u9A8C\u5B89\u88C5\u73AF\u5883\u2026",
      jump_to_deep_reading: "\u8DF3\u8F6C\u5230\u7CBE\u8BFB",
      label_agent: "Agent \u5E73\u53F0",
      nav_close: "\u5173\u95ED",
      nav_next: "\u4E0B\u4E00\u6B65 \u2192",
      nav_prev: "\u2190 \u4E0A\u4E00\u6B65",
      no_pending_ocr: "\u6240\u6709 OCR \u4EFB\u52A1\u5DF2\u5B8C\u6210",
      not_set: "\u672A\u8BBE\u7F6E",
      notice_python_missing:
        "Python \u672A\u68C0\u6D4B\u5230\uFF0C\u8BF7\u5148\u5B89\u88C5 Python 3.11+ \u5E76\u52A0\u5165 PATH",
      ocr_privacy_title: "OCR \u9690\u79C1\u63D0\u793A",
      ocr_privacy_warning:
        "OCR \u4F1A\u5C06 PDF \u4E0A\u4F20\u5230 PaddleOCR API \u8FDB\u884C\u5904\u7406\u3002\u8BF7\u4E0D\u8981\u4E0A\u4F20\u5305\u542B\u654F\u611F\u4FE1\u606F\u6216\u65E0\u6CD5\u5916\u4F20\u7684\u6587\u732E\u3002",
      ocr_queue_add: "\u52A0\u5165 OCR \u961F\u5217",
      ocr_queue_added: "\u5DF2\u52A0\u5165 OCR \u961F\u5217",
      ocr_queue_remove: "\u79FB\u51FA OCR \u961F\u5217",
      ocr_queue_removed: "\u5DF2\u79FB\u51FA OCR \u961F\u5217",
      ocr_understand: "\u6211\u4E86\u89E3\uFF0C\u7EE7\u7EED",
      optional_later:
        "\uFF08\u7A0D\u540E\u53EF\u5728\u8BBE\u7F6E\u4E2D\u8865\u5145\uFF09",
      orphan_delete_failed: "\u6E05\u7406\u5931\u8D25",
      orphan_delete_selected: "\u5220\u9664 {count} \u7BC7",
      orphan_deleted:
        "\u5DF2\u5220\u9664 {count} \u7BC7\u6B8B\u7559\u6587\u732E",
      orphan_desc:
        "\u8FD9\u4E9B\u6587\u732E\u5DF2\u4ECE Zotero \u4E2D\u79FB\u9664\u3002",
      orphan_deselect_all: "\u53D6\u6D88\u5168\u9009",
      orphan_explain:
        "\u5DF2\u4ECE Zotero \u4E2D\u79FB\u9664\u3002\u5DE5\u4F5C\u533A\u6587\u4EF6\u4ECD\u4FDD\u7559\u5728\u78C1\u76D8\u4E0A\u3002",
      orphan_keep_all: "\u4FDD\u7559\u5168\u90E8",
      orphan_none_selected: "\u672A\u9009\u62E9\u4EFB\u4F55\u6587\u732E",
      orphan_select_all: "\u5168\u9009",
      orphan_title: "\u53D1\u73B0 {count} \u7BC7\u6B8B\u7559\u6587\u732E",
      panel_actions: "\u5FEB\u6377\u64CD\u4F5C",
      prep_bbt: "Better BibTeX",
      prep_bbt_desc:
        "Zotero \u2192 \u5DE5\u5177 \u2192 \u63D2\u4EF6 \u2192 \u5B89\u88C5 Better BibTeX",
      prep_export: "BBT \u81EA\u52A8\u5BFC\u51FA",
      prep_export_desc:
        "\u53F3\u952E\u6587\u732E\u5B50\u5206\u7C7B \u2192 \u5BFC\u51FA\u5206\u7C7B \u2192 BetterBibTeX JSON \u2192 \u52FE\u9009\u4FDD\u6301\u66F4\u65B0 \u2192 \u5BFC\u51FA\u5230\uFF08JSON \u6587\u4EF6\u540D\u5373\u4E3A Base \u540D\uFF09\uFF1A",
      prep_key: "PaddleOCR Key",
      prep_python: "Python 3.11+",
      prep_python_desc:
        "\u786E\u4FDD Python \u53EF\u547D\u4EE4\u884C\u8C03\u7528\u3002\u70B9\u51FB\u4E0B\u65B9\u6309\u94AE\u81EA\u52A8\u68C0\u6D4B\u3002",
      prep_zotero: "Zotero \u684C\u9762\u7248",
      prep_zotero_desc: "\u5B89\u88C5 Zotero (https://www.zotero.org)",
      run_in_agent: "\u5728 {0} \u4E2D\u8FD0\u884C",
      runtime_health: "\u8FD0\u884C\u65F6\u72B6\u6001",
      runtime_health_checking: "\u6B63\u5728\u68C0\u6D4B\u2026",
      runtime_health_desc:
        "\u68C0\u67E5\u63D2\u4EF6\u4E0E Python \u8FD0\u884C\u65F6\u7248\u672C\u7684\u5339\u914D\u60C5\u51B5\uFF0C\u5E76\u786E\u8BA4\u5DF2\u90E8\u7F72\u7684 skill contract \u662F\u5426\u4E3A\u5F53\u524D\u7248\u672C\u3002",
      runtime_health_match: "\u5339\u914D",
      runtime_health_mismatch: "\u4E0D\u5339\u914D",
      runtime_health_package_ver: "Python \u5305 v{0}",
      runtime_health_plugin_ver: "\u63D2\u4EF6 v{0}",
      runtime_health_sync: "\u540C\u6B65\u8FD0\u884C\u65F6",
      runtime_health_sync_done:
        "\u8FD0\u884C\u65F6\u5DF2\u540C\u6B65\u81F3 v{0}",
      runtime_health_sync_fail:
        "\u8FD0\u884C\u65F6\u540C\u6B65\u5931\u8D25\uFF1A{0}",
      runtime_health_syncing: "\u6B63\u5728\u540C\u6B65\u2026",
      section_config: "\u5F53\u524D\u914D\u7F6E",
      section_guide: "\u64CD\u4F5C\u65B9\u5F0F",
      section_prep: "\u5B89\u88C5\u51C6\u5907",
      section_prep_desc:
        "\u9996\u6B21\u4F7F\u7528\u524D\uFF0C\u8BF7\u4F9D\u6B21\u5B8C\u6210\u4EE5\u4E0B\u51C6\u5907\uFF1A",
      setup_done:
        "\u2713 PaperForge \u73AF\u5883\u5DF2\u914D\u7F6E\u5B8C\u6210",
      setup_pending:
        "\u5C1A\u672A\u5B89\u88C5\uFF0C\u5B8C\u6210\u5B89\u88C5\u51C6\u5907\u540E\u70B9\u51FB\u5B89\u88C5\u5411\u5BFC",
      tab_overview: "\u6982\u89C8",
      tab_modules: "\u6A21\u5757\u8BE6\u60C5",
      tab_help: "\u5E2E\u52A9",
      tab_features: "\u529F\u80FD",
      tab_setup: "\u5B89\u88C5",
      tab_maintenance: "\u7EF4\u62A4",
      validate_base: "Base \u76EE\u5F55\u672A\u586B\u5199",
      validate_fail: "\u914D\u7F6E\u9A8C\u8BC1\u5931\u8D25",
      validate_index: "\u7D22\u5F15\u76EE\u5F55\u672A\u586B\u5199",
      validate_key: "PaddleOCR API \u5BC6\u94A5\u672A\u586B\u5199",
      validate_notes: "\u6B63\u6587\u76EE\u5F55\u672A\u586B\u5199",
      validate_resources: "\u8D44\u6E90\u76EE\u5F55\u672A\u586B\u5199",
      validate_system: "\u7CFB\u7EDF\u76EE\u5F55\u672A\u586B\u5199",
      validate_vault: "Vault \u8DEF\u5F84\u672A\u586B\u5199",
      validate_zotero:
        "Zotero \u6570\u636E\u76EE\u5F55\u4E3A\u5FC5\u586B\u9879",
      wizard_agent_hint:
        "\u9009\u62E9\u4F60\u4F7F\u7528\u7684 AI Agent \u5E73\u53F0\uFF0C\u5B89\u88C5\u65F6\u5C06\u6309\u5BF9\u5E94\u683C\u5F0F\u90E8\u7F72\u6280\u80FD\u6587\u4EF6\uFF1A",
      wizard_dir_hint:
        "\u8D44\u6E90\u76EE\u5F55\u662F\u6587\u732E\u6570\u636E\u7684\u7EDF\u4E00\u6839\u76EE\u5F55\uFF0C\u4EE5\u4E0B\u5B50\u76EE\u5F55\u5C06\u521B\u5EFA\u5728\u5176\u5185\u90E8\uFF1A",
      wizard_dir_sub_hint:
        "\u8D44\u6E90\u76EE\u5F55\u5185\u7684\u4E24\u4E2A\u5B50\u76EE\u5F55\uFF1A",
      wizard_intro:
        "\u672C\u5411\u5BFC\u5C06\u5F15\u5BFC\u60A8\u5B8C\u6210 PaperForge \u73AF\u5883\u7684\u5B8C\u6574\u914D\u7F6E\u3002\u5B89\u88C5\u8FC7\u7A0B\u4F1A\u81EA\u52A8\u521B\u5EFA\u6240\u6709\u76EE\u5F55\u7ED3\u6784\uFF0C\u65E0\u9700\u624B\u52A8\u64CD\u4F5C\u3002",
      wizard_keys_hint:
        "\u4EE5\u4E0B\u4E3A API \u5BC6\u94A5\u4E0E Zotero \u914D\u7F6E\uFF1A",
      wizard_preview:
        "\u7CFB\u7EDF\u6587\u4EF6\u548C Agent \u914D\u7F6E\u4F4D\u4E8E Vault \u6839\u76EE\u5F55\u4E0B\u3002\u6587\u732E\u6570\u636E\uFF08\u6B63\u6587\u3001\u7D22\u5F15\uFF09\u7EDF\u4E00\u5B58\u653E\u5728\u8D44\u6E90\u76EE\u5F55\u5185\u3002\u5B89\u88C5\u540E\u4ECD\u53EF\u5728\u8BBE\u7F6E\u4E2D\u4FEE\u6539\u3002",
      wizard_safety:
        "\u5B89\u5168\u8BF4\u660E\uFF1A\u5982\u679C\u4F60\u9009\u62E9\u7684\u76EE\u5F55\u91CC\u5DF2\u7ECF\u6709\u6587\u4EF6\uFF0C\u5B89\u88C5\u5411\u5BFC\u4F1A\u4FDD\u7559\u5DF2\u6709\u5185\u5BB9\uFF0C\u53EA\u8865\u5145\u7F3A\u5931\u7684 PaperForge \u6587\u4EF6\u548C\u76EE\u5F55\u3002",
      wizard_step1: "\u6982\u89C8",
      wizard_step2: "\u76EE\u5F55",
      wizard_step3: "Agent",
      wizard_step4: "\u5B89\u88C5",
      wizard_step5: "\u5B8C\u6210",
      wizard_skip_ocr_desc:
        "OCR \u529F\u80FD\u5728\u914D\u7F6E\u6709\u6548\u7684 PaddleOCR API \u5BC6\u94A5\u4E4B\u524D\u4E0D\u53EF\u7528\u3002\u60A8\u53EF\u4EE5\u7EE7\u7EED\u5B8C\u6210\u8BBE\u7F6E\uFF0C\u7A0D\u540E\u5728\u8BBE\u7F6E\u4E2D\u914D\u7F6E\u3002",
      wizard_skip_ocr_continue:
        "\u7EE7\u7EED\uFF0C\u7A0D\u540E\u914D\u7F6E\u5BC6\u94A5",
      wizard_skip_ocr_back: "\u8FD4\u56DE\u914D\u7F6E",
      wizard_api_hint_skip:
        "OCR \u5BC6\u94A5\u4E3A\u9009\u586B\u9879 \u2014 \u53EF\u8DF3\u8FC7\uFF0C\u7A0D\u540E\u5728\u8BBE\u7F6E\u4E2D\u914D\u7F6E\u3002",
      wizard_sys_hint:
        "\u72EC\u7ACB\u4E8E\u8D44\u6E90\u76EE\u5F55\u7684\u7CFB\u7EDF\u6587\u4EF6\uFF1A",
      wizard_title: "PaperForge \u5B89\u88C5\u5411\u5BFC",
      ocr_maint_no_action: "\u65E0\u9700\u5904\u7406",
      ocr_maint_rebuild: "\u5EFA\u8BAE\u91CD\u5EFA",
      ocr_maint_failed: "OCR \u5931\u8D25",
      ocr_maint_limited: "\u7ED3\u679C\u4E00\u822C",
      ocr_maint_needs_attention: "\u9700\u8981\u5904\u7406",
      ocr_maint_limitations: "\u7ED3\u679C\u8BF4\u660E",
      ocr_maint_hero_ok: "OCR \u6574\u4F53\u6B63\u5E38\u3002",
      ocr_maint_hero_warn:
        "OCR \u9700\u8981\u5173\u6CE8\uFF1A{rebuild} \u7BC7\u5EFA\u8BAE\u91CD\u5EFA\uFF0C{failed} \u7BC7\u5904\u7406\u5931\u8D25\u3002",
      ocr_maint_hero_note:
        "\u672C\u9875\u53EA\u63D0\u793A\u7EF4\u62A4\u540E\u5927\u6982\u7387\u4F1A\u6539\u5584\u7684\u95EE\u9898\u3002\u90E8\u5206\u8BBA\u6587\u6548\u679C\u4E00\u822C\uFF0C\u7EF4\u62A4\u672A\u5FC5\u80FD\u6539\u5584\u3002",
      ocr_maint_limitations_intro:
        "\u8FD9\u7C7B\u8BBA\u6587\u901A\u5E38\u8868\u793A\u7248\u5F0F\u590D\u6742\u6216\u4FE1\u53F7\u504F\u5F31\uFF0CPaperForge \u76EE\u524D\u6CA1\u6709\u9AD8\u7F6E\u4FE1\u5EA6\u7684\u7EF4\u62A4\u5EFA\u8BAE\u3002",
      ocr_maint_all_papers: "\u5168\u90E8\u8BBA\u6587",
      ocr_maint_rebuild_btn: "\u91CD\u5EFA\u7ED3\u679C",
      ocr_maint_redo_btn: "\u91CD\u65B0 OCR",
      ocr_maint_redo_confirm:
        "\u786E\u8BA4\u91CD\u65B0 OCR {n} \u7BC7\u8BBA\u6587\uFF1F\u73B0\u6709\u7684\u6D3E\u751F OCR \u7ED3\u679C\u5C06\u88AB\u66FF\u6362\u3002",
      maintenance_group_retry: "\u9700\u8981\u91CD\u8BD5",
      maintenance_group_rebuild: "\u53EF\u91CD\u5EFA\u7ED3\u679C",
      maintenance_group_legacy:
        "\u53EF\u5347\u7EA7\u65E7\u7ED3\u679C\uFF08\u53EF\u9009\uFF09",
      maintenance_btn_retry: "\u91CD\u8BD5",
      maintenance_btn_rebuild: "\u91CD\u5EFA",
      maintenance_btn_upgrade: "\u5347\u7EA7",
      maintenance_refresh_spinning: "\u6B63\u5728\u66F4\u65B0\u2026",
      maintenance_all_good: "\u2705 \u5168\u90E8\u6B63\u5E38",
      maintenance_n_pending: "{n} \u7BC7\u9700\u8981\u5904\u7406",
      maintenance_filter_all: "\u5168\u90E8",
      maintenance_filter_recommended: "\u5EFA\u8BAE\u5904\u7406",
      maintenance_batch_rebuild: "\u25B6 \u91CD\u5EFA\u5DF2\u9009",
      maintenance_batch_redo: "\u25B6 \u5168\u90E8\u91CD\u8DD1 OCR",
      maintenance_stop: "\u505C\u6B62",
      maintenance_batch_complete:
        "\u6279\u91CF\u64CD\u4F5C\u5B8C\u6210 \u2014 \u5904\u7406\u4E86 {n} \u7BC7\u8BBA\u6587\u3002",
      maintenance_progress_label: "{current}/{total} \u7BC7",
      version_panel_title: "\u7248\u672C\u5386\u53F2",
      version_panel_back: "\u8FD4\u56DE",
      version_filter_placeholder: "\u641C\u7D22\u8BBA\u6587...",
      version_papers_count: "{n} \u7BC7\u8BBA\u6587",
      version_current: "\u5F53\u524D",
      version_restore_btn: "\u6062\u590D",
      version_compare_btn: "\u5BF9\u6BD4",
      version_restore_selected: "\u6062\u590D\u9009\u4E2D\u7248\u672C",
      version_clear_old: "\u6E05\u9664\u65E7\u7248\u672C (\u91CA\u653E {size})",
      version_no_backups:
        "\u6CA1\u6709\u53EF\u6062\u590D\u7684\u5386\u53F2\u7248\u672C",
      md_select_installation: "\u5B89\u88C5",
      md_select_library: "\u6587\u732E\u5E93",
      md_select_ocr: "OCR",
      md_select_memory: "\u8BB0\u5FC6\u5C42",
      installation_detail_heading: "\u5B89\u88C5\u8BE6\u60C5",
      btn_back_to_overview: "\u2190 \u8FD4\u56DE\u6982\u89C8",
      agent_integration_section: "Agent \u96C6\u6210",
      module_detail_open_installation: "\u6253\u5F00\u5B89\u88C5",
      module_detail_open_help: "\u5E2E\u52A9\u4E0E\u6587\u6863",
      module_detail_open_maintenance: "\u7EF4\u62A4",
      module_detail_open_library: "\u6253\u5F00\u6587\u732E\u5E93",
      module_detail_open_ocr: "\u6253\u5F00 OCR",
      module_detail_open_memory: "\u6253\u5F00\u8BB0\u5FC6",
      action_unknown_pair: "\u672A\u77E5\u64CD\u4F5C: {verb}",
      ocr_stop_batch: "\u505C\u6B62 OCR \u6279\u5904\u7406",
      runtime_not_available: "Python \u8FD0\u884C\u65F6\u4E0D\u53EF\u7528",
      md_unavailable_module: "\u6682\u4E0D\u53EF\u7528",
      library_detail_heading: "\u6587\u732E\u5E93\u8BE6\u60C5",
      ocr_detail_heading: "OCR \u8BE6\u60C5",
      memory_detail_heading: "\u8BB0\u5FC6\u5C42\u8BE6\u60C5",
      managed_runtime_status: "\u8FD0\u884C\u65F6\u72B6\u6001",
      managed_runtime_install: "\u5B89\u88C5\u8FD0\u884C\u65F6",
      managed_runtime_repair: "\u4FEE\u590D\u8FD0\u884C\u65F6",
      managed_runtime_rollback: "\u56DE\u6EDA",
      managed_runtime_update: "\u66F4\u65B0\u8FD0\u884C\u65F6",
      managed_runtime_check_status: "\u68C0\u67E5\u72B6\u6001",
      managed_runtime_refresh: "\u5237\u65B0\u72B6\u6001",
      managed_runtime_manual_setup: "\u624B\u52A8\u914D\u7F6E",
      managed_runtime_stop: "\u505C\u6B62",
      managed_runtime_unknown_state: "\u672A\u77E5",
      managed_runtime_ok_state: "\u5C31\u7EEA",
      managed_runtime_not_installed: "\u672A\u5B89\u88C5",
      managed_runtime_needs_repair: "\u9700\u8981\u4FEE\u590D",
      managed_runtime_unavailable: "\u4E0D\u53EF\u7528",
      managed_runtime_last_verified: "\u6700\u540E\u9A8C\u8BC1\uFF1A{time}",
      managed_runtime_running:
        "\u8FD0\u884C\u65F6\u64CD\u4F5C\u8FDB\u884C\u4E2D...",
      managed_runtime_action_complete:
        "\u8FD0\u884C\u65F6\u64CD\u4F5C\u5DF2\u5B8C\u6210\u3002",
      managed_runtime_action_cancelled:
        "\u8FD0\u884C\u65F6\u64CD\u4F5C\u5DF2\u53D6\u6D88\u3002",
      managed_runtime_action_failed:
        "\u8FD0\u884C\u65F6\u64CD\u4F5C\u5931\u8D25\uFF1A{error}",
      version_restore_confirm:
        "\u786E\u8BA4\u5C06 {paper} \u6062\u590D\u5230 {label}\uFF1F",
      version_restore_done: "\u5DF2\u6062\u590D\u5230 {label}",
      version_compare_title: "{vA} vs {vB}",
      version_compare_paragraphs: "{n} \u6BB5\u6709\u53D8\u5316",
      version_error_read: "\u65E0\u6CD5\u8BFB\u53D6\u7248\u672C\u6570\u636E",
      retrieval_search_placeholder:
        "\u641C\u7D22\u8BBA\u6587...\uFF08@ \u542F\u52A8\u6DF1\u5EA6\u641C\u7D22\uFF09",
      retrieval_search_placeholder_deep:
        "\u641C\u7D22\u8BBA\u6587\u5185\u5BB9...",
      retrieval_search_idle_hint:
        "\u8F93\u5165\u5173\u952E\u8BCD\u641C\u7D22\u8BBA\u6587\uFF0C\u6216\u4EE5 @ \u5F00\u5934\u641C\u7D22\u8BBA\u6587\u5185\u5BB9",
      retrieval_searching_metadata: "\u641C\u7D22\u5143\u6570\u636E\u4E2D...",
      retrieval_searching_deep: "\u6DF1\u5EA6\u641C\u7D22\u4E2D...",
      retrieval_search_cancel: "\u53D6\u6D88",
      retrieval_results_count: "{n} \u4E2A\u7ED3\u679C",
      retrieval_empty: "\u672A\u627E\u5230\u5339\u914D\u7684\u8BBA\u6587\u3002",
      retrieval_empty_tips:
        "\u5C1D\u8BD5\u66F4\u5BBD\u6CDB\u7684\u5173\u952E\u8BCD\uFF0C\u6216\u4F7F\u7528 @ \u6DF1\u5EA6\u641C\u7D22\u8BBA\u6587\u5185\u5BB9\u3002",
      retrieval_vectors_not_built: "\u5411\u91CF\u7D22\u5F15\u672A\u6784\u5EFA",
      retrieval_vectors_not_built_desc:
        "\u6784\u5EFA\u5411\u91CF\u7D22\u5F15\u4EE5\u542F\u7528 @ \u6DF1\u5EA6\u8BED\u4E49\u641C\u7D22\u3002",
      retrieval_open_vector_settings: "\u6253\u5F00\u5411\u91CF\u8BBE\u7F6E",
      retrieval_backend_unavailable:
        "\u641C\u7D22\u540E\u7AEF\u4E0D\u53EF\u7528",
      retrieval_backend_unavailable_desc:
        "Python CLI \u641C\u7D22\u540E\u7AEF\u672A\u6B63\u5E38\u54CD\u5E94\u3002",
      retrieval_run_doctor: "\u8FD0\u884C\u8BCA\u65AD",
      retrieval_retry: "\u91CD\u8BD5",
      retrieval_timeout_title: "\u641C\u7D22\u8D85\u65F6",
      retrieval_timeout_desc:
        "\u641C\u7D22\u8017\u65F6\u8FC7\u957F\uFF0C\u8BF7\u5C1D\u8BD5\u66F4\u7CBE\u786E\u7684\u67E5\u8BE2\u3002",
      retrieval_model_changed: "\u6A21\u578B\u5DF2\u66F4\u6362",
      retrieval_model_changed_desc:
        "\u5D4C\u5165\u6A21\u578B\u5DF2\u66F4\u6362\uFF0C\u9700\u91CD\u5EFA\u5411\u91CF\u540E\u624D\u80FD\u4F7F\u7528\u6DF1\u5EA6\u641C\u7D22\u3002",
      retrieval_rebuild_vectors: "\u91CD\u5EFA\u5411\u91CF",
      retrieval_build_idle: "\u5411\u91CF\u6570\u636E\u5E93\u5C31\u7EEA",
      retrieval_build_ready: "\u5DF2\u6784\u5EFA {n} \u4E2A\u5411\u91CF",
      retrieval_build_stopping: "\u6B63\u5728\u505C\u6B62...",
      cc_summary_attention: "\u90E8\u5206\u6A21\u5757\u9700\u8981\u5173\u6CE8",
      cc_summary_ok_body:
        "PaperForge \u73AF\u5883\u5DF2\u5B8C\u5168\u5C31\u7EEA\u3002\u5B89\u88C5\u548C\u5E2E\u52A9\u6587\u6863\u5747\u6B63\u5E38\u53EF\u7528\u3002",
      cc_summary_core_ok_body:
        "\u5B89\u88C5\u548C\u5E2E\u52A9\u6A21\u5757\u5DF2\u53EF\u7528\u3002\u6587\u732E\u7D22\u5F15\u3001OCR\u3001\u8BB0\u5FC6\u5C42\u548C\u7EF4\u62A4\u6A21\u5757\u5C06\u5728\u540E\u7AEF\u63A5\u5165\u540E\u663E\u793A\u5B9E\u65F6\u72B6\u6001\u3002",
      cc_summary_attention_body:
        "\u4E00\u4E2A\u6216\u591A\u4E2A\u6838\u5FC3\u6A21\u5757\u9700\u8981\u60A8\u7684\u5173\u6CE8\u624D\u80FD\u6B63\u5E38\u8FD0\u884C\u3002",
      retrieval_build_stopped:
        "\u6784\u5EFA\u5DF2\u505C\u6B62\uFF08{n}/{t} \u7BC7\uFF09",
      retrieval_build_failed: "\u6784\u5EFA\u5931\u8D25",
      retrieval_build_stale:
        "\u5411\u91CF\u5DF2\u8FC7\u671F \u2014 \u5EFA\u8BAE\u91CD\u5EFA",
      retrieval_build_deps_missing:
        "\u4F9D\u8D56\u7F3A\u5931\u3002\u8BF7\u5B89\u88C5 chromadb \u548C openai\u3002",
      retrieval_build_runtime_mismatch:
        "Python \u8FD0\u884C\u65F6\u7248\u672C\u4E0D\u5339\u914D\u3002",
      retrieval_stop: "\u505C\u6B62",
      retrieval_no_python: "\u672A\u627E\u5230 Python",
      retrieval_internal_error: "\u53D1\u751F\u5185\u90E8\u9519\u8BEF",
      retrieval_force_rebuild: "\u5F3A\u5236\u91CD\u5EFA",
      retrieval_rebuild_warning:
        "\u91CD\u5EFA\u5C06\u66FF\u6362 {n} \u4E2A\u73B0\u6709\u6587\u672C\u5757\uFF0C\u662F\u5426\u7EE7\u7EED\uFF1F",
      cc_summary_ok: "\u5168\u90E8\u6B63\u5E38",
      cc_summary_core_ok:
        "\u6838\u5FC3\u73AF\u5883\u6B63\u5E38\uFF1B{n} \u4E2A\u6A21\u5757\u72B6\u6001\u68C0\u6D4B\u5F85\u63A5\u5165",
      cc_badge_ok: "\u5DF2\u5C31\u7EEA",
      cc_badge_pending: "\u5F85\u63A5\u5165",
      cc_badge_setup: "\u9700\u8981\u5B89\u88C5",
      cc_badge_attention: "\u9700\u8981\u6CE8\u610F",
      cc_diagnostic_toggle: "\u8BE6\u60C5",
      cc_n_ready: "{n} \u5DF2\u5C31\u7EEA",
      cc_n_pending: "{n} \u5F85\u63A5\u5165",
      cc_title: "\u7CFB\u7EDF\u72B6\u6001",
      cc_desc:
        "PaperForge \u6838\u5FC3\u6A21\u5757\u7684\u5B9E\u65F6\u72B6\u6001\u3002\u6709\u5F85\u5904\u7406\u64CD\u4F5C\u7684\u6A21\u5757\u9700\u8981\u60A8\u7684\u5173\u6CE8\u3002",
      cc_zone_attention: "\u9700\u8981\u5173\u6CE8",
      cc_zone_modules: "\u6240\u6709\u6A21\u5757",
      cc_module_installation: "\u5B89\u88C5",
      cc_module_help: "\u5E2E\u52A9\u4E0E\u6587\u6863",
      cc_module_library: "\u6587\u732E\u5E93",
      cc_module_ocr: "OCR \u5F15\u64CE",
      cc_module_memory: "\u667A\u80FD\u68C0\u7D22",
      cc_module_maintenance: "\u7EF4\u62A4",
      cc_state_ready: "\u5C31\u7EEA",
      cc_state_limited: "\u53D7\u9650",
      cc_state_unavailable: "\u4E0D\u53EF\u7528",
      cc_state_unknown: "\u672A\u77E5",
      cc_severity_ok: "\u6B63\u5E38",
      cc_severity_unknown: "\u672A\u77E5",
      cc_severity_warning: "\u8B66\u544A",
      cc_severity_error: "\u9519\u8BEF",
      cc_state_missing_input: "\u7F3A\u5C11\u8F93\u5165",
      cc_state_needs_action: "\u9700\u8981\u64CD\u4F5C",
      cc_action_setup: "\u6253\u5F00\u5B89\u88C5\u5411\u5BFC",
      cc_action_probe: "\u68C0\u6D4B",
      cc_action_set_config: "\u914D\u7F6E\u8BBE\u7F6E",
      cc_action_update: "\u66F4\u65B0",
      cc_reason_installation_ready:
        "PaperForge \u73AF\u5883\u5DF2\u6B63\u786E\u914D\u7F6E\u3002",
      cc_reason_config_missing:
        "\u914D\u7F6E\u6587\u4EF6\u7F3A\u5931\uFF0C\u8BF7\u8FD0\u884C\u5B89\u88C5\u5411\u5BFC\u3002",
      cc_reason_config_corrupt:
        "\u914D\u7F6E\u6587\u4EF6\u635F\u574F\uFF0C\u8BF7\u8FD0\u884C\u5B89\u88C5\u5411\u5BFC\u4FEE\u590D\u3002",
      cc_reason_python_version_unsupported:
        "Python \u7248\u672C\u4E0D\u53D7\u652F\u6301\uFF0C\u8BF7\u5B89\u88C5 Python 3.11+\u3002",
      cc_reason_help_ready: "\u5E2E\u52A9\u6587\u6863\u5DF2\u53EF\u7528\u3002",
      cc_reason_docs_missing:
        "\u5E2E\u52A9\u6587\u6863\u5C1A\u672A\u5B89\u88C5\u3002",
      cc_reason_placeholder:
        "\u72B6\u6001\u68C0\u6D4B\u5F85\u63A5\u5165\uFF0C\u63A5\u5165\u540E\u5C06\u663E\u793A\u5B9E\u65F6\u72B6\u6001\u3002",
      cc_diag_module: "\u6A21\u5757",
      cc_diag_state: "\u72B6\u6001",
      cc_diag_severity: "\u4E25\u91CD\u7A0B\u5EA6",
      cc_diag_activity: "\u6D3B\u52A8",
      cc_diag_reason: "\u539F\u56E0",
      cc_diag_ttl: "TTL",
      cc_diag_updated: "\u66F4\u65B0\u65F6\u95F4",
      cc_reason_no_probe: "{module} \u5C1A\u672A\u68C0\u6D4B\u3002",
      cc_reason_stale:
        "{module} \u7684\u68C0\u6D4B\u6570\u636E\u5DF2\u8FC7\u671F\u3002",
      cc_reason_invalid_response:
        "{module} \u7684\u68C0\u6D4B\u54CD\u5E94\u65E0\u6548\u3002",
      activity_syncing: "\u540C\u6B65\u4E2D...",
      activity_ocr_running: "\u6B63\u5728\u5904\u7406 OCR... {pct}%",
      activity_ocr_running_noprogress: "\u6B63\u5728\u5904\u7406 OCR...",
      cc_action_unknown_verb: "\u672A\u77E5\u540E\u7AEF\u64CD\u4F5C: {verb}",
      cc_action_investigate: "\u6B63\u5728\u8FD0\u884C\u8BCA\u65AD...",
      cc_reason_probing: "\u6B63\u5728\u68C0\u6D4B {module} \u72B6\u6001...",
      cc_notice_placeholder:
        "{module} \u6A21\u5757\u68C0\u6D4B\u529F\u80FD\u5C1A\u672A\u53EF\u7528\uFF0C\u5C06\u5728\u540E\u7EED\u7248\u672C\u4E2D\u6DFB\u52A0\u3002",
      cc_notice_refreshed: "\u6A21\u5757\u72B6\u6001\u5DF2\u5237\u65B0\u3002",
      cc_notice_refresh_failed:
        "\u6A21\u5757\u72B6\u6001\u5237\u65B0\u5931\u8D25\u3002",
      cc_activity_idle: "\u7A7A\u95F2",
      cc_activity_running: "\u8FD0\u884C\u4E2D",
      maintenance_inbox_title: "\u7EF4\u62A4\u6536\u4EF6\u7BB1",
      maintenance_checking:
        "\u6B63\u5728\u68C0\u6D4B\u7EF4\u62A4\u72B6\u6001\u2026",
      maintenance_all_clear:
        "\u6240\u6709\u6A21\u5757\u5DF2\u5C31\u7EEA \u2014 \u65E0\u9700\u7EF4\u62A4\u3002",
      maintenance_n_pending_inbox:
        "{n} \u4E2A\u6A21\u5757\u9700\u8981\u5173\u6CE8",
      maintenance_dismiss: "\u5FFD\u7565",
      maintenance_undismiss: "\u663E\u793A",
      maintenance_ocr_section: "OCR \u7EF4\u62A4",
      maintenance_action_result_success:
        "\u64CD\u4F5C\u5B8C\u6210 \u2014 \u6A21\u5757\u5DF2\u5C31\u7EEA\u3002",
      maintenance_action_result_failure:
        "\u64CD\u4F5C\u5931\u8D25 \u2014 \u6A21\u5757\u4ECD\u9700\u5173\u6CE8\u3002",
      maintenance_confirm_redo_title: "\u786E\u8BA4\u91CD\u65B0\u8FD0\u884C",
      maintenance_confirm_redo_body:
        "\u8FD9\u5C06\u5220\u9664\u5E76\u91CD\u65B0\u8FD0\u884C\u6240\u9009\u8BBA\u6587\u7684 OCR\u3002\u5DF2\u6709\u7684\u884D\u751F\u7ED3\u679C\u5C06\u88AB\u66FF\u6362\u3002",
      maintenance_confirm_restore_title: "\u786E\u8BA4\u6062\u590D",
      maintenance_confirm_restore_body:
        "\u8FD9\u5C06\u4ECE\u5907\u4EFD\u6062\u590D\u8BB0\u5FC6\u6570\u636E\u5E93\u3002\u5F53\u524D\u6570\u636E\u5C06\u88AB\u66FF\u6362\u3002",
      maintenance_confirm_ok: "\u7EE7\u7EED",
      maintenance_confirm_cancel: "\u53D6\u6D88",
      maintenance_issue_draft_title: "OCR \u95EE\u9898\u8349\u7A3F",
      maintenance_issue_draft_preview:
        "\u5728\u6253\u5F00 GitHub \u4E4B\u524D\uFF0C\u8BF7\u5BA1\u9605\u4EE5\u4E0B\u95EE\u9898\u8349\u7A3F\u3002",
      maintenance_issue_draft_included: "\u5DF2\u5305\u542B",
      maintenance_issue_draft_redacted: "\u5DF2\u8131\u654F",
      maintenance_issue_draft_open_github: "\u6253\u5F00 GitHub Issue",
      maintenance_issue_draft_edit: "\u7F16\u8F91\u8349\u7A3F",
    },
  },
  Et = null;
function Br(d) {
  try {
    let l = d.vault;
    if (typeof l.getConfig == "function") {
      let e = l.getConfig("language");
      if (e && String(e).startsWith("zh")) return "zh";
    }
  } catch (l) {}
  try {
    if (typeof localStorage != "undefined") {
      let l = localStorage.getItem("language");
      if (l && String(l).startsWith("zh")) return "zh";
    }
  } catch (l) {}
  return "en";
}
function Ut(d) {
  Et = Br(d) === "zh" ? vt.zh : vt.en;
}
function o(d) {
  return (Et && Et[d]) || vt.en[d] || d;
}
var A = require("obsidian"),
  G = z(require("fs")),
  te = z(require("path")),
  br = z(require("os")),
  ee = require("child_process");
var vr = z(xt());
var Nr = {
    checking: "pf-badge pf-badge--checking",
    ready: "pf-badge pf-badge--ready",
    not_enabled: "pf-badge pf-badge--not-enabled",
    setup_required: "pf-badge pf-badge--setup-required",
    action_required: "pf-badge pf-badge--action-required",
    detection_failed: "pf-badge pf-badge--detection-failed",
  },
  Hr = {
    checking: "Checking",
    ready: "Ready",
    not_enabled: "Not Enabled",
    setup_required: "Setup Required",
    action_required: "Action Required",
    detection_failed: "Detection Failed",
  };
function Ue(d, l, e) {
  return d.createEl("span", {
    cls: Nr[l],
    text: e != null ? e : Hr[l],
    attr: { role: "status" },
  });
}
function qe(d, l) {
  let e = d.createEl("div", { cls: "pf-activity-row" }),
    t = e.createEl("span", { cls: "pf-activity-label", text: l.label });
  if (l.progress && l.progress.total > 0) {
    let r = e.createEl("div", { cls: "pf-activity-bar" }),
      n = Math.round((l.progress.current / l.progress.total) * 100);
    (r.createEl("div", {
      cls: "pf-activity-bar-fill",
      attr: {
        style: `width: ${n}%`,
        role: "progressbar",
        "aria-valuenow": String(l.progress.current),
        "aria-valuemin": "1",
        "aria-valuemax": String(l.progress.total),
      },
    }),
      e.createEl("span", {
        cls: "pf-activity-count",
        text: `${l.progress.current}/${l.progress.total}`,
      }));
  } else
    e.createEl("span", { cls: "pf-activity-spinner" }).setAttr(
      "aria-label",
      "In progress"
    );
  if (
    (l.scope && e.createEl("span", { cls: "pf-activity-scope", text: l.scope }),
    l.stopLabel && l.onStop)
  ) {
    let r = e.createEl("button", {
      cls: "pf-activity-stop",
      text: l.stopLabel,
    });
    (r.addEventListener("click", l.onStop),
      r.addEventListener("keydown", (n) => {
        var s;
        (n.key === "Enter" || n.key === " ") &&
          (n.preventDefault(), (s = l.onStop) == null || s.call(l));
      }));
  }
  return e;
}
function le(d, l) {
  let e = d.createEl("button", {
    cls: "pf-action-btn",
    text: l.loading ? "\u2026" : l.label,
  });
  return (
    (l.disabled || l.loading) &&
      (e.setAttr("disabled", "true"),
      e.classList.add("pf-action-btn--disabled")),
    l.loading && e.classList.add("pf-action-btn--loading"),
    !l.disabled &&
      !l.loading &&
      (e.addEventListener("click", l.onClick),
      e.addEventListener("keydown", (t) => {
        (t.key === "Enter" || t.key === " ") &&
          (t.preventDefault(), l.onClick());
      })),
    e
  );
}
function rt(d, l) {
  let e = d.createEl("div", { cls: "pf-error-anatomy" });
  e.createEl("div", { cls: "pf-error-title", text: l.whatHappened });
  let t = e.createEl("div", { cls: "pf-error-impact" });
  (t.createEl("span", { cls: "pf-error-impact-label", text: "Impact: " }),
    t.createEl("span", { text: l.impact }),
    l.reasonCode &&
      e.createEl("div", { cls: "pf-error-code", text: l.reasonCode }));
  let r = e.createEl("div", { cls: "pf-error-next" });
  return (
    r.createEl("span", {
      cls: "pf-error-next-label",
      text: (l.nextLabel || "Next:") + " ",
    }),
    r.createEl("span", { text: l.nextStep }),
    l.onCopyDiagnostic &&
      e
        .createEl("button", {
          cls: "pf-error-copy-diagnostic",
          text: l.copyLabel || "Copy Diagnostic Information",
        })
        .addEventListener("click", l.onCopyDiagnostic),
    e
  );
}
function qt(d, l) {
  let e = d.createEl("div", { cls: "pf-config-summary" });
  for (let r of l.items) {
    let n = e.createEl("div", { cls: "pf-config-row" });
    n.createEl("span", { cls: "pf-config-label", text: r.label });
    let s = r.isCredential
      ? r.value
        ? l.configuredLabel || "Configured"
        : l.notConfiguredLabel || "Not configured"
      : r.value;
    n.createEl("span", {
      cls: `pf-config-value${r.isCredential ? (r.value ? " pf-config-value--ok" : " pf-config-value--muted") : ""}`,
      text: s,
    });
  }
  return (
    e
      .createEl("button", {
        cls: "pf-config-change-btn",
        text: l.onChangeLabel,
      })
      .addEventListener("click", l.onChange),
    e
  );
}
function Wt(d) {
  let l = [];
  (l.push("=== PaperForge Support Diagnostic ==="),
    l.push(`Time: ${new Date().toISOString()}`),
    l.push(`Plugin: ${d.pluginVersion}`),
    d.backendVersion && l.push(`Backend: ${d.backendVersion}`),
    l.push(""),
    l.push("--- Module Status ---"));
  for (let e of d.modules)
    (l.push(`${e.module}: ${e.userState}`),
      e.reasonCode && l.push(`  reason: ${e.reasonCode}`),
      e.actionId && l.push(`  action: ${e.actionId}`),
      e.lastSuccessAt && l.push(`  last-success: ${e.lastSuccessAt}`),
      e.errorExcerpt && l.push(`  error: ${e.errorExcerpt}`));
  return (
    l.push(""),
    l.push("=== End ==="),
    l.join(`
`)
  );
}
function Zt(d, l) {
  navigator.clipboard
    .writeText(d)
    .then(() => {
      l == null || l();
    })
    .catch((e) => {
      console.warn("[PaperForge] Failed to copy diagnostic:", e);
    });
}
function Gt(d) {
  return { envelope: d, capturedAt: new Date().toISOString() };
}
function Jt(d, l) {
  return !d || l.user_state === "ready"
    ? !0
    : !(l.user_state === "detection_failed" || d.user_state === "ready");
}
function Yt(d, l) {
  var t, r, n, s, a, i, c;
  let e = [];
  for (let [p, u] of Object.entries(d)) {
    let _ = l.get(p);
    e.push({
      module: p,
      userState: u.user_state,
      lastSuccessAt: (t = _ == null ? void 0 : _.capturedAt) != null ? t : null,
      reasonCode: (r = u.reason) == null ? void 0 : r.code,
      actionId:
        (s = (n = u.action) == null ? void 0 : n.primary) == null
          ? void 0
          : s.action_id,
      errorExcerpt:
        (c =
          (i = (a = u.reason) == null ? void 0 : a.text) == null
            ? void 0
            : i.slice(0, 200)) != null
          ? c
          : void 0,
    });
  }
  return e;
}
var me = z(require("fs")),
  Pe = z(require("path")),
  rr = z(require("os")),
  Te = require("child_process");
var Vr = ["paddleocr_api_key", "vector_db_api_key"],
  jr = {
    paddleocr_api_key: "paddleocr-api-key",
    vector_db_api_key: "vector-db-api-key",
  },
  Xt = {
    paddleocr_api_key: "_paddleocr_configured",
    vector_db_api_key: "_vector_db_configured",
  },
  $r = {
    ocr: ["PADDLEOCR_API_KEY", "PADDLEOCR_API_TOKEN"],
    memory: ["VECTOR_DB_API_KEY", "VECTOR_DB_API_BASE", "VECTOR_DB_API_MODEL"],
    embed: ["VECTOR_DB_API_KEY", "VECTOR_DB_API_BASE", "VECTOR_DB_API_MODEL"],
  };
async function Qt(d, l) {
  var s;
  let e = (s = d.app) == null ? void 0 : s.secretStorage;
  if (!e || typeof e.getSecret != "function")
    return { migrated: [], warnings: [] };
  let t = [],
    r = [],
    n = Array.isArray(l._migrated_keys) ? l._migrated_keys : [];
  for (let a of Vr) {
    if (n.includes(a)) continue;
    let i = typeof l[a] == "string" ? l[a] : "";
    if (!i) continue;
    let c = jr[a] || a,
      p = await e.getSecret(c);
    if (p !== null) {
      if (p === i) {
        ((l[a] = ""), (l[Xt[a]] = !0), t.push(a));
        continue;
      }
      r.push(a);
      continue;
    }
    try {
      await e.setSecret(c, i);
    } catch (_) {
      r.push(a);
      continue;
    }
    if ((await e.getSecret(c)) !== i) {
      r.push(a);
      continue;
    }
    ((l[a] = ""), t.push(a), (l[Xt[a]] = !0));
  }
  if (t.length > 0 || r.length > 0) {
    let a = Array.isArray(l._migrated_keys) ? [...l._migrated_keys] : [];
    for (let i of t) a.includes(i) || a.push(i);
    if (((l._migrated_keys = a), r.length > 0)) {
      let i = Array.isArray(l._migration_warnings) ? l._migration_warnings : [];
      l._migration_warnings = [...i, ...r];
    }
    await d.saveData(l);
  }
  return { migrated: t, warnings: r };
}
async function We(d, l) {
  if (!$r[l]) return {};
  let t = d.app.secretStorage,
    r = {};
  if (l === "ocr") {
    let n = await t.getSecret("paddleocr-api-key");
    n && ((r.PADDLEOCR_API_KEY = n), (r.PADDLEOCR_API_TOKEN = n));
  } else if (l === "memory" || l === "embed") {
    let n = await t.getSecret("vector-db-api-key");
    n && (r.VECTOR_DB_API_KEY = n);
  }
  return r;
}
var zr = ["PADDLEOCR_", "VECTOR_DB_", "OPENAI_"];
function er(d) {
  let l = {};
  for (let [e, t] of Object.entries(d))
    zr.some((r) => e.startsWith(r)) || (l[e] = t);
  return l;
}
var kt = null,
  tr = !1;
function wt(d) {
  let l = String(d),
    t = {
      ENOENT: {
        type: "python_missing",
        message: "Python executable not found",
        recoverable: !0,
      },
      "python-missing": {
        type: "python_missing",
        message: "Python executable not found",
        recoverable: !0,
      },
      MODULE_NOT_FOUND: {
        type: "import_failed",
        message: "PaperForge package not installed",
        recoverable: !0,
      },
      "import-failed": {
        type: "import_failed",
        message: "PaperForge package not installed",
        recoverable: !0,
      },
      "version-mismatch": {
        type: "version_mismatch",
        message: "Plugin and package versions differ",
        recoverable: !0,
        action: "sync-runtime",
      },
      "pip-failed": {
        type: "pip_install_failure",
        message: "pip install command failed",
        recoverable: !0,
      },
      ETIMEDOUT: {
        type: "timeout",
        message: "Subprocess timed out",
        recoverable: !0,
        action: "retry",
      },
      timeout: {
        type: "timeout",
        message: "Subprocess timed out",
        recoverable: !0,
        action: "retry",
      },
      NO_PYTHON: {
        type: "no_python",
        message: "Python executable not found",
        recoverable: !0,
        action: "open-setup",
      },
      VECTOR_NOT_BUILT: {
        type: "vectors_not_built",
        message: "Vector index has not been built yet",
        recoverable: !0,
        action: "open-vector-settings",
      },
      VECTOR_CORRUPTED: {
        type: "vectors_corrupted",
        message: "Vector index is corrupted",
        recoverable: !0,
        action: "force-rebuild",
      },
      MODEL_CHANGED: {
        type: "model_changed",
        message: "Embedding model has changed since vectors were built",
        recoverable: !0,
        action: "rebuild-vectors",
      },
      BACKEND_UNAVAILABLE: {
        type: "backend_unavailable",
        message: "Python CLI search backend is not responding",
        recoverable: !0,
        action: "run-doctor",
      },
      TIMEOUT: {
        type: "timeout",
        message: "Search timed out",
        recoverable: !0,
        action: "retry",
      },
      INTERNAL_ERROR: {
        type: "internal_error",
        message: "An internal error occurred",
        recoverable: !1,
      },
    }[l];
  return t
    ? { ...t }
    : { type: "unknown", message: String(d), recoverable: !1 };
}
function St() {
  if (tr) return kt;
  tr = !0;
  try {
    let d;
    if (process.platform === "win32") {
      let l = process.env.ComSpec || "C:\\Windows\\System32\\cmd.exe";
      d = (0, Te.execFileSync)(l, ["/c", "where", "git"], {
        timeout: 5e3,
        windowsHide: !0,
        encoding: "utf-8",
      });
    } else
      d = (0, Te.execFileSync)("which", ["git"], {
        timeout: 5e3,
        encoding: "utf-8",
      });
    if (d) {
      let l = d
        .split(
          `
`
        )[0]
        .trim();
      l && (kt = Pe.dirname(l));
    }
  } catch (d) {}
  return kt;
}
function de() {
  let d = { ...process.env },
    l = process.platform,
    e = rr.homedir(),
    t = [],
    r = St();
  (r && t.push(r),
    l === "darwin"
      ? t.push(
          "/opt/homebrew/bin",
          "/usr/local/bin",
          "/usr/bin",
          `${e}/.local/bin`
        )
      : l === "linux" &&
        t.push("/usr/local/bin", "/usr/bin", `${e}/.local/bin`));
  let n = d.PATH || "";
  return ((d.PATH = [...t, n].filter(Boolean).join(Pe.delimiter)), er(d));
}
async function ge(d, l) {
  let e = await We(d, l),
    t = de();
  return Object.keys(e).length === 0 ? t : Object.assign({}, t, e);
}
function nr(d) {
  return String(d)
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "")
    .includes("betterbibtex");
}
function Pt(d) {
  if (!d) return !1;
  try {
    if (!me.existsSync(d)) return !1;
    for (let l of me.readdirSync(d)) if (nr(l)) return !0;
  } catch (l) {}
  return !1;
}
function nt(d) {
  if (!d) return !1;
  try {
    if (!me.existsSync(d)) return !1;
    for (let l of me.readdirSync(d)) {
      let e = Pe.join(d, l, "extensions");
      try {
        if (!me.existsSync(e)) continue;
        for (let t of me.readdirSync(e)) if (nr(t)) return !0;
      } catch (t) {}
    }
  } catch (l) {}
  return !1;
}
var Fe = z(require("fs")),
  X = z(require("path")),
  ar = require("child_process");
function Kr(d, l) {
  let e = l || Fe,
    t = X.join(d, "paperforge.json"),
    r = {
      system_dir: "System",
      resources_dir: "Resources",
      literature_dir: "Literature",
      base_dir: "Bases",
    };
  try {
    if (!e.existsSync(t))
      return { ...r, _warning: "paperforge.json not found; using defaults" };
    let n = e.readFileSync(t, "utf-8"),
      s = JSON.parse(n),
      a = s.vault_config || {};
    return {
      system_dir: a.system_dir || s.system_dir || r.system_dir,
      resources_dir: a.resources_dir || s.resources_dir || r.resources_dir,
      literature_dir: a.literature_dir || s.literature_dir || r.literature_dir,
      base_dir: a.base_dir || s.base_dir || r.base_dir,
      _warning: null,
    };
  } catch (n) {
    return (
      console.warn(
        "PaperForge: Failed to read paperforge.json, using defaults",
        n
      ),
      { ...r, _warning: "paperforge.json invalid; using defaults" }
    );
  }
}
function ue(d, l) {
  let e = Kr(d, l),
    t = X.join(d, e.system_dir, "PaperForge");
  return {
    vault: d,
    systemDir: t,
    indexesDir: X.join(t, "indexes"),
    logsDir: X.join(t, "logs"),
    dbPath: X.join(t, "indexes", "paperforge.db"),
    memoryStatePath: X.join(t, "indexes", "memory-runtime-state.json"),
    vectorStatePath: X.join(t, "indexes", "vector-runtime-state.json"),
    healthStatePath: X.join(t, "indexes", "runtime-health.json"),
    buildStatePath: X.join(t, "indexes", "vector-build-state.json"),
    orphanStatePath: X.join(t, "indexes", "sync-orphan-state.json"),
    exportsDir: X.join(t, "exports"),
    ocrDir: X.join(t, "ocr"),
    pluginDataPath: X.join(
      d,
      ".obsidian",
      "plugins",
      "paperforge",
      "data.json"
    ),
    pfJsonPath: X.join(d, "paperforge.json"),
    configWarning: e._warning,
  };
}
function Ct(d) {
  try {
    return Fe.existsSync(d) ? JSON.parse(Fe.readFileSync(d, "utf-8")) : null;
  } catch (l) {
    return null;
  }
}
function Ur(d) {
  let l = ue(d);
  return Ct(l.memoryStatePath);
}
var De = null;
function at(d) {
  let l = ue(d),
    e = Date.now();
  if (De && De.vaultPath === d && e - De.ts < 2e3) return De.result;
  let t = "",
    r = [
      X.join(d, ".paperforge-test-venv", "Scripts", "python.exe"),
      X.join(d, ".venv", "Scripts", "python.exe"),
      X.join(d, "venv", "Scripts", "python.exe"),
    ];
  for (let s = 0; s < r.length; s++)
    if (Fe.existsSync(r[s])) {
      t = r[s];
      break;
    }
  if (t)
    try {
      let s = (0, ar.execFileSync)(
          t,
          ["-m", "paperforge", "--vault", d, "embed", "status", "--json"],
          { encoding: "utf-8", timeout: 1e4, windowsHide: !0 }
        ),
        a = JSON.parse(s);
      if (a.ok && a.data) {
        let i = a.data;
        return ((De = { vaultPath: d, result: i, ts: e }), i);
      }
    } catch (s) {}
  let n = Ct(l.vectorStatePath);
  return ((De = { vaultPath: d, result: n, ts: e }), n);
}
function Ze(d) {
  let l = ue(d);
  return Ct(l.healthStatePath);
}
function sr(d) {
  var e;
  let l = Ze(d);
  return !!(l && ((e = l.summary) == null ? void 0 : e.status) === "ok");
}
function Rt(d) {
  let l = Ur(d);
  return !l || l.paper_count_db === 0
    ? "DB not found. Run paperforge memory build."
    : "Papers: " + l.paper_count_db + " | " + (l.fresh ? "fresh" : "stale");
}
function Me(d) {
  var t, r, n;
  let l = at(d);
  return l
    ? l.healthy === !1
      ? "Vector index unreadable - rebuild required"
      : "Chunks: " +
        (((t = l.chunk_count) != null ? t : 0) +
          ((r = l.body_chunk_count) != null ? r : 0) +
          ((n = l.object_chunk_count) != null ? n : 0)) +
        " | " +
        l.model +
        " | " +
        l.mode
    : "Status unavailable";
}
var Q = require("obsidian"),
  ce = z(require("fs")),
  Tt = z(require("path")),
  ur = z(require("https")),
  Le = require("child_process");
var At = z(require("fs")),
  $ = z(require("path")),
  it = require("child_process"),
  lr = z(require("os")),
  ir = 300 * 1e3,
  qr = "3.11";
function st() {
  let d, l;
  return {
    promise: new Promise((t, r) => {
      ((d = t), (l = r));
    }),
    resolve: d,
    reject: l,
  };
}
function Wr(d) {
  let l = d.match(/Python\s+(\d+\.\d+(?:\.\d+)?)/);
  if (l) return l[1];
  let e = d.match(/Python\s+(\d+\.\d+)/);
  return e ? e[1] + ".0" : null;
}
function cr(d, l) {
  var r, n;
  let e = d.split(".").map(Number),
    t = l.split(".").map(Number);
  for (let s = 0; s < Math.max(e.length, t.length); s++) {
    let a = (r = e[s]) != null ? r : 0,
      i = (n = t[s]) != null ? n : 0;
    if (a !== i) return a - i;
  }
  return 0;
}
function Zr(d, l) {
  return cr(d, l) >= 0;
}
function Gr() {
  var d;
  return (
    process.env.FLATPAK_ID !== void 0 ||
    ((d = process.env.XDG_DATA_DIRS) != null ? d : "").includes("flatpak") ||
    !1
  );
}
function Jr() {
  return process.env.SNAP !== void 0 || process.env.SNAP_NAME !== void 0 || !1;
}
function or(d, l) {
  var t;
  return `${(t = { win32: "windows", darwin: "macos", linux: "linux" }[d]) != null ? t : d}-${l}`;
}
function pr(d, l, e) {
  if (l !== void 0 || e !== void 0) {
    if (e) return [{ verb: "stop", label: "Stop" }];
    switch (d.state) {
      case "not_installed":
        return [{ verb: "install", label: "Install Runtime" }];
      case "needs_repair": {
        let t = [{ verb: "repair", label: "Repair Runtime" }];
        return (
          d.pythonPath && t.push({ verb: "rollback", label: "Rollback" }),
          t
        );
      }
      case "ready": {
        let t = [
          { verb: "status", label: "Check Status" },
          { verb: "update", label: "Update Runtime" },
        ];
        return (
          d.previousVersion && t.push({ verb: "rollback", label: "Rollback" }),
          t
        );
      }
      case "unknown":
        return [{ verb: "retry", label: "Retry" }];
      case "unavailable":
        return [{ verb: "setup", label: "Manual Setup" }];
      default:
        return [{ verb: "retry", label: "Retry" }];
    }
  }
  switch (d.state) {
    case "not_installed":
      return [
        {
          id: "install",
          label: "Install Runtime",
          primary: !0,
          destructive: !1,
        },
      ];
    case "needs_repair": {
      let t = [
        { id: "repair", label: "Repair Runtime", primary: !0, destructive: !1 },
      ];
      return (
        d.pythonPath &&
          t.push({
            id: "rollback",
            label: "Rollback",
            primary: !1,
            destructive: !1,
          }),
        t
      );
    }
    case "ready":
      return [
        { id: "status", label: "Check Status", primary: !1, destructive: !1 },
        { id: "update", label: "Update Runtime", primary: !1, destructive: !1 },
      ];
    case "unknown":
      return [
        { id: "probe", label: "Refresh Status", primary: !0, destructive: !1 },
      ];
    case "unavailable":
      return [
        { id: "setup", label: "Manual Setup", primary: !0, destructive: !1 },
      ];
    default:
      return [
        { id: "probe", label: "Refresh Status", primary: !0, destructive: !1 },
      ];
  }
}
function xe(d) {
  return d.state !== "ready" || !d.pythonPath
    ? null
    : { command: d.pythonPath, args: [] };
}
var Ee = class {
  constructor(l) {
    this._cache = null;
    this._cacheTime = 0;
    var r, n, s, a, i, c, p, u, _, g, h;
    let e =
        (n = (r = l.osPlatform) != null ? r : l.platform) != null
          ? n
          : process.platform,
      t = (a = (s = l.osArch) != null ? s : l.arch) != null ? a : process.arch;
    if (
      ((this.osPlatform = e),
      (this.osArch = t),
      (this.triplet = `${e}-${t}`),
      l.runtimeDir)
    )
      ((this.runtimeDir = l.runtimeDir),
        (this.rootDir = $.dirname(l.runtimeDir)),
        (this.pluginVersion =
          (c = (i = l.pluginVersion) != null ? i : l.version) != null
            ? c
            : "0.0.0"));
    else {
      let f = lr.homedir();
      ((this.rootDir = $.join(f, ".paperforge", "runtime")),
        (this.runtimeDir = $.join(this.rootDir, or(e, t))),
        (this.pluginVersion =
          (u = (p = l.version) != null ? p : l.pluginVersion) != null
            ? u
            : "0.0.0"));
    }
    ((this.pointerPath = $.join(this.rootDir, "active-runtime.json")),
      (this._fs = (_ = l.fs) != null ? _ : At),
      (this._execFile = (g = l.execFile) != null ? g : it.execFile),
      (this._execFileSync =
        (h = l.execFileSync) != null ? h : it.execFileSync));
  }
  current() {
    return this._cache
      ? Date.now() - this._cacheTime > ir
        ? { ...this._cache, state: "unknown", stale: !0 }
        : { ...this._cache, stale: !1 }
      : {
          state: "unknown",
          pythonPath: null,
          version: null,
          source: "none",
          error: null,
          lastVerifiedAt: null,
          stale: !0,
          warnings: [],
          previousVersion: null,
          previousPythonPath: null,
        };
  }
  async status(l) {
    var a;
    if (this._cache) {
      let i = Date.now() - this._cacheTime > ir;
      if (!i && this._cache.state === "ready")
        return { ...this._cache, stale: !1 };
      if (i && l != null && l.allowStale) return { ...this._cache, stale: !0 };
    }
    let e = null,
      t = null,
      r = null,
      n = null,
      s = [];
    try {
      let i = this._fs.readFileSync(this.pointerPath, "utf-8"),
        c = JSON.parse(i);
      e = typeof c.version == "string" ? c.version : null;
      let p = typeof c.pythonPath == "string" ? c.pythonPath : null;
      ((t = p ? $.resolve($.dirname(this.pointerPath), p) : null),
        (r = typeof c.previousVersion == "string" ? c.previousVersion : null),
        (n =
          typeof c.previousPythonPath == "string"
            ? c.previousPythonPath
            : null),
        (s = Array.isArray(c.warnings) ? c.warnings : []));
    } catch (i) {
      return this._setCache({
        state: "not_installed",
        pythonPath: null,
        version: null,
        source: "none",
        error: null,
        lastVerifiedAt: null,
        stale: !1,
        warnings: [],
        previousVersion: null,
        previousPythonPath: null,
      });
    }
    if (!t)
      return this._setCache({
        state: "needs_repair",
        pythonPath: null,
        version: e,
        source: "none",
        error: {
          code: "POINTER_MISSING_PATH",
          message: "Active runtime pointer has no pythonPath",
          platformAction: "Reinstall runtime",
        },
        lastVerifiedAt: null,
        stale: !1,
        warnings: s,
        previousVersion: r,
        previousPythonPath: n,
      });
    if (!this._fs.existsSync(t))
      return this._setCache({
        state: "needs_repair",
        pythonPath: t,
        version: e,
        source: "none",
        error: {
          code: "PYTHON_NOT_FOUND",
          message: "Python executable not found at pointer path",
          platformAction: "Reinstall runtime",
        },
        lastVerifiedAt: null,
        stale: !1,
        warnings: s,
        previousVersion: r,
        previousPythonPath: n,
      });
    try {
      let i = await this._probe(t),
        c = [...s];
      return this._setCache({
        state: "ready",
        pythonPath: t,
        version: (a = i.version) != null ? a : e,
        source: "venv",
        error: null,
        lastVerifiedAt: new Date().toISOString(),
        stale: !1,
        warnings: c,
        previousVersion: r,
        previousPythonPath: n,
      });
    } catch (i) {
      let c = i instanceof Error ? i.message : String(i);
      return this._setCache({
        state: "needs_repair",
        pythonPath: t,
        version: e,
        source: "venv",
        error: {
          code: "PROBE_FAILED",
          message: c,
          platformAction: "Repair runtime",
        },
        lastVerifiedAt: null,
        stale: !1,
        warnings: s,
        previousVersion: r,
        previousPythonPath: n,
      });
    }
  }
  async ensure(l) {
    var v, y;
    let e =
        (v = l == null ? void 0 : l.version) != null ? v : this.pluginVersion,
      t = (y = l == null ? void 0 : l.force) != null ? y : !1,
      r = l == null ? void 0 : l.signal;
    if (r != null && r.aborted) return this._abortedHealth();
    if (!t) {
      let m = this.current();
      if (m.state === "ready" && !m.stale) {
        let E = await this.status();
        if (E.state === "ready") return E;
      }
    }
    if (r != null && r.aborted) return this._abortedHealth();
    let n;
    try {
      n = this._resolveBootstrapPython();
    } catch (m) {
      if (Gr() || Jr())
        return this._setCache({
          state: "unavailable",
          pythonPath: null,
          version: null,
          source: "none",
          error: {
            code: "FLATPAK_SNAP_UNSUPPORTED",
            message:
              "Flatpak and Snap are not supported. Install Python 3.11+ natively.",
            platformAction:
              "Install Python 3.11+ from python.org or package manager",
          },
          lastVerifiedAt: null,
          stale: !1,
          warnings: [],
          previousVersion: null,
          previousPythonPath: null,
        });
      let E = or(this.osPlatform, this.osArch),
        k = this.osPlatform === "darwin",
        b = ["macos-x64", "macos-arm64"],
        x = ["windows-x64", "linux-x64"];
      return k && b.includes(E)
        ? this._setCache({
            state: "unavailable",
            pythonPath: null,
            version: null,
            source: "none",
            error: {
              code: "NO_PYTHON",
              message:
                "No Python 3.11+ found. macOS auto-download disabled until signed/notarized artifacts exist.",
              platformAction:
                "Install Python 3.11+ from python.org or Homebrew",
            },
            lastVerifiedAt: null,
            stale: !1,
            warnings: [],
            previousVersion: null,
            previousPythonPath: null,
          })
        : x.includes(E)
          ? this._setCache({
              state: "unavailable",
              pythonPath: null,
              version: null,
              source: "none",
              error: {
                code: "NO_PYTHON",
                message: "No Python 3.11+ found and automatic download failed.",
                platformAction: "Install Python 3.11+ manually",
              },
              lastVerifiedAt: null,
              stale: !1,
              warnings: [],
              previousVersion: null,
              previousPythonPath: null,
            })
          : this._setCache({
              state: "unavailable",
              pythonPath: null,
              version: null,
              source: "none",
              error: {
                code: "FALLBACK_UNAVAILABLE",
                message:
                  "No Python found and this platform has no validated fallback.",
                platformAction: "Install Python 3.11+ manually from python.org",
              },
              lastVerifiedAt: null,
              stale: !1,
              warnings: [],
              previousVersion: null,
              previousPythonPath: null,
            });
    }
    if (r != null && r.aborted) return this._abortedHealth();
    if (!Zr(n.version, qr))
      return this._setCache({
        state: "unavailable",
        pythonPath: null,
        version: n.version,
        source: "none",
        error: {
          code: "PYTHON_TOO_OLD",
          message: `Python ${n.version} is too old. Python 3.11+ required.`,
          platformAction: "Install Python 3.11+",
        },
        lastVerifiedAt: null,
        stale: !1,
        warnings: [],
        previousVersion: null,
        previousPythonPath: null,
      });
    if (this._currentSlotExists(e) && !t) {
      let m = !1;
      try {
        let E = this._fs.readFileSync(this.pointerPath, "utf-8"),
          k = JSON.parse(E),
          b = typeof k.version == "string" ? k.version : null;
        m = b !== null && b !== e;
      } catch (E) {}
      if (m) {
        let E = $.join(this.runtimeDir, `v${e}`),
          k = $.join(E, "venv"),
          b =
            this.osPlatform === "win32"
              ? $.join(k, "Scripts", "python.exe")
              : $.join(k, "bin", "python");
        try {
          await this._probe(b, r);
        } catch (P) {
          if (P instanceof Error && P.name === "AbortError")
            return this._abortedHealth();
          let L = P instanceof Error ? P.message : String(P);
          return this._setCache({
            state: "needs_repair",
            pythonPath: b,
            version: e,
            source: "venv",
            error: {
              code: "RETAINED_SLOT_PROBE_FAILED",
              message: `Retained slot v${e} failed verification: ${L}`,
              platformAction: "Repair runtime",
            },
            lastVerifiedAt: null,
            stale: !1,
            warnings: [],
            previousVersion: null,
            previousPythonPath: null,
          });
        }
        let x = null,
          w = null;
        try {
          let P = this._fs.readFileSync(this.pointerPath, "utf-8"),
            L = JSON.parse(P);
          ((x = typeof L.version == "string" ? L.version : null),
            (w = typeof L.pythonPath == "string" ? L.pythonPath : null));
        } catch (P) {}
        let R = $.dirname(this.pointerPath);
        this._fs.existsSync(R) || this._fs.mkdirSync(R, { recursive: !0 });
        let S = $.relative($.dirname(this.pointerPath), b),
          T = JSON.stringify(
            {
              schema_version: 1,
              version: e,
              pythonPath: S,
              activatedAt: new Date().toISOString(),
              previousVersion: x,
              previousPythonPath: w,
            },
            null,
            2
          ),
          F = this.pointerPath + ".tmp";
        (this._fs.writeFileSync(F, T, "utf-8"),
          this._fs.renameSync(F, this.pointerPath));
        let M = {
          state: "ready",
          pythonPath: b,
          version: e,
          source: "venv",
          error: null,
          lastVerifiedAt: new Date().toISOString(),
          stale: !1,
          warnings: [],
          previousVersion: x,
          previousPythonPath: w,
        };
        return (
          (this._cache = M),
          (this._cacheTime = Date.now()),
          this._cleanupOldSlots(e),
          M
        );
      }
    }
    if (r != null && r.aborted) return this._abortedHealth();
    let s = t
        ? $.join(this.runtimeDir, `v${e}_build2`)
        : $.join(this.runtimeDir, `v${e}`),
      a = $.join(s, "venv"),
      i =
        this.osPlatform === "win32"
          ? $.join(a, "Scripts", "python.exe")
          : $.join(a, "bin", "python");
    try {
      this._fs.mkdirSync(s, { recursive: !0 });
      let { promise: m, reject: E, resolve: k } = st();
      (this._execFile(
        n.path,
        ["-m", "venv", a],
        { timeout: 6e4, signal: r },
        (b) => {
          b ? E(b) : k();
        }
      ),
        await m);
    } catch (m) {
      if (m instanceof Error && m.name === "AbortError") {
        try {
          this._fs.rmSync(s, { recursive: !0, force: !0 });
        } catch (E) {}
        return this._abortedHealth();
      }
      return this._slotFailed(e, "VENV_CREATION_FAILED", m, s);
    }
    if (r != null && r.aborted) return this._abortedHealth();
    try {
      let { promise: m, reject: E, resolve: k } = st();
      (this._execFile(
        i,
        ["-m", "pip", "install", `paperforge==${e}`],
        { timeout: 12e4, signal: r },
        (b) => {
          b ? E(b) : k();
        }
      ),
        await m);
    } catch (m) {
      if (m instanceof Error && m.name === "AbortError") {
        try {
          this._fs.rmSync(s, { recursive: !0, force: !0 });
        } catch (E) {}
        return this._abortedHealth();
      }
      return this._slotFailed(e, "PIP_INSTALL_FAILED", m, s);
    }
    if (r != null && r.aborted) return this._abortedHealth();
    try {
      let { promise: m, reject: E, resolve: k } = st();
      (this._execFile(
        i,
        ["-I", "-c", "import paperforge; print(paperforge.__version__)"],
        { timeout: 3e4, signal: r },
        (b) => {
          b ? E(b) : k();
        }
      ),
        await m);
    } catch (m) {
      if (m instanceof Error && m.name === "AbortError") {
        try {
          this._fs.rmSync(s, { recursive: !0, force: !0 });
        } catch (E) {}
        return this._abortedHealth();
      }
      return this._slotFailed(e, "VERIFY_FAILED", m, s);
    }
    let c = null,
      p = null;
    try {
      let m = this._fs.readFileSync(this.pointerPath, "utf-8"),
        E = JSON.parse(m);
      ((c = typeof E.version == "string" ? E.version : null),
        (p = typeof E.pythonPath == "string" ? E.pythonPath : null));
    } catch (m) {}
    let u = $.dirname(this.pointerPath);
    this._fs.existsSync(u) || this._fs.mkdirSync(u, { recursive: !0 });
    let _ = $.relative($.dirname(this.pointerPath), i),
      g = JSON.stringify(
        {
          schema_version: 1,
          version: e,
          pythonPath: _,
          activatedAt: new Date().toISOString(),
          previousVersion: c,
          previousPythonPath: p,
        },
        null,
        2
      ),
      h = this.pointerPath + ".tmp";
    (this._fs.writeFileSync(h, g, "utf-8"),
      this._fs.renameSync(h, this.pointerPath));
    let f = {
      state: "ready",
      pythonPath: i,
      version: e,
      source: "venv",
      error: null,
      lastVerifiedAt: new Date().toISOString(),
      stale: !1,
      warnings: [],
      previousVersion: c,
      previousPythonPath: p,
    };
    return (
      (this._cache = f),
      (this._cacheTime = Date.now()),
      this._cleanupOldSlots(e),
      f
    );
  }
  _setCache(l) {
    return ((this._cache = l), (this._cacheTime = Date.now()), l);
  }
  _abortedHealth() {
    return {
      state: "needs_repair",
      pythonPath: null,
      version: null,
      source: "none",
      error: {
        code: "ABORTED",
        message: "Operation was cancelled",
        platformAction: "Retry operation",
      },
      lastVerifiedAt: null,
      stale: !1,
      warnings: [],
      previousVersion: null,
      previousPythonPath: null,
    };
  }
  _slotFailed(l, e, t, r) {
    try {
      this._fs.rmSync(r, { recursive: !0, force: !0 });
    } catch (s) {}
    let n = t instanceof Error ? t.message : String(t);
    return this._setCache({
      state: "needs_repair",
      pythonPath: null,
      version: l,
      source: "none",
      error: { code: e, message: n, platformAction: "Retry installation" },
      lastVerifiedAt: null,
      stale: !1,
      warnings: [],
      previousVersion: null,
      previousPythonPath: null,
    });
  }
  _currentSlotExists(l) {
    let e = $.join(this.runtimeDir, `v${l}`);
    return this._fs.existsSync(e);
  }
  _resolveBootstrapPython() {
    let l = [];
    this.osPlatform === "win32"
      ? l.push(
          { path: "py", args: ["-3.11"] },
          { path: "py", args: ["-3.10"] },
          { path: "py", args: ["-3"] },
          { path: "python", args: [] }
        )
      : this.osPlatform === "darwin"
        ? l.push(
            { path: "/usr/bin/python3", args: [] },
            { path: "python3", args: [] },
            { path: "python", args: [] }
          )
        : l.push(
            { path: "/usr/bin/python3", args: [] },
            { path: "python3", args: [] },
            { path: "python", args: [] }
          );
    for (let e of l)
      try {
        let t = this._execFileSync(e.path, [...e.args, "--version"], {
            encoding: "utf-8",
            timeout: 5e3,
          }),
          r = Wr(t);
        if (r) return { path: e.path, version: r };
      } catch (t) {}
    throw new Error("No Python 3.11+ found on system");
  }
  _probe(l, e) {
    let { promise: t, resolve: r, reject: n } = st();
    return (
      this._execFile(
        l,
        ["-I", "-c", "import paperforge; print(paperforge.__version__)"],
        { timeout: 3e4, signal: e },
        (s, a) => {
          if (s) n(s);
          else {
            let i = (a != null ? a : "").trim() || null;
            r({ version: i });
          }
        }
      ),
      t
    );
  }
  _cleanupOldSlots(l, e = 2) {
    try {
      let r = this._fs
        .readdirSync(this.runtimeDir, { withFileTypes: !0 })
        .filter((n) => n.isDirectory() && n.name.startsWith("v"))
        .map((n) => {
          let s = n.name.replace(/^v/, "").replace(/_build\d+$/, "");
          return { name: n.name, version: s };
        })
        .filter((n) => n.version !== l)
        .sort((n, s) => cr(s.version, n.version));
      for (let n = e; n < r.length; n++)
        this._fs.rmSync($.join(this.runtimeDir, r[n].name), {
          recursive: !0,
          force: !0,
        });
    } catch (t) {}
  }
};
function dr(d, l) {
  return !l || !l.trim()
    ? { blocked: !0, reason: "zotero" }
    : d
      ? { blocked: !1 }
      : { blocked: !0, reason: "ocr" };
}
var Dt = class extends Q.Modal {
  constructor(e, t, r, n) {
    super(e);
    this._rowEls = [];
    ((this.orphans = t.map((s, a) => ({ ...s, _selected: !0, _idx: a }))),
      (this.vaultPath = r),
      (this.py = n));
  }
  _updateUI() {
    let e = this.orphans.filter((t) => t._selected);
    (this._countEl.setText(
      o("orphan_delete_selected").replace("{count}", String(e.length))
    ),
      this._selectAllBtn.setText(
        e.length === this.orphans.length
          ? o("orphan_deselect_all")
          : o("orphan_select_all")
      ));
    for (let t of this.orphans) {
      let r = this._rowEls[t._idx];
      r && r.toggleClass("paperforge-orphan-dimmed", !t._selected);
    }
  }
  onOpen() {
    let { contentEl: e } = this;
    (e.addClass("paperforge-modal"),
      e.createEl("h2", {
        text: o("orphan_title").replace("{count}", String(this.orphans.length)),
      }),
      e.createEl("p", { cls: "paperforge-modal-desc", text: o("orphan_desc") }),
      (this._rowEls = []));
    let t = e.createEl("div", { cls: "paperforge-orphan-list" });
    for (let n of this.orphans) {
      let s = t.createEl("div", {
        cls:
          "paperforge-orphan-row" +
          (n._selected ? "" : " paperforge-orphan-dimmed"),
      });
      this._rowEls.push(s);
      let a = s.createEl("div", { cls: "paperforge-orphan-info" }),
        i = a.createEl("div", { cls: "paperforge-orphan-header" });
      i.createEl("span", {
        cls: "paperforge-orphan-key",
        text: n.citation_key || n.key,
      });
      let c = i.createEl("span", { cls: "paperforge-orphan-tags" });
      (c.createEl("span", {
        cls: "paperforge-tag " + (n.has_pdf ? "tag-pdf" : "tag-nopdf"),
        text: n.has_pdf ? "PDF" : "no PDF",
      }),
        n.collection_path &&
          c.createEl("span", {
            cls: "paperforge-tag tag-collection",
            text: n.collection_path,
          }),
        n.title &&
          a.createEl("div", { cls: "paperforge-orphan-title", text: n.title }));
      let p = [];
      (n.authors && p.push(n.authors),
        n.year && p.push(n.year),
        p.length > 0 &&
          a.createEl("div", {
            cls: "paperforge-orphan-meta",
            text: p.join(" \xB7 "),
          }),
        a.createEl("div", {
          cls: "paperforge-orphan-explain",
          text: o("orphan_explain"),
        }),
        s.addEventListener("click", () => {
          ((n._selected = !n._selected), this._updateUI());
        }));
    }
    let r = e.createEl("div", { cls: "paperforge-modal-actions" });
    ((this._selectAllBtn = r.createEl("button", {
      cls: "paperforge-step-btn",
      text: "Deselect all",
    })),
      this._selectAllBtn.addEventListener("click", () => {
        let n = this.orphans.every((s) => s._selected);
        for (let s of this.orphans) s._selected = !n;
        this._updateUI();
      }),
      (this._countEl = r.createEl("button", {
        cls: "paperforge-step-btn mod-cta",
        text: "Delete " + this.orphans.length + " selected",
      })),
      r
        .createEl("button", { cls: "paperforge-step-btn", text: "Keep all" })
        .addEventListener("click", () => this.close()),
      this._countEl.addEventListener("click", () => {
        let n = this.orphans.filter((a) => a._selected);
        if (n.length === 0) {
          new Q.Notice(o("orphan_none_selected"));
          return;
        }
        if (
          (this._countEl.setText("Deleting..."),
          this._countEl.setAttr("disabled", ""),
          this._selectAllBtn.setAttr("disabled", ""),
          !this.py || !this.py.path)
        ) {
          (new Q.Notice("PaperForge: Python not found"), this.close());
          return;
        }
        let s = n.map((a) => a.key);
        (0, Le.execFile)(
          this.py.path,
          [
            ...this.py.extraArgs,
            "-m",
            "paperforge",
            "--vault",
            this.vaultPath,
            "prune",
            "--force",
            "--json",
            ...s,
          ],
          { cwd: this.vaultPath, timeout: 6e4 },
          (a, i) => {
            if (a) {
              (new Q.Notice("PaperForge: prune failed"), this.close());
              return;
            }
            try {
              let c = JSON.parse(i),
                p = (c.data && c.data.deleted) || [];
              new Q.Notice("Deleted " + p.length + " orphan workspace(s)");
            } catch (c) {
              new Q.Notice("PaperForge: prune done");
            }
            this.close();
          }
        );
      }));
  }
  onClose() {
    this.contentEl.empty();
  }
};
function ct(d, l, e) {
  console.log("[PF] checkOrphanState called");
  try {
    let r = ue(e).orphanStatePath;
    if (!ce.existsSync(r)) {
      console.log("[PF] orphan file NOT FOUND");
      return;
    }
    console.log("[PF] orphan file FOUND");
    let n = ce.readFileSync(r, "utf-8"),
      a = JSON.parse(n),
      i = { path: "python", extraArgs: [], source: "auto-detected" };
    (console.log("[PF] py.path:", i ? i.path : "null"),
      new Dt(d, a, e, i).open(),
      ce.unlinkSync(r),
      console.log("[PF] orphan file cleaned"));
  } catch (t) {
    console.log("[PF] checkOrphanState exception:", t.message || t);
  }
}
var ke = class extends Q.Modal {
  constructor(e, t, r) {
    super(e);
    this._pendingSave = null;
    this._showSkipConfirm = !1;
    ((this.plugin = t), (this._step = 1), (this._onComplete = r));
  }
  _resolvePython() {
    var n;
    let e =
        ((n = this.plugin.settings.vault_path) == null ? void 0 : n.trim()) ||
        ".",
      t = new Ee({
        runtimeDir: Tt.join(e, ".paperforge-test-venv"),
        pluginVersion: this.plugin.manifest.version,
        osPlatform: process.platform,
        osArch: process.arch,
        fs: ce,
        execFile: Le.execFile,
        execFileSync: require("child_process").execFileSync,
      }),
      r = xe(t.current());
    return r
      ? { path: r.command, args: [...r.args] }
      : { path: "python", args: [] };
  }
  onOpen() {
    this._render();
  }
  onClose() {
    this.contentEl.empty();
  }
  _render() {
    let { contentEl: e } = this;
    (e.empty(),
      e.addClass("paperforge-modal"),
      this._renderStepIndicator(),
      this._renderStepContent(),
      this._renderNavigation());
  }
  _renderStepIndicator() {
    let e = [
        o("wizard_step1"),
        o("wizard_step2"),
        o("wizard_step3"),
        o("wizard_step4"),
        o("wizard_step5"),
      ],
      t = this.contentEl.createEl("div", { cls: "paperforge-step-bar" });
    e.forEach((r, n) => {
      let s = n + 1,
        a = t.createEl("div", {
          cls: `paperforge-step-dot ${s === this._step ? "active" : ""} ${s < this._step ? "done" : ""}`,
        });
      (a.createEl("span", { cls: "paperforge-step-num", text: `${s}` }),
        a.createEl("span", { cls: "paperforge-step-label", text: r }));
    });
  }
  _renderStepContent() {
    let e = this.contentEl.createEl("div", { cls: "paperforge-step-content" });
    switch (this._step) {
      case 1:
        this._stepOverview(e);
        break;
      case 2:
        this._stepDirectories(e);
        break;
      case 3:
        this._stepKeys(e);
        break;
      case 4:
        this._stepInstall(e);
        break;
      case 5:
        this._stepComplete(e);
        break;
    }
  }
  _renderNavigation() {
    let e = this.contentEl.createEl("div", { cls: "paperforge-step-nav" });
    (this._step > 1 &&
      e
        .createEl("button", { cls: "paperforge-step-btn", text: o("nav_prev") })
        .addEventListener("click", () => {
          (this._step--, (this._showSkipConfirm = !1), this._render());
        }),
      this._step < 5
        ? e
            .createEl("button", {
              cls: "paperforge-step-btn mod-cta",
              text: o("nav_next"),
            })
            .addEventListener("click", () => {
              if (this._step === 3) {
                let r = this._validateStep3();
                if (r.blocked) {
                  if (r.reason === "zotero") return;
                  if (r.reason === "ocr") {
                    ((this._showSkipConfirm = !0), this._render());
                    return;
                  }
                }
              }
              (this._step++, (this._showSkipConfirm = !1), this._render());
            })
        : e
            .createEl("button", {
              cls: "paperforge-step-btn",
              text: o("nav_close"),
            })
            .addEventListener("click", () => this.close()));
  }
  _validateStep3() {
    let e = this.plugin.settings,
      t = dr(this._apiKeyValidated, e.zotero_data_dir);
    if (t.reason === "ocr") return t;
    let r = (e.zotero_data_dir || "").trim();
    if (!r)
      return (
        new Q.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u4E3A\u5FC5\u586B\u9879\uFF0C\u8BF7\u586B\u5199\u8DEF\u5F84"
        ),
        { blocked: !0, reason: "zotero" }
      );
    if (!ce.existsSync(r))
      return (
        new Q.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u8DEF\u5F84\u4E0D\u5B58\u5728"
        ),
        { blocked: !0, reason: "zotero" }
      );
    if (!ce.statSync(r).isDirectory())
      return (
        new Q.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u8DEF\u5F84\u4E0D\u662F\u4E00\u4E2A\u76EE\u5F55"
        ),
        { blocked: !0, reason: "zotero" }
      );
    let n = Tt.join(r, "storage");
    return !ce.existsSync(n) || !ce.statSync(n).isDirectory()
      ? (new Q.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u4E2D\u672A\u627E\u5230 storage/ \u5B50\u76EE\u5F55"
        ),
        { blocked: !0, reason: "zotero" })
      : { blocked: !1 };
  }
  _stepOverview(e) {
    (e.createEl("h2", { text: o("wizard_title") }),
      e.createEl("p", { text: o("wizard_intro") }));
    let t = this.plugin.settings,
      r = this.app.vault.adapter.basePath,
      n = e.createEl("div", { cls: "paperforge-dir-tree" }),
      s = n.createEl("div", { cls: "paperforge-dir-node root" });
    s.textContent = `\u{1F4C1} Vault (${r})`;
    let a = n.createEl("div", { cls: "paperforge-dir-children" }),
      i = a.createEl("div", { cls: "paperforge-dir-node folder" });
    ((i.textContent = `\u{1F4C1} ${t.resources_dir || "Resources"}/ \u2014 \u6587\u732E\u5361\u7247\u76EE\u5F55\uFF08Base \u6570\u636E\u6765\u6E90\uFF09`),
      i
        .createEl("div", { cls: "paperforge-dir-children" })
        .createEl("div", {
          cls: "paperforge-dir-node file",
          text: `\u{1F4C1} ${t.literature_dir || "Literature"}/ \u2014 \u6587\u732E\u5361\u7247`,
        }),
      a.createEl("div", {
        cls: "paperforge-dir-node folder",
        text: `\u{1F4C1} ${t.base_dir || "Bases"}/ \u2014 \u6570\u636E\u7BA1\u7406\u9762\u677F`,
      }),
      a.createEl("div", {
        cls: "paperforge-dir-node folder",
        text: `\u{1F4C1} ${t.system_dir || "System"}/ \u2014 Zotero \u8F6F\u94FE\u63A5 + PaperForge \u7CFB\u7EDF\u6587\u4EF6\u5939`,
      }),
      e.createEl("p", {
        text: o("wizard_preview"),
        cls: "paperforge-modal-hint",
      }),
      e.createEl("p", {
        text: o("wizard_safety"),
        cls: "paperforge-modal-hint",
      }));
    let p = e.createEl("div", { cls: "paperforge-summary" }),
      u = [
        {
          label: o("dir_resources"),
          val: `${r}/${t.resources_dir || "Resources"}`,
        },
        {
          label: o("dir_notes"),
          val: `${r}/${t.resources_dir || "Resources"}/${t.literature_dir || "Literature"}`,
        },
        { label: o("dir_base"), val: `${r}/${t.base_dir || "Bases"}` },
        { label: o("dir_system"), val: `${r}/${t.system_dir || "System"}` },
      ];
    for (let _ of u) {
      let g = p.createEl("div", { cls: "paperforge-summary-row" });
      (g.createEl("span", { cls: "paperforge-summary-label", text: _.label }),
        g.createEl("span", { cls: "paperforge-summary-value", text: _.val }));
    }
  }
  _stepDirectories(e) {
    (e.createEl("h2", { text: o("wizard_step2") }),
      e.createEl("p", { text: o("wizard_intro") }));
    let t = this.plugin.settings,
      r = this.app.vault.adapter.basePath;
    (this._modalField(e, o("dir_vault"), r, !0),
      e.createEl("p", {
        text: o("wizard_dir_hint"),
        cls: "paperforge-modal-hint",
      }),
      this._modalInput(
        e,
        "\u8D44\u6E90\u76EE\u5F55\uFF08\u521B\u5EFA\u6587\u732E\u5361\u7247\u76EE\u5F55\u7684\u5730\u65B9\uFF09",
        "resources_dir",
        t.resources_dir,
        "Resources"
      ),
      e.createEl("p", {
        text: o("wizard_dir_sub_hint"),
        cls: "paperforge-modal-hint",
      }),
      this._modalInput(
        e,
        "\u6587\u732E\u5361\u7247\u76EE\u5F55\uFF08\u5B58\u653E\u6587\u732E\u5361\u7247\u7684\u5730\u65B9\uFF0CBase \u6570\u636E\u6765\u6E90\uFF09",
        "literature_dir",
        t.literature_dir,
        "Literature"
      ),
      e.createEl("p", {
        text: o("wizard_sys_hint"),
        cls: "paperforge-modal-hint",
      }),
      this._modalInput(
        e,
        "\u7CFB\u7EDF\u76EE\u5F55\uFF08\u5B58\u653E Zotero \u8F6F\u94FE\u63A5\u548C PaperForge \u7CFB\u7EDF\u6587\u4EF6\uFF09",
        "system_dir",
        t.system_dir,
        "System"
      ),
      this._modalInput(
        e,
        "Base \u76EE\u5F55\uFF08\u5B58\u653E\u6570\u636E\u7BA1\u7406\u9762\u677F\u7684\u5730\u65B9\uFF09",
        "base_dir",
        t.base_dir,
        "Bases"
      ),
      e.createEl("p", {
        text: o("wizard_safety"),
        cls: "paperforge-modal-hint",
      }));
    let n = e.createEl("div", { cls: "paperforge-summary" }),
      s = [
        { label: o("dir_resources"), val: `${r}/${t.resources_dir || ""}` },
        {
          label: o("dir_notes"),
          val: `${r}/${t.resources_dir || ""}/${t.literature_dir || ""}`,
        },
        { label: o("dir_system"), val: `${r}/${t.system_dir || ""}` },
        { label: o("dir_base"), val: `${r}/${t.base_dir || ""}` },
      ];
    for (let a of s) {
      let i = n.createEl("div", { cls: "paperforge-summary-row" });
      (i.createEl("span", { cls: "paperforge-summary-label", text: a.label }),
        i.createEl("span", { cls: "paperforge-summary-value", text: a.val }));
    }
  }
  _stepKeys(e) {
    if (
      (e.createEl("h2", { text: o("wizard_step3") }), this._showSkipConfirm)
    ) {
      this._renderSkipConfirm(e);
      return;
    }
    let t = this.plugin.settings;
    e.createEl("p", {
      text: o("wizard_agent_hint"),
      cls: "paperforge-modal-hint",
    });
    let r = [
        { key: "opencode", name: "OpenCode" },
        { key: "claude", name: "Claude Code" },
        { key: "cursor", name: "Cursor" },
        { key: "github_copilot", name: "GitHub Copilot" },
        { key: "windsurf", name: "Windsurf" },
        { key: "codex", name: "Codex" },
        { key: "gemini", name: "Gemini CLI" },
        { key: "cline", name: "Cline" },
      ],
      n = e.createEl("div", { cls: "paperforge-modal-field" });
    n.createEl("label", {
      cls: "paperforge-modal-label",
      text: o("label_agent"),
    });
    let s = n.createEl("select", { cls: "paperforge-modal-select" });
    for (let g of r) {
      let h = s.createEl("option", { text: g.name, attr: { value: g.key } });
      g.key === (t.agent_platform || "opencode") && (h.selected = !0);
    }
    (s.addEventListener("change", () => {
      ((t.agent_platform = s.value),
        this._pendingSave && clearTimeout(this._pendingSave),
        (this._pendingSave = setTimeout(() => {
          (this.plugin.saveSettings(), (this._pendingSave = null));
        }, 500)));
    }),
      e.createEl("p", {
        text: o("wizard_keys_hint"),
        cls: "paperforge-modal-hint",
      }));
    let a = e.createEl("div", { cls: "paperforge-modal-field" });
    a.createEl("label", {
      cls: "paperforge-modal-label",
      text: o("field_paddleocr"),
    });
    let i = a.createEl("input", {
        cls: "paperforge-modal-input",
        attr: { type: "password", placeholder: "API Key" },
      }),
      c = this.plugin.settings._paddleocr_configured || !1;
    ((i.placeholder = c
      ? "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022 (stored securely)"
      : "API Key"),
      (i.value = ""),
      (this._apiKeyValidated = !1),
      (this._apiKeyStatus = a.createEl("span", {
        cls: "paperforge-apikey-status",
        text: "",
      })));
    let p = a.createEl("button", {
      cls: "paperforge-step-btn",
      text: "\u9A8C\u8BC1",
    });
    (p.addEventListener("click", () => this._validateApiKey(i.value, p)),
      i.addEventListener("input", () => {
        ((this._apiKeyValidated = !1),
          (this._apiKeyStatus.textContent = ""),
          (this._apiKeyStatus.className = "paperforge-apikey-status"));
      }),
      this._pendingSave && clearTimeout(this._pendingSave),
      (this._pendingSave = setTimeout(() => {
        (this.plugin.saveSettings(), (this._pendingSave = null));
      }, 500)),
      e.createEl("p", {
        text: o("wizard_api_hint_skip"),
        cls: "paperforge-modal-hint",
      }));
    let u = e.createEl("div", { cls: "paperforge-modal-field" });
    u.createEl("label", {
      cls: "paperforge-modal-label",
      text: o("field_zotero_data"),
    });
    let _ = u.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text", placeholder: o("field_zotero_placeholder") },
    });
    ((_.value = t.zotero_data_dir || ""),
      _.addEventListener("input", () => {
        ((t.zotero_data_dir = _.value),
          this._pendingSave && clearTimeout(this._pendingSave),
          (this._pendingSave = setTimeout(() => {
            (this.plugin.saveSettings(), (this._pendingSave = null));
          }, 500)));
      }));
  }
  _validateApiKey(e, t) {
    if (!e || e.length < 10) {
      ((this._apiKeyStatus.textContent =
        "\u5BC6\u94A5\u683C\u5F0F\u4E0D\u6B63\u786E\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
        (this._apiKeyStatus.className = "paperforge-apikey-status error"));
      return;
    }
    ((t.disabled = !0),
      (t.textContent = "\u9A8C\u8BC1\u4E2D\u2026"),
      (this._apiKeyStatus.textContent = "\u6B63\u5728\u9A8C\u8BC1\u2026"),
      (this._apiKeyStatus.className = "paperforge-apikey-status"));
    let r = JSON.stringify({ model: "PaddleOCR-VL-1.5" }),
      n = {
        hostname: "paddleocr.aistudio-app.com",
        path: "/api/v2/ocr/jobs",
        method: "POST",
        headers: {
          Authorization: "bearer " + e,
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(r),
        },
        timeout: 1e4,
      },
      s = ur.request(n, async (a) => {
        ((t.disabled = !1), (t.textContent = "\u9A8C\u8BC1"));
        let i = "";
        (a.on("data", (c) => (i += c)),
          a.on("end", async () => {
            var c, p;
            try {
              let u = JSON.parse(i);
              if (a.statusCode === 400 && u.code === 10001) {
                let _ = this.app.secretStorage;
                try {
                  if (
                    (await ((c = _ == null ? void 0 : _.setSecret) == null
                      ? void 0
                      : c.call(_, "paddleocr-api-key", e)),
                    (await ((p = _ == null ? void 0 : _.getSecret) == null
                      ? void 0
                      : p.call(_, "paddleocr-api-key"))) === e)
                  ) {
                    let h = this.plugin.settings;
                    ((h._paddleocr_configured = !0),
                      (h.paddleocr_api_key = ""),
                      this.plugin.saveSettings());
                  }
                } catch (g) {}
                ((this._apiKeyStatus.textContent =
                  "\u2713 \u5BC6\u94A5\u6709\u6548"),
                  (this._apiKeyStatus.className =
                    "paperforge-apikey-status ok"),
                  (this._apiKeyValidated = !0));
              } else
                a.statusCode === 401
                  ? ((this._apiKeyStatus.textContent =
                      "\u9A8C\u8BC1\u5931\u8D25\uFF1A\u5BC6\u94A5\u65E0\u6548\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
                    (this._apiKeyStatus.className =
                      "paperforge-apikey-status error"),
                    (this._apiKeyValidated = !1))
                  : ((this._apiKeyStatus.textContent =
                      "\u9A8C\u8BC1\u5931\u8D25\uFF1AAPI \u8FD4\u56DE " +
                      a.statusCode +
                      "\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
                    (this._apiKeyStatus.className =
                      "paperforge-apikey-status error"),
                    (this._apiKeyValidated = !1));
            } catch (u) {
              ((this._apiKeyStatus.textContent =
                "\u9A8C\u8BC1\u5931\u8D25\uFF1A\u65E0\u6CD5\u89E3\u6790\u54CD\u5E94\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
                (this._apiKeyStatus.className =
                  "paperforge-apikey-status error"),
                (this._apiKeyValidated = !1));
            }
          }));
      });
    (s.on("error", (a) => {
      ((t.disabled = !1),
        (t.textContent = "\u9A8C\u8BC1"),
        (this._apiKeyStatus.textContent =
          "\u9A8C\u8BC1\u5931\u8D25\uFF1A\u65E0\u6CD5\u8FDE\u63A5 (" +
          a.message +
          ")\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
        (this._apiKeyStatus.className = "paperforge-apikey-status error"),
        (this._apiKeyValidated = !1));
    }),
      s.write(r),
      s.end());
  }
  _renderSkipConfirm(e) {
    e.createEl("p", {
      text: o("wizard_skip_ocr_desc"),
      cls: "paperforge-modal-desc",
    });
    let t = e.createEl("div", { cls: "paperforge-modal-actions" });
    (t
      .createEl("button", {
        cls: "paperforge-step-btn mod-cta",
        text: o("wizard_skip_ocr_continue"),
      })
      .addEventListener("click", () => {
        ((this._showSkipConfirm = !1), this._step++, this._render());
      }),
      t
        .createEl("button", {
          cls: "paperforge-step-btn",
          text: o("wizard_skip_ocr_back"),
        })
        .addEventListener("click", () => {
          ((this._showSkipConfirm = !1), this._render());
        }));
  }
  _modalField(e, t, r, n) {
    let s = e.createEl("div", { cls: "paperforge-modal-field" });
    s.createEl("label", { cls: "paperforge-modal-label", text: t });
    let a = s.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text" },
    });
    ((a.value = r), (a.disabled = !!n));
  }
  _modalInput(e, t, r, n, s) {
    let a = e.createEl("div", { cls: "paperforge-modal-field" });
    a.createEl("label", { cls: "paperforge-modal-label", text: t });
    let i = a.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text", placeholder: s || "" },
    });
    i.value = n;
    let c = this.plugin.settings;
    i.addEventListener("input", () => {
      ((c[r] = i.value),
        this._pendingSave && clearTimeout(this._pendingSave),
        (this._pendingSave = setTimeout(() => {
          (this.plugin.saveSettings(), (this._pendingSave = null));
        }, 500)));
    });
  }
  _modalSecret(e, t, r, n, s) {
    let a = e.createEl("div", { cls: "paperforge-modal-field" });
    a.createEl("label", { cls: "paperforge-modal-label", text: t });
    let i = a.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "password", placeholder: s || "" },
    });
    i.value = n;
    let c = this.plugin.settings;
    i.addEventListener("input", () => {
      ((c[r] = i.value),
        this._pendingSave && clearTimeout(this._pendingSave),
        (this._pendingSave = setTimeout(() => {
          (this.plugin.saveSettings(), (this._pendingSave = null));
        }, 500)));
    });
  }
  _stepInstall(e) {
    (e.createEl("h2", { text: o("wizard_step4") }),
      (this._installLog = e.createEl("div", {
        cls: "paperforge-install-log",
      })));
    let t = e.createEl("button", {
      cls: "paperforge-step-btn mod-cta",
      text: o("install_btn"),
    });
    t.addEventListener("click", () => this._runInstall(t));
  }
  async _runInstall(e) {
    var a, i, c, p, u, _;
    ((e.disabled = !0),
      (e.textContent = o("install_btn_running")),
      this._installLog.setText(
        o("install_validating") +
          `
`
      ),
      this._log(o("install_validating")));
    let t = this.plugin.settings,
      r = this._validate();
    if (r.length > 0) {
      (this._log(o("validate_fail") + ":"),
        r.forEach((g) => this._log("  \u2717 " + g)),
        (e.disabled = !1),
        (e.textContent = o("install_btn_retry")));
      return;
    }
    let n = (g, h = {}) =>
        new Promise((f, v) => {
          let { path: y, args: m = [] } = this._resolvePython(),
            E = (0, Le.spawn)(y, [...m, ...g], {
              cwd: t.vault_path.trim(),
              env: de(),
              timeout: 12e4,
              ...h,
            }),
            k = "",
            b = "";
          (E.stdout.on("data", (x) => {
            let w = x.toString("utf-8");
            ((k += w), h.logStdout && this._processSetupOutput(w));
          }),
            E.stderr.on("data", (x) => {
              let w = x.toString("utf-8");
              ((b += w), this._log("[stderr] " + w.trim()));
            }),
            E.on("close", (x) => {
              x === 0
                ? f({ stdout: k, stderr: b })
                : v(new Error(b.trim() || k.trim() || `exit code ${x}`));
            }),
            E.on("error", (x) => v(x)));
        }),
      s = [
        "-m",
        "paperforge",
        "--vault",
        t.vault_path.trim(),
        "setup",
        "--headless",
        "--system-dir",
        t.system_dir.trim(),
        "--resources-dir",
        t.resources_dir.trim(),
        "--literature-dir",
        t.literature_dir.trim(),
        "--base-dir",
        t.base_dir.trim(),
        "--agent",
        t.agent_platform || "opencode",
      ];
    t.zotero_data_dir &&
      t.zotero_data_dir.trim() &&
      s.push("--zotero-data", t.zotero_data_dir.trim());
    try {
      let g = !0;
      try {
        await n(["-c", "import paperforge"]);
      } catch (h) {
        g = !1;
      }
      if (!g) {
        this._log(o("install_bootstrapping"));
        let h = this.plugin.manifest.version;
        this._log(`[install] Trying PyPI: pip install paperforge==${h}`);
        let f = ["-m", "pip", "install", "--upgrade"];
        (process.platform !== "win32" && f.push("--user"),
          f.push(`paperforge==${h}`));
        try {
          await n(f, { logStdout: !0 });
        } catch (v) {
          (this._log(
            `[install] PyPI failed, falling back to git: git+https://...@v${h}`
          ),
            console.warn(
              "[PaperForge] PyPI install failed, falling back to git:",
              (a = v.message) == null ? void 0 : a.slice(0, 200)
            ));
          let y = ["-m", "pip", "install", "--upgrade"];
          (process.platform !== "win32" && y.push("--user"),
            y.push(`git+https://github.com/LLLin000/PaperForge.git@v${h}`),
            await n(y, { logStdout: !0 }));
        }
      }
      (await n(s, { logStdout: !0, env: de() }),
        this._log(o("install_complete")),
        await this.plugin.saveSettings(),
        this._onComplete && this._onComplete(),
        setTimeout(() => {
          ((this._step = 5), this._render());
        }, 800));
    } catch (g) {
      console.error("PaperForge setup failed:", g.message);
      let h = this._formatSetupError(g.message);
      this._log(o("install_failed") + h);
      let f =
        (i = this._installLog.parentElement) == null
          ? void 0
          : i.createEl("button", {
              cls: "paperforge-copy-diag-btn",
              text: o("error_copy_diagnostic") || "Copy diagnostic",
            });
      if (f) {
        let v = g.message,
          y =
            ((p = (c = this.plugin) == null ? void 0 : c.settings) == null
              ? void 0
              : p.python_path) || "auto",
          m =
            ((_ = (u = this.plugin) == null ? void 0 : u.manifest) == null
              ? void 0
              : _.version) || "?",
          E = process.platform + " " + process.arch,
          k,
          b;
        try {
          k = St() || "(not found)";
        } catch (S) {
          k = "(error)";
        }
        try {
          b = this._resolvePython();
        } catch (S) {
          b = null;
        }
        let x = (process.env.PATH || "").length,
          w = (process.env.PATH || "").toLowerCase().includes("git"),
          R = [
            "[PaperForge Diagnostic]",
            "Category: " + h,
            "Plugin version: " + m,
            "Python: " + y,
            "Resolved Python: " + ((b == null ? void 0 : b.path) || "?"),
            "OS: " + E,
            "Vault path: " + (t.vault_path || "?"),
            "--- Git ---",
            "Git dir (resolved): " + k,
            "PATH length: " + x + " chars",
            "PATH contains git: " + w,
            "--- Raw error ---",
            v.slice(0, 2e3),
          ].join(`
`);
        f.addEventListener("click", () => {
          navigator.clipboard
            .writeText(R)
            .then(() => {
              (f.setText(o("error_copied") || "Copied!"),
                setTimeout(() => {
                  f.setText(o("error_copy_diagnostic") || "Copy diagnostic");
                }, 3e3));
            })
            .catch(() => {
              new Q.Notice("[!!] Clipboard write failed", 6e3);
            });
        });
      }
      ((e.disabled = !1), (e.textContent = o("install_btn_retry")));
    }
  }
  _log(e) {
    this._installLog &&
      this._installLog.setText(
        this._installLog.textContent +
          e +
          `
`
      );
  }
  _validate() {
    let e = [],
      t = this.plugin.settings;
    return (
      (!t.vault_path || !t.vault_path.trim()) && e.push(o("validate_vault")),
      (!t.resources_dir || !t.resources_dir.trim()) &&
        e.push(o("validate_resources")),
      (!t.literature_dir || !t.literature_dir.trim()) &&
        e.push(o("validate_notes")),
      (!t.base_dir || !t.base_dir.trim()) && e.push(o("validate_base")),
      this.plugin.settings._paddleocr_configured ||
        !1 ||
        this._log("  ! " + o("validate_key") + " " + o("optional_later")),
      (!t.zotero_data_dir || !t.zotero_data_dir.trim()) &&
        this._log("  ! " + o("validate_zotero") + " " + o("optional_later")),
      e
    );
  }
  _processSetupOutput(e) {
    let t = e
      .split(
        `
`
      )
      .filter(Boolean);
    for (let r of t)
      if (r.includes("[*]") || r.includes("[OK]") || r.includes("[FAIL]")) {
        let n = r
          .replace(/^\[\*\].*\d+:?\s*/, "")
          .replace(/^\[OK\]\s*/, "")
          .replace(/^\[FAIL\]\s*/, "");
        this._log("  " + n);
      }
  }
  _formatSetupError(e) {
    if (
      process.platform === "darwin" &&
      /No module named ['"]?paperforge/i.test(e)
    )
      return "PaperForge not installed \u2014 install Python from Homebrew or python.org (Apple CLT /Library/Developer/CommandLineTools python often fails); then: python3 -m pip install --user git+https://github.com/LLLin000/PaperForge.git";
    let t = [
      {
        match: /pip.*not found|No module named.*pip|command not found.*pip/i,
        msg: "pip not found",
      },
      {
        match: /command not found|No such file|not recognized/i,
        msg: "Python not found",
      },
      {
        match:
          /resolve host|getaddrinfo.*nodename|connect ETIMEDOUT|connect ECONNREFUSED|fetch failed|Network error|ENOTFOUND|ECONNREFUSED|ECONNRESET/i,
        msg: "Network error",
      },
      {
        match:
          /certificate verify failed|SSL.*certificate|self.signed.cert|CERTIFICATE_VERIFY_FAILED/i,
        msg: "SSL certificate error",
      },
      { match: /No space left on device|disk full|ENOSPC/i, msg: "Disk full" },
      {
        match:
          /paperforge.*not found|cannot import|ModuleNotFoundError|No module named/i,
        msg: "PaperForge not installed",
      },
      { match: /permission denied|EACCES|EPERM/i, msg: "Permission denied" },
      { match: /ENOENT/i, msg: "Path not found" },
      { match: /timeout|timed out/i, msg: "Timeout" },
    ];
    for (let n of t) if (n.match.test(e)) return n.msg;
    return (
      e
        .split(
          `
`
        )
        .filter(Boolean)
        .slice(0, 3)
        .join(" | ")
        .slice(0, 200) || "Unknown error"
    );
  }
  _stepComplete(e) {
    e.createEl("h2", { text: o("complete_title") });
    let t = e.createEl("div", { cls: "paperforge-summary" });
    t.createEl("div", {
      cls: "paperforge-summary-title",
      text: o("complete_summary"),
    });
    let r = this.plugin.settings,
      n = this.app.vault.adapter.basePath,
      s = [
        { label: o("dir_vault"), val: n },
        { label: o("dir_resources"), val: `${n}/${r.resources_dir}` },
        {
          label: o("dir_notes"),
          val: `${n}/${r.resources_dir}/${r.literature_dir}`,
        },
        { label: o("dir_base"), val: `${n}/${r.base_dir}` },
        { label: o("dir_system"), val: `${n}/${r.system_dir}` },
        {
          label: "API Key",
          val: this.plugin.settings._paddleocr_configured
            ? o("api_key_set")
            : o("api_key_missing"),
        },
        {
          label: o("field_zotero_data"),
          val: r.zotero_data_dir || o("not_set"),
        },
      ];
    for (let u of s) {
      let _ = t.createEl("div", { cls: "paperforge-summary-row" });
      (_.createEl("span", { cls: "paperforge-summary-label", text: u.label }),
        _.createEl("span", { cls: "paperforge-summary-value", text: u.val }));
    }
    let a = t.createEl("div", { cls: "paperforge-summary-row" });
    a.createEl("span", { cls: "paperforge-summary-label", text: "PaperForge" });
    let i = a.createEl("span", {
      cls: "paperforge-summary-value",
      text: "\u2014",
    });
    {
      let u = n,
        { path: _, args: g = [] } = this._resolvePython();
      (0, Le.execFile)(
        _,
        [...g, "-c", "import paperforge; print(paperforge.__version__)"],
        { cwd: u, timeout: 1e4 },
        (h, f) => {
          !h && f && (i.textContent = "v" + f.trim());
        }
      );
    }
    for (let u of s) {
      let _ = t.createEl("div", { cls: "paperforge-summary-row" });
      (_.createEl("span", { cls: "paperforge-summary-label", text: u.label }),
        _.createEl("span", { cls: "paperforge-summary-value", text: u.val }));
    }
    e.createEl("h3", { text: o("complete_next") });
    let c = e.createEl("div", { cls: "paperforge-nextsteps" }),
      p = [
        [o("complete_step4"), o("complete_step4_desc")],
        [
          "",
          `${o("complete_export_path")} ${n}/${r.system_dir}/PaperForge/exports/`,
        ],
        [o("complete_step1"), o("complete_step1_desc")],
        [o("complete_step2"), o("complete_step2_desc")],
        [o("complete_step3"), o("complete_step3_desc")],
      ];
    for (let [u, _] of p) {
      let g = c.createEl("div", { cls: "paperforge-nextstep-item" });
      (u && g.createEl("strong", { text: u }), g.createEl("span", { text: _ }));
    }
  }
};
function _r(d, l) {
  if (l.key !== "Tab") return;
  let e = d.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  if (e.length === 0) return;
  let t = e[0],
    r = e[e.length - 1];
  l.shiftKey
    ? document.activeElement === t && (l.preventDefault(), r.focus())
    : document.activeElement === r && (l.preventDefault(), t.focus());
}
var ot = class extends Q.Modal {
    constructor(e, t, r) {
      super(e);
      this._returnFocusEl = null;
      this._inertedEls = [];
      ((this._config = t),
        (this._onConfirm = r),
        (this._returnFocusEl = document.activeElement));
    }
    onOpen() {
      let { contentEl: e } = this;
      (e.addClass("paperforge-modal"),
        e.addClass("paperforge-confirm-modal"),
        e.setAttr("role", "alertdialog"),
        e.setAttr("aria-modal", "true"));
      let t = e.closest(".modal-container");
      if (t) {
        let i = t.parentElement;
        if (i)
          for (let c of Array.from(i.children))
            c !== t &&
              !c.hasAttribute("inert") &&
              (c.setAttribute("inert", ""), this._inertedEls.push(c));
      }
      e.createEl("h2", { text: this._config.title });
      let r = e.createEl("div", { cls: "paperforge-confirm-effect" });
      (r.createEl("span", {
        cls: "paperforge-confirm-effect-label",
        text: "Effect: ",
      }),
        r.createEl("span", { text: this._config.effectLabel }));
      let n = e.createEl("div", { cls: "paperforge-confirm-actions" }),
        s = n.createEl("button", {
          text:
            this._config.cancelLabel ||
            o("maintenance_confirm_cancel") ||
            "Cancel",
        });
      (s.addEventListener("click", () => this.close()),
        n
          .createEl("button", {
            cls: "mod-warning",
            text:
              this._config.confirmLabel ||
              o("maintenance_confirm_ok") ||
              "Proceed",
          })
          .addEventListener("click", () => {
            (this._onConfirm && this._onConfirm(), this.close());
          }),
        (this._boundKeydown = (i) => _r(e, i)),
        e.addEventListener("keydown", this._boundKeydown),
        s.focus());
    }
    onClose() {
      for (let e of this._inertedEls) e.removeAttribute("inert");
      if (
        ((this._inertedEls.length = 0),
        this._boundKeydown &&
          this.contentEl.removeEventListener("keydown", this._boundKeydown),
        this.contentEl.empty(),
        this._returnFocusEl && typeof this._returnFocusEl.focus == "function")
      )
        try {
          this._returnFocusEl.focus();
        } catch (e) {}
    }
  },
  Yr = [
    { pattern: /sk-[A-Za-z0-9]{16,}/g, label: "API key", class_: "credential" },
    {
      pattern: /[A-Za-z0-9+/]{20,}={0,2}/g,
      label: "Credential token",
      class_: "credential",
    },
    {
      pattern: /api[_-]?key[=:]\s*['"]?\S+['"]?/gi,
      label: "API key",
      class_: "credential",
    },
    {
      pattern: /token[=:]\s*['"]?\S+['"]?/gi,
      label: "Token",
      class_: "credential",
    },
    {
      pattern: /[A-Za-z]:\\[^"'\n,;]+/gi,
      label: "Absolute path",
      class_: "vault-path",
    },
    {
      pattern: /(?<=^|\s)\/[^/\s][^"'\n,;]*/g,
      label: "Absolute path",
      class_: "vault-path",
    },
    {
      pattern: /Zotero[^"'\s,;]*/gi,
      label: "Zotero path",
      class_: "zotero-path",
    },
    {
      pattern: /Paper:\s*[^\n]+/gi,
      label: "Paper title",
      class_: "paper-title",
    },
    {
      pattern: /Title:\s*[^\n]+/gi,
      label: "Paper title",
      class_: "paper-title",
    },
  ];
function Ge(d) {
  let l = {},
    e = d;
  for (let { pattern: t, label: r, class_: n } of Yr) {
    let s = 0;
    ((e = e.replace(t, () => (s++, "[REDACTED]"))),
      s > 0 &&
        (l[n] || (l[n] = { label: r, class_: n, count: 0 }),
        (l[n].count += s)));
  }
  return { clean: e, redactions: Object.values(l) };
}
function fr(d, l, e, t) {
  let r = `OCR: ${d} (${e} papers)`,
    n = [
      "## Diagnostic Summary",
      `- Reason: ${d}`,
      `- Detail: ${l}`,
      `- Papers affected: ${e}`,
      "",
      "## Environment",
      "- Vault: [REDACTED]",
      "- Plugin version: PaperForge",
      "",
      "## Steps to reproduce",
      "1. Run OCR on affected papers",
      "2. Review output quality",
      "3. Review this draft, then open GitHub to submit",
    ].join(`
`);
  return { title: r, body: n, labels: ["ocr", "quality", "auto-generated"] };
}
var lt = class extends Q.Modal {
  constructor(e, t, r) {
    super(e);
    this._returnFocusEl = null;
    this._inertedEls = [];
    ((this._draft = t),
      (this._githubUrl = r),
      (this._returnFocusEl = document.activeElement));
  }
  onOpen() {
    let { contentEl: e } = this;
    (e.addClass("paperforge-modal"),
      e.addClass("paperforge-issue-draft-modal"),
      e.setAttr("role", "dialog"),
      e.setAttr("aria-modal", "true"));
    let t = e.closest(".modal-container");
    if (t) {
      let f = t.parentElement;
      if (f)
        for (let v of Array.from(f.children))
          v !== t &&
            !v.hasAttribute("inert") &&
            (v.setAttribute("inert", ""), this._inertedEls.push(v));
    }
    (e.createEl("h2", {
      text: o("maintenance_issue_draft_title") || "OCR Issue Draft",
    }),
      e.createEl("p", {
        cls: "paperforge-issue-draft-desc",
        text:
          o("maintenance_issue_draft_preview") ||
          "Review the issue draft below before opening GitHub.",
      }));
    let r = e.createEl("div", { cls: "paperforge-issue-draft-field" });
    r.createEl("label", { text: "Title" });
    let n = Ge(this._draft.title).clean;
    this._titleInput = r.createEl("input", {
      cls: "paperforge-issue-draft-input",
      attr: { type: "text", value: n },
    });
    let s = e.createEl("div", { cls: "paperforge-issue-draft-field" });
    s.createEl("label", { text: "Body" });
    let a = Ge(this._draft.body).clean;
    this._bodyTextarea = s.createEl("textarea", {
      cls: "paperforge-issue-draft-textarea",
      attr: { rows: "12" },
      text: a,
    });
    let { redactions: i } = Ge(
        this._draft.title +
          `
` +
          this._draft.body
      ),
      c = e.createEl("div", { cls: "paperforge-issue-draft-preview" }),
      p = c.createEl("div", { cls: "paperforge-issue-draft-included" });
    (p.createEl("span", {
      cls: "paperforge-issue-draft-preview-label",
      text: (o("maintenance_issue_draft_included") || "Included") + ": ",
    }),
      p.createEl("span", {
        text: `Title, Body, Labels (${this._draft.labels.join(", ")})`,
      }));
    let u = c.createEl("div", { cls: "paperforge-issue-draft-redacted" });
    (u.createEl("span", {
      cls: "paperforge-issue-draft-preview-label",
      text: (o("maintenance_issue_draft_redacted") || "Redacted") + ": ",
    }),
      u.createEl("span", {
        text:
          "Credentials, vault/Zotero paths, paper titles, paper content are excluded" +
          (i.length > 0
            ? " (" + i.map((f) => `${f.count} ${f.label}`).join(", ") + ")"
            : ""),
      }));
    let _ = e.createEl("div", { cls: "paperforge-issue-draft-actions" });
    (_.createEl("button", {
      text: o("maintenance_confirm_cancel") || "Cancel",
    }).addEventListener("click", () => this.close()),
      _.createEl("button", {
        cls: "mod-cta",
        text: o("maintenance_issue_draft_open_github") || "Open GitHub Issue",
      }).addEventListener("click", () => {
        let f = encodeURIComponent(Ge(this._titleInput.value).clean),
          v = encodeURIComponent(Ge(this._bodyTextarea.value).clean),
          y = encodeURIComponent(this._draft.labels.join(",")),
          m = `${this._githubUrl}?title=${f}&body=${v}&labels=${y}`;
        window.open(m, "_blank", "noopener,noreferrer");
      }),
      (this._boundKeydown = (f) => _r(e, f)),
      e.addEventListener("keydown", this._boundKeydown),
      this._titleInput.focus());
  }
  onClose() {
    for (let e of this._inertedEls) e.removeAttribute("inert");
    if (
      ((this._inertedEls.length = 0),
      this._boundKeydown &&
        this.contentEl.removeEventListener("keydown", this._boundKeydown),
      this.contentEl.empty(),
      this._returnFocusEl && typeof this._returnFocusEl.focus == "function")
    )
      try {
        this._returnFocusEl.focus();
      } catch (e) {}
  }
};
var Oe = z(require("fs")),
  pt = z(require("path")),
  gr = require("child_process");
function Ft(d) {
  return d.display_action === "rebuild_result"
    ? "rebuild"
    : d.display_action === "retry_ocr" || d.display_action === "upgrade_legacy"
      ? "redo"
      : null;
}
function Mt(d) {
  return d === "redo";
}
function Xr(d, l, e) {
  let t = { manifest: d, papers: {}, cached_at: new Date().toISOString() };
  if (e != null && e.papers)
    for (let r of Object.keys(d)) e.papers[r] && (t.papers[r] = e.papers[r]);
  for (let r of l) t.papers[r.key] = r;
  return t;
}
function mr(d) {
  return pt.join(d, "System", "PaperForge", "cache", "ocr_maintenance.json");
}
function dt(d) {
  try {
    let l = mr(d),
      e = Oe.readFileSync(l, "utf-8");
    return JSON.parse(e);
  } catch (l) {
    return null;
  }
}
function Qr(d, l) {
  let e = mr(d),
    t = pt.dirname(e);
  (Oe.mkdirSync(t, { recursive: !0 }),
    Oe.writeFileSync(e, JSON.stringify(l, null, 2), "utf-8"));
}
function hr(d, l, e) {
  return new Promise((t, r) => {
    (0, gr.execFile)(d, l, e, (n, s) => {
      n ? r(n) : t(s);
    });
  });
}
async function Lt(d, l, e, t) {
  let r = await hr(l, [...e, "-m", "paperforge", "ocr", "list", "--manifest"], {
      cwd: d,
      timeout: 3e4,
    }),
    n = JSON.parse(r);
  if (t) {
    let u = Object.keys(t.manifest),
      _ = Object.keys(n);
    if (
      u.length === _.length &&
      u.every((h) => t.manifest[h] === n[h]) &&
      Object.values(t.papers).every(
        (f) => typeof f.needs_derived_rebuild == "boolean"
      )
    )
      return { data: Object.values(t.papers), changed: !1 };
  }
  let s = Object.keys(n),
    a = await hr(
      l,
      [...e, "-m", "paperforge", "ocr", "list", "--json", "--keys", ...s],
      { cwd: d, timeout: 3e4 }
    ),
    i = JSON.parse(a),
    c = Xr(n, i, t);
  return (Qr(d, c), { data: Object.values(c.papers), changed: !0 });
}
function Ot(d, l, e) {
  return !d ||
    typeof d != "object" ||
    !Object.prototype.hasOwnProperty.call(d, l)
    ? !!e
    : !!d[l];
}
function yr(d, l, e) {
  let t = !Ot(d, l, e);
  return (d && typeof d == "object" && (d[l] = t), t);
}
var en = ["EMBED", "OCR_REBUILD", "OCR_REDO"];
function Je(d, l) {
  var s, a;
  let t = (l + d).split(`
`),
    r = (s = t.pop()) != null ? s : "",
    n = [];
  for (let i of t)
    for (let c of en) {
      let p = c.length;
      if (i.startsWith(c + "_START:")) {
        let u = parseInt(i.slice(p + 7), 10) || 0;
        n.push({ prefix: c, event: "START", total: u });
        break;
      }
      if (i.startsWith(c + "_PROGRESS:")) {
        let _ = i.slice(p + 10).split(":");
        n.push({
          prefix: c,
          event: "PROGRESS",
          current: parseInt(_[0], 10) || 0,
          total: parseInt(_[1], 10) || 0,
          key: (a = _[2]) != null ? a : "",
        });
        break;
      }
      if (i === c + "_DONE" || i.startsWith(c + "_DONE:")) {
        n.push({ prefix: c, event: "DONE" });
        break;
      }
    }
  return { events: n, buffer: r };
}
function Ye(d) {
  return { app: { secretStorage: d.secretStorage }, saveData: async () => {} };
}
var Ce = class Ce extends A.PluginSettingTab {
  constructor(e, t) {
    super(e, t);
    this._saveTimeout = null;
    this._pfConfig = null;
    this._lastSyncTime = null;
    this._memoryStatusText = null;
    this._vectorDepsOk = null;
    this._embedStatusText = null;
    this._skillsCollapsed = { user: !0 };
    this._featurePanelsCollapsed = {};
    this._advCollapsed = !0;
    this._refreshPending = !1;
    this._pythonInterpDescEl = null;
    this._customPathDescEl = null;
    this._checkEl = null;
    this.activeTab = "overview";
    this._buildState = "idle";
    this._buildProgress = { current: 0, total: 0, key: "" };
    this._capabilityState = null;
    this._lastKnownState = new Map();
    this._navMemory = { destination: "overview" };
    this._probing = new Set();
    this._attemptedProbes = new Set();
    this._setupView = "overview";
    this._setupStage = 1;
    this._setupOptionals = { ocr: !1, memory: !1, agent: !1 };
    this._selectedDetailModule = "";
    this._focusTargetId = null;
    this._runtimeAbortController = null;
    this._managedRuntime = null;
    this._runtimeBusy = !1;
    this._libraryRunning = !1;
    this._dismissedMaintenanceItems = new Set();
    this._displayInProgress = !1;
    this._pendingMaintenanceRefresh = !1;
    this._maintenanceNoticeShown = !1;
    this._detailReturn = null;
    this.plugin = t;
  }
  _getOverviewModules() {
    return [
      { id: "installation", label: o("cc_module_foundation") || "Foundation" },
      { id: "library", label: o("cc_module_library") || "Library" },
      { id: "ocr", label: o("cc_module_ocr") || "OCR" },
      { id: "memory", label: o("cc_module_memory") || "Smart Retrieval" },
      { id: "agent", label: o("cc_module_agent") || "Agent Integration" },
    ];
  }
  _getUserModuleName(e) {
    let t =
      "cc_module_" +
      (e === "installation" ? "foundation" : e === "memory" ? "memory" : e);
    return o(t) || e.charAt(0).toUpperCase() + e.slice(1);
  }
  _refreshPfConfig() {
    this._pfConfig = this.plugin.readPaperforgeJson();
  }
  display() {
    this._displayInProgress = !0;
    let { containerEl: e } = this;
    if (
      (e.empty(),
      this._refreshPfConfig(),
      this._restoreNavMemory(),
      this._initCapabilityState(),
      this._applyStaleTolerance(),
      this.plugin.settings._setup_complete === !1)
    ) {
      (this._renderSetupJourney(e), (this._displayInProgress = !1));
      return;
    }
    if (!document.getElementById("paperforge-tab-styles")) {
      let a = document.createElement("style");
      ((a.id = "paperforge-tab-styles"),
        (a.textContent = `
                .paperforge-settings-tabs { display: flex; gap: 4px; margin-bottom: 16px; border-bottom: 1px solid var(--background-modifier-border); }
                .paperforge-settings-tab { padding: 6px 16px; border: none; background: none; cursor: pointer; border-bottom: 2px solid transparent; font-size: 14px; color: var(--text-muted); }
                .paperforge-settings-tab--active { color: var(--text-accent); border-bottom-color: var(--text-accent); }
                .paperforge-tab-content { display: none; }
                .paperforge-tab-content--active { display: block; }
                .paperforge-skills-collapse-header { display: flex !important; align-items: center; cursor: pointer; padding: 6px 0 !important; margin: 0 !important; }
                .paperforge-skills-collapse-header h4 { margin: 0 !important; }
                .paperforge-skills-collapse-content { margin: 0 !important; padding: 0 !important; }
                .paperforge-skills-group { margin-bottom: 10px; }
                .paperforge-skills-group:last-child { margin-bottom: 0; }
                .vertical-tab-content-container { overflow-y: scroll !important; }
                .paperforge-release-card { border: 1px solid var(--background-modifier-border); border-radius: 6px; padding: 12px; margin-bottom: 12px; }
                .paperforge-release-header { margin-bottom: 8px; }
                .paperforge-release-date { color: var(--text-muted); font-size: 12px; }
                .paperforge-release-section { margin-bottom: 6px; }
                .paperforge-release-label { font-weight: 600; color: var(--text-accent); margin-bottom: 2px; font-size: 13px; }
                .paperforge-release-item { font-size: 13px; margin-left: 8px; color: var(--text-muted); }
                .paperforge-release-item-bold { font-size: 13px; margin-left: 8px; font-weight: 600; color: var(--text-normal); }
                .paperforge-release-recommended { background: rgba(var(--color-orange-rgb, 255,166,0), 0.08); border-radius: 4px; padding: 6px 8px; }
                .paperforge-manual-links { margin-top: 8px; }
                .paperforge-manual-links a { color: var(--text-accent); }
                .paperforge-modal-item { font-size: 13px; margin-left: 8px; color: var(--text-muted); }
                .paperforge-migration-warning { border: 1px solid var(--text-warning); border-radius: 6px; padding: 10px 14px; margin-bottom: 12px; background: rgba(var(--color-yellow-rgb, 255, 208, 0), 0.08); color: var(--text-warning); font-size: 13px; }
                .paperforge-migration-warning strong { color: var(--text-warning); }
                .paperforge-migration-warning code { background: var(--background-modifier-border); padding: 1px 4px; border-radius: 3px; }
                .pf-maintenance-inbox { margin-bottom: 24px; container-type: inline-size; }
                .pf-maintenance-inbox-empty { color: var(--text-muted); font-style: italic; padding: 12px 0; }
                .pf-maintenance-inbox-summary { font-weight: 600; margin-bottom: 8px; }
                .pf-maintenance-inbox-list { display: flex; flex-direction: column; gap: 8px; }
                .pf-maintenance-inbox-item { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding: 8px 12px; border: 1px solid var(--background-modifier-border); border-radius: 6px; background: var(--background-primary); flex-wrap: wrap; }
                @container (max-width: 730px) { .pf-maintenance-inbox-item { flex-direction: column; } .pf-maintenance-inbox-item-actions { width: 100%; justify-content: flex-end; } }
                .pf-maintenance-inbox-item--dismissed { opacity: 0.45; }
                .pf-maintenance-inbox-item-info { flex: 1; min-width: 0; }
                .pf-maintenance-inbox-item-module { font-weight: 600; cursor: pointer; background: none; border: none; color: var(--text-accent); padding: 0; font-size: inherit; text-align: left; }
                .pf-maintenance-inbox-item-module:hover { text-decoration: underline; }
                .pf-maintenance-inbox-item-reason { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
                .pf-maintenance-inbox-item-activity { font-size: 11px; color: var(--text-accent); margin-top: 2px; }
                .pf-maintenance-inbox-item-actions { display: flex; align-items: center; gap: 6px; flex-shrink: 0; flex-wrap: wrap; }
                .pf-maintenance-inbox-item-badge { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: var(--background-modifier-border); white-space: nowrap; }
                .pf-maintenance-inbox-item-badge--warn { background: rgba(var(--color-yellow-rgb),0.15); color: var(--text-warning); }
                .pf-maintenance-inbox-item-badge--error { background: rgba(var(--color-red-rgb),0.12); color: var(--text-error); }
                .pf-maintenance-inbox-item-badge--unknown { background: var(--background-modifier-border); color: var(--text-muted); }
                .pf-maintenance-inbox-item-action { font-size: 12px; padding: 3px 10px; cursor: pointer; }
                .pf-maintenance-inbox-item-dismiss { font-size: 11px; padding: 2px 6px; background: none; border: 1px solid var(--background-modifier-border); border-radius: 4px; cursor: pointer; color: var(--text-muted); }
                .paperforge-confirm-effect { margin: 8px 0; font-size: 13px; }
                .paperforge-confirm-effect-label { font-weight: 600; }
                .paperforge-confirm-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px; }
                .paperforge-issue-draft-desc { font-size: 13px; color: var(--text-muted); margin-bottom: 12px; }
                .paperforge-issue-draft-field { margin-bottom: 12px; }
                .paperforge-issue-draft-field label { display: block; font-weight: 600; margin-bottom: 4px; font-size: 13px; }
                .paperforge-issue-draft-input { width: 100%; padding: 6px 8px; border: 1px solid var(--background-modifier-border); border-radius: 4px; font-size: 13px; }
                .paperforge-issue-draft-textarea { width: 100%; padding: 6px 8px; border: 1px solid var(--background-modifier-border); border-radius: 4px; font-size: 13px; resize: vertical; min-height: 120px; }
                .paperforge-issue-draft-preview { margin: 12px 0; padding: 8px 12px; background: var(--background-secondary); border-radius: 6px; font-size: 12px; }
                .paperforge-issue-draft-preview-label { font-weight: 600; }
                .paperforge-issue-draft-included { color: var(--text-success); margin-bottom: 2px; }
                .paperforge-issue-draft-redacted { color: var(--text-warning); }
                .paperforge-issue-draft-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px; }
            `),
        document.head.appendChild(a));
    }
    let t = this.plugin.settings._migration_warnings;
    if (Array.isArray(t) && t.length > 0) {
      let a = e.createDiv({ cls: "paperforge-migration-warning" }),
        i = t
          .map((c) => (c === "paddleocr_api_key" ? "OCR" : "Smart Retrieval"))
          .join(", ");
      (a.createEl("strong", {
        text: o("migration_banner_title") || "Credential Migration Notice",
      }),
        a.createEl("p", {
          text: `One or more credentials could not be automatically migrated (${i}). Your existing keys are preserved in plaintext and remain functional. To complete the migration, re-enter the affected keys in the Settings fields below.`,
        }),
        a.createEl("p", {
          text: "After re-entering, save settings. The plugin will retry migration on next restart.",
          cls: "paperforge-manual-links",
        }));
    }
    let r = e.createDiv({ cls: "paperforge-settings-tabs" }),
      n = [
        { id: "overview", label: o("tab_overview") || "Overview" },
        { id: "maintenance", label: o("tab_maintenance") || "Maintenance" },
        { id: "help", label: o("tab_help") || "Help" },
      ],
      s = {};
    if (
      (n.forEach((a) => {
        r.createEl("button", {
          cls:
            "paperforge-settings-tab" +
            (a.id === this.activeTab ? " paperforge-settings-tab--active" : ""),
          text: a.label,
        }).addEventListener("click", () => {
          (a.id === "maintenance"
            ? ((this._maintenanceNoticeShown = !1),
              (this._focusTargetId = "#pf-maintenance-heading"))
            : (this._detailReturn = null),
            (this.activeTab = a.id),
            (this._navMemory = { destination: a.id }),
            this._persistNavMemory(),
            this.display());
        });
      }),
      n.forEach((a) => {
        s[a.id] = e.createDiv({
          cls:
            "paperforge-tab-content" +
            (a.id === this.activeTab ? " paperforge-tab-content--active" : ""),
        });
      }),
      (s["module-detail"] = e.createDiv({
        cls:
          "paperforge-tab-content" +
          (this.activeTab === "module-detail"
            ? " paperforge-tab-content--active"
            : ""),
      })),
      this.activeTab === "overview"
        ? this._renderOverviewTab(s.overview)
        : this.activeTab === "module-detail"
          ? this._renderModuleDetailTab(s["module-detail"])
          : this.activeTab === "maintenance"
            ? this._renderMaintenanceTab(s.maintenance)
            : this.activeTab === "help" && this._renderHelpTab(s.help),
      this._focusTargetId && this.activeTab !== "help")
    ) {
      let a = e.querySelector(this._focusTargetId);
      if (
        (!a &&
          this.activeTab === "overview" &&
          (a = e.querySelector(".pf-cc-card")),
        a)
      ) {
        try {
          a.focus();
        } catch (i) {}
        this._focusTargetId = null;
      }
    }
    this._displayInProgress = !1;
  }
  _renderOverviewTab(e) {
    var r;
    let t = this._getVaultBasePath();
    (this.plugin.settings.vault_path ||
      ((this.plugin.settings.vault_path = t), this._debouncedSave()),
      e.createEl("h2", { text: o("header_title") || "PaperForge" }),
      e.createEl("p", { text: o("desc"), cls: "paperforge-settings-desc" }),
      this._renderControlCenter(e));
    for (let n of je) {
      let s = (r = this._capabilityState) == null ? void 0 : r[n];
      s &&
        s.capability_state === "unknown" &&
        s.updated_at === new Date(0).toISOString() &&
        !this._attemptedProbes.has(n) &&
        (this._attemptedProbes.add(n),
        n !== "maintenance" && this._probeModule(n));
    }
  }
  _getVaultBasePath() {
    let e = this.app.vault.adapter;
    if (e && typeof e == "object" && "basePath" in e) {
      let t = e.basePath;
      return typeof t == "string" ? t : "";
    }
    return "";
  }
  _ensureManagedRuntime() {
    var e, t, r;
    return this._managedRuntime
      ? this._managedRuntime
      : ((this._managedRuntime =
          (r =
            (t = (e = this.plugin).getManagedRuntime) == null
              ? void 0
              : t.call(e)) != null
            ? r
            : new Ee({ version: this.plugin.manifest.version })),
        this._managedRuntime);
  }
  _resolveRuntimeCommand(e) {
    let t = xe(this._ensureManagedRuntime().current());
    return t ? { path: t.command, args: [...t.args] } : null;
  }
  _renderInstallationDetail(e) {
    var w, R;
    e.createEl("button", {
      cls: "pf-back-btn",
      text: o("btn_back_to_overview"),
    }).addEventListener("click", () => {
      var S;
      (((S = this._detailReturn) == null ? void 0 : S.tab) === "maintenance"
        ? ((this.activeTab = this._detailReturn.tab),
          (this._focusTargetId = this._detailReturn.selector),
          (this._detailReturn = null))
        : ((this.activeTab = "overview"),
          (this._focusTargetId =
            "button.pf-open-module-btn[data-module=installation]")),
        (this._selectedDetailModule = ""),
        this.display());
    });
    let r = e.createEl("h2", {
        cls: "pf-installation-detail-heading",
        text: o("installation_detail_heading") || "Installation Details",
        attr: { id: "pf-installation-detail-heading", tabindex: "-1" },
      }),
      n = [
        {
          id: "installation",
          labelKey: "md_select_installation",
          disabled: !1,
        },
      ],
      s = e.createEl("div", { cls: "pf-module-detail-selector" });
    for (let S of n) {
      let T = s.createEl("button", {
        cls:
          "pf-module-detail-btn" +
          (S.id === "installation" ? " pf-module-detail-btn--active" : "") +
          (S.disabled ? " pf-module-detail-btn--disabled" : ""),
        text: o(S.labelKey),
      });
      S.disabled && (T.disabled = !0);
    }
    let a = (w = this._capabilityState) != null ? w : {},
      i = "installation",
      c = (R = a[i]) != null ? R : oe(i),
      p = this._sevClass(c.severity),
      u = ze(c),
      _ = e.createEl("div", {
        cls: "pf-cc-card pf-open-module-btn",
        attr: { style: "margin-bottom: 12px;" },
      }),
      g = _.createEl("div", { cls: "pf-cc-card-header" });
    (g.createEl("span", {
      cls: "pf-cc-card-name",
      text: o("cc_module_installation"),
    }),
      g.createEl("span", {
        cls: `pf-cc-card-badge pf-cc-card-badge--${p}`,
        text: o(this._ccBadgeKey(c, i)),
      }));
    let h = this._localizeReason(c.reason.code, "installation");
    if (
      (_.createEl("div", {
        cls: "pf-cc-card-reason",
        text: h != null ? h : c.reason.text,
      }),
      c.action.primary && !u)
    ) {
      let S = Ke(c),
        F =
          S.kind === "setup"
            ? "pf-cc-card-action pf-cc-card-action--primary"
            : "pf-cc-card-action";
      _.createEl("button", { cls: F, text: S.label }).addEventListener(
        "click",
        () => {
          S.kind === "setup"
            ? new ke(this.app, this.plugin, () => {
                (this._probeModule("installation"), this._probeModule("help"));
              }).open()
            : this._probeModule(i);
        }
      );
    }
    e.createEl("h3", { text: o("managed_runtime_status") });
    let f = e.createEl("div", { cls: "pf-runtime-status-card" }),
      v = (S, T, F) => {
        let M = f.createEl("div", { cls: "pf-runtime-actions" });
        for (let P of S) {
          let L = M.createEl("button", {
            cls: "pf-runtime-action-btn",
            text: P.label,
          });
          (F && P.verb !== "stop" && (L.disabled = !0),
            L.addEventListener("click", async () => {
              var K;
              if (P.verb === "stop") {
                let V = this._runtimeAbortController;
                if (!V || V.signal.aborted) return;
                (V.abort(),
                  new A.Notice(o("managed_runtime_action_cancelled")),
                  this.display(),
                  this._probeModule("installation"),
                  this._probeModule("help"));
                return;
              }
              let C = this._ensureManagedRuntime(),
                I = new AbortController();
              ((this._runtimeAbortController = I),
                (this._runtimeBusy = !0),
                new A.Notice(o("managed_runtime_running")));
              try {
                (P.verb === "install" ||
                P.verb === "repair" ||
                P.verb === "update"
                  ? await C.ensure({
                      signal: I.signal,
                      force: P.verb === "update" || P.verb === "repair",
                    })
                  : P.verb === "rollback"
                    ? await C.ensure({
                        signal: I.signal,
                        version: (K = T.previousVersion) != null ? K : void 0,
                      })
                    : await C.status(),
                  I.signal.aborted ||
                    new A.Notice(o("managed_runtime_action_complete")));
              } catch (V) {
                if ((V == null ? void 0 : V.name) !== "AbortError") {
                  let N = V instanceof Error ? V.message : String(V);
                  new A.Notice(
                    o("managed_runtime_action_failed").replace("{error}", N),
                    8e3
                  );
                }
              } finally {
                ((this._runtimeAbortController = null),
                  (this._runtimeBusy = !1),
                  this._probeModule("installation"),
                  this._probeModule("help"),
                  this.display());
              }
            }));
        }
      },
      y = () => {
        var C;
        f.empty();
        let T = this._ensureManagedRuntime().current(),
          F = f.createEl("div", { cls: "pf-runtime-status-header" });
        F.createEl("div", {
          cls: "pf-runtime-status-label",
          text: o("managed_runtime_status"),
        });
        let M, P;
        switch (T.state) {
          case "ready":
            ((M = "ok"), (P = o("managed_runtime_ok_state")));
            break;
          case "not_installed":
            ((M = "warn"), (P = o("managed_runtime_not_installed")));
            break;
          case "needs_repair":
            ((M = "warn"), (P = o("managed_runtime_needs_repair")));
            break;
          case "unavailable":
            ((M = "error"), (P = o("managed_runtime_unavailable")));
            break;
          default:
            ((M = "unknown"), (P = o("managed_runtime_unknown_state")));
        }
        if (
          (F.createEl("span", {
            cls: `pf-runtime-status-state pf-runtime-status-state--${M}`,
            text: P,
          }),
          T.version &&
            f.createEl("div", { cls: "pf-meta", text: `Python ${T.version}` }),
          T.pythonPath &&
            f.createEl("div", {
              cls: "pf-meta",
              text: T.pythonPath,
              attr: { style: "word-break: break-all;" },
            }),
          T.lastVerifiedAt &&
            f.createEl("div", {
              cls: "pf-meta",
              text: o("managed_runtime_last_verified").replace(
                "{time}",
                new Date(T.lastVerifiedAt).toLocaleString()
              ),
            }),
          T.error &&
            f.createEl("div", {
              cls: "pf-runtime-error",
              text: `${T.error.code}: ${T.error.message}`,
            }),
          T.warnings && T.warnings.length > 0)
        )
          for (let I of T.warnings) {
            let K = f.createEl("div", {
              cls: "pf-runtime-warning",
              text: `\u26A0 ${I.message}`,
            });
            I.platformAction &&
              K.createEl("div", {
                cls: "pf-runtime-warning-action",
                text: I.platformAction,
              });
          }
        (C = T.error) != null &&
          C.platformAction &&
          f.createEl("div", {
            cls: "pf-runtime-error-action",
            text: T.error.platformAction,
          });
        let L = pr(T, this.plugin.manifest.version, this._runtimeBusy);
        v(L, T, this._runtimeBusy);
      };
    y();
    let m = this._ensureManagedRuntime().status();
    (m &&
      m
        .then(() => {
          e.isConnected && y();
        })
        .catch(() => {}),
      e.createEl("h3", {
        text: o("section_config") || "Current Configuration",
      }));
    let E = this._getVaultBasePath(),
      k = this._resolveRuntimeCommand(E),
      b = k
        ? this._getPythonDesc(k.path, "managed")
        : "Python runtime not ready \u2014 install via Managed Runtime above";
    new A.Setting(e)
      .setName(o("field_python_interp") || "Python Interpreter")
      .setDesc(b)
      .addExtraButton((S) => {
        S.setIcon("reset")
          .setTooltip("Re-detect")
          .onClick(() => {
            ((this._pythonInterpDescEl = null),
              (this._managedRuntime = null),
              this.display());
          });
      })
      .addButton((S) => {
        S.setButtonText(o("runtime_health_sync") || "Sync Runtime").onClick(
          async () => {
            (S.setDisabled(!0),
              S.setButtonText(o("runtime_health_syncing")),
              await this._ensureManagedRuntime().ensure(),
              this.display());
          }
        );
      });
    let x = e.createEl("div", { cls: "setting-item-description" });
    ((this._customPathDescEl = x),
      new A.Setting(e)
        .setName(o("field_python_custom") || "Custom Python Path")
        .setDesc(o("optional_later"))
        .addText((S) => {
          S.setPlaceholder("e.g. C:\\Python311\\python.exe")
            .setValue(this.plugin.settings.python_path || "")
            .onChange((T) => {
              ((this.plugin.settings.python_path = T.trim()),
                this._debouncedSave(),
                (this._managedRuntime = null));
            });
        })
        .addButton((S) => {
          S.setButtonText(o("feat_verify") || "Validate").onClick(() => {
            this._validatePythonOverride();
          });
        }),
      new A.Setting(e)
        .setName(o("field_zotero_data") || "Zotero Data Dir")
        .setDesc(o("field_zotero_placeholder"))
        .addText((S) => {
          S.setPlaceholder("C:\\Users\\...\\Zotero")
            .setValue(this.plugin.settings.zotero_data_dir || "")
            .onChange((T) => {
              ((this.plugin.settings.zotero_data_dir = T.trim()),
                this._debouncedSave());
            });
        }),
      e.createEl("h3", {
        text: o("agent_integration_section") || "Agent Integration",
      }));
    try {
      r.focus();
    } catch (S) {}
  }
  _renderSkillsList(e) {
    let t = {
        opencode: "OpenCode",
        claude: "Claude Code",
        codex: "Codex",
        cursor: "Cursor",
        windsurf: "Windsurf",
        github_copilot: "GitHub Copilot",
        gemini: "Gemini CLI",
      },
      r = {
        opencode: ".opencode/skills",
        claude: ".claude/skills",
        codex: ".codex/skills",
        cursor: ".cursor/skills",
        windsurf: ".windsurf/skills",
        github_copilot: ".github/skills",
        gemini: ".gemini/skills",
      },
      n = this._getVaultBasePath(),
      s = this.plugin.settings.agent_platform || "opencode";
    (new A.Setting(e)
      .setName(o("label_agent") || "Agent Platform")
      .setDesc(o("feat_agent_platform_desc"))
      .addDropdown((g) => {
        (Object.entries(t).forEach(([h, f]) => g.addOption(h, f)),
          g.setValue(s).onChange((h) => {
            ((this.plugin.settings.agent_platform = h),
              this.plugin.saveSettings(),
              this.display());
          }));
      })
      .addExtraButton((g) => {
        g.setIcon("folder")
          .setTooltip("Open skills folder")
          .onClick(() => {
            let h = r[s] || ".opencode/skills",
              f = te.join(n, h);
            G.existsSync(f)
              ? (0, ee.exec)(`start "" "${f}"`)
              : new A.Notice(`Skills folder not found: ${h}`);
          });
      }),
      e.createEl("h3", { text: "Skills" }));
    let a = e.createEl("div", { cls: "paperforge-desc-box" });
    (a.setText(o("feat_skills_desc")),
      a.createEl("br"),
      a.createEl("span", { text: o("feat_skills_system") }));
    let i = te.join(n, r[s]),
      c = [],
      p = [];
    G.existsSync(i) &&
      G.readdirSync(i, { withFileTypes: !0 }).forEach((g) => {
        if (!g.isDirectory()) return;
        let h = te.join(i, g.name, "SKILL.md");
        if (!G.existsSync(h)) return;
        let f = G.readFileSync(h, "utf-8"),
          v = f.match(/^name:\s*(.+)$/m),
          y = f.split(`
`),
          m = y.findIndex((R) => /^description:/.test(R)),
          E = "";
        if (m >= 0) {
          let R = y[m].match(/^description:\s*(.+)$/);
          if (R && R[1] && R[1] !== ">" && R[1] !== "|-" && R[1] !== "|")
            E = R[1].trim();
          else {
            for (
              let S = m + 1;
              S < y.length && (/^\s{2,}/.test(y[S]) || y[S].trim() === "");
              S++
            )
              E += y[S].trim() + " ";
            E = E.trim();
          }
        }
        let k = f.match(/^source:\s*(.+)$/m),
          b = f.match(/^disable-model-invocation:\s*(.+)$/m),
          x = f.match(/^version:\s*(.+)$/m),
          w = {
            name: v ? v[1].trim() : g.name,
            desc: E,
            source: k ? k[1].trim() : "user",
            disabled: !!b && b[1].trim() === "true",
            version: x ? x[1].trim() : "",
            path: h,
            content: f,
            dirName: g.name,
          };
        w.source === "paperforge" ? c.push(w) : p.push(w);
      });
    let u = e.createEl("div", { cls: "paperforge-skills-box" }),
      _ = (g, h, f) => {
        if (h.length === 0) return;
        let v = u.createEl("div", { cls: "paperforge-skills-group" }),
          y = v.createEl("div", { cls: "paperforge-skills-collapse-header" }),
          m = v.createEl("div", { cls: "paperforge-skills-collapse-content" }),
          E = y.createEl("span", {
            text: "\u25BC",
            cls: "paperforge-skills-arrow",
          });
        (y.createEl("h4", {
          text: `${g} (${h.length})`,
          cls: "paperforge-skills-subheader",
        }),
          h.forEach((x) => {
            let w = x.name + (x.version ? " v" + x.version : ""),
              R = f ? " [system]" : " [user]",
              S = x.desc || "",
              T = new A.Setting(m).setName(w + R).setDesc(S);
            ((T.settingEl.style.opacity = x.disabled ? "0.4" : "1"),
              T.addToggle((F) => {
                F.setValue(!x.disabled).onChange((M) => {
                  let P = !M,
                    C = x.content.match(/^disable-model-invocation:\s*(.+)$/m)
                      ? x.content.replace(
                          /^disable-model-invocation:\s*.+$/m,
                          `disable-model-invocation: ${P}`
                        )
                      : x.content.replace(
                          /^(---\r?\n)/,
                          `$1disable-model-invocation: ${P}
`
                        );
                  (G.writeFileSync(x.path, C, "utf-8"),
                    (x.disabled = P),
                    (x.content = C),
                    (T.settingEl.style.opacity = x.disabled ? "0.4" : "1"));
                });
              }));
          }));
        let k = f ? "system" : "user";
        ((this._skillsCollapsed[k] || !1) &&
          ((m.style.display = "none"), (E.style.transform = "rotate(-90deg)")),
          y.addEventListener("click", () => {
            (m.style.display !== "none"
              ? ((m.style.display = "none"),
                (E.style.transform = "rotate(-90deg)"))
              : ((m.style.display = ""), (E.style.transform = "rotate(0deg)")),
              (this._skillsCollapsed[k] = m.style.display === "none"));
          }));
      };
    (_("System Skills", c, !0),
      _("User Skills", p, !1),
      c.length === 0 &&
        p.length === 0 &&
        u.createEl("p", {
          text: `No skills found in ${r[s]}. Run setup to deploy skills.`,
          cls: "setting-item-description",
        }));
  }
  _renderModuleDetailTab(e) {
    (this._selectedDetailModule ||
      (this._selectedDetailModule = "installation"),
      this._selectedDetailModule === "installation"
        ? this._renderInstallationDetail(e)
        : this._selectedDetailModule === "library"
          ? this._renderLibraryDetail(e)
          : this._selectedDetailModule === "ocr"
            ? this._renderOcrDetail(e)
            : this._selectedDetailModule === "memory"
              ? this._renderMemoryDetail(e)
              : this._selectedDetailModule === "agent"
                ? this._renderAgentDetail(e)
                : ((this._selectedDetailModule = "installation"),
                  this._renderInstallationDetail(e)));
  }
  _renderLibraryDetail(e) {
    var n, s, a, i, c;
    this._renderModuleDetailShell(e, "library");
    let t =
        (s = (n = this._capabilityState) == null ? void 0 : n.library) != null
          ? s
          : oe("library"),
      r = e.createDiv({ cls: "pf-module-body" });
    (r.createEl("h3", {
      text: o("md_library_connection") || "Zotero Connection",
    }),
      t.user_state === "ready"
        ? r.createEl("p", {
            text:
              o("md_library_ready") ||
              "Zotero is connected and literature is up to date.",
            cls: "pf-status-ok",
          })
        : t.user_state === "action_required" &&
          rt(r, {
            whatHappened: "Library needs attention",
            impact: t.user_impact || "Literature may be out of date.",
            nextStep:
              ((i = (a = t.action) == null ? void 0 : a.primary) == null
                ? void 0
                : i.label) || "Check configuration.",
            reasonCode: (c = t.reason) == null ? void 0 : c.code,
            onCopyDiagnostic: () => this._buildAndCopyDiagnostic(),
          }),
      t.activity_state === "running" &&
        t.activity_label &&
        (r.createEl("h4", {
          text: o("md_current_activity") || "Current Activity",
        }),
        qe(r, { label: t.activity_label, progress: t.activity_progress })),
      t.updated_at &&
        t.updated_at !== new Date(0).toISOString() &&
        r.createEl("p", {
          cls: "pf-last-known",
          text:
            (o("cc_last_checked") || "Last checked: ") +
            new Date(t.updated_at).toLocaleString(),
        }),
      r.createEl("h4", { text: o("md_configuration") || "Configuration" }),
      qt(r, {
        items: [
          {
            label: "Zotero data directory",
            value: this.plugin.settings.zotero_data_dir || "Not configured",
          },
        ],
        onChangeLabel: "Change",
        onChange: () => {
          new ke(this.app, this.plugin, () => {
            this._probeModule("library");
          }).open();
        },
      }));
  }
  _renderOcrDetail(e) {
    var s, a, i, c, p;
    this._renderModuleDetailShell(e, "ocr");
    let t =
        (a = (s = this._capabilityState) == null ? void 0 : s.ocr) != null
          ? a
          : oe("ocr"),
      r = e.createDiv({ cls: "pf-module-body" });
    if (
      (r.createEl("h3", { text: o("md_ocr_status") || "OCR Status" }),
      t.user_state === "ready"
        ? r.createEl("p", {
            text: o("md_ocr_ready") || "OCR pipeline is functional.",
            cls: "pf-status-ok",
          })
        : t.user_state === "action_required" &&
          rt(r, {
            whatHappened: "OCR needs attention",
            impact: t.user_impact || "Some papers may have issues.",
            nextStep:
              ((c = (i = t.action) == null ? void 0 : i.primary) == null
                ? void 0
                : c.label) || "Check.",
            reasonCode: (p = t.reason) == null ? void 0 : p.code,
            onCopyDiagnostic: () => this._buildAndCopyDiagnostic(),
          }),
      t.activity_state === "running" &&
        t.activity_label &&
        qe(r, { label: t.activity_label, progress: t.activity_progress }),
      this.plugin._ocrProcess != null)
    ) {
      let u = e.createEl("div", { cls: "pf-detail-controls" });
      u.createEl("button", {
        cls: "mod-warning",
        text: o("ocr_stop_batch") || "Stop OCR batch",
      }).addEventListener("click", () => {
        var f;
        let h = this.plugin._ocrProcess;
        (f = h == null ? void 0 : h.stdin) != null && f.write
          ? (h.stdin.write(`PAPERFORGE_STOP
`),
            (this.plugin._ocrWasStopped = !0))
          : h != null && h.kill && h.kill("SIGINT");
      });
      let g = this.plugin._ocrProgress;
      g &&
        g.total > 0 &&
        u.createEl("span", {
          cls: "pf-detail-progress",
          text: `${g.current}/${g.total} papers`,
        });
    }
  }
  _renderAgentDetail(e) {
    (e.createEl("h2", {
      text: o("md_agent_integration") || "Agent Integration",
    }),
      Ue(e, "not_enabled"),
      e.createEl("p", {
        text:
          o("md_agent_placeholder") ||
          "Agent Integration will be available in a future update.",
      }),
      le(e, {
        label: o("md_copy_diagnostic") || "Copy Diagnostic",
        onClick: () => this._buildAndCopyDiagnostic(),
      }));
  }
  _renderMemoryDetail(e) {
    var n, s, a, i, c;
    this._renderModuleDetailShell(e, "memory");
    let t =
        (s = (n = this._capabilityState) == null ? void 0 : n.memory) != null
          ? s
          : oe("memory"),
      r = e.createDiv({ cls: "pf-module-body" });
    (r.createEl("h3", {
      text: o("md_retrieval_coverage") || "Retrieval Coverage",
    }),
      t.user_state === "ready"
        ? r.createEl("p", {
            text:
              o("md_retrieval_ready") ||
              "All papers are indexed and searchable.",
            cls: "pf-status-ok",
          })
        : t.user_state === "action_required" &&
          rt(r, {
            whatHappened: "Smart Retrieval needs attention",
            impact: t.user_impact || "Search may not work.",
            nextStep:
              ((i = (a = t.action) == null ? void 0 : a.primary) == null
                ? void 0
                : i.label) || "Rebuild index.",
            reasonCode: (c = t.reason) == null ? void 0 : c.code,
            onCopyDiagnostic: () => this._buildAndCopyDiagnostic(),
          }),
      t.activity_state === "running" &&
        t.activity_label &&
        qe(r, { label: t.activity_label, progress: t.activity_progress }));
  }
  _dispatchModuleAction(e, t) {
    var a, i, c, p;
    let r = (a = t.action) == null ? void 0 : a.primary;
    if (!r) {
      this._probeModule(e);
      return;
    }
    let n = r.verb,
      s = (i = r.command) != null ? i : "";
    if (r.safety_class !== "safe" && r.confirmation_required) {
      new ot(
        this.app,
        {
          title: r.label,
          effectLabel:
            (c =
              (r.replacement_facts || []).join("; ") ||
              r.confirmation_prompt) != null
              ? c
              : "Proceed?",
        },
        () => {
          var u;
          this._runAllowedDispatch(
            e,
            r.verb,
            (u = r.command) != null ? u : "",
            t
          );
        }
      ).open();
      return;
    }
    this._runAllowedDispatch(e, r.verb, (p = r.command) != null ? p : "", t);
  }
  _runAllowedDispatch(e, t, r, n) {
    var s, a, i;
    if (
      (t === "setup" || t === "set_config") &&
      r === "paperforge setup" &&
      (e === "installation" || e === "library" || e === "ocr")
    ) {
      let c = [e];
      (e === "installation" && c.push("help"),
        new ke(this.app, this.plugin, () => {
          for (let p of c) this._probeModule(p);
        }).open());
      return;
    }
    if (t === "probe" && r === "probe " + e) {
      this._probeModule(e);
      return;
    }
    if (e !== "installation") {
      if (e === "library") {
        if (t === "sync" && r === "paperforge sync") {
          this._runManualSync();
          return;
        }
      } else if (e === "ocr") {
        if (t === "run" && r === "paperforge ocr run") {
          this._dispatchOcrAction("run");
          return;
        }
        if (t === "rebuild_derived" && r === "paperforge ocr rebuild --all") {
          this._dispatchOcrAction("rebuild");
          return;
        }
        if (t === "redo" && r === "paperforge ocr redo") {
          this._dispatchOcrAction("redo");
          return;
        }
        if (t === "investigate") {
          if (r === "paperforge ocr issue-draft") {
            let c = this._getVaultBasePath(),
              p = fr(
                n.reason.code,
                n.reason.text,
                (i =
                  (a = (s = n.action) == null ? void 0 : s.primary) == null
                    ? void 0
                    : a.scope_count) != null
                  ? i
                  : 0,
                c
              );
            new lt(
              this.app,
              p,
              "https://github.com/LLLin000/PaperForge/issues/new"
            ).open();
            return;
          }
          if (r === "paperforge ocr doctor") {
            this._callPython(["ocr", "doctor"], {
              timeout: 3e4,
              onClose: (c) => {
                (this._probeModule("ocr"), this.display());
              },
            });
            return;
          }
          if (r === "paperforge ocr list --json") {
            this._callPython(["ocr", "list", "--json"], {
              timeout: 3e4,
              onClose: (c) => {
                (this._probeModule("ocr"), this.display());
              },
            });
            return;
          }
        }
      } else if (e === "memory") {
        if (
          (t === "run" || t === "rebuild_index") &&
          r === "paperforge memory build"
        ) {
          this._dispatchMemoryBuild("build");
          return;
        }
        if (t === "rebuild_index" && r === "paperforge embed build --force") {
          this._dispatchMemoryBuild("embed");
          return;
        }
        if (
          t === "restore_backup" &&
          r === "paperforge memory restore-backup"
        ) {
          this._callPython(["memory", "restore-backup"], {
            timeout: 3e4,
            onClose: (c) => {
              (this._probeModule("memory"), this.display());
            },
          });
          return;
        }
      }
    }
    (new A.Notice(
      (o("action_unknown_pair") || "Unknown action: {verb}").replace(
        "{verb}",
        t
      ),
      5e3
    ),
      this._probeModule(e));
  }
  _dispatchOcrAction(e) {
    var c;
    let t = this.app.vault.adapter.basePath;
    if (!this._resolveRuntimeCommand(t)) {
      new A.Notice(o("runtime_not_available") || "No Python runtime available");
      return;
    }
    let n =
        e === "run"
          ? ["ocr", "run"]
          : e === "rebuild"
            ? ["ocr", "rebuild", "--all"]
            : ["ocr", "redo"],
      s = {
        run: "Running OCR\u2026",
        rebuild: "Rebuilding OCR derived artifacts\u2026",
        redo: "Running OCR redo\u2026",
      },
      a = (c = this._capabilityState) != null ? c : {};
    (a.ocr &&
      ((a.ocr.activity_state = "running"),
      (a.ocr.activity_label = s[e] || "Running\u2026"),
      (a.ocr.activity_progress = { current: 0, total: 1 })),
      (this.plugin._ocrBuffer = ""),
      (this.plugin._ocrProgress = { current: 0, total: 1, key: "" }),
      (this.plugin._ocrWasStopped = !1),
      this.display());
    let i = this._callPython(n, {
      stream: !0,
      onData: (p) => {
        var h;
        let u =
            typeof p == "string"
              ? p
              : Buffer.isBuffer(p)
                ? p.toString("utf-8")
                : String(p),
          { events: _, buffer: g } = Je(
            u,
            (h = this.plugin._ocrBuffer) != null ? h : ""
          );
        this.plugin._ocrBuffer = g;
        for (let f of _)
          f.event === "START"
            ? (this.plugin._ocrProgress &&
                (this.plugin._ocrProgress.total = f.total || 1),
              a.ocr &&
                (a.ocr.activity_progress = { current: 0, total: f.total || 1 }))
            : f.event === "PROGRESS" &&
              ((this.plugin._ocrProgress = {
                current: f.current || 0,
                total: f.total || 1,
                key: f.key || "",
              }),
              a.ocr &&
                (a.ocr.activity_progress = {
                  current: f.current || 0,
                  total: f.total || 1,
                }));
        this.display();
      },
      onError: (p) => {
        ((this.plugin._ocrProcess = null),
          a.ocr &&
            ((a.ocr.activity_state = "idle"),
            (a.ocr.activity_label = null),
            (a.ocr.activity_progress = null)),
          new A.Notice("OCR error: " + (p.message || p), 8e3),
          this._probeModule("ocr"),
          this.display());
      },
      onClose: (p) => {
        ((this.plugin._ocrProcess = null),
          a.ocr &&
            ((a.ocr.activity_state = "idle"),
            (a.ocr.activity_label = null),
            (a.ocr.activity_progress = null)),
          p === 0
            ? new A.Notice(
                e === "run"
                  ? "OCR run complete."
                  : e === "rebuild"
                    ? "OCR rebuild complete."
                    : "OCR redo complete."
              )
            : p === 130 || this.plugin._ocrWasStopped
              ? ((this.plugin._ocrWasStopped = !1),
                new A.Notice("OCR batch stopped by user."))
              : new A.Notice(
                  "OCR operation failed with exit code " +
                    (p != null ? p : "?"),
                  8e3
                ),
          this._probeModule("ocr"),
          this.display());
      },
    });
    this.plugin._ocrProcess = i;
  }
  _dispatchMemoryBuild(e) {
    var a;
    let t = this.app.vault.adapter.basePath,
      r = (a = this._capabilityState) != null ? a : {};
    (r.memory &&
      ((r.memory.activity_state = "running"),
      (r.memory.activity_label =
        e === "embed"
          ? "Building vector index\u2026"
          : "Building memory\u2026")),
      this.display());
    let n = e === "embed" ? ["embed", "build", "--force"] : ["memory", "build"],
      s = e === "embed" ? "Vector index" : "Memory";
    if (e === "embed") {
      ((this.plugin._embedBuffer = ""),
        (this.plugin._embedProgress = { current: 0, total: 0, key: "" }));
      let i = this._callPython(n, {
        stream: !0,
        onData: (c) => {
          var g;
          let p =
              typeof c == "string"
                ? c
                : Buffer.isBuffer(c)
                  ? c.toString("utf-8")
                  : String(c),
            { events: u, buffer: _ } = Je(
              p,
              (g = this.plugin._embedBuffer) != null ? g : ""
            );
          this.plugin._embedBuffer = _;
          for (let h of u)
            h.event === "PROGRESS" &&
              ((this.plugin._embedProgress = {
                current: h.current || 0,
                total: h.total || 0,
                key: h.key || "",
              }),
              r.memory &&
                (r.memory.activity_progress = {
                  current: h.current || 0,
                  total: h.total || 1,
                }));
          this.display();
        },
        onError: (c) => {
          ((this.plugin._embedProcess = null),
            r.memory &&
              ((r.memory.activity_state = "idle"),
              (r.memory.activity_label = null),
              (r.memory.activity_progress = null)),
            new A.Notice(s + " build error: " + (c.message || c), 8e3),
            this._probeModule("memory"),
            this.display());
        },
        onClose: (c) => {
          ((this.plugin._embedProcess = null),
            r.memory &&
              ((r.memory.activity_state = "idle"),
              (r.memory.activity_label = null),
              (r.memory.activity_progress = null)),
            c === 0
              ? new A.Notice(s + " build complete.")
              : new A.Notice(
                  s + " build failed with exit code " + (c != null ? c : "?"),
                  8e3
                ),
            this._probeModule("memory"),
            this.display());
        },
      });
      this.plugin._embedProcess = i;
    } else
      this._callPython(n, {
        timeout: 12e4,
        onClose: (i, c, p) => {
          (r.memory &&
            ((r.memory.activity_state = "idle"),
            (r.memory.activity_label = null)),
            i === 0
              ? new A.Notice(s + " rebuild complete")
              : new A.Notice(
                  s + " build failed" + (p ? ": " + p.slice(0, 120) : ""),
                  8e3
                ),
            this._probeModule("memory"),
            this.display());
        },
      });
  }
  _renderModuleDetailShell(e, t) {
    var T, F, M;
    let r = t + "_detail_heading",
      n = "pf-" + t + "-detail-heading";
    e.createEl("button", {
      cls: "pf-back-btn",
      text: o("btn_back_to_overview"),
    }).addEventListener("click", () => {
      var P;
      (((P = this._detailReturn) == null ? void 0 : P.tab) === "maintenance"
        ? ((this.activeTab = this._detailReturn.tab),
          (this._focusTargetId = this._detailReturn.selector),
          (this._detailReturn = null))
        : ((this.activeTab = "overview"),
          (this._focusTargetId =
            "button.pf-open-module-btn[data-module=" + t + "]")),
        (this._selectedDetailModule = ""),
        this.display());
    });
    let a = e.createEl("h2", {
        cls: "pf-module-detail-heading",
        text: o(r) || o("cc_module_" + t),
        attr: { id: n, tabindex: "-1" },
      }),
      i = [
        { id: "installation", labelKey: "md_select_installation" },
        { id: "library", labelKey: "md_select_library" },
        { id: "ocr", labelKey: "md_select_ocr" },
        { id: "memory", labelKey: "md_select_memory" },
      ],
      c = e.createEl("div", { cls: "pf-module-detail-selector" });
    for (let P of i)
      c.createEl("button", {
        cls:
          "pf-module-detail-btn" +
          (P.id === t ? " pf-module-detail-btn--active" : ""),
        text: o(P.labelKey),
      }).addEventListener("click", () => {
        ((this._selectedDetailModule = P.id),
          (this._focusTargetId =
            P.id === "installation"
              ? "#pf-installation-detail-heading"
              : "#pf-" + P.id + "-detail-heading"),
          this.display());
      });
    let u =
        (F = ((T = this._capabilityState) != null ? T : {})[t]) != null
          ? F
          : oe(t),
      _ = this._sevClass(u.severity),
      g = ze(u),
      h = e.createEl("div", { cls: "pf-cc-card pf-module-detail-card" }),
      f = h.createEl("div", { cls: "pf-cc-card-header" });
    if (
      (f.createEl("span", {
        cls: "pf-cc-card-name",
        text: o("cc_module_" + t),
      }),
      f.createEl("span", {
        cls: "pf-cc-card-badge pf-cc-card-badge--" + _,
        text: o(this._ccBadgeKey(u, t)),
      }),
      u.activity_state === "running" && u.activity_label)
    ) {
      let P = h.createEl("div", {
        cls: "pf-cc-card-activity",
        attr: { "aria-live": "polite" },
      });
      if (
        (P.createEl("span", { text: u.activity_label }),
        u.activity_progress && u.activity_progress.total > 0)
      ) {
        let L = Math.round(
            (u.activity_progress.current / u.activity_progress.total) * 100
          ),
          I = P.createEl("div", {
            cls: "pf-cc-card-progress",
            attr: {
              role: "progressbar",
              "aria-valuenow": String(u.activity_progress.current),
              "aria-valuemin": "0",
              "aria-valuemax": String(u.activity_progress.total),
            },
          }).createEl("div", { cls: "pf-cc-card-progress-fill" });
        I.style.width = L + "%";
      }
    }
    let v = this._localizeReason(u.reason.code, t);
    h.createEl("div", {
      cls: "pf-cc-card-reason",
      text: v != null ? v : u.reason.text,
    });
    let y = (M = u.action) == null ? void 0 : M.primary;
    if (y && !g) {
      y.safety_class !== "safe" &&
        y.confirmation_required &&
        h
          .createEl("div", { cls: "pf-destructive-notice" })
          .createEl("span", { text: (y.replacement_facts || []).join("; ") });
      let P = u.activity_state === "running",
        L = Ke(u),
        C = h.createEl("button", {
          cls: "pf-cc-card-action pf-cc-card-action--primary",
          text: L.label,
        });
      (P && C.setAttr("disabled", "disabled"),
        C.addEventListener("click", () => {
          P || this._dispatchModuleAction(t, u);
        }));
    }
    let m = h.createEl("div", { cls: "pf-meta" }),
      E;
    try {
      E = new Date(u.updated_at).toLocaleString();
    } catch (P) {
      E = u.updated_at;
    }
    if (
      (m.createEl("span", {
        text:
          o("cc_diag_updated") +
          ": " +
          E +
          " | TTL: " +
          String(u.ttl_seconds) +
          "s",
      }),
      u.notices && u.notices.length > 0)
    )
      for (let P of u.notices)
        e.createEl("div", {
          cls: "pf-notice pf-notice--" + (P.level || "info"),
          text: P.message,
        });
    let k = h.createEl("details", { cls: "pf-cc-card-diagnostic" });
    k.createEl("summary", { text: o("cc_diagnostic_toggle") });
    let b = k.createEl("div", { cls: "pf-cc-card-diagnostic-body" }),
      x = o("cc_state_" + u.capability_state) || u.capability_state,
      w = o("cc_severity_" + u.severity) || u.severity,
      R = o("cc_activity_" + u.activity_state) || u.activity_state;
    (b.createEl("div", {
      text:
        o("cc_diag_module") + ": " + (o("cc_module_" + u.module) || u.module),
    }),
      b.createEl("div", { text: o("cc_diag_state") + ": " + x }),
      b.createEl("div", { text: o("cc_diag_severity") + ": " + w }),
      b.createEl("div", { text: o("cc_diag_activity") + ": " + R }));
    let S = b.createEl("div");
    (S.appendText(
      o("cc_diag_reason") + ": " + (v != null ? v : u.reason.text) + " "
    ),
      S.createEl("code", { text: u.reason.code }));
    try {
      a.focus();
    } catch (P) {}
  }
  _renderHelpTab(e) {
    var E, k;
    let t = (E = this._capabilityState) != null ? E : {},
      r = "help",
      n = (k = t[r]) != null ? k : oe(r),
      s = this._sevClass(n.severity),
      a = Ce._REAL_PROBE.has(r);
    e.createEl("h2", { text: o("cc_module_help") || "Help & Docs" });
    let i = e.createEl("div", {
        cls: "pf-cc-card pf-open-module-btn",
        attr: { style: "margin-bottom: 12px;" },
      }),
      c = i.createEl("div", { cls: "pf-cc-card-header" });
    (c.createEl("span", { cls: "pf-cc-card-name", text: o("cc_module_help") }),
      c.createEl("span", {
        cls: `pf-cc-card-badge pf-cc-card-badge--${s}`,
        text: o(this._ccBadgeKey(n, r)),
      }));
    let p;
    if (!a)
      p = o("cc_reason_placeholder").replace("{module}", o("cc_module_" + r));
    else {
      let b = this._localizeReason(n.reason.code, r);
      p = b != null ? b : n.reason.text;
    }
    if (
      (i.createEl("div", { cls: "pf-cc-card-reason", text: p }),
      n.action.primary && !ze(n))
    ) {
      let b = Ke(n),
        w =
          b.kind === "setup"
            ? "pf-cc-card-action pf-cc-card-action--primary"
            : "pf-cc-card-action";
      i.createEl("button", {
        cls: w,
        text: b.label,
        attr: { "aria-label": b.label },
      }).addEventListener("click", () => {
        b.kind === "setup"
          ? new ke(this.app, this.plugin, () => {
              (this._probeModule("installation"), this._probeModule("help"));
            }).open()
          : this._probeModule(r);
      });
    }
    let u = i.createEl("details", { cls: "pf-cc-card-diagnostic" });
    u.createEl("summary", { text: o("cc_diagnostic_toggle") });
    let _ = u.createEl("div", { cls: "pf-cc-card-diagnostic-body" }),
      g = o("cc_state_" + n.capability_state) || n.capability_state,
      h = o("cc_severity_" + n.severity) || n.severity,
      f = o("cc_activity_" + n.activity_state) || n.activity_state,
      v;
    try {
      v = new Date(n.updated_at).toLocaleString();
    } catch (b) {
      v = n.updated_at;
    }
    (_.createEl("div", { text: `${o("cc_diag_module")}: ${n.module}` }),
      _.createEl("div", { text: `${o("cc_diag_state")}: ${g}` }),
      _.createEl("div", { text: `${o("cc_diag_severity")}: ${h}` }),
      _.createEl("div", { text: `${o("cc_diag_activity")}: ${f}` }));
    let y = _.createEl("div");
    y.appendText(o("cc_diag_reason") + ": " + p + " ");
    let m = y.createEl("code", { text: n.reason.code });
    (_.createEl("div", {
      text: `${o("cc_diag_ttl")}: ${String(n.ttl_seconds)}s`,
    }),
      _.createEl("div", { text: `${o("cc_diag_updated")}: ${v}` }),
      this._renderReleaseNotesTab(e));
  }
  _execMemoryStatus(e, t, r) {
    let n = de();
    (0, ee.exec)(
      `"${e}" -m paperforge --vault "${t}" memory status --json`,
      { encoding: "utf-8", timeout: 15e3, env: n },
      (s, a) => {
        if (s) {
          r("Status unavailable");
          return;
        }
        try {
          let i = JSON.parse(a);
          if (i.ok) {
            let c = i.data,
              p = c.fresh ? "fresh" : "stale";
            r(
              `Papers: ${c.paper_count_db} | ${p}${c.needs_rebuild ? " - needs rebuild" : ""}`
            );
          } else r("DB not found. Run paperforge memory build.");
        } catch (i) {
          r("Could not parse status.");
        }
      }
    );
  }
  _execEmbedStatus(e, t, r) {
    let n = de();
    (0, ee.exec)(
      `"${e}" -m paperforge --vault "${t}" embed status --json`,
      { encoding: "utf-8", timeout: 15e3, env: n },
      (s, a) => {
        if (s) {
          r("Status unavailable");
          return;
        }
        try {
          let i = JSON.parse(a);
          i.ok
            ? r(
                `Chunks: ${i.data.chunk_count} | ${i.data.model} | ${i.data.mode}`
              )
            : r("Could not parse status.");
        } catch (i) {
          r("Could not parse status.");
        }
      }
    );
  }
  _callPython(e, t) {
    let r = this.app.vault.adapter.basePath,
      n = this._resolveRuntimeCommand(r);
    if (!n)
      return (
        t && t.onClose && t.onClose(1, "", "No python runtime available"),
        null
      );
    let s = [...n.args, "-m", "paperforge", "--vault", r, ...e],
      a = (t == null ? void 0 : t.credentialType) && !(t != null && t.env),
      i = (u) => {
        let _ = (0, ee.spawn)(n.path, s, { cwd: r, env: u, windowsHide: !0 });
        return (
          t.onData && _.stdout.on("data", t.onData),
          t.onStderr && _.stderr.on("data", t.onStderr),
          t.onError && _.on("error", t.onError),
          _.on("close", t.onClose),
          _
        );
      },
      c = (u) => {
        (0, ee.execFile)(
          n.path,
          s,
          { cwd: r, timeout: (t && t.timeout) || 6e4, env: u },
          (_, g, h) => {
            t && t.onClose && t.onClose(_ ? 1 : 0, g, h);
          }
        );
      };
    if (a)
      return (
        ge(Ye(this.app), t.credentialType).then((u) => {
          t && t.stream ? i(u) : c(u);
        }),
        null
      );
    let p = (t == null ? void 0 : t.env) || de();
    return t && t.stream ? i(p) : (c(p), null);
  }
  _renderMemoryStatusText(e, t, r) {
    ((e.innerHTML = ""),
      e.createEl("span", { text: t, cls: "paperforge-memory-text" }),
      r === "syncing"
        ? e.createEl("span", {
            text: "Syncing...",
            cls: "paperforge-sync-status",
          })
        : r && e.createEl("span", { text: r, cls: "paperforge-sync-status" }));
    let n = e.createEl("button", {
      cls: "paperforge-rebuild-btn",
      text: o("feat_memory_rebuild_btn"),
    });
    ((n.title = "Rebuild memory database"),
      (n.onclick = () => {
        let a = this.app.vault.adapter.basePath,
          i = this._resolveRuntimeCommand(a);
        if (!(i != null && i.path)) {
          new A.Notice(o("feat_no_python"));
          return;
        }
        (console.log("[PaperForge] Rebuilding memory:", i.path),
          n.setText(o("feat_memory_rebuilding")),
          n.setAttr("disabled", ""),
          this._callPython(["memory", "build"], {
            timeout: 6e4,
            onClose: (c, p, u) => {
              (console.log(
                "[PaperForge] memory build exit:",
                c ? "FAIL:" + c : "OK",
                (p || "").slice(0, 200),
                (u || "").slice(0, 200)
              ),
                n.setText(o("feat_memory_rebuild_btn")),
                n.removeAttribute("disabled"),
                c === 0
                  ? new A.Notice(o("feat_memory_rebuild_done"))
                  : new A.Notice(
                      o("feat_memory_rebuild_failed") +
                        (u ? " " + u.slice(0, 80) : "")
                    ),
                (this._memoryStatusText = Rt(a)),
                this._refreshSnapshots(a));
            },
          }));
      }));
    let s = e.createEl("button", {
      cls: "paperforge-refresh-btn",
      text: "\u21BB",
    });
    ((s.title = "Sync now"),
      (s.onclick = () => {
        ((this._memoryStatusText = null), this._runManualSync());
      }));
  }
  _getBuildCommand(e) {
    let t = this.app.vault.adapter.basePath,
      r = this._resolveRuntimeCommand(t);
    return r ? `"${r.path}" -m paperforge --vault "${t}" sync` : null;
  }
  _runManualSync() {
    var s;
    let e = this.app.vault.adapter.basePath,
      t = this._resolveRuntimeCommand(e);
    if (!(t != null && t.path)) return;
    let r = (s = this._capabilityState) != null ? s : {};
    r.library &&
      ((r.library.activity_state = "running"),
      (r.library.activity_label = "Syncing library\u2026"));
    let n = document.querySelector(".paperforge-memory-status");
    (n && this._renderMemoryStatusText(n, "Checking...", "syncing"),
      (this.plugin._autoSyncRunning = !0),
      (this._libraryRunning = !0),
      this.display(),
      this._callPython(["sync"], {
        timeout: 12e4,
        onClose: (a) => {
          ((this.plugin._autoSyncRunning = !1),
            (this._libraryRunning = !1),
            (this._memoryStatusText = null),
            r.library &&
              ((r.library.activity_state = "idle"),
              (r.library.activity_label = null)),
            a === 0 &&
              ((this._lastSyncTime = new Date().toLocaleTimeString()),
              (this.plugin._lastSyncTime = this._lastSyncTime)),
            this._probeModule("library", a != null ? a : 1),
            this.display(),
            this._refreshSnapshots(e),
            ct(this.app, this.plugin, e));
        },
      }));
  }
  _refreshSnapshots(e) {
    let t = this._resolveRuntimeCommand(e);
    if (!t) return;
    let r = [
      ...t.args,
      "-m",
      "paperforge",
      "--vault",
      e,
      "runtime-health",
      "--json",
    ];
    ((this._refreshPending = !0),
      (0, ee.execFile)(
        t.path,
        r,
        { cwd: e, timeout: 3e4, windowsHide: !0 },
        (n, s, a) => {
          ((this._refreshPending = !1),
            (this._memoryStatusText = Rt(e)),
            (this._embedStatusText = Me(e)),
            this.display());
        }
      ));
  }
  _renderVectorSection(e) {
    var c;
    if (
      (e.createEl("h4", { text: "Smart Retrieval" }),
      this.plugin.settings.features ||
        (this.plugin.settings.features = { memory_layer: !0, vector_db: !1 }),
      e
        .createEl("div", { cls: "paperforge-desc-box" })
        .setText(o("feat_vector_desc")),
      new A.Setting(e)
        .setName(o("feat_vector_enable"))
        .setDesc(o("feat_vector_enable_desc"))
        .addToggle((p) => {
          p.setValue(!!this.plugin.settings.features.vector_db).onChange(
            (u) => {
              ((this.plugin.settings.features.vector_db = u),
                this.plugin.saveSettings(),
                (this._vectorDepsOk = null),
                (this._embedStatusText = null),
                this.display());
            }
          );
        }),
      !this.plugin.settings.features.vector_db)
    )
      return;
    let r = this.app.vault.adapter.basePath,
      n = e.createEl("div", { cls: "paperforge-vec-header" }),
      s = n.createEl("span", {
        text: "\u25BC",
        cls: "paperforge-skills-arrow",
      });
    n.createEl("span", {
      cls: "paperforge-vec-header-label",
      text: o("feat_vector_config_label"),
    });
    let a = e.createEl("div", { cls: "paperforge-vector-config" }),
      i = (p) => {
        ((a.style.display = p ? "none" : ""),
          (s.style.transform = p ? "rotate(-90deg)" : "rotate(0deg)"));
      };
    if (
      (i(Ot(this._featurePanelsCollapsed, "vectorConfig", !1)),
      n.addEventListener("click", () => {
        let p = yr(this._featurePanelsCollapsed, "vectorConfig", !1);
        i(p);
      }),
      this._vectorDepsOk === !0)
    ) {
      this._renderVectorReady(a, r);
      return;
    }
    if (this._vectorDepsOk === !1) {
      this._renderVectorNoDeps(a);
      return;
    }
    if (this._vectorDepsOk === null) {
      let p = at(r);
      ((this._vectorDepsOk = p && (c = p.deps_installed) != null ? c : !1),
        this._vectorDepsOk && (this._embedStatusText = Me(r)),
        this.display());
    }
  }
  _renderApiConfig(e) {
    let r =
        this.plugin.settings._vector_db_configured || !1
          ? "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022"
          : "sk-...",
      n = null;
    (new A.Setting(e)
      .setName(o("feat_openai_key"))
      .setDesc(o("feat_openai_key_desc"))
      .addText((s) => {
        ((s.inputEl.type = "password"),
          s
            .setPlaceholder(r)
            .setValue("")
            .onChange((a) => {
              a &&
                (n && clearTimeout(n),
                (n = setTimeout(async () => {
                  let i = this.app.secretStorage;
                  if (i != null && i.setSecret) {
                    try {
                      (await i.setSecret("vector-db-api-key", a),
                        (await i.getSecret("vector-db-api-key")) === a &&
                          ((this.plugin.settings._vector_db_configured = !0),
                          (this.plugin.settings.vector_db_api_key = ""),
                          await this.plugin.saveSettings(),
                          s.setValue("")));
                    } catch (c) {}
                    n = null;
                  }
                }, 600)));
            }));
      }),
      new A.Setting(e)
        .setName(o("feat_api_base_url"))
        .setDesc(o("feat_api_base_url_desc"))
        .addText((s) => {
          s.setPlaceholder("https://api.openai.com/v1")
            .setValue(this.plugin.settings.vector_db_api_base || "")
            .onChange((a) => {
              ((this.plugin.settings.vector_db_api_base = a),
                this.plugin.saveSettings());
            });
        }),
      new A.Setting(e)
        .setName(o("feat_api_model"))
        .setDesc(o("feat_api_model_desc"))
        .addText((s) => {
          s.setPlaceholder("text-embedding-3-small")
            .setValue(
              this.plugin.settings.vector_db_api_model ||
                "text-embedding-3-small"
            )
            .onChange((a) => {
              ((this.plugin.settings.vector_db_api_model = a),
                this.plugin.saveSettings());
            });
        }));
  }
  _renderVectorNoDeps(e) {
    (e
      .createEl("div", { cls: "paperforge-desc-box" })
      .setText(o("feat_deps_missing")),
      new A.Setting(e)
        .setName(o("feat_install_deps"))
        .setDesc(o("feat_install_deps_desc"))
        .addButton((r) => {
          r.setButtonText(o("feat_install_btn"))
            .setCta()
            .onClick(async () => {
              let n = this.app.vault.adapter.basePath,
                s = this._resolveRuntimeCommand(n);
              if (!(s != null && s.path)) {
                new A.Notice(o("feat_no_python"));
                return;
              }
              (r.setButtonText(o("feat_installing")), r.setDisabled(!0));
              let a = "chromadb openai",
                i = new A.Notice(
                  o("feat_installing_pkgs").replace("{pkgs}", a),
                  0
                );
              try {
                let c = Object.assign(de(), {
                    PYTHONIOENCODING: "utf-8",
                    PYTHONUTF8: "1",
                  }),
                  p = a.split(" ");
                (await new Promise((u, _) => {
                  (0, ee.execFile)(
                    s.path,
                    [...s.args, "-m", "pip", "install", ...p],
                    { cwd: n, timeout: 3e5, env: c, windowsHide: !0 },
                    (g) => {
                      g ? _(g) : u();
                    }
                  );
                }),
                  i.hide(),
                  new A.Notice(o("feat_install_done")),
                  (this._vectorDepsOk = !0),
                  (this._embedStatusText = Me(n)),
                  this.display());
              } catch (c) {
                (i.hide(),
                  new A.Notice(
                    o("feat_install_failed") + (c.stderr || c.message || c)
                  ),
                  r.setButtonText(o("feat_retry_btn")),
                  r.setDisabled(!1));
              }
            });
        }));
  }
  _renderVectorReady(e, t) {
    (e.createEl("div", { cls: "paperforge-desc-box" }).setText(Me(t)),
      this._renderApiConfig(e));
    let n = e.createEl("div", { cls: "paperforge-embed-section" });
    n.createEl("div", { cls: "paperforge-embed-header" }).createEl("span", {
      text: o("retrieval_rebuild_vectors"),
      cls: "setting-item-name",
    });
    let a = n.createEl("div", { cls: "paperforge-embed-controls" }),
      i = n.createEl("div", {
        cls: "paperforge-embed-status-text",
        attr: { "aria-live": "polite" },
      });
    (() => {
      (a.empty(), i.empty());
      let p = at(t),
        u = p == null ? void 0 : p.build_state,
        _ = u && typeof u == "object" && !Array.isArray(u) ? u : {};
      ((this.plugin._embedProgress = this.plugin._embedProgress || {
        current: 0,
        total: 0,
        key: "",
      }),
        !this.plugin._embedProcess &&
          _.status === "running" &&
          (this.plugin._embedProgress = {
            current: typeof _.current == "number" ? _.current : 0,
            total: typeof _.total == "number" ? _.total : 1,
            key: typeof _.paper_id == "string" ? _.paper_id : "",
          }));
      let { current: g, total: h, key: f } = this.plugin._embedProgress,
        v =
          typeof (p == null ? void 0 : p.body_chunk_count) == "number"
            ? p.body_chunk_count
            : 0,
        y =
          typeof (p == null ? void 0 : p.object_chunk_count) == "number"
            ? p.object_chunk_count
            : 0,
        E =
          (typeof (p == null ? void 0 : p.chunk_count) == "number"
            ? p.chunk_count
            : 0) +
          v +
          y,
        k = E > 0,
        b = p !== null && typeof p.corrupted == "boolean" && p.corrupted,
        x = !!this.plugin._embedProcess,
        w = !this.plugin._embedProcess && _.status === "running",
        R =
          (p == null ? void 0 : p.deps_installed) !== void 0
            ? !!p.deps_installed
            : !0,
        S = typeof _.status == "string" ? _.status : "",
        T = typeof _.message == "string" ? _.message : "",
        F = async (C) => {
          var V;
          if (C === "--resume" && k && !b) {
            let N = o("retrieval_rebuild_warning").replace("{n}", String(E));
            if (!confirm(N)) return;
          }
          if (C === "--force" && k && !b) {
            let N =
              "Force rebuild will replace " +
              E +
              " existing chunk(s). Continue?";
            if (!confirm(N)) return;
          }
          let I = this._resolveRuntimeCommand(t);
          if (!(I != null && I.path)) {
            new A.Notice(o("retrieval_no_python"));
            return;
          }
          let K = await ge(Ye(this.app), "embed");
          ((K.PYTHONIOENCODING = "utf-8"),
            (K.PYTHONUTF8 = "1"),
            (K.VECTOR_DB_API_BASE =
              this.plugin.settings.vector_db_api_base || ""),
            (K.VECTOR_DB_API_MODEL =
              this.plugin.settings.vector_db_api_model || ""),
            (this.plugin._embedStderr = ""),
            (this.plugin._embedProgress = { current: 0, total: 0, key: "" }),
            (this.plugin._embedProcess = this._callPython(
              ["embed", "build", C],
              {
                stream: !0,
                env: K,
                onData: (N) => {
                  var se;
                  let re =
                      typeof N == "string"
                        ? N
                        : Buffer.isBuffer(N)
                          ? N.toString("utf-8")
                          : String(N),
                    { events: ae, buffer: _e } = Je(
                      re,
                      (se = this.plugin._embedBuffer) != null ? se : ""
                    );
                  this.plugin._embedBuffer = _e;
                  for (let U of ae)
                    U.event === "START"
                      ? (this.plugin._embedProgress.total = U.total || 0)
                      : U.event === "PROGRESS"
                        ? ((this.plugin._embedProgress.current =
                            U.current || 0),
                          (this.plugin._embedProgress.key = U.key || ""))
                        : U.event === "DONE" &&
                          ((this.plugin._embedProcess = null),
                          (this.plugin._embedProgress.current =
                            this.plugin._embedProgress.total));
                  this.display();
                },
                onStderr: (N) => {
                  (this.plugin._embedStderr || (this.plugin._embedStderr = ""),
                    (this.plugin._embedStderr += String(N)));
                },
                onError: (N) => {
                  ((this.plugin._embedProcess = null),
                    new A.Notice(
                      o("feat_build_failed") + ": " + (N.message || N)
                    ),
                    this.display());
                },
                onClose: (N) => {
                  var re;
                  if (
                    (clearInterval(
                      (re = this.plugin._embedPollInterval) != null
                        ? re
                        : void 0
                    ),
                    (this.plugin._embedPollInterval = null),
                    (this.plugin._embedProcess = null),
                    N === 0)
                  )
                    ((this.plugin._embedProgress.current =
                      this.plugin._embedProgress.total),
                      this.plugin.saveSettings(),
                      (this._embedStatusText = Me(t)),
                      new A.Notice(o("feat_build_complete")));
                  else {
                    this._embedStatusText = null;
                    let ae = (this.plugin._embedStderr || "").slice(0, 200);
                    new A.Notice(
                      o("feat_build_failed") + (ae ? ": " + ae : ""),
                      8e3
                    );
                  }
                  ((this.plugin._embedStderr = ""),
                    this.display(),
                    this._refreshSnapshots(t));
                },
              }
            )),
            clearInterval(
              (V = this.plugin._embedPollInterval) != null ? V : void 0
            ),
            (this.plugin._embedPollInterval = setInterval(() => {
              this.plugin._embedPolling ||
                ((this.plugin._embedPolling = !0),
                this._callPython(["embed", "status", "--json"], {
                  timeout: 5e3,
                  onClose: (N, re) => {
                    var ae;
                    if (((this.plugin._embedPolling = !1), N === 0 && re))
                      try {
                        let se = JSON.parse(re).data;
                        if (se && se.build_state) {
                          let U = se.build_state;
                          ((U.status === "stopping" || U.status === "idle") &&
                            this.plugin._embedProcess &&
                            ((this.plugin._embedProcess = null),
                            clearInterval(
                              (ae = this.plugin._embedPollInterval) != null
                                ? ae
                                : void 0
                            ),
                            (this.plugin._embedPollInterval = null),
                            this.display()),
                            U.current !== void 0 &&
                              U.total !== void 0 &&
                              ((this.plugin._embedProgress.current = U.current),
                              (this.plugin._embedProgress.total = U.total || 1),
                              (this.plugin._embedProgress.key =
                                U.paper_id || "")));
                        }
                      } catch (_e) {}
                  },
                }));
            }, 2e3)),
            this.display());
        },
        M = Ze(t),
        P = !1;
      M &&
        typeof M.summary == "object" &&
        M.summary !== null &&
        "status" in M.summary &&
        (P = M.summary.status === "version_mismatch");
      let L;
      switch (
        (R
          ? P
            ? (L = "runtime-mismatch")
            : S === "stopping"
              ? (L = "stopping")
              : x && S === "running"
                ? (L = "building")
                : S === "failed"
                  ? (L = "failed")
                  : S === "stopped"
                    ? (L = "stopped")
                    : w
                      ? (L = "stale")
                      : b
                        ? (L = "corrupted")
                        : k
                          ? (L = "ready")
                          : (L = "idle")
          : (L = "deps-missing"),
        L)
      ) {
        case "building": {
          let C = a.createEl("div", { cls: "paperforge-progress-track" });
          C.style.cssText = "flex:1;";
          let I = h > 0 ? ((g / h) * 100).toFixed(1) : "0",
            K = C.createEl("div", { cls: "paperforge-progress-seg done" });
          if (
            ((K.style.cssText = `width:${I}%; min-width:${g > 0 ? "2px" : "0"};`),
            g < h)
          ) {
            let N = C.createEl("div", {
              cls: "paperforge-progress-seg pending",
            });
            N.style.cssText = `width:${(100 - parseFloat(I)).toFixed(1)}%;`;
          }
          (i.createEl("span", {
            cls: "paperforge-embed-progress-text",
            text: `${g}/${h} papers`,
          }),
            f &&
              i.createEl("span", {
                cls: "paperforge-embed-progress-key",
                text: ` (${f})`,
              }));
          let V = a.createEl("button");
          (V.setText(o("retrieval_stop")),
            (V.className = "mod-warning"),
            V.addEventListener("click", () => {
              (this._callPython(["embed", "stop", "--json"], { timeout: 8e3 }),
                this.display());
            }));
          break;
        }
        case "stopping": {
          let C = a.createEl("div", { cls: "paperforge-progress-track" });
          C.style.cssText = "flex:1; opacity:0.5;";
          let I = h > 0 ? ((g / h) * 100).toFixed(1) : "0",
            K = C.createEl("div", { cls: "paperforge-progress-seg done" });
          if (
            ((K.style.cssText = `width:${I}%; min-width:${g > 0 ? "2px" : "0"};`),
            g < h)
          ) {
            let N = C.createEl("div", {
              cls: "paperforge-progress-seg pending",
            });
            N.style.cssText = `width:${(100 - parseFloat(I)).toFixed(1)}%;`;
          }
          i.createEl("span", { text: o("retrieval_build_stopping") });
          let V = a.createEl("button");
          (V.setText(o("retrieval_stop")),
            (V.className = "mod-warning"),
            V.setAttr("disabled", ""));
          break;
        }
        case "failed": {
          i.createEl("div", {
            cls: "paperforge-desc-box",
            text: o("retrieval_build_failed") + (T ? ": " + T : ""),
            attr: { style: "color:var(--text-error);" },
          });
          let C = a.createEl("button");
          (C.setText(o("retrieval_retry")),
            (C.className = "mod-cta"),
            C.addEventListener("click", () => F("--resume")));
          let I = a.createEl("button");
          (I.setText(o("retrieval_force_rebuild")),
            (I.style.marginLeft = "6px"),
            I.addEventListener("click", () => F("--force")));
          break;
        }
        case "stopped": {
          i.setText(o("retrieval_build_stopped"));
          let C = a.createEl("button");
          (C.setText(o("retrieval_retry")),
            (C.className = "mod-cta"),
            C.addEventListener("click", () => F("--resume")));
          break;
        }
        case "corrupted": {
          i.createEl("div", {
            cls: "paperforge-desc-box",
            text: o("feat_vector_corrupted"),
            attr: { style: "background:var(--background-modifier-warning);" },
          });
          let C = a.createEl("button");
          (C.setText(o("retrieval_force_rebuild")),
            (C.className = "mod-cta"),
            C.addEventListener("click", () => F("--force")));
          break;
        }
        case "stale": {
          i.createEl("div", {
            cls: "paperforge-desc-box",
            text: o("retrieval_build_stale"),
            attr: { style: "color:var(--text-warning);" },
          });
          let C = a.createEl("button");
          (C.setText(o("retrieval_rebuild_vectors")),
            (C.className = "mod-cta"),
            C.addEventListener("click", () => F("--resume")));
          break;
        }
        case "ready": {
          a.createEl("span", {
            text: E + " chunks embedded",
            cls: "setting-item-description",
          });
          let C = a.createEl("button");
          (C.setText(o("retrieval_rebuild_vectors")),
            (C.className = "mod-cta"),
            C.addEventListener("click", () => F("--resume")));
          let I = a.createEl("button");
          (I.setText(o("retrieval_force_rebuild")),
            (I.style.marginLeft = "6px"),
            I.addEventListener("click", () => F("--force")));
          break;
        }
        case "deps-missing": {
          i.setText(o("retrieval_build_deps_missing"));
          let C = a.createEl("a");
          (C.setText(o("feat_install_deps")),
            (C.style.cssText = "cursor:pointer; text-decoration:underline;"),
            C.addEventListener("click", () => {
              this.display();
            }));
          break;
        }
        case "runtime-mismatch": {
          i.createEl("div", {
            cls: "paperforge-desc-box",
            text: o("retrieval_build_runtime_mismatch"),
            attr: { style: "color:var(--text-warning);" },
          });
          let C = a.createEl("a");
          (C.setText(o("runtime_health_sync")),
            (C.style.cssText = "cursor:pointer; text-decoration:underline;"),
            C.addEventListener("click", () => {
              this.display();
            }));
          break;
        }
        case "idle":
        default: {
          i.setText(o("retrieval_build_idle"));
          let C = a.createEl("button");
          (C.setText(o("feat_build_btn")),
            (C.className = "mod-cta"),
            C.addEventListener("click", () => F("--resume")));
          break;
        }
      }
    })();
  }
  _getCurrentModelKey() {
    return this.plugin.settings.vector_db_api_model || "text-embedding-3-small";
  }
  _parseEmbedStatus(e) {
    let t = {};
    return (
      e &&
        (e
          .split(
            `
`
          )
          .forEach((r) => {
            let n = r.match(/^\s*([^:]+):\s*(.*)/);
            n && (t[n[1].trim()] = n[2].trim());
          }),
        t.db_exists !== void 0 && (t.db_exists = t.db_exists === "True"),
        t.chunk_count !== void 0 &&
          (t.chunk_count = parseInt(t.chunk_count, 10) || 0)),
      t
    );
  }
  _getPythonDesc(e, t) {
    return t === "stale"
      ? `[!!] ${e} (stale \u2014 path no longer exists, update or clear the override below)`
      : t === "manual"
        ? `${e} (manual)`
        : `${e} (auto-detected)`;
  }
  _refreshPythonInterpDesc(e, t) {
    let r = this._pythonInterpDescEl;
    r &&
      (t === "stale"
        ? (r.textContent = `[!!] ${e} (stale \u2014 path no longer exists, update or clear the override below)`)
        : t === "manual"
          ? (r.textContent = `${e} (manual)`)
          : (r.textContent = `${e} (auto-detected)`));
  }
  _validatePythonOverride() {
    let e = this.plugin.settings.python_path
        ? this.plugin.settings.python_path.trim()
        : "",
      t = this._customPathDescEl;
    if (!e) {
      let r = "\u8BF7\u8F93\u5165\u8DEF\u5F84 / Enter a path first";
      (t &&
        (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${r}</span>`),
        new A.Notice(r));
      return;
    }
    if (!G.existsSync(e)) {
      let r = "\u8DEF\u5F84\u4E0D\u5B58\u5728 / Path does not exist";
      (t &&
        (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${r}</span>`),
        new A.Notice(r, 4e3));
      return;
    }
    try {
      G.accessSync(e, G.constants.X_OK);
    } catch (r) {
      let n = "\u4E0D\u53EF\u6267\u884C / Not executable";
      (t &&
        (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${n}</span>`),
        new A.Notice(n, 4e3));
      return;
    }
    (0, ee.execFile)(e, ["--version"], { timeout: 8e3 }, (r, n) => {
      if (r || !n) {
        let c = "\u65E0\u6CD5\u8FD0\u884C / Cannot run";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${c}</span>`),
          new A.Notice(c, 4e3));
        return;
      }
      let s = n.match(/Python (\d+)\.(\d+)/);
      if (!s) {
        let c = "\u65E0\u6CD5\u89E3\u6790\u7248\u672C / Cannot parse version";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${c}</span>`),
          new A.Notice(c, 4e3));
        return;
      }
      let a = parseInt(s[1], 10),
        i = parseInt(s[2], 10);
      if (a < 3 || (a === 3 && i < 11)) {
        let c =
          "Python \u7248\u672C\u8FC7\u4F4E\uFF0C\u9700\u8981 3.11+ / Python version too low, need 3.11+";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${c}</span>`),
          new A.Notice(c, 4e3));
        return;
      }
      (0, ee.execFile)(e, ["-m", "pip", "--version"], { timeout: 8e3 }, (c) => {
        if (c) {
          let p = `\u2713 Python ${a}.${i} \u6709\u6548\uFF0C\u4F46\u672A\u68C0\u6D4B\u5230 pip / Valid, but pip not found`;
          (t &&
            (t.innerHTML = `<span style="color:var(--text-warning)">\u26A0 ${p}</span>`),
            new A.Notice(p, 4e3));
        } else {
          let p = `\u2713 Python ${a}.${i} \u6709\u6548 / Valid`;
          (t &&
            (t.innerHTML = `<span style="color:var(--text-accent)">${p}</span>`),
            new A.Notice(p, 4e3));
        }
      });
    });
  }
  _debouncedSave() {
    (clearTimeout(this._saveTimeout),
      (this._saveTimeout = setTimeout(() => this.plugin.saveSettings(), 500)));
  }
  _preCheck(e) {
    let t = this.app.vault.adapter.basePath,
      r = this._resolveRuntimeCommand(t);
    if (!r) {
      e();
      return;
    }
    (0, ee.execFile)(
      r.path,
      [...r.args, "--version"],
      { timeout: 8e3 },
      (n, s) => {
        let a = [];
        a.push({
          label: "environment",
          ok: !n,
          detail: n ? o("check_python_fail") : s.trim(),
        });
        let i = !1,
          c = process.env.HOME || process.env.USERPROFILE || br.homedir() || "";
        if (process.platform === "darwin")
          i = [
            "/Applications/Zotero.app",
            te.join(c, "Applications", "Zotero.app"),
          ].some((v) => {
            try {
              return G.existsSync(v);
            } catch (y) {
              return !1;
            }
          });
        else if (process.platform === "win32") {
          let f = process.env.ProgramFiles || "",
            v = process.env.LOCALAPPDATA || "";
          i = [
            te.join(f, "Zotero"),
            te.join(f, "(x86)", "Zotero"),
            te.join(v, "Programs", "Zotero"),
            te.join(v, "Zotero"),
            te.join(c, "AppData", "Local", "Programs", "Zotero"),
          ]
            .filter(Boolean)
            .some((m) => {
              try {
                return G.existsSync(m);
              } catch (E) {
                return !1;
              }
            });
        } else
          i = [
            te.join(c, ".local", "share", "zotero", "zotero"),
            "/usr/bin/zotero",
            "/usr/local/bin/zotero",
          ].some((v) => {
            try {
              return G.existsSync(v);
            } catch (y) {
              return !1;
            }
          });
        let p = this.plugin.settings.zotero_data_dir;
        if (!i && p)
          try {
            i = G.existsSync(p);
          } catch (f) {}
        a.push({
          label: "Zotero",
          ok: i,
          detail: i ? o("check_zotero_ok") : o("check_zotero_fail"),
        });
        let u = !1,
          _ = process.env.APPDATA || "";
        (process.platform === "win32" &&
          _ &&
          (u = nt(te.join(_, "Zotero", "Zotero", "Profiles"))),
          !u &&
            process.platform === "darwin" &&
            c &&
            (u = nt(
              te.join(c, "Library", "Application Support", "Zotero", "Profiles")
            )),
          !u &&
            process.platform !== "win32" &&
            process.platform !== "darwin" &&
            c &&
            (u = nt(te.join(c, ".zotero", "zotero", "Profiles"))),
          !u && p && String(p).trim() && (u = Pt(p.trim())),
          !u && c && (u = Pt(te.join(c, "Zotero"))),
          a.push({
            label: "Better BibTeX",
            ok: u,
            detail: u ? o("check_bbt_ok") : o("check_bbt_fail"),
          }));
        let g = { true: "\u2713", false: "\u2717" };
        if (this._checkEl) {
          this._checkEl.setText(
            a.map((v) => `${g[String(v.ok)]} ${v.label}: ${v.detail}`).join(`
`)
          );
          let f = a.some((v) => !v.ok);
          this._checkEl.className = `paperforge-message msg-${f ? "error" : "ok"}`;
        }
        let h = a.filter((f) => !f.ok);
        (h.length > 0 &&
          new A.Notice(
            `[!!] \u672A\u901A\u8FC7: ${h.map((f) => f.label).join(", ")}`,
            6e3
          ),
          e());
      }
    );
  }
  _dispatchItemAction(e) {
    var r, n, s;
    if (!e.action) return;
    this._pendingMaintenanceRefresh = !0;
    let t = {
      schema_version: 1,
      module: e.module,
      capability_state: e.capability_state,
      activity_state: e.activity_state,
      activity_label: e.activity_label,
      activity_progress: e.activity_progress,
      severity: e.severity,
      reason: { code: e.reason_code, text: e.reason_text },
      action: { primary: e.action },
      notices: [],
      user_state:
        (r = e.user_state) != null
          ? r
          : e.capability_state === "ready"
            ? "ready"
            : "action_required",
      capability_kind:
        e.module === "installation" || e.module === "library"
          ? "required"
          : "optional",
      maintenance_eligible: (n = e.maintenance_eligible) != null ? n : !1,
      user_visible_failure: !1,
      user_impact: (s = e.user_impact) != null ? s : null,
      updated_at: e.module + "-item",
      ttl_seconds: 60,
    };
    this._dispatchModuleAction(e.module, t);
  }
  _requestMaintenanceProjection() {
    if (this._probing.has("maintenance")) {
      this._pendingMaintenanceRefresh = !0;
      return;
    }
    ((this._pendingMaintenanceRefresh = !1), this._probeModule("maintenance"));
  }
  _renderMaintenanceInbox(e) {
    var i, c, p;
    let t = e.createEl("div", { cls: "pf-maintenance-inbox" }),
      r = (i = this._capabilityState) == null ? void 0 : i.maintenance;
    if (!r) {
      (t.createEl("div", {
        cls: "pf-maintenance-inbox-empty",
        text: o("maintenance_checking") || "Checking maintenance status\u2026",
      }),
        this._probeModule("maintenance"));
      return;
    }
    if (
      r.activity_state === "running" &&
      ((c = r.reason) == null ? void 0 : c.code) === "maintenance.probing"
    ) {
      t.createEl("div", {
        cls: "pf-maintenance-inbox-empty",
        text: o("maintenance_checking") || "Checking maintenance status\u2026",
      });
      return;
    }
    if (
      r.capability_state === "ready" &&
      ((p = r.reason) == null ? void 0 : p.code) === "maintenance.no_items" &&
      Array.isArray(r.items) &&
      r.items.length === 0
    ) {
      t.createEl("div", {
        cls: "pf-maintenance-inbox-empty",
        text:
          o("maintenance_all_clear") ||
          "All modules are ready \u2014 no maintenance needed.",
      });
      return;
    }
    if (r.capability_state === "unknown") {
      (t.createEl("div", {
        cls: "pf-maintenance-inbox-empty",
        text: o("maintenance_checking") || "Checking maintenance status\u2026",
      }),
        this._probing.has("maintenance") || this._probeModule("maintenance"));
      return;
    }
    if (
      r.capability_state !== "ready" &&
      r.capability_state !== "needs_action"
    ) {
      (t.createEl("div", {
        cls: "pf-maintenance-inbox-empty",
        text: o("maintenance_checking") || "Checking maintenance status\u2026",
      }),
        this._requestMaintenanceProjection());
      return;
    }
    let n = r.items;
    if (!n || !Array.isArray(n) || n.length === 0) {
      (t.createEl("div", {
        cls: "pf-maintenance-inbox-empty",
        text: o("maintenance_checking") || "Checking maintenance status\u2026",
      }),
        this._requestMaintenanceProjection());
      return;
    }
    (this._maintenanceNoticeShown ||
      ((this._maintenanceNoticeShown = !0),
      new A.Notice(
        o("maintenance_n_pending").replace("{n}", String(n.length)),
        5e3
      )),
      t
        .createEl("div", { cls: "pf-maintenance-inbox-summary" })
        .createEl("span", {
          text: o("maintenance_n_pending").replace("{n}", String(n.length)),
        }));
    let a = t.createEl("div", {
      cls: "pf-maintenance-inbox-list",
      attr: { role: "list" },
    });
    for (let u of n) this._renderMaintenanceInboxItem(a, u);
  }
  _renderMaintenanceInboxItem(e, t) {
    let r = this._dismissedMaintenanceItems.has(t.module),
      n = this._sevClass(t.severity),
      s = e.createEl("div", {
        cls:
          "pf-maintenance-inbox-item" +
          (r ? " pf-maintenance-inbox-item--dismissed" : ""),
        attr: { role: "listitem", "data-module": t.module },
      }),
      a = s.createEl("div", { cls: "pf-maintenance-inbox-item-info" }),
      i = o("cc_module_" + t.module) || t.module;
    a.createEl("button", {
      cls: "pf-maintenance-inbox-item-module",
      text: i,
      attr: { "data-module": t.module },
    }).addEventListener("click", () => {
      ((this._detailReturn = {
        tab: "maintenance",
        selector:
          'button.pf-maintenance-inbox-item-module[data-module="' +
          t.module +
          '"]',
      }),
        this._handleCardNavigation(t.module));
    });
    let p = this._localizeReason(t.reason_code, t.module);
    (a.createEl("div", {
      cls: "pf-maintenance-inbox-item-reason",
      text: p != null ? p : t.reason_text,
    }),
      t.activity_state === "running" &&
        t.activity_label &&
        a.createEl("div", {
          cls: "pf-maintenance-inbox-item-activity",
          text: t.activity_label,
        }));
    let u = s.createEl("div", { cls: "pf-maintenance-inbox-item-actions" });
    (u.createEl("span", {
      cls:
        "pf-maintenance-inbox-item-badge pf-maintenance-inbox-item-badge--" + n,
      text: o("cc_badge_" + (n === "ok" ? "ok" : "attention")),
    }),
      t.action &&
        u
          .createEl("button", {
            cls: "pf-maintenance-inbox-item-action",
            text: t.action.label,
          })
          .addEventListener("click", () => {
            this._dispatchItemAction(t);
          }),
      u
        .createEl("button", {
          cls: "pf-maintenance-inbox-item-dismiss",
          text: r
            ? o("maintenance_undismiss") || "Show"
            : o("maintenance_dismiss") || "Dismiss",
        })
        .addEventListener("click", () => {
          (r
            ? this._dismissedMaintenanceItems.delete(t.module)
            : this._dismissedMaintenanceItems.add(t.module),
            this.display());
        }));
  }
  _renderMaintenanceTab(e) {
    var u;
    (e.createEl("h2", {
      text: o("tab_maintenance") || "\u7EF4\u62A4",
      attr: { id: "pf-maintenance-heading", tabindex: "-1" },
    }),
      this._renderMaintenanceInbox(e),
      e.createEl("h3", {
        text: o("maintenance_ocr_section") || "OCR Maintenance",
      }));
    let r = (u = this.app.vault.adapter.basePath) != null ? u : "",
      n = e.createEl("div"),
      s = { active: "all" },
      a = null;
    try {
      a = dt(r);
    } catch (_) {}
    let i = this._resolveRuntimeCommand(r);
    if (!i) {
      n.createEl("p", {
        text: "\u26A0 Python runtime not ready \u2014 install via Installation tab.",
        cls: "setting-item-description",
      });
      return;
    }
    let c = () => !!this.plugin._ocrProcess,
      p = (_) => {
        n.empty();
        let g = _,
          h = n.createEl("div", { cls: "pf-maint-filters" }),
          f = h.createEl("button", {
            cls: "pf-maint-filter" + (s.active === "all" ? " active" : ""),
            text: o("maintenance_filter_all") || "All",
          });
        f.addEventListener("click", () => {
          ((s.active = "all"), p(_));
        });
        let v = h.createEl("button", {
          cls:
            "pf-maint-filter" + (s.active === "recommended" ? " active" : ""),
          text: o("maintenance_filter_recommended") || "Recommended",
        });
        v.addEventListener("click", () => {
          ((s.active = "recommended"), p(_));
        });
        let y =
          s.active === "recommended"
            ? g.filter((m) => m.needs_derived_rebuild === !0)
            : g;
        if (y.length === 0)
          n.createEl("p", {
            text: "\u5F53\u524D\u7B5B\u9009\u6761\u4EF6\u4E0B\u65E0\u6570\u636E",
            cls: "setting-item-description",
          });
        else {
          let m = i.path,
            E = i.args,
            k = n.createEl("div", { cls: "pf-maint-progress" });
          k.style.display = "none";
          let b = k.createEl("div", { cls: "paperforge-progress-track" });
          b.style.cssText = "flex:1;";
          let x = b.createEl("div", { cls: "paperforge-progress-seg done" }),
            w = b.createEl("div", { cls: "paperforge-progress-seg pending" }),
            R = k.createEl("span", { cls: "pf-maint-progress-text" }),
            S = k.createEl("span", { cls: "pf-maint-progress-key" }),
            T = k.createEl("button", { text: o("maintenance_stop") || "Stop" });
          ((T.className = "mod-warning"),
            T.addEventListener("click", () => {
              let D = this.plugin._ocrProcess;
              (D &&
                (D.stdin && typeof D.stdin.write == "function"
                  ? D.stdin.write(`PAPERFORGE_STOP
`)
                  : typeof D.kill == "function" && D.kill("SIGINT")),
                (this.plugin._ocrWasStopped = !0),
                (T.disabled = !0),
                (T.textContent = (o("maintenance_stop") || "Stop") + "\u2026"));
            }));
          let F = () => {
            let D = this.plugin._ocrProgress;
            if (!D || D.total === 0 || !this.plugin._ocrProcess) {
              k.style.display = "none";
              return;
            }
            k.style.display = "flex";
            let Y =
              D.total > 0 ? ((D.current / D.total) * 100).toFixed(1) : "0";
            ((x.style.width = `${Y}%`),
              (x.style.minWidth = D.current > 0 ? "2px" : "0"),
              D.current < D.total
                ? ((w.style.display = ""), (w.style.flex = "1"))
                : (w.style.display = "none"),
              (R.textContent = (
                o("maintenance_progress_label") || "{current}/{total} papers"
              )
                .replace("{current}", String(D.current))
                .replace("{total}", String(D.total))),
              (S.textContent = D.key ? ` (${D.key})` : ""));
          };
          F();
          let M = new Map();
          for (let D of y) M.set(D.key, !1);
          let P = n.createEl("div", { cls: "pf-maint-table-wrap" }),
            L = P.createEl("table", { cls: "pf-maint-table" }),
            C = L.createEl("thead"),
            I = L.createEl("tbody"),
            K = C.insertRow();
          ["", "Paper", "Status Reason", "Actions"].forEach((D) => {
            let Y = document.createElement("th");
            ((Y.textContent = D), K.appendChild(Y));
          });
          let V = c();
          for (let D of y) {
            let Y = I.insertRow(),
              pe = Y.insertCell();
            pe.style.cssText = "padding:3px 4px;text-align:center;width:24px;";
            let O = document.createElement("input");
            ((O.type = "checkbox"),
              (O.className = "pf-maint-sel"),
              (O.checked = M.get(D.key) || !1),
              O.addEventListener("change", () => {
                (M.set(D.key, O.checked), ae());
              }),
              pe.appendChild(O));
            let j = Y.insertCell();
            j.style.cssText = "padding:3px 4px;";
            let ne = j.createEl("div", { cls: "pf-maint-paper-info" });
            (ne.createEl("div", {
              cls: "pf-maint-paper-title",
              text: D.title || D.key,
            }),
              ne.createEl("div", { cls: "pf-maint-paper-key", text: D.key }));
            let B = Y.insertCell();
            ((B.style.cssText = "padding:3px 4px;"),
              B.createEl("div", {
                cls: "pf-maint-reason",
                text: D.display_reason || "",
              }));
            let q = Y.insertCell();
            q.style.cssText = "padding:3px 4px;white-space:nowrap;";
            let fe = q.createEl("div", { cls: "pf-maint-actions" }),
              be = Ft(D);
            if (be === "rebuild") {
              let ve = fe.createEl("button", {
                cls: "pf-maint-action-btn rebuild",
                text: o("maintenance_btn_rebuild") || "Rebuild",
              });
              (V && (ve.disabled = !0),
                ve.addEventListener("click", async () => {
                  let he = await We(Ye(this.app), "ocr"),
                    ht = de();
                  (0, ee.execFile)(
                    m,
                    [...E, "-m", "paperforge", "ocr", "rebuild", D.key],
                    {
                      cwd: r,
                      timeout: 12e4,
                      windowsHide: !0,
                      env: Object.assign({}, ht, he),
                    },
                    () => {
                      new A.Notice(
                        (o("maintenance_btn_rebuild") || "Rebuild") +
                          " \u2014 " +
                          D.key
                      );
                    }
                  );
                }));
            } else if (be === "redo") {
              let ve = fe.createEl("button", {
                cls: "pf-maint-action-btn redo",
                text: o("ocr_maint_redo_btn") || "Redo",
              });
              (V && (ve.disabled = !0),
                ve.addEventListener("click", async () => {
                  if (
                    Mt("redo") &&
                    !confirm(
                      (
                        o("ocr_maint_redo_confirm") ||
                        "Rerun OCR for {n} paper(s)? Existing derived OCR artifacts will be replaced."
                      ).replace("{n}", "1")
                    )
                  )
                    return;
                  let he = await We(Ye(this.app), "ocr"),
                    ht = de();
                  (0, ee.execFile)(
                    m,
                    [...E, "-m", "paperforge", "ocr", "redo", D.key],
                    {
                      cwd: r,
                      timeout: 3e5,
                      windowsHide: !0,
                      env: Object.assign({}, ht, he),
                    },
                    () => {
                      new A.Notice(
                        (o("ocr_maint_redo_btn") || "Redo OCR") +
                          " \u2014 " +
                          D.key
                      );
                    }
                  );
                }));
            }
          }
          let N = n.createEl("div", { cls: "pf-maint-batch-bar" }),
            re = N.createEl("span", {
              cls: "pf-maint-batch-label",
              text: "0 selected",
            }),
            ae = () => {
              let D = y.filter((Y) => M.get(Y.key)).length;
              re.textContent = D + " selected";
            },
            _e = N.createEl("button", {
              cls: "mod-cta",
              text: o("maintenance_batch_rebuild") || "\u25B6 Rebuild selected",
            });
          _e.disabled = V;
          let se = N.createEl("button", {
            cls: "mod-cta",
            text:
              o("maintenance_batch_redo") || "\u25B6 Full OCR redo selected",
          });
          se.disabled = V;
          let U = async (D) => {
            let Y = y.filter((B) => M.get(B.key) && Ft(B) === D);
            if (Y.length === 0) {
              let B =
                D === "rebuild"
                  ? o("maintenance_btn_rebuild") || "Rebuild"
                  : o("ocr_maint_redo_btn") || "Redo";
              new A.Notice(
                "Selected papers are not eligible for " +
                  B +
                  ". Uncheck ineligible rows and try again.",
                6e3
              );
              return;
            }
            if (
              Mt(D) &&
              !confirm(
                (
                  o("ocr_maint_redo_confirm") ||
                  "Rerun OCR for {n} paper(s)? Existing derived OCR artifacts will be replaced."
                ).replace("{n}", String(Y.length))
              )
            )
              return;
            let pe = Y.map((B) => B.key);
            ((this.plugin._ocrProgress = {
              current: 0,
              total: pe.length,
              key: "",
            }),
              (this.plugin._ocrBuffer = ""),
              (this.plugin._ocrWasStopped = !1));
            let O = D === "rebuild" ? "OCR_REBUILD" : "OCR_REDO";
            ((_e.disabled = !0),
              (se.disabled = !0),
              Array.from(P.querySelectorAll(".pf-maint-action-btn")).forEach(
                (B) => {
                  B.disabled = !0;
                }
              ),
              Array.from(P.querySelectorAll(".pf-maint-sel")).forEach((B) => {
                B.disabled = !0;
              }),
              (f.disabled = !0),
              (v.disabled = !0),
              (T.disabled = !1),
              (T.textContent = o("maintenance_stop") || "Stop"));
            let j = await ge(Ye(this.app), "ocr"),
              ne = this._callPython(["ocr", D, ...pe], {
                env: j,
                onData: (B) => {
                  var ve;
                  let q =
                      typeof B == "string"
                        ? B
                        : Buffer.isBuffer(B)
                          ? B.toString("utf-8")
                          : String(B),
                    { events: fe, buffer: be } = Je(
                      q,
                      (ve = this.plugin._ocrBuffer) != null ? ve : ""
                    );
                  this.plugin._ocrBuffer = be;
                  for (let he of fe)
                    he.event === "START"
                      ? this.plugin._ocrProgress &&
                        (this.plugin._ocrProgress.total = he.total || pe.length)
                      : he.event === "PROGRESS" &&
                        (this.plugin._ocrProgress = {
                          current: he.current || 0,
                          total: he.total || pe.length,
                          key: he.key || "",
                        });
                  F();
                },
                onError: (B) => {
                  ((this.plugin._ocrProcess = null),
                    new A.Notice("Batch error: " + (B.message || B)),
                    p(_));
                },
                onClose: (B) => {
                  (this.plugin._ocrWasStopped || B === 130
                    ? ((this.plugin._ocrWasStopped = !1),
                      (this.plugin._ocrProcess = null),
                      F(),
                      new A.Notice("OCR batch stopped by user."))
                    : B === 0
                      ? (this.plugin._ocrProgress &&
                          (this.plugin._ocrProgress.current =
                            this.plugin._ocrProgress.total),
                        (this.plugin._ocrProcess = null),
                        F(),
                        new A.Notice(
                          (
                            o("maintenance_batch_complete") ||
                            "Batch operation complete \u2014 {n} papers processed."
                          ).replace("{n}", String(pe.length))
                        ))
                      : ((this.plugin._ocrProcess = null),
                        F(),
                        new A.Notice(
                          "Batch operation finished with exit code " + B + ".",
                          8e3
                        )),
                    Lt(r, m, E, a)
                      .then((q) => {
                        ((a = dt(r)), p(q.data));
                      })
                      .catch(() => {
                        p(g);
                      }));
                },
              });
            ((this.plugin._ocrProcess = ne), F());
          };
          (_e.addEventListener("click", () => U("rebuild")),
            se.addEventListener("click", () => U("redo")),
            ae());
        }
      };
    if (a) {
      let _ = Object.values(a.papers);
      p(_);
    } else
      n.createEl("p", {
        text: "\u6B63\u5728\u52A0\u8F7D OCR \u7EF4\u62A4\u6570\u636E\u2026",
      });
    Lt(r, i.path, i.args, a || null)
      .then((_) => {
        ((a = dt(r)), (_.changed || !a) && p(_.data));
      })
      .catch(() => {
        a ||
          (n.empty(),
          n.createEl("p", {
            text: "\u65E0\u6CD5\u52A0\u8F7D OCR \u6570\u636E\u3002\u8BF7\u786E\u4FDD\u5DF2\u5B89\u88C5 paperforge \u5E76\u8FD0\u884C\u8FC7 OCR\u3002",
            cls: "setting-item-description",
          }));
      });
  }
  _renderReleaseNotesTab(e) {
    (e.createEl("h2", { text: "\u66F4\u65B0\u4E0E\u624B\u518C" }),
      e.createEl("h3", { text: "\u7248\u672C\u66F4\u65B0\u8BB0\u5F55" }));
    let t = vr.default.versions || [];
    for (let s of t) {
      let a = e.createEl("div", { cls: "paperforge-release-card" }),
        i = a.createEl("div", { cls: "paperforge-release-header" });
      if (
        (i.createEl("strong", { text: `v${s.version} \u2014 ${s.title}` }),
        i.createEl("span", {
          cls: "paperforge-release-date",
          text: `  (${s.date})`,
        }),
        s.breaking_or_migration && s.breaking_or_migration.length > 0)
      ) {
        let c = a.createEl("div", { cls: "paperforge-release-section" });
        c.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u884C\u4E3A\u53D8\u66F4 / \u8FC1\u79FB\u6CE8\u610F",
        });
        for (let p of s.breaking_or_migration)
          c.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${p}`,
          });
      }
      if (s.new_features && s.new_features.length > 0) {
        let c = a.createEl("div", { cls: "paperforge-release-section" });
        c.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u65B0\u529F\u80FD",
        });
        for (let p of s.new_features)
          c.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${p}`,
          });
      }
      if (s.fixes && s.fixes.length > 0) {
        let c = a.createEl("div", { cls: "paperforge-release-section" });
        c.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u4FEE\u590D",
        });
        for (let p of s.fixes)
          c.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${p}`,
          });
      }
      if (s.recommended_actions && s.recommended_actions.length > 0) {
        let c = a.createEl("div", {
          cls: "paperforge-release-section paperforge-release-recommended",
        });
        c.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u5EFA\u8BAE\u64CD\u4F5C",
        });
        for (let p of s.recommended_actions)
          c.createEl("div", {
            cls: "paperforge-release-item paperforge-release-item-bold",
            text: `\u2022 ${p}`,
          });
      }
    }
    (e.createEl("h3", { text: "\u4F7F\u7528\u624B\u518C" }),
      e
        .createEl("div", { cls: "paperforge-manual-links" })
        .createEl("a", {
          text: "\u2192 \u67E5\u770B\u5B8C\u6574\u4F7F\u7528\u624B\u518C\uFF08GitHub\uFF09",
          href: "https://github.com/LLLin000/PaperForge/blob/master/docs/user-manual.md",
        })
        .setAttr("target", "_blank"));
  }
  _initCapabilityState() {
    let e = this.plugin.settings.capabilityState;
    ((this._capabilityState = Kt(e != null ? e : {}, je)),
      this._persistCapabilityState());
  }
  _persistCapabilityState() {
    this._capabilityState &&
      ((this.plugin.settings.capabilityState = this._capabilityState),
      this.plugin.saveSettings());
  }
  _probeModule(e, t) {
    var c, p, u, _;
    if (this._probing.has(e)) return;
    this._probing.add(e);
    let r = (c = this._capabilityState) == null ? void 0 : c[e],
      n = {
        schema_version: 2,
        module: e,
        capability_state:
          (p = r == null ? void 0 : r.capability_state) != null ? p : "unknown",
        activity_state: "running",
        activity_label: "Probing...",
        activity_progress: null,
        severity: "unknown",
        reason: { code: `${e}.probing`, text: `Checking ${e} status...` },
        action: { primary: e === "maintenance" ? null : $e(e) },
        notices: (u = r == null ? void 0 : r.notices) != null ? u : [],
        user_state: "checking",
        capability_kind:
          e === "installation" || e === "library" ? "required" : "optional",
        maintenance_eligible: !1,
        user_visible_failure: !1,
        user_impact: null,
        updated_at: new Date().toISOString(),
        ttl_seconds: (_ = r == null ? void 0 : r.ttl_seconds) != null ? _ : 0,
      };
    this._updateCapabilityEnvelope(e, n);
    let s = this.app.vault.adapter.basePath,
      a = this._resolveRuntimeCommand(s);
    if (!a) {
      if ((this._probing.delete(e), e === "installation")) {
        let g = {
          schema_version: 2,
          module: "installation",
          capability_state: "unknown",
          activity_state: "idle",
          activity_label: null,
          activity_progress: null,
          severity: "error",
          reason: {
            code: "installation.no_python",
            text: "No Python found. Run the Setup Wizard to install the managed runtime.",
          },
          action: { primary: zt() },
          notices: [],
          user_state: "setup_required",
          capability_kind: "required",
          maintenance_eligible: !1,
          user_visible_failure: !1,
          user_impact: null,
          updated_at: new Date().toISOString(),
          ttl_seconds: 60,
        };
        this._updateCapabilityEnvelope(e, g);
      } else this._updateCapabilityEnvelope(e, Ae(e));
      return;
    }
    let i = [...a.args, "-m", "paperforge", "--vault", s, "probe", e, "--json"];
    (e === "library" &&
      t != null &&
      t !== 0 &&
      i.push("--last-operation-exit-code", String(t)),
      (0, ee.execFile)(a.path, i, { cwd: s, timeout: 15e3 }, (g, h, f) => {
        if ((this._probing.delete(e), g)) {
          (console.warn(`[PaperForge] Probe ${e} failed:`, g.message),
            this._updateCapabilityEnvelope(e, Ae(e)));
          return;
        }
        try {
          let v = JSON.parse(h);
          mt(v, e)
            ? this._updateCapabilityEnvelope(e, v)
            : (console.warn(
                `[PaperForge] Probe ${e}: invalid envelope schema`,
                h == null ? void 0 : h.slice(0, 200)
              ),
              this._updateCapabilityEnvelope(e, Ae(e)));
        } catch (v) {
          (console.warn(
            `[PaperForge] Probe ${e}: unparseable JSON`,
            h == null ? void 0 : h.slice(0, 200)
          ),
            this._updateCapabilityEnvelope(e, Ae(e)));
        }
      }));
  }
  _updateCapabilityEnvelope(e, t) {
    this._capabilityState || (this._capabilityState = {});
    let r = this._capabilityState[t.module];
    (Jt(r, t) && this._lastKnownState.set(e, Gt(t)),
      (this._capabilityState[t.module] = t),
      this._persistCapabilityState(),
      (r == null ? void 0 : r.activity_state) === "running" &&
        t.activity_state !== "running" &&
        (new A.Notice(o("cc_notice_refreshed"), 3e3),
        t.module !== "maintenance"
          ? (this._pendingMaintenanceRefresh ||
              this.activeTab === "maintenance") &&
            this._requestMaintenanceProjection()
          : this._pendingMaintenanceRefresh &&
            ((this._pendingMaintenanceRefresh = !1),
            this._probeModule("maintenance"))),
      this._displayInProgress || this.display());
  }
  _ccBadgeKey(e, t) {
    return e.severity === "ok"
      ? "cc_badge_ok"
      : e.severity === "error" && t === "installation"
        ? "cc_badge_setup"
        : e.severity === "warning" || e.severity === "error"
          ? "cc_badge_attention"
          : "cc_badge_pending";
  }
  _sevClass(e) {
    return e === "error"
      ? "error"
      : e === "warning"
        ? "warn"
        : e === "unknown"
          ? "unknown"
          : "ok";
  }
  _localizeReason(e, t) {
    let r = "cc_reason_" + e.replace(/\./g, "_"),
      n = o(r);
    if (n !== r) return n.replace("{module}", t);
    let a = "cc_reason_" + e.replace(/^[a-z]+\./, ""),
      i = o(a);
    return i === a ? null : i.replace("{module}", t);
  }
  _renderCard(e, t, r) {
    let n = r,
      s = this._sevClass(n.severity),
      a = Ce._REAL_PROBE.has(t),
      i = Ce._NAVIGABLE.has(t),
      c = e.createEl("div", {
        cls: "pf-cc-card pf-open-module-btn",
        attr: {
          role: "listitem",
          tabindex: "0",
          "data-module": t,
          "aria-label": `${o("cc_module_" + t)} \u2014 ${o(this._ccBadgeKey(n, t))}`,
        },
      }),
      p = c.createEl("div", { cls: "pf-cc-card-header" }),
      u = p.createEl("div", { cls: "pf-cc-card-name-area" });
    if (i) {
      let x =
          t === "installation"
            ? o("module_detail_open_installation")
            : t === "library"
              ? o("module_detail_open_library")
              : t === "ocr"
                ? o("module_detail_open_ocr")
                : t === "memory"
                  ? o("module_detail_open_memory")
                  : t === "help"
                    ? o("module_detail_open_help")
                    : t === "maintenance"
                      ? o("module_detail_open_maintenance")
                      : o("md_select_installation"),
        w = u.createEl("button", {
          cls: "pf-open-module-btn",
          text: o("cc_module_" + t),
          attr: { "data-module": t, "aria-label": x },
        });
      (w.addEventListener("click", () => this._handleCardNavigation(t)),
        w.addEventListener("keydown", (R) => {
          (R.key === "Enter" || R.key === " ") &&
            (R.preventDefault(), this._handleCardNavigation(t));
        }));
    } else
      u.createEl("div", { cls: "pf-cc-card-name", text: o("cc_module_" + t) });
    p.createEl("div", {
      cls: `pf-cc-card-badge pf-cc-card-badge--${s}`,
      text: o(this._ccBadgeKey(n, t)),
    });
    let _;
    if (!a)
      _ = o("cc_reason_placeholder").replace("{module}", o("cc_module_" + t));
    else {
      let x = this._localizeReason(n.reason.code, t);
      _ = x != null ? x : n.reason.text;
    }
    if (
      (c.createEl("div", { cls: "pf-cc-card-reason", text: _ }),
      n.activity_state === "running" && n.activity_label)
    ) {
      let x = c.createEl("div", {
        cls: "pf-cc-card-activity",
        attr: { "aria-live": "polite" },
      });
      if (
        (x.createEl("span", { text: n.activity_label }),
        n.activity_progress && n.activity_progress.total > 0)
      ) {
        let w = Math.round(
            (n.activity_progress.current / n.activity_progress.total) * 100
          ),
          S = x
            .createEl("div", {
              cls: "pf-cc-card-progress",
              attr: {
                role: "progressbar",
                "aria-valuenow": String(n.activity_progress.current),
                "aria-valuemin": "0",
                "aria-valuemax": String(n.activity_progress.total),
              },
            })
            .createEl("div", { cls: "pf-cc-card-progress-fill" });
        S.style.width = w + "%";
      }
    }
    let g = c.createEl("div", { cls: "pf-cc-card-footer" });
    if (a && n.action.primary && !ze(n)) {
      let x = Ke(n),
        R =
          x.kind === "setup"
            ? "pf-cc-card-action pf-cc-card-action--primary"
            : "pf-cc-card-action";
      g.createEl("button", {
        cls: R,
        text: x.label,
        attr: { "aria-label": x.label },
      }).addEventListener("click", () => {
        x.kind === "setup"
          ? new ke(this.app, this.plugin, () => {
              (this._probeModule("installation"), this._probeModule("help"));
            }).open()
          : this._dispatchModuleAction(t, n);
      });
    }
    let h = c.createEl("details", { cls: "pf-cc-card-diagnostic" });
    h.createEl("summary", { text: o("cc_diagnostic_toggle") });
    let f = h.createEl("div", { cls: "pf-cc-card-diagnostic-body" }),
      v = o("cc_state_" + n.capability_state) || n.capability_state,
      y = o("cc_severity_" + n.severity) || n.severity,
      m = o("cc_activity_" + n.activity_state) || n.activity_state,
      E;
    try {
      E = new Date(n.updated_at).toLocaleString();
    } catch (x) {
      E = n.updated_at;
    }
    (f.createEl("div", { text: `${o("cc_diag_module")}: ${n.module}` }),
      f.createEl("div", { text: `${o("cc_diag_state")}: ${v}` }),
      f.createEl("div", { text: `${o("cc_diag_severity")}: ${y}` }),
      f.createEl("div", { text: `${o("cc_diag_activity")}: ${m}` }));
    let k = f.createEl("div");
    k.appendText(o("cc_diag_reason") + ": " + _ + " ");
    let b = k.createEl("code", { text: n.reason.code });
    (f.createEl("div", {
      text: `${o("cc_diag_ttl")}: ${String(n.ttl_seconds)}s`,
    }),
      f.createEl("div", { text: `${o("cc_diag_updated")}: ${E}` }));
  }
  _handleCardNavigation(e) {
    (e === "help"
      ? ((this.activeTab = "help"),
        (this._selectedDetailModule = ""),
        (this._focusTargetId = "button.pf-open-module-btn[data-module=help]"))
      : e === "maintenance"
        ? ((this.activeTab = "maintenance"),
          (this._selectedDetailModule = ""),
          (this._focusTargetId = "#pf-maintenance-heading"),
          (this._maintenanceNoticeShown = !1))
        : e === "agent"
          ? ((this.activeTab = "module-detail"),
            (this._selectedDetailModule = "agent"),
            (this._focusTargetId = "#pf-agent-detail-heading"))
          : ((this.activeTab = "module-detail"),
            (this._selectedDetailModule = e),
            (this._focusTargetId = "#pf-" + e + "-detail-heading")),
      this.display());
  }
  _renderControlCenter(e) {
    var m, E, k, b;
    let t = e.createEl("div", { cls: "pf-control-center" }),
      r = (m = this._capabilityState) != null ? m : {},
      n = (E = r.installation) != null ? E : oe("installation"),
      s = (k = r.library) != null ? k : oe("library"),
      a = n.capability_state === "ready" && n.action.primary === null,
      i = s.capability_state === "ready" && s.action.primary === null,
      c = a && i,
      p = 0,
      u = r.maintenance;
    u != null && u.items && Array.isArray(u.items) && (p = u.items.length);
    let _ = t.createEl("div", { cls: "pf-cc-summary" }),
      g = c
        ? o("cc_summary_ready") || "PaperForge is ready"
        : o("cc_summary_incomplete") || "Setup incomplete";
    (_.createEl("div", { cls: "pf-cc-summary-title", text: g }),
      _.createEl("div", {
        cls: "pf-cc-summary-body",
        text: c
          ? o("cc_summary_ready_body") ||
            "Foundation and Library are operational."
          : o("cc_summary_incomplete_body") ||
            "Complete Foundation and Library setup to use PaperForge.",
      }));
    let h = _.createEl("div", { cls: "pf-cc-summary-meta" });
    (p > 0 &&
      h.createEl("span", {
        cls: "pf-cc-summary-maintenance",
        text: p + " item" + (p !== 1 ? "s" : "") + " need attention",
      }),
      h
        .createEl("button", {
          cls: "pf-global-refresh-btn",
          text: o("cc_refresh_btn") || "Refresh Status",
        })
        .addEventListener("click", () => {
          (this._refreshAllModules(), this._probeModule("maintenance"));
        }));
    let v = Object.values(r)
      .map((x) => x.updated_at)
      .filter(Boolean)
      .sort()
      .pop();
    v &&
      h.createEl("span", {
        cls: "pf-last-known",
        text:
          (o("cc_last_checked") || "Last checked: ") +
          new Date(v).toLocaleString(),
      });
    let y = t.createEl("div", {
      cls: "pf-cc-grid",
      attr: { role: "list", "aria-label": "Operational Modules" },
    });
    for (let x of this._getOverviewModules()) {
      let w =
        x.id === "agent"
          ? this._getAgentPlaceholderEnvelope()
          : (b = r[x.id]) != null
            ? b
            : oe(x.id);
      this._renderOverviewCard(y, x.id, x.label, w);
    }
  }
  _getAgentPlaceholderEnvelope() {
    return {
      schema_version: 2,
      module: "agent",
      capability_state: "unknown",
      activity_state: "idle",
      activity_label: null,
      activity_progress: null,
      severity: "unknown",
      reason: {
        code: "agent.not_implemented",
        text: "Agent Integration will be available in a future update.",
      },
      action: { primary: null },
      notices: [],
      user_state: "not_enabled",
      capability_kind: "optional",
      maintenance_eligible: !1,
      user_visible_failure: !1,
      user_impact: null,
      updated_at: new Date(0).toISOString(),
      ttl_seconds: 0,
    };
  }
  _renderOverviewCard(e, t, r, n) {
    let s = e.createEl("button", {
      cls: "pf-cc-card pf-open-module-btn",
      attr: { "data-module": t, role: "listitem" },
    });
    (Ue(s, n.user_state, this._getUserStateLabel(n.user_state)),
      s.createEl("div", { cls: "pf-cc-card-title", text: r }));
    let a = this._getModuleConsequence(t, n);
    (s.createEl("div", { cls: "pf-cc-card-consequence", text: a }),
      n.activity_state === "running" &&
        n.activity_label &&
        qe(s, { label: n.activity_label, progress: n.activity_progress }),
      n.updated_at &&
        n.updated_at !== new Date(0).toISOString() &&
        s.createEl("div", {
          cls: "pf-last-known",
          text:
            (o("cc_last_checked") || "Last checked: ") +
            new Date(n.updated_at).toLocaleString(),
        }),
      n.user_state === "detection_failed" &&
        s
          .createEl("button", {
            cls: "pf-cc-card-retry",
            text: o("cc_card_retry") || "Retry",
          })
          .addEventListener("click", (c) => {
            (c.stopPropagation(), this._probeModule(t));
          }),
      s.addEventListener("click", () => {
        this._handleCardNavigation(t);
      }));
  }
  _getUserStateLabel(e) {
    let t = "cc_badge_" + e;
    return (
      o(t) || e.replace(/_/g, " ").replace(/\b\w/g, (r) => r.toUpperCase())
    );
  }
  _getModuleConsequence(e, t) {
    var c;
    let r = t.user_state,
      n = "cc_consequence_" + e + "_" + r,
      s = o(n);
    if (s && s !== n) return s;
    let a = "cc_consequence_" + r,
      i = o(a);
    return i && i !== a
      ? i
      : ((c = t.reason) == null ? void 0 : c.text) ||
          o("cc_consequence_default") ||
          "Status unknown.";
  }
  _applyStaleTolerance() {
    if (!this._capabilityState) return;
    let e = !1;
    for (let t of je) {
      let r = this._capabilityState[t];
      r && bt(r) && ((this._capabilityState[t] = yt(t)), (e = !0));
    }
    e && this._persistCapabilityState();
  }
  _refreshAllModules() {
    let e = ["installation", "library", "ocr", "memory"];
    for (let t of e) this._probeModule(t);
  }
  _buildAndCopyDiagnostic() {
    var s, a, i;
    let e =
        (a = (s = this.plugin.manifest) == null ? void 0 : s.version) != null
          ? a
          : "unknown",
      t = Yt(
        (i = this._capabilityState) != null ? i : {},
        this._lastKnownState
      ),
      n = Wt({ pluginVersion: e, modules: t });
    Zt(n, () => {
      new A.Notice("Diagnostic copied to clipboard", 3e3);
    });
  }
  _persistNavMemory() {
    ((this.plugin.settings._navMemory = { ...this._navMemory }),
      this.plugin.saveSettings());
  }
  _renderSetupJourney(e) {
    let t = e.createDiv({ cls: "pf-setup-journey" });
    (t.createEl("h2", { text: o("setup_welcome") || "Welcome to PaperForge" }),
      t.createEl("p", {
        text:
          o("setup_desc") ||
          "Let's set up your research environment in a few steps.",
        cls: "pf-setup-desc",
      }));
    let r = [
        "Foundation",
        "Connect Library",
        "Optional Capabilities",
        "Review & Begin",
      ],
      n = t.createDiv({ cls: "pf-setup-progress" });
    r.forEach((a, i) => {
      let c = n.createEl("span", {
        cls:
          "pf-setup-step" +
          (i + 1 === this._setupStage ? " pf-setup-step--active" : "") +
          (i + 1 < this._setupStage ? " pf-setup-step--done" : ""),
        text: String(i + 1) + ". " + a,
      });
    });
    let s = t.createDiv({ cls: "pf-setup-body" });
    switch (this._setupStage) {
      case 1:
        this._renderSetupStageFoundation(s);
        break;
      case 2:
        this._renderSetupStageLibrary(s);
        break;
      case 3:
        this._renderSetupStageOptionals(s);
        break;
      case 4:
        this._renderSetupStageReview(s);
        break;
    }
  }
  _renderSetupStageFoundation(e) {
    var n, s, a, i;
    let t =
      (s = (n = this._capabilityState) == null ? void 0 : n.installation) !=
      null
        ? s
        : oe("installation");
    (e.createEl("h3", { text: "Step 1: Foundation" }),
      e.createEl("p", {
        text:
          o("setup_foundation_desc") ||
          "PaperForge needs a managed environment on this device.",
      }),
      Ue(e, t.user_state),
      t.user_state === "ready"
        ? e.createEl("p", {
            text: o("setup_ready") || "Foundation is ready.",
            cls: "pf-setup-ok",
          })
        : (e.createEl("p", {
            text: ((a = t.reason) == null ? void 0 : a.text) || "Checking...",
            cls: "pf-setup-status",
          }),
          (i = t.action) != null &&
            i.primary &&
            le(e, {
              label: t.action.primary.label,
              onClick: () => {
                this._runAllowedDispatch(
                  "installation",
                  t.action.primary.verb,
                  t.action.primary.command,
                  t
                );
              },
            })));
    let r = e.createDiv({ cls: "pf-setup-nav" });
    le(r, {
      label: t.user_state === "ready" ? "Continue" : "Skip for now",
      onClick: () => {
        ((this._setupStage = 2), this.display());
      },
    });
  }
  _renderSetupStageLibrary(e) {
    var n, s, a, i;
    let t =
      (s = (n = this._capabilityState) == null ? void 0 : n.library) != null
        ? s
        : oe("library");
    (e.createEl("h3", { text: "Step 2: Connect Library" }),
      e.createEl("p", {
        text:
          o("setup_library_desc") ||
          "Connect your Zotero library to sync your literature.",
      }),
      Ue(e, t.user_state),
      t.user_state === "ready"
        ? e.createEl("p", {
            text: o("setup_library_ready") || "Library is connected.",
            cls: "pf-setup-ok",
          })
        : (e.createEl("p", {
            text:
              ((a = t.reason) == null ? void 0 : a.text) ||
              "Not connected yet.",
            cls: "pf-setup-status",
          }),
          (i = t.action) != null &&
            i.primary &&
            le(e, {
              label: t.action.primary.label,
              onClick: () => {
                this._runAllowedDispatch(
                  "library",
                  t.action.primary.verb,
                  t.action.primary.command,
                  t
                );
              },
            })));
    let r = e.createDiv({ cls: "pf-setup-nav" });
    (le(r, {
      label: "Back",
      onClick: () => {
        ((this._setupStage = 1), this.display());
      },
    }),
      le(r, {
        label: "Continue",
        onClick: () => {
          ((this._setupStage = 3), this.display());
        },
      }));
  }
  _renderSetupStageOptionals(e) {
    (e.createEl("h3", { text: "Step 3: Optional Capabilities" }),
      e.createEl("p", {
        text:
          o("setup_optionals_desc") ||
          "Enable additional features. You can change these later.",
      }));
    let t = [
      {
        id: "ocr",
        label: o("cc_module_ocr") || "OCR",
        desc: o("setup_opt_ocr_desc") || "Extract text and figures from PDFs",
      },
      {
        id: "memory",
        label: "Smart Retrieval",
        desc: "Search and navigate your papers",
      },
      {
        id: "agent",
        label: "Agent Integration",
        desc: "Deploy skills to your AI agent",
      },
    ];
    for (let n of t) {
      let s = e.createDiv({ cls: "pf-setup-optional" }),
        a = s.createEl("input", {
          attr: { type: "checkbox", id: "pf-setup-opt-" + n.id },
        });
      ((a.checked = this._setupOptionals[n.id]),
        a.addEventListener("change", () => {
          this._setupOptionals[n.id] = a.checked;
        }),
        s.createEl("label", {
          attr: { for: "pf-setup-opt-" + n.id },
          text: n.label,
          cls: "pf-setup-optional-label",
        }),
        s.createEl("div", { text: n.desc, cls: "pf-setup-optional-desc" }));
    }
    let r = e.createDiv({ cls: "pf-setup-nav" });
    (le(r, {
      label: "Back",
      onClick: () => {
        ((this._setupStage = 2), this.display());
      },
    }),
      le(r, {
        label: "Continue",
        onClick: () => {
          ((this._setupStage = 4), this.display());
        },
      }));
  }
  _renderSetupStageReview(e) {
    var c, p;
    e.createEl("h3", { text: "Step 4: Review & Begin" });
    let t = (c = this._capabilityState) == null ? void 0 : c.installation,
      r = (p = this._capabilityState) == null ? void 0 : p.library,
      n = (t == null ? void 0 : t.user_state) === "ready",
      s = (r == null ? void 0 : r.user_state) === "ready";
    (e.createEl("p", {
      text: n ? "Foundation is ready." : "Foundation needs setup.",
      cls: n ? "pf-setup-ok" : "pf-setup-warn",
    }),
      e.createEl("p", {
        text: s ? "Library is connected." : "Library needs setup.",
        cls: s ? "pf-setup-ok" : "pf-setup-warn",
      }));
    let a = Object.entries(this._setupOptionals)
      .filter(([u, _]) => _)
      .map(([u]) => u);
    a.length > 0
      ? e.createEl("p", {
          text: (o("setup_review_selected") || "Selected: ") + a.join(", "),
        })
      : e.createEl("p", {
          text:
            o("setup_no_optionals") ||
            "No optional capabilities selected. You can enable them later in Settings.",
        });
    let i = e.createDiv({ cls: "pf-setup-nav" });
    (le(i, {
      label: "Back",
      onClick: () => {
        ((this._setupStage = 3), this.display());
      },
    }),
      n && s
        ? le(i, {
            label: "Complete Setup",
            onClick: () => {
              this._completeSetup();
            },
          })
        : (le(i, { label: "Complete Setup", disabled: !0, onClick: () => {} }),
          e.createEl("p", {
            text:
              o("setup_incomplete_warn") ||
              "Complete Foundation and Library setup before finishing.",
            cls: "pf-setup-warn",
          })));
  }
  _completeSetup() {
    ((this.plugin.settings._setup_complete = !0),
      this.plugin.saveSettings(),
      (this.activeTab = "overview"),
      this.display());
  }
  _restoreNavMemory() {
    let e = this.plugin.settings._navMemory;
    e != null &&
      e.destination &&
      ["overview", "maintenance", "help"].includes(e.destination) &&
      ((this.activeTab = e.destination),
      (this._navMemory = { destination: e.destination }),
      (this._focusTargetId = null),
      (this._detailReturn = null),
      (this._setupView = "overview"));
  }
};
((Ce._REAL_PROBE = new Set([
  "installation",
  "library",
  "ocr",
  "memory",
  "help",
  "maintenance",
])),
  (Ce._NAVIGABLE = new Set([
    "installation",
    "library",
    "ocr",
    "memory",
    "maintenance",
    "help",
  ])));
var ut = Ce;
var H = require("obsidian"),
  Re = z(require("fs")),
  _t = z(require("path")),
  ye = require("child_process");
var Xe = z(require("path"));
function Er(d) {
  if (!d) return null;
  let l = Xe.dirname(d);
  for (;;) {
    let e = Xe.basename(l);
    if (!e || e === ".") break;
    let t = e.match(/^([A-Z0-9]{8})(?:\s*-\s*.*)?$/i);
    if (t) return t[1];
    let r = Xe.dirname(l);
    if (r === l) break;
    l = r;
  }
  return null;
}
var W = z(require("fs")),
  we = z(require("path"));
function Qe(d) {
  return ue(d).ocrDir;
}
function tn(d, l) {
  let e = we.join(Qe(d), l, "versions", "manifest.json");
  try {
    if (!W.existsSync(e)) return null;
    let t = W.readFileSync(e, "utf-8"),
      r = JSON.parse(t);
    if (r && typeof r == "object" && "versions" in r && "current" in r) {
      let n = r,
        s = n.versions,
        a = n.current;
      if (Array.isArray(s) && a && typeof a == "object" && "label" in a)
        return r;
    }
    return null;
  } catch (t) {
    return null;
  }
}
function rn(d) {
  let l = Qe(d);
  try {
    return W.existsSync(l)
      ? W.readdirSync(l, { withFileTypes: !0 })
          .filter((e) => e.isDirectory())
          .map((e) => e.name)
      : [];
  } catch (e) {
    return [];
  }
}
function Bt(d) {
  let l = rn(d),
    e = [];
  for (let t of l) {
    let r = tn(d, t);
    if (!r) continue;
    let n = r.versions.map((a) => a.label),
      s = 0;
    for (let a of n) {
      let i = we.join(Qe(d), t, "versions", a, "fulltext.md");
      try {
        W.existsSync(i) && (s += W.statSync(i).size);
      } catch (c) {}
    }
    e.push({
      key: t,
      title: t.replace(/_/g, " "),
      versions: r.versions,
      currentLabel: r.current.label,
      totalSize: s,
    });
  }
  return (e.sort((t, r) => t.title.localeCompare(r.title)), e);
}
function kr(d, l, e) {
  let t = Qe(d),
    r = we.join(t, l, "versions", e, "fulltext.md"),
    n = we.join(t, l, "render"),
    s = we.join(n, "fulltext.md");
  try {
    return W.existsSync(r)
      ? (W.existsSync(n) || W.mkdirSync(n, { recursive: !0 }),
        W.copyFileSync(r, s),
        !0)
      : !1;
  } catch (a) {
    return !1;
  }
}
function wr(d, l, e, t) {
  var g;
  let r = Qe(d),
    n = we.join(r, l, "versions", e, "fulltext.md"),
    s = we.join(r, l, "versions", t, "fulltext.md"),
    a = "",
    i = "";
  try {
    W.existsSync(n) && (a = W.readFileSync(n, "utf-8"));
  } catch (h) {}
  try {
    W.existsSync(s) && (i = W.readFileSync(s, "utf-8"));
  } catch (h) {}
  let c = xr(a),
    p = xr(i),
    u = Math.max(c.length, p.length),
    _ = [];
  for (let h = 0; h < u; h++) {
    let f = h < c.length ? c[h] : "",
      v = h < p.length ? p[h] : "",
      y =
        (g = (f || v).split(`
`)[0]) != null
          ? g
          : "",
      m = y.startsWith("## ") ? y.replace(/^##\s+/, "") : "",
      E = "unchanged";
    (!f && v
      ? (E = "added")
      : f && !v
        ? (E = "removed")
        : f !== v && (E = "changed"),
      E !== "unchanged" &&
        _.push({
          paragraphIndex: h,
          heading: m,
          type: E,
          oldText: f || void 0,
          newText: v || void 0,
        }));
  }
  return _;
}
function xr(d) {
  let l = d.split(`
`),
    e = [],
    t = [];
  for (let r of l)
    if (r.startsWith("## ") && t.length > 0)
      (e.push(
        t
          .join(
            `
`
          )
          .trim()
      ),
        (t = [r]));
    else if (r.trim() === "" && t.length > 0) {
      let n = t
        .join(
          `
`
        )
        .trim();
      n && (e.push(n), (t = []));
    } else t.push(r);
  if (t.length > 0) {
    let r = t
      .join(
        `
`
      )
      .trim();
    r && e.push(r);
  }
  return e;
}
var Be = class extends H.ItemView {
  constructor(e) {
    super(e);
    this._currentMode = null;
    this._currentDomain = null;
    this._currentPaperKey = null;
    this._currentPaperEntry = null;
    this._currentFilePath = null;
    this._cachedItems = null;
    this._modeSubscribers = [];
    this._leafChangeTimer = null;
    this._ocrPrivacyShown = !1;
    this._cachedStats = null;
    this._techDetailsExpanded = !1;
    this._paperforgeVersion = "";
    this._dashboardPermissions = {};
    this._headerTitle = null;
    this._versionBadge = null;
    this._messageEl = null;
    this._metricsEl = null;
    this._ocrSection = null;
    this._ocrEmpty = null;
    this._ocrBadge = null;
    this._ocrTrack = null;
    this._ocrCounts = null;
    this._driftBannerEl = null;
    this._versionPapers = null;
    this._versionFilter = "";
    this._searchContainer = null;
    this._searchInput = null;
    this._searchResultsEl = null;
    this._searchTimer = void 0;
    this._searchState = "idle";
    this._searchMode = "M";
    this._searchResults = null;
    this._searchActiveIndex = -1;
    this._onKeyDown = null;
    ((this._currentMode = null),
      (this._currentDomain = null),
      (this._currentPaperKey = null),
      (this._currentPaperEntry = null),
      (this._currentFilePath = null),
      (this._cachedItems = null),
      (this._modeSubscribers = []),
      (this._leafChangeTimer = null),
      (this._ocrPrivacyShown = !1));
  }
  _resolvePython() {
    var n;
    let e = this.app.plugins.plugins.paperforge,
      t =
        (n = e == null ? void 0 : e.getManagedRuntime) == null
          ? void 0
          : n.call(e);
    if (!t) return null;
    let r = xe(t.current());
    return r ? { path: r.command, args: [...r.args] } : null;
  }
  getViewType() {
    return Se;
  }
  getDisplayText() {
    return "PaperForge";
  }
  getIcon() {
    return He;
  }
  async onOpen() {
    (this._buildPanel(),
      (this._modeSubscribers = []),
      (this._leafChangeTimer = null),
      this._setupEventSubscriptions(),
      this._fetchVersion(),
      this._detectAndSwitch(),
      (this._onKeyDown = (e) => {
        var t, r, n;
        if (e.key === "/" && !e.ctrlKey && !e.metaKey && !e.altKey) {
          let s =
            (r = (t = e.target) == null ? void 0 : t.tagName) == null
              ? void 0
              : r.toLowerCase();
          s !== "input" &&
            s !== "textarea" &&
            (e.preventDefault(), (n = this._searchInput) == null || n.focus());
        }
      }),
      document.addEventListener("keydown", this._onKeyDown));
  }
  async onClose() {
    if (this._modeSubscribers && this._modeSubscribers.length > 0) {
      for (let e of this._modeSubscribers)
        e.event === "active-leaf-change"
          ? this.app.workspace.off("active-leaf-change", e.ref)
          : e.event === "modify" && this.app.vault.off("modify", e.ref);
      this._modeSubscribers = [];
    }
    (this._leafChangeTimer &&
      (clearTimeout(this._leafChangeTimer), (this._leafChangeTimer = null)),
      this._onKeyDown &&
        (document.removeEventListener("keydown", this._onKeyDown),
        (this._onKeyDown = null)),
      (this._searchState = "idle"),
      (this._searchResults = null),
      (this._searchActiveIndex = -1),
      (this._searchTimer = void 0),
      (this._cachedItems = null),
      (this._cachedStats = null));
  }
  _buildPanel() {
    let e = this.containerEl;
    (e.empty(), e.addClass("paperforge-status-panel"));
    let t = e.createEl("div", { cls: "paperforge-header" }),
      r = t.createEl("div", { cls: "paperforge-header-left" });
    (r.createEl("div", { cls: "paperforge-header-logo", text: "P" }),
      (this._modeContextEl = r.createEl("div", {
        cls: "paperforge-mode-context",
      })),
      (this._headerTitle = r.createEl("h3", {
        cls: "paperforge-header-title",
        text: "PaperForge",
      })),
      (this._versionBadge = r.createEl("span", {
        cls: "paperforge-header-badge",
        text: "v\u2014",
      })));
    let n = t.createEl("button", {
      cls: "paperforge-header-refresh",
      attr: { "aria-label": "Refresh" },
    });
    ((n.innerHTML = "\u21BB"),
      n.addEventListener("click", () => {
        (this._invalidateIndex(), this._detectAndSwitch());
      }),
      (this._messageEl = e.createEl("div", {
        cls: "paperforge-message",
        attr: { "aria-live": "polite" },
      })),
      (this._contentEl = e.createEl("div", {
        cls: "paperforge-content-area",
      })));
  }
  _fetchVersion() {
    var i;
    let e = this.app.vault.adapter.basePath,
      t = this.app.plugins.plugins.paperforge,
      r =
        ((i = t == null ? void 0 : t.manifest) == null ? void 0 : i.version) ||
        "?",
      n = this._resolvePython();
    if (!n) return;
    let { path: s, args: a = [] } = n;
    Promise.resolve({ status: "ok", pyVersion: "?" }).then((c) => {
      if (c.status === "not-installed") return;
      let p = c.pyVersion || "";
      ((this._paperforgeVersion = p.startsWith("v") ? p : "v" + p),
        this._versionBadge &&
          this._versionBadge.setText(this._paperforgeVersion),
        this._driftBannerEl &&
        r &&
        this._paperforgeVersion !== "v" + r.replace(/^v/, "")
          ? ((this._driftBannerEl.style.display = "block"),
            this._driftBannerEl.setText(
              o("dashboard_drift_warning")
                .replace("{0}", this._paperforgeVersion)
                .replace("{1}", "v" + r.replace(/^v/, ""))
            ))
          : this._driftBannerEl &&
            (this._driftBannerEl.style.display = "none"));
    });
  }
  _fetchStats(e) {
    if (!this._metricsEl) return;
    if (!e && !this._cachedStats)
      (this._metricsEl.empty(),
        this._metricsEl.createEl("div", {
          cls: "paperforge-status-loading",
          text: "Loading...",
        }));
    else if (e && !this._cachedStats) return;
    let t = this.app.vault.adapter.basePath,
      r = this.app.plugins.plugins.paperforge,
      n = this._resolvePython();
    if (!n) {
      this._fallbackFetchStats(e, t, r);
      return;
    }
    let { path: s, args: a = [] } = n;
    (0, ye.execFile)(
      s,
      [...a, "-m", "paperforge", "dashboard", "--json"],
      { cwd: t, timeout: 3e4 },
      (i, c) => {
        if (!i)
          try {
            let p = JSON.parse(c);
            if (p.ok && p.data) {
              let u = this._normalizeDashboardData(p.data);
              ((this._cachedStats = u),
                this._metricsEl.empty(),
                this._renderStats(u),
                this._renderOcr(u),
                (this._dashboardPermissions = p.data.permissions || {}));
              return;
            }
          } catch (p) {}
        this._fallbackFetchStats(e, t, r);
      }
    );
  }
  _normalizeDashboardData(e) {
    let t = e.stats || {},
      r = t.ocr_health || {},
      n = t.pdf_health || {},
      s = e.ocr_version_state || {},
      a = (r.done || 0) + (r.pending || 0) + (r.failed || 0);
    return {
      total_papers: t.papers || 0,
      formal_notes: t.papers || 0,
      exports: 0,
      bases: 0,
      ocr: {
        total: a,
        pending: r.pending || 0,
        processing: 0,
        done: r.done || 0,
        failed: r.failed || 0,
      },
      path_errors: (n.broken || 0) + (n.missing || 0),
      ocr_version_state: {
        total_papers: s.total_papers || 0,
        derived_stale_count: s.derived_stale_count || 0,
        raw_upgradable_count: s.raw_upgradable_count || 0,
      },
    };
  }
  _fallbackFetchStats(e, t, r) {
    var a, i;
    let n =
        ((a = r == null ? void 0 : r.settings) == null
          ? void 0
          : a.system_dir) || "System",
      s = _t.join(t, n, "PaperForge", "indexes", "formal-library.json");
    try {
      let c = Re.readFileSync(s, "utf-8"),
        p = JSON.parse(c),
        u = p.items || [],
        _ = {},
        g = {
          pdf_health: { healthy: 0, unhealthy: 0 },
          ocr_health: { healthy: 0, unhealthy: 0 },
          note_health: { healthy: 0, unhealthy: 0 },
          asset_health: { healthy: 0, unhealthy: 0 },
        },
        h = 0,
        f = 0,
        v = 0,
        y = 0,
        m = 0,
        E = 0;
      for (let k of u) {
        k.note_path && E++;
        let b = k.lifecycle || "pdf_ready";
        _[b] = (_[b] || 0) + 1;
        let x = k.health || {};
        for (let R of [
          "pdf_health",
          "ocr_health",
          "note_health",
          "asset_health",
        ])
          (x[R] || "healthy") === "healthy" ? g[R].healthy++ : g[R].unhealthy++;
        let w = k.ocr_status || "";
        (h++,
          w === "done"
            ? f++
            : w === "pending"
              ? v++
              : w === "processing" || w === "queued" || w === "running"
                ? y++
                : m++);
      }
      ((this._cachedStats = {
        version:
          p.paperforge_version ||
          ((i = this._cachedStats) == null ? void 0 : i.version) ||
          "\u2014",
        total_papers: u.length,
        formal_notes: E,
        exports: 0,
        bases: 0,
        ocr: { total: h, pending: v, processing: y, done: f, failed: m },
        path_errors: 0,
        lifecycle_level_counts: _,
        health_aggregate: g,
      }),
        this._metricsEl.empty(),
        this._renderStats(this._cachedStats),
        this._renderOcr(this._cachedStats));
    } catch (c) {
      !e &&
        !this._cachedStats &&
        this._metricsEl.createEl("div", {
          cls: "paperforge-status-loading",
          text: "No index \u2014 trying CLI...",
        });
      let p = this._resolvePython();
      if (!p) {
        this._cachedStats ||
          this._metricsEl.createEl("div", {
            cls: "paperforge-status-error",
            text: `Cannot reach PaperForge CLI.
Make sure paperforge is installed and in your PATH.`,
          });
        return;
      }
      let { path: u, args: _ = [] } = p;
      (0, ye.execFile)(
        u,
        [..._, "-m", "paperforge", "status", "--json"],
        { cwd: t, timeout: 3e4 },
        (g, h) => {
          if (g) {
            if (this._cachedStats) return;
            this._metricsEl.createEl("div", {
              cls: "paperforge-status-error",
              text: `Cannot reach PaperForge CLI.
Make sure paperforge is installed and in your PATH.`,
            });
            return;
          }
          try {
            let f = JSON.parse(h);
            ((this._cachedStats = f),
              this._metricsEl.empty(),
              this._renderStats(f),
              this._renderOcr(f));
          } catch (f) {
            this._cachedStats ||
              this._metricsEl.createEl("div", {
                cls: "paperforge-status-error",
                text: "Invalid response from paperforge status.",
              });
          }
        }
      );
    }
  }
  _renderSkeleton(e) {
    e.addClass("paperforge-loading");
  }
  _renderEmptyState(e, t) {
    e.createEl("div", { cls: "paperforge-empty-state", text: t || "No data" });
  }
  _buildMetricBar(e, t, r) {
    if (r <= 0) return;
    let n = Math.min(100, (t / r) * 100);
    e.createEl("div", { cls: "paperforge-metric-progress" }).createEl("div", {
      cls: "paperforge-metric-progress-fill",
      attr: { style: `width:${n.toFixed(1)}%` },
    });
  }
  _loadIndex() {
    var s;
    let e = this.app.vault.adapter.basePath,
      t = this.app.plugins.plugins.paperforge,
      r =
        ((s = t == null ? void 0 : t.settings) == null
          ? void 0
          : s.system_dir) || "System",
      n = _t.join(e, r, "PaperForge", "indexes", "formal-library.json");
    try {
      let a = Re.readFileSync(n, "utf-8");
      return JSON.parse(a);
    } catch (a) {
      return null;
    }
  }
  _getCachedIndex() {
    if (!this._cachedItems) {
      let e = this._loadIndex();
      this._cachedItems = e ? e.items || [] : [];
    }
    return this._cachedItems;
  }
  _findEntry(e) {
    if (!e) return null;
    let t = this._getCachedIndex().find((r) => r.zotero_key === e) || null;
    return $t(this.app, t);
  }
  _patchCachedEntry(e, t) {
    if (!e || !this._cachedItems) return;
    let r = this._cachedItems.findIndex((n) => n.zotero_key === e);
    r !== -1 && (this._cachedItems[r] = gt(this._cachedItems[r], t));
  }
  _filterByDomain(e) {
    return e ? this._getCachedIndex().filter((t) => t.domain === e) : [];
  }
  _renderStats(e) {
    var a;
    if (
      (this._versionBadge &&
        this._versionBadge.setText(
          this._paperforgeVersion || (e.version ? "v" + e.version : "v\u2014")
        ),
      !e || typeof e.total_papers == "undefined")
    ) {
      this._metricsEl && this._renderSkeleton(this._metricsEl);
      return;
    }
    if (!this._metricsEl) return;
    this._metricsEl.removeClass("paperforge-loading");
    let t = e.total_papers || 0,
      r = e.formal_notes || 0,
      n = [
        { value: t, label: "Papers", color: "var(--color-cyan)", barMax: 0 },
        {
          value: r,
          label: "Formal Notes",
          color: "var(--color-blue)",
          barMax: t,
        },
        {
          value: e.exports || 0,
          label: "Exports",
          color: "var(--color-purple)",
          barMax: 0,
        },
      ];
    for (let i of n) {
      let c = this._metricsEl.createEl("div", {
        cls: "paperforge-metric-card",
      });
      (c.style.setProperty("--metric-color", i.color),
        c.createEl("div", {
          cls: "paperforge-metric-value",
          text: ((a = i.value) == null ? void 0 : a.toString()) || "\u2014",
        }),
        c.createEl("div", { cls: "paperforge-metric-label", text: i.label }),
        i.barMax > 0 && this._buildMetricBar(c, i.value, i.barMax));
    }
    let s = e.ocr_version_state || {};
    if (
      s.total_papers > 0 &&
      (s.derived_stale_count > 0 || s.raw_upgradable_count > 0)
    ) {
      let i = [];
      (s.derived_stale_count > 0 && i.push(`${s.derived_stale_count} stale`),
        s.raw_upgradable_count > 0 &&
          i.push(`${s.raw_upgradable_count} upgradable`));
      let c = this._metricsEl.createEl("div", {
        cls: "paperforge-metric-card",
      });
      (c.style.setProperty("--metric-color", "var(--color-yellow)"),
        c.createEl("div", {
          cls: "paperforge-metric-value",
          text: i.join(", "),
        }),
        c.createEl("div", {
          cls: "paperforge-metric-label",
          text: "OCR Version",
        }));
    }
  }
  _renderOcr(e) {
    if (!this._ocrSection) return;
    let t = e.ocr || {},
      r = t.total || 0;
    if (r === 0) {
      this._ocrSection.style.display = "none";
      return;
    }
    ((this._ocrSection.style.display = "block"),
      this._ocrEmpty && (this._ocrEmpty.style.display = "none"));
    let n = t.done || 0,
      s = t.pending || 0,
      a = t.processing || 0,
      i = t.failed || 0;
    if (
      (this._ocrBadge &&
        (this._ocrBadge.removeClass("active", "idle"),
        a > 0
          ? (this._ocrBadge.addClass("active"),
            this._ocrBadge.setText("Processing"))
          : s > 0
            ? (this._ocrBadge.addClass("idle"),
              this._ocrBadge.setText("Pending"))
            : (this._ocrBadge.addClass("idle"),
              this._ocrBadge.setText("Idle"))),
      this._ocrTrack)
    ) {
      (this._ocrTrack.empty(),
        a > 0
          ? this._ocrTrack.addClass("paperforge-processing")
          : this._ocrTrack.removeClass("paperforge-processing"));
      let c = [
        { cls: "pending", count: s },
        { cls: "active", count: a },
        { cls: "done", count: n },
        { cls: "failed", count: i },
      ];
      for (let p of c)
        if (p.count > 0) {
          let u = ((p.count / r) * 100).toFixed(1);
          this._ocrTrack.createEl("div", {
            cls: `paperforge-progress-seg ${p.cls}`,
            attr: { style: `width:${u}%` },
          });
        }
    }
    if (this._ocrCounts) {
      this._ocrCounts.empty();
      let c = [
        { cls: "pending", value: s, label: "Pending" },
        { cls: "active", value: a, label: "Processing" },
        { cls: "done", value: n, label: "Done" },
        { cls: "failed", value: i, label: "Failed" },
      ];
      for (let p of c) {
        let u = this._ocrCounts.createEl("div", {
          cls: "paperforge-ocr-count",
        });
        (u.createEl("div", {
          cls: "paperforge-ocr-count-value",
          text: p.value.toString(),
        }),
          u.createEl("div", {
            cls: "paperforge-ocr-count-label",
            text: p.label,
          }));
      }
    }
  }
  _renderLifecycleStepper(e, t, r) {
    if (!t || !r) {
      this._renderSkeleton(e);
      return;
    }
    let n = [
        { key: "indexed", label: "Indexed" },
        { key: "pdf_ready", label: "PDF Ready" },
        { key: "fulltext_ready", label: "Fulltext Ready" },
        { key: "deep_read_done", label: "Deep Read" },
      ],
      s = e.createEl("div", { cls: "paperforge-lifecycle-stepper" }),
      a = !1;
    for (let i of n) {
      let c = s.createEl("div", { cls: "step" });
      (c.createEl("div", { cls: "step-indicator" }),
        c.createEl("div", { cls: "step-label", text: i.label }),
        i.key === r
          ? (c.addClass("current"), (a = !0))
          : a
            ? c.addClass("pending")
            : c.addClass("completed"));
    }
  }
  _renderHealthMatrix(e, t) {
    if (!t) {
      this._renderSkeleton(e);
      return;
    }
    let r = [
        {
          key: "pdf_health",
          label: "PDF Health",
          iconOk: "\u2713",
          iconWarn: "\u26A0",
          iconFail: "\u2717",
        },
        {
          key: "ocr_health",
          label: "OCR Health",
          iconOk: "\u2713",
          iconWarn: "\u26A0",
          iconFail: "\u2717",
        },
        {
          key: "note_health",
          label: "Note Health",
          iconOk: "\u2713",
          iconWarn: "\u26A0",
          iconFail: "\u2717",
        },
        {
          key: "asset_health",
          label: "Asset Health",
          iconOk: "\u2713",
          iconWarn: "\u26A0",
          iconFail: "\u2717",
        },
      ],
      n = e.createEl("div", { cls: "paperforge-health-matrix" });
    for (let s of r) {
      let a = t[s.key] || "healthy",
        i = n.createEl("div", { cls: "paperforge-health-cell" }),
        c,
        p,
        u;
      (a === "healthy" || a === "ok"
        ? ((c = s.iconOk), (p = "ok"), (u = `${s.label}: OK`))
        : a === "warn" || a === "warning" || a === "degraded"
          ? ((c = s.iconWarn),
            (p = "warn"),
            (u = `${s.label}: Needs Attention`))
          : ((c = s.iconFail), (p = "fail"), (u = `${s.label}: Failed`)),
        i.addClass(p),
        i.setAttribute("title", u),
        i.createEl("div", { cls: "paperforge-health-cell-icon", text: c }),
        i.createEl("div", {
          cls: "paperforge-health-cell-label",
          text: s.label,
        }));
    }
  }
  _renderMaturityGauge(e, t, r) {
    if (t == null || t === void 0) {
      this._renderSkeleton(e);
      return;
    }
    let n = e.createEl("div", { cls: "paperforge-maturity-gauge" }),
      s = n.createEl("div", { cls: "gauge-track" }),
      a = 4,
      i = Math.max(1, Math.min(a, Math.round(t)));
    for (let c = 1; c <= a; c++) {
      let p = s.createEl("div", { cls: "gauge-segment" });
      c <= i && (p.addClass("filled"), p.addClass(`level-${c}`));
    }
    if (
      (n.createEl("div", { cls: "gauge-level", text: `Level ${i} / ${a}` }),
      i < a && r)
    ) {
      let c = typeof r == "string" ? [r] : r;
      if (c.length > 0) {
        let p = n.createEl("ul", { cls: "gauge-blockers" });
        for (let u of c) p.createEl("li", { text: u });
      }
    }
  }
  _renderBarChart(e, t) {
    if (!t || Object.keys(t).length === 0) {
      this._renderEmptyState(e, "No lifecycle data");
      return;
    }
    let r = [
        { key: "indexed", label: "Indexed", cls: "stage-indexed" },
        { key: "pdf_ready", label: "PDF Ready", cls: "stage-pdf-ready" },
        {
          key: "fulltext_ready",
          label: "Fulltext Ready",
          cls: "stage-fulltext-ready",
        },
        { key: "deep_read_done", label: "Deep Read", cls: "stage-deep-read" },
      ],
      n = e.createEl("div", { cls: "paperforge-bar-chart" }),
      s = Math.max(1, ...r.map((a) => t[a.key] || 0));
    for (let a of r) {
      let i = t[a.key] || 0,
        c = (i / s) * 100,
        p = n.createEl("div", { cls: "bar-row" });
      (p.createEl("div", { cls: "bar-label", text: a.label }),
        p
          .createEl("div", { cls: "bar-track" })
          .createEl("div", {
            cls: `bar-fill ${a.cls}`,
            attr: { style: `width:${c.toFixed(1)}%` },
          }),
        p.createEl("div", { cls: "bar-count", text: i.toString() }));
    }
  }
  _invalidateIndex() {
    this._cachedItems = null;
  }
  _extractZoteroKeyFromPath(e) {
    return Er(e);
  }
  _resolveModeForFile(e) {
    if (!e) return { mode: "global", filePath: null, key: null, domain: null };
    let t = e.extension,
      r = e.path;
    if (t === "base")
      return {
        mode: "collection",
        filePath: r,
        key: null,
        domain: e.basename.trim(),
      };
    if (t === "md") {
      let s = this.app.metadataCache.getFileCache(e),
        a = s && s.frontmatter && s.frontmatter.zotero_key;
      if (a) return { mode: "paper", filePath: r, key: a, domain: null };
    }
    if (t === "pdf") {
      let s = this._getCachedIndex();
      for (let a of s) {
        let i = (a.pdf_path || "").match(/\[\[([^\]]+)\]\]/);
        if ((i ? i[1] : a.pdf_path) === r)
          return {
            mode: "paper",
            filePath: r,
            key: a.zotero_key,
            domain: null,
          };
      }
    }
    let n = this._extractZoteroKeyFromPath(r);
    return n
      ? { mode: "paper", filePath: r, key: n, domain: null }
      : { mode: "global", filePath: r, key: null, domain: null };
  }
  _detectAndSwitch() {
    let e = this._resolveModeForFile(this.app.workspace.getActiveFile());
    ((this._currentDomain = e.domain || null),
      (this._currentPaperKey = e.key || null),
      (this._currentPaperEntry = e.key ? this._findEntry(e.key) : null),
      this._switchMode(e.mode, e.filePath));
  }
  _switchMode(e, t) {
    if (this._currentMode === e && this._currentFilePath === t) {
      this._refreshCurrentMode();
      return;
    }
    if (
      ((this._currentMode = e),
      (this._currentFilePath = t),
      (this._techDetailsExpanded = !1),
      !!this._contentEl)
    )
      switch (
        (this._contentEl.empty(),
        this._contentEl.removeClass("switching"),
        this._renderModeHeader(e),
        e)
      ) {
        case "global":
          this._renderGlobalMode();
          break;
        case "paper":
          this._renderPaperMode();
          break;
        case "collection":
          this._renderCollectionMode();
          break;
        case "versions":
          this._renderVersionMode();
          break;
      }
  }
  _renderGlobalMode() {
    var ae, _e, se, U, D, Y, pe;
    if (!this._contentEl) return;
    let e = this._contentEl.createEl("div", { cls: "paperforge-global-view" });
    ((this._driftBannerEl = e.createEl("div", {
      cls: "paperforge-drift-banner",
    })),
      (this._driftBannerEl.style.display = "none"));
    let t = this._getCachedIndex(),
      r = t.length,
      n = 0,
      s = 0,
      a = 0;
    for (let O of t)
      (O.has_pdf && n++,
        O.ocr_status === "done" && s++,
        O.deep_reading_status === "done" && a++);
    let i = e.createEl("div", { cls: "paperforge-library-snapshot" });
    i.createEl("div", {
      cls: "paperforge-section-label",
      text: "Library Snapshot",
    });
    let c = i.createEl("div", { cls: "paperforge-snapshot-pills" }),
      p = [
        { value: r, label: "papers" },
        { value: n, label: "PDFs ready" },
        { value: s, label: "OCR done" },
        { value: a, label: "deep-read done" },
      ];
    for (let O of p) {
      let j = c.createEl("div", { cls: "paperforge-snapshot-pill" });
      (j.createEl("span", {
        cls: "paperforge-snapshot-value",
        text: String(O.value),
      }),
        j.createEl("span", {
          cls: "paperforge-snapshot-label",
          text: " " + O.label,
        }));
    }
    let u = e.createEl("div", { cls: "paperforge-system-status" });
    u.createEl("div", {
      cls: "paperforge-section-label",
      text: "System Status",
    });
    let _ = u.createEl("div", { cls: "paperforge-status-grid" }),
      g = this.app.plugins.plugins.paperforge,
      h =
        ((ae = g == null ? void 0 : g.manifest) == null
          ? void 0
          : ae.version) || "?",
      f = this._paperforgeVersion;
    if (!f) {
      let O = this._resolvePython();
      if (O) {
        let { path: j, args: ne = [] } = O;
        try {
          let B = this.app.vault.adapter.basePath,
            q = (0, ye.execFileSync)(
              j,
              [...ne, "-c", "import paperforge; print(paperforge.__version__)"],
              { cwd: B, timeout: 5e3, encoding: "utf-8", windowsHide: !0 }
            ).trim();
          q &&
            ((f = q.startsWith("v") ? q : "v" + q),
            (this._paperforgeVersion = f));
        } catch (B) {}
      }
    }
    f = f || "\u2014";
    let v = f === "v" + h;
    this._renderSystemStatusRow(
      _,
      "Runtime",
      v ? "healthy" : "mismatch",
      v ? "v" + h : "plugin v" + h + " \u2260 CLI " + f
    );
    let y = this._loadIndex(),
      m = y && y.items && y.items.length > 0;
    this._renderSystemStatusRow(
      _,
      "Index",
      m ? "healthy" : "missing",
      m ? y.items.length + " entries" : "formal-library.json not found"
    );
    let E =
        ((_e = g == null ? void 0 : g.settings) == null
          ? void 0
          : _e.system_dir) || "System",
      k = this.app.vault.adapter.basePath,
      b = !1,
      x = "No exports found";
    try {
      let O = _t.join(k, E, "PaperForge", "exports");
      if (Re.existsSync(O)) {
        let j = Re.readdirSync(O).filter((ne) => ne.endsWith(".json"));
        ((b = j.length > 0),
          (x = b ? j.length + " export(s)" : "No JSON exports"));
      }
    } catch (O) {}
    this._renderSystemStatusRow(
      _,
      "Zotero Export",
      b ? "healthy" : "missing",
      x
    );
    let w =
        (U = (se = this.app.plugins) == null ? void 0 : se.plugins) == null
          ? void 0
          : U.paperforge,
      R = !!(
        (D = w == null ? void 0 : w.settings) != null && D._paddleocr_configured
      );
    this._renderSystemStatusRow(
      _,
      "OCR Token",
      R ? "configured" : "missing",
      R ? "Configured" : "Not set"
    );
    let S = !1,
      T = "",
      F = this.app.vault.adapter.basePath,
      M = Ze(F);
    ((S = sr(F)),
      (T =
        (M && ((Y = M.summary) == null ? void 0 : Y.reason)) ||
        (M && ((pe = M.summary) == null ? void 0 : pe.status)) ||
        "Unknown"),
      this._renderSystemStatusRow(
        _,
        "Memory Layer",
        S ? "healthy" : "fail",
        T
      ));
    let P = !v && f !== "\u2014";
    if (P || !m || !b || !R) {
      let O = e.createEl("div", { cls: "paperforge-issue-summary" });
      O.createEl("div", {
        cls: "paperforge-section-label",
        text: "\u9700\u8981\u5904\u7406",
      });
      let j = O.createEl("div", { cls: "paperforge-issue-list" });
      (P &&
        j.createEl("div", {
          cls: "paperforge-issue-item",
          text: "Runtime version mismatch",
        }),
        m ||
          j.createEl("div", {
            cls: "paperforge-issue-item",
            text: "Index missing or corrupted",
          }),
        b ||
          j.createEl("div", {
            cls: "paperforge-issue-item",
            text: "No Zotero export found",
          }),
        R ||
          j.createEl("div", {
            cls: "paperforge-issue-item",
            text: "PaddleOCR API key not configured",
          }));
      let ne = O.createEl("div", { cls: "paperforge-issue-actions" }),
        B = ne.createEl("button", { cls: "paperforge-contextual-btn" });
      (B.createEl("span", { text: "Run Doctor" }),
        B.addEventListener("click", () => {
          let fe = ie.find((be) => be.id === "paperforge-doctor");
          fe && this._runAction(fe, B);
        }));
      let q = ne.createEl("button", { cls: "paperforge-contextual-btn" });
      (q.createEl("span", { text: "Repair Issues" }),
        q.addEventListener("click", () => {
          let fe = ie.find((be) => be.id === "paperforge-repair");
          fe && this._runAction(fe, q);
        }));
    }
    let C = e.createEl("div", { cls: "paperforge-global-actions" });
    C.createEl("div", {
      cls: "paperforge-section-label",
      text: "Start Working",
    });
    let I = C.createEl("div", { cls: "paperforge-global-actions-row" }),
      K = I.createEl("button", { cls: "paperforge-contextual-btn primary" });
    (K.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u{1F4C1}",
    }),
      K.createEl("span", { text: "Open Literature Hub" }),
      K.addEventListener("click", () => {
        var ne;
        let O =
            ((ne = g == null ? void 0 : g.settings) == null
              ? void 0
              : ne.base_dir) || "Bases",
          j = this.app.vault.getAbstractFileByPath(O);
        if (j) {
          let B = null;
          if (
            (j.children && (B = j.children.find((q) => q.extension === "base")),
            B)
          ) {
            let q = this.app.workspace.getLeaf(!1);
            q && q.openFile(B);
          } else new H.Notice("[!!] No .base file found in " + O, 6e3);
        } else new H.Notice("[!!] Base directory not found: " + O, 6e3);
      }));
    let V = I.createEl("button", { cls: "paperforge-contextual-btn" });
    (V.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    }),
      V.createEl("span", { text: "Sync Library" }),
      V.addEventListener("click", () => {
        let O = ie.find((j) => j.id === "paperforge-sync");
        O && this._runAction(O, V);
      }));
    let N = I.createEl("button", { cls: "paperforge-contextual-btn" });
    (N.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    }),
      N.createEl("span", { text: "Run OCR" }),
      N.addEventListener("click", () => {
        let O = ie.find((j) => j.id === "paperforge-ocr");
        O && this._runAction(O, N);
      }));
    let re = I.createEl("button", { cls: "paperforge-contextual-btn warn" });
    (re.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BA",
    }),
      re.createEl("span", { text: "Redo OCR" }),
      re.addEventListener("click", () => {
        let O = ie.find((j) => j.id === "paperforge-ocr-redo");
        O && this._runAction(O, re);
      }));
  }
  _renderSystemStatusRow(e, t, r, n) {
    let s = e.createEl("div", { cls: "paperforge-status-row" });
    (s
      .createEl("span", { cls: "paperforge-status-dot" })
      .addClass(r === "healthy" || r === "configured" ? "ok" : "fail"),
      s.createEl("span", { cls: "paperforge-status-label", text: t }),
      s.createEl("span", { cls: "paperforge-status-detail", text: n || "" }));
  }
  _renderPaperMode() {
    let e = this._currentPaperEntry,
      t = this._currentPaperKey;
    if (!this._contentEl) return;
    if (!t) {
      this._renderEmptyState(this._contentEl, "No paper data available.");
      return;
    }
    if (!e) {
      this._contentEl.createEl("div", {
        cls: "paperforge-content-placeholder",
        text: 'Paper "' + t + '" not found in canonical index. Sync first.',
      });
      return;
    }
    let r = this._contentEl.createEl("div", { cls: "paperforge-paper-view" }),
      n = r.createEl("div", { cls: "paperforge-paper-header" });
    n.createEl("div", {
      cls: "paperforge-paper-title pf-copy",
      text: e.title || "Untitled",
    }).addEventListener("click", () => {
      (navigator.clipboard.writeText(e.title || ""),
        new H.Notice("Title copied"));
    });
    let a = n.createEl("div", { cls: "paperforge-paper-meta" });
    (e.authors &&
      e.authors.length > 0 &&
      a.createEl("span", {
        cls: "paperforge-paper-authors",
        text: e.authors.join(", "),
      }),
      e.year &&
        a.createEl("span", {
          cls: "paperforge-paper-year",
          text: String(e.year),
        }));
    let i = r.createEl("div", { cls: "paperforge-status-strip" }),
      c = i.createEl("div", { cls: "paperforge-status-strip-left" }),
      p = i.createEl("div", { cls: "paperforge-status-strip-right" }),
      u = [
        { key: "pdf", label: "PDF", ok: e.has_pdf === !0 },
        {
          key: "ocr",
          label: "OCR",
          ok: e.ocr_status === "done",
          pending: ["pending", "queued", "processing"].includes(
            e.ocr_status || ""
          ),
          fail: ["failed", "blocked", "done_incomplete", "nopdf"].includes(
            e.ocr_status || ""
          ),
        },
        {
          key: "deep",
          label: "\u7CBE\u8BFB",
          ok: e.deep_reading_status === "done",
        },
      ];
    for (let g of u) {
      let h = c.createEl("span", { cls: "paperforge-status-pill" }),
        f = "pending";
      (g.ok ? (f = "ok") : g.fail ? (f = "fail") : g.pending && (f = "pending"),
        h.addClass(f));
      let v = g.ok ? "\u2713" : g.fail ? "\u2717" : "\u25CB";
      (h.createEl("span", { cls: "paperforge-status-pill-icon", text: v }),
        h.createEl("span", { text: " " + g.label }));
    }
    if (e.pdf_path) {
      let g = p.createEl("button", { cls: "paperforge-contextual-btn" });
      (g.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\u{1F4C4}",
      }),
        g.createEl("span", { text: "\u6253\u5F00 PDF" }),
        g.addEventListener("click", () => {
          let h = e.pdf_path.match(/\[\[([^\]]+)\]\]/),
            f = h ? h[1] : e.pdf_path;
          this.app.vault.getAbstractFileByPath(f)
            ? this.app.workspace.openLinkText(f, "")
            : new H.Notice("[!!] PDF not found: " + f, 6e3);
        }));
    }
    if (e.fulltext_path) {
      let g = p.createEl("button", { cls: "paperforge-contextual-btn" });
      (g.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\u{1F4DD}",
      }),
        g.createEl("span", { text: "\u6253\u5F00\u5168\u6587" }),
        g.addEventListener("click", () => this._openFulltext(e.fulltext_path)));
    }
    let _ = p.createEl("button", { cls: "paperforge-contextual-btn" });
    if (
      (_.createEl("span", { text: o("version_panel_title") }),
      _.addEventListener("click", () => {
        this._switchToVersionMode(t);
      }),
      this._renderPaperOverviewCard(r, e),
      e.next_step === "ready" && e.deep_reading_status === "done")
    ) {
      let g = r.createEl("div", { cls: "paperforge-complete-row" });
      (g.createEl("span", { text: "\u2713" }),
        g.createEl("span", {
          text: "\u5DF2\u5B8C\u6210\uFF0C\u53EF\u76F4\u63A5\u4F7F\u7528",
        }));
    } else this._renderNextStepCard(r, e, t);
    (this._renderRecentDiscussionCard(r, e),
      this._renderPaperTechnicalDetails(r, e));
  }
  _renderPaperOverviewCard(e, t) {
    let r = e.createEl("div", { cls: "paperforge-paper-overview" });
    r.createEl("div", { cls: "paperforge-paper-overview-header" }).createEl(
      "span",
      {
        cls: "paperforge-paper-overview-title",
        text: "\u6587\u7AE0\u6982\u89C8",
      }
    );
    let s = r.createEl("div", { cls: "paperforge-paper-overview-body" }),
      a = s.createEl("div", {
        cls: "paperforge-paper-overview-excerpt",
        text: "\u52A0\u8F7D\u4E2D...",
      });
    if (t.note_path) {
      let i = this.app.vault.getAbstractFileByPath(t.note_path);
      i
        ? this.app.vault
            .read(i)
            .then((c) => {
              let p = this._extractOverviewFromNote(c);
              if (p) {
                let u = p.length > 200 ? p.slice(0, 200) + "..." : p;
                if ((a.setText(u), p.length > 200)) {
                  let _ = s.createEl("div", {
                      cls: "paperforge-expand-container",
                    }),
                    g = _.createEl("button", {
                      cls: "paperforge-expand-icon",
                      title: "\u5C55\u5F00/\u6536\u8D77",
                    });
                  g.innerHTML =
                    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>';
                  let h = !1;
                  _.addEventListener("click", () => {
                    (a.setText(h ? u : p),
                      (g.innerHTML = h
                        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>'
                        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>'),
                      (h = !h));
                  });
                }
              } else
                a.setText(
                  "\u5C1A\u672A\u751F\u6210\u6587\u7AE0\u6982\u89C8\u3002\u8FD0\u884C /pf-deep \u5F00\u59CB\u7CBE\u8BFB\u3002"
                );
            })
            .catch(() => {
              a.setText("\u65E0\u6CD5\u8BFB\u53D6\u7B14\u8BB0\u5185\u5BB9");
            })
        : a.setText("\u7B14\u8BB0\u6587\u4EF6\u4E0D\u5B58\u5728");
    } else a.setText("\u5C1A\u672A\u751F\u6210\u6587\u7AE0\u6982\u89C8");
  }
  _extractOverviewFromNote(e) {
    if (!e) return null;
    let t = e.indexOf("## \u{1F50D} \u7CBE\u8BFB");
    if (t === -1) return null;
    let r = e.slice(t),
      n = [
        "**\u4E00\u53E5\u8BDD\u603B\u89C8:**",
        "**\u4E00\u53E5\u8BDD\u603B\u89C8**",
        "**\u6587\u7AE0\u6458\u8981:**",
        "**\u6587\u7AE0\u6458\u8981**",
      ];
    for (let i of n) {
      let c = r.indexOf(i);
      if (c !== -1) {
        let p = r.slice(c + i.length),
          u = ["**5 Cs", "**Figure", "**\u8BC1\u636E", "### Pass 2", "## "],
          _ = p.length;
        for (let f of u) {
          let v = p.indexOf(f);
          v !== -1 && v < _ && (_ = v);
        }
        let g = p.indexOf(`

`);
        g !== -1 && g < _ && (_ = g);
        let h = p.slice(0, _).trim();
        return (
          h.startsWith("**") && (h = h.slice(2)),
          h.endsWith("**") && (h = h.slice(0, -2)),
          h || null
        );
      }
    }
    let s = r.indexOf(`
`);
    if (s === -1) return null;
    let a = r
      .slice(s + 1)
      .split(
        `

`
      )[0]
      .trim();
    return !a || a.startsWith("###") || a.startsWith("##")
      ? null
      : a.length > 300
        ? a.slice(0, 300) + "..."
        : a;
  }
  _renderRecentDiscussionCard(e, t) {
    let r = e.createEl("div", { cls: "paperforge-discussion-card" });
    if (((r.style.display = "none"), !t.note_path)) return;
    let n = t.note_path.lastIndexOf("/"),
      a = (n !== -1 ? t.note_path.substring(0, n) : ".") + "/ai/discussion.md";
    this.app.vault.adapter
      .exists(a)
      .then((i) => {
        if (i) return this.app.vault.adapter.read(a);
      })
      .then(async (i) => {
        if (!i) return;
        let c = this._parseDiscussionMD(i);
        if (!c || c.length === 0) return;
        ((r.style.display = "block"),
          r
            .createEl("div", { cls: "paperforge-discussion-header" })
            .createEl("span", {
              cls: "paperforge-discussion-title",
              text: "\u6700\u8FD1\u8BA8\u8BBA",
            }));
        for (let _ of c) {
          let g = r.createEl("div", { cls: "paperforge-discussion-item" }),
            h = g.createEl("div", { cls: "paperforge-discussion-q" });
          (h.createEl("span", {
            cls: "paperforge-discussion-q-label",
            text: "\u63D0\u95EE\uFF1A",
          }),
            h.createEl("span", {
              cls: "paperforge-discussion-q-text",
              text: _.question,
            }));
          let f = g.createEl("div", { cls: "paperforge-discussion-a" }),
            v = !1;
          if (
            (_.answer &&
              _.answer.length > 500 &&
              ((v = !0), f.classList.add("paperforge-discussion-a-collapsed")),
            await H.MarkdownRenderer.render(
              this.app,
              _.answer || "",
              f,
              a,
              this
            ),
            v)
          ) {
            let y = !1;
            ((g.style.cursor = "pointer"),
              g.addEventListener("click", () => {
                ((y = !y),
                  f.classList.toggle("paperforge-discussion-a-collapsed", !y),
                  f.classList.toggle("paperforge-discussion-a-expanded", y));
              }));
          }
        }
        r.createEl("a", {
          cls: "paperforge-discussion-viewall",
          text: "\u67E5\u770B\u5168\u90E8\u8BA8\u8BBA \u2192",
        }).addEventListener("click", (_) => {
          (_.preventDefault(),
            this.app.vault.getAbstractFileByPath(a)
              ? this.app.workspace.openLinkText(a, "")
              : new H.Notice(
                  "\u8BA8\u8BBA\u6587\u4EF6\u5C1A\u672A\u751F\u6210"
                ));
        });
      })
      .catch((i) => {
        console.error("PaperForge: discussion.md read error", a, i.message);
      });
  }
  _parseDiscussionMD(e) {
    let t = e.split(/\n## /).slice(1);
    if (t.length === 0) return null;
    let r = t[t.length - 1],
      n = [],
      s = r.split(/\*\*\u95EE\u9898:\*\*/).slice(1);
    for (let a of s) {
      let i = a.match(/\*\*\u89E3\u7B54:\*\*/);
      if (!i) continue;
      let c = a.substring(0, i.index).trim(),
        p = a.substring(i.index + 3 + 4).trim();
      n.push({ question: c, answer: p });
    }
    return n.slice(-3);
  }
  _renderPaperTechnicalDetails(e, t) {
    let r = this._currentPaperKey,
      n = e.createEl("div", { cls: "paperforge-technical-details" }),
      s = n.createEl("button", { cls: "paperforge-technical-details-toggle" }),
      a = n.createEl("div", { cls: "paperforge-technical-details-body" });
    ((a.style.display = "none"),
      this._techDetailsExpanded
        ? ((a.style.display = "block"),
          s.setText("\u6280\u672F\u8BE6\u60C5 \u25BE"))
        : s.setText("\u6280\u672F\u8BE6\u60C5 \u25B8"),
      s.addEventListener("click", () => {
        let g = a.style.display !== "none";
        ((a.style.display = g ? "none" : "block"),
          s.setText(
            g
              ? "\u6280\u672F\u8BE6\u60C5 \u25B8"
              : "\u6280\u672F\u8BE6\u60C5 \u25BE"
          ),
          (this._techDetailsExpanded = !g));
      }));
    let i = a.createEl("div", { cls: "paperforge-workflow-toggles" }),
      c = [
        { key: "do_ocr", label: "OCR", hint: "\u52A0\u5165 OCR" },
        {
          key: "analyze",
          label: "\u7CBE\u8BFB",
          hint: "\u6807\u8BB0\u7CBE\u8BFB",
        },
      ];
    for (let g of c) {
      let h = i.createEl("label", { cls: "paperforge-workflow-toggle" }),
        f = h.createEl("input", {
          type: "checkbox",
          cls: "paperforge-workflow-checkbox",
        });
      ((f.checked = t[g.key] === !0),
        h.createEl("span", {
          cls: "paperforge-workflow-toggle-label",
          text: g.label,
        }),
        h.createEl("span", {
          cls: "paperforge-workflow-toggle-hint",
          text: g.hint,
        }),
        f.addEventListener("change", async () => {
          let v = t.note_path
            ? this.app.vault.getAbstractFileByPath(t.note_path)
            : null;
          if (!v) {
            new H.Notice("[!!] Note file not found", 6e3);
            return;
          }
          let y = f.checked;
          (await this.app.fileManager.processFrontMatter(v, (m) => {
            m[g.key] = y;
          }),
            this._patchCachedEntry(r, { [g.key]: y }),
            (this._currentPaperEntry = gt(this._currentPaperEntry, {
              [g.key]: y,
            })));
        }));
    }
    let p = t.health || {},
      u = [
        ["PDF Health", p.pdf_health || "\u2014"],
        ["OCR Status", t.ocr_status || "\u2014"],
        ["Asset Health", p.asset_health || "\u2014"],
        ["Note Path", t.note_path || "\u2014"],
        ["Fulltext Path", t.fulltext_path || "\u2014"],
      ],
      _ = new Set(["Note Path", "Fulltext Path", "Key"]);
    for (let [g, h] of u) {
      let f = a.createEl("div", { cls: "paperforge-technical-row" });
      f.createEl("span", { cls: "paperforge-technical-label", text: g });
      let v = f.createEl("span", {
        cls: "paperforge-technical-value",
        text: String(h),
      });
      _.has(g) &&
        h &&
        h !== "\u2014" &&
        (v.addClass("pf-copy"),
        v.addEventListener("click", () => {
          (navigator.clipboard.writeText(h), new H.Notice(g + " copied"));
        }));
    }
  }
  _renderNextStepCard(e, t, r) {
    var c, p;
    let n = t.next_step || "ready",
      s = {
        sync: {
          label: "Sync Needed",
          text: "This paper needs to be synced from Zotero. Click to run sync.",
          cmd: "sync",
          icon: "\u21BB",
        },
        ocr: {
          label: "OCR Needed",
          text: "Fulltext is missing but PDF is present. Click to run OCR.",
          cmd: "ocr",
          icon: "\u229E",
        },
        repair: {
          label: "Repair Needed",
          text: "State divergence or path errors detected. Click to repair.",
          cmd: "repair",
          icon: "\u21BA",
        },
        "rebuild index": {
          label: "Rebuild Needed",
          text: "Index may be stale. Click to run sync to rebuild.",
          cmd: "sync",
          icon: "\u21BB",
        },
        "/pf-deep": {
          label: "Ready for Deep Reading",
          text: "Fulltext is ready. Copy /pf-deep command and run in your agent.",
          cmd: null,
          icon: "\u{1F50D}",
        },
        ready: {
          label: "All Set",
          text: "This paper is fully processed and ready for use.",
          cmd: "ready",
          icon: "\u2713",
        },
      },
      a = s[n] || s.ready,
      i = e.createEl("div", { cls: "paperforge-next-step-card" });
    if (
      (n === "ready" && i.addClass("ready"),
      i.createEl("div", {
        cls: "paperforge-next-step-label",
        text: "Recommended Next Step",
      }),
      i.createEl("div", { cls: "paperforge-next-step-text", text: a.text }),
      a.cmd && a.cmd !== "ready")
    ) {
      let u = i.createEl("button", { cls: "paperforge-next-step-trigger" });
      (u.createEl("span", { text: a.icon + "  " + a.label }),
        u.addEventListener("click", () => {
          let _ = ie.find((g) => g.cmd === a.cmd);
          _ && this._runAction(_, u);
        }));
    } else if (n === "/pf-deep") {
      let u = i.createEl("button", { cls: "paperforge-next-step-trigger" });
      (u.createEl("span", { text: "\u{1F4CB}  " + o("copy_pf_deep_cmd") }),
        u.addEventListener("click", () => {
          let v = "/pf-deep " + r;
          navigator.clipboard
            .writeText(v)
            .then(() => {
              (u.setText("\u2713  " + o("copied")),
                new H.Notice(v + " copied"));
            })
            .catch(() => {
              new H.Notice("[!!] Clipboard write failed", 6e3);
            });
        }));
      let _ =
          ((p =
            (c = this.app.plugins.plugins.paperforge) == null
              ? void 0
              : c.settings) == null
            ? void 0
            : p.agent_platform) || "opencode",
        h =
          {
            opencode: "OpenCode",
            claude: "Claude Code",
            cursor: "Cursor",
            github_copilot: "GitHub Copilot",
            windsurf: "Windsurf",
            codex: "Codex",
            gemini: "Gemini CLI",
            cline: "Cline",
          }[_] || _;
      i.createEl("div", { cls: "paperforge-agent-platform-label" }).setText(
        o("run_in_agent").replace("{0}", h)
      );
    } else
      n === "ready" &&
        i
          .createEl("button", { cls: "paperforge-next-step-trigger" })
          .createEl("span", { text: "\u2713  " + a.label });
  }
  _openFulltext(e) {
    if (!e) {
      new H.Notice("[!!] No fulltext path available for this paper", 6e3);
      return;
    }
    let t = this.app.vault.getAbstractFileByPath(e);
    t
      ? this.app.workspace.openLinkText(t.path, "")
      : new H.Notice("[!!] Fulltext file not found: " + e, 6e3);
  }
  _renderCollectionMode() {
    let e = this._currentDomain || "Unknown",
      t = this._filterByDomain(e);
    if (t.length === 0) {
      this._renderGlobalMode();
      return;
    }
    if (!this._contentEl) return;
    let r = this._contentEl.createEl("div", {
        cls: "paperforge-collection-view",
      }),
      n = t.length,
      s = 0,
      a = 0,
      i = 0,
      c = 0,
      p = 0,
      u = 0,
      _ = 0;
    for (let b of t) {
      (b.has_pdf && s++,
        b.ocr_status === "done" && a++,
        b.ocr_status === "done" && b.analyze === !0 && i++,
        b.deep_reading_status === "done" && c++);
      let x = b.ocr_status || "";
      x === "pending" || x === "queued"
        ? p++
        : x === "processing"
          ? u++
          : (x === "failed" ||
              x === "blocked" ||
              x === "done_incomplete" ||
              x === "nopdf") &&
            _++;
    }
    r.createEl("div", { cls: "paperforge-collection-header" }).createEl("div", {
      cls: "paperforge-collection-title",
      text: e,
    });
    let h = r.createEl("div", { cls: "paperforge-workflow-overview" });
    h.createEl("div", {
      cls: "paperforge-section-label",
      text: "Workflow Overview",
    });
    let f = h.createEl("div", { cls: "paperforge-workflow-funnel" }),
      v = [
        { value: n, label: "Total" },
        { value: s, label: "PDF Ready" },
        { value: a, label: "OCR Done" },
        { value: c, label: "Deep Read" },
      ];
    for (let b = 0; b < v.length; b++) {
      let x = f.createEl("div", { cls: "paperforge-workflow-stage" });
      (x.createEl("div", {
        cls: "paperforge-workflow-stage-value",
        text: String(v[b].value),
      }),
        x.createEl("div", {
          cls: "paperforge-workflow-stage-label",
          text: v[b].label,
        }),
        b < v.length - 1 &&
          f.createEl("div", {
            cls: "paperforge-workflow-arrow",
            text: "\u2192",
          }));
    }
    if (p + u + a + _ > 0) {
      let b = r.createEl("div", { cls: "paperforge-ocr-section" }),
        x = b.createEl("div", { cls: "paperforge-collection-ocr-header" });
      x.createEl("h4", { cls: "paperforge-ocr-title", text: "OCR Pipeline" });
      let w = x.createEl("span", { cls: "paperforge-ocr-badge idle" });
      u > 0
        ? (w.addClass("active"), w.setText("Processing"))
        : p > 0
          ? w.setText("Pending")
          : (w.addClass("idle"), w.setText("Idle"));
      let R = b.createEl("div", { cls: "paperforge-progress-track" });
      u > 0 && R.addClass("paperforge-processing");
      let S = p + u + a + _,
        T = [
          { cls: "pending", count: p },
          { cls: "active", count: u },
          { cls: "done", count: a },
          { cls: "failed", count: _ },
        ];
      for (let P of T)
        if (P.count > 0) {
          let L = ((P.count / S) * 100).toFixed(1);
          R.createEl("div", {
            cls: `paperforge-progress-seg ${P.cls}`,
            attr: { style: `width:${L}%` },
          });
        }
      let F = b.createEl("div", { cls: "paperforge-ocr-counts" }),
        M = [
          { cls: "pending", value: p, label: "Pending" },
          { cls: "active", value: u, label: "Processing" },
          { cls: "done", value: a, label: "Done" },
          { cls: "failed", value: _, label: "Attention" },
        ];
      for (let P of M) {
        let L = F.createEl("div", { cls: "paperforge-ocr-count" });
        (L.createEl("div", {
          cls: "paperforge-ocr-count-value",
          text: P.value.toString(),
        }),
          L.createEl("div", {
            cls: "paperforge-ocr-count-label",
            text: P.label,
          }));
      }
    }
    let y = r.createEl("div", { cls: "paperforge-collection-actions" }),
      m = y.createEl("button", { cls: "paperforge-contextual-btn primary" });
    (m.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    }),
      m.createEl("span", { text: "Run OCR" }),
      m.addEventListener("click", () => {
        let b = ie.find((x) => x.id === "paperforge-ocr");
        b && this._runAction(b, m);
      }));
    let E = y.createEl("button", { cls: "paperforge-contextual-btn" });
    (E.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    }),
      E.createEl("span", { text: "Sync Library" }),
      E.addEventListener("click", () => {
        let b = ie.find((x) => x.id === "paperforge-sync");
        b && this._runAction(b, E);
      }));
    let k = y.createEl("button", { cls: "paperforge-contextual-btn warn" });
    (k.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BA",
    }),
      k.createEl("span", { text: "Redo OCR" }),
      k.addEventListener("click", () => {
        let b = ie.find((x) => x.id === "paperforge-ocr-redo");
        b && this._runAction(b, k);
      }),
      this.renderSearchSection(r));
  }
  _refreshCurrentMode() {
    if (!(!this._currentMode || !this._contentEl)) {
      (this._contentEl.empty(),
        this._contentEl.addClass("switching"),
        this._invalidateIndex(),
        (this._currentPaperEntry = this._currentPaperKey
          ? this._findEntry(this._currentPaperKey)
          : null),
        this._renderModeHeader(this._currentMode));
      try {
        switch (this._currentMode) {
          case "global":
            this._renderGlobalMode();
            break;
          case "paper":
            this._renderPaperMode();
            break;
          case "collection":
            this._renderCollectionMode();
            break;
          case "versions":
            this._renderVersionMode();
            break;
        }
      } finally {
        setTimeout(() => {
          this._contentEl && this._contentEl.removeClass("switching");
        }, 50);
      }
    }
  }
  _switchToVersionMode(e) {
    let r = this.app.vault.adapter.basePath,
      n = typeof r == "string" ? r : "";
    if (!n) {
      new H.Notice("Cannot determine vault path");
      return;
    }
    ((this._versionPapers = Bt(n)),
      (this._versionFilter = ""),
      (this._currentMode = "versions"),
      (this._currentFilePath = null),
      (this._techDetailsExpanded = !1),
      this._contentEl &&
        (this._contentEl.empty(),
        this._contentEl.removeClass("switching"),
        this._renderModeHeader("versions"),
        this._renderVersionMode()));
  }
  _renderVersionMode() {
    if (!this._contentEl) return;
    let e = this._contentEl.createEl("div", {
        cls: "paperforge-version-panel",
      }),
      r = this.app.vault.adapter.basePath,
      n = typeof r == "string" ? r : "";
    if (!n) {
      e.createEl("div", {
        cls: "paperforge-status-error",
        text: "Could not determine vault path",
      });
      return;
    }
    (!this._versionPapers || this._versionPapers.length === 0) &&
      (this._versionPapers = Bt(n));
    let s = e.createEl("div", { cls: "paperforge-version-left" }),
      a = e.createEl("div", { cls: "paperforge-version-right" }),
      i = s.createEl("input", {
        cls: "paperforge-version-filter",
        attr: { type: "text", placeholder: o("version_filter_placeholder") },
      });
    i.value = this._versionFilter;
    let c = s.createEl("div", { cls: "paperforge-version-paper-list" }),
      p = () => {
        c.empty();
        let m = this._versionFilter.toLowerCase(),
          E = this._versionPapers
            ? this._versionPapers.filter(
                (b) =>
                  !m ||
                  b.key.toLowerCase().includes(m) ||
                  b.title.toLowerCase().includes(m)
              )
            : [];
        if (E.length === 0) {
          c.createEl("div", {
            cls: "paperforge-meta",
            text: o("version_no_backups"),
          });
          return;
        }
        let k = c.createEl("div", {
          cls: "paperforge-meta",
          text: o("version_papers_count").replace("{n}", String(E.length)),
        });
        for (let b of E) {
          let x = c.createEl("div", { cls: "paperforge-version-paper-item" }),
            w = x.createEl("span", {
              cls: "paperforge-version-paper-title",
              text: b.title,
            }),
            R = x.createEl("span", {
              cls: "paperforge-version-paper-versions",
              text: b.versions.map((S) => S.label).join(" "),
            });
          x.addEventListener("click", () => {
            (c
              .querySelectorAll(".paperforge-version-paper-item.selected")
              .forEach((S) => S.removeClass("selected")),
              x.addClass("selected"),
              _(b));
          });
        }
      };
    i.addEventListener("input", () => {
      ((this._versionFilter = i.value), p());
    });
    let u = a.createEl("div", { cls: "paperforge-version-timeline-area" }),
      _ = (m) => {
        if (
          (u.empty(),
          u
            .createEl("div", { cls: "paperforge-version-timeline-header" })
            .createEl("span", { cls: "pf-title", text: m.title }),
          m.versions.length === 0)
        ) {
          u.createEl("div", {
            cls: "paperforge-meta",
            text: o("version_no_backups"),
          });
          return;
        }
        let k = u.createEl("div", { cls: "paperforge-version-timeline" });
        for (let b of m.versions) {
          let x = b.label === m.currentLabel,
            w = k.createEl("div", {
              cls:
                "paperforge-version-entry" +
                (x ? " paperforge-version-current" : ""),
            }),
            R = w.createEl("div", { cls: "paperforge-version-dot" }),
            S = w.createEl("div", { cls: "paperforge-version-content" }),
            T = S.createEl("div", { cls: "paperforge-version-label-row" });
          (T.createEl("span", {
            cls: "paperforge-version-label",
            text: b.label,
          }),
            x &&
              T.createEl("span", {
                cls: "paperforge-version-current-tag",
                text: o("version_current"),
              }));
          let F = b.created_at ? b.created_at.slice(0, 10) : "";
          S.createEl("div", {
            cls: "paperforge-meta",
            text: F + " \u2014 " + b.source,
          });
          let M = b.fulltext_size
            ? b.fulltext_size > 1024
              ? (b.fulltext_size / 1024).toFixed(0) + "KB"
              : b.fulltext_size + "B"
            : "";
          M && S.createEl("div", { cls: "paperforge-meta", text: M });
          let P = S.createEl("div", { cls: "paperforge-version-actions" });
          (P.createEl("button", {
            cls: "pf-btn-primary",
            text: o("version_restore_btn"),
          }).addEventListener("click", () => {
            kr(n, m.key, b.label)
              ? new H.Notice(
                  o("version_restore_done").replace("{label}", b.label)
                )
              : new H.Notice("Restore failed", 6e3);
          }),
            m.versions.length > 1 &&
              !x &&
              P.createEl("button", {
                cls: "pf-btn-secondary",
                text: o("version_compare_btn"),
              }).addEventListener("click", () => {
                h(m, b.label, m.currentLabel);
              }));
        }
      },
      g = a.createEl("div", { cls: "paperforge-version-compare" });
    g.style.display = "none";
    let h = (m, E, k) => {
        let b = wr(n, m.key, E, k);
        ((g.style.display = "block"), g.empty());
        let x = g.createEl("div", { cls: "paperforge-version-compare-header" });
        if (
          (x.createEl("span", {
            cls: "pf-title",
            text: o("version_compare_title")
              .replace("{vA}", E)
              .replace("{vB}", k),
          }),
          x.createEl("span", {
            cls: "paperforge-meta",
            text: o("version_compare_paragraphs").replace(
              "{n}",
              String(b.length)
            ),
          }),
          b.length === 0)
        ) {
          g.createEl("div", { cls: "paperforge-meta", text: "No changes" });
          return;
        }
        let w = g.createEl("div", { cls: "paperforge-version-diff-list" });
        for (let R of b) {
          let S = w.createEl("div", { cls: "paperforge-version-diff-row" }),
            T =
              R.type === "added" ? "[+]" : R.type === "removed" ? "[-]" : "[~]",
            F = R.heading || "paragraph " + (R.paragraphIndex + 1);
          (S.createEl("span", {
            cls: "paperforge-version-diff-label",
            text: T + " " + F,
          }),
            R.oldText &&
              S.createEl("pre", {
                cls: "paperforge-version-diff-old",
                text: R.oldText.slice(0, 200),
              }),
            R.newText &&
              S.createEl("pre", {
                cls: "paperforge-version-diff-new",
                text: R.newText.slice(0, 200),
              }));
        }
      },
      f = e.createEl("div", { cls: "paperforge-version-actions-bar" }),
      v = f.createEl("button", {
        cls: "pf-btn-primary",
        text: o("version_restore_selected"),
      }),
      y = f.createEl("button", {
        cls: "pf-btn-secondary",
        text: o("version_clear_old").replace("{size}", ""),
      });
    p();
  }
  renderSearchSection(e) {
    ((this._searchContainer = e.createEl("div", {
      cls: "paperforge-search-section",
    })),
      this._searchContainer
        .createEl("div", { cls: "paperforge-search-header" })
        .createEl("span", { cls: "pf-label", text: "Search" }));
    let r = this._searchContainer.createEl("div", {
        cls: "paperforge-search-input-row",
      }),
      n = r.createEl("span", { cls: "paperforge-search-mode", text: "M" });
    ((this._searchInput = r.createEl("input", {
      cls: "paperforge-search-input",
      attr: {
        type: "text",
        placeholder: "Search papers... (@ for deep search)",
      },
    })),
      (this._searchResultsEl = this._searchContainer.createEl("div", {
        cls: "paperforge-search-results",
      })),
      (this._searchInput.placeholder = o("retrieval_search_placeholder")),
      this._searchInput.addEventListener("input", () => {
        var a;
        let s = ((a = this._searchInput) == null ? void 0 : a.value) || "";
        if (
          (s.startsWith("@") && !s.startsWith("@ ")
            ? ((this._searchMode = "@"),
              n.setText("@"),
              n.addClass("deep"),
              this._searchInput &&
                (this._searchInput.placeholder = o(
                  "retrieval_search_placeholder_deep"
                )))
            : ((this._searchMode = "M"),
              n.setText("M"),
              n.removeClass("deep"),
              this._searchInput &&
                (this._searchInput.placeholder = o(
                  "retrieval_search_placeholder"
                ))),
          clearTimeout(this._searchTimer),
          !s.trim())
        ) {
          ((this._searchState = "idle"),
            (this._searchResults = null),
            (this._searchActiveIndex = -1),
            this._renderSearchState());
          return;
        }
        s.startsWith("@") ||
          (this._searchTimer = setTimeout(() => {
            this.executeSearch();
          }, 200));
      }),
      this._searchInput.addEventListener("keydown", (s) => {
        var a, i;
        if (s.key === "Escape") {
          (s.preventDefault(),
            this._searchInput &&
              ((this._searchInput.value = ""), this._searchInput.blur()),
            (this._searchState = "idle"),
            (this._searchResults = null),
            (this._searchActiveIndex = -1),
            this._renderSearchState());
          return;
        }
        if (s.key === "ArrowDown" || s.key === "ArrowUp") {
          if (
            this._searchState !== "results" ||
            !((a = this._searchResults) != null && a.length)
          )
            return;
          s.preventDefault();
          let c = this._searchResults.length;
          s.key === "ArrowDown"
            ? (this._searchActiveIndex = Math.min(
                this._searchActiveIndex + 1,
                c - 1
              ))
            : (this._searchActiveIndex = Math.max(
                this._searchActiveIndex - 1,
                -1
              ));
          let p =
            (i = this._searchResultsEl) == null
              ? void 0
              : i.querySelectorAll(".paperforge-search-result-card");
          p &&
            p.forEach((u, _) => {
              _ === this._searchActiveIndex
                ? (u.setAttribute("aria-selected", "true"),
                  u.classList.add("active"))
                : (u.setAttribute("aria-selected", "false"),
                  u.classList.remove("active"));
            });
          return;
        }
        if (s.key === "Enter" && s.ctrlKey) {
          (s.preventDefault(),
            this._searchTimer &&
              (clearTimeout(this._searchTimer), (this._searchTimer = void 0)));
          let c = this._searchMode;
          ((this._searchMode = "@"),
            this.executeSearch(),
            (this._searchMode = c));
          return;
        }
        s.key === "Enter" &&
          (s.preventDefault(),
          this._searchTimer &&
            (clearTimeout(this._searchTimer), (this._searchTimer = void 0)),
          this.executeSearch());
      }));
  }
  _renderSearchState() {
    if (!this._searchResultsEl) return;
    switch (
      (this._searchResultsEl.empty(),
      this._searchResultsEl.removeAttribute("role"),
      this._searchResultsEl.removeAttribute("aria-live"),
      this._searchInput && (this._searchInput.disabled = !1),
      this._searchState)
    ) {
      case "idle":
        break;
      case "searching": {
        let t = this._searchMode === "@";
        (this._searchResultsEl.createEl("div", {
          cls: "paperforge-search-loading",
          text: t
            ? o("retrieval_searching_deep")
            : o("retrieval_searching_metadata"),
        }),
          this._searchResultsEl.setAttr("aria-live", "polite"),
          t && this._searchInput && (this._searchInput.disabled = !0));
        break;
      }
      case "results": {
        (this._searchResultsEl.setAttr("role", "listbox"),
          this._searchResultsEl.setAttr("aria-live", "polite"),
          this._searchResults &&
            this._renderSearchResultsList(
              this._searchResults,
              this._searchMode === "@"
            ),
          setTimeout(() => {
            var r;
            let t =
              (r = this._searchResultsEl) == null
                ? void 0
                : r.querySelector(".paperforge-search-result-card");
            t && t instanceof HTMLElement && t.focus();
          }, 100));
        break;
      }
      case "empty": {
        let t = this._searchResultsEl.createEl("div", {
          cls: "paperforge-search-empty",
        });
        (t.setAttr("role", "alert"),
          t.createEl("div", { text: o("retrieval_empty") }),
          t.createEl("div", {
            cls: "paperforge-search-empty-tips",
            text: o("retrieval_empty_tips"),
          }));
        break;
      }
      case "vectors-not-built": {
        let t = this._searchResultsEl.createEl("div", {
          cls: "paperforge-search-state-card",
          attr: { role: "alert" },
        });
        (t.addClass("warning-soft"),
          t.createEl("div", {
            cls: "paperforge-search-state-title",
            text: o("retrieval_vectors_not_built"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: o("retrieval_vectors_not_built_desc"),
          }));
        let r = t.createEl("button", {
          cls: "pf-btn-link",
          text: o("retrieval_open_vector_settings"),
        });
        (r.addEventListener("click", () => {
          let n = this.app.setting;
          if (n && typeof n == "object") {
            let s = n.openTab;
            typeof s == "function" && s.call(n, "paperforge");
          }
        }),
          setTimeout(() => {
            r.focus();
          }, 100));
        break;
      }
      case "backend-unavailable": {
        let t = this._searchResultsEl.createEl("div", {
          cls: "paperforge-search-state-card",
          attr: { role: "alert" },
        });
        (t.addClass("error-soft"),
          t.createEl("div", {
            cls: "paperforge-search-state-title",
            text: o("retrieval_backend_unavailable"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: o("retrieval_backend_unavailable_desc"),
          }));
        let r = t.createEl("div", { cls: "paperforge-search-state-actions" }),
          n = r.createEl("button", {
            cls: "pf-btn-primary",
            text: o("retrieval_run_doctor"),
          });
        (n.addEventListener("click", () => {
          let a = this.app.vault.adapter.basePath;
          if (typeof a != "string") return;
          let i = this._resolvePython();
          if (!i) return;
          let { path: c, args: p = [] } = i;
          (0, ye.spawn)(c, [...p, "-m", "paperforge", "doctor"], {
            cwd: a,
            stdio: "inherit",
          });
        }),
          r
            .createEl("button", {
              cls: "pf-btn-secondary",
              text: o("retrieval_retry"),
            })
            .addEventListener("click", () => {
              this.executeSearch();
            }),
          setTimeout(() => {
            n.focus();
          }, 100));
        break;
      }
      case "timeout": {
        let t = this._searchResultsEl.createEl("div", {
          cls: "paperforge-search-state-card",
          attr: { role: "alert" },
        });
        (t.addClass("warning-soft"),
          t.createEl("div", {
            cls: "paperforge-search-state-title",
            text: o("retrieval_timeout_title"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: o("retrieval_timeout_desc"),
          }));
        let r = t.createEl("button", {
          cls: "pf-btn-primary",
          text: o("retrieval_retry"),
        });
        (r.addEventListener("click", () => {
          this.executeSearch();
        }),
          setTimeout(() => {
            r.focus();
          }, 100));
        break;
      }
      case "model-changed": {
        let t = this._searchResultsEl.createEl("div", {
          cls: "paperforge-search-state-card",
          attr: { role: "alert" },
        });
        (t.addClass("warning-soft"),
          t.createEl("div", {
            cls: "paperforge-search-state-title",
            text: o("retrieval_model_changed"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: o("retrieval_model_changed_desc"),
          }));
        let r = t.createEl("button", {
          cls: "pf-btn-primary",
          text: o("retrieval_rebuild_vectors"),
        });
        (r.addEventListener("click", () => {
          let n = this.app.setting;
          if (n && typeof n == "object") {
            let s = n.openTab;
            typeof s == "function" && s.call(n, "paperforge");
          }
        }),
          setTimeout(() => {
            r.focus();
          }, 100));
        break;
      }
      default: {
        (this._searchResultsEl
          .createEl("div", {
            cls: "paperforge-search-state-card",
            text: o("retrieval_internal_error"),
            attr: { role: "alert" },
          })
          .addClass("error-soft"),
          setTimeout(() => {
            this._searchInput && this._searchInput.focus();
          }, 100));
        break;
      }
    }
  }
  async executeSearch() {
    if (!this._searchInput || !this._searchResultsEl) return;
    let e = this._searchInput.value.trim();
    if (!e) return;
    let t = this._searchMode === "@" || e.startsWith("@"),
      r = t ? e.replace(/^@\s*/, "").trim() : e;
    if (!r) return;
    let n = t ? "retrieve" : "search";
    ((this._searchState = "searching"),
      (this._searchResults = null),
      (this._searchActiveIndex = -1),
      this._renderSearchState());
    let s = this.app.vault.adapter,
      a = "";
    if (s && typeof s == "object" && "basePath" in s) {
      let m = s.basePath;
      a = typeof m == "string" ? m : "";
    }
    if (!a) {
      ((this._searchState = "backend-unavailable"), this._renderSearchState());
      return;
    }
    let i = null,
      p = this.app.plugins;
    if (p && typeof p == "object" && "plugins" in p) {
      let m = p.plugins;
      if (m && typeof m == "object" && "paperforge" in m) {
        let E = m.paperforge;
        E && typeof E == "object" && "settings" in E && (i = E.settings);
      }
    }
    let u = this._resolvePython();
    if (!u) {
      ((this._searchState = "backend-unavailable"), this._renderSearchState());
      return;
    }
    let { path: _, args: g = [] } = u,
      h = n === "retrieve" ? ["--deep"] : [],
      f = await ge({ app: this.app }, "memory"),
      v = (0, ye.spawn)(
        _,
        [...g, "-m", "paperforge", "--vault", a, n, r, ...h, "--json"],
        { cwd: a, timeout: 3e4, env: f }
      ),
      y = [];
    (v.stdout.on("data", (m) => {
      y.push(m.toString("utf-8"));
    }),
      v.stderr.on("data", () => {}),
      v.on("close", (m) => {
        if (m !== 0) {
          let w = wt(String(m));
          ((this._searchState = this._mapErrorToSearchState(w.type)),
            this._renderSearchState());
          return;
        }
        let E = y.join(""),
          k = E.indexOf("{"),
          b = E.lastIndexOf("}"),
          x = "";
        if (k !== -1 && b > k) x = E.slice(k, b + 1);
        else {
          let w = E.indexOf("["),
            R = E.lastIndexOf("]");
          w !== -1 && R > w && (x = E.slice(w, R + 1));
        }
        if (!x) {
          ((this._searchState = "internal-error"), this._renderSearchState());
          return;
        }
        try {
          let w = JSON.parse(x),
            R = [];
          if (w && typeof w == "object" && "data" in w) {
            let S = w.data;
            if (S && typeof S == "object") {
              let T = S;
              "matches" in T && Array.isArray(T.matches) && (R = T.matches);
            }
          }
          ((this._searchResults = R),
            (this._searchState = R.length > 0 ? "results" : "empty"),
            this._renderSearchState());
        } catch (w) {
          let R = w instanceof Error ? w.message : String(w);
          ((this._searchState = "internal-error"), this._renderSearchState());
        }
      }),
      v.on("error", (m) => {
        let E = m.code;
        if (typeof E == "string") {
          let k = wt(E);
          this._searchState = this._mapErrorToSearchState(k.type);
        } else this._searchState = "backend-unavailable";
        this._renderSearchState();
      }));
  }
  _mapErrorToSearchState(e) {
    switch (e) {
      case "vectors_not_built":
        return "vectors-not-built";
      case "vectors_corrupted":
        return "vectors-not-built";
      case "backend_unavailable":
        return "backend-unavailable";
      case "model_changed":
        return "model-changed";
      case "timeout":
        return "timeout";
      case "no_python":
      case "python_missing":
      case "import_failed":
      case "version_mismatch":
        return "backend-unavailable";
      default:
        return "backend-unavailable";
    }
  }
  _renderSearchResultsList(e, t) {
    if (!this._searchResultsEl) return;
    if (
      (this._searchResultsEl.setAttr("aria-live", "polite"), e.length === 0)
    ) {
      this._searchResultsEl.createEl("div", {
        cls: "paperforge-search-empty",
        text: "No results found.",
      });
      return;
    }
    let r = this._searchResultsEl.createEl("div", {
      cls: "paperforge-search-results-header",
    });
    (r
      .createEl("span", {
        text: o("retrieval_results_count")
          .replace("{n}", String(e.length))
          .replace("{s}", e.length !== 1 ? "s" : ""),
      })
      .setAttr("aria-live", "polite"),
      r.createEl("span", {
        cls: "paperforge-search-mode",
        text: t ? "@" : "M",
      }));
    for (let s = 0; s < e.length; s++) {
      let a = e[s];
      if (!a || typeof a != "object") continue;
      let i = a,
        c = s === this._searchActiveIndex,
        p = this._searchResultsEl.createEl("div", {
          cls: "paperforge-search-result-card",
          attr: {
            role: "option",
            tabindex: "0",
            "aria-selected": c ? "true" : "false",
            "aria-posinset": String(s + 1),
            "aria-setsize": String(e.length),
          },
        });
      c && p.addClass("active");
      let u =
        typeof i.title == "string"
          ? i.title
          : typeof i.file_name == "string"
            ? i.file_name
            : "(untitled)";
      p.createEl("div", { cls: "paperforge-search-result-title", text: u });
      let _ = typeof i.zotero_key == "string" ? i.zotero_key : "",
        g =
          typeof i.main_note_path == "string" && i.main_note_path
            ? i.main_note_path
            : null,
        h = typeof i.note_path == "string" && i.note_path ? i.note_path : null,
        f = g || h;
      if (!f && _) {
        let m = this._getCachedIndex().find(
          (E) =>
            E !== null &&
            typeof E == "object" &&
            "zotero_key" in E &&
            E.zotero_key === _
        );
        if (m && typeof m == "object") {
          let E = m;
          f =
            typeof E.main_note_path == "string" && E.main_note_path
              ? E.main_note_path
              : typeof E.note_path == "string" && E.note_path
                ? E.note_path
                : null;
        }
      }
      (f
        ? p.addEventListener("click", (y) => {
            let m = y.ctrlKey || y.metaKey;
            this.app.workspace.openLinkText(f, "", m);
          })
        : p.addEventListener("click", () => {
            new H.Notice("[!!] Note not found: " + (_ || "unknown"), 6e3);
          }),
        p.addEventListener("keydown", (y) => {
          if (y.key === "Enter" && f) {
            y.preventDefault();
            let m = y.ctrlKey || y.metaKey;
            this.app.workspace.openLinkText(f, "", m);
          }
        }));
      let v = p.createEl("div", { cls: "paperforge-search-result-meta" });
      if (
        (typeof i.first_author == "string" &&
          i.first_author &&
          v.createEl("span", {
            cls: "paperforge-search-result-author",
            text: i.first_author,
          }),
        typeof i.journal == "string" &&
          i.journal &&
          v.createEl("span", {
            cls: "paperforge-search-result-journal",
            text: i.journal,
          }),
        i.score !== void 0)
      ) {
        let y = i.score,
          m = typeof y == "number" ? y.toFixed(3) : String(y);
        v.createEl("span", {
          cls: "paperforge-search-result-score",
          text: "Score: " + m,
        });
      }
      if (
        (typeof i.domain == "string" &&
          i.domain &&
          p.createEl("span", {
            cls: "paperforge-search-result-tag",
            text: i.domain,
          }),
        typeof i.abstract == "string" && i.abstract)
      ) {
        let y = i.abstract;
        p.createEl("div", {
          cls: "paperforge-search-result-abstract",
          text: y.length > 200 ? y.slice(0, 200) + "..." : y,
        });
      }
      if (t && typeof i.text == "string" && i.text) {
        let y = i.text;
        p.createEl("div", {
          cls: "paperforge-search-result-source",
          text: y.length > 300 ? y.slice(0, 300) + "..." : y,
        });
      }
    }
  }
  _renderSearchError(e) {
    this._searchResultsEl &&
      (this._searchResultsEl.empty(),
      this._searchResultsEl.createEl("div", {
        cls: "paperforge-search-error",
        text: e,
      }));
  }
  async _runAction(e, t) {
    if (e.disabled) {
      new H.Notice(
        `[i] ${e.disabledMsg || "This action is not yet available."}`,
        6e3
      );
      return;
    }
    if (t.classList.contains("running")) return;
    t.addClass("running");
    let r = this.app.vault.adapter.basePath;
    this._showMessage("Processing...", "running");
    let n = Array.isArray(e.args) ? [...e.args] : [];
    if (e.needsKey) {
      let f = this.app.workspace.getActiveFile(),
        v = null;
      if (f) {
        let y = this.app.metadataCache.getFileCache(f);
        if (
          (y && y.frontmatter && y.frontmatter.zotero_key
            ? (v = y.frontmatter.zotero_key)
            : (v = this._extractZoteroKeyFromPath(f.path)),
          v)
        )
          n = [...n, v];
        else if (y && y.frontmatter) {
          (this._showMessage(
            "[!!] No zotero_key in active note frontmatter",
            "error"
          ),
            new H.Notice(
              "[!!] Open a paper note with a zotero_key in its frontmatter first",
              6e3
            ),
            t.removeClass("running"));
          return;
        } else {
          (this._showMessage("[!!] No frontmatter in active note", "error"),
            new H.Notice(
              "[!!] The active note has no frontmatter with a zotero_key",
              6e3
            ),
            t.removeClass("running"));
          return;
        }
      } else {
        (this._showMessage("[!!] No active note open", "error"),
          new H.Notice(
            "[!!] Open a paper note with a zotero_key in its frontmatter first",
            6e3
          ),
          t.removeClass("running"));
        return;
      }
    }
    e.needsFilter && (n = [...n, "--all"]);
    let s = e.needsFilter ? 6e4 : e.needsKey ? 3e4 : 6e5,
      a = this._resolvePython();
    if (!a) {
      (this._showMessage("[!!] Runtime not available", "error"),
        new H.Notice(
          "[!!] PaperForge runtime is not ready. Check settings.",
          6e3
        ),
        t.removeClass("running"));
      return;
    }
    let { path: i, args: c = [] } = a,
      p = await ge({ app: this.app }, e.cmd),
      u = (0, ye.spawn)(i, [...c, "-m", "paperforge", e.cmd, ...n], {
        cwd: r,
        timeout: s,
        env: p,
      }),
      _ = [],
      g = Date.now(),
      h = setInterval(() => this._fetchStats(!0), 4e3);
    (u.stdout.on("data", (f) => {
      let v = f
        .toString("utf-8")
        .split(
          `
`
        )
        .filter(Boolean);
      for (let y of v) {
        let m = y.trim();
        m &&
          (_.push(m),
          this._showMessage(
            _.slice(-8).join(`
`),
            "running"
          ));
      }
    }),
      u.stderr.on("data", (f) => {
        let v = f
          .toString("utf-8")
          .split(
            `
`
          )
          .filter(Boolean);
        for (let y of v) {
          if (y.includes("\r") || y.includes("%") || y.includes("\u2588"))
            continue;
          let m = y.trim();
          m &&
            !m.match(/^\d+%|^\|/) &&
            (_.push(m),
            this._showMessage(
              _.slice(-8).join(`
`),
              "running"
            ));
        }
      }),
      u.on("close", (f) => {
        (clearInterval(h), t.removeClass("running"));
        let v = ((Date.now() - g) / 1e3).toFixed(1);
        if (f !== 0) {
          let y = _.slice(-3).join(" | ") || "exit code " + f;
          (e.cmd === "repair" || e.cmd === "ocr") && f === 1
            ? (this._showMessage("[WARN] " + y, "running"),
              new H.Notice("[WARN] " + e.cmd + " partial: " + y, 8e3),
              this._fetchStats(!0))
            : (this._showMessage("[!!] " + y, "error"),
              new H.Notice("[!!] " + e.cmd + " failed: " + y, 8e3));
        } else if (e.needsKey || e.needsFilter) {
          let y = _.join(`
`);
          if (y.trim())
            try {
              (JSON.parse(y),
                navigator.clipboard
                  .writeText(y)
                  .then(() => {
                    let m = `${v}s \u2014 ${y.length} chars copied`;
                    (this._showMessage("[OK] " + e.title + ": " + m, "ok"),
                      new H.Notice(
                        "[OK] " + e.okMsg + " \u2014 " + y.length + " chars"
                      ));
                  })
                  .catch((m) => {
                    (this._showMessage(
                      "[!!] Clipboard write failed: " + m.message,
                      "error"
                    ),
                      new H.Notice("[!!] Clipboard error", 6e3));
                  }));
            } catch (m) {
              (this._showMessage("[!!] Invalid JSON from " + e.title, "error"),
                new H.Notice(
                  "[!!] " +
                    e.title +
                    " returned invalid JSON: " +
                    m.message.slice(0, 100),
                  8e3
                ));
            }
          else
            (this._showMessage("[!!] No output from context command", "error"),
              new H.Notice("[!!] Context command returned empty output", 8e3));
          this._fetchStats(!0);
        } else {
          let m =
              _.filter((k) => k.match(/updated \d+/)).pop() ||
              _[_.length - 1] ||
              "",
            E = `${v}s \u2014 ${m}`;
          (this._showMessage("[OK] " + e.title + ": " + E, "ok"),
            new H.Notice("[OK] " + e.okMsg),
            this._contentEl && this._contentEl.removeClass("switching"),
            (this._cachedStats = null));
          try {
            this._fetchStats(!1);
          } catch (k) {
            console.log("[PF] fetchStats error:", k);
          }
          (console.log("[PF] close cmd=" + e.cmd + " id=" + e.id),
            e.cmd === "sync" &&
              ct(this.app, this.app.plugins.plugins.paperforge, r));
        }
      }),
      u.on("error", (f) => {
        (t.removeClass("running"),
          this._contentEl && this._contentEl.removeClass("switching"),
          this._showMessage("[!!] " + f.message, "error"),
          new H.Notice("[!!] Cannot start: " + f.message, 8e3));
      }));
  }
  _showMessage(e, t) {
    this._messageEl &&
      (this._messageEl.setText(e),
      (this._messageEl.className = `paperforge-message msg-${t}`));
  }
  _renderModeHeader(e) {
    if (!this._modeContextEl) return;
    this._modeContextEl.empty();
    let t = this._modeContextEl.createEl("span", {
        cls: "paperforge-mode-badge",
      }),
      r = "";
    switch (e) {
      case "global":
        (t.addClass("global"),
          t.setText("Global"),
          this._headerTitle && this._headerTitle.setText("PaperForge"));
        break;
      case "paper":
        (t.addClass("paper"),
          t.setText("Paper"),
          this._headerTitle && this._headerTitle.setText("Paper"),
          this._currentPaperEntry && this._currentPaperEntry.title
            ? (r = this._currentPaperEntry.title)
            : this._currentPaperKey
              ? ((r = this._currentPaperKey),
                this._modeContextEl.createEl("span", {
                  cls: "paperforge-mode-warning",
                  text: "Not found in index",
                }))
              : (r = "Unknown paper"));
        break;
      case "collection":
        (t.addClass("collection"),
          t.setText("Collection"),
          this._headerTitle && this._headerTitle.setText("Collection"),
          (r = this._currentDomain || "Unknown Domain"));
        break;
      case "versions":
        (t.addClass("versions"),
          t.setText(o("version_panel_title")),
          this._headerTitle &&
            this._headerTitle.setText(o("version_panel_title")));
        break;
    }
    r &&
      this._modeContextEl.createEl("span", {
        cls: "paperforge-mode-name",
        text: r,
      });
  }
  _setupEventSubscriptions() {
    let e = this.app.workspace.on("active-leaf-change", () => {
      (this._leafChangeTimer && clearTimeout(this._leafChangeTimer),
        (this._leafChangeTimer = setTimeout(() => {
          let r = this._resolveModeForFile(this.app.workspace.getActiveFile()),
            n = r.mode,
            s = r.filePath;
          (this._currentMode === n && this._currentFilePath === s) ||
            this._detectAndSwitch();
        }, 300)));
    });
    this._modeSubscribers.push({ event: "active-leaf-change", ref: e });
    let t = this.app.vault.on("modify", (r) => {
      r &&
        r.path &&
        r.path.endsWith("formal-library.json") &&
        (this._invalidateIndex(), this._refreshCurrentMode());
    });
    this._modeSubscribers.push({ event: "modify", ref: t });
  }
  static async open(e) {
    let t = e.app.workspace.getLeavesOfType(Se);
    if (t.length > 0) {
      e.app.workspace.revealLeaf(t[0]);
      return;
    }
    let r = e.app.workspace.getRightLeaf(!1);
    r &&
      (await r.setViewState({ type: Se, active: !0 }),
      e.app.workspace.revealLeaf(r));
  }
};
var ft = class extends J.Plugin {
  constructor() {
    super(...arguments);
    this._lastExportMtime = 0;
    this._lastOcrMtimes = {};
    this._autoSyncRunning = !1;
    this._lastSyncTime = null;
    this._pollTimer = null;
    this._embedProcess = null;
    this._embedProgress = { current: 0, total: 0, key: "" };
    this._embedStderr = "";
    this._memoryStatusText = null;
    this._managedRuntime = null;
  }
  getManagedRuntime() {
    return (
      this._managedRuntime ||
        (this._managedRuntime = new Ee({ version: this.manifest.version })),
      this._managedRuntime
    );
  }
  _getPythonCommand() {
    let e = xe(this.getManagedRuntime().current());
    return e ? { path: e.command, args: [...e.args] } : null;
  }
  async onload() {
    (await this.loadSettings(),
      await Qt(
        {
          app: { secretStorage: this.app.secretStorage },
          saveData: async () => this.saveSettings(),
        },
        this.settings
      ),
      await this.saveSettings());
    try {
      await this.getManagedRuntime().status();
    } catch (t) {}
    (Ut(this.app), this.registerView(Se, (t) => new Be(t)));
    try {
      (0, J.addIcon)(He, jt);
    } catch (t) {}
    (this.addRibbonIcon(He, "PaperForge Dashboard", () => Be.open(this)),
      ie.find((t) => t.id === "paperforge-ocr-redo") &&
        this.addRibbonIcon("reset", "PaperForge: Redo OCR", async () => {
          let t = this.app.vault.adapter.basePath;
          new J.Notice("PaperForge: Redo OCR starting...");
          let r = this._getPythonCommand();
          if (!r) {
            new J.Notice("Runtime not ready");
            return;
          }
          let { path: n, args: s } = r,
            a = await ge(this, "ocr");
          (0, Ne.execFile)(
            n,
            [...s, "-m", "paperforge", "ocr", "redo"],
            { cwd: t, timeout: 6e5, env: a },
            (i, c, p) => {
              if (i) {
                new J.Notice("PaperForge: Redo OCR failed");
                return;
              }
              new J.Notice("PaperForge: Redo OCR done");
            }
          );
        }),
      this.addSettingTab(new ut(this.app, this)),
      this.addCommand({
        id: "paperforge-status-panel",
        name: `PaperForge: ${o("guide_open")}`,
        callback: () => Be.open(this),
      }));
    for (let t of ie)
      this.addCommand({
        id: t.id,
        name: `PaperForge: ${t.title}`,
        callback: async () => {
          if (t.disabled) {
            new J.Notice(
              `[i] ${t.disabledMsg || "This action is not yet available."}`,
              6e3
            );
            return;
          }
          let r = this.app.vault.adapter.basePath;
          new J.Notice(`PaperForge: running ${t.cmd}...`);
          let n = this._getPythonCommand();
          if (!n) {
            new J.Notice("Runtime not ready");
            return;
          }
          let { path: s, args: a = [] } = n,
            i = Array.isArray(t.args) ? [...t.args] : [],
            c = await ge(this, t.cmd);
          (0, Ne.execFile)(
            s,
            [...a, "-m", "paperforge", t.cmd, ...i],
            { cwd: r, timeout: 3e5, env: c },
            (p, u, _) => {
              if (p) {
                new J.Notice(
                  `[!!] ${t.cmd} failed: ${(_ || p.message).slice(0, 120)}`,
                  8e3
                );
                return;
              }
              new J.Notice(
                `[OK] ${
                  t.okMsg ||
                  u
                    .trim()
                    .split(
                      `
`
                    )[0]
                    .slice(0, 80)
                }`
              );
            }
          );
        },
      });
    (this._startFilePolling(), this._checkReleaseNotes());
  }
  _startFilePolling() {
    let e = this.app.vault.adapter.basePath;
    this._pollTimer = setInterval(() => {
      (this._checkExports(e), this._checkOcr(e));
    }, 12e4);
  }
  _checkExports(e) {
    if (this._autoSyncRunning) return;
    let t = ue(e).exportsDir;
    if (!Z.existsSync(t)) return;
    let r = 0;
    try {
      Z.readdirSync(t).forEach((n) => {
        if (!n.endsWith(".json")) return;
        let s = Z.statSync(Ie.join(t, n));
        s.mtimeMs > r && (r = s.mtimeMs);
      });
    } catch (n) {
      return;
    }
    r > this._lastExportMtime &&
      ((this._lastExportMtime = r), this._autoSync(e));
  }
  _autoSync(e) {
    if (this._autoSyncRunning) return;
    this._autoSyncRunning = !0;
    let t = this._getPythonCommand();
    if (!t) {
      this._autoSyncRunning = !1;
      return;
    }
    let r = `"${t.path}" ${t.args.join(" ")} -m paperforge --vault "${e}" sync`;
    (0, Ne.exec)(r, { timeout: 12e4, encoding: "utf-8" }, (n, s, a) => {
      ((this._autoSyncRunning = !1),
        (this._memoryStatusText = null),
        n || (this._lastSyncTime = new Date().toLocaleTimeString()));
      try {
        let i = ue(e).exportsDir,
          c = 0;
        (Z.readdirSync(i).forEach((p) => {
          p.endsWith(".json") &&
            (c = Math.max(c, Z.statSync(Ie.join(i, p)).mtimeMs));
        }),
          (this._lastExportMtime = c));
      } catch (i) {}
    });
  }
  _checkOcr(e) {
    if (this._autoSyncRunning) return;
    let t = ue(e).ocrDir;
    if (Z.existsSync(t))
      try {
        Z.readdirSync(t, { withFileTypes: !0 }).forEach((r) => {
          if (!r.isDirectory()) return;
          let n = Ie.join(t, r.name, "meta.json");
          if (!Z.existsSync(n)) return;
          let s = Z.statSync(n),
            a = this._lastOcrMtimes[r.name] || 0;
          if (
            s.mtimeMs <= a ||
            ((this._lastOcrMtimes[r.name] = s.mtimeMs), this._autoSyncRunning)
          )
            return;
          this._autoSyncRunning = !0;
          let i = this._getPythonCommand();
          if (!i) {
            this._autoSyncRunning = !1;
            return;
          }
          let c = `"${i.path}" ${i.args.join(" ")} -m paperforge --vault "${e}" sync`;
          (0, Ne.exec)(c, { timeout: 3e4, encoding: "utf-8" }, () => {
            ((this._autoSyncRunning = !1), (this._memoryStatusText = null));
          });
        });
      } catch (r) {}
  }
  readPaperforgeJson() {
    let e = this.app.vault.adapter.basePath,
      t = Ie.join(e, "paperforge.json"),
      r = {
        system_dir: "System",
        resources_dir: "Resources",
        literature_dir: "Literature",
        base_dir: "Bases",
      };
    try {
      if (!Z.existsSync(t)) return r;
      let n = Z.readFileSync(t, "utf-8"),
        s = JSON.parse(n),
        a = s.vault_config || {};
      return {
        system_dir: a.system_dir || s.system_dir || r.system_dir,
        resources_dir: a.resources_dir || s.resources_dir || r.resources_dir,
        literature_dir:
          a.literature_dir || s.literature_dir || r.literature_dir,
        base_dir: a.base_dir || s.base_dir || r.base_dir,
      };
    } catch (n) {
      return (
        console.warn(
          "PaperForge: Failed to read paperforge.json, using defaults",
          n
        ),
        r
      );
    }
  }
  savePaperforgeJson(e) {
    let t = this.app.vault.adapter.basePath,
      r = Ie.join(t, "paperforge.json"),
      n = {};
    try {
      Z.existsSync(r) && (n = JSON.parse(Z.readFileSync(r, "utf-8")));
    } catch (a) {
      console.warn("PaperForge: Failed to read paperforge.json for update", a);
    }
    (!n.vault_config || typeof n.vault_config != "object") &&
      (n.vault_config = {});
    let s = ["system_dir", "resources_dir", "literature_dir", "base_dir"];
    for (let a of s) e[a] !== void 0 && (n.vault_config[a] = e[a]);
    n.schema_version || (n.schema_version = "2");
    for (let a of s) delete n[a];
    try {
      if (
        (Z.writeFileSync(r, JSON.stringify(n, null, 2), "utf-8"), this.settings)
      ) {
        let a = this.readPaperforgeJson();
        ((this.settings.system_dir = a.system_dir),
          (this.settings.resources_dir = a.resources_dir),
          (this.settings.literature_dir = a.literature_dir),
          (this.settings.base_dir = a.base_dir));
      }
    } catch (a) {
      (console.error("PaperForge: Failed to write paperforge.json", a),
        new J.Notice(
          "PaperForge: Failed to save configuration to paperforge.json"
        ));
    }
  }
  onunload() {
    (this._pollTimer && clearInterval(this._pollTimer),
      this.app.workspace.detachLeavesOfType(Se));
  }
  async loadSettings() {
    ((this.settings = Object.assign({}, Ve, await this.loadData())),
      this.settings.features &&
        Ve.features &&
        (this.settings.features = Object.assign(
          {},
          Ve.features,
          this.settings.features || {}
        )),
      this.settings.frozen_skills || (this.settings.frozen_skills = {}));
    let e = this.readPaperforgeJson();
    if (
      ((this.settings.system_dir = e.system_dir),
      (this.settings.resources_dir = e.resources_dir),
      (this.settings.literature_dir = e.literature_dir),
      (this.settings.base_dir = e.base_dir),
      this.settings.python_path && this.settings.python_path.trim())
    ) {
      let t = this.settings.python_path.trim();
      Z.existsSync(t)
        ? (this.settings._python_path_stale = !1)
        : (console.warn(
            `PaperForge: Saved python_path "${t}" no longer exists - showing stale warning`
          ),
          (this.settings._python_path_stale = !0));
    }
  }
  async saveSettings() {
    let e = {};
    for (let t of Object.keys(Ve))
      t in this.settings && (e[t] = this.settings[t]);
    await this.saveData(e);
  }
  _checkReleaseNotes() {
    let e = this.manifest.version;
    if (this.settings.last_seen_version === e) return;
    let s = (xt().versions || []).find((i) => i.version === e);
    class a extends J.Modal {
      constructor(c, p) {
        (super(c), (this._entry = p));
      }
      onOpen() {
        let { contentEl: c } = this;
        if (
          (c.createEl("h2", {
            text: `PaperForge v${e} \u66F4\u65B0\u8BF4\u660E`,
          }),
          this._entry)
        ) {
          if (
            (c.createEl("p", {
              text: this._entry.title,
              cls: "paperforge-modal-subtitle",
            }),
            this._entry.breaking_or_migration &&
              this._entry.breaking_or_migration.length > 0)
          ) {
            c.createEl("h4", {
              text: "\u884C\u4E3A\u53D8\u66F4 / \u8FC1\u79FB\u6CE8\u610F",
            });
            for (let p of this._entry.breaking_or_migration)
              c.createEl("p", {
                text: `\u2022 ${p}`,
                cls: "paperforge-modal-item",
              });
          }
          if (this._entry.new_features && this._entry.new_features.length > 0) {
            c.createEl("h4", { text: "\u65B0\u529F\u80FD" });
            for (let p of this._entry.new_features)
              c.createEl("p", {
                text: `\u2022 ${p}`,
                cls: "paperforge-modal-item",
              });
          }
          if (this._entry.fixes && this._entry.fixes.length > 0) {
            c.createEl("h4", { text: "\u4FEE\u590D" });
            for (let p of this._entry.fixes)
              c.createEl("p", {
                text: `\u2022 ${p}`,
                cls: "paperforge-modal-item",
              });
          }
          if (
            this._entry.recommended_actions &&
            this._entry.recommended_actions.length > 0
          ) {
            let p = c.createEl("div", {
              cls: "paperforge-release-recommended",
            });
            (p.createEl("h4", { text: "\u5EFA\u8BAE\u64CD\u4F5C", cls: "" }),
              (p.style.marginBottom = "8px"));
            for (let u of this._entry.recommended_actions)
              p.createEl("p", {
                text: `\u2022 ${u}`,
                cls: "paperforge-release-item-bold",
              });
          }
        } else
          c.createEl("p", {
            text:
              "\u7248\u672C\u5DF2\u66F4\u65B0\u81F3 v" +
              e +
              "\uFF0C\u8BF7\u524D\u5F80\u8BBE\u7F6E \u2192 \u66F4\u65B0\u4E0E\u624B\u518C \u67E5\u770B\u5B8C\u6574\u66F4\u65B0\u8BB0\u5F55\u3002",
          });
        new J.Setting(c).addButton((p) =>
          p
            .setButtonText("\u77E5\u9053\u4E86")
            .setCta()
            .onClick(() => {
              this.close();
            })
        );
      }
      onClose() {
        let { contentEl: c } = this;
        c.empty();
      }
    }
    (new a(this.app, s).open(),
      (this.settings.last_seen_version = e),
      this.saveSettings());
  }
};
