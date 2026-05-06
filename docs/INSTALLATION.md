# PaperForge 快速安装指南

> 详细版教程（含截图和每个步骤的说明）请见 [setup-guide.md](setup-guide.md)。

---

## 前置条件

- Python 3.10+
- Zotero + Better BibTeX 插件
- Obsidian
- PaddleOCR API Key（[申请地址](https://paddleocr.baidu.com)）

> 安装向导是**增量式**的：如果你选择的 Vault 或目录里已经有文件，PaperForge 只会创建缺失的目录和文件，不会删除已有内容。

---

## 安装（推荐方式：pip）

```powershell
# 1. 安装
pip install git+https://github.com/LLLin000/PaperForge.git

# 2. 运行安装向导（会把插件文件部署到当前 Vault）
paperforge setup
```

向导会引导你完成 Vault 配置、Zotero 链接、API Key 设置，并把插件文件部署到 `.obsidian/plugins/paperforge/`。

安装向导完成后，才进入 Obsidian 启用插件；启用之前不能打开 Dashboard。

---

## Better BibTeX 配置

这一步在 `paperforge setup` 完成之后再做，因为导出目录要先由安装向导创建。

1. 打开 Zotero
2. 对你要同步的库或分类右键 → `Export...` / `导出...`
3. 格式选择 **Better BibTeX JSON**
4. 勾选 **"Keep updated"**
5. 导出到：`{你的Vault}/[system_dir]/PaperForge/exports/`
6. JSON 文件名会作为 Base 名称，例如：`library.json`、`骨科.json`

---

## 验证安装

```powershell
paperforge status   # 确认 setup 已经把 PaperForge 部署到当前 Vault
```

然后在 Obsidian 中：

1. `Settings -> Community Plugins -> Installed -> PaperForge -> Enable`
2. 按 `Ctrl+P` 搜索 `PaperForge`

之后再执行：

```powershell
paperforge doctor   # 诊断所有组件
```

---

## 下一步

详细使用流程见 [setup-guide.md](setup-guide.md#6-首次使用流程)。
