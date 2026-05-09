# PaperForge Headless Setup — For LLM Agents (简体中文)

> **IMPORTANT**: 直接读取此文件。不要用 WebFetch 或摘要——会丢失关键的 CLI 参数和决策逻辑。
> 
> 完整安装参考请见 [INSTALLATION.md](../INSTALLATION.md)。

---

## For Humans（给人类用户）

复制粘贴给你的 AI Agent：

```
在当前的 vault 里安装 PaperForge。参考下面的文档完成安装：
https://raw.githubusercontent.com/LLLin000/PaperForge/master/docs/ai-agent-setup-guide-zh.md
```

---

## For LLM Agents（给 AI Agent）

你正在帮用户在 Obsidian Vault 里安装 PaperForge。**按顺序执行每一步，不要跳过。**每步完成后报告结果再继续。

**用中文和用户对话。**

---

### Step 0: 收集信息 — 先问清楚再动手

**以下所有问题必须在执行任何命令之前问完。不能猜，不能用默认值糊弄。**

**Q1: Vault 路径**

> 你的 Obsidian Vault 的完整绝对路径是什么？
> （如果不知道：打开 Obsidian → 左下角点 vault 名称 → "管理 Vault" → 右键 vault → "在系统文件管理器中显示"。把那个文件夹的完整路径发给我。）

要求绝对路径，不接受相对路径。

**Q2: AI Agent 平台**

> 你正在使用哪个 AI Agent？

展示表格让用户选：

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

不回答则默认 `opencode`。

**Q3: Zotero 数据目录**

先尝试自动检测：
```bash
python -c "from pathlib import Path; d = Path.home() / 'Zotero'; print(str(d) if (d / 'zotero.sqlite').exists() else 'NOT_FOUND')"
```

把检测结果告诉用户并确认：

> 我检测到 Zotero 数据目录可能在这个位置：`<path>`
> 这个目录应该包含 zotero.sqlite 和 storage/ 文件夹。
> — 正确就回复"对"
> — 不对就把正确的 Zotero 数据目录完整路径发给我

如果是 `NOT_FOUND`：

> 未检测到 Zotero 数据目录。请把你的 Zotero 数据目录完整路径发给我。
> （需要包含 zotero.sqlite 和 storage/ 文件夹的那个目录）

**拿不到绝对路径不往下走。**

**Q4: PaddleOCR API Key**

> PaperForge 的 OCR 功能依赖 PaddleOCR。你有 API Key 吗？
> 没有的话去 https://paddleocr.baidu.com 注册（免费额度）。
> 如果现在跳过，OCR 功能暂时不可用。是否跳过？

**Q5: 目录名称**

解释每个目录用途，逐一确认或修改：

| 参数 | 默认值 | 用途 |
|------|--------|------|
| 系统目录 | `99_System` | 存放 PaperForge 自身文件（插件、OCR 结果、导出 JSON） |
| 资源目录 | `03_Resources` | 存放文献笔记和状态跟踪文件 |
| 文献目录 | `Literature` | 存放正式文献卡片（你的笔记） |
| 控制目录 | `LiteratureControl` | 存放文献状态跟踪（每篇文献的 OCR/精读状态） |
| Base 目录 | `05_Bases` | 存放 Obsidian Base 视图文件（表格化浏览文献队列） |

Vault 最终结构：
```
<Vault>/
├── <系统目录>/
│   └── PaperForge/       ← OCR 结果、导出 JSON、worker 脚本
├── <资源目录>/
│   ├── <文献目录>/         ← 正式文献笔记
│   └── <控制目录>/         ← 文献状态跟踪
└── <Base目录>/            ← Obsidian Base 视图
```

逐一确认：
> 1. 系统目录，默认 `99_System`，你用这个还是改？
> 2. 资源目录，默认 `03_Resources`？
> 3. 文献目录，默认 `Literature`？
> 4. 控制目录，默认 `LiteratureControl`？
> 5. Base 目录，默认 `05_Bases`？

用户改了的记下来，没改的用默认值。

---

### Step 1: 检查 Python 版本

```bash
python --version
```

- Python >= 3.10 → 继续 Step 2
- Python < 3.10 或不存在 → **停止**。

> PaperForge 需要 Python 3.10 或更高版本。请从 https://python.org 下载安装（勾选 "Add Python to PATH"），装好后告诉我。

**等用户确认后再继续。**

---

### Step 2: 安装 paperforge 包

```bash
pip install git+https://github.com/LLLin000/PaperForge.git
```

- 成功 → "paperforge 已安装"，继续 Step 3
- 权限错误 → 重试：`pip install --user git+https://github.com/LLLin000/PaperForge.git`
- 其他错误 → 把错误信息展示给用户，**停止**

---

### Step 3: 检测 Zotero

```bash
python -c "from paperforge.setup_wizard import EnvChecker; from pathlib import Path; c = EnvChecker(Path('<vault_path>')); r = c.check_zotero(); print('OK' if r.passed else 'NOT_FOUND'); print(r.detail)"
```

- `OK` → 继续 Step 4
- `NOT_FOUND` → **停止**。

> 未检测到 Zotero。请从 https://zotero.org 下载安装，装好后告诉我。

**等用户确认后再继续。**

---

### Step 4: 检测 Better BibTeX 插件

```bash
python -c "from paperforge.setup_wizard import EnvChecker; from pathlib import Path; c = EnvChecker(Path('<vault_path>')); r = c.check_bbt(); print('OK' if r.passed else 'NOT_FOUND'); print(r.detail)"
```

- `OK` → 继续 Step 5
- `NOT_FOUND` → **停止**。

> 未检测到 Better BibTeX 插件。请安装：
> 1. 下载：https://retorque.re/zotero-better-bibtex/
> 2. Zotero → 工具 → 插件 → 齿轮 → Install Plugin From File
> 3. 选择 .xpi → 重启 Zotero
> 装好后告诉我。

**等用户确认后再继续。**

---

### Step 5: 创建目录并部署文件

重要安全规则：这个安装流程必须是增量式的。如果目标 Vault 或所选目录里已经有文件，PaperForge 只能创建缺失的目录和文件，不能覆盖已有内容。

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
- 如果用户在 Q4 跳过了 PaddleOCR，去掉 `--paddleocr-key` 那一行
- 如果用户某个目录用了默认值，就写默认值
- `--skip-checks` 因为 Step 1-4 已经逐项检测过了

**示例（Windows，全部默认值）：**
```bash
paperforge setup --headless --vault "D:\Documents\MyVault" --agent opencode --zotero-data "C:\Users\name\Zotero" --system-dir "99_System" --resources-dir "03_Resources" --literature-dir "Literature" --control-dir "LiteratureControl" --base-dir "05_Bases" --paddleocr-key "sk-xxx" --skip-checks
```

**期望输出：**
```
[*] Phase 2: Creating directories...    [OK] 10 directories ready
[*] Phase 4: Deploying files...         [OK] worker scripts / skill files / ...
[*] Phase 5: Creating config files...   [OK] .env / paperforge.json
[*] Phase 6: Registering CLI...         [OK] paperforge CLI registered
[*] Phase 7: Verifying installation...  [OK] All 12 checks passed
```

**失败退出码：**

| 退出码 | 含义 | 处理 |
|--------|------|------|
| 1 | 找不到 paperforge 包目录 | 重新 pip install |
| 4 | Worker 脚本缺失 | 同上 |
| 5 | Skill 文件缺失 | 同上 |
| 6 | 文件完整性验证失败 | 检查磁盘空间和写权限 |

---

### Step 6: 验证安装

```bash
paperforge status
```

如果 `paperforge` 命令找不到，试：
```bash
python -m paperforge status
```

---

### Step 7: 告诉用户下一步

> 安装完成。接下来你需要做 4 件事：
>
> **1. 配置 Zotero 自动导出 JSON（必须）**
> PaperForge 的数据来源，不做这一步 sync 无法工作：
> - 打开 Zotero
> - 对要同步的文献库或分类右键 → 导出
> - 格式选 Better BibTeX JSON
> - 必须勾选 "保持更新"
> - 保存到 Vault 里的 <system_dir>/PaperForge/exports/
>
> **2. 在 Obsidian 里启用 PaperForge 插件**
> - 设置 → 社区插件 → 已安装 → PaperForge → 启用
> - Ctrl+P 输入 "PaperForge"，打开 Dashboard
>
> **3. 同步文献**
> - 在 Dashboard 中点击 `Sync Library`
>
> **4. 若跳过了 PaddleOCR Key**
> - 在 <system_dir>/PaperForge/.env 里添加：
>   PADDLEOCR_API_TOKEN=<你的key>

---

## 常见问题

### 用户卡在某个步骤

回到那个步骤重新检测，确认用户已完成后再继续。不要跳过。

### vault 路径有空格

用双引号括起来：`--vault "D:\My Documents\MyVault"`

### macOS/Linux 上 pip 权限错误

加 `--user`：
```bash
pip install --user git+https://github.com/LLLin000/PaperForge.git
```

### 用户已经装过 PaperForge（升级场景）

跳过 Step 0-1，直接：
```bash
paperforge setup --headless --vault "<path>" --agent "<key>" --skip-checks
```
