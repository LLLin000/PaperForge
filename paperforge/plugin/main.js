const { Plugin, Notice, ItemView, Modal, Setting, PluginSettingTab, addIcon } = require('obsidian');
const { exec, execFile, spawn, execFileSync } = require('node:child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

// ── Inlined from src/testable.js ──

function resolvePythonExecutable(vaultPath, settings, _fs, _execFileSync) {
    const f = _fs || fs;
    const execSync = _execFileSync || execFileSync;

    if (settings && settings.python_path && settings.python_path.trim()) {
        const manualPath = settings.python_path.trim();
        if (f.existsSync(manualPath)) {
            return { path: manualPath, source: "manual", extraArgs: [] };
        }
    }

    const venvCandidates = [
        path.join(vaultPath, ".paperforge-test-venv", "Scripts", "python.exe"),
        path.join(vaultPath, ".venv", "Scripts", "python.exe"),
        path.join(vaultPath, "venv", "Scripts", "python.exe"),
    ];
    for (const candidate of venvCandidates) {
        try {
            if (f.existsSync(candidate)) {
                return { path: candidate, source: "auto-detected", extraArgs: [] };
            }
        } catch {}
    }

    const systemCandidates = [
        { path: "python", extraArgs: [] },
        { path: "python3", extraArgs: [] },
    ];
    for (const candidate of systemCandidates) {
        try {
            const verOut = execSync(candidate.path, [...candidate.extraArgs, "--version"], {
                encoding: "utf-8", timeout: 5000, windowsHide: true,
            });
            if (verOut && verOut.toLowerCase().includes("python")) {
                return { path: candidate.path, source: "auto-detected", extraArgs: candidate.extraArgs };
            }
        } catch {}
    }

    return { path: "python", source: "auto-detected", extraArgs: [] };
}

function getPluginVersion(app) {
    try {
        const manifest = app && app.plugins && app.plugins.plugins &&
            app.plugins.plugins["paperforge"] && app.plugins.plugins["paperforge"].manifest;
        return (manifest && manifest.version) || null;
    } catch {
        return null;
    }
}

function checkRuntimeVersion(pythonExe, pluginVersion, cwd, timeout, _execFile) {
    if (timeout === undefined) timeout = 10000;
    const exe = _execFile || execFile;

    return new Promise((resolve) => {
        exe(pythonExe, ["-c", "import paperforge; print(paperforge.__version__)"],
            { cwd, timeout },
            (err, stdout) => {
                if (err) {
                    resolve({ status: "not-installed", pyVersion: null, pluginVersion, error: err.message });
                    return;
                }
                const pyVer = (stdout && stdout.trim()) || null;
                if (pyVer === pluginVersion) {
                    resolve({ status: "match", pyVersion: pyVer, pluginVersion, error: null });
                } else {
                    resolve({ status: "mismatch", pyVersion: pyVer, pluginVersion, error: null });
                }
                    });
                });
        }

function classifyError(errorCode) {
    const code = String(errorCode);
    const patterns = {
        ENOENT: { type: "python_missing", message: "Python executable not found", recoverable: true },
        "python-missing": { type: "python_missing", message: "Python executable not found", recoverable: true },
        MODULE_NOT_FOUND: { type: "import_failed", message: "PaperForge package not installed", recoverable: true },
        "import-failed": { type: "import_failed", message: "PaperForge package not installed", recoverable: true },
        "version-mismatch": { type: "version_mismatch", message: "Plugin and package versions differ", recoverable: true, action: "sync-runtime" },
        "pip-failed": { type: "pip_install_failure", message: "pip install command failed", recoverable: true },
        ETIMEDOUT: { type: "timeout", message: "Subprocess timed out", recoverable: true, action: "retry" },
        timeout: { type: "timeout", message: "Subprocess timed out", recoverable: true, action: "retry" },
    };
    const match = patterns[code];
    if (match) return { ...match };
    return { type: "unknown", message: String(errorCode), recoverable: false };
}

function buildRuntimeInstallCommand(pythonExe, version, extraArgs) {
    if (extraArgs === undefined) extraArgs = [];
    const pypiPkg = `paperforge==${version}`;
    const gitUrl = `git+https://github.com/LLLin000/PaperForge.git@v${version}`;
    const pypiArgs = [...extraArgs, "-m", "pip", "install", "--upgrade", pypiPkg];
    const gitArgs = [...extraArgs, "-m", "pip", "install", "--upgrade", gitUrl];
    return { cmd: pythonExe, pypiArgs, gitArgs, timeout: 120000 };
}

function parseRuntimeStatus(err, stdout, stderr) {
    if (!err && stdout) {
        return { status: "ok", version: stdout.trim() };
    }
    if (err && err.code === "ENOENT") {
        const classified = classifyError("ENOENT");
        return { status: "error", version: null, ...classified };
    }
    if (stderr && stderr.includes("No module named paperforge")) {
        const classified = classifyError("import-failed");
        return { status: "error", version: null, ...classified };
    }
    if (err && err.killed) {
        const classified = classifyError("timeout");
        return { status: "error", version: null, ...classified };
    }
    if (stderr && stderr.includes("ModuleNotFoundError")) {
        const classified = classifyError("import-failed");
        return { status: "error", version: null, ...classified };
    }
    return { status: "error", version: null, type: "unknown",
        message: err ? err.message : String(stderr), recoverable: false };
}

const ACTIONS = [
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
        okMsg: "OCR complete",
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

function buildCommandArgs(action, key, filter) {
    const args = Array.isArray(action.args) ? [...action.args] : [];
    if (action.needsKey && key) args.push(key);
    if (action.needsFilter || filter) args.push("--all");
    return args;
}

function runSubprocess(pythonExe, args, cwd, timeout, _spawn, env) {
    const sp = _spawn || spawn;

    return new Promise((resolve) => {
        const startTime = Date.now();
        const opts = { cwd, timeout, windowsHide: true };
        if (env) opts.env = env;
        const child = sp(pythonExe, args, opts);
        const stdoutChunks = [];
        const stderrChunks = [];

        child.stdout.on("data", (data) => { stdoutChunks.push(data.toString("utf-8")); });
        child.stderr.on("data", (data) => { stderrChunks.push(data.toString("utf-8")); });

        child.on("close", (code) => {
            resolve({ stdout: stdoutChunks.join(""), stderr: stderrChunks.join(""),
                exitCode: code, elapsed: Date.now() - startTime });
        });

        child.on("error", (err) => {
            resolve({ stdout: stdoutChunks.join(""),
                stderr: stderrChunks.join("") + "\n" + err.message,
                exitCode: -1, elapsed: Date.now() - startTime });
        });
    });

}

// ── Cross-platform Python and BBT detection (macOS/Linux) ──

let _gitDir = null;
let _gitDirResolved = false;

function resolveGitDir() {
    if (_gitDirResolved) return _gitDir;
    _gitDirResolved = true;
    try {
        let out;
        if (process.platform === 'win32') {
            const cmdExe = process.env.ComSpec || 'C:\\Windows\\System32\\cmd.exe';
            out = require('node:child_process').execFileSync(cmdExe, ['/c', 'where', 'git'], { timeout: 5000, windowsHide: true, encoding: 'utf-8' });
        } else {
            out = require('node:child_process').execFileSync('which', ['git'], { timeout: 5000, encoding: 'utf-8' });
        }
        if (out) {
            const line = out.split('\n')[0].trim();
            if (line) _gitDir = path.dirname(line);
        }
    } catch (_) {}
    return _gitDir;
}

function paperforgeEnrichedEnv() {
    const env = { ...process.env };
    const plat = process.platform;
    const home = os.homedir();
    const extras = [];
    const gitDir = resolveGitDir();
    if (gitDir) extras.push(gitDir);
    if (plat === 'darwin') {
        extras.push('/opt/homebrew/bin', '/usr/local/bin', '/usr/bin', `${home}/.local/bin`);
    } else if (plat === 'linux') {
        extras.push('/usr/local/bin', '/usr/bin', `${home}/.local/bin`);
    }
    const cur = env.PATH || '';
    env.PATH = [...extras, cur].filter(Boolean).join(path.delimiter);
    return env;
}

function shellQuoteForExec(cmd) {
    if (!cmd) return "''";
    if (/[\s'"\\]/.test(cmd)) return `'${cmd.replace(/'/g, "'\\''")}'`;
    return cmd;
}

function isLikelyAppleStubPython(resolvedAbsPath) {
    const n = String(resolvedAbsPath).toLowerCase().replace(/\\/g, '/');
    return n.includes('commandlinetools') || n.includes('/library/developer/commandlinetools');
}

function collectDarwinPythonCandidates(home) {
    return [
        '/opt/homebrew/bin/python3',
        '/usr/local/bin/python3',
        path.join(home, '.local', 'bin', 'python3'),
        path.join(home, '.pyenv', 'shims', 'python3'),
        '/usr/bin/python3',
    ];
}

function getPaperforgePythonCmd() {
    const plat = process.platform;
    const home = os.homedir();
    if (plat === 'darwin') {
        let stubFallback = null;
        for (const p of collectDarwinPythonCandidates(home)) {
            try {
                if (!p || !fs.existsSync(p)) continue;
                let resolved = p;
                try { resolved = fs.realpathSync(p); } catch (_) {}
                if (isLikelyAppleStubPython(resolved)) {
                    if (!stubFallback) stubFallback = p;
                    continue;
                }
                return p;
            } catch (_) {}
        }
        if (stubFallback) return stubFallback;
        return 'python3';
    }
    const candidates = [];
    if (plat === 'linux') {
        candidates.push('/usr/bin/python3', '/usr/local/bin/python3', path.join(home, '.local', 'bin', 'python3'), path.join(home, '.pyenv', 'shims', 'python3'));
    }
    for (const p of candidates) {
        try { if (p && fs.existsSync(p)) return p; } catch (_) {}
    }
    if (plat === 'win32') return 'python';
    return 'python3';
}

function paperforgePythonExecArgs(scriptTail) {
    const py = shellQuoteForExec(getPaperforgePythonCmd());
    return `${py} ${scriptTail}`;
}

function tryExecPythonVersion(callback) {
    const plat = process.platform;
    const home = os.homedir();
    const tried = new Set();
    const list = [];
    if (plat === 'darwin') {
        const nonStub = [], stub = [];
        for (const p of collectDarwinPythonCandidates(home)) {
            try {
                if (!fs.existsSync(p)) continue;
                let resolved = p;
                try { resolved = fs.realpathSync(p); } catch (_) {}
                if (isLikelyAppleStubPython(resolved)) stub.push(p);
                else nonStub.push(p);
            } catch (_) {}
        }
        list.push(...nonStub, ...stub);
    } else if (plat === 'linux') {
        list.push('/usr/bin/python3', '/usr/local/bin/python3', path.join(home, '.local', 'bin', 'python3'), path.join(home, '.pyenv', 'shims', 'python3'));
    }
    list.push(plat === 'win32' ? 'python' : 'python3', 'python');
    const candidates = list.filter((c) => { if (!c || tried.has(c)) return false; tried.add(c); return true; });
    let i = 0;
    const next = () => {
        if (i >= candidates.length) { callback(new Error('Python not found'), '', null); return; }
        const py = candidates[i++];
        if (py.includes(path.sep) || py.startsWith('/')) {
            try { if (!fs.existsSync(py)) { next(); return; } } catch (_) { next(); return; }
        }
        exec(`${shellQuoteForExec(py)} --version`, { timeout: 8000, env: paperforgeEnrichedEnv() }, (err, stdout) => {
            if (!err && stdout) callback(null, stdout.trim(), py);
            else next();
        });
    };
    next();
}

function dirLooksLikeBetterBibtexFolder(entryName) {
    const compact = String(entryName).toLowerCase().replace(/[^a-z0-9]/g, '');
    return compact.includes('betterbibtex');
}

function scanBbtDirectChildren(dir) {
    if (!dir) return false;
    try {
        if (!fs.existsSync(dir)) return false;
        for (const entry of fs.readdirSync(dir)) {
            if (dirLooksLikeBetterBibtexFolder(entry)) return true;
        }
    } catch (_) {}
    return false;
}

function scanBbtUnderProfiles(profilesDir) {
    if (!profilesDir) return false;
    try {
        if (!fs.existsSync(profilesDir)) return false;
        for (const prof of fs.readdirSync(profilesDir)) {
            const extDir = path.join(profilesDir, prof, 'extensions');
            try {
                if (!fs.existsSync(extDir)) continue;
                for (const entry of fs.readdirSync(extDir)) {
                    if (dirLooksLikeBetterBibtexFolder(entry)) return true;
                }
            } catch (_) {}
        }
    } catch (_) {}
    return false;
}



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

    /* ── DASH-02: /pf-deep Handoff (Plan 54-001) ── */
    copy_pf_deep_cmd: 'Copy /pf-deep Command',
    copied: 'Copied!',
    run_in_agent: 'Run in {0}',

    /* ── DASH-03: Privacy Warning (Plan 54-003) ── */
    ocr_privacy_title: 'OCR Privacy Notice',
    ocr_privacy_warning: 'OCR will upload PDFs to the PaddleOCR API. Do not upload sensitive or confidential documents.',
    ocr_understand: 'I understand, continue',

    /* ── Tabbed Settings ── */
    tab_setup: 'Installation',
    tab_features: 'Features',
    /* ── Features tab descriptions ── */
    feat_skills_desc: 'Manage and enable/disable agent skills installed in your vault. Each row corresponds to a SKILL.md file — toggle off to prevent the agent from auto-invoking that skill.',
    feat_skills_system: 'System Skills ship with PaperForge and are updated alongside PaperForge.',
    feat_skills_user: 'User Skills are custom skills you install from community or create yourself.',
    feat_memory_desc: 'The Memory Layer is the core data engine of PaperForge, powered by SQLite. It integrates all literature metadata (papers, assets, aliases, reading events), provides FTS5 full-text search across titles/abstracts/authors/collections, and enables the agent-context and paper-status commands. Always active — no toggle needed.',
    feat_vector_desc: 'Vector Database enables semantic search across OCR-extracted fulltext using embedding models. Documents are split into chunks, embedded into vector space, and stored in ChromaDB. Supports local models (free, CPU) or OpenAI API (paid, faster).',
    feat_vector_config_label: 'Advanced Configuration',
    feat_agent_platform: 'Agent Platform',
    feat_agent_platform_desc: 'Select which agent platform to manage skills for.',
    feat_vector_enable: 'Enable Vector Retrieval',
    feat_vector_enable_desc: 'Semantic search across OCR fulltext. Requires: pip install chromadb sentence-transformers openai (~500MB).',
    feat_hf_mirror: 'HF Mirror / Endpoint',
    feat_hf_mirror_desc: 'Model download source. Try official if mirror fails. Custom: type any URL.',
    feat_custom_endpoint: 'Custom Endpoint',
    feat_custom_endpoint_desc: 'Enter a custom HuggingFace mirror URL.',
    feat_hf_token: 'HF Token',
    feat_hf_token_desc: 'HuggingFace access token (optional, helps with rate limits and gated models).',
    feat_model: 'Model',
    feat_embed_mode: 'Embedding Mode',
    feat_embed_mode_local: 'Local (free, CPU)',
    feat_embed_mode_api: 'API (OpenAI, paid)',
    feat_openai_key: 'OpenAI API Key',
    feat_openai_key_desc: 'Used for text-embedding-3-small (1536d).',
    feat_verify: 'Verify',
    feat_checking: 'Checking...',
    feat_rebuild_vectors: 'Rebuild Vectors',
    feat_rebuild_vectors_desc: 'Rebuild all OCR fulltext vectors. Required after model or mode change.',
    feat_rebuild_vectors_changed: 'Model changed — rebuild to update all vectors.',
    feat_install_deps: 'Install Dependencies',
    feat_install_deps_desc: 'pip install chromadb sentence-transformers openai (~500MB).',
    feat_model_bge_small: 'Best balance — fast, accurate, recommended for most users (384d, 130MB)',
    feat_model_minilm: 'Lightest & fastest — lower accuracy, minimal disk (384d, 80MB)',
    feat_model_bge_base: 'Highest accuracy — slower, large disk footprint (768d, 440MB)',
    feat_api_base_url: 'API Base URL',
    feat_api_base_url_desc: 'Custom OpenAI-compatible API endpoint. Leave empty for default.',
    feat_api_model: 'API Model',
    feat_api_model_desc: 'Embedding model name for this endpoint.',
    feat_deps_missing: 'Dependencies not installed. Required: chromadb, sentence-transformers, openai.',
    feat_deps_checking: 'Checking dependencies...',
    feat_no_python: 'No Python found. Check Installation tab.',
    feat_rebuild_btn: 'Rebuild',
    feat_build_btn: 'Build',
    feat_building: 'Building...',
    feat_installing: 'Installing...',
    feat_install_btn: 'Install',
    feat_retry_btn: 'Retry',
    feat_removing: 'Removing...',
    feat_not_cached: 'Not cached',
    feat_uninstall_btn: 'Uninstall',
    feat_verify_btn: 'Verify',
    feat_checking_btn: 'Checking...',
    feat_valid_key: 'API key valid.',
    feat_key_rejected: 'API key rejected.',
    feat_enter_key: 'Enter a valid OpenAI API key.',
    feat_network_error: 'Network error: ',
    feat_build_complete: 'Vector build complete.',
    feat_build_failed: 'Build failed. See terminal output.',
    feat_output_copied: 'Output copied to clipboard.',
    feat_install_done: 'Dependencies installed. Building vectors...',
    feat_install_failed: 'Install failed: ',
});

/* ── LANG.zh: v1.12 runtime health, OCR queue, pf-deep, dashboard translations ── */
Object.assign(LANG.zh, {
    field_python_interp: '当前 Python 解释器',
    field_python_custom: '自定义 Python 路径',
    btn_validate: '验证',
    runtime_health: '运行时状态',
    runtime_health_desc: '检查插件与 Python 运行时版本的匹配情况',
    runtime_health_plugin_ver: '插件 v{0}',
    runtime_health_package_ver: 'Python 包 v{0}',
    runtime_health_match: '匹配',
    runtime_health_mismatch: '不匹配',
    runtime_health_checking: '正在检测…',
    runtime_health_sync: '同步运行时',
    runtime_health_syncing: '正在同步…',
    runtime_health_sync_done: '运行时已同步至 v{0}',
    runtime_health_sync_fail: '运行时同步失败：{0}',
    dashboard_drift_warning: '插件版本与 Python 运行时版本不匹配。请在设置中点击"同步运行时"。',
    error_copy_diagnostic: '复制诊断信息',
    error_copied: '已复制！',
    ocr_queue_add: '加入 OCR 队列',
    ocr_queue_remove: '移出 OCR 队列',
    ocr_queue_added: '已加入 OCR 队列',
    ocr_queue_removed: '已移出 OCR 队列',
    no_pending_ocr: '所有 OCR 任务已完成',
    copy_pf_deep_cmd: '复制 /pf-deep 命令',
    copied: '已复制！',
    run_in_agent: '在 {0} 中运行',
    ocr_privacy_title: 'OCR 隐私提示',
    ocr_privacy_warning: 'OCR 会将 PDF 上传到 PaddleOCR API 进行处理。请不要上传包含敏感信息或无法外传的文献。',
    ocr_understand: '我了解，继续',
    install_validating: '正在校验安装环境…',
    install_bootstrapping: '未检测到 PaperForge Python 包，正在自动安装…',
    wizard_safety: '安全说明：如果你选择的目录里已经有文件，安装向导会保留已有内容，只补充缺失的 PaperForge 文件和目录。',

    /* ── Tabbed Settings ── */
    tab_setup: '安装',
    tab_features: '功能',
    /* ── 功能介绍的描述文本 ── */
    feat_skills_desc: '管理 Vault 中已安装的 Agent 技能。每行对应一个 SKILL.md 文件，关闭开关可阻止 Agent 自动调用该技能。',
    feat_skills_system: '系统技能随 PaperForge 一同发布，会跟随 PaperForge 版本更新。',
    feat_skills_user: '用户技能是你自行安装或创建的自定义技能。',
    feat_memory_desc: '记忆层是 PaperForge 的核心数据引擎，基于 SQLite 构建。它整合了所有文献元数据（论文、资源文件、别名、阅读事件），支持 FTS5 全文检索（可搜索标题、摘要、作者、分类），并为 agent-context 和 paper-status 命令提供数据支撑。始终运行，无需手动开启。',
    feat_vector_desc: '向量数据库通过嵌入模型实现 OCR 全文的语义搜索。文档被切分为文本块（chunk），编码为向量存入 ChromaDB。支持本地模型（免费，CPU 运行）或 OpenAI API（付费，更快速）。',
    feat_vector_config_label: '高级配置',
    feat_agent_platform: 'Agent 平台',
    feat_agent_platform_desc: '选择要管理的 Agent 平台。',
    feat_vector_enable: '启用向量检索',
    feat_vector_enable_desc: '对 OCR 全文进行语义搜索。需安装: pip install chromadb sentence-transformers openai (~500MB)。',
    feat_hf_mirror: 'HF 镜像站 / 端点',
    feat_hf_mirror_desc: '模型下载源。镜像不可用时尝试官方源。自定义：输入任意 URL。',
    feat_custom_endpoint: '自定义端点',
    feat_custom_endpoint_desc: '输入自定义 HuggingFace 镜像 URL。',
    feat_hf_token: 'HF Token',
    feat_hf_token_desc: 'HuggingFace 访问令牌（可选，有助于解除限速和下载受限模型）。',
    feat_model: '模型',
    feat_embed_mode: '嵌入模式',
    feat_embed_mode_local: '本地（免费，CPU）',
    feat_embed_mode_api: 'API（OpenAI，付费）',
    feat_openai_key: 'OpenAI API Key',
    feat_openai_key_desc: '用于 text-embedding-3-small（1536 维）。',
    feat_verify: '验证',
    feat_checking: '检测中…',
    feat_rebuild_vectors: '重建向量',
    feat_rebuild_vectors_desc: '重建所有 OCR 全文向量。更换模型或模式后需要重建。',
    feat_rebuild_vectors_changed: '模型已更换 — 需要重建向量。',
    feat_install_deps: '安装依赖',
    feat_install_deps_desc: 'pip install chromadb sentence-transformers openai (~500MB)。',
    feat_model_bge_small: '最佳平衡 — 快速、准确，推荐大多数用户使用 (384d, 130MB)',
    feat_model_minilm: '最轻最快 — 精度略低，磁盘占用最小 (384d, 80MB)',
    feat_model_bge_base: '最高精度 — 较慢，磁盘占用大 (768d, 440MB)',
    feat_api_base_url: 'API 地址',
    feat_api_base_url_desc: '自定义 OpenAI 兼容 API 端点。留空使用默认地址。',
    feat_api_model: 'API 模型',
    feat_api_model_desc: '该端点使用的嵌入模型名称。',
    feat_deps_missing: '依赖未安装。需要：chromadb, sentence-transformers, openai。',
    feat_deps_checking: '正在检测依赖…',
    feat_no_python: '未找到 Python。请查看安装标签页。',
    feat_rebuild_btn: '重建',
    feat_build_btn: '构建',
    feat_building: '构建中…',
    feat_installing: '安装中…',
    feat_install_btn: '安装',
    feat_retry_btn: '重试',
    feat_removing: '删除中…',
    feat_not_cached: '未缓存',
    feat_uninstall_btn: '卸载',
    feat_verify_btn: '验证',
    feat_checking_btn: '检测中…',
    feat_valid_key: 'API Key 有效。',
    feat_key_rejected: 'API Key 被拒绝。',
    feat_enter_key: '请输入有效的 OpenAI API Key。',
    feat_network_error: '网络错误：',
    feat_build_complete: '向量构建完成。',
    feat_build_failed: '构建失败。请查看终端输出。',
    feat_output_copied: '输出已复制到剪贴板。',
    feat_install_done: '依赖已安装。正在构建向量…',
    feat_install_failed: '安装失败：',
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
    return 'en';  // default English
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
    // Feature toggles
    features: {
        memory_layer: true,
        vector_db: false,
    },
    selected_skill_platform: 'opencode',
    vector_db_mode: 'local',
    vector_db_model: 'BAAI/bge-small-en-v1.5',
    vector_db_api_key: '',
    vector_db_api_base: '',
    vector_db_api_model: 'text-embedding-3-small',
    vector_db_hf_endpoint: 'https://hf-mirror.com',
    vector_db_hf_token: '',
    vector_db_last_model: '',
    frozen_skills: {},
};

// ACTIONS, resolvePythonExecutable extracted to src/ modules (Plan 53-001)

function overlayEntryWorkflowState(app, entry) {
    if (!entry || !entry.note_path) return entry;
    const noteFile = app.vault.getAbstractFileByPath(entry.note_path);
    if (!noteFile) return entry;
    const cache = app.metadataCache.getFileCache(noteFile);
    const fm = cache && cache.frontmatter;
    if (!fm) return entry;
    const merged = { ...entry };
    for (const key of ['do_ocr', 'analyze', 'ocr_status', 'deep_reading_status']) {
        if (Object.prototype.hasOwnProperty.call(fm, key)) merged[key] = fm[key];
    }
    return merged;
}

function patchEntryWorkflowState(entry, patch) {
    return entry ? { ...entry, ...patch } : entry;
}

class PaperForgeStatusView extends ItemView {
    constructor(leaf) {
        super(leaf);
        this._currentMode = null;       // 'global' | 'paper' | 'collection'
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

    }

    /* ---------------------------------------------------------------------- */
    /*  Fetch & Render Stats                                                  */
    /* ---------------------------------------------------------------------- */
    _fetchVersion() {
        const vp = this.app.vault.adapter.basePath;
        const plugin = this.app.plugins.plugins['paperforge'];
        const pluginVer = plugin?.manifest?.version || '?';
        const { path: pythonExe, extraArgs = [] } = resolvePythonExecutable(vp, plugin?.settings);
        checkRuntimeVersion(pythonExe, pluginVer, vp, 10000).then((result) => {
            if (result.status === 'not-installed') {
                return;
            }
            const v = result.pyVersion || '';
            this._paperforgeVersion = v.startsWith('v') ? v : 'v' + v;
            if (this._versionBadge) this._versionBadge.setText(this._paperforgeVersion);

            // Check drift for dashboard banner
            if (this._driftBannerEl && pluginVer && this._paperforgeVersion !== 'v' + pluginVer.replace(/^v/, '')) {
                this._driftBannerEl.style.display = 'block';
                this._driftBannerEl.setText(t('dashboard_drift_warning')
                    .replace('{0}', this._paperforgeVersion)
                    .replace('{1}', 'v' + pluginVer.replace(/^v/, '')));
            } else if (this._driftBannerEl) {
                this._driftBannerEl.style.display = 'none';
            }
        });
    }

    _fetchStats(quiet) {
        if (!this._metricsEl) return;
        if (!quiet && !this._cachedStats) {
            this._metricsEl.empty();
            this._metricsEl.createEl('div', { cls: 'paperforge-status-loading', text: 'Loading...' });
        } else if (quiet && !this._cachedStats) {
            return;
        }

        const vp = this.app.vault.adapter.basePath;
        const plugin = this.app.plugins.plugins['paperforge'];
        const { path: pythonExe, extraArgs = [] } = resolvePythonExecutable(vp, plugin?.settings);

        // Plan 57-04: Try paperforge dashboard --json first, fallback to file
        execFile(pythonExe, [...extraArgs, '-m', 'paperforge', 'dashboard', '--json'], { cwd: vp, timeout: 30000 }, (err, stdout) => {
            if (!err) {
                try {
                    const body = JSON.parse(stdout);
                    if (body.ok && body.data) {
                        const d = this._normalizeDashboardData(body.data);
                        this._cachedStats = d;
                        this._metricsEl.empty();
                        this._renderStats(d);
                        this._renderOcr(d);
                        this._dashboardPermissions = body.data.permissions || {};
                        return;
                    }
                } catch (_) {
                    // Fall through to file fallback
                }
            }
            // Fallback: read formal-library.json directly
            this._fallbackFetchStats(quiet, vp, plugin);
        });
    }

    _normalizeDashboardData(data) {
        const stats = data.stats || {};
        const ocrHealth = stats.ocr_health || {};
        const pdfHealth = stats.pdf_health || {};
        const ocrTotal = (ocrHealth.done || 0) + (ocrHealth.pending || 0) + (ocrHealth.failed || 0);
        return {
            total_papers: stats.papers || 0,
            formal_notes: stats.papers || 0,
            exports: 0,
            bases: 0,
            ocr: { total: ocrTotal, pending: ocrHealth.pending || 0, processing: 0, done: ocrHealth.done || 0, failed: ocrHealth.failed || 0 },
            path_errors: (pdfHealth.broken || 0) + (pdfHealth.missing || 0),
        };
    }

    _fallbackFetchStats(quiet, vp, plugin) {
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
            // D-07: Second fallback — spawn CLI if file is missing or corrupt
            if (!quiet && !this._cachedStats) {
                this._metricsEl.createEl('div', { cls: 'paperforge-status-loading', text: 'No index \u2014 trying CLI...' });
            }
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
        const entry = this._getCachedIndex().find(item => item.zotero_key === key) || null;
        return overlayEntryWorkflowState(this.app, entry);
    }

    _patchCachedEntry(key, patch) {
        if (!key || !this._cachedItems) return;
        const idx = this._cachedItems.findIndex(item => item.zotero_key === key);
        if (idx === -1) return;
        this._cachedItems[idx] = patchEntryWorkflowState(this._cachedItems[idx], patch);
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

        if (!this._metricsEl) return;  // guard: global mode no longer creates metrics container

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
        if (!this._ocrSection) return;  // guard: global mode no longer creates OCR container
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


    /* ── Invalidate cached index (D-14) ── */
    _invalidateIndex() {
        this._cachedItems = null;
    }

    /* ── Extract zotero_key from workspace directory name ── */
    _extractZoteroKeyFromPath(filePath) {
        if (!filePath) return null;
        let dir = path.dirname(filePath);
        while (true) {
            const basename = path.basename(dir);
            if (!basename || basename === '.') break;
            const match = basename.match(/^([A-Z0-9]{8})(?:\s*-\s*)/i);
            if (match) return match[1];
            const parent = path.dirname(dir);
            if (parent === dir) break;
            dir = parent;
        }
        return null;
    }

    /* ── Pure Mode Resolution (D-07, Phase 32) ── */
    _resolveModeForFile(file) {
        if (!file) return { mode: 'global', filePath: null, key: null, domain: null };

        const ext = file.extension;
        const filePath = file.path;

        if (ext === 'base') {
            return { mode: 'collection', filePath, key: null, domain: file.basename.trim() };
        }

        if (ext === 'md') {
            const cache = this.app.metadataCache.getFileCache(file);
            const fmKey = cache && cache.frontmatter && cache.frontmatter.zotero_key;
            if (fmKey) {
                return { mode: 'paper', filePath, key: fmKey, domain: null };
            }
        }

        // PDF files: match to paper via pdf_path in canonical index
        if (ext === 'pdf') {
            const items = this._getCachedIndex();
            for (const item of items) {
                const pathMatch = (item.pdf_path || '').match(/\[\[([^\]]+)\]\]/);
                const targetPath = pathMatch ? pathMatch[1] : item.pdf_path;
                if (targetPath === filePath) {
                    return { mode: 'paper', filePath, key: item.zotero_key, domain: null };
                }
            }
        }

        // Workspace path detection: any file inside a paper workspace directory
        const wsKey = this._extractZoteroKeyFromPath(filePath);
        if (wsKey) {
            return { mode: 'paper', filePath, key: wsKey, domain: null };
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
        this._techDetailsExpanded = false;  // reset disclosure state on mode switch

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

    /* ── Global Mode Render: System Homepage ── */
    _renderGlobalMode() {
        const view = this._contentEl.createEl('div', { cls: 'paperforge-global-view' });

        // Drift warning banner (hidden by default, shown on version mismatch)
        this._driftBannerEl = view.createEl('div', { cls: 'paperforge-drift-banner' });
        this._driftBannerEl.style.display = 'none';

        // ── Library Snapshot ──
        const items = this._getCachedIndex();
        const totalPapers = items.length;
        let pdfReady = 0, ocrDone = 0, deepReadDone = 0;
        for (const item of items) {
            if (item.has_pdf) pdfReady++;
            if (item.ocr_status === 'done') ocrDone++;
            if (item.deep_reading_status === 'done') deepReadDone++;
        }

        const snapshot = view.createEl('div', { cls: 'paperforge-library-snapshot' });
        snapshot.createEl('div', { cls: 'paperforge-section-label', text: 'Library Snapshot' });
        const pills = snapshot.createEl('div', { cls: 'paperforge-snapshot-pills' });
        const snapData = [
            { value: totalPapers, label: 'papers' },
            { value: pdfReady, label: 'PDFs ready' },
            { value: ocrDone, label: 'OCR done' },
            { value: deepReadDone, label: 'deep-read done' },
        ];
        for (const s of snapData) {
            const pill = pills.createEl('div', { cls: 'paperforge-snapshot-pill' });
            pill.createEl('span', { cls: 'paperforge-snapshot-value', text: String(s.value) });
            pill.createEl('span', { cls: 'paperforge-snapshot-label', text: ' ' + s.label });
        }

        // ── System Status ──
        const statusSection = view.createEl('div', { cls: 'paperforge-system-status' });
        statusSection.createEl('div', { cls: 'paperforge-section-label', text: 'System Status' });
        const statusGrid = statusSection.createEl('div', { cls: 'paperforge-status-grid' });

        // Runtime
        const plugin = this.app.plugins.plugins['paperforge'];
        const pluginVer = plugin?.manifest?.version || '?';
        let pyVer = this._paperforgeVersion;
        if (!pyVer) {
            // Async _fetchVersion() may not have resolved yet — try synchronous fallback
            try {
                const vp = this.app.vault.adapter.basePath;
                const { path: pyExe, extraArgs = [] } = resolvePythonExecutable(vp, plugin?.settings);
                const raw = execFileSync(pyExe, [...extraArgs, '-c', 'import paperforge; print(paperforge.__version__)'], { cwd: vp, timeout: 5000, encoding: 'utf-8', windowsHide: true }).trim();
                if (raw) { pyVer = raw.startsWith('v') ? raw : 'v' + raw; this._paperforgeVersion = pyVer; }
            } catch {}
        }
        pyVer = pyVer || '\u2014';
        const runtimeOk = pyVer === 'v' + pluginVer;
        this._renderSystemStatusRow(statusGrid, 'Runtime', runtimeOk ? 'healthy' : 'mismatch',
            runtimeOk ? ('v' + pluginVer) : ('plugin v' + pluginVer + ' \u2260 CLI ' + pyVer));

        // Index
        const index = this._loadIndex();
        const indexOk = index && index.items && index.items.length > 0;
        this._renderSystemStatusRow(statusGrid, 'Index', indexOk ? 'healthy' : 'missing',
            indexOk ? (index.items.length + ' entries') : 'formal-library.json not found');

        // Zotero export (check if any JSON export exists)
        const systemDir = plugin?.settings?.system_dir || 'System';
        const vp = this.app.vault.adapter.basePath;
        let exportOk = false, exportDetail = 'No exports found';
        try {
            const exportsDir = path.join(vp, systemDir, 'PaperForge', 'exports');
            if (fs.existsSync(exportsDir)) {
                const files = fs.readdirSync(exportsDir).filter(f => f.endsWith('.json'));
                exportOk = files.length > 0;
                exportDetail = exportOk ? (files.length + ' export(s)') : 'No JSON exports';
            }
        } catch (_) {}
        this._renderSystemStatusRow(statusGrid, 'Zotero Export', exportOk ? 'healthy' : 'missing', exportDetail);

        // OCR token (check: plugin settings → .env file → OS environment)
        let tokenOk = !!(plugin?.settings?.paddleocr_api_key);
        if (!tokenOk) {
            try {
                const sysDir = plugin?.settings?.system_dir || 'System';
                const envPath = path.join(vp, sysDir, 'PaperForge', '.env');
                if (fs.existsSync(envPath)) {
                    const envContent = fs.readFileSync(envPath, 'utf-8');
                    const tokenMatch = envContent.match(/^PADDLEOCR_API_TOKEN\s*=\s*(.+)$/m);
                    tokenOk = !!(tokenMatch && tokenMatch[1] && tokenMatch[1].trim());
                }
            } catch (_) {}
        }
        if (!tokenOk) {
            tokenOk = !!(process.env.PADDLEOCR_API_TOKEN || process.env.PADDLEOCR_API_KEY || process.env.OCR_TOKEN);
        }
        this._renderSystemStatusRow(statusGrid, 'OCR Token', tokenOk ? 'configured' : 'missing',
            tokenOk ? 'Configured' : 'Not set');

        // ── Issues Panel (only for serious blockers) ──
        const hasVersionMismatch = !runtimeOk && pyVer !== '\u2014';
        const hasIssues = hasVersionMismatch || !indexOk || !exportOk || !tokenOk;
        if (hasIssues) {
            const issueSection = view.createEl('div', { cls: 'paperforge-issue-summary' });
            issueSection.createEl('div', { cls: 'paperforge-section-label', text: '需要处理' });
            const issueList = issueSection.createEl('div', { cls: 'paperforge-issue-list' });
            if (hasVersionMismatch) issueList.createEl('div', { cls: 'paperforge-issue-item', text: 'Runtime version mismatch' });
            if (!indexOk) issueList.createEl('div', { cls: 'paperforge-issue-item', text: 'Index missing or corrupted' });
            if (!exportOk) issueList.createEl('div', { cls: 'paperforge-issue-item', text: 'No Zotero export found' });
            if (!tokenOk) issueList.createEl('div', { cls: 'paperforge-issue-item', text: 'PaddleOCR API key not configured' });

            const issueActions = issueSection.createEl('div', { cls: 'paperforge-issue-actions' });
            const doctorBtn = issueActions.createEl('button', { cls: 'paperforge-contextual-btn' });
            doctorBtn.createEl('span', { text: 'Run Doctor' });
            doctorBtn.addEventListener('click', () => {
                const action = ACTIONS.find(a => a.id === 'paperforge-doctor');
                if (action) this._runAction(action, doctorBtn);
            });
            const repairBtn = issueActions.createEl('button', { cls: 'paperforge-contextual-btn' });
            repairBtn.createEl('span', { text: 'Repair Issues' });
            repairBtn.addEventListener('click', () => {
                const action = ACTIONS.find(a => a.id === 'paperforge-repair');
                if (action) this._runAction(action, repairBtn);
            });
        }

        // ── Contextual Actions ──
        const actionsRow = view.createEl('div', { cls: 'paperforge-global-actions' });
        actionsRow.createEl('div', { cls: 'paperforge-section-label', text: 'Start Working' });
        const btnsRow = actionsRow.createEl('div', { cls: 'paperforge-global-actions-row' });
        const hubBtn = btnsRow.createEl('button', { cls: 'paperforge-contextual-btn primary' });
        hubBtn.createEl('span', { cls: 'paperforge-contextual-btn-icon', text: '\uD83D\uDCC1' });
        hubBtn.createEl('span', { text: 'Open Literature Hub' });
        hubBtn.addEventListener('click', () => {
            const baseDir = plugin?.settings?.base_dir || 'Bases';
            const baseFolder = this.app.vault.getAbstractFileByPath(baseDir);
            if (baseFolder) {
                // Find first .base file in the base directory
                let baseFile = null;
                if (baseFolder.children) {
                    baseFile = baseFolder.children.find(f => f.extension === 'base');
                }
                if (baseFile) {
                    const leaf = this.app.workspace.getLeaf(false);
                    if (leaf) leaf.openFile(baseFile);
                } else {
                    new Notice('[!!] No .base file found in ' + baseDir, 6000);
                }
            } else {
                new Notice('[!!] Base directory not found: ' + baseDir, 6000);
            }
        });

        const globalSyncBtn = btnsRow.createEl('button', { cls: 'paperforge-contextual-btn' });
        globalSyncBtn.createEl('span', { cls: 'paperforge-contextual-btn-icon', text: '\u21BB' });
        globalSyncBtn.createEl('span', { text: 'Sync Library' });
        globalSyncBtn.addEventListener('click', () => {
            const action = ACTIONS.find(a => a.id === 'paperforge-sync');
            if (action) this._runAction(action, globalSyncBtn);
        });
    }

    /* ── System Status Row helper ── */
    _renderSystemStatusRow(container, label, status, detail) {
        const row = container.createEl('div', { cls: 'paperforge-status-row' });
        const dot = row.createEl('span', { cls: 'paperforge-status-dot' });
        dot.addClass(status === 'healthy' || status === 'configured' ? 'ok' : 'fail');
        row.createEl('span', { cls: 'paperforge-status-label', text: label });
        row.createEl('span', { cls: 'paperforge-status-detail', text: detail || '' });
    }

    /* ── Per-Paper Mode Render: Reading Companion ── */
    _renderPaperMode() {
        const entry = this._currentPaperEntry;
        const key = this._currentPaperKey;

        if (!key) {
            this._renderEmptyState(this._contentEl, 'No paper data available.');
            return;
        }

        if (!entry) {
            this._contentEl.createEl('div', {
                cls: 'paperforge-content-placeholder',
                text: 'Paper "' + key + '" not found in canonical index. Sync first.',
            });
            return;
        }

        const view = this._contentEl.createEl('div', { cls: 'paperforge-paper-view' });

        // ── Header ──
        const header = view.createEl('div', { cls: 'paperforge-paper-header' });
        header.createEl('div', { cls: 'paperforge-paper-title', text: entry.title || 'Untitled' });
        const meta = header.createEl('div', { cls: 'paperforge-paper-meta' });
        if (entry.authors && entry.authors.length > 0) {
            meta.createEl('span', { cls: 'paperforge-paper-authors', text: entry.authors.join(', ') });
        }
        if (entry.year) {
            meta.createEl('span', { cls: 'paperforge-paper-year', text: String(entry.year) });
        }

        // ── Status Strip + File Buttons (merged row) ──
        const strip = view.createEl('div', { cls: 'paperforge-status-strip' });
        const stripLeft = strip.createEl('div', { cls: 'paperforge-status-strip-left' });
        const stripRight = strip.createEl('div', { cls: 'paperforge-status-strip-right' });

        const items = [
            { key: 'pdf', label: 'PDF', ok: entry.has_pdf === true },
            { key: 'ocr', label: 'OCR',
              ok: entry.ocr_status === 'done',
              pending: ['pending','queued','processing'].includes(entry.ocr_status || ''),
              fail: ['failed','blocked','done_incomplete','nopdf'].includes(entry.ocr_status || '') },
            { key: 'deep', label: '精读', ok: entry.deep_reading_status === 'done' },
        ];
        for (const item of items) {
            const pill = stripLeft.createEl('span', { cls: 'paperforge-status-pill' });
            let statusCls = 'pending';
            if (item.ok) statusCls = 'ok';
            else if (item.fail) statusCls = 'fail';
            else if (item.pending) statusCls = 'pending';
            pill.addClass(statusCls);
            const icon = item.ok ? '\u2713' : (item.fail ? '\u2717' : '\u25CB');
            pill.createEl('span', { cls: 'paperforge-status-pill-icon', text: icon });
            pill.createEl('span', { text: ' ' + item.label });
        }

        // File buttons in status strip row
        if (entry.pdf_path) {
            const pdfBtn = stripRight.createEl('button', { cls: 'paperforge-contextual-btn' });
            pdfBtn.createEl('span', { cls: 'paperforge-contextual-btn-icon', text: '\uD83D\uDCC4' });
            pdfBtn.createEl('span', { text: '打开 PDF' });
            pdfBtn.addEventListener('click', () => {
                const pathMatch = entry.pdf_path.match(/\[\[([^\]]+)\]\]/);
                const targetPath = pathMatch ? pathMatch[1] : entry.pdf_path;
                const file = this.app.vault.getAbstractFileByPath(targetPath);
                if (file) { this.app.workspace.openLinkText(targetPath, ''); }
                else { new Notice('[!!] PDF not found: ' + targetPath, 6000); }
            });
        }
        if (entry.fulltext_path) {
            const ftBtn = stripRight.createEl('button', { cls: 'paperforge-contextual-btn' });
            ftBtn.createEl('span', { cls: 'paperforge-contextual-btn-icon', text: '\uD83D\uDCDD' });
            ftBtn.createEl('span', { text: '打开全文' });
            ftBtn.addEventListener('click', () => this._openFulltext(entry.fulltext_path));
        }

        // ── Paper Overview ──
        this._renderPaperOverviewCard(view, entry);

        // ── Complete state or Next Step ──
        if (entry.next_step === 'ready' && entry.deep_reading_status === 'done') {
            const complete = view.createEl('div', { cls: 'paperforge-complete-row' });
            complete.createEl('span', { text: '\u2713' });
            complete.createEl('span', { text: '已完成，可直接使用' });
        } else {
            this._renderNextStepCard(view, entry, key);
        }

        // ── Recent Discussion ──
        this._renderRecentDiscussionCard(view, entry);

        // ── Technical Details (disclosure) ──
        this._renderPaperTechnicalDetails(view, entry);
    }

    /* ── Paper Overview Card: read from formal note body ── */
    _renderPaperOverviewCard(container, entry) {
        const card = container.createEl('div', { cls: 'paperforge-paper-overview' });
        const header = card.createEl('div', { cls: 'paperforge-paper-overview-header' });
        header.createEl('span', { cls: 'paperforge-paper-overview-title', text: '文章概览' });
        const body = card.createEl('div', { cls: 'paperforge-paper-overview-body' });
        const excerptEl = body.createEl('div', { cls: 'paperforge-paper-overview-excerpt', text: '加载中...' });

        // Async read formal note body
        if (entry.note_path) {
            const noteFile = this.app.vault.getAbstractFileByPath(entry.note_path);
            if (noteFile) {
                this.app.vault.read(noteFile).then((content) => {
                    const extracted = this._extractOverviewFromNote(content);
                    if (extracted) {
                        const truncated = extracted.length > 200 ? extracted.slice(0, 200) + '...' : extracted;
                        excerptEl.setText(truncated);
                        if (extracted.length > 200) {
                            const expandContainer = body.createEl('div', { cls: 'paperforge-expand-container' });
                            const expandBtn = expandContainer.createEl('button', { cls: 'paperforge-expand-icon', title: '展开/收起' });
                            
                            // Insert arrow SVG
                            expandBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>';
                            
                            let expanded = false;
                            
                            // Make the whole container clickable
                            expandContainer.addEventListener('click', () => {
                                excerptEl.setText(expanded ? truncated : extracted);
                                expandBtn.innerHTML = expanded 
                                    ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>'
                                    : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>';
                                expanded = !expanded;
                            });
                        }
                    } else {
                        excerptEl.setText('尚未生成文章概览。运行 /pf-deep 开始精读。');
                    }
                }).catch(() => {
                    excerptEl.setText('无法读取笔记内容');
                });
            } else {
                excerptEl.setText('笔记文件不存在');
            }
        } else {
            excerptEl.setText('尚未生成文章概览');
        }
    }

    /* ── Extract overview from formal note body ── */
    _extractOverviewFromNote(content) {
        if (!content) return null;
        // Find "## 🔍 精读" section
        const deepIdx = content.indexOf('## 🔍 精读');
        if (deepIdx === -1) return null;
        const section = content.slice(deepIdx);
        // Extract "**一句话总览**" or "**文章摘要**" or "**一句话总览:**"
        const markers = ['**一句话总览:**', '**一句话总览**', '**文章摘要:**', '**文章摘要**'];
        for (const marker of markers) {
            const idx = section.indexOf(marker);
            if (idx !== -1) {
                const after = section.slice(idx + marker.length);
                // Cut at next marker or double newline
                const cutMarkers = ['**5 Cs', '**Figure', '**证据', '### Pass 2', '## '];
                let nextCut = after.length;
                for (const cm of cutMarkers) {
                    const ci = after.indexOf(cm);
                    if (ci !== -1 && ci < nextCut) nextCut = ci;
                }
                // Also stop at double newline
                const nnIdx = after.indexOf('\n\n');
                if (nnIdx !== -1 && nnIdx < nextCut) nextCut = nnIdx;
                let text = after.slice(0, nextCut).trim();
                // Clean up leading ** if marker didn't include trailing **
                if (text.startsWith('**')) text = text.slice(2);
                if (text.endsWith('**')) text = text.slice(0, -2);
                return text || null;
            }
        }
        // Fallback: return first paragraph of the deep reading section
        const firstNewline = section.indexOf('\n');
        if (firstNewline === -1) return null;
        const para = section.slice(firstNewline + 1).split('\n\n')[0].trim();
        // Skip empty or header-only lines
        if (!para || para.startsWith('###') || para.startsWith('##')) return null;
        return para.length > 300 ? para.slice(0, 300) + '...' : para;
    }

    /* ── Recent Discussion Card: read ai/discussion.json ── */
    _renderRecentDiscussionCard(container, entry) {
        const card = container.createEl('div', { cls: 'paperforge-discussion-card' });
        card.style.display = 'none';

        if (!entry.note_path) return;
        const lastSlash = entry.note_path.lastIndexOf('/');
        const wsDir = lastSlash !== -1 ? entry.note_path.substring(0, lastSlash) : '.';
        const discPath = wsDir + '/ai/discussion.json';

        // Use Obsidian adapter for path correctness (handles unicode reliably)
        this.app.vault.adapter.exists(discPath).then((exists) => {
            if (!exists) return;
            return this.app.vault.adapter.read(discPath);
        }).then((raw) => {
            if (!raw) return;
            const data = JSON.parse(raw);
            if (!data.sessions || data.sessions.length === 0) return;

            card.style.display = 'block';
            const header = card.createEl('div', { cls: 'paperforge-discussion-header' });
            header.createEl('span', { cls: 'paperforge-discussion-title', text: '最近讨论' });

            const latestSession = data.sessions[data.sessions.length - 1];
            const pairs = (latestSession.qa_pairs || []).slice(-3);

            for (const qa of pairs) {
                const item = card.createEl('div', { cls: 'paperforge-discussion-item' });
                const qEl = item.createEl('div', { cls: 'paperforge-discussion-q', text: '提问：' + qa.question });
                const aEl = item.createEl('div', { cls: 'paperforge-discussion-a' });
                const shortAnswer = qa.answer && qa.answer.length > 150
                    ? qa.answer.slice(0, 150) + '...'
                    : (qa.answer || '');
                aEl.createEl('span', { cls: 'paperforge-discussion-a-text', text: '解答：' + shortAnswer });
                if (qa.answer && qa.answer.length > 150) {
                    const expandContainer = aEl.createEl('div', { cls: 'paperforge-expand-container' });
                    const expandBtn = expandContainer.createEl('button', { cls: 'paperforge-expand-icon', title: '展开/收起' });
                    
                    // Insert arrow SVG
                    expandBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>';
                    
                    let expanded = false;
                    
                    // Make the whole container clickable
                    expandContainer.addEventListener('click', () => {
                        const textSpan = aEl.querySelector('.paperforge-discussion-a-text');
                        if (textSpan) {
                            textSpan.setText(expanded ? ('解答：' + shortAnswer) : ('解答：' + qa.answer));
                        }
                        expandBtn.innerHTML = expanded 
                            ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>'
                            : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>';
                        expanded = !expanded;
                    });
                }
            }

            // "查看全部" link
            const viewAll = card.createEl('a', { cls: 'paperforge-discussion-viewall', text: '查看全部讨论 →' });
            viewAll.addEventListener('click', (e) => {
                e.preventDefault();
                const discMdPath = wsDir + '/ai/discussion.md';
                const discFile = this.app.vault.getAbstractFileByPath(discMdPath);
                if (discFile) {
                    this.app.workspace.openLinkText(discMdPath, '');
                } else {
                    new Notice('讨论文件尚未生成');
                }
            });
        }).catch((e) => {
            console.error('PaperForge: discussion.json read error', discPath, e.message);
        });
    }

    /* ── Paper Technical Details (disclosure with workflow toggles) ── */
    _renderPaperTechnicalDetails(container, entry) {
        const key = this._currentPaperKey;
        const section = container.createEl('div', { cls: 'paperforge-technical-details' });
        const toggle = section.createEl('button', { cls: 'paperforge-technical-details-toggle' });
        const body = section.createEl('div', { cls: 'paperforge-technical-details-body' });
        body.style.display = 'none';

        // Restore expanded state from previous render (prevents flash on refresh)
        if (this._techDetailsExpanded) {
            body.style.display = 'block';
            toggle.setText('技术详情 ▾');
        } else {
            toggle.setText('技术详情 ▸');
        }

        toggle.addEventListener('click', () => {
            const visible = body.style.display !== 'none';
            body.style.display = visible ? 'none' : 'block';
            toggle.setText(visible ? '技术详情 ▸' : '技术详情 ▾');
            this._techDetailsExpanded = !visible;
        });

        // Workflow toggles inside disclosure
        const togglesRow = body.createEl('div', { cls: 'paperforge-workflow-toggles' });
        const toggleFields = [
            { key: 'do_ocr', label: 'OCR', hint: '加入 OCR' },
            { key: 'analyze', label: '精读', hint: '标记精读' },
        ];
        for (const tf of toggleFields) {
            const label = togglesRow.createEl('label', { cls: 'paperforge-workflow-toggle' });
            const cb = label.createEl('input', { type: 'checkbox', cls: 'paperforge-workflow-checkbox' });
            cb.checked = entry[tf.key] === true;
            label.createEl('span', { cls: 'paperforge-workflow-toggle-label', text: tf.label });
            label.createEl('span', { cls: 'paperforge-workflow-toggle-hint', text: tf.hint });
            cb.addEventListener('change', async () => {
                const noteFile = entry.note_path ? this.app.vault.getAbstractFileByPath(entry.note_path) : null;
                if (!noteFile) { new Notice('[!!] Note file not found', 6000); return; }
                const newVal = cb.checked;
                await this.app.fileManager.processFrontMatter(noteFile, (fm) => { fm[tf.key] = newVal; });
                this._patchCachedEntry(key, { [tf.key]: newVal });
                this._currentPaperEntry = patchEntryWorkflowState(this._currentPaperEntry, { [tf.key]: newVal });
            });
        }

        const health = entry.health || {};
        const rows = [
            ['PDF Health', health.pdf_health || '\u2014'],
            ['OCR Status', entry.ocr_status || '\u2014'],
            ['Asset Health', health.asset_health || '\u2014'],
            ['Note Path', entry.note_path || '\u2014'],
            ['Fulltext Path', entry.fulltext_path || '\u2014'],
        ];
        for (const [l, v] of rows) {
            const row = body.createEl('div', { cls: 'paperforge-technical-row' });
            row.createEl('span', { cls: 'paperforge-technical-label', text: l });
            row.createEl('span', { cls: 'paperforge-technical-value', text: String(v) });
        }
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
            const platformKey = this.app.plugins.plugins['paperforge']?.settings?.agent_platform || 'opencode';
            const AGENTS = {
                'opencode': 'OpenCode',
                'claude': 'Claude Code',
                'cursor': 'Cursor',
                'github_copilot': 'GitHub Copilot',
                'windsurf': 'Windsurf',
                'codex': 'Codex',
                'cline': 'Cline'
            };
            const platformName = AGENTS[platformKey] || platformKey;
            const labelEl = card.createEl('div', { cls: 'paperforge-agent-platform-label' });
            labelEl.setText(t('run_in_agent').replace('{0}', platformName));
        } else if (nextStep === 'ready') {
            const trigger = card.createEl('button', { cls: 'paperforge-next-step-trigger' });
            trigger.createEl('span', { text: '✓  ' + info.label });
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






    /* ── Collection Mode Render: Batch Workflow Workspace ── */
    _renderCollectionMode() {
        const domain = this._currentDomain || 'Unknown';
        const domainItems = this._filterByDomain(domain);

        if (domainItems.length === 0) {
            // Fall back to global mode if no papers match this domain (e.g. "Literature Hub")
            this._renderGlobalMode();
            return;
        }

        const view = this._contentEl.createEl('div', { cls: 'paperforge-collection-view' });

        // ── Single-pass aggregation ──
        const totalPapers = domainItems.length;
        let hasPdf = 0, ocrDone = 0, analyzeReady = 0, deepRead = 0;
        let ocrPending = 0, ocrProcessing = 0, ocrFailed = 0;

        for (const item of domainItems) {
            if (item.has_pdf) hasPdf++;
            if (item.ocr_status === 'done') ocrDone++;
            if (item.ocr_status === 'done' && item.analyze === true) analyzeReady++;
            if (item.deep_reading_status === 'done') deepRead++;

            const ocs = item.ocr_status || '';
            if (ocs === 'pending' || ocs === 'queued') ocrPending++;
            else if (ocs === 'processing') ocrProcessing++;
            else if (ocs === 'failed' || ocs === 'blocked' || ocs === 'done_incomplete' || ocs === 'nopdf') ocrFailed++;
        }

        // ── Header ──
        const header = view.createEl('div', { cls: 'paperforge-collection-header' });
        header.createEl('div', { cls: 'paperforge-collection-title', text: domain });

        // ── Workflow Overview (funnel) ──
        const wfSection = view.createEl('div', { cls: 'paperforge-workflow-overview' });
        wfSection.createEl('div', { cls: 'paperforge-section-label', text: 'Workflow Overview' });
        const funnel = wfSection.createEl('div', { cls: 'paperforge-workflow-funnel' });
        const stages = [
            { value: totalPapers, label: 'Total' },
            { value: hasPdf, label: 'PDF Ready' },
            { value: ocrDone, label: 'OCR Done' },
            { value: deepRead, label: 'Deep Read' },
        ];
        for (let i = 0; i < stages.length; i++) {
            const stage = funnel.createEl('div', { cls: 'paperforge-workflow-stage' });
            stage.createEl('div', { cls: 'paperforge-workflow-stage-value', text: String(stages[i].value) });
            stage.createEl('div', { cls: 'paperforge-workflow-stage-label', text: stages[i].label });
            if (i < stages.length - 1) {
                funnel.createEl('div', { cls: 'paperforge-workflow-arrow', text: '\u2192' });
            }
        }

        // ── OCR Pipeline (scoped to this base) ──
        if (ocrPending + ocrProcessing + ocrDone + ocrFailed > 0) {
            const ocrSection = view.createEl('div', { cls: 'paperforge-ocr-section' });
            const ocrHeader = ocrSection.createEl('div', { cls: 'paperforge-collection-ocr-header' });
            ocrHeader.createEl('h4', { cls: 'paperforge-ocr-title', text: 'OCR Pipeline' });
            const ocrBadge = ocrHeader.createEl('span', { cls: 'paperforge-ocr-badge idle' });
            if (ocrProcessing > 0) { ocrBadge.addClass('active'); ocrBadge.setText('Processing'); }
            else if (ocrPending > 0) ocrBadge.setText('Pending');
            else { ocrBadge.addClass('idle'); ocrBadge.setText('Idle'); }

            const ocrTrack = ocrSection.createEl('div', { cls: 'paperforge-progress-track' });
            if (ocrProcessing > 0) ocrTrack.addClass('paperforge-processing');
            const totalOcr = ocrPending + ocrProcessing + ocrDone + ocrFailed;
            const ocrSegs = [
                { cls: 'pending', count: ocrPending },
                { cls: 'active', count: ocrProcessing },
                { cls: 'done', count: ocrDone },
                { cls: 'failed', count: ocrFailed },
            ];
            for (const s of ocrSegs) {
                if (s.count > 0) {
                    const pct = (s.count / totalOcr * 100).toFixed(1);
                    ocrTrack.createEl('div', { cls: `paperforge-progress-seg ${s.cls}`, attr: { style: `width:${pct}%` } });
                }
            }

            const ocrCounts = ocrSection.createEl('div', { cls: 'paperforge-ocr-counts' });
            const ocrLabels = [
                { cls: 'pending', value: ocrPending, label: 'Pending' },
                { cls: 'active', value: ocrProcessing, label: 'Processing' },
                { cls: 'done', value: ocrDone, label: 'Done' },
                { cls: 'failed', value: ocrFailed, label: 'Attention' },
            ];
            for (const l of ocrLabels) {
                const cnt = ocrCounts.createEl('div', { cls: 'paperforge-ocr-count' });
                cnt.createEl('div', { cls: 'paperforge-ocr-count-value', text: l.value.toString() });
                cnt.createEl('div', { cls: 'paperforge-ocr-count-label', text: l.label });
            }
        }

        // ── Contextual Actions ──
        const actionsRow = view.createEl('div', { cls: 'paperforge-collection-actions' });
        const ocrActionBtn = actionsRow.createEl('button', { cls: 'paperforge-contextual-btn primary' });
        ocrActionBtn.createEl('span', { cls: 'paperforge-contextual-btn-icon', text: '\u229E' });
        ocrActionBtn.createEl('span', { text: 'Run OCR' });
        ocrActionBtn.addEventListener('click', () => {
            const action = ACTIONS.find(a => a.id === 'paperforge-ocr');
            if (action) this._runAction(action, ocrActionBtn);
        });

        const syncBtn = actionsRow.createEl('button', { cls: 'paperforge-contextual-btn' });
        syncBtn.createEl('span', { cls: 'paperforge-contextual-btn-icon', text: '\u21BB' });
        syncBtn.createEl('span', { text: 'Sync Library' });
        syncBtn.addEventListener('click', () => {
            const action = ACTIONS.find(a => a.id === 'paperforge-sync');
            if (action) this._runAction(action, syncBtn);
        });
    }

    /* ── Refresh current mode (called on index change, D-09, REFR-01) ── */
    _refreshCurrentMode() {
        if (!this._currentMode) return;
        this._contentEl.empty();
        this._contentEl.addClass('switching');
        this._invalidateIndex();
        this._currentPaperEntry = this._currentPaperKey ? this._findEntry(this._currentPaperKey) : null;

        this._renderModeHeader(this._currentMode);

        try {
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
        } finally {
            // Always remove switching, even if render throws
            setTimeout(() => {
                if (this._contentEl) this._contentEl.removeClass('switching');
            }, 50);
        }
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
                if (clean) { log.push(clean); this._showMessage(log.slice(-8).join('\n'), 'running'); new Notice(clean, 5000); }
            }
        });
        child.stderr.on('data', (data) => {
            const lines = data.toString('utf-8').split('\n').filter(Boolean);
            for (const l of lines) {
                if (l.includes('\r') || l.includes('%') || l.includes('\u2588')) continue;
                const trim = l.trim();
                if (trim && !trim.match(/^\d+%|^\|/)) { log.push(trim); this._showMessage(log.slice(-8).join('\n'), 'running'); new Notice(trim, 5000); }
            }
        });
        child.on('close', (code) => {
            clearInterval(pollTimer);
            card.removeClass('running');
            const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
            if (code !== 0) {
                const last = log.slice(-3).join(' | ') || 'exit code ' + code;
                if ((a.cmd === 'repair' || a.cmd === 'ocr') && code === 1) {
                    this._showMessage('[WARN] ' + last, 'running');
                    new Notice('[WARN] ' + a.cmd + ' partial: ' + last, 8000);
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
                if (this._contentEl) this._contentEl.removeClass('switching');
                this._cachedStats = null;
                this._fetchStats();
            }
        });
        child.on('error', (err) => {
            card.removeClass('running');
            if (this._contentEl) this._contentEl.removeClass('switching');
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
                const resolved = this._resolveModeForFile(this.app.workspace.getActiveFile());
                const nextMode = resolved.mode;
                const nextFilePath = resolved.filePath;

                // Clicking inside the dashboard can activate its leaf without changing
                // the underlying paper/base context. Avoid rebuilding the whole mode
                // tree in that case, or transient UI state like discussion expansion resets.
                if (this._currentMode === nextMode && this._currentFilePath === nextFilePath) {
                    return;
                }

                this._detectAndSwitch();
            }, 300);
        });
        this._modeSubscribers.push({ event: 'active-leaf-change', ref: leafHandler });

        // D-09: File modification -- formal-library.json only (deep-finalize signals completion)
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
        this._lastSyncTime = null;
        this._memoryStatusText = null;   // null = not checked yet, string = cached result
        this._vectorDepsOk = null;       // null = not checked, bool = cached
        this._embedStatusText = null;
        this._skillsCollapsed = { user: true };  // User skills collapsed by default
        this.activeTab = 'setup';
    }

    /** Reload path config from paperforge.json */
    _refreshPfConfig() {
        this._pfConfig = this.plugin.readPaperforgeJson();
    }

    display() {
        const { containerEl } = this;
        containerEl.empty();
        this._refreshPfConfig();

        // Inject tab CSS once
        if (!document.getElementById('paperforge-tab-styles')) {
            const style = document.createElement('style');
            style.id = 'paperforge-tab-styles';
            style.textContent = `
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
            `;
            document.head.appendChild(style);
        }

        // --- Tab bar ---
        const tabBar = containerEl.createDiv({ cls: 'paperforge-settings-tabs' });
        const tabs = [
            { id: 'setup', label: t('tab_setup') || 'Installation' },
            { id: 'features', label: t('tab_features') || 'Features' },
        ];
        const tabContents = {};

        tabs.forEach(tab => {
            const btn = tabBar.createEl('button', {
                cls: 'paperforge-settings-tab' + (tab.id === this.activeTab ? ' paperforge-settings-tab--active' : ''),
                text: tab.label,
            });
            btn.addEventListener('click', () => {
                this.activeTab = tab.id;
                this.display(); // re-render with new active tab
            });
        });

        // --- Tab content containers ---
        tabs.forEach(tab => {
            tabContents[tab.id] = containerEl.createDiv({
                cls: 'paperforge-tab-content' + (tab.id === this.activeTab ? ' paperforge-tab-content--active' : ''),
            });
        });

        // --- Render active tab ---
        if (this.activeTab === 'setup') {
            this._renderSetupTab(tabContents.setup);
        } else {
            this._renderFeaturesTab(tabContents.features);
        }
    }

    _renderSetupTab(containerEl) {
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
                const setupDone = this.plugin.settings.setup_complete;
                const pyVer = (!err && stdout) ? stdout.trim() : null;
                const descText = pyVer
                    ? `${t('runtime_health_plugin_ver').replace('{0}', pluginVer)} → ${t('runtime_health_package_ver').replace('{0}', pyVer)}`
                    : (setupDone ? `Plugin v${pluginVer} → Python package not installed. Click "Sync Runtime" to install.`
                       : `Plugin v${pluginVer} → Not configured. Please open the setup wizard first.`);
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
                    badgeEl.setText(setupDone ? 'Not installed' : 'Setup needed');
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

    _execMemoryStatus(pythonPath, vp, callback) {
        const { exec } = require('child_process');
        exec(`"${pythonPath}" -m paperforge --vault "${vp}" memory status --json`, { encoding: 'utf-8', timeout: 15000 }, (err, stdout) => {
            if (err) { callback('Status unavailable'); return; }
            try {
                const data = JSON.parse(stdout);
                if (data.ok) {
                    const s = data.data;
                    const freshness = s.fresh ? 'fresh' : 'stale';
                    callback(`Papers: ${s.paper_count_db} | ${freshness}${s.needs_rebuild ? ' - needs rebuild' : ''}`);
                } else {
                    callback('DB not found. Run paperforge memory build.');
                }
            } catch(e) { callback('Could not parse status.'); }
        });
    }

    _execEmbedStatus(pythonPath, vp, callback) {
        const { exec } = require('child_process');
        exec(`"${pythonPath}" -m paperforge --vault "${vp}" embed status --json`, { encoding: 'utf-8', timeout: 15000 }, (err, stdout) => {
            if (err) { callback('Status unavailable'); return; }
            try {
                const data = JSON.parse(stdout);
                if (data.ok) {
                    callback(`Chunks: ${data.data.chunk_count} | ${data.data.model} | ${data.data.mode}`);
                } else {
                    callback('Could not parse status.');
                }
            } catch(e) { callback('Could not parse status.'); }
        });
    }

    _renderMemoryStatusText(el, text, extraInfo) {
        el.innerHTML = '';
        el.createEl('span', { text: text, cls: 'paperforge-memory-text' }).style.cssText = 'flex:1;';

        if (extraInfo === 'syncing') {
            const syncEl = el.createEl('span', { text: 'Syncing...', cls: 'paperforge-sync-status' });
            syncEl.style.cssText = 'opacity:0.7; margin-right:8px;';
        } else if (extraInfo) {
            const timeEl = el.createEl('span', { text: extraInfo, cls: 'paperforge-sync-status' });
            timeEl.style.cssText = 'opacity:0.7; margin-right:8px;';
        }

        const refreshBtn = el.createEl('button', { cls: 'paperforge-refresh-btn', text: '\u21BB' });
        refreshBtn.style.cssText = 'margin-left:auto; border:none; background:none; cursor:pointer; font-size:16px; padding:0 4px;';
        refreshBtn.title = 'Sync now';
        refreshBtn.onclick = () => {
            this._memoryStatusText = null;
            this._runManualSync();
        };
    }

    _getBuildCommand(settings) {
        const vp = this.app.vault.adapter.basePath;
        const pyResult = resolvePythonExecutable(vp, settings);
        if (!pyResult.path) return null;
        return `"${pyResult.path}" -m paperforge --vault "${vp}" sync`;
    }

    _runManualSync() {
        const vp = this.app.vault.adapter.basePath;
        const pyResult = resolvePythonExecutable(vp, this.plugin.settings);
        if (!pyResult.path) return;

        const statusRow = document.querySelector('.paperforge-memory-status');
        if (statusRow) {
            this._renderMemoryStatusText(statusRow, 'Checking...', 'syncing');
        }

        this.plugin._autoSyncRunning = true;
        const { exec } = require('child_process');
        exec(`"${pyResult.path}" -m paperforge --vault "${vp}" sync`, { timeout: 120000, encoding: 'utf-8' }, (err) => {
            this.plugin._autoSyncRunning = false;
            this._memoryStatusText = null;
            if (!err) {
                this._lastSyncTime = new Date().toLocaleTimeString();
                this.plugin._lastSyncTime = this._lastSyncTime;
            }
            this.display(); // re-render
        });
    }

    _renderFeaturesTab(containerEl) {
        // --- Section: Skills ---
        containerEl.createEl('h3', { text: 'Skills' });
        const skillsDescEl = containerEl.createEl('div', { cls: 'paperforge-desc-box' });
        skillsDescEl.style.cssText = 'padding:8px 12px; margin:0 0 12px; background:var(--background-secondary); border-radius:4px; font-size:12px; color:var(--text-muted); line-height:1.5;';
        skillsDescEl.setText(t('feat_skills_desc'));
        skillsDescEl.createEl('br');
        skillsDescEl.createEl('span', { text: t('feat_skills_system'), cls: '' }).style.opacity = '0.7';

        // Agent platform selector
        const agentPlatforms = {
            'opencode': 'OpenCode',
            'claude': 'Claude Code',
            'codex': 'Codex',
            'cursor': 'Cursor',
            'windsurf': 'Windsurf',
            'github_copilot': 'GitHub Copilot',
        };
        const agentDirs = {
            'opencode': '.opencode/skills',
            'claude': '.claude/skills',
            'codex': '.codex/skills',
            'cursor': '.cursor/skills',
            'windsurf': '.windsurf/skills',
            'github_copilot': '.github/skills',
        };

        const vaultPath = this.app.vault.adapter.basePath;
        const fs = require('fs');
        const path = require('path');

        let selectedPlatform = this.plugin.settings.selected_skill_platform || 'opencode';

        new Setting(containerEl)
            .setName(t('feat_agent_platform'))
            .setDesc(t('feat_agent_platform_desc'))
            .addDropdown(dropdown => {
                Object.entries(agentPlatforms).forEach(([key, label]) => dropdown.addOption(key, label));
                dropdown.setValue(selectedPlatform)
                    .onChange(value => {
                        this.plugin.settings.selected_skill_platform = value;
                        this.plugin.saveSettings();
                        this.display();
                    });
            })
            .addExtraButton(btn => {
                btn.setIcon('folder')
                    .setTooltip('Open skills folder')
                    .onClick(() => {
                        const dir = agentDirs[selectedPlatform] || '.opencode/skills';
                        const fullPath = path.join(vaultPath, dir);
                        if (fs.existsSync(fullPath)) {
                            const { exec } = require('child_process');
                            exec(`start "" "${fullPath}"`);
                        } else {
                            new Notice(`Skills folder not found: ${dir}`);
                        }
                    });
            });

        // Show skills for selected platform
        const skillDir = path.join(vaultPath, agentDirs[selectedPlatform]);
        let systemSkills = [];
        let userSkills = [];

        if (fs.existsSync(skillDir)) {
            fs.readdirSync(skillDir, { withFileTypes: true }).forEach(entry => {
                if (!entry.isDirectory()) return;
                const skillFile = path.join(skillDir, entry.name, 'SKILL.md');
                if (!fs.existsSync(skillFile)) return;
                const content = fs.readFileSync(skillFile, 'utf-8');
                const nameMatch = content.match(/^name:\s*(.+)$/m);
                const lines = content.split('\n');
                const descIdx = lines.findIndex(l => /^description:/.test(l));
                let desc = '';
                if (descIdx >= 0) {
                    const first = lines[descIdx].match(/^description:\s*(.+)$/);
                    if (first && first[1] && first[1] !== '>' && first[1] !== '|-' && first[1] !== '|') {
                        desc = first[1].trim();
                    } else {
                        for (let i = descIdx + 1; i < lines.length; i++) {
                            if (/^\s{2,}/.test(lines[i]) || lines[i].trim() === '') {
                                desc += lines[i].trim() + ' ';
                            } else break;
                        }
                        desc = desc.trim();
                    }
                }
                const sourceMatch = content.match(/^source:\s*(.+)$/m);
                const disableMatch = content.match(/^disable-model-invocation:\s*(.+)$/m);
                const versionMatch = content.match(/^version:\s*(.+)$/m);

                const skill = {
                    name: nameMatch ? nameMatch[1].trim() : entry.name,
                    desc: desc,
                    source: sourceMatch ? sourceMatch[1].trim() : 'user',
                    disabled: disableMatch && disableMatch[1].trim() === 'true',
                    version: versionMatch ? versionMatch[1].trim() : '',
                    path: skillFile,
                    content: content,
                    dirName: entry.name,
                };

                if (skill.source === 'paperforge') {
                    systemSkills.push(skill);
                } else {
                    userSkills.push(skill);
                }
            });
        }

        const skillsBox = containerEl.createEl('div');
        skillsBox.style.cssText = 'background:var(--background-secondary); border-radius:8px; padding:12px 12px 10px; margin:8px 0 16px;';

        const renderCollapsibleSkills = (label, skills, isSystem) => {
            if (skills.length === 0) return;

            // Group wrapper for spacing between groups
            const group = skillsBox.createEl('div', { cls: 'paperforge-skills-group' });

            // Header row with toggle arrow (created first so it appears above content)
            const header = group.createEl('div', { cls: 'paperforge-skills-collapse-header' });

            // Content wrapper
            const content = group.createEl('div', { cls: 'paperforge-skills-collapse-content' });
            const arrow = header.createEl('span', { text: '\u25BC', cls: 'paperforge-skills-arrow' });
            arrow.style.cssText = 'display:inline-block; font-size:10px; margin-right:6px; transition:transform 0.2s; transform:rotate(0deg);';
            header.createEl('h4', { text: `${label} (${skills.length})`, cls: 'paperforge-skills-subheader' });

            skills.forEach(s => {
                const nameText = s.name + (s.version ? ' v' + s.version : '');
                const sourceLabel = isSystem ? ' [system]' : ' [user]';
                const descText = s.desc || '';

                const setting = new Setting(content)
                    .setName(nameText + sourceLabel)
                    .setDesc(descText);
                setting.settingEl.style.opacity = s.disabled ? '0.4' : '1';

                setting.addToggle(toggle => {
                    toggle.setValue(!s.disabled)
                        .onChange(value => {
                            const newDisabled = !value;
                            const disableMatch = s.content.match(/^disable-model-invocation:\s*(.+)$/m);
                            const newContent = disableMatch
                                ? s.content.replace(/^disable-model-invocation:\s*.+$/m, `disable-model-invocation: ${newDisabled}`)
                                : s.content.replace(/^(---\r?\n)/, `$1disable-model-invocation: ${newDisabled}\n`);
                            fs.writeFileSync(s.path, newContent, 'utf-8');
                            s.disabled = newDisabled;
                            s.content = newContent;
                            setting.settingEl.style.opacity = s.disabled ? '0.4' : '1';
                        });
                });
            });

            // Toggle with state preservation
            const stateKey = isSystem ? 'system' : 'user';
            const collapsed = this._skillsCollapsed[stateKey] || false;
            if (collapsed) {
                content.style.display = 'none';
                arrow.style.transform = 'rotate(-90deg)';
            }

            header.addEventListener('click', () => {
                const nowCollapsed = content.style.display !== 'none';
                if (nowCollapsed) {
                    content.style.display = 'none';
                    arrow.style.transform = 'rotate(-90deg)';
                } else {
                    content.style.display = '';
                    arrow.style.transform = 'rotate(0deg)';
                }
                this._skillsCollapsed[stateKey] = content.style.display === 'none';
            });
        };

        // System skills
        renderCollapsibleSkills('System Skills', systemSkills, true);

        // User skills
        renderCollapsibleSkills('User Skills', userSkills, false);

        if (systemSkills.length === 0 && userSkills.length === 0) {
            skillsBox.createEl('p', {
                text: `No skills found in ${agentDirs[selectedPlatform]}. Run setup to deploy skills.`,
                cls: 'setting-item-description'
            });
        }

        // --- Section: Memory Layer ---
        containerEl.createEl('h3', { text: 'Memory Layer' });

        const memoryDescEl = containerEl.createEl('div', { cls: 'paperforge-desc-box' });
        memoryDescEl.style.cssText = 'padding:8px 12px; margin:0 0 12px; background:var(--background-secondary); border-radius:4px; font-size:12px; color:var(--text-muted); line-height:1.5;';
        memoryDescEl.setText(t('feat_memory_desc'));

        // Always-on SQLite status display
        const statusRow = containerEl.createEl('div', { cls: 'paperforge-memory-status' });
        statusRow.style.cssText = 'display:flex; align-items:center; padding:8px 12px; margin:8px 0; background:var(--background-secondary); border-radius:4px;';

        const vp = this.app.vault.adapter.basePath;
        const pyResult = resolvePythonExecutable(vp, this.plugin.settings);

        if (this.plugin._lastSyncTime && !this._lastSyncTime) {
            this._lastSyncTime = this.plugin._lastSyncTime;
        }

        if (this._memoryStatusText !== null) {
            this._renderMemoryStatusText(statusRow, this._memoryStatusText, this._lastSyncTime);
        } else if (pyResult.path) {
            this._renderMemoryStatusText(statusRow, 'Checking...', this._lastSyncTime);
            this._execMemoryStatus(pyResult.path, vp, (text) => {
                this._memoryStatusText = text;
                this._renderMemoryStatusText(statusRow, text, this._lastSyncTime);
            });
        } else {
            this._renderMemoryStatusText(statusRow, 'No Python found.', this._lastSyncTime);
        }

        this._renderVectorSection(containerEl);
    }

    _renderVectorSection(containerEl) {
        // --- Vector Database (within Memory Layer) ---
        containerEl.createEl('h4', { text: 'Vector Database' });

        const vecDescEl = containerEl.createEl('div', { cls: 'paperforge-desc-box' });
        vecDescEl.style.cssText = 'padding:8px 12px; margin:0 0 8px; background:var(--background-secondary); border-radius:4px; font-size:12px; color:var(--text-muted); line-height:1.5;';
        vecDescEl.setText(t('feat_vector_desc'));

        new Setting(containerEl)
            .setName(t('feat_vector_enable'))
            .setDesc(t('feat_vector_enable_desc'))
            .addToggle(toggle => {
                toggle.setValue(this.plugin.settings.features.vector_db)
                    .onChange(value => {
                        this.plugin.settings.features.vector_db = value;
                        this.plugin.saveSettings();
                        this._vectorDepsOk = null;
                        this._embedStatusText = null;
                        this.display();
                    });
            });

        if (!this.plugin.settings.features.vector_db) return;

        const vp = this.app.vault.adapter.basePath;

        // Collapsible config section
        const vecConfigHeader = containerEl.createEl('div', { cls: 'paperforge-skills-collapse-header' });
        vecConfigHeader.style.cssText = 'display:flex; align-items:center; cursor:pointer; padding:6px 0 2px; margin:0;';
        const vecArrow = vecConfigHeader.createEl('span', { text: '\u25BC' });
        vecArrow.style.cssText = 'display:inline-block; font-size:10px; margin-right:6px; transition:transform 0.2s;';
        vecConfigHeader.createEl('span', { text: t('feat_vector_config_label'), cls: '' }).style.cssText = 'font-size:12px; color:var(--text-muted);';
        const vecConfigContent = containerEl.createEl('div', { cls: 'paperforge-vector-config' });

        let vecConfigCollapsed = false;
        vecConfigHeader.addEventListener('click', () => {
            vecConfigCollapsed = !vecConfigCollapsed;
            vecConfigContent.style.display = vecConfigCollapsed ? 'none' : '';
            vecArrow.style.transform = vecConfigCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)';
        });

        // === Resolve state ===
        if (this._vectorDepsOk === true && this._embedStatusText !== null) {
            this._renderVectorReady(vecConfigContent, vp);
            return;
        }
        if (this._vectorDepsOk === false) {
            this._renderVectorNoDeps(vecConfigContent);
            return;
        }
        // First check — deps unknown, run async
        if (this._vectorDepsOk === null) {
            const statusBox = vecConfigContent.createEl('div');
            statusBox.style.cssText = 'padding:8px 12px; margin:8px 0; background:var(--background-secondary); border-radius:4px;';
            statusBox.setText(t('feat_deps_checking'));

            const pyResult = resolvePythonExecutable(vp, this.plugin.settings);
            if (!pyResult.path) {
                statusBox.setText(t('feat_no_python'));
                this._vectorDepsOk = false;
                return;
            }
            const { exec } = require('child_process');
            exec(`"${pyResult.path}" -c "import chromadb; import sentence_transformers; import openai; print('ok')"`, {
                encoding: 'utf-8', timeout: 15000
            }, (err, stdout) => {
                const ok = !err && (stdout || '').trim() === 'ok';
                this._vectorDepsOk = ok;
                if (ok) {
                    // Deps OK — now check embed status
                    this._execEmbedStatus(pyResult.path, vp, (statusText) => {
                        this._embedStatusText = statusText;
                        this.display();
                    });
                } else {
                    this.display();
                }
            });
        }
    }

    _renderHfMirror(containerEl) {
        const setting = new Setting(containerEl)
            .setName(t('feat_hf_mirror'))
            .setDesc(t('feat_hf_mirror_desc'))
            .addDropdown(dropdown => {
                dropdown.addOption('https://hf-mirror.com', 'hf-mirror.com (recommended)');
                dropdown.addOption('https://huggingface.co', 'huggingface.co (official)');
                dropdown.addOption('__custom__', 'Custom...');
                const current = this.plugin.settings.vector_db_hf_endpoint || 'https://hf-mirror.com';
                const isPreset = ['https://hf-mirror.com', 'https://huggingface.co'].includes(current);
                dropdown.setValue(isPreset ? current : '__custom__')
                    .onChange(value => {
                        if (value !== '__custom__') {
                            this.plugin.settings.vector_db_hf_endpoint = value;
                            this.plugin.saveSettings();
                            if (customInput) { customInput.settingEl.style.display = 'none'; if (this._hfCustomText) this._hfCustomText.setValue(''); }
                        } else {
                            if (customInput) customInput.settingEl.style.display = '';
                        }
                    });
            });
        const customInput = new Setting(containerEl)
            .setName(t('feat_custom_endpoint'))
            .setDesc(t('feat_custom_endpoint_desc'))
            .addText(text => {
                this._hfCustomText = text;
                const current = this.plugin.settings.vector_db_hf_endpoint || '';
                const isPreset = ['https://hf-mirror.com', 'https://huggingface.co'].includes(current);
                text.setPlaceholder('https://your-mirror.com')
                    .setValue(isPreset ? '' : current)
                    .onChange(value => {
                        this.plugin.settings.vector_db_hf_endpoint = value;
                        this.plugin.saveSettings();
                    });
            });
        const current = this.plugin.settings.vector_db_hf_endpoint || 'https://hf-mirror.com';
        const isPreset = ['https://hf-mirror.com', 'https://huggingface.co'].includes(current);
        if (isPreset) customInput.settingEl.style.display = 'none';

        new Setting(containerEl)
            .setName(t('feat_hf_token'))
            .setDesc(t('feat_hf_token_desc'))
            .addText(text => {
                text.setPlaceholder('hf_...')
                    .setValue(this.plugin.settings.vector_db_hf_token || '')
                    .onChange(value => {
                        this.plugin.settings.vector_db_hf_token = value;
                        this.plugin.saveSettings();
                    });
            });
    }

    _renderApiConfig(containerEl) {
        if (this.plugin.settings.vector_db_mode !== 'api') return;

        new Setting(containerEl)
            .setName(t('feat_openai_key'))
            .setDesc(t('feat_openai_key_desc'))
            .addText(text => {
                text.setPlaceholder('sk-...')
                    .setValue(this.plugin.settings.vector_db_api_key || '')
                    .onChange(value => {
                        this.plugin.settings.vector_db_api_key = value;
                        this.plugin.saveSettings();
                    });
            });
        new Setting(containerEl)
            .setName(t('feat_api_base_url'))
            .setDesc(t('feat_api_base_url_desc'))
            .addText(text => {
                text.setPlaceholder('https://api.openai.com/v1')
                    .setValue(this.plugin.settings.vector_db_api_base || '')
                    .onChange(value => {
                        this.plugin.settings.vector_db_api_base = value;
                        this.plugin.saveSettings();
                    });
            });
        new Setting(containerEl)
            .setName(t('feat_api_model'))
            .setDesc(t('feat_api_model_desc'))
            .addText(text => {
                text.setPlaceholder('text-embedding-3-small')
                    .setValue(this.plugin.settings.vector_db_api_model || 'text-embedding-3-small')
                    .onChange(value => {
                        this.plugin.settings.vector_db_api_model = value;
                        this.plugin.saveSettings();
                    });
            });
    }

    _renderVectorNoDeps(containerEl) {
        const box = containerEl.createEl('div');
        box.style.cssText = 'padding:8px 12px; margin:8px 0; background:var(--background-secondary); border-radius:4px;';
        box.setText(t('feat_deps_missing'));

        new Setting(containerEl)
            .setName(t('feat_install_deps'))
            .setDesc(t('feat_install_deps_desc'))
            .addButton(button => {
                button.setButtonText(t('feat_install_btn'))
                    .setCta()
                    .onClick(async () => {
                        const vp = this.app.vault.adapter.basePath;
                        const pyResult = resolvePythonExecutable(vp, this.plugin.settings);
                        if (!pyResult.path) { new Notice('No Python found.'); return; }
                        button.setButtonText(t('feat_installing'));
                            button.setDisabled(true);
                            const notice = new Notice('Installing chromadb + sentence-transformers + openai...', 0);
                        try {
                            const { exec } = require('child_process');
        const env = Object.assign({}, process.env, { PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1', HF_ENDPOINT: this.plugin.settings.vector_db_hf_endpoint || 'https://hf-mirror.com', HF_TOKEN: this.plugin.settings.vector_db_hf_token || '' });
                            await new Promise((resolve, reject) => {
                                exec(`"${pyResult.path}" -m pip install chromadb sentence-transformers openai`, {
                                    encoding: 'utf-8', timeout: 300000, env: env,
                                }, (error) => { error ? reject(error) : resolve(); });
                            });
                            notice.hide();
                            new Notice('Dependencies installed. Building vectors...');
                            // Auto-build after install
                            this._vectorDepsOk = true;
                            this._execEmbedStatus(pyResult.path, vp, (text) => {
                                this._embedStatusText = text;
                            });
                            this.display();
                        } catch (e) {
                            notice.hide();
                            new Notice('Install failed: ' + (e.stderr || e.message || e));
                            button.setButtonText(t('feat_retry_btn'));
                            button.setDisabled(false);
                        }
                    });
            });
    }

    _renderVectorReady(containerEl, vp) {
        // Status line
        const statusEl = containerEl.createEl('div');
        statusEl.style.cssText = 'padding:8px 12px; margin:8px 0; background:var(--background-secondary); border-radius:4px;';
        statusEl.setText(this._embedStatusText || 'Loading...');

        // Detect model mismatch
        const embedInfo = this._embedStatusText ? this._parseEmbedStatus(this._embedStatusText) : null;
        const currentModel = this._getCurrentModelKey();
        const lastModel = this.plugin.settings.vector_db_last_model || '';
        const modelChanged = embedInfo && embedInfo.db_exists && lastModel && lastModel !== currentModel;

        if (modelChanged) {
            const warnEl = containerEl.createEl('div');
            warnEl.style.cssText = 'padding:8px 12px; margin:8px 0; background:var(--background-modifier-warning); border-radius:4px;';
            warnEl.setText(`Model changed (${lastModel} -> ${currentModel}). Existing vectors are incompatible — rebuild required.`);
        }

        // Mode selector
        new Setting(containerEl)
            .setName(t('feat_embed_mode'))
            .addDropdown(dropdown => {
                dropdown.addOption('local', t('feat_embed_mode_local'));
                dropdown.addOption('api', t('feat_embed_mode_api'));
                dropdown.setValue(this.plugin.settings.vector_db_mode)
                    .onChange(value => {
                        this.plugin.settings.vector_db_mode = value;
                        this.plugin.saveSettings();
                        this.display();
                    });
            });

        // Model selector (local mode)
        if (this.plugin.settings.vector_db_mode === 'local') {
            // HF settings only relevant for local model downloads
            this._renderHfMirror(containerEl);
            const modelDesc = {
                'BAAI/bge-small-en-v1.5': t('feat_model_bge_small'),
                'sentence-transformers/all-MiniLM-L6-v2': t('feat_model_minilm'),
                'BAAI/bge-base-en-v1.5': t('feat_model_bge_base'),
            };
            new Setting(containerEl)
                .setName(t('feat_model'))
                .setDesc(modelDesc[this.plugin.settings.vector_db_model] || '')
                .addDropdown(dropdown => {
                    dropdown.addOption('BAAI/bge-small-en-v1.5', 'bge-small (384d, 130MB)');
                    dropdown.addOption('sentence-transformers/all-MiniLM-L6-v2', 'MiniLM (384d, 80MB)');
                    dropdown.addOption('BAAI/bge-base-en-v1.5', 'bge-base (768d, 440MB)');
                    dropdown.setValue(this.plugin.settings.vector_db_model)
                        .onChange(value => {
                            this.plugin.settings.vector_db_model = value;
                            this.plugin.saveSettings();
                            this.display();
                        });
                })
                .addButton(button => {
                    const model = this.plugin.settings.vector_db_model;
                    const cacheName = 'models--' + model.replace('/', '--');
                    const fs = require('fs');
                    const os = require('os');
                    const path = require('path');
                    const cachePath = path.join(os.homedir(), '.cache', 'huggingface', 'hub', cacheName);

                    // Check integrity: directory exists AND has snapshots with files
                    let isCached = false;
                    if (fs.existsSync(cachePath)) {
                        const snapDir = path.join(cachePath, 'snapshots');
                        if (fs.existsSync(snapDir)) {
                            try {
                                const entries = fs.readdirSync(snapDir);
                                isCached = entries.some(e => {
                                    const p = path.join(snapDir, e);
                                    return fs.statSync(p).isDirectory() && fs.readdirSync(p).length > 0;
                                });
                            } catch (_) {}
                        }
                    }

                    if (isCached) {
                        button.setButtonText(t('feat_uninstall_btn')).setWarning();
                    } else {
                        button.setButtonText(t('feat_not_cached'));
                        button.setDisabled(true);
                    }
                    button.onClick(async () => {
                        if (!isCached) return;
                        button.setButtonText(t('feat_removing'));
                        button.setDisabled(true);
                        try {
                            const pyResult = resolvePythonExecutable(vp, this.plugin.settings);
                            const { exec } = require('child_process');
                            const env = Object.assign({}, process.env, { PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' });
                            await new Promise((resolve, reject) => {
                                exec(`"${pyResult.path}" -c "import shutil, os; p=os.path.join(os.path.expanduser('~/.cache/huggingface/hub'), '${cacheName}'); shutil.rmtree(p,ignore_errors=True); print('done')"`, {
                                    encoding: 'utf-8', timeout: 30000, env: env
                                }, (error) => error ? reject(error) : resolve());
                            });
                            new Notice('Model cache removed.');
                        } catch (e) {
                            new Notice('Failed: ' + (e.stderr || e.message || e));
                        }
                        this.display();
                    });
                });
        }

        // API config (api mode)
        this._renderApiConfig(containerEl);

        // Rebuild button with live terminal output
        const terminalEl = containerEl.createEl('pre');
        terminalEl.style.cssText = 'display:none; background:var(--background-primary); padding:10px; border-radius:4px; border:1px solid var(--background-modifier-border); max-height:250px; overflow-y:auto; font-size:11px; font-family:var(--font-monospace); margin:8px 0; white-space:pre-wrap; word-break:break-all; opacity:0.8;';
        terminalEl.onclick = () => {
            const text = terminalEl.textContent;
            if (text) { navigator.clipboard.writeText(text); new Notice('Output copied to clipboard'); }
        };

        new Setting(containerEl)
            .setName(t('feat_rebuild_vectors'))
            .setDesc(modelChanged ? t('feat_rebuild_vectors_changed') : t('feat_rebuild_vectors_desc'))
            .addButton(button => {
                const label = embedInfo && embedInfo.db_exists ? t('feat_rebuild_btn') : t('feat_build_btn');
                button.setButtonText(label)
                    .setCta()
                    .onClick(async () => {
                        const pyResult = resolvePythonExecutable(vp, this.plugin.settings);
                        if (!pyResult.path) { new Notice(t('feat_no_python')); return; }
                        button.setButtonText(t('feat_building'));
                        button.setDisabled(true);
                        terminalEl.style.display = 'block';
                        terminalEl.setText('');

                        const { spawn } = require('child_process');
                        const env = Object.assign({}, process.env, { PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1', HF_ENDPOINT: this.plugin.settings.vector_db_hf_endpoint || 'https://hf-mirror.com', HF_TOKEN: this.plugin.settings.vector_db_hf_token || '', VECTOR_DB_API_KEY: this.plugin.settings.vector_db_api_key || '', VECTOR_DB_API_BASE: this.plugin.settings.vector_db_api_base || '', VECTOR_DB_API_MODEL: this.plugin.settings.vector_db_api_model || '' });
                        const child = spawn(pyResult.path, ['-m', 'paperforge', '--vault', vp, 'embed', 'build', '--force'], {
                            env: env, stdio: ['ignore', 'pipe', 'pipe']
                        });

                        const append = (text) => {
                            terminalEl.setText((terminalEl.getText() || '') + text);
                            terminalEl.scrollTop = terminalEl.scrollHeight;
                        };

                        child.stdout.on('data', (data) => append(data.toString()));
                        child.stderr.on('data', (data) => append(data.toString()));

                        try {
                            await new Promise((resolve, reject) => {
                                child.on('close', (code) => code === 0 ? resolve() : reject(new Error('Exit code ' + code)));
                                child.on('error', reject);
                            });
                            this.plugin.settings.vector_db_last_model = currentModel;
                            this.plugin.saveSettings();
                            this._embedStatusText = null;
                            this._execEmbedStatus(pyResult.path, vp, (text) => { this._embedStatusText = text; this.display(); });
                            new Notice(t('feat_build_complete'));
                        } catch (e) {
                            append('\n--- BUILD FAILED ---\n' + (e.stderr || e.message || e));
                            new Notice(t('feat_build_failed'));
                            button.setButtonText(label);
                            button.setDisabled(false);
                        }
                    });
            });
    }

    _getCurrentModelKey() {
        if (this.plugin.settings.vector_db_mode === 'api') return this.plugin.settings.vector_db_api_model || 'openai/text-embedding-3-small';
        return this.plugin.settings.vector_db_model || 'BAAI/bge-small-en-v1.5';
    }

    _parseEmbedStatus(text) {
        // Parse "  key: value" lines from paperforge embed status output
        const info = {};
        if (!text) return info;
        text.split('\n').forEach(line => {
            const m = line.match(/^\s*([^:]+):\s*(.*)/);
            if (m) info[m[1].trim()] = m[2].trim();
        });
        // Normalize bools
        if (info.db_exists !== undefined) info.db_exists = info.db_exists === 'True';
        if (info.chunk_count !== undefined) info.chunk_count = parseInt(info.chunk_count, 10) || 0;
        return info;
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
        const ver = this.plugin.manifest.version;
        const installCmd = buildRuntimeInstallCommand(pythonExe, ver, extraArgs);

        btn.setDisabled(true);
        btn.setButtonText(t('runtime_health_syncing'));

        const tryInstall = (args, label) => {
            console.log(`[PaperForge] Sync Runtime: trying ${label}`);
            return runSubprocess(installCmd.cmd, args, vp, installCmd.timeout, undefined, paperforgeEnrichedEnv());
        };

        const deploySkills = () => {
            let agentKey = 'opencode';
            try {
                const cfgRaw = fs.readFileSync(path.join(vp, 'paperforge.json'), 'utf-8');
                const cfg = JSON.parse(cfgRaw);
                if (cfg.agent_key) agentKey = cfg.agent_key;
            } catch {}
            const { spawn } = require('node:child_process');
            const deployArgs = [...extraArgs, '-c',
                'from paperforge.services.skill_deploy import deploy_skills; ' +
                'from pathlib import Path; ' +
                'r=deploy_skills(vault=Path(r"' + vp.replace(/\\/g, '\\\\') + '"), agent_key="' + agentKey + '", overwrite=True); ' +
                'print("skills deployed" if r["skill_deployed"] else "skills skipped", flush=True)'
            ];
            const child = spawn(pythonExe, deployArgs, { cwd: vp, timeout: 30000, windowsHide: true });
            let out = '';
            child.stdout.on('data', (d) => { out += d.toString('utf-8'); });
            child.on('close', (code) => {
                console.log(`[PaperForge] Skill deploy: ${out.trim()} (exit ${code})`);
            });
        };

        tryInstall(installCmd.pypiArgs, 'PyPI').then((result) => {
            if (result.exitCode === 0) {
                console.log('[PaperForge] Sync Runtime: installed via PyPI');
                deploySkills();
                new Notice(t('runtime_health_sync_done').replace('{0}', ver), 5000);
                this.display();
                return;
            }
            console.warn('[PaperForge] Sync Runtime: PyPI failed, falling back to git...');
            tryInstall(installCmd.gitArgs, 'git').then((r2) => {
                if (r2.exitCode === 0) {
                    console.log('[PaperForge] Sync Runtime: installed via git');
                    deploySkills();
                    new Notice(t('runtime_health_sync_done').replace('{0}', ver), 5000);
                    this.display();
                } else {
                    btn.setDisabled(false);
                    btn.setButtonText(t('runtime_health_sync'));
                    console.error('[PaperForge] git fallback stderr:', r2.stderr);
                    new Notice(t('runtime_health_sync_fail').replace('{0}', 'pip exit code ' + r2.exitCode), 8000);
                }
            });
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
            const home = process.env.HOME || process.env.USERPROFILE || os.homedir() || '';
            if (process.platform === 'darwin') {
                const macZot = [
                    '/Applications/Zotero.app',
                    path.join(home, 'Applications', 'Zotero.app'),
                ];
                zotOk = macZot.some(d => { try { return fs.existsSync(d); } catch { return false; } });
            } else if (process.platform === 'win32') {
                const progFiles = process.env.ProgramFiles || '';
                const localAppData = process.env.LOCALAPPDATA || '';
                const zotInstallDirs = [
                    path.join(progFiles, 'Zotero'),
                    path.join(progFiles, '(x86)', 'Zotero'),
                    path.join(localAppData, 'Programs', 'Zotero'),
                    path.join(localAppData, 'Zotero'),
                    path.join(home, 'AppData', 'Local', 'Programs', 'Zotero'),
                ].filter(Boolean);
                zotOk = zotInstallDirs.some(d => { try { return fs.existsSync(d); } catch { return false; } });
            } else {
                const linuxPaths = [
                    path.join(home, '.local', 'share', 'zotero', 'zotero'),
                    '/usr/bin/zotero',
                    '/usr/local/bin/zotero',
                ];
                zotOk = linuxPaths.some(d => { try { return fs.existsSync(d); } catch { return false; } });
            }
            // Fallback: check if data dir is configured
            const zotDataDir = this.plugin.settings.zotero_data_dir;
            if (!zotOk && zotDataDir) {
                try { zotOk = fs.existsSync(zotDataDir); } catch {}
            }
            results.push({ label: 'Zotero', ok: zotOk, detail: zotOk ? t('check_zotero_ok') : t('check_zotero_fail') });

            /* 3 — Better BibTeX (Profiles-aware scan) */
            let bbtOk = false;
            const appData = process.env.APPDATA || '';
            if (process.platform === 'win32' && appData) {
                bbtOk = scanBbtUnderProfiles(path.join(appData, 'Zotero', 'Zotero', 'Profiles'));
            }
            if (!bbtOk && process.platform === 'darwin' && home) {
                bbtOk = scanBbtUnderProfiles(path.join(home, 'Library', 'Application Support', 'Zotero', 'Profiles'));
            }
            if (!bbtOk && process.platform !== 'win32' && process.platform !== 'darwin' && home) {
                bbtOk = scanBbtUnderProfiles(path.join(home, '.zotero', 'zotero', 'Profiles'));
            }
            if (!bbtOk && zotDataDir && String(zotDataDir).trim()) {
                bbtOk = scanBbtDirectChildren(zotDataDir.trim());
            }
            if (!bbtOk && home) {
                bbtOk = scanBbtDirectChildren(path.join(home, 'Zotero'));
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
                env: paperforgeEnrichedEnv(),
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
            '--base-dir', s.base_dir.trim(),
            '--agent', s.agent_platform || 'opencode',
        ];
        setupArgs.push('--zotero-data', s.zotero_data_dir.trim());
        setupArgs.push('--paddleocr-key', s.paddleocr_api_key.trim());

        try {
            let hasPaperforge = true;
            try {
                await runPython(['-c', 'import paperforge']);
            } catch {
                hasPaperforge = false;
            }

            if (!hasPaperforge) {
                this._log(t('install_bootstrapping'));
                const ver = this.plugin.manifest.version;
                this._log(`[install] Trying PyPI: pip install paperforge==${ver}`);
                const pypiArgs = ['-m', 'pip', 'install', '--upgrade'];
                if (process.platform !== 'win32') pypiArgs.push('--user');
                pypiArgs.push(`paperforge==${ver}`);
                try {
                    await runPython(pypiArgs, { logStdout: true });
                } catch (pypiErr) {
                    this._log(`[install] PyPI failed, falling back to git: git+https://...@v${ver}`);
                    console.warn('[PaperForge] PyPI install failed, falling back to git:', pypiErr.message?.slice(0, 200));
                    const gitArgs = ['-m', 'pip', 'install', '--upgrade'];
                    if (process.platform !== 'win32') gitArgs.push('--user');
                    gitArgs.push(`git+https://github.com/LLLin000/PaperForge.git@v${ver}`);
                    await runPython(gitArgs, { logStdout: true });
                }
            }

            await runPython(setupArgs, {
                logStdout: true,
                env: paperforgeEnrichedEnv(),
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
                let gitDir, resolvedPy;
                try { gitDir = resolveGitDir() || '(not found)'; } catch (_) { gitDir = '(error)'; }
                try { resolvedPy = resolvePythonExecutable(s.vault_path.trim(), this.plugin.settings); } catch (_) { resolvedPy = null; }
                const pathLen = (process.env.PATH || '').length;
                const pathHasGit = (process.env.PATH || '').toLowerCase().includes('git');
                const diagnostic = [
                    '[PaperForge Diagnostic]',
                    'Category: ' + errorMsg,
                    'Plugin version: ' + pluginVer,
                    'Python: ' + pyInfo,
                    'Resolved Python: ' + (resolvedPy?.path || '?'),
                    'OS: ' + osInfo,
                    'Vault path: ' + (s.vault_path || '?'),
                    '--- Git ---',
                    'Git dir (resolved): ' + gitDir,
                    'PATH length: ' + pathLen + ' chars',
                    'PATH contains git: ' + pathHasGit,
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
        if (process.platform === 'darwin' && /No module named ['"]?paperforge/i.test(raw)) {
            return 'PaperForge not installed — install Python from Homebrew or python.org (Apple CLT /Library/Developer/CommandLineTools python often fails); then: python3 -m pip install --user git+https://github.com/LLLin000/PaperForge.git';
        }
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
        // ── Automatic file polling state ──
        this._lastExportMtime = 0;
        this._lastOcrMtimes = {};
        this._autoSyncRunning = false;
        this._lastSyncTime = null;
        this._pollTimer = null;
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


        /* ── Auto-update PaperForge (deferred — don't slow startup) ── */
        if (this.settings.auto_update !== false && this.settings.setup_complete) {
            setTimeout(() => this._autoUpdate(), 3000);
        }
        this._startFilePolling();
    }

    _autoUpdate() {
        const vp = this.app.vault.adapter.basePath;
        const { path: pythonExe, extraArgs = [] } = resolvePythonExecutable(vp, this.settings);
        const ver = this.manifest.version;
        const pypiPkg = `paperforge==${ver}`;
        const gitUrl = `git+https://github.com/LLLin000/PaperForge.git@v${ver}`;

        const doInstall = (pkg, onDone) => {
            const { spawn } = require('node:child_process');
            const child = spawn(pythonExe, [...extraArgs, '-m', 'pip', 'install', '--upgrade', pkg], { cwd: vp, timeout: 120000, env: paperforgeEnrichedEnv() });
            child.on('close', (code) => onDone(code === 0));
        };

        // Check if installed package version matches plugin version
        const { execFile } = require('node:child_process');
        execFile(pythonExe, [...extraArgs, '-c', 'import paperforge; print(paperforge.__version__)'], { cwd: vp, timeout: 10000 }, (err, stdout) => {
            const install = (label) => {
                console.log(`[PaperForge] Auto-update: trying PyPI (paperforge==${ver})`);
                doInstall(pypiPkg, (ok) => {
                    if (ok) { console.log('[PaperForge] Auto-update: installed via PyPI'); new Notice(`[OK] PaperForge CLI ${label}`, 5000); return; }
                    console.warn('[PaperForge] Auto-update: PyPI failed, falling back to git...');
                    doInstall(gitUrl, (ok2) => {
                        if (ok2) { console.log('[PaperForge] Auto-update: installed via git'); new Notice(`[OK] PaperForge CLI ${label} (via git)`, 5000); }
                    });
                });
            };
            if (err) {
                install('installed');
                return;
            }
            const pyVer = stdout.trim();
            if (pyVer !== ver) {
                install(`${pyVer} -> ${ver}`);
            }
        });
    }

    /* ── Automatic file polling for seamless memory layer ── */

    _startFilePolling() {
        const vaultPath = this.app.vault.adapter.basePath;
        const fs = require('fs');
        const path = require('path');
        const { exec } = require('child_process');

        this._pollTimer = setInterval(() => {
            this._checkExports(vaultPath, fs, path, exec);
            this._checkOcr(vaultPath, fs, path, exec);
        }, 120000); // every 120 seconds
    }

    _checkExports(vaultPath, fs, path, exec) {
        if (this._autoSyncRunning) return;
        const exportsDir = path.join(vaultPath, 'System', 'PaperForge', 'exports');
        if (!fs.existsSync(exportsDir)) return;

        let newestMtime = 0;
        try {
            fs.readdirSync(exportsDir).forEach(f => {
                if (!f.endsWith('.json')) return;
                const stat = fs.statSync(path.join(exportsDir, f));
                if (stat.mtimeMs > newestMtime) newestMtime = stat.mtimeMs;
            });
        } catch(e) { return; }

        if (newestMtime > this._lastExportMtime) {
            this._lastExportMtime = newestMtime;
            this._autoSync(vaultPath, exec);
        }
    }

    _autoSync(vaultPath, exec) {
        if (this._autoSyncRunning) return;
        this._autoSyncRunning = true;

        const pyResult = resolvePythonExecutable(vaultPath, this.settings);
        if (!pyResult.path) { this._autoSyncRunning = false; return; }

        const cmd = `"${pyResult.path}" -m paperforge --vault "${vaultPath}" sync`;
        exec(cmd, { timeout: 120000, encoding: 'utf-8' }, (err, stdout, stderr) => {
            this._autoSyncRunning = false;
            this._memoryStatusText = null; // force re-check next time
            if (!err) {
                this._lastSyncTime = new Date().toLocaleTimeString();
            }
            // Update last export mtime to avoid re-trigger during build
            try {
                const fs = require('fs');
                const path = require('path');
                const exportsDir = path.join(vaultPath, 'System', 'PaperForge', 'exports');
                let newest = 0;
                fs.readdirSync(exportsDir).forEach(f => {
                    if (!f.endsWith('.json')) return;
                    newest = Math.max(newest, fs.statSync(path.join(exportsDir, f)).mtimeMs);
                });
                this._lastExportMtime = newest;
            } catch(e) {}
        });
    }

    _checkOcr(vaultPath, fs, path, exec) {
        if (this._autoSyncRunning) return;
        const ocrDir = path.join(vaultPath, 'System', 'PaperForge', 'ocr');
        if (!fs.existsSync(ocrDir)) return;

        try {
            fs.readdirSync(ocrDir, { withFileTypes: true }).forEach(entry => {
                if (!entry.isDirectory()) return;
                const metaPath = path.join(ocrDir, entry.name, 'meta.json');
                if (!fs.existsSync(metaPath)) return;
                const stat = fs.statSync(metaPath);
                const prevMtime = this._lastOcrMtimes[entry.name] || 0;
                if (stat.mtimeMs <= prevMtime) return;

                this._lastOcrMtimes[entry.name] = stat.mtimeMs;
                if (this._autoSyncRunning) return;
                this._autoSyncRunning = true;

                const pyResult = resolvePythonExecutable(vaultPath, this.settings);
                if (!pyResult.path) { this._autoSyncRunning = false; return; }

                const cmd = `"${pyResult.path}" -m paperforge --vault "${vaultPath}" sync --key "${entry.name}"`;
                exec(cmd, { timeout: 30000, encoding: 'utf-8' }, () => {
                    this._autoSyncRunning = false;
                    this._memoryStatusText = null;
                });
            });
        } catch(e) {}
    }

    /**
     * Read path configuration from the canonical paperforge.json file.
     * Falls back to Python-level DEFAULT_CONFIG values if file does not exist.
     * Returns {system_dir, resources_dir, literature_dir, base_dir}.
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
        const validPathKeys = ['system_dir', 'resources_dir', 'literature_dir', 'base_dir'];
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
                this.settings.base_dir = pfConfig.base_dir;
            }
        } catch (e) {
            console.error('PaperForge: Failed to write paperforge.json', e);
            new Notice('PaperForge: Failed to save configuration to paperforge.json');
        }
    }

    onunload() {
        if (this._pollTimer) clearInterval(this._pollTimer);
        this.app.workspace.detachLeavesOfType(VIEW_TYPE_PAPERFORGE);
    }

    async loadSettings() {
        this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
        // Deep-merge nested objects (features, frozen_skills) to avoid overwrite
        if (this.settings.features && DEFAULT_SETTINGS.features) {
            this.settings.features = Object.assign({}, DEFAULT_SETTINGS.features, this.settings.features || {});
        }
        if (!this.settings.frozen_skills) { this.settings.frozen_skills = {}; }
        // Path fields come from paperforge.json, not from DEFAULT_SETTINGS or plugin data.json
        const pfConfig = this.readPaperforgeJson();
        this.settings.system_dir = pfConfig.system_dir;
        this.settings.resources_dir = pfConfig.resources_dir;
        this.settings.literature_dir = pfConfig.literature_dir;
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


