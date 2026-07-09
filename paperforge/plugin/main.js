"use strict";
var Et = Object.create;
var Be = Object.defineProperty;
var kt = Object.getOwnPropertyDescriptor;
var wt = Object.getOwnPropertyNames;
var St = Object.getPrototypeOf,
  Pt = Object.prototype.hasOwnProperty;
var Ct = (g, h) => () => (h || g((h = { exports: {} }).exports, h), h.exports),
  Ft = (g, h) => {
    for (var e in h) Be(g, e, { get: h[e], enumerable: !0 });
  },
  Ye = (g, h, e, t) => {
    if ((h && typeof h == "object") || typeof h == "function")
      for (let r of wt(h))
        !Pt.call(g, r) &&
          r !== e &&
          Be(g, r, {
            get: () => h[r],
            enumerable: !(t = kt(h, r)) || t.enumerable,
          });
    return g;
  };
var H = (g, h, e) => (
    (e = g != null ? Et(St(g)) : {}),
    Ye(
      h || !g || !g.__esModule
        ? Be(e, "default", { value: g, enumerable: !0 })
        : e,
      g
    )
  ),
  Rt = (g) => Ye(Be({}, "__esModule", { value: !0 }), g);
var Ke = Ct((Nt, Dt) => {
  Dt.exports = {
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
var Ot = {};
Ft(Ot, { default: () => $e });
module.exports = Rt(Ot);
var V = require("obsidian"),
  $ = H(require("fs")),
  xe = H(require("path")),
  ae = require("child_process");
var ge = "paperforge-status",
  Se = "paperforge",
  Qe =
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path><line x1="8" y1="7" x2="16" y2="7"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>',
  G = [
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
  Pe = {
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
function et(g, h) {
  if (!h || !h.note_path) return h;
  let e = g.vault.getAbstractFileByPath(h.note_path);
  if (!e) return h;
  let t = g.metadataCache.getFileCache(e),
    r = t && t.frontmatter;
  if (!r) return h;
  let n = { ...h };
  for (let a of [
    "do_ocr",
    "analyze",
    "ocr_status",
    "ocr_redo",
    "deep_reading_status",
  ])
    Object.prototype.hasOwnProperty.call(r, a) && (n[a] = r[a]);
  return n;
}
function je(g, h) {
  return g && { ...g, ...h };
}
var He = {
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
    },
  },
  Ve = null;
function Tt(g) {
  try {
    let h = g.vault;
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
function tt(g) {
  Ve = Tt(g) === "zh" ? He.zh : He.en;
}
function l(g) {
  return (Ve && Ve[g]) || He.en[g] || g;
}
var w = require("obsidian"),
  I = H(require("fs")),
  Z = H(require("path")),
  bt = H(require("os")),
  N = require("child_process");
var vt = H(Ke());
var re = H(require("fs")),
  te = H(require("path")),
  st = H(require("os")),
  oe = require("child_process"),
  Ze = null,
  rt = !1;
function M(g, h, e, t) {
  let r = e || re,
    n = t || oe.execFileSync;
  if (h && h.python_path && h.python_path.trim()) {
    let o = h.python_path.trim();
    if (r.existsSync(o)) return { path: o, source: "manual", extraArgs: [] };
  }
  let a = [
    te.join(g, ".paperforge-test-venv", "Scripts", "python.exe"),
    te.join(g, ".venv", "Scripts", "python.exe"),
    te.join(g, "venv", "Scripts", "python.exe"),
  ];
  for (let o of a)
    try {
      if (r.existsSync(o))
        return { path: o, source: "auto-detected", extraArgs: [] };
    } catch (i) {}
  let s = [
    { path: "py", extraArgs: ["-3"] },
    { path: "python", extraArgs: [] },
    { path: "python3", extraArgs: [] },
  ];
  for (let o of s)
    try {
      let i = n(o.path, [...o.extraArgs, "--version"], {
        encoding: "utf-8",
        timeout: 5e3,
        windowsHide: !0,
      });
      if (i && i.toLowerCase().includes("python"))
        return {
          path: o.path,
          source: "auto-detected",
          extraArgs: o.extraArgs,
        };
    } catch (i) {}
  return { path: "python", source: "auto-detected", extraArgs: [] };
}
function nt(g, h, e, t, r) {
  t === void 0 && (t = 1e4);
  let n = r || oe.execFile;
  return new Promise((a) => {
    n(
      g,
      ["-c", "import paperforge; print(paperforge.__version__)"],
      { cwd: e, timeout: t },
      (s, o) => {
        if (s) {
          a({
            status: "not-installed",
            pyVersion: null,
            pluginVersion: h,
            error: s.message,
          });
          return;
        }
        let i = (o && o.trim()) || null;
        a(
          i === h
            ? { status: "match", pyVersion: i, pluginVersion: h, error: null }
            : {
                status: "mismatch",
                pyVersion: i,
                pluginVersion: h,
                error: null,
              }
        );
      }
    );
  });
}
function at(g, h, e) {
  e === void 0 && (e = []);
  let t = `paperforge==${h}`,
    r = `git+https://github.com/LLLin000/PaperForge.git@${h}`,
    n = [...e, "-m", "pip", "install", "--upgrade", t],
    a = [...e, "-m", "pip", "install", "--upgrade", r];
  return { cmd: g, url: r, args: a, pypiArgs: n, gitArgs: a, timeout: 12e4 };
}
function it(g, h, e, t, r, n) {
  let a = r || oe.spawn;
  return new Promise((s) => {
    let o = Date.now(),
      i = { cwd: e, timeout: t, windowsHide: !0 };
    n && (i.env = n);
    let c = a(g, h, i),
      d = [],
      u = [];
    (c.stdout.on("data", (p) => {
      d.push(p.toString("utf-8"));
    }),
      c.stderr.on("data", (p) => {
        u.push(p.toString("utf-8"));
      }),
      c.on("close", (p) => {
        s({
          stdout: d.join(""),
          stderr: u.join(""),
          exitCode: p,
          elapsed: Date.now() - o,
        });
      }),
      c.on("error", (p) => {
        s({
          stdout: d.join(""),
          stderr:
            u.join("") +
            `
` +
            p.message,
          exitCode: -1,
          elapsed: Date.now() - o,
        });
      }));
  });
}
function We() {
  if (rt) return Ze;
  rt = !0;
  try {
    let g;
    if (process.platform === "win32") {
      let h = process.env.ComSpec || "C:\\Windows\\System32\\cmd.exe";
      g = (0, oe.execFileSync)(h, ["/c", "where", "git"], {
        timeout: 5e3,
        windowsHide: !0,
        encoding: "utf-8",
      });
    } else
      g = (0, oe.execFileSync)("which", ["git"], {
        timeout: 5e3,
        encoding: "utf-8",
      });
    if (g) {
      let h = g
        .split(
          `
`
        )[0]
        .trim();
      h && (Ze = te.dirname(h));
    }
  } catch (g) {}
  return Ze;
}
function fe() {
  let g = { ...process.env },
    h = process.platform,
    e = st.homedir(),
    t = [],
    r = We();
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
  let n = g.PATH || "";
  return ((g.PATH = [...t, n].filter(Boolean).join(te.delimiter)), g);
}
function ot(g) {
  return String(g)
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "")
    .includes("betterbibtex");
}
function qe(g) {
  if (!g) return !1;
  try {
    if (!re.existsSync(g)) return !1;
    for (let h of re.readdirSync(g)) if (ot(h)) return !0;
  } catch (h) {}
  return !1;
}
function Ae(g) {
  if (!g) return !1;
  try {
    if (!re.existsSync(g)) return !1;
    for (let h of re.readdirSync(g)) {
      let e = te.join(g, h, "extensions");
      try {
        if (!re.existsSync(e)) continue;
        for (let t of re.readdirSync(e)) if (ot(t)) return !0;
      } catch (t) {}
    }
  } catch (h) {}
  return !1;
}
var _e = H(require("fs")),
  K = H(require("path")),
  lt = require("child_process"),
  se = null;
function Bt(g, h) {
  let e = h || _e,
    t = K.join(g, "paperforge.json"),
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
      a = JSON.parse(n),
      s = a.vault_config || {};
    return {
      system_dir: s.system_dir || a.system_dir || r.system_dir,
      resources_dir: s.resources_dir || a.resources_dir || r.resources_dir,
      literature_dir: s.literature_dir || a.literature_dir || r.literature_dir,
      base_dir: s.base_dir || a.base_dir || r.base_dir,
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
function ne(g, h) {
  let e = Bt(g, h),
    t = K.join(g, e.system_dir, "PaperForge");
  return {
    vault: g,
    systemDir: t,
    indexesDir: K.join(t, "indexes"),
    logsDir: K.join(t, "logs"),
    dbPath: K.join(t, "indexes", "paperforge.db"),
    memoryStatePath: K.join(t, "indexes", "memory-runtime-state.json"),
    vectorStatePath: K.join(t, "indexes", "vector-runtime-state.json"),
    healthStatePath: K.join(t, "indexes", "runtime-health.json"),
    buildStatePath: K.join(t, "indexes", "vector-build-state.json"),
    orphanStatePath: K.join(t, "indexes", "sync-orphan-state.json"),
    exportsDir: K.join(t, "exports"),
    ocrDir: K.join(t, "ocr"),
    pluginDataPath: K.join(
      g,
      ".obsidian",
      "plugins",
      "paperforge",
      "data.json"
    ),
    pfJsonPath: K.join(g, "paperforge.json"),
    configWarning: e._warning,
  };
}
function Je(g) {
  try {
    return _e.existsSync(g) ? JSON.parse(_e.readFileSync(g, "utf-8")) : null;
  } catch (h) {
    return null;
  }
}
function At(g) {
  let h = ne(g);
  return Je(h.memoryStatePath);
}
function Ce(g) {
  let h = ne(g);
  return Je(h.vectorStatePath);
}
function Ue(g) {
  let h = ne(g);
  return Je(h.healthStatePath);
}
function ct(g) {
  var e;
  let h = Ue(g);
  return !!(h && ((e = h.summary) == null ? void 0 : e.status) === "ok");
}
function Oe(g) {
  let h = At(g);
  return !h || h.paper_count_db === 0
    ? "DB not found. Run paperforge memory build."
    : "Papers: " + h.paper_count_db + " | " + (h.fresh ? "fresh" : "stale");
}
function ye(g) {
  var t, r, n;
  let h = Ce(g);
  return h
    ? h.healthy === !1
      ? "Vector index unreadable - rebuild required"
      : "Chunks: " +
        (((t = h.chunk_count) != null ? t : 0) +
          ((r = h.body_chunk_count) != null ? r : 0) +
          ((n = h.object_chunk_count) != null ? n : 0)) +
        " | " +
        h.model +
        " | " +
        h.mode
    : "Status unavailable";
}
function le(g, h) {
  if (se) return se;
  if (h && h.python_path && h.python_path.trim()) {
    let r = h.python_path.trim();
    if (_e.existsSync(r))
      return ((se = { path: r, source: "manual", extraArgs: [] }), se);
  }
  let e = [
    K.join(g, ".paperforge-test-venv", "Scripts", "python.exe"),
    K.join(g, ".venv", "Scripts", "python.exe"),
    K.join(g, "venv", "Scripts", "python.exe"),
  ];
  for (let r = 0; r < e.length; r++)
    if (_e.existsSync(e[r]))
      return (
        (se = { path: e[r], source: "auto-detected", extraArgs: [] }),
        se
      );
  let t = [
    { path: "py", extraArgs: ["-3"] },
    { path: "python", extraArgs: [] },
    { path: "python3", extraArgs: [] },
  ];
  for (let r = 0; r < t.length; r++)
    try {
      let n = t[r],
        a = (0, lt.execFileSync)(n.path, n.extraArgs.concat(["--version"]), {
          encoding: "utf-8",
          timeout: 5e3,
          windowsHide: !0,
        });
      if (a && a.toLowerCase().indexOf("python") !== -1)
        return (
          (se = {
            path: n.path,
            source: "auto-detected",
            extraArgs: n.extraArgs,
          }),
          se
        );
    } catch (n) {}
  return (
    (se = { path: "python", source: "auto-detected", extraArgs: [] }),
    se
  );
}
function Ge(g, h, e) {
  return !g ||
    typeof g != "object" ||
    !Object.prototype.hasOwnProperty.call(g, h)
    ? !!e
    : !!g[h];
}
function pt(g, h, e) {
  let t = !Ge(g, h, e);
  return (g && typeof g == "object" && (g[h] = t), t);
}
var J = require("obsidian"),
  Q = H(require("fs")),
  ut = H(require("path")),
  ht = H(require("https")),
  Re = require("child_process");
function dt(g, h) {
  return !h || !h.trim()
    ? { blocked: !0, reason: "zotero" }
    : g
      ? { blocked: !1 }
      : { blocked: !0, reason: "ocr" };
}
var Xe = class extends J.Modal {
  constructor(e, t, r, n) {
    super(e);
    this._rowEls = [];
    ((this.orphans = t.map((a, s) => ({ ...a, _selected: !0, _idx: s }))),
      (this.vaultPath = r),
      (this.py = n));
  }
  _updateUI() {
    let e = this.orphans.filter((t) => t._selected);
    (this._countEl.setText(
      l("orphan_delete_selected").replace("{count}", String(e.length))
    ),
      this._selectAllBtn.setText(
        e.length === this.orphans.length
          ? l("orphan_deselect_all")
          : l("orphan_select_all")
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
        text: l("orphan_title").replace("{count}", String(this.orphans.length)),
      }),
      e.createEl("p", { cls: "paperforge-modal-desc", text: l("orphan_desc") }),
      (this._rowEls = []));
    let t = e.createEl("div", { cls: "paperforge-orphan-list" });
    for (let n of this.orphans) {
      let a = t.createEl("div", {
        cls:
          "paperforge-orphan-row" +
          (n._selected ? "" : " paperforge-orphan-dimmed"),
      });
      this._rowEls.push(a);
      let s = a.createEl("div", { cls: "paperforge-orphan-info" }),
        o = s.createEl("div", { cls: "paperforge-orphan-header" });
      o.createEl("span", {
        cls: "paperforge-orphan-key",
        text: n.citation_key || n.key,
      });
      let i = o.createEl("span", { cls: "paperforge-orphan-tags" });
      (i.createEl("span", {
        cls: "paperforge-tag " + (n.has_pdf ? "tag-pdf" : "tag-nopdf"),
        text: n.has_pdf ? "PDF" : "no PDF",
      }),
        n.collection_path &&
          i.createEl("span", {
            cls: "paperforge-tag tag-collection",
            text: n.collection_path,
          }),
        n.title &&
          s.createEl("div", { cls: "paperforge-orphan-title", text: n.title }));
      let c = [];
      (n.authors && c.push(n.authors),
        n.year && c.push(n.year),
        c.length > 0 &&
          s.createEl("div", {
            cls: "paperforge-orphan-meta",
            text: c.join(" \xB7 "),
          }),
        s.createEl("div", {
          cls: "paperforge-orphan-explain",
          text: l("orphan_explain"),
        }),
        a.addEventListener("click", () => {
          ((n._selected = !n._selected), this._updateUI());
        }));
    }
    let r = e.createEl("div", { cls: "paperforge-modal-actions" });
    ((this._selectAllBtn = r.createEl("button", {
      cls: "paperforge-step-btn",
      text: "Deselect all",
    })),
      this._selectAllBtn.addEventListener("click", () => {
        let n = this.orphans.every((a) => a._selected);
        for (let a of this.orphans) a._selected = !n;
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
        let n = this.orphans.filter((s) => s._selected);
        if (n.length === 0) {
          new J.Notice(l("orphan_none_selected"));
          return;
        }
        if (
          (this._countEl.setText("Deleting..."),
          this._countEl.setAttr("disabled", ""),
          this._selectAllBtn.setAttr("disabled", ""),
          !this.py || !this.py.path)
        ) {
          (new J.Notice("PaperForge: Python not found"), this.close());
          return;
        }
        let a = n.map((s) => s.key);
        (0, Re.execFile)(
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
          (s, o) => {
            if (s) {
              (new J.Notice("PaperForge: prune failed"), this.close());
              return;
            }
            try {
              let i = JSON.parse(o),
                c = (i.data && i.data.deleted) || [];
              new J.Notice("Deleted " + c.length + " orphan workspace(s)");
            } catch (i) {
              new J.Notice("PaperForge: prune done");
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
function Me(g, h, e) {
  console.log("[PF] checkOrphanState called");
  try {
    let r = ne(e).orphanStatePath;
    if (!Q.existsSync(r)) {
      console.log("[PF] orphan file NOT FOUND");
      return;
    }
    console.log("[PF] orphan file FOUND");
    let n = Q.readFileSync(r, "utf-8"),
      s = JSON.parse(n).orphans || [];
    if ((console.log("[PF] orphans count:", s.length), s.length === 0)) return;
    let o = le(e, h.settings);
    (console.log("[PF] py.path:", o ? o.path : "null"),
      new Xe(g, s, e, o).open(),
      Q.unlinkSync(r),
      console.log("[PF] orphan file cleaned"));
  } catch (t) {
    console.log("[PF] checkOrphanState exception:", t.message || t);
  }
}
var Fe = class extends J.Modal {
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
        l("wizard_step1"),
        l("wizard_step2"),
        l("wizard_step3"),
        l("wizard_step4"),
        l("wizard_step5"),
      ],
      t = this.contentEl.createEl("div", { cls: "paperforge-step-bar" });
    e.forEach((r, n) => {
      let a = n + 1,
        s = t.createEl("div", {
          cls: `paperforge-step-dot ${a === this._step ? "active" : ""} ${a < this._step ? "done" : ""}`,
        });
      (s.createEl("span", { cls: "paperforge-step-num", text: `${a}` }),
        s.createEl("span", { cls: "paperforge-step-label", text: r }));
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
        .createEl("button", { cls: "paperforge-step-btn", text: l("nav_prev") })
        .addEventListener("click", () => {
          (this._step--, (this._showSkipConfirm = !1), this._render());
        }),
      this._step < 5
        ? e
            .createEl("button", {
              cls: "paperforge-step-btn mod-cta",
              text: l("nav_next"),
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
              text: l("nav_close"),
            })
            .addEventListener("click", () => this.close()));
  }
  _validateStep3() {
    let e = this.plugin.settings,
      t = dt(this._apiKeyValidated, e.zotero_data_dir);
    if (t.reason === "ocr") return t;
    let r = (e.zotero_data_dir || "").trim();
    if (!r)
      return (
        new J.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u4E3A\u5FC5\u586B\u9879\uFF0C\u8BF7\u586B\u5199\u8DEF\u5F84"
        ),
        { blocked: !0, reason: "zotero" }
      );
    if (!Q.existsSync(r))
      return (
        new J.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u8DEF\u5F84\u4E0D\u5B58\u5728"
        ),
        { blocked: !0, reason: "zotero" }
      );
    if (!Q.statSync(r).isDirectory())
      return (
        new J.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u8DEF\u5F84\u4E0D\u662F\u4E00\u4E2A\u76EE\u5F55"
        ),
        { blocked: !0, reason: "zotero" }
      );
    let n = ut.join(r, "storage");
    return !Q.existsSync(n) || !Q.statSync(n).isDirectory()
      ? (new J.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u4E2D\u672A\u627E\u5230 storage/ \u5B50\u76EE\u5F55"
        ),
        { blocked: !0, reason: "zotero" })
      : { blocked: !1 };
  }
  _stepOverview(e) {
    (e.createEl("h2", { text: l("wizard_title") }),
      e.createEl("p", { text: l("wizard_intro") }));
    let t = this.plugin.settings,
      r = this.app.vault.adapter.basePath,
      n = e.createEl("div", { cls: "paperforge-dir-tree" }),
      a = n.createEl("div", { cls: "paperforge-dir-node root" });
    a.textContent = `\u{1F4C1} Vault (${r})`;
    let s = n.createEl("div", { cls: "paperforge-dir-children" }),
      o = s.createEl("div", { cls: "paperforge-dir-node folder" });
    ((o.textContent = `\u{1F4C1} ${t.resources_dir || "Resources"}/ \u2014 \u6587\u732E\u5361\u7247\u76EE\u5F55\uFF08Base \u6570\u636E\u6765\u6E90\uFF09`),
      o
        .createEl("div", { cls: "paperforge-dir-children" })
        .createEl("div", {
          cls: "paperforge-dir-node file",
          text: `\u{1F4C1} ${t.literature_dir || "Literature"}/ \u2014 \u6587\u732E\u5361\u7247`,
        }),
      s.createEl("div", {
        cls: "paperforge-dir-node folder",
        text: `\u{1F4C1} ${t.base_dir || "Bases"}/ \u2014 \u6570\u636E\u7BA1\u7406\u9762\u677F`,
      }),
      s.createEl("div", {
        cls: "paperforge-dir-node folder",
        text: `\u{1F4C1} ${t.system_dir || "System"}/ \u2014 Zotero \u8F6F\u94FE\u63A5 + PaperForge \u7CFB\u7EDF\u6587\u4EF6\u5939`,
      }),
      e.createEl("p", {
        text: l("wizard_preview"),
        cls: "paperforge-modal-hint",
      }),
      e.createEl("p", {
        text: l("wizard_safety"),
        cls: "paperforge-modal-hint",
      }));
    let c = e.createEl("div", { cls: "paperforge-summary" }),
      d = [
        {
          label: l("dir_resources"),
          val: `${r}/${t.resources_dir || "Resources"}`,
        },
        {
          label: l("dir_notes"),
          val: `${r}/${t.resources_dir || "Resources"}/${t.literature_dir || "Literature"}`,
        },
        { label: l("dir_base"), val: `${r}/${t.base_dir || "Bases"}` },
        { label: l("dir_system"), val: `${r}/${t.system_dir || "System"}` },
      ];
    for (let u of d) {
      let p = c.createEl("div", { cls: "paperforge-summary-row" });
      (p.createEl("span", { cls: "paperforge-summary-label", text: u.label }),
        p.createEl("span", { cls: "paperforge-summary-value", text: u.val }));
    }
  }
  _stepDirectories(e) {
    (e.createEl("h2", { text: l("wizard_step2") }),
      e.createEl("p", { text: l("wizard_intro") }));
    let t = this.plugin.settings,
      r = this.app.vault.adapter.basePath;
    (this._modalField(e, l("dir_vault"), r, !0),
      e.createEl("p", {
        text: l("wizard_dir_hint"),
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
        text: l("wizard_dir_sub_hint"),
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
        text: l("wizard_sys_hint"),
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
        text: l("wizard_safety"),
        cls: "paperforge-modal-hint",
      }));
    let n = e.createEl("div", { cls: "paperforge-summary" }),
      a = [
        { label: l("dir_resources"), val: `${r}/${t.resources_dir || ""}` },
        {
          label: l("dir_notes"),
          val: `${r}/${t.resources_dir || ""}/${t.literature_dir || ""}`,
        },
        { label: l("dir_system"), val: `${r}/${t.system_dir || ""}` },
        { label: l("dir_base"), val: `${r}/${t.base_dir || ""}` },
      ];
    for (let s of a) {
      let o = n.createEl("div", { cls: "paperforge-summary-row" });
      (o.createEl("span", { cls: "paperforge-summary-label", text: s.label }),
        o.createEl("span", { cls: "paperforge-summary-value", text: s.val }));
    }
  }
  _stepKeys(e) {
    if (
      (e.createEl("h2", { text: l("wizard_step3") }), this._showSkipConfirm)
    ) {
      this._renderSkipConfirm(e);
      return;
    }
    let t = this.plugin.settings;
    e.createEl("p", {
      text: l("wizard_agent_hint"),
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
      text: l("label_agent"),
    });
    let a = n.createEl("select", { cls: "paperforge-modal-select" });
    for (let u of r) {
      let p = a.createEl("option", { text: u.name, attr: { value: u.key } });
      u.key === (t.agent_platform || "opencode") && (p.selected = !0);
    }
    (a.addEventListener("change", () => {
      ((t.agent_platform = a.value),
        this._pendingSave && clearTimeout(this._pendingSave),
        (this._pendingSave = setTimeout(() => {
          (this.plugin.saveSettings(), (this._pendingSave = null));
        }, 500)));
    }),
      e.createEl("p", {
        text: l("wizard_keys_hint"),
        cls: "paperforge-modal-hint",
      }));
    let s = e.createEl("div", { cls: "paperforge-modal-field" });
    s.createEl("label", {
      cls: "paperforge-modal-label",
      text: l("field_paddleocr"),
    });
    let o = s.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "password", placeholder: "API Key" },
    });
    ((o.value = t.paddleocr_api_key || ""),
      (this._apiKeyValidated = !1),
      (this._apiKeyStatus = s.createEl("span", {
        cls: "paperforge-apikey-status",
        text: "",
      })));
    let i = s.createEl("button", {
      cls: "paperforge-step-btn",
      text: "\u9A8C\u8BC1",
    });
    (i.addEventListener("click", () => this._validateApiKey(o.value, i)),
      o.addEventListener("input", () => {
        ((t.paddleocr_api_key = o.value),
          (this._apiKeyValidated = !1),
          (this._apiKeyStatus.textContent = ""),
          (this._apiKeyStatus.className = "paperforge-apikey-status"));
      }),
      this._pendingSave && clearTimeout(this._pendingSave),
      (this._pendingSave = setTimeout(() => {
        (this.plugin.saveSettings(), (this._pendingSave = null));
      }, 500)),
      e.createEl("p", {
        text: l("wizard_api_hint_skip"),
        cls: "paperforge-modal-hint",
      }));
    let c = e.createEl("div", { cls: "paperforge-modal-field" });
    c.createEl("label", {
      cls: "paperforge-modal-label",
      text: l("field_zotero_data"),
    });
    let d = c.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text", placeholder: l("field_zotero_placeholder") },
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
      a = ht.request(n, (s) => {
        ((t.disabled = !1), (t.textContent = "\u9A8C\u8BC1"));
        let o = "";
        (s.on("data", (i) => (o += i)),
          s.on("end", () => {
            try {
              let i = JSON.parse(o);
              s.statusCode === 400 && i.code === 10001
                ? ((this._apiKeyStatus.textContent =
                    "\u2713 \u5BC6\u94A5\u6709\u6548"),
                  (this._apiKeyStatus.className =
                    "paperforge-apikey-status ok"),
                  (this._apiKeyValidated = !0))
                : s.statusCode === 401
                  ? ((this._apiKeyStatus.textContent =
                      "\u9A8C\u8BC1\u5931\u8D25\uFF1A\u5BC6\u94A5\u65E0\u6548\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
                    (this._apiKeyStatus.className =
                      "paperforge-apikey-status error"),
                    (this._apiKeyValidated = !1))
                  : ((this._apiKeyStatus.textContent =
                      "\u9A8C\u8BC1\u5931\u8D25\uFF1AAPI \u8FD4\u56DE " +
                      s.statusCode +
                      "\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
                    (this._apiKeyStatus.className =
                      "paperforge-apikey-status error"),
                    (this._apiKeyValidated = !1));
            } catch (i) {
              ((this._apiKeyStatus.textContent =
                "\u9A8C\u8BC1\u5931\u8D25\uFF1A\u65E0\u6CD5\u89E3\u6790\u54CD\u5E94\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
                (this._apiKeyStatus.className =
                  "paperforge-apikey-status error"),
                (this._apiKeyValidated = !1));
            }
          }));
      });
    (a.on("error", (s) => {
      ((t.disabled = !1),
        (t.textContent = "\u9A8C\u8BC1"),
        (this._apiKeyStatus.textContent =
          "\u9A8C\u8BC1\u5931\u8D25\uFF1A\u65E0\u6CD5\u8FDE\u63A5 (" +
          s.message +
          ")\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
        (this._apiKeyStatus.className = "paperforge-apikey-status error"),
        (this._apiKeyValidated = !1));
    }),
      a.write(r),
      a.end());
  }
  _renderSkipConfirm(e) {
    e.createEl("p", {
      text: l("wizard_skip_ocr_desc"),
      cls: "paperforge-modal-desc",
    });
    let t = e.createEl("div", { cls: "paperforge-modal-actions" });
    (t
      .createEl("button", {
        cls: "paperforge-step-btn mod-cta",
        text: l("wizard_skip_ocr_continue"),
      })
      .addEventListener("click", () => {
        ((this._showSkipConfirm = !1), this._step++, this._render());
      }),
      t
        .createEl("button", {
          cls: "paperforge-step-btn",
          text: l("wizard_skip_ocr_back"),
        })
        .addEventListener("click", () => {
          ((this._showSkipConfirm = !1), this._render());
        }));
  }
  _modalField(e, t, r, n) {
    let a = e.createEl("div", { cls: "paperforge-modal-field" });
    a.createEl("label", { cls: "paperforge-modal-label", text: t });
    let s = a.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text" },
    });
    ((s.value = r), (s.disabled = !!n));
  }
  _modalInput(e, t, r, n, a) {
    let s = e.createEl("div", { cls: "paperforge-modal-field" });
    s.createEl("label", { cls: "paperforge-modal-label", text: t });
    let o = s.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text", placeholder: a || "" },
    });
    o.value = n;
    let i = this.plugin.settings;
    o.addEventListener("input", () => {
      ((i[r] = o.value),
        this._pendingSave && clearTimeout(this._pendingSave),
        (this._pendingSave = setTimeout(() => {
          (this.plugin.saveSettings(), (this._pendingSave = null));
        }, 500)));
    });
  }
  _modalSecret(e, t, r, n, a) {
    let s = e.createEl("div", { cls: "paperforge-modal-field" });
    s.createEl("label", { cls: "paperforge-modal-label", text: t });
    let o = s.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "password", placeholder: a || "" },
    });
    o.value = n;
    let i = this.plugin.settings;
    o.addEventListener("input", () => {
      ((i[r] = o.value),
        this._pendingSave && clearTimeout(this._pendingSave),
        (this._pendingSave = setTimeout(() => {
          (this.plugin.saveSettings(), (this._pendingSave = null));
        }, 500)));
    });
  }
  _stepInstall(e) {
    (e.createEl("h2", { text: l("wizard_step4") }),
      (this._installLog = e.createEl("div", {
        cls: "paperforge-install-log",
      })));
    let t = e.createEl("button", {
      cls: "paperforge-step-btn mod-cta",
      text: l("install_btn"),
    });
    t.addEventListener("click", () => this._runInstall(t));
  }
  async _runInstall(e) {
    var s, o, i, c, d, u;
    ((e.disabled = !0),
      (e.textContent = l("install_btn_running")),
      this._installLog.setText(
        l("install_validating") +
          `
`
      ),
      this._log(l("install_validating")));
    let t = this.plugin.settings,
      r = this._validate();
    if (r.length > 0) {
      (this._log(l("validate_fail") + ":"),
        r.forEach((p) => this._log("  \u2717 " + p)),
        (e.disabled = !1),
        (e.textContent = l("install_btn_retry")));
      return;
    }
    let n = (p, _ = {}) =>
        new Promise((m, E) => {
          let { path: f, extraArgs: v = [] } = M(
              t.vault_path.trim(),
              this.plugin.settings,
              void 0,
              void 0
            ),
            S = (0, Re.spawn)(f, [...v, ...p], {
              cwd: t.vault_path.trim(),
              env: fe(),
              timeout: 12e4,
              ..._,
            }),
            x = "",
            y = "";
          (S.stdout.on("data", (b) => {
            let k = b.toString("utf-8");
            ((x += k), _.logStdout && this._processSetupOutput(k));
          }),
            S.stderr.on("data", (b) => {
              let k = b.toString("utf-8");
              ((y += k), this._log("[stderr] " + k.trim()));
            }),
            S.on("close", (b) => {
              b === 0
                ? m({ stdout: x, stderr: y })
                : E(new Error(y.trim() || x.trim() || `exit code ${b}`));
            }),
            S.on("error", (b) => E(b)));
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
        await n(["-c", "import paperforge"]);
      } catch (_) {
        p = !1;
      }
      if (!p) {
        this._log(l("install_bootstrapping"));
        let _ = this.plugin.manifest.version;
        this._log(`[install] Trying PyPI: pip install paperforge==${_}`);
        let m = ["-m", "pip", "install", "--upgrade"];
        (process.platform !== "win32" && m.push("--user"),
          m.push(`paperforge==${_}`));
        try {
          await n(m, { logStdout: !0 });
        } catch (E) {
          (this._log(
            `[install] PyPI failed, falling back to git: git+https://...@v${_}`
          ),
            console.warn(
              "[PaperForge] PyPI install failed, falling back to git:",
              (s = E.message) == null ? void 0 : s.slice(0, 200)
            ));
          let f = ["-m", "pip", "install", "--upgrade"];
          (process.platform !== "win32" && f.push("--user"),
            f.push(`git+https://github.com/LLLin000/PaperForge.git@v${_}`),
            await n(f, { logStdout: !0 }));
        }
      }
      (await n(a, { logStdout: !0, env: fe() }),
        this._log(l("install_complete")),
        (t.setup_complete = !0),
        await this.plugin.saveSettings(),
        setTimeout(() => {
          ((this._step = 5), this._render());
        }, 800));
    } catch (p) {
      console.error("PaperForge setup failed:", p.message);
      let _ = this._formatSetupError(p.message);
      this._log(l("install_failed") + _);
      let m =
        (o = this._installLog.parentElement) == null
          ? void 0
          : o.createEl("button", {
              cls: "paperforge-copy-diag-btn",
              text: l("error_copy_diagnostic") || "Copy diagnostic",
            });
      if (m) {
        let E = p.message,
          f =
            ((c = (i = this.plugin) == null ? void 0 : i.settings) == null
              ? void 0
              : c.python_path) || "auto",
          v =
            ((u = (d = this.plugin) == null ? void 0 : d.manifest) == null
              ? void 0
              : u.version) || "?",
          S = process.platform + " " + process.arch,
          x,
          y;
        try {
          x = We() || "(not found)";
        } catch (T) {
          x = "(error)";
        }
        try {
          y = M(t.vault_path.trim(), this.plugin.settings, void 0, void 0);
        } catch (T) {
          y = null;
        }
        let b = (process.env.PATH || "").length,
          k = (process.env.PATH || "").toLowerCase().includes("git"),
          C = [
            "[PaperForge Diagnostic]",
            "Category: " + _,
            "Plugin version: " + v,
            "Python: " + f,
            "Resolved Python: " + ((y == null ? void 0 : y.path) || "?"),
            "OS: " + S,
            "Vault path: " + (t.vault_path || "?"),
            "--- Git ---",
            "Git dir (resolved): " + x,
            "PATH length: " + b + " chars",
            "PATH contains git: " + k,
            "--- Raw error ---",
            E.slice(0, 2e3),
          ].join(`
`);
        m.addEventListener("click", () => {
          navigator.clipboard
            .writeText(C)
            .then(() => {
              (m.setText(l("error_copied") || "Copied!"),
                setTimeout(() => {
                  m.setText(l("error_copy_diagnostic") || "Copy diagnostic");
                }, 3e3));
            })
            .catch(() => {
              new J.Notice("[!!] Clipboard write failed", 6e3);
            });
        });
      }
      ((e.disabled = !1), (e.textContent = l("install_btn_retry")));
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
      (!t.vault_path || !t.vault_path.trim()) && e.push(l("validate_vault")),
      (!t.resources_dir || !t.resources_dir.trim()) &&
        e.push(l("validate_resources")),
      (!t.literature_dir || !t.literature_dir.trim()) &&
        e.push(l("validate_notes")),
      (!t.base_dir || !t.base_dir.trim()) && e.push(l("validate_base")),
      (!t.paddleocr_api_key || !t.paddleocr_api_key.trim()) &&
        this._log("  ! " + l("validate_key") + " " + l("optional_later")),
      (!t.zotero_data_dir || !t.zotero_data_dir.trim()) &&
        this._log("  ! " + l("validate_zotero") + " " + l("optional_later")),
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
    e.createEl("h2", { text: l("complete_title") });
    let t = e.createEl("div", { cls: "paperforge-summary" });
    t.createEl("div", {
      cls: "paperforge-summary-title",
      text: l("complete_summary"),
    });
    let r = this.plugin.settings,
      n = this.app.vault.adapter.basePath,
      a = [
        { label: l("dir_vault"), val: n },
        { label: l("dir_resources"), val: `${n}/${r.resources_dir}` },
        {
          label: l("dir_notes"),
          val: `${n}/${r.resources_dir}/${r.literature_dir}`,
        },
        { label: l("dir_base"), val: `${n}/${r.base_dir}` },
        { label: l("dir_system"), val: `${n}/${r.system_dir}` },
        {
          label: "API Key",
          val: r.paddleocr_api_key ? l("api_key_set") : l("api_key_missing"),
        },
        {
          label: l("field_zotero_data"),
          val: r.zotero_data_dir || l("not_set"),
        },
      ];
    for (let d of a) {
      let u = t.createEl("div", { cls: "paperforge-summary-row" });
      (u.createEl("span", { cls: "paperforge-summary-label", text: d.label }),
        u.createEl("span", { cls: "paperforge-summary-value", text: d.val }));
    }
    let s = t.createEl("div", { cls: "paperforge-summary-row" });
    s.createEl("span", { cls: "paperforge-summary-label", text: "PaperForge" });
    let o = s.createEl("span", {
      cls: "paperforge-summary-value",
      text: "\u2014",
    });
    {
      let d = n,
        { path: u, extraArgs: p = [] } = M(
          d,
          this.plugin.settings,
          void 0,
          void 0
        );
      (0, Re.execFile)(
        u,
        [...p, "-c", "import paperforge; print(paperforge.__version__)"],
        { cwd: d, timeout: 1e4 },
        (_, m) => {
          !_ && m && (o.textContent = "v" + m.trim());
        }
      );
    }
    for (let d of a) {
      let u = t.createEl("div", { cls: "paperforge-summary-row" });
      (u.createEl("span", { cls: "paperforge-summary-label", text: d.label }),
        u.createEl("span", { cls: "paperforge-summary-value", text: d.val }));
    }
    e.createEl("h3", { text: l("complete_next") });
    let i = e.createEl("div", { cls: "paperforge-nextsteps" }),
      c = [
        [l("complete_step4"), l("complete_step4_desc")],
        [
          "",
          `${l("complete_export_path")} ${n}/${r.system_dir}/PaperForge/exports/`,
        ],
        [l("complete_step1"), l("complete_step1_desc")],
        [l("complete_step2"), l("complete_step2_desc")],
        [l("complete_step3"), l("complete_step3_desc")],
      ];
    for (let [d, u] of c) {
      let p = i.createEl("div", { cls: "paperforge-nextstep-item" });
      (d && p.createEl("strong", { text: d }), p.createEl("span", { text: u }));
    }
  }
};
var be = H(require("fs")),
  Le = H(require("path")),
  ft = require("child_process");
function _t(g) {
  return Le.join(g, "System", "PaperForge", "cache", "ocr_maintenance.json");
}
function mt(g) {
  try {
    let h = _t(g),
      e = be.readFileSync(h, "utf-8");
    return JSON.parse(e);
  } catch (h) {
    return null;
  }
}
function Ie(g, h) {
  let e = _t(g),
    t = Le.dirname(e);
  (be.mkdirSync(t, { recursive: !0 }),
    be.writeFileSync(e, JSON.stringify(h, null, 2), "utf-8"));
}
function gt(g, h, e) {
  return new Promise((t, r) => {
    (0, ft.execFile)(g, h, e, (n, a) => {
      n ? r(n) : t(a);
    });
  });
}
async function yt(g, h, e, t) {
  let r = await gt(h, [...e, "-m", "paperforge", "ocr", "list", "--manifest"], {
      cwd: g,
      timeout: 3e4,
    }),
    n = JSON.parse(r);
  if (t) {
    let d = Object.keys(t.manifest),
      u = Object.keys(n);
    if (d.length === u.length && d.every((_) => t.manifest[_] === n[_]))
      return {
        data: Object.values(t.papers).filter((m) => m.visible_in_maintenance),
        changed: !1,
      };
  }
  let a = Object.keys(n).filter(
      (d) => !(t != null && t.manifest[d]) || t.manifest[d] !== n[d]
    ),
    s = await gt(
      h,
      [...e, "-m", "paperforge", "ocr", "list", "--json", "--keys", ...a],
      { cwd: g, timeout: 3e4 }
    ),
    o = JSON.parse(s),
    i = { manifest: n, papers: {}, cached_at: new Date().toISOString() };
  if (t != null && t.papers)
    for (let d of Object.keys(n)) t.papers[d] && (i.papers[d] = t.papers[d]);
  for (let d of o) i.papers[d.key] = d;
  return (
    Ie(g, i),
    {
      data: Object.values(i.papers).filter((d) => d.visible_in_maintenance),
      changed: !0,
    }
  );
}
var Ne = class extends w.PluginSettingTab {
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
        { id: "setup", label: l("tab_setup") || "\u5B89\u88C5" },
        { id: "features", label: l("tab_features") || "\u529F\u80FD" },
        { id: "maintenance", label: l("tab_maintenance") || "\u7EF4\u62A4" },
        { id: "release-notes", label: "\u66F4\u65B0\u4E0E\u624B\u518C" },
      ],
      n = {};
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
        n[a.id] = e.createDiv({
          cls:
            "paperforge-tab-content" +
            (a.id === this.activeTab ? " paperforge-tab-content--active" : ""),
        });
      }),
      this.activeTab === "setup"
        ? this._renderSetupTab(n.setup)
        : this.activeTab === "features"
          ? this._renderFeaturesTab(n.features)
          : this.activeTab === "maintenance"
            ? this._renderMaintenanceTab(n.maintenance)
            : this._renderReleaseNotesTab(n["release-notes"]));
  }
  _renderSetupTab(e) {
    let t = this.app.vault.adapter.basePath;
    (this.plugin.settings.vault_path ||
      ((this.plugin.settings.vault_path = t), this._debouncedSave()),
      this.plugin.settings.setup_complete &&
        (I.existsSync(Z.join(t, "paperforge.json")) ||
          ((this.plugin.settings.setup_complete = !1), this._debouncedSave())),
      e.createEl("h2", { text: l("header_title") || "PaperForge" }),
      e.createEl("p", { text: l("desc"), cls: "paperforge-settings-desc" }));
    let n = e
      .createEl("div", { cls: "paperforge-setup-bar" })
      .createEl("span", { cls: "paperforge-setup-label" });
    this.plugin.settings.setup_complete
      ? (n.setText(l("setup_done")), n.addClass("paperforge-setup-done"))
      : (n.setText(l("setup_pending")), n.addClass("paperforge-setup-pending"));
    let a = this.app.vault.adapter.basePath,
      s = M(a, this.plugin.settings, void 0, void 0),
      o = s.path,
      i = this.plugin.settings._python_path_stale ? "stale" : s.source,
      c = new w.Setting(e)
        .setName(l("field_python_interp"))
        .setDesc(this._getPythonDesc(o, i));
    this._pythonInterpDescEl = c.descEl;
    let d = new w.Setting(e).setName(l("field_python_custom")).setDesc("");
    ((this._customPathDescEl = d.descEl),
      d.addText((x) => {
        x.setPlaceholder("e.g. C:\\Python310\\python.exe")
          .setValue(this.plugin.settings.python_path || "")
          .onChange((y) => {
            if (
              ((this.plugin.settings.python_path = y),
              this.plugin.saveSettings(),
              y && y.trim())
            ) {
              let C = I.existsSync(y.trim());
              this.plugin.settings._python_path_stale = !C;
            } else this.plugin.settings._python_path_stale = !1;
            let b = M(
                this.app.vault.adapter.basePath,
                this.plugin.settings,
                void 0,
                void 0
              ),
              k = this.plugin.settings._python_path_stale ? "stale" : b.source;
            this._pythonInterpDescEl &&
              (this._pythonInterpDescEl.textContent = this._getPythonDesc(
                b.path,
                k
              ));
          });
      }),
      d.addButton((x) => {
        x.setButtonText(l("btn_validate")).onClick(() =>
          this._validatePythonOverride()
        );
      }),
      e.createEl("h3", { text: l("runtime_health") }),
      e.createEl("p", {
        text: l("runtime_health_desc"),
        cls: "paperforge-settings-desc",
      }));
    let u = new w.Setting(e)
        .setName("PaperForge")
        .setDesc(l("runtime_health_checking")),
      p = u.descEl.createEl("span", { cls: "paperforge-runtime-badge" }),
      _ = null;
    u.addButton((x) => {
      ((_ = x),
        x
          .setButtonText(l("runtime_health_sync"))
          .setDisabled(!0)
          .onClick(() => this._syncRuntime(x)));
    });
    {
      let x = this.app.vault.adapter.basePath,
        { path: y, extraArgs: b = [] } = M(
          x,
          this.plugin.settings,
          void 0,
          void 0
        ),
        k = this.plugin.manifest.version || "?";
      (0, N.execFile)(
        y,
        [...b, "-c", "import paperforge; print(paperforge.__version__)"],
        { cwd: x, timeout: 1e4 },
        (C, T) => {
          let O = this.plugin.settings.setup_complete,
            D = !C && T ? T.trim() : null,
            z = D
              ? `${l("runtime_health_plugin_ver").replace("{0}", k)} \u2192 ${l("runtime_health_package_ver").replace("{0}", D)}`
              : O
                ? `Plugin v${k} \u2192 Python package not installed. Click "Sync Runtime" to install.`
                : `Plugin v${k} \u2192 Not configured. Please open the setup wizard first.`;
          (u.setDesc(z),
            D === k
              ? (p.setText(l("runtime_health_match")),
                (p.className = "paperforge-runtime-badge match"),
                _ && _.setDisabled(!0))
              : D
                ? (p.setText(l("runtime_health_mismatch")),
                  (p.className = "paperforge-runtime-badge mismatch"),
                  _ && _.setDisabled(!1))
                : (p.setText(O ? "Not installed" : "Setup needed"),
                  (p.className = "paperforge-runtime-badge missing"),
                  _ && _.setDisabled(!1)));
        }
      );
    }
    (e.createEl("h3", { text: l("section_prep") }),
      e.createEl("p", {
        text: l("section_prep_desc"),
        cls: "paperforge-settings-desc",
      }));
    let m = e.createEl("div", { cls: "paperforge-guide" }),
      E = [
        ["prep_python", "prep_python_desc"],
        ["prep_zotero", "prep_zotero_desc"],
        ["prep_bbt", "prep_bbt_desc"],
        ["prep_key", "prep_key_desc"],
      ];
    for (let [x, y] of E) {
      let b = m.createEl("div", { cls: "paperforge-guide-item" });
      (b.createEl("strong", { text: l(x) }),
        b.createEl("span", { text: " \u2014 " + l(y) }));
    }
    this._checkEl = e.createEl("div", { cls: "paperforge-message" });
    let f = !this.plugin.settings.setup_complete;
    (new w.Setting(e)
      .setName(l(f ? "btn_install" : "btn_reconfig"))
      .setDesc(l(f ? "btn_install_desc" : "btn_reconfig_desc"))
      .addButton((x) => {
        x.setButtonText(l(f ? "btn_install" : "btn_reconfig"))
          .setCta()
          .onClick(() => {
            f
              ? this._preCheck(() => {
                  new Fe(this.app, this.plugin).open();
                })
              : new Fe(this.app, this.plugin).open();
          });
      }),
      e.createEl("h3", { text: l("section_guide") }));
    let v = e.createEl("div", { cls: "paperforge-guide" }),
      S = [
        ["guide_open", "guide_open_desc"],
        ["guide_sync", "guide_sync_desc"],
        ["guide_ocr", "guide_ocr_desc"],
      ];
    for (let [x, y] of S) {
      let b = v.createEl("div", { cls: "paperforge-guide-item" });
      (b.createEl("strong", { text: l(x) }),
        b.createEl("span", { text: " \u2014 " + l(y) }));
    }
    if (this.plugin.settings.setup_complete) {
      e.createEl("h3", { text: l("section_config") });
      let x = e.createEl("div", { cls: "paperforge-summary" }),
        y = this.plugin.settings,
        b = this._pfConfig,
        k = [
          { label: l("dir_vault"), val: t },
          {
            label: l("dir_resources"),
            val: `${t}/${b == null ? void 0 : b.resources_dir}`,
          },
          {
            label: "  " + l("dir_notes"),
            val: `${t}/${b == null ? void 0 : b.resources_dir}/${b == null ? void 0 : b.literature_dir}`,
          },
          {
            label: l("dir_base"),
            val: `${t}/${b == null ? void 0 : b.base_dir}`,
          },
          {
            label: l("dir_system"),
            val: `${t}/${b == null ? void 0 : b.system_dir}`,
          },
          {
            label: "API Key",
            val: y.paddleocr_api_key ? l("api_key_set") : l("api_key_missing"),
          },
          {
            label: l("field_zotero_data"),
            val: y.zotero_data_dir || l("not_set"),
          },
        ];
      for (let C of k) {
        let T = x.createEl("div", { cls: "paperforge-summary-row" });
        (T.createEl("span", { cls: "paperforge-summary-label", text: C.label }),
          T.createEl("span", { cls: "paperforge-summary-value", text: C.val }));
      }
    }
  }
  _execMemoryStatus(e, t, r) {
    (0, N.exec)(
      `"${e}" -m paperforge --vault "${t}" memory status --json`,
      { encoding: "utf-8", timeout: 15e3 },
      (n, a) => {
        if (n) {
          r("Status unavailable");
          return;
        }
        try {
          let s = JSON.parse(a);
          if (s.ok) {
            let o = s.data,
              i = o.fresh ? "fresh" : "stale";
            r(
              `Papers: ${o.paper_count_db} | ${i}${o.needs_rebuild ? " - needs rebuild" : ""}`
            );
          } else r("DB not found. Run paperforge memory build.");
        } catch (s) {
          r("Could not parse status.");
        }
      }
    );
  }
  _execEmbedStatus(e, t, r) {
    (0, N.exec)(
      `"${e}" -m paperforge --vault "${t}" embed status --json`,
      { encoding: "utf-8", timeout: 15e3 },
      (n, a) => {
        if (n) {
          r("Status unavailable");
          return;
        }
        try {
          let s = JSON.parse(a);
          s.ok
            ? r(
                `Chunks: ${s.data.chunk_count} | ${s.data.model} | ${s.data.mode}`
              )
            : r("Could not parse status.");
        } catch (s) {
          r("Could not parse status.");
        }
      }
    );
  }
  _callPython(e, t) {
    let r = this.app.vault.adapter.basePath,
      n = le(r, this.plugin.settings),
      a = [...n.extraArgs, "-m", "paperforge", "--vault", r, ...e];
    if (t && t.stream) {
      let s = (0, N.spawn)(n.path, a, {
        cwd: r,
        env: t.env || process.env,
        windowsHide: !0,
      });
      return (
        t.onData && s.stdout.on("data", t.onData),
        t.onStderr && s.stderr.on("data", t.onStderr),
        t.onError && s.on("error", t.onError),
        s.on("close", t.onClose),
        s
      );
    }
    return (
      (0, N.execFile)(
        n.path,
        a,
        { cwd: r, timeout: (t && t.timeout) || 6e4 },
        (s, o, i) => {
          t && t.onClose && t.onClose(s ? 1 : 0, o, i);
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
    let n = e.createEl("button", {
      cls: "paperforge-rebuild-btn",
      text: l("feat_memory_rebuild_btn"),
    });
    ((n.title = "Rebuild memory database"),
      (n.onclick = () => {
        let s = this.app.vault.adapter.basePath,
          o = le(s, this.plugin.settings);
        if (!o.path) {
          new w.Notice(l("feat_no_python"));
          return;
        }
        (console.log("[PaperForge] Rebuilding memory:", o.path),
          n.setText(l("feat_memory_rebuilding")),
          n.setAttr("disabled", ""),
          this._callPython(["memory", "build"], {
            timeout: 6e4,
            onClose: (i, c, d) => {
              (console.log(
                "[PaperForge] memory build exit:",
                i ? "FAIL:" + i : "OK",
                (c || "").slice(0, 200),
                (d || "").slice(0, 200)
              ),
                n.setText(l("feat_memory_rebuild_btn")),
                n.removeAttribute("disabled"),
                i === 0
                  ? new w.Notice(l("feat_memory_rebuild_done"))
                  : new w.Notice(
                      l("feat_memory_rebuild_failed") +
                        (d ? " " + d.slice(0, 80) : "")
                    ),
                (this._memoryStatusText = Oe(s)),
                this._refreshSnapshots(s));
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
      r = M(t, e, void 0, void 0);
    return r.path ? `"${r.path}" -m paperforge --vault "${t}" sync` : null;
  }
  _runManualSync() {
    let e = this.app.vault.adapter.basePath;
    if (!le(e, this.plugin.settings).path) return;
    let r = document.querySelector(".paperforge-memory-status");
    (r && this._renderMemoryStatusText(r, "Checking...", "syncing"),
      (this.plugin._autoSyncRunning = !0),
      this._callPython(["sync"], {
        timeout: 12e4,
        onClose: (n) => {
          ((this.plugin._autoSyncRunning = !1),
            (this._memoryStatusText = null),
            n === 0 &&
              ((this._lastSyncTime = new Date().toLocaleTimeString()),
              (this.plugin._lastSyncTime = this._lastSyncTime)),
            this.display(),
            this._refreshSnapshots(e),
            Me(this.app, this.plugin, e));
        },
      }));
  }
  _refreshSnapshots(e) {
    let t = le(e, this.plugin.settings),
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
      (0, N.execFile)(
        t.path,
        r,
        { cwd: e, timeout: 3e4, windowsHide: !0 },
        (n, a, s) => {
          ((this._refreshPending = !1),
            (this._memoryStatusText = Oe(e)),
            (this._embedStatusText = ye(e)),
            this.display());
        }
      ));
  }
  _renderFeaturesTab(e) {
    e.createEl("h3", { text: "Skills" });
    let t = e.createEl("div", { cls: "paperforge-desc-box" });
    (t.setText(l("feat_skills_desc")),
      t.createEl("br"),
      t.createEl("span", { text: l("feat_skills_system") }));
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
      a = this.app.vault.adapter.basePath,
      s = this.plugin.settings.selected_skill_platform || "opencode";
    new w.Setting(e)
      .setName(l("feat_agent_platform"))
      .setDesc(l("feat_agent_platform_desc"))
      .addDropdown((y) => {
        (Object.entries(r).forEach(([b, k]) => y.addOption(b, k)),
          y.setValue(s).onChange((b) => {
            ((this.plugin.settings.selected_skill_platform = b),
              this.plugin.saveSettings(),
              this.display());
          }));
      })
      .addExtraButton((y) => {
        y.setIcon("folder")
          .setTooltip("Open skills folder")
          .onClick(() => {
            let b = n[s] || ".opencode/skills",
              k = Z.join(a, b);
            I.existsSync(k)
              ? (0, N.exec)(`start "" "${k}"`)
              : new w.Notice(`Skills folder not found: ${b}`);
          });
      });
    let o = Z.join(a, n[s]),
      i = [],
      c = [];
    I.existsSync(o) &&
      I.readdirSync(o, { withFileTypes: !0 }).forEach((y) => {
        if (!y.isDirectory()) return;
        let b = Z.join(o, y.name, "SKILL.md");
        if (!I.existsSync(b)) return;
        let k = I.readFileSync(b, "utf-8"),
          C = k.match(/^name:\s*(.+)$/m),
          T = k.split(`
`),
          O = T.findIndex((W) => /^description:/.test(W)),
          D = "";
        if (O >= 0) {
          let W = T[O].match(/^description:\s*(.+)$/);
          if (W && W[1] && W[1] !== ">" && W[1] !== "|-" && W[1] !== "|")
            D = W[1].trim();
          else {
            for (
              let P = O + 1;
              P < T.length && (/^\s{2,}/.test(T[P]) || T[P].trim() === "");
              P++
            )
              D += T[P].trim() + " ";
            D = D.trim();
          }
        }
        let z = k.match(/^source:\s*(.+)$/m),
          j = k.match(/^disable-model-invocation:\s*(.+)$/m),
          B = k.match(/^version:\s*(.+)$/m),
          X = {
            name: C ? C[1].trim() : y.name,
            desc: D,
            source: z ? z[1].trim() : "user",
            disabled: j && j[1].trim() === "true",
            version: B ? B[1].trim() : "",
            path: b,
            content: k,
            dirName: y.name,
          };
        X.source === "paperforge" ? i.push(X) : c.push(X);
      });
    let d = e.createEl("div", { cls: "paperforge-skills-box" }),
      u = (y, b, k) => {
        if (b.length === 0) return;
        let C = d.createEl("div", { cls: "paperforge-skills-group" }),
          T = C.createEl("div", { cls: "paperforge-skills-collapse-header" }),
          O = C.createEl("div", { cls: "paperforge-skills-collapse-content" }),
          D = T.createEl("span", {
            text: "\u25BC",
            cls: "paperforge-skills-arrow",
          });
        (T.createEl("h4", {
          text: `${y} (${b.length})`,
          cls: "paperforge-skills-subheader",
        }),
          b.forEach((B) => {
            let X = B.name + (B.version ? " v" + B.version : ""),
              W = k ? " [system]" : " [user]",
              P = B.desc || "",
              R = new w.Setting(O).setName(X + W).setDesc(P);
            ((R.settingEl.style.opacity = B.disabled ? "0.4" : "1"),
              R.addToggle((U) => {
                U.setValue(!B.disabled).onChange((Y) => {
                  let ie = !Y,
                    pe = B.content.match(/^disable-model-invocation:\s*(.+)$/m)
                      ? B.content.replace(
                          /^disable-model-invocation:\s*.+$/m,
                          `disable-model-invocation: ${ie}`
                        )
                      : B.content.replace(
                          /^(---\r?\n)/,
                          `$1disable-model-invocation: ${ie}
`
                        );
                  (I.writeFileSync(B.path, pe, "utf-8"),
                    (B.disabled = ie),
                    (B.content = pe),
                    (R.settingEl.style.opacity = B.disabled ? "0.4" : "1"));
                });
              }));
          }));
        let z = k ? "system" : "user";
        ((this._skillsCollapsed[z] || !1) &&
          ((O.style.display = "none"), (D.style.transform = "rotate(-90deg)")),
          T.addEventListener("click", () => {
            (O.style.display !== "none"
              ? ((O.style.display = "none"),
                (D.style.transform = "rotate(-90deg)"))
              : ((O.style.display = ""), (D.style.transform = "rotate(0deg)")),
              (this._skillsCollapsed[z] = O.style.display === "none"));
          }));
      };
    (u("System Skills", i, !0),
      u("User Skills", c, !1),
      i.length === 0 &&
        c.length === 0 &&
        d.createEl("p", {
          text: `No skills found in ${n[s]}. Run setup to deploy skills.`,
          cls: "setting-item-description",
        }),
      this._advCollapsed === void 0 && (this._advCollapsed = !0));
    let p = e.createEl("div", { cls: "paperforge-collapsible-header" }),
      _ = p.createEl("span", {
        text: "\u25B6",
        cls: "paperforge-collapsible-arrow",
      });
    _.style.transform = this._advCollapsed ? "rotate(0deg)" : "rotate(90deg)";
    let m = p.createEl("span", {
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
          (_.style.transform = this._advCollapsed
            ? "rotate(0deg)"
            : "rotate(90deg)"));
      }),
      f.createEl("h4", { text: "Memory Layer" }),
      f
        .createEl("div", { cls: "paperforge-desc-box" })
        .setText(l("feat_memory_desc")));
    let S = f.createEl("div", { cls: "paperforge-memory-status" }),
      x = this.app.vault.adapter.basePath;
    (this.plugin._lastSyncTime &&
      !this._lastSyncTime &&
      (this._lastSyncTime = this.plugin._lastSyncTime),
      this._memoryStatusText === null && (this._memoryStatusText = Oe(x)),
      this._renderMemoryStatusText(
        S,
        this._memoryStatusText,
        this._lastSyncTime
      ),
      this._renderVectorSection(f));
  }
  _renderVectorSection(e) {
    var i;
    if (
      (e.createEl("h4", { text: "Vector Database" }),
      this.plugin.settings.features ||
        (this.plugin.settings.features = { memory_layer: !0, vector_db: !1 }),
      e
        .createEl("div", { cls: "paperforge-desc-box" })
        .setText(l("feat_vector_desc")),
      new w.Setting(e)
        .setName(l("feat_vector_enable"))
        .setDesc(l("feat_vector_enable_desc"))
        .addToggle((c) => {
          c.setValue(!!this.plugin.settings.features.vector_db).onChange(
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
      n = e.createEl("div", { cls: "paperforge-vec-header" }),
      a = n.createEl("span", {
        text: "\u25BC",
        cls: "paperforge-skills-arrow",
      });
    n.createEl("span", {
      cls: "paperforge-vec-header-label",
      text: l("feat_vector_config_label"),
    });
    let s = e.createEl("div", { cls: "paperforge-vector-config" }),
      o = (c) => {
        ((s.style.display = c ? "none" : ""),
          (a.style.transform = c ? "rotate(-90deg)" : "rotate(0deg)"));
      };
    if (
      (o(Ge(this._featurePanelsCollapsed, "vectorConfig", !1)),
      n.addEventListener("click", () => {
        let c = pt(this._featurePanelsCollapsed, "vectorConfig", !1);
        o(c);
      }),
      this._vectorDepsOk === !0)
    ) {
      this._renderVectorReady(s, r);
      return;
    }
    if (this._vectorDepsOk === !1) {
      this._renderVectorNoDeps(s);
      return;
    }
    if (this._vectorDepsOk === null) {
      let c = Ce(r);
      ((this._vectorDepsOk = c && (i = c.deps_installed) != null ? i : !1),
        this._vectorDepsOk && (this._embedStatusText = ye(r)),
        this.display());
    }
  }
  _renderApiConfig(e) {
    (new w.Setting(e)
      .setName(l("feat_openai_key"))
      .setDesc(l("feat_openai_key_desc"))
      .addText((t) => {
        t.setPlaceholder("sk-...")
          .setValue(this.plugin.settings.vector_db_api_key || "")
          .onChange((r) => {
            ((this.plugin.settings.vector_db_api_key = r),
              this.plugin.saveSettings());
          });
      }),
      new w.Setting(e)
        .setName(l("feat_api_base_url"))
        .setDesc(l("feat_api_base_url_desc"))
        .addText((t) => {
          t.setPlaceholder("https://api.openai.com/v1")
            .setValue(this.plugin.settings.vector_db_api_base || "")
            .onChange((r) => {
              ((this.plugin.settings.vector_db_api_base = r),
                this.plugin.saveSettings());
            });
        }),
      new w.Setting(e)
        .setName(l("feat_api_model"))
        .setDesc(l("feat_api_model_desc"))
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
      .setText(l("feat_deps_missing")),
      new w.Setting(e)
        .setName(l("feat_install_deps"))
        .setDesc(l("feat_install_deps_desc"))
        .addButton((r) => {
          r.setButtonText(l("feat_install_btn"))
            .setCta()
            .onClick(async () => {
              let n = this.app.vault.adapter.basePath,
                a = le(n, this.plugin.settings);
              if (!a.path) {
                new w.Notice(l("feat_no_python"));
                return;
              }
              (r.setButtonText(l("feat_installing")), r.setDisabled(!0));
              let s = "chromadb openai",
                o = new w.Notice(
                  l("feat_installing_pkgs").replace("{pkgs}", s),
                  0
                );
              try {
                let i = Object.assign({}, process.env, {
                    PYTHONIOENCODING: "utf-8",
                    PYTHONUTF8: "1",
                  }),
                  c = s.split(" ");
                (await new Promise((d, u) => {
                  (0, N.execFile)(
                    a.path,
                    [...a.extraArgs, "-m", "pip", "install", ...c],
                    { cwd: n, timeout: 3e5, env: i, windowsHide: !0 },
                    (p) => {
                      p ? u(p) : d();
                    }
                  );
                }),
                  o.hide(),
                  new w.Notice(l("feat_install_done")),
                  (this._vectorDepsOk = !0),
                  (this._embedStatusText = ye(n)),
                  this.display());
              } catch (i) {
                (o.hide(),
                  new w.Notice(
                    l("feat_install_failed") + (i.stderr || i.message || i)
                  ),
                  r.setButtonText(l("feat_retry_btn")),
                  r.setDisabled(!1));
              }
            });
        }));
  }
  _renderVectorReady(e, t) {
    (e.createEl("div", { cls: "paperforge-desc-box" }).setText(ye(t)),
      this._renderApiConfig(e));
    let n = e.createEl("div", { cls: "paperforge-embed-section" });
    n.createEl("div", { cls: "paperforge-embed-header" }).createEl("span", {
      text: l("feat_rebuild_vectors"),
      cls: "setting-item-name",
    });
    let s = n.createEl("div", { cls: "paperforge-embed-controls" }),
      o = n.createEl("div", { cls: "paperforge-embed-status-text" });
    (() => {
      var m, E, f;
      (s.empty(), o.empty());
      let c = (Ce(t) || {}).build_state || {};
      ((this.plugin._embedProgress = this.plugin._embedProgress || {
        current: 0,
        total: 0,
        key: "",
      }),
        !this.plugin._embedProcess &&
          c.status === "running" &&
          (this.plugin._embedProgress = {
            current: c.current || 0,
            total: c.total || 1,
            key: c.paper_id || "",
          }));
      let { current: d, total: u, key: p } = this.plugin._embedProgress;
      if (!!this.plugin._embedProcess || c.status === "running") {
        let v = s.createEl("div", { cls: "paperforge-progress-track" });
        v.style.cssText = "flex:1;";
        let S = u > 0 ? ((d / u) * 100).toFixed(1) : "0",
          x = v.createEl("div", { cls: "paperforge-progress-seg done" });
        if (
          ((x.style.cssText = `width:${S}%; min-width:${d > 0 ? "2px" : "0"};`),
          d < u)
        ) {
          let b = v.createEl("div", { cls: "paperforge-progress-seg pending" });
          b.style.cssText = `width:${(100 - parseFloat(S)).toFixed(1)}%;`;
        }
        (o.createEl("span", {
          cls: "paperforge-embed-progress-text",
          text: `${d}/${u} papers`,
        }),
          p &&
            o.createEl("span", {
              cls: "paperforge-embed-progress-key",
              text: ` (${p})`,
            }));
        let y = s.createEl("button");
        (y.setText("Stop"),
          (y.className = "mod-warning"),
          y.addEventListener("click", () => {
            (this._callPython(["embed", "stop", "--json"], { timeout: 8e3 }),
              this.plugin._embedProcess &&
                (this.plugin._embedProcess.kill(),
                (this.plugin._embedProcess = null)),
              this.display());
          }));
      } else {
        let v = Ce(t),
          S =
            ((m = v == null ? void 0 : v.chunk_count) != null ? m : 0) +
            ((E = v == null ? void 0 : v.body_chunk_count) != null ? E : 0) +
            ((f = v == null ? void 0 : v.object_chunk_count) != null ? f : 0),
          x = S > 0,
          y = v ? !!v.corrupted : !1,
          b = (C) => {
            if (!le(t, this.plugin.settings).path) {
              new w.Notice(l("feat_no_python"));
              return;
            }
            let O = Object.assign({}, process.env, {
              PYTHONIOENCODING: "utf-8",
              PYTHONUTF8: "1",
              VECTOR_DB_API_KEY: this.plugin.settings.vector_db_api_key || "",
              VECTOR_DB_API_BASE: this.plugin.settings.vector_db_api_base || "",
              VECTOR_DB_API_MODEL:
                this.plugin.settings.vector_db_api_model || "",
            });
            ((this.plugin._embedStderr = ""),
              (this.plugin._embedProgress = { current: 0, total: 0, key: "" }),
              (this.plugin._embedProcess = this._callPython(
                ["embed", "build", C],
                {
                  stream: !0,
                  env: O,
                  onData: (D) => {
                    let z = D.toString("utf-8").split(`
`);
                    for (let j of z)
                      if (j.startsWith("EMBED_START:"))
                        this.plugin._embedProgress.total =
                          parseInt(j.split(":")[1]) || 0;
                      else if (j.startsWith("EMBED_PROGRESS:")) {
                        let B = j.split(":");
                        ((this.plugin._embedProgress.current =
                          parseInt(B[1]) || 0),
                          (this.plugin._embedProgress.key = B[3] || ""));
                      } else
                        j.startsWith("EMBED_DONE") &&
                          ((this.plugin._embedProcess = null),
                          (this.plugin._embedProgress.current =
                            this.plugin._embedProgress.total));
                    this.display();
                  },
                  onStderr: (D) => {
                    (this.plugin._embedStderr ||
                      (this.plugin._embedStderr = ""),
                      (this.plugin._embedStderr += D.toString("utf-8")));
                  },
                  onError: (D) => {
                    ((this.plugin._embedProcess = null),
                      new w.Notice(
                        l("feat_build_failed") + ": " + (D.message || D)
                      ),
                      this.display());
                  },
                  onClose: (D) => {
                    if (((this.plugin._embedProcess = null), D === 0))
                      ((this.plugin._embedProgress.current =
                        this.plugin._embedProgress.total),
                        this.plugin.saveSettings(),
                        (this._embedStatusText = ye(t)),
                        new w.Notice(l("feat_build_complete")));
                    else {
                      this._embedStatusText = null;
                      let z = (this.plugin._embedStderr || "").slice(0, 200);
                      new w.Notice(
                        l("feat_build_failed") + (z ? ": " + z : ""),
                        8e3
                      );
                    }
                    ((this.plugin._embedStderr = ""),
                      this.display(),
                      this._refreshSnapshots(t));
                  },
                }
              )),
              this.display());
          };
        if (y) {
          let C = n.createEl("div");
          ((C.style.cssText =
            "padding:8px 12px; margin:8px 0; background:var(--background-modifier-warning); border-radius:4px; font-size:12px; display:flex; align-items:center; justify-content:space-between;"),
            C.createEl("span", { text: l("feat_vector_corrupted") }));
          let T = C.createEl("button", {
            text: l("feat_vector_rebuild_force_btn"),
          });
          ((T.className = "mod-cta"),
            T.addEventListener("click", () => b("--force")));
        }
        x &&
          !y &&
          s.createEl("span", {
            text: S + " chunks embedded",
            cls: "setting-item-description",
          });
        let k = s.createEl("button");
        if (
          (k.setText(x ? l("feat_rebuild_btn") : l("feat_build_btn")),
          k.addClass("mod-cta"),
          k.addEventListener("click", () => b("--resume")),
          !y && x)
        ) {
          let C = s.createEl("button");
          (C.setText(l("feat_vector_rebuild_force_btn")),
            (C.style.marginLeft = "6px"),
            C.addEventListener("click", () => b("--force")));
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
        new w.Notice(r));
      return;
    }
    if (!I.existsSync(e)) {
      let r = "\u8DEF\u5F84\u4E0D\u5B58\u5728 / Path does not exist";
      (t &&
        (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${r}</span>`),
        new w.Notice(r, 4e3));
      return;
    }
    try {
      I.accessSync(e, I.constants.X_OK);
    } catch (r) {
      let n = "\u4E0D\u53EF\u6267\u884C / Not executable";
      (t &&
        (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${n}</span>`),
        new w.Notice(n, 4e3));
      return;
    }
    (0, N.execFile)(e, ["--version"], { timeout: 8e3 }, (r, n) => {
      if (r || !n) {
        let i = "\u65E0\u6CD5\u8FD0\u884C / Cannot run";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${i}</span>`),
          new w.Notice(i, 4e3));
        return;
      }
      let a = n.match(/Python (\d+)\.(\d+)/);
      if (!a) {
        let i = "\u65E0\u6CD5\u89E3\u6790\u7248\u672C / Cannot parse version";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${i}</span>`),
          new w.Notice(i, 4e3));
        return;
      }
      let s = parseInt(a[1], 10),
        o = parseInt(a[2], 10);
      if (s < 3 || (s === 3 && o < 10)) {
        let i =
          "Python \u7248\u672C\u8FC7\u4F4E\uFF0C\u9700\u8981 3.10+ / Python version too low, need 3.10+";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${i}</span>`),
          new w.Notice(i, 4e3));
        return;
      }
      (0, N.execFile)(e, ["-m", "pip", "--version"], { timeout: 8e3 }, (i) => {
        if (i) {
          let c = `\u2713 Python ${s}.${o} \u6709\u6548\uFF0C\u4F46\u672A\u68C0\u6D4B\u5230 pip / Valid, but pip not found`;
          (t &&
            (t.innerHTML = `<span style="color:var(--text-warning)">\u26A0 ${c}</span>`),
            new w.Notice(c, 4e3));
        } else {
          let c = `\u2713 Python ${s}.${o} \u6709\u6548 / Valid`;
          (t &&
            (t.innerHTML = `<span style="color:var(--text-accent)">${c}</span>`),
            new w.Notice(c, 4e3));
        }
      });
    });
  }
  _syncRuntime(e) {
    let t = this.app.vault.adapter.basePath,
      { path: r, extraArgs: n = [] } = M(
        t,
        this.plugin.settings,
        void 0,
        void 0
      ),
      a = this.plugin.manifest.version,
      s = at(r, a, n);
    (e.setDisabled(!0), e.setButtonText(l("runtime_health_syncing")));
    let o = (c, d) => (
        console.log(`[PaperForge] Sync Runtime: trying ${d}`),
        it(s.cmd, c, t, s.timeout, void 0, fe())
      ),
      i = () => {
        let c = "opencode";
        try {
          let _ = I.readFileSync(Z.join(t, "paperforge.json"), "utf-8"),
            m = JSON.parse(_);
          m.agent_key && (c = m.agent_key);
        } catch (_) {}
        let d = [
            ...n,
            "-c",
            'from paperforge.services.skill_deploy import deploy_skills; from pathlib import Path; r=deploy_skills(vault=Path(r"' +
              t.replace(/\\/g, "\\\\") +
              '"), agent_key="' +
              c +
              '", overwrite=True); print("skills deployed" if r["skill_deployed"] else "skills skipped", flush=True)',
          ],
          u = (0, N.spawn)(r, d, { cwd: t, timeout: 3e4, windowsHide: !0 }),
          p = "";
        (u.stdout.on("data", (_) => {
          p += _.toString("utf-8");
        }),
          u.on("close", (_) => {
            console.log(`[PaperForge] Skill deploy: ${p.trim()} (exit ${_})`);
          }));
      };
    o(s.pypiArgs, "PyPI").then((c) => {
      if (c.exitCode === 0) {
        (console.log("[PaperForge] Sync Runtime: installed via PyPI"),
          i(),
          new w.Notice(l("runtime_health_sync_done").replace("{0}", a), 5e3),
          this.display());
        return;
      }
      (console.warn(
        "[PaperForge] Sync Runtime: PyPI failed, falling back to git..."
      ),
        o(s.gitArgs, "git").then((d) => {
          d.exitCode === 0
            ? (console.log("[PaperForge] Sync Runtime: installed via git"),
              i(),
              new w.Notice(
                l("runtime_health_sync_done").replace("{0}", a),
                5e3
              ),
              this.display())
            : (e.setDisabled(!1),
              e.setButtonText(l("runtime_health_sync")),
              console.error("[PaperForge] git fallback stderr:", d.stderr),
              new w.Notice(
                l("runtime_health_sync_fail").replace(
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
      { path: r, extraArgs: n = [] } = M(
        t,
        (a = this.plugin) == null ? void 0 : a.settings,
        void 0,
        void 0
      );
    (0, N.execFile)(r, [...n, "--version"], { timeout: 8e3 }, (s, o) => {
      let i = [];
      i.push({
        label: "Python",
        ok: !s,
        detail: s ? l("check_python_fail") : o.trim(),
      });
      let c = !1,
        d = process.env.HOME || process.env.USERPROFILE || bt.homedir() || "";
      if (process.platform === "darwin")
        c = [
          "/Applications/Zotero.app",
          Z.join(d, "Applications", "Zotero.app"),
        ].some((v) => {
          try {
            return I.existsSync(v);
          } catch (S) {
            return !1;
          }
        });
      else if (process.platform === "win32") {
        let f = process.env.ProgramFiles || "",
          v = process.env.LOCALAPPDATA || "";
        c = [
          Z.join(f, "Zotero"),
          Z.join(f, "(x86)", "Zotero"),
          Z.join(v, "Programs", "Zotero"),
          Z.join(v, "Zotero"),
          Z.join(d, "AppData", "Local", "Programs", "Zotero"),
        ]
          .filter(Boolean)
          .some((x) => {
            try {
              return I.existsSync(x);
            } catch (y) {
              return !1;
            }
          });
      } else
        c = [
          Z.join(d, ".local", "share", "zotero", "zotero"),
          "/usr/bin/zotero",
          "/usr/local/bin/zotero",
        ].some((v) => {
          try {
            return I.existsSync(v);
          } catch (S) {
            return !1;
          }
        });
      let u = this.plugin.settings.zotero_data_dir;
      if (!c && u)
        try {
          c = I.existsSync(u);
        } catch (f) {}
      i.push({
        label: "Zotero",
        ok: c,
        detail: c ? l("check_zotero_ok") : l("check_zotero_fail"),
      });
      let p = !1,
        _ = process.env.APPDATA || "";
      (process.platform === "win32" &&
        _ &&
        (p = Ae(Z.join(_, "Zotero", "Zotero", "Profiles"))),
        !p &&
          process.platform === "darwin" &&
          d &&
          (p = Ae(
            Z.join(d, "Library", "Application Support", "Zotero", "Profiles")
          )),
        !p &&
          process.platform !== "win32" &&
          process.platform !== "darwin" &&
          d &&
          (p = Ae(Z.join(d, ".zotero", "zotero", "Profiles"))),
        !p && u && String(u).trim() && (p = qe(u.trim())),
        !p && d && (p = qe(Z.join(d, "Zotero"))),
        i.push({
          label: "Better BibTeX",
          ok: p,
          detail: p ? l("check_bbt_ok") : l("check_bbt_fail"),
        }));
      let m = { true: "\u2713", false: "\u2717" };
      if (this._checkEl) {
        this._checkEl.setText(
          i.map((v) => `${m[String(v.ok)]} ${v.label}: ${v.detail}`).join(`
`)
        );
        let f = i.some((v) => !v.ok);
        this._checkEl.className = `paperforge-message msg-${f ? "error" : "ok"}`;
      }
      let E = i.filter((f) => !f.ok);
      (E.length > 0 &&
        new w.Notice(
          `[!!] \u672A\u901A\u8FC7: ${E.map((f) => f.label).join(", ")}`,
          6e3
        ),
        e());
    });
  }
  _renderMaintenanceTab(e) {
    e.createEl("h2", { text: l("tab_maintenance") || "\u7EF4\u62A4" });
    let t = this.app.vault.adapter.basePath,
      r = e.createEl("div"),
      n = (u, p) =>
        p === "retry_ocr" || p === "upgrade_legacy"
          ? { cmd: ["-m", "paperforge", "ocr", "redo", ...u], timeout: 3e5 }
          : p === "rebuild_result"
            ? {
                cmd: ["-m", "paperforge", "ocr", "rebuild", ...u],
                timeout: 12e4,
              }
            : null,
      a = null;
    try {
      a = mt(t);
    } catch (u) {}
    let s = M(t, this.plugin.settings, I, N.execFileSync);
    if (!s.path) {
      r.createEl("p", {
        text: "\u26A0 Python \u672A\u914D\u7F6E\uFF0C\u8BF7\u5148\u5728\u300C\u5B89\u88C5\u300D\u6807\u7B7E\u9875\u914D\u7F6E\u3002",
        cls: "setting-item-description",
      });
      return;
    }
    let o = (u) => {
      r.empty();
      let p = u.filter((f) => f.visible_in_maintenance);
      if (p.length === 0) {
        r.createEl("p", {
          text: l("maintenance_all_good") || "\u2705 \u5168\u90E8\u6B63\u5E38",
        });
        return;
      }
      let _ = s.path,
        m = s.extraArgs || [],
        E = [
          {
            key: "retry",
            title: l("maintenance_group_retry") || "\u9700\u8981\u91CD\u8BD5",
            items: [],
          },
          {
            key: "rebuild",
            title:
              l("maintenance_group_rebuild") ||
              "\u53EF\u91CD\u5EFA\u7ED3\u679C",
            items: [],
          },
          {
            key: "legacy_optional",
            title:
              l("maintenance_group_legacy") ||
              "\u53EF\u5347\u7EA7\u65E7\u7ED3\u679C\uFF08\u53EF\u9009\uFF09",
            items: [],
          },
        ];
      for (let f of p) {
        let v = E.find((S) => S.key === f.display_group);
        v && v.items.push(f);
      }
      for (let f of E) {
        if (f.items.length === 0) continue;
        let v = f.key === "legacy_optional",
          S = v ? r.createEl("details") : r.createEl("div");
        v
          ? S.createEl("summary").createEl("strong", {
              text: f.title + " (" + f.items.length + ")",
            })
          : S.createEl("h3", { text: f.title + " (" + f.items.length + ")" });
        let x = new Map();
        for (let P of f.items) x.set(P.key, !1);
        let y = S.createEl("div", { cls: "pf-maint-toolbar" }),
          b = y.createEl("button", { text: "\u5168\u9009" }),
          k = y.createEl("button", { text: "\u53D6\u6D88\u5168\u9009" }),
          C = y.createEl("button", {
            text: "\u25B6 \u6267\u884C\u5DF2\u9009",
            cls: "mod-cta",
          }),
          T = y.createEl("span", { cls: "pf-maint-exec-label" }),
          O = () => {
            let P = f.items.filter((R) => x.get(R.key)).length;
            T.setText("\u5DF2\u9009 " + P + " \u7BC7");
          };
        (O(),
          b.addEventListener("click", () => {
            for (let R of f.items) x.set(R.key, !0);
            (O(),
              S.querySelectorAll("input[type=checkbox].pf-maint-sel").forEach(
                (R) => {
                  R.checked = !0;
                }
              ));
          }),
          k.addEventListener("click", () => {
            for (let R of f.items) x.set(R.key, !1);
            (O(),
              S.querySelectorAll("input[type=checkbox].pf-maint-sel").forEach(
                (R) => {
                  R.checked = !1;
                }
              ));
          }),
          C.addEventListener("click", () => {
            let P = f.items.filter((R) => x.get(R.key));
            if (P.length === 0) {
              new w.Notice(
                "\u8BF7\u5148\u9009\u62E9\u8981\u5904\u7406\u7684\u8BBA\u6587\u3002"
              );
              return;
            }
            for (let R of P) {
              let U = n([R.key], R.display_action);
              U &&
                (0, N.execFile)(
                  _,
                  [...m, ...U.cmd],
                  { cwd: t, timeout: U.timeout, windowsHide: !0 },
                  () => {
                    new w.Notice(R.display_label + " \u2014 " + R.key);
                  }
                );
            }
          }));
        let z = S.createEl("div", { cls: "pf-maint-table-wrap" }).createEl(
            "table",
            { cls: "pf-maint-table" }
          ),
          j = z.createEl("thead"),
          B = z.createEl("tbody"),
          X = j.insertRow();
        [
          "",
          "Key",
          "Title",
          "\u5EFA\u8BAE\u64CD\u4F5C",
          "\u539F\u56E0",
          "\u64CD\u4F5C",
        ].forEach((P) => {
          let R = document.createElement("th");
          ((R.textContent = P), X.appendChild(R));
        });
        let W = (P) =>
          P === "retry_ocr"
            ? l("maintenance_btn_retry") || "\u91CD\u8BD5"
            : P === "rebuild_result"
              ? l("maintenance_btn_rebuild") || "\u91CD\u5EFA"
              : P === "upgrade_legacy"
                ? l("maintenance_btn_upgrade") || "\u5347\u7EA7"
                : "";
        for (let P of f.items) {
          let R = B.insertRow(),
            U = R.insertCell();
          U.style.cssText = "padding:3px 4px;text-align:center;";
          let Y = document.createElement("input");
          ((Y.type = "checkbox"),
            (Y.className = "pf-maint-sel"),
            (Y.checked = x.get(P.key) || !1),
            Y.addEventListener("change", () => {
              (x.set(P.key, Y.checked), O());
            }),
            U.appendChild(Y));
          let ie = R.insertCell();
          ((ie.style.cssText =
            "padding:3px 4px;white-space:nowrap;font-size:11px;max-width:90px;overflow:hidden;text-overflow:ellipsis;"),
            (ie.textContent = P.key));
          let me = R.insertCell();
          ((me.style.cssText =
            "padding:3px 4px;white-space:nowrap;max-width:220px;overflow:hidden;text-overflow:ellipsis;"),
            (me.textContent = P.title || P.key));
          let pe = R.insertCell();
          ((pe.style.cssText = "padding:3px 4px;white-space:nowrap;"),
            (pe.textContent = P.display_label));
          let Ee = R.insertCell();
          ((Ee.style.cssText =
            "padding:3px 4px;white-space:nowrap;max-width:160px;overflow:hidden;text-overflow:ellipsis;font-size:11px;color:var(--text-muted);"),
            (Ee.textContent = P.display_reason || ""));
          let ke = R.insertCell();
          ke.style.cssText =
            "padding:3px 4px;text-align:center;white-space:nowrap;";
          let he = document.createElement("button");
          ((he.textContent = W(P.display_action)),
            he.textContent &&
              (he.addEventListener("click", () => {
                let F = n([P.key], P.display_action);
                F &&
                  (0, N.execFile)(
                    _,
                    [...m, ...F.cmd],
                    { cwd: t, timeout: F.timeout, windowsHide: !0 },
                    () => {
                      new w.Notice(P.display_label + " \u2014 " + P.key);
                    }
                  );
              }),
              ke.appendChild(he)));
        }
      }
    };
    if (a) {
      let u = Object.values(a.papers);
      o(u);
    } else
      r.createEl("p", {
        text: "\u6B63\u5728\u52A0\u8F7D OCR \u7EF4\u62A4\u6570\u636E\u2026",
      });
    (yt(t, s.path, s.extraArgs || [], a || null)
      .then((u) => {
        u.changed
          ? (o(u.data),
            Ie(t, {
              manifest: {},
              papers: Object.fromEntries(u.data.map((p) => [p.key, p])),
              cached_at: new Date().toISOString(),
            }))
          : a ||
            (o(u.data),
            Ie(t, {
              manifest: {},
              papers: Object.fromEntries(u.data.map((p) => [p.key, p])),
              cached_at: new Date().toISOString(),
            }));
      })
      .catch(() => {
        a ||
          (r.empty(),
          r.createEl("p", {
            text: "\u65E0\u6CD5\u52A0\u8F7D OCR \u6570\u636E\u3002\u8BF7\u786E\u4FDD\u5DF2\u5B89\u88C5 paperforge \u5E76\u8FD0\u884C\u8FC7 OCR\u3002",
            cls: "setting-item-description",
          }));
      }),
      e.createEl("hr"),
      e.createEl("h3", { text: "\u5168\u5C40\u64CD\u4F5C" }));
    let i = e.createEl("div", { cls: "pf-maint-global" });
    (i
      .createEl("button", { text: "\u91CD\u5EFA\u641C\u7D22\u7D22\u5F15" })
      .addEventListener("click", () => {
        (new w.Notice("\u6B63\u5728\u91CD\u5EFA\u641C\u7D22\u7D22\u5F15\u2026"),
          (0, N.execFile)(
            s.path,
            [
              ...(s.extraArgs || []),
              "-m",
              "paperforge",
              "embed",
              "build",
              "--force",
            ],
            { cwd: t, timeout: 3e5, windowsHide: !0 },
            () => {
              new w.Notice(
                "\u641C\u7D22\u7D22\u5F15\u91CD\u5EFA\u5B8C\u6210\u3002"
              );
            }
          ));
      }),
      i
        .createEl("button", { text: "\u91CD\u5EFA\u8BB0\u5FC6\u5E93" })
        .addEventListener("click", () => {
          (new w.Notice("\u6B63\u5728\u91CD\u5EFA\u8BB0\u5FC6\u5E93\u2026"),
            (0, N.execFile)(
              s.path,
              [...(s.extraArgs || []), "-m", "paperforge", "repair", "--fix"],
              { cwd: t, timeout: 12e4, windowsHide: !0 },
              () => {
                new w.Notice(
                  "\u8BB0\u5FC6\u5E93\u91CD\u5EFA\u5B8C\u6210\u3002"
                );
              }
            ));
        }));
  }
  _renderReleaseNotesTab(e) {
    (e.createEl("h2", { text: "\u66F4\u65B0\u4E0E\u624B\u518C" }),
      e.createEl("h3", { text: "\u7248\u672C\u66F4\u65B0\u8BB0\u5F55" }));
    let t = vt.default.versions || [];
    for (let a of t) {
      let s = e.createEl("div", { cls: "paperforge-release-card" }),
        o = s.createEl("div", { cls: "paperforge-release-header" });
      if (
        (o.createEl("strong", { text: `v${a.version} \u2014 ${a.title}` }),
        o.createEl("span", {
          cls: "paperforge-release-date",
          text: `  (${a.date})`,
        }),
        a.breaking_or_migration && a.breaking_or_migration.length > 0)
      ) {
        let i = s.createEl("div", { cls: "paperforge-release-section" });
        i.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u884C\u4E3A\u53D8\u66F4 / \u8FC1\u79FB\u6CE8\u610F",
        });
        for (let c of a.breaking_or_migration)
          i.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${c}`,
          });
      }
      if (a.new_features && a.new_features.length > 0) {
        let i = s.createEl("div", { cls: "paperforge-release-section" });
        i.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u65B0\u529F\u80FD",
        });
        for (let c of a.new_features)
          i.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${c}`,
          });
      }
      if (a.fixes && a.fixes.length > 0) {
        let i = s.createEl("div", { cls: "paperforge-release-section" });
        i.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u4FEE\u590D",
        });
        for (let c of a.fixes)
          i.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${c}`,
          });
      }
      if (a.recommended_actions && a.recommended_actions.length > 0) {
        let i = s.createEl("div", {
          cls: "paperforge-release-section paperforge-release-recommended",
        });
        i.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u5EFA\u8BAE\u64CD\u4F5C",
        });
        for (let c of a.recommended_actions)
          i.createEl("div", {
            cls: "paperforge-release-item paperforge-release-item-bold",
            text: `\u2022 ${c}`,
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
var A = require("obsidian"),
  ce = H(require("fs")),
  De = H(require("path")),
  ue = require("child_process");
var Te = H(require("path"));
function xt(g) {
  if (!g) return null;
  let h = Te.dirname(g);
  for (;;) {
    let e = Te.basename(h);
    if (!e || e === ".") break;
    let t = e.match(/^([A-Z0-9]{8})(?:\s*-\s*.*)?$/i);
    if (t) return t[1];
    let r = Te.dirname(h);
    if (r === h) break;
    h = r;
  }
  return null;
}
var ve = class extends A.ItemView {
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
    this._searchContainer = null;
    this._searchInput = null;
    this._searchResultsEl = null;
    this._searchTimer = null;
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
    return ge;
  }
  getDisplayText() {
    return "PaperForge";
  }
  getIcon() {
    return Se;
  }
  async onOpen() {
    (this._buildPanel(),
      (this._modeSubscribers = []),
      (this._leafChangeTimer = null),
      this._setupEventSubscriptions(),
      this._fetchVersion(),
      this._detectAndSwitch());
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
      (this._messageEl = e.createEl("div", { cls: "paperforge-message" })),
      (this._contentEl = e.createEl("div", {
        cls: "paperforge-content-area",
      })));
  }
  _fetchVersion() {
    var s, o;
    let e = this.app.vault.adapter.basePath,
      t = this.app.plugins.plugins.paperforge,
      r =
        ((s = t == null ? void 0 : t.manifest) == null ? void 0 : s.version) ||
        "?",
      { path: n, extraArgs: a = [] } = M(
        e,
        (o = t == null ? void 0 : t.settings) != null ? o : null,
        void 0,
        void 0
      );
    nt(n, r, e, 1e4, void 0).then((i) => {
      if (i.status === "not-installed") return;
      let c = i.pyVersion || "";
      ((this._paperforgeVersion = c.startsWith("v") ? c : "v" + c),
        this._versionBadge &&
          this._versionBadge.setText(this._paperforgeVersion),
        this._driftBannerEl &&
        r &&
        this._paperforgeVersion !== "v" + r.replace(/^v/, "")
          ? ((this._driftBannerEl.style.display = "block"),
            this._driftBannerEl.setText(
              l("dashboard_drift_warning")
                .replace("{0}", this._paperforgeVersion)
                .replace("{1}", "v" + r.replace(/^v/, ""))
            ))
          : this._driftBannerEl &&
            (this._driftBannerEl.style.display = "none"));
    });
  }
  _fetchStats(e) {
    var s;
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
      { path: n, extraArgs: a = [] } = M(
        t,
        (s = r == null ? void 0 : r.settings) != null ? s : null,
        void 0,
        void 0
      );
    (0, ue.execFile)(
      n,
      [...a, "-m", "paperforge", "dashboard", "--json"],
      { cwd: t, timeout: 3e4 },
      (o, i) => {
        if (!o)
          try {
            let c = JSON.parse(i);
            if (c.ok && c.data) {
              let d = this._normalizeDashboardData(c.data);
              ((this._cachedStats = d),
                this._metricsEl.empty(),
                this._renderStats(d),
                this._renderOcr(d),
                (this._dashboardPermissions = c.data.permissions || {}));
              return;
            }
          } catch (c) {}
        this._fallbackFetchStats(e, t, r);
      }
    );
  }
  _normalizeDashboardData(e) {
    let t = e.stats || {},
      r = t.ocr_health || {},
      n = t.pdf_health || {},
      a = e.ocr_version_state || {},
      s = (r.done || 0) + (r.pending || 0) + (r.failed || 0);
    return {
      total_papers: t.papers || 0,
      formal_notes: t.papers || 0,
      exports: 0,
      bases: 0,
      ocr: {
        total: s,
        pending: r.pending || 0,
        processing: 0,
        done: r.done || 0,
        failed: r.failed || 0,
      },
      path_errors: (n.broken || 0) + (n.missing || 0),
      ocr_version_state: {
        total_papers: a.total_papers || 0,
        derived_stale_count: a.derived_stale_count || 0,
        raw_upgradable_count: a.raw_upgradable_count || 0,
      },
    };
  }
  _fallbackFetchStats(e, t, r) {
    var s, o, i;
    let n =
        ((s = r == null ? void 0 : r.settings) == null
          ? void 0
          : s.system_dir) || "System",
      a = De.join(t, n, "PaperForge", "indexes", "formal-library.json");
    try {
      let c = ce.readFileSync(a, "utf-8"),
        d = JSON.parse(c),
        u = d.items || [],
        p = {},
        _ = {
          pdf_health: { healthy: 0, unhealthy: 0 },
          ocr_health: { healthy: 0, unhealthy: 0 },
          note_health: { healthy: 0, unhealthy: 0 },
          asset_health: { healthy: 0, unhealthy: 0 },
        },
        m = 0,
        E = 0,
        f = 0,
        v = 0,
        S = 0,
        x = 0;
      for (let y of u) {
        y.note_path && x++;
        let b = y.lifecycle || "pdf_ready";
        p[b] = (p[b] || 0) + 1;
        let k = y.health || {};
        for (let T of [
          "pdf_health",
          "ocr_health",
          "note_health",
          "asset_health",
        ])
          (k[T] || "healthy") === "healthy" ? _[T].healthy++ : _[T].unhealthy++;
        let C = y.ocr_status || "";
        (m++,
          C === "done"
            ? E++
            : C === "pending"
              ? f++
              : C === "processing" || C === "queued" || C === "running"
                ? v++
                : S++);
      }
      ((this._cachedStats = {
        version:
          d.paperforge_version ||
          ((o = this._cachedStats) == null ? void 0 : o.version) ||
          "\u2014",
        total_papers: u.length,
        formal_notes: x,
        exports: 0,
        bases: 0,
        ocr: { total: m, pending: f, processing: v, done: E, failed: S },
        path_errors: 0,
        lifecycle_level_counts: p,
        health_aggregate: _,
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
      let { path: d, extraArgs: u = [] } = M(
        t,
        (i = r == null ? void 0 : r.settings) != null ? i : null,
        void 0,
        void 0
      );
      (0, ue.execFile)(
        d,
        [...u, "-m", "paperforge", "status", "--json"],
        { cwd: t, timeout: 3e4 },
        (p, _) => {
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
            let m = JSON.parse(_);
            ((this._cachedStats = m),
              this._metricsEl.empty(),
              this._renderStats(m),
              this._renderOcr(m));
          } catch (m) {
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
    var a;
    let e = this.app.vault.adapter.basePath,
      t = this.app.plugins.plugins.paperforge,
      r =
        ((a = t == null ? void 0 : t.settings) == null
          ? void 0
          : a.system_dir) || "System",
      n = De.join(e, r, "PaperForge", "indexes", "formal-library.json");
    try {
      let s = ce.readFileSync(n, "utf-8");
      return JSON.parse(s);
    } catch (s) {
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
    return et(this.app, t);
  }
  _patchCachedEntry(e, t) {
    if (!e || !this._cachedItems) return;
    let r = this._cachedItems.findIndex((n) => n.zotero_key === e);
    r !== -1 && (this._cachedItems[r] = je(this._cachedItems[r], t));
  }
  _filterByDomain(e) {
    return e ? this._getCachedIndex().filter((t) => t.domain === e) : [];
  }
  _renderStats(e) {
    var s;
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
      let i = this._metricsEl.createEl("div", {
        cls: "paperforge-metric-card",
      });
      (i.style.setProperty("--metric-color", o.color),
        i.createEl("div", {
          cls: "paperforge-metric-value",
          text: ((s = o.value) == null ? void 0 : s.toString()) || "\u2014",
        }),
        i.createEl("div", { cls: "paperforge-metric-label", text: o.label }),
        o.barMax > 0 && this._buildMetricBar(i, o.value, o.barMax));
    }
    let a = e.ocr_version_state || {};
    if (
      a.total_papers > 0 &&
      (a.derived_stale_count > 0 || a.raw_upgradable_count > 0)
    ) {
      let o = [];
      (a.derived_stale_count > 0 && o.push(`${a.derived_stale_count} stale`),
        a.raw_upgradable_count > 0 &&
          o.push(`${a.raw_upgradable_count} upgradable`));
      let i = this._metricsEl.createEl("div", {
        cls: "paperforge-metric-card",
      });
      (i.style.setProperty("--metric-color", "var(--color-yellow)"),
        i.createEl("div", {
          cls: "paperforge-metric-value",
          text: o.join(", "),
        }),
        i.createEl("div", {
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
      a = t.pending || 0,
      s = t.processing || 0,
      o = t.failed || 0;
    if (
      (this._ocrBadge &&
        (this._ocrBadge.removeClass("active", "idle"),
        s > 0
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
        s > 0
          ? this._ocrTrack.addClass("paperforge-processing")
          : this._ocrTrack.removeClass("paperforge-processing"));
      let i = [
        { cls: "pending", count: a },
        { cls: "active", count: s },
        { cls: "done", count: n },
        { cls: "failed", count: o },
      ];
      for (let c of i)
        if (c.count > 0) {
          let d = ((c.count / r) * 100).toFixed(1);
          this._ocrTrack.createEl("div", {
            cls: `paperforge-progress-seg ${c.cls}`,
            attr: { style: `width:${d}%` },
          });
        }
    }
    if (this._ocrCounts) {
      this._ocrCounts.empty();
      let i = [
        { cls: "pending", value: a, label: "Pending" },
        { cls: "active", value: s, label: "Processing" },
        { cls: "done", value: n, label: "Done" },
        { cls: "failed", value: o, label: "Failed" },
      ];
      for (let c of i) {
        let d = this._ocrCounts.createEl("div", {
          cls: "paperforge-ocr-count",
        });
        (d.createEl("div", {
          cls: "paperforge-ocr-count-value",
          text: c.value.toString(),
        }),
          d.createEl("div", {
            cls: "paperforge-ocr-count-label",
            text: c.label,
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
      a = e.createEl("div", { cls: "paperforge-lifecycle-stepper" }),
      s = !1;
    for (let o of n) {
      let i = a.createEl("div", { cls: "step" });
      (i.createEl("div", { cls: "step-indicator" }),
        i.createEl("div", { cls: "step-label", text: o.label }),
        o.key === r
          ? (i.addClass("current"), (s = !0))
          : s
            ? i.addClass("pending")
            : i.addClass("completed"));
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
    for (let a of r) {
      let s = t[a.key] || "healthy",
        o = n.createEl("div", { cls: "paperforge-health-cell" }),
        i,
        c,
        d;
      (s === "healthy" || s === "ok"
        ? ((i = a.iconOk), (c = "ok"), (d = `${a.label}: OK`))
        : s === "warn" || s === "warning" || s === "degraded"
          ? ((i = a.iconWarn),
            (c = "warn"),
            (d = `${a.label}: Needs Attention`))
          : ((i = a.iconFail), (c = "fail"), (d = `${a.label}: Failed`)),
        o.addClass(c),
        o.setAttribute("title", d),
        o.createEl("div", { cls: "paperforge-health-cell-icon", text: i }),
        o.createEl("div", {
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
    let n = e.createEl("div", { cls: "paperforge-maturity-gauge" }),
      a = n.createEl("div", { cls: "gauge-track" }),
      s = 4,
      o = Math.max(1, Math.min(s, Math.round(t)));
    for (let i = 1; i <= s; i++) {
      let c = a.createEl("div", { cls: "gauge-segment" });
      i <= o && (c.addClass("filled"), c.addClass(`level-${i}`));
    }
    if (
      (n.createEl("div", { cls: "gauge-level", text: `Level ${o} / ${s}` }),
      o < s && r)
    ) {
      let i = typeof r == "string" ? [r] : r;
      if (i.length > 0) {
        let c = n.createEl("ul", { cls: "gauge-blockers" });
        for (let d of i) c.createEl("li", { text: d });
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
      a = Math.max(1, ...r.map((s) => t[s.key] || 0));
    for (let s of r) {
      let o = t[s.key] || 0,
        i = (o / a) * 100,
        c = n.createEl("div", { cls: "bar-row" });
      (c.createEl("div", { cls: "bar-label", text: s.label }),
        c
          .createEl("div", { cls: "bar-track" })
          .createEl("div", {
            cls: `bar-fill ${s.cls}`,
            attr: { style: `width:${i.toFixed(1)}%` },
          }),
        c.createEl("div", { cls: "bar-count", text: o.toString() }));
    }
  }
  _invalidateIndex() {
    this._cachedItems = null;
  }
  _extractZoteroKeyFromPath(e) {
    return xt(e);
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
        s = a && a.frontmatter && a.frontmatter.zotero_key;
      if (s) return { mode: "paper", filePath: r, key: s, domain: null };
    }
    if (t === "pdf") {
      let a = this._getCachedIndex();
      for (let s of a) {
        let o = (s.pdf_path || "").match(/\[\[([^\]]+)\]\]/);
        if ((o ? o[1] : s.pdf_path) === r)
          return {
            mode: "paper",
            filePath: r,
            key: s.zotero_key,
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
      }
  }
  _renderGlobalMode() {
    var Y, ie, me, pe, Ee, ke, he;
    if (!this._contentEl) return;
    let e = this._contentEl.createEl("div", { cls: "paperforge-global-view" });
    ((this._driftBannerEl = e.createEl("div", {
      cls: "paperforge-drift-banner",
    })),
      (this._driftBannerEl.style.display = "none"));
    let t = this._getCachedIndex(),
      r = t.length,
      n = 0,
      a = 0,
      s = 0;
    for (let F of t)
      (F.has_pdf && n++,
        F.ocr_status === "done" && a++,
        F.deep_reading_status === "done" && s++);
    let o = e.createEl("div", { cls: "paperforge-library-snapshot" });
    o.createEl("div", {
      cls: "paperforge-section-label",
      text: "Library Snapshot",
    });
    let i = o.createEl("div", { cls: "paperforge-snapshot-pills" }),
      c = [
        { value: r, label: "papers" },
        { value: n, label: "PDFs ready" },
        { value: a, label: "OCR done" },
        { value: s, label: "deep-read done" },
      ];
    for (let F of c) {
      let L = i.createEl("div", { cls: "paperforge-snapshot-pill" });
      (L.createEl("span", {
        cls: "paperforge-snapshot-value",
        text: String(F.value),
      }),
        L.createEl("span", {
          cls: "paperforge-snapshot-label",
          text: " " + F.label,
        }));
    }
    let d = e.createEl("div", { cls: "paperforge-system-status" });
    d.createEl("div", {
      cls: "paperforge-section-label",
      text: "System Status",
    });
    let u = d.createEl("div", { cls: "paperforge-status-grid" }),
      p = this.app.plugins.plugins.paperforge,
      _ =
        ((Y = p == null ? void 0 : p.manifest) == null ? void 0 : Y.version) ||
        "?",
      m = this._paperforgeVersion;
    if (!m)
      try {
        let F = this.app.vault.adapter.basePath,
          { path: L, extraArgs: ee = [] } = M(
            F,
            (ie = p == null ? void 0 : p.settings) != null ? ie : null,
            void 0,
            void 0
          ),
          q = (0, ue.execFileSync)(
            L,
            [...ee, "-c", "import paperforge; print(paperforge.__version__)"],
            { cwd: F, timeout: 5e3, encoding: "utf-8", windowsHide: !0 }
          ).trim();
        q &&
          ((m = q.startsWith("v") ? q : "v" + q),
          (this._paperforgeVersion = m));
      } catch (F) {}
    m = m || "\u2014";
    let E = m === "v" + _;
    this._renderSystemStatusRow(
      u,
      "Runtime",
      E ? "healthy" : "mismatch",
      E ? "v" + _ : "plugin v" + _ + " \u2260 CLI " + m
    );
    let f = this._loadIndex(),
      v = f && f.items && f.items.length > 0;
    this._renderSystemStatusRow(
      u,
      "Index",
      v ? "healthy" : "missing",
      v ? f.items.length + " entries" : "formal-library.json not found"
    );
    let S =
        ((me = p == null ? void 0 : p.settings) == null
          ? void 0
          : me.system_dir) || "System",
      x = this.app.vault.adapter.basePath,
      y = !1,
      b = "No exports found";
    try {
      let F = De.join(x, S, "PaperForge", "exports");
      if (ce.existsSync(F)) {
        let L = ce.readdirSync(F).filter((ee) => ee.endsWith(".json"));
        ((y = L.length > 0),
          (b = y ? L.length + " export(s)" : "No JSON exports"));
      }
    } catch (F) {}
    this._renderSystemStatusRow(
      u,
      "Zotero Export",
      y ? "healthy" : "missing",
      b
    );
    let k = !!(
      (pe = p == null ? void 0 : p.settings) != null && pe.paddleocr_api_key
    );
    if (!k)
      try {
        let F =
            ((Ee = p == null ? void 0 : p.settings) == null
              ? void 0
              : Ee.system_dir) || "System",
          L = De.join(x, F, "PaperForge", ".env");
        if (ce.existsSync(L)) {
          let q = ce
            .readFileSync(L, "utf-8")
            .match(/^PADDLEOCR_API_TOKEN\s*=\s*(.+)$/m);
          k = !!(q && q[1] && q[1].trim());
        }
      } catch (F) {}
    (k ||
      (k = !!(
        process.env.PADDLEOCR_API_TOKEN ||
        process.env.PADDLEOCR_API_KEY ||
        process.env.OCR_TOKEN
      )),
      this._renderSystemStatusRow(
        u,
        "OCR Token",
        k ? "configured" : "missing",
        k ? "Configured" : "Not set"
      ));
    let C = !1,
      T = "",
      O = this.app.vault.adapter.basePath,
      D = Ue(O);
    ((C = ct(O)),
      (T =
        (D && ((ke = D.summary) == null ? void 0 : ke.reason)) ||
        (D && ((he = D.summary) == null ? void 0 : he.status)) ||
        "Unknown"),
      this._renderSystemStatusRow(
        u,
        "Memory Layer",
        C ? "healthy" : "fail",
        T
      ));
    let z = !E && m !== "\u2014";
    if (z || !v || !y || !k) {
      let F = e.createEl("div", { cls: "paperforge-issue-summary" });
      F.createEl("div", {
        cls: "paperforge-section-label",
        text: "\u9700\u8981\u5904\u7406",
      });
      let L = F.createEl("div", { cls: "paperforge-issue-list" });
      (z &&
        L.createEl("div", {
          cls: "paperforge-issue-item",
          text: "Runtime version mismatch",
        }),
        v ||
          L.createEl("div", {
            cls: "paperforge-issue-item",
            text: "Index missing or corrupted",
          }),
        y ||
          L.createEl("div", {
            cls: "paperforge-issue-item",
            text: "No Zotero export found",
          }),
        k ||
          L.createEl("div", {
            cls: "paperforge-issue-item",
            text: "PaddleOCR API key not configured",
          }));
      let ee = F.createEl("div", { cls: "paperforge-issue-actions" }),
        q = ee.createEl("button", { cls: "paperforge-contextual-btn" });
      (q.createEl("span", { text: "Run Doctor" }),
        q.addEventListener("click", () => {
          let we = G.find((ze) => ze.id === "paperforge-doctor");
          we && this._runAction(we, q);
        }));
      let de = ee.createEl("button", { cls: "paperforge-contextual-btn" });
      (de.createEl("span", { text: "Repair Issues" }),
        de.addEventListener("click", () => {
          let we = G.find((ze) => ze.id === "paperforge-repair");
          we && this._runAction(we, de);
        }));
    }
    let B = e.createEl("div", { cls: "paperforge-global-actions" });
    B.createEl("div", {
      cls: "paperforge-section-label",
      text: "Start Working",
    });
    let X = B.createEl("div", { cls: "paperforge-global-actions-row" }),
      W = X.createEl("button", { cls: "paperforge-contextual-btn primary" });
    (W.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u{1F4C1}",
    }),
      W.createEl("span", { text: "Open Literature Hub" }),
      W.addEventListener("click", () => {
        var ee;
        let F =
            ((ee = p == null ? void 0 : p.settings) == null
              ? void 0
              : ee.base_dir) || "Bases",
          L = this.app.vault.getAbstractFileByPath(F);
        if (L) {
          let q = null;
          if (
            (L.children &&
              (q = L.children.find((de) => de.extension === "base")),
            q)
          ) {
            let de = this.app.workspace.getLeaf(!1);
            de && de.openFile(q);
          } else new A.Notice("[!!] No .base file found in " + F, 6e3);
        } else new A.Notice("[!!] Base directory not found: " + F, 6e3);
      }));
    let P = X.createEl("button", { cls: "paperforge-contextual-btn" });
    (P.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    }),
      P.createEl("span", { text: "Sync Library" }),
      P.addEventListener("click", () => {
        let F = G.find((L) => L.id === "paperforge-sync");
        F && this._runAction(F, P);
      }));
    let R = X.createEl("button", { cls: "paperforge-contextual-btn" });
    (R.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    }),
      R.createEl("span", { text: "Run OCR" }),
      R.addEventListener("click", () => {
        let F = G.find((L) => L.id === "paperforge-ocr");
        F && this._runAction(F, R);
      }));
    let U = X.createEl("button", { cls: "paperforge-contextual-btn warn" });
    (U.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BA",
    }),
      U.createEl("span", { text: "Redo OCR" }),
      U.addEventListener("click", () => {
        let F = G.find((L) => L.id === "paperforge-ocr-redo");
        F && this._runAction(F, U);
      }));
  }
  _renderSystemStatusRow(e, t, r, n) {
    let a = e.createEl("div", { cls: "paperforge-status-row" });
    (a
      .createEl("span", { cls: "paperforge-status-dot" })
      .addClass(r === "healthy" || r === "configured" ? "ok" : "fail"),
      a.createEl("span", { cls: "paperforge-status-label", text: t }),
      a.createEl("span", { cls: "paperforge-status-detail", text: n || "" }));
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
        new A.Notice("Title copied"));
    });
    let s = n.createEl("div", { cls: "paperforge-paper-meta" });
    (e.authors &&
      e.authors.length > 0 &&
      s.createEl("span", {
        cls: "paperforge-paper-authors",
        text: e.authors.join(", "),
      }),
      e.year &&
        s.createEl("span", {
          cls: "paperforge-paper-year",
          text: String(e.year),
        }));
    let o = r.createEl("div", { cls: "paperforge-status-strip" }),
      i = o.createEl("div", { cls: "paperforge-status-strip-left" }),
      c = o.createEl("div", { cls: "paperforge-status-strip-right" }),
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
    for (let u of d) {
      let p = i.createEl("span", { cls: "paperforge-status-pill" }),
        _ = "pending";
      (u.ok ? (_ = "ok") : u.fail ? (_ = "fail") : u.pending && (_ = "pending"),
        p.addClass(_));
      let m = u.ok ? "\u2713" : u.fail ? "\u2717" : "\u25CB";
      (p.createEl("span", { cls: "paperforge-status-pill-icon", text: m }),
        p.createEl("span", { text: " " + u.label }));
    }
    if (e.pdf_path) {
      let u = c.createEl("button", { cls: "paperforge-contextual-btn" });
      (u.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\u{1F4C4}",
      }),
        u.createEl("span", { text: "\u6253\u5F00 PDF" }),
        u.addEventListener("click", () => {
          let p = e.pdf_path.match(/\[\[([^\]]+)\]\]/),
            _ = p ? p[1] : e.pdf_path;
          this.app.vault.getAbstractFileByPath(_)
            ? this.app.workspace.openLinkText(_, "")
            : new A.Notice("[!!] PDF not found: " + _, 6e3);
        }));
    }
    if (e.fulltext_path) {
      let u = c.createEl("button", { cls: "paperforge-contextual-btn" });
      (u.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\u{1F4DD}",
      }),
        u.createEl("span", { text: "\u6253\u5F00\u5168\u6587" }),
        u.addEventListener("click", () => this._openFulltext(e.fulltext_path)));
    }
    if (
      (this._renderPaperOverviewCard(r, e),
      e.next_step === "ready" && e.deep_reading_status === "done")
    ) {
      let u = r.createEl("div", { cls: "paperforge-complete-row" });
      (u.createEl("span", { text: "\u2713" }),
        u.createEl("span", {
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
      s = a.createEl("div", {
        cls: "paperforge-paper-overview-excerpt",
        text: "\u52A0\u8F7D\u4E2D...",
      });
    if (t.note_path) {
      let o = this.app.vault.getAbstractFileByPath(t.note_path);
      o
        ? this.app.vault
            .read(o)
            .then((i) => {
              let c = this._extractOverviewFromNote(i);
              if (c) {
                let d = c.length > 200 ? c.slice(0, 200) + "..." : c;
                if ((s.setText(d), c.length > 200)) {
                  let u = a.createEl("div", {
                      cls: "paperforge-expand-container",
                    }),
                    p = u.createEl("button", {
                      cls: "paperforge-expand-icon",
                      title: "\u5C55\u5F00/\u6536\u8D77",
                    });
                  p.innerHTML =
                    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>';
                  let _ = !1;
                  u.addEventListener("click", () => {
                    (s.setText(_ ? d : c),
                      (p.innerHTML = _
                        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>'
                        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>'),
                      (_ = !_));
                  });
                }
              } else
                s.setText(
                  "\u5C1A\u672A\u751F\u6210\u6587\u7AE0\u6982\u89C8\u3002\u8FD0\u884C /pf-deep \u5F00\u59CB\u7CBE\u8BFB\u3002"
                );
            })
            .catch(() => {
              s.setText("\u65E0\u6CD5\u8BFB\u53D6\u7B14\u8BB0\u5185\u5BB9");
            })
        : s.setText("\u7B14\u8BB0\u6587\u4EF6\u4E0D\u5B58\u5728");
    } else s.setText("\u5C1A\u672A\u751F\u6210\u6587\u7AE0\u6982\u89C8");
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
      let i = r.indexOf(o);
      if (i !== -1) {
        let c = r.slice(i + o.length),
          d = ["**5 Cs", "**Figure", "**\u8BC1\u636E", "### Pass 2", "## "],
          u = c.length;
        for (let m of d) {
          let E = c.indexOf(m);
          E !== -1 && E < u && (u = E);
        }
        let p = c.indexOf(`

`);
        p !== -1 && p < u && (u = p);
        let _ = c.slice(0, u).trim();
        return (
          _.startsWith("**") && (_ = _.slice(2)),
          _.endsWith("**") && (_ = _.slice(0, -2)),
          _ || null
        );
      }
    }
    let a = r.indexOf(`
`);
    if (a === -1) return null;
    let s = r
      .slice(a + 1)
      .split(
        `

`
      )[0]
      .trim();
    return !s || s.startsWith("###") || s.startsWith("##")
      ? null
      : s.length > 300
        ? s.slice(0, 300) + "..."
        : s;
  }
  _renderRecentDiscussionCard(e, t) {
    let r = e.createEl("div", { cls: "paperforge-discussion-card" });
    if (((r.style.display = "none"), !t.note_path)) return;
    let n = t.note_path.lastIndexOf("/"),
      s = (n !== -1 ? t.note_path.substring(0, n) : ".") + "/ai/discussion.md";
    this.app.vault.adapter
      .exists(s)
      .then((o) => {
        if (o) return this.app.vault.adapter.read(s);
      })
      .then(async (o) => {
        if (!o) return;
        let i = this._parseDiscussionMD(o);
        if (!i || i.length === 0) return;
        ((r.style.display = "block"),
          r
            .createEl("div", { cls: "paperforge-discussion-header" })
            .createEl("span", {
              cls: "paperforge-discussion-title",
              text: "\u6700\u8FD1\u8BA8\u8BBA",
            }));
        for (let u of i) {
          let p = r.createEl("div", { cls: "paperforge-discussion-item" }),
            _ = p.createEl("div", { cls: "paperforge-discussion-q" });
          (_.createEl("span", {
            cls: "paperforge-discussion-q-label",
            text: "\u63D0\u95EE\uFF1A",
          }),
            _.createEl("span", {
              cls: "paperforge-discussion-q-text",
              text: u.question,
            }));
          let m = p.createEl("div", { cls: "paperforge-discussion-a" }),
            E = !1;
          if (
            (u.answer &&
              u.answer.length > 500 &&
              ((E = !0), m.classList.add("paperforge-discussion-a-collapsed")),
            await A.MarkdownRenderer.render(
              this.app,
              u.answer || "",
              m,
              s,
              this
            ),
            E)
          ) {
            let f = !1;
            ((p.style.cursor = "pointer"),
              p.addEventListener("click", () => {
                ((f = !f),
                  m.classList.toggle("paperforge-discussion-a-collapsed", !f),
                  m.classList.toggle("paperforge-discussion-a-expanded", f));
              }));
          }
        }
        r.createEl("a", {
          cls: "paperforge-discussion-viewall",
          text: "\u67E5\u770B\u5168\u90E8\u8BA8\u8BBA \u2192",
        }).addEventListener("click", (u) => {
          (u.preventDefault(),
            this.app.vault.getAbstractFileByPath(s)
              ? this.app.workspace.openLinkText(s, "")
              : new A.Notice(
                  "\u8BA8\u8BBA\u6587\u4EF6\u5C1A\u672A\u751F\u6210"
                ));
        });
      })
      .catch((o) => {
        console.error("PaperForge: discussion.md read error", s, o.message);
      });
  }
  _parseDiscussionMD(e) {
    let t = e.split(/\n## /).slice(1);
    if (t.length === 0) return null;
    let r = t[t.length - 1],
      n = [],
      a = r.split(/\*\*\u95EE\u9898:\*\*/).slice(1);
    for (let s of a) {
      let o = s.match(/\*\*\u89E3\u7B54:\*\*/);
      if (!o) continue;
      let i = s.substring(0, o.index).trim(),
        c = s.substring(o.index + 3 + 4).trim();
      n.push({ question: i, answer: c });
    }
    return n.slice(-3);
  }
  _renderPaperTechnicalDetails(e, t) {
    let r = this._currentPaperKey,
      n = e.createEl("div", { cls: "paperforge-technical-details" }),
      a = n.createEl("button", { cls: "paperforge-technical-details-toggle" }),
      s = n.createEl("div", { cls: "paperforge-technical-details-body" });
    ((s.style.display = "none"),
      this._techDetailsExpanded
        ? ((s.style.display = "block"),
          a.setText("\u6280\u672F\u8BE6\u60C5 \u25BE"))
        : a.setText("\u6280\u672F\u8BE6\u60C5 \u25B8"),
      a.addEventListener("click", () => {
        let p = s.style.display !== "none";
        ((s.style.display = p ? "none" : "block"),
          a.setText(
            p
              ? "\u6280\u672F\u8BE6\u60C5 \u25B8"
              : "\u6280\u672F\u8BE6\u60C5 \u25BE"
          ),
          (this._techDetailsExpanded = !p));
      }));
    let o = s.createEl("div", { cls: "paperforge-workflow-toggles" }),
      i = [
        { key: "do_ocr", label: "OCR", hint: "\u52A0\u5165 OCR" },
        {
          key: "analyze",
          label: "\u7CBE\u8BFB",
          hint: "\u6807\u8BB0\u7CBE\u8BFB",
        },
      ];
    for (let p of i) {
      let _ = o.createEl("label", { cls: "paperforge-workflow-toggle" }),
        m = _.createEl("input", {
          type: "checkbox",
          cls: "paperforge-workflow-checkbox",
        });
      ((m.checked = t[p.key] === !0),
        _.createEl("span", {
          cls: "paperforge-workflow-toggle-label",
          text: p.label,
        }),
        _.createEl("span", {
          cls: "paperforge-workflow-toggle-hint",
          text: p.hint,
        }),
        m.addEventListener("change", async () => {
          let E = t.note_path
            ? this.app.vault.getAbstractFileByPath(t.note_path)
            : null;
          if (!E) {
            new A.Notice("[!!] Note file not found", 6e3);
            return;
          }
          let f = m.checked;
          (await this.app.fileManager.processFrontMatter(E, (v) => {
            v[p.key] = f;
          }),
            this._patchCachedEntry(r, { [p.key]: f }),
            (this._currentPaperEntry = je(this._currentPaperEntry, {
              [p.key]: f,
            })));
        }));
    }
    let c = t.health || {},
      d = [
        ["PDF Health", c.pdf_health || "\u2014"],
        ["OCR Status", t.ocr_status || "\u2014"],
        ["Asset Health", c.asset_health || "\u2014"],
        ["Note Path", t.note_path || "\u2014"],
        ["Fulltext Path", t.fulltext_path || "\u2014"],
      ],
      u = new Set(["Note Path", "Fulltext Path", "Key"]);
    for (let [p, _] of d) {
      let m = s.createEl("div", { cls: "paperforge-technical-row" });
      m.createEl("span", { cls: "paperforge-technical-label", text: p });
      let E = m.createEl("span", {
        cls: "paperforge-technical-value",
        text: String(_),
      });
      u.has(p) &&
        _ &&
        _ !== "\u2014" &&
        (E.addClass("pf-copy"),
        E.addEventListener("click", () => {
          (navigator.clipboard.writeText(_), new A.Notice(p + " copied"));
        }));
    }
  }
  _renderNextStepCard(e, t, r) {
    var i, c;
    let n = t.next_step || "ready",
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
      s = a[n] || a.ready,
      o = e.createEl("div", { cls: "paperforge-next-step-card" });
    if (
      (n === "ready" && o.addClass("ready"),
      o.createEl("div", {
        cls: "paperforge-next-step-label",
        text: "Recommended Next Step",
      }),
      o.createEl("div", { cls: "paperforge-next-step-text", text: s.text }),
      s.cmd && s.cmd !== "ready")
    ) {
      let d = o.createEl("button", { cls: "paperforge-next-step-trigger" });
      (d.createEl("span", { text: s.icon + "  " + s.label }),
        d.addEventListener("click", () => {
          let u = G.find((p) => p.cmd === s.cmd);
          u && this._runAction(u, d);
        }));
    } else if (n === "/pf-deep") {
      let d = o.createEl("button", { cls: "paperforge-next-step-trigger" });
      (d.createEl("span", { text: "\u{1F4CB}  " + l("copy_pf_deep_cmd") }),
        d.addEventListener("click", () => {
          let E = "/pf-deep " + r;
          navigator.clipboard
            .writeText(E)
            .then(() => {
              (d.setText("\u2713  " + l("copied")),
                new A.Notice(E + " copied"));
            })
            .catch(() => {
              new A.Notice("[!!] Clipboard write failed", 6e3);
            });
        }));
      let u =
          ((c =
            (i = this.app.plugins.plugins.paperforge) == null
              ? void 0
              : i.settings) == null
            ? void 0
            : c.agent_platform) || "opencode",
        _ =
          {
            opencode: "OpenCode",
            claude: "Claude Code",
            cursor: "Cursor",
            github_copilot: "GitHub Copilot",
            windsurf: "Windsurf",
            codex: "Codex",
            gemini: "Gemini CLI",
            cline: "Cline",
          }[u] || u;
      o.createEl("div", { cls: "paperforge-agent-platform-label" }).setText(
        l("run_in_agent").replace("{0}", _)
      );
    } else
      n === "ready" &&
        o
          .createEl("button", { cls: "paperforge-next-step-trigger" })
          .createEl("span", { text: "\u2713  " + s.label });
  }
  _openFulltext(e) {
    if (!e) {
      new A.Notice("[!!] No fulltext path available for this paper", 6e3);
      return;
    }
    let t = this.app.vault.getAbstractFileByPath(e);
    t
      ? this.app.workspace.openLinkText(t.path, "")
      : new A.Notice("[!!] Fulltext file not found: " + e, 6e3);
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
      a = 0,
      s = 0,
      o = 0,
      i = 0,
      c = 0,
      d = 0,
      u = 0;
    for (let y of t) {
      (y.has_pdf && a++,
        y.ocr_status === "done" && s++,
        y.ocr_status === "done" && y.analyze === !0 && o++,
        y.deep_reading_status === "done" && i++);
      let b = y.ocr_status || "";
      b === "pending" || b === "queued"
        ? c++
        : b === "processing"
          ? d++
          : (b === "failed" ||
              b === "blocked" ||
              b === "done_incomplete" ||
              b === "nopdf") &&
            u++;
    }
    r.createEl("div", { cls: "paperforge-collection-header" }).createEl("div", {
      cls: "paperforge-collection-title",
      text: e,
    });
    let _ = r.createEl("div", { cls: "paperforge-workflow-overview" });
    _.createEl("div", {
      cls: "paperforge-section-label",
      text: "Workflow Overview",
    });
    let m = _.createEl("div", { cls: "paperforge-workflow-funnel" }),
      E = [
        { value: n, label: "Total" },
        { value: a, label: "PDF Ready" },
        { value: s, label: "OCR Done" },
        { value: i, label: "Deep Read" },
      ];
    for (let y = 0; y < E.length; y++) {
      let b = m.createEl("div", { cls: "paperforge-workflow-stage" });
      (b.createEl("div", {
        cls: "paperforge-workflow-stage-value",
        text: String(E[y].value),
      }),
        b.createEl("div", {
          cls: "paperforge-workflow-stage-label",
          text: E[y].label,
        }),
        y < E.length - 1 &&
          m.createEl("div", {
            cls: "paperforge-workflow-arrow",
            text: "\u2192",
          }));
    }
    if (c + d + s + u > 0) {
      let y = r.createEl("div", { cls: "paperforge-ocr-section" }),
        b = y.createEl("div", { cls: "paperforge-collection-ocr-header" });
      b.createEl("h4", { cls: "paperforge-ocr-title", text: "OCR Pipeline" });
      let k = b.createEl("span", { cls: "paperforge-ocr-badge idle" });
      d > 0
        ? (k.addClass("active"), k.setText("Processing"))
        : c > 0
          ? k.setText("Pending")
          : (k.addClass("idle"), k.setText("Idle"));
      let C = y.createEl("div", { cls: "paperforge-progress-track" });
      d > 0 && C.addClass("paperforge-processing");
      let T = c + d + s + u,
        O = [
          { cls: "pending", count: c },
          { cls: "active", count: d },
          { cls: "done", count: s },
          { cls: "failed", count: u },
        ];
      for (let j of O)
        if (j.count > 0) {
          let B = ((j.count / T) * 100).toFixed(1);
          C.createEl("div", {
            cls: `paperforge-progress-seg ${j.cls}`,
            attr: { style: `width:${B}%` },
          });
        }
      let D = y.createEl("div", { cls: "paperforge-ocr-counts" }),
        z = [
          { cls: "pending", value: c, label: "Pending" },
          { cls: "active", value: d, label: "Processing" },
          { cls: "done", value: s, label: "Done" },
          { cls: "failed", value: u, label: "Attention" },
        ];
      for (let j of z) {
        let B = D.createEl("div", { cls: "paperforge-ocr-count" });
        (B.createEl("div", {
          cls: "paperforge-ocr-count-value",
          text: j.value.toString(),
        }),
          B.createEl("div", {
            cls: "paperforge-ocr-count-label",
            text: j.label,
          }));
      }
    }
    let f = r.createEl("div", { cls: "paperforge-collection-actions" }),
      v = f.createEl("button", { cls: "paperforge-contextual-btn primary" });
    (v.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    }),
      v.createEl("span", { text: "Run OCR" }),
      v.addEventListener("click", () => {
        let y = G.find((b) => b.id === "paperforge-ocr");
        y && this._runAction(y, v);
      }));
    let S = f.createEl("button", { cls: "paperforge-contextual-btn" });
    (S.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    }),
      S.createEl("span", { text: "Sync Library" }),
      S.addEventListener("click", () => {
        let y = G.find((b) => b.id === "paperforge-sync");
        y && this._runAction(y, S);
      }));
    let x = f.createEl("button", { cls: "paperforge-contextual-btn warn" });
    (x.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BA",
    }),
      x.createEl("span", { text: "Redo OCR" }),
      x.addEventListener("click", () => {
        let y = G.find((b) => b.id === "paperforge-ocr-redo");
        y && this._runAction(y, x);
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
        }
      } finally {
        setTimeout(() => {
          this._contentEl && this._contentEl.removeClass("switching");
        }, 50);
      }
    }
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
      this._searchInput.addEventListener("input", () => {
        var s;
        let a = ((s = this._searchInput) == null ? void 0 : s.value) || "";
        a.startsWith("@") && !a.startsWith("@ ")
          ? (n.setText("@"), n.addClass("deep"))
          : (n.setText("M"), n.removeClass("deep"));
      }),
      this._searchInput.addEventListener("keydown", (a) => {
        a.key === "Enter" && (a.preventDefault(), this.executeSearch());
      }));
  }
  executeSearch() {
    if (!this._searchInput || !this._searchResultsEl) return;
    let e = this._searchInput.value.trim();
    if (!e) return;
    let t = e.startsWith("@"),
      r = t ? e.slice(1).trim() : e;
    if (!r) return;
    let n = t ? "retrieve" : "search";
    (this._searchResultsEl.empty(),
      this._searchResultsEl.createEl("div", {
        cls: "paperforge-search-loading",
        text: "Searching...",
      }));
    let a = this.app.vault.adapter,
      s = "";
    if (a && typeof a == "object" && "basePath" in a) {
      let m = a.basePath;
      s = typeof m == "string" ? m : "";
    }
    if (!s) {
      this._renderSearchError("Could not determine vault path");
      return;
    }
    let o = null,
      c = this.app.plugins;
    if (c && typeof c == "object" && "plugins" in c) {
      let m = c.plugins;
      if (m && typeof m == "object" && "paperforge" in m) {
        let E = m.paperforge;
        E && typeof E == "object" && "settings" in E && (o = E.settings);
      }
    }
    let { path: d, extraArgs: u = [] } = M(s, o, void 0, void 0),
      p = (0, ue.spawn)(d, [...u, "-m", "paperforge", n, r, "--json"], {
        cwd: s,
        timeout: 3e4,
      }),
      _ = [];
    (p.stdout.on("data", (m) => {
      _.push(m.toString("utf-8"));
    }),
      p.stderr.on("data", () => {}),
      p.on("close", (m) => {
        if (m !== 0) {
          this._renderSearchError(`Search failed (exit ${m})`);
          return;
        }
        let E = _.join(""),
          f = E.indexOf("{"),
          v = E.lastIndexOf("}"),
          S = "";
        if (f !== -1 && v > f) S = E.slice(f, v + 1);
        else {
          let x = E.indexOf("["),
            y = E.lastIndexOf("]");
          x !== -1 && y > x && (S = E.slice(x, y + 1));
        }
        if (!S) {
          this._renderSearchError("No JSON output from CLI");
          return;
        }
        try {
          let x = JSON.parse(S),
            y = [];
          if (Array.isArray(x)) y = x;
          else if (x && typeof x == "object" && "results" in x) {
            let b = x.results;
            y = Array.isArray(b) ? b : [];
          }
          this.renderSearchResults(y, t);
        } catch (x) {
          let y = x instanceof Error ? x.message : String(x);
          this._renderSearchError("Failed to parse results: " + y);
        }
      }),
      p.on("error", (m) => {
        this._renderSearchError("Process error: " + m.message);
      }));
  }
  renderSearchResults(e, t) {
    if (!this._searchResultsEl) return;
    if ((this._searchResultsEl.empty(), e.length === 0)) {
      this._searchResultsEl.createEl("div", {
        cls: "paperforge-search-empty",
        text: "No results found.",
      });
      return;
    }
    let r = this._searchResultsEl.createEl("div", {
      cls: "paperforge-search-results-header",
    });
    (r.createEl("span", {
      text: `${e.length} result${e.length !== 1 ? "s" : ""}`,
    }),
      r.createEl("span", {
        cls: "paperforge-search-mode",
        text: t ? "@" : "M",
      }));
    for (let n of e) {
      if (!n || typeof n != "object") continue;
      let a = n,
        s = this._searchResultsEl.createEl("div", {
          cls: "paperforge-search-result-card",
        }),
        o =
          typeof a.title == "string"
            ? a.title
            : typeof a.file_name == "string"
              ? a.file_name
              : "(untitled)",
        i = s.createEl("div", {
          cls: "paperforge-search-result-title",
          text: o,
        }),
        c = typeof a.file_path == "string" ? a.file_path : null;
      c &&
        i.addEventListener("click", () => {
          let u = this.app.vault.getAbstractFileByPath(c);
          u instanceof A.TFile && this.app.workspace.getLeaf(!1).openFile(u);
        });
      let d = s.createEl("div", { cls: "paperforge-search-result-meta" });
      if (
        (typeof a.authors == "string"
          ? d.createEl("span", {
              cls: "paperforge-search-result-author",
              text: a.authors,
            })
          : Array.isArray(a.authors) &&
            d.createEl("span", {
              cls: "paperforge-search-result-author",
              text: a.authors.slice(0, 3).join("; "),
            }),
        (typeof a.year == "number" || typeof a.year == "string") &&
          d.createEl("span", {
            cls: "paperforge-search-result-year",
            text: String(a.year),
          }),
        typeof a.journal == "string" &&
          a.journal &&
          d.createEl("span", {
            cls: "paperforge-search-result-journal",
            text: a.journal,
          }),
        a.score !== void 0)
      ) {
        let u = a.score,
          p = typeof u == "number" ? u.toFixed(3) : String(u);
        d.createEl("span", {
          cls: "paperforge-search-result-score",
          text: "Score: " + p,
        });
      }
      if (
        (typeof a.domain == "string" &&
          a.domain &&
          s.createEl("span", {
            cls: "paperforge-search-result-tag",
            text: a.domain,
          }),
        typeof a.abstract == "string" && a.abstract)
      ) {
        let u = a.abstract;
        s.createEl("div", {
          cls: "paperforge-search-result-abstract",
          text: u.length > 200 ? u.slice(0, 200) + "..." : u,
        });
      }
      if (t && typeof a.matched_text == "string" && a.matched_text) {
        let u = a.matched_text;
        s.createEl("div", {
          cls: "paperforge-search-result-source",
          text: u.length > 300 ? u.slice(0, 300) + "..." : u,
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
    var p, _;
    if (e.disabled) {
      new A.Notice(
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
      let m = this.app.workspace.getActiveFile(),
        E = null;
      if (m) {
        let f = this.app.metadataCache.getFileCache(m);
        if (
          (f && f.frontmatter && f.frontmatter.zotero_key
            ? (E = f.frontmatter.zotero_key)
            : (E = this._extractZoteroKeyFromPath(m.path)),
          E)
        )
          n = [...n, E];
        else if (f && f.frontmatter) {
          (this._showMessage(
            "[!!] No zotero_key in active note frontmatter",
            "error"
          ),
            new A.Notice(
              "[!!] Open a paper note with a zotero_key in its frontmatter first",
              6e3
            ),
            t.removeClass("running"));
          return;
        } else {
          (this._showMessage("[!!] No frontmatter in active note", "error"),
            new A.Notice(
              "[!!] The active note has no frontmatter with a zotero_key",
              6e3
            ),
            t.removeClass("running"));
          return;
        }
      } else {
        (this._showMessage("[!!] No active note open", "error"),
          new A.Notice(
            "[!!] Open a paper note with a zotero_key in its frontmatter first",
            6e3
          ),
          t.removeClass("running"));
        return;
      }
    }
    e.needsFilter && (n = [...n, "--all"]);
    let a = e.needsFilter ? 6e4 : e.needsKey ? 3e4 : 6e5,
      { path: s, extraArgs: o = [] } = M(
        r,
        (_ =
          (p = this.app.plugins.plugins.paperforge) == null
            ? void 0
            : p.settings) != null
          ? _
          : null,
        void 0,
        void 0
      ),
      i = (0, ue.spawn)(s, [...o, "-m", "paperforge", e.cmd, ...n], {
        cwd: r,
        timeout: a,
      }),
      c = [],
      d = Date.now(),
      u = setInterval(() => this._fetchStats(!0), 4e3);
    (i.stdout.on("data", (m) => {
      let E = m
        .toString("utf-8")
        .split(
          `
`
        )
        .filter(Boolean);
      for (let f of E) {
        let v = f.trim();
        v &&
          (c.push(v),
          this._showMessage(
            c.slice(-8).join(`
`),
            "running"
          ));
      }
    }),
      i.stderr.on("data", (m) => {
        let E = m
          .toString("utf-8")
          .split(
            `
`
          )
          .filter(Boolean);
        for (let f of E) {
          if (f.includes("\r") || f.includes("%") || f.includes("\u2588"))
            continue;
          let v = f.trim();
          v &&
            !v.match(/^\d+%|^\|/) &&
            (c.push(v),
            this._showMessage(
              c.slice(-8).join(`
`),
              "running"
            ));
        }
      }),
      i.on("close", (m) => {
        (clearInterval(u), t.removeClass("running"));
        let E = ((Date.now() - d) / 1e3).toFixed(1);
        if (m !== 0) {
          let f = c.slice(-3).join(" | ") || "exit code " + m;
          (e.cmd === "repair" || e.cmd === "ocr") && m === 1
            ? (this._showMessage("[WARN] " + f, "running"),
              new A.Notice("[WARN] " + e.cmd + " partial: " + f, 8e3),
              this._fetchStats(!0))
            : (this._showMessage("[!!] " + f, "error"),
              new A.Notice("[!!] " + e.cmd + " failed: " + f, 8e3));
        } else if (e.needsKey || e.needsFilter) {
          let f = c.join(`
`);
          if (f.trim())
            try {
              (JSON.parse(f),
                navigator.clipboard
                  .writeText(f)
                  .then(() => {
                    let v = `${E}s \u2014 ${f.length} chars copied`;
                    (this._showMessage("[OK] " + e.title + ": " + v, "ok"),
                      new A.Notice(
                        "[OK] " + e.okMsg + " \u2014 " + f.length + " chars"
                      ));
                  })
                  .catch((v) => {
                    (this._showMessage(
                      "[!!] Clipboard write failed: " + v.message,
                      "error"
                    ),
                      new A.Notice("[!!] Clipboard error", 6e3));
                  }));
            } catch (v) {
              (this._showMessage("[!!] Invalid JSON from " + e.title, "error"),
                new A.Notice(
                  "[!!] " +
                    e.title +
                    " returned invalid JSON: " +
                    v.message.slice(0, 100),
                  8e3
                ));
            }
          else
            (this._showMessage("[!!] No output from context command", "error"),
              new A.Notice("[!!] Context command returned empty output", 8e3));
          this._fetchStats(!0);
        } else {
          let v =
              c.filter((x) => x.match(/updated \d+/)).pop() ||
              c[c.length - 1] ||
              "",
            S = `${E}s \u2014 ${v}`;
          (this._showMessage("[OK] " + e.title + ": " + S, "ok"),
            new A.Notice("[OK] " + e.okMsg),
            this._contentEl && this._contentEl.removeClass("switching"),
            (this._cachedStats = null));
          try {
            this._fetchStats(!1);
          } catch (x) {
            console.log("[PF] fetchStats error:", x);
          }
          (console.log("[PF] close cmd=" + e.cmd + " id=" + e.id),
            e.cmd === "sync" &&
              Me(this.app, this.app.plugins.plugins.paperforge, r));
        }
      }),
      i.on("error", (m) => {
        (t.removeClass("running"),
          this._contentEl && this._contentEl.removeClass("switching"),
          this._showMessage("[!!] " + m.message, "error"),
          new A.Notice("[!!] Cannot start: " + m.message, 8e3));
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
            a = r.filePath;
          (this._currentMode === n && this._currentFilePath === a) ||
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
var $e = class extends V.Plugin {
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
      tt(this.app),
      this.registerView(ge, (t) => new ve(t)));
    try {
      (0, V.addIcon)(Se, Qe);
    } catch (t) {}
    (this.addRibbonIcon(Se, "PaperForge Dashboard", () => ve.open(this)),
      G.find((t) => t.id === "paperforge-ocr-redo") &&
        this.addRibbonIcon("reset", "PaperForge: Redo OCR", () => {
          let t = this.app.vault.adapter.basePath;
          new V.Notice("PaperForge: Redo OCR starting...");
          let { path: r, extraArgs: n } = M(t, this.settings, void 0, void 0);
          (0, ae.execFile)(
            r,
            [...n, "-m", "paperforge", "ocr", "redo"],
            { cwd: t, timeout: 6e5 },
            (a, s, o) => {
              if (a) {
                new V.Notice("PaperForge: Redo OCR failed");
                return;
              }
              new V.Notice("PaperForge: Redo OCR done");
            }
          );
        }),
      this.addSettingTab(new Ne(this.app, this)),
      this.addCommand({
        id: "paperforge-status-panel",
        name: `PaperForge: ${l("guide_open")}`,
        callback: () => ve.open(this),
      }));
    for (let t of G)
      this.addCommand({
        id: t.id,
        name: `PaperForge: ${t.title}`,
        callback: () => {
          if (t.disabled) {
            new V.Notice(
              `[i] ${t.disabledMsg || "This action is not yet available."}`,
              6e3
            );
            return;
          }
          let r = this.app.vault.adapter.basePath;
          new V.Notice(`PaperForge: running ${t.cmd}...`);
          let { path: n, extraArgs: a = [] } = M(
              r,
              this.settings,
              void 0,
              void 0
            ),
            s = Array.isArray(t.args) ? [...t.args] : [];
          (0, ae.execFile)(
            n,
            [...a, "-m", "paperforge", t.cmd, ...s],
            { cwd: r, timeout: 3e5 },
            (o, i, c) => {
              if (o) {
                new V.Notice(
                  `[!!] ${t.cmd} failed: ${(c || o.message).slice(0, 120)}`,
                  8e3
                );
                return;
              }
              new V.Notice(
                `[OK] ${
                  t.okMsg ||
                  i
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
    let r = ne(e).memoryStatePath;
    if (!$.existsSync(r)) {
      let n = M(e, this.settings, void 0, void 0);
      [
        ["runtime-health", "--json"],
        ["memory", "status", "--json"],
        ["embed", "status", "--json"],
      ].forEach((s) => {
        let o = [...n.extraArgs, "-m", "paperforge", "--vault", e, ...s];
        (0, ae.execFile)(
          n.path,
          o,
          { cwd: e, timeout: 6e4, windowsHide: !0 },
          () => {}
        );
      });
    }
  }
  _autoUpdate() {
    let e = this.app.vault.adapter.basePath,
      { path: t, extraArgs: r = [] } = M(e, this.settings, void 0, void 0),
      n = this.manifest.version,
      a = `paperforge==${n}`,
      s = `git+https://github.com/LLLin000/PaperForge.git@${n}`,
      o = (i, c) => {
        (0, ae.spawn)(t, [...r, "-m", "pip", "install", "--upgrade", i], {
          cwd: e,
          timeout: 12e4,
          env: fe(),
        }).on("close", (u) => c(u === 0));
      };
    (0, ae.execFile)(
      t,
      [...r, "-c", "import paperforge; print(paperforge.__version__)"],
      { cwd: e, timeout: 1e4 },
      (i, c) => {
        let d = (p) => {
          (console.log(
            `[PaperForge] Auto-update: trying PyPI (paperforge==${n})`
          ),
            o(a, (_) => {
              if (_) {
                (console.log("[PaperForge] Auto-update: installed via PyPI"),
                  new V.Notice(`[OK] PaperForge CLI ${p}`, 5e3));
                return;
              }
              (console.warn(
                "[PaperForge] Auto-update: PyPI failed, falling back to git..."
              ),
                o(s, (m) => {
                  m &&
                    (console.log("[PaperForge] Auto-update: installed via git"),
                    new V.Notice(`[OK] PaperForge CLI ${p} (via git)`, 5e3));
                }));
            }));
        };
        if (i) {
          d("installed");
          return;
        }
        let u = c.trim();
        u !== n && d(`${u} -> ${n}`);
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
    let t = ne(e).exportsDir;
    if (!$.existsSync(t)) return;
    let r = 0;
    try {
      $.readdirSync(t).forEach((n) => {
        if (!n.endsWith(".json")) return;
        let a = $.statSync(xe.join(t, n));
        a.mtimeMs > r && (r = a.mtimeMs);
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
    let t = M(e, this.settings, void 0, void 0);
    if (!t.path) {
      this._autoSyncRunning = !1;
      return;
    }
    let r = `"${t.path}" -m paperforge --vault "${e}" sync`;
    (0, ae.exec)(r, { timeout: 12e4, encoding: "utf-8" }, (n, a, s) => {
      ((this._autoSyncRunning = !1),
        (this._memoryStatusText = null),
        n || (this._lastSyncTime = new Date().toLocaleTimeString()));
      try {
        let o = ne(e).exportsDir,
          i = 0;
        ($.readdirSync(o).forEach((c) => {
          c.endsWith(".json") &&
            (i = Math.max(i, $.statSync(xe.join(o, c)).mtimeMs));
        }),
          (this._lastExportMtime = i));
      } catch (o) {}
    });
  }
  _checkOcr(e) {
    if (this._autoSyncRunning) return;
    let t = ne(e).ocrDir;
    if ($.existsSync(t))
      try {
        $.readdirSync(t, { withFileTypes: !0 }).forEach((r) => {
          if (!r.isDirectory()) return;
          let n = xe.join(t, r.name, "meta.json");
          if (!$.existsSync(n)) return;
          let a = $.statSync(n),
            s = this._lastOcrMtimes[r.name] || 0;
          if (
            a.mtimeMs <= s ||
            ((this._lastOcrMtimes[r.name] = a.mtimeMs), this._autoSyncRunning)
          )
            return;
          this._autoSyncRunning = !0;
          let o = M(e, this.settings, void 0, void 0);
          if (!o.path) {
            this._autoSyncRunning = !1;
            return;
          }
          let i = `"${o.path}" -m paperforge --vault "${e}" sync`;
          (0, ae.exec)(i, { timeout: 3e4, encoding: "utf-8" }, () => {
            ((this._autoSyncRunning = !1), (this._memoryStatusText = null));
          });
        });
      } catch (r) {}
  }
  readPaperforgeJson() {
    let e = this.app.vault.adapter.basePath,
      t = xe.join(e, "paperforge.json"),
      r = {
        system_dir: "System",
        resources_dir: "Resources",
        literature_dir: "Literature",
        base_dir: "Bases",
      };
    try {
      if (!$.existsSync(t)) return r;
      let n = $.readFileSync(t, "utf-8"),
        a = JSON.parse(n),
        s = a.vault_config || {};
      return {
        system_dir: s.system_dir || a.system_dir || r.system_dir,
        resources_dir: s.resources_dir || a.resources_dir || r.resources_dir,
        literature_dir:
          s.literature_dir || a.literature_dir || r.literature_dir,
        base_dir: s.base_dir || a.base_dir || r.base_dir,
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
      r = xe.join(t, "paperforge.json"),
      n = {};
    try {
      $.existsSync(r) && (n = JSON.parse($.readFileSync(r, "utf-8")));
    } catch (s) {
      console.warn("PaperForge: Failed to read paperforge.json for update", s);
    }
    (!n.vault_config || typeof n.vault_config != "object") &&
      (n.vault_config = {});
    let a = ["system_dir", "resources_dir", "literature_dir", "base_dir"];
    for (let s of a) e[s] !== void 0 && (n.vault_config[s] = e[s]);
    n.schema_version || (n.schema_version = "2");
    for (let s of a) delete n[s];
    try {
      if (
        ($.writeFileSync(r, JSON.stringify(n, null, 2), "utf-8"), this.settings)
      ) {
        let s = this.readPaperforgeJson();
        ((this.settings.system_dir = s.system_dir),
          (this.settings.resources_dir = s.resources_dir),
          (this.settings.literature_dir = s.literature_dir),
          (this.settings.base_dir = s.base_dir));
      }
    } catch (s) {
      (console.error("PaperForge: Failed to write paperforge.json", s),
        new V.Notice(
          "PaperForge: Failed to save configuration to paperforge.json"
        ));
    }
  }
  onunload() {
    (this._pollTimer && clearInterval(this._pollTimer),
      this.app.workspace.detachLeavesOfType(ge));
  }
  async loadSettings() {
    ((this.settings = Object.assign({}, Pe, await this.loadData())),
      this.settings.features &&
        Pe.features &&
        (this.settings.features = Object.assign(
          {},
          Pe.features,
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
      $.existsSync(t)
        ? (this.settings._python_path_stale = !1)
        : (console.warn(
            `PaperForge: Saved python_path "${t}" no longer exists - showing stale warning`
          ),
          (this.settings._python_path_stale = !0));
    }
  }
  async saveSettings() {
    let e = {};
    for (let t of Object.keys(Pe))
      t in this.settings && (e[t] = this.settings[t]);
    await this.saveData(e);
  }
  _checkReleaseNotes() {
    let e = this.manifest.version;
    if (this.settings.last_seen_version === e) return;
    let a = (Ke().versions || []).find((o) => o.version === e);
    class s extends V.Modal {
      constructor(i, c) {
        (super(i), (this._entry = c));
      }
      onOpen() {
        let { contentEl: i } = this;
        if (
          (i.createEl("h2", {
            text: `PaperForge v${e} \u66F4\u65B0\u8BF4\u660E`,
          }),
          this._entry)
        ) {
          if (
            (i.createEl("p", {
              text: this._entry.title,
              cls: "paperforge-modal-subtitle",
            }),
            this._entry.breaking_or_migration &&
              this._entry.breaking_or_migration.length > 0)
          ) {
            i.createEl("h4", {
              text: "\u884C\u4E3A\u53D8\u66F4 / \u8FC1\u79FB\u6CE8\u610F",
            });
            for (let c of this._entry.breaking_or_migration)
              i.createEl("p", {
                text: `\u2022 ${c}`,
                cls: "paperforge-modal-item",
              });
          }
          if (this._entry.new_features && this._entry.new_features.length > 0) {
            i.createEl("h4", { text: "\u65B0\u529F\u80FD" });
            for (let c of this._entry.new_features)
              i.createEl("p", {
                text: `\u2022 ${c}`,
                cls: "paperforge-modal-item",
              });
          }
          if (this._entry.fixes && this._entry.fixes.length > 0) {
            i.createEl("h4", { text: "\u4FEE\u590D" });
            for (let c of this._entry.fixes)
              i.createEl("p", {
                text: `\u2022 ${c}`,
                cls: "paperforge-modal-item",
              });
          }
          if (
            this._entry.recommended_actions &&
            this._entry.recommended_actions.length > 0
          ) {
            let c = i.createEl("div", {
              cls: "paperforge-release-recommended",
            });
            (c.createEl("h4", { text: "\u5EFA\u8BAE\u64CD\u4F5C", cls: "" }),
              (c.style.marginBottom = "8px"));
            for (let d of this._entry.recommended_actions)
              c.createEl("p", {
                text: `\u2022 ${d}`,
                cls: "paperforge-release-item-bold",
              });
          }
        } else
          i.createEl("p", {
            text:
              "\u7248\u672C\u5DF2\u66F4\u65B0\u81F3 v" +
              e +
              "\uFF0C\u8BF7\u524D\u5F80\u8BBE\u7F6E \u2192 \u66F4\u65B0\u4E0E\u624B\u518C \u67E5\u770B\u5B8C\u6574\u66F4\u65B0\u8BB0\u5F55\u3002",
          });
        new V.Setting(i).addButton((c) =>
          c
            .setButtonText("\u77E5\u9053\u4E86")
            .setCta()
            .onClick(() => {
              this.close();
            })
        );
      }
      onClose() {
        let { contentEl: i } = this;
        i.empty();
      }
    }
    (new s(this.app, a).open(),
      (this.settings.last_seen_version = e),
      this.saveSettings());
  }
};
