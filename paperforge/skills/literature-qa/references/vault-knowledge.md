# PaperForge Vault 结构知识

本文件是 Agent 理解 PaperForge Vault 的共享参考。精读、问答、检索等所有工作流都先从这里获取基础概念。

## 浏览场景

用户说"看一下库里内容"、"看一下文献库"、"库里有什么"、"浏览文献"时，Agent 展示 Vault 概况：

1. 跑 `paths` 获取 `literature_dir` 和 `index_path`
2. 列出 `literature_dir` 下所有 domain（领域文件夹名）
3. 读 formal-library.json，统计每个 domain：论文总数、OCR 完成数、无 PDF 数
4. 输出概览：

```
Vault: D:\...\Vault
Domains: 骨科 (550 papers, 520 OCR done), 运动医学 (263 papers, 129 OCR done)
```

如果用户继续问具体内容，Agent 加载 [paper-search.md](paper-search.md) 搜索。

---

## 1. 获取路径

所有路径从 `paperforge.json` 配置派生。Agent 不硬编码。每次需要路径时先跑：

```
python -m paperforge.worker.paper_resolver paths --vault .
```

返回：

```json
{
  "vault_root": "D:\\...\\Vault",
  "index_path": "D:\\...\\System\\PaperForge\\indexes\\formal-library.json",
  "literature_dir": "D:\\...\\Resources\\Literature",
  "ocr_dir": "D:\\...\\System\\PaperForge\\ocr"
}
```

## 2. 目录结构速览

```
{vault_root}/
├── {resources_dir}/
│   └── {literature_dir}/              ← 正式文献笔记
│       ├── 骨科/                       ← 领域 (domain)
│       │   ├── ABC12345 - Paper Title/ ← workspace 目录
│       │   │   ├── ABC12345 - Paper Title.md  ← 正式笔记 (含 frontmatter)
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

## 3. Domain 与 Collection

- **Domain**（领域）= `literature_dir` 下的子目录名，如 `骨科`、`运动医学`
- **Collection**（Zotero 收藏夹）= BBT JSON 里的分组，映射关系在 `{system_dir}/PaperForge/config/domain-collections.json`
- 每篇论文属于一个 domain，可能有子分类 (`collection_path`)

Domain 列表可以直接 `Get-ChildItem {literature_dir} -Directory` 获取，不需要读配置。

## 4. formal-library.json — 核心索引

位置：`paths` 返回的 `index_path`

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

## 5. Workspace 结构

每篇论文的 workspace 目录：

```
{literature_dir}/{domain}/{KEY} - {Title}/
├── {KEY} - {Title}.md       ← 正式笔记 (frontmatter + 精读内容)
├── fulltext.md                ← OCR 全文 (含 <!-- page N --> 分页标记)
├── paper-meta.json            ← 生命周期追踪
└── ai/                         ← Agent 工作区
    ├── discussion.md           ← /pf-paper 讨论记录
    └── discussion.json         ← 结构化 Q&A
```

## 6. 如何读论文内容

| 你要做什么         | 操作                                                                                                                                   |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| 看论文元数据       | 读 formal-library.json 或正式笔记 frontmatter                                                                                         |
| 读 OCR 全文        | 读 workspace 的 `fulltext.md`（如果 `ocr_status == "done"`）                                                                            |
| 读精读笔记         | 读正式笔记的 `## 🔍 精读` 区域                                                                                                           |
| 按 key 查完整路径  | `python -m paperforge.worker.paper_resolver resolve-key <KEY> --vault .`                                                                |
| 按 DOMAIN 搜关键词 | `python -m paperforge.worker.paper_resolver search --title "..." --domain "..." --vault .`<br>或直接 grep formal-library.json 的 title |

## 7. 论文定位

详见 [paper-resolution.md](paper-resolution.md)。定位论文后，用返回的 workspace 路径找到 `fulltext.md` 读内容。
