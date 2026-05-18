# PaperForge 维护者指南

> 面向贡献者和维护者。

---

## 项目结构

```
paperforge/
├── core/           PFResult 契约层
├── adapters/       BBT 解析、frontmatter、路径
├── services/       SyncService 编排
├── worker/         OCR、sync、status、repair
├── memory/         SQLite、ChromaDB、快照
├── commands/       CLI 分发
├── setup/          安装向导
├── schema/         field_registry.yaml
├── doctor/         字段校验
├── plugin/         Obsidian 插件
│   ├── main.js     UI + 快照读取
│   └── src/testable.js  提取的纯函数
└── skills/paperforge/  Agent skill 文件
```

## 架构原则

1. Python 写 canonical 快照，JS 只读
2. CLI 是所有命令的真相源
3. `paperforge.json` 是路径真相源
4. `formal-library.json` 是文献索引真相源

## 版本号

版本只在 `paperforge/__init__.py` 定义。升版本：

```bash
python scripts/bump.py patch
python scripts/bump.py minor
```

自动更新：`__init__.py`、`manifest.json`、`versions.json`、git tag。

## 发布

```bash
python scripts/bump.py patch
git push && git push --tags
gh release create vX.Y.Z \
    --title "vX.Y.Z" \
    --notes "说明" \
    paperforge/plugin/main.js \
    paperforge/plugin/styles.css \
    paperforge/plugin/manifest.json \
    paperforge/plugin/versions.json
```

## 测试

```bash
ruff check --fix paperforge/ && ruff format paperforge/
python -m pytest tests/unit/ tests/cli/ -v --tb=short
cd paperforge/plugin && npx vitest run
```

## i18n

插件文案在 `paperforge/plugin/main.js` 的 `LANG` 对象中。中文 keys 在 `LANG.zh`，英文在 `LANG.en`。代码用 `t('key')` 读取。

## 相关文档

- [架构](ARCHITECTURE.md)
- [命令参考](COMMANDS.md)
- [AGENTS.md](../AGENTS.md)
