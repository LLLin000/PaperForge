# Orphan Paper Cleanup (Prune) — Design Spec

> **Status:** Draft | **Date:** 2026-05-18
> **Review:** Pending
> **Depends on:** embedding-package-extraction (embedding/ package exists)

## Motivation

Sync rebuilds `formal-library.json` from current BBT exports. Papers removed from Zotero disappear from the index, but their physical files remain permanently:

| Artifact | After sync | Problem |
|---|---|---|
| Workspace dir (note + ai/) | Orphan | "最近讨论"卡片仍可访问已删论文 |
| OCR dir (`System/PaperForge/ocr/{key}/`) | Orphan | 占空间 |
| Note `.md` | Orphan | 用户仍能在 Obsidian 中看到 |
| ChromaDB vectors | Orphan | 除非 `embed build --force` 全量重建 |
| Formal-library index | Clean (rebuilt) | — |
| Memory DB (SQLite) | Clean (rebuilt) | — |

这些孤儿文件会无限堆积，且 `sync` 对其完全沉默。

## Design

### Approach: key-based deletion, post-index-rebuild

核心思路：在 `run_index_refresh()` 末尾（index 已重建后），用新 index 的 key set 扫描工作区，删除不在 set 中的孤儿。

不需要 diff 旧 index，不需要记录历史。新 index 就是真相源。

### Entry point

```python
# sync_service.py 末尾，run_index_refresh() 执行后
prune_orphan_papers(vault, paths, fresh_index)  # 可选
```

### What to delete

For each orphan key `k` (present on filesystem but absent from fresh index):

```
1. rm -rf {literature}/{domain}/{k} - {slug}/      # workspace + ai/ + note
2. rm -rf System/PaperForge/ocr/{k}/                 # OCR fulltext + images
3. delete_paper_vectors(k)                           # ChromaDB 单条删除（非全量重建）
```

以上三者全部删除。

### Safety: key matching

- 从 `{literature}/{domain}/` 下各子目录提取 key：`{子目录名}.split(" - ")[0]`
- 如果该 key 不在新鲜 index 的 key set 中 → 孤儿
- 只扫 `{literature}/{domain}/` 下一级（`{key} - {slug}/` 结构的目录），不碰未知目录
- 遇到无法 split 出 key 的目录 → 跳过（不是 PaperForge 管理的）

### Deletion order

1. 先删除 OCR 目录（最安全，可随时重新 OCR）
2. 再删除 workspace 目录
3. 最后删除 ChromaDB 向量（ID 匹配）

顺序保证：如果任何一步失败，上一步已经删了的东西不会回滚，但已删的部分不致命（key 不在 index 中，不会产生冲突）。

### `--prune` flag on sync

```bash
paperforge sync --prune            # dry-run：打印将删除的文件列表，不实际删除
paperforge sync --prune --force    # 实际执行删除
```

两步确认机制：
- `--prune` 只输出 affected keys 列表
- `--prune --force` 实际执行 `rmtree` + `delete_paper_vectors`

### Standalone command

```bash
paperforge prune            # dry-run
paperforge prune --force    # 实际删除
```

作为独立 CLI 命令注册，方便手动调用。

### Logging

```
[PRUNE] Deleted OCR dir       abc12345  → System/PaperForge/ocr/abc12345/
[PRUNE] Deleted workspace     abc12345  → Resources/Literature/CS/abc12345 - Old Title/
[PRUNE] Deleted vectors       abc12345  → 47 chunks removed
```

记录在 `sync` 的标准输出和 `project-log` 中。

## What is NOT covered

- **Vector DB 的 `--resume` 模式不受影响**：prune 只删除 index 中没有的 paper 的向量，重建时 resume 遍历 index 中存在的 paper。完全正交。
- **Memory DB 不需要额外操作**：`build_from_index()` 已用新鲜 index 重建。
- **不是 GC/defrag**：不压缩 ChromaDB HNSW 索引，不清理 SQLite WAL。
- **不会误删除在 Zotero 中后来以不同 key 重新添加的 paper**：新 key 不在 old key 的匹配范围内。

## Sequence Diagram

```
sync (--prune --force)
  ├── run_selection_sync()         # BBT 计数
  ├── asset_index.build_index()    # 重建 formal-library.json
  ├── build_from_index()           # 重建 memory DB
  ├── prune_orphan_papers()
  │   ├── 读取新鲜 index → key_set
  │   ├── 遍历 literature/ 目录 → 提取文件系统 key_set
  │   ├── orphan_keys = filesystem - fresh
  │   ├── for key in orphan_keys:
  │   │   ├── rmtree(ocr_dir)         # 跳过如果已不存在
  │   │   ├── rmtree(workspace_dir)   # 跳过如果已不存在
  │   │   └── delete_paper_vectors(key)
  │   └── 打印删除摘要
  └── 标准 status 报告
```

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| 用户意外删除 Zotero 文献后 sync 导致 note 丢失 | 两层保护：(1) `--prune` 是 dry-run；(2) `--force` 才实际删除。用户需显式确认 |
| 文件名格式不匹配导致误删非 PaperForge 目录 | 只处理 `{key} - {slug}` 格式的目录，未知格式跳过 |
| ChromaDB `delete_paper_vectors` 失败 | 打印 warning，不中断流程。OCR 和 workspace 已删，向量残留在下次 `embed build` 时会被 IndexError 发现 |
| 多进程安全（sync 和 embed 同时运行） | prune 只能在 sync 末尾且无其他子进程操作对应 key 时执行。现有 lock 机制足以防护 |
