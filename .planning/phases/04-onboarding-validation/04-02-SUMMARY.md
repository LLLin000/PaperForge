# 04-02 Summary: paperforge doctor 子命令

## 做了什么

### Task 1: 添加 doctor 子命令到 CLI parser

- `paperforge_lite/cli.py`：
  - `build_parser()` 中添加 `sub.add_parser("doctor", ...)`
  - `main()` 中添加 `if args.command == "doctor": from pipeline.worker.scripts.literature_pipeline import run_doctor; return run_doctor(vault)`

### Task 2: 实现 run_doctor 函数

- `pipeline/worker/scripts/literature_pipeline.py` 新增 `run_doctor(vault: Path) -> int`
- 检查 7 个类别，每类返回 (status, message, fix)：
  1. **Python 环境** — Python 版本 >= 3.10，required_modules 可导入
  2. **Vault 结构** — paperforge.json / system_dir / resources_dir / control_dir 存在
  3. **Zotero 链接** — system_dir/Zotero 目录存在且为 junction/symlink（warn 如果是普通目录）
  4. **BBT 导出** — exports/library.json 存在、可解析 JSON、包含 citation key 条目
  5. **OCR 配置** — PADDLEOCR_API_KEY 或 OCR_TOKEN 环境变量已设置
  6. **Worker 脚本** — literature_pipeline.py 存在且所有 worker 函数可导入
  7. **Agent 脚本** — literature-qa skill 目录存在
- 输出格式：`[PASS]/[FAIL]/[WARN] 类别 — 消息`，失败时输出"修复步骤"
- 新增辅助函数 `_is_junction(path: Path) -> bool` 用于检测 Windows junction

### Task 3: 添加测试

- 新建 `tests/test_doctor.py`（4 个测试）：
  - `test_doctor_command_exists` — CLI dispatch 正确
  - `test_doctor_python_check` — 函数签名正确
  - `test_doctor_returns_int` — 返回类型正确
  - `test_doctor_on_empty_vault` — 空 vault 输出正确格式，code=1

## 验证

```
paperforge doctor  # 输出 7 类检查结果，[PASS]/[FAIL]/[WARN] + 修复步骤
```

## 修改的文件

- `paperforge_lite/cli.py` — 添加 doctor 子命令
- `pipeline/worker/scripts/literature_pipeline.py` — run_doctor 实现
- `tests/test_doctor.py` — 新建测试文件（4 tests）
