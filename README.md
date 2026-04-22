# Literature Workflow for Medical Research

基于 Obsidian + Zotero + PaddleOCR 的医学文献精读工作流，支持自动 OCR、深度阅读笔记生成和队列管理。

## 快速开始

### 方式一：让 Agent 帮你配置（推荐）

复制以下内容，粘贴给你的 AI Agent，它会自动完成全部配置：

```
Install and configure the literature workflow by following the instructions here:
https://raw.githubusercontent.com/YOUR-USERNAME/YOUR-REPO/main/docs/INSTALLATION.md
```

Agent 会问你几个问题，然后自动完成安装、配置和验证。

### 方式二：手动安装

需要：
- Python 3.10+
- Zotero（安装 Better BibTex 插件）
- Obsidian
- PaddleOCR API Key

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR-USERNAME/YOUR-REPO.git
cd YOUR-REPO

# 2. 安装 Python 依赖
pip install -r requirements.txt

# 3. 运行安装脚本
python setup.py
```

## 功能特性

- `/LD-deep` — 深度精读（Keshav 三阶段阅读法）
- 自动 OCR 提取（PaddleOCR-VL API）
- 图表类型智能识别（20 种图表类型自动检测）
- 图表质量审查指南（14 种图表类型的专业审查清单）
- Zotero 双向同步
- 文献队列管理（Base 集成）

## 文档

- [安装指南](docs/INSTALLATION.md)
- [使用指南](docs/USAGE.md)
- [读图指南](99_System/Template/科研读图指南.md)

## License

MIT License — 允许商业使用，需保留版权声明。
