# Phase 7 — Assumptions: Zotero PDF, Metadata, And State Repair

## 概述

| Sub-task | 现有实现 | 需修复位置 | 状态 |
|----------|----------|------------|------|
| PDF 路径修复 | `storage:` 前缀处理存在，但 BBT 实际输出 `KEY/KEY.pdf` 裸路径 | `pdf_resolver.py:59-64`，`literature_pipeline.py:750` | 需修复 |
| OCR meta 校验 | `validate_ocr_meta()` 已存在但 `run_deep_reading()` 未调用 | `literature_pipeline.py:2792` | 需修复 |
| 统一 repair 命令 | 无 | 需新建 `run_repair()` + CLI | 需新建 |
| 三向状态分歧检测 | 无 | 需在 repair 命令中新建 | 需新建 |

---

## 研究任务 1 — PDF 路径解析（BBT 附件路径）

**假设:** 主要修复点在 `load_export_rows()` (`literature_pipeline.py:750`) — 它从附件路径中剥离了 `storage:` 前缀，导致 `resolve_pdf_path()` 的 storage-relative 分支（`pdf_resolver.py:59-64`）永远不会被触发。

- **原因:** Better BibTeX 导出附件路径为 `KEY/KEY.pdf`（而非 `storage:KEY/KEY.pdf`）。`load_export_rows()` 第 750 行只提取 `attachment.get('path', '')`，不检查也不保留 `storage:` 前缀。`resolve_pdf_path()` 第 60 行明确检查 `raw.startswith("storage:")` 才会尝试 storage-relative 解析。裸格式 `KEY/KEY.pdf` 落到 vault-relative 分支（第 50 行）也会失败，因为 vault 根目录下没有 `storage/` 目录。
- **如果错误:** 如果 `resolve_pdf_path()` 有其他分支能正确解析 `KEY/KEY.pdf`，则修复点在别处（如 `zotero_dir` 的构造方式）。
- **置信度:** 高（已端到端追溯）

**假设:** `resolve_junction()` 函数（第 70-108 行）已正确处理 Windows junction 和 symlink（通过 `os.path.realpath` + ctypes fallback）。junction 解析逻辑不是问题所在，问题是路径从未达到可解析的形式。

- **原因:** `resolve_junction()` 在 `resolve_pdf_path()` 第 44 和 55 行被调用，只处理 absolute 和 vault-relative 候选路径。`storage:KEY/...` 路径在第 60 行绕过了 junction 解析（直接走 `zotero_dir / storage_rel` 而不调用 `resolve_junction`）。
- **如果错误:** 如果 `os.path.realpath` 在此 Windows 版本上不跟随 junctions，则修复点应在 `resolve_junction()` 而非 `load_export_rows()`。
- **置信度:** 中

---

## 研究任务 2 — OCR meta.json `ocr_status` 校验

**假设:** `validate_ocr_meta()`（第 1589-1620 行）已实现 META-01/META-02/STATE-02 所需的校验逻辑。它已在 `run_selection_sync()`（第 966 行）和 `run_index_refresh()`（第 1503 行）中被调用。

- **原因:** 函数检查 7 个条件（zotero_key 存在、fulltext.md 存在、result.json 存在、page_count 有效性、文件大小、page markers）后才确认 `done` 状态。它返回修正后的 `ocr_status` 和错误信息。已接入两个入口点。
- **如果错误:** 如果 `validate_ocr_meta()` 有 bug 导致返回错误状态，修复点应在该函数内部。
- **置信度:** 高

**假设:** `run_deep_reading()` 第 2788-2795 行直接读取 `meta.get('ocr_status')` **未调用** `validate_ocr_meta()`。这是当前 gap — 如果 `meta.json` 标记 `ocr_status: done` 但实际文件缺失，`run_deep_reading` 仍会报告论文已就绪。

- **原因:** 代码第 2792 行执行 `meta = read_json(meta_path)` 然后 `ocr_status = str(meta.get('ocr_status', 'pending')).strip().lower()`，从未调用 `validate_ocr_meta`。这与 `run_selection_sync` 和 `run_index_refresh` 处理同一 meta 的方式不一致。
- **如果错误:** 如果 `run_deep_reading` 实际调用了 `validate_ocr_meta()`（在某个未检查的代码路径中），则不存在 gap。
- **置信度:** 高（已验证函数代码）

---

## 研究任务 3 — Repair / State-Sync 逻辑

**假设:** 代码库中**不存在现有的 repair 命令**。ROADMAP 中描述的 repair 概念尚未实现。现有状态同步只有：

1. `run_deep_reading()` 第 2746 行 — 同步 `deep_reading_status`（library_record ↔ formal_note，不同步 OCR state）
2. `run_index_refresh()` 第 1521-1560 行 — 当 title 与任何 export key 不匹配时删除孤儿 library_record
3. `run_selection_sync()` 第 941 行 — 从 export 写入 library_record
4. `run_ocr()` 第 2570 行 — 运行 OCR 并写入 meta.json；末尾调用 `run_selection_sync` 和 `run_index_refresh`

这些都不构成能检测三向分歧（library_record vs formal_note vs meta.json）的统一 repair 命令。

- **原因:** 在源文件中 grep "repair" 返回零匹配。ROADMAP 明确将 Phase 7 描述为创建此命令的阶段。
- **如果错误:** 如果 repair 逻辑以其他名称存在（如 `verify`, `check`, `sync`），grep 未发现。
- **置信度:** 高

**假设:** 三向分歧检测需要比较：
1. `library_record.md` frontmatter `ocr_status` vs
2. `formal_note.md` frontmatter `ocr_status` vs
3. `meta.json` `ocr_status`（经过 `validate_ocr_meta()` 校验后）

目前这三个状态由**不同 worker 独立更新**，无交叉检查。`run_selection_sync` 更新 library_record（第 966-997 行），`run_index_refresh` 更新 formal_note（第 1503-1507 行），`run_ocr` 直接更新 meta.json。repair 命令需要调和对所有三个来源的矛盾。

- **原因:** 三个来源由三条独立代码路径更新。没有单一函数读取全部三个并解决矛盾。
- **如果错误:** 如果存在未发现的隐藏调解步骤，repair 命令范围会更小。
- **置信度:** 高

---

## 研究任务 4 — 测试覆盖

**假设:** `tests/test_pdf_resolver.py`（143 行）覆盖了 PDF 解析，但未覆盖 `load_export_rows()` 生成 `resolve_pdf_path()` 无法处理的路径这一集成场景。测试第 62 行用显式 `zotero_dir` 测试 `storage:ABC123/item.pdf` — 格式正确，但 BBT 实际产生的格式从不是这样。

- **原因:** `test_pdf_resolver.py` 中全部 8 个测试隔离测试 `resolve_pdf_path()`，输入格式良好。没有测试Exercise `load_export_rows()` → `resolve_pdf_path()` 链。
- **如果错误:** 如果某处测试exercise完整链并失败，则 gap 更小。
- **置信度:** 高

**假设:** `tests/test_ocr_state_machine.py` 覆盖 OCR 状态机，但专门测试状态转换（pending → queued → done），不测试 library_record vs formal_note vs meta.json 之间的校验一致性。

- **原因:** 文件第 440 行明确测试"run_ocr 处理所有文档化状态而不崩溃" — 测试 worker 健壮性，不测试跨系统状态一致性。
- **置信度:** 高

---

## 需修改的具体代码位置

1. **`literature_pipeline.py:750`** — `load_export_rows()`: 将 BBT 路径 `KEY/KEY.pdf` 规范化为 `storage:KEY/KEY.pdf` 格式后再返回
2. **`literature_pipeline.py:2792`** — `run_deep_reading()`: 在读取 `meta.json` 的 `ocr_status` 前调用 `validate_ocr_meta()`
3. **`literature_pipeline.py`** (新函数) — `run_repair(vault: Path)`: 检测三向分歧并报告/修复
4. **`paperforge_lite/cli.py`** — 添加 `repair` 子命令到 CLI dispatch

---

## 现有测试文件

| 文件 | 覆盖范围 |
|------|----------|
| `tests/test_pdf_resolver.py` (143 lines) | `is_valid_pdf`, `resolve_junction`, `resolve_pdf_path` — 8 个测试，隔离单元测试 |
| `tests/test_ocr_state_machine.py` | OCR 状态转换 — 测试 pending/queued/done/error/blocked/nopdf |
| `tests/test_ocr_preflight.py` | PDF preflight — 4 个测试覆盖 has_pdf、路径解析、nopdf 状态 |
| `tests/test_smoke.py` | `run_deep_reading` 冒烟测试 — 第 210-225 行覆盖三状态输出 |
| `tests/test_cli_worker_dispatch.py` | CLI dispatch stubs — 非集成测试 |

无测试覆盖 `load_export_rows()` → `resolve_pdf_path()` 链处理 `KEY/KEY.pdf` BBT 路径的场景。无测试覆盖三向状态分歧。

---

## 需外部研究

- Better BibTeX 是否可配置为在附件路径中输出 `storage:` 前缀（ZPATH-02 提到 `storage:KEY/file.pdf` 表明这可能是 BBT 配置选项）
- `KEY/KEY.pdf` 裸格式是否是 BBT 唯一输出的格式，或不同 BBT 版本是否产生不同格式
