"use strict";
var Ot = Object.create;
var ze = Object.defineProperty;
var Lt = Object.getOwnPropertyDescriptor;
var It = Object.getOwnPropertyNames;
var Mt = Object.getPrototypeOf,
  Nt = Object.prototype.hasOwnProperty;
var jt = (u, h) => () => (h || u((h = { exports: {} }).exports, h), h.exports),
  zt = (u, h) => {
    for (var e in h) ze(u, e, { get: h[e], enumerable: !0 });
  },
  ct = (u, h, e, t) => {
    if ((h && typeof h == "object") || typeof h == "function")
      for (let r of It(h))
        !Nt.call(u, r) &&
          r !== e &&
          ze(u, r, {
            get: () => h[r],
            enumerable: !(t = Lt(h, r)) || t.enumerable,
          });
    return u;
  };
var K = (u, h, e) => (
    (e = u != null ? Ot(Mt(u)) : {}),
    ct(
      h || !u || !u.__esModule
        ? ze(e, "default", { value: u, enumerable: !0 })
        : e,
      u
    )
  ),
  $t = (u) => ct(ze({}, "__esModule", { value: !0 }), u);
var Xe = jt((Qt, Ht) => {
  Ht.exports = {
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
var Jt = {};
zt(Jt, { default: () => Ue });
module.exports = $t(Jt);
var X = require("obsidian"),
  Z = K(require("fs")),
  Te = K(require("path")),
  fe = require("child_process");
var we = "paperforge-status",
  De = "paperforge",
  pt =
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path><line x1="8" y1="7" x2="16" y2="7"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>',
  oe = [
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
  Be = {
    vault_path: "",
    setup_complete: !1,
    auto_update: !0,
    auto_update_on_startup: !0,
    agent_platform: "opencode",
    language: "",
    paddleocr_api_key: "",
    zotero_data_dir: "",
    python_path: "",
    features: { memory_layer: !0, vector_db: !1 },
    selected_skill_platform: "opencode",
    vector_db_api_key: "",
    vector_db_api_base: "",
    vector_db_api_model: "text-embedding-3-small",
    frozen_skills: {},
    system_dir: "",
    resources_dir: "",
    literature_dir: "",
    base_dir: "",
    last_seen_version: "",
  };
function dt(u, h) {
  if (!h || !h.note_path) return h;
  let e = u.vault.getAbstractFileByPath(h.note_path);
  if (!e) return h;
  let t = u.metadataCache.getFileCache(e),
    r = t && t.frontmatter;
  if (!r) return h;
  let s = { ...h };
  for (let a of [
    "do_ocr",
    "analyze",
    "ocr_status",
    "ocr_redo",
    "deep_reading_status",
  ])
    Object.prototype.hasOwnProperty.call(r, a) && (s[a] = r[a]);
  return s;
}
function qe(u, h) {
  return u && { ...u, ...h };
}
var Je = {
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
        "Python was not detected. Install Python 3.10+ and add it to PATH.",
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
      prep_python: "Python 3.10+",
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
      tab_features: "Features",
      tab_setup: "Installation",
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
      notice_check_fail: "\u672A\u901A\u8FC7: ",
      notice_python_missing:
        "Python \u672A\u68C0\u6D4B\u5230\uFF0C\u8BF7\u5148\u5B89\u88C5 Python 3.10+ \u5E76\u52A0\u5165 PATH",
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
      prep_key_desc:
        "\u5728 https://aistudio.baidu.com/paddleocr \u83B7\u53D6 API Key",
      prep_python: "Python 3.10+",
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
    },
  },
  Ge = null;
function Vt(u) {
  try {
    let h = u.vault;
    if (typeof h.getConfig == "function") {
      let e = h.getConfig("language");
      if (e && String(e).startsWith("zh")) return "zh";
    }
  } catch (h) {}
  try {
    if (typeof localStorage != "undefined") {
      let h = localStorage.getItem("language");
      if (h && String(h).startsWith("zh")) return "zh";
    }
  } catch (h) {}
  return "en";
}
function ut(u) {
  Ge = Vt(u) === "zh" ? Je.zh : Je.en;
}
function o(u) {
  return (Ge && Ge[u]) || Je.en[u] || u;
}
var C = require("obsidian"),
  V = K(require("fs")),
  te = K(require("path")),
  Rt = K(require("os")),
  G = require("child_process");
var Ft = K(Xe());
var he = K(require("fs")),
  ue = K(require("path")),
  _t = K(require("os")),
  ge = require("child_process"),
  Ye = null,
  ht = !1;
function z(u, h, e, t) {
  let r = e || he,
    s = t || ge.execFileSync;
  if (h && h.python_path && h.python_path.trim()) {
    let i = h.python_path.trim();
    if (r.existsSync(i)) return { path: i, source: "manual", extraArgs: [] };
  }
  let a = [
    ue.join(u, ".paperforge-test-venv", "Scripts", "python.exe"),
    ue.join(u, ".venv", "Scripts", "python.exe"),
    ue.join(u, "venv", "Scripts", "python.exe"),
  ];
  for (let i of a)
    try {
      if (r.existsSync(i))
        return { path: i, source: "auto-detected", extraArgs: [] };
    } catch (c) {}
  let n = [
    { path: "py", extraArgs: ["-3"] },
    { path: "python", extraArgs: [] },
    { path: "python3", extraArgs: [] },
  ];
  for (let i of n)
    try {
      let c = s(i.path, [...i.extraArgs, "--version"], {
        encoding: "utf-8",
        timeout: 5e3,
        windowsHide: !0,
      });
      if (c && c.toLowerCase().includes("python"))
        return {
          path: i.path,
          source: "auto-detected",
          extraArgs: i.extraArgs,
        };
    } catch (c) {}
  return { path: "python", source: "auto-detected", extraArgs: [] };
}
function ft(u, h, e, t, r) {
  t === void 0 && (t = 1e4);
  let s = r || ge.execFile;
  return new Promise((a) => {
    s(
      u,
      ["-c", "import paperforge; print(paperforge.__version__)"],
      { cwd: e, timeout: t },
      (n, i) => {
        if (n) {
          a({
            status: "not-installed",
            pyVersion: null,
            pluginVersion: h,
            error: n.message,
          });
          return;
        }
        let c = (i && i.trim()) || null;
        a(
          c === h
            ? { status: "match", pyVersion: c, pluginVersion: h, error: null }
            : {
                status: "mismatch",
                pyVersion: c,
                pluginVersion: h,
                error: null,
              }
        );
      }
    );
  });
}
function Qe(u) {
  let h = String(u),
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
    }[h];
  return t
    ? { ...t }
    : { type: "unknown", message: String(u), recoverable: !1 };
}
function gt(u, h, e) {
  e === void 0 && (e = []);
  let t = `paperforge==${h}`,
    r = `git+https://github.com/LLLin000/PaperForge.git@${h}`,
    s = [...e, "-m", "pip", "install", "--upgrade", t],
    a = [...e, "-m", "pip", "install", "--upgrade", r];
  return { cmd: u, url: r, args: a, pypiArgs: s, gitArgs: a, timeout: 12e4 };
}
function mt(u, h, e, t, r, s) {
  let a = r || ge.spawn;
  return new Promise((n) => {
    let i = Date.now(),
      c = { cwd: e, timeout: t, windowsHide: !0 };
    s && (c.env = s);
    let l = a(u, h, c),
      d = [],
      _ = [];
    (l.stdout.on("data", (p) => {
      d.push(p.toString("utf-8"));
    }),
      l.stderr.on("data", (p) => {
        _.push(p.toString("utf-8"));
      }),
      l.on("close", (p) => {
        n({
          stdout: d.join(""),
          stderr: _.join(""),
          exitCode: p,
          elapsed: Date.now() - i,
        });
      }),
      l.on("error", (p) => {
        n({
          stdout: d.join(""),
          stderr:
            _.join("") +
            `
` +
            p.message,
          exitCode: -1,
          elapsed: Date.now() - i,
        });
      }));
  });
}
function et() {
  if (ht) return Ye;
  ht = !0;
  try {
    let u;
    if (process.platform === "win32") {
      let h = process.env.ComSpec || "C:\\Windows\\System32\\cmd.exe";
      u = (0, ge.execFileSync)(h, ["/c", "where", "git"], {
        timeout: 5e3,
        windowsHide: !0,
        encoding: "utf-8",
      });
    } else
      u = (0, ge.execFileSync)("which", ["git"], {
        timeout: 5e3,
        encoding: "utf-8",
      });
    if (u) {
      let h = u
        .split(
          `
`
        )[0]
        .trim();
      h && (Ye = ue.dirname(h));
    }
  } catch (u) {}
  return Ye;
}
function Se() {
  let u = { ...process.env },
    h = process.platform,
    e = _t.homedir(),
    t = [],
    r = et();
  (r && t.push(r),
    h === "darwin"
      ? t.push(
          "/opt/homebrew/bin",
          "/usr/local/bin",
          "/usr/bin",
          `${e}/.local/bin`
        )
      : h === "linux" &&
        t.push("/usr/local/bin", "/usr/bin", `${e}/.local/bin`));
  let s = u.PATH || "";
  return ((u.PATH = [...t, s].filter(Boolean).join(ue.delimiter)), u);
}
function yt(u) {
  return String(u)
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "")
    .includes("betterbibtex");
}
function tt(u) {
  if (!u) return !1;
  try {
    if (!he.existsSync(u)) return !1;
    for (let h of he.readdirSync(u)) if (yt(h)) return !0;
  } catch (h) {}
  return !1;
}
function $e(u) {
  if (!u) return !1;
  try {
    if (!he.existsSync(u)) return !1;
    for (let h of he.readdirSync(u)) {
      let e = ue.join(u, h, "extensions");
      try {
        if (!he.existsSync(e)) continue;
        for (let t of he.readdirSync(e)) if (yt(t)) return !0;
      } catch (t) {}
    }
  } catch (h) {}
  return !1;
}
var xe = K(require("fs")),
  W = K(require("path")),
  rt = require("child_process"),
  _e = null;
function Kt(u, h) {
  let e = h || xe,
    t = W.join(u, "paperforge.json"),
    r = {
      system_dir: "System",
      resources_dir: "Resources",
      literature_dir: "Literature",
      base_dir: "Bases",
    };
  try {
    if (!e.existsSync(t))
      return { ...r, _warning: "paperforge.json not found; using defaults" };
    let s = e.readFileSync(t, "utf-8"),
      a = JSON.parse(s),
      n = a.vault_config || {};
    return {
      system_dir: n.system_dir || a.system_dir || r.system_dir,
      resources_dir: n.resources_dir || a.resources_dir || r.resources_dir,
      literature_dir: n.literature_dir || a.literature_dir || r.literature_dir,
      base_dir: n.base_dir || a.base_dir || r.base_dir,
      _warning: null,
    };
  } catch (s) {
    return (
      console.warn(
        "PaperForge: Failed to read paperforge.json, using defaults",
        s
      ),
      { ...r, _warning: "paperforge.json invalid; using defaults" }
    );
  }
}
function le(u, h) {
  let e = Kt(u, h),
    t = W.join(u, e.system_dir, "PaperForge");
  return {
    vault: u,
    systemDir: t,
    indexesDir: W.join(t, "indexes"),
    logsDir: W.join(t, "logs"),
    dbPath: W.join(t, "indexes", "paperforge.db"),
    memoryStatePath: W.join(t, "indexes", "memory-runtime-state.json"),
    vectorStatePath: W.join(t, "indexes", "vector-runtime-state.json"),
    healthStatePath: W.join(t, "indexes", "runtime-health.json"),
    buildStatePath: W.join(t, "indexes", "vector-build-state.json"),
    orphanStatePath: W.join(t, "indexes", "sync-orphan-state.json"),
    exportsDir: W.join(t, "exports"),
    ocrDir: W.join(t, "ocr"),
    pluginDataPath: W.join(
      u,
      ".obsidian",
      "plugins",
      "paperforge",
      "data.json"
    ),
    pfJsonPath: W.join(u, "paperforge.json"),
    configWarning: e._warning,
  };
}
function st(u) {
  try {
    return xe.existsSync(u) ? JSON.parse(xe.readFileSync(u, "utf-8")) : null;
  } catch (h) {
    return null;
  }
}
function Wt(u) {
  let h = le(u);
  return st(h.memoryStatePath);
}
var Pe = null;
function Ve(u) {
  let h = le(u),
    e = Date.now();
  if (Pe && Pe.vaultPath === u && e - Pe.ts < 2e3) return Pe.result;
  let t = "",
    r = [
      W.join(u, ".paperforge-test-venv", "Scripts", "python.exe"),
      W.join(u, ".venv", "Scripts", "python.exe"),
      W.join(u, "venv", "Scripts", "python.exe"),
    ];
  for (let a = 0; a < r.length; a++)
    if (xe.existsSync(r[a])) {
      t = r[a];
      break;
    }
  if (t)
    try {
      let a = (0, rt.execFileSync)(
          t,
          ["-m", "paperforge", "--vault", u, "embed", "status", "--json"],
          { encoding: "utf-8", timeout: 1e4, windowsHide: !0 }
        ),
        n = JSON.parse(a);
      if (n.ok && n.data) {
        let i = n.data;
        return ((Pe = { vaultPath: u, result: i, ts: e }), i);
      }
    } catch (a) {}
  let s = st(h.vectorStatePath);
  return ((Pe = { vaultPath: u, result: s, ts: e }), s);
}
function Ae(u) {
  let h = le(u);
  return st(h.healthStatePath);
}
function vt(u) {
  var e;
  let h = Ae(u);
  return !!(h && ((e = h.summary) == null ? void 0 : e.status) === "ok");
}
function He(u) {
  let h = Wt(u);
  return !h || h.paper_count_db === 0
    ? "DB not found. Run paperforge memory build."
    : "Papers: " + h.paper_count_db + " | " + (h.fresh ? "fresh" : "stale");
}
function Ce(u) {
  var t, r, s;
  let h = Ve(u);
  return h
    ? h.healthy === !1
      ? "Vector index unreadable - rebuild required"
      : "Chunks: " +
        (((t = h.chunk_count) != null ? t : 0) +
          ((r = h.body_chunk_count) != null ? r : 0) +
          ((s = h.object_chunk_count) != null ? s : 0)) +
        " | " +
        h.model +
        " | " +
        h.mode
    : "Status unavailable";
}
function me(u, h) {
  if (_e) return _e;
  if (h && h.python_path && h.python_path.trim()) {
    let r = h.python_path.trim();
    if (xe.existsSync(r))
      return ((_e = { path: r, source: "manual", extraArgs: [] }), _e);
  }
  let e = [
    W.join(u, ".paperforge-test-venv", "Scripts", "python.exe"),
    W.join(u, ".venv", "Scripts", "python.exe"),
    W.join(u, "venv", "Scripts", "python.exe"),
  ];
  for (let r = 0; r < e.length; r++)
    if (xe.existsSync(e[r]))
      return (
        (_e = { path: e[r], source: "auto-detected", extraArgs: [] }),
        _e
      );
  let t = [
    { path: "py", extraArgs: ["-3"] },
    { path: "python", extraArgs: [] },
    { path: "python3", extraArgs: [] },
  ];
  for (let r = 0; r < t.length; r++)
    try {
      let s = t[r],
        a = (0, rt.execFileSync)(s.path, s.extraArgs.concat(["--version"]), {
          encoding: "utf-8",
          timeout: 5e3,
          windowsHide: !0,
        });
      if (a && a.toLowerCase().indexOf("python") !== -1)
        return (
          (_e = {
            path: s.path,
            source: "auto-detected",
            extraArgs: s.extraArgs,
          }),
          _e
        );
    } catch (s) {}
  return (
    (_e = { path: "python", source: "auto-detected", extraArgs: [] }),
    _e
  );
}
function nt(u, h, e) {
  return !u ||
    typeof u != "object" ||
    !Object.prototype.hasOwnProperty.call(u, h)
    ? !!e
    : !!u[h];
}
function bt(u, h, e) {
  let t = !nt(u, h, e);
  return (u && typeof u == "object" && (u[h] = t), t);
}
var ae = require("obsidian"),
  pe = K(require("fs")),
  xt = K(require("path")),
  kt = K(require("https")),
  Le = require("child_process");
function Et(u, h) {
  return !h || !h.trim()
    ? { blocked: !0, reason: "zotero" }
    : u
      ? { blocked: !1 }
      : { blocked: !0, reason: "ocr" };
}
var at = class extends ae.Modal {
  constructor(e, t, r, s) {
    super(e);
    this._rowEls = [];
    ((this.orphans = t.map((a, n) => ({ ...a, _selected: !0, _idx: n }))),
      (this.vaultPath = r),
      (this.py = s));
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
    for (let s of this.orphans) {
      let a = t.createEl("div", {
        cls:
          "paperforge-orphan-row" +
          (s._selected ? "" : " paperforge-orphan-dimmed"),
      });
      this._rowEls.push(a);
      let n = a.createEl("div", { cls: "paperforge-orphan-info" }),
        i = n.createEl("div", { cls: "paperforge-orphan-header" });
      i.createEl("span", {
        cls: "paperforge-orphan-key",
        text: s.citation_key || s.key,
      });
      let c = i.createEl("span", { cls: "paperforge-orphan-tags" });
      (c.createEl("span", {
        cls: "paperforge-tag " + (s.has_pdf ? "tag-pdf" : "tag-nopdf"),
        text: s.has_pdf ? "PDF" : "no PDF",
      }),
        s.collection_path &&
          c.createEl("span", {
            cls: "paperforge-tag tag-collection",
            text: s.collection_path,
          }),
        s.title &&
          n.createEl("div", { cls: "paperforge-orphan-title", text: s.title }));
      let l = [];
      (s.authors && l.push(s.authors),
        s.year && l.push(s.year),
        l.length > 0 &&
          n.createEl("div", {
            cls: "paperforge-orphan-meta",
            text: l.join(" \xB7 "),
          }),
        n.createEl("div", {
          cls: "paperforge-orphan-explain",
          text: o("orphan_explain"),
        }),
        a.addEventListener("click", () => {
          ((s._selected = !s._selected), this._updateUI());
        }));
    }
    let r = e.createEl("div", { cls: "paperforge-modal-actions" });
    ((this._selectAllBtn = r.createEl("button", {
      cls: "paperforge-step-btn",
      text: "Deselect all",
    })),
      this._selectAllBtn.addEventListener("click", () => {
        let s = this.orphans.every((a) => a._selected);
        for (let a of this.orphans) a._selected = !s;
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
        let s = this.orphans.filter((n) => n._selected);
        if (s.length === 0) {
          new ae.Notice(o("orphan_none_selected"));
          return;
        }
        if (
          (this._countEl.setText("Deleting..."),
          this._countEl.setAttr("disabled", ""),
          this._selectAllBtn.setAttr("disabled", ""),
          !this.py || !this.py.path)
        ) {
          (new ae.Notice("PaperForge: Python not found"), this.close());
          return;
        }
        let a = s.map((n) => n.key);
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
            ...a,
          ],
          { cwd: this.vaultPath, timeout: 6e4 },
          (n, i) => {
            if (n) {
              (new ae.Notice("PaperForge: prune failed"), this.close());
              return;
            }
            try {
              let c = JSON.parse(i),
                l = (c.data && c.data.deleted) || [];
              new ae.Notice("Deleted " + l.length + " orphan workspace(s)");
            } catch (c) {
              new ae.Notice("PaperForge: prune done");
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
function Ke(u, h, e) {
  console.log("[PF] checkOrphanState called");
  try {
    let r = le(e).orphanStatePath;
    if (!pe.existsSync(r)) {
      console.log("[PF] orphan file NOT FOUND");
      return;
    }
    console.log("[PF] orphan file FOUND");
    let s = pe.readFileSync(r, "utf-8"),
      n = JSON.parse(s).orphans || [];
    if ((console.log("[PF] orphans count:", n.length), n.length === 0)) return;
    let i = me(e, h.settings);
    (console.log("[PF] py.path:", i ? i.path : "null"),
      new at(u, n, e, i).open(),
      pe.unlinkSync(r),
      console.log("[PF] orphan file cleaned"));
  } catch (t) {
    console.log("[PF] checkOrphanState exception:", t.message || t);
  }
}
var Oe = class extends ae.Modal {
  constructor(e, t) {
    super(e);
    this._pendingSave = null;
    this._showSkipConfirm = !1;
    ((this.plugin = t), (this._step = 1));
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
    e.forEach((r, s) => {
      let a = s + 1,
        n = t.createEl("div", {
          cls: `paperforge-step-dot ${a === this._step ? "active" : ""} ${a < this._step ? "done" : ""}`,
        });
      (n.createEl("span", { cls: "paperforge-step-num", text: `${a}` }),
        n.createEl("span", { cls: "paperforge-step-label", text: r }));
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
      t = Et(this._apiKeyValidated, e.zotero_data_dir);
    if (t.reason === "ocr") return t;
    let r = (e.zotero_data_dir || "").trim();
    if (!r)
      return (
        new ae.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u4E3A\u5FC5\u586B\u9879\uFF0C\u8BF7\u586B\u5199\u8DEF\u5F84"
        ),
        { blocked: !0, reason: "zotero" }
      );
    if (!pe.existsSync(r))
      return (
        new ae.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u8DEF\u5F84\u4E0D\u5B58\u5728"
        ),
        { blocked: !0, reason: "zotero" }
      );
    if (!pe.statSync(r).isDirectory())
      return (
        new ae.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u8DEF\u5F84\u4E0D\u662F\u4E00\u4E2A\u76EE\u5F55"
        ),
        { blocked: !0, reason: "zotero" }
      );
    let s = xt.join(r, "storage");
    return !pe.existsSync(s) || !pe.statSync(s).isDirectory()
      ? (new ae.Notice(
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
      s = e.createEl("div", { cls: "paperforge-dir-tree" }),
      a = s.createEl("div", { cls: "paperforge-dir-node root" });
    a.textContent = `\u{1F4C1} Vault (${r})`;
    let n = s.createEl("div", { cls: "paperforge-dir-children" }),
      i = n.createEl("div", { cls: "paperforge-dir-node folder" });
    ((i.textContent = `\u{1F4C1} ${t.resources_dir || "Resources"}/ \u2014 \u6587\u732E\u5361\u7247\u76EE\u5F55\uFF08Base \u6570\u636E\u6765\u6E90\uFF09`),
      i
        .createEl("div", { cls: "paperforge-dir-children" })
        .createEl("div", {
          cls: "paperforge-dir-node file",
          text: `\u{1F4C1} ${t.literature_dir || "Literature"}/ \u2014 \u6587\u732E\u5361\u7247`,
        }),
      n.createEl("div", {
        cls: "paperforge-dir-node folder",
        text: `\u{1F4C1} ${t.base_dir || "Bases"}/ \u2014 \u6570\u636E\u7BA1\u7406\u9762\u677F`,
      }),
      n.createEl("div", {
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
    let l = e.createEl("div", { cls: "paperforge-summary" }),
      d = [
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
    for (let _ of d) {
      let p = l.createEl("div", { cls: "paperforge-summary-row" });
      (p.createEl("span", { cls: "paperforge-summary-label", text: _.label }),
        p.createEl("span", { cls: "paperforge-summary-value", text: _.val }));
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
    let s = e.createEl("div", { cls: "paperforge-summary" }),
      a = [
        { label: o("dir_resources"), val: `${r}/${t.resources_dir || ""}` },
        {
          label: o("dir_notes"),
          val: `${r}/${t.resources_dir || ""}/${t.literature_dir || ""}`,
        },
        { label: o("dir_system"), val: `${r}/${t.system_dir || ""}` },
        { label: o("dir_base"), val: `${r}/${t.base_dir || ""}` },
      ];
    for (let n of a) {
      let i = s.createEl("div", { cls: "paperforge-summary-row" });
      (i.createEl("span", { cls: "paperforge-summary-label", text: n.label }),
        i.createEl("span", { cls: "paperforge-summary-value", text: n.val }));
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
      s = e.createEl("div", { cls: "paperforge-modal-field" });
    s.createEl("label", {
      cls: "paperforge-modal-label",
      text: o("label_agent"),
    });
    let a = s.createEl("select", { cls: "paperforge-modal-select" });
    for (let _ of r) {
      let p = a.createEl("option", { text: _.name, attr: { value: _.key } });
      _.key === (t.agent_platform || "opencode") && (p.selected = !0);
    }
    (a.addEventListener("change", () => {
      ((t.agent_platform = a.value),
        this._pendingSave && clearTimeout(this._pendingSave),
        (this._pendingSave = setTimeout(() => {
          (this.plugin.saveSettings(), (this._pendingSave = null));
        }, 500)));
    }),
      e.createEl("p", {
        text: o("wizard_keys_hint"),
        cls: "paperforge-modal-hint",
      }));
    let n = e.createEl("div", { cls: "paperforge-modal-field" });
    n.createEl("label", {
      cls: "paperforge-modal-label",
      text: o("field_paddleocr"),
    });
    let i = n.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "password", placeholder: "API Key" },
    });
    ((i.value = t.paddleocr_api_key || ""),
      (this._apiKeyValidated = !1),
      (this._apiKeyStatus = n.createEl("span", {
        cls: "paperforge-apikey-status",
        text: "",
      })));
    let c = n.createEl("button", {
      cls: "paperforge-step-btn",
      text: "\u9A8C\u8BC1",
    });
    (c.addEventListener("click", () => this._validateApiKey(i.value, c)),
      i.addEventListener("input", () => {
        ((t.paddleocr_api_key = i.value),
          (this._apiKeyValidated = !1),
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
    let l = e.createEl("div", { cls: "paperforge-modal-field" });
    l.createEl("label", {
      cls: "paperforge-modal-label",
      text: o("field_zotero_data"),
    });
    let d = l.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text", placeholder: o("field_zotero_placeholder") },
    });
    ((d.value = t.zotero_data_dir || ""),
      d.addEventListener("input", () => {
        ((t.zotero_data_dir = d.value),
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
      s = {
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
      a = kt.request(s, (n) => {
        ((t.disabled = !1), (t.textContent = "\u9A8C\u8BC1"));
        let i = "";
        (n.on("data", (c) => (i += c)),
          n.on("end", () => {
            try {
              let c = JSON.parse(i);
              n.statusCode === 400 && c.code === 10001
                ? ((this._apiKeyStatus.textContent =
                    "\u2713 \u5BC6\u94A5\u6709\u6548"),
                  (this._apiKeyStatus.className =
                    "paperforge-apikey-status ok"),
                  (this._apiKeyValidated = !0))
                : n.statusCode === 401
                  ? ((this._apiKeyStatus.textContent =
                      "\u9A8C\u8BC1\u5931\u8D25\uFF1A\u5BC6\u94A5\u65E0\u6548\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
                    (this._apiKeyStatus.className =
                      "paperforge-apikey-status error"),
                    (this._apiKeyValidated = !1))
                  : ((this._apiKeyStatus.textContent =
                      "\u9A8C\u8BC1\u5931\u8D25\uFF1AAPI \u8FD4\u56DE " +
                      n.statusCode +
                      "\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
                    (this._apiKeyStatus.className =
                      "paperforge-apikey-status error"),
                    (this._apiKeyValidated = !1));
            } catch (c) {
              ((this._apiKeyStatus.textContent =
                "\u9A8C\u8BC1\u5931\u8D25\uFF1A\u65E0\u6CD5\u89E3\u6790\u54CD\u5E94\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
                (this._apiKeyStatus.className =
                  "paperforge-apikey-status error"),
                (this._apiKeyValidated = !1));
            }
          }));
      });
    (a.on("error", (n) => {
      ((t.disabled = !1),
        (t.textContent = "\u9A8C\u8BC1"),
        (this._apiKeyStatus.textContent =
          "\u9A8C\u8BC1\u5931\u8D25\uFF1A\u65E0\u6CD5\u8FDE\u63A5 (" +
          n.message +
          ")\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
        (this._apiKeyStatus.className = "paperforge-apikey-status error"),
        (this._apiKeyValidated = !1));
    }),
      a.write(r),
      a.end());
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
  _modalField(e, t, r, s) {
    let a = e.createEl("div", { cls: "paperforge-modal-field" });
    a.createEl("label", { cls: "paperforge-modal-label", text: t });
    let n = a.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text" },
    });
    ((n.value = r), (n.disabled = !!s));
  }
  _modalInput(e, t, r, s, a) {
    let n = e.createEl("div", { cls: "paperforge-modal-field" });
    n.createEl("label", { cls: "paperforge-modal-label", text: t });
    let i = n.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text", placeholder: a || "" },
    });
    i.value = s;
    let c = this.plugin.settings;
    i.addEventListener("input", () => {
      ((c[r] = i.value),
        this._pendingSave && clearTimeout(this._pendingSave),
        (this._pendingSave = setTimeout(() => {
          (this.plugin.saveSettings(), (this._pendingSave = null));
        }, 500)));
    });
  }
  _modalSecret(e, t, r, s, a) {
    let n = e.createEl("div", { cls: "paperforge-modal-field" });
    n.createEl("label", { cls: "paperforge-modal-label", text: t });
    let i = n.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "password", placeholder: a || "" },
    });
    i.value = s;
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
    var n, i, c, l, d, _;
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
        r.forEach((p) => this._log("  \u2717 " + p)),
        (e.disabled = !1),
        (e.textContent = o("install_btn_retry")));
      return;
    }
    let s = (p, g = {}) =>
        new Promise((y, E) => {
          let { path: f, extraArgs: b = [] } = z(
              t.vault_path.trim(),
              this.plugin.settings,
              void 0,
              void 0
            ),
            w = (0, Le.spawn)(f, [...b, ...p], {
              cwd: t.vault_path.trim(),
              env: Se(),
              timeout: 12e4,
              ...g,
            }),
            x = "",
            m = "";
          (w.stdout.on("data", (v) => {
            let k = v.toString("utf-8");
            ((x += k), g.logStdout && this._processSetupOutput(k));
          }),
            w.stderr.on("data", (v) => {
              let k = v.toString("utf-8");
              ((m += k), this._log("[stderr] " + k.trim()));
            }),
            w.on("close", (v) => {
              v === 0
                ? y({ stdout: x, stderr: m })
                : E(new Error(m.trim() || x.trim() || `exit code ${v}`));
            }),
            w.on("error", (v) => E(v)));
        }),
      a = [
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
    (t.zotero_data_dir &&
      t.zotero_data_dir.trim() &&
      a.push("--zotero-data", t.zotero_data_dir.trim()),
      t.paddleocr_api_key &&
        t.paddleocr_api_key.trim() &&
        a.push("--paddleocr-key", t.paddleocr_api_key.trim()));
    try {
      let p = !0;
      try {
        await s(["-c", "import paperforge"]);
      } catch (g) {
        p = !1;
      }
      if (!p) {
        this._log(o("install_bootstrapping"));
        let g = this.plugin.manifest.version;
        this._log(`[install] Trying PyPI: pip install paperforge==${g}`);
        let y = ["-m", "pip", "install", "--upgrade"];
        (process.platform !== "win32" && y.push("--user"),
          y.push(`paperforge==${g}`));
        try {
          await s(y, { logStdout: !0 });
        } catch (E) {
          (this._log(
            `[install] PyPI failed, falling back to git: git+https://...@v${g}`
          ),
            console.warn(
              "[PaperForge] PyPI install failed, falling back to git:",
              (n = E.message) == null ? void 0 : n.slice(0, 200)
            ));
          let f = ["-m", "pip", "install", "--upgrade"];
          (process.platform !== "win32" && f.push("--user"),
            f.push(`git+https://github.com/LLLin000/PaperForge.git@v${g}`),
            await s(f, { logStdout: !0 }));
        }
      }
      (await s(a, { logStdout: !0, env: Se() }),
        this._log(o("install_complete")),
        (t.setup_complete = !0),
        await this.plugin.saveSettings(),
        setTimeout(() => {
          ((this._step = 5), this._render());
        }, 800));
    } catch (p) {
      console.error("PaperForge setup failed:", p.message);
      let g = this._formatSetupError(p.message);
      this._log(o("install_failed") + g);
      let y =
        (i = this._installLog.parentElement) == null
          ? void 0
          : i.createEl("button", {
              cls: "paperforge-copy-diag-btn",
              text: o("error_copy_diagnostic") || "Copy diagnostic",
            });
      if (y) {
        let E = p.message,
          f =
            ((l = (c = this.plugin) == null ? void 0 : c.settings) == null
              ? void 0
              : l.python_path) || "auto",
          b =
            ((_ = (d = this.plugin) == null ? void 0 : d.manifest) == null
              ? void 0
              : _.version) || "?",
          w = process.platform + " " + process.arch,
          x,
          m;
        try {
          x = et() || "(not found)";
        } catch (P) {
          x = "(error)";
        }
        try {
          m = z(t.vault_path.trim(), this.plugin.settings, void 0, void 0);
        } catch (P) {
          m = null;
        }
        let v = (process.env.PATH || "").length,
          k = (process.env.PATH || "").toLowerCase().includes("git"),
          R = [
            "[PaperForge Diagnostic]",
            "Category: " + g,
            "Plugin version: " + b,
            "Python: " + f,
            "Resolved Python: " + ((m == null ? void 0 : m.path) || "?"),
            "OS: " + w,
            "Vault path: " + (t.vault_path || "?"),
            "--- Git ---",
            "Git dir (resolved): " + x,
            "PATH length: " + v + " chars",
            "PATH contains git: " + k,
            "--- Raw error ---",
            E.slice(0, 2e3),
          ].join(`
`);
        y.addEventListener("click", () => {
          navigator.clipboard
            .writeText(R)
            .then(() => {
              (y.setText(o("error_copied") || "Copied!"),
                setTimeout(() => {
                  y.setText(o("error_copy_diagnostic") || "Copy diagnostic");
                }, 3e3));
            })
            .catch(() => {
              new ae.Notice("[!!] Clipboard write failed", 6e3);
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
      (!t.paddleocr_api_key || !t.paddleocr_api_key.trim()) &&
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
        let s = r
          .replace(/^\[\*\].*\d+:?\s*/, "")
          .replace(/^\[OK\]\s*/, "")
          .replace(/^\[FAIL\]\s*/, "");
        this._log("  " + s);
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
    for (let s of t) if (s.match.test(e)) return s.msg;
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
      s = this.app.vault.adapter.basePath,
      a = [
        { label: o("dir_vault"), val: s },
        { label: o("dir_resources"), val: `${s}/${r.resources_dir}` },
        {
          label: o("dir_notes"),
          val: `${s}/${r.resources_dir}/${r.literature_dir}`,
        },
        { label: o("dir_base"), val: `${s}/${r.base_dir}` },
        { label: o("dir_system"), val: `${s}/${r.system_dir}` },
        {
          label: "API Key",
          val: r.paddleocr_api_key ? o("api_key_set") : o("api_key_missing"),
        },
        {
          label: o("field_zotero_data"),
          val: r.zotero_data_dir || o("not_set"),
        },
      ];
    for (let d of a) {
      let _ = t.createEl("div", { cls: "paperforge-summary-row" });
      (_.createEl("span", { cls: "paperforge-summary-label", text: d.label }),
        _.createEl("span", { cls: "paperforge-summary-value", text: d.val }));
    }
    let n = t.createEl("div", { cls: "paperforge-summary-row" });
    n.createEl("span", { cls: "paperforge-summary-label", text: "PaperForge" });
    let i = n.createEl("span", {
      cls: "paperforge-summary-value",
      text: "\u2014",
    });
    {
      let d = s,
        { path: _, extraArgs: p = [] } = z(
          d,
          this.plugin.settings,
          void 0,
          void 0
        );
      (0, Le.execFile)(
        _,
        [...p, "-c", "import paperforge; print(paperforge.__version__)"],
        { cwd: d, timeout: 1e4 },
        (g, y) => {
          !g && y && (i.textContent = "v" + y.trim());
        }
      );
    }
    for (let d of a) {
      let _ = t.createEl("div", { cls: "paperforge-summary-row" });
      (_.createEl("span", { cls: "paperforge-summary-label", text: d.label }),
        _.createEl("span", { cls: "paperforge-summary-value", text: d.val }));
    }
    e.createEl("h3", { text: o("complete_next") });
    let c = e.createEl("div", { cls: "paperforge-nextsteps" }),
      l = [
        [o("complete_step4"), o("complete_step4_desc")],
        [
          "",
          `${o("complete_export_path")} ${s}/${r.system_dir}/PaperForge/exports/`,
        ],
        [o("complete_step1"), o("complete_step1_desc")],
        [o("complete_step2"), o("complete_step2_desc")],
        [o("complete_step3"), o("complete_step3_desc")],
      ];
    for (let [d, _] of l) {
      let p = c.createEl("div", { cls: "paperforge-nextstep-item" });
      (d && p.createEl("strong", { text: d }), p.createEl("span", { text: _ }));
    }
  }
};
var Re = K(require("fs")),
  We = K(require("path")),
  St = require("child_process");
function Pt(u) {
  return We.join(u, "System", "PaperForge", "cache", "ocr_maintenance.json");
}
function Ct(u) {
  try {
    let h = Pt(u),
      e = Re.readFileSync(h, "utf-8");
    return JSON.parse(e);
  } catch (h) {
    return null;
  }
}
function Ie(u, h) {
  let e = Pt(u),
    t = We.dirname(e);
  (Re.mkdirSync(t, { recursive: !0 }),
    Re.writeFileSync(e, JSON.stringify(h, null, 2), "utf-8"));
}
function wt(u, h, e) {
  return new Promise((t, r) => {
    (0, St.execFile)(u, h, e, (s, a) => {
      s ? r(s) : t(a);
    });
  });
}
async function it(u, h, e, t) {
  let r = await wt(h, [...e, "-m", "paperforge", "ocr", "list", "--manifest"], {
      cwd: u,
      timeout: 3e4,
    }),
    s = JSON.parse(r);
  if (t) {
    let d = Object.keys(t.manifest),
      _ = Object.keys(s);
    if (d.length === _.length && d.every((g) => t.manifest[g] === s[g]))
      return {
        data: Object.values(t.papers).filter((y) => y.visible_in_maintenance),
        changed: !1,
      };
  }
  let a = Object.keys(s).filter(
      (d) => !(t != null && t.manifest[d]) || t.manifest[d] !== s[d]
    ),
    n = await wt(
      h,
      [...e, "-m", "paperforge", "ocr", "list", "--json", "--keys", ...a],
      { cwd: u, timeout: 3e4 }
    ),
    i = JSON.parse(n),
    c = { manifest: s, papers: {}, cached_at: new Date().toISOString() };
  if (t != null && t.papers)
    for (let d of Object.keys(s)) t.papers[d] && (c.papers[d] = t.papers[d]);
  for (let d of i) c.papers[d.key] = d;
  return (
    Ie(u, c),
    {
      data: Object.values(c.papers).filter((d) => d.visible_in_maintenance),
      changed: !0,
    }
  );
}
var Zt = ["EMBED", "OCR_REBUILD", "OCR_REDO"];
function ot(u, h) {
  var a, n;
  let t = (h + u).split(`
`),
    r = (a = t.pop()) != null ? a : "",
    s = [];
  for (let i of t)
    for (let c of Zt) {
      let l = c.length;
      if (i.startsWith(c + "_START:")) {
        let d = parseInt(i.slice(l + 7), 10) || 0;
        s.push({ prefix: c, event: "START", total: d });
        break;
      }
      if (i.startsWith(c + "_PROGRESS:")) {
        let _ = i.slice(l + 10).split(":");
        s.push({
          prefix: c,
          event: "PROGRESS",
          current: parseInt(_[0], 10) || 0,
          total: parseInt(_[1], 10) || 0,
          key: (n = _[2]) != null ? n : "",
        });
        break;
      }
      if (i === c + "_DONE" || i.startsWith(c + "_DONE:")) {
        s.push({ prefix: c, event: "DONE" });
        break;
      }
    }
  return { events: s, buffer: r };
}
var Ze = class extends C.PluginSettingTab {
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
    this.activeTab = "setup";
    this._buildState = "idle";
    this._buildProgress = { current: 0, total: 0, key: "" };
    this.plugin = t;
  }
  _refreshPfConfig() {
    this._pfConfig = this.plugin.readPaperforgeJson();
  }
  display() {
    let { containerEl: e } = this;
    if (
      (e.empty(),
      this._refreshPfConfig(),
      !document.getElementById("paperforge-tab-styles"))
    ) {
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
                .paperforge-modal-subtitle { color: var(--text-muted); font-size: 13px; margin-bottom: 12px; }
                .paperforge-modal-item { font-size: 13px; margin-left: 8px; color: var(--text-muted); }
            `),
        document.head.appendChild(a));
    }
    let t = e.createDiv({ cls: "paperforge-settings-tabs" }),
      r = [
        { id: "setup", label: o("tab_setup") || "\u5B89\u88C5" },
        { id: "features", label: o("tab_features") || "\u529F\u80FD" },
        { id: "maintenance", label: o("tab_maintenance") || "\u7EF4\u62A4" },
        { id: "release-notes", label: "\u66F4\u65B0\u4E0E\u624B\u518C" },
      ],
      s = {};
    (r.forEach((a) => {
      t.createEl("button", {
        cls:
          "paperforge-settings-tab" +
          (a.id === this.activeTab ? " paperforge-settings-tab--active" : ""),
        text: a.label,
      }).addEventListener("click", () => {
        ((this.activeTab = a.id), this.display());
      });
    }),
      r.forEach((a) => {
        s[a.id] = e.createDiv({
          cls:
            "paperforge-tab-content" +
            (a.id === this.activeTab ? " paperforge-tab-content--active" : ""),
        });
      }),
      this.activeTab === "setup"
        ? this._renderSetupTab(s.setup)
        : this.activeTab === "features"
          ? this._renderFeaturesTab(s.features)
          : this.activeTab === "maintenance"
            ? this._renderMaintenanceTab(s.maintenance)
            : this._renderReleaseNotesTab(s["release-notes"]));
  }
  _renderSetupTab(e) {
    let t = this.app.vault.adapter.basePath;
    (this.plugin.settings.vault_path ||
      ((this.plugin.settings.vault_path = t), this._debouncedSave()),
      this.plugin.settings.setup_complete &&
        (V.existsSync(te.join(t, "paperforge.json")) ||
          ((this.plugin.settings.setup_complete = !1), this._debouncedSave())),
      e.createEl("h2", { text: o("header_title") || "PaperForge" }),
      e.createEl("p", { text: o("desc"), cls: "paperforge-settings-desc" }));
    let s = e
      .createEl("div", { cls: "paperforge-setup-bar" })
      .createEl("span", { cls: "paperforge-setup-label" });
    this.plugin.settings.setup_complete
      ? (s.setText(o("setup_done")), s.addClass("paperforge-setup-done"))
      : (s.setText(o("setup_pending")), s.addClass("paperforge-setup-pending"));
    let a = this.app.vault.adapter.basePath,
      n = z(a, this.plugin.settings, void 0, void 0),
      i = n.path,
      c = this.plugin.settings._python_path_stale ? "stale" : n.source,
      l = new C.Setting(e)
        .setName(o("field_python_interp"))
        .setDesc(this._getPythonDesc(i, c));
    this._pythonInterpDescEl = l.descEl;
    let d = new C.Setting(e).setName(o("field_python_custom")).setDesc("");
    ((this._customPathDescEl = d.descEl),
      d.addText((x) => {
        x.setPlaceholder("e.g. C:\\Python310\\python.exe")
          .setValue(this.plugin.settings.python_path || "")
          .onChange((m) => {
            if (
              ((this.plugin.settings.python_path = m),
              this.plugin.saveSettings(),
              m && m.trim())
            ) {
              let R = V.existsSync(m.trim());
              this.plugin.settings._python_path_stale = !R;
            } else this.plugin.settings._python_path_stale = !1;
            let v = z(
                this.app.vault.adapter.basePath,
                this.plugin.settings,
                void 0,
                void 0
              ),
              k = this.plugin.settings._python_path_stale ? "stale" : v.source;
            this._pythonInterpDescEl &&
              (this._pythonInterpDescEl.textContent = this._getPythonDesc(
                v.path,
                k
              ));
          });
      }),
      d.addButton((x) => {
        x.setButtonText(o("btn_validate")).onClick(() =>
          this._validatePythonOverride()
        );
      }),
      e.createEl("h3", { text: o("runtime_health") }),
      e.createEl("p", {
        text: o("runtime_health_desc"),
        cls: "paperforge-settings-desc",
      }));
    let _ = new C.Setting(e)
        .setName("PaperForge")
        .setDesc(o("runtime_health_checking")),
      p = _.descEl.createEl("span", { cls: "paperforge-runtime-badge" }),
      g = null;
    _.addButton((x) => {
      ((g = x),
        x
          .setButtonText(o("runtime_health_sync"))
          .setDisabled(!0)
          .onClick(() => this._syncRuntime(x)));
    });
    {
      let x = this.app.vault.adapter.basePath,
        { path: m, extraArgs: v = [] } = z(
          x,
          this.plugin.settings,
          void 0,
          void 0
        ),
        k = this.plugin.manifest.version || "?";
      (0, G.execFile)(
        m,
        [...v, "-c", "import paperforge; print(paperforge.__version__)"],
        { cwd: x, timeout: 1e4 },
        (R, P) => {
          let O = this.plugin.settings.setup_complete,
            D = !R && P ? P.trim() : null,
            j = D
              ? `${o("runtime_health_plugin_ver").replace("{0}", k)} \u2192 ${o("runtime_health_package_ver").replace("{0}", D)}`
              : O
                ? `Plugin v${k} \u2192 Python package not installed. Click "Sync Runtime" to install.`
                : `Plugin v${k} \u2192 Not configured. Please open the setup wizard first.`;
          (_.setDesc(j),
            D === k
              ? (p.setText(o("runtime_health_match")),
                (p.className = "paperforge-runtime-badge match"),
                g && g.setDisabled(!0))
              : D
                ? (p.setText(o("runtime_health_mismatch")),
                  (p.className = "paperforge-runtime-badge mismatch"),
                  g && g.setDisabled(!1))
                : (p.setText(O ? "Not installed" : "Setup needed"),
                  (p.className = "paperforge-runtime-badge missing"),
                  g && g.setDisabled(!1)));
        }
      );
    }
    (e.createEl("h3", { text: o("section_prep") }),
      e.createEl("p", {
        text: o("section_prep_desc"),
        cls: "paperforge-settings-desc",
      }));
    let y = e.createEl("div", { cls: "paperforge-guide" }),
      E = [
        ["prep_python", "prep_python_desc"],
        ["prep_zotero", "prep_zotero_desc"],
        ["prep_bbt", "prep_bbt_desc"],
        ["prep_key", "prep_key_desc"],
      ];
    for (let [x, m] of E) {
      let v = y.createEl("div", { cls: "paperforge-guide-item" });
      (v.createEl("strong", { text: o(x) }),
        v.createEl("span", { text: " \u2014 " + o(m) }));
    }
    this._checkEl = e.createEl("div", { cls: "paperforge-message" });
    let f = !this.plugin.settings.setup_complete;
    (new C.Setting(e)
      .setName(o(f ? "btn_install" : "btn_reconfig"))
      .setDesc(o(f ? "btn_install_desc" : "btn_reconfig_desc"))
      .addButton((x) => {
        x.setButtonText(o(f ? "btn_install" : "btn_reconfig"))
          .setCta()
          .onClick(() => {
            f
              ? this._preCheck(() => {
                  new Oe(this.app, this.plugin).open();
                })
              : new Oe(this.app, this.plugin).open();
          });
      }),
      e.createEl("h3", { text: o("section_guide") }));
    let b = e.createEl("div", { cls: "paperforge-guide" }),
      w = [
        ["guide_open", "guide_open_desc"],
        ["guide_sync", "guide_sync_desc"],
        ["guide_ocr", "guide_ocr_desc"],
      ];
    for (let [x, m] of w) {
      let v = b.createEl("div", { cls: "paperforge-guide-item" });
      (v.createEl("strong", { text: o(x) }),
        v.createEl("span", { text: " \u2014 " + o(m) }));
    }
    if (this.plugin.settings.setup_complete) {
      e.createEl("h3", { text: o("section_config") });
      let x = e.createEl("div", { cls: "paperforge-summary" }),
        m = this.plugin.settings,
        v = this._pfConfig,
        k = [
          { label: o("dir_vault"), val: t },
          {
            label: o("dir_resources"),
            val: `${t}/${v == null ? void 0 : v.resources_dir}`,
          },
          {
            label: "  " + o("dir_notes"),
            val: `${t}/${v == null ? void 0 : v.resources_dir}/${v == null ? void 0 : v.literature_dir}`,
          },
          {
            label: o("dir_base"),
            val: `${t}/${v == null ? void 0 : v.base_dir}`,
          },
          {
            label: o("dir_system"),
            val: `${t}/${v == null ? void 0 : v.system_dir}`,
          },
          {
            label: "API Key",
            val: m.paddleocr_api_key ? o("api_key_set") : o("api_key_missing"),
          },
          {
            label: o("field_zotero_data"),
            val: m.zotero_data_dir || o("not_set"),
          },
        ];
      for (let R of k) {
        let P = x.createEl("div", { cls: "paperforge-summary-row" });
        (P.createEl("span", { cls: "paperforge-summary-label", text: R.label }),
          P.createEl("span", { cls: "paperforge-summary-value", text: R.val }));
      }
    }
  }
  _execMemoryStatus(e, t, r) {
    (0, G.exec)(
      `"${e}" -m paperforge --vault "${t}" memory status --json`,
      { encoding: "utf-8", timeout: 15e3 },
      (s, a) => {
        if (s) {
          r("Status unavailable");
          return;
        }
        try {
          let n = JSON.parse(a);
          if (n.ok) {
            let i = n.data,
              c = i.fresh ? "fresh" : "stale";
            r(
              `Papers: ${i.paper_count_db} | ${c}${i.needs_rebuild ? " - needs rebuild" : ""}`
            );
          } else r("DB not found. Run paperforge memory build.");
        } catch (n) {
          r("Could not parse status.");
        }
      }
    );
  }
  _execEmbedStatus(e, t, r) {
    (0, G.exec)(
      `"${e}" -m paperforge --vault "${t}" embed status --json`,
      { encoding: "utf-8", timeout: 15e3 },
      (s, a) => {
        if (s) {
          r("Status unavailable");
          return;
        }
        try {
          let n = JSON.parse(a);
          n.ok
            ? r(
                `Chunks: ${n.data.chunk_count} | ${n.data.model} | ${n.data.mode}`
              )
            : r("Could not parse status.");
        } catch (n) {
          r("Could not parse status.");
        }
      }
    );
  }
  _callPython(e, t) {
    let r = this.app.vault.adapter.basePath,
      s = me(r, this.plugin.settings),
      a = [...s.extraArgs, "-m", "paperforge", "--vault", r, ...e];
    if (t && t.stream) {
      let n = (0, G.spawn)(s.path, a, {
        cwd: r,
        env: t.env || process.env,
        windowsHide: !0,
      });
      return (
        t.onData && n.stdout.on("data", t.onData),
        t.onStderr && n.stderr.on("data", t.onStderr),
        t.onError && n.on("error", t.onError),
        n.on("close", t.onClose),
        n
      );
    }
    return (
      (0, G.execFile)(
        s.path,
        a,
        { cwd: r, timeout: (t && t.timeout) || 6e4 },
        (n, i, c) => {
          t && t.onClose && t.onClose(n ? 1 : 0, i, c);
        }
      ),
      null
    );
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
    let s = e.createEl("button", {
      cls: "paperforge-rebuild-btn",
      text: o("feat_memory_rebuild_btn"),
    });
    ((s.title = "Rebuild memory database"),
      (s.onclick = () => {
        let n = this.app.vault.adapter.basePath,
          i = me(n, this.plugin.settings);
        if (!i.path) {
          new C.Notice(o("feat_no_python"));
          return;
        }
        (console.log("[PaperForge] Rebuilding memory:", i.path),
          s.setText(o("feat_memory_rebuilding")),
          s.setAttr("disabled", ""),
          this._callPython(["memory", "build"], {
            timeout: 6e4,
            onClose: (c, l, d) => {
              (console.log(
                "[PaperForge] memory build exit:",
                c ? "FAIL:" + c : "OK",
                (l || "").slice(0, 200),
                (d || "").slice(0, 200)
              ),
                s.setText(o("feat_memory_rebuild_btn")),
                s.removeAttribute("disabled"),
                c === 0
                  ? new C.Notice(o("feat_memory_rebuild_done"))
                  : new C.Notice(
                      o("feat_memory_rebuild_failed") +
                        (d ? " " + d.slice(0, 80) : "")
                    ),
                (this._memoryStatusText = He(n)),
                this._refreshSnapshots(n));
            },
          }));
      }));
    let a = e.createEl("button", {
      cls: "paperforge-refresh-btn",
      text: "\u21BB",
    });
    ((a.title = "Sync now"),
      (a.onclick = () => {
        ((this._memoryStatusText = null), this._runManualSync());
      }));
  }
  _getBuildCommand(e) {
    let t = this.app.vault.adapter.basePath,
      r = z(t, e, void 0, void 0);
    return r.path ? `"${r.path}" -m paperforge --vault "${t}" sync` : null;
  }
  _runManualSync() {
    let e = this.app.vault.adapter.basePath;
    if (!me(e, this.plugin.settings).path) return;
    let r = document.querySelector(".paperforge-memory-status");
    (r && this._renderMemoryStatusText(r, "Checking...", "syncing"),
      (this.plugin._autoSyncRunning = !0),
      this._callPython(["sync"], {
        timeout: 12e4,
        onClose: (s) => {
          ((this.plugin._autoSyncRunning = !1),
            (this._memoryStatusText = null),
            s === 0 &&
              ((this._lastSyncTime = new Date().toLocaleTimeString()),
              (this.plugin._lastSyncTime = this._lastSyncTime)),
            this.display(),
            this._refreshSnapshots(e),
            Ke(this.app, this.plugin, e));
        },
      }));
  }
  _refreshSnapshots(e) {
    let t = me(e, this.plugin.settings),
      r = [
        ...t.extraArgs,
        "-m",
        "paperforge",
        "--vault",
        e,
        "runtime-health",
        "--json",
      ];
    ((this._refreshPending = !0),
      (0, G.execFile)(
        t.path,
        r,
        { cwd: e, timeout: 3e4, windowsHide: !0 },
        (s, a, n) => {
          ((this._refreshPending = !1),
            (this._memoryStatusText = He(e)),
            (this._embedStatusText = Ce(e)),
            this.display());
        }
      ));
  }
  _renderFeaturesTab(e) {
    e.createEl("h3", { text: "Skills" });
    let t = e.createEl("div", { cls: "paperforge-desc-box" });
    (t.setText(o("feat_skills_desc")),
      t.createEl("br"),
      t.createEl("span", { text: o("feat_skills_system") }));
    let r = {
        opencode: "OpenCode",
        claude: "Claude Code",
        codex: "Codex",
        cursor: "Cursor",
        windsurf: "Windsurf",
        github_copilot: "GitHub Copilot",
        gemini: "Gemini CLI",
      },
      s = {
        opencode: ".opencode/skills",
        claude: ".claude/skills",
        codex: ".codex/skills",
        cursor: ".cursor/skills",
        windsurf: ".windsurf/skills",
        github_copilot: ".github/skills",
        gemini: ".gemini/skills",
      },
      a = this.app.vault.adapter.basePath,
      n = this.plugin.settings.selected_skill_platform || "opencode";
    new C.Setting(e)
      .setName(o("feat_agent_platform"))
      .setDesc(o("feat_agent_platform_desc"))
      .addDropdown((m) => {
        (Object.entries(r).forEach(([v, k]) => m.addOption(v, k)),
          m.setValue(n).onChange((v) => {
            ((this.plugin.settings.selected_skill_platform = v),
              this.plugin.saveSettings(),
              this.display());
          }));
      })
      .addExtraButton((m) => {
        m.setIcon("folder")
          .setTooltip("Open skills folder")
          .onClick(() => {
            let v = s[n] || ".opencode/skills",
              k = te.join(a, v);
            V.existsSync(k)
              ? (0, G.exec)(`start "" "${k}"`)
              : new C.Notice(`Skills folder not found: ${v}`);
          });
      });
    let i = te.join(a, s[n]),
      c = [],
      l = [];
    V.existsSync(i) &&
      V.readdirSync(i, { withFileTypes: !0 }).forEach((m) => {
        if (!m.isDirectory()) return;
        let v = te.join(i, m.name, "SKILL.md");
        if (!V.existsSync(v)) return;
        let k = V.readFileSync(v, "utf-8"),
          R = k.match(/^name:\s*(.+)$/m),
          P = k.split(`
`),
          O = P.findIndex((N) => /^description:/.test(N)),
          D = "";
        if (O >= 0) {
          let N = P[O].match(/^description:\s*(.+)$/);
          if (N && N[1] && N[1] !== ">" && N[1] !== "|-" && N[1] !== "|")
            D = N[1].trim();
          else {
            for (
              let U = O + 1;
              U < P.length && (/^\s{2,}/.test(P[U]) || P[U].trim() === "");
              U++
            )
              D += P[U].trim() + " ";
            D = D.trim();
          }
        }
        let j = k.match(/^source:\s*(.+)$/m),
          H = k.match(/^disable-model-invocation:\s*(.+)$/m),
          B = k.match(/^version:\s*(.+)$/m),
          S = {
            name: R ? R[1].trim() : m.name,
            desc: D,
            source: j ? j[1].trim() : "user",
            disabled: H && H[1].trim() === "true",
            version: B ? B[1].trim() : "",
            path: v,
            content: k,
            dirName: m.name,
          };
        S.source === "paperforge" ? c.push(S) : l.push(S);
      });
    let d = e.createEl("div", { cls: "paperforge-skills-box" }),
      _ = (m, v, k) => {
        if (v.length === 0) return;
        let R = d.createEl("div", { cls: "paperforge-skills-group" }),
          P = R.createEl("div", { cls: "paperforge-skills-collapse-header" }),
          O = R.createEl("div", { cls: "paperforge-skills-collapse-content" }),
          D = P.createEl("span", {
            text: "\u25BC",
            cls: "paperforge-skills-arrow",
          });
        (P.createEl("h4", {
          text: `${m} (${v.length})`,
          cls: "paperforge-skills-subheader",
        }),
          v.forEach((B) => {
            let S = B.name + (B.version ? " v" + B.version : ""),
              N = k ? " [system]" : " [user]",
              U = B.desc || "",
              $ = new C.Setting(O).setName(S + N).setDesc(U);
            (($.settingEl.style.opacity = B.disabled ? "0.4" : "1"),
              $.addToggle((L) => {
                L.setValue(!B.disabled).onChange((ne) => {
                  let Y = !ne,
                    re = B.content.match(/^disable-model-invocation:\s*(.+)$/m)
                      ? B.content.replace(
                          /^disable-model-invocation:\s*.+$/m,
                          `disable-model-invocation: ${Y}`
                        )
                      : B.content.replace(
                          /^(---\r?\n)/,
                          `$1disable-model-invocation: ${Y}
`
                        );
                  (V.writeFileSync(B.path, re, "utf-8"),
                    (B.disabled = Y),
                    (B.content = re),
                    ($.settingEl.style.opacity = B.disabled ? "0.4" : "1"));
                });
              }));
          }));
        let j = k ? "system" : "user";
        ((this._skillsCollapsed[j] || !1) &&
          ((O.style.display = "none"), (D.style.transform = "rotate(-90deg)")),
          P.addEventListener("click", () => {
            (O.style.display !== "none"
              ? ((O.style.display = "none"),
                (D.style.transform = "rotate(-90deg)"))
              : ((O.style.display = ""), (D.style.transform = "rotate(0deg)")),
              (this._skillsCollapsed[j] = O.style.display === "none"));
          }));
      };
    (_("System Skills", c, !0),
      _("User Skills", l, !1),
      c.length === 0 &&
        l.length === 0 &&
        d.createEl("p", {
          text: `No skills found in ${s[n]}. Run setup to deploy skills.`,
          cls: "setting-item-description",
        }),
      this._advCollapsed === void 0 && (this._advCollapsed = !0));
    let p = e.createEl("div", { cls: "paperforge-collapsible-header" }),
      g = p.createEl("span", {
        text: "\u25B6",
        cls: "paperforge-collapsible-arrow",
      });
    g.style.transform = this._advCollapsed ? "rotate(0deg)" : "rotate(90deg)";
    let y = p.createEl("span", {
        cls: "paperforge-collapsible-title",
        text: "Advanced",
      }),
      E = p.createEl("span", {
        cls: "paperforge-collapsible-sub",
        text: "Memory + Vector DB + Embedding",
      }),
      f = e.createEl("div", { cls: "paperforge-collapsible-content" });
    ((f.style.display = this._advCollapsed ? "none" : ""),
      p.addEventListener("click", () => {
        ((this._advCollapsed = !this._advCollapsed),
          (f.style.display = this._advCollapsed ? "none" : ""),
          (g.style.transform = this._advCollapsed
            ? "rotate(0deg)"
            : "rotate(90deg)"));
      }),
      f.createEl("h4", { text: "Memory Layer" }),
      f
        .createEl("div", { cls: "paperforge-desc-box" })
        .setText(o("feat_memory_desc")));
    let w = f.createEl("div", { cls: "paperforge-memory-status" }),
      x = this.app.vault.adapter.basePath;
    (this.plugin._lastSyncTime &&
      !this._lastSyncTime &&
      (this._lastSyncTime = this.plugin._lastSyncTime),
      this._memoryStatusText === null && (this._memoryStatusText = He(x)),
      this._renderMemoryStatusText(
        w,
        this._memoryStatusText,
        this._lastSyncTime
      ),
      this._renderVectorSection(f));
  }
  _renderVectorSection(e) {
    var c;
    if (
      (e.createEl("h4", { text: "Vector Database" }),
      this.plugin.settings.features ||
        (this.plugin.settings.features = { memory_layer: !0, vector_db: !1 }),
      e
        .createEl("div", { cls: "paperforge-desc-box" })
        .setText(o("feat_vector_desc")),
      new C.Setting(e)
        .setName(o("feat_vector_enable"))
        .setDesc(o("feat_vector_enable_desc"))
        .addToggle((l) => {
          l.setValue(!!this.plugin.settings.features.vector_db).onChange(
            (d) => {
              ((this.plugin.settings.features.vector_db = d),
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
      s = e.createEl("div", { cls: "paperforge-vec-header" }),
      a = s.createEl("span", {
        text: "\u25BC",
        cls: "paperforge-skills-arrow",
      });
    s.createEl("span", {
      cls: "paperforge-vec-header-label",
      text: o("feat_vector_config_label"),
    });
    let n = e.createEl("div", { cls: "paperforge-vector-config" }),
      i = (l) => {
        ((n.style.display = l ? "none" : ""),
          (a.style.transform = l ? "rotate(-90deg)" : "rotate(0deg)"));
      };
    if (
      (i(nt(this._featurePanelsCollapsed, "vectorConfig", !1)),
      s.addEventListener("click", () => {
        let l = bt(this._featurePanelsCollapsed, "vectorConfig", !1);
        i(l);
      }),
      this._vectorDepsOk === !0)
    ) {
      this._renderVectorReady(n, r);
      return;
    }
    if (this._vectorDepsOk === !1) {
      this._renderVectorNoDeps(n);
      return;
    }
    if (this._vectorDepsOk === null) {
      let l = Ve(r);
      ((this._vectorDepsOk = l && (c = l.deps_installed) != null ? c : !1),
        this._vectorDepsOk && (this._embedStatusText = Ce(r)),
        this.display());
    }
  }
  _renderApiConfig(e) {
    (new C.Setting(e)
      .setName(o("feat_openai_key"))
      .setDesc(o("feat_openai_key_desc"))
      .addText((t) => {
        t.setPlaceholder("sk-...")
          .setValue(this.plugin.settings.vector_db_api_key || "")
          .onChange((r) => {
            ((this.plugin.settings.vector_db_api_key = r),
              this.plugin.saveSettings());
          });
      }),
      new C.Setting(e)
        .setName(o("feat_api_base_url"))
        .setDesc(o("feat_api_base_url_desc"))
        .addText((t) => {
          t.setPlaceholder("https://api.openai.com/v1")
            .setValue(this.plugin.settings.vector_db_api_base || "")
            .onChange((r) => {
              ((this.plugin.settings.vector_db_api_base = r),
                this.plugin.saveSettings());
            });
        }),
      new C.Setting(e)
        .setName(o("feat_api_model"))
        .setDesc(o("feat_api_model_desc"))
        .addText((t) => {
          t.setPlaceholder("text-embedding-3-small")
            .setValue(
              this.plugin.settings.vector_db_api_model ||
                "text-embedding-3-small"
            )
            .onChange((r) => {
              ((this.plugin.settings.vector_db_api_model = r),
                this.plugin.saveSettings());
            });
        }));
  }
  _renderVectorNoDeps(e) {
    (e
      .createEl("div", { cls: "paperforge-desc-box" })
      .setText(o("feat_deps_missing")),
      new C.Setting(e)
        .setName(o("feat_install_deps"))
        .setDesc(o("feat_install_deps_desc"))
        .addButton((r) => {
          r.setButtonText(o("feat_install_btn"))
            .setCta()
            .onClick(async () => {
              let s = this.app.vault.adapter.basePath,
                a = me(s, this.plugin.settings);
              if (!a.path) {
                new C.Notice(o("feat_no_python"));
                return;
              }
              (r.setButtonText(o("feat_installing")), r.setDisabled(!0));
              let n = "chromadb openai",
                i = new C.Notice(
                  o("feat_installing_pkgs").replace("{pkgs}", n),
                  0
                );
              try {
                let c = Object.assign({}, process.env, {
                    PYTHONIOENCODING: "utf-8",
                    PYTHONUTF8: "1",
                  }),
                  l = n.split(" ");
                (await new Promise((d, _) => {
                  (0, G.execFile)(
                    a.path,
                    [...a.extraArgs, "-m", "pip", "install", ...l],
                    { cwd: s, timeout: 3e5, env: c, windowsHide: !0 },
                    (p) => {
                      p ? _(p) : d();
                    }
                  );
                }),
                  i.hide(),
                  new C.Notice(o("feat_install_done")),
                  (this._vectorDepsOk = !0),
                  (this._embedStatusText = Ce(s)),
                  this.display());
              } catch (c) {
                (i.hide(),
                  new C.Notice(
                    o("feat_install_failed") + (c.stderr || c.message || c)
                  ),
                  r.setButtonText(o("feat_retry_btn")),
                  r.setDisabled(!1));
              }
            });
        }));
  }
  _renderVectorReady(e, t) {
    (e.createEl("div", { cls: "paperforge-desc-box" }).setText(Ce(t)),
      this._renderApiConfig(e));
    let s = e.createEl("div", { cls: "paperforge-embed-section" });
    s.createEl("div", { cls: "paperforge-embed-header" }).createEl("span", {
      text: o("retrieval_rebuild_vectors"),
      cls: "setting-item-name",
    });
    let n = s.createEl("div", { cls: "paperforge-embed-controls" }),
      i = s.createEl("div", {
        cls: "paperforge-embed-status-text",
        attr: { "aria-live": "polite" },
      });
    (() => {
      (n.empty(), i.empty());
      let l = Ve(t),
        d = l == null ? void 0 : l.build_state,
        _ = d && typeof d == "object" && !Array.isArray(d) ? d : {};
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
      let { current: p, total: g, key: y } = this.plugin._embedProgress,
        E =
          typeof (l == null ? void 0 : l.body_chunk_count) == "number"
            ? l.body_chunk_count
            : 0,
        f =
          typeof (l == null ? void 0 : l.object_chunk_count) == "number"
            ? l.object_chunk_count
            : 0,
        w =
          (typeof (l == null ? void 0 : l.chunk_count) == "number"
            ? l.chunk_count
            : 0) +
          E +
          f,
        x = w > 0,
        m = l !== null && typeof l.corrupted == "boolean" && l.corrupted,
        v = !!this.plugin._embedProcess,
        k = !this.plugin._embedProcess && _.status === "running",
        R =
          (l == null ? void 0 : l.deps_installed) !== void 0
            ? !!l.deps_installed
            : !0,
        P = typeof _.status == "string" ? _.status : "",
        O = typeof _.message == "string" ? _.message : "",
        D = (S) => {
          var $;
          if (S === "--resume" && x && !m) {
            let L = o("retrieval_rebuild_warning").replace("{n}", String(w));
            if (!confirm(L)) return;
          }
          if (S === "--force" && x && !m) {
            let L =
              "Force rebuild will replace " +
              w +
              " existing chunk(s). Continue?";
            if (!confirm(L)) return;
          }
          if (!me(t, this.plugin.settings).path) {
            new C.Notice(o("retrieval_no_python"));
            return;
          }
          let U = Object.assign({}, process.env, {
            PYTHONIOENCODING: "utf-8",
            PYTHONUTF8: "1",
            VECTOR_DB_API_KEY: this.plugin.settings.vector_db_api_key || "",
            VECTOR_DB_API_BASE: this.plugin.settings.vector_db_api_base || "",
            VECTOR_DB_API_MODEL: this.plugin.settings.vector_db_api_model || "",
          });
          ((this.plugin._embedStderr = ""),
            (this.plugin._embedProgress = { current: 0, total: 0, key: "" }),
            (this.plugin._embedProcess = this._callPython(
              ["embed", "build", S],
              {
                stream: !0,
                env: U,
                onData: (L) => {
                  var re;
                  let ne =
                      typeof L == "string"
                        ? L
                        : Buffer.isBuffer(L)
                          ? L.toString("utf-8")
                          : String(L),
                    { events: Y, buffer: ce } = ot(
                      ne,
                      (re = this.plugin._embedBuffer) != null ? re : ""
                    );
                  this.plugin._embedBuffer = ce;
                  for (let q of Y)
                    q.event === "START"
                      ? (this.plugin._embedProgress.total = q.total || 0)
                      : q.event === "PROGRESS"
                        ? ((this.plugin._embedProgress.current =
                            q.current || 0),
                          (this.plugin._embedProgress.key = q.key || ""))
                        : q.event === "DONE" &&
                          ((this.plugin._embedProcess = null),
                          (this.plugin._embedProgress.current =
                            this.plugin._embedProgress.total));
                  this.display();
                },
                onStderr: (L) => {
                  (this.plugin._embedStderr || (this.plugin._embedStderr = ""),
                    (this.plugin._embedStderr += String(L)));
                },
                onError: (L) => {
                  ((this.plugin._embedProcess = null),
                    new C.Notice(
                      o("feat_build_failed") + ": " + (L.message || L)
                    ),
                    this.display());
                },
                onClose: (L) => {
                  var ne;
                  if (
                    (clearInterval(
                      (ne = this.plugin._embedPollInterval) != null
                        ? ne
                        : void 0
                    ),
                    (this.plugin._embedPollInterval = null),
                    (this.plugin._embedProcess = null),
                    L === 0)
                  )
                    ((this.plugin._embedProgress.current =
                      this.plugin._embedProgress.total),
                      this.plugin.saveSettings(),
                      (this._embedStatusText = Ce(t)),
                      new C.Notice(o("feat_build_complete")));
                  else {
                    this._embedStatusText = null;
                    let Y = (this.plugin._embedStderr || "").slice(0, 200);
                    new C.Notice(
                      o("feat_build_failed") + (Y ? ": " + Y : ""),
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
              ($ = this.plugin._embedPollInterval) != null ? $ : void 0
            ),
            (this.plugin._embedPollInterval = setInterval(() => {
              this.plugin._embedPolling ||
                ((this.plugin._embedPolling = !0),
                this._callPython(["embed", "status", "--json"], {
                  timeout: 5e3,
                  onClose: (L, ne) => {
                    var Y;
                    if (((this.plugin._embedPolling = !1), L === 0 && ne))
                      try {
                        let re = JSON.parse(ne).data;
                        if (re && re.build_state) {
                          let q = re.build_state;
                          ((q.status === "stopping" || q.status === "idle") &&
                            this.plugin._embedProcess &&
                            ((this.plugin._embedProcess = null),
                            clearInterval(
                              (Y = this.plugin._embedPollInterval) != null
                                ? Y
                                : void 0
                            ),
                            (this.plugin._embedPollInterval = null),
                            this.display()),
                            q.current !== void 0 &&
                              q.total !== void 0 &&
                              ((this.plugin._embedProgress.current = q.current),
                              (this.plugin._embedProgress.total = q.total || 1),
                              (this.plugin._embedProgress.key =
                                q.paper_id || "")));
                        }
                      } catch (ce) {}
                  },
                }));
            }, 2e3)),
            this.display());
        },
        j = Ae(t),
        H = !1;
      j &&
        typeof j.summary == "object" &&
        j.summary !== null &&
        "status" in j.summary &&
        (H = j.summary.status === "version_mismatch");
      let B;
      switch (
        (R
          ? H
            ? (B = "runtime-mismatch")
            : P === "stopping"
              ? (B = "stopping")
              : v && P === "running"
                ? (B = "building")
                : P === "failed"
                  ? (B = "failed")
                  : P === "stopped"
                    ? (B = "stopped")
                    : k
                      ? (B = "stale")
                      : m
                        ? (B = "corrupted")
                        : x
                          ? (B = "ready")
                          : (B = "idle")
          : (B = "deps-missing"),
        B)
      ) {
        case "building": {
          let S = n.createEl("div", { cls: "paperforge-progress-track" });
          S.style.cssText = "flex:1;";
          let N = g > 0 ? ((p / g) * 100).toFixed(1) : "0",
            U = S.createEl("div", { cls: "paperforge-progress-seg done" });
          if (
            ((U.style.cssText = `width:${N}%; min-width:${p > 0 ? "2px" : "0"};`),
            p < g)
          ) {
            let L = S.createEl("div", {
              cls: "paperforge-progress-seg pending",
            });
            L.style.cssText = `width:${(100 - parseFloat(N)).toFixed(1)}%;`;
          }
          (i.createEl("span", {
            cls: "paperforge-embed-progress-text",
            text: `${p}/${g} papers`,
          }),
            y &&
              i.createEl("span", {
                cls: "paperforge-embed-progress-key",
                text: ` (${y})`,
              }));
          let $ = n.createEl("button");
          ($.setText(o("retrieval_stop")),
            ($.className = "mod-warning"),
            $.addEventListener("click", () => {
              (this._callPython(["embed", "stop", "--json"], { timeout: 8e3 }),
                this.display());
            }));
          break;
        }
        case "stopping": {
          let S = n.createEl("div", { cls: "paperforge-progress-track" });
          S.style.cssText = "flex:1; opacity:0.5;";
          let N = g > 0 ? ((p / g) * 100).toFixed(1) : "0",
            U = S.createEl("div", { cls: "paperforge-progress-seg done" });
          if (
            ((U.style.cssText = `width:${N}%; min-width:${p > 0 ? "2px" : "0"};`),
            p < g)
          ) {
            let L = S.createEl("div", {
              cls: "paperforge-progress-seg pending",
            });
            L.style.cssText = `width:${(100 - parseFloat(N)).toFixed(1)}%;`;
          }
          i.createEl("span", { text: o("retrieval_build_stopping") });
          let $ = n.createEl("button");
          ($.setText(o("retrieval_stop")),
            ($.className = "mod-warning"),
            $.setAttr("disabled", ""));
          break;
        }
        case "failed": {
          i.createEl("div", {
            cls: "paperforge-desc-box",
            text: o("retrieval_build_failed") + (O ? ": " + O : ""),
            attr: { style: "color:var(--text-error);" },
          });
          let S = n.createEl("button");
          (S.setText(o("retrieval_retry")),
            (S.className = "mod-cta"),
            S.addEventListener("click", () => D("--resume")));
          let N = n.createEl("button");
          (N.setText(o("retrieval_force_rebuild")),
            (N.style.marginLeft = "6px"),
            N.addEventListener("click", () => D("--force")));
          break;
        }
        case "stopped": {
          i.setText(o("retrieval_build_stopped"));
          let S = n.createEl("button");
          (S.setText(o("retrieval_retry")),
            (S.className = "mod-cta"),
            S.addEventListener("click", () => D("--resume")));
          break;
        }
        case "corrupted": {
          i.createEl("div", {
            cls: "paperforge-desc-box",
            text: o("feat_vector_corrupted"),
            attr: { style: "background:var(--background-modifier-warning);" },
          });
          let S = n.createEl("button");
          (S.setText(o("retrieval_force_rebuild")),
            (S.className = "mod-cta"),
            S.addEventListener("click", () => D("--force")));
          break;
        }
        case "stale": {
          i.createEl("div", {
            cls: "paperforge-desc-box",
            text: o("retrieval_build_stale"),
            attr: { style: "color:var(--text-warning);" },
          });
          let S = n.createEl("button");
          (S.setText(o("retrieval_rebuild_vectors")),
            (S.className = "mod-cta"),
            S.addEventListener("click", () => D("--resume")));
          break;
        }
        case "ready": {
          n.createEl("span", {
            text: w + " chunks embedded",
            cls: "setting-item-description",
          });
          let S = n.createEl("button");
          (S.setText(o("retrieval_rebuild_vectors")),
            (S.className = "mod-cta"),
            S.addEventListener("click", () => D("--resume")));
          let N = n.createEl("button");
          (N.setText(o("retrieval_force_rebuild")),
            (N.style.marginLeft = "6px"),
            N.addEventListener("click", () => D("--force")));
          break;
        }
        case "deps-missing": {
          i.setText(o("retrieval_build_deps_missing"));
          let S = n.createEl("a");
          (S.setText(o("feat_install_deps")),
            (S.style.cssText = "cursor:pointer; text-decoration:underline;"),
            S.addEventListener("click", () => {
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
          let S = n.createEl("a");
          (S.setText(o("runtime_health_sync")),
            (S.style.cssText = "cursor:pointer; text-decoration:underline;"),
            S.addEventListener("click", () => {
              this.display();
            }));
          break;
        }
        case "idle":
        default: {
          i.setText(o("retrieval_build_idle"));
          let S = n.createEl("button");
          (S.setText(o("feat_build_btn")),
            (S.className = "mod-cta"),
            S.addEventListener("click", () => D("--resume")));
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
            let s = r.match(/^\s*([^:]+):\s*(.*)/);
            s && (t[s[1].trim()] = s[2].trim());
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
    if (!V.existsSync(e)) {
      let r = "\u8DEF\u5F84\u4E0D\u5B58\u5728 / Path does not exist";
      (t &&
        (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${r}</span>`),
        new C.Notice(r, 4e3));
      return;
    }
    try {
      V.accessSync(e, V.constants.X_OK);
    } catch (r) {
      let s = "\u4E0D\u53EF\u6267\u884C / Not executable";
      (t &&
        (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${s}</span>`),
        new C.Notice(s, 4e3));
      return;
    }
    (0, G.execFile)(e, ["--version"], { timeout: 8e3 }, (r, s) => {
      if (r || !s) {
        let c = "\u65E0\u6CD5\u8FD0\u884C / Cannot run";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${c}</span>`),
          new C.Notice(c, 4e3));
        return;
      }
      let a = s.match(/Python (\d+)\.(\d+)/);
      if (!a) {
        let c = "\u65E0\u6CD5\u89E3\u6790\u7248\u672C / Cannot parse version";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${c}</span>`),
          new C.Notice(c, 4e3));
        return;
      }
      let n = parseInt(a[1], 10),
        i = parseInt(a[2], 10);
      if (n < 3 || (n === 3 && i < 10)) {
        let c =
          "Python \u7248\u672C\u8FC7\u4F4E\uFF0C\u9700\u8981 3.10+ / Python version too low, need 3.10+";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${c}</span>`),
          new C.Notice(c, 4e3));
        return;
      }
      (0, G.execFile)(e, ["-m", "pip", "--version"], { timeout: 8e3 }, (c) => {
        if (c) {
          let l = `\u2713 Python ${n}.${i} \u6709\u6548\uFF0C\u4F46\u672A\u68C0\u6D4B\u5230 pip / Valid, but pip not found`;
          (t &&
            (t.innerHTML = `<span style="color:var(--text-warning)">\u26A0 ${l}</span>`),
            new C.Notice(l, 4e3));
        } else {
          let l = `\u2713 Python ${n}.${i} \u6709\u6548 / Valid`;
          (t &&
            (t.innerHTML = `<span style="color:var(--text-accent)">${l}</span>`),
            new C.Notice(l, 4e3));
        }
      });
    });
  }
  _syncRuntime(e) {
    let t = this.app.vault.adapter.basePath,
      { path: r, extraArgs: s = [] } = z(
        t,
        this.plugin.settings,
        void 0,
        void 0
      ),
      a = this.plugin.manifest.version,
      n = gt(r, a, s);
    (e.setDisabled(!0), e.setButtonText(o("runtime_health_syncing")));
    let i = (l, d) => (
        console.log(`[PaperForge] Sync Runtime: trying ${d}`),
        mt(n.cmd, l, t, n.timeout, void 0, Se())
      ),
      c = () => {
        let l = "opencode";
        try {
          let g = V.readFileSync(te.join(t, "paperforge.json"), "utf-8"),
            y = JSON.parse(g);
          y.agent_key && (l = y.agent_key);
        } catch (g) {}
        let d = [
            ...s,
            "-c",
            'from paperforge.services.skill_deploy import deploy_skills; from pathlib import Path; r=deploy_skills(vault=Path(r"' +
              t.replace(/\\/g, "\\\\") +
              '"), agent_key="' +
              l +
              '", overwrite=True); print("skills deployed" if r["skill_deployed"] else "skills skipped", flush=True)',
          ],
          _ = (0, G.spawn)(r, d, { cwd: t, timeout: 3e4, windowsHide: !0 }),
          p = "";
        (_.stdout.on("data", (g) => {
          p += g.toString("utf-8");
        }),
          _.on("close", (g) => {
            console.log(`[PaperForge] Skill deploy: ${p.trim()} (exit ${g})`);
          }));
      };
    i(n.pypiArgs, "PyPI").then((l) => {
      if (l.exitCode === 0) {
        (console.log("[PaperForge] Sync Runtime: installed via PyPI"),
          c(),
          new C.Notice(o("runtime_health_sync_done").replace("{0}", a), 5e3),
          this.display());
        return;
      }
      (console.warn(
        "[PaperForge] Sync Runtime: PyPI failed, falling back to git..."
      ),
        i(n.gitArgs, "git").then((d) => {
          d.exitCode === 0
            ? (console.log("[PaperForge] Sync Runtime: installed via git"),
              c(),
              new C.Notice(
                o("runtime_health_sync_done").replace("{0}", a),
                5e3
              ),
              this.display())
            : (e.setDisabled(!1),
              e.setButtonText(o("runtime_health_sync")),
              console.error("[PaperForge] git fallback stderr:", d.stderr),
              new C.Notice(
                o("runtime_health_sync_fail").replace(
                  "{0}",
                  "pip exit code " + d.exitCode
                ),
                8e3
              ));
        }));
    });
  }
  _debouncedSave() {
    (clearTimeout(this._saveTimeout),
      (this._saveTimeout = setTimeout(() => this.plugin.saveSettings(), 500)));
  }
  _preCheck(e) {
    var a;
    let t = this.app.vault.adapter.basePath,
      { path: r, extraArgs: s = [] } = z(
        t,
        (a = this.plugin) == null ? void 0 : a.settings,
        void 0,
        void 0
      );
    (0, G.execFile)(r, [...s, "--version"], { timeout: 8e3 }, (n, i) => {
      let c = [];
      c.push({
        label: "Python",
        ok: !n,
        detail: n ? o("check_python_fail") : i.trim(),
      });
      let l = !1,
        d = process.env.HOME || process.env.USERPROFILE || Rt.homedir() || "";
      if (process.platform === "darwin")
        l = [
          "/Applications/Zotero.app",
          te.join(d, "Applications", "Zotero.app"),
        ].some((b) => {
          try {
            return V.existsSync(b);
          } catch (w) {
            return !1;
          }
        });
      else if (process.platform === "win32") {
        let f = process.env.ProgramFiles || "",
          b = process.env.LOCALAPPDATA || "";
        l = [
          te.join(f, "Zotero"),
          te.join(f, "(x86)", "Zotero"),
          te.join(b, "Programs", "Zotero"),
          te.join(b, "Zotero"),
          te.join(d, "AppData", "Local", "Programs", "Zotero"),
        ]
          .filter(Boolean)
          .some((x) => {
            try {
              return V.existsSync(x);
            } catch (m) {
              return !1;
            }
          });
      } else
        l = [
          te.join(d, ".local", "share", "zotero", "zotero"),
          "/usr/bin/zotero",
          "/usr/local/bin/zotero",
        ].some((b) => {
          try {
            return V.existsSync(b);
          } catch (w) {
            return !1;
          }
        });
      let _ = this.plugin.settings.zotero_data_dir;
      if (!l && _)
        try {
          l = V.existsSync(_);
        } catch (f) {}
      c.push({
        label: "Zotero",
        ok: l,
        detail: l ? o("check_zotero_ok") : o("check_zotero_fail"),
      });
      let p = !1,
        g = process.env.APPDATA || "";
      (process.platform === "win32" &&
        g &&
        (p = $e(te.join(g, "Zotero", "Zotero", "Profiles"))),
        !p &&
          process.platform === "darwin" &&
          d &&
          (p = $e(
            te.join(d, "Library", "Application Support", "Zotero", "Profiles")
          )),
        !p &&
          process.platform !== "win32" &&
          process.platform !== "darwin" &&
          d &&
          (p = $e(te.join(d, ".zotero", "zotero", "Profiles"))),
        !p && _ && String(_).trim() && (p = tt(_.trim())),
        !p && d && (p = tt(te.join(d, "Zotero"))),
        c.push({
          label: "Better BibTeX",
          ok: p,
          detail: p ? o("check_bbt_ok") : o("check_bbt_fail"),
        }));
      let y = { true: "\u2713", false: "\u2717" };
      if (this._checkEl) {
        this._checkEl.setText(
          c.map((b) => `${y[String(b.ok)]} ${b.label}: ${b.detail}`).join(`
`)
        );
        let f = c.some((b) => !b.ok);
        this._checkEl.className = `paperforge-message msg-${f ? "error" : "ok"}`;
      }
      let E = c.filter((f) => !f.ok);
      (E.length > 0 &&
        new C.Notice(
          `[!!] \u672A\u901A\u8FC7: ${E.map((f) => f.label).join(", ")}`,
          6e3
        ),
        e());
    });
  }
  _renderMaintenanceTab(e) {
    var d;
    e.createEl("h2", { text: o("tab_maintenance") || "\u7EF4\u62A4" });
    let r = (d = this.app.vault.adapter.basePath) != null ? d : "",
      s = e.createEl("div"),
      a = { active: "all" },
      n = null;
    try {
      n = Ct(r);
    } catch (_) {}
    let i = z(r, this.plugin.settings, V, G.execFileSync);
    if (!i.path) {
      s.createEl("p", {
        text: "\u26A0 Python \u672A\u914D\u7F6E\uFF0C\u8BF7\u5148\u5728\u300C\u5B89\u88C5\u300D\u6807\u7B7E\u9875\u914D\u7F6E\u3002",
        cls: "setting-item-description",
      });
      return;
    }
    let c = () => !!this.plugin._ocrProcess,
      l = (_) => {
        s.empty();
        let p = _.filter((b) => b.visible_in_maintenance),
          g = s.createEl("div", { cls: "pf-maint-filters" }),
          y = g.createEl("button", {
            cls: "pf-maint-filter" + (a.active === "all" ? " active" : ""),
            text: o("maintenance_filter_all") || "All",
          });
        y.addEventListener("click", () => {
          ((a.active = "all"), l(_));
        });
        let E = g.createEl("button", {
          cls:
            "pf-maint-filter" + (a.active === "recommended" ? " active" : ""),
          text: o("maintenance_filter_recommended") || "Recommended",
        });
        E.addEventListener("click", () => {
          ((a.active = "recommended"), l(_));
        });
        let f =
          a.active === "recommended"
            ? p.filter(
                (b) =>
                  b.display_group === "rebuild" ||
                  b.display_action === "rebuild_result"
              )
            : p;
        if (f.length === 0)
          s.createEl("p", {
            text: "\u5F53\u524D\u7B5B\u9009\u6761\u4EF6\u4E0B\u65E0\u6570\u636E",
            cls: "setting-item-description",
          });
        else {
          let b = i.path,
            w = i.extraArgs || [],
            x = s.createEl("div", { cls: "pf-maint-progress" });
          x.style.display = "none";
          let m = x.createEl("div", { cls: "paperforge-progress-track" });
          m.style.cssText = "flex:1;";
          let v = m.createEl("div", { cls: "paperforge-progress-seg done" }),
            k = m.createEl("div", { cls: "paperforge-progress-seg pending" }),
            R = x.createEl("span", { cls: "pf-maint-progress-text" }),
            P = x.createEl("span", { cls: "pf-maint-progress-key" }),
            O = x.createEl("button", { text: o("maintenance_stop") || "Stop" });
          ((O.className = "mod-warning"),
            O.addEventListener("click", () => {
              let F = this.plugin._ocrProcess;
              (F &&
                (F.stdin && typeof F.stdin.write == "function"
                  ? F.stdin.write(`PAPERFORGE_STOP
`)
                  : typeof F.kill == "function" && F.kill("SIGINT")),
                (this.plugin._ocrWasStopped = !0),
                (O.disabled = !0),
                (O.textContent = (o("maintenance_stop") || "Stop") + "\u2026"));
            }));
          let D = () => {
            let F = this.plugin._ocrProgress;
            if (!F || F.total === 0 || !this.plugin._ocrProcess) {
              x.style.display = "none";
              return;
            }
            x.style.display = "flex";
            let Q =
              F.total > 0 ? ((F.current / F.total) * 100).toFixed(1) : "0";
            ((v.style.width = `${Q}%`),
              (v.style.minWidth = F.current > 0 ? "2px" : "0"),
              F.current < F.total
                ? ((k.style.display = ""), (k.style.flex = "1"))
                : (k.style.display = "none"),
              (R.textContent = (
                o("maintenance_progress_label") || "{current}/{total} papers"
              )
                .replace("{current}", String(F.current))
                .replace("{total}", String(F.total))),
              (P.textContent = F.key ? ` (${F.key})` : ""));
          };
          D();
          let j = new Map();
          for (let F of f) j.set(F.key, !1);
          let H = s.createEl("div", { cls: "pf-maint-table-wrap" }),
            B = H.createEl("table", { cls: "pf-maint-table" }),
            S = B.createEl("thead"),
            N = B.createEl("tbody"),
            U = S.insertRow();
          ["", "Paper", "Status Reason", "Actions"].forEach((F) => {
            let Q = document.createElement("th");
            ((Q.textContent = F), U.appendChild(Q));
          });
          let $ = c();
          for (let F of f) {
            let Q = N.insertRow(),
              T = Q.insertCell();
            T.style.cssText = "padding:3px 4px;text-align:center;width:24px;";
            let I = document.createElement("input");
            ((I.type = "checkbox"),
              (I.className = "pf-maint-sel"),
              (I.checked = j.get(F.key) || !1),
              I.addEventListener("change", () => {
                (j.set(F.key, I.checked), Y());
              }),
              T.appendChild(I));
            let se = Q.insertCell();
            se.style.cssText = "padding:3px 4px;";
            let A = se.createEl("div", { cls: "pf-maint-paper-info" });
            (A.createEl("div", {
              cls: "pf-maint-paper-title",
              text: F.title || F.key,
            }),
              A.createEl("div", { cls: "pf-maint-paper-key", text: F.key }));
            let ee = Q.insertCell();
            ((ee.style.cssText = "padding:3px 4px;"),
              ee.createEl("div", {
                cls: "pf-maint-reason",
                text: F.display_reason || "",
              }));
            let ie = Q.insertCell();
            ie.style.cssText = "padding:3px 4px;white-space:nowrap;";
            let be = ie.createEl("div", { cls: "pf-maint-actions" });
            if (F.can_rebuild) {
              let Ee = be.createEl("button", {
                cls: "pf-maint-action-btn rebuild",
                text: o("maintenance_btn_rebuild") || "Rebuild",
              });
              ($ && (Ee.disabled = !0),
                Ee.addEventListener("click", () => {
                  let de = [...w, "-m", "paperforge", "ocr", "rebuild", F.key];
                  (0, G.execFile)(
                    b,
                    de,
                    { cwd: r, timeout: 12e4, windowsHide: !0 },
                    () => {
                      new C.Notice(
                        (o("maintenance_btn_rebuild") || "Rebuild") +
                          " \u2014 " +
                          F.key
                      );
                    }
                  );
                }));
            }
            if (F.can_redo) {
              let Ee = be.createEl("button", {
                cls: "pf-maint-action-btn redo",
                text: o("ocr_maint_redo_btn") || "Redo",
              });
              ($ && (Ee.disabled = !0),
                Ee.addEventListener("click", () => {
                  let de = [...w, "-m", "paperforge", "ocr", "redo", F.key];
                  (0, G.execFile)(
                    b,
                    de,
                    { cwd: r, timeout: 3e5, windowsHide: !0 },
                    () => {
                      new C.Notice(
                        (o("ocr_maint_redo_btn") || "Redo OCR") +
                          " \u2014 " +
                          F.key
                      );
                    }
                  );
                }));
            }
          }
          let L = s.createEl("div", { cls: "pf-maint-batch-bar" }),
            ne = L.createEl("span", {
              cls: "pf-maint-batch-label",
              text: "0 selected",
            }),
            Y = () => {
              let F = f.filter((Q) => j.get(Q.key)).length;
              ne.textContent = F + " selected";
            },
            ce = L.createEl("button", {
              cls: "mod-cta",
              text: o("maintenance_batch_rebuild") || "\u25B6 Rebuild selected",
            });
          ce.disabled = $;
          let re = L.createEl("button", {
            cls: "mod-cta",
            text:
              o("maintenance_batch_redo") || "\u25B6 Full OCR redo selected",
          });
          re.disabled = $;
          let q = (F) => {
            let Q = f.filter((A) => j.get(A.key));
            if (Q.length === 0) {
              new C.Notice("Please select papers first.");
              return;
            }
            let T = Q.map((A) => A.key);
            ((this.plugin._ocrProgress = {
              current: 0,
              total: T.length,
              key: "",
            }),
              (this.plugin._ocrBuffer = ""),
              (this.plugin._ocrWasStopped = !1));
            let I = F === "rebuild" ? "OCR_REBUILD" : "OCR_REDO";
            ((ce.disabled = !0),
              (re.disabled = !0),
              Array.from(H.querySelectorAll(".pf-maint-action-btn")).forEach(
                (A) => {
                  A.disabled = !0;
                }
              ),
              Array.from(H.querySelectorAll(".pf-maint-sel")).forEach((A) => {
                A.disabled = !0;
              }),
              (y.disabled = !0),
              (E.disabled = !0),
              (O.disabled = !1),
              (O.textContent = o("maintenance_stop") || "Stop"));
            let se = this._callPython(["ocr", F, ...T], {
              stream: !0,
              onData: (A) => {
                var Ee;
                let ee =
                    typeof A == "string"
                      ? A
                      : Buffer.isBuffer(A)
                        ? A.toString("utf-8")
                        : String(A),
                  { events: ie, buffer: be } = ot(
                    ee,
                    (Ee = this.plugin._ocrBuffer) != null ? Ee : ""
                  );
                this.plugin._ocrBuffer = be;
                for (let de of ie)
                  de.event === "START"
                    ? this.plugin._ocrProgress &&
                      (this.plugin._ocrProgress.total = de.total || T.length)
                    : de.event === "PROGRESS" &&
                      (this.plugin._ocrProgress = {
                        current: de.current || 0,
                        total: de.total || T.length,
                        key: de.key || "",
                      });
                D();
              },
              onError: (A) => {
                ((this.plugin._ocrProcess = null),
                  new C.Notice("Batch error: " + (A.message || A)),
                  l(_));
              },
              onClose: (A) => {
                (this.plugin._ocrWasStopped || A === 130
                  ? ((this.plugin._ocrWasStopped = !1),
                    (this.plugin._ocrProcess = null),
                    D(),
                    new C.Notice("OCR batch stopped by user."))
                  : A === 0
                    ? (this.plugin._ocrProgress &&
                        (this.plugin._ocrProgress.current =
                          this.plugin._ocrProgress.total),
                      (this.plugin._ocrProcess = null),
                      D(),
                      new C.Notice(
                        (
                          o("maintenance_batch_complete") ||
                          "Batch operation complete \u2014 {n} papers processed."
                        ).replace("{n}", String(T.length))
                      ))
                    : ((this.plugin._ocrProcess = null),
                      D(),
                      new C.Notice(
                        "Batch operation finished with exit code " + A + ".",
                        8e3
                      )),
                  it(r, b, w, n)
                    .then((ee) => {
                      ((ee.changed || !n) &&
                        ((n = {
                          manifest: {},
                          papers: Object.fromEntries(
                            ee.data.map((ie) => [ie.key, ie])
                          ),
                          cached_at: new Date().toISOString(),
                        }),
                        Ie(r, n)),
                        l(ee.data));
                    })
                    .catch(() => {
                      l(p);
                    }));
              },
            });
            ((this.plugin._ocrProcess = se), D());
          };
          (ce.addEventListener("click", () => q("rebuild")),
            re.addEventListener("click", () => q("redo")),
            Y());
        }
      };
    if (n) {
      let _ = Object.values(n.papers);
      l(_);
    } else
      s.createEl("p", {
        text: "\u6B63\u5728\u52A0\u8F7D OCR \u7EF4\u62A4\u6570\u636E\u2026",
      });
    it(r, i.path, i.extraArgs || [], n || null)
      .then((_) => {
        _.changed
          ? (l(_.data),
            Ie(r, {
              manifest: {},
              papers: Object.fromEntries(_.data.map((p) => [p.key, p])),
              cached_at: new Date().toISOString(),
            }))
          : n ||
            (l(_.data),
            Ie(r, {
              manifest: {},
              papers: Object.fromEntries(_.data.map((p) => [p.key, p])),
              cached_at: new Date().toISOString(),
            }));
      })
      .catch(() => {
        n ||
          (s.empty(),
          s.createEl("p", {
            text: "\u65E0\u6CD5\u52A0\u8F7D OCR \u6570\u636E\u3002\u8BF7\u786E\u4FDD\u5DF2\u5B89\u88C5 paperforge \u5E76\u8FD0\u884C\u8FC7 OCR\u3002",
            cls: "setting-item-description",
          }));
      });
  }
  _renderReleaseNotesTab(e) {
    (e.createEl("h2", { text: "\u66F4\u65B0\u4E0E\u624B\u518C" }),
      e.createEl("h3", { text: "\u7248\u672C\u66F4\u65B0\u8BB0\u5F55" }));
    let t = Ft.default.versions || [];
    for (let a of t) {
      let n = e.createEl("div", { cls: "paperforge-release-card" }),
        i = n.createEl("div", { cls: "paperforge-release-header" });
      if (
        (i.createEl("strong", { text: `v${a.version} \u2014 ${a.title}` }),
        i.createEl("span", {
          cls: "paperforge-release-date",
          text: `  (${a.date})`,
        }),
        a.breaking_or_migration && a.breaking_or_migration.length > 0)
      ) {
        let c = n.createEl("div", { cls: "paperforge-release-section" });
        c.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u884C\u4E3A\u53D8\u66F4 / \u8FC1\u79FB\u6CE8\u610F",
        });
        for (let l of a.breaking_or_migration)
          c.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${l}`,
          });
      }
      if (a.new_features && a.new_features.length > 0) {
        let c = n.createEl("div", { cls: "paperforge-release-section" });
        c.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u65B0\u529F\u80FD",
        });
        for (let l of a.new_features)
          c.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${l}`,
          });
      }
      if (a.fixes && a.fixes.length > 0) {
        let c = n.createEl("div", { cls: "paperforge-release-section" });
        c.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u4FEE\u590D",
        });
        for (let l of a.fixes)
          c.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${l}`,
          });
      }
      if (a.recommended_actions && a.recommended_actions.length > 0) {
        let c = n.createEl("div", {
          cls: "paperforge-release-section paperforge-release-recommended",
        });
        c.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u5EFA\u8BAE\u64CD\u4F5C",
        });
        for (let l of a.recommended_actions)
          c.createEl("div", {
            cls: "paperforge-release-item paperforge-release-item-bold",
            text: `\u2022 ${l}`,
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
};
var M = require("obsidian"),
  ye = K(require("fs")),
  je = K(require("path")),
  ve = require("child_process");
var Me = K(require("path"));
function Tt(u) {
  if (!u) return null;
  let h = Me.dirname(u);
  for (;;) {
    let e = Me.basename(h);
    if (!e || e === ".") break;
    let t = e.match(/^([A-Z0-9]{8})(?:\s*-\s*.*)?$/i);
    if (t) return t[1];
    let r = Me.dirname(h);
    if (r === h) break;
    h = r;
  }
  return null;
}
var J = K(require("fs")),
  ke = K(require("path"));
function Ne(u) {
  return le(u).ocrDir;
}
function Ut(u, h) {
  let e = ke.join(Ne(u), h, "versions", "manifest.json");
  try {
    if (!J.existsSync(e)) return null;
    let t = J.readFileSync(e, "utf-8"),
      r = JSON.parse(t);
    if (r && typeof r == "object" && "versions" in r && "current" in r) {
      let s = r,
        a = s.versions,
        n = s.current;
      if (Array.isArray(a) && n && typeof n == "object" && "label" in n)
        return r;
    }
    return null;
  } catch (t) {
    return null;
  }
}
function qt(u) {
  let h = Ne(u);
  try {
    return J.existsSync(h)
      ? J.readdirSync(h, { withFileTypes: !0 })
          .filter((e) => e.isDirectory())
          .map((e) => e.name)
      : [];
  } catch (e) {
    return [];
  }
}
function lt(u) {
  let h = qt(u),
    e = [];
  for (let t of h) {
    let r = Ut(u, t);
    if (!r) continue;
    let s = r.versions.map((n) => n.label),
      a = 0;
    for (let n of s) {
      let i = ke.join(Ne(u), t, "versions", n, "fulltext.md");
      try {
        J.existsSync(i) && (a += J.statSync(i).size);
      } catch (c) {}
    }
    e.push({
      key: t,
      title: t.replace(/_/g, " "),
      versions: r.versions,
      currentLabel: r.current.label,
      totalSize: a,
    });
  }
  return (e.sort((t, r) => t.title.localeCompare(r.title)), e);
}
function Bt(u, h, e) {
  let t = Ne(u),
    r = ke.join(t, h, "versions", e, "fulltext.md"),
    s = ke.join(t, h, "render"),
    a = ke.join(s, "fulltext.md");
  try {
    return J.existsSync(r)
      ? (J.existsSync(s) || J.mkdirSync(s, { recursive: !0 }),
        J.copyFileSync(r, a),
        !0)
      : !1;
  } catch (n) {
    return !1;
  }
}
function At(u, h, e, t) {
  var p;
  let r = Ne(u),
    s = ke.join(r, h, "versions", e, "fulltext.md"),
    a = ke.join(r, h, "versions", t, "fulltext.md"),
    n = "",
    i = "";
  try {
    J.existsSync(s) && (n = J.readFileSync(s, "utf-8"));
  } catch (g) {}
  try {
    J.existsSync(a) && (i = J.readFileSync(a, "utf-8"));
  } catch (g) {}
  let c = Dt(n),
    l = Dt(i),
    d = Math.max(c.length, l.length),
    _ = [];
  for (let g = 0; g < d; g++) {
    let y = g < c.length ? c[g] : "",
      E = g < l.length ? l[g] : "",
      f =
        (p = (y || E).split(`
`)[0]) != null
          ? p
          : "",
      b = f.startsWith("## ") ? f.replace(/^##\s+/, "") : "",
      w = "unchanged";
    (!y && E
      ? (w = "added")
      : y && !E
        ? (w = "removed")
        : y !== E && (w = "changed"),
      w !== "unchanged" &&
        _.push({
          paragraphIndex: g,
          heading: b,
          type: w,
          oldText: y || void 0,
          newText: E || void 0,
        }));
  }
  return _;
}
function Dt(u) {
  let h = u.split(`
`),
    e = [],
    t = [];
  for (let r of h)
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
      let s = t
        .join(
          `
`
        )
        .trim();
      s && (e.push(s), (t = []));
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
var Fe = class extends M.ItemView {
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
  getViewType() {
    return we;
  }
  getDisplayText() {
    return "PaperForge";
  }
  getIcon() {
    return De;
  }
  async onOpen() {
    (this._buildPanel(),
      (this._modeSubscribers = []),
      (this._leafChangeTimer = null),
      this._setupEventSubscriptions(),
      this._fetchVersion(),
      this._detectAndSwitch(),
      (this._onKeyDown = (e) => {
        var t, r, s;
        if (e.key === "/" && !e.ctrlKey && !e.metaKey && !e.altKey) {
          let a =
            (r = (t = e.target) == null ? void 0 : t.tagName) == null
              ? void 0
              : r.toLowerCase();
          a !== "input" &&
            a !== "textarea" &&
            (e.preventDefault(), (s = this._searchInput) == null || s.focus());
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
    let s = t.createEl("button", {
      cls: "paperforge-header-refresh",
      attr: { "aria-label": "Refresh" },
    });
    ((s.innerHTML = "\u21BB"),
      s.addEventListener("click", () => {
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
    var n, i;
    let e = this.app.vault.adapter.basePath,
      t = this.app.plugins.plugins.paperforge,
      r =
        ((n = t == null ? void 0 : t.manifest) == null ? void 0 : n.version) ||
        "?",
      { path: s, extraArgs: a = [] } = z(
        e,
        (i = t == null ? void 0 : t.settings) != null ? i : null,
        void 0,
        void 0
      );
    ft(s, r, e, 1e4, void 0).then((c) => {
      if (c.status === "not-installed") return;
      let l = c.pyVersion || "";
      ((this._paperforgeVersion = l.startsWith("v") ? l : "v" + l),
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
    var n;
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
      { path: s, extraArgs: a = [] } = z(
        t,
        (n = r == null ? void 0 : r.settings) != null ? n : null,
        void 0,
        void 0
      );
    (0, ve.execFile)(
      s,
      [...a, "-m", "paperforge", "dashboard", "--json"],
      { cwd: t, timeout: 3e4 },
      (i, c) => {
        if (!i)
          try {
            let l = JSON.parse(c);
            if (l.ok && l.data) {
              let d = this._normalizeDashboardData(l.data);
              ((this._cachedStats = d),
                this._metricsEl.empty(),
                this._renderStats(d),
                this._renderOcr(d),
                (this._dashboardPermissions = l.data.permissions || {}));
              return;
            }
          } catch (l) {}
        this._fallbackFetchStats(e, t, r);
      }
    );
  }
  _normalizeDashboardData(e) {
    let t = e.stats || {},
      r = t.ocr_health || {},
      s = t.pdf_health || {},
      a = e.ocr_version_state || {},
      n = (r.done || 0) + (r.pending || 0) + (r.failed || 0);
    return {
      total_papers: t.papers || 0,
      formal_notes: t.papers || 0,
      exports: 0,
      bases: 0,
      ocr: {
        total: n,
        pending: r.pending || 0,
        processing: 0,
        done: r.done || 0,
        failed: r.failed || 0,
      },
      path_errors: (s.broken || 0) + (s.missing || 0),
      ocr_version_state: {
        total_papers: a.total_papers || 0,
        derived_stale_count: a.derived_stale_count || 0,
        raw_upgradable_count: a.raw_upgradable_count || 0,
      },
    };
  }
  _fallbackFetchStats(e, t, r) {
    var n, i, c;
    let s =
        ((n = r == null ? void 0 : r.settings) == null
          ? void 0
          : n.system_dir) || "System",
      a = je.join(t, s, "PaperForge", "indexes", "formal-library.json");
    try {
      let l = ye.readFileSync(a, "utf-8"),
        d = JSON.parse(l),
        _ = d.items || [],
        p = {},
        g = {
          pdf_health: { healthy: 0, unhealthy: 0 },
          ocr_health: { healthy: 0, unhealthy: 0 },
          note_health: { healthy: 0, unhealthy: 0 },
          asset_health: { healthy: 0, unhealthy: 0 },
        },
        y = 0,
        E = 0,
        f = 0,
        b = 0,
        w = 0,
        x = 0;
      for (let m of _) {
        m.note_path && x++;
        let v = m.lifecycle || "pdf_ready";
        p[v] = (p[v] || 0) + 1;
        let k = m.health || {};
        for (let P of [
          "pdf_health",
          "ocr_health",
          "note_health",
          "asset_health",
        ])
          (k[P] || "healthy") === "healthy" ? g[P].healthy++ : g[P].unhealthy++;
        let R = m.ocr_status || "";
        (y++,
          R === "done"
            ? E++
            : R === "pending"
              ? f++
              : R === "processing" || R === "queued" || R === "running"
                ? b++
                : w++);
      }
      ((this._cachedStats = {
        version:
          d.paperforge_version ||
          ((i = this._cachedStats) == null ? void 0 : i.version) ||
          "\u2014",
        total_papers: _.length,
        formal_notes: x,
        exports: 0,
        bases: 0,
        ocr: { total: y, pending: f, processing: b, done: E, failed: w },
        path_errors: 0,
        lifecycle_level_counts: p,
        health_aggregate: g,
      }),
        this._metricsEl.empty(),
        this._renderStats(this._cachedStats),
        this._renderOcr(this._cachedStats));
    } catch (l) {
      !e &&
        !this._cachedStats &&
        this._metricsEl.createEl("div", {
          cls: "paperforge-status-loading",
          text: "No index \u2014 trying CLI...",
        });
      let { path: d, extraArgs: _ = [] } = z(
        t,
        (c = r == null ? void 0 : r.settings) != null ? c : null,
        void 0,
        void 0
      );
      (0, ve.execFile)(
        d,
        [..._, "-m", "paperforge", "status", "--json"],
        { cwd: t, timeout: 3e4 },
        (p, g) => {
          if (p) {
            if (this._cachedStats) return;
            this._metricsEl.createEl("div", {
              cls: "paperforge-status-error",
              text: `Cannot reach PaperForge CLI.
Make sure paperforge is installed and in your PATH.`,
            });
            return;
          }
          try {
            let y = JSON.parse(g);
            ((this._cachedStats = y),
              this._metricsEl.empty(),
              this._renderStats(y),
              this._renderOcr(y));
          } catch (y) {
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
    let s = Math.min(100, (t / r) * 100);
    e.createEl("div", { cls: "paperforge-metric-progress" }).createEl("div", {
      cls: "paperforge-metric-progress-fill",
      attr: { style: `width:${s.toFixed(1)}%` },
    });
  }
  _loadIndex() {
    var a;
    let e = this.app.vault.adapter.basePath,
      t = this.app.plugins.plugins.paperforge,
      r =
        ((a = t == null ? void 0 : t.settings) == null
          ? void 0
          : a.system_dir) || "System",
      s = je.join(e, r, "PaperForge", "indexes", "formal-library.json");
    try {
      let n = ye.readFileSync(s, "utf-8");
      return JSON.parse(n);
    } catch (n) {
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
    return dt(this.app, t);
  }
  _patchCachedEntry(e, t) {
    if (!e || !this._cachedItems) return;
    let r = this._cachedItems.findIndex((s) => s.zotero_key === e);
    r !== -1 && (this._cachedItems[r] = qe(this._cachedItems[r], t));
  }
  _filterByDomain(e) {
    return e ? this._getCachedIndex().filter((t) => t.domain === e) : [];
  }
  _renderStats(e) {
    var n;
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
      s = [
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
    for (let i of s) {
      let c = this._metricsEl.createEl("div", {
        cls: "paperforge-metric-card",
      });
      (c.style.setProperty("--metric-color", i.color),
        c.createEl("div", {
          cls: "paperforge-metric-value",
          text: ((n = i.value) == null ? void 0 : n.toString()) || "\u2014",
        }),
        c.createEl("div", { cls: "paperforge-metric-label", text: i.label }),
        i.barMax > 0 && this._buildMetricBar(c, i.value, i.barMax));
    }
    let a = e.ocr_version_state || {};
    if (
      a.total_papers > 0 &&
      (a.derived_stale_count > 0 || a.raw_upgradable_count > 0)
    ) {
      let i = [];
      (a.derived_stale_count > 0 && i.push(`${a.derived_stale_count} stale`),
        a.raw_upgradable_count > 0 &&
          i.push(`${a.raw_upgradable_count} upgradable`));
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
    let s = t.done || 0,
      a = t.pending || 0,
      n = t.processing || 0,
      i = t.failed || 0;
    if (
      (this._ocrBadge &&
        (this._ocrBadge.removeClass("active", "idle"),
        n > 0
          ? (this._ocrBadge.addClass("active"),
            this._ocrBadge.setText("Processing"))
          : a > 0
            ? (this._ocrBadge.addClass("idle"),
              this._ocrBadge.setText("Pending"))
            : (this._ocrBadge.addClass("idle"),
              this._ocrBadge.setText("Idle"))),
      this._ocrTrack)
    ) {
      (this._ocrTrack.empty(),
        n > 0
          ? this._ocrTrack.addClass("paperforge-processing")
          : this._ocrTrack.removeClass("paperforge-processing"));
      let c = [
        { cls: "pending", count: a },
        { cls: "active", count: n },
        { cls: "done", count: s },
        { cls: "failed", count: i },
      ];
      for (let l of c)
        if (l.count > 0) {
          let d = ((l.count / r) * 100).toFixed(1);
          this._ocrTrack.createEl("div", {
            cls: `paperforge-progress-seg ${l.cls}`,
            attr: { style: `width:${d}%` },
          });
        }
    }
    if (this._ocrCounts) {
      this._ocrCounts.empty();
      let c = [
        { cls: "pending", value: a, label: "Pending" },
        { cls: "active", value: n, label: "Processing" },
        { cls: "done", value: s, label: "Done" },
        { cls: "failed", value: i, label: "Failed" },
      ];
      for (let l of c) {
        let d = this._ocrCounts.createEl("div", {
          cls: "paperforge-ocr-count",
        });
        (d.createEl("div", {
          cls: "paperforge-ocr-count-value",
          text: l.value.toString(),
        }),
          d.createEl("div", {
            cls: "paperforge-ocr-count-label",
            text: l.label,
          }));
      }
    }
  }
  _renderLifecycleStepper(e, t, r) {
    if (!t || !r) {
      this._renderSkeleton(e);
      return;
    }
    let s = [
        { key: "indexed", label: "Indexed" },
        { key: "pdf_ready", label: "PDF Ready" },
        { key: "fulltext_ready", label: "Fulltext Ready" },
        { key: "deep_read_done", label: "Deep Read" },
      ],
      a = e.createEl("div", { cls: "paperforge-lifecycle-stepper" }),
      n = !1;
    for (let i of s) {
      let c = a.createEl("div", { cls: "step" });
      (c.createEl("div", { cls: "step-indicator" }),
        c.createEl("div", { cls: "step-label", text: i.label }),
        i.key === r
          ? (c.addClass("current"), (n = !0))
          : n
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
      s = e.createEl("div", { cls: "paperforge-health-matrix" });
    for (let a of r) {
      let n = t[a.key] || "healthy",
        i = s.createEl("div", { cls: "paperforge-health-cell" }),
        c,
        l,
        d;
      (n === "healthy" || n === "ok"
        ? ((c = a.iconOk), (l = "ok"), (d = `${a.label}: OK`))
        : n === "warn" || n === "warning" || n === "degraded"
          ? ((c = a.iconWarn),
            (l = "warn"),
            (d = `${a.label}: Needs Attention`))
          : ((c = a.iconFail), (l = "fail"), (d = `${a.label}: Failed`)),
        i.addClass(l),
        i.setAttribute("title", d),
        i.createEl("div", { cls: "paperforge-health-cell-icon", text: c }),
        i.createEl("div", {
          cls: "paperforge-health-cell-label",
          text: a.label,
        }));
    }
  }
  _renderMaturityGauge(e, t, r) {
    if (t == null || t === void 0) {
      this._renderSkeleton(e);
      return;
    }
    let s = e.createEl("div", { cls: "paperforge-maturity-gauge" }),
      a = s.createEl("div", { cls: "gauge-track" }),
      n = 4,
      i = Math.max(1, Math.min(n, Math.round(t)));
    for (let c = 1; c <= n; c++) {
      let l = a.createEl("div", { cls: "gauge-segment" });
      c <= i && (l.addClass("filled"), l.addClass(`level-${c}`));
    }
    if (
      (s.createEl("div", { cls: "gauge-level", text: `Level ${i} / ${n}` }),
      i < n && r)
    ) {
      let c = typeof r == "string" ? [r] : r;
      if (c.length > 0) {
        let l = s.createEl("ul", { cls: "gauge-blockers" });
        for (let d of c) l.createEl("li", { text: d });
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
      s = e.createEl("div", { cls: "paperforge-bar-chart" }),
      a = Math.max(1, ...r.map((n) => t[n.key] || 0));
    for (let n of r) {
      let i = t[n.key] || 0,
        c = (i / a) * 100,
        l = s.createEl("div", { cls: "bar-row" });
      (l.createEl("div", { cls: "bar-label", text: n.label }),
        l
          .createEl("div", { cls: "bar-track" })
          .createEl("div", {
            cls: `bar-fill ${n.cls}`,
            attr: { style: `width:${c.toFixed(1)}%` },
          }),
        l.createEl("div", { cls: "bar-count", text: i.toString() }));
    }
  }
  _invalidateIndex() {
    this._cachedItems = null;
  }
  _extractZoteroKeyFromPath(e) {
    return Tt(e);
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
      let a = this.app.metadataCache.getFileCache(e),
        n = a && a.frontmatter && a.frontmatter.zotero_key;
      if (n) return { mode: "paper", filePath: r, key: n, domain: null };
    }
    if (t === "pdf") {
      let a = this._getCachedIndex();
      for (let n of a) {
        let i = (n.pdf_path || "").match(/\[\[([^\]]+)\]\]/);
        if ((i ? i[1] : n.pdf_path) === r)
          return {
            mode: "paper",
            filePath: r,
            key: n.zotero_key,
            domain: null,
          };
      }
    }
    let s = this._extractZoteroKeyFromPath(r);
    return s
      ? { mode: "paper", filePath: r, key: s, domain: null }
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
    var ne, Y, ce, re, q, F, Q;
    if (!this._contentEl) return;
    let e = this._contentEl.createEl("div", { cls: "paperforge-global-view" });
    ((this._driftBannerEl = e.createEl("div", {
      cls: "paperforge-drift-banner",
    })),
      (this._driftBannerEl.style.display = "none"));
    let t = this._getCachedIndex(),
      r = t.length,
      s = 0,
      a = 0,
      n = 0;
    for (let T of t)
      (T.has_pdf && s++,
        T.ocr_status === "done" && a++,
        T.deep_reading_status === "done" && n++);
    let i = e.createEl("div", { cls: "paperforge-library-snapshot" });
    i.createEl("div", {
      cls: "paperforge-section-label",
      text: "Library Snapshot",
    });
    let c = i.createEl("div", { cls: "paperforge-snapshot-pills" }),
      l = [
        { value: r, label: "papers" },
        { value: s, label: "PDFs ready" },
        { value: a, label: "OCR done" },
        { value: n, label: "deep-read done" },
      ];
    for (let T of l) {
      let I = c.createEl("div", { cls: "paperforge-snapshot-pill" });
      (I.createEl("span", {
        cls: "paperforge-snapshot-value",
        text: String(T.value),
      }),
        I.createEl("span", {
          cls: "paperforge-snapshot-label",
          text: " " + T.label,
        }));
    }
    let d = e.createEl("div", { cls: "paperforge-system-status" });
    d.createEl("div", {
      cls: "paperforge-section-label",
      text: "System Status",
    });
    let _ = d.createEl("div", { cls: "paperforge-status-grid" }),
      p = this.app.plugins.plugins.paperforge,
      g =
        ((ne = p == null ? void 0 : p.manifest) == null
          ? void 0
          : ne.version) || "?",
      y = this._paperforgeVersion;
    if (!y)
      try {
        let T = this.app.vault.adapter.basePath,
          { path: I, extraArgs: se = [] } = z(
            T,
            (Y = p == null ? void 0 : p.settings) != null ? Y : null,
            void 0,
            void 0
          ),
          A = (0, ve.execFileSync)(
            I,
            [...se, "-c", "import paperforge; print(paperforge.__version__)"],
            { cwd: T, timeout: 5e3, encoding: "utf-8", windowsHide: !0 }
          ).trim();
        A &&
          ((y = A.startsWith("v") ? A : "v" + A),
          (this._paperforgeVersion = y));
      } catch (T) {}
    y = y || "\u2014";
    let E = y === "v" + g;
    this._renderSystemStatusRow(
      _,
      "Runtime",
      E ? "healthy" : "mismatch",
      E ? "v" + g : "plugin v" + g + " \u2260 CLI " + y
    );
    let f = this._loadIndex(),
      b = f && f.items && f.items.length > 0;
    this._renderSystemStatusRow(
      _,
      "Index",
      b ? "healthy" : "missing",
      b ? f.items.length + " entries" : "formal-library.json not found"
    );
    let w =
        ((ce = p == null ? void 0 : p.settings) == null
          ? void 0
          : ce.system_dir) || "System",
      x = this.app.vault.adapter.basePath,
      m = !1,
      v = "No exports found";
    try {
      let T = je.join(x, w, "PaperForge", "exports");
      if (ye.existsSync(T)) {
        let I = ye.readdirSync(T).filter((se) => se.endsWith(".json"));
        ((m = I.length > 0),
          (v = m ? I.length + " export(s)" : "No JSON exports"));
      }
    } catch (T) {}
    this._renderSystemStatusRow(
      _,
      "Zotero Export",
      m ? "healthy" : "missing",
      v
    );
    let k = !!(
      (re = p == null ? void 0 : p.settings) != null && re.paddleocr_api_key
    );
    if (!k)
      try {
        let T =
            ((q = p == null ? void 0 : p.settings) == null
              ? void 0
              : q.system_dir) || "System",
          I = je.join(x, T, "PaperForge", ".env");
        if (ye.existsSync(I)) {
          let A = ye
            .readFileSync(I, "utf-8")
            .match(/^PADDLEOCR_API_TOKEN\s*=\s*(.+)$/m);
          k = !!(A && A[1] && A[1].trim());
        }
      } catch (T) {}
    (k ||
      (k = !!(
        process.env.PADDLEOCR_API_TOKEN ||
        process.env.PADDLEOCR_API_KEY ||
        process.env.OCR_TOKEN
      )),
      this._renderSystemStatusRow(
        _,
        "OCR Token",
        k ? "configured" : "missing",
        k ? "Configured" : "Not set"
      ));
    let R = !1,
      P = "",
      O = this.app.vault.adapter.basePath,
      D = Ae(O);
    ((R = vt(O)),
      (P =
        (D && ((F = D.summary) == null ? void 0 : F.reason)) ||
        (D && ((Q = D.summary) == null ? void 0 : Q.status)) ||
        "Unknown"),
      this._renderSystemStatusRow(
        _,
        "Memory Layer",
        R ? "healthy" : "fail",
        P
      ));
    let j = !E && y !== "\u2014";
    if (j || !b || !m || !k) {
      let T = e.createEl("div", { cls: "paperforge-issue-summary" });
      T.createEl("div", {
        cls: "paperforge-section-label",
        text: "\u9700\u8981\u5904\u7406",
      });
      let I = T.createEl("div", { cls: "paperforge-issue-list" });
      (j &&
        I.createEl("div", {
          cls: "paperforge-issue-item",
          text: "Runtime version mismatch",
        }),
        b ||
          I.createEl("div", {
            cls: "paperforge-issue-item",
            text: "Index missing or corrupted",
          }),
        m ||
          I.createEl("div", {
            cls: "paperforge-issue-item",
            text: "No Zotero export found",
          }),
        k ||
          I.createEl("div", {
            cls: "paperforge-issue-item",
            text: "PaddleOCR API key not configured",
          }));
      let se = T.createEl("div", { cls: "paperforge-issue-actions" }),
        A = se.createEl("button", { cls: "paperforge-contextual-btn" });
      (A.createEl("span", { text: "Run Doctor" }),
        A.addEventListener("click", () => {
          let ie = oe.find((be) => be.id === "paperforge-doctor");
          ie && this._runAction(ie, A);
        }));
      let ee = se.createEl("button", { cls: "paperforge-contextual-btn" });
      (ee.createEl("span", { text: "Repair Issues" }),
        ee.addEventListener("click", () => {
          let ie = oe.find((be) => be.id === "paperforge-repair");
          ie && this._runAction(ie, ee);
        }));
    }
    let B = e.createEl("div", { cls: "paperforge-global-actions" });
    B.createEl("div", {
      cls: "paperforge-section-label",
      text: "Start Working",
    });
    let S = B.createEl("div", { cls: "paperforge-global-actions-row" }),
      N = S.createEl("button", { cls: "paperforge-contextual-btn primary" });
    (N.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u{1F4C1}",
    }),
      N.createEl("span", { text: "Open Literature Hub" }),
      N.addEventListener("click", () => {
        var se;
        let T =
            ((se = p == null ? void 0 : p.settings) == null
              ? void 0
              : se.base_dir) || "Bases",
          I = this.app.vault.getAbstractFileByPath(T);
        if (I) {
          let A = null;
          if (
            (I.children &&
              (A = I.children.find((ee) => ee.extension === "base")),
            A)
          ) {
            let ee = this.app.workspace.getLeaf(!1);
            ee && ee.openFile(A);
          } else new M.Notice("[!!] No .base file found in " + T, 6e3);
        } else new M.Notice("[!!] Base directory not found: " + T, 6e3);
      }));
    let U = S.createEl("button", { cls: "paperforge-contextual-btn" });
    (U.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    }),
      U.createEl("span", { text: "Sync Library" }),
      U.addEventListener("click", () => {
        let T = oe.find((I) => I.id === "paperforge-sync");
        T && this._runAction(T, U);
      }));
    let $ = S.createEl("button", { cls: "paperforge-contextual-btn" });
    ($.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    }),
      $.createEl("span", { text: "Run OCR" }),
      $.addEventListener("click", () => {
        let T = oe.find((I) => I.id === "paperforge-ocr");
        T && this._runAction(T, $);
      }));
    let L = S.createEl("button", { cls: "paperforge-contextual-btn warn" });
    (L.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BA",
    }),
      L.createEl("span", { text: "Redo OCR" }),
      L.addEventListener("click", () => {
        let T = oe.find((I) => I.id === "paperforge-ocr-redo");
        T && this._runAction(T, L);
      }));
  }
  _renderSystemStatusRow(e, t, r, s) {
    let a = e.createEl("div", { cls: "paperforge-status-row" });
    (a
      .createEl("span", { cls: "paperforge-status-dot" })
      .addClass(r === "healthy" || r === "configured" ? "ok" : "fail"),
      a.createEl("span", { cls: "paperforge-status-label", text: t }),
      a.createEl("span", { cls: "paperforge-status-detail", text: s || "" }));
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
      s = r.createEl("div", { cls: "paperforge-paper-header" });
    s.createEl("div", {
      cls: "paperforge-paper-title pf-copy",
      text: e.title || "Untitled",
    }).addEventListener("click", () => {
      (navigator.clipboard.writeText(e.title || ""),
        new M.Notice("Title copied"));
    });
    let n = s.createEl("div", { cls: "paperforge-paper-meta" });
    (e.authors &&
      e.authors.length > 0 &&
      n.createEl("span", {
        cls: "paperforge-paper-authors",
        text: e.authors.join(", "),
      }),
      e.year &&
        n.createEl("span", {
          cls: "paperforge-paper-year",
          text: String(e.year),
        }));
    let i = r.createEl("div", { cls: "paperforge-status-strip" }),
      c = i.createEl("div", { cls: "paperforge-status-strip-left" }),
      l = i.createEl("div", { cls: "paperforge-status-strip-right" }),
      d = [
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
    for (let p of d) {
      let g = c.createEl("span", { cls: "paperforge-status-pill" }),
        y = "pending";
      (p.ok ? (y = "ok") : p.fail ? (y = "fail") : p.pending && (y = "pending"),
        g.addClass(y));
      let E = p.ok ? "\u2713" : p.fail ? "\u2717" : "\u25CB";
      (g.createEl("span", { cls: "paperforge-status-pill-icon", text: E }),
        g.createEl("span", { text: " " + p.label }));
    }
    if (e.pdf_path) {
      let p = l.createEl("button", { cls: "paperforge-contextual-btn" });
      (p.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\u{1F4C4}",
      }),
        p.createEl("span", { text: "\u6253\u5F00 PDF" }),
        p.addEventListener("click", () => {
          let g = e.pdf_path.match(/\[\[([^\]]+)\]\]/),
            y = g ? g[1] : e.pdf_path;
          this.app.vault.getAbstractFileByPath(y)
            ? this.app.workspace.openLinkText(y, "")
            : new M.Notice("[!!] PDF not found: " + y, 6e3);
        }));
    }
    if (e.fulltext_path) {
      let p = l.createEl("button", { cls: "paperforge-contextual-btn" });
      (p.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\u{1F4DD}",
      }),
        p.createEl("span", { text: "\u6253\u5F00\u5168\u6587" }),
        p.addEventListener("click", () => this._openFulltext(e.fulltext_path)));
    }
    let _ = l.createEl("button", { cls: "paperforge-contextual-btn" });
    if (
      (_.createEl("span", { text: o("version_panel_title") }),
      _.addEventListener("click", () => {
        this._switchToVersionMode(t);
      }),
      this._renderPaperOverviewCard(r, e),
      e.next_step === "ready" && e.deep_reading_status === "done")
    ) {
      let p = r.createEl("div", { cls: "paperforge-complete-row" });
      (p.createEl("span", { text: "\u2713" }),
        p.createEl("span", {
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
    let a = r.createEl("div", { cls: "paperforge-paper-overview-body" }),
      n = a.createEl("div", {
        cls: "paperforge-paper-overview-excerpt",
        text: "\u52A0\u8F7D\u4E2D...",
      });
    if (t.note_path) {
      let i = this.app.vault.getAbstractFileByPath(t.note_path);
      i
        ? this.app.vault
            .read(i)
            .then((c) => {
              let l = this._extractOverviewFromNote(c);
              if (l) {
                let d = l.length > 200 ? l.slice(0, 200) + "..." : l;
                if ((n.setText(d), l.length > 200)) {
                  let _ = a.createEl("div", {
                      cls: "paperforge-expand-container",
                    }),
                    p = _.createEl("button", {
                      cls: "paperforge-expand-icon",
                      title: "\u5C55\u5F00/\u6536\u8D77",
                    });
                  p.innerHTML =
                    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>';
                  let g = !1;
                  _.addEventListener("click", () => {
                    (n.setText(g ? d : l),
                      (p.innerHTML = g
                        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>'
                        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>'),
                      (g = !g));
                  });
                }
              } else
                n.setText(
                  "\u5C1A\u672A\u751F\u6210\u6587\u7AE0\u6982\u89C8\u3002\u8FD0\u884C /pf-deep \u5F00\u59CB\u7CBE\u8BFB\u3002"
                );
            })
            .catch(() => {
              n.setText("\u65E0\u6CD5\u8BFB\u53D6\u7B14\u8BB0\u5185\u5BB9");
            })
        : n.setText("\u7B14\u8BB0\u6587\u4EF6\u4E0D\u5B58\u5728");
    } else n.setText("\u5C1A\u672A\u751F\u6210\u6587\u7AE0\u6982\u89C8");
  }
  _extractOverviewFromNote(e) {
    if (!e) return null;
    let t = e.indexOf("## \u{1F50D} \u7CBE\u8BFB");
    if (t === -1) return null;
    let r = e.slice(t),
      s = [
        "**\u4E00\u53E5\u8BDD\u603B\u89C8:**",
        "**\u4E00\u53E5\u8BDD\u603B\u89C8**",
        "**\u6587\u7AE0\u6458\u8981:**",
        "**\u6587\u7AE0\u6458\u8981**",
      ];
    for (let i of s) {
      let c = r.indexOf(i);
      if (c !== -1) {
        let l = r.slice(c + i.length),
          d = ["**5 Cs", "**Figure", "**\u8BC1\u636E", "### Pass 2", "## "],
          _ = l.length;
        for (let y of d) {
          let E = l.indexOf(y);
          E !== -1 && E < _ && (_ = E);
        }
        let p = l.indexOf(`

`);
        p !== -1 && p < _ && (_ = p);
        let g = l.slice(0, _).trim();
        return (
          g.startsWith("**") && (g = g.slice(2)),
          g.endsWith("**") && (g = g.slice(0, -2)),
          g || null
        );
      }
    }
    let a = r.indexOf(`
`);
    if (a === -1) return null;
    let n = r
      .slice(a + 1)
      .split(
        `

`
      )[0]
      .trim();
    return !n || n.startsWith("###") || n.startsWith("##")
      ? null
      : n.length > 300
        ? n.slice(0, 300) + "..."
        : n;
  }
  _renderRecentDiscussionCard(e, t) {
    let r = e.createEl("div", { cls: "paperforge-discussion-card" });
    if (((r.style.display = "none"), !t.note_path)) return;
    let s = t.note_path.lastIndexOf("/"),
      n = (s !== -1 ? t.note_path.substring(0, s) : ".") + "/ai/discussion.md";
    this.app.vault.adapter
      .exists(n)
      .then((i) => {
        if (i) return this.app.vault.adapter.read(n);
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
          let p = r.createEl("div", { cls: "paperforge-discussion-item" }),
            g = p.createEl("div", { cls: "paperforge-discussion-q" });
          (g.createEl("span", {
            cls: "paperforge-discussion-q-label",
            text: "\u63D0\u95EE\uFF1A",
          }),
            g.createEl("span", {
              cls: "paperforge-discussion-q-text",
              text: _.question,
            }));
          let y = p.createEl("div", { cls: "paperforge-discussion-a" }),
            E = !1;
          if (
            (_.answer &&
              _.answer.length > 500 &&
              ((E = !0), y.classList.add("paperforge-discussion-a-collapsed")),
            await M.MarkdownRenderer.render(
              this.app,
              _.answer || "",
              y,
              n,
              this
            ),
            E)
          ) {
            let f = !1;
            ((p.style.cursor = "pointer"),
              p.addEventListener("click", () => {
                ((f = !f),
                  y.classList.toggle("paperforge-discussion-a-collapsed", !f),
                  y.classList.toggle("paperforge-discussion-a-expanded", f));
              }));
          }
        }
        r.createEl("a", {
          cls: "paperforge-discussion-viewall",
          text: "\u67E5\u770B\u5168\u90E8\u8BA8\u8BBA \u2192",
        }).addEventListener("click", (_) => {
          (_.preventDefault(),
            this.app.vault.getAbstractFileByPath(n)
              ? this.app.workspace.openLinkText(n, "")
              : new M.Notice(
                  "\u8BA8\u8BBA\u6587\u4EF6\u5C1A\u672A\u751F\u6210"
                ));
        });
      })
      .catch((i) => {
        console.error("PaperForge: discussion.md read error", n, i.message);
      });
  }
  _parseDiscussionMD(e) {
    let t = e.split(/\n## /).slice(1);
    if (t.length === 0) return null;
    let r = t[t.length - 1],
      s = [],
      a = r.split(/\*\*\u95EE\u9898:\*\*/).slice(1);
    for (let n of a) {
      let i = n.match(/\*\*\u89E3\u7B54:\*\*/);
      if (!i) continue;
      let c = n.substring(0, i.index).trim(),
        l = n.substring(i.index + 3 + 4).trim();
      s.push({ question: c, answer: l });
    }
    return s.slice(-3);
  }
  _renderPaperTechnicalDetails(e, t) {
    let r = this._currentPaperKey,
      s = e.createEl("div", { cls: "paperforge-technical-details" }),
      a = s.createEl("button", { cls: "paperforge-technical-details-toggle" }),
      n = s.createEl("div", { cls: "paperforge-technical-details-body" });
    ((n.style.display = "none"),
      this._techDetailsExpanded
        ? ((n.style.display = "block"),
          a.setText("\u6280\u672F\u8BE6\u60C5 \u25BE"))
        : a.setText("\u6280\u672F\u8BE6\u60C5 \u25B8"),
      a.addEventListener("click", () => {
        let p = n.style.display !== "none";
        ((n.style.display = p ? "none" : "block"),
          a.setText(
            p
              ? "\u6280\u672F\u8BE6\u60C5 \u25B8"
              : "\u6280\u672F\u8BE6\u60C5 \u25BE"
          ),
          (this._techDetailsExpanded = !p));
      }));
    let i = n.createEl("div", { cls: "paperforge-workflow-toggles" }),
      c = [
        { key: "do_ocr", label: "OCR", hint: "\u52A0\u5165 OCR" },
        {
          key: "analyze",
          label: "\u7CBE\u8BFB",
          hint: "\u6807\u8BB0\u7CBE\u8BFB",
        },
      ];
    for (let p of c) {
      let g = i.createEl("label", { cls: "paperforge-workflow-toggle" }),
        y = g.createEl("input", {
          type: "checkbox",
          cls: "paperforge-workflow-checkbox",
        });
      ((y.checked = t[p.key] === !0),
        g.createEl("span", {
          cls: "paperforge-workflow-toggle-label",
          text: p.label,
        }),
        g.createEl("span", {
          cls: "paperforge-workflow-toggle-hint",
          text: p.hint,
        }),
        y.addEventListener("change", async () => {
          let E = t.note_path
            ? this.app.vault.getAbstractFileByPath(t.note_path)
            : null;
          if (!E) {
            new M.Notice("[!!] Note file not found", 6e3);
            return;
          }
          let f = y.checked;
          (await this.app.fileManager.processFrontMatter(E, (b) => {
            b[p.key] = f;
          }),
            this._patchCachedEntry(r, { [p.key]: f }),
            (this._currentPaperEntry = qe(this._currentPaperEntry, {
              [p.key]: f,
            })));
        }));
    }
    let l = t.health || {},
      d = [
        ["PDF Health", l.pdf_health || "\u2014"],
        ["OCR Status", t.ocr_status || "\u2014"],
        ["Asset Health", l.asset_health || "\u2014"],
        ["Note Path", t.note_path || "\u2014"],
        ["Fulltext Path", t.fulltext_path || "\u2014"],
      ],
      _ = new Set(["Note Path", "Fulltext Path", "Key"]);
    for (let [p, g] of d) {
      let y = n.createEl("div", { cls: "paperforge-technical-row" });
      y.createEl("span", { cls: "paperforge-technical-label", text: p });
      let E = y.createEl("span", {
        cls: "paperforge-technical-value",
        text: String(g),
      });
      _.has(p) &&
        g &&
        g !== "\u2014" &&
        (E.addClass("pf-copy"),
        E.addEventListener("click", () => {
          (navigator.clipboard.writeText(g), new M.Notice(p + " copied"));
        }));
    }
  }
  _renderNextStepCard(e, t, r) {
    var c, l;
    let s = t.next_step || "ready",
      a = {
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
      n = a[s] || a.ready,
      i = e.createEl("div", { cls: "paperforge-next-step-card" });
    if (
      (s === "ready" && i.addClass("ready"),
      i.createEl("div", {
        cls: "paperforge-next-step-label",
        text: "Recommended Next Step",
      }),
      i.createEl("div", { cls: "paperforge-next-step-text", text: n.text }),
      n.cmd && n.cmd !== "ready")
    ) {
      let d = i.createEl("button", { cls: "paperforge-next-step-trigger" });
      (d.createEl("span", { text: n.icon + "  " + n.label }),
        d.addEventListener("click", () => {
          let _ = oe.find((p) => p.cmd === n.cmd);
          _ && this._runAction(_, d);
        }));
    } else if (s === "/pf-deep") {
      let d = i.createEl("button", { cls: "paperforge-next-step-trigger" });
      (d.createEl("span", { text: "\u{1F4CB}  " + o("copy_pf_deep_cmd") }),
        d.addEventListener("click", () => {
          let E = "/pf-deep " + r;
          navigator.clipboard
            .writeText(E)
            .then(() => {
              (d.setText("\u2713  " + o("copied")),
                new M.Notice(E + " copied"));
            })
            .catch(() => {
              new M.Notice("[!!] Clipboard write failed", 6e3);
            });
        }));
      let _ =
          ((l =
            (c = this.app.plugins.plugins.paperforge) == null
              ? void 0
              : c.settings) == null
            ? void 0
            : l.agent_platform) || "opencode",
        g =
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
        o("run_in_agent").replace("{0}", g)
      );
    } else
      s === "ready" &&
        i
          .createEl("button", { cls: "paperforge-next-step-trigger" })
          .createEl("span", { text: "\u2713  " + n.label });
  }
  _openFulltext(e) {
    if (!e) {
      new M.Notice("[!!] No fulltext path available for this paper", 6e3);
      return;
    }
    let t = this.app.vault.getAbstractFileByPath(e);
    t
      ? this.app.workspace.openLinkText(t.path, "")
      : new M.Notice("[!!] Fulltext file not found: " + e, 6e3);
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
      s = t.length,
      a = 0,
      n = 0,
      i = 0,
      c = 0,
      l = 0,
      d = 0,
      _ = 0;
    for (let m of t) {
      (m.has_pdf && a++,
        m.ocr_status === "done" && n++,
        m.ocr_status === "done" && m.analyze === !0 && i++,
        m.deep_reading_status === "done" && c++);
      let v = m.ocr_status || "";
      v === "pending" || v === "queued"
        ? l++
        : v === "processing"
          ? d++
          : (v === "failed" ||
              v === "blocked" ||
              v === "done_incomplete" ||
              v === "nopdf") &&
            _++;
    }
    r.createEl("div", { cls: "paperforge-collection-header" }).createEl("div", {
      cls: "paperforge-collection-title",
      text: e,
    });
    let g = r.createEl("div", { cls: "paperforge-workflow-overview" });
    g.createEl("div", {
      cls: "paperforge-section-label",
      text: "Workflow Overview",
    });
    let y = g.createEl("div", { cls: "paperforge-workflow-funnel" }),
      E = [
        { value: s, label: "Total" },
        { value: a, label: "PDF Ready" },
        { value: n, label: "OCR Done" },
        { value: c, label: "Deep Read" },
      ];
    for (let m = 0; m < E.length; m++) {
      let v = y.createEl("div", { cls: "paperforge-workflow-stage" });
      (v.createEl("div", {
        cls: "paperforge-workflow-stage-value",
        text: String(E[m].value),
      }),
        v.createEl("div", {
          cls: "paperforge-workflow-stage-label",
          text: E[m].label,
        }),
        m < E.length - 1 &&
          y.createEl("div", {
            cls: "paperforge-workflow-arrow",
            text: "\u2192",
          }));
    }
    if (l + d + n + _ > 0) {
      let m = r.createEl("div", { cls: "paperforge-ocr-section" }),
        v = m.createEl("div", { cls: "paperforge-collection-ocr-header" });
      v.createEl("h4", { cls: "paperforge-ocr-title", text: "OCR Pipeline" });
      let k = v.createEl("span", { cls: "paperforge-ocr-badge idle" });
      d > 0
        ? (k.addClass("active"), k.setText("Processing"))
        : l > 0
          ? k.setText("Pending")
          : (k.addClass("idle"), k.setText("Idle"));
      let R = m.createEl("div", { cls: "paperforge-progress-track" });
      d > 0 && R.addClass("paperforge-processing");
      let P = l + d + n + _,
        O = [
          { cls: "pending", count: l },
          { cls: "active", count: d },
          { cls: "done", count: n },
          { cls: "failed", count: _ },
        ];
      for (let H of O)
        if (H.count > 0) {
          let B = ((H.count / P) * 100).toFixed(1);
          R.createEl("div", {
            cls: `paperforge-progress-seg ${H.cls}`,
            attr: { style: `width:${B}%` },
          });
        }
      let D = m.createEl("div", { cls: "paperforge-ocr-counts" }),
        j = [
          { cls: "pending", value: l, label: "Pending" },
          { cls: "active", value: d, label: "Processing" },
          { cls: "done", value: n, label: "Done" },
          { cls: "failed", value: _, label: "Attention" },
        ];
      for (let H of j) {
        let B = D.createEl("div", { cls: "paperforge-ocr-count" });
        (B.createEl("div", {
          cls: "paperforge-ocr-count-value",
          text: H.value.toString(),
        }),
          B.createEl("div", {
            cls: "paperforge-ocr-count-label",
            text: H.label,
          }));
      }
    }
    let f = r.createEl("div", { cls: "paperforge-collection-actions" }),
      b = f.createEl("button", { cls: "paperforge-contextual-btn primary" });
    (b.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    }),
      b.createEl("span", { text: "Run OCR" }),
      b.addEventListener("click", () => {
        let m = oe.find((v) => v.id === "paperforge-ocr");
        m && this._runAction(m, b);
      }));
    let w = f.createEl("button", { cls: "paperforge-contextual-btn" });
    (w.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    }),
      w.createEl("span", { text: "Sync Library" }),
      w.addEventListener("click", () => {
        let m = oe.find((v) => v.id === "paperforge-sync");
        m && this._runAction(m, w);
      }));
    let x = f.createEl("button", { cls: "paperforge-contextual-btn warn" });
    (x.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BA",
    }),
      x.createEl("span", { text: "Redo OCR" }),
      x.addEventListener("click", () => {
        let m = oe.find((v) => v.id === "paperforge-ocr-redo");
        m && this._runAction(m, x);
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
      s = typeof r == "string" ? r : "";
    if (!s) {
      new M.Notice("Cannot determine vault path");
      return;
    }
    ((this._versionPapers = lt(s)),
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
      s = typeof r == "string" ? r : "";
    if (!s) {
      e.createEl("div", {
        cls: "paperforge-status-error",
        text: "Could not determine vault path",
      });
      return;
    }
    (!this._versionPapers || this._versionPapers.length === 0) &&
      (this._versionPapers = lt(s));
    let a = e.createEl("div", { cls: "paperforge-version-left" }),
      n = e.createEl("div", { cls: "paperforge-version-right" }),
      i = a.createEl("input", {
        cls: "paperforge-version-filter",
        attr: { type: "text", placeholder: o("version_filter_placeholder") },
      });
    i.value = this._versionFilter;
    let c = a.createEl("div", { cls: "paperforge-version-paper-list" }),
      l = () => {
        c.empty();
        let b = this._versionFilter.toLowerCase(),
          w = this._versionPapers
            ? this._versionPapers.filter(
                (m) =>
                  !b ||
                  m.key.toLowerCase().includes(b) ||
                  m.title.toLowerCase().includes(b)
              )
            : [];
        if (w.length === 0) {
          c.createEl("div", {
            cls: "paperforge-meta",
            text: o("version_no_backups"),
          });
          return;
        }
        let x = c.createEl("div", {
          cls: "paperforge-meta",
          text: o("version_papers_count").replace("{n}", String(w.length)),
        });
        for (let m of w) {
          let v = c.createEl("div", { cls: "paperforge-version-paper-item" }),
            k = v.createEl("span", {
              cls: "paperforge-version-paper-title",
              text: m.title,
            }),
            R = v.createEl("span", {
              cls: "paperforge-version-paper-versions",
              text: m.versions.map((P) => P.label).join(" "),
            });
          v.addEventListener("click", () => {
            (c
              .querySelectorAll(".paperforge-version-paper-item.selected")
              .forEach((P) => P.removeClass("selected")),
              v.addClass("selected"),
              _(m));
          });
        }
      };
    i.addEventListener("input", () => {
      ((this._versionFilter = i.value), l());
    });
    let d = n.createEl("div", { cls: "paperforge-version-timeline-area" }),
      _ = (b) => {
        if (
          (d.empty(),
          d
            .createEl("div", { cls: "paperforge-version-timeline-header" })
            .createEl("span", { cls: "pf-title", text: b.title }),
          b.versions.length === 0)
        ) {
          d.createEl("div", {
            cls: "paperforge-meta",
            text: o("version_no_backups"),
          });
          return;
        }
        let x = d.createEl("div", { cls: "paperforge-version-timeline" });
        for (let m of b.versions) {
          let v = m.label === b.currentLabel,
            k = x.createEl("div", {
              cls:
                "paperforge-version-entry" +
                (v ? " paperforge-version-current" : ""),
            }),
            R = k.createEl("div", { cls: "paperforge-version-dot" }),
            P = k.createEl("div", { cls: "paperforge-version-content" }),
            O = P.createEl("div", { cls: "paperforge-version-label-row" });
          (O.createEl("span", {
            cls: "paperforge-version-label",
            text: m.label,
          }),
            v &&
              O.createEl("span", {
                cls: "paperforge-version-current-tag",
                text: o("version_current"),
              }));
          let D = m.created_at ? m.created_at.slice(0, 10) : "";
          P.createEl("div", {
            cls: "paperforge-meta",
            text: D + " \u2014 " + m.source,
          });
          let j = m.fulltext_size
            ? m.fulltext_size > 1024
              ? (m.fulltext_size / 1024).toFixed(0) + "KB"
              : m.fulltext_size + "B"
            : "";
          j && P.createEl("div", { cls: "paperforge-meta", text: j });
          let H = P.createEl("div", { cls: "paperforge-version-actions" });
          (H.createEl("button", {
            cls: "pf-btn-primary",
            text: o("version_restore_btn"),
          }).addEventListener("click", () => {
            Bt(s, b.key, m.label)
              ? new M.Notice(
                  o("version_restore_done").replace("{label}", m.label)
                )
              : new M.Notice("Restore failed", 6e3);
          }),
            b.versions.length > 1 &&
              !v &&
              H.createEl("button", {
                cls: "pf-btn-secondary",
                text: o("version_compare_btn"),
              }).addEventListener("click", () => {
                g(b, m.label, b.currentLabel);
              }));
        }
      },
      p = n.createEl("div", { cls: "paperforge-version-compare" });
    p.style.display = "none";
    let g = (b, w, x) => {
        let m = At(s, b.key, w, x);
        ((p.style.display = "block"), p.empty());
        let v = p.createEl("div", { cls: "paperforge-version-compare-header" });
        if (
          (v.createEl("span", {
            cls: "pf-title",
            text: o("version_compare_title")
              .replace("{vA}", w)
              .replace("{vB}", x),
          }),
          v.createEl("span", {
            cls: "paperforge-meta",
            text: o("version_compare_paragraphs").replace(
              "{n}",
              String(m.length)
            ),
          }),
          m.length === 0)
        ) {
          p.createEl("div", { cls: "paperforge-meta", text: "No changes" });
          return;
        }
        let k = p.createEl("div", { cls: "paperforge-version-diff-list" });
        for (let R of m) {
          let P = k.createEl("div", { cls: "paperforge-version-diff-row" }),
            O =
              R.type === "added" ? "[+]" : R.type === "removed" ? "[-]" : "[~]",
            D = R.heading || "paragraph " + (R.paragraphIndex + 1);
          (P.createEl("span", {
            cls: "paperforge-version-diff-label",
            text: O + " " + D,
          }),
            R.oldText &&
              P.createEl("pre", {
                cls: "paperforge-version-diff-old",
                text: R.oldText.slice(0, 200),
              }),
            R.newText &&
              P.createEl("pre", {
                cls: "paperforge-version-diff-new",
                text: R.newText.slice(0, 200),
              }));
        }
      },
      y = e.createEl("div", { cls: "paperforge-version-actions-bar" }),
      E = y.createEl("button", {
        cls: "pf-btn-primary",
        text: o("version_restore_selected"),
      }),
      f = y.createEl("button", {
        cls: "pf-btn-secondary",
        text: o("version_clear_old").replace("{size}", ""),
      });
    l();
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
      s = r.createEl("span", { cls: "paperforge-search-mode", text: "M" });
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
        var n;
        let a = ((n = this._searchInput) == null ? void 0 : n.value) || "";
        if (
          (a.startsWith("@") && !a.startsWith("@ ")
            ? ((this._searchMode = "@"),
              s.setText("@"),
              s.addClass("deep"),
              this._searchInput &&
                (this._searchInput.placeholder = o(
                  "retrieval_search_placeholder_deep"
                )))
            : ((this._searchMode = "M"),
              s.setText("M"),
              s.removeClass("deep"),
              this._searchInput &&
                (this._searchInput.placeholder = o(
                  "retrieval_search_placeholder"
                ))),
          clearTimeout(this._searchTimer),
          !a.trim())
        ) {
          ((this._searchState = "idle"),
            (this._searchResults = null),
            (this._searchActiveIndex = -1),
            this._renderSearchState());
          return;
        }
        a.startsWith("@") ||
          (this._searchTimer = setTimeout(() => {
            this.executeSearch();
          }, 200));
      }),
      this._searchInput.addEventListener("keydown", (a) => {
        var n, i;
        if (a.key === "Escape") {
          (a.preventDefault(),
            this._searchInput &&
              ((this._searchInput.value = ""), this._searchInput.blur()),
            (this._searchState = "idle"),
            (this._searchResults = null),
            (this._searchActiveIndex = -1),
            this._renderSearchState());
          return;
        }
        if (a.key === "ArrowDown" || a.key === "ArrowUp") {
          if (
            this._searchState !== "results" ||
            !((n = this._searchResults) != null && n.length)
          )
            return;
          a.preventDefault();
          let c = this._searchResults.length;
          a.key === "ArrowDown"
            ? (this._searchActiveIndex = Math.min(
                this._searchActiveIndex + 1,
                c - 1
              ))
            : (this._searchActiveIndex = Math.max(
                this._searchActiveIndex - 1,
                -1
              ));
          let l =
            (i = this._searchResultsEl) == null
              ? void 0
              : i.querySelectorAll(".paperforge-search-result-card");
          l &&
            l.forEach((d, _) => {
              _ === this._searchActiveIndex
                ? (d.setAttribute("aria-selected", "true"),
                  d.classList.add("active"))
                : (d.setAttribute("aria-selected", "false"),
                  d.classList.remove("active"));
            });
          return;
        }
        if (a.key === "Enter" && a.ctrlKey) {
          (a.preventDefault(),
            this._searchTimer &&
              (clearTimeout(this._searchTimer), (this._searchTimer = void 0)));
          let c = this._searchMode;
          ((this._searchMode = "@"),
            this.executeSearch(),
            (this._searchMode = c));
          return;
        }
        a.key === "Enter" &&
          (a.preventDefault(),
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
          let s = this.app.setting;
          if (s && typeof s == "object") {
            let a = s.openTab;
            typeof a == "function" && a.call(s, "paperforge");
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
          s = r.createEl("button", {
            cls: "pf-btn-primary",
            text: o("retrieval_run_doctor"),
          });
        (s.addEventListener("click", () => {
          let n = this.app.vault.adapter.basePath;
          if (typeof n == "string") {
            let { path: i, extraArgs: c = [] } = z(n, null, void 0, void 0);
            (0, ve.spawn)(i, [...c, "-m", "paperforge", "doctor"], {
              cwd: n,
              stdio: "inherit",
            });
          }
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
            s.focus();
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
          let s = this.app.setting;
          if (s && typeof s == "object") {
            let a = s.openTab;
            typeof a == "function" && a.call(s, "paperforge");
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
    let s = t ? "retrieve" : "search";
    ((this._searchState = "searching"),
      (this._searchResults = null),
      (this._searchActiveIndex = -1),
      this._renderSearchState());
    let a = this.app.vault.adapter,
      n = "";
    if (a && typeof a == "object" && "basePath" in a) {
      let E = a.basePath;
      n = typeof E == "string" ? E : "";
    }
    if (!n) {
      ((this._searchState = "backend-unavailable"), this._renderSearchState());
      return;
    }
    let i = null,
      l = this.app.plugins;
    if (l && typeof l == "object" && "plugins" in l) {
      let E = l.plugins;
      if (E && typeof E == "object" && "paperforge" in E) {
        let f = E.paperforge;
        f && typeof f == "object" && "settings" in f && (i = f.settings);
      }
    }
    let { path: d, extraArgs: _ = [] } = z(n, i, void 0, void 0),
      p = s === "retrieve" ? ["--deep"] : [],
      g = (0, ve.spawn)(
        d,
        [..._, "-m", "paperforge", "--vault", n, s, r, ...p, "--json"],
        { cwd: n, timeout: 3e4 }
      ),
      y = [];
    (g.stdout.on("data", (E) => {
      y.push(E.toString("utf-8"));
    }),
      g.stderr.on("data", () => {}),
      g.on("close", (E) => {
        if (E !== 0) {
          let m = Qe(String(E));
          ((this._searchState = this._mapErrorToSearchState(m.type)),
            this._renderSearchState());
          return;
        }
        let f = y.join(""),
          b = f.indexOf("{"),
          w = f.lastIndexOf("}"),
          x = "";
        if (b !== -1 && w > b) x = f.slice(b, w + 1);
        else {
          let m = f.indexOf("["),
            v = f.lastIndexOf("]");
          m !== -1 && v > m && (x = f.slice(m, v + 1));
        }
        if (!x) {
          ((this._searchState = "internal-error"), this._renderSearchState());
          return;
        }
        try {
          let m = JSON.parse(x),
            v = [];
          if (m && typeof m == "object" && "data" in m) {
            let k = m.data;
            if (k && typeof k == "object") {
              let R = k;
              "matches" in R && Array.isArray(R.matches) && (v = R.matches);
            }
          }
          ((this._searchResults = v),
            (this._searchState = v.length > 0 ? "results" : "empty"),
            this._renderSearchState());
        } catch (m) {
          let v = m instanceof Error ? m.message : String(m);
          ((this._searchState = "internal-error"), this._renderSearchState());
        }
      }),
      g.on("error", (E) => {
        let f = E.code;
        if (typeof f == "string") {
          let b = Qe(f);
          this._searchState = this._mapErrorToSearchState(b.type);
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
    for (let a = 0; a < e.length; a++) {
      let n = e[a];
      if (!n || typeof n != "object") continue;
      let i = n,
        c = a === this._searchActiveIndex,
        l = this._searchResultsEl.createEl("div", {
          cls: "paperforge-search-result-card",
          attr: {
            role: "option",
            tabindex: "0",
            "aria-selected": c ? "true" : "false",
            "aria-posinset": String(a + 1),
            "aria-setsize": String(e.length),
          },
        });
      c && l.addClass("active");
      let d =
        typeof i.title == "string"
          ? i.title
          : typeof i.file_name == "string"
            ? i.file_name
            : "(untitled)";
      l.createEl("div", { cls: "paperforge-search-result-title", text: d });
      let _ = typeof i.zotero_key == "string" ? i.zotero_key : "",
        p =
          typeof i.main_note_path == "string" && i.main_note_path
            ? i.main_note_path
            : null,
        g = typeof i.note_path == "string" && i.note_path ? i.note_path : null,
        y = p || g;
      if (!y && _) {
        let b = this._getCachedIndex().find(
          (w) =>
            w !== null &&
            typeof w == "object" &&
            "zotero_key" in w &&
            w.zotero_key === _
        );
        if (b && typeof b == "object") {
          let w = b;
          y =
            typeof w.main_note_path == "string" && w.main_note_path
              ? w.main_note_path
              : typeof w.note_path == "string" && w.note_path
                ? w.note_path
                : null;
        }
      }
      (y
        ? l.addEventListener("click", (f) => {
            let b = f.ctrlKey || f.metaKey;
            this.app.workspace.openLinkText(y, "", b);
          })
        : l.addEventListener("click", () => {
            new M.Notice("[!!] Note not found: " + (_ || "unknown"), 6e3);
          }),
        l.addEventListener("keydown", (f) => {
          if (f.key === "Enter" && y) {
            f.preventDefault();
            let b = f.ctrlKey || f.metaKey;
            this.app.workspace.openLinkText(y, "", b);
          }
        }));
      let E = l.createEl("div", { cls: "paperforge-search-result-meta" });
      if (
        (typeof i.first_author == "string" &&
          i.first_author &&
          E.createEl("span", {
            cls: "paperforge-search-result-author",
            text: i.first_author,
          }),
        typeof i.journal == "string" &&
          i.journal &&
          E.createEl("span", {
            cls: "paperforge-search-result-journal",
            text: i.journal,
          }),
        i.score !== void 0)
      ) {
        let f = i.score,
          b = typeof f == "number" ? f.toFixed(3) : String(f);
        E.createEl("span", {
          cls: "paperforge-search-result-score",
          text: "Score: " + b,
        });
      }
      if (
        (typeof i.domain == "string" &&
          i.domain &&
          l.createEl("span", {
            cls: "paperforge-search-result-tag",
            text: i.domain,
          }),
        typeof i.abstract == "string" && i.abstract)
      ) {
        let f = i.abstract;
        l.createEl("div", {
          cls: "paperforge-search-result-abstract",
          text: f.length > 200 ? f.slice(0, 200) + "..." : f,
        });
      }
      if (t && typeof i.text == "string" && i.text) {
        let f = i.text;
        l.createEl("div", {
          cls: "paperforge-search-result-source",
          text: f.length > 300 ? f.slice(0, 300) + "..." : f,
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
  _runAction(e, t) {
    var p, g;
    if (e.disabled) {
      new M.Notice(
        `[i] ${e.disabledMsg || "This action is not yet available."}`,
        6e3
      );
      return;
    }
    if (t.classList.contains("running")) return;
    t.addClass("running");
    let r = this.app.vault.adapter.basePath;
    this._showMessage("Processing...", "running");
    let s = Array.isArray(e.args) ? [...e.args] : [];
    if (e.needsKey) {
      let y = this.app.workspace.getActiveFile(),
        E = null;
      if (y) {
        let f = this.app.metadataCache.getFileCache(y);
        if (
          (f && f.frontmatter && f.frontmatter.zotero_key
            ? (E = f.frontmatter.zotero_key)
            : (E = this._extractZoteroKeyFromPath(y.path)),
          E)
        )
          s = [...s, E];
        else if (f && f.frontmatter) {
          (this._showMessage(
            "[!!] No zotero_key in active note frontmatter",
            "error"
          ),
            new M.Notice(
              "[!!] Open a paper note with a zotero_key in its frontmatter first",
              6e3
            ),
            t.removeClass("running"));
          return;
        } else {
          (this._showMessage("[!!] No frontmatter in active note", "error"),
            new M.Notice(
              "[!!] The active note has no frontmatter with a zotero_key",
              6e3
            ),
            t.removeClass("running"));
          return;
        }
      } else {
        (this._showMessage("[!!] No active note open", "error"),
          new M.Notice(
            "[!!] Open a paper note with a zotero_key in its frontmatter first",
            6e3
          ),
          t.removeClass("running"));
        return;
      }
    }
    e.needsFilter && (s = [...s, "--all"]);
    let a = e.needsFilter ? 6e4 : e.needsKey ? 3e4 : 6e5,
      { path: n, extraArgs: i = [] } = z(
        r,
        (g =
          (p = this.app.plugins.plugins.paperforge) == null
            ? void 0
            : p.settings) != null
          ? g
          : null,
        void 0,
        void 0
      ),
      c = (0, ve.spawn)(n, [...i, "-m", "paperforge", e.cmd, ...s], {
        cwd: r,
        timeout: a,
      }),
      l = [],
      d = Date.now(),
      _ = setInterval(() => this._fetchStats(!0), 4e3);
    (c.stdout.on("data", (y) => {
      let E = y
        .toString("utf-8")
        .split(
          `
`
        )
        .filter(Boolean);
      for (let f of E) {
        let b = f.trim();
        b &&
          (l.push(b),
          this._showMessage(
            l.slice(-8).join(`
`),
            "running"
          ));
      }
    }),
      c.stderr.on("data", (y) => {
        let E = y
          .toString("utf-8")
          .split(
            `
`
          )
          .filter(Boolean);
        for (let f of E) {
          if (f.includes("\r") || f.includes("%") || f.includes("\u2588"))
            continue;
          let b = f.trim();
          b &&
            !b.match(/^\d+%|^\|/) &&
            (l.push(b),
            this._showMessage(
              l.slice(-8).join(`
`),
              "running"
            ));
        }
      }),
      c.on("close", (y) => {
        (clearInterval(_), t.removeClass("running"));
        let E = ((Date.now() - d) / 1e3).toFixed(1);
        if (y !== 0) {
          let f = l.slice(-3).join(" | ") || "exit code " + y;
          (e.cmd === "repair" || e.cmd === "ocr") && y === 1
            ? (this._showMessage("[WARN] " + f, "running"),
              new M.Notice("[WARN] " + e.cmd + " partial: " + f, 8e3),
              this._fetchStats(!0))
            : (this._showMessage("[!!] " + f, "error"),
              new M.Notice("[!!] " + e.cmd + " failed: " + f, 8e3));
        } else if (e.needsKey || e.needsFilter) {
          let f = l.join(`
`);
          if (f.trim())
            try {
              (JSON.parse(f),
                navigator.clipboard
                  .writeText(f)
                  .then(() => {
                    let b = `${E}s \u2014 ${f.length} chars copied`;
                    (this._showMessage("[OK] " + e.title + ": " + b, "ok"),
                      new M.Notice(
                        "[OK] " + e.okMsg + " \u2014 " + f.length + " chars"
                      ));
                  })
                  .catch((b) => {
                    (this._showMessage(
                      "[!!] Clipboard write failed: " + b.message,
                      "error"
                    ),
                      new M.Notice("[!!] Clipboard error", 6e3));
                  }));
            } catch (b) {
              (this._showMessage("[!!] Invalid JSON from " + e.title, "error"),
                new M.Notice(
                  "[!!] " +
                    e.title +
                    " returned invalid JSON: " +
                    b.message.slice(0, 100),
                  8e3
                ));
            }
          else
            (this._showMessage("[!!] No output from context command", "error"),
              new M.Notice("[!!] Context command returned empty output", 8e3));
          this._fetchStats(!0);
        } else {
          let b =
              l.filter((x) => x.match(/updated \d+/)).pop() ||
              l[l.length - 1] ||
              "",
            w = `${E}s \u2014 ${b}`;
          (this._showMessage("[OK] " + e.title + ": " + w, "ok"),
            new M.Notice("[OK] " + e.okMsg),
            this._contentEl && this._contentEl.removeClass("switching"),
            (this._cachedStats = null));
          try {
            this._fetchStats(!1);
          } catch (x) {
            console.log("[PF] fetchStats error:", x);
          }
          (console.log("[PF] close cmd=" + e.cmd + " id=" + e.id),
            e.cmd === "sync" &&
              Ke(this.app, this.app.plugins.plugins.paperforge, r));
        }
      }),
      c.on("error", (y) => {
        (t.removeClass("running"),
          this._contentEl && this._contentEl.removeClass("switching"),
          this._showMessage("[!!] " + y.message, "error"),
          new M.Notice("[!!] Cannot start: " + y.message, 8e3));
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
            s = r.mode,
            a = r.filePath;
          (this._currentMode === s && this._currentFilePath === a) ||
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
    let t = e.app.workspace.getLeavesOfType(we);
    if (t.length > 0) {
      e.app.workspace.revealLeaf(t[0]);
      return;
    }
    let r = e.app.workspace.getRightLeaf(!1);
    r &&
      (await r.setViewState({ type: we, active: !0 }),
      e.app.workspace.revealLeaf(r));
  }
};
var Ue = class extends X.Plugin {
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
  }
  async onload() {
    (await this.loadSettings(),
      this.saveSettings(),
      ut(this.app),
      this.registerView(we, (t) => new Fe(t)));
    try {
      (0, X.addIcon)(De, pt);
    } catch (t) {}
    (this.addRibbonIcon(De, "PaperForge Dashboard", () => Fe.open(this)),
      oe.find((t) => t.id === "paperforge-ocr-redo") &&
        this.addRibbonIcon("reset", "PaperForge: Redo OCR", () => {
          let t = this.app.vault.adapter.basePath;
          new X.Notice("PaperForge: Redo OCR starting...");
          let { path: r, extraArgs: s } = z(t, this.settings, void 0, void 0);
          (0, fe.execFile)(
            r,
            [...s, "-m", "paperforge", "ocr", "redo"],
            { cwd: t, timeout: 6e5 },
            (a, n, i) => {
              if (a) {
                new X.Notice("PaperForge: Redo OCR failed");
                return;
              }
              new X.Notice("PaperForge: Redo OCR done");
            }
          );
        }),
      this.addSettingTab(new Ze(this.app, this)),
      this.addCommand({
        id: "paperforge-status-panel",
        name: `PaperForge: ${o("guide_open")}`,
        callback: () => Fe.open(this),
      }));
    for (let t of oe)
      this.addCommand({
        id: t.id,
        name: `PaperForge: ${t.title}`,
        callback: () => {
          if (t.disabled) {
            new X.Notice(
              `[i] ${t.disabledMsg || "This action is not yet available."}`,
              6e3
            );
            return;
          }
          let r = this.app.vault.adapter.basePath;
          new X.Notice(`PaperForge: running ${t.cmd}...`);
          let { path: s, extraArgs: a = [] } = z(
              r,
              this.settings,
              void 0,
              void 0
            ),
            n = Array.isArray(t.args) ? [...t.args] : [];
          (0, fe.execFile)(
            s,
            [...a, "-m", "paperforge", t.cmd, ...n],
            { cwd: r, timeout: 3e5 },
            (i, c, l) => {
              if (i) {
                new X.Notice(
                  `[!!] ${t.cmd} failed: ${(l || i.message).slice(0, 120)}`,
                  8e3
                );
                return;
              }
              new X.Notice(
                `[OK] ${
                  t.okMsg ||
                  c
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
    (this.settings.auto_update_on_startup === !0 &&
      this.settings.setup_complete &&
      setTimeout(() => this._autoUpdate(), 3e3),
      this._startFilePolling(),
      this._firstLaunchSnapshotMigration(),
      this._checkReleaseNotes());
  }
  _firstLaunchSnapshotMigration() {
    let e = this.app.vault.adapter.basePath;
    if (!e) return;
    let r = le(e).memoryStatePath;
    if (!Z.existsSync(r)) {
      let s = z(e, this.settings, void 0, void 0);
      [
        ["runtime-health", "--json"],
        ["memory", "status", "--json"],
        ["embed", "status", "--json"],
      ].forEach((n) => {
        let i = [...s.extraArgs, "-m", "paperforge", "--vault", e, ...n];
        (0, fe.execFile)(
          s.path,
          i,
          { cwd: e, timeout: 6e4, windowsHide: !0 },
          () => {}
        );
      });
    }
  }
  _autoUpdate() {
    let e = this.app.vault.adapter.basePath,
      { path: t, extraArgs: r = [] } = z(e, this.settings, void 0, void 0),
      s = this.manifest.version,
      a = `paperforge==${s}`,
      n = `git+https://github.com/LLLin000/PaperForge.git@${s}`,
      i = (c, l) => {
        (0, fe.spawn)(t, [...r, "-m", "pip", "install", "--upgrade", c], {
          cwd: e,
          timeout: 12e4,
          env: Se(),
        }).on("close", (_) => l(_ === 0));
      };
    (0, fe.execFile)(
      t,
      [...r, "-c", "import paperforge; print(paperforge.__version__)"],
      { cwd: e, timeout: 1e4 },
      (c, l) => {
        let d = (p) => {
          (console.log(
            `[PaperForge] Auto-update: trying PyPI (paperforge==${s})`
          ),
            i(a, (g) => {
              if (g) {
                (console.log("[PaperForge] Auto-update: installed via PyPI"),
                  new X.Notice(`[OK] PaperForge CLI ${p}`, 5e3));
                return;
              }
              (console.warn(
                "[PaperForge] Auto-update: PyPI failed, falling back to git..."
              ),
                i(n, (y) => {
                  y &&
                    (console.log("[PaperForge] Auto-update: installed via git"),
                    new X.Notice(`[OK] PaperForge CLI ${p} (via git)`, 5e3));
                }));
            }));
        };
        if (c) {
          d("installed");
          return;
        }
        let _ = l.trim();
        _ !== s && d(`${_} -> ${s}`);
      }
    );
  }
  _startFilePolling() {
    let e = this.app.vault.adapter.basePath;
    this._pollTimer = setInterval(() => {
      (this._checkExports(e), this._checkOcr(e));
    }, 12e4);
  }
  _checkExports(e) {
    if (this._autoSyncRunning) return;
    let t = le(e).exportsDir;
    if (!Z.existsSync(t)) return;
    let r = 0;
    try {
      Z.readdirSync(t).forEach((s) => {
        if (!s.endsWith(".json")) return;
        let a = Z.statSync(Te.join(t, s));
        a.mtimeMs > r && (r = a.mtimeMs);
      });
    } catch (s) {
      return;
    }
    r > this._lastExportMtime &&
      ((this._lastExportMtime = r), this._autoSync(e));
  }
  _autoSync(e) {
    if (this._autoSyncRunning) return;
    this._autoSyncRunning = !0;
    let t = z(e, this.settings, void 0, void 0);
    if (!t.path) {
      this._autoSyncRunning = !1;
      return;
    }
    let r = `"${t.path}" -m paperforge --vault "${e}" sync`;
    (0, fe.exec)(r, { timeout: 12e4, encoding: "utf-8" }, (s, a, n) => {
      ((this._autoSyncRunning = !1),
        (this._memoryStatusText = null),
        s || (this._lastSyncTime = new Date().toLocaleTimeString()));
      try {
        let i = le(e).exportsDir,
          c = 0;
        (Z.readdirSync(i).forEach((l) => {
          l.endsWith(".json") &&
            (c = Math.max(c, Z.statSync(Te.join(i, l)).mtimeMs));
        }),
          (this._lastExportMtime = c));
      } catch (i) {}
    });
  }
  _checkOcr(e) {
    if (this._autoSyncRunning) return;
    let t = le(e).ocrDir;
    if (Z.existsSync(t))
      try {
        Z.readdirSync(t, { withFileTypes: !0 }).forEach((r) => {
          if (!r.isDirectory()) return;
          let s = Te.join(t, r.name, "meta.json");
          if (!Z.existsSync(s)) return;
          let a = Z.statSync(s),
            n = this._lastOcrMtimes[r.name] || 0;
          if (
            a.mtimeMs <= n ||
            ((this._lastOcrMtimes[r.name] = a.mtimeMs), this._autoSyncRunning)
          )
            return;
          this._autoSyncRunning = !0;
          let i = z(e, this.settings, void 0, void 0);
          if (!i.path) {
            this._autoSyncRunning = !1;
            return;
          }
          let c = `"${i.path}" -m paperforge --vault "${e}" sync`;
          (0, fe.exec)(c, { timeout: 3e4, encoding: "utf-8" }, () => {
            ((this._autoSyncRunning = !1), (this._memoryStatusText = null));
          });
        });
      } catch (r) {}
  }
  readPaperforgeJson() {
    let e = this.app.vault.adapter.basePath,
      t = Te.join(e, "paperforge.json"),
      r = {
        system_dir: "System",
        resources_dir: "Resources",
        literature_dir: "Literature",
        base_dir: "Bases",
      };
    try {
      if (!Z.existsSync(t)) return r;
      let s = Z.readFileSync(t, "utf-8"),
        a = JSON.parse(s),
        n = a.vault_config || {};
      return {
        system_dir: n.system_dir || a.system_dir || r.system_dir,
        resources_dir: n.resources_dir || a.resources_dir || r.resources_dir,
        literature_dir:
          n.literature_dir || a.literature_dir || r.literature_dir,
        base_dir: n.base_dir || a.base_dir || r.base_dir,
      };
    } catch (s) {
      return (
        console.warn(
          "PaperForge: Failed to read paperforge.json, using defaults",
          s
        ),
        r
      );
    }
  }
  savePaperforgeJson(e) {
    let t = this.app.vault.adapter.basePath,
      r = Te.join(t, "paperforge.json"),
      s = {};
    try {
      Z.existsSync(r) && (s = JSON.parse(Z.readFileSync(r, "utf-8")));
    } catch (n) {
      console.warn("PaperForge: Failed to read paperforge.json for update", n);
    }
    (!s.vault_config || typeof s.vault_config != "object") &&
      (s.vault_config = {});
    let a = ["system_dir", "resources_dir", "literature_dir", "base_dir"];
    for (let n of a) e[n] !== void 0 && (s.vault_config[n] = e[n]);
    s.schema_version || (s.schema_version = "2");
    for (let n of a) delete s[n];
    try {
      if (
        (Z.writeFileSync(r, JSON.stringify(s, null, 2), "utf-8"), this.settings)
      ) {
        let n = this.readPaperforgeJson();
        ((this.settings.system_dir = n.system_dir),
          (this.settings.resources_dir = n.resources_dir),
          (this.settings.literature_dir = n.literature_dir),
          (this.settings.base_dir = n.base_dir));
      }
    } catch (n) {
      (console.error("PaperForge: Failed to write paperforge.json", n),
        new X.Notice(
          "PaperForge: Failed to save configuration to paperforge.json"
        ));
    }
  }
  onunload() {
    (this._pollTimer && clearInterval(this._pollTimer),
      this.app.workspace.detachLeavesOfType(we));
  }
  async loadSettings() {
    ((this.settings = Object.assign({}, Be, await this.loadData())),
      this.settings.features &&
        Be.features &&
        (this.settings.features = Object.assign(
          {},
          Be.features,
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
    for (let t of Object.keys(Be))
      t in this.settings && (e[t] = this.settings[t]);
    await this.saveData(e);
  }
  _checkReleaseNotes() {
    let e = this.manifest.version;
    if (this.settings.last_seen_version === e) return;
    let a = (Xe().versions || []).find((i) => i.version === e);
    class n extends X.Modal {
      constructor(c, l) {
        (super(c), (this._entry = l));
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
            for (let l of this._entry.breaking_or_migration)
              c.createEl("p", {
                text: `\u2022 ${l}`,
                cls: "paperforge-modal-item",
              });
          }
          if (this._entry.new_features && this._entry.new_features.length > 0) {
            c.createEl("h4", { text: "\u65B0\u529F\u80FD" });
            for (let l of this._entry.new_features)
              c.createEl("p", {
                text: `\u2022 ${l}`,
                cls: "paperforge-modal-item",
              });
          }
          if (this._entry.fixes && this._entry.fixes.length > 0) {
            c.createEl("h4", { text: "\u4FEE\u590D" });
            for (let l of this._entry.fixes)
              c.createEl("p", {
                text: `\u2022 ${l}`,
                cls: "paperforge-modal-item",
              });
          }
          if (
            this._entry.recommended_actions &&
            this._entry.recommended_actions.length > 0
          ) {
            let l = c.createEl("div", {
              cls: "paperforge-release-recommended",
            });
            (l.createEl("h4", { text: "\u5EFA\u8BAE\u64CD\u4F5C", cls: "" }),
              (l.style.marginBottom = "8px"));
            for (let d of this._entry.recommended_actions)
              l.createEl("p", {
                text: `\u2022 ${d}`,
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
        new X.Setting(c).addButton((l) =>
          l
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
    (new n(this.app, a).open(),
      (this.settings.last_seen_version = e),
      this.saveSettings());
  }
};
