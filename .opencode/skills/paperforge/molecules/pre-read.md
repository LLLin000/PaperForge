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

## Step 3 — Read(读文)

```bash
paperforge --vault "$VAULT" read <KEY> --find "<关键词>" --json
```

READ ONLY THESE FIELDS:

```text
data.status             — "matched" | "no_match" | "no_readable_source"
data.matches[]          — 每项:source("fulltext"|"pdf")、text、line 或 page
```

判定(三态):

- **matched** → 用 `data.matches[]` 回答,引用 source + line/page。完成。
- **no_match**(源可读但无命中):
  - 问题本身是语义概念(原文可能不用该词)→ `retrieve` 一次:
    ```bash
    paperforge --vault "$VAULT" retrieve "<问题>" --paper <KEY> --json
    ```
    之后无论结果如何都 STOP,不二次 fallback。
  - 找的是明确原文术语 → 报告 "论文中未检索到该词",STOP。
- **no_readable_source** → **STOP**,报告 "no readable source"。

协议负责 fulltext/PDF 路径解析、wikilink 剥离与提取;Agent 不接触路径、不构造
grep/PyMuPDF 命令。一次 Step 3 最多一个 fallback(read 之外最多再执行一次
retrieve)。

---

## 完成时报告

- 已定位:title(来自 `data.paper.title`)· key
- 证据来源:fulltext 段落 | canonical PDF(page N)| retrieve 命中(标记
  "semantic match")
- 论文未提及的内容明确说明 "论文中未提及"
