# Better BibTeX 配置指南

## 什么是 Better BibTeX

Better BibTeX (BBT) 是一个 Zotero 插件，用于生成和管理 citation key，并支持自动导出 JSON 格式的文献库。

## 为什么需要 BBT

PaperForge 通过 BBT 的 JSON 导出功能获取文献信息：
- citation key（zotero_key）
- 标题、作者、年份
- DOI、期刊、摘要
- PDF 附件路径

没有 BBT 导出，selection-sync 无法检测到 Zotero 中的新文献。

---

## 配置步骤

### Step 1: 安装 Better BibTeX 插件

1. 打开 Zotero
2. 进入 Edit → Preferences → Plugins
3. 搜索 "Better BibTeX"
4. 安装并重启 Zotero

### Step 2: 配置自动导出

1. Zotero → Edit → Preferences → Better BibTeX
2. 勾选 **"Keep updated"**（保持更新）—— 这会让 Zotero 在每次添加/修改文献时自动更新 JSON 文件
3. 选择导出格式：**Better BibLaTeX** 或 **Better BibTeX**（二者皆可）
4. 导出路径设置为：
   ```
   {你的Vault路径}/{system_dir}/PaperForge/exports/library.json
   ```
   其中 `{system_dir}` 默认是 `99_System`，可以通过 `paperforge.json` 自定义。

   **完整路径示例（Windows）：**
   ```
   D:\MyVault\99_System\PaperForge\exports\library.json
   ```

   **完整路径示例（macOS/Linux）：**
   ```
   /Users/name/MyVault/99_System/PaperForge/exports/library.json
   ```

5. 点击 OK，JSON 文件会自动生成并保持同步

### Step 3: 验证配置

1. 在 Zotero 中手动触发一次导出（右击收藏夹 → Export...）
2. 确认 JSON 文件已生成且包含文献数据
3. 运行验证命令：
   ```bash
   paperforge doctor
   ```
   检查输出中的 **"BBT 导出"** 部分，确认显示 `[PASS]`

---

## 使用 paperforge doctor 验证

```bash
paperforge doctor
```

输出示例（正常情况）：
```
[PASS] BBT 导出 — library.json 正常 (25 条)
```

输出示例（有问题）：
```
[FAIL] BBT 导出 — library.json 不存在
修复步骤:
  - BBT 导出: 在 Zotero Better BibTeX 设置中配置导出路径
```

---

## 常见问题

### Q: 导出路径填什么？

A: 完整路径 = `{Vault根目录}/{system_dir}/PaperForge/exports/library.json`

示例：`D:\MyVault\99_System\PaperForge\exports\library.json`

如果不确定 system_dir 是什么，运行 `paperforge paths` 查看。

### Q: "Keep updated" 是什么？

A: 勾选后，每次添加/修改文献时 Zotero 会自动更新 JSON 文件。**强烈建议勾选**，否则需要手动导出。

### Q: JSON 文件是空的怎么办？

A: 检查以下几点：
1. 确认 Zotero 中有文献
2. 确认导出了 PDF 附件的文献（没有 PDF 的文献可能不会被某些 BBT 格式导出）
3. 检查 Zotero → Better BibTeX preferences 中的导出格式设置

### Q: citation key 是什么？

A: citation key 是文献的唯一标识符，例如 `Smith2024AI`。BBT 根据作者、年份、标题自动生成。PaperForge 用它作为 `zotero_key` 来关联文献。

### Q: BBT 导出的 JSON 格式是什么样的？

A: JSON 是一个数组，每个元素包含文献元数据：
```json
[
  {
    "key": "Smith2024AI",
    "title": "Example Paper Title",
    "authors": [{"family": "Smith", "given": "John"}],
    "year": 2024,
    "DOI": "10.xxxx/xxxxx",
    ...
  },
  ...
]
```

### Q: 可以在多台电脑上使用同一个导出路径吗？

A: 不建议。JSON 导出路径应该指向**本地 vault 目录**，由 Zotero 自动维护。如果使用网络共享路径，可能导致文件锁定或同步问题。
