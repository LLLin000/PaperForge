# 论文定位协议

本文件定义如何将用户输入（key / DOI / 标题 / 作者年份 / 自然语言）解析为论文 workspace。所有子流程（deep-reading, paper-qa, save-session）共用此协议。

## 核心原则

1. **确定性输入走 Python。** key、DOI、标题片段、作者+年份 —— 这些是机器能精确处理的。
2. **自然语言走 Agent。** "关于骨再生的那篇"、"去年那篇Nature" —— 需要 AI 理解语义。
3. **Python 搜不到时 Agent 兜底。** 不是报错，是换个方式再试一次。
4. **所有路径从环境变量获取。** 每条路由启动时先跑 `python -m paperforge.worker.paper_resolver env --vault . --shell pwsh | Invoke-Expression`。此后 `$env:PF_VAULT`、`$env:PF_LITERATURE_DIR`、`$env:PF_OCR_DIR`、`$env:PF_INDEX_PATH` 全程可用。不写死任何目录名。

---

## 前置：获取 vault 路径配置（每个路由启动时跑一次）

```bash
python -m paperforge.worker.paper_resolver paths --vault .
```

返回示例（所有路径均由 `paperforge.json` 动态计算）：
```json
{
  "ok": true,
  "data": {
    "vault_root": "/path/to/vault",
    "index_path": "<system_dir>/PaperForge/indexes/formal-library.json",
    "literature_dir": "<resources_dir>/<literature_dir>",
    "ocr_dir": "<system_dir>/PaperForge/ocr"
  }
}
```

**后续所有路径操作使用此输出中的值，不要自己拼接。**

---

## 输入类型判断

### 类型 1: Zotero Key（8位字符）

**识别规则：** 8位字母数字组合，如 `XGT9Z257`、`ABC12345`

**执行命令：**
```bash
python -m paperforge.worker.paper_resolver resolve-key <KEY> --vault .
```

**返回示例（路径由 paperforge.json 配置决定，不固定）：**
```json
{
  "ok": true,
  "data": {
    "match": {
      "key": "ABC12345",
      "title": "TGF-beta in Bone Regeneration",
      "domain": "骨科",
      "formal_note_path": "...",
      "ocr_path": "...",
      "fulltext_path": "...",
      "ocr_status": "done"
    }
  }
}
```

**返回 `"match": null` 时：** Agent fallback — 用 `paths` 命令获取的 `literature_dir` 路径 grep frontmatter：
```bash
rg -l "zotero_key:.*ABC12345" <literature_dir>/
```

---

### 类型 2: DOI

**识别规则：** 以 `10.` 开头的标准 DOI 格式，可能带 URL 前缀

**执行命令：**
```bash
python -m paperforge.worker.paper_resolver resolve-doi "10.1016/j.jse.2018.01.001" --vault .
```

**返回格式同类型1。** 返回的路径直接使用，不自己拼接。

---

### 类型 3: 标题片段

**识别规则：** 看起来像论文标题的文本（含学术关键词，非自然语言问句）

**执行命令：**
```bash
python -m paperforge.worker.paper_resolver search --title "Predictive findings on MRI" --vault .
```

**返回示例：**
```json
{
  "ok": true,
  "data": {
    "matches": [{ "key": "...", "title": "...", "formal_note_path": "...", ... }],
    "count": 3
  }
}
```

---

### 类型 4: 作者 + 年份

**识别规则：** 包含作者名（英文姓）和年份

**执行命令：**
```bash
python -m paperforge.worker.paper_resolver search --author "Smith" --year 2024 --vault .
```

---

### 类型 5: 自然语言

**识别规则：** 中文自然语言描述，如 "关于骨再生的那篇"、"去年Nature上那篇讲TGF的"

**Agent 操作：**
1. 用 `paths` 命令获取的 `index_path` 读 `formal-library.json`
2. 理解用户意图中的关键信息：主题词、年份、期刊、领域
3. 在 JSON 的 `title`、`domain`、`journal`、`abstract` 字段中搜索匹配
4. 如果 formal-library.json 无结果，用 `paths` 命令获取的 `literature_dir` grep formal notes：
   ```bash
   rg -i -l "骨再生|bone regeneration" <literature_dir>/ --include "*.md" -g "!*.canvas"
   ```
5. 读匹配的 frontmatter 确认是目标论文

---

## 多篇匹配处理

当搜索返回多个匹配时，Agent 必须列出候选清单，让用户选择：

```
找到 3 篇匹配的论文：

[1] ABC12345 — TGF-beta in Bone Regeneration (2024, 骨科, OCR: done)
[2] DEF67890 — Bone Healing After Fracture (2023, 骨科, OCR: pending)
[3] GHI11111 — Scaffold Design for Bone Repair (2024, 骨科, OCR: done)

请输入编号选择，或 refine 搜索词。
```

**格式要求：**
- 编号 + key + title + (year, domain, ocr_status)
- 不要只列标题或只列 key

---

## Fallback 顺序

```
输入
  │
  ├── 看起来像 key/DOI/标题/作者年份？
  │     └── YES → Python paper_resolver
  │             ├── 有结果 → 使用
  │             └── 无结果 → Agent grep fallback
  │                    ├── 有结果 → 使用
  │                    └── 无结果 → 告知用户
  │
  └── 看起来像自然语言？
        └── Agent 读 formal-library.json
              ├── 有结果 → 列出/使用
              └── 无结果 → Agent grep fallback
                     ├── 有结果 → 使用
                     └── 无结果 → 告知用户
```
