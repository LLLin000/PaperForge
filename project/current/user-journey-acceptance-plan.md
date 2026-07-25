# User Journey Acceptance Tests

## 问题

Issue 粒度的 acceptance 测试"OCR 命令接受 key 参数"，但用户看到的是"我在 OCR Workspace 选了两篇论文点 Process，等了 10 分钟回来还是 Pending"。

**每个用户旅程 = 一串前后端步骤，任何一步断裂用户就看到了 bug。**

## 用户旅程清单

| # | 旅程 | 步骤数 | 今天发现 bug 在哪步 |
|---|---|---|---|
| J1 | 安装 → 可用 | 6 | pip 检测（步骤 4） |
| J2 | OCR Workspace：选论文 → Process → 看结果 | 5 | argparse 拒绝 key（步骤 2） |
| J3 | OCR Settings：看状态 → Update Available → Re-extract → 进度 → Ready | 6 | 版本号不写入（步骤 1→永远显示 stale） |
| J4 | OCR 单篇 redo：备份 → 删旧 → 跑 OCR → 写新 | 5 | 是否备份未知（待验证） |
| J5 | Smart Retrieval：启用 → Build → 进度 → Ready | 5 | 进度条不更新（run_ocr 不发射 token） |
| J6 | 语言切换：全部 9 个页面 en ↔ zh | 18 | 可能有遗漏 |
| J7 | Control Center 导航：Overview → 模块 → 回 Overview | 15 | 导航闭环未知 |

## 测试格式

每个旅程一个 `acceptance/journey-N.sh`：

```bash
#!/usr/bin/env bash
# J2: OCR Workspace — select paper → Process → see result
source "$(dirname "$0")/_lib.sh"

echo "=== J2: OCR Workspace closed loop ==="

# 1. 模拟：用户在 Workspace 选 2BB8VM5W 点 Process
echo "Step 1: Process paper via CLI"
assert "ocr run accepts key" \
    'run_paperforge ocr run 2BB8VM5W 2>&1 | grep -q "Processing specific keys"'

# 2. 验证：meta.json 写入完成状态和版本
echo "Step 2: meta.json has pipeline version"
assert "ocr_pipeline_version is 2.0.0" \
    'python -c "
import json; meta=json.load(open(\"$VAULT/System/PaperForge/ocr/2BB8VM5W/meta.json\"))
assert meta.get(\"ocr_pipeline_version\")==\"2.0.0\" and meta.get(\"ocr_status\")in(\"done\",\"done_degraded\")
"'

# 3. 验证：probe 返回 stale=0（前端不显示 Update Available）
echo "Step 3: probe shows papers on current"
assert "stale count is 0" \
    'python -c "
from paperforge.commands.probe import probe_ocr; from pathlib import Path
r=probe_ocr(Path(\"$VAULT\"))
assert r[\"pipeline_version_summary\"][\"stale\"]==0
"'

# 4. 验证：OCR Workspace 重读 data 后 paper 状态变为 done
echo "Step 4: workspace would see done status"
assert "paper status is done" \
    'python -c "
import json; meta=json.load(open(\"$VAULT/System/PaperForge/ocr/2BB8VM5W/meta.json\"))
assert meta[\"ocr_status\"]==\"done\", f\"status={meta.get(\"ocr_status\")}\"
"'

summary
```

## 实现顺序

### Phase 1：写今天发现 bug 的三个旅程（J2, J3, J5）

这三个是"代码声称 done 但用户实际用会炸"的。

### Phase 2：补 J1, J4, J6, J7

### Phase 3：CI + pre-commit

`acceptance/run-all.sh` 串行跑，任一失败 exit 1。

## 与 issue acceptance 的关系

Issue acceptance = 单点验证（"parser 有 keys 参数"）
Journey acceptance = 闭环验证（"用户点 Process → paper 状态变 done → 前端不显示 stale"）

两个都要。Issue 粒度的是 CI barrier，Journey 粒度的是 pre-release gate。

## 不过度设计

- **7 个 journey，不超过 70 个 assertion**
- **一个 helper 文件 `_lib.sh`（< 30 行）**
- **不用 Docker，不用 mock，直接打 test vault 和真实 CLI**
