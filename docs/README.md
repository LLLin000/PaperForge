# PaperForge 文档总导航（Documentation Index）

> PaperForge v2.0 面向**研究者 / 终态用户**、**系统维护者**与 **AI Agent** 的权威文档入口。关于早期 Better BibTeX 配置细节，请直接参阅 [新手入门指南](getting-started.md) 与 [中文使用引导](help/zh/guide.md)。

---

## 1. 全量技术参考手册（面向维护者与 AI Agent）

PaperForge 的完整工程实现细节采用 **“14 篇专题源码核对分册 + 1 份自动编译单文件全景底本”** 双层架构维护，受 `tests/test_technical_docs_sync.py` 自动化门禁与源码实时对账：

- **单文件全景参考**：[PAPERFORGE-TECHNICAL-REFERENCE.md](PAPERFORGE-TECHNICAL-REFERENCE.md) —— 由 `scripts/build_technical_reference.py` 从 `docs/handbook/` 14 章确定性编译生成，适合整库上下文检索、排障溯源与跨模块升级设计。

| 章节   | 专题分册                                                                                                       | 核心覆盖范围与源码入口                                                                                                                   |
| :----- | :------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------- |
| **01** | [第 01 章：系统架构、分层约束与磁盘存储契约](handbook/01-architecture-and-storage.md)                          | Python Core 单一权威、P0 AST 分层门禁、`resolve_paths()`、`.paperforge/` 布局、`migrate-storage`、`trash.py`                             |
| **02** | [第 02 章：配置系统、凭据鉴权与运行时安装器](handbook/02-config-auth-and-runtime.md)                           | Schema v2（17 项 `FIELD_SPECS`、15 项 `AGENT_PLATFORM_IDS`）、OS Keyring、`pointer.json`、`runtime_installer.py`、`setup`/`doctor`       |
| **03** | [第 03 章：CLI 路由、PFResult 协议与流式取消机制](handbook/03-protocol-pfresult-and-stream.md)                 | `cli.py` 46 个子命令、`PFResult`/`ErrorCode`、NDJSON 事件流、`PAPERFORGE_STOP\n` 协作取消、原子 IO                                       |
| **04** | [第 04 章：控制面状态探针与 Reconcile 缺口推导](handbook/04-probes-and-reconcile.md)                           | Schema-v2 `probes/`（6 模块、6 种 `USER_STATE_*`、TTL）与冻结的 `reconcile` 缺口/决策推导                                                |
| **05** | [第 05 章：Action 注册表、双阶段 Preflight 与安全分级](handbook/05-action-registry-and-safety.md)              | `ACTION_REGISTRY`（9 个声明式动作）、`NON_REGISTRY_ACTIONS`、`--confirm` 双阶段执行与 `run_chain` 编排                                   |
| **06** | [第 06 章：Zotero/BBT 同步、PDF 解析、谱系与 Obsidian Base 生成](handbook/06-zotero-sync-and-lineage.md)       | `bbt.py`、`pdf_resolver.py`、`formal-library.json`、单一 `paperforge-table` 视图、`lineage.py`、`.state-seq.json`、`repair`/`prune`      |
| **07** | [第 07 章：OCR Provider、异步作业与 Canonical 持久化](handbook/07-ocr-provider-and-canonical.md)               | `OCRProvider`/PaddleOCR 异步提交、重试与批轮询、`canonical/blocks.raw.jsonl`、`raw`/`derived` 版本、`result-hash.txt`、`ocr redo`        |
| **08** | [第 08 章：V3 OCR 结构化管线、图表归属与渲染契约](handbook/08-ocr-v3-pipeline-and-objects.md)                  | V3 阶段序列、`pre_match`/`post_match`/`apply_object_writebacks`、`figure_inner_text` 合图、12 Pass 图表配对、`layout/`、`reader_gate.py` |
| **09** | [第 09 章：Render Audit、R/P 事务晋升与版本快照管理](handbook/09-render-audit-and-reconcile.md)                | `render_audit.py`、`promote_r.py` Schema-v2 事务日志、CAS 回滚、`accept_proposal.py`、ADR-0002、`versions` 滚动快照                      |
| **10** | [第 10 章：SQLite Memory DB v7、Embedding 与混合检索](handbook/10-memory-db-and-retrieval.md)                  | Schema v7（18+1+3 张表）、`WriterLock`、WAL、`ShadowBuild`、`sqlite-vec` 维度检测、BM25+Vector RRF、Layer 4 检索                         |
| **11** | [第 11 章：无损 Sidecar PDF 批注、Living Memory Card 与永久日志](handbook/11-annotations-and-living-memory.md) | `annotations.jsonl` 无损坐标事件、3 级 PDF Grounding、Living Memory Card 双写与历史、永久日志、`note set-flag`                           |
| **12** | [第 12 章：Agent Skills 分发、斜杠工作流与 AI 上下文命令](handbook/12-agent-skills-and-workflows.md)           | `paperforge/skills/` 部署与摘要校验、`/pf-*` 契约、`deep-reading`/`deep-finalize` 闭环、Agent 检索命令族                                 |
| **13** | [第 13 章：Obsidian Thin-Client 插件、IPC 传输与五大视图交互](handbook/13-obsidian-plugin-and-views.md)        | `PaperForgeClient` & `NodeProcessTransport`、单 `OperationLock`、Base/Companion/PDF Reader/Control Center/OCR Workspace 五大界面         |
| **14** | [第 14 章：测试金字塔、静态契约门禁与维修升级手册](handbook/14-testing-gates-and-maintenance.md)               | `.husky/pre-commit`、P0 架构门禁、`ci.yml`、V3 OCR 聚焦套件、`ocr_rebuild_paper.py`、`bump.py` 与排障手册                                |

---

## 2. 用户指南与安装运维（面向终端用户）

| 文档                                                                     | 用途说明                                                                    |
| :----------------------------------------------------------------------- | :-------------------------------------------------------------------------- |
| [新手入门指南](getting-started.md)                                       | 安装 Python 运行时、Zotero 与 Better BibTeX 自动导出配置、Obsidian 首次建库 |
| [用户完整手册](user-manual.md)                                           | 工作流全流程、Obsidian Base 文献表、PDF 批注、深度阅读与检索功能说明        |
| [CLI 命令参考](COMMANDS.md)                                              | 全部 `paperforge` CLI 子命令语法、参数与输出格式参考                        |
| [常见问题排查](troubleshooting.md)                                       | Zotero/BBT 导出、OCR 队列、向量构建与运行环境常见故障修复                   |
| [升级与更新指南](update-upgrade.md)                                      | 版本升级步骤与兼容性说明                                                    |
| [中文帮助文档目录](help/zh/guide.md) / [English Guide](help/en/guide.md) | 插件内嵌双语帮助与 FAQ 原文                                                 |

---

## 3. 架构决策（ADR）、专项契约与升级演进

| 文档                                                                                     | 说明                                                                    |
| :--------------------------------------------------------------------------------------- | :---------------------------------------------------------------------- |
| [系统架构概览](ARCHITECTURE.md)                                                          | 控制系统控制面、数据面、检索面与插件薄客户端的高层架构                  |
| [Obsidian UI 与 Base 视图设计规范](OBSIDIAN-UI-AND-BASE-DESIGN.md)                       | 苹果预览 / Minimal 风格 UI 交互规范、v4 多态视觉回归基线                |
| [跨平台安装与热更架构设计](INSTALL-AND-UPDATE-ARCHITECTURE.md)                           | 全平台 `uv` + `python-build-standalone` 与四维解耦升级设计蓝图（Draft） |
| [OCR 对象生命周期契约](OBJECT-LIFECYCLE-CONTRACT.md)                                     | Figure / Table / Provenance 状态迁移契约                                |
| [Reconcile 扩展契约](RECONCILE-EXTENSION-CONTRACT.md)                                    | Reconcile 只读发现者与冻结变更通道约定                                  |
| [版本迁移指南（v1.2 / v1.4）](MIGRATION-v1.2.md) & [v1.4 迁移](MIGRATION-v1.4.md)        | 历史版本目录布局与命令体系升级指南                                      |
| [OCR 高危规则审计](ocr/high-risk-rule-audit.md) & [OCR 生产路由审计](ocr/route-audit.md) | 受自动化单测锁定的 OCR 规则边界与 10 阶段路由盘点                       |
| [维护者指南](maintainer-guide.md)                                                        | 仓库协作者发布与维护注意事项                                            |

---

## 4. 历史设计与归档资料

- **已归档历史草案与演练报告**：见 [docs/archive/README.md](archive/README.md)，收录已完成的早期布局草案、PRD、 Dry-Run 报告与割接计划。
- **保留的历史 ADR 引用文件**：根目录中由 `docs/ARCHITECTURE.md`、`docs/adr/` 或 `paperforge/reconcile.py` 引用的历史草案（如 `design-*.md`、`BACKEND-FRONTEND-CONTRACT-MAPPING.md`、`ux-contract.md`）按原文保留于 `docs/` 以维持历史决策链完整，不再作为现行代码事实依据；所有现行接口、字段与行为以 [PAPERFORGE-TECHNICAL-REFERENCE.md](PAPERFORGE-TECHNICAL-REFERENCE.md) 与 [docs/handbook/](handbook/01-architecture-and-storage.md) 为准。
