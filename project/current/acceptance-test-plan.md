# Acceptance Test Plan

## 问题

单元测试覆盖模块内部逻辑，但漏掉端到端集成路径。今天发现的三个 bug 都是"每个组件在单元测试里对了，但串起来就断"：

- `ocr run KEY` — argparse 拒绝，因为 parser 没定义 keys 参数
- `meta.json` 缺 `ocr_pipeline_version` — 三个写入路径都没写这个字段
- `pip not found` — `shutil.which("pip")` 在 Electron PATH 里找不到

## 方案

每个 issue 配一个 `acceptance/<issue-id>-<slug>.sh`，模拟"用户在 Obsidian 里操作"的完整路径。`_lib.sh` 提供共享 helper。

## 目录结构

```
acceptance/
├── README.md
├── _lib.sh                    # 共享 helper
├── issue-95-ocr-workspace.sh  # OCR Workspace 闭环
├── issue-96-ocr-3state.sh     # OCR 3 状态 UX
├── issue-97-pipeline-version.sh
├── issue-98-i18n.sh
├── issue-99-redo-backup.sh    # Redo 备份安全
├── issue-100-kami-css.sh      # CSS 回归（视觉 diff）
├── issue-101-progress-bar.sh  # 进度条 token 发射
├── issue-102-embed-backup.sh
├── issue-103-sr-vec0.sh
├── issue-104-sr-ux.sh
└── issue-94-wayfinder.sh      # 聚合（跑所有子 issue）
```

## 优先级

### P0 — 今天修过的 + 还 open 的 bug（立即写）

| Issue | 测试什么 | 防什么回归 |
|---|---|---|
| #95 | `ocr run KEY` 不报错，workspace 闭环刷新 | argparse 又拒绝 keys |
| #99 | redo 先备份再删，失败可还原 | `shutil.rmtree` 回到原位 |
| #101 | `run_ocr()` 发射 `OCR_RUN_START/PROGRESS/DONE` token | 进度条永远 0% |

### P1 — 今天刚关的（防止再次断裂）

| Issue | 测试什么 |
|---|---|
| #97 | `meta.json` 含 `ocr_pipeline_version="2.0.0"`，probe 返回 stale=0 |
| #102 | `embed build --force` 创建 `.pre-rebuild-{ts}.db` 备份 |
| #103 | `probe_memory()` 返回 `build_state` 路由而非 ChromaDB 路径 |
| #96 | OCR 状态显示 Ready（非 Update Available），badge + action 匹配 probe |
| #98 | 所有 i18n 键在 en/zh 都有值，不出现原始 key |
| #104 | SR 状态卡渲染 `reason_code` → 正确 badge + action |

### P2 — 非可脚本化的（手动 + 视觉）

| Issue | 怎么测 |
|---|---|
| #100 | 打开 Obsidian 检查 CSS 不用硬编码颜色，对比浅色/深色主题 |
| #94 | 跑 `issue-94-wayfinder.sh`（聚合 P0+P1），确认所有子 issue 通过 |

## Helper 规范 (`_lib.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail

VAULT="${PAPERFORGE_TEST_VAULT:-D:/L/Med/test}"
PYTHON="${PAPERFORGE_PYTHON:-python}"
PASS=0
FAIL=0

assert() {
    local desc="$1"
    if eval "$2"; then
        echo "  ✓ $desc"
        ((PASS++))
    else
        echo "  ✗ $desc"
        ((FAIL++))
    fi
}

summary() {
    echo "---"
    echo "$PASS passed, $FAIL failed"
    return $FAIL
}

run_paperforge() {
    # 模拟用户在 Obsidian 里触发的命令（带 --vault 前缀 + 环境隔离）
    "$PYTHON" -m paperforge --vault "$VAULT" "$@"
}
```

## 每个脚本模板

```bash
#!/usr/bin/env bash
source "$(dirname "$0")/_lib.sh"

echo "=== Issue #XX: <title> ==="

# Step 1: 模拟用户操作
echo "Step 1: <what the user does>"
run_paperforge ocr run 2BB8VM5W  # ← 如果 argparse 拒绝，这里就炸

# Step 2: 验证数据
echo "Step 2: <what should be true>"
"$PYTHON" -c "
import json
from pathlib import Path
meta = json.loads(open('$VAULT/System/PaperForge/ocr/2BB8VM5W/meta.json'))
assert meta.get('ocr_pipeline_version') == '2.0.0', 'wrong version'
print('OK')
"

summary
```

## CI 集成

```yaml
# .github/workflows/acceptance.yml
- name: Run acceptance tests
  run: |
    for f in acceptance/issue-*.sh; do
      echo "=== $f ==="
      bash "$f" || exit 1
    done
```

Pre-commit hook（可选）：只跑 P0 的三个，不阻塞日常开发。

## 不过度设计的原则

1. **一个 issue 一个脚本** — 不做抽象框架
2. **用 assert + Python one-liner 验证** — 不引入新测试框架
3. **test vault 是固定 fixture** — CI 从 git 里 checkout 一份干净的
4. **失败了就 exit 1** — 不带 `--verbose` 和报告格式
5. **每个脚本独立可执行** — 不依赖先后顺序
