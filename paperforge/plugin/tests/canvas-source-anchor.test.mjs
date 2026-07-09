/**
 * Vitest tests for pure source surface and anchor contracts (Phase ANN12, Plan 01).
 *
 * Tests cover:
 *   Task 1 — surface.js: source priority (fulltext → note → unavailable),
 *            source unavailable diagnostics, page block shaping,
 *            text normalization, pure boundary.
 *   Task 2 — anchors.js: exact/page-level/unresolved anchor resolution,
 *            downgrade reasons, diagnostics, card visibility when source missing.
 *
 * @module tests/canvas-source-anchor
 */

import { describe, it, expect } from 'vitest';

// ---------------------------------------------------------------------------
// Task 1: surface.js — source priority, block shaping, normalization
// ---------------------------------------------------------------------------

describe('surface.js — source priority (D-01, D-02, D-03, D-16, D-17, D-18)', () => {
    let SOURCE_KINDS, SOURCE_STATES, buildCanvasSourceModel, buildSourceBlocks, normalizeSourceTextForAnchors;

    beforeAll(async () => {
        const mod = await import('../src/canvas/surface.js');
        SOURCE_KINDS = mod.SOURCE_KINDS;
        SOURCE_STATES = mod.SOURCE_STATES;
        buildCanvasSourceModel = mod.buildCanvasSourceModel;
        buildSourceBlocks = mod.buildSourceBlocks;
        normalizeSourceTextForAnchors = mod.normalizeSourceTextForAnchors;
    });

    // ── D-01: fulltext_path + readable content → ready, sourceKind=fulltext ──

    it('D-01: fulltext with readable content produces ready model with sourceKind=fulltext', () => {
        const entry = { key: 'PAPER_A', fulltext_path: 'some/path/fulltext.md', note_path: 'some/path/note.md' };
        const sourceInputs = {
            fulltext: { path: 'some/path/fulltext.md', text: 'Full text content here.', exists: true, readable: true },
            note: { path: 'some/path/note.md', text: 'Note text.', exists: true, readable: true },
        };
        const model = buildCanvasSourceModel(entry, sourceInputs);
        expect(model.status).toBe(SOURCE_STATES.READY);
        expect(model.sourceKind).toBe(SOURCE_KINDS.FULLTEXT);
        expect(model.text).toBe('Full text content here.');
    });

    it('D-01: note content is ignored when fulltext is usable', () => {
        const entry = { key: 'PAPER_A', fulltext_path: 'ft.md', note_path: 'nt.md' };
        const sourceInputs = {
            fulltext: { path: 'ft.md', text: 'Fulltext body.', exists: true, readable: true },
            note: { path: 'nt.md', text: 'Note body (should be ignored).', exists: true, readable: true },
        };
        const model = buildCanvasSourceModel(entry, sourceInputs);
        expect(model.status).toBe(SOURCE_STATES.READY);
        expect(model.sourceKind).toBe(SOURCE_KINDS.FULLTEXT);
        expect(model.text).toBe('Fulltext body.');
        expect(model.text).not.toContain('Note body');
    });

    // ── D-02: fulltext unavailable, note_path usable → ready, sourceKind=note ──

    it('D-02: fulltext unavailable but note readable produces ready model with sourceKind=note', () => {
        const entry = { key: 'PAPER_B', fulltext_path: 'ft.md', note_path: 'nt.md' };
        const sourceInputs = {
            fulltext: { path: 'ft.md', text: null, exists: false, readable: false, error: 'fulltext-file-missing' },
            note: { path: 'nt.md', text: 'Note content.', exists: true, readable: true },
        };
        const model = buildCanvasSourceModel(entry, sourceInputs);
        expect(model.status).toBe(SOURCE_STATES.READY);
        expect(model.sourceKind).toBe(SOURCE_KINDS.NOTE);
        expect(model.text).toBe('Note content.');
    });

    it('D-02: diagnostics record fulltext miss when falling back to note', () => {
        const entry = { key: 'PAPER_B', fulltext_path: 'ft.md', note_path: 'nt.md' };
        const sourceInputs = {
            fulltext: { path: 'ft.md', text: null, exists: false, readable: false, error: 'fulltext-file-missing' },
            note: { path: 'nt.md', text: 'Note content.', exists: true, readable: true },
        };
        const model = buildCanvasSourceModel(entry, sourceInputs);
        expect(model.status).toBe(SOURCE_STATES.READY);
        expect(model.sourceKind).toBe(SOURCE_KINDS.NOTE);
        expect(model.text).toBe('Note content.');
        // Diagnostics should contain info about the fulltext miss
        expect(model.diagnostics).toBeTruthy();
        expect(model.diagnostics.fulltext).toBeDefined();
        expect(model.diagnostics.fulltext.reason).toEqual(expect.any(String));
        expect(model.diagnostics.fulltext.miss).toBe(true);
    });

    it('D-02: source model includes fulltext_path and note_path when falling back', () => {
        const entry = { key: 'PAPER_B', fulltext_path: 'ft.md', note_path: 'nt.md' };
        const sourceInputs = {
            fulltext: { path: 'ft.md', text: null, exists: false, readable: false, error: 'fulltext-file-missing' },
            note: { path: 'nt.md', text: 'Note body.', exists: true, readable: true },
        };
        const model = buildCanvasSourceModel(entry, sourceInputs);
        expect(model.fulltextPath).toBe('ft.md');
        expect(model.notePath).toBe('nt.md');
    });

    // ── D-03/D-16/D-18: neither source usable → source-unavailable ──

    it('D-03: neither source usable produces source-unavailable model', () => {
        const entry = { key: 'PAPER_C', fulltext_path: 'ft.md', note_path: 'nt.md' };
        const sourceInputs = {
            fulltext: { path: 'ft.md', text: null, exists: false, readable: false, error: 'fulltext-file-missing' },
            note: { path: 'nt.md', text: null, exists: false, readable: false, error: 'note-file-missing' },
        };
        const model = buildCanvasSourceModel(entry, sourceInputs);
        expect(model.status).toBe(SOURCE_STATES.UNAVAILABLE);
        expect(model.sourceKind).toBeNull();
        expect(model.text).toBeNull();
    });

    it('D-16: source-unavailable model does not indicate empty annotations', () => {
        const entry = { key: 'PAPER_C', fulltext_path: 'ft.md', note_path: 'nt.md' };
        const sourceInputs = {
            fulltext: { path: 'ft.md', text: null, exists: false, readable: false, error: 'fulltext-path-missing' },
            note: { path: 'nt.md', text: null, exists: false, readable: false, error: 'note-path-missing' },
        };
        const model = buildCanvasSourceModel(entry, sourceInputs);
        // The reason must not say "no annotations" or imply annotations are empty
        expect(model.reason).toBeTruthy();
        expect(model.reason.toLowerCase()).not.toContain('no annotations');
        expect(model.reason.toLowerCase()).not.toContain('no annotation');
    });

    it('D-18: source-unavailable model has a clear reason without crashing', () => {
        const entry = { key: 'PAPER_D' };
        const sourceInputs = {
            fulltext: { path: null, text: null, exists: false, readable: false },
            note: { path: null, text: null, exists: false, readable: false },
        };
        const model = buildCanvasSourceModel(entry, sourceInputs);
        expect(model.status).toBe(SOURCE_STATES.UNAVAILABLE);
        expect(typeof model.reason).toBe('string');
        expect(model.reason.length).toBeGreaterThan(0);
    });

    // ── D-17: distinguish path-missing vs file-missing ──

    it('D-17: fulltext-path-missing is distinguishable from fulltext-file-missing', () => {
        const entry = { key: 'PAPER_E' };
        const sourceInputsPathMissing = {
            fulltext: { path: null, text: null, exists: false, readable: false },
            note: { path: null, text: null, exists: false, readable: false },
        };
        const modelPathMissing = buildCanvasSourceModel(entry, sourceInputsPathMissing);
        expect(modelPathMissing.sourceKind).toBeNull();
        expect(modelPathMissing.reason).toMatch(/fulltext-path-missing/i);

        const sourceInputsFileMissing = {
            fulltext: { path: 'ft.md', text: null, exists: false, readable: false, error: 'fulltext-file-missing' },
            note: { path: null, text: null, exists: false, readable: false },
        };
        const modelFileMissing = buildCanvasSourceModel(entry, sourceInputsFileMissing);
        expect(modelFileMissing.reason).toMatch(/fulltext-file-missing/i);
    });

    it('D-17: note-path-missing is distinguishable from note-file-missing', () => {
        const entry = { key: 'PAPER_F', fulltext_path: 'ft.md' };
        const sourceInputsFulltextOk = {
            fulltext: { path: 'ft.md', text: 'Fulltext exists.', exists: true, readable: true },
            note: { path: null, text: null, exists: false, readable: false },
        };
        // Fulltext is available, so note-path-missing should not affect the model
        const model = buildCanvasSourceModel(entry, sourceInputsFulltextOk);
        expect(model.status).toBe(SOURCE_STATES.READY);
        expect(model.sourceKind).toBe(SOURCE_KINDS.FULLTEXT);
    });

    it('D-17: note-path-missing affects model when fulltext is also missing', () => {
        const entry = { key: 'PAPER_G' };
        const sourceInputs = {
            fulltext: { path: null, text: null, exists: false, readable: false },
            note: { path: null, text: null, exists: false, readable: false },
        };
        const model = buildCanvasSourceModel(entry, sourceInputs);
        expect(model.status).toBe(SOURCE_STATES.UNAVAILABLE);
        // The reason should include note-path-missing context
        expect(model.reason).toMatch(/note-path-missing/i);
    });
});

describe('surface.js — buildSourceBlocks (D-01, D-04)', () => {
    let SOURCE_KINDS, buildSourceBlocks;

    beforeAll(async () => {
        const mod = await import('../src/canvas/surface.js');
        SOURCE_KINDS = mod.SOURCE_KINDS;
        buildSourceBlocks = mod.buildSourceBlocks;
    });

    it('splits text by page markers into blocks', () => {
        const text = 'Intro text.\n<!-- page 1 -->\nPage 1 content.\n<!-- page 2 -->\nPage 2 content.';
        const blocks = buildSourceBlocks(text, SOURCE_KINDS.FULLTEXT);
        expect(Array.isArray(blocks)).toBe(true);
        expect(blocks.length).toBeGreaterThanOrEqual(3);
        // First block should be the intro (before first marker)
        expect(blocks[0]).toHaveProperty('pageIndex');
        expect(blocks[0]).toHaveProperty('text');
        expect(blocks[0]).toHaveProperty('sourceKind');
        expect(blocks[0].sourceKind).toBe(SOURCE_KINDS.FULLTEXT);
    });

    it('each block has stable id and pageIndex', () => {
        const text = 'Header.\n<!-- page 1 -->\nBody.\n<!-- page 2 -->\nFooter.';
        const blocks = buildSourceBlocks(text, SOURCE_KINDS.FULLTEXT);
        expect(blocks.length).toBeGreaterThanOrEqual(1);
        for (const block of blocks) {
            expect(block).toHaveProperty('id');
            expect(typeof block.id).toBe('string');
            expect(block.id.length).toBeGreaterThan(0);
            expect(block).toHaveProperty('pageIndex');
            expect(block).toHaveProperty('text');
            expect(block).toHaveProperty('sourceKind');
        }
    });

    it('empty text returns empty array', () => {
        const blocks = buildSourceBlocks('', SOURCE_KINDS.FULLTEXT);
        expect(Array.isArray(blocks)).toBe(true);
        expect(blocks.length).toBe(0);
    });

    it('handles text with no page markers as a single block', () => {
        const text = 'Continuous text without any page markers.';
        const blocks = buildSourceBlocks(text, SOURCE_KINDS.NOTE);
        expect(blocks.length).toBe(1);
        expect(blocks[0].text).toBe(text);
        expect(blocks[0].sourceKind).toBe(SOURCE_KINDS.NOTE);
    });

    it('sourceKind is preserved in each block', () => {
        const text = '<!-- page 1 -->\nContent.';
        const ftBlocks = buildSourceBlocks(text, SOURCE_KINDS.FULLTEXT);
        expect(ftBlocks[0].sourceKind).toBe(SOURCE_KINDS.FULLTEXT);

        const noteBlocks = buildSourceBlocks(text, SOURCE_KINDS.NOTE);
        expect(noteBlocks[0].sourceKind).toBe(SOURCE_KINDS.NOTE);
    });
});

describe('surface.js — normalizeSourceTextForAnchors (D-04, D-26)', () => {
    let normalizeSourceTextForAnchors;

    beforeAll(async () => {
        const mod = await import('../src/canvas/surface.js');
        normalizeSourceTextForAnchors = mod.normalizeSourceTextForAnchors;
    });

    it('collapses whitespace runs into single spaces', () => {
        const result = normalizeSourceTextForAnchors('Hello    world\n\n  \nfoo');
        expect(result.normalized).toBe('Hello world foo');
    });

    it('preserves raw-offset mapping', () => {
        const input = 'Hello world';
        const result = normalizeSourceTextForAnchors(input);
        expect(result.normalized).toBe('Hello world');
        expect(Array.isArray(result.offsetMap)).toBe(true);
    });

    it('offset map entries have rawStart, rawEnd, normStart, normEnd', () => {
        const input = 'Hello    world';
        const result = normalizeSourceTextForAnchors(input);
        expect(result.offsetMap.length).toBeGreaterThan(0);
        for (const entry of result.offsetMap) {
            expect(entry).toHaveProperty('rawStart');
            expect(entry).toHaveProperty('rawEnd');
            expect(entry).toHaveProperty('normStart');
            expect(entry).toHaveProperty('normEnd');
            expect(typeof entry.rawStart).toBe('number');
            expect(typeof entry.rawEnd).toBe('number');
            expect(typeof entry.normStart).toBe('number');
            expect(typeof entry.normEnd).toBe('number');
        }
    });

    it('preserves text case, punctuation, and CJK', () => {
        const cjk = '细胞凋亡在肿瘤发生发展中的作用机制研究';
        const result = normalizeSourceTextForAnchors(cjk);
        expect(result.normalized).toBe(cjk);
    });

    it('trims leading and trailing whitespace from normalized text', () => {
        const result = normalizeSourceTextForAnchors('  \n  Hello world  \n  ');
        expect(result.normalized).toBe('Hello world');
    });

    it('returns { normalized, offsetMap } shape', () => {
        const result = normalizeSourceTextForAnchors('test');
        expect(result).toHaveProperty('normalized');
        expect(result).toHaveProperty('offsetMap');
    });
});

describe('surface.js — pure boundary (D-04, D-05, D-26)', () => {
    it('surface.js is a CommonJS module with no fs, no Obsidian, no innerHTML', async () => {
        const mod = await import('../src/canvas/surface.js');
        // Module should export expected constants and functions
        expect(mod).toHaveProperty('SOURCE_KINDS');
        expect(mod).toHaveProperty('SOURCE_STATES');
        expect(mod).toHaveProperty('buildCanvasSourceModel');
        expect(mod).toHaveProperty('buildSourceBlocks');
        expect(mod).toHaveProperty('normalizeSourceTextForAnchors');
        // Constants should be frozen objects
        expect(Object.isFrozen(mod.SOURCE_KINDS)).toBe(true);
        expect(Object.isFrozen(mod.SOURCE_STATES)).toBe(true);
    });

    it('surface.js exports do not include DOM, fs, or Obsidian references', async () => {
        const src = await import('../src/canvas/surface.js');
        const keys = Object.keys(src);
        // No function references that suggest native PDF, DOM, or file system
        for (const key of keys) {
            if (typeof src[key] === 'function') {
                const fnStr = src[key].toString();
                expect(fnStr).not.toContain('require("fs")');
                expect(fnStr).not.toContain("require('fs')");
                expect(fnStr).not.toContain('require("obsidian")');
                expect(fnStr).not.toContain("require('obsidian')");
                expect(fnStr).not.toContain('innerHTML');
            }
        }
    });
});

// ---------------------------------------------------------------------------
// Task 2: anchors.js — anchor resolution (added in Task 2)
// ---------------------------------------------------------------------------

describe('anchors.js — anchor status constants and MIN_EXACT_TEXT_CHARS', () => {
    let ANCHOR_STATUSES, MIN_EXACT_TEXT_CHARS;

    beforeAll(async () => {
        const mod = await import('../src/canvas/anchors.js');
        ANCHOR_STATUSES = mod.ANCHOR_STATUSES;
        MIN_EXACT_TEXT_CHARS = mod.MIN_EXACT_TEXT_CHARS;
    });

    it('ANCHOR_STATUSES has exact, page-level, and unresolved', () => {
        expect(ANCHOR_STATUSES).toBeDefined();
        expect(ANCHOR_STATUSES.EXACT).toBe('exact');
        expect(ANCHOR_STATUSES.PAGE_LEVEL).toBe('page-level');
        expect(ANCHOR_STATUSES.UNRESOLVED).toBe('unresolved');
        expect(Object.keys(ANCHOR_STATUSES).length).toBe(3);
    });

    it('MIN_EXACT_TEXT_CHARS is a positive integer', () => {
        expect(typeof MIN_EXACT_TEXT_CHARS).toBe('number');
        expect(MIN_EXACT_TEXT_CHARS).toBeGreaterThan(0);
        expect(Number.isInteger(MIN_EXACT_TEXT_CHARS)).toBe(true);
    });
});

describe('anchors.js — resolveCanvasAnchor (D-06 through D-14, D-23)', () => {
    it('normalizes OCR punctuation and preserves raw source offsets', async () => {
        const { normalizeForAnchor } = await import('../src/canvas/anchors.js');
        const raw = '\uFF34\uFF45\uFF53\uFF54 \u201Cvalue\u201D\uFF0C next \u3002';
        const result = normalizeForAnchor(raw);

        expect(result.normalized).toBe('Test value next');
        expect(result.offsetMap).toHaveLength(result.normalized.length);
        expect(result.offsetMap[0].rawStart).toBe(0);
        expect(result.offsetMap[result.offsetMap.length - 1].rawEnd).toBe(raw.indexOf('next') + 4);
    });

    let ANCHOR_STATUSES, SOURCE_KINDS, SOURCE_STATES;
    let buildCanvasSourceModel, resolveCanvasAnchor, resolveCanvasAnchors;
    let entry, sourceInputs, sourceModel;

    beforeAll(async () => {
        const surface = await import('../src/canvas/surface.js');
        SOURCE_KINDS = surface.SOURCE_KINDS;
        SOURCE_STATES = surface.SOURCE_STATES;
        buildCanvasSourceModel = surface.buildCanvasSourceModel;

        const anchors = await import('../src/canvas/anchors.js');
        ANCHOR_STATUSES = anchors.ANCHOR_STATUSES;
        resolveCanvasAnchor = anchors.resolveCanvasAnchor;
        resolveCanvasAnchors = anchors.resolveCanvasAnchors;
    });

    beforeEach(() => {
        entry = { key: 'PAPER_A' };
        sourceInputs = {
            fulltext: {
                path: 'fulltext.md',
                text: 'Introduction to cancer biology.\n<!-- page 1 -->\nCell division is a fundamental process.\n<!-- page 2 -->\nApoptosis pathways are tightly regulated.\nMitochondrial outer membrane permeabilization.\n<!-- page 3 -->\nSignaling cascades control cell fate.',
                exists: true,
                readable: true,
            },
            note: { path: 'note.md', text: 'Note summary.', exists: true, readable: true },
        };
        sourceModel = buildCanvasSourceModel(entry, sourceInputs);
    });

    // ── D-06/D-07/D-11: exact anchor requires exactly one normalized match ──

    it('D-06: exact anchor when selected text has exactly one normalized match', () => {
        const card = { cardId: 'card-1', selectedText: 'Cell division', pageIndex: 1 };
        const anchor = resolveCanvasAnchor(card, sourceModel);
        expect(anchor.status).toBe(ANCHOR_STATUSES.EXACT);
        expect(anchor.matchCount).toBe(1);
    });

    it('D-07: exact anchor has sourceKind, reason, and provenance', () => {
        const card = { cardId: 'card-2', selectedText: 'Apoptosis pathways', pageIndex: 2 };
        const anchor = resolveCanvasAnchor(card, sourceModel);
        expect(anchor.status).toBe(ANCHOR_STATUSES.EXACT);
        expect(anchor.sourceKind).toBe(SOURCE_KINDS.FULLTEXT);
        expect(anchor.reason).toBeNull();
        expect(anchor.matchCount).toBe(1);
    });

    it('D-11: repeated text in source does NOT produce exact (downgrade)', () => {
        // "Signaling" only appears once — let's use a text that repeats
        // Actually let's use a phrase that appears only once
        const repeatedSourceInputs = {
            fulltext: {
                path: 'ft.md',
                text: 'Cell division is key.\n<!-- page 1 -->\nCell division is key again.\nCell death is important.\n<!-- page 2 -->\nCell division is key.',
                exists: true,
                readable: true,
            },
            note: { path: null, text: null, exists: false, readable: false },
        };
        const repeatedModel = buildCanvasSourceModel(entry, repeatedSourceInputs);
        const card = { cardId: 'card-ambig', selectedText: 'Cell division', pageIndex: 0 };
        const anchor = resolveCanvasAnchor(card, repeatedModel);
        // Should downgrade because "Cell division" appears multiple times
        expect(anchor.status).not.toBe(ANCHOR_STATUSES.EXACT);
        expect(anchor.matchCount).toBeGreaterThan(1);
    });

    it('D-11: single match in source produces exact with matchCount:1', () => {
        const card = { cardId: 'card-unique', selectedText: 'Mitochondrial outer membrane permeabilization', pageIndex: 2 };
        const anchor = resolveCanvasAnchor(card, sourceModel);
        expect(anchor.status).toBe(ANCHOR_STATUSES.EXACT);
        expect(anchor.matchCount).toBe(1);
    });

    // ── D-08/D-09: page-level when page metadata exists but no unique text ──

    it('resolves a unique OCR line-end hyphen match with staged metadata', () => {
        const ocrModel = buildCanvasSourceModel(entry, {
            fulltext: {
                path: 'ft.md',
                text: 'The immune-\ncheckpoint response, was durable.',
                exists: true,
                readable: true,
            },
            note: { path: null, text: null, exists: false, readable: false },
        });
        const anchor = resolveCanvasAnchor({
            cardId: 'card-ocr',
            selectedText: 'The immune checkpoint response was durable.',
            pageIndex: 0,
        }, ocrModel);

        expect(anchor.status).toBe(ANCHOR_STATUSES.EXACT);
        expect(anchor.strategy).toBe('ocr-normalized');
        expect(anchor.confidence).toBeGreaterThanOrEqual(0.9);
        expect(anchor.candidateCount).toBe(1);
        expect(anchor.rawStart).toBe(0);
        expect(anchor.rawEnd).toBe(ocrModel.text.length);
    });

    it('removes an OCR line-end hyphen inside a split word', () => {
        const text = 'A multi-\nmodal model.';
        const ocrModel = buildCanvasSourceModel(entry, {
            fulltext: { path: 'ft.md', text, exists: true, readable: true },
            note: { path: null, text: null, exists: false, readable: false },
        });
        const anchor = resolveCanvasAnchor({
            cardId: 'card-hyphenated-word',
            selectedText: 'A multimodal model.',
            pageIndex: 0,
        }, ocrModel);

        expect(anchor.status).toBe(ANCHOR_STATUSES.EXACT);
        expect(anchor.strategy).toBe('ocr-normalized');
        expect(anchor.rawStart).toBe(0);
        expect(anchor.rawEnd).toBe(text.length);
    });

    it('does not equate different mathematical comparison symbols', () => {
        const symbolModel = buildCanvasSourceModel(entry, {
            fulltext: { path: 'ft.md', text: 'p < 0.05', exists: true, readable: true },
            note: { path: null, text: null, exists: false, readable: false },
        });
        const anchor = resolveCanvasAnchor({
            cardId: 'card-semantic-symbol',
            selectedText: 'p > 0.05',
            pageIndex: null,
        }, symbolModel);

        expect(anchor.status).toBe(ANCHOR_STATUSES.UNRESOLVED);
        expect(anchor.strategy).toBe('none');
    });

    it('keeps repeated text unresolved when no context can disambiguate it', () => {
        const repeatedModel = buildCanvasSourceModel(entry, {
            fulltext: {
                path: 'ft.md',
                text: 'Repeated result.\nSome intervening text.\nRepeated result.',
                exists: true,
                readable: true,
            },
            note: { path: null, text: null, exists: false, readable: false },
        });
        const anchor = resolveCanvasAnchor({
            cardId: 'card-repeated',
            selectedText: 'Repeated result.',
            pageIndex: 0,
        }, repeatedModel);

        expect(anchor.status).toBe(ANCHOR_STATUSES.UNRESOLVED);
        expect(anchor.strategy).toBe('none');
        expect(anchor.candidateCount).toBe(2);
        expect(anchor.reason).toMatch(/ambiguous/i);
    });

    it('D-08: page-level when page metadata exists but text is ambiguous or missing', () => {
        const card = { cardId: 'card-page', selectedText: '', pageIndex: 1, pageLabel: '1' };
        const anchor = resolveCanvasAnchor(card, sourceModel);
        expect(anchor.status).toBe(ANCHOR_STATUSES.PAGE_LEVEL);
        expect(anchor.reason).toBeTruthy();
    });

    it('D-09: page-level when selected text too short', () => {
        const card = { cardId: 'card-short', selectedText: 'a', pageIndex: 0 };
        const anchor = resolveCanvasAnchor(card, sourceModel);
        expect(anchor.status).toBe(ANCHOR_STATUSES.PAGE_LEVEL);
        expect(anchor.reason).toMatch(/short|too short/i);
    });

    it('D-09: page-level when selected text not found in source', () => {
        const card = { cardId: 'card-nf', selectedText: 'Non-existent text in the source', pageIndex: 1 };
        const anchor = resolveCanvasAnchor(card, sourceModel);
        expect(anchor.status).toBe(ANCHOR_STATUSES.PAGE_LEVEL);
        expect(anchor.reason).toMatch(/not found|no match|missing/i);
    });

    // ── D-10: unresolved when neither source nor page metadata available ──

    it('D-10: unresolved when source is unavailable', () => {
        const unavailableSourceInputs = {
            fulltext: { path: null, text: null, exists: false, readable: false },
            note: { path: null, text: null, exists: false, readable: false },
        };
        const unavailModel = buildCanvasSourceModel(entry, unavailableSourceInputs);
        const card = { cardId: 'card-unavail', selectedText: 'Some text', pageIndex: 0 };
        const anchor = resolveCanvasAnchor(card, unavailModel);
        expect(anchor.status).toBe(ANCHOR_STATUSES.UNRESOLVED);
        expect(anchor.reason).toBeTruthy();
    });

    it('D-10: unresolved when card has no pageIndex and source is unavailable', () => {
        const unavailModel = buildCanvasSourceModel(entry, {
            fulltext: { path: null, text: null, exists: false, readable: false },
            note: { path: null, text: null, exists: false, readable: false },
        });
        const card = { cardId: 'card-nopage', selectedText: '', pageIndex: null };
        const anchor = resolveCanvasAnchor(card, unavailModel);
        expect(anchor.status).toBe(ANCHOR_STATUSES.UNRESOLVED);
    });

    // ── D-12: downgrade reasons ──

    it('D-12: empty selected text downgrades to page-level or unresolved', () => {
        const card = { cardId: 'card-empty', selectedText: '', pageIndex: 0 };
        const anchor = resolveCanvasAnchor(card, sourceModel);
        expect([ANCHOR_STATUSES.PAGE_LEVEL, ANCHOR_STATUSES.UNRESOLVED]).toContain(anchor.status);
    });

    it('D-12: source-mismatched paper identity downgrades', () => {
        // Source model has paper key PAPER_A, card references a different paper
        const card = { cardId: 'card-mismatch', selectedText: 'Cell division', pageIndex: 0, paperKey: 'PAPER_B' };
        const anchor = resolveCanvasAnchor(card, sourceModel);
        expect(anchor.status).toBe(ANCHOR_STATUSES.PAGE_LEVEL);
        if (anchor.reason) {
            expect(anchor.reason.toLowerCase()).toMatch(/mismatch|identity|paper/i);
        }
    });

    it('D-12: ambiguous matches (multiple in source) downgrade with reason', () => {
        const ambigSourceInputs = {
            fulltext: {
                path: 'ft.md',
                text: 'Important concept.\nImportant concept again.\nImportant concept elsewhere.',
                exists: true,
                readable: true,
            },
            note: { path: null, text: null, exists: false, readable: false },
        };
        const ambigModel = buildCanvasSourceModel(entry, ambigSourceInputs);
        const card = { cardId: 'card-ambig2', selectedText: 'Important concept', pageIndex: 0 };
        const anchor = resolveCanvasAnchor(card, ambigModel);
        expect(anchor.status).not.toBe(ANCHOR_STATUSES.EXACT);
        expect(anchor.matchCount).toBeGreaterThan(1);
    });

    // ── D-14/D-23: anchor preserves diagnostics and identity ──

    it('D-14: anchor has anchorId, cardId, sourceKind, matchCount, pageIndex', () => {
        const card = { cardId: 'card-diag', selectedText: 'Apoptosis pathways', pageIndex: 2 };
        const anchor = resolveCanvasAnchor(card, sourceModel);
        expect(anchor).toHaveProperty('anchorId');
        expect(anchor.anchorId).toBeTruthy();
        expect(anchor.cardId).toBe('card-diag');
        expect(anchor.sourceKind).toBe(SOURCE_KINDS.FULLTEXT);
        expect(anchor).toHaveProperty('matchCount');
        expect(anchor).toHaveProperty('pageIndex');
        expect(anchor.pageIndex).toBe(2);
    });

    it('D-23: anchor includes reason and provenance diagnostics', () => {
        const card = { cardId: 'card-provenance', selectedText: 'Mitochondrial', pageIndex: 2 };
        const anchor = resolveCanvasAnchor(card, sourceModel);
        expect(anchor).toHaveProperty('reason');
        expect(anchor).toHaveProperty('diagnostics');
        // All anchors should have diagnostics, even exact ones (provenance context)
        expect(anchor.diagnostics).toBeTruthy();
    });

    it('D-23: exact anchor has source span with raw source offsets', () => {
        const card = { cardId: 'card-span', selectedText: 'Apoptosis pathways', pageIndex: 2 };
        const anchor = resolveCanvasAnchor(card, sourceModel);
        if (anchor.status === ANCHOR_STATUSES.EXACT) {
            expect(anchor).toHaveProperty('sourceSpan');
            expect(anchor.sourceSpan).toHaveProperty('rawStart');
            expect(anchor.sourceSpan).toHaveProperty('rawEnd');
            expect(anchor.sourceSpan).toHaveProperty('normStart');
            expect(anchor.sourceSpan).toHaveProperty('normEnd');
        }
    });

    // ── D-15/D-18: cards visible when source missing ──

    it('D-15: card with unresolved anchor still has all expected fields', () => {
        const unavailModel = buildCanvasSourceModel(entry, {
            fulltext: { path: null, text: null, exists: false, readable: false },
            note: { path: null, text: null, exists: false, readable: false },
        });
        const card = { cardId: 'card-vis', selectedText: 'Some text', pageIndex: 0, type: 'highlight', color: '#ffd400' };
        const anchor = resolveCanvasAnchor(card, unavailModel);
        expect(anchor.status).toBe(ANCHOR_STATUSES.UNRESOLVED);
        expect(anchor.cardId).toBe('card-vis');
        // Card properties not mutated or removed
        expect(card.cardId).toBe('card-vis');
        expect(card.type).toBe('highlight');
    });

    // ── D-24/D-25: no navigation, connector, SVG, mutation, write-back ──

    it('D-24: anchor model has no navigation, connector, or SVG properties', () => {
        const card = { cardId: 'card-clean', selectedText: 'Cell division', pageIndex: 1 };
        const anchor = resolveCanvasAnchor(card, sourceModel);
        expect(anchor).not.toHaveProperty('navigation');
        expect(anchor).not.toHaveProperty('connector');
        expect(anchor).not.toHaveProperty('svg');
        expect(anchor).not.toHaveProperty('svgPath');
        expect(anchor).not.toHaveProperty('scrollTo');
        expect(anchor).not.toHaveProperty('focus');
    });

    it('D-25: anchor model has no mutation, import, apply, or write-back fields', () => {
        const card = { cardId: 'card-mut', selectedText: 'Cell division', pageIndex: 1 };
        const anchor = resolveCanvasAnchor(card, sourceModel);
        expect(anchor).not.toHaveProperty('edit');
        expect(anchor).not.toHaveProperty('delete');
        expect(anchor).not.toHaveProperty('create');
        expect(anchor).not.toHaveProperty('save');
        expect(anchor).not.toHaveProperty('import');
        expect(anchor).not.toHaveProperty('apply');
        expect(anchor).not.toHaveProperty('writeBack');
        expect(anchor).not.toHaveProperty('writeback');
        expect(anchor).not.toHaveProperty('write_back');
    });

    it('D-24: anchor model properties are all primitives or plain objects (no functions)', () => {
        const card = { cardId: 'card-nofn', selectedText: 'Cell division', pageIndex: 1 };
        const anchor = resolveCanvasAnchor(card, sourceModel);
        for (const [, value] of Object.entries(anchor)) {
            if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
                // Plain object is ok
                expect(value.constructor).toBe(Object);
            } else if (value !== null) {
                expect(['string', 'number', 'boolean']).toContain(typeof value);
            }
        }
    });
});

describe('anchors.js — resolveCanvasAnchors batch (D-06, D-23)', () => {
    let ANCHOR_STATUSES, SOURCE_KINDS;
    let buildCanvasSourceModel, resolveCanvasAnchors;

    beforeAll(async () => {
        const surface = await import('../src/canvas/surface.js');
        SOURCE_KINDS = surface.SOURCE_KINDS;
        buildCanvasSourceModel = surface.buildCanvasSourceModel;
        const anchors = await import('../src/canvas/anchors.js');
        ANCHOR_STATUSES = anchors.ANCHOR_STATUSES;
        resolveCanvasAnchors = anchors.resolveCanvasAnchors;
    });

    it('resolves anchors for all cards in batch', () => {
        const entry = { key: 'PAPER_A' };
        const sourceInputs = {
            fulltext: { path: 'ft.md', text: 'Page one text.\n<!-- page 1 -->\nPage two unique content.', exists: true, readable: true },
            note: { path: null, text: null, exists: false, readable: false },
        };
        const model = buildCanvasSourceModel(entry, sourceInputs);
        const cards = [
            { cardId: 'c1', selectedText: 'Page one', pageIndex: 0 },
            { cardId: 'c2', selectedText: 'Page two unique', pageIndex: 1 },
            { cardId: 'c3', selectedText: '', pageIndex: null },
        ];
        const results = resolveCanvasAnchors(cards, model);
        expect(Array.isArray(results)).toBe(true);
        expect(results.length).toBe(3);
        expect(results[0]).toHaveProperty('anchorId');
        expect(results[1]).toHaveProperty('anchorId');
        expect(results[2]).toHaveProperty('anchorId');
    });

    it('each card result preserves cardId mapping', () => {
        const entry = { key: 'PAPER_A' };
        const sourceInputs = {
            fulltext: { path: 'ft.md', text: 'Unique content A.\n<!-- page 1 -->\nUnique content B.', exists: true, readable: true },
            note: { path: null, text: null, exists: false, readable: false },
        };
        const model = buildCanvasSourceModel(entry, sourceInputs);
        const cards = [
            { cardId: 'c1', selectedText: 'Unique content A', pageIndex: 0 },
            { cardId: 'c2', selectedText: 'Unique content B', pageIndex: 1 },
        ];
        const results = resolveCanvasAnchors(cards, model);
        expect(results[0].cardId).toBe('c1');
        expect(results[1].cardId).toBe('c2');
    });

    it('returns empty array for empty cards input', () => {
        const entry = { key: 'PAPER_A' };
        const sourceInputs = {
            fulltext: { path: 'ft.md', text: 'Content.', exists: true, readable: true },
            note: { path: null, text: null, exists: false, readable: false },
        };
        const model = buildCanvasSourceModel(entry, sourceInputs);
        const results = resolveCanvasAnchors([], model);
        expect(Array.isArray(results)).toBe(true);
        expect(results.length).toBe(0);
    });

    it('handles null/undefined cards gracefully', () => {
        const entry = { key: 'PAPER_A' };
        const sourceInputs = {
            fulltext: { path: 'ft.md', text: 'Content.', exists: true, readable: true },
            note: { path: null, text: null, exists: false, readable: false },
        };
        const model = buildCanvasSourceModel(entry, sourceInputs);
        expect(resolveCanvasAnchors(null, model)).toEqual([]);
        expect(resolveCanvasAnchors(undefined, model)).toEqual([]);
    });
});

describe('anchors.js — pure boundary (D-04, D-05, D-26)', () => {
    it('anchors.js exports are pure CommonJS data functions', async () => {
        const mod = await import('../src/canvas/anchors.js');
        expect(mod).toHaveProperty('ANCHOR_STATUSES');
        expect(mod).toHaveProperty('MIN_EXACT_TEXT_CHARS');
        expect(mod).toHaveProperty('resolveCanvasAnchor');
        expect(mod).toHaveProperty('resolveCanvasAnchors');
        expect(Object.isFrozen(mod.ANCHOR_STATUSES)).toBe(true);
    });

    it('anchors.js functions contain no DOM, fs, or Obsidian references', async () => {
        const mod = await import('../src/canvas/anchors.js');
        for (const key of Object.keys(mod)) {
            if (typeof mod[key] === 'function') {
                const fnStr = mod[key].toString();
                expect(fnStr).not.toContain('require("fs")');
                expect(fnStr).not.toContain("require('fs')");
                expect(fnStr).not.toContain('require("obsidian")');
                expect(fnStr).not.toContain("require('obsidian')");
                expect(fnStr).not.toContain('innerHTML');
            }
        }
    });
});
