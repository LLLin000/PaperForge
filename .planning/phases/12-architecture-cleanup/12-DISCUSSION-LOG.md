# Phase 12: Architecture Cleanup - Discussion Log

**Phase:** 12  
**Topic:** 修复模块边界泄漏，消除测试死区  
**Base Commit:** 4297dcd  

---

## Decision D-01: Pipeline 迁移策略

**Question:** 如何将 `pipeline/worker/scripts/literature_pipeline.py`（2900+ 行）整合到 `paperforge/` 包中？

**Options Considered:**
- A. 完全重构到 `paperforge/worker/` — 拆分为 sync.py, ocr.py, repair.py, status.py, base_views.py 等模块
- B. 直接移动为 `paperforge/worker/literature_pipeline.py`（保持单文件）
- C. 保持 `pipeline/` 原位置，仅添加到 setup.py

**Decision: A** — 完全重构，与 `paperforge/commands/` 结构对齐。理由：
- Phase 9 已证明模块化有效（commands/ 包）
- literature_pipeline.py 2900+ 行，功能混杂（sync + ocr + deep-reading + repair + status + base_views）
- 模块化后可独立测试每个子系统
- 消除 `pipeline/` 到 `paperforge/` 的跨目录导入

**Impact:** 需要更新所有导入路径（commands/, tests/, scripts/）

---

## Decision D-02: Skills 迁移策略

**Question:** `skills/literature-qa/scripts/ld_deep.py` 如何整合到 paperforge 包？

**Options Considered:**
- A. 移动 `skills/literature-qa/` → `paperforge/skills/literature-qa/`（保留子目录结构）
- B. 扁平化 → `paperforge/skills/ld_deep.py`
- C. 保持外部，创建包装器

**Decision: A** — 保留子目录结构。理由：
- literature-qa/ 包含 prompt_deep_subagent.md, chart-reading/ 等配套资源
- 子目录结构清晰，未来可扩展其他 skills
- 与 paperforge.commands 的子目录模式一致

**Impact:** 需要更新 `paperforge.config.find_skill_script()` 和 tests/

---

## Decision D-03: Test Dead Zones 修复策略

**Question:** `test_base_preservation.py`（257行，9个测试类）和 `test_base_views.py`（101行，6个测试类）从旧的 `pipeline` 模块导入函数，如何修复？

**Options Considered:**
- A. 迁移函数到 `paperforge/worker/base_views.py`，修复测试导入
- B. 保留在迁移后的 `paperforge/worker/literature_pipeline.py` 中
- C. 如果这些函数不再使用，删除测试文件

**Decision: A** — 迁移函数并修复测试导入。理由：
- 用户明确指示"全都按照这个标准来"（完全模块化）
- 这些函数（build_base_views, merge_base_views, ensure_base_views）是 runtime 功能
- 独立的 base_views.py 模块更易于维护

**Impact:** 需要从 literature_pipeline.py 中提取 base_views 相关函数

---

## Decision D-04: Test 失败状态

**Question:** `test_pdf_resolver.py` 的 2 个失败如何修复？

**发现：** Phase 11 执行期间已自动修复：
- `test_absolute_path_normalized_with_prefix` — Phase 11 的 `_normalize_attachment_path()` 已处理 absolute: 前缀
- 测试运行时：203 passed, 2 skipped, 0 failed

**Decision:** 无需额外修复。Phase 11 已解决。

---

## Decision D-05: Phase 12 范围确认

**包含：**
1. Pipeline 模块拆分和迁移（pipeline/ → paperforge/worker/）
2. Skills 目录迁移（skills/ → paperforge/skills/）
3. Base views 提取和测试修复
4. 所有导入路径更新
5. 文档更新（AGENTS.md, ARCHITECTURE.md 等）

**不包含（已排定到其他阶段或低优先级）：**
- Repair scan 性能优化 → 保留为 future work
- 一致性审计 CI 集成 → 低优先级，延后
- paperforge doctor 增强 → 已在 Phase 11 完成

---

## Deferred Ideas

1. **Repair scan O(n*m) 优化** — 需要重构 repair 算法，超出当前范围
2. **一致性审计 CI 集成** — 低优先级，等有 CI 环境时再实施
3. **Skill 热加载机制** — 未来 Agent 平台扩展时考虑
