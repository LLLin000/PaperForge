---
name: pf-ocr
description: Process the PDF OCR queue for formal notes marked do_ocr: true. Uploads PDFs to PaddleOCR API and extracts fulltext with figures.
allowed-tools: [Bash]
---

# /pf-ocr

## Purpose

处理正式笔记 frontmatter 中 `do_ocr: true` 的 PDF OCR 队列。

`paperforge ocr` 会自动读取 `paperforge.json` 定位 ocr 目录和 worker 脚本，运行 OCR 并自动诊断结果。

## CLI Equivalent

```bash
paperforge ocr
```

## Prerequisites

- [ ] formal note frontmatter 中 `do_ocr: true` 已设置
- [ ] PDF 附件存在（`has_pdf: true`）
- [ ] PaddleOCR API Key 已配置（`.env` 中 `PADDLEOCR_API_TOKEN`）
- [ ] 网络连接正常（可访问 PaddleOCR 服务）

## Arguments

| 参数 | 必需 | 说明 |
|------|------|------|
| `--diagnose` | 否 | 仅诊断配置，不上传 PDF |
| `--key <KEY>` | 否 | 仅处理指定 Zotero key 的文献 |
| `--vault <PATH>` | 否 | 指定 Vault 根目录（默认当前目录） |
| `--live` | 否 | 与 `--diagnose` 联用，执行实时 PDF 测试 |

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
├── fulltext.md        # 提取的全文（含 <!-- page N --> 分页标记）
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
- `PADDLEOCR_API_TOKEN` 未设置 → 在 `.env` 文件中添加

### 服务不可达（L2 失败）
- 无法连接 PaddleOCR → 检查网络连接

### PDF 上传失败（L4 失败）
- PDF 提交后未返回结果 → 检查 PDF 文件是否损坏

### OCR 状态卡住
- `ocr_status` 长期显示 `processing` → 重新设置 `do_ocr: true` 后再次运行

## See Also

- [pf-sync](pf-sync.md) — 文献同步（生成正式笔记）
- [pf-deep](pf-deep.md) — 深度精读（依赖 OCR 结果）
