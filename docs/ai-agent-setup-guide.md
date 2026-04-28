# PaperForge Headless Setup — For LLM Agents

> **IMPORTANT**: Read this file directly. Do NOT use WebFetch or summarization — you will lose critical CLI flags and decision logic.

---

## For Humans

Copy this and paste it to your AI agent:

```
请帮我安装 PaperForge。
参考 https://raw.githubusercontent.com/LLLin000/PaperForge/master/docs/ai-agent-setup-guide.md 完成安装。
```

---

## For LLM Agents

You are installing PaperForge into the user's Obsidian Vault. Follow each step in order. **Do not skip steps.** Report results at each step before proceeding.

---

### Step 0: 收集信息 — 问用户 3 个问题

**必须问。不能猜。不能跳过。**

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

**Q3（可选）: PaddleOCR API Key**

问：
> 你有 PaddleOCR API Key 吗？

- 有 → 拿到 key 值，记下来
- 没有 → 跳过，不追问。获取地址：https://paddleocr.baidu.com

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

现在一次性完成目录创建和文件部署：

```bash
paperforge setup --headless \
  --vault "<vault_path>" \
  --agent "<agent_key>" \
  --skip-checks
```

**重要**：加 `--skip-checks`，因为 Step 1-4 已经逐项检测过了，不需要重复。

如果有 PaddleOCR Key，加上 `--paddleocr-key "<key>"`。

示例（Windows，OpenCode，无 Key）：
```bash
paperforge setup --headless --vault "D:\Documents\医学文献" --agent opencode --skip-checks
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

> 安装完成。接下来你需要做：
> 
> **在 Obsidian 里启用插件：**
> 1. 打开 Obsidian
> 2. 设置 → 社区插件 → 已安装插件 → 找到 PaperForge → 启用
> 3. Ctrl+P 输入 "PaperForge"，可以看到 3 个命令
> 
> **配置 Zotero 自动导出（必须）：**
> 4. Zotero → 文件 → 导出库 → 格式选 Better BibTeX
> 5. 保存到 Vault 里的 `<system_dir>/PaperForge/exports/`
> 6. 勾选 "保持更新"
> 
> **首次使用流程：**
> 7. 在 Zotero 里添加文献 → `paperforge sync`（同步到 Obsidian）
> 8. 在 Obsidian 的 library-records 里设置 `do_ocr: true`
> 9. `paperforge ocr`（运行 OCR）
> 10. 在 Agent 里输入 `/pf-deep <key>`（精读）

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
