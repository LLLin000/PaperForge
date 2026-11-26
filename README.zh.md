<p align="center">
  <img src="docs/images/paperforge-banner.png" alt="PaperForge banner" width="100%" />
</p>

# PaperForge

[![Version](https://img.shields.io/github/v/release/LLLin000/PaperForge?style=for-the-badge&label=version)](https://github.com/LLLin000/PaperForge/releases)
[![Python](https://img.shields.io/pypi/pyversions/paperforge?style=for-the-badge&logo=python&logoColor=white&color=3775A9)](https://python.org)
[![License](https://img.shields.io/badge/license-CC--BY--NC--SA--4.0-lightgreen?style=for-the-badge)](LICENSE)

**简体中文** · [English](README.md)

> **铸知识为器，启洞见之明。 — Forge Knowledge, Empower Insight.**

PaperForge 让你的 Zotero 文献库无缝进入 Obsidian：免 Better BibTeX 直连 `zotero.sqlite` 同步、内置无损 PDF 批注器、V3 OCR 全文与图表提取、SQLite FTS5 + `sqlite-vec` 混合检索、以及原生 MCP AI Agent 精读——全部在一个 Vault 中完成。

---

## 0. v2.0.x 三层协同架构（零 Python 前置）

| 组件 | 形态 | 职责 | 所在位置 |
| :--- | :--- | :--- | :--- |
| **Obsidian 插件** | `main.js` + `manifest.json` + `styles.css` | Thin-Client 界面：单一 `.base` 工作台、内置 PDF 批注、伴读面板、4 页极简设置中心 | `<vault>/.obsidian/plugins/paperforge/` |
| **原生 Rust 守护进程** | `paperforge-daemon`（6 平台单文件二进制） | 零 Python 快路径（`base-snapshot`、`search`、`config`）、`--mcp` 服务端（7 工具）、零前置 `uv` 引导 | `~/.paperforge/bin/` |
| **托管 Python 核心** | `paperforge`（`uv` 自动部署隔离 Python 3.12） | Zotero SQLite 同步、V3 OCR 与图表提取、SQLite FTS5 + `sqlite-vec` 检索、Living Memory Cards | `~/.paperforge/runtime/` |

隐藏缓存、OCR 中间产物与 `paperforge.db` 均收纳于 `<vault>/.paperforge/`，不拖慢 Obsidian 文件索引。

---

## 1. 安装 Obsidian 插件

1. 在 Obsidian **社区插件市场** 搜索 **PaperForge** 安装并启用（或通过 **BRAT** 订阅 `https://github.com/LLLin000/PaperForge`，或从 [Releases](https://github.com/LLLin000/PaperForge/releases) 手动下载三件套）。
2. 打开 **设置 → PaperForge**，进入 **「一屏极速开启」**：
   - 点击 **「一键启用引擎并同步文献库」**：原生 `paperforge-daemon` 会自动下载校验便携 `uv` 并在 `~/.paperforge/runtime/` 中配置隔离 Python 3.12，无需用户预装 Python 或手动 `pip install`。
   - **直连 Zotero**：自动只读快照 `zotero.sqlite`（不再强制 Better BibTeX，仍保留可选兼容模式），支持按顶级分类建子文件夹或平铺模式的实时预览。
   - **四页设置与 10 态决策树**：分为 **概览 · 模块配置 · 外观 · 帮助** 四页；老版本 `System/PaperForge/` Vault 可在主卡 3 秒无损升级。
   - **可选 OCR / 向量检索**：API Key 加密存入操作系统 Keyring（不存明文 `.env`），向量检索使用内置 `sqlite-vec`（`vec0`），无需 ChromaDB。

---

## 2. 独立命令行与 AI Agent MCP 接入

```bash
pip install "paperforge[vector]"
paperforge setup --modular
paperforge auth set ocr          # 安全交互输入 PaddleOCR Token（写入 OS Keyring）
paperforge sync
paperforge ocr
paperforge status --json
```

一键为 Claude Code、Cursor、Codex、OpenCode 等客户端接入原生 MCP 与 Skill Hub：

```bash
paperforge-daemon mcp-install --vault <VAULT_DIR> --platform claude
paperforge-daemon mcp-check --vault <VAULT_DIR> --platform claude --probe-mcp
paperforge-daemon skill-sync-all
```

在 Agent 对话中输入 `/pf-deep <zotero_key>` 执行 Keshav 三阶段精读，或 `/pf-paper <zotero_key>` 进行交互问答。

---

## 文档导航

| 你想做什么 | 去看 |
| :--- | :--- |
| 快速上手教程 | [使用教程](docs/getting-started.md) |
| 完整使用手册 | [使用手册](docs/user-manual.md) |
| 查某个 CLI / Daemon / MCP 命令 | [命令参考](docs/COMMANDS.md) |
| 独立命令行安装说明 | [安装指南](INSTALLATION.md) |
| 遇到问题了 | [故障排除](docs/troubleshooting.md) |
| 安装与升级架构蓝图 | [架构蓝图](docs/INSTALL-AND-UPDATE-ARCHITECTURE.md) |
| AI Agent 协作契约 | [AGENTS.md](AGENTS.md) |

---

## 协议与致谢

- 协议：[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)（仅限非商业使用）。
- 致谢：基于 [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)、[Obsidian](https://obsidian.md)、[Zotero](https://www.zotero.org/) 与 [sqlite-vec](https://github.com/asg017/sqlite-vec) 构建。
