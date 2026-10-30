# PaperForge 模块状态与接口收敛（#356）

## 结论与边界

当前进入 **Integration & Release Stabilization**：冻结既有 `PFResult`、Probe v2、Action Registry、NDJSON 和 `PaperForgeClient` 契约，不扩功能或新增控制内核；先收口上游集成，再以同一最终源码、wheel、插件 bundle 和宿主做统一候选认证，独立处置发布风险。本文是证据与计划的投影，任务状态以 GitHub Issue、发布接受以 CI/owner 门禁为准。

public 分支的产品修复提交仍为 **`5aa440ed14eb4eb856467fb439eb06f52ec61f78`**；本轮已在同一 worktree 的独立本地分支 `integration/offline-preview-356` 完成祖先集成，固定候选源码为 **`9ead0993290812f0575236fbe81b7620f658189d`**，见末节。本地候选已配对构建和包级验证，但不是 master/Release，也未通过完整 H 或两次 UI 旅程。既有 PR/master 未改，整合分支未推送；public 只追加证据与历史身份说明。旧阶段产物/收据保留，不冒充当前候选或正式发行。RC6 续作（2026-10-30）是另一条身份：基于 `42437546116a04c27efd917df94b0c845331e697` 的未提交 overlay，`2.0.0rc6` 配对 wheel/bundle 与离线 CLI smoke 已验证；source commit、新候选 ref 和 Hosted CI/H 尚未完成，详见末尾 G3 更新。

首次使用候选 `9ead099` 的两次隔离安装暴露路径投影未刷新：Python 配置为 `System`，向导却显示根目录下的 `PaperForge/exports`；两份原始失败证据保留。当前工作树修复在成功 setup 后重新读取 Python 配置并刷新既有投影；独立宿主通过 UI 将测试库目录改为 `TrialSystem` 后，配置读回和向导路径一致，无需重载。此宿主绿证是已安装运行时的路径修改，不等同于全新安装绿证；修复后最终候选身份和两次完整旅程仍待验证。真实 OCR/Embedding 继续冻结。

隔离 B 试用库：正式索引 189 篇、29 个 Collection；首次观察 Obsidian 缓存 179 篇，完整重启后为 189 篇且 key 唯一。实际 PDF 可打开，研究记录保存并按非标题用途找回，重启后仍可打开；外部 Zotero PDF 自动带入记录时被来源校验拒绝，清空后仅保存为未核验记录。通过界面建立本地 Memory 后元数据搜索命中，向量索引未建立。重复同步从 UI 发起后观察到真实 client 的成功终态且仍有 189 个唯一 key；自动同步也启用，终态归属尚未独立隔离。两次完整同候选旅程、来源精确定位及最终升级仍未证明。

隔离 A 继续使用原 `9ead099` bundle：打开实际 PDF、保存未核验记录并按用途找回；本地 Memory 构建后元数据检索命中。完整重启后 189 个唯一论文、`System` 设置及记录读回。A、B 的 bundle 不同，不能合称两次同候选通过。当前索引中的 164 个 PDF 解析路径均位于 Vault 外；来源核验要求 Vault 内且与索引路径一致，不能通过擅改索引或复制后冒称同一来源来验收。两台试用宿主均正常退出，私有证据保留；升级与精确来源验证仍未完成。

未收口的修复风险：只读复查指出，路径配置未水合时 Setup 的 BBT 检测仍可能对错误投影目录执行创建；配置 readback 字段缺失时镜像可能被置空。这些是待修复和验证的风险，不以已有测试或路径修改实机证明覆盖。RC4 → 最终候选的升级、取消和恢复须在修复并固定对应 wheel/bundle 后独立验收；旧版本回执不代替最终候选证据。完整 H 和正式发布仍待独立门禁。

后续本地修复：Setup 在路径尚未水合时不再展示或创建猜测的 exports 目录，复制与检测禁用；配置回读缺失必需目录时拒绝更新投影并显示失败。定向回归 86 项与 typecheck 通过；这不等于修复后全新安装、RC4 升级或取消恢复的宿主验收。软链接可用于打开外部 PDF，但当前来源核验会解析实际目标并拒绝指向 Vault 外的链接，不能将两者混为一谈。

本轮发现并修复运行时清理安全问题：原 `retireUnusedRuntimes(null)` 会删除所有 `venv-*`，实文件系统回归复现；现仅当 active root 指向当前运行时目录中存在的 generation 时清理，其余情况全部保留。受影响的 managed-runtime 与 setup 回归 137 项通过，typecheck/build 通过；仍未实机执行最终候选的升级与取消。

修复后插件完整离线回归 645 passed / 1 skipped。直接在工作树离线构建的试验 wheel 虽与当时 bundle 和 237 个 Python 文件逐字节一致，但包含 `skills/paperforge/scripts/__pycache__/pf_deep.cpython-312.pyc`，且源树未提交：该 wheel 已隔离，不能作为安装或发行候选。需从干净、身份固定的源码重新构建并检查完整归档后，才执行最终安装与升级验收。

随后从已提交基线归档加明确记录的 5 个未提交文件哈希，在独立构建目录生成干净试验 wheel：237 个 Python 文件和 4 个插件资产与快照一致，归档内无 `.pyc`；wheel SHA256 `7a0a00aadf429afe9c66a44c6f120a61e13fd03d7a6bbe76f11c7b9baf21b6ab`，bundle SHA256 `3835d4ccd9c76686af7f57404ea8c625d3f23b97f1fdd582c7df0866a46ba8c0`。在独立 Python 3.11.15 venv 使用离线依赖安装，版本和模块路径核验、依赖检查、CLI `--help` 通过；这是未提交快照的包级 smoke，不是正式发行或 UI 安装／升级验收。

后续隔离宿主的真实 UI 安装在 pip 阶段失败，pointer 未发布。此前“pip 把 legacy-vector 的 chromadb 自动纳入 vector”“system Python 3.14 导致 UI 安装失败”的归因均证据不足，现撤回；所读 wheel METADATA 明确将 chromadb 仅列为 legacy-vector。部分手动复现使用了错误 ABI、已有同版本安装或未隔离的工作目录，不能作为 UI 根因证据；全新环境没有旧运行时，也不能证明旧运行时保留。原始失败回执保留，需记录实际 UI 子进程解释器、受控环境和完整私有错误后再定因。不得通过补装 chromadb、跳过依赖或改变安装产品需求来制造通过。

隔离宿主进程环境实测 `PIP_CONSTRAINT` 指向不存在的 `path-refresh/constraints.txt`；使用相同宿主环境执行 pip dry-run，返回无法打开该文件。此证据证明验收环境存在阻断，不证明先前 UI 每次失败均由此引起。用户另行决定移除 ChromaDB 及迁移入口，保留 sqlite-vec；当前未提交工作树的定向 Python 回归 112 项通过，插件定向回归 182 项、typecheck 和 bundle build 通过。CLI `embed --help` 显示 build/status；新配对 wheel、真实 UI 安装及升级尚未验证，不是正式发行验收。旧 Chroma 存储未删除；任何 embedding 重建可能产生费用，不自动执行。

续验候选基于 `795792ce` 加未提交变更快照，wheel SHA256 `c01e94bf2a53f634669fc66553ea31b536426bb16c4f828e979794b03d708922`、bundle SHA256 `5f06cfe68445f599c6da9c3a7b1f0cad9159d1b36cfeecd656a24dedce7e5c9b`；235 个 wheel Python 文件与快照一致、无 `.pyc`、包依赖无 chromadb。Python 3.11 隔离 venv 从离线 wheelhouse 安装 `paperforge[vector]` 并通过 pip check；这不代表 managed UI 安装或升级通过。真实 Obsidian 1.14.5 隔离宿主已发起 UI 安装，观察时仍在运行、pointer 尚未发布；未作成功判定。OCR 与 embedding 凭据在系统 keyring 中显示 available，但未验证其身份或有效性；用户已允许指定 provider，真实请求与数据上传结果仍未验证。

后续观察：隔离 Obsidian 1.14.5 的真实 Setup 安装达到“已就绪”，Python 发布的 pointer 指向隔离 HOME 内 candidate，安装的模块与 distribution 均为 `2.0.0rc5`；升级、取消及恢复尚未验收。用户授权后，仅提交一页合成 PDF：候选包的 `PaddleOCRProvider` 返回 queued → running → done，抓取结果 1 页；指定 SiliconFlow `Qwen/Qwen3-Embedding-4B` 对一条合成文本返回 HTTP 200、2560 维、8 prompt tokens。这是提供方连通性与 OCR provider API 测试，不是产品 OCR→向量构建→检索的端到端验收。已有 keyring 中的 embedding 凭据对指定服务返回 401，用户提供的凭据返回 200；密钥未写入本报告。

真实文献计时续验（用户授权上传，隔离复制，未修改原 Zotero；候选 wheel/bundle 同上）：三篇文献同步 UI 客户端终态成功 2.674 秒；单篇 8 页 OCR UI 确认至本地 done 14.110 秒（meta 处理 8.005 秒）；两篇并行 UI 确认至两篇 done 31.324 秒（19 页 24.377 秒、2 页 27.365 秒）。三篇均一个 provider job、零重试、云端 GET done 与本地 done 一致，UI 显示已处理；未覆盖真实运行中/异常云状态 UI。同步后 memory CLI 0.321 秒，embedding CLI 重建 4.820 秒、3 篇 56 chunks，单篇 scoped deep retrieve CLI 2.048 秒、5 条属于指定论文；真实 UI 搜索观察到 5 张卡片但等待选择器写错，故无有效渲染耗时。OCR 离线模拟状态/取消回归 41 passed / 1 skipped，非真实云故障验收。`ocr status --batch` 对已完成批次显示 complete/0 unsettled；本次 `ocr-queue.json` 仍记录 4 条 pending，是快照观测，不推断其为权威或产品故障。单行合成样本首次 embedding 返回 0 篇/0 chunks，不能算向量功能通过。

验收脚本失误必须保留：拦截 OCR `runAction` 时误以为其返回同步句柄，UI 报错但一条合成任务已提交并完成；后来单篇真实试验误选合成行，等待 252.739 秒后发现真实 PDF 未提交；修正行选择并在确认弹窗核对 scope 后才进行上述三篇真实任务。首次 UI 安装实际开始时间未捕获，不能报告安装耗时；RC4 升级、停止/恢复、真实 401/超时及收费操作的全量状态映射仍待验证。代码检查显示 `ocr-workspace.ts` 失败提示只读取 `availability_reason` 否则显示 exit code，而 OCR action 的 pending/failed 提示写在错误 message；取消提示是否引导状态查询/恢复也需真实或可靠集成验收，不将静态审查当实机失败。

后续全流程续验：重启后的真实 Obsidian UI 深度检索在 3.496 秒渲染 5 张结果卡；同一论文上下文仍在，但卡片未包含该论文标题，故只记为 UI 查询渲染通过、结果范围未完全证明。隔离真实 PDF 打开耗时 0.252 秒；研究记录保存 0.737 秒，检索 0.948 秒，重启后打开 0.191 秒，记录内容和“来源未知/未核验”状态均保留。三篇真实 OCR 输出的 render audit 总耗时 5.668 秒：两篇 CLEAN，一篇 DEGRADED，2 个 P0 `render_dangling_asset_reference`，均为第 3 页缺失表格图片，诊断为 `source_asset_unavailable` / `pdf_input=missing`，建议 rerender。隔离验证确认同一 PDF locator 经 `resolve_pdf_path` 可解析为真实文件，但后处理后续阶段又从 `meta.source_pdf` 重新构造未解析路径；这是待修复的具体渲染根因，尚未改代码或重跑。

RC4 升级续验：从官方 release 下载的 RC4 wheel 与 checksums 匹配，tar.gz 下载返回 `unexpected EOF` 且 checksum 不匹配，未使用 tar；RC4 wheel 的 vector extra 仍包含 ChromaDB。隔离 RC4 venv 安装首次 pip 运行超过 232 秒未终止，保留该超时证据并停止自有进程；使用 uv 离线补齐依赖后，RC4 import/version、pip check、Python setup pointer 发布均通过。真实 UI 读取到 RC4 pointer/runtime，但插件 bundle 为 RC5；重装按钮进入 Setup 后实际没有候选安装按钮，UI 随后显示基础环境已就绪却仍指向 RC4，未形成 RC4→RC5 upgrade PASS。不得把历史 B-upgrade 收据或当前 fresh install 代替本次候选升级。

失败/取消边界：隔离 loopback provider 的 D04 cancel 与 J02 partial batch 均 VERIFIED，合计 80.153 秒（receipt 分别 52.560 秒、26.166 秒）；它们证明进程取消、单终态、部分成功和不重复提交，不证明真实云端故障 UI。真实云端本轮仅做成功任务和只读终态查询；未注入真实 401/429/超时/取消，未验证 UI 是否展示 pending 的“重新运行/状态-resume”指令。当前代码审查仍发现 action error message 与工作区 fallback notice 可能丢失具体原因；这保持为阻断项，不宣称完成。

受控故障续验完成（实际 Obsidian/CLI 与 loopback HTTP，不冒称真实云失败）：UI 点击停止后 3.099 秒退出本地 watcher，provider 恰好 1 次提交，提示“已提交的服务端任务仍会继续，请查看 OCR 状态”；本地保持 running，`ocr status --batch` 显示 incomplete/1 job，切换受控服务到 done 后，CLI resume 6.614 秒完成且 submit count 仍为 1。UI 对外部 CLI resume 的结果未自动刷新，重启后才读回。新隔离 scope 的受控 HTTP 401 在 3.707 秒返回，本地 blocked，实际 UI 显示“已阻塞”；但 Action terminal 错误码是 `OCR_POLL_TIMEOUT`，message 建议重跑轮询，是已复现的错误指令分类，不只是代码推测。未通过此失败边界。

PDF locator 修复已在源码实施并回归：只解析一次，在页渲染、span backfill、fingerprint 和 object materialization 复用同一真实文件，meta 仍保留原 locator；新增真实 PDF/wikilink/CWD 隔离行为测试，定向门禁 45 passed。真实载荷在另一个隔离副本离线 replay 6.663 秒，原来缺失的 PDF input 变为 available；但两个表格仍没有 asset/bbox，因此 0.474 秒 audit 仍为 DEGRADED/2 issues，不能声称缺图已修复。原候选 wheel/bundle 未重建，以上代码修复不能归入已安装候选的绿证；应在完整修复后重建新的配对候选重新验收。三篇原 PDF 与隔离输入 checksum 一致，原库未改；三篇原 OCR 的 raw/render/meta 和 cleared pending marker 均在重启后保留。

本轮收口：任务“完成”表示执行测试并记录 verdict，不代表各门禁均通过。RC4→候选升级恢复 FAIL（重装入口未执行安装且仍读 RC4），渲染 FAIL（两条 P0 缺图），401 指令分类 FAIL（blocked 被包装为 poll-timeout）；这些故障不能因 45 项回归通过而降级或覆盖。PDF locator 子修复经一次 correctness/maintainability 审查，无 P0–P2 finding；仍未覆盖剩余表格 geometry/asset 缺口。记录/PDF/重启读取通过；UI 搜索可渲染但相关性与范围未完全验收。受控云异常/取消使用 loopback，真实云仅验证成功与终态读取，429/长超时未做实机证明。所有自有验收宿主正常退出，loopback 服务关闭，临时 keyring 文件删除，原系统 keyring 未改，完整逐步 timing 保留于隔离 trial `timings.json`。无 commit/push/CI/release；本 worktree 无 `PROJECT-MANAGEMENT.md`，未在主 checkout 替写台账。

修复候选续验（不覆盖以上失败记录）：基于 `795792ce` 加未提交工作区快照，wheel SHA256 `0fe49344848bbc837655e2c5c59cb6db8801a138150fc539a59ee85fa4a168b3`，bundle SHA256 `7bf71064468f1c3cc5221b4814ee4df283cf3942d2f3a41616623be09c2180f2`；235 个 Python 文件与快照一致，无 `.pyc`。Python 定向回归 297 passed/1 skipped，插件定向回归 119 passed、typecheck/build 通过。保留的真实 OCR 载荷离线重放后 audit CLEAN、无悬空引用；缺少几何的对象保留真实文字，不能据此声称缺失的表格图像已恢复。

隔离 Obsidian 1.14.5 的 RC4→候选实机：取消前发布时保留 RC4 pointer；随后经基础环境的“重新安装”发起安装，141.227 秒观察到 Python 发布 RC5 pointer，安装后版本与路径验证为 RC5，旧环境在发布后删除，控制中心返回就绪。重要限制：初始 RC4 后端仍被 RC5 控制中心显示为“已就绪”，显式重装入口可用，但自动提示版本不匹配尚未解决；取消点击自动化报错后 UI 已显示取消、pointer 未变，不能记作完整取消时序证明。候选受控 401 UI、真实 429/长超时和修复后完整双旅程仍未复验，不能宣布完整验收或正式发布。

受控 401 续验：隔离 Obsidian 1.14.5 使用已安装的 `0fe493…` 后端及独立 bundle `fb493bd6abffe46394f31f162026c2fa2d13b71a8b0b95b1a5f279eac0d39da8`；合成 PDF 发往 loopback 401，无云请求。首轮发现 notice 虽显示 blocked 指令却缺论文 key：测试此前把 keys 放在 PFResult 顶层，实际 wire 位于 `data`。修正读取位置并按真实 wire 形状回归（改前 2 失败，改后插件定向 119 passed、typecheck/build 通过），重载插件后真实 UI 再执行一次受控请求，notice 显示合成论文 key 和凭据/源文件修复指令，列表显示阻塞；只证明 loopback 401，非真实云失败。宿主退出、loopback 关闭、临时 keyring 删除；该 bundle 尚未重新与 wheel 配对，不可与前一候选混称同一固定候选。

RC4 初始误报的已证实原因：官方 RC4 wheel 的 `probe all` 忽略 `--expected-version`，即使 RC5 客户端正确传参，旧后端仍按 RC4 自身版本判断 ready；RC4 的单模块 installation probe 支持该参数。直接在 UI 补第二套版本判断会破坏 Python 权威与 aggregate/maintenance 同源约束，尚未实施此类绕过；应在保留单一权威与投影一致性的前提下修复升级检测并对同一新候选重新验收。

本轮未提交修复与证据边界：官方 RC4 的 aggregate 忽略预期版本；插件改为调用既有 Python 单模块 versioned probe，不自行比较版本。隔离 Obsidian 对 RC4 fixture 已观察到 `installation.version_mismatch`，刷新后仍为 `action_required`；尚未用最终配对候选完成两次完整首装和升级旅程。安装发布成功后路径读取失败现单独提示，不再声称安装失败；该路径为定向测试，尚无实机故障注入证据。

OCR 付费安全：真实 loopback 在收到 POST 后断开响应的源码实验，修复前收到 2 次 POST；修复后首次及再次运行均保持 1 次 POST，持久化 `submitting`，无 job id 时禁止自动重传。已有远程 job 的超时不再清除身份或重新上传；provider 结果获取失败（含 404）保留原 job，提示检查 provider。受控 429 的源码 CLI 实验为单次 POST、返回 quota 提示并包含论文 key。以上不是实际云端失败；用户可操作的未知提交结果人工恢复路径及真实 429/长超时仍待验收，不得以成功案例代替。

未知提交恢复决策边界（只读核查）：上传响应丢失且无 job ID 时，`ocr status` 只能显示未知，`ocr resume` 有意排除此记录；现有 UI 未提供人工对账或重新绑定任务入口。不能因用户已检查 provider 就推断可以安全重传。方案：保持阻断，或由 Owner 批准新增具备人工确认及可靠论文—远端任务关联的恢复契约；推荐继续禁止自动重传并先明确 provider 可提供的关联证据。新增公开操作或持久化关联触及本 Goal 的 Owner 决策边界。

Owner 决定：不需要自动重试或新增恢复 API；明确提示操作者下一步即可。保留未知态和禁止自动重传，提示按论文与提交时间检查服务商任务列表（如有），再联系 PaperForge 支持对账；没有匹配不证明上传失败，不要重传或删除本地记录。隔离 Obsidian 1.14.5 使用新配对 wheel `874f48624a448847f74059ac3690d9514d24aff41c331cb36b0dad891465981a`、bundle `d45c9679360dc344633df8fd20e280e9dfa644bdcbeb0ff499794b0ee664b2c3` 与合成凭据，实际选中未知态论文后 UI 显示上述中文步骤、不出现相反的重跑建议，提交标记保留；fixture 安装不是 managed-install 验收。该提示不意味着未知任务已自动恢复。

同一新配对候选的真实宿主断连续验：loopback 收到合成 PDF 的 POST 后直接断开，UI 显示中文对账指引，状态保留 `submitting` 且无 job ID；同一 UI 再次操作和完整关闭重启后再操作，服务端 POST 累计均为 1。仅证明受控断连与重启场景，不代表长时间无响应、真实云或完整用户旅程通过；隔离宿主退出，loopback 与临时 keyring 已关闭。

继承凭据的有限启动检查：同一新配对候选在隔离 Obsidian 中继承合成 OCR/Embedding 环境凭据，未点击远程操作，观察 20 秒；受控 OCR loopback 端点收到 0 GET、0 POST。仅覆盖这段启动窗口和 OCR 端点；未对 Embedding/其他网络目的地做全局监控，不证明完整 Preview 无任何未授权联网。

随后在同一隔离候选分别将 OCR 和 Embedding 的配置端点指向受控 loopback，继承合成凭据后重启真实宿主且不点击远程操作；20 秒内两个端点共计 0 GET、0 POST。仅覆盖启动窗口与这两个配置端点，不能替代全部 Preview 旅程或全局网络审计；无真实凭据及真实 provider。

配对候选补充故障证明：使用隔离 fixture 安装该 wheel（非 managed-install 验收），同一 bundle 在 Obsidian 1.14.5 对合成 PDF 分别发起受控 loopback 401 和 429：各 1 次 POST，真实 UI 对 401 显示已阻塞及凭据/源文件指引，对 429 显示失败及 quota 指引，均显示论文 key。候选 CLI 的 provider-result 404 在首次和再次运行后均只累计 1 次 POST，保留 job id、显示结果不可获取并要求检查 provider。均非真实云失败；宿主已退出、临时测试 keyring 和 loopback 已清理。

本次最终源码门禁：Python 316 passed、1 skipped；插件 209 passed，typecheck/build 通过；一次复审无 P0–P2，较宽 OCR state-machine 测试曾有 3 个测试失败，未纳入该定向门禁，不得当成全套通过。隔离候选 wheel SHA256 `1345adffc677a25cf7a83bc90ea8642e338f48e83c1ea05f161feac07af22e8b`，bundle SHA256 `a0383fddb55d4c3e74927e879d15821ef12784191688ecf21481d56c59202684`；235 个 Python 文件及 wheel 中 bundle 与隔离源码快照逐字节一致。快照是 `795792ce` 加未提交 overlay，**不是最终 Git source SHA**；该新配对候选未完成真实 UI/双旅程、CI/H、RC4 升级及发布验收，不得标记 Preview 通过。上面的历史失败与各代不同候选证据继续保留。

隔离 overlay 的本机 Python 全量尝试未通过：3553 passed、292 skipped、30 failed；并非 hosted CI。失败日志保留；修正测试解释器 PATH、启用 Python UTF-8 并在隔离测试 venv 用 ensurepip 补齐 pip 后，相关失败区域复验为 151 passed、1 failed。剩余 `test_partial_resume` 中 sync/index 为 6 篇，但 memory build 的 body units 为 0；源码 `memory/builder.py` 使用固定 `vault/System/PaperForge/ocr`，该测试将 OCR 置于已配置的 `99_System`。这是待修复或进一步确认的配置路径不一致，未证明 resume 通过，也未重新运行整个门禁。

后续源码修复：memory builder 通过 `paperforge_paths(vault)["ocr"]` 使用配置目录；resume 夹具子进程改用 `sys.executable` 并检查退出码，保留原有断言。隔离 vault 的真实 CLI sync / memory build 对 `99_System` 观察到 6 篇、18 个 body units；resume、embedding resume 与 scoped memory 测试合计 21 passed。此修复尚未进入上述候选 wheel，也未重跑全量门禁或完成最终旅程。

修复后隔离全量 Python 尝试：3626 passed、293 skipped、3 failed、4 errors；非 hosted CI。三项失败为隔离快照缺少 TypeScript 模块，四项 error 为禁止自动加载插件时未显式加载 mock/snapshot fixture。明确配置现有 TypeScript 的 `NODE_PATH` 并显式加载两个 pytest 插件后，相关文件定向复验 38 passed、2 skipped；不能将定向复验拼成全量通过。原日志均保留，完整同环境全量与 hosted CI/H 仍未验收。

修正隔离环境后对同一源码 overlay 重新执行 Python `tests`：3633 passed、293 skipped，出口 0；允许 loopback、禁止其他 socket，显式加载 timeout/mock/snapshot 插件并使用现有 TypeScript。此结果不包括 hosted CI、H matrix 或真实 provider，跳过项不算验收通过；旧失败记录不删除。

当前工作树插件全量 Vitest：653 passed、1 skipped；typecheck 通过。跳过项为真实安装进程强杀用例，不能算安装恢复通过；本机测试结果不替代最终候选的真实 UI 双旅程或 hosted CI。

OCR state-machine 续验：原三处失败测试将纯文本写成 `.pdf`；locator 修复使真实 PDF 渲染使用该文件后暴露夹具无效。仅将三处夹具改为 PyMuPDF 生成的有效 PDF，未改断言；`tests/test_ocr_state_machine.py` 与 `tests/cli/test_ocr_scope_safety.py` 合计 51 passed。此前“base worktree 21 passed”的试跑从另一工作目录执行，未证明实际导入 base 实现，不作为基线结论。此为源码定向证据，不提升先前候选的验收等级。

## 模块责任表

路径均相对于仓库根目录。表中的诊断命令前加 `python -m paperforge --vault <隔离 Vault>`，不是让用户在生产库执行写操作。

| 模块 | 唯一事实来源与执行入口 | 诊断入口 | 本轮证据及缺口 |
|---|---|---|---|
| 安装/运行时 | `runtime_pointer.py`、`setup/plan.py`；插件 `services/managed-runtime.ts` 的 Candidate → Probe → Python 发布 pointer | `probe installation --json`、`doctor --json` | 真实 UI 已验证：官方 RC5 前后端配对在空 HOME 首次安装就绪；从官方 RC4 旧运行时升级到修复候选，取消保留旧指针/可运行环境，重试成功后才发布新指针并退役旧环境。修复候选 237 个 Python 文件与目标 wheel 一致，PyMuPDF 1.28.2、vector extras、pip check 通过；官方 RC5 的 PyMuPDF 2.0 无上限风险保留。安装阶段 frontend 为 fa650fdf，后续 Scope bundle 独立实机绑定；实验运行时已退役，指针仅为历史证据 |
| 配置/凭据 | `config.py` 的 canonical config；`commands/auth.py` 与凭据存储 | `config list --json`、`config validate --json` | 实际初始化合成 Vault。只用 Null keyring；未读写生产凭据 |
| Zotero/同步/Base | `services/sync_service.py`、`commands/sync.py`；正式索引经 `worker/asset_index.py` 读取 | `probe library --json`、`status --json` | 本轮证据：空库显示 Zotero 未配置；插件真实进程协议测试使用合成导出同步。历史 #352/#354 曾有真实库验收（不在本轮重验），本轮未重验≠否认旧证据 |
| OCR 范围/任务 | `actions/registry.py` 与 `actions/runner.py` 执行策略；`commands/ocr.py` legacy CLI；`worker/ocr.py` 最终作业与上传 | `probe ocr --json`、`ocr list --json` | 远端冻结。范围、取消的离线回归与真实服务终态/内容质量是两类证据，不混用 |
| OCR 结构/渲染 | `worker/ocr_document.py`、`ocr_figures.py`、`ocr_tables.py`、`ocr_render.py`；`render_audit.py` | `render audit KEY --json` | 审计会写 `render.consistency.json`，只能在副本运行；本轮未重跑真实 PDF 视觉质量验收 |
| Memory/元数据搜索 | `memory/builder.py`、`schema.py`、`query.py`；SQLite 是派生投影 | `memory status --json`、`search QUERY --json`、`runtime-health --json` | 空库搜索返回 `PATH_NOT_FOUND`，不是空结果。2026-10-26 真实隔离 UI 闭环：M 搜索 `Biomechanical` → `missing-memory-index` 卡 → CTA 进 Memory 详情 → `memory.build`（all）本地完成（`paperforge.db`，papers=1，`zotero_key=TSTONE001` 合成）→ 同查询命中 1 结果 → 重启仍命中。证据隔离留存 `ui-smoke-2026-10-26` 收据/DOM/截图（TRIAL_ROOT 下，未入库）。构建后 probe 为 `memory.index_stale`（vector 未建），未调用 embedding/远端。独立环境 `[vector]` 前置依赖说明保留（远端冻结，属历史行） |
| Embedding/语义检索 | `embedding/*`、`retrieval/gateway.py` | `embed status --json`、`runtime-health --json` | 没有调用提供商；未验证召回质量、付费范围及真实模型兼容性 |
| 阅读/研究记录 | `memory/permanent.py` 中 JSONL 是 authority；`commands/reading_log.py`；插件 `views/research-record.ts` | `reading-log --search QUERY --json`、paper-context | 本轮真实隔离 UI：保存→非标题关键词命中具体记录→打开→追加纠正→默认排除旧引文→历史开关找回→重启持久，JSONL 与 correction 关系读回一致；另完成真实授权 PDF 引文的 exact_text 匹配与来源跳转。历史 #352/#354 真实库证据保留，不把本轮隔离库验收替代正式发布验收 |
| 来源/页面定位 | 既有 reading-record source 校验与插件打开来源入口 | 记录 source check、原有来源测试 | 2026-10-26 真实授权 PDF 验收 PARTIAL PASS：隔离留存 `source-acceptance` 收据（真实授权副本的 PDF 字节/引文原文/BBT 路径均未入库）。状态机 matched（全 PDF 唯一命中，物理页 1/印刷页 248）→ 变异 SHA `0a7c7c4c…` 后 status=changed/`VALIDATION_ERROR` → 恢复原 SHA `467c800e…`（9 页）后 matched。错页 mismatch、user_confirmed/recorded 分支未验 |
| 版本/回收/恢复 | `commands/versions.py`、`worker/trash.py`；删除通过 move+manifest | `versions list --json`、相关回归测试 | 历史 CLI 已验证 versions/trash 字节保留；本轮论文面板真实版本历史 Modal 验证正文恢复但 provenance 未保存的持久提示、当前版本标记和正常恢复关闭/读回。直接 timeline 恢复及其他 Modal 适配器属 UNIT/源码覆盖，不冒充逐入口实机通过；失败元数据未被自动修复 |
| Agent/技能 | `commands/agent_context.py`、部署入口与包内 skills | `probe help --json`、`agent-context --json` | 隔离副本实测 `agent-context`、skill deploy、重复 deploy 的 noop 保护、`pf_bootstrap.py --vault`；未改用户技能。无本地模型，远端仍冻结，模型驱动的实际研究任务 BLOCKED，不把部署或帮助成功当模型任务通过 |
| 控制面/运维 | `reconcile.py` 是 next_actions 生产者；Registry 是动作策略 authority；maintenance 仅投影 | `probe all --json`、`reconcile --scope all --json`、`action list --json` | 实际拿到六个模块信封和九个动作；maintenance=ready 只表示没有维护项不表示所有模块可用。2026-10-26 runtime-health已修（vector层显式enabled事实，仅vector返回值加字段、_layer原API不变；disabled→safe_vector/vector_retrieve=false，层状态仍ok；见CHANGELOG与红/绿CLI收据） |
| 插件/传输 | `client/node-transport.ts` 唯一进程 authority，`client/paperforge-client.ts` 唯一业务 client | client/transport/protocol-conformance 本地验证 | 本轮修复 result-mode 拒绝原因丢失和假成功；真实 Obsidian 故障演练的诊断复制/搜索错误显示已覆盖（缺索引卡 CTA 进详情零 runAction、genuine 失败脱敏单条 Console）。旧自由文本 console 调用点已在本轮续作 diff 中移除，当前 src 原始 `console.*` 只剩 `trace.ts` 两处（见下“日志隐私限制”），不再列为未修。本轮记录流实测：每次 genuine 失败恰好一条 Console 行（rr-step5 空页保存 1 行 → rr-step6 成功保存零新增 → rr-step10 来源核验失败第 2 行；无单操作双行，单终态规则成立） |
| 架构/发布 | `architecture_audit/collectors` 确定性观察；Contract lifecycle 决定架构接受；CI/owner 决定发布 | `scripts/ci_local.py --list`、既有 collect/gate、`scripts/release_readiness.py` | 不提升 lifecycle 或 release 状态。原 new-on/new-off 的产物身份不一致记录仍为历史 INCONCLUSIVE；新归档重建的 new-on-rebuild/new-off-rebuild 各一次通过，实际 served hash 与新构建回执一致，旧证据冻结不变。短 A/B 身份缺口已闭合，不代表 full H/A01 根因已解决。官方首次安装与修复候选升级已实测，不为旧 RC5 自身的原地升级失败安全性背书 |

## 接口统一规则（沿用现有实现）

| 问题类型 | 权威接口 | 消费规则 |
|---|---|---|
| 同步命令结果 | `core/result.py::PFResult` | 保留 `ok/command/version/data/error/warnings/next_actions`。`error.code/message/details` 不得被通用 exit code 吞掉；进程失败与 payload 自报成功矛盾时失败优先 |
| 模块可用性 | `commands/probe.py` 的 schema v2 | 读 `reason.code/text`、`action.primary`、`user_state`、`capability_kind`。未配置、未启用、检测失败、空数据不同；不把 maintenance.ready 当全局成功 |
| 动作与范围 | `actions/types.py` + Registry + runner | UI 传 ActionRequest，`buildActionArgv()` 组装参数；后端验证 scope、preflight、确认，再执行。不要由新 UI 推导 all 或重新维护动作策略表 |
| 长任务 | `core/ndjson.py` + `NdjsonStreamParser` | 非终态事件后恰好一个 `result/error/cancelled`，随后 EOF；无 terminal 是协议失败。取消本地提交不等于取消云端作业 |
| 前端访问 | `PaperForgeClient` → `Transport` | View 不直接 spawn、不解析运行时 pointer；复用缓存失效、operation lock 和诊断字段。命令特定的裸数组/authority JSON 仍由具名 client 方法适配，不强制破坏全部旧接口 |

原 `BACKEND-FRONTEND-CONTRACT-MAPPING.md` 是设计蓝图，其示例不是逐字段的现行 schema；运行时代码和协议测试优先。例如实际 Probe 是 `reason: {code,text}` 与 `action: {primary: ...}`，不是蓝图示例中的扁平 `reason_code/action_primary`。

### 早期修复：result-mode 动作契约

`PaperForgeClient.runAction()` 的 result 分支此前：

- rc 非零时丢弃结构化 stdout，`payload=null`；
- rc=0 时即使 `ok:false` 或非 JSON 也返回成功。

现在保留后端原始 PFResult 拒绝，原 `error.code/message/details` 可被现有消费者读取；非 JSON/缺少 boolean `ok` 为 `protocol_error`；非零 rc 却自报成功为 `transport_error`。执行过的命令保留真实 exit code，`ok:false` 不伪装成进程 rc=1。不可用/busy 的早退也提供结构化 error，不分发执行。没有新增原始 stdout/stderr 导出或遥测；transport 的现有 Error.message 可能带 stderr，不能保证它不含私密内容，外发诊断仍需脱敏。保持 `buildActionArgv`、stream 路径、缓存失效和返回 DTO 不变。没有把所有 worker 异常随意映射为 scope 错误。

模块回归同时暴露一个真实的跨模块别名耦合：`worker/ocr.py` 从 `worker.sync` 二次导入 `load_export_rows`。Sync 单测在临时替换 loader 时触发首次 OCR 导入，OCR 会永久保留该临时对象；随后单篇范围检查把真实存在的 key 报成 unknown，7 个 HTTP 范围/取消用例和2个流用例失败。独立新进程复现已证明这条捕获链，不是 PDF 或索引数据格式问题。修复为直接引用既有 `adapters.bbt.load_export_rows`，保留原调用 seam 和范围检查，未改成 all，也未弱化断言。原 9 failed / 739 passed / 3 skipped 的证据保留，最终重跑同一组用例。

## 开发时的最短定位路径

1. **先固定身份**：记录源码 SHA、工作树、`sys.executable`、`paperforge.__file__`、版本与安装来源。禁止借用指向别的 checkout 的 editable venv。本轮安装包的 237 个 Python 文件与候选逐个 SHA-256 比对一致。
2. **看模块状态**：一次 `probe all --json`；再按上表选具体模块。不要重复扫描整个项目。
3. **看动作拒绝**：保留 action id、scope、keys 数量、exit code 与 `error.code/message/details`。若没有终态，先查 transport 的 `protocolFailure`、stderr 尾和 last event，不先改业务 worker。
4. **跑该模块回归**：按下面选择文件；有跨层变更才加真实 Python/client 协议验证。不要把一次失败变成长时间全套 CI 轮询。
5. **修复后做本地最终门**：受影响 Python 回归 + 插件测试/typecheck/build + 一次实际 CLI 或 UI 路径。CI 留作集成/发布证据，不作为本地开发等待环。

### 可复用的本地入口

在隔离工作树运行，准备独立 venv（不加 `--system-site-packages`）：

```powershell
py -3.12 -m venv <venv>
<venv>/Scripts/python.exe -m pip install ".[test,vector]"
<venv>/Scripts/python.exe -c "import sys,paperforge; print(sys.executable, paperforge.__file__, paperforge.__version__)"
<venv>/Scripts/python.exe scripts/ci_local.py --list --json
<venv>/Scripts/python.exe -m paperforge --vault <test-vault> probe all --json
```

`ci_local.py` 从现有 workflow 推导命令，不是启动 GitHub Actions；不要不加筛选就执行全部 job。它跳过的 conditional/setup 步骤不能记为通过。各模块的快速入口：

| 改动位置 | 最小选择 |
|---|---|
| 配置/探测 | `pytest tests/test_config.py tests/test_probe.py tests/test_probe_all_lineage_reuse.py -q` |
| 动作/控制面 | `pytest tests/test_action_registry.py tests/test_reconcile.py tests/test_architecture_boundaries.py -q` |
| 同步/笔记/Base | `pytest tests/test_sync.py tests/test_sync_next_actions.py tests/test_base_preservation.py -q` |
| OCR 范围/取消/流 | `pytest tests/cli/test_ocr_scope_safety.py tests/cli/test_ocr_progress_contracts.py tests/test_ocr_stream_stdout.py tests/test_ocr_redo.py tests/test_ocr_rebuild.py -q` |
| 记录/Memory | `pytest tests/cli/test_research_records.py tests/unit/memory tests/test_local_read.py -q` |
| 渲染/版本/回收 | `pytest tests/test_render_wire.py tests/test_render_audit.py tests/test_versions_command.py tests/test_no_raw_delete.py -q` |
| 插件/client 边界 | `npx vitest run tests/client/paperforge-client.test.ts tests/client/protocol-conformance.test.ts`，设置 `PF_PYTHON` 为上述 venv；随后 `npm run typecheck`、`npm run build` |

使用同一个解释器的 `-m pytest`，不要依赖 PATH 上另一个 pytest。`tests/sandbox/00_TestVault` 与 `PF_EVIDENCE_DIR/index.json` 是共享写入点，相关测试串行运行，不用 `-n auto`。不同 checkout/不同临时 Vault 的独立工作可以并行。

离线 OCR 回归必须拦截最终 multipart 上传，并在 Python 进程和子进程中禁止实际 socket connect；清空继承的凭据环境、使用 Null keyring，确保故障测试不会意外读取生产凭据。`probe ocr` 也可能探测远端，不要在带生产凭据的环境把所有诊断当纯本地命令。安装依赖的包下载不属于运行产品的收费服务请求。

## 已观察但本轮不混修的接口缺口

| 优先级 | 事实/证据 | 下一次最小修复和验证 |
|---|---|---|
| P1（本轮范围） | 本轮续作 diff 移除了 client 拥有终态的 View 重复与调试噪音（`configSet` 回写、`_runLibrarySync` 后刷新、`dashboardStats` typed 结果、`checkOrphanState` 调用/found/not-found/exception、`savePaperforgeJson` warn、dashboard render/version/sync Notice 拼 message、modals 孤儿 `console.log`、settings 安装失败 Error 对象）；当前 src `grep console\.` 仅命中 `trace.ts` 两处。历史段落曾列三处为未修是过期投影，本行以当前 worktree 只读核实为准 | 本轮内已做，无需再修；仍不能因公共路径收敛就宣称全应用日志已脱敏（约束仍在：`console.debug` 需 `debug_trace` 开关） |
| P2 | `core/next_actions.py` 保留旧验证表；实际生产已由 `actions.registry` 发射/执行，旧 helper 只被旧测试引用 | 先查全部引用，再删除死 helper/测试；不要添加第三份 registry，也不要仅加“legacy”注释保留双权威 |
| P2 | legacy OCR 取消结果与 Action runner 的 error.code 表达不同 | 复用现有取消结果语义，保留 operation 字符串；验证原有流消费者，不做全局改名 |
| P1（已闭环，不再是缺口） | 缺 Memory DB 的元数据搜索已由 `#356` 续作细分为 `missing-memory-index` 卡（中英说明 + 阅读笔记可用 + 不调用 Embedding/收费 + `打开记忆设置` CTA 经 `openModuleSettings("memory")` 进入真实 Memory 详情，零 runAction、不自动 build）；2026-10-26 真实隔离 UI 已验证恢复→`memory.build`→命中→重启持久。深度 retrieve 的同码仍走 `backend-unavailable`，两者不混淆 | 保留，无需再修；误判为缺向量的表述已在卡片与测试中排除 |
| P2（已修已验证） | runtime-health 曾把用户关闭的 vector 投影为 safe_vector/vector_retrieve=true；现仅 vector 层增加显式 enabled 事实，关闭不代表故障，也不代表可检索 | 保留总体状态及真实检索权威；disabled→false、enabled-unready→degraded/false、enabled-ready→true。最终影响集 64 passed/2 skipped；正常非 editable 候选 CLI 绿证据为 `runtime-health-newcand-green-pinned.json`，依赖检查 `uv-pip-check-newcand-pinned.txt`。`runtime-health-candidate-green.json` 是早期诊断回执，不作为最终候选证明 |

这是一条按模块补齐契约的维护队列，不是本轮已全部完成的修复清单。暂不追加 RAG、Daemon、Rust 重写或 UI 大改。

## 上一阶段本地验证回执（aa2e44a9）

历史隔离 receipts（`TRIAL_ROOT/module-interface-356/` 下：python-source-identity、smoke-summary、逐检查 stdout/stderr、JUnit 与摘要；未入库）。首次5个动作负例全部失败；集中修复后，最终本地结果如下。所有远端能力保持冻结；没有新的正式 H 矩阵、Release 安装或收费服务质量证明。

| 本轮检查 | 最终结果 | 能证明/不能证明 |
|---|---|---|
| Python 模块回归（同一选集、串行、禁止 socket） | **748 passed / 3 skipped**，164.66 秒 | 包括 CLI、probe/config、scope/取消、同步、Memory、渲染/版本等选定边界；不是全 Python suite 或全用户旅程通过。此前9个失败同组选集已消失，断言未改 |
| 插件全部 Vitest | **581 passed / 1 skipped**，32 文件通过、1 文件跳过 | 含真实 Python 进程协议11项；不替代 Obsidian Electron 实机 |
| 插件 typecheck / build | **通过 / 通过** | 构建成功；不安装进用户 Vault，生成的 main.js 不作为本次源码提交变更 |
| 实际 CLI 与六模块 probe | **已执行并读回** | doctor 在未完成安装/无数据的合成库 rc=1，元数据 search 缺 DB 返回 PATH_NOT_FOUND，均保留原始报告，不篡改为全部 ready |
| BBT loader 捕获复现 | **红 rc=1 → 绿 rc=0** | 同一临时 Sync override 结束后，已安装候选能读取真实合成 export 的 MODULE356 |
| 网络保护检查 | **通过** | 连接函数在发起 socket I/O 前抛 OFFLINE_356；Python 子进程继承保护与 Null keyring |
| 两轴审核与一次集中修复 | **无重要剩余发现** | 修复保留真实 exit code、统一不可用/busy 错误、澄清隐私表述；没有循环加测或通过放宽断言制造绿色 |

原始缺 vector extra 的 collection failure、9-failure gate、初次 probe 和红复现均单独保留，不用后续绿色覆盖历史证据。跳过项不计通过。

候选不包含受保护且未跟踪在该提交中的 `PROJECT-MANAGEMENT.md` / active queue。本轮不复制、不修改主工作树台账；此报告是本次模块盘点的投影，不是任务状态或发布接受的 authority。

## 继续阶段：本地诊断与受控实机烟测（2026-10-24）

本阶段以 `aa2e44a9` 为基线，实施和本地验证均已完成；以下回执独立于上一阶段，旧日志不覆盖。它不是整款软件、全宿主矩阵或正式发布验收。

### 本轮代码变动

| 方向 | 变动 | 决策/测试缝 |
|---|---|---|
| Doctor 解释器权威 | 删除 `_read_plugin_data` + `_resolve_plugin_interpreter` 死 bootstrap 副本；正式插件执行目标只读 `runtime_pointer.read_pointer()`，绝不 fallback py/python/python3、config python_path 或 ambient Python。检查顺序对齐 probe 现有权威：pointer missing → version stale → executable missing（无新 readiness 规则）。缺失/陈旧/缺文件 pointer 明确报告未准备并指向 `paperforge setup` / `update` / `repair --runtime`，跳过一切目标环境子进程探测；当前诊断进程身份是独立事实（3.11 地板与 probe 一致）。有效 pointer 复用 `_query_resolved_*` + `run_readonly_probe`（extra_args=[]），不再拼原地/global pip。`_query_resolved_package` 用目标解释器 `importlib.metadata.distribution` 读 Name/Version/Location（uv 无 pip 也可诊断；PackageNotFound→None）。正常 Vault/配置/OCR 检查仍运行，不读写生产 pointer | `tests/test_doctor.py` 新增：缺失 pointer（文本+JSON）报 setup 且零目标探测；有效 pointer 只查 pointer 路径；陈旧 pointer 用真实存在可执行文件隔离条件、零目标探测、明确 fail+可执行修复建议；无 pip 也能读 dist 版本（`_query_resolved_package` 回归）与缺失 dist→None。调用方迁移：`run_doctor` 唯一调用点已改；无外部引用（已 grep）。Worker `pip install -e .` 与 skill `pip install -e .` 文案改为 `repair --runtime` / 确认配置 |
| Maintenance 文案 | `probe.py:1617` + `i18n.ts` en/zh 只改“无维护项”的准确措辞，不改 eligibility/readiness。不新增文案字符串测试（既有 eligibility/状态语义测试保留；review 要求改变聚合策略已拒绝） | runtime-health vector disabled 不扩 enabled DTO：本轮明确记为未修 |
| Console 错误 | 在 trace/client 公共边界统一一次安全 `console.error`，复用 trace ring/record，不另建 logger 或新页面。覆盖：typed JSON 拒绝（pfresult：完成态 doctor 诊断报告除外；search+PATH_NOT_FOUND 空库预期态除外）、协议失败（protocol_contradiction/protocol_error，矛盾只最外终态记一次且保持 protocol code）、进程失败（transport runAction catch；NO_PYTHON 预期 setup 态保留 machine code 但抑制 Console）、runAction 结果失败、stream 终态失败（`streamOperation` wrapped outcome 单点，含 outcome-reject 异常路径；runAction stream 分支不再重复）。无跨操作全局 dedupe：同错两次独立尝试各记一次；单操作内靠终态归属（pfresult/process/stream 单点）不双报。`_executePfResult` 恢复 bare-JSON 兼容（`action preflight` 裸 descriptor rc0 即成功载荷；PFResult 识别 `ok` 即判，`ok:false` 即使无 `data` 也保留 code/data）。`commandIdentity` 按首命令 family 匹配固定 subcommand（search/retrieve/reading-log 永不带第二参数；query=`run`/`status`/`list` 反例锁定）；绝不输出用户值或 flags。Console 退出码取自 transportError.exitCode（rc0 业务拒绝 exit=0）。Console 只固定字段 op/stage/machine code/exitCode；`_executeRaw` 层不散打日志。预期缺配置/未启用/用户取消（cancelled、action.busy/unavailable、credential 缺失、*.disabled/*.not_enabled、NO_PYTHON）在默认 Console 下不报错；调试仍走 `debug_trace` 开关。legacy 散落自由文本 console（settings/dashboard/modals）不在本轮迁移，报告明确，不称全局已脱敏 | `trace.test.ts` 新增 traceConsoleError 组：单次+redaction+预期态抑制+两次独立同错==2、rc非零+PFResult拒绝单操作==1（exit=1）/rc0==exit=0+矛盾单次 protocol code+stream reject 单次+空库 search 零 Console 且 trace 保留 code+NO_PYTHON 抑制+commandIdentity 私密值断言（search/retrieve/reading-log query、config value、action keys、run/status/list query 反例）+dashboard 状态映射。未覆盖边界（legacy raw 方法）：`sync()`、`probe()`、`reconcile()`、`paperStatus()`、`queryOcrPapers()` 等仍走 `_executeRaw`+JSON.parse 的只读/旧路径，未接入统一 Console 输出——不在本轮私改契约，列为剩余边界 |

### 日志隐私限制

统一 Console 输出只含固定字段；当前 worktree `paperforge/plugin/src` 内原始 `console.*` 只剩 `client/trace.ts` 两处（`traceConsoleError` 的 `console.error` 与 `debug_trace` 开关门控的 `console.debug`），旧自由文本调用点（settings 安装失败含 Error 对象、`configSet` 回写、`_runLibrarySync` 后刷新、`dashboardStats` typed 结果、`checkOrphanState` 调试噪音、退休 `savePaperforgeJson` warn、dashboard render/version/sync Notice 拼 message、modals 孤儿 `console.log`）已在本轮续作 diff 中移除（`git diff` 仅见 `-` 删除行，`grep console\.` 全 src 仅命中 trace.ts）。默认 Console 可见的是真正失败（traceConsoleError），预期态被抑制。

### 本轮本地验证命令（父侧已实际执行，外部 runner 未随 repo 提交）

外部 runner 实际执行（`TRIAL_ROOT` 为本机隔离根，占位符；命令未随 repo 提交，仅形态记录）：

```powershell
# 1. 非 editable 重装候选 + 237 文件验证 + 同组 Python 回归（含新增 doctor/status/runtime-health 组）
python <TRIAL_ROOT>/module-interface-356-continuation/continuation-verify.py python
# 2. 全 Vitest + typecheck + build（含新增 trace/client 卡片/Console 组）
python <TRIAL_ROOT>/module-interface-356-continuation/continuation-verify.py plugin
# 3. 实际 CLI 烟雾（6 模块 probe + doctor + status + runtime-health + action/search/reconcile）
python <TRIAL_ROOT>/module-interface-356-continuation/continuation-verify.py smoke
```

外部脚本复用原 `module-interface-356/verify.py` 的 ENV 清洗/socket 守卫/原 venv 路径（`<candidate-venv>/Scripts/python.exe`）；OUT 改独立 `module-interface-356-continuation/` 目录；offline 守卫仍原 `module-interface-356/offline`；manifest 区分 `base_sha=aa2e44a9…` 与 working-tree 文件 hash，不把 dirty 候选标成 HEAD。旧 `aa2e44a9` 证据目录不可覆盖。

### 本阶段实际结果与证据范围

- Python 选定模块串行回归：**769 passed / 3 skipped**，173.08 秒。新增的无 pip 回归使用真正 `venv(with_pip=False)` 和目标解释器中的 distribution metadata，不再用返回值 mock 冒充该边界证明。
- 实际 CLI：doctor 现在只检查 pointer 目标 Python 3.12.8，PaperForge distribution 和依赖均通过；合成空库的 doctor 总 verdict 仍为 FAIL，因为未连接 Zotero/导出/凭据。未把这些缺配置项洗成绿色。
- Maintenance 的空 inbox 保持原有 eligibility/ready 语义，文案只说“无维护项”，不推导全局就绪。
- 搜索保留 error.code/data；typed JSON 兼容原有裸 preflight。真正失败的 Console 固定输出 operation/stage/code/exit，不输出查询、错误 message、raw stdout/stderr 或 Error 对象。同一请求只记一次；相同失败重试仍各记录一次。缺 Memory DB、未发布 runtime、向量 not_built/stale、取消等已定义预期状态不打红色错误，仍保留可分类的 trace/界面状态。
- 受控真实 UI：新建 `module-interface-356-continuation/ui-vault`，独立 HOME/APPDATA/profile；实测 **Obsidian 1.14.5 / Electron 37.6.0 / Chromium 138.0.7204.251**，插件版本 2.0.0rc5。通过真实输入框/Enter 触发，验证向量未建、缺 Memory DB、INTERNAL_ERROR、空结果与重复失败；截图显示约 300px 侧栏中的对应卡片和恢复按钮。
- UI 使用明确注入的离线 transport 故障，不是真实提供商或原 166 篇库验收。Python CLI 另行真实执行；两类证据不混称端到端服务质量。页面离线、子进程 socket 守卫、Null keyring，未触发收费能力。
- 观察到既有 `@ `（带空格）输入的徽标仍显示 M，但请求走 retrieve；已记录为显示一致性后续项，未顺手扩修。缺 Memory DB 卡片仍泛化，亦如上表保留，不宣称全部 UX 闭环。

本阶段 raw/manifest/截图回执隔离留存于 `TRIAL_ROOT/module-interface-356-continuation/`（未入库）。旧的 6 个插件失败、doctor 无 pip 误诊与无效测试条件保留在 before-repair/after-agent-repair 文件中。最后的插件数字、构建、Console 与 UI 重测结果以该目录收口回执和 Issue #356 最新评论为准；跳过项不计通过。

### 收口状态

| 验证 | 实际结果 |
|---|---|
| Python 选定模块回归 | 769 passed / 3 skipped |
| 插件完整 Vitest | 595 passed / 1 skipped；32 文件通过、1 文件跳过 |
| Typecheck / Build | 均通过 |
| 受控构建的真实 Obsidian 故障演练 | 向量 not_built → 对应恢复卡片且无红日志；缺 Memory DB → 非向量卡片且无红日志；INTERNAL_ERROR → 每次 Enter 一条脱敏 Console；两次相同失败保留两条；空结果 → empty 且无红日志 |

受控实机证据绑定在 `ui-plugin-assets.json`（部署 bundle 哈希）、`ui-host-artifact-provenance.json`（宿主/应用资产哈希）、`candidate-source-manifest.json`（被测工作树源码哈希）以及三张 `ui-*.webp` 截图。宿主会话已停止，仅保留独立测试 Vault/证据；未覆盖原试用库或生产设置。实现状态为**本地候选已验证**，不是全应用接口已统一、正式宿主矩阵已通过或可发布。

实机结束后补齐了“进程未给出退出码时显示 `exit=?`，不能伪装成 `exit=0`”的元数据回归；卡片映射与实机所测 rc=1 路径未改变。实机源码快照另存 `ui-tested-source-manifest.json`，最终本地候选记录在 `candidate-source-manifest.json`，不把两份构建身份混写。

## 本轮实现：缺 Memory 恢复与 Console 归属（已验证，证据见 recovery 目录）

本轮基线 `16427446f252bb621eae2a395eb6c90315946677`。上一阶段的 769/595 未冒充为本轮证明。
本轮 gates 由隔离 `TRIAL_ROOT/module-interface-356-recovery/verify.py`（plugin 模式）实际执行，
证据隔离留存于 `TRIAL_ROOT/module-interface-356-recovery/`（均未入库）：`plugin-summary.json` +
`plugin-regression.stdout/stderr.txt`、`plugin-typecheck.stdout/stderr.txt`、`plugin-build.stdout/stderr.txt`。
真实 Obsidian 离线 smoke 证据同目录：`ui-smoke-2026-10-25.json`（另有既有 `smoke-summary.json` 为 CLI 历史证据，不重跑）。

### 搜索卡片分野

- 仅元数据搜索（`search`，非 `@`/retrieve）+ `PATH_NOT_FOUND` 映射到新状态 `missing-memory-index`；深度 retrieve 的同码仍走 `backend-unavailable`，不与其混淆。
- 新卡中英说明：元数据搜索需要本地 Memory 索引；阅读笔记仍可用；此步骤不调用 Embedding/收费服务。不宣称“元数据搜索不受影响”。
- 新卡与向量设置 CTA 均经 `PaperForgePlugin.openModuleSettings("memory")` 进入真实 Memory 模块详情（`app.setting.open/openTabById('paperforge')` + settings-tab `_handleCardNavigation`），不只打开设置首页，不自动执行 build，不触发 embedding/确认绕过，不新建路由。无有效导航能力时明确提示不可用，不默默无操作。
- `executeSearch` 改用 `trace.ts` 的 `rejectionCode/rejectionData` 读取结构化拒绝的稳定 machine code/data，不把 message 转 code。

### Console 所有权决定

- 复用 `traceConsoleError`；新增 `rejectionCode/rejectionData` 放在现有 `trace.ts`（多调用者 code 提取，非新 logger）。
- 删除 client 已拥有终态的 View 重复：`configSet` 失败回写、`_runLibrarySync` 后刷新、`dashboardStats` typed 结果的 View 重复、`checkOrphanState` called/found/not-found 调试噪音、退休 `savePaperforgeJson` 的 warn。
- 保留单次脱敏诊断（固定 op/stage/code/exit，无路径/Error/message/query/envelope）：`_installFoundation` 非 stream 形态失败（`foundation.setup/install`，stream outcome 形态不双报，取消无红）、`_applyLibraryConfiguration` 本地失败（`library.setup/local`，stream 失败不 outer echo，取消中性）、probe 信封非法（`probe.<mod>/protocol/protocol_error`）、raw probe 失败（`probe.<mod>/process`，`NO_PYTHON` 保持 quiet）、discussion 本地读（`discussion.read/local`）、外部 note 刷新（`note.refresh/local`）、clipboard（`diagnostic.copy/local`）、lineage probe 失败（`probe.lineage/process` + Notice，不让“无孤儿”冒充失败）。
- 正常取消/`NO_PYTHON`/empty 保持 quiet；真正 local/raw 错误可定位。

### 测试缝与验证结果（2026-10-25 实测）

- `plugin-regression`：32 passed + 1 skipped（601 passed / 1 skipped），约 29s。
- `plugin-typecheck`：exit 0，约 3.6s。`plugin-build`：exit 0，约 2.5s。
- `retrieval-knowledge-cutover`：缺 Memory/深度 vector 缺索引/genuine backend/empty 四态分野；
  预期态（缺 Memory 卡、empty）零 Console，genuine 终态各一次固定诊断且不含 query 文本；
  missingMemory/向量 CTA 调用正确导航且零 transport 调用。
- `installation-navigation`：`Plugin.openModuleSettings` 选中 paperforge tab、导航到 memory detail、再打开设置
  （Obsidian 1.14 下 `openTabById→navigate→open` 顺序，方法引用绑定后调用；缺 tab 时返回 false）。
- `trace`：本地失败单次脱敏（clipboard 拒绝写入 stub、lineage 无隐私值）、client 失败（configSet）不被 View 重复；
  bootstrap 失败仍有诊断、取消无红。
- 真实 Obsidian 离线 smoke（`ui-smoke-2026-10-25.json`）：隔离 vault 绝对路径与 HOME 已确认；
  TSTONE001 真实笔记打开，paper 模式；`Biomechanical` 回车后 `missing-memory-index` 新卡 + Console 零新增；
  CTA 经 `openModuleSettings("memory")` 返回 true、零 runAction 调度，进入独立 Settings popout（`设置 - ui-vault`），
  PaperForge tab 选中、memory 模块详情（`智能检索` heading、`Build memory` + `db_missing` + API Key 配置可见）；
  ui-vault 无 memory.db、无新增 db 文件。Memory build 的 UI 闭环未在本次 smoke 内执行（按约束不 embed/远端），
  其能力仅由既有 CLI 历史证据 `smoke-summary.json`（cli-vault：PATH_NOT_FOUND → memory build → 命中 TSTONE001）覆盖，
  与 ui-vault（无 DB）只读核实区分，不假称闭环。
- 仍未证明：含远端/embedding 的 build、收费 API 路径；`_installFoundation` 的 stream outcome 形态判断依赖 outcome
  字段命名（后端形态变化需复核）；probe raw 路径的 exit 统一记 `null`（`exit=?`），不伪造 rc。

### UI 闭环补记（2026-10-26 实测，覆盖上条“未在本次 smoke 内执行”）

复用同一隔离 ui-vault/profile/HOME（未重建环境、未覆盖旧证明；bundle `a33d905e…` 与 worktree 一致）。
真实 UI 顺序：M 搜索 `Biomechanical` → `missing-memory-index` 卡（Console 零新增）→ CTA `openModuleSettings("memory")`
返回 true、零 runAction → 独立 Settings popout 的 Memory 详情（`智能检索`、`Build memory` + `db_missing`）→ 点击
`Build memory` 经确认模态（`Build memory / 影响: 此操作将更改 PaperForge 数据。/ 取消|继续`）→ `继续` 后分发且仅分发
`{action_id:"memory.build", scope:{kind:"all"}}`（hook 实录；`embed.*`/`upgrade_backend` 未分发；新增 Console 错误 0，
CDP 外部 http(s) 资源 0，post-build probe 为 `memory.index_stale` 即 vector 未建）→ 本地 `paperforge.db` 生成
（`papers=1`，`zotero_key=TSTONE001`）→ 同查询 M 模式命中 1 结果 → 打开笔记确认为 TSTONE001 → 仅停止自己的隔离实例后
重启，同一查询仍命中（持久化成立）。收据隔离留存 `TRIAL_ROOT/module-interface-356-recovery/ui-smoke-2026-10-26.json`
（8 张合成截图 + `cdp-step*.json` DOM/action/Console 回执，均未入库；合成库 `zotero_key=TSTONE001`）。用户实例未动；
主 PROJECT-MANAGEMENT 与 queue 未改；既有 601 gates 不重跑（无产品修改）。

### 研究记录 UI 闭环补记（2026-10-26 实测，与 Memory 闭环同库接续）

复用同一隔离 ui-vault/profile/HOME/venv（未重建环境、未覆盖 Memory 证据；bundle `a33d905e…`）。真实 UI 顺序：
TSTONE001 paper 模式 → `[data-pf-testid=save-research-record]` → `ResearchRecordCaptureModal`
（excerpt/usage 必填，pdf 预填 `System/Zotero/storage/<SYNTH_KEY>/<SYNTH_KEY>.pdf`）→ 首次提交 page 为空被后端
`VALIDATION_ERROR` 拒绝（输入保留；Console 恰一条固定脱敏行
`[PF] failed op=reading-log stage=pfresult code=VALIDATION_ERROR exit=1`，属 genuine 失败单次诊断；
回执链：rr-step5 `calls=1/errs=1`，rr-step6 成功保存后 `calls=2/errs=仍为1`，即成功保存零新增行）→ 补 `page=1`
后保存成功，稳定 ID `<SYNTH_RECORD_ID>`，状态 `来源不可用 — 需重新核验`（`verified=false`，basis=recorded，
从未标 verified）。回执 `hooks.console_errors_total=2` 的第二条来自**来源核验操作**
（rr-step10 `readingRecordSource`：后端 `reading_log.py:361-363` 把 `Source requires recheck` 映射为
`ok:false/code=VALIDATION_ERROR/exit=1`，client pfresult 分支按 genuine 失败记一行；rr-step14 读回 `errs=2`）。
已核对：没有任何单个操作产生两条 Console 行，每次 genuine 失败恰好一行（单终态规则成立，非重复打日志缺陷，
Console 行为 PASS）。`saveReadingRecord_calls=2` 仅计数 hook 包装的 `client.saveReadingRecord`
（call#1 失败首次提交、call#2 成功补页提交；correction/source-check 走其他 client 方法，不计入此数）。
（不含论文标题，不冒充真实结论）。独有关键词搜索：论文窗格正确为空（`未找到匹配的论文`），研究记录窗格命中该记录
（`当前记录` + 来源未核验提示 + `查看记录`）。打开记录核对内容/用途/归属一致；`重新核验并打开 PDF 物理页`
（`readingRecordSource`）按设计失败：`PDF is missing; recheck required`（合成库无真实 PDF 文件，
`has_pdf` 仅为元数据；未生成伪 PDF、未用 CLI 替代），记录保持未核验。追加修正
（`<SYNTH_CORR_ID>`）后状态变为 `已纠正 — 历史记录，非当前证据`；默认搜索不再命中旧记录
JSONL authority 读回：`logs/reading-log.jsonl`（1 行，`verified:false`）与 `logs/correction-log.jsonl`（1 行）一致。
仅停止自己的隔离实例后重启：默认搜索仍排除旧记录，历史勾选后仍可找回（含 corrections 的 details JSON，
`legacy_verified:false`），0 新增 Console 错误。收据隔离留存 `TRIAL_ROOT/module-interface-356-recovery/ui-research-record-2026-10-26.json`
（10 张合成截图 + `rr-step*.json` 16 份 DOM/action/Console 回执，均未入库；合成记录 ID 仅本机有效）。用户实例与原 Zotero 数据未动；
主 PROJECT-MANAGEMENT 与 queue 未改；既有 gates 未重跑（无产品修改）。

## 剩余验收收口与准确阻断（历史阶段：4cb 前；正式发行安装升级条已于本轮接受，见“本轮验收”）

- 历史阶段（snapshot 0adfc5f3）：插件 601 passed/1 skipped、typecheck/build 仅证明当时未变的 TS；Python 64 passed/2 skipped 与当时候选 CLI 绑定当时 Python 文件 hash。其后的 bb79312a 阶段为 Python 221 passed/3 skipped、插件 603 passed/1 skipped、bundle fa650fdf。当前 Scope 产品提交为 527d7960，manifest 的 current_verification 绑定实际源码及 673b71ca bundle；Python 文件未变，沿用原专用环境回归而不冒称重新执行。
- 来源 UI 证据绑定原 UI 环境，最终 vector 修复绑定新候选环境。真实 PDF 的页码/引文匹配成功与 PDF 变更失效均已观察；不能推广为任意 PDF/OCR 内容质量保证。
- 新建临时 candidate 退役前已保存源码 wheel、安装路径/版本/hash、依赖清单与绿 CLI；已删除约 162.7 MB 临时环境。曾误用的 h-ab 旧 runtime 已按原 wheel 恢复并逐文件核对，后续旧基线对照使用恢复后的环境；不隐瞒这次隔离边界错误。
- `remaining-local-acceptance.json` 的 versions/trash/Agent/64测试摘要来自本次代理原始工具回执转录，并非逐命令原始 stdout 文件；证据强度明确，不伪装为可重放日志。
- 尚未接受的门禁：真实 OCR/Embedding/云端模型任务仍被冻结，无可用本地模型；full H/A01 根因仍未解决。已实测的是修复候选从官方 RC4 升级（含取消保旧与成功发布后退役），以及官方 RC5 前后端配对在空 HOME 首次 Setup；不将它们外推为旧 RC5 自身升级失败安全性或整款软件发布接受。
- 主工作树 WIP、生产数据/凭据/pointer、#352/#354 分支均未改；未运行托管 CI、未提交/推送/合并、未自动恢复远端调用。

## 操作一致性续修（历史阶段：public 快照后、4cb 前）

- 搜索模式标签跟随本次请求（两轮 review 修后）：徽标/防抖用 trim 后同一前缀判定（`"  @ query"` 判 deep）；Ctrl+Enter 为单次 `executeSearch(true)`，不永久改徽标/mode，普通 Enter 仍 metadata；loading/结果头读捕获的 `_searchDeep`；两重试按钮显式回放 `this._searchDeep`（失败的 Ctrl+Enter deep 重试仍 retrieve）。测试走真实 `renderSearchSection` 接缝：`@ `/前导空格断实际 DOM badge/label 与 retrieve argv；Ctrl+Enter 单次性 + Retry 回放 retrieve + 普通 Enter 回 metadata + 在途不变性；console 用 argv 分流 mock（record 成功静默），genuine op 各恰一条、expected 零条、无 query/exception 文本。
- OCR 取消三终态（redo/rebuild/run）均经真实生产路径覆盖 `terminal.error.code==action.cancelled` + event/rc130/无额外上传：redo（stop 接缝既有用例追加断言）、rebuild（真实 `_run_ocr_rebuild` + stop token 新增用例）、run（真实 `commands.ocr.run` + 130-returning worker + stop token 新增用例；删 echo 占位）。改前红记录：payload `error: null`（现统一为 `action.cancelled`）。
- `tests/test_next_actions.py` 已删除（既有 `test_emit_unknown_action_fails_closed` 等 registry/reconcile 覆盖未知 id fail-closed，不重复）。生产活 DTO（`NextAction`/`NextActionScope`）+ schema 版本保留；删除前已确认生产仅 `actions/registry.py:1148` 引用 DTO。
- 证据 manifest 不再提交占位 bundle；`ui_bundle_this_fix` 为本次源码 `npm run build` 实得 hash，最终 gate 若 rebuild 变化则先修正再提交。snapshot 期 system-Python gate 与本次 dedicated-venv gate 分开标。
- 最终短 smoke（bundle `fa650fdf…`，隔离 ui-vault/profile/HOME/端口8217，已停自有实例并还原 vault bundle）：OBSERVED live——`'  @ spaced'` → badge `@` + loading `深度搜索中...`；`Biomechanical` M → `1 个结果M` 命中；页面 resource 0 外部 http（无 provider 出网）。UNOBSERVED——Ctrl+Enter 注入的请求语义：未记录 transport argv 与 `_searchDeep` 值（dispatch 返回 False 但消费 listener 未确认；settled 为 shared empty 卡，未区分 metadata/deep）。UNTESTED live——forced-deep 失败卡 + Retry 回放（本轮未注入后端故障）。UNIT-VERIFIED——真实 DOM 点击覆盖 forced-deep fail → Retry 回放 retrieve → 普通 Enter 回 search。不宣称宿主物理键已验，不宣称 live 捕获了 raw argv。本 smoke 原始 DOM 留私有，仅脱敏摘要入库。

## 本轮验收（4cb 公共 HEAD，2026-10-25 实测）

- 配对升级（真实 UI，B-upgrade-home/vault，端口 8225，bundle `fa650fdf…`）：官方 rc4 真轮（API 四项 SHA 全 MATCH）建旧 fixture `venv-2.0.0rc4-prior`，236 文件与官方轮一致，Python 发布旧 pointer（明确标注升级前置，不冒充首次安装）。UI 如实报版本不一致；走升级恢复入口真实 Cancel——旧 pointer/runtime 可运行（probe/versions 实测），失败 candidate 由产品移除；同 UI 重试完成升级——新 pointer 2.0.0rc5，237 文件与本轮新轮一致，旧 runtime 仅成功发布后由产品退役。pip 视图同一时刻只含一个同版本 paperforge 文件（官方 8f 在升级期隔离在外），产品 pip 命令未改（仅环境变量注入）。当前后端新轮 `0d58ff6f…` 建自 4cb（237 文件零差异绑定），旧 fecc 轮仅留私有红历史。
- 官方对（真实 UI，B-official-home/vault，端口 8227，官方 main.js `e6d0ede8…` + 官方后端 `8f931635…`）：空 HOME 首次 Setup 真实安装，236 文件与官方轮一致，依赖 110（含 pymupdf 2.0——RC5 未设上限，已如实记录风险，不算已锁依赖），Foundation READY。兼容轨（当前前端+官方后端）不冒充官方 UI 通过。
- A 判别（当时为可逆诊断，零产品 diff）：Obsidian 烘焙热键 Ctrl+Enter → editor:open-link-in-new-leaf；可信 CDP 输入触发调试 Scope，但搜索框原 keydown 未触发，普通 Enter 对照正常。随后已在 527d7960 做焦点限定的真正 Scope 修复并完成宿主红绿；不再将该软件缺陷误报为 CDP/前台权限问题。
- 本节为安装与初始判别阶段；当前产品与完整源码/产物身份以“Scope 修复验收”及 manifest 的 current_verification 为准。

## Scope 修复验收（产品提交 527d7960；测试基线 b1530c1c）

- Scope 唯一 owner（真实 UI，A ui-vault，bundle `673b71ca…`，deployed==worktree）：trusted CDP Ctrl+Enter → Scope callback → view entry `forceDeep:true` 恰一 → 实际 transport `retrieve --deep` → 离线 fault 卡 → 真实 Retry 回放 forceDeep → recover 真后端 deep → 普通 Enter 回 metadata。失焦/close 不拦截（零 entry/argv，父 baked `editor:open-link-in-new-leaf`  intact）；重渲染仅新 input 生效；旧 input 不再激活。unit 保留方法级 forced-deep one-shot（原名已正名），真实 Scope 集成回归以本 host 红/绿/blur/re-render/close 证据为准（unit 无适当宿主 Scope 接缝，不造假路由测试，删 wiring 用例及其 Scope import）。
- 分层绑定：B1 新轮 `0d58ff6f…` + B2 official `8f931635…` 绑定 fa650fdf 安装源码阶段；当前 scope 新 bundle 独立在 A host 实机绑定。Python 221 unchanged，不重冒称新 wheel；B runtime retired（pointer 为历史发布证明，非 live 安装断言）。
- 历史保留：A UNOBSERVED/草稿 dd2 绿为历史；current 以本节为准。远程冻结/full H 根因未闭（仅 short-A/B 身份闭合），无 merge/release。

## Integration & Release Stabilization：执行契约（集成未执行；单次诊断进展见后节）

计划建立时（`014953ca`）仅修正文档身份并整理收口方案，未新建集成分支、修改 #352/#354、合并或运行 CI。其后经用户明确授权，仅执行了一次 A01 单项诊断，结果见后节；不是完整 CI 或产品验收。该计划与单次 A01 阶段的 #356 产品提交为 `527d7960`；最新有限状态续修见末节，最终 master 集成候选仍未产生。主工作树 WIP 和生产环境继续隔离。

### 1. 按依赖收敛，不整体合并 public 分支

本地提交图显示：`master@a856f84f` 与 public 快照的共同祖先为 `46dbbd2d`；public 相对 master 为 53 文件、`+4795/-1353`，不能称为独立小修复。下表是本地已包含提交的归属，不替代操作前读取的 PR HEAD/base SHA。

| 顺序 | 有限交付 | 操作前与完成门禁 |
|---|---|---|
| 1：#352 | 首次 OCR 发现、笔记读取、历史任务呈现；本地对应 `439aa3d1`、`6cb6131e`、`18620e67` | 保持 Draft，先关闭当前 master 的完整 H 阻断；获合并授权后核对 issue `updated_at`、PR HEAD/base、目标 master SHA，整理为面向 master 的实际差异，跑所需检查和正常审查，不借用旧堆叠目标的绿灯 |
| 2：#354 | 研究记录闭环；本地对应 `9ab7812d`、`a7a74f7a`，另包含依赖修复 `605be45d` | 等 #352 收口后才处理目标基线、冲突和必需检查；保留原记录权威、修正历史及来源状态，不混入 #356，也不提前重写分支 |
| 3：#356 | 仅提取 `605be45d..786924a0` 的模块一致性增量；当前为 30 文件、`+2539/-709` | 上游完成后，在明确授权的隔离集成 worktree 整理增量；审查 client/transport、dashboard、i18n、设置、OCR 取消和 probe 接缝。不是直接把 public 分支合入 master |

`605be45d` 与 master 的 `2c3089ba` 不是相同提交：稳定 patch-id 不同；`pyproject.toml`、`requirements.txt`、`tests/test_ocr_state_machine.py` 的文件内容一致，CHANGELOG 记录不同。集成时核对并保留一次等价的依赖约束和回归，不重复套用整个修复，也不以标题相同就跳过审查。

共同接缝包括 CHANGELOG、命令文档、dashboard/i18n/client、测试及已跟踪 `main.js`。源码冲突逐项裁决；bundle 从最终源码重新构建，不手工拼接不同分支的编译件。不复制主工作树实现、不 force-push 共享历史。任何接受范围或 issue `updated_at` 改变，先刷新实施契约再写代码。

### 2. 一个最终候选，不拼装不同阶段的验收结论

| Gate | 明确动作与通过条件 |
|---|---|
| 身份冻结 | 上游集成完成后确定 `source_sha`、版本、wheel SHA256、bundle SHA256、依赖闭包、host profile 和 runner kind；目前这些最终候选值均为 **PENDING**。`527d7960` 是现有产品提交，`786924a0` 是文档快照，均不预称最终 master |
| 统一构建 | 从同一干净候选源码构建 wheel 与插件，生成发行文件校验清单。非 editable 安装；核对版本、真实安装路径、候选实际文件数与内容 hash、`pip check`、PyMuPDF 版本及 `<2` 约束。不能拼接旧轮 `0d58ff6f…` 与 Scope bundle `673b71ca…` 就宣称统一候选已验收 |
| 安装与升级 | 同一最终 wheel/bundle 真实空 HOME 首次 Setup；官方 RC4 → 候选的取消保旧、重试、成功发布 pointer 后退役旧环境。若声明支持官方 RC5 升级，再验 RC5 → 同候选的对应流程。官方 RC5 空 HOME 首装仅为独立发行对照，不是第二条升级证据；未测旧版本不外推支持 |
| 关键本地旅程 | 在同一候选真实宿主完成：同步/已有笔记读回；缺 Memory → UI build → 检索 → 重启；研究记录保存 → 纠正 → 历史找回；来源匹配 → PDF 变化失效 → 恢复；Ctrl+Enter 单次 deep → 故障 Retry → 普通 Enter metadata。记录实际部署 bundle hash，保留离线 OCR 上传集合及取消后零新增提交的回归 |
| CI 与完整 H | 实施中仅跑相关本地检查；每个 PR 遵守必需检查。最后一次产品变更后，对同一最终 SHA 做一次必要的完整候选门禁，不为纯文档投影反复启动全套 CI。当前 `ci.yml:452` 的 PR 事件只有 latest/latest，非 PR 才是三组 H；`All Checks Passed` 仅汇总实际运行的 jobs，所以 PR 全绿不能代替完整 H |

完整 H 记录解析后的固定 app/installer、Electron/Chromium、ChromeDriver、服务包和二进制身份。`full H/A01` 原因仍待关闭；short-A/B 重建的两次成功只补齐短实验身份，不允许据此标记完整宿主认证通过。首次失败保留，定位后修复；不提高超时、自动重试、删断言或标 known-flaky 放行。

### 3. 证据沿用与报告规则

- 未变能力的历史功能证据可以引用，但须说明原 source/artifact/host、相关源码与传递调用、依赖和输入是否保持一致；变化只触发受影响接缝的重验，不一律重做所有旧实机操作。插件 `603 passed / 1 skipped` 与沿用的 Python `221 passed / 3 skipped` 继续分层记录，不能称为最终 master CI。
- 最终候选必需的安装、关键旅程和完整门禁仍绑定统一身份。旧收据不改写 source SHA，也不把 B 阶段安装 bundle 当成 Scope 阶段 bundle。无法确认等价性的结果保留历史身份并标待验，不推导为候选 PASS。
- 复用现有 `scripts/release_readiness.py` 做 report-only 判定，不新增证据数据库或控制内核。其候选格式为 `source_sha/version/wheel_sha256/bundle_sha256`，矩阵按 capability/profile/layer/cases 声明，记录保留 source、artifact 与 runner。该工具要求 source SHA 和产物匹配；不支持的跨源码复用只能作为历史支持材料，不冒充新候选 VERIFIED。
- 每个候选单独保存证据目录并保留旧候选归档；同一候选的失败历史不可删除。判定器 R9 不把失败后的复跑绿色自动当作已验证，CLI 也不能替代 H/V 宿主证明，skip/timeout/warn 不算 pass。发布接受仍需现有 CI 与 owner gate。

### 4. 独立风险，不混入上游功能 PR

| 风险 | 最小处置与解除条件 |
|---|---|
| 官方 RC5 的无上限 PyMuPDF 依赖 | 保留旧发行物及风险记录；不原地替换旧资产、不声称 master 的 pin 已修复旧下载。后续获授权的新候选/发行物携带约束并核对实际安装闭包，发布说明明确旧发行物限制 |
| 完整 H/A01：已捕获 GPU 致命退出，诱因未定 | 单次诊断捕获 Chromium GPU fatal，浏览器 PID 与 WER 匹配；仍需区分 GPU/沙箱/runner 与插件交互诱因，不能据此排除产品影响或直接关闭 H。保留原始失败，不回滚 #350、不弱化矩阵 |
| 升级与来源核验覆盖不全 | 逐个声明实际支持的升级起点和宿主；来源错页、手工确认、仅记录位置等未覆盖分支继续标待验，不扩大“已匹配”或升级安全承诺 |
| 真实 OCR / Embedding / 云端模型 | 继续冻结。服务商作业终态、费用、数据留存与凭据处置仍须独立证据；恢复前另行确认授权、单篇目标及付费/上传范围，离线安全测试通过不等于恢复许可 |

该集成计划仍需关闭完整 H 阻断并准备 #352 的最终目标基线验收；本轮另完成用户授权的有限状态续修，见末节。不新增 UI/状态抽象、Rust 重写或 Evidence Engine，不自动合并 #354/#356 或发布。

## A01 单次诊断：原生 GPU 退出证据（2026-10-25）

用户明确授权的一次诊断为 [40217042572](https://github.com/LLLin000/PaperForge/actions/runs/40217042572)，诊断源码 `3d908391`、被测产品源码 `a856f84f`，仅 app 1.14.5 / installer 1.5.8 的原 A01；不是 #356 产品、完整 H 或最终候选认证。防火墙、真实 loopback 探针、离线 pip、原断言及超时均保留；任务失败，未重跑。

- **退出机制已观察**：`obsidian-native.log` 记录 `gpu_data_manager_impl_private.cc(448): GPU process isn't usable. Goodbye.`。日志 PID `8236` = WER PID `0x202C`，也对应进程采样的 `browser`，现可确认浏览器进程原生退出，而不再只描述为 renderer 失联。WER 异常 `0x80000003` / offset `0x1bf4993` 与先前成对诊断一致；不能据此反推先前每次故障都有相同诱因。
- **安装边界已收窄**：采样先见 venv 创建进程，后见 pip 进程；随后 GPU fatal。pointer 未发布，没有 A01 收据。共保留 1089 帧进程样本，未保存命令行；没有采到 GPU PID 不等于没有尝试启动 GPU 进程。
- **诊断自身缺陷如实保留**：新增 beforeTest 把同步版本 getter 当 Promise 调用 `.catch()`，产生 TypeError；原 afterTest 也有同类调用。因此本次有采集 hook 污染，且旧版本字段为 null 不应全部归因为崩溃。已将 hook 改为兼容同步/异步读取，实际旧 hook 的负例和新 hook 的同步、异步、不可用分支在本地红→绿；没有把本地修复当作新 CI 通过，也不回填旧收据。
- **仍未证明**：GPU 失败的底层诱因、是否存在插件触发关系、干净的 A01 通过、完整 H 通过。未添加 `--disable-gpu` 等绕过项，未将旧 Electron 标为不支持。后续只需针对同一宿主的 GPU 启动/沙箱/渲染配置做有判别力的调查，不再重复安装、同步、记录等已过路径；任何新远端诊断另需授权。
- **单次权限已消耗**：诊断 workflow 改为手动触发，避免后续推送自动追加运行。原始日志留在私有证据库；公开 manifest 仅发布机器码、身份和四份原始日志 hash。产品源码、#352/#354、主 WIP、生产 pointer/凭据未改；收费 OCR/Embedding/模型继续冻结。

## 八方向状态续修（2026-10-26，产品 f6775fd1）

契约：Issue #356 的 `2026-10-26T02:01:13Z` 用户授权续作，父需求 #130；基线 `f289608c`，同一隔离 worktree/public 分支。八个只读 scout 盘点，父代理唯一写入，并按正确性/验收、可维护性两轴集中复核。所有方向均已检查，**不等于所有状态已实机验证**。

统一的是既有跨层契约与错误归属，不是全应用一台状态机：Probe 描述模块可用性，Registry/runner 决定动作/范围，NDJSON 描述执行终态，client 管在途锁，View 管加载与关闭生命周期。未新建状态、日志、事件或存储框架。

| 方向 | 本次结果与证据等级 | 保留边界 |
|---|---|---|
| 安装/运行时 | UNIT VERIFIED：保存设置期间取消，不再开始后续 setup；运行时返回首页不再伪装 idle；abort listener 清理 | 本轮没有重新安装/升级。旧正式资产安装证据保留原身份；Stage 2 已发出的配置写入没有新增事务取消承诺 |
| 文献库/同步 | UNIT VERIFIED：sync 的 PFResult 拒绝保留 code/data/实际 exit；失败不再作为成功返回 | 原 166 篇验收为历史，不在本轮重跑；自动/手动同步并发策略未新增 |
| OCR 列表/操作 | UNIT + LIVE：加载中、需配置、失败、真正空库区分；失败显示 Retry 而非 0 篇；关闭丢弃迟到列表；刷新移除失效选择，负例无 stream 提交 | LIVE 为声明合成空库及离线故障注入；不等于真实 OCR/上传/质量验收，后端 scope 未改 |
| 搜索/Memory | UNIT VERIFIED：关闭清除防抖，不再发新搜索；在途回复不再改写已关闭 DOM | 本次空库 global dashboard 无搜索框，未把方法调用冒充真实搜索交互；当前两项关闭回归没有新增实机搜索证明。既有纸篇/Collection 搜索历史证据保留 |
| 研究记录/来源 | INSPECTED + HISTORICAL VERIFIED：沿用 JSONL、稳定 ID、correction 与来源契约，无本轮产品改动 | 来源 wrong-page、user_confirmed/recorded 等未覆盖分支仍待验；没有因为审代码就补记 PASS |
| 维护/恢复 | UNIT VERIFIED：Memory 备份恢复失败可见，后续成功重试有结果反馈 | 静态候选：版本恢复 `provenance_persisted:false` 的部分成功呈现仍需复现/裁定，本轮未改、不宣称通过 |
| Transport/终态/锁 | UNIT + REAL PROCESS：error/cancelled/result.ok:false + exit0 不变成功；启动失败传给事件消费者；解析 runtime 期间 stop 不 spawn；busy 返回结构化拒绝；卸载回收真实流子进程并释放锁 | 本地停止不代表撤销云端已提交作业。无全进程/全 OS 崩溃恢复承诺 |
| Console | UNIT + LIVE：probe/sync/OCR-list 复用既有 PFResult 入口；View 不重复记录同一 probe；一次故障一条脱敏 code/stage/exit，NO_PYTHON 与真实本地取消静默 | 不能据此保证 legacy 文本/authority-JSON 入口、局部文件打开和原生崩溃均被完整覆盖；原生 H 问题仍需独立日志/WER |

### 红绿、实机与身份

- 先复现 **19 个失败**：共享边界 10、启动生命周期 2、设置 3、关闭/失效选择 4；原始红输出保留。新增 probe 正/非零 exit 拒绝边界后，完整插件 **626 passed / 1 skipped**（32 文件通过、1 文件跳过），typecheck/build 通过；skip 不算 pass。后端 Python 未改，旧 `221 passed / 3 skipped` 不冒称新跑。
- 本轮 frontend bundle：`a13eef8bd2ad32d83772d2c5782e5c6b2ddfed35faab7afd5779242797bb93a1`，部署件与工作树构建相同；Obsidian 1.14.5 / Electron 37.6.0 / Chromium 138.0.7204.251，独立 HOME/profile/Vault，autoSync=false，runner 为真实桌面 CDP。
- LIVE：未发布 pointer 的合成 HOME 正确呈现 setup_required，零 Console/零子进程；声明的离线 transport 注入使 OCR list `ok:false + exit0` 出现失败卡，恰一条 `[PF]` Console；原生点击 Retry 后真实后端读取恢复正常空库，零新增错误。保存三张截图、读回/Console 收据。
- REAL PROCESS：通过已有自定义 runtime/spawner 接缝启动仅 sleep 的真实 Python 子进程，等待 spawn 事件后卸载插件；进程 exit1、registry=0、active=false、outcome.cancelled=true、零 Console。首轮 fixture 在卸载前已超时结束，保留为**非卸载通过**；它实际验证了 exit0 无 terminal 仍为 protocol_failure，不删除此记录。
- 身份前置发现旧私有 venv 有 3 个历史 Python 文件差异，未原地安装/修改。随后只在可删除测试目录展开既有冻结 wheel `0d58ff6f…`，237/237 Python 文件与当前源码一致，经**明确声明的测试 runtime-wrapper**复测真实列表；依赖仍用原独立 venv。此方法只证明源码绑定的离线接口 smoke，不冒充 managed runtime 首装/升级或统一发行候选。初始旧 venv 的 Retry 收据和最终精确 wheel 的读取分开标。
- Chromium offline + 失效代理，Python 子进程重注入 socket guard，Null keyring、无凭据。无 OCR run/resume/redo、Embedding、模型、托管 CI、生产 pointer/数据或上游 PR 改动；未解除远端冻结。

私有证据留在 `TRIAL_ROOT/module-interface-356-state-audit/`：八份 scout 输出、四组红日志、完整绿日志、source manifest、UI/子进程/历史差异收据。public manifest 仅含 hash、状态、计数、命令与限制。自建临时 profile/HOME/Vault/wheel 展开目录已移除（含 ASAR 硬链接的文件逻辑大小约 39 MB，不冒称等额实际释放空间）；原有环境/历史证据未删除。

### 后续仍有价值的有限工作

1. 对版本恢复“字节成功、provenance 未持久化”的部分成功做离线复现，再决定最小 UI/诊断修正。
2. 补真实 paper/Collection 上下文的关闭在途搜索实机证据，盘清 global 模式的搜索入口，不为获得 PASS 人工调用 renderer。
3. 检查剩余 legacy 文本与 authority-JSON 端点的终态/Console 归属，保持合法审计报告与命令失败不同，不强制全部套同一种 decoder。
4. 完整 H、最终集成/发行认证、真实提供商质量和费用继续独立；无新增 CI 或付费授权，不用本轮本地绿灯豁免。

## 剩余缺口第二批分发（2026-10-26，历史定位快照）

基线 `cbb7c84d9205bcdb37f99ead2479eb42dc2ec5e2`；Issue #356 快照 `2026-10-26T04:15:36Z`；父需求 #130、原 worktree/安全边界不变。五个只读 scout 已返回并保存原输出，父代理核对争议接缝；**本节没有新产品修改、运行时复现或测试通过声明**，产品与 626/1 证据仍绑定 `f6775fd1`。

| 顺序 | 分发方向与源码结果 | 最小后续工作，不重复已过验收 |
|---|---|---|
| 1 | 版本恢复：`commands/versions.py:368-419` 明确允许字节恢复成功、`provenance_persisted:false`；client 保留该 flag，但 modal 四个适配调用和 dashboard 直接入口丢弃结果/统一显示成功 | 后端坏 meta 的 false 分支已在既有测试覆盖，不必重跑证明其存在。新增 UI 负例，再保留返回值、提示“内容已恢复，来源元数据未保存”；不谎称回滚，不自动重试，不改变字节 authority |
| 2 | 搜索：`onClose` 已清防抖/递增 generation；`dashboard.ts::_switchMode/_refreshCurrentMode` 替换 DOM 时没有同样失效处理，存在旧回复进入新上下文的源码风险 | 先用在途回复 + 正常切换论文/重渲染复现，再选共同生命周期接缝；补 paper/Collection 的真实输入→关闭实机证明。global 本来不渲染搜索，不人工调用 renderer 冒充用户入口 |
| 3 | Setup：Stage 2 正常 `outcome.ok:false` 已避免 View 重复日志；但 rejected `handle.outcome` 经 client `:551-586` 记录并重抛，仍可能落入 settings `:862-871` 的第二次记录 | 针对启动 rejection 做一次精确负例，再复用 Stage 1 的错误归属模式；本地 saveSettings 失败仍须有日志。关闭设置当前继续后台执行，不未经产品决定新增取消/事务回滚 |
| 4 | Legacy/渲染：`_executeStructuredJson` 有意把合法负面 authority 报告作为值返回；audit/staging 还需区分真实拒绝、协议异常和合法审计失败 | 先核对真实后端 shape，再选最小共享错误归属；不把全部 `ok:false` 强制 throw。`read/reconcile/paperStatus` 当前无 src 消费者的项不优先扩建；backendVersion 的 View 实际有 `.catch`，不是未捕获 Promise |
| 5 | 来源核验：读时重算 source_provenance，hash/内容变更会失效；recorded/user_confirmed 明确不等于程序文本匹配，暂未找到消费者自动标 verified 的漏洞 | 只补确有价值的覆盖：exact_text 在别页/多处匹配、printed_page 改动绑定，以及手工位置允许打开但不升级核验的分支；不改既有安全门或增加证据存储 |

上述为分发当时的 **INSPECTED** 快照，不是五项已经修复；后续已实施项目见末节。原始输出及父代理纠偏留在 `TRIAL_ROOT/module-interface-356-state-audit/remaining-triage/`。该定位阶段没有启动 CI、浏览器、Python 进程或服务商调用；完整 H、最终集成/发行和真实服务授权仍不动。

## 全流程与错误体验收敛方案（实施前设计基线，2026-10-26）

用户要求把完整流程和错误提示理顺。以下是实施前方案，基于 `eda097a18451056baeff255b0ceb65c1240c0e6b`、Issue #356 快照 `2026-10-26T04:34:56Z`；设计时产品为 `f6775fd1`。本轮 A/B 的实际交付与尚未证明的 C 阶段见末节，不能把整份方案标为完成。任务状态以 Issue 为准；主 WIP、既有堆叠 PR、生产环境、CI/收费冻结不变。

### 目标与主路径

目标不是“所有页面都不报错”，而是：用户能知道正在做什么、影响哪些文献、已经改变什么、结果是否可信，以及下一步能安全做什么。禁止错误变空库、部分成功变全成功、未知结果变安全重试、未配置变系统损坏。

| 用户任务 | 顺畅路径与必要反馈 | 异常后的下一步 / 最小离线验收 |
|---|---|---|
| 准备运行引擎 | 既有 Setup → Candidate → 版本/安装验证 → Python 发布 pointer；阶段与耗时可见，不伪造百分比 | 安装失败说明失败阶段，不一律怪 Python 路径；取消保留旧运行时。沿用已绑定的历史安装证据，最终候选另验 |
| 连接 Zotero | 选择真实 BBT JSON，说明格式、检测结果及附件连接；只读连接原始数据 | 缺文件、无法识别导出、格式错误分别提示；回到正确选择入口，不要求普通用户改配置或跑 CLI |
| 首次/再次同步 | 明确同步范围；完成后显示真实文献/新增/更新结果，已有笔记保留 | 空导出不是后端失联；部分失败显示成功部分与失败对象。重复同步不重复建文献；失败后先刷新已知结果再决定重试 |
| 找论文与阅读 | Library/Base → 论文身份 → 正式笔记/PDF；阅读不以 OCR/Embedding 为前提 | PDF 不可达不等于文献没导入；保留可读笔记，指向附件连接恢复。切换论文不串内容 |
| 可选 OCR | 确认单篇/Collection/全库的标题、数量与发送范围；请求范围和最终拦截 HTTP 集合一致 | 凭据未配显示待配置；停止新增提交与云端既有作业分开报告。断连不能宣称云端已取消。仅离线验范围，真实服务另授权 |
| 保存研究记录 | 自动带入当前论文，保存引文/用途/来源，返回稳定 ID；立即能检索该记录 | 保存失败保留输入；正文已保存但来源不可核验分别呈现，不升级为“已核验”。纠正保留历史，默认结果排除旧引文 |
| 检索与回到来源 | 元数据、研究记录、全文/语义结果分清；打开具体命中与原文位置 | 元数据缺 Memory → 现有 Memory 恢复入口，构建需显式操作；JSONL 记录检索不要求 Memory/Embedding。来源变化需重查，不把页码跳转当文本匹配 |
| 恢复与重启 | 恢复内容、来源元数据、历史任务与当前可取消任务分别读回；重启不丢记录/配置 | 恢复字节成功但 provenance 未确认，明确部分成功；无 terminal 的写操作先显示结果未确认，先查已有事实，不盲目重做 |

这些入口优先复用既有 Setup、Library/Base、论文面板、OCR Workspace、Memory 详情和记录结果，不另建工作台。全局搜索入口若需要新增产品行为，单独成为 agent-ready UX Issue，不悄悄扩进 #356/#352/#354。

### 状态与提示规则

这是展示/交互语义，不是新增后端 wire 枚举或全局状态机。模块可用性、操作执行、产物质量、来源核验仍各认既有 authority。

| 情况 | 用户应看到 | 操作规则 |
|---|---|---|
| 未配置 / 可选未启用 | 缺什么、影响哪项能力、去哪里配置；不把整个产品标故障 | 基础阅读和记录能力不被可选能力拖死；正常未准备状态不刷红 Console |
| 已确认空数据 | “读取成功，但没有文献/匹配结果”，附导入或调整查询入口 | 仅在权威读取成功后展示，不能靠 catch 后的空数组推断 |
| 加载 / 运行 | 当前步骤、已确认数量；进度未知就显示不确定进度 | 同一动作不重复提交；不把历史任务当本地活动任务；不显示无效时间 |
| 成功 | 已实际完成的结果与可打开产物 | 不用进程 exit0 代替语义成功，不用写入成功代替可检索/可定位 |
| 部分成功 | 成功部分与失败/未确认部分分开，例如“正文已恢复，来源记录尚未确认保存” | 保留真实主结果，不谎称回滚；旧响应缺 flag 不能断言写入必然失败；只给确实存在的查看/诊断动作 |
| 已失败 | 哪一步失败、已知影响、一个主要恢复动作，必要时一项次要动作 | 重试复用当次捕获的范围/参数，不随当前论文选择改变；收费/破坏性操作不自动重试 |
| 已取消 / 关闭视图 | 已停止什么、哪些副作用仍存在；本地与云端分开 | 关闭/切换视图废弃旧读取回复，不误杀其他模块的共享任务。Stage2 保留后台继续语义并说明“关闭设置不会停止配置”，不伪造 Cancel 能力 |
| 结果未确认 | “连接中断，是否完成尚未确认”；保留已知事实与查询入口 | 使用已有本地状态/产物/作业事实先核对；无终态不等于无副作用，不默认重试。远端查询仍遵守授权冻结 |

反馈以当前界面的持久卡片/行内状态为主；Notice 只补确有必要的跨页面结果，不重复弹同一失败。中文 UI 的主状态、下一步和关键确认文案保持中文，机器码仅放技术详情。不用 300px 侧栏塞原始 JSON、命令行或长错误堆栈。

### 错误归属与诊断

- Python/Registry/worker 提供事实、拒绝原因、范围与终态；不由 View 推测根因。Transport 处理进程/NDJSON，`PaperForgeClient` 按具名命令解码，View 负责用户恢复；合法负面 audit 报告不等于命令执行失败，不能全局把 `ok:false` 改成 throw。
- 每次真正失败只有一个诊断 owner：client 已记录的业务/stream/probe 拒绝不再由 View echo；本地文件、设置保存等没有 client 终态的失败仍由本地记录。部分成功只记录已确认失败的子步骤，不把成功主结果改成失败。
- Console 复用现有 `op/stage/code/exit` 与 trace；已有操作身份/时间字段能用则用，不引入另一套链路 ID、日志库、遥测或全局去重。不打印密钥、查询/引文、私人路径、完整 argv、stdout/stderr、Error 对象/stack。复制诊断仍只提供现有安全字段。
- Console 的目标是定位失败模块、步骤与错误类别，不保证仅凭一行确定所有根因。原生 GPU/进程退出和 JS 上下文消失需既有本机日志/WER；不宣称“一切错误都能在 Console 看到”。

### 实施顺序与验收门

1. **结果先讲真（#356 有限修复）**：版本恢复五处 UI 的部分成功；Stage2 启动 rejection 与本地保存失败的日志归属；核对真实 audit/staging shape 后最小修补。先写/执行能够失败的消费者负例，不重复证明已覆盖的后端分支。
2. **跨页面不串状态**：先复现实际 mode-switch/rerender 的迟到回复与防抖问题，再修共同生命周期接缝；真实 paper/Collection 输入、切换、关闭、Retry 保持原始目标。无实际 DOM 替换的检查不应无故取消正常在途查询。
3. **整条离线旅程验收**：按主路径表验证正常、未配置、已确认空、真实拒绝、进程/协议异常、部分成功、取消、结果未确认、重启。源定位补错页/多处匹配/printed-page 绑定/人工状态；不为缺测试而改正确的产品安全门。

每项交付都记录：步骤/确认范围、实际请求与副作用集合、可见终态、恢复是否成功、Console 条数/脱敏、重启读回、源码/构建/部署/宿主身份。证据继续分 INSPECTED、UNIT、LIVE、BLOCKED；不靠 mock 回声、方法直调或重跑一次变绿冒充用户旅程。

保持一个写入者；复用现有五份只读分发结果，不再重开全库泛查。实施时只跑相关 seam 检查，同一批最后一次产品变更后跑一次完整受影响本地门与真实宿主 smoke；旧代码未变的证据注明原身份后沿用。开发不逐小改等待 CI；最终集成的必需 CI、完整 H、统一 source/wheel/bundle/host 与 owner 发布门仍独立必需，不能豁免。真实 OCR/Embedding/模型及费用/留存验收继续另行授权。

## 流程与错误体验 A/B 有限修复（LOCAL VERIFIED，2026-10-26）

实施合同：Issue #356 / parent #130，Issue 快照 `2026-10-26T05:47:29Z`；基线 `5f7504ec7a837d5c1153697f9f84d38b75a33bc0`，产品 `2137cea9bd54a9b3708bba614c4983f2f2865ecf`。三份只读 scout 分别核对真实 audit wire、恢复响应兼容性和隔离宿主夹具；父代理为唯一写入者。未另建状态机、日志库、数据库或重试框架。

| 修复接缝 | 当前行为 | 本轮证明等级 |
|---|---|---|
| 版本恢复部分成功 | 显式 false 与旧响应缺 flag 都不冒充完全成功；正文已恢复与来源记录未确认分开提示，当前版本标记跟随已确认复制结果，选择其他版本不丢警告；仅显式 false 记录一条安全子步骤诊断 | 真实论文面板 Modal：故意损坏合成 meta，恢复 v1 后字节一致、meta 未改、当前标记 v1、选 v2 警告仍在；移除夹具故障后恢复 v2，正常关闭且 provenance/字节读回一致。直接 timeline 同类状态为 UNIT，不冒充实机 |
| Setup 启动失败日志归属 | client 已拥有启动失败时 View 不再重复记录；NO_PYTHON 仍静默，本地保存失败仍由本地记录一次 | 实际 client/MockTransport/Stage2 seam：ECONNREFUSED 一条、NO_PYTHON 零条、本地 saveSettings 失败一条；UNIT，非本轮真实安装验收 |
| 搜索视图生命周期 | 关闭及真正替换搜索 DOM 的 mode-switch/refresh 共用既有清理接缝，作废防抖和旧回复；不杀其他共享任务 | UNIT 覆盖 switch/refresh；真实 Ctrl+O 切论文、Ctrl+W 关闭与重开后搜索通过，见下 |
| render authority JSON | 保留合法 FAILED 审计和 ok:false mutation rejection 为值；启动失败、非 JSON/非对象和失败 transport 自报 ok:true 各有单条诊断，未知退出码也不能伪装成功 | 实际后端格式经源码核对；既有 client seam 覆盖合法负面报告与协议/进程负例。UNIT/INSPECTED，不宣称渲染内容质量已重验 |

### 红绿与真实操作证据

- 原始红例：首组 **8 failed / 2 passed**、render **3 failed**；实机发现后的当前版本标记红例、timeline 红例、未知退出码矛盾红例均保留。未知退出码红例保存为明确标注的工具回执转录，不伪装原始 stdout。
- 最终离线插件门：**641 passed / 1 skipped**，32 files passed / 1 skipped；typecheck、build 和 whitespace 检查通过。新增 15 个行为/边界用例，未新增永久测试文件。中间 639/1 属旧阶段，未改写为最终门。
- 最终构建/部署 bundle SHA256：`d964fd7e2a7b65b2633cbaa191458edd27452874784517d80ea2c0290fac47d2`。最终截图已实际查看。
- 搜索使用真实本地 Python/FTS，不是 canned response：Alpha 实际命中 A；通过原生 Ctrl+O 打开 B，再发起 Beta 查询。夹具仅延迟真实结果交付；释放 A 后 B 仍 searching、旧 DOM 零回写；释放 B 后仅显示 B。另发起真实 Workflow 查询，原生 Ctrl+W 关闭活动面板，再释放结果：leaf=0、idle、引用清空、旧 DOM 零回写；从产品命令重开后 Beta Study 正常命中。四次实际 search argv 和后端结果私下留存。
- 故障恢复演练只作用于合成 meta；正常恢复分支前由夹具移除损坏，**不是产品自动修复成功**。恢复警告是当前 View 的反馈，不承诺跨关闭/重启保留该 UI 消息。
- 测试工具问题也保留：热重载后首次按钮 detached，重新观察稳定页面后点击成功；错误的 PFResult 根字段等待谓词与 raw page/tab.evaluate 的全局上下文差异造成等待超时，未重提恢复操作，未当作产品时延失败或稳定性通过。上下文差异已上报工具；后续等待只检查真实 DOM。

### 身份、安全和清理

Windows x64；Obsidian **1.14.5 / Electron 37.6.0 / Chromium 138.0.7204.251**，宿主二进制 hash 见 manifest。独立 HOME/profile/Vault，autoSync=false；两篇 BBT 条目和两份 PDF 均为声明合成，不复制真实用户文献，也未运行 hardcoded 共享 sandbox builder。

本历史阶段使用已有专用 Python3.12.8 的依赖，加声明的 runtime-wrapper 指向冻结 wheel；当时 237/237 Python 文件匹配，wheel SHA256 为 `0d58ff6f75a8937ecbcd30fb48b786281f280b74c777cbfa71ec5ae4b8790c66`，实际 CLI/distribution/插件均观察为 2.0.0rc5。**更正独立身份探针**：另一次直接 `python -c` 未固定 cwd，`package` 实际指向主 checkout，虽然 distribution metadata 来自冻结目录；其 2.0.0 不是候选源码常量，旧说法撤回，原始收据保留。wrapper/字节校验与该探针分开看待；新候选已在 checkout 外用 `-I` 核实实际 site-packages 的 module/distribution 都为 2.0.0rc5。该历史阶段仍不是新的 managed 安装认证。

Node 外部 TCP guard、Python socket guard、Null keyring、Chromium offline/dead proxy 生效；没有真实 OCR/Embedding/模型或费用调用。本轮未改 Python 产品，不重跑也不冒称新的 Python suite；历史 221/3 仍仅属历史。

原始红绿日志、操作/源码收据、截图和清理回执保留于 `TRIAL_ROOT/module-interface-356-workflow-repair/`；公开 manifest 仅含身份、状态和 hash。已停止自己的宿主进程树并删除本轮临时 Vault/profile/wheel 解包目录，已有共享 venv/wheel/历史证据未动，asar hardlink 不冒算为释放空间。首次删除遇短暂 IndexedDB 文件锁的事实也保留。

### 仍未完成，不与本批混算

1. 设计 C 阶段：来源错页/多处匹配/printed-page 与手工核验状态等补充实机分支，以及更完整的失败/取消/结果未确认旅程；不是这次 641 项通过就全局验收。
2. 本次截图仍可见中英文混排、默认笔记暴露技术属性与 key 标题；这是明确 UX 待改善，不宣称全流程已经流畅。
3. 完整 H/原生 GPU 根因、上游集成、最终 source/wheel/bundle/host 发行组合、旧分发依赖及跨版本升级门仍独立未接受；未操作 #352/#354、master 或正式发布。
4. 真实服务终态、OCR 内容质量、Embedding/Agent 质量、事故费用/留存/凭据轮换仍需独立证据与授权，远端继续冻结。Console 帮助定位模块/阶段/错误类别，不保证单行自动确定所有根因。

## Offline Preview 范围冻结（2026-10-26，历史决策快照）

采纳用户新的停止条件：**不追求全仓无 Bug；以一个固定、可安装候选在声明环境中两次独立完成核心任务为目标。** 不再派自由扫描任务，不以测试数增长衡量产品进度。只准入错误数据/来源、数据丢失/越权收费、核心任务阻断，以及安装/升级/恢复/正式门禁阻断；其他 Findings 排队。

### 已完成的实际动作与唯一代码准入

- Issue #356 / parent #130，实施前 Issue 快照 `2026-10-26T08:56:18Z`，基线 `6c99f22e`；仍为父代理唯一写入。两个既有只读代理已收口，无新增广泛调查。
- 合成真实 PDF 的 `bridge bridge bridge` 中，引文 `bridge bridge` 有两处重叠命中；旧算法错误报告 `matched/occurrences=1`，实际 CLI source-check 返回 0。最小修复为字面量 lookahead 计数，保留现有 wire、路径/页码/hash/binding 和人工核验契约。
- 旧记录不重写：同一 ID 的实时投影现在为 `ambiguous/occurrences=2`，source-check 返回 1；完整且唯一的三词引文仍 matched/返回 0。专用 Python3.12.8 + socket guard + 隔离 HOME 的来源/阅读记录 CLI 回归 **15 passed**，只新增一个现有测试文件中的行为用例。
- 没有 TS 修改、重新安装或新增实机 UI 验收。641/1 是上一阶段未变 TS 的历史证据，不是新 Python 的整体验收。新修复前的 `0d58ff6f…` wheel 已不包含当前 Python 全量源码，不再宣称 237/237 当前匹配。
- 提交门禁判定先前记录不满足“最后修改后验收”而阻止一次提交，具体触发机制未调查；随后正常在 Bash 记录同一 15 项门并提交，未绕过 hook。重复执行不计为第二次独立用户旅程。

### 四个主工作包与两个独立队列

| 工作包 | 当前事实 / 下一动作 |
|---|---|
| 1. 分支集成 | 查询时 remote `6c99f22e` 对 master `a856f84f` 为 ahead20/behind4、60 个变更文件；共同基线 `46dbbd2d`。#352 HEAD=`de434c1b`，#354 HEAD=`605be45d`，仍 Draft 且保持原 base。对当前产品 `5aa440ed` 的 `git merge-tree` 完整模拟仅报告 `CHANGELOG.md` 内容冲突，未改变 HEAD/index/文件或完成真实合并。沿 #352 → #354 → #356 增量收口，不直接整体合入 public；计数为绑定快照，不是 Bug 数 |
| 2. 完整 H | 最新 master CI `39616028538` completed/failure，绑定 `a856f84f`。单次诊断 `40217042572` 采到 browser GPU fatal，但 instrumentation 污染/根因未闭。保留 latest/earliest 必过项，不延超时、不重试洗绿、不默认缩减支持范围；新的诊断 CI 仍需独立授权 |
| 3. 最终分发组合 | 最终集成 SHA、wheel、bundle、依赖闭包、managed runtime、宿主/runner 一次性绑定，全部以实际产物为准。旧阶段安装与 UI 证据不能拼成最终 tuple。现在不再制造一份未集成的临时 wheel 冒充 Preview |
| 4. 关键数据安全 | 本轮只修已证实的重叠引文错误核验。错页/多处命中/手工确认/恢复保护按固定用户旅程做准入，不随 Findings 扩修。现有来源 authority 限 Vault 内 canonical PDF；外部 Zotero 附件的实际同步/阅读/来源路径必须单独明确，不能把 Vault 内通过外推为外部目录已支持 |
| 5. UX 维护队列 | 中英文混排、key/技术属性优先展示、来源错误展示原始 dict 等进入维护队列；只有确实阻断核心任务才提升为本候选阻断。不做新画廊、状态内核或大 UI 重构 |
| 6. 提供商独立授权 | OCR/Embedding/云模型、费用/历史作业、数据留存和密钥轮换独立处理。当前是执行冻结，**尚不等于最终分发物已强制禁用远端能力**；离线 Preview 开放前也要证明不会因继承凭据而发起收费调用 |

### 最终 tuple 与两次独立主流程

最终 source/wheel/依赖/runtime **PENDING**；插件 bundle `d964fd7e…` 未变，只作历史/未变前端支持。已观察主机为 Windows x64、Obsidian1.14.5/Electron37.6.0/Chromium138.0.7204.251，不因此豁免已有其他宿主门禁。版本名沿用发布工具契约；不得在安装视图混入多个同版本 wheel 让 pip 随机选择。

| 固定候选步骤 | 每次独立运行必须读回的结果 |
|---|---|
| 1. 干净环境安装 | 实际插件/distribution/CLI 版本、源码与 artifact hash、安装来源、Probe 和 Python 发布 pointer；不用 editable 或手工预置运行时冒充 Setup |
| 2. 连接并同步授权 Zotero 导出 | 实际 BBT 文件、范围/数量、正式笔记/索引、附件可达；重复同步不重复、不改原始 Zotero |
| 3. 阅读和本地元数据搜索 | 正确论文/笔记/PDF；M 查询命中真实论文，缺索引能从 UI 恢复，不依赖 Embedding |
| 4. 保存与找回具体研究记录 | 稳定记录 ID、引文与用途；用非标题关键词命中该记录；保存后立即可见，纠正与历史关系正确 |
| 5. 回到来源 | 打开正确 PDF 的实际物理页；区分印刷页/人工确认/程序匹配，错页/重复/失效不伪称核验成功 |
| 6. 完整关闭并重启 | 同一数据/设置/记录/搜索与来源状态读回正确；不是只重载插件 |
| 7. 一次升级与一次安全恢复 | 旧内容不丢，失败/取消保留旧可运行状态，成功后才发布/退役；恢复的字节与 provenance 分开核对 |

两次运行用独立 HOME/profile/Vault 和各自证据目录，使用**同一最终候选 tuple**；不能把一次运行重启、重跑某个测试或历史产物拼接成两次。正常流程优先 UI，CLI 绕过必须标注。未授权真实 JSON/原始数据不可用模拟数据伪装；不开放真实收费操作。

**停止条件**：两次主流程均通过、主要 CI 与完整必需 H 门通过、无未解释的数据/授权 P0、产物身份一致，且故障真实可报告并不破坏已有数据。达到后停止本轮维护开发，进入实际用户试用；当前尚未达到，不能称“离线 Preview 已发布/已认证”。

该冻结快照确定的主线是：依赖集成 → 唯一配对候选 → 两次主流程认证。后续本地集成/构建已完成，见下节；真实 PR 改 base/Ready、合入 master 和新增 CI 仍未获得额外授权，不把权限边界解释为技术失败。

## 本地统一候选已构建（2026-10-26，LOCAL PACKAGE VERIFIED）

基线 public `59b89729`，Issue #356 快照 `2026-10-26T09:46:37Z`；没有新建 worktree。父代理唯一写入，四个只读小任务提供打包/gate recipe 与资产/证据核对；错误 cwd、包名和证据边界的建议由父代理依据实际文件/metadata 裁定，不直接采信。

本地分支从 public 建立；#354 `605be45d` 已为祖先，随后正常合入最新 #352 `de434c1b`（本地 merge `3d7500d4`）及 master `a856f84f`（本地 merge `9ead0993`）。两次均无内容冲突；最终四个上游 ref 都是祖先，较 public 仅 `CHANGELOG.md` 多一行，未新增产品实现。此前直接 master 模拟的冲突并未原样发生在这条顺序中。正常 gate/hook 均保留，不改现有 PR/base/Ready，不合入 master。

| 固定资产 | 实际身份 |
|---|---|
| 源码 | `9ead0993290812f0575236fbe81b7620f658189d`，仅本地整合分支 |
| wheel | `paperforge-2.0.0rc5-py3-none-any.whl`；SHA256 `5f0c40217610311c4edb6d76d1ae693ca4e9ace521088b2d275c1ffadbdbe1bc` |
| 插件 bundle | SHA256 `d964fd7e2a7b65b2633cbaa191458edd27452874784517d80ea2c0290fac47d2`；与 wheel 内 main.js 及单独资产逐字节一致 |

构建从该提交的 tracked-source archive 取包输入，复用本地 node_modules 编译后移除 staging junction，再以 `uv build --offline` 构建；不混入旧 build/egg-info/依赖目录。原始提交的预构建 JS 有 94 个 CRLF、hash 为 `7491393a…`，**重新编译的 canonical 源与历史 working-tree 构建都得到 d964fd7e**，不是两个不同的新 bundle。源码归档时间固定到 SOURCE_DATE_EPOCH。wheel 内 237 个 Python 文件与 canonical archive 一致；工作树 236 个字节一致，`core/next_actions.py` 仅 EOL 不同，未冒称全部 raw bytes 相同。

### 实际运行结果

- fresh 非 editable venv，Windows Python3.12.8，本机缓存离线安装 `[vector]`；35 个 distribution，`uv pip check` 全兼容，PyMuPDF1.28.2。实际 module/distribution/插件版本均为 2.0.0rc5，module 路径位于该候选 site-packages；299 个安装产品文件逐字节匹配 wheel。声明的 runtime pins 固定 34 个依赖版本，不是跨平台 hash-lock 或完整离线 wheelhouse。
- 集成插件完整本地门：**641 passed / 1 skipped**（32 files passed / 1 skipped）；真实 Python 子进程指定 fresh candidate，Node 外部 TCP guard 与 Python socket guard 生效。typecheck/production build 通过，未用历史 641/1 冒充本次运行。
- Python 串行范围门：Registry/reconcile、最终 OCR HTTP scope/cancellation、进度/状态、研究记录来源共 **167 passed / 1 skipped**。该门输出保存为明确标注的工具回执转录；不是全 Python suite 或真实提供商验收。
- 在 checkout 外执行安装候选的 **9 条真实 CLI 检查**（每条 fresh process）：保存 → 用途关键词命中同一记录 → exact_text 对应物理页2；重叠引文 ambiguous/count2 与错页 mismatch 均拒绝；人工确认为 confirmed，不是程序文本匹配。均为生成 PDF/合成 Vault，包含预期 exit1 的拒绝检查；不计为两条完整用户旅程。
- 依赖中 `httpx2/httpcore2` 已由实际安装的 OpenAI/HTTPX metadata 声明，且 pip check clean；未认定为拼写错误，也未验证提供商兼容性。构建输出的 license-table deprecation 只是已记录警告，不顺带扩修。

### 保留与未证明边界

本机仅保留 `TRIAL_ROOT/module-interface-356-offline-preview/candidate/` 中一套 wheel、四个插件资产、runtime constraints、candidate.json、checksums.txt，以及小型原始/转录证据。构建 staging、临时 venv、合成 Vault/HOME、测试 temp 已退役；共享旧 venv/node_modules/cache 未清理，临时 runtime 路径仅为历史身份。

**本次没有 managed Setup/pointer 发布、升级/恢复或新的真实 Obsidian 用户旅程。** 完整 H/主要 CI、两次独立七步 UI 验收、跨机依赖可获得性和分发物侧收费能力禁用仍 PENDING；测试 guard 不在 wheel 内，不能把测试环境断网说成产品已强制离线。候选仅本机留存，整合分支未推送，未发布/关闭 Issue/恢复提供商调用。

当前本地包仍沿用源码版本 2.0.0rc5、由 source/hash 区分，**不能假定既有 rc5 环境会因替换同版本 wheel 自动升级**；正式试用前应沿既有版本流程确定可区分的候选身份，或验证现有显式重装入口。不能混放多个同版本 wheel，也不以本次 fresh venv 成功替代这个升级边界。

## G3 trace/OCR 阻断诊断与本地修复（2026-10-28）

### 冻结失败证据

- Hosted run `40884914428` 的 H job `123485929988` 失败：28 passed、5 failed、2 skipped；同矩阵另外两个 H job 被取消。运行基于 `v2.0.0-rc6-candidate` / `42437546116a04c27efd917df94b0c845331e697`。原始 CI 记录仍由 GitHub 保存：[run/job](https://github.com/LLLin000/PaperForge/actions/runs/40884914428/job/123485929988)。
- Trace 失败来自过时的 E2E 断言：测试期待 `sync --json`，记录实际为 `exec sync ok=true`。`commandIdentity` 有意移除参数；产品 trace 行为不是故障。
- OCR 测试把 403、5xx、连接断开和畸形响应都要求成终态。无 job ID 的 5xx/断连/畸形响应不能证明服务端未接单，原行为正确地保留 `pending` + `submission_state=submitting`、不重传；测试等待终态导致超时。403 是可确认的访问拒绝，但 worker 之前未单独处理，误落入未确认分支，是实际缺陷。

### 修复与本地证据

- Trace E2E 现在断言 `exec sync` 且明确禁止出现 `--json`；保留既有参数脱敏契约。
- OCR worker 将 401/403 归类为 `blocked`，清除 `submission_state`，记录状态码并给出安全说明。E2E 分开检查 401/403、429 与 5xx/断连/畸形响应；无 job ID 的模糊提交仍须保持未确认，且只允许一次 POST。
- 红测先出现 **1 failed / 4 passed**：403 被落为 `blocked=0, pending=1`；修复后定向 Python 回归 **5 passed / 28 deselected**。Trace 单测 **30 passed**，插件 typecheck 通过，新增 Python 测试文件的 `ruff check` 通过。
- 对整份既有 worker/registry 文件运行 Ruff 仍报告 39 条 lint 诊断；没有一条指向本次新增分支或测试。未批量重排既有代码。

### 未接受的门禁与身份

- 本次证明 trace/OCR 修复、RC6 wheel 与候选源码绑定；不代表 provider 或发行认证。Hosted CI/H 按 Issue #356 的禁止 CI trigger/wait 约束未执行；G2 两次完整旅程、升级/恢复和 G4 发行安全仍为 PENDING。RC6 本地 host E2E 未启动：`where.exe Obsidian.exe` 未找到可执行文件，repo `.obsidian-cache` 不存在；setup-positive runner 会在 `os.homedir()` 下发布 runtime pointer，本轮没有预置隔离 host profile。
- Owner 批准 canonical version `2.0.0rc6`；`scripts/bump.py 2.0.0rc6 --no-git` 和 `scripts/check_version_sync.py` 通过。15 个文件已提交到 `7837e8a1f6a0942f7251feef28d4e66924129096`。`paperforge/plugin/.prettierignore` 让 pre-commit Prettier 忽略生成的 `main.js`，避免把 388.3KB 构建产物扩成 15,179 行空白格式变更。
- 最终 wheel-only 离线构建来自干净 staging（base `git archive` + tracked diff），并将经 `npm run build` 的 canonical `main.js` 放入 staging；wheel SHA256 `fba125f0b121f0c858523084fc6a57783607fff78b298fc5386b040b3f986990`。sdist 构建超时，未纳入候选。提交后用新鲜 `git archive 7837e8a1f6a0942f7251feef28d4e66924129096` 逐文件比对：297 个 wheel package entries 均存在且内容一致，唯一差异为 `paperforge/plugin/main.js` 的 CRLF/LF；其中 235 个 Python 源、9 个 plugin 文件，0 个 `.pyc/.pyo`。wheel 的 Python 源、版本 metadata 与 commit archive 一致。
- wheel 内插件 `main.js` SHA256 `5191b5f7944efc917980ee71ac4ec50b96b6022076983d55174de678f2c771f7`，`manifest.json` SHA256 `215cf6d0f82badb866804471d72fd7c615151fa2fbccef83432d4206ac69822a`，`versions.json` SHA256 `1c4961c6e4b161c02e3309c13c7983c4c4de21f5c8608beb7c0310b19bfb599d`。bundle 只在 CRLF/LF 上与 Git archive 不同；manifest 与 versions 文件逐字节一致。
- 最终本地源码门：独立 CPython 3.12.8 环境下 OCR state-machine + scope safety **54 passed**；插件 Vitest **654 passed / 1 skipped**；typecheck、production build、版本同步检查通过。Focused Ruff 测试文件检查通过；worker/registry 全文件仍有 39 条历史诊断，未顺带重写。
- Fresh non-editable CPython 3.12.8 venv 离线安装最终配对 wheel（35 个运行 distributions），`pip check` 全部兼容。隔离 HOME/合成 Vault 中实际执行 `config init`、reading-log 写入及搜索，返回并找回同一条合成记录；未使用 provider 或生产凭据。
- 同一最终 wheel 在隔离 Vault 执行 `probe all --json`：`NullKeyring` 与 socket/DNS deny guard 生效；六模块如实返回 installation=pointer missing、library=Zotero missing、OCR=无输出/无凭据、memory=DB missing、help=ready、maintenance=no items，进程 exit 0。OCR notice 原文为 “PaddleOCR API unreachable: OCR credential not found”；这是本地无凭据诊断，不是 provider 连通性证据，也不把整体状态记作 ready。
- 已创建并推送 annotated tag `v2.0.0-rc6-candidate-2`，GitHub tag object `0ff22aa2fb4a1988ca028ca6a8d45d74b64cb4e8` → target `61faf6961b35e0ea5fa6564e8b7ebeed47bcca0a`；包代码来源 commit 为 `7837e8a1f6a0942f7251feef28d4e66924129096`。GitHub API 已确认 tag ref/object。此 `v` 前缀 tag 不匹配 `publish.yml` 的数字 tag pattern；`ci.yml` 只对 main/master push 自动运行，因此该 tag push 不触发 CI/release。按 Issue #356 约束未 dispatch Hosted CI/H；G2/G4 仍 PENDING。
- G4 发行/安全结论未作出：Issue #356 未定义 RC6 专用 security checklist；当前 worktree 中没有 `candidate.json`/`matrix.json`（`scripts/release_readiness.py` 的输入），也没有 `project/current` evidence directory。不能据此宣称通过 release-security gate。
