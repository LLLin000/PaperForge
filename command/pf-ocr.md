# /pf-ocr

## Purpose

处理 library-records 中 `do_ocr: true` 的 PDF OCR 队列。

`paperforge ocr` 会自动读取 `paperforge.json` 定位 ocr 目录和 worker 脚本，运行 OCR 并自动诊断结果。

## CLI Equivalent

```bash
paperforge ocr
```

如需使用 Python 直接调用（备选方式）：

```bash
python -m paperforge ocr --vault .
```

## Prerequisites

- [ ] library-record 中 `do_ocr: true` 已设置
- [ ] PDF 附件存在（`has_pdf: true`）
- [ ] PaddleOCR API Key 已配置（`.env` 中 `PADDLEOCR_API_TOKEN`）
- [ ] 网络连接正常（可访问 PaddleOCR 服务）
- [ ] `paperforge.json` 配置正确（路径解析无误）

## Arguments

| 参数 | 必需 | 说明 |
|------|------|------|
| `--diagnose` | 否 | 仅诊断配置，不上传 PDF |
| `--key <KEY>` | 否 | 仅处理指定 Zotero key 的文献 |
| `--vault <PATH>` | 否 | 指定 Vault 根目录（默认当前目录） |
| `--live` | 否 | 与 `--diagnose` 联用，执行实时 PDF 测试 |

### 诊断模式

验证 OCR 配置 before queueing jobs：

```bash
paperforge ocr --diagnose
```

执行完整诊断（含实时 PDF 测试）：

```bash
paperforge ocr --diagnose --live
```

### 诊断等级

| 等级 | 检查项 | 失败含义 |
|------|--------|---------|
| L1 | API token 存在性 | `PADDLEOCR_API_TOKEN` 缺失或为空 |
| L2 | URL 可达性 | 无法连接 PaddleOCR 服务 |
| L3 | API 格式验证 | 服务可达但响应格式异常 |
| L4 | 实时 PDF 往返 | 完整提交和结果获取失败 |

> Exit code `0` = 所有检查通过。Exit code `1` = 至少一项检查失败。

## Example

```bash
# 处理所有标记 do_ocr: true 的文献
paperforge ocr

# 仅处理指定文献
paperforge ocr --key ABCDEFG

# 诊断模式（不实际运行）
paperforge ocr --diagnose

# 完整诊断（含实时测试）
paperforge ocr --diagnose --live

# 指定 Vault 目录
paperforge ocr --vault /path/to/vault
```

## Output

OCR 完成后，每个文献生成以下文件：

```
<system_dir>/PaperForge/ocr/<key>/
├── fulltext.md        # 提取的全文（含 `<!-- page N -->` 分页标记）
├── images/            # 自动切割的图表图片
├── meta.json          # OCR 元数据（含 ocr_status）
└── figure-map.json    # 图表索引（自动生成）
```

`meta.json` 中的 `ocr_status` 字段：
- `pending` — 等待处理
- `processing` — 正在处理
- `done` — 完成
- `failed` — 失败

## Error Handling

### API Token 缺失（L1 失败）
- **表现**：`PADDLEOCR_API_TOKEN` 未设置或为空
- **解决**：在 `.env` 文件中添加 `PADDLEOCR_API_TOKEN=your_token_here`

### 服务不可达（L2 失败）
- **表现**：无法连接 PaddleOCR 服务
- **解决**：检查网络连接，确认服务 URL 配置正确

### PDF 上传失败（L4 失败）
- **表现**：PDF 提交后未返回结果
- **解决**：检查 PDF 文件是否损坏，确认文件大小未超过限制

### OCR 状态卡住
- **表现**：`ocr_status` 长期显示 `processing`
- **解决**：检查 `<system_dir>/PaperForge/ocr/<key>/meta.json` 中的错误信息，重新设置 `do_ocr: true` 后再次运行

## Platform Notes

### OpenCode

> `/pf-ocr` 是 **CLI 命令**，Agent 层不直接提供 `/pf-ocr` 聊天命令。
> 
> 用户需要：
> 1. 在 Obsidian 中将 library-record 的 `do_ocr` 设为 `true`
> 2. 在终端运行 `paperforge ocr`
> 3. 或在 Agent 对话中要求 Agent 执行上述步骤

### Codex

> **Future**：计划支持。预计通过 API 调用实现类似功能。

### Claude Code

> **Future**：计划支持。预计通过工具调用实现类似功能。

## See Also

- [pf-sync](pf-sync.md) — 文献同步（生成 library-records）
- [pf-deep](pf-deep.md) — 深度精读（依赖 OCR 结果）
- [AGENTS.md](../AGENTS.md) — 完整使用指南、架构说明、常见问题
- [docs/COMMANDS.md](COMMANDS.md) — 命令总览与矩阵
