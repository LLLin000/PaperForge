# 论文定位协议

本文件定义如何将用户输入解析为论文 workspace。所有子流程公用。

## 核心原则

1. **Python 做确定性查找。** key、DOI、标题片段、作者+年份。
2. **Agent 做理解和兜底。** 自然语言、Python 无结果时的 fallback 搜索。
3. **路径从 `paths` 获取，不硬编码。** 禁止根据 vault-knowledge.md 的示例结构拼接路径。`ocr_dir`、`literature_dir`、`index_path` 只能从 `paper_resolver paths` 或 `paper_resolver resolve-key` 的返回 JSON 中读取。任何情况下都不要把目录名（如 `System`、`Resources`）写死在路径里。

---

## 通用命令

| 操作 | 命令 |
|------|------|
| 获取 vault 路径 | 已由 pf_bootstrap 完成 |
| 按 key 查 | `$PYTHON -m paperforge.worker.paper_resolver resolve-key <KEY> --vault "$VAULT"` |
| 按 DOI 查 | `$PYTHON -m paperforge.worker.paper_resolver resolve-doi "<DOI>" --vault "$VAULT"` |
| 按字段搜 | `$PYTHON -m paperforge.worker.paper_resolver search --title "..." --author "..." --year ... --domain "..." --vault "$VAULT"` |

---

## 输入类型判断

### 类型 1: Zotero Key（8位字母数字组合）

```
$PYTHON -m paperforge.worker.paper_resolver resolve-key <KEY> --vault "$VAULT"
```

返回 JSON 含 `key`, `title`, `domain`, `formal_note_path`, `ocr_path`, `fulltext_path`, `ocr_status` 等。所有路径由 `paperforge.json` 配置决定。

### 类型 2: DOI（以 `10.` 开头，可能带 URL 前缀）

```
$PYTHON -m paperforge.worker.paper_resolver resolve-doi "<DOI>" --vault "$VAULT"
```

返回格式同类型 1。

### 类型 3: 标题片段

```
$PYTHON -m paperforge.worker.paper_resolver search --title "..." --vault "$VAULT"
```

返回 `{"matches": [...], "count": N}`。

### 类型 4: 作者 + 年份

```
$PYTHON -m paperforge.worker.paper_resolver search --author "Smith" --year 2024 --vault "$VAULT"
```

### 类型 5: 自然语言（"关于骨再生的那篇"）

Agent 自己处理：
1. 读 `$IDX_PATH`（已由 pf_bootstrap 提供）
2. 读 `index_path` 指向的 `formal-library.json`
3. 在 `title`、`domain`、`journal`、`abstract` 中搜匹配
4. 搜不到就 grep formal notes 目录（`paths` 里的 `literature_dir`）下的 frontmatter

---

## Python 无结果时的 Agent fallback

Agent 用 `paths` 拿到的 `literature_dir`，自行 grep/read formal notes 下的 frontmatter。

## 多篇匹配处理

列出候选清单让用户选：

```
找到 3 篇匹配的论文：

[1] ABC12345 — TGF-beta in Bone Regeneration (2024, 骨科, OCR: done)
[2] DEF67890 — Bone Healing After Fracture (2023, 骨科, OCR: pending)
[3] GHI11111 — Scaffold Design for Bone Repair (2024, 骨科, OCR: done)

请输入编号选择，或 refine 搜索词。
```

## Fallback 顺序

```
输入
  │
  ├── 像 key/DOI/标题/作者年份？
  │     └── Python paper_resolver → 有/无结果 → Agent 兜底
  │
  └── 自然语言？
        └── Agent 读 formal-library.json → 搜 → 有/无
```
