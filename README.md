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

**一行命令安装：**

```powershell
pip install git+https://github.com/LLLin000/PaperForge.git
paperforge setup
```

安装向导会自动完成：
- 检测 Python 环境和依赖
- 配置 Vault 目录结构（可自定义名称）
- 链接 Zotero 数据目录
- 检测 Better BibTeX 插件
- 配置 PaddleOCR API Key
- 部署 Agent 命令和精读脚本
- 创建 `.env` 配置文件

> **Windows 一键安装脚本**（适用于新用户，无需提前安装 Python 知识）：
> ```powershell
> powershell -c "iwr -Uri https://raw.githubusercontent.com/LLLin000/PaperForge/master/scripts/install-paperforge.ps1 -OutFile install.ps1; ./install.ps1"
> paperforge setup
> ```

## 功能特性

- **交互式安装向导** — `paperforge setup` 步骤引导配置
- **`/pf-deep`** — 深度精读（Keshav 三阶段阅读法）
- **自动 OCR 提取** — PaddleOCR-VL API，自动重试+进度条
- **图表类型智能识别** — 19 种图表类型自动检测
- **图表质量审查指南** — 19 种图表类型专业审查清单
- **Zotero 双向同步** — Better BibTeX 自动导出
- **文献队列管理** — Obsidian Base 视图集成
- **持久轮询** — OCR 上传后自动等待完成，一次命令搞定
- **结构化日志** — `--verbose`/`-v` 全局参数，stderr 诊断输出
- **代码质量栅栏** — pre-commit + ruff 检查 + 一致性审计
- **自动更新** — `paperforge update`

## 安装要求

- Python 3.10+
- Zotero + Better BibTeX 插件（配置自动导出 JSON）
- Obsidian
- PaddleOCR API Key（安装时配置）

## 目录结构

```
your-vault/
├── [资源目录]/                  # 安装时可自定义
│   └── [文献索引目录]/
│       └── library-records/     # 文献状态跟踪
├── [系统目录]/                  # 安装时可自定义
│   ├── PaperForge/
│   │   ├── exports/             # Zotero JSON 导出
│   │   └── ocr/                 # OCR 结果
│   └── Zotero/                  # Junction 到 Zotero 数据目录
├── [Agent配置目录]/             # 根据平台决定
│   └── skills/
│       └── literature-qa/
│           ├── scripts/ld_deep.py
│           ├── prompt_deep_subagent.md
│           └── chart-reading/   # 19 种图表阅读指南
├── .env                         # API Key 配置
├── paperforge.json              # 版本配置
└── AGENTS.md                    # 安装后指南
```

## 核心命令

```bash
# 终端命令
paperforge setup              # 运行安装向导
paperforge status             # 查看状态
paperforge sync               # 同步 Zotero 并生成笔记
paperforge ocr                # OCR（自动上传+等待+下载）
paperforge deep-reading       # 查看精读队列
paperforge doctor             # 诊断配置
paperforge update             # 检查更新
paperforge --verbose          # 全局 DEBUG 日志

# Agent 命令（在 OpenCode 中使用）
/pf-deep <zotero_key>    # 完整三阶段精读
/pf-paper <zotero_key>   # 快速摘要
/pf-sync                 # 同步 Zotero
/pf-ocr                  # 运行 OCR
/pf-status               # 查看状态
```

## 更新

```bash
paperforge update
# 或
pip install --upgrade git+https://github.com/LLLin000/PaperForge.git
```

## 文档

- [安装指南](docs/INSTALLATION.md)
- [安装后指南](AGENTS.md)
- [变更日志](CHANGELOG.md)
- [贡献指南](CONTRIBUTING.md)
- [v1.4 迁移说明](docs/MIGRATION-v1.4.md)

## License

MIT License
