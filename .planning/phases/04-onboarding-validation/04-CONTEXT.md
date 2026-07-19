# Phase 4 Context: End-To-End Onboarding And Validation

## Discuss Mode: All 4 areas discussed in Chinese.

---

## Area 1: Onboarding Validation — 验证报告和分步骤引导

**结论：**

- `paperforge doctor` 是独立子命令，纳入 `paperforge` 命令体系
- 验证报告按类别分组输出（Python 环境 / Vault 结构 / Zotero 链接 / BBT 导出 / OCR 配置 / Worker 脚本 / Agent 脚本）
- Next-step 动态生成：从 ocr meta.json 的 error 字段读取 fix suggestion，而不是写死
- `/LD-deep` prepare 失败诊断不单独做子命令，由 literature-qa skill 自己的 Agent 自己分析问题出在哪（user: "agent 应该可以自己分析问题出在哪"）

**待实现：**
- `paperforge doctor` 输出分组
- Next-step 动态生成逻辑（需要 OCR meta.json error 字段支持 fix suggestion）

---

## Area 2: Better BibTeX Export Validation

**结论：**

- BBT export validation 放在 `paperforge doctor` 里
- 检查内容（全部实现）：
  1. 导出路径是否存在
  2. JSON 文件能否被 Python json 库正常解析
  3. JSON 是否包含有效的 citation key（zotero_key 字段）
  4. 导出条目数量是否异常少（量级差异检测）
- README 单独介绍 BBT 配置（用户的手动操作）

**待实现：**
- `paperforge doctor` 中的 BBT 导出检查函数
- docs/README.md 中的 BBT 配置说明

---

## Area 3: Deep Reading Queue

**结论：**

- OCR 状态流转：`pending → queued → done`
- `paperforge deep-reading` 默认输出扁平列表，包含：
  - 就绪：`ocr_status = done`
  - 阻塞：`analyze = true` 但 `ocr_status != done`
  - 等待 OCR：`do_ocr = true` 且 `ocr_status = pending/processing`
- `paperforge deep-reading --verbose` 包含修复指令（与 ONBD-03 一致）
- `/LD-deep` prepare 失败诊断不单独做子命令，Skill Agent 自己分析

**待实现：**
- `paperforge deep-reading` 三态输出（就绪/阻塞/等待 OCR）
- `--verbose` 模式修复指令输出

---

## Area 4: Doc-Command Alignment

**发现的关键不一致：**

AGENTS.md 记录的是 legacy Python path 调用，不是 `paperforge` CLI 命令。

| 命令 | AGENTS.md (legacy) | cli.py (actual) |
|------|-------------------|-----------------|
| selection-sync | `python <system_dir>/.../literature_pipeline.py --vault ... selection-sync` | `paperforge selection-sync` |
| index-refresh | `python ... literature_pipeline.py ... index-refresh` | `paperforge index-refresh` |
| ocr | `python ... literature_pipeline.py ... ocr` | `paperforge ocr run` |
| deep-reading | `python ... literature_pipeline.py ... deep-reading` | `paperforge deep-reading` |
| status | `python ... literature_pipeline.py ... status` | `paperforge status` |

**结论：**

- 更新 AGENTS.md 所有命令示例为 `paperforge <command>` 形式
- 保留 Python path 作为备用/legacy 选项说明
- AGENTS.md 是 Agent 的工作手册（不是给用户看的）
- ld-deep.md 是 literature-qa skill 的一部分，Doc-Command Alignment 不涉及 ld-deep.md

**待实现：**
- 更新 AGENTS.md 的所有 bash 示例命令

---

## Phase 4 待办清单

### 必须实现
1. `paperforge doctor` — 分组验证报告（Python / Vault / Zotero / BBT / OCR / Worker / Agent）
2. `paperforge doctor` 中 BBT 导出检查（路径 / JSON 解析 / citation key / 条目数量）
3. `paperforge deep-reading` 三态输出（就绪/阻塞/等待 OCR）
4. `paperforge deep-reading --verbose` 修复指令
5. Next-step 动态生成逻辑（从 OCR meta.json error 字段读取 fix suggestion）
6. docs/README.md — BBT 配置说明（用户手动操作指南）
7. 更新 AGENTS.md 所有命令为 `paperforge` CLI 形式

### Skill 自己解决（不单独做子命令）
- `/LD-deep` prepare 失败诊断 → literature-qa skill Agent 自己分析

---

## 关键约束

- 所有 `paperforge` 子命令统一通过 `paperforge/cli.py` 的 ArgumentParser 分发
- `paperforge doctor` 是 `paperforge` 下的独立子命令（不是 `ocr doctor` 的扩展）
- OCR meta.json error 字段需要支持 `fix_suggestion` 字段（Phase 2 可能已部分实现，需验证）
- AGENTS.md 更新后，Python path 形式作为 "legacy / 备用" 说明保留
