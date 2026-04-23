# /lp-status

查看 PaperForge Lite 当前安装与运行状态。

## Command

```bash
paperforge status
```

## 说明

`paperforge` 是 PaperForge Lite 的统一入口点，会自动读取 `paperforge.json` 解析路径。
如需使用 Python 直接调用（备选方式）：

```bash
python $(paperforge paths --json | python -c "import json,sys; print(json.load(sys.stdin)['worker_script'])") --vault . status
```

更简单的方式是直接使用 `paperforge status`（见上方）。
