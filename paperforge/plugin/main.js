const { Plugin, Notice, ItemView, Modal, Setting, PluginSettingTab, addIcon } = require('obsidian');
const { exec } = require('node:child_process');
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
    en: { header_title:'PaperForge',desc:'Obsidian + Zotero literature pipeline.',setup_done:'✓ PaperForge environment configured',setup_pending:'Not installed — complete preparation and open the wizard',section_prep:'Prerequisites',section_prep_desc:'Before first use, complete the following:',section_guide:'Usage',section_config:'Configuration',prep_python:'Python 3.9+',prep_python_desc:'Must be callable from command line. Click below to auto-detect.',prep_zotero:'Zotero Desktop',prep_zotero_desc:'Install Zotero (https://www.zotero.org)',prep_bbt:'Better BibTeX',prep_bbt_desc:'Zotero → Tools → Add-ons → Install Better BibTeX',prep_export:'BBT Auto-export',prep_export_desc:'Right-click collection → Export → BetterBibTeX JSON → Keep updated → to:',prep_key:'PaddleOCR Key',prep_key_desc:'Get free key at https://aistudio.baidu.com/paddleocr',guide_open:'Open Dashboard',guide_open_desc:'Ctrl+P → "PaperForge: Open Dashboard", or sidebar book icon',guide_sync:'Sync Literature',guide_sync_desc:'Dashboard → Sync Library — pull from Zotero, generate notes',guide_ocr:'Run OCR',guide_ocr_desc:'Dashboard → Run OCR — extract PDF text & figures',btn_install:'Open Wizard',btn_reconfig:'Reconfigure',btn_install_desc:'Auto-detect environment, then open setup wizard',btn_reconfig_desc:'Re-run wizard to change directories or keys',wizard_step1:'Overview',wizard_step2:'Dirs',wizard_step3:'Agent',wizard_step4:'Install',wizard_step5:'Done',wizard_title:'PaperForge Setup Wizard',wizard_intro:'This wizard will guide you through the complete setup.',wizard_dir_hint:'The resources directory is the root for all literature data. Sub-directories inside it:',wizard_dir_sub_hint:'Two sub-directories within resources:',wizard_sys_hint:'System directories (at vault root):',wizard_agent_hint:'Select your AI Agent platform. Skill files deploy in the correct format.',wizard_keys_hint:'API key and Zotero:',wizard_preview:'System/agent files at vault root. Literature (notes, index) under resources.',dir_vault:'Vault Path',dir_resources:'Resource Dir',dir_notes:'Notes Dir',dir_index:'Index Dir',dir_system:'System Dir',dir_base:'Base Dir',field_paddleocr:'PaddleOCR API Key',field_zotero_data:'Zotero Data Dir',field_zotero_placeholder:'Optional, for auto PDF detection',label_agent:'Agent Platform',check_python_ok:'Ready',check_python_fail:'Not found',check_zotero_ok:'Found',check_zotero_fail:'Not detected',check_bbt_ok:'Installed',check_bbt_fail:'Not detected',install_btn:'Install',install_btn_running:'Installing...',install_btn_retry:'Retry',install_complete:'✓ Installation complete!',install_failed:'✗ Installation failed: ',complete_title:'✓ Setup Complete',complete_summary:'Configuration',complete_next:'Next Steps',complete_step1:'Open Dashboard',complete_step1_desc:'Ctrl+P → "PaperForge: Open Dashboard" or sidebar book icon',complete_step2:'Sync Literature',complete_step2_desc:'Dashboard → Sync Library — pull from Zotero',complete_step3:'Run OCR',complete_step3_desc:'Dashboard → Run OCR — extract full text & figures',complete_step4:'Configure BBT Auto-export',nav_prev:'← Back',nav_next:'Next →',nav_close:'Close',validate_fail:'Validation failed',validate_vault:'Vault path not set',validate_resources:'Resource dir not set',validate_notes:'Notes dir not set',validate_index:'Index dir not set',validate_base:'Base dir not set',validate_key:'API key not set',validate_system:'System dir not set',notice_python_missing:'Python not detected. Install Python 3.9+ and add to PATH.',notice_check_fail:'Missing: ',panel_actions:'Quick Actions',action_running:'Running ',api_key_set:'Configured ✓',api_key_missing:'Not configured ✗',not_set:'Not set', },
    zh: { header_title:'PaperForge',desc:'Obsidian + Zotero 文献管理流水线。自动同步文献、生成笔记、OCR 提取全文，一站式文献精读工作流。',setup_done:'✓ PaperForge 环境已配置完成',setup_pending:'尚未安装，完成安装准备后点击安装向导',section_prep:'安装准备',section_prep_desc:'首次使用前，请依次完成以下准备：',section_guide:'操作方式',section_config:'当前配置',prep_python:'Python 3.9+',prep_python_desc:'确保 Python 可命令行调用。点击下方按钮自动检测。',prep_zotero:'Zotero 桌面版',prep_zotero_desc:'安装 Zotero (https://www.zotero.org)',prep_bbt:'Better BibTeX',prep_bbt_desc:'Zotero → 工具 → 插件 → 安装 Better BibTeX',prep_export:'BBT 自动导出',prep_export_desc:'右键文献子分类 → 导出分类 → BetterBibTeX JSON → 勾选保持更新 → 导出到（JSON 文件名即为 Base 名）：',prep_key:'PaddleOCR Key',prep_key_desc:'在 https://aistudio.baidu.com/paddleocr 获取 API Key',guide_open:'打开 Dashboard',guide_open_desc:'Ctrl+P → 输入 PaperForge: Open Dashboard，或点左侧书本图标',guide_sync:'同步文献',guide_sync_desc:'Dashboard 中点 Sync Library，从 Zotero 拉取文献生成笔记',guide_ocr:'运行 OCR',guide_ocr_desc:'Dashboard 中点 Run OCR，提取 PDF 全文与图表',btn_install:'打开安装向导',btn_reconfig:'重新配置',btn_install_desc:'自动检测 Python + 前置环境，通过后打开分步安装向导',btn_reconfig_desc:'重新运行安装向导，修改目录或密钥配置',wizard_step1:'概览',wizard_step2:'目录',wizard_step3:'Agent',wizard_step4:'安装',wizard_step5:'完成',wizard_title:'PaperForge 安装向导',wizard_intro:'本向导将引导您完成 PaperForge 环境的完整配置。安装过程会自动创建所有目录结构，无需手动操作。',wizard_dir_hint:'资源目录是文献数据的统一根目录，以下子目录将创建在其内部：',wizard_dir_sub_hint:'资源目录内的两个子目录：',wizard_sys_hint:'独立于资源目录的系统文件：',wizard_agent_hint:'选择你使用的 AI Agent 平台，安装时将按对应格式部署技能文件：',wizard_keys_hint:'以下为 API 密钥与 Zotero 配置：',wizard_preview:'系统文件和 Agent 配置位于 Vault 根目录下。文献数据（正文、索引）统一存放在资源目录内。安装后仍可在设置中修改。',dir_vault:'Vault 路径',dir_resources:'资源目录',dir_notes:'正文目录',dir_index:'索引目录',dir_system:'系统目录',dir_base:'Base 目录',field_paddleocr:'PaddleOCR API 密钥',field_zotero_data:'Zotero 数据目录',field_zotero_placeholder:'可选，用于自动检测 PDF',label_agent:'Agent 平台',check_python_ok:'已就绪',check_python_fail:'未安装',check_zotero_ok:'已安装',check_zotero_fail:'未检测到',check_bbt_ok:'已安装',check_bbt_fail:'未检测到',install_btn:'开始安装',install_btn_running:'正在安装...',install_btn_retry:'重试',install_complete:'✓ 安装完成！',install_failed:'✗ 安装失败：',complete_title:'✓ PaperForge 安装完成',complete_summary:'当前完整配置',complete_next:'下一步操作',complete_step1:'打开 PaperForge Dashboard',complete_step1_desc:'Ctrl+P → 输入 PaperForge: Open Dashboard，或点左侧书本图标',complete_step2:'同步文献',complete_step2_desc:'Dashboard 中点 Sync Library，从 Zotero 拉取文献生成笔记',complete_step3:'运行 OCR',complete_step3_desc:'Dashboard 中点 Run OCR，提取 PDF 全文与图表',complete_step4:'配置 BBT 自动导出',nav_prev:'← 上一步',nav_next:'下一步 →',nav_close:'关闭',validate_fail:'配置验证失败',validate_vault:'Vault 路径未填写',validate_resources:'资源目录未填写',validate_notes:'正文目录未填写',validate_index:'索引目录未填写',validate_base:'Base 目录未填写',validate_key:'PaddleOCR API 密钥未填写',validate_system:'系统目录未填写',notice_python_missing:'Python 未检测到，请先安装 Python 3.9+ 并加入 PATH',notice_check_fail:'未通过: ',panel_actions:'快捷操作',action_running:'正在执行 ',api_key_set:'已配置 ✓',api_key_missing:'未配置 ✗',not_set:'未设置', }
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
    field_zotero_placeholder: 'Optional. Helps auto-locate PDF attachments in Zotero storage',
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
    validate_system: 'System directory is required',
    notice_python_missing: 'Python was not detected. Install Python 3.9+ and add it to PATH.',
    api_key_set: 'Entered',
    api_key_missing: 'Missing',
    not_set: 'Not entered',
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
    field_zotero_placeholder: '可选。填写后可帮助自动定位 Zotero 存储中的 PDF 附件',
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
    notice_python_missing: '未检测到 Python。请先安装 Python 3.9+，并确保它已加入 PATH。',
    api_key_set: '已填写',
    api_key_missing: '未填写',
    not_set: '未填写',
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
    },
    {
        id: 'paperforge-repair',
        title: 'Repair Issues',
        desc: 'Fix three-way state divergence, path errors, and rebuild index',
        icon: '\u21BA',  // ↺
        cmd: 'repair',
        okMsg: 'Repair complete',
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

class PaperForgeStatusView extends ItemView {
    constructor(leaf) {
        super(leaf);
        this._currentMode = null;       // 'global' | 'paper' | 'collection' (D-05)
        this._currentDomain = null;     // domain name when in collection mode (D-15)
        this._currentPaperKey = null;   // zotero_key when in per-paper mode (D-03)
        this._currentPaperEntry = null; // full entry when in per-paper mode
        this._cachedItems = null;       // lazy-loaded index items (Plan 28-01)
        this._modeSubscribers = [];     // event handler refs for cleanup
        this._leafChangeTimer = null;   // debounce timer for active-leaf-change
    }

    getViewType() { return VIEW_TYPE_PAPERFORGE; }
    getDisplayText() { return 'PaperForge'; }
    getIcon() { return PF_ICON_ID; }

    async onOpen() {
        this._buildPanel();
        this._contentEl = this.containerEl.querySelector('.paperforge-content-area');
        this._modeSubscribers = [];     // reused by both workspace and vault events
        this._leafChangeTimer = null;   // debounce timer for active-leaf-change

        // Subscribe to file change events (D-08, D-09)
        this._setupEventSubscriptions();

        // Initial data load per D-10
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
        const systemDir = plugin?.settings?.system_dir || '99_System';
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
                version: this._cachedStats?.version || '\u2014',
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
            exec('python -m paperforge status --json', { cwd: vp, timeout: 30000 }, (err2, stdout) => {
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
        const systemDir = plugin?.settings?.system_dir || '99_System';
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
        this._versionBadge.setText(d.version ? 'v' + d.version : 'v\u2014');

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
    }

    /* ── Lifecycle Stepper (D-07 through D-11) ── */
    _renderLifecycleStepper(container, lifecycle, currentStage) {
        if (!lifecycle || !currentStage) {
            this._renderSkeleton(container);
            return;
        }

        const stages = [
            { key: 'imported', label: 'Imported' },
            { key: 'indexed', label: 'Indexed' },
            { key: 'pdf_ready', label: 'PDF Ready' },
            { key: 'fulltext_ready', label: 'Fulltext Ready' },
            { key: 'deep_read', label: 'Deep Read' },
            { key: 'ai_ready', label: 'AI Ready' },
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
        const currentLevel = Math.max(1, Math.min(6, Math.round(maturityLevel)));

        for (let i = 1; i <= 6; i++) {
            const seg = track.createEl('div', { cls: 'gauge-segment' });
            if (i <= currentLevel) {
                seg.addClass('filled');
                seg.addClass(`level-${i}`);
            }
        }

        gauge.createEl('div', { cls: 'gauge-level', text: `Level ${currentLevel} / 6` });

        if (currentLevel < 6 && blockingChecks && blockingChecks.length > 0) {
            const list = gauge.createEl('ul', { cls: 'gauge-blockers' });
            for (const check of blockingChecks) {
                list.createEl('li', { text: check });
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
            { key: 'imported', label: 'Imported', cls: 'stage-imported' },
            { key: 'indexed', label: 'Indexed', cls: 'stage-indexed' },
            { key: 'pdf_ready', label: 'PDF Ready', cls: 'stage-pdf-ready' },
            { key: 'fulltext_ready', label: 'Fulltext Ready', cls: 'stage-fulltext-ready' },
            { key: 'deep_read', label: 'Deep Read', cls: 'stage-deep-read' },
            { key: 'ai_ready', label: 'AI Ready', cls: 'stage-ai-ready' },
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
            card.createEl('div', { cls: 'paperforge-action-card-icon', text: a.icon });
            card.createEl('div', { cls: 'paperforge-action-card-title', text: a.title });
            card.createEl('div', { cls: 'paperforge-action-card-desc', text: a.desc });
            card.createEl('div', { cls: 'paperforge-action-card-hint', text: 'Click to run' });
            card.addEventListener('click', () => this._runAction(a, card));
        }
    }

    /* ── Invalidate cached index (D-14) ── */
    _invalidateIndex() {
        this._cachedItems = null;
    }

    /* ── Context Detection & Mode Switch (D-01, D-02, D-03, D-04, D-10) ── */
    _detectAndSwitch() {
        const activeFile = this.app.workspace.getActiveFile();

        if (!activeFile) {
            // No active file -> global mode (D-04)
            this._switchMode('global');
            return;
        }

        const ext = activeFile.extension;

        if (ext === 'base') {
            // .base file -> collection mode (D-02, D-15)
            this._currentDomain = activeFile.basename;
            this._currentPaperKey = null;
            this._currentPaperEntry = null;
            this._switchMode('collection');
            return;
        }

        if (ext === 'md') {
            // .md file -- check for zotero_key in frontmatter (D-03)
            const cache = this.app.metadataCache.getFileCache(activeFile);
            const key = cache && cache.frontmatter && cache.frontmatter.zotero_key;

            if (key) {
                // Has zotero_key -> per-paper mode (D-03)
                this._currentPaperKey = key;
                this._currentPaperEntry = this._findEntry(key);
                this._currentDomain = null;
                this._switchMode('paper');
            } else {
                // .md without zotero_key -> global mode (D-04)
                this._currentDomain = null;
                this._currentPaperKey = null;
                this._currentPaperEntry = null;
                this._switchMode('global');
            }
            return;
        }

        // Any other file type -> global mode (D-04)
        this._currentDomain = null;
        this._currentPaperKey = null;
        this._currentPaperEntry = null;
        this._switchMode('global');
    }

    /* ── Mode Switching (D-05, D-06) ── */
    _switchMode(mode) {
        if (this._currentMode === mode) {
            // Already in this mode -- just refresh if needed (D-04)
            this._refreshCurrentMode();
            return;
        }

        this._currentMode = mode;

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
        }
    }

    /* ── Global Mode Render (existing dashboard, extracted from _fetchStats + _renderOcr) ── */
    _renderGlobalMode() {
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
            '/pf-deep':     { label: 'Ready for Deep Reading', text: 'Fulltext is ready. Copy key to use /pf-deep in OpenCode.',          cmd: null,       icon: '\uD83D\uDD0D' },
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
            // Copy zotero_key to clipboard for /pf-deep (D-09)
            const trigger = card.createEl('button', { cls: 'paperforge-next-step-trigger' });
            trigger.createEl('span', { text: '\uD83D\uDCCB  Copy Key for /pf-deep' });
            trigger.addEventListener('click', () => {
                navigator.clipboard.writeText(key).then(() => {
                    trigger.setText('\u2713  Copied!');
                    new Notice('Zotero key copied: ' + key);
                }).catch(() => {
                    new Notice('[!!] Clipboard write failed', 6000);
                });
            });
        } else if (nextStep === 'ready') {
            // Show "Copy Context" shortcut for ready state (D-09)
            const trigger = card.createEl('button', { cls: 'paperforge-next-step-trigger' });
            trigger.createEl('span', { text: '\u2139  Copy Context' });
            trigger.addEventListener('click', () => {
                const action = ACTIONS.find(a => a.id === 'paperforge-copy-context');
                if (action) this._runAction(action, trigger);
            });
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
        const lifecycleCounts = {};
        const healthAgg = {
            pdf_health: { healthy: 0, unhealthy: 0 },
            ocr_health: { healthy: 0, unhealthy: 0 },
            note_health: { healthy: 0, unhealthy: 0 },
            asset_health: { healthy: 0, unhealthy: 0 },
        };
        let fulltextReady = 0;
        let deepRead = 0;

        for (const item of domainItems) {
            const lifecycle = item.lifecycle || 'pdf_ready';
            lifecycleCounts[lifecycle] = (lifecycleCounts[lifecycle] || 0) + 1;

            if (['fulltext_ready', 'deep_read', 'ai_ready'].includes(lifecycle)) fulltextReady++;
            if (['deep_read', 'ai_ready'].includes(lifecycle)) deepRead++;

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

        // --- Lifecycle distribution bar chart (D-04) ---
        this._renderBarChart(view, lifecycleCounts);

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
        }

        // Brief delay before removing switching class for smooth fade transition
        setTimeout(() => {
            if (this._contentEl) this._contentEl.removeClass('switching');
        }, 50);
    }

    /* ── Run Action ── */
    _runAction(a, card) {
        // Guard: prevent running the same action simultaneously
        if (card.classList.contains('running')) {
            return;
        }
        card.addClass('running');
        const vp = this.app.vault.adapter.basePath;
        this._showMessage('Processing...', 'running');

        // Resolve extra arguments based on action flags
        let extraArgs = [];

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
            extraArgs = [key];
        }

        if (a.needsFilter) {
            // Default to --all for the initial implementation
            extraArgs = ['--all'];
        }

        const { spawn } = require('node:child_process');
        const cmdTimeout = a.needsFilter ? 60000 : (a.needsKey ? 30000 : 600000);
        const child = spawn('python', ['-m', 'paperforge', a.cmd, ...extraArgs], { cwd: vp, timeout: cmdTimeout });
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
                this._showMessage('[!!] ' + last, 'error');
                new Notice('[!!] ' + a.cmd + ' failed: ' + last, 8000);
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
                this._headerTitle.setText(modeName);
                break;

            case 'collection':
                badge.addClass('collection');
                badge.setText('Collection');
                modeName = this._currentDomain || 'Unknown Domain';
                this._headerTitle.setText(modeName);
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

    _debouncedSave() {
        clearTimeout(this._saveTimeout);
        this._saveTimeout = setTimeout(() => this.plugin.saveSettings(), 500);
    }

    _preCheck(onPass) {
        exec('python --version', { timeout: 8000 }, (pyErr, pyOut) => {
            const results = [];
            const fs = require('fs');
            const path = require('path');

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
            nav.createEl('button', { cls: 'paperforge-step-btn mod-cta', text: t('nav_next') })
                .addEventListener('click', () => { this._step++; this._render(); });
        } else {
            nav.createEl('button', { cls: 'paperforge-step-btn', text: t('nav_close') })
                .addEventListener('click', () => this.close());
        }
    }

    /* ── Step 1: Overview ── */
    _stepOverview(el) {
        el.createEl('h2', { text: t('wizard_title') });
        el.createEl('p', { text: t('wizard_intro') });

        const s = this.plugin.settings;
        const vault = this.app.vault.adapter.basePath;
        const tree = el.createEl('div', { cls: 'paperforge-dir-tree' });
        tree.innerHTML = `
            <div class="paperforge-dir-node root">📁 Vault (${vault})</div>
            <div class="paperforge-dir-children">
                <div class="paperforge-dir-node folder">📁 ${s.resources_dir || 'Resources'}/ — 文献资源根目录
                    <div class="paperforge-dir-children">
                        <div class="paperforge-dir-node file">📁 ${s.literature_dir || 'Notes'}/ — 正文笔记</div>
                        <div class="paperforge-dir-node file">📁 ${s.control_dir || 'Index_Cards'}/ — 索引卡片</div>
                    </div>
                </div>
                <div class="paperforge-dir-node folder">📁 ${s.base_dir || 'Base'}/ — Base 视图文件</div>
                <div class="paperforge-dir-node folder">📁 ${s.system_dir || 'System'}/ — 系统文件</div>
            </div>`;

        el.createEl('p', { text: t('wizard_preview'), cls: 'paperforge-modal-hint' });
        el.createEl('p', { text: t('wizard_safety'), cls: 'paperforge-modal-hint' });

        const summary = el.createEl('div', { cls: 'paperforge-summary' });
        const overviewItems = [
            { label: t('dir_resources'), val: `${vault}/${s.resources_dir || '03_Resources'}` },
            { label: t('dir_notes'), val: `${vault}/${s.resources_dir || '03_Resources'}/${s.literature_dir || 'Literature'}` },
            { label: t('dir_index'), val: `${vault}/${s.resources_dir || '03_Resources'}/${s.control_dir || 'LiteratureControl'}` },
            { label: t('dir_base'), val: `${vault}/${s.base_dir || '05_Bases'}` },
            { label: t('dir_system'), val: `${vault}/${s.system_dir || '99_System'}` },
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

        this._modalInput(el, t('dir_resources'), 'resources_dir', s.resources_dir, 'Resources');

        el.createEl('p', { text: t('wizard_dir_sub_hint'), cls: 'paperforge-modal-hint' });

        this._modalInput(el, t('dir_notes'), 'literature_dir', s.literature_dir, 'Notes');
        this._modalInput(el, t('dir_index'), 'control_dir', s.control_dir, 'Index_Cards');

        el.createEl('p', { text: t('wizard_sys_hint'), cls: 'paperforge-modal-hint' });

        this._modalInput(el, t('dir_system'), 'system_dir', s.system_dir, 'System');
        this._modalInput(el, t('dir_base'), 'base_dir', s.base_dir, 'Base');

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

        this._modalSecret(el, t('field_paddleocr'), 'paddleocr_api_key', s.paddleocr_api_key, 'API Key');
        this._modalInput(el, t('field_zotero_data'), 'zotero_data_dir', s.zotero_data_dir || '', t('field_zotero_placeholder'));
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
            const child = spawn('python', args, {
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
            '--paddleocr-key', s.paddleocr_api_key.trim(),
            '--system-dir', s.system_dir.trim(),
            '--resources-dir', s.resources_dir.trim(),
            '--literature-dir', s.literature_dir.trim(),
            '--control-dir', s.control_dir.trim(),
            '--base-dir', s.base_dir.trim(),
            '--agent', s.agent_platform || 'opencode',
        ];
        if (s.zotero_data_dir && s.zotero_data_dir.trim()) {
            setupArgs.push('--zotero-data', s.zotero_data_dir.trim());
        }

        try {
            let hasPaperforge = true;
            try {
                await runPython(['-m', 'paperforge', '--version']);
            } catch {
                hasPaperforge = false;
            }

            if (!hasPaperforge) {
                this._log(t('install_bootstrapping'));
                await runPython([
                    '-m', 'pip', 'install', '--upgrade',
                    'git+https://github.com/LLLin000/PaperForge.git',
                ]);
            }

            await runPython(setupArgs, { logStdout: true });
            this._log(t('install_complete'));
            s.setup_complete = true;
            await this.plugin.saveSettings();
            setTimeout(() => { this._step = 5; this._render(); }, 800);
        } catch (err) {
            console.error('PaperForge setup failed:', err.message);
            this._log(t('install_failed') + this._formatSetupError(err.message));
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
            { match: /command not found|No such file|not recognized/i, msg: 'Python not found' },
            { match: /paperforge.*not found|cannot import|ModuleNotFoundError|No module named/i, msg: 'PaperForge not installed' },
            { match: /permission denied|EACCES/i, msg: 'Permission denied' },
            { match: /ENOENT/i, msg: 'Path not found' },
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
                    const vp = this.app.vault.adapter.basePath;
                    new Notice(`PaperForge: running ${a.cmd}...`);
                    exec(`python -m paperforge ${a.cmd}`, { cwd: vp, timeout: 300000 }, (err, stdout, stderr) => {
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
        exec('python -m paperforge update', { cwd: vp, timeout: 60000 }, (err, stdout) => {
            if (err) return;
            const result = stdout.trim();
            if (result.includes('already up to date') || result.includes('already up-to-date')) return;
            const firstLine = result.split('\n')[0].slice(0, 80);
            new Notice(`[OK] PaperForge 已更新: ${firstLine}`, 6000);
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
            system_dir: '99_System',
            resources_dir: '03_Resources',
            literature_dir: 'Literature',
            control_dir: 'LiteratureControl',
            base_dir: '05_Bases',
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
