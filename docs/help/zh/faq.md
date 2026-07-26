# 常见问题

## 为什么文献库显示未就绪？

文献库模块需要三个条件：有效的 Zotero 数据目录路径、保管库中的 BBT JSON 导出文件、以及一次成功的同步运行。

检查 **Setup → 文献库** 阶段以验证路径，确保 Zotero 正在运行且已安装 BBT，然后从 Zotero 重新导出 BBT JSON 文件（`文件 → 导出文献库 → Better BibTeX JSON`）。最后从概览页点击**同步**。

---

## OCR 提取为什么会失败？

OCR 失败通常由以下原因导致：Zotero 中缺少 PDF 附件、PDF 文件损坏、或 PaddleOCR API 配置错误。

在 OCR 工作区查看论文的状态标签——「失败」表示处理出错。尝试对该论文重新运行 OCR。如果持续失败，检查 Setup 中的 PaddleOCR API Key，并确保 Zotero 中存在 PDF 文件。

---

## 如何重建向量索引？

从概览页打开**智能检索**，点击**构建索引**。索引会从头重建，重新嵌入每篇论文的全文。

在以下情况后可能需要重建：新增了大量论文、更改了嵌入模型、或索引标记为过期。构建过程会实时显示进度。

---

## 如何更新 BBT JSON 文件？

PaperForge 使用 Better BibTeX JSON 格式的 Zotero 文献库导出作为论文索引来源。

更新方法：
1. 打开已安装 Better BibTeX 插件的 Zotero。
2. 右键文献库或分类 → **导出文献库…**
3. 选择 **Better BibTeX JSON** 格式。
4. 保存到保管库的配置路径，覆盖已有文件。
5. 在 PaperForge 中，前往概览页点击**同步文献库**。

只有在向 Zotero 添加、删除或修改论文时才需要重新导出。

---

## 如何卸载 PaperForge？

在 **Obsidian 设置 → 第三方插件 → PaperForge** 中禁用插件。要完全移除：删除 `.obsidian/plugins/paperforge/` 插件文件夹以及保管库 System 文件夹中的 PaperForge 运行时目录。

你的 Zotero 数据、PDF 和笔记不会受到 PaperForge 的任何修改，将完整保留。
