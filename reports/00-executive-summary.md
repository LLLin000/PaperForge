# Executive Summary — PaperForge PDF Annotation Layer

> ROBCO INDUSTRIES (TM) TERMLINK REPORT
> Status: RESEARCH COMPLETE | DESIGN READY

## The 10 Key Questions Answered

### 1. ZotFlow 哪些设计值得 PaperForge 借鉴？

- **AnnotationJSON schema** — ZotFlow 的 `AnnotationJSON` 接口（id, type, position, sortIndex, color, comment, text, tags 等字段）是经过 production 验证的 Zotero 兼容模型
- **Sync conflict resolution** — 字段级别 diff + version-based optimistic locking + 三种 conflict action（keep-local / accept-remote / mark-conflict）
- **LiquidJS template pipeline** — 模板驱动的 source note 生成可直接复用
- **Dexie/IndexedDB 缓存模式** — 在 Python 端可用 SQLite 等价实现，设计思路一致（syncStatus 追踪、全 raw payload 存储）

### 2. ZotFlow 哪些部分太重，PaperForge 应该避免？

- **内嵌 Zotero reader iframe** — 整个 reader/ 子模块（Zotero PDF.js + Penpal + Comlink），约 2/3 的代码量
- **CodeMirror 6 扩展** — 可编辑区域、锁、comments、citation suggest 等 O(N) 级别的 editor 集成
- **React UI 组件** — TreeView（react-arborist）、Activity Center、settings tab 等
- **完整的自适应同步引擎** — 42,918 行的 sync.ts，涵盖双向 pull/push、冲突检测、批量重试等，对只读场景完全不需要

### 3. 本地解析 Zotero SQLite 是否足够支持只读 annotation sync？

**完全足够。** 所有 annotation 数据存储在 `itemAnnotations` 表 + `items` 表 + `tags` 表 + `itemTags` 表，通过 standard SQL JOIN 可获取全部字段（type, text, comment, color, pageLabel, sortIndex, position JSON, tags, dateModified）。

Zotero 官方文档明确标注 SQLite 可以被外部工具只读提取。

注意点：Zotero 运行时 SQLite 有缓存层，必须先 COPY DB 到临时目录再读，避免锁和不一致。

### 4. Zotero annotation 到 PaperForge annotation 的字段映射

| Zotero 字段               | PaperForge 字段    | 说明                              |
| ------------------------- | ------------------ | --------------------------------- |
| `itemAnnotations.type`    | `type`             | 1→highlight, 2→note, 3→image...  |
| `items.key`               | `zotero_key`       | 8 字符 base32 key                 |
| `itemAnnotations.text`    | `selected_text`    | 仅 highlight/underline 有值       |
| `itemAnnotations.comment` | `comment`          | 所有类型都可能含 comment           |
| `itemAnnotations.color`   | `color`            | Hex 色号，如 #ffd400              |
| `itemAnnotations.pageLabel`| `page_label`      | 标页码字符串                      |
| `itemAnnotations.sortIndex`| `sort_index`      | 格式化零填充排序索引               |
| `itemAnnotations.position` | `position_json`   | 原始 JSON 字符串，含 rects/paths  |
| `itemTags → tags.name`    | `tags_json`        | JSON 数组                          |
| `items.dateModified`      | `source_modified_at` | ISO 8601                         |

### 5. PaperForge 是否应该修改现有 paperforge.db schema？

**不应该。** Annotation 是用户数据，现有 `drop_all_tables()` 会在 memory rebuild 时无差别删除。

**决策：独立 `annotations.db`**，与 `paperforge.db` 并列存放。两者通过 `zotero_key` 关联。rebuild memory layer 时 annotations.db 完全不受影响。

### 6. Annotation 表应该如何避免被 memory rebuild 删除？

采用独立 DB + 独立 schema version 管理：

```
paperforge/indexes/
├── paperforge.db          ← memory layer (schema v2, 可 rebuild)
├── annotations.db         ← annotation layer (schema v1, 独立管理)
├── formal-library.json    ← canonical index
├── memory-runtime-state.json
└── vector-runtime-state.json
```

`annotations.db` 有自己的 `meta` 表记录 `schema_version`，由 annotation CLI 命令独立管理 migration。

### 7. Obsidian PDF overlay 第一版是否可行？

**可行。** PDF++（2095 stars）已验证了 monkey-patching 路线的可行性。核心机制：

1. 用 `monkey-around` 库的 `around()` 函数 patch `PDFViewerChild.prototype`
2. 在每个 `div.page` 内创建 overlay layer div
3. 用 `window.pdfjsLib.setLayerDimensions()` 对齐坐标空间
4. 用百分比 CSS 定位实现缩放无关渲染
5. 监听 `textlayerrendered` / `annotationlayerrendered` 事件触发重绘

### 8. 是否需要自建 PDF.js reader？

**不需要** 且 **不推荐**。Obsidian 内置了 PDF.js（通过 `loadPdfJs()` 可从 plugin 访问），ZotFlow 的自建 reader iframe 是其最重的部分。PaperForge 应该直接 hook 原生 PDF viewer，仅在需要 overlay 的页面上添加 DOM 层。

### 9. 第一版是否应该写回 Zotero？

**架构层面设计写回，但 v1 不实现。** 推荐 hybrid 路线：

- **读路径**：本地 SQLite 只读解析（快、离线、零配置）
- **写路径**：通过 Zotero Web API 写回（安全、version 乐观锁、官方支持）
- **v1**：本地 SQLite 读取 + 本地 annotations.db 编辑，`sync_state` = `local` / `pending_push`
- **v2**：实现 Web API push，`sync_state` = `zotero_synced`

schema 从第一天就包含 `sync_state`、`source`、`source_version` 等字段，为写回预留。

### 10. 最推荐的 MVP 开发路线是什么？

```
Phase 1 (1 周): DB + CLI
  annotations.db schema
  paperforge annotation import (Zotero SQLite read-only)
  paperforge annotation list/patch/delete
  独立 schema version 管理，sync_state 预留

Phase 2 (1-2 周): Plugin Overlay
  monkey-patch PDF viewer
  render highlight/underline/note rects
  selection → create annotation
  click → edit popover
  Zotero annotations show as read-only (lock icon)
  PaperForge local annotations are editable

Phase 3 (后续): Web API Write-back
  Web API 客户端 (zotero-api-client 封装)
  sync queue → pending_push → API push
  冲突检测与手动解决
```
