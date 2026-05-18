# PaperForge 故障排除

---

## 插件无法加载

确认 `.obsidian/plugins/paperforge/` 下有 `main.js`、`manifest.json`、`styles.css`。

如果从旧版本升级：删除整个 `paperforge` 插件文件夹，通过社区插件浏览器重新安装。

打开开发者控制台（`Ctrl+Shift+I`）查看红色错误信息。

---

## "Sync Runtime" 不更新版本

插件可能调用了和终端不同的 Python。检查设置面板中的 Python Path。

如果仍不行，使用 `--no-cache-dir` 避开 pip 缓存。

确认 `https://github.com/LLLin000/PaperForge` 可访问。

---

## OCR 一直 pending

1. 确认 `.env` 中有 `PADDLEOCR_API_TOKEN`
2. 运行 `paperforge ocr --diagnose` 检查接口连通性
3. 如果 PDF 路径有问题，运行 `paperforge repair --fix-paths`

---

## 同步后没有生成笔记

1. Zotero 的 Better BibTeX 自动导出配好了吗？JSON 文件在 `exports/` 下？
2. 运行 `paperforge doctor` 定位失败步骤

---

## /pf-deep 无反应

前置条件：`ocr_status: done` 且 `analyze: true`。

确认队列就绪：
```bash
paperforge deep-reading --verbose
```

Agent 必须能访问 vault，确认 Agent 配置路径正确。

---

## Base 视图中 pdf_path 显示绝对路径

Obsidian 渲染问题，数据实际是相对路径。不影响功能。

---

## 命令参考

```bash
paperforge status          # 查看系统状态
paperforge doctor          # 验证安装配置
paperforge repair --fix    # 修复状态分歧
```

更多见 [命令参考](COMMANDS.md)。
