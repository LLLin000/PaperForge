# /pf-sync

## Purpose

同步 Zotero Better BibTeX JSON 导出并生成/更新正式文献笔记。

`paperforge sync` 自动检测 Zotero JSON 中的新条目并直接生成正式文献笔记。

自动读取 `paperforge.json` 定位 exports 目录、control 目录和 literature 目录。

## CLI Equivalent

```bash
paperforge sync
```

如需使用 Python 直接调用（备选方式）：

```bash
python -m paperforge sync --vault .
```

## Prerequisites

- [ ] Zotero 已安装且 Better BibTeX 插件已启用
- [ ] Better BibTeX 已配置自动导出 JSON
- [ ] JSON 导出文件存在（`<system_dir>/PaperForge/exports/library.json`）
- [ ] `paperforge.json` 配置正确（Vault 根目录下）
- [ ] 目录结构已创建（`setup.py` 会自动完成）

## Arguments

| 参数 | 必需 | 说明 |
|------|------|------|
| `--dry-run` | 否 | 预览变更，不实际写入文件 |
| `--domain <DOMAIN>` | 否 | 仅同步指定领域（如 `骨科`） |
| `--vault <PATH>` | 否 | 指定 Vault 根目录（默认当前目录） |

预览同步结果（不实际写入）：

```bash
paperforge sync --dry-run
```

按领域过滤同步：

```bash
paperforge sync --domain 骨科
```

## Example

```bash
# 完整同步
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
[INFO] Generated 5 formal notes
[INFO] Output: <resources_dir>/<literature_dir>/骨科/XXXXXXX - Title.md
```

生成文件：
- `<resources_dir>/<literature_dir>/<domain>/<key> - <Title>.md`

## Error Handling

### JSON 文件不存在
- **表现**：`[ERROR] library.json not found`
- **解决**：检查 Better BibTeX 导出路径是否正确配置

### 目录权限错误
- **表现**：`[ERROR] Permission denied`
- **解决**：检查 Vault 目录和子目录的写入权限

### Zotero key 重复
- **表现**：`[WARNING] Duplicate key detected`
- **解决**：在 Zotero 中检查重复的 citation key

### 空 JSON 导出
- **表现**：`[INFO] Found 0 new items`（预期有文献但未检测到）
- **解决**：
  1. 确认 Zotero 中有带 citation key 的文献
  2. 确认 Better BibTeX 已启用"Keep updated"
  3. 手动触发一次导出（Tools → Better BibTeX → Refresh BibTeX Key）

## Platform Notes

### OpenCode

> `/pf-sync` 是 **CLI 命令**，Agent 层不直接提供 `/pf-sync` 聊天命令。
>
> 用户需要在终端运行 `paperforge sync`。
> Agent 可以在对话中指导用户执行同步步骤，或通过 Bash tool 代为执行。

### Codex

> **Future**：计划支持。预计通过 API 调用实现类似功能。

### Claude Code

> **Future**：计划支持。预计通过工具调用实现类似功能。

## See Also

- [pf-ocr](pf-ocr.md) — OCR 提取（下一步操作）
- [pf-status](pf-status.md) — 检查系统状态
- [AGENTS.md](../AGENTS.md) — 完整使用指南、架构说明、常见问题
- [docs/COMMANDS.md](../docs/COMMANDS.md) — 命令总览与矩阵
