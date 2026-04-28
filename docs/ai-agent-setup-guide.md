# PaperForge Headless Setup — For LLM Agents

> **IMPORTANT**: Read this file directly. Do NOT use WebFetch or summarization — you will lose critical CLI flags and decision logic.

---

## For Humans

**English users** — copy this and paste it to your AI agent:

```
Install PaperForge in this vault by following:
https://raw.githubusercontent.com/LLLin000/PaperForge/master/docs/ai-agent-setup-guide.md
```

**中文用户** — 复制粘贴给 AI：

```
在当前的 vault 里安装 PaperForge。参考下面的文档完成安装：
https://raw.githubusercontent.com/LLLin000/PaperForge/master/docs/ai-agent-setup-guide.md
```
请帮我安装 PaperForge。
参考 https://raw.githubusercontent.com/LLLin000/PaperForge/master/docs/ai-agent-setup-guide.md 完成安装。
```

---

## For LLM Agents

You are installing PaperForge into the user's Obsidian Vault. Follow each step in order. **Do not skip steps.** Report results at each step before proceeding.

### Language

**Detect the user's language from their initial message.** The prompts in this guide are provided in Chinese (for Chinese-speaking users) and English (for English-speaking users). Use the language the user first spoke to you in.

- 用户说中文 → 用中文提问
- User speaks English → use English prompts

All command outputs and technical terms can stay in English — only the conversational prompts need to match the user's language.

---

### Step 0: 收集信息 — 必须先问清楚

**以下所有问题必须在执行任何命令之前问完。不能猜，不能用默认值糊弄。**

**EN**: Ask all questions before running anything. Do not guess.

**Q1: Obsidian Vault 路径 / Vault Path**

中文：
> 你的 Obsidian Vault 的完整绝对路径是什么？
> （如果不知道：打开 Obsidian → 左下角点 vault 名称 → "管理 Vault" → 右键 vault → "在系统文件管理器中显示"。把那个文件夹的完整路径发给我。）

English:
> What is the absolute path to your Obsidian Vault?
> (If you don't know: Open Obsidian → bottom-left vault name → "Manage Vaults" → right-click your vault → "Show in system explorer". Send me the full path.)

**Q2: AI Agent 平台 / Agent Platform**

Show the user this table and wait for one choice:

| Key | Name |
|-----|------|
| `opencode` | OpenCode |
| `cursor` | Cursor |
| `claude` | Claude Code |
| `windsurf` | Windsurf |
| `github_copilot` | GitHub Copilot |
| `cline` | Cline |
| `augment` | Augment |
| `trae` | Trae |

中文：你正在使用哪个 AI Agent？选一个。
English: Which AI Agent are you using? Pick one.

Default if no answer: `opencode`.

**Q3: Zotero 数据目录 / Zotero Data Directory**

First try auto-detection:
```bash
python -c "from pathlib import Path; d = Path.home() / 'Zotero'; print(str(d) if (d / 'zotero.sqlite').exists() else 'NOT_FOUND')"
```

中文：
> 我检测到 Zotero 数据目录可能在这个位置：`<path>`
> 这个目录应该包含 zotero.sqlite 和 storage/ 文件夹。
> — 正确就回复"对"
> — 不对就把正确的 Zotero 数据目录完整路径发给我

English:
> I detected a Zotero data directory at: `<path>`
> This should contain zotero.sqlite and a storage/ folder.
> — Reply "yes" if correct
> — Otherwise send me the full path to your Zotero data directory

If `NOT_FOUND`:

中文：未检测到 Zotero 数据目录。请把你的 Zotero 数据目录完整路径发给我。
English: Could not auto-detect Zotero data directory. Please send me the full path.

**Do not proceed without this path.**

**Q4: PaddleOCR API Key**

中文：
> PaperForge 的 OCR 功能依赖 PaddleOCR。你有 API Key 吗？
> 没有的话去 https://paddleocr.baidu.com 注册（免费额度）。
> 如果现在跳过，OCR 功能暂时不可用。是否跳过？

English:
> PaperForge needs a PaddleOCR API Key for OCR. Do you have one?
> If not, sign up at https://paddleocr.baidu.com (free tier).
> If you skip now, OCR won't work until configured later. Skip?

**Q5: 目录名称 / Directory Names**

Explain each directory and ask user to confirm or change.

Show this table and ask about each one:

| 参数 / Parameter | 默认 / Default | 用途 / Purpose |
|------|--------|------|
| system dir / 系统目录 | `99_System` | PaperForge internal files (plugins, OCR results, export JSON) |
| resources dir / 资源目录 | `03_Resources` | Literature notes and state tracking |
| literature dir / 文献目录 | `Literature` | Formal literature note cards (your notes) |
| control dir / 控制目录 | `LiteratureControl` | Per-paper state tracking (OCR/deep-reading status) |
| base dir / Base目录 | `05_Bases` | Obsidian Base view files (tabular queue browser) |

Final vault structure:
```
<Vault>/
├── <system-dir>/
│   └── PaperForge/       ← OCR, exports, workers
├── <resources-dir>/
│   ├── <literature-dir>/  ← formal notes
│   └── <control-dir>/     ← state tracking
└── <base-dir>/            ← Obsidian Base views
```

Ask one by one:

中文：
> 1. 系统目录，默认 99_System，你用这个还是改？
> 2. 资源目录，默认 03_Resources？
> 3. 文献目录，默认 Literature？
> 4. 控制目录，默认 LiteratureControl？
> 5. Base 目录，默认 05_Bases？

English:
> 1. System directory, default 99_System. Keep or change?
> 2. Resources directory, default 03_Resources?
> 3. Literature directory, default Literature?
> 4. Control directory, default LiteratureControl?
> 5. Base directory, default 05_Bases?

Use defaults for any the user doesn't change.

---

### Step 1: 检查 Python 版本 / Check Python

```bash
python --version
```

- Python >= 3.10 → proceed to Step 2
- Python < 3.10 or missing → **STOP**.

中文：PaperForge 需要 Python 3.10 或更高版本。请从 https://python.org 下载安装（勾选 "Add Python to PATH"），装好后告诉我。

English: PaperForge requires Python 3.10+. Please install from https://python.org (check "Add Python to PATH"), then tell me when done.

**Wait for user before continuing.**

---

### Step 2: 安装 paperforge 包

```bash
pip install git+https://github.com/LLLin000/PaperForge.git
```

- 成功 → 告诉用户"paperforge 已安装"，进入 Step 3
- 权限错误 → 重试 `pip install --user git+https://github.com/LLLin000/PaperForge.git`
- 其他错误 → 把错误信息展示给用户，**停止**

---

### Step 3: 检测 Zotero / Check Zotero

```bash
python -c "from paperforge.setup_wizard import EnvChecker; from pathlib import Path; c = EnvChecker(Path('<vault_path>')); r = c.check_zotero(); print('OK' if r.passed else 'NOT_FOUND'); print(r.detail)"
```

- `OK` → proceed to Step 4
- `NOT_FOUND` → **STOP**.

中文：未检测到 Zotero。请从 https://zotero.org 下载安装，装好后告诉我。

English: Zotero not found. Please install from https://zotero.org, then tell me when done.

**Wait for user before continuing.**

---

### Step 4: 检测 Better BibTeX 插件 / Check BBT

```bash
python -c "from paperforge.setup_wizard import EnvChecker; from pathlib import Path; c = EnvChecker(Path('<vault_path>')); r = c.check_bbt(); print('OK' if r.passed else 'NOT_FOUND'); print(r.detail)"
```

- `OK` → proceed to Step 5
- `NOT_FOUND` → **STOP**.

中文：
> 未检测到 Better BibTeX 插件。请安装：
> 1. 下载：https://retorque.re/zotero-better-bibtex/
> 2. Zotero → 工具 → 插件 → 齿轮 → Install Plugin From File
> 3. 选择 .xpi → 重启 Zotero
> 装好后告诉我。

English:
> Better BibTeX plugin not found. Please install:
> 1. Download: https://retorque.re/zotero-better-bibtex/
> 2. Zotero → Tools → Add-ons → gear icon → Install Add-on From File
> 3. Select the .xpi → restart Zotero
> Tell me when done.

**Wait for user before continuing.**

---

### Step 5: 创建目录并部署文件

把 Step 0 收集到的所有信息拼成一条命令：

```bash
paperforge setup --headless \
  --vault "<vault_path>" \
  --agent "<agent_key>" \
  --zotero-data "<zotero_data_dir>" \
  --system-dir "<system_dir>" \
  --resources-dir "<resources_dir>" \
  --literature-dir "<literature_dir>" \
  --control-dir "<control_dir>" \
  --base-dir "<base_dir>" \
  --paddleocr-key "<api_key>" \
  --skip-checks
```

- 用 Step 0 收集到的实际值替换每个 `<...>`
- 如果用户 Q4 跳过了 PaddleOCR，去掉 `--paddleocr-key` 那一行
- 如果用户 Q5 某个目录用了默认值，就用默认值（`99_System` / `03_Resources` / `Literature` / `LiteratureControl` / `05_Bases`）
- `--skip-checks` 因为 Step 1-4 已经逐项检测过了

**示例（Windows，全部显式传参）：**
```bash
paperforge setup --headless --vault "D:\Documents\医学文献" --agent opencode --zotero-data "C:\Users\lin\Zotero" --system-dir "99_System" --resources-dir "03_Resources" --literature-dir "Literature" --control-dir "LiteratureControl" --base-dir "05_Bases" --paddleocr-key "sk-xxx" --skip-checks
```

**输出解读**

成功时输出类似：
```
[*] Phase 2: Creating directories...    [OK] 10 directories ready
[*] Phase 4: Deploying files...         [OK] worker scripts / skill files / ...
[*] Phase 5: Creating config files...   [OK] .env / paperforge.json
[*] Phase 6: Registering CLI...         [OK] paperforge CLI registered
[*] Phase 7: Verifying installation...  [OK] All 12 checks passed
```

失败时查看退出码：

| 退出码 | 含义 | 处理 |
|--------|------|------|
| 1 | 找不到 paperforge 包目录 | 包安装不完整，重新 pip install |
| 4 | Worker 脚本缺失 | 同上 |
| 5 | Skill 文件缺失 | 同上 |
| 6 | 文件完整性验证失败 | 检查磁盘空间和写权限 |

---

### Step 6: 验证安装

```bash
paperforge status
```

如果能正常输出状态信息 → 安装成功。

```bash
python -m paperforge status
```

如果 `paperforge` 命令找不到，用这个备选。两者等效。

---

### Step 7: 告诉用户下一步 / Tell User Next Steps

中文：
> 安装完成。接下来你需要做 3 件事：
>
> **1. 配置 Zotero 自动导出 JSON（必须）**
> PaperForge 的数据来源，不做这一步 sync 无法工作：
> - 打开 Zotero
> - 文件 → 导出库 → 格式选 Better BibTeX
> - 保存到 Vault 里的 <system_dir>/PaperForge/exports/
> - 必须勾选 "保持更新" ← 这是自动同步的关键
>
> **2. 在 Obsidian 里启用 PaperForge 插件**
> - 设置 → 社区插件 → 已安装 → PaperForge → 启用
> - Ctrl+P 输入 "PaperForge"
>
> **3. 若跳过了 PaddleOCR Key**
> - 在 <system_dir>/PaperForge/.env 里添加：
>   PADDLEOCR_API_TOKEN=<你的key>

English:
> Installation complete. Three things to do next:
>
> **1. Configure Zotero auto-export JSON (required)**
> This is PaperForge's data source. Sync won't work without it:
> - Open Zotero
> - File → Export Library → Format: Better BibTeX
> - Save to <system_dir>/PaperForge/exports/ in your vault
> - Must check "Keep Updated" ← critical for auto-sync
>
> **2. Enable PaperForge plugin in Obsidian**
> - Settings → Community Plugins → Installed → PaperForge → Enable
> - Ctrl+P, type "PaperForge"
>
> **3. If you skipped PaddleOCR Key**
> - Add to <system_dir>/PaperForge/.env:
>   PADDLEOCR_API_TOKEN=<your key>

---

## 常见问题

### 用户卡在某个步骤

回到那个步骤重新检测，确认用户已完成后再继续。不要跳过。

### vault 路径有空格

用双引号括起来：`--vault "D:\My Documents\MyVault"`

### macOS/Linux 上的 pip 权限问题

加 `--user`：
```bash
pip install --user git+https://github.com/LLLin000/PaperForge.git
```

### 用户已装过 PaperForge（upgrade 场景）

跳过 Step 0-1，直接：
```bash
paperforge setup --headless --vault "<path>" --agent "<key>" --skip-checks
```
