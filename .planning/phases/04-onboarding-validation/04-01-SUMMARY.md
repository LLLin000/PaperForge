# 04-01 Summary: deep-reading 三态输出 + --verbose

## 做了什么

### Task 1: 添加 --verbose flag 到 cli.py

- 修改 `paperforge/cli.py`：为 `deep-reading` 子命令添加了 `--verbose/-v` flag
- 将 `run_deep_reading` 从 dispatch_map 移出，改为单独的 if 分支以传递 verbose 参数
- 更新测试 stub `stub_run_deep_reading` 接受 `verbose: bool = False` 参数

### Task 2: 增强 run_deep_reading 实现三态输出

- `pipeline/worker/scripts/literature_pipeline.py`：
  - 函数签名改为 `run_deep_reading(vault: Path, verbose: bool = False) -> int`
  - 新增 `do_ocr` 检测：从 library-record 中解析 `do_ocr: true/false`
  - 三态输出：
    - **就绪**：ocr_status = done
    - **等待 OCR**：do_ocr = true 且 ocr_status in (pending, processing)
    - **阻塞**：analyze = true 但不在就绪和等待状态
  - `--verbose` 模式：为每个阻塞条目输出修复步骤
    - pending → `paperforge ocr run`
    - processing → "等待完成"
    - failed → 检查 meta.json 后重试

### Task 3: 验证测试

- 7/7 CLI dispatch tests PASSED

## 验证

```
paperforge deep-reading --help  # 显示 --verbose 选项
paperforge deep-reading         # 三态输出（就绪/等待 OCR/阻塞）
paperforge deep-reading --verbose  # 含修复指令
```

## 修改的文件

- `paperforge/cli.py` — 添加 --verbose flag，修改 dispatch
- `pipeline/worker/scripts/literature_pipeline.py` — run_deep_reading 三态 + verbose
- `tests/test_cli_worker_dispatch.py` — stub_run_deep_reading 更新
