# /pf-sync

同步 Zotero Better BibTeX JSON 导出到 library-records，并生成/更新正式文献笔记。

## Command

```bash
paperforge sync
```

## 说明

`paperforge sync` 是 `selection-sync` 和 `index-refresh` 的统一入口：

1. **selection-sync 阶段**：检测 Zotero JSON 中的新条目，创建 library-records
2. **index-refresh 阶段**：基于 library-records 和 Zotero 元数据生成正式文献笔记

自动读取 `paperforge.json` 定位 exports 目录、control 目录和 literature 目录。

如需使用 Python 直接调用（备选方式）：

```bash
python -m paperforge sync --vault .
```

### 常用选项

| 选项 | 说明 |
|------|------|
| `--dry-run` | 预览变更，不实际写入文件 |
| `--domain <DOMAIN>` | 仅同步指定领域（如 `骨科`） |
| `--selection` | 仅执行 selection-sync 阶段 |
| `--index` | 仅执行 index-refresh 阶段 |
| `--vault <PATH>` | 指定 Vault 根目录（默认当前目录） |

### 分阶段执行

仅同步 Zotero 到 library-records：

```bash
paperforge sync --selection
```

仅根据现有 library-records 生成正式笔记：

```bash
paperforge sync --index
```

预览同步结果（不实际写入）：

```bash
paperforge sync --dry-run
```

按领域过滤同步：

```bash
paperforge sync --domain 骨科
```
