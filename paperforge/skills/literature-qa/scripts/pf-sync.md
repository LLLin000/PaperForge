---
name: pf-sync
description: Sync Zotero Better BibTeX JSON export and generate/update formal literature notes.
allowed-tools: [Bash]
---

# /pf-sync

## Purpose

同步 Zotero Better BibTeX JSON 导出并生成/更新正式文献笔记。

`paperforge sync` 读取 Zotero JSON 中的新条目，直接生成正式文献笔记。

自动读取 `paperforge.json` 定位 exports 目录和 literature 目录。

## CLI Equivalent

```bash
paperforge sync
```

## Prerequisites

- [ ] Zotero 已安装且 Better BibTeX 插件已启用
- [ ] Better BibTeX 已配置自动导出 JSON
- [ ] JSON 导出文件存在（`<system_dir>/PaperForge/exports/library.json`）
- [ ] `paperforge.json` 配置正确（Vault 根目录下）

## Arguments

| 参数 | 必需 | 说明 |
|------|------|------|
| `--dry-run` | 否 | 预览变更，不实际写入文件 |
| `--domain <DOMAIN>` | 否 | 仅同步指定领域（如 `骨科`） |
| `--selection` | 否 | （已废弃）仅保留以兼容旧版 |
| `--index` | 否 | （已废弃）仅保留以兼容旧版 |
| `--vault <PATH>` | 否 | 指定 Vault 根目录（默认当前目录） |

### 选项

```bash
paperforge sync --dry-run      # 预览同步结果
paperforge sync --domain 骨科   # 按领域过滤同步
```

## Example

```bash
# 同步 Zotero 并生成正式笔记
paperforge sync

# 预览模式
paperforge sync --dry-run

# 仅同步特定领域
paperforge sync --domain 骨科

# 指定 Vault 目录
paperforge sync --vault /path/to/vault
```

## Output

```
[INFO] Found 5 new items
[INFO] Created 骨科/XXXXXXX.md
[INFO] Generated 5 formal notes
[INFO] Output: <resources_dir>/<literature_dir>/骨科/XXXXXXX - Title.md
```

生成文件：`<resources_dir>/<literature_dir>/<domain>/<key> - <Title>.md`

## Error Handling

### JSON 文件不存在
- `[ERROR] library.json not found` → 检查 Better BibTeX 导出路径

### 空 JSON 导出
- `[INFO] Found 0 new items` → 确认 Zotero 中有带 citation key 的文献，Better BibTeX 已启用"Keep updated"

## See Also

- [pf-ocr](pf-ocr.md) — OCR 提取（下一步操作）
- [pf-status](pf-status.md) — 检查系统状态
