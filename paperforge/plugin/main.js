const { Plugin, Notice, ItemView, Modal, Setting, PluginSettingTab, addIcon } = require('obsidian');
const { exec, execFile } = require('node:child_process');
const fs = require('fs');
const path = require('path');

const VIEW_TYPE_PAPERFORGE = 'paperforge-status';
const PF_ICON_ID = 'paperforge';
const PF_RIBBON_SVG = `
    <path d="M62 10H26c-4.4 0-8 3.6-8 8v64c0 4.4 3.6 8 8 8h48c4.4 0 8-3.6 8-8V30z" fill="none" stroke="currentColor" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M62 10v20h20" fill="none" stroke="currentColor" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
    <rect x="32" y="38" width="36" height="28" rx="6" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M42 46v12" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"/>
    <path d="M50 42v20" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"/>
    <path d="M58 48v8" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"/>`;

// ── i18n: language pack (auto-detected from Obsidian config) ──
const LANG = {
    en: { header_title:'PaperForge',desc:'Obsidian + Zotero literature pipeline.',setup_done:'✓ PaperForge environment configured',setup_pending:'Not installed — complete preparation and open the wizard',section_prep:'Prerequisites',section_prep_desc:'Before first use, complete the following:',section_guide:'Usage',section_config:'Configuration',prep_python:'Python 3.10+',prep_python_desc:'Must be callable from command line. Click below to auto-detect.',prep_zotero:'Zotero Desktop',prep_zotero_desc:'Install Zotero (https://www.zotero.org)',prep_bbt:'Better BibTeX',prep_bbt_desc:'Zotero → Tools → Add-ons → Install Better BibTeX',prep_export:'BBT Auto-export',prep_export_desc:'Right-click collection → Export → BetterBibTeX JSON → Keep updated → to:',prep_key:'PaddleOCR Key',prep_key_desc:'Get free key at https://aistudio.baidu.com/paddleocr',guide_open:'Open Dashboard',guide_open_desc:'Ctrl+P → "PaperForge: Open Dashboard", or sidebar book icon',guide_sync:'Sync Literature',guide_sync_desc:'Dashboard → Sync Library — pull from Zotero, generate notes',guide_ocr:'Run OCR',guide_ocr_desc:'Dashboard → Run OCR — extract PDF text & figures',btn_install:'Open Wizard',btn_reconfig:'Reconfigure',btn_install_desc:'Auto-detect environment, then open setup wizard',btn_reconfig_desc:'Re-run wizard to change directories or keys',wizard_step1:'Overview',wizard_step2:'Dirs',wizard_step3:'Agent',wizard_step4:'Install',wizard_step5:'Done',wizard_title:'PaperForge Setup Wizard',wizard_intro:'This wizard will guide you through the complete setup.',wizard_dir_hint:'The resources directory is the root for all literature data. Sub-directories inside it:',wizard_dir_sub_hint:'Two sub-directories within resources:',wizard_sys_hint:'System directories (at vault root):',wizard_agent_hint:'Select your AI Agent platform. Skill files deploy in the correct format.',wizard_keys_hint:'API key and Zotero:',wizard_preview:'System/agent files at vault root. Literature (notes, index) under resources.',dir_vault:'Vault Path',dir_resources:'Resource Dir',dir_notes:'Notes Dir',dir_index:'Index Dir',dir_system:'System Dir',dir_base:'Base Dir',field_paddleocr:'PaddleOCR API Key',field_zotero_data:'Zotero Data Dir',field_zotero_placeholder:'Optional, for auto PDF detection',label_agent:'Agent Platform',check_python_ok:'Ready',check_python_fail:'Not found',check_zotero_ok:'Found',check_zotero_fail:'Not detected',check_bbt_ok:'Installed',check_bbt_fail:'Not detected',install_btn:'Install',install_btn_running:'Installing...',install_btn_retry:'Retry',install_complete:'✓ Installation complete!',install_failed:'✗ Installation failed: ',complete_title:'✓ Setup Complete',complete_summary:'Configuration',complete_next:'Next Steps',complete_step1:'Open Dashboard',complete_step1_desc:'Ctrl+P → "PaperForge: Open Dashboard" or sidebar book icon',complete_step2:'Sync Literature',complete_step2_desc:'Dashboard → Sync Library — pull from Zotero',complete_step3:'Run OCR',complete_step3_desc:'Dashboard → Run OCR — extract full text & figures',complete_step4:'Configure BBT Auto-export',nav_prev:'← Back',nav_next:'Next →',nav_close:'Close',validate_fail:'Validation failed',validate_vault:'Vault path not set',validate_resources:'Resource dir not set',validate_notes:'Notes dir not set',validate_index:'Index dir not set',validate_base:'Base dir not set',validate_key:'API key not set',validate_system:'System dir not set',notice_python_missing:'Python not detected. Install Python 3.10+ and add to PATH.',notice_check_fail:'Missing: ',panel_actions:'Quick Actions',action_running:'Running ',api_key_set:'Configured ✓',api_key_missing:'Not configured ✗',not_set:'Not set',jump_to_deep_reading:'Open Deep Reading',deep_reading_not_found:'Deep reading file not found', },
    zh: { header_title:'PaperForge',desc:'Obsidian + Zotero 文献管理流水线。自动同步文献、生成笔记、OCR 提取全文，一站式文献精读工作流。',setup_done:'✓ PaperForge 环境已配置完成',setup_pending:'尚未安装，完成安装准备后点击安装向导',section_prep:'安装准备',section_prep_desc:'首次使用前，请依次完成以下准备：',section_guide:'操作方式',section_config:'当前配置',prep_python:'Python 3.10+',prep_python_desc:'确保 Python 可命令行调用。点击下方按钮自动检测。',prep_zotero:'Zotero 桌面版',prep_zotero_desc:'安装 Zotero (https://www.zotero.org)',prep_bbt:'Better BibTeX',prep_bbt_desc:'Zotero → 工具 → 插件 → 安装 Better BibTeX',prep_export:'BBT 自动导出',prep_export_desc:'右键文献子分类 → 导出分类 → BetterBibTeX JSON → 勾选保持更新 → 导出到（JSON 文件名即为 Base 名）：',prep_key:'PaddleOCR Key',prep_key_desc:'在 https://aistudio.baidu.com/paddleocr 获取 API Key',guide_open:'打开 Dashboard',guide_open_desc:'Ctrl+P → 输入 PaperForge: Open Dashboard，或点左侧书本图标',guide_sync:'同步文献',guide_sync_desc:'Dashboard 中点 Sync Library，从 Zotero 拉取文献生成笔记',guide_ocr:'运行 OCR',guide_ocr_desc:'Dashboard 中点 Run OCR，提取 PDF 全文与图表',btn_install:'打开安装向导',btn_reconfig:'重新配置',btn_install_desc:'自动检测 Python + 前置环境，通过后打开分步安装向导',btn_reconfig_desc:'重新运行安装向导，修改目录或密钥配置',wizard_step1:'概览',wizard_step2:'目录',wizard_step3:'Agent',wizard_step4:'安装',wizard_step5:'完成',wizard_title:'PaperForge 安装向导',wizard_intro:'本向导将引导您完成 PaperForge 环境的完整配置。安装过程会自动创建所有目录结构，无需手动操作。',wizard_dir_hint:'资源目录是文献数据的统一根目录，以下子目录将创建在其内部：',wizard_dir_sub_hint:'资源目录内的两个子目录：',wizard_sys_hint:'独立于资源目录的系统文件：',wizard_agent_hint:'选择你使用的 AI Agent 平台，安装时将按对应格式部署技能文件：',wizard_keys_hint:'以下为 API 密钥与 Zotero 配置：',wizard_preview:'系统文件和 Agent 配置位于 Vault 根目录下。文献数据（正文、索引）统一存放在资源目录内。安装后仍可在设置中修改。',dir_vault:'Vault 路径',dir_resources:'资源目录',dir_notes:'正文目录',dir_index:'索引目录',dir_system:'系统目录',dir_base:'Base 目录',field_paddleocr:'PaddleOCR API 密钥',field_zotero_data:'Zotero 数据目录',field_zotero_placeholder:'可选，用于自动检测 PDF',label_agent:'Agent 平台',check_python_ok:'已就绪',check_python_fail:'未安装',check_zotero_ok:'已安装',check_zotero_fail:'未检测到',check_bbt_ok:'已安装',check_bbt_fail:'未检测到',install_btn:'开始安装',install_btn_running:'正在安装...',install_btn_retry:'重试',install_complete:'✓ 安装完成！',install_failed:'✗ 安装失败：',complete_title:'✓ PaperForge 安装完成',complete_summary:'当前完整配置',complete_next:'下一步操作',complete_step1:'打开 PaperForge Dashboard',complete_step1_desc:'Ctrl+P → 输入 PaperForge: Open Dashboard，或点左侧书本图标',complete_step2:'同步文献',complete_step2_desc:'Dashboard 中点 Sync Library，从 Zotero 拉取文献生成笔记',complete_step3:'运行 OCR',complete_step3_desc:'Dashboard 中点 Run OCR，提取 PDF 全文与图表',complete_step4:'配置 BBT 自动导出',nav_prev:'← 上一步',nav_next:'下一步 →',nav_close:'关闭',validate_fail:'配置验证失败',validate_vault:'Vault 路径未填写',validate_resources:'资源目录未填写',validate_notes:'正文目录未填写',validate_index:'索引目录未填写',validate_base:'Base 目录未填写',validate_key:'PaddleOCR API 密钥未填写',validate_zotero:'Zotero 数据目录为必填项',validate_system:'系统目录未填写',notice_python_missing:'Python 未检测到，请先安装 Python 3.10+ 并加入 PATH',notice_check_fail:'未通过: ',panel_actions:'快捷操作',action_running:'正在执行 ',api_key_set:'已配置 ✓',api_key_missing:'未配置 ✗',not_set:'未设置',jump_to_deep_reading:'跳转到精读',deep_reading_not_found:'精读文件未找到', }
};

let T = LANG.zh;

Object.assign(LANG.en, {
    desc: 'Obsidian + Zotero literature pipeline. Sync papers, generate notes, run OCR, and read deeply in one place.',
    setup_done: 'PaperForge environment is ready',
    setup_pending: 'Not installed yet. Finish the preparation items below, then open the wizard.',
    section_prep: 'Preparation',
    section_prep_desc: 'Before first use, finish these 4 preparation items. Better BibTeX auto-export is configured after setup:',
    section_guide: 'How To Use',
    section_config: 'Current Configuration',
    prep_python_desc: 'Python must be available from the command line. If you are not sure, click below to auto-detect.',
    prep_zotero_desc: 'Install Zotero from https://www.zotero.org',
    prep_bbt_desc: 'In Zotero: Tools -> Add-ons -> install Better BibTeX.',
    prep_export: 'Better BibTeX Auto-export',
    prep_export_desc: 'In Zotero, right-click the collection you want to sync -> Export Collection -> BetterBibTeX JSON -> enable "Keep updated" -> save the JSON file into the exports folder shown below. Obsidian Base views will use the JSON filename as the Base name:',
    prep_export_path_label: 'Save the exported JSON file into this folder:',
    prep_key_desc: 'Get your API key from https://aistudio.baidu.com/paddleocr',
    guide_open: 'Open Main Panel',
    guide_open_desc: 'Press Ctrl+P and run "PaperForge: Open Main Panel", or click the PaperForge icon in the left sidebar.',
    guide_sync_desc: 'After Better BibTeX JSON export is configured, click Sync Library to import papers from Zotero into Obsidian and generate notes automatically.',
    guide_ocr_desc: 'In the main panel, click Run OCR to extract full text and figures from PDFs for later reading and analysis.',
    btn_install: 'Open Setup Wizard',
    btn_install_desc: 'Check whether the environment is ready, then open the step-by-step setup wizard',
    btn_reconfig_desc: 'Open the setup wizard again to change directories, platform, or API keys',
    wizard_step2: 'Directory Setup',
    wizard_step3: 'Platform & Keys',
    wizard_intro: 'This wizard walks you through the full setup. In most cases, the default values are fine to keep.',
    wizard_dir_hint: 'PaperForge stores user-facing literature data under the resources directory. These folders will live there:',
    wizard_dir_sub_hint: 'Resolved folder preview based on the names below:',
    wizard_sys_hint: 'These folders live at the vault root, outside the resources directory:',
    wizard_agent_hint: 'Choose the AI agent platform you use most often. PaperForge will place the matching command and skill files in the correct location.',
    wizard_keys_hint: 'Enter your PaddleOCR API key below. If you want PaperForge to auto-locate Zotero PDFs, you can also fill in the Zotero data directory.',
    wizard_preview: 'After installation, system files stay at the vault root while literature data stays under the resources directory.',
    wizard_safety: 'Safety: if the selected folders already contain files, setup preserves existing files and only creates missing PaperForge folders and files.',
    field_zotero_placeholder: 'Required. Path to Zotero data directory for PDF attachment resolution.',
    install_btn: 'Start Install',
    install_validating: 'Validating setup...',
    install_bootstrapping: 'PaperForge Python package not found. Installing automatically...',
    install_complete: 'Installation complete!',
    install_failed: 'Installation failed: ',
    complete_title: 'Setup Complete',
    complete_summary: 'Saved Configuration',
    complete_next: 'Recommended next steps',
    complete_step1_desc: 'Press Ctrl+P and run "PaperForge: Open Main Panel", or click the PaperForge icon in the left sidebar.',
    complete_step2_desc: 'In the main panel, click Sync Library to bring papers from Zotero into Obsidian and generate notes.',
    complete_step3_desc: 'In the Obsidian Base view, mark do_ocr:true on papers, then run OCR in the main panel.',
    complete_step4: 'Configure Better BibTeX Auto-export',
    complete_step4_desc: 'In Zotero, right-click the library or collection you want to sync -> Export -> Better BibTeX JSON -> enable "Keep updated".',
    complete_export_path: 'Save Better BibTeX JSON exports into:',
    nav_prev: 'Back',
    nav_next: 'Next',
    validate_fail: 'Please complete the required fields below',
    validate_vault: 'Vault path is required',
    validate_resources: 'Resources directory is required',
    validate_notes: 'Notes directory is required',
    validate_index: 'Index directory is required',
    validate_base: 'Base directory is required',
    validate_key: 'PaddleOCR API key is required',
    validate_zotero: 'Zotero data directory is required',
    validate_system: 'System directory is required',
    notice_python_missing: 'Python was not detected. Install Python 3.10+ and add it to PATH.',
    api_key_set: 'Entered',
    api_key_missing: 'Missing',
    not_set: 'Not entered',
    field_python_interp: 'Python Interpreter',
    field_python_custom: 'Custom Path',
    btn_validate: 'Validate',

    /* ── Runtime Health (Task 2) ── */
    runtime_health: 'Runtime Health',
    runtime_health_desc: 'Check whether the installed paperforge Python package matches the plugin version',
    runtime_health_plugin_ver: 'Plugin v{0}',
    runtime_health_package_ver: 'Python package v{0}',
    runtime_health_match: 'Match',
    runtime_health_mismatch: 'Mismatch',
    runtime_health_checking: 'Checking...',
    runtime_health_sync: 'Sync Runtime',
    runtime_health_syncing: 'Syncing...',
    runtime_health_sync_done: 'Runtime synced to v{0}',
    runtime_health_sync_fail: 'Sync failed: {0}',
    dashboard_drift_warning: 'PaperForge CLI (v{0}) differs from plugin (v{1}). Open Settings → Runtime Health to sync.',

    /* ── Copy Diagnostic (Task 3) ── */
    error_copy_diagnostic: 'Copy diagnostic',
    error_copied: 'Copied!',

    /* ── DASH-01: OCR Queue (Plan 54-001) ── */
    ocr_queue_add: 'Add to OCR Queue',
    ocr_queue_remove: 'Remove from OCR Queue',
    ocr_queue_added: 'Added to OCR queue',
    ocr_queue_removed: 'Removed from OCR queue',
    run_pending_ocr: 'Run All Pending OCR',
    run_pending_ocr_desc: 'Run OCR on all papers waiting in the queue',
    no_pending_ocr: 'All OCR tasks done',

    /* ── DASH-02: /pf-deep Handoff (Plan 54-001) ── */
    copy_pf_deep_cmd: 'Copy /pf-deep Command',
    copied: 'Copied!',
    run_in_agent: 'Run in {0}',

    /* ── DASH-03: Privacy Warning (Plan 54-003) ── */
    ocr_privacy_title: 'OCR Privacy Notice',
    ocr_privacy_warning: 'OCR will upload PDFs to the PaddleOCR API for processing. Do not upload sensitive or confidential documents.',
    ocr_understand: 'I Understand',
});

Object.assign(LANG.zh, {
    desc: 'Obsidian + Zotero 文献管理流水线。自动同步文献、生成笔记、OCR 提取全文，一站式完成文献整理与精读。',
    setup_done: 'PaperForge 环境已准备完成',
    setup_pending: '尚未完成安装。请先完成下面的准备，再打开安装向导。',
    section_prep_desc: '第一次使用前，请先完成下面 4 项准备。Better BibTeX 自动导出放在安装完成后配置：',
    prep_python_desc: '确认系统可以直接运行 Python 命令。如果不确定，点击下方按钮自动检测。',
    prep_zotero_desc: '先安装 Zotero：https://www.zotero.org',
    prep_bbt_desc: '在 Zotero 中依次打开：工具 -> 插件 -> 安装 Better BibTeX。',
    prep_export: 'Better BibTeX 自动导出设置',
    prep_export_desc: '在 Zotero 中右键需要同步的文献分类 -> 选择“导出分类” -> 选择 BetterBibTeX JSON -> 勾选“保持更新” -> 把导出的 JSON 文件保存到下面这个 exports 文件夹。之后 Obsidian Base 会根据 JSON 文件名自动建立对应名称：',
    prep_export_path_label: '请把导出的 JSON 文件保存到这个文件夹：',
    guide_open: '打开主面板',
    guide_open_desc: '按 Ctrl+P，输入 PaperForge: 打开主面板；或点击左侧的 PaperForge 图标。',
    guide_sync_desc: '先完成 Better BibTeX JSON 自动导出配置，再在主面板点击 Sync Library，把 Zotero 文献同步到 Obsidian 并自动生成笔记。',
    guide_ocr_desc: '在主面板点击 Run OCR，从 PDF 中提取全文和图表，供后续精读和分析使用。',
    btn_install_desc: '先检查环境是否就绪，再打开分步安装向导',
    btn_reconfig_desc: '重新打开安装向导，修改目录、平台或密钥配置',
    wizard_step2: '目录配置',
    wizard_step3: '平台与密钥',
    wizard_intro: '这个向导会一步步帮你完成安装。大部分选项保持默认即可，安装时会自动创建所需目录。',
    wizard_dir_hint: '资源目录用于存放用户可见的文献数据。下面这些目录都会位于资源目录内部：',
    wizard_dir_sub_hint: '根据下面的目录名，最终路径会是：',
    wizard_sys_hint: '这些目录位于 Vault 根目录，不属于资源目录：',
    wizard_agent_hint: '选择你平时使用的 AI Agent 平台。安装完成后，PaperForge 会把对应的命令和技能文件放到正确位置。',
    wizard_keys_hint: '下面填写 PaddleOCR API 密钥；如果你希望自动定位 Zotero 中的 PDF，也可以补充 Zotero 数据目录。',
    wizard_preview: '安装后：系统文件位于 Vault 根目录，文献数据统一放在资源目录内。以后仍可在设置页修改。',
    wizard_safety: '安全说明：如果你选择的目录里已经有文件，安装向导会保留已有内容，只补充缺失的 PaperForge 文件和目录。',
    field_zotero_placeholder: '必填。Zotero 数据目录路径，用于解析 PDF 附件位置。',
    install_validating: '正在校验安装环境...',
    install_bootstrapping: '未检测到 PaperForge Python 包，正在自动安装...',
    install_complete: '安装完成！',
    install_failed: '安装失败：',
    complete_title: 'PaperForge 安装完成',
    complete_summary: '已保存的安装配置',
    complete_next: '建议下一步',
    complete_step1_desc: '按 Ctrl+P，输入 PaperForge: 打开主面板；或点击左侧的 PaperForge 图标。',
    complete_step2_desc: '在主面板点击 Sync Library，把 Zotero 文献同步到 Obsidian 并自动生成笔记。',
    complete_step3_desc: '在 Obsidian Base 视图中将文献的 do_ocr 设为 true，然后在主面板点击 Run OCR。',
    complete_step4: '配置 Better BibTeX 自动导出',
    complete_step4_desc: '在 Zotero 中右键要同步的文献库或分类 -> 导出 -> 选择 Better BibTeX JSON -> 勾选“保持更新”。',
    complete_export_path: 'Better BibTeX 导出的 JSON 文件请保存到：',
    nav_prev: '上一步',
    nav_next: '下一步',
    validate_fail: '下面这些必填项还没有填写完整',
    notice_python_missing: '未检测到 Python。请先安装 Python 3.10+，并确保它已加入 PATH。',
    api_key_set: '已填写',
    api_key_missing: '未填写',
    not_set: '未填写',
    field_python_interp: 'Python 解释器',
    field_python_custom: '自定义路径',
    btn_validate: '验证',

    /* ── Runtime Health (Task 2) ── */
    runtime_health: '运行时状态',
    runtime_health_desc: '检查已安装的 paperforge Python 包是否与插件版本一致',
    runtime_health_plugin_ver: '插件 v{0}',
    runtime_health_package_ver: 'Python 包 v{0}',
    runtime_health_match: '一致',
    runtime_health_mismatch: '不一致',
    runtime_health_checking: '正在检查...',
    runtime_health_sync: '同步运行时',
    runtime_health_syncing: '正在同步...',
    runtime_health_sync_done: '运行时已同步至 v{0}',
    runtime_health_sync_fail: '同步失败: {0}',
    dashboard_drift_warning: 'PaperForge CLI (v{0}) 与插件 (v{1}) 版本不一致，请打开设置 → 运行时状态进行同步。',

    /* ── Copy Diagnostic (Task 3) ── */
    error_copy_diagnostic: '复制诊断信息',
    error_copied: '已复制',

    /* ── DASH-01: OCR Queue (Plan 54-001) ── */
    ocr_queue_add: '加入 OCR 队列',
    ocr_queue_remove: '移出 OCR 队列',
    ocr_queue_added: '已加入 OCR 队列',
    ocr_queue_removed: '已移出 OCR 队列',
    run_pending_ocr: '运行所有待处理 OCR',
    run_pending_ocr_desc: '对队列中所有等待处理的文献运行 OCR',
    no_pending_ocr: '所有 OCR 任务已完成',

    /* ── DASH-02: /pf-deep Handoff (Plan 54-001) ── */
    copy_pf_deep_cmd: '复制 /pf-deep 命令',
    copied: '已复制！',
    run_in_agent: '在 {0} 中运行',

    /* ── DASH-03: Privacy Warning (Plan 54-003) ── */
    ocr_privacy_title: 'OCR 隐私提示',
    ocr_privacy_warning: 'OCR 将把 PDF 上传到 PaddleOCR API 进行处理。请不要上传包含敏感信息或无法外传的文献。',
    ocr_understand: '我知道了',
});

function langFromApp(app) {
    try {
        if (app && app.vault && typeof app.vault.getConfig === 'function') {
            const l = app.vault.getConfig('language');
            if (l && String(l).startsWith('zh')) return 'zh';
        }
    } catch {}
    try {
        if (typeof localStorage !== 'undefined') {
            const l = localStorage.getItem('language');
            if (l && String(l).startsWith('zh')) return 'zh';
        }
    } catch {}
    return 'zh';  // default Chinese
}

function t(key) { return (T && T[key]) || (LANG.en[key]) || key; }

const DEFAULT_SETTINGS = {
    vault_path: '',
    setup_complete: false,
    auto_update: true,
    agent_platform: 'opencode',
    language: '',
    paddleocr_api_key: '',
    zotero_data_dir: '',
    python_path: '',
};

const ACTIONS = [
    {
        id: 'paperforge-sync',
        title: 'Sync Library',
        desc: 'Pull new references from Zotero and generate literature notes',
        icon: '\u21BB',  // ↻
        cmd: 'sync',
        okMsg: 'Sync complete',
    },
    {
        id: 'paperforge-ocr',
        title: 'Run OCR',
        desc: 'Extract full text and figures from PDFs via PaddleOCR',
        icon: '\u229E',  // ⊞
        cmd: 'ocr',
        okMsg: 'OCR started',
    },
    {
        id: 'paperforge-doctor',
        title: 'Run Doctor',
        desc: 'Verify PaperForge setup \u2014 check configs, Zotero, paths, and index health',
        icon: '\u2695',  // ⚕
        cmd: 'doctor',
        okMsg: 'Doctor complete',
        disabled: true,
        disabledMsg: 'Run Doctor will be available in a future update.',
    },
    {
        id: 'paperforge-repair',
        title: 'Repair Issues',
        desc: 'Fix three-way state divergence, path errors, and rebuild index',
        icon: '\u21BA',  // ↺
        cmd: 'repair',
        args: ['--fix', '--fix-paths'],
        okMsg: 'Repair complete',
        disabled: true,
        disabledMsg: 'Repair Issues will be available in a future update.',
    },
    {
        id: 'paperforge-copy-context',
        title: 'Copy Context',
        desc: 'Copy this paper\u2019s canonical index entry JSON to clipboard for AI use',
        icon: '\u2139',  // ℹ
        cmd: 'context',
        needsKey: true,
        okMsg: 'Context copied',
    },
    {
        id: 'paperforge-copy-collection-context',
        title: 'Copy Collection Context',
        desc: 'Copy canonical index entries for all visible papers to clipboard',
        icon: '\u2261',  // ≡
        cmd: 'context',
        needsFilter: true,
        okMsg: 'Collection context copied',
    },
];

function resolvePythonExecutable(vaultPath, settings) {
    // 1. Manual override — absolute source of truth
    if (settings && settings.python_path && settings.python_path.trim()) {
        const manualPath = settings.python_path.trim();
        if (fs.existsSync(manualPath)) {
            return { path: manualPath, source: 'manual', extraArgs: [] };
        }
    }

    // 2. Venv candidates
    const venvCandidates = [
        path.join(vaultPath, '.paperforge-test-venv', 'Scripts', 'python.exe'),
        path.join(vaultPath, '.venv', 'Scripts', 'python.exe'),
        path.join(vaultPath, 'venv', 'Scripts', 'python.exe'),
    ];
    for (const candidate of venvCandidates) {
        try {
            if (fs.existsSync(candidate)) return { path: candidate, source: 'auto-detected', extraArgs: [] };
        } catch {}
    }

    // 3. System candidates — test each with --version, pick first that succeeds
    const { execFileSync } = require('node:child_process');
    const systemCandidates = [
        { path: 'py', extraArgs: ['-3'] },
        { path: 'python', extraArgs: [] },
        { path: 'python3', extraArgs: [] },
    ];
    for (const candidate of systemCandidates) {
        try {
            const verOut = execFileSync(candidate.path, [...candidate.extraArgs, '--version'], {
                encoding: 'utf-8',
                timeout: 5000,
                windowsHide: true,
            });
            if (verOut && verOut.toLowerCase().includes('python')) {
                return { path: candidate.path, source: 'auto-detected', extraArgs: candidate.extraArgs };
            }
        } catch {}
    }

    // 4. Last-resort fallback
    return { path: 'python', source: 'auto-detected', extraArgs: [] };
}

class PaperForgeStatusView extends ItemView {
    constructor(leaf) {
        super(leaf);
        this._currentMode = null;       // 'global' | 'paper' | 'collection' | 'deep-reading' (D-05)
        this._currentDomain = null;     // domain name when in collection mode (D-15)
        this._currentPaperKey = null;   // zotero_key when in per-paper mode (D-03)
        this._currentPaperEntry = null; // full entry when in per-paper mode
        this._currentFilePath = null;   // active file path for identity guard (D-06)
        this._cachedItems = null;       // lazy-loaded index items (Plan 28-01)
        this._modeSubscribers = [];     // event handler refs for cleanup
        this._leafChangeTimer = null;   // debounce timer for active-leaf-change
        this._ocrPrivacyShown = false;  // DASH-03: once-per-session privacy flag
    }

    getViewType() { return VIEW_TYPE_PAPERFORGE; }
    getDisplayText() { return 'PaperForge'; }
    getIcon() { return PF_ICON_ID; }

    async onOpen() {
        this._buildPanel();
        this._contentEl = this.containerEl.querySelector('.paperforge-content-area');
        this._modeSubscribers = [];
        this._leafChangeTimer = null;

        this._setupEventSubscriptions();

        // Fetch Python package version (once, not from index)
        this._fetchVersion();

        this._detectAndSwitch();
    }

    onClose() {
        // Unsubscribe from all event subscriptions (D-08, D-09)
        if (this._modeSubscribers && this._modeSubscribers.length > 0) {
            for (const sub of this._modeSubscribers) {
                if (sub.event === 'active-leaf-change') {
                    this.app.workspace.off('active-leaf-change', sub.ref);
                } else if (sub.event === 'modify') {
                    this.app.vault.off('modify', sub.ref);
                }
            }
            this._modeSubscribers = [];
        }

        // Clear debounce timer
        if (this._leafChangeTimer) {
            clearTimeout(this._leafChangeTimer);
            this._leafChangeTimer = null;
        }

        // Clear cached data
        this._cachedItems = null;
        this._cachedStats = null;
    }

    /* ---------------------------------------------------------------------- */
    /*  Build Panel                                                           */
    /* ---------------------------------------------------------------------- */
    _buildPanel() {
        const root = this.containerEl;
        root.empty();
        root.addClass('paperforge-status-panel');

        /* ── Header ── */
        const header = root.createEl('div', { cls: 'paperforge-header' });

        const headerLeft = header.createEl('div', { cls: 'paperforge-header-left' });
        headerLeft.createEl('div', { cls: 'paperforge-header-logo', text: 'P' });

        // Mode context area (populated by _renderModeHeader)
        this._modeContextEl = headerLeft.createEl('div', { cls: 'paperforge-mode-context' });

        this._headerTitle = headerLeft.createEl('h3', { cls: 'paperforge-header-title', text: 'PaperForge' });
        this._versionBadge = headerLeft.createEl('span', { cls: 'paperforge-header-badge', text: 'v\u2014' });

        const refreshBtn = header.createEl('button', { cls: 'paperforge-header-refresh', attr: { 'aria-label': 'Refresh' } });
        refreshBtn.innerHTML = '\u21BB';
        refreshBtn.addEventListener('click', () => {
            this._invalidateIndex();
            this._detectAndSwitch();
        });

        /* ── Status Message (command output) ── */
        this._messageEl = root.createEl('div', { cls: 'paperforge-message' });

        /* ── Mode-Switched Content Area (per D-06) ── */
        this._contentEl = root.createEl('div', { cls: 'paperforge-content-area' });

        /* ── Quick Actions (visible in all modes per D-07 / "Specific Ideas") ── */
        const actions = root.createEl('div', { cls: 'paperforge-actions-section' });
        actions.createEl('h4', { cls: 'paperforge-actions-title', text: 'Quick Actions' });
        this._actionsGrid = actions.createEl('div', { cls: 'paperforge-actions-grid' });
        this._renderActions();  // extracted so actions can be re-rendered per mode
    }

    /* ---------------------------------------------------------------------- */
    /*  Fetch & Render Stats                                                  */
    /* ---------------------------------------------------------------------- */
    _fetchVersion() {
        const vp = this.app.vault.adapter.basePath;
        const plugin = this.app.plugins.plugins['paperforge'];
        const { path: pythonExe, extraArgs = [] } = resolvePythonExecutable(vp, plugin?.settings);
        execFile(pythonExe, [...extraArgs, '-c', 'import paperforge; print(paperforge.__version__)'], { cwd: vp, timeout: 10000 }, (err, stdout) => {
            if (!err && stdout) {
                const v = stdout.trim();
                this._paperforgeVersion = v.startsWith('v') ? v : 'v' + v;
                if (this._versionBadge) this._versionBadge.setText(this._paperforgeVersion);

                // Check drift for dashboard banner
                const pluginVer = this.app.plugins.plugins['paperforge']?.manifest?.version;
                if (this._driftBannerEl && pluginVer && this._paperforgeVersion !== 'v' + pluginVer.replace(/^v/, '')) {
                    this._driftBannerEl.style.display = 'block';
                    this._driftBannerEl.setText(t('dashboard_drift_warning')
                        .replace('{0}', this._paperforgeVersion)
                        .replace('{1}', 'v' + pluginVer.replace(/^v/, '')));
                } else if (this._driftBannerEl) {
                    this._driftBannerEl.style.display = 'none';
                }
            }
        });
    }

    _fetchStats(quiet) {
        // Phase 25: Read canonical index JSON directly (D-05)
        if (!quiet && !this._cachedStats) {
            this._metricsEl.empty();
            this._metricsEl.createEl('div', { cls: 'paperforge-status-loading', text: 'Loading...' });
        } else if (quiet && !this._cachedStats) {
            return;
        }

        const vp = this.app.vault.adapter.basePath;
        const plugin = this.app.plugins.plugins['paperforge'];
        const systemDir = plugin?.settings?.system_dir || 'System';
        const indexPath = path.join(vp, systemDir, 'PaperForge', 'indexes', 'formal-library.json');

        try {
            const raw = fs.readFileSync(indexPath, 'utf-8');
            const index = JSON.parse(raw);
            const items = index.items || [];

            // D-06: Single-pass aggregation — no item references held after loop
            const lifecycleCounts = {};
            const healthCounts = {
                pdf_health: { healthy: 0, unhealthy: 0 },
                ocr_health: { healthy: 0, unhealthy: 0 },
                note_health: { healthy: 0, unhealthy: 0 },
                asset_health: { healthy: 0, unhealthy: 0 },
            };
            let ocrTotal = 0, ocrDone = 0, ocrPending = 0, ocrProcessing = 0, ocrFailed = 0;
            let formalNotes = 0;

            for (const item of items) {
                if (item.note_path) formalNotes++;

                const lifecycle = item.lifecycle || 'pdf_ready';
                lifecycleCounts[lifecycle] = (lifecycleCounts[lifecycle] || 0) + 1;

                const health = item.health || {};
                for (const dim of ['pdf_health', 'ocr_health', 'note_health', 'asset_health']) {
                    const val = health[dim] || 'healthy';
                    if (val === 'healthy') healthCounts[dim].healthy++;
                    else healthCounts[dim].unhealthy++;
                }

                const ocrStatus = item.ocr_status || '';
                ocrTotal++;
                if (ocrStatus === 'done') ocrDone++;
                else if (ocrStatus === 'pending') ocrPending++;
                else if (ocrStatus === 'processing' || ocrStatus === 'queued' || ocrStatus === 'running') ocrProcessing++;
                else ocrFailed++;
            }

            this._cachedStats = {
                version: index.paperforge_version || this._cachedStats?.version || '\u2014',
                total_papers: items.length,
                formal_notes: formalNotes,
                exports: 0,
                bases: 0,
                ocr: { total: ocrTotal, pending: ocrPending, processing: ocrProcessing, done: ocrDone, failed: ocrFailed },
                path_errors: 0,
                lifecycle_level_counts: lifecycleCounts,
                health_aggregate: healthCounts,
            };

            this._metricsEl.empty();
            this._renderStats(this._cachedStats);
            this._renderOcr(this._cachedStats);
        } catch (err) {
            // D-07: Fallback — spawn CLI if file is missing or corrupt
            if (!quiet && !this._cachedStats) {
                this._metricsEl.createEl('div', { cls: 'paperforge-status-loading', text: 'No index \u2014 trying CLI...' });
            }
            const plugin = this.app.plugins.plugins['paperforge'];
            const { path: pythonExe, extraArgs = [] } = resolvePythonExecutable(vp, plugin?.settings);
            execFile(pythonExe, [...extraArgs, '-m', 'paperforge', 'status', '--json'], { cwd: vp, timeout: 30000 }, (err2, stdout) => {
                if (err2) {
                    if (this._cachedStats) return;
                    this._metricsEl.createEl('div', { cls: 'paperforge-status-error', text: 'Cannot reach PaperForge CLI.\nMake sure paperforge is installed and in your PATH.' });
                    return;
                }
                try {
                    const d = JSON.parse(stdout);
                    this._cachedStats = d;
                    this._metricsEl.empty();
                    this._renderStats(d);
                    this._renderOcr(d);
                } catch {
                    if (!this._cachedStats) {
                        this._metricsEl.createEl('div', { cls: 'paperforge-status-error', text: 'Invalid response from paperforge status.' });
                    }
                }
            });
        }
    }

    /* ── Loading Skeleton Utility (D-24) ── */
    _renderSkeleton(container) {
        container.addClass('paperforge-loading');
    }

    /* ── Empty State Utility (D-25) ── */
    _renderEmptyState(container, message) {
        container.createEl('div', {
            cls: 'paperforge-empty-state',
            text: message || 'No data',
        });
    }

    /* ── Metric Progress Bar Helper (D-05) ── */
    _buildMetricBar(card, value, max) {
        if (max <= 0) return;
        const pct = Math.min(100, (value / max) * 100);
        const bar = card.createEl('div', { cls: 'paperforge-metric-progress' });
        bar.createEl('div', {
            cls: 'paperforge-metric-progress-fill',
            attr: { style: `width:${pct.toFixed(1)}%` },
        });
    }

    /* ── Index Loading (D-11, D-17, D-19) ── */
    _loadIndex() {
        const vp = this.app.vault.adapter.basePath;
        const plugin = this.app.plugins.plugins['paperforge'];
        const systemDir = plugin?.settings?.system_dir || 'System';
        const indexPath = path.join(vp, systemDir, 'PaperForge', 'indexes', 'formal-library.json');
        try {
            const raw = fs.readFileSync(indexPath, 'utf-8');
            return JSON.parse(raw);
        } catch {
            return null;
        }
    }

    /* ── Cached Index Accessor (D-14) ── */
    _getCachedIndex() {
        if (!this._cachedItems) {
            const index = this._loadIndex();
            this._cachedItems = index ? (index.items || []) : [];
        }
        return this._cachedItems;
    }

    /* ── Single Paper Lookup by Key (D-12, D-18) ── */
    _findEntry(key) {
        if (!key) return null;
        return this._getCachedIndex().find(item => item.zotero_key === key) || null;
    }

    /* ── Filter Papers by Domain (D-13, D-16) ── */
    _filterByDomain(domain) {
        if (!domain) return [];
        return this._getCachedIndex().filter(item => item.domain === domain);
    }

    /* ── Metric Cards (Enhanced D-04, D-05, D-06) ── */
    _renderStats(d) {
        this._versionBadge.setText(this._paperforgeVersion || (d.version ? 'v' + d.version : 'v\u2014'));

        if (!d || typeof d.total_papers === 'undefined') {
            this._renderSkeleton(this._metricsEl);
            return;
        }

        this._metricsEl.removeClass('paperforge-loading');

        const totalPapers = d.total_papers || 0;
        const totalFormal = d.formal_notes || 0;

        const metrics = [
            { value: totalPapers, label: 'Papers', color: 'var(--color-cyan)', barMax: 0 },
            { value: totalFormal, label: 'Formal Notes', color: 'var(--color-blue)', barMax: totalPapers },
            { value: d.exports || 0, label: 'Exports', color: 'var(--color-purple)', barMax: 0 },
        ];
        for (const m of metrics) {
            const card = this._metricsEl.createEl('div', { cls: 'paperforge-metric-card' });
            card.style.setProperty('--metric-color', m.color);
            card.createEl('div', { cls: 'paperforge-metric-value', text: (m.value)?.toString() || '\u2014' });
            card.createEl('div', { cls: 'paperforge-metric-label', text: m.label });
            if (m.barMax > 0) {
                this._buildMetricBar(card, m.value, m.barMax);
            }
        }
    }

    /* ── OCR Pipeline ── */
    _renderOcr(d) {
        const ocr = d.ocr || {};
        const total = ocr.total || 0;

        if (total === 0) {
            this._ocrSection.style.display = 'none';
            return;
        }

        this._ocrSection.style.display = 'block';
        this._ocrEmpty.style.display = 'none';

        const done = ocr.done || 0;
        const pending = ocr.pending || 0;
        const processing = ocr.processing || 0;
        const failed = ocr.failed || 0;

        /* Badge */
        this._ocrBadge.removeClass('active', 'idle');
        if (processing > 0) {
            this._ocrBadge.addClass('active');
            this._ocrBadge.setText('Processing');
        } else if (pending > 0) {
            this._ocrBadge.addClass('idle');
            this._ocrBadge.setText('Pending');
        } else {
            this._ocrBadge.addClass('idle');
            this._ocrBadge.setText('Idle');
        }

        /* Progress bar */
        this._ocrTrack.empty();
        if (processing > 0) {
            this._ocrTrack.addClass('paperforge-processing');
        } else {
            this._ocrTrack.removeClass('paperforge-processing');
        }
        const segs = [
            { cls: 'pending', count: pending },
            { cls: 'active', count: processing },
            { cls: 'done', count: done },
            { cls: 'failed', count: failed },
        ];
        for (const s of segs) {
            if (s.count > 0) {
                const pct = (s.count / total * 100).toFixed(1);
                this._ocrTrack.createEl('div', {
                    cls: `paperforge-progress-seg ${s.cls}`,
                    attr: { style: `width:${pct}%` },
                });
            }
        }

        /* Counts row */
        this._ocrCounts.empty();
        const labels = [
            { cls: 'pending', value: pending, label: 'Pending' },
            { cls: 'active', value: processing, label: 'Processing' },
            { cls: 'done', value: done, label: 'Done' },
            { cls: 'failed', value: failed, label: 'Failed' },
        ];
        for (const l of labels) {
            const cnt = this._ocrCounts.createEl('div', { cls: 'paperforge-ocr-count' });
            cnt.createEl('div', { cls: 'paperforge-ocr-count-value', text: l.value.toString() });
            cnt.createEl('div', { cls: 'paperforge-ocr-count-label', text: l.label });
        }

        // ── Dynamic: "Run All Pending OCR" when items are in queue (DASH-01) ──
        this._renderPendingOcrAction(pending);
    }

    /* ── Lifecycle Stepper (D-07 through D-11) ── */
    _renderLifecycleStepper(container, lifecycle, currentStage) {
        if (!lifecycle || !currentStage) {
            this._renderSkeleton(container);
            return;
        }

        const stages = [
            { key: 'indexed', label: 'Indexed' },
            { key: 'pdf_ready', label: 'PDF Ready' },
            { key: 'fulltext_ready', label: 'Fulltext Ready' },
            { key: 'deep_read_done', label: 'Deep Read' },
        ];

        const stepper = container.createEl('div', { cls: 'paperforge-lifecycle-stepper' });
        let foundCurrent = false;

        for (const stage of stages) {
            const step = stepper.createEl('div', { cls: 'step' });
            step.createEl('div', { cls: 'step-indicator' });
            step.createEl('div', { cls: 'step-label', text: stage.label });

            if (stage.key === currentStage) {
                step.addClass('current');
                foundCurrent = true;
            } else if (!foundCurrent) {
                step.addClass('completed');
            } else {
                step.addClass('pending');
            }
        }
    }

    /* ── Health Matrix (D-12 through D-16) ── */
    _renderHealthMatrix(container, health) {
        if (!health) {
            this._renderSkeleton(container);
            return;
        }

        const dimensions = [
            { key: 'pdf_health', label: 'PDF Health', iconOk: '\u2713', iconWarn: '\u26A0', iconFail: '\u2717' },
            { key: 'ocr_health', label: 'OCR Health', iconOk: '\u2713', iconWarn: '\u26A0', iconFail: '\u2717' },
            { key: 'note_health', label: 'Note Health', iconOk: '\u2713', iconWarn: '\u26A0', iconFail: '\u2717' },
            { key: 'asset_health', label: 'Asset Health', iconOk: '\u2713', iconWarn: '\u26A0', iconFail: '\u2717' },
        ];

        const matrix = container.createEl('div', { cls: 'paperforge-health-matrix' });

        for (const dim of dimensions) {
            const status = health[dim.key] || 'healthy';
            const cell = matrix.createEl('div', { cls: 'paperforge-health-cell' });

            let icon, statusClass, tooltip;
            if (status === 'healthy' || status === 'ok') {
                icon = dim.iconOk;
                statusClass = 'ok';
                tooltip = `${dim.label}: OK`;
            } else if (status === 'warn' || status === 'warning' || status === 'degraded') {
                icon = dim.iconWarn;
                statusClass = 'warn';
                tooltip = `${dim.label}: Needs Attention`;
            } else {
                icon = dim.iconFail;
                statusClass = 'fail';
                tooltip = `${dim.label}: Failed`;
            }

            cell.addClass(statusClass);
            cell.setAttribute('title', tooltip);
            cell.createEl('div', { cls: 'paperforge-health-cell-icon', text: icon });
            cell.createEl('div', { cls: 'paperforge-health-cell-label', text: dim.label });
        }
    }

    /* ── Maturity Gauge (D-17 through D-20) ── */
    _renderMaturityGauge(container, maturityLevel, blockingChecks) {
        if (maturityLevel == null || maturityLevel === undefined) {
            this._renderSkeleton(container);
            return;
        }

        const gauge = container.createEl('div', { cls: 'paperforge-maturity-gauge' });
        const track = gauge.createEl('div', { cls: 'gauge-track' });
        const maxLevel = 4;
        const currentLevel = Math.max(1, Math.min(maxLevel, Math.round(maturityLevel)));

        for (let i = 1; i <= maxLevel; i++) {
            const seg = track.createEl('div', { cls: 'gauge-segment' });
            if (i <= currentLevel) {
                seg.addClass('filled');
                seg.addClass(`level-${i}`);
            }
        }

        gauge.createEl('div', { cls: 'gauge-level', text: `Level ${currentLevel} / ${maxLevel}` });

        if (currentLevel < maxLevel && blockingChecks) {
            const blockers = typeof blockingChecks === 'string' ? [blockingChecks] : blockingChecks;
            if (blockers.length > 0) {
                const list = gauge.createEl('ul', { cls: 'gauge-blockers' });
                for (const check of blockers) {
                    list.createEl('li', { text: check });
                }
            }
        }
    }

    /* ── Bar Chart (D-21 through D-23) ── */
    _renderBarChart(container, lifecycleCounts) {
        if (!lifecycleCounts || Object.keys(lifecycleCounts).length === 0) {
            this._renderEmptyState(container, 'No lifecycle data');
            return;
        }

        const stages = [
            { key: 'indexed', label: 'Indexed', cls: 'stage-indexed' },
            { key: 'pdf_ready', label: 'PDF Ready', cls: 'stage-pdf-ready' },
            { key: 'fulltext_ready', label: 'Fulltext Ready', cls: 'stage-fulltext-ready' },
            { key: 'deep_read_done', label: 'Deep Read', cls: 'stage-deep-read' },
        ];

        const chart = container.createEl('div', { cls: 'paperforge-bar-chart' });
        const maxCount = Math.max(1, ...stages.map(s => lifecycleCounts[s.key] || 0));

        for (const stage of stages) {
            const count = lifecycleCounts[stage.key] || 0;
            const pct = (count / maxCount) * 100;

            const row = chart.createEl('div', { cls: 'bar-row' });
            row.createEl('div', { cls: 'bar-label', text: stage.label });
            const track = row.createEl('div', { cls: 'bar-track' });
            const fill = track.createEl('div', {
                cls: `bar-fill ${stage.cls}`,
                attr: { style: `width:${pct.toFixed(1)}%` },
            });
            row.createEl('div', { cls: 'bar-count', text: count.toString() });
        }
    }

    /* ── Render Quick Actions (extracted from _buildPanel for mode-aware reuse) ── */
    _renderActions() {
        this._actionsGrid.empty();
        for (const a of ACTIONS) {
            const card = this._actionsGrid.createEl('div', { cls: 'paperforge-action-card' });
            if (a.disabled) card.addClass('disabled');
            card.createEl('div', { cls: 'paperforge-action-card-icon', text: a.icon });
            card.createEl('div', { cls: 'paperforge-action-card-title', text: a.title });
            card.createEl('div', { cls: 'paperforge-action-card-desc', text: a.desc });
            card.createEl('div', { cls: 'paperforge-action-card-hint', text: a.disabled ? 'Coming soon' : 'Click to run' });
            card.addEventListener('click', () => this._runAction(a, card));
        }
    }

    /* ── Dynamic "Run All Pending OCR" action (DASH-01) ── */
    _renderPendingOcrAction(pending) {
        // Remove stale pending action card if any
        const existing = this._actionsGrid.querySelector('.paperforge-pending-ocr-action');
        if (existing) existing.remove();

        if (pending > 0) {
            const card = this._actionsGrid.createEl('div', { cls: 'paperforge-action-card paperforge-pending-ocr-action' });
            card.createEl('div', { cls: 'paperforge-action-card-icon', text: '\u229E' });
            card.createEl('div', { cls: 'paperforge-action-card-title', text: t('run_pending_ocr') });
            card.createEl('div', { cls: 'paperforge-action-card-desc', text: pending + ' ' + t('run_pending_ocr_desc') });
            card.createEl('div', { cls: 'paperforge-action-card-hint', text: 'Click to run' });
            card.addEventListener('click', () => {
                const action = ACTIONS.find(a => a.id === 'paperforge-ocr');
                if (action) this._runAction(action, card);
            });
        }
    }

    /* ── Invalidate cached index (D-14) ── */
    _invalidateIndex() {
        this._cachedItems = null;
    }

    /* ── Pure Mode Resolution (D-07, Phase 32) ── */
    _resolveModeForFile(file) {
        if (!file) return { mode: 'global', filePath: null, key: null, domain: null };

        const ext = file.extension;
        const filePath = file.path;

        if (ext === 'base') {
            return { mode: 'collection', filePath, key: null, domain: file.basename };
        }

        if (ext === 'md') {
            // D-01: Check deep-reading.md FIRST — before zotero_key frontmatter
            if (file.name === 'deep-reading.md') {
                const parentDir = file.parent ? file.parent.name : '';
                // D-02: Parent directory must match {8-char-key} - {Title}
                if (/^[A-Z0-9]{8} - .+$/.test(parentDir)) {
                    const cache = this.app.metadataCache.getFileCache(file);
                    const key = cache && cache.frontmatter && cache.frontmatter.zotero_key;
                    if (key) {
                        return { mode: 'deep-reading', filePath, key, domain: null };
                    }
                }
                // D-03: Fall through to normal .md handling
            }

            // Standard .md — check for zotero_key in frontmatter (D-03)
            const cache = this.app.metadataCache.getFileCache(file);
            const key = cache && cache.frontmatter && cache.frontmatter.zotero_key;
            if (key) {
                return { mode: 'paper', filePath, key, domain: null };
            }
            return { mode: 'global', filePath, key: null, domain: null };
        }

        return { mode: 'global', filePath, key: null, domain: null };
    }

    /* ── Context Detection & Mode Switch (D-01, D-02, D-03, D-04, D-10) ── */
    _detectAndSwitch() {
        const resolved = this._resolveModeForFile(this.app.workspace.getActiveFile());

        this._currentDomain = resolved.domain || null;
        this._currentPaperKey = resolved.key || null;
        this._currentPaperEntry = resolved.key ? this._findEntry(resolved.key) : null;

        this._switchMode(resolved.mode, resolved.filePath);
    }

    /* ── Mode Switching (D-05, D-06) ── */
    _switchMode(mode, filePath) {
        // D-06: Identity guard — check BOTH mode AND file path
        if (this._currentMode === mode && this._currentFilePath === filePath) {
            this._refreshCurrentMode();
            return;
        }

        this._currentMode = mode;
        this._currentFilePath = filePath;

        // Clear existing content (D-06)
        this._contentEl.empty();
        this._contentEl.removeClass('switching');

        // Update header (D-07)
        this._renderModeHeader(mode);

        // Render mode-specific content (D-06)
        switch (mode) {
            case 'global':
                this._renderGlobalMode();
                break;
            case 'paper':
                this._renderPaperMode();
                break;
            case 'collection':
                this._renderCollectionMode();
                break;
            case 'deep-reading':
                this._renderDeepReadingMode();
                break;
        }
    }

    /* ── Global Mode Render (existing dashboard, extracted from _fetchStats + _renderOcr) ── */
    _renderGlobalMode() {
        // Drift warning banner (hidden by default, shown on version mismatch)
        this._driftBannerEl = this._contentEl.createEl('div', { cls: 'paperforge-drift-banner' });
        this._driftBannerEl.style.display = 'none';

        // Metric cards
        this._metricsEl = this._contentEl.createEl('div', { cls: 'paperforge-metrics' });

        // OCR pipeline section (_renderOcr expects these instance vars)
        this._ocrSection = this._contentEl.createEl('div', { cls: 'paperforge-ocr-section' });
        this._ocrSection.style.display = 'none';
        const ocrHeader = this._ocrSection.createEl('div', { cls: 'paperforge-ocr-header' });
        ocrHeader.createEl('h4', { cls: 'paperforge-ocr-title', text: 'OCR Pipeline' });
        this._ocrBadge = ocrHeader.createEl('span', { cls: 'paperforge-ocr-badge idle', text: 'Idle' });
        this._ocrTrack = this._ocrSection.createEl('div', { cls: 'paperforge-progress-track' });
        this._ocrCounts = this._ocrSection.createEl('div', { cls: 'paperforge-ocr-counts' });
        this._ocrEmpty = this._ocrSection.createEl('div', { cls: 'paperforge-ocr-empty', text: 'No OCR tasks yet. Mark papers with do_ocr: true to start.' });

        this._cachedStats = null; // force fresh load
        this._fetchStats();
    }

    /* ── Per-Paper Mode Render (D-01 through D-09, Phase 29) ── */
    _renderPaperMode() {
        const entry = this._currentPaperEntry;
        const key = this._currentPaperKey;

        // --- Handle loading / empty / not-found states (D-03) ---
        if (!key) {
            // No key at all (defensive fallback)
            this._renderEmptyState(this._contentEl, 'No paper data available.');
            return;
        }

        if (!entry) {
            // Key exists but entry not found in index (D-18)
            this._contentEl.createEl('div', {
                cls: 'paperforge-content-placeholder',
                text: 'Paper "' + key + '" not found in canonical index. Sync first.',
            });
            return;
        }

        // --- Create per-paper view container (D-04 through D-09) ---
        const view = this._contentEl.createEl('div', { cls: 'paperforge-paper-view' });

        // ============ Contextual Action Buttons Row (D-10, D-11, D-12, D-13) ============
        const actionsRow = view.createEl('div', { cls: 'paperforge-paper-actions' });

        // "Copy Context" button (D-11) — reuse existing paperforge-copy-context action
        const ctxBtn = actionsRow.createEl('button', { cls: 'paperforge-contextual-btn' });
        ctxBtn.createEl('span', { cls: 'paperforge-contextual-btn-icon', text: '\u2139' });
        ctxBtn.createEl('span', { text: 'Copy Context' });
        ctxBtn.addEventListener('click', () => {
            const action = ACTIONS.find(a => a.id === 'paperforge-copy-context');
            if (action) this._runAction(action, ctxBtn);
        });

        // "Open Fulltext" button (D-12) — open fulltext.md in Obsidian
        if (entry.fulltext_path) {
            const ftBtn = actionsRow.createEl('button', { cls: 'paperforge-contextual-btn' });
            ftBtn.createEl('span', { cls: 'paperforge-contextual-btn-icon', text: '\uD83D\uDCC4' });
            ftBtn.createEl('span', { text: 'Open Fulltext' });
            ftBtn.addEventListener('click', () => this._openFulltext(entry.fulltext_path));
        }

        // ============ Paper Metadata Header (D-04) ============
        const header = view.createEl('div', { cls: 'paperforge-paper-header' });
        const titleText = entry.title || 'Untitled';
        header.createEl('div', { cls: 'paperforge-paper-title', text: titleText });

        const meta = header.createEl('div', { cls: 'paperforge-paper-meta' });
        if (entry.authors && entry.authors.length > 0) {
            const authorsStr = entry.authors.join(', ');
            meta.createEl('span', { cls: 'paperforge-paper-authors', text: authorsStr });
        }
        if (entry.year) {
            meta.createEl('span', { cls: 'paperforge-paper-year', text: String(entry.year) });
        }

        // ============ Lifecycle Stepper (D-05) ============
        this._renderLifecycleStepper(view, entry, entry.lifecycle);

        // ============ Health Matrix (D-06) ============
        this._renderHealthMatrix(view, entry.health);

        // ============ Maturity Gauge (D-07) ============
        const maturity = entry.maturity || {};
        this._renderMaturityGauge(view, maturity.level, maturity.blocking);

        // ============ OCR Queue Control (DASH-01) ============
        const ocrRow = view.createEl('div', { cls: 'paperforge-paper-actions' });
        const inQueue = entry.do_ocr === true;
        const ocrBtn = ocrRow.createEl('button', { cls: 'paperforge-contextual-btn' });
        ocrBtn.createEl('span', { cls: 'paperforge-contextual-btn-icon', text: inQueue ? '\u23F1' : '\u23F0' });
        ocrBtn.createEl('span', { text: inQueue ? t('ocr_queue_remove') : t('ocr_queue_add') });
        ocrBtn.addEventListener('click', async () => {
            const noteFile = entry.note_path ? this.app.vault.getAbstractFileByPath(entry.note_path) : null;
            if (!noteFile) {
                new Notice('[!!] Note file not found: ' + (entry.note_path || 'unknown'), 6000);
                return;
            }
            const newValue = !inQueue;
            await this.app.fileManager.processFrontMatter(noteFile, (fm) => {
                fm.do_ocr = newValue;
            });
            new Notice(newValue ? t('ocr_queue_added') : t('ocr_queue_removed'));
            this._refreshCurrentMode();
        });
        if (inQueue) {
            ocrRow.createEl('span', {
                cls: 'paperforge-ocr-queue-hint',
                text: 'OCR ' + (entry.ocr_status === 'done' ? 'already done' : 'pending'),
            });
        }

        // ============ Next-Step Recommendation Card (D-08, D-09) ============
        this._renderNextStepCard(view, entry, key);
    }

    /* ── Next-Step Recommendation Card (D-08, D-09) ── */
    _renderNextStepCard(container, entry, key) {
        const nextStep = entry.next_step || 'ready';

        // Map next_step value to human-readable info
        const stepInfo = {
            'sync':         { label: 'Sync Needed',    text: 'This paper needs to be synced from Zotero. Click to run sync.',             cmd: 'sync',     icon: '\u21BB' },
            'ocr':          { label: 'OCR Needed',     text: 'Fulltext is missing but PDF is present. Click to run OCR.',                  cmd: 'ocr',      icon: '\u229E' },
            'repair':       { label: 'Repair Needed',  text: 'State divergence or path errors detected. Click to repair.',                 cmd: 'repair',   icon: '\u21BA' },
            'rebuild index':{ label: 'Rebuild Needed', text: 'Index may be stale. Click to run sync to rebuild.',                          cmd: 'sync',     icon: '\u21BB' },
            '/pf-deep':     { label: 'Ready for Deep Reading', text: 'Fulltext is ready. Copy /pf-deep command and run in your agent.',   cmd: null,       icon: '\uD83D\uDD0D' },
            'ready':        { label: 'All Set',        text: 'This paper is fully processed and ready for use.',                           cmd: 'ready',    icon: '\u2713' },
        };

        const info = stepInfo[nextStep] || stepInfo['ready'];

        // Build the card
        const card = container.createEl('div', { cls: 'paperforge-next-step-card' });
        if (nextStep === 'ready') card.addClass('ready');

        card.createEl('div', { cls: 'paperforge-next-step-label', text: 'Recommended Next Step' });
        card.createEl('div', { cls: 'paperforge-next-step-text', text: info.text });

        if (info.cmd && info.cmd !== 'ready') {
            // Action button for sync/ocr/repair/rebuild index — reuse existing _runAction
            const trigger = card.createEl('button', { cls: 'paperforge-next-step-trigger' });
            trigger.createEl('span', { text: info.icon + '  ' + info.label });
            trigger.addEventListener('click', () => {
                const action = ACTIONS.find(a => a.cmd === info.cmd);
                if (action) this._runAction(action, trigger);
            });
        } else if (nextStep === '/pf-deep') {
            // Copy full command /pf-deep <key> to clipboard (DASH-02)
            const trigger = card.createEl('button', { cls: 'paperforge-next-step-trigger' });
            trigger.createEl('span', { text: '\uD83D\uDCCB  ' + t('copy_pf_deep_cmd') });
            trigger.addEventListener('click', () => {
                const fullCmd = '/pf-deep ' + key;
                navigator.clipboard.writeText(fullCmd).then(() => {
                    trigger.setText('\u2713  ' + t('copied'));
                    new Notice(fullCmd + ' copied');
                }).catch(() => {
                    new Notice('[!!] Clipboard write failed', 6000);
                });
            });

            // Show "Run in [agent_platform]" label below the button (DASH-02)
            const platform = this.plugin.settings?.agent_platform || 'opencode';
            const labelEl = card.createEl('div', { cls: 'paperforge-agent-platform-label' });
            labelEl.setText(t('run_in_agent').replace('{0}', platform));
        } else if (nextStep === 'ready') {
            if (entry.deep_reading_path && entry.deep_reading_status === 'done') {
                // D-01, D-03: Jump-to-deep-reading button replaces Copy Context when deep reading exists
                const trigger = card.createEl('button', { cls: 'paperforge-next-step-trigger' });
                trigger.createEl('span', { text: '\uD83D\uDD0D  ' + t('jump_to_deep_reading') });
                trigger.addEventListener('click', () => {
                    // D-04: Follow _openFulltext() pattern — verify file, open, error Notice
                    const drFile = this.app.vault.getAbstractFileByPath(entry.deep_reading_path);
                    if (drFile) {
                        this.app.workspace.openLinkText(drFile.path, '');
                    } else {
                        // D-05: File missing from disk despite index claiming it exists
                        new Notice('[!!] ' + t('deep_reading_not_found'), 6000);
                    }
                });
            } else {
                // D-02, D-03: Fall back to existing Copy Context button
                const trigger = card.createEl('button', { cls: 'paperforge-next-step-trigger' });
                trigger.createEl('span', { text: '\u2139  Copy Context' });
                trigger.addEventListener('click', () => {
                    const action = ACTIONS.find(a => a.id === 'paperforge-copy-context');
                    if (action) this._runAction(action, trigger);
                });
            }
        }
    }

    /* ── Open Fulltext File in Obsidian (D-12) ── */
    _openFulltext(fulltextPath) {
        if (!fulltextPath) {
            new Notice('[!!] No fulltext path available for this paper', 6000);
            return;
        }
        // fulltext_path is relative to vault root (e.g., "Literature/domain/key - Title/fulltext.md")
        // Use Obsidian API to open the file
        const file = this.app.vault.getAbstractFileByPath(fulltextPath);
        if (file) {
            this.app.workspace.openLinkText(file.path, '');
        } else {
            new Notice('[!!] Fulltext file not found: ' + fulltextPath, 6000);
        }
    }

    /* ── Deep-Reading Mode Render (Phase 33) ── */
    async _renderDeepReadingMode() {
        const entry = this._currentPaperEntry;
        const modeGuard = () => this._currentMode === 'deep-reading';
        const view = this._contentEl.createEl('div', { cls: 'paperforge-mode-deepreading' });

        // Read deep-reading.md content
        let deepReadingText = '';
        if (entry && entry.deep_reading_path) {
            const drFile = this.app.vault.getAbstractFileByPath(entry.deep_reading_path);
            if (drFile) {
                deepReadingText = await this.app.vault.read(drFile);
            }
            if (!modeGuard()) return; // Guard: mode switched during async read
        }

        // Read discussion.json
        let discussionData = null;
        if (entry && entry.ai_path) {
            const aiPath = entry.ai_path.replace(/^\[\[/, '').replace(/\]\]$/, '');
            const djPath = aiPath + 'discussion.json';
            const djFile = this.app.vault.getAbstractFileByPath(djPath);
            if (djFile) {
                try {
                    const raw = await this.app.vault.read(djFile);
                    if (!modeGuard()) return; // Guard: mode switched
                    discussionData = JSON.parse(raw);
                } catch (e) { /* file missing or parse error */ }
            }
        }

        // Render sections
        this._renderDeepStatusCard(view, entry);
        this._renderDeepPass1Card(view, deepReadingText);
        this._renderDeepQACard(view, discussionData);
    }

    /* ── Deep-Reading Status Card ── */
    _renderDeepStatusCard(container, entry) {
        const card = container.createEl('div', { cls: 'paperforge-deepreading-card' });
        card.createEl('div', { cls: 'paperforge-deepreading-card-title', text: '\uD83D\uDCCA \u72B6\u6001\u6982\u89C8' });

        if (!entry) {
            card.createEl('div', { cls: 'paperforge-deepreading-empty', text: '\u6682\u65E0\u6570\u636E' });
            return;
        }

        const statusItems = [
            { label: 'Figure-Map', value: entry.figure_map ? '\u2705 \u5DF2\u751F\u6210' : '\u23F3 \u5F85\u751F\u6210' },
            { label: 'OCR \u72B6\u6001', value: entry.ocr_status === 'done' ? '\u2705 \u5DF2\u5B8C\u6210' : '\u23F3 ' + (entry.ocr_status || '\u5F85\u5904\u7406') },
            { label: 'Pass \u5B8C\u6210', value: this._getPassCompletion(entry) },
            { label: '\u5065\u5EB7\u72B6\u51B5', value: entry.health && entry.health.pdf_health === 'healthy' ? '\u2705 \u6B63\u5E38' : '\u26A0\uFE0F \u9700\u5173\u6CE8' },
        ];

        const list = card.createEl('div', { cls: 'paperforge-deepreading-status-list' });
        for (const item of statusItems) {
            const row = list.createEl('div', { cls: 'paperforge-deepreading-status-row' });
            row.createEl('span', { cls: 'paperforge-deepreading-status-label', text: item.label });
            row.createEl('span', { cls: 'paperforge-deepreading-status-value', text: item.value });
        }
    }

    _getPassCompletion(entry) {
        const status = entry.deep_reading_status || 'pending';
        if (status === 'done') return '\u2705 3/3 (\u5DF2\u5B8C\u6210)';
        return '\u23F3 \u5F85\u5B8C\u6210';
    }

    /* ── Deep-Reading Pass 1 Summary Card ── */
    _renderDeepPass1Card(container, text) {
        const card = container.createEl('div', { cls: 'paperforge-deepreading-card' });
        card.createEl('div', { cls: 'paperforge-deepreading-card-title', text: '\uD83D\uDCDD Pass 1 \u603B\u7ED3' });

        if (!text || text.trim() === '') {
            card.createEl('div', { cls: 'paperforge-deepreading-empty', text: '\u6682\u65E0 Pass 1 \u603B\u7ED3' });
            return;
        }

        const extracted = this._extractPass1Content(text);
        if (!extracted) {
            card.createEl('div', { cls: 'paperforge-deepreading-empty', text: '\u6682\u65E0 Pass 1 \u603B\u7ED3' });
            return;
        }

        const content = card.createEl('div', { cls: 'paperforge-deepreading-pass1-content' });
        const lines = extracted.split('\n').filter(l => l.trim());
        for (const line of lines) {
            if (line.startsWith('### ')) {
                content.createEl('h4', { cls: 'paperforge-deepreading-pass1-subheading', text: line.replace('### ', '') });
            } else if (line.startsWith('**') && line.endsWith('**')) {
                content.createEl('p', { cls: 'paperforge-deepreading-pass1-marker', text: line });
            } else if (line.trim()) {
                content.createEl('p', { cls: 'paperforge-deepreading-pass1-text', text: line });
            }
        }
    }

    _extractPass1Content(text) {
        const markers = ['**\u4E00\u53E5\u8BDD\u603B\u89C8**', '## Pass 1', '**\u6587\u7AE0\u6458\u8981**'];
        for (const marker of markers) {
            const idx = text.indexOf(marker);
            if (idx !== -1) {
                const after = idx + marker.length;
                // Cut at next major section marker
                const cutMarkers = ['**\u8BC1\u636E\u8FB9\u754C**', '**Figure \u5BFC\u8BFB**', '**\u4E3B\u8981\u53D1\u73B0**'];
                let nextCut = text.length;
                for (const cm of cutMarkers) {
                    const ci = text.indexOf(cm, after);
                    if (ci !== -1 && ci < nextCut) nextCut = ci;
                }
                return text.substring(after, nextCut).trim();
            }
        }
        return null;
    }

    /* ── Deep-Reading AI Q&A History Card ── */
    _renderDeepQACard(container, data) {
        const card = container.createEl('div', { cls: 'paperforge-deepreading-card' });

        // D-10: Collapsible header
        const header = card.createEl('div', { cls: 'paperforge-deepreading-card-header collapsible' });
        header.createEl('div', { cls: 'paperforge-deepreading-card-title', text: '\uD83D\uDCAC AI \u95EE\u7B54\u8BB0\u5F55' });

        const body = card.createEl('div', { cls: 'paperforge-deepreading-card-body collapsed' });

        // Toggle collapse
        header.addEventListener('click', () => {
            body.classList.toggle('collapsed');
        });

        // D-12: Empty states
        if (!data || !data.sessions || data.sessions.length === 0) {
            body.createEl('div', { cls: 'paperforge-deepreading-empty', text: !data ? '\u6682\u65E0\u8BA8\u8BBA\u8BB0\u5F55' : '\u6682\u65E0\u95EE\u7B54\u5185\u5BB9' });
            return;
        }

        // D-08: Sessions-based grouping
        for (const session of data.sessions) {
            const sessionEl = body.createEl('div', { cls: 'paperforge-deepreading-session' });
            const sessionHeader = sessionEl.createEl('div', { cls: 'paperforge-deepreading-session-header' });
            sessionHeader.createEl('span', { text: session.model || 'AI' });
            sessionHeader.createEl('span', { cls: 'paperforge-deepreading-session-date', text: session.started || '' });

            // D-09: Dialog bubbles
            if (session.qa_pairs) {
                for (const qa of session.qa_pairs) {
                    const qBubble = sessionEl.createEl('div', { cls: 'paperforge-deepreading-bubble question' });
                    qBubble.createEl('div', { cls: 'bubble-label', text: '\u95EE\u9898' });
                    qBubble.createEl('div', { cls: 'bubble-text', text: qa.question });

                    const aBubble = sessionEl.createEl('div', { cls: 'paperforge-deepreading-bubble answer' });
                    aBubble.createEl('div', { cls: 'bubble-label', text: '\u89E3\u7B54' });
                    aBubble.createEl('div', { cls: 'bubble-text', text: qa.answer });
                }
            }
        }
    }

    /* ── Collection Mode Render (Phase 30) ── */
    _renderCollectionMode() {
        const domain = this._currentDomain || 'Unknown';
        const domainItems = this._filterByDomain(domain);

        const view = this._contentEl.createEl('div', { cls: 'paperforge-collection-view' });

        // --- Empty state ---
        if (domainItems.length === 0) {
            this._renderEmptyState(view, 'No papers found in domain "' + domain + '". Sync some papers first.');
            return;
        }

        // --- Single-pass aggregation ---
        const healthAgg = {
            pdf_health: { healthy: 0, unhealthy: 0 },
            ocr_health: { healthy: 0, unhealthy: 0 },
            note_health: { healthy: 0, unhealthy: 0 },
            asset_health: { healthy: 0, unhealthy: 0 },
        };
        let hasPdf = 0;
        let fulltextReady = 0;
        let deepRead = 0;

        for (const item of domainItems) {
            if (item.has_pdf) hasPdf++;
            if (item.ocr_status === 'done') fulltextReady++;
            if (item.deep_reading_status === 'done') deepRead++;

            const health = item.health || {};
            for (const dim of ['pdf_health', 'ocr_health', 'note_health', 'asset_health']) {
                const val = health[dim] || 'healthy';
                if (val === 'healthy') healthAgg[dim].healthy++;
                else healthAgg[dim].unhealthy++;
            }
        }

        // --- Metric cards row (D-03) ---
        const metrics = view.createEl('div', { cls: 'paperforge-collection-metrics' });
        const totalPapers = domainItems.length;

        const metricCards = [
            { value: totalPapers, label: 'Papers', color: 'var(--color-cyan)', barMax: 0 },
            { value: fulltextReady, label: 'Fulltext Ready', color: 'var(--color-green)', barMax: totalPapers },
            { value: deepRead, label: 'Deep Read', color: 'var(--color-yellow)', barMax: totalPapers },
        ];
        for (const m of metricCards) {
            const card = metrics.createEl('div', { cls: 'paperforge-metric-card' });
            card.style.setProperty('--metric-color', m.color);
            card.createEl('div', { cls: 'paperforge-metric-value', text: (m.value)?.toString() || '\u2014' });
            card.createEl('div', { cls: 'paperforge-metric-label', text: m.label });
            if (m.barMax > 0) {
                this._buildMetricBar(card, m.value, m.barMax);
            }
        }

        // --- Lifecycle distribution bar chart (cumulative, D-04) ---
        this._renderBarChart(view, {
            indexed: totalPapers - hasPdf,
            pdf_ready: hasPdf,
            fulltext_ready: fulltextReady,
            deep_read_done: deepRead,
        });

        // --- Health overview (D-05) ---
        this._renderCollectionHealth(view, healthAgg);
    }

    /* ── Collection Health Overview (Phase 30, D-05) ── */
    _renderCollectionHealth(container, healthAgg) {
        if (!healthAgg) return;

        const dimensions = [
            { key: 'pdf_health', label: 'PDF Health', okLabel: 'Healthy', failLabel: 'Broken' },
            { key: 'ocr_health', label: 'OCR Health', okLabel: 'Done', failLabel: 'Pending/Failed' },
            { key: 'note_health', label: 'Note Health', okLabel: 'Present', failLabel: 'Missing' },
            { key: 'asset_health', label: 'Asset Health', okLabel: 'Valid', failLabel: 'Drifted' },
        ];

        const grid = container.createEl('div', { cls: 'paperforge-collection-health' });

        for (const dim of dimensions) {
            const data = healthAgg[dim.key] || { healthy: 0, unhealthy: 0 };
            const cell = grid.createEl('div', { cls: 'paperforge-collection-health-cell' });
            cell.createEl('div', { cls: 'paperforge-collection-health-cell-label', text: dim.label });

            const counts = cell.createEl('div', { cls: 'paperforge-collection-health-counts' });
            const okSpan = counts.createEl('span', { cls: 'ok', text: String(data.healthy) + ' ' + dim.okLabel });
            counts.createEl('span', { text: ' \u00B7 ' });
            const failSpan = counts.createEl('span', { cls: 'fail', text: String(data.unhealthy) + ' ' + dim.failLabel });
        }
    }

    /* ── Refresh current mode (called on index change, D-09, REFR-01) ── */
    _refreshCurrentMode() {
        if (!this._currentMode) return;
        this._contentEl.empty();
        this._contentEl.addClass('switching');
        this._invalidateIndex(); // force fresh data load

        this._renderModeHeader(this._currentMode);

        switch (this._currentMode) {
            case 'global':
                this._renderGlobalMode();
                break;
            case 'paper':
                this._renderPaperMode();
                break;
            case 'collection':
                this._renderCollectionMode();
                break;
            case 'deep-reading':
                this._renderDeepReadingMode();
                break;
        }

        // Brief delay before removing switching class for smooth fade transition
        setTimeout(() => {
            if (this._contentEl) this._contentEl.removeClass('switching');
        }, 50);
    }

    /* ── Run Action ── */
    _runAction(a, card) {
        // DASH-03: OCR privacy warning — once per session
        if (a.id === 'paperforge-ocr' && !this._ocrPrivacyShown) {
            const modal = new PaperForgeOcrPrivacyModal(this.app, () => {
                this._ocrPrivacyShown = true;
                this._runAction(a, card);  // Re-trigger after acknowledgment
            });
            modal.open();
            return;
        }
        // Guard: disabled actions show coming-soon notice
        if (a.disabled) {
            new Notice(`[i] ${a.disabledMsg || 'This action is not yet available.'}`, 6000);
            return;
        }
        // Guard: prevent running the same action simultaneously
        if (card.classList.contains('running')) {
            return;
        }
        card.addClass('running');
        const vp = this.app.vault.adapter.basePath;
        this._showMessage('Processing...', 'running');

        // Resolve extra arguments based on action flags
        let extraArgs = Array.isArray(a.args) ? [...a.args] : [];

        if (a.needsKey) {
            // Resolve zotero_key from active file frontmatter
            const activeFile = this.app.workspace.getActiveFile();
            let key = null;
            if (activeFile) {
                const cache = this.app.metadataCache.getFileCache(activeFile);
                if (cache && cache.frontmatter && cache.frontmatter.zotero_key) {
                    key = cache.frontmatter.zotero_key;
                } else if (cache && cache.frontmatter) {
                    this._showMessage('[!!] No zotero_key in active note frontmatter', 'error');
                    new Notice('[!!] Open a paper note with a zotero_key in its frontmatter first', 6000);
                    card.removeClass('running');
                    return;
                } else {
                    this._showMessage('[!!] No frontmatter in active note', 'error');
                    new Notice('[!!] The active note has no frontmatter with a zotero_key', 6000);
                    card.removeClass('running');
                    return;
                }
            } else {
                this._showMessage('[!!] No active note open', 'error');
                new Notice('[!!] Open a paper note with a zotero_key in its frontmatter first', 6000);
                card.removeClass('running');
                return;
            }
            extraArgs = [...extraArgs, key];
        }

        if (a.needsFilter) {
            // Default to --all for the initial implementation
            extraArgs = [...extraArgs, '--all'];
        }

        const { spawn } = require('node:child_process');
        const cmdTimeout = a.needsFilter ? 60000 : (a.needsKey ? 30000 : 600000);
        const { path: pythonExe, extraArgs: pyExtra = [] } = resolvePythonExecutable(vp, this.app.plugins.plugins['paperforge']?.settings);
        const child = spawn(pythonExe, [...pyExtra, '-m', 'paperforge', a.cmd, ...extraArgs], { cwd: vp, timeout: cmdTimeout });
        const log = [];
        const startTime = Date.now();
        const pollTimer = setInterval(() => this._fetchStats(true), 4000);
        child.stdout.on('data', (data) => {
            const lines = data.toString('utf-8').split('\n').filter(Boolean);
            for (const l of lines) {
                const clean = l.trim();
                if (clean) { log.push(clean); this._showMessage(log.slice(-8).join('\n'), 'running'); }
            }
        });
        child.stderr.on('data', (data) => {
            const lines = data.toString('utf-8').split('\n').filter(Boolean);
            for (const l of lines) {
                if (l.includes('\r') || l.includes('%') || l.includes('█')) continue;
                const trim = l.trim();
                if (trim && !trim.match(/^\d+%|^\|/)) { log.push(trim); this._showMessage(log.slice(-8).join('\n'), 'running'); }
            }
        });
        child.on('close', (code) => {
            clearInterval(pollTimer);
            card.removeClass('running');
            const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
            if (code !== 0) {
                const last = log.slice(-3).join(' | ') || 'exit code ' + code;
                if (a.cmd === 'repair' && code === 1) {
                    this._showMessage('[WARN] ' + last, 'running');
                    new Notice('[WARN] Repair completed with remaining issues: ' + last, 8000);
                    this._fetchStats(true);
                } else {
                    this._showMessage('[!!] ' + last, 'error');
                    new Notice('[!!] ' + a.cmd + ' failed: ' + last, 8000);
                }
            } else if (a.needsKey || a.needsFilter) {
                // Context actions: copy JSON output to clipboard
                const output = log.join('\n');
                if (output.trim()) {
                    try {
                        JSON.parse(output);
                        navigator.clipboard.writeText(output).then(() => {
                            const summary = `${elapsed}s \u2014 ${output.length} chars copied`;
                            this._showMessage('[OK] ' + a.title + ': ' + summary, 'ok');
                            new Notice('[OK] ' + a.okMsg + ' \u2014 ' + output.length + ' chars');
                        }).catch((err) => {
                            this._showMessage('[!!] Clipboard write failed: ' + err.message, 'error');
                            new Notice('[!!] Clipboard error', 6000);
                        });
                    } catch (e) {
                        this._showMessage('[!!] Invalid JSON from ' + a.title, 'error');
                        new Notice('[!!] ' + a.title + ' returned invalid JSON: ' + e.message.slice(0, 100), 8000);
                    }
                } else {
                    this._showMessage('[!!] No output from context command', 'error');
                    new Notice('[!!] Context command returned empty output', 8000);
                }
                this._fetchStats(true);
            } else {
                // Existing actions (sync, ocr, doctor, repair): build summary from log lines
                const updated = log.filter(l => l.match(/updated \d+/));
                const lastUpdated = updated.pop() || log[log.length - 1] || '';
                const summary = `${elapsed}s \u2014 ${lastUpdated}`;
                this._showMessage('[OK] ' + a.title + ': ' + summary, 'ok');
                new Notice('[OK] ' + a.okMsg);
                this._fetchStats(true);
            }
        });
        child.on('error', (err) => {
            card.removeClass('running');
            this._showMessage('[!!] ' + err.message, 'error');
            new Notice('[!!] Cannot start: ' + err.message, 8000);
        });
    }

    _showMessage(msg, cls) {
        if (this._messageEl) {
            this._messageEl.setText(msg);
            this._messageEl.className = `paperforge-message msg-${cls}`;
        }
    }

    /* ── Mode-Aware Header (D-07) ── */
    _renderModeHeader(mode) {
        this._modeContextEl.empty();

        // Build mode badge
        const badge = this._modeContextEl.createEl('span', { cls: 'paperforge-mode-badge' });
        let modeName = '';

        switch (mode) {
            case 'global':
                badge.addClass('global');
                badge.setText('Global');
                this._headerTitle.setText('PaperForge');
                break;

            case 'paper':
                badge.addClass('paper');
                badge.setText('Paper');
                this._headerTitle.setText('Paper');
                if (this._currentPaperEntry && this._currentPaperEntry.title) {
                    modeName = this._currentPaperEntry.title;
                } else if (this._currentPaperKey) {
                    modeName = this._currentPaperKey;
                    // Show warning if entry not found (D-18)
                    this._modeContextEl.createEl('span', {
                        cls: 'paperforge-mode-warning',
                        text: 'Not found in index',
                    });
                } else {
                    modeName = 'Unknown paper';
                }
                break;

            case 'collection':
                badge.addClass('collection');
                badge.setText('Collection');
                this._headerTitle.setText('Collection');
                modeName = this._currentDomain || 'Unknown Domain';
                break;

            case 'deep-reading':
                badge.addClass('deep-reading');
                badge.setText('Deep');
                this._headerTitle.setText('Deep Reading');
                if (this._currentPaperEntry && this._currentPaperEntry.title) {
                    modeName = this._currentPaperEntry.title;
                } else if (this._currentPaperKey) {
                    modeName = this._currentPaperKey;
                } else {
                    modeName = 'Unknown paper';
                }
                break;
        }

        if (modeName) {
            this._modeContextEl.createEl('span', {
                cls: 'paperforge-mode-name',
                text: modeName,
            });
        }
    }

    /* ── Event Subscriptions (D-08, D-09, D-19) ── */
    _setupEventSubscriptions() {
        // D-08: Active leaf change -- debounced with 300ms delay
        const leafHandler = this.app.workspace.on('active-leaf-change', () => {
            clearTimeout(this._leafChangeTimer);
            this._leafChangeTimer = setTimeout(() => {
                this._detectAndSwitch();
            }, 300);
        });
        this._modeSubscribers.push({ event: 'active-leaf-change', ref: leafHandler });

        // D-09: File modification -- filter to formal-library.json only
        const modifyHandler = this.app.vault.on('modify', (file) => {
            if (file && file.path && file.path.endsWith('formal-library.json')) {
                this._invalidateIndex();  // D-14: invalidate cache
                this._refreshCurrentMode();
            }
        });
        this._modeSubscribers.push({ event: 'modify', ref: modifyHandler });
    }

    /* ── Static: open or reveal view ── */
    static async open(plugin) {
        const leaves = plugin.app.workspace.getLeavesOfType(VIEW_TYPE_PAPERFORGE);
        if (leaves.length > 0) {
            plugin.app.workspace.revealLeaf(leaves[0]);
            return;
        }
        const leaf = plugin.app.workspace.getRightLeaf(false);
        if (leaf) {
            await leaf.setViewState({ type: VIEW_TYPE_PAPERFORGE, active: true });
            plugin.app.workspace.revealLeaf(leaf);
        }
    }
}

class PaperForgeSettingTab extends PluginSettingTab {
    constructor(app, plugin) {
        super(app, plugin);
        this.plugin = plugin;
        this._saveTimeout = null;
        this._pfConfig = null;  // cached paperforge.json config
    }

    /** Reload path config from paperforge.json */
    _refreshPfConfig() {
        this._pfConfig = this.plugin.readPaperforgeJson();
    }

    display() {
        const { containerEl } = this;
        containerEl.empty();
        this._refreshPfConfig();

        const vaultPath = this.app.vault.adapter.basePath;
        if (!this.plugin.settings.vault_path) {
            this.plugin.settings.vault_path = vaultPath;
            this._debouncedSave();
        }

        /* ── Validate setup_complete against paperforge.json ── */
        if (this.plugin.settings.setup_complete) {
            const fs = require('fs');
            const path = require('path');
            if (!fs.existsSync(path.join(vaultPath, 'paperforge.json'))) {
                this.plugin.settings.setup_complete = false;
                this._debouncedSave();
            }
        }

        /* ── Header ── */
        containerEl.createEl('h2', { text: t('header_title') || 'PaperForge' });
        containerEl.createEl('p', {
            text: t('desc'),
            cls: 'paperforge-settings-desc'
        });

        /* ── Setup Status ── */
        const statusRow = containerEl.createEl('div', { cls: 'paperforge-setup-bar' });
        const statusLabel = statusRow.createEl('span', { cls: 'paperforge-setup-label' });
        if (this.plugin.settings.setup_complete) {
            statusLabel.setText(t('setup_done'));
            statusLabel.addClass('paperforge-setup-done');
        } else {
            statusLabel.setText(t('setup_pending'));
            statusLabel.addClass('paperforge-setup-pending');
        }

        /* ── Python Interpreter Section ── */
        const vaultPathForPython = this.app.vault.adapter.basePath;
        const pyResult = resolvePythonExecutable(vaultPathForPython, this.plugin.settings);
        const pyPath = pyResult.path;
        const pySource = this.plugin.settings._python_path_stale ? 'stale' : pyResult.source;

        // 2a — Read-only current interpreter row
        const pyInterpSetting = new Setting(containerEl)
            .setName(t('field_python_interp'))
            .setDesc(this._getPythonDesc(pyPath, pySource));
        this._pythonInterpDescEl = pyInterpSetting.descEl;

        // 2b+2c — Manual override text input + Validate button
        const customSetting = new Setting(containerEl)
            .setName(t('field_python_custom'))
            .setDesc('');
        this._customPathDescEl = customSetting.descEl;

        customSetting.addText(text => {
            text.setPlaceholder('e.g. C:\\Python310\\python.exe')
                .setValue(this.plugin.settings.python_path || '')
                .onChange(value => {
                    this.plugin.settings.python_path = value;
                    this.plugin.saveSettings();

                    // Clear stale flag when user modifies the path
                    if (value && value.trim()) {
                        const fs = require('fs');
                        const exists = fs.existsSync(value.trim());
                        this.plugin.settings._python_path_stale = !exists;
                    } else {
                        this.plugin.settings._python_path_stale = false;
                    }

                    // Re-render the read-only Python interpreter row desc
                    const pyResult2 = resolvePythonExecutable(this.app.vault.adapter.basePath, this.plugin.settings);
                    const pySource2 = this.plugin.settings._python_path_stale ? 'stale' : pyResult2.source;
                    if (this._pythonInterpDescEl) {
                        this._pythonInterpDescEl.textContent = this._getPythonDesc(pyResult2.path, pySource2);
                    }
                });
        });

        customSetting.addButton(btn => {
            btn.setButtonText(t('btn_validate'))
                .onClick(() => this._validatePythonOverride());
        });

        /* ── Runtime Health Section ── */
        containerEl.createEl('h3', { text: t('runtime_health') });
        containerEl.createEl('p', { text: t('runtime_health_desc'), cls: 'paperforge-settings-desc' });

        const versionRow = new Setting(containerEl)
            .setName('PaperForge')
            .setDesc(t('runtime_health_checking'));

        const badgeEl = versionRow.descEl.createEl('span', { cls: 'paperforge-runtime-badge' });
        let syncBtn = null;

        versionRow.addButton(btn => {
            syncBtn = btn;
            btn.setButtonText(t('runtime_health_sync'))
                .setDisabled(true)
                .onClick(() => this._syncRuntime(btn));
        });

        // Fetch version asynchronously
        {
            const vp = this.app.vault.adapter.basePath;
            const { path: pythonExe, extraArgs = [] } = resolvePythonExecutable(vp, this.plugin.settings);
            const pluginVer = this.plugin.manifest.version || '?';

            execFile(pythonExe, [...extraArgs, '-c', 'import paperforge; print(paperforge.__version__)'], { cwd: vp, timeout: 10000 }, (err, stdout) => {
                const pyVer = (!err && stdout) ? stdout.trim() : null;
                const descText = pyVer
                    ? `${t('runtime_health_plugin_ver').replace('{0}', pluginVer)} → ${t('runtime_health_package_ver').replace('{0}', pyVer)}`
                    : `Plugin v${pluginVer} → Python package not installed`;
                versionRow.setDesc(descText);
                if (pyVer === pluginVer) {
                    badgeEl.setText(t('runtime_health_match'));
                    badgeEl.className = 'paperforge-runtime-badge match';
                    if (syncBtn) syncBtn.setDisabled(true);
                } else if (pyVer) {
                    badgeEl.setText(t('runtime_health_mismatch'));
                    badgeEl.className = 'paperforge-runtime-badge mismatch';
                    if (syncBtn) syncBtn.setDisabled(false);
                } else {
                    badgeEl.setText('Not installed');
                    badgeEl.className = 'paperforge-runtime-badge missing';
                    if (syncBtn) syncBtn.setDisabled(false);
                }
            });
        }

        /* ── Preparation Guide ── */
        containerEl.createEl('h3', { text: t('section_prep') });
        containerEl.createEl('p', { text: t('section_prep_desc'), cls: 'paperforge-settings-desc' });
        const prep = containerEl.createEl('div', { cls: 'paperforge-guide' });
        const prepData = [
            ['prep_python', 'prep_python_desc'],
            ['prep_zotero', 'prep_zotero_desc'],
            ['prep_bbt', 'prep_bbt_desc'],
            ['prep_key', 'prep_key_desc'],
        ];
        for (const [kTitle, kDesc] of prepData) {
            const row = prep.createEl('div', { cls: 'paperforge-guide-item' });
            row.createEl('strong', { text: t(kTitle) });
            row.createEl('span', { text: ' — ' + t(kDesc) });
        }

        /* ── Pre-check status area ── */
        this._checkEl = containerEl.createEl('div', { cls: 'paperforge-message' });

        /* ── Install / Reconfigure Button ── */
        const needSetup = !this.plugin.settings.setup_complete;
        new Setting(containerEl)
            .setName(t(needSetup ? 'btn_install' : 'btn_reconfig'))
            .setDesc(t(needSetup ? 'btn_install_desc' : 'btn_reconfig_desc'))
            .addButton((btn) => {
                btn.setButtonText(t(needSetup ? 'btn_install' : 'btn_reconfig'))
                    .setCta()
                    .onClick(() => {
                        if (!needSetup) {
                            new PaperForgeSetupModal(this.app, this.plugin).open();
                        } else {
                            this._preCheck(() => {
                                new PaperForgeSetupModal(this.app, this.plugin).open();
                            });
                        }
                    });
            });

        /* ── Operation Guide ── */
        containerEl.createEl('h3', { text: t('section_guide') });
        const guide = containerEl.createEl('div', { cls: 'paperforge-guide' });
        const guideData = [
            ['guide_open', 'guide_open_desc'],
            ['guide_sync', 'guide_sync_desc'],
            ['guide_ocr', 'guide_ocr_desc'],
        ];
        for (const [kTitle, kDesc] of guideData) {
            const row = guide.createEl('div', { cls: 'paperforge-guide-item' });
            row.createEl('strong', { text: t(kTitle) });
            row.createEl('span', { text: ' — ' + t(kDesc) });
        }

        /* ── Config Summary (only after install) ── */
        if (this.plugin.settings.setup_complete) {
            containerEl.createEl('h3', { text: t('section_config') });
            const summary = containerEl.createEl('div', { cls: 'paperforge-summary' });
            const s = this.plugin.settings;
            const pf = this._pfConfig;  // source of truth for path fields
            const items = [
                { label: t('dir_vault'), val: vaultPath },
                { label: t('dir_resources'), val: `${vaultPath}/${pf.resources_dir}` },
                { label: '  ' + t('dir_notes'), val: `${vaultPath}/${pf.resources_dir}/${pf.literature_dir}` },
                { label: '  ' + t('dir_index'), val: `${vaultPath}/${pf.resources_dir}/${pf.control_dir}` },
                { label: t('dir_base'), val: `${vaultPath}/${pf.base_dir}` },
                { label: t('dir_system'), val: `${vaultPath}/${pf.system_dir}` },
                { label: 'API Key', val: s.paddleocr_api_key ? t('api_key_set') : t('api_key_missing') },
                { label: t('field_zotero_data'), val: s.zotero_data_dir || t('not_set') },
            ];
            for (const item of items) {
                const row = summary.createEl('div', { cls: 'paperforge-summary-row' });
                row.createEl('span', { cls: 'paperforge-summary-label', text: item.label });
                row.createEl('span', { cls: 'paperforge-summary-value', text: item.val });
            }
        }
    }

    _getPythonDesc(pyPath, source) {
        if (source === 'stale') {
            return `[!!] ${pyPath} (stale — path no longer exists, update or clear the override below)`;
        }
        if (source === 'manual') {
            return `${pyPath} (manual)`;
        }
        return `${pyPath} (auto-detected)`;
    }

    _refreshPythonInterpDesc(pyPath, source) {
        const desc = this._pythonInterpDescEl;
        if (desc) {
            if (source === 'stale') {
                desc.textContent = `[!!] ${pyPath} (stale — path no longer exists, update or clear the override below)`;
            } else if (source === 'manual') {
                desc.textContent = `${pyPath} (manual)`;
            } else {
                desc.textContent = `${pyPath} (auto-detected)`;
            }
        }
    }

    _validatePythonOverride() {
        const fs = require('fs');
        const { execFile } = require('node:child_process');
        const customPath = this.plugin.settings.python_path ? this.plugin.settings.python_path.trim() : '';
        const desc = this._customPathDescEl;

        if (!customPath) {
            const msg = '请输入路径 / Enter a path first';
            if (desc) desc.textContent = msg;
            new Notice(msg);
            return;
        }

        // Check exists
        if (!fs.existsSync(customPath)) {
            const msg = '路径不存在 / Path does not exist';
            if (desc) desc.innerHTML = `<span style="color:var(--text-error)">\u2717 ${msg}</span>`;
            new Notice(msg, 4000);
            return;
        }

        // Check executable
        try {
            fs.accessSync(customPath, fs.constants.X_OK);
        } catch {
            const msg = '不可执行 / Not executable';
            if (desc) desc.innerHTML = `<span style="color:var(--text-error)">\u2717 ${msg}</span>`;
            new Notice(msg, 4000);
            return;
        }

        // Check version >= 3.10
        execFile(customPath, ['--version'], { timeout: 8000 }, (verErr, verOut) => {
            if (verErr || !verOut) {
                const msg = '无法运行 / Cannot run';
                if (desc) desc.innerHTML = `<span style="color:var(--text-error)">\u2717 ${msg}</span>`;
                new Notice(msg, 4000);
                return;
            }

            const match = verOut.match(/Python (\d+)\.(\d+)/);
            if (!match) {
                const msg = '无法解析版本 / Cannot parse version';
                if (desc) desc.innerHTML = `<span style="color:var(--text-error)">\u2717 ${msg}</span>`;
                new Notice(msg, 4000);
                return;
            }

            const major = parseInt(match[1], 10);
            const minor = parseInt(match[2], 10);

            if (major < 3 || (major === 3 && minor < 10)) {
                const msg = 'Python 版本过低，需要 3.10+ / Python version too low, need 3.10+';
                if (desc) desc.innerHTML = `<span style="color:var(--text-error)">\u2717 ${msg}</span>`;
                new Notice(msg, 4000);
                return;
            }

            // Check pip
            execFile(customPath, ['-m', 'pip', '--version'], { timeout: 8000 }, (pipErr) => {
                if (pipErr) {
                    const warnMsg = `\u2713 Python ${major}.${minor} 有效，但未检测到 pip / Valid, but pip not found`;
                    if (desc) desc.innerHTML = `<span style="color:var(--text-warning)">\u26A0 ${warnMsg}</span>`;
                    new Notice(warnMsg, 4000);
                } else {
                    const okMsg = `\u2713 Python ${major}.${minor} 有效 / Valid`;
                    if (desc) desc.innerHTML = `<span style="color:var(--text-accent)">${okMsg}</span>`;
                    new Notice(okMsg, 4000);
                }
            });
        });
    }

    _syncRuntime(btn) {
        const vp = this.app.vault.adapter.basePath;
        const { path: pythonExe, extraArgs = [] } = resolvePythonExecutable(vp, this.plugin.settings);
        const ver = this.plugin.manifest.version || '1.4.17rc2';
        const url = `git+https://github.com/LLLin000/PaperForge.git@${ver}`;
        const spawn = require('node:child_process').spawn;

        btn.setDisabled(true);
        btn.setButtonText(t('runtime_health_syncing'));

        const child = spawn(pythonExe, [...extraArgs, '-m', 'pip', 'install', '--upgrade', url], { cwd: vp, timeout: 120000 });
        child.on('close', (code) => {
            if (code === 0) {
                new Notice(t('runtime_health_sync_done').replace('{0}', ver), 5000);
                this.display();
            } else {
                btn.setDisabled(false);
                btn.setButtonText(t('runtime_health_sync'));
                new Notice(t('runtime_health_sync_fail').replace('{0}', 'pip exit code ' + code), 8000);
            }
        });
        child.on('error', (e) => {
            btn.setDisabled(false);
            btn.setButtonText(t('runtime_health_sync'));
            new Notice(t('runtime_health_sync_fail').replace('{0}', e.message), 8000);
        });
    }

    _debouncedSave() {
        clearTimeout(this._saveTimeout);
        this._saveTimeout = setTimeout(() => this.plugin.saveSettings(), 500);
    }

    _preCheck(onPass) {
        const fs = require('fs');
        const path = require('path');
        const { execFile } = require('node:child_process');
        const vaultPath = this.app.vault.adapter.basePath;
        const { path: pythonExe, extraArgs = [] } = resolvePythonExecutable(vaultPath, this.plugin?.settings);
        execFile(pythonExe, [...extraArgs, '--version'], { timeout: 8000 }, (pyErr, pyOut) => {
            const results = [];

            /* 1 — Python */
            results.push({ label: 'Python', ok: !pyErr, detail: pyErr ? t('check_python_fail') : pyOut.trim() });

            /* 2 — Zotero (check install + data dir) */
            let zotOk = false;
            // Try common install locations
            const progFiles = process.env.ProgramFiles || '';
            const localAppData = process.env.LOCALAPPDATA || '';
            const home = process.env.USERPROFILE || process.env.HOME || '';
            const zotInstallDirs = [
                path.join(progFiles, 'Zotero'),
                path.join(progFiles, '(x86)', 'Zotero'),
                path.join(localAppData, 'Programs', 'Zotero'),
                path.join(localAppData, 'Zotero'),
                path.join(home, 'AppData', 'Local', 'Programs', 'Zotero'),
            ].filter(Boolean);
            zotOk = zotInstallDirs.some(d => { try { return fs.existsSync(d); } catch { return false; } });
            // Fallback: check if data dir is configured
            const zotDataDir = this.plugin.settings.zotero_data_dir;
            if (!zotOk && zotDataDir) {
                try { zotOk = fs.existsSync(zotDataDir); } catch {}
            }
            results.push({ label: 'Zotero', ok: zotOk, detail: zotOk ? t('check_zotero_ok') : t('check_zotero_fail') });

            /* 3 — Better BibTeX (recursive search) */
            function scanBbt(dir) {
                if (!dir) return false;
                try {
                    if (!fs.existsSync(dir)) return false;
                    for (const entry of fs.readdirSync(dir)) {
                        const full = path.join(dir, entry);
                        try {
                            if (fs.statSync(full).isDirectory()) {
                                if (entry.startsWith('better-bibtex')) return true;
                                // Recurse one level into common Zotero subdirs
                                if (entry === 'extensions' || entry === 'Profiles') {
                                    if (scanBbt(full)) return true;
                                }
                            }
                        } catch {}
                    }
                } catch {}
                return false;
            }
            let bbtOk = false;
            const appData = process.env.APPDATA || '';
            // 1) Standard: %APPDATA%\Zotero\Zotero\
            if (!bbtOk && appData) {
                bbtOk = scanBbt(path.join(appData, 'Zotero', 'Zotero'));
            }
            // 2) Fallback: user-configured zotero_data_dir
            if (!bbtOk && zotDataDir) {
                bbtOk = scanBbt(zotDataDir);
            }
            results.push({ label: 'Better BibTeX', ok: bbtOk, detail: bbtOk ? t('check_bbt_ok') : t('check_bbt_fail') });

            /* Render */
            const marks = { true: '✓', false: '✗' };
            if (this._checkEl) {
                this._checkEl.setText(results.map(r => `${marks[r.ok]} ${r.label}: ${r.detail}`).join('\n'));
                const anyFail = results.some(r => !r.ok);
                this._checkEl.className = `paperforge-message msg-${anyFail ? 'error' : 'ok'}`;
            }
            const bad = results.filter(r => !r.ok);
            if (bad.length > 0) {
                new Notice(`[!!] 未通过: ${bad.map(r => r.label).join(', ')}`, 6000);
            }

            onPass();
        });
    }
}

/* ── OCR Privacy Warning Modal (DASH-03) ── */
class PaperForgeOcrPrivacyModal extends Modal {
    constructor(app, onConfirm) {
        super(app);
        this._onConfirm = onConfirm;
    }

    onOpen() {
        const { contentEl } = this;
        contentEl.addClass('paperforge-modal');
        contentEl.addClass('paperforge-ocr-privacy-modal');

        // Title
        contentEl.createEl('h2', { text: t('ocr_privacy_title') });

        // Warning text
        const warningEl = contentEl.createEl('div', { cls: 'paperforge-ocr-privacy-warning' });
        warningEl.createEl('p', { text: t('ocr_privacy_warning') });

        // "I Understand" button
        const btnRow = contentEl.createEl('div', { cls: 'paperforge-ocr-privacy-actions' });
        const confirmBtn = btnRow.createEl('button', {
            cls: 'paperforge-step-btn mod-cta',
            text: t('ocr_understand'),
        });
        confirmBtn.addEventListener('click', () => {
            this.close();
            if (this._onConfirm) this._onConfirm();
        });
    }

    onClose() {
        this.contentEl.empty();
    }
}

/* ==========================================================================
   Setup Wizard Modal
   ========================================================================== */
class PaperForgeSetupModal extends Modal {
    constructor(app, plugin) {
        super(app);
        this.plugin = plugin;
        this._step = 1;
    }

    onOpen() {
        this._render();
    }

    onClose() {
        this.contentEl.empty();
    }

    _render() {
        const { contentEl } = this;
        contentEl.empty();
        contentEl.addClass('paperforge-modal');

        this._renderStepIndicator();
        this._renderStepContent();
        this._renderNavigation();
    }

    _renderStepIndicator() {
        const steps = [t('wizard_step1'), t('wizard_step2'), t('wizard_step3'), t('wizard_step4'), t('wizard_step5')];
        const bar = this.contentEl.createEl('div', { cls: 'paperforge-step-bar' });
        steps.forEach((label, i) => {
            const n = i + 1;
            const dot = bar.createEl('div', {
                cls: `paperforge-step-dot ${n === this._step ? 'active' : ''} ${n < this._step ? 'done' : ''}`
            });
            dot.createEl('span', { cls: 'paperforge-step-num', text: `${n}` });
            dot.createEl('span', { cls: 'paperforge-step-label', text: label });
        });
    }

    _renderStepContent() {
        const el = this.contentEl.createEl('div', { cls: 'paperforge-step-content' });
        switch (this._step) {
            case 1: this._stepOverview(el); break;
            case 2: this._stepDirectories(el); break;
            case 3: this._stepKeys(el); break;
            case 4: this._stepInstall(el); break;
            case 5: this._stepComplete(el); break;
        }
    }

    _renderNavigation() {
        const nav = this.contentEl.createEl('div', { cls: 'paperforge-step-nav' });
        if (this._step > 1) {
            nav.createEl('button', { cls: 'paperforge-step-btn', text: t('nav_prev') })
                .addEventListener('click', () => { this._step--; this._render(); });
        }
        if (this._step < 5) {
            const nextBtn = nav.createEl('button', { cls: 'paperforge-step-btn mod-cta', text: t('nav_next') });
            nextBtn.addEventListener('click', () => {
                if (this._step === 3 && !this._validateStep3()) return;
                this._step++;
                this._render();
            });
        } else {
            nav.createEl('button', { cls: 'paperforge-step-btn', text: t('nav_close') })
                .addEventListener('click', () => this.close());
        }
    }

    _validateStep3() {
        const s = this.plugin.settings;
        const fs = require('fs');

        // Check API key validated
        if (!this._apiKeyValidated) {
            new Notice('请先验证 PaddleOCR API 密钥');
            return false;
        }

        // Check Zotero data directory: required + exists + is directory + has storage/
        if (!s.zotero_data_dir || !s.zotero_data_dir.trim()) {
            new Notice('Zotero 数据目录为必填项，请填写路径');
            return false;
        }
        const zotPath = s.zotero_data_dir.trim();
        if (!fs.existsSync(zotPath)) {
            new Notice('Zotero 数据目录路径不存在');
            return false;
        }
        if (!fs.statSync(zotPath).isDirectory()) {
            new Notice('Zotero 数据目录路径不是一个目录');
            return false;
        }
        const storagePath = path.join(zotPath, 'storage');
        if (!fs.existsSync(storagePath) || !fs.statSync(storagePath).isDirectory()) {
            new Notice('Zotero 数据目录中未找到 storage/ 子目录');
            return false;
        }

        return true;
    }

    /* ── Step 1: Overview ── */
    _stepOverview(el) {
        el.createEl('h2', { text: t('wizard_title') });
        el.createEl('p', { text: t('wizard_intro') });

        const s = this.plugin.settings;
        const vault = this.app.vault.adapter.basePath;
        const tree = el.createEl('div', { cls: 'paperforge-dir-tree' });
        // HARDEN-05: Use createEl() DOM API instead of innerHTML to prevent XSS
        // from user-configured directory names containing HTML/script tags.
        const rootNode = tree.createEl('div', { cls: 'paperforge-dir-node root' });
        rootNode.textContent = `📁 Vault (${vault})`;

        const children = tree.createEl('div', { cls: 'paperforge-dir-children' });

        const resourcesFolder = children.createEl('div', { cls: 'paperforge-dir-node folder' });
        resourcesFolder.textContent = `📁 ${s.resources_dir || 'Resources'}/ — 文献卡片目录（Base 数据来源）`;
        const resourcesChildren = resourcesFolder.createEl('div', { cls: 'paperforge-dir-children' });
        resourcesChildren.createEl('div', { cls: 'paperforge-dir-node file',
            text: `📁 ${s.literature_dir || 'Literature'}/ — 文献卡片` });

        children.createEl('div', { cls: 'paperforge-dir-node folder',
            text: `📁 ${s.base_dir || 'Bases'}/ — 数据管理面板` });
        children.createEl('div', { cls: 'paperforge-dir-node folder',
            text: `📁 ${s.system_dir || 'System'}/ — Zotero 软链接 + PaperForge 系统文件夹` });

        el.createEl('p', { text: t('wizard_preview'), cls: 'paperforge-modal-hint' });
        el.createEl('p', { text: t('wizard_safety'), cls: 'paperforge-modal-hint' });

        const summary = el.createEl('div', { cls: 'paperforge-summary' });
        const overviewItems = [
            { label: t('dir_resources'), val: `${vault}/${s.resources_dir || 'Resources'}` },
            { label: t('dir_notes'), val: `${vault}/${s.resources_dir || 'Resources'}/${s.literature_dir || 'Literature'}` },
            { label: t('dir_base'), val: `${vault}/${s.base_dir || 'Bases'}` },
            { label: t('dir_system'), val: `${vault}/${s.system_dir || 'System'}` },
        ];
        for (const item of overviewItems) {
            const row = summary.createEl('div', { cls: 'paperforge-summary-row' });
            row.createEl('span', { cls: 'paperforge-summary-label', text: item.label });
            row.createEl('span', { cls: 'paperforge-summary-value', text: item.val });
        }
    }

    /* ── Step 2: Directory Config (editable) ── */
    _stepDirectories(el) {
        el.createEl('h2', { text: t('wizard_step2') });
        el.createEl('p', { text: t('wizard_intro') });

        const s = this.plugin.settings;
        const vault = this.app.vault.adapter.basePath;

        this._modalField(el, t('dir_vault'), vault, true);

        el.createEl('p', { text: t('wizard_dir_hint'), cls: 'paperforge-modal-hint' });

        this._modalInput(el, '资源目录（创建文献卡片目录的地方）', 'resources_dir', s.resources_dir, 'Resources');

        el.createEl('p', { text: t('wizard_dir_sub_hint'), cls: 'paperforge-modal-hint' });

        this._modalInput(el, '文献卡片目录（存放文献卡片的地方，Base 数据来源）', 'literature_dir', s.literature_dir, 'Literature');

        el.createEl('p', { text: t('wizard_sys_hint'), cls: 'paperforge-modal-hint' });

        this._modalInput(el, '系统目录（存放 Zotero 软链接和 PaperForge 系统文件）', 'system_dir', s.system_dir, 'System');
        this._modalInput(el, 'Base 目录（存放数据管理面板的地方）', 'base_dir', s.base_dir, 'Bases');

        el.createEl('p', { text: t('wizard_safety'), cls: 'paperforge-modal-hint' });
        const preview = el.createEl('div', { cls: 'paperforge-summary' });
        const previewItems = [
            { label: t('dir_resources'), val: `${vault}/${s.resources_dir || ''}` },
            { label: t('dir_notes'), val: `${vault}/${s.resources_dir || ''}/${s.literature_dir || ''}` },
            { label: t('dir_index'), val: `${vault}/${s.resources_dir || ''}/${s.control_dir || ''}` },
            { label: t('dir_system'), val: `${vault}/${s.system_dir || ''}` },
            { label: t('dir_base'), val: `${vault}/${s.base_dir || ''}` },
        ];
        for (const item of previewItems) {
            const row = preview.createEl('div', { cls: 'paperforge-summary-row' });
            row.createEl('span', { cls: 'paperforge-summary-label', text: item.label });
            row.createEl('span', { cls: 'paperforge-summary-value', text: item.val });
        }
    }

    /* ── Step 3: Keys, Zotero & Agent ── */
    _stepKeys(el) {
        el.createEl('h2', { text: t('wizard_step3') });
        const s = this.plugin.settings;

        el.createEl('p', { text: t('wizard_agent_hint'), cls: 'paperforge-modal-hint' });

        const AGENTS = [
            { key: 'opencode', name: 'OpenCode' },
            { key: 'claude', name: 'Claude Code' },
            { key: 'cursor', name: 'Cursor' },
            { key: 'github_copilot', name: 'GitHub Copilot' },
            { key: 'windsurf', name: 'Windsurf' },
            { key: 'codex', name: 'Codex' },
            { key: 'cline', name: 'Cline' },
        ];
        const agentRow = el.createEl('div', { cls: 'paperforge-modal-field' });
        agentRow.createEl('label', { cls: 'paperforge-modal-label', text: t('label_agent') });
        const select = agentRow.createEl('select', { cls: 'paperforge-modal-select' });
        for (const a of AGENTS) {
            const opt = select.createEl('option', { text: a.name, attr: { value: a.key } });
            if (a.key === (s.agent_platform || 'opencode')) opt.selected = true;
        }
        select.addEventListener('change', () => {
            s.agent_platform = select.value;
            if (this._pendingSave) clearTimeout(this._pendingSave);
            this._pendingSave = setTimeout(() => { this.plugin.saveSettings(); this._pendingSave = null; }, 500);
        });

        el.createEl('p', { text: t('wizard_keys_hint'), cls: 'paperforge-modal-hint' });

        // PaddleOCR API Key with validate button
        const apiRow = el.createEl('div', { cls: 'paperforge-modal-field' });
        apiRow.createEl('label', { cls: 'paperforge-modal-label', text: t('field_paddleocr') });
        const apiInput = apiRow.createEl('input', {
            cls: 'paperforge-modal-input',
            attr: { type: 'password', placeholder: 'API Key' }
        });
        apiInput.value = s.paddleocr_api_key || '';
        this._apiKeyValidated = false;
        this._apiKeyStatus = apiRow.createEl('span', { cls: 'paperforge-apikey-status', text: '' });
        const validateBtn = apiRow.createEl('button', { cls: 'paperforge-step-btn', text: '验证' });
        validateBtn.addEventListener('click', () => this._validateApiKey(apiInput.value, validateBtn));
        apiInput.addEventListener('input', () => {
            s.paddleocr_api_key = apiInput.value;
            this._apiKeyValidated = false;
            this._apiKeyStatus.textContent = '';
            this._apiKeyStatus.className = 'paperforge-apikey-status';
        });
        if (this._pendingSave) clearTimeout(this._pendingSave);
        this._pendingSave = setTimeout(() => { this.plugin.saveSettings(); this._pendingSave = null; }, 500);

        // Zotero data directory (now required)
        const zotRow = el.createEl('div', { cls: 'paperforge-modal-field' });
        zotRow.createEl('label', { cls: 'paperforge-modal-label', text: t('field_zotero_data') });
        const zotInput = zotRow.createEl('input', {
            cls: 'paperforge-modal-input',
            attr: { type: 'text', placeholder: t('field_zotero_placeholder') }
        });
        zotInput.value = s.zotero_data_dir || '';
        zotInput.addEventListener('input', () => {
            s.zotero_data_dir = zotInput.value;
            if (this._pendingSave) clearTimeout(this._pendingSave);
            this._pendingSave = setTimeout(() => { this.plugin.saveSettings(); this._pendingSave = null; }, 500);
        });
    }

    _validateApiKey(key, btn) {
        if (!key || key.length < 10) {
            this._apiKeyStatus.textContent = '密钥格式不正确';
            this._apiKeyStatus.className = 'paperforge-apikey-status error';
            return;
        }
        btn.disabled = true;
        btn.textContent = '验证中…';
        this._apiKeyStatus.textContent = '正在验证…';
        this._apiKeyStatus.className = 'paperforge-apikey-status';

        const https = require('https');
        const postData = JSON.stringify({ model: 'PaddleOCR-VL-1.5' });
        const options = {
            hostname: 'paddleocr.aistudio-app.com',
            path: '/api/v2/ocr/jobs',
            method: 'POST',
            headers: {
                'Authorization': 'bearer ' + key,
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData),
            },
            timeout: 10000,
        };
        const req = https.request(options, (res) => {
            btn.disabled = false;
            btn.textContent = '验证';
            let body = '';
            res.on('data', (chunk) => body += chunk);
            res.on('end', () => {
                try {
                    const json = JSON.parse(body);
                    if (res.statusCode === 400 && json.code === 10001) {
                        // 400 code=10001 = auth passed, file missing (expected)
                        this._apiKeyStatus.textContent = '✓ 密钥有效';
                        this._apiKeyStatus.className = 'paperforge-apikey-status ok';
                        this._apiKeyValidated = true;
                    } else if (res.statusCode === 401) {
                        this._apiKeyStatus.textContent = '验证失败：密钥无效';
                        this._apiKeyStatus.className = 'paperforge-apikey-status error';
                        this._apiKeyValidated = false;
                    } else {
                        this._apiKeyStatus.textContent = '验证失败：API 返回 ' + res.statusCode;
                        this._apiKeyStatus.className = 'paperforge-apikey-status error';
                        this._apiKeyValidated = false;
                    }
                } catch (e) {
                    this._apiKeyStatus.textContent = '验证失败：无法解析响应';
                    this._apiKeyStatus.className = 'paperforge-apikey-status error';
                    this._apiKeyValidated = false;
                }
            });
        });
        req.on('error', (e) => {
            btn.disabled = false;
            btn.textContent = '验证';
            this._apiKeyStatus.textContent = '验证失败：无法连接 (' + e.message + ')';
            this._apiKeyStatus.className = 'paperforge-apikey-status error';
            this._apiKeyValidated = false;
        });
        req.write(postData);
        req.end();
    }

    /* ── Modal form helpers ── */
    _modalField(el, label, value, disabled) {
        const row = el.createEl('div', { cls: 'paperforge-modal-field' });
        row.createEl('label', { cls: 'paperforge-modal-label', text: label });
        const input = row.createEl('input', { cls: 'paperforge-modal-input', attr: { type: 'text' } });
        input.value = value;
        input.disabled = !!disabled;
    }

    _modalInput(el, label, key, value, placeholder) {
        const row = el.createEl('div', { cls: 'paperforge-modal-field' });
        row.createEl('label', { cls: 'paperforge-modal-label', text: label });
        const input = row.createEl('input', {
            cls: 'paperforge-modal-input',
            attr: { type: 'text', placeholder: placeholder || '' }
        });
        input.value = value;
        const settings = this.plugin.settings;
        input.addEventListener('input', () => {
            settings[key] = input.value;
            if (this._pendingSave) clearTimeout(this._pendingSave);
            this._pendingSave = setTimeout(() => {
                this.plugin.saveSettings();
                this._pendingSave = null;
            }, 500);
        });
    }

    _modalSecret(el, label, key, value, placeholder) {
        const row = el.createEl('div', { cls: 'paperforge-modal-field' });
        row.createEl('label', { cls: 'paperforge-modal-label', text: label });
        const input = row.createEl('input', {
            cls: 'paperforge-modal-input',
            attr: { type: 'password', placeholder: placeholder || '' }
        });
        input.value = value;
        const settings = this.plugin.settings;
        input.addEventListener('input', () => {
            settings[key] = input.value;
            if (this._pendingSave) clearTimeout(this._pendingSave);
            this._pendingSave = setTimeout(() => {
                this.plugin.saveSettings();
                this._pendingSave = null;
            }, 500);
        });
    }

    /* ── Step 4: Install ── */
    _stepInstall(el) {
        el.createEl('h2', { text: t('wizard_step4') });
        this._installLog = el.createEl('div', { cls: 'paperforge-install-log' });

        const startBtn = el.createEl('button', { cls: 'paperforge-step-btn mod-cta', text: t('install_btn') });
        startBtn.addEventListener('click', () => this._runInstall(startBtn));
    }

    async _runInstall(btn) {
        btn.disabled = true;
        btn.textContent = t('install_btn_running');
        this._installLog.setText(t('install_validating') + '\n');
        this._log(t('install_validating'));

        const s = this.plugin.settings;
        const errors = this._validate();
        if (errors.length > 0) {
            this._log(t('validate_fail') + ':');
            errors.forEach(e => this._log('  ✗ ' + e));
            btn.disabled = false;
            btn.textContent = t('install_btn_retry');
            return;
        }

        const { spawn } = require('node:child_process');
        const runPython = (args, options = {}) => new Promise((resolve, reject) => {
            const { path: pyExe, extraArgs: pyExtra = [] } = resolvePythonExecutable(s.vault_path.trim(), this.plugin.settings);
            const child = spawn(pyExe, [...pyExtra, ...args], {
                cwd: s.vault_path.trim(),
                env: process.env,
                timeout: 120000,
                ...options,
            });
            let stdout = '';
            let stderr = '';
            child.stdout.on('data', (data) => {
                const text = data.toString('utf-8');
                stdout += text;
                if (options.logStdout) this._processSetupOutput(text);
            });
            child.stderr.on('data', (data) => {
                const text = data.toString('utf-8');
                stderr += text;
                this._log('[stderr] ' + text.trim());
            });
            child.on('close', (code) => {
                code === 0 ? resolve({ stdout, stderr }) : reject(new Error(stderr.trim() || stdout.trim() || `exit code ${code}`));
            });
            child.on('error', (err) => reject(err));
        });

        const setupArgs = [
            '-m', 'paperforge',
            '--vault', s.vault_path.trim(),
            'setup', '--headless',
            '--system-dir', s.system_dir.trim(),
            '--resources-dir', s.resources_dir.trim(),
            '--literature-dir', s.literature_dir.trim(),
            '--control-dir', s.control_dir.trim(),
            '--base-dir', s.base_dir.trim(),
            '--agent', s.agent_platform || 'opencode',
        ];
        setupArgs.push('--zotero-data', s.zotero_data_dir.trim());

        try {
            let hasPaperforge = true;
            try {
                await runPython(['-c', 'import paperforge']);
            } catch {
                hasPaperforge = false;
            }

            if (!hasPaperforge) {
                this._log(t('install_bootstrapping'));
                const ver = this.plugin.manifest.version || '1.4.17rc2';
                await runPython([
                    '-m', 'pip', 'install', '--upgrade',
                    `git+https://github.com/LLLin000/PaperForge.git@${ver}`,
                ]);
            }

            await runPython(setupArgs, {
                logStdout: true,
                env: { ...process.env, PADDLEOCR_API_TOKEN: s.paddleocr_api_key.trim() },
            });
            this._log(t('install_complete'));
            s.setup_complete = true;
            await this.plugin.saveSettings();
            setTimeout(() => { this._step = 5; this._render(); }, 800);
        } catch (err) {
            console.error('PaperForge setup failed:', err.message);
            const errorMsg = this._formatSetupError(err.message);
            this._log(t('install_failed') + errorMsg);

            // Add "Copy diagnostic" button
            const diagBtn = this._installLog.parentElement?.createEl('button', {
                cls: 'paperforge-copy-diag-btn',
                text: t('error_copy_diagnostic') || 'Copy diagnostic',
            });
            if (diagBtn) {
                const rawError = err.message;
                const pyInfo = this.plugin?.settings?.python_path || 'auto';
                const pluginVer = this.plugin?.manifest?.version || '?';
                const osInfo = process.platform + ' ' + process.arch;
                const diagnostic = [
                    '[PaperForge Diagnostic]',
                    'Category: ' + errorMsg,
                    'Plugin version: ' + pluginVer,
                    'Python: ' + pyInfo,
                    'OS: ' + osInfo,
                    '--- Raw error ---',
                    rawError.slice(0, 2000),
                ].join('\n');
                diagBtn.addEventListener('click', () => {
                    navigator.clipboard.writeText(diagnostic).then(() => {
                        diagBtn.setText(t('error_copied') || 'Copied!');
                        setTimeout(() => {
                            diagBtn.setText(t('error_copy_diagnostic') || 'Copy diagnostic');
                        }, 3000);
                    }).catch(() => {
                        new Notice('[!!] Clipboard write failed', 6000);
                    });
                });
            }

            btn.disabled = false;
            btn.textContent = t('install_btn_retry');
        }
    }

    _log(msg) {
        if (this._installLog) {
            this._installLog.setText(this._installLog.textContent + msg + '\n');
        }
    }

    _validate() {
        const errors = [];
        const s = this.plugin.settings;
        if (!s.vault_path || !s.vault_path.trim()) errors.push(t('validate_vault'));
        if (!s.resources_dir || !s.resources_dir.trim()) errors.push(t('validate_resources'));
        if (!s.literature_dir || !s.literature_dir.trim()) errors.push(t('validate_notes'));
        if (!s.control_dir || !s.control_dir.trim()) errors.push(t('validate_index'));
        if (!s.base_dir || !s.base_dir.trim()) errors.push(t('validate_base'));
        if (!s.paddleocr_api_key || !s.paddleocr_api_key.trim()) errors.push(t('validate_key'));
        if (!s.zotero_data_dir || !s.zotero_data_dir.trim()) errors.push(t('validate_zotero'));
        return errors;
    }

    _processSetupOutput(text) {
        const lines = text.split('\n').filter(Boolean);
        for (const line of lines) {
            if (line.includes('[*]') || line.includes('[OK]') || line.includes('[FAIL]')) {
                const clean = line.replace(/^\[\*\].*\d+:?\s*/, '').replace(/^\[OK\]\s*/, '').replace(/^\[FAIL\]\s*/, '');
                this._log('  ' + clean);
            }
        }
    }

    _formatSetupError(raw) {
        const patterns = [
            // New: pip not found (before generic command not found)
            { match: /pip.*not found|No module named.*pip|command not found.*pip/i, msg: 'pip not found' },
            // Existing: Python not found (keep broad)
            { match: /command not found|No such file|not recognized/i, msg: 'Python not found' },
            // New: Network error (DNS resolution, connection refused, etc.)
            { match: /resolve host|getaddrinfo.*nodename|connect ETIMEDOUT|connect ECONNREFUSED|fetch failed|Network error|ENOTFOUND|ECONNREFUSED|ECONNRESET/i, msg: 'Network error' },
            // New: SSL certificate
            { match: /certificate verify failed|SSL.*certificate|self.signed.cert|CERTIFICATE_VERIFY_FAILED/i, msg: 'SSL certificate error' },
            // New: Disk full
            { match: /No space left on device|disk full|ENOSPC/i, msg: 'Disk full' },
            // Existing: PaperForge not installed
            { match: /paperforge.*not found|cannot import|ModuleNotFoundError|No module named/i, msg: 'PaperForge not installed' },
            // Existing + New: Permission denied (expand pattern)
            { match: /permission denied|EACCES|EPERM/i, msg: 'Permission denied' },
            // Existing: Path not found
            { match: /ENOENT/i, msg: 'Path not found' },
            // Existing: Timeout
            { match: /timeout|timed out/i, msg: 'Timeout' },
        ];
        for (const p of patterns) { if (p.match.test(raw)) return p.msg; }
        const fallback = raw.split('\n').filter(Boolean).slice(0, 3).join(' | ');
        return fallback.slice(0, 200) || 'Unknown error';
    }

    /* ── Step 5: Complete ── */
    _stepComplete(el) {
        el.createEl('h2', { text: t('complete_title') });
        const summary = el.createEl('div', { cls: 'paperforge-summary' });
        summary.createEl('div', { cls: 'paperforge-summary-title', text: t('complete_summary') });
        const s = this.plugin.settings;
        const vault = this.app.vault.adapter.basePath;
        const items = [
            { label: t('dir_vault'), val: vault },
            { label: t('dir_resources'), val: `${vault}/${s.resources_dir}` },
            { label: t('dir_notes'), val: `${vault}/${s.resources_dir}/${s.literature_dir}` },
            { label: t('dir_index'), val: `${vault}/${s.resources_dir}/${s.control_dir}` },
            { label: t('dir_base'), val: `${vault}/${s.base_dir}` },
            { label: t('dir_system'), val: `${vault}/${s.system_dir}` },
            { label: 'API Key', val: s.paddleocr_api_key ? t('api_key_set') : t('api_key_missing') },
            { label: t('field_zotero_data'), val: s.zotero_data_dir || t('not_set') },
        ];
        for (const item of items) {
            const row = summary.createEl('div', { cls: 'paperforge-summary-row' });
            row.createEl('span', { cls: 'paperforge-summary-label', text: item.label });
            row.createEl('span', { cls: 'paperforge-summary-value', text: item.val });
        }
        // PaperForge version (fetched async)
        const verRow = summary.createEl('div', { cls: 'paperforge-summary-row' });
        verRow.createEl('span', { cls: 'paperforge-summary-label', text: 'PaperForge' });
        const verVal = verRow.createEl('span', { cls: 'paperforge-summary-value', text: '\u2014' });
        {
            const vp = vault;
            const { path: pythonExe, extraArgs = [] } = resolvePythonExecutable(vp, this.plugin.settings);
            execFile(pythonExe, [...extraArgs, '-c', 'import paperforge; print(paperforge.__version__)'], { cwd: vp, timeout: 10000 }, (err, stdout) => {
                if (!err && stdout) verVal.textContent = 'v' + stdout.trim();
            });
        }
        for (const item of items) {
            const row = summary.createEl('div', { cls: 'paperforge-summary-row' });
            row.createEl('span', { cls: 'paperforge-summary-label', text: item.label });
            row.createEl('span', { cls: 'paperforge-summary-value', text: item.val });
        }
        el.createEl('h3', { text: t('complete_next') });
        const nextList = el.createEl('div', { cls: 'paperforge-nextsteps' });
        const steps = [
            [t('complete_step4'), t('complete_step4_desc')],
            ['', `${t('complete_export_path')} ${vault}/${s.system_dir}/PaperForge/exports/`],
            [t('complete_step1'), t('complete_step1_desc')],
            [t('complete_step2'), t('complete_step2_desc')],
            [t('complete_step3'), t('complete_step3_desc')],
        ];
        for (const [title, desc] of steps) {
            const item = nextList.createEl('div', { cls: 'paperforge-nextstep-item' });
            if (title) item.createEl('strong', { text: title });
            item.createEl('span', { text: desc });
        }
    }
}

module.exports = class PaperForgePlugin extends Plugin {
    async onload() {
        await this.loadSettings();
        // Clean stale path fields from plugin data.json (migrated to paperforge.json)
        this.saveSettings();
        T = (langFromApp(this.app) === 'zh') ? LANG.zh : LANG.en;
        this.registerView(VIEW_TYPE_PAPERFORGE, (leaf) => new PaperForgeStatusView(leaf));

        try { addIcon(PF_ICON_ID, PF_RIBBON_SVG); } catch (_) {}
        this.addRibbonIcon(PF_ICON_ID, 'PaperForge Dashboard', () => PaperForgeStatusView.open(this));

        this.addSettingTab(new PaperForgeSettingTab(this.app, this));

        this.addCommand({
            id: 'paperforge-status-panel',
            name: `PaperForge: ${t('guide_open')}`,
            callback: () => PaperForgeStatusView.open(this),
        });

        for (const a of ACTIONS) {
            this.addCommand({
                id: a.id,
                name: `PaperForge: ${a.title}`,
                callback: () => {
                    if (a.disabled) {
                        new Notice(`[i] ${a.disabledMsg || 'This action is not yet available.'}`, 6000);
                        return;
                    }
                    const vp = this.app.vault.adapter.basePath;
                    new Notice(`PaperForge: running ${a.cmd}...`);
                    const { path: cmdPythonExe, extraArgs: cmdExtra = [] } = resolvePythonExecutable(vp, this.settings);
                    execFile(cmdPythonExe, [...cmdExtra, '-m', 'paperforge', a.cmd], { cwd: vp, timeout: 300000 }, (err, stdout, stderr) => {
                        if (err) {
                            new Notice(`[!!] ${a.cmd} failed: ${(stderr || err.message).slice(0, 120)}`, 8000);
                            return;
                        }
                        new Notice(`[OK] ${a.okMsg || stdout.trim().split('\n')[0].slice(0, 80)}`);
                    });
                },
            });
        }

        /* ── Command palette: context actions (use view\u2019s _runAction for key resolution) ── */
        this.addCommand({
            id: 'paperforge-copy-context',
            name: 'Copy Context: Copy active paper\u2019s index entry JSON to clipboard',
            callback: () => {
                const leaves = this.app.workspace.getLeavesOfType(VIEW_TYPE_PAPERFORGE);
                if (leaves.length > 0 && leaves[0].view instanceof PaperForgeStatusView) {
                    const action = ACTIONS.find(a => a.id === 'paperforge-copy-context');
                    if (action) {
                        const tempCard = document.createElement('div');
                        leaves[0].view._runAction(action, tempCard);
                    }
                } else {
                    new Notice('[!!] Open PaperForge Dashboard first (click sidebar icon)', 5000);
                }
            },
        });
        this.addCommand({
            id: 'paperforge-copy-collection-context',
            name: 'Copy Collection Context: Copy all canonical index entries to clipboard',
            callback: () => {
                const leaves = this.app.workspace.getLeavesOfType(VIEW_TYPE_PAPERFORGE);
                if (leaves.length > 0 && leaves[0].view instanceof PaperForgeStatusView) {
                    const action = ACTIONS.find(a => a.id === 'paperforge-copy-collection-context');
                    if (action) {
                        const tempCard = document.createElement('div');
                        leaves[0].view._runAction(action, tempCard);
                    }
                } else {
                    new Notice('[!!] Open PaperForge Dashboard first (click sidebar icon)', 5000);
                }
            },
        });

        /* ── Auto-update PaperForge (deferred — don't slow startup) ── */
        if (this.settings.auto_update !== false) {
            setTimeout(() => this._autoUpdate(), 3000);
        }
    }

    _autoUpdate() {
        const vp = this.app.vault.adapter.basePath;
        const { path: pythonExe, extraArgs = [] } = resolvePythonExecutable(vp, this.settings);
        const ver = this.manifest.version || '1.4.17rc2';
        const url = `git+https://github.com/LLLin000/PaperForge.git@${ver}`;

        // Check if installed package version matches plugin version
        const { execFile } = require('node:child_process');
        execFile(pythonExe, [...extraArgs, '-c', 'import paperforge; print(paperforge.__version__)'], { cwd: vp, timeout: 10000 }, (err, stdout) => {
            if (err) {
                // Not installed — install now
                const spawn = require('node:child_process').spawn;
                const child = spawn(pythonExe, [...extraArgs, '-m', 'pip', 'install', '--upgrade', url], { cwd: vp, timeout: 120000 });
                child.on('close', (code) => {
                    if (code === 0) new Notice('[OK] PaperForge CLI installed', 5000);
                });
                return;
            }
            const pyVer = stdout.trim();
            if (pyVer !== ver) {
                // Mismatch — upgrade
                const spawn = require('node:child_process').spawn;
                const child = spawn(pythonExe, [...extraArgs, '-m', 'pip', 'install', '--upgrade', url], { cwd: vp, timeout: 120000 });
                child.on('close', (code) => {
                    if (code === 0) new Notice(`[OK] PaperForge ${pyVer} -> ${ver}`, 5000);
                });
            }
        });
    }

    /**
     * Read path configuration from the canonical paperforge.json file.
     * Falls back to Python-level DEFAULT_CONFIG values if file does not exist.
     * Returns {system_dir, resources_dir, literature_dir, control_dir, base_dir}.
     */
    readPaperforgeJson() {
        const fs = require('fs');
        const path = require('path');
        const vaultPath = this.app.vault.adapter.basePath;
        const pfPath = path.join(vaultPath, 'paperforge.json');

        // Python DEFAULT_CONFIG values as fallback (must match config.py exactly)
        const DEFAULTS = {
            system_dir: 'System',
            resources_dir: 'Resources',
            literature_dir: 'Literature',
            control_dir: 'LiteratureControl',
            base_dir: 'Bases',
        };

        try {
            if (!fs.existsSync(pfPath)) {
                return DEFAULTS;
            }
            const raw = fs.readFileSync(pfPath, 'utf-8');
            const data = JSON.parse(raw);

            // Try vault_config block first (canonical), fall back to top-level (legacy)
            const vc = data.vault_config || {};
            return {
                system_dir: vc.system_dir || data.system_dir || DEFAULTS.system_dir,
                resources_dir: vc.resources_dir || data.resources_dir || DEFAULTS.resources_dir,
                literature_dir: vc.literature_dir || data.literature_dir || DEFAULTS.literature_dir,
                control_dir: vc.control_dir || data.control_dir || DEFAULTS.control_dir,
                base_dir: vc.base_dir || data.base_dir || DEFAULTS.base_dir,
            };
        } catch (e) {
            console.warn('PaperForge: Failed to read paperforge.json, using defaults', e);
            return DEFAULTS;
        }
    }

    /**
     * Write path configuration back to paperforge.json vault_config block.
     * Reads the existing file, updates vault_config with the new values,
     * and writes back preserving all other keys.
     */
    savePaperforgeJson(pathConfig) {
        const fs = require('fs');
        const path = require('path');
        const vaultPath = this.app.vault.adapter.basePath;
        const pfPath = path.join(vaultPath, 'paperforge.json');

        let data = {};
        try {
            if (fs.existsSync(pfPath)) {
                data = JSON.parse(fs.readFileSync(pfPath, 'utf-8'));
            }
        } catch (e) {
            console.warn('PaperForge: Failed to read paperforge.json for update', e);
        }

        // Ensure vault_config block exists
        if (!data.vault_config || typeof data.vault_config !== 'object') {
            data.vault_config = {};
        }

        // Update vault_config with new path values
        const validPathKeys = ['system_dir', 'resources_dir', 'literature_dir', 'control_dir', 'base_dir'];
        for (const key of validPathKeys) {
            if (pathConfig[key] !== undefined) {
                data.vault_config[key] = pathConfig[key];
            }
        }

        // Ensure schema_version
        if (!data.schema_version) {
            data.schema_version = '2';
        }

        // Remove any stale top-level path keys (they were migrated to vault_config)
        for (const key of validPathKeys) {
            delete data[key];
        }

        try {
            fs.writeFileSync(pfPath, JSON.stringify(data, null, 2), 'utf-8');
            // Refresh the in-memory settings
            if (this.settings) {
                const pfConfig = this.readPaperforgeJson();
                this.settings.system_dir = pfConfig.system_dir;
                this.settings.resources_dir = pfConfig.resources_dir;
                this.settings.literature_dir = pfConfig.literature_dir;
                this.settings.control_dir = pfConfig.control_dir;
                this.settings.base_dir = pfConfig.base_dir;
            }
        } catch (e) {
            console.error('PaperForge: Failed to write paperforge.json', e);
            new Notice('PaperForge: Failed to save configuration to paperforge.json');
        }
    }

    onunload() {
        this.app.workspace.detachLeavesOfType(VIEW_TYPE_PAPERFORGE);
    }

    async loadSettings() {
        this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
        // Path fields come from paperforge.json, not from DEFAULT_SETTINGS or plugin data.json
        const pfConfig = this.readPaperforgeJson();
        this.settings.system_dir = pfConfig.system_dir;
        this.settings.resources_dir = pfConfig.resources_dir;
        this.settings.literature_dir = pfConfig.literature_dir;
        this.settings.control_dir = pfConfig.control_dir;
        this.settings.base_dir = pfConfig.base_dir;

        // Re-validate saved python_path override
        if (this.settings.python_path && this.settings.python_path.trim()) {
            const pp = this.settings.python_path.trim();
            if (!fs.existsSync(pp)) {
                console.warn(`PaperForge: Saved python_path "${pp}" no longer exists — showing stale warning`);
                this.settings._python_path_stale = true;
            } else {
                this.settings._python_path_stale = false;
            }
        }
    }

    async saveSettings() {
        // Only persist non-path settings to plugin data.json
        const dataToSave = {};
        for (const key of Object.keys(DEFAULT_SETTINGS)) {
            if (key in this.settings) {
                dataToSave[key] = this.settings[key];
            }
        }
        await this.saveData(dataToSave);
    }
};
