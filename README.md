# PaperForge Lite

基于 Obsidian + Zotero + PaddleOCR 的医学文献精读工作流，支持自动 OCR、深度阅读笔记生成和队列管理。

```
    ______  ___  ______ _________________ ___________ _____  _____ 
    | ___ \/ _ \ | ___ \  ___| ___ \  ___|  _  | ___ \  __ \|  ___|
    | |_/ / /_\ \| |_/ / |__ | |_/ / |_  | | | | |_/ / |  \/| |__  
    |  __/|  _  ||  __/|  __||    /|  _| | | | |    /| | __ |  __| 
    | |   | | | || |   | |___| |\ \| |   \ \_/ / |\ \| |_\ \| |___ 
    \_|   \_| |_/\_|   \____/\_| \_\_|    \___/\_| \_|\____/\____/ 
```

## 快速开始（推荐方式）

**PaperForge 提供交互式安装向导，引导你完成全部配置：**

```bash
# 1. 克隆仓库
git clone https://github.com/LLLin000/PaperForge.git
cd PaperForge

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行向导（交互式，按步骤引导）
python setup_wizard.py --vault /path/to/your/vault
```

向导会自动完成：
- 检测 Python 环境和依赖
- 配置 Vault 目录结构（可自定义名称）
- 链接 Zotero 数据目录
- 检测 Better BibTeX 插件
- 配置 JSON 自动导出
- 部署工作流脚本和 Agent 命令
- 创建 .env 配置文件

## 功能特性

- **交互式安装向导** — 步骤引导，自动检测，安全验证
- **`/LD-deep`** — 深度精读（Keshav 三阶段阅读法）
- **自动 OCR 提取** — PaddleOCR-VL API 提取全文和图表
- **图表类型智能识别** — 20 种图表类型自动检测
- **图表质量审查指南** — 14 种图表类型的专业审查清单
- **Zotero 双向同步** — Better BibTeX 自动导出
- **文献队列管理** — Obsidian Base 集成
- **自动更新** — `python literature_pipeline.py --vault . update`

## 安装要求

- Python 3.10+
- Zotero + Better BibTeX 插件
- Obsidian
- PaddleOCR API Key（安装后配置）

## 目录结构

```
your-vault/
├── [资源目录]/                  # 安装时可自定义
│   └── [文献索引目录]/
│       └── library-records/     # 文献状态跟踪
├── [系统目录]/                  # 安装时可自定义
│   ├── PaperForge/
│   │   ├── exports/             # Zotero JSON 导出
│   │   ├── ocr/                 # OCR 结果
│   │   └── worker/scripts/
│   │       └── literature_pipeline.py
│   └── Zotero/                  # Junction 到 Zotero 数据目录
├── [Agent配置目录]/             # 根据平台和安装配置决定
│   └── skills/
│       └── literature-qa/
│           ├── scripts/ld_deep.py
│           ├── prompt_deep_subagent.md
│           └── chart-reading/   # 14 种图表阅读指南
├── .env                         # API Key 配置
├── paperforge.json              # 版本配置
└── AGENTS.md                    # 安装后指南
```

## 文档

- [安装指南](docs/INSTALLATION.md) — 详细安装步骤
- [安装后指南](AGENTS.md) — 第一次使用必看
- [设置向导](setup_wizard.py) — 交互式配置工具

## 核心命令

```bash
# PaperForge 统一入口（推荐）
paperforge status            # 查看状态
paperforge selection-sync    # 同步 Zotero 文献
paperforge index-refresh     # 生成正式笔记
paperforge ocr run           # 运行 PDF OCR
paperforge deep-reading      # 查看精读队列

# Agent 命令（在 OpenCode 中使用）
/LD-deep <zotero_key>    # 完整三阶段精读
/LD-paper <zotero_key>   # 快速摘要

# 备选：直接调用 worker 脚本（需要先运行 paperforge paths --json 获取路径）
python <resolved_worker_script> --vault . selection-sync
python <resolved_worker_script> --vault . index-refresh
python <resolved_worker_script> --vault . ocr
python <resolved_worker_script> --vault . status
```

## License

MIT License — 允许商业使用，需保留版权声明。

