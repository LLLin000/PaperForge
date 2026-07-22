"use strict";
var ur = Object.create;
var je = Object.defineProperty;
var _r = Object.getOwnPropertyDescriptor;
var fr = Object.getOwnPropertyNames;
var hr = Object.getPrototypeOf,
  gr = Object.prototype.hasOwnProperty;
var mr = (d, l) => () => (l || d((l = { exports: {} }).exports, l), l.exports),
  yr = (d, l) => {
    for (var e in l) je(d, e, { get: l[e], enumerable: !0 });
  },
  St = (d, l, e, t) => {
    if ((l && typeof l == "object") || typeof l == "function")
      for (let r of fr(l))
        !gr.call(d, r) &&
          r !== e &&
          je(d, r, {
            get: () => l[r],
            enumerable: !(t = _r(l, r)) || t.enumerable,
          });
    return d;
  };
var H = (d, l, e) => (
    (e = d != null ? ur(hr(d)) : {}),
    St(
      l || !d || !d.__esModule
        ? je(e, "default", { value: d, enumerable: !0 })
        : e,
      d
    )
  ),
  br = (d) => St(je({}, "__esModule", { value: !0 }), d);
var lt = mr((Ur, Sr) => {
  Sr.exports = {
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
var zr = {};
yr(zr, { default: () => et });
module.exports = br(zr);
var K = require("obsidian"),
  $ = H(require("fs")),
  Ae = H(require("path")),
  De = require("child_process");
var ge = "paperforge-status",
  Le = "paperforge",
  Rt =
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path><line x1="8" y1="7" x2="16" y2="7"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>',
  Q = [
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
  Oe = {
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
function Ft(d, l) {
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
function rt(d, l) {
  return d && { ...d, ...l };
}
var ze = 2,
  Me = ["installation", "library", "ocr", "memory", "maintenance", "help"],
  vr = new Set([
    "checking",
    "ready",
    "not_enabled",
    "setup_required",
    "action_required",
    "detection_failed",
  ]),
  wt = new Set([
    "unknown",
    "unavailable",
    "missing_input",
    "needs_action",
    "limited",
    "ready",
  ]),
  Er = new Set(["unknown", "ok", "warning", "error"]),
  Pt = new Set(["idle", "running"]),
  xr = new Set(["safe", "destructive", "irreversible"]);
function Ct(d) {
  if (!d || typeof d != "object" || Array.isArray(d)) return !1;
  let l = d;
  return !(
    typeof l.action_id != "string" ||
    !l.action_id ||
    typeof l.verb != "string" ||
    typeof l.label != "string" ||
    typeof l.availability != "string" ||
    typeof l.safety_class != "string" ||
    !xr.has(l.safety_class) ||
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
function Ie(d) {
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
function At() {
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
function nt(d, l) {
  if (!d || typeof d != "object") return !1;
  let e = d;
  if (
    e.schema_version !== ze ||
    typeof e.module != "string" ||
    !e.module ||
    !Me.includes(e.module) ||
    (l !== void 0 && e.module !== l) ||
    typeof e.capability_state != "string" ||
    !wt.has(e.capability_state) ||
    typeof e.activity_state != "string" ||
    !Pt.has(e.activity_state) ||
    typeof e.user_state != "string" ||
    !vr.has(e.user_state) ||
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
    (r.primary !== null && !Ct(r.primary)) ||
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
        !wt.has(s.capability_state) ||
        typeof s.severity != "string" ||
        !Er.has(s.severity) ||
        typeof s.activity_state != "string" ||
        !Pt.has(s.activity_state) ||
        (s.activity_label !== null && typeof s.activity_label != "string")
      )
        return !1;
      if (s.activity_progress !== null) {
        if (typeof s.activity_progress != "object") return !1;
        let o = s.activity_progress;
        if (typeof o.current != "number" || typeof o.total != "number")
          return !1;
      }
      if (
        typeof s.reason_code != "string" ||
        !s.reason_code ||
        typeof s.reason_text != "string" ||
        (s.action !== null && !Ct(s.action))
      )
        return !1;
    }
  }
  return !0;
}
function re(d) {
  return {
    schema_version: ze,
    module: d,
    capability_state: "unknown",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    severity: "unknown",
    reason: { code: d + ".no_probe", text: d + " has not been probed yet." },
    action: { primary: d === "maintenance" ? null : Ie(d) },
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
function at(d) {
  return {
    schema_version: ze,
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
    action: { primary: d === "maintenance" ? null : Ie(d) },
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
function ve(d) {
  return {
    schema_version: ze,
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
    action: { primary: d === "maintenance" ? null : Ie(d) },
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
function st(d) {
  if (d.activity_state === "running") return !1;
  if (d.ttl_seconds <= 0) return !0;
  let l = new Date(d.updated_at).getTime();
  return isNaN(l) ? !0 : Date.now() - l > d.ttl_seconds * 1e3;
}
function Dt(d) {
  return d.capability_state === "ready" && d.action.primary === null;
}
function Tt(d) {
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
function Lt(d, l) {
  let e = {};
  for (let t of l) {
    let r = d[t];
    if (!r || typeof r != "object") {
      e[t] = re(t);
      continue;
    }
    if (!nt(r, t)) {
      e[t] = ve(t);
      continue;
    }
    if (st(r)) {
      e[t] = at(t);
      continue;
    }
    e[t] = r;
  }
  return e;
}
var it = {
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
      md_select_installation: "Foundation",
      md_select_library: "Library",
      md_select_ocr: "OCR",
      md_select_memory: "Smart Retrieval",
      md_select_agent: "Agent Integration",
      installation_detail_heading: "Foundation",
      library_detail_heading: "Library",
      ocr_detail_heading: "OCR",
      memory_detail_heading: "Smart Retrieval",
      agent_detail_heading: "Agent Integration",
      btn_back_to_overview: "\u2190 Back to Overview",
      agent_integration_section: "Agent Integration",
      module_detail_open_installation: "Open Foundation",
      module_detail_open_help: "Help",
      module_detail_open_maintenance: "Maintenance",
      module_detail_open_library: "Open Library",
      module_detail_open_ocr: "Open OCR",
      module_detail_open_memory: "Open Smart Retrieval",
      action_unknown_pair: "Unknown action: {verb}",
      ocr_stop_batch: "Stop OCR batch",
      runtime_not_available: "Environment unavailable",
      md_unavailable_module: "Not available yet",
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
      cc_module_foundation: "Foundation",
      cc_module_agent: "Agent Integration",
      cc_badge_checking: "Checking",
      cc_badge_ready: "Ready",
      cc_badge_not_enabled: "Not Enabled",
      cc_badge_setup_required: "Setup Required",
      cc_badge_action_required: "Action Required",
      cc_badge_detection_failed: "Detection Failed",
      cc_summary_ready: "PaperForge is ready",
      cc_summary_incomplete: "Setup incomplete",
      cc_summary_ready_body: "Foundation and Library are operational.",
      cc_summary_incomplete_body:
        "Complete Foundation and Library setup to use PaperForge.",
      cc_summary_checking: "Checking PaperForge",
      cc_summary_checking_body: "Checking Foundation and Library status\u2026",
      cc_refresh_btn: "Refresh Status",
      cc_last_checked: "Last checked: ",
      cc_maintenance_count: "{n} items need attention",
      cc_card_retry: "Retry",
      cc_action_rebuild_derived: "Rebuild",
      ocr_progress: "{current}/{total} papers",
      cc_operational_modules: "Operational modules",
      cc_consequence_default: "Status is not available yet.",
      cc_consequence_checking: "Checking the latest status\u2026",
      cc_consequence_detection_failed:
        "PaperForge could not determine the current status.",
      cc_consequence_setup_required: "Configuration is required before use.",
      cc_consequence_action_required: "A problem needs your attention.",
      cc_consequence_installation_ready: "PaperForge is ready on this device.",
      cc_consequence_library_ready:
        "Your Zotero library is connected and current.",
      cc_consequence_ocr_ready: "OCR is ready to process papers.",
      cc_consequence_memory_ready: "Your papers are indexed and searchable.",
      cc_consequence_agent_not_enabled:
        "Choose an agent platform when you want to deploy PaperForge Skills.",
      cc_consequence_ocr_not_enabled:
        "OCR is optional and is currently not enabled.",
      cc_consequence_memory_not_enabled:
        "Smart Retrieval is optional and is currently not enabled.",
      md_foundation_overview: "Environment",
      md_foundation_ready:
        "PaperForge is installed, verified, and ready for normal use.",
      md_library_connection: "Zotero connection",
      md_library_ready: "Zotero is connected and literature is up to date.",
      md_library_corpus: "Literature corpus",
      md_library_last_sync: "Last successful sync",
      md_ocr_status: "OCR capability",
      ocr_error_notice:
        "OCR stopped because of an error. Open Advanced Diagnostics for details.",
      ocr_run_complete: "OCR run complete.",
      ocr_rebuild_complete: "OCR rebuild complete.",
      ocr_redo_complete: "OCR redo complete.",
      ocr_stopped_notice: "OCR batch stopped.",
      ocr_failed_notice:
        "OCR did not complete. Open Advanced Diagnostics for details.",
      md_ocr_ready: "OCR is configured and ready.",
      md_ocr_workspace: "Open OCR Workspace",
      md_retrieval_coverage: "Retrieval coverage",
      md_retrieval_ready: "All available papers are indexed and searchable.",
      md_agent_integration: "Agent Integration",
      md_agent_placeholder:
        "Configure a target platform, deploy PaperForge files, and manage Skills. File deployment does not verify a live agent connection.",
      md_agent_platform: "Target platform",
      md_agent_deployment: "Deployment state",
      agent_deployed: "Files deployed",
      agent_not_deployed: "Files not deployed",
      agent_live_connection: "Live connection",
      agent_verify_found: "PaperForge Skills were found for this platform.",
      agent_verify_missing:
        "No PaperForge Skills were found for this platform. Run setup to deploy them.",
      skills_system: "System Skills",
      skills_user: "User Skills",
      skills_empty: "No Skills are deployed for the selected platform.",
      md_agent_connection_unknown: "Live connection is not verified",
      md_agent_skills: "PaperForge Skills",
      md_copy_diagnostic: "Copy Support Diagnostic",
      md_configuration: "Configuration",
      md_current_activity: "Current activity",
      config_change: "Change",
      config_save: "Save",
      config_cancel: "Cancel",
      config_verify: "Verify",
      config_configured: "Configured",
      config_not_configured: "Not configured",
      config_zotero_dir: "Zotero data directory",
      problem_what_happened: "What happened",
      problem_impact: "Impact:",
      problem_next: "Next:",
      problem_copy: "Copy Diagnostic Information",
      problem_use_action: "Use the action above to resolve this problem.",
      library_problem_impact:
        "New references and literature notes may not be available.",
      ocr_problem_impact: "Some papers may not have readable full text.",
      retrieval_problem_impact:
        "Search and retrieval may miss papers until coverage is restored.",
      metric_after_sync: "Available after the next successful sync",
      metric_not_available: "Not available",
      coverage_complete: "Complete",
      retrieval_freshness: "Last checked",
      md_module_switcher: "Module",
      advanced_diagnostics: "Advanced Diagnostics",
      foundation_version: "PaperForge version",
      foundation_last_verified: "Last verified",
      foundation_runtime_managed: "Managed environment",
      foundation_runtime_system: "System environment",
      foundation_runtime_unavailable: "Environment unavailable",
      foundation_skills_ready: "Available",
      foundation_skills: "Skills",
      setup_welcome: "Set up PaperForge",
      setup_desc:
        "Complete the required stages, then choose any optional capabilities you want to enable.",
      setup_stage_1: "Foundation",
      setup_stage_2: "Connect Library",
      setup_stage_3: "Optional Capabilities",
      setup_stage_4: "Review & Begin",
      setup_progress: "Setup progress",
      setup_foundation_title: "Step 1: Foundation",
      setup_foundation_desc:
        "PaperForge needs a verified environment on this device.",
      setup_ready: "Foundation is ready.",
      setup_library_title: "Step 2: Connect Library",
      setup_library_desc:
        "Connect Zotero so PaperForge can sync your literature.",
      setup_library_ready: "Library is connected.",
      setup_optionals_title: "Step 3: Optional Capabilities",
      setup_optionals_desc:
        "Choose only what you need. Skipped capabilities can be enabled later.",
      setup_opt_ocr_desc: "Extract text and figures from PDFs",
      setup_opt_memory_desc: "Search and navigate across your papers",
      setup_opt_agent_desc: "Deploy and manage PaperForge Skills",
      setup_review_title: "Step 4: Review & Begin",
      setup_review_selected: "Selected: ",
      setup_no_optionals: "No optional capabilities selected.",
      setup_incomplete_warn:
        "Foundation and Library must be ready before setup can finish.",
      setup_nav_continue: "Continue",
      setup_nav_skip: "Skip for now",
      setup_nav_back: "Back",
      setup_nav_complete: "Complete Setup",
      help_title: "Help",
      help_intro:
        "Choose a task or copy a privacy-safe diagnostic for support.",
      help_getting_started: "Getting started",
      help_library_task: "Connect Zotero and sync your literature",
      help_ocr_task: "Configure OCR and open the OCR Workspace",
      help_retrieval_task: "Enable Smart Retrieval and build coverage",
      help_agent_task: "Choose an agent platform and deploy Skills",
      help_current_problem: "Current problem guidance",
      help_no_problem: "No current problem needs guidance.",
      help_support: "Support Diagnostic",
      help_support_desc:
        "Copies module states and version identifiers without secrets, content, identity, absolute paths, or raw logs.",
      help_copy: "Copy Support Diagnostic",
      help_documentation: "Documentation",
      help_documentation_desc:
        "Open the project guide for setup, workflows, and troubleshooting.",
      help_open_documentation: "Open PaperForge Documentation",
      help_release_notes: "Release notes",
      help_release_notes_desc:
        "Installed version: {version}. See GitHub for the complete change history.",
      help_open_release_notes: "Open Release Notes",
      support_diagnostic_copied: "Support diagnostic copied.",
      maintenance_empty_title: "No maintenance needed",
      maintenance_empty_body:
        "There are no unresolved problems that require action.",
      maintenance_default_impact:
        "This capability may be unavailable or return incomplete results.",
      maintenance_open_module: "Open module",
      migration_banner_title: "Credential Migration Notice",
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
      migration_banner_body:
        "Credentials for {modules} could not be moved to secure storage automatically. Re-enter them in the owning module.",
      migration_banner_next:
        "Save the new value; PaperForge will retry secure migration on restart.",
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
      cc_reason_library_sync_failed:
        "Last library sync failed. Retry when the source is available.",
      cc_reason_ocr_ready: "OCR pipeline is configured and functional.",
      cc_reason_ocr_config_missing:
        "Configuration not found \u2014 run setup to configure OCR.",
      cc_reason_ocr_config_corrupt:
        "Configuration file is corrupt \u2014 OCR cannot proceed.",
      cc_reason_ocr_api_key_missing:
        "No OCR API key configured \u2014 add one in setup.",
      cc_reason_ocr_artifacts_missing:
        "No OCR output found \u2014 run OCR on papers.",
      cc_reason_memory_ready: "Smart Retrieval is healthy and indexed.",
      cc_reason_memory_db_missing:
        "The retrieval index has not been built \u2014 build it to enable search.",
      cc_reason_memory_db_corrupt:
        "The retrieval index is damaged \u2014 restore it from backup.",
      cc_reason_memory_index_stale:
        "Smart Retrieval needs a rebuild to match the current library.",
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
      md_select_installation: "\u57FA\u7840\u73AF\u5883",
      md_select_library: "\u6587\u732E\u5E93",
      md_select_ocr: "OCR",
      md_select_memory: "\u667A\u80FD\u68C0\u7D22",
      md_select_agent: "Agent \u96C6\u6210",
      installation_detail_heading: "\u57FA\u7840\u73AF\u5883",
      library_detail_heading: "\u6587\u732E\u5E93",
      ocr_detail_heading: "OCR",
      memory_detail_heading: "\u667A\u80FD\u68C0\u7D22",
      agent_detail_heading: "Agent \u96C6\u6210",
      btn_back_to_overview: "\u2190 \u8FD4\u56DE\u6982\u89C8",
      agent_integration_section: "Agent \u96C6\u6210",
      module_detail_open_installation: "\u6253\u5F00\u57FA\u7840\u73AF\u5883",
      module_detail_open_help: "\u5E2E\u52A9",
      module_detail_open_maintenance: "\u7EF4\u62A4",
      module_detail_open_library: "\u6253\u5F00\u6587\u732E\u5E93",
      module_detail_open_ocr: "\u6253\u5F00 OCR",
      module_detail_open_memory: "\u6253\u5F00\u667A\u80FD\u68C0\u7D22",
      action_unknown_pair: "\u672A\u77E5\u64CD\u4F5C: {verb}",
      ocr_stop_batch: "\u505C\u6B62 OCR \u6279\u5904\u7406",
      runtime_not_available: "\u73AF\u5883\u4E0D\u53EF\u7528",
      md_unavailable_module: "\u6682\u4E0D\u53EF\u7528",
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
      cc_module_foundation: "\u57FA\u7840\u73AF\u5883",
      cc_module_agent: "Agent \u96C6\u6210",
      cc_badge_checking: "\u6B63\u5728\u68C0\u67E5",
      cc_badge_ready: "\u5DF2\u5C31\u7EEA",
      cc_badge_not_enabled: "\u672A\u542F\u7528",
      cc_badge_setup_required: "\u9700\u8981\u8BBE\u7F6E",
      cc_badge_action_required: "\u9700\u8981\u64CD\u4F5C",
      cc_badge_detection_failed: "\u68C0\u6D4B\u5931\u8D25",
      cc_summary_ready: "PaperForge \u5DF2\u5C31\u7EEA",
      cc_summary_incomplete: "\u8BBE\u7F6E\u672A\u5B8C\u6210",
      cc_summary_ready_body:
        "\u57FA\u7840\u73AF\u5883\u548C\u6587\u732E\u5E93\u5747\u5DF2\u6B63\u5E38\u8FD0\u884C\u3002",
      cc_summary_incomplete_body:
        "\u8BF7\u5B8C\u6210\u57FA\u7840\u73AF\u5883\u548C\u6587\u732E\u5E93\u8BBE\u7F6E\u540E\u518D\u4F7F\u7528 PaperForge\u3002",
      cc_summary_checking: "\u6B63\u5728\u68C0\u67E5 PaperForge",
      cc_summary_checking_body:
        "\u6B63\u5728\u68C0\u67E5\u57FA\u7840\u73AF\u5883\u548C\u6587\u732E\u5E93\u72B6\u6001\u2026",
      cc_refresh_btn: "\u5237\u65B0\u72B6\u6001",
      cc_last_checked: "\u4E0A\u6B21\u68C0\u67E5\uFF1A",
      cc_maintenance_count: "{n} \u9879\u9700\u8981\u5173\u6CE8",
      cc_card_retry: "\u91CD\u8BD5",
      cc_consequence_default:
        "\u5F53\u524D\u72B6\u6001\u6682\u4E0D\u53EF\u7528\u3002",
      cc_action_rebuild_derived: "\u91CD\u5EFA",
      ocr_progress: "{current}/{total} \u7BC7\u8BBA\u6587",
      cc_operational_modules: "\u8FD0\u884C\u6A21\u5757",
      cc_consequence_checking:
        "\u6B63\u5728\u68C0\u67E5\u6700\u65B0\u72B6\u6001\u2026",
      cc_consequence_detection_failed:
        "PaperForge \u65E0\u6CD5\u786E\u5B9A\u5F53\u524D\u72B6\u6001\u3002",
      cc_consequence_setup_required:
        "\u4F7F\u7528\u524D\u9700\u8981\u5B8C\u6210\u914D\u7F6E\u3002",
      cc_consequence_action_required:
        "\u6709\u4E00\u9879\u95EE\u9898\u9700\u8981\u5904\u7406\u3002",
      cc_consequence_installation_ready:
        "PaperForge \u5DF2\u5728\u6B64\u8BBE\u5907\u4E0A\u5C31\u7EEA\u3002",
      cc_consequence_library_ready:
        "Zotero \u6587\u732E\u5E93\u5DF2\u8FDE\u63A5\u5E76\u4FDD\u6301\u6700\u65B0\u3002",
      cc_consequence_ocr_ready:
        "OCR \u5DF2\u51C6\u5907\u597D\u5904\u7406\u8BBA\u6587\u3002",
      cc_consequence_memory_ready:
        "\u8BBA\u6587\u5DF2\u5EFA\u7ACB\u7D22\u5F15\u5E76\u53EF\u641C\u7D22\u3002",
      cc_consequence_agent_not_enabled:
        "\u9700\u8981\u90E8\u7F72 PaperForge Skills \u65F6\u518D\u9009\u62E9 Agent \u5E73\u53F0\u3002",
      cc_consequence_ocr_not_enabled:
        "OCR \u4E3A\u53EF\u9009\u529F\u80FD\uFF0C\u5F53\u524D\u672A\u542F\u7528\u3002",
      cc_consequence_memory_not_enabled:
        "\u667A\u80FD\u68C0\u7D22\u4E3A\u53EF\u9009\u529F\u80FD\uFF0C\u5F53\u524D\u672A\u542F\u7528\u3002",
      md_foundation_overview: "\u8FD0\u884C\u73AF\u5883",
      md_foundation_ready:
        "PaperForge \u5DF2\u5B89\u88C5\u5E76\u901A\u8FC7\u9A8C\u8BC1\uFF0C\u53EF\u4EE5\u6B63\u5E38\u4F7F\u7528\u3002",
      md_library_connection: "Zotero \u8FDE\u63A5",
      ocr_error_notice:
        "OCR \u56E0\u9519\u8BEF\u505C\u6B62\uFF0C\u8BF7\u6253\u5F00\u9AD8\u7EA7\u8BCA\u65AD\u67E5\u770B\u8BE6\u60C5\u3002",
      ocr_run_complete: "OCR \u5904\u7406\u5B8C\u6210\u3002",
      ocr_rebuild_complete: "OCR \u91CD\u5EFA\u5B8C\u6210\u3002",
      ocr_redo_complete: "OCR \u91CD\u505A\u5B8C\u6210\u3002",
      ocr_stopped_notice: "OCR \u6279\u5904\u7406\u5DF2\u505C\u6B62\u3002",
      ocr_failed_notice:
        "OCR \u672A\u5B8C\u6210\uFF0C\u8BF7\u6253\u5F00\u9AD8\u7EA7\u8BCA\u65AD\u67E5\u770B\u8BE6\u60C5\u3002",
      md_library_ready:
        "Zotero \u5DF2\u8FDE\u63A5\uFF0C\u6587\u732E\u5E93\u5DF2\u540C\u6B65\u3002",
      md_library_corpus: "\u6587\u732E\u8BED\u6599\u5E93",
      md_library_last_sync: "\u4E0A\u6B21\u6210\u529F\u540C\u6B65",
      md_ocr_status: "OCR \u529F\u80FD",
      md_ocr_ready: "OCR \u5DF2\u914D\u7F6E\u5E76\u53EF\u7528\u3002",
      md_ocr_workspace: "\u6253\u5F00 OCR \u5DE5\u4F5C\u533A",
      md_retrieval_coverage: "\u68C0\u7D22\u8986\u76D6\u8303\u56F4",
      md_retrieval_ready:
        "\u6240\u6709\u53EF\u7528\u8BBA\u6587\u5747\u5DF2\u5EFA\u7ACB\u7D22\u5F15\u5E76\u53EF\u641C\u7D22\u3002",
      md_agent_integration: "Agent \u96C6\u6210",
      md_agent_placeholder:
        "\u914D\u7F6E\u76EE\u6807\u5E73\u53F0\u3001\u90E8\u7F72 PaperForge \u6587\u4EF6\u5E76\u7BA1\u7406 Skills\u3002\u6587\u4EF6\u5DF2\u90E8\u7F72\u4E0D\u4EE3\u8868\u5B9E\u65F6\u8FDE\u63A5\u5DF2\u7ECF\u9A8C\u8BC1\u3002",
      md_agent_platform: "\u76EE\u6807\u5E73\u53F0",
      md_agent_deployment: "\u90E8\u7F72\u72B6\u6001",
      agent_deployed: "\u6587\u4EF6\u5DF2\u90E8\u7F72",
      agent_not_deployed: "\u6587\u4EF6\u672A\u90E8\u7F72",
      agent_live_connection: "\u5B9E\u65F6\u8FDE\u63A5",
      agent_verify_found:
        "\u5DF2\u627E\u5230\u6B64\u5E73\u53F0\u7684 PaperForge Skills\u3002",
      agent_verify_missing:
        "\u672A\u627E\u5230\u6B64\u5E73\u53F0\u7684 PaperForge Skills\uFF0C\u8BF7\u8FD0\u884C\u8BBE\u7F6E\u8FDB\u884C\u90E8\u7F72\u3002",
      skills_system: "\u7CFB\u7EDF Skills",
      skills_user: "\u7528\u6237 Skills",
      skills_empty:
        "\u6240\u9009\u5E73\u53F0\u5C1A\u672A\u90E8\u7F72 Skills\u3002",
      md_agent_connection_unknown:
        "\u5B9E\u65F6\u8FDE\u63A5\u5C1A\u672A\u9A8C\u8BC1",
      md_agent_skills: "PaperForge Skills",
      md_copy_diagnostic: "\u590D\u5236\u652F\u6301\u8BCA\u65AD",
      md_configuration: "\u914D\u7F6E",
      md_current_activity: "\u5F53\u524D\u6D3B\u52A8",
      config_change: "\u66F4\u6539",
      config_save: "\u4FDD\u5B58",
      config_cancel: "\u53D6\u6D88",
      config_verify: "\u9A8C\u8BC1",
      config_configured: "\u5DF2\u914D\u7F6E",
      config_not_configured: "\u672A\u914D\u7F6E",
      config_zotero_dir: "Zotero \u6570\u636E\u76EE\u5F55",
      problem_what_happened: "\u53D1\u751F\u4E86\u4EC0\u4E48",
      problem_impact: "\u5F71\u54CD\uFF1A",
      problem_next: "\u4E0B\u4E00\u6B65\uFF1A",
      problem_copy: "\u590D\u5236\u8BCA\u65AD\u4FE1\u606F",
      problem_use_action:
        "\u4F7F\u7528\u4E0A\u65B9\u64CD\u4F5C\u5904\u7406\u6B64\u95EE\u9898\u3002",
      library_problem_impact:
        "\u65B0\u7684\u53C2\u8003\u6587\u732E\u548C\u6587\u732E\u7B14\u8BB0\u53EF\u80FD\u6682\u4E0D\u53EF\u7528\u3002",
      ocr_problem_impact:
        "\u90E8\u5206\u8BBA\u6587\u53EF\u80FD\u6CA1\u6709\u53EF\u9605\u8BFB\u7684\u5168\u6587\u3002",
      retrieval_problem_impact:
        "\u6062\u590D\u8986\u76D6\u524D\uFF0C\u641C\u7D22\u548C\u68C0\u7D22\u53EF\u80FD\u9057\u6F0F\u8BBA\u6587\u3002",
      metric_after_sync:
        "\u4E0B\u6B21\u6210\u529F\u540C\u6B65\u540E\u53EF\u7528",
      metric_not_available: "\u6682\u4E0D\u53EF\u7528",
      coverage_complete: "\u5B8C\u6574",
      retrieval_freshness: "\u4E0A\u6B21\u68C0\u67E5",
      md_module_switcher: "\u6A21\u5757",
      advanced_diagnostics: "\u9AD8\u7EA7\u8BCA\u65AD",
      foundation_version: "PaperForge \u7248\u672C",
      foundation_last_verified: "\u4E0A\u6B21\u9A8C\u8BC1",
      foundation_runtime_managed: "\u6258\u7BA1\u8FD0\u884C\u73AF\u5883",
      foundation_runtime_system: "\u7CFB\u7EDF\u8FD0\u884C\u73AF\u5883",
      foundation_runtime_unavailable:
        "\u8FD0\u884C\u73AF\u5883\u4E0D\u53EF\u7528",
      foundation_skills_ready: "\u53EF\u7528",
      foundation_skills: "Skills",
      feat_install_deps_desc:
        "\u5B89\u88C5\u667A\u80FD\u68C0\u7D22\u6240\u9700\u7684\u4F9D\u8D56\u9879\u3002",
      setup_welcome: "\u8BBE\u7F6E PaperForge",
      setup_desc:
        "\u5B8C\u6210\u5FC5\u9700\u9636\u6BB5\uFF0C\u7136\u540E\u9009\u62E9\u9700\u8981\u542F\u7528\u7684\u53EF\u9009\u529F\u80FD\u3002",
      setup_stage_1: "\u57FA\u7840\u73AF\u5883",
      setup_stage_2: "\u8FDE\u63A5\u6587\u732E\u5E93",
      setup_stage_3: "\u53EF\u9009\u529F\u80FD",
      setup_stage_4: "\u68C0\u67E5\u5E76\u5F00\u59CB",
      setup_progress: "\u8BBE\u7F6E\u8FDB\u5EA6",
      setup_foundation_title: "\u7B2C 1 \u6B65\uFF1A\u57FA\u7840\u73AF\u5883",
      setup_foundation_desc:
        "PaperForge \u9700\u8981\u5728\u6B64\u8BBE\u5907\u4E0A\u51C6\u5907\u597D\u7ECF\u8FC7\u9A8C\u8BC1\u7684\u8FD0\u884C\u73AF\u5883\u3002",
      setup_ready: "\u57FA\u7840\u73AF\u5883\u5DF2\u5C31\u7EEA\u3002",
      setup_library_title:
        "\u7B2C 2 \u6B65\uFF1A\u8FDE\u63A5\u6587\u732E\u5E93",
      setup_library_desc:
        "\u8FDE\u63A5 Zotero\uFF0C\u8BA9 PaperForge \u53EF\u4EE5\u540C\u6B65\u6587\u732E\u3002",
      setup_library_ready: "\u6587\u732E\u5E93\u5DF2\u8FDE\u63A5\u3002",
      setup_optionals_title: "\u7B2C 3 \u6B65\uFF1A\u53EF\u9009\u529F\u80FD",
      setup_optionals_desc:
        "\u53EA\u9009\u62E9\u9700\u8981\u7684\u529F\u80FD\uFF1B\u8DF3\u8FC7\u540E\u4ECD\u53EF\u968F\u65F6\u542F\u7528\u3002",
      setup_opt_ocr_desc:
        "\u4ECE PDF \u63D0\u53D6\u6587\u672C\u548C\u56FE\u8868",
      setup_opt_memory_desc: "\u8DE8\u8BBA\u6587\u641C\u7D22\u548C\u6D4F\u89C8",
      setup_opt_agent_desc: "\u90E8\u7F72\u5E76\u7BA1\u7406 PaperForge Skills",
      setup_review_title: "\u7B2C 4 \u6B65\uFF1A\u68C0\u67E5\u5E76\u5F00\u59CB",
      setup_review_selected: "\u5DF2\u9009\u62E9\uFF1A",
      setup_no_optionals: "\u672A\u9009\u62E9\u53EF\u9009\u529F\u80FD\u3002",
      setup_incomplete_warn:
        "\u57FA\u7840\u73AF\u5883\u548C\u6587\u732E\u5E93\u5747\u5C31\u7EEA\u540E\u624D\u80FD\u5B8C\u6210\u8BBE\u7F6E\u3002",
      setup_nav_continue: "\u7EE7\u7EED",
      setup_nav_skip: "\u6682\u65F6\u8DF3\u8FC7",
      setup_nav_back: "\u8FD4\u56DE",
      setup_nav_complete: "\u5B8C\u6210\u8BBE\u7F6E",
      help_title: "\u5E2E\u52A9",
      help_intro:
        "\u9009\u62E9\u4E00\u4E2A\u4EFB\u52A1\uFF0C\u6216\u590D\u5236\u9690\u79C1\u5B89\u5168\u7684\u652F\u6301\u8BCA\u65AD\u3002",
      help_getting_started: "\u5F00\u59CB\u4F7F\u7528",
      help_library_task: "\u8FDE\u63A5 Zotero \u5E76\u540C\u6B65\u6587\u732E",
      help_ocr_task:
        "\u914D\u7F6E OCR \u5E76\u6253\u5F00 OCR \u5DE5\u4F5C\u533A",
      help_retrieval_task:
        "\u542F\u7528\u667A\u80FD\u68C0\u7D22\u5E76\u5EFA\u7ACB\u8986\u76D6",
      help_agent_task:
        "\u9009\u62E9 Agent \u5E73\u53F0\u5E76\u90E8\u7F72 Skills",
      help_current_problem: "\u5F53\u524D\u95EE\u9898\u6307\u5F15",
      help_no_problem:
        "\u5F53\u524D\u6CA1\u6709\u9700\u8981\u6307\u5F15\u7684\u95EE\u9898\u3002",
      help_support: "\u652F\u6301\u8BCA\u65AD",
      help_support_desc:
        "\u4EC5\u590D\u5236\u6A21\u5757\u72B6\u6001\u548C\u7248\u672C\u6807\u8BC6\uFF0C\u4E0D\u5305\u542B\u5BC6\u94A5\u3001\u5185\u5BB9\u3001\u8EAB\u4EFD\u3001\u7EDD\u5BF9\u8DEF\u5F84\u6216\u539F\u59CB\u65E5\u5FD7\u3002",
      help_copy: "\u590D\u5236\u652F\u6301\u8BCA\u65AD",
      help_documentation: "\u6587\u6863",
      help_documentation_desc:
        "\u6253\u5F00\u9879\u76EE\u6307\u5357\uFF0C\u67E5\u770B\u8BBE\u7F6E\u3001\u5DE5\u4F5C\u6D41\u7A0B\u548C\u6545\u969C\u6392\u9664\u8BF4\u660E\u3002",
      help_open_documentation: "\u6253\u5F00 PaperForge \u6587\u6863",
      help_release_notes: "\u7248\u672C\u8BF4\u660E",
      help_release_notes_desc:
        "\u5F53\u524D\u5B89\u88C5\u7248\u672C\uFF1A{version}\u3002\u5B8C\u6574\u53D8\u66F4\u8BB0\u5F55\u8BF7\u67E5\u770B GitHub\u3002",
      help_open_release_notes: "\u6253\u5F00\u7248\u672C\u8BF4\u660E",
      support_diagnostic_copied:
        "\u652F\u6301\u8BCA\u65AD\u5DF2\u590D\u5236\u3002",
      maintenance_empty_title: "\u65E0\u9700\u7EF4\u62A4",
      maintenance_empty_body:
        "\u5F53\u524D\u6CA1\u6709\u9700\u8981\u5904\u7406\u7684\u672A\u89E3\u51B3\u95EE\u9898\u3002",
      maintenance_default_impact:
        "\u6B64\u529F\u80FD\u53EF\u80FD\u4E0D\u53EF\u7528\uFF0C\u6216\u8FD4\u56DE\u4E0D\u5B8C\u6574\u7684\u7ED3\u679C\u3002",
      maintenance_open_module: "\u6253\u5F00\u6A21\u5757",
      migration_banner_title: "\u51ED\u636E\u8FC1\u79FB\u901A\u77E5",
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
      migration_banner_body:
        "{modules} \u7684\u51ED\u636E\u65E0\u6CD5\u81EA\u52A8\u8FC1\u79FB\u5230\u5B89\u5168\u5B58\u50A8\uFF0C\u8BF7\u5728\u6240\u5C5E\u6A21\u5757\u4E2D\u91CD\u65B0\u8F93\u5165\u3002",
      migration_banner_next:
        "\u4FDD\u5B58\u65B0\u503C\u540E\uFF0CPaperForge \u5C06\u5728\u91CD\u542F\u65F6\u518D\u6B21\u5C1D\u8BD5\u5B89\u5168\u8FC1\u79FB\u3002",
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
      cc_reason_library_ready:
        "\u6587\u732E\u5E93\u5DF2\u540C\u6B65\u5E76\u5EFA\u7ACB\u7D22\u5F15\u3002",
      cc_reason_library_config_missing:
        "\u672A\u627E\u5230\u914D\u7F6E\uFF0C\u8BF7\u5148\u8BBE\u7F6E\u6587\u732E\u5E93\u3002",
      cc_reason_library_config_corrupt:
        "\u914D\u7F6E\u6587\u4EF6\u635F\u574F\uFF0C\u6587\u732E\u5E93\u65E0\u6CD5\u8FD0\u884C\u3002",
      cc_reason_library_zotero_missing:
        "\u5C1A\u672A\u914D\u7F6E Zotero \u6570\u636E\u76EE\u5F55\u3002",
      cc_reason_library_zotero_not_found:
        "Zotero \u6570\u636E\u76EE\u5F55\u4E0D\u5B58\u5728\u3002",
      cc_reason_library_index_missing:
        "\u5C1A\u672A\u5EFA\u7ACB\u6587\u732E\u7D22\u5F15\uFF0C\u8BF7\u5148\u540C\u6B65\u3002",
      cc_reason_library_index_stale:
        "\u6587\u732E\u7D22\u5F15\u5DF2\u8FC7\u671F\uFF0C\u8BF7\u540C\u6B65\u5237\u65B0\u3002",
      cc_reason_ocr_ready:
        "OCR \u5DF2\u914D\u7F6E\u5E76\u53EF\u6B63\u5E38\u8FD0\u884C\u3002",
      cc_reason_ocr_config_missing:
        "\u672A\u627E\u5230\u914D\u7F6E\uFF0C\u8BF7\u5148\u8BBE\u7F6E OCR\u3002",
      cc_reason_ocr_config_corrupt:
        "\u914D\u7F6E\u6587\u4EF6\u635F\u574F\uFF0COCR \u65E0\u6CD5\u8FD0\u884C\u3002",
      cc_reason_ocr_api_key_missing:
        "\u5C1A\u672A\u914D\u7F6E OCR API \u5BC6\u94A5\u3002",
      cc_reason_ocr_artifacts_missing:
        "\u5C1A\u65E0 OCR \u8F93\u51FA\uFF0C\u8BF7\u5148\u5904\u7406\u8BBA\u6587\u3002",
      cc_reason_memory_ready:
        "\u667A\u80FD\u68C0\u7D22\u72B6\u6001\u6B63\u5E38\u4E14\u5DF2\u5EFA\u7ACB\u7D22\u5F15\u3002",
      cc_reason_memory_db_missing:
        "\u5C1A\u672A\u5EFA\u7ACB\u68C0\u7D22\u7D22\u5F15\uFF0C\u8BF7\u5148\u6784\u5EFA\u4EE5\u542F\u7528\u641C\u7D22\u3002",
      cc_reason_memory_db_corrupt:
        "\u68C0\u7D22\u7D22\u5F15\u5DF2\u635F\u574F\uFF0C\u8BF7\u4ECE\u5907\u4EFD\u6062\u590D\u3002",
      cc_reason_memory_index_stale:
        "\u667A\u80FD\u68C0\u7D22\u9700\u8981\u91CD\u5EFA\u4EE5\u5339\u914D\u5F53\u524D\u6587\u732E\u5E93\u3002",
      cc_diag_module: "\u6A21\u5757",
      cc_diag_state: "\u72B6\u6001",
      cc_reason_library_sync_failed:
        "\u4E0A\u6B21\u6587\u732E\u5E93\u540C\u6B65\u5931\u8D25\uFF0C\u8BF7\u5728\u6570\u636E\u6E90\u53EF\u7528\u540E\u91CD\u8BD5\u3002",
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
  ot = null;
function kr(d) {
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
  try {
    let l = document.documentElement.lang || navigator.language;
    if (l && l.startsWith("zh")) return "zh";
  } catch (l) {}
  return "en";
}
function Ot(d, l = "") {
  ot = (l || kr(d)).startsWith("zh") ? it.zh : it.en;
}
function i(d) {
  return (ot && ot[d]) || it.en[d] || d;
}
var C = require("obsidian"),
  j = H(require("fs")),
  G = H(require("path")),
  ir = H(require("os")),
  ee = require("child_process");
var or = H(lt());
var wr = {
    checking: "pf-badge pf-badge--checking",
    ready: "pf-badge pf-badge--ready",
    not_enabled: "pf-badge pf-badge--not-enabled",
    setup_required: "pf-badge pf-badge--setup-required",
    action_required: "pf-badge pf-badge--action-required",
    detection_failed: "pf-badge pf-badge--detection-failed",
  },
  Pr = {
    checking: "Checking",
    ready: "Ready",
    not_enabled: "Not Enabled",
    setup_required: "Setup Required",
    action_required: "Action Required",
    detection_failed: "Detection Failed",
  };
function Ee(d, l, e) {
  return d.createEl("span", {
    cls: wr[l],
    text: e != null ? e : Pr[l],
    attr: { role: "status" },
  });
}
function ct(d, l) {
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
function W(d, l) {
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
function $e(d, l) {
  let e = d.createEl("div", { cls: "pf-error-anatomy" });
  e.createEl("div", { cls: "pf-error-title", text: l.whatHappened });
  let t = e.createEl("div", { cls: "pf-error-impact" });
  (t.createEl("span", {
    cls: "pf-error-impact-label",
    text: (l.impactLabel || "Impact:") + " ",
  }),
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
function Mt(d, l) {
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
function It(d) {
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
function Bt(d, l) {
  navigator.clipboard
    .writeText(d)
    .then(() => {
      l == null || l();
    })
    .catch((e) => {
      console.warn("[PaperForge] Failed to copy diagnostic:", e);
    });
}
function Nt(d) {
  return { envelope: d, capturedAt: new Date().toISOString() };
}
function Ht(d, l) {
  return !d || l.user_state === "ready"
    ? !0
    : !(l.user_state === "detection_failed" || d.user_state === "ready");
}
function Vt(d, l) {
  var t, r, n, s, a, o, c;
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
          (o = (a = u.reason) == null ? void 0 : a.text) == null
            ? void 0
            : o.slice(0, 200)) != null
          ? c
          : void 0,
    });
  }
  return e;
}
var ce = H(require("fs")),
  me = H(require("path")),
  Ut = H(require("os")),
  xe = require("child_process");
var Cr = ["paddleocr_api_key", "vector_db_api_key"],
  Rr = {
    paddleocr_api_key: "paddleocr-api-key",
    vector_db_api_key: "vector-db-api-key",
  },
  jt = {
    paddleocr_api_key: "_paddleocr_configured",
    vector_db_api_key: "_vector_db_configured",
  },
  Fr = {
    ocr: ["PADDLEOCR_API_KEY", "PADDLEOCR_API_TOKEN"],
    memory: ["VECTOR_DB_API_KEY", "VECTOR_DB_API_BASE", "VECTOR_DB_API_MODEL"],
    embed: ["VECTOR_DB_API_KEY", "VECTOR_DB_API_BASE", "VECTOR_DB_API_MODEL"],
  };
async function zt(d, l) {
  var s;
  let e = (s = d.app) == null ? void 0 : s.secretStorage;
  if (!e || typeof e.getSecret != "function")
    return { migrated: [], warnings: [] };
  let t = [],
    r = [],
    n = Array.isArray(l._migrated_keys) ? l._migrated_keys : [];
  for (let a of Cr) {
    if (n.includes(a)) continue;
    let o = typeof l[a] == "string" ? l[a] : "";
    if (!o) continue;
    let c = Rr[a] || a,
      p = await e.getSecret(c);
    if (p !== null) {
      if (p === o) {
        ((l[a] = ""), (l[jt[a]] = !0), t.push(a));
        continue;
      }
      r.push(a);
      continue;
    }
    try {
      await e.setSecret(c, o);
    } catch (_) {
      r.push(a);
      continue;
    }
    if ((await e.getSecret(c)) !== o) {
      r.push(a);
      continue;
    }
    ((l[a] = ""), t.push(a), (l[jt[a]] = !0));
  }
  if (t.length > 0 || r.length > 0) {
    let a = Array.isArray(l._migrated_keys) ? [...l._migrated_keys] : [];
    for (let o of t) a.includes(o) || a.push(o);
    if (((l._migrated_keys = a), r.length > 0)) {
      let o = Array.isArray(l._migration_warnings) ? l._migration_warnings : [];
      l._migration_warnings = [...o, ...r];
    }
    await d.saveData(l);
  }
  return { migrated: t, warnings: r };
}
async function $t(d, l) {
  if (!Fr[l]) return {};
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
var Ar = ["PADDLEOCR_", "VECTOR_DB_", "OPENAI_"];
function Kt(d) {
  let l = {};
  for (let [e, t] of Object.entries(d))
    Ar.some((r) => e.startsWith(r)) || (l[e] = t);
  return l;
}
var pt = null,
  qt = !1;
function dt(d) {
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
function ut() {
  if (qt) return pt;
  qt = !0;
  try {
    let d;
    if (process.platform === "win32") {
      let l = process.env.ComSpec || "C:\\Windows\\System32\\cmd.exe";
      d = (0, xe.execFileSync)(l, ["/c", "where", "git"], {
        timeout: 5e3,
        windowsHide: !0,
        encoding: "utf-8",
      });
    } else
      d = (0, xe.execFileSync)("which", ["git"], {
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
      l && (pt = me.dirname(l));
    }
  } catch (d) {}
  return pt;
}
function pe() {
  let d = { ...process.env },
    l = process.platform,
    e = Ut.homedir(),
    t = [],
    r = ut();
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
  return ((d.PATH = [...t, n].filter(Boolean).join(me.delimiter)), Kt(d));
}
async function de(d, l) {
  let e = await $t(d, l),
    t = pe();
  return Object.keys(e).length === 0 ? t : Object.assign({}, t, e);
}
function Wt(d) {
  return String(d)
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "")
    .includes("betterbibtex");
}
function _t(d) {
  if (!d) return !1;
  try {
    if (!ce.existsSync(d)) return !1;
    for (let l of ce.readdirSync(d)) if (Wt(l)) return !0;
  } catch (l) {}
  return !1;
}
function Ke(d) {
  if (!d) return !1;
  try {
    if (!ce.existsSync(d)) return !1;
    for (let l of ce.readdirSync(d)) {
      let e = me.join(d, l, "extensions");
      try {
        if (!ce.existsSync(e)) continue;
        for (let t of ce.readdirSync(e)) if (Wt(t)) return !0;
      } catch (t) {}
    }
  } catch (l) {}
  return !1;
}
var Se = H(require("fs")),
  q = H(require("path")),
  Zt = require("child_process");
function Dr(d, l) {
  let e = l || Se,
    t = q.join(d, "paperforge.json"),
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
function ae(d, l) {
  let e = Dr(d, l),
    t = q.join(d, e.system_dir, "PaperForge");
  return {
    vault: d,
    systemDir: t,
    indexesDir: q.join(t, "indexes"),
    logsDir: q.join(t, "logs"),
    dbPath: q.join(t, "indexes", "paperforge.db"),
    memoryStatePath: q.join(t, "indexes", "memory-runtime-state.json"),
    vectorStatePath: q.join(t, "indexes", "vector-runtime-state.json"),
    healthStatePath: q.join(t, "indexes", "runtime-health.json"),
    buildStatePath: q.join(t, "indexes", "vector-build-state.json"),
    orphanStatePath: q.join(t, "indexes", "sync-orphan-state.json"),
    exportsDir: q.join(t, "exports"),
    ocrDir: q.join(t, "ocr"),
    pluginDataPath: q.join(
      d,
      ".obsidian",
      "plugins",
      "paperforge",
      "data.json"
    ),
    pfJsonPath: q.join(d, "paperforge.json"),
    configWarning: e._warning,
  };
}
function ft(d) {
  try {
    return Se.existsSync(d) ? JSON.parse(Se.readFileSync(d, "utf-8")) : null;
  } catch (l) {
    return null;
  }
}
function Tr(d) {
  let l = ae(d);
  return ft(l.memoryStatePath);
}
var ke = null;
function qe(d) {
  let l = ae(d),
    e = Date.now();
  if (ke && ke.vaultPath === d && e - ke.ts < 2e3) return ke.result;
  let t = "",
    r = [
      q.join(d, ".paperforge-test-venv", "Scripts", "python.exe"),
      q.join(d, ".venv", "Scripts", "python.exe"),
      q.join(d, "venv", "Scripts", "python.exe"),
    ];
  for (let s = 0; s < r.length; s++)
    if (Se.existsSync(r[s])) {
      t = r[s];
      break;
    }
  if (t)
    try {
      let s = (0, Zt.execFileSync)(
          t,
          ["-m", "paperforge", "--vault", d, "embed", "status", "--json"],
          { encoding: "utf-8", timeout: 1e4, windowsHide: !0 }
        ),
        a = JSON.parse(s);
      if (a.ok && a.data) {
        let o = a.data;
        return ((ke = { vaultPath: d, result: o, ts: e }), o);
      }
    } catch (s) {}
  let n = ft(l.vectorStatePath);
  return ((ke = { vaultPath: d, result: n, ts: e }), n);
}
function Be(d) {
  let l = ae(d);
  return ft(l.healthStatePath);
}
function Gt(d) {
  var e;
  let l = Be(d);
  return !!(l && ((e = l.summary) == null ? void 0 : e.status) === "ok");
}
function ht(d) {
  let l = Tr(d);
  return !l || l.paper_count_db === 0
    ? "DB not found. Run paperforge memory build."
    : "Papers: " + l.paper_count_db + " | " + (l.fresh ? "fresh" : "stale");
}
function we(d) {
  var t, r, n;
  let l = qe(d);
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
var Z = require("obsidian"),
  ne = H(require("fs")),
  mt = H(require("path")),
  tr = H(require("https")),
  Pe = require("child_process");
var gt = H(require("fs")),
  L = H(require("path")),
  We = require("child_process"),
  Xt = H(require("os")),
  Jt = 300 * 1e3,
  Lr = "3.11";
function Ue() {
  let d, l;
  return {
    promise: new Promise((t, r) => {
      ((d = t), (l = r));
    }),
    resolve: d,
    reject: l,
  };
}
function Or(d) {
  let l = d.match(/Python\s+(\d+\.\d+(?:\.\d+)?)/);
  if (l) return l[1];
  let e = d.match(/Python\s+(\d+\.\d+)/);
  return e ? e[1] + ".0" : null;
}
function Qt(d, l) {
  var r, n;
  let e = d.split(".").map(Number),
    t = l.split(".").map(Number);
  for (let s = 0; s < Math.max(e.length, t.length); s++) {
    let a = (r = e[s]) != null ? r : 0,
      o = (n = t[s]) != null ? n : 0;
    if (a !== o) return a - o;
  }
  return 0;
}
function Mr(d, l) {
  return Qt(d, l) >= 0;
}
function Ir() {
  var d;
  return (
    process.env.FLATPAK_ID !== void 0 ||
    ((d = process.env.XDG_DATA_DIRS) != null ? d : "").includes("flatpak") ||
    !1
  );
}
function Br() {
  return process.env.SNAP !== void 0 || process.env.SNAP_NAME !== void 0 || !1;
}
function Yt(d, l) {
  var t;
  return `${(t = { win32: "windows", darwin: "macos", linux: "linux" }[d]) != null ? t : d}-${l}`;
}
function fe(d) {
  return d.state !== "ready" || !d.pythonPath
    ? null
    : { command: d.pythonPath, args: [] };
}
var _e = class {
  constructor(l) {
    this._cache = null;
    this._cacheTime = 0;
    var r, n, s, a, o, c, p, u, _, f, h;
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
        (this.rootDir = L.dirname(l.runtimeDir)),
        (this.pluginVersion =
          (c = (o = l.pluginVersion) != null ? o : l.version) != null
            ? c
            : "0.0.0"));
    else {
      let g = Xt.homedir();
      ((this.rootDir = L.join(g, ".paperforge", "runtime")),
        (this.runtimeDir = L.join(this.rootDir, Yt(e, t))),
        (this.pluginVersion =
          (u = (p = l.version) != null ? p : l.pluginVersion) != null
            ? u
            : "0.0.0"));
    }
    ((this.pointerPath = L.join(this.rootDir, "active-runtime.json")),
      (this._fs = (_ = l.fs) != null ? _ : gt),
      (this._execFile = (f = l.execFile) != null ? f : We.execFile),
      (this._execFileSync =
        (h = l.execFileSync) != null ? h : We.execFileSync));
  }
  current() {
    return this._cache
      ? Date.now() - this._cacheTime > Jt
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
      let o = Date.now() - this._cacheTime > Jt;
      if (!o && this._cache.state === "ready")
        return { ...this._cache, stale: !1 };
      if (o && l != null && l.allowStale) return { ...this._cache, stale: !0 };
    }
    let e = null,
      t = null,
      r = null,
      n = null,
      s = [];
    try {
      let o = this._fs.readFileSync(this.pointerPath, "utf-8"),
        c = JSON.parse(o);
      e = typeof c.version == "string" ? c.version : null;
      let p = typeof c.pythonPath == "string" ? c.pythonPath : null;
      ((t = p ? L.resolve(L.dirname(this.pointerPath), p) : null),
        (r = typeof c.previousVersion == "string" ? c.previousVersion : null),
        (n =
          typeof c.previousPythonPath == "string"
            ? c.previousPythonPath
            : null),
        (s = Array.isArray(c.warnings) ? c.warnings : []));
    } catch (o) {
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
      let o = await this._probe(t),
        c = [...s];
      return this._setCache({
        state: "ready",
        pythonPath: t,
        version: (a = o.version) != null ? a : e,
        source: "venv",
        error: null,
        lastVerifiedAt: new Date().toISOString(),
        stale: !1,
        warnings: c,
        previousVersion: r,
        previousPythonPath: n,
      });
    } catch (o) {
      let c = o instanceof Error ? o.message : String(o);
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
    var y, v;
    let e =
        (y = l == null ? void 0 : l.version) != null ? y : this.pluginVersion,
      t = (v = l == null ? void 0 : l.force) != null ? v : !1,
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
      if (Ir() || Br())
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
      let E = Yt(this.osPlatform, this.osArch),
        w = this.osPlatform === "darwin",
        b = ["macos-x64", "macos-arm64"],
        x = ["windows-x64", "linux-x64"];
      return w && b.includes(E)
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
    if (!Mr(n.version, Lr))
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
          w = JSON.parse(E),
          b = typeof w.version == "string" ? w.version : null;
        m = b !== null && b !== e;
      } catch (E) {}
      if (m) {
        let E = L.join(this.runtimeDir, `v${e}`),
          w = L.join(E, "venv"),
          b =
            this.osPlatform === "win32"
              ? L.join(w, "Scripts", "python.exe")
              : L.join(w, "bin", "python");
        try {
          await this._probe(b, r);
        } catch (O) {
          if (O instanceof Error && O.name === "AbortError")
            return this._abortedHealth();
          let D = O instanceof Error ? O.message : String(O);
          return this._setCache({
            state: "needs_repair",
            pythonPath: b,
            version: e,
            source: "venv",
            error: {
              code: "RETAINED_SLOT_PROBE_FAILED",
              message: `Retained slot v${e} failed verification: ${D}`,
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
          k = null;
        try {
          let O = this._fs.readFileSync(this.pointerPath, "utf-8"),
            D = JSON.parse(O);
          ((x = typeof D.version == "string" ? D.version : null),
            (k = typeof D.pythonPath == "string" ? D.pythonPath : null));
        } catch (O) {}
        let S = L.dirname(this.pointerPath);
        this._fs.existsSync(S) || this._fs.mkdirSync(S, { recursive: !0 });
        let R = L.relative(L.dirname(this.pointerPath), b),
          V = JSON.stringify(
            {
              schema_version: 1,
              version: e,
              pythonPath: R,
              activatedAt: new Date().toISOString(),
              previousVersion: x,
              previousPythonPath: k,
            },
            null,
            2
          ),
          M = this.pointerPath + ".tmp";
        (this._fs.writeFileSync(M, V, "utf-8"),
          this._fs.renameSync(M, this.pointerPath));
        let I = {
          state: "ready",
          pythonPath: b,
          version: e,
          source: "venv",
          error: null,
          lastVerifiedAt: new Date().toISOString(),
          stale: !1,
          warnings: [],
          previousVersion: x,
          previousPythonPath: k,
        };
        return (
          (this._cache = I),
          (this._cacheTime = Date.now()),
          this._cleanupOldSlots(e),
          I
        );
      }
    }
    if (r != null && r.aborted) return this._abortedHealth();
    let s = t
        ? L.join(this.runtimeDir, `v${e}_build2`)
        : L.join(this.runtimeDir, `v${e}`),
      a = L.join(s, "venv"),
      o =
        this.osPlatform === "win32"
          ? L.join(a, "Scripts", "python.exe")
          : L.join(a, "bin", "python");
    try {
      this._fs.mkdirSync(s, { recursive: !0 });
      let { promise: m, reject: E, resolve: w } = Ue();
      (this._execFile(
        n.path,
        ["-m", "venv", a],
        { timeout: 6e4, signal: r },
        (b) => {
          b ? E(b) : w();
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
      let { promise: m, reject: E, resolve: w } = Ue();
      (this._execFile(
        o,
        ["-m", "pip", "install", `paperforge==${e}`],
        { timeout: 12e4, signal: r },
        (b) => {
          b ? E(b) : w();
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
      let { promise: m, reject: E, resolve: w } = Ue();
      (this._execFile(
        o,
        ["-I", "-c", "import paperforge; print(paperforge.__version__)"],
        { timeout: 3e4, signal: r },
        (b) => {
          b ? E(b) : w();
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
    let u = L.dirname(this.pointerPath);
    this._fs.existsSync(u) || this._fs.mkdirSync(u, { recursive: !0 });
    let _ = L.relative(L.dirname(this.pointerPath), o),
      f = JSON.stringify(
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
    (this._fs.writeFileSync(h, f, "utf-8"),
      this._fs.renameSync(h, this.pointerPath));
    let g = {
      state: "ready",
      pythonPath: o,
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
      (this._cache = g),
      (this._cacheTime = Date.now()),
      this._cleanupOldSlots(e),
      g
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
    let e = L.join(this.runtimeDir, `v${l}`);
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
          r = Or(t);
        if (r) return { path: e.path, version: r };
      } catch (t) {}
    throw new Error("No Python 3.11+ found on system");
  }
  _probe(l, e) {
    let { promise: t, resolve: r, reject: n } = Ue();
    return (
      this._execFile(
        l,
        ["-I", "-c", "import paperforge; print(paperforge.__version__)"],
        { timeout: 3e4, signal: e },
        (s, a) => {
          if (s) n(s);
          else {
            let o = (a != null ? a : "").trim() || null;
            r({ version: o });
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
        .sort((n, s) => Qt(s.version, n.version));
      for (let n = e; n < r.length; n++)
        this._fs.rmSync(L.join(this.runtimeDir, r[n].name), {
          recursive: !0,
          force: !0,
        });
    } catch (t) {}
  }
};
function er(d, l) {
  return !l || !l.trim()
    ? { blocked: !0, reason: "zotero" }
    : d
      ? { blocked: !1 }
      : { blocked: !0, reason: "ocr" };
}
var yt = class extends Z.Modal {
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
      i("orphan_delete_selected").replace("{count}", String(e.length))
    ),
      this._selectAllBtn.setText(
        e.length === this.orphans.length
          ? i("orphan_deselect_all")
          : i("orphan_select_all")
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
        text: i("orphan_title").replace("{count}", String(this.orphans.length)),
      }),
      e.createEl("p", { cls: "paperforge-modal-desc", text: i("orphan_desc") }),
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
        o = a.createEl("div", { cls: "paperforge-orphan-header" });
      o.createEl("span", {
        cls: "paperforge-orphan-key",
        text: n.citation_key || n.key,
      });
      let c = o.createEl("span", { cls: "paperforge-orphan-tags" });
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
          text: i("orphan_explain"),
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
          new Z.Notice(i("orphan_none_selected"));
          return;
        }
        if (
          (this._countEl.setText("Deleting..."),
          this._countEl.setAttr("disabled", ""),
          this._selectAllBtn.setAttr("disabled", ""),
          !this.py || !this.py.path)
        ) {
          (new Z.Notice("PaperForge: Python not found"), this.close());
          return;
        }
        let s = n.map((a) => a.key);
        (0, Pe.execFile)(
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
          (a, o) => {
            if (a) {
              (new Z.Notice("PaperForge: prune failed"), this.close());
              return;
            }
            try {
              let c = JSON.parse(o),
                p = (c.data && c.data.deleted) || [];
              new Z.Notice("Deleted " + p.length + " orphan workspace(s)");
            } catch (c) {
              new Z.Notice("PaperForge: prune done");
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
function Je(d, l, e) {
  console.log("[PF] checkOrphanState called");
  try {
    let r = ae(e).orphanStatePath;
    if (!ne.existsSync(r)) {
      console.log("[PF] orphan file NOT FOUND");
      return;
    }
    console.log("[PF] orphan file FOUND");
    let n = ne.readFileSync(r, "utf-8"),
      a = JSON.parse(n),
      o = { path: "python", extraArgs: [], source: "auto-detected" };
    (console.log("[PF] py.path:", o ? o.path : "null"),
      new yt(d, a, e, o).open(),
      ne.unlinkSync(r),
      console.log("[PF] orphan file cleaned"));
  } catch (t) {
    console.log("[PF] checkOrphanState exception:", t.message || t);
  }
}
var Ce = class extends Z.Modal {
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
      t = new _e({
        runtimeDir: mt.join(e, ".paperforge-test-venv"),
        pluginVersion: this.plugin.manifest.version,
        osPlatform: process.platform,
        osArch: process.arch,
        fs: ne,
        execFile: Pe.execFile,
        execFileSync: require("child_process").execFileSync,
      }),
      r = fe(t.current());
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
        i("wizard_step1"),
        i("wizard_step2"),
        i("wizard_step3"),
        i("wizard_step4"),
        i("wizard_step5"),
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
        .createEl("button", { cls: "paperforge-step-btn", text: i("nav_prev") })
        .addEventListener("click", () => {
          (this._step--, (this._showSkipConfirm = !1), this._render());
        }),
      this._step < 5
        ? e
            .createEl("button", {
              cls: "paperforge-step-btn mod-cta",
              text: i("nav_next"),
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
              text: i("nav_close"),
            })
            .addEventListener("click", () => this.close()));
  }
  _validateStep3() {
    let e = this.plugin.settings,
      t = er(this._apiKeyValidated, e.zotero_data_dir);
    if (t.reason === "ocr") return t;
    let r = (e.zotero_data_dir || "").trim();
    if (!r)
      return (
        new Z.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u4E3A\u5FC5\u586B\u9879\uFF0C\u8BF7\u586B\u5199\u8DEF\u5F84"
        ),
        { blocked: !0, reason: "zotero" }
      );
    if (!ne.existsSync(r))
      return (
        new Z.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u8DEF\u5F84\u4E0D\u5B58\u5728"
        ),
        { blocked: !0, reason: "zotero" }
      );
    if (!ne.statSync(r).isDirectory())
      return (
        new Z.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u8DEF\u5F84\u4E0D\u662F\u4E00\u4E2A\u76EE\u5F55"
        ),
        { blocked: !0, reason: "zotero" }
      );
    let n = mt.join(r, "storage");
    return !ne.existsSync(n) || !ne.statSync(n).isDirectory()
      ? (new Z.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u4E2D\u672A\u627E\u5230 storage/ \u5B50\u76EE\u5F55"
        ),
        { blocked: !0, reason: "zotero" })
      : { blocked: !1 };
  }
  _stepOverview(e) {
    (e.createEl("h2", { text: i("wizard_title") }),
      e.createEl("p", { text: i("wizard_intro") }));
    let t = this.plugin.settings,
      r = this.app.vault.adapter.basePath,
      n = e.createEl("div", { cls: "paperforge-dir-tree" }),
      s = n.createEl("div", { cls: "paperforge-dir-node root" });
    s.textContent = `\u{1F4C1} Vault (${r})`;
    let a = n.createEl("div", { cls: "paperforge-dir-children" }),
      o = a.createEl("div", { cls: "paperforge-dir-node folder" });
    ((o.textContent = `\u{1F4C1} ${t.resources_dir || "Resources"}/ \u2014 \u6587\u732E\u5361\u7247\u76EE\u5F55\uFF08Base \u6570\u636E\u6765\u6E90\uFF09`),
      o
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
        text: i("wizard_preview"),
        cls: "paperforge-modal-hint",
      }),
      e.createEl("p", {
        text: i("wizard_safety"),
        cls: "paperforge-modal-hint",
      }));
    let p = e.createEl("div", { cls: "paperforge-summary" }),
      u = [
        {
          label: i("dir_resources"),
          val: `${r}/${t.resources_dir || "Resources"}`,
        },
        {
          label: i("dir_notes"),
          val: `${r}/${t.resources_dir || "Resources"}/${t.literature_dir || "Literature"}`,
        },
        { label: i("dir_base"), val: `${r}/${t.base_dir || "Bases"}` },
        { label: i("dir_system"), val: `${r}/${t.system_dir || "System"}` },
      ];
    for (let _ of u) {
      let f = p.createEl("div", { cls: "paperforge-summary-row" });
      (f.createEl("span", { cls: "paperforge-summary-label", text: _.label }),
        f.createEl("span", { cls: "paperforge-summary-value", text: _.val }));
    }
  }
  _stepDirectories(e) {
    (e.createEl("h2", { text: i("wizard_step2") }),
      e.createEl("p", { text: i("wizard_intro") }));
    let t = this.plugin.settings,
      r = this.app.vault.adapter.basePath;
    (this._modalField(e, i("dir_vault"), r, !0),
      e.createEl("p", {
        text: i("wizard_dir_hint"),
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
        text: i("wizard_dir_sub_hint"),
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
        text: i("wizard_sys_hint"),
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
        text: i("wizard_safety"),
        cls: "paperforge-modal-hint",
      }));
    let n = e.createEl("div", { cls: "paperforge-summary" }),
      s = [
        { label: i("dir_resources"), val: `${r}/${t.resources_dir || ""}` },
        {
          label: i("dir_notes"),
          val: `${r}/${t.resources_dir || ""}/${t.literature_dir || ""}`,
        },
        { label: i("dir_system"), val: `${r}/${t.system_dir || ""}` },
        { label: i("dir_base"), val: `${r}/${t.base_dir || ""}` },
      ];
    for (let a of s) {
      let o = n.createEl("div", { cls: "paperforge-summary-row" });
      (o.createEl("span", { cls: "paperforge-summary-label", text: a.label }),
        o.createEl("span", { cls: "paperforge-summary-value", text: a.val }));
    }
  }
  _stepKeys(e) {
    if (
      (e.createEl("h2", { text: i("wizard_step3") }), this._showSkipConfirm)
    ) {
      this._renderSkipConfirm(e);
      return;
    }
    let t = this.plugin.settings;
    e.createEl("p", {
      text: i("wizard_agent_hint"),
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
      text: i("label_agent"),
    });
    let s = n.createEl("select", { cls: "paperforge-modal-select" });
    for (let f of r) {
      let h = s.createEl("option", { text: f.name, attr: { value: f.key } });
      f.key === (t.agent_platform || "opencode") && (h.selected = !0);
    }
    (s.addEventListener("change", () => {
      ((t.agent_platform = s.value),
        this._pendingSave && clearTimeout(this._pendingSave),
        (this._pendingSave = setTimeout(() => {
          (this.plugin.saveSettings(), (this._pendingSave = null));
        }, 500)));
    }),
      e.createEl("p", {
        text: i("wizard_keys_hint"),
        cls: "paperforge-modal-hint",
      }));
    let a = e.createEl("div", { cls: "paperforge-modal-field" });
    a.createEl("label", {
      cls: "paperforge-modal-label",
      text: i("field_paddleocr"),
    });
    let o = a.createEl("input", {
        cls: "paperforge-modal-input",
        attr: { type: "password", placeholder: "API Key" },
      }),
      c = this.plugin.settings._paddleocr_configured || !1;
    ((o.placeholder = c
      ? "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022 (stored securely)"
      : "API Key"),
      (o.value = ""),
      (this._apiKeyValidated = !1),
      (this._apiKeyStatus = a.createEl("span", {
        cls: "paperforge-apikey-status",
        text: "",
      })));
    let p = a.createEl("button", {
      cls: "paperforge-step-btn",
      text: "\u9A8C\u8BC1",
    });
    (p.addEventListener("click", () => this._validateApiKey(o.value, p)),
      o.addEventListener("input", () => {
        ((this._apiKeyValidated = !1),
          (this._apiKeyStatus.textContent = ""),
          (this._apiKeyStatus.className = "paperforge-apikey-status"));
      }),
      this._pendingSave && clearTimeout(this._pendingSave),
      (this._pendingSave = setTimeout(() => {
        (this.plugin.saveSettings(), (this._pendingSave = null));
      }, 500)),
      e.createEl("p", {
        text: i("wizard_api_hint_skip"),
        cls: "paperforge-modal-hint",
      }));
    let u = e.createEl("div", { cls: "paperforge-modal-field" });
    u.createEl("label", {
      cls: "paperforge-modal-label",
      text: i("field_zotero_data"),
    });
    let _ = u.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text", placeholder: i("field_zotero_placeholder") },
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
      s = tr.request(n, async (a) => {
        ((t.disabled = !1), (t.textContent = "\u9A8C\u8BC1"));
        let o = "";
        (a.on("data", (c) => (o += c)),
          a.on("end", async () => {
            var c, p;
            try {
              let u = JSON.parse(o);
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
                } catch (f) {}
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
      text: i("wizard_skip_ocr_desc"),
      cls: "paperforge-modal-desc",
    });
    let t = e.createEl("div", { cls: "paperforge-modal-actions" });
    (t
      .createEl("button", {
        cls: "paperforge-step-btn mod-cta",
        text: i("wizard_skip_ocr_continue"),
      })
      .addEventListener("click", () => {
        ((this._showSkipConfirm = !1), this._step++, this._render());
      }),
      t
        .createEl("button", {
          cls: "paperforge-step-btn",
          text: i("wizard_skip_ocr_back"),
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
    let o = a.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text", placeholder: s || "" },
    });
    o.value = n;
    let c = this.plugin.settings;
    o.addEventListener("input", () => {
      ((c[r] = o.value),
        this._pendingSave && clearTimeout(this._pendingSave),
        (this._pendingSave = setTimeout(() => {
          (this.plugin.saveSettings(), (this._pendingSave = null));
        }, 500)));
    });
  }
  _modalSecret(e, t, r, n, s) {
    let a = e.createEl("div", { cls: "paperforge-modal-field" });
    a.createEl("label", { cls: "paperforge-modal-label", text: t });
    let o = a.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "password", placeholder: s || "" },
    });
    o.value = n;
    let c = this.plugin.settings;
    o.addEventListener("input", () => {
      ((c[r] = o.value),
        this._pendingSave && clearTimeout(this._pendingSave),
        (this._pendingSave = setTimeout(() => {
          (this.plugin.saveSettings(), (this._pendingSave = null));
        }, 500)));
    });
  }
  _stepInstall(e) {
    (e.createEl("h2", { text: i("wizard_step4") }),
      (this._installLog = e.createEl("div", {
        cls: "paperforge-install-log",
      })));
    let t = e.createEl("button", {
      cls: "paperforge-step-btn mod-cta",
      text: i("install_btn"),
    });
    t.addEventListener("click", () => this._runInstall(t));
  }
  async _runInstall(e) {
    var a, o, c, p, u, _;
    ((e.disabled = !0),
      (e.textContent = i("install_btn_running")),
      this._installLog.setText(
        i("install_validating") +
          `
`
      ),
      this._log(i("install_validating")));
    let t = this.plugin.settings,
      r = this._validate();
    if (r.length > 0) {
      (this._log(i("validate_fail") + ":"),
        r.forEach((f) => this._log("  \u2717 " + f)),
        (e.disabled = !1),
        (e.textContent = i("install_btn_retry")));
      return;
    }
    let n = (f, h = {}) =>
        new Promise((g, y) => {
          let { path: v, args: m = [] } = this._resolvePython(),
            E = (0, Pe.spawn)(v, [...m, ...f], {
              cwd: t.vault_path.trim(),
              env: pe(),
              timeout: 12e4,
              ...h,
            }),
            w = "",
            b = "";
          (E.stdout.on("data", (x) => {
            let k = x.toString("utf-8");
            ((w += k), h.logStdout && this._processSetupOutput(k));
          }),
            E.stderr.on("data", (x) => {
              let k = x.toString("utf-8");
              ((b += k), this._log("[stderr] " + k.trim()));
            }),
            E.on("close", (x) => {
              x === 0
                ? g({ stdout: w, stderr: b })
                : y(new Error(b.trim() || w.trim() || `exit code ${x}`));
            }),
            E.on("error", (x) => y(x)));
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
      let f = !0;
      try {
        await n(["-c", "import paperforge"]);
      } catch (h) {
        f = !1;
      }
      if (!f) {
        this._log(i("install_bootstrapping"));
        let h = this.plugin.manifest.version;
        this._log(`[install] Trying PyPI: pip install paperforge==${h}`);
        let g = ["-m", "pip", "install", "--upgrade"];
        (process.platform !== "win32" && g.push("--user"),
          g.push(`paperforge==${h}`));
        try {
          await n(g, { logStdout: !0 });
        } catch (y) {
          (this._log(
            `[install] PyPI failed, falling back to git: git+https://...@v${h}`
          ),
            console.warn(
              "[PaperForge] PyPI install failed, falling back to git:",
              (a = y.message) == null ? void 0 : a.slice(0, 200)
            ));
          let v = ["-m", "pip", "install", "--upgrade"];
          (process.platform !== "win32" && v.push("--user"),
            v.push(`git+https://github.com/LLLin000/PaperForge.git@v${h}`),
            await n(v, { logStdout: !0 }));
        }
      }
      (await n(s, { logStdout: !0, env: pe() }),
        this._log(i("install_complete")),
        await this.plugin.saveSettings(),
        this._onComplete && this._onComplete(),
        setTimeout(() => {
          ((this._step = 5), this._render());
        }, 800));
    } catch (f) {
      console.error("PaperForge setup failed:", f.message);
      let h = this._formatSetupError(f.message);
      this._log(i("install_failed") + h);
      let g =
        (o = this._installLog.parentElement) == null
          ? void 0
          : o.createEl("button", {
              cls: "paperforge-copy-diag-btn",
              text: i("error_copy_diagnostic") || "Copy diagnostic",
            });
      if (g) {
        let y = f.message,
          v =
            ((p = (c = this.plugin) == null ? void 0 : c.settings) == null
              ? void 0
              : p.python_path) || "auto",
          m =
            ((_ = (u = this.plugin) == null ? void 0 : u.manifest) == null
              ? void 0
              : _.version) || "?",
          E = process.platform + " " + process.arch,
          w,
          b;
        try {
          w = ut() || "(not found)";
        } catch (R) {
          w = "(error)";
        }
        try {
          b = this._resolvePython();
        } catch (R) {
          b = null;
        }
        let x = (process.env.PATH || "").length,
          k = (process.env.PATH || "").toLowerCase().includes("git"),
          S = [
            "[PaperForge Diagnostic]",
            "Category: " + h,
            "Plugin version: " + m,
            "Python: " + v,
            "Resolved Python: " + ((b == null ? void 0 : b.path) || "?"),
            "OS: " + E,
            "Vault path: " + (t.vault_path || "?"),
            "--- Git ---",
            "Git dir (resolved): " + w,
            "PATH length: " + x + " chars",
            "PATH contains git: " + k,
            "--- Raw error ---",
            y.slice(0, 2e3),
          ].join(`
`);
        g.addEventListener("click", () => {
          navigator.clipboard
            .writeText(S)
            .then(() => {
              (g.setText(i("error_copied") || "Copied!"),
                setTimeout(() => {
                  g.setText(i("error_copy_diagnostic") || "Copy diagnostic");
                }, 3e3));
            })
            .catch(() => {
              new Z.Notice("[!!] Clipboard write failed", 6e3);
            });
        });
      }
      ((e.disabled = !1), (e.textContent = i("install_btn_retry")));
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
      (!t.vault_path || !t.vault_path.trim()) && e.push(i("validate_vault")),
      (!t.resources_dir || !t.resources_dir.trim()) &&
        e.push(i("validate_resources")),
      (!t.literature_dir || !t.literature_dir.trim()) &&
        e.push(i("validate_notes")),
      (!t.base_dir || !t.base_dir.trim()) && e.push(i("validate_base")),
      this.plugin.settings._paddleocr_configured ||
        !1 ||
        this._log("  ! " + i("validate_key") + " " + i("optional_later")),
      (!t.zotero_data_dir || !t.zotero_data_dir.trim()) &&
        this._log("  ! " + i("validate_zotero") + " " + i("optional_later")),
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
    e.createEl("h2", { text: i("complete_title") });
    let t = e.createEl("div", { cls: "paperforge-summary" });
    t.createEl("div", {
      cls: "paperforge-summary-title",
      text: i("complete_summary"),
    });
    let r = this.plugin.settings,
      n = this.app.vault.adapter.basePath,
      s = [
        { label: i("dir_vault"), val: n },
        { label: i("dir_resources"), val: `${n}/${r.resources_dir}` },
        {
          label: i("dir_notes"),
          val: `${n}/${r.resources_dir}/${r.literature_dir}`,
        },
        { label: i("dir_base"), val: `${n}/${r.base_dir}` },
        { label: i("dir_system"), val: `${n}/${r.system_dir}` },
        {
          label: "API Key",
          val: this.plugin.settings._paddleocr_configured
            ? i("api_key_set")
            : i("api_key_missing"),
        },
        {
          label: i("field_zotero_data"),
          val: r.zotero_data_dir || i("not_set"),
        },
      ];
    for (let u of s) {
      let _ = t.createEl("div", { cls: "paperforge-summary-row" });
      (_.createEl("span", { cls: "paperforge-summary-label", text: u.label }),
        _.createEl("span", { cls: "paperforge-summary-value", text: u.val }));
    }
    let a = t.createEl("div", { cls: "paperforge-summary-row" });
    a.createEl("span", { cls: "paperforge-summary-label", text: "PaperForge" });
    let o = a.createEl("span", {
      cls: "paperforge-summary-value",
      text: "\u2014",
    });
    {
      let u = n,
        { path: _, args: f = [] } = this._resolvePython();
      (0, Pe.execFile)(
        _,
        [...f, "-c", "import paperforge; print(paperforge.__version__)"],
        { cwd: u, timeout: 1e4 },
        (h, g) => {
          !h && g && (o.textContent = "v" + g.trim());
        }
      );
    }
    for (let u of s) {
      let _ = t.createEl("div", { cls: "paperforge-summary-row" });
      (_.createEl("span", { cls: "paperforge-summary-label", text: u.label }),
        _.createEl("span", { cls: "paperforge-summary-value", text: u.val }));
    }
    e.createEl("h3", { text: i("complete_next") });
    let c = e.createEl("div", { cls: "paperforge-nextsteps" }),
      p = [
        [i("complete_step4"), i("complete_step4_desc")],
        [
          "",
          `${i("complete_export_path")} ${n}/${r.system_dir}/PaperForge/exports/`,
        ],
        [i("complete_step1"), i("complete_step1_desc")],
        [i("complete_step2"), i("complete_step2_desc")],
        [i("complete_step3"), i("complete_step3_desc")],
      ];
    for (let [u, _] of p) {
      let f = c.createEl("div", { cls: "paperforge-nextstep-item" });
      (u && f.createEl("strong", { text: u }), f.createEl("span", { text: _ }));
    }
  }
};
function rr(d, l) {
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
var Ze = class extends Z.Modal {
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
        let o = t.parentElement;
        if (o)
          for (let c of Array.from(o.children))
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
            i("maintenance_confirm_cancel") ||
            "Cancel",
        });
      (s.addEventListener("click", () => this.close()),
        n
          .createEl("button", {
            cls: "mod-warning",
            text:
              this._config.confirmLabel ||
              i("maintenance_confirm_ok") ||
              "Proceed",
          })
          .addEventListener("click", () => {
            (this._onConfirm && this._onConfirm(), this.close());
          }),
        (this._boundKeydown = (o) => rr(e, o)),
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
  Nr = [
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
function Ne(d) {
  let l = {},
    e = d;
  for (let { pattern: t, label: r, class_: n } of Nr) {
    let s = 0;
    ((e = e.replace(t, () => (s++, "[REDACTED]"))),
      s > 0 &&
        (l[n] || (l[n] = { label: r, class_: n, count: 0 }),
        (l[n].count += s)));
  }
  return { clean: e, redactions: Object.values(l) };
}
function nr(d, l, e, t) {
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
var Ge = class extends Z.Modal {
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
      let g = t.parentElement;
      if (g)
        for (let y of Array.from(g.children))
          y !== t &&
            !y.hasAttribute("inert") &&
            (y.setAttribute("inert", ""), this._inertedEls.push(y));
    }
    (e.createEl("h2", {
      text: i("maintenance_issue_draft_title") || "OCR Issue Draft",
    }),
      e.createEl("p", {
        cls: "paperforge-issue-draft-desc",
        text:
          i("maintenance_issue_draft_preview") ||
          "Review the issue draft below before opening GitHub.",
      }));
    let r = e.createEl("div", { cls: "paperforge-issue-draft-field" });
    r.createEl("label", { text: "Title" });
    let n = Ne(this._draft.title).clean;
    this._titleInput = r.createEl("input", {
      cls: "paperforge-issue-draft-input",
      attr: { type: "text", value: n },
    });
    let s = e.createEl("div", { cls: "paperforge-issue-draft-field" });
    s.createEl("label", { text: "Body" });
    let a = Ne(this._draft.body).clean;
    this._bodyTextarea = s.createEl("textarea", {
      cls: "paperforge-issue-draft-textarea",
      attr: { rows: "12" },
      text: a,
    });
    let { redactions: o } = Ne(
        this._draft.title +
          `
` +
          this._draft.body
      ),
      c = e.createEl("div", { cls: "paperforge-issue-draft-preview" }),
      p = c.createEl("div", { cls: "paperforge-issue-draft-included" });
    (p.createEl("span", {
      cls: "paperforge-issue-draft-preview-label",
      text: (i("maintenance_issue_draft_included") || "Included") + ": ",
    }),
      p.createEl("span", {
        text: `Title, Body, Labels (${this._draft.labels.join(", ")})`,
      }));
    let u = c.createEl("div", { cls: "paperforge-issue-draft-redacted" });
    (u.createEl("span", {
      cls: "paperforge-issue-draft-preview-label",
      text: (i("maintenance_issue_draft_redacted") || "Redacted") + ": ",
    }),
      u.createEl("span", {
        text:
          "Credentials, vault/Zotero paths, paper titles, paper content are excluded" +
          (o.length > 0
            ? " (" + o.map((g) => `${g.count} ${g.label}`).join(", ") + ")"
            : ""),
      }));
    let _ = e.createEl("div", { cls: "paperforge-issue-draft-actions" });
    (_.createEl("button", {
      text: i("maintenance_confirm_cancel") || "Cancel",
    }).addEventListener("click", () => this.close()),
      _.createEl("button", {
        cls: "mod-cta",
        text: i("maintenance_issue_draft_open_github") || "Open GitHub Issue",
      }).addEventListener("click", () => {
        let g = encodeURIComponent(Ne(this._titleInput.value).clean),
          y = encodeURIComponent(Ne(this._bodyTextarea.value).clean),
          v = encodeURIComponent(this._draft.labels.join(",")),
          m = `${this._githubUrl}?title=${g}&body=${y}&labels=${v}`;
        window.open(m, "_blank", "noopener,noreferrer");
      }),
      (this._boundKeydown = (g) => rr(e, g)),
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
function bt(d, l, e) {
  return !d ||
    typeof d != "object" ||
    !Object.prototype.hasOwnProperty.call(d, l)
    ? !!e
    : !!d[l];
}
function ar(d, l, e) {
  let t = !bt(d, l, e);
  return (d && typeof d == "object" && (d[l] = t), t);
}
var Hr = ["EMBED", "OCR_REBUILD", "OCR_REDO"];
function Ye(d, l) {
  var s, a;
  let t = (l + d).split(`
`),
    r = (s = t.pop()) != null ? s : "",
    n = [];
  for (let o of t)
    for (let c of Hr) {
      let p = c.length;
      if (o.startsWith(c + "_START:")) {
        let u = parseInt(o.slice(p + 7), 10) || 0;
        n.push({ prefix: c, event: "START", total: u });
        break;
      }
      if (o.startsWith(c + "_PROGRESS:")) {
        let _ = o.slice(p + 10).split(":");
        n.push({
          prefix: c,
          event: "PROGRESS",
          current: parseInt(_[0], 10) || 0,
          total: parseInt(_[1], 10) || 0,
          key: (a = _[2]) != null ? a : "",
        });
        break;
      }
      if (o === c + "_DONE" || o.startsWith(c + "_DONE:")) {
        n.push({ prefix: c, event: "DONE" });
        break;
      }
    }
  return { events: n, buffer: r };
}
function sr(d) {
  return { app: { secretStorage: d.secretStorage }, saveData: async () => {} };
}
var Re = class Re extends C.PluginSettingTab {
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
    this._agentPlatformDraft = null;
    this.plugin = t;
  }
  _getOverviewModules() {
    return [
      { id: "installation", label: i("cc_module_foundation") || "Foundation" },
      { id: "library", label: i("cc_module_library") || "Library" },
      { id: "ocr", label: i("cc_module_ocr") || "OCR" },
      { id: "memory", label: i("cc_module_memory") || "Smart Retrieval" },
      { id: "agent", label: i("cc_module_agent") || "Agent Integration" },
    ];
  }
  _getUserModuleName(e) {
    let t =
      "cc_module_" +
      (e === "installation" ? "foundation" : e === "memory" ? "memory" : e);
    return i(t) || e.charAt(0).toUpperCase() + e.slice(1);
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
        o = t
          .map((c) => (c === "paddleocr_api_key" ? "OCR" : "Smart Retrieval"))
          .join(", ");
      (a.createEl("strong", { text: i("migration_banner_title") }),
        a.createEl("p", {
          text: i("migration_banner_body").replace("{modules}", o),
        }),
        a.createEl("p", {
          text: i("migration_banner_next"),
          cls: "paperforge-manual-links",
        }));
    }
    let r = e.createDiv({ cls: "paperforge-settings-tabs" }),
      n = [
        { id: "overview", label: i("tab_overview") || "Overview" },
        { id: "maintenance", label: i("tab_maintenance") || "Maintenance" },
        { id: "help", label: i("tab_help") || "Help" },
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
        } catch (o) {}
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
      e.createEl("h2", { text: i("header_title") || "PaperForge" }),
      e.createEl("p", { text: i("desc"), cls: "paperforge-settings-desc" }),
      this._renderControlCenter(e));
    for (let n of Me) {
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
            : new _e({ version: this.plugin.manifest.version })),
        this._managedRuntime);
  }
  _resolveRuntimeCommand(e) {
    let t = fe(this._ensureManagedRuntime().current());
    return t ? { path: t.command, args: [...t.args] } : null;
  }
  _renderInstallationDetail(e) {
    var o, c;
    this._renderModuleDetailShell(e, "installation");
    let t =
        (c = (o = this._capabilityState) == null ? void 0 : o.installation) !=
        null
          ? c
          : re("installation"),
      r = e.createDiv({ cls: "pf-module-body" });
    (r.createEl("h3", { text: i("md_foundation_overview") }),
      r.createEl("p", {
        text:
          t.user_state === "ready"
            ? i("md_foundation_ready")
            : this._getModuleConsequence("installation", t),
        cls:
          t.user_state === "ready"
            ? "pf-status-ok"
            : "setting-item-description",
      }));
    let n = r.createDiv({ cls: "pf-module-facts" }),
      s = n.createDiv({ cls: "pf-module-fact" });
    (s.createEl("span", { text: i("foundation_version") }),
      s.createEl("span", { text: this.plugin.manifest.version }));
    let a = n.createDiv({ cls: "pf-module-fact" });
    (a.createEl("span", { text: i("foundation_skills") }),
      a.createEl("span", {
        text: i("foundation_skills_ready"),
        cls: "pf-status-ok",
      }));
  }
  _renderSkillsList(e) {
    let t = {
        opencode: ".opencode/skills",
        claude: ".claude/skills",
        codex: ".codex/skills",
        cursor: ".cursor/skills",
        windsurf: ".windsurf/skills",
        github_copilot: ".github/skills",
        gemini: ".gemini/skills",
      },
      r = this._getVaultBasePath(),
      n = this.plugin.settings.agent_platform || "opencode";
    e.createEl("h3", { text: i("md_agent_skills") });
    let s = e.createEl("div", { cls: "paperforge-desc-box" });
    (s.setText(i("feat_skills_desc")),
      s.createEl("br"),
      s.createEl("span", { text: i("feat_skills_system") }));
    let a = G.join(r, t[n]),
      o = [],
      c = [];
    j.existsSync(a) &&
      j.readdirSync(a, { withFileTypes: !0 }).forEach((_) => {
        if (!_.isDirectory()) return;
        let f = G.join(a, _.name, "SKILL.md");
        if (!j.existsSync(f)) return;
        let h = j.readFileSync(f, "utf-8"),
          g = h.match(/^name:\s*(.+)$/m),
          y = h.split(`
`),
          v = y.findIndex((k) => /^description:/.test(k)),
          m = "";
        if (v >= 0) {
          let k = y[v].match(/^description:\s*(.+)$/);
          if (k && k[1] && k[1] !== ">" && k[1] !== "|-" && k[1] !== "|")
            m = k[1].trim();
          else {
            for (
              let S = v + 1;
              S < y.length && (/^\s{2,}/.test(y[S]) || y[S].trim() === "");
              S++
            )
              m += y[S].trim() + " ";
            m = m.trim();
          }
        }
        let E = h.match(/^source:\s*(.+)$/m),
          w = h.match(/^disable-model-invocation:\s*(.+)$/m),
          b = h.match(/^version:\s*(.+)$/m),
          x = {
            name: g ? g[1].trim() : _.name,
            desc: m,
            source: E ? E[1].trim() : "user",
            disabled: !!w && w[1].trim() === "true",
            version: b ? b[1].trim() : "",
            path: f,
            content: h,
            dirName: _.name,
          };
        x.source === "paperforge" ? o.push(x) : c.push(x);
      });
    let p = e.createEl("div", { cls: "paperforge-skills-box" }),
      u = (_, f, h) => {
        if (f.length === 0) return;
        let g = p.createEl("div", { cls: "paperforge-skills-group" }),
          y = g.createEl("div", { cls: "paperforge-skills-collapse-header" }),
          v = g.createEl("div", { cls: "paperforge-skills-collapse-content" }),
          m = y.createEl("span", {
            text: "\u25BC",
            cls: "paperforge-skills-arrow",
          });
        (y.createEl("h4", {
          text: `${_} (${f.length})`,
          cls: "paperforge-skills-subheader",
        }),
          f.forEach((b) => {
            let x = b.name + (b.version ? " v" + b.version : ""),
              k = h
                ? " [" + i("skills_system") + "]"
                : " [" + i("skills_user") + "]",
              S = b.desc || "",
              R = new C.Setting(v).setName(x + k).setDesc(S);
            ((R.settingEl.style.opacity = b.disabled ? "0.4" : "1"),
              R.addToggle((V) => {
                V.setValue(!b.disabled).onChange((M) => {
                  let I = !M,
                    D = b.content.match(/^disable-model-invocation:\s*(.+)$/m)
                      ? b.content.replace(
                          /^disable-model-invocation:\s*.+$/m,
                          `disable-model-invocation: ${I}`
                        )
                      : b.content.replace(
                          /^(---\r?\n)/,
                          `$1disable-model-invocation: ${I}
`
                        );
                  (j.writeFileSync(b.path, D, "utf-8"),
                    (b.disabled = I),
                    (b.content = D),
                    (R.settingEl.style.opacity = b.disabled ? "0.4" : "1"));
                });
              }));
          }));
        let E = h ? "system" : "user";
        ((this._skillsCollapsed[E] || !1) &&
          ((v.style.display = "none"), (m.style.transform = "rotate(-90deg)")),
          y.addEventListener("click", () => {
            (v.style.display !== "none"
              ? ((v.style.display = "none"),
                (m.style.transform = "rotate(-90deg)"))
              : ((v.style.display = ""), (m.style.transform = "rotate(0deg)")),
              (this._skillsCollapsed[E] = v.style.display === "none"));
          }));
      };
    (u(i("skills_system"), o, !0),
      u(i("skills_user"), c, !1),
      o.length === 0 &&
        c.length === 0 &&
        p.createEl("p", {
          text: i("skills_empty"),
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
    var o, c;
    this._renderModuleDetailShell(e, "library");
    let t =
        (c = (o = this._capabilityState) == null ? void 0 : o.library) != null
          ? c
          : re("library"),
      r = e.createDiv({ cls: "pf-module-body" });
    (r.createEl("h3", { text: i("md_library_connection") }),
      t.user_state === "ready"
        ? r.createEl("p", { text: i("md_library_ready"), cls: "pf-status-ok" })
        : t.user_state !== "checking" &&
          t.user_state !== "not_enabled" &&
          $e(r, {
            whatHappened:
              i("cc_module_library") +
              " \u2014 " +
              this._getUserStateLabel(t.user_state),
            impact: i("library_problem_impact"),
            nextStep: i("problem_use_action"),
            impactLabel: i("problem_impact"),
            nextLabel: i("problem_next"),
            copyLabel: i("problem_copy"),
            onCopyDiagnostic: () => this._buildAndCopyDiagnostic(),
          }));
    let n = r.createDiv({ cls: "pf-module-facts" }),
      s = n.createDiv({ cls: "pf-module-fact" });
    (s.createEl("span", { text: i("md_library_corpus") }),
      s.createEl("span", { text: i("metric_after_sync") }));
    let a = n.createDiv({ cls: "pf-module-fact" });
    (a.createEl("span", { text: i("md_library_last_sync") }),
      a.createEl("span", {
        text: this.plugin._lastSyncTime || i("metric_not_available"),
      }),
      r.createEl("h3", { text: i("md_configuration") }),
      Mt(r, {
        items: [
          {
            label: i("config_zotero_dir"),
            value:
              this.plugin.settings.zotero_data_dir ||
              i("config_not_configured"),
          },
        ],
        configuredLabel: i("config_configured"),
        notConfiguredLabel: i("config_not_configured"),
        onChangeLabel: i("config_change"),
        onChange: () => {
          new Ce(this.app, this.plugin, () => {
            (this.plugin.savePaperforgeJson({
              zotero_data_dir: this.plugin.settings.zotero_data_dir,
            }),
              this._probeModule("library"));
          }).open();
        },
      }));
  }
  _renderOcrDetail(e) {
    var s, a;
    this._renderModuleDetailShell(e, "ocr");
    let t =
        (a = (s = this._capabilityState) == null ? void 0 : s.ocr) != null
          ? a
          : re("ocr"),
      r = e.createDiv({ cls: "pf-module-body" });
    (r.createEl("h3", { text: i("md_ocr_status") }),
      t.user_state === "ready"
        ? r.createEl("p", { text: i("md_ocr_ready"), cls: "pf-status-ok" })
        : t.user_state !== "checking" &&
          t.user_state !== "not_enabled" &&
          $e(r, {
            whatHappened:
              i("cc_module_ocr") +
              " \u2014 " +
              this._getUserStateLabel(t.user_state),
            impact: i("ocr_problem_impact"),
            nextStep: i("problem_use_action"),
            impactLabel: i("problem_impact"),
            nextLabel: i("problem_next"),
            copyLabel: i("problem_copy"),
            onCopyDiagnostic: () => this._buildAndCopyDiagnostic(),
          }),
      W(r, {
        label: i("md_ocr_workspace"),
        onClick: () =>
          this.app.commands.executeCommandById(
            "paperforge:paperforge-status-panel"
          ),
      }));
    let n = this.plugin._ocrProcess;
    if (n) {
      let o = r.createDiv({ cls: "pf-detail-controls" });
      o.createEl("button", {
        cls: "pf-action-btn mod-warning",
        text: i("ocr_stop_batch"),
      }).addEventListener("click", () => {
        var u, _;
        (u = n.stdin) != null && u.write
          ? (n.stdin.write(`PAPERFORGE_STOP
`),
            (this.plugin._ocrWasStopped = !0))
          : (_ = n.kill) == null || _.call(n, "SIGINT");
      });
      let p = this.plugin._ocrProgress;
      p != null &&
        p.total &&
        o.createEl("span", {
          cls: "pf-detail-progress",
          text: i("ocr_progress")
            .replace("{current}", String(p.current))
            .replace("{total}", String(p.total)),
        });
    }
  }
  _renderAgentDetail(e) {
    var f;
    this._renderModuleDetailShell(e, "agent");
    let t = e.createDiv({ cls: "pf-module-body" });
    (t.createEl("h3", { text: i("md_agent_integration") }),
      t.createEl("p", {
        text: i("md_agent_placeholder"),
        cls: "setting-item-description",
      }));
    let r = {
        opencode: "OpenCode",
        claude: "Claude Code",
        codex: "Codex",
        cursor: "Cursor",
        windsurf: "Windsurf",
        github_copilot: "GitHub Copilot",
        gemini: "Gemini CLI",
      },
      n = {
        opencode: ".opencode/skills",
        claude: ".claude/skills",
        codex: ".codex/skills",
        cursor: ".cursor/skills",
        windsurf: ".windsurf/skills",
        github_copilot: ".github/skills",
        gemini: ".gemini/skills",
      },
      s = this.plugin.settings.agent_platform || "opencode",
      a = G.join(this._getVaultBasePath(), n[s]),
      o = j.existsSync(a),
      c = t.createDiv({ cls: "pf-module-facts" }),
      p = c.createDiv({ cls: "pf-module-fact" });
    (p.createEl("span", { text: i("md_agent_platform") }),
      p.createEl("span", { text: (f = r[s]) != null ? f : s }));
    let u = c.createDiv({ cls: "pf-module-fact" });
    (u.createEl("span", { text: i("md_agent_deployment") }),
      u.createEl("span", {
        text: o ? i("agent_deployed") : i("agent_not_deployed"),
      }));
    let _ = c.createDiv({ cls: "pf-module-fact" });
    if (
      (_.createEl("span", { text: i("agent_live_connection") }),
      _.createEl("span", { text: i("md_agent_connection_unknown") }),
      this._agentPlatformDraft === null)
    )
      W(t, {
        label: i("config_change"),
        onClick: () => {
          ((this._agentPlatformDraft = s), this.display());
        },
      });
    else {
      let h = t.createDiv({ cls: "pf-agent-config-editor" }),
        g = h.createEl("select", {
          attr: { "aria-label": i("md_agent_platform") },
        });
      for (let [v, m] of Object.entries(r)) {
        let E = g.createEl("option", { text: m, attr: { value: v } });
        E.selected = v === this._agentPlatformDraft;
      }
      g.addEventListener("change", () => {
        this._agentPlatformDraft = g.value;
      });
      let y = h.createDiv({ cls: "pf-agent-config-actions" });
      (W(y, {
        label: i("config_save"),
        onClick: () => {
          var m;
          let v = (m = this._agentPlatformDraft) != null ? m : s;
          ((this.plugin.settings.agent_platform = v),
            this.plugin.savePaperforgeJson({ agent_platform: v }),
            this.plugin.saveSettings(),
            (this._agentPlatformDraft = null),
            this.display());
        },
      }),
        W(y, {
          label: i("config_cancel"),
          onClick: () => {
            ((this._agentPlatformDraft = null), this.display());
          },
        }),
        W(y, {
          label: i("config_verify"),
          onClick: () => {
            var E;
            let v = (E = this._agentPlatformDraft) != null ? E : s,
              m = j.existsSync(G.join(this._getVaultBasePath(), n[v]));
            new C.Notice(
              m ? i("agent_verify_found") : i("agent_verify_missing")
            );
          },
        }));
    }
    this._renderSkillsList(t);
  }
  _renderMemoryDetail(e) {
    var o, c;
    this._renderModuleDetailShell(e, "memory");
    let t =
        (c = (o = this._capabilityState) == null ? void 0 : o.memory) != null
          ? c
          : re("memory"),
      r = e.createDiv({ cls: "pf-module-body" });
    (r.createEl("h3", { text: i("md_retrieval_coverage") }),
      t.user_state === "ready"
        ? r.createEl("p", {
            text: i("md_retrieval_ready"),
            cls: "pf-status-ok",
          })
        : t.user_state !== "checking" &&
          t.user_state !== "not_enabled" &&
          $e(r, {
            whatHappened:
              i("cc_module_memory") +
              " \u2014 " +
              this._getUserStateLabel(t.user_state),
            impact: i("retrieval_problem_impact"),
            nextStep: i("problem_use_action"),
            impactLabel: i("problem_impact"),
            nextLabel: i("problem_next"),
            copyLabel: i("problem_copy"),
            onCopyDiagnostic: () => this._buildAndCopyDiagnostic(),
          }));
    let n = r.createDiv({ cls: "pf-module-facts" }),
      s = n.createDiv({ cls: "pf-module-fact" });
    (s.createEl("span", { text: i("md_retrieval_coverage") }),
      s.createEl("span", {
        text:
          t.user_state === "ready"
            ? i("coverage_complete")
            : i("metric_not_available"),
      }));
    let a = n.createDiv({ cls: "pf-module-fact" });
    (a.createEl("span", { text: i("retrieval_freshness") }),
      a.createEl("span", {
        text:
          t.updated_at && t.updated_at !== new Date(0).toISOString()
            ? new Date(t.updated_at).toLocaleString()
            : i("metric_not_available"),
      }));
  }
  _dispatchModuleAction(e, t) {
    var a, o, c, p;
    let r = (a = t.action) == null ? void 0 : a.primary;
    if (!r) {
      this._probeModule(e);
      return;
    }
    let n = r.verb,
      s = (o = r.command) != null ? o : "";
    if (r.safety_class !== "safe" && r.confirmation_required) {
      new Ze(
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
    var s, a, o;
    if (
      (t === "setup" || t === "set_config") &&
      r === "paperforge setup" &&
      (e === "installation" || e === "library" || e === "ocr")
    ) {
      let c = [e];
      (e === "installation" && c.push("help"),
        new Ce(this.app, this.plugin, () => {
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
              p = nr(
                n.reason.code,
                n.reason.text,
                (o =
                  (a = (s = n.action) == null ? void 0 : s.primary) == null
                    ? void 0
                    : a.scope_count) != null
                  ? o
                  : 0,
                c
              );
            new Ge(
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
    (new C.Notice(
      (i("action_unknown_pair") || "Unknown action: {verb}").replace(
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
      new C.Notice(i("runtime_not_available") || "No Python runtime available");
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
    let o = this._callPython(n, {
      stream: !0,
      onData: (p) => {
        var h;
        let u =
            typeof p == "string"
              ? p
              : Buffer.isBuffer(p)
                ? p.toString("utf-8")
                : String(p),
          { events: _, buffer: f } = Ye(
            u,
            (h = this.plugin._ocrBuffer) != null ? h : ""
          );
        this.plugin._ocrBuffer = f;
        for (let g of _)
          g.event === "START"
            ? (this.plugin._ocrProgress &&
                (this.plugin._ocrProgress.total = g.total || 1),
              a.ocr &&
                (a.ocr.activity_progress = { current: 0, total: g.total || 1 }))
            : g.event === "PROGRESS" &&
              ((this.plugin._ocrProgress = {
                current: g.current || 0,
                total: g.total || 1,
                key: g.key || "",
              }),
              a.ocr &&
                (a.ocr.activity_progress = {
                  current: g.current || 0,
                  total: g.total || 1,
                }));
        this.display();
      },
      onError: (p) => {
        ((this.plugin._ocrProcess = null),
          a.ocr &&
            ((a.ocr.activity_state = "idle"),
            (a.ocr.activity_label = null),
            (a.ocr.activity_progress = null)),
          new C.Notice(i("ocr_error_notice"), 8e3),
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
            ? new C.Notice(
                e === "run"
                  ? i("ocr_run_complete")
                  : e === "rebuild"
                    ? i("ocr_rebuild_complete")
                    : i("ocr_redo_complete")
              )
            : p === 130 || this.plugin._ocrWasStopped
              ? ((this.plugin._ocrWasStopped = !1),
                new C.Notice(i("ocr_stopped_notice")))
              : new C.Notice(i("ocr_failed_notice"), 8e3),
          this._probeModule("ocr"),
          this.display());
      },
    });
    this.plugin._ocrProcess = o;
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
      let o = this._callPython(n, {
        stream: !0,
        onData: (c) => {
          var f;
          let p =
              typeof c == "string"
                ? c
                : Buffer.isBuffer(c)
                  ? c.toString("utf-8")
                  : String(c),
            { events: u, buffer: _ } = Ye(
              p,
              (f = this.plugin._embedBuffer) != null ? f : ""
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
            new C.Notice(s + " build error: " + (c.message || c), 8e3),
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
              ? new C.Notice(s + " build complete.")
              : new C.Notice(
                  s + " build failed with exit code " + (c != null ? c : "?"),
                  8e3
                ),
            this._probeModule("memory"),
            this.display());
        },
      });
      this.plugin._embedProcess = o;
    } else
      this._callPython(n, {
        timeout: 12e4,
        onClose: (o, c, p) => {
          (r.memory &&
            ((r.memory.activity_state = "idle"),
            (r.memory.activity_label = null)),
            o === 0
              ? new C.Notice(s + " rebuild complete")
              : new C.Notice(
                  s + " build failed" + (p ? ": " + p.slice(0, 120) : ""),
                  8e3
                ),
            this._probeModule("memory"),
            this.display());
        },
      });
  }
  _renderModuleDetailShell(e, t) {
    var v, m, E, w, b, x;
    e.classList.add("pf-module-detail");
    let r = t === "agent" ? "agent_detail_heading" : t + "_detail_heading",
      n = "pf-" + t + "-detail-heading";
    e.createEl("button", {
      cls: "pf-back-btn",
      text: i("btn_back_to_overview"),
    }).addEventListener("click", () => {
      (this._detailReturn
        ? ((this.activeTab = this._detailReturn.tab),
          (this._focusTargetId = this._detailReturn.selector),
          (this._detailReturn = null))
        : ((this.activeTab = "overview"),
          (this._focusTargetId = `button.pf-cc-card[data-module="${t}"]`)),
        (this._selectedDetailModule = ""),
        this.display());
    });
    let a = this._getOverviewModules(),
      o = e.createDiv({
        cls: "pf-module-detail-selector",
        attr: { role: "tablist", "aria-label": i("md_module_switcher") },
      });
    for (let k of a)
      o.createEl("button", {
        cls:
          "pf-module-detail-btn" +
          (k.id === t ? " pf-module-detail-btn--active" : ""),
        text: k.label,
        attr: { role: "tab", "aria-selected": String(k.id === t) },
      }).addEventListener("click", () => {
        ((this._selectedDetailModule = k.id),
          (this._focusTargetId = "#pf-" + k.id + "-detail-heading"),
          this.display());
      });
    let c = e.createEl("select", {
      cls: "pf-module-switcher",
      attr: { "aria-label": i("md_module_switcher") },
    });
    for (let k of a) {
      let S = c.createEl("option", { text: k.label, attr: { value: k.id } });
      S.selected = k.id === t;
    }
    (c.addEventListener("change", () => {
      ((this._selectedDetailModule = c.value),
        (this._focusTargetId = "#pf-" + c.value + "-detail-heading"),
        this.display());
    }),
      e.createEl("h2", {
        cls: "pf-module-detail-heading",
        text: i(r),
        attr: { id: n, tabindex: "-1" },
      }));
    let p =
        t === "agent"
          ? this._getAgentPlaceholderEnvelope()
          : (m = (v = this._capabilityState) == null ? void 0 : v[t]) != null
            ? m
            : re(t),
      u =
        (E = p.user_state) != null
          ? E
          : p.capability_state === "ready"
            ? "ready"
            : "action_required",
      _ = e.createDiv({
        cls: "pf-module-summary",
        attr: { "aria-live": "polite" },
      }),
      f = _.createDiv({ cls: "pf-module-summary-header" });
    (f.createEl("span", {
      cls: "pf-module-summary-name",
      text: this._getUserModuleName(t),
    }),
      Ee(f, u, this._getUserStateLabel(u)),
      _.createEl("p", {
        cls: "pf-module-summary-consequence",
        text: this._getModuleConsequence(t, p),
      }),
      p.activity_state === "running" &&
        ct(_, {
          label: i("cc_activity_running"),
          progress: p.activity_progress,
        }));
    let h = (w = p.action) == null ? void 0 : w.primary;
    if (h && u !== "ready" && t !== "agent") {
      let k =
          "action_" +
          ((b = h.action_id) != null ? b : h.verb).replace(/[.-]/g, "_"),
        S = i(k),
        R =
          S !== k
            ? S
            : i("cc_action_" + h.verb) !== "cc_action_" + h.verb
              ? i("cc_action_" + h.verb)
              : i("cc_action_probe");
      W(_, {
        label: R,
        loading: p.activity_state === "running",
        onClick: () => this._dispatchModuleAction(t, p),
      });
    }
    let g = _.createEl("details", { cls: "pf-module-diagnostics" });
    g.createEl("summary", { text: i("advanced_diagnostics") });
    let y = g.createDiv({ cls: "pf-module-diagnostics-body" });
    (y.createEl("div", { text: i("cc_diag_module") + ": " + p.module }),
      y.createEl("div", {
        text: i("cc_diag_state") + ": " + this._getUserStateLabel(u),
      }),
      y.createEl("div", { text: i("cc_diag_severity") + ": " + p.severity }),
      y.createEl("div", {
        text: i("cc_diag_activity") + ": " + p.activity_state,
      }),
      y.createEl("div", { text: i("cc_diag_reason") + ": " + p.reason.code }),
      y.createEl("div", {
        text: i("cc_diag_ttl") + ": " + p.ttl_seconds + "s",
      }));
    for (let k of (x = p.notices) != null ? x : [])
      y.createEl("div", { text: k.message });
    y.createEl("div", {
      text:
        i("cc_diag_updated") + ": " + new Date(p.updated_at).toLocaleString(),
    });
  }
  _renderHelpTab(e) {
    var u, _, f;
    (e.createEl("h2", { text: i("help_title") }),
      e.createEl("p", {
        text: i("help_intro"),
        cls: "paperforge-settings-desc",
      }));
    let t = e.createDiv({ cls: "pf-help-section" });
    t.createEl("h3", { text: i("help_getting_started") });
    for (let h of [
      ["library", "help_library_task"],
      ["ocr", "help_ocr_task"],
      ["memory", "help_retrieval_task"],
      ["agent", "help_agent_task"],
    ])
      t.createEl("button", {
        cls: "pf-help-task",
        text: i(h[1]),
        attr: { "data-module": h[0] },
      }).addEventListener("click", () => {
        ((this._detailReturn = {
          tab: "help",
          selector: `.pf-help-task[data-module="${h[0]}"]`,
        }),
          this._handleCardNavigation(h[0]));
      });
    let r = Object.values((u = this._capabilityState) != null ? u : {}).filter(
        (h) =>
          h.user_visible_failure ||
          h.user_state === "action_required" ||
          h.user_state === "detection_failed"
      ),
      n = e.createDiv({ cls: "pf-help-section" });
    if ((n.createEl("h3", { text: i("help_current_problem") }), r.length === 0))
      n.createEl("p", {
        text: i("help_no_problem"),
        cls: "setting-item-description",
      });
    else
      for (let h of r) {
        let g = n.createDiv({ cls: "pf-help-problem" });
        (g.createEl("strong", { text: this._getUserModuleName(h.module) }),
          g.createEl("span", {
            text: this._getModuleConsequence(h.module, h),
          }));
      }
    let s = e.createDiv({ cls: "pf-help-section" });
    (s.createEl("h3", { text: i("help_support") }),
      s.createEl("p", {
        text: i("help_support_desc"),
        cls: "setting-item-description",
      }),
      W(s, {
        label: i("help_copy"),
        onClick: () => this._buildAndCopyDiagnostic(),
      }));
    let a = e.createDiv({ cls: "pf-help-section" });
    (a.createEl("h3", { text: i("help_documentation") }),
      a.createEl("p", {
        text: i("help_documentation_desc"),
        cls: "setting-item-description",
      }),
      a
        .createEl("a", {
          text: i("help_open_documentation"),
          href: "https://github.com/LLLin000/PaperForge#readme",
          cls: "pf-help-link",
        })
        .setAttr("target", "_blank"));
    let c = e.createDiv({ cls: "pf-help-section" });
    (c.createEl("h3", { text: i("help_release_notes") }),
      c.createEl("p", {
        text: i("help_release_notes_desc").replace(
          "{version}",
          (f = (_ = this.plugin.manifest) == null ? void 0 : _.version) != null
            ? f
            : "\u2014"
        ),
        cls: "setting-item-description",
      }),
      c
        .createEl("a", {
          text: i("help_open_release_notes"),
          href: "https://github.com/LLLin000/PaperForge/releases",
          cls: "pf-help-link",
        })
        .setAttr("target", "_blank"));
  }
  _execMemoryStatus(e, t, r) {
    let n = pe();
    (0, ee.exec)(
      `"${e}" -m paperforge --vault "${t}" memory status --json`,
      { encoding: "utf-8", timeout: 15e3, env: n },
      (s, a) => {
        if (s) {
          r("Status unavailable");
          return;
        }
        try {
          let o = JSON.parse(a);
          if (o.ok) {
            let c = o.data,
              p = c.fresh ? "fresh" : "stale";
            r(
              `Papers: ${c.paper_count_db} | ${p}${c.needs_rebuild ? " - needs rebuild" : ""}`
            );
          } else r("DB not found. Run paperforge memory build.");
        } catch (o) {
          r("Could not parse status.");
        }
      }
    );
  }
  _execEmbedStatus(e, t, r) {
    let n = pe();
    (0, ee.exec)(
      `"${e}" -m paperforge --vault "${t}" embed status --json`,
      { encoding: "utf-8", timeout: 15e3, env: n },
      (s, a) => {
        if (s) {
          r("Status unavailable");
          return;
        }
        try {
          let o = JSON.parse(a);
          o.ok
            ? r(
                `Chunks: ${o.data.chunk_count} | ${o.data.model} | ${o.data.mode}`
              )
            : r("Could not parse status.");
        } catch (o) {
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
      o = (u) => {
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
          (_, f, h) => {
            t && t.onClose && t.onClose(_ ? 1 : 0, f, h);
          }
        );
      };
    if (a)
      return (
        de(sr(this.app), t.credentialType).then((u) => {
          t && t.stream ? o(u) : c(u);
        }),
        null
      );
    let p = (t == null ? void 0 : t.env) || pe();
    return t && t.stream ? o(p) : (c(p), null);
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
      text: i("feat_memory_rebuild_btn"),
    });
    ((n.title = "Rebuild memory database"),
      (n.onclick = () => {
        let a = this.app.vault.adapter.basePath,
          o = this._resolveRuntimeCommand(a);
        if (!(o != null && o.path)) {
          new C.Notice(i("feat_no_python"));
          return;
        }
        (console.log("[PaperForge] Rebuilding memory:", o.path),
          n.setText(i("feat_memory_rebuilding")),
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
                n.setText(i("feat_memory_rebuild_btn")),
                n.removeAttribute("disabled"),
                c === 0
                  ? new C.Notice(i("feat_memory_rebuild_done"))
                  : new C.Notice(
                      i("feat_memory_rebuild_failed") +
                        (u ? " " + u.slice(0, 80) : "")
                    ),
                (this._memoryStatusText = ht(a)),
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
            Je(this.app, this.plugin, e));
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
            (this._memoryStatusText = ht(e)),
            (this._embedStatusText = we(e)),
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
        .setText(i("feat_vector_desc")),
      new C.Setting(e)
        .setName(i("feat_vector_enable"))
        .setDesc(i("feat_vector_enable_desc"))
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
      text: i("feat_vector_config_label"),
    });
    let a = e.createEl("div", { cls: "paperforge-vector-config" }),
      o = (p) => {
        ((a.style.display = p ? "none" : ""),
          (s.style.transform = p ? "rotate(-90deg)" : "rotate(0deg)"));
      };
    if (
      (o(bt(this._featurePanelsCollapsed, "vectorConfig", !1)),
      n.addEventListener("click", () => {
        let p = ar(this._featurePanelsCollapsed, "vectorConfig", !1);
        o(p);
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
      let p = qe(r);
      ((this._vectorDepsOk = p && (c = p.deps_installed) != null ? c : !1),
        this._vectorDepsOk && (this._embedStatusText = we(r)),
        this.display());
    }
  }
  _renderApiConfig(e) {
    let r =
        this.plugin.settings._vector_db_configured || !1
          ? "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022"
          : "sk-...",
      n = null;
    (new C.Setting(e)
      .setName(i("feat_openai_key"))
      .setDesc(i("feat_openai_key_desc"))
      .addText((s) => {
        ((s.inputEl.type = "password"),
          s
            .setPlaceholder(r)
            .setValue("")
            .onChange((a) => {
              a &&
                (n && clearTimeout(n),
                (n = setTimeout(async () => {
                  let o = this.app.secretStorage;
                  if (o != null && o.setSecret) {
                    try {
                      (await o.setSecret("vector-db-api-key", a),
                        (await o.getSecret("vector-db-api-key")) === a &&
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
      new C.Setting(e)
        .setName(i("feat_api_base_url"))
        .setDesc(i("feat_api_base_url_desc"))
        .addText((s) => {
          s.setPlaceholder("https://api.openai.com/v1")
            .setValue(this.plugin.settings.vector_db_api_base || "")
            .onChange((a) => {
              ((this.plugin.settings.vector_db_api_base = a),
                this.plugin.saveSettings());
            });
        }),
      new C.Setting(e)
        .setName(i("feat_api_model"))
        .setDesc(i("feat_api_model_desc"))
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
      .setText(i("feat_deps_missing")),
      new C.Setting(e)
        .setName(i("feat_install_deps"))
        .setDesc(i("feat_install_deps_desc"))
        .addButton((r) => {
          r.setButtonText(i("feat_install_btn"))
            .setCta()
            .onClick(async () => {
              let n = this.app.vault.adapter.basePath,
                s = this._resolveRuntimeCommand(n);
              if (!(s != null && s.path)) {
                new C.Notice(i("feat_no_python"));
                return;
              }
              (r.setButtonText(i("feat_installing")), r.setDisabled(!0));
              let a = "chromadb openai",
                o = new C.Notice(
                  i("feat_installing_pkgs").replace("{pkgs}", a),
                  0
                );
              try {
                let c = Object.assign(pe(), {
                    PYTHONIOENCODING: "utf-8",
                    PYTHONUTF8: "1",
                  }),
                  p = a.split(" ");
                (await new Promise((u, _) => {
                  (0, ee.execFile)(
                    s.path,
                    [...s.args, "-m", "pip", "install", ...p],
                    { cwd: n, timeout: 3e5, env: c, windowsHide: !0 },
                    (f) => {
                      f ? _(f) : u();
                    }
                  );
                }),
                  o.hide(),
                  new C.Notice(i("feat_install_done")),
                  (this._vectorDepsOk = !0),
                  (this._embedStatusText = we(n)),
                  this.display());
              } catch (c) {
                (o.hide(),
                  new C.Notice(
                    i("feat_install_failed") + (c.stderr || c.message || c)
                  ),
                  r.setButtonText(i("feat_retry_btn")),
                  r.setDisabled(!1));
              }
            });
        }));
  }
  _renderVectorReady(e, t) {
    (e.createEl("div", { cls: "paperforge-desc-box" }).setText(we(t)),
      this._renderApiConfig(e));
    let n = e.createEl("div", { cls: "paperforge-embed-section" });
    n.createEl("div", { cls: "paperforge-embed-header" }).createEl("span", {
      text: i("retrieval_rebuild_vectors"),
      cls: "setting-item-name",
    });
    let a = n.createEl("div", { cls: "paperforge-embed-controls" }),
      o = n.createEl("div", {
        cls: "paperforge-embed-status-text",
        attr: { "aria-live": "polite" },
      });
    (() => {
      (a.empty(), o.empty());
      let p = qe(t),
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
      let { current: f, total: h, key: g } = this.plugin._embedProgress,
        y =
          typeof (p == null ? void 0 : p.body_chunk_count) == "number"
            ? p.body_chunk_count
            : 0,
        v =
          typeof (p == null ? void 0 : p.object_chunk_count) == "number"
            ? p.object_chunk_count
            : 0,
        E =
          (typeof (p == null ? void 0 : p.chunk_count) == "number"
            ? p.chunk_count
            : 0) +
          y +
          v,
        w = E > 0,
        b = p !== null && typeof p.corrupted == "boolean" && p.corrupted,
        x = !!this.plugin._embedProcess,
        k = !this.plugin._embedProcess && _.status === "running",
        S =
          (p == null ? void 0 : p.deps_installed) !== void 0
            ? !!p.deps_installed
            : !0,
        R = typeof _.status == "string" ? _.status : "",
        V = typeof _.message == "string" ? _.message : "",
        M = async (P) => {
          var J;
          if (P === "--resume" && w && !b) {
            let T = i("retrieval_rebuild_warning").replace("{n}", String(E));
            if (!confirm(T)) return;
          }
          if (P === "--force" && w && !b) {
            let T =
              "Force rebuild will replace " +
              E +
              " existing chunk(s). Continue?";
            if (!confirm(T)) return;
          }
          let B = this._resolveRuntimeCommand(t);
          if (!(B != null && B.path)) {
            new C.Notice(i("retrieval_no_python"));
            return;
          }
          let Y = await de(sr(this.app), "embed");
          ((Y.PYTHONIOENCODING = "utf-8"),
            (Y.PYTHONUTF8 = "1"),
            (Y.VECTOR_DB_API_BASE =
              this.plugin.settings.vector_db_api_base || ""),
            (Y.VECTOR_DB_API_MODEL =
              this.plugin.settings.vector_db_api_model || ""),
            (this.plugin._embedStderr = ""),
            (this.plugin._embedProgress = { current: 0, total: 0, key: "" }),
            (this.plugin._embedProcess = this._callPython(
              ["embed", "build", P],
              {
                stream: !0,
                env: Y,
                onData: (T) => {
                  var oe;
                  let te =
                      typeof T == "string"
                        ? T
                        : Buffer.isBuffer(T)
                          ? T.toString("utf-8")
                          : String(T),
                    { events: se, buffer: be } = Ye(
                      te,
                      (oe = this.plugin._embedBuffer) != null ? oe : ""
                    );
                  this.plugin._embedBuffer = be;
                  for (let U of se)
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
                onStderr: (T) => {
                  (this.plugin._embedStderr || (this.plugin._embedStderr = ""),
                    (this.plugin._embedStderr += String(T)));
                },
                onError: (T) => {
                  ((this.plugin._embedProcess = null),
                    new C.Notice(
                      i("feat_build_failed") + ": " + (T.message || T)
                    ),
                    this.display());
                },
                onClose: (T) => {
                  var te;
                  if (
                    (clearInterval(
                      (te = this.plugin._embedPollInterval) != null
                        ? te
                        : void 0
                    ),
                    (this.plugin._embedPollInterval = null),
                    (this.plugin._embedProcess = null),
                    T === 0)
                  )
                    ((this.plugin._embedProgress.current =
                      this.plugin._embedProgress.total),
                      this.plugin.saveSettings(),
                      (this._embedStatusText = we(t)),
                      new C.Notice(i("feat_build_complete")));
                  else {
                    this._embedStatusText = null;
                    let se = (this.plugin._embedStderr || "").slice(0, 200);
                    new C.Notice(
                      i("feat_build_failed") + (se ? ": " + se : ""),
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
              (J = this.plugin._embedPollInterval) != null ? J : void 0
            ),
            (this.plugin._embedPollInterval = setInterval(() => {
              this.plugin._embedPolling ||
                ((this.plugin._embedPolling = !0),
                this._callPython(["embed", "status", "--json"], {
                  timeout: 5e3,
                  onClose: (T, te) => {
                    var se;
                    if (((this.plugin._embedPolling = !1), T === 0 && te))
                      try {
                        let oe = JSON.parse(te).data;
                        if (oe && oe.build_state) {
                          let U = oe.build_state;
                          ((U.status === "stopping" || U.status === "idle") &&
                            this.plugin._embedProcess &&
                            ((this.plugin._embedProcess = null),
                            clearInterval(
                              (se = this.plugin._embedPollInterval) != null
                                ? se
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
                      } catch (be) {}
                  },
                }));
            }, 2e3)),
            this.display());
        },
        I = Be(t),
        O = !1;
      I &&
        typeof I.summary == "object" &&
        I.summary !== null &&
        "status" in I.summary &&
        (O = I.summary.status === "version_mismatch");
      let D;
      switch (
        (S
          ? O
            ? (D = "runtime-mismatch")
            : R === "stopping"
              ? (D = "stopping")
              : x && R === "running"
                ? (D = "building")
                : R === "failed"
                  ? (D = "failed")
                  : R === "stopped"
                    ? (D = "stopped")
                    : k
                      ? (D = "stale")
                      : b
                        ? (D = "corrupted")
                        : w
                          ? (D = "ready")
                          : (D = "idle")
          : (D = "deps-missing"),
        D)
      ) {
        case "building": {
          let P = a.createEl("div", { cls: "paperforge-progress-track" });
          P.style.cssText = "flex:1;";
          let B = h > 0 ? ((f / h) * 100).toFixed(1) : "0",
            Y = P.createEl("div", { cls: "paperforge-progress-seg done" });
          if (
            ((Y.style.cssText = `width:${B}%; min-width:${f > 0 ? "2px" : "0"};`),
            f < h)
          ) {
            let T = P.createEl("div", {
              cls: "paperforge-progress-seg pending",
            });
            T.style.cssText = `width:${(100 - parseFloat(B)).toFixed(1)}%;`;
          }
          (o.createEl("span", {
            cls: "paperforge-embed-progress-text",
            text: `${f}/${h} papers`,
          }),
            g &&
              o.createEl("span", {
                cls: "paperforge-embed-progress-key",
                text: ` (${g})`,
              }));
          let J = a.createEl("button");
          (J.setText(i("retrieval_stop")),
            (J.className = "mod-warning"),
            J.addEventListener("click", () => {
              (this._callPython(["embed", "stop", "--json"], { timeout: 8e3 }),
                this.display());
            }));
          break;
        }
        case "stopping": {
          let P = a.createEl("div", { cls: "paperforge-progress-track" });
          P.style.cssText = "flex:1; opacity:0.5;";
          let B = h > 0 ? ((f / h) * 100).toFixed(1) : "0",
            Y = P.createEl("div", { cls: "paperforge-progress-seg done" });
          if (
            ((Y.style.cssText = `width:${B}%; min-width:${f > 0 ? "2px" : "0"};`),
            f < h)
          ) {
            let T = P.createEl("div", {
              cls: "paperforge-progress-seg pending",
            });
            T.style.cssText = `width:${(100 - parseFloat(B)).toFixed(1)}%;`;
          }
          o.createEl("span", { text: i("retrieval_build_stopping") });
          let J = a.createEl("button");
          (J.setText(i("retrieval_stop")),
            (J.className = "mod-warning"),
            J.setAttr("disabled", ""));
          break;
        }
        case "failed": {
          o.createEl("div", {
            cls: "paperforge-desc-box",
            text: i("retrieval_build_failed") + (V ? ": " + V : ""),
            attr: { style: "color:var(--text-error);" },
          });
          let P = a.createEl("button");
          (P.setText(i("retrieval_retry")),
            (P.className = "mod-cta"),
            P.addEventListener("click", () => M("--resume")));
          let B = a.createEl("button");
          (B.setText(i("retrieval_force_rebuild")),
            (B.style.marginLeft = "6px"),
            B.addEventListener("click", () => M("--force")));
          break;
        }
        case "stopped": {
          o.setText(i("retrieval_build_stopped"));
          let P = a.createEl("button");
          (P.setText(i("retrieval_retry")),
            (P.className = "mod-cta"),
            P.addEventListener("click", () => M("--resume")));
          break;
        }
        case "corrupted": {
          o.createEl("div", {
            cls: "paperforge-desc-box",
            text: i("feat_vector_corrupted"),
            attr: { style: "background:var(--background-modifier-warning);" },
          });
          let P = a.createEl("button");
          (P.setText(i("retrieval_force_rebuild")),
            (P.className = "mod-cta"),
            P.addEventListener("click", () => M("--force")));
          break;
        }
        case "stale": {
          o.createEl("div", {
            cls: "paperforge-desc-box",
            text: i("retrieval_build_stale"),
            attr: { style: "color:var(--text-warning);" },
          });
          let P = a.createEl("button");
          (P.setText(i("retrieval_rebuild_vectors")),
            (P.className = "mod-cta"),
            P.addEventListener("click", () => M("--resume")));
          break;
        }
        case "ready": {
          a.createEl("span", {
            text: E + " chunks embedded",
            cls: "setting-item-description",
          });
          let P = a.createEl("button");
          (P.setText(i("retrieval_rebuild_vectors")),
            (P.className = "mod-cta"),
            P.addEventListener("click", () => M("--resume")));
          let B = a.createEl("button");
          (B.setText(i("retrieval_force_rebuild")),
            (B.style.marginLeft = "6px"),
            B.addEventListener("click", () => M("--force")));
          break;
        }
        case "deps-missing": {
          o.setText(i("retrieval_build_deps_missing"));
          let P = a.createEl("a");
          (P.setText(i("feat_install_deps")),
            (P.style.cssText = "cursor:pointer; text-decoration:underline;"),
            P.addEventListener("click", () => {
              this.display();
            }));
          break;
        }
        case "runtime-mismatch": {
          o.createEl("div", {
            cls: "paperforge-desc-box",
            text: i("retrieval_build_runtime_mismatch"),
            attr: { style: "color:var(--text-warning);" },
          });
          let P = a.createEl("a");
          (P.setText(i("runtime_health_sync")),
            (P.style.cssText = "cursor:pointer; text-decoration:underline;"),
            P.addEventListener("click", () => {
              this.display();
            }));
          break;
        }
        case "idle":
        default: {
          o.setText(i("retrieval_build_idle"));
          let P = a.createEl("button");
          (P.setText(i("feat_build_btn")),
            (P.className = "mod-cta"),
            P.addEventListener("click", () => M("--resume")));
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
        new C.Notice(r));
      return;
    }
    if (!j.existsSync(e)) {
      let r = "\u8DEF\u5F84\u4E0D\u5B58\u5728 / Path does not exist";
      (t &&
        (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${r}</span>`),
        new C.Notice(r, 4e3));
      return;
    }
    try {
      j.accessSync(e, j.constants.X_OK);
    } catch (r) {
      let n = "\u4E0D\u53EF\u6267\u884C / Not executable";
      (t &&
        (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${n}</span>`),
        new C.Notice(n, 4e3));
      return;
    }
    (0, ee.execFile)(e, ["--version"], { timeout: 8e3 }, (r, n) => {
      if (r || !n) {
        let c = "\u65E0\u6CD5\u8FD0\u884C / Cannot run";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${c}</span>`),
          new C.Notice(c, 4e3));
        return;
      }
      let s = n.match(/Python (\d+)\.(\d+)/);
      if (!s) {
        let c = "\u65E0\u6CD5\u89E3\u6790\u7248\u672C / Cannot parse version";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${c}</span>`),
          new C.Notice(c, 4e3));
        return;
      }
      let a = parseInt(s[1], 10),
        o = parseInt(s[2], 10);
      if (a < 3 || (a === 3 && o < 11)) {
        let c =
          "Python \u7248\u672C\u8FC7\u4F4E\uFF0C\u9700\u8981 3.11+ / Python version too low, need 3.11+";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${c}</span>`),
          new C.Notice(c, 4e3));
        return;
      }
      (0, ee.execFile)(e, ["-m", "pip", "--version"], { timeout: 8e3 }, (c) => {
        if (c) {
          let p = `\u2713 Python ${a}.${o} \u6709\u6548\uFF0C\u4F46\u672A\u68C0\u6D4B\u5230 pip / Valid, but pip not found`;
          (t &&
            (t.innerHTML = `<span style="color:var(--text-warning)">\u26A0 ${p}</span>`),
            new C.Notice(p, 4e3));
        } else {
          let p = `\u2713 Python ${a}.${o} \u6709\u6548 / Valid`;
          (t &&
            (t.innerHTML = `<span style="color:var(--text-accent)">${p}</span>`),
            new C.Notice(p, 4e3));
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
          detail: n ? i("check_python_fail") : s.trim(),
        });
        let o = !1,
          c = process.env.HOME || process.env.USERPROFILE || ir.homedir() || "";
        if (process.platform === "darwin")
          o = [
            "/Applications/Zotero.app",
            G.join(c, "Applications", "Zotero.app"),
          ].some((y) => {
            try {
              return j.existsSync(y);
            } catch (v) {
              return !1;
            }
          });
        else if (process.platform === "win32") {
          let g = process.env.ProgramFiles || "",
            y = process.env.LOCALAPPDATA || "";
          o = [
            G.join(g, "Zotero"),
            G.join(g, "(x86)", "Zotero"),
            G.join(y, "Programs", "Zotero"),
            G.join(y, "Zotero"),
            G.join(c, "AppData", "Local", "Programs", "Zotero"),
          ]
            .filter(Boolean)
            .some((m) => {
              try {
                return j.existsSync(m);
              } catch (E) {
                return !1;
              }
            });
        } else
          o = [
            G.join(c, ".local", "share", "zotero", "zotero"),
            "/usr/bin/zotero",
            "/usr/local/bin/zotero",
          ].some((y) => {
            try {
              return j.existsSync(y);
            } catch (v) {
              return !1;
            }
          });
        let p = this.plugin.settings.zotero_data_dir;
        if (!o && p)
          try {
            o = j.existsSync(p);
          } catch (g) {}
        a.push({
          label: "Zotero",
          ok: o,
          detail: o ? i("check_zotero_ok") : i("check_zotero_fail"),
        });
        let u = !1,
          _ = process.env.APPDATA || "";
        (process.platform === "win32" &&
          _ &&
          (u = Ke(G.join(_, "Zotero", "Zotero", "Profiles"))),
          !u &&
            process.platform === "darwin" &&
            c &&
            (u = Ke(
              G.join(c, "Library", "Application Support", "Zotero", "Profiles")
            )),
          !u &&
            process.platform !== "win32" &&
            process.platform !== "darwin" &&
            c &&
            (u = Ke(G.join(c, ".zotero", "zotero", "Profiles"))),
          !u && p && String(p).trim() && (u = _t(p.trim())),
          !u && c && (u = _t(G.join(c, "Zotero"))),
          a.push({
            label: "Better BibTeX",
            ok: u,
            detail: u ? i("check_bbt_ok") : i("check_bbt_fail"),
          }));
        let f = { true: "\u2713", false: "\u2717" };
        if (this._checkEl) {
          this._checkEl.setText(
            a.map((y) => `${f[String(y.ok)]} ${y.label}: ${y.detail}`).join(`
`)
          );
          let g = a.some((y) => !y.ok);
          this._checkEl.className = `paperforge-message msg-${g ? "error" : "ok"}`;
        }
        let h = a.filter((g) => !g.ok);
        (h.length > 0 &&
          new C.Notice(
            `[!!] \u672A\u901A\u8FC7: ${h.map((g) => g.label).join(", ")}`,
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
    var o, c, p;
    let t = e.createDiv({ cls: "pf-maintenance-inbox" }),
      r = (o = this._capabilityState) == null ? void 0 : o.maintenance;
    if (
      !r ||
      (r.activity_state === "running" &&
        ((c = r.reason) == null ? void 0 : c.code) === "maintenance.probing") ||
      r.user_state === "checking" ||
      r.capability_state === "unknown" ||
      (r.capability_state !== "ready" && r.capability_state !== "needs_action")
    ) {
      (t.createEl("p", {
        cls: "pf-maintenance-inbox-empty",
        text: i("maintenance_checking"),
      }),
        !r || r.capability_state === "unknown"
          ? this._probing.has("maintenance") || this._probeModule("maintenance")
          : r.activity_state !== "running" &&
            this._requestMaintenanceProjection());
      return;
    }
    let s = ((p = r.items) != null ? p : []).filter(
      (u) => u.activity_state !== "running" && u.maintenance_eligible !== !1
    );
    if (s.length === 0) {
      let u = t.createDiv({ cls: "pf-maintenance-empty-state" });
      (u.createEl("h3", { text: i("maintenance_empty_title") }),
        u.createEl("p", { text: i("maintenance_empty_body") }));
      return;
    }
    t.createEl("p", {
      cls: "pf-maintenance-inbox-summary",
      text: i("maintenance_n_pending").replace("{n}", String(s.length)),
    });
    let a = t.createDiv({
      cls: "pf-maintenance-inbox-list",
      attr: { role: "list" },
    });
    for (let u of s) this._renderMaintenanceInboxItem(a, u);
  }
  _renderMaintenanceInboxItem(e, t) {
    var f, h, g;
    let r = e.createDiv({
        cls: "pf-maintenance-inbox-item",
        attr: { role: "listitem", "data-module": t.module },
      }),
      n = r.createDiv({ cls: "pf-maintenance-inbox-item-info" }),
      s = n.createDiv({ cls: "pf-maintenance-item-header" });
    s.createEl("strong", { text: this._getUserModuleName(t.module) });
    let a =
      (f = t.user_state) != null
        ? f
        : t.severity === "error" || t.severity === "warning"
          ? "action_required"
          : "detection_failed";
    (Ee(s, a, this._getUserStateLabel(a)),
      n.createEl("p", {
        cls: "pf-maintenance-inbox-item-reason",
        text:
          (h = this._localizeReason(t.reason_code, t.module)) != null
            ? h
            : i("cc_consequence_action_required"),
      }),
      n.createEl("p", {
        cls: "pf-maintenance-inbox-item-impact",
        text:
          t.module === "library"
            ? i("library_problem_impact")
            : t.module === "ocr"
              ? i("ocr_problem_impact")
              : t.module === "memory"
                ? i("retrieval_problem_impact")
                : i("maintenance_default_impact"),
      }));
    let o = t.action,
      c = o
        ? "action_" +
          ((g = o.action_id) != null ? g : o.verb).replace(/[.-]/g, "_")
        : "",
      p = c ? i(c) : "",
      u = o
        ? p !== c
          ? p
          : i("cc_action_" + o.verb) !== "cc_action_" + o.verb
            ? i("cc_action_" + o.verb)
            : i("maintenance_open_module")
        : i("maintenance_open_module");
    r.createEl("button", {
      cls: "pf-maintenance-inbox-item-action",
      text: u,
    }).addEventListener("click", () => {
      o
        ? this._dispatchItemAction(t)
        : ((this._detailReturn = {
            tab: "maintenance",
            selector:
              '.pf-maintenance-inbox-item[data-module="' + t.module + '"]',
          }),
          this._handleCardNavigation(t.module));
    });
  }
  _renderMaintenanceTab(e) {
    (e.createEl("h2", {
      text: i("tab_maintenance"),
      attr: { id: "pf-maintenance-heading", tabindex: "-1" },
    }),
      this._renderMaintenanceInbox(e));
  }
  _renderReleaseNotesTab(e) {
    (e.createEl("h2", { text: "\u66F4\u65B0\u4E0E\u624B\u518C" }),
      e.createEl("h3", { text: "\u7248\u672C\u66F4\u65B0\u8BB0\u5F55" }));
    let t = or.default.versions || [];
    for (let s of t) {
      let a = e.createEl("div", { cls: "paperforge-release-card" }),
        o = a.createEl("div", { cls: "paperforge-release-header" });
      if (
        (o.createEl("strong", { text: `v${s.version} \u2014 ${s.title}` }),
        o.createEl("span", {
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
    ((this._capabilityState = Lt(e != null ? e : {}, Me)),
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
        action: { primary: e === "maintenance" ? null : Ie(e) },
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
        let f = {
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
          action: { primary: At() },
          notices: [],
          user_state: "setup_required",
          capability_kind: "required",
          maintenance_eligible: !1,
          user_visible_failure: !1,
          user_impact: null,
          updated_at: new Date().toISOString(),
          ttl_seconds: 60,
        };
        this._updateCapabilityEnvelope(e, f);
      } else this._updateCapabilityEnvelope(e, ve(e));
      return;
    }
    let o = [...a.args, "-m", "paperforge", "--vault", s, "probe", e, "--json"];
    (e === "library" &&
      t != null &&
      t !== 0 &&
      o.push("--last-operation-exit-code", String(t)),
      (0, ee.execFile)(a.path, o, { cwd: s, timeout: 15e3 }, (f, h, g) => {
        if ((this._probing.delete(e), f)) {
          (console.warn(`[PaperForge] Probe ${e} failed:`, f.message),
            this._updateCapabilityEnvelope(e, ve(e)));
          return;
        }
        try {
          let y = JSON.parse(h);
          nt(y, e)
            ? this._updateCapabilityEnvelope(e, y)
            : (console.warn(
                `[PaperForge] Probe ${e}: invalid envelope schema`,
                h == null ? void 0 : h.slice(0, 200)
              ),
              this._updateCapabilityEnvelope(e, ve(e)));
        } catch (y) {
          (console.warn(
            `[PaperForge] Probe ${e}: unparseable JSON`,
            h == null ? void 0 : h.slice(0, 200)
          ),
            this._updateCapabilityEnvelope(e, ve(e)));
        }
      }));
  }
  _updateCapabilityEnvelope(e, t) {
    this._capabilityState || (this._capabilityState = {});
    let r = this._capabilityState[t.module];
    (Ht(r, t) && this._lastKnownState.set(e, Nt(t)),
      (this._capabilityState[t.module] = t),
      this._persistCapabilityState(),
      (r == null ? void 0 : r.activity_state) === "running" &&
        t.activity_state !== "running" &&
        (new C.Notice(i("cc_notice_refreshed"), 3e3),
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
      n = i(r);
    if (n !== r) return n.replace("{module}", t);
    let a = "cc_reason_" + e.replace(/^[a-z]+\./, ""),
      o = i(a);
    return o === a ? null : o.replace("{module}", t);
  }
  _renderCard(e, t, r) {
    let n = r,
      s = this._sevClass(n.severity),
      a = Re._REAL_PROBE.has(t),
      o = Re._NAVIGABLE.has(t),
      c = e.createEl("div", {
        cls: "pf-cc-card pf-open-module-btn",
        attr: {
          role: "listitem",
          tabindex: "0",
          "data-module": t,
          "aria-label": `${i("cc_module_" + t)} \u2014 ${i(this._ccBadgeKey(n, t))}`,
        },
      }),
      p = c.createEl("div", { cls: "pf-cc-card-header" }),
      u = p.createEl("div", { cls: "pf-cc-card-name-area" });
    if (o) {
      let x =
          t === "installation"
            ? i("module_detail_open_installation")
            : t === "library"
              ? i("module_detail_open_library")
              : t === "ocr"
                ? i("module_detail_open_ocr")
                : t === "memory"
                  ? i("module_detail_open_memory")
                  : t === "help"
                    ? i("module_detail_open_help")
                    : t === "maintenance"
                      ? i("module_detail_open_maintenance")
                      : i("md_select_installation"),
        k = u.createEl("button", {
          cls: "pf-open-module-btn",
          text: i("cc_module_" + t),
          attr: { "data-module": t, "aria-label": x },
        });
      (k.addEventListener("click", () => this._handleCardNavigation(t)),
        k.addEventListener("keydown", (S) => {
          (S.key === "Enter" || S.key === " ") &&
            (S.preventDefault(), this._handleCardNavigation(t));
        }));
    } else
      u.createEl("div", { cls: "pf-cc-card-name", text: i("cc_module_" + t) });
    p.createEl("div", {
      cls: `pf-cc-card-badge pf-cc-card-badge--${s}`,
      text: i(this._ccBadgeKey(n, t)),
    });
    let _;
    if (!a)
      _ = i("cc_reason_placeholder").replace("{module}", i("cc_module_" + t));
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
        let k = Math.round(
            (n.activity_progress.current / n.activity_progress.total) * 100
          ),
          R = x
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
        R.style.width = k + "%";
      }
    }
    let f = c.createEl("div", { cls: "pf-cc-card-footer" });
    if (a && n.action.primary && !Dt(n)) {
      let x = Tt(n),
        S =
          x.kind === "setup"
            ? "pf-cc-card-action pf-cc-card-action--primary"
            : "pf-cc-card-action";
      f.createEl("button", {
        cls: S,
        text: x.label,
        attr: { "aria-label": x.label },
      }).addEventListener("click", () => {
        x.kind === "setup"
          ? new Ce(this.app, this.plugin, () => {
              (this._probeModule("installation"), this._probeModule("help"));
            }).open()
          : this._dispatchModuleAction(t, n);
      });
    }
    let h = c.createEl("details", { cls: "pf-cc-card-diagnostic" });
    h.createEl("summary", { text: i("cc_diagnostic_toggle") });
    let g = h.createEl("div", { cls: "pf-cc-card-diagnostic-body" }),
      y = i("cc_state_" + n.capability_state) || n.capability_state,
      v = i("cc_severity_" + n.severity) || n.severity,
      m = i("cc_activity_" + n.activity_state) || n.activity_state,
      E;
    try {
      E = new Date(n.updated_at).toLocaleString();
    } catch (x) {
      E = n.updated_at;
    }
    (g.createEl("div", { text: `${i("cc_diag_module")}: ${n.module}` }),
      g.createEl("div", { text: `${i("cc_diag_state")}: ${y}` }),
      g.createEl("div", { text: `${i("cc_diag_severity")}: ${v}` }),
      g.createEl("div", { text: `${i("cc_diag_activity")}: ${m}` }));
    let w = g.createEl("div");
    w.appendText(i("cc_diag_reason") + ": " + _ + " ");
    let b = w.createEl("code", { text: n.reason.code });
    (g.createEl("div", {
      text: `${i("cc_diag_ttl")}: ${String(n.ttl_seconds)}s`,
    }),
      g.createEl("div", { text: `${i("cc_diag_updated")}: ${E}` }));
  }
  _handleCardNavigation(e) {
    (e === "help"
      ? ((this.activeTab = "help"),
        (this._selectedDetailModule = ""),
        (this._focusTargetId = "button.pf-open-module-btn[data-module=help]"))
      : e === "maintenance"
        ? ((this.activeTab = "maintenance"),
          (this._selectedDetailModule = ""),
          (this._focusTargetId = "#pf-maintenance-heading"))
        : ((this.activeTab = "module-detail"),
          (this._selectedDetailModule = e),
          (this._focusTargetId = "#pf-" + e + "-detail-heading")),
      this.display());
  }
  _renderControlCenter(e) {
    var w, b, x, k;
    let t = e.createEl("div", { cls: "pf-control-center" }),
      r = (w = this._capabilityState) != null ? w : {},
      n = (b = r.installation) != null ? b : re("installation"),
      s = (x = r.library) != null ? x : re("library"),
      a = n.user_state === "ready",
      o = s.user_state === "ready",
      c = a && o,
      p = [n, s].some((S) => S.user_state === "checking"),
      u = 0,
      _ = r.maintenance;
    _ != null && _.items && Array.isArray(_.items) && (u = _.items.length);
    let f = t.createEl("div", { cls: "pf-cc-summary" }),
      h = c
        ? i("cc_summary_ready")
        : p
          ? i("cc_summary_checking")
          : this.plugin.settings._setup_complete === !1
            ? i("cc_summary_incomplete")
            : i("cc_summary_attention"),
      g = c
        ? i("cc_summary_ready_body")
        : p
          ? i("cc_summary_checking_body")
          : this.plugin.settings._setup_complete === !1
            ? i("cc_summary_incomplete_body")
            : i("cc_summary_attention_body");
    (f.createEl("div", { cls: "pf-cc-summary-title", text: h }),
      f.createEl("div", { cls: "pf-cc-summary-body", text: g }));
    let y = f.createEl("div", { cls: "pf-cc-summary-meta" });
    (u > 0 &&
      y.createEl("span", {
        cls: "pf-cc-summary-maintenance",
        text: i("cc_maintenance_count").replace("{n}", String(u)),
      }),
      y
        .createEl("button", {
          cls: "pf-global-refresh-btn",
          text: i("cc_refresh_btn") || "Refresh Status",
        })
        .addEventListener("click", () => {
          this._refreshAllModules();
        }));
    let m = Object.values(r)
      .map((S) => S.updated_at)
      .filter(Boolean)
      .sort()
      .pop();
    m &&
      y.createEl("span", {
        cls: "pf-last-known",
        text:
          (i("cc_last_checked") || "Last checked: ") +
          new Date(m).toLocaleString(),
      });
    let E = t.createEl("div", {
      cls: "pf-cc-grid",
      attr: { role: "list", "aria-label": i("cc_operational_modules") },
    });
    for (let S of this._getOverviewModules()) {
      let R =
        S.id === "agent"
          ? this._getAgentPlaceholderEnvelope()
          : (k = r[S.id]) != null
            ? k
            : re(S.id);
      this._renderOverviewCard(E, S.id, S.label, R);
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
    let s = e.createDiv({ cls: "pf-cc-card-item", attr: { role: "listitem" } }),
      a = s.createEl("button", {
        cls: "pf-cc-card pf-open-module-btn",
        attr: {
          "data-module": t,
          "aria-label": r + " \u2014 " + this._getUserStateLabel(n.user_state),
        },
      }),
      o = a.createDiv({ cls: "pf-cc-card-header" });
    (o.createEl("span", { cls: "pf-cc-card-title", text: r }),
      Ee(o, n.user_state, this._getUserStateLabel(n.user_state)),
      a.createEl("div", {
        cls: "pf-cc-card-consequence",
        text: this._getModuleConsequence(t, n),
      }),
      n.activity_state === "running" &&
        ct(a, {
          label: i("cc_activity_running"),
          progress: n.activity_progress,
        }),
      n.updated_at &&
        n.updated_at !== new Date(0).toISOString() &&
        a.createEl("div", {
          cls: "pf-cc-card-last-known",
          text: i("cc_last_checked") + new Date(n.updated_at).toLocaleString(),
        }),
      a.addEventListener("click", () => this._handleCardNavigation(t)),
      n.user_state === "detection_failed" &&
        t !== "agent" &&
        s
          .createEl("button", {
            cls: "pf-cc-card-retry",
            text: i("cc_card_retry"),
          })
          .addEventListener("click", () => this._probeModule(t)));
  }
  _getUserStateLabel(e) {
    return i("cc_badge_" + e);
  }
  _getModuleConsequence(e, t) {
    var p, u, _;
    let r =
        (p = t.user_state) != null
          ? p
          : t.capability_state === "ready"
            ? "ready"
            : "action_required",
      n = "cc_consequence_" + e + "_" + r,
      s = i(n);
    if (s && s !== n) return s;
    let a = this._localizeReason(
      (_ = (u = t.reason) == null ? void 0 : u.code) != null ? _ : "",
      this._getUserModuleName(e)
    );
    if (a) return a;
    let o = "cc_consequence_" + r,
      c = i(o);
    return c !== o ? c : i("cc_consequence_default");
  }
  _applyStaleTolerance() {
    if (!this._capabilityState) return;
    let e = !1;
    for (let t of Me) {
      let r = this._capabilityState[t];
      r && st(r) && ((this._capabilityState[t] = at(t)), (e = !0));
    }
    e && this._persistCapabilityState();
  }
  _refreshAllModules() {
    let e = ["installation", "library", "ocr", "memory"];
    for (let t of e) this._probeModule(t);
  }
  _buildAndCopyDiagnostic() {
    var s, a, o;
    let e =
        (a = (s = this.plugin.manifest) == null ? void 0 : s.version) != null
          ? a
          : "unknown",
      t = Vt(
        (o = this._capabilityState) != null ? o : {},
        this._lastKnownState
      ),
      n = It({ pluginVersion: e, modules: t });
    Bt(n, () => {
      new C.Notice(i("support_diagnostic_copied"), 3e3);
    });
  }
  _persistNavMemory() {
    ((this.plugin.settings._navMemory = { ...this._navMemory }),
      this.plugin.saveSettings());
  }
  _renderSetupJourney(e) {
    this.plugin.settings._setup_journey_started !== !0 &&
      ((this.plugin.settings._setup_journey_started = !0),
      this.plugin.saveSettings());
    let t = e.createDiv({ cls: "pf-setup-journey" });
    (t.createEl("h2", { text: i("setup_welcome") }),
      t.createEl("p", { text: i("setup_desc"), cls: "pf-setup-desc" }));
    let r = [
        i("setup_stage_1"),
        i("setup_stage_2"),
        i("setup_stage_3"),
        i("setup_stage_4"),
      ],
      n = t.createDiv({
        cls: "pf-setup-progress",
        attr: { "aria-label": i("setup_progress") },
      });
    r.forEach((a, o) => {
      n.createEl("span", {
        cls:
          "pf-setup-step" +
          (o + 1 === this._setupStage ? " pf-setup-step--active" : "") +
          (o + 1 < this._setupStage ? " pf-setup-step--done" : ""),
        text: String(o + 1) + ". " + a,
        attr: { "aria-current": o + 1 === this._setupStage ? "step" : "false" },
      });
    });
    let s = t.createDiv({ cls: "pf-setup-body" });
    this._setupStage === 1
      ? this._renderSetupStageFoundation(s)
      : this._setupStage === 2
        ? this._renderSetupStageLibrary(s)
        : this._setupStage === 3
          ? this._renderSetupStageOptionals(s)
          : this._renderSetupStageReview(s);
  }
  _renderSetupStageFoundation(e) {
    var n, s, a;
    let t =
      (s = (n = this._capabilityState) == null ? void 0 : n.installation) !=
      null
        ? s
        : re("installation");
    if (
      (e.createEl("h3", { text: i("setup_foundation_title") }),
      e.createEl("p", { text: i("setup_foundation_desc") }),
      Ee(e, t.user_state, this._getUserStateLabel(t.user_state)),
      e.createEl("p", {
        text:
          t.user_state === "ready"
            ? i("setup_ready")
            : this._getModuleConsequence("installation", t),
        cls: t.user_state === "ready" ? "pf-setup-ok" : "pf-setup-status",
      }),
      (a = t.action) != null && a.primary && t.user_state !== "ready")
    ) {
      let o = "cc_action_" + t.action.primary.verb;
      W(e, {
        label: i(o) === o ? i("cc_action_setup") : i(o),
        onClick: () =>
          this._runAllowedDispatch(
            "installation",
            t.action.primary.verb,
            t.action.primary.command,
            t
          ),
      });
    }
    let r = e.createDiv({ cls: "pf-setup-nav" });
    W(r, {
      label: i("setup_nav_continue"),
      disabled: t.user_state !== "ready",
      onClick: () => {
        ((this._setupStage = 2), this.display());
      },
    });
  }
  _renderSetupStageLibrary(e) {
    var n, s, a;
    let t =
      (s = (n = this._capabilityState) == null ? void 0 : n.library) != null
        ? s
        : re("library");
    if (
      (e.createEl("h3", { text: i("setup_library_title") }),
      e.createEl("p", { text: i("setup_library_desc") }),
      Ee(e, t.user_state, this._getUserStateLabel(t.user_state)),
      e.createEl("p", {
        text:
          t.user_state === "ready"
            ? i("setup_library_ready")
            : this._getModuleConsequence("library", t),
        cls: t.user_state === "ready" ? "pf-setup-ok" : "pf-setup-status",
      }),
      (a = t.action) != null && a.primary && t.user_state !== "ready")
    ) {
      let o = "cc_action_" + t.action.primary.verb;
      W(e, {
        label: i(o) === o ? i("cc_action_set_config") : i(o),
        onClick: () =>
          this._runAllowedDispatch(
            "library",
            t.action.primary.verb,
            t.action.primary.command,
            t
          ),
      });
    }
    let r = e.createDiv({ cls: "pf-setup-nav" });
    (W(r, {
      label: i("setup_nav_back"),
      onClick: () => {
        ((this._setupStage = 1), this.display());
      },
    }),
      W(r, {
        label: i("setup_nav_continue"),
        disabled: t.user_state !== "ready",
        onClick: () => {
          ((this._setupStage = 3), this.display());
        },
      }));
  }
  _renderSetupStageOptionals(e) {
    (e.createEl("h3", { text: i("setup_optionals_title") }),
      e.createEl("p", { text: i("setup_optionals_desc") }));
    let t = [
      { id: "ocr", label: i("cc_module_ocr"), desc: i("setup_opt_ocr_desc") },
      {
        id: "memory",
        label: i("cc_module_memory"),
        desc: i("setup_opt_memory_desc"),
      },
      {
        id: "agent",
        label: i("cc_module_agent"),
        desc: i("setup_opt_agent_desc"),
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
        }));
      let o = s.createDiv({ cls: "pf-setup-optional-copy" });
      (o.createEl("label", {
        attr: { for: "pf-setup-opt-" + n.id },
        text: n.label,
        cls: "pf-setup-optional-label",
      }),
        o.createEl("div", { text: n.desc, cls: "pf-setup-optional-desc" }));
    }
    let r = e.createDiv({ cls: "pf-setup-nav" });
    (W(r, {
      label: i("setup_nav_back"),
      onClick: () => {
        ((this._setupStage = 2), this.display());
      },
    }),
      W(r, {
        label: i("setup_nav_continue"),
        onClick: () => {
          ((this._setupStage = 4), this.display());
        },
      }));
  }
  _renderSetupStageReview(e) {
    var a, o, c, p;
    e.createEl("h3", { text: i("setup_review_title") });
    let t =
        ((o = (a = this._capabilityState) == null ? void 0 : a.installation) ==
        null
          ? void 0
          : o.user_state) === "ready",
      r =
        ((p = (c = this._capabilityState) == null ? void 0 : c.library) == null
          ? void 0
          : p.user_state) === "ready";
    (e.createEl("p", {
      text: t ? i("setup_ready") : i("cc_consequence_setup_required"),
      cls: t ? "pf-setup-ok" : "pf-setup-warn",
    }),
      e.createEl("p", {
        text: r ? i("setup_library_ready") : i("cc_consequence_setup_required"),
        cls: r ? "pf-setup-ok" : "pf-setup-warn",
      }));
    let n = Object.entries(this._setupOptionals)
      .filter(([, u]) => u)
      .map(([u]) => this._getUserModuleName(u));
    e.createEl("p", {
      text:
        n.length > 0
          ? i("setup_review_selected") + n.join(", ")
          : i("setup_no_optionals"),
    });
    let s = e.createDiv({ cls: "pf-setup-nav" });
    (W(s, {
      label: i("setup_nav_back"),
      onClick: () => {
        ((this._setupStage = 3), this.display());
      },
    }),
      W(s, {
        label: i("setup_nav_complete"),
        disabled: !t || !r,
        onClick: () => this._completeSetup(),
      }),
      (!t || !r) &&
        e.createEl("p", {
          text: i("setup_incomplete_warn"),
          cls: "pf-setup-warn",
        }));
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
((Re._REAL_PROBE = new Set([
  "installation",
  "library",
  "ocr",
  "memory",
  "help",
  "maintenance",
])),
  (Re._NAVIGABLE = new Set([
    "installation",
    "library",
    "ocr",
    "memory",
    "maintenance",
    "help",
  ])));
var Xe = Re;
var F = require("obsidian"),
  ye = H(require("fs")),
  Qe = H(require("path")),
  ue = require("child_process");
var He = H(require("path"));
function lr(d) {
  if (!d) return null;
  let l = He.dirname(d);
  for (;;) {
    let e = He.basename(l);
    if (!e || e === ".") break;
    let t = e.match(/^([A-Z0-9]{8})(?:\s*-\s*.*)?$/i);
    if (t) return t[1];
    let r = He.dirname(l);
    if (r === l) break;
    l = r;
  }
  return null;
}
var z = H(require("fs")),
  he = H(require("path"));
function Ve(d) {
  return ae(d).ocrDir;
}
function Vr(d, l) {
  let e = he.join(Ve(d), l, "versions", "manifest.json");
  try {
    if (!z.existsSync(e)) return null;
    let t = z.readFileSync(e, "utf-8"),
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
function jr(d) {
  let l = Ve(d);
  try {
    return z.existsSync(l)
      ? z
          .readdirSync(l, { withFileTypes: !0 })
          .filter((e) => e.isDirectory())
          .map((e) => e.name)
      : [];
  } catch (e) {
    return [];
  }
}
function vt(d) {
  let l = jr(d),
    e = [];
  for (let t of l) {
    let r = Vr(d, t);
    if (!r) continue;
    let n = r.versions.map((a) => a.label),
      s = 0;
    for (let a of n) {
      let o = he.join(Ve(d), t, "versions", a, "fulltext.md");
      try {
        z.existsSync(o) && (s += z.statSync(o).size);
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
function pr(d, l, e) {
  let t = Ve(d),
    r = he.join(t, l, "versions", e, "fulltext.md"),
    n = he.join(t, l, "render"),
    s = he.join(n, "fulltext.md");
  try {
    return z.existsSync(r)
      ? (z.existsSync(n) || z.mkdirSync(n, { recursive: !0 }),
        z.copyFileSync(r, s),
        !0)
      : !1;
  } catch (a) {
    return !1;
  }
}
function dr(d, l, e, t) {
  var f;
  let r = Ve(d),
    n = he.join(r, l, "versions", e, "fulltext.md"),
    s = he.join(r, l, "versions", t, "fulltext.md"),
    a = "",
    o = "";
  try {
    z.existsSync(n) && (a = z.readFileSync(n, "utf-8"));
  } catch (h) {}
  try {
    z.existsSync(s) && (o = z.readFileSync(s, "utf-8"));
  } catch (h) {}
  let c = cr(a),
    p = cr(o),
    u = Math.max(c.length, p.length),
    _ = [];
  for (let h = 0; h < u; h++) {
    let g = h < c.length ? c[h] : "",
      y = h < p.length ? p[h] : "",
      v =
        (f = (g || y).split(`
`)[0]) != null
          ? f
          : "",
      m = v.startsWith("## ") ? v.replace(/^##\s+/, "") : "",
      E = "unchanged";
    (!g && y
      ? (E = "added")
      : g && !y
        ? (E = "removed")
        : g !== y && (E = "changed"),
      E !== "unchanged" &&
        _.push({
          paragraphIndex: h,
          heading: m,
          type: E,
          oldText: g || void 0,
          newText: y || void 0,
        }));
  }
  return _;
}
function cr(d) {
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
var Fe = class extends F.ItemView {
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
    let r = fe(t.current());
    return r ? { path: r.command, args: [...r.args] } : null;
  }
  getViewType() {
    return ge;
  }
  getDisplayText() {
    return "PaperForge";
  }
  getIcon() {
    return Le;
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
    var o;
    let e = this.app.vault.adapter.basePath,
      t = this.app.plugins.plugins.paperforge,
      r =
        ((o = t == null ? void 0 : t.manifest) == null ? void 0 : o.version) ||
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
              i("dashboard_drift_warning")
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
    (0, ue.execFile)(
      s,
      [...a, "-m", "paperforge", "dashboard", "--json"],
      { cwd: t, timeout: 3e4 },
      (o, c) => {
        if (!o)
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
    var a, o;
    let n =
        ((a = r == null ? void 0 : r.settings) == null
          ? void 0
          : a.system_dir) || "System",
      s = Qe.join(t, n, "PaperForge", "indexes", "formal-library.json");
    try {
      let c = ye.readFileSync(s, "utf-8"),
        p = JSON.parse(c),
        u = p.items || [],
        _ = {},
        f = {
          pdf_health: { healthy: 0, unhealthy: 0 },
          ocr_health: { healthy: 0, unhealthy: 0 },
          note_health: { healthy: 0, unhealthy: 0 },
          asset_health: { healthy: 0, unhealthy: 0 },
        },
        h = 0,
        g = 0,
        y = 0,
        v = 0,
        m = 0,
        E = 0;
      for (let w of u) {
        w.note_path && E++;
        let b = w.lifecycle || "pdf_ready";
        _[b] = (_[b] || 0) + 1;
        let x = w.health || {};
        for (let S of [
          "pdf_health",
          "ocr_health",
          "note_health",
          "asset_health",
        ])
          (x[S] || "healthy") === "healthy" ? f[S].healthy++ : f[S].unhealthy++;
        let k = w.ocr_status || "";
        (h++,
          k === "done"
            ? g++
            : k === "pending"
              ? y++
              : k === "processing" || k === "queued" || k === "running"
                ? v++
                : m++);
      }
      ((this._cachedStats = {
        version:
          p.paperforge_version ||
          ((o = this._cachedStats) == null ? void 0 : o.version) ||
          "\u2014",
        total_papers: u.length,
        formal_notes: E,
        exports: 0,
        bases: 0,
        ocr: { total: h, pending: y, processing: v, done: g, failed: m },
        path_errors: 0,
        lifecycle_level_counts: _,
        health_aggregate: f,
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
      (0, ue.execFile)(
        u,
        [..._, "-m", "paperforge", "status", "--json"],
        { cwd: t, timeout: 3e4 },
        (f, h) => {
          if (f) {
            if (this._cachedStats) return;
            this._metricsEl.createEl("div", {
              cls: "paperforge-status-error",
              text: `Cannot reach PaperForge CLI.
Make sure paperforge is installed and in your PATH.`,
            });
            return;
          }
          try {
            let g = JSON.parse(h);
            ((this._cachedStats = g),
              this._metricsEl.empty(),
              this._renderStats(g),
              this._renderOcr(g));
          } catch (g) {
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
      n = Qe.join(e, r, "PaperForge", "indexes", "formal-library.json");
    try {
      let a = ye.readFileSync(n, "utf-8");
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
    return Ft(this.app, t);
  }
  _patchCachedEntry(e, t) {
    if (!e || !this._cachedItems) return;
    let r = this._cachedItems.findIndex((n) => n.zotero_key === e);
    r !== -1 && (this._cachedItems[r] = rt(this._cachedItems[r], t));
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
    for (let o of n) {
      let c = this._metricsEl.createEl("div", {
        cls: "paperforge-metric-card",
      });
      (c.style.setProperty("--metric-color", o.color),
        c.createEl("div", {
          cls: "paperforge-metric-value",
          text: ((a = o.value) == null ? void 0 : a.toString()) || "\u2014",
        }),
        c.createEl("div", { cls: "paperforge-metric-label", text: o.label }),
        o.barMax > 0 && this._buildMetricBar(c, o.value, o.barMax));
    }
    let s = e.ocr_version_state || {};
    if (
      s.total_papers > 0 &&
      (s.derived_stale_count > 0 || s.raw_upgradable_count > 0)
    ) {
      let o = [];
      (s.derived_stale_count > 0 && o.push(`${s.derived_stale_count} stale`),
        s.raw_upgradable_count > 0 &&
          o.push(`${s.raw_upgradable_count} upgradable`));
      let c = this._metricsEl.createEl("div", {
        cls: "paperforge-metric-card",
      });
      (c.style.setProperty("--metric-color", "var(--color-yellow)"),
        c.createEl("div", {
          cls: "paperforge-metric-value",
          text: o.join(", "),
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
      o = t.failed || 0;
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
        { cls: "failed", count: o },
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
        { cls: "failed", value: o, label: "Failed" },
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
    for (let o of n) {
      let c = s.createEl("div", { cls: "step" });
      (c.createEl("div", { cls: "step-indicator" }),
        c.createEl("div", { cls: "step-label", text: o.label }),
        o.key === r
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
        o = n.createEl("div", { cls: "paperforge-health-cell" }),
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
        o.addClass(p),
        o.setAttribute("title", u),
        o.createEl("div", { cls: "paperforge-health-cell-icon", text: c }),
        o.createEl("div", {
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
      o = Math.max(1, Math.min(a, Math.round(t)));
    for (let c = 1; c <= a; c++) {
      let p = s.createEl("div", { cls: "gauge-segment" });
      c <= o && (p.addClass("filled"), p.addClass(`level-${c}`));
    }
    if (
      (n.createEl("div", { cls: "gauge-level", text: `Level ${o} / ${a}` }),
      o < a && r)
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
      let o = t[a.key] || 0,
        c = (o / s) * 100,
        p = n.createEl("div", { cls: "bar-row" });
      (p.createEl("div", { cls: "bar-label", text: a.label }),
        p
          .createEl("div", { cls: "bar-track" })
          .createEl("div", {
            cls: `bar-fill ${a.cls}`,
            attr: { style: `width:${c.toFixed(1)}%` },
          }),
        p.createEl("div", { cls: "bar-count", text: o.toString() }));
    }
  }
  _invalidateIndex() {
    this._cachedItems = null;
  }
  _extractZoteroKeyFromPath(e) {
    return lr(e);
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
        let o = (a.pdf_path || "").match(/\[\[([^\]]+)\]\]/);
        if ((o ? o[1] : a.pdf_path) === r)
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
    var se, be, oe, U, Et, xt, kt;
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
    for (let A of t)
      (A.has_pdf && n++,
        A.ocr_status === "done" && s++,
        A.deep_reading_status === "done" && a++);
    let o = e.createEl("div", { cls: "paperforge-library-snapshot" });
    o.createEl("div", {
      cls: "paperforge-section-label",
      text: "Library Snapshot",
    });
    let c = o.createEl("div", { cls: "paperforge-snapshot-pills" }),
      p = [
        { value: r, label: "papers" },
        { value: n, label: "PDFs ready" },
        { value: s, label: "OCR done" },
        { value: a, label: "deep-read done" },
      ];
    for (let A of p) {
      let N = c.createEl("div", { cls: "paperforge-snapshot-pill" });
      (N.createEl("span", {
        cls: "paperforge-snapshot-value",
        text: String(A.value),
      }),
        N.createEl("span", {
          cls: "paperforge-snapshot-label",
          text: " " + A.label,
        }));
    }
    let u = e.createEl("div", { cls: "paperforge-system-status" });
    u.createEl("div", {
      cls: "paperforge-section-label",
      text: "System Status",
    });
    let _ = u.createEl("div", { cls: "paperforge-status-grid" }),
      f = this.app.plugins.plugins.paperforge,
      h =
        ((se = f == null ? void 0 : f.manifest) == null
          ? void 0
          : se.version) || "?",
      g = this._paperforgeVersion;
    if (!g) {
      let A = this._resolvePython();
      if (A) {
        let { path: N, args: le = [] } = A;
        try {
          let ie = this.app.vault.adapter.basePath,
            X = (0, ue.execFileSync)(
              N,
              [...le, "-c", "import paperforge; print(paperforge.__version__)"],
              { cwd: ie, timeout: 5e3, encoding: "utf-8", windowsHide: !0 }
            ).trim();
          X &&
            ((g = X.startsWith("v") ? X : "v" + X),
            (this._paperforgeVersion = g));
        } catch (ie) {}
      }
    }
    g = g || "\u2014";
    let y = g === "v" + h;
    this._renderSystemStatusRow(
      _,
      "Runtime",
      y ? "healthy" : "mismatch",
      y ? "v" + h : "plugin v" + h + " \u2260 CLI " + g
    );
    let v = this._loadIndex(),
      m = v && v.items && v.items.length > 0;
    this._renderSystemStatusRow(
      _,
      "Index",
      m ? "healthy" : "missing",
      m ? v.items.length + " entries" : "formal-library.json not found"
    );
    let E =
        ((be = f == null ? void 0 : f.settings) == null
          ? void 0
          : be.system_dir) || "System",
      w = this.app.vault.adapter.basePath,
      b = !1,
      x = "No exports found";
    try {
      let A = Qe.join(w, E, "PaperForge", "exports");
      if (ye.existsSync(A)) {
        let N = ye.readdirSync(A).filter((le) => le.endsWith(".json"));
        ((b = N.length > 0),
          (x = b ? N.length + " export(s)" : "No JSON exports"));
      }
    } catch (A) {}
    this._renderSystemStatusRow(
      _,
      "Zotero Export",
      b ? "healthy" : "missing",
      x
    );
    let k =
        (U = (oe = this.app.plugins) == null ? void 0 : oe.plugins) == null
          ? void 0
          : U.paperforge,
      S = !!(
        (Et = k == null ? void 0 : k.settings) != null &&
        Et._paddleocr_configured
      );
    this._renderSystemStatusRow(
      _,
      "OCR Token",
      S ? "configured" : "missing",
      S ? "Configured" : "Not set"
    );
    let R = !1,
      V = "",
      M = this.app.vault.adapter.basePath,
      I = Be(M);
    ((R = Gt(M)),
      (V =
        (I && ((xt = I.summary) == null ? void 0 : xt.reason)) ||
        (I && ((kt = I.summary) == null ? void 0 : kt.status)) ||
        "Unknown"),
      this._renderSystemStatusRow(
        _,
        "Memory Layer",
        R ? "healthy" : "fail",
        V
      ));
    let O = !y && g !== "\u2014";
    if (O || !m || !b || !S) {
      let A = e.createEl("div", { cls: "paperforge-issue-summary" });
      A.createEl("div", {
        cls: "paperforge-section-label",
        text: "\u9700\u8981\u5904\u7406",
      });
      let N = A.createEl("div", { cls: "paperforge-issue-list" });
      (O &&
        N.createEl("div", {
          cls: "paperforge-issue-item",
          text: "Runtime version mismatch",
        }),
        m ||
          N.createEl("div", {
            cls: "paperforge-issue-item",
            text: "Index missing or corrupted",
          }),
        b ||
          N.createEl("div", {
            cls: "paperforge-issue-item",
            text: "No Zotero export found",
          }),
        S ||
          N.createEl("div", {
            cls: "paperforge-issue-item",
            text: "PaddleOCR API key not configured",
          }));
      let le = A.createEl("div", { cls: "paperforge-issue-actions" }),
        ie = le.createEl("button", { cls: "paperforge-contextual-btn" });
      (ie.createEl("span", { text: "Run Doctor" }),
        ie.addEventListener("click", () => {
          let Te = Q.find((tt) => tt.id === "paperforge-doctor");
          Te && this._runAction(Te, ie);
        }));
      let X = le.createEl("button", { cls: "paperforge-contextual-btn" });
      (X.createEl("span", { text: "Repair Issues" }),
        X.addEventListener("click", () => {
          let Te = Q.find((tt) => tt.id === "paperforge-repair");
          Te && this._runAction(Te, X);
        }));
    }
    let P = e.createEl("div", { cls: "paperforge-global-actions" });
    P.createEl("div", {
      cls: "paperforge-section-label",
      text: "Start Working",
    });
    let B = P.createEl("div", { cls: "paperforge-global-actions-row" }),
      Y = B.createEl("button", { cls: "paperforge-contextual-btn primary" });
    (Y.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u{1F4C1}",
    }),
      Y.createEl("span", { text: "Open Literature Hub" }),
      Y.addEventListener("click", () => {
        var le;
        let A =
            ((le = f == null ? void 0 : f.settings) == null
              ? void 0
              : le.base_dir) || "Bases",
          N = this.app.vault.getAbstractFileByPath(A);
        if (N) {
          let ie = null;
          if (
            (N.children &&
              (ie = N.children.find((X) => X.extension === "base")),
            ie)
          ) {
            let X = this.app.workspace.getLeaf(!1);
            X && X.openFile(ie);
          } else new F.Notice("[!!] No .base file found in " + A, 6e3);
        } else new F.Notice("[!!] Base directory not found: " + A, 6e3);
      }));
    let J = B.createEl("button", { cls: "paperforge-contextual-btn" });
    (J.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    }),
      J.createEl("span", { text: "Sync Library" }),
      J.addEventListener("click", () => {
        let A = Q.find((N) => N.id === "paperforge-sync");
        A && this._runAction(A, J);
      }));
    let T = B.createEl("button", { cls: "paperforge-contextual-btn" });
    (T.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    }),
      T.createEl("span", { text: "Run OCR" }),
      T.addEventListener("click", () => {
        let A = Q.find((N) => N.id === "paperforge-ocr");
        A && this._runAction(A, T);
      }));
    let te = B.createEl("button", { cls: "paperforge-contextual-btn warn" });
    (te.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BA",
    }),
      te.createEl("span", { text: "Redo OCR" }),
      te.addEventListener("click", () => {
        let A = Q.find((N) => N.id === "paperforge-ocr-redo");
        A && this._runAction(A, te);
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
        new F.Notice("Title copied"));
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
    let o = r.createEl("div", { cls: "paperforge-status-strip" }),
      c = o.createEl("div", { cls: "paperforge-status-strip-left" }),
      p = o.createEl("div", { cls: "paperforge-status-strip-right" }),
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
    for (let f of u) {
      let h = c.createEl("span", { cls: "paperforge-status-pill" }),
        g = "pending";
      (f.ok ? (g = "ok") : f.fail ? (g = "fail") : f.pending && (g = "pending"),
        h.addClass(g));
      let y = f.ok ? "\u2713" : f.fail ? "\u2717" : "\u25CB";
      (h.createEl("span", { cls: "paperforge-status-pill-icon", text: y }),
        h.createEl("span", { text: " " + f.label }));
    }
    if (e.pdf_path) {
      let f = p.createEl("button", { cls: "paperforge-contextual-btn" });
      (f.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\u{1F4C4}",
      }),
        f.createEl("span", { text: "\u6253\u5F00 PDF" }),
        f.addEventListener("click", () => {
          let h = e.pdf_path.match(/\[\[([^\]]+)\]\]/),
            g = h ? h[1] : e.pdf_path;
          this.app.vault.getAbstractFileByPath(g)
            ? this.app.workspace.openLinkText(g, "")
            : new F.Notice("[!!] PDF not found: " + g, 6e3);
        }));
    }
    if (e.fulltext_path) {
      let f = p.createEl("button", { cls: "paperforge-contextual-btn" });
      (f.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\u{1F4DD}",
      }),
        f.createEl("span", { text: "\u6253\u5F00\u5168\u6587" }),
        f.addEventListener("click", () => this._openFulltext(e.fulltext_path)));
    }
    let _ = p.createEl("button", { cls: "paperforge-contextual-btn" });
    if (
      (_.createEl("span", { text: i("version_panel_title") }),
      _.addEventListener("click", () => {
        this._switchToVersionMode(t);
      }),
      this._renderPaperOverviewCard(r, e),
      e.next_step === "ready" && e.deep_reading_status === "done")
    ) {
      let f = r.createEl("div", { cls: "paperforge-complete-row" });
      (f.createEl("span", { text: "\u2713" }),
        f.createEl("span", {
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
      let o = this.app.vault.getAbstractFileByPath(t.note_path);
      o
        ? this.app.vault
            .read(o)
            .then((c) => {
              let p = this._extractOverviewFromNote(c);
              if (p) {
                let u = p.length > 200 ? p.slice(0, 200) + "..." : p;
                if ((a.setText(u), p.length > 200)) {
                  let _ = s.createEl("div", {
                      cls: "paperforge-expand-container",
                    }),
                    f = _.createEl("button", {
                      cls: "paperforge-expand-icon",
                      title: "\u5C55\u5F00/\u6536\u8D77",
                    });
                  f.innerHTML =
                    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>';
                  let h = !1;
                  _.addEventListener("click", () => {
                    (a.setText(h ? u : p),
                      (f.innerHTML = h
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
    for (let o of n) {
      let c = r.indexOf(o);
      if (c !== -1) {
        let p = r.slice(c + o.length),
          u = ["**5 Cs", "**Figure", "**\u8BC1\u636E", "### Pass 2", "## "],
          _ = p.length;
        for (let g of u) {
          let y = p.indexOf(g);
          y !== -1 && y < _ && (_ = y);
        }
        let f = p.indexOf(`

`);
        f !== -1 && f < _ && (_ = f);
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
      .then((o) => {
        if (o) return this.app.vault.adapter.read(a);
      })
      .then(async (o) => {
        if (!o) return;
        let c = this._parseDiscussionMD(o);
        if (!c || c.length === 0) return;
        ((r.style.display = "block"),
          r
            .createEl("div", { cls: "paperforge-discussion-header" })
            .createEl("span", {
              cls: "paperforge-discussion-title",
              text: "\u6700\u8FD1\u8BA8\u8BBA",
            }));
        for (let _ of c) {
          let f = r.createEl("div", { cls: "paperforge-discussion-item" }),
            h = f.createEl("div", { cls: "paperforge-discussion-q" });
          (h.createEl("span", {
            cls: "paperforge-discussion-q-label",
            text: "\u63D0\u95EE\uFF1A",
          }),
            h.createEl("span", {
              cls: "paperforge-discussion-q-text",
              text: _.question,
            }));
          let g = f.createEl("div", { cls: "paperforge-discussion-a" }),
            y = !1;
          if (
            (_.answer &&
              _.answer.length > 500 &&
              ((y = !0), g.classList.add("paperforge-discussion-a-collapsed")),
            await F.MarkdownRenderer.render(
              this.app,
              _.answer || "",
              g,
              a,
              this
            ),
            y)
          ) {
            let v = !1;
            ((f.style.cursor = "pointer"),
              f.addEventListener("click", () => {
                ((v = !v),
                  g.classList.toggle("paperforge-discussion-a-collapsed", !v),
                  g.classList.toggle("paperforge-discussion-a-expanded", v));
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
              : new F.Notice(
                  "\u8BA8\u8BBA\u6587\u4EF6\u5C1A\u672A\u751F\u6210"
                ));
        });
      })
      .catch((o) => {
        console.error("PaperForge: discussion.md read error", a, o.message);
      });
  }
  _parseDiscussionMD(e) {
    let t = e.split(/\n## /).slice(1);
    if (t.length === 0) return null;
    let r = t[t.length - 1],
      n = [],
      s = r.split(/\*\*\u95EE\u9898:\*\*/).slice(1);
    for (let a of s) {
      let o = a.match(/\*\*\u89E3\u7B54:\*\*/);
      if (!o) continue;
      let c = a.substring(0, o.index).trim(),
        p = a.substring(o.index + 3 + 4).trim();
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
        let f = a.style.display !== "none";
        ((a.style.display = f ? "none" : "block"),
          s.setText(
            f
              ? "\u6280\u672F\u8BE6\u60C5 \u25B8"
              : "\u6280\u672F\u8BE6\u60C5 \u25BE"
          ),
          (this._techDetailsExpanded = !f));
      }));
    let o = a.createEl("div", { cls: "paperforge-workflow-toggles" }),
      c = [
        { key: "do_ocr", label: "OCR", hint: "\u52A0\u5165 OCR" },
        {
          key: "analyze",
          label: "\u7CBE\u8BFB",
          hint: "\u6807\u8BB0\u7CBE\u8BFB",
        },
      ];
    for (let f of c) {
      let h = o.createEl("label", { cls: "paperforge-workflow-toggle" }),
        g = h.createEl("input", {
          type: "checkbox",
          cls: "paperforge-workflow-checkbox",
        });
      ((g.checked = t[f.key] === !0),
        h.createEl("span", {
          cls: "paperforge-workflow-toggle-label",
          text: f.label,
        }),
        h.createEl("span", {
          cls: "paperforge-workflow-toggle-hint",
          text: f.hint,
        }),
        g.addEventListener("change", async () => {
          let y = t.note_path
            ? this.app.vault.getAbstractFileByPath(t.note_path)
            : null;
          if (!y) {
            new F.Notice("[!!] Note file not found", 6e3);
            return;
          }
          let v = g.checked;
          (await this.app.fileManager.processFrontMatter(y, (m) => {
            m[f.key] = v;
          }),
            this._patchCachedEntry(r, { [f.key]: v }),
            (this._currentPaperEntry = rt(this._currentPaperEntry, {
              [f.key]: v,
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
    for (let [f, h] of u) {
      let g = a.createEl("div", { cls: "paperforge-technical-row" });
      g.createEl("span", { cls: "paperforge-technical-label", text: f });
      let y = g.createEl("span", {
        cls: "paperforge-technical-value",
        text: String(h),
      });
      _.has(f) &&
        h &&
        h !== "\u2014" &&
        (y.addClass("pf-copy"),
        y.addEventListener("click", () => {
          (navigator.clipboard.writeText(h), new F.Notice(f + " copied"));
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
      o = e.createEl("div", { cls: "paperforge-next-step-card" });
    if (
      (n === "ready" && o.addClass("ready"),
      o.createEl("div", {
        cls: "paperforge-next-step-label",
        text: "Recommended Next Step",
      }),
      o.createEl("div", { cls: "paperforge-next-step-text", text: a.text }),
      a.cmd && a.cmd !== "ready")
    ) {
      let u = o.createEl("button", { cls: "paperforge-next-step-trigger" });
      (u.createEl("span", { text: a.icon + "  " + a.label }),
        u.addEventListener("click", () => {
          let _ = Q.find((f) => f.cmd === a.cmd);
          _ && this._runAction(_, u);
        }));
    } else if (n === "/pf-deep") {
      let u = o.createEl("button", { cls: "paperforge-next-step-trigger" });
      (u.createEl("span", { text: "\u{1F4CB}  " + i("copy_pf_deep_cmd") }),
        u.addEventListener("click", () => {
          let y = "/pf-deep " + r;
          navigator.clipboard
            .writeText(y)
            .then(() => {
              (u.setText("\u2713  " + i("copied")),
                new F.Notice(y + " copied"));
            })
            .catch(() => {
              new F.Notice("[!!] Clipboard write failed", 6e3);
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
      o.createEl("div", { cls: "paperforge-agent-platform-label" }).setText(
        i("run_in_agent").replace("{0}", h)
      );
    } else
      n === "ready" &&
        o
          .createEl("button", { cls: "paperforge-next-step-trigger" })
          .createEl("span", { text: "\u2713  " + a.label });
  }
  _openFulltext(e) {
    if (!e) {
      new F.Notice("[!!] No fulltext path available for this paper", 6e3);
      return;
    }
    let t = this.app.vault.getAbstractFileByPath(e);
    t
      ? this.app.workspace.openLinkText(t.path, "")
      : new F.Notice("[!!] Fulltext file not found: " + e, 6e3);
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
      o = 0,
      c = 0,
      p = 0,
      u = 0,
      _ = 0;
    for (let b of t) {
      (b.has_pdf && s++,
        b.ocr_status === "done" && a++,
        b.ocr_status === "done" && b.analyze === !0 && o++,
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
    let g = h.createEl("div", { cls: "paperforge-workflow-funnel" }),
      y = [
        { value: n, label: "Total" },
        { value: s, label: "PDF Ready" },
        { value: a, label: "OCR Done" },
        { value: c, label: "Deep Read" },
      ];
    for (let b = 0; b < y.length; b++) {
      let x = g.createEl("div", { cls: "paperforge-workflow-stage" });
      (x.createEl("div", {
        cls: "paperforge-workflow-stage-value",
        text: String(y[b].value),
      }),
        x.createEl("div", {
          cls: "paperforge-workflow-stage-label",
          text: y[b].label,
        }),
        b < y.length - 1 &&
          g.createEl("div", {
            cls: "paperforge-workflow-arrow",
            text: "\u2192",
          }));
    }
    if (p + u + a + _ > 0) {
      let b = r.createEl("div", { cls: "paperforge-ocr-section" }),
        x = b.createEl("div", { cls: "paperforge-collection-ocr-header" });
      x.createEl("h4", { cls: "paperforge-ocr-title", text: "OCR Pipeline" });
      let k = x.createEl("span", { cls: "paperforge-ocr-badge idle" });
      u > 0
        ? (k.addClass("active"), k.setText("Processing"))
        : p > 0
          ? k.setText("Pending")
          : (k.addClass("idle"), k.setText("Idle"));
      let S = b.createEl("div", { cls: "paperforge-progress-track" });
      u > 0 && S.addClass("paperforge-processing");
      let R = p + u + a + _,
        V = [
          { cls: "pending", count: p },
          { cls: "active", count: u },
          { cls: "done", count: a },
          { cls: "failed", count: _ },
        ];
      for (let O of V)
        if (O.count > 0) {
          let D = ((O.count / R) * 100).toFixed(1);
          S.createEl("div", {
            cls: `paperforge-progress-seg ${O.cls}`,
            attr: { style: `width:${D}%` },
          });
        }
      let M = b.createEl("div", { cls: "paperforge-ocr-counts" }),
        I = [
          { cls: "pending", value: p, label: "Pending" },
          { cls: "active", value: u, label: "Processing" },
          { cls: "done", value: a, label: "Done" },
          { cls: "failed", value: _, label: "Attention" },
        ];
      for (let O of I) {
        let D = M.createEl("div", { cls: "paperforge-ocr-count" });
        (D.createEl("div", {
          cls: "paperforge-ocr-count-value",
          text: O.value.toString(),
        }),
          D.createEl("div", {
            cls: "paperforge-ocr-count-label",
            text: O.label,
          }));
      }
    }
    let v = r.createEl("div", { cls: "paperforge-collection-actions" }),
      m = v.createEl("button", { cls: "paperforge-contextual-btn primary" });
    (m.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    }),
      m.createEl("span", { text: "Run OCR" }),
      m.addEventListener("click", () => {
        let b = Q.find((x) => x.id === "paperforge-ocr");
        b && this._runAction(b, m);
      }));
    let E = v.createEl("button", { cls: "paperforge-contextual-btn" });
    (E.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    }),
      E.createEl("span", { text: "Sync Library" }),
      E.addEventListener("click", () => {
        let b = Q.find((x) => x.id === "paperforge-sync");
        b && this._runAction(b, E);
      }));
    let w = v.createEl("button", { cls: "paperforge-contextual-btn warn" });
    (w.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BA",
    }),
      w.createEl("span", { text: "Redo OCR" }),
      w.addEventListener("click", () => {
        let b = Q.find((x) => x.id === "paperforge-ocr-redo");
        b && this._runAction(b, w);
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
      new F.Notice("Cannot determine vault path");
      return;
    }
    ((this._versionPapers = vt(n)),
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
      (this._versionPapers = vt(n));
    let s = e.createEl("div", { cls: "paperforge-version-left" }),
      a = e.createEl("div", { cls: "paperforge-version-right" }),
      o = s.createEl("input", {
        cls: "paperforge-version-filter",
        attr: { type: "text", placeholder: i("version_filter_placeholder") },
      });
    o.value = this._versionFilter;
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
            text: i("version_no_backups"),
          });
          return;
        }
        let w = c.createEl("div", {
          cls: "paperforge-meta",
          text: i("version_papers_count").replace("{n}", String(E.length)),
        });
        for (let b of E) {
          let x = c.createEl("div", { cls: "paperforge-version-paper-item" }),
            k = x.createEl("span", {
              cls: "paperforge-version-paper-title",
              text: b.title,
            }),
            S = x.createEl("span", {
              cls: "paperforge-version-paper-versions",
              text: b.versions.map((R) => R.label).join(" "),
            });
          x.addEventListener("click", () => {
            (c
              .querySelectorAll(".paperforge-version-paper-item.selected")
              .forEach((R) => R.removeClass("selected")),
              x.addClass("selected"),
              _(b));
          });
        }
      };
    o.addEventListener("input", () => {
      ((this._versionFilter = o.value), p());
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
            text: i("version_no_backups"),
          });
          return;
        }
        let w = u.createEl("div", { cls: "paperforge-version-timeline" });
        for (let b of m.versions) {
          let x = b.label === m.currentLabel,
            k = w.createEl("div", {
              cls:
                "paperforge-version-entry" +
                (x ? " paperforge-version-current" : ""),
            }),
            S = k.createEl("div", { cls: "paperforge-version-dot" }),
            R = k.createEl("div", { cls: "paperforge-version-content" }),
            V = R.createEl("div", { cls: "paperforge-version-label-row" });
          (V.createEl("span", {
            cls: "paperforge-version-label",
            text: b.label,
          }),
            x &&
              V.createEl("span", {
                cls: "paperforge-version-current-tag",
                text: i("version_current"),
              }));
          let M = b.created_at ? b.created_at.slice(0, 10) : "";
          R.createEl("div", {
            cls: "paperforge-meta",
            text: M + " \u2014 " + b.source,
          });
          let I = b.fulltext_size
            ? b.fulltext_size > 1024
              ? (b.fulltext_size / 1024).toFixed(0) + "KB"
              : b.fulltext_size + "B"
            : "";
          I && R.createEl("div", { cls: "paperforge-meta", text: I });
          let O = R.createEl("div", { cls: "paperforge-version-actions" });
          (O.createEl("button", {
            cls: "pf-btn-primary",
            text: i("version_restore_btn"),
          }).addEventListener("click", () => {
            pr(n, m.key, b.label)
              ? new F.Notice(
                  i("version_restore_done").replace("{label}", b.label)
                )
              : new F.Notice("Restore failed", 6e3);
          }),
            m.versions.length > 1 &&
              !x &&
              O.createEl("button", {
                cls: "pf-btn-secondary",
                text: i("version_compare_btn"),
              }).addEventListener("click", () => {
                h(m, b.label, m.currentLabel);
              }));
        }
      },
      f = a.createEl("div", { cls: "paperforge-version-compare" });
    f.style.display = "none";
    let h = (m, E, w) => {
        let b = dr(n, m.key, E, w);
        ((f.style.display = "block"), f.empty());
        let x = f.createEl("div", { cls: "paperforge-version-compare-header" });
        if (
          (x.createEl("span", {
            cls: "pf-title",
            text: i("version_compare_title")
              .replace("{vA}", E)
              .replace("{vB}", w),
          }),
          x.createEl("span", {
            cls: "paperforge-meta",
            text: i("version_compare_paragraphs").replace(
              "{n}",
              String(b.length)
            ),
          }),
          b.length === 0)
        ) {
          f.createEl("div", { cls: "paperforge-meta", text: "No changes" });
          return;
        }
        let k = f.createEl("div", { cls: "paperforge-version-diff-list" });
        for (let S of b) {
          let R = k.createEl("div", { cls: "paperforge-version-diff-row" }),
            V =
              S.type === "added" ? "[+]" : S.type === "removed" ? "[-]" : "[~]",
            M = S.heading || "paragraph " + (S.paragraphIndex + 1);
          (R.createEl("span", {
            cls: "paperforge-version-diff-label",
            text: V + " " + M,
          }),
            S.oldText &&
              R.createEl("pre", {
                cls: "paperforge-version-diff-old",
                text: S.oldText.slice(0, 200),
              }),
            S.newText &&
              R.createEl("pre", {
                cls: "paperforge-version-diff-new",
                text: S.newText.slice(0, 200),
              }));
        }
      },
      g = e.createEl("div", { cls: "paperforge-version-actions-bar" }),
      y = g.createEl("button", {
        cls: "pf-btn-primary",
        text: i("version_restore_selected"),
      }),
      v = g.createEl("button", {
        cls: "pf-btn-secondary",
        text: i("version_clear_old").replace("{size}", ""),
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
      (this._searchInput.placeholder = i("retrieval_search_placeholder")),
      this._searchInput.addEventListener("input", () => {
        var a;
        let s = ((a = this._searchInput) == null ? void 0 : a.value) || "";
        if (
          (s.startsWith("@") && !s.startsWith("@ ")
            ? ((this._searchMode = "@"),
              n.setText("@"),
              n.addClass("deep"),
              this._searchInput &&
                (this._searchInput.placeholder = i(
                  "retrieval_search_placeholder_deep"
                )))
            : ((this._searchMode = "M"),
              n.setText("M"),
              n.removeClass("deep"),
              this._searchInput &&
                (this._searchInput.placeholder = i(
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
        var a, o;
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
            (o = this._searchResultsEl) == null
              ? void 0
              : o.querySelectorAll(".paperforge-search-result-card");
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
            ? i("retrieval_searching_deep")
            : i("retrieval_searching_metadata"),
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
          t.createEl("div", { text: i("retrieval_empty") }),
          t.createEl("div", {
            cls: "paperforge-search-empty-tips",
            text: i("retrieval_empty_tips"),
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
            text: i("retrieval_vectors_not_built"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: i("retrieval_vectors_not_built_desc"),
          }));
        let r = t.createEl("button", {
          cls: "pf-btn-link",
          text: i("retrieval_open_vector_settings"),
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
            text: i("retrieval_backend_unavailable"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: i("retrieval_backend_unavailable_desc"),
          }));
        let r = t.createEl("div", { cls: "paperforge-search-state-actions" }),
          n = r.createEl("button", {
            cls: "pf-btn-primary",
            text: i("retrieval_run_doctor"),
          });
        (n.addEventListener("click", () => {
          let a = this.app.vault.adapter.basePath;
          if (typeof a != "string") return;
          let o = this._resolvePython();
          if (!o) return;
          let { path: c, args: p = [] } = o;
          (0, ue.spawn)(c, [...p, "-m", "paperforge", "doctor"], {
            cwd: a,
            stdio: "inherit",
          });
        }),
          r
            .createEl("button", {
              cls: "pf-btn-secondary",
              text: i("retrieval_retry"),
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
            text: i("retrieval_timeout_title"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: i("retrieval_timeout_desc"),
          }));
        let r = t.createEl("button", {
          cls: "pf-btn-primary",
          text: i("retrieval_retry"),
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
            text: i("retrieval_model_changed"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: i("retrieval_model_changed_desc"),
          }));
        let r = t.createEl("button", {
          cls: "pf-btn-primary",
          text: i("retrieval_rebuild_vectors"),
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
            text: i("retrieval_internal_error"),
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
    let o = null,
      p = this.app.plugins;
    if (p && typeof p == "object" && "plugins" in p) {
      let m = p.plugins;
      if (m && typeof m == "object" && "paperforge" in m) {
        let E = m.paperforge;
        E && typeof E == "object" && "settings" in E && (o = E.settings);
      }
    }
    let u = this._resolvePython();
    if (!u) {
      ((this._searchState = "backend-unavailable"), this._renderSearchState());
      return;
    }
    let { path: _, args: f = [] } = u,
      h = n === "retrieve" ? ["--deep"] : [],
      g = await de({ app: this.app }, "memory"),
      y = (0, ue.spawn)(
        _,
        [...f, "-m", "paperforge", "--vault", a, n, r, ...h, "--json"],
        { cwd: a, timeout: 3e4, env: g }
      ),
      v = [];
    (y.stdout.on("data", (m) => {
      v.push(m.toString("utf-8"));
    }),
      y.stderr.on("data", () => {}),
      y.on("close", (m) => {
        if (m !== 0) {
          let k = dt(String(m));
          ((this._searchState = this._mapErrorToSearchState(k.type)),
            this._renderSearchState());
          return;
        }
        let E = v.join(""),
          w = E.indexOf("{"),
          b = E.lastIndexOf("}"),
          x = "";
        if (w !== -1 && b > w) x = E.slice(w, b + 1);
        else {
          let k = E.indexOf("["),
            S = E.lastIndexOf("]");
          k !== -1 && S > k && (x = E.slice(k, S + 1));
        }
        if (!x) {
          ((this._searchState = "internal-error"), this._renderSearchState());
          return;
        }
        try {
          let k = JSON.parse(x),
            S = [];
          if (k && typeof k == "object" && "data" in k) {
            let R = k.data;
            if (R && typeof R == "object") {
              let V = R;
              "matches" in V && Array.isArray(V.matches) && (S = V.matches);
            }
          }
          ((this._searchResults = S),
            (this._searchState = S.length > 0 ? "results" : "empty"),
            this._renderSearchState());
        } catch (k) {
          let S = k instanceof Error ? k.message : String(k);
          ((this._searchState = "internal-error"), this._renderSearchState());
        }
      }),
      y.on("error", (m) => {
        let E = m.code;
        if (typeof E == "string") {
          let w = dt(E);
          this._searchState = this._mapErrorToSearchState(w.type);
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
        text: i("retrieval_results_count")
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
      let o = a,
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
        typeof o.title == "string"
          ? o.title
          : typeof o.file_name == "string"
            ? o.file_name
            : "(untitled)";
      p.createEl("div", { cls: "paperforge-search-result-title", text: u });
      let _ = typeof o.zotero_key == "string" ? o.zotero_key : "",
        f =
          typeof o.main_note_path == "string" && o.main_note_path
            ? o.main_note_path
            : null,
        h = typeof o.note_path == "string" && o.note_path ? o.note_path : null,
        g = f || h;
      if (!g && _) {
        let m = this._getCachedIndex().find(
          (E) =>
            E !== null &&
            typeof E == "object" &&
            "zotero_key" in E &&
            E.zotero_key === _
        );
        if (m && typeof m == "object") {
          let E = m;
          g =
            typeof E.main_note_path == "string" && E.main_note_path
              ? E.main_note_path
              : typeof E.note_path == "string" && E.note_path
                ? E.note_path
                : null;
        }
      }
      (g
        ? p.addEventListener("click", (v) => {
            let m = v.ctrlKey || v.metaKey;
            this.app.workspace.openLinkText(g, "", m);
          })
        : p.addEventListener("click", () => {
            new F.Notice("[!!] Note not found: " + (_ || "unknown"), 6e3);
          }),
        p.addEventListener("keydown", (v) => {
          if (v.key === "Enter" && g) {
            v.preventDefault();
            let m = v.ctrlKey || v.metaKey;
            this.app.workspace.openLinkText(g, "", m);
          }
        }));
      let y = p.createEl("div", { cls: "paperforge-search-result-meta" });
      if (
        (typeof o.first_author == "string" &&
          o.first_author &&
          y.createEl("span", {
            cls: "paperforge-search-result-author",
            text: o.first_author,
          }),
        typeof o.journal == "string" &&
          o.journal &&
          y.createEl("span", {
            cls: "paperforge-search-result-journal",
            text: o.journal,
          }),
        o.score !== void 0)
      ) {
        let v = o.score,
          m = typeof v == "number" ? v.toFixed(3) : String(v);
        y.createEl("span", {
          cls: "paperforge-search-result-score",
          text: "Score: " + m,
        });
      }
      if (
        (typeof o.domain == "string" &&
          o.domain &&
          p.createEl("span", {
            cls: "paperforge-search-result-tag",
            text: o.domain,
          }),
        typeof o.abstract == "string" && o.abstract)
      ) {
        let v = o.abstract;
        p.createEl("div", {
          cls: "paperforge-search-result-abstract",
          text: v.length > 200 ? v.slice(0, 200) + "..." : v,
        });
      }
      if (t && typeof o.text == "string" && o.text) {
        let v = o.text;
        p.createEl("div", {
          cls: "paperforge-search-result-source",
          text: v.length > 300 ? v.slice(0, 300) + "..." : v,
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
      new F.Notice(
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
      let g = this.app.workspace.getActiveFile(),
        y = null;
      if (g) {
        let v = this.app.metadataCache.getFileCache(g);
        if (
          (v && v.frontmatter && v.frontmatter.zotero_key
            ? (y = v.frontmatter.zotero_key)
            : (y = this._extractZoteroKeyFromPath(g.path)),
          y)
        )
          n = [...n, y];
        else if (v && v.frontmatter) {
          (this._showMessage(
            "[!!] No zotero_key in active note frontmatter",
            "error"
          ),
            new F.Notice(
              "[!!] Open a paper note with a zotero_key in its frontmatter first",
              6e3
            ),
            t.removeClass("running"));
          return;
        } else {
          (this._showMessage("[!!] No frontmatter in active note", "error"),
            new F.Notice(
              "[!!] The active note has no frontmatter with a zotero_key",
              6e3
            ),
            t.removeClass("running"));
          return;
        }
      } else {
        (this._showMessage("[!!] No active note open", "error"),
          new F.Notice(
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
        new F.Notice(
          "[!!] PaperForge runtime is not ready. Check settings.",
          6e3
        ),
        t.removeClass("running"));
      return;
    }
    let { path: o, args: c = [] } = a,
      p = await de({ app: this.app }, e.cmd),
      u = (0, ue.spawn)(o, [...c, "-m", "paperforge", e.cmd, ...n], {
        cwd: r,
        timeout: s,
        env: p,
      }),
      _ = [],
      f = Date.now(),
      h = setInterval(() => this._fetchStats(!0), 4e3);
    (u.stdout.on("data", (g) => {
      let y = g
        .toString("utf-8")
        .split(
          `
`
        )
        .filter(Boolean);
      for (let v of y) {
        let m = v.trim();
        m &&
          (_.push(m),
          this._showMessage(
            _.slice(-8).join(`
`),
            "running"
          ));
      }
    }),
      u.stderr.on("data", (g) => {
        let y = g
          .toString("utf-8")
          .split(
            `
`
          )
          .filter(Boolean);
        for (let v of y) {
          if (v.includes("\r") || v.includes("%") || v.includes("\u2588"))
            continue;
          let m = v.trim();
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
      u.on("close", (g) => {
        (clearInterval(h), t.removeClass("running"));
        let y = ((Date.now() - f) / 1e3).toFixed(1);
        if (g !== 0) {
          let v = _.slice(-3).join(" | ") || "exit code " + g;
          (e.cmd === "repair" || e.cmd === "ocr") && g === 1
            ? (this._showMessage("[WARN] " + v, "running"),
              new F.Notice("[WARN] " + e.cmd + " partial: " + v, 8e3),
              this._fetchStats(!0))
            : (this._showMessage("[!!] " + v, "error"),
              new F.Notice("[!!] " + e.cmd + " failed: " + v, 8e3));
        } else if (e.needsKey || e.needsFilter) {
          let v = _.join(`
`);
          if (v.trim())
            try {
              (JSON.parse(v),
                navigator.clipboard
                  .writeText(v)
                  .then(() => {
                    let m = `${y}s \u2014 ${v.length} chars copied`;
                    (this._showMessage("[OK] " + e.title + ": " + m, "ok"),
                      new F.Notice(
                        "[OK] " + e.okMsg + " \u2014 " + v.length + " chars"
                      ));
                  })
                  .catch((m) => {
                    (this._showMessage(
                      "[!!] Clipboard write failed: " + m.message,
                      "error"
                    ),
                      new F.Notice("[!!] Clipboard error", 6e3));
                  }));
            } catch (m) {
              (this._showMessage("[!!] Invalid JSON from " + e.title, "error"),
                new F.Notice(
                  "[!!] " +
                    e.title +
                    " returned invalid JSON: " +
                    m.message.slice(0, 100),
                  8e3
                ));
            }
          else
            (this._showMessage("[!!] No output from context command", "error"),
              new F.Notice("[!!] Context command returned empty output", 8e3));
          this._fetchStats(!0);
        } else {
          let m =
              _.filter((w) => w.match(/updated \d+/)).pop() ||
              _[_.length - 1] ||
              "",
            E = `${y}s \u2014 ${m}`;
          (this._showMessage("[OK] " + e.title + ": " + E, "ok"),
            new F.Notice("[OK] " + e.okMsg),
            this._contentEl && this._contentEl.removeClass("switching"),
            (this._cachedStats = null));
          try {
            this._fetchStats(!1);
          } catch (w) {
            console.log("[PF] fetchStats error:", w);
          }
          (console.log("[PF] close cmd=" + e.cmd + " id=" + e.id),
            e.cmd === "sync" &&
              Je(this.app, this.app.plugins.plugins.paperforge, r));
        }
      }),
      u.on("error", (g) => {
        (t.removeClass("running"),
          this._contentEl && this._contentEl.removeClass("switching"),
          this._showMessage("[!!] " + g.message, "error"),
          new F.Notice("[!!] Cannot start: " + g.message, 8e3));
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
          t.setText(i("version_panel_title")),
          this._headerTitle &&
            this._headerTitle.setText(i("version_panel_title")));
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
    let t = e.app.workspace.getLeavesOfType(ge);
    if (t.length > 0) {
      e.app.workspace.revealLeaf(t[0]);
      return;
    }
    let r = e.app.workspace.getRightLeaf(!1);
    r &&
      (await r.setViewState({ type: ge, active: !0 }),
      e.app.workspace.revealLeaf(r));
  }
};
var et = class extends K.Plugin {
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
        (this._managedRuntime = new _e({ version: this.manifest.version })),
      this._managedRuntime
    );
  }
  _getPythonCommand() {
    let e = fe(this.getManagedRuntime().current());
    return e ? { path: e.command, args: [...e.args] } : null;
  }
  async onload() {
    (await this.loadSettings(),
      await zt(
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
    (Ot(this.app, this.settings.language),
      this.registerView(ge, (t) => new Fe(t)));
    try {
      (0, K.addIcon)(Le, Rt);
    } catch (t) {}
    (this.addRibbonIcon(Le, "PaperForge Dashboard", () => Fe.open(this)),
      Q.find((t) => t.id === "paperforge-ocr-redo") &&
        this.addRibbonIcon("reset", "PaperForge: Redo OCR", async () => {
          let t = this.app.vault.adapter.basePath;
          new K.Notice("PaperForge: Redo OCR starting...");
          let r = this._getPythonCommand();
          if (!r) {
            new K.Notice("Runtime not ready");
            return;
          }
          let { path: n, args: s } = r,
            a = await de(this, "ocr");
          (0, De.execFile)(
            n,
            [...s, "-m", "paperforge", "ocr", "redo"],
            { cwd: t, timeout: 6e5, env: a },
            (o, c, p) => {
              if (o) {
                new K.Notice("PaperForge: Redo OCR failed");
                return;
              }
              new K.Notice("PaperForge: Redo OCR done");
            }
          );
        }),
      this.addSettingTab(new Xe(this.app, this)),
      this.addCommand({
        id: "paperforge-status-panel",
        name: `PaperForge: ${i("guide_open")}`,
        callback: () => Fe.open(this),
      }));
    for (let t of Q)
      this.addCommand({
        id: t.id,
        name: `PaperForge: ${t.title}`,
        callback: async () => {
          if (t.disabled) {
            new K.Notice(
              `[i] ${t.disabledMsg || "This action is not yet available."}`,
              6e3
            );
            return;
          }
          let r = this.app.vault.adapter.basePath;
          new K.Notice(`PaperForge: running ${t.cmd}...`);
          let n = this._getPythonCommand();
          if (!n) {
            new K.Notice("Runtime not ready");
            return;
          }
          let { path: s, args: a = [] } = n,
            o = Array.isArray(t.args) ? [...t.args] : [],
            c = await de(this, t.cmd);
          (0, De.execFile)(
            s,
            [...a, "-m", "paperforge", t.cmd, ...o],
            { cwd: r, timeout: 3e5, env: c },
            (p, u, _) => {
              if (p) {
                new K.Notice(
                  `[!!] ${t.cmd} failed: ${(_ || p.message).slice(0, 120)}`,
                  8e3
                );
                return;
              }
              new K.Notice(
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
    let t = ae(e).exportsDir;
    if (!$.existsSync(t)) return;
    let r = 0;
    try {
      $.readdirSync(t).forEach((n) => {
        if (!n.endsWith(".json")) return;
        let s = $.statSync(Ae.join(t, n));
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
    (0, De.exec)(r, { timeout: 12e4, encoding: "utf-8" }, (n, s, a) => {
      ((this._autoSyncRunning = !1),
        (this._memoryStatusText = null),
        n || (this._lastSyncTime = new Date().toLocaleTimeString()));
      try {
        let o = ae(e).exportsDir,
          c = 0;
        ($.readdirSync(o).forEach((p) => {
          p.endsWith(".json") &&
            (c = Math.max(c, $.statSync(Ae.join(o, p)).mtimeMs));
        }),
          (this._lastExportMtime = c));
      } catch (o) {}
    });
  }
  _checkOcr(e) {
    if (this._autoSyncRunning) return;
    let t = ae(e).ocrDir;
    if ($.existsSync(t))
      try {
        $.readdirSync(t, { withFileTypes: !0 }).forEach((r) => {
          if (!r.isDirectory()) return;
          let n = Ae.join(t, r.name, "meta.json");
          if (!$.existsSync(n)) return;
          let s = $.statSync(n),
            a = this._lastOcrMtimes[r.name] || 0;
          if (
            s.mtimeMs <= a ||
            ((this._lastOcrMtimes[r.name] = s.mtimeMs), this._autoSyncRunning)
          )
            return;
          this._autoSyncRunning = !0;
          let o = this._getPythonCommand();
          if (!o) {
            this._autoSyncRunning = !1;
            return;
          }
          let c = `"${o.path}" ${o.args.join(" ")} -m paperforge --vault "${e}" sync`;
          (0, De.exec)(c, { timeout: 3e4, encoding: "utf-8" }, () => {
            ((this._autoSyncRunning = !1), (this._memoryStatusText = null));
          });
        });
      } catch (r) {}
  }
  readPaperforgeJson() {
    let e = this.app.vault.adapter.basePath,
      t = Ae.join(e, "paperforge.json"),
      r = {
        system_dir: "System",
        resources_dir: "Resources",
        literature_dir: "Literature",
        base_dir: "Bases",
        zotero_data_dir: "",
      };
    try {
      if (!$.existsSync(t)) return r;
      let n = $.readFileSync(t, "utf-8"),
        s = JSON.parse(n),
        a = s.vault_config || {};
      return {
        system_dir: a.system_dir || s.system_dir || r.system_dir,
        resources_dir: a.resources_dir || s.resources_dir || r.resources_dir,
        literature_dir:
          a.literature_dir || s.literature_dir || r.literature_dir,
        base_dir: a.base_dir || s.base_dir || r.base_dir,
        zotero_data_dir: s.zotero_data_dir || r.zotero_data_dir,
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
      r = Ae.join(t, "paperforge.json"),
      n = {};
    try {
      $.existsSync(r) && (n = JSON.parse($.readFileSync(r, "utf-8")));
    } catch (a) {
      console.warn("PaperForge: Failed to read paperforge.json for update", a);
    }
    (!n.vault_config || typeof n.vault_config != "object") &&
      (n.vault_config = {});
    let s = ["system_dir", "resources_dir", "literature_dir", "base_dir"];
    for (let a of s) e[a] !== void 0 && (n.vault_config[a] = e[a]);
    (e.zotero_data_dir !== void 0 && (n.zotero_data_dir = e.zotero_data_dir),
      n.schema_version || (n.schema_version = "2"));
    for (let a of s) delete n[a];
    try {
      if (
        ($.writeFileSync(r, JSON.stringify(n, null, 2), "utf-8"), this.settings)
      ) {
        let a = this.readPaperforgeJson();
        ((this.settings.system_dir = a.system_dir),
          (this.settings.resources_dir = a.resources_dir),
          (this.settings.literature_dir = a.literature_dir),
          (this.settings.base_dir = a.base_dir));
      }
    } catch (a) {
      (console.error("PaperForge: Failed to write paperforge.json", a),
        new K.Notice(
          "PaperForge: Failed to save configuration to paperforge.json"
        ));
    }
  }
  onunload() {
    (this._pollTimer && clearInterval(this._pollTimer),
      this.app.workspace.detachLeavesOfType(ge));
  }
  async loadSettings() {
    var n, s;
    let e = (n = await this.loadData()) != null ? n : {};
    ((this.settings = Object.assign({}, Oe, e)),
      this.settings.features &&
        Oe.features &&
        (this.settings.features = Object.assign(
          {},
          Oe.features,
          this.settings.features || {}
        )),
      this.settings.frozen_skills || (this.settings.frozen_skills = {}));
    let t = !!e.capabilityState || !!e.last_seen_version || !!e.vault_path;
    e._setup_complete === !1 &&
      t &&
      e._setup_journey_started !== !0 &&
      (this.settings._setup_complete = !0);
    let r = this.readPaperforgeJson();
    if (
      ((this.settings.system_dir = r.system_dir),
      (this.settings.resources_dir = r.resources_dir),
      (this.settings.literature_dir = r.literature_dir),
      (this.settings.base_dir = r.base_dir),
      r.zotero_data_dir
        ? (this.settings.zotero_data_dir = r.zotero_data_dir)
        : (s = this.settings.zotero_data_dir) != null &&
          s.trim() &&
          this.savePaperforgeJson({
            zotero_data_dir: this.settings.zotero_data_dir.trim(),
          }),
      this.settings.python_path && this.settings.python_path.trim())
    ) {
      let a = this.settings.python_path.trim();
      this.settings._python_path_stale = !$.existsSync(a);
    }
  }
  async saveSettings() {
    let e = {};
    for (let t of Object.keys(Oe))
      t in this.settings && (e[t] = this.settings[t]);
    await this.saveData(e);
  }
  _checkReleaseNotes() {
    let e = this.manifest.version;
    if (this.settings.last_seen_version === e) return;
    let s = (lt().versions || []).find((o) => o.version === e);
    class a extends K.Modal {
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
        new K.Setting(c).addButton((p) =>
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
