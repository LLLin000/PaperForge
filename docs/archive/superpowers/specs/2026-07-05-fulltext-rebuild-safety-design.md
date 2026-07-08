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

已经升级过的 vault 可能存在 machine side 的第二份 fulltext 副本，但把“双文件对比”作为长期机制会带来额外存储、路径复杂度和心智负担。设计应回到**单工作文件 + provenance**。

第一版同时承认一个现实：当前 pipeline 仍可能继续生成 `render/fulltext.md`。因此本设计必须明确区分：

- `paper_root/fulltext.md`：用户工作文本，也是 drift / backup / provenance 关注对象
- `render/fulltext.md`：允许继续存在的 derived render artifact，不参与 drift 判断，不作为 machine baseline

### 3. mtime 只适合做启发式，不适合做真相源

真实样本表明：`fulltext.md` 的修改时间可能晚于 OCR / rebuild 完成时间，但文本内容仍然完全一致。因此，mtime 不能单独作为“用户改过内容”的主判据。

## 核心原则

1. **Single user-facing fulltext**：长期只把 `paper_root/fulltext.md` 作为工作文本与保护对象。
2. **Derived artifacts may remain**：`render/fulltext.md` 若仍由现有 pipeline 产出，只视为 derived render artifact，不进入 provenance 模型。
3. **Meta owns provenance**：机器写入状态由 `meta.json` 记录，不依赖第二份常驻 baseline 文件。
4. **Hash over time**：内容哈希比 mtime 更可靠；mtime 只作为 legacy fallback 辅助手段。
5. **Backup before destruction**：backup 发生在即将覆盖 `paper_root/fulltext.md` 的同一临界区内。
6. **New-user first**：新用户有完整保护模型；legacy 用户不做升级 UX。
7. **Count-based retention**：backup 按数量保留，不按时间过期。

## 设计决策

## 1. 数据模型

machine provenance 放在每篇论文的 `meta.json`。

新增/规范字段：

- `ocr_finished_at`: 首次 OCR 成功完成时间
- `rebuild_count`: rebuild 次数，未 rebuild 时为 `0`
- `rebuild_finished_at`: 最近一次 rebuild 完成时间；未 rebuild 时为 `null` 或缺省
- `machine_fulltext_hash`: 最近一次**机器成功写入到 `paper_root/fulltext.md` 后**的 SHA-256
- `last_backup_at`: 最近一次 destructive write 前 backup 的时间
- `last_backup_path`: 最近一次 backup 的相对路径

派生语义：

- `effective_machine_time = rebuild_finished_at or ocr_finished_at`

注意：

- 不使用 `0` 作为时间 sentinel
- `rebuild_count` 表达是否 rebuild 过；时间字段始终保持“时间或空”
- `machine_fulltext_hash` 使用 `sha256:<hex>` 形式

## 2. 基线模型

系统**不长期保存第二份 machine fulltext 作为 baseline**。

唯一进入用户保护模型的文本是：

- `paper_root/fulltext.md`

若当前 pipeline 继续生成：

- `render/fulltext.md`

则它只被视为 derived render artifact：

- 不参与 drift 判断
- 不参与 backup 决策
- 不写入 `machine_fulltext_hash`
- 不作为长期 machine baseline

最近一次机器写入状态完全通过 `machine_fulltext_hash` 表达：

- 当前 `paper_root/fulltext.md` 的 SHA-256 与 `machine_fulltext_hash` 相同
  - 表示自最近一次机器写入后未改动
- 不同
  - 表示 `paper_root/fulltext.md` 已偏离最近一次机器写入状态

这解决的是“当前工作文本是否偏离机器状态”，而不是保存所有历史版本内容。

## 3. destructive write 前的保护动作

系统**不在 rebuild 任务刚开始时备份**，而是在即将覆盖 `paper_root/fulltext.md` 前备份当前磁盘文件。

流程：

1. 先完成 derived rebuild 计算，生成新的 markdown 到内存或临时文件
2. 在覆盖 `paper_root/fulltext.md` 前，检查当前 `paper_root/fulltext.md` 是否存在
3. 若存在，则创建 backup：
   - `backups/fulltext.pre-rebuild.<UTC timestamp>[.<seq>].md`
4. backup 创建成功并可读后，才允许执行 atomic replace
5. 若 backup 失败，则中止 `paper_root/fulltext.md` 覆盖
6. backup retention 在新 backup 创建成功后执行；retention cleanup 失败只记录 warning，不撤销 backup

该规则适用于：

- 新用户
- legacy 用户

区别只在于：legacy 用户没有额外迁移提示；但 destructive write safety net 仍然生效。

## 4. atomic 写入协议

当 rebuild 成功生成新的 markdown 后，覆盖 `paper_root/fulltext.md` 必须遵守最小 atomic protocol：

1. 新 markdown 先写入 `fulltext.md.tmp`
2. 对 `fulltext.md.tmp` 计算 SHA-256
3. 若当前 `paper_root/fulltext.md` 存在，则在临界区内创建 backup
4. `fulltext.md.tmp -> fulltext.md` 原子替换
5. 更新 `meta.json.tmp -> meta.json`
6. 若 meta 更新失败：
   - 不写伪 `machine_fulltext_hash`
   - 保留错误状态
   - 下次 drift 状态不得显示为“safe / untouched”

首次 OCR 成功写入 `paper_root/fulltext.md` 时，也应在同一末尾写回点写入首个 `machine_fulltext_hash`。

## 5. drift 判断规则

系统若需要判断当前 `paper_root/fulltext.md` 是否被后续修改，只做一件事：

- 计算当前磁盘 `paper_root/fulltext.md` 的 SHA-256
- 与 `meta.json.machine_fulltext_hash` 比较

### hash 规则

- `machine_fulltext_hash` 使用 `sha256:` 前缀
- 计算对象为 `paper_root/fulltext.md` 当前磁盘 UTF-8 bytes
- 不做换行、空格、BOM 或 Markdown 语义归一化
- CRLF / LF 差异视为 drift

### drift 状态三态

- `MATCHED`
  - 当前 hash == `machine_fulltext_hash`
- `DRIFTED`
  - 当前 hash != `machine_fulltext_hash`
- `UNKNOWN`
  - `machine_fulltext_hash` 缺失
  - `paper_root/fulltext.md` 不存在
  - hash 计算失败
  - fulltext 覆盖成功但 meta 更新失败

legacy 用户首次手动 rebuild 前默认属于 `UNKNOWN`。

## 6. backup retention policy

backup 保留策略采用**按篇按数量保留**：

- 每篇 paper 最多保留最近 **5** 份 backup
- 当新 backup 写入后若总数超过 5，则删除最老的，直到剩 5

实现细节写死：

- timestamp 使用 UTC，格式：`YYYYMMDDTHHMMSSZ`
- 同秒多次 backup 用顺序后缀：`.001`、`.002` …
- retention 只匹配：`backups/fulltext.pre-rebuild.*.md`
- “最老”按文件名 timestamp / seq 排序，不按 mtime 排序
- retention cleanup 失败只记 warning，不回滚 rebuild

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

如果当前 `paper_root/fulltext.md` 存在且 backup 创建失败：

- destructive write 应中止
- 不允许进入 `fulltext.md.tmp -> fulltext.md` 替换

原因：本设计的第一安全前提就是“先留退路，再做破坏性动作”。

### 2. hash 计算失败

如果新 markdown 已生成但 `fulltext.md.tmp` 的 hash 计算失败：

- destructive write 不应继续
- `machine_fulltext_hash` 不应写入伪值
- 错误状态需要在 `meta.json` 或运行日志中可见

### 3. fulltext 覆盖成功但 meta 更新失败

如果 `paper_root/fulltext.md` 已原子替换成功，但 `meta.json` 更新失败：

- 不补写伪 `machine_fulltext_hash`
- 下次 drift 状态必须是 `UNKNOWN` 或 `DRIFTED`
- 不得显示为 `MATCHED`、`safe` 或 `untouched`

### 4. `meta.json` 缺字段

缺字段不应阻止旧论文被读取；但第一次 rebuild 成功后，系统应把相关字段补齐。

## UI / 文案约束

第一版只需要最小文案，不做复杂迁移引导。

建议文案：

- rebuild 前：
  - `A backup of fulltext.md will be created before replace.`
- 若 drift 状态为 `DRIFTED`：
  - `fulltext.md has changed since the last machine write. A backup will be kept before rebuild.`
- 若 drift 状态为 `UNKNOWN`：
  - `No machine baseline is available. A backup will be kept before rebuild.`
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
2. `render/fulltext.md` 若存在，不参与 drift 判断
3. backup 发生在覆盖 `paper_root/fulltext.md` 的同一临界区内，而不是 rebuild 任务开始时
4. 每次 rebuild 成功后，`rebuild_count`、`rebuild_finished_at`、`machine_fulltext_hash` 更新
5. rebuild 中途失败且未进入 fulltext 覆盖阶段时，不应产生误导性 `machine_fulltext_hash`
6. fulltext 覆盖成功但 meta 更新失败时，系统下次 drift 状态为 `UNKNOWN` 或 `DRIFTED`
7. backup 文件同秒创建不覆盖旧 backup
8. retention 只删除 `backups/fulltext.pre-rebuild.*.md`，不删除其他用户文件
9. 同一篇 paper 的 backup 数量超过 5 时，自动删除最老的匹配 backup
10. legacy 用户缺 `machine_fulltext_hash` 时，drift 状态为 `UNKNOWN`
11. hash 使用磁盘 bytes 计算，CRLF / LF 差异会被视为 drift
12. legacy 用户不出现迁移提示，但手动 rebuild 仍可获得 backup 保护

## 后续非阻塞扩展

以下内容可后续再做，不是第一版必须项：

- 把 backup 元数据做成独立小索引
- 为 backup 提供“restore latest backup”入口
- 为 hash drift 提供人类可读 diff 预览
- 将 backup retention 变成可配置项
