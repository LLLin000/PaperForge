# PaperForge 安装指南

## 推荐方式：交互式安装向导

PaperForge 提供图形化安装向导，引导你完成全部配置：

```bash
# 1. 克隆仓库
git clone https://github.com/LLLin000/PaperForge.git
cd PaperForge

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行向导
python setup_wizard.py --vault /path/to/your/vault
```

向导会按步骤引导你：
1. **选择 Agent 平台** — OpenCode / Cursor / Claude Code 等
2. **检查 Python 环境** — 自动检测版本和依赖
3. **配置 Vault 目录** — 自定义系统目录和资源目录名称
4. **链接 Zotero 数据目录** — 自动创建 Junction
5. **检测 Better BibTeX** — 确认插件已安装
6. **配置 JSON 导出** — 设置自动导出路径和"保持更新"
7. **一键部署** — 自动复制脚本、创建配置、验证完整性

### 前置条件

| 工具 | 用途 | 获取方式 |
|------|------|----------|
| Python 3.10+ | 运行工作流脚本 | https://python.org |
| Zotero | 文献管理 | https://zotero.org |
| Better BibTeX | Zotero 插件，生成 citation key 和 JSON 导出 | https://retorque.re/zotero-better-bibtex/ |
| Obsidian | 笔记软件 | https://obsidian.md |
| PaddleOCR API Key | OCR 服务 | https://paddleocr.baidu.com |

---

## 手动安装（备用）

如果向导无法运行，可以手动安装：

### Step 1: 安装依赖

```bash
pip install requests pymupdf pillow
```

### Step 2: 创建目录结构

```bash
mkdir -p "{vault_path}/<system_dir>/PaperForge/ocr"
mkdir -p "{vault_path}/<system_dir>/PaperForge/worker/scripts"
mkdir -p "{vault_path}/<system_dir>/Zotero"
mkdir -p "{vault_path}/<resources_dir>/<control_dir>/library-records"
```

### Step 3: 链接 Zotero 数据目录

**Windows** (管理员终端):
```cmd
mklink /J "{vault_path}\<system_dir>\Zotero" "C:\Users\<User>\Zotero"
```

**macOS/Linux**:
```bash
ln -s "~/Zotero" "{vault_path}/<system_dir>/Zotero"
```

### Step 4: 配置 .env

创建 `{vault_path}/.env`:
```
PADDLEOCR_API_TOKEN=your_api_token_here
PADDLEOCR_JOB_URL=https://paddleocr.aistudio-app.com/api/v2/ocr/jobs
```

### Step 5: 部署脚本

```bash
cp pipeline/worker/scripts/literature_pipeline.py "{vault_path}/<system_dir>/PaperForge/worker/scripts/"
cp -r skills/literature-qa "{vault_path}/<skill_dir>/"
cp AGENTS.md "{vault_path}/AGENTS.md"
```

---

## 安装后验证

运行向导后，验证安装：

```bash
cd "{vault_path}"

# 验证 PaperForge 路径配置
paperforge paths

# 验证系统状态
paperforge status
```

预期输出（`paperforge status`）：
```
PaperForge Lite v1.2.0
Vault: /path/to/your/vault
Status: OK
```

**备选方式**（直接调用 worker 脚本）：
```bash
# 先获取 worker 脚本路径
python -m pip install -e .
python $(python -c "import json; print(json.load(open('paperforge.json'))['paperforge_path'] + '/worker/scripts/literature_pipeline.py')" --vault . status
```

---

## 故障排除

### Zotero 未找到
- 确认 Zotero 已安装
- 检查数据目录路径（Zotero → Edit → Preferences → Advanced → Files and Folders）
- 向导中手动输入正确的数据目录路径

### 权限被拒绝（Windows）
- 以管理员身份运行终端来创建 Junction
- 或手动创建 Junction：`mklink /J "目标" "源"`

### Better BibTeX 未安装
- Zotero → 工具 → 插件 → 齿轮图标 → Install Plugin From File...
- 下载地址：https://retorque.re/zotero-better-bibtex/

---

## 下一步

安装完成后：

1. **同步文献**：运行 selection-sync 检测 Zotero 中的文献
2. **生成笔记**：运行 index-refresh 创建正式文献笔记
3. **标记精读**：在 Obsidian 中设置 `do_ocr: true` 和 `analyze: true`
4. **运行 OCR**：执行 ocr 命令处理 PDF
5. **开始精读**：使用 `/LD-deep <zotero_key>` 生成结构化阅读笔记

详细用法参见 [AGENTS.md](../AGENTS.md)。

