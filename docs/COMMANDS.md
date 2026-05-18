# PaperForge 命令参考

> 所有 CLI 命令和 Agent 命令速查。

---

## 命令矩阵

| Agent 命令 | CLI 命令 | 用途 | 前置条件 |
|-----------|---------|------|---------|
| `/pf-sync` | `paperforge sync` | 同步 Zotero，生成正式笔记 | BBT JSON 导出 |
| `/pf-ocr` | `paperforge ocr` | PDF OCR 文本与图表提取 | `do_ocr: true` |
| `/pf-status` | `paperforge status` | 查看系统状态 | 配置完成 |
| `/pf-deep <key>` | `paperforge deep-reading` | 三阶段精读 | OCR done + `analyze: true` |
| `/pf-paper <key>` | — | 文献问答 | 正式笔记存在 |

---

## CLI 命令

### `paperforge sync`

```bash
paperforge sync                 # 完整同步
paperforge sync --dry-run       # 预览
paperforge sync --rebuild-index # 强制重建索引
paperforge sync --json          # JSON 输出
```

### `paperforge ocr`

```bash
paperforge ocr                  # 处理队列
paperforge ocr --key ABCDEFG    # 处理指定文献
paperforge ocr --diagnose       # 诊断模式
paperforge ocr --json           # JSON 输出
```

### `paperforge status`

```bash
paperforge status               # 完整状态
paperforge status --json        # JSON 输出
```

### `paperforge doctor`

```bash
paperforge doctor               # 验证安装配置
paperforge doctor --json        # JSON 输出
```

### `paperforge repair`

```bash
paperforge repair               # 扫描分歧（dry-run）
paperforge repair --fix          # 修复
paperforge repair --fix-paths    # 修复 PDF 路径
paperforge repair --json         # JSON 输出
```

### `paperforge deep-reading`

```bash
paperforge deep-reading          # 查看精读队列
paperforge deep-reading --verbose # 含修复指令
```

### `paperforge embed`

```bash
paperforge embed build           # 构建向量索引
paperforge embed build --resume  # 续建
paperforge embed status          # 查看状态
paperforge embed stop            # 停止构建
```

### `paperforge memory`

```bash
paperforge memory build          # 构建 memory DB
paperforge memory status         # 查看状态
```

### `paperforge search`

```bash
paperforge search "<query>" --json
paperforge search "PEMF" --domain 骨科 --ocr done --year-from 2020
```

### `paperforge runtime-health`

```bash
paperforge runtime-health --json
```

---

## 相关文档

- [使用教程](getting-started.md)
- [故障排除](troubleshooting.md)
- [更新指南](update-upgrade.md)
