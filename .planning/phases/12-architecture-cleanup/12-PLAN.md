# Phase 12: Architecture Cleanup - Execution Plan

**Plan Date:** 2026-04-24
**Base Commit:** 4297dcd
**Phase Goal:** 修复模块边界泄漏，消除测试死区

---

## Task Overview

| Task | Description | Est. Effort | Files |
|------|-------------|-------------|-------|
| 1 | Create `paperforge/worker/` package structure | Low | 6 files |
| 2 | Migrate sync functions from literature_pipeline.py | Medium | 1 source + import updates |
| 3 | Migrate OCR functions | Medium | 1 source + import updates |
| 4 | Migrate repair functions | Medium | 1 source + import updates |
| 5 | Migrate status/doctor functions | Low | 1 source + import updates |
| 6 | Migrate deep-reading functions | Low | 1 source + import updates |
| 7 | Extract base_views module | Medium | 1 source + test updates |
| 8 | Migrate skills/ to paperforge/skills/ | Low | Directory move + import updates |
| 9 | Update all import paths | Medium | 10+ files |
| 10 | Verify tests and consistency audit | Low | Test run + audit |
| 11 | Update documentation | Low | AGENTS.md, ARCHITECTURE.md |

---

## Task Dependencies

```
Task 1 (Create package)
    ├── Task 2 (Sync) ──╮
    ├── Task 3 (OCR) ───┤
    ├── Task 4 (Repair) ┤
    ├── Task 5 (Status) ┼── Task 9 (Update imports)
    ├── Task 6 (Deep) ──┤
    ├── Task 7 (Base) ──┤
    └── Task 8 (Skills) ─╯
                           │
                           ▼
                    Task 10 (Verify)
                           │
                           ▼
                    Task 11 (Docs)
```

---

## Wave Strategy

### Wave 1: Package Structure + Sync/OCR (Tasks 1-3)
- 创建 `paperforge/worker/__init__.py`
- 从 literature_pipeline.py 提取 sync 相关函数到 `paperforge/worker/sync.py`
- 从 literature_pipeline.py 提取 OCR 相关函数到 `paperforge/worker/ocr.py`
- 更新 `paperforge/commands/sync.py` 和 `paperforge/commands/ocr.py` 的导入
- **验证：** sync 和 ocr 的测试通过

### Wave 2: Repair/Status/Deep (Tasks 4-6)
- 提取 repair 函数到 `paperforge/worker/repair.py`
- 提取 status/doctor 函数到 `paperforge/worker/status.py`
- 提取 deep-reading 函数到 `paperforge/worker/deep_reading.py`
- 更新对应 commands/ 导入
- **验证：** repair, status, deep-reading 测试通过

### Wave 3: Base Views + Skills (Tasks 7-8)
- 提取 base_views 函数到 `paperforge/worker/base_views.py`
- 迁移 `skills/literature-qa/` → `paperforge/skills/literature-qa/`
- 更新 `paperforge/config.py` 中的 skill 查找逻辑
- 修复 `test_base_preservation.py` 和 `test_base_views.py` 的导入
- **验证：** base views 测试通过，skill 可导入

### Wave 4: Import Cleanup + Verification (Tasks 9-10)
- 扫描并修复所有剩余的旧导入路径
- 删除 `pipeline/` 目录（确认无引用后）
- 运行完整测试套件
- 运行一致性审计
- **验证：** 所有测试通过，审计通过

### Wave 5: Documentation (Task 11)
- 更新 `AGENTS.md` 中的路径引用
- 更新 `ARCHITECTURE.md` 的目录结构图
- 更新 `docs/MIGRATION-v1.2.md`（如有必要）
- 创建 12-SUMMARY.md
- 更新 STATE.md 和 ROADMAP.md

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| 遗漏导入路径 | 使用 grep 搜索所有 `pipeline.worker.scripts` 和 `skills.literature_qa` 引用 |
| 循环导入 | 保持 __init__.py 轻量，避免在包初始化时导入所有子模块 |
| 功能回归 | 每波完成后运行相关测试，不累积到最后一并验证 |
| Git 历史丢失 | 使用 `git mv` 保留文件历史 |

---

## Acceptance Criteria

- [ ] `pipeline/` 目录完全移除（或仅剩空壳待后续删除）
- [ ] `skills/` 目录完全移除（或仅剩空壳待后续删除）
- [ ] `paperforge/worker/` 包含所有原 pipeline 功能
- [ ] `paperforge/skills/` 包含所有原 skills 功能
- [ ] 所有测试通过（≥203 passed）
- [ ] 一致性审计通过（4/4）
- [ ] 无 `pipeline.worker.scripts` 导入残留
- [ ] 无 `skills.literature_qa` 导入残留
- [ ] 文档已更新

---

## Rollback Plan

若 Wave 1-2 出现严重问题：
```bash
git reset --hard 4297dcd  # 回到 Phase 12 开始前的状态
```

所有变更应在单个 feature branch 上进行，便于整体回滚。
