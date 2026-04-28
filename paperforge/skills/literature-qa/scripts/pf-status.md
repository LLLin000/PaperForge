---
name: pf-status
description: Check PaperForge installation and runtime status. Verifies configuration, paths, and data integrity.
allowed-tools: [Bash]
---

# /pf-status

## Purpose

查看 PaperForge 当前安装与运行状态。

`paperforge status` 会检查：

- 安装完整性（Python 包、依赖）
- 配置文件（`paperforge.json`、`.env`）
- 路径连通性（exports、ocr、library-records、literature 目录）
- Zotero 数据目录链接状态
- Better BibTeX 导出文件状态

## CLI Equivalent

```bash
paperforge status
```

## Prerequisites

无特殊前置条件。此命令用于诊断安装问题，即使在配置不完整时也会尽量输出可用信息。

## Arguments

| 参数 | 必需 | 说明 |
|------|------|------|
| `--vault <PATH>` | 否 | 指定 Vault 根目录（默认当前目录） |

## Example

```bash
# 检查当前目录的 Vault 状态
paperforge status

# 检查指定 Vault 的状态
paperforge status --vault /path/to/vault
```

## Output

典型输出示例：

```
PaperForge Lite v1.2
====================

[安装检查]
✓ Python 包: paperforge v1.2.0
✓ 依赖: requests, pymupdf, pillow

[配置检查]
✓ paperforge.json: 存在且有效
✓ .env: 存在
✓ PADDLEOCR_API_TOKEN: 已设置

[路径检查]
✓ exports: <system_dir>/PaperForge/exports/
✓ ocr: <system_dir>/PaperForge/ocr/
✓ library-records: <resources_dir>/<control_dir>/library-records/
✓ literature: <resources_dir>/<literature_dir>/
✓ Zotero: <system_dir>/Zotero/

[数据检查]
✓ library.json: 存在，包含 150 条文献
✓ library-records: 150 条记录
✓ 正式笔记: 150 篇

状态: 一切正常 ✅
```

## Error Handling

### 配置缺失
- `✗ paperforge.json: 未找到` → 运行 `paperforge doctor` 或重新执行安装

### 路径错误
- `✗ Zotero: 目录不存在或不是有效链接` → 创建 junction/symlink 到 Zotero 数据目录

### 依赖缺失
- `✗ 依赖: requests 未安装` → `pip install requests pymupdf pillow`

### API Key 未设置
- `✗ PADDLEOCR_API_TOKEN: 未设置` → 在 `.env` 文件中添加 API token

## See Also

- [pf-sync](pf-sync.md) — 文献同步
- [pf-ocr](pf-ocr.md) — OCR 提取
