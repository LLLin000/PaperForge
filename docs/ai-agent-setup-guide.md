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

---

### Step 0: 收集信息 — 必须先问清楚

**以下所有问题必须在执行任何命令之前问完。不能猜，不能用默认值糊弄。**

**Q1: Obsidian Vault 路径**

问：
> 你的 Obsidian Vault 的完整绝对路径是什么？

要求用户提供绝对路径（如 `D:\Documents\医学文献` 或 `/Users/name/Documents/MyVault`）。

如果用户说不知道：
> 打开 Obsidian → 左下角点 vault 名称 → "管理 Vault" → 右键 vault → "在系统文件管理器中显示"。把那个文件夹的完整路径发给我。

**Q2: AI Agent 平台**

问：
> 你正在使用哪个 AI Agent？

展示列表让用户选：

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

用户不回答则默认 `opencode`。

**Q3: Zotero 数据目录**

先尝试自动检测：
```bash
python -c "from pathlib import Path; d = Path.home() / 'Zotero'; print(str(d) if (d / 'zotero.sqlite').exists() else 'NOT_FOUND')"
```

然后告诉用户检测结果，并给用户手动指定的机会：

> 我检测到 Zotero 数据目录可能在这个位置：`<检测到的路径>`
>
> 这个目录应该包含 `zotero.sqlite` 和 `storage/` 文件夹。
>
> — 如果正确，回复"对"
> — 如果不对，请把正确的 Zotero 数据目录完整路径发给我
>
> （常见位置：Windows: `C:/Users/<用户名>/Zotero`，macOS: `~/Zotero`）

如果检测结果是 `NOT_FOUND`，直接问：
> 未检测到默认位置的 Zotero 数据目录。请把你的 Zotero 数据目录完整路径发给我。
> （需要包含 `zotero.sqlite` 和 `storage/` 文件夹的那个目录）

**拿不到绝对路径不往下走。**

**Q4: PaddleOCR API Key**

问：
> PaperForge 的 OCR 功能依赖 PaddleOCR。你有 API Key 吗？

- 有 → 拿到 key 值，记下来
- 没有 → 告诉用户：
  > 请到 https://paddleocr.baidu.com 注册获取（免费额度）。
  > 如果现在跳过，OCR 功能暂时不可用。后续在 <system_dir>/PaperForge/.env 里配置。
  > 是否跳过？

**Q5: 目录名称（必选）**

问：
> PaperForge 会在 Vault 里创建 5 个目录。每个目录默认一个名称，你可以改。下面列出各自用途，你确认或修改后我继续：

| 参数 | 默认值 | 用途 |
|------|--------|------|
| 系统目录 | `99_System` | 存放 PaperForge 自身文件（插件、OCR 结果、导出 JSON） |
| 资源目录 | `03_Resources` | 存放文献笔记和状态跟踪文件 |
| 文献子目录 | `Literature` | 存放正式文献卡片（你的笔记） |
| 控制目录 | `LiteratureControl` | 存放文献状态跟踪（每篇文献的 OCR/精读状态） |
| Base 目录 | `05_Bases` | 存放 Obsidian Base 视图文件（表格化浏览文献队列） |

Vault 最终结构：
```
<Vault>/
├── <系统目录>/
│   └── PaperForge/       ← OCR 结果、导出 JSON、worker 脚本
├── <资源目录>/
│   ├── <文献子目录>/       ← 正式文献笔记
│   └── <控制目录>/         ← 文献状态跟踪
└── <Base目录>/            ← Obsidian Base 视图
```

逐项确认：
> 1. 系统目录名，默认 `99_System`，你用这个还是改？
> 2. 资源目录名，默认 `03_Resources`，你用这个还是改？
> 3. 文献子目录名，默认 `Literature`，你用这个还是改？
> 4. 控制目录名，默认 `LiteratureControl`，你用这个还是改？
> 5. Base 目录名，默认 `05_Bases`，你用这个还是改？

用户改了的记下来，没改的用默认值。

---

### Step 1: 检查 Python 版本

```bash
python --version
```

- Python >= 3.10 → 通过，进入 Step 2
- Python < 3.10 或不存在 → **停止**。告诉用户：
  > PaperForge 需要 Python 3.10 或更高版本。请从 https://python.org 下载安装后再继续。
  > 
  > 安装时请勾选 "Add Python to PATH"。

---

### Step 2: 安装 paperforge 包

```bash
pip install git+https://github.com/LLLin000/PaperForge.git
```

- 成功 → 告诉用户"paperforge 已安装"，进入 Step 3
- 权限错误 → 重试 `pip install --user git+https://github.com/LLLin000/PaperForge.git`
- 其他错误 → 把错误信息展示给用户，**停止**

---

### Step 3: 检测 Zotero

```bash
python -c "from paperforge.setup_wizard import EnvChecker; from pathlib import Path; c = EnvChecker(Path('<vault_path>')); r = c.check_zotero(); print('OK' if r.passed else 'NOT_FOUND'); print(r.detail)"
```

把 `<vault_path>` 替换为 Step 0 拿到的路径。

- `OK` → 告诉用户 "检测到 Zotero"，进入 Step 4
- `NOT_FOUND` → 告诉用户：
  > 未检测到 Zotero。请从 https://zotero.org 下载安装。
  > 
  > 安装完成后告诉我，我继续检测。
  
  **等待用户确认后再继续**。

---

### Step 4: 检测 Better BibTeX 插件

```bash
python -c "from paperforge.setup_wizard import EnvChecker; from pathlib import Path; c = EnvChecker(Path('<vault_path>')); r = c.check_bbt(); print('OK' if r.passed else 'NOT_FOUND'); print(r.detail)"
```

- `OK` → 告诉用户 "检测到 Better BibTeX"，进入 Step 5
- `NOT_FOUND` → 告诉用户：
  > 未检测到 Better BibTeX 插件。请按以下步骤安装：
  > 1. 下载：https://retorque.re/zotero-better-bibtex/
  > 2. Zotero → 工具 → 插件 → 齿轮 → Install Plugin From File
  > 3. 选择下载的 .xpi 文件 → 重启 Zotero
  
  **等待用户确认后再继续**。

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

### Step 7: 告诉用户下一步

报告给用户以下信息：

> 安装完成。接下来你需要做 3 件事：

> **1. 配置 Zotero 自动导出 JSON（必须）**
> 这是 PaperForge 的数据来源，不做这一步 sync 无法工作：
> - 打开 Zotero
> - 文件 → 导出库 → 格式选 **Better BibTeX**
> - 保存到 Vault 里的 `<system_dir>/PaperForge/exports/`
> - **必须勾选 "保持更新"** ← 这是自动同步的关键
>
> 配置完成后运行 `paperforge sync` 测试是否正常。

> **2. 在 Obsidian 里启用 PaperForge 插件**
> - 打开 Obsidian
> - 设置 → 社区插件 → 已安装插件 → 找到 PaperForge → 启用
> - Ctrl+P 输入 "PaperForge"，可以看到 3 个命令：
>   - `PaperForge: 同步文献并生成笔记`
>   - `PaperForge: 运行 OCR`
>   - `PaperForge: 查看系统状态`

> **3. 若跳过了 PaddleOCR Key**
> - 在 `<system_dir>/PaperForge/.env` 里添加：
>   ```
>   PADDLEOCR_API_TOKEN=<你的key>
>   ```
> - 获取地址：https://paddleocr.baidu.com

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
