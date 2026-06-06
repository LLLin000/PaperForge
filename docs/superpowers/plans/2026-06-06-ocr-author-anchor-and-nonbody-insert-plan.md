# OCR Author Anchor And Non-Body Insert Plan

Date: 2026-06-06  
Scope: `ocr_roles.py`, `ocr_document.py`, `ocr_metadata.py`, `ocr_blocks.py`, related tests, real-paper validation on `SAN9AYVR`

## Goal

收掉当前最不稳的一条链：

1. 开放式 `authors` 文本识别会误伤正文
2. early-page 作者简介 / profile card / side insert 会被误救回正文
3. `page` 号和人名信号都不该作为主判定依据

目标是把这条线改成：

- `authors` 只走 `frontmatter zone + Zotero/source metadata anchor`
- `author bio` / `profile card` / `early-page side insert` 统一走 `non_body_insert` 路径
- 先识别正文主 spine，再识别“不属于正文”的插入 cluster
- 人名/履历句式只做增强信号，不做主判定

## Current Root Cause

`SAN9AYVR` 暴露了三类错误：

### 1. 正文被误判成 `authors`

例如 page 3 的：

- `In Section 5, the focus is on ES based bioelectronics ... $^{8,49}$`

被打成 `authors`。

根因：

- 当前 `ocr_roles.py` 对 author-like text 仍然开放式识别
- superscript / comma / name-like token 在综述正文里很容易误触发

### 2. page-1 / page-2 的作者简介块被当正文

例如：

- `Dr Ya Huang is currently ...`
- `Zhenlin Chen is currently ...`
- `Xinge Yu is the Associate Director ...`

这些在 PDF 上是明显的 early-page 插入 profile blocks，不属于正文主链。  
但现在要么直接被判 `body_paragraph`，要么先成 `frontmatter_noise` 再被 rescue 成 `body_paragraph`。

根因：

- 系统还缺少 `non_body_insert` 这一类结构类型
- rescue 只看“像不像 body”，没先问“它是否属于 body spine”

### 3. `authors` 和 `author bio` 的职责混在一起

现在 `authors` 被拿来承担两种事情：

- metadata/frontmatter 作者块
- 各种 name-like non-body blocks

这是不对的。两者必须拆开：

- `authors`：frontmatter metadata anchor
- `author_bio` / `profile insert`：non-body insert

## Design Principles

### 1. `authors` must be anchored, not guessed

`authors` 只允许来自：

- page-1 `frontmatter zone`
- 与 Zotero/source metadata authors list 有足够匹配的 OCR block

禁止：

- 从正文任意 block 开放式猜 `authors`
- 仅因有人名样式/上标/逗号就升成 `authors`

### 2. Determine body spine first

不是先识别 “sidebar”。

而是：

1. 先识别正文主 spine
2. 再找不属于 body spine 的 early-page insert cluster
3. 最后再用人名/履历语义做弱确认

### 3. Name-like text is only a confidence booster

人名信号只能在以下前提后使用：

- 该 block 已被判定为 non-body cluster 成员

用途：

- 增强 `profile_insert` / `author_bio_insert` 置信度

不能：

- 直接产出 `authors`
- 直接产出 `sidebar`

### 4. Avoid absolute page heuristics

不要写：

- `page <= 3 -> maybe sidebar`
- `page == 2 -> maybe author bio`

可以使用的只有弱相对先验：

- early document region
- close to frontmatter/body transition
- detached from body spine

但 page 号不能单独决定角色。

## Target End State

After this plan:

- metadata authors come from Zotero/source metadata truth, optionally aligned to a real OCR block
- body text no longer gets promoted to `authors`
- early-page author biography/profile cards become `non_body_insert`-family blocks
- rescue no longer converts non-body insert blocks back into `body_paragraph`

## Implementation Plan

### Task 1: Remove open-ended `authors` text heuristics

Files:

- `paperforge/worker/ocr_roles.py`
- tests in `tests/test_ocr_roles.py`

#### 1.1 Remove generic author promotion from `text` blocks

Find and delete or strongly demote logic that promotes arbitrary text to `authors` based on:

- superscript affiliation markers
- commas
- name-like shapes
- lack of year parens

This logic is currently too broad and causes正文误识别.

#### 1.2 Keep `authors` only in frontmatter zone

Allow `authors` assignment only when:

- page-1 zone detector returns `author_zone`
- or a future anchored author-candidate check explicitly confirms it

All other blocks should fall through to:

- `body_paragraph`
- `unknown_structural`
- or later `non_body_insert`

Acceptance:

- body blocks can no longer become `authors` purely from text shape

### Task 2: Add Zotero-anchored author candidate resolution

Files:

- `paperforge/worker/ocr_metadata.py`
- optionally `ocr_roles.py`
- tests in `tests/test_ocr_metadata.py`

#### 2.1 Treat source metadata authors as truth

For resolved metadata:

- if Zotero/source metadata authors exist, they are canonical
- OCR authors should only serve as alignment/traceability support

#### 2.2 Add OCR block alignment, not OCR author guessing

Implement a helper along the lines of:

- `_match_author_block_to_source_authors(blocks, source_authors)`

Use:

- page-1 candidate blocks only
- normalized name matching
- token overlap / fuzzy similarity

If matched:

- keep block role as `authors`
- store raw OCR authors evidence if useful

If not matched:

- metadata still uses source authors
- do not invent OCR `authors`

Acceptance:

- wrong OCR `authors` block does not pollute `resolved_metadata.authors`

### Task 3: Introduce `non_body_insert` / `profile_insert` regime

Files:

- `paperforge/worker/ocr_document.py`
- `paperforge/worker/ocr_blocks.py`
- `ocr_render.py` if render suppression is needed
- tests in `tests/test_ocr_document.py`, `tests/test_ocr_render_stabilization.py`

#### 3.1 Add a document-level detector for early-page non-body insert clusters

New helper(s), for example:

- `_detect_body_spine(blocks)`
- `_detect_non_body_insert_clusters(blocks, body_spine, ...)`

The detector should rely primarily on:

- geometry
- block continuity
- cluster layout
- style coherence

Not on fixed text phrases.

#### 3.2 What counts as a candidate cluster

Signals:

- block is not on the main body spine
- block belongs to an early-page region near the body/frontmatter transition
- multiple similar blocks appear in a local grid / side cluster
- cluster width / line height / family differ from body spine
- there is a visible vertical separation from body paragraphs

Optional weak boost:

- name-like lead
- biography-like tense or CV-style sentence forms

#### 3.3 Role strategy

Do not overload `authors`.

Either:

- introduce explicit role `non_body_insert`

or:

- add `_non_body_insert = true` regime marker while keeping `body_paragraph` temporarily

Recommendation:

- use explicit role `non_body_insert`

This keeps downstream logic simpler.

Acceptance:

- page 1/2 author bio blocks in `SAN9AYVR` no longer belong to body spine

### Task 4: Block rescue from pulling insert clusters back into body

Files:

- `paperforge/worker/ocr_document.py`
- tests in `tests/test_ocr_document.py`

#### 4.1 Add rescue guard

In `rescue_roles_with_document_context()`:

- before rescuing `frontmatter_noise -> body_paragraph`
- or similar body-promoting logic

check:

- whether the block belongs to a detected `non_body_insert` cluster

If yes:

- do not rescue to body

#### 4.2 Body-like font is not enough

This is the key fix for `SAN9AYVR`:

- page-1/2 author bio blocks have body-like font size
- but they are still not body

So rescue must require:

- body family match
- and body-spine compatibility

not just font match.

Acceptance:

- author bio/profile insert blocks stay out of正文 even when their font matches body

### Task 5: Use style/geometry more explicitly for insert detection

Files:

- `paperforge/worker/ocr_profiles.py`
- `paperforge/worker/ocr_document.py`

#### 5.1 Add body-spine comparison helpers

Useful block-level features:

- block width
- line height distribution
- mean font size
- font family
- italic/bold ratios
- x-column placement
- gap above/below

Use these to compare candidate blocks to the learned body spine.

#### 5.2 Detection logic should be relative, not absolute

No:

- fixed page number
- fixed width thresholds without page-relative normalization

Yes:

- narrower/wider than body family on the same paper
- detached from body chain on the same page/spread
- repeated cluster pattern on the same paper

Acceptance:

- insert detection generalizes across journals better than phrase rules

### Task 6: Downstream behavior

Files:

- `ocr_metadata.py`
- `ocr_render.py`
- maybe `ocr_index.py`

#### 6.1 Metadata

- `non_body_insert` must not be used as author candidate
- only anchored `authors` blocks may feed OCR frontmatter candidates

#### 6.2 Render

Default:

- `non_body_insert` should not render in `fulltext.md`

Optional:

- if needed later, preserve them in separate object/appendix notes
- but do not include in正文

#### 6.3 Index

- keep them out of main body index buckets
- optionally add a separate bucket later if useful

## Testing Plan

### Unit / integration tests

1. `tests/test_ocr_roles.py`
- body paragraph with superscript citations must not become `authors`
- page-1 author zone still yields `authors`

2. `tests/test_ocr_metadata.py`
- source/Zotero authors override bad OCR author candidates
- OCR alignment works only for page-1 candidates

3. `tests/test_ocr_document.py`
- early-page insert cluster is detected as non-body
- non-body insert is not rescued to `body_paragraph`

4. `tests/test_ocr_render_stabilization.py`
- `non_body_insert` does not appear in rendered正文

### Real-paper validation

Primary:

- `SAN9AYVR`

Must verify:

- `resolved_metadata.authors` is correct
- author bio blocks on pages 1-2 are absent from正文
- page 3 `In Section 5 ...` is body, not authors

Secondary regression:

- `2GN9LMCW`
- `7C8829BD`

Must verify:

- no regression in frontmatter authors
- no regression in tail/backmatter structure

## Acceptance Criteria

This plan is complete when:

1. arbitrary正文 text can no longer be promoted to `authors`
2. metadata authors are anchored to source/Zotero truth
3. early-page author biographies/profile cards are classified as non-body insert blocks
4. rescue no longer drags these insert blocks back into正文
5. `SAN9AYVR/fulltext.md` no longer contains author biography prose

## Risks

1. Overfitting insert detection to this one paper
- avoid “is currently / received degree” as primary rules

2. Hiding legitimate boxed正文 content
- keep detection cluster-based and relative to body spine
- validate on at least one paper with real正文 side notes later

3. Confusing affiliation/footnote blocks with author bios
- author bios are paragraph-like insert clusters
- affiliation blocks remain page-1 frontmatter candidates

