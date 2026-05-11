# PaperForge Vault 结构知识

本文件是 Agent 理解 PaperForge Vault 的共享参考。精读、问答、检索等所有工作流都先从这里获取基础概念。

---

## 0. Pre-flight Checklist — 进任何流程前必做

1. **确认 vault 路径** — 找到 `paperforge.json` 的目录
2. **跑 paths 获取实际目录** — `python -m paperforge.worker.paper_resolver paths --vault "$VAULT"`
3. **确认 paths 命令成功** — 拿到 `literature_dir`、`index_path`、`ocr_dir`
4. **记住这些路径** — 后面所有文件读写都用 `paths` 返回的实际值。**禁止将示例路径（如 `D:\...\System\PaperForge`）与 paperforge.json 里的目录名（如 `system_dir: "99_System"`）拼接。** 一切路径完全来自 `paper_resolver paths` 或 `paper_resolver resolve-key` 返回的 JSON。

如果 `paper_resolver` 报错，先解决报错再继续。**绝对不要在没有 paths JSON 的情况下自己通过拼接目录名来猜测路径。**

---

## 浏览场景

用户说"看一下库里内容"、"库里有什么"、"浏览文献库"时：

pf_bootstrap 已经返回了 `domains` 和 `index_summary`。直接展示：

```
Vault: <vault_root>
Domains:
  - 骨科: 550 篇
  - 运动医学: 263 篇
共 813 篇
```

如果用户继续问具体内容，Agent 加载 [paper-search.md](paper-search.md) 搜索。

---

## 1. 目录结构速览

Path 全部由 pf_bootstrap 的 `paths` JSON 提供，不要自己拼。

```
{vault_root}/
├── {resources_dir}/
│   └── {literature_dir}/              ← 正式文献笔记
│       ├── 骨科/                       ← 领域 (domain)
│       │   ├── ABC12345 - Paper Title/ ← workspace 目录
│       │   │   ├── ABC12345.md          ← 正式笔记 (文件名 = key)
│       │   │   ├── fulltext.md               ← OCR 全文
│       │   │   └── ai/                        ← Agent 工作区
│       │   └── ...
│       └── 运动医学/
│           └── ...
├── {system_dir}/
│   └── PaperForge/
│       ├── exports/                   ← Zotero BBT 导出 JSON
│       ├── ocr/{KEY}/                 ← OCR 原始结果 (fulltext.md, images/, meta.json)
│       └── indexes/
│           └── formal-library.json    ← 核心索引
```

## 2. Domain 与 Collection

- **Domain**（领域）= `literature_dir` 下的子目录名，如 `骨科`、`运动医学`
- **Collection**（Zotero 收藏夹）= BBT JSON 里的分组，映射关系在 `{system_dir}/PaperForge/config/domain-collections.json`
- 每篇论文属于一个 domain，可能有子分类 (`collection_path`)

Domain 列表可以直接 `Get-ChildItem {literature_dir} -Directory` 获取，不需要读配置。

## 3. formal-library.json — 核心索引

位置：pf_bootstrap 的 `paths.index_path`

结构：

```json
{
  "items": {
    "ABC12345": {
      "key": "ABC12345",
      "title": "Paper Title",
      "domain": "骨科",
      "year": 2024,
      "doi": "10.xxxx/xxxxx",
      "first_author": "Smith",
      "journal": "Journal of ...",
      "ocr_status": "done",
      "has_pdf": true,
      "collection_path": "子分类名"
    }
  }
}
```

Agent 读这个 JSON 可以按 domain、年份、作者、标题关键词等筛选。

## 4. Workspace 结构

每篇论文的 workspace 目录：

```
{literature_dir}/{domain}/{KEY} - {Title}/
├── {KEY}.md                   ← 正式笔记 (文件名 = key, 标题在 frontmatter title + aliases)
├── fulltext.md                ← OCR 全文 (含 <!-- page N --> 分页标记)
├── paper-meta.json            ← 生命周期追踪
└── ai/                         ← Agent 工作区
    ├── discussion.md           ← /pf-paper 讨论记录
    └── discussion.json         ← 结构化 Q&A
```

## 5. 如何读论文内容

| 你要做什么         | 操作                                                                                                                                   |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| 看论文元数据       | 读 formal-library.json 或正式笔记 frontmatter                                                                                         |
| 读 OCR 全文        | 读 workspace 的 `fulltext.md`（如果 `ocr_status == "done"`）                                                                            |
| 读精读笔记         | 读正式笔记的 `## 🔍 精读` 区域                                                                                                           |
| 按 key 查完整路径  | `$PYTHON -m paperforge.worker.paper_resolver resolve-key <KEY> --vault "$VAULT"`                                                         |
| 按 domain 搜关键词 | `$PYTHON -m paperforge.worker.paper_resolver search --title "..." --domain "..." --vault "$VAULT"`<br>或直接读 formal-library.json      |

## 6. 论文定位

详见 [paper-resolution.md](paper-resolution.md)。定位论文后，用返回的 workspace 路径找到 `fulltext.md` 读内容。
