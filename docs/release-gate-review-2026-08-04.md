# PaperForge Release-Gate 处理汇报（2026-08-04）

> 供 GPT 审核使用。每条结论附代码证据 / 提交 / 验证结果，可逐项核对。
> 仓库：`LLLin000/PaperForge`（master）；本会话提交链：`ae3e505d` → `257e222d`（13 commits）。

---

## 0. 总览

| 项目 | 状态 |
|------|------|
| #117 原子阴影向量重建 | ✅ 关闭（7 轮 GPT review，最终接受 9/10） |
| 89-failure 清理 | ✅ 0 failed / 2596 passed / 7 xfailed（后全部清零） |
| 发布审计 7 个 P0 | ✅ P0-2…P0-7 全部落地；**P0-1 版本号按用户要求留给发布时** |
| CI（master） | ✅ 9/9 jobs 全绿（本会话修复前**从 1.5.15 起一直红**） |
| #118 七个 OCR 决策点 | ✅ 全部关闭（2 个真实生产 bug + 3 个测试修复） |
| 当前 xfail 数 | ✅ 0（曾 7 个） |

---

## 1. #117 Atomic Shadow Vector Rebuild（7 轮）

提交：`ae3e505d`→`960a60c8`→`aba21fb0`→`ff1f6d47`→`15333bec`→`cfbfe076`→`e0901d55`。

核心设计（每轮修复 GPT 发现的问题，全部先验证后修复）：

- **状态机**：`NEW→PREPARED→BUILDING→SEALED→VERIFIED→PUBLISHED`；提交点 = `os.replace`，`state=PUBLISHED` 紧随其后原子写入；publish 后 abort 为 no-op。
- **锁**：WriterLock 按 DB 路径可重入；`open_live_reader` 可重入读屏障（超时传播，不降级解锁）；全部 14 处 `get_connection(read_only=True)` 统一走读屏障。
- **身份**：`get_effective_api_base_url()`（DEFAULT_OPENAI_BASE_URL）在 provider/dim-cache/identity/persisted-state 四侧统一；`VECTOR_IDENTITY_VERSION=1` 触发 legacy 重建；`inspect_vector_layout()`/`VectorLayout` 单一契约（六表、每表 dim、**orphan-meta 检查**——vec0 `COUNT(*)` 含 tombstone，计数相等无意义）。
- **停止控制面**：`paperforge.embed-control.json` sidecar（原子写）、跨平台 `_pid_alive`、`completed_before_stop`、build 存活过 kill 窗口时诚实返回 rc=1。
- **验证器**：六表全查（0 行合法、缺 schema 拒绝）、按 collection 期望计数、首个非空 collection KNN；`_expected_dim` 来自 `ensure_vec_tables` 返回值（无候选 DDL 自证）。
- **过程中发现并修复的真实 bug**：WAL 在 publish 后回翻（WAL 只在新建 DB 初始化）、build_state 模型丢失（publish 后 resume 全量重嵌）、`retrieve_chunks` 因丢 import 的 NameError、`get_connection` 新建库 WAL 初始化顺序。
- **验证**：shadow 36/36；core 191 pass；全库 2526 pass / 89 基线逐名比对；生产数据副本真实 E2E（force→35 chunks→publish，journal 保持 DELETE；resume hash-skip；8 并发读 publish 干净；API 失败中止路径）。最终接受 9/10。

## 2. 89-failure 清理（3 批）

- `68cd9bb6`（46→…）：**2 个真实代码 bug** —— `ocr_document.py:5756` `max()` 空迭代崩溃（`max((...), default=0)`，解 13 个测试）；`status.py` 布局检查（orphan meta/掉 vec → unhealthy）。其余为测试漂移修复（test_vector_db 重写、lance 后端删除类、diagnostics 改接 merge_retrieve、deep_search CREATE_META、pr9b 维度 pin、embed/e2e 无 key 跳过等）。
- `9f80fb32`：OCR 测试漂移 5 处 + **6 个行为 xfail 绑定 #118**（生产 OCR 不动）。
- `8cbc4a93`：30 处测试漂移（migration `{key}.md` 自愈重命名契约、setup_wizard 改名、bootstrap 断言、skill_graph 中文关键词、memory_restore safety_class、literature_hub 超时 30→90s 等）+ 1 xfail（slugify 18xx）。
- 结果：**0 failed / 2596 passed / 7 xfailed**；25 errors 全部是 Windows 共享沙箱目录锁（WinError 32，单独跑通过，Linux CI 无）。

## 3. 发布审计 7 个 P0 → #119/#120/#121

审计确认 7 个 P0 全部真实（版本、vector extras、`_callPython` null 返回、双 UI、双 workflow、CI gate、license）。除 P0-1（版本号，用户发布时处理）外全部转 issue 并落地：

### #119 运行时依赖闭环（P0-2）
`3e658410`：
- `managed-runtime.ts`：pip 安装 `paperforge[vector]==<v>`（原裸 `paperforge` → 新用户装完点 Build Index 必缺 sqlite-vec）；安装后隔离验证 `import paperforge, openai, sqlite_vec`。
- `embed.py` status 依赖块：加入 `import sqlite_vec` → 缺失时报告哪个没装。
- `probe.py` memory Gate 5a：完成但缺依赖 → **不再误报 ready**，改 `memory.dependencies_missing` + `memory.install_vector_deps` 动作（`paperforge setup`）。
- `pyproject.toml`：`requires-python >=3.10 → >=3.11`。
- 验证：py_compile 通过；4 个相关测试 16 passed；生产 `probe memory` 依赖齐全时仍 ready。

### #120 前端 EmbedBuildController（P0-3/P0-4）
`3e658410`：
- **背景**：`_dispatchMemoryBuild('embed')` 走 `_callPython` 异步分支**返回 null** —— 无子进程句柄 → 重复点击起多个 build、reject 时 UI 永久 running、unload 不杀进程。
- **新** `services/embed-build-controller.ts`：状态机 `idle→resolving_credentials→running→stopping→success|success_with_warning|failed`；`start()` 由 `busy` getter 防重复启动；**先解析凭据（buildTargetedEnv）再 spawn**（真实 ChildProcess 句柄）；`PYTHONIOENCODING/PYTHONUTF8`；stdout 解析 START/PROGRESS/DONE；stderr 收集（尾部 300 字符）；`close` code 0→success，否则按 warning 有无分 success_with_warning/failed；`stop()` 走 `embed stop --json`（45s 超时）识别 `stopped|completed_before_stop`，子进程仍活则回 running；2s 轮询 `embed status --json` 更新 build_state 进度；`dispose()` 杀子进程+清轮询。
- `progress-parser.ts`：`EMBED_PHASE:`/`EMBED_NOTICE:` 前向兼容解析（后端尚未发射，纯增量）。
- `settings.ts` `_dispatchMemoryBuild('embed')`：controller + `PaperForgeConfirmModal` 强确认（API 成本 / 索引可用到验证完成 / 不删数据 / 可停止）；状态驱动 activity 标签与 Notice（成功 / 警告 / 失败 / completed_before_stop）。
- `main.ts onunload`：`_embedController?.dispose()`。
- **坑**：`Promise.withResolvers` 在 ES2018+Node20 不可用 → 新建 `services/deferred.ts` 共享 helper。
- 验证：typecheck 干净；vitest 全绿（5 个 embed 测试改确认后契约）；**顺带修 3 个 pre-existing 插件测试失败**（见 §5）。

### #121 发布链（P0-5/P0-6/P0-7）
`8144fed8`：
- **P0-5**：`release.yml`+`publish.yml` 双 workflow 同 tag 竞态（一个建 Release 一个删了重建）→ 合并为单一 `publish.yml`：版本/tag 强校验（tag ≠ `__version__` 直接失败，杜绝 skip-existing 静默跳过旧版本）→ Python build + wheel 装回验证 vector 栈 → 插件 vitest+typecheck+build → PyPI → **一次** Release（含插件 4 件 + `dist/*` + sha256 checksums）。
- **P0-6**：alls-green 从 `needs [unit, plugin]` + `allowed-skips: version-check` 收紧为 needs **全部 8 个 job**（version-check / ruff(新) / unit×3 / protocol-tests(新) / plugin-tests(含 typecheck+build) / e2e），allowed-skips 移除。
- **P0-7**：pyproject 删 MIT classifier（LICENSE 实为 CC BY-NC-SA 4.0）+ 删过时的 3.10 classifier。

## 4. CI 基线修复（本会话第 4 项工作，`7b1a93d7`）

**发现**：#121 把真实 gate 加上后，CI 暴露 master **自 1.5.15 起每个 run 都红**（查证 e0901d55 起 7 个 run 全 failure，被 allowed-skips 掩盖）。

| 故障 | 证据 | 修复 |
|------|------|------|
| `versions.json` 缺 1.5.14/1.5.15 | 版本同步脚本 exit 1；列表只到 1.5.13 | 补两行（Obsidian 更新门依赖；非升版本） |
| CI 装 `.[test]` 缺 chromadb | 全新 runner 上 L1/L2 collection 即 `ModuleNotFoundError`（本地过因为开发环境早装） | 三处 install 改 `.[test,vector]` |
| **12 个 F821 undefined name** | ruff 新 gate 揪出；其中 **1 个是 #119 自己引入**：`probe.py:905` 写成 `USER_STATE_ACTION_NEEDED`（正确常量 `USER_STATE_ACTION_REQUIRED`）——deps 缺失分支运行时必炸 | 常量修正 + 11 处惰性注解补 import（sqlite3/Callable/Any/Image/Path/RenderOutput，全部零行为变化） |
| ruff gate 62 错误 | 50 个是存量 F401 风格债 | gate 收窄 `--select F821,F822,F823`（真 NameError 类），F401 留本地 |
| 插件 3 个 pre-existing 失败 | ① triplet 测试硬编码 win32-x64 而 `ManagedRuntime` 读 `process.platform`（本地 Windows 恰好命中，Linux CI 暴露）② renderActionButton 测试用 `dispatchEvent`（绕过 jsdom 的 disabled 检查，`.click()` 才尊重）③ Help→Overview focus 测试切 tab 后没调 `display()` 重渲染 | 三个测试修复，产品代码零改动 |

验证：本地 ruff F821 清零、version-sync PASS、协议套件 41 passed、vitest 414/414、**CI 9/9 success**。

## 5. #118 七个 OCR 决策点（本会话第 5 项工作，`42324657`）

每个 xfail 先去掉标记跑真实断言、追生产代码、查 fixture 证据，再定决策：

| 决策点 | 证据 | 判定 | 处理 |
|--------|------|------|------|
| ① OCR_REDO PROGRESS ×3 | 生产实测输出 `OCR_REDO_START:3 … OCR_REDO_DONE` **无 PROGRESS**；`redo_papers_for_keys` 主循环（Phase1–4+refresh）从不调 `progress_callback`，只在 3 个异常分支调 | **真实生产 bug** | 主循环每 key 后发射；前端进度条不再卡 0/N |
| ② cluster crop 图引用 | 测试传 `pdf_path=None` 却断言 markdown 必须引用整簇 crop 图——无 PDF 不可能裁剪；vnext 在 `was_cropped=False` 时不写图（旧版写指向不存在文件的断链） | 测试矛盾 | mock `_crop_asset_from_pdf` 成功路径；保留"失败不写断链"诚实行为 |
| ③ 任务级 fitz.open | `_crop_asset_from_pdf` 的 `fitz.open` 无 try/except，调用方（主 OCR + rebuild）也无保护 → 坏 PDF 崩掉整篇/整批 | **真实生产 bug** | open 失败 → 返回 False → 无图 note + 调用方 failed_keys 记账，与主流程单篇容错一致 |
| ④ DWQQK2YB Fig 4 页码 | fixture 证据：Fig 4 题注+7 资产在 **p41**（p40 是 Fig 3 的 caption）；vnext 产生**两条** matched entry（41 页真条目 + 40 页 0 资产幽灵条目）；测试 helper 的 dict 推导取最后一条 → 幽灵覆盖真条目 | 测试 helper 缺陷（跨页续接是有意设计，图 2 测试背书） | helper 改为优先资产非空条目；**幽灵条目现象开 #122 跟踪**（OCR 领域待决策） |
| ⑤ slugify 18xx | `worker/_utils._extract_year` 用 `\d{4}`（当前生产行为，提取 1899）；`(19\|20)` 锚属于 `core/date_utils.extract_year`（另一个函数）；测试 import 的是宽松版却按严格版断言 | 测试期望过时 | 期望翻转（1899 提取对 slug 文件名无害且 19 世纪文献真实存在） |

验证：4 个文件 **75 passed / 52 skipped（xfail 归零）**；宽回归（unit/worker+cli+rebuild+shadow）**211 passed**；CI 全绿。
（注：`test_ocr_progress_contracts.py` 与 `test_ocr_real_paper_regressions.py` 在本次提交做了 LF 行尾规范化——HEAD blob 携带历史未规范化的 CRLF；内容变化仅为上述行。）

## 6. 全部验证证据汇总

| 层 | 结果 |
|----|------|
| 插件 | `npm run typecheck` 干净；vitest **414/414** |
| Python 协议 | shadow+pr9c+deep_search+query_diagnostics **65 passed**（CI L2 同集） |
| 宽回归 | worker+cli+rebuild+shadow **211 passed** |
| 生产烟测 | `probe memory` = ready（依赖齐全）；`embed status` = ok |
| CI | **9/9 jobs success**（version-sync、ruff、unit×3 OS、protocol、plugin、e2e、alls-green） |
| 发布管线 | 两个 workflow YAML 解析通过；版本脚本 PASS |

## 7. 未决事项（有意保留）

1. **P0-1 版本号**（1.6.0 + 6 个 manifest 文件同步）——用户明确发布时自行处理，未动。
2. **#122** DWQQK2YB Fig 4 幽灵 matched entry（`page=40, 0 assets, legend_id=1` 指向 Fig 3 的 caption 块）——OCR 配对领域决策，已由 helper 规避，非阻断。
3. **`_renderVectorReady` 旧引导 UI** 未并入 controller（功能可用，缺 stop/confirm 生命周期）——技术债，留下一迭代。
4. **50 个存量 F401** unused imports——风格债，有意排除在 CI gate 外。
5. wayfinder v2 队列 #97–#105——下一里程碑，非发布阻断。
