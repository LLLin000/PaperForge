# 04-03 Summary: AGENTS.md 命令更新为 paperforge CLI

## 做了什么

### Task 1: 更新 Section 4 Core Workers

- selection-sync / index-refresh / ocr / deep-reading 的示例命令从 legacy `python ...` 改为 `paperforge <command>`
- 添加 `# Legacy (备用):` 注释行保留原 Python path

### Task 2: 更新 Section 7 第一次使用指南

- Step 2 (selection-sync) / Step 3 (index-refresh) / Step 5 (ocr run) / Step 6 (deep-reading) 的 bash 示例全部更新
- 移除 `--vault` 参数（CLI 自动从 cwd/env 读取）

### Task 3: 更新 Section 8 常用命令速查

- 所有命令更新为 `paperforge` CLI 形式
- 新增 `paperforge doctor` 到速查表
- 新增 `paperforge deep-reading --verbose` 到速查表

## 一致性验证

```
OK: All paperforge commands are valid
OK: No uncommented legacy paths
paperforge commands found: {'deep-reading', 'ocr', 'status', 'selection-sync', 'index-refresh', 'doctor'}
```

## 修改的文件

- `AGENTS.md` — Section 4/7/8 所有命令示例更新
