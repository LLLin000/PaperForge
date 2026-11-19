# PaperForge 使用教程

> 面向终端用户。如果你刚安装完 PaperForge，从这里开始。

---

## 1. 安装与运行前检查（当前 `v2.0.0rc6`）

> [!NOTE]
> PaperForge 会在用户主目录 `.paperforge/runtime/` 下维护完全隔离的受管 Python 运行时并写入 `pointer.json`，不会污染系统包。若桌面端尚未安装本机 Python 3.11+，在 Obsidian 设置 → PaperForge 向导点击安装时会自动启用便携 `uv` 下载托管 Python 3.12 并完成引导（也支持按下面终端命令显式执行；详见 [跨平台安装与热更架构设计](INSTALL-AND-UPDATE-ARCHITECTURE.md)）。

1. 桌面端点击向导一键安装（推荐，自动处理零 Python 环境与 `uv` 缓存），**或者**在已安装 Python 3.11+ 的终端显式安装受管运行时：
   ```bash
   python -m pip install --user "paperforge==2.0.0rc6"
   python -m paperforge runtime install --expected-version 2.0.0rc6
   ```
   （将 `2.0.0rc6` 替换为插件设置面板展示的当前版本号）
2. Obsidian 已打开当前 Vault，且 PaperForge 插件已在社区插件设置中启用
3. Python 运行时已确认就绪（Obsidian 设置面板 → PaperForge Control Center → 验证通过 `pointer.json` 隔离环境）

---

## 2. 配置 Better BibTeX 自动导出

1. 打开 Zotero
2. 对你要同步的文献库或分类右键 -> `导出...`
3. 格式选：**Better BibTeX JSON**
4. 勾选 **"Keep updated"**
5. 保存到向导自动创建的导出目录（新库默认为 `{你的Vault路径}/.paperforge/exports/`；旧库升级为 `{你的Vault路径}/System/PaperForge/exports/`）

> 💡 新建 Vault 默认将引擎缓存、OCR 中间文件与内部 `fulltext.md` 收归隐藏目录 `.paperforge/`，避免上万个中间文件拖慢 Obsidian 索引与启动速度；如果你正在使用旧版 `System/PaperForge/` 目录，可随时运行 `paperforge migrate-storage` 一键平滑迁移。

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

OCR 结果保存在隐藏引擎目录 `.paperforge/ocr/<key>/`（或旧版 `System/PaperForge/ocr/<key>/`）下，包括供检索与 Agent 使用的全文文本，并将裁切好的独立命名图表 `assets/<key>_figure_*.jpg` 同步到正式笔记工作区；`fulltext.md` 不再冗余复制到可见文献文件夹。

---

## 5. 阅读原版 PDF 并无损批注（Obsidian 内置阅读器）

在 Dashboard 或单篇文献面板点击 **打开 PDF**，即可直接在 Obsidian 标签页中使用内置 **PaperForge PDF Annotator**（基于原生 `loadPdfJs()`）：

- **划线高亮与科研意图标注**：支持选区高亮并标注为 `evidence`（💡 核心证据）、`question`（❓ 存疑待查）、`method`（🧪 方法细节）、`quote`（✍️ 可引述）
- **框选截图**：框选图表面板或公式区域自动生成独立截图 `assets/<key>_ann_<id>.jpg` 并绑定 OCR 章节与图表上下文
- **随文献永存、原 PDF 零改动**：全部批注保存在文献工作区 `<workspace>/annotations.jsonl`，严格不修改原始 PDF 字节，支持一键晋升为可检索的 `reading-log` 证据卡，并在执行 `/pf-deep` 时自动喂给 AI Agent 优先解答你标记的疑问

---

## 6. 深度精读

OCR 完成后，把 formal note 的 `analyze` 改为 `true`。

确认就绪：

```bash
paperforge deep-reading
```

在 Agent 中输入 `/pf-deep <zotero_key>`，Agent 会执行 Keshav 三阶段精读，结果直接写入 formal note 的 `## 精读` 区域。

---

## 7. 文献问答

不强制 OCR。直接输入 `/pf-paper <zotero_key>` 进入交互式问答。

---

## 8. 日常路径

```
添加文献到 Zotero
  -> BBT 自动导出到 exports/
  -> 点 Sync
  -> Obsidian 内置 PDF 阅读器划线/框选批注 (annotations.jsonl)
  -> 标记 do_ocr: true
  -> 运行 OCR
  -> 标记 analyze: true
  -> /pf-deep <key>
  -> /pf-paper <key>
```

---

## 9. 相关文档

- [命令参考](COMMANDS.md) — 所有 CLI 和 Agent 命令速查
- [故障排除](troubleshooting.md) — 常见问题
- [更新指南](update-upgrade.md) — 如何升级 PaperForge
