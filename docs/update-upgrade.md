# 更新与升级

---

## 插件更新

Obsidian 社区插件浏览器自动更新。BRAT 安装用户同样自动检测更新。

## Python Core 更新与修复

Core 的环境生命周期由终端中的独立 CLI 管理，Obsidian 插件只报告状态并读取 runtime pointer。

将 `<NEW_PLUGIN_VERSION>` 替换为已安装插件的新版本，并使用同一个 Python 3.11+ 解释器：

```bash
python -m pip install --user --upgrade "paperforge==<NEW_PLUGIN_VERSION>"
python -m paperforge runtime update --expected-version <NEW_PLUGIN_VERSION>
```

如果 Runtime 损坏或依赖缺失，运行：

```bash
python -m paperforge runtime repair --expected-version <PLUGIN_VERSION>
```

更新或修复后，在 Obsidian 设置中刷新 Runtime 状态。插件不执行 pip、venv、Core 更新或修复。

## 备份

更新前建议备份：
- `.env`（API key）
- `Resources/` 目录（文献笔记）
- `System/PaperForge/ocr/`（OCR 结果）

## 迁移指南

大版本升级详见：
- [MIGRATION-v1.2.md](MIGRATION-v1.2.md) — v1.1 -> v1.2
- [MIGRATION-v1.4.md](MIGRATION-v1.4.md) — v1.3 -> v1.4

---

相关问题见 [故障排除](troubleshooting.md)。
