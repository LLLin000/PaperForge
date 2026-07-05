# PaperForge 命令参考

> 所有 CLI 命令和 Agent 命令速查。

---

## 命令矩阵

| Agent 命令 | CLI 命令 | 用途 | 前置条件 |
|-----------|---------|------|---------|
| `/pf-sync` | `paperforge sync` | 同步 Zotero，生成正式笔记 | BBT JSON 导出 |
| `/pf-ocr` | `paperforge ocr` | PDF OCR 文本与图表提取 | `do_ocr: true` |
| `/pf-status` | `paperforge status` / `paperforge runtime-health` | 查看系统状态 | 配置完成 |
| `/pf-deep <key>` | `paperforge deep-reading` (队列) | 三阶段精读 (Agent 层) | OCR done + `analyze: true` |
| `/pf-paper <key>` | — | 文献问答 (Agent 层) | 正式笔记存在 |
| `/pf-end <key>` | — | 结束精读/问答 Session (Agent 层) | 精读或问答进行中 |
| `/pf-log-reading` | `paperforge reading-log --write <key>` | 记录阅读笔记 | 精读进行中 |
| `/pf-log-session` | `paperforge project-log --write` | 总结会话决策 | 会话结束 |

---

## CLI 命令

### `paperforge paths`

```bash
paperforge paths                    # 打印 vault 路径清单
paperforge paths --json             # JSON 格式输出
```

### `paperforge status`

```bash
paperforge status                   # 完整状态检查
paperforge status --json            # JSON 输出
```

### `paperforge sync`

```bash
paperforge sync                     # 完整同步
paperforge sync --dry-run           # 预览
paperforge sync --selection         # 仅 selection-sync
paperforge sync --index             # 仅 index-refresh
paperforge sync --rebuild-index     # 强制重建索引
paperforge sync --prune             # 预览清理孤儿笔记 (dry-run)
paperforge sync --prune-force       # 执行清理
paperforge sync --json              # JSON 输出
```

### `paperforge selection-sync`

```bash
paperforge selection-sync           # 同步 Zotero 选择到文献记录 (向后兼容)
```

### `paperforge index-refresh`

```bash
paperforge index-refresh            # 刷新正式文献笔记 (向后兼容)
```

### `paperforge deep-reading`

```bash
paperforge deep-reading             # 查精读队列状态
paperforge deep-reading --json      # JSON 输出
```

### `paperforge deep-finalize`

```bash
paperforge deep-finalize <KEY>      # 标记精读完成并通知 Dashboard
paperforge deep-finalize <KEY> --json
```

### `paperforge repair`

```bash
paperforge repair                   # 扫描分歧 (dry-run)
paperforge repair --fix             # 修复
paperforge repair --fix-paths       # 修复 PDF 路径
paperforge repair --json            # JSON 输出
```

### `paperforge ocr`

```bash
paperforge ocr                      # 处理队列 (旧式)
paperforge ocr --key <KEY>          # 处理指定文献
paperforge ocr --diagnose           # 诊断模式
paperforge ocr --json               # JSON 输出
paperforge ocr run                  # 运行 OCR 队列 (新式)
paperforge ocr doctor               # 诊断 OCR 配置和连接
paperforge ocr doctor --live        # 运行真实 PDF 测试 (L4)
paperforge ocr redo                 # 重新运行所有标记 ocr_redo 的文献
paperforge ocr redo <KEY> [KEY...]  # 重新运行指定文献
paperforge ocr redo --dry-run       # 预览待重做的文献
paperforge ocr list                 # 列出所有 OCR 维护状态
paperforge ocr list --json          # JSON 输出
paperforge ocr list --manifest      # 输出 key→sha256 清单
paperforge ocr list --keys <KEY>... # 仅指定 key 的信息
paperforge ocr rebuild              # 从已有 raw blocks 重建 OCR 产物
paperforge ocr rebuild <KEY>...     # 重建指定文献
paperforge ocr rebuild --all        # 重建全部
paperforge ocr rebuild --status done # 按状态过滤
paperforge ocr rebuild --dry-run    # 预览
paperforge ocr rebuild --resume     # 跳过已有检查点的文献
```

### `paperforge context`

```bash
paperforge context <KEY>            # 单篇文献的 AI context 包 (JSON)
paperforge context --domain 骨科    # 按 domain 过滤 (JSON 数组)
paperforge context --collection "path/to/coll" # 按 collection 过滤
paperforge context --all            # 输出全部 canonical index
```

### `paperforge dashboard`

```bash
paperforge dashboard                # 聚合统计和 Dashboard 权限
paperforge dashboard --json         # JSON 输出
```

### `paperforge embed`

```bash
paperforge embed build              # 构建向量索引
paperforge embed build --resume     # 续建
paperforge embed build --force      # 强制重建
paperforge embed build --json       # JSON 输出
paperforge embed status             # 查看向量 DB 状态
paperforge embed status --json      # JSON 输出
paperforge embed stop               # 停止构建
paperforge embed stop --json        # JSON 输出
```

### `paperforge retrieve`

```bash
paperforge retrieve "<query>"       # 跨 OCR 全文语义检索
paperforge retrieve "PEMF" --limit 10 --json
paperforge retrieve "75 Hz" --no-expand
```

### `paperforge query-plan`

```bash
paperforge query-plan "<query>" --intent discover    # 文献发现
paperforge query-plan "<query>" --intent content      # 内容检索
paperforge query-plan "<query>" --intent known-paper  # 已知论文定位
paperforge query-plan "<query>" --intent discover --json
```

### `paperforge prune`

```bash
paperforge prune                     # 预览删除孤儿产物 (dry-run)
paperforge prune --force             # 实际删除
paperforge prune <KEY> [KEY...]      # 仅处理指定 key
paperforge prune --json              # JSON 输出
```

### `paperforge memory`

```bash
paperforge memory build              # 构建 memory DB
paperforge memory build --json       # JSON 输出
paperforge memory status             # 查看 memory DB 状态
paperforge memory status --json      # JSON 输出
```

### `paperforge search`

```bash
paperforge search "<query>"          # 元数据全文搜索
paperforge search "<query>" --json
paperforge search "PEMF" --domain 骨科 --ocr done --year-from 2020
paperforge search "PEMF" --deep done --lifecycle fulltext_ready
paperforge search "PEMF" --next-step ocr --limit 10
```

### `paperforge paper-status`

```bash
paperforge paper-status <query>      # 查找文献状态 (key/DOI/title/alias)
paperforge paper-status "XGT9Z257" --json
```

### `paperforge paper-context`

```bash
paperforge paper-context <key>       # 文献完整上下文
paperforge paper-context "XGT9Z257" --json
```

### `paperforge reading-log`

```bash
paperforge reading-log --write <KEY> --section "Discussion P12" --excerpt "..." --usage "..." # 写阅读笔记
paperforge reading-log --render      # 渲染 reading-log.md
paperforge reading-log --lookup <KEY> # 查某文献的阅读笔记
paperforge reading-log --since 2026-01-01 --limit 100 --output notes.md # 导出
paperforge reading-log --validate reading-log.md
paperforge reading-log --import reading-log.md
paperforge reading-log --correct <ID> --correction "..." --reason "..." # 修正笔记
paperforge reading-log --json
```

### `paperforge project-log`

```bash
paperforge project-log --write --project "ProjectX" --payload '{"hours":2,"status":"progress"}' # 写工作日志
paperforge project-log --list --project "ProjectX"
paperforge project-log --render --project "ProjectX"
paperforge project-log --project "ProjectX" --json
```

### `paperforge agent-context`

```bash
paperforge agent-context             # 生成 Agent 引导上下文
paperforge agent-context --json      # JSON 输出
```

### `paperforge runtime-health`

```bash
paperforge runtime-health            # 检查 memory layer 运行时健康
paperforge runtime-health --json     # JSON 输出
```

### `paperforge base-refresh`

```bash
paperforge base-refresh              # 刷新 Obsidian Base 视图
paperforge base-refresh --force      # 强制全量重建
```

### `paperforge doctor`

```bash
paperforge doctor                    # 验证安装配置
paperforge doctor --json             # JSON 输出
```

### `paperforge update`

```bash
paperforge update                    # 更新到最新版本
```

### `paperforge setup`

```bash
paperforge setup                     # 交互式设置
paperforge setup --headless          # 非交互式 (AI 代理)
paperforge setup --agent opencode    # 指定 AI Agent 平台
paperforge setup --paddleocr-key "KEY" --paddleocr-url "URL"
paperforge setup --skip-checks       # 跳过环境检查
paperforge setup --modular           # 使用模块化设置 (v2.1+)
```

### `paperforge paper-lookup`

```bash
paperforge paper-lookup "<query>"    # L4 网关: 定位文献
paperforge paper-lookup "PEMF" --json --limit 10
```

### `paperforge content-discovery`

```bash
paperforge content-discovery "<query>" # L4 网关: 内容发现
paperforge content-discovery "骨科 生物力学" --json --limit 10
```

### `paperforge paper-navigation`

```bash
paperforge paper-navigation "<query>"  # L4 网关: 文献结构导航
paperforge paper-navigation "XGT9Z257" --json
```

### `paperforge scoped-fetch`

```bash
paperforge scoped-fetch "<query>"      # L4 网关: 范围受限获取
paperforge scoped-fetch "PEMF 75 Hz treatment protocol" --json --limit 10
```

---

## 相关文档

- [使用教程](getting-started.md)
- [故障排除](troubleshooting.md)
- [更新指南](update-upgrade.md)

---

## 测试

### 合成 OCR 测试（CI 默认）

```bash
python -m pytest tests/test_ocr_synthetic_fixtures.py -q --tb=short
```

### 真实文献 OCR 回归测试（可选集成测试）

需要设置环境变量指定 vault 路径和要测试的文献 key：

**Unix/macOS:**

```bash
PAPERFORGE_REAL_OCR_VAULT="/path/to/Literature-hub" PAPERFORGE_REAL_OCR_KEYS="SAN9AYVR,2GN9LMCW" python -m pytest tests/test_ocr_real_paper_regressions.py -q
```

**PowerShell:**

```powershell
$env:PAPERFORGE_REAL_OCR_VAULT="D:\path\to\Literature-hub"; $env:PAPERFORGE_REAL_OCR_KEYS="SAN9AYVR,2GN9LMCW"; python -m pytest tests/test_ocr_real_paper_regressions.py -q
```

不设置环境变量时，真实文献测试自动 SKIP。

