# PaperForge Lite 安装与配置指南

> 本文档是 [setup_wizard.py](../setup_wizard.py) 的补充说明。如果 TUI 向导中的文字指引不够直观，请参考本页的详细步骤。

---

## 第一步：安装 Zotero

Zotero 是免费的文献管理软件，用于收集、组织和引用文献。

### 下载安装

1. 访问 https://www.zotero.org/download/
2. 下载对应系统的安装包
3. 按向导完成安装

### 验证安装

安装完成后，确认可以正常打开 Zotero 主界面。

---

## 第二步：安装 Better BibTeX 插件

Better BibTeX (BBT) 是 Zotero 的插件，用于生成可供 PaperForge 读取的 JSON 导出。

### 下载插件

1. 访问 https://retorque.re/zotero-better-bibtex/
2. 找到最新版本的 `.xpi` 文件并下载

### 安装到 Zotero

```
Zotero
  └─ 工具(Tools)
       └─ 插件(Plugins)
            └─ [齿轮图标]
                 └─ Install Plugin From File...
                      └─ [选择下载的 .xpi 文件]
                           └─ [重启 Zotero]
```

**Windows 详细步骤：**

1. 打开 Zotero
2. 菜单栏点击 `工具(Tools)` → `插件(Plugins)`
3. 在插件管理器右上角点击齿轮图标
4. 选择 `Install Plugin From File...`
5. 浏览到下载的 `.xpi` 文件，选中后点击打开
6. 提示安装成功，重启 Zotero

**macOS 详细步骤：**

1. 打开 Zotero
2. 菜单栏 `Zotero` → `Preferences` → `Plugins`
3. 点击齿轮图标 → `Install Plugin From File...`
4. 选择 `.xpi` 文件
5. 重启 Zotero

### 验证安装

重启后，打开 `工具(Tools)` 菜单，确认出现 `Better BibTeX` 子菜单。

---

## 第三步：配置 Better BibTeX 自动导出

这是最关键的一步。每个导出的 JSON 文件将对应一个 Obsidian Base 视图。

### 理解 JSON 与 Base 的关系

```
你的 Zotero 收藏夹结构：
  ├── 骨科
  ├── 运动医学
  └── 综述

Better BibTeX 导出后：
  ├── exports/骨科.json
  ├── exports/运动医学.json
  └── exports/综述.json

PaperForge 自动生成：
  ├── 05_Bases/骨科.base
  ├── 05_Bases/运动医学.base
  └── 05_Bases/综述.base
```

**规则：一个 JSON 文件 = 一个 Base 视图 = 一个文献分类**

### 配置自动导出

**步骤一：设置自动导出模式**

```
Zotero
  └─ 编辑(Edit)
       └─ 首选项(Preferences)
            └─ Better BibTeX（左侧边栏）
                 └─ [勾选] Automatic export: On Change
```

**步骤二：导出第一个 JSON**

```
Zotero
  └─ 文件(File)
       └─ 导出库(Export Library...)
            ├─ 格式(Format): Better BibLaTeX  ★ 重要！不是 BibTeX
            ├─ 勾选 [Keep updated]            ★ 必须勾选
            ├─ 文件名: 骨科.json              ★ 建议用中文名，好识别
            └─ 保存位置: {你的Vault}/99_System/LiteraturePipeline/exports/
                 └─ [保存]
```

**Windows 详细步骤：**

1. 在 Zotero 左侧选择你要导出的收藏夹（如"骨科"）
2. 菜单栏 `文件(File)` → `导出库(Export Library...)`
3. 格式下拉框选择 `Better BibLaTeX`
4. 勾选右下角的 `Keep updated`
5. 点击 `...` 选择保存位置，导航到：
   ```
   {你的Vault根目录}/99_System/LiteraturePipeline/exports/
   ```
6. 文件名填写收藏夹名称，如 `骨科.json`
7. 点击保存

**重复上述步骤**，为每个需要管理的收藏夹导出 JSON。

### 验证导出

导出完成后，检查文件：

```bash
ls 99_System/LiteraturePipeline/exports/
# 应该看到: 骨科.json  运动医学.json  ...
```

打开任意 JSON 文件，确认包含类似以下结构：

```json
[
  {
    "citationKey": "XXXXX",
    "title": "论文标题",
    "year": 2024,
    ...
  }
]
```

---

## 第四步：运行 PaperForge 工作流

完成上述配置后，回到 Vault 根目录，运行：

```bash
# 1. 检测 Zotero 新条目，创建状态记录
python pipeline/worker/scripts/literature_pipeline.py --vault . selection-sync

# 2. 生成正式 Obsidian 笔记
python pipeline/worker/scripts/literature_pipeline.py --vault . index-refresh
```

此时你应该看到：
- `03_Resources/LiteratureControl/library-records/` 下出现状态记录文件
- `03_Resources/Literature/` 下出现正式笔记
- `05_Bases/` 下出现 Base 视图文件（每个 JSON 对应一个）

---

## 常见问题

### Q: 导出格式选错成 BibTeX 怎么办？

重新导出，务必选择 `Better BibLaTeX`。BibTeX 格式缺少 citation key 等必要字段。

### Q: JSON 文件很大，导出慢？

正常。大型文献库的 JSON 可能几十 MB，导出需要几十秒。勾选 `Keep updated` 后，后续只有新增/修改的条目会更新。

### Q: 可以导出多个收藏夹吗？

可以，而且推荐这样做。每个收藏夹导出一个 JSON，PaperForge 会为每个 JSON 创建一个独立的 Base 视图。例如：
- `骨科.json` → `骨科.base`
- `运动医学.json` → `运动医学.base`

### Q: 如何添加新的收藏夹？

1. 在 Zotero 中创建新收藏夹并添加文献
2. 按照步骤三导出新的 JSON
3. 重新运行 `selection-sync` 和 `index-refresh`

### Q: 修改了收藏夹名称？

1. 在 Zotero 中修改收藏夹名称
2. 重新导出 JSON（可以覆盖原文件或导出为新文件）
3. 如果导出了新文件名的 JSON，旧文件可以手动删除
4. 重新运行 `selection-sync` 和 `index-refresh`

---

## 下一步

配置完成后，阅读 `AGENTS.md` 了解完整工作流，或运行 TUI 向导：

```bash
python setup_wizard.py --vault .
```

---

*PaperForge Lite | 安装指南*
