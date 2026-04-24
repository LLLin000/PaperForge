# /pf-status

查看 PaperForge 当前安装与运行状态。

## Command

```bash
paperforge status
```

## 说明

`paperforge` 是 PaperForge 的统一入口点，会自动读取 `paperforge.json` 解析路径。

如需使用 Python 直接调用（备选方式）：

```bash
python -m paperforge status --vault .
```

更简单的方式是直接使用 `paperforge status`（见上方）。
