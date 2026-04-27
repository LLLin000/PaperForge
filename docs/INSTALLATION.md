# PaperForge Lite 快速安装指南

> 详细版教程（含截图和每个步骤的说明）请见 [setup-guide.md](setup-guide.md)。

---

## 前置条件

- Python 3.10+
- Zotero + Better BibTeX 插件
- Obsidian
- PaddleOCR API Key（[申请地址](https://paddleocr.baidu.com)）

---

## 安装（推荐方式：pip）

```powershell
# 1. 安装
pip install git+https://github.com/LLLin000/PaperForge.git

# 2. 运行安装向导
paperforge setup
```

向导会引导你完成 Vault 配置、Zotero 链接、API Key 设置。

---

## Better BibTeX 配置

1. Zotero → Edit → Preferences → Better BibTeX
2. 勾选 **"Keep updated"**
3. 格式：Better BibLaTeX
4. 导出路径：`{你的Vault}/[system_dir]/PaperForge/exports/library.json`
5. 点击 OK

---

## 验证安装

```powershell
paperforge doctor   # 诊断所有组件
paperforge status   # 查看系统状态
```

---

## 下一步

详细使用流程见 [setup-guide.md](setup-guide.md#6-首次使用流程)。
