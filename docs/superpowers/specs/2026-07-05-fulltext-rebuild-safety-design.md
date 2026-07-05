# fulltext rebuild 安全设计

> 设计讨论：2026-07-05
> 状态：设计稿（待评审）

## 设计目标

本设计只解决一个问题：**当用户触发 OCR rebuild 时，如何在不引入多份常驻 fulltext 基线文件的前提下，保护用户可能对 `fulltext.md` 做过的修改。**

本设计不追求“自动迁移所有历史用户”。它只为**新用户**建立清晰、可验证、低惊扰的 rebuild 保护模型。

## 范围

### 目标内

1. rebuild 前自动备份当前 `fulltext.md`
2. 在 `meta.json` 中记录 machine provenance
3. 用 hash 判断 `fulltext.md` 是否偏离最近一次机器写入状态
4. 定义 backup retention policy
5. 明确新用户与 legacy 用户的行为边界

### 非目标

本设计明确不做：

- 对 legacy 用户做迁移引导或“可能有批注”提示
- 为 legacy 用户补建历史 machine baseline
- 常驻保存第二份 machine fulltext（如 `render/fulltext.md`）作为长期基线
- 通过 mtime 单独判断用户是否做过修改
- 把 vector rebuild 绑定为 OCR rebuild 的必选后续动作

## 当前问题

### 1. `fulltext.md` 兼具机器产物与用户工作文件角色

当用户把 `fulltext.md` 当作可读、可修、可批注的文本时，OCR rebuild 就不再只是“重建缓存”，而是可能覆盖用户资产。

### 2. 现有新布局里的双 fulltext 不应成为长期依赖

已经升级过的 vault 可能存在 machine side 的第二份 fulltext 副本，但把“双文件对比”作为长期机制会带来额外存储、路径复杂度和心智负担。设计应回到**单文件 + provenance**。

### 3. mtime 只适合做启发式，不适合做真相源

真实样本表明：`fulltext.md` 的修改时间可能晚于 OCR / rebuild 完成时间，但文本内容仍然完全一致。因此，mtime 不能单独作为“用户改过内容”的主判据。

## 核心原则

1. **Single fulltext**：长期只保留一个 `fulltext.md` 作为工作文本。
2. **Meta owns provenance**：机器写入状态由 `meta.json` 记录，不依赖第二份常驻 baseline 文件。
3. **Hash over time**：内容哈希比 mtime 更可靠；mtime 只作为辅助手段。
4. **Backup before destruction**：只要发生 rebuild，就先备份当前 `fulltext.md`。
5. **New-user first**：新用户有完整保护模型；legacy 用户不做升级 UX。
6. **Count-based retention**：backup 按数量保留，不按时间过期。

## 设计决策

## 1. 数据模型

machine provenance 放在每篇论文的 `meta.json`。

新增/规范字段：

- `ocr_finished_at`: 首次 OCR 成功完成时间
- `rebuild_count`: rebuild 次数，未 rebuild 时为 `0`
- `rebuild_finished_at`: 最近一次 rebuild 完成时间；未 rebuild 时为 `null` 或缺省
- `machine_fulltext_hash`: 最近一次**机器写入后的 `fulltext.md`** 的 SHA-256
- `last_backup_at`: 最近一次 rebuild 触发 backup 的时间
- `last_backup_path`: 最近一次 backup 的相对路径

派生语义：

- `effective_machine_time = rebuild_finished_at or ocr_finished_at`

注意：

- 不使用 `0` 作为时间 sentinel
- `rebuild_count` 表达是否 rebuild 过；时间字段始终保持“时间或空”

## 2. 基线模型

系统**不长期保存第二份 machine fulltext**。

唯一工作文本是：

- `fulltext.md`

最近一次机器写入状态通过 `machine_fulltext_hash` 表达：

- 当前 `fulltext.md` 的 SHA-256 与 `machine_fulltext_hash` 相同
  - 表示自最近一次机器写入后未改动
- 不同
  - 表示 `fulltext.md` 已偏离最近一次机器写入状态

这解决的是“当前文件是否偏离机器状态”，而不是保存所有历史版本内容。

## 3. rebuild 前的保护动作

只要用户触发 rebuild，系统一律：

1. 检查 `fulltext.md` 是否存在
2. 若存在，则在同一篇 paper 的 OCR 目录下创建 backup：
   - `backups/fulltext.pre-rebuild.<timestamp>.md`
3. 写入 `last_backup_at` 与 `last_backup_path`
4. 然后才开始新的 rebuild

该规则适用于：

- 新用户
- legacy 用户

区别只在于：legacy 用户没有额外迁移提示；但 rebuild safety net 仍然生效。

## 4. rebuild 完成后的写回

当 rebuild 成功完成后，系统执行：

1. 覆盖写入新的 `fulltext.md`
2. 计算新文件的 SHA-256
3. 更新 `meta.json`：
   - `rebuild_count += 1`
   - `rebuild_finished_at = now`
   - `machine_fulltext_hash = sha256(new fulltext.md)`

首次 OCR 成功写入 `fulltext.md` 时，也应写入首个 `machine_fulltext_hash`。

## 5. drift 判断规则

系统若需要判断当前 `fulltext.md` 是否被后续修改，只做一件事：

- 计算当前 `fulltext.md` 的 SHA-256
- 与 `meta.json.machine_fulltext_hash` 比较

不引入“疑似安全”的弱文案到 rebuild 主流程中。

### 说明

- 这不是内容审计系统
- 也不回答“谁改的、改了什么”
- 它只回答：**当前文件是否仍等于最近一次机器写入版本**

## 6. backup retention policy

backup 保留策略采用**按篇按数量保留**：

- 每篇 paper 最多保留最近 **5** 份 backup
- 当新 backup 写入后若总数超过 5，则删除最老的，直到剩 5

明确不采用：

- 30 天自动过期
- 90 天自动过期
- 全局集中清理

原因：

- 数量策略更可预测
- 用户更容易理解
- `fulltext.md` 是文本文件，体积通常较小
- “最近 5 次 rebuild 前状态”足以覆盖常见试错场景

## 用户分层策略

## 新用户

新用户从第一篇 OCR / 第一篇 rebuild 开始就带有 machine provenance：

- `machine_fulltext_hash`
- `rebuild_count`
- `rebuild_finished_at`
- backup 机制

因此，新用户支持完整的 drift 判断与 rebuild 保护。

## legacy 用户

legacy 用户不做专门迁移 UX：

- 不提示“哪些文章可能有批注”
- 不提示“建议升级到新模型”
- 不补建历史 baseline

但如果 legacy 用户手动触发 rebuild：

- 仍然先 backup
- 然后按新规则写入新的 provenance

也就是说，legacy 用户**从第一次手动 rebuild 开始**进入新模型。

## 与向量库的关系

本设计不把 vector rebuild 绑定为 OCR rebuild 的强制动作。

结论：

- OCR rebuild 负责 `fulltext.md` 与 `meta.json` provenance
- vector 是否重建，是后续独立决策
- 第一版不在本设计内耦合这两个动作

## 错误处理

### 1. backup 失败

如果 `fulltext.md` 存在且 backup 创建失败：

- rebuild 应中止
- 不允许直接进入覆盖写入

原因：本设计的第一安全前提就是“先留退路，再做破坏性动作”。

### 2. hash 计算失败

如果新 `fulltext.md` 已写入但 hash 计算失败：

- rebuild 结果视为部分失败
- `machine_fulltext_hash` 不应写入伪值
- 错误状态需要在 `meta.json` 或运行日志中可见

### 3. `meta.json` 缺字段

缺字段不应阻止旧论文被读取；但第一次 rebuild 成功后，系统应把相关字段补齐。

## UI / 文案约束

第一版只需要最小文案，不做复杂迁移引导。

建议文案：

- rebuild 前：
  - `A backup of fulltext.md will be created before rebuild.`
- 若检测到当前 hash 与 machine hash 不一致：
  - `fulltext.md has changed since the last machine write. A backup will be kept before rebuild.`
- backup retention：
  - `PaperForge keeps the latest 5 rebuild backups for this paper.`

避免使用：

- `safe to rebuild`
- `untouched`
- `guaranteed no edits`

因为系统没有做语义级内容理解，只做状态级保护。

## 验收标准

本设计落地后，应满足：

1. 新用户首次 OCR 成功后，`meta.json` 写入 `machine_fulltext_hash`
2. 每次 rebuild 前，若 `fulltext.md` 存在，则先生成 backup
3. rebuild 成功后，`rebuild_count`、`rebuild_finished_at`、`machine_fulltext_hash` 更新
4. 同一篇 paper 的 backup 数量超过 5 时，自动删除最老的
5. legacy 用户不出现迁移提示，但手动 rebuild 仍可获得 backup 保护
6. drift 判断只依赖当前文件 hash 与 `machine_fulltext_hash` 对比

## 后续非阻塞扩展

以下内容可后续再做，不是第一版必须项：

- 把 backup 元数据做成独立小索引
- 为 backup 提供“restore latest backup”入口
- 为 hash drift 提供人类可读 diff 预览
- 将 backup retention 变成可配置项
