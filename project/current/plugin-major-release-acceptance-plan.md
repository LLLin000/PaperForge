# PaperForge 插件大版本：全工作流测试完善与发布验收计划

> 日期：2026-09-09
> 文档状态：PLANNED；实施未开始；本文件不表示任何新增测试已通过，也不授权发布。
> 调查基线：`d1244f96ef6e0f8c61c1bdf3510e0c771f1c479e`。
> 规划 checkout：`D:/L/Med/Research/99_System/LiteraturePipeline/github-release`。后续每个 issue 使用自己的权威 worktree，不把这个路径硬编码为测试 vault。
> 目标：本计划内所有适用工作流的测试补齐、缺陷修复、候选产物重新验证、owner 签字后，再发布插件大版本。
> 产品基线：[#83](https://github.com/LLLin000/PaperForge/issues/83)（CLOSED，updated_at `2026-07-22T14:11:40Z`）；旧发布 owner gate：[#81](https://github.com/LLLin000/PaperForge/issues/81)（OPEN / ready-for-human，updated_at `2026-08-19T09:35:04Z`）。本轮没有新建或修改远端 issue。

## 0. 使用方法与完成定义

1. 从 **W00** 开始，核定发布范围、支持窗口和历史契约差异；把本计划作为新验收 PRD 的输入。
2. 按 §8 的工作包拆成 Ask Matt agent-ready issues。一个 issue、一个权威 worktree、一个 writer、一个 `/implement` 会话，完成后按 `/review` 的 Standards / Spec 两轴审查。
3. 每个 issue 开始前固定父 PRD、issue URL 与 `updated_at`、base SHA、worktree、场景 ID、修改范围、测试 seam 和准确命令。issue 变化就刷新契约，不沿用旧验收。
4. 每个场景记录“现有测试是什么、缺什么、最终由哪条测试证明”；先复用现有 pytest/Vitest/WDIO，不为数量重复造测试。
5. 执行工作包中的红绿修复与实际表面验证；完成后提交对应证据。一个工作包若超过单 issue 的安全修改边界，按场景 ID 再拆，不能把未做部分算入完成。
6. 全部实施结束后冻结候选，再跑 **W22 发布认证**。实施时的旧绿色记录不能代替候选认证。
7. **W22 = RELEASE_READY** 只表示具备发布条件；**W23 = RELEASED** 必须另有 owner 对准确版本/产物的发布授权与发布后 smoke。

### 完成状态

| 状态 | 含义 | 能否计入发布通过 |
|---|---|---|
| PLANNED | 仅有计划 | 否 |
| IMPLEMENTED | 已实现测试或修复，但候选证据未闭合 | 否 |
| VERIFIED | 在明确 SHA、环境、产物上执行并满足断言 | 仅对该证据范围有效 |
| BLOCKED | 缺真实凭据、运行环境、产品决定或其他前置条件 | 否 |
| NOT_APPLICABLE | 不属于已经冻结的支持范围，有原因与 owner 批准 | 不冒充 PASS；进入范围记录 |
| RELEASE_READY | 发布前业务集 VERIFIED，R05 认证完成，owner 已接受证据；R07/R08 尚待发布阶段 | 仍不得自动发版 |
| RELEASED | owner 授权后实际发布，发布后 smoke 完成 | 是 |

**用户目标是全部完成，不是抽样完成。** §5 的每个场景都必须有证据或明确的范围决定；未实现功能、缺运行环境、失败或长期 skip 不能标为 NOT_APPLICABLE。任何缩减原定范围都要 owner 明确批准。当前文档中的 case ID / W 编号只是规划索引，不是第二套 issue 状态权威；GitHub issue 仍是任务状态权威，CI / owner gate 是发布验收权威。

**认证集合明确分开：**发布前业务集为 A、B、C、D、E、F、X、J 全部场景，加 R01–R04 与 R06；R05 是对该集合和 G01–G12 的最终认证结果，不要求先证明自己。R07/R08 只在 W23 发布与发布后执行，不作为 W22 的既成结果前置条件。发布链的无副作用演练必须在 W19/W21 提前完成，不能等实际发布才第一次验证门禁。

## 1. Problem Statement / 用户目标

用户准备发布包含前后端大幅更新的 Obsidian 插件。当前测试可以证明若干组件和正常路径，但缺少覆盖全部入口、状态转换、真实持久化和恢复的统一验收记录。单次“7/7”无法回答：升级会不会损坏旧 vault、设置是否重启丢失、任务取消是否重复收费、恢复是否只改正确论文、CI 是否测试了实际发布 bundle。

本计划从用户任务组织测试，保证每项适用能力的成功、拒绝、失败、恢复和界面回显可被追溯。§5 的每行是一条用户故事：**作为该工作流的用户，我希望得到该行的可观察结果，并在所列异常下保持安全。** §7 再验证任务之间的交接，不以内部调用次数替代用户结果。

## 2. 范围、现状与不可跨越的边界

### 2.1 已有基础：复用，不重建

- Python：`tests/unit/`、`tests/cli/`、`tests/integration/`、`tests/journey/`、`tests/e2e/`、`tests/chaos/`、`tests/embedding/`，以及根层的业务回归文件。
- 前端：`paperforge/plugin/tests/` 下的 Vitest 行为、契约与 DOM 测试。
- 真宿主：`paperforge/plugin/wdio.conf.mts`、`test/specs/paperforge.e2e.ts`、`test/fixtures/build_e2e_vault.py`；WebdriverIO + Mocha + wdio-obsidian-service。
- 当前 7 条真宿主用例混合了 UI、命令触发和 client 集成；上一轮记录为 7 passing、452 个单元通过。它们是历史记录，本轮未重跑，不自动作为将来 RC 的结果。
- `ci.yml` 已有三系统 Python unit/J-matrix、协议、OCR、插件 typecheck/build、Python E2E/audit、architecture gate；`All Checks Passed` 聚合这些 job。当前没有 WDIO job。
- `publish.yml` 是唯一 tag 发布入口：等待同 SHA 的 All Checks Passed，构建 wheel 和插件，发布 PyPI，再创建/补齐 GitHub Release。当前尚未将本计划中的真宿主、升级、故障恢复和发布产物认证纳入完整门禁。
- `package.json` 的 `pretest:e2e` 只构建 vault，没有 build 插件；W01 必须修正“测到旧 main.js”的风险。

### 2.2 现有 7 条的整改目标

| 原用例 | 保留内容 | 完整化要求 | 场景归属 |
|---|---|---|---|
| 插件加载/probe | 真宿主到真 Python | 不硬编码旧后端版本；绑定候选兼容契约，补非 ready 与恢复 | A02、R04 |
| Sync 按钮 | 真实 UI 点击 | 唯一数据变化、旁观对象保护、排除启动 autosync 旧 trace | B01、B02、B04 |
| 元数据搜索 | 输入与结果显示 | key/范围/导航/无结果/故障；不称为全文或语义质量测试 | C01、C02 |
| OCR 列表 | 真实行渲染 | 筛选、分页、范围、确认、执行、终态 | D01、D02 |
| 版本 restore | UI 确认与正文读回 | 显式版本选择、取消、provenance 结果、同沙箱重启、无旁路修改 | D07、D08 |
| memory.build | 真实 action | DB/FTS/下游查询正确，不能只断言 ok | E01 |
| trace/timing | 真实边界数据 | UI 开关/复制/清空、脱敏、失败关联、timing 结构和条件语义 | F06、X08 |

### 2.3 冻结的产品/安全约束

- Ticket 07 保持 CLOSED / SEALED。本计划是新发布验收工作，不重新打开旧票，不重建已删 bridge/fallback。
- Python 是身份、语义、配置和持久化 authority；`PaperForgeClient` 是前端共享执行入口；`NodeProcessTransport` 是进程入口。前端不能为测试便利新增第二 client 或绕过 authority。
- #137 NDJSON 保持现有 10-event / schema_version=1 契约；测试协议，不发明新事件兼容层。
- Reconcile Core 冻结；R/P 的 scope、review hash、CAS、journal、post-audit 和 rollback 约束继续有效。生产批量 rollout 仍需独立 owner gate。
- 本计划默认只在一次性沙箱做修改，不读写真实用户 vault、Zotero 源库、用户 keyring 或全局 runtime pointer。真实 provider 验收使用批准的公开/合成样本和专用凭据。
- 不修改 `paperforge/worker/ocr_figures.py`、`ocr_objects.py`、`ocr.py`、`ocr_rebuild.py`、`ocr_render.py` 来“凑测试通过”。若真实复现证明冻结文件有缺陷，形成独立 owner 决策/issue，在范围被明确批准前保持发布阻塞。
- 旧 #74/#81 的 SecretStorage、旧 runtime API、旧 credential env 等措辞可能与已封存的后续契约不一致。W00 必须对齐当前批准契约与父 issue；不能按旧文字恢复已删除的权限路径，也不能以源码现状自动覆盖产品要求。
- 不默认把“大版本”写成 2.0.0。具体版本、后端兼容区间、Release-N 支持窗口在 W00 绑定；没有决定时相应门禁保持 BLOCKED。

### 2.4 源码风险登记，不等于已经复现的 bug

| 风险 | 调查位置（规划基线，后续定位需重读） | 验收要求 |
|---|---|---|
| 向导 model/base 只存插件设置，而详情页走 configSet | `settings.ts:4077–4095` 与 `1570–1604`；`main.ts:581–588` | A03：两入口分别保存，Python 读回，同沙箱重启，实际请求使用正确配置 |
| 版本模式底部按钮创建后无绑定 | `dashboard.ts:2407–2422` | D07/D09：真实入口可达性与每个显示操作有实际结果或明确不可用理由；不能臆造删除版本后端 |
| 设置向导 configSet 异常被吞后继续 setup | `settings.ts:567–605` | A03：注入失败，验证没有假成功，错误可恢复 |
| Dashboard memory 状态依赖保存的 capabilityState | `dashboard.ts:750–761` | B06：未开 Settings 的冷启动、刷新、跨视图一致 |
| 启动自动 sync 污染“按钮成功”的 trace | `main.ts:419–475`；旧 sync E2E | B04/W01：隔离自动/手动场景，以目标数据差异关联操作 |
| 历史 archive 验收脚本使用固定 test vault、旧进度 token | 旧 acceptance plans 与 `acceptance/` | 仅历史参考；不得原样运行来证明新契约或直接打真实 test vault |

## 3. 测试设计契约

### 3.1 每个 case 都要填的八项

1. 用户入口（按钮/设置/命令/CLI），目标对象与前置状态。
2. 允许的范围与修改集合；至少一个不应被影响的旁观对象。
3. 实际操作序列，授权/确认与预检行为。
4. 可观察过程：busy、progress、error、cancel、terminal。
5. 独立结果判据：文件字节/语义、DB rows/查询、配置读回、实际打开的文档。
6. 失败与恢复判据：拒绝零副作用，部分成功逐项诚实，重试安全。
7. 刷新与持久化：旧响应不能覆盖新状态；需持久化的改动在同一沙箱重启后存在。
8. 准确执行命令、支持环境、证据目录、关联 issue 和代码 SHA。

### 3.2 层级标记

| 标记 | 实际运行范围 | 能证明/不能证明 |
|---|---|---|
| U | Python/Vitest 行为与状态测试 | 边界、解析、状态序列；不能独自证明真实 spawn/UI |
| I | 真实 Node client/transport 或真实 CLI → Python 子进程 → 临时 FS/SQLite | 进程协议与持久化；不能独自证明按钮能用 |
| H | 真实 Obsidian + 本次构建插件 + 真实本地后端 | UI 工作流；若 provider 为替身，必须明示 |
| V | 专用凭据 + 真实外部 provider/OS adapter | 真实认证和服务契约；不表示所有网络故障都覆盖 |
| Q | 人工真值集上的内容/检索评估 | 内容身份、质量及回归；不以 ok 或文件存在代替 |
| P | 干净环境安装候选发布产物 | 包安装/升级/回退与兼容性；不能用源码 import 冒充 |

在 U 中可 fake clock/transport；I/H 的业务主链必须用真实 client、transport、Python、SQLite、文件操作。外部 HTTP provider 可用本地可控服务，但替换点位于网络边界；不替换 runAction、worker 完成事件或最终文件来宣称端到端通过。没有现成网络 seam 时先在 issue 内固定最小 seam；不能把 fake module 在进程外失效的问题靠测试专用生产分支解决。

### 3.3 通用不变量（按风险适用，不机械复制全部组合）

- 修改范围不超过获授权的 scope；unknown/ambiguous identity 不猜测；越界路径不读写。
- 收费、危险或需确认动作在拒绝/缺确认时无提交、无写入；预检与真正执行之间的状态变化再次检查。
- 重复点击和后台并发不产生未经授权的第二执行；OperationLock 与后端锁各自验证，不能把前端锁当成跨进程锁。
- 每条 stream 只有一个合法 terminal；非 JSON stdout、未知事件、schema 不符、终态后事件、无 terminal EOF 均按冻结协议拒绝。stderr 日志不混进 stdout。
- terminal / 退出码 / UI 三者一致；structured rejection 的 code 保留，不退化成“成功但空数据”。
- 取消在承诺的安全点生效；本地 detach 不等于远端 cancel；不确定提交不能盲目重试收费请求。
- 部分成功逐 key 可追溯；follow-up 只用实际成功集合；不能只看进程 exit=0。
- 幂等按业务语义判断；日志中明确允许追加的事件不强行要求字节不变。稳定文件和旁观对象必须保持不变量。
- “已提交，但 report/provenance/cleanup 部分失败”按当前契约诚实表示；不能错误 rollback 已提交结果，也不能把 best-effort provenance_persisted=false 写成完整成功。
- 用户正文、批注、自定义 Base 和不在修改范围内的配置受保护。H 中 Obsidian 自己会修改 `.obsidian`；用职责 allowlist 区分宿主变化和插件越权。I 中 headless sync 继续验证 `.obsidian` 保护。
- secret 不出现在 argv、普通配置、stdout、trace、截图或分享诊断；实际 OS keyring 验证使用隔离身份/命名空间或专用测试账号。

## 4. Fixture、环境和证据准备

### 4.1 Fixture 分类（名称是数据类别，不强制增加同名目录）

| 类别 | 数据构造 | 用途 |
|---|---|---|
| EMPTY | 空 vault，无规范 config/index/DB | 首次安装、缺依赖、可跳过可选能力 |
| BASIC | 至少两个 domain；A/B 为目标，C 为旁观；同名不同 key；唯一检索词 | 同步、身份、scope、搜索导航 |
| OCR | 有效 PDF + 固定 provider response/已有 raw；缺 PDF、坏 raw、pending 三类 | OCR/rebuild/恢复；付费测试另行标记 |
| VERSION | v1/v2/current 正文互不相同；legacy backup；非法 label/path 样本 | 选版、比较、restore、provenance |
| MEMORY | 空 DB、当前 DB、旧 schema、坏 DB、有备份、部分向量、stale lineage | build/migrate/restore/retrieve |
| RESIDUAL | workspace-only、OCR-only、FTS-only、vector-only orphan；保护文件 | prune/trash/repair 与旁观保护 |
| LEGACY | 从准确 Release-N 产物生成/脱敏的兼容样本，记录版本与 hash | 升级、重启、回退；不能只手写一个自称 N 的 config |
| SCALE | 参数化合成元数据、小/中/大正文和版本；记录规模 | UI 响应、内存、同步与检索性能 |
| QUALITY | 公开许可/合成 PDF 与人工确认的正文、图/表身份、查询相关性标签 | Q/V；与调试样本区分，变更标签需审阅 |

基础 builder 可继续用真实 sync/memory build，但预期 key 集合、查询词、正文和保护 hash 必须由独立 fixture 真值定义。构建失败立即退出；构建步骤产生的产物不能自动证明该步骤的业务正确。版本 fixture 必须记录其来源为 seeded，而非声称完整版本生成链已经测过。

### 4.2 沙箱边界

- 每个 I/H mutation 测试独立临时 vault；至少在安全用例验证实际解析后的工作路径属于该沙箱。
- 测试 root 必须是 runner 创建且标记的一次性目录；拒绝 cwd、空路径、vault 根以外、用户目录、真实 Zotero 和硬编码个人 vault。清理前重新核对 root 与所有权。
- 同时隔离 HOME/APPDATA/XDG、runtime pointer/slots、缓存、日志、credential backend、网络 endpoint；不能只复制 vault。
- Linux/macOS 用原生 filesystem/process 行为；Windows 的锁、task tree、junction/symlink 专项在 Windows 真跑。有权限限制时换具备能力的 runner，不把关键安全 skip 计通过。
- 默认禁止对真实 provider 的意外出网；受控 provider 绑定 loopback，随机端口，响应/请求记录脱敏，结束时清理子进程。
- freshness/竞态用可控 barrier 或 hook 建立顺序，不靠长 sleep。H 等待可见可用状态与业务结果；定位用 accessible name/明确 test-id，不绑定 DOM 层级。
- 正常独立 H 用例：`reloadObsidian({vault: fixturePath})` 新副本。重启持久化用例：重启当前临时 vault，不重新传原 fixture 来清空结果。resetVault 只重置文件，不能假定它清空模块 cache/timer。
- autosync 正常用例独立运行；其他 mutation 用例在启动前关闭自动 sync 或显式等待并隔离其结束，设置属于测试环境配置，不新增产品后门。

### 4.3 证据记录（W01/W19 实现最小 JSON 汇总，不另造测试平台）

每次报告至少含：case_id、issue、source_sha、worktree_dirty、artifact_sha256、fixture_id/hash、OS/arch、Obsidian app/installer/Electron、Python/Node、backend/plugin 版本、provider_kind（none/local-controlled/live）、命令、开始/结束时间、首次结果、retry 结果、status、断言摘要、证据路径、skip/block 原因。

证据保存：runner 原生 JSON/JUnit + 失败截图/DOM/console + 脱敏进程日志/NDJSON + 目标产物前后差异；敏感或真实文献正文不上传公共 CI。证据放临时目录/CI artifacts，发布 manifest 只引用稳定位置和 hashes。先失败后重跑成功必须记录 flaky，不覆盖首次失败。

证据按 `case_id + variant + required_layer + environment` 记录，而不是每个 case 只有一个布尔值。例如 A05 的本地协议/失败回滚由 W03 负责，真实 OS adapter 由 W20 汇总；W03 的 scoped issue 完成不等于 A05 全部 VERIFIED。同理，W19 可以完成 CI 接线，但最终候选所有环境的 X10/X12 证据仍由 W22 汇总。只有该 case 的所有适用变体与层级齐全，才能提升整个 case 状态。

## 5. 全工作流验收矩阵

下表所有行初始均为 PLANNED。标记 `!` 表示安全/发布高风险，不能用重试、skip 或仅 U 测试替代。每一行至少拆出列明的成功与异常场景；一个测试可以同时证明多个 ID，但每个 ID 都要有可查询映射。W00 还要扫描当时的 CLI/action/UI 入口，若出现此表未列的新能力，先追加稳定 ID 再实施。

### A — Foundation、配置、凭据、生命周期

| ID | 用户工作流与可观察成功结果 | 必测失败/边界及保护证据 | 层级 | 工作包 |
|---|---|---|---|---|
| A01! | 首次安装：空环境→向导→配置→probe 可用；可选 OCR/检索可跳过 | 无 Python/venv、路径无权限、网络失败、取消、重复安装；无未验证 pointer 发布，现有内容保留 | U/I/H/P | W04 |
| A02! | 已有 vault 冷开→已验证后端→状态与恢复入口 | 缺失/坏/过期 pointer、非 ready、版本不兼容、离线；拒绝 ambient Python fallback，不假 ready | U/I/H/P | W04 |
| A03! | 设置向导及详情页修改 model/base/path/agent→Python 读回→同沙箱重启→实际生效 | 非法/只读/secret key、写失败、快速连续改、并发字段写；无丢字段、无假保存、受保护配置不变 | U/I/H | W03 |
| A04! | 旧配置预览→确认迁移→重新 hydrate→重启 | dry-run/取消零业务写；canonical 与 legacy 冲突、重复迁移、部分失败，优先级符合当前契约 | U/I/H/P | W03 |
| A05! | OCR/embedding secret 保存/替换/删除/迁移→presence 更新 | 无确认/冲突、keyring 错误、读回不符、env precedence；失败保留旧值，秘密不泄漏；CLI env 与插件 stdin 路径分开验证 | U/I/H/V | W03 |
| A06! | foundation.update/repair→新进程验证→切换运行时 | 无 pointer、下载/安装/验证失败、取消、版本不符；旧运行时可启动，新槽未验证不激活 | U/I/H/P | W04 |
| A07! | 禁用/重启插件及关闭 vault 后安全再启用 | 任务运行中关闭、多次启停；无孤儿子进程/重复 timer/listener，锁释放/恢复按契约 | U/I/H | W04 |
| A08! | Release-N→候选升级→重启→规定窗口内回退/重新安装 | 旧 schema、不同 Python、失败迁移、离线回退；不能以插件二进制回退声称数据降级兼容，旧版可读写范围有实证 | I/H/P | W21 |

### B — Library、模式、笔记、导航

| ID | 用户工作流与可观察成功结果 | 必测失败/边界及保护证据 | 层级 | 工作包 |
|---|---|---|---|---|
| B01 | 初次 sync 后出现人工指定 key、规范索引/工作区/笔记 | 空/坏 BBT、缺 PDF、多 domain、重复身份；缺输入与零论文区分，源 Zotero 不修改 | I/H | W05 |
| B02! | 修改导出后点击 Sync：新增/修改/移除的准确结果，重跑幂等 | 旁观论文和人工正文/hash 保留；坏导出不被当成删除全库授权；不能只断言计数或旧 trace | U/I/H | W05 |
| B03 | selection-sync/index-refresh/base-refresh 各自完成限定刷新 | 自定义 Base、路径移动、force/无 force、重复运行；不执行未请求的远程任务 | I/H | W05 |
| B04! | 启动/定时 autosync→安全自动 follow-up→刷新 | disabled、hydrate 未完成、前次未结束、手动同时触发、失败；不重入、不自动收费、不弹干扰确认 | U/I/H | W05 |
| B05! | 普通文件/Base/论文/PDF→Python identity→正确模式/key | 同名不同 key、未知/模糊路径、重命名、快速 A→B、旧响应晚到；无 TS 猜 key、无串论文 | U/I/H | W06 |
| B06 | Overview/Dashboard/collection/paper 多视图状态一致 | 从未开 Settings 的冷启动、空库、缺数据源、stale/unknown、失败后 Refresh/Doctor 恢复 | U/I/H | W06 |
| B07! | do_ocr/analyze 勾选→规范 note 仅目标字段变化→重启保持 | CRLF/LF/BOM、inline fence、无/坏 frontmatter、非法 flag、重复值、后端拒绝、外部编辑；失败 checkbox 回退 | U/I/H | W06 |
| B08! | 卡片/列表/正文/PDF/版本入口打开正确文件并可返回 | 文件缺失/移动、旧路径、越界、focus 切换；断言实际 active file/key，不能只 spy openFile | U/I/H | W06 |

### C — Search、Read、Knowledge、Agent

| ID | 用户工作流与可观察成功结果 | 必测失败/边界及保护证据 | 层级 | 工作包 |
|---|---|---|---|---|
| C01 | M 元数据搜索命中准确 key，过滤/domain/collection 范围正确 | 空白/中文/引号/特殊字符、无结果、DB 缺失；输入文字不变成 FTS/命令注入 | U/I/H | W07 |
| C02 | 连续输入/切 M与@/键盘 Enter、Ctrl+Enter、结果导航 | Q1 晚于 Q2、请求失败再 Retry、空列表键盘操作；不显示过期结果，不假导航 | U/I/H | W07 |
| C03! | @/deep retrieve 返回正确论文片段，可追溯原文 | vectors 未建/stale/model-changed、reader gate、无正文、401/429/超时；故障不是“无结果”，错误建议来自 authority | U/I/H/V/Q | W07 |
| C04 | read literal 在 fulltext/PDF 返回正确行/页/内容 | regex 字符按 literal、无匹配/无可读源/坏 PDF 分开；只读与 scope 保留 | U/I | W07 |
| C05! | paper-lookup/context/status 与 content-discovery/navigation/scoped-fetch/query-plan 正确限定对象 | key/DOI/citation/路径模糊、缺结构、未知对象、超范围；无幻造来源、无越界内容 | U/I | W07 |
| C06 | reading-log 写/读/导入/导出/validate/correct 与关联论文一致 | 坏 payload、重复提交契约、纠正链、导入失败；原记录保留，重建 DB 后可读取 | U/I | W08 |
| C07 | project-log、context/agent-context、deep-reading/deep-finalize 形成完整记录与状态 | 错 key/缺产物/重复 finalize、无 index/DB、invalid JSON；无假完成或无来源内容 | U/I | W08 |
| C08! | Agent platform/skill 部署与 UI 状态、生成内容对应 | 目标冲突、拒绝 overwrite、不可写、重部署、平台选择变化；自定义内容受保护，不宣称未验证的 live agent 连接 | U/I/H | W08 |

### D — OCR、Derived、Versions

| ID | 用户工作流与可观察成功结果 | 必测失败/边界及保护证据 | 层级 | 工作包 |
|---|---|---|---|---|
| D01 | OCR workspace 筛选/搜索/分页/选择/详情显示正确 | 零行、跨页选择、刷新后对象消失、隐藏选择；明确显示实际 batch scope，不偷换 all | U/I/H | W09 |
| D02! | 命令/Settings/Dashboard/Workspace 发起 OCR→确认→实际范围执行 | 拒绝/缺 secret/busy/未知 action/双击；每种独立 dispatch 入口至少一条 H，未确认零网络提交 | U/I/H | W09 |
| D03! | OCR 逐篇 progress/settlement→对应产物→刷新及后续任务 | A成功/B失败/C未选、pending/degraded/noop；汇总与逐篇一致，follow-up 不扩大到失败项 | U/I/H | W09 |
| D04! | Stop→单一 cancelled/既定终态→安全恢复 | 提交前后、发布前、完成竞争、协作停止无响应；正确进程树退出，远程提交不确定时不盲目重发 | U/I/H | W10 |
| D05! | 后端 redo/resume 与 UI 对外契约一致，故障后旧内容可恢复 | redo 中断/orphan、重复 resume、submitting、不存在 job/PDF；不新增已删除 ocr.redo action，不把 UI redo 擅自当同名 CLI | U/I/H | W10 |
| D06! | 本地 rebuild derived 从已有 raw 产出一致 lineage/结构/显示 | raw 缺失/坏、备份/写入失败、取消、部分成功；受保护 raw 不变，无远程调用，失败不发布 ready | U/I/H | W11 |
| D07 | Version History modal 与独立版本模式：列、选、预览、比较 | 无版本/坏 manifest/缺文件/legacy backup/大文本、切论文、两页入口不等价；每个可见按钮有行为或明确不可用 | U/I/H | W12 |
| D08! | 显式选 v1→取消零变化→再确认 restore→正文/provenance 读回→同沙箱重启 | label traversal、symlink、源改变、写失败、provenance 部分失败；raw/index/vector 不误改，终态诚实 | U/I/H | W12 |
| D09! | 旧版本清理控件的可用性/范围/确认与真实 authority 对齐 | 若没有获批清理能力：不可保留无反馈可点击按钮，也不可为测试临时造删除能力；owner 定义行为后验证保留当前/保护版本与恢复 | U/I/H | W12 |

### E — Memory、Embedding、Maintenance

| ID | 用户工作流与可观察成功结果 | 必测失败/边界及保护证据 | 层级 | 工作包 |
|---|---|---|---|---|
| E01! | memory.build/rebuild→精确 DB/FTS rows→新查询命中 | fresh DB/scoped、unknown keys、schema 变化、busy、幂等；目标与旁观范围正确，不只 ok | U/I/H | W13 |
| E02! | memory restore-backup 验证备份→替换→新进程查询成功 | 坏/缺备份、replace失败、锁/占用；保留原 DB/坏副本/备份，UI 不误报全恢复 | U/I/H | W13 |
| E03! | embed.build/resume 确认→批处理→发布→真实 retrieve | 各 scope、force/resume 冲突、model/dimension 变化、partial/401/429；lineage 绑定正确，未完成不 ready | U/I/H | W14 |
| E04! | embed Stop/崩溃→恢复→已完成工作不重复或丢失 | publish 前后取消、同库 readers/writers、scoped shadow 限制；旧可用索引保留或明确不可用，不混用新旧模型 | U/I/H | W14 |
| E05! | embedding 后端迁移→status→检索验证 | 旧格式/缺扩展/重复迁移/写失败；失败保留旧可恢复状态，迁移成功有内容证据 | U/I/H | W14 |
| E06 | Doctor/repair/path repair：诊断→明确动作→再诊断 | 无可修项、不可修、权限拒绝、路径过期；scan 只读，fix 只改承诺字段，失败可见且可重试 | U/I/H | W15 |
| E07! | orphan preview→拒绝零变化→prune→trash list→restore→必要 rebuild→读取 | 各 carrier 残留、确认后源状态变动、空/根/越界路径、原路径已存在、部分失败；purge 仅明确 trash 范围，旁观文件保留 | U/I/H | W15 |

### F — Render、控制面、UX/帮助

| ID | 用户工作流与可观察成功结果 | 必测失败/边界及保护证据 | 层级 | 工作包 |
|---|---|---|---|---|
| F01! | render audit 报告真实问题→staging 展示真实候选证据 | FAILED/unknown、重复 figure_id/错图/缺图/同 claim；报告写入不等于审计通过；staging 不写生产对象 | U/I/H/Q | W16 |
| F02! | R promote：明确对象→确认→CAS/journal/post-audit→再执行 noop | stale snapshot、越界成员、冲突、写失败、crash/recovery；不重建 inventory，不绕过 owner 批量 gate | U/I/H | W16 |
| F03! | P accept：审阅实际图/成员/plan hash→确认→规范产物更新 | hash 过期/伪造/身份冲突/并发修改/post-audit失败；精确授权，安全 rollback，报告刷新失败不误回滚 commit | U/I/H | W16 |
| F04! | reconcile/preflight/describe/list 与 next_actions 展示、执行一致 | read-only、unknown id、duplicate/cycle/depth、失败父任务、确认后变更；只有允许的 local automatic inline，收费/危险项 pending | U/I/H | W02 |
| F05 | Overview/模块详情/Help/各真实目的地导航，zh/en、明暗、窄宽面板可用 | loading/empty/error/disabled、Tab/Enter/Space、focus恢复/trap、reduced motion；无 raw key/遮挡关键操作 | U/H | W17 |
| F06! | trace toggle/copy/clear、诊断草稿、报告分享 | 秘密/个人路径/标题脱敏按分享契约；不静默上传、不自动发帖；关闭 console trace 不影响基本功能 | U/I/H | W17 |
| F07 | Help 在线/离线、release notes 初次与已读、重开行为 | 网络错误、畸形内容、modal 拦截；有可恢复说明，不用统一 Escape 吞掉未知产品错误 | U/H | W17 |
| F08 | 更新后 probe/dashboard/Settings/workspace 同步刷新 | 冷启动、旧缓存、窗口切换、mutation失败/部分提交后的 refresh；不以陈旧状态显示 ready，不把错误淹没在 console | U/I/H | W06 |

### X — 横切稳健性（应用到代表任务，不复制全笛卡尔积）

| ID | 必须守住的可观察契约 | 最低代表任务/故障点 | 层级 | 工作包 |
|---|---|---|---|---|
| X01! | 真实 subprocess JSON/text/NDJSON、退出码、UTF-8 chunk/framing、stderr 分流 | probe/read/action stream；split multibyte、CRLF、partial最后行、bad schema/event/EOF/extra terminal；严格按冻结契约 | U/I | W02 |
| X02! | scope/identity/path/secret 与内容渲染信任边界 | 多 key、空/重复/未知 key、shell metachar、Unicode/长路径、symlink/junction retarget；BBT/检索片段/远程Markdown或HTML不能执行脚本、注入事件或越权打开协议/文件；无法可靠防御的威胁交owner决策，不宣称安全 | U/I/H | W18 |
| X03! | 并发与读写时序 | 双击、跨视图与跨进程writer、autosync+手动、Q1/Q2、mutate后旧read到达、锁持有者退出；两个vault共享机器运行时/凭据时仍按契约隔离数据、cache与任务，更新不破坏另一vault运行中的任务 | U/I/H | W18 |
| X04! | 取消/强杀/中断后的单一诚实终态与恢复 | OCR/embed/setup；启动前、提交后、publish前、publish后；Windows task tree/POSIX group | U/I/H | W18 |
| X05! | I/O/崩溃下原子性与可恢复性 | versions restore、DB restore、prune、runtime pointer、R/P journal；临时写完/rename前后/部分对象完成 | U/I/P | W18 |
| X06! | 网络失败不变成假成功、无限重试或意外花费 | loopback provider 的401/403/429+Retry-After/5xx/超时/断连/坏 JSON；deadline与取消可达 | U/I/H | W18 |
| X07! | dry-run/预检/拒绝/幂等与旁观保护 | config migrate、sync、prune、R/P、memory；定义允许 telemetry 后检查业务 diff，不假要求所有文件零变化 | U/I/H | W18 |
| X08 | 性能与 timing 语义：非负、单位、阶段条件、wall total不重复求和 | 冷/热开、sync、搜索、模式切换、大版本 diff、Stop响应；记录 p50/p95与样本数，不把 timeout 当性能预算 | I/H | W18 |
| X09 | 长时间使用不积累异常资源 | 多次开关 view/plugin、连续搜索/刷新、长任务；进程/listener/内存趋势、UI可响应，停止后回到可用状态 | I/H | W18 |
| X10! | 候选在所有声称支持的 OS/arch/app/installer 上运行 | 固定 app+installer；latest+旧兼容installer；最低支持版；真实 keyring/SQLite扩展/文件锁专项 | I/H/P | W19 |
| X11! | 测试独立、可靠、无旧产物与假阳性 | build hash、沙箱逃逸保护、同沙箱重启 vs 新副本、autosync隔离、故意错误结果应使测试失败 | U/I/H | W01 |
| X12 | 稳定性证据而不是重试洗绿 | 关键 H 首次通过率、独立/随机顺序、固定 seed 的状态序列、首次失败证据保存 | I/H | W19 |

### R — 内容、发布与 owner 验收

| ID | 验收任务 | 明确证据 / 阻塞条件 | 层级 | 工作包 |
|---|---|---|---|---|
| R01! | 真实 OCR/embedding provider 与 OS credential adapter 小规模验收 | 专用凭据/公开样本、审批范围与费用上限、请求/模型版本、实际产物/检索、redaction；无授权即 BLOCKED | H/V | W20 |
| R02! | OCR/图表身份/检索相关性质量回归 | 人工真值、数据集hash、来源许可、指标/阈值先固定；错论文/错图身份零容忍；不能只看ok或文件存在 | Q/V | W20 |
| R03! | 版本/tag/plugin/backend/schema/依赖/兼容窗口一致 | 规范版本、root/plugin manifest、versions.json、bundle内版本、wheel metadata、lockfile；不假定package.json每个字段都必须相同；禁用发布上传的演练验证合法/非法tag与资产完整性 | P | W21 |
| R04! | 干净环境安装准确待发 wheel+插件文件 | 源码checkout不在import路径；wheel运行与bundle hash绑定；main.js/styles.css/manifest.json及承诺资源齐全，安装/映射文件与实际release资产核对；新装/已有vault/离线读取/真实UI smoke | H/P | W21 |
| R05! | 准确 SHA 的完整 CI/候选认证与结果矩阵 | §0发布前业务集全部适用变体VERIFIED，required jobs绿色；不把R05自身或R07/R08作为已通过前置；源码/产物改变重绑证据 | I/H/P | W22 |
| R06! | 发布说明、迁移/回退指引、隐私与已知限制 | 声明实际支持范围，给出恢复步骤；未满足承诺的必测项阻塞，不靠文案隐藏功能缺失 | P | W21 |
| R07! | owner发布授权、唯一发布链及可恢复发布失败 | 版本/SHA/hashes精确签字；tag与Python pre-release格式核对；PyPI→GitHub部分失败可补齐不误发新版本 | P | W23 |
| R08! | 发布后从实际分发资产安装 smoke 与受控观察 | 校验下载hash、新装/升级关键任务、错误/延迟/内容/费用观察；停止扩大发布和回退/撤回策略可执行 | H/P/V | W23 |

## 6. 九个 action 的专属契约

这是规划基线 `action list --json` 的观察，不用该表覆盖未来经过批准的 registry 变更。W00/W02 重新核对差异。

| action_id | scope | 确认 / 自动 | execution_mode | 最低业务证据 |
|---|---|---|---|---|
| foundation.update | all | required / false | stream | A06 |
| foundation.repair | all | required / false | result | A06 |
| memory.build | all,papers | none / true | result | E01 |
| memory.rebuild | all | none / true | result | E01 |
| library.prune | all | required / false | result | E07 |
| embed.resume | all,papers | required / false | stream | E03、E04 |
| embed.build | all | required / false | stream | E03、E04 |
| ocr.run | all,papers | required / false | stream | D02、D03、D04 |
| ocr.rebuild_derived | all,papers | none / true | stream | D06 |

所有 action 经同一个 runner 验证通用拒绝/确认/未知 action/scope 契约；每个 handler 再验证自己的真实效果，不能只 snapshot registry。注意当前 library.prune 的 impact 是 mutating，但明确 required/nonautomatic；测试必须守住实际确认行为，不在验收计划里擅自重分类为 destructive。result/stream 的取消能力按真实 API 与 UI 合同测试，不假定所有 result 操作都提供可见 Stop。

## 7. 跨任务旅程（每条必须具备真正的前后结果）

| ID | 操作序列 | 验收与保护 | 工作包 |
|---|---|---|---|
| J01 | 新文献进入导出→UI Sync→memory更新→M搜索→点击打开 | 一个明确key贯穿；旁观笔记保留；不由启动autosync代跑 | W05 |
| J02 | 选择A/B→拒绝一次→确认OCR→A成功/B失败→后续任务→打开A | 拒绝零提交；逐篇终态与范围正确；C完全不动 | W09 |
| J03 | OCR/embed运行→Stop→终态→重启同沙箱→恢复 | 旧内容可用、锁/进程恢复、无盲目重发、完成项不丢 | W18 |
| J04 | 向导改model/base→Python读回→重启→详情页→受控请求 | 两个入口与后端同值，失败有反馈，未写到另一vault | W03 |
| J05 | 显式选择v1→预览→取消→再确认→跨视图→重启 | 正文精确、provenance结果诚实、raw/index/vector保护 | W12 |
| J06 | orphan preview→拒绝→prune→trash→restore→rebuild→搜索 | 各carrier范围明确；文件恢复不冒充DB/向量同步恢复；保护对象字节一致 | W15 |
| J07 | 正常查询→备份→损坏DB→诊断→恢复→新进程检索 | 不假零结果；恢复失败不破坏可用备份；真实内容恢复 | W13 |
| J08 | 安装Release-N→用户写笔记/配置→升级候选→重启→规定回退 | 真实旧包、明确支持窗口、用户内容不丢、旧版可用性有实证 | W21 |

## 8. 分阶段工作包与阻塞关系

**所有工作包当前均为 PLANNED。** 下表的 Depends 是真实前置边，不表示允许同一 worktree 多 writer。不同领域可并行只读调查；写入仍按项目一 writer 规则。这里定义拆票边界，不为每包预设固定测试数量。

| 包 | 阶段 / 工作内容 | Depends | Cases / 范围 | 完成标准 |
|---|---|---|---|---|
| W00 | Contract：发布范围与验收PRD对齐 | — | 全表入口盘点；#81/#83与封存契约差异；版本/平台/质量/性能/费用决策 | 新PRD与子票链接可追溯；所有入口有case；阈值和支持范围在运行前批准，旧issue冲突已解决或明确BLOCKED |
| W01 | Harness：真bundle、隔离与独立oracle | W00 | X11；旧7条通用整改；fixture/证据基础 | build先于WDIO且校验hash；安全root、网络/用户状态隔离；同沙箱重启演示；无旧trace假成功 |
| W02 | Protocol：真实transport/action/preflight/chain | W01 | X01、F04；全部9 actions通用契约 | 真Node→Python进程证明JSON/text/stream与错误语义；非法协议拒绝；确认、scope、follow-up边界有效 |
| W03 | Config/Auth：两UI入口与持久化 | W02 | A03、A04、A05、J04 | 每项改动Python读回+重启；拒绝/rollback/secret脱敏；实际OS adapter范围列明，live部分由W20汇总 |
| W04 | Lifecycle：新装、运行时、启停 | W02、W03 | A01、A02、A06、A07 | 干净安装、失败/取消、指针和进程安全；已安装后端离线可用；未测试triplet不宣称支持 |
| W05 | Library：同步与自动收敛 | W02 | B01、B02、B03、B04、J01 | 增量精确diff、用户内容保留、autosync与手动独立、后续动作不越权；复用真实journey |
| W06 | Context：身份、标记与跨视图 | W05 | B05、B06、B07、B08、F08 | 无串论文、坏identity拒绝、checkbox失败回退、cold-open/refresh一致；Note字节边界覆盖 |
| W07 | Retrieval：搜索与只读gateway | W06 | C01、C02、C03、C04、C05 | UI输入/导航和真CLI读取范围正确；无结果与故障区分；Q/V部分交W20最终汇总 |
| W08 | Knowledge：日志、精读、Agent部署 | W03、W05 | C06、C07、C08 | 写读导入纠正/重启闭环；精读状态不假完成；自定义skill不被覆盖 |
| W09 | OCR：入口、scope、部分成功 | W02、W06 | D01、D02、D03、J02 | 各真实UI dispatcher至少代表路径；实际scope、确认、逐篇settlement、progress、下游刷新有证据 |
| W10 | OCR Recovery：停止、redo、resume | W09 | D04、D05 | 本地受控provider提交/停止/恢复链；协作/强杀/提交不确定边界；无意外真实收费 |
| W11 | Derived：本地重建 | W09 | D06 | 固定raw到产物的真实过程；cancel/write失败/partial；raw与未选论文保持；冻结源码缺陷另请批准 |
| W12 | Versions：全部入口和恢复 | W06、W11 | D07、D08、D09、J05 | 精确选版本、取消、restore+provenance、重启；旧模式死按钮按批准产品行为解决；不自行增删能力 |
| W13 | Memory：构建与备份恢复 | W02、W05 | E01、E02、J07 | 精确DB/FTS与内容查询；scoped/fresh/corrupt/busy；replace失败与同库重启恢复 |
| W14 | Embedding：构建/迁移/恢复 | W07、W13 | E03、E04、E05 | 受控HTTP服务与真worker、shadow发布、取消/模型变化/partial/reader gate；实际查询验证 |
| W15 | Maintenance：诊断/清理/恢复 | W05、W13、W14 | E06、E07、J06 | 各carrier orphan+旁观对象、拒绝、trash/purge安全；恢复契约真实而非文件存在即成功 |
| W16 | Render：冻结R/P契约验收 | W11、W12 | F01、F02、F03 | 仅沙箱的图像证据、hash/CAS/journal/post-audit与recovery；生产batch gate不变 |
| W17 | UX：语言、键盘、诊断与帮助 | W03、W06、W09、W12、W15、W16 | F05、F06、F07 | 全部现存页面/关键状态zh-en、明暗/窄宽；焦点可达；错误/分享不泄漏；帮助离线可恢复 |
| W18 | Resilience：故障、竞态与性能 | W04、W07、W08、W10、W12、W14、W15、W16 | X02、X03、X04、X05、X06、X07、X08、X09、J03 | 可重现的代表故障点、状态序列、无越界/误提交；批准性能预算与soak通过，保存首次失败证据 |
| W19 | CI：跨环境与稳定性门禁 | W01、W02 | X10、X12；ci.yml与publish.yml证据连接 | 固定版H进入All Checks Passed，定时latest/installer矩阵；禁用所有上传/发布动作的门禁演练覆盖success/failure/pending/missing/skipped/cancelled、错误SHA/错误workflow或过期attempt；后续领域case持续纳入 |
| W20 | Quality/Live：真实服务与内容验收 | W03、W07、W10、W14、W16、W18、W19 | R01、R02；A05/C03/F01的V/Q证据 | 事前批准样本/费用/阈值；真实OCR+embedding与keyring支持环境；质量无已知身份错误，费用与隐私可控 |
| W21 | Release Artifact：安装升级与文档 | W04、W08、W12、W15、W17、W19 | A08、R03、R04、R06、J08 | wheel+完整插件资产干净安装；Release-N升级/回退；tag格式/manifest/资源/hash与部分发布失败恢复先无副作用演练；迁移说明与支持声明一致 |
| W22 | Certification：最终候选统一认证 | W18、W19、W20、W21 | R05；全部发布前适用cases最终重绑 | 无未解决阻塞；准确SHA/产物下完整门禁绿色；证据索引完整；owner接受后标RELEASE_READY，不发布 |
| W23 | Publication：owner授权与发布后验证 | W22 | R07、R08 | owner另行签版本+SHA+hashes；唯一发布链；实际下载资产smoke；观察/回退机制执行后标RELEASED |

### 8.1 每包允许改什么

- W01/W19：现有测试配置、fixture、runner/CI证据集成；不另建第二套测试框架或发布编排。
- W02：现有client/transport与Python契约测试；只在复现发现真实缺陷时修正契约内实现。
- W03–W17：对应业务现有测试和必要产品修复；不做无关重构。前端相同文件的多任务必须顺序集成。
- W18：现有seam的故障注入/状态测试；能用subprocess barrier、临时FS、HTTP边界就不加生产配置/隐藏测试按钮。
- W20：评估样本与真实运行证据，不把质量阈值下降当修复；算法变化需要独立issue与scope批准。
- W21/W23：现有版本/打包/发布流程的必要加固；不创建第二个tag发布workflow。

### 8.2 每个实施 issue 的标准模板

- Parent PRD / 当前 issue / updated_at / base SHA / worktree。
- 本票负责的 case IDs、用户可观察行为、非目标。
- 现有测试与seam；精确重现命令；测试前置fixture与保护对象。
- 红阶段：违反契约的最小输入或真实UI动作能使测试失败；不能靠断言源码字符串或mock echo制造覆盖。
- 绿阶段：最小修复；准确命令和可观察证据；H问题必须跑H，I不能替代。
- Acceptance：每个case的正常/失败/恢复/持久化明确；补测不是降低原断言。
- Closeout：一次Standards/Spec review、集中修复、一次re-review；仍有重要缺陷就回验收契约或拆票。最后修改后重新验证，再按项目规则提交。
- Status/证据回写真实issue，ledger/queue只投影；下票新会话。发布命令不属于普通实施票默认授权。

## 9. 验证命令与测试落点

### 9.1 现有命令（在对应权威worktree执行）

仓库根：

```text
python -m paperforge --help
python -m paperforge action list --json
python scripts/check_version_sync.py
python -m pytest tests/test_action_registry.py tests/test_chain.py tests/test_reconcile.py tests/cli/test_json_contracts.py tests/cli/test_ocr_progress_contracts.py -q
python -m pytest tests/test_config.py tests/test_credentials.py tests/test_note_set_flag.py tests/test_versions_command.py -q
python -m pytest tests/test_memory_build_scoped.py tests/test_memory_restore.py tests/test_embed_scoped.py tests/test_shadow_rebuild.py -q
python -m pytest tests/journey/ tests/integration/ -q
python -m pytest tests/e2e/ -m e2e -q
```

插件目录 `paperforge/plugin`：

```text
npm ci
npm run typecheck
npm run build
npm test
npm run test:e2e
```

准确依赖、平台skip、安全fixture必须先按实际CI与该issue确认。上面的focused命令是已有文件的入口，不代表整仓suite；不得无检查地跑历史固定vault脚本。最终必需suite以W00/W19审定的required清单为准，避免仅跑tests/unit漏掉根层业务测试。

W01需让e2e入口自身保证build/fixture的顺序；当前命令还不保证。W19补充分组选跑、矩阵与证据汇总后，将新增的**实际可执行命令**填回对应issue和本节；本文不把尚不存在的脚本写成已经可以运行。

### 9.2 复用位置

| 业务 | 优先复用 |
|---|---|
| client/transport/action | `paperforge/plugin/tests/client/`、`tests/long-task-client.test.ts`（插件目录下，历史名称）、`tests/test_action_registry.py`、`tests/cli/`、`tests/test_chain.py` |
| sync/identity/note | `tests/journey/`、`tests/e2e/test_sync_pipeline.py`、`tests/test_paper_lookup_from_path.py`、`tests/test_note_set_flag.py`、插件dashboard/runtime测试 |
| OCR/versions/render | `tests/test_ocr_control_plane.py`、`test_ocr_redo.py`、`test_ocr_rebuild.py`、`test_versions_command.py`、`test_render_audit.py`、`test_promote_r.py`、`test_accept_proposal.py` |
| memory/embed/retrieval | `tests/test_memory_build_scoped.py`、`test_memory_restore.py`、`test_embed_scoped.py`、`tests/embedding/`、`test_shadow_rebuild.py`、`test_layer4_gateway_commands.py` |
| runtime/config/auth | `tests/test_config.py`、`test_credentials.py`、`test_update_lifecycle.py`、`test_runtime_pointer.py`、`test_setup_plan_v2.py`、插件managed-runtime/secret-storage测试 |
| prune/trash | `tests/unit/worker/`、`tests/test_no_raw_delete.py`、插件maintenance相关测试 |
| 真宿主 | `paperforge/plugin/test/specs/` 与现有fixture builder；按业务拆spec，避免一条巨型串行旅程掩盖独立失败 |

不要机械保留现有测试：若只锁定文案、内部函数调用、源码子串或mock回声，替换成可观察行为判据；架构权限静态gate作为单独约束保留，不冒充功能验收。

## 10. CI、兼容性与稳定性策略

### 10.1 运行频率

| 频率 | 内容 | 阻塞规则 |
|---|---|---|
| 每票本地 | 与改动相关的U/I与至少一条真实表面H；修改Python执行针对性Ruff | 最后修改后失败不提交closeout |
| 每PR | 现有required jobs + 固定Obsidian版本的关键H + 真实进程契约/业务覆盖 | All Checks Passed显式needs所有required job；未运行/skip不算绿 |
| 定时 | latest app、旧兼容installer、支持OS/arch、完整H、状态序列/soak/稳定性 | 不能用定时job替代RC准确SHA验证；失败形成阻塞或明确可归因的环境问题 |
| RC认证 | 在准确候选产物上跑所有适用U/I/H/P，V/Q证据按契约重新绑定 | 关键项全部首次通过，无未解释flaky；不承认旧SHA green |
| 发布后 | 实际分发资产安装与关键业务smoke、受控观察 | 失败停止扩大发布，按恢复手册处置 |

### 10.2 支持矩阵

- PR用固定app/installer具体版本保证复现；nightly跟latest，记录解析后的版本。
- 每个正式支持triplet都必须有原生CI或等价可保存证据的runner。不能从“ubuntu runner通过”推导Windows/macOS/ARM通过。
- 当前manifest `minAppVersion=1.11.4`、desktop-only。最低app+其兼容旧installer、当前app+当前installer、当前app+兼容旧installer至少作为组合类别；具体版本W00/W19锁定。
- Windows：路径/文件锁/task tree/junction；macOS：keyring/SQLite扩展/签名与实际支持arch；Linux：venv/共享库/桌面展示环境。明确Flatpak/Snap等是否支持，不凭测试service支持能力扩大产品承诺。
- Python版本以实际包和runtime契约的上下界测试，Node以构建契约为准；不要把运行Obsidian的Electron与构建Node混淆。
- zh/en、明暗、620/730px附近面板与宽屏至少代表覆盖；键盘、focus、reduced motion是功能验收，不只是截图好看。

### 10.3 稳定性与性能预算

W00先批准预算，W18按统一设备/fixture测量。建议起始认证协议：关键H固定环境连续20轮无未解释首次失败；完整H至少3轮且有不同顺序；另测30分钟代表交互/任务soak。这些是**本项目建议的验收采样量，不是行业标准或可靠性保证**；owner可在开跑前调整并记录理由，不能失败后临时降低。

预算表在W00必须填实值：cold first-use、warm panel、metadata query、mode switch、sync按库规模、Stop反馈与安全结束deadline、version compare、峰值/稳态内存趋势。p50/p95必须有足够样本并报告n，单次运行不称p95；网络provider响应与本地开销分开。全部功能timeout只是上限，不等于性能目标。

## 11. 真实provider、质量集与canary

### 11.1 Live gate

- owner先批准provider/model/version、专用credential存放、公开样本列表、请求次数/费用上限、网络目的地、日志脱敏与保留策略。
- 真实OCR：至少一份含正文+图+表的代表PDF，真正提交/轮询/产物/打开；真实embedding：批准的小批内容→向量→相关查询→来源回读。所需广度由W00冻结的支持声明决定，不把一份PDF泛化为所有版式。
- 401/429/断网等确定性故障主要在本地provider做，不主动耗尽真实配额。真实服务未测试的能力明确BLOCKED，不能以不可达endpoint测试替代成功链。
- 实际keyring行为在隔离账号或测试命名空间验证，结束后按专用标识清理，不碰用户已有secret。

### 11.2 Quality gate

- 固定数据集hash/许可/标注来源，保留开发与验收样本的区分；对图像身份必须看图/人工真值，不只文件名/尺寸匹配。
- OCR：正文保真、阅读顺序、图表身份、caption绑定、引用/结构可追溯；检索：按任务标注相关性与证据支持，报告Recall@K/MRR或经批准指标及失败个案。
- 阈值在W00/W20正式运行前锁定；身份串论文/错图、不可恢复数据损失为零容忍。其他质量指标至少对比指定Release-N基线，不得掩盖已知回归。
- 算法缺陷若位于冻结前OCR/render文件，需另行批准修改范围；未修复的本版承诺内缺陷保持No-Go，不以“属于算法”绕过。

### 11.3 Canary gate

- 测试通过不自动授权生产canary。先沙箱回放，再由owner明确授权用户/论文/对象范围与持续时间；R/P生产权限单独签。
- Canary至少跨一个完整工作单元与恢复过程；观察成功/错误、延迟、内容正确、scope、远程费用，而不是只看进程没崩。
- 出现误写/误删/secret泄漏/错误身份/重复远程提交/无法恢复立即停止，不继续扩样。恢复流程只操作本次scope；不能自动拿旧快照覆盖用户期间的新修改。
- 若发布范围不含生产R/P rollout，保留其gate并在发布说明明确；不是把该能力的沙箱安全测试删掉。

## 12. 发布前 Go / No-Go 清单

### 12.1 W22：RELEASE_READY 必须全部满足

- [ ] G01：W00范围、支持窗口、阈值、每个case与真实issue/测试映射已批准；无未归属可见入口。
- [ ] G02：§0明确定义的发布前业务集及其所有适用变体/层级VERIFIED；R05由本次认证产出，R07/R08留待发布阶段。未完成、BLOCKED、未经批准skip均为No-Go。
- [ ] G03：本版scope内已知产品缺陷已修复；没有P0/P1遗留、无未解释首次失败。已有历史failure也要解决或经owner明确证明不适用，不能简单称“pre-existing”。
- [ ] G04：准确candidate SHA与plugin/wheel/config/fixture hashes冻结；所有验收针对准确产物，import没有串入源码或旧安装。
- [ ] G05：完整required CI通过，包含真实进程与真Obsidian；聚合/发布gate已无副作用演练，只有受信workflow的正确SHA与有效run/attempt能放行，缺job/取消/skip/过期green均不能误放行。
- [ ] G06：所有正式支持OS/arch/app/installer/运行时组合有有效证据；没有用“service支持”代替实测。
- [ ] G07：拒绝/取消/崩溃/并发/IO/网络/路径/secret安全项均通过；备份、恢复、旁观保护得到验证。
- [ ] G08：干净发布包安装、Release-N升级与规定回退路径通过；数据降级限制和支持窗口明确。
- [ ] G09：真实provider、OS adapter与质量gate完成，批准费用内运行；无身份/内容不可接受回归。
- [ ] G10：稳定性/性能/UX/a11y/i18n预算满足；首次失败与重试记录可审计。
- [ ] G11：发布说明、迁移/备份/回退、隐私、支持范围、已知非阻塞限制与实际行为一致。
- [ ] G12：最终Standards/Spec与owner证据接受完成；ledger/queue引用本候选，不引用旧green作为当前真相。

任一G未满足就保留No-Go。若最后修改了代码、依赖、bundle、默认配置、打包内容或测试断言，重新冻结与运行受影响gate；发布前最终required gate仍在最后候选完整跑一次。纯文档变更也须记录与产物的绑定，不能直接把别的SHA发布权限挪过来。

V/Q 的复用也受候选绑定约束：先前证据只能在可证明相关源码、依赖、配置、模型和产物内容未变时由 owner 接受复用；否则对最终候选重新执行批准范围内的 live/质量验证，费用需重新核对。仅修改报告中的 SHA 字段不是“证据重绑”。

### 12.2 W23：授权与发布

- [ ] owner显式批准准确版本、tag、source SHA、plugin/wheel hashes、平台范围、支持窗口与发布渠道。
- [ ] tag格式同时满足Python packaging与Obsidian分发规则；特别核查当前publish脚本对`v`/数字tag及pre-release的识别，不用未经测试的RC版本字符串。
- [ ] 唯一publish workflow等待正确SHA完整gate，并消费/验证已认证产物；若发布时重建，必须hash一致或重新认证，不能认证A发布B。
- [ ] wheel与GitHub Release资产完整，checksums可核验；PyPI已发但GitHub失败时可安全补齐，不能删除历史版本或静默覆盖不一致产物。
- [ ] 从实际下载渠道在干净环境安装，做新装/升级/查询/一次获准本地mutation smoke。
- [ ] release notes与安装说明可见；观察窗口和owner响应责任明确。
- [ ] 发现严重问题时停止扩大发布，记录用户恢复步骤；版本回退与数据恢复分别验证，必要时用新修复版本/平台支持的撤回机制处理，不能假定发出的包可无痕撤销。

只有完成以上发布后项才标RELEASED。W22完成后等待owner不是失败，也不是“全部已发布”。

## 13. Owner 决策与外部前置条件

这些值不能编造，但不影响先写计划/补确定性测试。W00负责把决定写入真实父issue，后续case不能默默用默认值冒充批准。

| 决策 | 何时必须落定 | 未落定的影响 |
|---|---|---|
| 新插件版本、后端兼容范围、Release-N实际版本、回退支持窗口 | W00，最终W21前重核 | A08/R03/R04与发布阻塞 |
| 正式支持OS/arch/Obsidian app/installer/Python范围 | W00/W19 | 无对应runner则支持声明或gate阻塞，不能暗中缩水 |
| 旧issue与sealed新契约的冲突处理、新验收PRD归属 | W00 | 相关实施issue不能ready-for-agent |
| 版本清理按钮的产品语义（实现/明确禁用/经批准移除） | W12前 | D09阻塞，禁止临时加未经审核的删除API |
| 质量数据集/指标阈值与性能预算/稳定性采样 | W00确定协议，W18/W20运行前锁定 | R02/X08/X12不能判PASS |
| live provider测试账号、样本、次数、费用上限 | W20前 | R01阻塞，但本地受控provider测试继续 |
| 生产canary与R/P具体写权限 | 任何生产动作前 | 不影响沙箱测试；禁止生产操作 |
| 最终发布授权与观察/回退负责人 | W23前 | 保持RELEASE_READY，不打tag/发布 |

## 14. 本次文档交付与后续记录

- 本文替代旧的CLI模拟GUI验收草案和7-journey上限计划；原文移入archive保留历史，旧脚本未被删除/执行。
- [历史单点验收草案](../archive/2026-09-09-acceptance-test-plan.md)、[历史用户旅程草案](../archive/2026-09-09-user-journey-acceptance-plan.md)。历史命令/进度token/固定vault不可作为当前执行指令。
- [Active Queue](ocr-v2-active-queue.md) 仅记录优先级，指向本计划；[PROJECT-MANAGEMENT](../../PROJECT-MANAGEMENT.md) 仅记录会话和证据投影。
- 新case、入口差异、失败复现、阈值决定在真实issue中维护，再更新本矩阵引用。不得在文档里把新测试“预计通过”写成VERIFIED。
- 本次只写计划与文档索引；未实现新增测试、未修上述源码风险、未运行收费/生产任务、未创建发布tag或执行发布。

## 15. 工程量评估（2026-09-09，[INFERENCE]；用于排期，不是承诺）

### 15.1 实测基线

| 资产 | 实测 |
|---|---|
| Python 测试 | 236 文件 / 3431 个 `test_` 函数（190 文件在 `tests/` 根层；unit/cli/e2e/journey/integration/chaos/embedding/audit 子目录） |
| 插件 Vitest | 26 文件 / 459 个 `it` |
| 真宿主 E2E | 1 spec / 7 个 `it`（唯一 H 层资产） |
| 混沌测试 | `tests/chaos/` 3 文件，断言"不崩"，非恢复正确性 |
| Fixture | `tests/sandbox/`（exports、ocr-complete、TestZoteroData 等真实样本） |
| 发布资产 | GitHub Release 至 1.5.15（2026-06-01），A08/J08 的 Release-N 无需另造 |
| CI | 9 job；`All Checks Passed` 聚合；无 WDIO job |
| 上游 CI 配方 | 官方 sample：Linux 需 `Xvfb` + `herbstluftwm`，`.obsidian-cache` 缓存键，`WDIO_MAX_INSTANCES=2` |

结论：单元层已强，缺口在集成/宿主层。工程量主体是**测试基础设施 + 少量产品修复**，不是重写测试体系。

### 15.2 增量估算

| 工作包 | 新增 H 场景 | 新增/扩展 I·U | 产品修复 | issue 数 |
|---|---|---|---|---|
| W00 | 0 | 0 | 0 | 1 |
| W01 | 改现有 7 | 2–3 | 1 | 2–3 |
| W02 | 0 | 8–12 | 0–2 | 2 |
| W03 | 4–6 | 6–10 | 1–2 | 2–3 |
| W04 | 6–8 | 6–10 | 1–3 | 3–4 |
| W05 | 5–7 | 6–10 | 1–2 | 2–3 |
| W06 | 6–8 | 8–12 | 1–3 | 3–4 |
| W07 | 5–7 | 8–12 | 0–2 | 3 |
| W08 | 4–6 | 5–8 | 0–1 | 2–3 |
| W09 | 5–7 | 6–10 | 1–2 | 3 |
| W10 | 4–6 | 5–8 | 1–2 | 2–3 |
| W11 | 2–3 | 3–5 | 0–1 | 2 |
| W12 | 4–6 | 4–6 | 1–2 | 3 |
| W13 | 3–4 | 4–6 | 0–1 | 2 |
| W14 | 5–7 | 6–10 | 1–2 | 3 |
| W15 | 4–6 | 5–8 | 1–2 | 2–3 |
| W16 | 4–6 | 5–8 | 0–2 | 3 |
| W17 | 6–8 | 6–10 | 1–3 | 3 |
| W18 | 8–12 | 10–16 | 2–5 | 4–6 |
| W19 | 0 | 4–6 job | 0–1 | 3–4 |
| W20 | 4–6 | 2–4 | 0–2 | 2–3 |
| W21 | 4–6 | 3–5 | 1–2 | 3 |
| W22 | 0 | 证据索引 1–2 | 0 | 2 |
| W23 | 2–3 | 0 | 0 | 1–2 |
| **合计** | **60–100 条新增真宿主场景** | **110–180** | **15–40 处** | **57–75 issue** |

工期：57–75 个 issue 会话（1 会话 = 1 `/implement` + 1 `/review`）。每天 2–3 个有效会话约 4–6 周；每天 1 个约 2.5–3.5 个月。W20 外部等待与 W19 CI 迭代不计入纯编码。**不确定性 ±40%**，主要来自 W18/W19/W20。

### 15.3 成本驱动与不确定性

1. **W18 韧性** — 故障注入/并发/原子性最贵最难估；仓库历史显示每轮 review 会再发现 1–5 个 P1。
2. **H 层 7 → 60–100** — W01 完成后边际成本下降，首轮付基础设施税。
3. **跨 OS × Obsidian 版本矩阵** — 上游默认只跑 ubuntu；Windows/macOS 需自证；Linux 需虚拟图形栈。
4. **W20 live + 质量** — 成本是凭据、费用与人工标注工时；R02 若做扎实可能由人力主导。
5. **W21 Release-N 升级/回退** — 资产已有，但旧包安装/schema 迁移调试琐碎。

### 15.4 非工程阻塞

8 项 owner 决策（§13）；live provider 凭据与费用上限；质量数据集标注人力与许可；CI 分钟数（矩阵全开会让 PR 的 H 时间升到十几分钟，建议 PR 固定版本、nightly 跑矩阵）。

### 15.5 校准与建议

先做 **W00 + W01 + 一条完整竖切**（建议 B01/B02+J01，或 A03——顺带暴露已发现的配置旁路），产出：真实每 H 场景耗时与 flake 率、build-before-e2e 与沙箱隔离是否成立、产品修复真实密度。用这些数据把 57–75 收敛为可信数字，再决定全量执行或与 owner 明确缩小范围（缩范围须在 release notes 写清排除项，且需 owner 批准）。

**先手性价比排序：W01（harness 修好）→ W02（协议）→ W03（配置持久化，顺带修旁路）→ W12（死按钮）。** 四项完成即可证明工程可执行并立即产出真实缺陷。

## 16. 研究依据（方法，不是覆盖率承诺）

1. [Electron Automated Testing](https://www.electronjs.org/docs/latest/tutorial/automated-testing)：WDIO/Electron和Playwright路线；保留现有WDIO，无需换框架。
2. [WDIO Obsidian Service](https://jesse-r-s-hines.github.io/wdio-obsidian-service/wdio-obsidian-service/README.html)：社区service的沙箱/CI/多版本、app与installer区别；不是Obsidian官方验收标准。
3. [ObsidianBrowserCommands](https://jesse-r-s-hines.github.io/wdio-obsidian-service/wdio-obsidian-service/ObsidianBrowserCommands.html)：reloadObsidian复制语义、当前vault重启、serialized callback限制。
4. [WebdriverIO Best Practices](https://webdriver.io/docs/bestpractices/)：稳定selector、自动等待/断言、避免pause。
5. [Playwright Best Practices](https://playwright.dev/docs/best-practices)：用户可见行为、数据隔离、可控外部依赖；借鉴方法不新增第二runner。
6. [The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)：不同粒度、避免重复与过量高层测试，不使用固定比例配额。
7. [pytest Flaky Tests](https://docs.pytest.org/en/stable/explanation/flaky.html)：顺序/共享状态/后台任务、首次失败证据与隔离。
8. [Hypothesis Stateful Tests](https://hypothesis.readthedocs.io/en/latest/stateful.html)：操作序列与不变量；先用明确序列，必要时再用生成式工具。
9. [How SQLite Is Tested](https://www.sqlite.org/testing.html)：I/O/crash/fault injection与完整性验证；进程强杀证据不等于断电耐久性证明。
10. [Google SRE Canarying Releases](https://sre.google/workbook/canarying-releases/)：准确候选、小范围发布、可归因指标与工作单元完整观察；不能替代发布前测试。
