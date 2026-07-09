# Visual Reading Canvas Correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Reading Canvas into a nonblank, read-only rendering of each paper's `fulltext.md` with Zotero highlights anchored in the source and comment-bearing annotations shown as connected side cards.

**Architecture:** Keep the existing annotation loader, card view models, navigation reducers, and connector geometry. Replace the plain source-block renderer with an Obsidian Markdown rendering adapter, add DOM-range projection for resolved source offsets, and make the Reading Canvas lifecycle expose every loading and failure state.

**Tech Stack:** Obsidian Plugin API (`ItemView`, `MarkdownRenderer`, vault APIs), CommonJS JavaScript, DOM `TreeWalker`/`Range`, CSS, Vitest, jsdom.

---

## File Structure

- Create `paperforge/plugin/src/canvas/markdown-surface.js`: render Markdown through an injected Obsidian adapter and expose a deterministic async result.
- Create `paperforge/plugin/src/canvas/dom-anchors.js`: map raw Markdown anchor ranges to rendered text nodes and wrap them without using `innerHTML`.
- Create `paperforge/plugin/tests/canvas-markdown-surface.test.mjs`: Markdown rendering and visible-state contracts.
- Create `paperforge/plugin/tests/canvas-dom-anchors.test.mjs`: DOM range projection, highlights, and unmatched cases.
- Modify `paperforge/plugin/src/canvas/anchors.js`: richer normalization, confidence, candidate count, and conservative disambiguation.
- Modify `paperforge/plugin/src/canvas/view-model.js`: separate inline-only annotations from side-card annotations and report unresolved counts.
- Modify `paperforge/plugin/src/canvas/render.js`: render the three-column reading shell, toolbar, card rails, popover, drawer, and error states.
- Modify `paperforge/plugin/src/canvas/index.js`: export the new surface and anchor APIs.
- Modify `paperforge/plugin/main.js`: inject `MarkdownRenderer`, coordinate async source/annotation rendering, and guarantee visible lifecycle states.
- Modify `paperforge/plugin/styles.css`: readable central article, side rails, highlights, popover, connectors, and narrow-pane drawer.
- Modify `paperforge/plugin/tests/canvas-source-anchor.test.mjs`: normalization/disambiguation regression coverage.
- Modify `paperforge/plugin/tests/canvas-viewmodel.test.mjs`: inline/card/unresolved partition coverage.
- Modify `paperforge/plugin/tests/canvas-render.test.mjs`: shell and visible-state DOM contracts.
- Modify `paperforge/plugin/tests/canvas-main-runtime.test.mjs`: end-to-end view lifecycle and stale-result tests.

### Task 1: Lock Down Nonblank Markdown Lifecycle

**Files:**
- Create: `paperforge/plugin/src/canvas/markdown-surface.js`
- Create: `paperforge/plugin/tests/canvas-markdown-surface.test.mjs`
- Modify: `paperforge/plugin/src/canvas/index.js`

- [ ] **Step 1: Write the failing Markdown surface tests**

```js
import { describe, expect, it, vi } from 'vitest';
import surface from '../src/canvas/markdown-surface.js';

describe('renderMarkdownSurface', () => {
  it('renders the complete source through the injected Markdown renderer', async () => {
    const host = document.createElement('div');
    const renderMarkdown = vi.fn(async (markdown, el) => {
      el.textContent = markdown;
    });

    const result = await surface.renderMarkdownSurface({
      host,
      markdown: '# Title\n\nComplete body.',
      sourcePath: 'Literature/BPQ8CXXR/fulltext.md',
      renderMarkdown,
    });

    expect(result.state).toBe('ready');
    expect(renderMarkdown).toHaveBeenCalledWith(
      '# Title\n\nComplete body.',
      expect.any(HTMLElement),
      'Literature/BPQ8CXXR/fulltext.md',
    );
    expect(host.textContent).toContain('Complete body.');
  });

  it('renders a visible error instead of an empty host', async () => {
    const host = document.createElement('div');
    const result = await surface.renderMarkdownSurface({
      host,
      markdown: '# Title',
      sourcePath: 'fulltext.md',
      renderMarkdown: async () => { throw new Error('renderer failed'); },
    });

    expect(result.state).toBe('render-error');
    expect(host.querySelector('[data-canvas-state="render-error"]')).not.toBeNull();
    expect(host.textContent).toContain('renderer failed');
  });
});
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```powershell
cd paperforge/plugin
npm.cmd test -- canvas-markdown-surface.test.mjs
```

Expected: FAIL because `src/canvas/markdown-surface.js` does not exist.

- [ ] **Step 3: Implement the injected Markdown surface adapter**

```js
async function renderMarkdownSurface(options) {
    var host = options.host;
    host.empty ? host.empty() : host.replaceChildren();
    var article = document.createElement('article');
    article.className = 'paperforge-canvas-article markdown-rendered';
    host.appendChild(article);
    try {
        await options.renderMarkdown(options.markdown, article, options.sourcePath);
        return { state: 'ready', article: article };
    } catch (error) {
        article.replaceChildren();
        article.dataset.canvasState = 'render-error';
        article.textContent = 'Could not render fulltext.md: ' + ((error && error.message) || 'Unknown error');
        return { state: 'render-error', article: article, error: error };
    }
}

module.exports = { renderMarkdownSurface };
```

Export `renderMarkdownSurface` from `src/canvas/index.js`.

- [ ] **Step 4: Run the focused test and verify it passes**

Run: `npm.cmd test -- canvas-markdown-surface.test.mjs`

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add paperforge/plugin/src/canvas/markdown-surface.js paperforge/plugin/src/canvas/index.js paperforge/plugin/tests/canvas-markdown-surface.test.mjs
git commit -m "feat(canvas): add markdown reading surface"
```

### Task 2: Strengthen Conservative Text Matching

**Files:**
- Modify: `paperforge/plugin/src/canvas/anchors.js`
- Modify: `paperforge/plugin/tests/canvas-source-anchor.test.mjs`

- [ ] **Step 1: Add failing normalization and ambiguity tests**

```js
it('matches OCR whitespace punctuation and line-break hyphenation differences', () => {
  const source = 'The immune-\ncheckpoint response, was durable.';
  const card = makeCard({ selectedText: 'The immune checkpoint response was durable.' });
  const anchor = resolveCanvasAnchor(card, readySource(source));
  expect(anchor.status).toBe('exact');
  expect(anchor.strategy).toBe('ocr-normalized');
  expect(anchor.confidence).toBeGreaterThanOrEqual(0.9);
});

it('does not force an ambiguous repeated passage without disambiguating context', () => {
  const source = 'Repeated result.\n\nRepeated result.';
  const card = makeCard({ selectedText: 'Repeated result.' });
  const anchor = resolveCanvasAnchor(card, readySource(source));
  expect(anchor.status).toBe('unresolved');
  expect(anchor.candidateCount).toBe(2);
  expect(anchor.reason).toContain('ambiguous');
});
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `npm.cmd test -- canvas-source-anchor.test.mjs`

Expected: FAIL on punctuation/hyphen normalization and ambiguity classification.

- [ ] **Step 3: Implement staged matching metadata**

Add a `normalizeForAnchor(value)` helper that:

```js
return value
    .normalize('NFKC')
    .replace(/-\s*\n\s*/g, '')
    .replace(/[\u2018\u2019]/g, "'")
    .replace(/[\u201c\u201d]/g, '"')
    .replace(/[，、]/g, ',')
    .replace(/[。]/g, '.')
    .replace(/\s+/g, ' ')
    .replace(/\s+([,.;:!?])/g, '$1')
    .trim();
```

Return this stable result shape from `resolveCanvasAnchor`:

```js
{
  status: 'exact' | 'page-level' | 'unresolved',
  strategy: 'literal' | 'ocr-normalized' | 'page-context' | 'none',
  confidence: number,
  candidateCount: number,
  rawStart: number | null,
  rawEnd: number | null,
  reason: string | null
}
```

Only choose among multiple candidates when page/context metadata produces a unique
winner; otherwise return `unresolved`.

- [ ] **Step 4: Run anchor tests**

Run: `npm.cmd test -- canvas-source-anchor.test.mjs`

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add paperforge/plugin/src/canvas/anchors.js paperforge/plugin/tests/canvas-source-anchor.test.mjs
git commit -m "feat(canvas): add conservative OCR anchor matching"
```

### Task 3: Project Source Offsets Into Rendered Markdown

**Files:**
- Create: `paperforge/plugin/src/canvas/dom-anchors.js`
- Create: `paperforge/plugin/tests/canvas-dom-anchors.test.mjs`
- Modify: `paperforge/plugin/src/canvas/index.js`

- [ ] **Step 1: Write failing DOM projection tests**

```js
it('wraps a range spanning multiple rendered text nodes', () => {
  const article = document.createElement('article');
  article.innerHTML = '<p>Alpha <strong>beta</strong> gamma.</p>';
  const result = applyDomHighlights(article, [{
    id: 'ANN-1', rawStart: 6, rawEnd: 16, color: '#ffd400',
  }]);

  expect(result.applied).toEqual(['ANN-1']);
  expect(article.querySelectorAll('[data-anchor-id="ANN-1"]').length).toBeGreaterThan(0);
  expect(article.textContent).toBe('Alpha beta gamma.');
});

it('reports an out-of-range anchor without changing the article', () => {
  const article = document.createElement('article');
  article.textContent = 'Short text';
  const result = applyDomHighlights(article, [{
    id: 'ANN-2', rawStart: 50, rawEnd: 60, color: '#ff0',
  }]);
  expect(result.unresolved).toEqual(['ANN-2']);
  expect(article.querySelector('[data-anchor-id]')).toBeNull();
});
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `npm.cmd test -- canvas-dom-anchors.test.mjs`

Expected: FAIL because `applyDomHighlights` is not defined.

- [ ] **Step 3: Implement text-node indexing and safe wrappers**

Implement:

```js
function buildTextNodeIndex(root) {
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    var nodes = [];
    var offset = 0;
    while (walker.nextNode()) {
        var node = walker.currentNode;
        var end = offset + node.nodeValue.length;
        nodes.push({ node: node, start: offset, end: end });
        offset = end;
    }
    return { nodes: nodes, length: offset };
}
```

`applyDomHighlights(article, anchors)` must split text nodes from the final node
backward, wrap only the selected slices in `<mark>`, set `data-anchor-id`,
`data-anchor-status="exact"`, `tabindex="0"`, and a CSS custom property for color.
It returns `{ applied: string[], unresolved: string[] }` and never uses
annotation-derived `innerHTML`.

- [ ] **Step 4: Run the focused tests**

Run: `npm.cmd test -- canvas-dom-anchors.test.mjs`

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add paperforge/plugin/src/canvas/dom-anchors.js paperforge/plugin/src/canvas/index.js paperforge/plugin/tests/canvas-dom-anchors.test.mjs
git commit -m "feat(canvas): map annotation ranges into rendered markdown"
```

### Task 4: Partition Inline Highlights, Side Cards, And Unresolved Items

**Files:**
- Modify: `paperforge/plugin/src/canvas/view-model.js`
- Modify: `paperforge/plugin/tests/canvas-viewmodel.test.mjs`

- [ ] **Step 1: Add failing view-model partition tests**

```js
it('creates side cards only for annotations with comments notes or images', () => {
  const vm = buildCanvasCardViewModel(readyState([
    annotation({ key: 'plain', selectedText: 'Plain highlight' }),
    annotation({ key: 'commented', selectedText: 'Text', comment: 'Important' }),
  ]), { sourceModel: readySource('Plain highlight Text') });

  expect(vm.highlights.map(x => x.id)).toEqual(['plain', 'commented']);
  expect(vm.cards.map(x => x.id)).toEqual(['commented']);
});

it('counts every failed anchor without dropping annotation data', () => {
  const vm = buildCanvasCardViewModel(readyState([
    annotation({ key: 'missing', selectedText: 'Not in source' }),
  ]), { sourceModel: readySource('Different text') });

  expect(vm.unresolvedCount).toBe(1);
  expect(vm.unresolved[0].id).toBe('missing');
});
```

- [ ] **Step 2: Run the view-model tests and verify they fail**

Run: `npm.cmd test -- canvas-viewmodel.test.mjs`

Expected: FAIL because `highlights`, `unresolved`, and `unresolvedCount` are absent
and plain highlights still become cards.

- [ ] **Step 3: Implement explicit partitions**

Return:

```js
{
  state,
  paperKey,
  sourceModel,
  highlights: allResolvedAnnotations,
  cards: annotationsWithCommentNoteOrImage,
  unresolved: allUnresolvedAnnotations,
  unresolvedCount: allUnresolvedAnnotations.length,
  message,
  stale
}
```

Use a single predicate:

```js
function annotationNeedsSideCard(annotation) {
    return Boolean(
        annotation.comment ||
        annotation.note ||
        annotation.imagePath ||
        annotation.imageData
    );
}
```

- [ ] **Step 4: Run view-model and layout tests**

Run: `npm.cmd test -- canvas-viewmodel.test.mjs canvas-layout.test.mjs`

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add paperforge/plugin/src/canvas/view-model.js paperforge/plugin/tests/canvas-viewmodel.test.mjs
git commit -m "feat(canvas): separate highlights cards and unresolved items"
```

### Task 5: Build The Reading Shell And Responsive Interaction Surface

**Files:**
- Modify: `paperforge/plugin/src/canvas/render.js`
- Modify: `paperforge/plugin/styles.css`
- Modify: `paperforge/plugin/tests/canvas-render.test.mjs`
- Modify: `paperforge/plugin/tests/canvas-card-dom.test.mjs`

- [ ] **Step 1: Write failing shell DOM tests**

```js
it('renders toolbar two card rails and a central markdown host', () => {
  const root = document.createElement('div');
  const shell = renderReadingCanvasShell(root, {
    paperKey: 'BPQ8CXXR', unresolvedCount: 2, annotationsVisible: true,
  });
  expect(root.querySelector('[data-canvas-role="toolbar"]')).not.toBeNull();
  expect(root.querySelector('[data-canvas-role="left-rail"]')).not.toBeNull();
  expect(root.querySelector('[data-canvas-role="article-host"]')).not.toBeNull();
  expect(root.querySelector('[data-canvas-role="right-rail"]')).not.toBeNull();
  expect(root.textContent).toContain('2 unresolved');
});

it('renders every terminal failure as visible text with retry', () => {
  const root = document.createElement('div');
  renderCanvasFailure(root, { state: 'missing-source', message: 'fulltext.md missing' });
  expect(root.textContent).toContain('fulltext.md missing');
  expect(root.querySelector('[data-canvas-action="retry"]')).not.toBeNull();
});
```

- [ ] **Step 2: Run render tests and verify they fail**

Run: `npm.cmd test -- canvas-render.test.mjs canvas-card-dom.test.mjs`

Expected: FAIL because the reading shell API and role selectors do not exist.

- [ ] **Step 3: Implement the shell and interaction DOM**

Add `renderReadingCanvasShell`, `renderCanvasFailure`, `renderHighlightPopover`, and
`renderUnresolvedDrawer`. Build DOM with `createElement`/`textContent`. Return
references `{ shell, toolbar, leftRail, articleHost, rightRail, drawer }` so
`main.js` does not rediscover structural elements through brittle selectors.

Add CSS with:

```css
.paperforge-canvas-reading-shell {
  display: grid;
  grid-template-columns: minmax(12rem, 18rem) minmax(32rem, 52rem) minmax(12rem, 18rem);
  align-items: start;
  gap: 1rem;
  position: relative;
}
.paperforge-canvas-article {
  min-width: 0;
  line-height: 1.65;
}
.paperforge-canvas-highlight {
  background: color-mix(in srgb, var(--paperforge-highlight-color) 38%, transparent);
}
@media (max-width: 900px) {
  .paperforge-canvas-reading-shell { grid-template-columns: minmax(0, 1fr); }
  .paperforge-canvas-card-rail { display: none; }
  .paperforge-canvas-drawer { display: block; }
}
```

- [ ] **Step 4: Run render and CSS contract tests**

Run: `npm.cmd test -- canvas-render.test.mjs canvas-card-dom.test.mjs canvas-section-dom.test.mjs`

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add paperforge/plugin/src/canvas/render.js paperforge/plugin/styles.css paperforge/plugin/tests/canvas-render.test.mjs paperforge/plugin/tests/canvas-card-dom.test.mjs
git commit -m "feat(canvas): render annotated fulltext reading shell"
```

### Task 6: Wire Obsidian Markdown Rendering Into The View Lifecycle

**Files:**
- Modify: `paperforge/plugin/main.js`
- Modify: `paperforge/plugin/tests/canvas-main-runtime.test.mjs`

- [ ] **Step 1: Add a failing view-level regression test for the exact blank symptom**

```js
it('renders fulltext before annotations and never leaves the canvas blank', async () => {
  const renderMarkdown = vi.fn(async (markdown, host) => {
    host.textContent = markdown;
  });
  const view = makeCanvasView({
    sourceText: '# Paper\n\nActual full text.',
    annotations: [],
    renderMarkdown,
  });

  view.setPaperContext('BPQ8CXXR', {
    key: 'BPQ8CXXR',
    fulltext_path: 'Literature/BPQ8CXXR/fulltext.md',
  });
  await flushPromises();

  expect(renderMarkdown).toHaveBeenCalled();
  expect(view.contentEl.textContent).toContain('Actual full text.');
  expect(view.contentEl.querySelector('[data-canvas-role="article-host"]')).not.toBeNull();
});
```

Also add tests for missing source, renderer rejection, annotation CLI rejection, and
switching from paper A to paper B while A is still loading.

- [ ] **Step 2: Run the runtime test and verify it fails**

Run: `npm.cmd test -- canvas-main-runtime.test.mjs`

Expected: FAIL because `_renderLoadedCanvas` still calls
`renderCanvasSourceSurface` with plain source blocks.

- [ ] **Step 3: Inject and coordinate `MarkdownRenderer`**

Import `MarkdownRenderer` from `obsidian`. Add:

```js
_renderMarkdown(markdown, host, sourcePath) {
    return MarkdownRenderer.render(
        this.app,
        markdown,
        host,
        sourcePath || '',
        this
    );
}
```

Convert `_renderLoadedCanvas` to `async`. It must:

1. Build the view model and shell.
2. Await `canvas.renderMarkdownSurface`.
3. Recheck `_canvasLoadSeq` and `_paperKey`.
4. Apply `canvas.applyDomHighlights` using `vm.highlights`.
5. Render side cards and unresolved drawer.
6. Initialize navigation and connectors only after DOM anchoring completes.

In `_loadAndRenderCanvas`, `await this._renderLoadedCanvas(...)`. Every catch branch
must call `renderCanvasFailure`; no branch may only clear `contentEl`.

- [ ] **Step 4: Run focused lifecycle tests**

Run:

```powershell
npm.cmd test -- canvas-main-runtime.test.mjs canvas-markdown-surface.test.mjs canvas-dom-anchors.test.mjs
```

Expected: all tests PASS, including blank-surface and stale-paper regressions.

- [ ] **Step 5: Commit**

```powershell
git add paperforge/plugin/main.js paperforge/plugin/tests/canvas-main-runtime.test.mjs
git commit -m "fix(canvas): render fulltext with visible lifecycle states"
```

### Task 7: Complete Navigation, Popover, Drawer, And Connector Wiring

**Files:**
- Modify: `paperforge/plugin/main.js`
- Modify: `paperforge/plugin/src/canvas/render.js`
- Modify: `paperforge/plugin/styles.css`
- Modify: `paperforge/plugin/tests/canvas-navigation.test.mjs`
- Modify: `paperforge/plugin/tests/canvas-connectors.test.mjs`
- Modify: `paperforge/plugin/tests/canvas-main-runtime.test.mjs`

- [ ] **Step 1: Write failing bidirectional interaction tests**

```js
it('scrolls from a side card to its inline highlight', () => {
  const { view, highlight, card } = renderedInteractiveCanvas();
  highlight.scrollIntoView = vi.fn();
  card.click();
  expect(highlight.scrollIntoView).toHaveBeenCalledWith({
    behavior: 'smooth', block: 'center',
  });
  expect(highlight.getAttribute('aria-selected')).toBe('true');
});

it('opens a detail popover for an inline-only highlight', () => {
  const { root, plainHighlight } = renderedInteractiveCanvas();
  plainHighlight.click();
  expect(root.querySelector('[data-canvas-role="annotation-popover"]')).not.toBeNull();
});
```

- [ ] **Step 2: Run interaction tests and verify they fail**

Run:

```powershell
npm.cmd test -- canvas-navigation.test.mjs canvas-connectors.test.mjs canvas-main-runtime.test.mjs
```

Expected: FAIL because source navigation still searches card-owned anchor elements
and inline-only highlights have no popover path.

- [ ] **Step 3: Wire interactions to the new DOM ownership**

Update delegated click handling:

- `[data-card-id]` selects the card, finds `[data-anchor-id="<id>"]`, and scrolls it
  to `block: 'center'`.
- `[data-anchor-id]` selects every fragment of that highlight, reveals its card when
  present, otherwise calls `renderHighlightPopover`.
- `[data-canvas-action="toggle-annotations"]` toggles rails/drawer.
- `[data-canvas-action="unresolved"]` opens the unresolved drawer.
- Escape closes popover/drawer before clearing selection.

Update connector measurement to use the rendered highlight fragment nearest the
card's vertical center. Keep the existing one-focused-connector policy.

- [ ] **Step 4: Run the complete canvas test set**

Run:

```powershell
npm.cmd test -- canvas-*.test.mjs annotation-main-runtime.test.mjs
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add paperforge/plugin/main.js paperforge/plugin/src/canvas/render.js paperforge/plugin/styles.css paperforge/plugin/tests/canvas-navigation.test.mjs paperforge/plugin/tests/canvas-connectors.test.mjs paperforge/plugin/tests/canvas-main-runtime.test.mjs
git commit -m "feat(canvas): complete annotated reading interactions"
```

### Task 8: Install And Run Real-Vault Acceptance

**Files:**
- Modify only if acceptance exposes a defect:
  - `paperforge/plugin/main.js`
  - `paperforge/plugin/styles.css`
  - relevant `paperforge/plugin/src/canvas/*.js`
  - matching regression test

- [ ] **Step 1: Run syntax and complete focused automated gates**

Run:

```powershell
node --check paperforge/plugin/main.js
Get-ChildItem paperforge/plugin/src/canvas -Filter *.js | ForEach-Object { node --check $_.FullName }
cd paperforge/plugin
npm.cmd test -- canvas-*.test.mjs annotation-*.test.mjs
```

Expected: syntax checks succeed and all focused tests PASS.

- [ ] **Step 2: Install the plugin into the shared Obsidian vault**

Run:

```powershell
C:\Users\tan\Desktop\SYSUCC\GaoLab-SYSUCC\.venv\Scripts\python.exe -c "from pathlib import Path; from paperforge.worker._utils import install_obsidian_plugin; vault=Path(r'C:\Users\tan\Desktop\SYSUCC\GaoLab-SYSUCC'); raise SystemExit(0 if install_obsidian_plugin(vault) else 1)"
```

This copies `main.js`, `styles.css`, `manifest.json`, and `src/canvas/` to:

```text
C:\Users\tan\Desktop\SYSUCC\GaoLab-SYSUCC\.obsidian\plugins\paperforge
```

Verify source and installed files match:

```powershell
$repo = 'C:\Users\tan\Desktop\SYSUCC\GaoLab-SYSUCC\9.code\PaperForge-feat-pdf-annotation-layer\paperforge\plugin'
$installed = 'C:\Users\tan\Desktop\SYSUCC\GaoLab-SYSUCC\.obsidian\plugins\paperforge'
@('main.js', 'styles.css', 'manifest.json') | ForEach-Object {
    if ((Get-FileHash (Join-Path $repo $_)).Hash -ne (Get-FileHash (Join-Path $installed $_)).Hash) {
        throw "Installed plugin file differs: $_"
    }
}
Get-ChildItem (Join-Path $repo 'src\canvas') -File | ForEach-Object {
    $target = Join-Path (Join-Path $installed 'src\canvas') $_.Name
    if ((Get-FileHash $_.FullName).Hash -ne (Get-FileHash $target).Hash) {
        throw "Installed canvas module differs: $($_.Name)"
    }
}
```

- [ ] **Step 3: Verify the real annotation fixture before opening Obsidian**

Run:

```powershell
C:\Users\tan\Desktop\SYSUCC\GaoLab-SYSUCC\.venv\Scripts\python.exe -m paperforge --vault C:\Users\tan\Desktop\SYSUCC\GaoLab-SYSUCC annotation export --paper BPQ8CXXR --json
```

Expected: valid JSON containing 17 annotations.

- [ ] **Step 4: Perform live Obsidian acceptance**

Reload PaperForge, open `BPQ8CXXR`, and select Reading Canvas. Verify:

- Complete `fulltext.md` is visible before interacting with annotations.
- All 17 annotations are accounted for as matched or unresolved.
- Plain highlights appear inline without side cards.
- Comment/note/image annotations have side cards.
- Card/highlight navigation and focused connector work.
- Narrowing the pane moves side cards into the drawer.
- Refresh, close/reopen, and rapid paper switching never leave a blank surface.

- [ ] **Step 5: Add a regression test for every acceptance defect, fix it, and rerun**

For each defect, first add the smallest failing test to the owning canvas test file,
then make the minimal implementation change. Rerun Step 1 and repeat Step 4 until
all acceptance checks pass.

- [ ] **Step 6: Commit acceptance fixes**

```powershell
git add paperforge/plugin
git commit -m "fix(canvas): close real-vault reading acceptance gaps"
```

If no acceptance defect required source changes, skip this commit.
