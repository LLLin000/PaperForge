# PaperForge 使用教程

> 面向终端用户。如果你刚安装完 PaperForge，从这里开始。

---

## 1. 安装后检查

1. Obsidian 已打开当前 Vault
2. PaperForge 插件已在设置中启用
3. Python 运行时已确认（设置面板 --> 验证）

---

## 2. 配置 Better BibTeX 自动导出

1. 打开 Zotero
2. 对你要同步的文献库或分类右键 -> `导出...`
3. 格式选：**Better BibTeX JSON**
4. 勾选 **"Keep updated"**
5. 保存到：`{你的Vault路径}/<system_dir>/PaperForge/exports/`

> system_dir 默认是 `System`，例如保存到 `MyVault/System/PaperForge/exports/library.json`

---

## 3. 第一次同步

打开 Dashboard（`Ctrl+P` -> `PaperForge: Open Main Panel`），点击 **Sync Library**。

或者终端执行：
```bash
paperforge sync
```

完成后，正式文献笔记出现在 `Resources/Literature/<领域>/` 下。

---

## 4. 触发 OCR

在正式笔记的 frontmatter 里把 `do_ocr` 改为 `true`，然后运行：

```bash
paperforge ocr
```

OCR 结果保存在 `System/PaperForge/ocr/<key>/` 下，包括全文文本和图表。

---

## 5. 深度精读

OCR 完成后，把 formal note 的 `analyze` 改为 `true`。

确认就绪：
```bash
paperforge deep-reading
```

在 Agent 中输入 `/pf-deep <zotero_key>`，Agent 会执行 Keshav 三阶段精读，结果直接写入 formal note 的 `## 精读` 区域。

---

## 6. 文献问答

不强制 OCR。直接输入 `/pf-paper <zotero_key>` 进入交互式问答。

---

## 7. 日常路径

```
添加文献到 Zotero
  -> BBT 自动导出到 exports/
  -> 点 Sync
  -> 标记 do_ocr: true
  -> 运行 OCR
  -> 标记 analyze: true
  -> /pf-deep <key>
  -> /pf-paper <key>
```

---

## 8. 相关文档

- [命令参考](COMMANDS.md) — 所有 CLI 和 Agent 命令速查
- [故障排除](troubleshooting.md) — 常见问题
- [更新指南](update-upgrade.md) — 如何升级 PaperForge
