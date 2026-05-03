# Project Research Summary

**Project:** PaperForge v1.6 literature asset foundation
**Domain:** 基于 Zotero + Obsidian 的本地优先文献资产管理与 AI 上下文基础设施
**Researched:** 2026-05-03
**Confidence:** HIGH

## Executive Summary

PaperForge v1.6 不应被做成“又一个提示词按钮集合”，而应被收敛为一个建立在现有 Worker/Agent 双层架构之上的“文献资产底座”。研究结论非常一致：Zotero 继续做书目与附件真相源，Obsidian 继续做知识工作台，Python 继续做业务语义与派生状态的唯一所有者；新增能力的核心不是更多提取功能，而是把每篇文献当前“有什么、缺什么、下一步做什么”稳定地表示出来。

推荐路径是：围绕现有 `paperforge.json`、`library-records`、OCR 产物、正式文献笔记，演进出一个由 Python 统一生成的规范资产索引，并让 plugin 只做 thin shell 展示与命令触发。这样可以把 lifecycle、health、maturity、AI-ready 等判断从当前分散的命令/界面里收敛到一个可重建的派生读模型中，再在此基础上提供 ask-this-paper、ask-this-collection、copy-context-pack 等通用 AI 入口。

最高风险不在“技术做不做得出”，而在 brownfield 演进中制造多重真相源、把 canonical index 用成手工数据库、以及在 plugin 中重复实现 Python 业务规则。v1.6 的里程碑设计必须先锁定字段归属、重建契约与迁移/回滚路径，再做 dashboard、成熟度评分和 AI context packaging；否则表面功能越多，状态漂移和维护成本只会越严重。

## Key Findings

### Recommended Stack

v1.6 的推荐栈是“Python-first + CommonJS thin-shell plugin”，不是引入新前端层，也不是把业务逻辑迁到 JS。核心新增依赖很克制：用 Pydantic 建立 `paperforge.json`、canonical index、health/maturity/context manifest 的强类型契约；用 filelock 与 `tempfile` + `os.replace()` 保证 Windows 友好的跨进程锁与原子写入；用 jsonschema 做测试和 `doctor` 级别的契约校验。

最重要的栈结论不是“加什么”，而是“不要加什么”：不要上 SQLite、不要上 watchdog/daemon、不要在 plugin 里引入 AJV/Zod 作为第二套契约、不要为 v1.6 引入向量库/搜索引擎。当前 PaperForge 的问题是资产状态不可统一解释，不是检索基础设施不足。

**Core technologies:**
- **Python 3.10+**：继续作为 config、lifecycle、health、maturity、context-pack 的唯一业务所有者，避免 JS/Python 双实现漂移。
- **Pydantic 2.13.3**：为 `paperforge.json`、`formal-library.json` 演进后的 envelope、context pack manifest 提供单一类型真相与 schema 输出。
- **filelock 3.29.0**：为 index/context pack 写入提供跨进程锁，防止 sync、ocr、plugin 同时写文件造成损坏。
- **`tempfile` + `os.replace()`**：保证 canonical JSON/缓存产物原子落盘，避免中断时出现半写文件。
- **CommonJS Obsidian plugin（现有）**：仅负责 dashboard、settings、命令触发与结果展示，不承担状态推导。
- **jsonschema 4.26.0（测试/诊断）**：用于验证生成的 schema 与导出产物，提升 doctor/CI 的可验证性。

**关键版本/格式要求：**
- `paperforge.json` 增加 `schema_version`
- 继续以文件系统 JSON snapshot 为主，不引入数据库
- canonical index 采用版本化 envelope，而不是裸列表

### Expected Features

研究对“必须做什么”和“不要做什么”划分很清楚。v1.6 的 table stakes 不是炫技式 AI，而是把文献库做成一个可读、可修、可重建、可复用的资产系统；真正的 differentiator 也不是医学专用提取表，而是可追溯的 context pack、统一 health/lifecycle 语义与可执行的 next-step guidance。

**Must have（table stakes）:**
- **Canonical asset index**：统一回答每篇文献有哪些资产、缺哪些资产、当前可用于什么。
- **显式 lifecycle state model**：区分 imported、indexed、pdf_ready、fulltext_ready、deep_read_done、ai_context_ready 等派生状态。
- **Library health surfaces**：能看到 PDF、路径、OCR、note/template/base 的健康状况，并支持聚合到 collection/library。
- **Stable per-asset schema**：统一标识符、路径、provenance、readiness 字段，保证长期可维护。
- **Derived queue / next-step views**：从派生状态给出“下一步该 sync / ocr / repair / pf-deep 什么”，而不是只暴露原始 frontmatter。
- **Idempotent rebuild / refresh**：任何修复后都能安全重建索引和视图，不污染正式笔记。

**Should have（differentiators）:**
- **Ask-this-paper context pack**：把单篇论文打包为可追溯 AI 输入，包含 metadata、fulltext、figures、note links、provenance。
- **Ask-this-collection / copy-context-pack**：把 collection 级资产打包给 NotebookLM 风格、但本地优先的综合工作流。
- **Maturity / workflow level scoring**：用透明、可解释的等级/评分告诉用户这篇论文距离“AI-ready”还有多远。
- **Actionable diagnostics with fix paths**：不仅报错，还明确推荐 `sync`、`ocr`、`repair`、重建 note 或重建 index。
- **Thin-shell plugin dashboard**：基于 canonical index 的产品化界面，而不是第二套业务引擎。

**Defer（v2+ 或保持为可选能力）:**
- 学科专用 extraction outputs（PICO、机制表、参数表等）
- 自动从 worker 触发 deep-reading agent
- 大量 prompt-specific 按钮与“功能爆炸”式 AI surface
- 替代 Zotero 的参考文献管理能力
- 云协作/远程同步
- Litmaps/ResearchRabbit 风格的完整发现图谱产品

**Anti-features（本里程碑明确不应产品化）:**
- 不把每个成功 prompt 升级为核心功能
- 不把 domain-specific extraction schema 烙进 core index
- 不在 plugin 里做第二套 lifecycle/health 逻辑
- 不做黑箱式“AI 自动整理一切”

### Architecture Approach

架构结论非常明确：不要新造第二个 canonical index，也不要重写现有本地文件架构；应当直接演进现有 `<system_dir>/PaperForge/indexes/formal-library.json`，把它从“笔记列表”升级为“版本化 canonical derived read model”。它读取 `paperforge.json` 作为配置真相、`library-record` 作为用户意图真相、OCR 目录作为机器事实真相、正式笔记中的 `## 🔍 精读` 作为 deep-reading 真相，再由 Python 一次性推导 lifecycle/health/maturity/context readiness，供 CLI、plugin、Bases 复用。

**Major components:**
1. **配置真相层（`paperforge.json` / `paperforge.config`）** — 统一路径解析与运行时配置，plugin 只做镜像缓存，不做独立默认值真相源。
2. **资产索引构建层（建议 `asset_index.py`）** — 汇总 library-record、OCR meta、formal note、figure-map 等，生成版本化 `formal-library.json`。
3. **状态/健康推导层（建议 `asset_state.py`）** — 以纯函数形式统一 lifecycle、readiness、health、maturity 与 next-step 规则。
4. **上下文打包层（建议 `context_pack.py`）** — 基于 canonical item 生成 per-paper / per-collection AI context packs。
5. **thin-shell plugin + Base 镜像层** — 只读 canonical index 或 CLI JSON 输出，展示 dashboard、queue、settings 和执行入口。

**架构立场（里程碑必须坚持）：**
- 演进 `formal-library.json`，不要新增并行索引文件
- `library-record` 保存用户意图 + machine mirror，不承载所有真相
- plugin 不决定 OCR 是否完成、paper 是否 AI-ready、health 是否红黄绿
- repair 永远修 source artifacts，再重建 index，不直接修 index

### Critical Pitfalls

1. **多重真相源并存** — 必须先发布字段归属矩阵：`paperforge.json` 管配置，plugin `data.json` 仅作 UI cache，`library-record` 管用户意图，OCR/meta 管机器事实，canonical index 只做派生投影。
2. **把 canonical index 用成手工数据库** — index 必须可删除、可重建、可追溯；任何手工覆写都应放在独立 override 层，而不是直接改 index。
3. **把意图、事实、派生 readiness 混成一个状态机** — `analyze/do_ocr`、OCR 完成、deep-reading 完成、AI-ready 必须分层表示；readiness 应计算得出，不应靠用户手改。
4. **在 Obsidian plugin 里重写 health/lifecycle 逻辑** — 所有 dashboard 数字和 next-step 都应来自 Python 输出的 JSON 契约，否则 CLI/plugin 很快会分叉。
5. **做出“看起来智能、实际上不可解释”的成熟度分数** — 若要评分，必须能拆成检查项、权重、证据与修复建议，优先做 level/band 而非伪精确百分制。
6. **没有 brownfield 迁移与回滚故事就上线 v1.6** — 必须做 schema version、doctor/repair 升级、legacy reader、stale Base/template 检测与可逆重建。

## Implications for Roadmap

基于四份研究，v1.6 最合适的 milestone 结构不是“先做 dashboard 再补后端”，而是“先收敛真相模型，再构建 canonical index，再统一 health/status，最后再把 AI 入口挂上去”。下面的阶段划分最贴合当前 PaperForge 架构与 brownfield 风险控制。

### Phase 1: 真相模型与配置收口
**Rationale:** 这是后续所有工作最强依赖；如果配置、意图、机器事实、派生状态的边界不先锁定，后面每个功能都会放大漂移。
**Delivers:** `paperforge.json` 的 schema_version、`vault_config` 作为规范写入目标、plugin 配置只作镜像缓存、字段 ownership matrix、术语表。
**Addresses:** 单一配置真相、stable per-asset schema 的前置部分、idempotent rebuild 的制度基础。
**Avoids:** 多重真相源、状态机混层、术语漂移。

### Phase 2: Canonical asset index 演进与重建管线
**Rationale:** canonical index 是 table stakes 中最核心的底座，也是 dashboard、queue、maturity、context pack 的共同依赖。
**Delivers:** 演进版 `formal-library.json` envelope、legacy tolerant reader、`asset_index.py`、按 key 增量刷新、原子写入与文件锁。
**Uses:** Pydantic、filelock、`tempfile` + `os.replace()`、现有 sync/ocr/deep-reading/repair 流程。
**Implements:** 从 source artifacts 到 derived read model 的唯一投影层。
**Avoids:** index 被当数据库、非幂等 rebuild、并发写入损坏。

### Phase 3: 统一 lifecycle / health / next-step 引擎
**Rationale:** 没有统一状态与健康规则，queue、doctor、status、plugin 仍会各自解释同一篇论文。
**Delivers:** `asset_state.py`、显式 lifecycle/readiness 模型、PDF/OCR/path/note/template/base 健康检查、evidence-aware diagnostics、镜像回写 `library-record` 的展示字段。
**Addresses:** health surfaces、derived queue views、actionable diagnostics、maturity 的规则基础。
**Avoids:** 浅层 health 检查、聚合状态不指向具体修复路径、CLI/plugin 语义不一致。

### Phase 4: Status / Repair / Plugin / Bases 收敛
**Rationale:** 只有在 canonical contract 稳定后，前端展示与修复入口才能避免锁死错误后端假设。
**Delivers:** `status --json` 读取 canonical summary、`repair` 修源后重建 index、plugin dashboard 只消费 Python JSON、Bases 增加 `asset_state` / `library_health` / `maturity_level` / `next_step` 等列。
**Addresses:** thin-shell dashboard、workflow progression、可操作 queue 与库级总览。
**Avoids:** dashboard-first 反向冻结后端、plugin 重算业务规则、stale generated surfaces 被忽略。

### Phase 5: Maturity guidance 与通用 AI context packs
**Rationale:** 这是真正的 differentiator，但只能建立在索引、健康与 provenance 已可靠之后；否则 AI 入口只会包装不可信资产。
**Delivers:** ask-this-paper、ask-this-collection、copy-context-pack、manifest + context.md、level/score + next-step guidance、token budget 与 provenance 显示。
**Addresses:** AI context entry points、traceable provenance bundle、rule-based maturity guidance。
**Avoids:** 黑箱 AI feature、过重 context pack、学科专用 schema 侵入 core model。

### Phase 6: Brownfield rollout、迁移验证与回滚保障
**Rationale:** v1.6 面向已有 vault 与已有用户，必须把升级安全性当作交付物，而不是上线后补救项。
**Delivers:** doctor/repair 升级、schema/version 检测、旧格式兼容、stale Base/template 检测、可逆 rebuild 流程、发布验证清单。
**Addresses:** 长期可维护性、升级可恢复性、对既有数据的兼容性保障。
**Avoids:** 旧库升级后 dashboard 损坏、用户需要手工删文件恢复、文档只能建议“重装试试”。

### Phase Ordering Rationale

- **先真相模型、后界面层**：因为当前 PaperForge 已经有 worker/plugin 多表面并存，若不先统一字段归属，dashboard 只会把旧分歧可视化。
- **先 canonical index、后 maturity/context**：因为 features 研究明确指出 queue、health、AI pack 都依赖 canonical index 和 stable schema。
- **先 health/repair、后 AI 入口**：因为“AI-ready”必须建立在可解释、可修复、可追溯的资产状态上，而不是包装坏资产。
- **把 plugin 放在 Phase 4 而不是更早**：这是直接响应 architecture 与 pitfalls 的共同结论，避免 UI 反向冻结错误契约。
- **单独留 rollout phase**：因为 v1.6 是 brownfield 演进，不是 greenfield 新产品，迁移安全本身就是 milestone 范围的一部分。

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 5（Maturity + Context Packs）:** 需要进一步约束 token budget、pack 结构、collection 聚合粒度，以及与 `/pf-deep`、NotebookLM 风格工作流的衔接细节。
- **Phase 6（Brownfield rollout）:** 需要针对真实旧 vault 样本验证 legacy `formal-library.json`、旧 Base 模板、旧 plugin data 的兼容策略与回滚步骤。

Phases with standard patterns（可少做专项 research-phase，直接进入需求拆解）:
- **Phase 1（真相模型与配置收口）:** 主要基于现有代码结构与已识别漂移问题，模式清晰。
- **Phase 2（Canonical index）:** 文件投影 + schema version + 原子写入 + 文件锁属于成熟工程模式，研究结论一致。
- **Phase 3（统一 health/status 规则）:** 规则虽需细化，但总体边界已充分明确，重点在实现而非再探索方向。
- **Phase 4（Status/Plugin/Bases 收敛）:** 在 thin-shell 原则已明确的前提下，可按契约驱动开发，无需重新定义产品方向。

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | 以官方文档、PyPI 版本信息与现有仓库结构为主，结论集中且依赖收敛。 |
| Features | HIGH | 直接对齐 `.planning/PROJECT.md`、Zotero/Obsidian 官方产品边界与本项目 local-first 方向。 |
| Architecture | HIGH | 基于现有 `formal-library.json` 路径契约、sync/ocr/status/plugin 真实代码边界，建议非常贴合当前仓库。 |
| Pitfalls | HIGH | 与本项目既有漂移经验、plugin thin-shell 历史教训和 brownfield 风险高度一致，且可操作性强。 |

**Overall confidence:** HIGH

### Gaps to Address

- **`formal-library.json` 现网内容规模与刷新性能阈值**：规划时需要确认全量重建与按 key 增量刷新在真实库规模下的成本，以决定 Phase 2/3 是否同时做 query endpoint。
- **library-record 镜像字段的最小集合**：需要在需求阶段明确哪些字段必须回写 frontmatter 供 Bases 使用，哪些只保留在 canonical index 中，避免 frontmatter 膨胀。
- **context pack 的缓存策略**：需确认 per-paper/per-collection pack 何时惰性生成、何时缓存刷新，以避免 Phase 5 出现过重/过 eager 产物。
- **成熟度评分展示形式**：研究更偏向 level/band，但具体是否保留 numeric score、如何解释 delta，仍需在 milestone 需求中定型。
- **升级覆盖面验证样本**：需要至少准备几类真实旧 vault（路径异常、OCR 残缺、旧 Base 模板、旧 plugin data）作为 Phase 6 验证基线。

## Sources

### Primary (HIGH confidence)
- `STACK.md` — Pydantic、filelock、jsonschema、原子写入策略与 Python-first 栈建议
- `FEATURES.md` — v1.6 table stakes、differentiators、anti-features、依赖关系
- `ARCHITECTURE.md` — `formal-library.json` 演进方案、数据归属边界、模块拆分、阶段顺序
- `PITFALLS.md` — brownfield 风险、迁移约束、health/maturity/plugin 反模式
- 现有仓库代码检查：`paperforge/config.py`、`paperforge/worker/sync.py`、`paperforge/worker/ocr.py`、`paperforge/worker/status.py`、`paperforge/plugin/main.js`

### Secondary (MEDIUM confidence)
- Zotero 官方文档（collections/tags、attachments、duplicates）— 用于确认上游真相源边界与“不替代 Zotero”的产品定位
- NotebookLM、ResearchRabbit、Litmaps、SciSpace 的产品定位信息 — 用于界定 differentiator 与 anti-feature 边界

### Tertiary (LOW confidence)
- AI knowledge/RAG 一般性文章 — 仅作为 context pack explainability 与 retrieval governance 的启发，不作为核心架构依据

---
*Research completed: 2026-05-03*
*Ready for roadmap: yes*
