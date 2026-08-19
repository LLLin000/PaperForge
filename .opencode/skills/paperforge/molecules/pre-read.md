# pre-read

**精读前的确定性定位与读文。完全线性:Agent 执行命令、读点名字段、按冻结规则回退。**
本 molecule 是 Route A(已知论文)与 Route B(已知论文内找段落)的协议体。

> [!warning] Safety Rules
> - 不捏造论文未提及的内容
> - 不推断字段嵌套——只读每一步点名的字段
> - 不手动找文件——只用 PaperForge 返回的路径
> - 不选择提取工具——只用下面写死的命令
> - 不重复 fallback——每阶段最多一次,然后 STOP

---

## Step 1 — Locate(定位)

**用户给了 Zotero key?** 直接跳到 Step 2,不做任何 search。

**只有 title / DOI / author+year:** 跑 exact search:

```bash
$PYTHON -m paperforge --vault "$VAULT" search "<标题/作者/DOI关键词>" --limit 5 --json
```

READ ONLY THIS FIELD:

```text
data.matches[0].zotero_key
```

- matches 非空 → 用第一个 key,进 Step 2。
- matches 空 → 用户输入里是否还有**另一个**明确 identifier(title 和 DOI
  都有时用 DOI;反之用 title)?有 → 用那个 identifier 再跑一次上面的
  exact search;没有 → **STOP**,报告 "paper not found"。
- **禁止**:0 结果后用 retrieve 定位。semantic retrieve 不承担 identity
  resolution。

## Step 2 — Context(取 canonical 上下文)

```bash
$PYTHON -m paperforge --vault "$VAULT" paper-context <KEY> --json
```

READ ONLY THESE FIELDS:

```text
data.paper.title
data.paper.fulltext_path
data.paper.pdf_path
```

不读 `data.title`。不要构造或猜测任何其他路径。

## Step 3 — Read(读文,三态)

### 3a. fulltext 存在

检查路径有效:

```bash
test -f "<data.paper.fulltext_path>" && echo EXISTS
```

`EXISTS` → 读该文件;找段落用词面搜索:

```bash
grep -n -i "<关键词>" "<data.paper.fulltext_path>"
```

命中 → 读命中行及前后文段落,回答。完成。

### 3b. fulltext 不足 → canonical PDF(互斥分支 A)

仅当 **fulltext 命中但句子被截断 / fulltext 不可读** 时用 canonical PDF。
**extractor 由协议固定为 PyMuPDF,Agent 不选择工具、不做 storage
discovery**:

```bash
$PYTHON -c "
import fitz
doc = fitz.open(r'<data.paper.pdf_path>')
for i, page in enumerate(doc):
    text = page.get_text()
    import re
    for m in re.finditer(r'<关键词>', text, re.I):
        s = max(0, m.start()-400); e = min(len(text), m.end()+900)
        print(f'=== page {i+1} ===')
        print(text[s:e].replace(chr(10), ' '))
" 2>&1
```

`<data.paper.pdf_path>` 替换为 Step 2 读到的确切值。**若该值形如
`[[...]]`(wikilink),替换前去掉最外层 `[[` 和 `]]`。**
命中 → 用提取文本回答。零命中 → 该词可能确实不在本文,**STOP**。
此分支后不再尝试 retrieve。

### 3c. fulltext 词面零命中 → 二选一,互斥(分支 B)

**找的是明确原文术语**(如 "RFE"、"sample size")→ 用 3b 的 PyMuPDF 命令
对 canonical PDF 做一次词面搜索,然后 **STOP**(不再 retrieve)。

**问的是语义概念**(原文可能完全不用该词,如 "这篇的模型怎么避免过拟合")
→ `retrieve` 一次:

```bash
$PYTHON -m paperforge --vault "$VAULT" retrieve "<问题>" --paper <KEY> --json
```

之后无论结果如何都 **STOP**,不二次 fallback。

**两条互斥:一次 Step 3 最多执行一个 fallback(PDF 或 retrieve),不串联。**

### 3d. 两者都没有 → STOP

fulltext 与 pdf 都无效 → **STOP**,报告 "no readable source"。

---

## 完成时报告

- 已定位:title(来自 `data.paper.title`)· key
- 证据来源:fulltext 段落 | canonical PDF(page N)| retrieve 命中(标记
  "semantic match")
- 论文未提及的内容明确说明 "论文中未提及"
