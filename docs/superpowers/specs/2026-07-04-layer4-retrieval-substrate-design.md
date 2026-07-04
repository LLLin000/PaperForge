# Layer 4 检索底座设计

> 设计讨论：2026-07-04
> 状态：设计稿（待评审）

## 设计目标

Layer 4 的目标不是“换一个更强的向量数据库”，而是把 PaperForge 从“全文切块 + 单路搜索”升级成**论文原生（paper-native）的检索底座**。

本层只解决两件事：

1. **稳定的文献召回**：在整个库中找到相关论文与正文证据。
2. **具体信息查询**：在已经定位的论文内，基于目录结构精确拉取某一节、某一块或某一对象附近证据。

Layer 4 不负责 PaperCard / SubmethodCard 这类理解层资产。那些内容留给 agent 阅读流程去完成，而不是预计算固化到检索层。

## 当前问题

### 1. 当前 chunker 仍是文本块思维

`paperforge/memory/chunker.py` 仍使用：
- section regex 猜标题
- 固定 3 段一组
- 单一 `chunk_fulltext(fulltext_path)` 输出

这与 OCR 升级后的结构化结果不匹配。OCR 升级带来的主要增益是**章节层级、边界、对象归属**更准，而不是“文本内容大面积缺失”。

### 2. 向量检索与默认能力层耦合不清

当前系统中：
- FTS / 关键词路径默认存在
- vector_db 是用户可选开启
- `retrieve` 与其他查找命令分离
- agent 需要自己拼装 `search / retrieve / context / paper-status / query-plan`

这导致两个问题：
- **single-arm false absence**：某一路查不到，就误判库里没有文章
- **入口太碎**：agent 很容易选错命令或过早停止

### 3. 检索与结构导航没有明确分层

一旦文章已经定位，继续做全库 semantic retrieval 的价值很低。此时更重要的是：
- 给 agent 目录结构
- 让 agent 知道 section / subsection / figure / table 的组织方式
- 再按结构精确拉块

## 核心原则

1. **Structure-first**：优先利用论文结构与边界信息，而不是继续把全文当普通文本。
2. **FTS-first, Vector-optional**：默认能力依赖 FTS 与结构树；向量库是增强层，不是底盘。
3. **Trust-neutral at paper level**：不因为某篇论文 OCR health 是 yellow/red 就整体降权它。
4. **Local junk veto only**：只在单元级别排除明显垃圾内容，如 reference 污染、空块、乱码、重复页眉页脚。
5. **Unified surface, explicit routing**：对 agent 暴露少量统一子命令，内部做明确意图路由，而不是黑箱混查。
6. **Decompose before concluding absence**：对于找文章任务，必须先拆 query、多路组合检索，禁止一次零结果就宣告不存在。

## 非目标

本层明确不做：
- PaperCard / SubmethodCard 抽取
- 论文理解层 schema
- paper-level OCR 信任分数参与召回排序
- 强制所有用户开启向量库
- 一步到位大爆炸数据库迁移

## 检索模式（产品层定义）

Layer 4 明确定义为两个模式：

### Mode 1：Corpus Recall
目标：在整个库中找到相关论文与正文证据。

适用问题：
- 哪些论文讨论了 X？
- 谁比较了 A 和 B？
- 哪些文章正文里出现了某个机制或现象？

### Mode 2：Structured Paper Navigation
目标：在已经定位的论文中，基于目录与结构精确拉取内容。

适用问题：
- 这篇 paper 的目录结构是什么？
- 把 Methods / 3.2 / Results 这块调出来。
- 在这篇 paper 里定位 intervention / baseline / limitation 的具体位置。

向量库主要服务 Mode 1；结构树与 scoped fetch 主要服务 Mode 2。

## 领域模型

### Retrieval Unit
可被索引、召回、展示的最小检索单元。不是任意三段文本，而是带类型的论文原生对象。

### Body Unit
正文检索单元。来源于章节树、section/subsection 边界与正文 families。服务跨论文正文证据召回。

### Object Unit
对象检索单元。包含：
- Figure Unit
- Table Unit

最少承载：
- caption / legend
- 邻近正文证据
- paper identity
- section path
- page span

### Structure Tree
论文目录结构。描述 section / subsection / object 在论文中的组织关系。是 Mode 2 的核心导航面，不是向量检索结果。

### Paper Manifest
构建控制面资产，记录：
- 该论文产出多少 body/object units
- 用了哪个 OCR result hash
- 用了哪个 retrieval policy version
- 是否需要重建

Paper Manifest 不是向量索引，而是增量构建与健康检查的依据。

## Index Shape

### 逻辑分层

#### `body_units`
主索引。只放 Body Unit。服务 P0：跨论文正文证据检索。

最少字段：
- `paper_id`
- `section_path`
- `page_span`
- `unit_text`
- `token_estimate`
- `unit_kind=body`
- `structure_quality_hints`

#### `object_units`
副索引。放 Figure Unit / Table Unit。第一阶段不是主入口，但 schema 从一开始就要留好。

最少字段：
- `paper_id`
- `object_kind=figure|table`
- `object_label`
- `caption_text`
- `nearby_body_text`
- `page_span`
- `section_path`

#### `paper_manifest`
构建 sidecar，不走向量检索。

### 设计规则

- 逻辑上必须把 `body_units` 与 `object_units` 分开。
- 物理上可以同库不同表 / collection。
- 不允许把 body / figure / table 混进一个大 collection 再靠 `type` 事后补救。

## 能力矩阵

Layer 4 必须显式承认默认能力层与增强能力层的区别：

| 能力 | FTS only | Vector enabled |
|---|---|---|
| 定位某篇 paper 后看目录 | ✅ | ✅ |
| 按 section 精确取块 | ✅ | ✅ |
| 全库关键词召回 | ✅ | ✅ |
| 全库 semantic recall | ❌ | ✅ |
| hybrid ranking | ❌ | ✅ |
| 图表语义召回（后续） | ❌ | ✅ |

结论：
- FTS 与结构树是默认地基。
- Vector 层是增强层，只在用户启用时介入。

## 统一入口与显式路由

### Agent-facing surface

对 agent 暴露四个统一子命令：
- `paperforge paper-lookup`
- `paperforge content-discovery`
- `paperforge paper-navigation`
- `paperforge scoped-fetch`

这四个命令共享同一个内部 routing / resolution core，但对外保持显式 intent，而不是黑箱混查。

关键不在于把一切折叠成一个万能命令，而在于**agent 默认不再直接编排一堆底层 CLI**。

### Internal arms

底层仍可复用或保留：
- metadata search
- FTS
- vector retrieval
- context inventory
- structure fetch
- section fetch

但这些更多是内部执行臂，而不是 agent 的默认入口。

## Intent Map

### Intent 1：`paper_lookup`
目标：定位某篇具体文章。

典型输入：
- 标题
- 作者 + 年份
- DOI
- citation key
- Zotero key
- 不完整标题

首选路由：
1. metadata exact/fuzzy search
2. paper inventory / paper status
3. 必要时再用 FTS 补正文或标题痕迹

禁止错误：
- 不能因为 FTS / semantic 没命中就说“库里没有这篇”

### Intent 2：`content_discovery`
目标：跨库找讨论某件事的论文与正文证据。

首选路由：
1. corpus FTS baseline
2. vector / hybrid enhancement（若启用）
3. paper-level regroup / dedup

禁止错误：
- 不能只给 chunks 不给 paper identity
- 不能把 metadata lookup 当主路径

### Intent 3：`paper_navigation`
目标：已定位 paper 后查看目录结构与大致内容组织。

首选路由：
1. structure tree / outline
2. section path / node id 展示
3. 必要时再做局部摘要

禁止错误：
- 已定位 paper 后重新跑全库检索

### Intent 4：`scoped_fetch`
目标：已知 paper 或 section 后精确拉取内容。

首选路由：
1. section-path fetch
2. node-id fetch
3. paper-scoped FTS
4. paper-scoped semantic drill-down（后续增强）

禁止错误：
- 为调一节内容又退回全库 search

## `paper_lookup` 的组合检索策略

对找文章任务，不能把一串关键词直接整体做一次性 FTS 或一次性 metadata 搜索。正确策略是：

### Step 1：Query decomposition
把输入拆成高信号槽位，例如：
- `author token`
- `year token`
- `title-like tokens`
- `doi / citation key / zotero key`

### Step 2：高信号 identity 路径
先尝试：
- DOI
- Zotero key
- citation key
- 完整标题近似

### Step 3：结构化交集
例如：
- `author ∩ year`
- `title fragment ∩ year`
- `author ∩ title fragment`

### Step 4：放宽组合
例如：
- 两两交集
- title token subsets
- author + 任意标题子集
- coverage-ranked unions

### Step 5：正文侧补救
必要时用 FTS / vector 在正文中寻找标题痕迹、作者提及或相关线索。

### 返回值规则
返回结果不能只有“命中/未命中”，而应包含：
- `matched_author`
- `matched_year`
- `matched_title_tokens`
- `matched_by`
- `coverage_score`

### 强约束
**单次零结果不能作为 absence proof。**
只有多条高优先级路径都失败，才允许返回“暂未定位”。

## 检索流程

### Corpus Recall Flow

1. Query Planning
2. Candidate Retrieval
   - FTS baseline
   - vector/hybrid enhancement（若启用）
3. Structural boundary-aware grouping
4. Local junk veto
5. Paper diversification / regroup
6. Evidence packaging

### Structured Paper Navigation Flow

1. 读取 structure tree / outline
2. 让 agent 先理解这篇 paper 的 section 组织
3. 按 `section_path` / `node_id` / page span 精确 fetch
4. 必要时在该 paper 内再做 scoped FTS / semantic drill-down

## OCR 质量与检索的关系

### 结论
OCR 升级对 Layer 4 的主要价值是**Boundary Fidelity**，不是给论文打可信度分。

### 允许做的事
- 利用结构信息定义更好的 `BodyUnit`
- 利用结构树导航 section / subsection
- 在局部单元级别排除 reference 污染、空块、乱码块、重复噪声
- 把 OCR health 作为 build diagnostics 与 UI explanation

### 不允许做的事
- 因为某篇 paper overall OCR health 是 yellow/red 就整体降权它
- 把 paper importance 与 OCR 健康状态混为一谈

结论：
- structure-first
- trust-neutral at paper level
- only local junk veto

## Backend Strategy

### 默认底盘
继续保留现有 FTS 路径作为默认底盘。理由：
- 默认启用
- 无需额外配置
- Mode 2（paper navigation / scoped fetch）本来也不依赖向量库

### Vector Adapter
把当前 hard-coded Chroma 路径抽成 adapter interface，例如：
- `search_body_units(...)`
- `upsert_body_units(...)`
- `delete_paper_units(...)`
- `health()`

这样未来可以存在：
- `ChromaBackend`
- `LanceBackend`
- `QdrantBackend`（若将来真需要）

### 为什么推荐 LanceDB 作为目标后端
在 Layer 4 的约束下，LanceDB 更贴近需求：
- 本地文件式，适合 Obsidian + Python CLI 工作流
- 支持 filter / hybrid / multimodal 形状，适合未来 `object_units`
- 比 Qdrant 更轻，不需要太强的“基础设施”心智
- 比当前 Chroma 更适合作为 typed retrieval schema 的承载层

### 为什么不是马上大爆炸迁移
因为当前更重要的是：
- retrieval unit 正确
- intent route 正确
- unified gateway 正确

在这些都没定型前直接换库，只会把问题从“检索系统设计”转成“数据库迁移工程”。

### Chroma 的位置
Chroma 更适合作为：
- 兼容层
- 现有行为的 adapter
- 对照后端

而不是长期唯一终局。

## 分阶段迁移

### Phase 1：产品面统一
先做：
- unified retrieval gateway
- intent router
- structure tree / scoped fetch
- FTS-first 默认路径

此阶段不强碰向量库。

### Phase 2：retrieval unit 重构
引入：
- `BodyUnit`
- `FigureUnit` / `TableUnit`
- `paper_manifest`
- 增量 build / reindex contract

### Phase 3：vector adapter
把 Chroma 从“硬编码后端”降成“一个 backend adapter”。

### Phase 4：Lance backend 接入与对比
在同一 retrieval contract 下，对比：
- 命中质量
- build 时间
- 本地稳定性
- agent 使用体验

### Phase 5：决定推荐可选后端
如果 LanceDB 明显更好，就让它成为 vector-enabled 用户的推荐后端；Chroma 留兼容迁移期。

## 设计结论

Layer 4 的最终目标不是“更强的向量搜索”，而是：

> **FTS-first + unified gateway + paper-native retrieval units + structured paper navigation + vector adapterization + Lance-targeted optional migration**

这条路线：
- 保住默认可用能力
- 利用 OCR 结构升级的真实收益
- 避免 single-arm false absence
- 给未来的 figure/table 检索和 multimodal 打开干净入口

## 参考资料

- PaperIndex README（structure-first paper-native indexing）  
  https://github.com/Biajin-PKU/PaperIndex
- Chroma cookbook（embedded persistence / constraints / metadata filter）  
  https://cookbook.chromadb.dev/running/deployment-patterns/  
  https://cookbook.chromadb.dev/core/system_constraints/  
  https://cookbook.chromadb.dev/core/filters/
- Qdrant Python client README（local mode / payload / collection config）  
  https://github.com/qdrant/qdrant-client/blob/master/README.md
- LanceDB Python README（local file-based search / filter / hybrid / multimodal）  
  https://github.com/lancedb/lancedb/blob/main/python/README.md
